# Design — Set di skill "React Native + Expo" per `~/my-skills/`

**Data**: 2026-05-16
**Autore**: brainstorming Luca + Claude
**Stato**: draft → da approvare prima di passare a `writing-plans`

---

## 1. Obiettivo

Creare un set di skill nel formato standard (`~/my-skills/<name>/SKILL.md`) che istruisca qualunque agente Claude Code a sviluppare applicazioni React Native + Expo seguendo un insieme opinionato di best practice, riducendo l'errore e il drift verso pattern obsoleti. Il set rispecchia per lo stack RN/Expo ciò che la famiglia di skill esistenti (`design-md-to-app`, `module-add`, `screenshot-to-page`, ecc.) fa per Next.js, *senza modificare* le skill Next.js esistenti.

Fonte autorevole di partenza: corso gratuito **"React Native for Beginners"** su [codewithbeto.dev/rnCourse](https://codewithbeto.dev/rnCourse/whatIsReactNative) (12 lezioni gratuite + 4 lezioni gratuite sparse in moduli avanzati). I moduli a pagamento (Components/APIs, Style and Design, gran parte di Expo Router, Animations, Testing, Backend, Supabase, EAS, Publishing/Payments) sono **non accessibili** via `WebFetch`: per quelle aree usiamo come fonte canonica le **docs ufficiali** dei rispettivi tool (Expo, NativeWind, TanStack Query, Reanimated, Gesture Handler, Supabase, RevenueCat, Maestro, ecc.).

## 2. Decisioni chiave fissate durante il brainstorming

1. **Tipo di skill**: knowledge + guardrail, formato standard `SKILL.md` con frontmatter — non genera codice arbitrario, indirizza l'agente a fare la cosa giusta.
2. **Relazione con `dev-flow`**: Mix — il `dev-flow` esistente viene esteso *minimamente* per smistare anche su `stack="expo-rn"`, e in parallelo nasce una famiglia di skill `rn-*` indipendente dal `dev-flow` (usabile anche su progetti RN già esistenti).
3. **Scoping fonti**: gratuito del corso + docs ufficiali, con marcatura `> Source:` in ogni file references. Niente blog post o video di terzi.
4. **Granularità**: 10 skill knowledge (≈ una per modulo del corso) + 5 skill operative (scaffold, add-screen, module-add, write-tests, eas-deploy).
5. **Famiglia operativa parallela**: skill `rn-*` operative *nuove*, le skill Next.js esistenti non vengono toccate (zero rischio di regressione).
6. **Stack opinionato**: Expo SDK ultima stabile, TypeScript, Expo Router, NativeWind v4, Zustand (+ Context per cross-cutting), TanStack Query, Reanimated 3 + Gesture Handler, Supabase (auth/DB/storage/realtime), EAS Build/Submit/Update, Jest + React Native Testing Library + Maestro.
7. **Profondità references**: "Deep selettivo" — le 4 skill core (`rn-fundamentals`, `rn-styling`, `rn-expo-router`, `rn-data-fetching`) hanno `concepts.md` + `patterns.md` + cartella `examples/` con snippet `.tsx`. Le altre 6 knowledge restano lean (`patterns.md` + `setup.md` o `decision-tree.md`).

## 3. Architettura del set

```
~/my-skills/
├── (skill Next.js esistenti — invariate)
├── dev-flow/                           ← orchestratore (estensione minima)
│   └── references/
│       ├── contracts.md
│       └── stack-expo-rn.md            ← NUOVO: stack definition + routing RN
│
├── rn-fundamentals/             ┐
├── rn-components-apis/          │
├── rn-styling/                  │
├── rn-expo-router/              │
├── rn-data-fetching/            │ FAMIGLIA KNOWLEDGE (10) — guardrail
├── rn-animations-gestures/      │ di conoscenza, auto-invocabili anche
├── rn-push-notifications/       │ fuori dal dev-flow
├── rn-backend-supabase/         │
├── rn-eas-build-submit-update/  │
├── rn-publishing-payments/      ┘
│
├── rn-bootstrap/                ┐
├── rn-add-screen/               │
├── rn-module-add/               │ FAMIGLIA OPERATIVA (5) — invocate
├── rn-write-tests/              │ dal dev-flow in fase scaffold/build/ship
└── rn-eas-deploy/               ┘
```

**Interazione tra famiglie**

- Skill operative *consumano* skill knowledge: il `SKILL.md` operativo elenca esplicitamente nella sezione "Sources of truth (knowledge dependencies)" le skill knowledge da consultare, e nei singoli step di workflow rimanda a `references/*.md` di quelle skill (es. lo step "wire NativeWind" di `rn-bootstrap` rimanda a `~/my-skills/rn-styling/references/nativewind-setup.md`). Non c'è un meccanismo runtime di "import": è auto-istruzione testuale che l'agente segue leggendo i file.
- `dev-flow` instrada in base a `meta.json#stack`:
  - `stack == "nextjs"` (o assente) → famiglia esistente
  - `stack == "expo-rn"` → famiglia `rn-*` operativa

**Cosa NON facciamo** (YAGNI esplicito):
- niente modifica alle skill Next.js (`design-md-to-app`, `module-add`, `screenshot-to-page`, `setup-deploy`, `write-tests`)
- niente skill "umbrella" unica
- niente skill granulari per ogni lezione del corso

## 4. Inventario delle 15 skill

### Famiglia KNOWLEDGE (10)

| # | Name | Quando si attiva | Profondità | Dipende da |
|---|---|---|---|---|
| K1 | `rn-fundamentals` | Inizio di qualunque task RN/Expo, scelta architettura, "come si fa X in RN", concetti base (bridge, Fabric, New Architecture, Hermes), differenze con web | **deep** | — |
| K2 | `rn-components-apis` | Uso di componenti core RN (`View`, `Text`, `ScrollView`, `FlatList`, `TextInput`, `Pressable`, `Modal`, `KeyboardAvoidingView`, `SafeAreaView`) o API platform (`Platform`, `Dimensions`, `Linking`, `AppState`) | lean | K1 |
| K3 | `rn-styling` | Stile, layout, NativeWind/Tailwind in RN, Flexbox RN, responsive, dark mode, safe area, design tokens da DESIGN.md, immagini ottimizzate (`expo-image`) | **deep** | K1 |
| K4 | `rn-expo-router` | Navigazione, routing file-based, layouts, tabs/stack/drawer, deep linking, typed routes, modal, search params | **deep** | K1, K2 |
| K5 | `rn-data-fetching` | Chiamate API, fetch, TanStack Query, cache, mutations, optimistic updates, gestione errori/loading, paginazione, infinite scroll | **deep** | K1 |
| K6 | `rn-animations-gestures` | Animazioni con Reanimated 3, worklets, shared values, layout animations, Gesture Handler (pan/pinch/long-press), transizioni | lean | K1, K2 |
| K7 | `rn-push-notifications` | Push notifications con `expo-notifications`, permessi, token APNs/FCM, payload, deep link da notifica, server-side trigger | lean | K1, K9 |
| K8 | `rn-backend-supabase` | Auth (email/oauth/magic link), Postgres + RLS, storage, realtime, edge functions, client setup `@supabase/supabase-js` su RN | lean | K1, K5 |
| K9 | `rn-eas-build-submit-update` | Build cloud con EAS, profili (dev/preview/prod), credenziali, EAS Submit, EAS Update OTA, EAS Workflows CI | lean | K1 |
| K10 | `rn-publishing-payments` | Pubblicazione su App Store + Play Store, screenshots, metadata, IAP (RevenueCat), Stripe (solo web view, rispetto policy) | lean | K1, K9 |

### Famiglia OPERATIVA (5)

| # | Name | Quando si attiva | Cosa fa | Consulta knowledge |
|---|---|---|---|---|
| O1 | `rn-bootstrap` | Phase `prd_drafted` con `stack="expo-rn"` | `create-expo-app` + TS + NativeWind + Zustand + TanStack Query + Expo Router + struttura cartelle + ESLint/Prettier + `.env.example` + `tailwind.config.js` da DESIGN.md | K1, K3, K4 |
| O2 | `rn-add-screen` | Phase `>= scaffolded`. "Aggiungi schermata X", screenshot → schermata | Crea route in `app/`, layout, componenti, applica NativeWind dai tokens, scaffolda data layer (query/mutation), validazione form | K2, K3, K4, K5 |
| O3 | `rn-module-add` | "Aggiungi auth/db/payments/push/storage/realtime" | Sub-moduli: `auth` (Supabase + expo-auth-session), `db` (Supabase + tipi generati), `storage` (Supabase Storage o expo-image-picker), `payments` (RevenueCat o Stripe via WebView), `push` (expo-notifications + endpoint), `realtime` (Supabase Realtime). Aggiorna `meta.json#stack_config` | K7, K8 |
| O4 | `rn-write-tests` | "Scrivi test per X" | Jest + RNTL per unit/integration, Maestro per e2e, mocking di Expo modules, snapshot solo per design system | K1, K3 |
| O5 | `rn-eas-deploy` | Phase `feature_complete` | Inizializza `eas.json`, profili, credenziali, build preview→production, OTA via EAS Update, prepara metadata store | K9, K10 |

## 5. Anatomia di una skill (template)

### 5.1 Template KNOWLEDGE — esempio `rn-styling/`

```
rn-styling/
├── SKILL.md
└── references/
    ├── concepts.md            ← (solo deep) Flexbox RN, unità, safe-area, dark mode
    ├── patterns.md            ← pattern raccomandati + anti-pattern noti
    ├── nativewind-setup.md    ← installazione + tailwind.config.js + provider
    ├── decision-tree.md       ← quando StyleSheet vs NativeWind vs inline
    └── examples/              ← (solo deep) snippet TS pronti
        ├── responsive-card.tsx
        ├── dark-mode-toggle.tsx
        └── safe-area-layout.tsx
```

Shape minimo del `SKILL.md`:

```markdown
---
name: rn-styling
description: 'Use when styling React Native / Expo components, configuring
  NativeWind/Tailwind, dealing with Flexbox layout, safe-area insets, dark mode,
  responsive design, or wiring DESIGN.md tokens into a tailwind.config. Triggers
  on: "style this screen", "add dark mode", "fix safe area", "import design
  tokens", or when an agent is about to write StyleSheet/className in an RN
  project. Not for: building screens end-to-end (rn-add-screen), animations
  (rn-animations-gestures), or non-RN web styling.'
---

# rn-styling — guardrail per styling in React Native + Expo

## What this skill enforces (the 5 rules)
1. NativeWind v4 è il default; StyleSheet vanilla solo per perf-critical.
2. Mai valori arbitrari hardcoded — sempre da `tailwind.config.js` (tokens).
3. SafeArea obbligatorio sui root screen.
4. Dark mode via `useColorScheme` + Tailwind `dark:` variant.
5. ...

## Quick decision tree
- "stilare un componente nuovo" → references/decision-tree.md
- "configurare NativeWind da zero" → references/nativewind-setup.md
- "capire perché Flexbox si comporta diversamente" → references/concepts.md

## Common anti-patterns (NEVER do)
- ❌ `style={{ padding: 16 }}` con magic number → usa token
- ❌ `View` come root senza `SafeAreaView` su iOS
- ❌ Importare `tailwindcss` direttamente

## Sources
- Lezione 10 "Styling Your App" — codewithbeto.dev (free)
- Expo docs: https://docs.expo.dev/develop/user-interface/styling/
- NativeWind v4 docs: https://www.nativewind.dev/
```

### 5.2 Template OPERATIVA — esempio `rn-bootstrap/`

```
rn-bootstrap/
├── SKILL.md
├── references/
│   ├── contracts.md             ← vendored dal dev-flow
│   ├── stack-defaults.md        ← versioni esatte (Expo SDK, Reanimated, ecc.)
│   └── post-bootstrap-checklist.md
└── scripts/
    ├── init-expo-app.sh         ← create-expo-app + clear template
    ├── install-stack.sh         ← NativeWind, Zustand, TanStack Query, Reanimated
    ├── wire-nativewind.ts       ← genera tailwind.config.js da DESIGN.md
    └── verify.ts                ← post-install verification
```

Shape minimo del `SKILL.md`:

```markdown
---
name: rn-bootstrap
description: 'Scaffold a new Expo + React Native app from a PROJECT.md +
  PRD.md + DESIGN.md, using the opinionated stack (Expo Router, TypeScript,
  NativeWind, Zustand, TanStack Query, Reanimated 3). Reads .workflow/meta.json
  with stack="expo-rn" and phase="prd_drafted" or "design_finalized", produces
  a running Expo app at the project root, bumps phase to "scaffolded". Always
  idempotent. Use when the orchestrator routes here from prd_drafted with the
  RN stack, or the user says "scaffolda app expo", "create RN app from PRD".
  Not for: adding screens (rn-add-screen), modules (rn-module-add), or
  Next.js scaffolding (design-md-to-app).'
---

# rn-bootstrap — scaffold Expo + RN da PRD/DESIGN

## Contract
See references/contracts.md. Key facts:
- Reads .workflow/meta.json#stack — must be "expo-rn"
- Reads PROJECT.md, PRD.md, DESIGN.md from project root
- Writes app to project root, sets phase = "scaffolded"
- Idempotent: re-running detects existing files, skips, reports

## Workflow
### Step 1 — Verify preconditions
### Step 2 — Run create-expo-app
### Step 3 — Install opinionated stack
### Step 4 — Wire NativeWind from DESIGN.md tokens
### Step 5 — Generate folder structure + boilerplate
### Step 6 — Verify (scripts/verify.ts)
### Step 7 — Update meta.json + commit

## Sources of truth (knowledge dependencies)
- rn-fundamentals (Expo SDK choice, New Architecture status)
- rn-styling (NativeWind setup)
- rn-expo-router (folder layout, initial route)
```

### 5.3 Convenzioni comuni

- **Lingua**: inglese (frontmatter + contenuto), come tutte le skill esistenti.
- **Frontmatter tono**: imperativo + lista trigger naturali + `Not for:` per disambiguare verso skill adiacenti (pattern usato in `module-add` e `dev-flow`).
- **Fonti marcate sempre**: ogni `references/*.md` ha in testa `> Source: corso codewithbeto.dev lezione X (free) | docs Expo | docs NativeWind`.
- **Skill "deep" (K1, K3, K4, K5)**: cartella `examples/` con file `.tsx` reali compilabili.
- **Skill "lean" (K2, K6, K7, K8, K9, K10)**: solo `patterns.md` + 1 `setup.md` o `decision-tree.md`.

## 6. Mapping fonti → skill

Legenda: 🆓 lezione gratuita codewithbeto · 💰 lezione a pagamento (sostituita da docs) · 📘 docs ufficiali · ⚙️ scelta opinionata del set

| Skill | Corso (free) | Corso (paid → docs) | Docs ufficiali | Opinionato |
|---|---|---|---|---|
| K1 `rn-fundamentals` | 🆓 1,2,3,5,6,12 + "Introduction" (free) | 💰 Native Modules basics | 📘 reactnative.dev, 📘 docs.expo.dev | ⚙️ Expo SDK ultima + New Architecture ON |
| K2 `rn-components-apis` | 🆓 (in 5,7,8,9) | 💰 "Components and APIs" | 📘 reactnative.dev/docs/components-and-apis | ⚙️ `expo-image` su `Image`, `FlashList` su `FlatList` per liste lunghe |
| K3 `rn-styling` | 🆓 10 "Styling Your App" | 💰 "Style and Design" | 📘 nativewind.dev v4, 📘 docs.expo.dev styling, 📘 react-native-safe-area-context | ⚙️ NativeWind v4 default + token da DESIGN.md |
| K4 `rn-expo-router` | 🆓 11 "Navigation Basics" + 1 free Expo Router | 💰 resto modulo | 📘 docs.expo.dev/router | ⚙️ typed routes ON, no react-navigation diretto |
| K5 `rn-data-fetching` | 🆓 7 + 8 | — | 📘 tanstack.com/query, 📘 docs.expo.dev networking | ⚙️ TanStack Query default; fetch+useEffect solo didattico |
| K6 `rn-animations-gestures` | 🆓 — | 💰 "Animations & Gestures" | 📘 docs.swmansion.com/react-native-reanimated/v3, 📘 docs.swmansion.com/react-native-gesture-handler | ⚙️ Reanimated 3 + RNGH 2, no Animated API legacy |
| K7 `rn-push-notifications` | 🆓 1 free Push Notifications | 💰 resto | 📘 docs.expo.dev/push-notifications | ⚙️ Expo push per dev/test, APNs/FCM diretti per prod |
| K8 `rn-backend-supabase` | 🆓 — | 💰 "Backend Basics" + "Supabase" | 📘 supabase.com/docs | ⚙️ Supabase default backend; tipi via `supabase gen types typescript` |
| K9 `rn-eas-build-submit-update` | 🆓 — | 💰 moduli EAS | 📘 docs.expo.dev/eas, 📘 docs.expo.dev/eas-update | ⚙️ profili `development`/`preview`/`production`, OTA solo per fix JS-only |
| K10 `rn-publishing-payments` | 🆓 — | 💰 "Publishing, Payments, Native Modules" | 📘 App Store Connect, 📘 Play Console, 📘 RevenueCat, 📘 Stripe in-app | ⚙️ RevenueCat per IAP; Stripe solo per servizi non-digital |

Skill operative (O1–O5) ereditano dalle knowledge che consumano.

**Principio**: nessuna fonte non-ufficiale. Solo corso (cosa è gratuito) + docs ufficiali della libreria. Set difendibile e aggiornabile.

## 7. Estensione `dev-flow`

Modifiche minime al `dev-flow` esistente.

### 7.1 `dev-flow/SKILL.md` — tabella di routing estesa

| Phase | Stack | Next skill |
|---|---|---|
| `prd_drafted` | `nextjs` (o assente) | `design-md-to-app` |
| `prd_drafted` | `expo-rn` | **`rn-bootstrap`** |
| `scaffolded` | `nextjs` | `module-add` / `screenshot-to-page` |
| `scaffolded` | `expo-rn` | **`rn-module-add`** / **`rn-add-screen`** |
| `feature_complete` | `nextjs` | `setup-deploy` |
| `feature_complete` | `expo-rn` | **`rn-eas-deploy`** |

### 7.2 `dev-flow/references/stack-expo-rn.md` — NUOVO

Contiene:
- Valore esatto: `stack = "expo-rn"`
- Lista skill operative della famiglia
- Sotto-chiavi attese in `meta.json#stack_config`: `expo_sdk`, `nativewind` (bool), `state_lib`, `backend`, `payments_lib`, ecc.
- Dipendenze inter-skill (chi consuma quale knowledge)

### 7.3 `prd-from-idea` — UNA domanda in più

Durante la discovery: "Target: web/mobile/desktop?". Se mobile, setta `stack="expo-rn"` in `meta.json`. Niente altro cambia.

### 7.4 `prd-to-tasks` — invariata

Stack-agnostica.

## 8. Ordine di build (3 wave)

> **Nota di scoping per `writing-plans`**: il primo piano implementativo coprirà **solo Wave 1** (MVP). Wave 2 e Wave 3 saranno oggetto di piani successivi, generati una volta che Wave 1 è verificato in produzione. Questo evita un piano da 15+ task tutto in una volta e permette di iterare sul template (template knowledge / template operativa) prima di scalare.


### Wave 1 — MVP (~giornata 1-3)
*Minimo set per scaffoldare un'app RN funzionante*

1. `rn-fundamentals` (K1)
2. `rn-styling` (K3)
3. `rn-expo-router` (K4)
4. `rn-bootstrap` (O1)
5. Modifiche a `dev-flow` + `stack-expo-rn.md` + `prd-from-idea`

✅ End-state Wave 1: da `PRD.md` + `DESIGN.md` si ottiene un'app Expo che gira, stilata coi token, con routing impostato.

### Wave 2 — Feature loop (~giornata 4-7)

6. `rn-components-apis` (K2)
7. `rn-data-fetching` (K5)
8. `rn-add-screen` (O2)
9. `rn-write-tests` (O4)

✅ End-state Wave 2: ciclo aggiungi-schermata + dati + test completo.

### Wave 3 — Backend, native, ship (~giornata 8-12)

10. `rn-backend-supabase` (K8)
11. `rn-animations-gestures` (K6)
12. `rn-push-notifications` (K7)
13. `rn-module-add` (O3)
14. `rn-eas-build-submit-update` (K9)
15. `rn-publishing-payments` (K10)
16. `rn-eas-deploy` (O5)

✅ End-state Wave 3: set completo, app pubblicabile su entrambi gli store.

## 9. Validazione del set

Per ogni skill prodotta:

1. **Trigger test**: scrivere 3 frasi che *devono* far invocare la skill e 3 frasi adiacenti che NON devono. Verificare empiricamente (chiedere a Claude di scegliere fra le skill disponibili).
2. **End-to-end smoke test** (a fine Wave 1): prendere un `PROJECT.md` di test, far girare `prd-from-idea → rn-bootstrap`, verificare che l'app generata compili (`npx expo start`) e mostri una schermata.
3. **Sources currency check** (mensile): confrontare versioni in `stack-defaults.md` con ultime release Expo SDK / NativeWind / Reanimated.

## 10. Esclusioni esplicite (YAGNI)

- ❌ Supporto a **bare workflow** (eject da Expo) — il 95% dei progetti non serve, se serve si parte da Expo + config plugins.
- ❌ Skill per **Detox** — Maestro è strettamente migliore per il 99% dei casi.
- ❌ Skill per **Redux Toolkit** — Zustand è il default.
- ❌ Skill per **react-navigation diretto** — Expo Router lo usa internamente.
- ❌ Supporto **React Native Web** — fuori scope per ora.
- ❌ Skill per **Tamagui / Restyle / Unistyles** — NativeWind unico default.

## 11. Decisioni rimaste aperte (da chiudere in writing-plans)

- Versione esatta di Expo SDK / Reanimated / NativeWind al momento della build (verifica `latest` in fase di setup).
- Se versionare le skill `rn-*` con un campo `version:` in frontmatter (oggi le tue skill esistenti non lo fanno).
- Se aggiungere uno script di lint comune (`scripts/lint-skill.sh`) per validare frontmatter consistente in tutte le skill `rn-*`.

---

**Next step**: review utente di questo documento → se approvato, passaggio alla skill `writing-plans` per produrre il piano di implementazione (con dipendenze fra task, file da creare per ogni skill, test di trigger).
