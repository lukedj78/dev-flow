---
name: rn-write-tests
description: 'Use to write tests for an Expo + RN app: Jest + React Native Testing Library for unit/integration (components, hooks, queries, mutations) and Maestro for end-to-end flows (sign-in, navigation, forms). Sets up the testing stack on first call (jest-expo preset, RNTL, jest config) and writes a focused test next to the source file. Triggers on: "write tests for X", "add e2e test", "mock expo-notifications", "test this hook". Not for: choosing what to test (the user decides), running the existing test suite (just `npm test`), or testing pure logic outside an Expo project.'
---

# rn-write-tests — Jest + RNTL + Maestro testing for Expo + RN

## Contract

See `references/contracts.md` (vendored from `dev-flow`). Key facts:
- Reads `<project-root>/.workflow/meta.json#stack.framework` — must be `"expo-rn"`.
- Adds dev dependencies + Jest config on first call (idempotent: detects existing setup).
- Writes test files under `<project-root>/__tests__/` (Jest convention) for unit/integration.
- Writes Maestro YAML flows under `<project-root>/.maestro/` for e2e.
- Does NOT modify `meta.json#phase`.

## When this skill applies

- User asks to write a test for a specific source file or flow.
- Orchestrator does NOT route here automatically — test writing is on-demand.

## Knowledge dependencies (read these first)

- `rn-fundamentals/SKILL.md` — TS strict, modern primitives the tests will see.
- `rn-data-fetching/references/patterns.md` — query/mutation patterns the tests must exercise.

## Workflow

### Step 1 — Verify preconditions

Read `.workflow/meta.json`. Abort if `stack.framework != "expo-rn"`.

### Step 2 — Detect / install the test stack

Check if `jest`, `jest-expo`, `@testing-library/react-native` are in `package.json`. If not:

```bash
npx expo install --dev \
  jest jest-expo \
  @testing-library/react-native \
  @types/jest -- --legacy-peer-deps
```

(Native matchers like `toBeOnTheScreen()` are built into `@testing-library/react-native` v12.4+ — no separate `@testing-library/jest-native` needed. See `references/jest-setup.md` for the full config.)

For Maestro: detect `.maestro/` directory. If missing AND user wants e2e, see `references/maestro.md` (manual install, not npm — Java 17+, `.maestro/` flow layout, `testID` conventions, and ⚠️ the Expo Go vs dev-build caveat: Expo Go can't `launchApp` your own `appId`, use `openLink: exp://…`).

### Step 3 — Choose what to test

Ask the user (one round-trip) what to test:
- **Component** (renders, props, interactions) → RNTL.
- **Hook** (`useQuery`, `useMutation`, custom hook) → RNTL `renderHook`.
- **Pure function** (utility, helper) → plain Jest.
- **e2e flow** (sign-in, navigation, form submit) → Maestro.

If the file under test is `lib/api.ts`, write a Jest test of the function with `fetch` mocked.
If the file under test is `app/(auth)/sign-in.tsx`, write an RNTL test of the screen + a Maestro flow of the user journey.

### Step 4 — Write the test

Use the canonical patterns from `references/rntl-patterns.md` (or `references/jest-setup.md` for utilities, or `references/maestro.md` for e2e).

Test files:
- Unit/integration: `__tests__/<mirror-source-path>.test.tsx` (or `.test.ts` for non-JSX).
- e2e: `.maestro/<flow-name>.yaml`.

### Step 5 — Run the test

```bash
cd <project-root> && npm test -- --runInBand --bail
```

(For Maestro: `maestro test .maestro/<flow-name>.yaml`.)

Test MUST pass. If it doesn't:
1. Read the failure. Is it a missing mock? An assumption about the test API?
2. Fix the test (NOT the source — that's a separate task).
3. Re-run.

### Step 6 — Commit

```bash
git add __tests__/<path>.test.tsx
git commit -m "test(<area>): cover <what>"
```

## Common anti-patterns (NEVER do)

- ❌ **Detox** — heavy, Expo Go unfriendly, requires native build. Use Maestro.
- ❌ **Enzyme** — abandoned. RNTL only.
- ❌ Snapshot for every component — only for stable design-system primitives.
- ❌ `jest.fn()` without typing the return → tests pass on wrong shape.
- ❌ Testing implementation details (state names, internal function calls) → brittle. Test user-facing behavior.
- ❌ Testing TanStack Query result shape directly → mock the queryFn instead and assert UI.
- ❌ Skipping cleanup → tests leak state. Always use RNTL's auto-cleanup (default).
- ❌ Sleeping `await new Promise(r => setTimeout(r, 1000))` → use `waitFor` with explicit assertions.

## Updating meta.json (recommended pattern)

This skill does NOT advance `meta.json#phase` (see Contract above) — never call `set-phase`. It only records the artifact and appends history, using the canonical script when available:

```bash
# Wherever dev-flow is installed (e.g. ~/.claude/skills/dev-flow/), invoke:
python3 .../dev-flow/scripts/update_meta.py <project-root> record-artifact \
    --path <relative-path> --produced-by '<this-skill-name>' [--derived-from <p1> <p2> ...]
python3 .../dev-flow/scripts/update_meta.py <project-root> append-history \
    --skill '<this-skill-name>' --inputs '{...}' --outputs '{...}' --phase-after <current_phase>
```

The script normalizes legacy kebab-case aliases (e.g. `module-added` → `module_added`) and writes the canonical sha256 + timestamp into `meta.json#artifacts`. **Fall back to direct JSON editing only if the script is not on PATH** (and warn the user).

## Sources

- Course: codewithbeto.dev/rnCourse — "Testing" module (paid, distilled).
- Official: https://callstack.github.io/react-native-testing-library/
- Official: https://docs.expo.dev/develop/unit-testing/
- Official: https://maestro.mobile.dev/
