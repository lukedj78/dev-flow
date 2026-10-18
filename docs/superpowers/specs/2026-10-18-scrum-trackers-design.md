# Scrum su Linear, Jira o GitHub, e il triage dei bug — 2026-10-18

Sesto punto della roadmap (`2026-10-17-founder-intelligence-design.md:450-461`, in sintesi):

> 6. **Triage dei bug e più sistemi di task management** (S + L): etichette di gravità e un percorso leggero per una
> singola funzione; e la skill di project management (oggi `linear-scrum`) supporta **Linear, Jira e GitHub** (Issues
> e Projects), con lo stesso metodo scrum e lo stesso contratto, invece di tre skill separate. **Il servizio si
> sceglie in fase di progettazione** (una domanda in `prd-from-idea`, registrata in `meta.json`). La skill cambia nome.
> Da decidere: il nome della skill e del campo, come si migra un progetto già in Linear, e la policy di dev-flow.

L'utente ha chiesto di saltare le domande (2026-10-18): le scelte qui sono **mie**, salvo quelle citate sopra, che
sono sue.

## Il problema

- La policy dice «ogni progetto in Linear», ma i progetti reali non lo sono: bidflow usa GitHub Issues
  (memoria del progetto: «Tracker: GitHub Issues, not Linear»), hostitaly Linear. Un cliente con Jira oggi non ha
  strada.
- GitHub esiste già, ma **fuori dal metodo**: `project-infra-setup/scripts/make_issues.py` crea le issue con una
  mappa titolo→numero in `.workflow/github-issues.json`, non registrata nel contratto; gli sprint sono milestone
  descritte in prosa (`provisioning.md`). Due implementazioni dello stesso metodo, con mappe diverse (`task_key` per
  Linear, titolo per GitHub).
- Jira non c'è.
- **I bug non hanno una strada.** Nessuna gravità, nessun tipo `bug`; ogni cosa passa da PRD → `tasks.md` →
  tracker, che per un bug in produzione è la strada sbagliata.

## Fatti verificati (2026-10-18)

