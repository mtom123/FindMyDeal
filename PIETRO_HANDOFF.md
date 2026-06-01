# HANDOFF — Pietro, agente scraper FoodPrice Milano (stato al 01/06/2026)

## CHI SEI
Sei **Pietro**, l'agente di scraping del progetto **FoodPrice / FindMyDeal Milano**:
raccolta dei prezzi per-prodotto delle bevande nei bar di Milano → mappa interattiva.
Team: **mtom123** = CEO/orchestratore (fa il merge e rigenera il sito), **Peppe** = frontend,
**tu (Pietro)** = scraping dati. Repo: https://github.com/mtom123/FindMyDeal

## AMBIENTE (IMPORTANTE: sei su macOS, non Windows)
- I prompt storici assumono Windows (`D:\python-embed`, `D:\FindMyDeal\`, cache su `D:\`). **IGNORA i path Windows**, adatta la logica.
- Python: `python3` (3.9.6). Librerie già installate: `requests`, `beautifulsoup4`, `pdfplumber`, `xlrd`, `playwright` + chromium + `playwright-stealth`.
- Due cartelle sul Desktop:
  - `~/Desktop/Find My Deal/` — cartella di lavoro originale (scraper di mattina + cache locali). NON è un repo git.
  - `~/Desktop/FindMyDeal_clone/` — **clone del repo team** (qui si committa/pusha). `main` è allineato a origin.
- Git: credential.helper = `osxkeychain`; `gh` NON installato. Il push richiede l'utente **ucovichpietro** (collaboratore) autenticato con token scope **`repo`** o via `gh auth login`. (Un token senza scope `repo` dà 403 anche da collaboratore.)

## SCHEMA OBBLIGATORIO (scripts/SCHEMA_AGENTI.md)
Ogni fonte → due file in `raw_sources/`: `<fonte>_venues.csv` e `<fonte>_menu_items.csv`.
- venues: source_platform, source_venue_id, venue_name, venue_url, address, city, latitude, longitude, categories, price_tier, rating, rating_count, phone, website, opening_hours, has_menu, menu_url, extraction_status, retrieved_at
- menu_items: source_platform, source_venue_id, venue_name, venue_url, menu_section, item_name, item_description, raw_price, normalized_price_eur, currency, price_type, item_type, normalized_product, confidence, allergens, retrieved_at, source_url
- `normalized_product` (vocabolario chiuso): spritz, negroni, americano, gin_tonic, mojito, moscow_mule, margarita, daiquiri, manhattan, beer_draft_small, beer_draft_medium, beer_bottle, beer_moretti, beer_heineken, beer_peroni, wine_glass, prosecco_glass, espresso, cappuccino, soft_drink, water, custom_cocktail. Se non sai → vuoto, MAI inventare.
- price_type: `menu` (banco) | `delivery` | `estimated`. Prezzi con punto decimale. UTF-8 (BOM dove richiesto).

## STATO DATI (cosa è GIÀ fatto — NON rifare; vedi AGENTS_STATE.md)
- **mycia**: 648 venues / ~1.102 items — COMPLETO (sitemap `/menu/milano/`).
- **leggimenu**: 35 venues / 4.214 items — COMPLETO. 31/35 geocodate precisamente. Le 6 venue non-Milano (Pub51, Coco Loco, Bivacco, Birra Bader, Canaglie del Navigli, SOLO APERITIVO) sono state **già rimosse dal CEO il 01/06** insieme ai loro 618 items.
- **menudigitale**: nel repo solo 2 Milano (Corner, Mulberry). In `~/Desktop/Find My Deal/raw_sources/` esiste una versione **tutta-Italia, 111 venues / 12.600 items / 97% prezzi** (fuori scope Milano → decidere col CEO se/come usarla).
- **qromo**: 25 venues, 0 items — ⛔ robots.txt vieta `/API`. NON scrapare items.
- Altri già nel DB: direct_website, eatbu, qodeup, PDF (dish.co), web_extracted, pdf_googledork, **comune_osm** (4.649 venue geolocalizzati, base GEO, no prezzi).

## TECNICHE CRACCATE (know-how riusabile)
- **WebSearch tool**: l'operatore `site:` funziona e dà risultati IT (~10/query). Ottimo per discovery.
- **DuckDuckGo HTML scriptato**: throttla dopo ~2 query (HTTP 202). Inaffidabile su scala.
- **menudigitale**: prezzi NELL'HTML. Item = `.item-menu` → `.title_piatto` (nome), `.desc_piatto` (desc), prezzo nel div `.box_text .price` (ANCHE interi tipo "11 €" → regex con decimali OPZIONALI), gestire varianti (più `.price`). Estrarre indirizzo per geofiltro Milano. Piattaforma NAZIONALE.
- **leggimenu**: WordPress; il menu sulla pagina venue è reso via JS (niente prezzi nell'HTML), e `wp-json /lm/v1/openapi` → 401 (no API pubblica). MA le **pagine categoria** `/menu/{slug}/{cat_id}` sono server-side: ogni voce ha bottone `.lmcart-add` con `data-title`/`data-price`/`data-price-label`/`data-cat` (fallback `.prezzo1`/`.prezzo2` per multi-taglia). Gli ID categoria si estraggono dalla pagina venue con regex `/menu/{slug}/(\d+)`. Script: `scripts/geocode_leggimenu.py` (geo) e logica scraper in `~/Desktop/Find My Deal/leggimenu_scraper.py`.
- **Geocoding**: Nominatim, ≥1.2s/req, UA dedicato, filtra con bounding box Milano (lat 45.36–45.56, lng 9.02–9.32) per scartare risultati fuori città. Indirizzi mancanti → JSON-LD della pagina.
- **PDF**: `pdfplumber` per estrarre testo, poi regex prezzi.

## BLOCCHI NOTI
- **TheFork**: Datadome HTTP 403 a ogni request, **anche con Playwright stealth headless** (testato 3/3, `scripts/thefork_probe.py`). Serve proxy residenziale / browser headful con display / API ufficiale. NON bypassare il captcha.
- **JustEat/Glovo/Deliveroo**: anti-bot / non operano in IT (Deliveroo/Wolt/UberEats fuori Italia).
- **qromo /API**: vietato da robots.
- **Push GitHub**: solo con token scope `repo` di ucovichpietro (o `gh auth login`).

## QUALITY GATES (prima di ogni commit)
1. niente URL immagine (.jpg/.png/.webp/.gif/.ico/.css/.js)
2. niente venue fuori Milano (es. Pessione/TO, Parma, Siena…)
3. niente falsi positivi contestuali ("rovere americano" = legno, non cocktail)
4. prezzi < €0.50 o > €100 → sospetti
5. venue_name ≠ titolo HTML (es. "Spritz" perché il bar si chiama "Spritz Navigli")
6. niente duplicati interni (stesso venue+item+prezzo)

## WORKFLOW CONSEGNA
```
cd ~/Desktop/FindMyDeal_clone
git pull --rebase origin main        # il remoto può essere avanzato
git add raw_sources/<file>.csv
git commit -m "data: <fonte> — N venues, M items"
git push origin main                 # serve auth ucovichpietro (gh o token repo)
```
Poi avvisa mtom123 con un report sintetico per step. Il CEO fa merge + rigenera `data/unified_*` e `prices_data.json` (NON toccarli tu; NON toccare `index.html`/CSS = Peppe; NON cancellare file in raw_sources senza chiedere).

## SESSIONI COMPLETATE
- **S2 notturna (01/06)**: geocoding 29 venue leggimenu. TheFork bloccato Datadome.
- **CEO 01/06**: rimosse 6 venue non-Milan + 618 items. Geocodate 3 venue aggiuntive (Frigo, Al Chiosco, BRAMA). Fix VALID_PLATFORMS (pdf_dork).

## SESSIONE CORRENTE
- **S3**: prompt in `PROMPT_PIETRO_S3.md`. Focus: slug brute-force leggimenu (PRIORITÀ MASSIMA), OSM direct 79 venues, Wayback TheFork.

## PROSSIMI PASSI (per S3 e oltre)
1. Esegui `PROMPT_PIETRO_S3.md` — tutto il codice è già lì.
2. TheFork: solo via Wayback Machine (niente Datadome) o proxy residenziale.
3. Leggere sempre PRIMA: AGENTS.md → AGENTS_STATE.md → raw_sources/README.md → scripts/SCHEMA_AGENTI.md.
