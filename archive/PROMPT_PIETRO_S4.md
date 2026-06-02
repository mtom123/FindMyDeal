# Prompt Pietro — Sessione S4: Deep Menu Scraping (02/06/2026)

> **OBIETTIVO STRATEGICO**
> Non cercare nuove venues. Re-scan PROFONDA dei menu di venues già nel DB con estrazione PARZIALE (1-3 items). Un bar che ha negroni quasi certamente ha anche gin tonic, mojito, spritz — l'agent precedente li ha persi.
>
> **TARGET MISURABILE**: +500-800 price points netti, senza nuove venues, mantenendo qualità.

---

## CONTESTO

- Sito: **SurPrice** (ex FoodPrice) — collettore di prezzi multi-categoria. Il drink di Milano resta il primo vertical anchor.
- Stato DB: 924 price points, 158 venues mappa, 613 venue-product pairs su 22 prodotti.
- Tu hai fatto S3 (leggimenu brute-force + osm_direct2) → +78 price points netti dopo pulizia CEO. Il filtro Milano post-hoc ha scartato il 92% del tuo output. Lezione: filtro città INLINE da qui in poi.

**Numeri grezzi che dimostrano il gap di estrazione attuale:**

| Prodotto | Price points DB |
|---|---|
| Spritz | 138 |
| Negroni | 87 |
| Gin Tonic | 54 |
| Margarita | 35 |
| Mojito | 42 |
| Moscow Mule | 16 |

Se un bar che ha negroni ha anche gin tonic (verità statistica per i cocktail bar), allora abbiamo perso ~30 gin tonic da venues già scansionate. Replicato su tutti i prodotti = centinaia di price points persi.

---

## SETUP

```bash
cd D:\FindMyDeal       # o equivalente macOS
git clone https://github.com/mtom123/FindMyDeal.git . 2>/dev/null || git pull origin main

# Leggi:
cat website/AGENTS.md
cat website/AGENTS_STATE.md
cat website/scripts/SCHEMA_AGENTI.md
cat website/PIETRO_S4_TARGETS.csv    # ⭐ lista priorità preparata dal CEO
```

Working dir output: `website/raw_sources/`
Prefisso file: `agent4_deepscan_*`

---

## STEP 1 — TARGET LIST: 88 venues con estrazione parziale

Il CEO ha preparato `website/PIETRO_S4_TARGETS.csv` con tutti i venues che hanno SOLO 1-3 price points nel DB. È la lista esatta su cui lavorare.

| current_items | n_venues | Yield atteso/venue |
|---|---|---|
| 1 item | 40 | +5-10 items |
| 2 items | 20 | +4-8 items |
| 3 items | 28 | +3-6 items |

Carica e processa:

```python
import csv

with open('website/PIETRO_S4_TARGETS.csv', encoding='utf-8-sig') as f:
    targets = list(csv.DictReader(f))

print(f"Targets: {len(targets)}")
# Sort: priorità ai venue con menos items (più upside)
targets.sort(key=lambda x: int(x['current_items']))
```

Ogni target ha:
- `venue_name`: nome canonico
- `current_items`: quanti price points attualmente nel DB
- `platforms`: source platforms da cui sono stati estratti
- `source_urls`: gli URL effettivi (pipe-separated)
- `lat`, `lon`: coordinate per geocoding

---

## STEP 2 — DEEP SCAN ALGORITMO

Per ogni venue target:

### 2.1 Re-visita il source URL originale

```python
import requests, time, re
from bs4 import BeautifulSoup

HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/124.0.0.0'}

def fetch(url):
    if url.lower().endswith('.pdf'):
        # PDF: usa pdfplumber
        import pdfplumber, io
        r = requests.get(url, headers=HEADERS, timeout=15)
        return ('pdf', io.BytesIO(r.content))
    else:
        r = requests.get(url, headers=HEADERS, timeout=10)
        return ('html', r.text)
```

### 2.2 Estrai TUTTI i drink standard, non solo quello già nel DB

