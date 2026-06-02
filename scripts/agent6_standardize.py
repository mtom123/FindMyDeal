#!/usr/bin/env python3
"""
Agent 6 — Standardizzazione venues drink Milano SENZA prezzo.

Scope (S6): NON cerca prezzi/venues nuove. Prende i ~1.440 venues del DB unificato
che non hanno un prezzo associato e li:
  Step 1  classifica TARGET / NO_TARGET / AMBIGUOUS_TO_REVIEW (bar vs ristoranti)
  Step 2  deduplica per nome normalizzato (canonical name + all_names)
  Step 4  categorizza per venue_type (cocktail_bar/pub/cafe/...)
  Step 6  emette CSV standardizzato (solo TARGET + AMBIGUOUS_TO_REVIEW)
  Step 7  quality gate inline (no-priced, Milano CAP, bbox, no NO_TARGET, nome pulito)

Geo (Step 3) lo fa scripts/agent6_geocode.py → agent6_geocode_fixes.csv, che questo
script rilegge per aggiornare lat/lon + geocoding_confidence.

Riusa la libreria condivisa scripts/normalization.py (is_milan_or_unknown, PRICE_RANGES).
Le funzioni di classificazione venue/venue_type sono S6-specifiche (non in normalization.py).
"""
import sys, os, csv, re, unicodedata, collections, datetime

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from normalization import is_milan_or_unknown  # libreria condivisa (NON duplicare)

ROOT = os.path.dirname(HERE)
VEN  = os.path.join(ROOT, "data", "unified_venues.csv")
PRI  = os.path.join(ROOT, "data", "unified_prices.csv")
RAW  = os.path.join(ROOT, "raw_sources")
GEOCODE_FIXES = os.path.join(RAW, "agent6_geocode_fixes.csv")
ADDR_FIXES = os.path.join(RAW, "agent6_address_fixes.csv")

OUT_NOPRICE = os.path.join(RAW, "agent6_venues_no_price.csv")
OUT_DEDUP   = os.path.join(RAW, "agent6_name_dedup.csv")

MILAN_BBOX = (45.39, 45.54, 9.04, 9.28)   # lat_lo, lat_hi, lon_lo, lon_hi
DUOMO = (45.4642, 9.1900)

# ─────────────────────────────────────────────
# Keyword sets (Step 1) — base dal prompt CEO + estensione su categorie reali
# ─────────────────────────────────────────────
# stem non sovrapposti: 'bistro' copre 'bistrot'; evitiamo doppi conteggi che creano falsi pareggi
TARGET_KEYWORDS = [
    'bar', 'pub', 'caffè', 'caffe', 'cafe', 'café', 'cafè', 'cocktail', 'bistro',
    'lounge', 'wine bar', 'enoteca', 'taproom', 'birreria', 'speakeasy', 'aperitivo',
    'rooftop', 'tap house', 'mescita',
    'nightclub', 'sala da te', 'caffetteria', 'american bar', 'vineria', 'beerhouse',
]
# nota: 'cantina'/'drink' RIMOSSI — falsi positivi (es. "Cantina Piemontese" = ristorante)
# 'pizz' copre 'pizzeria'/'pizza'; non elenchiamo entrambi
NO_TARGET_KEYWORDS = [
    'ristorante', 'sushi', 'trattoria', 'osteria', 'focacceria',
    'panini', 'panino', 'rosticceria', 'gelateria', 'pasticceria', 'tacos',
    'kebab', 'noodle', 'poke', 'hamburger', 'burger', 'tortilleria', 'ramen',
    'piadina', 'pizz', 'pollo', 'fritti', 'cremeria', 'creperia', 'crêperie',
    'fast-food', 'fast food', 'hamburgheria', 'steak', 'grill', 'bakery',
    'panetteria', 'forno', 'piadineria', 'yogurt', 'macelleria', 'friggitoria',
    'self-service', 'mensa', 'tavola calda',
]


def norm_name(s: str) -> str:
    """Nome normalizzato per matching/clustering."""
    s = unicodedata.normalize('NFD', (clean_display_name(s)).lower())
    s = ''.join(c for c in s if unicodedata.category(c) != 'Mn')   # rimuovi accenti
    s = re.sub(r'\.(it|com|net|org|bar)\b', '', s)                  # rimuovi TLD
    s = re.sub(r'[^a-z0-9]', '', s)
    return s


