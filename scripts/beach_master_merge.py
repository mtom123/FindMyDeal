"""
beach_master_merge.py — CEO master merge per vertical beach.

Logica:
1. Base = beach_s1_venues.csv (9.252 OSM venues)
2. Applica beach_s2x_master_updates.csv: per ogni update, popola SOLO se field master è vuoto.
   MAI sovrascrivere dati esistenti.
3. Append i 4.394 venues NON in master da beach_s2x_spiagge_consolidated_venues.csv
   (match_type == "no_match" o "geo_only_name_diff").
4. Output: beach_master_venues.csv (13.646 venues attesi).
"""

import csv
from pathlib import Path
from collections import defaultdict

REPO = Path("C:/Users/motti/Desktop/FindMyDeal/website")
RAW = REPO / "raw_sources"

# --- STEP 1: Carica master S1
print("=== STEP 1: Carica beach_s1_venues.csv ===")
with open(RAW / "beach_s1_venues.csv", encoding='utf-8-sig') as f:
    reader = csv.DictReader(f)
    s1_fields = reader.fieldnames
    s1_venues = list(reader)
print(f"S1 venues: {len(s1_venues)}")

# Index per source_venue_id
s1_index = {v['source_venue_id']: v for v in s1_venues}
print(f"S1 unique IDs: {len(s1_index)}")

# --- STEP 2: Applica master updates (popola solo campi vuoti)
print("\n=== STEP 2: Applica master updates ===")
with open(RAW / "beach_s2x_master_updates.csv", encoding='utf-8-sig') as f:
    updates = list(csv.DictReader(f))
print(f"Total update suggestions: {len(updates)}")

applied = 0
skipped_already_set = 0
skipped_no_target = 0

# Aggiungi field 'booking_provider' allo schema se non presente
if 'booking_provider' not in s1_fields:
    s1_fields = list(s1_fields) + ['booking_provider']

for upd in updates:
    vid = upd['master_source_venue_id']
    field = upd['field']
    new_val = upd['new_value']

    if vid not in s1_index:
        skipped_no_target += 1
        continue

    target = s1_index[vid]

    # Add field to row if missing
    if field not in target:
        target[field] = ''

    # Apply only if currently empty
    current = (target.get(field) or '').strip()
    if current:
        skipped_already_set += 1
    else:
        target[field] = new_val
        applied += 1

print(f"  Applied: {applied}")
print(f"  Skipped (already set): {skipped_already_set}")
print(f"  Skipped (no target): {skipped_no_target}")

# --- STEP 3: Append nuovi venues da spiagge.it non in master
print("\n=== STEP 3: Append spiagge.it venues NOT in master ===")
with open(RAW / "beach_s2x_spiagge_consolidated_venues.csv", encoding='utf-8-sig') as f:
    reader = csv.DictReader(f)
    spiagge_fields = reader.fieldnames
    spiagge_venues = list(reader)

new_venues = [v for v in spiagge_venues if v.get('match_type','') in ('no_match','geo_only_name_diff')]
print(f"Nuovi venues (no_match + geo_only_name_diff): {len(new_venues)}")

# Schema unificato: prendi tutti i campi da spiagge che NON sono in s1
all_fields = list(s1_fields)
for f in spiagge_fields:
    if f not in all_fields and f not in ('match_type','master_source_venue_id','match_distance_m','match_name_similarity'):
        all_fields.append(f)

# Costruisci righe finali
final_venues = []

# Master s1 (con updates applicati)
for v in s1_venues:
    row = {f: v.get(f, '') for f in all_fields}
    final_venues.append(row)

# Append nuovi venues (escludendo match_type metadata)
for v in new_venues:
    row = {f: v.get(f, '') for f in all_fields}
    final_venues.append(row)

print(f"Total master venues: {len(final_venues)}")

# Output
out = RAW / "beach_master_venues.csv"
with open(out, 'w', encoding='utf-8-sig', newline='') as f:
    writer = csv.DictWriter(f, fieldnames=all_fields, extrasaction='ignore')
    writer.writeheader()
    writer.writerows(final_venues)

print(f"\nWritten: {out}")
print(f"Field count: {len(all_fields)}")

# Stats finali
print("\n=== STATS FINALI ===")
with_provider = sum(1 for v in final_venues if v.get('booking_provider'))
with_city = sum(1 for v in final_venues if v.get('city'))
with_region = sum(1 for v in final_venues if v.get('region'))
with_geo = sum(1 for v in final_venues if v.get('latitude') and v.get('longitude'))
with_amenities = sum(1 for v in final_venues if v.get('amenities'))
print(f"Total venues: {len(final_venues)}")
print(f"  Con geo: {with_geo} ({100*with_geo//len(final_venues)}%)")
print(f"  Con city: {with_city} ({100*with_city//len(final_venues)}%)")
print(f"  Con region: {with_region} ({100*with_region//len(final_venues)}%)")
print(f"  Con booking_provider: {with_provider} ({100*with_provider//len(final_venues)}%)")
print(f"  Con amenities: {with_amenities} ({100*with_amenities//len(final_venues)}%)")

# Region breakdown
from collections import Counter
regions = Counter(v.get('region','') for v in final_venues if v.get('region'))
print(f"\nRegion distribution (top 15):")
for r, c in regions.most_common(15):
    print(f"  {r}: {c}")
