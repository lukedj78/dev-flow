# Audit del debito — un elenco solo, in ordine, per un progetto già online — 2026-10-18

Quinto punto della roadmap (`2026-10-17-founder-intelligence-design.md:449`, verbatim):

> 5. **Audit del debito ordinato** (M): una modalità di dev-flow, dopo `deployed`, che compone gli
>    audit esistenti con un controllo sulla copertura dei test e li ordina.

L'utente ha chiesto di saltare le domande (2026-10-18): le scelte di questo documento sono **mie**, salvo dove è
citata una sua decisione precedente.

## Il problema

Un progetto dev-flow arrivato a `deployed` ha già molti audit: sicurezza, conformità, costi, UI, lancio,
osservabilità, regole React, componenti da promuovere. Ma chi riapre il progetto dopo settimane non sa **da dove
cominciare**:

- ogni audit parla una lingua sua (`H/M/L`, `HIGH/MEDIUM/LOW`, `found/not checked`, `block/review`, nessuna
  severità per shadscan e launch-audit) e scrive in un posto suo (`meta.json#security`, `#compliance`, `#shadscan`,
  `#vercel_doctor`, `#launch_audit`, chat, `docs/…`);
- dopo `deployed` dev-flow dice una riga sola («re-run the gates after material changes») e nessuno controlla se un
  gate è vecchio rispetto all'ultimo cambio, tranne `vercel-deploy` e solo al momento del deploy;
- **nessuno guarda i test**: `write-tests` «doesn't gate on coverage», nessun progetto ha la copertura configurata,
  e non c'è niente che dica quale Server Action non ha un test.

Il risultato del Playbook che vogliamo: un elenco **ordinato** in tre fasce — *prima del prossimo rilascio*,
*insieme alle funzioni*, *dopo* — su tutto il codice, non su un diff.

## Fatti verificati (2026-10-18, ricognizione del repo)

- **Con script e JSON** (app-security usa la rete per le dipendenze e le regole di Semgrep, fino a 600 s per
  strumento; offline quelle parti dicono *not checked*):
  - `app-security/scripts/scan_security.py <root> --json` → `[{check, status, detail, where[], routed_to}]`,
    status `ok | found | not checked | not applicable`; nessuna severità, solo l'ordine «segreti nella storia
    prima».
  - `launch-audit/scripts/scan_launch.py <root> --json` → stesso formato, status `ok | missing | unknown | not
    requested`; solo web.
  - `module-add/scripts/observability_check.py <root> --json` → `[{level, status, detail}]`.
  - `compliance-audit/scripts/scan.py <root>` → `{findings[{id, severity H|M, article, title}]}`, senza file.
  - `registry-intake/scripts/registry_intake.py check <root>` → righe di testo, exit 0/1, niente `--json`.
  - `promote-component/scripts/scan_promotion.py <root>` → solo una tabella markdown.
- **CLI esterne** (`npx`, rete): shadscan (`docs/ui/shadscan.json`, `agentHandoff.actionables[]` con
  `disposition fix|verify|decide`) e vercel-doctor (`meta.json#vercel_doctor.findings{high,medium,low}`).
- **Solo prosa**: `spec-review` (un diff), `state-discipline`, `data-fetching`, `forms` (ricette `rg` →
  violazioni `HIGH|MEDIUM|LOW` in chat), `write-tests`.
- **Rischi accettati** già registrati, ciascuno a modo suo e **per controllo, non per file**:
  `security.findings.accepted` (`{check, reason}`), `launch_audit.dismissed`, `shadscan.false_positives` /
  `rules_left_red`. `compliance.flagged` **non** è un rischio accettato: vuol dire «serve una decisione legale».
- **Gli scanner danno segnali, non verdetti**: `scan_security.py` («SIGNAL, not a verdict») e `compliance scan.py`
  («verify each hit in code before reporting») chiedono all'agente di leggere ogni file segnalato.
- `meta.json#vercel_doctor` e `#compliance` tengono **solo i conteggi** per severità, non l'elenco.
- **Il modello «vecchio rispetto all'ultimo cambio»** esiste già: `verification_line` in `show_state.py` confronta
  `history[].ran_at` delle `MATERIAL_SKILLS` con il timestamp del blocco.
- **Copertura**: nessuna configurazione da nessuna parte (`@vitest/coverage-v8`, `json-summary`, `lcov` non
  compaiono). `stack.test` dice quali strati esistono (`vitest+playwright`, `jest-expo+rntl+maestro`).
