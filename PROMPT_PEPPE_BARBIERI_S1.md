# Prompt Peppe — Vertical Barbieri/Parrucchieri S1 (03/06/2026)

> **NUOVO VERTICAL**: SurPrice si espande oltre drink + balneari. Tu lanci il vertical Barbieri/Parrucchieri.
>
> **OBIETTIVO**: data scraping + frontend integration per vertical "Barbieri/Parrucchieri Milano" (poi Italia). Replica playbook Beach S1+Phase3 che hai già fatto.

---

## CONTESTO CALL ODIERNA

Decisione utente + team:
- SurPrice si espande a **3 vertical paralleli**:
  - 🍹 Drink (Pietro espande a 6 città Italia)
  - 💈 **Barbieri/Parrucchieri** (TU — Milano prima, poi Italia)
  - 💪 Palestre/Fitness (utente direttamente)
- Brand unico SurPrice multi-vertical (no spin-off)
- Crowdsourcing Supabase setup stasera (CEO + utente)

Tu hai il vertical più "verde" del progetto. Mercato:
- **€6B Italia** (parrucchieri €4.5B + barbieri €1.5B)
- **~50.000 saloni** Italia, ~3.500 Milano
- Frammentato locale, listini quasi mai online → opacità altissima = perfect SurPrice target

---

## STRUTTURA DELIVERY S1 (replica playbook tuo balneari)

| Phase | Cosa | Tempo |
|---|---|---|
| **Phase 1 — Master list** | OSM Overpass amenity=hairdresser/barber Milano + CKAN Comune | 2-3h |
| **Phase 2 — Provider discovery** | Treatwell/Wellry/Booksy/Fresha quali dominano IT? | 1-2h |
| **Phase 3 — Sample prezzi** | 20-30 saloni con listini scrapabili (siti propri/dish.co PDF) | 3-4h |
| **Phase 4 — Frontend integration** | Nuovo toggle Barbieri sulla mappa | 3-4h |
| **Report** | Schema validato, gap analysis | 1h |

**Totale stimato: 10-14h spalmate su 2 sessioni**.

---

## SETUP

```bash
cd ~/percorso/SurPrice
git pull origin main
```

**OBBLIGATORIO leggere**:
- `AGENTS.md`, `AGENTS_STATE.md`, `CHANGELOG.md`
- `scripts/normalization.py` (libreria condivisa quality gate)
- `scripts/SCHEMA_AGENTI.md` (schema CSV)
- `beach_s1_REPORT.md` (riferimento playbook tuo)
- `PROMPT_PEPPE_BEACH_S1.md` (tuo prompt storico, riusa struttura)

Working dir: `raw_sources/` · Prefisso: `barber_s1_*` · Script: `scripts/barber_s1_*.py`

---

## PHASE 1 — MASTER LIST BARBIERI/PARRUCCHIERI MILANO

### Fonti

| Fonte | Tag/Query | Stima venues |
|---|---|---|
| **OSM Overpass** | `amenity=hairdresser` + `shop=hairdresser` + `shop=beauty` | ~1.500-3.000 Milano |
| **CKAN Comune Milano** | dati.comune.milano.it categoria "Acconciatore" / "Estetista" | ~2.000-3.500 |
| **Google Maps Places API** (free $200 tier) | category=hair_salon, barber_shop | Backup |

### Query Overpass Milano
```python
query = """
[out:json][timeout:300];
area["name"="Milano"]["admin_level"="8"]->.milano;
(
  node["amenity"="hairdresser"]["name"](area.milano);
  node["shop"~"^(hairdresser|beauty)$"]["name"](area.milano);
  node["craft"="barber"]["name"](area.milano);
);
out center tags;
"""
```

### CKAN Comune Milano
Riusa pattern CEO night research:
```python
import requests
r = requests.get("https://dati.comune.milano.it/api/3/action/package_search",
                 params={'q':'acconciatori estetisti','rows':20})
# Filter dataset pubblici esercizi non-piano → categoria "Acconciatore" / "Estetica"
```

