"""
tripadvisor_scraper.py — TripAdvisor Milano Bar/Pub/Brewery/Winery Scraper
===========================================================================
Usa Playwright (Chromium reale) per bypassare Akamai Bot Manager di TripAdvisor.

Strategia:
  1. Apre pagine di ricerca TripAdvisor per bar/pub/birrerie/wine bar a Milano
  2. Raccoglie URL di tutte le venue (paginazione automatica)
  3. Per ogni venue: estrae nome, indirizzo, coordinate, rating, sito web
  4. Cerca link menu esterno o sito proprio → visita e cerca prezzi
  5. Output → raw_sources/tripadvisor_venues.csv + tripadvisor_menu_items.csv

Run:
  cd FindMyDeal/scripts
  python3 tripadvisor_scraper.py

Resume: ri-esegui — venue già elaborate sono saltate (checkpoint su disco).
"""

from __future__ import annotations

import csv
import hashlib
import json
import random
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright, Page, Browser, TimeoutError as PWTimeout

# ─────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────

OUTPUT_DIR = Path("../raw_sources")
OUTPUT_DIR.mkdir(exist_ok=True)
RAW_DIR    = Path("../raw_data_tripadvisor")
RAW_DIR.mkdir(exist_ok=True)

VENUES_CSV = OUTPUT_DIR / "tripadvisor_venues.csv"
ITEMS_CSV  = OUTPUT_DIR / "tripadvisor_menu_items.csv"
CHECKPOINT = Path("../tripadvisor_checkpoint.txt")

SOURCE_PLATFORM = "tripadvisor"
CITY            = "Milano"

# Pagine di ricerca TripAdvisor Milano — già filtrate per categoria
TA_SEARCH_URLS = [
    "https://www.tripadvisor.it/Nightlife-g187849-Milan_Lombardy.html",
    "https://www.tripadvisor.it/Restaurants-g187849-a_cuisine.25-Milan_Lombardy.html",   # Bar/Pub
    "https://www.tripadvisor.it/Restaurants-g187849-a_cuisine.10665-Milan_Lombardy.html", # Wine bar / Enoteca
    "https://www.tripadvisor.it/Restaurants-g187849-a_cuisine.10664-Milan_Lombardy.html", # Brewery / Birrificio
]

MAX_PAGES_PER_SEARCH = 10   # 30 venue/pag → max ~300 per categoria
MAX_VENUES_TOTAL     = 500
PAGE_DELAY           = (2.0, 4.0)   # (min, max) secondi random tra pagine
VENUE_DELAY          = (2.5, 5.0)   # secondi random tra venue

TARGET_CATEGORIES = {
    "bar", "pub", "birreria", "birrificio", "enoteca", "wine bar",
    "cocktail bar", "lounge bar", "taverna", "american bar",
    "nightlife", "night club", "brewery", "locali notturni",
}

# ─────────────────────────────────────────────
# PRODUCT NORMALIZATION
# ─────────────────────────────────────────────

PRODUCT_RULES = [
    (r"\bspritz\b",                                           "spritz"),
    (r"\baperspritz\b",                                       "spritz"),
    (r"\bnegroni\b",                                          "negroni"),
    (r"\bamericano\b",                                        "americano"),
    (r"\bgin\s*[&e]\s*tonic\b",                               "gin_tonic"),
    (r"\bgin\s*tonic\b",                                      "gin_tonic"),
    (r"\bmoscow\s*mule\b",                                    "moscow_mule"),
    (r"\bmargarita\b",                                        "margarita"),
    (r"\bmojito\b",                                           "mojito"),
    (r"\bmanhattan\b",                                        "manhattan"),
    (r"\bdaiquiri\b",                                         "daiquiri"),
    (r"\bespresso\b|\bcaff[eè]\b",                            "espresso"),
    (r"\bcappuccino\b",                                       "cappuccino"),
    (r"\bcoca.?cola\b|\bpepsi\b|\bfanta\b|\bbibita\b",        "soft_drink"),
    (r"\bacqua\b|\bwater\b",                                  "water"),
    (r"\bcalice\b|\bvino.{0,10}(calice|bicchiere)\b",         "wine_glass"),
    (r"\bprosecco.{0,10}(flute|calice|bicchiere)\b",          "prosecco_glass"),
    (r"\bmoretti\b",                                          "beer_moretti"),
    (r"\bheineken\b",                                         "beer_heineken"),
    (r"\bperoni\b|\bnastro\s*azzurro\b",                      "beer_peroni"),
    (r"\bbirra?\s+alla\s+spina.{0,15}(piccol|0[,.]?[23]|33\s*cl)", "beer_draft_small"),
    (r"\bbirra?\s+alla\s+spina.{0,15}(medi|0[,.]?[45]|40\s*cl|50\s*cl)", "beer_draft_medium"),
    (r"\bbirra?\s+piccol",                                    "beer_draft_small"),
    (r"\bbirra?\s+medi",                                      "beer_draft_medium"),
    (r"\bbirra?\s+(in\s+)?bottigli",                          "beer_bottle"),
    (r"\bbottled\s+beer\b",                                   "beer_bottle"),
]

