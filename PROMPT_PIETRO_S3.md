# Prompt Pietro — Sessione 3: Maximum Yield (01/06/2026)

> **Copia questo file nella tua sessione Claude Code e lasciala girare per ore.**
> Questo è un prompt autonomo. Leggi tutto prima di eseguire qualsiasi step.

---

## CHI SEI E CONTESTO

Sei Pietro, l'agente scraper di FoodPrice Milano.

**Sessioni precedenti:**
- S1: 47 venues direct_website + 4 PDF + 4 eatbu
- S2: geocoding leggimenu (29 venues precise), TheFork BLOCCATO
- CEO ha già fatto merge: 829 price points, 146 venues sulla mappa, 5.361 items

**Stato attuale che devi conoscere:**
- leggimenu: 35 venues (pulite, geocodate), 4.214 items ✅
- TheFork: Datadome HTTP 403 anche con Playwright stealth headless. **Non ritentare da IP datacenter.**
- 22 venues sono ancora stackate su Milano centro (fallback geocoding) — sono OK, non è un errore tuo
- 79 venues con website non ancora estratto (lista esatta in Step 1)
- leggimenu ha sicuramente più venues di quelle 35 — lo slug brute-force non è stato fatto (Step 2)

---

## SETUP (PRIMA DI TUTTO)

```bash
# Se sei su disco D (spazio):
cd D:\FindMyDeal
git clone https://github.com/mtom123/FindMyDeal.git . 2>/dev/null || git pull origin main

# Leggi in quest'ordine (5 minuti):
cat website/AGENTS_STATE.md      # stato DB — NON duplicare
cat website/scripts/SCHEMA_AGENTI.md  # formato CSV obbligatorio

# Setup Python (su D: se C: è piena):
D:\python-embed\python.exe -m pip install requests beautifulsoup4 lxml tqdm pdfplumber playwright playwright-stealth --quiet
D:\python-embed\python.exe -m playwright install chromium
```

**Working directory per output:** `D:\FindMyDeal\raw_sources\` (oppure usa il clone della repo)

---

## STEP 1 — Direct scraping 79 venues OSM note (PRIORITÀ 1)

**Perché:** Sono bar Milano verificati, geocodati, con website. Hit rate atteso ~15-25%
(più alto del 6.7% del batch random, perché questa lista è già filtrata: sono bar con sito proprio).

**La lista completa (79 venues non ancora nel DB prezzi):**

```python
TARGET_VENUES = [
    {"name": "Radetzky Café",       "website": "https://www.radetzky.it/",            "lat": 45.4764, "lon": 9.1773},
    {"name": "Scott Duff",          "website": "https://scottduff.it/",                "lat": 45.4702, "lon": 9.2010},
    {"name": "Mulligan's",          "website": "https://mulliganspub.it/",             "lat": 45.4641, "lon": 9.1851},
    {"name": "Blues Bikers Pub",    "website": "http://www.bluesbikerspub.com",        "lat": 45.4599, "lon": 9.1762},
    {"name": "55 Milano",           "website": "https://www.55milano.com/",            "lat": 45.4587, "lon": 9.1717},
    {"name": "Il Gattopardo",       "website": "https://www.ilgattopardomilano.com/",  "lat": 45.4731, "lon": 9.1761},
    {"name": "DrinKasi",            "website": "https://drinkasi.webnode.it",          "lat": 45.4501, "lon": 9.2301},
    {"name": "Living",              "website": "https://www.livingmilano.com/",        "lat": 45.4642, "lon": 9.1853},
    {"name": "Shatar Pub",          "website": "http://www.shatarpub.com",             "lat": 45.4611, "lon": 9.2187},
    {"name": "Lost in Town",        "website": "http://www.lostintown-milano.com/",    "lat": 45.4688, "lon": 9.1597},
    {"name": "Bar Bianco",          "website": "https://www.barbiancomilano.com/",     "lat": 45.4741, "lon": 9.1591},
    {"name": "Banshee",             "website": "http://www.banshee.pub/",              "lat": 45.4756, "lon": 9.2017},
    {"name": "Karma",               "website": "http://www.karmamilano.it",            "lat": 45.4668, "lon": 9.1751},
    {"name": "Gate",                "website": "https://www.gatemilano.it/",           "lat": 45.4821, "lon": 9.1812},
    {"name": "11 Clubroom",         "website": "https://www.11milano.it/",             "lat": 45.4638, "lon": 9.1882},
    {"name": "Caffè Letterario",    "website": "https://www.caffeletterariomilano.it/","lat": 45.4557, "lon": 9.1777},
    {"name": "Cantine Isola",       "website": "https://www.cantineisola.it/",         "lat": 45.4831, "lon": 9.1817},
    {"name": "Mag Café",            "website": "https://www.mag-cafe.it/",             "lat": 45.4528, "lon": 9.1720},
    {"name": "Rita",                "website": "https://www.ritamilano.it/",           "lat": 45.4513, "lon": 9.1668},
    {"name": "Retrogroove",         "website": "https://www.retrogroove.it/",          "lat": 45.4618, "lon": 9.2148},
    {"name": "El Brellin",          "website": "https://www.elbrellin.com/",           "lat": 45.4521, "lon": 9.1628},
    {"name": "The Spirit",          "website": "https://www.thespiritmilano.it/",      "lat": 45.4891, "lon": 9.1741},
    {"name": "Cuore",               "website": "https://www.cuoremilano.it/",          "lat": 45.4538, "lon": 9.1718},
    {"name": "Baladin Milano",      "website": "https://www.baladin.it/",              "lat": 45.4641, "lon": 9.1883},
    {"name": "Birrificio Lambrate", "website": "https://www.birrificiolambrate.com/",  "lat": 45.4831, "lon": 9.2541},
    {"name": "Birrificio Artigianale Italiano", "website": "https://www.bai.it/",     "lat": 45.4711, "lon": 9.1801},
    {"name": "Ostello Bello",       "website": "https://www.ostellobello.com/",        "lat": 45.4621, "lon": 9.1778},
    {"name": "Upcycle",             "website": "https://www.upcyclemilano.it/",        "lat": 45.4588, "lon": 9.1762},
    {"name": "The Doping Club",     "website": "https://www.thedopingclub.it/",        "lat": 45.4782, "lon": 9.1992},
    {"name": "Spazio Oberdan",      "website": "https://www.spaziooberdanmilano.it/",  "lat": 45.4751, "lon": 9.2018},
]

