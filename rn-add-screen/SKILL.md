---
name: rn-add-screen
description: 'Use to add a new screen to an existing Expo + RN app: from a description, a wireframe, or a screenshot, generate the route file in app/ (Expo Router file-based), wire up data fetching via TanStack Query if needed, apply NativeWind classes from the project DESIGN.md tokens, and respect the scaffolded folder layout. Reads .workflow/meta.json with stack.framework="expo-rn" and phase ≥ "scaffolded". Use when dev-flow routes here from scaffolded+expo-rn, or the user says "add a login screen", "create a profile screen from this screenshot", "aggiungi una schermata X". Not for: scaffolding the app (rn-bootstrap), adding backend modules (rn-module-add Wave 3), pure styling changes to an existing screen (rn-styling).'
---

# rn-add-screen — add a new screen to a scaffolded RN/Expo app

## Contract

See `references/contracts.md` (vendored from `dev-flow`). Key facts:
- Reads `<project-root>/.workflow/meta.json#stack.framework` — must be `"expo-rn"`.
- Requires `meta.json#phase ≥ "scaffolded"` (run `rn-bootstrap` first).
- Reads `DESIGN.md` from project root for the design tokens.
- Writes ONE new file under `<project-root>/app/...` per call. Optional: components under `<project-root>/components/`, hooks under `<project-root>/lib/queries/`.
- Sets `meta.json#phase = "page_generated"` after the first screen, then leaves it (subsequent screens are still `page_generated`).
- Always idempotent: re-adding the same route detects the existing file and reports.

## When this skill applies

- Phase is `scaffolded` or `page_generated`.
- The user describes a screen: name, content, behavior. Or provides a screenshot/wireframe to translate.
- Orchestrator routes here from `dev-flow`.

## Knowledge dependencies (read these first)

- `rn-fundamentals/SKILL.md` — file layout, modern primitives.
- `rn-styling/references/patterns.md` — root screen pattern, dark mode, FlashList.
- `rn-expo-router/references/concepts.md` — file-based routing rules.
- `rn-expo-router/references/patterns.md` — modal vs push, search params, auth gates.
- `rn-data-fetching/references/patterns.md` — if the screen fetches data, use the patterns there.
- `rn-components-apis/references/decision-tree.md` — which primitive (FlashList vs ScrollView, Pressable, etc.).

## Workflow

### Step 1 — Verify preconditions

Read `.workflow/meta.json`. Abort with clear message if:
- `stack.framework != "expo-rn"` → "Wrong stack."
- `phase < "scaffolded"` → "Run rn-bootstrap first."

### Step 2 — Understand the screen

Gather from user (one round-trip max — collect everything at once):

- **Route path** in Expo Router convention: `/profile/[id]` → `app/profile/[id].tsx`. Group? `(auth)/sign-in`? Modal? See `references/screen-patterns.md` for the mapping.
- **Top-level layout**: scroll vs FlashList vs form. Modal or full-screen.
- **Data**: does it need a query? A mutation? Static?
- **Navigation in**: how does the user reach it (link from another screen, push, modal, deep link)?
- **Navigation out**: what does it do on success / back?

If a screenshot is provided, infer the above and confirm with the user before generating.

### Step 3 — Pick the right scaffold template

See `references/screen-patterns.md` for canonical templates:
- List screen (FlashList + TanStack Query)
- Detail screen (typed search params + query)
- Form screen (KeyboardAvoidingView + controlled inputs + mutation)
- Modal screen (presentation: "modal", dismiss button)
- Auth-gated screen (inside `(app)/` group)

Pick ONE template; do not mix unless the screen is genuinely hybrid.

### Step 4 — Generate the file

Write to `<project-root>/app/<route>.tsx`. The file MUST:
- Use `SafeAreaView` from `react-native-safe-area-context` at root.
- Use NativeWind classes from existing `tailwind.config.js` tokens (no magic colors).
- Use `Pressable`, `expo-image`, `FlashList` as appropriate.
- If using data, use TanStack Query with a centralized query key (add to `lib/query-keys.ts` if it doesn't exist).
- If using a form, use controlled state + a `useMutation` hook for submit.

### Step 5 — Update related files (only if necessary)

- If the screen uses a NEW shared component, write it under `<project-root>/components/`.
- If the screen uses a NEW query/mutation, write the hook under `<project-root>/lib/queries/` or `lib/mutations/`.
- If the screen is reachable from another screen, add a `<Link>` there ONLY IF the user explicitly asks.

### Step 6 — Verify

Run:
- `npx tsc --noEmit` from project root → must pass.
- `npx expo-router-typegen` (if available) so typed routes refresh.

If typing fails, fix and re-verify before reporting done.

### Step 7 — Update meta.json + commit

- `meta.json#phase`: if currently `"scaffolded"`, set to `"page_generated"`. Otherwise leave.
- `meta.json#history`: append `{ skill: "rn-add-screen", ran_at: <iso>, outputs: [<file paths>], phase_before: <prev>, phase_after: <current> }`.
- If git repo: `git add` the new files + `git commit -m "feat(<route>): add <screen-name> screen"`.

## Common anti-patterns (NEVER do)

- ❌ Add layout configuration (`<Tabs.Screen>`, `<Stack.Screen>`) inside the screen file. Layout lives in `_layout.tsx`.
- ❌ Rewrite an existing screen unless the user explicitly says "rewrite".
- ❌ Hardcode colors or spacing in the new file — use Tailwind tokens.
- ❌ Use `Image` from `react-native` — `expo-image`.
- ❌ Use `FlatList` for a long list — `FlashList`.
- ❌ Use `fetch + useEffect` for production data — TanStack Query.
- ❌ Touch unrelated files (`tailwind.config.js`, `app.json`, other routes).

## Updating meta.json (recommended pattern)

When this skill modifies state (artifact written, phase advanced, history appended), use the canonical script when available:

```bash
# Wherever dev-flow is installed (e.g. ~/.claude/skills/dev-flow/), invoke:
python3 .../dev-flow/scripts/update_meta.py <project-root> record-artifact \
    --path <relative-path> --produced-by '<this-skill-name>' [--derived-from <p1> <p2> ...]
python3 .../dev-flow/scripts/update_meta.py <project-root> set-phase <new_phase>
python3 .../dev-flow/scripts/update_meta.py <project-root> append-history \
    --skill '<this-skill-name>' --inputs '{...}' --outputs '{...}' --phase-after <new_phase>
```

The script enforces phase monotonicity, normalizes legacy kebab-case aliases (e.g. `module-added` → `module_added`), and writes the canonical sha256 + timestamp into `meta.json#artifacts`. **Fall back to direct JSON editing only if the script is not on PATH** (and warn the user).

## Sources

- Course: codewithbeto.dev/rnCourse — modules "Components and APIs" + "Style and Design" (paid, distilled).
- Knowledge skills consumed (see above).
