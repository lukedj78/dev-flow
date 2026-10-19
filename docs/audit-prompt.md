# Audit di dev-flow — prompt in tre giri

Versione tagliata dell'audit monolitico. Tre giri indipendenti, da lanciare
**in sessioni separate e pulite**: ogni giro produce il proprio referto, e un
giro non ha bisogno dei risultati degli altri.

Perché separati: un solo passaggio con novanta sotto-domande produce *la forma*
di un audit — tabelle, matrici, voti — con asserzioni al posto delle misure.
Ogni riscontro vero su questo repo è costato una misura: scaricare un tarball,
sondare un registro, passare 36 progetti.

**Chi lo esegue.** Non la sessione che ha scritto il codice. Una sessione pulita,
o un subagente, che non ha in contesto le giustificazioni di chi l'ha scritto —
altrimenti riporta le ragioni dell'autore invece dei suoi errori.

---

## Vincoli comuni (valgono per tutti i tre giri)

1. **Ogni affermazione porta la sua prova**: percorso file e numero di riga, oppure
   il comando eseguito e il suo output. Un'affermazione senza prova va cancellata,
   non ammorbidita.
2. **Non confondere una regola descritta in un documento con una regola verificata
   da un controllo automatico.** Questa è la distinzione centrale dell'audit.
   Il repo è ~58 000 righe di markdown contro ~18 000 di Python: la prosa è la
   maggioranza, e la prosa non si applica da sola.
3. **Classifica ogni riscontro** in una di quattro categorie, e dillo esplicitamente:
   - **problema dimostrato** — hai eseguito qualcosa e si è rotto, o hai il file
     che contraddice il documento;
   - **rischio plausibile** — un meccanismo che può rompersi, senza una dimostrazione;
   - **miglioramento facoltativo** — funziona, si potrebbe fare meglio;
   - **preferenza personale** — dillo e passa oltre.
4. **Se non puoi eseguire una verifica, dichiaralo** e scrivi quale comando servirebbe.
   Nessuna stima al posto di una misura.
5. **Nessun voto numerico.** Per ogni area, una frase: *cosa si rompe per primo, e
   quale misura lo mostrerebbe*. Un 6/10 non è azionabile e un «voto previsto dopo
   le correzioni» è un numero inventato per costruzione.
6. **Non proporre riscritture dell'architettura.** Interventi minimi, locali,
   verificabili uno per uno.

## Dove sono già le prove (leggi prima di cercare)

- `evals/run_evals.py` — golden test property-based sugli script deterministici.
- `evals/generated-page/check.py` — sedici controlli meccanici su un'app generata.
- `evals/compliance/comply.py` — sessioni `claude -p` reali, graduate su **cosa l'agente
  ha fatto** a tre livelli di supporto nel prompt. È l'unico dato che misura
  l'obbedienza alla prosa, non la prosa.
- `scripts/lint_skills.py` — lint sui sorgenti delle skill.
- `.githooks/pre-commit` + `scripts/install-git-hooks.sh` — rigenerazione e lint al commit.
  Nota: `core.hooksPath` è per clone, quindi il gancio esiste solo dove qualcuno l'ha installato.
- `dev-flow/references/contracts.md` — il contratto, **vendorizzato in 41 skill**
  (più 41 copie in `dist/`), che devono essere byte-identiche.
- `dev-flow/scripts/show_state.py` — i controlli su `.workflow/meta.json`.
- `registry-intake/scripts/registry_intake.py` + il suo self-test.

---

## Giro 1 — Contratto e stato

**Domanda:** il contratto dice il vero, e lo dice in un solo posto?

Da fare:

1. Verifica che le 41 copie vendorizzate di `contracts.md` siano byte-identiche
   alla sorgente (e le 41 in `dist/`). Se divergono, elenca le divergenze.
2. Prendi ogni chiave `stack.*` e ogni fase del ciclo di vita dichiarate nel contratto
   e di' per ognuna: **esiste un controllo che la verifica, o è solo prosa?**
   Cita il controllo (file e riga) o marcala *non applicata*.