# Nota: questa è la lista PARZIALE mostrata dal CEO. Recupera la lista COMPLETA con:
import csv
already_priced = set()
with open('D:/FindMyDeal/website/data/unified_prices.csv', encoding='utf-8-sig') as f:
    for row in csv.DictReader(f):
        already_priced.add(row['venue_name'].lower().strip())

osm_targets = []
with open('D:/FindMyDeal/website/raw_sources/comune_osm_venues.csv', encoding='utf-8-sig') as f:
    for row in csv.DictReader(f):
        ws = row.get('website','').strip()
        name = row.get('venue_name','').strip()
        if ws and name and name.lower() not in already_priced:
            if 'instagram' not in ws and 'facebook' not in ws and 'tripadvisor' not in ws:
                osm_targets.append(row)

print(f"Target venues: {len(osm_targets)}")
```

**Algoritmo per ogni venue:**

```python
import requests
from bs4 import BeautifulSoup
import re, time

PRICE_RE = re.compile(r'(?<!\d)(\d{1,2}[,.]?\d{0,2})\s*€|€\s*(\d{1,2}[,.]?\d{0,2})', re.I)
DRINK_KEYWORDS = re.compile(
    r'\b(spritz|negroni|americano cocktail|gin\s*tonic|mojito|moscow\s*mule|margarita|'
    r'daiquiri|manhattan|hugo|aperol|campari|moretti|heineken|peroni|nastro\s*azzurro|'
    r'birra\s*(spina|alla\s*spina)|calice|prosecco|craft\s*beer|ipa|stout|lager|'
    r'caff[eè]|cappuccino|acqua|coca\s*cola|fanta)\b', re.I)

MENU_PATHS = ['/menu', '/drink', '/drinks', '/cocktail', '/cocktails', '/carta',
              '/listino', '/beverage', '/bere', '/birra', '/birre', '/carta-dei-cocktail',
              '/drink-list', '/food-and-drinks']

def try_extract_menu(venue_name, base_url):
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124'}
    results = []
    
    # Prova homepage + path-probing
    urls_to_try = [base_url] + [base_url.rstrip('/') + p for p in MENU_PATHS]
    
    for url in urls_to_try:
        try:
            r = requests.get(url, headers=headers, timeout=8, allow_redirects=True)
            if r.status_code != 200:
                continue
            
            # Check PDF link nella pagina
            soup = BeautifulSoup(r.text, 'lxml')
            pdf_links = [a['href'] for a in soup.find_all('a', href=True) 
                        if a['href'].lower().endswith('.pdf')]
            if pdf_links:
                print(f"  PDF trovato: {pdf_links[0]}")
                # Torna il link PDF per il parsing separato
                results.append({'type': 'pdf', 'url': pdf_links[0], 'venue': venue_name})
            
            # Cerca prezzi nel testo
            text = soup.get_text(separator='\n')
            lines = [l.strip() for l in text.split('\n') if l.strip()]
            
            for i, line in enumerate(lines):
                prices = PRICE_RE.findall(line)
                if not prices:
                    continue
                # Cerca keyword drink nella stessa riga o ±2 righe
                context = ' '.join(lines[max(0,i-2):i+3])
                if not DRINK_KEYWORDS.search(context):
                    continue
                
                for match in prices:
                    price_str = match[0] or match[1]
                    try:
                        price = float(price_str.replace(',', '.'))
                    except:
                        continue
                    if price < 0.5 or price > 60:
                        continue
                    
                    results.append({
                        'type': 'item',
                        'venue': venue_name,
                        'url': url,
                        'line': line[:100],
                        'price': price
                    })
            
            if results:
                break  # ha trovato qualcosa, non serve andare oltre
                
        except Exception as e:
            pass
        time.sleep(2)
    
    return results
