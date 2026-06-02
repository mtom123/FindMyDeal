# PROMPT PIETRO — S9: Gym Website Price Scraping
**CEO, 2026-06-02**

---

Pietro, S8 drink completato perfettamente — 6 città, 6.036 venue, 100% opening hours. Ottimo lavoro.

## Il tuo task S9: Gym website price scraping

Ho costruito uno script pronto. Il tuo lavoro: girarlo su tutte le 3.095 palestre con sito web e riportarmi i risultati. È un task di esecuzione + monitoring, non di coding.

---

## Setup

```bash
# 1. Assicurati di avere playwright installato
pip install playwright playwright-stealth
playwright install chromium

# 2. Entra nella cartella
cd agent_ceo_gym/

# 3. Imposta encoding Windows (IMPORTANTE)
$env:PYTHONIOENCODING = "utf-8"
```

---

## Modifica necessaria prima di lanciare

Apri `gym_s1_websites.py` e trova questa riga:
```python
gyms = gyms[:150]
```
Cambiala in:
```python
gyms = gyms[:3095]
```
(io ho girato solo 150 per test iniziale, tu fai il full run)

---

## Come lanciare

```bash
# Full run con logging
python gym_s1_websites.py > gym_s9_log.txt 2>&1
```

Durata stimata: 45-90 minuti (dipende dalla velocità dei siti).
Salva un checkpoint ogni 20 venue, quindi se si interrompe puoi vedere i progressi.

---

## Output che mi serve

Quando finisce, dimmi nel tuo report:
1. Quante palestre hanno prezzi trovati (X / 3.095)
2. Breakdown per tipo di prezzo:
   - mensile: n=? min=?€ max=?€ avg=?€
   - day_pass: n=? min=?€ max=?€
   - annuale: n=?
   - iscrizione: n=?
3. Top 10 palestre con il prezzo mensile più basso
4. Qualsiasi errore strano o pattern interessante che noti

---

## Poi: commit e push

```bash
git add agent_ceo_gym/gym_website_prices.csv
git add agent_ceo_gym/gym_s9_log.txt
git commit -m "data: S9 gym — X venue prezzate, website direct scraping"
git push
```

---

## Note tecniche

- Lo script usa Claude Haiku per validare i prezzi trovati → serve ANTHROPIC_API_KEY nell'environment
- Se Claude Haiku non è disponibile, usa regex fallback (comunque funziona)
- Il context text nei CSV potrebbe avere caratteri strani (encoding issue Windows, non preoccuparti, i numeri sono giusti)
- Rate limiting: 1 secondo tra ogni sito, già gestito dallo script

---

## Dopo S9 (se vuoi fare di più — opzionale)

Se hai tempo, prova anche `gym_s1_classpass.py` — cerca prezzi day-pass su ClassPass.
Browser headed (apre Chrome visibile), cerca palestre per città.
Ma prima dimmi se S9 è andato bene.

---

Grazie Pietro. Output atteso: 200-500 palestre prezzate dai loro siti web.

— CEO
