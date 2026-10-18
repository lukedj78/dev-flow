# Criteri di modifica dello scope — anche nel percorso diretto — 2026-10-18

Terzo punto della roadmap uscita dal confronto con *The Founder's Playbook*
(`2026-10-17-founder-intelligence-design.md`, §Confronto e roadmap, punto 3, verbatim):

> **Criteri di modifica dello scope** (S): una riga nel PRD (*quale prova giustifica una funzione nuova*) e un
> passo breve che mette alla prova una richiesta prima che `prd-to-tasks` riparta. Founder Intelligence li produce
> già; serve che esistano anche nel percorso diretto.

## Fatti verificati nel repo (2026-10-18)

- **Percorso founder: c'è quasi tutto.** Il Playbook §12 contiene «la prova che giustificherebbe una funzione
  nuova» (`founder-intelligence/references/stages.md:86-92`, `assets/founder-playbook.md:52-55`). Le decisioni del
  §18 arrivano al PRD intatte, un conflitto si segnala e torna a `founder-intelligence`, e una revisione richiede una
  nuova approvazione del founder (`dev-flow/references/policies.md:11`).
- **Percorso diretto: niente.**
  - Il template del PRD (`prd-from-idea/SKILL.md:240-275`) ha già:
    - 3–5 storie MVP;
    - «Post-MVP»;
    - `## Non-goals`.

    Non ha nessuna riga su cosa giustifica aggiungere qualcosa.
  - La modalità revise di `prd-from-idea` (`:21`) modifica il PRD sul posto, senza criteri e senza traccia.
  - La modalità revise di `prd-to-tasks` (`:21`) aggiunge e toglie task senza dire perché.
- **`spec-review`** trova lo scope creep nel codice e lo conta in `spec_findings.scope_creep` (`:173`, `:217`), ma il
  risultato non va da nessuna parte: nessuno chiede se va cambiato il PRD o tolto il codice.
- **`linear-scrum`** non dice niente sulle issue aggiunte a metà sprint che non sono nel PRD.
- **Un cambio di scope non lascia traccia**: niente nel PRD, niente in `meta.json`.

## Intento

Quando arriva una richiesta che il PRD non contiene (una funzione nuova, un'issue a metà sprint, un pezzo di codice
che `spec-review` segnala come fuori scope), la richiesta passa da un controllo breve **prima** di diventare lavoro.
Il controllo la confronta con un criterio scritto in anticipo nel PRD. Decide l'utente, e la decisione resta scritta
nel PRD.

Il punto non è dire di no. È che «il codice costa poco» non basta come motivo: è la stessa regola che
`founder-intelligence` applica già (stage 9).

## Obiettivi

1. Ogni PRD nuovo ha una sezione `## Scope rules`:
   - quale prova giustifica una funzione nuova;
   - cosa non entra comunque prima del lancio.

   Nel percorso founder, la sezione è copiata dal Playbook §12 senza modifiche.
2. Un controllo dello scope, breve, con quattro esiti, usato da tutti i punti in cui una richiesta nuova entra:
   - richiesta in chat;
   - modalità revise di `prd-from-idea` e di `prd-to-tasks`;
   - risultato `scope_creep` di `spec-review`;
   - issue nuova in `linear-scrum`.
3. Ogni decisione è registrata, una sola volta, in una sezione `## Scope changes` del PRD, più una voce nella history.
4. Togliere qualcosa (descope) ha una procedura:
   - la storia passa a Post-MVP o a Non-goals;
   - i task collegati sono marcati come tagliati con il motivo, non cancellati;
   - le issue Linear tornano nel backlog.

## Non obiettivi

- Un processo di change management formale, con comitati e moduli.
- Bloccare il lavoro. Il controllo propone, l'utente decide, e una richiesta urgente passa subito se l'utente lo dice:
  in quel caso si registra solo il motivo.
- Cambiare il percorso founder, che ha già le sue regole: qui si riusano.
- Rifare il PRD dei progetti esistenti. La sezione si aggiunge quando serve, non con una migrazione.

## Anti-obiettivi

- Un controllo che l'utente salta perché è lungo. Deve stare in cinque righe.
- Una seconda copia della decisione in `meta.json` che invecchia per conto suo. La memoria del 2026-10-17 lo ha
  misurato: le copie doppie diventano false.
- Un agente che decide da solo di aggiungere o togliere una funzione.
- Un «no» meccanico a una richiesta che soddisfa il criterio scritto.

## Il design

### 1. La sezione `## Scope rules` nel PRD

Nel template di `prd-from-idea`, subito dopo `## Non-goals`:

```markdown
## Scope rules

- **A new feature enters the MVP when**: <the evidence, e.g. "three test users hit the same wall", "a story
  cannot be completed without it", "the activation metric shows the drop-off here">
- **Not before launch, whatever the evidence**: <e.g. "a second payment provider", "an admin panel">
- **Who decides**: <the user, or the named owner>
```

