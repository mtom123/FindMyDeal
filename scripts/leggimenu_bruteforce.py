#!/usr/bin/env python3
"""
STEP 2 (PROMPT_PIETRO_S3) — leggimenu slug brute-force.
Genera slug candidati dai nomi bar, prova https://www.leggimenu.it/menu/{slug},
e sui HIT estrae gli items col metodo SERVER-SIDE giA' validato (pagine categoria
/menu/{slug}/{catid} -> bottoni .lmcart-add con data-price/data-title/data-cat,
fallback .prezzo1/.prezzo2). Geofiltro Milano. Cache. Salvataggi incrementali.

Uso:
  python scripts/leggimenu_bruteforce.py --limit 40    # campione (misura hit rate)
  python scripts/leggimenu_bruteforce.py               # full run (ore)
"""
import argparse, csv, json, os, re, sys, time, unicodedata
from datetime import datetime, timezone
import requests
from bs4 import BeautifulSoup

BASE = "https://www.leggimenu.it/menu/"
H = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"}
CACHE = "cache_leggimenu_s3"
SLEEP = 1.5
NOW = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
OUT_V = "raw_sources/leggimenu_s3_venues.csv"
OUT_I = "raw_sources/leggimenu_s3_menu_items.csv"
MAX_CATS = 60
NON_MILAN = ["torino","palermo","siena","parma","ferrara","lecce","trento","pessione",
             "roma","napoli","genova","venezia","rosa","aradeo","transacqua","lercara",
             "bologna","asti","firenze","bari","catania","verona","padova"]
VCOLS = ["source_platform","source_venue_id","venue_name","venue_url","address","city",
         "latitude","longitude","categories","price_tier","rating","rating_count","phone",
         "website","opening_hours","has_menu","menu_url","extraction_status","retrieved_at"]
ICOLS = ["source_platform","source_venue_id","venue_name","venue_url","menu_section",
         "item_name","item_description","raw_price","normalized_price_eur","currency",
         "price_type","item_type","normalized_product","confidence","allergens",
         "retrieved_at","source_url"]


def to_slugs(name):
    name = name.lower().strip()
    a = "".join(c for c in unicodedata.normalize("NFD", name) if unicodedata.category(c) != "Mn")
    out = []
    s1 = re.sub(r"[^a-z0-9]", "", a)
    if len(s1) > 3: out.append(s1)
    s2 = re.sub(r"[^a-z0-9]+", "-", a).strip("-")
    if s2 and s2 not in out: out.append(s2)
    clean = re.sub(r"\b(bar|pub|caffe|caffe|il|la|lo|i|gli|le|the|in|al|alla|del|della|di|da)\b", "", a)
    clean = re.sub(r"\s+", "", clean.strip())
    if len(clean) > 3 and clean not in out: out.append(clean)
    if "milano" not in a:
        s4 = re.sub(r"[^a-z0-9]", "", a) + "milano"
        if s4 not in out: out.append(s4)
    return out


def fetch(url):
    os.makedirs(CACHE, exist_ok=True)
    import hashlib
    p = os.path.join(CACHE, hashlib.sha256(url.encode()).hexdigest()[:24] + ".html")
    if os.path.exists(p):
        return open(p, encoding="utf-8").read(), open(p + ".url", encoding="utf-8").read() if os.path.exists(p+".url") else url, False
    try:
        time.sleep(SLEEP)
        r = requests.get(url, headers=H, timeout=10, allow_redirects=True)
    except requests.RequestException:
        return None, None, None
    if r.status_code == 429:
        return "429", None, None
    if r.status_code != 200:
        return None, None, False
    open(p, "w", encoding="utf-8").write(r.text)
    open(p + ".url", "w", encoding="utf-8").write(r.url)
    return r.text, r.url, False


def classify(name):
    t = name.lower()
    rules = [("moretti","beer_moretti"),("heineken","beer_heineken"),
             ("peroni","beer_peroni"),("nastro azzurro","beer_peroni"),
             ("spritz","spritz"),("negroni","negroni"),("moscow mule","moscow_mule"),
             ("gin tonic","gin_tonic"),("gin&tonic","gin_tonic"),("mojito","mojito"),
             ("margarita","margarita"),("daiquiri","daiquiri"),("manhattan","manhattan"),
             ("mojto","mojito"),("cappuccino","cappuccino")]
    for k,v in rules:
        if k in t: return v
    if "americano" in t and "caff" not in t: return "americano"
    if ("calice" in t or "bicchiere" in t) and "vino" in t: return "wine_glass"
    if "prosecco" in t and ("flute" in t or "calice" in t): return "prosecco_glass"
    if "espresso" in t or t.strip() in ("caffe","caffe'"): return "espresso"
    if any(w in t for w in ("coca","fanta","sprite","bibita")): return "soft_drink"
    if "acqua" in t: return "water"
    if "birra" in t or "beer" in t:
        if any(w in t for w in ("piccola","0,2","0.2","0,3","0.3","33","small")): return "beer_draft_small"
        if any(w in t for w in ("media","0,4","0.4","0,5","0.5","grande","large")): return "beer_draft_medium"
        return "beer_bottle"
    return ""


