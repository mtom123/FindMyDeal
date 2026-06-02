"""
Barber S1 — Treatwell Italia (4 threads, partition model)
Primary: window.__state__ JSON. Fallback: DOM.
Continues from checkpoint. Checkpoint every 100 venues per thread.
"""
import sys, os, re, json, csv, time, logging
from datetime import datetime, timezone
from urllib.parse import urlparse
from bs4 import BeautifulSoup
import requests
import threading

sys.path.insert(0, os.path.dirname(__file__))
from normalization import BARBER_PRODUCTS, validate_barber_item

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(message)s',
    handlers=[
        logging.FileHandler('barber_s1_treatwell.log'),
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
    'Referer': 'https://www.treatwell.it/',
}

WORKERS      = 4
DELAY        = 1.2
TIMEOUT      = 20
CHECKPOINT   = 100   # flush every N per thread

BASE_DIR    = os.path.join(os.path.dirname(__file__), '..', 'raw_sources')
VENUES_FILE = os.path.join(BASE_DIR, 'barber_s1_treatwell_venues.csv')
ITEMS_FILE  = os.path.join(BASE_DIR, 'barber_s1_menu_items.csv')
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

# ─── Service classifier ───────────────────────────────────────────────────────
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

def parse_price(raw) -> float:
    if isinstance(raw, (int, float)):
        return float(raw)
    raw = str(raw).replace('\xa0', ' ').replace('da ', '').replace('Da ', '').strip()
    m = re.search(r'(\d+[,.]?\d*)', raw)
    return float(m.group(1).replace(',', '.')) if m else 0.0

def detect_category(name, url):
    n = (name + url).lower()
    if any(kw in n for kw in ['barber','barbiere','barbershop']):
        return 'barber'
    if any(kw in n for kw in ['donna','women','ladies','femmin']):
        return 'salon_donna'
    if any(kw in n for kw in ['bimb','bambino','kid','child']):
        return 'kids'
    return 'unisex'

# ─── __state__ extractor ──────────────────────────────────────────────────────

