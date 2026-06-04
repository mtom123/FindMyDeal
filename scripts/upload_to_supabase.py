#!/usr/bin/env python3
"""
Upload gym master + prices to Supabase.
Usato una volta sola per bootstrappare il DB.

Setup:
  Crea website/.env con:
    SUPABASE_URL=https://xxx.supabase.co
    SUPABASE_SERVICE_KEY=eyJ...

Run:
  cd website/
  python scripts/upload_to_supabase.py
"""
import csv, sys, os, time
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# Legge chiavi da .env (mai committare .env su GitHub)
def load_env(path):
    env = {}
    try:
        for line in open(path):
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                k, v = line.split('=', 1)
                env[k.strip()] = v.strip()
    except FileNotFoundError:
        pass
    return env

env = load_env(os.path.join(os.path.dirname(__file__), '..', '.env'))

SUPABASE_URL = os.environ.get('SUPABASE_URL') or env.get('SUPABASE_URL')
SERVICE_KEY  = os.environ.get('SUPABASE_SERVICE_KEY') or env.get('SUPABASE_SERVICE_KEY')

if not SUPABASE_URL or not SERVICE_KEY:
    print("ERRORE: mancano SUPABASE_URL o SUPABASE_SERVICE_KEY in .env")
    sys.exit(1)

from supabase import create_client
sb = create_client(SUPABASE_URL, SERVICE_KEY)

# ── 1. UPLOAD GYMS (12.648 venue) ──────────────────────────────────────
print("=== STEP 1: Upload gyms ===")
master_path = os.path.join(os.path.dirname(__file__), '..', 'raw_sources', 'gym_master_italia.csv')

with open(master_path, encoding='utf-8-sig') as f:
    rows = list(csv.DictReader(f))

print(f"Letti {len(rows)} record dal master CSV")

records = []
for r in rows:
    lat = r.get('latitude','').strip()
    lon = r.get('longitude','').strip()
    vid = r.get('source_venue_id','').strip()
    if not vid:
        continue
    records.append({
        'id':       vid,
        'name':     (r.get('venue_name') or '').strip(),
        'city':     (r.get('city') or '').strip() or None,
        'lat':      float(lat) if lat else None,
        'lon':      float(lon) if lon else None,
        'website':  (r.get('venue_url') or '').strip() or None,
        'vertical': 'gym',
    })

BATCH = 500
ok = 0
for i in range(0, len(records), BATCH):
    batch = records[i:i+BATCH]
    try:
        sb.table('gyms').upsert(batch, on_conflict='id').execute()
        ok += len(batch)
        print(f"  Gyms: {ok}/{len(records)}")
    except Exception as e:
        print(f"  ERRORE batch {i}: {e}")
    time.sleep(0.1)

print(f"Gyms caricati: {ok}\n")

# ── 2. UPLOAD WEBSITE PRICES ───────────────────────────────────────────
print("=== STEP 2: Upload gym website prices ===")
prices_path = os.path.join(os.path.dirname(__file__), '..', 'agent_ceo_gym', 'gym_website_prices.csv')

with open(prices_path, encoding='utf-8-sig') as f:
    price_rows = list(csv.DictReader(f))

price_records = []
for r in price_rows:
    price_str = r.get('price','').strip().replace('€','').replace(',','.').strip()
    price_val = None
    try:
        price_val = float(price_str) if price_str else None
    except: pass

    price_type = r.get('price_type','monthly').strip().lower()
    rec = {'gym_id': r.get('gym_id','').strip() or None, 'source': 'scraped_web', 'confidence': r.get('confidence','medium').strip()}
    if price_type in ('monthly','mensile'): rec['price_monthly'] = price_val
    elif price_type in ('annual','annuale'): rec['price_annual'] = price_val
    elif price_type in ('day_pass','ingresso'): rec['price_day_pass'] = price_val
    else: rec['price_monthly'] = price_val
    if rec['gym_id']:
        price_records.append(rec)

if price_records:
    try:
        sb.table('gym_prices').upsert(price_records).execute()
        print(f"Inseriti {len(price_records)} prezzi web")
    except Exception as e:
        print(f"ERRORE prezzi web: {e}")

# ── 3. UPLOAD CHAIN PRICES ─────────────────────────────────────────────
print("\n=== STEP 3: Upload chain prices ===")
chains_path = os.path.join(os.path.dirname(__file__), '..', 'agent_ceo_gym', 'gym_chain_prices.csv')

with open(chains_path, encoding='utf-8-sig') as f:
    chain_rows = list(csv.DictReader(f))

chain_records = []
for r in chain_rows:
    price_str = r.get('price','').strip().replace('€','').replace(',','.').strip()
    price_val = None
    try:
        price_val = float(price_str) if price_str else None
    except: pass

    price_type = r.get('price_type','').strip().lower()
    rec = {'gym_id': None, 'source': 'scraped_chain', 'confidence': 'high',
           'note': f"{r.get('chain','')} — {r.get('context','')}"}
    if 'annual' in price_type: rec['price_annual'] = price_val
    elif 'day' in price_type:  rec['price_day_pass'] = price_val
    else:                      rec['price_monthly'] = price_val
    chain_records.append(rec)

try:
    sb.table('gym_prices').insert(chain_records).execute()
    print(f"Inseriti {len(chain_records)} prezzi catene")
except Exception as e:
    print(f"ERRORE prezzi catene: {e}")

print(f"\n=== DONE — Gyms: {ok}, Prezzi web: {len(price_records)}, Catene: {len(chain_records)} ===")
