"""
SurPrice normalization library — quality gate condivisa.

USO IN AGENT SCRAPER (PRIMA di consegnare CSV):
    from scripts.normalization import clean_item_product, is_milan_or_unknown, PRICE_RANGES

    # Filtra ogni item prima di scrivere
    for item in raw_items:
        corrected_prod, skip_reason = clean_item_product(item)
        if skip_reason:
            continue
        item['normalized_product'] = corrected_prod
        # ... write item

    # Filtra venues per città
    for v in raw_venues:
        if not is_milan_or_unknown(v.get('address','')):
            continue

USO NEL MERGE_PIPELINE (CEO):
    Le funzioni sono importate e applicate inline durante il merge.

PHILOSOPHY:
- Inline gate > post-hoc cleanup (lezione S3 → S4/S5)
- Vocabolario chiuso normalized_product (22 codici)
- Banda prezzo per prodotto (realistic Milano)
- Pattern noise filter HTML scraping
- Disambiguazione brand (Moretti birra vs Vittorio Moretti vino)
"""
import re

# ─────────────────────────────────────────────
# PRICE RANGES (banda min/max per prodotto, EUR Milano realistic)
# ─────────────────────────────────────────────
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

# Vocabolario chiuso normalized_product
VALID_PRODUCTS = set(PRICE_RANGES.keys()) | {''}

# Cities non-Milan note (per quick check, ma il main check è CAP)
NON_MILAN_CITIES = [
    'pessione','torino','palermo','siena','parma','ferrara','lecce','trento',
    'roma','napoli','genova','venezia','firenze','san ferdinando','sondrio',
    'pavia','varese','como','bergamo','brescia','aradeo','transacqua','colombano',
    'assago','collecchio','biella','udine','pordenone','savona','livorno',
    'taranto','cagliari','sardara','reggio','cosenza','ancona','foggia','cremona',
    'urbania','misano','iglesias','agrigento','salerno','potenza','vignola',
]


# ─────────────────────────────────────────────
# CITY FILTER (CAP-based)
# ─────────────────────────────────────────────
def is_milan_or_unknown(addr: str) -> bool:
    """
    True se address è plausibilmente Milano (CAP 20xxx) o se non c'è CAP.
    False solo se address ha CAP NON-Milano esplicito.
    """
    if not addr:
        return True
    caps = re.findall(r'\b(\d{5})\b', addr)
    if not caps:
        return True
    for cap in caps:
        if 20000 <= int(cap) <= 20999:
            return True
    return False


