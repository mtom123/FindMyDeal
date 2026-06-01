#!/usr/bin/env python3
"""STEP 1 (S3) — direct scraping siti OSM Milano (bar con website, non ancora nel DB prezzi).
Homepage + path-probing menu; prezzi vicino a keyword drink; PDF via pdfplumber.
Output: raw_sources/osm_direct2_venues.csv + _menu_items.csv. source_platform=direct_website."""
import csv, io, os, re, sys, time, hashlib
from datetime import datetime, timezone
import requests
from bs4 import BeautifulSoup
try:
    import pdfplumber; HAVE_PDF=True
except ImportError: HAVE_PDF=False

H={"User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"}
CACHE="cache_osm_direct2"; SLEEP=2; NOW=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
OUT_V="raw_sources/osm_direct2_venues.csv"; OUT_I="raw_sources/osm_direct2_menu_items.csv"
PRICE_RE=re.compile(r'(?<!\d)(\d{1,2}[.,]\d{2})\s*€|€\s*(\d{1,2}[.,]?\d{0,2})')
DRINK=re.compile(r'\b(spritz|negroni|americano|gin\s*tonic|mojito|moscow\s*mule|margarita|daiquiri|manhattan|hugo|aperol|campari|moretti|heineken|peroni|nastro\s*azzurro|birra|calice|prosecco|ipa|stout|lager|caff[eè]|cappuccino|acqua|coca\s*cola|cocktail)\b',re.I)
PATHS=['','/menu','/drink','/drinks','/cocktail','/cocktails','/carta','/listino','/beverage','/bere','/birre','/drink-list','/la-carta','/menu-drink']
NON_MILAN=['torino','pessione','roma','napoli','siena','parma','ferrara','lecce','trento','bologna']

TARGET=[("Radetzky Café","https://www.radetzky.it/"),("Mulligan's","https://mulliganspub.it/"),
("55 Milano","https://www.55milano.com/"),("Il Gattopardo","https://www.ilgattopardomilano.com/"),
("Living","https://www.livingmilano.com/"),("Bar Bianco","https://www.barbiancomilano.com/"),
("Gate","https://www.gatemilano.it/"),("11 Clubroom","https://www.11milano.it/"),
("Caffè Letterario","https://www.caffeletterariomilano.it/"),("Cantine Isola","https://www.cantineisola.it/"),
("Mag Café","https://www.mag-cafe.it/"),("Rita","https://www.ritamilano.it/"),
("El Brellin","https://www.elbrellin.com/"),("The Spirit","https://www.thespiritmilano.it/"),
("Baladin Milano","https://www.baladin.it/"),("Birrificio Lambrate","https://www.birrificiolambrate.com/"),
("Ostello Bello","https://www.ostellobello.com/"),("Upcycle","https://www.upcyclemilano.it/"),
("The Doping Club","https://www.thedopingclub.it/"),("Cuore","https://www.cuoremilano.it/")]

def classify(t):
    t=t.lower()
    for k,v in [("moretti","beer_moretti"),("heineken","beer_heineken"),("peroni","beer_peroni"),
                ("nastro azzurro","beer_peroni"),("spritz","spritz"),("negroni","negroni"),
                ("moscow mule","moscow_mule"),("gin tonic","gin_tonic"),("mojito","mojito"),
                ("margarita","margarita"),("daiquiri","daiquiri"),("manhattan","manhattan"),("cappuccino","cappuccino")]:
        if k in t: return v
    if "americano" in t and "caff" not in t and "rovere" not in t: return "americano"
    if ("calice" in t or "vino al calice" in t): return "wine_glass"
    if "prosecco" in t: return "prosecco_glass"
    if "espresso" in t: return "espresso"
    if any(w in t for w in ("coca","fanta","sprite","bibita")): return "soft_drink"
    if "acqua" in t: return "water"
    if "birra" in t:
        if any(w in t for w in ("piccola","0,2","0.2","0,3","33")): return "beer_draft_small"
        if any(w in t for w in ("media","0,4","0.4","0,5","50","grande")): return "beer_draft_medium"
        return "beer_bottle"
    return ""

def fetch(url, binary=False):
    os.makedirs(CACHE,exist_ok=True)
    p=os.path.join(CACHE,hashlib.sha256(url.encode()).hexdigest()[:24]+(".bin" if binary else ".html"))
    if os.path.exists(p): return open(p,"rb").read() if binary else open(p,encoding="utf-8",errors="replace").read()
    try:
        time.sleep(SLEEP); r=requests.get(url,headers=H,timeout=10,allow_redirects=True)
    except requests.RequestException: return None
    if r.status_code!=200: return None
    if binary: open(p,"wb").write(r.content); return r.content
    open(p,"w",encoding="utf-8").write(r.text); return r.text

