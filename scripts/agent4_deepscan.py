#!/usr/bin/env python3
"""S4 — Deep menu re-scan delle venue gia' nel DB (estrazione parziale 1-3 item).
Ri-visita i source_url, applica i 22 pattern drink, quality-gate INLINE, dedup.
Output: raw_sources/agent4_deepscan_{venues,menu_items}.csv  Report: agent4_REPORT.md
Uso: python scripts/agent4_deepscan.py [--limit N] [--sample nome1,nome2]"""
import argparse, csv, io, os, re, sys, time, hashlib
from datetime import datetime, timezone
from urllib.parse import urljoin, urlparse
import requests
from bs4 import BeautifulSoup
try: import pdfplumber; HAVE_PDF=True
except ImportError: HAVE_PDF=False

H={"User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"}
CACHE="cache_agent4"; NOW=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
OUT_V="raw_sources/agent4_deepscan_venues.csv"; OUT_I="raw_sources/agent4_deepscan_menu_items.csv"
PATHS=["/menu","/drink","/drinks","/cocktail","/cocktails","/carta","/listino","/menu/cocktail","/menu/drink","/menu/bevande","/la-carta","/drinks-menu","/cocktail-list"]

DRINK_PATTERNS={
 'spritz': r'\b(spritz|aperol\s*spritz|campari\s*spritz|hugo\s*spritz|select\s*spritz|cynar\s*spritz)\b',
 'negroni': r'\b(negroni|negroni\s*sbagliato|boulevardier|negrosky)\b',
 'americano': r'\bamericano\b',
 'gin_tonic': r'\b(gin\s*tonic|gin\s*&\s*tonic|gin\s*\+\s*tonic|g\s*&\s*t)\b',
 'mojito': r'\b(mojito)\b',
 'moscow_mule': r'\b(moscow\s*mule|london\s*mule|mexican\s*mule|mediterranean\s*mule)\b',
 'margarita': r'\b(margarita|paloma)\b',
 'daiquiri': r'\b(daiquiri)\b',
 'manhattan': r'\b(manhattan|rob\s*roy)\b',
 'beer_moretti': r'\b(moretti)\b',
 'beer_heineken': r'\b(heineken)\b',
 'beer_peroni': r'\b(peroni|nastro\s*azzurro)\b',
 'beer_bottle': r'\b(corona|ichnusa|menabrea|baladin|beck.?s|guinness|kilkenny|tennent.?s|warsteiner|ipa|stout|weiss)\b',
 'beer_draft_small': r'((?:spina|birra)\s*piccola|piccola\s*(?:alla\s*)?spina|birra[^\n]{0,15}0[.,][23]\s*l\b|birra[^\n]{0,15}33\s*cl)',
 'beer_draft_medium': r'((?:spina|birra)\s*media|media\s*(?:alla\s*)?spina|birra[^\n]{0,15}0[.,][45]\s*l\b|birra[^\n]{0,15}(?:40|50)\s*cl)',
 'wine_glass': r'\b(calice\s*(?:di\s*)?vino|vino\s*al\s*calice|wine\s*glass|glass\s*of\s*wine|calice)\b',
 'prosecco_glass': r'\b(prosecco|flute)\b',
 'espresso': r'\b(caff[eè]|espresso)\b',
 'cappuccino': r'\b(cappuccino)\b',
 'soft_drink': r'\b(coca\s*cola|coca-cola|fanta|sprite|chinotto|schweppes|tonica|tonic\s*water|bibita)\b',
 'water': r'\b(acqua(?:\s*(?:naturale|frizzante|gassata|minerale))?)\b',
}
PRICE_RE=re.compile(r'€\s*(\d{1,2}(?:[,.]\d{1,2})?)|(?<!\d)(\d{1,2}(?:[,.]\d{1,2})?)\s*€')
FOOD=re.compile(r'\b(piatto|pasta|pizza|insalata|carne|pesce|risotto|antipasto|prim[oi]|second[oi]|dolce|dessert|tagliere|focaccia|panino|hamburger|tartare|frittura|bruschetta)\b',re.I)

def fetch(url, binary=False):
    os.makedirs(CACHE,exist_ok=True)
    p=os.path.join(CACHE,hashlib.sha256(url.encode()).hexdigest()[:24]+(".bin" if binary else ".html"))
    if os.path.exists(p): return open(p,"rb").read() if binary else open(p,encoding="utf-8",errors="replace").read()
    try:
        r=requests.get(url,headers=H,timeout=15,allow_redirects=True)
    except requests.RequestException: return None
    if r.status_code==429: return "429"
    if r.status_code!=200: return None
    if binary: open(p,"wb").write(r.content); return r.content
    open(p,"w",encoding="utf-8").write(r.text); return r.text

