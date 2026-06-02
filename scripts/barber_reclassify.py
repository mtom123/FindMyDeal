#!/usr/bin/env python3
"""Ri-classificazione accurata degli item del database haircut.
Opera sui nomi reali degli item: scarta non-capelli (unghie, ceretta, trucco,
viso/corpo, ciglia...), separa piega/taglio/colore, ricostruisce i bucket prezzo,
rimuove i venue non-parrucchieri, ricalcola la metadata.
Backup -> barber_data.json.bak2
"""
import json, re, statistics, shutil
from collections import defaultdict

BASE = '/Users/g_giaimo02/Desktop/TTW/FindMyDeal/data'
data = json.load(open(f'{BASE}/barber_data.json'))
V, meta = data['venues'], data['metadata']

def norm(s): return (s or '').lower().strip()

# ── EXCLUDE: servizi NON capelli ──────────────────────────────────────
EXCLUDE = re.compile(
    r'unghi|manicure|pedicure|\bnail|smalt|semipermanent|ricostruzione ungh|press[- ]?on|'
    r'ceretta|\bcera\b|epilaz|depilaz|\blaser|luce pulsata|\bbaffett|brasilian|inguine|ascell|'
    r'\bviso\b|\bcorpo\b|massagg|peeling|pressoterap|linfodren|\bfango|scrub|abbronz|solarium|'
    r'cellulit|smagliat|radiofreq|cavitazion|pulizia del viso|acido|filler labbr|'
    r'\btrucco|make[ -]?up|makeup|cerimonia|'
    r'cigli|tatuagg|piercing|foratur|microblad|dermopigment|'
    r'manucure|\bspa\b|sauna|bagno turco|idromassagg|doccia solare|'
    r'osteopat|fisioterap|posturolog|nutrizion|podolog'
)

# ── classificatore servizio capelli ──────────────────────────────────
def reclassify(name, orig_code):
    n = norm(name)
    # sopracciglia PRIMA dell'esclusione "ciglia"
    if re.search(r'sopraccigli', n):
        return 'eyebrow_trim'
    if EXCLUDE.search(n):
        return None
    has_taglio = bool(re.search(r'\btagli|haircut|\bcut\b|rasoio|sfoltitur|spuntatin|capelli corti', n))
    has_barba  = bool(re.search(r'\bbarba\b|baffi|rasatura', n))
    has_colore = bool(re.search(r'\bcolore|tinta|colorazion|tintur', n))
    # pacchetti (combo)
    if has_taglio and has_barba:                      return 'package_cut_beard'
    if has_taglio and has_colore:                     return 'package_color_cut'
    # barba
    if has_barba:
        if re.search(r'rasatur', n):                  return 'beard_shave'
        if re.search(r'color|tinta', n):              return 'beard_color'
        return 'beard_trim'
    # colore / mech / toning / decolor
    if re.search(r'mech|m[èe]ches|colpi di sole|balayage|shatush|degrad|baby ?lights', n):
        return 'hair_highlight'
    if re.search(r'decolora|bleach|biondo platino|super schiarit', n):
        return 'hair_bleach'
    if re.search(r'tonalizz|riflessant|\bgloss|\btoner\b|cristalli liquidi', n):
        return 'hair_toning'
    if has_colore:                                    return 'hair_color'
    # styling / trattamenti / forme
    if re.search(r'extension|allungament|infoltiment|cheratina brasil', n):
        return 'hair_extensions'
    if re.search(r'permanent|\bboccoli|ondulaz|arricciat', n):
        return 'hair_perm'
    if re.search(r'stirat|liscia|lisciant|cheratina|keratin', n):
        return 'hair_straightening'
    if re.search(r'acconciatur|raccolt|chignon|messa in opera', n):
        return 'hair_updo'
    if re.search(r'lavaggio.*piega|shampoo.*piega', n):
        return 'hair_wash_blowdry'
    if re.search(r'piega|brushing|messa in piega|asciugatur|styling|phon', n):
        return 'hair_blowdry'
    if re.search(r'trattament|ricostruzion|maschera|impacc|cauteriz|botox|\bfiller|fial|ristruttur|olaplex|hair ?spa', n):
        return 'hair_treatment'
    # taglio (capelli) — usa il genere esplicito o quello del bucket originale
    if has_taglio:
        if re.search(r'\buomo|uomini|\bman\b|maschi|barbie', n):      return 'haircut_man'
        if re.search(r'donna|signora|femmin|\blady|\bwoman', n):      return 'haircut_woman'
        if re.search(r'bimb|bambin|baby|junior|\bkids|child|ragazz|b[eè]b[eè]', n): return 'haircut_child'
        if orig_code in ('haircut_man','haircut_woman','haircut_child'): return orig_code
        return 'haircut_man'   # generico (es. barbershop "Taglio")
    return None  # non riconosciuto come servizio capelli -> scarta

# ── ricostruzione prezzi per venue ────────────────────────────────────
cat_def = {c['code']: c for c in meta['categories']}
GENDER_OF = {c['code']: c['gender'] for c in meta['categories']}

def rebuild(v):
    buckets = defaultdict(list)
    for code, p in (v.get('prices') or {}).items():
        for it in p.get('items', []):
            nc = reclassify(it.get('name',''), code)
            if nc and it.get('price') is not None:
                buckets[nc].append(it)
    prices = {}
    for code, items in buckets.items():
        mn = min(i['price'] for i in items)
        prices[code] = {'min': mn, 'label': cat_def.get(code,{}).get('label',code),
                        'gender': GENDER_OF.get(code, []), 'category': cat_def.get(code,{}).get('category'),
                        'items': sorted(items, key=lambda i:i['price'])}
    return prices