DRINK_NORMALIZED = {
    "spritz","negroni","americano","gin_tonic","moscow_mule","margarita","mojito",
    "manhattan","daiquiri","beer_draft_small","beer_draft_medium","beer_bottle",
    "beer_moretti","beer_heineken","beer_peroni","wine_glass","prosecco_glass",
    "espresso","cappuccino","soft_drink","water","custom_cocktail",
}

DRINK_SECTION_KW = {
    "spritz","cocktail","drink","aperitivi","aperitivo","birra","birre","vini",
    "vino","calici","analcolici","bevande","caffetteria","liquori","gin","rum",
    "vodka","whisky","amari","digestivi","long drink","mocktail","prosecco",
    "bollicine","bevanda",
}

PRICE_RE      = re.compile(r"(?:€\s*)?(\d{1,3}(?:[.,]\d{1,2})?)\s*€?")
FOOD_SEC_RE   = re.compile(
    r"\b(pizza|burger|panino|piatt|antipast|prim[io]|second[io]|dolci|dessert|"
    r"pasta|risotto|grill|insalat|carne|pesce|vegano|fritto)\b", re.I
)
VENUE_URL_RE  = re.compile(
    r'href="((?:/Attraction_Review|/Restaurant_Review)-g187849-d\d+-Reviews-[^"#?]+\.html)"',
    re.I,
)


def normalize_product(name: str) -> tuple[str, str]:
    low = name.lower()
    for pat, prod in PRODUCT_RULES:
        if re.search(pat, low):
            return prod, "high"
    return "", "low"


def parse_price(raw: str) -> float | None:
    if not raw:
        return None
    m = PRICE_RE.search(raw.strip())
    if m:
        try:
            p = float(m.group(1).replace(",", "."))
            return p if 0.5 < p < 150 else None
        except ValueError:
            return None
    return None


def is_drink_section(s: str) -> bool:
    low = s.lower()
    return any(kw in low for kw in DRINK_SECTION_KW)


# ─────────────────────────────────────────────
# DISK CACHE (HTML grezzo)
# ─────────────────────────────────────────────

def cache_path(url: str) -> Path:
    return RAW_DIR / (hashlib.md5(url.encode()).hexdigest() + ".html")


def cache_get(url: str) -> str | None:
    cp = cache_path(url)
    return cp.read_text(encoding="utf-8", errors="replace") if cp.exists() else None


def cache_put(url: str, html: str):
    cache_path(url).write_text(html, encoding="utf-8")


# ─────────────────────────────────────────────
# PLAYWRIGHT FETCH
# ─────────────────────────────────────────────

def pw_fetch(page: Page, url: str, use_cache: bool = True,
             wait_for: str = "domcontentloaded") -> str | None:
    """Naviga a URL con Playwright, usa cache su disco se disponibile."""
    if use_cache:
        cached = cache_get(url)
        if cached:
            return cached
    try:
        page.goto(url, wait_until=wait_for, timeout=30000)
        # Piccola pausa per JS post-load
        page.wait_for_timeout(random.randint(1200, 2200))
        html = page.content()
        cache_put(url, html)
        time.sleep(random.uniform(*PAGE_DELAY))
        return html
    except PWTimeout:
        print(f"  [TIMEOUT] {url[:70]}")
        return None
    except Exception as e:
        print(f"  [ERR] {url[:70]}: {e}")
        return None


