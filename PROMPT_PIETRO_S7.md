# Prompt Pietro — Sessione S7: Discovery comune/CKAN/OSM → set drink Milano classificato & deduplicato (02/06/2026)

> **OBIETTIVO STRATEGICO**
> Trasformare il bacino di **discovery open-data** (~13.700 righe grezze in 3 file: comune_osm + CKAN Comune Milano + OSM Overpass) in **un set TARGET drink Milano pulito**: con **nome commerciale recuperato**, **classificato** (TARGET/NO_TARGET/AMBIGUOUS), **tipizzato** (venue_type), **arricchito** (website/phone da OSM) e soprattutto **DEDUPLICATO** — cross-source *e* contro il DB esistente.
>
> Il risultato alimenta il layer "Prezzo non disponibile — Contribuisci" del frontend, con filtro per quartiere (NIL). **Quality > quantity**: meglio 2.500 venues puliti e non-doppi che 13.000 grezzi pieni di duplicati e ristoranti.

S7 è la naturale prosecuzione di S6 (che ha standardizzato i 1.441 no-price **già nel DB**). S7 lavora i venues di discovery **NON ancora nel DB**, lasciati esplicitamente fuori da S6.

---

## CONTESTO E NUMERI

### I tre file di discovery (in `raw_sources/`)

| File | Righe | Nome commerciale | Geo | Website/Phone | Note |
|---|---:|---|---|---|---|
| `ckan_milano_drink_venues_no_price.csv` | **3.804** | ✅ 3.803 con nome reale | ✅ preciso + CAP + NIL | ❌ | **Gold source**: CKAN ufficiale `dati.comune.milano.it`, già con `venue_type` + `nil_quartiere` + campi `_osm_*` |
| `comune_osm_venues.csv` | **4.649** | ⚠️ **3.270 = `[bar non identificato]`** | ✅ preciso | ❌ | Versione più vecchia, in gran parte placeholder. Utile solo per i ~1.379 nominati non in CKAN |
| `osm_milano_drink_overpass.csv` | **5.229** | ✅ 5.229 con nome | ✅ preciso | ✅ **1.477 website + 1.382 phone** | OSM raw: `name,lat,lon,amenity,cuisine,website,phone`. Porta i metadati che a CKAN mancano |

### Composizione OSM Overpass per `amenity`
`restaurant 2.805` (→ **NO_TARGET**) · `cafe 1.580` · `bar 606` · `pub 183` · `nightclub 55` (→ **TARGET ~2.424**)

### CKAN `venue_type` già presente (license-derived, da rivalidare)
`cafe 2.620 · bar 848 · pub 317 · cocktail_bar 19`

### Overlap (perché la dedup è il cuore di S7)
- **2.845 / 3.804** venues CKAN hanno un venue OSM Overpass entro ~30 m → name-recovery + dedup ad alto potenziale.
- comune_osm e CKAN derivano dalla **stessa anagrafica licenze Comune** → fortissima sovrapposizione (es. *Piazza Bandiera 13* = `[bar non identificato]` in comune_osm ma **`Altrè`** in CKAN, stesse coordinate).
- Tutti e tre vanno deduplicati anche **contro il DB**: 161 venues prezzati + 824 no-price già consegnati da S6 (`agent6_venues_no_price.csv`) + il master CEO `data/unified_venues_no_price.csv` (4.124).

### Riferimento: ricerca notturna CEO
`NIGHT_RESEARCH_REPORT.md` definisce l'hand-off per Pietro S7:
1. **CKAN cross-ref OSM Overpass** per recuperare il nome commerciale (yield atteso 1.000–1.500).
2. **Cluster CKAN + DB** per dedup nominale.
3. (Opzionale) **TheFork metadata bulk** via `curl_cffi` `impersonate='safari17_2_ios'` (bypass Datadome 403, solo metadata, no prezzi).

---

## SETUP (macOS — ignora path Windows e prefisso `website/`)

```bash
cd ~/Desktop/FindMyDeal_clone
git pull --rebase origin main
```

**OBBLIGATORIO leggere/riusare (NON duplicare logica):**
- `AGENTS.md`, `AGENTS_STATE.md`, `scripts/SCHEMA_AGENTI.md`
- `scripts/normalization.py` → `is_milan_or_unknown`, `PRICE_RANGES`
- `scripts/agent6_standardize.py` → **riusa così com'è**: `classify_venue`, `detect_venue_type`, `norm_name`, `clean_display_name`, `is_junk_name`, `sanitize_milan_address`, `fix_mojibake`, `MILAN_BBOX`, `DUOMO`
- `NIGHT_RESEARCH_REPORT.md` (tecniche + hand-off)