def price_block(b):
    h2 = b.find("h2")
    txt = (h2.get_text("", strip=True) if h2 else b.get_text("", strip=True)).replace(" ", "")
    m = re.search(r"(\d+(?:[.,]\d{1,2})?)", txt)
    if not m: return "", 0.0, ""
    sm = b.find("small")
    lab = sm.get_text(" ", strip=True) if sm else ""
    return "€" + m.group(1) + ((" "+lab) if lab else ""), float(m.group(1).replace(",",".")), lab


def parse_category(html, vname, vurl, slug, src):
    soup = BeautifulSoup(html, "html.parser")
    sec = ""
    st = soup.find(class_="menu-title")
    if st:
        t = re.sub(r"\s+"," ",st.get_text(" ",strip=True))
        if t and t not in ("-","Menu"): sec = t[:60]
    rows = []
    for card in soup.select(".card-style"):
        h2 = card.find("h2", class_=re.compile("font-18")) or card.find("h2")
        nm = re.sub(r"\s+"," ",h2.get_text(" ",strip=True)) if h2 else ""
        de = card.find("p", class_=re.compile("descrizione"))
        desc = re.sub(r"\s+"," ",de.get_text(" ",strip=True)) if de else ""
        btns = [b for b in card.select("[data-price]") if b.get("data-price")]
        if btns:
            for b in btns:
                pr = (b.get("data-price") or "").strip()
                try: val = float(pr.replace(",","."))
                except: val = 0.0
                title = re.sub(r"\s+"," ",(b.get("data-title") or nm)).strip()
                lab = (b.get("data-price-label") or "").strip()
                cat = (b.get("data-cat") or "").strip() or sec
                iname = f"{title} [{lab}]" if lab else title
                raw = (f"€{pr}"+(f" {lab}" if lab else "")) if pr else ""
                rows.append(_row(slug,vname,vurl,cat,iname,title,desc,raw,val,src))
            continue
        if not nm: continue
        blocks = card.select(".prezzo1, .prezzo2, .prezzo")
        prices = [price_block(b) for b in blocks]
        prices = [p for p in prices if p[1] > 0] or [("",0.0,"")]
        for raw,val,lab in prices:
            iname = f"{nm} — {lab}" if lab and len(prices)>1 else nm
            rows.append(_row(slug,vname,vurl,sec,iname,nm,desc,raw,val,src))
    return rows


def _row(slug,vname,vurl,sec,iname,base,desc,raw,val,src):
    prod = classify(base)
    return {"source_platform":"leggimenu","source_venue_id":slug,"venue_name":vname,
            "venue_url":vurl,"menu_section":sec,"item_name":iname,"item_description":desc,
            "raw_price":raw,"normalized_price_eur":val,"currency":"EUR","price_type":"menu",
            "item_type":"drink" if prod else "","normalized_product":prod,
            "confidence":"high" if val>0 else "low","allergens":"","retrieved_at":NOW,"source_url":src}


def jsonld(soup):
    name=lat=lon=addr=""
    for sc in soup.find_all("script", type="application/ld+json"):
        try: d=json.loads(sc.string)
        except: continue
        for o in (d if isinstance(d,list) else [d]):
            if not isinstance(o,dict): continue
            name=name or o.get("name","")
            a=o.get("address")
            if isinstance(a,dict):
                addr=", ".join(filter(None,[a.get("streetAddress",""),a.get("postalCode",""),a.get("addressLocality","")]))
            g=o.get("geo")
            if isinstance(g,dict):
                lat=str(g.get("latitude","")); lon=str(g.get("longitude",""))
    return name,lat,lon,addr


