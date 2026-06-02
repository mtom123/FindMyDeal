# Supabase Setup — Piano per stasera

## Obiettivo
Creare infrastruttura crowdsourcing per prezzi palestre.  
Quando un utente conosce il prezzo della sua palestra, lo inserisce → validato → mostrato nella mappa.

---

## Step 1: Crea progetto Supabase (fai tu, CEO ti guida)

1. Vai su [supabase.com](https://supabase.com) → New Project
2. Nome: `surprice-prod`
3. Password DB: genera e salva in `.env`
4. Region: EU West (Ireland)

---

## Step 2: Schema SQL da eseguire in Supabase SQL Editor

```sql
-- Tabella palestre (sync dal master CSV)
CREATE TABLE gyms (
  id TEXT PRIMARY KEY,  -- = source_venue_id dal master CSV
  name TEXT NOT NULL,
  city TEXT,
  region TEXT,
  lat DECIMAL(10,7),
  lon DECIMAL(10,7),
  brand TEXT,
  venue_type TEXT,
  website TEXT,
  vertical TEXT DEFAULT 'gym',
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Tabella prezzi (crowdsourced + scraped)
CREATE TABLE gym_prices (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  gym_id TEXT REFERENCES gyms(id) ON DELETE CASCADE,
  price_monthly DECIMAL(8,2),    -- abbonamento mensile
  price_annual DECIMAL(8,2),     -- abbonamento annuale
  price_day_pass DECIMAL(8,2),   -- ingresso singolo
  price_signup DECIMAL(8,2),     -- quota iscrizione
  source TEXT NOT NULL,          -- 'user_submitted' | 'scraped_web' | 'scraped_chain'
  user_id UUID REFERENCES auth.users(id),
  confidence TEXT DEFAULT 'medium',  -- 'high' | 'medium' | 'low'
  note TEXT,
  valid_from DATE,
  verified BOOLEAN DEFAULT FALSE,
  upvotes INTEGER DEFAULT 0,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Index per query veloci
CREATE INDEX idx_gym_prices_gym_id ON gym_prices(gym_id);
CREATE INDEX idx_gym_prices_source ON gym_prices(source);
CREATE INDEX idx_gyms_city ON gyms(city);
CREATE INDEX idx_gyms_lat_lon ON gyms(lat, lon);

-- RLS (Row Level Security)
ALTER TABLE gyms ENABLE ROW LEVEL SECURITY;
ALTER TABLE gym_prices ENABLE ROW LEVEL SECURITY;

-- Policy: tutti possono leggere
CREATE POLICY "Public read gyms" ON gyms FOR SELECT USING (true);
CREATE POLICY "Public read prices" ON gym_prices FOR SELECT USING (true);

-- Policy: solo utenti autenticati possono inserire prezzi
CREATE POLICY "Auth users insert prices" ON gym_prices 
  FOR INSERT WITH CHECK (auth.uid() = user_id);

-- Policy: utenti possono aggiornare solo i propri prezzi
CREATE POLICY "Auth users update own prices" ON gym_prices 
  FOR UPDATE USING (auth.uid() = user_id);

-- View aggregata per frontend (prezzo medio per palestra)
CREATE OR REPLACE VIEW gym_price_summary AS
SELECT 
  g.id,
  g.name,
  g.city,
  g.region,
  g.lat,
  g.lon,
  g.brand,
  g.venue_type,
  g.website,
  COUNT(gp.id) AS price_count,
  AVG(gp.price_monthly) AS avg_monthly,
  MIN(gp.price_monthly) AS min_monthly,
  MAX(gp.price_monthly) AS max_monthly,
  AVG(gp.price_day_pass) AS avg_day_pass,
  AVG(gp.price_annual) AS avg_annual
FROM gyms g
LEFT JOIN gym_prices gp ON g.id = gp.gym_id
GROUP BY g.id, g.name, g.city, g.region, g.lat, g.lon, g.brand, g.venue_type, g.website;
```

---

## Step 3: Upload master CSV su Supabase

Script Python da eseguire dopo setup:

```python
# upload_gyms_to_supabase.py
import csv, os
from supabase import create_client

SUPABASE_URL = os.environ['SUPABASE_URL']
SUPABASE_KEY = os.environ['SUPABASE_SERVICE_KEY']
sb = create_client(SUPABASE_URL, SUPABASE_KEY)

with open('agent_ceo_gym/gym_master_italia.csv', encoding='utf-8') as f:
    rows = list(csv.DictReader(f))

records = []
for r in rows:
    records.append({
        'id': r['source_venue_id'],
        'name': r['venue_name'],
        'city': r['city'],
        'lat': float(r['latitude']) if r['latitude'] else None,
        'lon': float(r['longitude']) if r['longitude'] else None,
        'brand': r.get('brand') or None,
        'venue_type': r.get('venue_type', 'gym'),
        'website': r.get('venue_url') or None,
        'vertical': 'gym',
    })

# Batch insert (1000 alla volta)
for i in range(0, len(records), 1000):
    batch = records[i:i+1000]
    sb.table('gyms').upsert(batch).execute()
    print(f"Uploaded {min(i+1000, len(records))}/{len(records)}")

print("DONE")
```

---

## Step 4: Upload prezzi già estratti

Dopo Step 3, caricare i prezzi da:
- `agent_ceo_gym/gym_chain_prices.csv` → source='scraped_chain', confidence='high'
- `agent_ceo_gym/gym_website_prices.csv` → source='scraped_web', confidence='medium'

---

## Step 5: Configurazione Auth (per crowdsourcing)

In Supabase Dashboard → Authentication → Providers:
- Abilita **Google OAuth** (serve Google Cloud Console)
- Redirect URL: `https://surprice.vercel.app/auth/callback`

---

## Step 6: Landing page crowdsourcing (Peppe - dopo backend)

Pagina semplice che:
1. Mostra una palestra casuale della tua città
2. Chiede: "Conosci il prezzo? Inseriscilo!"
3. Form: mensile / annuale / day pass
4. Auth con Google
5. Submit → Supabase

Gamification: badge "Price Hunter", "Verificatore" ecc.

---

## Env variables da settare

```bash
SUPABASE_URL=https://xxxxx.supabase.co
SUPABASE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...  # anon key
SUPABASE_SERVICE_KEY=eyJ...  # service role key (solo backend)
ANTHROPIC_API_KEY=sk-ant-...  # già disponibile
```
