"""
MyCIA Milano Nightlife Venue & Menu Extractor
=============================================
Extracts venue data and menu prices from mycia.it for Milan bar/pub/cocktail categories.

Strategy:
  1. Download sitemap XML → collect all /menu/milano/ URLs
  2. Fetch each venue page (server-rendered HTML + JSON-LD)
  3. Parse venue info and menu items
  4. Filter to target nightlife/bar categories
  5. Output 3 CSV files

Run:
  python mycia_scraper.py

Resume:  re-run any time — already-cached pages are not re-downloaded.
"""

import csv
import hashlib
import json
import os
import re
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
from tqdm import tqdm

# ─────────────────────────────────────────────
# CONFIGURATION
# ─────────────────────────────────────────────

BASE_URL = "https://www.mycia.it"
SITEMAP_URL = "https://www.mycia.it/sitemap.xml"
CITY_SLUG = "milano"

TARGET_CATEGORIES = {
    "enoteca", "taverna", "wine bar", "pub", "ristopub", "bar",
    "lounge bar", "birreria", "cocktail bar", "café", "cafe",
    "contemporary bar", "casual cocktail bar", "fashion cocktail bar",
    "premium cocktail bar", "mixology cocktail bar",
}

DRINK_SECTIONS_KEYWORDS = {
    "spritz", "cocktail", "coctel", "cocteles", "classic cocktail", "premium cocktail",
    "drinks", "drink", "aperitivi", "aperitivo", "aperitif",
    "birre", "birra", "birre alla spina", "birra alla spina",
    "birre in bottiglia", "birra in bottiglia", "birre artigianali",
    "vini", "vino", "calici", "calice", "analcolici", "analcolico",
    "bevande", "bevanda", "caffetteria", "caffe", "caffè",
    "liquori", "liquore", "amari", "amaro", "digestivi", "digestivo",
    "long drink", "mocktail", "prosecco", "bollicine",
    "gin", "rum", "vodka", "whisky", "whiskey", "tequila",
    "softies", "soft drink", "softdrink", "bibite", "bibita",
    "acqua", "succhi", "succo", "grandi classici",
}

# Products that are always drinks regardless of section name
DRINK_NORMALIZED_PRODUCTS = {
    "spritz", "negroni", "americano", "gin_tonic", "moscow_mule",
    "margarita", "mojito", "manhattan", "daiquiri", "beer_draft_small",
    "beer_draft_medium", "beer_bottle", "wine_glass", "soft_drink",
    "water", "espresso",
}

# Map MyCIA's numeric priceRange to € tier symbols
PRICE_TIER_MAP = {"1": "€", "2": "€€", "3": "€€€", "4": "€€€€"}

REQUEST_DELAY = 1.5   # seconds between requests
REQUEST_TIMEOUT = 20  # seconds

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "it-IT,it;q=0.9,en;q=0.8",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

OUTPUT_DIR = Path(".")
RAW_DIR = Path("raw_data")
RAW_DIR.mkdir(exist_ok=True)

VENUES_CSV = OUTPUT_DIR / "mycia_milano_venues.csv"
MENU_CSV = OUTPUT_DIR / "mycia_milano_menu_items.csv"
LOG_CSV = OUTPUT_DIR / "mycia_extraction_log.csv"

# ─────────────────────────────────────────────
# PRODUCT NORMALIZATION
# ─────────────────────────────────────────────

PRODUCT_RULES = [
    (r"\bspritz\b", "spritz"),
    (r"\baperspritz\b", "spritz"),
    (r"\bnegroni\b", "negroni"),
    (r"\bamericano\b", "americano"),
    (r"\bgin\s*[&e]\s*tonic\b", "gin_tonic"),
    (r"\bgin\s*tonic\b", "gin_tonic"),
    (r"\bmoscow\s*mule\b", "moscow_mule"),
    (r"\bmargarita\b", "margarita"),
    (r"\bmojito\b", "mojito"),
    (r"\bmanhattan\b", "manhattan"),
    (r"\bdaiquiri\b", "daiquiri"),
    (r"\bespresso\b", "espresso"),
    (r"\bcaffè\b", "espresso"),
    (r"\bcaffe\b", "espresso"),
    (r"\bcoca\s*cola\b", "soft_drink"),
    (r"\bpepsi\b", "soft_drink"),
    (r"\bfanta\b", "soft_drink"),
    (r"\bbibita\b", "soft_drink"),
    (r"\bacqua\b", "water"),
    (r"\bwater\b", "water"),
    (r"\bcalice\b", "wine_glass"),
    (r"\bvino\s+al\s+bicchiere\b", "wine_glass"),
    (r"\bbirra?\s+alla\s+spina.{0,15}(piccol|0[,.]?[23]|33\s*cl)", "beer_draft_small"),
    (r"\bbirra?\s+alla\s+spina.{0,15}(medi|0[,.]?[45]|40\s*cl|50\s*cl)", "beer_draft_medium"),
    (r"\bbirra?\s+piccol", "beer_draft_small"),
    (r"\bbirra?\s+medi", "beer_draft_medium"),
    (r"\bbirra?\s+in\s+bottiglia\b", "beer_bottle"),
    (r"\bbirra?\s+bottigli", "beer_bottle"),
    (r"\bbottled\s+beer\b", "beer_bottle"),
]