```

**Normalizzazione prodotto:**
```python
def normalize_product(item_name_or_line):
    t = item_name_or_line.lower()
    if re.search(r'\baperol\b|\bcampari\s*spritz\b|\bhugh?\s*spritz\b|spritz', t): return 'spritz'
    if 'negroni' in t: return 'negroni'
    if re.search(r'\bamericano\b', t) and not re.search(r'caff|caffè|whisky|rovere', t): return 'americano'
    if re.search(r'gin\s*tonic|g\s*&\s*t\b', t): return 'gin_tonic'
    if 'mojito' in t: return 'mojito'
    if re.search(r'moscow\s*mule', t): return 'moscow_mule'
    if 'margarita' in t: return 'margarita'
    if 'daiquiri' in t: return 'daiquiri'
    if 'manhattan' in t: return 'manhattan'
    if re.search(r'moretti', t): return 'beer_moretti'
    if re.search(r'heineken', t): return 'beer_heineken'
    if re.search(r'peroni|nastro\s*azzurro', t): return 'beer_peroni'
    if re.search(r'birra\s*(spina|alla\s*spina).{0,20}(pic|small|0[.,]?[23]|33)', t): return 'beer_draft_small'
    if re.search(r'birra\s*(spina|alla\s*spina).{0,20}(med|0[.,]?[45]|50)', t): return 'beer_draft_medium'
    if re.search(r'birra\s*bottiglia|bottiglia\s*birra', t): return 'beer_bottle'
    if re.search(r'calice\s*di?\s*vino|vino\s*al\s*calice', t): return 'wine_glass'
    if re.search(r'prosecco|flute', t): return 'prosecco_glass'
    if re.search(r'caff[eè]\s*espresso|\bespresso\b|\bcaffè\b(?!\s*americano|\s*corretto)', t): return 'espresso'
    if 'cappuccino' in t: return 'cappuccino'
    if re.search(r'coca\s*cola|fanta|sprite|bibita', t): return 'soft_drink'
    if re.search(r'\bacqua\b', t): return 'water'
    return ''  # lascia vuoto se non sicuro
```

**Output:** `raw_sources/osm_direct2_venues.csv` + `raw_sources/osm_direct2_menu_items.csv`
**source_platform:** `direct_website`

---

## STEP 2 — leggimenu slug brute-force (PRIORITÀ 2, ALTO VOLUME ATTESO)

**Perché:** leggimenu ha URL della forma `https://www.leggimenu.it/menu/{slug}`.
I slug sono spesso il nome del bar normalizzato (lowercase, no spazi). Abbiamo 850+ nomi
di bar Milano (da scraper_venues.csv). Hit rate atteso 5-15% = **40-120 nuove venues con menu**.
leggimenu ha 100-200 item per venue = **4.000-24.000 nuovi items potenziali**.
QUESTO È IL GAME CHANGER.

**Come normalizzare il nome in slug:**

```python
import re, unicodedata

def to_slugs(name):
    """Genera lista di slug candidati da un nome venue."""
    name = name.lower().strip()
    
    # Rimuovi accenti
    name_ascii = ''.join(c for c in unicodedata.normalize('NFD', name)
                         if unicodedata.category(c) != 'Mn')
    
    slugs = []
    
    # Variante 1: tutto attaccato, solo alfanumerici
    slug1 = re.sub(r'[^a-z0-9]', '', name_ascii)
    if slug1 and len(slug1) > 3:
        slugs.append(slug1)
    
    # Variante 2: con trattini
    slug2 = re.sub(r'[^a-z0-9]+', '-', name_ascii).strip('-')
    if slug2 and slug2 != slug1:
        slugs.append(slug2)
    
    # Variante 3: rimuovi parole comuni (bar, pub, caffe, il, la, lo, the)
    clean = re.sub(r'\b(bar|pub|caffe|caffè|il|la|lo|i|gli|le|the|in|al|alla|del|della|di|da)\b', '', name_ascii)
    clean = re.sub(r'\s+', '', clean.strip())
    if clean and len(clean) > 3 and clean not in slugs:
        slugs.append(clean)
    
    # Variante 4: nome + "milano"
    if 'milano' not in name_ascii:
        slugs.append(re.sub(r'[^a-z0-9]', '', name_ascii) + 'milano')
    
    return list(dict.fromkeys(slugs))  # dedup mantenendo ordine

# Test:
print(to_slugs("Spritz Navigli Milano"))
# → ['spritznavoglimilano', 'spritz-navigli-milano', 'spritznavoglimilano']
print(to_slugs("Bar Basso"))
# → ['barbasso', 'bar-basso', 'basso', 'bassomilano']
```

