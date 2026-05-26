# React Native + Expo skills — Wave 1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** ship the MVP slice of the RN/Expo skills set: 3 knowledge skills (`rn-fundamentals`, `rn-styling`, `rn-expo-router`), 1 operative skill (`rn-bootstrap`), and the minimum `dev-flow` extension needed to route to it from `stack="expo-rn"`. After this plan, an agent can take a `PRD.md` + `DESIGN.md` and produce a running Expo app that boots, is styled with NativeWind from DESIGN tokens, and has Expo Router wired up.

**Architecture:** all new skills live under `~/my-skills/<skill-name>/` in the standard format (`SKILL.md` + `references/` + optionally `scripts/`). Knowledge skills are inert markdown that the agent reads in context to learn what to do / not do. The operative skill `rn-bootstrap` consults its three knowledge dependencies and runs scripts that scaffold an Expo app. `dev-flow` learns one new route: `prd_drafted` + `stack="expo-rn"` → `rn-bootstrap`.

**Tech Stack:** Markdown skills, bash scripts (POSIX), Node.js + TypeScript for one helper script, Expo SDK (latest stable) via `create-expo-app`, NativeWind v4, Expo Router. No new runtime dependencies for the skills themselves.

**Spec reference:** [docs/superpowers/specs/2026-05-16-rn-expo-skills-set-design.md](../specs/2026-05-16-rn-expo-skills-set-design.md) — Wave 1 only (sections 4 row K1/K3/K4/O1, section 7 dev-flow extension, section 8 Wave 1).

**Scoping notes:**
- This plan covers Wave 1 only. Wave 2 (`rn-components-apis`, `rn-data-fetching`, `rn-add-screen`, `rn-write-tests`) and Wave 3 (Supabase / animations / push / module-add / EAS / publishing / eas-deploy) get separate plans after Wave 1 ships and the templates are validated.
- `~/my-skills/` is not currently a git repository. Git commit steps are written but marked **skip-if-not-git**; once the directory becomes a repo (Task 0a — optional), they activate. The plan is otherwise unchanged.
- Italiano in user-facing text? **No** — skill content stays in English, matching the existing `~/my-skills/*.skill` style. The user works in italiano in conversation but skills are international artifacts.

---

## File Structure

All paths are absolute, rooted at `/Users/lucadigerlando/my-skills/`.

### New files

```
rn-fundamentals/
├── SKILL.md
└── references/
    ├── concepts.md              # bridge / Fabric / Hermes / New Architecture / RN vs web
    ├── patterns.md              # do's and dont's at fundamentals level
    ├── stack-defaults.md        # exact versions of Expo SDK, RN, key libs
    └── decision-tree.md         # "managed vs bare", "Expo Go vs dev client", etc.

rn-styling/
├── SKILL.md
└── references/
    ├── concepts.md              # Flexbox in RN, units, safe-area, dark mode
    ├── patterns.md              # 5 rules + anti-patterns
    ├── nativewind-setup.md      # install + tailwind.config.js + provider wiring
    ├── decision-tree.md         # StyleSheet vs NativeWind vs inline
    └── examples/
        ├── responsive-card.tsx
        ├── dark-mode-toggle.tsx
        └── safe-area-layout.tsx

rn-expo-router/
├── SKILL.md
└── references/
    ├── concepts.md              # file-based routing, typed routes, layouts
    ├── patterns.md              # tabs/stack/drawer, modal, search params
    ├── deep-linking-setup.md    # universal links, app links, scheme
    ├── decision-tree.md         # "tabs vs stack vs drawer" + when to use modals
    └── examples/
        ├── layout-with-tabs.tsx
        ├── modal-route.tsx
        └── typed-search-params.tsx

rn-bootstrap/
├── SKILL.md
├── references/
│   ├── contracts.md             # vendored copy of dev-flow contracts (same pattern as module-add)
│   ├── stack-defaults.md        # versions snapshot for the bootstrap moment
│   └── post-bootstrap-checklist.md
└── scripts/
    ├── init-expo-app.sh         # create-expo-app + blank-typescript template
    ├── install-stack.sh         # NativeWind v4 + Zustand + TanStack Query + Reanimated 3 + RNGH
    ├── wire-nativewind.ts       # reads DESIGN.md → writes tailwind.config.js
    └── verify.ts                # post-install smoke: tsc passes, expo doctor OK

dev-flow/references/stack-expo-rn.md       # NEW: stack definition + routing for RN

# Trigger acceptance tests (one file per skill, kept under spec dir, not shipped with the skill)
docs/superpowers/tests/
├── triggers-rn-fundamentals.md
├── triggers-rn-styling.md
├── triggers-rn-expo-router.md
└── triggers-rn-bootstrap.md
```

### Modified files

```
dev-flow/SKILL.md                # add routing row for stack="expo-rn"
prd-from-idea/SKILL.md           # add one discovery question "Target: web/mobile/desktop?"
                                 # if mobile → write stack="expo-rn" in meta.json
```

### Responsibility boundaries

- **`SKILL.md`** of each skill: frontmatter (name + description with triggers + "Not for:") and a short prose page enumerating the 3-5 rules the skill enforces + a quick decision tree pointing to references.
- **`references/concepts.md`**: pure knowledge — concepts the agent needs to reason correctly. No prescriptions.
- **`references/patterns.md`**: prescriptive — "do this, never do that".
- **`references/decision-tree.md`**: branching guide for the agent to pick the right approach.
- **`references/examples/*.tsx`**: real, compilable TypeScript snippets. Each file ≤ 80 lines.
- **`scripts/*.sh|.ts`**: idempotent, one responsibility per file, exit non-zero on failure.

---

## Task 0a (OPTIONAL): Initialize git in `~/my-skills/`

**Files:**
- Modify: `/Users/lucadigerlando/my-skills/` (git init)

> Skip if the user does not want this directory to become a git repo. If skipped, all "Commit" steps in later tasks become no-ops; mark them skipped.

- [ ] **Step 1: Check current state**

Run: `cd /Users/lucadigerlando/my-skills && git rev-parse --is-inside-work-tree 2>&1 || echo "not a repo"`
Expected: `not a repo` (or `true` — if `true`, skip the rest of Task 0a).

- [ ] **Step 2: Initialize**

Run: `cd /Users/lucadigerlando/my-skills && git init -b main`
Expected: `Initialized empty Git repository in /Users/lucadigerlando/my-skills/.git/`

- [ ] **Step 3: Add minimal `.gitignore`**

Create `/Users/lucadigerlando/my-skills/.gitignore`:

```
.DS_Store
node_modules/
.expo/
*.log
.playwright-mcp/
figma-to-design-md-workspace/
```

- [ ] **Step 4: Initial commit of current state**

Run:
```bash
cd /Users/lucadigerlando/my-skills && \
git add .gitignore docs/superpowers/specs docs/superpowers/plans && \
git commit -m "chore: init git, add design spec + plan for RN/Expo skills (Wave 1)"
```
Expected: commit created.

---

## Task 0b: Create directory scaffold (empty dirs + trigger test placeholders)

**Files:**
- Create: 4 skill directories + `dev-flow/references/stack-expo-rn.md` (empty stub) + 4 trigger test files.

- [ ] **Step 1: Create empty skill directories**

Run:
```bash
cd /Users/lucadigerlando/my-skills && \
mkdir -p rn-fundamentals/references \
         rn-styling/references/examples \
         rn-expo-router/references/examples \
         rn-bootstrap/references \
         rn-bootstrap/scripts \
         docs/superpowers/tests
```
Expected: directories created, no output.

- [ ] **Step 2: Verify**

Run: `ls -d /Users/lucadigerlando/my-skills/rn-* | sort`
Expected: 4 lines — `rn-bootstrap`, `rn-expo-router`, `rn-fundamentals`, `rn-styling`.

- [ ] **Step 3: Commit (skip-if-not-git)**

```bash
cd /Users/lucadigerlando/my-skills && \
git add rn-fundamentals rn-styling rn-expo-router rn-bootstrap docs/superpowers/tests 2>/dev/null && \
git commit -m "chore: scaffold Wave 1 skill directories"
```

---

## Task 1: Trigger acceptance list for `rn-fundamentals`

**Files:**
- Create: `docs/superpowers/tests/triggers-rn-fundamentals.md`

This is the "test" we write before the skill itself. It documents what the skill must do (be selected) and must not do (be selected on adjacent topics).

- [ ] **Step 1: Write the trigger spec**

Create `/Users/lucadigerlando/my-skills/docs/superpowers/tests/triggers-rn-fundamentals.md`:

```markdown
# Trigger acceptance list — rn-fundamentals

This skill MUST be selected by the agent when the user asks something matching these patterns:

## Should trigger (3+)
1. "Sto iniziando un nuovo progetto React Native, da dove parto?"
2. "Cosa cambia tra Expo managed e bare workflow?"
3. "Mi spieghi la New Architecture di RN (Fabric, Hermes, JSI)?"

## Should NOT trigger (3+)
1. "Aggiungi una schermata di login" → expect rn-add-screen (Wave 2) or rn-expo-router
2. "Stila questa card con dark mode" → expect rn-styling
3. "Configura Stripe nel mio progetto Next.js" → expect module-add (Next.js stack)

## Anti-patterns the skill content MUST forbid
1. Using `react-native init` (CLI bare) when Expo managed works — Expo is default.
2. Using legacy "Old Architecture" without justification — New Architecture default ON.
3. Mixing Yarn + npm in the same project — pick one (npm by default).
```

- [ ] **Step 2: Commit (skip-if-not-git)**

```bash
cd /Users/lucadigerlando/my-skills && \
git add docs/superpowers/tests/triggers-rn-fundamentals.md && \
git commit -m "test: trigger acceptance list for rn-fundamentals"
```

---

## Task 2: Write `rn-fundamentals/SKILL.md`

**Files:**
- Create: `rn-fundamentals/SKILL.md`

- [ ] **Step 1: Write the file**

Create `/Users/lucadigerlando/my-skills/rn-fundamentals/SKILL.md`:

```markdown
---
name: rn-fundamentals
description: 'Use at the start of any React Native or Expo task to lock in foundational choices: Expo managed workflow as default, latest Expo SDK with New Architecture ON, TypeScript, npm. Triggers on: "starting a new RN/Expo project", "what is the right architecture for an Expo app", "managed vs bare workflow", questions about Fabric/Hermes/JSI/New Architecture, "differences between RN and React web". Also triggers as a precondition when any other rn-* skill is selected and project setup is unclear. Not for: styling (rn-styling), navigation (rn-expo-router), data (rn-data-fetching).'
---

# rn-fundamentals — foundational rules for React Native + Expo

This skill is the prerequisite read for any RN/Expo work. It sets the four non-negotiables and points you to deeper concept material when needed.

## The 4 non-negotiables

1. **Expo managed workflow** is the default. Bare workflow / `react-native init` only if there is a documented native dependency Expo cannot wrap.
2. **Latest stable Expo SDK** at bootstrap time, with **New Architecture ON** (`newArchEnabled: true` in `app.json`). Hermes is the default JS engine — leave it on.
3. **TypeScript** is mandatory. Template `blank-typescript`. `tsconfig.json` extends `expo/tsconfig.base`.
4. **npm** is the package manager (matches Expo defaults and `npx create-expo-app`). No Yarn, no pnpm in this set.

## Quick decision tree

- "Should I use Expo or bare RN?" → `references/decision-tree.md`
- "What versions am I targeting?" → `references/stack-defaults.md`
- "Why does X behave differently than React on the web?" → `references/concepts.md`
- "Is this an OK pattern at the foundational level?" → `references/patterns.md`

## Common anti-patterns (NEVER do)

- ❌ `npx react-native init` when Expo managed would have worked — Expo is the default.
- ❌ Leaving New Architecture OFF on a new project — opt out only with a written reason.
- ❌ Mixing `yarn` and `npm install` in the same project.
- ❌ Pinning Expo SDK to a version older than the current stable without justification.

## Sources

- Course: codewithbeto.dev/rnCourse — lessons 1, 2, 3, 5, 6, 12 + "Introduction" module (free).
- Official: https://reactnative.dev/architecture/landing-page
- Official: https://docs.expo.dev/get-started/introduction/
```

- [ ] **Step 2: Verify frontmatter is valid YAML**

Run: `python3 -c "import yaml,sys; d=open('/Users/lucadigerlando/my-skills/rn-fundamentals/SKILL.md').read(); fm=d.split('---')[1]; print(yaml.safe_load(fm))"`
Expected: prints a dict with `name` and `description` keys, no exception.

- [ ] **Step 3: Verify it satisfies the trigger acceptance list (manual)**

Read `docs/superpowers/tests/triggers-rn-fundamentals.md` and the SKILL.md just written. For each "Should trigger" entry, check the description text contains a clear hook (project starting / managed vs bare / New Architecture). For each "Anti-pattern", check the SKILL.md explicitly forbids it in the "Common anti-patterns" section. Note any gap in a TODO comment at the bottom of the trigger file — but do not commit TODOs to SKILL.md.

- [ ] **Step 4: Commit (skip-if-not-git)**

```bash
cd /Users/lucadigerlando/my-skills && \
git add rn-fundamentals/SKILL.md && \
git commit -m "feat(rn-fundamentals): SKILL.md with 4 non-negotiables"
```

---

## Task 3: Write `rn-fundamentals/references/concepts.md`

**Files:**
- Create: `rn-fundamentals/references/concepts.md`

- [ ] **Step 1: Write the file**

Create `/Users/lucadigerlando/my-skills/rn-fundamentals/references/concepts.md`:

