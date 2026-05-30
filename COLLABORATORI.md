# Guida per i collaboratori — FoodPrice Data Pipeline

## Il progetto

**FoodPrice Milano** — mappa interattiva prezzi drink nei bar.
Sito live: https://mtom123.github.io/FindMyDeal/

Questo repo contiene sia il frontend che la pipeline dati.
Ogni collaboratore contribuisce con CSV di dati estratti dalle proprie fonti.

---

## Setup iniziale (una volta sola)

```bash
git clone https://github.com/mtom123/FindMyDeal.git
cd FindMyDeal
pip install requests beautifulsoup4 lxml tqdm
```

---

## Struttura del repo

```
FindMyDeal/
├── index.html              # sito live (GitHub Pages)
├── prices_data.json        # dati per il sito (NON modificare a mano)
│
├── raw_sources/            # << TU LAVORI QUI
│   ├── mycia_venues.csv       già presente (orchestratore)
│   ├── mycia_menu_items.csv   già presente (orchestratore)
│   ├── direct_venues.csv      già presente (orchestratore)
│   └── {tua_fonte}_venues.csv      ← il tuo output
│   └── {tua_fonte}_menu_items.csv  ← il tuo output
│
├── data/                   # output unificato (generato dall'orchestratore)
│   ├── unified_venues.csv
│   ├── unified_menu_items.csv
│   └── unified_prices.csv
│
└── scripts/                # strumenti pipeline
    ├── merge_pipeline.py   # orchestratore: unisce tutto
    ├── SCHEMA_AGENTI.md    # << LEGGI QUESTO PRIMA
    └── ...
```

---

## Il tuo workflow

### 1. Prima di iniziare — aggiorna dal repo
```bash
git pull origin main
```

### 2. Lavori sul tuo scraper in locale
Produci due file nel formato definito in `scripts/SCHEMA_AGENTI.md`:
- `raw_sources/{tua_fonte}_venues.csv`
- `raw_sources/{tua_fonte}_menu_items.csv`

Esempi nomi fonte: `thefork`, `glovo`, `justeat`, `leggimenu`, `iamenu`

### 3. Quando hai dati pronti — push
```bash
git add raw_sources/{tua_fonte}_venues.csv
git add raw_sources/{tua_fonte}_menu_items.csv
git commit -m "data: add {tua_fonte} Milano venues+menu"
git push origin main
```

### 4. Avvisa l'orchestratore
Manda messaggio con: fonte, numero venues, numero items con prezzo.
L'orchestratore fa girare `merge_pipeline.py` e aggiorna il sito.

---

## Formato CSV obbligatorio

Leggi `scripts/SCHEMA_AGENTI.md` — è la spec completa.

Campi minimi per `{fonte}_venues.csv`:
```
source_platform, source_venue_id, venue_name, venue_url,
address, city, latitude, longitude, has_menu, extraction_status, retrieved_at
```

Campi minimi per `{fonte}_menu_items.csv`:
```
source_platform, source_venue_id, venue_name, venue_url,
menu_section, item_name, raw_price, normalized_price_eur,
currency, price_type, item_type, confidence, retrieved_at, source_url
```

Valori `price_type`: `menu` (prezzo al banco) o `delivery` (prezzo delivery, maggiorato)

---

## Prodotti da normalizzare (`normalized_product`)

Usa ESATTAMENTE questi codici:

| Codice | Prodotto |
|--------|----------|
| `spritz` | Aperol/Campari Spritz |
| `negroni` | Negroni, Negroni Sbagliato |
| `americano` | Americano cocktail |
| `gin_tonic` | Gin Tonic |
| `mojito` | Mojito |
| `beer_draft_small` | Birra spina piccola (0.2-0.3L) |
| `beer_draft_medium` | Birra spina media (0.4-0.5L) |
| `beer_bottle` | Birra in bottiglia |
| `beer_moretti` | Birra Moretti (specifica) |
| `wine_glass` | Vino al calice |
| `espresso` | Caffè espresso |
| `custom_cocktail` | Cocktail con nome proprio |

Se non sei sicuro → lascia `normalized_product` vuoto.

---

## Note importanti

- **Wolt NON è in Italia** — non perdere tempo
- **Rate limiting**: minimo 1.5s tra request
- **Encoding**: UTF-8 per tutti i CSV
- **Prezzi**: usa il punto decimale (`7.50`, non `7,50`)
- **Cache**: salva le pagine scaricate in locale, non ri-scaricare

---

## Domande?

Apri una Issue su GitHub o contatta l'orchestratore.
