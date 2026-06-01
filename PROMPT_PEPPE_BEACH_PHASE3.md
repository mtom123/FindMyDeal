# Prompt Peppe — Beach Phase 3 (Estrazione Prezzi)

> **CONTEXT**: S1+S2+S2X chiusi con un dataset master di ~13.646 venue (9.252 OSM + 4.394 spiagge.it nuovi + 2.299 match). 269 venue con prezzi. Ora si entra nella fase che genera **il valore vero del prodotto**: prezzi su scala.
>
> **Vedi**: commit `6b97a06`, `beach_s2x_REPORT.md`, `PROMPT_PEPPE_SPIAGGE_S2X.md`.

---

## OBIETTIVO STRATEGICO

Trasformare 13.646 venue metadata in un dataset **price-rich** che alimenti il frontend S3 con prezzi reali per estate 2026.

**Sequenza esecutiva** (rigida):
1. **Spiagge.it** prima — è il pool più grande (6.693 venue) e già scoperti, smoke confermato
2. **iBagnino** secondo — booking provider tradizionale, 50-150 venue stimati
3. **Beacharound/Summer Booking** terzo — già scoperto pattern URL in S2 (`/prezzi-ombrellone-lettino-sdraio`)
4. **iBeach / Cocobuk / Mondo Balneare** quarto — long tail provider
5. **Direct websites** quinto — venue con `website` popolato ma `booking_provider` vuoto

---

## OBIETTIVI MISURABILI PHASE 3

| Metrica | Target | Note |
|---|---|---|
| Venue con almeno 1 prezzo estratto | ≥ 2.000 | Era 35 in S2 |
| Price items totali | ≥ 25.000 | Era 269 in S2 |
| Copertura spiagge.it | ≥ 1.500 / 6.693 (22%) | Pool primario |
| Copertura iBagnino + secondari | ≥ 300 venue | Pool secondario |
| Direct websites | ≥ 200 venue | Coda lunga |
| Sud Italia venue prezzati | ≥ 500 | Era 5 in S2 |
| Coverage ≥30 venue prezzati per regione costiera | sì | 15 regioni |
| Confidence high+medium ratio | ≥ 80% | Solo low se ambiguo |
| Average price items per venue | ≥ 10 | 2 date × 5 zone medie |

**Punto onesto**: target dipendono dall'esito Step 3.0 (DOM discovery widget spiagge.it). Se selectors stabili → numeri raggiungibili in 1 sessione lunga. Se DOM cambia/captcha trigger → S3.5 con stack alternativo.

---

## INPUT DA REPO

```
raw_sources/
├── beach_s1_venues.csv                          # 9.252 master OSM
├── beach_s2_venues_enriched.csv                 # 9.252 + geo arricchito
├── beach_s2x_spiagge_venues.csv                 # 6.693 spiagge metadata
├── beach_s2x_spiagge_consolidated_venues.csv    # 6.693 + match_type
├── beach_s2x_master_updates.csv                 # 10.223 diff (decisional)
├── beach_s2x_spiagge_url_list.csv               # 6.693 URL spiagge.it
├── beach_s1_menu_items.csv                      # 214 items S1
├── beach_s2_direct_menu_items.csv               # 39 items S2 direct
├── beach_s2_pdf_menu_items.csv                  # 16 items S2 PDF
└── .spiagge_cache/                              # 6.693 JSON metadata cache (riusabile)

beach_s1_PROVIDERS.md                            # 8 provider booking analysis
beach_s2x_SMOKETEST.md                           # No anti-bot rilevato
```

**NON modificare** S1/S2/S2X CSV esistenti. Tutto output in `beach_phase3_*.csv`.

---

## OUTPUT PHASE 3

