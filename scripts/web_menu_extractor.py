"""
web_menu_extractor.py — Nome venue → sito web → menu prezzi
============================================================
Per ogni venue nuovo (da comune_osm_venues.csv senza dati prezzi):
  1. Cerca il sito ufficiale via Startpage (parsing risultati Google)
  2. Visita sito + eventuale pagina /menu + PDF linkati
  3. Estrae drink+prezzi (JSON-LD, PDF pdfplumber, scan €)
  4. Output → raw_sources/web_extracted_venues.csv + _menu_items.csv

Resume: checkpoint su disco, ri-eseguibile.
"""
from __future__ import annotations
import csv, re, json, hashlib, io, time, random, sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote, urlparse, urljoin

import requests
from bs4 import BeautifulSoup
try:
    import pdfplumber
    HAS_PDF = True
except ImportError:
    HAS_PDF = False
import urllib3
urllib3.disable_warnings()

OUT  = Path("raw_sources")
RAW  = Path("raw_data_webextract"); RAW.mkdir(exist_ok=True)
CHECKPOINT = Path("web_extract_checkpoint.txt")
NOW = datetime.now(timezone.utc).isoformat()

HEADERS = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
                         "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
           "Accept-Language": "it-IT,it;q=0.9"}

MAX_VENUES = 672
SEARCH_DELAY = (3.0, 6.0)   # delay tra ricerche Startpage (anti rate-limit)

# Domini da ignorare (aggregatori, blog, social, directory)
SKIP_DOMAINS = [
    "tripadvisor","facebook","instagram","thefork","google","yelp","foursquare","mapquest",
    "quandoo","startpage","mojeek","wikipedia","youtube","linkedin","twitter","x.com",
    "bargiornale","scattidigusto","misterimprese","paginegialle","2gis","virgilio",
    "comune.milano","dissapore","gamberorosso","milanotoday","coqtailmilano","zero.eu",
    "restaurantguru","ufficiocamerale","electomagazine","le-strade","cibvs","improntabirraia",
    "rockfork","cocktailsandcarryons","fashionancien","operamylove","timeout","thrillist",
    "deliveroo","glovo","justeat","ubereats","theknot","booking","expedia","yelp",
    "infobel","cylex","europages","hotfrog","wheretraveler","atmosphere","mapcarta",
    "buttondown","mastodon","blocksurvey","torproject","trustpilot","trovaprezzi",
    "treatwell","vincicasa","sluurpy","piatti.menu","prenotazione","thefork","theknot",
    "restaurant.guru","misterimprese","cibo360","ilcittadinomb","aroundtheworld",
    "happycow","wanderlog","komoot","tabelog","retailmenot","groupon","tuttocitta",
]

# ─── Product normalization ───
PRODUCT_RULES = [
    (r"\bspritz\b","spritz"),(r"\bnegroni\b","negroni"),(r"\bamericano\b","americano"),
    (r"\bgin\s*[&e]?\s*tonic\b","gin_tonic"),(r"\bmoscow\s*mule\b","moscow_mule"),
    (r"\bmargarita\b","margarita"),(r"\bmojito\b","mojito"),(r"\bmanhattan\b","manhattan"),
    (r"\bdaiquiri\b","daiquiri"),(r"\bespresso\b|\bcaff[eè]\b","espresso"),
    (r"\bcappuccino\b","cappuccino"),(r"\bcoca.?cola\b|\bfanta\b|\bbibita\b","soft_drink"),
    (r"\bacqua\b","water"),(r"\bcalice\b|\bvino.{0,10}(calice|bicchiere)\b","wine_glass"),
    (r"\bprosecco\b","prosecco_glass"),(r"\bmoretti\b","beer_moretti"),
    (r"\bheineken\b","beer_heineken"),(r"\bperoni\b|\bnastro\s*azzurro\b","beer_peroni"),
    (r"\bbirra?\s+alla\s+spina.{0,15}(piccol|0[,.]?[23]|33)","beer_draft_small"),
    (r"\bbirra?\s+alla\s+spina.{0,15}(medi|0[,.]?[45]|50)","beer_draft_medium"),
    (r"\bbirra?\s+(in\s+)?bottigli","beer_bottle"),
]
DRINK_NORM = {p for _,p in PRODUCT_RULES}
DRINK_SEC = re.compile(r"\b(cocktail|drink|aperitiv|birr|vini?|calici|analcolic|bevande|"
                       r"liquori|amari|digestiv|gin|rum|vodka|whisky|spritz|bollicine|prosecco)\b", re.I)