def fix_double(s):  # PDF HHAARRPP -> HARP
    return re.sub(r'([A-Za-z])\1', r'\1', s) if re.search(r'([A-Za-z])\1{1,}',s) and len(re.findall(r'([A-Za-z])\1',s))>3 else s

def quality(item):
    name=item['item_name']; desc=item.get('item_description',''); url=item.get('source_url','')
    prod=item['normalized_product']; t=(name+" "+desc).lower()
    try: price=float(item['normalized_price_eur'])
    except: price=0
    if any(url.lower().endswith(e) for e in ('.jpg','.jpeg','.png','.webp','.gif','.ico','.svg')): return False,'IMAGE_URL'
    if any(c in t for c in ('pessione','torino','palermo','siena','parma','ferrara','lecce','trento','san ferdinando')): return False,'NON_MILAN'
    if 'rovere americano' in t: return False,'OAK'
    if prod=='americano' and re.search(r'caff[eè]',t): return False,'COFFEE_NOT_COCKTAIL'
    if price<0.5 or price>80: return False,'PRICE_RANGE'
    if price>PMAX.get(prod,80): return False,'PRICE_TOO_HIGH_FOR_PRODUCT'
    if len(name)>150: return False,'NAME_LONG'
    if 'paginegialle' in url.lower(): return False,'PAGINEGIALLE'
    if FOOD.search(t): return False,'FOOD'
    if re.search(r'\b(personalizzazion|eventuali|supplement|coperto|servizio al tavolo|aggiunt[ae])\b',t): return False,'MENU_NOTE'
    return True,None

# prezzo massimo plausibile per prodotto (un calice/caffè non costa come una bottiglia)
PMAX={'prosecco_glass':18,'wine_glass':25,'espresso':3.5,'cappuccino':5,'water':6,'soft_drink':8,
      'spritz':18,'negroni':22,'americano':18,'gin_tonic':22,'mojito':20,'moscow_mule':20,
      'margarita':22,'daiquiri':22,'manhattan':25,'beer_draft_small':9,'beer_draft_medium':12,
      'beer_bottle':15,'beer_moretti':12,'beer_heineken':12,'beer_peroni':12}

def extract(text, vid, vname, src, platform, is_pdf=False):
    if is_pdf: text=fix_double(text)
    lines=[re.sub(r'\s+',' ',l).strip() for l in re.split(r'\n+|<br/?>',text) if l.strip()]
    items=[]; rej={}
    for i,line in enumerate(lines):
        if len(line)<4 or len(line)>120: continue
        # CLASSIFICA SULLA RIGA (il nome dell'item), non sul window — evita falsi positivi
        prod=classify_name(line)
        if not prod: continue
        # prezzo: nella riga stessa, altrimenti nella riga successiva
        pm=PRICE_RE.findall(line)
        if not pm and i+1<len(lines): pm=PRICE_RE.findall(lines[i+1])
        ps=next((m[0] or m[1] for m in pm if (m[0] or m[1])),None) if pm else None
        if not ps: continue
        try: price=float(ps.replace(',','.'))
        except: continue
        if price>PMAX.get(prod,80): rej['PRICE_TOO_HIGH_FOR_PRODUCT']=rej.get('PRICE_TOO_HIGH_FOR_PRODUCT',0)+1; continue
        it={"source_platform":platform,"source_venue_id":vid,"venue_name":vname,"venue_url":src,
            "menu_section":"","item_name":line[:80],"item_description":line[:200],
            "raw_price":f"€ {ps}","normalized_price_eur":price,"currency":"EUR","price_type":"menu",
            "item_type":"drink","normalized_product":prod,"confidence":"medium","allergens":"",
            "retrieved_at":NOW,"source_url":src}
        ok,why=quality(it)
        if ok: items.append(it)
        else: rej[why]=rej.get(why,0)+1
    seen=set(); uniq=[]
    for it in items:
        k=(it['normalized_product'],it['normalized_price_eur'])
        if k not in seen: seen.add(k); uniq.append(it)
    return uniq,rej

def platform_of(url):
    h=urlparse(url).netloc.lower()
    if "leggimenu" in h: return "leggimenu","2"
    if "mycia" in h: return "mycia","2"
    if "eatbu" in h: return "eatbu","2.5"
    return "direct_website","2.5"

