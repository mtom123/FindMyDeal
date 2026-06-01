# Ricerca notturna CEO (modalità scraper bestiale) — 02/06/2026

> **Trigger**: "metti i panni dello scraper, esplora nuove vie, parti in autonomia, cracca le barriere"
>
> **Tempo**: ~45 minuti effettivi (8 batch di test)
>
> **Output bottom-line**: **3.815 nuovi venues drink Milano** scoperti + 4 nuove tecniche documentate.

---

## Piano eseguito (8 fronti)

| # | Target | Tecnica | Esito |
|---|---|---|---|
| 1 | TheFork prezzi live | `curl_cffi` TLS impersonate Chrome/Safari | 🟡 PARZIALE — bypass HTTP 403 con `safari17_2_ios`, ma menu items via JS lazy (no SSR) |
| 2 | eatbu 11 venues Pietro discovered | Path probing + JSON-LD + PDF detection | 🟡 PARZIALE — 11 metadata (geo+addr) salvati, 0 prezzi (no PDF tranne ITTOLITTOS = food) |
| 3 | Yelp.it Milano cocktail bar | JSON-LD + business pages | ❌ FAIL — niente prezzi, solo metadata |
| 4 | Quandoo.it Milano | curl_cffi | ❌ FAIL — HTTP 404 (probabilmente cambio struttura URL) |
| 5 | Michelin Guide Milano | curl_cffi | ❌ FAIL — HTTP 404 |
| 6 | Glovo Wayback bulk | CDX API matchType=prefix | ❌ FAIL — solo 4 URL venue totali su 13 zone |
| 7 | Glovo live | curl_cffi | ❌ FAIL — SSR vuoto, prodotti via JS XHR |
| 8 | **CKAN Comune Milano** | API package_search + download CSV | ✅ **WIN — 3.804 venues drink Milano nuove** |
| 9 | Siti propri 11 eatbu venues | DNS guess + curl_cffi | ❌ FAIL — solo ittolittos.it esiste |

---

## 🏆 BOTTINO PRINCIPALE — CKAN Comune Milano

### Dataset scoperto
**API CKAN ufficiale**: `https://dati.comune.milano.it/api/3/action/package_search`

Dataset rilevanti trovati:
- `ds58_economia_pubblici_esercizi_in_piano` — 9.417 esercizi commerciali Milano
- `ds59_economia_pubblici_esercizi_fuori_piano` — 3.717 esercizi extra
- **Totale: 13.143 esercizi pubblici Milano** con geo + categoria licenza + quartiere (NIL)

### Filtro applicato per drink-target
```python
DRINK_CATEGORIES = {
    'f - bar caffè e simili': 'cafe',
    'e - bar gastronomici e simili': 'bar',
    'g - bar pasticceria, bar gelateria': 'cafe',
    'h - wine bar, birreria, pub enoteche': 'pub',
    'i - disco bar, america bar, locali serali': 'cocktail_bar',
    'j - discoteche, sale da ballo': 'cocktail_bar',
}
```

### Risultato dopo dedup vs DB attuale
- 3.840 venues TARGET (bar/caffè/pasticceria) → **3.804 NON ancora nel DB drink**
- Distribuzione venue_type:
  - `cafe`: 2.620
  - `bar`: 848
  - `pub`: 317
  - `cocktail_bar`: 19

Tutti con geo precisa, CAP, indirizzo verificato Comune, quartiere (NIL).

### Top 10 quartieri Milano coperti
| Quartiere (NIL) | Venues |
|---|---|
| Buenos Aires - Porta Venezia - Porta Monforte | 317 |
| Duomo | 315 |
| Brera | 189 |
| Sarpi | 150 |
| Guastalla | 133 |
| Porta Ticinese - Conchetta | 131 |
| XXII Marzo | 131 |
| Loreto - Casoretto - NoLo | 126 |
| Porta Ticinese - Conca del Naviglio | 126 |
| Isola | 125 |

### Output
File: `agent_ceo_night/agent_ceo_ckan_venues_no_price.csv`
- 3.804 righe
- Schema esteso: + `venue_type`, `nil_quartiere`

