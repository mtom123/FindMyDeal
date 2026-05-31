# Guida collaboratori — FoodPrice Milano

> Questo file è stato consolidato in **`AGENTS.md`**.
> Tutto quello che serve per onboarding è lì.

## TL;DR per nuovi collaboratori

```bash
git clone https://github.com/mtom123/FindMyDeal.git
cd FindMyDeal
```

Poi leggi nell'ordine:
1. **`AGENTS.md`** — chi fa cosa, workflow, regole
2. **`AGENTS_STATE.md`** — cosa è già fatto
3. **`CHANGELOG.md`** — perché è stato fatto così
4. Il file specifico per il tuo ruolo:
   - Scraper: `scripts/SCHEMA_AGENTI.md` + eventuale prompt (`PROMPT_PIETRO_NOTTE.md`)
   - Frontend: `BRIEF_PEPPE.md`

## Setup tecnico minimo

```bash
pip install requests beautifulsoup4 lxml tqdm
```

Per scraping avanzato:
```bash
pip install playwright playwright-stealth pdfplumber
playwright install chromium
```

## Domande?

Apri Issue su GitHub o contatta il CEO.