def normalize_product(name: str) -> tuple[str, str]:
    """Return (normalized_product, confidence)."""
    low = name.lower()
    for pattern, product in PRODUCT_RULES:
        if re.search(pattern, low):
            return product, "high"
    # Partial keyword match
    for pattern, product in PRODUCT_RULES:
        core = pattern.replace(r"\b", "").replace("\\s*", " ").replace("\\s+", " ")
        if core.strip() in low:
            return product, "medium"
    return "", "low"


# ─────────────────────────────────────────────
# PRICE EXTRACTION
# ─────────────────────────────────────────────

PRICE_RE = re.compile(
    r"(?:€\s*)?(\d{1,3}(?:[.,]\d{1,2})?)\s*€?",
    re.IGNORECASE,
)


def parse_price(raw: str) -> float | None:
    """Return float EUR or None."""
    if not raw:
        return None
    m = PRICE_RE.search(raw.strip())
    if not m:
        return None
    try:
        return float(m.group(1).replace(",", "."))
    except ValueError:
        return None


# ─────────────────────────────────────────────
# HTTP HELPERS
# ─────────────────────────────────────────────

session = requests.Session()
session.headers.update(HEADERS)


def _cache_path(url: str) -> Path:
    key = hashlib.md5(url.encode()).hexdigest()
    return RAW_DIR / f"{key}.html"


def fetch(url: str, use_cache: bool = True) -> str | None:
    """Fetch URL with disk cache. Returns HTML string or None on error."""
    cache = _cache_path(url)
    if use_cache and cache.exists():
        return cache.read_text(encoding="utf-8", errors="replace")

    try:
        r = session.get(url, timeout=REQUEST_TIMEOUT)
        if r.status_code == 429:
            log_action(url, "fetch", "rate_limited", "HTTP 429 — sleeping 30s")
            time.sleep(30)
            r = session.get(url, timeout=REQUEST_TIMEOUT)
        if r.status_code != 200:
            log_action(url, "fetch", f"http_{r.status_code}", f"Status {r.status_code}")
            return None
        html = r.text
        cache.write_text(html, encoding="utf-8")
        time.sleep(REQUEST_DELAY)
        return html
    except Exception as exc:
        log_action(url, "fetch", "error", str(exc))
        return None


# ─────────────────────────────────────────────
# LOGGING
# ─────────────────────────────────────────────

_log_writer = None
_log_file = None


def init_log():
    global _log_writer, _log_file
    _log_file = open(LOG_CSV, "a", newline="", encoding="utf-8")
    _log_writer = csv.writer(_log_file)
    if os.path.getsize(LOG_CSV) == 0:
        _log_writer.writerow(["timestamp", "url", "action", "status", "error_message", "notes"])


def log_action(url: str, action: str, status: str, error: str = "", notes: str = ""):
    if _log_writer:
        _log_writer.writerow([
            datetime.now(timezone.utc).isoformat(),
            url, action, status, error, notes,
        ])
        _log_file.flush()


# ─────────────────────────────────────────────
# SITEMAP → VENUE URLs
# ─────────────────────────────────────────────

