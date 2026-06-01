# Stato corrente del dataset — aggiornato 02/06/2026 (Pietro S4 + Peppe Phase3)

> **SurPrice** = multi-vertical price intelligence. Vertical attivi: **drink** (Milano), **beach** (Italia).

---

## 🏖️ VERTICAL BEACH (Peppe Phase 3 chiusa)

| Metrica | Valore |
|---|---|
| **Master venues consolidato** | **13.646** (file: `raw_sources/beach_master_venues.csv`) |
| Coordinate geo precise | 13.635 (99%) |
| Con city/region popolati | ~6.700 (49%) |
| Con `booking_provider` mappato | 6.203 (45% — spiagge.it via sitemap S2X) |
| Con amenities normalizzate | 4.127 (30% — 15+ servizi vocabolario chiuso) |
| **Price items raccolti** | **3.443** (S1 214 + S2 55 + Phase3 3.174) |
| **Venues prezzate** | **1.731** (12.7% del master) |
| **Confidence high** | **3.420 (99.3%)** |
| Provider booking identificati | 8 (spiagge.it dominant 6.203 venues) |

### Breakthrough tecnico Phase 3 (Peppe)
- **Discovery critica**: spiagge.it espone prezzi via query string `?from=&to=` direttamente nel HTML SSR. NO Playwright necessario.
- **Risparmio**: 70x più veloce di Playwright (25 min vs 25h stimate)
- **Pattern**: `"price":N`, `"stagingItems":"1U_2B"`, `"bookingAvailable":true|false`
- **Zero anti-bot**: requests puro funziona, no captcha

### Breakdown items beach
| Source | Items | Note |
|---|---|---|
| spiagge.it (Phase 3) | 3.174 | 2 slot/venue: peak Aug + mid Jun |
| direct_website (S2) | 252 | Siti propri |
| bibionemare (S1) | 17 | Consorzio |

### Geographic spread items
- Peak Aug median: €150/settimana (2 lettini + ombrellone)
- Mid Jun median: €126/settimana (spread +19%)
- Sud Italia: **524 venues prezzati** (era 5 in S2 = +10.380%)
- Tutte 17 regioni costiere coperte

### File beach raw_sources
beach_master_venues.csv, beach_s1_*, beach_s2_*, beach_s2x_*, beach_phase3_*

### Composizione master beach
- 9.252 venues OSM (S1, foundation geografica)
- 4.394 venues spiagge.it NON in OSM (S2X, marketplace-only commerciali)
- 6.682 venues spiagge.it overlap → arricchiti come master (city/region/provider/amenities)

### Copertura geografica beach (top regioni)
Emilia-Romagna 898 | Toscana 811 | Liguria 757 | Lazio 582 | Campania 529 | Puglia 511 | Marche 496 | Abruzzo 419 | Calabria 380 | Sicilia 279

### Status vertical beach
- ✅ Master list completata (acquisition)
- ⚠️ Prezzi parziali: 37/13.646 venues = 0.3% coverage. **Phase D = Playwright spiagge.it** = next big push.
- ❌ Frontend integration non ancora fatto (è S3 beach)

---

## 🍹 VERTICAL DRINK (Milano) — post merge Pietro S4

| Metrica | Valore |
|---|---|
| **Venues totali nel DB** | **1.601** |
| **Venues uniche sulla mappa** | **161** (139 precise + 23 fallback) |
| **Items menu totali** | 5.708 |
| **Price points geo+normalizzati** | **1.080** |
| **Venue-product pairs** | 723 |
| **Prodotti coperti** | 22 |

### Pietro S4 deep-scan (commit 733925e)
- 88 venues re-processate dalla lista CEO (1-3 items DB pre-merge)
- 66/88 venue con nuovi drink estratti (75% yield)
- 236 items puliti dopo quality gate inline
- Top yield: Caffè Fernanda +10, Norin Caffè Bistrot +10, Papeete +8, Refeel +8, Armanisilos +8
- Distribuzione prodotti: spritz +35, negroni +34, americano +25, espresso +24, beer_bottle +20
- Confidence: 100% medium (re-extraction, downgrade da high)
- Quality gate 0 issues

### Cleanup CEO 02/06 (merge agent4 + audit completo)
- Mergiato agent4 (TheFork via Wayback, eatbu, leggimenu, glovo) → 35 venues, 100 items consegnati
- Quality fix agent4: rimossi 4 venues (BAR MILAN/San Colombano, Maki Poke dupe, Casa Fassona title, Officina recensioni) + 22 items (Don Vincè €6 FP, Refeel Piscolada FP, aperitivo bundle)
- **Bug merge_pipeline fixato**: filtro CAP non-Milano inline → 22 venues legacy mycia fuori Milano scartate (es. Misano Adriatico, Roma, Cagliari, Palermo)
- **Ghost canonical merger**: 56 canonical duplicate con stesso nome ma lat='' uniti al canonical principale con geo → +15 price points recuperati
- Filtro inline `item_name` parser noise: items < 3 char clean o "menu prezzo fisso" descrittivi
- Filtro inline beach files dal merge drink (vertical separation netta)

### Pre-merge (riferimento)
Pre-merge agent4: 924 → post-merge + cleanup: **939** (+15 netti).

> Questo file dice **cosa è già fatto** e **cosa serve ancora**.
> Aggiornare dopo ogni merge.

---

## 📊 Numeri attuali

| Metrica | Valore |
|---|---|
| **Venues totali nel DB** | **1.644** |
| **Venues uniche sulla mappa** (con prezzo + geo) | **158** |
| **Items menu totali** | 5.487 |
| **Price points geo+normalizzati** (sito) | **924** |
| **Venue-product pairs** | 613 |
| **Prodotti coperti** | 22 |

