# Changelog — FoodPrice Milano

> Storico decisioni, problemi risolti, ragionamenti.
> Aggiornare dopo ogni merge o decisione di design importante.
> Formato: data → cosa è successo → perché → impatto.

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
