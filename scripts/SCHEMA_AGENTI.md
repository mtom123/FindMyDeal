# Schema Unificato — Output di tutti gli agenti scraper

> **OBBLIGATORIO**: ogni agente deve produrre CSV in questo formato esatto.
> Il merge pipeline lo leggerà automaticamente. Campo sbagliato = riga scartata.

---

## File da consegnare

Ogni agente produce **due file** nella cartella `raw_sources/`:

```
raw_sources/
├── <fonte>_venues.csv       # una riga per venue
└── <fonte>_menu_items.csv   # una riga per item di menu
```

Esempi: `thefork_venues.csv`, `glovo_menu_items.csv`, `leggimenu_venues.csv`

---

## Schema 1: `<fonte>_venues.csv`

| Campo | Tipo | Obbligatorio | Esempio |
|-------|------|:---:|---------|
| `source_platform` | string | ✅ | `thefork` / `glovo` / `mycia` / `leggimenu` |
| `source_venue_id` | string | ✅ | ID interno della piattaforma (se esiste) |
| `venue_name` | string | ✅ | `Bar Magenta` |
| `venue_url` | string | ✅ | URL della pagina venue sulla piattaforma |
| `address` | string | ✅ | `Via Carducci 13, Milano` |
| `city` | string | ✅ | `Milano` |
| `latitude` | float | se disponibile | `45.4654` |
| `longitude` | float | se disponibile | `9.1859` |
| `categories` | string | se disponibile | `Bar; Pub; Cocktail Bar` (separato da `;`) |
| `price_tier` | string | se disponibile | `€` / `€€` / `€€€` |
| `rating` | float | se disponibile | `4.2` |
| `rating_count` | int | se disponibile | `312` |
| `phone` | string | se disponibile | `+39 02 1234567` |
| `website` | string | se disponibile | URL sito proprio del locale |
| `opening_hours` | string | se disponibile | `Lun-Ven 18:00-02:00` |
| `has_menu` | bool | ✅ | `True` / `False` |
| `menu_url` | string | se disponibile | URL diretto del menu |
| `extraction_status` | string | ✅ | `ok` / `no_menu` / `error` / `filtered_out` |
| `retrieved_at` | ISO datetime | ✅ | `2026-05-30T21:00:00Z` |

---

## Schema 2: `<fonte>_menu_items.csv`

| Campo | Tipo | Obbligatorio | Esempio |
|-------|------|:---:|---------|
| `source_platform` | string | ✅ | `thefork` |
| `source_venue_id` | string | ✅ | stesso ID di venues.csv |
| `venue_name` | string | ✅ | `Bar Magenta` |
| `venue_url` | string | ✅ | URL pagina venue |
| `menu_section` | string | ✅ | `COCKTAIL` / `BIRRE ALLA SPINA` / `VINI` |
| `item_name` | string | ✅ | `Aperol Spritz` |
| `item_description` | string | se disponibile | `Prosecco, Aperol, Seltz` |
| `raw_price` | string | ✅ | `7,50` / `7.50` / `€ 7,50` (come appare sul sito) |
| `normalized_price_eur` | float | ✅ | `7.5` (già convertito, 0 se non disponibile) |
| `currency` | string | ✅ | `EUR` |
| `price_type` | string | ✅ | `menu` / `delivery` / `estimated` |
| `item_type` | string | ✅ | `drink` / `food` / `unknown` |
| `normalized_product` | string | se possibile | vedi tabella sotto |
| `confidence` | string | ✅ | `high` / `medium` / `low` |
| `allergens` | string | se disponibile | `glutine, latte` |
| `retrieved_at` | ISO datetime | ✅ | `2026-05-30T21:00:00Z` |
| `source_url` | string | ✅ | URL esatto da cui è stato estratto il dato |

---

## Valori validi per `normalized_product`

Usa ESATTAMENTE questi codici (lowercase, underscore):

| Codice | Cosa include |
|--------|--------------|
| `spritz` | Aperol Spritz, Campari Spritz, Hugo Spritz |
| `negroni` | Negroni, Negroni Sbagliato, White Negroni |
| `americano` | Americano cocktail |
| `gin_tonic` | Gin Tonic, G&T |
| `mojito` | Mojito |
| `moscow_mule` | Moscow Mule |
| `margarita` | Margarita |
| `daiquiri` | Daiquiri |
| `manhattan` | Manhattan |
| `beer_draft_small` | Birra spina 0.2L / 0.3L / 33cl piccola |
| `beer_draft_medium` | Birra spina 0.4L / 0.5L / media |
| `beer_bottle` | Birra in bottiglia (qualsiasi) |
| `beer_moretti` | **Birra Moretti specificamente** (33cl o 66cl) |
| `beer_heineken` | Heineken bottiglia/spina |
| `beer_peroni` | Peroni/Nastro Azzurro |
| `wine_glass` | Vino al calice / calice di vino |
| `prosecco_glass` | Flute di prosecco |
| `espresso` | Caffè espresso |
| `cappuccino` | Cappuccino |
| `soft_drink` | Coca Cola, Fanta, bibita in lattina/bottiglia |
| `water` | Acqua naturale o frizzante |
| `custom_cocktail` | Cocktail con nome proprio non standard |

Se non sei sicuro → lascia il campo vuoto (non inventare).

---

## Valori validi per `source_platform`

```
mycia | thefork | eatbu | leggimenu | wolt | justeat | glovo | deliveroo
iamenu | gromo | one2menu | menutiger | ordable | buonmenu | dishcovery
menudigitale | direct_website | other
```

---

## Valori validi per `price_type`

| Valore | Quando usarlo |
|--------|--------------|
| `menu` | Prezzo da menu fisico/digitale del locale (prezzo al banco) |
| `delivery` | Prezzo da app delivery (Glovo, Wolt, JustEat) — può essere maggiorato |
| `estimated` | Prezzo stimato / non ufficiale |

> ⚠️ **IMPORTANTE**: non mischiare prezzi delivery con prezzi menu nella stessa analisi.
> Il merge pipeline li terrà separati.

---

## Note per gli agenti

1. **Encoding**: UTF-8 obbligatorio
2. **Separatore**: virgola (,) — usa quoting per campi che contengono virgole
3. **Date**: ISO 8601 `2026-05-30T21:00:00Z`
4. **Prezzi**: punto decimale (7.50 non 7,50) in `normalized_price_eur`
5. **Bool**: `True`/`False` (Python style) oppure `1`/`0`
6. **Campi mancanti**: stringa vuota `""`, non `NULL`/`None`/`N/A`
7. **Deduplicazione interna**: ogni agente deduplica per `source_venue_id + item_name + raw_price` prima di consegnare
8. **Rate limiting**: minimo 1s tra request, stop se HTTP 429

---

## Dove consegnare

Creare cartella `raw_sources/` dentro `FindMyDeal/` e mettere i file lì:

```
FindMyDeal/
├── raw_sources/
│   ├── mycia_venues.csv          ← già esistente (vedi mycia_milano_venues.csv)
│   ├── mycia_menu_items.csv      ← già esistente (vedi mycia_milano_menu_items.csv)
│   ├── thefork_venues.csv
│   ├── thefork_menu_items.csv
│   ├── glovo_venues.csv
│   ├── glovo_menu_items.csv
│   └── ...
└── merge_pipeline.py             ← orchestratore unifica tutto
```