**Loop principale:**

```python
import requests, csv, time, json
from bs4 import BeautifulSoup

LEGGIMENU_BASE = "https://www.leggimenu.it/menu/"
HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/124'}

# Carica nomi già nel DB leggimenu (non rifare)
existing_slugs = set()
with open('website/raw_sources/leggimenu_venues.csv', encoding='utf-8-sig') as f:
    for row in csv.DictReader(f):
        # Estrai slug dall'URL: https://www.leggimenu.it/menu/SLUG
        url = row.get('venue_url','')
        slug = url.split('/menu/')[-1].strip('/')
        if slug:
            existing_slugs.add(slug)

# Carica tutti i nomi bar dai vari raw_sources
candidate_names = set()
for fname in ['raw_sources/scraper_venues.csv', 'raw_sources/comune_osm_venues.csv',
              'raw_sources/direct_venues.csv']:
    try:
        with open(f'website/{fname}', encoding='utf-8-sig') as f:
            for row in csv.DictReader(f):
                name = row.get('venue_name','').strip()
                if name:
                    candidate_names.add(name)
    except: pass

print(f"Candidati: {len(candidate_names)} nomi")

# Genera tutti gli slug
all_slugs = {}  # slug → nome_originale
for name in candidate_names:
    for slug in to_slugs(name):
        if slug not in existing_slugs and slug not in all_slugs:
            all_slugs[slug] = name

print(f"Slug candidati: {len(all_slugs)}")

# Prova ogni slug
new_venues = []
new_items = []
checked = 0

for slug, original_name in all_slugs.items():
    url = LEGGIMENU_BASE + slug
    try:
        r = requests.get(url, headers=HEADERS, timeout=8, allow_redirects=True)
        checked += 1
        
        if r.status_code == 404:
            pass  # normale, continua
        elif r.status_code == 200 and 'leggimenu.it/menu/' in r.url:
            # Trovato! Ora estrai i dati come leggimenu_scraper.py
            soup = BeautifulSoup(r.text, 'lxml')
            
            # Nome venue reale dalla pagina (non il nostro nome candidato)
            venue_name_tag = soup.find('h1') or soup.find('title')
            real_name = venue_name_tag.get_text(strip=True).split('|')[0].strip() if venue_name_tag else original_name
            
            # JSON-LD per indirizzo e geo
            lat, lon, address = '', '', ''
            for script in soup.find_all('script', type='application/ld+json'):
                try:
                    data = json.loads(script.string)
                    if isinstance(data, list): data = data[0]
                    if isinstance(data, dict):
                        addr = data.get('address', {})
                        if isinstance(addr, dict):
                            address = ', '.join(filter(None, [
                                addr.get('streetAddress',''),
                                addr.get('addressLocality',''),
                                addr.get('postalCode','')
                            ]))
                        geo = data.get('geo', {})
                        if isinstance(geo, dict):
                            lat = str(geo.get('latitude',''))
                            lon = str(geo.get('longitude',''))
                except: pass
            
            # Verifica che sia Milano (address o slug content)
            if address and any(x in address.lower() for x in ['torino','palermo','roma','napoli',
                                                                'siena','parma','ferrara','lecce','trento']):
                print(f"  NON MILAN skip: {real_name} - {address}")
                time.sleep(1.5)
                continue
            
            print(f"  HIT: {real_name} ({slug}) - {address}")
            
            # Estrai items — cerca elementi con data-price (stile leggimenu)
            items_found = []
            
            # Pattern 1: elementi con classe lmcart-add o simili con data-price
            for el in soup.find_all(attrs={'data-price': True}):
                price_raw = el.get('data-price','')
                name_el = el.get('data-name','') or el.get('data-productname','')
                section_el = ''
                # risali al section header
                parent = el.parent
                for _ in range(5):
                    if parent is None: break
                    h = parent.find(['h2','h3','h4'])
                    if h:
                        section_el = h.get_text(strip=True)
                        break
                    parent = parent.parent
                
                try:
                    price = float(str(price_raw).replace(',','.'))
                except: continue
                if price <= 0 or price > 100: continue
                
                items_found.append({
                    'item_name': name_el or 'unknown',
                    'raw_price': price_raw,
                    'normalized_price_eur': price,
                    'menu_section': section_el
                })
            
            # Pattern 2: cerca testo con prezzi in formato "Nome €X.XX"
            if not items_found:
                text = soup.get_text(separator='\n')
                for line in text.split('\n'):
                    line = line.strip()
                    prices = re.findall(r'€\s*(\d+[,.]?\d{0,2})', line)
                    if prices and len(line) < 100:
                        try:
                            price = float(prices[0].replace(',','.'))
                            if 0.5 <= price <= 60:
                                item_text = re.sub(r'€.*', '', line).strip()
                                if len(item_text) > 2:
                                    items_found.append({
                                        'item_name': item_text[:80],
                                        'raw_price': f"€{prices[0]}",
                                        'normalized_price_eur': price,
                                        'menu_section': ''
                                    })
                        except: pass
            
            if not items_found:
                print(f"    -> venue trovata ma 0 items estraibili (menu non strutturato?)")
            else:
                print(f"    -> {len(items_found)} items trovati")
            
            # Aggiungi venue
            new_venues.append({
                'source_platform': 'leggimenu',
                'source_venue_id': slug,
                'venue_name': real_name,
                'venue_url': url,
                'address': address,
                'city': 'Milano',
                'latitude': lat or '45.4642',
                'longitude': lon or '9.1900',
                'has_menu': 'True' if items_found else 'False',
                'menu_url': url,
                'extraction_status': 'ok' if items_found else 'no_menu',
                'retrieved_at': datetime.utcnow().isoformat() + 'Z',
                'categories': '', 'price_tier': '', 'rating': '',
                'rating_count': '', 'phone': '', 'website': '', 'opening_hours': ''
            })
            
            # Aggiungi items
            for item in items_found:
                prod = normalize_product(item['item_name'])
                new_items.append({
                    'source_platform': 'leggimenu',
                    'source_venue_id': slug,
                    'venue_name': real_name,
                    'venue_url': url,
                    'menu_section': item['menu_section'],
                    'item_name': item['item_name'],
                    'item_description': '',
                    'raw_price': item['raw_price'],
                    'normalized_price_eur': item['normalized_price_eur'],
                    'currency': 'EUR',
                    'price_type': 'menu',
                    'item_type': 'drink',
                    'normalized_product': prod,
                    'confidence': 'high' if prod else 'medium',
                    'allergens': '',
                    'retrieved_at': datetime.utcnow().isoformat() + 'Z',
                    'source_url': url
                })
        elif r.status_code == 429:
            print("  Rate limit! Sleep 120s")
            time.sleep(120)
            continue
        
    except Exception as e:
        print(f"  ERR {slug}: {e}")
    
    time.sleep(1.5)  # OBBLIGATORIO — Nominatim style per leggimenu
    
    # Salva ogni 50 venue per sicurezza
    if checked % 50 == 0:
        save_progress(new_venues, new_items)
        print(f"[{checked}] Progress saved. Hit: {len(new_venues)} venues, {len(new_items)} items")
```

