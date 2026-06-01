#!/usr/bin/env python3
"""
Phase 3.1 — Mass price extraction da spiagge.it.
Pattern scoperto in 3.0:
  URL: {venue_url}/?from=YYYY-MM-DD&to=YYYY-MM-DD
  Estrai dal HTML SSR: "price":N, "stagingItems":"...", "availableSpots":N,
                       "bookingAvailable":true|false
Per ogni venue: 2 fetch (peak Aug + mid Jun). Cache su disco per resume.
"""

import csv
import json
import os
import re
import sys
import time
import threading
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone

HEADERS = {"User-Agent": "SurPrice-Research/1.0 (research@surprice.it)"}

SESSION = requests.Session()
SESSION.headers.update(HEADERS)
SESSION.mount("https://", HTTPAdapter(
    pool_connections=50, pool_maxsize=50,
    max_retries=Retry(total=2, backoff_factor=0.5, status_forcelist=[502, 503, 504]),
))

INPUT = "raw_sources/beach_s2x_spiagge_venues.csv"
OUTPUT = "raw_sources/beach_phase3_spiagge_menu_items.csv"
CACHE_DIR = "raw_sources/.phase3_cache"
os.makedirs(CACHE_DIR, exist_ok=True)

# Regex extractors (operate on raw HTML)
RE_PRICE = re.compile(r'\\"price\\":(\d+)')
RE_STAGING = re.compile(r'\\"stagingItems\\":\\"([^\\]+)\\"')
RE_SPOTS = re.compile(r'\\"availableSpots\\":(\d+)')
RE_BOOKABLE = re.compile(r'\\"bookingAvailable\\":(true|false)')

# Date slots
SLOTS = [
    ("peak_aug", "2026-08-01", "2026-08-07"),
    ("mid_jun", "2026-06-15", "2026-06-21"),
]

# Map stagingItems to normalized_product
def map_product(staging):
    if not staging:
        return ""
    # "1U_2B" = 1 Umbrella + 2 Beds → set
    # "1B" = 1 Bed only → sunbed
    # "1U_2B_1C" = + Cabin → set (cabin extra)
    if "U" in staging and "B" in staging:
        return "beach_set_2lettini_ombrellone"
    if staging == "1B":
        return "beach_sunbed"
    if "U" in staging:
        return "beach_umbrella_standard"
    if "C" in staging:
        return "beach_cabin_day"
    return ""


OUT_FIELDS = [
    "source_platform", "source_venue_id", "venue_name", "venue_url",
    "menu_section", "item_name", "item_description",
    "raw_price", "normalized_price_eur", "currency",
    "price_type", "item_type", "normalized_product",
    "confidence", "allergens", "retrieved_at", "source_url",
    "season", "validity_start", "validity_end", "vertical",
    "peak_or_mid", "check_in_date", "check_out_date",
    "staging_items", "available_spots", "booking_available",
    "booking_provider",
]


def fetch_venue_slot(venue_row, slot_label, check_in, check_out):
    vid = venue_row["spiagge_venue_id"]
    url_base = venue_row["venue_url"].rstrip("/")
    url = f"{url_base}/?from={check_in}&to={check_out}"

    cache_key = f"{vid}_{slot_label}"
    cache_path = os.path.join(CACHE_DIR, f"{cache_key}.json")
    if os.path.exists(cache_path):
        with open(cache_path, encoding="utf-8") as f:
            return json.load(f)

    try:
        r = SESSION.get(url, timeout=30)
        if r.status_code != 200:
            res = {"status": f"http_{r.status_code}", "vid": vid, "slot": slot_label}
        else:
            h = r.text
            m_price = RE_PRICE.search(h)
            m_stage = RE_STAGING.search(h)
            m_spots = RE_SPOTS.search(h)
            m_book = RE_BOOKABLE.search(h)
            res = {
                "status": "ok",
                "vid": vid,
                "slot": slot_label,
                "url": url,
                "price": int(m_price.group(1)) if m_price else None,
                "staging": m_stage.group(1) if m_stage else "",
                "spots": int(m_spots.group(1)) if m_spots else None,
                "bookable": m_book.group(1) == "true" if m_book else False,
                "check_in": check_in,
                "check_out": check_out,
            }
    except Exception as e:
        res = {"status": "error", "vid": vid, "slot": slot_label, "error": str(e)[:200]}

    with open(cache_path, "w", encoding="utf-8") as f:
        json.dump(res, f, ensure_ascii=False)
    return res


