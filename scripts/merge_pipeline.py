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
    "address", "city", "extraction_status", "retrieved_at",
}
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
    if mycia_v.exists():
        vv = remap_mycia_venues(mycia_v)
        all_venues.extend(vv)
        print(f"  mycia_venues (legacy): {len(vv)} rows")
        sources_found.append("mycia")
    if mycia_i.exists():
        ii = remap_mycia_items(mycia_i)
        all_items.extend(ii)
        print(f"  mycia_items (legacy):  {len(ii)} rows")

    # New unified-schema files from raw_sources/
    for vfile in sorted(RAW_DIR.glob("*_venues.csv")):
        platform = vfile.stem.replace("_venues", "")
        rows = load_csv(vfile)
        warn_count = 0
        valid_rows = []
        for row in rows:
            warns = validate_row(row, VENUE_REQUIRED, str(vfile))
            if warns:
                warn_count += 1
            else:
                valid_rows.append(row)
        all_venues.extend(valid_rows)
        sources_found.append(platform)
        print(f"  {vfile.name}: {len(valid_rows)} valid / {len(rows)} total ({warn_count} warnings)")
        report_lines.append(f"{vfile.name}: {len(valid_rows)} valid, {warn_count} warnings")

    for ifile in sorted(RAW_DIR.glob("*_menu_items.csv")):
        rows = load_csv(ifile)
        warn_count = 0
        valid_rows = []
        for row in rows:
            warns = validate_row(row, ITEM_REQUIRED, str(ifile))
            if warns:
                warn_count += 1
            else:
                valid_rows.append(row)
        all_items.extend(valid_rows)
        print(f"  {ifile.name}: {len(valid_rows)} valid / {len(rows)} total ({warn_count} warnings)")
        report_lines.append(f"{ifile.name}: {len(valid_rows)} valid, {warn_count} warnings")

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
        venue_canonical_map[pid] = fp

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
    # Only items with geo + normalized_product + price
    price_rows = [
        i for i in dedup_items
        if i["normalized_product"]
        and i["latitude"]
        and i["price_eur"] > 0
    ]

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