**Output:** APPEND a `raw_sources/leggimenu_venues.csv` + `raw_sources/leggimenu_menu_items.csv`
(NON sovrascrivere! Usa DictWriter con `mode='a'` e `writeheader=False`)

**ATTENZIONE QUALITÀ:**
- Se `address` contiene città non-Milano → SKIP (`continue`)
- Se `real_name` è uguale a un nome già nel DB leggimenu (fuzzy match >90%) → SKIP
- Se `items_found` = 0 → aggiungi venues con `extraction_status='no_menu'` ma NESSUN item

---

## STEP 3 — TheFork via Wayback Machine (ALTERNATIVA SENZA CAPTCHA)

**Perché:** archive.org non usa Datadome. TheFork è crawlata massivamente da Wayback.
Possiamo leggere snapshot recenti (2025/2026) delle pagine menu TheFork senza essere bloccati.

**Discovery venue URLs da CDX API:**

```python
import requests, json, re, time
from urllib.parse import quote

CDX_API = "http://web.archive.org/cdx/search/cdx"

# Step A: trova tutti gli URL TheFork.it per ristoranti/bar Milano
# Il CDX API restituisce tutti gli URL indicizzati da Wayback Machine

params = {
    'url': 'thefork.it/ristorante/*',
    'output': 'json',
    'fl': 'original,timestamp,statuscode',
    'filter': 'statuscode:200',
    'from': '20250601',
    'to': '20260601',
    'limit': '5000',
    'collapse': 'original',  # un URL per venue
}
r = requests.get(CDX_API, params=params, timeout=60)
data = r.json()
# data[0] è l'header ['original','timestamp','statuscode']
urls = [(row[0], row[1]) for row in data[1:] if '/ristorante/' in row[0]]
print(f"TheFork URLs in Wayback: {len(urls)}")

# Filter Milano (many ways to tell):
# 1. URL contiene '-milano-' o '-mi-'
# 2. Visita pagina e controlla JSON-LD addressLocality

milan_urls = [(u, t) for u, t in urls if '-milano' in u.lower() or '/milano/' in u.lower()]
print(f"URL con 'milano' nell'URL: {len(milan_urls)}")

# Step B: visita lo snapshot Wayback per ogni URL Milan
WAYBACK_TPL = "https://web.archive.org/web/{timestamp}/{url}"

venues_found = []
for original_url, timestamp in milan_urls[:200]:  # max 200 per sessione
    wayback_url = WAYBACK_TPL.format(timestamp=timestamp, url=original_url)
    
    try:
        r = requests.get(wayback_url, timeout=15,
                         headers={'User-Agent': 'Mozilla/5.0'})
        if r.status_code != 200:
            time.sleep(1)
            continue
        
        soup = BeautifulSoup(r.text, 'lxml')
        
        # Rimuovi banner Wayback Machine
        for wb in soup.find_all(id=['wm-ipp-base', 'wm-ipp']):
            wb.decompose()
        
        # Estrai JSON-LD
        venue_name, lat, lon, address = '', '', '', ''
        for script in soup.find_all('script', type='application/ld+json'):
            try:
                data = json.loads(script.string)
                if isinstance(data, list): data = data[0]
                if isinstance(data, dict):
                    venue_name = data.get('name', '')
                    geo = data.get('geo', {})
                    if isinstance(geo, dict):
                        lat = str(geo.get('latitude',''))
                        lon = str(geo.get('longitude',''))
                    addr = data.get('address', {})
                    if isinstance(addr, dict):
                        address = ', '.join(filter(None,[
                            addr.get('streetAddress',''),
                            addr.get('addressLocality','')
                        ]))
            except: pass
        
        # Verifica sia Milano
        if address and 'Milano' not in address and 'MI' not in address:
            time.sleep(1)
            continue
        
        # Cerca sezione menu/prezzi
        items_from_page = []
        
        # TheFork espone prezzi in elementi con classe specifica
        for price_el in soup.find_all(class_=re.compile(r'price|prezzo|menu-item|dish')):
            text = price_el.get_text(strip=True)
            prices = re.findall(r'(\d+[,.]?\d{0,2})\s*€|€\s*(\d+[,.]?\d{0,2})', text)
            if prices and len(text) < 150:
                for m in prices:
                    price_str = m[0] or m[1]
                    try:
                        price = float(price_str.replace(',','.'))
                        if 0.5 <= price <= 60:
                            items_from_page.append({'text': text, 'price': price})
                    except: pass
        
        if venue_name:
            print(f"  FOUND: {venue_name} | {address} | {len(items_from_page)} items | {original_url}")
            venues_found.append({
                'name': venue_name, 'lat': lat, 'lon': lon,
                'address': address, 'url': original_url,
                'items': items_from_page
            })
        
    except Exception as e:
        print(f"  ERR {original_url[:60]}: {e}")
    
    time.sleep(2)  # Wayback ha rate limit gentile ma rispettalo

print(f"\nTheFork via Wayback: {len(venues_found)} venues trovate")
```

