---
name: rn-upgrade
description: 'Use to upgrade an existing Expo + RN project to a newer Expo SDK: bump `expo`, run `npx expo install --fix` to align every dependency, run `npx expo-doctor` for diagnostics, clear caches, and native-rebuild only for bare-workflow projects — skipped entirely for CNG (Continuous Native Generation) projects. Walks a breaking-changes checklist (removed APIs, moved imports, deprecated native modules). Reads `.workflow/meta.json` with `stack.framework="expo-rn"`; does NOT bump `phase`. Triggers on: "upgrade Expo SDK", "upgrade to Expo SDK 57", "bump expo version", "npx expo-doctor is failing", "upgrade React Native", "aggiorna Expo", "aggiorna il progetto RN", "expo install --fix". Not for: scaffolding a new app (`rn-bootstrap`), adding a screen (`rn-add-screen`), adding a backend/infra module (`rn-module-add`), or building/submitting to stores (`rn-eas-deploy`, `rn-eas-build-submit-update`).'
---

# rn-upgrade — upgrade an Expo + RN project to a newer SDK

## Contract

See `references/contracts.md` (vendored from `dev-flow`). Key facts:
- Reads `<project-root>/.workflow/meta.json#stack.framework` — must be `"expo-rn"`.
- Requires `meta.json#phase ≥ "scaffolded"` (there must be a real app to upgrade — this skill never scaffolds).
- This is a **maintenance** operation, not a pipeline step: it does **not** advance `phase`. It only appends a `history` entry recording the SDK versions before/after.
- Idempotent in spirit: re-running on an already-upgraded project is a no-op after Step 1 detects `expo` is already at the target version (still worth running `expo-doctor` to catch drift).

## When this skill applies

- Phase is `scaffolded` or later (an Expo app already exists at the project root).
- User asks to move to a newer Expo SDK / React Native version, or reports `npx expo-doctor` failures, or dependency drift after manual `npm install`.
- Orchestrator note: `dev-flow` does not route here automatically as part of the phase pipeline — this is invoked ad hoc, whenever the user wants to upgrade an already-running project.

## Knowledge dependencies (read these first)

- `rn-fundamentals/SKILL.md` — the 4 non-negotiables (Expo managed, latest SDK, TypeScript, npm) this skill is restoring/advancing.
- `rn-bootstrap/references/stack-defaults.md` — the pinned baseline versions used at scaffold time; the diff target for this upgrade.
- `rn-eas-build-submit-update/references/eas-json.md` — `runtimeVersion` policy must be re-verified after an SDK bump (a new SDK usually means a new runtime version, which affects EAS Update compatibility).
- `rn-module-add/SKILL.md` + `rn-backend/references/*` — if a wired module depends on a module being deprecated (e.g. `expo-av` used for audio/video in a wired feature), the breaking-changes step touches that code.

## Source of truth — read this before trusting any command below

Expo SDKs ship roughly every quarter and change command surface, deprecations, and config shape release to release. **This skill's workflow shape is stable; the exact command flags and package names are not.** Before executing anything marked `[VERIFY]`:

1. Check the live Expo docs for the **target** SDK: `https://docs.expo.dev/workflow/upgrading-expo-sdk-walkthrough/` and `https://docs.expo.dev/changelog/`.
2. If MCP tools are available, query **MCP Expo** (`https://mcp.expo.dev/mcp`) for the current upgrade guidance and API status — it is more current than any static doc snapshot.
3. Cross-check against the official `expo/skills` repo's `expo-upgrade` skill if installed/available — this skill is modeled on it but does not vendor its per-SDK specifics, since those go stale.

Never silently apply a `[VERIFY]` command from memory across a major SDK boundary — confirm it against one of the three sources above first.

## Workflow

### Step 1 — Preconditions + detect current state

Read `.workflow/meta.json`. Abort if `stack.framework != "expo-rn"` or `phase < "scaffolded"`.

Read `package.json` to record the current `expo` version (this is `from_sdk` for the history entry). Read `app.json`/`app.config.*` for `expo.sdkVersion` if pinned there too.

### Step 2 — Detect CNG vs bare workflow

Check for `ios/` and `android/` directories at the project root:

- **Absent → CNG (Continuous Native Generation)**: native projects are generated on demand by `expo prebuild` at build time. `expo prebuild --clean` is **not required** as part of the upgrade — the next `expo run:ios` / `eas build` regenerates them fresh from `app.json` + config plugins. Skip Step 6 native-rebuild commands entirely.
- **Present → bare workflow**: native folders are checked into the repo and must be regenerated + reinstalled manually. Step 6 applies in full.

See `references/native-rebuild.md` for the exact per-mode commands and rationale.

### Step 3 — Bump Expo and align every dependency

```bash
npx expo install expo@latest
npx expo install --fix
```

`expo install --fix` re-resolves every Expo-adjacent package (`react-native`, `react`, `expo-router`, `react-native-reanimated`, etc.) to the versions the newly-installed SDK expects — this is the step that actually fixes the dependency graph, not just the `expo` package itself.

`[VERIFY]` — on some SDKs the second command's exact flag name has changed historically (`--fix` vs interactive prompt-only); confirm against the live docs for the target SDK.

### Step 4 — Diagnose with expo-doctor

```bash
npx expo-doctor
```

Walk every flagged issue. Common categories: mismatched dependency versions, invalid `app.json` config plugin entries, native folders out of sync with config (bare only). Do not proceed to Step 5 with unresolved `expo-doctor` errors — fix them first, re-run until clean (warnings can be triaged, errors cannot).

### Step 5 — Clean caches and reinstall

