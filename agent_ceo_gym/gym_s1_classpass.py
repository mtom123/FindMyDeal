"""
gym_s1_classpass.py — ClassPass Italia: prezzi per gym

ClassPass mostra i crediti necessari per ogni visita su pagine pubbliche.
Strategia:
  1. Cerca palestre italiane su ClassPass (prima senza login)
  2. Per ogni palestra, cattura i crediti del day pass
  3. Calcola €/visita in base ai piani pubblici ClassPass

Se Cloudflare blocca headless: usa modalità headed + stealth.

Output: agent_ceo_gym/gym_classpass_prices.csv
"""

import asyncio, csv, json, os, re
from playwright.async_api import async_playwright
from playwright_stealth import stealth_async  # pip install playwright-stealth

OUT_DIR = os.path.dirname(__file__)
OUT_CSV = os.path.join(OUT_DIR, 'gym_classpass_prices.csv')

# Città italiane da cercare
CITIES = ['Milano', 'Roma', 'Torino', 'Napoli', 'Bologna', 'Firenze', 'Venezia']

# ClassPass URL patterns
BASE_URL = 'https://classpass.com'

async def scrape_classpass_city(page, city: str) -> list[dict]:
    """Cerca palestre per una città e cattura prezzi."""
    results = []
    api_data = []

    async def capture(response):
        if response.status != 200:
            return
        ct = response.headers.get('content-type', '')
        url = response.url
        if 'json' not in ct.lower() and 'graphql' not in url.lower():
            return
        try:
            body = await response.body()
            txt = body.decode('utf-8', errors='replace')
            if any(k in txt.lower() for k in ['credit', 'venue', 'studio', 'gym', 'fitness']):
                api_data.append({'url': url, 'body': txt})
        except:
            pass

    page.on('response', capture)

    try:
        # URL ClassPass per città italiana
        city_lower = city.lower().replace(' ', '-')
        search_urls = [
            f'https://classpass.com/search/{city_lower}--italy/gyms',
            f'https://classpass.com/search/{city_lower}--italy',
            f'https://classpass.com/it/search/{city_lower}--italy/gyms',
        ]

        for url in search_urls:
            try:
                print(f"  [{city}] {url}")
                resp = await page.goto(url, wait_until='networkidle', timeout=30000)
                if not resp or resp.status >= 400:
                    print(f"    -> {resp.status if resp else 'timeout'}")
                    continue

                await asyncio.sleep(5)
                content = await page.content()

                # Check Cloudflare block
                if 'cloudflare' in content.lower() or 'challenge' in content.lower():
                    print(f"    -> Cloudflare blocked!")
                    break

                title = await page.title()
                print(f"    -> title: {title[:60]}")

                # Analisi API responses
                for d in api_data:
                    try:
                        data = json.loads(d['body'])
                        venues = (
                            data.get('venues') or
                            data.get('results') or
                            data.get('studios') or
                            (data.get('data', {}).get('venues') if isinstance(data.get('data'), dict) else None) or
                            []
                        )
                        for venue in venues[:50]:
                            name = venue.get('name') or venue.get('title', '')
                            credits = (
                                venue.get('min_credits') or
                                venue.get('credits') or
                                (venue.get('pricing', {}).get('credits') if isinstance(venue.get('pricing'), dict) else None)
                            )
                            lat = venue.get('latitude') or venue.get('lat')
                            lon = venue.get('longitude') or venue.get('lon')

                            if name and credits:
                                results.append({
                                    'name': name,
                                    'city': city,
                                    'classpass_credits': credits,
                                    'lat': lat or '',
                                    'lon': lon or '',
                                    'source': 'classpass_api',
                                    'url': d['url'][:100],
                                })
                    except:
                        pass

                if results:
                    print(f"    -> Trovati {len(results)} venues con crediti")
                    break

                # Scroll per caricare più risultati
                for _ in range(3):
                    await page.mouse.wheel(0, 2000)
                    await asyncio.sleep(1.5)

            except Exception as e:
                print(f"    -> ERR: {str(e)[:80]}")

    finally:
        page.remove_listener('response', capture)

    return results


