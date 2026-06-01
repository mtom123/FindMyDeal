#!/usr/bin/env bash
# Run after Phase C batch completes: regenerate venues CSV from cache,
# then consolidate with master S1.
set -e
cd /Users/g_giaimo02/Desktop/TTW/FindMyDeal

echo "Cache: $(ls raw_sources/.spiagge_cache/ | wc -l) entries"

# Regenerate venues CSV from cache (force re-run by removing existing CSV)
echo "Regenerating beach_s2x_spiagge_venues.csv..."
python3 scripts/beach_s2x_metadata.py 0 4 0  # workers=4, delay=0 because cache hits only

echo "Running consolidation..."
python3 scripts/beach_s2x_consolidate.py

echo ""
echo "=== FINAL STATS ==="
python3 -c "
import csv
with open('raw_sources/beach_s2x_spiagge_venues.csv') as f:
    rows = list(csv.DictReader(f))
ok = sum(1 for r in rows if r['extraction_status']=='ok')
geo = sum(1 for r in rows if r['latitude'])
print(f'Spiagge venues: {len(rows)} | ok: {ok} | with_geo: {geo}')
"
