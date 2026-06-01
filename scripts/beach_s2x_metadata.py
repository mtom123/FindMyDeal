#!/usr/bin/env python3
"""
S2X Phase C — Metadati SSR extraction via JSON-LD.
Concurrent fetch (4 thread) with rate limit. Cache on disk for resume.
"""
import csv
import json
import os
import re
import sys
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests
from datetime import datetime, timezone

HEADERS = {"User-Agent": "SurPrice-Research/1.0 (research@surprice.it)"}
INPUT = "raw_sources/beach_s2x_spiagge_url_list.csv"
OUTPUT = "raw_sources/beach_s2x_spiagge_venues.csv"
CACHE_DIR = "raw_sources/.spiagge_cache"
os.makedirs(CACHE_DIR, exist_ok=True)

OUT_FIELDS = [
    "source_platform", "source_venue_id", "spiagge_venue_id",
    "venue_name", "venue_url", "address", "city", "province",
    "region", "postal_code", "latitude", "longitude",
    "categories", "price_tier", "rating", "rating_count",
    "phone", "website", "opening_hours", "has_menu", "menu_url",
    "extraction_status", "retrieved_at", "google_maps_url",
    "instagram", "facebook", "booking_provider", "vertical",
    "amenities", "description_excerpt", "image_url",
]

JSON_LD_RE = re.compile(
    r'<script type="application/ld\+json">(\[.*?\])</script>',
    re.DOTALL,
)


def extract_venue(url, vid):
    cache_path = os.path.join(CACHE_DIR, f"{vid}.json")
    if os.path.exists(cache_path):
        with open(cache_path, encoding="utf-8") as f:
            return json.load(f)
    try:
        r = requests.get(url, headers=HEADERS, timeout=30)
        if r.status_code != 200:
            return {"status": r.status_code, "url": url, "vid": vid}
        html = r.text
        # Find all JSON-LD scripts
        scripts = JSON_LD_RE.findall(html)
        venue_data = None
        for s in scripts:
            try:
                arr = json.loads(s)
                for obj in arr:
                    if obj.get("@type") in ("SportsActivityLocation", "LodgingBusiness", "Place"):
                        venue_data = obj
                        break
                if venue_data:
                    break
            except json.JSONDecodeError:
                continue
        if not venue_data:
            return {"status": "no_json_ld", "url": url, "vid": vid}
        result = {"status": "ok", "url": url, "vid": vid, "ld": venue_data, "html_size": len(html)}
        with open(cache_path, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False)
        return result
    except Exception as e:
        return {"status": "error", "url": url, "vid": vid, "error": str(e)}


def to_csv_row(result, retrieved_at):
    if result["status"] != "ok":
        return {
            "source_platform": "spiagge",
            "source_venue_id": f"spiagge_{result['vid']}",
            "spiagge_venue_id": result["vid"],
            "venue_url": result["url"],
            "extraction_status": f"error_{result['status']}",
            "retrieved_at": retrieved_at,
            "booking_provider": "spiagge.it",
            "vertical": "beach",
            "has_menu": "False",
        }
    ld = result["ld"]
    addr = ld.get("address", {}) or {}
    geo = ld.get("geo", {}) or {}
    amenities = ld.get("amenityFeature", []) or []
    amenity_names = "; ".join(
        a["name"] for a in amenities if isinstance(a, dict) and a.get("value")
    )
    images = ld.get("image", []) or []
    img_url = images[0] if images else ""
    if isinstance(img_url, dict):
        img_url = img_url.get("url", "")
    desc = (ld.get("description") or "")[:500].replace("\n", " ").replace("\r", " ")
    lat = geo.get("latitude")
    lon = geo.get("longitude")
    # Google Maps URL
    gmap = ""
    if lat and lon:
        gmap = f"https://www.google.com/maps/search/?api=1&query={lat},{lon}"

    return {
        "source_platform": "spiagge",
        "source_venue_id": f"spiagge_{result['vid']}",
        "spiagge_venue_id": result["vid"],
        "venue_name": ld.get("name", ""),
        "venue_url": result["url"],
        "address": addr.get("streetAddress", ""),
        "city": addr.get("addressLocality", ""),
        "province": "",
        "region": addr.get("addressRegion", ""),
        "postal_code": addr.get("postalCode", ""),
        "latitude": lat or "",
        "longitude": lon or "",
        "categories": ld.get("@type", ""),
        "price_tier": "",
        "rating": (ld.get("aggregateRating") or {}).get("ratingValue", ""),
        "rating_count": (ld.get("aggregateRating") or {}).get("reviewCount", ""),
        "phone": ld.get("telephone", ""),
        "website": ld.get("url", ""),  # spiagge URL, not external
        "opening_hours": "",
        "has_menu": "False",
        "menu_url": "",
        "extraction_status": "ok",
        "retrieved_at": retrieved_at,
        "google_maps_url": gmap,
        "instagram": "",
        "facebook": "",
        "booking_provider": "spiagge.it",
        "vertical": "beach",
        "amenities": amenity_names,
        "description_excerpt": desc,
        "image_url": img_url if isinstance(img_url, str) else "",
    }


def main():
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else None
    workers = int(sys.argv[2]) if len(sys.argv) > 2 else 4
    delay = float(sys.argv[3]) if len(sys.argv) > 3 else 0.6

    with open(INPUT, encoding="utf-8", newline="") as f:
        urls = list(csv.DictReader(f))
    if limit:
        urls = urls[:limit]
    print(f"Processing {len(urls)} venues with {workers} workers, delay {delay}s")

    retrieved_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    lock = threading.Lock()
    processed = [0]
    results = []
    rate_sem = threading.Semaphore(1)

    def worker(row):
        with rate_sem:
            time.sleep(delay)
        res = extract_venue(row["spiagge_url"], row["spiagge_venue_id"])
        with lock:
            processed[0] += 1
            if processed[0] % 50 == 0:
                ok = sum(1 for r in results if r and r.get("status") == "ok")
                print(f"  {processed[0]}/{len(urls)} | ok: {ok}", flush=True)
        return res

    with ThreadPoolExecutor(max_workers=workers) as ex:
        futures = [ex.submit(worker, row) for row in urls]
        for fut in as_completed(futures):
            results.append(fut.result())

    ok_count = sum(1 for r in results if r.get("status") == "ok")
    err_count = len(results) - ok_count
    print(f"\nOK: {ok_count} | Errors: {err_count}")

    with open(OUTPUT, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=OUT_FIELDS)
        w.writeheader()
        for r in results:
            w.writerow(to_csv_row(r, retrieved_at))
    print(f"Written: {OUTPUT}")


if __name__ == "__main__":
    main()
