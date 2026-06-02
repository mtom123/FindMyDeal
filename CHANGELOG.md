# Changelog — FoodPrice Milano

> Storico decisioni, problemi risolti, ragionamenti.
> Aggiornare dopo ogni merge o decisione di design importante.
> Formato: data → cosa è successo → perché → impatto.

---

## 2026-06-02 SERA — Ricerca notturna CEO (scraper bestiale) → 4.124 venues no-price Milano

### Trigger
Utente: "metti i panni dello scraper, esplora nuove vie, parti in autonomia, cracca le barriere".

### Esplorazione su 9 fronti
| # | Target | Esito |
|---|---|---|
| 1 | TheFork prezzi live (curl_cffi TLS impersonate) | 🟡 bypass 403 con safari17_2_ios, ma menu via JS lazy |
| 2 | eatbu 11 venues Pietro S5 (XHR reverse) | 🟡 metadata only, 0 prezzi |
| 3 | Yelp.it cocktail bar Milano | ❌ no prezzi |
| 4 | Quandoo.it | ❌ HTTP 404 (URL changed) |
| 5 | Michelin Guide Italia | ❌ HTTP 404 |
| 6 | Glovo Wayback bulk | ❌ solo 4 venues su 13 zone |
| 7 | Glovo live | ❌ SSR vuoto, Vue.js XHR |
| 8 | **CKAN Comune Milano API** | ✅ **3.804 venues nuove** |
| 9 | **OSM Overpass amenity bar/pub/cafe** | ✅ **5.229 OSM venues con nome commerciale Milano** |

### 🏆 WIN principale — CKAN + OSM cross-ref
Scoperto API ufficiale `dati.comune.milano.it/api/3/action/package_search`:
- Dataset `ds58_economia_pubblici_esercizi_in_piano` → 9.417 esercizi
- Filter drink-target (categorie f/e/g/h/i/j) → 3.840 venues TARGET
- Post-dedup vs unified_venues drink → **3.804 NON ancora nel DB**

Cross-ref OSM Overpass (5.229 venues con nome commerciale Milano):
- Match geo ≤50m → 2.970 / 3.804 = **78% match rate**
- 2.970 venues CKAN ora hanno nome commerciale reale (era "Bar Via X N")

### Build pipeline
`scripts/build_no_price_map.py` produce `data/unified_venues_no_price.csv`:
- 1.247 dal DB unified (no-price subset, geo, bbox Milano)
- 2.867 da CKAN enriched (matched OSM, filtrati "Bar VIA X" placeholders)
- 10 da eatbu agent_ceo metadata
- Dedup nome+geo round(3) → 948 dupes rimossi
- **Output finale: 4.124 venues no-price**

### Frontend impact
Mappa Milano drink: **153 prezzati + 4.124 no-price = 4.277 pin totali** (+2.696% vs solo 153).

Peppe ha già implementato `unpriced toggle` (commit 4463c2a). File `data/unified_venues_no_price.csv` pronto per essere consumato direttamente.