def pw_fetch_external(page: Page, url: str) -> str | None:
    """Fetch sito esterno (sito venue, menu esterno) — delay più corto."""
    cached = cache_get(url)
    if cached:
        return cached
    try:
        page.goto(url, wait_until="domcontentloaded", timeout=20000)
        page.wait_for_timeout(random.randint(800, 1500))
        html = page.content()
        cache_put(url, html)
        time.sleep(random.uniform(1.0, 2.5))
        return html
    except Exception:
        return None


# ─────────────────────────────────────────────
# FASE 1 — RACCOLTA URL VENUE
# ─────────────────────────────────────────────

def paginate_url(base_url: str, offset: int) -> str:
    """Inserisce -oa{offset}- nell'URL TripAdvisor per la paginazione."""
    cleaned = re.sub(r"-oa\d+-", "-", base_url)
    result  = re.sub(r"(-Milan_Lombardy\.html)", f"-oa{offset}\\1", cleaned)
    return result


def collect_venue_urls(page: Page, search_urls: list[str]) -> list[str]:
    all_urls: dict[str, bool] = {}

    for base_url in search_urls:
        print(f"\n  Ricerca: {base_url[:80]}")
        for pg in range(MAX_PAGES_PER_SEARCH):
            offset = pg * 30
            url    = paginate_url(base_url, offset) if offset > 0 else base_url

            html = pw_fetch(page, url)
            if not html:
                break

            found = VENUE_URL_RE.findall(html)
            new_count = 0
            for rel in found:
                abs_url = "https://www.tripadvisor.it" + rel.split("#")[0]
                if abs_url not in all_urls:
                    all_urls[abs_url] = True
                    new_count += 1

            print(f"    Pag {pg+1} (offset={offset}): {len(found)} link, "
                  f"{new_count} nuovi — totale {len(all_urls)}")

            if new_count == 0:
                break
            if len(all_urls) >= MAX_VENUES_TOTAL:
                print(f"    Limite {MAX_VENUES_TOTAL} raggiunto")
                break

        if len(all_urls) >= MAX_VENUES_TOTAL:
            break

    return list(all_urls.keys())


# ─────────────────────────────────────────────
# FASE 2 — PARSING VENUE PAGE
# ─────────────────────────────────────────────

def extract_venue_id(url: str) -> str:
    m = re.search(r"-d(\d+)-", url)
    return m.group(1) if m else hashlib.md5(url.encode()).hexdigest()[:10]


