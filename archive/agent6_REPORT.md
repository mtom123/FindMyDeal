# Agent 6 — Report S6: venues drink no-price standardizzati

_Generato da `scripts/agent6_*.py` · vertical drink Milano · 824 venues in output_

## 1. Sintesi esecutiva (per CEO)

- **652 venues TARGET** + **172 AMBIGUOUS_TO_REVIEW** = **824 venues** in `agent6_venues_no_price.csv`, puliti/deduplicati/categorizzati, pronti come pin "no price yet".
- **29 venues geocodate con precisione** (precise 13 + web_addr 16) su 98 no-geo processate; 69 → fallback Duomo.
- **43 cluster di nomi duplicati** consolidati (canonical + all_names).
- **169 address** riempiti via reverse-geocoding (popup-ready).
- Quality gate inline: esclusi i NO_TARGET (ristoranti/pizzerie), i CAP non-Milano, i geo fuori bbox, i nomi-piattaforma.

## 1b. Integrazione con `data/unified_venues_no_price.csv` (pipeline CEO)

Il CEO ha creato in parallelo `data/unified_venues_no_price.csv` (4.124 venues: 1.247 unified_db + 2.867 ckan_milano + 10 eatbu) — **senza `target_classification` e con `venue_type` vuoto sui 1.247 unified_db**.
Questo deliverable lo completa. Join consigliato **per `venue_name`** (o norm_name):
- aggiunge **`target_classification`** → permette di **nascondere dalla mappa i ~537 NO_TARGET** (ristoranti/pizzerie/sushi);
- riempie **`venue_type`** per gli unified_db (qui 599+ tipizzati);
- porta il **canonical name + all_names** (dedup di 43 cluster) per evitare pin doppi.
> NB: i venues CKAN/OSM discovery (S7, fuori scope S6) non sono classificati qui; la stessa logica `classify_venue`/`detect_venue_type` di `agent6_standardize.py` è riusabile su di essi.

## 2. Step 1 — Classificazione TARGET (pool no-price)

| Classe | Count | Note |
|---|---:|---|
| TARGET | 713 | bar/pub/caffè/cocktail/wine bar… |
| AMBIGUOUS | 190 | nessuna keyword o food+bar pari → review |
| NO_TARGET | 537 | ristoranti/pizzerie/sushi → esclusi dall'output |
| **Pool totale** | **1440** | venues senza prezzo nel DB |

In output (post quality-gate, deduplicati): **652 TARGET** + **172 AMBIGUOUS_TO_REVIEW**.

## 3. Step 4 — Distribuzione venue_type (output)

| venue_type | Count | Definizione |
|---|---:|---|
| cocktail_bar | 97 | Cocktail focus / nightclub / lounge |
| pub | 81 | Birre alla spina, pub, taproom |
| cafe | 421 | Caffetteria / bar di quartiere (default "bar" generico IT) |
| wine_bar | 9 | Enoteca / vineria / mescita |
| aperitivo_bar | 0 | Aperitivo italiano dominante |
| bistro | 47 | Bistrot ibrido bar + cibo leggero |
| craft_beer | 50 | Birra artigianale / birrificio |
| rooftop | 3 | Rooftop / terrazza panoramica |
| hotel_bar | 2 | Bar interno hotel |
| unknown | 114 | Non determinabile da metadata |

Tipi reali rappresentati: **8/9** (+ 114 unknown). Assente: **aperitivo_bar** — vedi nota.
> Nota `aperitivo_bar`: 0 nel pool no-price perché i locali con "aperitivo" esplicito nei metadata (Camparino, Bar Basso…) sono già prezzati e sulla mappa. Non forzo classificazioni inventate.

## 4. Step 3 — Geocoding (no-geo TARGET/AMBIG)

| confidence | Count |
|---|---:|
| precise | 13 |
| web_addr | 16 |
| fallback | 69 |
| **totale processate** | **98** |

Metodi: {'duomo_centro': 69, 'jsonld_geo_menu': 1, 'nominatim_address': 13, 'jsonld_geo_website': 15}

