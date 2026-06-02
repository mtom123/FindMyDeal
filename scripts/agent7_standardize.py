#!/usr/bin/env python3
"""
Agent 7 — Discovery comune/CKAN/OSM → set drink Milano classificato & deduplicato.

Pool: CKAN (3.804) + comune_osm (named) + OSM Overpass (5.229) [+ TheFork, opzionale].
Clustering geo-proximity = name-recovery (OSM name per i placeholder) + dedup cross-source
in un colpo solo. Poi classify amenity-first + venue_type + esclusione vs DB reale.

Riusa scripts/agent6_standardize.py (NON duplica logica).
Output: raw_sources/agent7_venues_no_price.csv + agent7_dedup_map.csv
"""
import sys, os, csv, re, math, collections
from difflib import SequenceMatcher

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from agent6_standardize import (classify_venue, detect_venue_type, norm_name,
    clean_display_name, is_junk_name, sanitize_milan_address, fix_mojibake,
    clean_address, formality_score, MILAN_BBOX, read_csv, has)
from normalization import is_milan_or_unknown

ROOT = os.path.dirname(HERE)
RAW = os.path.join(ROOT, "raw_sources")
PRICES = os.path.join(ROOT, "data", "unified_prices.csv")
AGENT6 = os.path.join(RAW, "agent6_venues_no_price.csv")
CKAN = os.path.join(RAW, "ckan_milano_drink_venues_no_price.csv")
COMUNE = os.path.join(RAW, "comune_osm_venues.csv")
OSM = os.path.join(RAW, "osm_milano_drink_overpass.csv")
OSM_ENRICHED = os.path.join(RAW, "agent7_osm_enriched.csv")   # re-query con opening_hours (Step 7.1)
THEFORK = os.path.join(RAW, "agent7_thefork_raw.csv")   # opzionale (Step 6)

OUT = os.path.join(RAW, "agent7_venues_no_price.csv")
OUT_DEDUP = os.path.join(RAW, "agent7_dedup_map.csv")

DRINK_AMENITIES = {"bar", "pub", "cafe", "nightclub", "biergarten"}
PLACEHOLDER_RE = re.compile(r"non\s*identificat|^\[?\s*bar\s*\]?$|^locale$", re.I)

# bucket licenza Comune → venue_type (priorità: il primo che matcha). NB: 'wine bar' prima di
# 'birreria' così "h - Wine bar, birreria, pub..." → wine_bar, NON craft_beer.
LICENSE_TYPE = [
    ("disco bar", "cocktail_bar"), ("america bar", "cocktail_bar"), ("discotech", "cocktail_bar"),
    ("sale da ballo", "cocktail_bar"), ("locali serali", "cocktail_bar"),
    ("wine bar", "wine_bar"), ("enotech", "wine_bar"),
    ("birreria", "pub"), ("pub", "pub"),
    ("pasticceria", "cafe"), ("gelateria", "cafe"), ("caffè", "cafe"), ("caffe", "cafe"),
    ("gastronomici", "cafe"),
]

# fascia oraria indicativa per venue_type (formato spec OSM) — usata SOLO come fallback
TYPICAL_HOURS = {
    "cafe": "Mo-Su 07:00-20:00", "cocktail_bar": "Mo-Su 18:00-02:00", "pub": "Mo-Su 17:00-02:00",
    "wine_bar": "Mo-Su 17:00-00:00", "aperitivo_bar": "Mo-Su 17:00-22:00",
    "bistro": "Mo-Su 12:00-00:00", "craft_beer": "Mo-Su 17:00-01:00", "rooftop": "Mo-Su 18:00-01:00",
    "hotel_bar": "Mo-Su 11:00-00:00", "unknown": "Mo-Su 08:00-22:00",
}


def is_placeholder(name):
    n = (name or "").strip()
    return (not n) or bool(PLACEHOLDER_RE.search(n))


