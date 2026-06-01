#!/usr/bin/env python3
"""
Beach S1 — Generate beach_s1_menu_items.csv from manually collected price data.
30 sample venues covering 3 source types: PDF, direct website, provider booking.
"""

import csv
import json
from datetime import datetime, timezone

RETRIEVED_AT = "2026-06-01T14:30:00Z"
MENU_FILE = "raw_sources/beach_s1_menu_items.csv"

MENU_FIELDS = [
    "source_platform", "source_venue_id", "venue_name", "venue_url",
    "menu_section", "item_name", "item_description",
    "raw_price", "normalized_price_eur", "currency",
    "price_type", "item_type", "normalized_product",
    "confidence", "allergens", "retrieved_at", "source_url",
    "season", "validity_start", "validity_end", "vertical",
]

SEASON = "summer_2026"
V_START = "2026-05-01"
V_END = "2026-09-30"
VERTICAL = "beach"
ITEM_TYPE = "beach_service"


def item(platform, venue_id, name, url, section, item_name, item_desc,
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


def i(p, vid, n, url, sec, iname, idesc, raw, norm, ptype, nprod, conf="high", src=None):
    return item(p, vid, n, url, sec, iname, idesc, raw, norm, ptype, nprod, conf, src)


rows = []

# ─────────────────────────────────────────────────────────────────────────────
# GROUP A: DIRECT WEBSITE (10 venues)
# ─────────────────────────────────────────────────────────────────────────────

# V01 — Bagno Teresa, Riccione (RN) – bagnoteresa.it/tariffe/
_P, _ID, _N, _URL = "direct_website", "bagnoteresa_riccione", "Bagno Teresa", "https://www.bagnoteresa.it/tariffe/"
rows += [
    i(_P,_ID,_N,_URL,"OMBRELLONI","Ombrellone Comfort prima fascia – giornaliero bassa stagione","Prima fascia, ombrellone comfort","€35,00",35.0,"per_day","beach_umbrella_first_row"),
    i(_P,_ID,_N,_URL,"OMBRELLONI","Ombrellone Comfort prima fascia – giornaliero alta stagione","Prima fascia, ombrellone comfort alta stagione","€40,00",40.0,"per_day","beach_umbrella_first_row"),
    i(_P,_ID,_N,_URL,"OMBRELLONI","Ombrellone Comfort prima fascia – settimanale bassa stagione","Prima fascia, 7 giorni","€200,00",200.0,"per_week","beach_umbrella_first_row"),
    i(_P,_ID,_N,_URL,"OMBRELLONI","Ombrellone Comfort prima fascia – mensile bassa stagione","Prima fascia, mensile","€700,00",700.0,"per_month","beach_umbrella_first_row"),
    i(_P,_ID,_N,_URL,"OMBRELLONI","Ombrellone Comfort prima fascia – stagionale","Prima fascia, stagione completa","€1.900,00",1900.0,"per_season","beach_subscription_season"),
    i(_P,_ID,_N,_URL,"OMBRELLONI","Tenda Superior prima fascia – giornaliero bassa stagione","Tenda 3x3m prima fascia","€80,00",80.0,"per_day","beach_umbrella_premium"),
    i(_P,_ID,_N,_URL,"OMBRELLONI","Tenda Superior prima fascia – stagionale","Tenda 3x3m stagione completa","€3.900,00",3900.0,"per_season","beach_subscription_season"),
    i(_P,_ID,_N,_URL,"OMBRELLONI","Ombrellone Basic seconda fascia – giornaliero","Seconda fascia standard","€25,00",25.0,"per_day","beach_umbrella_standard"),
    i(_P,_ID,_N,_URL,"OMBRELLONI","Ombrellone Basic seconda fascia – stagionale","Seconda fascia, stagionale","€1.400,00",1400.0,"per_season","beach_subscription_season"),
    i(_P,_ID,_N,_URL,"ARREDI","Lettino – giornaliero","Lettino aggiuntivo","€10,00",10.0,"per_day","beach_sunbed"),
    i(_P,_ID,_N,_URL,"ARREDI","Lettino – stagionale","Lettino aggiuntivo stagionale","€400,00",400.0,"per_season","beach_sunbed"),
    i(_P,_ID,_N,_URL,"ARREDI","Sedia – giornaliero","Sedia aggiuntiva","€5,00",5.0,"per_day","beach_chair"),
    i(_P,_ID,_N,_URL,"ARREDI","Cabina – giornaliero","Cabina privata","€20,00",20.0,"one_off","beach_cabin_day"),
    i(_P,_ID,_N,_URL,"ARREDI","Cabina – stagionale","Cabina stagionale","€650,00",650.0,"per_season","beach_cabin_season"),
]

# V02 — Apulian Beach Club, Otranto area (LE) – apulianbeachclub.it
_P, _ID, _N, _URL = "direct_website", "apulian_beach_club", "Apulian Beach Club", "https://apulianbeachclub.it/listino-prezzi/"
rows += [
    i(_P,_ID,_N,_URL,"PRIMA FILA","Ombrellone prima fila – giornaliero giugno","1 ombrellone bassa stagione prima fila","€35,00",35.0,"per_day","beach_umbrella_first_row"),
    i(_P,_ID,_N,_URL,"PRIMA FILA","Ombrellone prima fila – giornaliero agosto","1 ombrellone alta stagione prima fila","€45,00",45.0,"per_day","beach_umbrella_first_row"),
    i(_P,_ID,_N,_URL,"PRIMA FILA","Lettino prima fila – giornaliero bassa stagione","Lettino singolo prima fila giugno","€7,00",7.0,"per_day","beach_sunbed"),
    i(_P,_ID,_N,_URL,"PRIMA FILA","Lettino prima fila – giornaliero alta stagione","Lettino singolo prima fila agosto","€9,00",9.0,"per_day","beach_sunbed"),
    i(_P,_ID,_N,_URL,"STANDARD","Ombrellone+2lettini standard – giornaliero bassa stagione","Set 2a+ fila bassa stagione","€25,00",25.0,"per_day","beach_set_2lettini_ombrellone"),
    i(_P,_ID,_N,_URL,"STANDARD","Ombrellone+2lettini standard – giornaliero alta stagione","Set 2a+ fila alta stagione","€35,00",35.0,"per_day","beach_set_2lettini_ombrellone"),
    i(_P,_ID,_N,_URL,"VIP","Gazebo VIP – giornaliero bassa stagione","Gazebo 3x3m + 4 lettini bassa stagione","€50,00",50.0,"per_day","beach_umbrella_premium"),
    i(_P,_ID,_N,_URL,"VIP","Gazebo VIP – giornaliero alta stagione","Gazebo alta stagione","€80,00",80.0,"per_day","beach_umbrella_premium"),
    i(_P,_ID,_N,_URL,"ABBONAMENTI","Abbonamento mensile prima fila giugno","2 lettini + ombrellone prima fila","€1.050,00",1050.0,"per_month","beach_subscription_month"),
    i(_P,_ID,_N,_URL,"ABBONAMENTI","Abbonamento mensile prima fila luglio","2 lettini + ombrellone prima fila","€1.140,00",1140.0,"per_month","beach_subscription_month"),
    i(_P,_ID,_N,_URL,"ABBONAMENTI","Abbonamento mensile prima fila agosto","2 lettini + ombrellone prima fila","€1.255,00",1255.0,"per_month","beach_subscription_month"),
    i(_P,_ID,_N,_URL,"ABBONAMENTI","Stagionale zona rossa","Abbonamento stagionale zona premium","€2.300,00",2300.0,"per_season","beach_subscription_season"),
]

# V03 — Bagni Fiume, Livorno (LI) – bagnifiume.com
_P, _ID, _N, _URL = "direct_website", "bagni_fiume_livorno", "Bagni Fiume", "https://www.bagnifiume.com/web/tariffe/"
rows += [
    i(_P,_ID,_N,_URL,"SPIAGGIA","Ombrellone+2sdraio zona mare – giornaliero","Zona cemento vicino al mare","€25,00",25.0,"per_day","beach_set_2lettini_ombrellone"),
    i(_P,_ID,_N,_URL,"SPIAGGIA","Ombrellone+2sdraio zona grande – giornaliero","Grande spiaggia sabbiosa","€20,00",20.0,"per_day","beach_set_2lettini_ombrellone"),
    i(_P,_ID,_N,_URL,"SPIAGGIA","Ombrellone+2sdraio settimanale","Zona cemento, 7 giorni","€150,00",150.0,"per_week","beach_set_2lettini_ombrellone"),
    i(_P,_ID,_N,_URL,"ABBONAMENTI","Stagionale zona mare","Ombrellone+2sdraio stagione completa zona mare","€930,00",930.0,"per_season","beach_subscription_season"),
    i(_P,_ID,_N,_URL,"CABINE","Cabina 6 persone – giornaliero","Cabina grande privata","€60,00",60.0,"one_off","beach_cabin_day"),
    i(_P,_ID,_N,_URL,"CABINE","Cabina 6 persone – stagionale","Cabina grande stagionale","€2.160,00",2160.0,"per_season","beach_cabin_season"),
    i(_P,_ID,_N,_URL,"INGRESSO","Ingresso standard – giornaliero","Ingresso adulto","€7,00",7.0,"per_day","beach_entry_fee"),
    i(_P,_ID,_N,_URL,"ARREDI","Sedia giornaliero","Sedia singola","€3,00",3.0,"per_day","beach_chair"),
]

# V04 — Marefelice, Eraclea Mare (VE) – marefelice.it
_P, _ID, _N, _URL = "direct_website", "marefelice_eraclea", "Marefelice", "https://www.marefelice.it/listino/"
rows += [
    i(_P,_ID,_N,_URL,"PRIMA FILA","Ombrellone+2lettini prima fila – giornaliero","Prima fila","€24,00",24.0,"per_day","beach_set_2lettini_ombrellone"),
    i(_P,_ID,_N,_URL,"STANDARD","Ombrellone+2lettini seconda-terza fila – giornaliero","Standard rows 2-3","€22,00",22.0,"per_day","beach_set_2lettini_ombrellone"),
    i(_P,_ID,_N,_URL,"STANDARD","Ombrellone+2lettini quarta fila+ – giornaliero","Quarta fila e oltre","€21,00",21.0,"per_day","beach_set_2lettini_ombrellone"),
    i(_P,_ID,_N,_URL,"STANDARD","Mezza giornata (dal pomeriggio)","Dalle 14:00","€15,00",15.0,"per_half_day","beach_set_2lettini_ombrellone"),
    i(_P,_ID,_N,_URL,"VIP","Gazebo+2maxi lettini – giornaliero","Gazebo premium","€35,00",35.0,"per_day","beach_umbrella_premium"),
    i(_P,_ID,_N,_URL,"ABBONAMENTI","Stagionale prima fila","Stagione completa prima fila","€1.300,00",1300.0,"per_season","beach_subscription_season"),
    i(_P,_ID,_N,_URL,"ABBONAMENTI","Abbonamento settimanale","7 giorni consecutivi","€140,00",140.0,"per_week","beach_subscription_week"),
    i(_P,_ID,_N,_URL,"ABBONAMENTI","Abbonamento mensile","30 giorni","€500,00",500.0,"per_month","beach_subscription_month"),
]

# V05 — Bagno Laura, Tirrenia (PI) – bagnolaura.net
_P, _ID, _N, _URL = "direct_website", "bagno_laura_tirrenia", "Bagno Laura", "https://bagnolaura.net/prezzi/"
rows += [
    i(_P,_ID,_N,_URL,"OMBRELLONI","Ombrellone+2lettini – giornaliero","Giornaliero stagione estiva","€20,00 - €25,00",22.5,"per_day","beach_set_2lettini_ombrellone","medium"),
    i(_P,_ID,_N,_URL,"OMBRELLONI","Ombrellone+2lettini – mezza giornata","Dal pomeriggio","€15,00 - €20,00",17.5,"per_half_day","beach_set_2lettini_ombrellone","medium"),
    i(_P,_ID,_N,_URL,"ABBONAMENTI","Abbonamento quindicinale","15 giorni","€170,00 - €300,00",235.0,"per_week","beach_set_2lettini_ombrellone","medium"),
    i(_P,_ID,_N,_URL,"ABBONAMENTI","Abbonamento mensile","30 giorni","€300,00 - €530,00",415.0,"per_month","beach_subscription_month","medium"),
    i(_P,_ID,_N,_URL,"ABBONAMENTI","Abbonamento stagionale","Stagione completa","€950,00 - €1.150,00",1050.0,"per_season","beach_subscription_season","medium"),
    i(_P,_ID,_N,_URL,"CABINE","Cabina standard + ombrellone+2lettini – giornaliero","Cabina 7 persone","€30,00 - €35,00",32.5,"per_day","beach_cabin_day","medium"),
    i(_P,_ID,_N,_URL,"CABINE","Cabina stagionale","Stagione completa","€1.550,00 - €1.850,00",1700.0,"per_season","beach_cabin_season","medium"),
    i(_P,_ID,_N,_URL,"ARREDI","Lettino singolo – giornaliero","Lettino con servizio","€10,00 - €13,00",11.5,"per_day","beach_sunbed","medium"),
    i(_P,_ID,_N,_URL,"ARREDI","Sedia regista – giornaliero","Sedia da direttore","€7,00",7.0,"per_day","beach_chair"),
]

# V06 — Bagno Milano, Forte dei Marmi (LU) – bagnomilano.org
_P, _ID,_N, _URL = "direct_website", "bagno_milano_fortedeimarmi", "Bagno Milano", "https://www.bagnomilano.org/it/tariffe.asp"
rows += [
    i(_P,_ID,_N,_URL,"OMBRELLONI","Ombrellone+2lettini+sdraio bassa stagione – giornaliero","Giugno 1-14 / Sett 14-30","€60,00",60.0,"per_day","beach_set_2lettini_ombrellone"),
    i(_P,_ID,_N,_URL,"OMBRELLONI","Ombrellone+2lettini+sdraio alta stagione – giornaliero","Luglio-Agosto","€70,00",70.0,"per_day","beach_set_2lettini_ombrellone"),
    i(_P,_ID,_N,_URL,"OMBRELLONI","Ombrellone+2lettini+sdraio stagionale","Stagione completa","€3.400,00",3400.0,"per_season","beach_subscription_season"),
    i(_P,_ID,_N,_URL,"TENDE","Tenda 5 posti bassa stagione – giornaliero","Tenda grande (2 lettini + 2 sdraio + sedia)","€100,00",100.0,"per_day","beach_umbrella_premium"),
    i(_P,_ID,_N,_URL,"TENDE","Tenda 5 posti alta stagione – giornaliero","Tenda grande alta stagione","€120,00",120.0,"per_day","beach_umbrella_premium"),
    i(_P,_ID,_N,_URL,"TENDE","Tenda 5 posti stagionale","Stagione completa","€4.600,00",4600.0,"per_season","beach_subscription_season"),
]

# V07 — Stabilimento Balneare Manzoni, Jesolo (VE) – stabilimentobalnearemanzoni.it
_P, _ID, _N, _URL = "direct_website", "manzoni_jesolo", "Stabilimento Balneare Manzoni", "https://www.stabilimentobalnearemanzoni.it/listino/"
rows += [
    i(_P,_ID,_N,_URL,"POSTAZIONI","Postazione prima fila – giornaliero","1 ombrellone+2lettini prima fila","€30,00",30.0,"per_day","beach_set_2lettini_ombrellone"),
    i(_P,_ID,_N,_URL,"POSTAZIONI","Postazione prima fila – settimanale","Prima fila, 7 giorni","€160,00",160.0,"per_week","beach_set_2lettini_ombrellone"),
    i(_P,_ID,_N,_URL,"POSTAZIONI","Postazione standard – giornaliero","Ombrellone+2lettini file centrali","€20,00",20.0,"per_day","beach_set_2lettini_ombrellone"),
    i(_P,_ID,_N,_URL,"POSTAZIONI","Postazione stagionale fila 1","Stagione completa prima fila","€2.200,00",2200.0,"per_season","beach_subscription_season"),
    i(_P,_ID,_N,_URL,"POSTAZIONI","Postazione stagionale standard","Stagione completa file interne","€900,00",900.0,"per_season","beach_subscription_season"),
    i(_P,_ID,_N,_URL,"PARCHEGGIO","Parcheggio – giornaliero","Parcheggio con prenotazione online","€5,00",5.0,"one_off","beach_parking"),
]

# V08 — Bagno Ninetta, Lido di Camaiore (LU) – bagnoninetta.it
_P, _ID, _N, _URL = "direct_website", "bagno_ninetta_camaiore", "Bagno Ninetta", "https://www.bagnoninetta.it/la-stagione/"
rows += [
    i(_P,_ID,_N,_URL,"GIORNALIERO","Ombrellone – giornaliero feriale","Feriale","€25,00",25.0,"per_day_weekday","beach_umbrella_standard"),
    i(_P,_ID,_N,_URL,"GIORNALIERO","Ombrellone – giornaliero weekend","Weekend / festivi","€30,00",30.0,"per_day_weekend","beach_umbrella_standard"),
    i(_P,_ID,_N,_URL,"SETTIMANALE","Ombrellone – settimanale","7 giorni","€140,00",140.0,"per_week","beach_umbrella_standard"),
    i(_P,_ID,_N,_URL,"ABBONAMENTI","Ombrellone + corredo – mensile luglio-agosto","Mensile alta stagione (cabina + ombrellone + corredo)","€850,00",850.0,"per_month","beach_subscription_month"),
    i(_P,_ID,_N,_URL,"ABBONAMENTI","Ombrellone + corredo – stagionale","Stagione completa","€2.300,00",2300.0,"per_season","beach_subscription_season"),
    i(_P,_ID,_N,_URL,"SERVIZI","Supplemento prima fila – stagionale","Prima fila, sovrapprezzo","€100,00",100.0,"per_season","beach_umbrella_first_row","medium"),
]

# V09 — Bagni Nino e Nando (Spiaggia 54), Riccione (RN) – spiaggia54riccione.it
_P, _ID, _N, _URL = "direct_website", "spiaggia54_riccione", "Bagni Nino e Nando - Spiaggia 54", "https://spiaggia54riccione.it/prezzi-spiaggia-e-tariffe-ombrellone/"
rows += [
    i(_P,_ID,_N,_URL,"BATTIGIA","Ombrellone+2lettini battigia – giornaliero media stagione","Prima fila vicino acqua media stagione","€35,00",35.0,"per_day","beach_umbrella_first_row"),
    i(_P,_ID,_N,_URL,"BATTIGIA","Ombrellone+2lettini battigia – giornaliero alta stagione","Prima fila vicino acqua agosto","€43,00",43.0,"per_day","beach_umbrella_first_row"),
    i(_P,_ID,_N,_URL,"PRIMA FILA","Tenda+2lettini prima fila – giornaliero media stagione","Tenda prima fila media stagione","€30,00",30.0,"per_day","beach_umbrella_first_row"),
    i(_P,_ID,_N,_URL,"PRIMA FILA","Tenda+2lettini prima fila – giornaliero alta stagione","Tenda prima fila agosto","€38,00",38.0,"per_day","beach_umbrella_first_row"),
    i(_P,_ID,_N,_URL,"STANDARD","Ombrellone+2lettini – giornaliero media stagione","Standard rows 2-4","€26,00",26.0,"per_day","beach_set_2lettini_ombrellone"),
    i(_P,_ID,_N,_URL,"STANDARD","Ombrellone+2lettini – giornaliero alta stagione","Standard agosto","€30,00",30.0,"per_day","beach_set_2lettini_ombrellone"),
    i(_P,_ID,_N,_URL,"STANDARD","Ombrellone+2lettini – settimanale media stagione","7 giorni standard media stagione","€140,00",140.0,"per_week","beach_set_2lettini_ombrellone"),
]

# V10 — Bagni Arcobaleno, Sottomarina (VE) – bagniarcobaleno.com
_P, _ID, _N, _URL = "direct_website", "bagni_arcobaleno_sottomarina", "Bagni Arcobaleno", "https://www.bagniarcobaleno.com/listino/"
rows += [
    i(_P,_ID,_N,_URL,"GIORNALIERO","Lettino – feriale","Singolo lettino feriale","€8,00",8.0,"per_day_weekday","beach_sunbed"),
    i(_P,_ID,_N,_URL,"GIORNALIERO","Lettino – weekend","Singolo lettino sabato-domenica","€9,00",9.0,"per_day_weekend","beach_sunbed"),
    i(_P,_ID,_N,_URL,"GIORNALIERO","Ombrellone+lettino – feriale","Set base feriale","€16,00",16.0,"per_day_weekday","beach_set_1lettino_ombrellone"),
    i(_P,_ID,_N,_URL,"GIORNALIERO","Ombrellone+lettino – weekend","Set base sabato-domenica","€18,00",18.0,"per_day_weekend","beach_set_1lettino_ombrellone"),
    i(_P,_ID,_N,_URL,"GIORNALIERO","Sdraio – feriale","Sedia a sdraio feriale","€7,00",7.0,"per_day_weekday","beach_chair"),
    i(_P,_ID,_N,_URL,"CABINE","Cabina+ombrellone+lettino+tavolo+4sedie+sedia regista – feriale","Pacchetto cabina completo","€32,00",32.0,"per_day_weekday","beach_cabin_day"),
]

# ─────────────────────────────────────────────────────────────────────────────
# GROUP B: PROVIDER BOOKING (10 venues via consortium/aggregator)
# ─────────────────────────────────────────────────────────────────────────────

# V11-V14 — Bibione venues (stabilimenti.bibionemare.com) — Veneto
def bibione_item(venue_id, name, section, iname, idesc, raw, norm, ptype, nprod):
    return i("bibionemare", venue_id, name,
             f"https://stabilimenti.bibionemare.com/en/",
             section, iname, idesc, raw, norm, ptype, nprod,
             src="https://stabilimenti.bibionemare.com/en/bibione-prices.php")

# V11 — Seven Beach, Bibione Pineda (VE)
rows += [
    bibione_item("seven_beach_bibione","Seven Beach","PRIMA FILA","Prima fila ombrellone+lettini – giornaliero alta stagione","1 ombrellone+maxi lettino+lettino+sdraio alta stagione","€36,50",36.5,"per_day","beach_set_2lettini_ombrellone"),
    bibione_item("seven_beach_bibione","Seven Beach","PRIMA FILA","Prima fila ombrellone+lettini – mezza giornata alta stagione","Mezza giornata alta stagione","€25,50",25.5,"per_half_day","beach_set_2lettini_ombrellone"),
    bibione_item("seven_beach_bibione","Seven Beach","STANDARD","Seconda-terza fila – giornaliero alta stagione","Rows 2-3 alta stagione","€30,00",30.0,"per_day","beach_set_2lettini_ombrellone"),
    bibione_item("seven_beach_bibione","Seven Beach","STANDARD","Altra fila ombrellone+2lettini+sdraio – giornaliero alta stagione","Rows 4+ alta stagione","€28,00",28.0,"per_day","beach_set_2lettini_ombrellone"),
    bibione_item("seven_beach_bibione","Seven Beach","BASSA STAGIONE","Prima fila ombrellone+lettini – giornaliero bassa stagione","Maggio–15 giugno / sett 14–20","€27,00",27.0,"per_day","beach_set_2lettini_ombrellone"),
]

# V12 — Kokeshy Beach, Bibione Pineda (VE)
rows += [
    bibione_item("kokeshy_beach_bibione","Kokeshy Beach","PRIMA FILA","Prima fila ombrellone+lettini – giornaliero alta stagione","Alta stagione","€36,50",36.5,"per_day","beach_set_2lettini_ombrellone"),
    bibione_item("kokeshy_beach_bibione","Kokeshy Beach","PRIMA FILA","Prima fila – mezza giornata alta stagione","Pomeridiano alta stagione","€25,50",25.5,"per_half_day","beach_set_2lettini_ombrellone"),
    bibione_item("kokeshy_beach_bibione","Kokeshy Beach","XONE HK","Zona speciale – giornaliero alta stagione","Zona XONE HK","€24,50",24.5,"per_day","beach_set_2lettini_ombrellone"),
    bibione_item("kokeshy_beach_bibione","Kokeshy Beach","STANDARD","Rows 2-3 – giornaliero alta stagione","Standard alta stagione","€30,00",30.0,"per_day","beach_set_2lettini_ombrellone"),
]

# V13 — Shany Beach, Bibione Pineda (VE)
rows += [
    bibione_item("shany_beach_bibione","Shany Beach","PRIMA FILA","Prima fila – giornaliero alta stagione","Alta stagione prima fila","€34,50",34.5,"per_day","beach_set_2lettini_ombrellone"),
    bibione_item("shany_beach_bibione","Shany Beach","PRIMA FILA","Prima fila – mezza giornata alta stagione","Pomeridiano","€24,00",24.0,"per_half_day","beach_set_2lettini_ombrellone"),
    bibione_item("shany_beach_bibione","Shany Beach","STANDARD","Seconda-terza fila – giornaliero alta stagione","Rows 2-3","€28,00",28.0,"per_day","beach_set_2lettini_ombrellone"),
    bibione_item("shany_beach_bibione","Shany Beach","STANDARD","Altra fila – giornaliero alta stagione","Rows 4+","€25,00",25.0,"per_day","beach_set_2lettini_ombrellone"),
]

# V14 — Pinedo Beach, Bibione Pineda (VE)
rows += [
    bibione_item("pinedo_beach_bibione","Pinedo Beach","PRIMA FILA","Prima fila – giornaliero alta stagione","Alta stagione prima fila","€34,50",34.5,"per_day","beach_set_2lettini_ombrellone"),
    bibione_item("pinedo_beach_bibione","Pinedo Beach","PRIMA FILA","Prima fila – mezza giornata","Pomeridiano alta stagione","€24,00",24.0,"per_half_day","beach_set_2lettini_ombrellone"),
    bibione_item("pinedo_beach_bibione","Pinedo Beach","HP ZONE","Zona HP – giornaliero alta stagione","Area speciale HP zone","€23,00",23.0,"per_day","beach_umbrella_premium"),
    bibione_item("pinedo_beach_bibione","Pinedo Beach","STANDARD","Standard rows – giornaliero alta stagione","Alta stagione standard","€28,00",28.0,"per_day","beach_set_2lettini_ombrellone"),
]

# V15-V17 — Spiagge.it venues (provider confirmed, no public prices shown)
# These are annotated as "no_price" for schema completeness – items not added

# V15 — Lignano Sabbiadoro venues (lignano-riviera.it / local consortium)
def lignano_item(venue_id, name, section, iname, idesc, raw, norm, ptype, nprod):
    return i("direct_website", venue_id, name,
             f"https://www.spiaggia14e15.it/it/listino.php",
             section, iname, idesc, raw, norm, ptype, nprod,
             src="https://www.spiaggia14e15.it/it/listino.php")

# V15 — Ufficio Spiaggia 14 e 15, Lignano Sabbiadoro (UD)
_P, _ID, _N, _URL = "direct_website", "spiaggia14e15_lignano", "Ufficio Spiaggia 14 e 15", "http://www.spiaggia14e15.it/it/listino.php"
rows += [
    i(_P,_ID,_N,_URL,"PRIMA FILA","Ombrellone+2lettini prima fila – giornaliero bassa stagione","Bassa stagione prima fila","€19,00",19.0,"per_day","beach_set_2lettini_ombrellone"),
    i(_P,_ID,_N,_URL,"PRIMA FILA","Ombrellone+2lettini prima fila – giornaliero alta stagione","Alta stagione (luglio-agosto)","€25,00",25.0,"per_day","beach_set_2lettini_ombrellone"),
    i(_P,_ID,_N,_URL,"PRIMA FILA","Ombrellone+2lettini prima fila – stagionale","Stagione completa prima fila","€1.600,00",1600.0,"per_season","beach_subscription_season"),
    i(_P,_ID,_N,_URL,"STANDARD","Ombrellone+2lettini 4a+ fila – giornaliero alta stagione","Quarta fila e oltre","€21,00",21.0,"per_day","beach_set_2lettini_ombrellone"),
    i(_P,_ID,_N,_URL,"STANDARD","Ombrellone+2lettini standard – stagionale","Stagionale file interne","€1.250,00",1250.0,"per_season","beach_subscription_season"),
    i(_P,_ID,_N,_URL,"ARREDI","Cabina – giornaliero alta stagione","Cabina privata","€10,00",10.0,"one_off","beach_cabin_day"),
    i(_P,_ID,_N,_URL,"ARREDI","Cabina – stagionale","Cabina stagionale","€500,00",500.0,"per_season","beach_cabin_season"),
    i(_P,_ID,_N,_URL,"ARREDI","Sdraio – giornaliero alta stagione","Sedia a sdraio","€4,00",4.0,"per_day","beach_chair"),
    i(_P,_ID,_N,_URL,"ARREDI","Lettino – giornaliero alta stagione","Lettino singolo","€7,00",7.0,"per_day","beach_sunbed"),
]

# V16 — La Spiaggia di Duke, Lignano Sabbiadoro (UD) – pet-friendly
_P, _ID, _N, _URL = "direct_website", "spiaggia_duke_lignano", "La Spiaggia di Duke", "https://www.laspiaggiadiduke.com/index.php/it/tariffe-e-prenotazioni"
rows += [
    i(_P,_ID,_N,_URL,"STANDARD","Ombrellone+2lettini rows 7+ – giornaliero","Fila 7 e oltre","€23,00 - €25,00",24.0,"per_day","beach_set_2lettini_ombrellone","medium"),
    i(_P,_ID,_N,_URL,"PRIMA FILA","Ombrellone+2lettini rows 1-6 – giornaliero","Prima fila fino a sesta","€28,00 - €30,00",29.0,"per_day","beach_set_2lettini_ombrellone","medium"),
    i(_P,_ID,_N,_URL,"STANDARD","Ombrellone+2lettini rows 7+ – settimanale","Settimanale fila interna","€140,00 - €155,00",147.5,"per_week","beach_set_2lettini_ombrellone","medium"),
    i(_P,_ID,_N,_URL,"PRIMA FILA","Ombrellone+2lettini rows 1-6 – settimanale","Settimanale prima fila","€170,00 - €190,00",180.0,"per_week","beach_set_2lettini_ombrellone","medium"),
    i(_P,_ID,_N,_URL,"ARREDI","Lettino aggiuntivo – giornaliero","Extra lettino","€8,00",8.0,"per_day","beach_sunbed"),
    i(_P,_ID,_N,_URL,"ARREDI","Sedia – giornaliero","Sedia aggiuntiva","€7,00",7.0,"per_day","beach_chair"),
]

# V17 — Bagni Lido, Alassio (SV) – bagnilido.com
_P, _ID, _N, _URL = "direct_website", "bagni_lido_alassio", "Bagni Lido", "https://www.bagnilido.com/"
rows += [
    i(_P,_ID,_N,_URL,"BASSA STAGIONE","Ombrellone+2lettini+sdraio – prima fila bassa stagione","Maggio, giugno, settembre prima fila","€50,00",50.0,"per_day","beach_umbrella_first_row"),
    i(_P,_ID,_N,_URL,"BASSA STAGIONE","Ombrellone+2lettini+sdraio – seconda fila bassa stagione","Seconda fila bassa stagione","€40,00",40.0,"per_day","beach_umbrella_standard"),
    i(_P,_ID,_N,_URL,"BASSA STAGIONE","Ombrellone+2lettini+sdraio – quarta-quinta fila bassa stagione","Quarta-quinta fila","€30,00",30.0,"per_day","beach_umbrella_standard"),
    i(_P,_ID,_N,_URL,"ALTA STAGIONE","Ombrellone+2lettini+sdraio – prima fila alta stagione","Luglio-agosto prima fila","€70,00",70.0,"per_day","beach_umbrella_first_row"),
    i(_P,_ID,_N,_URL,"ALTA STAGIONE","Ombrellone+2lettini+sdraio – quinta fila alta stagione","Quinta fila alta stagione","€45,00",45.0,"per_day","beach_umbrella_standard"),
    i(_P,_ID,_N,_URL,"ABBONAMENTI","Mensile prima fila – bassa stagione","Maggio/giugno/settembre","€1.300,00",1300.0,"per_month","beach_subscription_month"),
    i(_P,_ID,_N,_URL,"ABBONAMENTI","Mensile prima fila – alta stagione","Luglio/agosto","€2.000,00",2000.0,"per_month","beach_subscription_month"),
]

# V18 — Bagni Carlo, Alassio (SV) – bagnicarlo.it
_P, _ID, _N, _URL = "direct_website", "bagni_carlo_alassio", "Bagni Carlo", "https://www.bagnicarlo.it/"
rows += [
    i(_P,_ID,_N,_URL,"PRIMA FILA","Ombrellone+2lettini prima fila – bassa stagione","Prima fila (maggio, giugno, settembre)","€45,00",45.0,"per_day","beach_umbrella_first_row"),
    i(_P,_ID,_N,_URL,"PRIMA FILA","Ombrellone+2lettini prima fila – alta stagione","Prima fila luglio-agosto","€65,00",65.0,"per_day","beach_umbrella_first_row"),
    i(_P,_ID,_N,_URL,"PRIMA FILA","Ombrellone+2lettini prima fila – weekend supplement","Sabato/domenica/festivi +€5","€70,00",70.0,"per_day_weekend","beach_umbrella_first_row"),
    i(_P,_ID,_N,_URL,"SECONDA FILA","Ombrellone+2lettini seconda fila – alta stagione","Seconda fila alta stagione","€60,00",60.0,"per_day","beach_umbrella_standard"),
    i(_P,_ID,_N,_URL,"TERZA FILA","Ombrellone+2lettini terza fila – alta stagione","Terza fila alta stagione","€55,00",55.0,"per_day","beach_umbrella_standard"),
    i(_P,_ID,_N,_URL,"ARREDI","Ingresso adulto – giornaliero","Ingresso","€7,00",7.0,"per_day","beach_entry_fee"),
    i(_P,_ID,_N,_URL,"ARREDI","Cabina – giornaliero","Cabina spogliatoio","€10,00",10.0,"one_off","beach_cabin_day"),
    i(_P,_ID,_N,_URL,"ARREDI","Sedia regista – giornaliero","Sedia da regista","€10,00",10.0,"per_day","beach_chair"),
]

# V19 — Rosanna, Alghero (SS) – stabilimentorosanna.it
_P, _ID, _N, _URL = "direct_website", "rosanna_alghero", "Stabilimento Balneare Rosanna", "https://stabilimentorosanna.it/about/"
rows += [
    i(_P,_ID,_N,_URL,"STANDARD","Postazione standard – giugno","Ombrellone+2lettini standard","€25,00",25.0,"per_day","beach_set_2lettini_ombrellone"),
    i(_P,_ID,_N,_URL,"STANDARD","Postazione standard – luglio","Ombrellone+2lettini standard","€30,00",30.0,"per_day","beach_set_2lettini_ombrellone"),
    i(_P,_ID,_N,_URL,"STANDARD","Postazione standard – agosto","Ombrellone+2lettini standard","€40,00",40.0,"per_day","beach_set_2lettini_ombrellone"),
    i(_P,_ID,_N,_URL,"STANDARD","Postazione standard – settembre","Ombrellone+2lettini standard","€25,00",25.0,"per_day","beach_set_2lettini_ombrellone"),
    i(_P,_ID,_N,_URL,"DELUXE","Postazione deluxe prima fila – giugno","Ombrellone+2lettini+materassini prima fila","€35,00",35.0,"per_day","beach_umbrella_first_row"),
    i(_P,_ID,_N,_URL,"DELUXE","Postazione deluxe prima fila – luglio","Prima fila luglio","€40,00",40.0,"per_day","beach_umbrella_first_row"),
    i(_P,_ID,_N,_URL,"DELUXE","Postazione deluxe prima fila – agosto","Prima fila agosto","€50,00",50.0,"per_day","beach_umbrella_first_row"),
    i(_P,_ID,_N,_URL,"DELUXE","Postazione deluxe prima fila – settembre","Prima fila settembre","€40,00",40.0,"per_day","beach_umbrella_first_row"),
    i(_P,_ID,_N,_URL,"DELUXE","Postazione standard domenica – giugno","Domenica/festivi standard","€30,00",30.0,"per_day_weekend","beach_set_2lettini_ombrellone"),
]

# V20 — Bagno Duilio, Viareggio (LU) – bagnoduilio.it
_P, _ID, _N, _URL = "direct_website", "bagno_duilio_viareggio", "Bagno Duilio", "https://bagnoduilio.it/prezzi/"
rows += [
    i(_P,_ID,_N,_URL,"STAGIONE","Posto spiaggia – maggio/settembre","Giornaliero bassa stagione (max 4 persone)","€20,00",20.0,"per_day","beach_set_2lettini_ombrellone"),
    i(_P,_ID,_N,_URL,"STAGIONE","Posto spiaggia – giugno","Giornaliero giugno","€22,00",22.0,"per_day","beach_set_2lettini_ombrellone"),
    i(_P,_ID,_N,_URL,"STAGIONE","Posto spiaggia – luglio/agosto","Giornaliero alta stagione","€27,00",27.0,"per_day","beach_set_2lettini_ombrellone"),
    i(_P,_ID,_N,_URL,"STAGIONE","Posto spiaggia – 8-23 agosto","Peak alta stagione","€30,00",30.0,"per_day","beach_set_2lettini_ombrellone"),
    i(_P,_ID,_N,_URL,"ABBONAMENTI","Stagionale standard fila bassa","Stagione completa file posteriori","€1.050,00",1050.0,"per_season","beach_subscription_season"),
    i(_P,_ID,_N,_URL,"ABBONAMENTI","Stagionale row 10","Stagionale row 10","€1.450,00",1450.0,"per_season","beach_subscription_season"),
    i(_P,_ID,_N,_URL,"ABBONAMENTI","Stagionale cabina inclusa","Stagionale con ombrellone+2lettini+cabina","€1.800,00",1800.0,"per_season","beach_subscription_season"),
    i(_P,_ID,_N,_URL,"ABBONAMENTI","Settimanale luglio/agosto","7 giorni alta stagione","€160,00",160.0,"per_week","beach_subscription_week"),
    i(_P,_ID,_N,_URL,"ARREDI","Lettino aggiuntivo – alta stagione","Lettino extra","€10,00",10.0,"per_day","beach_sunbed"),
    i(_P,_ID,_N,_URL,"ARREDI","Cabina – alta stagione","Cabina giornaliera","€8,00",8.0,"one_off","beach_cabin_day"),
]

# ─────────────────────────────────────────────────────────────────────────────
# GROUP C: PDF LISTINI (7 venues from PDF files)
# ─────────────────────────────────────────────────────────────────────────────

# V21 — Balmor, Cervia (RA) – balmor.it (PDF 2024, latest available)
_P, _ID, _N, _URL = "direct_website", "balmor_cervia", "Balmor", "https://www.balmor.it/"
_SRC = "https://www.balmor.it/wp-content/uploads/2024/05/tariffe-spiaggia-balmor-2024.pdf"
rows += [
    i(_P,_ID,_N,_URL,"ALTA STAGIONE","Ombrellone+2lettini alta stagione – giornaliero","01/07-25/08 standard","€25,00",25.0,"per_day","beach_set_2lettini_ombrellone","high",_SRC),
    i(_P,_ID,_N,_URL,"ALTA STAGIONE","Ombrellone+3lettini alta stagione – giornaliero","Alta stagione 3 lettini","€30,00",30.0,"per_day","beach_set_2lettini_ombrellone","high",_SRC),
    i(_P,_ID,_N,_URL,"ALTA STAGIONE","Ombrellone+1lettino alta stagione – giornaliero","Alta stagione 1 lettino","€20,00",20.0,"per_day","beach_set_1lettino_ombrellone","high",_SRC),
    i(_P,_ID,_N,_URL,"ALTA STAGIONE","Lettino extra – giornaliero","Lettino aggiuntivo","€8,00",8.0,"per_day","beach_sunbed","high",_SRC),
    i(_P,_ID,_N,_URL,"ALTA STAGIONE","Cabina privata – giornaliero","Cabina giornaliera","€15,00",15.0,"one_off","beach_cabin_day","high",_SRC),
    i(_P,_ID,_N,_URL,"ALTA STAGIONE","Supplemento prima fila","Prima fila +40%","€10,50",10.5,"per_day","beach_umbrella_first_row","high",_SRC),
    i(_P,_ID,_N,_URL,"MEDIA STAGIONE","Ombrellone+2lettini media stagione – giornaliero","01/06-30/06 e 26/08-15/09","€25,00",25.0,"per_day","beach_set_2lettini_ombrellone","high",_SRC),
    i(_P,_ID,_N,_URL,"BASSA STAGIONE","Ombrellone+2lettini bassa stagione – giornaliero","01/04-31/05 e 16/09-30/09","€20,00",20.0,"per_day","beach_set_2lettini_ombrellone","high",_SRC),
    i(_P,_ID,_N,_URL,"BASSA STAGIONE","Lettino extra bassa stagione","Bassa stagione","€6,00",6.0,"per_day","beach_sunbed","high",_SRC),
    i(_P,_ID,_N,_URL,"ALTA STAGIONE","Pomeridiano ombrellone+2lettini","Dalle 14:00 alta stagione","€25,00",25.0,"per_half_day","beach_set_2lettini_ombrellone","high",_SRC),
]

# V22 — Lido Scogliera (2026 PDF) – lidoscogliera.com
_P, _ID, _N, _URL = "direct_website", "lido_scogliera", "Lido Scogliera", "https://www.lidoscogliera.com/"
_SRC = "https://www.lidoscogliera.com/prezzi/giornaliero.pdf"
rows += [
    i(_P,_ID,_N,_URL,"ALTA STAGIONE","Pacchetto 1 prima fila – alta stagione","2 persone + 2 lettini + ombrellone + cabina privata","€64,00",64.0,"per_day","beach_cabin_day","high",_SRC),
    i(_P,_ID,_N,_URL,"MEDIA STAGIONE","Pacchetto 1 prima fila – media stagione","Stessa config media stagione","€52,00",52.0,"per_day","beach_cabin_day","high",_SRC),
    i(_P,_ID,_N,_URL,"BASSA STAGIONE","Pacchetto 1 prima fila – bassa stagione","Bassa stagione","€37,00",37.0,"per_day","beach_cabin_day","high",_SRC),
    i(_P,_ID,_N,_URL,"ALTA STAGIONE","Pacchetto base rows 5-7 – alta stagione","2 persone+2 lettini+ombrellone+spogliatoio comune","€41,00",41.0,"per_day","beach_set_2lettini_ombrellone","high",_SRC),
    i(_P,_ID,_N,_URL,"MEDIA STAGIONE","Pacchetto base rows 5-7 – media stagione","Media stagione","€33,00",33.0,"per_day","beach_set_2lettini_ombrellone","high",_SRC),
    i(_P,_ID,_N,_URL,"BASSA STAGIONE","Pacchetto base rows 5-7 – bassa stagione","Bassa stagione","€23,00",23.0,"per_day","beach_set_2lettini_ombrellone","high",_SRC),
    i(_P,_ID,_N,_URL,"ALTA STAGIONE","Pacchetto singolo – alta stagione","1 persona+1 lettino+ombrellone","€25,00",25.0,"per_day","beach_set_1lettino_ombrellone","high",_SRC),
    i(_P,_ID,_N,_URL,"ALTA STAGIONE","Pacchetto solarium – alta stagione","1 persona+1 lettino, solo solarium","€13,00",13.0,"per_day","beach_sunbed","high",_SRC),
]

# V23 — Rivazzurra Beach, Anzio (RM) – rivazzurrabeach.it (PDF 2026)
_P, _ID, _N, _URL = "direct_website", "rivazzurra_beach_anzio", "Rivazzurra Beach", "https://www.rivazzurrabeach.it/"
_SRC = "https://www.rivazzurrabeach.it/stabilimento/wp-content/uploads/2026/05/LISTINO_2026.pdf"
rows += [
    i(_P,_ID,_N,_URL,"GIORNALIERO","Lettino – feriale","Lettino singolo feriale","€8,00",8.0,"per_day_weekday","beach_sunbed","high",_SRC),
    i(_P,_ID,_N,_URL,"GIORNALIERO","Lettino – festivo","Lettino festivo","€10,00",10.0,"per_day_weekend","beach_sunbed","high",_SRC),
    i(_P,_ID,_N,_URL,"GIORNALIERO","Lettino – pomeridiano","Lettino dal pomeriggio","€6,00",6.0,"per_half_day","beach_sunbed","high",_SRC),
    i(_P,_ID,_N,_URL,"GIORNALIERO","Ombrellone+2lettini – feriale","Set base feriale","€30,00",30.0,"per_day_weekday","beach_set_2lettini_ombrellone","high",_SRC),
    i(_P,_ID,_N,_URL,"GIORNALIERO","Ombrellone+2lettini – festivo","Set base festivo","€35,00",35.0,"per_day_weekend","beach_set_2lettini_ombrellone","high",_SRC),
    i(_P,_ID,_N,_URL,"GIORNALIERO","Ombrellone+2lettini – pomeridiano","Set base pomeridiano","€20,00",20.0,"per_half_day","beach_set_2lettini_ombrellone","high",_SRC),
    i(_P,_ID,_N,_URL,"GIORNALIERO","Maxi+2lettini+sedia – feriale","Premium set feriale","€40,00",40.0,"per_day_weekday","beach_umbrella_premium","high",_SRC),
    i(_P,_ID,_N,_URL,"GIORNALIERO","Gazebo+2lettini+2sdraio – feriale","Gazebo feriale","€40,00",40.0,"per_day_weekday","beach_umbrella_premium","high",_SRC),
    i(_P,_ID,_N,_URL,"SETTIMANALE","Ombrellone+2lettini – settimana (sett. A/B)","7 gg settore standard","€200,00",200.0,"per_week","beach_set_2lettini_ombrellone","high",_SRC),
    i(_P,_ID,_N,_URL,"SETTIMANALE","Ombrellone+2lettini – settimana (sett. C maxi)","7 gg settore premium","€295,00",295.0,"per_week","beach_umbrella_premium","high",_SRC),
    i(_P,_ID,_N,_URL,"STAGIONALE","Stagionale settore A/B","107 giorni stagionale standard","€1.350,00",1350.0,"per_season","beach_subscription_season","high",_SRC),
    i(_P,_ID,_N,_URL,"STAGIONALE","Stagionale settore C maxi","107 giorni settore premium","€1.500,00",1500.0,"per_season","beach_subscription_season","high",_SRC),
    i(_P,_ID,_N,_URL,"TESSERE","Tessera 15 lettini (5 festivi+10 feriali)","Carnet multi-ingresso","€110,00",110.0,"per_season","beach_minimum_spend","high",_SRC),
]

# V24 — Bagni 79, Senigallia (AN) – bagni79.it
_P, _ID, _N, _URL = "direct_website", "bagni79_senigallia", "Bagni 79", "https://www.bagni79.it/listino.php"
rows += [
    i(_P,_ID,_N,_URL,"PRIMA FILA","Ombrellone+2lettini prima fila – giornaliero","Prima fila","€28,00",28.0,"per_day","beach_umbrella_first_row"),
    i(_P,_ID,_N,_URL,"PRIMA FILA","Ombrellone+2lettini prima fila – settimanale","Prima fila 7 giorni","€185,00",185.0,"per_week","beach_umbrella_first_row"),
    i(_P,_ID,_N,_URL,"PRIMA FILA","Ombrellone+2lettini prima fila – quindicinale","Prima fila 15 giorni","€315,00",315.0,"per_week","beach_umbrella_first_row"),
    i(_P,_ID,_N,_URL,"PRIMA FILA","Ombrellone+2lettini prima fila – mensile","Prima fila 30 giorni","€425,00",425.0,"per_month","beach_umbrella_first_row"),
    i(_P,_ID,_N,_URL,"STANDARD","Ombrellone+2lettini 2a-3a fila – giornaliero","Seconda/terza fila","€25,00",25.0,"per_day","beach_set_2lettini_ombrellone"),
    i(_P,_ID,_N,_URL,"STANDARD","Ombrellone+2lettini 2a-3a fila – settimanale","Seconda/terza fila 7 giorni","€165,00",165.0,"per_week","beach_set_2lettini_ombrellone"),
    i(_P,_ID,_N,_URL,"STANDARD","Ombrellone+2lettini file posteriori – giornaliero","File interne","€22,00",22.0,"per_day","beach_set_2lettini_ombrellone"),
    i(_P,_ID,_N,_URL,"STANDARD","Ombrellone+2lettini file posteriori – settimanale","File interne 7 giorni","€145,00",145.0,"per_week","beach_set_2lettini_ombrellone"),
]

# V25 — Bagno Baratti, Baratti/Piombino (LI) – bagnobaratti.it
_P, _ID, _N, _URL = "direct_website", "bagno_baratti_piombino", "Bagno Baratti Beach", "https://www.bagnobaratti.it/listino-prezzi/"
rows += [
    i(_P,_ID,_N,_URL,"PRIMA FILA","Ombrellone+2lettini prima fila – maggio","Maggio prima fila","€30,00",30.0,"per_day","beach_umbrella_first_row"),
    i(_P,_ID,_N,_URL,"PRIMA FILA","Ombrellone+2lettini prima fila – giugno","Giugno prima fila","€35,00",35.0,"per_day","beach_umbrella_first_row"),
    i(_P,_ID,_N,_URL,"PRIMA FILA","Ombrellone+2lettini prima fila – luglio","Luglio prima fila","€40,00",40.0,"per_day","beach_umbrella_first_row"),
    i(_P,_ID,_N,_URL,"PRIMA FILA","Ombrellone+2lettini prima fila – agosto","Agosto prima fila","€45,00",45.0,"per_day","beach_umbrella_first_row"),
    i(_P,_ID,_N,_URL,"STANDARD","Ombrellone+2lettini standard – agosto","Agosto file standard","€40,00",40.0,"per_day","beach_set_2lettini_ombrellone"),
    i(_P,_ID,_N,_URL,"STANDARD","Ombrellone+2lettini standard – luglio","Luglio file standard","€35,00",35.0,"per_day","beach_set_2lettini_ombrellone"),
    i(_P,_ID,_N,_URL,"VIP","Gazebo – agosto","Gazebo agosto","€90,00",90.0,"per_day","beach_umbrella_premium"),
    i(_P,_ID,_N,_URL,"VIP","Gazebo – maggio","Gazebo bassa stagione","€60,00",60.0,"per_day","beach_umbrella_premium"),
    i(_P,_ID,_N,_URL,"ARREDI","Lettino prima fila – giugno","Lettino singolo prima fila","€10,00",10.0,"per_day","beach_sunbed"),
    i(_P,_ID,_N,_URL,"ARREDI","Sdraio prima fila – giugno","Sedia a sdraio","€7,00",7.0,"per_day","beach_chair"),
]

# V26 — Bagno Imperiale, Tirrenia (PI) – bagnoimperiale.it
_P, _ID, _N, _URL = "direct_website", "bagno_imperiale_tirrenia", "Bagno Imperiale", "https://www.bagnoimperiale.it/listino-prezzi/"
rows += [
    i(_P,_ID,_N,_URL,"GIORNALIERO","Ombrellone+2lettini – feriale","Feriale","€15,00",15.0,"per_day_weekday","beach_set_2lettini_ombrellone"),
    i(_P,_ID,_N,_URL,"GIORNALIERO","Ombrellone+2lettini – weekend","Weekend/festivo","€28,00",28.0,"per_day_weekend","beach_set_2lettini_ombrellone"),
    i(_P,_ID,_N,_URL,"QUINDICINALE","Ombrellone+2lettini – quindicinale bassa stagione","15 gg maggio/giugno/settembre","€170,00",170.0,"per_week","beach_set_2lettini_ombrellone"),
    i(_P,_ID,_N,_URL,"QUINDICINALE","Ombrellone+2lettini – quindicinale alta stagione","15 gg luglio/agosto","€250,00",250.0,"per_week","beach_set_2lettini_ombrellone"),
    i(_P,_ID,_N,_URL,"MENSILE","Ombrellone+2lettini – mensile bassa stagione","30 gg bassa stagione","€300,00",300.0,"per_month","beach_set_2lettini_ombrellone"),
    i(_P,_ID,_N,_URL,"MENSILE","Ombrellone+2lettini – mensile alta stagione","30 gg luglio/agosto","€400,00",400.0,"per_month","beach_set_2lettini_ombrellone"),
    i(_P,_ID,_N,_URL,"STAGIONALE","Ombrellone+2lettini – stagionale","Stagione completa","€1.000,00",1000.0,"per_season","beach_subscription_season"),
    i(_P,_ID,_N,_URL,"CABINE","Cabina+ombrellone+2sdraio – feriale","Cabina giornaliera feriale","€25,00",25.0,"per_day_weekday","beach_cabin_day"),
    i(_P,_ID,_N,_URL,"CABINE","Cabina+ombrellone+2sdraio – stagionale","Stagionale con cabina","€1.750,00",1750.0,"per_season","beach_cabin_season"),
    i(_P,_ID,_N,_URL,"CABINE","Doccia calda per persona","Doccia calda singola","€1,00",1.0,"one_off","beach_shower"),
    i(_P,_ID,_N,_URL,"INGRESSO","Ingresso per persona","Ingresso giornaliero","€5,00",5.0,"per_day","beach_entry_fee"),
    i(_P,_ID,_N,_URL,"ARREDI","Lettino aggiuntivo – mensile","Lettino extra mensile","€100,00",100.0,"per_month","beach_sunbed"),
]

# V27 — Riva del Sole, Otranto/Laghi Alimini (LE) – spiaggiarivadelsole.com
_P, _ID, _N, _URL = "direct_website", "riva_del_sole_otranto", "Riva del Sole", "https://www.spiaggiarivadelsole.com/prezzi/"
rows += [
    i(_P,_ID,_N,_URL,"GIUGNO","Ombrellone+2lettini – giornaliero giugno","Set standard giugno","€20,00",20.0,"per_day","beach_set_2lettini_ombrellone"),
    i(_P,_ID,_N,_URL,"LUGLIO","Ombrellone+2lettini – giornaliero luglio","Set standard luglio","€25,00",25.0,"per_day","beach_set_2lettini_ombrellone"),
    i(_P,_ID,_N,_URL,"AGOSTO","Ombrellone+2lettini – giornaliero agosto","Set standard agosto","€30,00",30.0,"per_day","beach_set_2lettini_ombrellone"),
    i(_P,_ID,_N,_URL,"SETTEMBRE","Ombrellone+2lettini – giornaliero settembre","Set standard settembre","€20,00",20.0,"per_day","beach_set_2lettini_ombrellone"),
    i(_P,_ID,_N,_URL,"PRIMA FILA","Prima fila Comfort – giornaliero bassa","Prima fila confort bassa stagione","€40,00",40.0,"per_day","beach_umbrella_first_row"),
    i(_P,_ID,_N,_URL,"PRIMA FILA","Prima fila Comfort – giornaliero alta","Prima fila alta stagione","€50,00",50.0,"per_day","beach_umbrella_first_row"),
    i(_P,_ID,_N,_URL,"QUINDICINALE","Ombrellone+2lettini – quindicinale luglio","15 giorni luglio","€320,00",320.0,"per_week","beach_set_2lettini_ombrellone"),
    i(_P,_ID,_N,_URL,"ABBONAMENTI","Stagionale (1 giugno - 15 settembre)","Stagione completa","€1.000,00",1000.0,"per_season","beach_subscription_season"),
    i(_P,_ID,_N,_URL,"ARREDI","Lettino singolo – bassa stagione","Lettino singolo giugno/settembre","€6,00",6.0,"per_day","beach_sunbed"),
    i(_P,_ID,_N,_URL,"ARREDI","Lettino singolo – alta stagione","Lettino singolo luglio/agosto","€9,00",9.0,"per_day","beach_sunbed"),
]

# ─────────────────────────────────────────────────────────────────────────────
# WRITE CSV
# ─────────────────────────────────────────────────────────────────────────────

# Dedup
seen = set()
unique_rows = []
for r in rows:
    key = (r["source_venue_id"], r["normalized_product"], r["raw_price"], r["price_type"])
    if key not in seen:
        seen.add(key)
        unique_rows.append(r)

print(f"Total items: {len(unique_rows)}")

# Count venues
venues_seen = set(r["source_venue_id"] for r in unique_rows)
print(f"Distinct venues: {len(venues_seen)}")
for v in sorted(venues_seen):
    cnt = sum(1 for r in unique_rows if r["source_venue_id"] == v)
    print(f"  {v}: {cnt} items")

with open(MENU_FILE, "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=MENU_FIELDS)
    writer.writeheader()
    writer.writerows(unique_rows)

print(f"\nWritten: {MENU_FILE}")