```markdown
> Sources: reactnative.dev/architecture, docs.expo.dev/get-started, codewithbeto.dev lessons 1-3 (free).

# Concepts — React Native + Expo

## RN vs React on the web (one-line each)

- **DOM**: there is none. JSX maps to native views (`<View>` → `UIView` on iOS / `android.view.View` on Android), not to `<div>`.
- **Styling**: no CSS cascade. Styles are JS objects (via `StyleSheet`, NativeWind, or inline). Layout is **Flexbox by default, in column direction** (web is row).
- **Events**: `onPress`, not `onClick`. `Pressable` is the modern primitive (NOT `TouchableOpacity` for new code).
- **Routing**: no `<a href>`. Use Expo Router (file-based, see `rn-expo-router`).
- **Persistence**: no `localStorage`. Use `AsyncStorage` or `expo-secure-store`.

## The bridge, JSI, Fabric, Hermes (what to actually know)

- **Old Architecture**: JS thread talks to native via a serialized "bridge". Async only, batching, sometimes laggy.
- **JSI (JavaScript Interface)**: replaces the bridge with direct C++ binding. Synchronous calls become possible.
- **Fabric**: the new UI renderer built on JSI. Concurrent rendering capable.
- **TurboModules**: native modules over JSI. Lazy-loaded.
- **Hermes**: the JS engine optimized for RN (smaller bundle, faster start). Default since SDK 49.
- **New Architecture = Fabric + TurboModules + Hermes**. Enable via `newArchEnabled: true`. Default ON for new Expo apps at the time of writing.

## Managed vs bare (TL;DR)

- **Managed**: `app.json` describes the native config; you don't touch Xcode/Android Studio. Expo prebuild generates native code on demand. 95% of apps.
- **Bare**: you own `ios/` and `android/` folders. Use when you need a native library Expo cannot wrap (rare).
- **Expo Go**: dev sandbox for managed apps with no custom native deps. Quick to start, can't load custom native modules.
- **Dev client** (`expo-dev-client`): custom Expo Go for your app, supports any native module. Use as soon as you add a config plugin or custom native dep.

## Sources

- https://reactnative.dev/architecture/landing-page
- https://docs.expo.dev/workflow/overview/
- https://docs.expo.dev/develop/development-builds/introduction/
```

- [ ] **Step 2: Commit (skip-if-not-git)**

```bash
cd /Users/lucadigerlando/my-skills && \
git add rn-fundamentals/references/concepts.md && \
git commit -m "docs(rn-fundamentals): concepts.md — bridge/JSI/Fabric/Hermes + managed vs bare"
```

---

## Task 4: Write `rn-fundamentals/references/stack-defaults.md`

**Files:**
- Create: `rn-fundamentals/references/stack-defaults.md`

- [ ] **Step 1: Determine current "latest stable" of each dependency**

Run:
```bash
npm view expo version
npm view react-native version
npm view nativewind version
npm view zustand version
npm view @tanstack/react-query version
npm view react-native-reanimated version
npm view react-native-gesture-handler version
npm view expo-router version
```

Note each version. Use these in step 2.

- [ ] **Step 2: Write the file**

Create `/Users/lucadigerlando/my-skills/rn-fundamentals/references/stack-defaults.md` (substitute `<X>` with the versions from step 1):

```markdown
> Snapshot date: 2026-05-16. Re-check monthly with `npm view <pkg> version`.

# Stack defaults (opinionated)

When bootstrapping a new RN/Expo app via `rn-bootstrap`, install these exact major versions:

| Package | Version | Purpose | Notes |
|---|---|---|---|
| `expo` | <X> | Expo SDK | Use the latest stable from `npm view expo version`. New Arch ON. |
| `react-native` | <X> | RN core | Bumped by Expo SDK, do not override. |
| `react` | <X> | React | Bumped by Expo SDK, do not override. |
| `typescript` | <X> | TS | Template `blank-typescript` brings a compatible version. |
| `expo-router` | <X> | File-based routing | Mandatory for all apps in this set. |
| `nativewind` | ^4 | Tailwind for RN | Major 4 only. |
| `tailwindcss` | ^3.4 | NativeWind v4 needs Tailwind 3.4+ | Pin minor. |
| `zustand` | <X> | Global state | Default for non-trivial global state. |
| `@tanstack/react-query` | ^5 | Data fetching | Major 5 only. |
| `react-native-reanimated` | <X> | Animations | Required by Expo Router for native stack animations. |
| `react-native-gesture-handler` | <X> | Gestures | Required by Expo Router. |
| `react-native-safe-area-context` | <X> | Safe area | Required for all root screens. |
| `expo-image` | <X> | Optimized `<Image>` | Replaces `Image` from `react-native`. |
| `@shopify/flash-list` | <X> | Performant lists | Replaces `FlatList` for long lists. |

## Engine / runtime defaults

- JS engine: **Hermes** (default).
- Architecture: **New Architecture ON** (`newArchEnabled: true` in `app.json`).
- Min iOS: 15.1 (Expo SDK 53+ default).
- Min Android: 24 (API level for Android 7.0).
- Bundler: Metro (Expo default).
- Package manager: **npm**.

## How to refresh

Run `bash /Users/lucadigerlando/my-skills/scripts/refresh-stack-defaults.sh` (created later, optional). For now, manually re-run `npm view ...` once a month.
```

- [ ] **Step 3: Commit (skip-if-not-git)**

```bash
cd /Users/lucadigerlando/my-skills && \
git add rn-fundamentals/references/stack-defaults.md && \
git commit -m "docs(rn-fundamentals): stack-defaults.md with pinned versions"
```

---

## Task 5: Write `rn-fundamentals/references/patterns.md`

**Files:**
- Create: `rn-fundamentals/references/patterns.md`

- [ ] **Step 1: Write the file**

Create `/Users/lucadigerlando/my-skills/rn-fundamentals/references/patterns.md`:

```markdown
> Sources: reactnative.dev best practices, docs.expo.dev, codewithbeto.dev lessons 5-6 (free).

# Patterns and anti-patterns at the foundational level

## Project layout (mandatory)

```
my-app/
├── app/                  # Expo Router file-based routes
│   ├── _layout.tsx
│   └── index.tsx
├── components/           # presentational + reusable components
├── lib/                  # framework-agnostic helpers (api client, supabase, utils)
├── store/                # Zustand stores
├── types/                # shared TS types
├── assets/               # images, fonts
├── tailwind.config.js
├── global.css            # NativeWind v4 entry CSS
├── app.json
├── tsconfig.json
└── package.json
```

## DO

- ✅ Use `Pressable` for new touchable components.
- ✅ Wrap every root screen in `SafeAreaView` (from `react-native-safe-area-context`).
- ✅ Use `expo-image` for static and remote images (gives caching and placeholders).
- ✅ Use `@shopify/flash-list` for any list with > 20 items or unknown length.
- ✅ Use TypeScript paths (e.g. `@/components/Button`) configured in `tsconfig.json`.
- ✅ Read env vars only via `process.env.EXPO_PUBLIC_*` (public) or expo-constants (build-time secrets).

## DON'T

- ❌ Use `TouchableOpacity` / `TouchableHighlight` in new code — `Pressable` covers all cases.
- ❌ Hardcode magic numbers — pull from `tailwind.config.js` tokens.
- ❌ Use `Image` from `react-native` — use `expo-image`.
- ❌ Use `FlatList` for long lists — use `FlashList`.
- ❌ Use `react-navigation` directly — Expo Router wraps it.
- ❌ Use `console.log` in shipped code — use `expo-dev-tools` logging.
- ❌ Use `dimensions = Dimensions.get('window')` at module top-level — recompute on `useWindowDimensions` to handle rotation/foldables.

## When the rules clash with the course (codewithbeto)

The course teaches `TouchableOpacity`, `Image`, `FlatList`, and `StyleSheet` in the free lessons because they are simpler for beginners. In this skill set, **prefer the modern alternative** (`Pressable`, `expo-image`, `FlashList`, NativeWind). The course concepts still apply 1:1.
```

- [ ] **Step 2: Commit (skip-if-not-git)**

```bash
cd /Users/lucadigerlando/my-skills && \
git add rn-fundamentals/references/patterns.md && \
git commit -m "docs(rn-fundamentals): patterns.md — DO/DON'T at foundational level"
```

---

## Task 6: Write `rn-fundamentals/references/decision-tree.md`

**Files:**
- Create: `rn-fundamentals/references/decision-tree.md`

- [ ] **Step 1: Write the file**

Create `/Users/lucadigerlando/my-skills/rn-fundamentals/references/decision-tree.md`:

```markdown
> Sources: docs.expo.dev/workflow/overview, docs.expo.dev/development-builds, internal opinion.

# Decision tree — fundamentals

## Q1: Expo managed or bare?

```
Need a native library Expo cannot wrap?
├── NO  → MANAGED. Always start here.
└── YES → Check expo-modules registry first. Still NO?
         ├── Library is a one-off (e.g. legacy SDK) → BARE
         └── Library is broadly useful → write a config plugin instead, stay MANAGED
```

**Default: managed. 95% of apps stay here.**

## Q2: Expo Go or dev client?

```
Adding any of: custom native module, config plugin, custom build flag?
├── NO  → EXPO GO. Faster onboarding for the team.
└── YES → DEV CLIENT (expo-dev-client). Build once per native change.
```

**Default for a brand-new app: Expo Go. Switch to dev client the day you add Reanimated 3 + native config OR any expo-* module that needs prebuild (very few do).**

## Q3: New Architecture ON or OFF?

```
ON, unless: a critical library is still incompatible (very rare in 2026).
```

If you turn it OFF: write the reason in `app.json` as a comment-equivalent (a `// reason` in README) and add a TODO to flip ON later.

## Q4: TypeScript strict mode?

```
ALWAYS strict: true in tsconfig.json. extends "expo/tsconfig.base".
```

## Q5: Monorepo?

Out of scope for Wave 1. If asked, defer with: "single-package Expo app for now; if you need a monorepo, that's a separate setup (pnpm workspaces or bun workspaces) outside this skill set."
```

- [ ] **Step 2: Commit (skip-if-not-git)**

```bash
cd /Users/lucadigerlando/my-skills && \
git add rn-fundamentals/references/decision-tree.md && \
git commit -m "docs(rn-fundamentals): decision-tree.md — managed/bare, Expo Go/dev client, etc."
```

---

## Task 7: Trigger acceptance list for `rn-styling`

**Files:**
- Create: `docs/superpowers/tests/triggers-rn-styling.md`

- [ ] **Step 1: Write the trigger spec**

Create `/Users/lucadigerlando/my-skills/docs/superpowers/tests/triggers-rn-styling.md`:

```markdown
# Trigger acceptance list — rn-styling

## Should trigger (3+)
1. "Stila questa schermata con dark mode"
2. "Configura NativeWind dal mio DESIGN.md"
3. "Ho un componente che ignora la safe area su iPhone, fixalo"

## Should NOT trigger (3+)
1. "Aggiungi una nuova route a /settings" → expect rn-expo-router
2. "Anima il pulsante al press" → expect rn-animations-gestures (Wave 3)
3. "Fetch dei posts da API" → expect rn-data-fetching (Wave 2)