def fnum(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def in_bbox(lat, lon):
    return lat is not None and (MILAN_BBOX[0] <= lat <= MILAN_BBOX[1]
                                and MILAN_BBOX[2] <= lon <= MILAN_BBOX[3])


def meters(lat1, lon1, lat2, lon2):
    """Equirettangolare — accurato a distanze < ~1km."""
    mlat = math.radians((lat1 + lat2) / 2)
    dx = math.radians(lon2 - lon1) * math.cos(mlat) * 6371000
    dy = math.radians(lat2 - lat1) * 6371000
    return math.hypot(dx, dy)


# ─────────────────────────────────────────────
# LOAD: normalizza ogni sorgente in record comune
# ─────────────────────────────────────────────
def rec(source, vid, name, addr, lat, lon, categories="", website="", phone="",
        amenity="", cuisine="", nil="", name_source="", opening_hours=""):
    return dict(source=source, source_venue_id=vid, venue_name=clean_display_name(name),
                address=clean_address(addr or ""), latitude=lat, longitude=lon,
                categories=fix_mojibake(categories or ""), website=(website or "").strip(),
                phone=(phone or "").strip(), amenity=(amenity or "").strip().lower(),
                cuisine=(cuisine or "").strip().lower(), nil_quartiere=(nil or "").strip(),
                name_source=name_source, opening_hours=(opening_hours or "").strip())


def load_sources():
    pool = []
    # CKAN — gold (named + nil + license categories + _osm_amenity)
    for r in read_csv(CKAN):
        lat, lon = fnum(r.get("latitude")), fnum(r.get("longitude"))
        pool.append(rec("comune_milano", r.get("source_venue_id", ""), r.get("venue_name", ""),
                        r.get("address", ""), lat, lon, r.get("categories", ""),
                        r.get("website", ""), r.get("phone", ""),
                        r.get("_osm_amenity", ""), r.get("_osm_cuisine", ""),
                        r.get("nil_quartiere", ""), "ckan"))
    # comune_osm — solo i NOMINATI non placeholder (3.270 placeholder ridondanti vs OSM)
    for r in read_csv(COMUNE):
        if is_placeholder(r.get("venue_name", "")):
            continue
        lat, lon = fnum(r.get("latitude")), fnum(r.get("longitude"))
        pool.append(rec("comune", r.get("source_venue_id", ""), r.get("venue_name", ""),
                        r.get("address", ""), lat, lon, r.get("categories", ""),
                        name_source="comune"))
    # OSM Overpass — name + amenity + website/phone (+ opening_hours se file arricchito presente)
    osm_file = OSM_ENRICHED if os.path.exists(OSM_ENRICHED) else OSM
    for r in read_csv(osm_file):
        lat, lon = fnum(r.get("lat")), fnum(r.get("lon"))
        pool.append(rec("osm", "", r.get("name", ""), r.get("address", ""), lat, lon, "",
                        r.get("website", ""), r.get("phone", ""),
                        r.get("amenity", ""), r.get("cuisine", ""), "", "osm_overpass",
                        opening_hours=r.get("opening_hours", "")))
    # TheFork (Step 6) se presente
    if os.path.exists(THEFORK):
        for r in read_csv(THEFORK):
            lat, lon = fnum(r.get("latitude")), fnum(r.get("longitude"))
            pool.append(rec("thefork", r.get("source_venue_id", ""), r.get("venue_name", ""),
                            r.get("address", ""), lat, lon, r.get("categories", ""),
                            "", r.get("phone", ""), "", "", "", "thefork",
                            opening_hours=r.get("opening_hours", "")))
    # tieni solo con geo in bbox Milano
    pool = [p for p in pool if in_bbox(p["latitude"], p["longitude"])]
    return pool


# ─────────────────────────────────────────────
# CLUSTERING geo-proximity (name-recovery + dedup)
# ─────────────────────────────────────────────
class UF:
    def __init__(self, n): self.p = list(range(n))
    def find(self, x):
        while self.p[x] != x:
            self.p[x] = self.p[self.p[x]]; x = self.p[x]
        return x
    def union(self, a, b):
        ra, rb = self.find(a), self.find(b)
        if ra != rb: self.p[ra] = rb


def name_compat(a, b):
    if is_placeholder(a) or is_placeholder(b):
        return True
    na, nb = norm_name(a), norm_name(b)
    if not na or not nb:
        return True
    if na == nb or na in nb or nb in na:
        return True
    return SequenceMatcher(None, na, nb).ratio() > 0.82


def cluster(pool, radius_m=40):
    CELL = 0.0005   # ~55 m lat
    grid = collections.defaultdict(list)
    for i, p in enumerate(pool):
        key = (int(p["latitude"] / CELL), int(p["longitude"] / CELL))
        grid[key].append(i)
    uf = UF(len(pool))
    for i, p in enumerate(pool):
        ci, cj = int(p["latitude"] / CELL), int(p["longitude"] / CELL)
        for di in (-1, 0, 1):
            for dj in (-1, 0, 1):
                for j in grid.get((ci + di, cj + dj), ()):
                    if j <= i:
                        continue
                    q = pool[j]
                    if meters(p["latitude"], p["longitude"], q["latitude"], q["longitude"]) <= radius_m \
                       and name_compat(p["venue_name"], q["venue_name"]):
                        uf.union(i, j)
    # 2° passata: stesso nome ESATTO entro 150 m = stesso locale (geo-imprecisione cross-source).
    # Gap netto nei dati: dupes ≤80 m (stesso venue) vs ≥250 m (catene/branch distinti → restano separati).
    byname = collections.defaultdict(list)
    for i, p in enumerate(pool):
        nn = norm_name(p["venue_name"])
        if nn and not is_placeholder(p["venue_name"]):
            byname[nn].append(i)
    for idxs in byname.values():
        for a in range(len(idxs)):
            for b in range(a + 1, len(idxs)):
                i, j = idxs[a], idxs[b]
                if meters(pool[i]["latitude"], pool[i]["longitude"],
                          pool[j]["latitude"], pool[j]["longitude"]) <= 150:
                    uf.union(i, j)

    clusters = collections.defaultdict(list)
    for i in range(len(pool)):
        clusters[uf.find(i)].append(pool[i])
    return list(clusters.values())


# ─────────────────────────────────────────────
# CLASSIFY (amenity-first) + venue_type
# ─────────────────────────────────────────────
def classify_s7(name, categories, amenity, provenance=""):
    base = classify_venue(name, categories)
    if amenity == "restaurant":
        return "NO_TARGET"
    if amenity in DRINK_AMENITIES:
        return "TARGET" if base != "NO_TARGET" else "AMBIGUOUS"
    # TheFork = piattaforma di RISTORANTI: un venue solo-TheFork senza segnale drink esplicito
    # (bistro/bar/cocktail/wine/pub...) è un ristorante → NO_TARGET, non AMBIGUOUS.
    if provenance and set(provenance.split("|")) == {"thefork"}:
        return "TARGET" if base == "TARGET" else "NO_TARGET"
    return base


def venue_type_s7(name, categories, amenity, cuisine):
    # 1. OSM amenity = tag reale del mondo (più affidabile della licenza)
    if amenity == "nightclub":
        return "cocktail_bar"
    if amenity == "pub":
        return "pub"
    if amenity == "biergarten":
        return "craft_beer"
    # 2. detect sul NOME (insegna) — NON sulle categorie licenza: il bucket "h" contiene
    #    'birreria' e farebbe scattare craft_beer su centinaia di wine bar/pub generici.
    vt = detect_venue_type(name, "")
    if vt != "unknown":
        return vt
    if amenity in ("bar", "cafe"):
        return "cafe"
    # 3. bucket licenza Comune
    cl = (categories or "").lower()
    for sub, t in LICENSE_TYPE:
        if sub in cl:
            return t
    if "coffee" in cuisine or "cafe" in cuisine:
        return "cafe"
    return "unknown"


# ─────────────────────────────────────────────
# CANONICAL per cluster
# ─────────────────────────────────────────────
SRC_RANK = {"osm_overpass": 4, "thefork": 3, "ckan": 2, "comune": 1, "": 0}


def canonicalize(members):
    # nome: preferisci sorgente con nome commerciale (osm > thefork > ckan > comune), poi formality
    named = [m for m in members if not is_placeholder(m["venue_name"])]
    if named:
        canonical = max(named, key=lambda m: (SRC_RANK.get(m["name_source"], 0),
                                              formality_score(m["venue_name"])))["venue_name"]
        name_source = max(named, key=lambda m: SRC_RANK.get(m["name_source"], 0))["name_source"]
    else:
        canonical = members[0]["venue_name"] or "[bar non identificato]"
        name_source = "placeholder"

    def best(field, prefer_src=None):
        vals = [(m[field], m) for m in members if (m.get(field) or "").strip()]
        if not vals:
            return ""
        if prefer_src:
            for v, m in vals:
                if m["name_source"] == prefer_src:
                    return v
        return max(vals, key=lambda vm: len(vm[0]))[0]

    amenity = best("amenity", "osm_overpass")
    cuisine = best("cuisine", "osm_overpass")
    cats = "; ".join(sorted(set(c for m in members for c in re.split(r"\s*;\s*", m["categories"]) if c)))
    lats = [m["latitude"] for m in members]
    lons = [m["longitude"] for m in members]
    # geo: media (i membri sono entro 40 m)
    lat, lon = sum(lats) / len(lats), sum(lons) / len(lons)
    all_names = []
    for m in members:
        nm = m["venue_name"]
        if nm and not is_placeholder(nm) and nm not in all_names:
            all_names.append(nm)
    provenance = "|".join(sorted(set(m["source"] for m in members)))

    cls = classify_s7(canonical, cats, amenity, provenance)
    vt = venue_type_s7(canonical, cats, amenity, cuisine)
    # opening_hours: reale (OSM/TheFork) → altrimenti fascia tipica per venue_type (mai vuoto)
    oh, oh_src = "", "typical_by_type"
    for m in members:
        if m.get("opening_hours"):
            oh = m["opening_hours"]
            oh_src = "thefork" if m["name_source"] == "thefork" else "osm"
            break
    if not oh:
        oh = TYPICAL_HOURS.get(vt, TYPICAL_HOURS["unknown"])
    return {
        "venue_name": canonical, "name_source": name_source,
        "address": best("address"), "latitude": lat, "longitude": lon,
        "categories": cats, "website": best("website", "osm_overpass"),
        "phone": best("phone", "osm_overpass"), "amenity": amenity,
        "nil_quartiere": best("nil_quartiere", "ckan"),
        "all_names": " | ".join(all_names), "source_provenance": provenance,
        "opening_hours": oh, "opening_hours_source": oh_src,
        "_class": cls, "_vtype": vt, "_size": len(members),
        "source_venue_id": next((m["source_venue_id"] for m in members if m["source_venue_id"]), ""),
        "source_platform": (provenance.split("|")[0] if provenance else "comune_milano"),
    }


def geo_key(lat, lon):
    return (round(lat, 4), round(lon, 4))


def main():
    pool = load_sources()
    print(f"pool (geo in bbox): {len(pool)}  per sorgente:",
          dict(collections.Counter(p["source"] for p in pool)))

    clusters = cluster(pool)
    print(f"cluster unici: {len(clusters)}  (dedup ratio {len(pool)}→{len(clusters)} "
          f"= -{100 - 100*len(clusters)//len(pool)}%)")

    canon = [canonicalize(c) for c in clusters]

    # name recovery: cluster con membro comune/CKAN che ha adottato un nome OSM/TheFork
    recovered = sum(1 for c in canon if c["name_source"] in ("osm_overpass", "thefork")
                    and ("comune" in c["source_provenance"]))
    multi = [c for c in canon if c["_size"] > 1]
    print(f"cluster multi-source (dedup reale): {len(multi)} | nomi recuperati (comune→OSM): {recovered}")

    # esclusione vs DB reale: priced + agent6
    db_norm, db_geo = set(), set()
    for r in read_csv(PRICES):
        if (r.get("venue_name") or "").strip():
            db_norm.add(norm_name(r["venue_name"]))
            la, lo = fnum(r.get("latitude")), fnum(r.get("longitude"))
            if la and lo:
                db_geo.add(geo_key(la, lo))
    if os.path.exists(AGENT6):
        for r in read_csv(AGENT6):
            db_norm.add(norm_name(r["venue_name"]))
            la, lo = fnum(r.get("latitude")), fnum(r.get("longitude"))
            if la and lo:
                db_geo.add(geo_key(la, lo))

    # quality gate + esclusioni
    kept, dropped = [], collections.Counter()
    for c in canon:
        nm = c["venue_name"]
        if c["_class"] == "NO_TARGET":
            dropped["NO_TARGET"] += 1; continue
        if is_junk_name(nm):
            dropped["JUNK_NAME"] += 1; continue
        if not is_milan_or_unknown(c["address"]):
            dropped["NON_MILAN_CAP"] += 1; continue
        if norm_name(nm) in db_norm or geo_key(c["latitude"], c["longitude"]) in db_geo:
            dropped["ALREADY_IN_DB"] += 1; continue
        if is_placeholder(nm) and not (c["address"].strip()):
            dropped["PLACEHOLDER_NO_ADDR"] += 1; continue
        kept.append(c)

    print(f"\nquality gate: {len(kept)} kept / {len(canon)} canonical")
    print("  dropped:", dict(dropped))
    print("  classification:", dict(collections.Counter(c["_class"] for c in kept)))
    print("  venue_type:", dict(collections.Counter(c["_vtype"] for c in kept).most_common()))
    print("  name_source:", dict(collections.Counter(c["name_source"] for c in kept)))
    print("  con website:", sum(1 for c in kept if c["website"]),
          "| con phone:", sum(1 for c in kept if c["phone"]),
          "| con nil:", sum(1 for c in kept if c["nil_quartiere"]))
    oh_cov = sum(1 for c in kept if c["opening_hours"])
    print(f"  opening_hours: {oh_cov}/{len(kept)} ({100*oh_cov//max(1,len(kept))}%) — by source:",
          dict(collections.Counter(c["opening_hours_source"] for c in kept)))

    # write File 1
    cols = ["source_platform", "source_venue_id", "venue_name", "venue_url", "address", "city",
            "latitude", "longitude", "categories", "price_tier", "rating", "rating_count",
            "phone", "website", "opening_hours", "has_menu", "menu_url", "extraction_status",
            "retrieved_at", "venue_type", "target_classification", "has_price",
            "geocoding_confidence", "all_names", "nil_quartiere", "name_source",
            "source_provenance", "opening_hours_source"]
    import datetime
    now = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    with open(OUT, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols); w.writeheader()
        for c in sorted(kept, key=lambda x: (x["_vtype"], x["venue_name"].lower())):
            cls = "TARGET" if c["_class"] == "TARGET" else "AMBIGUOUS_TO_REVIEW"
            w.writerow({
                "source_platform": c["source_platform"], "source_venue_id": c["source_venue_id"],
                "venue_name": c["venue_name"], "venue_url": "",
                "address": c["address"], "city": "Milano",
                "latitude": f"{c['latitude']:.6f}", "longitude": f"{c['longitude']:.6f}",
                "categories": c["categories"], "price_tier": "", "rating": "", "rating_count": "",
                "phone": c["phone"], "website": c["website"], "opening_hours": c["opening_hours"],
                "has_menu": "False", "menu_url": "", "extraction_status": "no_price",
                "retrieved_at": now, "venue_type": c["_vtype"], "target_classification": cls,
                "has_price": "False", "geocoding_confidence": "existing",
                "all_names": c["all_names"], "nil_quartiere": c["nil_quartiere"],
                "name_source": c["name_source"], "source_provenance": c["source_provenance"],
                "opening_hours_source": c["opening_hours_source"]})
    print(f"\n✍  {OUT} ({len(kept)} venues)")

    # File 2: dedup map (cluster multi-source o esclusi)
    with open(OUT_DEDUP, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["canonical_name", "all_variants", "geo_key", "source_provenance",
                    "cluster_size", "target_classification"])
        for c in sorted(canon, key=lambda x: -x["_size"]):
            if c["_size"] > 1:
                w.writerow([c["venue_name"], c["all_names"],
                            f"{c['latitude']:.4f},{c['longitude']:.4f}",
                            c["source_provenance"], c["_size"], c["_class"]])
    print(f"✍  {OUT_DEDUP}")

    # CAP / NIL coverage
    caps = collections.Counter()
    for c in kept:
        m = re.findall(r"\b(20\d{3})\b", c["address"])
        if m: caps[m[0]] += 1
    nils = collections.Counter(c["nil_quartiere"] for c in kept if c["nil_quartiere"])
    print(f"\nCAP distinti: {len(caps)} | NIL distinti: {len(nils)} | "
          f"NIL con ≥3: {sum(1 for n,v in nils.items() if v>=3)}")

    # stats sidecar per agent7_report.py
    import json
    stats = {
        "pool_total": len(pool),
        "pool_by_source": dict(collections.Counter(p["source"] for p in pool)),
        "n_clusters": len(clusters), "n_multi": len(multi), "recovered": recovered,
        "dropped": dict(dropped), "kept": len(kept),
        "classification": dict(collections.Counter(c["_class"] for c in kept)),
        "venue_type": dict(collections.Counter(c["_vtype"] for c in kept)),
        "name_source": dict(collections.Counter(c["name_source"] for c in kept)),
        "oh_source": dict(collections.Counter(c["opening_hours_source"] for c in kept)),
        "website": sum(1 for c in kept if c["website"]),
        "phone": sum(1 for c in kept if c["phone"]),
        "nil": sum(1 for c in kept if c["nil_quartiere"]),
        "n_caps": len(caps), "caps": dict(caps.most_common()),
        "n_nils": len(nils), "nils_ge3": sum(1 for n, v in nils.items() if v >= 3),
        "thefork_in_pool": dict(collections.Counter(p["source"] for p in pool)).get("thefork", 0),
    }
    json.dump(stats, open(os.path.join(RAW, ".agent7_stats.json"), "w"), ensure_ascii=False)


if __name__ == "__main__":
    main()