def get_milano_urls() -> list[str]:
    """Download sitemap and return all /menu/milano/ URLs."""
    print("Fetching sitemap…")
    html = fetch(SITEMAP_URL, use_cache=False)
    if not html:
        print("  ERROR: Could not fetch sitemap")
        return []

    # Parse XML
    urls = []
    try:
        root = ET.fromstring(html)
        ns = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}

        # Check if this is a sitemap index
        for sitemap_el in root.findall("sm:sitemap", ns):
            loc = sitemap_el.find("sm:loc", ns)
            if loc is not None:
                sub = fetch(loc.text, use_cache=True)
                if sub:
                    sub_root = ET.fromstring(sub)
                    for url_el in sub_root.findall("sm:url", ns):
                        loc2 = url_el.find("sm:loc", ns)
                        if loc2 is not None and f"/menu/{CITY_SLUG}/" in loc2.text:
                            urls.append(loc2.text)

        # Single sitemap
        for url_el in root.findall("sm:url", ns):
            loc = url_el.find("sm:loc", ns)
            if loc is not None and f"/menu/{CITY_SLUG}/" in loc.text:
                urls.append(loc.text)

    except ET.ParseError:
        # Fallback: regex
        urls = re.findall(
            rf"<loc>(https://www\.mycia\.it/menu/{CITY_SLUG}/[^<]+)</loc>",
            html,
        )

    urls = list(dict.fromkeys(urls))  # deduplicate preserving order
    print(f"  Found {len(urls)} Milano venue URLs in sitemap")
    log_action(SITEMAP_URL, "sitemap_parse", "ok", notes=f"{len(urls)} milano urls")
    return urls


# ─────────────────────────────────────────────
# VENUE PAGE PARSING
# ─────────────────────────────────────────────

def slug_to_id(url: str) -> str:
    """Extract venue ID from URL slug (last hyphen-separated token)."""
    path = url.rstrip("/").split("/")[-1]
    parts = path.rsplit("-", 1)
    return parts[-1] if len(parts) == 2 else path


def parse_venue(url: str, html: str) -> dict:
    """Parse venue info from page HTML."""
    soup = BeautifulSoup(html, "lxml")
    venue: dict = {
        "venue_id": slug_to_id(url),
        "venue_name": "",
        "venue_url": url,
        "menu_url": url,
        "address": "",
        "city": "Milano",
        "latitude": "",
        "longitude": "",
        "categories": "",
        "price_tier": "",
        "rating": "",
        "opening_hours": "",
        "extraction_status": "pending",
        "source_provider": "mycia",
        "retrieved_at": datetime.now(timezone.utc).isoformat(),
    }

    # ── JSON-LD structured data ──────────────────────
    # MyCIA serves multiple JSON-LD blocks; pick the richest fields
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(script.string or "")
            schemas = data if isinstance(data, list) else [data]
            for s in schemas:
                t = s.get("@type", "")
                if t not in ("Restaurant", "FoodEstablishment", "BarOrPub",
                             "CafeOrCoffeeShop", "NightClub"):
                    continue

                # Name — use first non-empty value
                venue["venue_name"] = venue["venue_name"] or s.get("name", "").strip()

                # Address — build from PostalAddress fields
                if not venue["address"]:
                    addr = s.get("address", {})
                    if isinstance(addr, dict):
                        street = addr.get("streetAddress", "").strip()
                        postal = addr.get("postalCode", "").strip()
                        locality = addr.get("addressLocality", "").strip()
                        parts = [p for p in [street, postal, locality] if p and p != "Milano"]
                        if parts:
                            venue["address"] = ", ".join(parts)

                # Geo — keep first found (small JSON-LD has it)
                if not venue["latitude"]:
                    geo = s.get("geo", {})
                    if isinstance(geo, dict) and geo.get("latitude"):
                        venue["latitude"] = str(geo["latitude"])
                        venue["longitude"] = str(geo.get("longitude", ""))

                # Categories
                if not venue["categories"]:
                    cats = s.get("servesCuisine", [])
                    if isinstance(cats, str):
                        cats = [cats]
                    if cats:
                        venue["categories"] = "; ".join(c.strip() for c in cats if c.strip())

                # Opening hours
                if not venue["opening_hours"]:
                    hours = s.get("openingHours", [])
                    if isinstance(hours, list):
                        venue["opening_hours"] = " | ".join(hours)
                    elif isinstance(hours, str):
                        venue["opening_hours"] = hours

                # Price tier — MyCIA uses numeric 1-4; map to € symbols
                if not venue["price_tier"]:
                    pr = str(s.get("priceRange", "")).strip()
                    venue["price_tier"] = PRICE_TIER_MAP.get(pr, pr)

                # Rating
                if not venue["rating"]:
                    ar = s.get("aggregateRating", {})
                    if isinstance(ar, dict):
                        venue["rating"] = str(ar.get("ratingValue", ""))

        except (json.JSONDecodeError, AttributeError):
            pass

    # ── Meta / OG fallbacks ──────────────────────────
    if not venue["venue_name"]:
        og = soup.find("meta", property="og:title")
        if og:
            venue["venue_name"] = og.get("content", "").split(" - ")[0].strip()
    if not venue["venue_name"]:
        h1 = soup.find("h1")
        if h1:
            venue["venue_name"] = h1.get_text(strip=True)

    # ── Latitude from data attribute fallback ────────
    if not venue["latitude"]:
        map_el = soup.find(attrs={"data-lat": True})
        if map_el:
            venue["latitude"] = map_el["data-lat"]
            venue["longitude"] = map_el.get("data-lng", "")

    # ── Clean up venue name ──────────────────────────
    venue["venue_name"] = venue["venue_name"].strip()

    return venue


