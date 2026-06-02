#!/usr/bin/env python3
"""Pulizia barber_data.json:
  1. Rimuove venue non-parrucchieri (solo servizi beauty ambigui + nome non-hair).
  2. Assegna la regione mancante via point-in-polygon (italy_regions.geojson).
  3. Ricalcola tutta la metadata (categories, regions, top_cities, totali).
Backup -> barber_data.json.bak
"""
import json, re, statistics, copy
from collections import defaultdict, Counter

BASE = '/Users/g_giaimo02/Desktop/TTW/FindMyDeal/data'

data = json.load(open(f'{BASE}/barber_data.json'))
gj   = json.load(open(f'{BASE}/italy_regions.geojson'))
V    = data['venues']
meta = data['metadata']
n0   = len(V)

# ── 1. FILTRO non-hair ────────────────────────────────────────────────
REAL_HAIR = {'haircut_man','haircut_woman','haircut_child','beard_trim','beard_shave',
             'beard_color','hair_color','hair_highlight','hair_toning','hair_bleach',
             'hair_blowdry','hair_updo','hair_straightening','hair_perm','hair_extensions',
             'hair_wash_blowdry','package_cut_beard','package_color_cut'}
HAIR_NAME = re.compile(r'barber|barbier|parrucch|hair|coiffeur|coiffure|capelli|\btagli|'
                       r'hairstyl|hair styl|salone|haircut', re.I)

def keep(v):
    if set((v.get('prices') or {}).keys()) & REAL_HAIR: return True
    if HAIR_NAME.search(v.get('name','')): return True
    return False

V = [v for v in V if keep(v)]
print(f'Rimossi {n0-len(V)} venue non-hair  ({n0} -> {len(V)})')

# ── 2. REGIONE via point-in-polygon ───────────────────────────────────
def rings_of(feat):
    g = feat['geometry']; t = g['type']; c = g['coordinates']
    if t == 'Polygon':       return [c[0]]
    if t == 'MultiPolygon':  return [poly[0] for poly in c]
    return []

REGIONS = [(f['properties']['name'], rings_of(f)) for f in gj['features']]

def pip(lng, lat, ring):
    inside = False; n = len(ring); j = n-1
    for i in range(n):
        xi,yi = ring[i][0], ring[i][1]
        xj,yj = ring[j][0], ring[j][1]
        if ((yi>lat) != (yj>lat)) and (lng < (xj-xi)*(lat-yi)/(yj-yi)+xi):
            inside = not inside
        j = i
    return inside

def region_of(lat, lng):
    for name, rings in REGIONS:
        for ring in rings:
            if pip(lng, lat, ring): return name
    return ''

assigned = 0
for v in V:
    if not v.get('region') and v.get('lat') and v.get('lng'):
        r = region_of(v['lat'], v['lng'])
        if r: v['region'] = r; assigned += 1
print(f'Regione assegnata via coordinate a {assigned} venue')
still_empty = sum(1 for v in V if not v.get('region'))
print(f'Ancora senza regione (fuori dai poligoni): {still_empty}')

# ── 3. RICALCOLO METADATA ─────────────────────────────────────────────
# Preserva code/label/gender/category dalle categorie esistenti
cat_def = {c['code']: {'code':c['code'],'label':c['label'],'gender':c['gender'],
                       'category':c.get('category')} for c in meta['categories']}

def venue_min(v, code):
    p = (v.get('prices') or {}).get(code)
    return p.get('min') if p and p.get('min') is not None else None

# categorie
cat_vals = defaultdict(list)
for v in V:
    for code in (v.get('prices') or {}):
        mn = venue_min(v, code)
        if mn is not None: cat_vals[code].append(mn)

categories = []
for code, base in cat_def.items():
    vals = cat_vals.get(code, [])
    if not vals: continue
    categories.append({**base,
        'count_venues': len(vals),
        'median': round(statistics.median(vals),1),
        'min': round(min(vals),1),
        'max': round(max(vals),1)})
categories.sort(key=lambda c: -c['count_venues'])

# regioni
reg_venues = defaultdict(list)
for v in V:
    reg_venues[v.get('region') or 'Sconosciuta'].append(v)

regions = []
for name, vs in reg_venues.items():
    priced = [v for v in vs if v.get('has_price')]
    medp = {}
    code_vals = defaultdict(list)
    for v in vs:
        for code in (v.get('prices') or {}):
            mn = venue_min(v, code)
            if mn is not None: code_vals[code].append(mn)
    for code, vals in code_vals.items():
        medp[code] = round(statistics.median(vals),1)
    regions.append({'name':name,'total':len(vs),'priced':len(priced),
                    'pct':round(100*len(priced)/len(vs)) if vs else 0,
                    'median_prices':medp})
regions.sort(key=lambda r: -r['total'])

# top città
city_c = defaultdict(lambda: [0,0])
for v in V:
    c = v.get('city') or 'Sconosciuta'
    city_c[c][0]+=1
    if v.get('has_price'): city_c[c][1]+=1
top_cities = sorted([{'name':c,'total':t,'priced':p} for c,(t,p) in city_c.items()],
                    key=lambda x:-x['total'])[:50]

meta['categories'] = categories
meta['regions']    = regions
meta['top_cities'] = top_cities
meta['total_venues'] = len(V)
meta['total_priced'] = sum(1 for v in V if v.get('has_price'))
data['venues'] = V

# ── BACKUP + SAVE ─────────────────────────────────────────────────────
import shutil
shutil.copy(f'{BASE}/barber_data.json', f'{BASE}/barber_data.json.bak')
json.dump(data, open(f'{BASE}/barber_data.json','w'), ensure_ascii=False)
print(f"\nSalvato. total_venues={meta['total_venues']} total_priced={meta['total_priced']}")
print('Regioni:', ', '.join(f"{r['name']}={r['total']}" for r in regions[:8]))
