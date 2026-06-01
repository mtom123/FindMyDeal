# SurPrice Beach — Data Access Guide (per agente frontend)

> Tutto quello che serve per accedere ai dati beach e costruire il frontend.
> Stato dataset: 2026-06-01 post Phase 3 (commit `ef0c593`).

---

## TL;DR

Il dataset beach è in 4 file CSV nel repo, tutti UTF-8 con header. Nessun database, nessun setup — `pandas.read_csv()` o `csv.DictReader` bastano.

| Fonte | Cosa contiene | Righe |
|---|---|---|
| `raw_sources/beach_s1_venues.csv` | Master OSM venue (anchor geografico) | 9.252 |
| `raw_sources/beach_s2x_spiagge_venues.csv` | Venue spiagge.it con amenities | 6.693 |
| `raw_sources/beach_s2x_spiagge_consolidated_venues.csv` | Venue spiagge.it + link al master | 6.693 |
| `raw_sources/beach_phase3_consolidated_items.csv` | Prezzi (UNICO file prezzi da usare) | 3.443 |

**Per il frontend serve sostanzialmente UN solo file prezzi e UNO o DUE venue file.** Tutto il resto è lavoro intermedio.

---

## Architettura dati

```
┌─────────────────────────────────────────────────────────────┐
│  VENUE LAYER (chi sono gli stabilimenti)                    │
│                                                             │
│  beach_s1_venues.csv (9.252)  ← OSM POI, geo anchor         │
│             │                                               │
│             │ match geo ≤300m + name sim                    │
│             ▼                                               │
│  beach_s2x_spiagge_venues.csv (6.693) ← amenities ricche    │
│             │                                               │
│             │ consolidamento                                │
│             ▼                                               │
│  beach_s2x_spiagge_consolidated_venues.csv (6.693)          │
│  └─ ha `master_source_venue_id` se match con OSM            │
└─────────────────────────────────────────────────────────────┘
                          │
                          │ linka via source_venue_id
                          ▼
┌─────────────────────────────────────────────────────────────┐
│  PRICE LAYER (cosa costa)                                   │
│                                                             │
│  beach_phase3_consolidated_items.csv (3.443)                │
│  └─ 1.731 venue unici con almeno 1 prezzo                   │
└─────────────────────────────────────────────────────────────┘
```

**Pattern di join**: `items.source_venue_id` ↔ `venues.source_venue_id`. Stesso campo in tutti i file.

---

## Schema dei file

### `beach_phase3_consolidated_items.csv` — PRICE TABLE (la più importante)

```
Campi chiave per UI:
  source_venue_id          venue_id da joinare ai venue
  venue_name               etichetta visibile
  venue_url                deep link sorgente (spiagge.it)
  normalized_price_eur     PREZZO in EUR (float)
  raw_price                stringa originale "€38,00" (fallback display)
  normalized_product       (vocabolario chiuso, vedi sotto)
  price_type               (vocabolario chiuso, vedi sotto)
  confidence               "high" | "medium" | "low"
  peak_or_mid              "peak_aug" | "mid_jun" | ""
  check_in_date            ISO date "2026-08-01"
  check_out_date           ISO date "2026-08-07"
  staging_items            "1U_2B" | "1B" | ecc. (config raw spiagge)
  available_spots          int (slot residui, utile per UX urgency)
  booking_provider         "spiagge.it" | "direct_website" | "bibionemare"
  source_url               URL per redirect booking esterno
  season                   sempre "summer_2026"
  validity_start/end       finestra validità prezzo
  vertical                 sempre "beach"
  _origin_file             file di provenienza (debug)
```

### `beach_s2x_spiagge_venues.csv` — VENUE TABLE (per la mappa)

