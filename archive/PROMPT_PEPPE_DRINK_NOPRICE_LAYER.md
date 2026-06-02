# Prompt Peppe — Drink No-Price Layer (03/06/2026)

> **OBIETTIVO**: aggiungere al vertical Drink il layer "venues senza prezzo" con toggle on/off, IDENTICO al pattern che hai già implementato per Balneari (commit `4463c2a` — `unpriced toggle`).
>
> **NON toccare nulla del vertical Balneari.** È perfetto così com'è.

---

## CONTESTO — Database aggiornato e pulito

Il CEO ha appena consolidato un nuovo file frontend-ready:

**File: `data/unified_venues_no_price.csv`**
- 3.712 venues drink Milano **senza prezzo**, geo-verificate, drink-target filtered
- 100% in bbox Milano (45.39-45.54, 9.04-9.28)
- 509 NO_TARGET già rimossi (ristoranti/pizzerie esclusi)
- Composizione: 2.867 CKAN Comune Milano + 738 unified_db Pietro TARGET + 97 Pietro S6 additions + 10 eatbu

### Schema CSV (13 colonne)
```csv
source,venue_name,address,city,latitude,longitude,venue_type,target_classification,phone,website,nil_quartiere,all_names,osm_amenity
```

| Campo | Esempio | Note |
|---|---|---|
| `source` | `ckan_milano`, `unified_db`, `pietro_s6`, `eatbu_metadata` | Provenance — usare per badge piccolo |
| `venue_name` | `A TAVOLA`, `Caffè Magenta`, `Spritz Navigli` | Nome commerciale (display principale) |
| `address` | `Largo Settimio Severo, 1, 20144 Milano, MI, Italia` | Address completo |
| `latitude` | `45.4660884` | Float — per Leaflet |
| `longitude` | `9.1624924` | Float — per Leaflet |
| `venue_type` | `cafe`, `bar`, `pub`, `cocktail_bar`, `craft_beer`, `bistro`, `wine_bar`, `rooftop`, `hotel_bar`, `unknown` | Per icona/colore marker |
| `target_classification` | `TARGET`, `AMBIGUOUS_TO_REVIEW`, vuoto | Vuoto = CKAN autoritative |
| `phone` | `+39 02 ...` | Opzionale, mostra in popup se presente |
| `website` | `https://...` | Opzionale, link in popup |
| `nil_quartiere` | `BRERA`, `DUOMO`, `BUENOS AIRES - PORTA VENEZIA - PORTA MONFORTE` | Quartiere Milano |
| `all_names` | `Caffè Fernanda \| Caffefernanda` | Varianti nome (debug only) |
| `osm_amenity` | `cafe`, `bar`, `restaurant` | Cross-ref OSM (debug only) |

### Distribuzione venue_type (per scegliere colori/icone)
- cafe: **2.427 (65%)** — colore prevalente
- bar: 636 (17%)
- pub: 300 (8%)
- cocktail_bar: 113 (3%)
- craft_beer: 50, bistro: 48
- wine_bar 9, rooftop 3, hotel_bar 2, unknown 116

---

## SETUP

```bash
cd ~/percorso/SurPrice
git pull origin main
```

Leggi (5 minuti):
- `AGENTS.md` (workflow generale)
- `AGENTS_STATE.md` (numeri attuali)
- `CHANGELOG.md` — vedi voce 03/06 per dettaglio merge 3.712 venues
- Il TUO codice esistente `index.html` (commit `4463c2a` per pattern unpriced beach)

---

## TASK SPECIFICHE

### TASK 1 — Caricamento dati

Aggiungi fetch del nuovo CSV nel boot del frontend, **solo quando il vertical è "Drink"**:

```javascript
// All'inizio quando carichi il drink vertical
const drinkNoPriceVenues = await fetch('./data/unified_venues_no_price.csv')
  .then(r => r.text())
  .then(parseCSV);  // riusa parser esistente
```

Mantieni il caricamento **lazy**: non scaricare 600KB al primo paint, solo al toggle ON.

### TASK 2 — Toggle button (replica balneari)

Riusa lo stesso componente `unpriced toggle` che hai già nella sidebar/header per i balneari. Stesso design, stesso comportamento (3-state hover/show/off — vedi commit `ddc2afc`).

**Posizione**: a fianco del filtro prodotti drink, NON nel tab balneari.

**Label suggerita**: "Mostra venues senza prezzo (3.712)" oppure "Tutti i bar Milano".

### TASK 3 — Marker design (CONSISTENT con balneari)

Hai già:
- Drink prezzati: **rectangular markers** con prezzo (commit `420d020`)
- Balneari: **circular markers** con droplet animation (commit `a1ebe2a`)
- Balneari no-price: **circular markers grigi** (commit `4463c2a`)

Per drink no-price → **rectangular markers GRIGI** (consistent con drink shape, niente prezzo).

**Color suggestion per venue_type:**
- `cocktail_bar`, `craft_beer`, `rooftop` → grigio scuro più saturato (premium)
- `cafe`, `bar`, `pub`, `bistro` → grigio medio
- `unknown` → grigio chiaro