## Anti-patterns the skill content MUST forbid
1. Magic numbers in inline `style={{ padding: 16 }}` — must use tokens.
2. Root screen without `SafeAreaView` from `react-native-safe-area-context`.
3. Importing `tailwindcss` directly (must go through NativeWind v4).
4. Using `Appearance.getColorScheme()` at module top-level instead of `useColorScheme()` (doesn't update reactively).
5. Using `Image` from `react-native` for remote images (must use `expo-image`).
```

- [ ] **Step 2: Commit (skip-if-not-git)**

```bash
cd /Users/lucadigerlando/my-skills && \
git add docs/superpowers/tests/triggers-rn-styling.md && \
git commit -m "test: trigger acceptance list for rn-styling"
```

---

## Task 8: Write `rn-styling/SKILL.md`

**Files:**
- Create: `rn-styling/SKILL.md`

- [ ] **Step 1: Write the file**

Create `/Users/lucadigerlando/my-skills/rn-styling/SKILL.md`:

```markdown
---
name: rn-styling
description: 'Use when styling React Native + Expo components: choosing between StyleSheet/NativeWind/inline, wiring NativeWind v4 from DESIGN.md tokens, handling Flexbox in RN (column-by-default, not row), safe-area insets, dark mode, responsive design with useWindowDimensions, optimized images via expo-image, performant lists via FlashList. Triggers on: "style this screen", "add dark mode", "fix safe area", "import design tokens", "set up NativeWind", or when an agent is about to write StyleSheet/className in an RN file. Not for: building screens end-to-end (rn-add-screen, Wave 2), navigation (rn-expo-router), animations (rn-animations-gestures, Wave 3), or web styling (Next.js stack).'
---

# rn-styling — guardrail for styling in React Native + Expo

## The 5 rules (non-negotiable)

1. **NativeWind v4 is the default**. `StyleSheet` only for performance-critical paths (per-frame animations etc.).
2. **No magic numbers**. Every spacing/color/radius/font value comes from `tailwind.config.js` (which mirrors the project's DESIGN.md tokens).
3. **SafeArea mandatory on every root screen**. Use `SafeAreaView` from `react-native-safe-area-context` (NOT the one from `react-native`).
4. **Dark mode via `useColorScheme` + Tailwind `dark:` variant**. Never `Appearance.getColorScheme()` at module top-level.
5. **Optimized primitives**: `expo-image` instead of `Image`; `@shopify/flash-list` for any list > 20 items.

## Quick decision tree

- "Should I style this with NativeWind or StyleSheet?" → `references/decision-tree.md`
- "How do I set up NativeWind v4 from scratch?" → `references/nativewind-setup.md`
- "Why does Flexbox behave differently than on the web?" → `references/concepts.md`
- "What are the common patterns and anti-patterns?" → `references/patterns.md`
- "Show me a real example" → `references/examples/`

## Common anti-patterns (NEVER do)

- ❌ `style={{ padding: 16 }}` with a magic number — pull from token.
- ❌ Root `<View>` without `SafeAreaView` from `react-native-safe-area-context`.
- ❌ `import "tailwindcss"` directly in code — only NativeWind imports.
- ❌ `Appearance.getColorScheme()` at module level — use `useColorScheme()` hook.
- ❌ `Image` from `react-native` for remote URIs — use `expo-image`.
- ❌ `flex: 1` on root + scroll without `contentContainerStyle` on `ScrollView` — content gets clipped.

## Sources

- Course: codewithbeto.dev/rnCourse — lesson 10 "Styling Your App" (free).
- Official: https://docs.expo.dev/develop/user-interface/styling/
- Official: https://www.nativewind.dev/ (v4)
- Official: https://github.com/AppAndFlow/react-native-safe-area-context
```

- [ ] **Step 2: Verify frontmatter**

Run: `python3 -c "import yaml; d=open('/Users/lucadigerlando/my-skills/rn-styling/SKILL.md').read(); fm=d.split('---')[1]; print(list(yaml.safe_load(fm).keys()))"`
Expected: `['name', 'description']`

- [ ] **Step 3: Check anti-pattern coverage**

Read `docs/superpowers/tests/triggers-rn-styling.md` "Anti-patterns" section. For each of the 5 anti-patterns listed, verify SKILL.md "Common anti-patterns" or "The 5 rules" mentions it explicitly. All 5 must be covered.

- [ ] **Step 4: Commit (skip-if-not-git)**

```bash
cd /Users/lucadigerlando/my-skills && \
git add rn-styling/SKILL.md && \
git commit -m "feat(rn-styling): SKILL.md with 5 styling rules"
```

---

## Task 9: Write `rn-styling/references/concepts.md`

**Files:**
- Create: `rn-styling/references/concepts.md`

- [ ] **Step 1: Write the file**

Create `/Users/lucadigerlando/my-skills/rn-styling/references/concepts.md`:

```markdown
> Sources: reactnative.dev/docs/flexbox, docs.expo.dev styling, codewithbeto.dev lesson 10 (free).

# Concepts — styling in React Native

## Flexbox: column by default

In RN, the default `flexDirection` is `column` (web defaults to `row`). This trips up every web developer. Always explicit: write `flexDirection: 'row'` (or `flex-row` in NativeWind) when you want horizontal.

```tsx
<View className="flex-1 flex-col">     {/* default, but be explicit */}
  <Text>top</Text>
  <Text>bottom</Text>
</View>

<View className="flex-1 flex-row">     {/* horizontal */}
  <Text>left</Text>
  <Text>right</Text>
</View>
```

## Units: no px, no em, no rem

Numbers are **density-independent pixels** (DIPs). `padding: 16` ≈ `16dp`. Tailwind's spacing scale (`p-4` = 16, `p-2` = 8, etc.) maps to the same numeric values.

For percent-of-parent, use a string: `width: '50%'`. For percent-of-screen, use `useWindowDimensions()` (NOT `Dimensions.get('window')` at module top-level).

## Safe area: why and where

iPhones with notches and Androids with cutouts have non-touchable insets at top/bottom. Wrap root screens in `SafeAreaView` from `react-native-safe-area-context` (NOT the deprecated one from `react-native`):

```tsx
import { SafeAreaView } from 'react-native-safe-area-context';

export default function Screen() {
  return (
    <SafeAreaView className="flex-1 bg-white dark:bg-zinc-900" edges={['top', 'bottom']}>
      {/* content */}
    </SafeAreaView>
  );
}
```

`edges` lets you opt out of inset on sides where the parent already handles it (e.g. tab bar covers `bottom`).

## Dark mode: reactive only

```tsx
// ❌ wrong — not reactive to runtime theme change
import { Appearance } from 'react-native';
const theme = Appearance.getColorScheme();

// ✅ correct — re-renders on theme change
import { useColorScheme } from 'react-native';
function Foo() {
  const colorScheme = useColorScheme(); // 'light' | 'dark' | null
  // …
}
```

With NativeWind, prefer the `dark:` variant — no hook needed:

```tsx
<View className="bg-white dark:bg-zinc-900">
  <Text className="text-zinc-900 dark:text-zinc-50">hello</Text>
</View>
```

## Tokens: DESIGN.md → tailwind.config.js

The project's `DESIGN.md` is the source of truth for colors, spacing, radii, type scale. The bootstrap step generates `tailwind.config.js` from it. NEVER hardcode a color or spacing value in a component; if you need a value that's not in the config, add it to `DESIGN.md` and re-run the generator.

## Sources

- https://reactnative.dev/docs/flexbox
- https://docs.expo.dev/develop/user-interface/styling/
- https://github.com/AppAndFlow/react-native-safe-area-context
```

- [ ] **Step 2: Commit (skip-if-not-git)**

```bash
cd /Users/lucadigerlando/my-skills && \
git add rn-styling/references/concepts.md && \
git commit -m "docs(rn-styling): concepts.md — flexbox/units/safe area/dark mode/tokens"
```

---

## Task 10: Write `rn-styling/references/nativewind-setup.md`

**Files:**
- Create: `rn-styling/references/nativewind-setup.md`

- [ ] **Step 1: Write the file**

Create `/Users/lucadigerlando/my-skills/rn-styling/references/nativewind-setup.md`:

```markdown
> Sources: https://www.nativewind.dev/v4/getting-started/expo-router

# NativeWind v4 setup for Expo Router

Run this *once* per project, at bootstrap time. `rn-bootstrap`'s `install-stack.sh` automates this — these are the manual steps for reference.

## 1. Install

```bash
npm install nativewind@^4 tailwindcss@^3.4 react-native-reanimated react-native-safe-area-context
```

## 2. `tailwind.config.js`

```js
/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./app/**/*.{js,jsx,ts,tsx}", "./components/**/*.{js,jsx,ts,tsx}"],
  presets: [require("nativewind/preset")],
  theme: {
    extend: {
      // populated from DESIGN.md by rn-bootstrap/scripts/wire-nativewind.ts
      colors: {
        primary: { DEFAULT: "#0ea5e9" /* example */ },
      },
    },
  },
  plugins: [],
};
```

## 3. `global.css`

```css
@tailwind base;
@tailwind components;
@tailwind utilities;
```

## 4. `babel.config.js`

```js
module.exports = function (api) {
  api.cache(true);
  return {
    presets: [
      ["babel-preset-expo", { jsxImportSource: "nativewind" }],
      "nativewind/babel",
    ],
  };
};
```

## 5. `metro.config.js`

```js
const { getDefaultConfig } = require("expo/metro-config");
const { withNativeWind } = require("nativewind/metro");

const config = getDefaultConfig(__dirname);
module.exports = withNativeWind(config, { input: "./global.css" });
```

## 6. Import the CSS in the root layout

```tsx
// app/_layout.tsx
import "../global.css";
import { Stack } from "expo-router";

export default function RootLayout() {
  return <Stack />;
}
```

## 7. Verify

```bash
npx expo start --clear
```

A `<Text className="text-2xl text-blue-500">hello</Text>` somewhere should render styled. If not, clear Metro cache: `npx expo start --clear`.

## Troubleshooting

- **Classes ignored**: check `content` glob in `tailwind.config.js` covers your files.
- **`Unable to resolve "nativewind/preset"`**: NativeWind v4 not installed. `npm ls nativewind`.
- **iOS simulator shows unstyled text**: babel cache stale. `rm -rf node_modules/.cache && npx expo start --clear`.
```

- [ ] **Step 2: Commit (skip-if-not-git)**

```bash
cd /Users/lucadigerlando/my-skills && \
git add rn-styling/references/nativewind-setup.md && \
git commit -m "docs(rn-styling): nativewind-setup.md — 7-step setup + troubleshooting"
```

---

## Task 11: Write `rn-styling/references/patterns.md`

**Files:**
- Create: `rn-styling/references/patterns.md`

- [ ] **Step 1: Write the file**

Create `/Users/lucadigerlando/my-skills/rn-styling/references/patterns.md`:

```markdown
> Sources: NativeWind v4 docs, reactnative.dev, internal opinion.

# Patterns and anti-patterns — styling

## Layout

### DO

- ✅ Root screen pattern:
  ```tsx
  <SafeAreaView className="flex-1 bg-white dark:bg-zinc-900">
    <ScrollView className="flex-1" contentContainerClassName="p-4 gap-4">
      {/* content */}
    </ScrollView>
  </SafeAreaView>
  ```
- ✅ Spacing between siblings via `gap-*` (NativeWind v4 supports it), not margins.
- ✅ `useWindowDimensions()` inside the component (not at module level).

### DON'T

- ❌ `flex: 1` without `flexDirection` explicit when ambiguous.
- ❌ Nested `ScrollView` (use one outer, multiple inner `<View>`).
- ❌ Fixed pixel heights for "% of screen" intent — use `dimensions.height * 0.5`.

## Color & theme

### DO

- ✅ Always pair light + dark: `bg-white dark:bg-zinc-900`, `text-zinc-900 dark:text-zinc-50`.
- ✅ Define semantic tokens in `tailwind.config.js` (`bg-background`, `bg-card`, `bg-primary`) — map to DESIGN.md.

### DON'T

- ❌ Hex literals inline: `style={{ color: '#0ea5e9' }}` → use `text-primary`.
- ❌ Forgetting the dark variant when introducing a new colored element.

## Typography

### DO

- ✅ Limit to 3-5 type scale steps defined in `tailwind.config.js` (`text-xs`, `text-sm`, `text-base`, `text-lg`, `text-2xl`).
- ✅ Load fonts via `expo-font` in `app/_layout.tsx`, surface via Tailwind `fontFamily`.

### DON'T

- ❌ `fontFamily: 'Helvetica'` literal in a component — Tailwind token only.
- ❌ Mixing system font + custom font without a fallback chain.

## Images

### DO

- ✅ `expo-image` for ALL images (static + remote):
  ```tsx
  import { Image } from 'expo-image';
  <Image source={uri} style={{ width: 200, height: 200 }} contentFit="cover" />
  ```
- ✅ Provide a `placeholder` (blurhash or local thumbnail) for remote.

### DON'T

- ❌ `import { Image } from 'react-native'` for remote — no caching.
- ❌ Setting only width OR only height — `expo-image` needs both (or `aspectRatio`).

## Lists

### DO

- ✅ `FlashList` for any list > 20 items or unknown length:
  ```tsx
  import { FlashList } from '@shopify/flash-list';
  <FlashList data={items} renderItem={({ item }) => <Row item={item} />} estimatedItemSize={64} />
  ```

### DON'T

- ❌ `FlatList` for long lists — slower at scale.
- ❌ `ScrollView` + `.map()` for any list with > 10 items.
```

- [ ] **Step 2: Commit (skip-if-not-git)**

```bash
cd /Users/lucadigerlando/my-skills && \
git add rn-styling/references/patterns.md && \
git commit -m "docs(rn-styling): patterns.md — layout/color/type/images/lists"
```

---

## Task 12: Write `rn-styling/references/decision-tree.md`

**Files:**
- Create: `rn-styling/references/decision-tree.md`

- [ ] **Step 1: Write the file**

Create `/Users/lucadigerlando/my-skills/rn-styling/references/decision-tree.md`:

```markdown
> Sources: NativeWind v4 docs, internal opinion.

# Decision tree — styling

## Q1: StyleSheet, NativeWind, or inline?

```
Is the style per-frame animated (gets read 60 times/sec)?
├── YES → StyleSheet (avoid string parsing overhead). Use Reanimated worklets if it's animated state.
└── NO  → NativeWind. Default for everything else.

Is the style derived from JS state (e.g. width based on a prop)?
├── YES with a *small* dynamic piece → inline style for the dynamic part:
│         className="rounded-lg" style={{ width: dynamicWidth }}
└── YES with mostly static → use NativeWind variants:
         className={cn("rounded-lg", isLarge && "p-8", isSmall && "p-2")}
```

## Q2: How do I make this responsive?

```
Need it to differ on phone vs tablet?
├── YES → useWindowDimensions() in the component, branch on width.
│        // No tailwind breakpoints in RN — NativeWind v4 supports them but RN ecosystem
│        // is mostly phone-sized; keep responsive logic in JS.
└── NO  → just write the design.
```

## Q3: Dark mode — do I need to wire anything?

```
Is the project already set up by rn-bootstrap?
├── YES → just use `dark:` variants. NativeWind reads useColorScheme() automatically.
└── NO  → add `darkMode: 'class'` in tailwind.config.js + wrap root with
         NativeWind colorScheme provider. See nativewind-setup.md.
```

## Q4: I need a value that's not in tailwind.config.js

```
Is the value going to be reused?
├── YES → add it to tailwind.config.js (and DESIGN.md upstream).
└── NO  → arbitrary value: className="p-[13px]" or className="bg-[#abc123]"
         (allowed sparingly; if you do this more than twice for the same value,
         go back to "YES").
```
```

- [ ] **Step 2: Commit (skip-if-not-git)**

```bash
cd /Users/lucadigerlando/my-skills && \
git add rn-styling/references/decision-tree.md && \
git commit -m "docs(rn-styling): decision-tree.md — when StyleSheet vs NativeWind, responsive, etc."
```

---

## Task 13: Write `rn-styling/references/examples/*.tsx`

**Files:**
- Create: `rn-styling/references/examples/responsive-card.tsx`
- Create: `rn-styling/references/examples/dark-mode-toggle.tsx`
- Create: `rn-styling/references/examples/safe-area-layout.tsx`

- [ ] **Step 1: Write `responsive-card.tsx`**

Create `/Users/lucadigerlando/my-skills/rn-styling/references/examples/responsive-card.tsx`:

```tsx
import { View, Text, useWindowDimensions } from "react-native";
import { Image } from "expo-image";

type Props = {
  title: string;
  subtitle: string;
  imageUri: string;
};

export function ResponsiveCard({ title, subtitle, imageUri }: Props) {
  const { width } = useWindowDimensions();
  const isWide = width >= 600;

  return (
    <View
      className={
        isWide
          ? "flex-row items-center gap-4 p-4 rounded-xl bg-white dark:bg-zinc-900 shadow"
          : "flex-col gap-3 p-4 rounded-xl bg-white dark:bg-zinc-900 shadow"
      }
    >
      <Image
        source={imageUri}
        style={{ width: isWide ? 96 : 200, height: isWide ? 96 : 200, borderRadius: 8 }}
        contentFit="cover"
        placeholder={{ blurhash: "L6Pj0^jE.AyE_3t7t7R**0o#DgR4" }}
      />
      <View className="flex-1">
        <Text className="text-lg font-semibold text-zinc-900 dark:text-zinc-50">{title}</Text>
        <Text className="text-sm text-zinc-600 dark:text-zinc-400">{subtitle}</Text>
      </View>
    </View>
  );
}
```

- [ ] **Step 2: Write `dark-mode-toggle.tsx`**

Create `/Users/lucadigerlando/my-skills/rn-styling/references/examples/dark-mode-toggle.tsx`:

```tsx
import { Pressable, Text, useColorScheme } from "react-native";
import { useState, useEffect } from "react";
import { Appearance } from "react-native";

export function DarkModeToggle() {
  const system = useColorScheme();
  const [override, setOverride] = useState<"light" | "dark" | null>(null);

  useEffect(() => {
    if (override) Appearance.setColorScheme(override);
  }, [override]);

  const current = override ?? system ?? "light";

  return (
    <Pressable
      onPress={() => setOverride(current === "dark" ? "light" : "dark")}
      className="flex-row items-center gap-2 px-4 py-2 rounded-full bg-zinc-200 dark:bg-zinc-800"
    >
      <Text className="text-zinc-900 dark:text-zinc-50">
        {current === "dark" ? "☀️ Light mode" : "🌙 Dark mode"}
      </Text>
    </Pressable>
  );
}
```

- [ ] **Step 3: Write `safe-area-layout.tsx`**

Create `/Users/lucadigerlando/my-skills/rn-styling/references/examples/safe-area-layout.tsx`:

```tsx
import { ScrollView, View, Text } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";

type Props = { title: string; children: React.ReactNode };

export function SafeAreaScreen({ title, children }: Props) {
  return (
    <SafeAreaView
      className="flex-1 bg-white dark:bg-zinc-900"
      edges={["top", "bottom"]}
    >
      <View className="px-4 py-3 border-b border-zinc-200 dark:border-zinc-800">
        <Text className="text-xl font-semibold text-zinc-900 dark:text-zinc-50">
          {title}
        </Text>
      </View>
      <ScrollView className="flex-1" contentContainerClassName="p-4 gap-4">
        {children}
      </ScrollView>
    </SafeAreaView>
  );
}
```

- [ ] **Step 4: Lint examples (syntax only)**

These examples are not in a real project so we can't typecheck them. Spot-check: open each, verify imports are correct and JSX is balanced.

- [ ] **Step 5: Commit (skip-if-not-git)**

```bash
cd /Users/lucadigerlando/my-skills && \
git add rn-styling/references/examples && \
git commit -m "docs(rn-styling): 3 example components (responsive card, dark toggle, safe area)"
```

---

## Task 14: Trigger acceptance list for `rn-expo-router`

**Files:**
- Create: `docs/superpowers/tests/triggers-rn-expo-router.md`

- [ ] **Step 1: Write the trigger spec**

Create `/Users/lucadigerlando/my-skills/docs/superpowers/tests/triggers-rn-expo-router.md`:

```markdown
# Trigger acceptance list — rn-expo-router

## Should trigger (3+)
1. "Aggiungi una nuova route /profile/[id]"
2. "Configura tab navigation con 3 tab"
3. "Apri questa schermata come modale"

## Should NOT trigger (3+)
1. "Cambia il colore del button" → expect rn-styling
2. "Anima la transizione tra schermate" → expect rn-animations-gestures (Wave 3)
3. "Fai un fetch dei posts" → expect rn-data-fetching (Wave 2)

## Anti-patterns the skill content MUST forbid
1. Importing `react-navigation/native` directly — must go through `expo-router`.
2. Using non-typed routes (`href="/foo"` instead of typed routes).
3. Hardcoded routes scattered in components — must be centralized as constants OR use typed routes.
4. Putting layout logic in screen files instead of `_layout.tsx`.
```

- [ ] **Step 2: Commit (skip-if-not-git)**

```bash
cd /Users/lucadigerlando/my-skills && \
git add docs/superpowers/tests/triggers-rn-expo-router.md && \
git commit -m "test: trigger acceptance list for rn-expo-router"
```

---

## Task 15: Write `rn-expo-router/SKILL.md`

**Files:**
- Create: `rn-expo-router/SKILL.md`

- [ ] **Step 1: Write the file**

Create `/Users/lucadigerlando/my-skills/rn-expo-router/SKILL.md`:

```markdown
---
name: rn-expo-router
description: 'Use when working with navigation in an Expo + React Native app: adding routes, building tab/stack/drawer layouts, modal routes, dynamic segments (e.g. /profile/[id]), typed routes, deep linking, search params. Triggers on: "add a route", "wire up tabs", "open as modal", "set up deep linking", "configure navigation", or whenever an agent is about to touch a file under app/. Not for: styling navigation chrome (rn-styling), animating transitions (rn-animations-gestures, Wave 3), or non-RN web routing.'
---

# rn-expo-router — guardrail for navigation in Expo + RN

## The 4 rules (non-negotiable)

1. **Expo Router only**. Never `import` from `@react-navigation/*` directly — Expo Router wraps and owns it.
2. **File-based**: routes live in `app/`. The filename IS the URL. `_layout.tsx` files define the layout for their directory.
3. **Typed routes ON**. In `app.json`: `"expo": { "experiments": { "typedRoutes": true } }`. Use `Href` type for navigation, never raw strings.
4. **Layouts contain navigators**. Screen files contain only the screen UI. Tab bar / stack header config goes in `_layout.tsx`.

## Quick decision tree

- "Tabs / Stack / Drawer — which?" → `references/decision-tree.md`
- "How do I structure routes for an auth-gated section?" → `references/patterns.md` (Auth groups)
- "Deep linking from notification or URL?" → `references/deep-linking-setup.md`
- "Show me a real layout" → `references/examples/`

## Common anti-patterns (NEVER do)

- ❌ `import { useNavigation } from '@react-navigation/native'` → use `useRouter()` from `expo-router`.
- ❌ `router.push('/profile/123')` as raw string → typed routes: `router.push({ pathname: '/profile/[id]', params: { id: '123' } })`.
- ❌ Defining a `<Tabs.Screen>` in a screen file — it goes in the parent `_layout.tsx`.
- ❌ Hardcoded route strings scattered everywhere → use typed routes (`expo-router/typed-routes` provides static checking).

## Sources

- Course: codewithbeto.dev/rnCourse — lesson 11 "Navigation Basics" (free) + 1 free Expo Router lesson.
- Official: https://docs.expo.dev/router/introduction/
- Official: https://docs.expo.dev/router/reference/typed-routes/
```

- [ ] **Step 2: Verify frontmatter**

Run: `python3 -c "import yaml; d=open('/Users/lucadigerlando/my-skills/rn-expo-router/SKILL.md').read(); fm=d.split('---')[1]; print(list(yaml.safe_load(fm).keys()))"`
Expected: `['name', 'description']`

- [ ] **Step 3: Commit (skip-if-not-git)**

```bash
cd /Users/lucadigerlando/my-skills && \
git add rn-expo-router/SKILL.md && \
git commit -m "feat(rn-expo-router): SKILL.md with 4 navigation rules"
```

---

## Task 16: Write `rn-expo-router/references/concepts.md`

**Files:**
- Create: `rn-expo-router/references/concepts.md`

- [ ] **Step 1: Write the file**

Create `/Users/lucadigerlando/my-skills/rn-expo-router/references/concepts.md`:

```markdown
> Sources: docs.expo.dev/router, codewithbeto.dev lesson 11 (free).

# Concepts — Expo Router

## File-based routing

The `app/` directory IS the routing config. Every file is a route.

```
app/
├── _layout.tsx              # root layout (wraps everything)
├── index.tsx                # /
├── about.tsx                # /about
├── profile/
│   ├── _layout.tsx          # layout for /profile/*
│   ├── index.tsx            # /profile
│   └── [id].tsx             # /profile/:id (dynamic segment)
└── (tabs)/                  # GROUP — parens are syntax, not URL
    ├── _layout.tsx          # tab navigator
    ├── feed.tsx             # /feed
    └── settings.tsx         # /settings
```

- `_layout.tsx` defines the layout (Stack / Tabs / Drawer / Slot) for its directory.
- `[id].tsx` is a dynamic segment. Access via `useLocalSearchParams<{ id: string }>()`.
- `(name)/` is a route GROUP: parens are stripped from the URL, used for shared layouts and code organization.
- `+not-found.tsx` is the 404 handler.

## Typed routes

With `"typedRoutes": true` in `app.json`, Expo Router generates TypeScript types for every route at build time. Then:

```tsx
import { Href, Link, useRouter } from "expo-router";

const href: Href = { pathname: "/profile/[id]", params: { id: "abc" } };

<Link href={href}>Go</Link>

const router = useRouter();
router.push(href);
```

Wrong route string → compile error. Wrong params → compile error.

## Layouts vs screens

- **Layouts** own the navigator (`<Stack />`, `<Tabs />`, `<Drawer />`) and the chrome (header, tab bar). Defined in `_layout.tsx`.
- **Screens** own only the content. Reference them in the parent layout via `<Stack.Screen name="…" options={…} />`.

```tsx
// app/(tabs)/_layout.tsx
import { Tabs } from "expo-router";

export default function TabsLayout() {
  return (
    <Tabs>
      <Tabs.Screen name="feed" options={{ title: "Feed" }} />
      <Tabs.Screen name="settings" options={{ title: "Settings" }} />
    </Tabs>
  );
}
```

## Groups for auth

```
app/
├── _layout.tsx                  # checks auth, redirects
├── (auth)/                      # public routes
│   ├── _layout.tsx
│   ├── sign-in.tsx
│   └── sign-up.tsx
└── (app)/                       # protected routes
    ├── _layout.tsx              # redirects to /(auth)/sign-in if no user
    ├── index.tsx
    └── profile/[id].tsx
```

## Sources

- https://docs.expo.dev/router/introduction/
- https://docs.expo.dev/router/reference/typed-routes/
- https://docs.expo.dev/router/advanced/router-settings/
```

- [ ] **Step 2: Commit (skip-if-not-git)**

```bash
cd /Users/lucadigerlando/my-skills && \
git add rn-expo-router/references/concepts.md && \
git commit -m "docs(rn-expo-router): concepts.md — file-based routing, typed routes, layouts, groups"
```

---

## Task 17: Write `rn-expo-router/references/patterns.md`

**Files:**
- Create: `rn-expo-router/references/patterns.md`

- [ ] **Step 1: Write the file**

Create `/Users/lucadigerlando/my-skills/rn-expo-router/references/patterns.md`:

```markdown
> Sources: docs.expo.dev/router/advanced, internal opinion.

# Patterns and anti-patterns — Expo Router

## Navigation

### DO

- ✅ `useRouter()` for imperative navigation:
  ```tsx
  const router = useRouter();
  router.push({ pathname: "/profile/[id]", params: { id: "abc" } });
  router.back();
  router.replace("/");
  ```
- ✅ `<Link>` for declarative:
  ```tsx
  <Link href={{ pathname: "/profile/[id]", params: { id: "abc" } }}>View profile</Link>
  ```
- ✅ `useLocalSearchParams<T>()` for typed dynamic segment / query params.

### DON'T

- ❌ `useNavigation()` from `@react-navigation/native` — Expo Router has its own primitives.
- ❌ Raw-string `router.push('/profile/abc')` — typed routes catch typos.
- ❌ Multiple nested navigators when a group + single navigator would do.

## Modals

A modal is a screen with `presentation: 'modal'`. Live under any layout.

```tsx
// app/_layout.tsx
<Stack>
  <Stack.Screen name="(tabs)" options={{ headerShown: false }} />
  <Stack.Screen name="settings-modal" options={{ presentation: "modal" }} />
</Stack>
```

```tsx
// app/settings-modal.tsx
import { View, Text } from "react-native";
export default function SettingsModal() {
  return <View><Text>Modal content</Text></View>;
}
```

Open via `router.push('/settings-modal')`.

## Auth gating

Pattern: protected group `(app)` with a `_layout.tsx` that redirects.

```tsx
// app/(app)/_layout.tsx
import { Redirect, Stack } from "expo-router";
import { useUser } from "@/lib/auth"; // your auth hook (see rn-backend Wave 3, provider-agnostic)

export default function ProtectedLayout() {
  const user = useUser();
  if (!user) return <Redirect href="/(auth)/sign-in" />;
  return <Stack />;
}
```

## Search params

```tsx
import { useLocalSearchParams } from "expo-router";

type Params = { id: string; tab?: "info" | "posts" };

export default function Profile() {
  const { id, tab = "info" } = useLocalSearchParams<Params>();
  return <Text>{id} - {tab}</Text>;
}
```

For non-route screens that observe URL changes, use `useGlobalSearchParams` (re-renders on any change).

## Anti-patterns

- ❌ Putting `<Tabs.Screen>` inside the screen component instead of the layout — won't work, Tabs ignores it.
- ❌ Two `_layout.tsx` at the same level — only one is allowed per directory.
- ❌ Defining a route AND a group with the same name (`profile.tsx` + `(profile)/`) — collision.
- ❌ Using `window.location` for URL parsing — use `usePathname()` from expo-router.
```

- [ ] **Step 2: Commit (skip-if-not-git)**

```bash
cd /Users/lucadigerlando/my-skills && \
git add rn-expo-router/references/patterns.md && \
git commit -m "docs(rn-expo-router): patterns.md — navigation/modals/auth gating/params"
```

---

## Task 18: Write `rn-expo-router/references/deep-linking-setup.md`

**Files:**
- Create: `rn-expo-router/references/deep-linking-setup.md`

- [ ] **Step 1: Write the file**

Create `/Users/lucadigerlando/my-skills/rn-expo-router/references/deep-linking-setup.md`:

```markdown
> Sources: docs.expo.dev/router/reference/redirects, docs.expo.dev/linking/

# Deep linking with Expo Router

Expo Router supports deep links out of the box: every file-route is reachable via a URL. You only need to declare the scheme(s) and verify the domain on iOS/Android.

## 1. Custom scheme (always set this)

`app.json`:
```json
{
  "expo": {
    "scheme": "myapp"
  }
}
```

Now `myapp://profile/abc` opens the app at `/profile/abc`.

## 2. Universal Links (iOS) / App Links (Android)

For HTTPS URLs (`https://myapp.com/profile/abc`):

`app.json`:
```json
{
  "expo": {
    "ios": {
      "associatedDomains": ["applinks:myapp.com"]
    },
    "android": {
      "intentFilters": [
        {
          "action": "VIEW",
          "data": [{ "scheme": "https", "host": "myapp.com" }],
          "category": ["BROWSABLE", "DEFAULT"],
          "autoVerify": true
        }
      ]
    }
  }
}
```

You also need to host:
- iOS: `https://myapp.com/.well-known/apple-app-site-association` (JSON, see Apple docs)
- Android: `https://myapp.com/.well-known/assetlinks.json` (JSON, see Google docs)

## 3. Test it

```bash
# iOS simulator
xcrun simctl openurl booted myapp://profile/abc

# Android emulator
adb shell am start -a android.intent.action.VIEW -d "myapp://profile/abc"
```

## 4. Read the incoming URL programmatically

```tsx
import { useURL } from "expo-linking";

export default function App() {
  const url = useURL(); // null until app opened from link
  // …parse and act, but normally Expo Router handles routing automatically
}
```

## 5. From a push notification

See `rn-push-notifications` (Wave 3) for how to map the notification payload to a deep link.
```

- [ ] **Step 2: Commit (skip-if-not-git)**

```bash
cd /Users/lucadigerlando/my-skills && \
git add rn-expo-router/references/deep-linking-setup.md && \
git commit -m "docs(rn-expo-router): deep-linking-setup.md — scheme + universal/app links"
```

---

## Task 19: Write `rn-expo-router/references/decision-tree.md`

**Files:**
- Create: `rn-expo-router/references/decision-tree.md`

- [ ] **Step 1: Write the file**

Create `/Users/lucadigerlando/my-skills/rn-expo-router/references/decision-tree.md`:

```markdown
> Sources: docs.expo.dev/router, internal opinion.

# Decision tree — Expo Router

## Q1: Stack, Tabs, or Drawer?

```
Are the top-level destinations a fixed small set the user switches between?
├── YES, 2-5 destinations    → Tabs (bottom on phones, top on web)
├── YES, 6+ destinations     → Drawer
└── NO, it's a hierarchy / flow → Stack (push/pop)
```

You can NEST them: a Stack inside a Tab, a Tab inside a Drawer, etc. The most common modern app: `Stack` at root → `(tabs)` group with `Tabs` layout → each tab has its own Stack of screens.

## Q2: Should this screen be a route or a component?

```
Does the user reach it via URL / share / deep link / push?
├── YES → file in app/ (route)
└── NO  → component in components/
```

## Q3: Modal or full screen?

```
Is the action temporary, dismissible, and shouldn't lose context?
├── YES → modal: <Stack.Screen options={{ presentation: 'modal' }} />
└── NO  → normal stack push
```

Use modal for: filters, sort, share sheet, settings overlay, sign-in prompt.
Use push for: detail view, list-to-item, anything you'd back-button out of.

## Q4: Should this protected area be a group or just a layout?

```
Multiple screens share the same auth-gate?
├── YES → (app)/ group with _layout.tsx that Redirects if no user
└── NO  → check auth inline in the single screen
```

## Q5: Where do I put the bottom-tab icons?

```
In the parent _layout.tsx, on each <Tabs.Screen options={{ tabBarIcon: () => ... }} />.
NEVER in the screen file itself.
```
```

- [ ] **Step 2: Commit (skip-if-not-git)**

```bash
cd /Users/lucadigerlando/my-skills && \
git add rn-expo-router/references/decision-tree.md && \
git commit -m "docs(rn-expo-router): decision-tree.md — Stack/Tabs/Drawer + modals + groups"
```

---

## Task 20: Write `rn-expo-router/references/examples/*.tsx`

**Files:**
- Create: `rn-expo-router/references/examples/layout-with-tabs.tsx`
- Create: `rn-expo-router/references/examples/modal-route.tsx`
- Create: `rn-expo-router/references/examples/typed-search-params.tsx`

- [ ] **Step 1: Write `layout-with-tabs.tsx`**

Create `/Users/lucadigerlando/my-skills/rn-expo-router/references/examples/layout-with-tabs.tsx`:

```tsx
// Place at: app/(tabs)/_layout.tsx
import { Tabs } from "expo-router";
import { Ionicons } from "@expo/vector-icons";

export default function TabsLayout() {
  return (
    <Tabs
      screenOptions={{
        tabBarActiveTintColor: "#0ea5e9",
        headerShown: false,
      }}
    >
      <Tabs.Screen
        name="feed"
        options={{
          title: "Feed",
          tabBarIcon: ({ color, size }) => (
            <Ionicons name="home-outline" color={color} size={size} />
          ),
        }}
      />
      <Tabs.Screen
        name="search"
        options={{
          title: "Search",
          tabBarIcon: ({ color, size }) => (
            <Ionicons name="search-outline" color={color} size={size} />
          ),
        }}
      />
      <Tabs.Screen
        name="settings"
        options={{
          title: "Settings",
          tabBarIcon: ({ color, size }) => (
            <Ionicons name="settings-outline" color={color} size={size} />
          ),
        }}
      />
    </Tabs>
  );
}
```

- [ ] **Step 2: Write `modal-route.tsx`**

Create `/Users/lucadigerlando/my-skills/rn-expo-router/references/examples/modal-route.tsx`:

```tsx
// Two files combined here for the example.

// FILE 1: app/_layout.tsx (root stack must declare the modal screen)
import { Stack } from "expo-router";
export function RootLayout() {
  return (
    <Stack>
      <Stack.Screen name="(tabs)" options={{ headerShown: false }} />
      <Stack.Screen
        name="filters-modal"
        options={{ presentation: "modal", title: "Filters" }}
      />
    </Stack>
  );
}

// FILE 2: app/filters-modal.tsx
import { View, Text, Pressable } from "react-native";
import { useRouter } from "expo-router";

export default function FiltersModal() {
  const router = useRouter();
  return (
    <View className="flex-1 bg-white dark:bg-zinc-900 p-4 gap-4">
      <Text className="text-xl font-semibold">Filters</Text>
      {/* …filter controls… */}
      <Pressable
        onPress={() => router.back()}
        className="self-end px-4 py-2 rounded-full bg-primary"
      >
        <Text className="text-white">Apply</Text>
      </Pressable>
    </View>
  );
}

