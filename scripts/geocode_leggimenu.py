#!/usr/bin/env python3
"""
STEP 2 (PROMPT_PIETRO_NOTTE) — geocoding preciso delle venue leggimenu stackate.

Le 39 venue con latitude == 45.4642 sono accatastate su Piazza Duomo (nessun geocoding).
Strategia:
  1. se la venue ha un address reale -> Nominatim
  2. se address mancante/placeholder -> fetch pagina leggimenu, estrai JSON-LD address, poi Nominatim
  3. accetta solo risultati dentro il bounding box di Milano (scarta geocodifiche sbagliate)

Rate limit Nominatim: >=1.2s tra richieste, stop 60s su 429.
Sovrascrive raw_sources/leggimenu_venues.csv con le coordinate aggiornate.
"""
import csv, json, re, sys, time
from urllib.parse import quote
import requests

VEN = "raw_sources/leggimenu_venues.csv"
STACK_LAT = "45.4642"
UA = {"User-Agent": "FoodPriceMilano/1.0 (geocoding; contact: pietro@foodprice.local)"}
NOMINATIM = "https://nominatim.openstreetmap.org/search"
# bounding box Milano (un po' allargato per hinterland vicino)
LAT_MIN, LAT_MAX, LNG_MIN, LNG_MAX = 45.36, 45.56, 9.02, 9.32
SLEEP = 1.3


def jsonld_address(slug):
    """Recupera un address dalla pagina leggimenu via JSON-LD / meta."""
    url = f"https://www.leggimenu.it/menu/{slug}"
    try:
        h = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=15).text
    except requests.RequestException:
        return ""
    for m in re.finditer(r'<script[^>]+application/ld\+json[^>]*>(.*?)</script>', h, re.S):
        try:
            data = json.loads(m.group(1))
        except json.JSONDecodeError:
            continue
        for obj in (data if isinstance(data, list) else [data]):
            addr = obj.get("address") if isinstance(obj, dict) else None
            if isinstance(addr, dict):
                parts = [addr.get(k, "") for k in ("streetAddress", "postalCode", "addressLocality")]
                s = " ".join(p for p in parts if p).strip()
                if s:
                    return s
            elif isinstance(addr, str) and addr.strip():
                return addr.strip()
    return ""


def geocode(addr):
    """Nominatim -> (lat,lng) o None. Filtra fuori bounding box Milano."""
    q = addr if "milano" in addr.lower() else addr + ", Milano"
    url = f"{NOMINATIM}?q={quote(q)}&format=json&limit=1&countrycodes=it"
    for attempt in range(3):
        try:
            r = requests.get(url, headers=UA, timeout=15)
        except requests.RequestException:
            time.sleep(2); continue
        if r.status_code == 429:
            print("   429 -> sleep 60s"); time.sleep(60); continue
        if r.status_code != 200:
            return None
        js = r.json()
        if not js:
            return None
        lat, lng = float(js[0]["lat"]), float(js[0]["lon"])
        if LAT_MIN <= lat <= LAT_MAX and LNG_MIN <= lng <= LNG_MAX:
            return round(lat, 6), round(lng, 6)
        return None  # fuori Milano: scarta
    return None


def main():
    rows = list(csv.DictReader(open(VEN, encoding="utf-8-sig")))
    fn = list(rows[0].keys())
    targets = [r for r in rows if r.get("latitude", "").strip() == STACK_LAT]
    print(f"Da geocodare: {len(targets)} venue stackate")
    ok = fail = 0
    for r in targets:
        addr = (r.get("address") or "").strip()
        slug = re.sub(r".*/menu/", "", r.get("menu_url") or r.get("venue_url") or "").strip("/")
        # address mancante o placeholder Duomo -> prova JSON-LD
        if not addr or "duomo 21" in addr.lower():
            ja = jsonld_address(slug)
            if ja:
                addr = ja
            time.sleep(SLEEP)
        if not addr:
            fail += 1; print(f"   [no addr] {r['venue_name'][:34]}"); continue
        res = geocode(addr)
        time.sleep(SLEEP)
        if not res:
            # retry con indirizzo ripulito: via la parte dopo 'angolo'/'/'/secondo segmento
            clean = re.split(r"\s+angolo\s+|/| - ", addr, flags=re.I)[0].strip()
            clean = re.sub(r"\s+", " ", clean)
            if clean and clean != addr:
                res = geocode(clean)
                time.sleep(SLEEP)
                if res:
                    addr = clean
        if res:
            r["latitude"], r["longitude"] = str(res[0]), str(res[1])
            r["address"] = addr
            ok += 1
            print(f"   OK  {r['venue_name'][:30]:<30} -> {res[0]},{res[1]}  ({addr[:40]})")
        else:
            fail += 1
            print(f"   --  {r['venue_name'][:30]:<30} geocode fallito ({addr[:40]})")

    with open(VEN, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=fn); w.writeheader(); w.writerows(rows)
    print(f"\nGeocodate: {ok}/{len(targets)} | fallite: {fail}")
    print(f"File aggiornato: {VEN}")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(1)
