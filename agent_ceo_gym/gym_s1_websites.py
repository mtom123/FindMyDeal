"""
gym_s1_websites.py — Prezzi da siti web delle singole palestre

Strategia:
  1. Carica gym_master_italia.csv
  2. Per ogni palestra con venue_url, visita il sito
  3. Prova /prezzi, /abbonamenti, /tariffe, /iscriviti
  4. Estrai prezzi con regex
  5. Usa Claude Haiku per confermare/classificare

Output: agent_ceo_gym/gym_website_prices.csv
"""

import asyncio, csv, json, os, re, sys, time
from playwright.async_api import async_playwright
try:
    import anthropic
except ImportError:
    anthropic = None  # regex fallback (vedi prompt S9: "regex fallback comunque funziona")

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

OUT_DIR = os.path.dirname(__file__)
MASTER_CSV = os.path.join(OUT_DIR, 'gym_master_italia.csv')
if not os.path.exists(MASTER_CSV):  # in questo repo il master è in raw_sources/
    MASTER_CSV = os.path.join(OUT_DIR, '..', 'raw_sources', 'gym_master_italia.csv')
OUT_CSV = os.path.join(OUT_DIR, 'gym_website_prices.csv')
PROGRESS = os.path.join(OUT_DIR, 'gym_s9_progress.json')  # resume: gym già processati
MAX_SECONDS = 1700  # soft-limit: esci pulito (~28 min) prima del kill background (~34 min)


def gym_key(g):
    return g.get('source_venue_id') or g.get('venue_url') or g.get('venue_name', '')

# Suffissi da provare dopo l'URL base
PRICE_PATHS = [
    '/prezzi', '/abbonamenti', '/abbonamento', '/tariffe', '/tariffe-e-prezzi',
    '/iscrizione', '/iscrivi', '/join', '/membership', '/piani',
    '/pricing', '/plans', '/rates', '/cost',
]

try:
    anthropic_client = anthropic.Anthropic() if anthropic else None
except Exception:
    anthropic_client = None  # no API key → confirm_with_llm cade su regex fallback

# ── Regex extractor ────────────────────────────────────────────────────────────

def extract_prices_from_text(text: str) -> list[dict]:
    results = []
    patterns = [
        (r'(?:abbonament\w+|mensil\w+)[^\d€]{0,30}(\d+[\.,]\d*)\s*€', 'mensile'),
        (r'€\s*(\d+[\.,]\d*)\s*(?:/\s*)?mes[ei]', 'mensile'),
        (r'(\d+[\.,]\d*)\s*€\s*(?:al\s+)?mes[ei]', 'mensile'),
        (r'(\d+[\.,]\d*)\s*euro\s*(?:al\s+)?mes[ei]', 'mensile'),
        (r'(?:quota\s+)?mensile[^\d€]{0,30}(\d+[\.,]\d*)\s*€', 'mensile'),
        (r'(\d+[\.,]\d*)\s*€\s*(?:per\s+)?ann[oi]', 'annuale'),
        (r'(?:abbonament\w+\s+)?annual\w*[^\d€]{0,30}(\d+[\.,]\d*)\s*€', 'annuale'),
        (r'ingress[oi]\s+(?:singol\w+\s+)?(?:da\s+)?(\d+[\.,]\d*)\s*€', 'day_pass'),
        (r'day\s*pass[^\d€]{0,20}(\d+[\.,]\d*)\s*€', 'day_pass'),
        (r'(?:quota\s+)?(?:di\s+)?iscriz\w+[^\d€]{0,30}(\d+[\.,]\d*)\s*€', 'iscrizione'),
        (r'(?:quota\s+)?(?:di\s+)?attivaz\w+[^\d€]{0,30}(\d+[\.,]\d*)\s*€', 'iscrizione'),
    ]
    seen = set()
    for pattern, price_type in patterns:
        for m in re.finditer(pattern, text, re.IGNORECASE):
            try:
                val = float(m.group(1).replace(',', '.'))
                if val < 1 or val > 3000:
                    continue
                key = (round(val, 2), price_type)
                if key not in seen:
                    seen.add(key)
                    ctx_start = max(0, m.start() - 60)
                    ctx_end = min(len(text), m.end() + 60)
                    results.append({
                        'price': round(val, 2),
                        'price_type': price_type,
                        'context': text[ctx_start:ctx_end].strip(),
                    })
            except:
                pass
    return results