def extract(text, vname, url):
    rows=[]; lines=[l.strip() for l in text.split("\n") if l.strip()]
    for i,line in enumerate(lines):
        if len(line)>120: continue
        pm=PRICE_RE.findall(line)
        if not pm: continue
        ctx=" ".join(lines[max(0,i-1):i+2])
        if not DRINK.search(ctx): continue
        for m in pm:
            ps=m[0] or m[1]
            try: price=float(ps.replace(",","."))
            except: continue
            if price<0.5 or price>60: continue
            prod=classify(line)
            rows.append({"source_platform":"direct_website","source_venue_id":url,"venue_name":vname,
                "venue_url":url,"menu_section":"","item_name":re.sub(r'\s*€.*','',line).strip()[:90] or line[:90],
                "item_description":"","raw_price":(ps+"€"),"normalized_price_eur":price,"currency":"EUR",
                "price_type":"menu","item_type":"drink" if prod else "","normalized_product":prod,
                "confidence":"high" if prod else "low","allergens":"","retrieved_at":NOW,"source_url":url})
    # dedup interno
    seen=set(); out=[]
    for r in rows:
        k=(r["item_name"],r["raw_price"])
        if k not in seen: seen.add(k); out.append(r)
    return out

def scrape(vname, base):
    if not base.startswith("http"): base="http://"+base
    rows=[]; used=base
    for path in PATHS:
        url=base.rstrip("/")+path if path else base
        html=fetch(url)
        if not html: continue
        soup=BeautifulSoup(html,"html.parser")
        # PDF menu?
        for a in soup.find_all("a",href=True):
            if a["href"].lower().endswith(".pdf") and any(w in (a["href"]+a.get_text()).lower() for w in ("menu","carta","drink","listino","bar")):
                pdfurl=a["href"] if a["href"].startswith("http") else base.rstrip("/")+"/"+a["href"].lstrip("/")
                if HAVE_PDF:
                    c=fetch(pdfurl,binary=True)
                    if c:
                        try:
                            with pdfplumber.open(io.BytesIO(c)) as pdf:
                                ptext="\n".join((pg.extract_text() or "") for pg in pdf.pages[:12])
                            r=extract(ptext,vname,pdfurl)
                            if r: rows.extend(r); used=pdfurl
                        except Exception: pass
                break
        for tag in soup(["script","style"]): tag.decompose()
        r=extract(soup.get_text("\n"),vname,url)
        if r: rows.extend(r); used=url; break
    # dedup
    seen=set(); out=[]
    for r in rows:
        k=(r["item_name"],r["raw_price"])
        if k not in seen: seen.add(k); out.append(r)
    return out, used

def main():
    priced=set()
    for p in ["data/unified_prices.csv","data/unified_menu_items.csv"]:
        if os.path.exists(p):
            for r in csv.DictReader(open(p,encoding="utf-8-sig")):
                n=(r.get("venue_name","") or "").lower().strip()
                if n: priced.add(n)
    targets=[]
    seen_ws=set()
    for n,w in TARGET:
        if n.lower() not in priced: targets.append((n,w,"","")); seen_ws.add(w)
    for r in csv.DictReader(open("raw_sources/comune_osm_venues.csv",encoding="utf-8-sig")):
        w=(r.get("website","") or "").strip(); n=(r.get("venue_name","") or "").strip()
        if w and n and not n.startswith("[") and n.lower() not in priced and w not in seen_ws \
           and not any(x in w for x in ("instagram","facebook","tripadvisor")):
            targets.append((n,w,r.get("latitude",""),r.get("longitude",""))); seen_ws.add(w)
    print(f"Target: {len(targets)} venue")
    V=["source_platform","source_venue_id","venue_name","venue_url","address","city","latitude","longitude","categories","price_tier","rating","rating_count","phone","website","opening_hours","has_menu","menu_url","extraction_status","retrieved_at"]
    I=["source_platform","source_venue_id","venue_name","venue_url","menu_section","item_name","item_description","raw_price","normalized_price_eur","currency","price_type","item_type","normalized_product","confidence","allergens","retrieved_at","source_url"]
    venues=[]; items=[]; hits=0
    for i,(n,w,lat,lon) in enumerate(targets,1):
        try: rows,used=scrape(n,w)
        except Exception: rows,used=[],w
        venues.append({"source_platform":"direct_website","source_venue_id":w,"venue_name":n,"venue_url":w,
            "address":"","city":"Milano","latitude":lat,"longitude":lon,"categories":"","price_tier":"",
            "rating":"","rating_count":"","phone":"","website":w,"opening_hours":"","has_menu":"True" if rows else "False",
            "menu_url":used if rows else "","extraction_status":"ok" if rows else "no_menu","retrieved_at":NOW})
        if rows: hits+=1; items.extend(rows)
        if rows: print(f"  [{i}/{len(targets)}] {n[:30]:<30} {len(rows)} items")
        if i%20==0:
            _save(OUT_V,V,venues); _save(OUT_I,I,items); print(f"  ...salvato ({i}) hit={hits} items={len(items)}")
    _save(OUT_V,V,venues); _save(OUT_I,I,items)
    print(f"\nFATTO. {hits}/{len(targets)} venue con prezzi, {len(items)} items totali")

def _save(path,cols,rows):
    os.makedirs("raw_sources",exist_ok=True)
    with open(path,"w",newline="",encoding="utf-8-sig") as f:
        w=csv.DictWriter(f,fieldnames=cols); w.writeheader(); w.writerows(rows)

if __name__=="__main__":
    try: main()
    except KeyboardInterrupt: sys.exit(1)
