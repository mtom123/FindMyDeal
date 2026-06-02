"""
Barber S1 — Consolidation
Merge Treatwell + Fresha → unified barber master + barber_data.json (frontend)
Schema replica beach_data.json structure.

Filtri frontend:
- Primo livello: gender (man/woman/unisex)
- Secondo livello: servizio (taglio/barba/colore/piega)
- Mappa: mostra SOLO prezzi della stessa categoria selezionata
"""
import csv, json, re, os, sys
from collections import defaultdict
from math import radians, cos, sin, sqrt, atan2

BASE = os.path.join(os.path.dirname(__file__), '..')
RAW  = os.path.join(BASE, 'raw_sources')
OUT  = os.path.join(BASE, 'data')
os.makedirs(OUT, exist_ok=True)

TREATWELL_V = os.path.join(RAW, 'barber_s1_master_venues.csv')
TREATWELL_I = os.path.join(RAW, 'barber_s1_master_items.csv')
FRESHA_V    = os.path.join(RAW, 'barber_s1_fresha_master_venues.csv')
FRESHA_I    = os.path.join(RAW, 'barber_s1_fresha_master_items.csv')

UNIFIED_V       = os.path.join(RAW, 'barber_unified_venues.csv')
UNIFIED_I       = os.path.join(RAW, 'barber_unified_items.csv')
BARBER_DATA     = os.path.join(OUT, 'barber_data.json')

# ─── Region mapping (city → region) — same source as beach ────────────────────
CITY_TO_REGION = {
    # Lombardia
    'milano':'Lombardia','bergamo':'Lombardia','brescia':'Lombardia','como':'Lombardia',
    'cremona':'Lombardia','lecco':'Lombardia','lodi':'Lombardia','mantova':'Lombardia',
    'monza':'Lombardia','pavia':'Lombardia','sondrio':'Lombardia','varese':'Lombardia',
    # Lazio
    'roma':'Lazio','frosinone':'Lazio','latina':'Lazio','rieti':'Lazio','viterbo':'Lazio',
    # Campania
    'napoli':'Campania','avellino':'Campania','benevento':'Campania','caserta':'Campania','salerno':'Campania',
    # Sicilia
    'palermo':'Sicilia','agrigento':'Sicilia','caltanissetta':'Sicilia','catania':'Sicilia',
    'enna':'Sicilia','messina':'Sicilia','ragusa':'Sicilia','siracusa':'Sicilia','trapani':'Sicilia',
    # Piemonte
    'torino':'Piemonte','alessandria':'Piemonte','asti':'Piemonte','biella':'Piemonte',
    'cuneo':'Piemonte','novara':'Piemonte','vercelli':'Piemonte',
    # Veneto
    'venezia':'Veneto','padova':'Veneto','verona':'Veneto','vicenza':'Veneto','treviso':'Veneto',
    'rovigo':'Veneto','belluno':'Veneto',
    # Emilia-Romagna
    'bologna':'Emilia-Romagna','modena':'Emilia-Romagna','parma':'Emilia-Romagna',
    'reggio emilia':'Emilia-Romagna','ferrara':'Emilia-Romagna','ravenna':'Emilia-Romagna',
    'forlì':'Emilia-Romagna','forli':'Emilia-Romagna','rimini':'Emilia-Romagna','piacenza':'Emilia-Romagna',
    # Toscana
    'firenze':'Toscana','arezzo':'Toscana','grosseto':'Toscana','livorno':'Toscana','lucca':'Toscana',
    'massa':'Toscana','pisa':'Toscana','pistoia':'Toscana','prato':'Toscana','siena':'Toscana',
    # Puglia
    'bari':'Puglia','barletta':'Puglia','brindisi':'Puglia','foggia':'Puglia','lecce':'Puglia','taranto':'Puglia',
    # Calabria
    'catanzaro':'Calabria','cosenza':'Calabria','crotone':'Calabria','reggio calabria':'Calabria','vibo valentia':'Calabria',
    # Sardegna
    'cagliari':'Sardegna','sassari':'Sardegna','nuoro':'Sardegna','oristano':'Sardegna',
    # Liguria
    'genova':'Liguria','imperia':'Liguria','la spezia':'Liguria','savona':'Liguria',
    # Marche
    'ancona':'Marche','ascoli piceno':'Marche','fermo':'Marche','macerata':'Marche','pesaro':'Marche','urbino':'Marche',
    # Abruzzo
    "l'aquila":'Abruzzo','chieti':'Abruzzo','pescara':'Abruzzo','teramo':'Abruzzo',
    # Friuli-Venezia Giulia
    'trieste':'Friuli-Venezia Giulia','udine':'Friuli-Venezia Giulia','gorizia':'Friuli-Venezia Giulia','pordenone':'Friuli-Venezia Giulia',
    # Trentino-Alto Adige
    'trento':'Trentino-Alto Adige','bolzano':'Trentino-Alto Adige',
    # Umbria
    'perugia':'Umbria','terni':'Umbria',
    # Molise
    'campobasso':'Molise','isernia':'Molise',
    # Basilicata
    'potenza':'Basilicata','matera':'Basilicata',
    # Valle d'Aosta
    'aosta':"Valle d'Aosta",
}

