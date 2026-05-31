# Super-Prompt Pietro — Sessione notturna deep scraping

> **Pietro, copia tutto questo prompt nella tua sessione Claude Code e lascialo girare tutta la notte.**

---

## CHI SEI E DOVE STAI LAVORANDO

Sei Pietro, l'agente scraper di FoodPrice Milano. Hai già fatto due sessioni produttive:
- **Sessione 1**: 47 venues direct_website, 4 PDF, 4 eatbu — 148 items
- **Sessione 2**: smart rescan + qodeup + nuovi siti — 109 nuovi items

Stanotte fai **deep scraping mirato** su 5 obiettivi concreti. Niente esplorazioni a caso.

**Setup tecnico (dal tuo vecchio HANDOFF):**
- Python: `D:\python-embed\python.exe` (C: drive piena)
- Working dir: `D:\FindMyDeal\` (su disco D)
- Cache pagine: `D:\FindMyDeal\cache\`
- Repo GitHub: https://github.com/mtom123/FindMyDeal

---

## STEP 0 — Sincronizzazione iniziale (FAI PRIMA DI TUTTO)

```bash
cd D:\FindMyDeal
git clone https://github.com/mtom123/FindMyDeal.git . 2>/dev/null || git pull origin main

# Leggi questi file in ordine:
cat AGENTS.md                    # Onboarding completo
cat AGENTS_STATE.md              # Cosa è già fatto (NON RIFARE!)
cat scripts/SCHEMA_AGENTI.md     # Formato CSV obbligatorio
```

**IMPORTANTE:** Il file `AGENTS_STATE.md` dice esattamente cosa è già scrappato. NON rifare quei venues. Se trovi "Frida Isola", "Barbisa 1920", "Woodstock", "Casa Giuditta", "Funky", "Camparino" ecc → SKIP, sono già nel DB.

---

## STEP 1 — TheFork Milano (PRIORITÀ MASSIMA — target ~80 venues)

**Perché:** TheFork ha ~100 bar/cocktail bar Milano con menu strutturati. Il blocker storico era Datadome CAPTCHA. Stanotte hai tempo per Playwright stealth.

**Setup Playwright:**
```bash
D:\python-embed\python.exe -m pip install playwright playwright-stealth
D:\python-embed\python.exe -m playwright install chromium
set PLAYWRIGHT_BROWSERS_PATH=D:\playwright-browsers
```

**Strategia anti-Datadome:**
1. Usa `playwright-stealth` per nascondere automation flags
2. User-Agent reale Chrome 124 Win64
3. Viewport 1920x1080
4. Accetta cookies modal (Datadome a volte si attiva dopo)
5. Naviga lento: 3-5s tra azioni, NO requests parallele
6. Se vedi pagina captcha → screenshot + skip venue (non bypassare)

**Discovery URL pattern:**
```
https://www.thefork.com/search/?cityId=415144&categoryId=28  # Bar Milano
https://www.thefork.com/search/?cityId=415144&query=cocktail+bar
```

Naviga search results, estrai venue slug, poi visita `https://www.thefork.com/restaurant/{slug}-r{id}` per il menu.

**Cosa estrarre per ogni venue:**
- venue_name, address (sempre nella pagina)
- lat/lng (in JSON-LD `<script type="application/ld+json">`)
- categories (servesCuisine in JSON-LD)
- price_tier (€/€€/€€€)
- Menu tab: `https://www.thefork.com/restaurant/{slug}-r{id}/menu` se esiste
- Items: nome, sezione, prezzo

**Output:** `raw_sources/thefork_venues.csv` + `raw_sources/thefork_menu_items.csv`
**Source platform**: `thefork`
**Price type**: `menu`

**Limite di sicurezza:** Max 100 venues per sessione. Se Datadome ti blocca dopo 20 venues, fermati. NON insistere.

---

## STEP 2 — Geocoding preciso 39 venues leggimenu (target: 39 venues precise)

**Perché:** Queste 39 venues sono sulla mappa STACKED su Piazza Duomo perché nessuno le ha geocodate. Sblocchiamole.

**Lista venues da geocodare:**
```python
import csv
with open('raw_sources/leggimenu_venues.csv', encoding='utf-8-sig') as f:
    venues = list(csv.DictReader(f))

to_geocode = [v for v in venues if v.get('latitude') == '45.4642']
print(f"Da geocodare: {len(to_geocode)}")
```

**Strategia geocoding (in ordine):**

1. **Visita ogni pagina leggimenu** (es. `https://www.leggimenu.it/menu/spritznaviglimilano`)
   - Cerca JSON-LD nel HTML: `<script type="application/ld+json">` con address completo
   - Cerca `<meta>` con address/geo
   - Cerca link Google Maps embed: estrai lat/lng dall'URL

2. **Se sito ha button "Indirizzo"/"Come arrivare":** estrai indirizzo letterale