FOOD_SEC = re.compile(r"\b(pizza|burger|panino|piatt|antipast|prim[io]|second[io]|dolci|"
                      r"dessert|pasta|risotto|insalat|carne|pesce|fritto|hamburger|toast)\b", re.I)
PRICE_RE = re.compile(r"(?:€\s*)?(\d{1,3}[,\.]\d{1,2})\s*€?")

def norm_product(name):
    low=name.lower()
    for pat,prod in PRODUCT_RULES:
        if re.search(pat,low): return prod,"high"
    return "",("medium" if DRINK_SEC.search(low) else "low")

def parse_price(raw):
    if not raw: return None
    m=PRICE_RE.search(str(raw).strip())
    if m:
        try:
            p=float(m.group(1).replace(",","."))
            return p if 0.5<p<150 else None
        except ValueError: return None
    return None

# ─── Cache ───
def cpath(url): return RAW/(hashlib.md5(url.encode()).hexdigest()+".cache")
def cget(url):
    p=cpath(url)
    return p.read_text(encoding="utf-8",errors="replace") if p.exists() else None
def cput(url,txt):
    try: cpath(url).write_text(txt,encoding="utf-8")
    except: pass

session=requests.Session(); session.headers.update(HEADERS)

def fetch(url,timeout=10):
    c=cget(url)
    if c is not None: return c
    try:
        r=session.get(url,timeout=timeout,verify=False)
        if r.status_code==200:
            cput(url,r.text); return r.text
    except Exception: pass
    return None

# ─── Step A: trova sito ufficiale ───
def find_official_site(venue_name, address=""):
    # query con nome + Milano
    clean_name=re.sub(r"\[.*?\]","",venue_name).strip()
    query=f"{clean_name} Milano"
    url=f"https://www.startpage.com/sp/search?query={quote(query)}"
    html=fetch(url,timeout=12)
    if not html: return ""
    soup=BeautifulSoup(html,"lxml")
    name_tokens=set(re.findall(r"[a-z0-9]{3,}",clean_name.lower()))
    cands=[]
    for a in soup.find_all("a",href=True):
        h=a["href"]
        if not h.startswith("http"): continue
        dom=urlparse(h).netloc.lower()
        if not dom or "." not in dom: continue
        if any(s in h.lower() for s in SKIP_DOMAINS): continue
        cands.append(h)
    cands=list(dict.fromkeys(cands))
    # Preferisci dominio che contiene parte del nome
    for h in cands:
        dom=urlparse(h).netloc.lower()
        if any(tok in dom for tok in name_tokens if len(tok)>=4):
            return h
    # Altrimenti primo .it
    for h in cands:
        if urlparse(h).netloc.lower().endswith(".it"): return h
    return cands[0] if cands else ""

