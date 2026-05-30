# Prompt per agenti scraper — da incollare in ogni nuova session

## Contesto

Stai lavorando al progetto **FoodPrice Milano** — raccolta prezzi drink nei bar
di Milano per una mappa interattiva. Sei uno degli agenti di scraping.

L'orchestratore raccoglierà i tuoi output e li unirà con quelli degli altri agenti
tramite `merge_pipeline.py`.

## Il tuo compito

Scraper le seguenti fonti: **[SOSTITUIRE CON LE FONTI ASSEGNATE]**

Città target: **Milano**

Prodotti da cercare (priorità alta):
- Spritz (Aperol Spritz, Campari Spritz)
- Negroni
- Birra alla spina (piccola/media)
- Birra Moretti
- Gin Tonic
- Mojito, Margarita, Daiquiri
- Vino al calice
- Birra Heineken, Peroni

## Formato output OBBLIGATORIO

Leggi `SCHEMA_AGENTI.md` nella cartella principale per il formato esatto.

Produci due file per ogni fonte:
- `raw_sources/<fonte>_venues.csv`
- `raw_sources/<fonte>_menu_items.csv`

Esempio: se scrapi TheFork → `raw_sources/thefork_venues.csv` + `raw_sources/thefork_menu_items.csv`

## Regole tecniche

- Rispetta robots.txt
- Rate limit: minimo 1.5s tra request
- Stop se ricevi HTTP 429 o blocchi
- Caching su disco (non ri-scaricare)
- Encoding: UTF-8
- Prezzi: usa il punto decimale (7.50), non la virgola
- `price_type`: usa `delivery` per Glovo/Wolt/JustEat, `menu` per tutti gli altri
- Deduplicazione interna prima di consegnare

## Come consegnare

Metti i file in `C:\Users\motti\Desktop\FindMyDeal\raw_sources\`
Poi avvisa l'orchestratore che puoi fare `python merge_pipeline.py`
