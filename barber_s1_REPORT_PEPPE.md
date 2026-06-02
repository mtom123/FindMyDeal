# Brief Peppe — Frontend Barber (02/06/2026)

> **Replica la struttura del vertical BEACH come riferimento.**
> Stessa UX, stessa logica sidebar, stesso pattern di interaction.
> Cambia: marker (hexagon viola), filtri (gender + servizio), categorie servizi.

---

## TL;DR per partire subito

1. Feed dati: **`data/barber_data.json`** (16 MB, già generato dal merge CEO)
2. Marker: **esagono viola** (clip-path CSS), brand color `#3d2b8a`
3. Filtri sidebar in **due livelli**:
   - **Primo livello**: gender (Uomo / Donna / Bambino)
   - **Secondo livello**: categoria servizio (Taglio / Barba / Colore / Piega / Trattamento / Altro)
4. **Regola d'oro**: la mappa mostra SEMPRE prezzi della stessa categoria selezionata.
   Mai mescolare prezzi di servizi diversi sullo stesso pin.
5. Statistiche sidebar: replica BEACH (regioni con mediana, top città, distribuzione prezzi)

---

## Schema `barber_data.json` (già generato)

```json
{
  "metadata": {
    "generated_at": "2026-06-02",
    "total_venues": 12019,
    "total_priced": 10709,
    "sources": ["treatwell", "fresha"],
    "regions": [
      {
        "name": "Lombardia",
        "total": 850,
        "priced": 720,
        "pct": 85,
        "median_prices": {
          "haircut_man": 18.0,
          "haircut_woman": 28.0,
          "hair_color": 50.0,
          "...": "..."
        }
      },
      ...
    ],
    "top_cities": [
      {"name": "Roma", "total": 1007, "priced": 848},
      {"name": "Milano", "total": 660, "priced": 563},
      ...
    ],
    "categories": [
      {
        "code": "haircut_man",
        "label": "Taglio Uomo",
        "gender": ["man"],
        "category": "taglio",
        "count_venues": 7936,
        "median": 15.0,
        "min": 5.0,
        "max": 250.0
      },
      ...
    ],
    "gender_filters": ["man", "woman", "child"],
    "service_categories": ["taglio", "barba", "colore", "piega", "trattamento", "altro"]
  },
  "venues": [
    {
      "id": "elixhair-cagliari-via-pasquale-tola-5-uwbr9p4a",
      "name": "Elixhair",
      "lat": 39.21984,
      "lng": 9.12419,
      "city": "Cagliari",
      "region": "Sardegna",
      "address": "Via Pasquale Tola 5",
      "url": "https://www.fresha.com/a/elixhair-cagliari...",
      "rating": "5",
      "rating_count": "47",
      "barber_category": "unisex",
      "genders": ["man", "woman"],
      "source_platforms": "fresha",
      "has_price": true,
      "min_price": 8.0,
      "n_priced_items": 12,
      "prices": {
        "haircut_man": {
          "min":   20.0,
          "label": "Taglio Uomo",
          "gender": ["man"],
          "category": "taglio",
          "items": [
            {"name": "Taglio uomo", "price": 20.0, "source": "fresha"}
          ]
        },
        "haircut_woman": {
          "min":   30.0,
          "label": "Taglio Donna",
          "gender": ["woman"],
          "category": "taglio",
          "items": [...]
        },
        "hair_color": {...}
      }
    },
    ...
  ]
}
```

---

## Marker design — ESAGONO VIOLA

Replica il pattern dei rettangolari (drink) e cerchi (beach), ma forma esagonale per distinguersi.

```css
/* Marker barber — hexagonal */
.pm.pm-barber {
  width: 56px;
  height: 46px;
  clip-path: polygon(25% 0%, 75% 0%, 100% 50%, 75% 100%, 25% 100%, 0% 50%);
  background: #3d2b8a;  /* viola brand barber */
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  font-family: 'IBM Plex Mono', monospace;
  font-size: 11px;
  font-weight: 600;
  cursor: pointer;
  transition: transform 0.15s ease;
  border: 0;
}
.pm.pm-barber:hover { transform: scale(1.13); z-index: 100; }
.pm.pm-barber.sel   { transform: scale(1.22); z-index: 200; }

/* Pricing tiers (same logic as beach) */
.pm.pm-barber.deal { background: #1e6639; }  /* verde — sotto mediana */
.pm.pm-barber.avg  { background: #7a5a00; }  /* ocra — vicino mediana */
.pm.pm-barber.exp  { background: #8b1a1a; }  /* rosso — sopra mediana */

/* No-price marker (grey, no label) */
.pm.pm-barber.no-price {
  background: rgba(0,0,0,0.20);
  border: 1px solid rgba(0,0,0,0.30);
}
```

**Label nel marker**: `€XX` formato compatto (es. "€18", "€140").
Per categorie con prezzi alti (extensions €1000+), abbreviare (es. "€1.1k").

