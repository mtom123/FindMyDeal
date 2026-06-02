# Barber S1 — Report CEO (02/06/2026)

## Executive Summary

Lanciato il 3° vertical SurPrice (barber/parrucchieri). In una sessione di lavoro:
**12.019 venue italiane prezzate, 10.709 con prezzi reali, 21 regioni coperte**.
Database unificato pronto per frontend (`data/barber_data.json`, 16 MB).

Strategia high-signal first ha funzionato: ~3 ore totali vs ~25 ore stimate
con approccio web-wide. Treatwell SSR + window.__state__ extraction = sorgente d'oro.

---

## Numeri assoluti

| Metrica | Valore |
|---|---|
| **Venue unificate (master)** | **12.019** |
| **Venue con prezzi reali** | **10.709 (89%)** |
| **Items prezzati totali** | ~395.000 |
| **Regioni coperte** | 21 (tutte le italiane) |
| **Tempo run totale** | ~3 ore |
| **Costi token** | basso (operazioni in background, no API) |

### Breakdown sorgenti

| Sorgente | Venue raw | Prezzate | Items | Tempo | Note |
|---|---|---|---|---|---|
| **Treatwell** | 20.185 → 11.331 (post-filter) | 10.426 | 387.120 | 142 min | Primary source, SSR puro |
| **Fresha** | 1.151 → 840 (geo IT only) | 814 | 19.023 | 12 min | Secondary, alta qualità dati |
| **Uala** | 0 | — | — | 0 | **DOMINIO ACQUISITO DA TREATWELL** — redirect 302. Già incluso in Treatwell. |
| **Booksy** | non fatto | — | — | — | Prezzi dietro login, basso ROI |
| **Post-dedup unified** | **12.019** | **10.709** | 395k | — | Geo + name match ≤80m |

---

## Cosa abbiamo scoperto sui provider

### Treatwell (✅ JACKPOT)
- 20.399 venue Italia totali nel sitemap (incluse beauty/nail/massage non-barber)
- 11.331 sono effettivamente barber/hair (56%) — filtrate per servizi
- **Window.__state__** JSON nella pagina = tutto strutturato:
  nome, indirizzo geocodificato, servizi con prezzi, rating, contatti
- SSR puro, zero JS rendering necessario
- Rate sostenuto: 175 venue/min con 4 thread @ 1.2s delay
- Anti-bot: nessuno (Cloudflare base, headers standard ok)

### Fresha (✅ ottimo)
- ~24k URL "Italia" nel sitemap MA solo 1.151 sono pagine venue ricche (`/a/`)
- Le altre 23k sono "lite venue pages" (`/lvp/`) — SEO landing senza prezzi
- Su 1.151 `/a/`: 840 sono effettivamente in Italia (filtro geo bbox)
- Le altre 311 sono in Romania/Svizzera/Moldova/Panama (toponimi "via-" comuni)
- NEXT_DATA → location.services array con priceRange = perfetto
- 97% delle venue ha prezzi (814/840)
- 12 min per estrarre tutto

### Uala (⚠️ SKIP)
- `uala.it` → HTTP 302 → `treatwell.it`
- Acquisita da Treatwell, dominio è solo alias
- Tutte le venue Uala sono già nel master Treatwell

### Booksy (❌ non fattibile)
- Prezzi nascosti dietro login
- Solo discovery senza prezzi = basso ROI

---

## Quality assessment

### Punti di forza
- **89% delle venue ha prezzi reali** (vs 13% beach vertical)
- **Geo precisa** su 99% delle venue (lat/lon da JSON-LD strutturato)
- **Vocabolario chiuso 23 servizi** già normalizzato (`scripts/normalization.py`)
- **Confidence high** sul 99% items (estratti da JSON strutturato, non DOM regex)
- Tutte le 21 regioni italiane coperte

### Issue noti / debito tecnico
- **1.373 venue con city "Sconosciuta"** (11%) — geo OK ma city vuota in source
  - Fix: reverse geocoding via Nominatim (1 req/s, ~25 min)
- **283k items "unclassified"** (servizi non hair: massaggi, nail, etc.)
  - Già filtrati dal `barber_data.json` ma rimangono nel master items per analisi
- **Roma/Milano duplicate naming**: già normalizzato ("Roma" + "Roma (RM)" → "Roma")
- **Categories barber**: 95% "unisex" (default), solo 5% identificate come "barber" o "salon_donna"
  - Fix: classificazione più rigorosa basata su mix servizi (>50% uomo → barber)

### Cosa NON è stato fatto (backlog S2)
1. Reverse geocoding venue senza city
2. Classificazione barber_category più precisa
3. Booksy discovery (anche solo metadata, no prezzi)
4. Cross-validation prezzi Treatwell vs Fresha per venue overlap
5. Enrichment Google Maps per rating/foto (solo metadata, no scraping mappa)
6. OSM coverage gap analysis (venue offline non sui marketplace)

---

## Distribuzione geografica (top 15 città)

