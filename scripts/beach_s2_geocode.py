#!/usr/bin/env python3
"""
Beach S2 — Reverse geocoding via Nominatim.
Populates city/province/region/postal_code for venues with empty fields.
Cache to disk to allow resume on crash.
"""

import csv
import json
import os
import time
import sys
import requests
from pathlib import Path

NOMINATIM = "https://nominatim.openstreetmap.org/reverse"
HEADERS = {
    "User-Agent": "SurPrice-Research/1.0 (research@surprice.it)",
    "Accept-Language": "it",
}

INPUT_CSV = "raw_sources/beach_s1_venues.csv"
OUTPUT_CSV = "raw_sources/beach_s2_venues_enriched.csv"
CACHE_FILE = "raw_sources/.geocode_cache.json"

RATE_SECONDS = 1.05  # Nominatim TOS: 1 req/sec max

ITALIAN_REGIONS = {
    "Liguria", "Toscana", "Lazio", "Campania", "Calabria", "Sicilia",
    "Sicilia", "Puglia", "Marche", "Abruzzo", "Molise", "Emilia-Romagna",
    "Veneto", "Friuli Venezia Giulia", "Friuli-Venezia Giulia",
    "Sardegna", "Basilicata", "Lombardia", "Piemonte", "Trentino-Alto Adige",
    "Valle d'Aosta", "Umbria",
}


def load_cache():
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_cache(cache):
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False)


def reverse_geocode(lat, lon, cache, stats):
    key = f"{round(float(lat), 5)},{round(float(lon), 5)}"
    if key in cache:
        stats["cache_hits"] += 1
        return cache[key]
    stats["api_calls"] += 1
    time.sleep(RATE_SECONDS)  # Rate-limit BEFORE API call
    try:
        r = requests.get(
            NOMINATIM,
            params={
                "lat": lat,
                "lon": lon,
                "format": "json",
                "addressdetails": 1,
                "zoom": 14,
            },
            headers=HEADERS,
            timeout=30,
        )
        if r.status_code == 200:
            addr = r.json().get("address", {})
            result = {
                "city": (
                    addr.get("city")
                    or addr.get("town")
                    or addr.get("village")
                    or addr.get("hamlet")
                    or addr.get("municipality")
                    or ""
                ),
                "province": addr.get("county") or addr.get("province") or "",
                "region": addr.get("state") or "",
                "postal_code": addr.get("postcode") or "",
                "country": addr.get("country_code", "").upper(),
            }
            cache[key] = result
            return result
        elif r.status_code == 429:
            print(f"  429 rate limited — sleeping 120s", flush=True)
            time.sleep(120)
            return None
    except Exception as e:
        print(f"  Error: {e}", flush=True)
    cache[key] = {"city": "", "province": "", "region": "", "postal_code": "", "country": ""}
    return cache[key]


def main():
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else None
    with open(INPUT_CSV, encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    print(f"Loaded {len(rows)} venues", flush=True)

    if limit:
        # Priority sort: venues with website first, then by lat (coastal sweep)
        rows_with_web = [r for r in rows if r.get("website")]
        rows_no_web = [r for r in rows if not r.get("website")]
        # Take all websites + sample of rest
        sample_size = max(0, limit - len(rows_with_web))
        # Sample every Nth from the rest to spread geographically
        step = max(1, len(rows_no_web) // sample_size) if sample_size else 1
        sampled = rows_no_web[::step][:sample_size]
        target_rows = rows_with_web + sampled
        target_ids = set(r["source_venue_id"] for r in target_rows)
        # Keep target_rows for processing; keep all rows in output (just enrich subset)
        print(f"Geocoding {len(target_rows)} priority venues (websites: {len(rows_with_web)}, sample: {len(sampled)})", flush=True)
    else:
        target_rows = rows
        target_ids = set(r["source_venue_id"] for r in rows)

    cache = load_cache()
    print(f"Cache: {len(cache)} entries", flush=True)

    fields = list(rows[0].keys())
    enriched = []
    stats = {"api_calls": 0, "cache_hits": 0}
    skipped = 0
    last_save = time.time()

    for idx, row in enumerate(rows):
        # Skip venues not in target set when limit applied
        if row["source_venue_id"] not in target_ids:
            enriched.append(row)
            continue

        # Skip if already enriched
        if row.get("city") and row.get("region"):
            enriched.append(row)
            skipped += 1
            continue

        lat = row.get("latitude")
        lon = row.get("longitude")
        if not lat or not lon:
            enriched.append(row)
            continue

        result = reverse_geocode(lat, lon, cache, stats)
        if result:
            # Only overwrite empty fields
            if not row.get("city") and result.get("city"):
                row["city"] = result["city"]
            if not row.get("province") and result.get("province"):
                row["province"] = result["province"]
            if not row.get("region") and result.get("region"):
                row["region"] = result["region"]
            if not row.get("postal_code") and result.get("postal_code"):
                row["postal_code"] = result["postal_code"]

            # Filter out non-IT venues
            if result.get("country") and result["country"] != "IT":
                row["extraction_status"] = "non_it_skip"

        enriched.append(row)

        if stats["api_calls"] > 0 and stats["api_calls"] % 100 == 0:
            print(f"  Progress {stats['api_calls']} API calls | cache_hits {stats['cache_hits']} | venues seen {idx+1}/{len(rows)}", flush=True)
            if time.time() - last_save > 30:
                save_cache(cache)
                last_save = time.time()

    save_cache(cache)

    with open(OUTPUT_CSV, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(enriched)

    print(f"\nWritten: {OUTPUT_CSV}", flush=True)
    # Stats
    with_city = sum(1 for r in enriched if r.get("city"))
    with_region = sum(1 for r in enriched if r.get("region"))
    print(f"  with city: {with_city}/{len(enriched)}", flush=True)
    print(f"  with region: {with_region}/{len(enriched)}", flush=True)


if __name__ == "__main__":
    main()