// USAGE from anywhere:
//   import { useRouter } from "expo-router";
//   const router = useRouter();
//   <Pressable onPress={() => router.push("/filters-modal")}><Text>Open</Text></Pressable>
```

- [ ] **Step 3: Write `typed-search-params.tsx`**

Create `/Users/lucadigerlando/my-skills/rn-expo-router/references/examples/typed-search-params.tsx`:

```tsx
// Place at: app/profile/[id].tsx
import { View, Text } from "react-native";
import { useLocalSearchParams, Link } from "expo-router";

type Params = {
  id: string;
  tab?: "info" | "posts" | "likes";
};

export default function ProfileScreen() {
  const { id, tab = "info" } = useLocalSearchParams<Params>();

  return (
    <View className="flex-1 p-4 gap-4">
      <Text className="text-xl">Profile {id}</Text>
      <Text>Active tab: {tab}</Text>

      <View className="flex-row gap-2">
        <Link href={{ pathname: "/profile/[id]", params: { id, tab: "info" } }}>
          <Text className={tab === "info" ? "font-bold" : ""}>Info</Text>
        </Link>
        <Link href={{ pathname: "/profile/[id]", params: { id, tab: "posts" } }}>
          <Text className={tab === "posts" ? "font-bold" : ""}>Posts</Text>
        </Link>
        <Link href={{ pathname: "/profile/[id]", params: { id, tab: "likes" } }}>
          <Text className={tab === "likes" ? "font-bold" : ""}>Likes</Text>
        </Link>
      </View>
    </View>
  );
}
```

- [ ] **Step 4: Commit (skip-if-not-git)**

```bash
cd /Users/lucadigerlando/my-skills && \
git add rn-expo-router/references/examples && \
git commit -m "docs(rn-expo-router): 3 example layouts (tabs, modal, typed params)"
```

---

## Task 21: Trigger acceptance list for `rn-bootstrap`

**Files:**
- Create: `docs/superpowers/tests/triggers-rn-bootstrap.md`

- [ ] **Step 1: Write the trigger spec**

Create `/Users/lucadigerlando/my-skills/docs/superpowers/tests/triggers-rn-bootstrap.md`:

```markdown
# Trigger acceptance list — rn-bootstrap

