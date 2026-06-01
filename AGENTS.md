# Agent Onboarding — FoodPrice Milano

> **LEGGI QUESTO FILE PER PRIMO** se sei un nuovo agente Claude su questo repo.

## 📚 Ordine di lettura per onboarding (5 minuti)

1. **`AGENTS.md`** (questo) — ruoli, workflow, regole base
2. **`AGENTS_STATE.md`** — cosa è già fatto, cosa serve. NON duplicare lavoro!
3. **`CHANGELOG.md`** — STORIA decisioni e ragionamenti del progetto. Capisci il PERCHÉ.
4. **`raw_sources/README.md`** — scheda d'identità di ogni file CSV
5. **`scripts/SCHEMA_AGENTI.md`** — formato CSV obbligatorio (solo per scraper)

Se sei frontend dev, leggi anche **`BRIEF_PEPPE.md`**.

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
│   ├── mycia_*.csv             ← completo (648 venues)
│   ├── leggimenu_*.csv         ← completo (35 venues Milano, 4.214 items)
│   ├── menudigitale_*.csv      ← completo (2 venues Milano)
│   ├── qromo_*.csv             ← solo venues, no items (robots.txt)
│   ├── direct_*.csv / scraper_*.csv / agent2_*.csv  ← sessioni Pietro
│   ├── pdf_*.csv / pdf_googledork_*.csv  ← menu PDF
│   ├── web_extracted_*.csv     ← Startpage→sito→menu (Peppe)
│   └── comune_osm_venues.csv   ← 4.649 venues geo base (Comune Milano)
│
├── data/                       ← OUTPUT unificato dal merge (NON modificare)
│   ├── unified_venues.csv      ← 1.558 venues deduplicate
│   ├── unified_menu_items.csv  ← 5.361 items normalizzati
│   └── unified_prices.csv      ← 829 price points geo+normalizzati
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
- **Storico decisioni**: `CHANGELOG.md`
- **Identità file raw_sources**: `raw_sources/README.md`
- **Brief frontend**: `BRIEF_PEPPE.md`

---

## 📞 Quando bloccato

1. Apri Issue su GitHub (`Bug` o `Question` label)
2. Tag @CEO nella issue
3. Continua con altro task nel frattempo

Buon lavoro! 🍹
