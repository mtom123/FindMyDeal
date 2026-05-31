# Sessione notturna Pietro — report (01/06/2026)

Eseguito `PROMPT_PIETRO_NOTTE.md` su ambiente **macOS** (il prompt era scritto per Windows/`D:\`).
Letti prima: `AGENTS_STATE.md`, `raw_sources/README.md`, `CLAUDE.md`.

## Esito per step

### ✅ STEP 2 — Geocoding leggimenu (FATTO)
- **29/39** venue stackate su Duomo (45.4642) ora hanno **coordinate precise** (Nominatim, bbox Milano).
- Totale leggimenu con geo preciso: **31/41**.
- Indirizzi recuperati da JSON-LD dove mancanti (es. Los Locos → Via Novara 196).
- File aggiornato: `raw_sources/leggimenu_venues.csv`. Script: `scripts/geocode_leggimenu.py`.

**⚠️ Scoperta di qualità — 6 venue NON sono a Milano** (falsi positivi della discovery leggimenu di stamattina; il bbox li ha scartati). Da **rimuovere** dal dataset Milano:
| Venue | Città reale |
|-------|-------------|
| Pub51 | Lercara Friddi (PA) |
| Coco Loco | Aradeo (LE) |
| Bivacco | Transacqua (TN) |
| Birra Bader | Siena |
| Canaglie del Navigli | Parma |
| SOLO APERITIVO popup | Ferrara |

4 venue Milano restano senza geo (indirizzo malformato/assente): Frigo Milano (Piazza Borromeo 5), Al Chiosco Da Giacomo (P.le Corvetto), Laudano e Misture, UNAHOTELS Scandinavia → geocoding manuale rapido.

### ⛔ STEP 1 — TheFork (BLOCCATO da Datadome)
- `thefork.it` e `thefork.com/search` → **HTTP 403 + Datadome al primo request** (anche solo homepage).
- Il prompt stesso impone "non bypassare il captcha, non insistere". Un bypass Datadome con Playwright-stealth da IP non residenziale ha probabilità molto basse.
- **Non perseguito** in coerenza col prompt. Serve decisione CEO (proxy residenziale? accordo API TheFork?).

### ⏭️ STEP 3 — Discovery leggimenu/comune_osm (in gran parte SUPERATO)
- `AGENTS_STATE` (31/05 sera) mostra che la sessione `web_extracted` ha **già** processato i ~505 nomi nuovi (inclusi quelli da `comune_osm`) → 34 hit, 441 prezzi. Il cross-ref nomi→menu è quindi già stato fatto dopo la stesura del prompt.
- Resa marginale residua bassa (slug leggimenu/menudigitale opachi, non basati sul nome).

### ⏭️ STEP 4 — PDF recovery (SUPERATO)
- Tutti i venue della lista (Harp, Barbisa, Headbangers, Frankie's, La Rocchetta, Brewfist, Pandenus) sono **già in `data/unified_venues.csv`** (coperti da `pdf_googledork`, 31/05 sera). Nessun nuovo da aggiungere.

### ⏭️ STEP 5 — Smart rescan cache (NON DISPONIBILE)
- Le 1.241 pagine HTML sono nella cache su `D:\FindMyDeal\cache\` (macchina Windows). Non presenti su questa macchina.

## Conclusione
Il prompt notturno è **parzialmente datato**: gli step 3-4 sono stati assorbiti dalle sessioni "sera", lo step 5 dipende da cache locale Windows, e lo step 1 (TheFork) resta l'unico vero blocker tecnico (Datadome).
**Valore reale aggiunto stanotte: geocoding di 29 venue** (sblocca i pin accatastati sul Duomo) + identificazione di 6 venue non-Milano da pulire.

## Consegna
- Modificato: `raw_sources/leggimenu_venues.csv` (coordinate). Nessun push (auth GitHub non configurata su questa macchina).
