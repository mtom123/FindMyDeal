"""
Barber S1 — Fresha Italia (light)
Sitemap: https://sitemaps.fresha.com/www/sitemap-salons-{N}.xml
Italy detection: image filenames contain '-IT-' (e.g. Elixhair-IT-Sardegna-Cagliari.jpg)
Fallback: Italian street keywords in URL slug
Source: __NEXT_DATA__ → location object (name, address, geo, services with prices)
"""
import sys, os, re, json, csv, time, logging
from datetime import datetime, timezone
from urllib.parse import urlparse
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests
import threading

sys.path.insert(0, os.path.dirname(__file__))
from normalization import BARBER_PRODUCTS, validate_barber_item

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(message)s',
    handlers=[
        logging.FileHandler('barber_s1_fresha.log'),
        logging.StreamHandler(sys.stdout),
    ]
)
log = logging.getLogger(__name__)

HEADERS = {
    'User-Agent': (
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) '
        'AppleWebKit/537.36 (KHTML, like Gecko) '
        'Chrome/124.0.0.0 Safari/537.36'
    ),
    'Accept-Language': 'it-IT,it;q=0.9,en;q=0.8',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Referer': 'https://www.fresha.com/',
}

WORKERS    = 4
DELAY      = 2.0   # Fresha is stricter than Treatwell (CF medium)
TIMEOUT    = 25
CHECKPOINT = 50

BASE_DIR    = os.path.join(os.path.dirname(__file__), '..', 'raw_sources')
VENUES_FILE = os.path.join(BASE_DIR, 'barber_s1_fresha_venues.csv')
ITEMS_FILE  = os.path.join(BASE_DIR, 'barber_s1_fresha_items.csv')
URLS_FILE   = os.path.join(BASE_DIR, 'barber_s1_fresha_italy_urls.txt')
NOW_ISO     = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
os.makedirs(BASE_DIR, exist_ok=True)

VENUE_FIELDS = [
    'source_platform','source_venue_id','venue_name','venue_url','address',
    'city','province','region','postal_code','latitude','longitude',
    'categories','barber_category','price_tier','rating','rating_count',
    'phone','website','booking_provider','extraction_status','retrieved_at','vertical',
]
ITEM_FIELDS = [
    'source_platform','source_venue_id','venue_name','venue_url','menu_section',
    'item_name','item_description','raw_price','normalized_price_eur','currency',
    'price_type','normalized_product','confidence','retrieved_at','source_url','vertical',
]

write_lock   = threading.Lock()
stats_lock   = threading.Lock()
GLOBAL_STATS = {'venues': 0, 'items': 0, 'priced_items': 0, 'errors': 0, 'done': 0}

# Italian street keywords
IT_STREET_RE = re.compile(
    r'-(via|viale|corso|piazza|piazzale|lungadige|lungomare|vicolo|largo|'
    r'strada|localita|borgo|contrada|salita|traversa|circonvallazione)-'
)

