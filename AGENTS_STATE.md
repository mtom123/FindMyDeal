# Stato corrente del dataset — aggiornato 01/06/2026

> Questo file dice **cosa è già fatto** e **cosa serve ancora**.
> Aggiornare dopo ogni merge.

---

## 📊 Numeri attuali

| Metrica | Valore |
|---|---|
| **Venues totali nel DB** | **1.558** (+ 499 da open data Comune) |
| **Venues uniche sulla mappa** (con prezzo + geo) | **146** |
| **Items menu totali** | 5.361 |
| **Price points geo+normalizzati** (sito) | **829** |
| **Venue-product pairs** | 547 |
| **Prodotti coperti** | 22 |

> **Nota 01/06**: -6 venue non-Milan rimosse (Pub51/PA, Coco Loco/LE, Bivacco/TN, Birra Bader/SI, Canaglie del Navigli/PR, SOLO APERITIVO popup/FE). +29 venue leggimenu geocodate con precisione (Pietro). Price points scesi da 888 a 829 per la pulizia non-Milan.

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
