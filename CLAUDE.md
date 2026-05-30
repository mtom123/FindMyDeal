# FoodPrice — Website Agent Context

## Progetto

**FoodPrice** è un'app che mostra su mappa interattiva i prezzi di singoli drink
(spritz, negroni, birra, ecc.) nei bar di Milano. L'utente cerca "Spritz" e vede
tutti i bar con il prezzo ordinato dal più basso al più alto.

Siamo nella **fase demo / TTW**: dobbiamo validare il concept con dati reali già
raccolti. Niente backend, niente database — solo frontend statico con dati embedded.

---

## Stack

- **Vanilla HTML + CSS + JS** (no framework, no build step)
- **Leaflet.js** per la mappa
- **Font**: Inter (Google Fonts)
- Deploy target: **GitHub Pages** (file statici, niente server)

Se serve qualcosa di più strutturato, usa **Vite + vanilla JS** (niente React per ora).

---

## Dati disponibili

### `prices_data.json` — feed principale

Struttura:
```json
{
  "spritz": {
    "code": "spritz",
    "label": "Spritz",
    "count": 29,
    "venues": [
      {
        "venue_name": "BAR PICCHIO",
        "address": "Via ..., Milano",
        "lat": 45.47,
        "lng": 9.20,
        "price_tier": "€",
        "categories": "Bar, Pub",
        "min_price": 3.50,
        "items": [
          { "name": "Aperol Spritz", "section": "APERITIVI", "price": 3.50 }
        ]
      }
    ]
  },
  "negroni": { ... },
  ...
}
```

**14 prodotti disponibili**: spritz, negroni, americano, gin_tonic, mojito,
moscow_mule, margarita, daiquiri, custom_cocktail, beer_draft, beer_bottle,
wine_glass, espresso, water

**79 venues** totali su Milano, tutte con lat/lng verificato.

### `prices_by_product.csv` — versione tabellare (backup)

Colonne: `normalized_product, product_label, item_name, menu_section, price_eur,
venue_name, address, city, latitude, longitude, price_tier, categories, source_url`

### `demo_map_reference.html` — prototipo funzionante

Mappa Leaflet già funzionante con tutti i dati. Usa come **riferimento tecnico**
per capire come è strutturato il codice Leaflet, non come design finale.

---

## Principi

- **Semplicità prima di tutto** — se funziona con 3 file HTML/CSS/JS, non aggiungere complessità
- **Mobile-first** — la maggior parte degli utenti la usa da telefono per bar
- **Dati reali zero invenzioni** — usa solo dati in `prices_data.json`
- **Deployabile subito** — deve aprirsi con `open index.html` senza server

---

## Feature MVP (in ordine di priorità)

1. **Mappa Milano** con pin per ogni bar
2. **Filtro prodotto** (spritz, negroni, birra…) — aggiorna i pin in real-time
3. **Marker con prezzo** — mostra il prezzo minimo sul pin
4. **Popup / card** al click sul pin con: nome bar, indirizzo, lista prodotti+prezzi
5. **Classifica prezzi** — lista laterale con i bar ordinati per prezzo crescente
6. **Colore marker** per fascia di prezzo (verde/arancio/rosso)

---

## File nella cartella

```
website/
├── CLAUDE.md                  ← questo file
├── prices_data.json           ← dati principali
├── prices_by_product.csv      ← dati CSV (backup)
└── demo_map_reference.html    ← prototipo tecnico di riferimento
```

Tutto il codice nuovo va creato qui dentro.