- Nell'intervista basta una domanda in più, accanto alla 7 («cosa è esplicitamente fuori scope?»): «quale prova ti
  farebbe aggiungere una funzione prima del lancio?». Se l'utente non lo sa, propongo un default e lo segno come mia
  proposta.
- Nel percorso founder la sezione non si chiede: si copia dal Playbook §12. Cambiarla vuol dire tornare a
  `founder-intelligence`, come dice già la policy.

### 2. Il controllo dello scope (`prd-from-idea/references/scope-check.md`)

Una richiesta che il PRD non contiene passa da quattro domande, ognuna con risposta in una riga:

1. **È già nel PRD?** Se è in una storia, in un'acceptance o in un task, non c'è niente da decidere.
2. **Contraddice un Non-goal o la riga «not before launch»?** Se sì, l'esito proposto è rifiutare, a meno che
   l'utente cambi quella riga di proposito.
3. **Soddisfa il criterio scritto in `## Scope rules`?** Quale prova c'è, e da dove viene.
4. **Cosa sposta?** Quale storia o quale task slitta per farle posto.

Gli esiti possibili sono quattro, e l'agente ne propone uno:

| Esito | Effetto |
|---|---|
| **add** | una nuova storia o acceptance nel PRD, poi `prd-to-tasks` in modalità revise |
| **defer** | entra in Post-MVP, con la prova che manca |
| **reject** | entra in Non-goals, con il motivo |
| **experiment** | una prova limitata, con scope, obiettivo e criterio di accettazione: la stessa forma di `approved_experiment` di `founder-intelligence` |

L'utente decide. Se dice «fallo e basta», l'esito è **add** con il suo motivo registrato tale e quale. Il controllo
non diventa mai un ostacolo.

Nel percorso founder, una richiesta che tocca una decisione bloccata del §18 non passa da qui: torna a
`founder-intelligence`, come già previsto.

### 3. La registrazione: `## Scope changes` nel PRD

In fondo al PRD, una riga per decisione:

```markdown
## Scope changes

| Date | Request | Decision | Evidence / reason | Decided by |
|---|---|---|---|---|
| 2026-10-18 | export to CSV | defer | one request, criterion asks for three | user |
```

- È l'unico posto dove la decisione è scritta.
- `meta.json#history` riceve una voce (`skill: prd-from-idea`, con l'esito in `outputs`). Nessun campo nuovo nel
  contratto, perché non serve un secondo registro.

### 4. Chi lo usa

- **dev-flow.** Quando l'utente chiede una funzione nuova su un progetto già oltre `prd_drafted`, propone il
  controllo prima di qualsiasi skill che costruisce.
- **`prd-from-idea`, modalità revise.** Un cambiamento che aggiunge o toglie storie passa dal controllo e scrive la
  riga in `## Scope changes`.
- **`prd-to-tasks`, modalità revise.** Un task nuovo cita la storia del PRD o la riga di `## Scope changes` che lo
  giustifica. Un task tagliato resta nel file, marcato `~~…~~ cut <data>: <motivo>`.
- **`spec-review`.** Ogni risultato `scope_creep` è instradato verso una scelta:
  - o il PRD cambia, e allora passa dal controllo;
  - o il codice si toglie.

  `spec-review` non decide quale delle due.
- **`linear-scrum`.** Un'issue creata a metà sprint che non corrisponde a una storia passa dal controllo prima di
  entrare nello sprint. Le issue di una storia tagliata tornano nel backlog con il motivo nel commento.

### 5. Un controllo leggero in `show_state.py`

Per i progetti oltre `prd_drafted`, con un `PRD.md` senza `## Scope rules`, `show_state.py` lo segnala una volta,
come nota e non come blocco, proponendo di aggiungere la sezione con `prd-from-idea` in modalità revise. Nel percorso
founder la nota dice di copiarla dal Playbook §12.

## Test

- `show_state.py`, con fixture:
  - un PRD senza la sezione mostra la nota;
  - un PRD con la sezione non la mostra;
  - un progetto prima di `prd_drafted` non la mostra.
- Il lint e le suite esistenti.
- Una prova a mano sul controllo, con una richiesta finta su un PRD di fixture: le quattro domande, l'esito
  proposto, la riga scritta in `## Scope changes` e la voce nella history.

## Lasciato a chi costruisce

- Le parole esatte della domanda nell'intervista e il default proposto quando l'utente non ha un criterio.
- Il formato esatto della voce nella history.

## Scelte mie, da controllare

- La decisione vive solo nel PRD (`## Scope changes`) più la history, senza un campo `meta.json#scope`, per non
  avere due registri.
- Il controllo vive in `prd-from-idea`, che possiede il PRD, e non in una skill nuova.
- Nessun blocco: né `set-phase` né altri gate rifiutano un PRD senza `## Scope rules`. Solo una nota.
- L'esito `experiment` riusa la forma di `approved_experiment` di `founder-intelligence` (scope, obiettivo, vincoli,
  accettazione).
- I task tagliati restano visibili, barrati, invece di essere cancellati.