### Tecniche tecniche aperte per Pietro futuro
1. **curl_cffi `safari17_2_ios`** = unlock TheFork SSR (HTTP 200). Usabile per discovery massiva metadata TheFork Milano.
2. **OSM Overpass amenity query Milano** = base universal per cross-ref nomi commerciali (Pietro l'usava per beach, ora replicato per drink).
3. **CKAN API package_search** = pattern replicabile per ALTRE città (Roma, Firenze, Torino se hanno dataset open analoghi).

### Strade chiuse documentate (no re-tentare senza nuove tecniche)
- Glovo live/Wayback (residenziale + Playwright)
- TheFork prezzi menu (Apollo GraphQL XHR, no SSR)
- Quandoo / Michelin (URL routing changed, ri-investigare)
- Yelp.it (prezzi non esposti)

### Numeri delta
| Metrica | Pre-notte | Post-notte | Δ |
|---|---|---|---|
| Venues drink mappa Milano | 153 | **4.277** | **+4.124 (+2.696%)** |
| Price points | 964 | 964 | 0 (barriere reali residue) |
| Venues totali DB unified | 1.601 | 1.601 | 0 (no merge nuovi, solo layer no-price) |
| Fonti integrate | 23 | 26 | +3 (CKAN + OSM Overpass + eatbu_ceo) |

### Onestà finale
- ✅ Venues mappa: **+4.124** (passa da 153 a 4.277, +2.696%)
- ❌ Price points: **+0** (le barriere TheFork/Glovo/JustEat live richiedono infrastruttura proxy residenziali + Playwright headful, fuori scope autonomo)

### File prodotti
- `unified_venues_no_price.csv` (workdir CEO)
- `data/unified_venues_no_price.csv` (frontend-ready)
- `raw_sources/ckan_milano_drink_venues_no_price.csv` (3.804 venues CKAN enriched)
- `raw_sources/osm_milano_drink_overpass.csv` (5.229 OSM venues base)
- `raw_sources/agent_ceo_eatbu_metadata.csv` (11 venues eatbu)
- `scripts/build_no_price_map.py` (pipeline build)
- `NIGHT_RESEARCH_REPORT.md` (report tecnico completo)

### Per CEO domani mattina
1. Decisione strategica: ora il bridge crowdsourcing è CRITICO (4.124 inviti naturali).
2. Pietro S6 in corso può integrare il file no-price come base partenza.
3. Peppe può attivare unpriced toggle layer puntando a `data/unified_venues_no_price.csv`.

---

## 2026-06-02 — Pietro S5 integration + libreria condivisa di normalizzazione

### Input Pietro S5 (commit af15ec8 — già pushato)
File consegnati:
- `raw_sources/agent5_geocode_fixes.csv` — 19 venues con coordinate precise (Nominatim/WebSearch)
- `raw_sources/agent5_quality_flags.csv` — 13 flag (4 EXCLUDE + 9 REVIEW) sui price points
- `raw_sources/agent5_eatbu_discovered.csv` — 11 venues eatbu nuovi (backlog, prezzi via XHR)
- `DATA_QUALITY_REPORT.md` — tassonomia FP + policy bande prezzo
- `PIETRO_NEXT_STEPS.md` — backlog 3 priorità + bloccati
- `scripts/quality_audit.py`, `quality_flags.py`, `geocode_fallback*.py`

### CEO action: applicate al merge
1. **Geocoding fixes** applicati ai raw_sources venues:
   - 45 fix totali (alcuni venue duplicate in agent2/agent3/agent4)
   - Venues mappa: 144 precise (era 133) + 9 fallback Duomo legit (Camparino, La Terrazza Aperol, ecc. — fisicamente in Duomo)
2. **Regola MAXI** aggiunta a `clean_item_product()`:
   - Tutti i cocktail con "maxi"/"caraffa"/"pitcher"/"brocca"/"litro"/"1L" nel nome → SKIP
   - **90 items MAXI rimossi** (dominante SPRITZ NAVIGLI MILANO Campari/Spritz/Mojito MAXI €19)
3. **eatbu discovered** lasciati come backlog (XHR scraping a sessione futura)

### Libreria condivisa `scripts/normalization.py` (raccomandazione Pietro)
**Problema**: ad ogni nuovo agent scraper, i falsi positivi noti vengono ricreati (americano caffè vs cocktail, Moretti birra vs Vittorio Moretti vino, prosecco glass vs bottiglia, MAXI multi-porzione).

**Soluzione**: modulo condiviso importato da tutti gli scraper PRIMA di consegnare CSV:
```python
from scripts.normalization import clean_item_product, is_milan_or_unknown, validate_item, PRICE_RANGES
```
Le 14 regole di disambiguazione + bande prezzo + city filter sono ora in `normalization.py`, ri-utilizzabili. Il merge_pipeline.py importa la libreria (fallback a inline se manca).

### Delta numeri
| Metrica | Pre S5 integration | Post | Δ |
|---|---|---|---|
| Price points | 985 | **964** | -21 (90 MAXI rimossi, +69 recuperati da geocoding) |
| Items totali | 5.626 | 5.605 | -21 |
| Venues mappa precise | 133 | **144** | +11 |
| Venues mappa fallback | 20 | 9 | -11 (geocoding fix funziona) |
| Venues mappa totale | 153 | 153 | 0 |

### Outliers residui (8) — TUTTI LEGIT
Tutti già verificati come premium venues legit:
- Morgante "Frenesia dei Navigli" €19, Barcollando €20, SPRITZ NAVIGLI Classici €20
- LiQUIDO Rooftop Negroni Experience €25, La Terrazza Aperol Gin Tonic Selection €21
- Oud Beersel Lambic 6Y €14 (craft beer artigianale)
- Ceresio 7 / Oysteroom Caffè €4 (rooftop upscale)

### Pietro raccomandazione strategica
Quote: "libreria di normalizzazione CONDIVISA così tutti gli agent applicano lo stesso gate e non si ricreano i falsi positivi"

**Implementato.** Tutti gli scraper futuri devono importare `scripts.normalization` e validare items con `validate_item()` prima di consegnare. Questa è ora best practice del progetto.

### Venues ancora su fallback Duomo (9, tutte legit)
BRAMA, Bistrot Pattari, Caffè Inn International Bistrot (dupe), Camparino in Galleria, FOD Save The Food Duomo, La Terrazza Aperol, Lab Milano, Morgantecocktail (vicolo privato), Terrazza Duomo 21.

Sono FISICAMENTE in Duomo (eccetto BRAMA e Morgante = casi limite). Non sono FP, sono pin corretti su Piazza Duomo.

---

## 2026-06-02 — Audit scrupoloso v2 + standardizzazione DB drink

### Trigger
Richiesta CEO: audit completo, focus su venues prezzate. Esempio specifico segnalato: spritz €0.75 Papeete (FP storico).

### Funzioni aggiunte a merge_pipeline.py
**`clean_item_product(item)`** — applica regole di reclassificazione e skip:

| Regola | Action | Esempi |
|---|---|---|
| `americano` + "caffè" + price<4 | Clear product | Bar Magenta caffè americano €1 |
| `espresso` + "martini"/"cocktail"/"affogato"/"mixed" | → `custom_cocktail` | Espresso Martini €10 |
| `espresso` + "corretto" + price>3 | Clear product | Caffè corretto grappa €3.90 |
| `prosecco_glass` + "bottiglia" + price>15 | SKIP | Prosecco Valdobbiadene Bottiglia €35 |
| `prosecco_glass` + price>15 | SKIP (likely bottiglia) | |
| `beer_moretti` + "vittorio"/"riserva"/"brut"/"spumante" | SKIP | Vittorio Moretti Riserva Extra Brut |
| `beer_bottle` + "vino"/"valpolicella"/"barolo"/"chianti"/"antipasto"/"ripasso" | SKIP | Ripasso di Valpolicella |
| `mojito` + "bloody mary"/"licorice mary" | SKIP | LICORICE MOJITO MARY |
| `margarita` + "caraffa"/"pitcher"/price>30 | SKIP | Santo Taco CARAFFA |
| `spritz` + "coca cola"/"fanta"/"soft drink" | → `soft_drink` | |
| `spritz` + "calice"/"vino bianco/rosso" | → `wine_glass` | |
| `spritz` + "birra" | SKIP | |
| `spritz` + "caffè"/"espresso" | SKIP | |

**Item name noise filter** — pattern aggiunti:
- `mail us`, email pattern (`@\w+\.\w+`), `where: <luogo>`
- Page navigation (>2 marker tra "home/contatti/footer/header/...")
- `>= 4 €` nel nome (parser concat fail tipo PDF mal-letti)
- `"menu" + 1 marker` (HTML toggle navigation)

**Price range filter in unified_prices** — solo items dentro range realistico Milano:
- spritz 3-22 · negroni 4-25 · americano 4-18 · gin_tonic 5-22 · mojito 5-22
- moscow_mule 5-20 · margarita 5-25 · daiquiri 6-22 · manhattan 7-25
- custom_cocktail 5-30 · beer_draft_small 2-8 · beer_draft_medium 3-12
- beer_bottle 2-14 · beer_brand 2-8 · wine_glass 3-15 · prosecco_glass 3-14
- espresso 0.8-4 · cappuccino 1.2-5.5 · soft_drink 1-7 · water 0.5-5

### Cleanup applicato (questo run)
- **NAME_NOISE: 99 items** (mail us, email, "menu -", concat parser fail)
- **NAME_PARSER_NOISE: 9** (HTML nav extracted as item)
- **SPRITZ_IS_COFFEE: 4** (parser ha matchato "spritz" in pagina caffè)
- **NAME_MULTI_EURO_CONCAT: 4** (parser PDF letto orizzontale)
- **BEER_BOTTLE_IS_FOOD_OR_WINE: 4** (Ripasso Valpolicella, Antipasto, Riserva)
- **PROSECCO_GLASS_TOO_HIGH: 4** (>€15 = bottiglia mascherata)
- **MARGARITA_CARAFFA: 2** (Santo Taco €60/€90)
- **PROSECCO_BOTTIGLIA: 2** (esplicito "Bottiglia" nel nome)
- **MOJITO_IS_BLOODY_MARY: 1** (Luma LICORICE MOJITO MARY)
- **MORETTI_SPUMANTE: 1** (Vittorio Moretti Franciacorta)
- **NAME_TOO_LONG_PAGE: 1**

**Items rimossi pre-merge: 131**

### Price range filter post-merge (unified_prices)
- soft_drink 15 (>€7 erano bottiglie grandi)
- americano 10 (<€4 erano caffè residui)
- espresso 5 (>€4 Espresso Martini)
- beer_bottle 3, cappuccino 2, beer_moretti 1, spritz 1, negroni 1, custom_cocktail 1

**Price points eliminati da range: 39**

### Delta numeri drink (audit v2)
| Metrica | Pre-audit | Post-audit | Δ |
|---|---|---|---|
| Price points | 1.080 | **985** | -95 (rumore) |
| Items | 5.708 | 5.626 | -82 |
| Venue-product pairs | 723 | 687 | -36 |
| Venues mappa | 161 | **153** | -8 (alcune erano solo punti junk) |
| Quality | ~85% clean | **94% clean** | +9 |

### Outliers residui (9) — LEGIT, non FP
| Item | Prezzo | Motivo legit |
|---|---|---|
| SPRITZ NAVIGLI CAMPARI MAXI | €19 | Spritz MAXI premium |
| Barcollando spritz | €20 | Cocktail upscale Navigli |
| Morgante "Frenesia dei navigli" | €19 | Cocktail signature |
| SPRITZ NAVIGLI CLASSICI | €20 | Premium tier |
| LiQUIDO Rooftop "Negroni Experience" | €25 | Rooftop premium |
| La Terrazza Aperol "GIN TONIC SELECTION" | €21 | Premium |
| Oud Beersel Lambic 6Y | €14 | Craft beer artigianale |
| Ceresio 7 caffè | €4 | Rooftop Dsquared (upscale) |
| Oysteroom caffè e latte | €4 | Locale upscale |

### Outliers minori segnalati ma non rimossi (60 mismatch)
60 items in mismatch product/item_name dove il parser HTML ha catturato page-title come item_name. Tutti dentro range prezzi plausibili, quindi non degradano qualità apparente. Sono ~6% del totale = noise floor accettabile.

### TODO futuro
- Standardizzazione casing venue (Caffè Fernanda vs Caffefernanda vs caffefernanda) → script dedicato
- Reverse-geocoding 20 venues fallback Duomo
- Audit beach vertical (3.443 items, da fare)

---

## 2026-06-02 — Pietro S4 deep-scan merge + Peppe Beach Phase 3 consegna

### Pietro S4 (commit 733925e) — drink deep-scan
- **Target**: re-scan 88 venues con estrazione parziale (1-3 items nel DB) dalla lista `PIETRO_S4_TARGETS.csv` preparata dal CEO
- **Output**: 88 venues processate, 66 con nuovi drink (75% yield), **236 price points puliti**
- **Tecnica**:
  - mycia (43): ri-classificazione locale dei menu già scaricati con 22 pattern regex → recupera birre/brand non normalizzati
  - direct_website/web_extract/eatbu (42): re-fetch + regex riga + PDF/path-probing
  - leggimenu (3): pagine categoria server-side (.lmcart-add data-price)
- **Quality gate inline**: scartati ~177 falsi positivi pre-emit (PRICE_TOO_HIGH_FOR_PRODUCT 36, MENU_NOTE, FOOD, COFFEE_NOT_COCKTAIL, NON_MILAN)
- **Onestà**: target +500 pp, raggiunti 236. Scelta qualità: "Meglio 236 puliti che 413 con 40% rumore"
- **Distribuzione**: spritz +35, negroni +34, americano +25, espresso +24, beer_bottle +20, soft_drink +16, water +14, cappuccino +12, wine_glass +10, beer_heineken +10, margarita +10
- **Top yield venues**: Caffè Fernanda +10 items, Norin Caffè Bistrot +10, Papeete +8, Refeel +8, Armanisilos +8, Luca & Andrea +8
- **Tutti confidence=medium** (corretto per re-extraction)

### CEO merge Pietro S4
- Sync agent4_deepscan_*.csv in workdir
- Run merge_pipeline.py (filtri inline già attivi: CAP città, nav markers, parser noise, ghost merger)
- **Delta drink**:
  - Price points: 939 → **1.080** (+141 netti vs 236 estratti = 95 erano già coperti da altre fonti)
  - Items totali: 5.576 → 5.708 (+132)
  - Venue-product pairs: 631 → **723** (+92)
  - Venues mappa: 159 → **161** (+2)
  - Venues DB: invariato 1.601

### Peppe Beach Phase 3 (commit ef0c593) — breakthrough tecnico
- **Phase 3.0 (DOM discovery)**:
  - Tentati 30+ endpoint REST `api.spiagge.it` → tutti 404
  - Playwright sniffing: zero XHR fired su "Vedi disponibilità"
  - **Scoperta**: prezzi esposti via query string `?from=&to=` direttamente nel HTML SSR
  - Pattern: `"price":N`, `"stagingItems":"1U_2B"`, `"bookingAvailable":true|false`
  - Risparmio: **70x più veloce** di Playwright (25 min vs 25h)
  - Zero anti-bot rilevato anche su prezzi (conferma S2X)
- **Phase 3.1 (mass extraction)**:
  - 6.686 venues × 2 slot (peak ago 1-7 + mid giu 15-21) = 13.372 fetch
  - 16 worker concurrent + Session pool = ~10 min totali
  - 3.174 items / 1.696 venues con `bookingAvailable=true`
  - **24% conversion rate** (75% venues spiagge.it senza booking online)
  - Sud Italia: 524 venues prezzati (era 5 in S2, +10.380%)
  - Peak Aug median €150/sett, mid Jun median €126/sett (spread +19%)
- **Phase 3.6 (consolidation)**: merge S1 214 + S2 direct 39 + S2 PDF 16 + Phase 3.1 3.174 = **3.443 items / 1.731 venues prezzati**, 99.3% high confidence, 0 rejection in QG
- **Schema invariato**: 16 normalized_product S1 + 8 price_type S1 sufficienti
- **Output**: `raw_sources/beach_phase3_consolidated_items.csv` (3.443 rows)
- **Phase 3.2-3.5 rinviate** (iBagnino, Beacharound, secondary, direct): 4-8h sessione futura per chiudere target 2.000 venues

### Stato finale post-merge entrambi
- Drink: 1.080 price points, 161 venues mappa, 22 prodotti
- Beach: 3.443 items, 1.731 venues prezzati, 17 regioni coperte

---

## 2026-06-02 — Merge agent4 (ultimo batch drink) + cleanup DB completo

### Input agent4 (consegna finale agent drink Milano)
- agent4_leggimenu (2 venues, 9 items): brute-force slug + JSON-LD Milano verify
- agent4_eatbu (5 venues, 18 items): PDF dish.co su 31K sitemap eatbu, filter postcode 20xxx
- agent4_thefork (31 venues, 88 items): snapshot Wayback Machine (Datadome bypass) + addressLocality JSON-LD
- agent4_glovo (1 venue, 7 items): tile/grid parser SSR Wayback su Maki Poke

### Quality fix CEO pre-merge (22 items rimossi)
- ✗ BAR MILAN: a San Colombano al Lambro (provincia LO), NON Milano → REMOVE venue
- ✗ "Prenota i migliori ristoranti per ogni occasione": page title come venue (Casa Fassona) → REMOVE
- ✗ "Recensioni - Officina Milano": estratto da pagina recensioni, non menu → REMOVE
- ✗ Maki Poke (glovo): già presente nel DB → duplicato REMOVE
- ✗ Don Vincè €6 FP × 4: parser ha matchato prezzo calice di vino invece del cocktail
- ✗ Refeel Milano spritz €12 FP: description "Piscolada 12 €" → falso match
- ✗ Aperitivo bundle × 3 (Papilla, 21 House, Benvenuto Family): item_name="Aperitivo" prezzo €15-16 = combo, non singolo prodotto
- ✗ Maki Poke 7 items già nel DB drink

### Product normalization fix
- `beer_corona`, `beer_ichnusa` → `beer_bottle` (vocabolario chiuso)
- `beer_draft` → `beer_draft_small` (taglia default)
- `aperol` → `spritz`
- `aperitivo` → vuoto (non è prodotto specifico)

### Audit completo DB post-merge (db_audit.py)
Trovati e fixati:
1. **22 venues con CAP non-20xxx**: legacy mycia con CAP esplicito fuori Milano (Misano Adriatico, Roma, Cagliari, Palermo, Salerno, Bergamo, Pavia, ecc). Bug merge_pipeline: nessun filtro città inline.
2. **6 items con HTML navigation markers**: "Vai alla Header Bar", "Salta al contenuto" come item_name.
3. **2 items parser noise**: item_name = ":" o "X € con N portate" (osm_direct2 55 Milano).
4. **56 ghost canonical**: stesso venue con lat='' vs lat=valore = 2 canonical entries diverse → bug fingerprint con lat/lng nel key.

### Bug fix merge_pipeline.py (definitivi)
1. **Filtro CAP città inline** (`is_milan_or_unknown`): venues con CAP non-20xxx vengono skippate. Si applica sia a mycia legacy che a raw_sources.
2. **Filtro nav markers inline**: items con HTML navigation skipped.
3. **Filtro item_name corti/noise**: <3 char clean o "X € con N portate" skipped.
4. **Ghost canonical merger** (Phase 2bis): post-dedup, canonical con stesso nome (clean) ma uno senza lat viene mergiato nel canonical principale. Items ghost re-mappati.
5. **Beach files filtro inline**: `beach_*`, `comune_osm_*` skippati dal merge drink (vertical separation).

### Delta numeri drink
- Pre-merge: 924 price points / 158 mappa / 1.610 DB
- Post-merge + cleanup: **939 price points** (+15 netti) / **159 mappa** (+1) / **1.601 DB** (-9 netti per ghost merge + non-Milan cleanup)
- Venue-product pairs: 613 → 631 (+18)

### File raw_sources finalizzati (drink workdir)
agent2_*, agent3_*, agent4_* (new), direct_*, glovo_*, leggimenu_*, leggimenu_s3_*,
menudigitale_*, mycia_*, osm_direct2_*, pdf_*, pdf_googledork_*, qromo_*, scraper_*,
web_extracted_*.

beach_*, comune_osm_* esistono ma sono skippati dal merge drink (vertical=beach).

### Cosa NON è stato fatto (per scelta)
- ❌ Frontend integration (su esplicita richiesta utente: prima consolidamento DB completo)
- ❌ Push del PROMPT_PEPPE_BEACH_PHASE3.md scritto da Peppe (out of scope di questo cleanup)
- ❌ Touch al beach master (out of scope, è pulito al 100%)

---

## 2026-06-02 — Beach S2 + S2X merge (Peppe) + master consolidato

### Input Peppe (3 sub-sessioni)
- **S2 standard** (commit 315fc17): 8 venues nuovi, 56 items (39 direct + 16 PDF + 1 consortium), reverse geocoding parziale 300/2000
- **S2X discovery** (562de36): sitemap spiagge.it → 6.693 URLs
- **S2X mass extraction** (6b97a06): metadati SSR + JSON-LD su 6.686/6.693 venues (99.9% success), no Playwright richiesto

### Tecniche-chiave validate
- **spiagge.it sitemap pubblico**: 3 file XML in robots.txt → 6.693 URLs venue
- **Next.js SSR + JSON-LD schema.org**: metadati completi nel HTML (no JS richiesto)
- **Concurrency 16 worker + Session pool**: 25 req/s sostenuti, 8 minuti totali per 6.693 venue
- **Zero anti-bot rilevato**: niente Datadome / Cloudflare / captcha
- **Amenities normalizzate**: 15+ servizi vocabolario chiuso da schema.org (asset UX gold per S3)

### Match algorithm S2X (consolidation)
Per ogni venue spiagge.it match contro master S1 OSM:
- 2.296 match geo ≤300m (stesso venue, link `master_source_venue_id`)
- 3 match name+city fallback
- 1.923 geo_only_name_diff (zona vicina ma venue diversi — tenuti separati)
- **2.471 no_match completamente nuovi**
- Totale nuovi venue prenotabili non in OSM: **4.394**

### CEO action: master merge
Eseguito `scripts/beach_master_merge.py`:
- Base = beach_s1_venues.csv (9.252 OSM)
- Applicati 10.223 update suggeriti (regola: popola solo campi vuoti, MAI sovrascrivere)
  - 8.058 applicati, 2.165 skipped (campo già popolato)
- Append 4.394 venues spiagge.it non-OSM
- Output: `raw_sources/beach_master_venues.csv` con **13.646 venues**

### Stats finali master beach
| Metrica | S1 | S2X | Master |
|---|---|---|---|
| Venues | 9.252 | 6.693 | **13.646** |
| Con geo | 9.252 | 6.682 | 13.635 (99%) |
| Con city | 875 (9%) | 6.670 (99%) | 6.728 (49%) |
| Con region | 0 | 6.663 | 6.173 (45%) |
| Con booking_provider | 0 | 6.693 | 6.203 (45%) |
| Con amenities | 0 | 6.330 | 4.127 (30%) |

### Insights strategici da Peppe
1. **OSM e spiagge.it sono complementari**, non sovrapposti (overlap solo 34%). Servono entrambi.
2. **Le amenities** sono asset UX gold per S3 (filtri "pet-friendly + ristorante", "accessibile disabili" ecc).
3. **Spiagge.it permissivo coi bot**: UA con contact + 25 req/s = nessun blocco. S2X.2 Playwright per prezzi sarà più sicuro (slower per natura).
4. **Bottleneck rimasto**: solo il widget JS dei prezzi richiede browser engine. Tutto il resto = requests + JSON-LD.

### Prossimi step beach (raccomandato Peppe + CEO)
1. **S3 frontend bootstrap** — MVP mappa Italia + filtri amenities su 13.646 venues. Prezzi parziali (269 items) sufficienti per smoke product.
2. **S2X.2 Playwright prezzi** — sniff XHR widget booking spiagge.it, scrape 2.299 venues prioritari × 2 date (peak agosto + giugno medio). Stima 5.000-10.000 price items.
3. Decisione strategica: prodotto consumer vs B2B dataset (vedi discussione CEO).

### File drink intatti
`data/unified_*.csv`, `prices_data.json`, `index.html` non toccati. Vertical drink resta a 924 price points.

---

## 2026-06-01 — Merge Pietro S3 (leggimenu brute-force + osm_direct2)

### Output Pietro S3
- **leggimenu_s3** (raw): 127 venues, 8635 items — brute-force slug su 850+ candidate names
- **osm_direct2** (raw): 86 venues, 44 items — direct website scraping OSM list
- Peppe in parallelo: zone polygons + zoom + venue card design (index.html)

### Quality filter CEO — drastico ma necessario
- **Problema leggimenu_s3**: brute-force ha pescato dal sitemap leggimenu **tutta Italia**, non solo Milano. Senza filtro città il dataset sarebbe stato compromesso.
- **Filtro applicato**: CAP 20xxx (Milano metropolitana) o "milano" chiaro nell'indirizzo. Esclude "via milano" in altre città a meno di CAP 20xxx.
- **Risultato**: 127 → 15 venues Milano (12% hit rate), 8635 → 703 items.
- **112 venues scartate** sparse in tutta Italia: Calabria (San Ferdinando, Cosenza), Sicilia (Palermo, Foggia, Taranto), Toscana (Livorno), Veneto (Treviso, Susegana), Sardegna (Cagliari, Sardara), Liguria (La Spezia, Savona), Piemonte (Biella, Garessio), Emilia (Cremona, Collecchio), Lazio (Cori, lazio), Marche (Ancona, Urbania), Lombardia non-Milano (Assago).

### Fix bug double-letter osm_direct2
- PDF parser di Mulligan's leggeva "HHAARRPP", "GGUUIINNNNEESSSS" (lettere duplicate).
- **Fix**: regex `([A-Z])\1` → `\1` applicato a parole all-CAPS con coppie ripetute.
- 30 item_name corretti.

### Delta numeri
- Price points: 846 → **924** (+78)
- Items: 5.402 → 5.487 (+85)
- Venue-product pairs: 554 → **613** (+59)
- Venues sulla mappa: 150 → **158** (+8, 134 precise + 24 fallback)
- Venues totali DB: 1.610 → 1.644 (+34)

### Outliers minori non bloccanti
- Papeete spritz €0.75 (Chandon Garden Spritz — flag low ma plausibile per piccola taglia)
- Santo Taco caraffe Margarita €60/€90 (item_name dice "CARAFFA" — legittimi non standard)

---

## 2026-06-01 — Merge agent "Drink Milano" (sessione 3)

### Nuove fonti integrate
- **agent3_direct_website** (110 items, 45 venues): siti diretti + PDF dish.co. Barbisa 1920, Casa Giuditta, Frida, Funky, Birrificio La Ribalta, Morgante, Woodstock, e ~40 altri.
- **agent3_eatbu** (27 items, 10 venues): 6 nuove venues eatbu (+39zerodue, Guzzo, Morna, PRESTIGE, Seoul Ristorante Coreano, Vesper Milano) oltre alle 4 già nel DB.
- **agent3_leggimenu** (5 items, 1 venue): Spritz Navigli via Playwright JS render.
- **glovo** (4 items, 1 venue): Maki Poke via Wayback Machine. price_type=delivery.
- **agent3_other** (1 item): Rob de Matt negroni (confidence=low, estimated).

### Quality gate applicato (rimossi 22 items prima del merge)
- ×9 IMAGE_URL: source_url terminante .jpg/.png/.webp (Eatmeandgo favicon, Tardis icon, carico.io og-image)
- ×1 OAK_FALSE_POS: Scott Duff "rovere americano" = legno botte (non cocktail)
- ×1 NON_MILAN: Terrazza Martini = Casa Martini Pessione TO
- ×1 FOOD_NOT_WINE: Sicilian "Ravioli alla Polpa di Granchio" classificato white_wine
- ×1 NO_MENU_CONTEXT: Sun Strac homepage navigation text, nessun prezzo reale
- ×2 PAGINEGIALLE: Divina Piadina (fonte junk)
- ×7 SCARTATI COMPLETAMENTE: qodeup (duplicati Woodstock), other junk (Sakeya invalid product, Morgante 2016 blog, Woodstock dupe)

### Product normalization corretta
- `beer_draft` → `beer_draft_small`/`medium` (contesto taglia)
- `beer_corona`, `beer_ichnusa` → `beer_bottle`
- `aperol` → `spritz`
- `white_wine` → `wine_glass`, `prosecco` → `prosecco_glass`

### Bug fix critico merge_pipeline.py
- **Problema**: `venue_canonical_map[pid]` sovrascrivibile da versione senza geo → agent3 (no lat/lon) sovrascriveva agent2 (con lat/lon) → 95 price points persi.
- **Fix**: mapping preserva versione geo-rich. Non sovrascrivere se existing canonical ha lat/lon.
- **Impatto**: 829 → 846 price points (recuperati e aggiunti 17 netti).

### Delta numeri
- Price points: 829 → 846 (+17)
- Items: 5.361 → 5.402 (+41)
- Venue-product pairs: 547 → 554 (+7)
- Venues sulla mappa: 146 → 150 (+4)
- Venues totali DB: 1.558 → 1.610 (+52)

---

## 2026-06-01 — CEO merge + pulizia repo

### Merge sessione notturna Pietro (geocoding leggimenu) — CEO
- **Cosa**: 29 venue leggimenu geocodate con precisione (Nominatim). 6 falsi positivi non-Milano rimossi.
- **Venues rimosse**: Pub51 (PA), Coco Loco (LE), Bivacco (TN), Birra Bader (SI), Canaglie del Navigli (PR), SOLO APERITIVO popup (FE) — erano nel sitemap leggimenu ma non a Milano.
- **618 items eliminati** (quelli di quelle 6 venues).
- **Fix pipeline**: aggiunto `pdf_dork` a `VALID_PLATFORMS` (era il platform tag reale in pdf_googledork_menu_items.csv, mancava dalla lista — 81 items ora validati).
- **Geocoding CEO**: Frigo Milano (45.4632, 9.1829), Al Chiosco Da Giacomo (45.4451, 9.2236), BRAMA Via Borromei (45.4641, 9.1820).
- **Delta**: price points 888 → 829, items 5.835 → 5.361, venues mappa 151 → 146.
- **Perché il calo**: le 6 venue non-Milano avevano molti price points validi come dati, ma fuori scope. Guadagno netto = qualità + 29 pin sbloccati dal Duomo.

### Pulizia repo — CEO
- **Eliminati**: `NIGHT_SESSION_PIETRO.md` (report eseguito, info in CHANGELOG), `PROMPT_PIETRO_NOTTE.md` (sessione S2 completata, superata da S3).
- **Aggiornati**: README.md (numeri pubblici), BRIEF_PEPPE.md (numeri + tabella prodotti), AGENTS.md (struttura repo), COLLABORATORI.md (punta a PROMPT_PIETRO_S3), CEO_HANDOFF_PROMPT.md (numeri e stato), PIETRO_HANDOFF.md (pulizia stale notes).
- **Creato**: `PROMPT_PIETRO_S3.md` — sessione multi-ore con slug brute-force leggimenu, OSM direct 79 venues, Wayback TheFork.

### TheFork — stato definitivo attuale
- Datadome blocca anche Playwright stealth headless (testato 3/3 URL, IP datacenter).
- **Non più in pending**: serve proxy residenziale o accordo API. Non è un TODO attivo.

---

## 2026-05-31 — Sera (sessione data-sourcing)

### Esplorazione fonti nuove + tecniche di estrazione
- **Cosa**: sessione dedicata a trovare nuove fonti di prezzi/venue oltre a quelle già integrate.
- **Output prodotti**: `comune_osm_venues.csv` (4.649 venue), `pdf_googledork_*.csv` (81 items), `web_extracted_*.csv` (in corso). Vedi `raw_sources/README.md`.

### NUOVA FONTE: Open data Comune di Milano (CKAN)
- **Cosa**: dataset "Attività commerciali: pubblici esercizi in piano" da `dati.comune.milano.it` → ~6.184 bar/pub geocodificati (lat/lng + indirizzo).
- **Perché utile**: censimento completo dei locali autorizzati = base geografica enorme.
- **Limite**: il campo `denominazione_pe` è la CATEGORIA licenza ("Bar caffè"), NON il nome commerciale.
- **Soluzione (join Comune × OSM)**: match per prossimità coordinate (<35m) con i ~1.000 bar nominati da OSM Overpass → si attribuisce il nome. Risultato: `comune_osm_venues.csv`, 1.380 con nome, di cui **~505 nomi nuovi** non ancora nei dati prezzi = target di scraping.

### NUOVA TECNICA: nome venue → sito ufficiale via Startpage
- **Problema**: Google/Bing/DuckDuckGo HTML bloccano i risultati da script (pagine vuote o 403/429).
- **Cosa funziona**: **Startpage** (proxy Google) e **Mojeek** rispondono. Parsing risultati → primo dominio non-aggregatore che contiene un token del nome o è `.it`. Es. "Cinc Food Drinks Milano" → `cincbrera.it`.
- **Impatto**: pipeline `scripts/web_menu_extractor.py` automatizza nome→sito→menu sui 505 nomi nuovi.
- **Risultato finale**: 505 processati, 34 con menu, **509 prezzi grezzi → 441 puliti** dopo quality-gate (215 normalizzati). Hit rate reale **~6,7%** (il 20-25% iniziale era un campione fortunato).

### Quality-gate su web_extracted (prima della consegna)
- **509 → 441 prezzi** (rimossi 68, corretti 8). Errori trovati = stessa famiglia dei tuoi quality gate:
  - **14 e-commerce**: "Paradise Caffè" era un negozio di macchine/capsule caffè (raw_price tipo "Il prezzo originale era: 138,00€"), NON un bar. Rimosso.
  - **49 nomi sporchi**: parsing PDF/€-scan multi-colonna → nome conteneva item successivo o piatto food. Rimossi (>42 char).
  - **4 fuori range** (>€40) + **1 food**.
  - **2 "Espresso Martini"** classificati `espresso` → corretti in `custom_cocktail` (è un cocktail).
  - **7 "Caffè Americano"** classificati `americano` → label tolta (è caffè, NON il cocktail — falso positivo #3 del CEO).
- **Nota per il merge**: alcuni `item_name` da €-scan contengono ancora il prezzo nel nome (es. "Negroni € 8,50") — cosmetico, il prezzo è estratto correttamente a parte.

### NUOVA TECNICA: path-probing per siti JS-rendered
- **Problema**: molti siti bar sono SPA (React/Wix) → l'HTML statico NON espone i link al menu (0 prezzi anche se il menu c'è).
- **Fix**: dopo aver trovato il dominio, provare a mano i path comuni (`/menu /drinks /carta /cocktail /cocktail-list /beverage /listino`...). Es. `cincbrera.it/drinks/` esponeva il PDF → 21 prezzi.

### NUOVA TECNICA: parsing PDF multi-colonna
- **Problema**: menu PDF a 2 colonne → `pdfplumber` mette due drink sulla stessa riga (stesso tipo di bug del "Funky beer split").
- **Fix**: estrarre TUTTE le coppie (nome, prezzo) per riga con `PRICE_RE.finditer`, non solo la prima.
- **Resa "PDF dai siti"**: visitando i siti già noti in `direct_venues.csv` e cercando `<a href="*.pdf">` → 81 prezzi da 7 locali (Frida, Deseo, Harp Pub, Banshee...). File: `pdf_googledork_*.csv`.

### VICOLI CIECHI verificati (NON ritentare)
- **TripAdvisor**: DataDome CAPTCHA. Blocca `requests` (403) E Playwright headless (iframe `geo.captcha-delivery.com` prima del contenuto). Servirebbero CAPTCHA-solver a pagamento + proxy residenziali → ROI negativo. Script lasciato come riferimento ma da non usare.
- **Google Maps scraping**: Cloudflare + JS challenge. E l'API Places NON dà prezzi singoli (solo fascia €/€€/€€€).
- **Wikidata SPARQL**: solo ~4 bar famosi mappati a Milano.
- **Wayback Machine (CDX)**: pochi snapshot di pagine menu, nessun prezzo strutturato → output rimosso (era vuoto).
- **Glovo/JustEat/Deliveroo API**: endpoint mobile cambiati o 403 (conferma indipendente di quanto già noto).
- **`gmaps_*`/`wayback_*`**: file esperimento rimossi perché a 0 prezzi.

### Sistema onboarding agenti (CEO)
- **Cosa**: Creati `AGENTS.md`, `AGENTS_STATE.md`, `PROMPT_PIETRO_NOTTE.md`.
- **Perché**: Nuove sessioni Claude partivano cold senza contesto. Peppe segnalato.
- **Decisione tenuta**: struttura piatta `raw_sources/{fonte}_*.csv`, NON cartelle per-collaboratore (genera silos, duplicati, context frammentato).
- **Impatto**: ogni nuovo agente fa `git clone` + legge `AGENTS.md` → onboarding 5 min.

### Merge agent2 (Pietro sessione 2) — CEO
- **Numeri**: 738 price points (+109), 22 prodotti, 487 venue-product pairs, 126 venues mappa.
- **Junk rimosso (28 items)**:
  - 9 dupes di leggimenu (Spritz Navigli page-title come item_name)
  - 9 URL di immagini (.webp/.png) scrapate per errore
  - 2 soft drink mismatch (Coca Cola descritti come spritz)
  - 1 Terrazza Martini (Casa Martini è a Pessione TO, NON Milano)
  - 1 Sicilian white_wine €16 (era pasta description)
  - Vari false positive ("rovere americano" = legno, non cocktail)
- **Geocoding**: 29 venues match esatto con DB esistente, 21 fallback Milan center.

### Frainteso "GAP 167 venues" dal report del collega
- **Diagnosi sbagliata**: il collega contava `extraction_status=filtered_out` come "da scrappare".
- **Realtà**: quelli sono ristoranti/pizzerie/sushi, NON sono target del progetto.
- **Decisione**: NON rifare scraping su quei venues. Le venues "mancanti" reali sono ~55 (per MyCIA), la maggior parte `ok_no_menu` (proprietario non ha caricato menu).

---

## 2026-05-31 — Mattina/Pomeriggio

### Merge sessione 1 Pietro (CEO)
- **Sources integrate**: pdf (52 items), scraper (36 items), leggimenu (4.832 items), menudigitale (242 items dopo filtro Milano).
- **Da 174 → 629 price points** in un colpo solo. Leggimenu il game-changer.
- **Problema risolto**: menudigitale conteneva 12.600 items NAZIONALI. Filtrato a sole 2 venues Milano confermate (Corner, Mulberry) per non inquinare il DB.
- **Problema risolto**: leggimenu venues senza geo → 2 match esatti DB + 39 fallback Milano centro. Da geocodare con precisione in sessione futura.

### Funky beer split fix
- **Bug parser PDF**: "Moretti IPA € 6,00 € 7,00" parsato come €13 (somma).
- **Fix**: split in 2 righe: piccola €6, media €7.
- **Stessa cosa**: Ichnusa €5+€6, vini in bottiglia €25 ma calice €6.

---

## 2026-05-30 — Setup iniziale

### Decisione: MyCIA come prima fonte (CEO)
- 648 Milano venues dal sitemap MyCIA. 122 con menu completo, 471 filtered_out (ristoranti).
- **Decisione**: scope "bar/pub/cocktail bar" → tutto il resto fuori.

### Decisione: Wolt NON in Italia
- Testato Wolt API → Italia non presente nel sitemap (verificato).
- **Impatto**: Pietro 1 deve sostituire Wolt con Glovo nella sua lista fonti.

### Decisione: NO Wolt/Glovo via API
- Wolt: API "We've updated the app" → bloccato.
- Glovo: richiede `Glovo-Perseus-Session-Id` real → solo Playwright.
- **Impatto**: rimandato a sessione Playwright dedicata.

### Decisione: qromo NON estratto
- robots.txt vieta `/API` esplicitamente.
- 25 venues nel DB come record (per discoverability), ma 0 items.
- **MAI tentare di bypassare**: progetto pubblico, no rischi legali.

---

## Convenzioni progetto

### Struttura raw_sources/
- **Naming**: `{fonte}_{venues|menu_items}.csv` — singolare fonte, plurale entità
- **Esempio**: `thefork_venues.csv` + `thefork_menu_items.csv`
- **Per re-scraping nuovi**: prefisso `agentN_` (es. `agent2_direct_website_*.csv`)
- **NO cartelle per-collaboratore**: silos cattivi. Naming già identifica autore via prefix.

### Quality gates pre-commit
Lista bloccanti applicata da CEO PRIMA di ogni merge:
1. Niente URL immagine (`.jpg/.png/.webp/.ico/.css/.js`)
2. Niente venues fuori Milano (verifica city/address)
3. Niente false positive contesto ("americano" su whiskey, "white_wine" su pasta)
4. Niente prezzi < €0.50 o > €100 senza review
5. Niente venue_name = titolo pagina HTML

### Geocoding policy
1. Match contro DB esistente (threshold 0.85 sequence match)
2. Se no match → Nominatim (1 req/s, free)
3. Se no match → Milano centro (`45.4642, 9.1900`) come fallback
4. Mark `geocoding_confidence` in metadata se importante distinguere

### Schema CSV
SEMPRE in linea con `scripts/SCHEMA_AGENTI.md`. Header obbligatorio. UTF-8 BOM.
