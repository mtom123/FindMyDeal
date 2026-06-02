# Prompt Pietro — Sessione S6: Standardizzazione venues drink SENZA prezzo (02/06/2026)

> **OBIETTIVO STRATEGICO**
> Sistemare il bacino di 1.441 venues drink Milano che sono nel DB **ma non hanno prezzo associato**.
> Il frontend SurPrice mostrerà questi pin con badge "Prezzo non disponibile — Contribuisci" (bridge a futuro crowdsourcing).
>
> **Tu NON cerchi nuove venues né nuovi prezzi**. Standardizzi metadata, geocodi i mancanti, deduplichi, categorizzi per tipo locale.

---

## CONTESTO E NUMERI

| Metrica | Valore |
|---|---|
| Venues totali DB drink | **1.601** |
| Venues con prezzo (mappa attuale) | 153 (9.6%) |
| **Venues SENZA prezzo (target S6)** | **1.441 (90.0%)** |
| Con geo precisa (lat/lon) | 1.304 (90.5%) |
| Senza geo | **137** (9.5%) |
| Con website | 738 (51%) |
| Con phone | 120 (8.3%) |
| Con menu_url | 1.410 (97.8%) |

**Breakdown source (venues senza prezzo):**

| Source | Count | Note |
|---|---|---|
| mycia | 593 | Mix di bar/ristoranti — serve filtro target |
| web_extract | 475 | comune_osm nomi nuovi, scrape esistente ma 0 prezzi |
| direct_website | 234 | Sito noto ma menu non estraibile |
| menudigitale | 80 | Vetrina Italia, alcuni Milano |
| thefork | 28 | Wayback metadata only |
| leggimenu | 16 | Pagine prezzo non disponibili |
| eatbu | 10 | Sitemap discovered ma no prezzi |
| altri | 5 | pdf_dork, glovo, other |

Plus disponibile come backlog discovery: `raw_sources/comune_osm_venues.csv` = 4.649 venues open data Comune Milano (categorizzati "Bar caffè", nome=licenza non commerciale).

---

## SETUP

```bash
cd ~/percorso/SurPrice
git pull origin main

# OBBLIGATORIO leggere:
cat website/AGENTS.md
cat website/AGENTS_STATE.md
cat website/scripts/normalization.py    # ⭐ NUOVA libreria condivisa (importa SEMPRE)
cat website/scripts/SCHEMA_AGENTI.md
```

**REGOLA OPERATIVA**: usa `scripts/normalization.py` per ogni validazione. Non duplicare logica.

```python
import sys
sys.path.insert(0, 'website/scripts')
from normalization import is_milan_or_unknown, clean_item_product, validate_item, PRICE_RANGES
```

Output dir: `website/raw_sources/`
Prefisso file: `agent6_*`

---

## STEP 1 — AUDIT VENUE TYPE (TARGET vs NO_TARGET)

I 1.441 venues senza prezzo NON sono tutti target del progetto drink. Esempi:
- "Burgez" = burger restaurant, NO target
- "Antica Pizzeria da Giulio" = pizzeria, NO target
- "Bar Magenta" = bar, **TARGET**
- "Caffè Letterario" = caffetteria, **TARGET**
- "Cocktail Bar X" = cocktail, **TARGET**

**Crea classificatore basato su nome + categories field:**

```python
TARGET_KEYWORDS = [
    'bar', 'pub', 'caffè', 'caffe', 'cafe', 'café', 'cocktail', 'bistrot', 'bistro',
    'lounge', 'wine bar', 'enoteca', 'taproom', 'birreria', 'speakeasy',
    'aperitivo', 'rooftop', 'tap house', 'cocktail lab'
]
NO_TARGET_KEYWORDS = [
    'pizzeria', 'ristorante', 'sushi', 'trattoria', 'osteria', 'focacceria',
    'panini', 'panino', 'rosticceria', 'gelateria', 'pasticceria', 'tacos',
    'kebab', 'noodle', 'poke', 'hamburger', 'burger', 'tortilleria', 'ramen',
    'piadina', 'pizz', 'pollo', 'fritti'
]

def classify_venue(venue_name, categories=''):
    n = (venue_name + ' ' + categories).lower()
    target_hits = sum(1 for kw in TARGET_KEYWORDS if kw in n)
    no_hits = sum(1 for kw in NO_TARGET_KEYWORDS if kw in n)
    if no_hits > target_hits:
        return 'NO_TARGET'
    if target_hits > 0:
        return 'TARGET'
    return 'AMBIGUOUS'  # da review (alcuni nomi puri tipo "Vittoria" o "Camparino")
```