```python
import sys; sys.path.insert(0, 'scripts')
from normalization import is_milan_or_unknown
from agent6_standardize import (classify_venue, detect_venue_type, norm_name,
    clean_display_name, is_junk_name, sanitize_milan_address, fix_mojibake, MILAN_BBOX)
```

Output dir: `raw_sources/` · Prefisso file: `agent7_*` · Script: `scripts/agent7_*.py`

---

## STEP 1 — INVENTORY & SOURCE RECONCILIATION

Carica i 3 file + il DB. Stabilisci per ogni sorgente: schema, n. righe, % con nome reale, % con geo in bbox, % con website/phone. Stampa una tabella di riconciliazione. Identifica i campi-chiave per il merge:
- geo (lat/lon) — presente ovunque, **chiave primaria di dedup**
- nome commerciale — presente in OSM + CKAN, assente in comune_osm placeholder
- `nil_quartiere` (solo CKAN) — da propagare al canonical
- `amenity`/`cuisine` (solo OSM) — segnale di classificazione
- `categories` license (CKAN/comune) — segnale di classificazione

---

## STEP 2 — NAME RECOVERY (cross-ref geografico OSM Overpass)

Per ogni venue **senza nome commerciale** (placeholder `[bar non identificato]`, o `venue_name` = indirizzo/licenziatario), cerca il venue OSM Overpass più vicino:

```
match se distanza(haversine) ≤ 35 m  AND  amenity OSM ∈ {bar,pub,cafe,nightclub}  (no restaurant)
→ adotta il name OSM come nome commerciale
```

- Se più OSM nel raggio → prendi il più vicino con amenity drink.
- Registra `name_source ∈ {osm_overpass, ckan, comune_license, placeholder}` per provenance.
- **Yield atteso**: 1.000–1.500 nomi recuperati (CEO stima). Riporta il numero reale.

> ⚠️ I nomi CKAN/comune possono essere **ragione sociale del licenziatario** (persona/azienda), non l'insegna. Se il nome OSM è disponibile, **preferiscilo**. Se nessun nome reale è recuperabile e resta solo un placeholder → marcare `name_source=placeholder` (gestito nel quality gate, Step 7).

---

## STEP 3 — TARGET CLASSIFICATION (riusa + estendi)

Priorità dei segnali (dal più forte al più debole):

1. **OSM `amenity`** (segnale fortissimo):
   - `restaurant` → **NO_TARGET** (salvo nome con keyword bar/cocktail forte)
   - `bar`, `pub`, `cafe`, `nightclub` → **TARGET**
2. **`categories` license Comune** → mappa drink:
   ```python
   DRINK_LICENSE = {
     'f - bar caffè e simili','e - bar gastronomici e simili',
     'g - bar pasticceria, bar gelateria','h - wine bar, birreria, pub enoteche',
     'i - disco bar, america bar','j - discoteche, sale da ballo',
   }
   ```
   Categorie ristorazione (`a - ristorante`, `b - …`) → NO_TARGET.
3. **`classify_venue(nome, categories)`** di agent6 (fallback su nome+keyword).

Regola di combinazione: amenity `restaurant` **batte** una license bar generica (i locali con licenza "bar" ma amenity OSM "restaurant" sono ristoranti). In caso di conflitto reale → `AMBIGUOUS_TO_REVIEW`.

**Attenzione**: la licenza Comune "Bar caffè e simili" è larghissima e include attività che NON sono bar drink (es. tabaccherie con caffè, edicole-bar). Filtra aggressivo i NO_TARGET; nel dubbio AMBIGUOUS, mai TARGET assertito.

---

## STEP 4 — venue_type (riusa + mappe sorgente)

1. `detect_venue_type(nome, categories)` di agent6 (categories-aware).
2. Override/refine con OSM `amenity`: `pub`→pub, `nightclub`→cocktail_bar, `cafe`→cafe, `bar`→cafe (default IT).
3. Mappa license Comune → tipo (come `DRINK_LICENSE` sopra, es. `h - wine bar…`→wine_bar/pub, `i - disco bar`→cocktail_bar).
4. `cuisine` OSM se utile (es. `cuisine=coffee_shop`→cafe).

Obiettivo: minimizzare `unknown`, rappresentare il più possibile i 9 tipi.

---

## STEP 5 — DEDUP CROSS-SOURCE + vs DB ⭐ (il cuore di S7)

**Doppia dedup obbligatoria.** I 3 file si sovrappongono pesantemente fra loro e col DB.

