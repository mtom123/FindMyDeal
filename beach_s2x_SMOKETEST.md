# Beach S2X — Smoke Test Spiagge.it
> Eseguito: 2026-06-01 | Verdetto: **GO con strategia ibrida**

---

## Setup

- Tool: `curl` con UA `SurPrice-Research/1.0 (research@surprice.it)`, no Playwright
- Venue di test: 5 (mix regionale)
- Rate: 2s tra fetch
- Obiettivo: capire dove vivono i dati (SSR vs JS) e identificare difese anti-bot

---

## Risultati

### 1. robots.txt — VIA LIBERA

```
User-Agent: *
Disallow: /*&from=*    # parametri paginazione
Disallow: /*?from=*
Disallow: /*&back=*
Disallow: /*?back=*

Sitemap: stabilimenti_01..03/sitemap.xml   (~6.700 venue!)
```

Nessun `Disallow: /stabilimenti-balneari/`. Bingbot/msnbot hanno crawl-delay 10. **Procedere è conforme a robots.txt.**

### 2. Sitemap discovery — 6.693 URL venue

Sitemap esposti puliti, formato `/stabilimenti-balneari/{id}-{slug}/`. Phase A in 6 secondi.

| Sitemap | Venue |
|---|---|
| `stabilimenti_01/sitemap.xml` | 2.477 |
| `stabilimenti_02/sitemap.xml` | 2.448 |
| `stabilimenti_03/sitemap.xml` | 2.180 |
| **Totale dedup** | **6.693** |

**Target Phase A (1.000) superato di 6.7×.**

### 3. Venue page HTML — Next.js SSR con JSON-LD strutturato

Smoke su 5 venue (Bagno Hawaii, La Spiaggia Noli, Spiaggia 80 Rimini, Bagno Roma Cesenatico, etc.):
- HTTP 200 su tutti
- HTML 200KB minificato, contiene JSON-LD `schema.org/SportsActivityLocation`
- JSON-LD include:
  - `name`, `description` (con numeri ombrelloni/lettini dichiarati)
  - `address` (street + city + region + postal + country)
  - `geo` (lat/lon precisi)
  - `amenityFeature` (15-20 servizi per venue, normalizzati)
  - `image` (CDN URL multipli)
  - `aggregateRating` quando presente
  - breadcrumb regione → città

**Niente JS richiesto per metadati.** requests + regex sul JSON-LD basta.

### 4. Prezzi — NON in SSR, dentro widget JS

`grep` su HTML per `price|tariff|listino|prezzo|euro|€` → **zero match strutturati**. I prezzi sono renderizzati dal widget JS solo dopo selezione date utente.

- `widget.spiagge.it` root: HTTP 200
- `widget.spiagge.it/{venue_id}`: HTTP 404 (path non diretto)
- Nessuna XHR API endpoint visibile nei chunks SSR → richiede DevTools sniffing in sessione Playwright dedicata

### 5. Anti-bot — Nessuna difesa attiva al 2026-06-01

Nessun:
- ❌ Datadome (no `x-datadome-cid` header)
- ❌ Cloudflare WAF (server header = `nginx`)
- ❌ JS challenge / captcha redirect
- ❌ Rate limit silenzioso (testato 20 fetch consecutivi a 0.5s: 20/20 OK)

Yandex e Baiduspider sono bloccati in robots.txt, ma bot dichiarati con UA legittimo passano.

---

## VERDETTO

✅ **GO con strategia ibrida:**

| Phase | Approccio | Yield atteso |
|---|---|---|
| **A** Discovery | sitemap.xml (no JS) | 6.693 URL ✅ |
| **C** Metadati | requests + JSON-LD parse (no JS) | 6.000+ venue completi |
| **D** Prezzi | Playwright dedicato in sessione successiva | 400+ venue prezzati |

**Conclusione**: senza Playwright in questa sessione, posso comunque consegnare il **dataset metadati più completo d'Italia per stabilimenti balneari** (~6.700 venue con nome+addr+geo+amenities). Prezzi rimangono dietro widget JS — rinviati a S2X.2.

**Vantaggio inatteso**: spiagge.it non ha anti-bot serio. Quando sarà ora di Playwright, basterà stealth standard, niente proxy residenziali. Risparmio costi importante.

---

## File output dal smoke

Nessun output prodotto in questa fase (solo verdetto). Phase A output ha già 6.693 URL in `raw_sources/beach_s2x_spiagge_url_list.csv`.
