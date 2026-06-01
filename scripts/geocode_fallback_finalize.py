#!/usr/bin/env python3
"""Completa il geocoding fallback: indirizzi trovati via WebSearch + duplicati."""
import csv, time, requests, os
NOM="https://nominatim.openstreetmap.org/search"; H={"User-Agent":"FoodPriceMilano/1.0"}
LAT=(45.40,45.54); LNG=(9.08,9.30)
ADDR={  # venue_name (come in unified) -> indirizzo (da WebSearch)
 "Victoriasclub":"Via Feltre 30, Milano","tardispubmilano.it":"Via Ornato 134, Milano",
 "labirrofila.com":"Via Sant'Ampellio 14, Milano","Floraetlabora":"Alzaia Naviglio Pavese 20, Milano",
 "Lucaeandreabar":"Alzaia Naviglio Grande 34, Milano","Armanisilos":"Via Bergognone 40, Milano",
 "Morgantecocktail":"Vicolo dei Lavandai, Milano"}
DUP={"Eatmeandgo":"Eatme&Go","Caffefernanda":"Caffè Fernanda","Caffè Inn International Bi":"Caffè Inn"}
def geo(q):
    try:
        d=requests.get(NOM,params={"q":q,"format":"json","limit":1,"countrycodes":"it"},headers=H,timeout=15).json()
        if d:
            la,lo=float(d[0]["lat"]),float(d[0]["lon"])
            if LAT[0]<=la<=LAT[1] and LNG[0]<=lo<=LNG[1]: return round(la,6),round(lo,6),d[0].get("display_name","")[:50]
    except Exception: pass
    return None
def main():
    rows=list(csv.DictReader(open("raw_sources/agent5_geocode_fixes.csv",encoding="utf-8-sig")))
    have={r["venue_name"] for r in rows}
    bylat={r["venue_name"]:(r["new_lat"],r["new_lng"]) for r in rows}
    # 1) indirizzi WebSearch
    for name,addr in ADDR.items():
        if name in have: continue
        res=geo(addr); time.sleep(1.2)
        if res:
            rows.append({"venue_name":name,"old_lat":"45.4642","old_lng":"","new_lat":res[0],"new_lng":res[1],"matched":addr,"method":"websearch_addr+nominatim"})
            print(f"  OK {name:<22} -> {res[0]},{res[1]} ({addr})")
        else: print(f"  -- {name:<22} non risolto ({addr})")
    # 2) duplicati
    for dupname,twin in DUP.items():
        if twin in bylat:
            la,lo=bylat[twin]
            rows.append({"venue_name":dupname,"old_lat":"45.4642","old_lng":"","new_lat":la,"new_lng":lo,"matched":f"= {twin}","method":"duplicate"})
            print(f"  OK {dupname:<22} -> {la},{lo} (dup di {twin})")
    with open("raw_sources/agent5_geocode_fixes.csv","w",newline="",encoding="utf-8-sig") as f:
        w=csv.DictWriter(f,fieldnames=["venue_name","old_lat","old_lng","new_lat","new_lng","matched","method"]); w.writeheader(); w.writerows(rows)
    print(f"\nTotale geocode fixes: {len(rows)}/20")
if __name__=="__main__": main()
