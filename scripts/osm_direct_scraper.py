"""
osm_direct_scraper.py — OSM + Direct Website Menu Scraper
==========================================================
1. Queries OpenStreetMap Overpass API for bars/pubs in Milan with website URLs
2. Fetches each official website looking for drink prices
3. Outputs to raw_sources/direct_venues.csv + raw_sources/direct_menu_items.csv

Run:  python osm_direct_scraper.py
"""

import csv
import hashlib
import json
import re
import time
import sys
from datetime import datetime, timezone
from pathlib import Path

import requests
from bs4 import BeautifulSoup

# ─────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────

OUTPUT_DIR  = Path("raw_sources")
OUTPUT_DIR.mkdir(exist_ok=True)
RAW_DIR     = Path("raw_data_direct")
RAW_DIR.mkdir(exist_ok=True)

VENUES_CSV = OUTPUT_DIR / "direct_venues.csv"
ITEMS_CSV  = OUTPUT_DIR / "direct_menu_items.csv"

REQUEST_DELAY = 2.0
TIMEOUT       = 15
MAX_VENUES    = 300  # cap to avoid abuse

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; FoodPriceResearch/1.0; +https://github.com/foodprice)",
    "Accept": "text/html,application/xhtml+xml,*/*",
    "Accept-Language": "it-IT,it;q=0.9,en;q=0.8",
}

# Milan bounding box: south,west,north,east
MILAN_BBOX = "45.38,9.03,45.55,9.30"

# ─────────────────────────────────────────────
# PRODUCT NORMALIZATION (copy from mycia_scraper)
# ─────────────────────────────────────────────

PRODUCT_RULES = [
    (r"\bspritz\b",                     "spritz"),
    (r"\baperspritz\b",                 "spritz"),
    (r"\bnegroni\b",                    "negroni"),
    (r"\bamericano\b",                  "americano"),
    (r"\bgin\s*[&e]\s*tonic\b",         "gin_tonic"),
    (r"\bgin\s*tonic\b",                "gin_tonic"),
    (r"\bmoscow\s*mule\b",              "moscow_mule"),
    (r"\bmargarita\b",                  "margarita"),
    (r"\bmojito\b",                     "mojito"),
    (r"\bmanhattan\b",                  "manhattan"),
    (r"\bdaiquiri\b",                   "daiquiri"),
    (r"\bespresso\b|\bcaff[eè]\b",      "espresso"),
    (r"\bcoca.?cola\b|\bpepsi\b|\bfanta\b|\bbibita\b", "soft_drink"),
    (r"\bacqua\b|\bwater\b",            "water"),
    (r"\bcalice\b|\bvino.{0,10}(calice|bicchiere)\b", "wine_glass"),
    (r"\bmoretti\b",                    "beer_moretti"),
    (r"\bheineken\b",                   "beer_heineken"),
    (r"\bperoni\b|\bnastro\s*azzurro\b","beer_peroni"),
    (r"\bbirra?\s+alla\s+spina.{0,15}(piccol|0[,.]?[23]|33\s*cl)", "beer_draft_small"),
    (r"\bbirra?\s+alla\s+spina.{0,15}(medi|0[,.]?[45]|40\s*cl|50\s*cl)", "beer_draft_medium"),
    (r"\bbirra?\s+piccol",              "beer_draft_small"),
    (r"\bbirra?\s+medi",                "beer_draft_medium"),
    (r"\bbirra?\s+(in\s+)?bottigli",    "beer_bottle"),
]

DRINK_NORMALIZED = {
    "spritz","negroni","americano","gin_tonic","moscow_mule","margarita","mojito",
    "manhattan","daiquiri","beer_draft_small","beer_draft_medium","beer_bottle",
    "beer_moretti","beer_heineken","beer_peroni","wine_glass","espresso","soft_drink","water",
}

DRINK_SECTION_KEYWORDS = {
    "spritz","cocktail","drink","aperitivi","aperitivo","birra","birre",
    "vini","vino","calici","analcolici","bevande","caffetteria","liquori",
    "gin","rum","vodka","whisky","amari","digestivi","long drink",
}

PRICE_RE = re.compile(r"(?:€\s*)?(\d{1,3}(?:[.,]\d{1,2})?)\s*€?")
FOOD_SECTION_RE = re.compile(
    r"\b(pizza|tacos?|burger|panino|piatt|antipast|prim|second|dolci|dessert|pasta|risotto|grill|insalat)\b",
    re.I
)


