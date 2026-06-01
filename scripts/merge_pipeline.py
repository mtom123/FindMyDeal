"""
merge_pipeline.py — FoodPrice Orchestrator
==========================================
Scansiona raw_sources/, carica tutti i *_venues.csv e *_menu_items.csv,
deduplica, normalizza e produce:

  unified_venues.csv      — master venue table
  unified_menu_items.csv  — tutti i prezzi normalizzati
  unified_prices.csv      — product-centric, pronto per il sito
  merge_report.txt        — statistiche e warning

Eseguibile in qualsiasi momento, anche parzialmente (agenti non ancora arrivati).

Run:  python merge_pipeline.py
"""

import csv
import re
import json
import hashlib
from pathlib import Path
from datetime import datetime, timezone
from collections import defaultdict, Counter
from difflib import SequenceMatcher

# ─────────────────────────────────────────────
# PATHS
# ─────────────────────────────────────────────

RAW_DIR   = Path("raw_sources")
OUT_DIR   = Path(".")
RAW_DIR.mkdir(exist_ok=True)

UNIFIED_VENUES = OUT_DIR / "unified_venues.csv"
UNIFIED_ITEMS  = OUT_DIR / "unified_menu_items.csv"
UNIFIED_PRICES = OUT_DIR / "unified_prices.csv"
REPORT_FILE    = OUT_DIR / "merge_report.txt"

# ─────────────────────────────────────────────
# EXPECTED SCHEMAS (for validation)
# ─────────────────────────────────────────────

VENUE_REQUIRED = {
    "source_platform", "venue_name", "venue_url",
    "extraction_status", "retrieved_at",
}
# address/city non obbligatori — molti agenti non li hanno (geocodificati in seguito)
ITEM_REQUIRED = {
    "source_platform", "venue_name",
    "item_name", "normalized_price_eur",
    "price_type", "item_type",
    "confidence", "retrieved_at",
}
# raw_price e venue_url sono opzionali — alcuni agenti li omettono per items senza prezzo

VALID_PLATFORMS = {
    "mycia", "thefork", "eatbu", "leggimenu", "wolt", "justeat",
    "glovo", "deliveroo", "iamenu", "gromo", "one2menu",
    "menutiger", "ordable", "buonmenu", "dishcovery",
    "menudigitale", "direct_website", "other",
    # Aggiunti session 31/05 sera
    "web_extract", "pdf_googledork", "comune", "qodeup",
    # Aggiunti 01/06 — pdf_dork è il platform tag reale in pdf_googledork_menu_items.csv
    "pdf_dork",
}

VALID_PRODUCTS = {
    "spritz", "negroni", "americano", "gin_tonic", "mojito",
    "moscow_mule", "margarita", "daiquiri", "manhattan",
    "beer_draft_small", "beer_draft_medium", "beer_bottle",
    "beer_moretti", "beer_heineken", "beer_peroni",
    "wine_glass", "prosecco_glass", "espresso", "cappuccino",
    "soft_drink", "water", "custom_cocktail",
}

PRODUCT_LABELS = {
    "spritz": "Spritz", "negroni": "Negroni", "americano": "Americano",
    "gin_tonic": "Gin Tonic", "mojito": "Mojito", "moscow_mule": "Moscow Mule",
    "margarita": "Margarita", "daiquiri": "Daiquiri", "manhattan": "Manhattan",
    "beer_draft_small": "Birra Spina Piccola", "beer_draft_medium": "Birra Spina Media",
    "beer_bottle": "Birra Bottiglia", "beer_moretti": "Birra Moretti",
    "beer_heineken": "Heineken", "beer_peroni": "Peroni/Nastro Azzurro",
    "wine_glass": "Vino al Calice", "prosecco_glass": "Prosecco Calice",
    "espresso": "Caffè", "cappuccino": "Cappuccino",
    "soft_drink": "Bibita", "water": "Acqua",
    "custom_cocktail": "Cocktail Custom",
}

PRODUCT_ORDER = list(PRODUCT_LABELS.keys())

# ─────────────────────────────────────────────
# NORMALISATION HELPERS
# ─────────────────────────────────────────────

def clean_name(name: str) -> str:
    """Normalise venue name for deduplication matching."""
    s = name.lower().strip()
    s = re.sub(r"[''`]", "", s)
    s = re.sub(r"\s+", " ", s)
    s = re.sub(r"\b(srl|snc|srls|spa|di|bar|café|caffe|the|il|la|lo|le|gli|i)\b", "", s)
    s = re.sub(r"[^a-z0-9 ]", "", s)
    return s.strip()

