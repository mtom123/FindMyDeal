# raw_sources/ — Drop zone scraper

> Ogni agente deposita qui i suoi CSV. Il CEO fa il merge unificato in `data/`.

---

## Naming convention

```
{fonte}_venues.csv         ← venues
{fonte}_menu_items.csv     ← items prezzi

Esempi:
  thefork_venues.csv
  thefork_menu_items.csv
  agent2_eatbu_venues.csv     ← re-scraping dello stesso agente, prefisso agentN_
```

**Non creare cartelle per collaboratore.** Il prefisso del file basta a tracciare autore/sessione.

---

## File correnti (31/05/2026)

| File | Autore | Sessione | Status | Note |
|---|---|---|---|---|
| `mycia_*.csv` | CEO (mycia_scraper.py) | 2026-05-30 | ✅ completo | Sitemap esaustivo. 648 venues, 1.102 items. Non rifare. |
| `leggimenu_*.csv` | Pietro | 2026-05-31 mattina | ✅ completo | 41 venues, 4.832 items. 39 da geocodare con precisione |
| `menudigitale_*.csv` | Pietro | 2026-05-31 mattina | ✅ Milano filtrato | 111 venues raw → 2 Milano confermate (242 items) |
| `qromo_*.csv` | Pietro | 2026-05-31 mattina | ⛔ legale | robots.txt vieta `/API`. Solo venues, no items |
| `direct_*.csv` | CEO (osm_direct_scraper.py) | 2026-05-30 | ✅ completo | 194 venues OSM bar Milano con website |
| `pdf_*.csv` | Pietro | 2026-05-31 mattina | ✅ completo | 4 PDF da dish.co (Deseo, Abbracci, Casa Giuditta, Funky) |
| `scraper_*.csv` | Pietro | 2026-05-31 mattina | ✅ parziale | 850 venues, 36 items (poi superato da agent2_) |
| `agent2_direct_website_*.csv` | Pietro | 2026-05-31 pomeriggio | ✅ completo | 46 venues, 92 items - smart rescan |
| `agent2_eatbu_*.csv` | Pietro | 2026-05-31 pomeriggio | ✅ completo | 4 venues, 15 items |
| `agent2_qodeup_*.csv` | Pietro | 2026-05-31 pomeriggio | ✅ completo | 1 venue (Woodstock), 12 items |
| `comune_osm_venues.csv` | data-sourcing | 2026-05-31 sera | 📍 base geografica | 4.649 venue (open data Comune Milano × OSM). NO items. 1.380 con nome, ~505 nomi nuovi = target scraping. |
| `pdf_googledork_*.csv` | data-sourcing | 2026-05-31 sera | 🟡 da review | 7 venue, 81 items da PDF sui siti dei locali. Parsing PDF grezzo → quality-gate prima del merge. |
| `web_extracted_*.csv` | data-sourcing | 2026-05-31 sera | ✅ quality-gated | nome→Startpage→menu sui 505 nomi nuovi (`scripts/web_menu_extractor.py`). 505 processati, 34 con menu, **441 prezzi puliti** (215 normalizzati) su 31 venue. Hit ~6,7%. Già passato il quality-gate (vedi CHANGELOG). |

---

## Quality gates obbligatori PRIMA del commit

Il CEO controlla questi 6 errori in ogni file in entrata. Verifica tu PRIMA di pushare:

1. ❌ URL di file immagine (`.jpg`, `.png`, `.webp`, `.gif`, `.ico`, `.css`, `.js`)
2. ❌ Venues fuori Milano (es. Casa Martini a Pessione TO)
3. ❌ False positive contestuali ("rovere americano" = legno, non cocktail)
4. ❌ Prezzi < €0.50 o > €100 senza spiegazione
5. ❌ venue_name = titolo HTML page (es. "Spritz" perché bar si chiama Spritz Navigli)
6. ❌ Duplicati interni (stesso item + prezzo + venue ripetuto)

Vedi esempi reali di errori risolti in `CHANGELOG.md`.

---

## Cosa NON va in raw_sources/

- ❌ Cache HTML scaricate (sono in `.gitignore`, troppo pesanti)
- ❌ File a metà (push solo file completi)
- ❌ File con encoding diverso da UTF-8 BOM
- ❌ Backup o copie (.bak, .old)
