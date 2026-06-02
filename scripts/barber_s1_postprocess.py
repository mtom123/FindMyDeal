"""
Barber S1 — Post-processing: filtro venue non-barber/hair, fix città, dedup.
Da eseguire dopo completamento barber_s1_treatwell.py.
"""
import csv, os, sys, re
from collections import defaultdict

BASE   = os.path.join(os.path.dirname(__file__), '..', 'raw_sources')
INFILE_V = os.path.join(BASE, 'barber_s1_treatwell_venues.csv')
INFILE_I = os.path.join(BASE, 'barber_s1_menu_items.csv')
OUT_V    = os.path.join(BASE, 'barber_s1_master_venues.csv')
OUT_I    = os.path.join(BASE, 'barber_s1_master_items.csv')

# Products that confirm a venue is barber/hair
BARBER_HAIR_PRODUCTS = {
    'haircut_man','haircut_woman','haircut_child',
    'beard_trim','beard_shave','beard_color',
    'hair_color','hair_highlight','hair_bleach','hair_toning',
    'hair_wash_blowdry','hair_blowdry','hair_treatment',
    'hair_perm','hair_straightening','hair_extensions','hair_updo',
    'eyebrow_trim',
    'package_cut_beard','package_color_cut','package_full_treatment',
}

# Additional keyword filter on venue name / item names
BARBER_KEYWORDS = re.compile(
    r'\b(barbier|barber|parrucchier|salone|capell|hair|taglio|piega|coloraz|tinta|'
    r'shampoo|mèche|balayage|barba|beard|cheratina|extension|permanente)\b',
    re.I
)

def is_barber_venue(venue, venue_items):
    # Check if any item has a barber/hair product code
    for it in venue_items:
        if it.get('normalized_product') in BARBER_HAIR_PRODUCTS:
            return True
    # Check venue name keywords
    name = venue.get('venue_name', '')
    if BARBER_KEYWORDS.search(name):
        return True
    # Check item names
    for it in venue_items:
        if BARBER_KEYWORDS.search(it.get('item_name', '')):
            return True
    return False

def main():
    print("Loading raw data…")
    venues = list(csv.DictReader(open(INFILE_V, encoding='utf-8')))
    items  = list(csv.DictReader(open(INFILE_I, encoding='utf-8')))
    print(f"Raw: {len(venues)} venues, {len(items)} items")

    # Group items by venue slug
    items_by_slug = defaultdict(list)
    for it in items:
        items_by_slug[it['source_venue_id']].append(it)

    # Dedup venues by slug (keep last)
    seen_slugs = {}
    for v in venues:
        seen_slugs[v['source_venue_id']] = v
    deduped_venues = list(seen_slugs.values())
    print(f"After dedup: {len(deduped_venues)} venues")

    # Filter to barber/hair only
    barber_venues = []
    barber_slugs  = set()
    for v in deduped_venues:
        slug  = v['source_venue_id']
        vitems = items_by_slug.get(slug, [])
        if is_barber_venue(v, vitems):
            barber_venues.append(v)
            barber_slugs.add(slug)

    barber_items = [it for it in items if it['source_venue_id'] in barber_slugs]

    print(f"Barber/hair venues: {len(barber_venues)} ({len(barber_venues)/len(deduped_venues)*100:.1f}%)")
    print(f"Barber/hair items: {len(barber_items)}")

    priced_v = len(set(it['source_venue_id'] for it in barber_items if float(it.get('normalized_price_eur') or 0) > 0))
    priced_i = sum(1 for it in barber_items if float(it.get('normalized_price_eur') or 0) > 0)
    print(f"Priced venues: {priced_v} | Priced items: {priced_i}")

    # City breakdown
    cities = {}
    for v in barber_venues:
        c = v.get('city') or 'unknown'
        cities[c] = cities.get(c, 0) + 1
    top_c = sorted(cities.items(), key=lambda x: -x[1])[:20]
    print("\nTop cities:")
    for c, n in top_c:
        print(f"  {c}: {n}")

    # Product breakdown
    prods = {}
    for it in barber_items:
        p = it.get('normalized_product') or 'unclassified'
        prods[p] = prods.get(p, 0) + 1
    print("\nTop products:")
    for p, n in sorted(prods.items(), key=lambda x: -x[1])[:15]:
        print(f"  {p}: {n}")

    # Write output
    fieldnames_v = list(venues[0].keys()) if venues else []
    fieldnames_i = list(items[0].keys()) if items else []
    with open(OUT_V, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=fieldnames_v, extrasaction='ignore')
        w.writeheader(); w.writerows(barber_venues)
    with open(OUT_I, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=fieldnames_i, extrasaction='ignore')
        w.writeheader(); w.writerows(barber_items)

    print(f"\nOutputs:")
    print(f"  {OUT_V}")
    print(f"  {OUT_I}")

if __name__ == '__main__':
    main()