def venue_fingerprint(name: str, lat: str, lng: str) -> str:
    """Stable ID for deduplication."""
    lat_r = round(float(lat), 4) if lat else 0
    lng_r = round(float(lng), 4) if lng else 0
    key = f"{clean_name(name)}|{lat_r}|{lng_r}"
    return hashlib.md5(key.encode()).hexdigest()[:12]

def name_similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, clean_name(a), clean_name(b)).ratio()

def parse_price(raw: str) -> float:
    if not raw:
        return 0.0
    try:
        return float(raw)
    except ValueError:
        m = re.search(r"(\d{1,3}(?:[.,]\d{1,2})?)", str(raw))
        if m:
            return float(m.group(1).replace(",", "."))
        return 0.0

# ─────────────────────────────────────────────
# CSV LOADING
# ─────────────────────────────────────────────

def load_csv(path: Path) -> list[dict]:
    try:
        with open(path, encoding="utf-8-sig") as f:
            return list(csv.DictReader(f))
    except Exception as e:
        print(f"  WARN: could not read {path}: {e}")
        return []


def validate_row(row: dict, required: set, source_file: str) -> list[str]:
    """Return list of validation warnings (empty = ok)."""
    warnings = []
    for field in required:
        if field not in row or not str(row.get(field, "")).strip():
            warnings.append(f"missing required field '{field}'")
    platform = row.get("source_platform", "")
    if platform and platform not in VALID_PLATFORMS:
        warnings.append(f"unknown platform '{platform}'")
    prod = row.get("normalized_product", "")
    if prod and prod not in VALID_PRODUCTS:
        warnings.append(f"unknown product '{prod}'")
    return warnings

# ─────────────────────────────────────────────
# ALSO LOAD LEGACY MYCIA FILES
# ─────────────────────────────────────────────

def remap_mycia_venues(path: Path) -> list[dict]:
    """Convert old mycia_milano_venues.csv to unified schema."""
    rows = load_csv(path)
    out = []
    for r in rows:
        out.append({
            "source_platform":  "mycia",
            "source_venue_id":  r.get("venue_id", ""),
            "venue_name":       r.get("venue_name", ""),
            "venue_url":        r.get("venue_url", ""),
            "address":          r.get("address", ""),
            "city":             r.get("city", "Milano"),
            "latitude":         r.get("latitude", ""),
            "longitude":        r.get("longitude", ""),
            "categories":       r.get("categories", ""),
            "price_tier":       r.get("price_tier", ""),
            "rating":           r.get("rating", ""),
            "rating_count":     "",
            "phone":            "",
            "website":          "",
            "opening_hours":    r.get("opening_hours", ""),
            "has_menu":         "True" if "menu" in r.get("extraction_status","") else "False",
            "menu_url":         r.get("menu_url", ""),
            "extraction_status":r.get("extraction_status", ""),
            "retrieved_at":     r.get("retrieved_at", ""),
        })
    return out


def remap_mycia_items(path: Path) -> list[dict]:
    """Convert old mycia_milano_menu_items.csv to unified schema."""
    rows = load_csv(path)
    out = []
    for r in rows:
        out.append({
            "source_platform":    "mycia",
            "source_venue_id":    r.get("venue_id", ""),
            "venue_name":         r.get("venue_name", ""),
            "venue_url":          r.get("source_url", ""),
            "menu_section":       r.get("menu_section", ""),
            "item_name":          r.get("item_name", ""),
            "item_description":   r.get("item_description", ""),
            "raw_price":          r.get("raw_price", ""),
            "normalized_price_eur": r.get("normalized_price_eur", ""),
            "currency":           r.get("currency", "EUR"),
            "price_type":         "menu",
            "item_type":          r.get("item_type", ""),
            "normalized_product": r.get("normalized_product", ""),
            "confidence":         r.get("confidence", ""),
            "allergens":          "",
            "retrieved_at":       r.get("retrieved_at", ""),
            "source_url":         r.get("source_url", ""),
        })
    return out

# ─────────────────────────────────────────────
# MAIN MERGE
# ─────────────────────────────────────────────

# Import libreria normalizzazione CONDIVISA (vedi normalization.py)
# Tutte le funzioni di disambiguazione/cleanup sono lì per essere riusate dagli agent scraper.
try:
    from normalization import clean_item_product, is_milan_or_unknown, PRICE_RANGES
    SHARED_LIB = True
    print(f"[merge] Loaded shared normalization library")
except ImportError:
    SHARED_LIB = False
    print("[merge] WARNING: normalization.py not found, using inline fallback")

