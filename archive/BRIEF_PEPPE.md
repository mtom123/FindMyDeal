# Brief per Peppe — aggiornamento al 01/06/2026

## Stato dati attuale

| Metrica | Valore |
|---|---|
| **Price points sulla mappa** | **829** |
| **Venues uniche sulla mappa** | **146** |
| **Venue-product pairs** | 547 |
| **Prodotti disponibili** | 22 |
| **Venues totali nel DB** | 1.558 |

Il file `prices_data.json` è già aggiornato e pushato. Le modifiche rilevanti vs. brief precedente:
- Rimossi 6 falsi positivi non-Milano (Pub51/PA, Coco Loco/LE, ecc.)
- 29 pin leggimenu spostati da Piazza Duomo alle coordinate reali
- Totale pin precisi: ~124 venues, ~22 ancora su fallback Milano centro (normale)

Pietro ha una sessione scraping in corso (S3) — probabilmente +500-2000 nuovi items. Aspetta il merge CEO prima di aggiornare cose che dipendono dalla quantità.

---

## Struttura prices_data.json (invariata)

```json
{
  "spritz": {
    "code": "spritz",
    "label": "Spritz",
    "count": 116,
    "venues": [
      {
        "venue_name": "Bar Magenta",
        "venue_url": "...",
        "address": "Via Carducci 13, Milano",
        "latitude": 45.4654,
        "longitude": 9.1859,
        "normalized_price_eur": 7.5,
        "raw_price": "7,50",
        "source_platform": "leggimenu",
        "item_name": "Spritz Aperol"
      }
    ]
  }
}
```

22 prodotti al primo livello. Ogni prodotto ha una lista `venues` con un prezzo-per-venue (il CEO deduplicato al minimo per venue). `count` = numero totale price points per quel prodotto.

---

## Prodotti e copertura (ordine volume)

| Prodotto | Price points | Range EUR | Mediana |
|---|---|---|---|
| Spritz | 116 | 0.75–20.00 | 8.00 |
| Negroni | 79 | 3.50–25.00 | 9.00 |
| Caffè | 72 | 1.00–36.00 | 2.00 |
| Birra Bottiglia | 69 | 3.00–25.00 | 6.40 |
| Americano | 64 | 1.00–18.00 | 8.00 |
| Bibita | 59 | 1.00–15.00 | 5.00 |
| Acqua | 55 | 0.50–5.00 | 2.00 |
| Gin Tonic | 46 | 5.00–18.00 | 10.00 |
| Mojito | 37 | 2.00–19.00 | 9.00 |
| Margarita | 32 | 6.00–90.00 | 10.00 |
| Cappuccino | 29 | 1.50–7.80 | 2.30 |
| Birra Spina Piccola | 22 | 3.50–7.40 | 5.00 |
| Moscow Mule | 22 | 5.00–18.00 | 8.50 |
| Vino al Calice | 22 | 3.50–9.00 | 7.00 |
| Peroni/Nastro Azzurro | 21 | 2.00–7.00 | 5.00 |
| Daiquiri | 20 | 6.00–19.00 | 10.00 |
| Birra Moretti | 17 | 1.50–8.00 | 4.00 |
| Prosecco Calice | 16 | 4.50–35.00 | 8.00 |
| Heineken | 11 | 2.00–6.00 | 4.00 |
| Birra Spina Media | 9 | 4.50–10.00 | 6.00 |
| Manhattan | 7 | 7.50–20.00 | 12.00 |
| Cocktail Custom | 4 | 6.00–14.00 | 12.00 |

---

## Cosa NON fare

- ❌ Non toccare `prices_data.json` — rigenerato automaticamente dal merge
- ❌ Non geocodare manualmente venues — lo fa il CEO
- ❌ Non aggiornare `data/unified_*.csv` — output del merge

## Domande / task frontend?

Apri Issue su GitHub oppure chiedi direttamente.

— CEO (01/06/2026)
