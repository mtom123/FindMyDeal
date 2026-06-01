# Prompt Peppe — Beach Club Price Intelligence S2

> **CONTEXT**: S1 chiusa con 9.252 venue OSM + 27 venue prezzate (validazione schema ok).
> S2 = scale-up: da 27 → 500+ venue con prezzi reali, e da 568 → 2.500+ venue con website.
> Vedi commit b31f4a7 e beach_s1_REPORT.md per il punto di partenza.

---

## OBIETTIVI MISURABILI S2

| Metrica | Target S2 |
|---|---|
| Venue con city/province/region popolata | ≥ 8.000 (reverse geocoding) |
| Venue con website associato | ≥ 2.500 (enrichment da spiagge.it + Maps) |
| Venue con booking_provider mappato | ≥ 1.500 |
| Venue con prezzi estratti | ≥ 500 |
| Price items totali | ≥ 3.000 |
| Copertura regionale: ogni regione costiera | ≥ 20 venue prezzate |
| Sud Italia (CAM/CAL/SIC/PUG): venue prezzate | ≥ 100 (era 2 in S1) |

---

## INPUT DA S1 (già in repo)

- `raw_sources/beach_s1_venues.csv` — 9.252 venue, USA QUESTO COME BASE
- `raw_sources/beach_s1_menu_items.csv` — 214 items già validati
- `beach_s1_PROVIDERS.md` — 8 provider con priorità di scraping
- `scripts/beach_s1_osm.py` — non rilanciare, OSM già coperto

NON rifare la query Overpass. NON re-scaricare i venue OSM.

---

## OUTPUT S2

```
raw_sources/
├── beach_s2_venues_enriched.csv      # 9.252 righe, ARRICCHITE (geocoding + website + provider)
├── beach_s2_consortium_menu_items.csv # da bibione/lignano consortia (target: ~80 venue)
├── beach_s2_summerbooking_menu_items.csv # da summerbooking.it (target: ~150 venue)
├── beach_s2_spiagge_menu_items.csv   # da spiagge.it via Playwright (target: ~200 venue)
├── beach_s2_pdf_menu_items.csv       # da PDF dorks (target: ~80 venue)
└── beach_s2_direct_menu_items.csv    # siti propri /tariffe /listino (target: ~50 venue)

beach_s2_REPORT.md                     # metriche, gap, raccomandazioni S3
beach_s2_PROVIDERS_UPDATE.md           # aggiornamento mappa provider con dati reali raccolti
```

---

## PHASE 1 — ENRICHMENT MASTER LIST (priorità: 1)

### Step 1.1 — Reverse geocoding (Nominatim)

Per ogni venue senza `city`/`province`/`region` (~8.400 venue):

```python
import requests, time

NOMINATIM = "https://nominatim.openstreetmap.org/reverse"
HEADERS = {"User-Agent": "SurPrice-Geocoding/1.0 (research@surprice.it)"}

def reverse_geocode(lat, lon):
    r = requests.get(NOMINATIM, params={
        "lat": lat, "lon": lon, "format": "json",
        "addressdetails": 1, "zoom": 14, "accept-language": "it",
    }, headers=HEADERS, timeout=30)
    if r.status_code == 200:
        addr = r.json().get("address", {})
        return {
            "city": addr.get("city") or addr.get("town") or addr.get("village", ""),
            "province": addr.get("county", ""),
            "region": addr.get("state", ""),
            "postal_code": addr.get("postcode", ""),
        }
    return None
```

**Rate limit Nominatim: 1 req/sec MASSIMO** (TOS). Per 8.400 venue → ~2,5 ore.
Usa cache su disco (`geocode_cache.json`) per non rifare query in caso di crash.

### Step 1.2 — Website enrichment via spiagge.it discovery

Scarica le pagine listing comune di spiagge.it per ogni città costiera identificata in Step 1.1:

```python
# Pattern: https://www.spiagge.it/stabilimenti-balneari/{comune-slug}/
# Estrai per ogni venue: nome, link spiagge.it, website esterno (se presente)
# Match contro master list per coordinate (≤300m) o name similarity (>0.85)
# Aggiorna campo `website` e `booking_provider="spiagge.it"` quando match
```

Lista comuni costieri da iterare: estrai da Step 1.1 tutti i comuni unici con ≥3 venue.

Rate: 2s tra request a spiagge.it. Max 500 query/sessione, poi pausa.

### Step 1.3 — Provider mapping per venue con website

Per ogni venue con `website` popolato (~2.500 attesi dopo Step 1.2):
1. Fetch homepage
2. Cerca link "Prenota"/"Booking"/"Riserva"
3. Estrai dominio destinazione → match contro lista 8 provider
4. Popola `booking_provider`

Rate: 2s tra GET. Skip 403/429.