**Stima output:**
- TARGET: ~700-800 venues bar/pub/caffè
- NO_TARGET: ~400-500 ristoranti/pizzerie (escludere dalla mappa drink)
- AMBIGUOUS: ~100-200 (review manuale o discovery menu)

**Per gli AMBIGUOUS**: visita rapidamente il `menu_url` o `website` (se presente), cerca keywords nel HTML: "cocktail", "spritz", "aperitivo", "drink menu", "bar"  → se hit, TARGET. Altrimenti AMBIGUOUS_TO_REVIEW.

---

## STEP 2 — STANDARDIZZAZIONE NOMI VENUE

Nel DB attuale ci sono **35+ cluster di nomi duplicati**: stessi venues scritti diversamente per source diverso.

**Esempi reali nel DB:**
- "Caffè Fernanda" / "Caffefernanda" / "caffefernanda" → **stessa venue**
- "Eatme&Go" / "Eatmeandgo" / "eatmego" → **stessa venue**
- "Caffè Inn" / "Caffè Inn International Bistrot" → **stessa venue**
- "Sun Strac" / "sunstrac" → **stessa venue**
- "Sui Generis" / "suigeneris.bar" → **stessa venue**
- "Lucaeandreabar" / "Luca & Andrea" → **stessa venue**
- "Morgante cocktail & soul" / "Morgantecocktail" → **stessa venue**

**Algoritmo deduplicazione:**

```python
import re, unicodedata
from difflib import SequenceMatcher

def norm_name(s):
    """Nome normalizzato per matching."""
    s = unicodedata.normalize('NFD', s.lower())
    s = ''.join(c for c in s if unicodedata.category(c) != 'Mn')  # rimuovi accenti
    s = re.sub(r'\.(it|com|net|org|bar)\b', '', s)  # rimuovi TLD
    s = re.sub(r'[^a-z0-9]', '', s)
    return s

def cluster_venues(venues):
    """Raggruppa venues con norm_name simile."""
    clusters = {}
    for v in venues:
        n = norm_name(v['venue_name'])
        if n not in clusters:
            clusters[n] = []
        clusters[n].append(v)
    # Cluster con >1 venue = dedup target
    return {k: vs for k, vs in clusters.items() if len(vs) > 1}
```

**Per ogni cluster:**
1. Identifica il "canonical name" — più completo/elegante (es. "Caffè Fernanda" non "caffefernanda")
2. Unifica metadata: prendi geo dal venue con geo, website dal venue con website, ecc.
3. Mantieni `all_names` array con tutte le varianti
4. **NON è dedup geo-fingerprint** (quello lo fa il merge_pipeline). Tu produci tabella di mappatura.

**Output: `agent6_name_dedup.csv`**

| canonical_name | all_variants | canonical_source_venue_id | dupe_count |
|---|---|---|---|
| Caffè Fernanda | Caffè Fernanda \| Caffefernanda \| caffefernanda | direct_website::caff_fernanda | 3 |

---

## STEP 3 — GEOCODING 137 VENUES SENZA GEO

Lista esatta: filtra `unified_venues.csv` dove `latitude=''`.

**Strategia per ogni venue:**

1. **Se ha address** → Nominatim con bbox Milano (`viewbox=9.04,45.39,9.28,45.54&bounded=1`)
2. **Se ha website** → fetch homepage, cerca JSON-LD `addressLocality`+`streetAddress`, poi Nominatim
3. **Se ha menu_url leggimenu/mycia** → fetch, cerca JSON-LD nella pagina
4. **Fallback WebSearch**: `"{venue_name}" milano indirizzo` → estrai address dalle SERP, poi Nominatim
5. **Ultimo fallback**: fallback Milano centro `45.4642, 9.1900` con flag `geocoding_confidence=fallback`

**Rate limit Nominatim**: 1.2s tra request, 1 req/sec hard limit.

**Output: `agent6_venue_geocode.csv`**

| venue_name | source_venue_id | old_lat | old_lng | new_lat | new_lng | confidence | method |
|---|---|---|---|---|---|---|---|

`confidence` = `precise` (Nominatim hit) | `web_addr` (WebSearch + Nominatim) | `fallback` (centro Milano).

**Target: 100-130 geocodate con precisione su 137 totali.**

---

