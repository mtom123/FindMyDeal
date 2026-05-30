# Delivery App Landscape — Italia 2026

## Stato attuale (verificato 2026-05-30)

| App | Italia | Milano | API senza browser | Note |
|-----|--------|--------|:-----------------:|------|
| **Glovo** | ✅ Attivo | ✅ | ❌ | Richiede `Glovo-Perseus-Session-Id` (header auth). Playwright needed. |
| **JustEat.it** | ✅ Attivo | ✅ | ❌ | SPA Next.js, tutto rimanda all'homepage. Playwright needed. |
| **Wolt** | ❌ **NON in Italia** | ❌ | — | Copre: FIN, SWE, EST, LTU, DNK, HUN, CZE, POL, GRC, ecc. **Italia non presente.** |
| **Deliveroo** | ❌ Uscita nel 2022 | ❌ | — | Exited Italian market. |
| **Uber Eats** | ❌ Uscita nel 2021 | ❌ | — | Exited Italian market. |
| **Amazon Prime Now** | ✅ Solo grocery | ❌ | — | No bar/ristoranti. |

## Raccomandazioni per gli agenti

- **Agent 1** (Wolt, JustEat, TheFork, Eatbu): **Rimuovere Wolt dalla lista** — non copre l'Italia.
  Sostituirlo con **Glovo** usando Playwright.
- **TheFork**: Datadome CAPTCHA — richiede Playwright obbligatoriamente.
- **JustEat**: SPA — richiede Playwright.
- **Glovo**: API autenticata — richiede Playwright con sessione reale.

## Fonti delivery attive in Italia (priorità per Agent 1)

1. **Glovo** (primario) — molti bar/pub, prezzi delivery, richiede Playwright
2. **JustEat.it** (secondario) — coverage minore per bar standalone

## Fonti NON-delivery accessibili senza browser

| Fonte | Accessibile | Note |
|-------|:-----------:|------|
| **MyCIA** | ✅ | Next.js RSC server-rendered, JSON-LD embedded |
| **OSM Overpass API** | ✅ | Free, bar con website URLs |
| **Siti diretti dei locali** | ✅ parziale | Dipende dal sito, molti sono SPA |
| **LeggiMenu** | ❌ | No city search pages (B2B QR tool) |
| **iamenu** | ❌ | SSL error |
| **one2menu** | ❌ | DNS non risolve |
| **buonmenu** | ❌ | Connection error |
| **menudigitale.it** | ❌ | Under construction |
| **dishcovery** | ❌ | Redirect JS |
| **gromo** | ❌ | 403 Forbidden |
| **TripAdvisor** | ❌ | Cloudflare bot protection |