# ─────────────────────────────────────────────
# ITEM CLEANER — reclassifica/skip falsi positivi
# ─────────────────────────────────────────────
def clean_item_product(item: dict) -> tuple:
    """
    Audit/cleanup per item:
    - Reclassifica/rimuove falsi positivi
    - Filtra noise nei nomi
    Returns: (corrected_product, reason_if_skipped)
        - se reason!=None: SCARTA item
        - se reason==None: usa corrected_product come normalized_product
    """
    prod = (item.get("normalized_product","") or "").strip()
    name = (item.get("item_name","") or "")
    desc = (item.get("item_description","") or "")
    try: price = float(item.get("normalized_price_eur", 0) or 0)
    except: price = 0
    name_lower = name.lower()

    # 1. PRODUCT FIXES (modifica normalized_product)
    # 1a. Coffee classificato come americano cocktail (cocktail = Campari+vermouth)
    if prod == 'americano':
        if 'caff' in name_lower and price < 4:
            return '', None
        if 'caff' in name_lower and price < 5:
            if re.search(r'caff[eè]\s*americano', name_lower):
                return '', None
    # 1b. Espresso classificato male
    if prod == 'espresso':
        if re.search(r'\b(martini|cocktail|affogato|mixed)\b', name_lower):
            return 'custom_cocktail', None
        if 'corretto' in name_lower and price > 3:
            return '', None
    # 1c. Prosecco glass quando è bottiglia
    if prod == 'prosecco_glass':
        if re.search(r'\bbottiglia\b', name_lower) and price > 15:
            return None, 'PROSECCO_BOTTIGLIA'
        if price > 15:
            return None, 'PROSECCO_GLASS_TOO_HIGH'
    # 1d. Beer Moretti = Vittorio Moretti (Franciacorta) o spumante
    if prod == 'beer_moretti':
        if re.search(r'\bvittorio\b|\briserva\b|\bextra\s*brut\b|\bbrut\b|\bspumante\b|\bfranciacorta\b', name_lower):
            return None, 'MORETTI_SPUMANTE'
    # 1e. Beer bottle ma è vino o food
    if prod == 'beer_bottle':
        if re.search(r'\b(vino|valpolicella|barolo|chianti|antipasto|ripasso|riserva)\b', name_lower):
            return None, 'BEER_BOTTLE_IS_FOOD_OR_WINE'
    # 1f. Mojito che è Bloody Mary
    if prod == 'mojito':
        if 'bloody mary' in name_lower or ('licorice' in name_lower and 'mary' in name_lower):
            return None, 'MOJITO_IS_BLOODY_MARY'
    # 1g. Margarita caraffa (pitcher)
    if prod == 'margarita':
        if 'caraffa' in name_lower or 'pitcher' in name_lower or price > 30:
            return None, 'MARGARITA_CARAFFA'
    # 1g-bis. FORMATO MAXI (multi-porzione) — tutti i cocktail
    if prod in ('spritz','negroni','americano','gin_tonic','mojito','moscow_mule',
                'margarita','daiquiri','manhattan','custom_cocktail'):
        if re.search(r'\bmaxi\b|\bcaraffa\b|\bpitcher\b|\bbrocca\b|\blitro\b|1\s*l(?:itro|t)?\b', name_lower):
            return None, 'FORMAT_MAXI'
    # 1h. Spritz mismatch -> soft_drink/wine_glass
    if prod == 'spritz':
        if re.search(r'\b(coca\s*cola|fanta|sprite|soft\s*drinks?)\b', name_lower) and 'spritz' not in name_lower:
            return 'soft_drink', None
        if re.search(r'\b(calice|vino\s+(?:bianco|rosso|al\s+calice))\b', name_lower) and 'spritz' not in name_lower:
            return 'wine_glass', None
        if re.search(r'\bbirra\b', name_lower) and 'spritz' not in name_lower:
            return None, 'SPRITZ_IS_BEER'
        if re.search(r'\b(caff[eè]|espresso|cappuccino)\b', name_lower) and 'spritz' not in name_lower:
            return None, 'SPRITZ_IS_COFFEE'

    # 2. NAME NOISE FILTERS
    NOISE_PATTERNS = [
        r'menu\s*[-–]\s*',
        r'salta\s+al\s+contenuto',
        r'menu\s+digitale',
        r'vai\s+alla\s+(header|footer)',
        r'#8211|#8217|&nbsp;',
        r'^\s*(home|contatti|chi\s+siamo|menu)\s*$',
        r'\bmail\s+us\b',
        r'@\w+\.\w+',
        r'\bwhere:\s*\w+',
        r'^\s*[\W\d]+\s*[A-Z]+[\W\d]+',
    ]
    for p in NOISE_PATTERNS:
        if re.search(p, name_lower, re.I):
            return None, 'NAME_NOISE'
    if name.count('€') >= 4:
        return None, 'NAME_MULTI_EURO_CONCAT'

    # 3. ITEM_NAME parser noise: page-title HTML
    if len(name) > 50:
        nav_kw = ['home', 'chi siamo', 'contatti', 'footer', 'header', 'navigation',
                  'salta al contenuto', 'toggle navigation', 'mail us', 'team news',
                  'about chef', 'seleziona una pagina', 'leggi il menu digitale',
                  'menu prenotazioni', 'instagram facebook']
        nav_hits = sum(1 for kw in nav_kw if kw in name_lower)
        if nav_hits >= 2:
            return None, 'NAME_PARSER_NOISE'
        if 'menu' in name_lower and nav_hits >= 1:
            return None, 'NAME_PARSER_NOISE'

    # 4. ITEM_NAME troppo lungo + page-like
    if len(name) > 100 and re.search(r'\b(home|menu|chi\s+siamo|contatti|footer|header)\b', name_lower):
        return None, 'NAME_TOO_LONG_PAGE'

    return prod, None


# ─────────────────────────────────────────────
# PRICE RANGE CHECK
# ─────────────────────────────────────────────
def is_price_in_range(product: str, price: float) -> bool:
    """True se prezzo dentro banda realistic per prodotto."""
    if product not in PRICE_RANGES:
        return True  # prodotto non in vocab, lascia passare
    lo, hi = PRICE_RANGES[product]
    return lo <= price <= hi


# ─────────────────────────────────────────────
# FULL VALIDATION (all-in-one per agent scraper)
# ─────────────────────────────────────────────
def validate_item(item: dict) -> tuple:
    """
    Validazione completa item.
    Returns: (is_valid, item_or_None, reason)
    """
    corrected_prod, skip_reason = clean_item_product(item)
    if skip_reason:
        return False, None, skip_reason
    # Update product
    if corrected_prod is not None:
        item['normalized_product'] = corrected_prod
    # Price range
    try: price = float(item.get('normalized_price_eur', 0) or 0)
    except: price = 0
    if corrected_prod and not is_price_in_range(corrected_prod, price):
        return False, None, f'PRICE_OUT_OF_RANGE_{corrected_prod}'
    return True, item, None