### 5a. Geo-fingerprint (chiave primaria)
```python
def geo_key(lat, lon):
    return (round(float(lat), 4), round(float(lon), 4))   # ~11 m
```
Cluster per `geo_key` con tolleranza: due venues entro **~30–40 m E norm_name simile (o uno placeholder)** = stesso locale. Usa anche `SequenceMatcher` sui norm_name per i borderline. **Non** fondere due insegne diverse alla stessa via (es. civici condivisi) → richiedi name-match o placeholder.

### 5b. Canonical per cluster
- **Nome**: OSM commercial > CKAN named > comune license-holder > placeholder (usa `formality_score`/`clean_display_name` di agent6).
- **Geo**: la più precisa (preferisci OSM/CKAN concordi).
- **Metadata**: union → website/phone da OSM, `nil_quartiere` da CKAN, `categories` license, `amenity`.
- `all_names` = tutte le varianti con `|`; `source_provenance` = sorgenti unite.

### 5c. Relazione col DB esistente (ESCLUDI vs SUPERSEDE — distinzione critica)
- **ESCLUDI** (sono già coperti, NON rimetterli): venues in `unified_prices.csv` (hanno prezzo, già sulla mappa) e in `agent6_venues_no_price.csv` (già standardizzati da S6 — match per norm_name **e** geo_key).
- **SUPERSEDE, NON escludere**: il master CEO `data/unified_venues_no_price.csv` contiene **2.867 venues CKAN grezzi** (senza target_classification, dedup o nome recuperato). Questi sono **proprio l'oggetto di S7**: vanno **processati e migliorati**, non scartati. L'output `agent7_*` è la versione pulita che il CEO userà per **sostituire/aggiornare** quelle righe grezze nel suo master. → **NON usare `unified_venues_no_price.csv` come filtro di esclusione.** Riporta l'overlap (quanti agent7 corrispondono a righe grezze del master) così il CEO sa cosa rimpiazzare.

Riporta il **dedup ratio**: righe grezze in ingresso (≈13.700) → cluster unici cross-source → output finale (dopo esclusione dei soli priced + agent6). Il "net-new" è inteso **rispetto al DB reale** (prezzi + agent6), non rispetto all'assorbimento grezzo CKAN del master CEO.

---

## STEP 6 — Discovery TheFork massiva (OBBLIGATORIO)

Discovery **a tappeto** dei venues TheFork Milano (metadata, NO prezzi). `curl_cffi` con `impersonate='safari17_2_ios'` bypassa Datadome 403 (vedi NIGHT_RESEARCH; chrome/edge → 403). `pip install curl_cffi` se mancante.

**Discovery URL (multi-canale, esaustivo — non fermarsi al primo che funziona):**
1. `sitemap.xml` / sitemap index di thefork.it e thefork.com → filtra URL `/restaurant/...` con città Milano.
2. Pagine listing/search Milano **paginate** (es. `thefork.it/citta/milano-*`, per quartiere/cucina) → estrai link `/restaurant/{slug}-r{id}`.
3. **Wayback CDX** (`matchType=prefix` su `/restaurant/`) come integrazione (agent4 ne prese 77).
4. Cross-ref: per i venues TARGET già noti senza fonte TheFork, prova a costruire/verificare lo slug.

**Per ogni venue**: fetch SSR con `safari17_2_ios`, estrai JSON-LD `Restaurant` (name, address, geo, rating, telephone). **NESSUN prezzo** (menu via Apollo/JS lazy — confermato NIGHT_RESEARCH). Filtra Milano (bbox + CAP), poi passa dallo **stesso** classify (Step 3) + venue_type (Step 4) + dedup (Step 5).

Rate **2–5 s/req**, stop+log su 403 ripetuti, **salva incrementale + resumable**, cache HTML in dir gitignored (`raw_data/` o `.agent7_thefork_cache/`). Confluisce in `agent7_venues_no_price.csv` con `source_platform=thefork`, `name_source=thefork`.

---

## STEP 7 — METADATA ENRICHMENT (bounded, no overwrite)

### 7.1 — OPENING HOURS ⭐ OBBLIGATORIO per TUTTI i venues
**Requisito CEO: ogni venue in output DEVE avere un `opening_hours` valorizzato** — orario reale dove disponibile, altrimenti una **fascia oraria indicativa per `venue_type`**. Nessun venue con `opening_hours` vuoto.