```
raw_sources/
├── beach_phase3_spiagge_menu_items.csv          # Prezzi spiagge.it (primario)
├── beach_phase3_ibagnino_menu_items.csv         # Prezzi iBagnino
├── beach_phase3_summerbooking_menu_items.csv    # Prezzi Summer Booking/Beacharound
├── beach_phase3_secondary_menu_items.csv        # iBeach, Cocobuk, Mondo Balneare
├── beach_phase3_direct_menu_items.csv           # Direct websites long tail
└── beach_phase3_consolidated_items.csv          # Tutti i menu items mergeati + dedup

scripts/
├── beach_phase3_playwright_client.py            # Client Playwright base (riusabile)
├── beach_phase3_spiagge_extract.py              # Estrattore spiagge.it
├── beach_phase3_ibagnino_extract.py             # Estrattore iBagnino
├── beach_phase3_summerbooking_extract.py        # Estrattore Beacharound/SB
├── beach_phase3_secondary_extract.py            # Long tail provider
├── beach_phase3_direct_extract.py               # Direct websites
└── beach_phase3_consolidate.py                  # Merge + dedup + quality gates

beach_phase3_SMOKE.md                             # DOM discovery + verdetto
beach_phase3_REPORT.md                            # Metriche finali + gap
beach_phase3_PROVIDERS_UPDATE.md                  # Update mappa provider
```

---

## SETUP TECNICO (una volta sola)

```bash
pip3 install playwright playwright-stealth lxml beautifulsoup4
playwright install chromium

# Verifica
python3 -c "from playwright.sync_api import sync_playwright; print('OK')"
```

`scripts/beach_phase3_playwright_client.py` — client base condiviso:

```python
"""
Phase 3 Playwright client riusabile.
- Stealth standard
- UA rotation
- Cookie reset ogni N venue
- Save partial ogni 10 venue (resume on crash)
- Rate limit con jitter umano (10-15s tra venue)
"""

from playwright.sync_api import sync_playwright, Page, Browser
from playwright_stealth import stealth_sync
import random, time, json, os
from datetime import datetime, timezone

USER_AGENTS = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
]

VIEWPORTS = [
    {"width": 1366, "height": 768},
    {"width": 1440, "height": 900},
    {"width": 1920, "height": 1080},
]

class PlaywrightClient:
    def __init__(self, headless=True, cache_dir=".playwright_cache"):
        self.headless = headless
        self.cache_dir = cache_dir
        os.makedirs(cache_dir, exist_ok=True)
        self.p = None
        self.browser = None
        self.context = None
        self.page = None
        self._count = 0
        self.RESET_EVERY = 50

    def __enter__(self):
        self.p = sync_playwright().start()
        self._new_context()
        return self

    def __exit__(self, *args):
        if self.context: self.context.close()
        if self.browser: self.browser.close()
        if self.p: self.p.stop()

    def _new_context(self):
        if self.context:
            self.context.close()
        if not self.browser:
            self.browser = self.p.chromium.launch(headless=self.headless)
        self.context = self.browser.new_context(
            user_agent=random.choice(USER_AGENTS),
            viewport=random.choice(VIEWPORTS),
            locale="it-IT",
            timezone_id="Europe/Rome",
        )
        self.page = self.context.new_page()
        stealth_sync(self.page)

    def goto(self, url, wait_until="networkidle", timeout=30000):
        # Reset context ogni RESET_EVERY venue
        if self._count > 0 and self._count % self.RESET_EVERY == 0:
            print(f"  → reset context dopo {self._count} fetch")
            self._new_context()
        # Human-like delay
        time.sleep(random.uniform(10, 15))
        # Tiny mouse jitter
        self.page.mouse.move(random.randint(100, 800), random.randint(100, 600))
        self._count += 1
        return self.page.goto(url, wait_until=wait_until, timeout=timeout)

    def cache_set(self, key, data):
        with open(os.path.join(self.cache_dir, f"{key}.json"), "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)

    def cache_get(self, key):
        path = os.path.join(self.cache_dir, f"{key}.json")
        if os.path.exists(path):
            with open(path, encoding="utf-8") as f:
                return json.load(f)
        return None
```

---

## PHASE 3.0 — DOM DISCOVERY SPIAGGE.IT (GATE)

> Fai questo PRIMA di scalare. Costa 30-60 min, salva ore di errori a valle.

### Step 3.0.1 — Manual inspection

1. Apri `https://www.spiagge.it/stabilimenti-balneari/10389-bagno-hawaii/` in Chrome **non headless**
2. DevTools → Network tab → filter XHR/Fetch
3. Compila il widget prezzi (date 1-7 ago 2026)
4. Cattura:
   - L'URL XHR che ritorna i prezzi
   - Il payload request (header + body)
   - Il payload response (struttura JSON)
   - I selettori CSS dei prezzi sul DOM finale

### Step 3.0.2 — Save findings in `beach_phase3_SMOKE.md`

Template da compilare:

