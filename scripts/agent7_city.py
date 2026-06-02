#!/usr/bin/env python3
"""
Agent 7 / S8 — discovery drink no-price PARAMETRICA per città (replica Milano).

Uso: python3 scripts/agent7_city.py <Città>
Es:  python3 scripts/agent7_city.py Roma

Sorgente universale = OSM Overpass (bar/pub/cafe/nightclub/biergarten nella bbox città):
porta name + amenity + opening_hours + website + phone + address. Poi riusa il pipeline
S7: dedup geo+nome, classify, venue_type, opening_hours cascade (reale OSM → typical_by_type).

Riusa: normalization (CITY_BBOX, is_in_city), agent6_standardize (helpers),
agent7_standardize (rec, cluster, canonicalize). NON duplica logica.

Output: raw_sources/agent7_<city>_venues_no_price.csv
"""
import sys, os, csv, json, time, datetime, urllib.request, urllib.parse, collections, re

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from normalization import CITY_BBOX, is_in_city
from agent6_standardize import is_junk_name, norm_name
from agent7_standardize import rec, cluster, canonicalize, fnum, RAW

ENDPOINTS = ["https://overpass-api.de/api/interpreter",
             "https://overpass.kumi.systems/api/interpreter"]
UA = "SurPrice-agent7-s8/1.0 (drink map Italia multi-city)"


def overpass(city):
    lat_min, lat_max, lon_min, lon_max = CITY_BBOX[city]
    q = (f"[out:json][timeout:180];"
         f'nwr["amenity"~"^(bar|pub|cafe|nightclub|biergarten)$"]'
         f"({lat_min},{lon_min},{lat_max},{lon_max});out center tags;")
    cache = os.path.join(RAW, f".agent7_osm_{city.lower()}.json")
    if os.path.exists(cache):
        try:
            return json.load(open(cache)).get("elements", [])
        except Exception:
            pass
    data = urllib.parse.urlencode({"data": q}).encode()
    for ep in ENDPOINTS:
        try:
            print(f"  Overpass {ep.split('/')[2]} for {city} ...")
            req = urllib.request.Request(ep, data=data, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=190) as r:
                d = json.loads(r.read().decode("utf-8", "replace"))
            json.dump(d, open(cache, "w"))
            return d.get("elements", [])
        except Exception as e:
            print(f"    fail: {type(e).__name__} {str(e)[:70]}")
            time.sleep(4)
    return []


def build_recs(els, city):
    out = []
    for el in els:
        t = el.get("tags", {})
        name = t.get("name", "")
        if not name:
            continue
        lat = el.get("lat") or el.get("center", {}).get("lat")
        lon = el.get("lon") or el.get("center", {}).get("lon")
        if lat is None or lon is None or not is_in_city(lat, lon, city):
            continue
        street = " ".join(x for x in [t.get("addr:street", ""), t.get("addr:housenumber", "")] if x)
        addr = ", ".join(x for x in [street, t.get("addr:postcode", ""),
                                     t.get("addr:city", city)] if x)
        out.append(rec("osm", str(el.get("id", "")), name, addr, lat, lon, "",
                       t.get("website") or t.get("contact:website", ""),
                       t.get("phone") or t.get("contact:phone", ""),
                       t.get("amenity", ""), t.get("cuisine", ""), "", "osm_overpass",
                       opening_hours=t.get("opening_hours", "")))
    return out


def main(city):
    if city not in CITY_BBOX:
        print(f"città non in CITY_BBOX: {city}"); return
    els = overpass(city)
    recs = build_recs(els, city)
    print(f"{city}: OSM elements {len(els)} → drink recs in bbox {len(recs)}")
    if not recs:
        print("nessun rec — skip"); return

    clusters = cluster(recs)
    canon = [canonicalize(c) for c in clusters]

    kept, dropped = [], collections.Counter()
    for c in canon:
        if c["_class"] == "NO_TARGET":
            dropped["NO_TARGET"] += 1; continue
        if is_junk_name(c["venue_name"]):
            dropped["JUNK"] += 1; continue
        if not is_in_city(c["latitude"], c["longitude"], city):
            dropped["OUT_BBOX"] += 1; continue
        kept.append(c)
    print(f"  cluster {len(canon)} → kept {len(kept)} (dropped {dict(dropped)})")
    print(f"  venue_type: {dict(collections.Counter(c['_vtype'] for c in kept).most_common())}")
    oh = collections.Counter(c["opening_hours_source"] for c in kept)
    print(f"  opening_hours 100%? {all(c['opening_hours'] for c in kept)} by-source {dict(oh)}")
    print(f"  website {sum(1 for c in kept if c['website'])} | phone {sum(1 for c in kept if c['phone'])}")

    cols = ["source_platform", "source_venue_id", "venue_name", "venue_url", "address", "city",
            "latitude", "longitude", "categories", "price_tier", "rating", "rating_count",
            "phone", "website", "opening_hours", "has_menu", "menu_url", "extraction_status",
            "retrieved_at", "venue_type", "target_classification", "has_price",
            "geocoding_confidence", "all_names", "nil_quartiere", "name_source",
            "source_provenance", "opening_hours_source"]
    now = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    out_path = os.path.join(RAW, f"agent7_{city.lower()}_venues_no_price.csv")
    with open(out_path, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols); w.writeheader()
        for c in sorted(kept, key=lambda x: (x["_vtype"], x["venue_name"].lower())):
            cls = "TARGET" if c["_class"] == "TARGET" else "AMBIGUOUS_TO_REVIEW"
            w.writerow({
                "source_platform": "osm", "source_venue_id": c["source_venue_id"],
                "venue_name": c["venue_name"], "venue_url": "", "address": c["address"],
                "city": city, "latitude": f"{c['latitude']:.6f}", "longitude": f"{c['longitude']:.6f}",
                "categories": c["categories"], "price_tier": "", "rating": "", "rating_count": "",
                "phone": c["phone"], "website": c["website"], "opening_hours": c["opening_hours"],
                "has_menu": "False", "menu_url": "", "extraction_status": "no_price",
                "retrieved_at": now, "venue_type": c["_vtype"], "target_classification": cls,
                "has_price": "False", "geocoding_confidence": "existing", "all_names": c["all_names"],
                "nil_quartiere": "", "name_source": c["name_source"],
                "source_provenance": c["source_provenance"], "opening_hours_source": c["opening_hours_source"]})
    print(f"✍  {out_path} ({len(kept)} venues)")
    return len(kept), oh.get("osm", 0)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "Roma")
