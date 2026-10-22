# Giro 1 — Contratto e stato

**Domanda**: il contratto dice il vero, e lo dice in un solo posto?

Sessione indipendente, nessun contesto precedente sul repo. Data di esecuzione: **2026-10-22**.
Sorgente del contratto: `/Users/lucadigerlando/my-skills/dev-flow/references/contracts.md` (575 righe).

Ogni riscontro porta il percorso+riga o il comando e il suo output. Classificazione esplicita in
testa a ogni voce: **problema dimostrato** / **rischio plausibile** / **miglioramento facoltativo** /
**preferenza personale**.

**Cosa si rompe per primo, per area** (una frase, nessun voto):

| Area | Cosa si rompe per primo | Quale misura lo mostrerebbe |
|---|---|---|
| Copie vendorizzate | nulla: sono byte-identiche e un controllo automatico lo verifica — ma solo le 44 fuori da `dist/` | `shasum -a 256` su tutte le 90 copie (fatto, sotto) |
| Chiavi `stack.*` | un valore fuori enum in `stack.framework` spegne in silenzio tre gate su quattro | contare i valori fuori enum sui progetti reali (fatto: 13 su 44) |
| Fasi | una fase ferma dietro al codice disattiva ogni controllo che si aggancia alla fase | contare i `page.tsx` contro la fase dichiarata (fatto: 6 progetti) |
| Strumenti esterni | la data più recente del contratto è di 19 giorni e tre affermazioni su shadcn/Next sono già false | rileggere l'artefatto pubblicato (`npm pack`, `registry.npmjs.org`) — fatto, sotto |
| Stato dei progetti | i gate di `scaffolded` non si rieseguono mai dopo l'attraversamento, e 28 progetti su 37 restano nello stato che il contratto dichiara rifiutato | eseguire `gate_refusal` sulle combinazioni di fase (fatto, sotto) |

---

## 1. Copie vendorizzate di `contracts.md`

### 1.1 Il conteggio del prompt d'audit è sbagliato — e per difetto

**problema dimostrato** (minore, documentale).

`docs/audit-prompt.md:51` e `:64` dicono «vendorizzato in 41 skill (più 41 copie in `dist/`)».
Il conteggio reale, misurato:

```
$ find . -name contracts.md -not -path "./dist/*" | wc -l
      45          # 44 copie vendorizzate + 1 sorgente (dev-flow/)
$ find ./dist -name contracts.md | wc -l
      45
```

Totale: **89 copie dello stesso file da 575 righe, più la sorgente** (90 file). Il prompt ne dichiara
82. `scripts/lint_skills.py:386` porta una nota che chiama questo numero «il conteggio delle copie del
contratto vendorizzato, non un conteggio di skill» — quindi il numero vive in almeno tre posti
(`audit-prompt.md`, il commento del linter, il filesystem) e due sono già invecchiati.

### 1.2 Nessuna divergenza di byte: tutte le 90 copie sono identiche

**nessun problema.** Misurato:

```
$ SRC=$(shasum -a 256 dev-flow/references/contracts.md | awk '{print $1}')
$ echo $SRC
1e381bf80f8db102c4c8d8c5e3e2f3ecd7498ee821cde3cae029ed6e4bdf1f00
$ find . -name contracts.md | while read f; do H=$(shasum -a 256 "$f" | awk '{print $1}');
    [ "$H" != "$SRC" ] && echo "DIVERGE: $f $H"; done
(nessun output)
```

**Zero divergenze.** Elenco delle divergenze richiesto dal prompt: vuoto.

### 1.3 L'identità è applicata da un controllo — ma il controllo non vede `dist/`

**rischio plausibile.**

Il controllo esiste ed è automatico: `scripts/lint_skills.py:770` `check_vendored_source()`, che scopre
le coppie con il glob di `scripts/lint_skills.py:766`:

```python
VENDORED_EVERYWHERE = [
    ("dev-flow/references/contracts.md", "*/references/contracts.md"),
]
```

`Path.glob("*/references/contracts.md")` risolve **un solo** componente di percorso. Misurato:

```
$ python3 -c "from pathlib import Path; root=Path('.')
print(len(list(root.glob('*/references/contracts.md'))))"
45
$ python3 -c "... len(list(root.glob('dist/agent-plugin/skills/*/references/contracts.md')))"
45
$ ... copie sotto dist/ catturate dal glob del linter: 0
```

Quindi il linter confronta **44 coppie** (45 match meno la canonica) e **nessuna delle 45 copie in
`dist/agent-plugin/skills/`**. Oggi sono identiche (misurato in §1.2), perciò non è un problema
dimostrato: è un meccanismo che può rompersi senza che nulla lo dica. Sono generate da
`scripts/build_agent_plugin.py` e ristaged dal gancio `.githooks/pre-commit` — ma il gancio è
`core.hooksPath`, cioè per-clone, quindi esiste solo dove qualcuno l'ha installato
(`.githooks/pre-commit`, riga di commento «Enable once per clone»).

**Intervento minimo** (una riga): aggiungere la coppia `("dev-flow/references/contracts.md",
"dist/agent-plugin/skills/*/references/contracts.md")` a `VENDORED_EVERYWHERE` in
`scripts/lint_skills.py:765`.

---

## 2. `stack.*` e fasi: regola → controllo | *non applicata*

Convenzioni della tabella:

- **rifiuta** = un gate che blocca il movimento di fase (`update_meta.py set-phase` /
  `append-history --phase-after`), cioè una regola *applicata*.
- **avvisa** = `show_state.py` lo stampa come `⚠` ma nulla si ferma: è prosa con un promemoria, non
  un'applicazione.
- ***non applicata*** = nessuno script nel repo guarda il valore.

Le 42 chiavi dichiarate nel contratto sono state estratte dalla §`stack` field
(`dev-flow/references/contracts.md:415`–`:467`) con
`grep -o '^- \`[a-z0-9_]*\`'`; il conteggio è confermato dallo script di rilevamento
(`stack keys declared in the contract: 42`).

### 2.1 Chiavi `stack.*`

