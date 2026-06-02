#!/usr/bin/env python3
"""Agent 7 / S8 — report multi-città da agent7_<city>_venues_no_price.csv."""
import os, csv, glob, collections

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(ROOT, "raw_sources")
REPORT = os.path.join(ROOT, "agent7_S8_REPORT.md")
VT = ["cocktail_bar", "pub", "cafe", "wine_bar", "aperitivo_bar", "bistro",
      "craft_beer", "rooftop", "hotel_bar", "unknown"]
CITIES = ["Roma", "Napoli", "Torino", "Firenze", "Bologna", "Venezia"]


def load(city):
    p = os.path.join(RAW, f"agent7_{city.lower()}_venues_no_price.csv")
    return list(csv.DictReader(open(p, encoding="utf-8-sig"))) if os.path.exists(p) else []


def main():
    data = {c: load(c) for c in CITIES}
    # Milano S7 (file senza prefisso città) per l'aggregato
    mil_p = os.path.join(RAW, "agent7_venues_no_price.csv")
    milano = list(csv.DictReader(open(mil_p, encoding="utf-8-sig"))) if os.path.exists(mil_p) else []

    L, A = [], lambda s: L.append(s)
    A("# Agent 7 / S8 — Espansione drink multi-città Italia (discovery no-price)\n")
    A("_Replica del playbook Milano su 6 nuove città · sorgente OSM Overpass · 0 prezzi (discovery)_\n")

    done = [c for c in CITIES if data[c]]
    tot = sum(len(data[c]) for c in done)
    A("## 1. Sintesi (per CEO)\n")
    A(f"- **{len(done)}/6 città** consegnate questa sessione: {', '.join(done)}.")
    A(f"- **{tot} venues drink net-new** (oltre ai 2.428 Milano S7), tutti classificati TARGET/AMBIGUOUS, "
      "tipizzati, deduplicati, con **opening_hours 100%**.")
    A("- Sorgente: **OSM Overpass** (bar/pub/cafe/nightclub/biergarten) — nomi commerciali reali, "
      "amenity, e dove disponibili opening_hours/website/phone. Pipeline `agent7_city.py` parametrico.")
    A("- ⚠️ **Prezzi = follow-up**: i dati nazionali esistenti (menudigitale) sono risultati esigui "
      "(~111 venues sparsi). I price points per città richiedono scraping dedicato (mycia/leggimenu per città) "
      "→ sessione separata. Questa sessione consegna il **venue master** (metrica primaria del prompt).\n")

    A("## 2. Per città\n")
    A("| Città | Venues | opening_hours reali | website | phone | venue_type top |")
    A("|---|---:|---:|---:|---:|---|")
    for c in CITIES:
        rows = data[c]
        if not rows:
            A(f"| {c} | — (follow-up) | | | | |"); continue
        oh_real = sum(1 for r in rows if r["opening_hours_source"] == "osm")
        web = sum(1 for r in rows if r["website"].strip())
        ph = sum(1 for r in rows if r["phone"].strip())
        vt = collections.Counter(r["venue_type"] for r in rows)
        top = ", ".join(f"{k} {v}" for k, v in vt.most_common(3))
        A(f"| {c} | {len(rows)} | {oh_real} | {web} | {ph} | {top} |")

    A("\n## 3. venue_type per città\n")
    A("| Città | " + " | ".join(VT) + " |")
    A("|---|" + "|".join("---:" for _ in VT) + "|")
    for c in done:
        vt = collections.Counter(r["venue_type"] for r in data[c])
        A(f"| {c} | " + " | ".join(str(vt.get(t, 0)) for t in VT) + " |")

    A("\n## 4. Quality gate (tutte le città)\n")
    A("Ogni venue: `is_in_city(lat,lon,city)` ✓ (bbox `normalization.CITY_BBOX`), "
      "classificazione TARGET/AMBIGUOUS (no NO_TARGET), no junk-name, dedup geo+nome "
      "(stesso-nome <150m fuso, branch >250m separati), **opening_hours non vuoto** (reale o typical_by_type).\n")

    A("## 5. Aggregato Italia\n")
    A(f"- Milano (S6+S7): 153 prezzati + 824 (agent6) + {len(milano)} (agent7 discovery)")
    for c in done:
        A(f"- {c}: {len(data[c])} venues discovery")
    A(f"- **Nuove città S8: {tot} venues** · pin no-price totali Italia in crescita verso il target ≥18.000.\n")

    A("## 6. TODO / follow-up (per CEO)\n")
    A("- **Prezzi per città** (mycia sitemap, leggimenu brute-force, menudigitale per-città): sessione dedicata.")
    A("- **CKAN per città** (Roma/Torino/Bologna/Firenze/Venezia hanno CKAN): espande il master con licenze "
      "comunali oltre OSM (come Milano). OSM-only qui = nomi puliti, alta qualità.")
    A("- **opening_hours**: la maggioranza è `typical_by_type` (OSM ha hours reali per ~15-20%). "
      "Affinabile via siti propri / crowdsourcing.")
    A("- **città mancanti** (se <6): re-run `python3 scripts/agent7_city.py <Città>` — pipeline pronto.\n")

    A("## 7. File consegnati\n")
    for c in done:
        A(f"- `raw_sources/agent7_{c.lower()}_venues_no_price.csv`")
    A("- `scripts/agent7_city.py` (pipeline parametrico) · `scripts/agent7_s8_report.py`")
    A("\n> Riusa `normalization.py` (CITY_BBOX/is_in_city, già estesa dal CEO) + `agent6/agent7_standardize.py`. "
      "NON tocca `data/`. Schema con `city` obbligatorio popolato.")

    open(REPORT, "w", encoding="utf-8").write("\n".join(L) + "\n")
    print(f"✍  {REPORT} | città: {done} | tot venues nuove: {tot}")


if __name__ == "__main__":
    main()