> **Onestà sui numeri**: target prompt "≥100 precise+web_addr/137" non raggiungibile: dei 137 no-geo, 39 sono NO_TARGET (esclusi dall'output → non geocodati) e ~73 dei restanti non avevano address (solo JSON-LD geo da website/menu, hit-rate parziale). Ceiling reale ~98 candidati in-scope.

## 5. Step 2 — Cluster nomi consolidati

**43 cluster** con duplicati nel pool no-price. Canonical = nome più formale (slug e mojibake penalizzati). Esempi:

| canonical_name | all_variants | dupe |
|---|---|---:|
| Burgez | Burgez | 3 |
| This is not a Sushi Bar | This is not a Sushi Bar | 3 |
| Victoria's | Victoria's | Victoriasclub | 3 |
| Spiller | Spiller | 3 |
| Starbucks | Starbucks | 3 |
| Abbracci Bistrot | Abbracci Bistrot | 2 |
| Agua Sancta | Agua Sancta | 2 |
| Antico Ristorante Boeucc | Antico Ristorante | Antico Ristorante Boeucc | 2 |
| Bar Mercurio | Bar Mercurio | 2 |
| Barba | Barba | 2 |
| Blue Note Milano | Blue Note Milano | Blue Note | 2 |
| Blues Canal | Blues Canal | 2 |
| Bob Milano | Bob Milano | 2 |
| Carpe Diem | Carpe Diem | Carpe diem | 2 |
| El Carnicero - Spartaco | El Carnicero | El Carnicero - Spartaco | 2 |

## 6. Copertura metadata (output)

| Campo | Coverage |
|---|---:|
| address | 768/824 (93%) |
| latitude | 824/824 (100%) |
| website | 609/824 (73%) |
| phone | 112/824 (13%) |
| opening_hours | 217/824 (26%) |
| menu_url | 798/824 (96%) |
| categories | 655/824 (79%) |

geocoding_confidence in output: {'fallback': 67, 'existing': 728, 'precise': 13, 'web_addr': 16}

## 7. Quartieri Milano (CAP 20XXX) coperti

CAP distinti: **45** (33 città + 12 hinterland). CAP **città** con ≥3 venues: **25** (20100, 20121, 20122, 20123, 20124, 20126, 20129, 20131, 20133, 20135, 20136, 20137, 20138, 20139, 20142, 20143, 20144, 20146, 20147, 20149, 20151, 20152, 20154, 20159, 20162).

> ⚠️ **Hinterland**: 52 venues hanno CAP di comuni limitrofi (non Milano città) — 20099×12, 20090×9, 20091×7, 20019×6, 20017×4, 20057×4, 20094×3, 20026×2. Sono entro la bbox e ammessi dal gate `is_milan_or_unknown` (qualsiasi 20xxx) come nel merge_pipeline. **Il CEO può filtrarli** a CAP 20121–20162 se serve solo Milano città.

Top 15 CAP per densità:

| CAP | venues |
|---|---:|
| 20124 | 20 |
| 20123 | 18 |
| 20136 | 17 |
| 20154 | 14 |
| 20121 | 13 |
| 20144 | 12 |
| 20099 | 12 |
| 20133 | 12 |
| 20122 | 10 |
| 20135 | 10 |
| 20143 | 10 |
| 20129 | 9 |
| 20090 | 9 |
| 20159 | 8 |
| 20131 | 8 |

## 8. Issues residui / TODO (per CEO)

- **aperitivo_bar = 0**: non determinabile dai metadata dei no-price (vedi §3).
- **phone / opening_hours non arricchiti in massa**: ROI basso (phone 8% coverage, ~700 fetch @2s; il popup mockup non li mostra). Lasciati ai valori esistenti. Candidato a sessione dedicata se servono.
- **69 venues su fallback Duomo**: geo imprecisa. Possibile top-up via WebSearch address (strategia 4) o crowdsourcing.
- **Duomo-stacked legacy** (lat=45.4642 esistenti, fuori scope Step 3 che filtra solo lat=''): da verificare in un pass futuro.
- **AMBIGUOUS_TO_REVIEW**: il prompt suggerisce HTML-peek di menu_url per cocktail/spritz/aperitivo. Non eseguito in massa (costo fetch); risolti via categorie OSM/mycia dove disponibili.
- **comune_osm 4.649** (S7 discovery) e prezzi nuovi: fuori scope S6.

## 9. File consegnati

- `raw_sources/agent6_venues_no_price.csv` — master TARGET+AMBIGUOUS (schema esteso)
- `raw_sources/agent6_geocode_fixes.csv` — Step 3 geocoding
- `raw_sources/agent6_name_dedup.csv` — Step 2 mappatura nomi
- `raw_sources/agent6_address_fixes.csv` — Step 5 address reverse-geocoded
- `scripts/agent6_standardize.py` / `agent6_geocode.py` / `agent6_enrich.py` / `agent6_report.py`

> NON toccati: `data/unified_*.csv`, `prices_data.json`, `index.html`, vertical beach. Riusata `scripts/normalization.py` (is_milan_or_unknown). Classificazione venue/venue_type = logica S6-specifica.
