"""
gym_s1_fitprime_prices.py — FitPrime pricing extractor

Step 1: Scrape FitPrime subscription plans (€/mese)
Step 2: Per ogni palestra nel master, visita la booking page e cattura il day-pass in crediti
Step 3: Calcola €/credito e salva gym_fitprime_prices.csv

Output: agent_ceo_gym/gym_fitprime_prices.csv
"""

import asyncio, csv, json, os, re, time
from playwright.async_api import async_playwright

OUT_DIR = os.path.dirname(__file__)
MASTER_CSV = os.path.join(OUT_DIR, 'gym_master_italia.csv')
OUT_CSV = os.path.join(OUT_DIR, 'gym_fitprime_prices.csv')
PLANS_JSON = os.path.join(OUT_DIR, 'fitprime_plans.json')

# ─── helpers ───────────────────────────────────────────────────────────────────

def extract_euro(text: str) -> float | None:
    """Estrae primo valore numerico €/mese da una stringa."""
    patterns = [
        r'€\s*(\d+[\.,]\d+)',
        r'(\d+[\.,]\d+)\s*€',
        r'(\d+[\.,]\d+)\s*euro',
        r'(\d+)\s*€',
    ]
    for p in patterns:
        m = re.search(p, text, re.IGNORECASE)
        if m:
            return float(m.group(1).replace(',', '.'))
    return None

def extract_credits(text: str) -> int | None:
    """Estrae numero di crediti da testo booking."""
    m = re.search(r'(\d+)\s*credit', text, re.IGNORECASE)
    if m:
        return int(m.group(1))
    return None


# ─── Step 1: piani abbonamento FitPrime ────────────────────────────────────────

async def scrape_fitprime_plans(page) -> dict:
    """Visita la pricing page e ritorna i piani con €/mese e crediti inclusi."""
    plans = {}

    plan_urls = [
        'https://www.fitprime.com/it/prezzi',
        'https://www.fitprime.com/it/abbonamenti',
        'https://www.fitprime.com/it/piani',
        'https://www.fitprime.com/prezzi',
    ]

    pricing_data = []

    async def capture_json(response):
        ct = response.headers.get('content-type', '')
        if response.status != 200:
            return
        if 'json' not in ct.lower():
            return
        try:
            body = await response.body()
            txt = body.decode('utf-8', errors='replace')
            if any(k in txt.lower() for k in ['price', 'prezzo', 'euro', 'plan', 'piano', 'credit']):
                pricing_data.append({'url': response.url, 'body': txt})
        except:
            pass

    page.on('response', capture_json)

    for url in plan_urls:
        try:
            print(f"  Visiting {url}...")
            await page.goto(url, wait_until='networkidle', timeout=30000)
            await asyncio.sleep(4)
            title = await page.title()
            print(f"    title: {title[:60]}")
            content = await page.content()

            # Cerca tabelle di prezzi nell'HTML
            price_matches = re.findall(r'€\s*\d+[\.,]?\d*', content)
            credit_matches = re.findall(r'\d+\s*credit(?:i)?', content, re.IGNORECASE)
            print(f"    Trovati: {len(price_matches)} prezzi, {len(credit_matches)} crediti")

            # Prova a estrarre JSON da script tags
            script_data = re.findall(r'<script[^>]*>\s*(\{.*?\})\s*</script>', content, re.DOTALL)
            for sd in script_data[:5]:
                try:
                    obj = json.loads(sd)
                    if any(k in str(obj).lower() for k in ['price', 'plan', 'credit']):
                        pricing_data.append({'url': url + '#script', 'body': json.dumps(obj)})
                except:
                    pass

            # Cerca __NEXT_DATA__ o window.__INITIAL_STATE__
            next_data = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', content, re.DOTALL)
            if next_data:
                try:
                    nd = json.loads(next_data.group(1))
                    pricing_data.append({'url': url + '#next_data', 'body': json.dumps(nd)})
                    print(f"    __NEXT_DATA__ trovato: {len(next_data.group(1))} chars")
                except:
                    pass

        except Exception as e:
            print(f"    ERR: {e}")

    # Salva tutti i pricing_data trovati
    for i, pd in enumerate(pricing_data[:20]):
        fname = os.path.join(OUT_DIR, f'fitprime_dump/plan_data_{i}.json')
        os.makedirs(os.path.dirname(fname), exist_ok=True)
        with open(fname, 'w', encoding='utf-8') as f:
            f.write(pd['body'][:500000])
        print(f"  Saved: plan_data_{i}.json from {pd['url'][:80]}")

    # Tenta estrazione piani strutturata dal contenuto
    # (pattern comune: piano starter/base/premium + €/mese)
    all_text = ' '.join(d['body'] for d in pricing_data)
    plan_patterns = [
        (r'(?:starter|base|light)[^\d€]*(\d+[\.,]\d+)\s*€', 'starter'),
        (r'(?:premium|pro|plus)[^\d€]*(\d+[\.,]\d+)\s*€', 'premium'),
        (r'(?:gold|vip|elite)[^\d€]*(\d+[\.,]\d+)\s*€', 'gold'),
        (r'(\d+[\.,]\d+)\s*€\s*/?\s*mese', 'generic'),
    ]
    for pattern, plan_name in plan_patterns:
        m = re.search(pattern, all_text, re.IGNORECASE)
        if m:
            plans[plan_name] = float(m.group(1).replace(',', '.'))

    print(f"\n  Piani trovati: {plans}")
    return plans


