"""
gym_s1_reviews_miner.py — Mining prezzi palestre da recensioni Google Maps

Strategia:
  1. Carica gym_master_italia.csv (top città)
  2. Per ogni palestra, cerca su Google Maps e scarica le recensioni
  3. Usa Claude claude-haiku-4-5-20251001 (o GPT-4o-mini se disponibile) per estrarre prezzi
  4. Aggrega e salva gym_reviews_prices.csv

API: usa Google Places API (GOOGLE_PLACES_API_KEY) oppure
     fallback Playwright su Google Maps (più lento, no API key)

Output: agent_ceo_gym/gym_reviews_prices.csv
"""

import asyncio, csv, json, os, re, time
from playwright.async_api import async_playwright

# ── Config ────────────────────────────────────────────────────────────────────
OUT_DIR = os.path.dirname(__file__)
MASTER_CSV = os.path.join(OUT_DIR, 'gym_master_italia.csv')
OUT_CSV = os.path.join(OUT_DIR, 'gym_reviews_prices.csv')

# API keys (opzionali, fallback su scraping)
GOOGLE_PLACES_KEY = os.environ.get('GOOGLE_PLACES_API_KEY', '')
OPENAI_KEY = os.environ.get('OPENAI_API_KEY', '')
ANTHROPIC_KEY = os.environ.get('ANTHROPIC_API_KEY', '')

# Top città per priorità
PRIORITY_CITIES = ['Milano', 'Roma', 'Torino', 'Napoli', 'Bologna',
                   'Firenze', 'Venezia', 'Genova', 'Palermo', 'Bari']

# ── LLM Price Extractor ───────────────────────────────────────────────────────

SYSTEM_PROMPT = """Sei un estrattore di prezzi per palestre italiane.
Analizza le seguenti recensioni e cerca menzioni di prezzi.
Pattern da cercare: "pago X€/mese", "abbonamento X euro", "mensile X€",
"ingresso X€", "day pass X€", "costa X euro al mese", "X euro mensili", ecc.

Rispondi SOLO con JSON nel formato:
{
  "prezzi_trovati": [
    {"tipo": "mensile|annuale|day_pass|iscrizione|unknown", "valore": 29.90, "confidenza": "alta|media|bassa", "testo_originale": "..."}
  ],
  "nessun_prezzo": true|false
}
Se non trovi prezzi, rispondi {"prezzi_trovati": [], "nessun_prezzo": true}
"""


async def extract_prices_with_llm(reviews_text: str, gym_name: str) -> list[dict]:
    """Usa LLM per estrarre prezzi da testo recensioni."""

    prompt = f"Palestra: {gym_name}\n\nRecensioni:\n{reviews_text[:4000]}"

    # Prova Anthropic Claude prima (spesso disponibile nel progetto)
    if ANTHROPIC_KEY:
        try:
            import anthropic
            client = anthropic.Anthropic(api_key=ANTHROPIC_KEY)
            msg = client.messages.create(
                model='claude-haiku-4-5-20251001',
                max_tokens=512,
                system=SYSTEM_PROMPT,
                messages=[{'role': 'user', 'content': prompt}]
            )
            result = json.loads(msg.content[0].text)
            return result.get('prezzi_trovati', [])
        except Exception as e:
            print(f"    Anthropic ERR: {e}")

    # Fallback: OpenAI
    if OPENAI_KEY:
        try:
            import openai
            client = openai.OpenAI(api_key=OPENAI_KEY)
            resp = client.chat.completions.create(
                model='gpt-4o-mini',
                max_tokens=512,
                messages=[
                    {'role': 'system', 'content': SYSTEM_PROMPT},
                    {'role': 'user', 'content': prompt},
                ],
                response_format={'type': 'json_object'},
            )
            result = json.loads(resp.choices[0].message.content)
            return result.get('prezzi_trovati', [])
        except Exception as e:
            print(f"    OpenAI ERR: {e}")

    # Fallback: regex semplice senza LLM
    return extract_prices_regex(reviews_text)