**Cluster styling**: come beach, usa `MarkerCluster` con classe custom `bcluster-barber`.

---

## Sidebar — replica BEACH

Tre sezioni accordion (stesso ordine):

### 1. Filtri (top)

**1.a — Gender chip selector** (single-select, default = nessuna selezione → mostra tutti)

```
[ Uomo ] [ Donna ] [ Bambino ]
```

Quando seleziono "Uomo": filtro venues a `genders` contains "man" → ricalcolo
le statistiche regioni/città su quel subset.

**1.b — Categoria servizio dropdown** (single-select)

Mostra solo le categorie disponibili **dato il gender selezionato**.

Esempio selezione "Donna":
```
▾ Categoria servizio
  Taglio Donna (3.055 saloni — mediana €25)
  Piega (3.970 saloni — €18)
  Colore Capelli (3.587 saloni — €44)
  Mèches / Colpi di Sole (2.230 saloni — €70)
  Stiratura (1.512 saloni — €140)
  Acconciatura (1.746 saloni — €50)
  Trattamento (6.692 saloni — €35)
  ...
```

Esempio selezione "Uomo":
```
▾ Categoria servizio
  Taglio Uomo (7.936 saloni — €15)
  Rifilatura Barba (1.805 saloni — €12)
  Rasatura (805 — €18)
  Pacchetto Taglio+Barba (~600 — €25)
  Colore Capelli (1.200 — €35)
  Trattamento (~2.500 — €30)
```

**Stato default (nessun gender + nessun servizio selezionato)**:
mostra TUTTI i venue come pin "no-price" + chip "Seleziona genere e servizio per vedere prezzi".

### 2. Toggle layer (beach replica)

```
[ Mostra solo prezzati ] (default ON)
[ Mostra regioni ] (toggle bordi regioni)
```

### 3. Statistiche regionali (replica BEACH)

Stessa struttura `beach-reg-list` ma per i barbers. Ogni regione mostra:
- nome regione
- N venue totali / N prezzate
- mediana prezzo **della categoria selezionata** (cambia dinamicamente!)
- click → zoom su regione

Esempio quando filtro "Donna + Colore Capelli":
```
Lombardia    850 / 720 prezzate    €50 mediana colore
Lazio        780 / 650             €52
Campania     420 / 380             €40
...
```

Se nessun servizio selezionato: mostra `min_price` overall per venue.

### 4. Top città chip (sotto le regioni)

```
Roma 1007  ·  Milano 660  ·  Torino 195  ·  Napoli 132  ·  Bologna 70 ...
```

Click su città → zoom su quella città.

---

## LOGICA DI FILTRAGGIO — il punto cruciale

La regola assoluta:
**la mappa mostra prezzi della stessa categoria selezionata. Mai mescolare.**

### Stato iniziale
- Nessun filtro → tutti i pin grigi "no-price"
- Sidebar: chip "Seleziona genere e servizio per vedere prezzi reali"

### Solo gender selezionato (es. "Uomo")
- Pin colorati: solo venue con `genders.includes("man")` AND `has_price === true`
- Marker label: `min_price` overall del venue (compromesso tra "vedere subito qualcosa" e accuracy)
- Stats sidebar: mediana per ogni categoria uomo nella regione

### Gender + servizio selezionato (es. "Donna" + "Colore Capelli")
- Pin colorati: SOLO venue con `prices.hair_color` esistente AND nel gender "woman"
- Marker label: `prices.hair_color.min` (es. €45)
- Color tier: confronto vs mediana regione di hair_color
- Stats sidebar: mediana hair_color per regione
- Popup venue al click: mostra TUTTI i servizi disponibili, ma evidenzia hair_color in alto

### Popup venue (al click su pin)

```
┌────────────────────────────────┐
│ ELIXHAIR                       │
│ Via Pasquale Tola 5, Cagliari  │
│ ★ 5.0 (47 reviews) — Fresha    │
├────────────────────────────────┤
│ 💰 COLORE CAPELLI (selezionato)│
│   da €45                       │
│                                │
│ Altri servizi:                 │
│   Taglio Donna       da €30   │
│   Piega              da €25   │
│   Mèches             da €60   │
│   Trattamento        da €35   │
│                                │
│   [ Prenota su Fresha ↗ ]      │
└────────────────────────────────┘
```

---

## Mapping campi feed → UI

| UI element | Campo `barber_data.json` |
|---|---|
| Marker position | `lat`, `lng` |
| Marker label (no filtro) | `min_price` |
| Marker label (filtro servizio) | `prices[code].min` |
| Marker color tier | confronto vs `metadata.regions[r].median_prices[code]` |
| Popup name | `name` |
| Popup address | `address`, `city` |
| Popup rating | `rating` ★ `rating_count` |
| Popup source link | `url`, `source_platforms` |
| Popup gender badges | `genders` (es. "Uomo · Donna") |
| Sidebar filter availability | `metadata.categories` |
| Sidebar region stats | `metadata.regions[].median_prices[selectedCode]` |
| Sidebar city chips | `metadata.top_cities` |