### Cosa serve dopo (per Pietro S6 / S7)
1. **Cross-ref OSM Overpass** per recuperare nome commerciale (es. "Bar Magenta" non "Bar Via Carducci 13"). Pietro l'aveva già fatto per beach in comune_osm_venues.csv → applicare stesso pattern.
2. Cluster CKAN + DB esistente per dedup nominal.

---

## 🟡 BOTTINO SECONDARIO — eatbu 11 venues metadata

### Discovery
Pietro S5 aveva identificato 11 venues eatbu Milano nuovi. Stanotte ho preso i loro metadata completi.

| Venue | Indirizzo | Geo |
|---|---|---|
| Amami | Corso Sempione 7, 20145 | 45.4770, 9.1701 |
| NICE CAFE' | Via Roberto Lepetit 3, 20124 | 45.4824, 9.2035 |
| Wave Cocktail Bar | Via Edmondo de Amicis 28, 20123 | 45.4626, 9.1816 |
| MOSCOVA 22 | Via della Moscova 22, 20121 | 45.4765, 9.1920 |
| ALKEMIA | Corso 22 Marzo 42, 20135 | 45.4620, 9.2196 |
| BOND MILANO | Via Pasquale Paoli 2, 20143 | 45.4508, 9.1714 |
| drinc. different. | Via Francesco Hayez 13, 20129 | 45.4753, 9.2162 |
| Bar Miro | Corso Buenos Aires 30, 20124 | 45.4783, 9.2093 |
| Bootleg Pub | Via Coluccio Salutati 2, 20144 | 45.4638, 9.1604 |
| ITTOLITTOS | Via Francesco Olgiati 25, 20143 | 45.4404, 9.1462 |
| UNPLUG | Corso Lodi 8/C, 20135 | 45.4505, 9.2044 |

**Caratteristica chiave**: tutti i venues eatbu espongono **JSON-LD `Restaurant`** completo nel HTML SSR. Nessun prezzo statico (caricati via Vue.js XHR sul `?lang=it` post-render). Per i prezzi serve Playwright o reverse del payload API.

### Output
File: `agent_ceo_night/agent_ceo_eatbu_venues.csv`
- 11 venues con extraction_status="ok_no_static_prices"

---

## 🔧 SCOPERTA TECNICA — curl_cffi TLS fingerprint

### Problema
Datadome blocca tutti gli HTTP client standard (requests, httpx, urllib) su TheFork.it perché rilevano il TLS fingerprint Python.

### Soluzione (parziale)
```python
from curl_cffi import requests
r = requests.get(url, impersonate='safari17_2_ios')  # ← key: imita TLS Safari iOS
```

### Esito test TheFork
| impersonate | TheFork status | Note |
|---|---|---|
| `chrome124` | HTTP 403 | Datadome bloccato |
| `chrome120` | HTTP 403 | |
| `chrome110` | HTTP 403 | |
| `safari17_2_ios` | **HTTP 200, 880KB HTML** | ✅ |
| `edge99` | HTTP 403 | |

**Implicazione**: HTML completo accessibile per scraping metadata (JSON-LD address, geo, rating). Menu items NO (sono via JS lazy load Apollo GraphQL, niente nel SSR).

**Per Pietro S7**: questa tecnica è **riutilizzabile per discovery TheFork venues** Milano senza Wayback. Provider unlocked per metadata.

### File salvati per riferimento
- `thefork_camparino_in_galleria.html` (737KB)
- `thefork_camparino_in_galleria_menu.html` (737KB)
- `thefork_ceresio_7.html`, `thefork_bar_basso.html`

Conferma struttura Apollo state in `props.pageProps.initialApolloState` (520 keys, no menu items).

---

## ❌ STRADE CHIUSE (documentate per non ritentare)

### Quandoo.it
- HTTP 404 su `/it/risultati?destination=milano`
- Probabile cambio URL routing post-redesign
- **TODO futuro**: scoprire nuovi pattern URL via sitemap.xml

### Michelin Guide
- HTTP 404 su `guide.michelin.com/it/it/lombardia/milan/restaurants`
- Stessa diagnosi (URL changed)

