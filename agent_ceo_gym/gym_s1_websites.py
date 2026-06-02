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
import anthropic

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

OUT_DIR = os.path.dirname(__file__)
MASTER_CSV = os.path.join(OUT_DIR, 'gym_master_italia.csv')
OUT_CSV = os.path.join(OUT_DIR, 'gym_website_prices.csv')

# Suffissi da provare dopo l'URL base
PRICE_PATHS = [
    '/prezzi', '/abbonamenti', '/abbonamento', '/tariffe', '/tariffe-e-prezzi',
    '/iscrizione', '/iscrivi', '/join', '/membership', '/piani',
    '/pricing', '/plans', '/rates', '/cost',
]

anthropic_client = anthropic.Anthropic()

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

    for url in urls_to_try[:6]:  # max 6 URL per palestra
        try:
            resp = await page.goto(url, wait_until='domcontentloaded', timeout=15000)
            if not resp or resp.status >= 400:
                continue

            await asyncio.sleep(1.5)
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
    print(f"  Processando prime 150...")
    gyms = gyms[:150]

    results = []

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

        for i, gym in enumerate(gyms):
            name = gym.get('venue_name', 'Unknown')
            city = gym.get('city', '')
            url = gym.get('venue_url', '')

            print(f"\n[{i+1}/{len(gyms)}] {name[:50]} ({city})")

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

            # Salva ogni 20
            if (i + 1) % 20 == 0 and results:
                _save(results)
                print(f"\n  [checkpoint] {len(results)} prezzi totali\n")

            await asyncio.sleep(1)

        await browser.close()

    print(f"\n=== RISULTATI FINALI ===")
    print(f"Palestre con prezzi: {len(set(r['gym_id'] for r in results))}")
    print(f"Prezzi totali: {len(results)}")

    if results:
        by_type = {}
        for r in results:
            by_type.setdefault(r['price_type'], []).append(r['price'])
        for t, prices in by_type.items():
            avg = sum(prices) / len(prices)
            print(f"  [{t}] n={len(prices)} min={min(prices):.2f} max={max(prices):.2f} avg={avg:.2f}")

    _save(results)


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