# ─── Service classifier (same as Treatwell) ─────────────────────────────────
SERVICE_MAP = [
    (r'\brasatura\b|\bshave\b|\bradere\b',                                    'beard_shave'),
    (r'(pacchetto|combo).{0,30}(taglio|cut).{0,30}barba|barba.{0,30}(taglio|cut)', 'package_cut_beard'),
    (r'\bbarba\b.{0,20}\bcolo(r|ur)',                                         'beard_color'),
    (r'\bbarba\b|\bbeard\b|\brifilatura barba\b',                             'beard_trim'),
    (r'\bbambino\b|\bchild\b|\bbimb\b|\bkid\b',                               'haircut_child'),
    (r'\bdonna\b|\blong hair\b|\bfemm\b|\bcapell.{0,10}lung',                 'haircut_woman'),
    (r'\buomo\b|\bman\b|\bmasch\b',                                           'haircut_man'),
    (r'(pacchetto|combo).{0,30}colo(r|ur).{0,30}taglio|colo(r|ur).{0,10}taglio', 'package_color_cut'),
    (r'\bmeches?\b|\bbalayage\b|\bcolpi.{0,10}sole\b|\bhighlight',            'hair_highlight'),
    (r'\bdecolor\b|\bbleach\b',                                               'hair_bleach'),
    (r'\btonali\b|\btoning\b|\bgloss\b',                                      'hair_toning'),
    (r'colo(r|ur).{0,20}capell|capell.{0,20}colo(r|ur)|\bcolorazione\b|\bcolore\b', 'hair_color'),
    (r'\bextension\b',                                                        'hair_extensions'),
    (r'\bpermanente\b|\bperm\b',                                              'hair_perm'),
    (r'\bcheratina\b|\bstiratura\b|\blisciante\b|\bstraighten\b',             'hair_straightening'),
    (r'\bacconciatura\b|\bupdo\b|\bcerimonia\b|\bsposa\b',                    'hair_updo'),
    (r'lavaggio.{0,20}piega|wash.{0,20}blow',                                 'hair_wash_blowdry'),
    (r'\bpiega\b|\bblowdr\b|\bblowout\b|\basciugatura\b',                     'hair_blowdry'),
    (r'\btrattamento\b|\bmaschera capell\b|\bhair treatment\b|\bkerat',       'hair_treatment'),
    (r'\bsopracciglia\b|\bbrow\b|\barch\b',                                   'eyebrow_trim'),
    (r'scrub.{0,15}vis|esfoliante',                                           'face_scrub'),
    (r'maschera.{0,15}vis|face mask',                                         'face_mask'),
    (r'\bpacchetto\b|\bfull treatment\b|\btrattamento completo\b',            'package_full_treatment'),
    (r'\btaglio\b|\bhaircut\b|\bcut\b',                                       'haircut_man'),
]

def classify_service(name: str) -> str:
    n = name.lower()
    for pattern, code in SERVICE_MAP:
        if re.search(pattern, n):
            return code
    return ''

def detect_category(name, url, biz_type=''):
    n = (name + url + biz_type).lower()
    if any(kw in n for kw in ['barber','barbiere','barbershop']):
        return 'barber'
    if 'parrucchier' in n:
        return 'unisex'
    if any(kw in n for kw in ['donna','women','ladies','femmin']):
        return 'salon_donna'
    if any(kw in n for kw in ['bimb','bambino','kid','child']):
        return 'kids'
    return 'unisex'

# ─── Italy URL discovery ─────────────────────────────────────────────────────

def discover_italy_urls():
    """Build list of Fresha Italy venue URLs from sitemap chunks."""
    if os.path.exists(URLS_FILE):
        with open(URLS_FILE) as f:
            urls = [line.strip() for line in f if line.strip()]
        log.info(f"Loaded {len(urls)} cached Italy URLs from {URLS_FILE}")
        return urls

    log.info("Discovering Italy URLs from Fresha sitemaps…")
    italy = set()
    session = requests.Session(); session.headers.update(HEADERS)

    # sitemap-salons-NNNNN — venue+image entries
    for chunk_n in ['00001', '00002']:
        url = f'https://sitemaps.fresha.com/www/sitemap-salons-{chunk_n}.xml'
        log.info(f"  Fetching {url}")
        try:
            r = session.get(url, timeout=60)
            r.raise_for_status()
        except Exception as e:
            log.warning(f"  Failed: {e}")
            continue
        soup = BeautifulSoup(r.text, 'lxml-xml')
        locs = [l.text for l in soup.find_all('loc')]

        curr_venue = None
        for loc in locs:
            if loc.startswith('https://www.fresha.com/a/'):
                curr_venue = loc
                # Fallback: Italian street keywords in slug
                if IT_STREET_RE.search(loc.lower()):
                    italy.add(curr_venue)
            elif 'images.fresha.com' in loc and curr_venue:
                if '-IT-' in loc:
                    italy.add(curr_venue)
        log.info(f"  Italy URLs so far: {len(italy)}")
        time.sleep(2)

    # lite-venue-pages: 25 chunks, Italian addresses in slug
    for i in range(1, 26):
        url = f'https://www.fresha.com/lp/en/sitemap-lite-venue-pages-{i:05d}.xml'
        try:
            r = session.get(url, timeout=60)
            if r.status_code != 200:
                continue
        except Exception:
            continue
        soup = BeautifulSoup(r.text, 'lxml-xml')
        locs = [l.text for l in soup.find_all('loc')]
        # Italian indicators in lvp slugs: ends with major IT city
        IT_CITIES = ['-milano-', '-roma-', '-torino-', '-napoli-', '-firenze-',
                     '-bologna-', '-genova-', '-palermo-', '-bari-', '-padova-',
                     '-verona-', '-catania-', '-venezia-', '-trieste-', '-brescia-',
                     '-parma-', '-modena-', '-perugia-', '-livorno-', '-rimini-']
        for loc in locs:
            ll = loc.lower()
            if any(c in ll for c in IT_CITIES):
                italy.add(loc)
        time.sleep(1)
        if i % 5 == 0:
            log.info(f"  lvp chunks {i}/25 | Italy URLs: {len(italy)}")

    italy_list = sorted(italy)
    with open(URLS_FILE, 'w') as f:
        for u in italy_list:
            f.write(u + '\n')
    log.info(f"Cached {len(italy_list)} Italy URLs → {URLS_FILE}")
    return italy_list

