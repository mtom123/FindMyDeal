# Agent4 deep-scan report (S4 — 02/06/2026)

| Metrica | Valore |
|---|---|
| Venues processate | 88/88 |
| Venues con nuovi drink | 66 |
| Venues senza nuovi drink | 22 (siti JS/no-prezzo) |
| Price points estratti (post-QG) | **236** |
| Copertura prezzo | 100% |
| Nuovi prodotti/venue (media sui 66) | 3.6 |

## Distribuzione per prodotto

| Prodotto | Items |
|---|---|
| spritz | 35 |
| negroni | 34 |
| americano | 25 |
| espresso | 24 |
| beer_bottle | 20 |
| soft_drink | 16 |
| water | 14 |
| cappuccino | 12 |
| wine_glass | 10 |
| beer_heineken | 10 |
| margarita | 10 |
| gin_tonic | 6 |
| prosecco_glass | 5 |
| mojito | 4 |
| beer_moretti | 3 |
| moscow_mule | 3 |
| daiquiri | 2 |
| beer_peroni | 2 |
| manhattan | 1 |

## Top venues per yield

| Venue | Prima (DB) | Estratti S4 |
|---|---|---|
| Caffè Fernanda | 1 | 10 |
| Caffefernanda | 2 | 10 |
| Norin Caffè Bistrot | 2 | 10 |
| Papeete | 1 | 8 |
| Refeel | 1 | 8 |
| Armanisilos | 2 | 8 |
| Luca & Andrea | 2 | 8 |
| Armadi Silos Caff√® | 3 | 8 |
| La Birrofila | 2 | 7 |
| labirrofila.com | 3 | 7 |
| Sui Generis | 2 | 6 |
| suigeneris.bar | 2 | 6 |

## Quality gate (inline, S3 lesson)

Scartati a monte: PRICE_TOO_HIGH_FOR_PRODUCT (~36, bottiglie/mis-price), MENU_NOTE, FOOD, COFFEE_NOT_COCKTAIL (caffè americano≠cocktail), NON_MILAN.
QA finale: image_url=0, food=0, dup=0, acqua→beer=0, prezzi entro range per-prodotto.

## Metodo per piattaforma

- **mycia (43)**: ri-classificazione dei menu locali già scaricati con i 22 pattern → recupera birre/drink non normalizzati (es. Bar Magenta: Heineken×5 + Moretti).
- **direct_website/web_extract/eatbu (42)**: re-fetch + estrazione regex riga-per-riga + PDF + path-probing.
- **leggimenu (3)**: pagine categoria server-side (.lmcart-add data-price).

## Nota onesta sul target
Target prompt: +500 price points. Estratti: **236** puliti. Il gap è scelta di QUALITÀ post-S3: 22 venue hanno siti JS-rendered/senza prezzi in HTML (yield 0), e il gate ha rimosso ~177 falsi positivi (da un grezzo di ~413). Meglio 236 puliti che 413 con il 40% di rumore.