```bash
rm -rf node_modules .expo
watchman watch-del-all 2>/dev/null || true
npm install
npx expo install --fix
```

Stale Metro/Watchman state is a common source of "upgrade worked but the app still crashes" reports — never skip this even if `expo-doctor` is clean.

### Step 6 — Native rebuild (bare workflow only — skip for CNG)

Only if Step 2 detected `ios/`/`android/` folders present:

```bash
npx expo prebuild --clean
cd ios && pod install --repo-update && cd ..
cd android && ./gradlew clean && cd ..
```

`--repo-update` on `pod install` matters after an SDK bump — the CocoaPods spec repo needs the latest podspecs for the new native module versions. Skipping it is the most common cause of "pod install succeeded but build fails" after an upgrade.

For CNG projects: do nothing here. If the user insists on regenerating native folders locally for debugging, that is a separate, explicit ask — not part of this upgrade flow.

Full rationale + exact per-mode commands: `references/native-rebuild.md`.

### Step 7 — Breaking-changes checklist

Walk `references/breaking-changes.md`: removed APIs, moved imports, deprecated native modules for the SDK range being crossed. The most common one to check every upgrade: **`expo-av` → `expo-audio` + `expo-video`** (the AV module was deprecated and split into two focused packages). If the project uses `expo-av` for camera-adjacent audio/video, migrate before considering the upgrade done.

After migrating any deprecated module, manually test:
- [ ] Camera capture (photo + video, if used).
- [ ] Audio playback/recording (if used).
- [ ] Video playback (if used).
- [ ] Navigation (Expo Router route transitions, deep links) — router internals sometimes shift between SDKs.

### Step 8 — Beta/preview SDK path (optional, only if explicitly requested)

If the user wants to target a not-yet-stable SDK:

```bash
npx expo install expo@next --fix
```

- Beta packages use the `@next` dist-tag or `.preview` prerelease versions (`x.y.z-preview.n`) — `[VERIFY]` the exact tag naming for the target beta against `https://docs.expo.dev/changelog/`.
- Check available runtime versions/manifests via `https://exp.host/--/api/v2/versions` when diagnosing beta-channel compatibility issues.
- Beta SDKs are inherently less stable — NEVER move a production app to `@next` without the user's explicit, informed confirmation (this is user-facing risk, not a default).

Full walkthrough (version checks, reverting, third-party compatibility caveats): `references/beta-preview.md`.

### Step 9 — Review release notes and refresh doc links

Read the target SDK's entry on `https://docs.expo.dev/changelog/` (or `expo.dev/changelog`) end to end — not just the breaking-changes section, since deprecation notices for the *next* upgrade often appear early. If the project's own docs (`.workflow/DESIGN.md`, README, code comments) link to version-pinned Expo docs URLs (e.g. `docs.expo.dev/versions/v53.0.0/...`), update them to the new SDK's version path.

### Step 10 — Verify

```bash
npx tsc --noEmit
```

Must pass. Run the app (`npx expo start`, or a dev build for bare) and manually smoke-test the flows touched in Step 7, plus core navigation.

### Step 11 — Update meta.json + commit

Update `meta.json`:
- `stack_config.expo_sdk`: set to the new SDK version (add this key if not already present).
- `phase`: **unchanged** — this is maintenance, never advance the pipeline phase for an upgrade.
- `history`: append `{ skill: "rn-upgrade", ran_at: <iso>, inputs: { from_sdk, to_sdk }, outputs: ["package.json", "app.json", ...], phase_before: <phase>, phase_after: <same phase> }`.

Commit: `chore(deps): upgrade Expo SDK <from> → <to>`.

## Common anti-patterns (NEVER do)

- ❌ Bump `expo` without immediately running `expo install --fix` — leaves the dependency graph half-upgraded.
- ❌ Skip `expo-doctor` "because the app still runs" — it catches config-plugin drift that only surfaces at build time.
- ❌ Run `expo prebuild --clean` on a CNG project as a matter of habit — unnecessary churn, and can accidentally commit generated native folders that shouldn't be tracked.
- ❌ Rebuild native (bare) without `pod install --repo-update` — stale CocoaPods specs silently break the build.
- ❌ Advance `meta.json#phase` as part of this skill — an upgrade is not scaffolding, a new screen, or a module; the phase must stay exactly where it was.
- ❌ Move a project to a beta/`@next` SDK without explicit user confirmation.
- ❌ Skip manual camera/audio/video/navigation testing after touching any deprecated native module.
- ❌ Trust a specific command flag from memory across SDK majors — check the `[VERIFY]` sources first.

## Updating meta.json (recommended pattern)

When this skill modifies state (history appended — no phase change), use the canonical script when available:

```bash
# Wherever dev-flow is installed (e.g. ~/.claude/skills/dev-flow/), invoke:
python3 .../dev-flow/scripts/update_meta.py <project-root> append-history \
    --skill 'rn-upgrade' --inputs '{"from_sdk":"<x>","to_sdk":"<y>"}' \
    --outputs '["package.json","app.json"]' --phase-after <same-phase-as-before>
```

Note there is deliberately **no `set-phase` call** in this skill's usage of the script — `phase-after` in the history entry must equal `phase-before`. **Fall back to direct JSON editing only if the script is not on PATH** (and warn the user), preserving every other field verbatim.

## Sources

- Official: https://docs.expo.dev/workflow/upgrading-expo-sdk-walkthrough/
- Official: https://docs.expo.dev/changelog/
- Official: https://docs.expo.dev/versions/latest/
- MCP Expo: https://mcp.expo.dev/mcp
- Modeled on the official `expo-upgrade` skill from the `expo/skills` repo (consult it directly for per-SDK specifics — not vendored here since it goes stale).
