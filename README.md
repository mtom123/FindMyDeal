# PriceLens — Milan Price Map

**Find My Deal** · Map-based price transparency for Milan nightlife.

🔗 **Live preview → [mtom123.github.io/FindMyDeal](https://mtom123.github.io/FindMyDeal/)**

---

## What it does

Search a drink (spritz, negroni, beer…) and see every bar in Milan where it's served, ranked from cheapest to most expensive. Prices shown directly on the map.

## Data

- **79 venues** across Milan, all with verified coordinates
- **14 drink categories** — spritz, negroni, cocktail, wine, caffè…
- **412+ price points** scraped from online menus (mycia.it)
- Price range: **€1 – €28**

> ⚠ **Experimental data.** Prices sourced from online menus, not live POS systems. Accuracy improves over time. Always confirm at the bar.

## Stack

| Layer | Tech |
|---|---|
| Frontend | Vanilla HTML + CSS + JS (no framework, no build step) |
| Map | Leaflet.js + CartoDB Dark tiles |
| Data | `prices_data.json` — static JSON |
| Fonts | Space Grotesk · IBM Plex Sans · IBM Plex Mono |
| Deploy | GitHub Pages |

## Roadmap

- **Phase 1** ← *we are here* — Static data, map prototype, concept validation
- **Phase 2** — Supabase + Postgres, user price submissions, confidence scoring
- **Phase 3** — Menu photo uploads, community verification, admin review

## Run locally

```bash
npx serve .
# open http://localhost:3000
```

> `prices_data.json` must be in the same folder. Requires a local server (fetch API doesn't work on `file://`).
