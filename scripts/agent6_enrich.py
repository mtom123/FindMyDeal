#!/usr/bin/env python3
"""
Agent 6 — Step 5 (scoped): address enrichment via Nominatim REVERSE geocoding.

Riempie SOLO address mancanti, SOLO per venues con geo REALE (existing o precise/web_addr).
ESCLUDE i fallback-Duomo (reverse darebbe "Piazza Duomo" = falso indirizzo).
NON sovrascrive mai address esistenti.

Phone/opening_hours: NON fatti in massa (ROI basso: phone 8% coverage, ~700 fetch @2s,
e il popup frontend non li mostra). Documentati come TODO nel report.

Output: raw_sources/agent6_address_fixes.csv
  source_venue_id, venue_name, latitude, longitude, address, method
"""
import sys, os, csv, json, time, urllib.request, urllib.parse

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from agent6_standardize import (read_csv, has, name_variants, classify_venue,
                                norm_name, clean_display_name, is_junk_name,
                                MILAN_BBOX, VEN, PRI, RAW)
from agent6_geocode import http_get, UA  # riuso fetch + UA

OUT = os.path.join(RAW, "agent6_address_fixes.csv")
CACHE = os.path.join(RAW, ".agent6_revgeo_cache.json")
GEOCODE_FIXES = os.path.join(RAW, "agent6_geocode_fixes.csv")

_cache = {}
if os.path.exists(CACHE):
    try: _cache = json.load(open(CACHE))
    except Exception: _cache = {}
_last = [0.0]


def reverse(lat, lon):
    key = f"R:{lat:.5f},{lon:.5f}"
    if key in _cache:
        return _cache[key]
    dt = time.time() - _last[0]
    if dt < 1.2:
        time.sleep(1.2 - dt)
    url = ("https://nominatim.openstreetmap.org/reverse?"
           + urllib.parse.urlencode({"lat": lat, "lon": lon, "format": "json",
                                     "zoom": 18, "addressdetails": 1}))
    _last[0] = time.time()
    txt = http_get(url, timeout=15)
    addr = ""
    if txt:
        try:
            d = json.loads(txt)
            a = d.get("address", {})
            road = a.get("road") or a.get("pedestrian") or a.get("footway") or ""
            num = a.get("house_number", "")
            cap = a.get("postcode", "")
            city = a.get("city") or a.get("town") or a.get("municipality") or "Milano"
            street = (road + (" " + num if num else "")).strip()
            addr = ", ".join(p for p in [street, cap, city] if p).strip(", ")
        except Exception:
            addr = ""
    _cache[key] = addr
    json.dump(_cache, open(CACHE, "w"))
    return addr


def main():
    venues = read_csv(VEN)
    prices = read_csv(PRI)
    priced = set(norm_name(p["venue_name"]) for p in prices if (p.get("venue_name") or "").strip())

    # geo fixes (forward) → mappa cid -> (lat,lon,conf)
    gfix = {}
    if os.path.exists(GEOCODE_FIXES):
        for r in read_csv(GEOCODE_FIXES):
            gfix[r["source_venue_id"]] = (r["new_lat"], r["new_lng"], r["confidence"])

    def geo_conf(v):
        cid = v["canonical_id"]
        if cid in gfix:
            return gfix[cid]
        if has(v, "latitude") and has(v, "longitude"):
            return v["latitude"], v["longitude"], "existing"
        return "", "", ""

    # candidati: TARGET/AMBIG, no-junk, NO address, geo REALE (non fallback)
    todo = []
    for v in venues:
        if name_variants(v) & priced:
            continue
        if classify_venue(v["venue_name"], v.get("categories", "")) == "NO_TARGET":
            continue
        if is_junk_name(v["venue_name"]):
            continue
        if has(v, "address"):
            continue
        la, lo, cf = geo_conf(v)
        if not la or cf == "fallback":
            continue
        try:
            laf, lof = float(la), float(lo)
        except ValueError:
            continue
        if not (MILAN_BBOX[0] <= laf <= MILAN_BBOX[1] and MILAN_BBOX[2] <= lof <= MILAN_BBOX[3]):
            continue
        todo.append((v, laf, lof))
    print(f"address-enrichment candidati (geo reale, no address): {len(todo)}")

    done = {}
    if os.path.exists(OUT):
        for r in read_csv(OUT):
            done[r["source_venue_id"]] = r
    results = dict(done)

    def write_all():
        cols = ["source_venue_id", "venue_name", "latitude", "longitude", "address", "method"]
        with open(OUT, "w", encoding="utf-8-sig", newline="") as f:
            w = csv.DictWriter(f, fieldnames=cols); w.writeheader()
            for r in results.values():
                w.writerow(r)

    n_ok = sum(1 for r in done.values() if r["address"])
    for i, (v, la, lo) in enumerate(todo, 1):
        cid = v["canonical_id"]
        if cid in done:
            continue
        addr = reverse(la, lo)
        results[cid] = {"source_venue_id": cid, "venue_name": clean_display_name(v["venue_name"]),
                        "latitude": f"{la:.6f}", "longitude": f"{lo:.6f}",
                        "address": addr, "method": "nominatim_reverse" if addr else "no_result"}
        if addr:
            n_ok += 1
        write_all()
        if i % 20 == 0:
            print(f"  [{i}/{len(todo)}] filled={n_ok}")
    write_all()
    print(f"DONE. address riempiti: {n_ok}/{len(results)}")


if __name__ == "__main__":
    main()