# Mojibake italiano comune (Mac-Roman double-encode + zero-width / smart punct)
_MOJIBAKE = {
    '√†': 'à', '√®': 'è', '√©': 'é', '√¨': 'ì', '√≤': 'ò', '√π': 'ù', '√ß': 'ç',
    '√Ä': 'Ä', '√Å': 'Á', '√â': 'É', '√ô': 'Ù',
    '‚Äô': '’', '‚Äú': '“', '‚Äù': '”', '‚Äì': '–', '‚Äî': '—', '‚Ä¶': '…',
    '‚Äã': '', '¬†': ' ', '¬∞': '°', 'Â°': '°',
}


def fix_mojibake(s: str) -> str:
    if not s:
        return s
    for bad, good in _MOJIBAKE.items():
        if bad in s:
            s = s.replace(bad, good)
    return s


PLATFORM_NAMES = {'mycia', 'leggimenu', 'eatbu', 'menudigitale', 'thefork', 'qromo',
                  'qodeup', 'glovo', 'tripadvisor', 'justeat', 'deliveroo', 'wolt',
                  'foodprice', 'surprice', 'findmydeal'}


def sanitize_milan_address(a: str) -> str:
    """Rimuove CAP non-20xxx (glitch reverse-geocode): la geo è già verificata in bbox Milano."""
    a = re.sub(r'\b(?!20)\d{5}\b', '', a or '')
    a = re.sub(r'\s*,\s*,', ', ', a)
    a = re.sub(r'\s{2,}', ' ', a).strip(' ,')
    return a


def clean_address(a: str) -> str:
    """Polish display address: ripara mojibake e fixa l'artefatto CAP float '20123.0' -> '20123'."""
    a = fix_mojibake(a or '')
    a = re.sub(r'(\b\d{5})\.0\b', r'\1', a)
    a = re.sub(r'\s{2,}', ' ', a).strip()
    return a


def is_junk_name(name: str) -> bool:
    """Nome = brand piattaforma o vuoto → non è una venue reale."""
    nn = norm_name(name)
    if not nn or len(nn) < 2:
        return True
    return nn in PLATFORM_NAMES


def clean_display_name(s: str) -> str:
    """Ripara mojibake, rimuove zero-width/pipe (collide col separatore all_names), collassa spazi."""
    if not s:
        return s
    s = fix_mojibake(s)
    s = s.replace('​', '').replace('﻿', '').replace(' ', ' ')
    s = s.replace('|', '/')                       # il pipe è il separatore di all_names
    s = re.sub(r'\s+', ' ', s).strip()
    return s


def classify_venue(venue_name: str, categories: str = '') -> str:
    """TARGET / NO_TARGET / AMBIGUOUS basato su nome + categorie."""
    n = ((venue_name or '') + ' ' + (categories or '')).lower()
    target_hits = sum(1 for kw in TARGET_KEYWORDS if kw in n)
    no_hits = sum(1 for kw in NO_TARGET_KEYWORDS if kw in n)
    if no_hits > target_hits:
        return 'NO_TARGET'
    if no_hits > 0 and no_hits == target_hits:
        return 'AMBIGUOUS'   # food+bar pari (es. "Pizzeria Bistrot") → review, non assertire TARGET
    if target_hits > 0:
        return 'TARGET'
    return 'AMBIGUOUS'


def detect_venue_type(name: str, categories: str = '', website: str = '', menu_url: str = '') -> str:
    """venue_type su priority order. Usa nome + categorie (segnale forte da mycia/OSM)."""
    n = ((name or '') + ' ' + (categories or '')).lower()
    if 'rooftop' in n or 'terrazza' in n and 'bar' in n:
        return 'rooftop'
    if 'cocktail' in n or 'speakeasy' in n or 'mixology' in n:
        return 'cocktail_bar'
    if 'craft' in n and 'beer' in n:
        return 'craft_beer'
    if any(k in n for k in ['birreria', 'birrificio', 'brewpub', 'brewery']):
        return 'craft_beer'
    if any(k in n for k in ['pub', 'taproom', 'tap house', 'tap room', 'beerhouse']):
        return 'pub'
    if any(k in n for k in ['wine bar', 'enoteca', 'vineria', 'mescita', 'cantina']):
        return 'wine_bar'
    if 'aperitivo' in n:
        return 'aperitivo_bar'
    if any(k in n for k in ['bistrot', 'bistro']):
        return 'bistro'
    if any(k in n for k in ['hotel', 'unahotels', 'ibis', 'nh ', 'b&b hotel']):
        return 'hotel_bar'
    if any(k in n for k in ['caffè', 'caffe', 'cafe', 'café', 'cafè', 'caffetteria', 'sala da te']):
        return 'cafe'
    if any(k in n for k in ['nightclub', 'lounge', 'disco']):
        return 'cocktail_bar'
    if 'bar' in n:
        return 'cafe'   # "bar" generico italiano = caffetteria/bar di quartiere
    return 'unknown'


