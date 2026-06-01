#!/usr/bin/env python3
"""
Beach S2 — Build enriched venues CSV from partial geocoding cache.
Apply current cache state to s1_venues.csv → s2_venues_enriched.csv.
Re-runnable: each invocation refreshes output from latest cache.
"""

import csv
import json
import os

INPUT_CSV = "raw_sources/beach_s1_venues.csv"
OUTPUT_CSV = "raw_sources/beach_s2_venues_enriched.csv"
CACHE_FILE = "raw_sources/.geocode_cache.json"


def main():
    cache = {}
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, encoding="utf-8") as f:
            cache = json.load(f)
    print(f"Cache: {len(cache)} entries")

    with open(INPUT_CSV, encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    fields = list(rows[0].keys())

    enriched_count = 0
    non_it_count = 0
    for row in rows:
        lat = row.get("latitude")
        lon = row.get("longitude")
        if not lat or not lon:
            continue
        try:
            key = f"{round(float(lat), 5)},{round(float(lon), 5)}"
        except ValueError:
            continue
        result = cache.get(key)
        if not result:
            continue
        if result.get("country") and result["country"] != "IT":
            row["extraction_status"] = "non_it_skip"
            non_it_count += 1
            continue
        before = (row.get("city"), row.get("province"), row.get("region"))
        if not row.get("city") and result.get("city"):
            row["city"] = result["city"]
        if not row.get("province") and result.get("province"):
            row["province"] = result["province"]
        if not row.get("region") and result.get("region"):
            row["region"] = result["region"]
        if not row.get("postal_code") and result.get("postal_code"):
            row["postal_code"] = result["postal_code"]
        after = (row.get("city"), row.get("province"), row.get("region"))
        if after != before:
            enriched_count += 1

    with open(OUTPUT_CSV, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)

    with_city = sum(1 for r in rows if r.get("city"))
    with_region = sum(1 for r in rows if r.get("region"))
    print(f"Enriched: {enriched_count}")
    print(f"Non-IT marked: {non_it_count}")
    print(f"Total venues: {len(rows)}")
    print(f"  with city: {with_city} ({100*with_city/len(rows):.1f}%)")
    print(f"  with region: {with_region} ({100*with_region/len(rows):.1f}%)")
    print(f"Written: {OUTPUT_CSV}")


if __name__ == "__main__":
    main()
