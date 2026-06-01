# Prompt Peppe — Spiagge.it Mass Extraction (S2X)

> **CONTEXT**: dopo S2 sub-iter abbiamo 35 venue prezzati, ma spiagge.it ospita 1.000+ stabilimenti italiani con prezzi reali via widget booking. Questa è la **miniera principale**. S2X = sessione dedicata, Playwright-first, con consolidation finale verso il master S1+S2.
>
> **Vedi**: commit cc373dc, beach_s1_PROVIDERS.md sezione Spiagge.it, beach_s2_REPORT.md.

---

## OBIETTIVO MISURABILE S2X

| Metrica | Target |
|---|---|
| URL venue spiagge.it scoperti | ≥ 1.000 (di cui ≥ 800 con detail page accessibile) |
| Venue con metadati estratti (nome, indirizzo, lat/lon, website, telefono) | ≥ 800 |
| Venue con almeno 1 prezzo estratto (peak Aug o bassa Jun) | ≥ 400 |
| Price items totali (ombrellone × fila × periodo × data) | ≥ 5.000 |
| Match con master S1 venue per coord/name (`venue_id` linking) | ≥ 600 |
| Nuove venue NON in master S1 (da aggiungere) | ≥ 200 |
| Sud Italia (CAM/CAL/SIC/PUG): venue prezzati | ≥ 150 |
| Copertura: ogni regione costiera con ≥ 30 venue prezzati | sì |

**Punto onesto**: questi target dipendono dall'esito del smoke test (Phase B). Se Datadome blocca → numeri si dimezzano e serve fallback API discovery.

---

## INPUT DA REPO

