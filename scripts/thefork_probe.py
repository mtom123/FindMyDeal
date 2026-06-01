#!/usr/bin/env python3
"""
STEP 1 (PROMPT_PIETRO_NOTTE) — TheFork via Playwright stealth.
Sonda BOUNDED: verifica se Datadome blocca un browser stealth. Se passa, prova a
estrarre qualche venue dalla ricerca Milano. Se captcha -> screenshot + stop (no bypass).
"""
import sys, time
from playwright.sync_api import sync_playwright

# stealth: supporta sia API vecchia (stealth_sync) che nuova (Stealth)
def apply_stealth(page, context):
    try:
        from playwright_stealth import stealth_sync
        stealth_sync(page); return "stealth_sync"
    except Exception:
        pass
    try:
        from playwright_stealth import Stealth
        Stealth().apply_stealth_sync(context); return "Stealth.apply"
    except Exception as e:
        return f"stealth non applicato ({type(e).__name__})"

URLS = [
    "https://www.thefork.it/",
    "https://www.thefork.it/cerca/milano-415144",
    "https://www.thefork.com/search/?cityId=415144",
]


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=[
            "--disable-blink-features=AutomationControlled",
            "--no-sandbox",
        ])
        ctx = browser.new_context(
            user_agent=("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"),
            viewport={"width": 1920, "height": 1080},
            locale="it-IT", timezone_id="Europe/Rome",
        )
        page = ctx.new_page()
        s = apply_stealth(page, ctx)
        print(f"stealth: {s}")
        blocked = 0
        for u in URLS:
            try:
                resp = page.goto(u, timeout=30000, wait_until="domcontentloaded")
                time.sleep(4)
                status = resp.status if resp else "?"
                html = page.content().lower()
                title = page.title()
                dd = any(k in html for k in ("datadome", "geo.captcha", "captcha-delivery",
                                             "verifica che sei un essere umano", "are you human"))
                print(f"\n{u}\n  HTTP {status} | title={title!r} | len={len(html)} | DATADOME/CAPTCHA={dd}")
                if dd or status == 403:
                    blocked += 1
                    page.screenshot(path=f"thefork_block_{blocked}.png")
                    print(f"  -> bloccato, screenshot thefork_block_{blocked}.png")
                else:
                    # pagina pulita: conta link ristorante
                    links = page.eval_on_selector_all(
                        "a[href*='/ristorante/'], a[href*='/restaurant/']",
                        "els => els.map(e => e.getAttribute('href')).slice(0,10)")
                    print(f"  -> PULITA! link ristorante trovati: {len(links)}")
                    for l in links[:5]:
                        print("     ", l)
            except Exception as e:
                print(f"  ERR {type(e).__name__}: {str(e)[:80]}")
            time.sleep(3)
        browser.close()
        print(f"\nESITO: {blocked}/{len(URLS)} URL bloccati da Datadome.")
        if blocked == len(URLS):
            print("TheFork completamente bloccato anche con browser stealth headless. Stop (come da prompt).")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(1)
