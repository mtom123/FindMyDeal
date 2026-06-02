"""
gym_s1_run_all.py — Orchestratore prezzi palestre

Esegue in sequenza:
  1. gym_s1_chains.py      → prezzi catene nazionali
  2. gym_s1_fitprime_prices.py → piani FitPrime + day pass
  3. gym_s1_reviews_miner.py  → mining recensioni Google Maps

Poi genera un report riassuntivo.
"""

import subprocess, sys, os, csv, json
from datetime import datetime

SCRIPTS_DIR = os.path.dirname(__file__)
PY = sys.executable

steps = [
    ('Chain pricing (McFit, FitActive, Virgin, Anytime...)', 'gym_s1_chains.py'),
    ('FitPrime piani + day pass', 'gym_s1_fitprime_prices.py'),
    ('Google Maps reviews mining', 'gym_s1_reviews_miner.py'),
]

def run_step(label: str, script: str):
    path = os.path.join(SCRIPTS_DIR, script)
    print(f"\n{'='*60}")
    print(f"STEP: {label}")
    print(f"Script: {script}")
    print('='*60)
    result = subprocess.run([PY, path], cwd=SCRIPTS_DIR, timeout=600)
    return result.returncode == 0

def generate_report():
    out_files = [
        ('Chain prices', os.path.join(SCRIPTS_DIR, 'gym_chain_prices.csv')),
        ('FitPrime prices', os.path.join(SCRIPTS_DIR, 'gym_fitprime_prices.csv')),
        ('Reviews prices', os.path.join(SCRIPTS_DIR, 'gym_reviews_prices.csv')),
    ]
    print(f"\n{'='*60}")
    print(f"GYM S1 PRICING REPORT — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print('='*60)
    total = 0
    for label, path in out_files:
        if os.path.exists(path):
            with open(path, newline='', encoding='utf-8') as f:
                rows = list(csv.DictReader(f))
            print(f"\n{label}: {len(rows)} record")
            total += len(rows)

            # Raggruppa per tipo prezzo
            by_type = {}
            for r in rows:
                t = r.get('price_type') or r.get('tipo', 'unknown')
                by_type.setdefault(t, []).append(r)
            for t, items in by_type.items():
                prices = []
                for item in items:
                    try:
                        prices.append(float(item.get('price') or item.get('price_eur') or 0))
                    except:
                        pass
                if prices:
                    print(f"  [{t}] n={len(prices)} min={min(prices):.2f}€ max={max(prices):.2f}€ avg={sum(prices)/len(prices):.2f}€")
        else:
            print(f"\n{label}: file non trovato")

    print(f"\nTOTALE PREZZI ESTRATTI: {total}")
    return total

if __name__ == '__main__':
    success_count = 0
    for label, script in steps:
        ok = run_step(label, script)
        if ok:
            success_count += 1
        else:
            print(f"  WARN: step fallito, continuo...")

    total = generate_report()

    print(f"\n{'='*60}")
    print(f"Steps completati: {success_count}/{len(steps)}")
    print(f"Prezzi totali estratti: {total}")
    if total > 0:
        print("SUCCESS — dati pronti per upload su Supabase")
    else:
        print("ATTENZIONE — 0 prezzi estratti, controlla i singoli script")
