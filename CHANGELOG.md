# Changelog — FoodPrice Milano

> Storico decisioni, problemi risolti, ragionamenti.
> Aggiornare dopo ogni merge o decisione di design importante.
> Formato: data → cosa è successo → perché → impatto.

---

## 2026-05-31 — Sera

### Sistema onboarding agenti (CEO)
- **Cosa**: Creati `AGENTS.md`, `AGENTS_STATE.md`, `PROMPT_PIETRO_NOTTE.md`.
- **Perché**: Nuove sessioni Claude partivano cold senza contesto. Peppe segnalato.
- **Decisione tenuta**: struttura piatta `raw_sources/{fonte}_*.csv`, NON cartelle per-collaboratore (genera silos, duplicati, context frammentato).
- **Impatto**: ogni nuovo agente fa `git clone` + legge `AGENTS.md` → onboarding 5 min.

### Merge agent2 (Pietro sessione 2) — CEO
- **Numeri**: 738 price points (+109), 22 prodotti, 487 venue-product pairs, 126 venues mappa.
- **Junk rimosso (28 items)**:
  - 9 dupes di leggimenu (Spritz Navigli page-title come item_name)
  - 9 URL di immagini (.webp/.png) scrapate per errore
  - 2 soft drink mismatch (Coca Cola descritti come spritz)
  - 1 Terrazza Martini (Casa Martini è a Pessione TO, NON Milano)
  - 1 Sicilian white_wine €16 (era pasta description)
  - Vari false positive ("rovere americano" = legno, non cocktail)
- **Geocoding**: 29 venues match esatto con DB esistente, 21 fallback Milan center.

### Frainteso "GAP 167 venues" dal report del collega
- **Diagnosi sbagliata**: il collega contava `extraction_status=filtered_out` come "da scrappare".
- **Realtà**: quelli sono ristoranti/pizzerie/sushi, NON sono target del progetto.
- **Decisione**: NON rifare scraping su quei venues. Le venues "mancanti" reali sono ~55 (per MyCIA), la maggior parte `ok_no_menu` (proprietario non ha caricato menu).

---

## 2026-05-31 — Mattina/Pomeriggio

### Merge sessione 1 Pietro (CEO)
- **Sources integrate**: pdf (52 items), scraper (36 items), leggimenu (4.832 items), menudigitale (242 items dopo filtro Milano).
- **Da 174 → 629 price points** in un colpo solo. Leggimenu il game-changer.
- **Problema risolto**: menudigitale conteneva 12.600 items NAZIONALI. Filtrato a sole 2 venues Milano confermate (Corner, Mulberry) per non inquinare il DB.
- **Problema risolto**: leggimenu venues senza geo → 2 match esatti DB + 39 fallback Milano centro. Da geocodare con precisione in sessione futura.

### Funky beer split fix
- **Bug parser PDF**: "Moretti IPA € 6,00 € 7,00" parsato come €13 (somma).
- **Fix**: split in 2 righe: piccola €6, media €7.
- **Stessa cosa**: Ichnusa €5+€6, vini in bottiglia €25 ma calice €6.

---

## 2026-05-30 — Setup iniziale

### Decisione: MyCIA come prima fonte (CEO)
- 648 Milano venues dal sitemap MyCIA. 122 con menu completo, 471 filtered_out (ristoranti).
- **Decisione**: scope "bar/pub/cocktail bar" → tutto il resto fuori.

### Decisione: Wolt NON in Italia
- Testato Wolt API → Italia non presente nel sitemap (verificato).
- **Impatto**: Pietro 1 deve sostituire Wolt con Glovo nella sua lista fonti.

### Decisione: NO Wolt/Glovo via API
- Wolt: API "We've updated the app" → bloccato.
- Glovo: richiede `Glovo-Perseus-Session-Id` real → solo Playwright.
- **Impatto**: rimandato a sessione Playwright dedicata.

### Decisione: qromo NON estratto
- robots.txt vieta `/API` esplicitamente.
- 25 venues nel DB come record (per discoverability), ma 0 items.
- **MAI tentare di bypassare**: progetto pubblico, no rischi legali.

---

## Convenzioni progetto

### Struttura raw_sources/
- **Naming**: `{fonte}_{venues|menu_items}.csv` — singolare fonte, plurale entità
- **Esempio**: `thefork_venues.csv` + `thefork_menu_items.csv`
- **Per re-scraping nuovi**: prefisso `agentN_` (es. `agent2_direct_website_*.csv`)
- **NO cartelle per-collaboratore**: silos cattivi. Naming già identifica autore via prefix.

### Quality gates pre-commit
Lista bloccanti applicata da CEO PRIMA di ogni merge:
1. Niente URL immagine (`.jpg/.png/.webp/.ico/.css/.js`)
2. Niente venues fuori Milano (verifica city/address)
3. Niente false positive contesto ("americano" su whiskey, "white_wine" su pasta)
4. Niente prezzi < €0.50 o > €100 senza review
5. Niente venue_name = titolo pagina HTML

### Geocoding policy
1. Match contro DB esistente (threshold 0.85 sequence match)
2. Se no match → Nominatim (1 req/s, free)
3. Se no match → Milano centro (`45.4642, 9.1900`) come fallback
4. Mark `geocoding_confidence` in metadata se importante distinguere

### Schema CSV
SEMPRE in linea con `scripts/SCHEMA_AGENTI.md`. Header obbligatorio. UTF-8 BOM.