def extract_from_state(soup, slug, url):
    for tag in soup.find_all('script'):
        t = tag.string or ''
        if '__state__' not in t:
            continue
        m = re.search(r'window\.__state__\s*=\s*(\{.+)', t, re.DOTALL)
        if not m:
            continue
        try:
            state = json.loads(m.group(1).rstrip(';'))
        except Exception:
            continue

        vs = state.get('venue', {}).get('venue', {})
        if not vs:
            continue

        name = vs.get('name', '') or slug
        loc  = vs.get('location', {}) or {}
        pt   = loc.get('point', {}) or {}
        lat  = str(pt.get('lat', ''))
        lon  = str(pt.get('lon', ''))
        addr_obj    = loc.get('address', {}) or {}
        addr_lines  = addr_obj.get('addressLines', [])
        postal_code = addr_obj.get('postalCode', '') or ''
        address     = ', '.join(filter(None, addr_lines))
        city = province = ''
        if addr_lines:
            last = addr_lines[-1].strip()
            m2 = re.match(r'^([A-Za-zÀ-ú ]+?)\s+([A-Z]{2})$', last)
            if m2:
                city = m2.group(1).strip(); province = m2.group(2)
            else:
                city = last
        if not city:
            tree = loc.get('tree', {}) or {}
            tree_name = tree.get('name', '')
            city = tree_name.split(',')[-1].strip() if ',' in tree_name else tree_name

        rating_obj   = vs.get('rating', {}) or {}
        rating       = str(rating_obj.get('average', ''))
        rating_count = str(rating_obj.get('count', ''))
        contact      = vs.get('contact', {}) or {}

        items = []
        menu_groups = (vs.get('menu', {}) or {}).get('menuGroups', []) or []
        seen_keys = set()
        for group in menu_groups:
            group_name = group.get('name', '')
            for mi in group.get('menuItems', []):
                data = mi.get('data', {}) or {}
                svc_name = data.get('name', '') or ''
                if not svc_name or len(svc_name) < 3:
                    continue
                pr = data.get('priceRange', {}) or {}
                min_price = pr.get('minSalePriceAmount') or pr.get('minFullPriceAmount') or 0
                norm_p = parse_price(min_price)
                key = (svc_name.lower(), str(norm_p))
                if key in seen_keys:
                    continue
                seen_keys.add(key)
                prod = classify_service(svc_name)
                item = {
                    'source_platform': 'treatwell', 'source_venue_id': slug,
                    'venue_name': name, 'venue_url': url,
                    'menu_section': group_name or 'servizi',
                    'item_name': svc_name[:150],
                    'item_description': (data.get('description', '') or '')[:200],
                    'raw_price': str(min_price),
                    'normalized_price_eur': norm_p,
                    'currency': 'EUR', 'price_type': 'per_service',
                    'normalized_product': prod,
                    'confidence': 'high' if norm_p > 0 else 'medium',
                    'retrieved_at': NOW_ISO, 'source_url': url, 'vertical': 'barber',
                }
                ok, clean, _ = validate_barber_item(item.copy())
                items.append(clean if ok else {**item, 'normalized_product': ''})

        barber_cat = detect_category(name, url)
        has_prices = any(float(it.get('normalized_price_eur') or 0) > 0 for it in items)
        venue = {
            'source_platform': 'treatwell', 'source_venue_id': slug,
            'venue_name': name, 'venue_url': url,
            'address': address, 'city': city, 'province': province,
            'region': '', 'postal_code': postal_code,
            'latitude': lat, 'longitude': lon, 'categories': '',
            'barber_category': barber_cat, 'price_tier': '',
            'rating': rating, 'rating_count': rating_count,
            'phone': contact.get('phoneNumber', ''),
            'website': contact.get('websiteUrl', ''),
            'booking_provider': 'treatwell',
            'extraction_status': 'ok' if has_prices else 'ok_no_prices',
            'retrieved_at': NOW_ISO, 'vertical': 'barber',
        }
        return venue, items

    return None, []

# ─── DOM fallback ─────────────────────────────────────────────────────────────

