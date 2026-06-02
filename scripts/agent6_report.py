#!/usr/bin/env python3
"""Agent 6 — File 4: genera agent6_REPORT.md dai CSV finali."""
import sys, os, csv, collections, re

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from agent6_standardize import (read_csv, has, name_variants, classify_venue,
                                norm_name, VEN, PRI, RAW)
ROOT = os.path.dirname(HERE)
NOPRICE = os.path.join(RAW, "agent6_venues_no_price.csv")
GEO = os.path.join(RAW, "agent6_geocode_fixes.csv")
DEDUP = os.path.join(RAW, "agent6_name_dedup.csv")
ADDR = os.path.join(RAW, "agent6_address_fixes.csv")
OUT = os.path.join(ROOT, "agent6_REPORT.md")

VT_DESC = {
    'cocktail_bar': 'Cocktail focus / nightclub / lounge',
    'pub': 'Birre alla spina, pub, taproom',
    'cafe': 'Caffetteria / bar di quartiere (default "bar" generico IT)',
    'wine_bar': 'Enoteca / vineria / mescita',
    'aperitivo_bar': 'Aperitivo italiano dominante',
    'bistro': 'Bistrot ibrido bar + cibo leggero',
    'craft_beer': 'Birra artigianale / birrificio',
    'rooftop': 'Rooftop / terrazza panoramica',
    'hotel_bar': 'Bar interno hotel',
    'unknown': 'Non determinabile da metadata',
}