---

## PHASE 2 — CONSORZI REGIONALI (priorità: 2 — alta confidenza)

### Step 2.1 — Bibione Mare

URL listing: `https://stabilimenti.bibionemare.com/it/`
Ogni venue ha pagina prezzi statica. Estrai sistematicamente.

### Step 2.2 — Lignano consortium

URL: `https://www.lignano-riviera.it/prenotazioni/` + siti uffici spiaggia (es. `spiaggia14e15.it`, `laspiaggiadiduke.com`).
Pattern: ogni "ufficio spiaggia" numerato (1-15) ha sito proprio o pagina dedicata.

### Step 2.3 — Bagni Rimini Cooperativa (verifica esistenza)

Cooperativa Bagnini Riviera Romagnola: cercare API/listing centralizzato per Rimini/Riccione/Cesenatico.

### Step 2.4 — Grado / Caorle / Jesolo

Check se hanno consorzi simili. Search: `site:*.it stabilimenti balneari Grado listino`.

**Stima output Phase 2: 60-100 venue prezzate, alta confidenza.**

---

## PHASE 3 — SUMMER BOOKING (priorità: 2)

URL pattern scoperto in S1:
```
https://summerbooking.it/it/spiagge/{slug}/prezzi-ombrellone-lettino-sdraio
```

### Step 3.1 — Discovery slug list

Sitemap probabilmente esposta: `https://summerbooking.it/sitemap.xml`. Verifica.
Fallback: Google dork `site:summerbooking.it /prezzi-ombrellone-lettino-sdraio`.

### Step 3.2 — Extraction

Per ogni slug → fetch pagina prezzi → parse tabella.
Rate: 2s tra GET.

**Stima output: 100-300 venue.**

---

## PHASE 4 — SPIAGGE.IT con Playwright (priorità: 3 — alto volume, alto sforzo)

Spiagge.it espone prezzi solo dopo selezione date. Usa Playwright headless.

### Setup

```python
from playwright.async_api import async_playwright

async def get_prices(venue_url, check_in, check_out):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto(venue_url)
        # Compila form date
        await page.fill('input[name="checkin"]', check_in)
        await page.fill('input[name="checkout"]', check_out)
        await page.click('button.search-availability')
        await page.wait_for_selector('.umbrella-price', timeout=15000)
        # Estrai tutti i prezzi visibili
        prices = await page.eval_on_selector_all('.umbrella-price',
            'els => els.map(e => ({row: e.dataset.row, price: e.textContent}))')
        await browser.close()
        return prices
```

### Strategia

- Date di riferimento: **1-7 agosto 2026** (peak season, comparabile con Altroconsumo benchmark)
- Anche **15-21 giugno 2026** (bassa stagione) per spread
- Pool venue: tutte quelle con `booking_provider="spiagge.it"` da Step 1.3

### Anti-rate-limit

- 10-15s tra venue (mimicry umano)
- Max 50 venue/sessione → poi rotate IP / pausa 30min
- Se ricevi captcha → STOP, segnala in REPORT, non bypassare

**Stima output: 150-300 venue, confidence high se prezzi visibili in DOM.**

---

## PHASE 5 — PDF DORKS SISTEMATICI (priorità: 3)

### Dork batch per regione

Per ogni regione costiera (14 totali), genera 5 query Startpage:

```
"listino" "stabilimento balneare" {regione} filetype:pdf 2026
"tariffe" "ombrellone" {regione} filetype:pdf
"prezzi" lido balneare {regione} pdf
"abbonamento stagionale" {regione} stabilimento pdf
site:*.it {regione} balneare listino 2026 pdf
```

70 query totali. Rate: 5s tra query, max 20 query consecutive, poi rotate Startpage → Mojeek.

### PDF parsing

Per ogni PDF scaricato:
```python
import pdfplumber

with pdfplumber.open(pdf_path) as pdf:
    text = ""
    for page in pdf.pages:
        text += page.extract_text() or ""
    # Bug noto S1: "LLEETTTTIINNOO" → applicare regex r"([A-Z])\1" → r"\1"
    text = re.sub(r"([A-Z])\1", r"\1", text)
```

Pattern estrazione prezzi: `€\s*(\d+(?:[,.]\d{2})?)` + match contestuale a parole-chiave (`ombrellone`, `lettino`, `cabina`, `stagionale`, `prima fila`).

Quality gate: prezzo €0-5.000, conferma con contesto testuale prima di scrivere.

**Stima output: 60-120 venue dai PDF.**

---

## PHASE 6 — DIRECT WEBSITE EXTRACTION (priorità: 4 — coda lunga)

Per ogni venue con `website` ma `booking_provider` vuoto (∼1.000 dopo Phase 1):

