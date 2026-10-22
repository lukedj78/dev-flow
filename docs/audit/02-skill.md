# Giro 2 — Skill e instradamento

**Domanda:** una skill viene scelta quando serve, e una sola?

Sessione indipendente, nessun contesto precedente sul repo. Ogni riscontro porta percorso +
riga o il comando eseguito. Classificazione esplicita per ognuno.

---

## 0. Il conteggio, prima di tutto

Il prompt dell'audit dice «59 skill». Misurato:

```
$ ls -d */SKILL.md | wc -l
56
$ grep '"skill_count"' skills.json
  "skill_count": 56,
```

**Le skill sono 56.** `skills.json` è corretto; il prompt dell'audit no. Non è un dettaglio
isolato — è la stessa classe di difetto di §4 (fatti duplicati in prosa fuori dalle liste di
controllo), e il prompt dell'audit ne è esso stesso un esempio. Vedi §4.1.

Nota di metodo: i 56 `SKILL.md` di primo livello sono le skill. `dist/` ne contiene 45 copie
di `references/contracts.md` e 56 pacchetti `.skill`; sono artefatti di build, esclusi da ogni
conteggio qui.

---

## 1. Instradabilità delle 56 `description`

### 1.1 Il dato grezzo

Tutte e 56 hanno `name` + `description`, e tutte e 56 contengono un marcatore di invocazione
(`Trigger` / `Use when` / `Use to` …) **e** una clausola `Not for:`. Non è un caso: è verificato
da un controllo automatico, `scripts/lint_skills.py:146-152`, che emette un `warn` quando manca
il marcatore e un altro quando manca `Not for:`. Eseguito:

```
$ python3 scripts/lint_skills.py
→ Linting 56 skills…
· 19 note(s) — informational, do not fail the build:
  …
✓ Clean (notes above).
```

**Nessuna skill è priva di una clausola «quando».** La risposta semplice alla domanda 1 è:
l'elenco delle skill «che un agente non saprebbe quando invocare» è vuoto, se il criterio è la
presenza di segnali. Ma il controllo verifica **la forma, non la sostanza**: `has_invocation_marker`
(`scripts/lint_skills.py:146`) è un test di sottostringa su sei marcatori. Una descrizione che
dicesse «Use to do the thing» lo supererebbe. Quindi la forma è applicata, l'instradabilità è prosa.

Misura meccanica della sostanza — quante enunciazioni dell'utente, fra virgolette, porta ogni
descrizione (è il formato di segnale che il repo stesso usa):

| enunciazioni citate | 0 | 1 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 13 | 15 | 17 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| n. skill | 1 | 2 | 2 | 8 | 17 | 8 | 5 | 8 | 1 | 1 | 1 | 2 |

Solo tre skill stanno sotto le tre enunciazioni: `registry-intake` (0), `data-fetching` (1),
`state-discipline` (1). Lette a mano, `registry-intake/SKILL.md:3` è comunque instradabile —
nomina situazioni concrete («asks if one is safe», «a hook refused an install») e registri
concreti (pdfcn, agentcn). Le altre due sono il problema di §2.3, non di questa sezione.

### 1.2 L'unica descrizione che instrada sé stessa sopra le altre

`rn-fundamentals/SKILL.md:3`:

> `Triggers on: "starting a new RN/Expo project", … Also triggers as a precondition when any other rn-* skill is selected and project setup is unclear.`

Questa seconda frase la rende co-candidata a **ognuno** dei 15 altri `rn-*`. È l'unica
descrizione del repo che si dichiara precondizione di un'altra famiglia intera. Chi vince non è
scritto in nessun punto applicato: `README.md:1340` la descrive («Start of any RN/Expo task»),
`dev-flow/references/stack-expo-rn.md:49` la elenca fra le skill di conoscenza, ma nessuno dei
due dice cosa fare quando entrambe si attivano, e la condizione «project setup is unclear» non è
osservabile dall'agente prima di aver letto il progetto.

Nove `rn-*` la citano nel corpo, non nella descrizione, e con una formula che non è un
instradamento (`rn-data-fetching/SKILL.md:8`, `rn-backend/SKILL.md:8`, `rn-expo-router/SKILL.md:8`,
`rn-animations-gestures/SKILL.md:8`, `rn-push-notifications/SKILL.md:8`,
`rn-publishing-payments/SKILL.md:8`: «see rn-fundamentals → …»). Il corpo si legge solo **dopo**
aver scelto la skill, quindi non partecipa alla scelta.

**Classificazione: rischio plausibile.** Non ho una sessione che si sia rotta su questo.
La misura che lo mostrerebbe: `evals/compliance/comply.py` è l'unico strumento del repo che
misura cosa l'agente *fa* invece di cosa la prosa dice; una batteria di prompt `claude -p` del
tipo «aggiungi una schermata di login» su un progetto Expo, contando quante volte viene invocata
`rn-fundamentals` oltre alla skill proprietaria, darebbe il numero.

**Intervento minimo:** togliere la seconda frase dalla descrizione e lasciare la precondizione
al corpo, oppure renderla condizionale a uno stato leggibile (`meta.json#stack` assente o
`stack.framework` non ancora scritto) invece di «unclear».

---

## 2. Sovrapposizioni

### 2.0 Cosa il repo applica già (e il limite esatto)

Esiste un controllo automatico, il **check 20** (`scripts/lint_skills.py:642-679`): due skill che
condividono una frase di trigger devono escludersi a vicenda nel `Not for:`. È vero enforcement,
non prosa, e oggi passa. Misurato replicando la sua logica:

```
== quoted phrases shared by >1 skill: 5 ==
   "add a cms"        ['module-add', 'rn-module-add']
   "add auth"         ['module-add', 'rn-module-add']
   "aggiungi sentry"  ['module-add', 'rn-module-add']
   "artboard"         ['iframe-canvas', 'wireframe-canvas']
   "set up sanity"    ['module-add', 'rn-module-add']
```

Tutte e cinque hanno esclusione reciproca. **Ma il check 20 vede solo le frasi fra doppi apici**
(`TRIGGER_PHRASE_RE = re.compile(r'["“]([^"”]{4,80})["”]')`, riga 648) e le confronta per
**uguaglianza esatta** dopo il lowercase (riga 670-672). Tre classi di sovrapposizione gli sono
strutturalmente invisibili:

1. un trigger in **backtick** anziché fra apici (§2.3);
2. un trigger che è **prefisso o variante** di un altro, non identico (§2.1);
3. un trigger espresso in **prosa non citata** (§2.2, §2.4).

Inoltre il test di esclusione è una **sottostringa** (`if b not in not_for`, riga 677): un
`Not for:` che nomina `rn-module-add` soddisfa automaticamente anche il requisito per
`module-add`, e `rn-write-tests` soddisfa `write-tests`. Ho verificato che **oggi nessuna delle 5
coppie passa solo per questa via** (replicato con confronto a confine di parola: zero buchi
attivi). Resta un falso negativo latente, non un difetto in atto.

**Classificazione del limite: rischio plausibile** (meccanismo che può rompersi, senza
dimostrazione in atto). *Intervento minimo:* in `check_shared_triggers` sostituire
`b not in not_for` con una ricerca a confine di parola — tre righe, nessun cambiamento di
architettura.

### 2.1 `transitions` ↔ `animated-icons` — trigger per prefisso, esclusione a senso unico

| | trigger | `Not for:` nomina l'altra? |
|---|---|---|
| `transitions/SKILL.md:3` | `"animate this"`, `"add a transition"`, `"aggiungi una transizione / animazione"` … | **no** |
| `animated-icons/SKILL.md:3` | `"animate this icon"`, `"animated icon"`, `"aggiungi un'icona animata"` … | **sì** — «a whole motion system (`transitions`)» |

`"animate this"` è prefisso stretto di `"animate this icon"`: su «animate this icon» entrambe
corrispondono. Il check 20 non lo vede perché le due stringhe non sono identiche.
`transitions`' `Not for:` nomina `rn-animations-gestures` e `module-add motion`, **non**
`animated-icons`.

**Chi dovrebbe vincere:** `animated-icons`, per una singola icona. Lo dice **solo**
`animated-icons`; `transitions` non lo dice da nessuna parte della descrizione, che è l'unica cosa
che l'agente legge prima di scegliere.

**Classificazione: problema dimostrato** (il file contraddice la simmetria che il check 20 esiste
per imporre; la dimostrazione è l'asimmetria stessa, verificata sui due file).
**Intervento minimo:** aggiungere «a single animated icon (`animated-icons`)» al `Not for:` di
`transitions/SKILL.md:3`. Una frase, in un file.

### 2.2 `vercel-deploy` attribuisce a `module-add deploy` ciò che la decisione registrata assegna a `project-infra-setup`

Tre skill toccano il progetto Vercel. La divisione è stata decisa e scritta in
`CHANGELOG.md:354`:

> «**`project-infra-setup`** creates and links the project, sets the project-level region and puts
> the values in. **`module-add deploy`** writes `vercel.json` and the build settings and decides
> which variables each environment needs.»

Ma `vercel-deploy/SKILL.md:3` dice:

> «Not for: the Vercel project config — `vercel.json`, **region, env-var matrix**, monorepo root
> directory are `module-add deploy` (**run it first**)»

e `project-infra-setup/SKILL.md:3` rivendica «the Vercel project (**region, environment
variables**, Git link)».

Quindi: `vercel-deploy` manda l'agente a `module-add deploy` per la *region* e le *variabili*,
che la decisione registrata assegna a `project-infra-setup` — ed è `project-infra-setup` la skill
che **crea e collega** il progetto. Un agente che segue «run it first» salta il passo che deve
venire prima. `vercel-deploy`'s `Not for:` non nomina `project-infra-setup` affatto (verificato:
`a→b=False`), mentre `project-infra-setup` nomina entrambe («Not for: wiring the code
(`module-add`), deploying (`vercel-deploy`)»).

**Classificazione: problema dimostrato** — il file contraddice la decisione registrata nel
CHANGELOG e nella descrizione della skill proprietaria.
**Intervento minimo:** in `vercel-deploy/SKILL.md:3` separare le due voci: «la creazione del
progetto, la region e i valori delle variabili sono `project-infra-setup`; `vercel.json` e le
build settings sono `module-add deploy`». Nessun'altra modifica.

### 2.3 `data-fetching` ↔ `state-discipline` — trigger identico, in backtick

`data-fetching/SKILL.md:3`:
> «…or **pastes `useState + useEffect + fetch`** in a Client Component»

`state-discipline/SKILL.md:3`:
> «Use when the user **pastes `useState + useEffect + fetch`**, reaches for `useState` to mirror a prop…»