## Should trigger (3+)
1. orchestrator routes here from `dev-flow` when `meta.json#stack == "expo-rn"` and `phase == "prd_drafted"`
2. user says: "scaffolda l'app Expo da questo PRD"
3. user says: "create RN app from PRD and DESIGN.md"

## Should NOT trigger (3+)
1. "Aggiungi una schermata di login" → expect rn-add-screen (Wave 2)
2. "Setup deploy on EAS" → expect rn-eas-deploy (Wave 3)
3. "Scaffolda l'app Next.js" → expect design-md-to-app (Next.js stack, untouched)

## Idempotency contract
1. Running the skill twice on the same project root MUST NOT duplicate package.json entries.
2. Running on a directory that already has package.json + app/ MUST report "already bootstrapped" and exit successfully.
3. Modifications to tailwind.config.js MUST be regenerated from DESIGN.md, not appended.

## Smoke test (post-bootstrap)
1. `package.json` exists with `expo`, `expo-router`, `nativewind`, `zustand`, `@tanstack/react-query`.
2. `app/_layout.tsx` exists and imports `../global.css`.
3. `tailwind.config.js` exists and contains colors derived from DESIGN.md.
4. `npx tsc --noEmit` exits 0.
5. `npx expo doctor` exits 0 (or with only warnings).
```

- [ ] **Step 2: Commit (skip-if-not-git)**

```bash
cd /Users/lucadigerlando/my-skills && \
git add docs/superpowers/tests/triggers-rn-bootstrap.md && \
git commit -m "test: trigger + smoke acceptance list for rn-bootstrap"
```

---

## Task 22: Vendor `contracts.md` into `rn-bootstrap/references/`

**Files:**
- Create: `rn-bootstrap/references/contracts.md` (copy from `dev-flow/references/contracts.md`)

This mirrors the pattern used by `module-add` (which has its own vendored `contracts.md`). Vendoring keeps the skill self-contained.

- [ ] **Step 1: Copy**

Run: `cp /Users/lucadigerlando/my-skills/dev-flow/references/contracts.md /Users/lucadigerlando/my-skills/rn-bootstrap/references/contracts.md`

- [ ] **Step 2: Verify**

Run: `head -5 /Users/lucadigerlando/my-skills/rn-bootstrap/references/contracts.md`
Expected: same first lines as the dev-flow version.

- [ ] **Step 3: Commit (skip-if-not-git)**

```bash
cd /Users/lucadigerlando/my-skills && \
git add rn-bootstrap/references/contracts.md && \
git commit -m "chore(rn-bootstrap): vendor dev-flow contracts.md"
```

---

## Task 23: Write `rn-bootstrap/references/stack-defaults.md`

**Files:**
- Create: `rn-bootstrap/references/stack-defaults.md`

This is a *snapshot* used at bootstrap time. It can diverge from `rn-fundamentals/references/stack-defaults.md` only via an explicit refresh — we keep both for separation of concerns (fundamentals = aspirational; bootstrap = exact at-install).

- [ ] **Step 1: Copy from rn-fundamentals**

Run: `cp /Users/lucadigerlando/my-skills/rn-fundamentals/references/stack-defaults.md /Users/lucadigerlando/my-skills/rn-bootstrap/references/stack-defaults.md`

- [ ] **Step 2: Add a header note**

Edit the first line of `/Users/lucadigerlando/my-skills/rn-bootstrap/references/stack-defaults.md` to read:

```markdown
> Bootstrap snapshot — kept in sync manually with rn-fundamentals/references/stack-defaults.md.
> Update both files together when bumping a major version.
```

(Replace the existing first `> Snapshot date: …` line with the above + keep date on a second line.)

- [ ] **Step 3: Commit (skip-if-not-git)**

```bash
cd /Users/lucadigerlando/my-skills && \
git add rn-bootstrap/references/stack-defaults.md && \
git commit -m "docs(rn-bootstrap): stack-defaults.md (snapshot for bootstrap moment)"
```

---

## Task 24: Write `rn-bootstrap/references/post-bootstrap-checklist.md`

**Files:**
- Create: `rn-bootstrap/references/post-bootstrap-checklist.md`

- [ ] **Step 1: Write the file**

Create `/Users/lucadigerlando/my-skills/rn-bootstrap/references/post-bootstrap-checklist.md`:

```markdown
# Post-bootstrap checklist