# ─── Step B: estrai menu da sito ───
def extract_from_site(site_url, vid, vname):
    items=[]; seen=set()
    def add(sec,name,desc,raw,src,conf_boost=0):
        prod,conf=norm_product(name)
        is_drink=bool(DRINK_SEC.search(sec) or DRINK_SEC.search(name) or prod in DRINK_NORM)
        if not is_drink: return
        if FOOD_SEC.search(sec) and not DRINK_SEC.search(sec) and not prod: return
        price=parse_price(raw)
        key=(name.lower(),raw)
        if not name or len(name)<3 or key in seen: return
        seen.add(key)
        items.append({"source_platform":"web_extract","source_venue_id":vid,"venue_name":vname,
            "venue_url":site_url,"menu_section":sec,"item_name":name,"item_description":desc,
            "raw_price":raw,"normalized_price_eur":price if price is not None else "",
            "currency":"EUR","price_type":"menu","item_type":"drink","normalized_product":prod,
            "confidence":conf,"allergens":"","retrieved_at":NOW,"source_url":src})

    html=fetch(site_url)
    if not html: return items, site_url
    soup=BeautifulSoup(html,"lxml")

    # trova pagina menu dedicata
    menu_re=re.compile(r"\b(men[uù]|carta|drink|cocktail|prezzi|bevande|listino)\b",re.I)
    menu_url=site_url
    for a in soup.find_all("a",href=True):
        h=a["href"]; txt=a.get_text()
        if (menu_re.search(txt) or menu_re.search(h)) and ".pdf" not in h.lower() and menu_url==site_url:
            if h.startswith("http") and urlparse(h).netloc==urlparse(site_url).netloc:
                menu_url=h
            elif h.startswith("/"):
                menu_url=urljoin(site_url,h)

    pages_html=[(site_url,html)]
    if menu_url!=site_url:
        mh=fetch(menu_url)
        if mh: pages_html.append((menu_url,mh))

    # probe path comuni di menu (siti JS-rendered non espongono i link nell'HTML statico)
    base=f"{urlparse(site_url).scheme}://{urlparse(site_url).netloc}"
    COMMON_PATHS=["/drinks","/drink","/drink-list","/menu","/menu-drink","/carta","/la-carta",
                  "/cocktail","/cocktail-list","/beverage","/bevande","/listino","/drink-menu",
                  "/i-nostri-drink","/cocktails","/bar","/menu-bar"]
    visited={u for u,_ in pages_html}
    for path in COMMON_PATHS:
        cand=base+path
        if cand in visited: continue
        ph=fetch(cand)
        if ph and len(ph)>500:
            pages_html.append((cand,ph)); visited.add(cand)

    # raccogli PDF da TUTTE le pagine visitate
    pdf_urls=[]
    for src,h in pages_html:
        sp=BeautifulSoup(h,"lxml")
        for a in sp.find_all("a",href=True):
            href=a["href"]
            if ".pdf" in href.lower():
                pdf_urls.append(href if href.startswith("http") else urljoin(src,href))

    # parse PDF — gestione layout multi-colonna (più item per riga)
    if HAS_PDF:
        for pu in list(dict.fromkeys(pdf_urls))[:4]:
            try:
                r=session.get(pu,timeout=20,verify=False)
                if r.status_code!=200: continue
                with pdfplumber.open(io.BytesIO(r.content)) as pdf:
                    sec="Menu"
                    for pg in pdf.pages:
                        for line in (pg.extract_text() or "").splitlines():
                            line=line.strip()
                            if not line: continue
                            if len(line)<40 and line.isupper() and not PRICE_RE.search(line):
                                sec=line.title(); continue
                            # estrai TUTTE le coppie (nome, prezzo) sulla riga
                            matches=list(PRICE_RE.finditer(line))
                            if not matches: continue
                            prev=0
                            for m in matches:
                                chunk=line[prev:m.start()].strip(" -–·.\t|")
                                nm=re.sub(r"\s{2,}"," ",chunk).strip()
                                if len(nm)>=3:
                                    add(sec,nm,"",m.group(0).strip(),pu)
                                prev=m.end()
            except Exception: pass

    # parse HTML pages
    for src,h in pages_html:
        s=BeautifulSoup(h,"lxml")
        # JSON-LD
        for script in s.find_all("script",type="application/ld+json"):
            try:
                d=json.loads(script.string or ""); schemas=d if isinstance(d,list) else [d]
                for sc in schemas:
                    menus=sc.get("menu",[]) if isinstance(sc.get("menu",[]),list) else []
                    if sc.get("@type")=="Menu": menus=[sc]
                    for mo in menus:
                        if not isinstance(mo,dict): continue
                        for sec in mo.get("hasMenuSection",[]):
                            sn=sec.get("name","Menu")
                            for e in sec.get("hasMenuItem",[]):
                                offer=e.get("offers",{})
                                pv=offer.get("price","") if isinstance(offer,dict) else ""
                                add(sn,e.get("name","").strip(),e.get("description","").strip()[:100],str(pv),src)
            except Exception: pass
        # €-scan
        for el in s.find_all(string=re.compile(r"€\s*\d|\d[,\.]\d{2}\s*€")):
            par=el.parent
            if not par: continue
            row=par.find_parent(["tr","li","div","article","p"])
            if not row: continue
            texts=[t.strip() for t in row.stripped_strings if t.strip()]
            if len(texts)>=2:
                ctx=" ".join(texts)
                if FOOD_SEC.search(ctx) and not DRINK_SEC.search(ctx): continue
                add("Menu",texts[0],"",str(el).strip(),src)

    return items, menu_url

