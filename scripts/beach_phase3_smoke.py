#!/usr/bin/env python3
"""
Phase 3.0 — Smoke test Playwright su spiagge.it venue.
Carica una pagina venue, cattura tutte le XHR/fetch network calls,
prova a triggerare il booking widget.
Salva log network e HTML pre/post-interaction.
"""

import json
import time
from playwright.sync_api import sync_playwright
from datetime import datetime

VENUE_URL = "https://www.spiagge.it/stabilimenti-balneari/10389-bagno-hawaii/"
OUT_DIR = "/tmp/p3"


def main():
    network_log = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(
            viewport={"width": 1366, "height": 768},
            locale="it-IT",
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                       "AppleWebKit/605.1.15 (KHTML, like Gecko) "
                       "Version/17.0 Safari/605.1.15",
        )
        page = ctx.new_page()

        # Track all network requests
        def on_request(req):
            network_log.append({
                "type": "request",
                "method": req.method,
                "url": req.url,
                "resource_type": req.resource_type,
                "headers": dict(req.headers),
                "post_data": req.post_data,
            })

        def on_response(resp):
            try:
                body = ""
                if resp.headers.get("content-type", "").startswith("application/json"):
                    body = resp.text()[:5000]
                network_log.append({
                    "type": "response",
                    "status": resp.status,
                    "url": resp.url,
                    "content_type": resp.headers.get("content-type", ""),
                    "body_preview": body,
                })
            except Exception as e:
                pass

        page.on("request", on_request)
        page.on("response", on_response)

        print(f"Loading {VENUE_URL}...")
        page.goto(VENUE_URL, wait_until="networkidle", timeout=60000)
        print(f"Loaded. Title: {page.title()}")
        time.sleep(3)

        # Look for booking button
        buttons = page.locator("button, a").all()
        print(f"Found {len(buttons)} clickable elements")
        for i, b in enumerate(buttons[:80]):
            try:
                txt = b.inner_text(timeout=500).strip()
                if any(kw in txt.lower() for kw in ["prenota", "verifica", "check", "disponibilità", "tariff"]):
                    print(f"  [{i}] {txt[:60]} | tag: {b.evaluate('e => e.tagName')}")
            except Exception:
                continue

        # Find "Prenota" button and click
        prenota_btn = None
        for sel in [
            "button:has-text('Prenota')",
            "a:has-text('Prenota')",
            "button:has-text('PRENOTA')",
            "button:has-text('Verifica')",
            "button:has-text('Disponibilità')",
            "[data-cy*='book']",
        ]:
            loc = page.locator(sel).first
            try:
                if loc.is_visible(timeout=2000):
                    prenota_btn = loc
                    print(f"Found booking button: {sel}")
                    break
            except Exception:
                continue

        if prenota_btn:
            print("Clicking 'Vedi disponibilità' to open booking modal...")
            try:
                prenota_btn.click(timeout=5000)
            except Exception:
                pass
            time.sleep(3)

            # Look for date inputs (id="start_*" / "end_*")
            try:
                # Use JS to set the date inputs directly
                page.evaluate("""
                    (function() {
                        const startInputs = document.querySelectorAll('input[id^="start_"]');
                        const endInputs = document.querySelectorAll('input[id^="end_"]');
                        startInputs.forEach(i => { i.value = '2026-08-01'; i.dispatchEvent(new Event('input', {bubbles:true})); i.dispatchEvent(new Event('change', {bubbles:true})); });
                        endInputs.forEach(i => { i.value = '2026-08-07'; i.dispatchEvent(new Event('input', {bubbles:true})); i.dispatchEvent(new Event('change', {bubbles:true})); });
                        console.log('Dates set:', startInputs.length, endInputs.length);
                    })();
                """)
                print("Dates injected via JS (1-7 ago 2026)")
            except Exception as e:
                print(f"Date inject error: {e}")

            time.sleep(2)

            # Click "Cerca" button (submit)
            try:
                cerca = page.locator("button:has-text('Cerca')").first
                if cerca.is_visible(timeout=3000):
                    print("Clicking 'Cerca' button...")
                    # Track navigation/new pages
                    try:
                        with ctx.expect_page(timeout=10000) as new_page_info:
                            cerca.click(timeout=5000)
                        new_tab = new_page_info.value
                        print(f"NEW TAB: {new_tab.url}")
                        new_tab.on("request", on_request)
                        new_tab.on("response", on_response)
                        new_tab.wait_for_load_state("networkidle", timeout=30000)
                        time.sleep(5)
                        with open(f"{OUT_DIR}/v_booking_result.html", "w", encoding="utf-8") as f:
                            f.write(new_tab.content())
                        new_tab.screenshot(path=f"{OUT_DIR}/v_booking_result.png", full_page=True)
                    except Exception as e:
                        print(f"No new tab from Cerca: {e}")
                        time.sleep(8)
                        print(f"URL after Cerca: {page.url}")
                        page.screenshot(path=f"{OUT_DIR}/after_cerca.png", full_page=True)
            except Exception as e:
                print(f"Cerca click error: {e}")

            # Check iframes
            print(f"\nFinal frames:")
            for fr in page.frames:
                print(f"  Frame: {fr.url[:140]}")
        else:
            print("No 'Vedi disponibilità' button found")

        # Save final HTML
        with open(f"{OUT_DIR}/v_post_load.html", "w", encoding="utf-8") as f:
            f.write(page.content())
        page.screenshot(path=f"{OUT_DIR}/v_loaded.png", full_page=True)

        browser.close()

    # Save network log
    with open(f"{OUT_DIR}/network_log.json", "w", encoding="utf-8") as f:
        json.dump(network_log, f, ensure_ascii=False, indent=2, default=str)

    # Summary
    apis = [e for e in network_log if e.get("type") == "response"
            and "spiagge.it" in e.get("url", "")
            and "application/json" in e.get("content_type", "")]
    print(f"\nAPI responses (JSON, spiagge.it): {len(apis)}")
    for a in apis[:10]:
        print(f"  [{a['status']}] {a['url'][:100]}")
        if a.get("body_preview"):
            print(f"    body: {a['body_preview'][:200]}")


if __name__ == "__main__":
    main()