1. Fetch homepage
2. Cerca link a `/tariffe`, `/listino`, `/prezzi`, `/rates`, `/pricing`
3. Se trovato → fetch + parse con stessi pattern Phase 5
4. Se nessuna pagina prezzi → marca `extraction_status="no_pricing_page"` e skip

**Stima output: 30-80 venue.**

---

## QUALITY GATES S2 (uguali a S1, REGOLA #1)

Per ogni VENUE:
1. ✅ Geo coerente (region+province+city)
2. ✅ Nome ≠ titolo HTML page
3. ✅ Vertical = "beach"
4. ✅ Provenance (`source_platform`, `source_url`)

Per ogni ITEM:
1. ✅ `normalized_price_eur` parseable, 0 < p ≤ 5000
2. ✅ `normalized_product` da vocabolario chiuso (16 codici S1) o vuoto
3. ✅ `price_type` da vocabolario chiuso o vuoto
4. ✅ No URL immagine in `source_url`
5. ✅ `item_name` < 200 char
6. ✅ No duplicati interni: dedup su `(source_venue_id, normalized_product, raw_price, price_type)`
7. ✅ `season="summer_2026"`, `validity_start/end` compilati

**Confidence assignment**:
- PDF strutturato → `high`
- Tabella HTML pulita → `high`
- Regex su HTML messy → `medium`
- Best-effort da snippet → `low` (e meglio ancora: skip)

---

## ANTI-PATTERN DA EVITARE (lessons S1)

1. ❌ **Non inventare codici**. Se un prezzo non mappa nel vocabolario chiuso, `normalized_product=""` e basta. NON aggiungere codici nuovi senza approvazione CEO.
2. ❌ **Non fidarsi di OCR su PDF scansionati** senza verifica. Se text extraction è vuoto/casuale, marca `extraction_status="pdf_ocr_required"` e skip — rifaremo con OCR dedicato.
3. ❌ **Non confondere prezzo "da" con prezzo effettivo**. Se vedi "Ombrellone da €25", `confidence=low` o skip.
4. ❌ **Non sovrascrivere `beach_s1_*.csv`**. Output S2 va in file separati `beach_s2_*.csv`. Il merge li unirà.
5. ❌ **Non fare commit a batch giganti**. Commit per phase: dopo Phase 1, dopo Phase 2, ecc. Permette rollback chirurgico.
6. ❌ **Non usare User-Agent generico** (`python-requests/2.x`). Setta header esplicito `SurPrice-Research/1.0 (research@surprice.it)`.

---

## RATE LIMITS RIASSUNTI

| Servizio | Rate |
|---|---|
| Nominatim | 1 req/sec (TOS hard limit) |
| Spiagge.it homepage | 2s |
| Spiagge.it Playwright | 10-15s |
| Summer Booking | 2s |
| PDF download | 1s, max 200/sessione |
| Generic website | 2s |
| Startpage search | 5s, max 20 consecutive |
| HTTP 429 → sleep 120s + retry una volta sola |
| HTTP 403 → skip, marca `extraction_status="blocked"` |

---

## DELIVERY

```bash
cd /Users/g_giaimo02/Desktop/TTW/FindMyDeal
git pull --rebase origin main
git add raw_sources/beach_s2_*.csv beach_s2_*.md scripts/beach_s2_*.py
git commit -m "data: beach S2 — N venues enriched, M items, K providers mappati"
git push origin main
```

Avvisa CEO con report sintetico: scostamento vs target per ogni Phase, gap rimasti, raccomandazione per S3 (frontend integration).

---

## CHE COSA NON FARE IN S2

- ❌ Frontend / UI (è S3)
- ❌ Toccare file drink (data/, prices_data.json, index.html)
- ❌ Aggiungere codici al vocabolario `normalized_product` senza approvazione
- ❌ Re-scrappare OSM (già fatto S1)
- ❌ Scrappare TUTTI i venue (la coda lunga è S3+, S2 punta a 500 venue prezzate, non 9.000)

---

## BUDGET TEMPO STIMATO

| Phase | Ore stimate |
|---|---|
| Phase 1 (geocoding + website enrichment) | 4-6 |
| Phase 2 (consorzi) | 3-4 |
| Phase 3 (Summer Booking) | 2-3 |
| Phase 4 (Spiagge.it Playwright) | 6-8 |
| Phase 5 (PDF dorks) | 3-5 |
| Phase 6 (direct website coda lunga) | 2-3 |
| Reporting | 1 |
| **Totale** | **21-30 ore** |

Se i tempi stringono: Phase 1 + Phase 2 + Phase 5 sono il **MVP S2**. Phase 3-4-6 possono slittare a S2.5.

---

Buona caccia, Peppe.
**Volume matters more than depth in S2 — abbiamo già provato che lo schema regge.**
