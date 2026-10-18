# `founder-intelligence` — decidere se vale la pena costruire, prima di come — 2026-10-17

dev-flow oggi sa portare un'idea fino al deploy, ma presume che l'idea valga la pena. Per un
prototipo, un refactor o uno strumento interno è giusto così. Per un prodotto commerciale nuovo
no: la domanda più costosa da sbagliare, *questo problema esiste ed è abbastanza grave da
pagarci?*, non ha nessuna skill che la ponga. Questo documento decide come aggiungere quella
domanda senza appesantire il percorso diretto.

Fonte metodologica: *The Founder's Playbook: Building an AI-Native Startup*, Anthropic, maggio
2026 (34 pagine, letto per intero il 2026-10-17). Ne prendiamo il metodo dello stadio Idea
(cap. 3) e una parte dello stadio MVP (cap. 4: il documento di scope e la misurazione decisa
prima del lancio). Non riproduciamo il testo. Le altre parti del PDF (lancio, crescita) sono
oggetto di un confronto separato con le skill esistenti, in fondo a questo documento.

## Cosa dice il PDF che conta qui

- Lo stadio Idea è **validazione orientata alla ricerca**: prove che il problema esiste e che la
  soluzione lo risolve, *prima* di impegnare risorse nel costruire.
- L'uscita è il **problem-solution fit**, con tre domande a cui rispondere sì: il problema è
  reale e specifico (chi, quanto spesso, quanto grave, cosa fa oggi); la soluzione risponde al
  problema emerso dalla validazione, non a quello immaginato; c'è abbastanza segnale da
  giustificare un MVP.
- La prova principale sono **conversazioni con persone reali**. Un prototipo serve a farle
  meglio, non le sostituisce.
- Tre trappole: scambiare il costruire per il validare; scalare l'esecuzione prima della
  validazione; perdere l'obiettività, perché un'AI a cui chiedi conferme le trova sempre. Il
  rimedio è usare la stessa AI come avvocato del diavolo, in ogni stadio.
- Esercizi concreti che diventano passi della skill: rendere l'ipotesi testabile (chi, quanto,
  perché); mappare i concorrenti per livello e argomentare perché ciascuno potrebbe vincere;
  estrarre le lamentele ricorrenti dalle recensioni dei concorrenti; TAM/SAM/SOM con le
  assunzioni messe sotto pressione; tre tendenze esterne, vento a favore o contro; domande di
  intervista sul passato, non sul futuro; ogni cinque interviste, due liste (a favore, contro) e
  un controllo sull'asimmetria; le tre assunzioni da cui dipende la soluzione; un prototipo
  minimo davanti a cinque persone del profilo giusto.
- Dallo stadio MVP: un documento di scope (cosa fa, cosa deliberatamente non fa, quale prova
  giustifica aggiungere qualcosa) e le metriche decise **prima** del lancio (attivazione,
  ritenzione, obiettivi a 7 e 30 giorni, cosa sarebbe un falso positivo).

## Intento

Una skill opzionale che trasforma un'idea grezza in un **Founder's Playbook** basato su prove,
criticato, e approvato esplicitamente dal founder. Il Playbook approvato diventa l'ingresso di
`prd-from-idea`. Founder Intelligence decide *cosa vale la pena costruire e perché*; dev-flow
decide *come*.

## Obiettivi