def extract_from_dom(soup, slug, url):
    name = ''
    h1 = soup.find('h1')
    if h1: name = h1.get_text(strip=True)
    lat = lon = address = city = postal_code = province = ''
    for tag in soup.find_all('script', type='application/ld+json'):
        try:
            d = json.loads(tag.string or '{}')
            if isinstance(d, list): d = d[0]
            geo  = d.get('geo', {}) or {}
            lat  = lat or str(geo.get('latitude', ''))
            lon  = lon or str(geo.get('longitude', ''))
            aobj = d.get('address', {}) or {}
            if isinstance(aobj, dict):
                address  = address or aobj.get('streetAddress', '')
                city     = city or aobj.get('addressLocality', '')
                province = province or aobj.get('addressRegion', '')
                postal_code = postal_code or aobj.get('postalCode', '')
        except Exception: pass

    items = []
    seen  = set()
    for container in soup.select('[class*="menu-item"]'):
        title_el = container.select_one('[class*="title"]')
        price_el = container.select_one('[class*="priceLabel"]')
        if not title_el: continue
        svc_name = title_el.get_text(strip=True)
        if not svc_name or len(svc_name) < 3: continue
        raw_p  = price_el.get_text(separator='', strip=True) if price_el else ''
        norm_p = parse_price(raw_p) if raw_p else 0.0
        key = (svc_name.lower(), str(norm_p))
        if key in seen: continue
        seen.add(key)
        prod = classify_service(svc_name)
        item = {
            'source_platform': 'treatwell', 'source_venue_id': slug,
            'venue_name': name or slug, 'venue_url': url,
            'menu_section': 'servizi', 'item_name': svc_name[:150],
            'item_description': '', 'raw_price': raw_p,
            'normalized_price_eur': norm_p, 'currency': 'EUR',
            'price_type': 'per_service', 'normalized_product': prod,
            'confidence': 'high' if norm_p > 0 else 'low',
            'retrieved_at': NOW_ISO, 'source_url': url, 'vertical': 'barber',
        }
        ok, clean, _ = validate_barber_item(item.copy())
        items.append(clean if ok else {**item, 'normalized_product': ''})

    barber_cat = detect_category(name, url)
    has_prices = any(float(it.get('normalized_price_eur') or 0) > 0 for it in items)
    venue = {
        'source_platform': 'treatwell', 'source_venue_id': slug,
        'venue_name': name or slug, 'venue_url': url,
        'address': address, 'city': city, 'province': province,
        'region': '', 'postal_code': postal_code,
        'latitude': lat, 'longitude': lon, 'categories': '',
        'barber_category': barber_cat, 'price_tier': '', 'rating': '', 'rating_count': '',
        'phone': '', 'website': '', 'booking_provider': 'treatwell',
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
    """Write headers if files don't exist."""
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

# ─── Worker thread ────────────────────────────────────────────────────────────

def worker_thread(thread_id: int, urls: list, start_time: float, total_remaining: int):
    session = requests.Session()
    session.headers.update(HEADERS)
    buf_v, buf_i = [], []

    for i, url in enumerate(urls):
        slug = urlparse(url).path.strip('/').split('/')[-1]
        try:
            time.sleep(DELAY)
            r = session.get(url, timeout=TIMEOUT)
            if r.status_code == 429:
                log.warning(f"[T{thread_id}] 429 — sleeping 90s")
                time.sleep(90)
                r = session.get(url, timeout=TIMEOUT)
            if r.status_code not in (200,):
                with stats_lock:
                    GLOBAL_STATS['errors'] += 1
                    GLOBAL_STATS['done']   += 1
                continue
        except Exception as e:
            log.warning(f"[T{thread_id}] error {slug}: {e}")
            with stats_lock:
                GLOBAL_STATS['errors'] += 1
                GLOBAL_STATS['done']   += 1
            continue

        soup = BeautifulSoup(r.text, 'lxml')
        venue, items = extract_from_state(soup, slug, url)
        if venue is None:
            venue, items = extract_from_dom(soup, slug, url)

        buf_v.append(venue)
        buf_i.extend(items)

        priced = sum(1 for it in items if float(it.get('normalized_price_eur') or 0) > 0)
        with stats_lock:
            GLOBAL_STATS['venues']      += 1
            GLOBAL_STATS['items']       += len(items)
            GLOBAL_STATS['priced_items'] += priced
            GLOBAL_STATS['done']        += 1

        if len(buf_v) >= CHECKPOINT:
            append_to_csv(buf_v, buf_i)
            elapsed = time.time() - start_time
            total_done = GLOBAL_STATS['done']
            rate = total_done / elapsed * 60
            eta_h = (total_remaining - total_done) / max(rate, 1) / 60
            log.info(
                f"[T{thread_id}] checkpoint | global done={total_done}/{total_remaining} "
                f"venues={GLOBAL_STATS['venues']} items={GLOBAL_STATS['items']} "
                f"priced={GLOBAL_STATS['priced_items']} errors={GLOBAL_STATS['errors']} "
                f"rate={rate:.0f}/min ETA={eta_h:.1f}h"
            )
            buf_v.clear(); buf_i.clear()

    # final flush
    if buf_v:
        append_to_csv(buf_v, buf_i)
        log.info(f"[T{thread_id}] DONE — flushed {len(buf_v)} remaining")

# ─── Main ─────────────────────────────────────────────────────────────────────

def load_sitemap():
    log.info("Fetching sitemap…")
    s = requests.Session(); s.headers.update(HEADERS)
    r = s.get('https://www.treatwell.it/salone/site-map-venue-details-1.xml', timeout=30)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, 'lxml-xml')
    urls = [loc.text.strip() for loc in soup.find_all('loc')]
    log.info(f"Sitemap: {len(urls)} URLs")
    return urls

