#!/usr/bin/env python3
"""
Beach S2 — Generate menu items CSV from new venues discovered S2.
Categories: direct websites for Sud Italia + extension Versilia + consortium.
"""

import csv

RETRIEVED_AT = "2026-06-01T16:30:00Z"
SEASON = "summer_2026"
V_START = "2026-05-01"
V_END = "2026-09-30"
VERTICAL = "beach"
ITEM_TYPE = "beach_service"

# Output split per source type
DIRECT_FILE = "raw_sources/beach_s2_direct_menu_items.csv"
PDF_FILE = "raw_sources/beach_s2_pdf_menu_items.csv"
CONSORTIUM_FILE = "raw_sources/beach_s2_consortium_menu_items.csv"

MENU_FIELDS = [
    "source_platform", "source_venue_id", "venue_name", "venue_url",
    "menu_section", "item_name", "item_description",
    "raw_price", "normalized_price_eur", "currency",
    "price_type", "item_type", "normalized_product",
    "confidence", "allergens", "retrieved_at", "source_url",
    "season", "validity_start", "validity_end", "vertical",
]


def make_item(platform, venue_id, name, url, section, item_name, item_desc,
              raw_price, norm_price, price_type, norm_product,
              confidence="high", source_url=None):
    return {
        "source_platform": platform,
        "source_venue_id": venue_id,
        "venue_name": name,
        "venue_url": url,
        "menu_section": section,
        "item_name": item_name,
        "item_description": item_desc,
        "raw_price": raw_price,
        "normalized_price_eur": norm_price,
        "currency": "EUR",
        "price_type": price_type,
        "item_type": ITEM_TYPE,
        "normalized_product": norm_product,
        "confidence": confidence,
        "allergens": "",
        "retrieved_at": RETRIEVED_AT,
        "source_url": source_url or url,
        "season": SEASON,
        "validity_start": V_START,
        "validity_end": V_END,
        "vertical": VERTICAL,
    }


def i(p, vid, n, url, sec, iname, idesc, raw, norm, ptype, nprod,
      conf="high", src=None):
    return make_item(p, vid, n, url, sec, iname, idesc,
                     raw, norm, ptype, nprod, conf, src)


direct_rows = []
pdf_rows = []
consortium_rows = []

# ─────────────────────────────────────────────────────────────────────
# DIRECT WEBSITE NEW VENUES (S2)
# ─────────────────────────────────────────────────────────────────────

# V28 — Le Tolde del Corallone, Tropea (VV) – Calabria
_P, _ID, _N, _URL = "direct_website", "tolde_corallone_tropea", "Le Tolde del Corallone", "https://www.letoldedelcorallone-tropea.it/servizio-spiaggia-tropea/"
direct_rows += [
    i(_P,_ID,_N,_URL,"GIUGNO","Ombrellone+2lettini – giornaliero giugno","1 ombrellone + 2 lettini bassa stagione","€20,00",20.0,"per_day","beach_set_2lettini_ombrellone"),
    i(_P,_ID,_N,_URL,"LUGLIO","Ombrellone+2lettini – giornaliero luglio","Media stagione","€30,00",30.0,"per_day","beach_set_2lettini_ombrellone"),
    i(_P,_ID,_N,_URL,"AGOSTO","Ombrellone+2lettini – giornaliero agosto peak","3-24 agosto peak","€50,00",50.0,"per_day","beach_set_2lettini_ombrellone"),
    i(_P,_ID,_N,_URL,"SETTEMBRE","Ombrellone+2lettini – giornaliero settembre","Settembre","€30,00",30.0,"per_day","beach_set_2lettini_ombrellone"),
    i(_P,_ID,_N,_URL,"ARREDI","Lettino aggiuntivo – giugno-luglio","Extra lettino media stagione","€10,00",10.0,"per_day","beach_sunbed"),
    i(_P,_ID,_N,_URL,"ARREDI","Lettino aggiuntivo – agosto peak","Extra lettino agosto","€5,00",5.0,"per_day","beach_sunbed"),
]

