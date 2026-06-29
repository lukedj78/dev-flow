# Relazione di stato — skill dev-flow + loop engineering

_Data: 2026-06-29 · Branch: `feat/eve-agent-skill` · PR: lukedj78/dev-flow#1_

Relazione dettagliata del lavoro svolto, delle decisioni prese, di cosa è **fatto**, cosa è
solo **documentato**, e cosa **manca** per avere un loop di sviluppo autonomo funzionante.

---

## 1. Sintesi esecutiva

In questa sessione abbiamo fatto due cose distinte:

1. **Lavoro sulle skill (completato e committato):** creata la skill `eve-agent`, integrata
   in `dev-flow`, aggiunti i moduli `voice` e `realtime` a `module-add`, aggiornati registry
   e installer. Tutto su un branch con PR aperta.
2. **Progettazione del loop engineering (documentata, NON configurata):** decise le scelte
   infrastrutturali (Linear, Hetzner CX23, subscription Claude, GitHub) e scritto un runbook
   + uno script di provisioning. **Nulla è ancora in esecuzione**: nessun server, nessun
   loop attivo.

Stato in una riga: **abbiamo la ricetta e gli ingredienti, ma la cucina non è accesa.**

---

## 2. Lavoro sulle skill — FATTO ✅

### 2.1 Nuova skill `eve-agent`
Scaffolda e gestisce un agente **eve** (Vercel's filesystem-first agent framework) in
`apps/agent`, come motore dietro un'app Next. Due modalità (scaffold / capability), idempotente.

- Allineata leggendo **end-to-end tutte le ~70 pagine** di `eve.dev/docs` (7 agenti in parallelo).
- File: `SKILL.md` + 4 reference (`eve-conventions`, `eve-scaffold`, `eve-capabilities`,
  `eve-web-integration`) + `scripts/check_eve_state.py` (rileva stato e modalità).
- Correzioni chiave emerse dai doc: import map per capability (`eve/tools`, `eve/skills`,
  `eve/hooks`, …), `agent.ts` + `instructions.md`, default model `anthropic/claude-sonnet-4.6`,
  `evals/` sibling di `agent/`, `withEve` (`eve/next`) + `useEveAgent` (`eve/react`),
  durabilità/idempotenza → approval gating, security model, auth fail-closed.

### 2.2 Integrazione in `dev-flow`
`eve-agent` modellato come **componente opzionale on-demand** (decisione di scope via
`stack.agent`, scelta in analisi o aggiunta dopo) — **non** una fase della pipeline, **non**
una discipline skill. Aggiornati `SKILL.md`, `references/contracts.md` (chiave `stack.agent`),
`references/stack-monorepo.md` (terza app `apps/agent`).

### 2.3 Moduli `voice` e `realtime` in `module-add`
Promossi da stub a moduli completi con template:
- `module-realtime.md` — Vercel Functions WebSockets (`experimental_upgradeWebSocket`),
  hook `useSocket` con reconnect/backoff, guida store esterno. **Fondato su doc verbatim.**
- `module-voice.md` — voce realtime AI Gateway (token route + `useRealtime`, topologia
  eve-come-cervello STT→eve→TTS). **Lower-confidence**: API `experimental_*`, ogni
  identificatore marcato `[VERIFY]`.

### 2.4 Registry, installer, lint
`skills.json` rigenerato (**33 skill**), `install.sh`/`uninstall.sh` aggiornati, `lint_skills.py`
**pulito**. Skill reinstallate in `~/.claude/skills/`.

### 2.5 Documentazione prodotta
- `docs/loop-engineering.md` — runbook end-to-end del loop.
- `docs/example-full-walkthrough.md` — caso "Helmsman" che usa tutte le 33 skill.
- `docs/relazione-stato-progetto.md` — questo file.

### 2.6 Commit (branch `feat/eve-agent-skill`, PR #1)
```
f47ca32  docs: full walkthrough exercising all 33 skills
3450a14  feat(module-add): implement voice and realtime modules
9651dc1  feat(module-add): add planned realtime module
dc29175  feat(module-add): add planned voice module
7930a31  docs: loop-engineering runbook
e943ad3  feat(eve-agent): add eve agent-engine skill + wire into dev-flow
```

---

## 3. Decisioni infrastrutturali del loop — DECISE 🟡

| Pezzo | Scelta | Note |
|---|---|---|
| **Coda task** | **Linear** | API token `lin_api_…`, no OAuth headless |
| **Server** | **Hetzner CX23** (x86, 2 vCPU / 4 GB / 40 GB, ~7 €) | + swapfile; resize → CX33 se OOM; location EU |
| **Auth Claude** | **subscription** via `claude setup-token` → `CLAUDE_CODE_OAUTH_TOKEN` | no API key; **limiti d'uso** → runner con pacing/backoff |
| **Code host / gate** | **GitHub + Actions + branch protection** | è il "giusto/sbagliato" automatico; alt. Gitea/GitLab |
| **Architettura x86** | CX (Intel/AMD), non CAX (Arm) | evita attriti arm64 su build/Playwright |

### 3.1 Dettagli Claude Code headless (verificati, v2.1+)
- `claude -p "<prompt>"` (print mode), `--output-format json` per leggere `.result`/`.session_id`/`.total_cost_usd`.
- Permessi non interattivi senza bypass totale: `--permission-mode acceptEdits` + `--allowedTools "Bash(git *),Bash(pnpm *),Bash(gh *),Read,Edit,Write"`.
- `--max-turns N` + `timeout` shell come doppio limite.
- MCP Linear via `--mcp-config .mcp.json` + `--allowedTools "mcp__linear__*"` (token, non OAuth).
- Le skill installate in `~/.claude/skills/` **funzionano** in `-p` mode.
- Exit code ≠ 0 = fallimento → issue in Blocked.
- Nota: `--bare` richiede v2.1.175+ (sul Mac c'è 2.1.174).

---

## 4. Decisioni architetturali (i principi)

1. **Loop ≠ dev-flow.** Una skill gira *dentro* un'esecuzione di Claude; quando finisce è
   morta. Chi lancia il giro dopo (ripeti/isola/limita/ferma) **deve** stare fuori dal
   modello. Quindi il runner è codice deterministico esterno; dev-flow è il **cervello di una
   iterazione**.
2. **eve-agent = componente opzionale**, non fase, non disciplina. Si attiva via `stack.agent`.
3. **voce/realtime = moduli web; eve è il cervello, voce/WS sono I/O.** Mai due loop di
   controllo in competizione (realtime speech-to-speech vs workflow durabile eve).
4. **Le guardrail non si affidano al modello.** Il gate CI (merge), l'HITL sulle azioni
   irreversibili, il budget e il kill-switch stanno fuori dall'agente.

---

## 5. Cosa è CONFIGURATO/ATTIVO — NIENTE ❌

Nessun loop sta girando. Inventario:

| Pezzo | Stato |
|---|---|
| `docs/loop-engineering.md` (la ricetta) | ✅ committato — è **doc**, non config attiva |
| `~/loop-ops/setup-hetzner.sh` (script che *configurerebbe* il server) | ⚠️ scritto, **scratch locale, mai eseguito** (fuori da git) |
| Server Hetzner CX23 | ❌ non creato |
| Linear: coda / stati / token | ❌ non fatto |
| Token subscription Claude | ❌ non generato |
| Token Linear / GitHub | ❌ non generati |
| `/etc/loop.env` compilato + `.mcp.json` reale | ❌ solo template nello script |
| **Runner** (`runner.sh` + `loop.service`) | ❌ **non scritto** |
| **Gate CI** (GitHub Actions + branch protection) | ❌ non scritto |

---

## 6. Cosa MANCA per arrivare a un loop funzionante

### Lato utente (account/chiavi — solo tu puoi farli)
1. Creare il **CX23** su Hetzner (EU) + associare la chiave SSH (`id_ed25519`, già presente).
2. `claude setup-token` sul Mac → `CLAUDE_CODE_OAUTH_TOKEN`.
3. Token **Linear** (Settings → API) e **GitHub** (fine-grained PAT: Contents RW + PR RW).

### Lato codice (li scrivo io — sono i due pezzi mancanti)
4. **Runner** `runner.sh` + `loop.service` (con pacing/backoff sui limiti subscription, worktree per issue, kill-switch).
5. **Gate CI** `.github/workflows/ci.yml` (install + lint/typecheck/build + `eve eval --strict` + test) e indicazioni branch protection.
6. `.mcp.json` con il **pacchetto MCP Linear reale** (oggi placeholder).

### Insieme (messa in opera)
7. `scp` + esecuzione di `setup-hetzner.sh` sul server.
8. Compilare `/etc/loop.env`, copiare le skill in `~/.claude/skills/`, avviare `loop.service`.
9. **Dry-run** su una issue usa-e-getta prima di lasciarlo libero.

---

## 7. Open items / da verificare prima del go-live

- **API eve**: i nomi esatti vanno riconfermati contro `node_modules/eve/docs/` della versione
  installata (è la regola n.1 della skill). I doc letti via WebFetch sono riassunti.
- **Modulo voice**: API `experimental_*` (`experimental_useRealtime`, `getToken`) dal blog →
  verificare contro `@ai-sdk/gateway`/`@ai-sdk/react` installati. Tutti i `[VERIFY]` nel file.
- **MCP Linear**: nome pacchetto reale da inserire nel `.mcp.json`.
- **NodeSource**: confermare disponibilità canale `setup_24.x` su Ubuntu.
- **`--bare`**: richiede Claude Code ≥ 2.1.175 (Mac: 2.1.174) — aggiornare se lo si usa.

---

## 8. Dove vive tutto

- **Repo skill**: `~/my-skills` (remote `lukedj78/dev-flow`), branch `feat/eve-agent-skill`, PR #1.
- **Skill installate**: `~/.claude/skills/` (eve-agent, dev-flow, module-add, … aggiornate).
- **Scratch loop (fuori da git)**: `~/loop-ops/setup-hetzner.sh`.
- **Doc operative**: `~/my-skills/docs/{loop-engineering,example-full-walkthrough,relazione-stato-progetto}.md`.

---

## 9. Prossimo passo concordato

Scrivere **runner + gate CI** (i due pezzi mancanti lato codice) in `~/loop-ops/`, così che
appena crei il server e i token, il loop sia pronto da mettere in opera.