# ─── Step 2: day pass per palestra ─────────────────────────────────────────────

async def scrape_gym_daypass(page, gym_row: dict) -> dict | None:
    """
    Data una palestra FitPrime, vai alla sua pagina e cattura il day pass in crediti.
    Ritorna {'gym_id':..., 'day_pass_credits':N, 'source':'fitprime'} oppure None.
    """
    # FitPrime URL pattern: /it/palestre/{city}/{slug}
    fitprime_url = gym_row.get('fitprime_url') or gym_row.get('url')
    if not fitprime_url or 'fitprime' not in str(fitprime_url):
        return None

    day_pass_data = []

    async def capture(response):
        if response.status != 200:
            return
        ct = response.headers.get('content-type', '')
        if 'json' not in ct.lower():
            return
        try:
            body = await response.body()
            txt = body.decode('utf-8', errors='replace')
            if any(k in txt.lower() for k in ['credit', 'price', 'prezzo', 'pass']):
                day_pass_data.append({'url': response.url, 'body': txt})
        except:
            pass

    page.on('response', capture)

    try:
        await page.goto(fitprime_url, wait_until='networkidle', timeout=30000)
        await asyncio.sleep(3)
        content = await page.content()

        # Cerca pulsante "Prenota" o "Accedi"
        book_btn = await page.query_selector('button:has-text("Prenota"), a:has-text("Prenota"), button:has-text("Book")')
        if book_btn:
            await book_btn.click()
            await asyncio.sleep(3)
            content = await page.content()

        # Cerca crediti nel contenuto
        credits = extract_credits(content)
        if credits:
            return {
                'gym_id': gym_row.get('id') or gym_row.get('gym_id'),
                'name': gym_row.get('name'),
                'day_pass_credits': credits,
                'source': 'fitprime_page',
            }

        # Cerca in JSON catturati
        for d in day_pass_data:
            credits = extract_credits(d['body'])
            if credits:
                return {
                    'gym_id': gym_row.get('id') or gym_row.get('gym_id'),
                    'name': gym_row.get('name'),
                    'day_pass_credits': credits,
                    'source': 'fitprime_api',
                }

    except Exception as e:
        print(f"    ERR {gym_row.get('name','?')}: {e}")

    page.remove_listener('response', capture)
    return None


# ─── Step 3: main ───────────────────────────────────────────────────────────────

async def main():
    # Leggi master CSV per avere le palestre FitPrime
    fitprime_gyms = []
    if os.path.exists(MASTER_CSV):
        with open(MASTER_CSV, newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if 'fitprime' in str(row.get('source', '')).lower() or 'fitprime' in str(row.get('url', '')).lower():
                    fitprime_gyms.append(row)
        print(f"Palestre FitPrime nel master: {len(fitprime_gyms)}")
    else:
        print(f"WARN: {MASTER_CSV} non trovato, skip day-pass scraping")

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False,  # visibile per debug, metti True in produzione
            args=['--disable-blink-features=AutomationControlled', '--no-sandbox']
        )
        ctx = await browser.new_context(
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
            locale='it-IT',
            viewport={'width': 1920, 'height': 1080},
        )
        page = await ctx.new_page()

        # ── Step 1: piani abbonamento ──
        print("\n=== STEP 1: Piani abbonamento FitPrime ===")
        plans = await scrape_fitprime_plans(page)
        with open(PLANS_JSON, 'w', encoding='utf-8') as f:
            json.dump(plans, f, ensure_ascii=False, indent=2)
        print(f"Piani salvati in {PLANS_JSON}")

        # Calcola €/credito se abbiamo i piani
        # FitPrime standard: piano da X€ include Y crediti/mese
        # Assumiamo piano base come riferimento se non estratto
        euro_per_credit = None
        if plans:
            # Heuristic: il piano più economico / crediti medi
            min_price = min(plans.values())
            # Tipicamente 1 credito FitPrime = 1-2€
            print(f"  Prezzo minimo piano: €{min_price}")

        # ── Step 2: day pass per palestre FitPrime ──
        results = []
        if fitprime_gyms:
            print(f"\n=== STEP 2: Day pass per {min(len(fitprime_gyms), 50)} palestre FitPrime ===")
            for i, gym in enumerate(fitprime_gyms[:50]):
                print(f"  [{i+1}/{min(len(fitprime_gyms),50)}] {gym.get('name','?')[:50]}")
                result = await scrape_gym_daypass(page, gym)
                if result:
                    print(f"    ✓ day pass: {result['day_pass_credits']} crediti")
                    results.append(result)
                await asyncio.sleep(2)

        # ── Step 3: Salva output ──
        print(f"\n=== RISULTATI ===")
        print(f"  Piani: {plans}")
        print(f"  Palestre con day pass: {len(results)}")

        if results:
            fieldnames = ['gym_id', 'name', 'day_pass_credits', 'source', 'euro_per_credit', 'day_pass_euro']
            with open(OUT_CSV, 'w', newline='', encoding='utf-8') as f:
                w = csv.DictWriter(f, fieldnames=fieldnames)
                w.writeheader()
                for r in results:
                    if euro_per_credit:
                        r['euro_per_credit'] = euro_per_credit
                        r['day_pass_euro'] = round(r['day_pass_credits'] * euro_per_credit, 2)
                    w.writerow(r)
            print(f"  Salvato: {OUT_CSV}")

        await browser.close()

if __name__ == '__main__':
    asyncio.run(main())