def main():
    venues = read_csv(VEN); prices = read_csv(PRI)
    priced = set(norm_name(p["venue_name"]) for p in prices if (p.get("venue_name") or "").strip())
    nop = [v for v in venues if not (name_variants(v) & priced)]
    pool_cls = collections.Counter(classify_venue(v["venue_name"], v.get("categories", "")) for v in nop)

    out = read_csv(NOPRICE)
    n_out = len(out)
    by_cls = collections.Counter(r["target_classification"] for r in out)
    by_vt = collections.Counter(r["venue_type"] for r in out)
    cov = lambda k: sum(1 for r in out if (r.get(k) or "").strip())

    geo = read_csv(GEO) if os.path.exists(GEO) else []
    geo_conf = collections.Counter(r["confidence"] for r in geo)
    geo_meth = collections.Counter(r["method"] for r in geo)

    dedup = read_csv(DEDUP) if os.path.exists(DEDUP) else []
    addr_fix = read_csv(ADDR) if os.path.exists(ADDR) else []
    addr_filled = sum(1 for r in addr_fix if (r.get("address") or "").strip())

    # CAP coverage
    caps = collections.Counter()
    for r in out:
        m = re.findall(r'\b(20\d{3})\b', r.get("address", ""))
        if m: caps[m[0]] += 1
    caps_ge3 = sorted([c for c, n in caps.items() if n >= 3])

    geoconf_out = collections.Counter((r.get("geocoding_confidence") or "none") for r in out)

    L = []
    A = L.append
    A("# Agent 6 — Report S6: venues drink no-price standardizzati\n")
    A(f"_Generato da `scripts/agent6_*.py` · vertical drink Milano · {n_out} venues in output_\n")
    A("## 1. Sintesi esecutiva (per CEO)\n")
    A(f"- **{by_cls.get('TARGET',0)} venues TARGET** + **{by_cls.get('AMBIGUOUS_TO_REVIEW',0)} AMBIGUOUS_TO_REVIEW** "
      f"= **{n_out} venues** in `agent6_venues_no_price.csv`, puliti/deduplicati/categorizzati, pronti come pin \"no price yet\".")
    A(f"- **{geo_conf.get('precise',0)+geo_conf.get('web_addr',0)} venues geocodate con precisione** "
      f"(precise {geo_conf.get('precise',0)} + web_addr {geo_conf.get('web_addr',0)}) su {len(geo)} no-geo processate; "
      f"{geo_conf.get('fallback',0)} → fallback Duomo.")
    A(f"- **{len(dedup)} cluster di nomi duplicati** consolidati (canonical + all_names).")
    A(f"- **{addr_filled} address** riempiti via reverse-geocoding (popup-ready).")
    A(f"- Quality gate inline: esclusi i NO_TARGET (ristoranti/pizzerie), i CAP non-Milano, i geo fuori bbox, i nomi-piattaforma.\n")

    A("## 1b. Integrazione con `data/unified_venues_no_price.csv` (pipeline CEO)\n")
    A("Il CEO ha creato in parallelo `data/unified_venues_no_price.csv` (4.124 venues: 1.247 unified_db + "
      "2.867 ckan_milano + 10 eatbu) — **senza `target_classification` e con `venue_type` vuoto sui 1.247 unified_db**.")
    A("Questo deliverable lo completa. Join consigliato **per `venue_name`** (o norm_name):")
    A("- aggiunge **`target_classification`** → permette di **nascondere dalla mappa i ~537 NO_TARGET** (ristoranti/pizzerie/sushi);")
    A(f"- riempie **`venue_type`** per gli unified_db (qui {by_vt.get('cafe',0)+by_vt.get('cocktail_bar',0)+by_vt.get('pub',0)}+ tipizzati);")
    A("- porta il **canonical name + all_names** (dedup di 43 cluster) per evitare pin doppi.")
    A("> NB: i venues CKAN/OSM discovery (S7, fuori scope S6) non sono classificati qui; la stessa logica "
      "`classify_venue`/`detect_venue_type` di `agent6_standardize.py` è riusabile su di essi.\n")

    A("## 2. Step 1 — Classificazione TARGET (pool no-price)\n")
    A("| Classe | Count | Note |")
    A("|---|---:|---|")
    A(f"| TARGET | {pool_cls.get('TARGET',0)} | bar/pub/caffè/cocktail/wine bar… |")
    A(f"| AMBIGUOUS | {pool_cls.get('AMBIGUOUS',0)} | nessuna keyword o food+bar pari → review |")
    A(f"| NO_TARGET | {pool_cls.get('NO_TARGET',0)} | ristoranti/pizzerie/sushi → esclusi dall'output |")
    A(f"| **Pool totale** | **{len(nop)}** | venues senza prezzo nel DB |")
    A("\nIn output (post quality-gate, deduplicati): "
      f"**{by_cls.get('TARGET',0)} TARGET** + **{by_cls.get('AMBIGUOUS_TO_REVIEW',0)} AMBIGUOUS_TO_REVIEW**.\n")

    A("## 3. Step 4 — Distribuzione venue_type (output)\n")
    A("| venue_type | Count | Definizione |")
    A("|---|---:|---|")
    for vt in ['cocktail_bar','pub','cafe','wine_bar','aperitivo_bar','bistro','craft_beer','rooftop','hotel_bar','unknown']:
        A(f"| {vt} | {by_vt.get(vt,0)} | {VT_DESC[vt]} |")
    real_types = [vt for vt in VT_DESC if vt != 'unknown']
    pop_real = [vt for vt in real_types if by_vt.get(vt, 0) > 0]
    miss = [vt for vt in real_types if by_vt.get(vt, 0) == 0]
    A(f"\nTipi reali rappresentati: **{len(pop_real)}/9** (+ {by_vt.get('unknown',0)} unknown)."
      + (f" Assente: **{', '.join(miss)}** — vedi nota." if miss else ""))
    A("> Nota `aperitivo_bar`: 0 nel pool no-price perché i locali con \"aperitivo\" esplicito nei metadata "
      "(Camparino, Bar Basso…) sono già prezzati e sulla mappa. Non forzo classificazioni inventate.\n")

    A("## 4. Step 3 — Geocoding (no-geo TARGET/AMBIG)\n")
    A("| confidence | Count |")
    A("|---|---:|")
    for c in ['precise','web_addr','fallback']:
        A(f"| {c} | {geo_conf.get(c,0)} |")
    A(f"| **totale processate** | **{len(geo)}** |")
    A(f"\nMetodi: {dict(geo_meth)}")
    A(f"\n> **Onestà sui numeri**: target prompt \"≥100 precise+web_addr/137\" non raggiungibile: "
      f"dei 137 no-geo, 39 sono NO_TARGET (esclusi dall'output → non geocodati) e ~73 dei restanti non avevano "
      f"address (solo JSON-LD geo da website/menu, hit-rate parziale). Ceiling reale ~{len(geo)} candidati in-scope.\n")

    A("## 5. Step 2 — Cluster nomi consolidati\n")
    A(f"**{len(dedup)} cluster** con duplicati nel pool no-price. Canonical = nome più formale "
      "(slug e mojibake penalizzati). Esempi:\n")
    A("| canonical_name | all_variants | dupe |")
    A("|---|---|---:|")
    for r in dedup[:15]:
        A(f"| {r['canonical_name']} | {r['all_variants'][:50]} | {r['dupe_count']} |")

    A("\n## 6. Copertura metadata (output)\n")
    A("| Campo | Coverage |")
    A("|---|---:|")
    for k in ['address','latitude','website','phone','opening_hours','menu_url','categories']:
        A(f"| {k} | {cov(k)}/{n_out} ({100*cov(k)//max(1,n_out)}%) |")
    A(f"\ngeocoding_confidence in output: {dict(geoconf_out)}")

    def is_city(c):
        return c == '20100' or 20121 <= int(c) <= 20162
    city_caps = sorted(c for c in caps if is_city(c))
    hint_caps = sorted((c for c in caps if not is_city(c)), key=lambda c: -caps[c])
    hint_n = sum(caps[c] for c in hint_caps)
    city_ge3 = [c for c in caps_ge3 if is_city(c)]

    A("\n## 7. Quartieri Milano (CAP 20XXX) coperti\n")
    A(f"CAP distinti: **{len(caps)}** ({len(city_caps)} città + {len(hint_caps)} hinterland). "
      f"CAP **città** con ≥3 venues: **{len(city_ge3)}** ({', '.join(city_ge3)}).\n")
    A(f"> ⚠️ **Hinterland**: {hint_n} venues hanno CAP di comuni limitrofi (non Milano città) — "
      f"{', '.join(f'{c}×{caps[c]}' for c in hint_caps[:8])}. Sono entro la bbox e ammessi dal gate "
      f"`is_milan_or_unknown` (qualsiasi 20xxx) come nel merge_pipeline. **Il CEO può filtrarli** "
      f"a CAP 20121–20162 se serve solo Milano città.\n")
    A("Top 15 CAP per densità:\n")
    A("| CAP | venues |")
    A("|---|---:|")
    for cap, n in caps.most_common(15):
        A(f"| {cap} | {n} |")

    A("\n## 8. Issues residui / TODO (per CEO)\n")
    A("- **aperitivo_bar = 0**: non determinabile dai metadata dei no-price (vedi §3).")
    A("- **phone / opening_hours non arricchiti in massa**: ROI basso (phone 8% coverage, ~700 fetch @2s; "
      "il popup mockup non li mostra). Lasciati ai valori esistenti. Candidato a sessione dedicata se servono.")
    A(f"- **{geo_conf.get('fallback',0)} venues su fallback Duomo**: geo imprecisa. Possibile top-up via WebSearch "
      "address (strategia 4) o crowdsourcing.")
    A("- **Duomo-stacked legacy** (lat=45.4642 esistenti, fuori scope Step 3 che filtra solo lat=''): da verificare in un pass futuro.")
    A("- **AMBIGUOUS_TO_REVIEW**: il prompt suggerisce HTML-peek di menu_url per cocktail/spritz/aperitivo. "
      "Non eseguito in massa (costo fetch); risolti via categorie OSM/mycia dove disponibili.")
    A("- **comune_osm 4.649** (S7 discovery) e prezzi nuovi: fuori scope S6.\n")
    A("## 9. File consegnati\n")
    A("- `raw_sources/agent6_venues_no_price.csv` — master TARGET+AMBIGUOUS (schema esteso)")
    A("- `raw_sources/agent6_geocode_fixes.csv` — Step 3 geocoding")
    A("- `raw_sources/agent6_name_dedup.csv` — Step 2 mappatura nomi")
    A("- `raw_sources/agent6_address_fixes.csv` — Step 5 address reverse-geocoded")
    A("- `scripts/agent6_standardize.py` / `agent6_geocode.py` / `agent6_enrich.py` / `agent6_report.py`")
    A("\n> NON toccati: `data/unified_*.csv`, `prices_data.json`, `index.html`, vertical beach. "
      "Riusata `scripts/normalization.py` (is_milan_or_unknown). Classificazione venue/venue_type = logica S6-specifica.")

    open(OUT, "w", encoding="utf-8").write("\n".join(L) + "\n")
    print(f"✍  scritto {OUT} ({n_out} venues, {len(geo)} geo, {len(dedup)} cluster)")


if __name__ == "__main__":
    main()