- **Mobile**: nessuno script di audit; si applicano solo `app-security` e `compliance-audit`.
- **Conteggi vecchi dei gate**: `compliance-audit/SKILL.md:109` dice «three pre-deploy gates», `launch-audit`
  «fourth gate», `vercel-doctor/SKILL.md:122` chiama shadscan «the third gate», la descrizione di `shadscan` dice
  «One of four»; anche `README.md` e `AUDIT.md` hanno conteggi vecchi. I gate sono cinque.

## Cosa costruiamo

### 1. `dev-flow/scripts/debt_audit.py` — chi compone

Un solo script stdlib, nella cartella di dev-flow perché è una **modalità di dev-flow**, non una skill nuova (la
roadmap dice così, e una skill in più sarebbe un'altra cosa da installare per avere un elenco).

```
python3 debt_audit.py collect <root> [--json]     # raccoglie, ordina, scrive il report
python3 debt_audit.py show <root>                 # rilegge l'ultimo report, senza rieseguire niente
```

`collect`:

1. **Esegue gli scanner locali** delle skill sorelle, trovati per percorso accanto a dev-flow (come `show_state.py`
   carica `scope.py` e `founder.py`): app-security, launch-audit (solo web), observability_check, compliance,
   registry-intake, promote-component. Ognuno in un sottoprocesso con `sys.executable` e un timeout più lungo di
   quello interno dello scanner (app-security: 1800 s; gli altri: 120 s); se la skill non è installata, lo script
   fallisce o scade, la fonte vale **not checked** con il motivo, mai «ok». `--skip <fonte>` salta una fonte (per
   esempio app-security offline), che allora è *not checked*.
2. **Legge i risultati registrati** delle CLI esterne, senza eseguirle (servono rete e `npx`): `docs/ui/shadscan.json`
   (`agentHandoff.actionables[]`, un risultato per voce) e `meta.json#vercel_doctor` (solo conteggi: **una riga per
   severità**, `vercel-doctor:high` ecc., senza file; nuovo/chiuso si confronta sul conteggio). Se mancano, la fonte è *missing*; se sono più vecchi dell'ultimo cambio materiale,
   la fonte è *stale* e i suoi risultati restano nell'elenco marcati «da rieseguire».
3. **Legge i risultati degli audit in prosa** da `.workflow/debt/manual.json`, una lista nello schema comune
   (sotto). Lo scrive l'agente quando esegue le ricette di `state-discipline`, `data-fetching`, `forms`: lo script
   non finge di saper fare il loro lavoro.
4. **Aggiunge il controllo sui test** (§2).
5. **Applica le decisioni già prese**, che non spariscono ma vanno nella sezione «tenuti apposta» con il loro motivo:
   - le chiavi dei gate (`security.findings.accepted`, `launch_audit.dismissed`, `shadscan.false_positives` /
     `rules_left_red`) valgono **per controllo**: un controllo accettato dal gate è accettato su ogni file, perché
     è così che il gate l'ha deciso;
   - `.workflow/debt/reviewed.json` vale **per risultato** (`{"<id>": {"verdict": "confirmed" | "false_positive" |
     "accepted", "reason": "…", "at": "…"}}`) ed è dove l'agente scrive le sue verifiche (sotto);
   - `compliance.flagged` resta aperto, con la nota «serve una decisione legale».
6. **Segnale o confermato.** Un risultato fresco di app-security o compliance è un **segnale** finché
   `reviewed.json` non lo conferma: ha la sua fascia, ma il report lo marca «da confermare», e il conteggio
   *before-release* di `debt_line` conta solo i confermati («N da confermare, M da sistemare»). La modalità dice
   all'agente di leggere ogni segnale con le regole della skill che l'ha prodotto (`app-security/references/review.md`,
   la verifica di compliance-audit) e di scrivere il verdetto; un `false_positive` torna «tenuto apposta» nei giri
   successivi finché il file non cambia (lo script salva l'hash del file con il verdetto).
7. **Assegna la fascia** con una tabella fissa (§3) e **ordina dentro la fascia**.
8. **Scrive** `docs/debt/debt-audit.md` (per l'utente), `.workflow/debt/findings.json` (per l'agente) e
   `meta.json#debt_audit` (§5), più una voce di history. Il report è in inglese, come ogni file generato dalle
   skill; all'utente l'agente lo riassume in chat nella sua lingua.

`collect` gira a **qualsiasi fase** (serve anche a un progetto ereditato); è `debt_line` che lo propone solo da
`deployed`.

**Schema comune** di un risultato:

```json
{ "id": "app-security:authz:app/actions/plan.ts", "source": "app-security", "check": "authz",
  "band": "before-release", "file": "app/actions/plan.ts", "line": 12,
  "detail": "Server Action without a session check", "routed_to": "app-security", "stale": false }
```

L'`id` è stabile (fonte, check, file): un risultato che torna al giro dopo è lo stesso risultato, e il report dice
cosa è **nuovo** e cosa è **stato chiuso** dall'ultimo giro.

### 2. Il controllo sui test — la parte nuova

Due misure, la prima sempre disponibile:

- **Codice critico senza test** (statico, sempre). Per ogni superficie web: i file `"use server"` e le route handler
  (`app/**/route.ts`) che scrivono (`POST|PUT|PATCH|DELETE`, `insert|update|delete` di Drizzle). Un file è
  «testato» se un file di test (`*.test.*`, `*.spec.*`, `e2e/`, `tests/`) lo importa o ne nomina il percorso. Ogni
  file critico non testato è un risultato `tests:untested-mutation`.

  **Gli e2e contano.** Playwright raggiunge una Server Action dall'URL, senza importarla: un file critico conta
  come testato anche quando una spec in `e2e/` visita (`goto("/percorso` o la stringa `"/percorso"`) una pagina che
  lo importa. L'URL della pagina si ricava dal suo percorso togliendo i gruppi `(…)` e i segmenti dinamici iniziali
  come `[locale]`. Il report distingue «unit» da «solo e2e». Su mobile e agent: not applicable (non c'è un
  equivalente chiaro di «codice che scrive»; scelta mia).
- **Copertura** (quando c'è il dato). Se esiste `coverage/coverage-summary.json` (formato istanbul `json-summary`,
  lo stesso per Vitest e Jest), lo script legge la percentuale delle righe totale e dei file critici. Se non c'è,
  la fonte è **not checked** e il report dice il comando che lo produce:
  - Vitest: `pnpm add -D @vitest/coverage-v8` una volta, poi `pnpm vitest run --coverage --coverage.reporter=json-summary`;
  - Jest: `npx jest --coverage --coverageReporters=json-summary`.

  Il modulo **non installa** la dipendenza da solo: la propone. **Non c'è una soglia** di copertura che fa fallire
  qualcosa: una percentuale si ottimizza contro, un file critico senza test no (come per shadscan: «mai
  ottimizzare lo score», regola già in memoria del progetto).

### 3. L'ordine — tre fasce, regole fisse

| Fascia | Cosa ci va |
|---|---|
| **before-release** | app-security `found` (segreti, autorizzazione, dipendenze vulnerabili, dati esposti); compliance `H`; registry-intake bloccante; observability `errors` mancante o mai scelto (un'app online senza tracciamento degli errori: il check gira con `--all` quando `stack.observability` è vuoto); Server Action / route che scrive senza test **e** con un risultato di autorizzazione sullo stesso file |
| **with-features** | tutto ciò che ha un file: violazioni `HIGH`/`MEDIUM` delle ricette, shadscan `fix`, vercel-doctor high/medium, compliance `M`, file critici non testati, launch-audit `missing` |
| **later** | violazioni `LOW`, shadscan `verify`/`decide`, vercel-doctor low, candidati di promote-component, observability `logs`/`uptime` mancanti |
| *not checked* (a parte) | ogni fonte o controllo che non ha potuto vedere: si elenca, non si ordina, non vale mai «ok» |

**Dentro la fascia** l'ordine è: prima i file **toccati più spesso** negli ultimi 90 giorni
(`git log --since=90.days --name-only`), perché «insieme alle funzioni» vuol dire proprio che quel file verrà
riaperto; a parità, l'ordine della fonte (app-security per primo, come dice la sua regola). Senza git, l'ordine è
quello della fonte.

La tabella vive nello script come dato (`BAND_RULES`), testata riga per riga; il reference la ripete per l'utente.

### 4. dev-flow — quando lo propone

- **`debt_line(meta, root)`** in `show_state.py`, accanto a `verification_line` e `observability_line`, dalla fase
  `deployed`:
  - nessun `debt_audit` → «Debt: never audited — dev-flow debt audit»;
  - `debt_audit.last_run_at` più vecchio dell'ultimo cambio materiale → «Debt: last audit older than <skill> on
    <data> — re-run»;
  - altrimenti, se `before_release > 0` → «Debt: N to fix before the next release (docs/debt/debt-audit.md)».
- La riga `deployed` della tabella di routing (`PHASE_NEXT_BY_STACK`, tutte e quattro le topologie) nomina il debt
  audit come primo passo del ciclo di manutenzione; `sync_routing_table.py` la porta in SKILL.md.
- **Dai risultati alle task**: dopo il report, l'agente propone la fascia *before-release* come task. Entrano in
  `tasks.md` con `prd-to-tasks` in modalità revisione, citando `debt:<id>` come giustificazione — una terza fonte
  accettata accanto a una storia del PRD e a una riga di `## Scope changes`. Con Linear attivo, la sync esistente
  le porta lì. Niente entra senza un sì dell'utente.

### 5. Contratto

`meta.json#debt_audit`:

```json
{ "last_run_at": "2026-10-18T12:00:00Z",
  "bands": { "before_release": 2, "with_features": 11, "later": 7 },
  "to_confirm": 4,
  "not_checked": ["coverage", "shadscan"],
  "sources": { "app-security": "fresh", "shadscan": "stale", "vercel-doctor": "missing" },
  "new": 3, "closed": 1, "report": "docs/debt/debt-audit.md" }
```

Scritto con `meta_io` (lock), come fa `verify_map.py`, non a mano. Una voce di history `{skill: "dev-flow",
action: "debt-audit"}`. Mai `phase`.

### 6. Pulizia dei conteggi

`compliance-audit`, `launch-audit`, `vercel-doctor`, `shadscan`, `README.md` e `AUDIT.md` dicono «tre/quattro/
quarto/terzo gate»: diventano «cinque gate», con lo stesso elenco di `policies.md`.

## Obiettivi, non obiettivi, anti-obiettivi

- **Obiettivo**: chi riapre un progetto online sa in un minuto cosa fare prima del prossimo rilascio, e sa cosa
  l'audit **non** ha potuto vedere.
- **Non obiettivi**: eseguire le CLI esterne dallo script (rete, tempo; le esegue l'agente quando sono stale);
  rifare il lavoro delle ricette in prosa; un punteggio complessivo; una soglia di copertura; audit dei diff (è
  `spec-review`).
- **Anti-obiettivi**: un elenco di 200 righe senza ordine (sarebbe la situazione di oggi, solo concatenata); un «ok»
  dove una fonte non ha girato; risultati accettati che ricompaiono come nuovi ogni giro.

## Vincoli

- Stdlib, Python 3.9+ (la CI prova 3.9), nessuna dipendenza.
- Non modifica il codice del progetto; scrive solo `docs/debt/`, `.workflow/debt/` e `meta.json` (via `meta_io`).
- Funziona senza le skill sorelle installate (ogni fonte assente è *not checked*).
- `surfaces.py` decide web / mobile / agent, come negli altri controlli.
- Codice, testi delle skill e report generato in inglese; il riassunto all'utente in chat nella sua lingua.

## Lasciato a chi costruisce

- I nomi interni delle funzioni e la forma esatta del markdown del report.
- Come riconoscere «scrive» in una route (euristica documentata e testata).
- Il formato con cui `registry-intake check` e `promote-component` vengono letti (testo e tabella): un parser
  piccolo e tollerante, con *not checked* se il formato non torna.

## Prova

Su una copia di fit-coach (come per osservabilità e verifica): `debt_audit.py collect` produce un report con le tre
fasce, almeno un file critico non testato vero oppure la conferma che ognuno ha un test, e la copertura *not
checked* con il comando giusto; poi, con `@vitest/coverage-v8` aggiunto solo nella copia, la copertura letta dal
`coverage-summary.json` vero.

## Decisioni prese dopo il builder check (mie)

1. Gli scanner danno segnali: un risultato fresco è «da confermare» finché l'agente non scrive il verdetto in
   `.workflow/debt/reviewed.json`; `debt_line` conta solo i confermati.
2. Le accettazioni dei gate valgono per controllo, quelle di `reviewed.json` per risultato; `compliance.flagged`
   resta aperto.
3. vercel-doctor: una riga per severità dai conteggi.
4. app-security si riesegue (timeout esterno 1800 s, `--skip` per l'offline).
5. Osservabilità mai scelta su un'app online = `errors` mancante, *before-release*.
6. `collect` gira a ogni fase; la proposta automatica solo da `deployed`.
7. Gli e2e contano quando visitano la pagina che importa l'azione.
8. Report in inglese, riassunto in chat nella lingua dell'utente.