# Le funzioni qui sotto sono fallback inline (se l'import sopra fallisce).
def _clean_item_product_inline(item: dict) -> tuple:
    prod = (item.get("normalized_product","") or "").strip()
    name = (item.get("item_name","") or "")
    desc = (item.get("item_description","") or "")
    try: price = float(item.get("normalized_price_eur", 0) or 0)
    except: price = 0
    text = (name + ' ' + desc).lower()
    name_lower = name.lower()
    name_upper = name.upper()

    # 1. PRODUCT FIXES (modifica normalized_product)
    # 1a. Coffee classificato come americano cocktail
    if prod == 'americano':
        if 'caff' in name_lower and price < 4:
            return '', None  # clear product, but tieni item (sara' espresso)
        if 'caff' in name_lower and price < 5:
            # ambiguo - se "caffè americano" è esplicito, non è cocktail
            if re.search(r'caff[eè]\s*americano', name_lower):
                return '', None
    # 1b. Espresso classificato male
    if prod == 'espresso':
        if re.search(r'\b(martini|cocktail|affogato|mixed)\b', name_lower):
            return 'custom_cocktail', None
        if 'corretto' in name_lower and price > 3:
            return '', None  # caffè corretto è espresso ma sopra range
    # 1c. Prosecco glass quando è bottiglia
    if prod == 'prosecco_glass':
        if re.search(r'\bbottiglia\b', name_lower) and price > 15:
            return None, 'PROSECCO_BOTTIGLIA'  # SKIP item
        if price > 15:
            return None, 'PROSECCO_GLASS_TOO_HIGH'  # SKIP (likely bottiglia)
    # 1d. Beer Moretti = Vittorio Moretti (Franciacorta)
    if prod == 'beer_moretti':
        if re.search(r'\bvittorio\b|\briserva\b|\bextra\s*brut\b|\bbrut\b|\bspumante\b', name_lower):
            return None, 'MORETTI_SPUMANTE'
    # 1e. Beer bottle ma è vino o food
    if prod == 'beer_bottle':
        if re.search(r'\b(vino|valpolicella|barolo|chianti|antipasto|ripasso|riserva)\b', name_lower):
            return None, 'BEER_BOTTLE_IS_FOOD_OR_WINE'
    # 1f. Mojito che è Bloody Mary
    if prod == 'mojito':
        if 'bloody mary' in name_lower or ('licorice' in name_lower and 'mary' in name_lower):
            return None, 'MOJITO_IS_BLOODY_MARY'
    # 1g. Margarita caraffa (pitcher) — fuori scope confronto singolo
    if prod == 'margarita':
        if 'caraffa' in name_lower or 'pitcher' in name_lower or price > 30:
            return None, 'MARGARITA_CARAFFA'
    # 1g-bis. FORMATO MAXI (multi-porzione) — applica a tutti i drink cocktail
    if prod in ('spritz','negroni','americano','gin_tonic','mojito','moscow_mule','margarita','daiquiri','manhattan','custom_cocktail'):
        if re.search(r'\bmaxi\b|\bcaraffa\b|\bpitcher\b|\bbrocca\b|\blitro\b|1\s*l(?:itro|t)?\b', name_lower):
            return None, 'FORMAT_MAXI'
    # 1h. Spritz mismatch -> soft_drink/wine_glass
    if prod == 'spritz':
        # "Soft drinks coca cola..." → soft_drink
        if re.search(r'\b(coca\s*cola|fanta|sprite|soft\s*drinks?)\b', name_lower) and 'spritz' not in name_lower:
            return 'soft_drink', None
        # "Calice bianco/rosso" / "vino bianco/rosso" → wine_glass
        if re.search(r'\b(calice|vino\s+(?:bianco|rosso|al\s+calice))\b', name_lower) and 'spritz' not in name_lower:
            return 'wine_glass', None
        # "Birra alla spina" / "Birra X" → beer_*
        if re.search(r'\bbirra\b', name_lower) and 'spritz' not in name_lower:
            return None, 'SPRITZ_IS_BEER'
        # "Caffè/Espresso/Cappuccino" → espresso
        if re.search(r'\b(caff[eè]|espresso|cappuccino)\b', name_lower) and 'spritz' not in name_lower:
            return None, 'SPRITZ_IS_COFFEE'

    # 2. NAME NOISE FILTERS (skippa item)
    NOISE_PATTERNS = [
        r'menu\s*[-–]\s*',
        r'salta\s+al\s+contenuto',
        r'menu\s+digitale',
        r'vai\s+alla\s+(header|footer)',
        r'#8211|#8217|&nbsp;',
        r'^\s*(home|contatti|chi\s+siamo|menu)\s*$',
        r'\bmail\s+us\b',
        r'@\w+\.\w+',  # email address
        r'\bwhere:\s*\w+',  # "where: duomo via torino"
        r'^\s*[\W\d]+\s*[A-Z]+[\W\d]+',  # "9€18€12€SANGRIA" parser concat
    ]
    for p in NOISE_PATTERNS:
        if re.search(p, name_lower, re.I):
            return None, 'NAME_NOISE'
    # 5+ euro symbols nel nome = parser concat fail
    if name.count('€') >= 4:
        return None, 'NAME_MULTI_EURO_CONCAT'

    # 3. ITEM_NAME parser noise: page-title HTML estratto come item
    if len(name) > 50:
        nav_kw = ['home', 'chi siamo', 'contatti', 'footer', 'header', 'navigation',
                  'salta al contenuto', 'toggle navigation', 'mail us', 'team news',
                  'about chef', 'seleziona una pagina', 'leggi il menu digitale',
                  'menu prenotazioni', 'instagram facebook']
        nav_hits = sum(1 for kw in nav_kw if kw in name_lower)
        if nav_hits >= 2:
            return None, 'NAME_PARSER_NOISE'
        # 'menu' + altri 2 marker = page nav
        if 'menu' in name_lower and nav_hits >= 1:
            return None, 'NAME_PARSER_NOISE'

    # 4. ITEM_NAME troppo lungo + page-like (single marker)
    if len(name) > 100 and re.search(r'\b(home|menu|chi\s+siamo|contatti|footer|header)\b', name_lower):
        return None, 'NAME_TOO_LONG_PAGE'

    return prod, None  # OK, mantiene il prodotto (anche se invariato)


