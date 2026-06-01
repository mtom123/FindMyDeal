#!/usr/bin/env python3
"""Genera raw_sources/agent5_quality_flags.csv: outlier + azione consigliata + tassonomia FP.
Input: data/unified_prices.csv. NON modifica i dati — produce solo una lista per il CEO."""
import csv, re, os
BANDS={'spritz':(4,18),'negroni':(6,22),'americano':(5,18),'gin_tonic':(5,20),'mojito':(5,18),
 'moscow_mule':(5,18),'margarita':(6,22),'daiquiri':(6,22),'manhattan':(7,22),'custom_cocktail':(5,25),
 'beer_draft_small':(2,8),'beer_draft_medium':(3.5,12),'beer_bottle':(2.5,15),'beer_moretti':(2,10),
 'beer_heineken':(2,10),'beer_peroni':(2,10),'wine_glass':(3,15),'prosecco_glass':(3,18),
 'espresso':(0.8,3.5),'cappuccino':(1,4.5),'soft_drink':(1.5,10),'water':(0.3,6)}

def action(prod,p,lo,hi,name):
    n=name.lower()
    # tassonomia falsi positivi -> azione
    if prod=='americano' and re.search(r'caff',n): return 'RECLASSIFY->espresso','caffe americano (NON cocktail)'
    if prod=='espresso' and 'martini' in n: return 'RECLASSIFY->custom_cocktail','Espresso Martini (cocktail)'
    if prod=='espresso' and re.search(r'tronchetto|cervo|affogato|latte',n): return 'EXCLUDE','food/altro, non espresso'
    if prod=='beer_moretti' and re.search(r'vittorio|riserva|franciacorta|extra brut',n): return 'EXCLUDE','Vittorio Moretti = VINO, non Birra Moretti'
    if prod=='beer_bottle' and re.search(r'valpolicella|ripasso|antipasto|prosecco|vino',n): return 'EXCLUDE','vino/food, non birra'
    if prod=='margarita' and re.search(r'caraffa|pitcher|brocca',n): return 'EXCLUDE','caraffa multi-porzione (non 1 drink)'
    if prod=='prosecco_glass' and (re.search(r'bottig|valdobbiadene|docg|cuv',n) or p>18): return 'RECLASSIFY->bottle/EXCLUDE','bottiglia, non calice'
    if prod=='cappuccino' and re.search(r'ice|gelato|pistacchio|chocolate',n): return 'EXCLUDE','gelato/ice, non cappuccino'
    if prod=='soft_drink' and re.search(r'stout|ipa|beer|birra|nera|velvet|barrel',n): return 'RECLASSIFY->beer','craft beer, non soft drink'
    if prod=='negroni' and re.search(r'menu|home|coca cola|soft drink',n): return 'EXCLUDE','testo pagina/altro prodotto'
    if prod=='spritz' and p<2: return 'EXCLUDE','prezzo implausibile (parse error / componente)'
    if re.search(r'maxi|caraffa|brocca|carafe|litro|1l\b',n): return 'EXCLUDE','formato maxi/multi-porzione'
    # generico
    if p<lo: return 'REVIEW','prezzo sotto banda (possibile componente/altro formato)'
    return 'REVIEW','prezzo sopra banda (premium o errore — verificare)'

def main():
    r=list(csv.DictReader(open('data/unified_prices.csv',encoding='utf-8-sig')))
    out=[]
    for x in r:
        prod=x['normalized_product']
        try: p=float(x['price_eur'])
        except: continue
        lo,hi=BANDS.get(prod,(0.5,80))
        if p<lo or p>hi:
            act,reason=action(prod,p,lo,hi,x['item_name'])
            out.append({"normalized_product":prod,"price_eur":p,"band_min":lo,"band_max":hi,
                "flag":"LOW" if p<lo else "HIGH","venue_name":x['venue_name'],"item_name":x['item_name'],
                "source_platform":x['source_platform'],"recommended_action":act,"reason":reason,"source_url":x.get('source_url','')})
    os.makedirs("raw_sources",exist_ok=True)
    cols=["normalized_product","price_eur","band_min","band_max","flag","venue_name","item_name","source_platform","recommended_action","reason","source_url"]
    with open("raw_sources/agent5_quality_flags.csv","w",newline="",encoding="utf-8-sig") as f:
        w=csv.DictWriter(f,fieldnames=cols); w.writeheader(); w.writerows(out)
    from collections import Counter
    print(f"flag totali: {len(out)}")
    print("azioni:",Counter(o['recommended_action'] for o in out).most_common())
    return out
if __name__=="__main__": main()
