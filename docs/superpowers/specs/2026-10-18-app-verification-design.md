# `app-verification` — un manuale per far girare l'app vera e provarla, scritto una volta per progetto — 2026-10-18

Nasce dalla lettura di `create-verification-skill` e `maintain-verification-skill` di **pstack** (Lauren Tan,
distribuito da Cursor in `cursor/plugins`, licenza **MIT** nel `LICENSE` di `pstack/`; letti dal sorgente il
2026-10-18, versione Cursor e versione `harness/pstack/claude-code/`, identiche salvo un rimando all'adapter).
L'utente ha chiesto di chiudere questa parte prima del punto 3 della roadmap.

## Il problema

Ogni volta che un agente deve dimostrare che una funzionalità funziona sull'app vera, riparte da zero: come si
avvia, quando è pronta, con quale utente entrare, quali dati di prova servono, dove guardare, come chiudere senza
lasciare processi accesi. Su app-security è successo due volte di fila (fit-coach, annotix). Quello che un agente
scopre non resta da nessuna parte, e il successivo lo riscopre, o peggio indovina: un controllo che «passa» su uno
stato che non era pronto, una prova presa da un endpoint di test invece che dal percorso dell'utente, un server
dell'utente spento per sbaglio.

dev-flow oggi ha i pezzi, non il manuale:
- `write-tests` scrive test Playwright e, con `references/e2e-agentic.md` (tester-army), test end-to-end agentici;
- `superpowers:verification-before-completion` chiede la prova prima di dichiarare finito, ma non dice come si
  ottiene su *questa* app;
- gli strumenti di Claude Code (browser integrato con `.claude/launch.json`, simulatore iOS, la skill `run`) sanno
  guidare un'app, ma non sanno niente del progetto.

## Cosa prendiamo da pstack, e cosa no

**Prendiamo**, riscritto con parole nostre:
- il manuale per progetto, in sei parti: avvio, *doctor*, guida, prove, pulizia, script di supporto;
- la regola della prontezza: pronta vuol dire usabile, non «il processo risponde»; da dati vuoti, migrazioni e
  seed compresi;
- il *doctor*: un solo controllo in sola lettura che dice se l'istanza merita di essere guidata, ripetuto dopo ogni
  cosa sorprendente;
- gli standard di prova: il percorso vero dell'utente, mai endpoint o setter di test; l'azione e lo stato che ne
  risulta, non solo la schermata finale; gli effetti collaterali (righe, file, messaggi); un «dry-run» si verifica
  osservando cosa salta davvero, non fidandosi del nome;
- la pulizia: si chiude solo ciò che si è avviato, mai per nome di processo; le prove sopravvivono alla pulizia;
- **«mai indebolire il percorso per farlo passare»**: se manca una precondizione, il percorso fallisce e il motivo va
  scritto;
- il manuale generato si esegue una volta da capo a fondo prima di consegnarlo; uno mai eseguito è una bozza;
- la manutenzione: una lettura del sorgente per funzionalità in parallelo, un solo passaggio dal vivo che le guida
  tutte, e tre esiti (`clean`, `changed`, `blocked`); si modifica solo il manuale, mai il codice del prodotto; un
  comportamento rotto è un problema del prodotto da riportare, non una frase da correggere.

**Non prendiamo:**
- i percorsi `.cursor/skills/` e `disable-model-invocation`: qui il manuale va in `.claude/skills/` e la skill si
  attiva anche da sola quando serve una prova;
- la feature map ricostruita indovinando da rotte e menu: **noi ce l'abbiamo già**, approvata dall'utente (§2);
- la PR della manutenzione: nei progetti dell'utente non si committa mai (regola dell'utente), quindi le correzioni
  restano nel working tree e l'utente le vede nella diff.

## Intento

Una skill `app-verification`, con due modalità:

- **create** — genera nel progetto il manuale `.claude/skills/verify-<app>/`, lo prova una volta, lo registra;
- **maintain** — lo tiene vero mentre l'app cambia.

Il manuale generato è per il prossimo agente, non per una persona: viene letto a freddo, a metà di un altro lavoro,
da qualcuno che non ha mai visto l'app.

## Obiettivi

