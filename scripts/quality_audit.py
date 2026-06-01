#!/usr/bin/env python3
"""Audit qualita' prezzi su data/unified_prices.csv: outlier per prodotto + policy tolleranza."""
import csv, statistics as st
from collections import defaultdict, Counter

# POLICY tolleranza [min,max] EUR per prodotto (prezzi bar Milano)
BANDS={'spritz':(4,18),'negroni':(6,22),'americano':(5,18),'gin_tonic':(5,20),'mojito':(5,18),
 'moscow_mule':(5,18),'margarita':(6,22),'daiquiri':(6,22),'manhattan':(7,22),'custom_cocktail':(5,25),
 'beer_draft_small':(2,8),'beer_draft_medium':(3.5,12),'beer_bottle':(2.5,15),'beer_moretti':(2,10),
 'beer_heineken':(2,10),'beer_peroni':(2,10),'wine_glass':(3,15),'prosecco_glass':(3,18),
 'espresso':(0.8,3.5),'cappuccino':(1,4.5),'soft_drink':(1.5,10),'water':(0.3,6)}

def main():
    r=list(csv.DictReader(open('data/unified_prices.csv',encoding='utf-8-sig')))
    viol=[]
    for x in r:
        prod=x['normalized_product']
        try: p=float(x['price_eur'])
        except: continue
        lo,hi=BANDS.get(prod,(0.5,80))
        if p<lo or p>hi:
            flag='BASSO' if p<lo else 'ALTO'
            viol.append((prod,p,lo,hi,flag,x['venue_name'],x['item_name'],x['source_platform']))
    print(f"VIOLAZIONI: {len(viol)}/{len(r)} ({len(viol)*100//len(r)}%)")
    print("per prodotto:",Counter(v[0] for v in viol).most_common())
    print("\n=== ELENCO (per CEO) ===")
    for prod,p,lo,hi,flag,ven,item,plat in sorted(viol,key=lambda v:(v[0],v[1])):
        print(f"  [{flag:<5}] {prod:<16} EUR{p:<6} band[{lo}-{hi}] | {ven[:18]:<18} | {item[:32]:<32} | {plat}")
    return viol

if __name__=="__main__":
    main()