Lo stesso trigger letterale, rivendicato da entrambe. Entrambe **si escludono** a vicenda
(`data-fetching`: «local UI state (`state-discipline`)»; `state-discipline`: «server-data reads
(use `data-fetching`)»), quindi la regola di simmetria è rispettata — ma l'esclusione è
formulata su **cosa l'utente vuole** (una lettura di dati vs stato locale), e l'incollata da sola
non lo dice: quello snippet *è* entrambe le cose. Il check 20 non lo vede perché la frase è in
backtick, non fra apici (riga 648).

Sono anche le due sole skill con una sola enunciazione citata in descrizione (§1.1), ed è la
stessa.

**Classificazione: rischio plausibile.** Non ho eseguito la misura.
**La misura che lo mostrerebbe:** `evals/compliance/comply.py` con un prompt che è *solo* quello
snippet, ripetuto ai tre livelli di supporto che quello script già implementa, contando quale
skill viene invocata. È l'unico dato del repo che misura l'obbedienza alla prosa.
**Intervento minimo:** in una delle due, qualificare il trigger con ciò che lo disambigua già nel
testo — p.es. `data-fetching` → «pastes `useState + useEffect + fetch` **to load server data**».

### 2.4 I quattro produttori di DESIGN.md — `figma-to-design-md` non esclude nessun fratello

Misurato (matrice di esclusione reciproca sulle descrizioni):

```
figma-to-design-md <-> image-to-design-md   a→b=False b→a=True
figma-to-design-md <-> url-to-design-md     a→b=False b→a=True
figma-to-design-md <-> screenshot-to-page   a→b=False b→a=True
figma-to-design-md <-> wireframe-canvas     a→b=False b→a=True
figma-to-design-md <-> design-md-to-app     a→b=False b→a=False
```

`figma-to-design-md/SKILL.md:3` è l'unica dei quattro produttori a non nominare **nessuno** dei
fratelli: il suo `Not for:` dice «converting Figma to code, reviewing production websites, or
design brainstorming before Figma work» — tre attività, zero skill. È anche la descrizione più
corta del repo (436 caratteri contro una media di ~830), quindi ha il margine per aggiungerle.

Nella pratica l'arbitrato esiste e funziona **per tipo di sorgente**: Figma URL / immagini raster
/ URL live sono segnali concreti e disgiunti, e i trigger citati non collidono
(`"crea il design.md"` e `"estrai i token"` sono solo di `figma-to-design-md`). Il rischio si
materializza solo quando la richiesta non nomina la sorgente — «estrai i token», «crea il
design.md» — e lì tre skill corrispondono mentre solo due si escludono.

