# Data Quality Report — audit prezzi SurPrice Milano (S5, 02/06/2026)

> Autore: Pietro (agente scraper). Scope: audit di `data/unified_prices.csv` (1.080 price points).
> **Non ho modificato i dati unificati** (territorio CEO). Questo report + `raw_sources/agent5_quality_flags.csv`
> sono la lista azionabile. Obiettivo: garantire un dato pulito e definire una policy di tolleranza.

## 1. Sintesi
> ⚠️ **Due fotografie** (il CEO ha pulito tra le due):
> - **Audit iniziale** (unified_prices = 1.080 punti): **58 fuori banda (5%)**, 16 EXCLUDE + 16 RECLASSIFY + 26 REVIEW.
> - **Audit attuale** (post-merge CEO, **985 punti**): **13 fuori banda (1.3%)** → **4 EXCLUDE + 9 REVIEW**.
>
> Il CEO ha già rimosso ~95 righe (outlier/dup) tra le due passate. La tabella distribuzione (§2) e la
> tassonomia (§4) restano dall'audit iniziale (più ricco, didatticamente utile). Il CSV
> `agent5_quality_flags.csv` riflette lo **stato attuale (13 flag)**.

**I 13 flag attuali** (dettaglio in `raw_sources/agent5_quality_flags.csv`):
- EXCLUDE (4): `CAMPARI SPRITZ — MAXI €19`, `BLACK MOJITO — MAXI €19` (formato maxi), `Coca Cola €5`→negroni (parse error), `Caffè e latte €4`→espresso.
- REVIEW (9): premium plausibili (Negroni Experience €25, Gin Tonic Selection €21, spritz rooftop €19-20), spritz €3.5 / Ichnusa €2 (bassi ma plausibili), "Caffè €4" Ceresio 7 (locale upscale), acqua-in-lattina→soft_drink, e un titolo-pagina ("Barcollando – Milano…" €20, in realtà EXCLUDE).

## 2. Distribuzione prezzi per prodotto (EUR)

| Prodotto | n | min | p10 | mediana | p90 | max |
|---|--:|--:|--:|--:|--:|--:|
| spritz | 145 | 0.75 | 6 | 8 | 14 | 20 |
| negroni | 102 | 3.50 | 7 | 9 | 14 | 25 |
| beer_bottle | 97 | 2 | 4 | 6 | 11 | 25 |
| espresso | 92 | 1 | 1.2 | 2 | 3.9 | 36 |
| soft_drink | 79 | 1 | 3 | 5 | 8.5 | 15 |
| water | 78 | 0.5 | 1 | 2 | 3.5 | 5 |
| americano | 76 | 1 | 2.4 | 8 | 10 | 18 |
| gin_tonic | 59 | 5 | 6 | 8 | 12.5 | 21 |
| mojito | 46 | 2 | 7 | 8.75 | 14 | 19 |
| cappuccino | 44 | 1.5 | 1.5 | 2.5 | 3.5 | 7.8 |
| margarita | 42 | 6 | 7 | 10 | 16 | **90** |
| wine_glass | 34 | 3.5 | 5 | 6.5 | 8 | 10 |
| moscow_mule | 27 | 5 | 7 | 8 | 12 | 18 |
| prosecco_glass | 22 | 4 | 4.5 | 7 | **25** | **35** |
| (beer_moretti, heineken, peroni, daiquiri, manhattan, draft, custom_cocktail: vedi audit) | | | | | | |

## 3. Policy di tolleranza proposta (banda [min, max] per prodotto)

Prezzi fuori banda → flag (escludere o rivedere). Bande tarate sui prezzi reali dei bar Milano:

| Prodotto | min | max | | Prodotto | min | max |
|---|--:|--:|---|---|--:|--:|
| spritz | 4 | 18 | | beer_bottle | 2.5 | 15 |
| negroni | 6 | 22 | | beer_moretti/heineken/peroni | 2 | 10 |
| americano (cocktail) | 5 | 18 | | beer_draft_small | 2 | 8 |
| gin_tonic | 5 | 20 | | beer_draft_medium | 3.5 | 12 |
| mojito | 5 | 18 | | wine_glass | 3 | 15 |
| moscow_mule | 5 | 18 | | prosecco_glass | 3 | 18 |
| margarita | 6 | 22 | | espresso | 0.8 | 3.5 |
| daiquiri | 6 | 22 | | cappuccino | 1 | 4.5 |
| manhattan | 7 | 22 | | soft_drink | 1.5 | 10 |
| custom_cocktail | 5 | 25 | | water | 0.3 | 6 |