async def get_classpass_plan_prices(page) -> dict:
    """Ottieni i prezzi dei piani ClassPass per calcolare €/credito."""
    plans = {}
    try:
        resp = await page.goto('https://classpass.com/plans', wait_until='networkidle', timeout=30000)
        await asyncio.sleep(4)
        content = await page.content()

        if 'cloudflare' not in content.lower():
            text = re.sub(r'<[^>]+>', ' ', content)
            # Pattern: X crediti per Y€/mese
            patterns = [
                r'(\d+)\s*credit[si]?\s*(?:per|a|for)?\s*(\d+[\.,]\d*)\s*€',
                r'(\d+[\.,]\d*)\s*€[^\d]{0,20}(\d+)\s*credit',
            ]
            for p in patterns:
                for m in re.finditer(p, text, re.IGNORECASE):
                    try:
                        a, b = float(m.group(1).replace(',', '.')), float(m.group(2).replace(',', '.'))
                        if a > b:  # crediti > euro
                            plans[f'{int(a)}_credits'] = b
                        else:  # euro < crediti
                            plans[f'{int(b)}_credits'] = a
                    except:
                        pass

            print(f"  ClassPass piani: {plans}")
    except Exception as e:
        print(f"  Plans ERR: {e}")

    return plans


async def main():
    print("=== CLASSPASS ITALIA PRICE SCRAPER ===\n")

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False,  # headed per evitare Cloudflare
            args=[
                '--disable-blink-features=AutomationControlled',
                '--no-sandbox',
                '--window-size=1280,900',
            ]
        )
        ctx = await browser.new_context(
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
            locale='it-IT',
            viewport={'width': 1280, 'height': 900},
        )
        page = await ctx.new_page()

        # Stealth mode
        try:
            await stealth_async(page)
        except:
            print("WARN: playwright-stealth non installato, continuo senza")

        # Prima visita la homepage per cookie/session
        print("Init: homepage ClassPass...")
        try:
            await page.goto('https://classpass.com/it', wait_until='networkidle', timeout=30000)
            await asyncio.sleep(3)
        except:
            await page.goto('https://classpass.com', wait_until='networkidle', timeout=30000)
            await asyncio.sleep(3)

        # Prezzi piani
        print("\nStep 1: Prezzi piani ClassPass")
        plans = await get_classpass_plan_prices(page)

        # Scraping per città
        all_results = []
        for city in CITIES:
            print(f"\nStep 2: {city}")
            results = await scrape_classpass_city(page, city)
            all_results.extend(results)
            print(f"  Totale per {city}: {len(results)} venues")
            await asyncio.sleep(3)

        await browser.close()

    print(f"\n=== TOTALE: {len(all_results)} venues con prezzi ClassPass ===")

    # Calcola €/visita se abbiamo i piani
    euro_per_credit = None
    if plans:
        # Heuristic: piano più economico
        cheapest_eur = min(plans.values())
        cheapest_credits = int(min(plans.keys(), key=lambda k: plans[k]).split('_')[0])
        euro_per_credit = cheapest_eur / cheapest_credits
        print(f"  €/credito (piano base): {euro_per_credit:.4f}")

    if all_results:
        for r in all_results:
            if euro_per_credit and r.get('classpass_credits'):
                r['visit_price_eur'] = round(float(r['classpass_credits']) * euro_per_credit, 2)

        fieldnames = ['name', 'city', 'classpass_credits', 'visit_price_eur', 'lat', 'lon', 'source', 'url']
        with open(OUT_CSV, 'w', newline='', encoding='utf-8') as f:
            w = csv.DictWriter(f, fieldnames=fieldnames)
            w.writeheader()
            w.writerows(all_results)
        print(f"Salvato: {OUT_CSV}")
    else:
        print("Nessun dato trovato (probabile Cloudflare block)")
        print("Alternativa: crea account ClassPass manualmente, salva cookies,")
        print("poi esegui con CLASSPASS_COOKIES=path/to/cookies.json")

if __name__ == '__main__':
    import sys
    if sys.platform == 'win32':
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    asyncio.run(main())