| Città | Venue | Prezzate |
|---|---|---|
| Sconosciuta* | 1.373 | 1.234 |
| Roma | 1.007 | 848 |
| Milano | 660 | 563 |
| Torino | 195 | 178 |
| Napoli | 132 | 119 |
| Bologna | 70 | 64 |
| Firenze | 68 | 57 |
| Verona | 67 | 64 |
| Cagliari | ~50 | ~45 |
| Palermo | ~50 | ~45 |
| Bergamo | ~50 | ~48 |
| Bari | ~45 | ~40 |
| Genova | ~45 | ~40 |
| Modena | ~45 | ~40 |
| Latina | ~40 | ~35 |

\* `Sconosciuta` = geo OK ma city non popolata in source. Reverse geocoding in S2.

---

## Statistiche servizi (medianas Italia)

| Servizio | Venue offerenti | Mediana € |
|---|---|---|
| Taglio Uomo | 7.936 | 15 |
| Trattamento | 6.692 | 35 |
| Piega | 3.970 | 18 |
| Sopracciglia | 3.676 | 10 |
| Colore Capelli | 3.587 | 44 |
| Taglio Donna | 3.055 | 25 |
| Mèches / Colpi di Sole | 2.230 | 70 |
| Rifilatura Barba | 1.805 | 12 |
| Acconciatura cerimonia | 1.746 | 50 |
| Stiratura | 1.512 | 140 |

**Insight commerciale**: il taglio uomo a €15 mediano nasconde varianza enorme
(da €8 a €70). Su Milano centro la mediana è probabilmente €25-30. La trasparenza
prezzi qui ha value prop chiaro.

---

## File prodotti

### Raw data
- `raw_sources/barber_s1_treatwell_venues.csv` — 20.185 venue Treatwell (incl. non-barber)
- `raw_sources/barber_s1_master_venues.csv` — 11.331 Treatwell post-filter barber/hair
- `raw_sources/barber_s1_master_items.csv` — 387.120 items
- `raw_sources/barber_s1_fresha_master_venues.csv` — 840 Fresha Italia
- `raw_sources/barber_s1_fresha_master_items.csv` — 19.023 items
- `raw_sources/barber_s1_fresha_italy_urls.txt` — 1.151 URLs discovered (cache)

### Unified
- `raw_sources/barber_unified_venues.csv` — **12.019 venue dedupplicate**
- `raw_sources/barber_unified_items.csv` — items dedupplicati per venue

### Frontend
- `data/barber_data.json` — **16 MB** feed pronto per `index.html`

### Scripts
- `scripts/barber_s1_treatwell.py` — scraper Treatwell (riutilizzabile S2)
- `scripts/barber_s1_fresha.py` — scraper Fresha
- `scripts/barber_s1_consolidate.py` — merge + dedup + JSON feed
- `scripts/barber_s1_postprocess.py` — filtro barber/hair sul raw Treatwell

---

## Decisioni architetturali da validare

1. **`barber_data.json` come feed unico** o split per regione (lazy load)?
   16 MB è gestibile ma su mobile potrebbe pesare. Suggerisco split per regione
   se l'adoption mobile è alta.

2. **Prezzo "min" o "mediana" come display principale?**
   Beach usa "min". Per i barber il min può essere fuorviante (es. €5 "ritocco barba" vs €30 taglio).
   Suggerisco: filtro frontend per servizio → mostra min di QUELLO specifico servizio.

3. **Booksy vale la pena?**
   No price extraction possibile, solo metadata. Skip per S1, valutare in S2 solo
   se vogliamo "discovery completa" (anche venue non prenotabili sui big marketplace).

4. **Frequenza refresh dati?**
   Prezzi cambiano stagionalmente (collezione AW/SS) ma listino raramente.
   Suggerisco refresh trimestrale, con monitoring spot su 100 venue al mese.

---

## Confronto con altri vertical SurPrice

| Vertical | Venue | % prezzate | Mediana copertura prezzi |
|---|---|---:|---:|
| Drink Milano | 1.601 | 9.6% | 22 prodotti |
| Beach Italia | 13.646 | 12.7% | 6 servizi |
| **Barber Italia** | **12.019** | **89.1%** | **21 servizi** |

Il barber vertical ha **la copertura prezzi più alta in assoluto** — perché i provider
booking (Treatwell, Fresha) richiedono di pubblicare il listino. Strutturalmente migliore
per price intelligence.

---

## Prossimi step suggeriti

### Immediati (questa settimana)
1. **Frontend integration** (Peppe) — vedi `barber_s1_REPORT_PEPPE.md`
2. **Reverse geocoding** delle 1.373 venue "Sconosciuta" → +11% city coverage
3. **Push to main** + deploy preview

### Medio termine (S2)
1. **Booksy discovery** (solo metadata, no prezzi)
2. **OSM gap analysis**: venue barber italiane non su marketplace
3. **Cross-source price validation**: per le ~150 venue su entrambi TW+FR, confronto prezzi
4. **Refresh pipeline**: weekly delta check sui 12k venue (~1h con threading)

### Long term
- **Pricing tier autoclassification** (€/€€/€€€) per ogni venue
- **Time series**: stoccare snapshot mensili per detectare price hikes
- **API esterna**: monetizzazione dati a aggregatori/concierge services

---

CEO sign-off needed:
- [ ] Push to main + tag `barber-s1-complete`
- [ ] Aggiornare `AGENTS_STATE.md` con metriche finali barber
- [ ] Comunicare a Peppe il green light per frontend integration