# ─── Service taxonomy for frontend ────────────────────────────────────────────
# Primo filtro: gender; secondo filtro: categoria servizio
# Per ogni servizio, mappiamo a gender + category
SERVICE_TAXONOMY = {
    # code: {gender: [...], category: 'taglio'|'barba'|'colore'|'piega'|'trattamento'|'altro'}
    'haircut_man':           {'gender': ['man'],         'category': 'taglio'},
    'haircut_woman':         {'gender': ['woman'],       'category': 'taglio'},
    'haircut_child':         {'gender': ['child'],       'category': 'taglio'},
    'beard_trim':            {'gender': ['man'],         'category': 'barba'},
    'beard_shave':           {'gender': ['man'],         'category': 'barba'},
    'beard_color':           {'gender': ['man'],         'category': 'barba'},
    'hair_color':            {'gender': ['woman','man'], 'category': 'colore'},
    'hair_highlight':        {'gender': ['woman'],       'category': 'colore'},
    'hair_bleach':           {'gender': ['woman','man'], 'category': 'colore'},
    'hair_toning':           {'gender': ['woman','man'], 'category': 'colore'},
    'hair_wash_blowdry':     {'gender': ['woman'],       'category': 'piega'},
    'hair_blowdry':          {'gender': ['woman'],       'category': 'piega'},
    'hair_treatment':        {'gender': ['woman','man'], 'category': 'trattamento'},
    'hair_perm':             {'gender': ['woman'],       'category': 'piega'},
    'hair_straightening':    {'gender': ['woman'],       'category': 'piega'},
    'hair_extensions':       {'gender': ['woman'],       'category': 'altro'},
    'hair_updo':             {'gender': ['woman'],       'category': 'piega'},
    'eyebrow_trim':          {'gender': ['woman','man'], 'category': 'altro'},
    'package_cut_beard':     {'gender': ['man'],         'category': 'taglio'},
    'package_color_cut':     {'gender': ['woman'],       'category': 'colore'},
    'package_full_treatment':{'gender': ['woman','man'], 'category': 'trattamento'},
}

SERVICE_LABEL = {
    'haircut_man':           'Taglio Uomo',
    'haircut_woman':         'Taglio Donna',
    'haircut_child':         'Taglio Bambino',
    'beard_trim':            'Rifilatura Barba',
    'beard_shave':           'Rasatura',
    'beard_color':           'Colore Barba',
    'hair_color':            'Colore Capelli',
    'hair_highlight':        'Mèches / Colpi di Sole',
    'hair_bleach':           'Decolorazione',
    'hair_toning':           'Tonalizzazione',
    'hair_wash_blowdry':     'Lavaggio + Piega',
    'hair_blowdry':          'Piega',
    'hair_treatment':        'Trattamento',
    'hair_perm':             'Permanente',
    'hair_straightening':    'Stiratura',
    'hair_extensions':       'Extension',
    'hair_updo':             'Acconciatura',
    'eyebrow_trim':          'Sopracciglia',
    'package_cut_beard':     'Pacchetto Taglio+Barba',
    'package_color_cut':     'Pacchetto Colore+Taglio',
    'package_full_treatment':'Trattamento Completo',
}