**Regole speciali (oltre alla banda):**
1. **Formato MAXI / caraffa / brocca / litro** → ESCLUDERE: è multi-porzione, non comparabile al singolo drink (es. "CAMPARI SPRITZ — MAXI €19", "CARAFFA DI MARGARITA €90").
2. **Disambiguazione brand**: `beer_moretti` deve essere *Birra* Moretti — **"Vittorio Moretti" / "Riserva" / "Franciacorta" = VINO** (Berlucchi/Bellavista), va escluso.
3. **`americano`**: è il *cocktail* (Campari+vermouth). "Caffè/Cafè americano" = **caffè** → reclassificare `espresso`.
4. **`espresso`**: "Espresso **Martini**" = cocktail → `custom_cocktail`. "Affogato/Caffè e latte/cervo" = food/altro → escludere.
5. **`prosecco_glass` vs bottiglia**: prezzo >18 o "bottiglia/Valdobbiadene/DOCG" → è una *bottiglia*, non un calice → escludere dalla metrica calice.
6. **`cappuccino`**: "Ice/Gelato Cappuccino" = gelato → escludere.
7. **`soft_drink`**: craft beer/stout/IPA classificati come soft → reclassificare `beer_*`.

## 4. Tassonomia falsi positivi (cause sistematiche)

| Pattern FP | n | Causa | Azione |
|---|--:|---|---|
| Caffè americano → `americano` cocktail | 11 | omonimia caffè/cocktail | RECLASSIFY→espresso |
| Espresso Martini / food → `espresso` | 11 | "espresso/caffè" nel nome di cocktail o piatto | RECLASSIFY/EXCLUDE |
| Bottiglia → `prosecco_glass` | 6 | "prosecco" nel nome di una bottiglia | RECLASSIFY→bottle/EXCLUDE |
| Vino → `beer_*` o `beer_moretti` | 7 | "Moretti"(vino), "Valpolicella/Ripasso" | EXCLUDE |
| Craft beer → `soft_drink` | 4 | tonica/lattina match troppo largo | RECLASSIFY→beer |
| Caraffa/MAXI → drink singolo | ~5 | formato multi-porzione | EXCLUDE |
| Parse error (es. Spritz €0.75, Coca €15) | ~4 | prezzo da componente/altra riga | EXCLUDE |
| Testo pagina → prodotto (es. "Menu Home" → negroni) | ~2 | estrazione da titolo HTML | EXCLUDE |

## 5. Soglia di tolleranza consigliata per l'inclusione nel DB
- **INCLUDI** se: prezzo entro banda **E** nome coerente col prodotto **E** non MAXI/caraffa.
- **ESCLUDI** automaticamente: fuori banda + pattern FP noto (sopra), MAXI/caraffa, brand-mismatch.
- **REVIEW manuale**: fuori banda ma plausibile premium (es. gin_tonic €21, negroni €25 "Experience", spritz €19 rooftop) → tenere ma con `confidence=low` o flag `premium`.
- Suggerimento: applicare le bande **inline** in tutti gli scraper futuri (già fatto in agent4/S4) per non riproporre il problema a valle.

## 6. Stato backlog S5
- **Geocoding fallback Duomo**: 19/20 venue geocodate → `raw_sources/agent5_geocode_fixes.csv` (1 irrisolto: Morgante, vicolo privato). Da applicare a `unified_venues` lato CEO.
- **eatbu**: sitemap inesistente (404, SPA). Discovery via WebSearch → **11 nuovi venue Milano** in `raw_sources/agent5_eatbu_discovered.csv`. Prezzi via XHR/JS → serve il metodo eatbu degli agent precedenti (non estraibili staticamente).

## 7. File prodotti
- `raw_sources/agent5_quality_flags.csv` — 58 outlier con azione consigliata (per il merge/cleanup CEO)
- `raw_sources/agent5_geocode_fixes.csv` — 19 correzioni coordinate
- `raw_sources/agent5_eatbu_discovered.csv` — 11 venue eatbu nuovi da scrapare
- `scripts/quality_audit.py`, `quality_flags.py`, `geocode_fallback*.py`