After `rn-bootstrap` finishes, verify each item before bumping `meta.json#phase` to `scaffolded`. The `scripts/verify.ts` automates most of this.

## File existence

- [ ] `package.json` with `expo`, `expo-router`, `nativewind`, `tailwindcss`, `zustand`, `@tanstack/react-query`, `react-native-reanimated`, `react-native-gesture-handler`, `react-native-safe-area-context`, `expo-image`, `@shopify/flash-list`.
- [ ] `app/_layout.tsx` imports `../global.css` and renders `<Stack />`.
- [ ] `app/index.tsx` exists with a "hello world" screen using NativeWind classes.
- [ ] `global.css` with `@tailwind base/components/utilities`.
- [ ] `tailwind.config.js` with `nativewind/preset` and tokens from DESIGN.md.
- [ ] `babel.config.js` with `nativewind/babel`.
- [ ] `metro.config.js` with `withNativeWind`.
- [ ] `app.json` with `expo.scheme`, `expo.experiments.typedRoutes: true`, `expo.newArchEnabled: true`.
- [ ] `tsconfig.json` with `extends: "expo/tsconfig.base"` and `paths` for `@/*`.
- [ ] `.env.example` listing `EXPO_PUBLIC_*` vars used by the app.
- [ ] `components/`, `lib/`, `store/`, `types/`, `assets/` directories (can be empty with `.gitkeep`).

## Tooling

- [ ] `npx tsc --noEmit` exits 0.
- [ ] `npx expo doctor` exits 0 or with only documented warnings (e.g. "no native modules").
- [ ] `npx expo start` starts Metro and shows the app in Expo Go / dev client.

## meta.json

- [ ] `meta.json#stack == "expo-rn"`.
- [ ] `meta.json#stack_config` populated (expo_sdk, nativewind, state_lib, backend, etc.).
- [ ] `meta.json#phase == "scaffolded"`.
- [ ] `meta.json#history` appended with this bootstrap event.

If any item fails: do NOT bump the phase. Report the failure and stop.
```

- [ ] **Step 2: Commit (skip-if-not-git)**

```bash
cd /Users/lucadigerlando/my-skills && \
git add rn-bootstrap/references/post-bootstrap-checklist.md && \
git commit -m "docs(rn-bootstrap): post-bootstrap-checklist.md (verification gate)"
```

---

## Task 25: Write `rn-bootstrap/scripts/init-expo-app.sh`

**Files:**
- Create: `rn-bootstrap/scripts/init-expo-app.sh`

- [ ] **Step 1: Write the script**

Create `/Users/lucadigerlando/my-skills/rn-bootstrap/scripts/init-expo-app.sh`:

```bash
#!/usr/bin/env bash
# init-expo-app.sh — create a new Expo + TypeScript app at the given project root.
# Idempotent: if package.json + app/ already exist, exits 0 with "already bootstrapped".
#
# Usage: init-expo-app.sh <project-root> <app-name>

set -euo pipefail

PROJECT_ROOT="${1:?project root required}"
APP_NAME="${2:?app name required}"

cd "$PROJECT_ROOT"

if [[ -f package.json && -d app ]]; then
  echo "[init-expo-app] already bootstrapped (package.json + app/ exist) — skipping"
  exit 0
fi

if [[ -f package.json ]]; then
  echo "[init-expo-app] package.json exists but app/ missing — refusing to overwrite, please clean up"
  exit 1
fi

echo "[init-expo-app] running create-expo-app …"
npx --yes create-expo-app@latest . \
    --template blank-typescript \
    --no-install

echo "[init-expo-app] adding expo-router preset …"
# create-expo-app with blank-typescript does NOT include expo-router. Install it now.
npm install expo-router

echo "[init-expo-app] done. Next: install-stack.sh"
```

- [ ] **Step 2: Make executable**

Run: `chmod +x /Users/lucadigerlando/my-skills/rn-bootstrap/scripts/init-expo-app.sh`

- [ ] **Step 3: Smoke test (dry-run — verify script parses)**

Run: `bash -n /Users/lucadigerlando/my-skills/rn-bootstrap/scripts/init-expo-app.sh && echo OK`
Expected: `OK`

- [ ] **Step 4: Commit (skip-if-not-git)**

```bash
cd /Users/lucadigerlando/my-skills && \
git add rn-bootstrap/scripts/init-expo-app.sh && \
git commit -m "feat(rn-bootstrap): init-expo-app.sh — idempotent Expo scaffold"
```

---

## Task 26: Write `rn-bootstrap/scripts/install-stack.sh`

**Files:**
- Create: `rn-bootstrap/scripts/install-stack.sh`

- [ ] **Step 1: Write the script**

Create `/Users/lucadigerlando/my-skills/rn-bootstrap/scripts/install-stack.sh`:

```bash
#!/usr/bin/env bash
# install-stack.sh — install the opinionated RN/Expo stack into an existing Expo app.
# Idempotent: re-running detects already-installed packages via npm.
#
# Usage: install-stack.sh <project-root>

set -euo pipefail

PROJECT_ROOT="${1:?project root required}"
cd "$PROJECT_ROOT"

if [[ ! -f package.json ]]; then
  echo "[install-stack] no package.json — run init-expo-app.sh first"
  exit 1
fi

echo "[install-stack] installing styling stack (NativeWind v4 + safe-area + expo-image + FlashList) …"
npx expo install \
  nativewind@^4 tailwindcss@^3.4 \
  react-native-safe-area-context \
  expo-image \
  @shopify/flash-list

echo "[install-stack] installing animations stack (Reanimated 3 + Gesture Handler) …"
# expo install will pick the version compatible with the Expo SDK
npx expo install react-native-reanimated react-native-gesture-handler

echo "[install-stack] installing state + data (Zustand + TanStack Query) …"
npm install zustand @tanstack/react-query

echo "[install-stack] installing dev tools (TypeScript types, prettier) …"
npm install --save-dev prettier prettier-plugin-tailwindcss

echo "[install-stack] done. Next: wire-nativewind.ts"
```

- [ ] **Step 2: Make executable + lint**

```bash
chmod +x /Users/lucadigerlando/my-skills/rn-bootstrap/scripts/install-stack.sh
bash -n /Users/lucadigerlando/my-skills/rn-bootstrap/scripts/install-stack.sh && echo OK
```
Expected: `OK`

- [ ] **Step 3: Commit (skip-if-not-git)**

```bash
cd /Users/lucadigerlando/my-skills && \
git add rn-bootstrap/scripts/install-stack.sh && \
git commit -m "feat(rn-bootstrap): install-stack.sh — opinionated dependencies"
```

---

## Task 27: Write `rn-bootstrap/scripts/wire-nativewind.ts`

**Files:**
- Create: `rn-bootstrap/scripts/wire-nativewind.ts`

This script reads `DESIGN.md` from the project root, parses the YAML/JSON token block, and writes `tailwind.config.js` + `global.css` + `babel.config.js` + `metro.config.js` accordingly. It's a TypeScript node script run with `npx tsx`.

- [ ] **Step 1: Write the script**

Create `/Users/lucadigerlando/my-skills/rn-bootstrap/scripts/wire-nativewind.ts`:

```typescript
#!/usr/bin/env -S npx tsx
// wire-nativewind.ts — generate NativeWind v4 config files from DESIGN.md tokens.
// Idempotent: overwrites the 4 generated files on every run.
//
// Usage: npx tsx wire-nativewind.ts <project-root>

import * as fs from "node:fs";
import * as path from "node:path";

type Tokens = {
  colors?: Record<string, string | Record<string, string>>;
  spacing?: Record<string, string>;
  borderRadius?: Record<string, string>;
  fontFamily?: Record<string, string[]>;
  fontSize?: Record<string, string | [string, { lineHeight?: string }]>;
};

function readDesignTokens(projectRoot: string): Tokens {
  const designPath = path.join(projectRoot, "DESIGN.md");
  if (!fs.existsSync(designPath)) {
    console.warn(`[wire-nativewind] no DESIGN.md at ${designPath}, using defaults`);
    return defaultTokens();
  }
  const md = fs.readFileSync(designPath, "utf8");
  // Convention: a fenced ```json block tagged "tokens" holds the tokens.
  const match = md.match(/```json tokens\n([\s\S]*?)\n```/);
  if (!match) {
    console.warn("[wire-nativewind] no ```json tokens block in DESIGN.md, using defaults");
    return defaultTokens();
  }
  try {
    return JSON.parse(match[1]) as Tokens;
  } catch (e) {
    console.error("[wire-nativewind] failed to parse tokens JSON:", e);
    process.exit(1);
  }
}

function defaultTokens(): Tokens {
  return {
    colors: {
      primary: "#0ea5e9",
      background: { DEFAULT: "#ffffff", dark: "#09090b" },
      foreground: { DEFAULT: "#09090b", dark: "#fafafa" },
    },
    borderRadius: { lg: "12px", md: "8px", sm: "4px" },
  };
}

function writeTailwindConfig(projectRoot: string, tokens: Tokens) {
  const config = `/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./app/**/*.{js,jsx,ts,tsx}", "./components/**/*.{js,jsx,ts,tsx}"],
  presets: [require("nativewind/preset")],
  darkMode: "class",
  theme: {
    extend: ${JSON.stringify({ ...tokens }, null, 6)},
  },
  plugins: [],
};
`;
  fs.writeFileSync(path.join(projectRoot, "tailwind.config.js"), config);
}

function writeGlobalCss(projectRoot: string) {
  fs.writeFileSync(
    path.join(projectRoot, "global.css"),
    "@tailwind base;\n@tailwind components;\n@tailwind utilities;\n",
  );
}

function writeBabelConfig(projectRoot: string) {
  fs.writeFileSync(
    path.join(projectRoot, "babel.config.js"),
    `module.exports = function (api) {
  api.cache(true);
  return {
    presets: [
      ["babel-preset-expo", { jsxImportSource: "nativewind" }],
      "nativewind/babel",
    ],
  };
};
`,
  );
}

function writeMetroConfig(projectRoot: string) {
  fs.writeFileSync(
    path.join(projectRoot, "metro.config.js"),
    `const { getDefaultConfig } = require("expo/metro-config");
const { withNativeWind } = require("nativewind/metro");

const config = getDefaultConfig(__dirname);
module.exports = withNativeWind(config, { input: "./global.css" });
`,
  );
}

function main() {
  const projectRoot = process.argv[2];
  if (!projectRoot) {
    console.error("Usage: wire-nativewind.ts <project-root>");
    process.exit(1);
  }
  const tokens = readDesignTokens(projectRoot);
  writeTailwindConfig(projectRoot, tokens);
  writeGlobalCss(projectRoot);
  writeBabelConfig(projectRoot);
  writeMetroConfig(projectRoot);
  console.log("[wire-nativewind] wrote tailwind.config.js, global.css, babel.config.js, metro.config.js");
}

main();
```

- [ ] **Step 2: Make executable + syntax check**

```bash
chmod +x /Users/lucadigerlando/my-skills/rn-bootstrap/scripts/wire-nativewind.ts
node --check /Users/lucadigerlando/my-skills/rn-bootstrap/scripts/wire-nativewind.ts 2>&1 || true
# (node --check works on .js; for .ts we rely on tsx at runtime. Lint with `npx tsc --noEmit`.)
```

- [ ] **Step 3: Smoke test (run against a tmp directory with no DESIGN.md)**

```bash
mkdir -p /tmp/rn-bootstrap-smoke && cd /tmp/rn-bootstrap-smoke && \
npx --yes tsx /Users/lucadigerlando/my-skills/rn-bootstrap/scripts/wire-nativewind.ts /tmp/rn-bootstrap-smoke && \
ls tailwind.config.js global.css babel.config.js metro.config.js && \
echo OK
```
Expected: `[wire-nativewind] no DESIGN.md…using defaults` then all 4 files listed then `OK`.

- [ ] **Step 4: Cleanup smoke test directory**

Run: `rm -rf /tmp/rn-bootstrap-smoke`

- [ ] **Step 5: Commit (skip-if-not-git)**

```bash
cd /Users/lucadigerlando/my-skills && \
git add rn-bootstrap/scripts/wire-nativewind.ts && \
git commit -m "feat(rn-bootstrap): wire-nativewind.ts — generate config files from DESIGN.md tokens"
```

---

## Task 28: Write `rn-bootstrap/scripts/verify.ts`

**Files:**
- Create: `rn-bootstrap/scripts/verify.ts`

- [ ] **Step 1: Write the script**

Create `/Users/lucadigerlando/my-skills/rn-bootstrap/scripts/verify.ts`:

```typescript
#!/usr/bin/env -S npx tsx
// verify.ts — post-bootstrap smoke test. Exits 0 if all checks pass, 1 otherwise.
//
// Usage: npx tsx verify.ts <project-root>

