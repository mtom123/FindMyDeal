# Next steps & deep-dive backlog (Pietro, agg. 02/06/2026)

Temi lasciati indietro nelle sessioni S2→S5, con priorità e approccio suggerito.

## 🔴 Alto valore
1. **eatbu — estrazione prezzi (11 venue nuovi pronti)**
   `raw_sources/agent5_eatbu_discovered.csv` ha 11 venue Milano (UNPLUG, Wave Cocktail, Bootleg Pub…).
   Prezzi NON nell'HTML statico (euro=0) → caricati via XHR/JS. Recuperare il metodo usato in
   agent2/3/4_eatbu (probabile endpoint API eatbu) e riapplicarlo. Yield atteso ~10 venue × 15-30 item.

2. **Applicare quality_flags + geocode_fixes al merge**
   `agent5_quality_flags.csv` (16 EXCLUDE + 16 RECLASSIFY) e `agent5_geocode_fixes.csv` (19 coord)
   vanno recepiti dal CEO nel `merge_pipeline.py` / pulizia `unified_*`. Sblocca dato più pulito + 19 pin corretti.

3. **Libreria di normalizzazione condivisa (anti-falsi-positivi)**
   Centralizzare le regole di disambiguazione in un modulo usato da TUTTI gli agent:
   - `americano` cocktail vs "caffè americano"
   - `beer_moretti` (birra) vs "Vittorio Moretti / Franciacorta" (vino)
   - `prosecco_glass` calice vs bottiglia; `espresso` vs "Espresso Martini"
   - formato MAXI/caraffa → escludere. Evita di ri-scoprire gli stessi FP ad ogni sessione.

## 🟠 Medio valore
4. **TheFork — prezzi**: Wayback dà venue+geo ma NON prezzi (menu JS). Servono proxy residenziale +
   browser headful, oppure API ufficiale. `agent4_thefork` ha già 77 item (metodo da verificare/estendere).
5. **menudigitale tutta-Italia**: in `~/Desktop/Find My Deal/raw_sources/` ho 12.600 item / 97% prezzi
   (tutta Italia, fuori scope Milano). Con SurPrice multi-vertical/multi-città potrebbe rientrare in scope →
   decisione CEO. Pronto da integrare se serve.
6. **26 outlier in REVIEW**: verifica manuale dei premium plausibili (gin_tonic €21, negroni €25 "Experience",
   spritz rooftop €19) vs errori. Tenere con flag `premium`/`confidence=low`.

## 🟢 Basso valore / completamento
7. **Morgante Cocktail** (1 venue): geocoding manuale — Vicolo dei Lavandai/Naviglio Grande (~45.451, 9.173).
8. **Copertura prodotti scarsi**: manhattan (10), custom_cocktail (4), beer_draft_medium (9) — pochi punti.
   Mirare venue cocktail-bar per questi nelle prossime estrazioni.
9. **mycia full-menu live**: ho ri-classificato il file locale; se per alcuni venue è parziale, ri-parsare
   il payload Next.js `self.__next_f.push(...)` della pagina live per il menu completo.

## ⛔ Bloccati (non re-tentare senza nuove risorse)
- **qromo**: `/API` vietata da robots.txt.
- **Glovo/JustEat**: SPA + anti-bot; solo `price_type=delivery` (prezzo maggiorato), bassa priorità.
- **TheFork live**: Datadome 403 anche con Playwright stealth headless (testato).

## Nota di metodo (lezione trasversale)
Quality-gate **inline** (bande prezzo + disambiguazione brand + no-MAXI) in ogni scraper PRIMA di consegnare.
Su S3 il filtro post-hoc ha scartato il 92%; su S4/S5 il gate inline ha tenuto il rumore <5%.
