# SurPrice — Agent Onboarding

> **LEGGI QUESTO FILE PER PRIMO.** Poi `AGENTS_STATE.md`. Poi il tuo prompt specifico.
> Tempo di lettura: 8 minuti. Non skippare.

---

## Cos'è il progetto

**SurPrice** — aggregatore prezzi neutro per servizi italiani.
Sito live: https://mtom123.github.io/FindMyDeal/
Repo: https://github.com/mtom123/FindMyDeal

Verticals attivi: **Drink** (Milano) · **Beach** (Italia) · **Barber** (Italia) · **Gym** (Italia, in corso)

---

## Chi fa cosa

| Ruolo | Chi | Compito attuale |
|-------|-----|-----------------|
| **CEO / Orchestratore** | Motti (Claude) | Merge authority, qualità dati, commit finali, orchestrazione |
| **Scraper Agent** | Pietro | Scraping dati — drink, gym websites |
| **Frontend Dev** | Peppe | Implementa verticali sul sito — ora: barbieri |

**Se sei un agente Claude appena avviato**: identifica il tuo ruolo dal prompt iniziale che ti è stato dato. Se non è chiaro, sei il CEO.

---

## Struttura repo (root = quello che vedi su GitHub)

```
/                           ← ROOT ATTIVO (file correnti)
├── AGENTS.md               ← QUESTO FILE
├── AGENTS_STATE.md         ← stato corrente di tutti i verticals
├── CEO_HANDOFF_PROMPT.md   ← context completo per nuovo agent CEO
├── CHANGELOG.md            ← storia decisioni (capisci il PERCHÉ)
├── CLAUDE.md               ← entry point Claude Code
├── COLLABORATORI.md        ← onboarding umani
├── README.md               ← presentazione pubblica
│
├── PROMPT_PIETRO_S9.md     ← task attivo Pietro
├── PROMPT_PEPPE_BARBIERI_S1.md  ← task attivo Peppe
├── PROMPT_PEPPE_GYM_FRONTEND_BRIEF.md  ← prossimo task Peppe (dopo barbieri)
├── barber_s1_REPORT_PEPPE.md    ← spec tecnica frontend barbieri
├── barber_s1_REPORT_CEO.md      ← report CEO barber S1
├── beach_phase3_REPORT.md       ← report beach (reference)
├── DATA_ACCESS_BEACH.md         ← reference dati beach
├── DATA_QUALITY_REPORT.md       ← metriche qualità
├── SUPABASE_SETUP_TONIGHT.md    ← schema SQL crowdsourcing gym
│
├── data/                   ← OUTPUT dati (NON modificare a mano)
│   ├── barber_data.json    ← feed frontend barbieri (16MB)
│   └── ...
│
├── raw_sources/            ← INPUT scraper (drop zone)
│   └── ...
│
├── scripts/                ← script Python
│   ├── SCHEMA_AGENTI.md    ← formato CSV obbligatorio
│   ├── normalization.py    ← libreria normalizzazione condivisa
│   └── ...
│
├── agent_ceo_gym/          ← script + dati vertial gym
│   ├── gym_master_italia.csv
│   ├── gym_chain_prices.csv
│   ├── gym_s1_chains.py
│   ├── gym_s1_websites.py
│   └── ...
│
└── archive/                ← prompt e report completati (tieni per context, non modificare)
```

---

## Workflow Git — REGOLE OBBLIGATORIE

### Setup una volta sola (su ogni macchina del team)

```bash
git config --global pull.rebase true
```

Questo è tutto. Tutti lavorano su `main` direttamente — CEO, Pietro, Peppe — senza branch.

### Perché "Merge branch 'main'" succede (e come evitarlo)

Succede quando fai `git commit` in locale e poi fai `git pull` mentre ci sono nuovi commit remoti. Git vede due storie divergenti e crea un merge commit automatico. Con `pull.rebase true` invece riapplica i tuoi commit sopra quelli remoti → storia pulita, nessun merge commit.

### Workflow per tutti (CEO, Pietro, Peppe)

```bash
git pull --rebase origin main     # SEMPRE prima di iniziare
# ... lavora ...
git add <file specifici>
git commit -m "tipo: descrizione chiara"
git push origin main
# avvisa il CEO se hai pushato dati da mergiare
```

### Workflow CEO

```bash
git pull --rebase origin main
# ... merge, aggiorna AGENTS_STATE.md, CHANGELOG.md ...
git add -A
git commit -m "ceo: [descrizione chiara]"
git push origin main
```

---

## Regole su file e commit — NON CREARE CASINO

### Naming dei file