# ── keep: è un parrucchiere/barbiere? ─────────────────────────────────
REAL_HAIR = {'haircut_man','haircut_woman','haircut_child','beard_trim','beard_shave',
             'beard_color','hair_color','hair_highlight','hair_toning','hair_bleach',
             'hair_blowdry','hair_updo','hair_straightening','hair_perm','hair_extensions',
             'hair_wash_blowdry','package_cut_beard','package_color_cut'}
HAIR_NAME = re.compile(r'barber|barbier|parrucch|hair|coiffeur|coiffure|capelli|\btagli|hairstyl|salone|haircut', re.I)
HAIR_TOKEN = re.compile(r'parrucch|barbier|barber|\bhair\b|capelli|coiffeur|coiffure', re.I)
STRONG_BEAUTY = re.compile(r'centro estetico|estetica avanzata|\bnail|\bunghie|solarium|'
                           r'istituto di bellezza|beauty center|centro benessere|profumeria', re.I)
MEN_SVC = {'haircut_man','beard_trim','beard_shave','beard_color','package_cut_beard'}

def keep(v, prices):
    codes = set(prices.keys())
    real  = codes & REAL_HAIR
    name  = v.get('name','')
    # centro estetico esplicito, senza servizi uomo e senza token capelli -> rimuovi
    if STRONG_BEAUTY.search(name) and not (codes & MEN_SVC) and not HAIR_TOKEN.search(name):
        return False
    if real: return True
    if HAIR_NAME.search(name): return True
    return False

# ── TEST sui casi citati ──────────────────────────────────────────────
print('=== TEST casi citati ===')
for needle in ['Barbitta','Parrucchieria Luca','Centro Estetico Elle','L\'Aura Estetica']:
    for v in V:
        if needle.lower() in v.get('name','').lower():
            pr = rebuild(v)
            k = keep(v, pr)
            print("\n" + v['name'] + "  -> keep=" + str(k))
            for code,p in pr.items():
                print("   [" + code + "] EUR" + str(p["min"]) + "  (" + str(len(p["items"])) + " item)")
            break

# ── PROCESSING completo ───────────────────────────────────────────────
GENDER_FROM_CODE = {c['code']: c['gender'] for c in meta['categories']}
out = []
for v in V:
    pr = rebuild(v)
    if not keep(v, pr): continue
    v['prices'] = pr
    v['has_price'] = bool(pr)
    v['n_priced_items'] = sum(len(p['items']) for p in pr.values())
    v['min_price'] = min((p['min'] for p in pr.values()), default=None)
    genders = set()
    for code in pr: genders.update(GENDER_FROM_CODE.get(code, []))
    v['genders'] = sorted(genders)
    out.append(v)

n0 = len(V)
V = out
print(f"\nVenue: {n0} -> {len(V)}  (rimossi {n0-len(V)})")

# ── RICALCOLO METADATA ────────────────────────────────────────────────
cat_base = {c['code']: {'code':c['code'],'label':c['label'],'gender':c['gender'],
                        'category':c.get('category')} for c in meta['categories']}
cat_vals = defaultdict(list)
for v in V:
    for code, p in v['prices'].items():
        if p['min'] is not None: cat_vals[code].append(p['min'])
categories = []
for code, base in cat_base.items():
    vals = cat_vals.get(code, [])
    if not vals: continue
    categories.append({**base, 'count_venues':len(vals),
        'median':round(statistics.median(vals),1),
        'min':round(min(vals),1), 'max':round(max(vals),1)})
categories.sort(key=lambda c:-c['count_venues'])

reg_v = defaultdict(list)
for v in V: reg_v[v.get('region') or 'Sconosciuta'].append(v)
regions = []
for name, vs in reg_v.items():
    priced=[v for v in vs if v.get('has_price')]
    code_vals=defaultdict(list)
    for v in vs:
        for code,p in v['prices'].items():
            if p['min'] is not None: code_vals[code].append(p['min'])
    medp={code:round(statistics.median(x),1) for code,x in code_vals.items()}
    regions.append({'name':name,'total':len(vs),'priced':len(priced),
                    'pct':round(100*len(priced)/len(vs)) if vs else 0,'median_prices':medp})
regions.sort(key=lambda r:-r['total'])

city_c=defaultdict(lambda:[0,0])
for v in V:
    c=v.get('city') or 'Sconosciuta'; city_c[c][0]+=1
    if v.get('has_price'): city_c[c][1]+=1
top_cities=sorted([{'name':c,'total':t,'priced':p} for c,(t,p) in city_c.items()],
                  key=lambda x:-x['total'])[:50]

meta['categories']=categories; meta['regions']=regions; meta['top_cities']=top_cities
meta['total_venues']=len(V); meta['total_priced']=sum(1 for v in V if v.get('has_price'))
data['venues']=V

shutil.copy(f'{BASE}/barber_data.json', f'{BASE}/barber_data.json.bak2')
json.dump(data, open(f'{BASE}/barber_data.json','w'), ensure_ascii=False)
print(f"\nSalvato. total_venues={meta['total_venues']} total_priced={meta['total_priced']}")
print('Categorie:', ', '.join(f"{c['code']}={c['count_venues']}(med{c['median']})" for c in categories[:6]))