### Glovo
- **Wayback**: pattern `glovoapp.com/it/it/milano-*` matcha solo zone (4 venues totali)
- **Live**: 200 OK ma SSR vuoto, prodotti via Vue XHR
- **Verdict**: solo Playwright può scrappare Glovo live

### Yelp.it
- 200 OK con JSON-LD strutturato MA solo metadata
- Pagina `/menu` non funziona (404)
- Niente prezzi nelle review

---

## 📊 NUMERI AGGREGATI

| Sorgente | Venues nuove | Prezzi nuovi |
|---|---|---|
| CKAN Comune Milano | **3.804** | 0 |
| eatbu (Pietro S5) | 11 | 0 |
| TheFork (metadata SSR) | 0 | 0 |
| Altri | 0 | 0 |
| **TOTALE** | **3.815** | **0** |

### Onestà sui prezzi nuovi
**Zero prezzi nuovi estratti.** Le fonti facilmente accessibili sono già state munte da Pietro/Peppe nei 5 sessioni precedenti. Le rimanenti (TheFork prezzi, Glovo live, JustEat) richiedono Playwright + IP residenziali — fuori scope notturno autonomo.

### Onestà sui venues
**3.815 venues nuove** sono un bacino enorme. Ma:
- **Quasi nessuno ha nome commerciale** (CKAN ha solo categoria licenza, non insegna). Serve OSM Overpass cross-ref (Pietro/Peppe stack).
- **Nessuno ha menu_url scrapabile** (sono in attesa di crowdsourcing o discovery sito proprio caso-per-caso).

---

## 💡 RACCOMANDAZIONI POST-NOTTE

### Per Pietro (prossima sessione)
1. **CKAN cross-ref OSM Overpass**: usa lo script Peppe `beach_s1_osm.py` come template per cross-ref bar Milano name → CKAN venue. Yield atteso: 1.000-1.500 nomi commerciali matched.

2. **TheFork metadata bulk**: `curl_cffi` con `safari17_2_ios` permette discovery massiva. Yield: 50-200 venues TheFork Milano con address+geo precisi (senza menu).

### Per Peppe (frontend)
1. **CKAN venues toggle**: aggiungi i 3.804 al layer "no-price" con marker visivo distinto da venues OSM nominate.
2. **NIL quartiere filter**: già 79 NIL diversi Milano coperti, ottimo filtro UX.

### Per CEO (strategico)
1. **Crowdsourcing infrastructure (Mossa 2 del piano)** diventa **CRITICA**: 3.804 venues no-price = 3.804 inviti a contribuire. Bridge necessario.
2. **Discovery Quandoo/Michelin** non scartata, solo richiede nuove tecniche (sitemap.xml, JSON-LD search).

---

## 📁 File prodotti

| File | Righe | Contenuto |
|---|---|---|
| `agent_ceo_ckan_venues_no_price.csv` | 3.804 | Venues drink Milano nuove (CKAN) |
| `agent_ceo_eatbu_venues.csv` | 11 | Metadata eatbu venues Pietro S5 discovered |
| `comune_in_piano.csv` | 9.417 | Raw CKAN dataset (per backup futuro) |
| `comune_fuori_piano.csv` | 3.717 | Raw CKAN fuori piano (per backup) |
| `glovo_milano_venues.txt` | 4 | Wayback Glovo URLs (no nuove) |
| `thefork_*.html` | 4 file | HTML cache TheFork SSR (reference Pietro) |

---

## Conclusione

**Ricerca bestiale completata.** 3.815 venues nuove sulla mappa Milano (passa da 1.601 a **~5.400 venues**, +238%). Prezzi nuovi: zero — barriere effettive su sources rimaste (Glovo/TheFork prezzi richiedono Playwright + residential IP).

Il vero ROI della notte è:
1. **Dataset CKAN Comune Milano** = il bacino autorevole "gold standard" venues Milano. Ora abbiamo riferimento ufficiale.
2. **Tecnica TLS impersonate** Safari iOS per TheFork metadata (bypass 403). Riusabile.

Buona notte. — CEO agent notturno