# ─── Carica venue da processare ───
def load_targets():
    targets=[]
    known=set()
    for vf in ["mycia_venues.csv","leggimenu_venues.csv","direct_venues.csv",
               "menudigitale_venues.csv","scraper_venues.csv","pdf_venues.csv",
               "pdf_googledork_venues.csv"]:
        p=OUT/vf
        if p.exists():
            with open(p,encoding="utf-8-sig") as f:
                for r in csv.DictReader(f):
                    n=re.sub(r"[^a-z0-9]","",r.get("venue_name","").lower())
                    if n: known.add(n)
    seen=set()
    with open(OUT/"comune_osm_venues.csv",encoding="utf-8") as f:
        for r in csv.DictReader(f):
            name=r.get("venue_name","")
            if name.startswith("[") or not name: continue
            nn=re.sub(r"[^a-z0-9]","",name.lower())
            if nn in known or nn in seen: continue
            seen.add(nn)
            targets.append(r)
    return targets

def main():
    targets=load_targets()
    print(f"Venue nuovi da processare: {len(targets)}")
    done=set(CHECKPOINT.read_text().splitlines()) if CHECKPOINT.exists() else set()
    print(f"Già fatti: {len(done)}")

    VF=["source_platform","source_venue_id","venue_name","venue_url","address","city","latitude",
        "longitude","categories","price_tier","rating","rating_count","phone","website",
        "opening_hours","has_menu","menu_url","extraction_status","retrieved_at"]
    IF=["source_platform","source_venue_id","venue_name","venue_url","menu_section","item_name",
        "item_description","raw_price","normalized_price_eur","currency","price_type","item_type",
        "normalized_product","confidence","allergens","retrieved_at","source_url"]

    new_v = not (OUT/"web_extracted_venues.csv").exists() or (OUT/"web_extracted_venues.csv").stat().st_size==0
    new_i = not (OUT/"web_extracted_menu_items.csv").exists() or (OUT/"web_extracted_menu_items.csv").stat().st_size==0
    vf=open(OUT/"web_extracted_venues.csv","a",newline="",encoding="utf-8")
    mf=open(OUT/"web_extracted_menu_items.csv","a",newline="",encoding="utf-8")
    vw=csv.DictWriter(vf,VF,extrasaction="ignore");
    mw=csv.DictWriter(mf,IF,extrasaction="ignore")
    if new_v: vw.writeheader()
    if new_i: mw.writeheader()

    sites_found=0; venues_with_menu=0; total_items=0; processed=0
    for t in targets[:MAX_VENUES]:
        name=t["venue_name"]
        vid=t.get("source_venue_id") or hashlib.md5(name.encode()).hexdigest()[:10]
        if vid in done: continue
        processed+=1
        sys.stdout.write(f"[{processed}] {name[:35]:35} ")
        sys.stdout.flush()

        site=find_official_site(name,t.get("address",""))
        status="no_site"; menu_url=""; items=[]
        if site:
            sites_found+=1
            sys.stdout.write(f"→ {urlparse(site).netloc[:30]:30} ")
            items,menu_url=extract_from_site(site,vid,name)
            status="ok_with_menu" if items else "site_no_menu"
        sys.stdout.write(f"[{len(items)} prezzi]\n"); sys.stdout.flush()

        if items:
            mw.writerows(items); mf.flush()
            total_items+=len(items); venues_with_menu+=1
        vw.writerow({"source_platform":"web_extract","source_venue_id":vid,"venue_name":name,
            "venue_url":site,"address":t.get("address",""),"city":"Milano",
            "latitude":t.get("latitude",""),"longitude":t.get("longitude",""),
            "categories":t.get("categories",""),"website":site,"has_menu":str(bool(items)),
            "menu_url":menu_url,"extraction_status":status,"retrieved_at":NOW})
        vf.flush()
        done.add(vid); CHECKPOINT.write_text("\n".join(done))
        time.sleep(random.uniform(*SEARCH_DELAY))

    vf.close(); mf.close()
    print(f"\n{'='*55}")
    print(f"Processati : {processed}")
    print(f"Siti trovati: {sites_found}")
    print(f"Con menu   : {venues_with_menu}")
    print(f"Prezzi tot : {total_items}")
    print(f"{'='*55}")

if __name__=="__main__":
    main()