```
Campi chiave per UI:
  source_venue_id          (formato "spiagge_NNNN")
  spiagge_venue_id         int numerico
  venue_name               nome
  venue_url                deep link spiagge.it
  address                  street
  city
  region                   regione italiana (15 costiere + 2 laghi)
  postal_code
  latitude  / longitude    float (per mappa)
  amenities                stringa "Bar; Doccia calda; WiFi; Cabine" separata da `;`
  description_excerpt      max 500 char editoriale
  image_url                CDN spiagge.it (HQ)
  rating  /  rating_count  (alcuni venue)
  booking_provider         sempre "spiagge.it"
  google_maps_url
```

### `beach_s1_venues.csv` — MASTER OSM (per copertura totale)

```
Stesso schema base S1 (vedi scripts/SCHEMA_AGENTI.md):
  source_venue_id          formato "osm_XXX"
  venue_name, latitude, longitude, region, city, ...
  website                  (568 popolati, gli altri vuoti)
  booking_provider         vuoto in S1, da popolare via diff S2X
```

Usalo se vuoi mostrare anche venue NON prezzati (per dataset completo).

### `beach_s2x_spiagge_consolidated_venues.csv` — JOIN HELPER

Stesso schema di `beach_s2x_spiagge_venues.csv` + tre colonne in più:
- `master_source_venue_id` ← link al master S1 se match
- `match_type` ∈ {`geo_300m`, `name_city`, `geo_only_name_diff`, `no_match`}
- `match_distance_m`, `match_name_ratio`

Usalo se vuoi dedup tra venue master e spiagge in un'unica vista.

---

## Vocabolari chiusi (vincolo di schema)

### `normalized_product` (16 codici)

Mappa user-facing per la UI:

```python
PRODUCT_LABELS = {
    "beach_set_2lettini_ombrellone": "Ombrellone + 2 lettini",
    "beach_set_1lettino_ombrellone": "Ombrellone + 1 lettino",
    "beach_umbrella_standard":       "Ombrellone",
    "beach_umbrella_first_row":      "Ombrellone prima fila",
    "beach_umbrella_premium":        "Ombrellone premium / tenda",
    "beach_sunbed":                  "Lettino singolo",
    "beach_chair":                   "Sedia / sdraio",
    "beach_cabin_day":               "Cabina giornaliera",
    "beach_cabin_season":            "Cabina stagionale",
    "beach_subscription_week":       "Abbonamento settimanale",
    "beach_subscription_month":      "Abbonamento mensile",
    "beach_subscription_season":     "Abbonamento stagionale",
    "beach_entry_fee":               "Ingresso",
    "beach_minimum_spend":           "Consumazione minima",
    "beach_parking":                 "Parcheggio",
    "beach_shower":                  "Doccia",
}
```

Distribuzione attuale items (top 5):
- `beach_set_2lettini_ombrellone` → 2.320 items (67%)
- `beach_sunbed` → 658 (19%)
- `beach_umbrella_standard` → 108 (3%)
- `beach_cabin_day` → 53 (2%)
- `beach_umbrella_first_row` → 35 (1%)

### `price_type` (8 codici)

```python
PRICE_TYPE_LABELS = {
    "per_day":          "al giorno",
    "per_day_weekday":  "al giorno (feriale)",
    "per_day_weekend":  "al giorno (weekend)",
    "per_half_day":     "pomeridiano",
    "per_week":         "settimanale",
    "per_month":        "mensile",
    "per_season":       "stagionale",
    "one_off":          "una tantum",
}
```

Distribuzione attuale:
- `per_week` → 3.199 items (93%) — Phase 3.1 ha estratto in slot settimanali
- `per_day` → 136 (4%)
- `per_season` → 40, `per_month` → 21, altro → 47

### `peak_or_mid` (3 valori)

- `peak_aug` → slot 1-7 agosto 2026 (alta stagione)
- `mid_jun` → slot 15-21 giugno 2026 (bassa stagione)
- `""` → items pre-Phase 3 (S1/S2/PDF), nessuna stagionalità dichiarata