**Prova anche thefork.com** (versione internazionale):
```python
# Stesso CDX approach ma per thefork.com/restaurant/*milano*
params['url'] = 'thefork.com/restaurant/*'
# + filter per 'milano' nell'URL
```

**Output:** `raw_sources/thefork_venues.csv` + `raw_sources/thefork_menu_items.csv`
**source_platform:** `thefork`

**NOTA:** Se Wayback dà 0 risultati su TheFork, prova **yelp.it**:
```
http://web.archive.org/cdx/search/cdx?url=yelp.it/biz/*&output=json&filter=statuscode:200&from=20250101&limit=2000&collapse=original
```
Yelp spesso ha prezzi menzionati nelle review in modo strutturato.

---

## STEP 4 — eatbu + dish.co discovery (30 min, quick wins)

**eatbu.com** — menù digitale italiano, già usato (4 venues). Ne ha altri Milano.

```python
# eatbu URL pattern: https://www.eatbu.com/en/menu-restaurant-{city}/{slug}
# o: https://www.eatbu.com/it/menu-ristorante-{city}/{slug}
# Discovery: DuckDuckGo HTML search

import requests
from bs4 import BeautifulSoup
import time

def ddg_search(query, max_results=30):
    url = "https://html.duckduckgo.com/html/"
    r = requests.post(url, data={'q': query, 'kl': 'it-it'},
                      headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)
    soup = BeautifulSoup(r.text, 'lxml')
    results = []
    for a in soup.find_all('a', class_='result__url'):
        href = a.get('href','')
        if href:
            results.append(href)
    return results[:max_results]

eatbu_urls = ddg_search('site:eatbu.com milano bar cocktail')
print("eatbu candidate URLs:", eatbu_urls)
time.sleep(3)

# dish.co — la platform dei PDF (già usata)
dish_urls = ddg_search('site:dish.co/menu milano bar')
print("dish.co candidate URLs:", dish_urls)
```

