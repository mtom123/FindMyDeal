#!/usr/bin/env python3
"""
Agent 7 — Step 7.1: re-query OSM Overpass per Milano bar/pub/cafe/nightclub/biergarten
includendo il tag `opening_hours` (+ website/phone/address) che il file esistente non ha.

Output: raw_sources/agent7_osm_enriched.csv
  name, lat, lon, amenity, cuisine, website, phone, opening_hours, address
"""
import os, csv, json, urllib.request, urllib.parse, time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "raw_sources", "agent7_osm_enriched.csv")
ENDPOINTS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
]
QUERY = """
[out:json][timeout:180];
area["name"="Milano"]["boundary"="administrative"]["admin_level"="8"]->.a;
(
  nwr["amenity"~"^(bar|pub|cafe|nightclub|biergarten)$"](area.a);
);
out center tags;
"""


def fetch():
    data = urllib.parse.urlencode({"data": QUERY}).encode()
    for ep in ENDPOINTS:
        try:
            print(f"query {ep} ...")
            req = urllib.request.Request(ep, data=data,
                  headers={"User-Agent": "SurPrice-agent7/1.0 (drink map Milano)"})
            with urllib.request.urlopen(req, timeout=190) as r:
                return json.loads(r.read().decode("utf-8", "replace"))
        except Exception as e:
            print(f"  fail: {type(e).__name__} {str(e)[:80]}")
            time.sleep(3)
    return None


def main():
    d = fetch()
    if not d:
        print("Overpass irraggiungibile — salto (il fallback typical_by_type garantisce comunque 100%).")
        return
    els = d.get("elements", [])
    rows, n_oh = [], 0
    for el in els:
        t = el.get("tags", {})
        name = t.get("name", "")
        if not name:
            continue
        lat = el.get("lat") or el.get("center", {}).get("lat")
        lon = el.get("lon") or el.get("center", {}).get("lon")
        if lat is None or lon is None:
            continue
        oh = t.get("opening_hours", "")
        if oh:
            n_oh += 1
        street = " ".join(x for x in [t.get("addr:street", ""), t.get("addr:housenumber", "")] if x)
        addr = ", ".join(x for x in [street, t.get("addr:postcode", ""), t.get("addr:city", "")] if x)
        rows.append({
            "name": name, "lat": f"{lat:.7f}", "lon": f"{lon:.7f}",
            "amenity": t.get("amenity", ""), "cuisine": t.get("cuisine", ""),
            "website": t.get("website") or t.get("contact:website", ""),
            "phone": t.get("phone") or t.get("contact:phone", ""),
            "opening_hours": oh, "address": addr,
        })
    with open(OUT, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["name", "lat", "lon", "amenity", "cuisine",
                                          "website", "phone", "opening_hours", "address"])
        w.writeheader(); w.writerows(rows)
    print(f"✍  {OUT}: {len(rows)} venues | con opening_hours: {n_oh} "
          f"| website: {sum(1 for r in rows if r['website'])} | phone: {sum(1 for r in rows if r['phone'])}")


if __name__ == "__main__":
    main()