def classify_name(name):
    """Mappa un nome item su un prodotto target (per ri-classificazione mycia)."""
    t=name.lower()
    if FOOD.search(t): return ''
    for prod,pat in DRINK_PATTERNS.items():
        if re.search(pat,t,re.I):
            if prod=='americano' and re.search(r'caff[eè]',t): continue
            if 'rovere' in t: continue
            return prod
    return ''

_MYCIA=None
def mycia_local(vname, venue_url):
    """Recupera i drink mancanti dai dati mycia gia' scaricati (ri-classifica)."""
    global _MYCIA
    if _MYCIA is None:
        _MYCIA={}
        try:
            for r in csv.DictReader(open("raw_sources/mycia_menu_items.csv",encoding="utf-8-sig")):
                _MYCIA.setdefault((r['venue_name'] or '').lower().strip(),[]).append(r)
        except FileNotFoundError: pass
    out=[]
    for r in _MYCIA.get(vname.lower().strip(),[]):
        prod=classify_name(r.get('item_name',''))
        if not prod: continue
        try: price=float(r.get('normalized_price_eur') or 0)
        except: price=0
        if price<=0: continue
        it={"source_platform":"mycia","source_venue_id":vname.lower().replace(' ','_'),
            "venue_name":vname,"venue_url":venue_url,"menu_section":r.get('menu_section',''),
            "item_name":(r.get('item_name','') or '')[:80],"item_description":(r.get('item_name','') or '')[:200],
            "raw_price":r.get('raw_price','') or f"€ {price}","normalized_price_eur":price,"currency":"EUR",
            "price_type":"menu","item_type":"drink","normalized_product":prod,"confidence":"medium",
            "allergens":"","retrieved_at":NOW,"source_url":r.get('source_url','') or venue_url}
        ok,_=quality(it)
        if ok: out.append(it)
    seen=set(); uniq=[]
    for it in out:
        k=(it['normalized_product'],it['normalized_price_eur'])
        if k not in seen: seen.add(k); uniq.append(it)
    return uniq

def leggimenu_cats(slug_url, vname):
    """Estrae i drink da TUTTE le pagine categoria leggimenu (server-side)."""
    m=re.search(r'/menu/([^/?#]+)',slug_url);
    if not m: return []
    slug=m.group(1); base=f"https://www.leggimenu.it/menu/{slug}"
    vp=fetch(base)
    if vp in (None,"429"): return []
    cats=list(dict.fromkeys(re.findall(rf"/menu/{re.escape(slug)}/(\d+)",vp)))[:60]
    out=[]
    for cid in cats:
        ch=fetch(f"{base}/{cid}")
        if ch in (None,"429"): time.sleep(2); continue
        soup=BeautifulSoup(ch,"html.parser")
        for card in soup.select(".card-style"):
            for b in card.select("[data-price]"):
                pr=(b.get("data-price") or "").strip()
                try: price=float(pr.replace(",","."))
                except: continue
                title=re.sub(r"\s+"," ",(b.get("data-title") or "")).strip()
                prod=classify_name(title)
                if not prod or price<=0: continue
                it={"source_platform":"leggimenu","source_venue_id":vname.lower().replace(' ','_'),
                    "venue_name":vname,"venue_url":base,"menu_section":(b.get("data-cat") or ""),
                    "item_name":title[:80],"item_description":title[:200],"raw_price":f"€{pr}",
                    "normalized_price_eur":price,"currency":"EUR","price_type":"menu","item_type":"drink",
                    "normalized_product":prod,"confidence":"medium","allergens":"","retrieved_at":NOW,"source_url":f"{base}/{cid}"}
                ok,_=quality(it)
                if ok: out.append(it)
        time.sleep(2)
    seen=set(); uniq=[]
    for it in out:
        k=(it['normalized_product'],it['normalized_price_eur'])
        if k not in seen: seen.add(k); uniq.append(it)
    return uniq