```markdown
## Spiagge.it Widget — Reverse Engineering

### XHR Endpoint scoperto
URL: https://...
Method: POST/GET
Required headers: ...
Payload schema: {...}
Response schema: {...}

### Selectors DOM (se vai via Playwright pure)
Date input: `input[name="..."]`
Submit button: `button.search-...`
Price cells: `.umbrella-price`
Row metadata: `[data-row]`, `[data-position]`

### Decisione finale (cerchia uno)
[ ] PURE_XHR: posso bypassare Playwright, chiamo l'API direttamente (10× più veloce)
[ ] PLAYWRIGHT_FULL: serve browser engine completo
[ ] HYBRID: Playwright per ottenere token/csrf, poi XHR diretti
```

### Step 3.0.3 — Test su 5 venue (mix province)

Estrai prezzi per 5 venue (uno per: ER Rimini, FVG Lignano, TOS Versilia, CAM Salerno, SIC Palermo).

Quality check per ogni venue:
- ✅ Prezzi numerici parseable
- ✅ Distinzione fila/zona se presente
- ✅ Distinzione date di check-in/out coerente
- ✅ Nessun "non disponibile" mascherato

**Verdetto smoke**:
- 5/5 OK → GO Step 3.1 (scaling)
- 3-4/5 OK → GO con limits (max 100 venue/sessione)
- 0-2/5 OK → STOP, escalate al CEO, propongo S3.5 con stack alternativo

---

## PHASE 3.1 — SPIAGGE.IT MASS EXTRACTION

### Pool target prioritizzato

Estrai prezzi sui venue **in quest'ordine** (sequenza esecutiva):

#### Wave 1 — Match con master S1 (2.299 venue) — HIGH PRIORITY

Sono venue già nel master OSM, doppia validazione (geo OSM + booking spiagge). Prezzarli arricchisce direttamente il dataset principale.

```python
# Filter
venues = read_csv("raw_sources/beach_s2x_spiagge_consolidated_venues.csv")
wave1 = [v for v in venues if v["match_type"] == "geo_300m"]  # 2.296 venue
```

#### Wave 2 — Sud Italia (528 venue) — HIGH IMPACT

Erano il gap principale di S1/S2 (5 venue prezzati). Wave 2 chiude il gap.

```python
SUD_REGIONS = {"Campania", "Calabria", "Sicilia", "Puglia", "Basilicata", "Molise"}
wave2 = [v for v in venues
         if v["region"] in SUD_REGIONS
         and v["match_type"] != "geo_300m"]  # 528 venue non già in Wave 1
```

#### Wave 3 — Resto Italia (3.866 venue) — VOLUME

I venue rimasti (no_match + geo_only_name_diff Centro+Nord).

### Date di reference

| Slot | Check-in | Check-out | Significato |
|---|---|---|---|
| **PEAK** | 2026-08-01 | 2026-08-07 | Alta stagione (benchmark Altroconsumo) |
| **MID** | 2026-06-15 | 2026-06-21 | Bassa stagione (spread) |
| **WEEKEND_PEAK** (opzionale) | 2026-08-08 | 2026-08-09 | Solo weekend agosto |

Per ogni venue: 2 fetch obbligatori (PEAK + MID), 3° opzionale se tempo.

### Rate / pacing

- 10-15s tra venue (random jitter)
- Reset context ogni 50 venue (cookie/cache clear)
- Salva incrementale ogni 10 venue su disco (`raw_sources/.phase3_cache/`)
- HTTP 429 → STOP, pause 4h, segnala
- Captcha trigger → STOP, screenshot, escalate

### Output mapping

Per ogni prezzo estratto → row nel CSV con questi campi extra vs S1:

```
peak_or_mid: "peak_aug" | "mid_jun" | "weekend_aug"
check_in_date: "2026-08-01"
check_out_date: "2026-08-07"
umbrella_row: "1" | "2" | "3" | "..."
umbrella_position: "12A" (se disponibile)
booking_provider: "spiagge.it"
```

Mapping a `normalized_product` (vocabolario S1):

| Widget label | normalized_product |
|---|---|
| Ombrellone (qualsiasi configurazione) | `beach_umbrella_standard` |
| Ombrellone 1ª fila | `beach_umbrella_first_row` |
| Ombrellone + 2 lettini (pacchetto) | `beach_set_2lettini_ombrellone` |
| Ombrellone + 1 lettino | `beach_set_1lettino_ombrellone` |
| Cabina giornaliera | `beach_cabin_day` |
| Cabina stagionale | `beach_cabin_season` |
| Solo lettino | `beach_sunbed` |