3. Cerca nel contratto le affermazioni su strumenti esterni (comandi, flag, default di
   versione). Per ognuna, verificala contro l'artefatto pubblicato — non contro la
   pagina che lo descrive. Precedente: `shadcn add --all` installa dall'indice di 61
   voci, quindi «tutti» era falso, e su quella riga poggiava una regola d'oro.
4. Prendi 5 progetti reali in `~/projects` con un `.workflow/meta.json` e confronta
   lo stato dichiarato con quello che c'è sul disco. **Non scrivere in nessun
   `.workflow/`**: un altro agente può avere una sessione attiva.

**Risultato:** `docs/audit/01-contratto.md` — divergenze, più una tabella
*regola → controllo | non applicata*.

---

## Giro 2 — Skill e instradamento

**Domanda:** una skill viene scelta quando serve, e una sola?

Da fare:

1. Per ognuna delle 59 skill: il `description` del frontmatter dice *quando* invocarla
   con dei segnali concreti, o descrive solo cosa fa? Elenca quelle che un agente non
   saprebbe quando invocare.
2. Trova le sovrapposizioni: coppie o gruppi di skill che un agente potrebbe invocare
   per lo stesso compito, e di' quale dovrebbe vincere e se il repo lo dice da qualche parte.
3. Trova i rinvii rotti: un documento che punta a una sezione, un file o uno script
   che non esiste più. **Attenzione**: un `grep` che non trova nulla può essere un
   `grep` sbagliato (caratteri `§`, pipe da escapare, virgolette). Prima di concludere
   che un contenuto manca, verifica il comando su un caso che *sai* esistere.
4. Misura la ridondanza: lo stesso fatto ripetuto in più documenti, dove una copia
   può invecchiare da sola. Precedente misurato: dieci memorie `reference` erano
   duplicati, e tre fasi di progetto erano già false.

**Risultato:** `docs/audit/02-skill.md` — skill non instradabili, sovrapposizioni,
rinvii rotti, duplicazioni con il posto dove il fatto dovrebbe vivere.

---

## Giro 3 — Test e sicurezza

**Domanda:** i controlli coprono le righe che contano, e i cancelli si possono aggirare?

Da fare:

1. Esegui tutto quello che è eseguibile: i self-test, `scripts/lint_skills.py`,
   `evals/run_evals.py`, i test di `registry-intake`. Riporta l'output, inclusi i
   fallimenti. Se un test non parte, dillo con l'errore.
2. 69 script Python, ~18 000 righe, 17 file di test. Di' **quali script non hanno
   alcun test**, e per i tre più usati quale comportamento non testato romperebbe
   più cose.
3. Prendi i cancelli di `registry-intake` (codici T/S/D/C/E/R/V, K1–K11, M1–M6, H1–H10)
   e per ognuno chiediti: **esiste un input che passa il cancello e non dovrebbe?**
   Precedenti reali di questa settimana: solo il primo script di un comando concatenato
   veniva letto; `shlex.split` non è una shell, quindi `${CLAUDE_PROJECT_DIR}` restava
   non espanso e produceva un falso «file mancante»; esentare il nostro gancio *per
   percorso* creava il nascondiglio perfetto. Cerca la prossima di queste.
4. Il gap dichiarato: **non c'è governance per le mod di Claude Code.** Verifica che
   sia ancora vero e di' qual è l'intervento minimo.

**Risultato:** `docs/audit/03-test-sicurezza.md` — output dei test, script senza
copertura, tentativi di aggiramento (riusciti e falliti), con il comando per riprodurli.

---

## Cosa NON chiedere a questo audit

- **Benchmark concettuale con altri framework.** È la fase a resa più bassa: l'agente
  attinge a quello che sa invece di misurare questo repo.
- **Voti e matrici di priorità P0–P3.** La priorità si decide dopo, leggendo i riscontri.
- **Una roadmap.** Prima i riscontri; il piano è un secondo giro, separato.
