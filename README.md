# PriceLens — Milan Price Map

**Find My Deal** · Map-based price transparency for Milan nightlife.

🔗 **Live preview → [mtom123.github.io/FindMyDeal](https://mtom123.github.io/FindMyDeal/)**

---

## What it does

Search a drink (spritz, negroni, beer…) and see every bar in Milan where it's served, ranked from cheapest to most expensive. Prices shown directly on the map.

## Data

- **146 venues** with at least one price on the map
- **22 drink categories** — spritz, negroni, beer, cocktail, wine, caffè…
- **829 price points** geo-normalized
- **1.558 venues** total in the database
- Sources: mycia.it, leggimenu.it, menudigitale.io, eatbu.com, qodeup.com, direct websites, comune Milano open data
- Price range: **€1 – €25**

> ⚠ **Experimental data.** Prices sourced from public online menus, not live POS systems. Accuracy improves over time. Always confirm at the bar.

## For collaborators

This repo is collaborative. If you're a new agent / contributor, read **[AGENTS.md](AGENTS.md)** first — it explains roles, workflow, file structure and conventions.

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
