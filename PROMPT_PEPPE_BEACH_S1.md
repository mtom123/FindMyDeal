# Prompt Peppe — Beach Club Price Intelligence S1 (02/06/2026)

> **CONTESTO**: SurPrice (ex FoodPrice) si estende oltre i drink di Milano. Primo nuovo vertical: **stabilimenti balneari italiani**. Costruiamo il database più completo di prezzi spiaggia in Italia.
>
> **Tua sessione**: PHASE 1 — Master list acquisition + PHASE 4 — Google index discovery (primo batch). PDF/listini reali extraction è S2.

---

## OBIETTIVO MISURABILE S1

| Metrica | Target |
|---|---|
| Venues master list (Italia coastal) | ≥ 3.000 |
| Venues con website associato | ≥ 800 |
| Venues con listino PDF/pagina prezzi trovato | ≥ 100 |
| Provider booking identificati | ≥ 5 dominanti |
| Listini estratti con prezzi normalizzati | ≥ 30 |

S1 = foundation. S2 (futura) estrarrà prezzi sistematicamente da ogni provider/PDF identificato in S1.

---

## SETUP

```bash
cd /percorso/SurPrice    # working dir
git clone https://github.com/mtom123/FindMyDeal.git . 2>/dev/null || git pull origin main

# Onboarding obbligatorio:
cat website/AGENTS.md
cat website/scripts/SCHEMA_AGENTI.md     # ⭐ schema CSV vincolante
```

Output directory: `website/raw_sources/`
Prefisso file: `beach_s1_*`

**REGOLA OPERATIVA #1**: Output CSV format DEVE rispettare lo schema unificato di SurPrice (campi e tipi). Vedi sezione "SCHEMA ADATTATO" più sotto.

---

## SCHEMA ADATTATO PER VERTICAL BEACH

Il merge_pipeline.py attuale supporta drink (22 prodotti). Per beach estendiamo SENZA rompere il drink. Useremo gli stessi due CSV (`*_venues.csv` e `*_menu_items.csv`) ma con nuovi `normalized_product` codes e nuovo `price_type`.

### Schema venues (`beach_s1_venues.csv`) — IDENTICO al drink schema con aggiunte

```
source_platform,source_venue_id,venue_name,venue_url,address,city,province,region,
postal_code,latitude,longitude,categories,price_tier,rating,rating_count,
phone,website,opening_hours,has_menu,menu_url,extraction_status,retrieved_at,
google_maps_url,instagram,facebook,booking_provider,vertical
```

Campi aggiunti vs schema standard (puoi inserirli, il merge li ignora se non presenti):
- `province` (es. "Rimini", "Latina")
- `region` (es. "Emilia-Romagna", "Lazio")
- `postal_code`
- `google_maps_url`
- `instagram`, `facebook`
- `booking_provider` (es. "spiagge.it", "bagnix", "ombrellobeach"...)
- `vertical` = **`beach`** ← marker categoria. Sempre `beach` in questo file.

**city** = comune (non solo "Milano"). Per i drink era sempre Milano, qui è dinamico.

### Schema menu_items (`beach_s1_menu_items.csv`) — riusa schema drink

```
source_platform,source_venue_id,venue_name,venue_url,menu_section,item_name,
item_description,raw_price,normalized_price_eur,currency,price_type,item_type,
normalized_product,confidence,allergens,retrieved_at,source_url,
season,validity_start,validity_end,vertical
```

Campi aggiunti:
- `season` (es. "summer_2026", "winter_2025")
- `validity_start`, `validity_end` (ISO date)
- `vertical` = **`beach`**

### Nuovi `normalized_product` codes per BEACH

Usare ESATTAMENTE questi codici (lowercase, underscore):

