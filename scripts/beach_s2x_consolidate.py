#!/usr/bin/env python3
"""
S2X Phase E — Consolidation con master S1+S2.
Match per geo (≤300m) + fallback name+city (>0.85 ratio).
Output:
  - beach_s2x_spiagge_consolidated_venues.csv  (master S1 + nuovi spiagge)
  - beach_s2x_master_updates.csv               (diff applicabili al master S1)
"""

import csv
import os
from math import radians, cos, sin, asin, sqrt
from difflib import SequenceMatcher
from datetime import datetime, timezone

MASTER_S1 = "raw_sources/beach_s1_venues.csv"
SPIAGGE = "raw_sources/beach_s2x_spiagge_venues.csv"
OUT_CONSOLIDATED = "raw_sources/beach_s2x_spiagge_consolidated_venues.csv"
OUT_UPDATES = "raw_sources/beach_s2x_master_updates.csv"

RADIUS_M = 300


def haversine_m(lat1, lon1, lat2, lon2):
    R = 6371000.0
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2) ** 2
    return 2 * R * asin(sqrt(a))


def name_sim(a, b):
    return SequenceMatcher(None, a.lower().strip(), b.lower().strip()).ratio()


def main():
    with open(MASTER_S1, encoding="utf-8", newline="") as f:
        master = list(csv.DictReader(f))
    with open(SPIAGGE, encoding="utf-8", newline="") as f:
        spiagge = list(csv.DictReader(f))

    print(f"Master S1: {len(master)} venues")
    print(f"Spiagge S2X: {len(spiagge)} venues")

    # Bucket master by integer lat/lon for faster lookup
    buckets = {}
    for m in master:
        try:
            lat = float(m["latitude"])
            lon = float(m["longitude"])
        except (ValueError, KeyError):
            continue
        # 0.01 deg ≈ 1.1 km — sufficiently broad bucket
        key = (round(lat * 100), round(lon * 100))
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                buckets.setdefault((key[0] + dx, key[1] + dy), []).append((lat, lon, m))

    matched_geo = 0
    matched_name = 0
    no_match = 0
    updates = []
    consolidated = []

    consolidated_fields = list(spiagge[0].keys()) + [
        "master_source_venue_id", "match_type", "match_distance_m", "match_name_ratio"
    ]

    for sp in spiagge:
        try:
            lat = float(sp["latitude"])
            lon = float(sp["longitude"])
        except (ValueError, KeyError):
            lat = lon = None

        best = None  # (distance_m, master_row)
        if lat is not None and lon is not None:
            key = (round(lat * 100), round(lon * 100))
            candidates = buckets.get(key, [])
            for mlat, mlon, mrow in candidates:
                d = haversine_m(lat, lon, mlat, mlon)
                if d <= RADIUS_M and (best is None or d < best[0]):
                    best = (d, mrow)

        match_type = "no_match"
        match_distance = ""
        match_ratio = ""
        master_id = ""

        if best:
            d, mrow = best
            # Confirm name similarity > 0.5 to filter out coincidental same-coord
            r = name_sim(sp["venue_name"], mrow["venue_name"])
            if r > 0.5:
                match_type = "geo_300m"
                master_id = mrow["source_venue_id"]
                match_distance = f"{d:.1f}"
                match_ratio = f"{r:.2f}"
                matched_geo += 1
            else:
                # Same area but different name → keep as candidate but no link
                match_type = "geo_only_name_diff"
                match_distance = f"{d:.1f}"
                match_ratio = f"{r:.2f}"
                no_match += 1
        else:
            # Fallback: name+city match (slow)
            city = sp["city"]
            if city:
                best_n = None
                for m in master:
                    if not m["city"] or m["city"].lower() != city.lower():
                        continue
                    r = name_sim(sp["venue_name"], m["venue_name"])
                    if r > 0.85 and (best_n is None or r > best_n[0]):
                        best_n = (r, m)
                if best_n:
                    r, mrow = best_n
                    match_type = "name_city"
                    master_id = mrow["source_venue_id"]
                    match_ratio = f"{r:.2f}"
                    matched_name += 1
                else:
                    no_match += 1
            else:
                no_match += 1

        # Build consolidated row
        row = dict(sp)
        row["master_source_venue_id"] = master_id
        row["match_type"] = match_type
        row["match_distance_m"] = match_distance
        row["match_name_ratio"] = match_ratio
        consolidated.append(row)

        # Generate updates for matched venues (only fill missing fields in master)
        if master_id:
            # Find master row
            mrow = next((m for m in master if m["source_venue_id"] == master_id), None)
            if mrow:
                for field in ("phone", "address", "city", "region", "postal_code"):
                    if not mrow.get(field) and sp.get(field):
                        updates.append({
                            "master_source_venue_id": master_id,
                            "field": field,
                            "old_value": mrow.get(field, ""),
                            "new_value": sp.get(field),
                            "source": f"spiagge:{sp['spiagge_venue_id']}",
                        })
                # booking_provider always set if master had none
                if not mrow.get("booking_provider"):
                    updates.append({
                        "master_source_venue_id": master_id,
                        "field": "booking_provider",
                        "old_value": "",
                        "new_value": "spiagge.it",
                        "source": f"spiagge:{sp['spiagge_venue_id']}",
                    })

    print(f"\nMatch results:")
    print(f"  geo_300m: {matched_geo}")
    print(f"  name_city: {matched_name}")
    print(f"  no_match (truly new venues): {no_match}")
    print(f"\nMaster update suggestions: {len(updates)}")

    with open(OUT_CONSOLIDATED, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=consolidated_fields)
        w.writeheader()
        w.writerows(consolidated)
    print(f"Written: {OUT_CONSOLIDATED}")

    with open(OUT_UPDATES, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=[
            "master_source_venue_id", "field", "old_value", "new_value", "source"
        ])
        w.writeheader()
        w.writerows(updates)
    print(f"Written: {OUT_UPDATES}")


if __name__ == "__main__":
    main()
