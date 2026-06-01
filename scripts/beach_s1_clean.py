#!/usr/bin/env python3
"""
Beach S1 — Clean and filter OSM venues, removing false positives.
Adds spiagge.it aggregator data via web search results.
"""
import csv
import re
import json
from datetime import datetime, timezone

INPUT = "raw_sources/beach_s1_venues.csv"
OUTPUT = "raw_sources/beach_s1_venues.csv"

# Categories that clearly are NOT beach clubs
SKIP_CATEGORIES = {
    "pharmacy", "police", "place_of_worship", "ferry_terminal",
    "drinking_water", "shelter", "townhall", "public_bath",
    "caravan_site",  # camping, not beach clubs
}

# Italian municipality name patterns — comuni whose names contain bagni/bagno/bagnolo
# These are false positives from name-based OSM search
COMUNE_PATTERNS = [
    r"^bagno a ripoli$",
    r"^bagno di romagna$",
    r"^bagni di lucca$",
    r"^bagnone$",
    r"^bagnolo\s+\w+",       # Bagnolo Mella, Bagnolo San Vito, etc.
    r"^bagnara\s+\w+",
    r"^bagnaria\s+\w+",
    r"^san casciano dei bagni$",
    r"^rapolano terme$",
    r"^riva di bagnolo$",
    r"^san giovanni in fiore$",  # not beach
    r"^lido di camaiore$",       # This IS a beach town → keep it  (override below)
]

# Actual beach municipalities that we want to KEEP even if they match comune pattern
KEEP_LOCATIONS = {
    "lido di camaiore", "lido di jesolo", "lido di venezia",
    "lido di savio", "lido di classe", "lido di ostia",
    "lido degli estensi", "lido di spina", "lido di pomposa",
}

# Categories that indicate genuine beach/water venues
BEACH_CATEGORIES = {
    "beach_resort", "swimming_pool", "water_park", "spa",
    "resort", "camp_site",  # many Italian campings are coastal
}

# Suffixes that suggest a real venue not a comune
VENUE_INDICATORS = {
    "stabilimento", "balneare", "club", "resort", "lido ",
    "bagni ", "bagno ", "spiaggia ", "piscina", "terme",
}


def is_false_positive(row):
    name_lower = row["venue_name"].lower().strip()
    category = row["categories"].lower() if row["categories"] else ""

    # Keep if strong beach category
    for bc in BEACH_CATEGORIES:
        if bc in category:
            return False

    # Remove if clearly wrong category
    for sc in SKIP_CATEGORIES:
        if sc in category:
            return True

    # Remove comuni with no geo amenity tag (categories='none' or empty)
    # that match Italian municipality name patterns
    if not category or category == "none":
        if name_lower in KEEP_LOCATIONS:
            return False
        for pat in COMUNE_PATTERNS:
            if re.match(pat, name_lower):
                return True

    # Remove if restaurant/bar/cafe/hotel with no beach connection in name
    bad_cats = {"restaurant", "bar", "cafe", "hotel", "pharmacy",
                "fast_food", "information", "parking", "pitch",
                "sports_centre", "park", "attraction", "guest_house"}
    for bc in bad_cats:
        if bc in category and bc not in BEACH_CATEGORIES:
            # Check if name suggests beach connection
            has_beach_indicator = any(vi in name_lower for vi in VENUE_INDICATORS)
            has_beach_word = any(w in name_lower for w in
                                  ["beach", "mare", "spiaggia", "marina",
                                   "lido", "balnear", "costiero", "riviera"])
            if not has_beach_indicator and not has_beach_word:
                return True

    return False


def main():
    with open(INPUT, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    print(f"Input: {len(rows)} rows")

    kept = []
    removed = []
    for row in rows:
        if is_false_positive(row):
            removed.append(row)
        else:
            kept.append(row)

    print(f"Kept: {len(kept)} | Removed: {len(removed)}")

    # Sample removed for review
    print("\nSample removed:")
    for r in removed[:15]:
        print(f"  {r['venue_name']} | {r['categories']} | {r['city']}")

    print("\nSample kept:")
    for r in kept[:15]:
        print(f"  {r['venue_name']} | {r['categories']} | {r['city']}")

    # Write cleaned file
    fields = list(rows[0].keys())
    with open(OUTPUT, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(kept)

    print(f"\nWritten cleaned: {OUTPUT} ({len(kept)} rows)")


if __name__ == "__main__":
    main()