def main():
    log.info(f"=== BARBER S1 Treatwell | {WORKERS} threads | {DELAY}s delay ===")
    all_urls   = load_sitemap()
    done_slugs = load_done_slugs()
    log.info(f"Already done: {len(done_slugs)}")
    init_csv()

    milano_urls = [u for u in all_urls if 'milano' in u.lower()]
    other_urls  = [u for u in all_urls if u not in set(milano_urls)]
    ordered     = milano_urls + other_urls
    remaining   = [u for u in ordered
                   if urlparse(u).path.strip('/').split('/')[-1] not in done_slugs]
    log.info(f"Total={len(all_urls)} Done={len(done_slugs)} Remaining={len(remaining)}")

    if not remaining:
        log.info("All done!")
        return

    # Partition into WORKERS chunks
    chunk_size = (len(remaining) + WORKERS - 1) // WORKERS
    chunks = [remaining[i:i+chunk_size] for i in range(0, len(remaining), chunk_size)]
    log.info(f"Chunks: {[len(c) for c in chunks]}")

    start = time.time()
    GLOBAL_STATS['done'] = len(done_slugs)
    threads = []
    for i, chunk in enumerate(chunks):
        t = threading.Thread(
            target=worker_thread,
            args=(i, chunk, start, len(all_urls)),
            daemon=True,
        )
        threads.append(t)
        t.start()

    for t in threads:
        t.join()

    # Final report
    all_v, all_i = [], []
    with open(VENUES_FILE, newline='', encoding='utf-8') as f: all_v = list(csv.DictReader(f))
    with open(ITEMS_FILE,  newline='', encoding='utf-8') as f: all_i = list(csv.DictReader(f))

    priced_v = len(set(it['source_venue_id'] for it in all_i if float(it.get('normalized_price_eur') or 0) > 0))
    priced_i = sum(1 for it in all_i if float(it.get('normalized_price_eur') or 0) > 0)
    cities   = {}
    for v in all_v: cities[v.get('city') or 'unknown'] = cities.get(v.get('city') or 'unknown', 0) + 1
    top_c    = sorted(cities.items(), key=lambda x: -x[1])[:20]
    prod_c   = {}
    for it in all_i: prod_c[it.get('normalized_product') or 'unclassified'] = prod_c.get(it.get('normalized_product') or 'unclassified', 0) + 1
    elapsed_min = (time.time() - start) / 60

    report = f"""# Barber S1 Treatwell — Report ({NOW_ISO})

## Metriche finali

| Metrica | Valore |
|---|---|
| **Venue totali** | {len(all_v)} |
| **Venue con prezzi** | {priced_v} |
| **Items totali** | {len(all_i)} |
| **Items prezzati** | {priced_i} |
| **Errors** | {GLOBAL_STATS['errors']} |
| **Sitemap URL** | {len(all_urls)} |
| **Run time** | {elapsed_min:.1f} min |

## Top Città

| Città | Venues |
|---|---|
{chr(10).join(f'| {c} | {n} |' for c,n in top_c)}

## Prodotti normalizzati (top 20)

| Prodotto | Items |
|---|---|
{chr(10).join(f'| {p} | {n} |' for p,n in sorted(prod_c.items(), key=lambda x:-x[1])[:20])}
"""
    rp = os.path.join(os.path.dirname(__file__), '..', 'barber_s1_REPORT.md')
    with open(rp, 'w') as f: f.write(report)
    log.info(f"=== DONE: {len(all_v)} venues | {priced_v} priced | {elapsed_min:.1f}min ===")

if __name__ == '__main__':
    main()
