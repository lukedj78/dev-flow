# Maestro — E2E flows for Expo + RN

The **how**, not just "use Maestro". Doc-grounded against `docs.maestro.dev` (CLI install, CLI commands & options, React Native platform page, command reference, selectors, nested flows, parameters, workspace config, Cloud + GitHub Actions) and `docs.expo.dev` (EAS Workflows `maestro` job). Re-checked **2026-08-26**. ⚠️ **The docs moved**: `maestro.mobile.dev` now redirects to
**`docs.maestro.dev`**, and the old deep paths went with it — `/cli/commands` →
`/reference/commands-available`, `/getting-started/installing-maestro` → `/get-started/quickstart`.

`[VERIFY]` CLI flags against `maestro --help` for the installed build, and note the cadence: the CLI
ships roughly monthly (`cli-2.9.0` landed **on 2026-08-26**, `2.8.0` on 07-31, `2.7.0` on 07-20), so a
flag list here is a snapshot, never a contract.

**Scope**: this file is the E2E complement to `references/rntl-patterns.md`. RNTL renders components in a Node/Jest environment; Maestro drives the **real binary on a real device/simulator** through the accessibility tree, with zero instrumentation and no npm package inside the app. One user journey per flow. Component rendering, hooks, and query/mutation logic stay in Jest + RNTL — do not re-test them here.

## Install (host machine, not the app)

Prerequisite: **Java 17+**, with `JAVA_HOME` pointing at it (`java -version`).

```bash
# macOS / Linux
curl -fsSL "https://get.maestro.mobile.dev" | bash

# macOS via Homebrew
brew tap mobile-dev-inc/tap
brew trust --formula mobile-dev-inc/tap/maestro
brew install mobile-dev-inc/tap/maestro

maestro --help        # verify; `maestro -v` prints the version
```

Windows: download `maestro.zip` from the GitHub releases page, extract, add `bin` to `PATH`. macOS also needs Xcode + Command Line Tools for the iOS driver.

Two naming notes that trip people up. The **docs moved to `docs.maestro.dev`** while the **install script still lives on `get.maestro.mobile.dev`**. And **Maestro Studio is now a separate desktop app** (`MaestroStudio.dmg` / `.exe` / `.AppImage`), no longer in the CLI subcommand list — which is `test`, `cloud`, `record`, `start-device`, `list-devices`, `list-cloud-devices`, `login`, `logout`, `mcp`, `download-samples`, `driver-setup`, `bugreport`. **Confirmed**: `docs.maestro.dev/maestro-studio` opens with *"Maestro Studio is the desktop app for…"* and has its own docs section, separate from the CLI. If `maestro studio` still runs on your build, treat it as a legacy alias.

## Project layout

```
.maestro/
├── config.yaml            # optional; workspace-level settings
├── common/
│   └── login.yaml         # reusable subflow
├── sign-in.yaml
├── create-post.yaml
└── checkout.yaml
```

`config.yaml` is optional and only needed once the suite grows: a `flows:` block of globs (`*` = folder contents, `**` = recurse) plus `platform:` tweaks such as `ios.snapshotKeyHonorModalViews`. Run a non-default one with `maestro test --config .maestro/ci-config.yaml .maestro/`.

## Flow syntax

A flow is a YAML file: a header (`appId`, optional `env`, `tags`), `---`, then a list of commands.

```yaml
# .maestro/sign-in.yaml
appId: com.yourcompany.yourapp     # app.json → expo.ios.bundleIdentifier / expo.android.package
env:
  EMAIL: "user@example.com"        # inline constants
tags:
  - smoke
---
- launchApp:
    clearState: true               # fresh install state
    clearKeychain: true            # iOS only — wipes SecureStore tokens too
- assertVisible: "Sign in"
- tapOn:
    id: "email-input"              # matches testID="email-input"
- inputText: ${EMAIL}
- tapOn:
    id: "password-input"
- inputText: ${PASSWORD}           # injected with -e PASSWORD=...
- tapOn: "Sign in"                 # plain text = text selector
- waitForAnimationToEnd:
    timeout: 5000                  # default 15000; succeeds even on timeout
- assertVisible: "Welcome back"
- assertNotVisible: "Sign in"
```