**Classificazione: rischio plausibile** (non *dimostrato*: non ho una sessione in cui la scelta
sia andata male, e l'arbitrato per sorgente è reale).
**Intervento minimo:** aggiungere al `Not for:` di `figma-to-design-md` i due fratelli, come i
due fratelli già fanno con lei.

### 2.5 Sovrapposizioni esaminate e giudicate sane

Le dichiaro per non lasciarle sospese:

- **i cinque cancelli pre-deploy** (`shadscan`, `compliance-audit`, `vercel-doctor`,
  `launch-audit`, `app-security`): ognuno nomina gli altri quattro nel `Not for:`, con l'asse di
  competenza esplicito (UI / legale / costo / lancio / sicurezza). Arbitrato chiaro, in ogni
  descrizione. (Il *conteggio* è un problema separato: §4.2.)
- **`module-add` ↔ `rn-module-add`**: quattro trigger condivisi, esclusione reciproca su
  `next` vs `expo-rn`. È il caso che ha fatto nascere il check 20 ed è chiuso.
- **`iframe-canvas` ↔ `wireframe-canvas`** su `"artboard"`: esclusione reciproca presente
  («wireframes before a scaffold (`wireframe-canvas`)» / «a canvas inside the product
  (`iframe-canvas`)»). Chiuso.
- **`composition-patterns-guide` ↔ `promote-component`**: entrambe si attivano su «refactor
  questo componente», entrambe nominano l'altra, con l'asse giusto (componibilità vs movimento
  verticale nella gerarchia). Chiuso.
- **`registry-intake` ↔ `product-to-agent-skill`**: nessuna nomina l'altra, ed entrambe parlano
  di «agent skill». Ma `registry-intake` qualifica sempre «from a community registry» e
  `product-to-agent-skill` «for the product you just built». **Miglioramento facoltativo**, non
  un rischio: i qualificatori bastano.

---

## 3. Rinvii rotti

### 3.1 Validazione dei comandi, prima dei risultati

Il prompt avverte che un `grep` che non trova nulla può essere un `grep` sbagliato. **È accaduto,
e l'ho corretto.** Primo tentativo:

```
$ grep -rn --include=*.md '§' . | …
(eval):1: no matches found: --include=*.md
```

zsh espande `--include=*.md` come glob prima di passarlo a `grep`: il comando non ha cercato
nulla e non ha segnalato zero risultati, ha **fallito**. Con `--include='*.md'` quotato, e
validato su una stringa che so esistere:

```
$ grep -rn --include='*.md' 'dev-flow contract' . | grep -v '^./dist/' | head -3
CONTEXT.md:128:| **a DESIGN.md** | the Google design.md spec: …
dev-flow/references/scripts.md:48:- Is part of the dev-flow contract (`.workflow/DESIGN.md`, …
state-discipline/SKILL.md:24:Follows the dev-flow contract — see `references/contracts.md`. …
```

Il comando funziona. Lo stesso per i link markdown: il risolutore ha trovato **90 link relativi
che risolvono** oltre a quelli rotti, quindi non stava semplicemente non-trovando nulla.
E per i percorsi in backtick: **4067 percorsi interni al repo risolti** contro 391 non risolti,
poi filtrati a mano (vedi 3.4).

### 3.2 Link markdown: sani

448 file markdown scansionati (esclusi `dist/`, `.git/`, `node_modules/`, `.workflow/`).
90 link relativi risolvono, 19 no — e tutti e 19 sono falsi positivi verificati a mano:

- 16 in `.skill-doctor-report/transcripts/*.md`, che sono **trascrizioni di sessioni d'agente**,
  non documentazione del repo;
- `module-add/references/module-observability.md:61` e
  `rn-module-add/references/module-observability.md:56`: `[?&](token|code|key)` è un **letterale
  di espressione regolare**, non un link;
- `scrum/references/issue-standard.md:9`: `[file#Ln](link)` è un **segnaposto** in un esempio.

**Nessun link markdown rotto.** Classificazione: nessun riscontro.

### 3.3 Il rinvio `§` rotto — una sola istanza, dimostrata

`CHANGELOG.md:165` registra lo spostamento:

> «the Step 2 policies, "Shipping the product's own agent-skill" and **"Resources the user hands
> over" → new `references/policies.md`**»

La sezione vive ora in `dev-flow/references/policies.md:74` («## Resources the user hands over —
analyse, record, then actually use»), con sette passi numerati. Ma **due file continuano a
puntare alla vecchia casa**:

- `dev-flow/references/resources.md:11` → «`SKILL.md` §*Resources the user hands over* — review
  run, traps resolved, one yes missing.»
- `dev-flow/references/before-you-build.md:46-47` → «the work starts at **step 5 of `SKILL.md`
  §*Resources the user hands over***, not at zero.»

Verificato che la sezione non esiste più in `dev-flow/SKILL.md` — l'elenco completo delle sue
intestazioni non la contiene, e la stringa non compare:

```
$ grep -rn 'Resources the user hands over' --include='*.md' . | grep -v dist | grep -v skill-doctor
CHANGELOG.md:165: … → new `references/policies.md`;
dev-flow/references/resources.md:11:`SKILL.md` §*Resources the user hands over* …
dev-flow/references/policies.md:74:## Resources the user hands over — analyse, record, then actually use
dev-flow/SKILL.md:211:- **Resources the user hands over** — analyse, record in `references/resources.md`, then actually use them.
```

`dev-flow/SKILL.md:211` è una **riga di elenco**, non una sezione, e non ha passi: lo «step 5»
citato da `before-you-build.md` esiste solo in `policies.md:74` (è «5. **Do not stop at "it is an
option"**», `dev-flow/references/policies.md`, quinto passo numerato della sezione).

**Classificazione: problema dimostrato.** Un agente che segue `before-you-build.md:46` apre
`dev-flow/SKILL.md`, non trova né la sezione né uno step 5, e perde la regola che gli dice di
portare il lavoro fino a «manca un solo sì» — che è esattamente la regola che la memoria
dell'utente registra come *use the resources given*.

**Intervento minimo:** in quei due file sostituire `SKILL.md` con `references/policies.md`.
Due stringhe.

### 3.4 Rinvii `§` controllati e validi (falsi positivi del mio risolutore)

Li dichiaro perché un elenco di «sezioni mancanti» senza questa verifica sarebbe rumore. 179
coppie `` `file` §Sezione `` unificate; il risolutore automatico ne segnalava ~60, e la
verifica a mano ha mostrato che tutte tranne quella di §3.3 sono valide. Le forme che il mio
matcher sbagliava:

- **sotto-voci con lettera**: `eve-patterns.md §8f` da `rn-eas-deploy/references/asc-cli.md:41`
  → esiste, è la voce «**f. Gate on reversibility…**» dentro `## 8.` di
  `eve-agent/references/eve-patterns.md:380`. Idem `§9e`, `§7d`, `§11b`, `§8b`.
- **grassetto con testo di coda**: `design-md-to-app/SKILL.md §Visual verification` → esiste a
  `design-md-to-app/SKILL.md:1146` («**Visual verification — best-effort obbligatorio.**»).
  Idem `iframe-canvas/SKILL.md §Overlays render in the parent` → `iframe-canvas/SKILL.md:156`.
- **voci di elenco anziché intestazioni**: `references/contracts.md § nextjs_version` da
  `compliance-audit/SKILL.md:54` → esiste a `compliance-audit/references/contracts.md:467`.
- **documentazione esterna**: `authentication.md §Optimistic` da
  `module-add/references/module-auth.md:299` è la **documentazione di Next.js**, non un file del
  repo. `docs/engineering/code-review.md` da `spec-review/SKILL.md:18` è un URL di
  `mattpocock/skills`. `docs/eve-registries.md` da `eve-registry-porting/SKILL.md:180` è
  dichiarato «in that repo» (AgentOS).
- **artefatti del progetto generato, non del repo**: `.workflow/meta.json`, `lib/auth.ts`,
  `app/layout.tsx`, `docs/compliance/dpia-template.md`, `docs/vercel/doctor-report.md`,
  `assets/icon.png`, `scripts/guard/primitives-guard.mjs`. Sono percorsi *nel progetto bersaglio*;
  l'originale di quest'ultimo è vendorizzato a
  `design-md-to-app/assets/guard/primitives-guard.mjs` e viene copiato all'installazione.
- **nomi di controllo, non di sezione**: `launch-audit §third-party-marks` da
  `design-md-to-app/SKILL.md:434` è l'id di un check dello scanner, verificato in
  `launch-audit/scripts/test_scan_launch.py:327`.
- **`linear-scrum`**: la skill non esiste più (rinominata `scrum`). Le sole due citazioni in file
  vivi — `README.md:955` e `CHANGELOG.md:22` — sono **deliberate**: descrivono la migrazione che
  `scripts/meta_tracker.py migrate` esegue dal vecchio formato. Non sono rinvii rotti. Le altre
  stanno in `docs/superpowers/` (piani archiviati).

Verifica che `AUDIT.md:283-296` non segnali script mancanti: i nomi vi compaiono senza estensione
(`dev-flow/scripts/test_inventory`), ma i file esistono tutti
(`dev-flow/scripts/test_inventory.py`, `…/test_wireframes_gate.py`,
`…/test_primitives_guard_gate.py`, `…/test_research.py`,
`design-md-to-app/scripts/test_setup_primitives_guard.py`,
`registry-intake/scripts/test_registry_intake.py`). Abbreviazione in prosa, non un rinvio rotto.

### 3.5 Il rinvio che punta a una skill che il repo non contiene

`write-tests/SKILL.md:3`, nella clausola `Not for:`:

> «running QA on a deployed site (**`qa`**)»

Misurato:

```
$ ls -d qa qa-only
ls: qa: No such file or directory
ls: qa-only: No such file or directory
$ grep -c '"qa"' skills.json
0
$ grep -n 'qa' install.sh
(nessun risultato)
$ grep -n '^### `qa\|^| `qa' README.md
(nessun risultato)
$ grep -n '\bqa\b' dev-flow/references/external-skills.md
(nessun risultato)
$ ls -d ~/.claude/skills/qa
/Users/lucadigerlando/.claude/skills/qa
```

`qa` **non è una delle 56 skill**, non è in `skills.json`, non è installata da `install.sh`, non
è nel catalogo del README, e non è nel registro delle skill esterne
(`dev-flow/references/external-skills.md`, che è il posto dove il repo dichiara ciò che non
possiede: vi stanno `sleekdotdesign/agent-skills`, `rorkai/app-store-connect-cli-skills`,
`mattpocock/skills`, `Rizzo-AI-Academy/rizzo-flow`, Skillry, `Leonxlnx/taste-skill`,
`echris6/motion-video-kit`). Esiste **solo** in `~/.claude/skills/qa`, la cartella personale di
questa macchina.

Chi installa dev-flow da questo repo ottiene una descrizione che instrada verso una skill che non
ha, e nulla nel repo gli dice dove trovarla.

Il lint non può vederlo: `check_routing_references` (`scripts/lint_skills.py:299-327`) richiede un
**verbo di instradamento** prima del nome in backtick (`invoke`, `route to`, `hand off to`,
`delegate to`, `defer to`, `that's`, `that is`), e il commento alla riga 292-293 dichiara la
scelta esplicitamente: «*a bare "→ `x`" is NOT a marker … Deliberately narrow*». Una clausola
`Not for: … (`qa`)` non ha verbo, quindi è fuori portata — ed è la stessa classe del difetto che
quel commento racconta: «*which is how `setup-deploy` stayed routed-to for months without
existing*».

**Classificazione: problema dimostrato.**
**Dove il fatto dovrebbe vivere:** `dev-flow/references/external-skills.md` ha già la forma
giusta (riga per skill esterna, con costo, licenza e «cosa fa dev-flow invece»). Se `qa` è una
skill esterna che vogliamo citare, le serve una riga lì; se non lo è, va togliuta dal `Not for:`
di `write-tests`.
**Intervento minimo aggiuntivo (facoltativo):** estendere `check_routing_references` a riconoscere
anche il contesto `Not for:` — le descrizioni sono 56 stringhe, il costo di scansionarle è nullo.

---

## 4. Ridondanza — lo stesso fatto in più documenti

### 4.0 Cosa è già applicato, e dove si ferma

Il repo **applica** la duplicazione a livello di *file*, e lo fa bene. `check_vendored_source`
(`scripts/lint_skills.py:770-793`) confronta byte a byte ogni copia vendorizzata, e per
`contracts.md` usa una **glob**, non un elenco:

```python
VENDORED_EVERYWHERE = [
    ("dev-flow/references/contracts.md", "*/references/contracts.md"),
]   # scripts/lint_skills.py:765-767
```

Il commento alla riga 763 spiega perché: «*Discovered rather than listed, so a skill that starts
carrying it is checked from its first commit.*» È la forma giusta — una lista non può invecchiare
se non è una lista. Verificato:

```
$ ls */references/contracts.md | wc -l
45
$ # confronto sha256 di ognuna contro dev-flow/references/contracts.md
identical-to-source: 44   diverging: 0
$ find dist -name contracts.md | wc -l
45
$ # idem per le copie in dist
dist identical: 45  diverging: 0
```

**45 copie nel repo e 45 in `dist/`, tutte e 90 byte-identiche. Zero divergenze.**

Dove si ferma: i fatti duplicati **dentro la prosa**. Lì il controllo è
`check_stated_counts` (`scripts/lint_skills.py:439-468`), e poggia su **due liste compilate a
mano**:

- `COUNT_FILES` (riga 401-407): **11 file**. `README.md`, `CONTEXT.md`,
  `docs/dev-flow-skill-map.html`, `install.sh`, `uninstall.sh`, `dev-flow/SKILL.md`,
  `dev-flow/references/external-skills.md`, `docs/skill-doctor-referto.html`, i due
  `.claude-plugin/*.json`, `dist/agent-plugin/plugin.json`. **Nessun altro `SKILL.md`, non
  `AUDIT.md`, non `CHANGELOG.md`, non `docs/`.**
- `TOTAL_PATTERNS` (riga 408-431): **25 espressioni regolari**, ognuna aggiunta dopo una
  mancanza specifica. I commenti lo ammettono: «*Found by eye, not by the check*» (riga 423),
  «*It sat at 44 for a full release*» (riga 429).

Un fatto in un file fuori dall'elenco, o in una formulazione fuori dalle 25, invecchia in
silenzio. Segue la dimostrazione.

### 4.1 Lo stesso fatto, tre numeri diversi, in tre file vivi — dimostrato

Il fatto: *in quante skill è vendorizzato `contracts.md`*. Misurato sopra: **45** (44 copie più
la sorgente).

| file | riga | dice | vero |
|---|---|---|---|
| `CONTEXT.md` | 172 | «byte-identical in **44 skills**» | 44 copie oltre la sorgente — **corretto** se letto così |
| `spec-review/references/risk.md` | 34 | «`contracts.md` in **41 skills**» | **falso, 45** |
| `docs/audit-prompt.md` | 51 | «vendorizzato in **41 skill** (più **41 copie** in `dist/`)» | **falso, 45 e 45** |

`CONTEXT.md` è dentro `COUNT_FILES` — ma la sua formulazione, «byte-identical in 44 skills», non
corrisponde a nessuno dei 25 `TOTAL_PATTERNS`, quindi nemmeno lì il numero è verificato: è
corretto per cura dell'autore, non per controllo. Gli altri due file non sono nemmeno
nell'elenco.

E lo stesso `docs/audit-prompt.md:88` dice «**59 skill**» dove sono **56** (§0).

**Classificazione: problema dimostrato.** Non è un'inferenza: ho contato i file e confrontato gli
hash.

**Conseguenza misurata in questa stessa sessione:** il prompt che mi è stato dato ordinava al
Giro 1 di «verificare che le **41** copie vendorizzate siano byte-identiche (e le **41** in
`dist/`)». Sono 45 e 45. Un numero stantio in un documento ha prodotto un'istruzione sbagliata a
un altro agente dell'audit — che è esattamente la classe di difetto che la memoria dell'utente
registra come misurata («dieci memorie `reference` erano duplicati, e tre fasi di progetto erano
già false»).

**Dove il fatto dovrebbe vivere:** in **nessun documento**. È già derivabile con un comando
(`ls */references/contracts.md | wc -l`), e `check_vendored_source` lo scopre già con una glob.
*Intervento minimo:* sostituire il numero con la glob o con il comando in
`spec-review/references/risk.md:34` e `docs/audit-prompt.md:51`; oppure, se un numero deve
restare leggibile, aggiungere a `TOTAL_PATTERNS` il pattern
`r"byte-identical in (\d+) skills"` + `r"contracts\.md` in (\d+) skills"` e mettere i due file in
`COUNT_FILES` — ma la prima strada è più corta e non può invecchiare.

### 4.2 «I cinque cancelli pre-deploy», in 16 posti vivi, senza alcun controllo

Il fatto — *quanti sono i cancelli pre-deploy e quali* — è ripetuto in almeno 16 posizioni vive,
cinque delle quali sono **frontmatter `description`** (ciò che instrada):

| file | riga |
|---|---|
| `launch-audit/SKILL.md` | 3 (descrizione), 17 |
| `shadscan/SKILL.md` | 3 (descrizione) |
| `app-security/SKILL.md` | 3 (descrizione) |
| `compliance-audit/SKILL.md` | 3 (descrizione) |
| `vercel-deploy/SKILL.md` | 3 (descrizione), 90, 106 |
| `vercel-doctor/SKILL.md` | 122 |
| `dev-flow/SKILL.md` | 189, 203 |
| `dev-flow/references/policies.md` | 23, 31 |
| `dev-flow/references/finishing-a-feature.md` | 68 |
| `spec-review/SKILL.md` | 83, 251 |
| `spec-review/references/risk.md` | 101 |
| `vercel-deploy/references/deploy-checklist.md` | 19 |
| `docs/knowledge-index.md` | 73 |
| `README.md` | 1269, 1288 |

Oggi **tutte dicono cinque e sono coerenti** — l'ho verificato con
`grep -rniE '(…|five|four|six) pre-deploy gates?|(five|four|six) gates'`. Il riscontro non è che
siano sbagliate: è che **nessun controllo le tiene insieme**, e sono già andate fuori sincrono
**due volte**, per ammissione del repo stesso:

- `CHANGELOG.md:360`: «*The number of pre-deploy gates moved from file to file: **four** in the
  routing table, **three** in the `deployed` row, the review policy, `spec-review`,
  `vercel-deploy` and the knowledge…*»
- `docs/superpowers/specs/2026-10-18-debt-audit-design.md:56`: «*Conteggi vecchi dei gate:
  `compliance-audit/SKILL.md:109` dice «**three** pre-deploy gates»…*»

Entrambe le volte la correzione è arrivata **a occhio**, elencata a mano in un piano
(`docs/superpowers/plans/2026-10-18-app-security.md:164-176` enumera i file da modificare uno per
uno, e la riga 176 dice «*and any other "four pre-deploy gates" that `grep -rn` finds*»). Il
piano riconosce che il meccanismo è un grep manuale.

C'è già pressione sul numero: `dev-flow/references/finishing-a-feature.md:68` elenca
«`app-verification`, **the five gates**» — un sesto passo pre-spedizione che non è contato — e
`spec-review/SKILL.md:251` deve dichiarare di «*non* essere un sesto cancello».

**Classificazione: rischio plausibile** (il meccanismo è dimostratamente fragile — due rotture
registrate — ma oggi i 16 posti sono coerenti, quindi non è un problema in atto).

**Dove il fatto dovrebbe vivere:** in `skills.json`, che è **generato**
(`scripts/build_skills_registry.py`) e già porta le famiglie. Un campo
`"gates": ["compliance-audit","vercel-doctor","shadscan","launch-audit","app-security"]` darebbe
al lint la stessa presa che ha sul conteggio delle skill.
**Intervento minimo:** aggiungere a `check_stated_counts` un pattern
`r"(?:the )?(five|four|six|three|\d+) (?:pre-deploy )?gates"` risolto contro
`len(skills.json["gates"])`, e aggiungere i cinque `SKILL.md` dei cancelli a `COUNT_FILES`.
Un controllo, una lista di cinque nomi: chiude 16 copie.

### 4.3 Ridondanza sana, dichiarata

- `rn-fundamentals/references/stack-defaults.md` ↔ `rn-bootstrap/references/stack-defaults.md`:
  duplicati **con controllo** (`scripts/lint_skills.py:759`), e il file stesso lo dichiara
  (`rn-bootstrap/references/stack-defaults.md:2`: «*This file is carried by `rn-fundamentals` and
  `rn-bootstrap`, byte-identical (`lint_skills.py` fails otherwise)*»). È il modello da imitare
  per §4.2.
- `contracts.md` in 45 skill: duplicazione **voluta**, dichiarata in `CONTEXT.md:170-174`, e
  verificata da una glob. Il difetto non è la duplicazione del file; è il *numero* ripetuto in
  prosa (§4.1).
- `dev-flow/scripts/meta_io.py`, `surfaces.py` e altri vendorizzati in più skill: tutti coperti
  da `VENDORED_SOURCE` (`scripts/lint_skills.py:752-759`). **Nessun riscontro.**

---

## 5. Cosa si rompe per primo, per area

Una frase per area, come richiesto, senza voti.

- **Instradabilità (§1).** Si rompe per prima `rn-fundamentals`, che si dichiara precondizione di
  15 altre skill senza che nessun documento dica chi vince; lo mostrerebbe una batteria di
  `claude -p` su un compito Expo ordinario, contando le invocazioni in eccesso con lo stesso
  metodo di `evals/compliance/comply.py`.
- **Sovrapposizioni (§2).** Si rompe per prima la coppia `transitions`/`animated-icons`, perché un
  trigger è prefisso stretto dell'altro e l'esclusione è a senso unico; lo mostrerebbe il check 20
  se confrontasse per prefisso invece che per uguaglianza esatta — oggi la misura è il diff
  manuale fra le due descrizioni, già fatto qui.
- **Rinvii (§3).** Si rompe per primo `write-tests` → `qa`, perché il rinvio esce dal repo e il
  lint è deliberatamente cieco alle clausole `Not for:`; lo mostrerebbe estendere
  `check_routing_references` alle 56 descrizioni, che costa una scansione di 56 stringhe.
- **Ridondanza (§4).** Si rompe per primo il conteggio dei cancelli pre-deploy, perché vive in 16
  posti di cui cinque instradano e nessun controllo li lega; lo mostrerebbe un pattern in
  `check_stated_counts` risolto contro un elenco in `skills.json` — e il fatto che sia già
  accaduto due volte è la misura che abbiamo.

---

## 6. Riepilogo dei riscontri

**Problemi dimostrati (4)**

| | riscontro | prova |
|---|---|---|
| D1 | `write-tests` instrada verso la skill `qa`, che il repo non contiene, non installa e non dichiara fra le esterne | `write-tests/SKILL.md:3`; `ls -d qa` → assente; `grep -c '"qa"' skills.json` → 0; assente da `install.sh`, dal catalogo README e da `dev-flow/references/external-skills.md`; presente solo in `~/.claude/skills/qa` |
| D2 | Lo stesso fatto (copie di `contracts.md`) porta tre numeri diversi in tre file vivi, e uno ha già sviato un altro agente di questo audit | vero = 45 (`ls */references/contracts.md \| wc -l`, 44 hash identici + sorgente, 45 in `dist/`); `CONTEXT.md:172` = 44, `spec-review/references/risk.md:34` = 41, `docs/audit-prompt.md:51` = 41 «+41 in dist». Inoltre `docs/audit-prompt.md:88` = «59 skill» vs 56 |
| D3 | `vercel-deploy` attribuisce region e variabili a `module-add deploy`, mentre la decisione registrata le assegna a `project-infra-setup`, che non è nominata | `vercel-deploy/SKILL.md:3` vs `CHANGELOG.md:354` e `project-infra-setup/SKILL.md:3`; matrice di esclusione: `vercel-deploy`→`project-infra-setup` = False |
| D4 | Due file puntano a una sezione di `dev-flow/SKILL.md` che è stata spostata in `references/policies.md` | `dev-flow/references/resources.md:11` e `dev-flow/references/before-you-build.md:46-47` vs `dev-flow/references/policies.md:74`; `dev-flow/SKILL.md:211` è una riga di elenco senza passi |

*(D3 e l'asimmetria `transitions`/`animated-icons` di §2.1 sono due istanze della stessa classe —
una descrizione che non nomina la skill con cui condivide il terreno. Conto §2.1 come quinto
riscontro dimostrato se si preferisce separarle; qui sta sotto D3 per non gonfiare il totale.)*

**Rischi plausibili (5)** — §1.2 `rn-fundamentals` precondizione di 15 skill · §2.0 il test di
esclusione del check 20 è una sottostringa (falso negativo latente, zero buchi attivi oggi) ·
§2.1 `transitions` non esclude `animated-icons` su un trigger per prefisso · §2.3
`data-fetching`/`state-discipline` rivendicano lo stesso trigger letterale in backtick · §4.2 il
conteggio dei cancelli in 16 posti senza controllo, già rotto due volte.

**Miglioramenti facoltativi (4)** — §2.4 `figma-to-design-md` non esclude i fratelli produttori di
DESIGN.md · §2.5 `registry-intake`/`product-to-agent-skill` non si nominano · §3.5 estendere
`check_routing_references` alle clausole `Not for:` · §4.2 spostare l'elenco dei cancelli in
`skills.json`.

**Preferenze personali (1)** — le 19 note su descrizioni fra 900 e 1024 caratteri
(`scripts/lint_skills.py:140-144`): il margine è del 7% su un limite dove, sopra, «*a conforming
client skips the skill*» (riga 59-62). Il limite **è** applicato come errore (riga 123-134), e
`GRANDFATHERED_LONG_DESC` è vuoto per scelta dichiarata, quindi il meccanismo è sano. Che 19
descrizioni su 56 stiano a meno di 125 caratteri dal taglio è una scelta di stile dell'autore, non
un difetto: lo dico e passo oltre.

---

## 7. Verifiche che non ho potuto eseguire

- **Quale skill un agente scelga davvero** sui trigger ambigui di §2.1, §2.3 e §1.2. Non l'ho
  misurato. Servirebbe: `python3 evals/compliance/comply.py` adattato a un corpus di prompt di
  instradamento (lo snippet `useState + useEffect + fetch` nudo, «animate this icon», «aggiungi una
  schermata di login» su progetto Expo), ai tre livelli di supporto che quello script già
  implementa, contando la skill invocata. È l'unico strumento del repo che misura cosa l'agente
  *fa*; tutto il resto in questo referto misura cosa i file *dicono*.
- **Se il client reale tronchi o scarti le descrizioni vicine al limite di 1024.** Non ho un modo
  di osservare la lista di skill che il client costruisce. Servirebbe un confronto fra le 56
  `description` sul disco e quelle effettivamente presentate all'agente.
- **Il check 20 con il confronto a confine di parola.** Ho replicato la sua logica in uno script
  di scratch e non ho trovato buchi attivi, ma non ho modificato `scripts/lint_skills.py` (vincolo:
  nessuna modifica ai sorgenti). Il comando che lo chiuderebbe: sostituire `b not in not_for` con
  `re.search(rf'(?<![\w-]){re.escape(b)}(?![\w-])', not_for)` alla riga 677 e rieseguire
  `python3 scripts/lint_skills.py`.

## 8. Comandi per riprodurre

```bash
cd /Users/lucadigerlando/my-skills

# §0 — il conteggio
ls -d */SKILL.md | wc -l                       # 56
grep '"skill_count"' skills.json               # 56

# §1 — il lint, e i suoi 19 note
python3 scripts/lint_skills.py

# §2 — frasi di trigger condivise (la logica del check 20)
#   vedi scripts/lint_skills.py:642-679 per l'originale

# §3.1 — la trappola del grep in zsh: quotare sempre --include
grep -rn --include='*.md' 'dev-flow contract' . | grep -v '^./dist/' | head -3   # valida il comando
grep -rn --include='*.md' '§' . | grep -v '^./dist/' | wc -l

# §3.3 — la sezione spostata
grep -rn 'Resources the user hands over' --include='*.md' . | grep -v dist | grep -v skill-doctor
grep -n '^#' dev-flow/SKILL.md                 # la sezione non c'è

# §3.5 — la skill qa
ls -d qa 2>&1; grep -c '"qa"' skills.json; grep -n 'qa' install.sh
grep -n '\bqa\b' dev-flow/references/external-skills.md

# §4.0/§4.1 — le copie vendorizzate, contate e confrontate
ls */references/contracts.md | wc -l           # 45
find dist -name contracts.md | wc -l           # 45
h=$(shasum -a256 dev-flow/references/contracts.md | cut -d' ' -f1)
for f in */references/contracts.md dist/agent-plugin/skills/*/references/contracts.md; do
  [ "$(shasum -a256 "$f" | cut -d' ' -f1)" = "$h" ] || echo "DIVERGE: $f"
done                                           # nessun output

# §4.2 — il conteggio dei cancelli, in ogni file vivo
grep -rniE '(five|four|six|three) (pre-deploy )?gates?' --include='*.md' . \
  | grep -v '^./dist/' | grep -v '^./docs/superpowers/' | grep -v skill-doctor
```

---

*Giro 2 di 3. Nessun sorgente di skill modificato, nessuna `.workflow/` toccata, nessun commit.*