## STEP 4 — CATEGORIZE LOCALE PER TIPO

Estendi schema venues con campo `venue_type` (nuovo):

| venue_type | Definizione | Esempi |
|---|---|---|
| `cocktail_bar` | Cocktail focus, signature drinks | LiQUIDO Rooftop, Morgante, Ugo Bar |
| `pub` | Birre alla spina dominant | Mulligan's, Tardis Pub, Banshee |
| `cafe` | Caffetteria, breakfast/lunch | Caffè Fernanda, B Cafè, Norin |
| `wine_bar` | Enoteca, vini al calice | La Cantinetta, La Vineria |
| `aperitivo_bar` | Italian aperitivo dominant | Camparino, Bar Basso, Terrazza Aperol |
| `bistro` | Hybrid bar + light food | Joy's, Trentase, Floraetlabora |
| `craft_beer` | Birra artigianale | Birrificio Lambrate, Myst, BAI |
| `rooftop` | Vista + cocktail | Ceresio 7, La Terrazza Duomo, LiQUIDO |
| `hotel_bar` | Bar interno hotel | UNAHOTELS Scandinavia, Hotel Ibis |
| `unknown` | Non determinabile da metadata |

**Detection logic** (priority order):

```python
def detect_venue_type(name, categories='', website='', menu_url=''):
    n = (name + ' ' + categories).lower()
    if 'rooftop' in n: return 'rooftop'
    if 'cocktail' in n or 'speakeasy' in n: return 'cocktail_bar'
    if any(k in n for k in ['pub', 'tap', 'birreria', 'taproom']): return 'pub'
    if 'craft' in n and 'beer' in n: return 'craft_beer'
    if any(k in n for k in ['wine bar', 'enoteca', 'vineria']): return 'wine_bar'
    if 'aperitivo' in n: return 'aperitivo_bar'
    if any(k in n for k in ['bistrot', 'bistro']): return 'bistro'
    if any(k in n for k in ['caffè', 'caffe', 'cafe', 'café']): return 'cafe'
    if any(k in n for k in ['hotel', 'unahotels', 'ibis']): return 'hotel_bar'
    return 'unknown'
```

---

## STEP 5 — METADATA ENRICHMENT (where missing)

Per ogni venue TARGET:

### 5.1 — Address completo
Se address mancante o incompleto, derivalo da:
- Nominatim reverse geocoding (lat/lon → address) se hai geo
- JSON-LD nel website
- WebSearch fallback

### 5.2 — Phone (solo se mancante)
Se website disponibile, fetch homepage e cerca pattern:
- `tel:` href
- `+39 02 \d{5,8}` regex
- JSON-LD `telephone`

### 5.3 — Opening hours (solo se mancante)
JSON-LD `openingHours`. Format: "Mo-Fr 18:00-02:00; Sa-Su 11:00-02:00".

**NON sovrascrivere mai** dati esistenti. Solo riempire vuoti.

---

## STEP 6 — OUTPUT STANDARDIZZATO

### File 1: `raw_sources/agent6_venues_no_price.csv`

Schema esteso vs SCHEMA_AGENTI.md standard:

```
source_platform, source_venue_id, venue_name, venue_url, address, city,
latitude, longitude, categories, price_tier, rating, rating_count,
phone, website, opening_hours, has_menu, menu_url,
extraction_status, retrieved_at,
venue_type, target_classification, has_price, geocoding_confidence, all_names
```

Campi nuovi:
- `venue_type` (cocktail_bar / pub / cafe / ... — vedi Step 4)
- `target_classification` (TARGET / NO_TARGET / AMBIGUOUS_TO_REVIEW)
- `has_price` = `False` per tutti (sono i no-price)
- `geocoding_confidence` (precise / web_addr / fallback)
- `all_names` (varianti unite con ` | `)

### File 2: `raw_sources/agent6_geocode_fixes.csv`
(Vedi step 3 output format)

### File 3: `raw_sources/agent6_name_dedup.csv`
(Vedi step 2 output format)

### File 4: `agent6_REPORT.md`

Sintesi:
- Venues processati TARGET vs NO_TARGET vs AMBIGUOUS
- Venues geocodate: precise / web / fallback
- Cluster nomi consolidati
- Distribuzione venue_type
- Top quartieri Milano coperti (raggruppa per zip code 20XXX)
- Issues residui / TODO future

---

## STEP 7 — QUALITY GATE (mandatory)

Per ogni venue scritta in output:

1. **NON in DB con prezzo** (skip se venue_name è già nel set `priced_venues`)
2. **`is_milan_or_unknown(address)` = True** (filter CAP non-Milano)
3. **lat/lon dentro bbox Milano** (lat 45.39-45.54, lon 9.04-9.28) se geo presente
4. **target_classification ∈ {TARGET, AMBIGUOUS_TO_REVIEW}** (no NO_TARGET nel output)
5. **`venue_name` pulito** (no HTML, no URL, no "Menu - X")
6. **Dedup**: ogni cluster nomi è 1 sola riga (canonical), con `all_names` array

```python
def quality_gate(venue):
    if venue['venue_name'].lower().strip() in priced_venues:
        return False, 'ALREADY_HAS_PRICE'
    if not is_milan_or_unknown(venue.get('address','')):
        return False, 'NON_MILAN_CAP'
    if venue.get('latitude'):
        try:
            lat, lon = float(venue['latitude']), float(venue['longitude'])
            if not (45.39 <= lat <= 45.54 and 9.04 <= lon <= 9.28):
                return False, 'OUT_OF_MILAN_BBOX'
        except: pass
    if venue.get('target_classification') == 'NO_TARGET':
        return False, 'NO_TARGET'
    return True, None
```

---

## RATE LIMITS

| Servizio | Rate |
|---|---|
| Nominatim | 1.2s tra req (hard limit) |
| WebSearch / Startpage | 5s tra query, max 20 consecutive |
| Website fetch (per metadata enrichment) | 2s tra GET |
| HTTP 429 → sleep 120s + retry una volta |
| HTTP 403 → skip venue, log |

---

## TARGET MISURABILI S6

| Metrica | Target |
|---|---|
| Venues TARGET classificate (con `venue_type`) | ≥ 700 |
| Venues geocodate (precise + web_addr) | ≥ 100 / 137 senza geo |
| Cluster nomi consolidati | ≥ 30 |
| Venues con address completo | ≥ 1.000 |
| Distribuzione venue_type | tutti i 9 tipi rappresentati |
| Quartieri Milano coperti | tutti i CAP 20100-20199 con ≥3 venues |

---

## ERRORI DA NON RIPETERE (lesson learned)

1. ❌ **Non includere venues con prezzo già nel DB** (sono 153, già sulla mappa)
2. ❌ **Non riassegnare nomi venue arbitrari** — preservare il nome "canonico" più formale (es. "Caffè Fernanda" non "caffefernanda")
3. ❌ **Non geocodare senza bbox Milano** — bbox check obbligatorio post-Nominatim
4. ❌ **Non includere NO_TARGET** (pizzerie/ristoranti) nel master no-price (usano altri vertical futuri se mai)
5. ❌ **Non bypassare normalization.py** — importa SEMPRE, non duplicare regole

---

## CONSEGNA

```bash
cd ~/percorso/SurPrice
git pull --rebase origin main
git add website/raw_sources/agent6_*.csv website/agent6_REPORT.md
git commit -m "data: S6 venues no-price standardizzati — N venues TARGET, M geocodate"
git push origin main
```

Report sintetico per CEO:
- N venues TARGET classificate (per venue_type)
- N venues geocodate (precise/web/fallback)
- N cluster nomi consolidati
- Issues residui / decisioni serve CEO

---

## USE CASE FRONTEND (cosa il CEO costruirà dopo)

I venues TARGET no-price diventeranno pin sulla mappa con badge:
> 🍸 **Bar Magenta**
> Cocktail bar · Via Carducci 13
> *Prezzo non disponibile — Contribuisci per primo*

Click → form crowdsourcing minimale (cocktail dropdown + prezzo + foto opzionale).

Quindi i metadati che produci ora (venue_type, address pulito, geo precisa, opening hours) servono direttamente al popup mappa. **Quality over quantity.**

---

## BACKLOG NON SCOPE S6

- ❌ Non scrapare prezzi nuovi (era S4/S5)
- ❌ Non aggiungere venues da comune_osm 4.649 (è discovery, è S7 futuro)
- ❌ Non toccare vertical beach
- ❌ Non costruire UI frontend
- ❌ Non aggiornare `data/unified_*.csv` (territorio CEO)

---

Buon lavoro Pietro. **L'obiettivo è una tabella venues TARGET pulita, deduplicata, geocodata, categorizzata — pronta per essere consumata dal frontend come pin "no price yet".**