- `raw_sources/beach_s1_venues.csv` (9.252 venue master, lat/lon completi)
- `raw_sources/beach_s2_venues_enriched.csv` (9.252 + città/regione parziale)
- `raw_sources/.geocode_cache.json` (cache geocoding, riusabile)
- `beach_s1_PROVIDERS.md` (8 provider, spiagge.it = priorità #1)

NON modificare i file S1/S2 esistenti. Output sempre in file separati `beach_s2x_*.csv`.

---

## OUTPUT S2X

```
raw_sources/
├── beach_s2x_spiagge_url_list.csv          # Phase A: discovery URL venue
├── beach_s2x_spiagge_venues.csv            # Phase C: metadati venue (nome, addr, geo)
├── beach_s2x_spiagge_menu_items.csv        # Phase D: prezzi estratti
└── beach_s2x_spiagge_consolidated_venues.csv # Phase E: master S1 + spiagge match/new

scripts/
├── beach_s2x_discover.py        # discovery via listing comune + sitemap
├── beach_s2x_metadata.py        # extraction metadati SSR (no Playwright)
├── beach_s2x_playwright.py      # extraction prezzi (Playwright)
└── beach_s2x_consolidate.py     # match con master + dedup + linking

beach_s2x_SMOKETEST.md           # verdetto GO/NO-GO
beach_s2x_REPORT.md              # metriche, scostamenti, raccomandazioni S3
```

---

## STRATEGIA — A CHE LIVELLO ATTACCARE

Spiagge.it è strutturato a 3 layer:

| Layer | Tecnologia | Scraping difficulty |
|---|---|---|
| **L1 — Listing comune** `/stabilimenti-balneari/{comune}/` | SSR (HTML completo) | BASSA — requests + BS4 ok |
| **L2 — Venue detail** `/stabilimenti-balneari/{id}-{slug}/` | SSR per metadati, JS widget per prezzi | MEDIA — metadati con requests, prezzi con Playwright |
| **L3 — Widget booking prezzi** | iframe `widget.spiagge.it` con form date | ALTA — Playwright + date selector + DOM extraction |

**Decisione architetturale**: separa L1+L2 (no Playwright) da L3 (Playwright only). Massimizza yield prima di esporsi all'anti-bot.

---

## PHASE A — URL DISCOVERY (no Playwright) — priorità: 0

### Step A.1 — Sitemap.xml

```bash
curl -A "SurPrice-Research/1.0" https://www.spiagge.it/sitemap.xml > /tmp/spiagge_sitemap.xml
# Se è sitemap index: ricorri sui sub-sitemap
# Cerca pattern /stabilimenti-balneari/{id}-{slug}/
```

Yield atteso: 1.000-2.000 URL venue.

### Step A.2 — Listing comune (fallback se sitemap incompleta)

Per ogni comune italiano costiero (lista da `beach_s2_venues_enriched.csv` con region in {Liguria, Toscana, Lazio, Campania, Calabria, Sicilia, Puglia, Marche, Abruzzo, Molise, Emilia-Romagna, Veneto, Friuli-Venezia Giulia, Sardegna, Basilicata}):

```python
url = f"https://www.spiagge.it/stabilimenti-balneari/{slugify(comune)}/"
# Fetch HTML, estrai tutti i link `/stabilimenti-balneari/\d+-`
```

Lista comuni costieri stimata: 300-500.
Rate: 2s tra fetch. Max 50 query consecutive → pausa 30s.

### Step A.3 — Pagine regionali aggregator

```
https://www.spiagge.it/stabilimenti-balneari/{regione-slug}/
es: https://www.spiagge.it/stabilimenti-balneari/emilia-romagna/
```

14 regioni costiere → 14 fetch.

### Output Phase A

`beach_s2x_spiagge_url_list.csv`:
```
spiagge_venue_id,spiagge_url,slug,comune_listing,discovered_at
25013,https://www.spiagge.it/stabilimenti-balneari/25013-bagno-libra-63-63a-63b-64-65/,bagno-libra-63,rimini,2026-06-02T...
```

Dedup per `spiagge_venue_id` (l'ID numerico nell'URL).

**Target Phase A**: ≥ 1.000 URL unici.

---

## PHASE B — SMOKE TEST PLAYWRIGHT (GATE OBBLIGATORIO)

> NON procedere a Phase D senza Phase B verde.

### Setup

```bash
pip3 install playwright playwright-stealth
playwright install chromium
```

### Test su 5 venue (mix province)

Pesca 5 venue dalla `url_list` di Phase A — uno per regione (RN, LU, LE, PA, SS).

Esegui in `headless=False` per debug visivo:

```python
from playwright.async_api import async_playwright
from playwright_stealth import stealth_async

async def smoke_one(url):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)  # VISIBILE
        ctx = await browser.new_context(
            viewport={"width": 1366, "height": 768},
            locale="it-IT",
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
        )
        page = await ctx.new_page()
        await stealth_async(page)
        await page.goto(url, wait_until="networkidle", timeout=30000)
        # Screenshot per debug
        await page.screenshot(path=f"smoke_{url.split('/')[-2]}.png", full_page=True)
        # Verifica check list (sotto)
        ...
```

### Check list smoke test (compila tabella in `beach_s2x_SMOKETEST.md`)

| Check | Cosa verificare | Verdetto venue X | Decisione |
|---|---|---|---|
| WAF / Datadome | Header `x-datadome-cid`, JS challenge, redirect a captcha-delivery.com | OK / KO | KO → usare playwright-stealth + undetected-chromium + residential proxy |
| HTTP status iniziale | 200 OK? 403? 503? | | KO → vedi WAF |
| DOM widget selector | Trova selettore CSS per prezzi (ispeziona DevTools): es. `.umbrella-price`, `[data-price]`, `.tariff-cell` | Stabile / Cambia | Cambia → estrai via JSON-LD o XHR sniffing |
| Date input reactivity | Inserisci date `2026-08-01` → `2026-08-07`, click submit, prezzi cambiano vs default? | SI / NO | NO → backend potrebbe esporre JSON API, ispeziona Network |
| Captcha trigger | Dopo 5 venue consecutivi (10s pause), appare reCAPTCHA / hCaptcha? | NO / SI | SI → captcha solver (€) o rotate IP / cookie clearing |
| Rate-limit silenzioso | Stesso prezzo cached / `503` su tutto dopo N call? | OK / KO | KO → pause 5min + rotate user agent |
| iframe widget.spiagge.it | I prezzi sono in iframe? | SI / NO | SI → `page.frame_locator` con switch context |

### Verdetto

- **5/5 OK** → GO Phase D, schedule scaling
- **3-4/5 OK** → GO Phase D ma con limiti (no notturno, max 50 venue/sessione, monitor strict)
- **0-2/5 OK** → NO-GO. Output `beach_s2x_SMOKETEST.md` con verdetto + screenshot evidence + raccomandazione fallback (es. partnership API request a spiagge.it, oppure attesa S3 con stack diverso)

### Tempo Phase B: 45-60 minuti.

---

## PHASE C — METADATI SSR EXTRACTION (no Playwright)

Mentre Phase B gira, attacca Phase C in parallelo: metadati venue. Spiagge.it venue detail page è SSR per quasi tutto tranne prezzi → BS4 basta.

### Per ogni URL in `beach_s2x_spiagge_url_list.csv`:

```python
import requests
from bs4 import BeautifulSoup

html = requests.get(url, headers={"User-Agent": "SurPrice-Research/1.0"}, timeout=20).text
soup = BeautifulSoup(html, "lxml")

# Estrai metadati dal JSON-LD <script type="application/ld+json"> se presente
# Fallback: parsing diretto del DOM
metadata = {
    "spiagge_venue_id": url.split("/")[-2].split("-")[0],
    "venue_name": soup.find("h1").get_text(strip=True),
    "address": soup.find("[itemprop=address]")?.get_text(strip=True),
    "phone": soup.find("a[href^=tel]")?.get("href").replace("tel:", ""),
    "website": soup.find("a[rel=external]")?.get("href"),  # link "Sito" esterno
    "latitude": ...,  # cerca data-lat, meta geo.position
    "longitude": ...,
    "amenities": [...],  # checkbox/icone servizi
    "umbrella_count": ...,  # spesso dichiarato in metadati
    "sqm": ...,  # dimensione spiaggia
    "season_dates": ...,  # apertura-chiusura
}
```

Rate: 2s tra fetch. Output: `beach_s2x_spiagge_venues.csv`.

**Target Phase C**: ≥ 800 venue con metadata complete (name + address + geo).

---

## PHASE D — PREZZI VIA PLAYWRIGHT (gated by Phase B)

### Strategia date

Due date di reference per ogni venue (compromesso copertura/costo):

| Slot | Date | Significato |
|---|---|---|
| **PEAK** | 2026-08-01 → 2026-08-07 | Alta stagione, settimana 1 agosto (benchmark Altroconsumo) |
| **MID** | 2026-06-15 → 2026-06-21 | Bassa stagione, spread per comparazione |

Per ogni venue: 2 fetch (uno per slot). Totale: ~1.600 fetch su 800 venue.

### Extraction logic

```python
async def extract_prices(url, check_in, check_out):
    page = await new_page()
    await page.goto(url, wait_until="networkidle")
    
    # 1. Compila form date
    await page.click("input.date-checkin")
    await page.fill("input.date-checkin", check_in)
    await page.fill("input.date-checkout", check_out)
    await page.click("button.search-availability")
    
    # 2. Attendi rendering prezzi
    try:
        await page.wait_for_selector(".umbrella-grid .price-cell", timeout=20000)
    except TimeoutError:
        return {"status": "no_prices_rendered", "url": url}
    
    # 3. Estrai tutti i prezzi visibili
    prices = await page.evaluate("""
        () => Array.from(document.querySelectorAll('.umbrella-grid .price-cell')).map(el => ({
            row: el.dataset.row || el.closest('[data-row]')?.dataset.row,
            position: el.dataset.position,
            price: el.textContent.trim(),
            type: el.dataset.type,  // ombrellone / lettino / cabina
        }))
    """)
    
    return {"status": "ok", "prices": prices, "check_in": check_in, "check_out": check_out}
```

**N.B.**: i selettori sopra sono indicativi. Aggiusta dopo Phase B sulla base del DOM reale.

### Rate / pacing

- 10-15s tra venue (mimicry umano)
- Max 50 venue per browser session → chiudi + ri-apri (cookie reset)
- Max 200 venue/giorno per IP → se rate-limit silenzioso, pause 4h + rotate
- Salva incrementale ogni 10 venue (resume su crash)
- HTTP 429 / captcha → STOP, save partial, segnala

### Output Phase D

`beach_s2x_spiagge_menu_items.csv` — stesso schema beach_s2x con campi extra:
- `peak_or_mid` (string: "peak_aug" / "mid_jun")
- `check_in_date`, `check_out_date` (ISO date)
- `umbrella_row` (1/2/3/...)
- `umbrella_position` (es. "12A" se mappato)

Mapping a `normalized_product` (vocabolario S1):
- "Ombrellone + 2 lettini" + row=1 → `beach_umbrella_first_row` (NO! è set, vedi sotto)
- "Ombrellone + 2 lettini" qualsiasi fila → `beach_set_2lettini_ombrellone`
- Solo ombrellone → `beach_umbrella_first_row` (se row=1) / `beach_umbrella_standard`
- Cabina → `beach_cabin_day`
- Abbonamento settimana → `beach_subscription_week`

Mapping a `price_type`:
- Settimana check_in/out 7 giorni → `per_week`
- Singolo giorno → `per_day`
- Pomeridiano → `per_half_day`

Se ambiguo → vuoto + `confidence=medium`.

**Target Phase D**: ≥ 400 venue con almeno 1 prezzo, ≥ 5.000 items totali.

---

## PHASE E — CONSOLIDATION CON MASTER S1+S2

### Step E.1 — Match per coordinate

Per ogni venue in `beach_s2x_spiagge_venues.csv`:

```python
from math import radians, cos, sin, asin, sqrt

def haversine_m(lat1, lon1, lat2, lon2):
    R = 6371000
    dlat = radians(lat2-lat1); dlon = radians(lon2-lon1)
    a = sin(dlat/2)**2 + cos(radians(lat1))*cos(radians(lat2))*sin(dlon/2)**2
    return 2*R*asin(sqrt(a))

# Per ogni venue spiagge: trova venue master entro 300m
for sp in spiagge_venues:
    for master in master_venues:
        if haversine_m(sp.lat, sp.lon, master.lat, master.lon) < 300:
            # Match! Linka via spiagge_venue_id → master source_venue_id
            sp.master_id = master.source_venue_id
            sp.match_type = "geo_300m"
            break
```

### Step E.2 — Fallback match per nome+città

Se no geo match, prova:
```python
from difflib import SequenceMatcher
def name_sim(a, b):
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()

# Match se nome similarity > 0.85 AND stesso comune
```

### Step E.3 — Output consolidato

`beach_s2x_spiagge_consolidated_venues.csv` — struttura:

```
source_venue_id,master_source_venue_id,match_type,spiagge_venue_id,
spiagge_url,venue_name,address,city,province,region,latitude,longitude,
website,phone,booking_provider,vertical,...
```

Dove:
- `source_venue_id` = `spiagge_{spiagge_venue_id}` (nuovo namespace)
- `master_source_venue_id` = link al master S1 se match
- `match_type` ∈ {`geo_300m`, `name_city`, `no_match`}
- `booking_provider` = `spiagge.it` (sempre)

### Step E.4 — Aggiorna master (NO sovrascrittura)

NON modificare `beach_s1_venues.csv`. Invece:

```
raw_sources/
├── beach_s2x_master_updates.csv   # diff da applicare: source_venue_id, field, old_value, new_value
```

Il CEO valuterà se applicare il diff al master in S3.

Campi che il diff può aggiornare:
- `booking_provider` (se era vuoto → spiagge.it)
- `website` (se mancante → da spiagge)
- `phone` (se mancante → da spiagge)
- `address` (se mancante → da spiagge)

**MAI sovrascrivere** un campo già popolato in S1.

**Target Phase E**: ≥ 600 venue spiagge.it matchati al master, ≥ 200 nuovi venue non in master.

---

## QUALITY GATES S2X

Per ogni VENUE (file `beach_s2x_spiagge_venues.csv`):
1. ✅ `spiagge_venue_id` numerico univoco
2. ✅ `venue_name` non vuoto e ≠ "Stabilimento balneare" generico
3. ✅ `latitude`/`longitude` plausibili (in IT bounding box: 35.5-47.5 lat, 6.5-19 lon)
4. ✅ `booking_provider = "spiagge.it"`
5. ✅ `vertical = "beach"`

Per ogni ITEM (file `beach_s2x_spiagge_menu_items.csv`):
1. ✅ `normalized_price_eur` parseable, 0 < p ≤ 6500 (alziamo cap perché C.A.P.LI. dimostra €6.400 esiste)
2. ✅ `normalized_product` da vocabolario chiuso S1 o vuoto
3. ✅ `price_type` da vocabolario chiuso o vuoto
4. ✅ `peak_or_mid` ∈ {"peak_aug", "mid_jun"}
5. ✅ `check_in_date` e `check_out_date` validi ISO
6. ✅ Dedup su `(spiagge_venue_id, normalized_product, raw_price, price_type, peak_or_mid, umbrella_row)`
7. ✅ `vertical = "beach"`, `season = "summer_2026"`
8. ✅ `confidence`: `high` solo se DOM stabile + prezzo esplicito; `medium` se inferito; `low` se ambiguo

---

## ANTI-BOT STRATEGY

### Tier 1 — Standard (prova prima)
- `playwright-stealth` per fingerprint masking
- User-Agent rotation (3 UA pool: Safari Mac, Chrome Mac, Chrome Linux)
- Viewport randomizzato (1280x720, 1366x768, 1920x1080)
- Cookie reset ogni 50 venue
- Mouse movements random (`page.mouse.move(...)` jitter)
- Delay tra azioni 0.5-2s random

### Tier 2 — Se Tier 1 KO
- `undetected-chromedriver` invece di chromium standard
- Residential proxy rotation (Bright Data / Oxylabs, ~€10/GB)
- Captcha solver (2captcha, ~€2/1000)

### Tier 3 — Ultima risorsa
- Manual scraping mode: apri venue manualmente in browser reale, copia-incolla prezzi in CSV. Yield basso ma 100% success.
- Outreach a spiagge.it per partnership data feed (probabilmente €€€).

**Documenta in REPORT quale tier hai usato** e con che success rate.

---

## RATE LIMITS

| Operation | Rate | Max consecutive | Pause after max |
|---|---|---|---|
| Sitemap fetch | 1s | 1 | n/a |
| Listing comune (Phase A) | 2s | 50 | 30s |
| Metadata SSR (Phase C) | 2s | 100 | 60s |
| Playwright venue (Phase D) | 10-15s | 50 | Chiudi browser + 5min |
| 429 / captcha | STOP, save partial | n/a | Resume non prima di 4h |
| 403 generico | Skip venue + log | n/a | n/a |

---

## LEGAL / TOS NOTE

Spiagge.it ToS (verifica al momento dell'esecuzione) potrebbero vietare scraping automatizzato. **Mitigation**:

1. User-Agent identificativo con contact email (`SurPrice-Research/1.0 (research@surprice.it)`) — no anonimato
2. Rate-limit conservativi (10-15s tra fetch è human-like)
3. Solo dati pubblicamente visibili (no bypass auth, no API auth)
4. Dataset solo per uso interno SurPrice + reporting aggregato (no resale, no esposizione 1:1)
5. Honor robots.txt: fetch `https://www.spiagge.it/robots.txt` PRIMA di Phase A. Se `Disallow: /stabilimenti-balneari/` → STOP, segnala al CEO per legal review.

Se fra 6 mesi spiagge.it manda cease-and-desist: data è già acquisita, future updates via partnership.

**Tu non sei l'avvocato**: documenta cosa fai, il CEO decide.

---

## BUDGET ORARIO

| Phase | Ore stimate | Note |
|---|---|---|
| Phase A — Discovery URL | 1-2 | sitemap.xml + 14 listing regionali + 300 comuni costieri |
| Phase B — Smoke test | 0.75-1 | gate obbligatorio |
| Phase C — Metadati SSR | 4-6 | 1.000 venue × 2s + buffer |
| Phase D — Prezzi Playwright | 12-20 | 800 venue × 2 date × 12s = ~5h pure + retry/captcha buffer |
| Phase E — Consolidation | 2-3 | match algorithm + dedup + diff master |
| Reporting + smoke doc | 1-2 | |
| **Totale (se smoke OK)** | **21-34 ore** | |
| **Solo MVP (no Phase D)** | **8-13 ore** | sblocca discovery + metadati, prezzi rinviati |

Se smoke KO: chiudi a 8h con report fallback + plan S2.6 alternative.

---

## DELIVERY

Commit per phase (no batch unico):

```bash
cd /Users/g_giaimo02/Desktop/TTW/FindMyDeal
git pull --rebase origin main

# Dopo Phase A
git add raw_sources/beach_s2x_spiagge_url_list.csv scripts/beach_s2x_discover.py
git commit -m "data: spiagge S2X Phase A — N URL discovered"
git push origin main

# Dopo Phase B
git add beach_s2x_SMOKETEST.md
git commit -m "docs: spiagge S2X smoke test — verdetto GO/NO-GO"
git push origin main

# ... etc per Phase C, D, E

# Finale
git add beach_s2x_REPORT.md
git commit -m "data: spiagge S2X completo — N venue, M items, K match master"
git push origin main
```

---

## CHE COSA NON FARE IN S2X

- ❌ Lanciare Playwright sui 1.000 venue senza smoke test
- ❌ Modificare `beach_s1_venues.csv` o `beach_s2_venues_enriched.csv` (diff in file separato)
- ❌ Mescolare metadati Phase C con prezzi Phase D in unico CSV (file separati)
- ❌ Inventare prezzi quando il widget restituisce "non disponibile" (skippa, marca `extraction_status="no_availability"`)
- ❌ Toccare file drink (data/, prices_data.json, index.html)
- ❌ Bypassare captcha senza solver licenziato (legal grey area)
- ❌ Aggiungere codici al vocabolario `normalized_product` (se DOM ti dà categorie nuove → segnala in REPORT, CEO valuta)
- ❌ Considerare "venue matchato" un match < 300m senza verifica name similarity > 0.6

---

## SE BLOCCATO

Documenta SEMPRE in REPORT:
1. Phase corrente e progress
2. Errore specifico (HTTP status, exception, screenshot)
3. Cosa hai tentato come retry
4. Raccomandazione esplicita: skip / pause / escalate

**Non procedere a Phase successiva con la precedente rotta** — il debito tecnico accumula peggio del ritardo.

---

Buona sessione Peppe. **Spiagge.it è la miniera. Estrai con metodo, smoke test prima, consolida dopo.**
