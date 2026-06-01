#!/usr/bin/env python3
"""
Build beach_data.json for the SURPRICE frontend.
Input:  raw_sources/beach_s2x_spiagge_venues.csv  (6.693 venue)
        raw_sources/beach_phase3_consolidated_items.csv (3.443 prezzi)
Output: data/beach_data.json
"""
import csv, json, os
from collections import defaultdict

BASE = os.path.join(os.path.dirname(__file__), "..")
VENUES_FILE = os.path.join(BASE, "raw_sources/beach_s2x_spiagge_venues.csv")
ITEMS_FILE  = os.path.join(BASE, "raw_sources/beach_phase3_consolidated_items.csv")
OUT         = os.path.join(BASE, "data/beach_data.json")

PRODUCT_LABELS = {
    "beach_set_2lettini_ombrellone": "Ombrellone + 2 lettini",
    "beach_set_1lettino_ombrellone": "Ombrellone + 1 lettino",
    "beach_umbrella_standard":       "Ombrellone",
    "beach_umbrella_first_row":      "Ombrellone prima fila",
    "beach_umbrella_premium":        "Ombrellone premium",
    "beach_sunbed":                  "Lettino",
    "beach_chair":                   "Sedia / sdraio",
    "beach_cabin_day":               "Cabina",
    "beach_cabin_season":            "Cabina stagionale",
    "beach_subscription_week":       "Abb. settimanale",
    "beach_subscription_month":      "Abb. mensile",
    "beach_subscription_season":     "Abb. stagionale",
    "beach_entry_fee":               "Ingresso",
    "beach_minimum_spend":           "Consumazione minima",
    "beach_parking":                 "Parcheggio",
    "beach_shower":                  "Doccia",
}

# Products surfaced in the UI category bar (order matters)
UI_CATEGORIES = [
    "beach_set_2lettini_ombrellone",
    "beach_sunbed",
    "beach_umbrella_standard",
    "beach_umbrella_first_row",
    "beach_cabin_day",
    "beach_entry_fee",
]

# ── Load items ────────────────────────────────────────────────────
# Per venue: { product: { 'peak':[items], 'mid':[items], 'other':[items] } }
items_by_venue_product = defaultdict(lambda: defaultdict(lambda: {"peak": [], "mid": [], "other": []}))

with open(ITEMS_FILE, encoding="utf-8") as f:
    for r in csv.DictReader(f):
        try:
            price = float(r["normalized_price_eur"])
        except (ValueError, KeyError):
            continue
        product = r.get("normalized_product", "")
        if not product:
            continue

        item = {
            "price": round(price, 2),
            "label": PRODUCT_LABELS.get(product, product),
            "price_type": r.get("price_type", ""),
            "staging": r.get("staging_items", ""),
            "source_url": r.get("source_url", ""),
        }

        slot = r.get("peak_or_mid", "")
        key = "peak" if slot == "peak_aug" else ("mid" if slot == "mid_jun" else "other")
        items_by_venue_product[r["source_venue_id"]][product][key].append(item)

# ── Load venues ───────────────────────────────────────────────────
venues_out = []
priced_count = 0
# Per-region: total, priced, lat/lng bounds for the bbox polygon
region_stats = defaultdict(lambda: {
    "total": 0, "priced": 0,
    "lat_min":  90, "lat_max": -90,
    "lng_min": 180, "lng_max": -180,
})

def min_price(items):
    return min((i["price"] for i in items), default=None)

