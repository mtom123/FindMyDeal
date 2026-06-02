# Agent 7 / S8 — Espansione drink multi-città Italia (discovery no-price)

_Replica del playbook Milano su 6 nuove città · sorgente OSM Overpass · 0 prezzi (discovery)_

## 1. Sintesi (per CEO)

- **6/6 città** consegnate questa sessione: Roma, Napoli, Torino, Firenze, Bologna, Venezia.
- **6036 venues drink net-new** (oltre ai 2.428 Milano S7), tutti classificati TARGET/AMBIGUOUS, tipizzati, deduplicati, con **opening_hours 100%**.
- Sorgente: **OSM Overpass** (bar/pub/cafe/nightclub/biergarten) — nomi commerciali reali, amenity, e dove disponibili opening_hours/website/phone. Pipeline `agent7_city.py` parametrico.
- ⚠️ **Prezzi = follow-up**: i dati nazionali esistenti (menudigitale) sono risultati esigui (~111 venues sparsi). I price points per città richiedono scraping dedicato (mycia/leggimenu per città) → sessione separata. Questa sessione consegna il **venue master** (metrica primaria del prompt).

## 2. Per città

| Città | Venues | opening_hours reali | website | phone | venue_type top |
|---|---:|---:|---:|---:|---|
| Roma | 2254 | 421 | 311 | 637 | cafe 1924, pub 206, cocktail_bar 72 |
| Napoli | 718 | 69 | 47 | 84 | cafe 640, pub 47, cocktail_bar 19 |
| Torino | 1297 | 317 | 114 | 227 | cafe 1102, pub 140, cocktail_bar 36 |
| Firenze | 713 | 123 | 56 | 93 | cafe 598, pub 69, cocktail_bar 24 |
| Bologna | 749 | 162 | 87 | 153 | cafe 656, pub 49, cocktail_bar 27 |
| Venezia | 305 | 74 | 47 | 67 | cafe 265, pub 23, wine_bar 8 |

## 3. venue_type per città

| Città | cocktail_bar | pub | cafe | wine_bar | aperitivo_bar | bistro | craft_beer | rooftop | hotel_bar | unknown |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Roma | 72 | 206 | 1924 | 10 | 1 | 32 | 6 | 2 | 1 | 0 |
| Napoli | 19 | 47 | 640 | 5 | 0 | 6 | 1 | 0 | 0 | 0 |
| Torino | 36 | 140 | 1102 | 6 | 1 | 12 | 0 | 0 | 0 | 0 |
| Firenze | 24 | 69 | 598 | 7 | 0 | 11 | 2 | 1 | 1 | 0 |
| Bologna | 27 | 49 | 656 | 6 | 0 | 8 | 3 | 0 | 0 | 0 |
| Venezia | 3 | 23 | 265 | 8 | 0 | 3 | 3 | 0 | 0 | 0 |

## 4. Quality gate (tutte le città)

Ogni venue: `is_in_city(lat,lon,city)` ✓ (bbox `normalization.CITY_BBOX`), classificazione TARGET/AMBIGUOUS (no NO_TARGET), no junk-name, dedup geo+nome (stesso-nome <150m fuso, branch >250m separati), **opening_hours non vuoto** (reale o typical_by_type).

## 5. Aggregato Italia

- Milano (S6+S7): 153 prezzati + 824 (agent6) + 2428 (agent7 discovery)
- Roma: 2254 venues discovery
- Napoli: 718 venues discovery
- Torino: 1297 venues discovery
- Firenze: 713 venues discovery
- Bologna: 749 venues discovery
- Venezia: 305 venues discovery
- **Nuove città S8: 6036 venues** · pin no-price totali Italia in crescita verso il target ≥18.000.

## 6. TODO / follow-up (per CEO)

- **Prezzi per città** (mycia sitemap, leggimenu brute-force, menudigitale per-città): sessione dedicata.
- **CKAN per città** (Roma/Torino/Bologna/Firenze/Venezia hanno CKAN): espande il master con licenze comunali oltre OSM (come Milano). OSM-only qui = nomi puliti, alta qualità.
- **opening_hours**: la maggioranza è `typical_by_type` (OSM ha hours reali per ~15-20%). Affinabile via siti propri / crowdsourcing.
- **città mancanti** (se <6): re-run `python3 scripts/agent7_city.py <Città>` — pipeline pronto.

## 7. File consegnati

- `raw_sources/agent7_roma_venues_no_price.csv`
- `raw_sources/agent7_napoli_venues_no_price.csv`
- `raw_sources/agent7_torino_venues_no_price.csv`
- `raw_sources/agent7_firenze_venues_no_price.csv`
- `raw_sources/agent7_bologna_venues_no_price.csv`
- `raw_sources/agent7_venezia_venues_no_price.csv`
- `scripts/agent7_city.py` (pipeline parametrico) · `scripts/agent7_s8_report.py`

> Riusa `normalization.py` (CITY_BBOX/is_in_city, già estesa dal CEO) + `agent6/agent7_standardize.py`. NON tocca `data/`. Schema con `city` obbligatorio popolato.