# ─── Venue extraction ────────────────────────────────────────────────────────

def extract_venue_from_next_data(soup, slug, url):
    nd = soup.find('script', id='__NEXT_DATA__')
    if not nd:
        return None, []
    try:
        data = json.loads(nd.string)
    except Exception:
        return None, []

    pp = data.get('props', {}).get('pageProps', {}) or {}
    loc = (pp.get('data', {}) or {}).get('location') or pp.get('liteLocation') or {}
    if not loc:
        return None, []

    name = loc.get('name', '') or slug
    addr = loc.get('address', {}) or {}
    street      = addr.get('streetAddress', '') or ''
    city        = addr.get('cityName', '') or ''
    region      = ''
    postal_code = ''
    full_addr   = addr.get('shortFormatted') or addr.get('simpleFormatted', '')
    # extract region/postal from short address
    if full_addr:
        m = re.search(r'\b(\d{5})\b', full_addr)
        if m: postal_code = m.group(1)
        # last segment often is region
        parts = [p.strip() for p in full_addr.split(',')]
        if len(parts) >= 3:
            region = parts[-1].strip()
    lat = addr.get('latitude', '')
    lon = addr.get('longitude', '')

    biz = (loc.get('primaryBusinessType') or {}).get('name', '') or ''
    rating       = str(loc.get('rating', '') or '')
    rating_count = str(loc.get('reviewsCount', '') or '')
    phone        = loc.get('contactNumber', '') or ''

    # Services
    items = []
    seen  = set()
    for group in loc.get('services', []) or []:
        group_name = group.get('name', '')
        for it in group.get('items', []) or []:
            svc_name = it.get('name', '') or ''
            if not svc_name or len(svc_name) < 3:
                continue
            price_obj = it.get('retailPrice') or {}
            currency  = price_obj.get('currency', 'EUR')
            value     = price_obj.get('value')
            try:
                norm_p = float(value) if value is not None else 0.0
            except Exception:
                norm_p = 0.0
            key = (svc_name.lower(), str(norm_p))
            if key in seen:
                continue
            seen.add(key)
            prod = classify_service(svc_name)
            item = {
                'source_platform': 'fresha', 'source_venue_id': slug,
                'venue_name': name, 'venue_url': url,
                'menu_section': group_name or 'servizi',
                'item_name': svc_name[:150],
                'item_description': (it.get('description') or '')[:200],
                'raw_price': str(value) if value is not None else '',
                'normalized_price_eur': norm_p,
                'currency': currency, 'price_type': 'per_service',
                'normalized_product': prod,
                'confidence': 'high' if norm_p > 0 else 'medium',
                'retrieved_at': NOW_ISO, 'source_url': url, 'vertical': 'barber',
            }
            ok, clean, _ = validate_barber_item(item.copy())
            items.append(clean if ok else {**item, 'normalized_product': ''})

    barber_cat = detect_category(name, url, biz)
    has_prices = any(float(it.get('normalized_price_eur') or 0) > 0 for it in items)
    venue = {
        'source_platform': 'fresha', 'source_venue_id': slug,
        'venue_name': name, 'venue_url': url,
        'address': street or full_addr, 'city': city,
        'province': '', 'region': region, 'postal_code': postal_code,
        'latitude': str(lat) if lat else '', 'longitude': str(lon) if lon else '',
        'categories': biz, 'barber_category': barber_cat,
        'price_tier': '',
        'rating': rating, 'rating_count': rating_count,
        'phone': phone, 'website': '',
        'booking_provider': 'fresha',
        'extraction_status': 'ok' if has_prices else 'ok_no_prices',
        'retrieved_at': NOW_ISO, 'vertical': 'barber',
    }
    return venue, items