### Schema CSV venues
**Estendi `SCHEMA_AGENTI.md` o usa `vertical=barber` come marker**:

```csv
source_platform,source_venue_id,venue_name,venue_url,address,city,latitude,longitude,
categories,price_tier,rating,rating_count,phone,website,opening_hours,
has_menu,menu_url,extraction_status,retrieved_at,
vertical,venue_type,nil_quartiere
```

Campi specifici:
- `vertical` = `'barber'` (marker categoria)
- `venue_type` ∈ {`barber`, `hairdresser`, `unisex_salon`, `beauty_salon`, `nail_salon`, `spa`}

---

## PHASE 2 — PROVIDER DISCOVERY (booking platforms)

Identifica i provider booking dominanti in Italia per parrucchieri. Pattern URL noti:

| Provider | URL | Stima venues IT |
|---|---|---|
| **Treatwell.it** | treatwell.it/parrucchieri | 5.000+ |
| **Wellry/Wellry.com** | wellry.com/it | 1.000+ |
| **Booksy IT** | booksy.com/it-it | 2.000+ |
| **Fresha.com** | fresha.com/it | 1.000+ |
| **Salonkee** | salonkee.it | 500+ |

**Test ognuno** con `curl_cffi` (impersonate Chrome/Safari iOS):
- Robots.txt accessibile?
- Sitemap pubblica?
- Listini prezzi nel HTML SSR o via JS?
- JSON-LD strutturato?

Output: `barber_s1_PROVIDERS.md` con mapping `provider → URL pattern → scraping feasibility`.

**Lesson learned spiagge.it (Phase 3 tuo)**: cerca query string parameters `?date=` o `?service=` che potrebbero esporre prezzi nel HTML SSR senza Playwright.

---

## PHASE 3 — SAMPLE PRICE EXTRACTION (20-30 venues)

### Schema CSV items
Riusa schema esteso (come hai fatto per beach):

```csv
source_platform,source_venue_id,venue_name,venue_url,menu_section,
item_name,item_description,raw_price,normalized_price_eur,currency,
price_type,item_type,normalized_product,confidence,allergens,
retrieved_at,source_url,vertical
```

### Vocabolario chiuso `normalized_product` per barbieri/parrucchieri

```python
# Da aggiungere a normalization.py (CEO update sera)
BARBER_PRODUCTS = {
    'haircut_men':       'Taglio uomo',
    'haircut_women':     'Taglio donna',
    'haircut_kids':      'Taglio bambino',
    'beard_trim':        'Regolazione barba',
    'shave_traditional': 'Rasatura tradizionale',
    'wash_blow':         'Lavaggio + piega',
    'color_full':        'Colore completo',
    'color_roots':       'Ritocco radici',
    'highlights':        'Colpi di sole / mèches',
    'balayage':          'Balayage',
    'perm':              'Permanente',
    'straightening':     'Stiratura',
    'extension':         'Extensions',
    'wedding_styling':   'Acconciatura sposa',
    'nail_manicure':     'Manicure',
    'nail_pedicure':     'Pedicure',
    'nail_gel':          'Gel/Semipermanente',
    'eyebrow_design':    'Design sopracciglia',
    'eyebrow_lamination':'Laminazione sopracciglia',
    'facial_treatment':  'Trattamento viso',
    'wax_partial':       'Cera parziale',
    'wax_full':          'Cera totale',
    'kids_haircut':      'Taglio bambino',
}
```

### Price ranges realistic Milano

