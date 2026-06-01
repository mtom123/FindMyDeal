"""
Costruisce unified_venues_no_price.csv:
- Venues nel DB drink SENZA price (1.441)
- + Venues CKAN enriched OSM (3.804 totali, 2.970 con nome commerciale)
- + Venues eatbu agent_ceo (11)
- Tutti con vertical=drink_no_price, geo precise, addr, venue_type

Output frontend-ready per pin "Prezzo non disponibile — Contribuisci".
"""
import csv, re
from pathlib import Path
from collections import Counter
from datetime import datetime

REPO = Path("C:/Users/motti/Desktop/FindMyDeal")

# 1) Venues con prezzo (li escludo)
priced_names = set()
with open(REPO / "unified_prices.csv", encoding='utf-8-sig') as f:
    for r in csv.DictReader(f):
        priced_names.add((r['venue_name'] or '').lower().strip())
print(f"Priced venues: {len(priced_names)}")

# 2) Venues DB SENZA prezzo
db_no_price = []
with open(REPO / "unified_venues.csv", encoding='utf-8-sig') as f:
    for v in csv.DictReader(f):
        name = (v.get('venue_name','') or '').lower().strip()
        if name and name not in priced_names and v.get('latitude'):
            try:
                lat = float(v['latitude']); lng = float(v['longitude'])
                if 45.39 <= lat <= 45.54 and 9.04 <= lng <= 9.28:
                    db_no_price.append({
                        'source': 'unified_db',
                        'venue_name': v['venue_name'],
                        'address': v.get('address',''),
                        'city': 'Milano',
                        'latitude': lat,
                        'longitude': lng,
                        'venue_type': '',
                        'phone': v.get('phone',''),
                        'website': v.get('website',''),
                        'nil_quartiere': '',
                        'all_names': v.get('all_names',''),
                    })
            except: pass
print(f"DB venues no-price (geo, in bbox Milano): {len(db_no_price)}")

# 3) CKAN enriched
ckan = []
with open(REPO / "website" / "raw_sources" / "ckan_milano_drink_venues_no_price.csv", encoding='utf-8-sig') as f:
    for v in csv.DictReader(f):
        try:
            lat = float(v['latitude']); lng = float(v['longitude'])
        except: continue
        if not (45.39 <= lat <= 45.54 and 9.04 <= lng <= 9.28):
            continue
        name = v.get('venue_name','').strip()
        # Skip se name è generico "Bar Via X" e non c'è match OSM
        if v.get('_match_method') == 'unmatched' and name.startswith('Bar VIA'):
            # Skip — senza nome commerciale è troppo generico
            continue
        ckan.append({
            'source': 'ckan_milano',
            'venue_name': name,
            'address': v.get('address',''),
            'city': 'Milano',
            'latitude': lat,
            'longitude': lng,
            'venue_type': v.get('venue_type',''),
            'phone': v.get('phone',''),
            'website': v.get('website',''),
            'nil_quartiere': v.get('nil_quartiere',''),
            'all_names': '',
            'osm_amenity': v.get('_osm_amenity',''),
        })
print(f"CKAN enriched (matched OSM, in bbox): {len(ckan)}")

# 4) eatbu agent_ceo
eatbu_ceo = []
with open(REPO / "website" / "raw_sources" / "agent_ceo_eatbu_metadata.csv", encoding='utf-8-sig') as f:
    for v in csv.DictReader(f):
        try:
            lat = float(v['latitude']); lng = float(v['longitude'])
            eatbu_ceo.append({
                'source': 'eatbu_metadata',
                'venue_name': v['venue_name'],
                'address': v.get('address',''),
                'city': 'Milano',
                'latitude': lat,
                'longitude': lng,
                'venue_type': '',
                'phone': '',
                'website': v.get('venue_url',''),
                'nil_quartiere': '',
                'all_names': '',
            })
        except: pass
print(f"eatbu CEO metadata: {len(eatbu_ceo)}")

# Dedup cross-source per nome normalizzato + geo proximity
def norm(s):
    return re.sub(r'[^a-z0-9]', '', (s or '').lower())[:30]

all_venues = db_no_price + ckan + eatbu_ceo
print(f"\nTotale pre-dedup: {len(all_venues)}")

# Dedup per nome + lat round(3)
seen = set()
deduped = []
duplicates_count = 0
for v in all_venues:
    n = norm(v['venue_name'])
    if not n or len(n) < 3:
        continue
    key = (n, round(v['latitude'], 3), round(v['longitude'], 3))
    if key in seen:
        duplicates_count += 1
        continue
    seen.add(key)
    deduped.append(v)
print(f"Dopo dedup: {len(deduped)} (rimossi {duplicates_count} dupes)")

# Stats
sources = Counter(v['source'] for v in deduped)
types = Counter(v.get('venue_type','') for v in deduped if v.get('venue_type'))
quartieri = Counter(v.get('nil_quartiere','') for v in deduped if v.get('nil_quartiere'))
print(f"\nFonti: {dict(sources)}")
print(f"Top venue_types: {dict(types.most_common(5))}")
print(f"Top quartieri: {dict(quartieri.most_common(5))}")

# Output
FIELDS = ['source','venue_name','address','city','latitude','longitude',
          'venue_type','phone','website','nil_quartiere','all_names','osm_amenity']
with open(REPO / "unified_venues_no_price.csv", 'w', encoding='utf-8-sig', newline='') as f:
    w = csv.DictWriter(f, fieldnames=FIELDS, extrasaction='ignore')
    w.writeheader()
    w.writerows(deduped)

# Salva anche nel website/data per il frontend
with open(REPO / "website" / "data" / "unified_venues_no_price.csv", 'w', encoding='utf-8-sig', newline='') as f:
    w = csv.DictWriter(f, fieldnames=FIELDS, extrasaction='ignore')
    w.writeheader()
    w.writerows(deduped)

print(f"\nOK. Output: unified_venues_no_price.csv ({len(deduped)} venues)")
print(f"  - website/data/unified_venues_no_price.csv")
print(f"  - C:/Users/motti/Desktop/FindMyDeal/unified_venues_no_price.csv")
