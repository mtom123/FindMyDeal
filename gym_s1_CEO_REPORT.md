# GYM S1 — CEO Report
**Data**: 2026-06-02  
**Autore**: CEO Agent

---

## Status: 12 prezzi estratti, framework completo pronto

### Dati estratti oggi

| Chain | Tipo | Prezzo | Note |
|-------|------|--------|------|
| McFit | mensile base | 34.90€ | Piano standard |
| McFit | mensile premium | 49.90€ | Piano Plus/All-Access |
| McFit | promo | 10€/mese | Speciale maggio (tempo limitato) |
| FitActive | mensile entry | 9.90€ | Offerta base |
| FitActive | mensile standard | 19.90€ | Piano annuale online |
| Gympass | piano 1 | 9.99€ | Employee welfare |
| Gympass | piano 2 | 19.99€ | Employee welfare |
| Gympass | piano 3 | 36.99€ | Employee welfare |
| Gympass | piano 4 | 59.99€ | Employee welfare |
| Gympass | piano 5 | 79.99€ | Employee welfare |
| Gympass | piano 6 | 94.99€ | Employee welfare |
| Gympass | piano 7 | 119.99€ | Employee welfare |
| Gympass | piano 8 | 164.99€ | Employee welfare premium |

**File**: `agent_ceo_gym/gym_chain_prices.csv`

---

## Scoperte chiave

### FitPrime è diventata B2B
FitPrime si è trasformata in piattaforma B2B (come Wellhub/Gympass) - tutti i piani consumer sono stati eliminati. Le 1.605 palestre FitPrime nel nostro master non hanno più prezzi pubblici su quel portale.

### Catene con prezzi nascosti
- **Virgin Active**: prezzi completamente nascosti, solo "richiedi info"  
- **Anytime Fitness**: prezzi per club, nessuna pubblicazione online  
- **Basic-Fit**: pagine pricing 404 (potrebbero non essere ancora in Italia)

### Catene low-cost con prezzi pubblici
- **McFit**: 34.90-49.90€/mese (chiari, da __NEXT_DATA__)  
- **FitActive**: 9.90-19.90€/mese (da HTML diretto)  
- **Gympass**: piani aziendali 9.99-164.99€/mese (per dipendenti)

---

## Script creati (pronti all'uso)

| Script | Stato | Descrizione |
|--------|-------|-------------|
| `gym_s1_chains.py` | ✅ FUNZIONANTE | Prezzi catene nazionali |
| `gym_s1_fitprime_prices.py` | ⚠️ FitPrime B2B | Rimane per future catene simili |
| `gym_s1_reviews_miner.py` | 🔧 PRONTO | Mining Google Maps recensioni (serve API key) |
| `gym_s1_classpass.py` | 🔧 PRONTO | ClassPass day pass (richiede headed + stealth) |
| `gym_s1_run_all.py` | ✅ ORCHESTRATORE | Lancia tutti gli step |

---

## Prossimi step prioritari

### Priorità 1: ClassPass (questa settimana)
1. Installa `playwright-stealth`: `pip install playwright-stealth`  
2. Esegui `gym_s1_classpass.py` (headless=False, richiede Cloudflare bypass)  
3. Se bloccato: crea account su classpass.com → salva cookies → rilancia  
4. Target: prezzi day pass in crediti per centinaia di palestre  

### Priorità 2: Google Maps Reviews (questa settimana)
1. Ottieni `GOOGLE_PLACES_API_KEY` (o usa scraping Playwright)  
2. Esegui `gym_s1_reviews_miner.py`  
3. Target: estrarre "pago X€/mese" dalle recensioni top 10 città  
4. LLM: usa `ANTHROPIC_API_KEY` o `OPENAI_API_KEY`  

### Priorità 3: Supabase crowdsourcing (stasera)
Schema tabella da creare:
```sql
CREATE TABLE gym_prices (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  gym_id TEXT REFERENCES gyms(id),
  prezzo_mensile DECIMAL(8,2),
  prezzo_annuale DECIMAL(8,2),
  day_pass DECIMAL(8,2),
  iscrizione DECIMAL(8,2),
  user_id UUID REFERENCES auth.users(id),
  confidenza TEXT DEFAULT 'user_submitted',
  note TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  verified BOOLEAN DEFAULT FALSE
);
```

### Priorità 4: Siti web singole palestre (prossima settimana)
Script automatico che:
- Carica URL website dal master CSV
- Visita `/prezzi`, `/abbonamenti`, `/iscrizione`  
- Estrae prezzi con regex + LLM  
- Target: 500 palestre con website nel master  

---

## Task per Peppe

### IMMEDIATO: Frontend Barbieri S1
Il brief `PROMPT_PEPPE_BARBIERI_S1.md` è nel repo - implementare subito.  
Marker esagonali viola, filtro genere → categoria servizio, color-tier vs mediana regionale.

### PROSSIMO: Frontend Gym
Dopo Supabase: mappa palestre con overlay prezzi (marker colorati in base a fascia €).

---

## Istruzioni per Pietro

Pietro deve fare S9: scraping prezzi singole palestre.  
Quando pronto, gli invio `PROMPT_PIETRO_S9.md`.

---

## Note tecniche

### Encoding Windows
Tutti gli script usano `sys.stdout.reconfigure(encoding='utf-8')` o `PYTHONIOENCODING=utf-8`.

### Rate limiting
- McFit: 3s tra richieste ✅  
- FitActive: timeout a 25s (sito lento) ✅  
- ClassPass: richiede stealth mode per evitare Cloudflare  

### Struttura dati output
```
agent_ceo_gym/
  gym_chain_prices.csv     ← 12 prezzi catene (PRONTO)
  gym_fitprime_prices.csv  ← vuoto (FitPrime B2B)
  gym_classpass_prices.csv ← da generare
  gym_reviews_prices.csv   ← da generare
```