def save(venues, items, reset):
    os.makedirs("raw_sources", exist_ok=True)
    for path,cols,rows in [(OUT_V,VCOLS,venues),(OUT_I,ICOLS,items)]:
        mode = "w" if reset else "w"  # riscriviamo sempre il cumulativo
        with open(path, "w", newline="", encoding="utf-8-sig") as f:
            w=csv.DictWriter(f,fieldnames=cols); w.writeheader(); w.writerows(rows)


def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--limit",type=int,default=0); a=ap.parse_args()
    # esistenti
    ex=set()
    for r in csv.DictReader(open("raw_sources/leggimenu_venues.csv",encoding="utf-8-sig")):
        s=(r.get("venue_url","") or r.get("menu_url","")).split("/menu/")[-1].strip("/")
        if s: ex.add(s)
    import glob
    def valid_name(n):
        if len(n) < 4: return False
        if len(re.findall(r"[a-zA-Z]", n)) < 3: return False        # serve testo, non numeri
        if re.fullmatch(r"[\d\-_.: ]+", n): return False            # date/numeri puri
        return True
    names=set()
    for f in glob.glob("raw_sources/*_venues.csv"):
        if "comune_osm" in f or "menudigitale" in f or "mycia" in f:
            continue   # mycia/menudigitale gia coperti; comune_osm spesso senza nome reale
        for r in csv.DictReader(open(f,encoding="utf-8-sig")):
            n=(r.get("venue_name","") or "").strip()
            if n and not n.startswith("[") and valid_name(n): names.add(n)
    slugmap={}
    for n in sorted(names):
        for s in to_slugs(n):
            if s not in ex and s not in slugmap: slugmap[s]=n
    slugs=list(slugmap.items())
    if a.limit: slugs=slugs[:a.limit]
    print(f"Slug da provare: {len(slugs)} (da {len(names)} nomi)")

    venues, items = [], []
    hits=checked=0
    for slug,orig in slugs:
        html,finalurl,_=fetch(BASE+slug)
        checked+=1
        if checked % 300 == 0:    # checkpoint periodico (anche sui 404) — salva sempre
            save(venues,items,True); print(f"[{checked}/{len(slugs)}] checkpoint: hit={hits} items={len(items)}")
        if html=="429": print("429 -> sleep 120"); time.sleep(120); continue
        if not html or "/menu/" not in (finalurl or ""): continue
        soup=BeautifulSoup(html,"html.parser")
        name,lat,lon,addr=jsonld(soup)
        if not name:
            h1=soup.find("h1") or soup.find("title")
            name=h1.get_text(strip=True).split("|")[0].strip() if h1 else orig
        cats=list(dict.fromkeys(re.findall(rf"/menu/{re.escape(slug)}/(\d+)", html)))[:MAX_CATS]
        # SOFT-404: leggimenu ritorna HTTP 200 con titolo "404" per slug inesistenti.
        # Un venue reale ha un nome valido E almeno una categoria.
        if name.strip() in ("404","") or not cats:
            continue
        if addr and any(c in addr.lower() for c in NON_MILAN):
            print(f"  skip non-Milano: {name} ({addr[:30]})"); continue
        vit=[]
        for cid in cats:
            ch,_,_=fetch(f"{BASE}{slug}/{cid}")
            if ch=="429": time.sleep(120); continue
            if ch: vit.extend(parse_category(ch,name,BASE+slug,slug,f"{BASE}{slug}/{cid}"))
        hits+=1
        venues.append({"source_platform":"leggimenu","source_venue_id":slug,"venue_name":name,
            "venue_url":BASE+slug,"address":addr,"city":"Milano","latitude":lat or "45.4642",
            "longitude":lon or "9.1900","categories":"","price_tier":"","rating":"","rating_count":"",
            "phone":"","website":"","opening_hours":"","has_menu":"True" if vit else "False",
            "menu_url":BASE+slug,"extraction_status":"ok" if vit else "no_menu","retrieved_at":NOW})
        items.extend(vit)
        print(f"  HIT {slug} -> {name[:30]} | cats={len(cats)} items={len(vit)}")
        if hits % 10 == 0:        # salva ogni 10 hit (i dati preziosi)
            save(venues,items,True); print(f"[{checked}/{len(slugs)}] salvato. hit={hits} items={len(items)}")
    save(venues,items,True)
    print(f"\nFATTO. provati={checked} hit={hits} venues, items={len(items)}")
    print(f"hit rate: {hits*100//checked if checked else 0}% | output: {OUT_V}, {OUT_I}")


if __name__ == "__main__":
    try: main()
    except KeyboardInterrupt: sys.exit(1)
