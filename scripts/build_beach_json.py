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

# ── Load items ────────────────────────────────────────────────────
items_by_venue = defaultdict(lambda: {"peak": [], "mid": [], "other": []})

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
            "product": product,
            "label": PRODUCT_LABELS.get(product, product),
            "price_type": r.get("price_type", ""),
            "staging": r.get("staging_items", ""),
            "spots": r.get("available_spots", ""),
            "source_url": r.get("source_url", ""),
        }

        slot = r.get("peak_or_mid", "")
        if slot == "peak_aug":
            items_by_venue[r["source_venue_id"]]["peak"].append(item)
        elif slot == "mid_jun":
            items_by_venue[r["source_venue_id"]]["mid"].append(item)
        else:
            items_by_venue[r["source_venue_id"]]["other"].append(item)

# ── Load venues ───────────────────────────────────────────────────
venues_out = []
regions_count = defaultdict(int)
priced_count = 0

def headline_price(items):
    """Min price of standard 2-lettini set, else min of all."""
    std = [i for i in items if i["product"] == "beach_set_2lettini_ombrellone"]
    pool = std if std else items
    prices = [i["price"] for i in pool]
    return min(prices) if prices else None

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

        vid    = r["source_venue_id"]
        prices = items_by_venue.get(vid, {"peak": [], "mid": [], "other": []})
        has_price = bool(prices["peak"] or prices["mid"] or prices["other"])

        min_peak  = headline_price(prices["peak"])
        min_mid   = headline_price(prices["mid"])
        min_price = min_peak or min_mid or headline_price(prices["other"])

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
            if min_price is not None:
                venue["min_price"] = round(min_price, 2)
            if min_peak  is not None:
                venue["min_peak"]  = round(min_peak, 2)
            if min_mid   is not None:
                venue["min_mid"]   = round(min_mid, 2)
            # Top items for detail card (max 4 per slot)
            venue["items_peak"]  = sorted(prices["peak"],  key=lambda x: x["price"])[:4]
            venue["items_mid"]   = sorted(prices["mid"],   key=lambda x: x["price"])[:4]
            if prices["other"]:
                venue["items_other"] = sorted(prices["other"], key=lambda x: x["price"])[:4]

        regions_count[r.get("region", "")] += 1
        venues_out.append(venue)

# ── Output ────────────────────────────────────────────────────────
out = {
    "metadata": {
        "season": "summer_2026",
        "generated_at": "2026-06-01",
        "total_venues": len(venues_out),
        "total_priced": priced_count,
        "regions": dict(sorted(regions_count.items(), key=lambda x: -x[1])),
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
