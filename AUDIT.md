# DevFlow — Audit tecnico, revisione architetturale e roadmap

> Data: 2026-10-17 · Commit analizzato: `1888df1` (main) · Passaggio 1 (audit, nessuna modifica al repository).
> Metodo: lettura del codice, esecuzione locale di tutte le suite di test, esperimenti riproducibili
> in directory temporanee fuori dal repo. Ogni affermazione porta un riferimento `file:riga` o il
> comando eseguito. Le etichette usate sono quattro:
> **[DIMOSTRATO]** (eseguito e rotto, o file che contraddice il documento) · **[RISCHIO]** (meccanismo
> che può rompersi, senza dimostrazione) · **[FACOLTATIVO]** · **[PREFERENZA]**.

---

## Stato al 2026-10-17 — implementazione

Il Passaggio 2 è stato eseguito: un punto alla volta, con test scritti prima (rossi sul codice di
partenza), regressione su Python 3.14 e 3.9, una voce nel CHANGELOG e un commit per punto. Tutto è nel
ramo `audit/p0-fixes`, PR [lukedj78/dev-flow#17](https://github.com/lukedj78/dev-flow/pull/17), con i 12
controlli della CI verdi. I numeri tra parentesi sono quelli della roadmap discussa in sessione.

| Punto | ID | Esito | Commit |
|---|---|---|---|
| (1) Scrittura atomica e lock di `meta.json`, in tutti i 12 scrittori | P0-1 | ✅ 20/20 scritture concorrenti conservate (11–15 prima) | `fb05ab6` |
| (2) Una tabella di fasi e alias | P0-3 | ✅ | `488bec1` |
| (3) Gate uguali su `set-phase` e `append-history` | P0-2 | ✅ | `c5cb31c` |
| (4) La history registra ogni cambio di fase | P1-10 | ✅ | `23d6eb3` |
| (5) Test diretti di `update_meta` / `show_state` | P1-3 | ✅ copertura 100% / 86%; 2 bug trovati | `e4641bc` |
| (6) Tutti i test in CI | P1-1 | ✅ da 4 file su 17 a 27 suite | `c031436` |
| (7) Identità delle copie vendorizzate | P1-4 | ✅ | `42c309b` |
| (8) Bundle verificati in CI | P1-5 | ✅ | `84fa8b7` |
| (9) Python 3.9 dichiarato e verificato | P1-6 | ✅ | `c3847b2` |
| (10) Lettura validante di `meta.json` | P1-2 | ✅ | `c995f8a` |
| (11) Backup `meta.json.bak` | P1-8 | ⏭ superato da P0-1, non implementato per scelta | — |
| (12) Disinstallazione non distruttiva | P0-4 | ✅ | `accd3b7` |
| (13) Test d'installazione sui 6 runtime | P1-7 | ✅ Linux e macOS | `6082dad` |
| (14) `contract-package` e template di bootstrap | P1-9 | ✅ | `d26acb9` |
| (15) Contraddizioni dell'orchestratore | P2-1 | ✅ | `5444fa7` |
| (16) Conteggi stantii | P2-6 | ✅ | `8b9492e` |
| (17) Un proprietario per Vercel | P2-5 | ✅ | `00d7e93` |
| (18) Conferme sui comandi verso l'esterno | P2-11 | ✅ | `6d5b897` |
| (19) Dieta del contesto di dev-flow | P2-3 | ✅ ~33k → ~9k token stimati per turno | `1c555fb` |
| (20) Una sola tabella di routing | P2-2 | ✅ | `6bbd2cb` |
| (21) Trigger reciproci, controllo 20 | P2-4 | ✅ | `ce1fec0` |
| (22) "Enforced" solo dove lo è | P2-7 | ✅ | `22b73a1` |
| (23) Segnale di freschezza, controllo 21 + job mensile | P2-8 | ✅ | `4990adf` |
| (24) Hook di registry-intake: più forme coperte, limiti dichiarati | P2-9 | ✅ più tre correzioni da revisioni di sicurezza | `75bfe8e`, `205acba`, `40e8c40` |
| (25) Hook solo in Claude Code: avviso | P2-10 | ✅ | `c965303` |
| (26) `contract_version` | P2-12 | ✅ | `efd6c3d` |
| (27) Meno rumore: `skills.json`, backup | P2-13 | ✅ | `ef5c30b` |
| (28) Eval di routing | P3-1 | ⏸ decisione aperta (costo stimato 15–50 USD equivalenti, in quota) | — |
| (29) Eval di compliance su altri gate | P3-2 | ⏸ decisione aperta (5–6 USD equivalenti) | — |
| (30) Dividere `design-md-to-app` | P3-3 | ⏸ condizionato a P3-1 | — |
| (31) Testo dal web come dato, `node_modules` ignorato | P3-4, P3-5 | ✅ | `a07833c` |
| (32) Guard dei primitivi sulle scritture via Bash | P1-32 | ✅ | `ba022bb` |
| (33) Modifiche a mano di `meta.json` riconosciute | P1-33 | ✅ | `ff2d57a` |
| (34) registry-intake controlla l'effetto dei comandi | P1-34 | ✅ | `922b47c`, `ca75f75` |
| Valutatore delle eval cieco alle scritture via Bash | — | ✅ emerso dalla prova a 5 sessioni | `4d5aa8e` |

### Correzioni a questo audit

Affermazioni del report qui sotto che il lavoro ha smentito o precisato:

- **§6.2, la back door di `append-history` era "latente".** Era attiva: i template di bootstrap per Codex,
  Gemini e i runtime generici cambiano fase proprio con `append-history --phase-after`, quindi su quei
  runtime quattro gate su sei non giravano mai.
- **§6.6, la regola d'oro 3 "ripetuta due volte" in `dev-flow/SKILL.md`.** La seconda copia è il testo che
  la policy sulle build parallele dice di incollare alla lettera nelle istruzioni dei sub-agenti:
  intenzionale, non un doppione.
- **§6.8, l'hook di registry-intake.** Le forme aggirabili erano più di quelle elencate: quattro giri di
  revisione automatica ne hanno trovata una nuova ogni volta. Riprodurre le regole della shell con
  un'espressione regolare è una corsa persa, quindi il parser ora analizza tutti gli argomenti di una
  shell `-c`. La difesa sull'effetto dei comandi (P1-34) rileva registry aggiunti e snapshot modificati,
  ma **non un'installazione da URL**, che lascia tracce identiche ai componenti ufficiali di shadcn.
  Contro quella serve una barriera di rete.
- **§6.10, i backup dell'installer.** Erano più di duecento; la conservazione dei 3 più recenti ne ha rimossi
  200 al primo `install.sh`.

### Problemi emersi durante l'implementazione, non visti dall'audit

- `check_drift` andava in crash su due progetti reali (`idea-validator`, `predictionleagues`): voci senza
  `sha256` e `derived_from` come semplici percorsi.
- `show_state` chiamava "sconosciuta" una fase valida che uno stack non attraversa, e proponeva di
  ripartire dal PRD.
- `record-artifact` rifiutava un percorso esterno con un traceback grezzo.
- `uninstall.sh --restore` avrebbe ripristinato una cartella dell'utente (`skills-backup-manual`) come se
  fosse un backup dell'installer.
- `contract-package` cancellava i campi che non modellava, e i template di bootstrap lo dichiaravano
  equivalente agli script, gate compresi.
- Il valutatore delle eval di compliance segnava come non conformi sessioni che avevano scritto i file
  via Bash.
- `fit-coach`: lo snapshot `vendor/registry/gauge-ui/gauge.json` è stato modificato un giorno dopo
  l'approvazione (commit `3dc99f9`), e lo ha mostrato solo il check, un mese dopo.
- La tabella delle versioni mobile è indietro di un'intera SDK (Expo 58, React Native 0.88).

### Metriche, misurate

| | Prima | Dopo |
|---|---|---|
| Suite di test eseguite in CI | 4 file su 17 | 27 suite, 3 job (Linux 3.12, Linux 3.9, macOS) |
| Scritture concorrenti su `meta.json` conservate | 11–15 su 20 | 20 su 20 |
| Gate scavalcabili | 4 su 6 via `append-history`, tutti con una modifica a mano | 0 |
| Copertura di `update_meta.py` | non testato | 100% righe e rami |
| `dev-flow/SKILL.md` | 496 righe, 62 KB | 292 righe, 32 KB (tabella di routing generata compresa) |
| Controlli del lint | 19 | 21 |
| Prova di compliance, 5 sessioni | — | 1,42 USD equivalenti in quota, 8 minuti |

Il voto "Affidabilità dimostrata" della §13 resta una stima: i numeri qui sopra sono le misure da cui
partire per rivederlo.

### Decisioni aperte

1. Merge della PR #17.
2. `fit-coach`: rivedere e riapprovare lo snapshot di `gauge-ui`, o ripristinare quello approvato.
3. P3-1, P3-2, P3-3.
4. Aggiornamento a Expo SDK 58.
5. Una barriera di rete per registry-intake, l'unica che ferma le installazioni da URL.

---

## 1. Executive summary

DevFlow è **architetturalmente sano e operativamente più fragile di quanto la documentazione lasci
intendere**. Il principio "il contratto è il nucleo, le skill sono consumatori" regge: lo dimostrano
un contratto su filesystem che preserva i campi sconosciuti, un gate di fase centralizzato in
`update_meta.py` con opt-out motivati, generatori deterministici con `--check` in CI, e un lint
ampio. Non serve né un database né un orchestratore più sofisticato.

I difetti reali sono concentrati in **un unico punto, lo strato di scrittura dello stato**, e in
**ciò che la CI non esegue**:

1. `meta.json` viene scritto senza atomicità e senza lock. Con 20 aggiornamenti concorrenti
   sopravvivono 11–15 voci (misurato), con exit code 0 per tutti i processi.
2. `append-history --phase-after` scavalca quattro dei sei gate che `set-phase` applica
   (riprodotto: un progetto vuoto arriva a `deployed` senza decisione sulla data residency).
3. Le tabelle di alias delle fasi divergono tra `show_state.py` e `update_meta.py`, e ciò permette
   una regressione di fase silenziosa (riprodotto: `page-generated → idea_captured`, exit 0).
4. `uninstall.sh` cancella una cartella `bootstrap/` dell'utente, e il README promette un ripristino
   dei backup che non avviene più.
5. **13 file di test su 17 esistono, passano, e la CI non li esegue**, tra cui quelli dei gate che
   proteggono `set-phase`. `update_meta.py` e `show_state.py`, i due script più centrali, non hanno
   test diretti.

**I tre interventi con il miglior rapporto beneficio/costo** (tutti di taglia S):

| # | Intervento | Perché |
|---|---|---|
| 1 | Scrittura atomica + `fcntl.flock` + `load_meta` validante in `update_meta.py` (e `init_workflow.py`) | Elimina perdita di aggiornamenti, letture troncate e traceback su JSON malformato. ~40 righe di stdlib. |
| 2 | Un'unica funzione `run_gates()` chiamata sia da `set-phase` sia da `append-history`, più un'unica tabella di alias importata da entrambi gli script | Chiude la back door e la regressione via alias, e toglie una fonte di divergenza. |
| 3 | CI che esegue `unittest discover` su ogni `test_*.py`, un check di identità hash sulle 41 copie di `contracts.md` e un diff dei bundle `dist/*.skill` | Trasforma test e invarianti già esistenti in barriere. Nessun nuovo codice di test necessario. |

---

## 2. Mappa dell'architettura attuale

### 2.1 Dimensioni (misurate, esclusi `dist/`, `node_modules`, `.claude/`)

| Tipo | Righe | Note |
|---|---|---|
| Markdown | ~69 000 (tracciato) / 77 852 (con file non skill) | Di cui 15 170 sono le 41 copie identiche di `contracts.md` (370 righe, 67,6 KB ciascuna) |
| Python | 17 842 | Di cui 4 111 di test |
| HTML | 8 463 | Sito generato e mappa delle skill |
| TypeScript | 2 025 | `agent-guards/` |
| Shell | 1 874 | Installer, hook, regenerate |

52 skill (`ls */SKILL.md`). Di queste, 20 hanno script deterministici e 32 sono solo prosa (tutte le
`rn-*`, `module-add`, `vercel-deploy`, `write-tests`, `prd-*`, `state-discipline`, `data-fetching`).

### 2.2 Componenti

| Componente | Responsabilità | Input → Output | Stato posseduto | Controlli | Rischio principale |
|---|---|---|---|---|---|
| **Contratto** `dev-flow/references/contracts.md` (+40 copie vendorizzate) | Schema di `meta.json`, enum delle fasi, regole d'oro | — | Definizione normativa | Nessun check di identità tra le copie (§6.4) | Copie e implementazioni che divergono |
| **`update_meta.py`** | Unico scrittore di fase, history e artefatti; ospita i gate | CLI → `meta.json` | `phase`, `history`, `artifacts` | Smoke test in `evals.yml`; nessun test unitario | Scrittura non atomica, nessun lock, gate incompleti in `append-history` |
| **`init_workflow.py`** | Crea `.workflow/` | root → `meta.json` | — | Idempotente (verificato) | Stesso `write_text` non atomico |
| **`show_state.py`** | Legge lo stato e propone il passo successivo (router deterministico) | `meta.json` → testo | Tabella di routing (duplicata in SKILL.md) | Nessun test | Traceback su JSON malformato; output contraddittorio su fase sconosciuta |
| **`check_drift.py`** | Hash sha256 degli artefatti + propagazione transitiva | `meta.json#artifacts` → report | — | Smoke test in CI | Crash `TypeError` su voce senza `sha256` |
| **Gate** `*_gate.py` (6) + `inventory.py`, `wireframes.py`, `data_residency.py` | Precondizioni di fase con opt-out motivato | `meta.json` + script della skill proprietaria → rifiuto/ok | `inventory`, `wireframes`, `stack.*` | 3 suite su 6 non eseguite in CI | Invocati in tre modi diversi da `update_meta.py` |
| **Orchestratore** `dev-flow/SKILL.md` (496 righe, ~15,7k token) | Routing fase × stack verso le skill specialiste | prosa → decisione dell'agente | — | Lint check 9 (i nomi instradati esistono) | Contraddizioni interne; ~33k token per turno di routing |
| **Skill specialiste** (51) | Lavoro di fase | `meta.json` + artefatti → codice/artefatti | Artefatti in `.workflow/` | Lint strutturale; 13 suite di script | Prosa "enforced" senza enforcement (§6.6) |
| **`contract-package/`** | Implementazione Python "di riferimento" del contratto | — | — | 18 test su CI 3.9–3.12 | **Non è usata da nessuno**; dichiara il falso (§6.5) |
| **Installer** `install.sh` / `uninstall.sh` / `bootstrap/` | Copia le skill in 6 runtime | repo → `$HOME/...` | Backup in `<dir>-backup-<ts>/` | Lint: elenchi coerenti con il disco | Nessun test d'installazione; disinstallazione distruttiva su `bootstrap/` |
| **Generatori** `scripts/build_*.py`, `regenerate.sh`, `.githooks/pre-commit` | skills.json, sito, mappa, manifest, bundle | sorgenti skill → file generati | File generati | `--check` in CI per skills.json, sito, plugin; **non per i bundle** | Bundle tenuti allineati solo dall'hook locale |
| **`lint_skills.py`** (894 righe) | 13+ controlli strutturali | sorgenti → errori | — | Gira in CI e pre-commit | Non vede conteggi in `plugin.json`, nomi senza marker, identità di `contracts.md` |
| **Eval** `evals/` | Golden test sugli script, check sull'app generata, compliance comportamentale | — | Baseline datate | Self-test in CI | Copertura stretta (§6.7) |
| **`registry-intake`** | Governance del codice da registry terzi: allowlist, snapshot hashato, hook PreToolUse | comandi agente → deny/ask | `.claude/` del progetto | 84 test (in CI) | L'hook è un controllo su stringhe aggirabile (§6.8) |
| **`agent-guards/`** | Difese contro prompt injection per agenti eve | — | — | CI su Node 20/22/24 + test di mutazione | Nessuno rilevante |

### 2.3 Cosa è centrale e cosa si può accorpare

- **Centrali**: il contratto, `update_meta.py` con i gate, `show_state.py`, i generatori e il lint.
  Tutto il resto dipende da questi.
- **Da accorpare**: le due tabelle di routing (prosa in `dev-flow/SKILL.md` e dizionario in
  `show_state.py:15`, che chiede a un umano di tenerle allineate) diventano una sola, quella del
  codice. Le tre tabelle di alias diventano una.
- **Da decidere**: `contract-package/` deve diventare la libreria che gli script importano, oppure
  essere etichettato come riferimento non normativo. Oggi è una terza implementazione che diverge.

---

## 3. Voti motivati per area

> Nota: `docs/audit-prompt.md` (il prompt "in tre giri" nel repo) chiede di **non** dare voti
> numerici. Il prompt di questa sessione li chiede, quindi li do, ma ogni voto è ancorato a una
> misura e affiancato dalla domanda "cosa si rompe per primo". Il voto **architettura** e il voto
> **affidabilità dimostrata** sono tenuti separati.

| Area | Voto | Motivazione ed evidenza | Limite principale | Intervento per salire |
|---|---|---|---|---|
| **Architettura** | **8** | Contratto su filesystem, un solo scrittore di stato, gate con `applies/verify/remedy` (`dev-flow/scripts/*_gate.py`, 38–81 righe ciascuno, non copiati), generatori idempotenti. | Due router (prosa + `show_state.py`) e tre implementazioni dello schema. | Una sola tabella di routing e una sola tabella di alias. |
| **Contratto e stato** | **5** | Preserva i campi sconosciuti, `init` e `record-artifact` sono idempotenti, i percorsi sono confinati (`update_meta.py:121,141`). Ma: nessuna atomicità (`update_meta.py:96`), nessun lock, nessuna validazione, nessun `schema_version`. | Perdita di aggiornamenti concorrenti, misurata al 25–45 %. | P0-1, P0-2, P0-3, P1-2. |
| **Qualità delle skill** | **6** | Riferimenti integri (1 sola rottura reale su tutto il repo), esclusioni "Not for" presenti ovunque, igiene dei comandi distruttivi buona. | 96 esclusioni non reciproche, trigger identici tra skill web/RN, regole dichiarate "enforced" senza controllo. | P2-4, P2-5, P2-7. |
| **Orchestrazione** | **6** | Distinzione netta tra "proponi" e gate obbligatori; routing esplicito per 4 stack. | Contraddizioni interne (topologia eve, astro, numero di gate), ~33k token per turno, verifica "la fase non è avanzata" che dà falsi errori sulle skill orizzontali. | P2-1, P2-2, P2-3. |
| **Test ed evaluation** | **5** | Ci sono suite buone (registry-intake 84, design-lint 35, launch-audit 43) e un test di mutazione in CI per `agent-guards`. Ma la CI ne esegue 4 su 17; `update_meta`/`show_state` non hanno test; il golden test copre un solo script; nessuna eval del routing. | Una regressione nei gate di wireframe o primitives guard passerebbe la CI. | P1-1, P1-3, P1-4. |
| **Sicurezza operativa** | **6** | `set -euo pipefail` ovunque, nessun `rm -rf` su variabile vuota, `subprocess` sempre con lista di argomenti, segreti mai in chat (`project-infra-setup/SKILL.md:15`). | `uninstall.sh` cancella file dell'utente; l'hook è aggirabile con `npm exec shadcn -- add`. | P0-4, P2-9. |
| **Portabilità** | **4** | Installer per 6 runtime, nessun costrutto shell GNU-only, `from __future__ import annotations` dove serve. | Nessun test d'installazione per alcun runtime; 4 runtime dichiarati "scaffolded, not validated" (`install.sh:91-95`); `research.py` non compila su Python 3.9; gli hook valgono solo in Claude Code. | P1-6, P1-7, P2-10. |
| **Manutenibilità** | **6** | Generatori con `--check`, pre-commit che rigenera, bundle oggi allineati (verificato byte per byte). | Fatti datati che invecchiano senza segnale (Next 16.3 dichiarato `latest` in 41 copie, mentre il watch log registra 16.4.0); conteggi stantii che il lint non vede. | P1-5, P2-6, P2-8. |
| **Documentazione** | **6** | Molto estesa, onesta sui limiti delle eval (n=1 dichiarato), con il "perché" accanto a ogni regola. | Affermazioni false misurabili: backup in `<skill>.bak` (`README.md:113`), "two gates" (`README.md:893`), "43 skills" nel manifest del marketplace. | P0-4, P2-6. |
| **Maturità complessiva** | **6** | Ottima per uno strumento personale a sviluppatore singolo e sessione singola. | L'affidabilità dimostrata da test è inferiore a quella dichiarata dalla prosa. | Le tre azioni dell'executive summary. |

**Affidabilità dimostrata (separata dall'architettura): 5/10.** È il voto che conta per la domanda
"posso fidarmi di `meta.json` quando lavorano più agenti?". Oggi la risposta è no, ed è misurabile.

---

## 4. Dieci punti di forza (da non toccare)

1. **Il contratto su filesystem preserva i campi sconosciuti.** Gli script fanno round-trip del
   dizionario (regola in `contracts.md:368-370`), quindi un progetto creato con una versione più
   recente non perde dati se lo tocca una versione più vecchia.
2. **Il gate di fase è centralizzato e spiegato.** I rifiuti dicono cosa manca, come rimediare e come
   fare opt-out con una motivazione che resta in `meta.json`. I gate "non sollevano mai eccezioni".
3. **`set-phase` va solo in avanti**, e `--allow-regress` riesegue comunque i gate.
4. **Idempotenza reale, verificata**: `init_workflow.py` eseguito due volte lascia il file identico
   byte per byte; `record-artifact` normalizza le chiavi (`./sub/../f.txt` → `f.txt`) e sostituisce.
5. **Confinamento dei percorsi**: `record-artifact` rifiuta percorsi assoluti, `../` e symlink che
   escono dal progetto (`update_meta.py:121,141`).
6. **Drift detection transitiva** con smoke test in CI (`evals.yml`, step "Smoke-test artifact
   hashing").
7. **Generatori deterministici con `--check` in CI** per skills.json, sito (53 pagine) e plugin. Ho
   ricostruito i 52 bundle in una copia del repo e li ho confrontati con quelli committati: zero
   differenze.
8. **Il lint è ampio e mirato**: frontmatter, cap a 1024 caratteri, nomi instradati esistenti,
   elenchi degli installer coerenti col disco, file vendorizzati di `agent-guards` in sync. Una sola
   rottura di riferimento reale su tutto il repo (`heroicons-animated`, §6.6).
9. **Eval che misurano il comportamento, non la prosa**: `evals/compliance/comply.py` gradua sessioni
   `claude -p` reali su tre livelli di supporto e dichiara onestamente che n=1 "è un aneddoto, non un
   tasso" (`evals/compliance/baselines/2026-09-22/README.md`). `generated-page/check.py --selftest`
   verifica che ogni check scatti sul caso cattivo e taccia su quello buono. La CI di `agent-guards`
   rimuove una difesa e pretende che la suite fallisca (`.github/workflows/agent-guards.yml`).
10. **Igiene shell e dei comandi**: `set -euo pipefail` in tutti gli script, backup spostati fuori
    dalla cartella delle skill per evitare la doppia registrazione (`install.sh:270-274`), HOME con
    spazi funzionante su tutte e 6 le piattaforme, nessun `push --force` o `reset --hard` nelle skill,
    `git add -A` esplicitamente vietato (`dev-flow/SKILL.md:411`).

---

## 5. Dieci problemi o rischi più importanti

| # | Problema | Tipo | Dove |
|---|---|---|---|
| 1 | Aggiornamenti concorrenti di `meta.json` persi in silenzio; letture troncate durante la scrittura | **[DIMOSTRATO]** | `update_meta.py:94-96` |
| 2 | `append-history --phase-after` scavalca i gate di data residency, design lint, registry intake e primitives guard | **[DIMOSTRATO]** | `update_meta.py:308-316` contro `:231-268` |
| 3 | Alias delle fasi divergenti: una regressione di fase passa con exit 0 | **[DIMOSTRATO]** | `show_state.py:62` contro `update_meta.py:67` |
| 4 | `uninstall.sh` cancella la `bootstrap/` e i file di bootstrap dell'utente; il README promette un ripristino che non esiste | **[DIMOSTRATO]** | `uninstall.sh:124-133`, `README.md:113` |
| 5 | 13 suite di test su 17 non girano in CI, comprese quelle dei gate di `set-phase` | **[DIMOSTRATO]** | `.github/workflows/lint-skills.yml:88-100` |
| 6 | Nessuna validazione di `meta.json`: traceback su JSON malformato o vuoto in ogni script, tipi sbagliati persistiti | **[DIMOSTRATO]** | `update_meta.py:91`, `show_state.py:175`, `check_drift.py:88,125` |
| 7 | `contract-package` dichiara di essere la base degli script ma non è importato da nessuno, e scarta campi | **[DIMOSTRATO]** | `contract-package/src/.../core.py:3-5,304` |
| 8 | Identità delle 41 copie di `contracts.md` non verificata da alcun controllo (oggi sono identiche) | **[DIMOSTRATO]** (assenza del controllo) / **[RISCHIO]** (divergenza) | `lint_skills.py:640-662` |
| 9 | Contraddizioni nell'orchestratore: topologia eve, `astro` proposto e poi rifiutato, numero dei gate pre-deploy | **[DIMOSTRATO]** | `dev-flow/SKILL.md:139-141,166,195,289-293` |
| 10 | Fatti di terze parti che invecchiano senza segnale (Next 16.3 dato per `latest` in 41 copie; i due `stack-defaults.md` divergono nella prosa) | **[DIMOSTRATO]** | `contracts.md:282`, `docs/vercel-changelog-watch.md:57` |

Non ho trovato problemi significativi in: integrità dei riferimenti tra skill, idempotenza di init e
record-artifact, sincronizzazione dei generatori e dei bundle a oggi, iniezione di comandi negli
script, compatibilità della shell tra macOS e Linux.

---

## 6. Evidenze tecniche

### 6.1 Esecuzione dei test (risultati reali, macOS, Python 3.14.6, Node 24.21.0)

| Suite | In CI? | Risultato locale |
|---|---|---|
| `scripts/lint_skills.py` | sì | ✓ Clean (9 note sulla lunghezza delle descrizioni) |
| `design-md-to-app/scripts/test_setup_design_lint` | sì | 35 OK |
| `registry-intake/scripts/test_registry_intake` | sì | 84 OK |
| `dev-flow/scripts/test_data_residency` | sì | 9 OK |
| `evals/compliance/comply.py selftest` | sì | 13/13 |
| `evals/generated-page/check.py --selftest` | sì | 16/16 |
| `evals/run_evals.py --ci` | sì | 11/11 (dopo aver installato Pillow/numpy/scikit-learn in un venv: il Python di sistema non li ha) |
| `contract-package` pytest | sì | 18 passed |
| `agent-guards` `npm test` | sì | 29 pass |
| `build_agent_plugin.py --check`, `build_site.py --check` | sì | ✓ |
| `dev-flow/scripts/test_inventory` | **no** | 16 OK |
| `dev-flow/scripts/test_wireframes_gate` | **no** | 14 OK |
| `dev-flow/scripts/test_primitives_guard_gate` | **no** | 7 OK |
| `dev-flow/scripts/test_research` | **no** | 14 OK |
| `design-md-to-app/scripts/test_setup_primitives_guard` | **no** | OK |
| `compliance-audit`, `coss-ui`, `launch-audit` (43), `linear-scrum`, `project-infra-setup`, `promote-component`, `transitions`, `wireframe-canvas` | **no** | tutte OK |

Verifica che nessuna di queste sia richiamata altrove:
`grep -rn "test_inventory\|test_wireframes\|test_primitives\|test_scan" .github .githooks scripts evals` → nessun risultato.

**Cosa i test passati non provano**: nessuno esercita `update_meta.py` sotto concorrenza, su JSON
malformato o con alias; nessuno esegue `install.sh`/`uninstall.sh`; nessuno verifica la scelta della
skill da parte dell'orchestratore.

### 6.2 Contratto e stato

**Scrittura non atomica e lost update [DIMOSTRATO].**
`save_meta` è `meta_path.write_text(json.dumps(...))` (`update_meta.py:94-96`; lo stesso schema in
`init_workflow.py:61` e in `contract-package/.../core.py:304`). Non esistono `os.replace`,
`tempfile` né `flock` negli script (`grep -n "flock\|os.replace" dev-flow/scripts/*.py` → solo usi nei
test). Riproduzione:

```bash
python3 dev-flow/scripts/init_workflow.py $D --name C
for i in $(seq 1 20); do python3 dev-flow/scripts/update_meta.py $D append-history --skill s$i & done; wait
# → 11 /20 voci di history sopravvissute; tutti i processi exit 0
```

Un agente separato ha misurato 14–15 su 20 in tre prove con 20 `append-history` e 20
`record-artifact` concorrenti. Con un lettore concorrente su un `meta.json` da ~1 MB: 30 letture
vuote su 1 102. **[RISCHIO]** derivato dal codice: un crash tra il troncamento e la scrittura lascia
un file vuoto, e da lì ogni script termina con un traceback (§6.2, validazione).

**Il modello è adeguato a un singolo sviluppatore con un solo agente alla volta.** Smette di esserlo
nel momento in cui due agenti (subagenti paralleli, una worktree più la sessione principale, un loop
autonomo e un umano) scrivono sullo stesso progetto. È lo scenario che il repo stesso promuove
(memoria "autonomy execution", loop scrum). Un lock di file locale basta: non serve altro.

**Back door nei gate [DIMOSTRATO].**

```bash
# progetto next+shadcn, inventory e wireframes saltati con motivazione, data_residency non decisa
update_meta.py $D set-phase deployed
# → "Phase change refused: 'empty' → 'deployed' needs a data-residency decision."
update_meta.py $D append-history --skill x --phase-after deployed
# → exit 0; phase = deployed, stack.data_residency = None
```

`append-history` controlla solo `inventory_refusal` e `wireframes_refusal`
(`update_meta.py:313-314`); gli altri quattro gate sono solo in `cmd_set_phase`
(`update_meta.py:231-268`). Oggi le skill chiamano `set-phase` per prima
(`monorepo-bootstrap/SKILL.md:175`, `rn-bootstrap/SKILL.md:91`), quindi la porta è latente, non
attiva. La CI testa questa back door solo per l'inventory (`evals.yml`, step "The inventory gate").

**Regressione via alias [DIMOSTRATO].**
`show_state.py:62` accetta `page-generated`, `design-extracted`, `module-added`; `update_meta.py:67`
solo `module-added`. Un `meta.json` con `"phase":"page-generated"` ha indice −1 per `update_meta`:

```bash
echo '{"phase":"page-generated", ... inventory skipped ...}' > meta.json
update_meta.py $D set-phase idea_captured   # → "phase: page-generated → idea_captured", exit 0
```

**Cinque copie dell'enum delle fasi.** `contracts.md`, `update_meta.PHASES`, `core.Phase`,
`show_state` e `setup_design_lint.PHASES_BEFORE_SCAFFOLD` oggi coincidono (11 fasi, confronto
meccanico). Fa eccezione `bootstrap/templates/system-prompt.md:17`, indietro di quattro fasi e con la
grafia kebab **[DIMOSTRATO]**. L'unico controllo incrociato confronta `core.py` con `contracts.md`
(`contract-package/tests/test_core.py:256`); nulla confronta `update_meta.PHASES`. Il commento di
`lint_skills.py:770` ("core.py is the only place phases are declared") è falso.

**Validazione assente [DIMOSTRATO].** Matrice misurata (exit code; TB = traceback; W = file riscritto):

| caso | show_state | check_drift | set-phase | append-history | record-artifact | init |
|---|---|---|---|---|---|---|
| JSON malformato / vuoto / array | 1 TB | 1 TB | 1 TB | 1 TB | 1 TB | 1 TB |
| `history = {}` | 0 | 0 | 1* | 1 TB | 0 W | 0 |
| `artifacts = []` | 0 | 0 | 1* | 0 W | 1 TB | 0 |
| `phase` intero o sconosciuto | 0 | 0 | 1* | 0 W | 0 W | 0 |

`*` = rifiutato pulito dal gate di inventory. Con un inventory presente, `set-phase` da `"bogus"`, `3`
o `null` riesce. `check_drift.py:125` va in `TypeError` su una voce senza `sha256`.

**Fase sconosciuta e router [DIMOSTRATO].** Con `{"phase":"shipping"}` `show_state.py` stampa cinque
avvisi "missing on a scaffolded project" e poi propone "unknown phase — treat as empty:
prd-from-idea": due conclusioni opposte nello stesso output.

**History e fase possono divergere [DIMOSTRATO].** `set-phase` non scrive una voce di history;
`append-history` registra `phase_after` anche quando la fase non cambia (regressione rifiutata in
silenzio).

**Versioning [RISCHIO].** Non c'è un campo `schema_version`. `contracts.md` ha 53 commit dal
2026-04-25, 26 dal 2026-09-10, e nessuno script di migrazione. La compatibilità regge oggi grazie alle
letture tolleranti `.get()` e alla preservazione dei campi: funziona, ma non c'è modo di sapere con
quale versione del contratto è stato scritto un progetto.

### 6.3 Installazione e disinstallazione

Tutti i test sono stati fatti con `HOME` puntato a una directory temporanea.

- **[DIMOSTRATO] `uninstall.sh` cancella file dell'utente.** `install.sh:286-287` scrive in
  `$SKILLS_DIR/bootstrap/`; `uninstall.sh:124-125` fa `rm -rf "$SKILLS_DIR/bootstrap"`. Con una skill
  utente preesistente `skills/bootstrap/SKILL.md`, la disinstallazione l'ha cancellata. Stesso
  comportamento per `AGENTS.md`, `GEMINI.md`, `.cursorrules` e `system-prompt.md`
  (`uninstall.sh:128-133`). Su Codex, `AGENTS.md` è proprio il file che l'utente unisce a mano.
- **[DIMOSTRATO] Ripristino promesso e non eseguito.** `README.md:113` dice backup in `<skill>.bak` e
  "uninstall + restore backups". In realtà `install.sh:275-277` sposta in
  `<skills-dir>-backup-<timestamp>/`, e `uninstall.sh:113-119` ripristina solo i `.bak` legacy
  (pre 2026-08-28). Una modifica locale a `forms/` è rimasta orfana nel backup.
- **[DIMOSTRATO] I backup si accumulano senza limite**: ~7 MB per esecuzione. Il commento di
  `install.sh:42-45` ("one level only") descrive il comportamento precedente.
- **[DIMOSTRATO, impatto basso]** Due installazioni nello stesso secondo condividono la cartella di
  backup e la seconda sovrascrive il backup della prima (`install.sh:276`).
- **[DIMOSTRATO, minore]** `uninstall.sh --platform` senza valore esce con 1 senza messaggio; `cursor`
  e `generic` condividono `~/.dev-flow-skills`.
- **Nessun problema**: installazione pulita, reinstallazione idempotente (a parte i backup), skill
  symlinkata (si sposta il link, non il target), doppia disinstallazione, HOME con spazi.

### 6.4 Duplicazione e invarianti non verificate

- **41 copie di `contracts.md`**: tutte con lo stesso hash, anche dentro i 41 bundle `dist/*.skill`.
  Ma `lint_skills.py:640-662` (`VENDORED_SOURCE`) verifica solo `guards.template.ts`. Ho aggiunto una
  riga a `forms/references/contracts.md` in una copia del repo: il lint restava "✓ Clean"
  **[DIMOSTRATO]**. L'invariante esiste solo come loop md5 manuale in `CONTEXT.md:186`, con un
  conteggio stantio ("33 skill", `CONTEXT.md:172`).
- **`stack-defaults.md`** in `rn-fundamentals/` e `rn-bootstrap/`: tabelle identiche, prosa divergente
  su NativeWind v5 **[DIMOSTRATO]**. `refresh_stack_defaults.py` riscrive solo le tabelle.
- **Bundle**: allineati oggi, ma la CI non li verifica; li tiene in riga solo l'hook pre-commit, che
  esiste solo nei clone dove è stato installato. Il commento dell'hook registra 12 bundle su 51
  sbagliati il 2026-10-03 **[RISCHIO]**.

### 6.5 `contract-package`

Nessuno script importa `dev_flow_contract` (verificato con grep). Il docstring "the CLI scripts
delegate to these primitives" (`core.py:3-5`) e il README ("runtime is a thin wrapper") sono falsi
**[DIMOSTRATO]**. Non ha gate (`set_phase(root, 'deployed')` da `empty` riesce). `core.record_artifact()`
scarta `inventory`, `wireframes`, `linear`, `stack.agent`, `stack.data_residency` e
`stack.design_lint`, violando `contracts.md:370` **[DIMOSTRATO]**. `core.Stack` (`core.py:83-98`) è
indietro di sei campi. Il suo workflow CI non si attiva quando cambia `update_meta.py`.

### 6.6 Skill e orchestrazione

- **Rottura di riferimento**: `dev-flow/SKILL.md:166` chiama la skill `heroicons-animated`; la skill
  si chiama `animated-icons` **[DIMOSTRATO]**. Il lint non la vede perché non c'è un marker "route to"
  davanti al nome.
- **Topologia**: `dev-flow/SKILL.md:293` dice che attivare eve "promotes the project to a monorepo";
  la Topology policy (`:231`, forma 1 = agente dentro l'app singola) e `contracts.md:279` ("does
  **not** dictate a repo shape") dicono il contrario **[DIMOSTRATO]**.
- **`astro`**: proposto per i siti marketing (`dev-flow/SKILL.md:195`) e poi rifiutato dal router
  (`:67`; `show_state.py` stampa "not recognized — dev-flow refuses to guess") **[DIMOSTRATO]**.
- **Gate pre-deploy**: quattro secondo `:140` e `show_state.py:31`; `:139` ne nomina uno, `:141` ne
  elenca tre; `:164` e `shadscan/SKILL.md:241` dicono "trio"; `vercel-deploy/SKILL.md:70-79` controlla
  "the three gates" e non legge `meta.json#launch_audit` **[DIMOSTRATO]**.
- **Loop di routing**: `:184` dice "loop until … `module_added`", ignorando `feature_complete` e
  `deployed` **[FACOLTATIVO]**. Il passo 3 (`:180`) tratta "la fase non è avanzata" come errore, ma le
  skill orizzontali per costruzione non avanzano la fase **[RISCHIO]**: falsi fallimenti.
- **Ping-pong** `design-md-to-app` ↔ `coss-ui` (`design-md-to-app/SKILL.md:142`, `coss-ui/SKILL.md:42`)
  senza una regola "non restituire al chiamante" **[RISCHIO]**.
- **Trigger identici**: "add auth", "add a CMS", "set up Sanity" sia in `module-add` sia in
  `rn-module-add`; "artboard" sia in `iframe-canvas` sia in `wireframe-canvas`; "write tests for X" sia
  in `write-tests` sia in `rn-write-tests`, e `write-tests` controlla `stack.test` ma non
  `stack.framework` **[DIMOSTRATO]** (sovrapposizione), **[RISCHIO]** (selezione sbagliata). In totale
  96 esclusioni "Not for" sono unidirezionali.
- **Doppio proprietario** di regione Vercel ed env var: `module-add/references/module-deploy.md:3,11`
  e `project-infra-setup/SKILL.md:26` **[DIMOSTRATO]**.
- **Prosa "enforced" senza enforcement [DIMOSTRATO]**: regola d'oro 1 ("code is in English",
  dichiarata "enforced on every project", `dev-flow/SKILL.md:24`) e regola d'oro 2 (nessuna stringa
  hardcoded) non hanno alcun controllo; "Never bare `useEffect`. Ban it via lint"
  (`state-discipline/SKILL.md:51`) non è installato dallo scaffold. La regola d'oro 3, invece, è
  davvero applicata (`setup_primitives_guard.py` + `primitives_guard_gate.py` + `set-phase`).
- **Costo di contesto**: `dev-flow/SKILL.md` ≈ 15,7k token, più `contracts.md` "before doing anything"
  (`:22`, ≈ 17k), più `resources.md` prima di ogni WebSearch (`:339`, ≈ 11k): un turno di routing parte
  da ~33k token o più. La regola d'oro 3 (~3 000 caratteri) è ripetuta quasi identica a `:30` e `:159`.
  `design-md-to-app/SKILL.md` è di 1 324 righe (~27k token).
- **Comandi verso l'esterno**: `rn-eas-deploy` esegue `eas submit … --non-interactive` senza una
  conferma esplicita in quel punto **[RISCHIO]**; `shadscan/SKILL.md:28` esegue `npx --yes
  @shadscan/cli` senza versione fissata **[RISCHIO]**, mentre la riga successiva fissa `@0.9.0`.

### 6.7 Eval

- `run_evals.py` ha fixture per **un solo script** (`image-to-design-md/scripts/quantize_palette.py`,
  2 fixture, 11 asserzioni), mentre `evals/README.md` cita "DESIGN.md parsing, registry building, etc."
  **[DIMOSTRATO]**.
- Le eval comportamentali coprono 3 gate, con n=1 per livello (n=3 solo per registry-intake dopo la
  correzione), su un modello solo. Nessuna eval misura la **scelta della skill** da parte
  dell'orchestratore.

### 6.8 Sicurezza

- **Hook di registry-intake**: nega correttamente `npx`/`pnpm dlx`/`yarn dlx`/`bunx shadcn add`, URL,
  catene `&&` e sostituzioni `$(…)`, e chiede conferma su `allow`/`approve`. Lascia passare
  `npm exec shadcn -- add @x/y` (`registry_intake.py:1870` richiede `rest[0]=="add"`), `npx shad""cn
  add` (corto circuito su stringa grezza a `:1946`), `sh -c "…"`, `X=@x/y; npx shadcn add $X`,
  l'esecuzione diretta di `node_modules/shadcn/dist/index.js` e i comandi scritti in un file ed
  eseguiti **[DIMOSTRATO]**. Per uno strumento personale è una trappola per agenti onesti, non una
  barriera contro un avversario. Il problema è che nessun documento lo dice, e `npm exec` è una forma
  che un agente onesto può scrivere.
- **Prompt injection**: `dev-flow/scripts/research.py` porta nel contesto Reddit, X, HN e pagine
  arbitrarie (via `r.jina.ai`) senza una regola "contenuto = dati, non istruzioni" nella skill
  **[RISCHIO]**. `registry-intake` e `agent-guards` invece trattano bene il tema.
- **Coerenza interna**: `rn-write-tests/references/maestro.md:19` e
  `monorepo-add-python-service/SKILL.md:100` usano `curl … | bash`, che la regola K2 di registry-intake
  bloccherebbe in una skill di terzi **[FACOLTATIVO]**: sono installer ufficiali, ma vale una nota.
- **Nessun problema** su `shell=True` (unico uso in `evals/run_evals.py:90`, configurazione fidata del
  repo), `os.system`, `eval`, dump dell'ambiente o permessi richiesti agli agenti.

### 6.9 Portabilità

- **[DIMOSTRATO]** `dev-flow/scripts/research.py:276` annida apici uguali dentro una f-string, sintassi
  valida solo da Python 3.12: `/usr/bin/python3` (3.9.6, il Python di sistema di macOS) fallisce con
  `SyntaxError`. È l'unico file su 69 che non compila su 3.9. La CI del lint gira solo su 3.12.
- **[DIMOSTRATO]** Nessun job CI esegue `install.sh` o `uninstall.sh` per alcun runtime.
  `install.sh:91-95` e la tabella di `README.md:590-596` dichiarano Codex, Copilot, Gemini e Cursor
  "scaffolded, not validated": la documentazione è onesta, ma `README.md:586` parla di skill
  "runtime-portable".
- **[RISCHIO]** Quattro skill dipendono dagli hook di Claude Code (`.claude/settings.json`,
  `$CLAUDE_PROJECT_DIR`) e due dai canvas di claude.ai. Su Codex o Cursor, registry-intake scrive l'hook
  ma nulla lo esegue e nulla lo segnala. `bootstrap/tool-mappings.md` mappa i nomi degli strumenti ma
  non parla di hook.

### 6.10 Manutenibilità e documentazione

- **Conteggi stantii che il lint non vede [DIMOSTRATO]**: "43 skills" in
  `scripts/build_plugin_manifest.py:37` → `.claude-plugin/plugin.json:5` e
  `dist/agent-plugin/plugin.json:5` (sono 52); "WEB FAMILY (15 skills)" in `README.md:31` (sono 18);
  `install.sh:11-20` "Core: 5 / Web: 16" contro 10/19 nell'array; `lint_skills.py:202` "vendored into 30
  skills". `COUNT_FILES` (`lint_skills.py:402`) non include i `plugin.json`.
- **README contro il codice**: su 10 affermazioni verificate, 7 vere e 3 stantie (`README.md:113`
  backup, `README.md:893` "two gates at scaffolded" quando i gate che toccano quella transizione sono
  cinque, `install.sh:6` "five runtimes" contro sei).
- **Freschezza**: 108 marker datati "verified/checked", il più vecchio `stack-expo-rn.md:44`
  (2026-05-22), e 215 tag `[VERIFY]`. Nessun controllo segnala un marker vecchio, nessun workflow ha un
  `schedule:`. La regola "re-read anything older than a couple of months" (`resources.md`) è solo prosa,
  e il caso Next 16.4 mostra il buco **[DIMOSTRATO]**.
- **Rumore**: `skills.json` è cambiato in 257 commit su 468 dal 2026-07-01, per via di `generated_at` e
  `skill_md_lines` **[FACOLTATIVO]**. `.git` pesa 94 MB, in buona parte per i bundle zip riscritti.
- **Churn basso nella famiglia mobile** (es. `rn-expo-router` 1 commit da luglio): è coerente con la
  deriva delle versioni, ma non dimostra che le skill siano inutilizzate.

---

## 7. Benchmark concettuale (Fase C)

> Basato sulla conoscenza delle categorie di strumenti, **senza** consultare fonti esterne in questa
> sessione: le affermazioni sui prodotti terzi vanno considerate da verificare.

1. **Cosa risolve meglio di una raccolta di skill.** Lo stato persistente tra sessioni (`meta.json`
   più la drift detection), le precondizioni di fase applicate dal codice e non solo dalla prosa, e la
   ripresa del lavoro senza ricostruire il contesto. Una raccolta di skill native (o un `CLAUDE.md` /
   `AGENTS.md`) non ha nessuna di queste tre cose.
2. **Funzionalità davvero differenzianti.** I gate di fase con opt-out motivato e tracciato; la drift
   detection transitiva tra artefatti; la governance dei registry di terzi con snapshot hashato; le
   eval di compliance comportamentale a tre livelli di supporto. Le ultime due sono rare anche negli
   strumenti pubblici.
3. **Cosa delegare a strumenti esistenti.** La gestione dei task (già delegata a Linear tramite
   `linear-scrum`: corretto); la verifica di stile e i divieti di codice (ESLint, già usato per la
   regola d'oro 3: la stessa strada vale per le regole 1, 2 e per `useEffect`); l'hook come barriera,
   che resta un aiuto e non un sandbox (i permessi del runtime fanno il resto).
4. **Duplicazione inutile.** Due router (prosa e codice); tre implementazioni dello schema (contratto,
   script, `contract-package`); la regola d'oro 3 ripetuta due volte nella stessa SKILL.md. Le 41 copie
   di `contracts.md` **non** sono inutili: servono all'installazione di una skill singola. Vanno solo
   verificate.
5. **Cosa manca per un'affidabilità superiore.** Scrittura atomica con lock; validazione dello schema;
   test diretti dello scrittore di stato; CI che esegua i test esistenti; un'eval di routing con un
   dataset di casi.
6. **Cosa non vale la pena fare in un framework personale.** Un database o un servizio di
   orchestrazione; locking distribuito; un motore di workflow (Temporal e simili); test end-to-end
   automatici su tutti e sei i runtime; un sandbox per l'hook.

---

## 8. Matrice degli interventi P0–P3

Stime di sforzo: **S** ≤ mezza giornata, **M** 1–2 giorni, **L** > 2 giorni, intese per una sessione
con agente su un repo già noto. Gli intervalli sono condizionati all'assenza di sorprese nei test.

### P0 — Bug e rischi concreti

| ID | Titolo | Problema / evidenza | Modifica proposta | File | Dip. | Rischio regressione | Test | Sforzo | Accettazione | Beneficio |
|---|---|---|---|---|---|---|---|---|---|---|
| **P0-1** | Scrittura atomica e lock di `meta.json` | Lost update 11/20 (§6.2); letture vuote; `update_meta.py:94-96` | `save_meta`: tempfile nella stessa directory + `os.fsync` + `os.replace`. `fcntl.flock` su `.workflow/.meta.lock` attorno a load-modify-save. Su piattaforme senza `fcntl`, fallback su lockfile con `O_EXCL`. Stesso trattamento in `init_workflow.py`. | `dev-flow/scripts/update_meta.py`, `init_workflow.py` (e `inventory.py`/`wireframes.py`/`data_residency.py` se scrivono `meta.json` per conto proprio) | — | Basso: stesso formato su disco | Test di concorrenza (20 processi → 20 voci); un lettore concorrente non vede mai un file vuoto | S (2–4 h) | 3 esecuzioni consecutive di 40 scritture concorrenti senza perdite; zero letture vuote su 1 000 | Lo stato regge i loop autonomi e i subagenti paralleli |
| **P0-2** | Gate unificati | Back door in `append-history` (§6.2); `update_meta.py:313-314` contro `:231-268` | Estrarre `run_gates(root, meta, cur, target)` con l'elenco completo; chiamarla da `cmd_set_phase` e da `cmd_append_history` | `update_meta.py` | — | Medio: una skill che oggi usa `append-history --phase-after` senza aver soddisfatto un gate inizierà a fallire. È il comportamento voluto, ma va annunciato nel changelog. | Per ogni gate: rifiuto sia via `set-phase` sia via `append-history` | S (2–3 h) | Lo step CI della back door esteso a tutti e sei i gate passa | Un gate non si scavalca più con un sottocomando |
| **P0-3** | Un'unica tabella di fasi e alias | `show_state.py:62` contro `update_meta.py:67`; regressione con exit 0 | Spostare `PHASES` e `PHASE_ALIASES` in un modulo `dev-flow/scripts/phases.py` importato da entrambi; un indice −1 (fase non riconosciuta) blocca un `set-phase` che non sia `--allow-regress` esplicito | `update_meta.py`, `show_state.py`, nuovo `phases.py` | — | Basso | Test: `page-generated` → `idea_captured` rifiutato; tutte le grafie alias normalizzate | S (1–2 h) | Il caso riprodotto in §6.2 esce con codice ≠ 0 | Una fonte in meno di divergenza |
| **P0-4** | Disinstallazione non distruttiva e README corretto | `uninstall.sh:124-133` cancella file dell'utente; `README.md:113` falso | `install.sh` scrive un manifest (`$SKILLS_DIR/.dev-flow-manifest`) con i percorsi installati; `uninstall.sh` rimuove solo quelli; `bootstrap/` diventa `.dev-flow-bootstrap/` (o viene rimossa solo se il suo contenuto coincide con quello installato). Opzione `--restore` che ripristina dall'ultimo backup. Aggiornare `README.md:113` e il commento di `install.sh:42-45`. | `install.sh`, `uninstall.sh`, `README.md` | — | Basso | Test d'installazione (P1-7): una skill utente `bootstrap/` e un `AGENTS.md` preesistente sopravvivono a install + uninstall | S–M (3–6 h) | Lo scenario di §6.3 non perde file | Nessuna perdita di lavoro dell'utente |

### P1 — Affidabilità

| ID | Titolo | Problema / evidenza | Modifica proposta | File | Dip. | Test | Sforzo | Accettazione |
|---|---|---|---|---|---|---|---|---|
| **P1-1** | CI esegue tutti i test | 13/17 suite fuori CI (§6.1) | Un job che scopre ogni `*/scripts/test_*.py` ed esegue `python3 -m unittest` nella sua directory; fallisce se una suite fallisce | `.github/workflows/lint-skills.yml` (o un nuovo `tests.yml` senza filtro `paths`) | — | Il job stesso | S (1 h) | Rimuovere un `assert` in `test_wireframes_gate.py` fa fallire la CI |
| **P1-2** | `load_meta` validante | Traceback su JSON malformato, vuoto o con tipi sbagliati (§6.2) | Una funzione condivisa: oggetto JSON, `phase` stringa, `history` lista, `artifacts` dizionario; errore leggibile con exit 2 e indicazione del backup `.bak` (P1-8). Usata da tutti gli script. `check_drift` tollera voci senza `sha256`. `show_state` non stampa avvisi "scaffolded" su una fase sconosciuta. | `update_meta.py`, `show_state.py`, `check_drift.py`, `init_workflow.py` | P0-3 | Matrice di §6.2 come test parametrico | S–M (3–5 h) | Nessun traceback nella matrice; nessun file riscritto con tipi invalidi |
| **P1-3** | Test diretti dello scrittore di stato | Nessun test per `update_meta.py`/`show_state.py` | `test_update_meta.py`: transizioni valide e non valide, alias, `--allow-regress`, idempotenza di `record-artifact`, confinamento dei percorsi, concorrenza (P0-1), back door (P0-2). `test_show_state.py`: tabella fase × stack → proposta. | `dev-flow/scripts/` | P0-1…P0-3 | — | M (1 giorno) | Copertura dei rami di `cmd_set_phase` e `cmd_append_history` ≥ 90 % (`coverage.py` in locale) |
| **P1-4** | Invarianti dei file vendorizzati | Nessun controllo sulle 41 copie di `contracts.md` (§6.4) | Aggiungere a `VENDORED_SOURCE` le 41 copie (sorgente: `dev-flow/references/contracts.md`) e la coppia `stack-defaults.md` | `scripts/lint_skills.py` | — | Modificare una copia → lint rosso | S (1 h) | L'esperimento di §6.4 fa fallire il lint |
| **P1-5** | Bundle verificati in CI | Solo l'hook locale tiene allineati i bundle | Step CI: rigenerare in una directory temporanea e confrontare il contenuto (hash per voce, non lo zip) | `.github/workflows/lint-skills.yml`, eventualmente `build_skill_bundles.py --check` | — | Toccare una reference senza rigenerare → CI rossa | S (1–2 h) | Il test descritto fallisce in CI |
| **P1-6** | Floor di Python dichiarato e verificato | `research.py:276` non compila su 3.9 | Correggere la f-string; aggiungere uno step `python -m compileall -q` su una matrice 3.9 e 3.12 per tutti gli script delle skill | `dev-flow/scripts/research.py`, workflow CI | — | La matrice stessa | S (1 h) | `compileall` verde su 3.9 |
| **P1-7** | Test d'installazione | Nessun job CI esegue gli installer (§6.9) | Job che, con `HOME` temporaneo, per ogni `--platform`: installa, reinstalla, disinstalla; verifica l'elenco dei file, la sopravvivenza dei file utente (P0-4) e l'assenza di skill duplicate | nuovo workflow `install.yml` | P0-4 | — | S–M (3–5 h) | Verde su ubuntu e macos per tutte e sei le piattaforme |
| **P1-8** | ~~Backup di sicurezza di `meta.json`~~ **Superato (2026-10-17):** la scrittura atomica di P0-1 elimina il file vuoto da crash; il recupero da una modifica a mano sbagliata resta git. Non implementato per scelta. | Un file vuoto o corrotto blocca tutto, senza copia | Prima di ogni `os.replace`, ruotare la versione precedente in `.workflow/meta.json.bak` (una sola copia) | `update_meta.py` | P0-1 | Corrompere il file → `load_meta` indica il `.bak` | S (1 h) | Il ripristino da `.bak` funziona nel test |
| **P1-9** | `contract-package`: decidere il ruolo | Dichiara il falso, scarta campi (§6.5) | **Raccomandazione:** etichettarlo come riferimento non normativo, correggere docstring e README, preservare i campi sconosciuti e far scattare la sua CI anche su `update_meta.py`. Farlo importare dagli script raddoppierebbe la superficie da migrare senza un beneficio dimostrato. Correggere o rimuovere `bootstrap/templates/system-prompt.md:17`. | `contract-package/`, `bootstrap/templates/` | P0-3 | Test di round-trip con campi sconosciuti | S (2 h) | Nessuna affermazione falsa; `record_artifact` preserva `inventory` |
| **P1-10** | `set-phase` scrive la history | History e fase divergono (§6.2) | `set-phase` aggiunge una voce `{skill: "set-phase", phase_before, phase_after}`; `append-history` non registra un `phase_after` che non ha applicato | `update_meta.py` | P0-2 | Coerenza: l'ultima voce con `phase_after` coincide con `phase` | S (1 h) | Invariante verificata nel test P1-3 |

### P2 — Manutenibilità ed efficienza

| ID | Titolo | Evidenza | Modifica | Sforzo | Accettazione |
|---|---|---|---|---|---|
| **P2-1** | Contraddizioni dell'orchestratore | §6.6 | Correggere `heroicons-animated` → `animated-icons` (`:166`); rimuovere `astro` da `:195` o farlo riconoscere; allineare la topologia eve (`:289-293`) alla Topology policy; un unico numero di gate pre-deploy in SKILL.md, nel contratto e in `shadscan`; `vercel-deploy` legge `meta.json#launch_audit`; il loop termina a `deployed` | S | `grep` mirati senza contraddizioni; lint verde |
| **P2-2** | Una sola tabella di routing | `show_state.py:15` "keep the two in sync" | La tabella in `show_state.py` è la fonte; la sezione di SKILL.md viene generata da `sync_skill_map.py` (o da uno script nuovo) e verificata in CI | M | Modificare il dizionario senza rigenerare → CI rossa |
| **P2-3** | Dieta del contesto di `dev-flow` | ~33k token per turno di routing | Spostare le policy (`:144-166`, `:329-419`) in reference caricate su richiesta; togliere il duplicato della regola d'oro 3; sostituire "leggi `contracts.md` prima di tutto" con "leggi la sezione X quando serve" | M | `SKILL.md` ≤ 250 righe; nessuna regola persa (diff semantico rivisto a mano) |
| **P2-4** | Trigger reciproci | 96 esclusioni unidirezionali; trigger identici | Aggiungere la parola di stack ("Next.js" / "Expo") ai trigger condivisi; esclusioni reciproche per le coppie di §6.6; un check di lint che segnali (warning) i "Not for: X" non ricambiati | S–M | Il nuovo warning a zero sulle coppie elencate |
| **P2-5** | Un proprietario per le impostazioni Vercel | §6.6 | `project-infra-setup` possiede le impostazioni di progetto (regione, env var, link); `module-add deploy` possiede `vercel.json`. Dichiararlo in entrambe | S | Nessuna doppia rivendicazione nelle descrizioni |
| **P2-6** | Conteggi e affermazioni stantie | §6.10 | Calcolare il numero di skill in `build_plugin_manifest.py` da skills.json; aggiungere i due `plugin.json` a `COUNT_FILES`; estendere `FAMILY_COUNT_RE` alla forma "(N skills)"; correggere `README.md:893`, `install.sh:6,11-20`, `CONTEXT.md:172`, `lint_skills.py:202`, `evals/README.md` | S | Lint rosso se un conteggio diverge |
| **P2-7** | Allineare "enforced" alla realtà | Regole d'oro 1 e 2, `useEffect` | Per ciascuna: o una regola ESLint nel preset di design-lint (es. `react/jsx-no-literals` per la 2, `no-restricted-syntax` per `useEffect`), o la parola "convention" al posto di "enforced". Per la regola 1 la seconda strada è la più onesta. | S–M | Ogni "enforced" nella prosa ha un controllo che lo implementa |
| **P2-8** | Segnale di freschezza | 108 marker datati, nessun controllo | Una nota di lint per i marker più vecchi di 60 giorni; un workflow mensile con `schedule:` che esegue `refresh_stack_defaults.py --dry-run` e apre una issue | S | La nota compare su `stack-expo-rn.md:44` |
| **P2-9** | Limiti dell'hook dichiarati e `npm exec` coperto | §6.8 | Gestire `npm exec <pkg> -- add` e il corto circuito su stringa grezza; documentare in `registry-intake/SKILL.md` che l'hook è una trappola per agenti onesti, non una barriera | S | Test per `npm exec shadcn -- add` → deny |
| **P2-10** | Avviso sugli hook nei runtime non Claude | §6.9 | `registry_intake.py setup` e i template di bootstrap avvisano che su Codex/Cursor l'hook non viene eseguito; `tool-mappings.md` include una riga sugli hook | S | Il testo compare nei template |
| **P2-11** | Conferme sui comandi verso l'esterno | §6.6 | Conferma esplicita prima di `eas submit`; versione fissata nel comando "explore" di `shadscan` | S | — |
| **P2-12** | `schema_version` nel contratto | §6.2 | Campo opzionale `contract_version` scritto da `init_workflow.py` e aggiornato da `update_meta.py`; la sua assenza significa "precedente all'introduzione". Nessuna migrazione oggi: serve a poterne fare una domani. | S | Un progetto vecchio continua a funzionare; uno nuovo porta il campo |
| **P2-13** | Rumore nei generatori | 257 commit su skills.json | Togliere `generated_at` da skills.json; conservazione limitata dei backup dell'installer (ultimi 3) | S | — |

### P3 — Evoluzione facoltativa

| ID | Titolo | Motivazione | Sforzo |
|---|---|---|---|
| **P3-1** | Eval di routing | Nessuna misura della scelta della skill. Dataset di 30–50 casi (fase, stack, richiesta → skill attesa e skill vietate), 3 ripetizioni per caso, metrica di accuratezza e di attivazioni incompatibili. Diagnostica, non bloccante. | M |
| **P3-2** | Più gate nelle eval di compliance, con n ≥ 3 | Oggi 3 gate con n=1. Priorità a `wireframes` e `inventory`, che sono i gate più "umani". | M (più costo API) |
| **P3-3** | Dividere `design-md-to-app` | 1 324 righe, quattro percorsi di libreria più chat surface più setup di lint e guard: le parti si scelgono in modo indipendente. Solo dopo P2-3, e solo se l'eval di routing (P3-1) mostra selezioni sbagliate. | L |
| **P3-4** | Regola anti-injection per `research.py` | Contenuto web trattato come dati, citando il modello di `agent-guards` | S |
| **P3-5** | `node_modules/` nel `.gitignore` di root | Oggi è ignorato solo dentro `agent-guards/` | S |

---

## 9. Architettura target (6–12 mesi)

**Principio: stessa architettura, scrittore di stato più robusto, una fonte per ogni fatto.**

- **Invariato**: il contratto in JSON + Markdown dentro `.workflow/`; le skill come consumatori; i
  gate con `applies/verify/remedy` e opt-out motivato; i generatori con `--check`; il lint; le eval
  comportamentali; `registry-intake` e `agent-guards`; le 41 copie vendorizzate di `contracts.md`
  (servono all'installazione singola).
- **Rafforzato**: `update_meta.py` diventa l'unico punto di scrittura con lock, scrittura atomica,
  backup a una copia, validazione e gate unificati. La CI esegue tutti i test esistenti, verifica i
  bundle e le copie vendorizzate, compila su 3.9 e prova gli installer.
- **Semplificato**: un modulo `phases.py` per fasi e alias; una tabella di routing (quella del codice)
  da cui si genera la prosa; `dev-flow/SKILL.md` ridotto al routing, con le policy nelle reference;
  `contract-package` dichiarato riferimento non normativo.
- **Nuovo (piccolo)**: `phases.py`; un manifest d'installazione; un campo `contract_version`
  opzionale; un'eval di routing diagnostica.
- **Da non costruire**: vedi §12.

**JSON + Markdown restano adeguati?** Sì. Il problema dimostrato è la concorrenza tra processi locali
sullo stesso file, che un `flock` risolve. SQLite risolverebbe la stessa cosa, ma renderebbe il
contratto illeggibile agli agenti e ai diff di git: il costo supera il beneficio. Il punto in cui
riconsiderare è uno scenario oggi assente: più macchine che scrivono lo stesso progetto senza git
come mediatore.

**Serve un orchestratore più complesso?** No. I difetti dell'orchestrazione sono contraddizioni nella
prosa e una doppia tabella di routing, non limiti del modello basato su filesystem. Un motore di
workflow aggiungerebbe uno stato da sincronizzare con `meta.json`, cioè esattamente il tipo di
divergenza che questo audit trova.

**Compatibilità con i progetti esistenti.** Nessuna modifica è breaking sul formato di `meta.json`. Il
lock usa un file separato. `contract_version` è opzionale. La validazione rifiuta solo ciò che oggi
produce un traceback. L'unico cambiamento di comportamento è P0-2 (`append-history` applica tutti i
gate): va annunciato nel changelog, con l'indicazione di usare `set-phase`.

**Come misurare il miglioramento.**

| Metrica | Oggi (misurato) | Obiettivo |
|---|---|---|
| Voci sopravvissute su 20 scritture concorrenti | 11–15 | 20, su 3 prove |
| Gate scavalcabili via `append-history` | 4 su 6 | 0 |
| Suite di test eseguite in CI | 4 su 17 | 17 su 17 (più `test_update_meta`, `test_show_state`) |
| Celle della matrice di malformazione con traceback | 20 (3 casi di JSON non valido × 6 script, più 2) | 0 |
| Conteggi o affermazioni stantie note | ≥ 8 | 0, con lint che lo garantisce |
| Token per turno di routing di `dev-flow` | ~33k | ≤ 18k |
| Runtime con installazione testata in CI | 0 | 6 (installazione; il comportamento resta "non validato") |

---

## 10. Roadmap dei primi 30 giorni

| Settimana | Interventi | Uscita verificabile |
|---|---|---|
| 1 | P0-1, P0-3, P0-2, P1-10 (in quest'ordine: lock e scrittura atomica prima, poi la tabella unica, poi i gate) + P1-3 per la parte che li copre | Il test di concorrenza e la back door estesa sono verdi in CI |
| 2 | P1-1, P1-4, P1-5, P1-6 (tutti S, tutti su CI e lint) + P1-2, P1-8 | CI con 17+ suite, lint che rifiuta una copia divergente di `contracts.md`, compileall su 3.9 |
| 3 | P0-4 + P1-7 (installer non distruttivo e suo test) + P1-9 | Job `install.yml` verde su 6 piattaforme; README corretto |
| 4 | P2-1, P2-6, P2-5, P2-11 (correzioni di prosa e conteggi) + avvio di P2-3 | Nessuna contraddizione tra i file elencati in §6.6; conteggi coperti dal lint |

Ogni intervento si chiude solo quando il suo criterio di accettazione è stato verificato.

---

## 11. Test da introdurre e criteri di accettazione

| Test | Tipo | Bloccante in CI? | Criterio |
|---|---|---|---|
| Concorrenza su `meta.json` (40 processi) | integrazione | **sì** | 40/40 voci, 3 ripetizioni |
| Lettore concorrente durante la scrittura | integrazione | **sì** | 0 letture vuote o troncate su 1 000 |
| Matrice di malformazione (§6.2) | contratto | **sì** | exit 2 con messaggio, nessun traceback, nessuna riscrittura |
| Transizioni non valide: salto con gate non soddisfatto, regressione, alias, fase sconosciuta | contratto | **sì** | Rifiuto via `set-phase` **e** via `append-history` |
| Idempotenza: `init` ×2, `record-artifact` ×2, `install.sh` ×2 | integrazione | **sì** | File identici, nessun duplicato |
| Compatibilità dello schema: fixture di `meta.json` da tre epoche (senza `inventory`, senza `wireframes`, attuale) | contratto | **sì** | `show_state` non va in crash; i campi sconosciuti sopravvivono a un round-trip |
| Drift: modifica, cancellazione, voce senza `sha256`, `derived_from` stantio | integrazione | **sì** | Stato corretto per ogni caso, nessun crash |
| Installazione e disinstallazione con `HOME` temporaneo, per piattaforma | installazione | **sì** | File dell'utente intatti, nessuna skill duplicata, `--restore` funzionante |
| Identità dei file vendorizzati | lint | **sì** | Una copia modificata fa fallire il lint |
| Bundle rigenerati uguali ai committati | generazione | **sì** | Diff vuoto |
| `compileall` su 3.9 e 3.12 | portabilità | **sì** | Verde |
| Routing deterministico: `show_state` su fixture fase × stack | unità | **sì** | Proposta attesa per ognuna delle 11 × 4 combinazioni |
| Routing LLM: dataset di 30–50 richieste, 3 ripetizioni, rubrica (skill attesa, skill vietate, nessuna attivazione incompatibile) | eval | **no**, diagnostico | Accuratezza ≥ 90 % sulla skill attesa; 0 attivazioni di skill vietate |
| Compliance comportamentale con n ≥ 3 su più gate | eval | **no**, diagnostico e a pagamento | Livello 2 ≥ 80 % per ogni check obbligatorio |

---

## 12. Funzionalità da non implementare

- **Un database** (SQLite o altro) per lo stato: il lock di file risolve il problema dimostrato, e il
  JSON resta leggibile da agenti e diff.
- **Un servizio o demone di orchestrazione**, o un motore di workflow: aggiungerebbe uno stato da
  tenere sincronizzato con `meta.json`.
- **Locking distribuito** o coordinamento tra macchine: nessuno scenario attuale lo richiede.
- **Una libreria di schema esterna** (pydantic, jsonschema) negli script: le skill girano con il
  `python3` dell'utente e senza dipendenze; la validazione necessaria sta in ~40 righe di stdlib.
- **Far importare `contract-package` agli script**: raddoppia la superficie da migrare senza un
  beneficio dimostrato.
- **Uniformare lo stile di tutte le skill**, o dividerle solo perché lunghe.
- **Test end-to-end comportamentali su tutti e sei i runtime**: il costo è alto e il valore per un
  utente che usa Claude Code in pratica è basso. Basta testare l'installazione e dichiarare il resto
  "non validato", come già fa il repo.
- **Trasformare l'hook di registry-intake in un sandbox**: per uno strumento personale basta
  dichiararne i limiti e coprire le forme che un agente onesto scrive.

---

## 13. Nuovo voto stimato dopo gli interventi

> **Questi sono stime, non misure.** Diventano risultati solo quando le metriche di §9 sono state
> rimisurate. `docs/audit-prompt.md` osserva giustamente che un voto previsto è inventato per
> costruzione: va letto come "ipotesi da falsificare".

| Area | Oggi | Stima dopo P0+P1 | Stima dopo P2 | Condizione per confermare la stima |
|---|---|---|---|---|
| Architettura | 8 | 8 | 8,5 | Una tabella di routing, una di fasi |
| Contratto e stato | 5 | 8 | 8 | Test di concorrenza e matrice di malformazione verdi in CI |
| Qualità delle skill | 6 | 6 | 7 | Zero contraddizioni nei file di §6.6; trigger reciproci |
| Orchestrazione | 6 | 6,5 | 7,5 | Routing generato dal codice; eval di routing ≥ 90 % |
| Test ed evaluation | 5 | 7,5 | 8 | 17+ suite in CI, installer testati |
| Sicurezza operativa | 6 | 7,5 | 8 | Disinstallazione non distruttiva verificata; hook su `npm exec` |
| Portabilità | 4 | 5,5 | 6 | Installazione testata su 6 piattaforme; compileall 3.9 |
| Manutenibilità | 6 | 7 | 8 | Lint su conteggi, copie vendorizzate e freschezza |
| Documentazione | 6 | 7 | 8 | Nessuna affermazione falsa tra quelle note |
| **Affidabilità dimostrata** | **5** | **7,5** | **8** | Le metriche di §9 rimisurate |

**Risultati effettivamente misurati in questo audit**: solo la colonna "Oggi" e le misure di §6.
Nessun intervento è stato implementato.

---

## Appendice — Cosa non è stato verificato

- Nessuna sessione `claude -p` è stata lanciata (le eval comportamentali sono a pagamento): i dati di
  compliance sono quelli committati al 2026-09-22.
- `shellcheck` non è installato su questa macchina: l'analisi della shell è stata manuale.
- I percorsi d'installazione di Codex e Copilot non sono stati confrontati con la documentazione
  attuale dei fornitori.
- Il benchmark (§7) non ha consultato fonti esterne.
- L'interruzione di un processo a metà scrittura è dedotta dal codice e non provocata; la lettura
  troncata sotto scrittura concorrente invece è stata misurata.

---

## Appendice — punti aperti durante l'implementazione (2026-10-17)

Emersi dalla prova di compliance a 5 sessioni (Claude Code 2.1.296, Sonnet, livello 2): ogni agente ha
scritto i file con `cat > percorso <<'EOF'` in Bash, e una sessione ha modificato `meta.json` con uno
script Python inline.

| ID | Titolo | Problema / evidenza | Modifica proposta | File | Sforzo | Accettazione |
|---|---|---|---|---|---|---|
| **P1-32** | Il guard dei primitivi vede le scritture via Bash subito, non a fine turno | L'hook PreToolUse del guard intercetta solo `Write\|Edit\|MultiEdit` (`setup_primitives_guard.py:47`); le scritture via shell le controlla solo lo `stop` (`primitives-guard.mjs:10`), cioè a fine turno, dopo che l'agente può aver costruito un'intera schermata a mano. Nella prova 4 sessioni su 4 hanno scritto i file via Bash. | Un hook **PostToolUse su Bash** che riusa la logica di `stop` sui soli file cambiati da quel comando: un registro degli hash dei file già controllati (in `os.tmpdir()`, per progetto) rende il controllo incrementale, senza tentare di interpretare il comando. Exit 2 dà il riscontro all'agente subito dopo il comando che ha aggiunto UI fatta a mano. | `design-md-to-app/assets/guard/primitives-guard.mjs`, `setup_primitives_guard.py`, test | M | Un `cat > page.tsx` con un `<button>` fatto a mano riceve il rifiuto alla chiamata successiva, non a fine turno; un comando che non tocca file UI non lancia il lint; i test del guard restano verdi. |
| **P1-33** | Una modifica a mano di `meta.json` viene riconosciuta, e non fa saltare i gate | Il contratto ammette la modifica diretta come ripiego, ma nulla la distingue da una scrittura degli script: una `phase` spostata a mano salta tutti i gate, e il `set-phase` successivo non li ricontrolla, perché parte dalla fase già "raggiunta". Nella prova, una sessione di data-residency ha scritto `meta.json` con Python inline. | `meta_io.write_json` registra un `meta_digest` (sha256 del documento senza il campo). Alla lettura, un digest che non corrisponde dice "modificato fuori dagli script". `show_state` lo segnala, e se la fase non coincide con l'ultima voce di history (invariante del punto 4) lo dice. `update_meta` calcola i gate a partire dall'ultima fase **registrata dagli script**, così una fase spostata a mano viene ricontrollata alla prima mossa successiva. | `dev-flow/scripts/meta_io.py` (+5 copie), `update_meta.py`, `show_state.py`, contratto, test | M | Una fase portata a mano a `scaffolded` senza data-residency: `show_state` lo segnala, e `set-phase page_generated` viene rifiutato dal gate di data residency; un file senza digest (tutti quelli esistenti) non dà avvisi finché uno script non lo riscrive. |
| **P1-34** | registry-intake controlla l'effetto dei comandi | L'hook PreToolUse legge il testo del comando, aggirabile in infiniti modi; registry aggiunti e snapshot modificati li trovava solo `check`, al gate di fase (fit-coach: un mese dopo). | Prima di ogni comando si salvano i problemi di registry; un hook PostToolUse (`hook-post`) segnala quelli introdotti dal comando. Non vede le installazioni da URL. | `registry-intake/scripts/registry_intake.py`, test | M | Un registry aggiunto o uno snapshot modificato da un comando sono segnalati subito dopo; un problema preesistente non viene ripetuto. |
