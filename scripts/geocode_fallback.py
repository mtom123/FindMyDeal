#!/usr/bin/env python3
"""Geocoding dei venue a fallback Duomo (45.4642) in unified_venues, per nome via Nominatim.
Output: raw_sources/agent5_geocode_fixes.csv (venue, old/new coord, address, method)."""
import csv, re, time, requests
NOM="https://nominatim.openstreetmap.org/search"
H={"User-Agent":"FoodPriceMilano/1.0 (geocoding)"}
LAT=(45.40,45.52); LNG=(9.10,9.28)  # bbox Milano citta'
def geo(q):
    try:
        r=requests.get(NOM,params={"q":q,"format":"json","limit":1,"countrycodes":"it"},headers=H,timeout=15)
        d=r.json()
        if d:
            la,lo=float(d[0]["lat"]),float(d[0]["lon"])
            if LAT[0]<=la<=LAT[1] and LNG[0]<=lo<=LNG[1]:
                return round(la,6),round(lo,6),d[0].get("display_name","")[:60]
    except Exception: pass
    return None
def clean(n):
    n=re.sub(r'\.(it|com|io)$','',n)  # domini
    n=re.sub(r'\s+(International|Bi.*)$','',n)
    return n.strip()
def main():
    r=list(csv.DictReader(open('data/unified_venues.csv',encoding='utf-8-sig')))
    fb=[x for x in r if x.get('latitude','')=='45.4642']
    out=[]; ok=0
    for x in fb:
        nm=clean(x['venue_name'])
        res=geo(nm+" Milano bar"); time.sleep(1.2)
        if not res:
            res=geo(nm+" Milano"); time.sleep(1.2)
        if res:
            ok+=1
            out.append({"venue_name":x['venue_name'],"old_lat":"45.4642","old_lng":x.get('longitude',''),
                        "new_lat":res[0],"new_lng":res[1],"matched":res[2],"method":"nominatim_name"})
            print(f"  OK  {x['venue_name'][:26]:<26} -> {res[0]},{res[1]}  ({res[2][:34]})")
        else:
            print(f"  --  {x['venue_name'][:26]:<26} non risolto")
    import os; os.makedirs("raw_sources",exist_ok=True)
    with open("raw_sources/agent5_geocode_fixes.csv","w",newline="",encoding="utf-8-sig") as f:
        w=csv.DictWriter(f,fieldnames=["venue_name","old_lat","old_lng","new_lat","new_lng","matched","method"]); w.writeheader(); w.writerows(out)
    print(f"\nGeocodate {ok}/{len(fb)} | output: raw_sources/agent5_geocode_fixes.csv")
if __name__=="__main__": main()