Per ogni venue (idealmente) hai DUE items: uno per slot. Spread mediano peak/mid ≈ +19%.

---

## Loader Python (copy-paste)

```python
import csv
from collections import defaultdict

ITEMS_FILE = "raw_sources/beach_phase3_consolidated_items.csv"
VENUES_FILE = "raw_sources/beach_s2x_spiagge_venues.csv"

# Load venues (per mappa + detail)
venues = {}
with open(VENUES_FILE, encoding="utf-8") as f:
    for r in csv.DictReader(f):
        if r["extraction_status"] != "ok":
            continue
        venues[r["source_venue_id"]] = {
            "id": r["source_venue_id"],
            "name": r["venue_name"],
            "city": r["city"],
            "region": r["region"],
            "lat": float(r["latitude"]) if r["latitude"] else None,
            "lng": float(r["longitude"]) if r["longitude"] else None,
            "amenities": [a.strip() for a in r["amenities"].split(";") if a.strip()],
            "image": r["image_url"],
            "address": r["address"],
            "url": r["venue_url"],
            "booking_provider": r["booking_provider"],
        }

# Load items, group by venue_id
items_by_venue = defaultdict(list)
with open(ITEMS_FILE, encoding="utf-8") as f:
    for r in csv.DictReader(f):
        try:
            price = float(r["normalized_price_eur"])
        except (ValueError, KeyError):
            continue
        items_by_venue[r["source_venue_id"]].append({
            "price_eur": price,
            "raw_price": r["raw_price"],
            "product": r["normalized_product"],
            "price_type": r["price_type"],
            "peak_or_mid": r["peak_or_mid"],
            "check_in": r["check_in_date"],
            "check_out": r["check_out_date"],
            "confidence": r["confidence"],
            "staging": r["staging_items"],
            "spots": r["available_spots"],
            "booking_provider": r["booking_provider"],
            "source_url": r["source_url"],
        })

# Build venue list con prezzi attaccati
venues_with_prices = []
for vid, venue in venues.items():
    prices = items_by_venue.get(vid, [])
    if not prices:
        continue
    venue["prices"] = prices
    # Helper: median prezzo standard "Ombrellone+2 lettini" peak
    standard_peak = [p["price_eur"] for p in prices
                     if p["product"] == "beach_set_2lettini_ombrellone"
                     and p["peak_or_mid"] == "peak_aug"]
    venue["headline_price_peak"] = standard_peak[0] if standard_peak else None
    venues_with_prices.append(venue)

print(f"{len(venues_with_prices)} venue con prezzi pronti per UI")
```

Tempo di caricamento: ~0.5s su laptop. Memoria: ~40MB.

---

## Output JSON suggerito per il browser

Pre-genera un JSON aggregato statico al deploy (no DB richiesto):

```javascript
// beach_data.json (servito statico)
{
  "metadata": {
    "season": "summer_2026",
    "generated_at": "2026-06-01T22:00:00Z",
    "total_venues": 1731,
    "total_items": 3443,
    "regions": ["Emilia-Romagna", "Toscana", ...],
    "amenities_master_list": ["Bar", "Ristorante", "WiFi", ...]
  },
  "venues": [
    {
      "id": "spiagge_10389",
      "name": "Bagno Hawaii",
      "city": "Cesenatico",
      "region": "Emilia-Romagna",
      "geo": {"lat": 44.183176, "lng": 12.424084},
      "image": "https://img.spiagge.it/uploads/bagno-hawaii-...jpg",
      "amenities": ["Bar", "Ristorante", "WiFi", "Cabine", "Beach Volley"],
      "booking_url": "https://www.spiagge.it/stabilimenti-balneari/10389-bagno-hawaii/",
      "prices": {
        "peak_aug": {
          "product": "beach_set_2lettini_ombrellone",
          "price_eur": 111,
          "price_type": "per_week",
          "check_in": "2026-08-01",
          "check_out": "2026-08-07"
        },
        "mid_jun": {
          "product": "beach_set_2lettini_ombrellone",
          "price_eur": 97,
          "price_type": "per_week",
          "check_in": "2026-06-15",
          "check_out": "2026-06-21"
        }
      },
      "spread_peak_mid_pct": 14
    },
    ...
  ]
}
```