def extract_prices_regex(text: str) -> list[dict]:
    """Estrazione prezzi con regex senza LLM."""
    results = []
    patterns = [
        (r'pago\s+(?:circa\s+)?(\d+[\.,]?\d*)\s*€?\s*(?:euro)?\s*(?:al\s+mese|mensil)', 'mensile'),
        (r'abbonamento\s+(?:mensile\s+)?(?:di\s+)?(\d+[\.,]?\d*)\s*€', 'mensile'),
        (r'(\d+[\.,]?\d*)\s*€\s*(?:al\s+)?mes[ei]', 'mensile'),
        (r'mensile\s+(?:di\s+)?(\d+[\.,]?\d*)\s*€', 'mensile'),
        (r'(\d+[\.,]?\d*)\s*euro\s+(?:al\s+)?mes[ei]', 'mensile'),
        (r'ingresso\s+(?:singolo\s+)?(?:di\s+)?(\d+[\.,]?\d*)\s*€', 'day_pass'),
        (r'day\s+pass\s+(?:di\s+)?(\d+[\.,]?\d*)\s*€', 'day_pass'),
        (r'(\d+[\.,]?\d*)\s*€\s*(?:per\s+)?anno', 'annuale'),
        (r'annuale\s+(?:di\s+)?(\d+[\.,]?\d*)\s*€', 'annuale'),
        (r'iscriz\w+\s+(?:di\s+)?(\d+[\.,]?\d*)\s*€', 'iscrizione'),
    ]

    seen = set()
    for pattern, price_type in patterns:
        for m in re.finditer(pattern, text, re.IGNORECASE):
            try:
                val = float(m.group(1).replace(',', '.'))
                if val < 1 or val > 2000:
                    continue
                key = (round(val, 2), price_type)
                if key not in seen:
                    seen.add(key)
                    ctx_start = max(0, m.start() - 50)
                    ctx_end = min(len(text), m.end() + 50)
                    results.append({
                        'tipo': price_type,
                        'valore': round(val, 2),
                        'confidenza': 'media',
                        'testo_originale': text[ctx_start:ctx_end].strip(),
                    })
            except:
                pass

    return results


# ── Google Places API ─────────────────────────────────────────────────────────

async def get_reviews_places_api(gym_name: str, lat: float, lon: float) -> str:
    """Cerca palestra via Google Places API e ritorna le recensioni concatenate."""
    import urllib.request, urllib.parse

    if not GOOGLE_PLACES_KEY:
        return ''

    try:
        # Find place
        params = urllib.parse.urlencode({
            'input': gym_name,
            'inputtype': 'textquery',
            'locationbias': f'circle:500@{lat},{lon}',
            'fields': 'place_id,name',
            'key': GOOGLE_PLACES_KEY,
            'language': 'it',
        })
        url = f'https://maps.googleapis.com/maps/api/place/findplacefromtext/json?{params}'
        with urllib.request.urlopen(url, timeout=10) as resp:
            data = json.loads(resp.read())

        if not data.get('candidates'):
            return ''
        place_id = data['candidates'][0]['place_id']

        # Get details with reviews
        params2 = urllib.parse.urlencode({
            'place_id': place_id,
            'fields': 'name,rating,user_ratings_total,reviews',
            'key': GOOGLE_PLACES_KEY,
            'language': 'it',
            'reviews_sort': 'most_relevant',
        })
        url2 = f'https://maps.googleapis.com/maps/api/place/details/json?{params2}'
        with urllib.request.urlopen(url2, timeout=10) as resp2:
            data2 = json.loads(resp2.read())

        reviews = data2.get('result', {}).get('reviews', [])
        return '\n---\n'.join(r.get('text', '') for r in reviews if r.get('text'))

    except Exception as e:
        print(f"    Places API ERR: {e}")
        return ''


# ── Google Maps scraping (fallback senza API key) ─────────────────────────────

async def get_reviews_playwright(page, gym_name: str, city: str) -> str:
    """Cerca palestra su Google Maps e scrapa le recensioni."""
    reviews_text = []
    try:
        query = urllib.parse.quote(f'{gym_name} palestra {city}')
        url = f'https://www.google.com/maps/search/{query}'

        await page.goto(url, wait_until='networkidle', timeout=30000)
        await asyncio.sleep(3)

        # Clicca sul primo risultato
        first = await page.query_selector('[data-result-index="1"] a, .hfpxzc')
        if first:
            await first.click()
            await asyncio.sleep(3)

        # Trova tab recensioni
        reviews_tab = await page.query_selector('button[aria-label*="ecensioni"], button[data-tab-index="1"]')
        if reviews_tab:
            await reviews_tab.click()
            await asyncio.sleep(2)

        # Scroll per caricare recensioni
        for _ in range(3):
            await page.mouse.wheel(0, 2000)
            await asyncio.sleep(1.5)

        # Espandi recensioni troncate
        see_more_buttons = await page.query_selector_all('button[aria-label="Visualizza altro"]')
        for btn in see_more_buttons[:10]:
            try:
                await btn.click()
                await asyncio.sleep(0.5)
            except:
                pass

        # Estrai testo recensioni
        review_elements = await page.query_selector_all('.MyEned, .wiI7pd, [data-review-id]')
        for el in review_elements[:20]:
            try:
                text = await el.inner_text()
                if text.strip():
                    reviews_text.append(text.strip())
            except:
                pass

    except Exception as e:
        print(f"    Maps scrape ERR: {e}")

    return '\n---\n'.join(reviews_text)