async def confirm_with_llm(prices: list[dict], gym_name: str, url: str) -> list[dict]:
    """Usa Claude Haiku per filtrare i prezzi plausibili e aggiungi confidenza."""
    if not prices:
        return []

    if anthropic_client is None:   # nessun anthropic/API key → regex fallback (confidenza media)
        for p in prices:
            p['confidenza'] = 'media'
        return prices

    prompt = f"""Palestra: {gym_name}
URL: {url}
Prezzi estratti da regex:
{json.dumps(prices, ensure_ascii=False, indent=2)}

Questi prezzi sono plausibili per una palestra italiana?
Rimuovi prezzi che sembrano non essere abbonamenti/ingressi (es. prezzi di prodotti, prezzi anomali).
Per ogni prezzo plausibile, aggiungi campo "confidenza": "alta" o "media".

Rispondi SOLO con JSON array:
[{{"price": X, "price_type": "mensile|annuale|day_pass|iscrizione", "confidenza": "alta|media", "context": "..."}}]
Se nessun prezzo è plausibile rispondi: []"""

    try:
        msg = anthropic_client.messages.create(
            model='claude-haiku-4-5-20251001',
            max_tokens=512,
            messages=[{'role': 'user', 'content': prompt}]
        )
        text = msg.content[0].text.strip()
        # Estrai JSON dall'eventuale testo extra
        json_match = re.search(r'\[.*\]', text, re.DOTALL)
        if json_match:
            return json.loads(json_match.group(0))
        return []
    except Exception as e:
        print(f"    LLM ERR: {e}")
        # Fallback: restituisci prezzi raw con confidenza media
        for p in prices:
            p['confidenza'] = 'media'
        return prices


async def scrape_gym_website(page, venue: dict) -> list[dict]:
    """Scrape un singolo sito web palestra. Ritorna lista di prezzi trovati."""
    base_url = venue.get('venue_url', '')
    name = venue.get('venue_name', '')

    if not base_url or base_url == '':
        return []

    # Normalizza URL
    if not base_url.startswith('http'):
        base_url = 'https://' + base_url

    # Estrai dominio base
    domain_match = re.match(r'(https?://[^/]+)', base_url)
    if not domain_match:
        return []
    domain = domain_match.group(1)

    found_prices = []

    # URL da provare: URL originale + path prezzi
    urls_to_try = [base_url] + [domain + path for path in PRICE_PATHS]

    for idx, url in enumerate(urls_to_try[:6]):  # max 6 URL per palestra
        try:
            resp = await page.goto(url, wait_until='domcontentloaded', timeout=15000)
            if not resp or resp.status >= 400:
                if idx == 0:
                    break  # base URL morto → dominio defunct, salta i 5 price-path (hit-rate-neutral)
                continue

            await asyncio.sleep(1.5)  # config CEO (hit rate ~16%)
            content = await page.content()

            # Rimuovi script/style/HTML
            text = re.sub(r'<(script|style)[^>]*>.*?</\1>', ' ', content, flags=re.DOTALL | re.IGNORECASE)
            text = re.sub(r'<[^>]+>', ' ', text)
            text = re.sub(r'\s+', ' ', text)

            prices = extract_prices_from_text(text)
            if prices:
                print(f"    [FOUND] {len(prices)} prezzi su {url}")
                found_prices.extend(prices)
                break  # trovato prezzi, non serve cercare altri URL

        except Exception as e:
            err = str(e)[:60]
            if idx == 0:
                break  # base URL timeout/errore → salta dominio (no prezzi su domini morti)
            if 'Timeout' not in err:
                print(f"    ERR {url[:50]}: {err}")

    if found_prices:
        # Deduplication
        seen = set()
        unique = []
        for p in found_prices:
            key = (p['price'], p['price_type'])
            if key not in seen:
                seen.add(key)
                unique.append(p)

        # Conferma con LLM
        confirmed = await confirm_with_llm(unique[:10], name, base_url)
        return confirmed

    return []