| Chiave `stack.*` | Controllo | Dove |
|---|---|---|
| `framework` | **letta** per decidere l'applicabilità dei gate; **il valore non è mai validato** | `dev-flow/scripts/design_lint_gate.py:27`, `registry_intake_gate.py:25`, `wireframes_gate.py:19` — nessun enum. Vedi §2.3 |
| `ui` | letta per l'applicabilità; valore non validato | `design_lint_gate.py:20` (`TAILWIND_UIS`), `:31` |
| `ui_base` | *non applicata* | solo letta in `forms/scripts/scaffold_lib_forms.py`, `design-md-to-app/scripts/setup_design_lint.py` |
| `shadcn_preset` | *non applicata* — nessun file `.py` nel repo contiene la stringa | `grep -rln --include="*.py" "'shadcn_preset'" .` → nessun risultato |
| `base_color` | *non applicata* (e l'enum è sbagliato: §3.2) | idem |
| `ui_theme` | *non applicata* (e l'enum è sbagliato: §3.3) | idem |
| `icon_library` | *non applicata* | idem |
| `illustrations` | *non applicata* | idem |
| `data_residency` | **rifiuta** — ma solo all'attraversamento di `scaffolded` (§4.3); **avvisa** dopo | `dev-flow/scripts/data_residency_gate.py:24`; `update_meta.py:258`; `show_state.py:494` |
| `design_lint` | **rifiuta** all'attraversamento **e a ogni fase successiva** | `design_lint_gate.py:41`; `update_meta.py:265`, `:280` |
| `primitives_guard` | **rifiuta** a ogni fase ≥ `scaffolded` | `primitives_guard_gate.py:38`; `update_meta.py:274`–`:279` |
| `lint` | **avvisa** (enum + confronto col repository reale) | `show_state.py:524`–`:530`, `LINT_VALUES` a `:96`, `linters_present()` a `:99` |
| `registry_intake` | **rifiuta** — solo all'attraversamento di `scaffolded` (§4.3); **avvisa** dopo | `registry_intake_gate.py:33`; `update_meta.py:265` |
| `test` | **avvisa** (grammatica dei layer validata, non un elenco fisso) | `show_state.py:86` `test_layers_ok()`, `:513`–`:516` |
| `css_variables` | *non applicata* | nessun `.py` la nomina |
| `rtl` | *non applicata* | nessun `.py` la nomina |
| `auth` | *non applicata* (letta da `data_residency.py`, `research.py`, `compliance-audit/scripts/scan.py`; nessun enum) | — |
| `db` | *non applicata* | — |
| `payments` | *non applicata* — due progetti portano `polar`, uno `mock`, nessuno avvisa (§4.4) | — |
| `deploy` | *non applicata* | — |
| `storage` | *non applicata* | — |
| `realtime` | *non applicata* — nessun `.py` la nomina | — |
| `analytics` | *non applicata* (solo letta da `launch-audit/scripts/scan_launch.py`) | — |
| `analytics_provider` | *non applicata* (solo letta da `data_residency.py`) | — |
| `observability` | **avvisa** da `feature_complete` | `show_state.py`, `module-add/scripts/observability_check.py` |
| `observability_provider` | letta da `module-add/scripts/observability_check.py`; enum non validato | — |
| `cms` | *non applicata* | — |
| `push` | *non applicata* | — |
| `route_groups` | *non applicata* — nessun `.py` la nomina | — |
| `i18n` | ***non applicata*** — regola d'oro 2, e nessuno script la guarda (§4.2) | nessun `.py` nel repo contiene `'i18n'` come chiave di stack |
| `locales` | ***non applicata*** — idem | idem |
| `maps` | *non applicata* | — |
| `graphs` | *non applicata* | — |
| `shaders` | *non applicata* | — |
| `monorepo` (`monorepo.services`) | letta da `surfaces.py`, `design_lint_gate.py:29`; contenuto non validato | — |
| `canvas` | *non applicata* | — |
| `launch_audit` | letta da `debt_model.py`; non validata | — |
| `mcp` | *non applicata* | — |
| `pdf` | *non applicata* | — |
| `forms` | *non applicata* (letta da `scaffold_lib_forms.py`) | — |
| `agent` | letta per l'applicabilità di `registry_intake_gate.py:25`; valore non validato | — |
| `nextjs_version` | ***non applicata*** — il floor di sicurezza è prosa (§3.1, §4.5) | `vercel-deploy/SKILL.md:112`; `vercel-deploy/` non ha nessuno `scripts/` |

**Somma**: su 42 chiavi, **4 sono rifiutate** da un gate (`data_residency`, `design_lint`,
`primitives_guard`, `registry_intake`), **3 sono avvisate** (`lint`, `test`, `observability`), e
**35 non hanno nessun controllo sul valore**. Due delle quattro rifiutate lo sono solo
all'attraversamento (§4.3).

### 2.2 Fasi del ciclo di vita

| Fase | Controllo | Dove |
|---|---|---|
| appartenenza all'enum | **rifiuta** (entrambe le porte) | `update_meta.py:306`, `:378`; enum unico in `dev-flow/scripts/phases.py:17` |
| monotonicità | **rifiuta** (salvo `--allow-regress`) | `update_meta.py:323` |
| fase ignota = regressione invisibile | **rifiuta** | `update_meta.py:314`–`:318`, `unknown_phase_refusal()` a `:290` |
| alias kebab-case legacy | **normalizzati** | `phases.py:35` `ALIASES` |
| `empty → idea_captured` | nessun gate | — |
| `* → prd_drafted` | **rifiuta** (founder, poi inventory) | `update_meta.py:238`; `founder_gate.py:29`, `inventory_gate.py:15` |
| `* → tasks_split` | nessun gate | — |
| `* → design_extracted` | nessun gate | — |
| `* → monorepo_initialized` | **rifiuta** (wireframes) | `update_meta.py:215`, `wireframes_gate.py:22` |
| `* → scaffolded` | **rifiuta** (data-residency, design-lint, registry-intake, primitives-guard, wireframes) | `update_meta.py:257`–`:285` |
| ogni fase ≥ `scaffolded` | **rifiuta** (design-lint + primitives-guard, **non** data-residency né registry-intake) | `update_meta.py:274`–`:285`; misurato in §4.3 |
| `page_generated`, `module_added`, `feature_complete`, `deployed` | nessun gate proprio | — |
| «la fase non deve restare dietro al codice» (`contracts.md:360`) | **avvisa** | `show_state.py:467` — vedi §4.1, 6 progetti reali violano |
| `contract_version` più alto di quello noto | **rifiuta** (exit 2) | `meta_io.py:185`–`:189` |
| `meta_digest` non corrispondente (modifica a mano) | **avvisa** | `show_state.py:417`; `meta_io.py:66` |
| `phase` davanti a `checked_phase` | **rifiuta** (i gate ripartono da `checked_phase`) | `update_meta.py:83` `gate_baseline()`; **avvisa** in `show_state.py:421` |
| livelli di intervento 1–4 (`contracts.md:363`–`:414`) | ***non applicata*** — `spec_review.level` è registrato, nessuno script lo verifica; il contratto stesso dice a `:412` che «non blocca mai un cancello» | — |
| regola d'oro 1 (codice in inglese) | ***non applicata*** — dichiarato dal contratto stesso a `:24` | «review only» |
| regola d'oro 2 (i18n) | ***non applicata*** — dichiarato dal contratto a `:30`, confermato in §4.2 | — |
| regola d'oro 3 (primitive) | **rifiuta** + guard a write-time | `primitives_guard_gate.py`, `design_lint_gate.py` |
| convenzioni di cartella (`contracts.md:498`–`:509`: no `src/`, `_components/`, Rule of Three) | ***non applicata*** — 3 progetti reali hanno `src/` al root (§4.6) | nessuno script le verifica |

### 2.3 Un valore fuori enum in `stack.framework` spegne tre gate su quattro

**problema dimostrato.** È il riscontro più grave del giro.

`~/projects/agenticflow` è un'app Next 16 reale (`package.json`: `"next": "16.2.4"`, `src/app/page.tsx`
presente, `components.json`, `eslint.config.mjs`), fase `scaffolded`, e dichiara
`stack.framework = "next-app-router"` — un valore che **non è nell'enum del contratto**
(`contracts.md:419`: `"next" | "vite-react" | "remix" | "astro" | "sveltekit" | "expo-rn" |
"monorepo" | "agent" | string` — la coda `| string` lo rende formalmente legale, ed è esattamente il
problema).

Eseguito (sola lettura, nessuna scrittura in nessun `.workflow/`):

```
$ python3 - <<'PY'
import json, sys; from pathlib import Path
sys.path.insert(0,"/Users/lucadigerlando/my-skills/dev-flow/scripts")
import design_lint_gate, registry_intake_gate, primitives_guard_gate, wireframes_gate
m=json.loads(Path("/Users/lucadigerlando/projects/agenticflow/.workflow/meta.json").read_text())
r=Path("/Users/lucadigerlando/projects/agenticflow")
for n,g in (...): print(n, g.applies(m), g.verify(r,m))
PY
agenticflow: phase = scaffolded | stack.framework = next-app-router
  design_lint        applies=False  verify=(True, 'design lint not applicable to this stack')
  registry_intake    applies=False  verify=(True, 'registry intake not applicable to this stack')
  primitives_guard   applies=False  verify=(True, 'primitives guard not applicable to this stack')
  wireframes         applies=True   verify=(False, 'meta.json#wireframes is missing: ...')
```

La causa è `dev-flow/scripts/design_lint_gate.py:27`:

```python
    if fw not in {"next", "monorepo"}:
        return False
```

`registry_intake_gate.py:25` e `primitives_guard_gate.py:30` delegano allo stesso `applies`, quindi
**un refuso in una chiave stringa libera disattiva in silenzio tutta la regola d'oro 3 e il registry
intake**, e il gate lo riporta come «not applicable to this stack», che è un'affermazione falsa su
quel progetto.

E c'è un secondo strato: anche correggendo `framework` a `"next"` **nel dizionario passato al gate**,
il design-lint gate passa comunque, perché il verificatore interno rilegge `meta.json` **dal disco**:

```
same project with framework corrected to 'next':
  design_lint   applies=True  passes=True
      why=["✓ not applicable: stack.framework='next-app-router' — the design lint is for Next web apps"]
```

Cioè `setup_design_lint.py --check` si autoassolve leggendo il valore sbagliato dal file, ed esce 0.

Misura della diffusione (44 progetti con `.workflow/meta.json`): **13 valori fuori enum** su 9 chiavi,
nessuno dei quali produce un avviso (§4.4).

**Intervento minimo**: in `design_lint_gate.applies()`, al posto di `return False` per un `framework`
ignoto, restituire «applicabile» (o far emettere un rifiuto esplicito) quando il valore non è
nell'enum del contratto *e* il progetto ha un `package.json` con una dipendenza `next`. Alternativa
ancora più locale e verificabile da sola: aggiungere a `show_state.py`, accanto al controllo già
presente su `stack.lint` (`:524`), un avviso per ogni chiave di `stack` il cui valore non è nell'enum
del contratto — lo stesso meccanismo, esteso.

---

## 3. Affermazioni del contratto sugli strumenti esterni, verificate sull'artefatto pubblicato

Metodo: `npm pack` / tarball da `registry.npmjs.org`, lettura del `dist` e dei `.d.ts` spediti; per il
registry shadcn, l'indice servito. Mai la pagina che descrive lo strumento.

Artefatti letti: `shadcn@4.22.1`, `@shadcn/registry@0.2.0`, `@shadcn/lint@0.2.3`,
`registry.npmjs.org/next`, `https://ui.shadcn.com/r/index.json`.

### 3.1 «Next 16.3 è `latest` su npm» — falso oggi

**problema dimostrato.**

`contracts.md:467`: «**Next 16.3 è stable** (released 2026-08-03; `latest` on npm)».
`vercel-deploy/SKILL.md:120`: «`16.3.8` is both the newest `16.3.x` and the newest 16.x stable
(**it is `latest`**)».

```
$ curl -s https://registry.npmjs.org/next | python3 -c "..."
dist-tags: {... "backport": "15.5.28", "latest": "16.4.2", "canary": "16.5.0-canary.21"}
16.4 -> newest stable: 16.4.2  time: 2026-10-15T20:57:24Z
16.3 -> newest stable: 16.3.8  time: 2026-09-30T16:07:21Z
15.5 -> newest stable: 15.5.28  time: 2026-10-14T17:36:08Z
16.3.0 released 2026-08-03T20:34:17Z      ← questa parte del contratto è vera
16.4.0 released 2026-10-06T18:35:31Z
```

`latest` è **16.4.2**, non 16.3.x: il contratto è superato da 16 giorni (16.4.0, 2026-10-06). Anche il
floor dichiarato a `contracts.md:471` — «Security floor: `16.3.8` (Active LTS) or `15.5.27`
(Maintenance LTS)» — è superato sulla linea di manutenzione: **15.5.28** è uscito il 2026-10-14 ed è
il valore del dist-tag `backport`.

Aggravante documentale: `scripts/lint_skills.py:685` dice, nel commento del check 21, che questo
**è già successo** («contracts.md kept calling Next 16.3 `latest` after 16.4.0 shipped (AUDIT.md
§6.10)»). Il check 21 non lo riprende, perché il marcatore è datato `2026-10-03`, cioè 19 giorni, e
`STALE_DAYS = 60` (`scripts/lint_skills.py:688`). Confermato eseguendo il linter:

```
$ python3 scripts/lint_skills.py
→ Linting 56 skills…
· 19 note(s) — informational, do not fail the build:
  (tutte e 19 sono «description is NNN chars, close to the 1024 cap»)
✓ Clean (notes above).
```

Nessuna nota su `contracts.md`. Il repo contiene un solo aggiornatore automatico di versioni,
`scripts/refresh_stack_defaults.py`, e il suo elenco `PACKAGES` (riga 24) copre solo
Expo/React Native: `grep -n "contracts.md\|nextjs_version\|16\.3" scripts/refresh_stack_defaults.py`
non restituisce nulla. **Il floor di sicurezza di Next è prosa senza aggiornatore e senza
verificatore.**

### 3.2 L'enum `base_color` contiene due valori che shadcn non ha, e omette quattro che ha

**problema dimostrato.**

`contracts.md:427`: `base_color` (web, only when `ui="shadcn"`): `"neutral" | "gray" | "zinc" |
"stone" | "slate"`. Default `"neutral"`.

Dai `.d.ts` spediti in `@shadcn/registry@0.2.0`
(`package/dist/registry/constants.d.ts`), cioè la lista che `init` offre:

```
BASE_COLORS: readonly [
  "neutral", "zinc", "stone", "mauve", "olive", "mist", "taupe"
]
```

e dalla lista dei preset (`package/dist/preset/preset.d.ts`):

```
PRESET_BASE_COLORS: readonly ["neutral", "stone", "zinc", "gray", "mauve", "olive", "mist", "taupe"]
```

- **`"slate"` non esiste** in nessuna delle due liste.
- **`"gray"` non è tra i `BASE_COLORS`** di `init` (è solo un preset base color).
- **`mauve`, `olive`, `mist`, `taupe` mancano dal contratto.** `taupe` non è teorico: è il
  `baseColor` di due degli stili spediti (`sera`, `rhea`), quindi uno scaffold con quello stile non
  può registrare il proprio valore onesto. È la **quarta** istanza della classe di errore che il
  contratto stesso documenta due volte — per `icon_library`/`phosphor` (`:429`: «the enum could not
  express a value the toolchain itself chooses») e per `stack.test` (`:436`).

### 3.3 `ui_theme` registra uno *style*, non un *theme*, e ne conosce 5 degli 8 spediti

**problema dimostrato.**

`contracts.md:428`: `ui_theme` (web): `"vega" | "nova" | "maia" | "lyra" | "mira" | null`. «The
shadcn create starting theme».

Dagli artefatti spediti:

```
PRESET_STYLES: readonly ["nova", "vega", "maia", "lyra", "mira", "luma", "sera", "rhea"]
PRESET_THEMES: readonly ["neutral", "stone", "zinc", "gray", "amber", "blue", "cyan", "emerald",
  "fuchsia", "green", "indigo", "lime", "orange", "pink", "purple", "red", "rose", "sky", "teal",
  "violet", "yellow", "mauve", "olive", "mist", "taupe"]
```

E dalla tabella dei preset dentro `shadcn@4.22.1/dist/index.js`:

```
nova: {... style:"nova", baseColor:"neutral", theme:"neutral", iconLibrary:"lucide", ...}
lyra: {... style:"lyra", baseColor:"neutral", theme:"neutral", iconLibrary:"phosphor", ...}
sera: {... style:"sera", baseColor:"taupe",   theme:"taupe",   iconLibrary:"lucide", ...}
```

Due errori distinti:

1. **Il nome della chiave è sbagliato**: i cinque valori che il contratto chiama `ui_theme` sono
   l'asse `style` dello strumento; l'asse `theme` è un nome di colore e nei preset spediti vale
   `neutral` o `taupe`. Nessuno dei cinque valori del contratto è un elemento di `PRESET_THEMES`.
2. **Mancano `luma`, `sera`, `rhea`** (8 spediti, 5 dichiarati).

### 3.4 `icon_library`: `remixicon` manca, `radix-icons` non è un preset shadcn

**miglioramento facoltativo** (la chiave finisce con `| string`, quindi un valore onesto resta
registrabile).

`contracts.md:429`: `"lucide" | "radix-icons" | "tabler" | "hugeicons" | "phosphor" | string`.
Spedito: `PRESET_ICON_LIBRARIES: readonly ["lucide", "hugeicons", "tabler", "phosphor", "remixicon"]`.

### 3.5 «l'indice porta 61 voci `registry:ui`, e `trace`/`code-block` ne sono assenti» — già falso

**problema dimostrato.** È il precedente che il prompt d'audit cita a `docs/audit-prompt.md:70` come
esempio di verifica ben fatta: è decaduto in cinque giorni.

`contracts.md:34`: «verified 2026-10-17, the index carries 61 `registry:ui` items while `trace`,
`code-block` and `use-highlighted-code` install by name and are absent from it».

```
$ curl -s https://ui.shadcn.com/r/index.json | python3 -c "..."
total items in index: 65
Counter({'registry:ui': 65})
  'trace' in index: True
  'code-block' in index: True
  'use-highlighted-code' in index: False
  'typeset' in index: False
```

Misurato il **2026-10-22**: 65 voci, non 61; **`trace` e `code-block` sono ora nell'indice**. Resta
vero solo per `use-highlighted-code`. Fuori indice è anche `typeset`, che
`design-md-to-app/SKILL.md` nomina tra le cose che «`add --all` misses».

La conclusione operativa del contratto — «prima di scrivere un componente a mano, chiedi al registry
per nome (`shadcn view <name>`)» — **resta corretta e anzi più robusta della lista**. Il difetto è la
lista: tre nomi e un numero congelati in prosa, senza nulla che li rilegga.

### 3.6 Affermazioni verificate e **vere**

Elencate perché il prompt chiede di verificare, non di trovare colpe.

| Affermazione | Riga | Verifica sull'artefatto |
|---|---|---|
| `shadcn create --base` esiste | `:425` | `shadcn@4.22.1/dist/index.js`: `new Command().name("init").alias("create")` + `.option("-b, --base <base>")` — `create` è un alias di `init` |
| `ui_base` ∈ `radix \| base \| aria` | `:425` | `PRESET_BASES: readonly ["radix", "base", "aria"]` |
| `shadcn preset decode <code>` esiste | `:426` | comandi spediti: `preset` con sottocomandi `decode`, `apply`, `open`, `url` |
| `shadcn info --json` esiste | `:429` | `.name("info").description("get information about your project")` + `.option("--json")` |
| `--css-variables`, `--rtl` | `:437`, `:438` | `.option("--css-variables")`, `.option("--no-css-variables")`, `.option("--rtl")`, `.option("--no-rtl")` |
| `pnpm dlx shadcn@latest view <name>` | `:34` | `.name("view").description("view items from the registry")` |
| lo stile `lyra` spedisce `@phosphor-icons/react` | `:429` | `lyra: {description:"Phosphor / JetBrains Mono", iconLibrary:"phosphor"}`; `@phosphor-icons/react` latest **2.1.10**, license **MIT** — i due numeri citati dal contratto coincidono |
| `@shadcn/lint` è un plugin ESLint | `:64`, `:434` | `@shadcn/lint@0.2.3`, `peerDependencies: {"eslint": ">=9.30.0", "@typescript-eslint/parser": ">=8.40.0"}`, license MIT |
| `@xyflow/react` è MIT | `:60` | `@xyflow/react` latest 12.12.0, license MIT |

Verifica che **ho fatto e che ha evitato un falso positivo**: `@shadcn/lint@0.2.3` spedisce sei
regole, tutte `shadcn/*` (`no-arbitrary-values`, `no-inline-styles`, `no-raw-colors`, `no-restyle`,
`no-unknown-classes`, `require-static-classes`) e **nessuna `design/*`**. Sembrava che il contratto
appoggiasse la regola d'oro 3 su una regola inesistente — ma `design/no-handmade-ui` e
`design/no-card-in-card` sono nostre, generate da
`design-md-to-app/scripts/setup_design_lint.py:558` (`export const designPlugin = { rules: {
"no-card-in-card": cardInCard, "no-handmade-ui": handmade } }`). **L'affermazione del contratto è
corretta**; lo registro perché la via breve («il plugin upstream non ha quella regola») avrebbe
prodotto un riscontro falso.

### 3.7 Verifiche che **non** ho potuto eseguire

Dichiarate come richiede il vincolo 4, con il comando che servirebbe.

| Affermazione | Riga | Comando necessario |
|---|---|---|
| `next dev` mantiene il blocco `<!-- BEGIN:nextjs-agent-rules -->` in `AGENTS.md`/`CLAUDE.md`, e `agentRules: false` lo disattiva | `:12` | installare `next@16.4.2` in un progetto vuoto ed eseguire `next dev`, poi `grep -n 'BEGIN:nextjs-agent-rules' AGENTS.md CLAUDE.md`; per il flag, cercarlo nello schema di config spedito (`npm pack next@16.4.2 && grep -rn 'agentRules' package/dist`) |
| eve spedisce i suoi doc in `node_modules/eve/docs/` | `:12` | `npm pack eve@<versione installata>` e `tar tzf` per elencare `package/docs/` |
| i 9 + 2 + 8 CVE e i loro vincoli di applicabilità (`:471`–`:493`) | `:471`–`:493` | `gh api /repos/vercel/next.js/security-advisories` oppure l'OSV API per `npm:next`, confrontando `vulnerable_version_range` e `patched_versions` advisory per advisory |
| «CARTO default tiles need an Enterprise license for commercial use» (mapcn) | `:55` | leggere i termini CARTO; non è un artefatto pubblicato su npm |
| licenza Koboyo «forbids products where the art *is* the feature» | `:57` | pagina di licenza; non verificabile su un artefatto |
| `npx skills add firecrawl/anydoc` e `--ocr hosted` manda il documento intero a terzi | `:62` | clonare `firecrawl/anydoc` e leggere il percorso di `--ocr hosted` nel sorgente spedito |

---

## 4. Cinque (sei) progetti reali: stato dichiarato contro stato sul disco

Selezione: `bidmaster`, `agentos`, `eve-hospitality`, `illustrate`, `desko` — i cinque richiesti — più
`smart-travel`, incluso perché è il caso che il contratto stesso usa come lezione
(`contracts.md:37`, `:42`, `:360`). `annotix` **non è stato toccato** (altro agente al lavoro), e
**nessuna scrittura è avvenuta in nessun `.workflow/`**: tutte le letture via `json.loads` e
`shasum`, i gate invocati come funzioni Python con un root fittizio.

Il campione di 6 è stato poi esteso in sola lettura a **tutti i 44 progetti** con `.workflow/meta.json`
per quantificare, perché un riscontro su 5 progetti non distingue un caso da un andamento.

### 4.1 `phase` dietro al codice: 6 progetti, fino a 136 file di rotta

**problema dimostrato.**

`contracts.md:360`: «The phase must not fall behind the code. Routes in `app/` or components in
`components/` while `phase` is still before `scaffolded` / `page_generated` means **every check keyed
on the phase (spec-review, shadscan, the set-phase gates) is silently off**».

Misurato (conteggio di `app/**/page.tsx`, `src/app/**/page.tsx`, `apps/*/app/**/page.tsx`):

```
ski-ai-concierge:              phase=tasks_split        ma 3 file di rotta
smart-travel:                  phase=design_extracted   ma 128 file di rotta
smart-travel-g6-coordinatore:  phase=design_extracted   ma 134 file di rotta
smart-travel-g6-incentive:     phase=design_extracted   ma 136 file di rotta
smart-travel-g6-pagamenti:     phase=design_extracted   ma 130 file di rotta
smart-travel-parity-builder:   phase=design_extracted   ma 128 file di rotta
```

`smart-travel` — il progetto su cui il contratto ha scritto tre paragrafi il 2026-10-12 — **è ancora
in quello stato il 2026-10-22**, con 128 rotte a fase `design_extracted`, e la lezione si è
moltiplicata in altri quattro repo fratelli. `show_state.py:467` lo stampa come `⚠⚠ PHASE BEHIND THE
CODE`, ma un avviso che nessuno esegue non muove la fase: il riallineamento richiede che qualcuno
lanci `set-phase`, e nulla lo richiede.

### 4.2 Regola d'oro 2 (i18n): dichiarata «non negoziabile», registrata in meno della metà dei progetti

**problema dimostrato.**

`contracts.md:26`: «Every frontend ships i18n from day one... The minimum locale set is **English +
Italian**... Record both `stack.i18n` and `stack.locales` in `meta.json`». A `:30` il contratto
ammette già che il controllo è «the scaffold... then review» e che «No lint rule catches a hardcoded
string».

Misurato sui 43 progetti con un frontend (`framework` ∈ `next`, `monorepo`, `expo-rn`):

```
frontend projects: 43;  con stack.i18n valorizzato: 21;  con stack.locales valorizzato: 20
di quelli già a `scaffolded` o oltre: 36;  con i18n: 16
```

Nei 5 progetti del campione: `bidmaster` (15 rotte), `agentos` (19), `eve-hospitality` (21),
`illustrate` (9), `desko` (27) hanno **tutti** `i18n=None` e `locales=None`. Solo `smart-travel` li
registra (`next-intl`, `["en","it"]`).

Non è un difetto del gate: **non esiste un gate.** Nessun file `.py` del repo contiene `'i18n'` o
`'locales'` come chiave di stack (verificato con il grep corretto, con `--include` quotato dopo che
una prima versione con glob non quotato in zsh aveva restituito zero su ogni chiave — vedi il
monito a `docs/audit-prompt.md:94`; il controllo di sanità su una chiave che *so* esistere,
`design_lint`, dà 66 riscontri).

**Intervento minimo**: aggiungere a `show_state.py`, accanto ai controlli già presenti su
`stack.test` (`:513`) e `stack.lint` (`:524`), un avviso quando un progetto con un frontend è a
`scaffolded` o oltre con `stack.i18n` o `stack.locales` nulli. Un avviso, non un rifiuto: 36
progetti esistenti lo farebbero fallire in blocco.

### 4.3 I gate `data_residency` e `registry_intake` non si rieseguono mai dopo l'attraversamento

**problema dimostrato.** Eseguito tracciando quali `verify()` vengono effettivamente invocati, con
ogni gate sostituito da un registratore che ritorna «passa» (così tutti hanno la loro occasione);
nessun file scritto, nessun `.workflow/` creato:

```
eve-hospitality: phase = module_added
  stack.data_residency = None | registry_intake = None | design_lint = None | primitives_guard = None

  design_extracted   -> scaffolded         gates invocati: ['data_residency', 'design_lint',
                                                            'registry_intake', 'primitives_guard',
                                                            'wireframes']
  scaffolded         -> page_generated     gates invocati: ['design_lint', 'primitives_guard']
  module_added       -> feature_complete   gates invocati: ['design_lint', 'primitives_guard']
  feature_complete   -> deployed           gates invocati: ['design_lint', 'primitives_guard']
```

La causa è la condizione di attraversamento a `dev-flow/scripts/update_meta.py:258`
(`if cur_idx < scaffold_idx <= new_idx:`), contro la condizione «a ogni fase» a `:274`
(`if new_idx >= scaffold_idx:`). `design_lint` e `primitives_guard` stanno nel secondo blocco;
`data_residency` e `registry_intake` solo nel primo.

Conseguenza misurata sui 37 progetti già a `scaffolded` o oltre:

```
data_residency     nullo/assente in 28 di 37
registry_intake    nullo/assente in 28 di 37
design_lint        nullo/assente in 13 di 37
primitives_guard   nullo/assente in 35 di 37
```

Cioè: **28 progetti portano lo stato che il contratto dichiara rifiutato a `scaffolded`
(`contracts.md:431`, `:435`) e nessun movimento di fase lo riprenderà mai.** `show_state.py` lo
riporta — verificato eseguendolo su `eve-hospitality`, che stampa quattro blocchi `⚠ ... missing on a
scaffolded project` più la remediation — ma è un avviso, non un cancello.

Nota su `design_lint`/`primitives_guard`: quei due **sì** si rieseguono, ed è il motivo per cui 35
progetti su 37 senza `primitives_guard` verrebbero bloccati al prossimo `set-phase`. Il meccanismo
funziona dove è stato scritto per funzionare; il difetto è l'asimmetria tra i quattro gate dello
stesso attraversamento.

**Intervento minimo**: spostare `data_residency_gate` e `registry_intake_gate` dal blocco a `:258` al
blocco a `:274`, cioè dalla condizione di attraversamento a quella «≥ scaffolded», come già fatto il
2026-10-12 per il design lint. Due righe. Attenzione: questo bloccherebbe 28 progetti al prossimo
movimento di fase, perciò va fatto insieme alla scelta se quei 28 vanno retrofittati o opt-outati con
`stack_config.*_reason`.

### 4.4 Lo schema `stack` non è validato: 13 valori fuori enum e 45 chiavi non dichiarate

**problema dimostrato.**

Confronto in sola lettura degli enum della §`stack` field contro i 44 `meta.json` reali:

```
framework:  agenticflow        'next-app-router'        ← §2.3: spegne tre gate
ui:         my-agent-test      'tailwind-custom'
ui_base:    bottega            'base-ui'                 (l'enum è radix|base|aria)
auth:       conjure            'passport'
db:         agenticflow 'drizzle+neon+pgvector' · conjure 'neon' · vault-ai 'sqlite-drizzle'
payments:   conjure 'polar' · eve-hospitality 'polar' · flight-booking 'mock'
deploy:     desko 'tbd' · skybnb 'eas+vercel'
storage:    illustrate         'cloudflare-r2'
```

Nessuno di questi produce un errore o un avviso. Confermato eseguendo
`show_state.py /Users/lucadigerlando/projects/eve-hospitality`: la riga `Stack:` stampa
`payments=polar` senza commento, mentre lo stesso script avvisa correttamente su `stack.test` e
`stack.lint`, le due sole chiavi che hanno un validatore.

E al contrario — chiavi presenti sul disco che il contratto non dichiara (**44 nomi distinti** su 44
progetti), le più diffuse:

```
email                 10 progetti: agentic-orchestrator, archistudio, bidflow, desko, fit-coach, fit-room, …
motion                 6 progetti: bottega, fit-room, hostitaly, mockly, mockly-wt, video
project_management     5 progetti: smart-travel, smart-travel-g6-*, smart-travel-parity-builder
default_locale         4 progetti: archistudio, fit-coach, fit-room, streaming-hub
font                   3 · shadcn_style 3 · ci 2 · theme 2 · pwa 2 · next_cache_components 2 · …
stack_config           1 progetto: fit-coach  ← stack_config annidato DENTRO stack: è un errore di forma
```

Due osservazioni che rendono questo riscontro più di un disordine:

1. **`email` e `ci` sono le due chiavi non dichiarate più diffuse, e sono esattamente le due che il
   pacchetto pubblicato conosce.** `contract-package/src/dev_flow_contract/core.py:99`–`:108` definisce
   `@dataclass Stack` con dieci campi: `framework, ui, auth, db, payments, **email**, test, **ci**,
   storage, deploy`. `grep -n '^- \`email\`\|^- \`ci\`\|stack\.email\|stack\.ci'
   dev-flow/references/contracts.md` → **exit 1, nessun riscontro**. Quindi il modello pubblicato
   (`dev-flow-contract` 0.1.0, `contract-package/pyproject.toml` — che però **non è su PyPI**:
   `curl -o /dev/null -w '%{http_code}' https://pypi.org/pypi/dev-flow-contract/json` → `404`) e il documento
   canonico **non concordano in entrambe le direzioni**: il modello conosce 2 chiavi che il contratto
   non dichiara, e ignora 34 delle 42 che il contratto dichiara (manca tutto: `ui_base`, `i18n`,
   `locales`, `design_lint`, `primitives_guard`, `registry_intake`, `data_residency`, `agent`,
   `nextjs_version`, `forms`, …). Il salvataggio di campi ignoti è gestito dal campo `raw`
   (`core.py:151`), quindi non si perde nulla — ma la risposta alla domanda «quali chiavi ha `stack`?»
   dipende da quale dei due file si legge. **Il contratto non lo dice in un solo posto.**
2. `default_locale` su 4 progetti è una chiave che duplica la semantica di `locales[0]`
   (`contracts.md:453`: «first entry = default locale»): la stessa informazione in due posti, e una
   delle due copie può invecchiare da sola.

**Intervento minimo**: un controllo in `show_state.py` che stampi un avviso per ogni chiave di `stack`
non presente nell'elenco della §`stack` field, con l'elenco estratto una volta sola e condiviso
(è lo stesso meccanismo di `TEST_LAYERS` e `LINT_VALUES`, già lì). E, separatamente, allineare
`contract-package`'s `Stack`: aggiungere `email` e `ci` al contratto o rimuoverli dal dataclass.

### 4.5 Il floor di sicurezza di Next: 30 progetti su 35 sotto il valore dichiarato

**problema dimostrato.**

`contracts.md:494`: «`vercel-deploy` checks this floor before shipping». Misurato:
`ls vercel-deploy/` → `SKILL.md`, `references`. **Non esiste nessuno `scripts/`**, e
`grep -rln "registry.npmjs.org/next\|npm view next" --include="*.py" --include="*.sh" .` non
restituisce nulla. Il «check» è un'istruzione in prosa a `vercel-deploy/SKILL.md:112`.

`next` dichiarato nei `package.json` dei progetti (35 progetti):

```
16.4.2  streaming-hub                 16.3.6  fit-coach, ldglab
16.4.1  archistudio                   16.3.5  hostitaly
16.3.8  bidflow, skill-lint, voicepass 16.3.4  bottega(^), fit-room, mockly, mockly-wt,
                                               smart-travel, smart-travel-g6-* (3), parity-builder,
                                               fx-harness-test
16.3.0-preview.6  familyboard
16.2.12 bug-triage, ski-ai-concierge, dev-flow-docs(^), my-agent-test(^)
16.2.10 studio   16.2.9 eve-hospitality   16.2.7 illustrate   16.2.6 design-md-studio
16.2.4  agentic-orchestrator, agenticflow, constellation, dataviz, idea-validator,
        notarius-crm, perf-gym, predictions-league, wisely
```

Contro il floor dichiarato di `16.3.8`: **5 progetti lo rispettano** (16.3.8 ×3, 16.4.1, 16.4.2) e
**30 sono sotto**, di cui **16 sulla linea 16.2.x** che il contratto stesso a `:469` descrive come
«now unpatched» perché non ha ricevuto la patch di agosto. `eve-hospitality` è a `16.2.9`, cioè sotto
anche l'ultima 16.2 esistente (`16.2.12`).

Non classifico la vulnerabilità effettiva (servirebbe l'analisi advisory-per-advisory del §3.7). Il
riscontro dimostrato è più semplice e più solido: **un floor dichiarato in prosa, letto dal 14% dei
progetti, con zero verificatori eseguibili nel repo.**

### 4.6 Convenzioni di cartella: `src/` su 3 progetti

**problema dimostrato** (minore).

`contracts.md:506`: «**No `src/` directory**: code lives at project root». Misurato:
`agenticflow`, `idea-validator`, `streaming-hub` hanno `src/` al root con un `.workflow/meta.json`.
`agenticflow` ha la sua unica pagina in `src/app/page.tsx`. Nessuno script verifica la convenzione; va
detto che il conteggio delle rotte di `show_state.py` e il mio probe gestiscono entrambi `src/app`,
quindi la deviazione è tollerata dagli strumenti e solo vietata dal documento.

### 4.7 `contract_version` e `meta_digest` assenti in 40 progetti su 44

**rischio plausibile**, con una conseguenza concreta.

```
contract_version valorizzato:  4 di 44
meta_digest presente:          4 di 44
blocco inventory:              9 di 44
blocco wireframes:             7 di 44
```

I 6 progetti del campione sono tutti senza digest (`meta_digest: ABSENT`). Il contratto lo prevede
(`:573`: «A file without the field predates it and is trusted as it is until its next write») e
`meta_io.checked_phase()` (`meta_io.py:72`) ripiega su `meta.get("phase")`. Il risultato è che
`gate_baseline()` (`update_meta.py:83`) non ha nulla da cui ripartire: la difesa contro una fase
scritta a mano — introdotta per AUDIT.md P1-33 — è **inerte su 40 progetti su 44**, e lo resterà
fino alla loro prossima scrittura via script. Non lo classifico come dimostrato perché non ho
eseguito l'aggiramento (richiederebbe scrivere in un `.workflow/`, escluso dai limiti).

**Comando che servirebbe** per dimostrarlo: copiare un `meta.json` senza digest in una radice
monouso, portare `phase` a `module_added` a mano, poi
`python3 dev-flow/scripts/update_meta.py <root> set-phase feature_complete` e osservare se i gate di
`scaffolded` vengono saltati.

### 4.8 Deriva degli `artifacts`: 15 voci su 37 non corrispondono al disco

**problema dimostrato** (atteso dal progetto, non un difetto del codice).

Hash ricalcolati sui file registrati in `meta.json#artifacts`:

| Progetto | registrati | self-drift | mancanti sul disco |
|---|---|---|---|
| bidmaster | 2 | 1 (`.workflow/PROMPT.md`) | 0 |
| agentos | 9 | 3 (`packages/ui/src/styles/globals.css`, `_design-md-mapping.json`, `packages/database/src/schema/index.ts`) | 0 |
| eve-hospitality | 14 | 6 | **2** (`apps/web/app/globals.css`, `apps/web/app/showcase/page.tsx`) |
| illustrate | 4 | 1 | 0 |
| desko | 3 | 0 | 0 |
| smart-travel | 5 | 4 (`PRD.md`, `tasks.md`, `DESIGN.md`, `docs/wireframes/screen-inventory.md`) | 0 |

Il contratto (`:178`) dice che `check_drift.py` è «diagnostic only, never mutating», quindi la deriva
è per progetto, non un bug. Il dato utile è il **tasso**: 15 su 37 artefatti registrati non
corrispondono, e su `smart-travel` i quattro derivati sono proprio i documenti su cui poggiano
l'inventario wireframe approvato (174 schermi, 768 artboard) e il gate che lo ha fatto passare —
cioè l'approvazione registrata copre una versione di `screen-inventory.md` che non è più quella sul
disco.

---

## 5. Riepilogo per categoria

**problema dimostrato (10)**

1. §2.3 — `stack.framework = "next-app-router"` su `agenticflow` disattiva in silenzio design-lint,
   registry-intake e primitives-guard; il verificatore interno si autoassolve rileggendo il valore
   sbagliato dal disco ed esce 0.
2. §4.3 — `data_residency` e `registry_intake` sono gate solo-attraversamento: 28 progetti su 37
   oltre `scaffolded` restano nello stato che il contratto dichiara rifiutato, per sempre.
3. §3.1 — «Next 16.3 è `latest` su npm» (`contracts.md:467`, `vercel-deploy/SKILL.md:120`) è falso:
   `latest` = 16.4.2; e `15.5.27` è superato da `15.5.28`. Il commento del check 21 dice che è già
   successo una volta.
4. §4.5 — 30 progetti su 35 sotto il floor `16.3.8`, e `vercel-deploy` non ha nessuno script per
   verificarlo.
5. §3.2 — `base_color`: `slate` non esiste in shadcn, `gray` non è tra i `BASE_COLORS` di `init`,
   mancano `mauve/olive/mist/taupe` (e `taupe` è il base color di due stili spediti).
6. §3.3 — `ui_theme` registra l'asse `style` sotto il nome `theme`, e ne conosce 5 degli 8 spediti.
7. §3.5 — «61 voci, `trace`/`code-block` assenti dall'indice» è già falso: 65 voci, e quei due ci
   sono.
8. §4.1 — 6 progetti con la fase dietro al codice, fino a 136 rotte; `smart-travel` è ancora lì
   dieci giorni dopo il paragrafo che lo cita.
9. §4.2 — regola d'oro 2: `stack.i18n` valorizzato in 16 dei 36 progetti frontend oltre
   `scaffolded`, e nessuno script la guarda.
10. §4.4 — nessuna validazione dello schema `stack`: 13 valori fuori enum, 44 nomi di chiave non
    dichiarati, e `contract-package`'s `Stack` discorda col contratto in entrambe le direzioni
    (`email`/`ci` non dichiarate; 34 chiavi dichiarate assenti dal modello).

*(Minori, nello stesso registro: §1.1 il conteggio «41» è 44+45; §4.6 `src/` su 3 progetti;
§4.8 15 artefatti su 37 derivati.)*

**rischio plausibile (2)**

1. §1.3 — le 45 copie di `contracts.md` sotto `dist/` non sono coperte dal controllo di identità
   (il glob risolve un solo componente). Oggi identiche; nulla lo garantirebbe domani.
2. §4.7 — `meta_digest` assente in 40 progetti su 44 rende inerte la difesa di `gate_baseline()`
   contro una fase scritta a mano. Non dimostrato: il comando per dimostrarlo è in §4.7.

**miglioramento facoltativo (3)**

1. §3.4 — `icon_library`: aggiungere `remixicon`, togliere o annotare `radix-icons`.
2. §4.4 — `default_locale` su 4 progetti duplica `locales[0]`: una sola casa.
3. §3.5 — la lista di nomi fuori indice (`trace`, `code-block`, `use-highlighted-code`, `typeset`)
   invecchia da sola; la regola operativa accanto («chiedi al registry per nome») non invecchia. Si
   può togliere la lista e tenere la regola.

**preferenza personale (1)**

1. La §`nextjs_version` è lunga 28 righe e per tre quarti è un bollettino CVE storico dentro il
   documento che definisce uno schema di dati. Lo trovo fuori posto — ma funziona, e il contratto
   motiva esplicitamente la scelta a `:478` («each is neutralised by a rule this contract already
   imposes»). Lo dico e passo oltre.

---

## 6. La risposta alla domanda del giro

**Il contratto dice il vero?** Nelle parti meccaniche sì, e con una precisione che le verifiche
sull'artefatto confermano riga per riga (§3.6: nove affermazioni su comandi e flag shadcn, tutte
vere, incluse due che sembravano sbagliate). Nelle parti datate no: le tre affermazioni più recenti
su strumenti esterni — `latest` di Next, il conteggio dell'indice shadcn, gli enum di `base_color` e
`ui_theme` — sono tutte scadute o sbagliate, e tutte e tre erano verificabili con un comando.
Il contratto conosce il problema (`:14` «the `dist` states the behaviour», `:469` «don't cache them»,
`:15` «Stale docs-grounding is a bug») e non ha nessuno strumento che applichi quella consapevolezza:
`refresh_stack_defaults.py` copre solo Expo/RN, e il check 21 ha una soglia di 60 giorni mentre
questi fatti si rompono in 5.

**Lo dice in un solo posto?** Per `contracts.md` sì, e lo dice byte per byte: 89 copie identiche, con
un controllo automatico che ne verifica 44. Ma **la domanda «quali chiavi ha `stack`, e quali valori
ammettono» ha tre risposte diverse** nel repo — la §`stack` field (42 chiavi, enum in prosa),
`contract-package`'s `Stack` (10 campi, nessun enum, 2 chiavi che il contratto non dichiara), e i 44
`meta.json` reali (44 nomi non dichiarati, 13 valori fuori enum) — e nessuna delle tre è confrontata
con le altre da un controllo.

Il tema unico di tutti i dieci problemi dimostrati: **dove c'è uno script, la regola tiene** (fasi,
monotonicità, digest, design-lint, primitives-guard, identità delle copie); **dove c'è solo prosa, il
disco se ne va per conto suo**, e la distanza fra documento e disco si misura in decine di progetti.