import * as fs from "node:fs";
import * as path from "node:path";
import { execSync } from "node:child_process";

type Check = { name: string; run: () => boolean };

const projectRoot = process.argv[2];
if (!projectRoot) {
  console.error("Usage: verify.ts <project-root>");
  process.exit(1);
}

const fileExists = (rel: string) => fs.existsSync(path.join(projectRoot, rel));
const packageJson = (): Record<string, unknown> | null => {
  try {
    return JSON.parse(fs.readFileSync(path.join(projectRoot, "package.json"), "utf8"));
  } catch {
    return null;
  }
};
const hasDep = (name: string): boolean => {
  const pkg = packageJson() as { dependencies?: Record<string, string>; devDependencies?: Record<string, string> } | null;
  if (!pkg) return false;
  return Boolean(pkg.dependencies?.[name]) || Boolean(pkg.devDependencies?.[name]);
};

const checks: Check[] = [
  { name: "package.json exists", run: () => fileExists("package.json") },
  { name: "dep: expo", run: () => hasDep("expo") },
  { name: "dep: expo-router", run: () => hasDep("expo-router") },
  { name: "dep: nativewind", run: () => hasDep("nativewind") },
  { name: "dep: tailwindcss", run: () => hasDep("tailwindcss") },
  { name: "dep: zustand", run: () => hasDep("zustand") },
  { name: "dep: @tanstack/react-query", run: () => hasDep("@tanstack/react-query") },
  { name: "dep: react-native-reanimated", run: () => hasDep("react-native-reanimated") },
  { name: "dep: react-native-gesture-handler", run: () => hasDep("react-native-gesture-handler") },
  { name: "dep: react-native-safe-area-context", run: () => hasDep("react-native-safe-area-context") },
  { name: "dep: expo-image", run: () => hasDep("expo-image") },
  { name: "dep: @shopify/flash-list", run: () => hasDep("@shopify/flash-list") },
  { name: "file: app/_layout.tsx", run: () => fileExists("app/_layout.tsx") },
  { name: "file: app/index.tsx", run: () => fileExists("app/index.tsx") },
  { name: "file: global.css", run: () => fileExists("global.css") },
  { name: "file: tailwind.config.js", run: () => fileExists("tailwind.config.js") },
  { name: "file: babel.config.js", run: () => fileExists("babel.config.js") },
  { name: "file: metro.config.js", run: () => fileExists("metro.config.js") },
  { name: "file: app.json with typedRoutes", run: () => {
    const p = path.join(projectRoot, "app.json");
    if (!fileExists("app.json")) return false;
    const cfg = JSON.parse(fs.readFileSync(p, "utf8"));
    return cfg?.expo?.experiments?.typedRoutes === true;
  }},
  { name: "tsc --noEmit passes", run: () => {
    try {
      execSync("npx tsc --noEmit", { cwd: projectRoot, stdio: "pipe" });
      return true;
    } catch {
      return false;
    }
  }},
];

let failed = 0;
for (const check of checks) {
  const ok = check.run();
  console.log(`${ok ? "✅" : "❌"} ${check.name}`);
  if (!ok) failed++;
}

if (failed > 0) {
  console.error(`\n${failed} check(s) failed.`);
  process.exit(1);
}
console.log("\nAll checks passed.");
```

- [ ] **Step 2: Make executable**

Run: `chmod +x /Users/lucadigerlando/my-skills/rn-bootstrap/scripts/verify.ts`

- [ ] **Step 3: Commit (skip-if-not-git)**

```bash
cd /Users/lucadigerlando/my-skills && \
git add rn-bootstrap/scripts/verify.ts && \
git commit -m "feat(rn-bootstrap): verify.ts — post-bootstrap smoke checks"
```

---

## Task 29: Write `rn-bootstrap/SKILL.md`

**Files:**
- Create: `rn-bootstrap/SKILL.md`

- [ ] **Step 1: Write the file**

Create `/Users/lucadigerlando/my-skills/rn-bootstrap/SKILL.md`:

````markdown
---
name: rn-bootstrap
description: 'Scaffold a new Expo + React Native app from a PROJECT.md + PRD.md + DESIGN.md using the opinionated stack (Expo Router, TypeScript, NativeWind v4, Zustand, TanStack Query, Reanimated 3, expo-image, FlashList). Reads .workflow/meta.json with stack="expo-rn" and phase in {prd_drafted, design_finalized}. Produces a running Expo app at the project root, sets phase to "scaffolded". Always idempotent: re-running detects existing files and skips. Use when dev-flow routes here from prd_drafted+expo-rn, or the user says "scaffolda app expo from PRD", "create RN app from this PRD/DESIGN", "bootstrap expo app". Not for: adding screens (rn-add-screen, Wave 2), modules (rn-module-add, Wave 3), Next.js scaffolding (design-md-to-app — different stack).'
---

# rn-bootstrap — scaffold Expo + RN from PRD/DESIGN

## Contract

See `references/contracts.md` (vendored from `dev-flow`). Key facts:
- Reads `<project-root>/.workflow/meta.json#stack` — must be `"expo-rn"`.
- Reads `<project-root>/{PROJECT.md, PRD.md, DESIGN.md}`. DESIGN.md is required for tokens; if absent, uses defaults from `references/stack-defaults.md`.
- Writes the app to `<project-root>/` (the same directory).
- Sets `meta.json#phase = "scaffolded"` on success.
- Always idempotent: re-running detects existing `package.json` + `app/` and exits 0.

## When this skill applies

- Orchestrator routes here from `dev-flow` when `meta.json#stack == "expo-rn"` and `meta.json#phase ∈ {prd_drafted, design_finalized}`.
- User says: "scaffolda app expo", "create RN app from PRD".

## Knowledge dependencies (read these first)

- `~/my-skills/rn-fundamentals/SKILL.md` — confirms Expo SDK + New Architecture + TypeScript + npm.
- `~/my-skills/rn-styling/references/nativewind-setup.md` — the 7-step NativeWind setup (this skill automates it).
- `~/my-skills/rn-expo-router/references/concepts.md` — folder layout for `app/`.

## Workflow

### Step 1 — Verify preconditions

Read `<project-root>/.workflow/meta.json`. Abort with a clear message if:
- file missing → "Run `dev-flow init_workflow.py` first."
- `stack != "expo-rn"` → "This skill is for stack=expo-rn. For Next.js use design-md-to-app."
- `phase ∉ {prd_drafted, design_finalized}` → "Expected phase prd_drafted or design_finalized, got X."

If `package.json` + `app/` already exist at project root: print "Already bootstrapped, nothing to do", set phase to scaffolded if not already, exit 0.

### Step 2 — Run create-expo-app

Run `scripts/init-expo-app.sh <project-root> <app-name>`. The app name comes from `meta.json#project_name` (or `PROJECT.md` title).

### Step 3 — Install opinionated stack

Run `scripts/install-stack.sh <project-root>`. Installs NativeWind, Zustand, TanStack Query, Reanimated 3, RNGH, expo-image, FlashList.

### Step 4 — Wire NativeWind from DESIGN.md tokens

Run `npx tsx scripts/wire-nativewind.ts <project-root>`. Generates `tailwind.config.js`, `global.css`, `babel.config.js`, `metro.config.js`.

### Step 5 — Generate folder structure + boilerplate

Create (only if absent — idempotent):
- `app/_layout.tsx` — Stack root, imports `../global.css`, renders `<Stack />`.
- `app/index.tsx` — hello-world screen using NativeWind classes.
- `components/`, `lib/`, `store/`, `types/`, `assets/` — empty dirs with `.gitkeep`.
- `.env.example` — empty stub with `EXPO_PUBLIC_API_URL=`.
- `tsconfig.json` — extend `expo/tsconfig.base`, add `paths` for `@/*`.

Also patch `app.json`:
- `expo.scheme` — set to a kebab-case of `meta.json#project_name`.
- `expo.experiments.typedRoutes` — `true`.
- `expo.newArchEnabled` — `true`.
- `expo.plugins` — add `"expo-router"`.

### Step 6 — Verify (scripts/verify.ts)

Run `npx tsx scripts/verify.ts <project-root>`. If exit code != 0, do NOT bump phase. Report failures from `references/post-bootstrap-checklist.md`.

### Step 7 — Update meta.json + commit

Update `meta.json`:
- `stack_config`: merge in `{ expo_sdk: "<X>", nativewind: true, state_lib: "zustand", data_lib: "tanstack-query", backend: null }`.
- `phase`: set to `"scaffolded"`.
- `history`: append `{ at: <iso>, skill: "rn-bootstrap", action: "scaffolded" }`.

If `<project-root>` is a git repo, create a commit: `chore: scaffold Expo + RN app via rn-bootstrap`.

## Sources

- Course: codewithbeto.dev/rnCourse — free lessons 5-6 (Creating Your First App, Project Structure).
- Official: https://docs.expo.dev/get-started/create-a-project/
- Official: https://www.nativewind.dev/v4/getting-started/expo-router
````

- [ ] **Step 2: Verify frontmatter**

Run: `python3 -c "import yaml; d=open('/Users/lucadigerlando/my-skills/rn-bootstrap/SKILL.md').read(); fm=d.split('---')[1]; print(list(yaml.safe_load(fm).keys()))"`
Expected: `['name', 'description']`

- [ ] **Step 3: Commit (skip-if-not-git)**

```bash
cd /Users/lucadigerlando/my-skills && \
git add rn-bootstrap/SKILL.md && \
git commit -m "feat(rn-bootstrap): SKILL.md — full workflow + contract"
```

---

## Task 30: Write `dev-flow/references/stack-expo-rn.md`

**Files:**
- Create: `dev-flow/references/stack-expo-rn.md`

- [ ] **Step 1: Write the file**

Create `/Users/lucadigerlando/my-skills/dev-flow/references/stack-expo-rn.md`:

```markdown
> Sources: internal spec docs/superpowers/specs/2026-05-16-rn-expo-skills-set-design.md

# Stack: expo-rn

Identifier in `meta.json#stack`: **`"expo-rn"`**

## What it means

The project targets mobile (iOS + Android) using **Expo + React Native** with the opinionated stack defined by the `rn-*` skill family.

## Routing — which skill for which phase

| Phase | Skill |
|---|---|
| `prd_drafted` or `design_finalized` | `rn-bootstrap` |
| `scaffolded` | `rn-add-screen` (Wave 2) for UI work, `rn-module-add` (Wave 3) for auth/db/payments |
| `feature_complete` | `rn-eas-deploy` (Wave 3) |

(Skills marked "Wave 2/3" are not yet implemented as of this snapshot — they exist as design entries in the spec.)

## Required sub-keys in `meta.json#stack_config`

After `rn-bootstrap` runs:
```json
{
  "stack": "expo-rn",
  "stack_config": {
    "expo_sdk": "53",
    "nativewind": true,
    "state_lib": "zustand",
    "data_lib": "tanstack-query",
    "backend": null,
    "payments_lib": null
  }
}
```

`backend` and `payments_lib` start as `null` and are populated by `rn-module-add` when those modules are wired.

## Knowledge skills available (auto-invoked when context matches)

- `rn-fundamentals` — foundational rules (Expo / TS / New Architecture)
- `rn-styling` — NativeWind v4, safe area, dark mode
- `rn-expo-router` — file-based routing, typed routes, modals

## Family membership

Operative skills in this stack: `rn-bootstrap` (Wave 1), `rn-add-screen` (Wave 2), `rn-module-add` (Wave 3), `rn-write-tests` (Wave 2), `rn-eas-deploy` (Wave 3).

Knowledge skills: `rn-fundamentals`, `rn-components-apis` (Wave 2), `rn-styling`, `rn-expo-router`, `rn-data-fetching` (Wave 2), `rn-animations-gestures` (Wave 3), `rn-push-notifications` (Wave 3), `rn-backend` (Wave 3, provider-agnostic), `rn-eas-build-submit-update` (Wave 3), `rn-publishing-payments` (Wave 3).

## NEVER use these skills on this stack

- `design-md-to-app` — Next.js scaffolder, would produce a web app.
- `module-add` — Next.js module wirer.
- `screenshot-to-page` — Next.js screen generator.
- `setup-deploy` — Vercel/Render/Fly, not EAS.

(These are reserved for `stack="nextjs"`.)
```

- [ ] **Step 2: Commit (skip-if-not-git)**

```bash
cd /Users/lucadigerlando/my-skills && \
git add dev-flow/references/stack-expo-rn.md && \
git commit -m "docs(dev-flow): stack-expo-rn.md — stack definition + routing for RN"
```

---

## Task 31: Modify `dev-flow/SKILL.md` to add the expo-rn routing rows

**Files:**
- Modify: `dev-flow/SKILL.md`

- [ ] **Step 1: Read the current file to find the routing table**

Run: `grep -n "Phase\|stack\|nextjs\|design-md-to-app" /Users/lucadigerlando/my-skills/dev-flow/SKILL.md | head -30`

Locate the routing section. If `dev-flow/SKILL.md` does NOT yet have a stack-aware routing table, the modification is more invasive — proceed to Step 2a. If it does, proceed to Step 2b.

- [ ] **Step 2a (if no stack-aware routing yet): add the section near the existing routing rules**

Open `dev-flow/SKILL.md`. Locate the section that describes how `dev-flow` decides "what to do next" (phase machine). Insert this subsection right before "## Phase machine" or equivalent:

```markdown
## Stack-aware routing

