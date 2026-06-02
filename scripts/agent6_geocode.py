#!/usr/bin/env python3
"""
Agent 6 — Step 3: geocoding dei venues no-price SENZA geo (latitude='').
Solo TARGET + AMBIGUOUS (i NO_TARGET non finiscono in output).

Strategia per venue (priority):
  1. address  → Nominatim (viewbox Milano, bounded)            confidence=precise
  2. website  → fetch homepage, JSON-LD geo o address→Nominatim confidence=web_addr
  3. menu_url → fetch, JSON-LD geo o address→Nominatim          confidence=web_addr
  4. fallback → Duomo 45.4642,9.1900                            confidence=fallback

bbox check OBBLIGATORIO post-Nominatim (scarta risultati fuori Milano).
Rate limit: Nominatim 1.2s, web fetch 2s, 429→sleep120+retry, 403→skip.
Resumable: rilegge agent6_geocode_fixes.csv e salta i già fatti, salva incrementale.

Output: raw_sources/agent6_geocode_fixes.csv
  venue_name, source_venue_id, old_lat, old_lng, new_lat, new_lng, confidence, method
"""
import sys, os, csv, re, json, time, html, urllib.request, urllib.parse

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from agent6_standardize import (read_csv, has, name_variants, classify_venue,
                                norm_name, clean_display_name, is_junk_name,
                                MILAN_BBOX, DUOMO, VEN, PRI, RAW)

OUT = os.path.join(RAW, "agent6_geocode_fixes.csv")
CACHE = os.path.join(RAW, ".agent6_geocode_cache.json")
UA = "SurPrice-agent6/1.0 (drink price map Milano; data standardization)"
VIEWBOX = "9.04,45.39,9.28,45.54"   # lon_min,lat_min,lon_max,lat_max

_cache = {}
if os.path.exists(CACHE):
    try: _cache = json.load(open(CACHE))
    except Exception: _cache = {}

_last_nominatim = [0.0]


def save_cache():
    json.dump(_cache, open(CACHE, "w"))


def in_bbox(lat, lon):
    return MILAN_BBOX[0] <= lat <= MILAN_BBOX[1] and MILAN_BBOX[2] <= lon <= MILAN_BBOX[3]


def http_get(url, timeout=12):
    """GET con UA; ritorna testo o None. Gestisce 429 (sleep+retry una volta) e 403 (skip)."""
    for attempt in (1, 2):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA,
                  "Accept-Language": "it-IT,it;q=0.9"})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                ct = r.headers.get_content_charset() or "utf-8"
                return r.read(2_000_000).decode(ct, "replace")
        except urllib.error.HTTPError as e:
            if e.code == 429 and attempt == 1:
                print("    429 → sleep 120s"); time.sleep(120); continue
            if e.code == 403:
                print("    403 → skip"); return None
            return None
        except Exception:
            return None
    return None


def nominatim(query):
    """Forward geocode dentro bbox Milano. Cache. Ritorna (lat,lon) o None."""
    key = "N:" + query.lower().strip()
    if key in _cache:
        v = _cache[key]
        return tuple(v) if v else None
    dt = time.time() - _last_nominatim[0]
    if dt < 1.2:
        time.sleep(1.2 - dt)
    url = ("https://nominatim.openstreetmap.org/search?"
           + urllib.parse.urlencode({"q": query, "format": "json", "limit": 1,
                                     "viewbox": VIEWBOX, "bounded": 1}))
    _last_nominatim[0] = time.time()
    txt = http_get(url, timeout=15)
    res = None
    if txt:
        try:
            arr = json.loads(txt)
            if arr:
                lat, lon = float(arr[0]["lat"]), float(arr[0]["lon"])
                if in_bbox(lat, lon):
                    res = (lat, lon)
        except Exception:
            res = None
    _cache[key] = list(res) if res else None
    save_cache()
    return res


def extract_jsonld(page):
    """Estrae (lat,lon) o address string da JSON-LD / meta nella pagina."""
    if not page:
        return None, None
    geo, addr = None, None
    for m in re.finditer(r'<script[^>]*type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
                         page, re.S | re.I):
        blob = m.group(1).strip()
        try:
            data = json.loads(blob)
        except Exception:
            continue
        stack = data if isinstance(data, list) else [data]
        while stack:
            node = stack.pop()
            if isinstance(node, dict):
                if "@graph" in node and isinstance(node["@graph"], list):
                    stack.extend(node["@graph"])
                g = node.get("geo")
                if isinstance(g, dict) and g.get("latitude") and g.get("longitude"):
                    try: geo = (float(g["latitude"]), float(g["longitude"]))
                    except Exception: pass
                a = node.get("address")
                if isinstance(a, dict):
                    parts = [a.get("streetAddress",""), a.get("postalCode",""),
                             a.get("addressLocality","")]
                    s = " ".join(p for p in parts if p).strip()
                    if s: addr = s
                elif isinstance(a, str) and a.strip():
                    addr = a.strip()
                for v in node.values():
                    if isinstance(v, (dict, list)):
                        stack.append(v)
            elif isinstance(node, list):
                stack.extend(node)
    return geo, addr