# ─── CSV I/O ──────────────────────────────────────────────────────────────────

def append_to_csv(venues, items):
    with write_lock:
        with open(VENUES_FILE, 'a', newline='', encoding='utf-8') as f:
            w = csv.DictWriter(f, fieldnames=VENUE_FIELDS, extrasaction='ignore')
            w.writerows(venues)
        with open(ITEMS_FILE, 'a', newline='', encoding='utf-8') as f:
            w = csv.DictWriter(f, fieldnames=ITEM_FIELDS, extrasaction='ignore')
            w.writerows(items)

def init_csv():
    if not os.path.exists(VENUES_FILE):
        with open(VENUES_FILE, 'w', newline='', encoding='utf-8') as f:
            csv.DictWriter(f, fieldnames=VENUE_FIELDS).writeheader()
    if not os.path.exists(ITEMS_FILE):
        with open(ITEMS_FILE, 'w', newline='', encoding='utf-8') as f:
            csv.DictWriter(f, fieldnames=ITEM_FIELDS).writeheader()

def load_done_slugs():
    done = set()
    if os.path.exists(VENUES_FILE):
        with open(VENUES_FILE, newline='', encoding='utf-8') as f:
            for row in csv.DictReader(f):
                if row.get('source_venue_id'):
                    done.add(row['source_venue_id'])
    return done

# ─── Worker ──────────────────────────────────────────────────────────────────

def worker_thread(tid: int, urls: list, start: float, total: int):
    session = requests.Session(); session.headers.update(HEADERS)
    buf_v, buf_i = [], []
    for url in urls:
        slug = urlparse(url).path.strip('/').split('/')[-1]
        try:
            time.sleep(DELAY)
            r = session.get(url, timeout=TIMEOUT)
            if r.status_code == 429:
                log.warning(f"[T{tid}] 429 — sleeping 120s")
                time.sleep(120)
                r = session.get(url, timeout=TIMEOUT)
            if r.status_code != 200:
                with stats_lock:
                    GLOBAL_STATS['errors'] += 1
                    GLOBAL_STATS['done'] += 1
                continue
        except Exception as e:
            log.warning(f"[T{tid}] err {slug}: {e}")
            with stats_lock:
                GLOBAL_STATS['errors'] += 1
                GLOBAL_STATS['done'] += 1
            continue

        soup = BeautifulSoup(r.text, 'lxml')
        venue, items = extract_venue_from_next_data(soup, slug, url)
        if venue is None:
            with stats_lock:
                GLOBAL_STATS['errors'] += 1
                GLOBAL_STATS['done'] += 1
            continue

        buf_v.append(venue)
        buf_i.extend(items)
        priced = sum(1 for it in items if float(it.get('normalized_price_eur') or 0) > 0)
        with stats_lock:
            GLOBAL_STATS['venues']       += 1
            GLOBAL_STATS['items']        += len(items)
            GLOBAL_STATS['priced_items'] += priced
            GLOBAL_STATS['done']         += 1

        if len(buf_v) >= CHECKPOINT:
            append_to_csv(buf_v, buf_i)
            elapsed = time.time() - start
            rate    = GLOBAL_STATS['done'] / elapsed * 60
            eta_min = (total - GLOBAL_STATS['done']) / max(rate, 1)
            log.info(
                f"[T{tid}] checkpoint | done={GLOBAL_STATS['done']}/{total} "
                f"venues={GLOBAL_STATS['venues']} items={GLOBAL_STATS['items']} "
                f"priced={GLOBAL_STATS['priced_items']} errors={GLOBAL_STATS['errors']} "
                f"rate={rate:.0f}/min ETA={eta_min:.0f}min"
            )
            buf_v.clear(); buf_i.clear()

    if buf_v:
        append_to_csv(buf_v, buf_i)
        log.info(f"[T{tid}] DONE — flushed {len(buf_v)}")