---

## Color tiering (per il marker)

Replica esattamente la logica beach:

```js
function priceTier(venuePrice, regionMedian) {
  if (venuePrice <= regionMedian * 0.85) return 'deal';  // verde
  if (venuePrice <= regionMedian * 1.15) return 'avg';   // ocra
  return 'exp';                                          // rosso
}
```

Se non c'è mediana regionale per quella categoria (rare), usa mediana nazionale
da `metadata.categories[code].median`.

---

## Performance — splitting suggerito

`barber_data.json` è **16 MB** unico. Per mobile è pesante.

Soluzione 1 (semplice): zip + lazy load
- Serve il JSON con gzip → ~3 MB on the wire
- Mantieni single file, leggi al boot, carica markers progressivamente per regione visibile

Soluzione 2 (più lavoro): split per regione
- 21 file `barber_data_lombardia.json`, etc.
- Lazy fetch quando si seleziona/zoom su regione

Consiglio: **partire con Soluzione 1** (zip). Misurare load time mobile. Switch a 2 solo se necessario.

---

## Differenze rispetto a BEACH (importanti!)

1. **Beach**: 1 venue → tanti prezzi per stesso prodotto (per_day, per_week, prima fila, etc.) → mostra "min".
   **Barber**: 1 venue → tanti prezzi per prodotti diversi (taglio, barba, colore...) → mostra "min del servizio selezionato".

2. **Beach**: filtro stagione (peak/mid) sopra a tutto.
   **Barber**: filtro gender + servizio (no stagionalità, prezzi più stabili).

3. **Beach**: amenities chip (Bar, Cabine, WiFi...).
   **Barber**: gender badges + source badges (Treatwell/Fresha).

4. **Beach**: il marker mostra il prezzo "principale" (set 2 lettini + ombrellone).
   **Barber**: il marker mostra il prezzo del servizio selezionato (o min overall se nessuno).

5. **Beach**: regions con stats di staging items.
   **Barber**: regions con stats per ogni categoria servizio.

---

## Checklist implementazione

- [ ] Caricare `barber_data.json` al boot (gzip + cache localStorage 24h)
- [ ] Layer toggle "Barbieri" nel sidebar generale (se multi-vertical)
- [ ] Marker esagonale viola (`.pm-barber`) + cluster custom
- [ ] Sidebar: chip selector gender (3 chip)
- [ ] Sidebar: dropdown categoria servizio (filtrato per gender)
- [ ] Sidebar: regions list con mediana dinamica per servizio selezionato
- [ ] Sidebar: top cities chips
- [ ] Logica color tier (deal/avg/exp) basata su regione
- [ ] Popup venue con servizio selezionato evidenziato
- [ ] Mobile responsive (16 MB JSON → gzip + lazy)
- [ ] Testing su 3 città reali (Roma, Milano, Cagliari)

---

## Domande / decisioni che richiedono il tuo input

1. **Bambino come gender separato o sub-filtro di Uomo/Donna?**
   Suggerisco: chip separato (più chiaro UX per ricerca "taglio bimbo a Roma").

2. **Quando nessun filtro è attivo, mostro pin grigi o niente?**
   Suggerisco: pin grigi così la mappa non è vuota, ma chip CTA "Seleziona genere e servizio".

3. **Sorting venue nel popup-list (quando ci sono cluster)?**
   Suggerisco: per `min_price` ascendente.

4. **Multi-vertical switcher**: drink / beach / barbieri in alto della pagina?
   Da definire se mantenere mappa unica multi-layer o tre URL separati.

---

## Sample mockup mentale

```
╔════════════════════════════════════════════════════╗
║ FindMyDeal · Barbieri                              ║
╠══════════════════╦═════════════════════════════════╣
║ 🔍 Roma          ║                                 ║
║                  ║                                 ║
║ ═══ FILTRI ═══   ║                                 ║
║                  ║      [🗺️ MAPPA LEAFLET]         ║
║ [Uomo][Donna]    ║                                 ║
║ [Bambino]        ║      hexagonal markers          ║
║                  ║      verde/ocra/rosso           ║
║ ▾ Servizio       ║      cluster bcluster-barber    ║
║   Taglio Uomo    ║                                 ║
║   €15 mediana    ║                                 ║
║                  ║                                 ║
║ ═══ REGIONI ═══  ║                                 ║
║ Lombardia 850    ║                                 ║
║   €18 mediana    ║                                 ║
║ Lazio 780        ║                                 ║
║   €15 mediana    ║                                 ║
║ ...              ║                                 ║
║                  ║                                 ║
║ Top: Roma 1007   ║                                 ║
║      Milano 660  ║                                 ║
║                  ║                                 ║
╚══════════════════╩═════════════════════════════════╝
```

Buon lavoro Peppe. Stessa qualità UX di beach, struttura cognitiva chiara,
prezzi sempre **omogenei** sulla mappa.