**Regex pattern catalog** (riusa estensivamente):

```python
DRINK_PATTERNS = {
    'spritz':            r'\b(spritz|aperol\s*spritz|campari\s*spritz|hugo\s*spritz|select\s*spritz|cynar\s*spritz)\b',
    'negroni':           r'\b(negroni(?!\s*sbagliato)|negroni\s*sbagliato|boulevardier|negrosky)\b',
    'americano':         r'\b(americano)\b(?!\s*(caff|coffee))',  # NO caffè americano
    'gin_tonic':         r'\b(gin\s*tonic|gin\s*&\s*tonic|gin\s*\+\s*tonic|g\s*&\s*t)\b',
    'mojito':            r'\b(mojito|mojito\s*classico|mojito\s*royal)\b',
    'moscow_mule':       r'\b(moscow\s*mule|london\s*mule|mexican\s*mule|mediterranean\s*mule)\b',
    'margarita':         r'\b(margarita|tommy\'?s\s*margarita|smoky\s*margarita|paloma)\b',
    'daiquiri':          r'\b(daiquiri|hemingway\s*daiquiri|frozen\s*daiquiri)\b',
    'manhattan':         r'\b(manhattan|perfect\s*manhattan|rob\s*roy)\b',
    'beer_moretti':      r'\b(moretti|birra\s*moretti)\b',
    'beer_heineken':     r'\b(heineken)\b',
    'beer_peroni':       r'\b(peroni|nastro\s*azzurro)\b',
    'beer_draft_small':  r'\b(spina\s*piccola|birra\s*piccola|piccola\s*spina|small\s*draft|0[.,]2|0[.,]3|33cl)\b',
    'beer_draft_medium': r'\b(spina\s*media|birra\s*media|media\s*spina|medium\s*draft|0[.,]4|0[.,]5|50cl|40cl)\b',
    'beer_bottle':       r'\b(birra\s*bottiglia|bottiglia\s*birra|corona|ichnusa|menabrea|baladin|beck.?s|guinness|kilkenny|tennent.?s|warsteiner)\b',
    'wine_glass':        r'\b(calice\s*(?:di\s*)?vino|vino\s*al\s*calice|wine\s*glass|glass\s*of\s*wine)\b',
    'prosecco_glass':    r'\b(prosecco|flute|spumante\s*calice)\b',
    'espresso':          r'\b(caff[eè](?!\s*americano)|espresso(?!\s*martini))\b',
    'cappuccino':        r'\b(cappuccino)\b',
    'soft_drink':        r'\b(coca\s*cola|fanta|sprite|chinotto|schweppes|tonica|tonic\s*water|bibita)\b',
    'water':             r'\b(acqua(?:\s*(?:naturale|frizzante|gassata))?)\b',
}
```

### 2.3 Estrazione price+name per ogni hit