```python
BARBER_PRICE_RANGES = {
    'haircut_men':       (10.0, 60.0),
    'haircut_women':     (20.0, 150.0),
    'haircut_kids':      (8.0, 30.0),
    'beard_trim':        (5.0, 30.0),
    'shave_traditional': (15.0, 50.0),
    'wash_blow':         (15.0, 80.0),
    'color_full':        (40.0, 250.0),
    'color_roots':       (25.0, 120.0),
    'highlights':        (50.0, 300.0),
    'balayage':          (80.0, 400.0),
    'perm':              (30.0, 200.0),
    'straightening':     (30.0, 200.0),
    'nail_manicure':     (10.0, 60.0),
    'nail_pedicure':     (15.0, 80.0),
    'nail_gel':          (20.0, 80.0),
    'eyebrow_design':    (5.0, 40.0),
    'wax_partial':       (10.0, 50.0),
    'wax_full':          (30.0, 120.0),
}
```

### Discovery prezzi (target: 20-30 venues sample)

Strategie cascade:
1. **Treatwell**: cerca venues Milano, scraping HTML SSR. Treatwell espone prezzi nelle service cards.
2. **Booksy**: profilo salone → service list con prezzi visibili senza login.
3. **Siti propri**: Google dork `site:*.it "listino" "parrucchiere" Milano` filetype:pdf
4. **Instagram bio**: alcuni saloni mettono link listino in bio (manuale, 5-10 venues)

---

## PHASE 4 — FRONTEND INTEGRATION

Aggiungi al `index.html`:

### Toggle vertical
Tab/dropdown con 3 verticals:
- 🍹 Drink (esistente)
- 🏖️ Balneari (esistente)
- 💈 **Barbieri** (nuovo) ← tu

### Marker design distintivo
- Drink prezzati: rectangular markers
- Beach: circular markers
- **Barbieri: hexagonal markers** (consistent ma distinto)

Colori per venue_type:
- `barber` → marrone scuro
- `hairdresser` (donna) → rosa
- `unisex_salon` → grigio neutro
- `beauty_salon` → viola

### Data feed
`data/barber_data.json` (replica struttura `beach_data.json`):
```json
{
  "metadata": {"city": "Milano", "total_venues": X, "total_priced": Y},
  "venues": [...]
}
```

Build script: `scripts/build_barber_json.py` (replica `build_beach_json.py`).

### Toggle no-price layer
Riusa il toggle pattern che hai già per drink no-price + beach unpriced. Default OFF, on toggle → mostra venues senza prezzo.

### Filtri venue_type
Chip filter: ☑ Tutti · ☑ Barbiere · ☑ Parrucchiere donna · ☑ Estetica · ☑ Nail · ☑ Unisex

---

## DELIVERABLES S1

| File | Contenuto |
|---|---|
| `raw_sources/barber_s1_venues.csv` | Master list Milano (~2.500+ venues) |
| `raw_sources/barber_s1_menu_items.csv` | 20-30 sample con prezzi |
| `raw_sources/barber_s1_providers.csv` | Provider mapping per venue (Treatwell/Booksy/...) |
| `barber_s1_PROVIDERS.md` | Report provider booking + scraping feasibility |
| `barber_s1_REPORT.md` | Metriche + gap analysis |
| `data/barber_data.json` | Frontend-ready (200 venues + 20 prezzi sample) |
| `scripts/barber_s1_osm.py` | OSM Overpass scraper |
| `scripts/barber_s1_discovery.py` | Provider/sitemap discovery |
| `scripts/barber_s1_extract.py` | Sample prezzi scraper |
| `scripts/build_barber_json.py` | Build pipeline frontend |
| `index.html` | Vertical toggle + barbieri layer integrato |

---

## QUALITY GATES (riusa shared lib)

```python
import sys; sys.path.insert(0, 'scripts')
from normalization import is_milan_or_unknown, validate_item
# Estendi tu se serve, ma il pattern è importare condiviso.
```

Per ogni venue:
1. Milano CAP 20100-20162 o bbox Milano
2. `venue_type` ∈ vocabolario chiuso barbieri
3. Geo verificato (no fallback Duomo per > 5% del totale)
4. Niente IMAGE_URL in source_url
5. Niente HTML noise nei nomi (riusa NOISE_PATTERNS)