| Codice | Cosa include |
|---|---|
| `beach_umbrella_standard` | Ombrellone fila standard / non prima fila |
| `beach_umbrella_first_row` | Ombrellone prima fila |
| `beach_umbrella_premium` | Ombrellone VIP / area dedicata |
| `beach_sunbed` | Lettino singolo |
| `beach_chair` | Sedia / sdraio |
| `beach_cabin_day` | Cabina giornaliera |
| `beach_cabin_season` | Cabina stagionale (abbonamento) |
| `beach_set_2lettini_ombrellone` | Pacchetto 2 lettini + ombrellone (config tipica) |
| `beach_set_1lettino_ombrellone` | Pacchetto 1 lettino + ombrellone |
| `beach_parking` | Parcheggio (giornaliero, se a pagamento) |
| `beach_shower` | Doccia calda |
| `beach_subscription_week` | Abbonamento settimanale |
| `beach_subscription_month` | Abbonamento mensile |
| `beach_subscription_season` | Abbonamento stagionale |
| `beach_entry_fee` | Ingresso giornaliero (dove applicabile) |
| `beach_minimum_spend` | Spesa minima richiesta |

Se non sei sicuro del codice → lascia `normalized_product` vuoto. **MAI inventare** un codice non in elenco.

### Nuovi `price_type` per beach

| Valore | Significato |
|---|---|
| `per_day_weekday` | Prezzo giornaliero giorni feriali |
| `per_day_weekend` | Prezzo giornaliero weekend/festivi |
| `per_day` | Prezzo giornaliero generico (se non distinto) |
| `per_half_day` | Mezza giornata (mattina o pomeriggio) |
| `per_week` | Settimana |
| `per_month` | Mese |
| `per_season` | Stagione completa |
| `one_off` | Servizio una tantum (doccia, parcheggio singolo) |

---

## PHASE 1 — MASTER LIST ACQUISITION

### Step 1.1 — Overpass API OSM (foundation)

OSM ha tutta la coastline italiana mappata. Query Overpass per recuperare tutte le entità "beach club/lido/stabilimento":

```python
import requests, json

OVERPASS = "https://overpass-api.de/api/interpreter"

query = """
[out:json][timeout:300];
area["ISO3166-1"="IT"]->.italy;
(
  node["tourism"="beach_resort"](area.italy);
  way["tourism"="beach_resort"](area.italy);
  node["leisure"="beach_resort"](area.italy);
  way["leisure"="beach_resort"](area.italy);
  node["amenity"="beach_club"](area.italy);
  way["amenity"="beach_club"](area.italy);
  node["name"~"stabilimento|lido|bagni|bagno",i]["natural"!="beach"](area.italy);
  way["name"~"stabilimento|lido|bagni|bagno",i]["natural"!="beach"](area.italy);
);
out center tags;
"""

r = requests.post(OVERPASS, data={'data': query}, timeout=600)
data = r.json()
print(f"OSM elements: {len(data['elements'])}")
```

Per ogni element: `tags['name']`, `lat`/`lon` (o `center.lat`/`center.lon` per ways), `tags.get('addr:city')`, `tags.get('addr:postcode')`, `tags.get('website')`, `tags.get('phone')`.

**Yield atteso: 1.500-3.000 venues OSM**.

### Step 1.2 — Aggregator websites (extension)

Siti aggregatori che hanno cataloghi balneari completi:

- `spiagge.it` (booking provider + directory)
- `bagnix.com` (provider)
- `solomare.it`
- `prenotaspiaggia.it`
- `cleartrip.com/it` (parziale)
- `tripadvisor.it/Attractions-...-Beaches` (faticoso ma copre)
- Siti tourist board regionali: emiliaromagnaturismo.it, regione.toscana.it/turismo, etc.

Per ognuno: discovery via `site:dominio.it stabilimento` o `site:dominio.it lido` via Startpage/Mojeek (NO Google diretto — captcha).

### Step 1.3 — Tourism directories regionali

Per ogni regione costiera (Liguria, Toscana, Lazio, Campania, Calabria, Sicilia, Puglia, Marche, Abruzzo, Molise, Emilia-Romagna, Veneto, Friuli-Venezia Giulia, Sardegna):
- Sito turistico ufficiale regione
- Lista comuni costieri → discovery venues per comune