Per ogni URL trovato che NON è già nel DB → estrai come fatto in sessione 1.

---

## STEP 5 — Geocoding finale venues rimaste su fallback

**Rimangono 2 venues leggimenu senza geo:**
- `laudanoemisture` → nessun indirizzo nel JSON-LD. Cerca su DuckDuckGo: `"Laudano e Misture" milano indirizzo`
- `scandinaviamilano` → UNAHOTELS Scandinavia, Via Soderini 21, 20146 Milano → geocoda direttamente

```python
import requests, time

NOMINATIM = 'https://nominatim.openstreetmap.org/search'
HEADERS = {'User-Agent': 'FoodPriceMilano/1.0 motti.tommy@gmail.com'}

# UNAHOTELS Scandinavia — indirizzo noto
r = requests.get(NOMINATIM, params={
    'q': 'Via Soderini 21 Milano', 'format': 'json', 'limit': 1, 'countrycodes': 'it'
}, headers=HEADERS, timeout=10)
data = r.json()
if data:
    print(f"UNAHOTELS: ({data[0]['lat']}, {data[0]['lon']})")
time.sleep(1.2)

# Laudano e Misture — prova con Startpage/DDG
# Dopo aver trovato l'indirizzo → geocoda con Nominatim
```

Aggiorna `raw_sources/leggimenu_venues.csv` con le coordinate trovate (sovrascrivi le righe con lat=45.4642).

---

## QUALITY GATES OBBLIGATORI

**Applica PRIMA di ogni commit:**

```python
def quality_check(items):
    issues = []
    for r in items:
        url = r.get('source_url','') or r.get('venue_url','')
        prod = r.get('normalized_product','')
        name = r.get('item_name','')
        venue = r.get('venue_name','')
        try: price = float(r.get('normalized_price_eur','0') or 0)
        except: price = 0
        
        # 1. URL immagine = junk
        if any(url.lower().endswith(e) for e in ['.jpg','.png','.webp','.gif','.ico','.css','.js']):
            issues.append(f'IMAGE_URL: {venue} | {url[-40:]}')
        
        # 2. Prezzi assurdi
        if 0 < price < 0.50:
            issues.append(f'PRICE_TOO_LOW: {venue} | {prod} | €{price}')
        if price > 80:
            issues.append(f'PRICE_TOO_HIGH: {venue} | {prod} | €{price} | {name}')
        
        # 3. False positive — rovere americano (legno botte whiskey)
        desc = (r.get('item_description','') or '').lower()
        if 'rovere americano' in desc or 'rovere americano' in name.lower():
            issues.append(f'OAK_FALSE_POSITIVE: {venue} | {name}')
        
        # 4. Caffè americano classificato come americano cocktail
        if prod == 'americano' and re.search(r'caff[eè]', name, re.I):
            issues.append(f'COFFEE_NOT_COCKTAIL: {venue} | {name} (rimuovi normalized_product)')
        
        # 5. Non-Milan venue
        addr = (r.get('address','') or '').lower()
        NON_MILAN = ['torino','palermo','siena','parma','ferrara','lecce','trento',
                     'pessione','roma','napoli','genova','venezia']
        if any(city in addr for city in NON_MILAN):
            issues.append(f'NON_MILAN: {venue} | addr={addr[:50]}')
        
        # 6. item_name troppo lungo = probabilmente pagina HTML, non un piatto
        if len(name) > 120:
            issues.append(f'NAME_TOO_LONG: {venue} | {name[:60]}...')
        
        # 7. Prezzo 0 con confidence high = errore
        if price == 0 and r.get('confidence','') == 'high':
            issues.append(f'ZERO_PRICE_HIGH_CONF: {venue} | {name}')
    
    return issues

issues = quality_check(all_new_items)
print(f"\n{'='*40}")
print(f"Quality check: {len(issues)} issues su {len(all_new_items)} items")
if issues:
    for i in issues[:30]:
        print(f"  {i}")
    print("Correggi prima di committare!")
else:
    print("OK — procedi col commit")
```