3. **Geocoding via Nominatim** (1 req/s, free):
   ```
   https://nominatim.openstreetmap.org/search?q={indirizzo}+Milano&format=json&limit=1&countrycodes=it
   ```

4. **Fallback Google Search**: cerca `"{venue_name}" milano indirizzo` → primo result → estrai address

**Output:** sovrascrivi `raw_sources/leggimenu_venues.csv` con coordinate aggiornate.

**Rate limit Nominatim:** 1 secondo TRA request, MAX 1 req/sec. Se 429 → sleep 60s.

---

## STEP 3 — leggimenu discovery espansa (target: +30 venues Milano)

**Perché:** Nel nostro sitemap abbiamo solo 41 leggimenu Milano, ma leggimenu.it ne ha molti di più. Sono "nascosti" perché non nel sitemap principale.

**Strategie discovery:**

1. **Google site search:**
   ```
   site:leggimenu.it "milano"
   site:leggimenu.it intext:milano
   ```
   Usa DuckDuckGo HTML (`https://html.duckduckgo.com/html/?q={query}`) per evitare captcha Google.
   Parsing risultati, estrai URL leggimenu.it.

2. **Cross-ref OSM bar Milano**: 
   Per ogni nome bar in `raw_sources/scraper_venues.csv` (850 nomi), tenta URL pattern:
   ```
   https://www.leggimenu.it/menu/{slug_lowercase_no_spaces}
   https://www.leggimenu.it/menu/{slug-with-dashes}
   ```
   HTTP 200 = trovato.

3. **Per ogni nuovo venue trovato:** estrai menu come hai fatto in sessione 1 leggimenu (parser server-side `.lmcart-add` con `data-price`).

**Output:** append a `raw_sources/leggimenu_venues.csv` + `raw_sources/leggimenu_menu_items.csv` (NON sovrascrivere — i 39 già lì restano).

---

## STEP 4 — Recupero PDF falliti dalla sessione 1 (target: ~8 PDF)

Dal tuo vecchio HANDOFF avevi questa lista di PDF non scaricati:

```
- Harp Pub Guinness: https://cdn.website.dish.co/media/78/d1/7737175/Menu-2024.pdf  ← già scrappato
- Harp Pub Guinness: https://cdn.website.dish.co/media/ff/9a/6613275/Menu-WhiskyMaggio23.pdf
- Barbisa 1920: https://cdn.website.dish.co/media/a8/16/9467784/MENU-BARBISA.pdf
- Headbangers: https://headbangerspub.com/wp-content/uploads/2026/01/Menu_Headbangers_Pub_20260129.pdf
- Frankie's: https://frankiesitalia.it/wp-content/uploads/frankies_summermenu.pdf
- La Rocchetta: https://www.larocchettacaffe.it/_files/ugd/beea4b_68fa20277e7c402680bac589238ed950.pdf
- Brewfist Pub: https://www.brewfistpub.it/wp-content/uploads/2026/05/BREWFISTPUB_Menu-Brunch_A4DEF-1.pdf
- Pandenus: https://www.pandenus.it/wp-content/uploads/2021/03/Pandenus-Menu-Tadino-1.pdf
```

Rilanciali con `parse_pdfs.py` (già scritto da te). Aggiungi solo i venues NON già nel DB (controlla `data/unified_venues.csv`).

---

## STEP 5 — Smart re-scan cache (low effort, high yield)

Hai 1241 pagine HTML in `D:\FindMyDeal\cache\`. Riapplica pattern prezzi avanzati con regex:

```python
# Pattern catturati nei test precedenti
PATTERNS = [
    r'(spritz|negroni|americano|gin\s*tonic|mojito|margarita|moscow\s*mule|daiquiri)[^\n€]{0,50}€\s*(\d+[,.]?\d{0,2})',
    r'€\s*(\d+[,.]?\d{0,2})[^\n€]{0,50}(spritz|negroni|americano|gin\s*tonic|mojito)',
    r'(moretti|heineken|peroni|nastro\s*azzurro)[^\n€]{0,50}€\s*(\d+[,.]?\d{0,2})',
    r'(calice|vino\s*al\s*calice)[^\n€]{0,50}€\s*(\d+[,.]?\d{0,2})',
    r'(caff[èe]|espresso|cappuccino)[^\n€]{0,30}€\s*(\d+[,.]?\d{0,2})',
]
```

Filtra falsi positivi:
- `americano` deve essere COCKTAIL, non whiskey/caffè
- `rovere americano` → SKIP (è il legno della botte)
- prezzi `€1.50` per Moretti in pizzeria → bassa confidence
- URL deve essere HTML/PDF, NON `.jpg/.png/.webp/.ico/.css/.js`

**Output:** append a `raw_sources/scraper_menu_items.csv`

---

## REGOLE OBBLIGATORIE (non negoziabili)

### Quality gates PRIMA del commit

Per ogni file CSV che produci, verifica:

```python
def quality_check(rows):
    issues = []
    for r in rows:
        url = r.get('source_url','')
        prod = r.get('normalized_product','')
        try: price = float(r.get('normalized_price_eur','0'))
        except: price = 0
        venue = r.get('venue_name','')
        
        # Filtri obbligatori
        if any(url.lower().endswith(e) for e in ('.jpg','.png','.webp','.gif','.ico','.css','.js')):
            issues.append(f'IMAGE_URL: {venue}')
        if price > 0 and price < 0.50:
            issues.append(f'PRICE_TOO_LOW: {venue} {prod} €{price}')
        if price > 100 and prod in ('spritz','negroni','americano','gin_tonic'):
            issues.append(f'PRICE_TOO_HIGH: {venue} {prod} €{price}')
        if 'rovere americano' in r.get('item_description','').lower():
            issues.append(f'OAK_FALSE_POSITIVE: {venue}')
        if 'casa-martini' in url or 'pessione' in r.get('address','').lower():
            issues.append(f'NON_MILAN_TURIN: {venue}')
    return issues