# ─── Main ────────────────────────────────────────────────────────────────────

def main():
    log.info(f"=== BARBER S1 — Fresha Italia | {WORKERS} threads | {DELAY}s ===")
    all_urls   = discover_italy_urls()
    done_slugs = load_done_slugs()
    log.info(f"Total Italy URLs: {len(all_urls)} | Already done: {len(done_slugs)}")
    init_csv()

    remaining = [u for u in all_urls
                 if urlparse(u).path.strip('/').split('/')[-1] not in done_slugs]
    log.info(f"Remaining: {len(remaining)}")
    if not remaining:
        log.info("All done!")
        return

    chunk_size = (len(remaining) + WORKERS - 1) // WORKERS
    chunks = [remaining[i:i+chunk_size] for i in range(0, len(remaining), chunk_size)]
    log.info(f"Chunks: {[len(c) for c in chunks]}")

    start = time.time()
    GLOBAL_STATS['done'] = 0
    threads = []
    for i, chunk in enumerate(chunks):
        t = threading.Thread(target=worker_thread,
                             args=(i, chunk, start, len(remaining)),
                             daemon=True)
        threads.append(t); t.start()
    for t in threads: t.join()

    # Report
    all_v, all_i = [], []
    with open(VENUES_FILE, newline='', encoding='utf-8') as f: all_v = list(csv.DictReader(f))
    with open(ITEMS_FILE,  newline='', encoding='utf-8') as f: all_i = list(csv.DictReader(f))

    priced_v = len(set(it['source_venue_id'] for it in all_i if float(it.get('normalized_price_eur') or 0) > 0))
    priced_i = sum(1 for it in all_i if float(it.get('normalized_price_eur') or 0) > 0)
    cities = {}
    for v in all_v: cities[v.get('city') or 'unknown'] = cities.get(v.get('city') or 'unknown', 0) + 1
    top_c = sorted(cities.items(), key=lambda x: -x[1])[:20]
    prod_c = {}
    for it in all_i: prod_c[it.get('normalized_product') or 'unclassified'] = prod_c.get(it.get('normalized_product') or 'unclassified', 0) + 1
    elapsed_min = (time.time() - start) / 60

    report = f"""# Barber S1 Fresha — Report ({NOW_ISO})

## Metriche

| Metrica | Valore |
|---|---|
| **Venue totali Italia** | {len(all_v)} |
| **Venue con prezzi** | {priced_v} |
| **Items totali** | {len(all_i)} |
| **Items prezzati** | {priced_i} |
| **Errors** | {GLOBAL_STATS['errors']} |
| **Run time** | {elapsed_min:.1f} min |

## Top Città

| Città | Venues |
|---|---|
{chr(10).join(f'| {c} | {n} |' for c,n in top_c)}

## Prodotti (top 20)

| Prodotto | Items |
|---|---|
{chr(10).join(f'| {p} | {n} |' for p,n in sorted(prod_c.items(), key=lambda x:-x[1])[:20])}
"""
    rp = os.path.join(os.path.dirname(__file__), '..', 'barber_s1_FRESHA_REPORT.md')
    with open(rp, 'w') as f: f.write(report)
    log.info(f"=== DONE: {len(all_v)} venues | {priced_v} priced | {elapsed_min:.1f}min ===")

if __name__ == '__main__':
    main()