# Fallback se shared lib non disponibile
if not SHARED_LIB:
    clean_item_product = _clean_item_product_inline


def _is_milan_or_unknown_inline(addr: str) -> bool:
    """
    Filtro città: True se address è plausibilmente Milano o se non c'è CAP.
    False solo se address ha CAP NON-Milano esplicito (es. 47843 = Misano Adriatico).
    """
    if not addr:
        return True  # senza addr = unknown = accetto, fingerprint farà il dedup
    caps = re.findall(r'\b(\d{5})\b', addr)
    if not caps:
        return True
    # Almeno un CAP deve essere 20xxx (Milano metro)
    for cap in caps:
        if 20000 <= int(cap) <= 20999:
            return True
    return False  # CAP esplicitamente fuori 20xxx


if not SHARED_LIB:
    is_milan_or_unknown = _is_milan_or_unknown_inline


def main():
    now = datetime.now(timezone.utc).isoformat()
    report_lines = [f"FoodPrice Merge Report — {now}", "=" * 60]

    # ── 1. Collect all venue files ─────────────────────
    all_venues: list[dict] = []
    all_items: list[dict] = []
    sources_found = []

    # Legacy MyCIA files (different schema)
    mycia_v = Path("mycia_milano_venues.csv")
    mycia_i = Path("mycia_milano_menu_items.csv")
    blocked_venue_ids = set()  # venues con CAP non-Milano → blocco anche i loro items
    if mycia_v.exists():
        vv = remap_mycia_venues(mycia_v)
        # Filtro città: scarta venues con CAP non-20xxx
        filtered = []
        for v in vv:
            if is_milan_or_unknown(v.get("address","")):
                filtered.append(v)
            else:
                blocked_venue_ids.add(v.get("source_venue_id",""))
        all_venues.extend(filtered)
        print(f"  mycia_venues (legacy): {len(filtered)} rows (skipped {len(vv)-len(filtered)} non-Milan CAP)")
        sources_found.append("mycia")
    if mycia_i.exists():
        ii = remap_mycia_items(mycia_i)
        # Blocca items di venues scartate
        ii_filtered = [i for i in ii if i.get("source_venue_id","") not in blocked_venue_ids]
        all_items.extend(ii_filtered)
        print(f"  mycia_items (legacy):  {len(ii_filtered)} rows (skipped {len(ii)-len(ii_filtered)} per non-Milan venue)")

    # New unified-schema files from raw_sources/
    NAV_MARKERS = ['Vai alla Header Bar', 'Vai al Contentuo', 'Footer Bar',
                   'Skip to content', 'Salta al contenuto']
    nav_skipped = 0
    city_skipped_venues = 0
    city_blocked_ids = set()  # per skippare anche gli items
    BEACH_FILES = ('beach_', 'comune_osm_')  # questi sono vertical=beach, skip dal merge drink

    for vfile in sorted(RAW_DIR.glob("*_venues.csv")):
        platform = vfile.stem.replace("_venues", "")
        # Skip vertical beach files (gestiti separatamente)
        if any(vfile.name.startswith(p) for p in BEACH_FILES):
            print(f"  {vfile.name}: SKIP (vertical=beach)")
            continue
        rows = load_csv(vfile)
        warn_count = 0
        valid_rows = []
        for row in rows:
            warns = validate_row(row, VENUE_REQUIRED, str(vfile))
            if warns:
                warn_count += 1
                continue
            # Filtro città inline
            if not is_milan_or_unknown(row.get("address","")):
                city_blocked_ids.add(row.get("source_venue_id",""))
                city_skipped_venues += 1
                continue
            valid_rows.append(row)
        all_venues.extend(valid_rows)
        sources_found.append(platform)
        print(f"  {vfile.name}: {len(valid_rows)} valid / {len(rows)} total ({warn_count} warnings)")
        report_lines.append(f"{vfile.name}: {len(valid_rows)} valid, {warn_count} warnings")

    if city_skipped_venues:
        print(f"  -> {city_skipped_venues} venues skipped (CAP non-Milano)")

    cleanup_skipped = Counter()
    for ifile in sorted(RAW_DIR.glob("*_menu_items.csv")):
        if any(ifile.name.startswith(p) for p in BEACH_FILES):
            continue
        rows = load_csv(ifile)
        warn_count = 0
        valid_rows = []
        for row in rows:
            warns = validate_row(row, ITEM_REQUIRED, str(ifile))
            if warns:
                warn_count += 1
                continue
            # Filtro: skippa items con HTML navigation in item_name
            iname = row.get('item_name','')
            if any(m in iname for m in NAV_MARKERS):
                nav_skipped += 1
                continue
            # Filtro: item_name troppo corto o solo punteggiatura (parser noise)
            iname_clean = re.sub(r'[^a-zA-Z0-9]', '', iname)
            if len(iname_clean) < 3:
                nav_skipped += 1
                continue
            # Filtro: item_name che descrive un menu prezzo fisso (€X con N portate)
            if re.search(r'\d+\s*€?\s*con\s+\d+\s+portate', iname, re.I):
                nav_skipped += 1
                continue
            # Filtro: skippa items di venues bloccate per CAP
            if row.get('source_venue_id','') in city_blocked_ids:
                continue
            # AUDIT v2: clean product + skip noise
            corrected_prod, skip_reason = clean_item_product(row)
            if skip_reason:
                cleanup_skipped[skip_reason] += 1
                continue
            if corrected_prod != row.get('normalized_product',''):
                row['normalized_product'] = corrected_prod
            valid_rows.append(row)
        all_items.extend(valid_rows)
        print(f"  {ifile.name}: {len(valid_rows)} valid / {len(rows)} total ({warn_count} warnings)")
        report_lines.append(f"{ifile.name}: {len(valid_rows)} valid, {warn_count} warnings")

    if nav_skipped:
        print(f"  -> {nav_skipped} items skipped (HTML navigation markers)")
    if cleanup_skipped:
        print(f"  -> AUDIT cleanup skip: {dict(cleanup_skipped)}")

    print(f"\nTotale grezzo: {len(all_venues)} venues, {len(all_items)} items")
    print(f"Fonti: {set(sources_found)}\n")

    # ── 2. Canonical venue deduplication ──────────────
    # Group venues by geo fingerprint, then by name similarity
    canonical: dict[str, dict] = {}   # fingerprint → best_venue_row
    venue_canonical_map: dict[str, str] = {}  # (platform+id) → fingerprint

    for v in all_venues:
        lat = str(v.get("latitude", "") or "")
        lng = str(v.get("longitude", "") or "")
        name = v.get("venue_name", "") or ""

        fp = venue_fingerprint(name, lat, lng)
        pid = f"{v.get('source_platform','')}::{v.get('source_venue_id', v.get('venue_url',''))}"
        # Prefer geo-rich mapping: only overwrite if current mapping has no geo
        existing_fp = venue_canonical_map.get(pid)
        if existing_fp is None:
            venue_canonical_map[pid] = fp
        elif lat and not canonical.get(existing_fp, {}).get("latitude"):
            # Upgrade: new entry has geo, existing canonical doesn't → update map
            venue_canonical_map[pid] = fp
        # else: keep existing (it already has geo, don't downgrade)

        if fp not in canonical:
            canonical[fp] = {**v, "_sources": [], "_all_names": []}

        # Merge: keep best data
        existing = canonical[fp]
        existing["_sources"].append(v.get("source_platform", ""))
        existing["_all_names"].append(name)

        # Prefer values from sources with geo data
        if not existing.get("latitude") and lat:
            existing["latitude"] = lat
            existing["longitude"] = lng
        for field in ("phone", "website", "opening_hours", "rating", "rating_count"):
            if not existing.get(field) and v.get(field):
                existing[field] = v[field]
        # Merge categories
        if v.get("categories") and v["categories"] not in existing.get("categories",""):
            existing["categories"] = "; ".join(filter(None, [existing.get("categories",""), v["categories"]]))

    print(f"Venues dopo deduplicazione: {len(canonical)} (da {len(all_venues)} raw)")
    report_lines.append(f"\nVenues raw: {len(all_venues)} → canonical: {len(canonical)}")

    # ── 2bis. GHOST MERGE: unisce canonical con stesso nome quando uno ha lat='' ──
    # Bug noto: stesso venue scrapato 2 volte (una con lat, una senza) crea 2 canonical entries.
    # Fix: per ogni nome ricorrente, se uno dei canonical ha lat='', mergialo nel canonical con lat.
    name_to_fps = {}
    for fp, v in canonical.items():
        n = clean_name(v.get("venue_name",""))
        if n and len(n) > 3:
            name_to_fps.setdefault(n, []).append(fp)

    ghost_merged = 0
    fp_redirect = {}  # ghost_fp -> real_fp (per re-map items)
    for n, fps in name_to_fps.items():
        if len(fps) < 2:
            continue
        # Trova il canonical con lat (preferito) e quelli ghost (lat='')
        with_lat = [fp for fp in fps if canonical[fp].get("latitude")]
        without_lat = [fp for fp in fps if not canonical[fp].get("latitude")]
        if not with_lat or not without_lat:
            continue
        # Scegli il canonical principale: quello con piu sources
        primary = max(with_lat, key=lambda fp: len(canonical[fp]["_sources"]))
        for ghost in without_lat:
            # Merge ghost into primary
            canonical[primary]["_sources"].extend(canonical[ghost]["_sources"])
            canonical[primary]["_all_names"].extend(canonical[ghost]["_all_names"])
            for field in ("phone","website","opening_hours","rating","menu_url"):
                if not canonical[primary].get(field) and canonical[ghost].get(field):
                    canonical[primary][field] = canonical[ghost][field]
            fp_redirect[ghost] = primary
            del canonical[ghost]
            ghost_merged += 1

    # Update venue_canonical_map per redirected ghosts
    for pid, fp in list(venue_canonical_map.items()):
        if fp in fp_redirect:
            venue_canonical_map[pid] = fp_redirect[fp]

    if ghost_merged:
        print(f"Ghost canonical merged: {ghost_merged} (stesso nome, lat='' -> lat')")
        report_lines.append(f"Ghost canonical merged: {ghost_merged}")

    # ── 3. Write unified_venues.csv ───────────────────
    VENUE_FIELDS = [
        "canonical_id", "venue_name", "all_names", "sources",
        "address", "city", "latitude", "longitude",
        "categories", "price_tier", "rating", "rating_count",
        "phone", "website", "opening_hours",
        "has_menu", "menu_url", "retrieved_at",
    ]
    with open(UNIFIED_VENUES, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=VENUE_FIELDS, extrasaction="ignore")
        w.writeheader()
        for fp, v in canonical.items():
            w.writerow({
                "canonical_id":  fp,
                "venue_name":    v.get("venue_name", ""),
                "all_names":     " | ".join(dict.fromkeys(n for n in v["_all_names"] if n)),
                "sources":       " | ".join(dict.fromkeys(v["_sources"])),
                **{k: v.get(k, "") for k in VENUE_FIELDS[4:]},
            })

    # ── 4. Enrich items with canonical_id ─────────────
    enriched_items = []
    unmatched = 0
    for item in all_items:
        # Find canonical_id
        platform = item.get("source_platform", "")
        sid = item.get("source_venue_id", item.get("venue_url", ""))
        pid = f"{platform}::{sid}"
        fp  = venue_canonical_map.get(pid)

        if not fp:
            # Fallback: name-based lookup
            name = item.get("venue_name", "")
            lat  = ""
            lng  = ""
            fp2 = venue_fingerprint(name, lat, lng)
            if fp2 in canonical:
                fp = fp2
            else:
                # Try name-similarity against all canonical venues
                best_score = 0.0
                for cfp, cv in canonical.items():
                    score = name_similarity(name, cv.get("venue_name",""))
                    if score > best_score:
                        best_score = score
                        fp = cfp
                if best_score < 0.7:
                    fp = None
                    unmatched += 1

        # Price filter
        price = parse_price(item.get("normalized_price_eur", ""))
        if price <= 0 or price > 300:
            continue

        canon = canonical.get(fp, {}) if fp else {}
        enriched_items.append({
            "canonical_venue_id":  fp or "",
            "venue_name":          item.get("venue_name", ""),
            "latitude":            canon.get("latitude", ""),
            "longitude":           canon.get("longitude", ""),
            "address":             canon.get("address", item.get("address", "")),
            "city":                "Milano",
            "source_platform":     platform,
            "price_type":          item.get("price_type", "menu"),
            "menu_section":        item.get("menu_section", ""),
            "item_name":           item.get("item_name", ""),
            "item_description":    item.get("item_description", ""),
            "raw_price":           item.get("raw_price", ""),
            "price_eur":           price,
            "currency":            "EUR",
            "item_type":           item.get("item_type", ""),
            "normalized_product":  item.get("normalized_product", ""),
            "confidence":          item.get("confidence", ""),
            "allergens":           item.get("allergens", ""),
            "source_url":          item.get("source_url", item.get("venue_url", "")),
            "retrieved_at":        item.get("retrieved_at", ""),
        })

    print(f"Items dopo enrichment: {len(enriched_items)} (unmatched venue: {unmatched})")
    report_lines.append(f"Items: {len(all_items)} raw → {len(enriched_items)} enriched ({unmatched} venue unmatched)")

    # ── 5. Deduplicate items ───────────────────────────
    seen_items: set = set()
    dedup_items = []
    for item in enriched_items:
        key = (
            item["canonical_venue_id"],
            item["normalized_product"] or item["item_name"].lower()[:30],
            item["price_eur"],
            item["price_type"],
        )
        if key not in seen_items:
            seen_items.add(key)
            dedup_items.append(item)

    print(f"Items dopo deduplicazione: {len(dedup_items)}")
    report_lines.append(f"Items dopo dedup: {len(dedup_items)}")

    # ── 6. Write unified_menu_items.csv ───────────────
    ITEM_FIELDS = [
        "canonical_venue_id", "venue_name", "latitude", "longitude",
        "address", "city", "source_platform", "price_type",
        "menu_section", "item_name", "item_description",
        "raw_price", "price_eur", "currency",
        "item_type", "normalized_product", "confidence",
        "allergens", "source_url", "retrieved_at",
    ]
    with open(UNIFIED_ITEMS, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=ITEM_FIELDS, extrasaction="ignore")
        w.writeheader()
        w.writerows(dedup_items)

    # ── 7. Build unified_prices.csv (product-centric) ──
    # Only items with geo + normalized_product + price + range plausibile
    PRICE_RANGES = {
        'spritz':            (3.0, 22.0),
        'negroni':           (4.0, 25.0),
        'americano':         (4.0, 18.0),
        'gin_tonic':         (5.0, 22.0),
        'mojito':            (5.0, 22.0),
        'moscow_mule':       (5.0, 20.0),
        'margarita':         (5.0, 25.0),
        'daiquiri':          (6.0, 22.0),
        'manhattan':         (7.0, 25.0),
        'custom_cocktail':   (5.0, 30.0),
        'beer_draft_small':  (2.0, 8.0),
        'beer_draft_medium': (3.0, 12.0),
        'beer_bottle':       (2.0, 14.0),
        'beer_moretti':      (2.0, 8.0),
        'beer_heineken':     (2.0, 8.0),
        'beer_peroni':       (2.0, 8.0),
        'wine_glass':        (3.0, 15.0),
        'prosecco_glass':    (3.0, 14.0),
        'espresso':          (0.8, 4.0),
        'cappuccino':        (1.2, 5.5),
        'soft_drink':        (1.0, 7.0),
        'water':             (0.5, 5.0),
    }
    price_rows = []
    range_skipped = Counter()
    for i in dedup_items:
        prod = i["normalized_product"]
        if not prod or not i["latitude"] or i["price_eur"] <= 0:
            continue
        if prod in PRICE_RANGES:
            lo, hi = PRICE_RANGES[prod]
            if i["price_eur"] < lo or i["price_eur"] > hi:
                range_skipped[prod] += 1
                continue
        price_rows.append(i)

    if range_skipped:
        print(f"Price points skipped per range: {dict(range_skipped)}")
        report_lines.append(f"Price-range filter: {dict(range_skipped)}")

    def prod_order(p):
        try: return PRODUCT_ORDER.index(p)
        except ValueError: return 99

    price_rows.sort(key=lambda x: (prod_order(x["normalized_product"]), x["price_eur"]))

    PRICE_FIELDS = [
        "normalized_product", "product_label",
        "item_name", "menu_section", "price_eur", "price_type",
        "venue_name", "address", "city", "latitude", "longitude",
        "source_platform", "confidence", "source_url", "retrieved_at",
    ]
    with open(UNIFIED_PRICES, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=PRICE_FIELDS, extrasaction="ignore")
        w.writeheader()
        for row in price_rows:
            row["product_label"] = PRODUCT_LABELS.get(row["normalized_product"], row["normalized_product"])
            w.writerow(row)

    # ── 8. Report ─────────────────────────────────────
    report_lines.append(f"\nPrice rows (geo + product + price): {len(price_rows)}")
    report_lines.append("\n--- Product breakdown ---")

    prod_counter = Counter(r["normalized_product"] for r in price_rows)
    for prod, count in sorted(prod_counter.items(), key=lambda x: -x[1]):
        prices = sorted(r["price_eur"] for r in price_rows if r["normalized_product"] == prod)
        if prices:
            med = prices[len(prices)//2]
            label = PRODUCT_LABELS.get(prod, prod)
            report_lines.append(
                f"  {label:25s} {count:4d} prezzi | "
                f"EUR {min(prices):.2f}-{max(prices):.2f} | median {med:.2f}"
            )

    report_lines.append("\n--- Sources breakdown ---")
    src_counter = Counter(r["source_platform"] for r in dedup_items)
    for src, count in sorted(src_counter.items(), key=lambda x: -x[1]):
        report_lines.append(f"  {src}: {count} items")

    report_text = "\n".join(report_lines)
    REPORT_FILE.write_text(report_text, encoding="utf-8")

    # Print summary
    print("\n" + "=" * 60)
    print("MERGE COMPLETE")
    print("=" * 60)
    print(f"  unified_venues.csv    : {len(canonical)} venues")
    print(f"  unified_menu_items.csv: {len(dedup_items)} items")
    print(f"  unified_prices.csv    : {len(price_rows)} price points")
    print(f"\nFonti integrate: {sorted(set(sources_found))}")
    print("\nProdotti:")
    for prod, count in sorted(prod_counter.items(), key=lambda x: -x[1])[:10]:
        print(f"  {PRODUCT_LABELS.get(prod,prod):25s} {count}")
    print(f"\nReport: {REPORT_FILE}")
    print("=" * 60)

    # ── 9. Auto-rebuild website/prices_data.json ───────
    rebuild_website_json(price_rows)


def rebuild_website_json(price_rows: list[dict]):
    """Rebuild website/prices_data.json from current unified_prices."""
    website_dir = Path("website")
    if not website_dir.exists():
        return

    from collections import defaultdict

    PRODUCT_LABELS_WEB = {
        "spritz": "Spritz", "negroni": "Negroni", "americano": "Americano",
        "gin_tonic": "Gin Tonic", "mojito": "Mojito", "moscow_mule": "Moscow Mule",
        "margarita": "Margarita", "daiquiri": "Daiquiri", "manhattan": "Manhattan",
        "beer_draft_small": "Birra Spina Piccola", "beer_draft_medium": "Birra Spina Media",
        "beer_draft": "Birra alla Spina", "beer_bottle": "Birra Bottiglia",
        "beer_moretti": "Birra Moretti", "beer_heineken": "Heineken",
        "beer_peroni": "Peroni/Nastro Azzurro",
        "wine_glass": "Vino al Calice", "prosecco_glass": "Prosecco Calice",
        "espresso": "Caffe", "cappuccino": "Cappuccino",
        "soft_drink": "Bibita", "water": "Acqua", "custom_cocktail": "Cocktail Custom",
    }

    venue_by_product: dict = defaultdict(dict)
    for row in price_rows:
        code  = row["normalized_product"]
        if not code or not row.get("latitude"):
            continue
        vid = row["venue_name"] + "|" + str(row.get("latitude",""))
        if vid not in venue_by_product[code]:
            venue_by_product[code][vid] = {
                "venue_name": row["venue_name"],
                "address":    row.get("address",""),
                "lat":        float(row["latitude"]),
                "lng":        float(row.get("longitude", 0)),
                "price_tier": row.get("price_tier",""),
                "categories": row.get("categories",""),
                "sources":    set(),
                "items":      [],
            }
        venue_by_product[code][vid]["items"].append({
            "name":    row["item_name"],
            "section": row.get("menu_section",""),
            "price":   float(row["price_eur"]),
        })
        venue_by_product[code][vid]["sources"].add(row.get("source_platform",""))

    output = {}
    for code, venues_dict in venue_by_product.items():
        venues_list = list(venues_dict.values())
        for v in venues_list:
            v["items"].sort(key=lambda x: x["price"])
            v["min_price"] = v["items"][0]["price"]
            v["sources"] = list(v["sources"])
        venues_list.sort(key=lambda x: x["min_price"])
        output[code] = {
            "code":   code,
            "label":  PRODUCT_LABELS_WEB.get(code, code.replace("_", " ").title()),
            "count":  len(venues_list),
            "venues": venues_list,
        }

    out_path = website_dir / "prices_data.json"
    import json
    out_path.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")

    n_venues = sum(p["count"] for p in output.values())
    print(f"\n  website/prices_data.json rebuilt: {len(output)} products, {n_venues} venue-product pairs")


if __name__ == "__main__":
    main()