# ─── City normalization ───────────────────────────────────────────────────────

def normalize_city(c):
    if not c: return ''
    c = c.strip()
    # "Milano MI" → "Milano", "Milano (MI)" → "Milano", "milano" → "Milano"
    c = re.sub(r'\s*\(?\s*[A-Z]{2}\)?\s*$', '', c)
    c = re.sub(r',?\s*Italia\s*$', '', c, flags=re.I)
    c = c.strip()
    # special common typos
    if c.lower() == 'italy' or c.lower() == 'it': return ''
    return c

def region_for_city(city):
    if not city: return ''
    return CITY_TO_REGION.get(city.lower(), '')

# ─── Geo dedup ────────────────────────────────────────────────────────────────

def haversine_m(a, b):
    """meters between (lat,lon) pairs."""
    R = 6371000
    lat1, lon1, lat2, lon2 = map(radians, [a[0], a[1], b[0], b[1]])
    dlat, dlon = lat2-lat1, lon2-lon1
    h = sin(dlat/2)**2 + cos(lat1)*cos(lat2)*sin(dlon/2)**2
    return 2*R*atan2(sqrt(h), sqrt(1-h))

def slugify(s):
    return re.sub(r'\W+', '', (s or '').lower())

def merge_venues(venues_list):
    """Dedup venues across sources by geo proximity (≤80m) + name similarity."""
    by_grid = defaultdict(list)
    # grid cells of ~100m
    for v in venues_list:
        try:
            lat = float(v.get('latitude') or 0)
            lon = float(v.get('longitude') or 0)
        except Exception:
            continue
        if lat == 0 or lon == 0:
            continue
        cell = (round(lat*1000), round(lon*1000))
        by_grid[cell].append((lat, lon, v))

    merged = []
    seen   = set()
    for cell, items in by_grid.items():
        # neighbors: check current + 8 surrounding cells
        for i, (lat, lon, v) in enumerate(items):
            vid = id(v)
            if vid in seen: continue
            seen.add(vid)
            group = [v]
            v_name_slug = slugify(v.get('venue_name',''))
            # scan same cell + 8 neighbors
            for dy in (-1,0,1):
                for dx in (-1,0,1):
                    neighbors = by_grid.get((cell[0]+dy, cell[1]+dx), [])
                    for lat2, lon2, v2 in neighbors:
                        if id(v2) in seen: continue
                        if haversine_m((lat,lon),(lat2,lon2)) > 80: continue
                        # name similarity (slug match or substring)
                        n2 = slugify(v2.get('venue_name',''))
                        if v_name_slug and n2 and (v_name_slug in n2 or n2 in v_name_slug):
                            group.append(v2)
                            seen.add(id(v2))
            merged.append(group)
    # add venues without geo as standalone
    for v in venues_list:
        if id(v) in seen: continue
        merged.append([v])
    return merged

# ─── Load CSVs ────────────────────────────────────────────────────────────────

def load_csv(path):
    if not os.path.exists(path):
        return []
    with open(path, newline='', encoding='utf-8') as f:
        return list(csv.DictReader(f))