1. **Due porte d'ingresso alternative** (decisione dell'utente, 2026-10-17):
   - **Founder Intelligence** per progetti grandi e commerciali, con mercato non chiaro. Prende
     il posto di "prima di costruire" (l'inventario) e passa a `prd-from-idea`.
   - **Percorso diretto** per prototipi, refactor, strumenti interni, cose già decise: identico a
     oggi, inventario e poi PRD.
2. **Invocabile più tardi** su un progetto già in sviluppo, senza ripartire da capo: i risultati
   tornano a dev-flow come proposte di revisione del PRD.
3. **Prove separate dalle ipotesi**, sempre: ogni affermazione rilevante ha una classe (vedi
   §Prove) e, se è un fatto, una fonte.
4. **Approvazione del founder resa una regola meccanica**, non una promessa del prompt.
5. **Riprendibile**: tutto lo stato sta in file versionabili; una sessione interrotta riparte da
   lì, senza rifare domande già fatte.

## Non obiettivi

- Generare il PRD, le task, l'architettura o il codice: restano a `prd-from-idea`,
  `prd-to-tasks` e alle skill di build.
- Coprire gli stadi Launch e Scale del PDF (operazioni aziendali, assunzioni, investitori).
- Un nuovo orchestratore, un nuovo sistema di configurazione, nuove dipendenze.
- Ricerca di mercato automatica per lavoro tecnico.

## Anti-obiettivi (fallimento anche se "funziona")

- Un business plan generico e lungo, prodotto da tre righe di input.
- Una skill che conferma l'idea del founder invece di cercarne i punti deboli.
- Precisione inventata: TAM, prezzi, conversioni presentati come fatti senza fonte né calcolo.
- Interviste, clienti, sondaggi o impegni d'acquisto simulati.
- Un percorso diretto che diventa più lento o chiede cose nuove.
- Un punteggio numerico presentato come prova di fattibilità commerciale.

## Vincoli

- Formato e convenzioni delle skill del repo: `SKILL.md` con frontmatter (`name`, descrizione
  ≤ 1024 caratteri con `Triggers` e `Not for:`), `references/`, `assets/`, script Python
  stdlib, Python ≥ 3.9.
- Tocca il contratto: `contracts.md` è vendorizzato in 41 copie identiche (lint), e la skill ne
  porta una sua; scrive `meta.json`, quindi vendorizza anche `meta_io.py`.
- Aggiunte al contratto solo additive: `contract_version` resta 1.
- Codice in inglese; il Playbook nella lingua dell'utente.

## Il design

### 1. Dove entra nel flusso

```
              ┌─ commerciale, mercato incerto ─► founder-intelligence ─► (approvato) ─┐
idea ─► dev-flow                                                                       ├─► prd-from-idea ─► …
              └─ prototipo / refactor / interno / già deciso ─► inventario ───────────┘
```

- In fase `empty` / `idea_captured`, dev-flow propone Founder Intelligence **in una riga** quando
  vede i segnali (prodotto da vendere, utenti esterni paganti, mercato o concorrenza non chiari,
  l'utente parla di startup, clienti, prezzi). Il default resta il percorso diretto; l'utente
  sceglie.
- Una volta avviata, il progetto ha il campo `meta.json#founder` e dev-flow propone
  Founder Intelligence come passo successivo finché c'è una decisione da prendere.
- **Invocazione tardiva** (fase ≥ `prd_drafted`): la skill legge PROJECT.md, PRD.md, tasks e il
  codice come contesto; produce o aggiorna il Playbook in modalità `existing`; il passaggio a
  dev-flow è un file di proposte di revisione (§6), non un nuovo ciclo.

### 2. La skill

```
founder-intelligence/
  SKILL.md                         ~150–200 righe: quando usarla, le regole sulle prove, il percorso, l'approvazione, il passaggio
  references/
    stages.md                      gli stadi, caricati uno alla volta
    evidence.md                    classi di prova, formato delle fonti, regole su TAM e stime
    interviews.md                  kit di intervista e sintesi ogni cinque interviste
    contracts.md                   copia vendorizzata
  assets/
    founder-playbook.md            modello del Playbook (le sezioni non pertinenti si omettono)
  scripts/
    founder.py                     unico scrittore di meta.json#founder
    meta_io.py                     copia vendorizzata
    test_founder.py
```

**Gli stadi** (in `stages.md`), adattati dal prompt utente e dal PDF. Si eseguono in ordine ma si
torna indietro quando un risultato cambia la direzione; si rifà solo lo stadio toccato.

| # | Stadio | Cosa produce | Note |
|---|---|---|---|
| 1 | Intake | idea, problema, utenti sospetti, soluzione, differenziazione, vincoli, cosa manca | parte da tre righe; nessun questionario iniziale |
| 2 | Ipotesi testabile | il problema riscritto come ipotesi verificabile (chi, quanto spesso, quanto grave, cosa fa oggi) | esercizio del PDF |
| 3 | Avvocato del diavolo | le ragioni più forti contro l'idea, cercate attivamente | prima delle interviste, per non fare domande che cercano conferme |
| 4 | Intervista al founder | motivazioni, successo, vantaggi, accesso ai clienti, budget, tempo, rischio, monetizzazione, vincoli | lotti di 3–4 domande; mai chiedere ciò che la ricerca può stabilire |
| 5 | Mercato e concorrenti | concorrenti per livello (diretti, indiretti, sostituti, acquirenti potenziali), prezzi osservati, lamentele dalle recensioni, tendenze esterne, stime di mercato con metodo | ogni fatto con fonte; perché ciascun concorrente potrebbe vincere |
| 6 | Scoperta del cliente | profilo preciso di chi intervistare, dove trovarlo, domande sul passato, kit di intervista | la skill **non** intervista nessuno: prepara, poi sintetizza le note che il founder porta |
| 7 | Posizionamento | problema, segmento iniziale, proposta di valore, perché cambierebbero, difendibilità, perché potrebbe fallire | include la contro-analisi e le alternative: restringere, cambiare mercato, rimandare, abbandonare |
| 8 | Modello di business | acquirente, prezzo, ricavi, costi (hosting, inferenza AI, API, supporto), canali, scenari e sensibilità | ogni numero con la sua classe di prova |
| 9 | Scope dell'MVP | percorsi principali, capacità essenziali, esclusioni esplicite, criteri per aggiungere funzioni, metriche decise prima del lancio, l'esperimento più economico | il "documento di scope" del PDF; non è un PRD |
| 10 | Fattibilità | vincoli tecnici, dati, integrazioni, privacy e regolazione, costi operativi, lock-in, cosa serve a uno specialista; **cosa esiste già da riusare** (passi 1–4 di `before-you-build.md`, `research.py repos`) | sostituisce l'inventario: da qui esce il verdetto |
| 11 | Go-to-market | primo segmento, come trovare i primi clienti, canali, messaggio, esperimenti su prezzo e landing page, metriche | pubblicare non è distribuire |
| 12 | Validazione e rischi | per ogni ipotesi critica: importanza, prove, fiducia, test più economico, criterio di successo, risultato, prossima azione; registro dei rischi | test fatti separati da test proposti |
| 13 | Sintesi | contraddizioni risolte, affermazioni ricontrollate, argomenti più forti contro, decisioni richieste al founder | poi lo stato di prontezza |

**Interazione** (in `SKILL.md`): prima ricerca, poi domande; domande in lotti piccoli, con il
perché quando conta; ogni risposta e ogni decisione annotata nel Playbook (§Domande e
decisioni), così non si richiede due volte; conclusioni intermedie quando cambiano la
direzione; se il founder cambia una decisione si aggiornano solo le sezioni toccate.

**Senza strumenti web** la skill lo dichiara in testa al Playbook e marca tutto come analisi
preliminare non verificata. Usa `research.py` (repo, Reddit, HN, paper, lettura pagine) e gli
strumenti di ricerca web della sessione, quando ci sono.

### 3. Le prove

Ogni affermazione rilevante nel Playbook porta una di queste classi:

| Classe | Significato | Esempio |
|---|---|---|
| `fonte` | fatto verificato, con URL e data di consultazione | il prezzo pubblico di un concorrente |
| `founder` | detto dal founder | "ho accesso a 40 studi legali" |
| `intervista` | da note di interviste reali portate dal founder | "3 su 5 riconciliano a mano" |
| `stima` | calcolo esplicito su input dichiarati | SOM = segmento × penetrazione assunta |
| `ipotesi` | da verificare | "pagherebbero 50 €/mese" |

Regole: niente TAM/SAM/SOM, quote di mercato o ricavi senza metodo e input visibili; un dato
che non si trova si dichiara mancante; nessuna citazione o pagina attribuita a una fonte senza
averla letta. Il registro delle fonti sta in `.workflow/founder/sources.md` (URL, data, cosa
sostiene, quali decisioni ne dipendono).

### 4. Gli artefatti

```
.workflow/founder/
  founder-playbook.md      il Playbook (unico documento strategico)
  sources.md               registro delle fonti
  interviews/NN-<chi>.md   note di interviste reali, scritte o incollate dal founder
  handoff.md               solo in modalità existing: proposte di revisione per dev-flow
```

Il Playbook segue `assets/founder-playbook.md`. Le sezioni sono quelle del prompt utente
(sommario, idea e obiettivi, problema, utenti, scoperta, mercato, fonti, opportunità,
posizionamento, modello di business, scenari, prodotto e confini dell'MVP, fattibilità, privacy
e regolazione, go-to-market, validazione, rischi, decisioni, assunzioni, approvazione), più
**Domande e decisioni** (aperte, risposte, decisioni con data) e **Registro delle revisioni**.
Le sezioni che non si applicano si omettono, non si riempiono.

### 5. Il contratto: `meta.json#founder`

Nuovo campo opzionale, scritto solo da `founder.py`:

```json
"founder": {
  "mode": "new | existing",
  "research": "in_progress | complete",
  "decision": "pending | approved | approved_experiment | revise | stop | bypassed",
  "playbook": ".workflow/founder/founder-playbook.md",
  "version": 3,
  "playbook_sha256": "…",
  "open_hypotheses": ["H2", "H5"],
  "approved_at": "…", "approved_by_user": true, "approval_quote": "…",
  "experiment": { "scope": "…", "objective": "…", "constraints": "…", "acceptance": "…" },
  "reason": "…"
}
```

Due assi separati invece di una scala unica, perché un Playbook può essere approvato con ipotesi
ancora aperte, e una scala non ha un posto per quel caso. Gli stati del prompt utente restano
come **etichette derivate**, stampate da `show_state.py` e da `founder.py status`:

| Etichetta | Quando |
|---|---|
| `RESEARCH_COMPLETE` | `research = complete` |
| `NEEDS_VALIDATION` | `open_hypotheses` non vuoto (si somma alle altre) |
| `READY_FOR_FOUNDER_APPROVAL` | `research = complete` e `decision = pending` |
| `APPROVED_FOR_DEVFLOW` | `decision = approved` o `approved_experiment` |
| `REVISE_OR_STOP` | `decision = revise` o `stop` |

`founder.py`:

- `start <root> --mode new|existing` crea il campo e la cartella dal modello.
- `status <root>` stampa etichette, ipotesi aperte, e se il Playbook è cambiato dopo l'approvazione.
- `record <root> --research complete|in_progress --open H2 H5` aggiorna lo stato della ricerca.
- `approve <root> --quote "<parole del founder>" [--experiment-scope … --experiment-objective … …]`:
  registra versione, sha256 del Playbook, citazione; **richiede** una citazione non vuota.
  Con `--experiment-*` la decisione è `approved_experiment`.
- `decide <root> revise|stop --reason "…"` registra il rifiuto o la revisione, con il motivo.
- `bypass <root> --reason "…"` abbandona Founder Intelligence e torna al percorso diretto.
- Ogni scrittura passa da `meta_io` (atomica, con lock) e aggiunge una voce alla history.

### 6. L'approvazione come gate

Nuovo `dev-flow/scripts/founder_gate.py`, chiamato da `gate_refusal()` in `update_meta.py` come
gli altri gate. Si applica **solo se `meta.json#founder` esiste**: un progetto diretto non ha
il campo, quindi per lui non cambia niente.

Rifiuta il passaggio a `prd_drafted` (sia `set-phase` sia `append-history --phase-after`)
quando:

- `decision` non è `approved`, `approved_experiment` o `bypassed`;
- `approved` senza `approved_by_user` e `approval_quote`;
- lo sha256 del Playbook non corrisponde a quello approvato: il Playbook è cambiato dopo
  l'approvazione, quindi serve una nuova approvazione (`founder.py approve`), come per gli
  snapshot di registry-intake;
- `bypassed` senza motivo.

Ogni rifiuto dice il comando che lo risolve. In modalità `existing` il gate non interviene:
il passaggio a `prd_drafted` è già avvenuto.

**Esecuzione autonoma** (nessuno da intervistare): la skill può arrivare a
`READY_FOR_FOUNDER_APPROVAL` ma non può approvare; il gate lo garantisce, perché l'approvazione
richiede una citazione del founder.

### 7. L'inventario

Il gate dell'inventario non cambia. Founder Intelligence lo soddisfa da sola: allo stadio 10
esegue i passi di `before-you-build.md` (in casa, strumenti già pagati, ecosistema Claude,
esterno) dentro la propria analisi, e all'approvazione chiama
`inventory.py record --verdict <have-it|adapts|halfway|build> --searched <canali usati>
--summary <rimando al Playbook>`. Così il contratto contiene il verdetto come in ogni altro
progetto, e una sola funzione lo scrive.

Con `bypass`, il percorso diretto riparte dall'inventario normale.

### 8. Il passaggio a dev-flow

**Progetto nuovo** (`decision` approvata): `prd-from-idea` riceve tre modifiche piccole.

1. Allo Step 1 legge `meta.json#founder`; se approvato, legge il Playbook.
2. Allo Step 3 non rifà le domande a cui il Playbook risponde già (pubblico, problema,
   alternative, wedge, successo); le scrive con la fonte `Playbook §…`. Restano le domande
   tecniche (piattaforma, UI, form, eve).
3. PROJECT.md e PRD.md riportano le **decisioni bloccate** (segmento, scope ed esclusioni
   dell'MVP, metriche di successo, vincoli) con il rimando al Playbook, e le ipotesi aperte in
   §Open questions. Con `approved_experiment`, il PRD è limitato allo scope dell'esperimento.

**Contraddizioni a valle**: se una skill successiva (`prd-from-idea`, `spec-review`, la build)
trova un vincolo che invalida una decisione bloccata, la segnala e propone di tornare a Founder
Intelligence; non la cambia in silenzio. Si aggiunge una riga in `dev-flow/references/policies.md`.

**Progetto esistente**: `handoff.md` elenca le proposte (cosa cambia nel PRD, nello scope,
nelle metriche, con il motivo e la fonte). L'utente decide; dev-flow le applica con le skill
esistenti (`prd-from-idea` sul PRD, `prd-to-tasks` per le task nuove).

### 9. Modifiche alle parti esistenti

| File | Modifica |
|---|---|
| `dev-flow/scripts/show_state.py` | `COMMON_NEXT` per `empty`/`idea_captured` menziona l'alternativa; se `founder` esiste e la decisione è aperta, il passo successivo è `founder-intelligence`; stampa le etichette |
| `dev-flow/SKILL.md` | Step 0: le due porte e i segnali, in poche righe; tabella di routing rigenerata da `sync_routing_table.py` |
| `dev-flow/scripts/update_meta.py` + `founder_gate.py` | il gate (§6) |
| `dev-flow/references/contracts.md` (+ 41 copie) | campo `founder`, cartella `.workflow/founder/`, e la documentazione di `inventory` che oggi manca |
| `dev-flow/references/policies.md` | la regola sulle contraddizioni a valle |
| `prd-from-idea/SKILL.md` | §8 |
| registrazione | `install.sh`/`uninstall.sh`, `TAXONOMY` in `build_skills_registry.py`, catalogo README, conteggi dichiarati, mappa delle skill, CHANGELOG |
| `contract-package` | una riga di documentazione sul campo `founder`; non esegue gate per scelta |

### 10. Test

**Meccanici** (unittest, in CI):

- `founder.py`: ogni sottocomando, la citazione obbligatoria, lo sha256, la history, l'inventario
  scritto all'approvazione, la scrittura confinata nel progetto.
- `founder_gate.py`: assente → passa; `pending` → rifiuta `prd_drafted`; approvato → passa;
  Playbook modificato dopo l'approvazione → rifiuta; `bypassed` con motivo → passa;
  `approved_experiment` → passa; modalità `existing` → non interviene; tutte e due le porte
  (`set-phase`, `append-history`).
- `show_state.py`: le etichette e il routing nei tre casi (assente, aperto, approvato).
- **Regressione del percorso diretto (scenario B)**: tutti i test esistenti invariati, più un
  progetto senza `founder` che attraversa ogni gate come prima.

**Comportamentali** (eval di compliance, `evals/compliance/gates/`), per gli scenari che solo
un agente può dimostrare:

- **A, idea grezza**: parte da tre righe, fa ricerca e domande, scrive il Playbook, **non**
  arriva a `prd_drafted` senza approvazione.
- **C/F, prove insufficienti e strumenti assenti**: nessuna validazione dichiarata senza prove,
  limiti dichiarati, ipotesi distinte dai fatti.
- **D, il founder rifiuta**: decisione e motivo registrati, nessuna forzatura.
- **E, invocazione tardiva**: usa gli artefatti esistenti, produce `handoff.md`, non riparte da
  capo.

Costo indicativo: 1–2 USD equivalenti a sessione su Sonnet, nella quota dell'abbonamento. Le
eval si scrivono con i selftest; quante sessioni lanciare lo decide l'utente.

### 11. Decisioni di dettaglio (dalla revisione del documento)

Risposte alle domande di un revisore che ha letto il documento senza la conversazione; tutte
scelte mie, da controllare.

- **Chi scrive l'inventario.** `founder.py` non chiama gli script di dev-flow e non li
  vendorizza. Come fanno già altre skill (`linear-scrum`, `registry-intake`, `rn-add-screen`…
  con `update_meta.py`), `SKILL.md` fa eseguire all'agente `dev-flow/scripts/inventory.py
  record` allo stadio 10, con verdetto e canali scelti lì. `founder.py approve` **rifiuta** se
  `meta.json#inventory` non ha un verdetto valido (diverso da `skipped`): così "l'inventario c'è
  all'approvazione" è un test di unità, e lo scrittore dell'inventario resta uno. Se un verdetto
  era già registrato prima, lo stadio 10 lo riscrive (è il comportamento normale di `record`).
  Vale anche per `approved_experiment`.
- **Transizioni ammesse.**
  - `start` su un progetto che ha già il campo non fa niente e stampa lo stato; su un progetto
    `stop` o `bypassed` lo riapre (`decision = pending`), con una voce nella history.
  - `approve` richiede `research = complete`.
  - Da `revise` si torna a lavorare e si riapprova; da `approved` si può passare a `revise`
    (il gate torna a rifiutare finché non c'è una nuova approvazione).
  - `stop` chiude: `show_state` non propone più Founder Intelligence né il PRD, e dice che il
    founder ha fermato il progetto e come riaprirlo.
  - `bypassed` riporta al percorso diretto: `show_state` propone l'inventario come oggi.
- **Cosa copre lo sha256.** Tutto il file del Playbook. Prima di calcolarlo, `approve` scrive lui
  stesso nella sezione *Approvazione* (tra due marcatori) versione, data e citazione; la voce del
  registro delle revisioni la scrive l'agente prima di `approve`. Ogni modifica successiva, anche
  piccola, chiede una nuova approvazione: costa un comando ed evita di decidere quali modifiche
  "contano".
- **Modalità `existing`.** La decisione riguarda le proposte di `handoff.md`: il founder le
  discute in chat, l'agente segna in `handoff.md` quelle accettate e rifiutate, e `approve`
  registra la citazione. Il gate non interviene, ma `show_state` propone Founder Intelligence
  finché la decisione è aperta, e dopo l'approvazione propone di applicare le proposte accettate
  con `prd-from-idea` / `prd-to-tasks`.
- **Il confronto con le altre skill** (sezione finale) non fa parte di questa costruzione: è una
  valutazione per lavori separati.
- **Progetto diretto = campo assente.** `bypass` esiste solo per chi ha avviato Founder
  Intelligence; un progetto che non l'ha mai avviata non ha il campo e attraversa ogni gate come
  oggi. È la base dei test di regressione.
- `contract-package` non esegue gate per scelta (lo dice il suo README): serve solo una riga di
  documentazione sul campo nuovo.

## Lasciato a chi costruisce

- La forma esatta delle sezioni del modello e la loro lunghezza indicativa.
- I segnali precisi con cui dev-flow propone Founder Intelligence, nel rispetto del default
  diretto.
- Il nome della famiglia nella `TAXONOMY` (proposta: `core`, ruolo `pre-development`).
- La divisione fine dei test tra i file esistenti e quelli nuovi.

## Scelte mie, da controllare

- Due assi (ricerca, decisione) con le etichette del prompt derivate, invece di cinque stati.
- Approvazione con citazione obbligatoria e sha256 del Playbook, sul modello di wireframe e
  registry-intake.
- Founder Intelligence soddisfa il gate dell'inventario registrando il verdetto, invece di
  cambiare il gate.
- Artefatti sotto `.workflow/founder/`, dentro il contratto.
- La skill prepara le interviste e sintetizza le note; non simula mai un'intervista.
- Documento il campo `inventory` nel contratto, che oggi manca.
- Il Playbook nella lingua dell'utente.

## Confronto tra il PDF e le altre skill di dev-flow

Richiesto dall'utente il 2026-10-17: le parti del PDF oltre lo stadio Idea (MVP, Launch,
Scale), confrontate con quello che le skill fanno davvero. Ricognizione sui file, con le due
affermazioni più pesanti verificate a mano (nessun modulo analytics in `module-add`, nessuna
revisione di sicurezza del codice nelle skill).

**In sintesi**: dev-flow copre bene la parte "costruire e spedire" degli stadi MVP e Launch
(scope e non-goals, contratto e regole, conformità GDPR/AI Act come ciclo continuo, i gate
prima del deploy, la cadenza scrum). Le differenze concettuali vere sono tre: **non misura
niente dopo il lancio**, **non rivede la sicurezza del codice dell'app**, e **la sua linea di
fasi finisce a `deployed`**, quindi il ciclo "itera verso le prove, o torna all'idea" del PDF
non ha un posto.

### MVP

| Raccomandazione del PDF | In dev-flow | Esito |
|---|---|---|
| Scope scritto: cosa fa, cosa deliberatamente non fa | `prd-from-idea` (Non-goals, Post-MVP), `prd-to-tasks` (i non-goals diventano task "da non fare") | coperto |
| Criteri per modificare lo scope, e mettere alla prova ogni nuova idea contro prove reali | `spec-review` segnala lo scope creep nel codice | **diverso**: dev-flow chiede se il codice rispetta il PRD; il PDF chiede se il PRD deve cambiare, e con quale prova. Il PRD non ha una sezione "cosa giustifica aggiungere una funzione" |
| Documento di architettura prima di costruire | regole della suite, decisioni di stack, sezioni di AGENTS.md scritte dalle skill | diverso ma adeguato: l'architettura viene dal contratto ed è imposta da strumenti, non scritta a mano per progetto |
| Metriche decise prima del lancio (attivazione, ritenzione, 7 e 30 giorni, falsi positivi) | solo "successo a 6 mesi" in `prd-from-idea`; `launch-audit` controlla che esista un analytics e rimanda a `module-add` | **mancante**, e in più `module-add` **non ha un modulo analytics**: il rimando di `launch-audit` va a vuoto |
| Test di product-market fit, iterare verso le prove, diagnosi di pivot | nessuno; `deployed` è l'ultima fase | mancante, ma è strategia di prodotto: lo prende Founder Intelligence in modalità `existing` |
| Revisione di sicurezza prima che un utente tocchi il prodotto (autorizzazioni, dati esposti nelle API, validazione, dipendenze vulnerabili) | soglia CVE di Next.js in `vercel-deploy`, PII nei log in `compliance-audit`, catena di fornitura in `registry-intake` | **mancante**: nessuna skill rivede autorizzazioni, injection o dati esposti, e i quattro gate prima del deploy la lasciano fuori |

### Launch

| Raccomandazione del PDF | In dev-flow | Esito |
|---|---|---|
| Audit del debito tecnico su tutto il codice, con un ordine (prima del rilascio / insieme alle funzioni / dopo) | audit per diff (`spec-review`) e per tema (forms, state, data-fetching, `promote-component`) | diverso: i pezzi ci sono, manca chi li compone in un elenco ordinato, e nessuno guarda i buchi di copertura dei test |
| Sicurezza e conformità come flusso di lavoro continuo | `compliance-audit` (GDPR, AI Act, rischi R1–R10, ripetuto dopo cambi rilevanti) | coperto per GDPR e AI Act; SOC 2 e HIPAA assenti, servono solo per l'enterprise |
| Cadenza degli sprint | `linear-scrum` | coperto |
| Triage dei bug, report settimanale sulle metriche | nessuno | mancante, piccolo; il report dipende dalle metriche |

### Scale

| Raccomandazione del PDF | In dev-flow | Esito |
|---|---|---|
| Una suite di casi limite del dominio come vantaggio difendibile | `write-tests` (dati peggiori come fixture di regressione), eval di eve | diverso ma vicino: basta un paragrafo |
| Integrazioni e lock-in (API, webhook, SDK) | modulo `mcp`, `product-to-agent-skill` | coperto per MCP; API pubbliche su richiesta |
| Osservabilità per poter offrire uno SLA (errori, log, uptime) | presente solo per mobile (`rn-eas-deploy`) | mancante per il web |
| Data flywheel, funzione GTM, assunzioni, finanza, investitori | nessuno | fuori ambito, o prematuro senza analytics |

### Cosa fare, secondo me

Fuori da questa skill, come lavori separati dopo Founder Intelligence, in quest'ordine:

1. **Misurazione** (M): un modulo `analytics` in `module-add`, con un default rispettoso della
   privacy e il consenso collegato a `compliance-audit`; una sezione *Misurazione* nel PRD
   (evento di attivazione, obiettivi a 7 e 30 giorni, cosa sarebbe un falso positivo);
   `launch-audit` controlla che gli obiettivi esistano, non solo la dipendenza. Va per primo
   perché oggi c'è un rimando a vuoto, e perché il percorso Founder Intelligence produce queste
   metriche allo stadio 9 ma il percorso diretto non ha dove scriverle.
2. **Revisione di sicurezza dell'app** (S–M): un quinto controllo prima del deploy
   (autorizzazioni, dati nelle risposte delle API e delle Server Action, validazione, segreti,
   dipendenze), appoggiato alle skill di security review già disponibili invece di costruirne
   una.
3. **Criteri di modifica dello scope** (S): una riga nel PRD (*quale prova giustifica una
   funzione nuova*) e un passo breve che mette alla prova una richiesta prima che
   `prd-to-tasks` riparta. Founder Intelligence li produce già; serve che esistano anche nel
   percorso diretto.
4. **Osservabilità web** (M): un modulo in `module-add` per errori, log strutturati e uptime.
5. **Audit del debito ordinato** (M): una modalità di dev-flow, dopo `deployed`, che compone gli
   audit esistenti con un controllo sulla copertura dei test e li ordina.
6. **Triage dei bug e più sistemi di task management** (S + L): etichette di gravità e un percorso
   leggero per una singola funzione; e, su richiesta dell'utente (2026-10-18), la skill di project
   management (oggi `linear-scrum`) supporta **Linear, Jira e GitHub** (Issues e Projects) come
   sistema di task management, con lo stesso metodo scrum e lo stesso contratto, invece di tre skill
   separate. **Il servizio si sceglie in fase di progettazione**, come le altre scelte di stack (una
   domanda in `prd-from-idea`, registrata in `meta.json`), in base al tipo di progetto e di cliente:
   Linear era la scelta iniziale, non l'unica. La skill cambia nome, perché non è più legata a un
   fornitore (proposte: `scrum`, `sprint-board`). Da decidere nel suo design: il nome della skill e del
   campo, come si migra un progetto già in Linear, e la policy di dev-flow che oggi dice "ogni
   progetto in Linear".

Non li farei: SOC 2 e HIPAA (finché un prodotto non punta all'enterprise), il data flywheel, e
il documento di architettura o il log di sessione per progetto (il contratto e la history di
`meta.json` bastano). Il ciclo "torna all'idea" dopo il lancio non va in dev-flow: è
l'invocazione tardiva di Founder Intelligence.