Per ogni item:
1. `normalized_product` in vocabolario barbieri (sopra) o vuoto
2. `normalized_price_eur` in `BARBER_PRICE_RANGES` o vuoto
3. Confidence: `high` (PDF listino), `medium` (HTML scraped), `low` (estimated)
4. NO MAXI/pacchetti (concentra su singolo servizio)

---

## VERTICAL FILTER INLINE (NO contaminazioni)

Tutti i tuoi CSV devono avere `vertical='barber'`. Il `merge_pipeline_drink.py` e `merge_pipeline_beach.py` del CEO ignoreranno i tuoi file (filter vertical).

Il CEO scriverà `merge_pipeline_barber.py` separato che consuma SOLO i tuoi `barber_*.csv`.

---

## RATE LIMITS

| Servizio | Rate |
|---|---|
| OSM Overpass | 1 big query OK |
| CKAN API | 1s/req |
| Treatwell | 2s/req, max 100 venues/sessione |
| Booksy | 2s/req |
| Fresha | 2s/req |
| Nominatim (se serve geocode) | 1.2s/req |

---

## ARCHITETTURA POST-S1 BARBIERI (per orientarti)

Schema repo dopo i lanci paralleli:

```
data/
├── prices_data.json         (drink Milano, esistente)
├── beach_data.json          (beach Italia, esistente)
├── barber_data.json         ← TU consegnerai
├── gym_data.json            (utente Palestre, futuro)
└── unified_venues_no_price.csv (drink, esistente)

scripts/
├── merge_pipeline_drink.py    (CEO refactor da merge_pipeline.py)
├── merge_pipeline_beach.py    (CEO new)
├── merge_pipeline_barber.py   ← CEO new, leggerà i tuoi CSV
├── merge_pipeline_gym.py      (CEO new per palestre)
├── normalization.py           (esteso multi-vertical)
└── build_barber_json.py       ← TU
```

---

## COSA NON È SCOPE S1

- ❌ Estensione barbieri Italia (Roma/Napoli/...) — è S2 barbieri
- ❌ Crowdsourcing UI (è CEO + utente questa sera con Supabase)
- ❌ Toccare verticali drink / balneari
- ❌ Modificare `merge_pipeline_drink.py` (territorio CEO)

---

## CONSEGNA

```bash
git pull --rebase origin main
git add raw_sources/barber_s1_*.csv barber_s1_*.md scripts/barber_s1_*.py scripts/build_barber_json.py data/barber_data.json index.html
git commit -m "feat(barber): vertical S1 — N venues, M sample prezzi, integration UI"
git push origin main
```

Avvisa CEO al chiuso di ogni Phase. Tempo stimato totale: 10-14h.

---

## TIPS LESSON LEARNED (da te su Beach)

1. **Smoke test prima di scalare** — testa 5 saloni Treatwell prima di bulk
2. **JSON-LD always check** — provider come Treatwell potrebbero esporre service+price strutturato
3. **Robots.txt check** — Booksy ha API blacklist? Treatwell?
4. **Mobile-first markers** — il vertical barbieri va sul mobile (target user)
5. **Vocabolario chiuso STRICT** — non inventare codici, lascia vuoto se incerto

---

## CONFIDENCE METRICA PER S1 (essere onesti)

Stimi a fine S1:
- 90%: master list 2.000-3.000 venues Milano
- 70%: 20-30 venues sample prezzi extracted
- 40%: provider booking dominante identificato + URL pattern stabile

Se a metà ti rendi conto che Treatwell richiede Playwright (anti-bot pesante), STOP e raccoglie solo OSM + CKAN venues + frontend, sample prezzi → S2. Quality > quantity.

---

Buon lavoro Peppe. **Il vertical barbieri è il test del modello SurPrice multi-vertical. Il framework esiste, replicalo.**