def parse_venue_page(url: str, html: str) -> dict:
    soup = BeautifulSoup(html, "lxml")
    now  = datetime.now(timezone.utc).isoformat()
    vid  = extract_venue_id(url)

    v = {
        "source_platform":   SOURCE_PLATFORM,
        "source_venue_id":   vid,
        "venue_name":        "",
        "venue_url":         url,
        "address":           "",
        "city":              CITY,
        "latitude":          "",
        "longitude":         "",
        "categories":        "",
        "price_tier":        "",
        "rating":            "",
        "rating_count":      "",
        "phone":             "",
        "website":           "",
        "opening_hours":     "",
        "has_menu":          "False",
        "menu_url":          "",
        "extraction_status": "pending",
        "retrieved_at":      now,
    }

    # JSON-LD
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            data    = json.loads(script.string or "")
            schemas = data if isinstance(data, list) else [data]
            for s in schemas:
                t = s.get("@type", "")
                if t not in ("Restaurant","FoodEstablishment","BarOrPub",
                             "CafeOrCoffeeShop","NightClub","TouristAttraction",
                             "LocalBusiness"):
                    continue
                v["venue_name"] = v["venue_name"] or s.get("name", "").strip()
                if not v["address"]:
                    addr = s.get("address", {})
                    if isinstance(addr, dict):
                        parts = [addr.get("streetAddress","").strip(),
                                 addr.get("postalCode","").strip(),
                                 addr.get("addressLocality","").strip()]
                        v["address"] = ", ".join(p for p in parts if p and p != CITY)
                if not v["latitude"]:
                    geo = s.get("geo", {})
                    if isinstance(geo, dict):
                        v["latitude"]  = str(geo.get("latitude",  ""))
                        v["longitude"] = str(geo.get("longitude", ""))
                if not v["categories"]:
                    cats = s.get("servesCuisine", [])
                    if isinstance(cats, str): cats = [cats]
                    v["categories"] = "; ".join(c.strip() for c in cats if c.strip())
                if not v["rating"]:
                    ar = s.get("aggregateRating", {})
                    if isinstance(ar, dict):
                        v["rating"]       = str(ar.get("ratingValue",""))
                        v["rating_count"] = str(ar.get("reviewCount",""))
                if not v["price_tier"]:
                    v["price_tier"] = str(s.get("priceRange","")).strip()
                if not v["website"]:
                    v["website"] = s.get("url","").strip()
                if not v["phone"]:
                    v["phone"] = s.get("telephone","").strip()
        except (json.JSONDecodeError, AttributeError):
            pass

    # Fallback nome
    if not v["venue_name"]:
        og = soup.find("meta", property="og:title")
        if og:
            v["venue_name"] = og.get("content","").split("-")[0].strip()
    if not v["venue_name"]:
        h1 = soup.find("h1")
        if h1:
            v["venue_name"] = h1.get_text(strip=True)

    # Cerca link menu / sito web nella pagina
    menu_url = _find_menu_link(soup)
    if menu_url:
        v["menu_url"] = menu_url
        v["has_menu"] = "True"
    if not v["website"]:
        v["website"] = _find_website_link(soup)

    return v


_MENU_RE = re.compile(r"\b(men[uù]|carta\s*(dei?)?\s*(drink|vini?|cocktail|prezzi))\b", re.I)
_SITE_RE = re.compile(r"\b(sito\s*web|visita\s*sito|website|vai\s*al\s*sito)\b", re.I)


def _find_menu_link(soup: BeautifulSoup) -> str:
    for a in soup.find_all("a", href=True):
        href = a["href"]
        text = a.get_text(strip=True)
        if _MENU_RE.search(text) or _MENU_RE.search(href):
            if href.startswith("http") and "tripadvisor" not in href.lower():
                return href
            elif href.startswith("/"):
                return "https://www.tripadvisor.it" + href
    for el in soup.find_all(attrs={"data-menu-url": True}):
        return el["data-menu-url"]
    return ""


def _find_website_link(soup: BeautifulSoup) -> str:
    for a in soup.find_all("a", href=True):
        href = a["href"]
        text = a.get_text(strip=True)
        if _SITE_RE.search(text) and href.startswith("http"):
            if "tripadvisor" not in href.lower():
                return href
    return ""


def is_target_category(cats: str) -> bool:
    if not cats:
        return True  # senza categoria: teniamo e marchiamo "uncertain"
    low = cats.lower()
    return any(tc in low for tc in TARGET_CATEGORIES)


# ─────────────────────────────────────────────
# FASE 3 — ESTRAZIONE PREZZI DA HTML
# ─────────────────────────────────────────────