1. Ogni progetto con qualcosa da guidare (web, Expo, eve) ha un manuale che porta un agente dall'app spenta a una
   prova salvata, e di nuovo all'app spenta, senza indovinare niente.
2. La feature map nasce dall'inventario delle schermate e dalle storie del PRD, non da una ricostruzione.
3. Il manuale è stato eseguito almeno una volta prima di essere consegnato, e la prova di quell'esecuzione esiste.
4. Gli standard di prova valgono in tutto dev-flow, anche dove il manuale non c'è ancora.
5. La manutenzione trova da sola dove il manuale non dice più il vero.

## Non obiettivi

- Sostituire i test. Il manuale serve a provare una cosa adesso; `write-tests` la rende ripetibile in CI. Un percorso
  provato a mano è un ottimo candidato per un test, e la skill lo dice.
- Un gate: non blocca fasi né deploy.
- Guidare la produzione. Il manuale avvia l'app in locale, o al massimo su una preview con dati di prova.

## Anti-obiettivi

- Un manuale con segnaposto, o con selettori d'esempio invece di quelli veri del repo.
- Un agente che pilota il server di sviluppo già aperto dall'utente, o lo spegne.
- Una prova che passa perché il percorso è stato semplificato.
- Credenziali in chat o nel manuale: stanno nel seed o in `.env.test`, come già vuole la regola sui test.

## Il design

### 1. Il manuale generato: `.claude/skills/verify-<app>/`

```
.claude/skills/verify-<app>/
├── SKILL.md            # frontmatter name + description, poi le sei sezioni
├── features/
│   ├── README.md       # precondizioni di base, convenzioni di guida, regole di prova, indice
│   └── <US-N>-<slug>.md   # una funzionalità per storia del PRD
└── scripts/            # solo se servono: eseguibili, e invocati per nome nel SKILL.md
```

Le sei sezioni di `SKILL.md`, ognuna riempita con quello che c'è davvero nel repo:

| Sezione | Cosa contiene |
|---|---|
| **Launch** | il comando, la porta, le variabili, come si capisce che è pronta (usabile); da dati vuoti, con migrazioni e seed; un nome nella configurazione `.claude/launch.json`, così gli strumenti di anteprima di Claude Code usano lo stesso avvio |
| **Doctor** | un controllo in sola lettura: processo nostro, build giusta, porta nostra, sessione valida |
| **Drive** | la ricetta per lo stack (§3) con i selettori veri: ruoli ARIA e nomi accessibili, attributi `data-`, rotte |
| **Evidence** | cosa salvare e dove (`.verification/evidence/<data>/`, git-ignorata), e gli standard di prova |
| **Cleanup** | chiudere ciò che il run ha avviato (PID e porte annotati all'avvio), mai per nome; le prove restano |
| **Isolation** | se due istanze possono convivere (porta, cartella dati); se no, il manuale lo dice e rifiuta di guidare un'istanza che non ha avviato |

### 2. La feature map, dall'inventario

Un file per ogni storia `US-N` del PRD. Per ogni file:

- **Sub-features**: gli stati delle schermate della storia, presi dalla colonna `States` dell'inventario
  (`L` loading, `E` empty, `Er` error, `S` success), più i rami della storia (crea, annulla, modifica…);
- **Come ci arriva l'utente**: le schermate dell'inventario mappate alla storia, con la rotta e il ruolo;
- **Guidarla con `<harness>`**: precondizioni, poi coppie azione-utente → comando esatto → risultato osservabile;
- **Trappole**: quello che fa perdere o invalida un run.

Le storie vengono da `.workflow/PRD.md`, le schermate da `docs/wireframes/screen-inventory.md`. Un progetto senza
inventario (precedente alla regola dei wireframe, o con `wireframes.skipped`) ricostruisce le funzionalità da rotte
e menu, come pstack, e lo dichiara nell'indice.

La parte meccanica (lo scheletro di ogni file con storia, schermate, rotte, ruoli e stati) la scrive uno script; la
parte che richiede di leggere il codice (selettori, comandi, risultati attesi) la scrive l'agente.

### 3. Le ricette per stack

| Stack | Guida | Prove |
|---|---|---|
| web (Next.js) | il browser integrato di Claude Code (anteprima da `.claude/launch.json`), oppure Playwright se il progetto lo ha già | albero di accessibilità, screenshot, risposta di rete, riga nel database |
| Expo / RN | il simulatore iOS di Claude Code; Maestro se il progetto lo ha già | screenshot, albero della UI, log |
| eve agent | `eve dev` e una chiamata al canale (HTTP, o il canale che l'agente espone) | risposta, trace, effetti dei tool |
| monorepo | un manuale per app (`verify-web`, `verify-mobile`, `verify-agent`) | come sopra |

Un harness già presente nel repo viene prima di una ricetta generica.

### 4. La skill: `app-verification`

**create**
1. Legge il repo, non l'utente: superficie, avvio, come guidarla, cosa si può osservare, isolamento. Chiede solo
   quello che non può vedere.
2. Se l'app non si avvia così com'è, lo dice con precisione prima di generare: un manuale scritto su una base rotta
   insegna passi sbagliati.
3. `scripts/verify_map.py scaffold <root>` scrive lo scheletro della feature map dall'inventario e dal PRD.
4. L'agente riempie le sei sezioni e le prime 3–5 funzionalità.
5. **Prova**: avvio, doctor, una funzionalità guidata da capo a fondo, prove salvate, pulizia; poi controlla che le
   prove ci siano ancora. Corregge e ripete, pulendo dopo ogni tentativo fallito.
6. `scripts/verify_map.py check <root>` controlla la struttura:
   - frontmatter presente;
   - le sei sezioni presenti;
   - nessun segnaposto `<…>` rimasto;
   - ogni storia del PRD ha un file;
   - ogni script in `scripts/` è eseguibile e nominato nel `SKILL.md`;
   - la cartella delle prove è nominata e ignorata da git.
7. Registra `meta.json#verification` e una voce nella history.

**maintain**
1. Igiene dell'indice: file mancanti, in più, doppi.
2. Lettura del sorgente, una per funzionalità, in parallelo e in sola lettura: come funziona oggi, dove il manuale
   non dice più il vero (con citazioni), una ricetta dal vivo.
3. Un solo passaggio dal vivo, che guida ogni funzionalità almeno una volta, con tre invarianti: doctor prima di
   guidare e dopo ogni cosa sorprendente; prove salvate che sopravvivono a ogni pulizia; niente di avviato che
   sopravvive al proprio uso.
4. Smistamento: descrizione sbagliata → si corregge il manuale; comportamento che funziona ma il manuale non sa
   guidare → si corregge il manuale; comportamento rotto → **problema del prodotto**, riportato all'utente, mai
   nascosto nel manuale.
5. Esito: `clean`, `changed` (correzioni lasciate nel working tree, mai committate), o `blocked` con il motivo.

### 5. Lo stato: `meta.json#verification`

```json
"verification": {
  "skill": ".claude/skills/verify-web",
  "features": 7,
  "source": "wireframes | routes",
  "proven_at": "<ISO-8601 UTC>", "proven_feature": "US-2",
  "evidence": ".verification/evidence/2026-10-18T10-00Z/",
  "maintained_at": "<ISO-8601 UTC>" | null, "maintain_outcome": "clean | changed | blocked" | null
}
```

In un monorepo, `skill` diventa una lista, una voce per app. Mai `phase`, sempre una voce nella history.

### 6. Dove entra nel flusso

- **dev-flow**:
  - propone **create** alla prima `page_generated` (web), alla prima schermata (Expo) o al primo tool (eve), cioè
    quando c'è qualcosa da guidare;
  - propone **maintain** a `feature_complete`, prima dei gate, e nel ciclo dopo `deployed` dopo modifiche rilevanti;
  - `show_state.py` dice se il manuale manca o se è più vecchio dell'ultima modifica rilevante.
- **`dev-flow/references/policies.md`**: un paragrafo con gli standard di prova, validi anche senza il manuale.
- **`spec-review`**: quando dice «non provato», rimanda al manuale.
- **`write-tests`**: un percorso provato a mano, con la sua ricetta, è il punto di partenza per un test Playwright o
  e2e; la skill lo propone.
- **`wireframe-canvas`**: un rimando: l'inventario alimenta anche la feature map.
- **`dev-flow/references/resources.md`**: una riga per pstack, con la licenza e quello che abbiamo preso.

### 7. Le superfici, riconosciute e non presunte (decisione dell'utente, 2026-10-18)

Nessun elenco fisso: la skill guarda il progetto e crea **un manuale per ogni superficie** che trova. Il
riconoscimento sta in **un modulo solo**, `dev-flow/scripts/surfaces.py`, copiato nelle skill che lo usano come
già `meta_io.py` (il lint tiene identiche le copie), perché oggi la stessa domanda — che pezzi ha questo progetto —
ha tre risposte diverse (`app-security`, `show_state`, e questa skill), e una ha già avuto un bug (Expo configurato da
`app.config.ts`).

| Tipo | Come si riconosce | Manuale |
|---|---|---|
| `web` | `next` nelle dipendenze, con `app/` o `src/app/` | `verify-web` (in un monorepo `verify-<app>`) |
| `mobile` | Expo: `expo` senza `next`, `app.json` con `expo`, `app.config.*` | `verify-mobile` |
| `agent` | eve: `agent/agent.ts`, `apps/agent`, o `stack.agent = "eve"` con la cartella | `verify-agent` |
| `api` | un servizio HTTP senza UI: le voci di `stack.monorepo.services` | `verify-<nome>` |
| `cli` | un pacchetto con `bin` in `package.json` | `verify-<nome>` |
| `other` | un'app in `apps/*` o `packages/*` con uno script `dev` o `start` che non rientra nei tipi sopra | `verify-<nome>`, con la ricetta segnata da completare |

Ogni superficie ha `kind`, `name`, `path` e `mounted_in`: un agente servito dall'app web (`withEve()` in
`next.config.*`, come in Archi Studio sotto `/eve/v1/*`) ha `mounted_in: "web"`, e il suo manuale non inventa un
avvio proprio ma rimanda a quello del web. I pacchetti senza niente da avviare (tipi, config condivisa, UI
condivisa) non sono superfici.

Usano il modulo: `verify_map.py` (`scaffold` e `check` su tutte le superfici, `--app` solo per forzarne una),
`show_state.py` (la nota per superficie: quale manuale manca) e `app-security` (che sostituisce il suo
riconoscimento di Next, Expo e delle radici del monorepo).

La prova vera si fa su due progetti: fit-coach (una superficie, `web`, mappa dalle rotte) e Archi Studio (due
superfici, `web` e `agent` montato nel web, mappa dall'inventario dei wireframe).

## Test

- **`verify_map.py`**, con fixture in cartelle temporanee:
  - `scaffold` scrive un file per storia, con le schermate e gli stati giusti presi dall'inventario;
  - `scaffold` senza inventario ripiega sulle rotte e lo dichiara;
  - `check` fallisce su ciascuno di questi casi, uno alla volta:
    - un segnaposto rimasto;
    - una sezione mancante;
    - una storia senza file;
    - uno script non eseguibile, o non nominato;
    - la cartella delle prove non ignorata;
  - `check` passa su un manuale completo.
- **`show_state.py`**: la nota per un manuale mancante o vecchio.
- **Una prova vera**, su un progetto scelto dall'utente: create completo, comprese la prova dal vivo e la pulizia.
  I file restano nel working tree del progetto, non committati.
- Il lint, i bundle, tutte le suite.

## Lasciato a chi costruisce

- Il formato esatto delle note per PID e porte avviati, e come il cleanup le legge.
- Quante funzionalità riempire nel primo create oltre la prima provata (pstack dice 3–5).
- Le parole esatte delle ricette per stack.

## Scelte mie, da controllare

- **Una skill sola con due modalità**, invece delle due skill di pstack: è il modello di `linear-scrum`
  (Setup, Sync).
- **La feature map per storia del PRD**, non per schermata: una funzionalità vista dall'utente attraversa più
  schermate, e le storie sono l'unità che il PRD, i task e Linear condividono già.
- **Il manuale in `.claude/skills/`** del progetto, così Claude Code lo trova da solo, e l'avvio in
  `.claude/launch.json`, così gli strumenti di anteprima e il manuale usano lo stesso comando.
- **Le prove in `.verification/evidence/`**, ignorata da git: restano sulla macchina, non nel repo.
- **Nessun commit nei progetti**: create e maintain lasciano i file nel working tree.
- **Nessun gate**.