# ─────────────────────────────────────────────
# IO helpers
# ─────────────────────────────────────────────
def read_csv(path):
    with open(path, encoding='utf-8-sig', newline='') as f:
        return list(csv.DictReader(f))


def has(v, k):
    return bool((v.get(k) or '').strip())


def name_variants(v):
    """norm_name del venue_name + di ogni all_names variant."""
    out = {norm_name(v['venue_name'])}
    for part in re.split(r'\s*\|\s*', v.get('all_names') or ''):
        if part.strip():
            out.add(norm_name(part))
    return {x for x in out if x}


def display_names(v):
    out = []
    for raw in [v['venue_name']] + re.split(r'\s*\|\s*', v.get('all_names') or ''):
        p = clean_display_name(raw)
        if p and p not in out:
            out.append(p)
    return out


def formality_score(name):
    """Più alto = nome più 'canonico/elegante'. Penalizza slug concatenati e mojibake."""
    s = 0
    if ' ' in name: s += 3
    if any(c.isupper() for c in name): s += 2
    if re.search(r'[àèéìòùÀÈÉÌÒÙâ]', name): s += 2          # accenti veri
    if re.search(r"['’&.\-]", name): s += 1                 # punteggiatura reale
    if '√' in name or 'â€' in name or '‚Ä' in name: s -= 6  # mojibake residuo
    if re.search(r'\.(it|com|net|org)\b', name.lower()): s -= 3
    if ' ' not in name and re.fullmatch(r'[A-Za-z0-9]+', name or '') and len(name) > 8:
        s -= 4    # slug concatenato: "Victoriasclub", "caffefernanda"
    s += min(len(name), 30) * 0.04
    return s


# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────
def main():
    venues = read_csv(VEN)
    prices = read_csv(PRI)

    # priced set: nomi normalizzati che hanno almeno un price point
    priced_norm = set(norm_name(p['venue_name']) for p in prices if (p.get('venue_name') or '').strip())

    def is_priced(v):
        return bool(name_variants(v) & priced_norm)

    no_price = [v for v in venues if not is_priced(v)]
    priced   = [v for v in venues if is_priced(v)]
    print(f"venues totali        : {len(venues)}")
    print(f"  con prezzo         : {len(priced)}")
    print(f"  SENZA prezzo (pool): {len(no_price)}")

    # ── Step 1: classify ──
    for v in no_price:
        v['_class'] = classify_venue(v['venue_name'], v.get('categories', ''))
        v['_vtype'] = detect_venue_type(v['venue_name'], v.get('categories', ''),
                                        v.get('website', ''), v.get('menu_url', ''))
    cls = collections.Counter(v['_class'] for v in no_price)
    print(f"\nClassificazione: {dict(cls)}")

    # ── Step 3 fold-in: leggi geocode fixes se presenti ──
    geo_fix = {}   # canonical_id -> (lat, lon, confidence)
    for src in (GEOCODE_FIXES,):
        if os.path.exists(src):
            for r in read_csv(src):
                cid = (r.get('source_venue_id') or r.get('canonical_id') or '').strip()
                lat, lon = (r.get('new_lat') or '').strip(), (r.get('new_lng') or '').strip()
                conf = (r.get('confidence') or '').strip()
                if cid and lat and lon:
                    geo_fix[cid] = (lat, lon, conf or 'precise')
    if geo_fix:
        print(f"geocode fixes caricati: {len(geo_fix)}")

    # Step 5 fold-in: address reverse-geocoded (riempie SOLO vuoti)
    addr_fix = {}   # canonical_id -> address
    if os.path.exists(ADDR_FIXES):
        for r in read_csv(ADDR_FIXES):
            cid = (r.get('source_venue_id') or '').strip()
            a = sanitize_milan_address((r.get('address') or '').strip())
            if cid and a:
                addr_fix[cid] = a
    if addr_fix:
        print(f"address fixes caricati: {len(addr_fix)}")

    def geo_of(v):
        """(lat, lon, confidence) usando fix se presente, altrimenti geo esistente."""
        cid = v['canonical_id']
        if cid in geo_fix:
            return geo_fix[cid]
        if has(v, 'latitude') and has(v, 'longitude'):
            return v['latitude'], v['longitude'], 'existing'
        return '', '', ''

    # ── Step 2: clustering per norm_name (exact) + prefix-merge conservativo ──
    by_norm = collections.defaultdict(list)
    for v in no_price:
        by_norm[norm_name(v['venue_name'])].append(v)

    # prefix-merge: se una chiave (>=8 char) è prefisso di un'altra → stesso cluster
    keys = sorted(by_norm.keys(), key=len)
    alias = {}  # key -> canonical key
    for i, a in enumerate(keys):
        if not a or len(a) < 8:
            continue
        for b in keys:
            if b != a and len(b) > len(a) and b.startswith(a):
                alias.setdefault(b, a)   # b confluisce in a (più corto = base)
    merged = collections.defaultdict(list)
    for k, vs in by_norm.items():
        root = k
        seen = set()
        while root in alias and root not in seen:
            seen.add(root); root = alias[root]
        merged[root].extend(vs)

    clusters = {k: vs for k, vs in merged.items() if k}
    dup_clusters = {k: vs for k, vs in clusters.items() if len(vs) > 1}
    print(f"\nCluster nomi (no-price): {len(clusters)} totali, {len(dup_clusters)} con duplicati "
          f"({sum(len(v) for v in dup_clusters.values())} righe)")

    # canonical row per cluster + metadata merge
    def merge_cluster(vs):
        # canonical = nome più formale
        all_disp = []
        for v in vs:
            for d in display_names(v):
                if d not in all_disp:
                    all_disp.append(d)
        canonical = max(all_disp, key=formality_score)
        # pick base row = quella col venue_name == canonical, else prima
        base = next((v for v in vs if v['venue_name'] == canonical), vs[0])
        out = dict(base)
        # riempi campi vuoti dai siblings; geo preferisci dentro bbox
        FIELDS = ['address', 'city', 'categories', 'price_tier', 'rating', 'rating_count',
                  'phone', 'website', 'opening_hours', 'menu_url', 'has_menu', 'sources']
        for f in FIELDS:
            if not (out.get(f) or '').strip():
                for v in vs:
                    if (v.get(f) or '').strip():
                        out[f] = v[f]; break
        # geo: scegli prima riga con geo dentro bbox, altrimenti qualunque geo
        best_geo = None
        for v in vs:
            la, lo, cf = geo_of(v)
            if la and lo:
                try:
                    laf, lof = float(la), float(lo)
                    inb = (MILAN_BBOX[0] <= laf <= MILAN_BBOX[1] and MILAN_BBOX[2] <= lof <= MILAN_BBOX[3])
                except ValueError:
                    inb = False
                if best_geo is None or (inb and best_geo[3] is False):
                    best_geo = (v['canonical_id'], la, lo, inb, cf)
        out['_canonical_name'] = canonical
        out['_all_names'] = all_disp
        out['_geo_src_cid'] = best_geo[0] if best_geo else base['canonical_id']
        # classificazione/venue_type ricalcolate sul canonical + categorie unite
        # (NO voting "any TARGET wins": promuoveva pizzerie clusterizzate a TARGET)
        out['_class'] = classify_venue(canonical, out.get('categories', ''))
        out['_vtype'] = detect_venue_type(canonical, out.get('categories', ''))
        out['_dupe_count'] = len(vs)
        return out

    canon_rows = [merge_cluster(vs) for vs in clusters.values()]

    # ── Step 7: quality gate ──
    def quality_gate(v):
        nm = v['_canonical_name'].strip()
        if not nm or len(nm) < 2:
            return False, 'EMPTY_NAME'
        if is_junk_name(nm):
            return False, 'JUNK_NAME'
        low = nm.lower()
        if low in priced_norm or norm_name(nm) in priced_norm:
            return False, 'ALREADY_HAS_PRICE'
        if re.search(r'https?://|www\.|<|>|menu\s*[-–]\s*', low):
            return False, 'DIRTY_NAME'
        if not is_milan_or_unknown(v.get('address', '')):
            return False, 'NON_MILAN_CAP'
        la, lo, cf = geo_of_canon(v)
        if la and lo:
            try:
                laf, lof = float(la), float(lo)
                if not (MILAN_BBOX[0] <= laf <= MILAN_BBOX[1] and MILAN_BBOX[2] <= lof <= MILAN_BBOX[3]):
                    return False, 'OUT_OF_MILAN_BBOX'
            except ValueError:
                pass
        if v['_class'] == 'NO_TARGET':
            return False, 'NO_TARGET'
        return True, None

    def geo_of_canon(v):
        cid = v.get('_geo_src_cid') or v['canonical_id']
        if cid in geo_fix:
            return geo_fix[cid]
        if has(v, 'latitude') and has(v, 'longitude'):
            return v['latitude'], v['longitude'], 'existing'
        return '', '', ''

    kept, gate_reasons = [], collections.Counter()
    for v in canon_rows:
        ok, why = quality_gate(v)
        if ok:
            kept.append(v)
        else:
            gate_reasons[why] += 1
    print(f"\nQuality gate: {len(kept)} kept / {len(canon_rows)} canonical")
    print("  scartati:", dict(gate_reasons))
    kvt = collections.Counter(v['_vtype'] for v in kept)
    print("  venue_type (kept):", dict(kvt.most_common()))
    kcl = collections.Counter(v['_class'] for v in kept)
    print("  classification (kept):", dict(kcl))

    # ── Step 6: write File 1 (no_price master) ──
    OUT_COLS = ['source_platform','source_venue_id','venue_name','venue_url','address','city',
                'latitude','longitude','categories','price_tier','rating','rating_count',
                'phone','website','opening_hours','has_menu','menu_url','extraction_status',
                'retrieved_at','venue_type','target_classification','has_price',
                'geocoding_confidence','all_names']
    now = datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    with open(OUT_NOPRICE, 'w', encoding='utf-8-sig', newline='') as f:
        w = csv.DictWriter(f, fieldnames=OUT_COLS)
        w.writeheader()
        for v in sorted(kept, key=lambda x: (x['_vtype'], x['_canonical_name'].lower())):
            la, lo, cf = geo_of_canon(v)
            cls_out = 'TARGET' if v['_class'] == 'TARGET' else 'AMBIGUOUS_TO_REVIEW'
            w.writerow({
                'source_platform': (v.get('sources') or '').split('|')[0].split(',')[0].strip() or 'unified',
                'source_venue_id': v['canonical_id'],
                'venue_name': v['_canonical_name'],
                'venue_url': v.get('menu_url') or v.get('website') or '',
                'address': clean_address(v.get('address', '') or addr_fix.get(v['canonical_id'], '')
                            or addr_fix.get(v.get('_geo_src_cid', ''), '')),
                'city': v.get('city') or 'Milano',
                'latitude': la, 'longitude': lo,
                'categories': fix_mojibake(v.get('categories', '')),
                'price_tier': v.get('price_tier', ''),
                'rating': v.get('rating', ''), 'rating_count': v.get('rating_count', ''),
                'phone': v.get('phone', ''), 'website': v.get('website', ''),
                'opening_hours': fix_mojibake(v.get('opening_hours', '')),
                'has_menu': v.get('has_menu', ''), 'menu_url': v.get('menu_url', ''),
                'extraction_status': 'no_price',
                'retrieved_at': v.get('retrieved_at') or now,
                'venue_type': v['_vtype'],
                'target_classification': cls_out,
                'has_price': 'False',
                'geocoding_confidence': cf,
                'all_names': ' | '.join(v['_all_names']),
            })
    print(f"\n✍  scritto {OUT_NOPRICE} ({len(kept)} venues)")

    # ── File 3: name dedup (tutti i cluster con duplicati nel pool no-price) ──
    with open(OUT_DEDUP, 'w', encoding='utf-8-sig', newline='') as f:
        w = csv.writer(f)
        w.writerow(['canonical_name','all_variants','canonical_source_venue_id','dupe_count',
                    'target_classification'])
        rows = sorted([v for v in canon_rows if v['_dupe_count'] > 1],
                      key=lambda x: -x['_dupe_count'])
        for v in rows:
            cls_out = ('TARGET' if v['_class'] == 'TARGET'
                       else 'NO_TARGET' if v['_class'] == 'NO_TARGET' else 'AMBIGUOUS_TO_REVIEW')
            w.writerow([v['_canonical_name'], ' | '.join(v['_all_names']),
                        v['canonical_id'], v['_dupe_count'], cls_out])
    print(f"✍  scritto {OUT_DEDUP} ({len(rows)} cluster duplicati)")

    # stats per report (stampa CAP coverage)
    caps = collections.Counter()
    for v in kept:
        m = re.findall(r'\b(20\d{3})\b', v.get('address', ''))
        if m: caps[m[0]] += 1
    print(f"\nCAP Milano coperti (kept, top 12): {dict(caps.most_common(12))}")
    print(f"CAP distinti: {len(caps)}")
    geoconf = collections.Counter(geo_of_canon(v)[2] or 'none' for v in kept)
    print(f"geocoding_confidence (kept): {dict(geoconf)}")


if __name__ == '__main__':
    main()