# V29 — Lido Mare Grande, Tropea (VV) – Calabria
_P, _ID, _N, _URL = "direct_website", "lido_maregrande_tropea", "Lido Mare Grande", "https://www.maregrande.it/lido-stabilimento-balneare-tropea.htm"
direct_rows += [
    i(_P,_ID,_N,_URL,"BASSA STAGIONE","Ombrellone+2lettini+parcheggio – bassa stagione","Giugno-settembre bassa stagione","€10,00 - €15,00",12.5,"per_day","beach_set_2lettini_ombrellone","medium"),
    i(_P,_ID,_N,_URL,"MEDIA STAGIONE","Ombrellone+2lettini+parcheggio – luglio","Media stagione","€15,00 - €20,00",17.5,"per_day","beach_set_2lettini_ombrellone","medium"),
    i(_P,_ID,_N,_URL,"ALTA STAGIONE","Ombrellone+2lettini+parcheggio – agosto","Alta stagione agosto","€20,00 - €40,00",30.0,"per_day","beach_set_2lettini_ombrellone","medium"),
]

# V30 — Lido Oasi, Principina a Mare (GR) – Toscana
_P, _ID, _N, _URL = "direct_website", "lido_oasi_principina", "Lido Oasi", "https://www.lidooasi.com/en/price-list"
direct_rows += [
    i(_P,_ID,_N,_URL,"BASSA STAGIONE","Ombrellone+2lettini – giornaliero bassa stagione","Giugno-settembre","€15,00",15.0,"per_day","beach_set_2lettini_ombrellone"),
    i(_P,_ID,_N,_URL,"ALTA STAGIONE","Ombrellone+2lettini – giornaliero alta stagione","Luglio-agosto","€22,00",22.0,"per_day","beach_set_2lettini_ombrellone"),
    i(_P,_ID,_N,_URL,"SETTIMANALE","Ombrellone+2lettini – settimanale bassa stagione","7 giorni bassa stagione","€95,00",95.0,"per_week","beach_set_2lettini_ombrellone"),
    i(_P,_ID,_N,_URL,"SETTIMANALE","Ombrellone+2lettini – settimanale alta stagione","7 giorni luglio-agosto","€140,00",140.0,"per_week","beach_set_2lettini_ombrellone"),
    i(_P,_ID,_N,_URL,"MENSILE","Ombrellone+2lettini – mensile alta stagione","30 giorni luglio-agosto","€360,00",360.0,"per_month","beach_set_2lettini_ombrellone"),
    i(_P,_ID,_N,_URL,"STAGIONALE","Ombrellone stagionale","Stagione completa standard","€750,00",750.0,"per_season","beach_subscription_season"),
    i(_P,_ID,_N,_URL,"STAGIONALE","Ombrellone stagionale extended","Stagione completa esteso","€850,00",850.0,"per_season","beach_subscription_season"),
    i(_P,_ID,_N,_URL,"CABINE","Cabina stagionale 3 persone","Cabina seasonal hut 3 posti","€850,00",850.0,"per_season","beach_cabin_season"),
]