---

## RATE LIMITS (OBBLIGATORI)

| Target | Delay min | Stop se |
|---|---|---|
| leggimenu | 1.5s tra GET | HTTP 429 → sleep 120s |
| eatbu / dish.co | 2s tra GET | HTTP 429 → sleep 60s |
| Wayback Machine | 2s tra GET | HTTP 429 → sleep 300s |
| Siti diretti OSM | 2s tra GET | HTTP 403 → skip |
| Nominatim | 1.2s tra GET | 1 req/s SEMPRE |
| DuckDuckGo HTML | 5s tra query | stop se captcha |

---

## SCHEMA CSV (REMINDER)

Header obbligatorio per `*_menu_items.csv`:
```
source_platform,source_venue_id,venue_name,venue_url,menu_section,item_name,item_description,raw_price,normalized_price_eur,currency,price_type,item_type,normalized_product,confidence,allergens,retrieved_at,source_url
```

Header obbligatorio per `*_venues.csv`:
```
source_platform,source_venue_id,venue_name,venue_url,address,city,latitude,longitude,categories,price_tier,rating,rating_count,phone,website,opening_hours,has_menu,menu_url,extraction_status,retrieved_at
```

- Encoding: **UTF-8-sig (BOM)**
- Prezzi: **punto decimale** (`7.50` non `7,50`)
- `normalized_product` se non sicuro: **lascia vuoto** (mai inventare)
- `source_platform` validi: `leggimenu`, `direct_website`, `thefork`, `eatbu`, `other`

---

## COMMIT E CONSEGNA

```bash
cd D:\FindMyDeal
git pull origin main  # SEMPRE prima di aggiungere file

# Add solo i tuoi file nuovi
git add website/raw_sources/osm_direct2_venues.csv
git add website/raw_sources/osm_direct2_menu_items.csv
git add website/raw_sources/leggimenu_venues.csv       # se aggiornato geocoding
git add website/raw_sources/leggimenu_menu_items.csv   # se appeso nuovi items
git add website/raw_sources/thefork_venues.csv         # se Wayback ha funzionato
git add website/raw_sources/thefork_menu_items.csv

git commit -m "data: S3 — {fonte}: N venues, M items"
git push origin main
```

**Poi informa il CEO con questo template:**

```
✅ Sessione S3 completata — {data}

Step 1 (OSM direct): N venues con menu, M items
Step 2 (leggimenu slugs): N nuove venues trovate, M items
Step 3 (Wayback/TheFork): N venues, M items [oppure: ZERO RISULTATI]
Step 4 (eatbu/dish.co): N nuove venues, M items
Step 5 (geocoding): K venues geocodate

TOTALE NUOVO: +N items, +M venues
File pushati: lista file
Quality check: issues = 0 [oppure: K issues corretti]

Anomalie trovate:
- [lista eventuali problemi]
```

---

## PRIORITÀ SE TEMPO SCARSO

| Priorità | Step | Yield atteso | Tempo |
|---|---|---|---|
| 🔴 1 | leggimenu slug brute-force | 40-120 venues × 50 items = **2.000-6.000 items** | 3-4h |
| 🟠 2 | OSM direct 79 venues | 10-20 venues × 25 items = **250-500 items** | 1-2h |
| 🟡 3 | TheFork Wayback | Incerto ma potenzialmente alto | 1h |
| 🟢 4 | eatbu/dish discovery | 5-15 venues × 20 items = **100-300 items** | 30min |
| ⚪ 5 | Geocoding 2 venues | Qualità, non volume | 15min |

---

## ERRORI DA NON RIPETERE (dalle sessioni precedenti)

1. ❌ "Sicilian white_wine €16" — era descrizione pasta. Verifica contesto prima di assegnare prodotto.
2. ❌ URL `.webp/.png` scrapate come se fossero pagine menu — check `source_url` extension.
3. ❌ Casa Martini a Pessione (TO) inclusa come "Milano" — verifica SEMPRE la città.
4. ❌ "Spritz Navigli" come `item_name = "Spritz"` perché il bar si chiama così — usa il contesto.
5. ❌ Eatmeandgo €9.9 "finger food + spritz" — è prezzo combo, NON solo spritz.
6. ❌ `americano` su "caffè americano" — è un caffè, NON il cocktail. Lascia `normalized_product` vuoto.
7. ❌ 12.000 items nazionali di menudigitale inclusi — filtra SEMPRE per città=Milano prima di committare.
8. ❌ Rovere americano (legno botte) normalizzato come cocktail `americano` — leggi la descrizione.

---

Buona sessione Pietro. L'obiettivo è **+2.000 items nuovi** col leggimenu brute-force.
Il CEO farà merge e push non appena consegni.
