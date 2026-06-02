# Prompt Pietro — Sessione S7: Espansione Drink TOP 6 città Italia (03/06/2026)

> **CAMBIO DI ROTTA CEO/Utente** (call odierna): il progetto SurPrice si espande dal solo Milano a **6 città principali Italia**. Tu sei l'unico scraper drink. Replica il playbook Milano per 5 nuove città.
>
> **Target**: 6 città totali, ognuna con stesso pattern dati che hai costruito per Milano (DB + no-price layer + price points).

---

## CITTÀ TARGET (in ordine priorità)

| # | Città | CAP range | Stima venues drink target |
|---|---|---|---|
| 0 | Milano (già fatto) | 20100-20162 | 153 prezzati + 3.712 no-price |
| 1 | **Roma** | 00100-00199 | ~6.000-8.000 |
| 2 | **Napoli** | 80100-80147 | ~2.500-3.500 |
| 3 | **Torino** | 10100-10156 | ~2.000-3.000 |
| 4 | **Firenze** | 50100-50145 | ~1.500-2.500 |
| 5 | **Bologna** | 40100-40141 | ~1.500-2.500 |
| 6 | **Venezia** | 30100-30176 | ~1.000-1.500 |

**Stima totale aggregato**: ~20.000 venues drink Italia + ~3.000-5.000 price points raccoglibili.

---

## NUOVA ARCHITETTURA — MULTI-CITY

### Schema CSV esteso (CRITICO — modifica `SCHEMA_AGENTI.md`)

Tutti i tuoi CSV output ora richiedono **`city`** come campo OBBLIGATORIO:

```csv
source_platform,source_venue_id,venue_name,venue_url,address,city,latitude,longitude,...
```

`city` ∈ {`Milano`, `Roma`, `Napoli`, `Torino`, `Firenze`, `Bologna`, `Venezia`}.

### Naming files raw_sources

Prefisso per città + sessione:
```
raw_sources/
├── agent7_milano_*.csv      # se aggiorni Milano
├── agent7_roma_*.csv         # nuova città
├── agent7_napoli_*.csv
├── agent7_torino_*.csv
├── agent7_firenze_*.csv
├── agent7_bologna_*.csv
└── agent7_venezia_*.csv
```

---

## PLAYBOOK PER CITTÀ (replica Milano)

Per ogni città dei 6 target, applica questo workflow:

### A) Discovery anagrafica venues (open data città)

**Strategia per ogni città** — cerca dataset CKAN/open data comunale + OSM:

| Città | Open data | CKAN endpoint | Note |
|---|---|---|---|
| Roma | dati.comune.roma.it | CKAN attivo | Cerca "esercizi commerciali", "pubblici esercizi" |
| Torino | aperto.comune.torino.it | CKAN attivo | "attivita commerciali" |
| Napoli | dati.comune.napoli.it | CKAN parziale | Spesso solo PDF, fallback OSM |
| Firenze | opendata.comune.fi.it | CKAN attivo | Categoria "esercizi pubblici" |
| Bologna | dati.comune.bologna.it | CKAN attivo | Forte open data culture |
| Venezia | dati.comune.venezia.it | CKAN attivo | Cerca "pubblici esercizi" |

**Workflow per ogni città**:
```python
# 1. CKAN package_search per "esercizi pubblici" / "attivita commerciali"
# 2. Filter su categoria bar/caffè/pub/wine bar (analogo a Milano f/e/g/h/i/j)
# 3. Estrai venues con geo + addr + CAP città-specifico

# 4. OSM Overpass query per amenity=bar/pub/cafe/nightclub area="Roma"
# 5. Cross-ref CKAN ↔ OSM (geo 50m) per nomi commerciali
# 6. Filter via bbox città (vedi sotto)
```

### B) Bbox per città (filter quality)

Da inserire nel `normalization.py` extension:

```python
CITY_BBOX = {
    'Milano':  (45.39, 45.54, 9.04, 9.28),
    'Roma':    (41.78, 42.00, 12.35, 12.65),
    'Napoli':  (40.78, 40.92, 14.15, 14.35),
    'Torino':  (45.00, 45.13, 7.55, 7.78),
    'Firenze': (43.72, 43.83, 11.18, 11.32),
    'Bologna': (44.43, 44.55, 11.25, 11.42),
    'Venezia': (45.40, 45.47, 12.30, 12.40),
}

def is_in_city(lat, lon, city):
    if city not in CITY_BBOX:
        return False
    lat_min, lat_max, lon_min, lon_max = CITY_BBOX[city]
    return lat_min <= lat <= lat_max and lon_min <= lon <= lon_max
```

### C) Discovery prezzi/menu (per ogni città)

**Riusa le tecniche provate**:

| Tecnica | Source | Status |
|---|---|---|
| **leggimenu.it slug brute-force** | leggimenu | ✅ provata Milano S3, replicabile |
| **mycia.it sitemap per città** | mycia | ✅ provata Milano S0 |
| **eatbu.com sitemap nazionale** | eatbu | ✅ già fatto Italy-wide, filtra per CAP città |
| **TheFork via Wayback** | thefork | ✅ provata Milano S4 |
| **TheFork live `curl_cffi safari17_2_ios`** | thefork | ✅ NUOVA (CEO night) — bypass 403, metadata only |
| **PDF dish.co via venue website Google dork** | direct_website | ✅ provata pdf_googledork |
| **menudigitale.it filter città** | menudigitale | ✅ già scaricato Italy-wide |
| **OSM Overpass bar/pub/cafe** | OSM | ✅ già usato Milano |

**Replica per Roma/Napoli/Torino/Firenze/Bologna/Venezia**:

```python
# Eatbu: stesso sitemap già scaricato, filter CAP per città
import csv
city_caps = {
    'Roma':    range(100, 200),
    'Napoli':  range(80100, 80148),
    # ...
}
# Per ogni venue eatbu con postcode in city_caps[X] → tag city=X
```

```python
# Leggimenu slug brute-force: stesso codice S3 ma con città target
slugs = generate_slugs(venue_names_from_OSM[city])
# fetch leggimenu.it/menu/<slug>
# Quality gate: address contiene città + CAP city range
```

### D) Quality gates per città (INLINE)

Per ogni venue/item, applica filtro:
1. `is_in_city(lat, lon, city)` deve essere True
2. CAP in address deve match `city_caps[city]`
3. Tutte le altre regole `clean_item_product()` da `normalization.py`

---

## ESTENSIONE LIBRERIA CONDIVISA (deliverable secondario)

**Estendi `scripts/normalization.py`** aggiungendo:

```python
# Aggiungi a normalization.py
CITY_BBOX = { ... }  # vedi sopra
CITY_CAP_RANGES = {
    'Milano':  range(20100, 20163),
    'Roma':    range(100, 200),  # 00100-00199
    'Napoli':  range(80100, 80148),
    'Torino':  range(10100, 10157),
    'Firenze': range(50100, 50146),
    'Bologna': range(40100, 40142),
    'Venezia': range(30100, 30177),
}

def is_in_city(lat, lon, city): ...
def detect_city_from_cap(cap_str): ...  # ritorna nome città dal CAP
def is_address_in_city(addr, city): ...
```

E `is_milan_or_unknown()` rinomina in `is_target_city_or_unknown(addr, cities=ALL)`.

**Commit separato `lib: normalization.py extension multi-city`** PRIMA di iniziare il scraping.

---

## TARGET MISURABILI S7

### Per ogni nuova città (Roma, Napoli, Torino, Firenze, Bologna, Venezia)

| Metrica | Target minimo | Target ottimo |
|---|---|---|
| Venues master discovery | 1.000 | 5.000 |
| Venues con geo precisa | 80% | 95% |
| Venues con nome commerciale | 60% | 90% |
| Price points estratti | 50 | 300 |
| Venue-product pairs | 30 | 200 |

### Aggregato 6 nuove città

| Metrica | Target |
|---|---|
| Venues master Italia (incl. Milano) | ≥ 20.000 |
| Price points Italia (incl. Milano 964) | ≥ 2.000 |
| Pin sulla mappa (priced+no-price) | ≥ 18.000 |

---

## SETUP

```bash
cd ~/percorso/SurPrice
git pull origin main
```

**OBBLIGATORIO leggere**:
- `AGENTS.md`, `AGENTS_STATE.md`, `CHANGELOG.md` (3 voci 03/06)
- `scripts/normalization.py` (libreria condivisa — estendi qui)
- `scripts/SCHEMA_AGENTI.md` (schema CSV — sarà esteso da CEO con `city`)
- `scripts/agent6_standardize.py` (logica classify/detect riusabile)
- `NIGHT_RESEARCH_REPORT.md` (CKAN + OSM Overpass + curl_cffi)

Working dir: `raw_sources/` · Prefisso: `agent7_<city>_*` · Script: `scripts/agent7_*.py`

---

## STEP OPERATIVI

### Step 1 — Estensione `normalization.py` (1 commit dedicato)
Aggiungi `CITY_BBOX`, `CITY_CAP_RANGES`, `is_in_city()`, `is_address_in_city()`.
Push immediato. CEO + Peppe useranno questa estensione.

### Step 2 — Discovery anagrafica per Roma (la più grande, prima)
- CKAN dati.comune.roma.it
- OSM Overpass Roma bar/pub/cafe
- Cross-ref + dedup
- Output: `raw_sources/agent7_roma_venues_no_price.csv`

### Step 3 — Discovery prezzi Roma (riusa tecniche Milano)
- eatbu sitemap filter Roma
- leggimenu slug brute-force Roma
- mycia sitemap Roma
- TheFork via Wayback Roma
- PDF dish.co
- Output: `raw_sources/agent7_roma_menu_items.csv` + `agent7_roma_venues.csv`

### Step 4-7 — Replica per Napoli, Torino, Firenze, Bologna, Venezia
Stesso pattern. Una città alla volta. Commit + push per ogni città chiusa (commit chirurgici, no batch monstre).

### Step 8 — Report finale
`agent7_REPORT.md` con tabella per città: venues, price points, quality gate stats.

---