Oppure tutti grigio neutro se preferisci semplicità.

### TASK 4 — Popup design

Quando l'utente clicca un pin no-price drink, mostra popup:

```
┌─────────────────────────────────────┐
│  🍸 [venue_name]                    │
│  [venue_type capitalized]           │
│                                     │
│  📍 [address abbreviato]            │
│  🏘️ [nil_quartiere]                 │  (se presente)
│                                     │
│  💰 Prezzo non disponibile          │
│  ┌─────────────────────────────┐   │
│  │  Contribuisci con un prezzo │   │  (CTA — futuro crowdsourcing)
│  └─────────────────────────────┘   │
│                                     │
│  [📞 phone] [🌐 website]            │  (solo se presenti)
└─────────────────────────────────────┘
```

**CTA "Contribuisci"**: per ora può essere un alert/modal placeholder ("Funzione in arrivo"). Il CEO predisporrà form crowdsourcing in S+1.

### TASK 5 — Performance

3.712 marker su Leaflet rallentano se renderizzati tutti insieme. **Riusa il pattern di clustering** che hai già implementato per balneari (commit `4463c2a` zoom clustering).

Soglia consigliata: cluster sotto zoom 14, individuali sopra.

### TASK 6 — Filtro venue_type (opzionale ma utile)

Aggiungi dropdown/chip per filtrare per venue_type:
- ☑ Tutti
- ☑ Cocktail bar
- ☑ Pub / Craft beer
- ☑ Caffè / Bar
- ☑ Wine bar / Bistrot
- ☑ Rooftop / Hotel bar

Nice-to-have. Skip se tempi stringono.

---

## QUALITY GATES (NON NEGOZIABILI)

1. ❌ **NON toccare nulla del vertical Balneari** (è perfetto, l'utente l'ha detto esplicitamente)
2. ❌ **NON modificare `prices_data.json`** o `data/beach_data.json` (territorio CEO)
3. ❌ **NON toccare `data/unified_*.csv`** (output merge_pipeline)
4. ✅ Il toggle drink-no-price deve essere INDIPENDENTE da quello beach-unpriced (due verticali separati)
5. ✅ Le 153 venues prezzate (mappa attuale) devono RESTARE visibili e identiche
6. ✅ Mobile responsive (commit `a1ebe2a` mobile polish — mantieni quel livello)
7. ✅ Performance: cluster sotto zoom 14, no lag su 3.712 marker

---

## COSA NON È IN SCOPE

- ❌ Crowdsourcing form vero (è S+1, lascia placeholder)
- ❌ Reverse geocoding aggiuntivo (CEO + Pietro hanno geocodato 99%)
- ❌ Aggiungere venues nuove (è scope Pietro)
- ❌ Modificare schema CSV (è territorio CEO)

---

## ESEMPIO USE-CASE END-TO-END

1. Utente apre il sito → vede 153 pin drink prezzati a Milano (UNCHANGED)
2. Utente clicca toggle "Mostra venues senza prezzo" → si caricano i 3.712 pin grigi
3. Utente naviga zoom-out → cluster grigi raggruppati
4. Utente zoom-in su NoLo → vede pin individuali, hover → popup con nome + addr + "Prezzo non disponibile"
5. Utente clicca "Contribuisci" → modal placeholder (per ora)
6. Utente toggle OFF → torna alla mappa solo 153 prezzati

---

## DELIVERABLE

```bash
git pull --rebase origin main
git add index.html [eventuali nuovi file css/js]
git commit -m "feat(drink): toggle no-price venues — 3.712 pin Milano"
git push origin main
```

Avvisa il CEO con screenshot della mappa con toggle ON.

---

## BUDGET TEMPO STIMATO

| Task | Tempo |
|---|---|
| Task 1+2 — Fetch + toggle | 30 min |
| Task 3 — Marker grigi rectangular | 30 min |
| Task 4 — Popup design | 45 min |
| Task 5 — Clustering | 20 min |
| Task 6 — Filtro venue_type (opt) | 30 min |
| Mobile polish + test | 30 min |
| **Totale** | **2.5–3 ore** |

---

## NOTE FINALI

- Il file `data/unified_venues_no_price.csv` è **frontend-ready**. Niente parsing complicato, niente edge case noti.
- Il merge_pipeline rigenera questo file ogni volta che il CEO esegue uno script `build_no_price_map.py`, quindi se Pietro porta nuove venues domani, basta refresh CSV.
- I 716 venues con `target_classification=AMBIGUOUS_TO_REVIEW` sono comunque drink-plausibili — non filtrare per default, semmai usali come "low confidence" badge se vuoi.
- I 2.811 CKAN sono autoritative — niente badge "ambiguous" su questi.

Buon lavoro Peppe. **L'obiettivo è 3.865 pin Milano drink (153 prezzati + 3.712 no-price) sulla mappa, con toggle e popup pronti per crowdsourcing.**