Commands used most in RN apps: `launchApp` (`appId`, `clearState`, `clearKeychain`, `stopApp: false` to foreground without restarting, `permissions`, `arguments`), `tapOn`, `doubleTapOn`, `longPressOn`, `inputText`, `eraseText`, `hideKeyboard`, `assertVisible` / `assertNotVisible` / `assertTrue`, `scroll`, `scrollUntilVisible`, `swipe`, `back`, `pressKey`, `openLink`, `repeat`, `retry`, `takeScreenshot`, `addMedia`, `setLocation`, `setAirplaneMode`, `waitForAnimationToEnd`, `extendedWaitUntil`.

Reaching a row in a long FlashList: `scrollUntilVisible` with `element: { id: "post-42" }` and `direction: DOWN`, then `tapOn` the same id.

### Reuse: `runFlow`

```yaml
- runFlow: common/login.yaml            # inline the subflow's commands

- runFlow:                              # ...with arguments
    file: common/login.yaml
    env:
      USERNAME: "admin@example.com"
      PASSWORD: ${ADMIN_PASSWORD}
```

Inside the subflow, read them as `${USERNAME}`. Variable names are case-sensitive, and CLI params arrive as **strings** (`parseInt(${COUNT})` if you need a number).

### Parameters and secrets

```bash
maestro test -e EMAIL=user@example.com -e PASSWORD="$TEST_PASSWORD" .maestro/sign-in.yaml
```

Shell variables prefixed `MAESTRO_` are picked up automatically by the CLI (not by Studio). Never commit credentials into a flow file — pass them with `-e`.

## Two-user flows (shared state)

A single-user journey cannot express the bug class that costs the most in production: **user A takes
something, user B must see it taken.** A seat on a flight, a slot in a calendar, an invite code, the
last unit in stock. It is exactly the test that surfaced a cross-user RLS bug in the flight-booking
tutorial this section was written after — the seat map was fed by a query the second user was not
allowed to read, so every seat looked free. Jest + RNTL cannot see it (one client, mocked backend);
only a real binary against the real backend can.

Layout — the shared steps are subflows, the scenario is one file that reads top to bottom:

```
.maestro/
├── common/
│   ├── sign-in-as.yaml        # env: EMAIL, PASSWORD — fresh install state, then sign in
│   ├── sign-out.yaml          # profile tab → sign out → asserts the auth screen is back
│   └── open-seat-map.yaml     # env: ORIGIN, DESTINATION, DATE — search → first result → seats
└── two-users-seat-lock.yaml   # the scenario
```

```yaml
# .maestro/common/sign-in-as.yaml
appId: ${APP_ID}
---
- launchApp:
    clearState: true            # a "just installed" app: no cached session, no query cache
    clearKeychain: true         # iOS: drop anything left in SecureStore too
- tapOn:
    id: "email"
- inputText: ${EMAIL}
- tapOn:
    id: "password"
- inputText: ${PASSWORD}
- tapOn:
    id: "sign-in"
- assertVisible:
    id: "tab-home"              # signed in = the tab bar is there
```

```yaml
# .maestro/common/sign-out.yaml
appId: ${APP_ID}
---
- tapOn:
    id: "tab-profile"
- tapOn:
    id: "sign-out"
- assertVisible:
    id: "sign-in"               # back on the auth screen
- assertNotVisible:
    id: "tab-home"
```

```yaml
# .maestro/two-users-seat-lock.yaml
appId: ${APP_ID}
tags:
  - multi-user
env:
  ORIGIN: "Lagos"
  DESTINATION: "London"
---
# --- user A books the seat ---------------------------------------------------
- runFlow:
    file: common/sign-in-as.yaml
    env:
      EMAIL: ${USER_A_EMAIL}
      PASSWORD: ${USER_A_PASSWORD}
- runFlow:
    file: common/open-seat-map.yaml
    env:
      DATE: ${DATE}
- tapOn:
    id: "seat-${SEAT}"
- tapOn:
    id: "pay-now"
- tapOn:
    id: "pay-with-card"
- assertVisible:
    id: "view-booking"          # payment succeeded
- runFlow: common/sign-out.yaml

# --- user B must find it taken -------------------------------------------------
- runFlow:
    file: common/sign-in-as.yaml
    env:
      EMAIL: ${USER_B_EMAIL}
      PASSWORD: ${USER_B_PASSWORD}
- runFlow:
    file: common/open-seat-map.yaml
    env:
      DATE: ${DATE}
- assertVisible:
    id: "seat-${SEAT}"
    enabled: false              # the seat exists and is NOT tappable for B
```

