# CLAUDE.md — Entry point for Claude Code sessions

> Claude Code legge automaticamente questo file all'avvio della sessione.
> Lo scopo è indirizzarti al file giusto in base al tuo ruolo.

---

## 👉 Leggi `AGENTS.md` per primo

`AGENTS.md` contiene l'onboarding completo: ruoli, workflow, regole, link.

Poi in base al tuo ruolo:

| Sei... | Leggi |
|---|---|
| Un **agente scraper** (Pietro o altri) | `AGENTS.md` → `AGENTS_STATE.md` → `scripts/SCHEMA_AGENTI.md` → eventuale prompt specifico (`PROMPT_PIETRO_NOTTE.md`) |
| Il **frontend dev** (Peppe) | `AGENTS.md` → `BRIEF_PEPPE.md` → guarda `index.html` |
| Il **CEO / Orchestratore** | `AGENTS.md` → `CHANGELOG.md` → `scripts/merge_pipeline.py` |
| Curioso / nuovo collaboratore | `README.md` per la visione generale, poi `AGENTS.md` |

---

## File chiave del repo

- `AGENTS.md` — onboarding agenti, workflow, regole
- `AGENTS_STATE.md` — cosa è fatto / cosa serve (NON duplicare lavoro)
- `CHANGELOG.md` — storico decisioni e ragionamenti (capisci IL PERCHÉ)
- `raw_sources/README.md` — identità di ogni file CSV
- `scripts/SCHEMA_AGENTI.md` — formato CSV obbligatorio
- `BRIEF_PEPPE.md` — istruzioni frontend
- `PROMPT_PIETRO_NOTTE.md` — prompt deep scraping notturno

**Tutto il resto è codice o dati. Leggi i markdown prima.**