def main():
    print("Loading…")
    tw_v = load_csv(TREATWELL_V); tw_i = load_csv(TREATWELL_I)
    fr_v = load_csv(FRESHA_V);    fr_i = load_csv(FRESHA_I)
    print(f"  Treatwell: {len(tw_v)} venues, {len(tw_i)} items")
    print(f"  Fresha:    {len(fr_v)} venues, {len(fr_i)} items")

    all_venues = tw_v + fr_v
    all_items  = tw_i + fr_i

    # Normalize city
    for v in all_venues:
        v['city']   = normalize_city(v.get('city',''))
        v['region'] = region_for_city(v['city'])

    # Index items by slug
    items_by_slug = defaultdict(list)
    for it in all_items:
        items_by_slug[it['source_venue_id']].append(it)

    # Dedup
    print("Deduplicating…")
    groups = merge_venues(all_venues)
    print(f"  Groups: {len(groups)} (from {len(all_venues)} raw)")

    # Build canonical venues
    canonical = []
    for grp in groups:
        # Pick venue with most items as canonical
        best = max(grp, key=lambda v: len(items_by_slug.get(v['source_venue_id'], [])))
        sources       = sorted({v['source_platform'] for v in grp})
        slugs_in_grp  = [v['source_venue_id'] for v in grp]
        items_all     = []
        for s in slugs_in_grp:
            items_all.extend(items_by_slug.get(s, []))
        # Dedup items within group (same item_name + same price)
        seen = set()
        items_dedup = []
        for it in items_all:
            key = (slugify(it.get('item_name','')), str(it.get('normalized_price_eur','')))
            if key in seen: continue
            seen.add(key)
            items_dedup.append(it)

        venue_canonical = dict(best)
        venue_canonical['source_platforms'] = ','.join(sources)
        venue_canonical['merged_slugs']     = ','.join(slugs_in_grp)
        venue_canonical['n_items']          = len(items_dedup)
        venue_canonical['n_items_priced']   = sum(1 for it in items_dedup if float(it.get('normalized_price_eur') or 0) > 0)
        canonical.append((venue_canonical, items_dedup))

    print(f"  Canonical venues: {len(canonical)}")

    # ─── Write unified CSVs ──
    if canonical:
        venue_fields = list(canonical[0][0].keys())
        with open(UNIFIED_V, 'w', newline='', encoding='utf-8') as f:
            w = csv.DictWriter(f, fieldnames=venue_fields, extrasaction='ignore')
            w.writeheader()
            for v, _ in canonical:
                w.writerow(v)
        item_fields = list(canonical[0][1][0].keys()) if canonical[0][1] else []
        with open(UNIFIED_I, 'w', newline='', encoding='utf-8') as f:
            w = csv.DictWriter(f, fieldnames=item_fields, extrasaction='ignore')
            w.writeheader()
            for _, items in canonical:
                w.writerows(items)
        print(f"  Wrote {UNIFIED_V}")
        print(f"  Wrote {UNIFIED_I}")

    # ─── Build barber_data.json (frontend) ──
    print("\nBuilding barber_data.json…")
    venues_json = []
    for v, items in canonical:
        try:
            lat = float(v.get('latitude') or 0)
            lon = float(v.get('longitude') or 0)
        except Exception:
            continue
        if lat == 0 or lon == 0:
            continue

        # Build prices by (gender, service_code, category)
        # prices_by_service: { service_code: {min_price, items: [...]}}
        prices = defaultdict(lambda: {'min_price': None, 'items': []})
        for it in items:
            code = it.get('normalized_product')
            if not code or code not in SERVICE_TAXONOMY:
                continue
            try:
                p = float(it.get('normalized_price_eur') or 0)
            except Exception:
                p = 0
            if p <= 0:
                continue
            prices[code]['items'].append({
                'name':   it.get('item_name', ''),
                'price':  p,
                'source': it.get('source_platform', ''),
            })
            if prices[code]['min_price'] is None or p < prices[code]['min_price']:
                prices[code]['min_price'] = p

        if not prices:
            # Still include in venue list (no price), but won't show on map by default
            has_price = False
        else:
            has_price = True

        # Compute gender flags
        genders_avail = set()
        for code in prices.keys():
            for g in SERVICE_TAXONOMY[code]['gender']:
                genders_avail.add(g)

        venue_obj = {
            'id':            v['source_venue_id'],
            'name':          v.get('venue_name', ''),
            'lat':           lat,
            'lng':           lon,
            'city':          v.get('city', ''),
            'region':        v.get('region', ''),
            'address':       v.get('address', ''),
            'url':           v.get('venue_url', ''),
            'rating':        v.get('rating', ''),
            'rating_count':  v.get('rating_count', ''),
            'barber_category': v.get('barber_category', 'unisex'),
            'genders':       sorted(genders_avail),
            'source_platforms': v.get('source_platforms', v.get('source_platform','')),
            'has_price':     has_price,
            'n_priced_items': sum(len(p['items']) for p in prices.values()),
        }
        if has_price:
            # Add prices object: { service_code: {min, label, gender, category, items_count} }
            venue_obj['prices'] = {
                code: {
                    'min':      p['min_price'],
                    'label':    SERVICE_LABEL.get(code, code),
                    'gender':   SERVICE_TAXONOMY[code]['gender'],
                    'category': SERVICE_TAXONOMY[code]['category'],
                    'items':    p['items'][:10],   # cap per-venue items
                } for code, p in prices.items()
            }
            # Convenience: min price overall
            venue_obj['min_price'] = min(p['min_price'] for p in prices.values())

        venues_json.append(venue_obj)

    # ─── Statistics (regions, categories) for sidebar ──
    by_region = defaultdict(lambda: {'total':0,'priced':0,'prices_by_service':defaultdict(list)})
    by_city   = defaultdict(lambda: {'total':0,'priced':0})
    for v in venues_json:
        r = v['region'] or 'Altro'
        c = v['city'] or 'Sconosciuta'
        by_region[r]['total']  += 1
        by_city[c]['total']    += 1
        if v.get('has_price'):
            by_region[r]['priced']  += 1
            by_city[c]['priced']    += 1
            for code, pdata in v['prices'].items():
                by_region[r]['prices_by_service'][code].append(pdata['min'])

    regions_meta = []
    for region, agg in sorted(by_region.items(), key=lambda x:-x[1]['total']):
        medians = {}
        for code, vals in agg['prices_by_service'].items():
            if vals:
                vals.sort()
                medians[code] = vals[len(vals)//2]
        regions_meta.append({
            'name':    region,
            'total':   agg['total'],
            'priced':  agg['priced'],
            'pct':     round(agg['priced']/agg['total']*100) if agg['total'] else 0,
            'median_prices': medians,
        })

    cities_meta = [
        {'name': c, 'total': a['total'], 'priced': a['priced']}
        for c, a in sorted(by_city.items(), key=lambda x:-x[1]['total'])[:50]
    ]

    # Categories meta — service codes available with overall medians
    cat_meta = []
    for code, taxonomy in SERVICE_TAXONOMY.items():
        all_prices = []
        for v in venues_json:
            if v.get('has_price') and code in v.get('prices', {}):
                all_prices.append(v['prices'][code]['min'])
        if not all_prices: continue
        all_prices.sort()
        cat_meta.append({
            'code':     code,
            'label':    SERVICE_LABEL.get(code, code),
            'gender':   taxonomy['gender'],
            'category': taxonomy['category'],
            'count_venues': len(all_prices),
            'median':   round(all_prices[len(all_prices)//2], 1),
            'min':      round(all_prices[0], 1),
            'max':      round(all_prices[-1], 1),
        })
    # sort by venue count
    cat_meta.sort(key=lambda x: -x['count_venues'])

    metadata = {
        'generated_at':       '2026-06-02',
        'total_venues':       len(venues_json),
        'total_priced':       sum(1 for v in venues_json if v.get('has_price')),
        'sources':            ['treatwell','fresha'],
        'regions':            regions_meta,
        'top_cities':         cities_meta,
        'categories':         cat_meta,
        'gender_filters':     ['man','woman','child'],
        'service_categories': ['taglio','barba','colore','piega','trattamento','altro'],
    }

    out = {'metadata': metadata, 'venues': venues_json}
    with open(BARBER_DATA, 'w', encoding='utf-8') as f:
        json.dump(out, f, ensure_ascii=False, separators=(',',':'))
    print(f"  Wrote {BARBER_DATA}  ({os.path.getsize(BARBER_DATA)//1024} KB)")

    # ─── Summary ──
    print("\n=== CONSOLIDATION SUMMARY ===")
    print(f"  Raw venues (TW+FR):  {len(all_venues)}")
    print(f"  Canonical venues:    {len(canonical)}")
    print(f"  In JSON (geo OK):    {len(venues_json)}")
    print(f"  Priced venues:       {sum(1 for v in venues_json if v.get('has_price'))}")
    print(f"  Total regions:       {len(regions_meta)}")
    print(f"  Top services:")
    for c in cat_meta[:10]:
        print(f"    {c['label']}: {c['count_venues']} venues, median €{c['median']}")
    print(f"\n  Top 8 cities:")
    for c in cities_meta[:8]:
        print(f"    {c['name']}: {c['total']} venues ({c['priced']} prezzati)")

if __name__ == '__main__':
    main()