Mapping a `price_type`:
- 7 giorni consecutivi → `per_week`
- 1 giorno → `per_day`
- Weekend → `per_day_weekend`
- Stagionale visibile nel widget → `per_season`

Se ambiguo → vuoto + `confidence=medium`.

---

## PHASE 3.2 — iBAGNINO

URL pattern: variabile per venue, spesso `ibagnino.com/{slug}/prezzi`.

### Discovery

1. Lista venue con `booking_provider="ibagnino"` (Phase 0 backfill, vedi S2X)
2. Se non ancora popolato: dorks `site:ibagnino.com inurl:prezzi`
3. Sitemap: `https://ibagnino.com/sitemap.xml` (verifica esistenza)

### Extraction

iBagnino è tipicamente listino statico HTML (no widget JS). Tentare prima `requests` puro:

```python
import requests, re
r = requests.get(url, headers={"User-Agent": "SurPrice-Research/1.0"})
# Pattern listino
prices = re.findall(r'€\s*(\d+(?:[,.]\d{2})?)', r.text)
```

Se yield < 50%, fallback Playwright.

**Target Phase 3.2**: 100-200 venue, 1.000-3.000 items.

---

## PHASE 3.3 — BEACHAROUND / SUMMER BOOKING

In S2 abbiamo già il pattern URL:
```
https://www.beacharound.com/it/spiagge/{slug}/prezzi-ombrellone-lettino-sdraio
```

In S2 abbiamo verificato: `beacharound.com` ridirige a `summerbooking.it` per i venue. Summer Booking è SPA pura (Phase 3 originale skip).

### Tentativo XHR API (PRIORITÀ)

Step 3.3.0: in DevTools, carica una pagina prezzi su summerbooking.it → cattura XHR. Se trovi `availability` o `prices` API → bypass Playwright.

### Fallback Playwright

Solo se XHR non funziona. Setup uguale a 3.1 (riusa client).

### Discovery URL

```bash
curl -A "SurPrice-Research/1.0" https://summerbooking.it/sitemap.xml
# Se vuoto/SPA: Google dork
# site:summerbooking.it inurl:prezzi-ombrellone
```

**Target Phase 3.3**: 100-300 venue, 800-2.500 items.

---

## PHASE 3.4 — SECONDARY PROVIDERS

Stesso approccio per:
- **iBeach** (`ibeach.it`)
- **Cocobuk** (`cocobuk.com`)
- **Mondo Balneare** (`mondobalneare.com`)
- **Bibionemare** (`stabilimenti.bibionemare.com`) — già parzialmente in S1

Pattern: `requests` first, Playwright fallback. Quality gate uguale.

**Target Phase 3.4**: 50-150 venue cumulativi.

---

## PHASE 3.5 — DIRECT WEBSITES (CODA LUNGA)

Pool: venue con `website` popolato in `beach_s1_venues.csv` ma `booking_provider` vuoto.

Per ogni website:
1. Fetch homepage con requests
2. Cerca link "Tariffe" / "Listino" / "Prezzi" / "Rates"
3. Se pagina prezzi trovata → parse con `re` su pattern `€\s*\d+`
4. Se PDF → download + `pdfplumber`
5. Se widget JS dinamico → skip (logga, non Playwright per coda lunga)

**Target Phase 3.5**: 100-200 venue, 500-1.500 items.

---

## PHASE 3.6 — CONSOLIDATION

Script `scripts/beach_phase3_consolidate.py`:

```python
import csv
from collections import defaultdict

# 1. Load all menu_items CSV
files = [
    "beach_s1_menu_items.csv",
    "beach_s2_direct_menu_items.csv",
    "beach_s2_pdf_menu_items.csv",
    "beach_phase3_spiagge_menu_items.csv",
    "beach_phase3_ibagnino_menu_items.csv",
    "beach_phase3_summerbooking_menu_items.csv",
    "beach_phase3_secondary_menu_items.csv",
    "beach_phase3_direct_menu_items.csv",
]

all_items = []
for f in files:
    with open(f) as fh:
        all_items.extend(csv.DictReader(fh))

# 2. Dedup chiave
def dedup_key(r):
    return (
        r["source_venue_id"],
        r["normalized_product"],
        r["raw_price"],
        r["price_type"],
        r.get("peak_or_mid", ""),
        r.get("umbrella_row", ""),
    )

seen = set()
unique = []
for r in all_items:
    k = dedup_key(r)
    if k not in seen:
        seen.add(k)
        unique.append(r)

# 3. Quality gate finale
GOOD_PRODUCTS = {"beach_umbrella_standard", "beach_umbrella_first_row", "beach_umbrella_premium",
                 "beach_sunbed", "beach_chair", "beach_cabin_day", "beach_cabin_season",
                 "beach_set_2lettini_ombrellone", "beach_set_1lettino_ombrellone",
                 "beach_parking", "beach_shower", "beach_subscription_week",
                 "beach_subscription_month", "beach_subscription_season",
                 "beach_entry_fee", "beach_minimum_spend", ""}
GOOD_PRICE_TYPES = {"per_day_weekday", "per_day_weekend", "per_day", "per_half_day",
                    "per_week", "per_month", "per_season", "one_off", ""}

clean = []
for r in unique:
    p = float(r["normalized_price_eur"] or 0)
    if p <= 0 or p > 7000: continue
    if r["normalized_product"] not in GOOD_PRODUCTS: continue
    if r["price_type"] not in GOOD_PRICE_TYPES: continue
    if r["vertical"] != "beach": continue
    clean.append(r)

# 4. Write consolidated
with open("raw_sources/beach_phase3_consolidated_items.csv", "w") as fh:
    w = csv.DictWriter(fh, fieldnames=clean[0].keys())
    w.writeheader()
    w.writerows(clean)
```

### Stats finali da reportare

- Items totali consolidati
- Venue unici con almeno 1 prezzo
- Distribuzione per `normalized_product`
- Distribuzione per `price_type`
- Distribuzione per regione + Sud Italia
- Confidence distribution

---

## QUALITY GATES PHASE 3

Per ogni ITEM:
1. ✅ `normalized_price_eur` parseable, 0 < p ≤ 7.000 (alziamo cap a 7k per coprire stagionali premium)
2. ✅ `normalized_product` da vocabolario chiuso S1 (16 codici) o vuoto
3. ✅ `price_type` da vocabolario chiuso S1 o vuoto
4. ✅ `peak_or_mid` ∈ {"peak_aug", "mid_jun", "weekend_aug", ""} per spiagge.it
5. ✅ `check_in_date`/`check_out_date` ISO date valide
6. ✅ `umbrella_row` numerico (se presente)
7. ✅ Dedup su `(venue_id, product, raw_price, price_type, peak_or_mid, row)`
8. ✅ `vertical = "beach"`, `season = "summer_2026"`
9. ✅ `booking_provider` popolato
10. ✅ **ANTI-LISTINI STANTII**: source PDF/page con "2024" o precedente → `confidence=low` o skip
11. ✅ `confidence`: `high` se DOM stabile + prezzo esplicito, `medium` se inferito, `low` se ambiguo (max 5% del totale può essere low)

---

## ANTI-BOT STRATEGY

### Tier 1 (default per Phase 3.1+)
- `playwright-stealth`
- UA rotation (3 UA pool)
- Viewport randomizzato
- Reset context ogni 50 venue
- Mouse jitter random
- Delay 10-15s tra azioni

### Tier 2 (se Tier 1 KO su provider X)
- `undetected-chromedriver`
- Residential proxy rotation
- Captcha solver (2captcha)

### Tier 3 (ultima risorsa)
- Manual scrape mode (apri browser reale, copia-incolla)
- Outreach partnership data feed

**Documenta in REPORT quale tier hai usato per ogni provider.**

---

## RATE LIMITS

| Provider | Rate | Note |
|---|---|---|
| Spiagge.it Playwright | 10-15s/venue | Confermato no anti-bot in S2X |
| Spiagge.it XHR (se trovato) | 1-2s/req | Backup veloce |
| iBagnino | 2s/req | Listino HTML statico atteso |
| Summer Booking Playwright | 12-18s/venue | SPA, più lento |
| Direct websites | 2s/req | Standard courtesy |
| Sitemap fetch | 1s | One-shot |
| HTTP 429 | STOP 4h | Save partial, segnala |
| Captcha | STOP | Screenshot + escalate |

---

## BUDGET TEMPO

