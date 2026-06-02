"""
gym_s1_chains.py — Prezzi palestre a catena italiane

Target chain (con URL diretto alla pagina abbonamenti):
  - McFit           → prezzi pubblici, piano mensile
  - FitActive       → prezzi per club sul sito
  - Anytime Fitness → prezzi per club
  - Virgin Active   → prezzi per club
  - Fitness First   → prezzi per club

Strategia: Playwright headless, intercetta XHR/JSON,
cerca window.__INITIAL_STATE__ / __NEXT_DATA__ / ld+json.

Output: agent_ceo_gym/gym_chain_prices.csv
"""

import asyncio, csv, json, os, re, sys
from playwright.async_api import async_playwright

# Fix Windows terminal encoding
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

OUT_DIR = os.path.dirname(__file__)
OUT_CSV = os.path.join(OUT_DIR, 'gym_chain_prices.csv')

CHAINS = [
    {
        'chain': 'McFit',
        'country_url': 'https://www.mcfit.com/it/',
        'price_urls': [
            'https://www.mcfit.com/it/abbonamento/',
            'https://www.mcfit.com/it/prezzi/',
            'https://www.mcfit.com/it/palestre/',
        ],
        'keywords': ['prezzo', 'euro', '€', 'mese', 'abbonamento', 'membership'],
    },
    {
        'chain': 'FitActive',
        'country_url': 'https://www.fitactive.it/',
        'price_urls': [
            'https://www.fitactive.it/',
            'https://www.fitactive.it/Home/Iscriviti',
            'https://www.fitactive.it/palestre/',
        ],
        'keywords': ['prezzo', 'euro', '€', 'mese', 'mensile', '19', '29'],
    },
    {
        'chain': 'Anytime Fitness',
        'country_url': 'https://www.anytimefitness.it/',
        'price_urls': [
            'https://www.anytimefitness.it/',
            'https://www.anytimefitness.it/palestre/',
            'https://www.anytimefitness.it/try-us-free/',
        ],
        'keywords': ['prezzo', 'euro', '€', 'mese', 'club'],
    },
    {
        'chain': 'Virgin Active',
        'country_url': 'https://www.virginactive.it/',
        'price_urls': [
            'https://www.virginactive.it/',
            'https://www.virginactive.it/assistenza',
            'https://shop.virginactive.it/account/register',
        ],
        'keywords': ['prezzo', 'euro', '€', 'mese', 'club', 'abbonament'],
    },
    {
        'chain': 'Gympass',
        'country_url': 'https://gympass.com/it-it',
        'price_urls': [
            'https://gympass.com/it-it/plans-pricing/',
            'https://gympass.com/it-it',
        ],
        'keywords': ['prezzo', 'euro', '€', 'mese', 'piano', 'plan'],
    },
    {
        'chain': 'Basic-Fit',
        'country_url': 'https://www.basic-fit.com/it-it',
        'price_urls': [
            'https://www.basic-fit.com/it-it/abbonamento',
            'https://www.basic-fit.com/it-it/membership',
            'https://www.basic-fit.com/it-it/',
        ],
        'keywords': ['prezzo', 'euro', '€', 'mese', 'mensile', 'membership'],
    },
    {
        'chain': 'Klab',
        'country_url': 'https://www.klabfitness.it/',
        'price_urls': [
            'https://www.klabfitness.it/',
            'https://www.klabfitness.it/abbonamenti',
            'https://www.klabfitness.it/prezzi',
        ],
        'keywords': ['prezzo', 'euro', '€', 'mese', 'mensile'],
    },
]


def extract_prices_from_text(text: str) -> list[dict]:
    """Estrae tutti i prezzi trovati con contesto."""
    results = []
    patterns = [
        r'(?P<pretext>[^\n]{0,60})€\s*(?P<price>\d+[\.,]\d+)(?P<posttext>[^\n]{0,60})',
        r'(?P<pretext>[^\n]{0,60})(?P<price>\d+[\.,]\d+)\s*€(?P<posttext>[^\n]{0,60})',
        r'(?P<pretext>[^\n]{0,60})(?P<price>\d+)\s*euro(?P<posttext>[^\n]{0,60})',
    ]
    seen = set()
    for p in patterns:
        for m in re.finditer(p, text, re.IGNORECASE):
            price_str = m.group('price').replace(',', '.')
            try:
                price_val = float(price_str)
                if price_val < 1 or price_val > 1000:
                    continue
                key = round(price_val, 2)
                if key not in seen:
                    seen.add(key)
                    ctx = (m.group('pretext') + ' €' + m.group('price') + m.group('posttext')).strip()
                    results.append({'price': key, 'context': ctx[:200]})
            except:
                pass
    return sorted(results, key=lambda x: x['price'])