**Lo step 1.3 può essere lasciato come backlog se i tempi stringono**: OSM + aggregator probabilmente coprono già 80% del mercato.

### Step 1.4 — Dedup + merge

Same logic del drink merge:
- Match per coordinate (≤50m → stessa venue)
- Fallback su nome similarity (>0.85) + stessa città
- Preserve `_sources` array per provenance

Output:
- `website/raw_sources/beach_s1_venues.csv` (target: 3.000+ righe)
- Field `vertical=beach` su TUTTE le righe

---

## PHASE 3 — BOOKING PROVIDER DISCOVERY (CRITICO)

I prezzi vivono spesso **fuori** dal sito ufficiale del balneare. Sono dentro il provider booking. Identifica i 5-10 provider dominanti.

### Workflow

Per ogni venue con website nel master list:
1. Visita homepage
2. Cerca link "Prenota" / "Booking" / "Riserva"
3. Salva il dominio destinazione
4. Aggrega → conta occorrenze per dominio

```python
from urllib.parse import urlparse
from collections import Counter

provider_count = Counter()
for venue in venues_with_website:
    html = fetch(venue['website'])
    soup = BeautifulSoup(html, 'lxml')
    for a in soup.find_all('a', href=True):
        text = a.get_text().lower()
        if any(kw in text for kw in ['prenota','prenotazione','book','riserva','reservation','acquista']):
            href = a['href']
            domain = urlparse(href).netloc
            if domain and domain != urlparse(venue['website']).netloc:
                provider_count[domain] += 1
```

**Yield atteso**: top 5-10 provider rappresentano probabilmente 60-80% del mercato.

### Per ogni provider identificato

Annota in un report markdown (`beach_s1_PROVIDERS.md`):

```markdown
## Provider: spiagge.it
- Venues che lo usano: 247
- URL pattern: https://spiagge.it/stabilimento/{slug}
- Pricing pubblico: SÌ / NO
- Indicizzato Google: SÌ / NO
- Anti-bot: niente / Cloudflare / Datadome
- Scraping feasibility: ALTA / MEDIA / BASSA
- Note: ...
```

Aggiorna `booking_provider` field nel CSV venues per ogni venue mappata.

---

## PHASE 4 — GOOGLE INDEX DISCOVERY

Cerca PDF listini e pagine prezzi via dorks. Usa Startpage (NO Google diretto).

### Dorks da provare

```
"listino" "stabilimento" filetype:pdf 2026
"listino prezzi" stabilimento balneare pdf
"prezzi" ombrellone lettino pdf 2026
"tariffe" stabilimento "prima fila"
"abbonamento stagionale" lido pdf
"listino" bagno spiaggia pdf 2026
"prima fila" ombrellone listino
site:bagnix.com prezzi
site:spiagge.it stabilimento
```

Per ogni risultato:
- Salva URL
- Se PDF → scarica + parse con pdfplumber
- Se HTML → fetch + parse
- Extract prezzi con pattern simili al drink scraping (`€ X.XX`, `X,00 €`)

**Yield atteso: 100-300 PDF/pagine prezzi trovati. Estraibili sistematicamente in S2.**

---

## PHASE 5 — FIRST BATCH PRICE EXTRACTION (sample 30 venues)

In S1 non serve estrarre TUTTI i prezzi. Estrai **30 venues di esempio** per validare lo schema:

- 10 venues da PDF (provider listini ufficiali)
- 10 venues da siti propri con pagina "Listino"
- 10 venues da provider booking (se prezzi pubblici)

Output → `beach_s1_menu_items.csv` con ~150-300 righe.

Lo scopo di S1 è **provare che lo schema regge** e che possiamo aggregare prezzi. S2 sarà extraction sistematica.

---

## QUALITY GATES (NON NEGOZIABILI)

Per ogni VENUE prima di scrivere:
1. **Deve avere `latitude`+`longitude` o `address` completo** (no venue fantasma)
2. **Nome venue ≠ titolo pagina HTML** (es. niente "Home", "Stabilimento Balneare", "Listino")
3. **Province e region devono coincidere geograficamente** (no Rimini con region "Lazio")
4. **vertical = "beach"** sempre