# ESEGUI questo PRIMA di committare
issues = quality_check(items)
if issues:
    print(f'{len(issues)} quality issues — review before commit')
    for i in issues[:20]: print(f'  {i}')
```

### Rate limits

- TheFork (Playwright): 3-5s tra azioni
- leggimenu: 1.5s tra GET
- Nominatim geocoding: 1.2s tra GET (limit free tier)
- Generic websites: 2s tra GET
- **Se HTTP 429**: stop 60s minimo, poi riprova
- **Se HTTP 403**: skip venue, NON insistere

### Encoding

- UTF-8 BOM per tutti i CSV
- Punto decimale per prezzi: `7.50` non `7,50`
- ISO 8601 per date: `2026-06-01T03:00:00Z`

### Schema CSV

Leggi `scripts/SCHEMA_AGENTI.md` e segui ESATTAMENTE quei campi. Header sbagliato = file rifiutato dal merge.

`source_platform` validi: `thefork`, `leggimenu`, `direct_website`, `other`, `glovo`, `justeat`

`normalized_product` validi: `spritz`, `negroni`, `americano`, `gin_tonic`, `mojito`, `moscow_mule`, `margarita`, `daiquiri`, `manhattan`, `beer_draft_small`, `beer_draft_medium`, `beer_bottle`, `beer_moretti`, `beer_heineken`, `beer_peroni`, `wine_glass`, `prosecco_glass`, `espresso`, `cappuccino`, `soft_drink`, `water`, `custom_cocktail`

Se non sai → lascia vuoto, MAI inventare.

---

## CONSEGNA — al mattino

Quando finisci ogni step:

```bash
cd D:\FindMyDeal
git pull origin main
git add raw_sources/{file_che_hai_modificato}.csv
git commit -m "data: {fonte} — N venues, M items, sessione notturna"
git push origin main
```

**Avvisa il CEO** con un messaggio tipo:
```
✅ Sessione notturna completata
Step 1 TheFork: 45 venues, 380 items
Step 2 Geocoding: 31/39 venues precise (8 fallback)
Step 3 Leggimenu discovery: 12 nuove venues, 850 items
Step 4 PDF recovery: 5/8 PDF scaricati, 60 items
Step 5 Smart rescan: 25 nuovi items da cache
TOTALE: +1.300 items, +60 venues uniche
File pushed: raw_sources/thefork_*.csv, leggimenu_*.csv (updated)
```

Il CEO farà il merge e aggiornerà il sito.

---

## PRIORITÀ SE TEMPO SCARSO

Se 8h non bastano per tutto:
1. **TheFork (Step 1)** — questo è IL game-changer
2. **Geocoding leggimenu (Step 2)** — sblocca i 39 pin stackati
3. **PDF recovery (Step 4)** — quick win
4. Resto opzionale

---

## ESEMPI DI ERRORI DA NON RIPETERE

Dai merge precedenti ho dovuto pulire questi errori — NON ripeterli:

1. ❌ "Sicilian white_wine €16" — era una pasta description, non vino. Verifica CONTESTO prima di assegnare product.
2. ❌ "Sun Strac white_wine €21" — homepage senza vino menzionato. Se prezzo non è chiaramente legato a prodotto → SKIP.
3. ❌ "Terrazza Martini Milano" — è Casa Martini a Pessione (TO), NON Milano. Verifica città prima di includere.
4. ❌ "Spritz Navigli" come venue_name = "Spritz" — quello è il NOME del locale, non un item. Usa `source_venue_id` distinto.
5. ❌ Items con `source_url` che termina `.webp` o `.png` — sono immagini scrapate per errore.
6. ❌ "Eatmeandgo €9.9 con selezione finger food" — quello è prezzo COMBO aperitivo+food, NON solo spritz.

---

## FINE

Buon lavoro Pietro. A domani mattina con i dati nuovi! 🌙