```python
PRICE_RE = re.compile(r'€\s*(\d{1,2}(?:[,.]\d{1,2})?)|(?<!\d)(\d{1,2}(?:[,.]\d{1,2})?)\s*€')

def extract_items_from_text(text, venue_id, venue_name, source_url):
    items = []
    # Split in paragrafi/righe ragionevoli
    chunks = re.split(r'\n+|<br/?>|\.\s+', text)
    
    for chunk in chunks:
        chunk_clean = re.sub(r'\s+', ' ', chunk).strip()
        if len(chunk_clean) > 200 or len(chunk_clean) < 5:
            continue
        
        # Trova prezzi nella chunk
        prices = PRICE_RE.findall(chunk_clean)
        if not prices:
            continue
        
        # Per ogni pattern drink, check se nel chunk
        for prod_code, pattern in DRINK_PATTERNS.items():
            if re.search(pattern, chunk_clean, re.I):
                # Estrai il prezzo più vicino (prima coincidenza)
                for price_match in prices:
                    price_str = price_match[0] or price_match[1]
                    try:
                        price = float(price_str.replace(',', '.'))
                    except: continue
                    
                    if price < 0.50 or price > 80:
                        continue
                    
                    # Quality: skip se contiene parole NO-drink
                    if re.search(r'\b(piatto|pasta|pizza|insalata|carne|pesce|risotto|antipasto|primo|secondo|dolce|dessert)\b', chunk_clean, re.I):
                        continue
                    
                    # Skip caffè americano falsamente classificato
                    if prod_code == 'americano' and re.search(r'caff[eè]', chunk_clean, re.I):
                        continue
                    
                    # Skip rovere americano (botte whiskey)
                    if 'rovere' in chunk_clean.lower():
                        continue
                    
                    items.append({
                        'source_platform':    'direct_website',  # o leggimenu se URL leggimenu
                        'source_venue_id':    venue_id,
                        'venue_name':         venue_name,
                        'venue_url':          source_url,
                        'menu_section':       '',
                        'item_name':          chunk_clean[:80],
                        'item_description':   chunk_clean[:200],
                        'raw_price':          f"€ {price_str}",
                        'normalized_price_eur': price,
                        'currency':           'EUR',
                        'price_type':         'menu',
                        'item_type':          'drink',
                        'normalized_product': prod_code,
                        'confidence':         'medium',  # downgrade da high — è re-extraction
                        'allergens':          '',
                        'retrieved_at':       datetime.utcnow().isoformat() + 'Z',
                        'source_url':         source_url,
                    })
                    break  # un prezzo per match
    
    # Dedup interno: stesso prodotto + stesso prezzo nella stessa venue
    seen = set()
    unique = []
    for it in items:
        key = (it['normalized_product'], it['normalized_price_eur'])
        if key not in seen:
            seen.add(key)
            unique.append(it)
    return unique
```

### 2.4 Per PDF: path-probing aggiuntivo

Se il source URL è una pagina HTML del sito ufficiale, cerca link a PDF nella pagina:

```python
def find_pdfs_on_page(html, base_url):
    soup = BeautifulSoup(html, 'lxml')
    pdfs = []
    for a in soup.find_all('a', href=True):
        href = a['href']
        if href.lower().endswith('.pdf'):
            full = urljoin(base_url, href)
            pdfs.append(full)
    return list(set(pdfs))
```

Aggiungi anche path-probing standard se non trovi nulla:
```
/menu /drink /drinks /cocktail /cocktails /carta /listino /menu/cocktail
/menu/drink /menu/bevande /la-carta /our-menu /drinks-menu
```

---

## STEP 3 — QUALITY GATE INLINE (REGOLA FERREA POST-S3)

**NON consegnare un singolo item che non passa questi 8 filtri:**

```python
def quality_check_inline(item):
    name = item.get('item_name', '')
    desc = item.get('item_description', '')
    url = item.get('source_url', '')
    venue = item.get('venue_name', '')
    prod = item.get('normalized_product', '')
    try: price = float(item.get('normalized_price_eur', 0))
    except: price = 0
    
    text = (name + ' ' + desc).lower()
    
    # 1. NO image URLs
    if any(url.lower().endswith(e) for e in ['.jpg','.jpeg','.png','.webp','.gif','.ico','.svg']):
        return False, 'IMAGE_URL'
    
    # 2. NO non-Milan address
    if any(c in text for c in ['pessione','torino','palermo','siena','parma','ferrara','lecce','trento','san ferdinando']):
        return False, 'NON_MILAN'
    
    # 3. NO oak false positive
    if 'rovere americano' in text:
        return False, 'OAK_FALSE_POS'
    
    # 4. NO caffè americano classificato come americano cocktail
    if prod == 'americano' and re.search(r'caff[eè]', text):
        return False, 'COFFEE_NOT_COCKTAIL'
    
    # 5. Prezzo sensato
    if price < 0.50 or price > 80:
        return False, f'PRICE_OUT_OF_RANGE_{price}'
    
    # 6. item_name non troppo lungo
    if len(name) > 150:
        return False, 'NAME_TOO_LONG'
    
    # 7. NO pagine_gialle
    if 'paginegialle' in url.lower():
        return False, 'PAGINEGIALLE'
    
    # 8. NO food context
    if re.search(r'\b(piatto|pasta|pizza|carne|pesce|risotto|antipasto|primo|secondo|dolce|dessert|insalata)\b', text):
        return False, 'FOOD_CONTEXT'
    
    return True, None
```

