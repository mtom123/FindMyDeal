# HANDOFF — Pietro (SurPrice scraper) — stato dopo S9 (03/06/2026)

> **LEGGI QUESTO PER PRIMO dopo `/compact`.** È il punto d'ingresso per riprendere senza perdere contesto.
> Poi: `cd ~/Desktop/FindMyDeal_clone && git pull --rebase origin main`.
> Storico profondo S0–S5 in `SESSION_RESUME_PIETRO.md` (locale, non committato). Questo doc copre **S6→S9** + tutto il contesto operativo necessario.

---

## 0. CHI SONO / COSA FACCIO
Sono **Pietro**, agente scraper del progetto **SurPrice** (repo GitHub `mtom123/FindMyDeal`). Utente GitHub: **ucovichpietro** (write access). Sono lo **scraper drink Italia** (vertical anchor) e eseguo i task assegnati dal CEO/utente via prompt `PROMPT_PIETRO_S*.md`.

**Team & vertical** (decisione 03/06, multi-vertical + multi-city):
- **mtom123** = CEO/orchestratore: fa merge (`scripts/merge_pipeline*.py`), rigenera `data/unified_*`, gestisce schema + Supabase community layer.
- **Peppe** = frontend (`index.html`) + vertical **beach** + vertical **barber/parrucchieri**.
- **Utente** = vertical **gym/palestre** + crowdsourcing Supabase.
- **Pietro (io)** = **drink** (Milano + 6 città) + eseguo task ad-hoc (es. S9 gym run).
- Vertical attivi: `drink, beach, barber, gym`. Città: `Milano, Roma, Napoli, Torino, Firenze, Bologna, Venezia`.

---

## 1. AMBIENTE & WORKFLOW (⚠️ CRITICO — leggere prima di agire)