def infer_price_type(context: str) -> str:
    """Inferisce il tipo di prezzo dal contesto."""
    ctx = context.lower()
    if any(k in ctx for k in ['mensil', 'mese', '/mese', 'month']):
        return 'mensile'
    if any(k in ctx for k in ['annua', 'anno', 'year', 'annual']):
        return 'annuale'
    if any(k in ctx for k in ['giorn', 'day pass', 'ingresso singol', 'giornali']):
        return 'day_pass'
    if any(k in ctx for k in ['trimest', '3 mesi']):
        return 'trimestrale'
    if any(k in ctx for k in ['iscriz', 'attivaz', 'starter']):
        return 'iscrizione'
    return 'unknown'


async def scrape_chain(browser, chain_info: dict) -> list[dict]:
    """Scrape prezzi per una catena. Ritorna lista di record."""
    chain_name = chain_info['chain']
    results = []
    captured_json = []

    ctx = await browser.new_context(
        user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
        locale='it-IT',
        viewport={'width': 1280, 'height': 900},
    )
    page = await ctx.new_page()

    async def handle_response(response):
        if response.status != 200:
            return
        ct = response.headers.get('content-type', '')
        if 'json' not in ct.lower():
            return
        try:
            body = await response.body()
            txt = body.decode('utf-8', errors='replace')
            if any(k in txt.lower() for k in chain_info['keywords']):
                captured_json.append({'url': response.url, 'body': txt})
        except:
            pass

    page.on('response', handle_response)

    for url in chain_info['price_urls']:
        try:
            print(f"  [{chain_name}] {url}")
            r = await page.goto(url, wait_until='networkidle', timeout=25000)
            if not r or r.status >= 400:
                print(f"    → {r.status if r else 'timeout'}, skip")
                continue
            await asyncio.sleep(3)

            content = await page.content()

            # Rimuovi tag HTML per analisi testo puro
            text_content = re.sub(r'<[^>]+>', ' ', content)
            text_content = re.sub(r'\s+', ' ', text_content)

            # Cerca __NEXT_DATA__
            next_data = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', content, re.DOTALL)
            if next_data:
                try:
                    nd = json.loads(next_data.group(1))
                    nd_text = json.dumps(nd)
                    prices = extract_prices_from_text(nd_text)
                    for p in prices:
                        results.append({
                            'chain': chain_name,
                            'url': url,
                            'price': p['price'],
                            'price_type': infer_price_type(p['context']),
                            'context': p['context'][:200],
                            'source': 'next_data',
                        })
                    if prices:
                        print(f"    → __NEXT_DATA__: {len(prices)} prezzi")
                except:
                    pass

            # Cerca window.__INITIAL_STATE__
            init_state = re.search(r'window\.__(?:INITIAL_STATE|STATE|DATA)__\s*=\s*(\{.*?\});', content, re.DOTALL)
            if init_state:
                try:
                    state = json.loads(init_state.group(1))
                    state_text = json.dumps(state)
                    prices = extract_prices_from_text(state_text)
                    for p in prices:
                        results.append({
                            'chain': chain_name,
                            'url': url,
                            'price': p['price'],
                            'price_type': infer_price_type(p['context']),
                            'context': p['context'][:200],
                            'source': 'initial_state',
                        })
                    if prices:
                        print(f"    → window.__STATE__: {len(prices)} prezzi")
                except:
                    pass

            # Analisi testo HTML diretto
            prices = extract_prices_from_text(text_content)
            gym_relevant = [p for p in prices if any(
                k in p['context'].lower()
                for k in ['mensil', 'mese', 'abbonament', 'iscriz', 'ingress', 'day', 'annual']
            )]
            for p in gym_relevant:
                results.append({
                    'chain': chain_name,
                    'url': url,
                    'price': p['price'],
                    'price_type': infer_price_type(p['context']),
                    'context': p['context'][:200],
                    'source': 'html_text',
                })
            if gym_relevant:
                print(f"    → HTML text: {len(gym_relevant)} prezzi rilevanti")

            # Prova a cliccare su "Abbonati"/"Iscriviti"/"Prezzi"
            try:
                btn = await page.query_selector(
                    'a:has-text("Abbonati"), a:has-text("Iscriviti"), button:has-text("Abbonati"), '
                    'a:has-text("Prezzi"), a:has-text("Abbonamento")'
                )
                if btn:
                    href = await btn.get_attribute('href')
                    text = await btn.inner_text()
                    print(f"    → Trovato pulsante: '{text.strip()[:30]}' → {href}")
                    if href and href.startswith('http'):
                        await page.goto(href, wait_until='networkidle', timeout=20000)
                        await asyncio.sleep(3)
                        content2 = await page.content()
                        text2 = re.sub(r'<[^>]+>', ' ', content2)
                        prices2 = extract_prices_from_text(text2)
                        for p in prices2:
                            results.append({
                                'chain': chain_name,
                                'url': href,
                                'price': p['price'],
                                'price_type': infer_price_type(p['context']),
                                'context': p['context'][:200],
                                'source': 'click_through',
                            })
                        if prices2:
                            print(f"    → Click-through: {len(prices2)} prezzi")
            except:
                pass

        except Exception as e:
            print(f"    ERR: {str(e)[:100]}")

    # Analisi JSON catturati
    for jd in captured_json:
        prices = extract_prices_from_text(jd['body'])
        for p in prices:
            results.append({
                'chain': chain_name,
                'url': jd['url'],
                'price': p['price'],
                'price_type': infer_price_type(p['context']),
                'context': p['context'][:200],
                'source': 'xhr_json',
            })
        if prices:
            print(f"  [{chain_name}] XHR JSON {jd['url'][:60]}: {len(prices)} prezzi")

    await ctx.close()

    # Deduplication: tieni solo prezzi unici per catena
    seen = set()
    unique = []
    for r in results:
        key = (r['chain'], r['price'], r['price_type'])
        if key not in seen:
            seen.add(key)
            unique.append(r)

    return unique