Cascata (priorità):
1. **OSM `opening_hours`** — **re-query Overpass includendo il tag `opening_hours`** (la `osm_milano_drink_overpass.csv` attuale non lo contiene): `node/way["amenity"~"^(bar|pub|cafe|nightclub|biergarten)$"](area Milano); out center tags;`. Join per geo/nome → adotta l'orario reale OSM (formato spec OSM, es. `Mo-Su 07:00-20:00`).
2. **TheFork JSON-LD** `openingHours` dove presente.
3. **Fallback `typical_by_type`** (fascia indicativa realistica Milano) per chi resta senza orario reale:
   ```
   cafe          Mo-Su 07:00-20:00      cocktail_bar  Mo-Su 18:00-02:00
   pub           Mo-Su 17:00-02:00      wine_bar      Mo-Su 17:00-00:00
   aperitivo_bar Mo-Su 17:00-22:00      bistro        Mo-Su 12:00-00:00
   craft_beer    Mo-Su 17:00-01:00      rooftop       Mo-Su 18:00-01:00
   hotel_bar     Mo-Su 11:00-00:00      unknown       Mo-Su 08:00-22:00
   ```
Traccia la provenienza in **`opening_hours_source ∈ {osm, thefork, typical_by_type}`** così il frontend mostra "orario indicativo" per i typical. **Mai inventare un orario reale**: la fascia è dichiaratamente tipica.

### 7.2 — Altri campi (no overwrite)
- **website/phone**: dai campi OSM Overpass (gratis, già nel file) → riempi i vuoti dei canonical matchati.
- **address**: già presente (Comune) o reverse-geocode (Nominatim, 1.2 s) solo per i pochi senza address ma con geo reale; **sanitizza CAP non-20xxx e mojibake** con le funzioni agent6.
- **NON** scrapare prezzi (fuori scope). **NON** sovrascrivere dati esistenti.

---

## STEP 8 — OUTPUT

### File 1 — `raw_sources/agent7_venues_no_price.csv`
Schema esteso (compatibile agent6 + campi discovery):
```
source_platform, source_venue_id, venue_name, venue_url, address, city,
latitude, longitude, categories, price_tier, rating, rating_count,
phone, website, opening_hours, has_menu, menu_url, extraction_status, retrieved_at,
venue_type, target_classification, has_price, geocoding_confidence,
all_names, nil_quartiere, name_source, source_provenance, opening_hours_source
```
`has_price=False` per tutti. `opening_hours` **sempre valorizzato** (vedi 7.1). Solo **TARGET + AMBIGUOUS_TO_REVIEW** (no NO_TARGET).

### File 2 — `raw_sources/agent7_dedup_map.csv`
`canonical_name, all_variants, geo_key, source_provenance, cluster_size, dropped_reason`
(traccia cosa è stato fuso e cosa scartato come già-in-DB).

### File 3 — `agent7_REPORT.md`
- Riconciliazione 3 sorgenti (righe in → cluster → net-new).
- Nomi commerciali recuperati (cross-ref OSM).
- TARGET / NO_TARGET / AMBIGUOUS.
- Distribuzione venue_type.
- **Dedup ratio** cross-source + vs DB (numero di doppioni evitati).
- Copertura NIL quartiere + CAP.
- Coverage website/phone aggiunti.
- Issues residui / TODO.

---

## STEP 9 — QUALITY GATE (mandatory, inline)

Per ogni venue in output:
- ❌ NON già in DB **reale** (priced `unified_prices` / `agent6_venues_no_price`) — per norm_name **e** geo_key. (NB: `unified_venues_no_price.csv` del CEO si **supersede**, non si esclude — vedi 5c.)
- `is_milan_or_unknown(address) == True`.
- lat/lon dentro `MILAN_BBOX` (45.39–45.54, 9.04–9.28).
- `target_classification ∈ {TARGET, AMBIGUOUS_TO_REVIEW}` (no NO_TARGET).
- `not is_junk_name(venue_name)`.
- nome pulito (no HTML/URL/pipe; mojibake riparato; CAP `.0` rimosso).
- **placeholder-only name** (`[bar non identificato]` senza recovery) → ammesso **solo** se ha geo+address validi, marcato `name_source=placeholder` per UI ("Bar in Via X" generico). Altrimenti scarta.
- **`opening_hours` NON vuoto** (reale OSM/thefork o `typical_by_type`) — requisito CEO, vedi 7.1.
- Ogni cluster = **1 sola riga canonical**.

```python
def quality_gate(v, in_db_norm, in_db_geo):
    if norm_name(v['venue_name']) in in_db_norm or v['geo_key'] in in_db_geo:
        return False, 'ALREADY_IN_DB'
    if not is_milan_or_unknown(v.get('address','')): return False, 'NON_MILAN_CAP'
    # ... bbox, NO_TARGET, junk, placeholder ...
    return True, None
```