---

## STEP 4 — EXPECTED OUTPUT FORMAT

```
website/raw_sources/agent4_deepscan_menu_items.csv
website/raw_sources/agent4_deepscan_venues.csv
```

**venues**: NON aggiungere nuovi venue. Per ogni venue target già nel DB, scrivi una riga con i metadati (per linking nel merge):

```python
# venue_url e source_venue_id devono matchare quelli già nel DB
# in modo che il merge_pipeline.py li mappi sullo stesso canonical_id
{
    'source_platform':    target['platforms'].split(';')[0],  # platform principale
    'source_venue_id':    target['venue_name'].lower().replace(' ','_'),  # stabile
    'venue_name':         target['venue_name'],
    'venue_url':          target['source_urls'].split('|')[0],
    'address':            '',
    'city':               'Milano',
    'latitude':           target['lat'],
    'longitude':          target['lon'],
    # ... altri campi vuoti
    'has_menu':           'True',
    'extraction_status':  'ok',
    'retrieved_at':       NOW,
}
```

**items**: tutte le righe estratte che passano il quality gate.

---

## STEP 5 — RATE LIMITS

- Siti diretti: 2.5s tra GET
- leggimenu re-fetch: 2s
- PDF download: 1s
- HTTP 429 → sleep 60s + retry
- HTTP 403 → skip venue, log

---

## STEP 6 — REPORT FINALE

A fine sessione genera `agent4_REPORT.md`:

```markdown
# Agent4 deep-scan report

| Metrica | Valore |
|---|---|
| Venues processate | XX/88 |
| Items estratti (raw) | XXX |
| Items passati quality gate | XXX |
| Items rifiutati | XX (breakdown per motivo) |
| Nuovi prodotti per venue media | X.X |

## Top venues per yield
| Venue | Items prima | Items dopo |
|---|---|---|

## Quality issues (per analisi)
- IMAGE_URL: XX
- FOOD_CONTEXT: XX
- NON_MILAN: XX
- ...
```

---

## CONSEGNA

```bash
cd ~/Desktop/FindMyDeal_clone  # o equivalente
git pull --rebase origin main
git add website/raw_sources/agent4_deepscan_*.csv website/agent4_REPORT.md
git commit -m "data: S4 deep-scan — N venues re-processate, M items aggiunti"
git push origin main
```

Avvisa il CEO con report sintetico. **NON toccare** `data/unified_*.csv`, `prices_data.json`, `index.html`, file di altre agent (agent3_*, leggimenu_s3_*).

---

## ERRORI DA NON RIPETERE (S3 lesson learned)

1. ❌ **Brute-force senza filtro città**: S3 ha pescato venues di tutta Italia. Su S4 lavori SOLO su lista predeterminata dal CEO.
2. ❌ **Item_name = navigation page text**: skippa chunk > 200 char, sono HTML nav.
3. ❌ **Double-letter PDF parser**: se vedi "HHAARRPP" applica regex `([A-Z])\1` → `\1` prima di salvare.
4. ❌ **Food/drink confusion**: filtra parole "pasta/pizza/risotto" nel context.
5. ❌ **Caffè americano = cocktail americano**: check inline obbligatorio.

---

## SE FINISCI PRIMA

Backlog dopo i 88 target:

1. **TheFork via Wayback Machine**: CDX API discovery (l'agent Drink Milano ha aperto la tecnica su Glovo, replicabile)
2. **eatbu sitemap nazionale → filter Milano** (31K venues, ~30-80 Milano nuove)
3. **Geocoding manuale 24 venues fallback Duomo** (lista da `unified_prices.csv` filtrando lat=45.4642)

---

Buona sessione. Target finale **+500 price points** netti.