def is_target_category(categories: str) -> bool:
    """Return True if at least one category is in our target list."""
    cats_low = categories.lower()
    return any(tc in cats_low for tc in TARGET_CATEGORIES)


# ─────────────────────────────────────────────
# MENU PARSING
# ─────────────────────────────────────────────

def _section_is_drink(section_name: str) -> bool:
    low = section_name.lower()
    return any(kw in low for kw in DRINK_SECTIONS_KEYWORDS)


def parse_menu(url: str, html: str, venue_id: str, venue_name: str) -> list[dict]:
    """Extract menu items from page. Returns list of item dicts."""
    soup = BeautifulSoup(html, "lxml")
    items = []
    now = datetime.now(timezone.utc).isoformat()

    def make_item(section, name, description, raw_price):
        norm_prod, conf = normalize_product(name)
        is_drink = (
            _section_is_drink(section)
            or _section_is_drink(name)
            or norm_prod in DRINK_NORMALIZED_PRODUCTS
        )
        price_eur = parse_price(raw_price)
        return {
            "venue_id": venue_id,
            "venue_name": venue_name,
            "source_url": url,
            "menu_section": section,
            "item_name": name,
            "item_description": description,
            "raw_price": raw_price,
            "normalized_price_eur": price_eur if price_eur is not None else "",
            "currency": "EUR" if price_eur is not None else "",
            "item_type": "drink" if is_drink else "non_drink",
            "normalized_product": norm_prod,
            "confidence": conf,
            "retrieved_at": now,
        }

    seen: set = set()

    def add_item(section, name, desc, raw_price):
        key = (venue_id, section, name, raw_price)
        if name and key not in seen:
            seen.add(key)
            items.append(make_item(section, name, desc, raw_price))

    # ── JSON-LD: Restaurant → menu[] → hasMenuSection[] → hasMenuItem[] ──
    # MyCIA embeds the full menu in the Restaurant JSON-LD as a 'menu' array.
    # Each element is a Menu object with hasMenuSection arrays.
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(script.string or "")
            schemas = data if isinstance(data, list) else [data]
            for s in schemas:
                t = s.get("@type", "")

                # Restaurant with inline menu array (primary MyCIA pattern)
                if t in ("Restaurant", "FoodEstablishment", "BarOrPub", "CafeOrCoffeeShop"):
                    for menu_obj in s.get("menu", []):
                        if not isinstance(menu_obj, dict):
                            continue
                        for section in menu_obj.get("hasMenuSection", []):
                            section_name = section.get("name", "Menu").strip()
                            for entry in section.get("hasMenuItem", []):
                                name = entry.get("name", "").strip()
                                desc = entry.get("description", "").strip()
                                offer = entry.get("offers", {})
                                price_val = offer.get("price", "") if isinstance(offer, dict) else ""
                                # Treat 0 / "0" as unknown price
                                try:
                                    raw = "" if float(str(price_val)) == 0 else str(price_val)
                                except (ValueError, TypeError):
                                    raw = str(price_val)
                                add_item(section_name, name, desc, raw)

                # Standalone Menu object
                if t == "Menu":
                    for section in s.get("hasMenuSection", []):
                        section_name = section.get("name", "Menu").strip()
                        for entry in section.get("hasMenuItem", []):
                            name = entry.get("name", "").strip()
                            desc = entry.get("description", "").strip()
                            offer = entry.get("offers", {})
                            price_val = offer.get("price", "") if isinstance(offer, dict) else ""
                            try:
                                raw = "" if float(str(price_val)) == 0 else str(price_val)
                            except (ValueError, TypeError):
                                raw = str(price_val)
                            add_item(section_name, name, desc, raw)

        except (json.JSONDecodeError, AttributeError):
            pass

    # ── HTML fallback: scan for price-adjacent text ──
    # Only used if JSON-LD gave nothing
    if not items:
        current_section = "Menu"
        for el in soup.find_all(string=re.compile(r"\d+[.,]\d{1,2}\s*€|€\s*\d")):
            parent = el.parent
            if not parent:
                continue
            row = parent.find_parent(["tr", "li", "div", "article"])
            if row:
                text_parts = [t.strip() for t in row.stripped_strings if t.strip()]
                if len(text_parts) >= 2:
                    name = text_parts[0]
                    raw_price = str(el).strip()
                    add_item(current_section, name, "", raw_price)

    return items