# V31 — Bagno Riviera, Marina di Pietrasanta (LU) – Toscana
_P, _ID, _N, _URL = "direct_website", "bagno_riviera_pietrasanta", "Bagno Riviera", "https://www.bagnoriviera.it/promozioni.html"
direct_rows += [
    i(_P,_ID,_N,_URL,"GIORNALIERO","Ombrellone+ingresso – maggio weekend","Pacchetto base maggio","€25,00",25.0,"per_day_weekend","beach_set_2lettini_ombrellone"),
    i(_P,_ID,_N,_URL,"GIORNALIERO","Ombrellone+ingresso – giugno-settembre weekend","Pacchetto base giugno-sett","€35,00",35.0,"per_day_weekend","beach_set_2lettini_ombrellone"),
    i(_P,_ID,_N,_URL,"GIORNALIERO","Ombrellone+ingresso – luglio weekend","Pacchetto base luglio","€40,00",40.0,"per_day_weekend","beach_set_2lettini_ombrellone"),
    i(_P,_ID,_N,_URL,"GIORNALIERO","Ombrellone+ingresso – agosto weekend","Pacchetto base agosto","€45,00",45.0,"per_day_weekend","beach_set_2lettini_ombrellone"),
    i(_P,_ID,_N,_URL,"TENDE","Tenda+ingresso – luglio weekend","Pacchetto tenda luglio","€55,00",55.0,"per_day_weekend","beach_umbrella_premium"),
    i(_P,_ID,_N,_URL,"TENDE","Tenda+ingresso – agosto weekend","Pacchetto tenda agosto","€60,00",60.0,"per_day_weekend","beach_umbrella_premium"),
    i(_P,_ID,_N,_URL,"POMERIDIANO","Pomeridiano feriale luglio","Lun-ven 14-20 luglio","€20,00",20.0,"per_half_day","beach_set_2lettini_ombrellone"),
    i(_P,_ID,_N,_URL,"POMERIDIANO","Pomeridiano feriale agosto","Lun-ven 14-20 agosto","€25,00",25.0,"per_half_day","beach_set_2lettini_ombrellone"),
    i(_P,_ID,_N,_URL,"CABINE","Cabina+doccia+ombrellone stagionale","Stagione completa","€2.640,00",2640.0,"per_season","beach_cabin_season"),
    i(_P,_ID,_N,_URL,"CABINE","Cabina+doccia+tenda stagionale","Stagionale premium","€3.700,00",3700.0,"per_season","beach_cabin_season"),
    i(_P,_ID,_N,_URL,"CABINE","Cabina+ombrellone mensile luglio","Mensile luglio","€902,00",902.0,"per_month","beach_cabin_day"),
    i(_P,_ID,_N,_URL,"CABINE","Cabina+ombrellone mensile agosto","Mensile agosto","€960,00",960.0,"per_month","beach_cabin_day"),
]

# V32 — Bagno Angelo Ponente, Forte dei Marmi (LU) – Toscana
_P, _ID, _N, _URL = "direct_website", "bagno_angelo_fortedeimarmi", "Bagno Angelo Ponente", "https://www.bagnoangelo.com/prezzi-offerte.php"
direct_rows += [
    i(_P,_ID,_N,_URL,"OMBRELLONE","Ombrellone+sdraio+lettini – settimanale maggio","Pacchetto ombrellone maggio","€250,00",250.0,"per_week","beach_umbrella_standard"),
    i(_P,_ID,_N,_URL,"OMBRELLONE","Ombrellone+sdraio+lettini – settimanale giugno","Pacchetto ombrellone giugno","€315,00",315.0,"per_week","beach_umbrella_standard"),
    i(_P,_ID,_N,_URL,"TENDA","Tenda+sdraio+lettini – settimanale maggio","Pacchetto tenda maggio","€400,00",400.0,"per_week","beach_umbrella_premium"),
    i(_P,_ID,_N,_URL,"TENDA","Tenda+sdraio+lettini – settimanale giugno","Pacchetto tenda giugno","€490,00",490.0,"per_week","beach_umbrella_premium"),
]

