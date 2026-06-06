#!/usr/bin/env python3
"""S9 finalize: merge shard CSVs → gym_website_prices.csv + report stats."""
import csv, glob, os, json, collections

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'gym_website_prices.csv')
FIELDS = ['gym_id', 'name', 'city', 'lat', 'lon', 'price', 'price_type',
          'confidence', 'context', 'source_url', 'source']


def main():
    rows, seen = [], set()
    for f in sorted(glob.glob(os.path.join(HERE, 'gym_website_prices_s*.csv'))):
        for r in csv.DictReader(open(f, encoding='utf-8')):
            key = (r.get('gym_id', ''), r.get('price', ''), r.get('price_type', ''))
            if key in seen:
                continue
            seen.add(key)
            rows.append(r)
    with open(OUT, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, '') for k in FIELDS})

    # progress totale (gym processati)
    done = 0
    for pf in glob.glob(os.path.join(HERE, 'gym_s9_progress_s*.json')):
        try: done += len(json.load(open(pf)))
        except Exception: pass

    priced_gyms = len(set(r['gym_id'] for r in rows if r.get('gym_id')))
    print(f"=== S9 FINALE ===")
    print(f"Gym processati: {done}/3095")
    print(f"Gym con prezzi: {priced_gyms}")
    print(f"Price points totali: {len(rows)}")
    print(f"Output: {OUT}\n")

    by_type = collections.defaultdict(list)
    for r in rows:
        try: by_type[r['price_type']].append(float(r['price']))
        except (ValueError, TypeError): pass
    print("Breakdown per tipo:")
    for t in ['mensile', 'day_pass', 'annuale', 'iscrizione']:
        ps = by_type.get(t, [])
        if ps:
            print(f"  {t:11} n={len(ps):3} min={min(ps):.0f}€ max={max(ps):.0f}€ avg={sum(ps)/len(ps):.0f}€")
        else:
            print(f"  {t:11} n=0")
    other = [t for t in by_type if t not in ('mensile', 'day_pass', 'annuale', 'iscrizione')]
    for t in other:
        ps = by_type[t]
        print(f"  {t:11} n={len(ps)} (altro)")

    print("\nTop 10 mensile più economici:")
    monthly = [(float(r['price']), r['name'], r['city']) for r in rows
               if r['price_type'] == 'mensile' and r.get('price')]
    for price, name, city in sorted(monthly)[:10]:
        print(f"  {price:6.0f}€  {name[:40]} ({city})")

    print("\nPer città (top):")
    bycity = collections.Counter(r['city'] for r in rows if r.get('city'))
    for c, n in bycity.most_common(8):
        print(f"  {c}: {n} price points")


if __name__ == '__main__':
    main()