# ─────────────────────────────────────────────
# CSV WRITERS
# ─────────────────────────────────────────────

VENUE_FIELDS = [
    "venue_id", "venue_name", "venue_url", "menu_url", "address", "city",
    "latitude", "longitude", "categories", "price_tier", "rating",
    "opening_hours", "extraction_status", "source_provider", "retrieved_at",
]

MENU_FIELDS = [
    "venue_id", "venue_name", "source_url", "menu_section", "item_name",
    "item_description", "raw_price", "normalized_price_eur", "currency",
    "item_type", "normalized_product", "confidence", "retrieved_at",
]


def init_csv(path: Path, fields: list[str]) -> csv.DictWriter:
    """Open CSV for appending, write header if new."""
    is_new = not path.exists() or path.stat().st_size == 0
    f = open(path, "a", newline="", encoding="utf-8")
    writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
    if is_new:
        writer.writeheader()
    return writer


# ─────────────────────────────────────────────
# CHECKPOINT (resumability)
# ─────────────────────────────────────────────

CHECKPOINT_FILE = Path("mycia_checkpoint.txt")


def load_checkpoint() -> set[str]:
    if not CHECKPOINT_FILE.exists():
        return set()
    return set(CHECKPOINT_FILE.read_text().splitlines())


def save_checkpoint(url: str, done: set[str]):
    done.add(url)
    CHECKPOINT_FILE.write_text("\n".join(sorted(done)))


# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────

def main():
    print("=" * 60)
    print("MyCIA Milano Extractor")
    print("=" * 60)

    init_log()

    venue_writer = init_csv(VENUES_CSV, VENUE_FIELDS)
    menu_writer = init_csv(MENU_CSV, MENU_FIELDS)

    done = load_checkpoint()
    print(f"Resuming: {len(done)} venues already processed")

    urls = get_milano_urls()
    if not urls:
        print("No URLs found — aborting.")
        return

    total_venues = 0
    target_venues = 0
    total_items = 0
    skipped = 0

    for url in tqdm(urls, desc="Venues", unit="venue"):
        if url in done:
            skipped += 1
            continue

        html = fetch(url)
        if not html:
            log_action(url, "parse_venue", "skip_no_html")
            save_checkpoint(url, done)
            continue

        venue = parse_venue(url, html)
        total_venues += 1

        # Category filter
        if not venue["categories"]:
            # No category info — keep and mark uncertain
            venue["extraction_status"] = "no_category"
        elif not is_target_category(venue["categories"]):
            venue["extraction_status"] = "filtered_out"
            log_action(url, "category_filter", "filtered_out", notes=venue["categories"])
            venue_writer.writerow(venue)
            save_checkpoint(url, done)
            continue
        else:
            venue["extraction_status"] = "ok"
            target_venues += 1

        # Menu extraction
        items = parse_menu(url, html, venue["venue_id"], venue["venue_name"])

        if items:
            venue["extraction_status"] = "ok_with_menu"
            for item in items:
                menu_writer.writerow(item)
            total_items += len(items)
            log_action(url, "extract_menu", "ok", notes=f"{len(items)} items")
        else:
            if venue["extraction_status"] == "ok":
                venue["extraction_status"] = "ok_no_menu"
            log_action(url, "extract_menu", "no_items_found")

        venue_writer.writerow(venue)
        save_checkpoint(url, done)

    print("\n" + "=" * 60)
    print(f"Done.")
    print(f"  Venues visited   : {total_venues}")
    print(f"  Target category  : {target_venues}")
    print(f"  Menu items found : {total_items}")
    print(f"  Already done     : {skipped}")
    print(f"\nOutputs:")
    print(f"  {VENUES_CSV}")
    print(f"  {MENU_CSV}")
    print(f"  {LOG_CSV}")
    print("=" * 60)

    log_action("main", "run_complete", "ok",
               notes=f"venues={total_venues} target={target_venues} items={total_items}")


if __name__ == "__main__":
    main()
