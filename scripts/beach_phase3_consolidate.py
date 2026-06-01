#!/usr/bin/env python3
"""
Phase 3.6 — Consolidation di TUTTI i menu items beach (S1 + S2 + Phase 3).
Dedup + quality gates + stats finali.
"""
import csv
import os

FILES_TO_MERGE = [
    "raw_sources/beach_s1_menu_items.csv",
    "raw_sources/beach_s2_direct_menu_items.csv",
    "raw_sources/beach_s2_pdf_menu_items.csv",
    "raw_sources/beach_phase3_spiagge_menu_items.csv",
]

OUTPUT = "raw_sources/beach_phase3_consolidated_items.csv"

GOOD_PRODUCTS = {
    "beach_umbrella_standard", "beach_umbrella_first_row", "beach_umbrella_premium",
    "beach_sunbed", "beach_chair", "beach_cabin_day", "beach_cabin_season",
    "beach_set_2lettini_ombrellone", "beach_set_1lettino_ombrellone",
    "beach_parking", "beach_shower", "beach_subscription_week",
    "beach_subscription_month", "beach_subscription_season",
    "beach_entry_fee", "beach_minimum_spend", "",
}
GOOD_PRICE_TYPES = {
    "per_day_weekday", "per_day_weekend", "per_day", "per_half_day",
    "per_week", "per_month", "per_season", "one_off", "",
}


def main():
    all_rows = []
    field_union = set()
    for f in FILES_TO_MERGE:
        if not os.path.exists(f):
            print(f"  skip: {f} not found")
            continue
        with open(f, encoding="utf-8", newline="") as fh:
            reader = csv.DictReader(fh)
            rows = list(reader)
            print(f"  loaded: {f} ({len(rows)} rows)")
            for r in rows:
                # Tag origin
                r["_origin_file"] = os.path.basename(f)
                all_rows.append(r)
                field_union.update(r.keys())

    print(f"\nTotal loaded: {len(all_rows)} rows")

    # Quality filter
    clean = []
    rej_reasons = {"bad_price": 0, "bad_product": 0, "bad_price_type": 0, "bad_vertical": 0}
    for r in all_rows:
        try:
            p = float(r.get("normalized_price_eur") or 0)
        except ValueError:
            rej_reasons["bad_price"] += 1
            continue
        if p <= 0 or p > 7500:
            rej_reasons["bad_price"] += 1
            continue
        if r.get("normalized_product", "") not in GOOD_PRODUCTS:
            rej_reasons["bad_product"] += 1
            continue
        if r.get("price_type", "") not in GOOD_PRICE_TYPES:
            rej_reasons["bad_price_type"] += 1
            continue
        if r.get("vertical") != "beach":
            rej_reasons["bad_vertical"] += 1
            continue
        clean.append(r)

    print(f"After QC: {len(clean)} rows | rejected: {rej_reasons}")

    # Dedup
    seen = set()
    unique = []
    for r in clean:
        k = (
            r.get("source_venue_id", ""),
            r.get("normalized_product", ""),
            r.get("raw_price", ""),
            r.get("price_type", ""),
            r.get("peak_or_mid", ""),
            r.get("check_in_date", ""),
        )
        if k not in seen:
            seen.add(k)
            unique.append(r)

    print(f"After dedup: {len(unique)} unique rows")

    # Write CSV with union of fields
    fields = sorted(field_union | {"_origin_file"})
    with open(OUTPUT, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for r in unique:
            w.writerow({k: r.get(k, "") for k in fields})
    print(f"\nWritten: {OUTPUT}")

    # Final stats
    from collections import Counter
    venues_priced = set(r["source_venue_id"] for r in unique)
    print(f"\n=== FINAL CONSOLIDATED STATS ===")
    print(f"Total items: {len(unique)}")
    print(f"Unique venues priced: {len(venues_priced)}")
    print(f"\nBy source platform:")
    for k, c in Counter(r.get("source_platform", "") for r in unique).most_common():
        print(f"  {c:5d}  {k}")
    print(f"\nBy product:")
    for k, c in Counter(r.get("normalized_product", "") for r in unique).most_common():
        print(f"  {c:5d}  {k}")
    print(f"\nBy price_type:")
    for k, c in Counter(r.get("price_type", "") for r in unique).most_common():
        print(f"  {c:5d}  {k}")
    print(f"\nBy confidence:")
    for k, c in Counter(r.get("confidence", "") for r in unique).most_common():
        print(f"  {c:5d}  {k}")


if __name__ == "__main__":
    main()