| Tipo | Pattern | Esempio |
|------|---------|---------|
| Prompt per agente | `PROMPT_{NOME}_{VERTICAL}_{SESSION}.md` | `PROMPT_PIETRO_GYM_S9.md` |
| Report CEO | `{vertical}_REPORT_CEO.md` | `gym_s1_REPORT_CEO.md` |
| Report per Peppe | `{vertical}_REPORT_PEPPE.md` | `barber_s1_REPORT_PEPPE.md` |
| Script scraping | `{vertical}_s{N}_{cosa}.py` | `gym_s1_websites.py` |
| Dati raw | `raw_sources/{vertical}_{fonte}_{tipo}.csv` | `raw_sources/barber_s1_treatwell_venues.csv` |
| Dati master | `{vertical}_master_{scope}.csv` | `gym_master_italia.csv` |

### Cosa NON committare

```
❌ File di debug/test temporanei (check_urls.py, test_*.py)
❌ File di log (.txt, .log) a meno che non siano report finali
❌ Dump HTML/JSON intermedi (fitprime_dump/, api_dump/)
❌ __pycache__/, .env, chiavi API
❌ File CSV intermedi non consolidati
```

### Cosa committare

```
✅ Script finiti e funzionanti
✅ CSV di output consolidati (master, prices)
✅ Prompt e brief per il team
✅ Report CEO dei risultati
✅ Aggiornamenti a AGENTS_STATE.md e CHANGELOG.md
```

### Granularità dei commit

**Un commit = un lavoro logico compiuto.**

```bash
# BUONO:
git commit -m "data: S9 gym — 340 venue prezzate da 3095 siti web"
git commit -m "feat: barber frontend — mappa base, marker esagonali funzionanti"
git commit -m "ceo: gym S1 pricing scripts + 12 prezzi catene"

# CATTIVO:
git commit -m "update"
git commit -m "fix"
git commit -m "vari cambiamenti"
git commit -m "Merge branch 'main' of https://github.com/..."  ← vedi sopra
```

---

## Regole dati — NON MODIFICARE OUTPUT A MANO

| File | Chi lo modifica | Come |
|------|----------------|------|
| `data/unified_*.csv` | Solo merge_pipeline.py | `python scripts/merge_pipeline.py` |
| `data/barber_data.json` | Solo script consolidamento | `python scripts/barber_s1_consolidate.py` |
| `prices_data.json` | Solo build script | `python scripts/build_outputs.py` |
| `raw_sources/*.csv` | Gli scraper agent | Drop zone: deposita e avvisa CEO |
| `agent_ceo_gym/*.csv` | Script gym o CEO | Non editare manualmente |

**Se trovi un errore nei dati**: segnalalo al CEO con issue GitHub. Non correggere il file direttamente.

---

## Errori da non ripetere

1. **Peppe committa direttamente su main** → merge conflict + storia sporca. Usa branch.
2. **"Merge branch 'main'"** nei commit → usa `git pull --rebase` o configura `pull.rebase true`.
3. **Creare mille file markdown** per ogni sessione → usa CHANGELOG.md per i ragionamenti, non file separati.
4. **Pushare dump HTML/JSON** da Playwright → sono in .gitignore, tienili fuori.
5. **Duplicare scraping già fatto** → leggi AGENTS_STATE.md prima di iniziare.
6. **Non avvisare il CEO** dopo aver pushato dati → il CEO non sa che ci sono nuovi raw_sources da mergiare.

---

## Come aggiornare lo stato del progetto

Dopo ogni sessione di lavoro significativa:
1. Aggiorna `AGENTS_STATE.md` con i nuovi numeri
2. Aggiorna `CHANGELOG.md` con il ragionamento
3. Aggiorna `CEO_HANDOFF_PROMPT.md` se cambia lo stato globale

**Non creare nuovi file markdown per ogni sessione** — accumulate diventano rumore.
L'eccezione: prompt specifici (`PROMPT_PIETRO_S9.md`) e report CEO (`gym_s1_REPORT_CEO.md`) — questi hanno senso.

---

## Quick reference per agenti

```
Sono Pietro (scraper):
  → Leggi PROMPT_PIETRO_S9.md
  → Leggi AGENTS_STATE.md per non duplicare
  → Scrivi in raw_sources/ o agent_ceo_gym/
  → Commit + avvisa CEO

Sono Peppe (frontend):
  → Leggi PROMPT_PEPPE_BARBIERI_S1.md + barber_s1_REPORT_PEPPE.md
  → Crea branch feat/barber-frontend
  → PR al CEO prima del merge

Sono CEO:
  → Leggi CEO_HANDOFF_PROMPT.md
  → Stato attuale in AGENTS_STATE.md
  → Merge authority su tutto
```

---

## Link rapidi

- Sito live: https://mtom123.github.io/FindMyDeal/
- Repo: https://github.com/mtom123/FindMyDeal
- Schema CSV: `scripts/SCHEMA_AGENTI.md`
- Stato verticals: `AGENTS_STATE.md`
- Storia decisioni: `CHANGELOG.md`