- **`linear-scrum`**: tutto l'I/O con Linear è prosa eseguita dall'agente via MCP; gli script sono neutrali
  (`task_key.py`) o quasi (`meta_linear.py`: solo il nome del blocco `linear` e i campi del team). Il metodo
  (Fibonacci dall'hint `Estimated:`, sprint fino a `velocity_target`, etichette scoperte e non assunte, modi
  Setup/Adopt/Sync, `issue_map` per l'idempotenza, il tracker fonte di verità dopo il Setup) è già indipendente
  dal servizio.
- **Linear MCP**: i cicli non si creano via MCP (verifica live della skill, 2026-08-27; nessuna novità nel
  changelog fino al 2026-10-08). Stima via `save_issue` se il team ha una scala attiva.
- **Jira — Atlassian Rovo MCP** (`mcp.atlassian.com`, pagina «supported tools», 2026): `createJiraIssue`,
  `editJiraIssue`, `transitionJiraIssue` (anche verso uno sprint o il backlog), `addOrEditJiraIssueComment`,
  `searchJiraIssuesUsingJql`, `listJiraProjects`, `listJiraBoards`, `listJiraBoardSprints`, **`manageJiraSprint`**
  (crea, popola, avvia, chiude: dal 2026-08-29). Le story point via `editJiraIssue` **non sono dimostrate** (segnalazioni
  di campi personalizzati non scrivibili); la REST le scrive con `PUT /rest/agile/1.0/issue/{key}/estimation?boardId=`,
  che funziona anche se il campo non è sulla schermata. `acli` non gestisce sprint né campi personalizzati: non serve.
  Residenza dati UE sui piani Standard, Premium, Enterprise.
- **GitHub**: `gh` 2.102.0. Issue, label, milestone; **Projects v2**: `gh project item-edit` imposta numero (stima),
  selezione singola (stato) e iterazione (sprint), ma `gh project field-create` **non** crea un campo iterazione —
  serve `gh api graphql` con `createProjectV2Field(dataType: ITERATION, iterationConfiguration: …)`, e
  `updateProjectV2Field` **sostituisce** tutta la configurazione (le iterazioni esistenti vanno ripassate con il loro
  id). Scope del token: `project`. github.com conserva i dati negli USA; la residenza UE è solo GitHub Enterprise
  Cloud con data residency (`*.ghe.com`).
- **Dove `linear-scrum` è citata**: dev-flow (routing in `show_state.py`, SKILL, `policies.md`,
  `merge-conflicts.md`, `eu-data-sovereignty.md`), `prd-to-tasks`, `prd-from-idea/references/scope-check.md`,
  `wireframe-canvas` (commenti con le PNG), `spec-review`, `project-infra-setup`, `compliance-audit`, il contratto
  (44 copie), `README`, `install.sh`, i registri generati, `test_meta_io.py`, `contract-package`.

## Cosa costruiamo

### 1. Una skill, `scrum`

`linear-scrum` diventa **`scrum`**: stesso metodo, stessi modi (Setup, Adopt, Sync), un adattatore per servizio in
`references/`:

| | Linear | Jira | GitHub |
|---|---|---|---|
| Come | Linear MCP | Atlassian Rovo MCP; story point via REST (`jira_estimate.py`) | `gh` |
| Progetto | Project nel team | progetto Jira + board scrum | il repository |
| Sprint | cicli, **creati dall'utente** nell'app (MCP non può) | sprint con `manageJiraSprint` | **una milestone per sprint, col nome del suo obiettivo** (regola dell'utente, 2026-10-14) |
| Stima | `estimate` | story point della board (REST `estimation`) | etichetta `estimate: N` (Fibonacci) |
| Stato | stati del workflow | transizioni (`listJiraIssueTransitions`) | aperta / chiusa, più le etichette `status: in progress`, `status: in review`, `blocked` |
| Priorità | priorità nativa | priorità nativa | etichetta `priority: Pn` su ogni issue (regola dell'utente) |
| Chiave | `LUC-123` | `ABC-123` | `#123` |

Nome: `scrum` (corto, è il metodo, non il fornitore; `sprint-board` dice meno). La descrizione conserva le parole
«Linear», «Jira», «GitHub Issues» perché le richieste dell'utente continuino a trovarla.

**Script neutrali** (stdlib), in `scrum/scripts/`:

- `task_key.py` — invariato.
- `meta_tracker.py <meta.json> choose | upsert | record-issues | ensure-scrum | migrate` — scrive `meta.json#tracker`
  e `#scrum` sotto il lock di `meta_io` (copia vendorizzata, come oggi):
  - `choose --provider linear|jira|github` — la scelta fatta in progettazione;
  - `upsert --provider … --project-id … --url … [--extra JSON]` — gli id del servizio;
  - `record-issues --mapping JSON` — `task_key → chiave`;
  - `ensure-scrum` — i default, più le **etichette di gravità** (§3);
  - `migrate` — porta un blocco `linear` legacy in `tracker` e, se esiste, `.workflow/github-issues.json` in
    `tracker.issue_map` (titolo → `task_key`), senza perdere nulla.
- `github_sync.py <root> --repo O/N` — GitHub lo fa uno script, perché `gh` è una CLI: crea le etichette mancanti
  (riusando quelle che il repository ha già), le issue nuove (solo i `task_key` assenti dalla mappa), con stima,
  priorità e milestone dello sprint; `--dry-run`; idempotente; registra la mappa con `meta_tracker.py
  record-issues`. Prende il posto di `project-infra-setup/scripts/make_issues.py` (con i suoi test), che resta come
  rimando di una riga. GitHub Projects v2 **non** serve: la regola dell'utente usa le milestone, e i progetti esistenti
  le usano già.
- `jira_estimate.py <root> --key ABC-1 --points 3` — le story point via REST (`PUT /rest/agile/1.0/issue/{key}/
  estimation?boardId=`), con `JIRA_EMAIL` e `JIRA_API_TOKEN` dall'ambiente e sito e board da `tracker.project`;
  mai un token in chat.
- Linear e il resto di Jira restano **prosa eseguita via MCP**, come oggi Linear: i riferimenti dicono quali
  strumenti, in che ordine e cosa registrare.
- **Lo standard del corpo delle issue** (decisioni con i link alle fonti, criteri di accettazione, dipendenze,
  schermate, checklist di verifica, un esempio approvato prima degli altri: regola dell'utente, 2026-10-14) passa da
  `project-infra-setup/references/provisioning.md` a `scrum/references/issue-standard.md` e vale per tutti e tre i
  servizi; `project-infra-setup` crea il repository e rimanda lì.

### 2. Contratto

```json
"tracker": {
  "provider": "linear | jira | github",
  "project": { "…": "id del servizio: team_id/project_id (Linear), site/project_key/board_id (Jira), repo/project_number (GitHub)" },
  "url": "…",
  "issue_map": { "<task_key>": "LUC-123 | ABC-123 | #123" },
  "last_synced_at": "<ISO-8601 UTC>"
},
"scrum": { "…invariato…", "severity_labels": { "S1": "severity: S1", "S2": "…", "S3": "…", "S4": "…" }, "bug_label": "bug" }
```

- `tracker` sostituisce `linear`. Un `meta.json` con il vecchio blocco resta valido: la skill lo legge e lo migra
  al primo Adopt o Sync (`migrate`), e `show_state.py` lo segnala finché c'è.
- **Esistono già blocchi `tracker` scritti a mano** (archistudio: `{kind: "github", repo, map, bodies, scrum{sprint_weeks,
  capacity_hours, milestones, plan, first_sprint_start}}`; fit-room: `{kind: "github-issues", repo, issue_map{titolo:
  numero}}`). `migrate` li normalizza senza perdere niente: `kind` → `provider` (`github-issues` → `github`), `repo`
  → `project.repo`, la mappa per titolo (inline o nel file `map`) → `issue_map` per `task_key` ricalcolato dai titoli
  di `tasks.md` (i titoli che non trova restano in `tracker.unmatched`, mai buttati), il `scrum` annidato si fonde nel
  `scrum` di primo livello (`sprint_weeks` → `cadence_weeks`, il resto tale e quale) e ogni altra chiave resta dov'è.
  Sui progetti reali le chiavi coincidono con i titoli di `tasks.md` (171/171, 116/117, 80/80, 140/140).
  `show_state.py` segnala ogni forma vecchia (blocco `linear`, `kind`, mappa per titolo).
- `tracker.provider` può esistere da solo, senza `project`: è la scelta fatta in progettazione, prima del Setup.
- **Non** è un sub-processor del prodotto: il registro (`docs/compliance/subprocessors.md`) elenca chi riceve dati
  personali per conto del prodotto, e un tracker del team non ne riceve — purché il triage non ci copi dati degli
  utenti (la regola del §3). `eu-data-sovereignty.md` aggiunge le righe di Jira (UE da Standard) e GitHub (UE solo con
  GHE.com data residency) per la scelta del team.

### 3. Il triage dei bug

**Gravità**, quattro livelli, etichette create dal Setup su ogni servizio (riusando quelle già presenti). La gravità
è dei bug; la priorità (`priority: Pn` su GitHub, nativa su Linear e Jira) resta l'ordine del lavoro pianificato, e
un bug le ha entrambe (S1/S2 → la priorità più alta):

| | Quando | Cosa succede |
|---|---|---|
| **S1** | rotto per tutti, dati persi o esposti, sicurezza | si lavora subito: entra nello sprint corrente, fuori dalla velocità; fix, verifica, rilascio |
| **S2** | una funzione importante non va e non c'è un modo per aggirarlo | entra nello sprint corrente |
| **S3** | c'è un modo per aggirarlo | al prossimo planning |
| **S4** | estetica, testo | backlog |

**Il percorso leggero per un bug** (modo **Triage** della skill), senza passare dal PRD né da `tasks.md`, perché un
bug ripara quello che era già promesso:

1. **riprodurre** sull'app vera con il manuale di `app-verification` (`verify-<app>`), o dire che non si riproduce;
2. **dare la gravità** con la tabella sopra, dicendo all'utente il perché in una riga;
3. **creare l'issue** sul servizio scelto, tipo/etichetta `bug` + gravità, con passi, atteso, osservato, evidenza;
4. **mettere** S1/S2 nello sprint corrente, S3/S4 nel backlog; una voce di history.

**Il Triage si ferma lì**: `scrum` non tocca il codice (come oggi `linear-scrum`). Il fix segue la strada normale —
un test che riproduce il bug (rosso → verde, `write-tests`), la skill che possiede il codice, PR che cita l'issue,
verifica sull'app, chiusura col riferimento al commit — e dev-flow lo propone. **Mai dati personali degli utenti
nell'issue**: l'evidenza si redige (id, non email; niente screenshot con dati veri).

**Il percorso leggero per una singola funzione** esiste già e va solo nominato: `scope-check` (quattro domande) →
`scope.py record` → una task in `tasks.md` (`prd-to-tasks` revisione) → Sync. Niente PRD riscritto.

### 4. dev-flow e le altre skill

- **Policy**: «ogni progetto è gestito con scrum sul tracker scelto in progettazione (Linear se l'utente non dice
  altro)». La domanda la fa `prd-from-idea` (una domanda, una riga in `meta.json` via `meta_tracker.py choose`),
  e i default sono: il tracker già usato dal progetto o dal cliente; altrimenti Linear.
- Routing: `tasks_split → scrum (Setup)` in tutte le topologie.
- `prd-to-tasks`, `scope-check.md`, `spec-review`, `merge-conflicts.md`, `wireframe-canvas` (i commenti con le PNG
  usano `tracker.issue_map` e, su GitHub, l'URL raw; su Linear e Jira l'agente allega le immagini),
  `project-infra-setup` (crea il repo; le issue sono di `scrum`), `compliance-audit` (sub-processor),
  `README`, registri: nome e testo neutrali.
- `install.sh` **rimuove** la copia installata di `linear-scrum` (dopo il backup che fa già), così l'agente non
  carica due skill per la stessa cosa; `uninstall.sh` conosce entrambi i nomi.

## Obiettivi, non obiettivi, anti-obiettivi

- **Obiettivo**: lo stesso metodo scrum su Linear, Jira o GitHub, scelto in progettazione; i progetti già in Linear o
  su GitHub continuano senza rifare niente; un bug ha una strada corta con una gravità.
- **Non obiettivi**: altri tracker (Asana, ClickUp, …); sincronizzazione bidirezionale dei campi oltre quella di
  oggi (stato e velocità tirati dal tracker, task nuove spinte); migrare un progetto da un tracker a un altro.
- **Anti-obiettivi**: tre skill che divergono; un metodo che cambia secondo il servizio; un bug S1 messo in coda al
  backlog perché la procedura voleva un PRD.

## Vincoli

- Stdlib, Python 3.9+; nessun token in chat: Jira REST con `JIRA_EMAIL` + `JIRA_API_TOKEN` nell'ambiente, GitHub con
  `gh auth` (scope `project`), Linear e Jira MCP con OAuth dell'utente.
- Niente account creati dalla skill; niente scrittura senza un sì dell'utente sul primo Setup (crea progetti e issue
  su un servizio esterno).
- Codice e testi delle skill in inglese.

## Lasciato a chi costruisce

- La forma interna di `github_sync.py` / `github_board.py`, purché testabili con un `gh` finto nel `PATH`.
- Come presentare la tabella di triage all'utente.

## Prova

- GitHub: su un repository di prova dell'utente, **solo con il suo sì** (crea issue e un Project), oppure con
  `--dry-run` e un `gh` finto se il sì non arriva. Scelta mia: i test automatici usano sempre il `gh` finto.
- Linear e Jira: i connettori non sono autorizzati in questa sessione; i riferimenti dicono cosa verificare al primo
  uso reale, come fa oggi `linear-mcp.md`.

## Decisioni prese dopo il builder check (mie)

1. GitHub: sprint = milestone, priorità = etichetta `priority: Pn` (regola dell'utente del 2026-10-14); niente Projects v2.
2. `migrate` normalizza anche i blocchi `tracker` scritti a mano (archistudio, fit-room) senza perdere chiavi; i titoli
   non ritrovati restano in `tracker.unmatched`.
3. Lo standard del corpo delle issue passa a `scrum` e vale per tutti i servizi.
4. Su un repository adottato le etichette esistenti si riusano; si crea solo ciò che manca.
5. Le story point di Jira le scrive `jira_estimate.py` (REST, token dall'ambiente).
6. Il Triage si ferma all'issue nello sprint giusto; il fix è la strada normale.
7. Il tracker non va nel registro dei sub-processor; il triage non copia dati personali nelle issue.
