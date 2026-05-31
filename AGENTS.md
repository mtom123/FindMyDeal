# Agent Onboarding — FoodPrice Milano

> **LEGGI QUESTO FILE PER PRIMO** se sei un nuovo agente Claude su questo repo.

---

## 🎯 Cos'è il progetto

**FoodPrice Milano** — mappa interattiva dei prezzi drink nei bar di Milano.
Sito live: https://mtom123.github.io/FindMyDeal/

Fase attuale: raccolta dati distribuita tra più collaboratori + un orchestratore.

---

## 👥 Chi fa cosa

| Ruolo | Nome | Compito |
|---|---|---|
| **CEO / Orchestratore** | Claude (Motti) | Coordina, fa merge, gestisce schema dati, aggiorna sito |
| **Agente Scraper 1** | Pietro | Scraping siti diretti, PDF, eatbu, qodeup, sources nuove |
| **Agente Scraper 2** | (vario) | leggimenu, menudigitale, qromo, mycia |
| **Frontend Dev** | Peppe | Implementa il sito (Leaflet + JS vanilla) |

Tu sei probabilmente **uno scraper agent** o **il CEO**. Identifica il tuo ruolo dal prompt che ti hanno dato.

---

## 📁 Struttura del repo

```
FindMyDeal/
├── index.html                  ← sito live (Peppe)
├── prices_data.json            ← feed dati sito (rigenerato dal merge)
│
├── AGENTS.md                   ← QUESTO FILE — onboarding agenti
├── BRIEF_PEPPE.md              ← brief per il frontend
├── COLLABORATORI.md            ← guida git workflow
├── README.md                   ← presentazione pubblica
│
├── raw_sources/                ← INPUT degli scraper
│   ├── mycia_*.csv             ← già completo
│   ├── leggimenu_*.csv         ← già completo
│   ├── menudigitale_*.csv      ← già completo  
│   ├── qromo_*.csv             ← legale, no items
│   ├── direct_*.csv            ← già completo
│   ├── pdf_*.csv               ← già completo
│   ├── scraper_*.csv           ← prima sessione Pietro
│   └── agent2_*.csv            ← seconda sessione Pietro
│
├── data/                       ← OUTPUT unificato dal merge
│   ├── unified_venues.csv      ← 1.059 venues deduplicate
│   ├── unified_menu_items.csv  ← 5.473 items normalizzati
│   └── unified_prices.csv      ← 738 price points geo+normalizzati
│
└── scripts/                    ← TOOLS
    ├── SCHEMA_AGENTI.md        ← spec CSV OBBLIGATORIA
    ├── merge_pipeline.py       ← orchestratore (solo CEO esegue)
    ├── mycia_scraper.py        ← reference scraper
    ├── osm_direct_scraper.py
    ├── build_outputs.py
    └── PROMPT_PER_AGENTI_SCRAPER.md
```

---

## 🔄 Workflow standard

### Sei uno SCRAPER agent?

```
1. git pull origin main                     # aggiornati prima di iniziare
2. Leggi scripts/SCHEMA_AGENTI.md           # formato CSV obbligatorio
3. Leggi AGENTS_STATE.md                    # vedi cosa è già stato fatto
4. Lavora sul tuo scraper in locale         # NON modificare data/ o prices_data.json
5. Output: raw_sources/{tua_fonte}_venues.csv + raw_sources/{tua_fonte}_menu_items.csv
6. git add raw_sources/{tua_fonte}_*.csv
   git commit -m "data: {fonte} — N venues, M items"
   git push origin main
7. AVVISA IL CEO — lui fa merge + push aggiornato
```

### Sei il CEO?

```
1. git pull
2. Verifica raw_sources/ per nuovi file
3. Quality check (filtra junk: image URLs, false positives, non-Milan venues)
4. python scripts/merge_pipeline.py
5. Verifica merge_report.txt e numeri unified_prices.csv
6. git add data/ prices_data.json + eventuali fix in raw_sources/
7. git commit + push
```

### Sei il FRONTEND dev (Peppe)?

```
1. git pull
2. Lavora su index.html / CSS / JS
3. NON toccare prices_data.json (rigenerato dal merge)
4. git add index.html + asset
5. git commit + push → sito live in 60s
```

---

## ⛔ Cosa NON fare MAI

- ❌ Non modificare `data/unified_*.csv` a mano (output del merge)
- ❌ Non modificare `prices_data.json` a mano (rigenerato dal merge)
- ❌ Non duplicare lavoro già fatto (vedi `AGENTS_STATE.md` per lo stato)
- ❌ Non inventare dati — se non hai un prezzo, lascia `normalized_price_eur=0` e `confidence=low`
- ❌ Non bypassare robots.txt (qromo /API è VIETATO, niente Wolt/Glovo senza Playwright)
- ❌ Non scrappare senza rate limiting (minimo 1.5s tra requests)
- ❌ Non pushare cache di pagine scaricate (sono in `.gitignore`: `raw_data/`)

---

## ⚠️ Errori comuni degli agenti precedenti

1. **Confondere `extraction_status=filtered_out` con "da scrappare"** → quei venues NON sono target (ristoranti, pizzerie). Non rifarli.
2. **Scrappare URL di immagini (.jpg/.png/.webp)** come fossero pagine menu → produce junk
3. **Normalizzare `americano` su "rovere americano" (whiskey)** → false positive contesto
4. **Geocodare venues senza verifica** → finiscono su Milano centro stacked
5. **Mandare 12.000 items "nazionali"** senza filtrare per Milano → 99% non utilizzabile

---

## 🔗 Link utili

- **Sito live**: https://mtom123.github.io/FindMyDeal/
- **Repo**: https://github.com/mtom123/FindMyDeal
- **Schema CSV**: `scripts/SCHEMA_AGENTI.md`
- **Stato dataset**: `AGENTS_STATE.md`
- **Brief frontend**: `BRIEF_PEPPE.md`

---

## 📞 Quando bloccato

1. Apri Issue su GitHub (`Bug` o `Question` label)
2. Tag @CEO nella issue
3. Continua con altro task nel frattempo

Buon lavoro! 🍹