### Script di build (mettilo come `scripts/build_frontend_json.py`)

```python
import csv, json
from collections import defaultdict

OUT = "data/beach_data.json"

# ... [loader sopra] ...

# Cluster per regione per pre-aggregati
region_stats = defaultdict(lambda: {"venues": 0, "prices_peak": [], "prices_mid": []})
for v in venues_with_prices:
    region_stats[v["region"]]["venues"] += 1
    for p in v["prices"]:
        if p["product"] == "beach_set_2lettini_ombrellone":
            if p["peak_or_mid"] == "peak_aug":
                region_stats[v["region"]]["prices_peak"].append(p["price_eur"])
            elif p["peak_or_mid"] == "mid_jun":
                region_stats[v["region"]]["prices_mid"].append(p["price_eur"])

regions_aggregated = []
for region, stats in region_stats.items():
    p_peak = sorted(stats["prices_peak"])
    p_mid = sorted(stats["prices_mid"])
    regions_aggregated.append({
        "region": region,
        "venue_count": stats["venues"],
        "median_peak_eur": p_peak[len(p_peak)//2] if p_peak else None,
        "median_mid_eur": p_mid[len(p_mid)//2] if p_mid else None,
        "min_peak_eur": p_peak[0] if p_peak else None,
        "max_peak_eur": p_peak[-1] if p_peak else None,
    })

# Output finale
out = {
    "metadata": {
        "season": "summer_2026",
        "generated_at": "2026-06-01T22:00:00Z",
        "total_venues": len(venues_with_prices),
        "regions": regions_aggregated,
    },
    "venues": venues_with_prices,
}
with open(OUT, "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, indent=2)
print(f"Written {OUT}: {len(venues_with_prices)} venue")
```

Output size stimato: 1.731 venue × ~1KB = **~1.7MB JSON** (300KB gzipped). Servibile come asset statico Vercel/Cloudflare senza problemi.

---

## Query / filtri tipici per UI

### Per la **mappa cluster regionale**
```python
# Pre-aggregato in metadata.regions
# Mostra cerchio con count + median price per regione
```

### Per **detail venue**
```python
venue = venues_by_id["spiagge_10389"]
# Mostra: name, image, amenities (chips), peak/mid affiancati, booking CTA
```

### Per **filtro città**
```python
[v for v in venues_with_prices if v["city"].lower() == "rimini"]
# 117 venue Rimini, 65+ con prezzi
```

### Per **filtro amenity**
```python
[v for v in venues_with_prices if "Accesso animali" in v["amenities"]]
# 1.116 pet-friendly nel dataset complete (376 anche prezzati)
```

### Per **filtro range prezzo**
```python
target = 50  # €/week peak agosto
candidates = [v for v in venues_with_prices
              if v.get("headline_price_peak") and v["headline_price_peak"] <= target]
```

### Per **compare 2-3 venue**
Affianca i blocchi `venue.prices.peak_aug` e `venue.prices.mid_jun`. Mostra spread.

---

## Performance notes

- **Dataset size**: 1.731 venue prezzati × ~1KB JSON = manageable client-side
- **No DB**: caricamento intero file in memoria. React `useState` regge senza problemi.
- **Mappa**: 1.731 marker → cluster con `react-leaflet-markercluster` o `mapbox` clustering. Niente Web GL richiesto.
- **Search**: full-text su venue_name + city via Fuse.js (<10ms per query)
- **Filtri**: tutti client-side (no API). Per ogni filtro: `array.filter()` su 1.731 elementi = istantaneo.

---

## Update workflow (per refresh dataset)

