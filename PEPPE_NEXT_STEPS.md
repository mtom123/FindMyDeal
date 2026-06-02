# Peppe — Next Steps (CEO, 2026-06-02)

## Priorità 1: Frontend Barbieri S1 (IMMEDIATO)

Il dataset è pronto: `data/barber_data.json` — 12.019 venue, 10.709 prezzate (89%).

### Cosa implementare

Segui esattamente `PROMPT_PEPPE_BARBIERI_S1.md` nel repo. Riepilogo chiave:

**Marker**: esagonali viola (come il beach ma colore diverso)  
**Color-tier**: verde/ambra/rosso rispetto alla mediana REGIONALE (non nazionale)  
**Sidebar filtri a 2 livelli**:
- Livello 1: Genere → `uomo` / `donna` / `bambino`
- Livello 2: Categoria servizio → `taglio_capelli` / `barba` / `colore` / `piega` / `trattamento`

**Dati da usare**: `barber_data.json` campo `services_normalized[]` con codici tipo `haircut_man`, `beard_trim`, ecc.

**UX pattern**: replica sidebar beach (già funzionante), adatta i label.

**Mediane regionali**: già pre-calcolate in `barber_data.json` sotto `region_stats.{region}.median_by_service`.

### Check iniziale

Prima di iniziare, apri `barber_s1_REPORT_PEPPE.md` nel repo — ha tutte le specifiche tecniche (415 righe, molto dettagliato).

---

## Priorità 2: Frontend Gym (dopo Supabase)

**Non fare niente fino a che CEO non dice GO.**

Il dataset gym è pronto (12.648 venue) ma ha 0 prezzi al momento.  
Quando avremo i primi prezzi da Supabase crowdsourcing, ti mando il brief.  
Per ora: preparati mentalmente per mappa palestre, filtri per tipo (palestra/yoga/crossfit/piscina), fascia prezzo mensile.

---

## Note tecniche

- Branch: lavora su `feat/barber-frontend`
- PR al CEO per review prima di merge su main
- Test su mobile (320px) e desktop (1440px)
- Il `barber_data.json` è 16MB — usa `fetch()` lazy o chunked loading se necessario