---

## RATE LIMITS

| Servizio | Rate |
|---|---|
| OSM Overpass | **già scaricato** (file locale) — niente nuove chiamate |
| Nominatim (reverse, solo gap) | 1.2 s/req, bbox Milano |
| curl_cffi TheFork (opzionale) | 2–5 s/req, stop su 403 |
| Website fetch (se serve) | 2 s/GET |

---

## TARGET MISURABILI S7

| Metrica | Target |
|---|---|
| Nomi commerciali recuperati (cross-ref OSM) | ≥ 1.000 |
| Venues TARGET classificate (con venue_type), net-new vs DB reale (prezzi+agent6) | ≥ 2.000 |
| **Dedup ratio** documentato (grezzi → cluster → net-new) | obbligatorio |
| Doppioni vs DB evitati | tutti (0 venue già in DB nell'output) |
| venue_type | ≥ 8/9 tipi reali rappresentati |
| Copertura NIL quartiere | tutti i NIL con ≥3 venues, ≥70 NIL |
| **opening_hours coverage** ⭐ OBBLIGATORIO | **100%** (reale OSM/thefork o typical_by_type) |
| website/phone aggiunti da OSM | realistico: ceiling ~350/~410 in OSM drink (no restaurant), ~120/~260 dopo dedup+DB |
| **TheFork discovery** (metadata Milano, no prezzi) — OBBLIGATORIO | ≥ 100 venues |

---

## ERRORI DA NON RIPETERE (lesson learned)

- ❌ **NON duplicare venues già nel DB** (priced 161 + agent6 824 + unified_venues_no_price 4.124) — dedup per norm_name **E** geo_key.
- ❌ **NON tenere placeholder `[bar non identificato]`** senza geo+address o senza recovery nome.
- ❌ **NON includere ristoranti** (OSM amenity=restaurant 2.805) — sono NO_TARGET.
- ❌ **NON fidarsi della sola license Comune** ("Bar caffè" è larga) — incrocia con amenity OSM.
- ❌ **NON saltare la geo-fingerprint dedup** — le 3 sorgenti si sovrappongono al ~75%.
- ❌ **NON bypassare `normalization.py` / `agent6_standardize.py`** — riusa, non riscrivere.
- ❌ **NON scrapare prezzi** (Playwright/IP residenziale richiesti — fuori scope).

---

## CONSEGNA

```bash
cd ~/Desktop/FindMyDeal_clone
git pull --rebase origin main
git add raw_sources/agent7_*.csv agent7_REPORT.md scripts/agent7_*.py
git commit -m "data: S7 discovery comune/CKAN/OSM — N venues TARGET net-new, M nomi recuperati, dedup ratio X"
git push origin main
```
**NON toccare**: `data/unified_*.csv`, `data/unified_venues_no_price.csv`, `prices_data.json`, `index.html`, vertical beach. (Il CEO integra `agent7_*` nel suo master.)

### Report sintetico per CEO
- N venues TARGET net-new (per venue_type) + N nomi commerciali recuperati.
- Dedup ratio (grezzi → cluster → net-new) e doppioni vs DB evitati.
- Copertura NIL quartiere + website/phone aggiunti.
- Issues residui / decisioni che servono al CEO.

---

## USE CASE FRONTEND

I venues TARGET no-price diventano pin "Prezzo non disponibile — Contribuisci", **filtrabili per quartiere (NIL)**. Con i nomi commerciali recuperati (non più "[bar non identificato]") e website/phone da OSM, il popup è informativo da subito:

> 🍸 **Altrè** · Cafe · Piazza Bandiera 13 · Brera
> Prezzo non disponibile — *Contribuisci per primo* · ☎ tel · 🌐 sito

---

## BACKLOG NON SCOPE S7

- ❌ Prezzi nuovi (richiedono Playwright + IP residenziale — TheFork/Glovo live).
- ❌ Vertical beach.
- ❌ UI frontend (è Peppe).
- ❌ `data/unified_*.csv` e `data/unified_venues_no_price.csv` (territorio CEO).
- ❌ Discovery Quandoo/Michelin (URL changed — richiede nuove tecniche, vedi NIGHT_RESEARCH).

Buon lavoro Pietro. L'obiettivo è il **bacino discovery del Comune trasformato in venues drink puliti, nominati e non-doppi** — la base "no price yet" più grande e autorevole della mappa, pronta per il crowdsourcing.
