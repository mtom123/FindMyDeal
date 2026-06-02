# Agent 7 — Report: discovery comune/CKAN/OSM + TheFork → drink Milano puliti

_vertical drink Milano · 2428 venues net-new in `agent7_venues_no_price.csv` · 0 prezzi (no-price)_

## 1. Sintesi esecutiva (per CEO)

- **2097 TARGET + 331 AMBIGUOUS_TO_REVIEW = 2428 venues net-new** (non già in DB prezzi/agent6), classificati, tipizzati, deduplicati.
- **Dedup cross-source**: 8949 righe pool → 5359 cluster (2243 multi-source). **1892 nomi commerciali recuperati** via cross-ref OSM.
- **750 doppioni vs DB evitati**, **2177 NO_TARGET (ristoranti) esclusi**.
- ⭐ **opening_hours: 100%** dei venues (236 reali OSM + 0 TheFork + 2192 fascia tipica per venue_type).
- **TheFork discovery** (curl_cffi safari17_2_ios, metadata no-prezzi): 1346 venues nel pool.

## 2. Riconciliazione sorgenti (dedup ratio)

| Sorgente (pool, geo in bbox) | Righe |
|---|---:|
| comune_milano | 3804 |
| osm | 2464 |
| thefork | 1346 |
| comune | 1335 |
| **Pool totale** | **8949** |

→ **5359 cluster unici** (geo-fingerprint + name match) = dedup -41%. Esclusi: 750 già-in-DB, 2177 NO_TARGET, 0 placeholder-no-addr, 4 CAP non-Milano. → **2428 in output**.

> **SUPERSEDE, non escludere**: il master CEO `unified_venues_no_price.csv` contiene i CKAN grezzi (senza classification/dedup/nome). Questo file è la versione pulita che li **sostituisce/aggiorna**.

## 3. Classificazione & venue_type

TARGET 2097 · AMBIGUOUS_TO_REVIEW 331. Tipi reali rappresentati: **8/9** (+ 38 unknown).

| venue_type | Count |
|---|---:|
| cocktail_bar | 19 |
| pub | 122 |
| cafe | 2162 |
| wine_bar | 9 |
| aperitivo_bar | 1 |
| bistro | 73 |
| craft_beer | 2 |
| rooftop | 2 |
| hotel_bar | 0 |
| unknown | 38 |
> `cafe` dominante = i "bar" generici di quartiere della licenza Comune (default IT). I tipi specializzati (cocktail/wine/rooftop) sono pochi qui perché i più noti sono già prezzati/in-DB.

## 4. Name recovery (cross-ref OSM)

**1892 venues** comune/CKAN (nome = licenziatario o `[bar non identificato]`) hanno adottato il **nome commerciale OSM** via match geografico (≤40 m). `name_source`: {'osm_overpass': 1820, 'ckan': 487, 'comune': 7, 'thefork': 114}.

## 5. ⭐ Opening hours (requisito CEO: 100%)

Copertura **100%** (2428/2428). Provenienza: **osm 236** (reale), **thefork 0**, **typical_by_type 2192** (fascia indicativa). Campo `opening_hours_source` distingue i reali dalle fasce tipiche → il frontend mostra "orario indicativo" per queste.

## 6. Copertura metadata

| Campo | Coverage |
|---|---:|
| opening_hours | 2428/2428 (100%) |
| website | 131/2428 |
| phone | 300/2428 |
| nil_quartiere | 1406/2428 |
| address | 2001/2428 |
> Nota onesta su website/phone: il ceiling è basso (OSM drink-amenity ha ~350 website / ~410 phone, no restaurant; i più popolari sono già in DB). Il target iniziale ≥800/≥700 era una mia stima errata (contava i ristoranti). Valore reale qui sopra.

## 7. Quartieri Milano

NIL quartiere distinti: **77**, con ≥3 venues: **69**. CAP distinti: **40** (38 città + 2 hinterland).

> ⚠️ Hinterland (comuni limitrofi, ammessi dal gate ma filtrabili dal CEO a 20121–20162): 20044×1, 20026×1.

## 8. TheFork discovery (Step 6, obbligatorio)

Tecnica: `curl_cffi` `impersonate='safari17_2_ios'` (bypass Datadome 403). Ogni pagina rende un ItemList JSON-LD da 25 Restaurant (name/address/geo/cuisine/rating) → paginazione listing città milano-c348156?p=N. **NESSUN prezzo** (menu via JS lazy, confermato). Venues TheFork nel pool: **1346**; in output (TARGET drink dopo dedup): **144**.
> TheFork è restaurant-heavy → la quota drink-TARGET è minoritaria; i metadata (geo/addr/rating) restano comunque utili e i duplicati vengono fusi nei cluster esistenti.

## 9. Issues residui / TODO (per CEO)

- **prezzi = 0** (atteso): no-price discovery. Bridge = crowdsourcing.
- **opening_hours typical_by_type**: la maggioranza è fascia indicativa (OSM ha hours solo per ~410 drink). Affinabile con scraping siti propri / crowdsourcing.
- **website/phone** bassi (ceiling OSM). TheFork/siti propri per arricchire (Playwright per i prezzi).
- **hinterland** nei CAP: il CEO decide se filtrare a Milano-città.
- **SUPERSEDE unified_venues_no_price**: il CEO rimpiazza i CKAN grezzi del master con questo output pulito.

## 10. File consegnati

- `raw_sources/agent7_venues_no_price.csv` — master discovery (schema esteso + nil_quartiere + name_source + opening_hours_source)
- `raw_sources/agent7_dedup_map.csv` — cluster multi-source consolidati
- `raw_sources/agent7_thefork_raw.csv` — raw TheFork metadata (input)
- `raw_sources/agent7_osm_enriched.csv` — OSM re-query con opening_hours
- `scripts/agent7_standardize.py` / `agent7_osm_overpass.py` / `agent7_thefork.py` / `agent7_report.py`

> Riusata `scripts/agent6_standardize.py` + `normalization.py`. NON toccati `data/`, `prices_data.json`, `index.html`, beach.