def extract_items(html: str, source_url: str, venue_id: str,
                  venue_name: str, price_type: str = "menu") -> list[dict]:
    soup  = BeautifulSoup(html, "lxml")
    now   = datetime.now(timezone.utc).isoformat()
    items = []
    seen: set = set()

    def add(section, name, desc, raw_price):
        prod, conf = normalize_product(name)
        is_drink   = is_drink_section(section) or is_drink_section(name) or prod in DRINK_NORMALIZED
        if not is_drink:
            return
        price = parse_price(raw_price)
        key   = (venue_id, section, name, raw_price)
        if not name or key in seen:
            return
        seen.add(key)
        items.append({
            "source_platform":      SOURCE_PLATFORM,
            "source_venue_id":      venue_id,
            "venue_name":           venue_name,
            "venue_url":            source_url,
            "menu_section":         section,
            "item_name":            name,
            "item_description":     desc,
            "raw_price":            raw_price,
            "normalized_price_eur": price if price is not None else "",
            "currency":             "EUR",
            "price_type":           price_type,
            "item_type":            "drink",
            "normalized_product":   prod,
            "confidence":           conf,
            "allergens":            "",
            "retrieved_at":         now,
            "source_url":           source_url,
        })

    # JSON-LD strutturato (menu embedded)
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            data    = json.loads(script.string or "")
            schemas = data if isinstance(data, list) else [data]
            for s in schemas:
                t     = s.get("@type", "")
                menus = []
                if t in ("Restaurant","FoodEstablishment","BarOrPub","CafeOrCoffeeShop"):
                    raw_m = s.get("menu", [])
                    if isinstance(raw_m, list):
                        menus = raw_m
                elif t == "Menu":
                    menus = [s]
                for menu_obj in menus:
                    if not isinstance(menu_obj, dict):
                        continue
                    for section in menu_obj.get("hasMenuSection", []):
                        sec = section.get("name", "Menu").strip()
                        if FOOD_SEC_RE.search(sec) and not is_drink_section(sec):
                            continue
                        for entry in section.get("hasMenuItem", []):
                            name  = entry.get("name","").strip()
                            desc  = entry.get("description","").strip()
                            offer = entry.get("offers", {})
                            pval  = offer.get("price","") if isinstance(offer, dict) else ""
                            try:
                                raw = "" if float(str(pval)) == 0 else str(pval)
                            except (ValueError, TypeError):
                                raw = str(pval)
                            add(sec, name, desc, raw)
        except (json.JSONDecodeError, AttributeError):
            pass

    # Fallback: scan €-pattern nell'HTML
    if not items:
        for el in soup.find_all(string=re.compile(r"€\s*\d|\d[,\.]\d{2}\s*€")):
            parent = el.parent
            if not parent:
                continue
            row = parent.find_parent(["tr", "li", "div", "article"])
            if not row:
                continue
            texts = [t.strip() for t in row.stripped_strings if t.strip()]
            if len(texts) >= 2:
                name = texts[0]
                raw  = str(el).strip()
                ctx  = " ".join(texts)
                if FOOD_SEC_RE.search(ctx) and not re.search(
                    r"\b(drink|cocktail|birr|vino|spritz|aperitiv)\b", ctx, re.I
                ):
                    continue
                add("Menu", name, "", raw)

    return items


def find_menu_subpage(base_url: str, html: str) -> str:
    """Cerca link a pagina /menu su sito proprio del locale."""
    soup     = BeautifulSoup(html, "lxml")
    menu_re  = re.compile(r"\b(men[uù]|carta|prezzi|drinks?|cocktail|birre)\b", re.I)
    for a in soup.find_all("a", href=True):
        text = a.get_text(strip=True)
        href = a["href"]
        if menu_re.search(text) or menu_re.search(href):
            if href.startswith("http"):
                return href
            elif href.startswith("/"):
                parsed = urlparse(base_url)
                return f"{parsed.scheme}://{parsed.netloc}{href}"
    return base_url


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


def open_csv(path: Path, fields: list[str]):
    is_new = not path.exists() or path.stat().st_size == 0
    f = open(path, "a", newline="", encoding="utf-8")
    w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
    if is_new:
        w.writeheader()
    return f, w


def load_checkpoint() -> set[str]:
    return set(CHECKPOINT.read_text().splitlines()) if CHECKPOINT.exists() else set()


def save_checkpoint(vid: str, done: set[str]):
    done.add(vid)
    CHECKPOINT.write_text("\n".join(sorted(done)))


# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────