with open(VENUES_FILE, encoding="utf-8") as f:
    for r in csv.DictReader(f):
        if r.get("extraction_status") != "ok":
            continue
        lat_s = r.get("latitude", "")
        lng_s = r.get("longitude", "")
        if not lat_s or not lng_s:
            continue
        try:
            lat = float(lat_s)
            lng = float(lng_s)
        except ValueError:
            continue

        vid = r["source_venue_id"]
        venue_products = items_by_venue_product.get(vid, {})

        # Per-product compact price index
        # prices = { product: { peak: 38.0, mid: 35.0, items_peak:[...], items_mid:[...] } }
        prices_by_product = {}
        for product, slots in venue_products.items():
            entry = {}
            mp = min_price(slots["peak"])
            mm = min_price(slots["mid"])
            mo = min_price(slots["other"])
            if mp is not None: entry["peak"] = mp
            if mm is not None: entry["mid"]  = mm
            if mo is not None: entry["other"] = mo
            entry["items_peak"] = sorted(slots["peak"], key=lambda x: x["price"])[:3]
            entry["items_mid"]  = sorted(slots["mid"],  key=lambda x: x["price"])[:3]
            if slots["other"]:
                entry["items_other"] = sorted(slots["other"], key=lambda x: x["price"])[:3]
            prices_by_product[product] = entry

        has_price = bool(prices_by_product)

        # Headline = min of beach_set_2lettini_ombrellone or first available
        headline = prices_by_product.get("beach_set_2lettini_ombrellone") or \
                   prices_by_product.get("beach_sunbed") or \
                   (next(iter(prices_by_product.values())) if prices_by_product else None)
        h_peak = headline.get("peak") if headline else None
        h_mid  = headline.get("mid")  if headline else None
        h_min  = h_peak or h_mid or (headline.get("other") if headline else None)

        amenities = []
        raw_amen = r.get("amenities", "") or ""
        if raw_amen:
            amenities = [a.strip() for a in raw_amen.split(";") if a.strip()][:10]

        venue = {
            "id":      vid,
            "name":    r["venue_name"],
            "lat":     lat,
            "lng":     lng,
            "city":    r.get("city", ""),
            "region":  r.get("region", ""),
            "address": r.get("address", ""),
            "url":     r.get("venue_url", ""),
            "image":   r.get("image_url", ""),
            "amenities": amenities,
            "has_price": has_price,
        }

        if has_price:
            priced_count += 1
            if h_min  is not None: venue["min_price"] = round(h_min, 2)
            if h_peak is not None: venue["min_peak"]  = round(h_peak, 2)
            if h_mid  is not None: venue["min_mid"]   = round(h_mid, 2)
            venue["prices"] = prices_by_product

        region = r.get("region", "") or "Altra"
        rs = region_stats[region]
        rs["total"]   += 1
        if has_price: rs["priced"] += 1
        rs["lat_min"]  = min(rs["lat_min"], lat)
        rs["lat_max"]  = max(rs["lat_max"], lat)
        rs["lng_min"]  = min(rs["lng_min"], lng)
        rs["lng_max"]  = max(rs["lng_max"], lng)
        venues_out.append(venue)

# Build regions list with bbox + coverage %
regions_out = []
for name, s in region_stats.items():
    if s["total"] == 0: continue
    # Headline price = median of region peak prices
    region_prices_peak = [v["min_peak"] for v in venues_out
                          if v.get("region") == name and v.get("min_peak") is not None]
    region_prices_peak.sort()
    median_peak = region_prices_peak[len(region_prices_peak)//2] if region_prices_peak else None
    regions_out.append({
        "name":      name,
        "total":     s["total"],
        "priced":    s["priced"],
        "pct":       round(100 * s["priced"] / s["total"]) if s["total"] else 0,
        "median_peak": median_peak,
        "bbox":      [s["lat_min"], s["lng_min"], s["lat_max"], s["lng_max"]],
    })
regions_out.sort(key=lambda r: -r["total"])

# ── Output ────────────────────────────────────────────────────────
out = {
    "metadata": {
        "season": "summer_2026",
        "generated_at": "2026-06-01",
        "total_venues": len(venues_out),
        "total_priced": priced_count,
        "regions": regions_out,
        "categories": [
            {"code": c, "label": PRODUCT_LABELS.get(c, c)}
            for c in UI_CATEGORIES
        ],
    },
    "venues": venues_out,
}

os.makedirs(os.path.dirname(OUT), exist_ok=True)
with open(OUT, "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, separators=(",", ":"))

size_mb = os.path.getsize(OUT) / 1024 / 1024
print(f"✓ {OUT}")
print(f"  {len(venues_out)} venues total, {priced_count} with prices")
print(f"  {size_mb:.1f} MB")