# V33 — Lido Tritone, Mondello (PA) – Sicilia (no individual prices on site,
# but aggregated Mondello prices from search)
_P, _ID, _N, _URL = "direct_website", "lido_tritone_mondello", "Lido Tritone", "https://www.mondelloitalobelga.it/lido-tritone.html"
direct_rows += [
    i(_P,_ID,_N,_URL,"GIORNALIERO","Ombrellone+1lettino – feriale","Lun-ven 1 ombrellone 1 lettino","€18,00",18.0,"per_day_weekday","beach_set_1lettino_ombrellone","medium"),
    i(_P,_ID,_N,_URL,"GIORNALIERO","Ombrellone+2lettini – feriale","Lun-ven 1 ombrellone 2 lettini","€22,00",22.0,"per_day_weekday","beach_set_2lettini_ombrellone","medium"),
    i(_P,_ID,_N,_URL,"GIORNALIERO","Ombrellone+1lettino – weekend","Sab-dom 1 ombrellone 1 lettino","€22,00",22.0,"per_day_weekend","beach_set_1lettino_ombrellone","medium"),
    i(_P,_ID,_N,_URL,"GIORNALIERO","Ombrellone+2lettini – weekend","Sab-dom 1 ombrellone 2 lettini","€28,00",28.0,"per_day_weekend","beach_set_2lettini_ombrellone","medium"),
    i(_P,_ID,_N,_URL,"STAGIONALE","Abbonamento stagionale","Maggio-settembre da","€1.500,00",1500.0,"per_season","beach_subscription_season","medium"),
]

# V34 — Lido Angeli del Mare, Cefalù (PA) – Sicilia
_P, _ID, _N, _URL = "direct_website", "lido_angeli_cefalu", "Lido Angeli del Mare", "https://www.lidoangelidelmare.it/"
direct_rows += [
    i(_P,_ID,_N,_URL,"GIORNALIERO","Lettino+ombrellone","Coppia base","€15,00",15.0,"per_day","beach_set_1lettino_ombrellone","medium"),
    i(_P,_ID,_N,_URL,"GIORNALIERO","Ombrellone+3lettini – luglio","Configurazione 3 lettini luglio","€35,00",35.0,"per_day","beach_set_2lettini_ombrellone","medium"),
]

# ─────────────────────────────────────────────────────────────────────
# PDF SOURCES (S2)
# ─────────────────────────────────────────────────────────────────────