Per ogni ITEM prima di scrivere:
1. **`normalized_price_eur` deve essere parseable** (>0, <500€ per item beach standard; abbonamento stagionale può arrivare a 5000€)
2. **`normalized_product` deve essere in vocabolario chiuso** (vedi tabella sopra). Se non sicuro → vuoto.
3. **`price_type` deve essere in vocabolario chiuso** (per_day/per_week/etc).
4. **Niente URL immagine** in `source_url` (.jpg/.png/.webp)
5. **`item_name` < 200 char**
6. **NO duplicati interni** (stesso venue + product + price + price_type)
7. **`season`/`validity_start`** se desumibile dal PDF (es. "Estate 2026" → season="summer_2026")

---

## RATE LIMITS

- Overpass API: 1 query grossa, no rate (è pensato per bulk)
- Startpage: 5s tra query, max 20 query consecutive → poi rotate
- PDF download: 1s tra GET, max 200 PDF/sessione
- Generic websites: 2s tra GET
- HTTP 429 → sleep 120s + retry
- HTTP 403 → skip

---

## DELIVERABLES S1

| File | Descrizione |
|---|---|
| `website/raw_sources/beach_s1_venues.csv` | Master list venues (3.000+ righe) |
| `website/raw_sources/beach_s1_menu_items.csv` | 30 sample venues + prezzi (~150-300 righe) |
| `website/beach_s1_PROVIDERS.md` | Report provider booking identificati |
| `website/beach_s1_REPORT.md` | Sintesi metriche, gaps, prossimi step S2 |

---

## CONSEGNA

```bash
cd ~/percorso/SurPrice_clone
git pull --rebase origin main
git add website/raw_sources/beach_s1_*.csv
git add website/beach_s1_*.md
git commit -m "data: beach S1 — N venues, M items, K providers identificati"
git push origin main
```

Avvisa il CEO con report sintetico.

---

## ARCHITECTURAL PRINCIPLES (da rispettare)

1. **Preserve provenance**: ogni valore estratto deve avere `source_url` + `retrieved_at` + `confidence`.
2. **Never overwrite raw data**: tieni `raw_price` originale + `normalized_price_eur` calcolato.
3. **Track coverage**: nel REPORT.md, breakdown per regione (totale stimato vs collected vs prezzi noti).
4. **No invention**: se non sai un campo → vuoto. Mai inventare.
5. **Geo accuracy**: meglio `latitude`/`longitude` vuoti che sbagliati.

---

## ERRORI DA NON RIPETERE (lesson learned dai drink)

1. ❌ **Brute-force senza filtro geo**: una sessione drink ha pescato 7.932 items di tutta Italia che andavano filtrati a Milano. Per beach il filtro è "Italia coast" (non sbagli quasi mai), ma su provincia/regione fai attenzione.
2. ❌ **Image URLs nel `source_url`**: skippa SEMPRE `.jpg/.png/.webp`.
3. ❌ **Nome venue = titolo HTML**: se la pagina si chiama "Listino Prezzi" non chiamare la venue "Listino Prezzi".
4. ❌ **PDF parser double-letter** (vedi bug Mulligan's): se vedi "LLEETTTTIINNOO" applica regex `([A-Z])\1` → `\1`.
5. ❌ **Confidence inflation**: se estratto da regex su HTML messy → `medium`. Solo da PDF strutturato o pagina "Listino" ufficiale → `high`.

---

## CHE COSA NON FARE IN S1

- ❌ Non estrarre prezzi da TUTTE le venues (è S2)
- ❌ Non costruire UI/frontend ora (è S3)
- ❌ Non toccare i file drink esistenti (`data/`, `prices_data.json`, `index.html`)
- ❌ Non aggiungere venues senza geo o address verificabile

---

Buona sessione Peppe. **Foundation matters more than completeness in S1.**