async def main():
    # Sharding: python gym_s1_websites.py <shard_k> <shard_n> → processa gyms[k::n] in parallelo
    global OUT_CSV, PROGRESS
    shard_k = int(sys.argv[1]) if len(sys.argv) > 1 else 0
    shard_n = int(sys.argv[2]) if len(sys.argv) > 2 else 1
    if shard_n > 1:
        OUT_CSV = os.path.join(OUT_DIR, f'gym_website_prices_s{shard_k}.csv')
        PROGRESS = os.path.join(OUT_DIR, f'gym_s9_progress_s{shard_k}.json')
        print(f"SHARD {shard_k}/{shard_n} → {os.path.basename(OUT_CSV)}")

    # Carica palestre con sito web
    gyms_with_url = []
    with open(MASTER_CSV, newline='', encoding='utf-8') as f:
        for row in csv.DictReader(f):
            url = row.get('venue_url', '')
            if url and url.startswith('http') and 'anytimefitness' not in url:
                gyms_with_url.append(row)

    print(f"Palestre con sito web: {len(gyms_with_url)}")

    # Filtra top città
    priority_cities = ['Milano', 'Roma', 'Torino', 'Napoli', 'Bologna', 'Firenze']
    priority = [g for g in gyms_with_url if any(c.lower() in g.get('city','').lower() for c in priority_cities)]
    others = [g for g in gyms_with_url if g not in priority]
    gyms = priority + others
    print(f"  Top città: {len(priority)}, altre: {len(others)}")
    print(f"  Processando full run...")
    gyms = gyms[:3095]
    if shard_n > 1:
        gyms = gyms[shard_k::shard_n]
        print(f"  SHARD {shard_k}/{shard_n}: {len(gyms)} gym in questo shard")

    # ── RESUME: salta i gym già processati, conserva i prezzi già salvati ──
    done_ids = set()
    if os.path.exists(PROGRESS):
        try: done_ids = set(json.load(open(PROGRESS)))
        except Exception: done_ids = set()
    results = []
    if os.path.exists(OUT_CSV):
        try:
            for row in csv.DictReader(open(OUT_CSV, encoding='utf-8')):
                results.append(row)
                if row.get('gym_id'): done_ids.add(row['gym_id'])
        except Exception: pass
    todo = [g for g in gyms if gym_key(g) not in done_ids]
    print(f"  RESUME: {len(done_ids)} gym già fatti, {len(todo)} da processare (di {len(gyms)})")
    start_t = time.time()
    if not todo:
        print("  Tutti i gym già processati — niente da fare."); _save(results); return

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=['--disable-blink-features=AutomationControlled', '--no-sandbox']
        )
        ctx = await browser.new_context(
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
            locale='it-IT',
            viewport={'width': 1280, 'height': 900},
        )
        page = await ctx.new_page()

        for i, gym in enumerate(todo):
            name = gym.get('venue_name', 'Unknown')
            city = gym.get('city', '')
            url = gym.get('venue_url', '')

            print(f"\n[{i+1}/{len(todo)}] {name[:50]} ({city})")

            prices = await scrape_gym_website(page, gym)
            if prices:
                for p in prices:
                    results.append({
                        'gym_id': gym.get('source_venue_id', ''),
                        'name': name,
                        'city': city,
                        'lat': gym.get('latitude', ''),
                        'lon': gym.get('longitude', ''),
                        'price': p['price'],
                        'price_type': p['price_type'],
                        'confidence': p.get('confidenza', 'media'),
                        'context': p.get('context', '')[:200],
                        'source_url': url,
                        'source': 'website_direct',
                    })
                print(f"  >> {len(prices)} prezzi trovati!")

            done_ids.add(gym_key(gym))

            # Checkpoint frequente (perde al max 10 gym se killed)
            if (i + 1) % 10 == 0:
                _save(results)
                json.dump(list(done_ids), open(PROGRESS, 'w'))
                print(f"\n  [checkpoint] {len(results)} prezzi | {len(done_ids)} gym fatti\n")

            # Soft-timeout: esci pulito prima del kill background, riprendi al prossimo run
            if time.time() - start_t > MAX_SECONDS:
                print(f"\n  SOFT-TIMEOUT {MAX_SECONDS}s → salvo e esco (resume al prossimo lancio)\n")
                break

            await asyncio.sleep(1)

        await browser.close()

    print(f"\n=== RISULTATI FINALI ===")
    print(f"Palestre con prezzi: {len(set(r['gym_id'] for r in results))}")
    print(f"Prezzi totali: {len(results)}")

    if results:
        by_type = {}
        for r in results:
            try: by_type.setdefault(r['price_type'], []).append(float(r['price']))
            except (ValueError, TypeError): pass
        for t, prices in by_type.items():
            if not prices: continue
            avg = sum(prices) / len(prices)
            print(f"  [{t}] n={len(prices)} min={min(prices):.2f} max={max(prices):.2f} avg={avg:.2f}")

    _save(results)
    json.dump(list(done_ids), open(PROGRESS, 'w'))
    remaining = len(todo) - sum(1 for g in todo if gym_key(g) in done_ids)
    print(f"\nRESUME-STATE: {len(done_ids)} gym fatti. "
          f"{'COMPLETO ✓' if remaining == 0 else f'{remaining} rimasti → rilancia per continuare'}")


def _save(results):
    if not results:
        return
    fieldnames = ['gym_id', 'name', 'city', 'lat', 'lon', 'price', 'price_type', 'confidence', 'context', 'source_url', 'source']
    with open(OUT_CSV, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(results)
    print(f"Salvato: {OUT_CSV} ({len(results)} righe)")


if __name__ == '__main__':
    asyncio.run(main())
