# CLAUDE.md — Entry point per sessioni Claude Code

> Claude Code legge automaticamente questo file all'avvio.
> Leggi questo, poi identifica il tuo ruolo, poi leggi il file specifico.

---

## Il progetto: SurPrice

Aggregatore prezzi neutro per servizi italiani.
Sito: https://mtom123.github.io/FindMyDeal/ | Repo: https://github.com/mtom123/FindMyDeal

Verticals: **Drink** (Milano) · **Beach** (Italia) · **Barber** (Italia) · **Gym** (Italia, in corso)

---

## Identifica il tuo ruolo e leggi il file giusto

| Sei... | Leggi subito |
|--------|-------------|
| **CEO / Orchestratore** | `CEO_HANDOFF_PROMPT.md` → `AGENTS_STATE.md` |
| **Pietro** (scraper agent) | `PROMPT_PIETRO_S9.md` → `AGENTS_STATE.md` |
| **Peppe** (frontend dev) | `PROMPT_PEPPE_BARBIERI_S1.md` → `barber_s1_REPORT_PEPPE.md` |
| Nuovo collaboratore | `AGENTS.md` → `AGENTS_STATE.md` → `CHANGELOG.md` |

**Non iniziare nessun lavoro prima di leggere `AGENTS_STATE.md`** — contiene lo stato attuale di tutti i verticals e cosa è già stato fatto. Duplicare lavoro è lo spreco più costoso.

---

## File sempre aggiornati (fonte di verità)

- `AGENTS.md` — workflow, regole git, naming convention, errori da non ripetere
- `AGENTS_STATE.md` — numeri aggiornati per ogni vertical, task attivi
- `CHANGELOG.md` — storia decisioni e ragionamenti
- `CEO_HANDOFF_PROMPT.md` — contesto CEO completo per nuove sessioni

---

## Regola d'oro

**Un file per sessione di lavoro, non dieci.**
Se stai per creare un nuovo markdown, chiediti: può andare in CHANGELOG.md? È davvero necessario?
Prompt attivi (`PROMPT_PIETRO_S9.md`) e report CEO (`gym_s1_REPORT_CEO.md`) vanno bene.
"Note varie sessione" non vanno committatate — mettile nel corpo del commit message.
