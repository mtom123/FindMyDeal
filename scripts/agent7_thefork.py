#!/usr/bin/env python3
"""
Agent 7 — Step 6: TheFork discovery massiva (metadata, NO prezzi).

curl_cffi impersonate='safari17_2_ios' bypassa Datadome (403 con chrome/edge).
Ogni pagina /ristorante/...-r{id} rende un ItemList JSON-LD con 25 Restaurant
(name, PostalAddress, geo, cuisine, priceRange, rating, url). BFS: i 25 url di ogni
pagina diventano nuovi seed → crawl dei venues TheFork Milano. NESSUN prezzo (menu via JS).

Output: raw_sources/agent7_thefork_raw.csv  (confluisce in agent7_standardize.py)
Rate 2.5s/req, stop su 403 ripetuti, resumable (cache visited + venues su disco).
"""
import os, csv, re, json, time, collections
from curl_cffi import requests

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(ROOT, "raw_sources")
SEEDS_CSV = os.path.join(RAW, "agent4_thefork_venues.csv")
OUT = os.path.join(RAW, "agent7_thefork_raw.csv")
VISITED = os.path.join(RAW, ".agent7_thefork_visited.json")
MAX_PAGES = 70
RATE = 2.5
BBOX = (45.39, 45.54, 9.04, 9.28)

URL_RE = re.compile(r"https://www\.thefork\.it/ristorante/[a-z0-9\-]+-r\d+")


def fetch(url):
    try:
        r = requests.get(url, impersonate="safari17_2_ios", timeout=25)
        return r.status_code, r.text
    except Exception as e:
        return "ERR", str(e)[:80]


def parse_itemlist(html):
    """Ritorna lista di dict restaurant dall'ItemList JSON-LD."""
    out = []
    for block in re.findall(r'<script[^>]*application/ld\+json[^>]*>(.*?)</script>', html, re.S):
        try:
            d = json.loads(block)
        except Exception:
            continue
        if not (isinstance(d, dict) and d.get("@type") == "ItemList"):
            continue
        for el in d.get("itemListElement", []):
            node = el.get("item", el) if isinstance(el, dict) else None
            if not isinstance(node, dict) or "Restaurant" not in str(node.get("@type", "")):
                continue
            addr = node.get("address", {}) or {}
            geo = node.get("geo", {}) or {}
            rating = node.get("aggregateRating", {}) or {}
            out.append({
                "url": node.get("url", ""),
                "name": node.get("name", ""),
                "street": addr.get("streetAddress", ""),
                "zip": addr.get("postalCode", ""),
                "city": addr.get("addressLocality", ""),
                "lat": geo.get("latitude"), "lon": geo.get("longitude"),
                "cuisine": ", ".join(node.get("servesCuisine", []) or []),
                "price": node.get("priceRange", ""),
                "rating": rating.get("ratingValue", ""),
                "rating_n": rating.get("reviewCount", ""),
            })
    return out


def in_milan(v):
    try:
        lat, lon = float(v["lat"]), float(v["lon"])
    except (TypeError, ValueError):
        return False
    if not (BBOX[0] <= lat <= BBOX[1] and BBOX[2] <= lon <= BBOX[3]):
        return False
    return (v["zip"].startswith("20") or "milan" in (v["city"] or "").lower())


def main():
    seeds = []
    if os.path.exists(SEEDS_CSV):
        for r in csv.DictReader(open(SEEDS_CSV, encoding="utf-8-sig")):
            u = (r.get("venue_url") or "").split("/menu")[0].strip()
            m = URL_RE.match(u)
            if m:
                seeds.append(m.group(0))
    seeds = list(dict.fromkeys(seeds))
    print(f"seed URLs (agent4): {len(seeds)}")

    visited = set()
    if os.path.exists(VISITED):
        try: visited = set(json.load(open(VISITED)))
        except Exception: visited = set()
    venues = {}   # url -> venue dict
    if os.path.exists(OUT):
        for r in csv.DictReader(open(OUT, encoding="utf-8-sig")):
            venues[r["venue_url"]] = r

    CITY = "https://www.thefork.it/ristoranti/milano-c348156"   # listing città, pagina ?p=N
    pages = 0
    err403 = 0

    def save():
        cols = ["source_platform", "source_venue_id", "venue_name", "venue_url", "address",
                "city", "latitude", "longitude", "categories", "price_tier", "rating",
                "rating_count", "phone", "opening_hours", "retrieved_at"]
        with open(OUT, "w", encoding="utf-8-sig", newline="") as f:
            w = csv.DictWriter(f, fieldnames=cols); w.writeheader()
            for v in venues.values():
                w.writerow(v)
        json.dump(list(visited), open(VISITED, "w"))

    import datetime
    now = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    seen_sigs, empty_streak = set(), 0
    for p in range(1, MAX_PAGES + 1):
        url = f"{CITY}?p={p}"
        st, html = fetch(url)
        pages += 1
        if st == 403:
            err403 += 1
            print(f"  [p{p}] 403")
            if err403 >= 3:
                print("  3x 403 → stop"); break
            time.sleep(RATE); continue
        if st != 200 or not isinstance(html, str):
            time.sleep(RATE); continue
        its = parse_itemlist(html)
        sig = tuple(sorted(x["url"] for x in its))
        if not its or sig in seen_sigs:      # listing ripetuto/vuoto = fine
            print(f"  [p{p}] listing ripetuto/vuoto → stop"); break
        seen_sigs.add(sig)
        added = 0
        for it in its:
            u = it["url"]
            if not in_milan(it) or u in venues:
                continue
            rid = re.search(r"-r(\d+)", u or "")
            addr = ", ".join(x for x in [it["street"], it["zip"], it["city"]] if x)
            venues[u] = {
                "source_platform": "thefork", "source_venue_id": rid.group(1) if rid else "",
                "venue_name": it["name"], "venue_url": u, "address": addr,
                "city": it["city"] or "Milano", "latitude": f"{float(it['lat']):.6f}",
                "longitude": f"{float(it['lon']):.6f}", "categories": it["cuisine"],
                "price_tier": it["price"], "rating": it["rating"], "rating_count": it["rating_n"],
                "phone": "", "opening_hours": "", "retrieved_at": now,
            }
            added += 1
        empty_streak = empty_streak + 1 if added == 0 else 0
        print(f"  [p{p}/{MAX_PAGES}] +{added} (tot {len(venues)})")
        save()
        if empty_streak >= 3:
            print("  3 pagine senza nuovi → stop"); break
        time.sleep(RATE)

    save()
    print(f"\nDONE. pagine={pages} | venues Milano TheFork: {len(venues)}")


if __name__ == "__main__":
    main()