# ── Main ──────────────────────────────────────────────────────────────────────

async def main():
    import urllib.parse

    # Carica palestre master (top città, max 500 per sessione)
    gyms = []
    if os.path.exists(MASTER_CSV):
        with open(MASTER_CSV, newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                city = row.get('city', '') or row.get('comune', '')
                # Normalizza "Milano" da "milano" ecc.
                if any(c.lower() in city.lower() for c in PRIORITY_CITIES) or city in PRIORITY_CITIES:
                    gyms.append(row)
    else:
        print(f"WARN: {MASTER_CSV} non trovato")
        return

    # Priorità: prima le città con più palestre, max 30 per test iniziale
    gyms = gyms[:30]
    print(f"Palestre da analizzare: {len(gyms)} (top città)")

    results = []
    use_playwright = not GOOGLE_PLACES_KEY

    async with async_playwright() as p:
        browser = None
        maps_page = None
        if use_playwright:
            print("No Google Places API key → uso Playwright su Google Maps")
            browser = await p.chromium.launch(
                headless=True,
                args=['--disable-blink-features=AutomationControlled', '--no-sandbox']
            )
            ctx = await browser.new_context(
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0.0.0 Safari/537.36',
                locale='it-IT',
            )
            maps_page = await ctx.new_page()

        processed = 0
        for i, gym in enumerate(gyms):
            name = gym.get('venue_name') or gym.get('name') or gym.get('nome', '')
            city = gym.get('city') or gym.get('comune', '')
            lat_str = gym.get('latitude') or gym.get('lat', '')
            lon_str = gym.get('longitude') or gym.get('lon', '')

            if not name:
                continue

            print(f"[{i+1}/{len(gyms)}] {name[:45]} ({city})")

            try:
                lat = float(lat_str) if lat_str else None
                lon = float(lon_str) if lon_str else None
            except:
                lat = lon = None

            # Recupera recensioni
            if GOOGLE_PLACES_KEY and lat and lon:
                reviews = await get_reviews_places_api(name, lat, lon)
                time.sleep(0.1)  # rispetta rate limit API
            elif use_playwright and maps_page:
                reviews = await get_reviews_playwright(maps_page, name, city)
                await asyncio.sleep(2)
            else:
                reviews = ''

            if not reviews:
                print(f"  → nessuna recensione")
                continue

            print(f"  → {len(reviews)} chars recensioni")

            # Estrai prezzi con LLM o regex
            prices = await extract_prices_with_llm(reviews, name)

            if prices:
                print(f"  → {len(prices)} prezzi trovati:")
                for pr in prices:
                    print(f"     €{pr['valore']} [{pr['tipo']}] conf={pr['confidenza']}")
                    results.append({
                        'gym_id': gym.get('source_venue_id') or gym.get('id') or gym.get('gym_id', ''),
                        'name': name,
                        'city': city,
                        'lat': lat or '',
                        'lon': lon or '',
                        'price_type': pr['tipo'],
                        'price_eur': pr['valore'],
                        'confidence': pr['confidenza'],
                        'text_snippet': pr.get('testo_originale', '')[:200],
                        'source': 'gmaps_reviews',
                    })
                processed += 1

            # Salva progressivo ogni 20 palestre
            if (i + 1) % 20 == 0 and results:
                _save(results)
                print(f"\n  [checkpoint] {len(results)} prezzi estratti finora\n")

        if browser:
            await browser.close()

    print(f"\n=== RISULTATI FINALI ===")
    print(f"Palestre processate: {processed}/{len(gyms)}")
    print(f"Prezzi estratti: {len(results)}")

    _save(results)


def _save(results: list[dict]):
    if not results:
        return
    fieldnames = ['gym_id', 'name', 'city', 'lat', 'lon', 'price_type', 'price_eur', 'confidence', 'text_snippet', 'source']
    with open(OUT_CSV, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(results)
    print(f"Salvato: {OUT_CSV} ({len(results)} righe)")


if __name__ == '__main__':
    import urllib.parse
    asyncio.run(main())
