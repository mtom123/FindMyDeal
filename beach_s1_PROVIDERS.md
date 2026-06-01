# Beach S1 — Booking Provider Discovery
> Sessione S1 | Data: 2026-06-01 | Metodo: web discovery + provider page analysis

## Executive Summary

Il mercato digitale degli stabilimenti balneari italiani è frammentato tra 7 provider principali. **Spiagge.it** domina con >1.000 venue e market share stimata al 40-50%. I provider restanti si spartiscono il mercato in nicchie regionali o funzionali. La pricing pubblica varia molto per provider: spiagge.it richiede selezione date (no scraping diretto), mentre i siti proprietari e i consorzi regionali espongono listini statici ideali per S2.

---

## Provider 1: Spiagge.it

- **URL**: https://www.spiagge.it/
- **Tipo**: Marketplace booking + gestionale SaaS
- **Venues stimate**: 1.000+
- **URL pattern venue**: `https://www.spiagge.it/stabilimenti-balneari/{ID}-{slug}/`
- **Esempio**: https://www.spiagge.it/stabilimenti-balneari/13832-la-spiaggia/
- **Pricing pubblico**: PARZIALE — prezzi visibili solo dopo selezione date (dynamic pricing widget)
- **Indicizzato Google**: SÌ — landing pages per ogni comune indicizzate
- **Anti-bot**: Leggero (nessun Cloudflare rilevato nelle pagine statiche; widget booking potenzialmente JS-heavy)
- **Scraping feasibility**: MEDIA — i metadati venue (nome, indirizzo, telefono, website) sono scrappabili; i prezzi richiedono interazione JS
- **Stagione coperta**: Tutto l'anno (prenotazioni da Aprile a Ottobre)
- **Note**: Il gestionale (ex-YourBeach) integra prenotazioni + punto vendita. 500.000+ prenotazioni estate 2022. Collabora con Ombrellove. Venue verificate hanno logo e badge "Partner Ufficiale".

**Venues trovate su spiagge.it durante S1** (sample Cesenatico + Rimini):
| Venue | URL |
|---|---|
| Bagno Hawaii | https://www.spiagge.it/stabilimenti-balneari/10389-bagno-hawaii/ |
| Bagno Libra | https://www.spiagge.it/stabilimenti-balneari/25013-bagno-libra-63-63a-63b-64-65/ |
| Blue Beach Rimini | https://www.spiagge.it/stabilimenti-balneari/19282-blue-beach/ |
| MiVida Beach | https://www.spiagge.it/stabilimenti-balneari/20373-bagno-mario-74a/ |
| Bagni La Spiaggia Noli | https://www.spiagge.it/stabilimenti-balneari/13832-la-spiaggia/ |
| Bagni Sirena | https://www.spiagge.it/stabilimenti-balneari/27339-bagni-sirena-21-23/ |
| Bagno Snoopy Cesenatico | https://www.spiagge.it/stabilimenti-balneari/10363-bagno-snoopy/ |
| Grand Hotel Cesenatico | https://www.spiagge.it/stabilimenti-balneari/22601-grand-hotel-cesenatico-52/ |

---

## Provider 2: iBagnino

- **URL**: https://ibagnino.com/
- **Tipo**: Booking + gestionale ombrelloni
- **Venues stimate**: 200-500 (dato non pubblico)
- **URL pattern venue**: `/stabilimento/{slug}` (da verificare)
- **Pricing pubblico**: NO — richiede account/date
- **Indicizzato Google**: SÌ (homepage)
- **Anti-bot**: Non rilevato
- **Scraping feasibility**: BASSA — pricing non esposta pubblicamente
- **Note**: Piattaforma specializzata nella selezione ombrellone su mappa interattiva. Focus Italia adriatica e tirrenica.

---

## Provider 3: BeachUP (Sintur)

- **URL**: https://beachup.sintur.com/
- **Tipo**: Gestionale + booking SaaS
- **Venues stimate**: 100-300
- **URL pattern venue**: Da determinare
- **Pricing pubblico**: NO
- **Indicizzato Google**: SÌ
- **Anti-bot**: Non rilevato
- **Scraping feasibility**: BASSA
- **Note**: Dashboard multi-stabilimento, mappa interattiva ombrelloni. Contatto: beachup@sintur.com | tel 0702347812. Probabilmente più forte in Sardegna (sede Cagliari).

---

## Provider 4: Mondo Balneare

