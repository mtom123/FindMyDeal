# Prompt Peppe — Barber/Hair Salon Price Intelligence S1 (02/06/2026)

> **CONTESTO**: SurPrice si estende al 3° vertical: **barbieri e parrucchieri**.
> Mercato target: ~€6B Italia, ~3.500 saloni solo a Milano, opacità prezzi altissima.
> Approccio: **high-signal first** — partiamo dai booking aggregator che concentrano
> venue commercialmente attivi e prenotabili. NO scraping web-wide casuale.
>
> **Tua sessione**: S1 — Master list discovery + Provider mapping + Sample prezzi.

---

## OBIETTIVI MISURABILI S1

| Metrica | Target |
|---|---|
| Venues master list (Italia, da aggregatori) | ≥ 5.000 |
| Di cui con prezzi estratti (sample) | ≥ 200 |
| Di cui a Milano (benchmark city) | ≥ 500 |
| Provider booking mappati | ≥ 4 |
| Smoke test scraping Treatwell (priority #1) | ✅ completo |

---

## SETUP

```bash
cd ~/percorso/FindMyDeal   # NON usare "website/" — è alias sbagliato
git pull origin main

# Onboarding obbligatorio:
cat AGENTS.md
cat AGENTS_STATE.md           # vedi cosa già esiste — NON duplicare
cat scripts/SCHEMA_AGENTI.md  # schema CSV vincolante
```

Output directory: `raw_sources/`  
Prefisso file: `barber_s1_*`

---

## VOCABOLARIO CHIUSO — 23 SERVIZI

Già definiti in `scripts/normalization.py` come `BARBER_PRICE_RANGES` + `BARBER_PRODUCTS`.
**Importa e usa prima di scrivere qualsiasi item:**

```python
import sys; sys.path.insert(0, 'scripts')
from normalization import BARBER_PRODUCTS, validate_barber_item, BARBER_PRICE_RANGES

# Per ogni item estratto:
ok, clean_item, reason = validate_barber_item(item)
if not ok:
    continue  # skip, log reason
```

| Codice `normalized_product` | Servizio | Range EUR |
|---|---|---|
| `haircut_man` | Taglio uomo | 8–70 |
| `haircut_woman` | Taglio donna | 15–140 |
| `haircut_child` | Taglio bambino | 7–40 |
| `beard_trim` | Rifilatura barba | 7–45 |
| `beard_shave` | Rasatura classica | 12–70 |
| `beard_color` | Colorazione barba | 12–65 |
| `hair_color` | Colorazione capelli | 35–220 |
| `hair_highlight` | Mèches / colpi di sole | 45–280 |
| `hair_bleach` | Decolorazione | 55–320 |
| `hair_toning` | Tonalizzazione | 18–110 |
| `hair_wash_blowdry` | Lavaggio + piega | 12–90 |
| `hair_blowdry` | Piega | 8–65 |
| `hair_treatment` | Trattamento / maschera | 12–90 |
| `hair_perm` | Permanente | 55–220 |
| `hair_straightening` | Stiratura / cheratina | 70–420 |
| `hair_extensions` | Extension | 150–1100 |
| `hair_updo` | Acconciatura cerimonia | 35–220 |
| `eyebrow_trim` | Sopracciglia | 6–35 |
| `face_scrub` | Scrub / esfoliante viso | 12–65 |
| `face_mask` | Maschera viso | 12–55 |
| `package_cut_beard` | Pacchetto taglio + barba | 18–95 |
| `package_color_cut` | Pacchetto colore + taglio | 55–320 |
| `package_full_treatment` | Pacchetto trattamento completo | 40–200 |

Se non sei sicuro → `normalized_product` vuoto. **MAI inventare codici non in lista.**

---

## SCHEMA CSV — VENUES

File: `raw_sources/barber_s1_venues.csv`

```
source_platform,source_venue_id,venue_name,venue_url,address,city,province,region,
postal_code,latitude,longitude,categories,barber_category,price_tier,rating,
rating_count,phone,website,opening_hours,booking_provider,extraction_status,
retrieved_at,vertical
```

Campi aggiuntivi vs schema base:
- `province` — es. "Milano", "Roma"
- `region` — es. "Lombardia", "Lazio"
- `barber_category` — **vocabolario chiuso**: `barber` / `salon_donna` / `unisex` / `kids`
- `booking_provider` — es. "treatwell", "uala", "fresha", "booksy"
- `vertical` = **`barber`** — sempre

## SCHEMA CSV — ITEMS

File: `raw_sources/barber_s1_menu_items.csv`

```
source_platform,source_venue_id,venue_name,venue_url,menu_section,item_name,
item_description,raw_price,normalized_price_eur,currency,price_type,
normalized_product,confidence,retrieved_at,source_url,vertical
```

- `price_type` vocabolario: `per_service` (default), `per_length_short`, `per_length_medium`, `per_length_long`
- `vertical` = **`barber`**
- `currency` = `EUR`

---

## SORGENTI — PRIORITY ORDER

### ⭐ PRIORITÀ 1: TREATWELL (attacca subito)

**Perché Treatwell è il target ottimale:**
- SSR completo → `requests.get()` funziona, zero Playwright
- Sitemap XML disponibile → discovery passiva di tutte le venue
- Prezzi nel HTML (lista servizi con tariffe visibili ad anon)
- JSON-LD structured data (nome, indirizzo, geo, rating)
- Anti-bot: Cloudflare base (facilmente bypassabile con headers standard)
- ~15.000-25.000 venue italiane stimate
- Categories esplicite (haircut_man, beard, color…)

**Discovery via sitemap:**

```python
import requests
from bs4 import BeautifulSoup

# Sitemap index
r = requests.get('https://www.treatwell.it/sitemap.xml',
    headers={'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) '
             'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36'},
    timeout=30)
soup = BeautifulSoup(r.text, 'lxml-xml')
sitemaps = [loc.text for loc in soup.find_all('loc')]
print(sitemaps)  # cerca sitemaps con "saloni" o "venues"
```

**Estrai venue URL dalla sitemap venue:**
```python
# es: https://www.treatwell.it/sitemap-venues-it.xml
venue_urls = [loc.text for loc in soup.find_all('loc')
              if '/salone/' in loc.text or '/barber/' in loc.text]
```

**Struttura pagina venue Treatwell** (pattern atteso):
- JSON-LD `@type: "LocalBusiness"` → nome, address, geo, rating
- Sezione "Servizi" → lista `<div class="service-...">` con nome + prezzo
- `<div class="rating">` + review count
- URL pattern: `https://www.treatwell.it/salone/{slug}/`

**Estrazione prezzi:**
```python
import re, json
from bs4 import BeautifulSoup

def extract_treatwell_venue(url, session):
    r = session.get(url, timeout=20)
    soup = BeautifulSoup(r.text, 'lxml')

    # JSON-LD metadata
    ld = soup.find('script', type='application/ld+json')
    meta = json.loads(ld.string) if ld else {}

    # Venue base
    venue = {
        'source_platform': 'treatwell',
        'venue_url': url,
        'venue_name': meta.get('name', ''),
        'address': meta.get('address', {}).get('streetAddress', ''),
        'city': meta.get('address', {}).get('addressLocality', ''),
        'latitude': meta.get('geo', {}).get('latitude', ''),
        'longitude': meta.get('geo', {}).get('longitude', ''),
        'rating': meta.get('aggregateRating', {}).get('ratingValue', ''),
        'rating_count': meta.get('aggregateRating', {}).get('reviewCount', ''),
        'booking_provider': 'treatwell',
        'vertical': 'barber',
    }

    # Prezzi servizi (ispeziona DOM reale per class names)
    items = []
    for svc in soup.select('[data-service-id], .service-item, [class*="service"]'):
        name_el = svc.select_one('[class*="name"], h3, h4')
        price_el = svc.select_one('[class*="price"], [class*="amount"]')
        if name_el and price_el:
            raw_price = price_el.get_text(strip=True)
            price_match = re.search(r'(\d+[,.]?\d*)', raw_price.replace(',', '.'))
            items.append({
                'item_name': name_el.get_text(strip=True),
                'raw_price': raw_price,
                'normalized_price_eur': float(price_match.group(1)) if price_match else 0,
                'vertical': 'barber',
                'source_platform': 'treatwell',
                'venue_url': url,
            })
    return venue, items
```

> **SMOKE TEST OBBLIGATORIO** (prime 10 venue di Milano): verifica che nome/geo/prezzi
> vengano estratti correttamente PRIMA di scalare a migliaia.

---

### ⭐ PRIORITÀ 2: UALA.IT

**Caratteristiche:**
- ~8.000-12.000 venue italiane
- Next.js SSR/ISR — la maggior parte delle pagine venue è SSR
- URL pattern: `https://uala.it/saloni/{slug}` o `/barbers/{slug}`
- Sitemap: da verificare con `robots.txt`
- Prezzi: visibili nel HTML (lista trattamenti con tariffe)
- Anti-bot: leggero, headers standard sufficienti

**Discovery:**
```python
r = requests.get('https://uala.it/robots.txt', timeout=10)
# Cerca Sitemap: righe
# Poi: curl https://uala.it/sitemap.xml
```

---

### PRIORITÀ 3: FRESHA

**Caratteristiche:**
- ~5.000-8.000 venue italiane
- Sitemap: `https://www.fresha.com/sitemap.xml`
- SSR parziale (Next.js) — dati principali in HTML, ma listing a volte via XHR
- Prezzi: in parte nel HTML (service cards), in parte via GraphQL interno
- Anti-bot: Medium (Cloudflare) — richiede headers curati o `curl_cffi safari17`
- URL pattern: `https://www.fresha.com/a/{slug}`

---

### PRIORITÀ 4: BOOKSY

**Caratteristiche:**
- ~10.000-15.000 venue italiane (forte su barber)
- Next.js SPA — HTML parziale, dati principali via API XHR
- Prezzi: **dietro login** (no anon access) → basso ROI per price extraction
- Utile solo per venue discovery (nome, indirizzo, geo, rating)
- Anti-bot: Medium

---

### FALLBACK: OSM (coverage gap)

OSM per barbieri: `amenity=hairdresser` → ~30.000-50.000 result Italia, molto noisy.
**Usa SOLO come fallback geografico** per aree non coperte da aggregatori.

```python
query = """
[out:json][timeout:300];
area["ISO3166-1"="IT"]->.italy;
(
  node["amenity"="hairdresser"](area.italy);
  node["shop"="hairdresser"](area.italy);
  node["amenity"="hairdresser"]["name"~"barber|barbier",i](area.italy);
);
out center tags;
"""
```

**Filtro obbligatorio**: mantieni SOLO venue con `name` non vuoto + `name` non generico
("Parrucchiere", "Barbiere", "Hairdresser" da soli → scarta).

---

## WORKFLOW S1

### Phase 1 — Discovery via Treatwell sitemap (≥ 5.000 venue)

1. Fetch `treatwell.it/sitemap.xml` → trova sitemap venue
2. Fetch sitemap venue → lista URL `/salone/*`
3. Filtra per `city` o URL slug con città italiane principali
4. Per ogni URL: estrai venue metadata (JSON-LD + DOM)
5. Salva in `raw_sources/barber_s1_treatwell_venues.csv`

### Phase 2 — Sample price extraction (≥ 200 venue con prezzi)

Dalla lista venue Treatwell, prioritizza Milano (≥ 200 venue):
1. Smoke test prime 10 venue → verifica schema
2. Se smoke OK → scala a 200 venue Milano
3. Per ogni venue: estrai servizi + prezzi
4. Valida con `validate_barber_item()` prima di scrivere
5. Salva in `raw_sources/barber_s1_menu_items.csv`

### Phase 3 — Provider mapping report

Per ogni provider (Treatwell, Uala, Fresha, Booksy):
1. Conta venue totali Italia (stima da sitemap)
2. Verifica se prezzi sono anon-accessibili
3. Valuta anti-bot resistance
4. Compila `barber_s1_PROVIDERS.md`

### Phase 4 — Uala discovery (se tempo)

Replica Phase 1 su Uala → aggiunge `raw_sources/barber_s1_uala_venues.csv`

### Phase 5 — Dedup + merge parziale

```python
# Match geo ≤50m o nome similarity >0.85 + stessa città
# Produce barber_s1_master_venues.csv (deduplicato)
```

---

## FRONTEND — 3° VERTICAL (HEXAGONAL MARKERS)

Aggiungi toggle barbieri nell'`index.html` **senza toccare drink né beach**.

**Marker visual**: esagonale (CSS clip-path) — distinto da:
- Drink: rectangular pill
- Beach: circle

```css
/* Marker barber — hexagonal */
.pm.pm-barber {
  width: 54px;
  height: 44px;
  clip-path: polygon(25% 0%, 75% 0%, 100% 50%, 75% 100%, 25% 100%, 0% 50%);
  background: #3d2b8a;  /* viola profondo — barber brand color */
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  font-size: 11px;
  font-weight: 600;
  cursor: pointer;
  transition: transform 0.15s;
}
.pm.pm-barber:hover  { transform: scale(1.12); z-index: 100; }
.pm.pm-barber.sel    { transform: scale(1.20); z-index: 200; }

/* Colori pricing */
.pm.pm-barber.deal { background: #1e6639; }
.pm.pm-barber.avg  { background: #7a5a00; }
.pm.pm-barber.exp  { background: #8b1a1a; }
```

**Toggle sidebar** — aggiungi chip "Barbieri" accanto a "Drink" e "Spiagge".
Il toggle mostra/nasconde il layer barber sulla mappa (stesso pattern beach).

**Data feed**: `barber_data.json` (struttura identica a `prices_data.json` ma con
servizi barber come primo livello: `haircut_man`, `haircut_woman`, `beard_trim`, etc.)

> **S1 = data only**. Il frontend toggle è opzionale in S1 — priorità ai dati.
> Se il tempo stringe, salta il frontend e consegna solo i CSV. Il CEO farà il merge.

---

## QUALITY GATES (NON NEGOZIABILI)

**Per ogni VENUE:**
1. `latitude` + `longitude` presenti OPPURE `address` + `city` completo
2. `venue_name` non è titolo HTML generico ("Salone", "Prenota", "Home")
3. `barber_category` è in `{'barber', 'salon_donna', 'unisex', 'kids'}` o vuoto
4. `vertical = "barber"` sempre
5. `city` popolato (no venue senza città)

**Per ogni ITEM:**
1. `validate_barber_item(item)` deve ritornare `True`
2. `normalized_product` in `BARBER_PRODUCTS` o vuoto (mai codici inventati)
3. `normalized_price_eur` > 0 (scarta items senza prezzo)
4. `item_name` < 200 caratteri
5. `confidence`: `high` solo da sorgente strutturata (JSON-LD/API) — altrimenti `medium`
6. NO duplicati (stesso venue + product + price → dedup inline)

---

## RATE LIMITS

| Target | Delay | Note |
|---|---|---|
| Treatwell | 1.5s tra GET | CF base — headers standard ok |
| Uala | 2s tra GET | Next.js, leggero |
| Fresha | 3s tra GET | CF più aggressivo |
| OSM Overpass | unica query bulk | timeout=300 |
| HTTP 429 | sleep 120s + retry | massimo 2 retry |
| HTTP 403 | skip URL | logga, non ritentare |

---

## DELIVERABLES S1

| File | Descrizione | Target |
|---|---|---|
| `raw_sources/barber_s1_treatwell_venues.csv` | Venue Treatwell Italia | ≥ 5.000 righe |
| `raw_sources/barber_s1_menu_items.csv` | Prezzi servizi (sample Milano) | ≥ 200 venue prezzate |
| `raw_sources/barber_s1_uala_venues.csv` | Venue Uala (se tempo) | ≥ 1.000 righe |
| `barber_s1_PROVIDERS.md` | Report provider comparativo | 4+ provider |
| `barber_s1_REPORT.md` | Metriche S1, gaps, prossimi step | obbligatorio |

---

## CONSEGNA

```bash
git pull --rebase origin main
git add raw_sources/barber_s1_*.csv
git add barber_s1_*.md
git commit -m "data: barber S1 — N venues Treatwell, M items prezzati, K provider mappati"
git push origin main
```

Avvisa CEO con metriche: venue totali, venues prezzate, città coperte, provider identificati.

---

## COSA NON FARE IN S1

- ❌ Non scrape Google Maps (anti-bot invalicabile, basso ROI per prezzi)
- ❌ Non fare web-wide discovery (partiamo dagli aggregatori, non dal web aperto)
- ❌ Non estrarre prezzi da TUTTE le venue (sample 200 Milano è sufficiente per S1)
- ❌ Non toccare i file drink/beach (`prices_data.json`, `beach_data.json`, `data/unified_*.csv`)
- ❌ Non finalizzare frontend se i dati non sono ancora solidi

---

## LESSON LEARNED DALLE SESSIONI PRECEDENTI

1. **SSR first**: se la pagina è SSR, requests.get() batte Playwright di 70x (lezione beach Phase 3)
2. **Smoke test on 10 venues PRIMA di scalare**: eviti di raccogliere migliaia di righe malformate
3. **Importa normalization.py**: non reinventare la quality gate — è già scritta
4. **City filter nazionale**: non c'è un CAP unico come Milano — usa `city` + `region` come filter/tag
5. **Never overwrite raw**: tieni `raw_price` originale + `normalized_price_eur` calcolato
6. **Confidence rigorosa**: `high` solo da JSON-LD/API strutturata, `medium` da parsing HTML

---

Buona sessione Peppe. **High-signal > high-volume in S1.**