def main():
    print("=" * 65)
    print("TripAdvisor Milano — Bar / Pub / Birreria / Enoteca Scraper")
    print("              (Playwright / Chromium)")
    print("=" * 65)

    done = load_checkpoint()
    print(f"Checkpoint: {len(done)} venue già elaborate\n")

    with sync_playwright() as pw:
        browser: Browser = pw.chromium.launch(
            headless=True,
            args=["--disable-blink-features=AutomationControlled"],
        )
        context = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            locale="it-IT",
            viewport={"width": 1280, "height": 900},
            java_script_enabled=True,
        )
        # Nascondi webdriver fingerprint
        context.add_init_script(
            "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
        )
        page = context.new_page()

        # ── FASE 1: raccolta URL venue ────────────────
        print("FASE 1 — Raccolta URL venue dalle pagine di ricerca")
        venue_urls = collect_venue_urls(page, TA_SEARCH_URLS)
        print(f"\nTotale URL venue raccolti: {len(venue_urls)}")

        if not venue_urls:
            print("Nessun URL trovato. Controlla la connessione o prova più tardi.")
            browser.close()
            return

        # ── FASE 2: elaborazione venue ────────────────
        print("\nFASE 2 — Elaborazione venue + ricerca prezzi")
        vf, venue_writer = open_csv(VENUES_CSV, VENUE_FIELDS)
        mf, items_writer = open_csv(ITEMS_CSV,  ITEM_FIELDS)

        total_venues  = 0
        total_items   = 0
        skipped       = 0

        for url in venue_urls:
            vid = extract_venue_id(url)
            if vid in done:
                skipped += 1
                continue

            sys.stdout.write(f"  [{total_venues + skipped + 1}/{len(venue_urls)}] ")
            sys.stdout.flush()

            html = pw_fetch(page, url)
            if not html:
                save_checkpoint(vid, done)
                continue

            venue = parse_venue_page(url, html)
            name  = venue["venue_name"] or f"venue_{vid}"
            sys.stdout.buffer.write(f"{name}\n".encode("utf-8"))
            sys.stdout.flush()

            # Filtro categoria
            if not is_target_category(venue["categories"]):
                venue["extraction_status"] = "filtered_out"
                venue_writer.writerow(venue)
                vf.flush()
                save_checkpoint(vid, done)
                total_venues += 1
                continue

            # ── Cerca prezzi (cascata) ────────────────
            items: list[dict] = []

            # 1) Link menu trovato su TripAdvisor
            if venue["menu_url"] and venue["menu_url"] != url:
                mhtml = pw_fetch_external(page, venue["menu_url"])
                if mhtml:
                    items = extract_items(mhtml, venue["menu_url"], vid, name)

            # 2) Sito web proprio del locale
            if not items and venue["website"]:
                shtml = pw_fetch_external(page, venue["website"])
                if shtml:
                    sub_url = find_menu_subpage(venue["website"], shtml)
                    if sub_url != venue["website"]:
                        sub_html = pw_fetch_external(page, sub_url)
                        if sub_html:
                            items = extract_items(sub_html, sub_url, vid, name)
                    if not items:
                        items = extract_items(shtml, venue["website"], vid, name)

            # 3) Fallback: cerca prezzi direttamente nella pagina TripAdvisor
            if not items:
                items = extract_items(html, url, vid, name)

            # Aggiorna stato
            if items:
                venue["extraction_status"] = "ok_with_menu"
                venue["has_menu"]          = "True"
                items_writer.writerows(items)
                mf.flush()
                total_items += len(items)
                print(f"      → {len(items)} prezzi trovati")
            else:
                venue["extraction_status"] = "ok_no_menu"

            venue_writer.writerow(venue)
            vf.flush()
            save_checkpoint(vid, done)
            total_venues += 1

            # Delay anti-ban tra venue
            time.sleep(random.uniform(*VENUE_DELAY))

        vf.close()
        mf.close()
        browser.close()

    print("\n" + "=" * 65)
    print("Fine.")
    print(f"  Venue elaborate   : {total_venues}")
    print(f"  Venue saltate     : {skipped}")
    print(f"  Prezzi trovati    : {total_items}")
    print(f"\n  Output:")
    print(f"    {VENUES_CSV}")
    print(f"    {ITEMS_CSV}")
    print("=" * 65)


if __name__ == "__main__":
    main()