async def main():
    print("=== GYM CHAIN PRICING SCRAPER ===\n")

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=['--disable-blink-features=AutomationControlled', '--no-sandbox']
        )

        all_results = []
        for chain in CHAINS:
            print(f"\n{'='*50}")
            print(f"Chain: {chain['chain']}")
            results = await scrape_chain(browser, chain)
            all_results.extend(results)
            print(f"  >> Trovati {len(results)} prezzi per {chain['chain']}")
            for r in results[:10]:
                print(f"     {r['price']:.2f}EUR [{r['price_type']}] {r['context'][:80]}")

        await browser.close()

    print(f"\n=== TOTALE: {len(all_results)} prezzi trovati ===")

    if all_results:
        fieldnames = ['chain', 'url', 'price', 'price_type', 'context', 'source']
        with open(OUT_CSV, 'w', newline='', encoding='utf-8') as f:
            w = csv.DictWriter(f, fieldnames=fieldnames)
            w.writeheader()
            w.writerows(all_results)
        print(f"Salvato: {OUT_CSV}")

        # Riepilogo per catena
        print("\n=== RIEPILOGO PER CATENA ===")
        by_chain = {}
        for r in all_results:
            by_chain.setdefault(r['chain'], []).append(r)
        for chain, items in by_chain.items():
            mensile = [i for i in items if i['price_type'] == 'mensile']
            if mensile:
                avg = sum(i['price'] for i in mensile) / len(mensile)
                mn = min(i['price'] for i in mensile)
                mx = max(i['price'] for i in mensile)
                print(f"  {chain}: mensile min={mn}€ max={mx}€ avg={avg:.2f}€")
            else:
                print(f"  {chain}: {len(items)} prezzi, nessuno mensile")
    else:
        print("Nessun prezzo trovato. Controlla i siti manualmente.")

if __name__ == '__main__':
    asyncio.run(main())