- **URL**: https://www.mondobalneare.com/
- **Tipo**: Directory + showcase + lead generation
- **Venues stimate**: 500+ (vetrina, non tutte prenotabili)
- **URL pattern venue**: `https://www.mondobalneare.com/stabilimenti/{slug}/`
- **Pricing pubblico**: PARZIALE — alcune venue mostrano "da €X"
- **Indicizzato Google**: SÌ — ben indicizzato per "stabilimenti [città]"
- **Anti-bot**: Non rilevato
- **Scraping feasibility**: ALTA per metadati; MEDIA per prezzi
- **Note**: Più vetrina che booking engine. Ha sezione "Fornitori" con tutti i software balneari. Dati utili per discovery venue.

---

## Provider 5: Summer Booking (Qbitsoft / beacharound.com)

- **URL**: https://summerbooking.it/
- **Tipo**: Gestionale + marketplace booking
- **Redirect**: beacharound.com → summerbooking.it (301)
- **Venues stimate**: 300+ (stima)
- **URL pattern venue**: `https://summerbooking.it/it/spiagge/{slug}/prezzi-ombrellone-lettino-sdraio`
- **Pricing pubblico**: PARZIALE — alcune venue espongono prezzi statici
- **Indicizzato Google**: SÌ
- **Anti-bot**: Non rilevato
- **Scraping feasibility**: MEDIA-ALTA
- **Note**: Piattaforma precedentemente nota come Beacharound. Acquisizione/rebrand 2025-2026. Ha pagine prezzi accessibili per alcune venue (pattern `/prezzi-ombrellone-lettino-sdraio`). **Target prioritario per S2**.

---

## Provider 6: Consorzi regionali (bibionemare.com, lignano-riviera.it, etc.)

- **URL**: https://stabilimenti.bibionemare.com/ e simili
- **Tipo**: Consorzio locale di prenotazione
- **Venues stimate**: 20-80 per consorzio
- **URL pattern venue**: `https://stabilimenti.bibionemare.com/en/` (listing unificato)
- **Pricing pubblico**: SÌ — listino prezzi per stagione e fila pubblicato
- **Indicizzato Google**: SÌ
- **Anti-bot**: Nessuno
- **Scraping feasibility**: ALTA — dati strutturati e pubblici
- **Note**: Bibione, Lignano, Jesolo, Grado hanno consorzi locali con prenotazione centralizzata. **Source di qualità massima per S2** per quelle aree.

Esempi trovati:
- bibionemare.com: 4 venue con prezzi (Seven Beach, Kokeshy, Shany, Pinedo)
- spiaggia14e15.it: Lignano, prezzi pubblici
- laspiaggiadiduke.com: Lignano, prezzi pubblici
- lignano-riviera.it: booking centralizzato Lignano

---

## Provider 7: iBeach

- **URL**: https://www.ibeach.it/
- **Tipo**: Booking ombrelloni (22.000+ ombrelloni dichiarati)
- **Status attuale**: ⚠️ IN MANUTENZIONE al 2026-06-01
- **Pricing pubblico**: Non verificabile (sito offline)
- **Scraping feasibility**: DA RIVALUTARE in S2
- **Note**: Stava emergendo come player con numerosi ombrelloni. Da monitorare se torna online.

---

## Provider 8: Cocobuk

- **URL**: https://cocobuk.com/
- **Tipo**: Booking ombrelloni multi-regione
- **Venues stimate**: 100+ (stima)
- **Pricing pubblico**: Richiede navigazione interna
- **Scraping feasibility**: MEDIA
- **Note**: Presente in Sicilia e altre regioni. Contenuto principale non accessibile da homepage.

---

## Mapping Booking Provider → Field `booking_provider`

Per il CSV venues, usare questi valori nel campo `booking_provider`:

| Provider | Valore CSV |
|---|---|
| Spiagge.it | `spiagge.it` |
| iBagnino | `ibagnino` |
| BeachUP | `beachup` |
| Mondo Balneare | `mondobalneare` |
| Summer Booking / Beacharound | `summerbooking` |
| Consorzio Bibione | `bibionemare` |
| Consorzio Lignano | `lignano-riviera` |
| iBeach | `ibeach` |
| Cocobuk | `cocobuk` |

---

## Strategia S2 (raccomandazione)

**Priority 1 — Consorzi regionali** (bibionemare, lignano-riviera, spiaggia14e15): prezzi pubblici, strutturati, alta confidenza. Estrarre sistematicamente.

**Priority 2 — Summer Booking / Beacharound** (`/prezzi-ombrellone-lettino-sdraio`): alcune venue espongono prezzi. Estrarre con pattern URL.

**Priority 3 — Spiagge.it**: Usare Playwright/Selenium per selezionare date e catturare prezzi dinamici. ~1.000 venue potenziali.

**Priority 4 — Siti propri con `/tariffe`, `/listino`, `/prezzi`**: Google dork `site:*.it "stabilimento balneare" "listino"` trova 500+ pagine accessibili.

**Priority 5 — PDF dorks**: ~100 PDF di listini trovati. Extraction con pdfplumber.