```bash
maestro test \
  -e APP_ID=com.example.app \
  -e USER_A_EMAIL=a@test.example -e USER_A_PASSWORD="$TEST_PW_A" \
  -e USER_B_EMAIL=b@test.example -e USER_B_PASSWORD="$TEST_PW_B" \
  -e DATE=2026-12-05 -e SEAT=11A \
  .maestro/two-users-seat-lock.yaml
```

Rules that make the flow trustworthy:

- **`clearState: true` between users, always.** Without it user B inherits A's persisted session or
  A's TanStack Query cache and the assertion passes for the wrong reason. This is the E2E mirror of
  `rn-backend` rule 5 (sign-out clears token, store and query cache) — and a flow that only passes
  *with* `clearState` is telling you sign-out leaks state.
- **Assert on `testID` + state, not on copy.** `id: "seat-11A"` with `enabled: false` survives a copy
  edit and the second locale; `assertVisible: "Booked"` does not. Map booked/locked to
  `accessibilityState={{ disabled: true }}` (Maestro's `enabled` reads it) — `rn-add-screen` lands
  the `testID`s when it generates the screen.
- **One unique resource per run.** Pass `SEAT` (or the slot / code) with `-e` and pick a value no
  previous run has taken; on CI, reset the test dataset before the suite (a seed script, a scratch
  Supabase branch, or a nightly truncate). A flow that hardcodes `11A` passes once.
- **Two real accounts, created out of band**, never in the flow — sign-up flows belong to their own
  file. Credentials arrive with `-e` or `MAESTRO_`-prefixed shell variables; nothing is committed.
- **Backend, not mock.** The point is the authorization boundary between two identities: RLS policies,
  `security definer` functions, ownership checks. Run it against a real (test) project, on a dev or
  release build — not Expo Go (see above).

Name the variant after the resource: `two-users-seat-lock`, `two-users-slot-conflict`,
`two-users-invite-once`. Tag them `multi-user` and run them in the nightly job, not on every PR — they
are slow and they need the seeded backend.

## testID conventions in RN (stable selectors)

Maestro maps React Native's `testID` to its `id` selector on both platforms. Text selectors are the easy path and the brittle one — they break on copy edits and on the second locale (and this repo ships i18n from day one).

```tsx
<TextInput testID="email-input" placeholder="Email" />
<Pressable testID="submit-button" onPress={onSubmit}><Text>Sign in</Text></Pressable>
<PostCard testID={`post-${post.id}`} />   // stable, data-derived ids for list rows
```

House rules:
- `testID` on every interactive element a flow touches: inputs, buttons, tabs, list rows.
- Kebab-case, `<domain>-<element>`; list items suffixed with the entity id.
- Assert on `id` for structure, on visible text only when the copy *is* the thing under test.
- Selectors also support `index`, `point`, relational forms (`below`, `containsChild`, `childOf`) and state (`enabled`, `checked`, `focused`, `selected`) — reach for those before writing coordinate taps.
- iOS only: if a nested element won't tap, RN swallowed the touch — set `accessible={false}` on the outer container and `accessible` on the inner element.

## Running locally

```bash
maestro start-device --platform ios        # or launch the simulator/emulator yourself
maestro list-devices

maestro test .maestro/sign-in.yaml         # one flow
maestro test .maestro/                     # whole suite
maestro test --device <udid> .maestro/     # pick a device
maestro test -c .maestro/sign-in.yaml      # continuous mode: re-runs on file change
maestro test --include-tags smoke .maestro/
maestro test --format JUNIT --output report.xml .maestro/
maestro record .maestro/sign-in.yaml       # MP4 of the run
```

Agent-driven authoring: **confirmed** — `docs.maestro.dev/get-started/maestro-mcp` registers it as a *local* MCP server with `Command: maestro mcp`, so a coding agent can write, run and debug flows directly.

## ⚠️ Expo Go cannot be launched by `appId` — use a dev build or a deep link

Under Expo Go your JS runs **inside the Expo container**, so `launchApp` with your own `appId` targets an app that isn't installed and the flow fails at line one. The documented workaround is to open the dev URL instead:

```yaml
# Expo Go only
- openLink: exp://127.0.0.1:19000
```

That works for a smoke check but is not what you should be testing: Expo Go carries Expo's own native modules, not yours. **Test a development build or an EAS build** — a real binary with your `appId`, where `launchApp`, `clearState`, `clearKeychain`, permissions, deep links, and push all behave as they will in production.

- **Dev build** (`npx expo run:ios` / `run:android`, or an EAS `development` profile): debuggable, dev menu present, Metro attached. Use while writing flows.
- **Release build** (EAS `preview` / `production`, or the `e2e-test` profile below): what CI runs. Minified, no dev overlays, real timing — flows that only pass against a dev build are hiding a race. Keep `testID`s in release builds; do not strip them.

## CI

**EAS Workflows** — the native path for this stack: build, then run flows against the build artifact.

```json
// eas.json
{ "build": { "e2e-test": {
  "withoutCredentials": true,
  "ios": { "simulator": true },
  "android": { "buildType": "apk" }
} } }
```

```yaml
# .eas/workflows/e2e-test-android.yml
name: e2e-test-android
on:
  pull_request:
    branches: ['*']
jobs:
  build_android_for_e2e:
    type: build
    params:
      platform: android
      profile: e2e-test
  maestro_test:
    needs: [build_android_for_e2e]
    type: maestro
    params:
      build_id: ${{ needs.build_android_for_e2e.outputs.build_id }}
      flow_path: ['.maestro/sign-in.yaml', '.maestro/create-post.yaml']
```

**Maestro Cloud** (paid plan) — device farm + parallelism, drivable from any CI:

```bash
maestro cloud --app-file build/app-release.apk --flows .maestro/ \
  --device-os android-34 --format JUNIT -e PASSWORD="$TEST_PASSWORD"
```

The official GitHub Action wraps the same thing — ⚠️ **the pinned tag here was a major behind**:
`v2.0.2` is from 2026-02-23, and the current release is **`v3.0.1`** (2026-05-20).

```yaml
- uses: mobile-dev-inc/action-maestro-cloud@v3.0.1
  with:
    api-key: ${{ secrets.MAESTRO_API_KEY }}
    project-id: <id>
    app-file: <path>
    maestro-cli-version: 2.9.0     # see below
```

`api-key` / `project-id` / `app-file` all still exist at v3.0.1 (read off its `action.yml`), so the
upgrade is a tag bump. **But v3 changed what runs underneath** — its release note is
*"Migrate to Maestro CLI instead of separate validation code and curl requests to do cloud upload"* —
which is why the new **`maestro-cli-version`** input matters: *"Pin a specific Maestro CLI version
(defaults to latest)"*. Left unpinned, your CI now silently tracks whatever the Maestro CLI ships
next, and that ships monthly. Pin it, or accept a moving dependency you never declared.

Other inputs worth knowing at v3.0.1: `include-tags` / `exclude-tags`, `env` (key=value into flows),
`async`, `device-os` / `device-model` / `device-locale` (the docs mark `android-api-level` and
`ios-version` as superseded by `device-os`), and `timeout` in minutes. Cloud runs have a ~15-minute soft limit per execution — split long journeys into parallelizable flows. Free alternative: run `maestro test --format JUNIT` on a self-hosted emulator.

## Integration in dev-flow

- Written by `rn-write-tests` into `.maestro/<flow-name>.yaml`; the skill does **not** bump `meta.json#phase`.
- One flow per user journey named after it (`sign-in`, `create-post`, `checkout`), factoring shared setup into `.maestro/common/`.
- `rn-add-screen` must land `testID`s as it generates the screen — retrofitting selectors afterwards is the expensive path.
- Wire the EAS Workflow when `rn-eas-build-submit-update` sets up build profiles; gate merges on the `smoke` tag.
- Never Detox (see `SKILL.md` anti-patterns): native build required, Expo-hostile.
