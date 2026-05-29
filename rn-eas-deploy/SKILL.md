---
name: rn-eas-deploy
description: 'Use to deploy an Expo + RN app end-to-end: initialize eas.json with 3 profiles (development/preview/production), set up credentials (APNs key, Android keystore) via `eas credentials`, build for preview to smoke-test, build production, submit to App Store Connect + Play Console via EAS Submit, configure EAS Update channels (preview + production), and verify the post-submission checklist from rn-publishing-payments. Reads .workflow/meta.json with stack.framework="expo-rn" and phase="feature_complete". Sets phase to "deployed" on success. Triggers on: "deploy to production", "ship to App Store / Play Store", "release the app". Not for: granular EAS Build/Submit/Update operations (rn-eas-build-submit-update), store metadata work (rn-publishing-payments).'
---

# rn-eas-deploy — end-to-end EAS deploy orchestration

## Contract

See `references/contracts.md`. Key facts:
- Reads `<project-root>/.workflow/meta.json#stack.framework` — must be `"expo-rn"`.
- Requires `meta.json#phase ≥ "feature_complete"`.
- Wires `eas.json` + credentials + first production build + submit.
- Sets `meta.json#stack.deploy = "eas"` and `phase = "deployed"` on success.
- Idempotent: re-running detects existing config and skips already-done steps.

## When this skill applies

- Phase is `feature_complete` (or later, for subsequent releases).
- User says: "deploy", "ship to stores", "release".
- Orchestrator routes here from `dev-flow`.

## Knowledge dependencies (read these first)

- `rn-eas-build-submit-update/SKILL.md` — the underlying knowledge (eas.json, credentials, channels, runtimeVersion).
- `rn-eas-build-submit-update/references/eas-json.md` — canonical 3-profile shape.
- `rn-eas-build-submit-update/references/credentials.md` — how `eas credentials` works.
- `rn-publishing-payments/references/review-guidelines.md` — pre-submission checklist.
- `rn-publishing-payments/references/store-assets.md` — what assets must be ready.

## Workflow

### Step 1 — Verify preconditions

Read `.workflow/meta.json`. Abort if:
- `stack.framework != "expo-rn"`.
- `phase < "feature_complete"`.
- App version not bumped since last deploy (read `app.json#expo.version` vs `meta.json#last_deployed_version`).

### Step 2 — Pre-submission checklist

Walk through `rn-publishing-payments/references/review-guidelines.md` "Pre-submission checklist". For each item, verify:

- [ ] App icon present + correct size.
- [ ] Screenshots ready in `store-assets/`.
- [ ] Privacy policy URL hosted.
- [ ] Privacy nutrition label / Data safety form filled.
- [ ] Sign in with Apple present (if other 3rd party auth on iOS).
- [ ] Restore Purchases button on paywall (if IAP).
- [ ] `npx expo doctor` passes.
- [ ] `npx tsc --noEmit` passes.
- [ ] `npm test` passes.
- [ ] Smoke-tested on at least one real device per platform via `preview` profile.

Report any unchecked items + abort. Do not proceed with incomplete checklist.

### Step 3 — Initialize eas.json (idempotent)

If `eas.json` exists at project root: read and validate it has 3 profiles. If missing/malformed:

- Run `eas init` to link the project to the EAS account.
- Run `eas build:configure` to generate `eas.json`.
- Then patch the generated config to match the canonical shape in `rn-eas-build-submit-update/references/eas-json.md`.

Commit: `chore(eas): initialize eas.json with 3 profiles`.

### Step 4 — Credentials check (interactive)

Run `eas credentials` for each platform to confirm:

- iOS: distribution certificate, provisioning profile, APNs key (if push enabled).
- Android: upload keystore, Play service account JSON (`google-play-service-account.json` at project root, gitignored).

If anything is missing, walk the user through generation (Apple ID login → EAS handles certs; Android → EAS generates keystore + user downloads backup).

NEVER auto-generate credentials without explicit user confirmation. Print which credential is needed + the exact `eas credentials` command to run.

### Step 5 — Preview build (smoke test)

Run `eas build --profile preview --platform all --non-interactive`. Wait for completion (5-15 minutes typical).

When done:
- Print install links.
- Pause and ask user: "Install on a real device and confirm the app works end-to-end. Reply 'OK' when smoke-tested."

### Step 6 — Bump app version (if needed)

Compare `app.json#expo.version` with `meta.json#last_deployed_version`:
- If same → require explicit user bump before proceeding.
- If user wants to ship a patch → bump patch (e.g. `1.2.3` → `1.2.4`).
- `ios.buildNumber` / `android.versionCode` are handled by `autoIncrement: true` in the production profile.

### Step 7 — Production build

Run `eas build --profile production --platform all --non-interactive`. Wait.

### Step 8 — Submit to stores

Run `eas submit --profile production --platform all --non-interactive`.

For first submission of a new app:
- App MUST exist in App Store Connect / Play Console with the correct bundle ID / package name (manual setup, can't be automated).
- Print clear instructions if either is missing.

For subsequent submissions:
- EAS uses the latest production build.
- User must release the build manually in the store dashboard (or configure auto-release in the Play Console).

### Step 9 — Configure EAS Update channels (first deploy only)

If this is the FIRST deploy:
- Verify `app.json#expo.updates.url` is set (EAS configures this automatically on `eas update:configure`).
- Verify `app.json#expo.runtimeVersion = { policy: "appVersion" }`.
- Smoke-test the update mechanism by publishing a no-op update to the `preview` channel: `eas update --branch initial --channel preview --message "init"`.

### Step 10 — Update meta.json + commit

```json
{
  "stack": { "deploy": "eas" },
  "stack_config": {
    "eas_profiles": ["development", "preview", "production"],
    "last_deployed_version": "1.2.3"
  },
  "phase": "deployed",
  "history": [
    ...,
    { "skill": "rn-eas-deploy", "ran_at": "<iso>", "version": "1.2.3", "platforms": ["ios", "android"] }
  ]
}
```

Commit: `release: deploy v<version> to App Store + Play Store via EAS`.

### Step 11 — Print next-steps summary

- Where to view build status: https://expo.dev/accounts/.../projects/.../builds
- Where to monitor crash reports: Sentry / Bugsnag dashboard (if configured).
- Reminder: review submission can take 24-48h (Apple) or hours (Google).
- For JS-only fixes post-release: `eas update --branch <name> --channel production` — but ALWAYS smoke-test on the `preview` channel first.

## Common anti-patterns (NEVER do)

- ❌ Skip the pre-submission checklist to "save time" — review rejection costs more.
- ❌ Skip the preview smoke test on a real device — first user crash on production is the most expensive bug.
- ❌ Auto-bump app version without user confirmation.
- ❌ `eas submit` before the App Store Connect / Play Console listing exists.
- ❌ Generate credentials without backing up the Android keystore — irreversible if lost.
- ❌ Set `phase = "deployed"` before the store actually accepts the binary.

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

- Course: codewithbeto.dev/rnCourse — EAS modules (paid).
- Knowledge skills consumed (see above).
- Official: https://docs.expo.dev/eas/, https://docs.expo.dev/submit/introduction/