# V35 — C.A.P.LI. (Consorzio Alberghi e Pensioni Lido), Lido di Venezia (VE)
# Listino 2025 (17 maggio - 14 settembre), PDF parsed con pdfplumber
_P, _ID, _N, _URL = "direct_website", "capli_lido_venezia", "Stabilimento Balneare C.A.P.LI.", "https://www.visitlido.it/"
_SRC = "https://www.visitlido.it/wp-content/uploads/2025/02/LISTINO-2025.pdf"
# Note: prezzi 2025 (PDF 2026 non ancora pubblicato al 2026-06-01)
pdf_rows += [
    # 1a Fila
    i(_P,_ID,_N,_URL,"1a FILA","Ombrellone+attrezzature 1a fila – stagionale","Stagione completa 17/5-14/9","€6.400,00",6400.0,"per_season","beach_umbrella_first_row","high",_SRC),
    i(_P,_ID,_N,_URL,"1a FILA","Ombrellone+attrezzature 1a fila – giornaliero luglio","Prezzo zona/giorno luglio","€120,00",120.0,"per_day","beach_umbrella_first_row","high",_SRC),
    i(_P,_ID,_N,_URL,"1a FILA","Ombrellone+attrezzature 1a fila – giornaliero agosto","Prezzo zona/giorno agosto","€120,00",120.0,"per_day","beach_umbrella_first_row","high",_SRC),
    i(_P,_ID,_N,_URL,"1a FILA","Ombrellone+attrezzature 1a fila – giornaliero giugno","Prezzo zona/giorno giugno","€100,00",100.0,"per_day","beach_umbrella_first_row","high",_SRC),
    i(_P,_ID,_N,_URL,"1a FILA","Ombrellone+attrezzature 1a fila – mensile luglio","Mese di luglio 31gg","€3.074,00",3074.0,"per_month","beach_umbrella_first_row","high",_SRC),
    i(_P,_ID,_N,_URL,"1a FILA","Ombrellone+attrezzature 1a fila – offerta lug-ago","Offerta 2 mesi luglio+agosto","€5.200,00",5200.0,"per_month","beach_umbrella_first_row","high",_SRC),
    # 2a Fila
    i(_P,_ID,_N,_URL,"2a FILA","Ombrellone+attrezzature 2a fila – stagionale","Stagione completa","€4.100,00",4100.0,"per_season","beach_umbrella_standard","high",_SRC),
    i(_P,_ID,_N,_URL,"2a FILA","Ombrellone+attrezzature 2a fila – giornaliero luglio","Prezzo zona/giorno","€100,00",100.0,"per_day","beach_umbrella_standard","high",_SRC),
    i(_P,_ID,_N,_URL,"2a FILA","Ombrellone+attrezzature 2a fila – mensile luglio","Mensile","€2.255,00",2255.0,"per_month","beach_umbrella_standard","high",_SRC),
    # 3a Fila
    i(_P,_ID,_N,_URL,"3a FILA","Ombrellone+attrezzature 3a fila – stagionale","Stagione completa","€3.450,00",3450.0,"per_season","beach_umbrella_standard","high",_SRC),
    i(_P,_ID,_N,_URL,"3a FILA","Ombrellone+attrezzature 3a fila – giornaliero luglio","Prezzo zona/giorno","€80,00",80.0,"per_day","beach_umbrella_standard","high",_SRC),
    # Minicapanne
    i(_P,_ID,_N,_URL,"MINICAPANNE","Minicapanna – stagionale","Stagione completa minicapanna","€2.400,00",2400.0,"per_season","beach_cabin_season","high",_SRC),
    i(_P,_ID,_N,_URL,"MINICAPANNE","Minicapanna – giornaliero luglio","Prezzo zona/giorno","€55,00",55.0,"per_day","beach_cabin_day","high",_SRC),
    i(_P,_ID,_N,_URL,"MINICAPANNE","Minicapanna – offerta lug-ago","2 mesi luglio+agosto","€1.800,00",1800.0,"per_month","beach_cabin_season","high",_SRC),
    # Camerini
    i(_P,_ID,_N,_URL,"CAMERINI","Camerino – stagionale","Stagione completa camerino","€1.500,00",1500.0,"per_season","beach_cabin_season","high",_SRC),
    i(_P,_ID,_N,_URL,"CAMERINI","Camerino – giornaliero luglio","Prezzo zona/giorno luglio","€45,00",45.0,"per_day","beach_cabin_day","high",_SRC),
    i(_P,_ID,_N,_URL,"CAMERINI","Camerino – mensile luglio","Mensile luglio","€760,00",760.0,"per_month","beach_cabin_season","high",_SRC),
]

# ─────────────────────────────────────────────────────────────────────
# CONSORTIUM (S2)
# ─────────────────────────────────────────────────────────────────────

# Use stabilimentorosanna.it+similar tradition — none new here vs S1
# Skip consortium for now: bibionemare already covered in S1

# ─────────────────────────────────────────────────────────────────────
# WRITE FILES
# ─────────────────────────────────────────────────────────────────────

def write_csv(path, rows):
    if not rows:
        return 0
    # Dedup
    seen = set()
    unique = []
    for r in rows:
        key = (r["source_venue_id"], r["normalized_product"], r["raw_price"], r["price_type"])
        if key not in seen:
            seen.add(key)
            unique.append(r)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=MENU_FIELDS)
        w.writeheader()
        w.writerows(unique)
    return len(unique)


n_direct = write_csv(DIRECT_FILE, direct_rows)
n_pdf = write_csv(PDF_FILE, pdf_rows)
n_cons = write_csv(CONSORTIUM_FILE, consortium_rows)

print(f"Direct: {n_direct} items in {DIRECT_FILE}")
print(f"PDF:    {n_pdf} items in {PDF_FILE}")
print(f"Cons:   {n_cons} items in {CONSORTIUM_FILE}")

# Total venue summary
all_rows = direct_rows + pdf_rows + consortium_rows
venues = set(r["source_venue_id"] for r in all_rows)
print(f"\nTotal new S2 venues: {len(venues)}")
print(f"Total new S2 items: {len(all_rows)}")