def result_to_row(r, venue_row, retrieved_at):
    if r.get("status") != "ok" or not r.get("bookable") or not r.get("price") or r["price"] == 0:
        return None
    staging = r.get("staging", "")
    product = map_product(staging)
    item_name_label = {
        "beach_set_2lettini_ombrellone": "Ombrellone + 2 lettini",
        "beach_sunbed": "Lettino singolo",
        "beach_umbrella_standard": "Ombrellone",
        "beach_cabin_day": "Cabina giornaliera",
    }.get(product, "Pacchetto base")
    period_label = "Settimana 1-7 agosto 2026 (peak)" if r["slot"] == "peak_aug" else "Settimana 15-21 giugno 2026 (mid)"

    return {
        "source_platform": "spiagge",
        "source_venue_id": f"spiagge_{r['vid']}",
        "venue_name": venue_row["venue_name"],
        "venue_url": venue_row["venue_url"],
        "menu_section": "PACCHETTO BASE",
        "item_name": f"{item_name_label} – {period_label}",
        "item_description": f"Configurazione: {staging} | available_spots: {r.get('spots')} | bookable via spiagge.it",
        "raw_price": f"€{r['price']},00",
        "normalized_price_eur": float(r["price"]),
        "currency": "EUR",
        "price_type": "per_week",
        "item_type": "beach_service",
        "normalized_product": product,
        "confidence": "high",
        "allergens": "",
        "retrieved_at": retrieved_at,
        "source_url": r["url"],
        "season": "summer_2026",
        "validity_start": "2026-05-01",
        "validity_end": "2026-09-30",
        "vertical": "beach",
        "peak_or_mid": r["slot"],
        "check_in_date": r["check_in"],
        "check_out_date": r["check_out"],
        "staging_items": staging,
        "available_spots": r.get("spots", ""),
        "booking_available": "true",
        "booking_provider": "spiagge.it",
    }


def main():
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else None
    workers = int(sys.argv[2]) if len(sys.argv) > 2 else 16
    delay = float(sys.argv[3]) if len(sys.argv) > 3 else 0.3

    with open(INPUT, encoding="utf-8", newline="") as f:
        venues = [v for v in csv.DictReader(f) if v["extraction_status"] == "ok"]
    if limit:
        venues = venues[:limit]
    print(f"Processing {len(venues)} venues × 2 slots = {len(venues)*2} fetches")
    print(f"Workers: {workers}, delay: {delay}s")

    retrieved_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    lock = threading.Lock()
    processed = [0]
    bookable_count = [0]
    results = []

    def worker(venue, slot):
        time.sleep(delay)
        label, ci, co = slot
        res = fetch_venue_slot(venue, label, ci, co)
        with lock:
            processed[0] += 1
            if res.get("bookable") and res.get("price"):
                bookable_count[0] += 1
            if processed[0] % 500 == 0:
                print(f"  {processed[0]}/{len(venues)*2} | bookable_w_price: {bookable_count[0]}", flush=True)
        return (venue, res)

    # Build tasks: each venue × 2 slots
    tasks = []
    for v in venues:
        for slot in SLOTS:
            tasks.append((v, slot))

    with ThreadPoolExecutor(max_workers=workers) as ex:
        futures = [ex.submit(worker, v, slot) for v, slot in tasks]
        for fut in as_completed(futures):
            results.append(fut.result())

    print(f"\nProcessed: {processed[0]}, bookable with price: {bookable_count[0]}")

    # Build CSV rows
    rows = []
    for venue, res in results:
        row = result_to_row(res, venue, retrieved_at)
        if row:
            rows.append(row)

    # Dedup
    seen = set()
    unique = []
    for r in rows:
        k = (r["source_venue_id"], r["normalized_product"], r["raw_price"],
             r["price_type"], r["peak_or_mid"])
        if k not in seen:
            seen.add(k)
            unique.append(r)

    with open(OUTPUT, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=OUT_FIELDS)
        w.writeheader()
        w.writerows(unique)

    # Stats
    venues_with_price = len(set(r["source_venue_id"] for r in unique))
    print(f"\nFinal stats:")
    print(f"  Items: {len(unique)}")
    print(f"  Unique venues with prices: {venues_with_price}")
    print(f"  Written: {OUTPUT}")


if __name__ == "__main__":
    main()