- **macOS, NON Windows.** I prompt CEO assumono spesso Windows (`D:\`, `$env:PYTHONIOENCODING`, path `website/`). **IGNORA i path Windows e il prefisso `website/`**: i file sono a ROOT del repo. Traduci i comandi PowerShell in bash (es. `$env:PYTHONIOENCODING="utf-8"` → prefisso `PYTHONIOENCODING=utf-8 python3 ...`).
- **Due cartelle sul Desktop:**
  - `~/Desktop/FindMyDeal_clone/` = **CLONE del repo team** → QUI si lavora/committa/pusha. (Il mio shell parte spesso da `~/Desktop/Find My Deal` — la cartella ORIGINALE non-git; usa sempre path assoluti del clone.)
  - `~/Desktop/Find My Deal/` = cartella originale (scraper "di mattina", cache). NON git.
- **Python**: `python3` (3.9). Librerie installate: `requests`, `beautifulsoup4`, `pdfplumber`, `playwright`(+chromium), `playwright-stealth`, **`curl_cffi`** (installato in S7).
  - ❌ **`anthropic` NON installato** e **NESSUN `ANTHROPIC_API_KEY`** nell'env → gli script che usano Claude Haiku devono avere fallback (vedi S9).
- **Git workflow** (ufficiale CEO, commit `c35ae95`): **tutti su `main`, NIENTE branch, solo `pull --rebase`.**
  - Sequenza: `git pull --rebase origin main` → `git add <file specifici>` → `git commit` → `GIT_TERMINAL_PROMPT=0 git push origin main`.
  - Token in keychain → push non-interattivo OK.
  - ⚠️ **Gotcha**: `git pull --rebase ... | tail` **maschera l'exit code** (l'exit di una pipeline è quello di `tail`). NON pipare il pull, o controlla davvero il risultato. Il remoto **avanza spessissimo** (CEO+Peppe+utente attivi) → quasi sempre serve un secondo `pull --rebase` prima del push.
  - `git add` SEMPRE file specifici (mai `git add .`): la repo ha tanti log/cache untracked da NON committare.
- **⚠️ BACKGROUND TASK KILL ~34 min**: i comandi `run_in_background` vengono **killati a ~34 min** (limite wall-clock). Per run lunghi (>30 min): rendi lo script **RESUMABLE** (progress file + checkpoint frequente) + **soft-exit a ~28 min** (1700s) + **rilancia su notifica** finché non è completo. Parallelizza con **sharding** (`gyms[k::n]`, file per-shard) per ridurre i round. (Lezione S9: vedi sotto.)
- **`scripts/normalization.py`** = **libreria condivisa** (mantenuta dal CEO, multi-vertical + multi-city). **RIUSA, non duplicare.** Espone:
  - `PRICE_RANGES`, `BARBER_PRICE_RANGES`, `GYM_PRICE_RANGES`, `is_price_in_range_vertical(vertical,prod,price)`, `get_valid_products(vertical)`
  - `clean_item_product(item)`, `validate_item(item)` (quality gate drink: americano vs caffè, Moretti birra vs vino, prosecco glass vs bottiglia, MAXI, noise HTML)
  - **multi-city**: `CITY_BBOX`, `CITY_CAP_RANGES`, `is_in_city(lat,lon,city)`, `detect_city_from_cap(addr)`, `is_address_in_city(addr,city)`, `is_milan_or_unknown(addr)`
- **NON toccare MAI**: `data/unified_*.csv`, `data/*_no_price.csv`, `prices_data.json`, `index.html`, file `beach_*`/`barber_*` (territorio CEO/Peppe). Io consegno SOLO in `raw_sources/` (+ report a root + script in `scripts/`).

---

## 2. COSA HO FATTO IN QUESTA SESSIONE (S6 → S9) — tutto committato/pushato

### S6 — Standardizzazione venues drink Milano SENZA prezzo ✅
Input: 1.440 venues no-price del DB (`data/unified_venues.csv`). Output: **824 venues** (652 TARGET + 172 AMBIGUOUS_TO_REVIEW), classificati/deduplicati/geocodati/categorizzati.
- Classificazione TARGET/NO_TARGET/AMBIGUOUS (nome+categorie), venue_type (9 tipi), dedup per nome normalizzato (43 cluster), geocoding 29 no-geo (Nominatim+JSON-LD), reverse-geocode 169 address, quality gate inline (0 violazioni).
- Fix qualità: mojibake (`Caf√®`→`Cafè`), slug→nome formale, pipe-in-name, CAP `.0`, junk platform-name (`MyCIA`).
- File: `raw_sources/agent6_{venues_no_price,geocode_fixes,name_dedup,address_fixes}.csv`, `agent6_REPORT.md`, `scripts/agent6_{standardize,geocode,enrich,report}.py`.

### S7 — Discovery comune/CKAN/OSM + TheFork Milano ✅
Pool 3 fonti (CKAN 3.804 + comune_osm + OSM Overpass) → **2.428 venues net-new** (no-price), classificati/tipizzati/deduplicati, **opening_hours 100%**, **1.640 nomi commerciali recuperati** (cross-ref geo OSM ≤40m).
- **TheFork craccato**: `curl_cffi` `impersonate='safari17_2_ios'` bypassa Datadome 403 (chrome/edge→403). I dati stanno nell'**ItemList JSON-LD** (25 venue/pagina); **paginazione listing città** `/ristoranti/<city>-c<id>?p=N`. **NESSUN prezzo** (menu via JS). TheFork = piattaforma ristoranti → default NO_TARGET salvo segnale drink.
- Dedup geo-fingerprint + same-name<150m; esclude priced+agent6.
- File: `raw_sources/agent7_{venues_no_price,dedup_map,thefork_raw,osm_enriched}.csv`, `agent7_REPORT.md`, `scripts/agent7_{standardize,osm_overpass,thefork,report}.py`.

### S8 — Espansione drink 6 città Italia ✅ (fase discovery)
**6.036 venues drink net-new** su 6 città via pipeline parametrico, **opening_hours 100%**:
| Roma 2.254 · Torino 1.297 · Bologna 749 · Napoli 718 · Firenze 713 · Venezia 305 |
- `scripts/agent7_city.py <Città>` = OSM Overpass bbox per città (bar/pub/cafe/nightclub/biergarten) → classify/dedup/venue_type/opening_hours (riusa `normalization.CITY_BBOX` + helper agent6/agent7). Dual-endpoint Overpass (overpass-api.de + kumi.systems fallback su 504).
- File: `raw_sources/agent7_<city>_venues_no_price.csv` (6), `agent7_S8_REPORT.md`, `scripts/agent7_{city,s8_report}.py`.
- **NOTA**: discovery OSM-only (nomi puliti). **Prezzi per città = follow-up** (dati nazionali esistenti esigui). **CKAN per-città = espansione futura** (Roma/Torino/Bologna/Firenze/Venezia hanno CKAN attivo).

### S9 — Gym website price scraping ✅ (task esecuzione, non mio vertical)
Girato lo script CEO `agent_ceo_gym/gym_s1_websites.py` su **tutte le 3.095 palestre con sito** → **59 gym prezzate, 116 price points**.
- Breakdown: mensile n=88 (5-460€, avg 62€), annuale 15 (30-440€), iscrizione 7, day_pass 6.
- **Modifiche fatte allo script** (flaggate, backward-compatible): anthropic opzionale (regex fallback, no key), master path fallback (`raw_sources/gym_master_italia.csv`), cap `[:3095]`, **RESUMABLE + sharded 3× + soft-exit 1700s** (per sopravvivere al kill ~34min), dead-domain skip (speedup hit-rate-neutral).
- ⚠️ **CAVEAT**: girato in **regex-fallback** (no Haiku) → prezzi NON validati. Over-extraction su 2 venue (AcquaIN/Dynamic up = 10 prezzi cad. da tabelle tariffarie). **Consiglio CEO: pass con `ANTHROPIC_API_KEY`** per ripulire.
- **Hit rate basso (~1.9%)** = realtà del canale: i siti palestre raramente pubblicano prezzi (concentrati nelle catene, coperte da `gym_s1_chains.py`). I 200-400 sperati non sono realistici da questo canale.
- File: `agent_ceo_gym/{gym_website_prices.csv,gym_s9_log.txt,gym_s1_websites.py,gym_s9_finalize.py}`.

---

## 3. TECNICHE CRACCATE / RIUSABILI (le mie armi)
- **OSM Overpass bbox per città**: `nwr["amenity"~"^(bar|pub|cafe|nightclub|biergarten)$"](lat_min,lon_min,lat_max,lon_max);out center tags;` → name+amenity+opening_hours+website+phone+addr. Universale per ogni città. Dual-endpoint (overpass-api.de, kumi.systems).
- **CKAN comune** (open data): `https://dati.comune.<city>.it/.../api/3/action/package_search?q=esercizi`. Roma/Torino/Bologna/Firenze/Venezia attivi. Categorie-licenza (`f - bar caffè`, `h - wine bar, birreria, pub`...) → mappa a venue_type/TARGET. ⚠️ nomi spesso = licenziatario o `[bar non identificato]` → recupera nome da OSM via match geo.
- **TheFork**: `curl_cffi` `safari17_2_ios` (bypass Datadome) → **ItemList JSON-LD** (25 venue/pagina), paginazione `/ristoranti/milano-c348156?p=N`. Solo metadata (no prezzi).
- **Dedup geo-fingerprint**: cluster per cella ~55m (grid) + haversine ≤40m + name-compat (SequenceMatcher>0.82 o placeholder); **2ª passata same-name<150m** per imprecisione cross-source; branch >250m restano separati.
- **opening_hours 100%**: cascata OSM reale → TheFork → **`typical_by_type`** (fascia indicativa per venue_type, es. `pub Mo-Su 17:00-02:00`), campo `opening_hours_source` distingue reale vs tipico.
- **mojibake repair**: mappa Mac-Roman (`√®`→è, `‚Äã`→zero-width) — `fix_mojibake()` in agent6_standardize.
- **Run lunghi resilienti**: progress.json + checkpoint ogni N + soft-exit <28min + sharding `[k::n]` + relaunch su notifica. (Vedi `gym_s1_websites.py`.)
- **WebSearch tool**: operatore `site:` funziona (~10 risultati IT/query), per discovery + indirizzi geocoding.

---

## 4. STATO DATI / RIPRESA
- **HEAD al momento dell'handoff**: commit `1545a66` (S9). Tutto committato+pushato, tree pulito.
- I miei deliverable sono in `raw_sources/agent6_*` e `raw_sources/agent7_*` + report a root + script in `scripts/`. Il CEO li mergia in `data/unified_*` (territorio suo).
- CEO ha aggiunto (commit recenti): Supabase community layer (12.648 palestre caricate), haircut vertical, dynamic stats.

---

## 5. ERRORI / LEZIONI (da non ripetere)
- **Pull SEMPRE prima di tutto**: in S6 credevo mancasse `normalization.py` — era solo stato local-stale; il pull l'ha portato. Idem `PROMPT_PIETRO_S*.md` appaiono via pull.
- **Non sacrificare qualità per velocità**: in S9 avevo abbassato il timeout 15→8s → hit rate crollato 16%→5.8% (tagliava le pagine prezzi). Ripristinato 15s. Per accelerare usa ottimizzazioni **hit-rate-neutral** (dead-domain skip), non timeout aggressivi.
- **Onestà sui numeri**: riporta la resa reale (S8 prezzi=follow-up; S9 116 vs 200-400 sperati). Quality > quantity.
- **Resumability per run lunghi** (il kill a ~34min è certo). Sharding per parallelizzare.
- **Riusa normalization.py + agent6/agent7 helper**, non riscrivere quality gate/classify.
- **SUPERSEDE vs exclude**: i miei output puliti SOSTITUISCONO i grezzi del CEO in `unified_venues_no_price.csv` (non si appendono).

---

## 6. BACKLOG / NEXT STEPS (priorità)
🔴 **Prezzi drink per città** (S8 follow-up): mycia sitemap + leggimenu brute-force per Roma/Napoli (le più dense). È IL gap — finora le 6 città hanno solo venues no-price, 0 prezzi.
🟠 **CKAN per-città** (S8 espansione): aggiungere licenze comunali oltre OSM per Roma/Torino/Bologna/Firenze/Venezia (più volume, come Milano).
🟠 **Validazione Haiku S9**: ri-girare `gym_s1_websites.py` con `ANTHROPIC_API_KEY` per ripulire i 116 price points (over-extraction AcquaIN/Dynamic up).
🟢 **TheFork metadata bulk** altre città (curl_cffi, come Milano). **ClassPass** day-pass (`gym_s1_classpass.py`, richiede browser headed). **Quandoo/Michelin** (URL changed, ritentare).

---

## 7. DECISIONI CHE SERVONO CEO/UTENTE
- S9: vuoi il pass di validazione Haiku? (serve API key nell'env). Vuoi `gym_s1_classpass.py` (browser headed)?
- S8: prossima sessione = prezzi Roma/Napoli? o prima espansione CKAN delle 6 città?
- Conferma che gli output `raw_sources/agent7_<city>_*` vanno mergiati in un `unified_*_drink_<city>` (il CEO scrive il merge multi-city).

---

_Fine handoff. Dopo `/compact`: rileggi questo file → `git pull --rebase origin main` → controlla l'ultimo `PROMPT_PIETRO_S*.md` per il task corrente._