`dev-flow` reads `meta.json#stack` and routes to a stack-specific family of operative skills.

| stack value | family | bootstrap skill | reference |
|---|---|---|---|
| `nextjs` (default if missing) | existing | `design-md-to-app` | (this file) |
| `expo-rn` | RN/Expo | `rn-bootstrap` | `references/stack-expo-rn.md` |

When `meta.json#stack == "expo-rn"`:
- `prd_drafted` or `design_finalized` → invoke `rn-bootstrap`
- `scaffolded` → invoke `rn-add-screen` (UI) or `rn-module-add` (backend/infra)
- `feature_complete` → invoke `rn-eas-deploy`

If a stack value is not recognized, refuse and ask the user which stack to use. NEVER silently fall back to Next.js when stack is set explicitly to something else.
```

- [ ] **Step 2b (if a routing table exists): just add the new row**

Edit the table to add `| expo-rn | rn-bootstrap |` row, and add a note referencing `references/stack-expo-rn.md`.

- [ ] **Step 3: Verify frontmatter still valid**

Run: `python3 -c "import yaml; d=open('/Users/lucadigerlando/my-skills/dev-flow/SKILL.md').read(); fm=d.split('---')[1]; print(list(yaml.safe_load(fm).keys()))"`
Expected: at least `name` and `description`.

- [ ] **Step 4: Commit (skip-if-not-git)**

```bash
cd /Users/lucadigerlando/my-skills && \
git add dev-flow/SKILL.md && \
git commit -m "feat(dev-flow): stack-aware routing (nextjs default + expo-rn for RN)"
```

---

## Task 32: Modify `prd-from-idea/SKILL.md` to ask "target: web/mobile/desktop?"

**Files:**
- Modify: `prd-from-idea/SKILL.md`

- [ ] **Step 1: Locate the discovery questions section**

Run: `grep -n "discovery\|question\|ask\|step" /Users/lucadigerlando/my-skills/prd-from-idea/SKILL.md | head -20`

- [ ] **Step 2: Add the target-platform question**

In the discovery questions section of `prd-from-idea/SKILL.md`, add a new question early in the flow (before any feature-specific questions):

```markdown
### Q: target platform

Ask: "What's the primary target — web, mobile (iOS+Android), or desktop?"

Map answer → `meta.json#stack`:
- "web" or "web app" or unspecified → `stack: "nextjs"` (current default)
- "mobile" or "iOS" or "Android" or "mobile app" or "native app" → `stack: "expo-rn"`
- "desktop" → out of scope for this skill set — refuse politely and refer the user to Tauri/Electron docs.

Write `stack` into `meta.json` immediately so downstream skills (`prd-to-tasks`, `dev-flow` routing) see it.
```

Insert it as a new subsection in the workflow, ideally as one of the first 2-3 questions asked.

- [ ] **Step 3: Verify frontmatter still valid**

Run: `python3 -c "import yaml; d=open('/Users/lucadigerlando/my-skills/prd-from-idea/SKILL.md').read(); fm=d.split('---')[1]; print(list(yaml.safe_load(fm).keys()))"`

- [ ] **Step 4: Commit (skip-if-not-git)**

```bash
cd /Users/lucadigerlando/my-skills && \
git add prd-from-idea/SKILL.md && \
git commit -m "feat(prd-from-idea): ask target platform (web/mobile/desktop) → set meta.json#stack"
```

---

## Task 33: End-to-end Wave 1 smoke test

**Files:**
- Create: `/tmp/rn-wave1-smoke/PROJECT.md`, `/tmp/rn-wave1-smoke/PRD.md`, `/tmp/rn-wave1-smoke/DESIGN.md`, `/tmp/rn-wave1-smoke/.workflow/meta.json`

This is the acceptance test for the entire Wave 1. We run the bootstrap end-to-end on a throwaway directory and verify everything compiles.

- [ ] **Step 1: Set up the test project**

Run:
```bash
mkdir -p /tmp/rn-wave1-smoke/.workflow && cd /tmp/rn-wave1-smoke && \
cat > PROJECT.md <<'EOF'
# Smoke Test App
A throwaway project to verify rn-bootstrap end-to-end.
EOF
cat > PRD.md <<'EOF'
# PRD — Smoke Test
One user story: app opens, shows "hello world".
EOF
cat > DESIGN.md <<'EOF'
# Design tokens

```json tokens
{
  "colors": {
    "primary": "#0ea5e9",
    "background": { "DEFAULT": "#ffffff", "dark": "#09090b" }
  },
  "borderRadius": { "lg": "12px", "md": "8px" }
}
```
EOF
cat > .workflow/meta.json <<'EOF'
{
  "project_name": "smoke-test-app",
  "stack": "expo-rn",
  "phase": "prd_drafted",
  "stack_config": {},
  "history": []
}
EOF
```

- [ ] **Step 2: Run init-expo-app.sh**

Run: `bash /Users/lucadigerlando/my-skills/rn-bootstrap/scripts/init-expo-app.sh /tmp/rn-wave1-smoke smoke-test-app`

Expected: completes without error. `package.json` and `app/` exist after.

> Note: this step downloads + installs Expo. It takes several minutes and ~500MB. If you are network-constrained, mock with `mkdir -p app && echo '{"name":"smoke-test-app","dependencies":{"expo":"^53","expo-router":"^4"}}' > package.json` instead.

- [ ] **Step 3: Run install-stack.sh**

Run: `bash /Users/lucadigerlando/my-skills/rn-bootstrap/scripts/install-stack.sh /tmp/rn-wave1-smoke`

Expected: completes without error. `package.json` now contains nativewind, zustand, @tanstack/react-query, etc.

- [ ] **Step 4: Run wire-nativewind.ts**

Run: `npx --yes tsx /Users/lucadigerlando/my-skills/rn-bootstrap/scripts/wire-nativewind.ts /tmp/rn-wave1-smoke`

Expected: writes 4 files. `tailwind.config.js` contains the `primary: "#0ea5e9"` color from DESIGN.md.

- [ ] **Step 5: Generate the minimal app boilerplate manually**

(This step would be performed by step 5 of the rn-bootstrap workflow; we do it by hand here because that part is human-readable instructions in the SKILL.md, not a script yet. Future Wave 2 task: extract into `scripts/generate-boilerplate.ts`.)

Run:
```bash
cd /tmp/rn-wave1-smoke && \
mkdir -p app components lib store types assets && \
touch components/.gitkeep lib/.gitkeep store/.gitkeep types/.gitkeep assets/.gitkeep && \
cat > app/_layout.tsx <<'EOF'
import "../global.css";
import { Stack } from "expo-router";
export default function RootLayout() {
  return <Stack />;
}
EOF
cat > app/index.tsx <<'EOF'
import { Text } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
export default function Home() {
  return (
    <SafeAreaView className="flex-1 bg-white dark:bg-zinc-900 items-center justify-center">
      <Text className="text-2xl text-zinc-900 dark:text-zinc-50">Hello, smoke test 👋</Text>
    </SafeAreaView>
  );
}
EOF
```

Also patch `app.json` to enable typedRoutes + newArchEnabled + scheme:
```bash
node -e "
const fs=require('fs');
const p='/tmp/rn-wave1-smoke/app.json';
const c=JSON.parse(fs.readFileSync(p,'utf8'));
c.expo.scheme='smoke-test-app';
c.expo.experiments={...(c.expo.experiments||{}),typedRoutes:true};
c.expo.newArchEnabled=true;
c.expo.plugins=Array.from(new Set([...(c.expo.plugins||[]),'expo-router']));
fs.writeFileSync(p,JSON.stringify(c,null,2));
"
```

- [ ] **Step 6: Run verify.ts**

Run: `npx --yes tsx /Users/lucadigerlando/my-skills/rn-bootstrap/scripts/verify.ts /tmp/rn-wave1-smoke`

Expected: all checks `✅`, "All checks passed." exit code 0.

If `tsc --noEmit` fails: check the example test app uses paths correctly. This is the most likely failure point.

- [ ] **Step 7: Idempotency test**

Re-run `bash /Users/lucadigerlando/my-skills/rn-bootstrap/scripts/init-expo-app.sh /tmp/rn-wave1-smoke smoke-test-app`

Expected: `[init-expo-app] already bootstrapped (package.json + app/ exist) — skipping`. Exit code 0.

- [ ] **Step 8: Cleanup**

Run: `rm -rf /tmp/rn-wave1-smoke`

- [ ] **Step 9: Document the run**

Append to `docs/superpowers/tests/triggers-rn-bootstrap.md` a section:

```markdown
## Smoke test run log

- Date: <YYYY-MM-DD>
- Expo SDK installed: <X>
- All verify.ts checks passed: yes/no
- Idempotency: confirmed
- Notes: …
```

- [ ] **Step 10: Commit (skip-if-not-git)**

```bash
cd /Users/lucadigerlando/my-skills && \
git add docs/superpowers/tests/triggers-rn-bootstrap.md && \
git commit -m "test(rn-bootstrap): smoke test run logged for Wave 1 acceptance"
```

---

## Task 34: Trigger acceptance verification (manual)

**Files:**
- (none — this is a verification ritual, not a code change)

- [ ] **Step 1: For each of the 4 skills, run the trigger acceptance list against the live Claude**

For each skill (`rn-fundamentals`, `rn-styling`, `rn-expo-router`, `rn-bootstrap`):

1. Open a fresh Claude Code session in `/Users/lucadigerlando/my-skills/`.
2. For each "Should trigger" sentence in `docs/superpowers/tests/triggers-<skill>.md`, paste it and confirm the skill IS selected (Claude reads the SKILL.md).
3. For each "Should NOT trigger" sentence, paste it and confirm the skill is NOT selected (a different/no skill is selected).
4. For each "Anti-pattern" entry, ask Claude "is X OK?" and confirm Claude refuses or warns based on the skill content.

- [ ] **Step 2: Record results**

For each skill, append a "Trigger verification" section to `docs/superpowers/tests/triggers-<skill>.md` with date + pass/fail per item.

- [ ] **Step 3: Iterate on `description:` if a trigger misses**

If a "Should trigger" sentence does NOT activate the skill, the `description:` is not specific enough. Edit it (more concrete trigger words / Italian + English) and retest.

- [ ] **Step 4: Commit verification results (skip-if-not-git)**

```bash
cd /Users/lucadigerlando/my-skills && \
git add docs/superpowers/tests && \
git commit -m "test: trigger verification results for Wave 1 skills"
```

---

## Self-Review

Performed after writing the plan, before handing off.

**1. Spec coverage** (cross-checked against `docs/superpowers/specs/2026-05-16-rn-expo-skills-set-design.md`):

| Spec section | Where covered in plan |
|---|---|
| §3 Architecture (two families, naming) | File Structure section + Tasks 0b, 30 |
| §4 Inventory — K1 rn-fundamentals (deep) | Tasks 1–6 |
| §4 Inventory — K3 rn-styling (deep) | Tasks 7–13 |
| §4 Inventory — K4 rn-expo-router (deep) | Tasks 14–20 |
| §4 Inventory — O1 rn-bootstrap | Tasks 21–29 |
| §5.1 Template KNOWLEDGE | Used in Tasks 2, 8, 15 |
| §5.2 Template OPERATIVA | Used in Task 29 |
| §5.3 Convenzioni: English, frontmatter, `Not for:`, fonti marcate | All SKILL.md + references include sources line |
| §6 Sources mapping | Each references file opens with `> Sources:` |
| §7.1 dev-flow routing table extended | Task 31 |
| §7.2 dev-flow/references/stack-expo-rn.md | Task 30 |
| §7.3 prd-from-idea: target question | Task 32 |
| §8 Wave 1 build order: K1 → K3 → K4 → O1 → dev-flow | Tasks 1–32 (in order) |
| §9 Validation: trigger tests + e2e smoke + sources currency | Tasks 1, 7, 14, 21, 33, 34 |
| §10 YAGNI exclusions (no bare, no Detox, no Redux, no react-navigation, no RN Web, no Tamagui) | Reflected in patterns.md / anti-patterns sections |

**Gaps found**: none material. Wave 2/3 skills are out of scope by design.

**2. Placeholder scan**: searched for TBD/TODO/`implement later`/`similar to Task N` — none in the plan. All code blocks are concrete.

**3. Type / naming consistency**:
- `meta.json#stack == "expo-rn"` — consistent across spec, plan, dev-flow ref, prd-from-idea modification, rn-bootstrap workflow.
- Script signatures: `init-expo-app.sh <project-root> <app-name>`, `install-stack.sh <project-root>`, `wire-nativewind.ts <project-root>`, `verify.ts <project-root>` — used consistently in Task 33 smoke test.
- Token convention: `` ```json tokens `` fenced block in DESIGN.md — used in both `wire-nativewind.ts` (Task 27) and smoke test DESIGN.md (Task 33).
- All `rn-*` skill names match across the inventory table, SKILL.md frontmatter names, and references in `dev-flow/references/stack-expo-rn.md`.

No fixes needed.

---

## Execution Handoff

Plan saved to [docs/superpowers/plans/2026-05-16-rn-expo-skills-wave1.md](docs/superpowers/plans/2026-05-16-rn-expo-skills-wave1.md).

**Two execution options:**

**1. Subagent-Driven (recommended)** — I dispatch a fresh subagent per task, review the diff between tasks, fast iteration. Best for a 34-task plan where each task is bite-sized and most are isolated file writes.

**2. Inline Execution** — I execute tasks in this session using `executing-plans`, with batch checkpoints. Lower context overhead per task, but my context fills up faster.

**Which approach?**