## QUALITY GATES (USA SHARED LIB, NON RICREARE)

```python
from normalization import (
    clean_item_product, validate_item, PRICE_RANGES,
    is_in_city, is_address_in_city  # ← nuove S7
)

# Per ogni item
is_valid, item, reason = validate_item(item)
if not is_valid:
    continue
# Per ogni venue
if not is_in_city(lat, lon, city):
    continue
```

Pattern noti coperti da shared lib (NON ricreare):
- americano cocktail vs caffè
- beer_moretti vs Vittorio Moretti Franciacorta
- prosecco_glass vs bottiglia
- MAXI/caraffa multi-porzione
- Item name HTML noise
- Range prezzi realistic Italian bar

---

## RATE LIMITS (importanti)

| Servizio | Rate |
|---|---|
| Nominatim | 1.2s/req (TOS hard) |
| Overpass API | query grosse OK ma rate-limited (1 query / 5 min consigliato) |
| leggimenu.it | 1.5s/req |
| mycia.it | 2s/req |
| eatbu.com | 2s/req |
| CKAN API città | 1s/req |
| Wayback Machine | 2s/req, HTTP 429 → sleep 300s |
| TheFork curl_cffi | 3-5s/req, max 50 venues/sessione |

---

## CONSEGNA

Commit chirurgici per città:
```bash
git pull --rebase origin main
git add raw_sources/agent7_roma_*.csv scripts/agent7_roma_*.py
git commit -m "data: S7 Roma — N venues discovery, M items prezzi"
git push origin main
```

Avvisa CEO ad ogni città chiusa. Il CEO farà merge incrementale (un `merge_pipeline_drink.py` multi-city).

---

## ERRORI DA NON RIPETERE

1. ❌ **City missing**: ogni riga DEVE avere `city` correttamente popolato. Niente Milano default.
2. ❌ **Bbox bypassed**: usa `is_in_city()`, non solo CAP (alcuni CAP overlap zone limitrofe).
3. ❌ **Brute-force senza filter città**: lezione S3 (leggimenu pesco Italia intera). Filter inline.
4. ❌ **Schema parziale**: usa SEMPRE schema completo SCHEMA_AGENTI.md.
5. ❌ **Dedup cross-city saltata**: stesso brand a Roma e Milano = 2 entries diverse, NON dedup.
6. ❌ **Library duplicate**: importa da `normalization.py`, NON riscrivere quality gate.

---

## BACKLOG OPZIONALE (se hai tempo extra)

- TheFork bulk metadata Italia con `curl_cffi safari17_2_ios` (tutte 6 città)
- Quandoo.it scoperta nuovo URL pattern (era 404 in CEO night, ri-tentare)
- Foursquare/Swarm API free tier per metadata

---

## ARCHITETTURA POST-S7 (per orientarti)

Il CEO trasformerà `merge_pipeline.py` in **multi-city + multi-vertical**:
- `scripts/merge_pipeline_drink.py` (legge tutti i `*_venues.csv` + `*_menu_items.csv` con `city` field, produce `data/unified_*_drink_<city>.csv` per ogni città)
- `scripts/merge_pipeline_beach.py` (vertical separato)
- `scripts/merge_pipeline_barbieri.py` (Peppe lancia vertical barbieri)
- `scripts/merge_pipeline_palestre.py` (utente lancia vertical palestre)

Tu non devi scrivere questi merge. Devi solo consegnare CSV con `city` corretto.

---

## TEMPO STIMATO

| Step | Ore |
|---|---|
| Step 1 (lib extension) | 1 |
| Step 2-3 Roma (discovery + prezzi) | 8-10 |
| Step 4 Napoli | 4-6 |
| Step 5 Torino | 4-6 |
| Step 6 Firenze | 3-5 |
| Step 7 Bologna | 3-5 |
| Step 8 Venezia | 2-3 |
| Step 8 Report | 1 |
| **Totale** | **26-37 ore** (3-4 sessioni Pietro distribuite) |

Se serve, prioritizza Roma + Napoli (le 2 più grandi) per primo deliverable. Le altre 4 città sono S7.2 / S8.

---

## DECISIONI STRATEGICHE PRESE (per il tuo briefing)

Pietro: oggi (03/06/2026) c'è stata call utente con team. Decisione:
1. **SurPrice si espande a 6 città** (Milano + Roma + Napoli + Torino + Firenze + Bologna + Venezia)
2. **Tu sei lo scraper drink Italia-wide** — il vertical anchor
3. **Peppe entra in vertical Barbieri** (nuovo vertical SurPrice)
4. **Utente entra in vertical Palestre** (terzo nuovo vertical)
5. **Crowdsourcing Supabase** sera oggi con utente (CEO setup)
6. **Spin-off**: NO. SurPrice resta brand unico multi-vertical (decisione CEO).

Il tuo lavoro (S7 drink Italia) è il **fondamento del brand**: drink è il vertical anchor, le altre 6 città replicano e validano il modello Milano. **Quality > quantity sempre**.

---

Buon lavoro Pietro. **L'obiettivo è 6 nuove città Italia con stesso rigore di Milano. Il framework esiste, va solo replicato.**