def main():
    venues = read_csv(VEN)
    prices = read_csv(PRI)
    priced = set(norm_name(p["venue_name"]) for p in prices if (p.get("venue_name") or "").strip())

    # no-geo TARGET+AMBIGUOUS (i NO_TARGET non servono: non finiscono in output)
    todo = []
    for v in venues:
        if name_variants(v) & priced:
            continue
        if has(v, "latitude") and has(v, "longitude"):
            continue
        if classify_venue(v["venue_name"], v.get("categories", "")) == "NO_TARGET":
            continue
        if is_junk_name(v["venue_name"]):
            continue
        todo.append(v)
    print(f"no-geo TARGET+AMBIG da geocodare: {len(todo)}")

    # resume
    done = {}
    if os.path.exists(OUT):
        for r in read_csv(OUT):
            done[r["source_venue_id"]] = r
        print(f"  già fatti (resume): {len(done)}")

    results = dict(done)
    n_precise = sum(1 for r in done.values() if r["confidence"] == "precise")
    n_web = sum(1 for r in done.values() if r["confidence"] == "web_addr")

    def write_all():
        cols = ["venue_name","source_venue_id","old_lat","old_lng","new_lat","new_lng",
                "confidence","method"]
        with open(OUT, "w", encoding="utf-8-sig", newline="") as f:
            w = csv.DictWriter(f, fieldnames=cols); w.writeheader()
            for r in results.values():
                w.writerow(r)

    for i, v in enumerate(todo, 1):
        cid = v["canonical_id"]
        if cid in done:
            continue
        name = clean_display_name(v["venue_name"])
        lat = lon = None
        conf = method = None

        # 1. address → Nominatim
        addr = (v.get("address") or "").strip()
        if addr:
            q = addr if "milano" in addr.lower() or "milan" in addr.lower() else addr + ", Milano"
            r = nominatim(q)
            if r:
                lat, lon = r; conf, method = "precise", "nominatim_address"

        # 2. website JSON-LD
        if lat is None and (v.get("website") or "").strip():
            page = http_get(v["website"].strip()); time.sleep(2)
            geo, jaddr = extract_jsonld(page)
            if geo and in_bbox(*geo):
                lat, lon = geo; conf, method = "web_addr", "jsonld_geo_website"
            elif jaddr:
                r = nominatim(jaddr if "milan" in jaddr.lower() else jaddr + ", Milano")
                if r: lat, lon = r; conf, method = "web_addr", "jsonld_addr_website"

        # 3. menu_url JSON-LD
        if lat is None and (v.get("menu_url") or "").strip():
            page = http_get(v["menu_url"].strip()); time.sleep(2)
            geo, jaddr = extract_jsonld(page)
            if geo and in_bbox(*geo):
                lat, lon = geo; conf, method = "web_addr", "jsonld_geo_menu"
            elif jaddr:
                r = nominatim(jaddr if "milan" in jaddr.lower() else jaddr + ", Milano")
                if r: lat, lon = r; conf, method = "web_addr", "jsonld_addr_menu"

        # 4. fallback Duomo
        if lat is None:
            lat, lon = DUOMO; conf, method = "fallback", "duomo_centro"

        results[cid] = {"venue_name": name, "source_venue_id": cid,
                        "old_lat": "", "old_lng": "",
                        "new_lat": f"{lat:.6f}", "new_lng": f"{lon:.6f}",
                        "confidence": conf, "method": method}
        if conf == "precise": n_precise += 1
        elif conf == "web_addr": n_web += 1
        write_all()
        if i % 10 == 0 or conf != "fallback":
            print(f"  [{i}/{len(todo)}] {name[:30]:30} → {conf:9} ({method})")

    write_all()
    print(f"\nDONE. precise={n_precise} web_addr={n_web} "
          f"fallback={len(results)-n_precise-n_web} / {len(results)} totali")
    print(f"  precise+web_addr = {n_precise + n_web}")


if __name__ == "__main__":
    main()