def normalize_product(name: str):
    low = name.lower()
    for pat, prod in PRODUCT_RULES:
        if re.search(pat, low):
            return prod, "high"
    return "", "low"


def parse_price(raw: str):
    if not raw:
        return None
    m = PRICE_RE.search(raw.strip())
    if m:
        try:
            p = float(m.group(1).replace(",", "."))
            return p if 0.5 < p < 100 else None
        except ValueError:
            return None
    return None


def is_drink_section(section: str) -> bool:
    low = section.lower()
    return any(kw in low for kw in DRINK_SECTION_KEYWORDS)


# ─────────────────────────────────────────────
# HTTP + CACHE
# ─────────────────────────────────────────────

session = requests.Session()
session.headers.update(HEADERS)


def cache_path(url: str) -> Path:
    return RAW_DIR / (hashlib.md5(url.encode()).hexdigest() + ".html")


def fetch(url: str) -> str | None:
    cp = cache_path(url)
    if cp.exists():
        return cp.read_text(encoding="utf-8", errors="replace")
    try:
        r = session.get(url, timeout=TIMEOUT)
        if r.status_code == 200:
            text = r.text
            cp.write_text(text, encoding="utf-8")
            time.sleep(REQUEST_DELAY)
            return text
        else:
            time.sleep(0.5)
            return None
    except Exception:
        return None


# ─────────────────────────────────────────────
# STEP 1: OSM Overpass query
# ─────────────────────────────────────────────

OVERPASS_URL = "https://overpass.kumi.systems/api/interpreter"

OVERPASS_QUERY = (
    f'[out:json][timeout:60];'
    f'(node["amenity"~"^(bar|pub|biergarten|nightclub|cocktail_bar|wine_bar)$"]["website"]({MILAN_BBOX});'
    f'way["amenity"~"^(bar|pub|biergarten|nightclub|cocktail_bar|wine_bar)$"]["website"]({MILAN_BBOX}););'
    f'out center tags;'
)


def fetch_osm_venues() -> list[dict]:
    """Query OSM for Milan bars with websites."""
    print("Querying OpenStreetMap Overpass API...")
    try:
        r = requests.get(
            OVERPASS_URL,
            params={"data": OVERPASS_QUERY},
            timeout=90,
            headers={"User-Agent": HEADERS["User-Agent"]},
        )
        r.raise_for_status()
        data = r.json()
    except Exception as e:
        print(f"  ERROR: {e}")
        return []

    elements = data.get("elements", [])
    print(f"  Found {len(elements)} OSM elements")

    venues = []
    for el in elements:
        tags = el.get("tags", {})
        lat = el.get("lat") or el.get("center", {}).get("lat")
        lng = el.get("lon") or el.get("center", {}).get("lon")
        website = tags.get("website", "").strip()
        if not website or not lat:
            continue
        # Normalise URL
        if not website.startswith("http"):
            website = "https://" + website

        venues.append({
            "osm_id":       str(el.get("id", "")),
            "venue_name":   tags.get("name", "").strip(),
            "website":      website,
            "address":      " ".join(filter(None, [
                tags.get("addr:street",""),
                tags.get("addr:housenumber",""),
            ])),
            "city":         tags.get("addr:city", "Milano"),
            "latitude":     lat,
            "longitude":    lng,
            "amenity":      tags.get("amenity",""),
            "phone":        tags.get("phone",""),
            "opening_hours":tags.get("opening_hours",""),
        })

    print(f"  Venues with websites: {len(venues)}")
    return venues


# ─────────────────────────────────────────────
# STEP 2: Scrape each website for menu/prices
# ─────────────────────────────────────────────

def find_menu_url(base_url: str, html: str) -> str:
    """Try to find a dedicated menu page from the homepage."""
    soup = BeautifulSoup(html, "lxml")
    menu_keywords = re.compile(r"\b(men[uù]|carta|prezzi|drinks?|cocktail|birre)\b", re.I)

    # Look for links containing menu keywords
    for a in soup.find_all("a", href=True):
        text = a.get_text(strip=True)
        href = a["href"]
        if menu_keywords.search(text) or menu_keywords.search(href):
            if href.startswith("http"):
                return href
            elif href.startswith("/"):
                from urllib.parse import urlparse
                parsed = urlparse(base_url)
                return f"{parsed.scheme}://{parsed.netloc}{href}"
    return base_url