| Phase | Ore | Note |
|---|---|---|
| 3.0 DOM discovery + smoke 5 venue | 1-2 | Gate obbligatorio |
| 3.1 Spiagge.it Wave 1 (2.296 venue) | 8-12 | 2 date × 12s = 24s/venue → ~15h pure, riducibile con XHR |
| 3.1 Spiagge.it Wave 2 (528 Sud) | 2-4 | Priorità alta |
| 3.1 Spiagge.it Wave 3 (3.866 resto) | 12-20 | Volume, opzionale |
| 3.2 iBagnino | 2-4 | |
| 3.3 Beacharound/SB | 3-6 | |
| 3.4 Secondary | 2-3 | |
| 3.5 Direct websites | 3-5 | |
| 3.6 Consolidation | 1-2 | |
| Reporting | 1-2 | |
| **MVP** (3.0 + 3.1 W1+W2 + 3.2 + 3.6 + report) | **17-31** | Garantisce 2.500 venue prezzati |
| **Completo** | **35-60** | Tutte le fasi |

**Decisione**: se le 17-31h pesano, MVP è sufficiente per dimostrare il prodotto. Wave 3 + 3.3-3.5 possono slittare a S3.5.

---

## DELIVERY (commit per phase)

```bash
cd /Users/g_giaimo02/Desktop/TTW/FindMyDeal
git pull --rebase origin main

# Dopo Phase 3.0
git add beach_phase3_SMOKE.md scripts/beach_phase3_playwright_client.py
git commit -m "infra: phase 3 playwright client + spiagge.it DOM discovery"
git push origin main

# Dopo Phase 3.1 (incrementi: ogni 500 venue scrapati)
git add raw_sources/beach_phase3_spiagge_menu_items.csv scripts/beach_phase3_spiagge_extract.py
git commit -m "data: phase 3.1 spiagge.it — N venue, M items"
git push origin main

# ... etc per 3.2, 3.3, 3.4, 3.5

# Finale
git add beach_phase3_REPORT.md raw_sources/beach_phase3_consolidated_items.csv
git commit -m "data: phase 3 COMPLETO — N venue prezzati, M items, K regioni coperte"
git push origin main
```

---

## CHE COSA NON FARE IN PHASE 3

- ❌ Lanciare Playwright a 6.693 venue senza Step 3.0 smoke completato
- ❌ Modificare file S1/S2/S2X esistenti
- ❌ Sovrascrivere `normalized_product` con codici nuovi (CEO approva eventuali aggiunte)
- ❌ Considerare `confidence=high` un prezzo da PDF/listino datato 2024 o precedente
- ❌ Considerare un widget che restituisce "non disponibile" come prezzo €0
- ❌ Bypassare captcha senza solver licenziato (legal grey area)
- ❌ Skippare il delay 10-15s tra venue su spiagge.it (vogliamo essere onesti, non solo cauti)
- ❌ Commit batch giganti senza checkpoint intermedi (rollback chirurgico richiesto se 1 wave va male)

---

## SE BLOCCATO IN UNA PHASE

Documenta SEMPRE in `beach_phase3_REPORT.md`:
1. Phase corrente e progress (venue processati / target)
2. Errore specifico (HTTP status, Playwright exception, screenshot)
3. Cosa hai tentato come retry
4. Raccomandazione esplicita: skip / pause / escalate

**Non procedere alla phase successiva con la precedente rotta** — il debito tecnico accumula peggio del ritardo.

Se sei bloccato su spiagge.it: **completa comunque le altre phase** (iBagnino, direct, ecc.) prima di dichiarare la sessione fallita. Spiagge.it è il pool maggiore ma non l'unico.

---

## HOOK A S3 FRONTEND

A fine Phase 3, oltre ai CSV, consegna in `beach_phase3_REPORT.md` una sezione **"Dati pronti per frontend"** con:

- Top 20 venue più cari per regione
- Distribuzione mediana prezzo `beach_set_2lettini_ombrellone` per_week per regione
- Lista delle 10 città con maggior copertura (per priorità S3 UI)
- 5 esempi di "schede venue" complete (nome, geo, amenities, prezzi peak+mid)

Servono al frontend team per dimensionare i widget UI.

---

Buona caccia, Peppe. **Phase 3 è il salto dal dato al prodotto. Spiagge.it prima, ma non ti fermare lì.**