Quando vuoi rinfrescare i dati (i prezzi cambiano in tempo reale su spiagge.it):

```bash
cd /Users/g_giaimo02/Desktop/TTW/FindMyDeal

# Phase 3.1 refresh (~10 min)
rm -rf raw_sources/.phase3_cache/
python3 scripts/beach_phase3_spiagge_extract.py 0 16 0.2

# Re-consolidate (~5s)
python3 scripts/beach_phase3_consolidate.py

# Re-build frontend JSON (~3s)
python3 scripts/build_frontend_json.py

# Deploy
git add raw_sources/beach_phase3_*.csv data/beach_data.json
git commit -m "data: weekly refresh prezzi spiagge.it"
git push origin main
```

**Cadenza suggerita**: refresh settimanale per peak season (giu-set), bisettimanale fuori.

---

## Insight strategici per il design UI

### Cosa funziona bene nel dataset

1. **Copertura regionale completa**: ogni regione costiera ha ≥30 venue prezzati. Mappa Italia funziona.
2. **Amenities normalizzate**: 15+ filtri possibili senza parsing fuzzy ("WiFi", "Cabine", "Accesso animali", "Disabili", etc.).
3. **Spread peak/mid**: dichiarato per 90% dei venue prezzati. Mostra "Risparmi €N in bassa stagione" naturale.
4. **`available_spots`**: numero variabile (10-300) → usabile per UX urgency ("Solo 12 posti rimasti!").

### Limiti onesti del dataset

1. **`price_type = "per_week"` per il 93% degli items**. Non puoi mostrare "€/giorno" affidabilmente per la maggior parte. Mostra "€/settimana" come default, "€/giorno" solo dove disponibile.
2. **Granularità per-fila assente**. Spiagge.it espone solo prezzo minimo per slot, non per riga ombrellone. UI deve essere onesta: "a partire da €N".
3. **Solo 1.731/13.646 venue (12.7%) hanno prezzi**. Per gli altri mostra "Prezzi non disponibili online" o lista solo i prezzati.
4. **Date fissate**: peak = 1-7 ago, mid = 15-21 giu. Non hai prezzi per altre date. Se UI ha date picker → deve disabilitare le date custom e mostrare solo i 2 slot validi.

### Suggerimento product

Dato il vincolo #4, fai una UI **slot-based** e non date-picker:
- Tab "Settimana peak (1-7 agosto)"
- Tab "Settimana mid (15-21 giugno)"
- Diff visivo "Risparmi €N andando in bassa stagione"

Più semplice da implementare, più chiaro per l'utente.

---

## File map completa (per riferimento)

```
FindMyDeal/
├── raw_sources/
│   ├── beach_s1_venues.csv                       9.252 venue OSM
│   ├── beach_s1_menu_items.csv                   214 items S1
│   ├── beach_s2_venues_enriched.csv              9.252 + geo arricchito S2
│   ├── beach_s2_direct_menu_items.csv            39 items S2 direct
│   ├── beach_s2_pdf_menu_items.csv               16 items S2 PDF
│   ├── beach_s2x_spiagge_url_list.csv            6.693 URL spiagge.it
│   ├── beach_s2x_spiagge_venues.csv              ⭐ 6.693 venue spiagge metadata
│   ├── beach_s2x_spiagge_consolidated_venues.csv 6.693 + match types
│   ├── beach_s2x_master_updates.csv              10.223 diff master S1
│   ├── beach_phase3_spiagge_menu_items.csv       3.174 items Phase 3.1
│   └── beach_phase3_consolidated_items.csv       ⭐ 3.443 items consolidati FINAL
│
├── scripts/
│   ├── SCHEMA_AGENTI.md                          schema CSV reference (legacy)
│   └── beach_phase3_*.py                         estrattori (riusabili)
│
└── DATA_ACCESS_BEACH.md                          questo file
```

**⭐ = i 2 file da usare per il frontend.**