def extract_prices_from_html(html: str, source_url: str, venue_id: str, venue_name: str) -> list[dict]:
    """Extract drink items and prices from arbitrary HTML."""
    soup = BeautifulSoup(html, "lxml")
    items = []
    now = datetime.now(timezone.utc).isoformat()
    seen = set()

    # ── JSON-LD (structured menus) ─────────────────
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(script.string or "")
            schemas = data if isinstance(data, list) else [data]
            for s in schemas:
                t = s.get("@type","")
                menus = []
                if t in ("Restaurant","FoodEstablishment","BarOrPub","CafeOrCoffeeShop"):
                    menus = s.get("menu", [])
                    if isinstance(menus, str):
                        # menu is a URL, skip
                        menus = []
                elif t == "Menu":
                    menus = [s]

                for menu_obj in menus:
                    if not isinstance(menu_obj, dict):
                        continue
                    for section in menu_obj.get("hasMenuSection", []):
                        sec_name = section.get("name","").strip()
                        if FOOD_SECTION_RE.search(sec_name) and not is_drink_section(sec_name):
                            continue
                        for entry in section.get("hasMenuItem", []):
                            name = entry.get("name","").strip()
                            desc = entry.get("description","").strip()
                            offer = entry.get("offers", {})
                            price_val = offer.get("price","") if isinstance(offer, dict) else ""
                            try:
                                price = float(str(price_val)) if price_val else 0
                                raw_price = "" if price == 0 else str(price)
                                price = price if price > 0 else None
                            except (ValueError, TypeError):
                                raw_price = str(price_val)
                                price = parse_price(raw_price)

                            prod, conf = normalize_product(name)
                            is_drink = is_drink_section(sec_name) or prod in DRINK_NORMALIZED
                            if not is_drink:
                                continue

                            key = (venue_id, sec_name, name, raw_price)
                            if key not in seen and name:
                                seen.add(key)
                                items.append({
                                    "source_platform":     "direct_website",
                                    "source_venue_id":     venue_id,
                                    "venue_name":          venue_name,
                                    "venue_url":           source_url,
                                    "menu_section":        sec_name,
                                    "item_name":           name,
                                    "item_description":    desc,
                                    "raw_price":           raw_price,
                                    "normalized_price_eur":price or "",
                                    "currency":            "EUR",
                                    "price_type":          "menu",
                                    "item_type":           "drink",
                                    "normalized_product":  prod,
                                    "confidence":          conf,
                                    "allergens":           "",
                                    "retrieved_at":        now,
                                    "source_url":          source_url,
                                })
        except (json.JSONDecodeError, AttributeError):
            pass

    # ── HTML price scan (€X,XX pattern) ───────────
    if not items:
        current_section = "Menu"
        for el in soup.find_all(string=re.compile(r"€\s*\d|\d[,\.]\d{2}\s*€")):
            parent = el.parent
            if not parent:
                continue
            # Check if in a food section (skip)
            section_el = parent.find_parent(
                lambda tag: tag.name in ["section","div","table"] and
                            tag.get("class") and
                            FOOD_SECTION_RE.search(" ".join(str(c) for c in tag.get("class",[])))
            )
            if section_el:
                continue

            row = parent.find_parent(["tr","li","div","article"])
            if not row:
                continue
            texts = [t.strip() for t in row.stripped_strings if t.strip()]
            if len(texts) >= 2:
                name = texts[0]
                raw_price = str(el).strip()
                price = parse_price(raw_price)
                if not price:
                    continue
                prod, conf = normalize_product(name)
                is_drink = prod in DRINK_NORMALIZED or is_drink_section(current_section)
                if not is_drink and conf == "low":
                    continue  # skip unknown items in unknown sections

                key = (venue_id, current_section, name, raw_price)
                if key not in seen and name:
                    seen.add(key)
                    items.append({
                        "source_platform":     "direct_website",
                        "source_venue_id":     venue_id,
                        "venue_name":          venue_name,
                        "venue_url":           source_url,
                        "menu_section":        current_section,
                        "item_name":           name,
                        "item_description":    "",
                        "raw_price":           raw_price,
                        "normalized_price_eur":price,
                        "currency":            "EUR",
                        "price_type":          "menu",
                        "item_type":           "drink",
                        "normalized_product":  prod,
                        "confidence":          conf,
                        "allergens":           "",
                        "retrieved_at":        now,
                        "source_url":          source_url,
                    })

    return items