def process_venue(t, rej_total):
    vname=t['venue_name']; vid=vname.lower().replace(' ','_')
    urls=[u for u in (t.get('source_urls','') or '').split('|') if u.strip()]
    allitems=[]
    for src in urls:
        plat,delay=platform_of(src)
        # ROUTING per piattaforma (mycia/leggimenu hanno estrazione dedicata)
        if plat=="mycia":
            allitems+=mycia_local(vname, src); continue
        if plat=="leggimenu":
            allitems+=leggimenu_cats(src, vname); continue
        is_pdf=src.lower().endswith('.pdf')
        if is_pdf:
            c=fetch(src,binary=True)
            if c in (None,"429"): continue
            if HAVE_PDF:
                try:
                    with pdfplumber.open(io.BytesIO(c)) as pdf:
                        txt="\n".join((pg.extract_text() or "") for pg in pdf.pages[:15])
                    its,rej=extract(txt,vid,vname,src,plat,is_pdf=True); allitems+=its
                    for k,v in rej.items(): rej_total[k]=rej_total.get(k,0)+v
                except Exception: pass
            time.sleep(1); continue
        html=fetch(src)
        if html in (None,"429"): continue
        soup=BeautifulSoup(html,"html.parser")
        for tag in soup(["script","style"]): tag.decompose()
        its,rej=extract(soup.get_text("\n"),vid,vname,src,plat); allitems+=its
        for k,v in rej.items(): rej_total[k]=rej_total.get(k,0)+v
        # PDF nella pagina + path-probing se poco
        if len(its)<3:
            pdfs=[urljoin(src,a['href']) for a in soup.find_all('a',href=True) if a['href'].lower().endswith('.pdf')]
            for pu in pdfs[:2]:
                c=fetch(pu,binary=True);
                if c in (None,"429") or not HAVE_PDF: continue
                try:
                    with pdfplumber.open(io.BytesIO(c)) as pdf:
                        txt="\n".join((pg.extract_text() or "") for pg in pdf.pages[:15])
                    its2,rej2=extract(txt,vid,vname,pu,plat,is_pdf=True); allitems+=its2
                except Exception: pass
                time.sleep(1)
            base=f"{urlparse(src).scheme}://{urlparse(src).netloc}"
            for path in PATHS[:6]:
                if plat in ("leggimenu","mycia"): break
                h2=fetch(base+path)
                if h2 in (None,"429"): continue
                s2=BeautifulSoup(h2,"html.parser")
                for tag in s2(["script","style"]): tag.decompose()
                its3,rej3=extract(s2.get_text("\n"),vid,vname,base+path,plat); allitems+=its3
                time.sleep(float(delay))
        time.sleep(float(delay))
    # dedup finale
    seen=set(); uniq=[]
    for it in allitems:
        k=(it['normalized_product'],it['normalized_price_eur'])
        if k not in seen: seen.add(k); uniq.append(it)
    return vid,uniq

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--limit",type=int,default=0); ap.add_argument("--sample",default=""); a=ap.parse_args()
    targets=list(csv.DictReader(open("PIETRO_S4_TARGETS.csv",encoding="utf-8-sig")))
    targets.sort(key=lambda x:int(x['current_items']))
    if a.sample: targets=[t for t in targets if t['venue_name'] in a.sample.split(',')]
    elif a.limit: targets=targets[:a.limit]
    VCOLS=["source_platform","source_venue_id","venue_name","venue_url","address","city","latitude","longitude","categories","price_tier","rating","rating_count","phone","website","opening_hours","has_menu","menu_url","extraction_status","retrieved_at"]
    ICOLS=["source_platform","source_venue_id","venue_name","venue_url","menu_section","item_name","item_description","raw_price","normalized_price_eur","currency","price_type","item_type","normalized_product","confidence","allergens","retrieved_at","source_url"]
    venues=[]; items=[]; rej_total={}
    for i,t in enumerate(targets,1):
        vid,its=process_venue(t,rej_total)
        plat=(t.get('platforms','') or 'direct_website').replace('|',';').split(';')[0]
        venues.append({"source_platform":plat,"source_venue_id":vid,"venue_name":t['venue_name'],
            "venue_url":(t.get('source_urls','') or '').split('|')[0],"address":"","city":"Milano",
            "latitude":t.get('lat',''),"longitude":t.get('lon',''),"categories":"","price_tier":"",
            "rating":"","rating_count":"","phone":"","website":"","opening_hours":"",
            "has_menu":"True" if its else "False","menu_url":(t.get('source_urls','') or '').split('|')[0],
            "extraction_status":"ok" if its else "no_menu","retrieved_at":NOW})
        items+=its
        print(f"  [{i}/{len(targets)}] {t['venue_name'][:26]:<26} was={t['current_items']} +{len(its)} drink")
        if i%15==0:
            _w(OUT_V,VCOLS,venues); _w(OUT_I,ICOLS,items)
    _w(OUT_V,VCOLS,venues); _w(OUT_I,ICOLS,items)
    print(f"\nFATTO. venue={len(venues)} | items estratti (post-QG)={len(items)} | rifiutati={rej_total}")

def _w(path,cols,rows):
    os.makedirs("raw_sources",exist_ok=True)
    with open(path,"w",newline="",encoding="utf-8-sig") as f:
        w=csv.DictWriter(f,fieldnames=cols); w.writeheader(); w.writerows(rows)

if __name__=="__main__":
    try: main()
    except KeyboardInterrupt: sys.exit(1)