> **Nota 01/06 (merge Pietro S3)**: +78 price points, +8 venues mappa, +85 items. Mergiato output Pietro S3 (leggimenu_s3 brute-force + osm_direct2). **WARNING**: leggimenu brute-force ha pescato 127 venues di tutta Italia, solo 15 sono effettivamente Milano (CAP 20xxx). Filtrati 112 venues non-Milan e 7932 items relativi. Tenuti 15 venues Milano + 703 items. osm_direct2: 86 venues (62 con geo precisa), 44 items. Bug double-letter Mulligan's items corretto (HHAARRPP→HARP).

---

## ✅ Cosa è GIÀ stato scrappato (non rifare)

| Source | Venues | Items | Status | Note |
|---|---:|---:|---|---|
| **leggimenu** | 41 | 4.832 | ✅ COMPLETO | Tutte le venues Milano coperte, prezzi server-side. 39 venues su Milano centro per geocoding mancante |
| **mycia** | 648 | 1.102 | ✅ COMPLETO | Sitemap completo. 471 filtered_out (non bar), 122 ok_with_menu (estratti), 27 ok_no_menu (proprietario non ha caricato), 28 no_category. NON c'è altro da estrarre |
| **menudigitale** | 111 | 242 | ✅ COMPLETO | 109 venues filtrate (non Milano), solo 2 Milano (Corner, Mulberry) entrambe estratte |
| **direct_website (Pietro 1)** | 47 | 120 | ✅ COMPLETO | Prima sessione Pietro |
| **agent2_direct_website (Pietro 2)** | 46 | 92 | ✅ COMPLETO | Seconda sessione Pietro - smart rescan cache |
| **PDF (dish.co)** | 4 | 52 | ✅ COMPLETO | Deseo, Abbracci, Casa Giuditta, Funky |
| **eatbu** | 4 | 15 | ✅ COMPLETO | Caffè Inn, Growler, Cris Bar |
| **qodeup** | 2 | 13 | ✅ COMPLETO | Woodstock + 1 altro |
| **scraper (vecchi)** | 850 | 36 | ✅ PARZIALE | Coverage estesa ma pochi items - sostituito da agent2 |
| **qromo** | 25 | 0 | ⛔ LEGALE BLOCK | robots.txt vieta `/API`. Non scrappare items |
| **web_extracted** (Peppe sera) | 505 | 441 | ✅ COMPLETO | nome→Startpage→sito ufficiale→menu. Hit rate 6.7% (34/505) |
| **pdf_googledork** (Peppe sera) | 7 | 81 | ✅ COMPLETO | PDF dai siti diretti già noti. Multi-colonna parsing |
| **comune_osm** (Peppe sera) | 4.649 | 0 | ✅ BASE GEO | Open data Comune Milano × OSM. Solo venues+geo, NO prezzi. Usare per discovery |

---

## ❌ Cosa NON è ancora stato fatto (TODO)

### 🟢 Priorità ALTA (alto valore, fattibile)

1. **TheFork Milano** (~50-100 venues stimati)
   - Bloccato da Datadome CAPTCHA con requests
   - **Richiede Playwright + stealth mode**
   - URL pattern: `https://www.thefork.com/restaurant/{slug}-r{id}`
   - Output: `raw_sources/thefork_*.csv`

2. **Geocoding preciso 39 venues leggimenu**
   - Attualmente stackate su Piazza Duomo (coordinate Milano centro)
   - Strategia: Nominatim (free, 1 req/s) o Google Geocoding (richiede API key)
   - Lista venues in `raw_sources/leggimenu_venues.csv` filtrate per `latitude == 45.4642`

3. **leggimenu discovery espansa**
   - Solo 41 venues nel sitemap Milano, ma leggimenu.it ne ha sicuramente di più
   - Strategia: Google "site:leggimenu.it milano" + parsing risultati
   - Cross-ref con OSM bar Milano per scoprire URL nascosti

### 🟡 Priorità MEDIA

4. **Glovo Milano** — delivery prezzi
   - Richiede Playwright + sessione reale (cookies)
   - Solo per `price_type=delivery` (prezzo maggiorato vs banco)

5. **JustEat.it Milano** — delivery
   - SPA Next.js, richiede Playwright
   - Categoria "bar" probabilmente molto limitata

6. **Foto Google Maps OCR**
   - Vision API per estrarre prezzi da foto menu
   - Costo: ~$1.50/1000 immagini

### 🔴 Priorità BASSA (basso ROI)

7. **Siti web diretti residui (~700 OSM con website)**
   - Hit rate ~1-5% (la maggior parte non ha menu strutturato)
   - Tempo speso > valore ottenuto
   - Solo da fare se altri pipeline esaurite

8. **TripAdvisor Italia**
   - Cloudflare anti-bot pesante
   - Pochi prezzi pubblici comunque

---

## 🚫 Bloccato / non fattibile

| Fonte | Motivo |
|---|---|
| Wolt | NON opera in Italia |
| Deliveroo | Uscita Italia 2022 |
| Uber Eats | Uscita Italia 2021 |
| qromo /API | robots.txt vieta esplicitamente |
| Instagram menu | Solo bio, no prezzi |
| Reddit threads | IP residenziale richiesto |

---

## 🎯 Target finale realistico

Con il completamento di TheFork + geocoding preciso:
- **800-1.000 venues sulla mappa**
- **1.500-2.000 price points**
- **25+ prodotti** con coverage decente
- Tutti i quartieri Milano rappresentati

Allo stato attuale (738 price points) abbiamo un MVP solido. I prossimi step sono "ottimizzazione qualità" più che "espansione quantità".