# ─────────────────────────────────────────────
# CSV HELPERS
# ─────────────────────────────────────────────

VENUE_FIELDS = [
    "source_platform","source_venue_id","venue_name","venue_url","address","city",
    "latitude","longitude","categories","price_tier","rating","rating_count",
    "phone","website","opening_hours","has_menu","menu_url",
    "extraction_status","retrieved_at",
]
ITEM_FIELDS = [
    "source_platform","source_venue_id","venue_name","venue_url","menu_section",
    "item_name","item_description","raw_price","normalized_price_eur","currency",
    "price_type","item_type","normalized_product","confidence","allergens",
    "retrieved_at","source_url",
]

CHECKPOINT = Path("osm_checkpoint.txt")


def load_checkpoint() -> set:
    return set(CHECKPOINT.read_text().splitlines()) if CHECKPOINT.exists() else set()


def save_checkpoint(osm_id: str, done: set):
    done.add(osm_id)
    CHECKPOINT.write_text("\n".join(sorted(done)))


# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────

def main():
    now = datetime.now(timezone.utc).isoformat()
    done = load_checkpoint()
    print(f"Checkpoint: {len(done)} venues already done")

    venues = fetch_osm_venues()
    if not venues:
        print("No venues found — aborting")
        return

    is_new_venues = not VENUES_CSV.exists() or VENUES_CSV.stat().st_size == 0
    is_new_items  = not ITEMS_CSV.exists()   or ITEMS_CSV.stat().st_size == 0

    venue_file = open(VENUES_CSV, "a", newline="", encoding="utf-8-sig")
    items_file = open(ITEMS_CSV,  "a", newline="", encoding="utf-8-sig")
    venue_writer = csv.DictWriter(venue_file, fieldnames=VENUE_FIELDS, extrasaction="ignore")
    items_writer = csv.DictWriter(items_file, fieldnames=ITEM_FIELDS,  extrasaction="ignore")
    if is_new_venues: venue_writer.writeheader()
    if is_new_items:  items_writer.writeheader()

    total_items = 0
    venues_with_menu = 0

    for v in venues[:MAX_VENUES]:
        osm_id = v["osm_id"]
        if osm_id in done:
            continue

        name    = v["venue_name"]
        website = v["website"]
        vid     = f"osm_{osm_id}"

        sys.stdout.buffer.write(f"  {name} → {website}\n".encode("utf-8"))

        # Fetch homepage
        html = fetch(website)
        menu_url = website
        menu_items = []

        if html:
            # Try to find dedicated menu page
            menu_url = find_menu_url(website, html)
            if menu_url != website:
                menu_html = fetch(menu_url)
                if menu_html:
                    menu_items = extract_prices_from_html(menu_html, menu_url, vid, name)

            if not menu_items:
                menu_items = extract_prices_from_html(html, website, vid, name)

        has_menu = len(menu_items) > 0
        status   = "ok_with_menu" if has_menu else ("ok_no_menu" if html else "error")

        venue_writer.writerow({
            "source_platform":  "direct_website",
            "source_venue_id":  vid,
            "venue_name":       name,
            "venue_url":        website,
            "address":          v["address"],
            "city":             v["city"],
            "latitude":         v["latitude"],
            "longitude":        v["longitude"],
            "categories":       v["amenity"],
            "price_tier":       "",
            "rating":           "",
            "rating_count":     "",
            "phone":            v["phone"],
            "website":          website,
            "opening_hours":    v["opening_hours"],
            "has_menu":         str(has_menu),
            "menu_url":         menu_url,
            "extraction_status":status,
            "retrieved_at":     now,
        })
        venue_file.flush()

        if menu_items:
            items_writer.writerows(menu_items)
            items_file.flush()
            total_items += len(menu_items)
            venues_with_menu += 1
            sys.stdout.buffer.write(f"    +{len(menu_items)} items\n".encode("utf-8"))

        save_checkpoint(osm_id, done)

    venue_file.close()
    items_file.close()

    print(f"\nDone.")
    print(f"  Venues processed : {len(venues)}")
    print(f"  Venues with menu : {venues_with_menu}")
    print(f"  Menu items found : {total_items}")
    print(f"  -> {VENUES_CSV}")
    print(f"  -> {ITEMS_CSV}")


if __name__ == "__main__":
    main()
