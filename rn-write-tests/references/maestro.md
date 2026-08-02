# Maestro — E2E flows for Expo + RN

The **how**, not just "use Maestro". Doc-grounded against `docs.maestro.dev` (CLI install, CLI commands & options, React Native platform page, command reference, selectors, nested flows, parameters, workspace config, Cloud + GitHub Actions) and `docs.expo.dev` (EAS Workflows `maestro` job). Checked 2026-08. `[VERIFY]` CLI flags against `maestro --help` for the installed build.

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

Two naming notes that trip people up. The **docs moved to `docs.maestro.dev`** while the **install script still lives on `get.maestro.mobile.dev`**. And **Maestro Studio is now a separate desktop app** (`MaestroStudio.dmg` / `.exe` / `.AppImage`), no longer in the CLI subcommand list — which is `test`, `cloud`, `record`, `start-device`, `list-devices`, `list-cloud-devices`, `login`, `logout`, `mcp`, `download-samples`, `driver-setup`, `bugreport`. `[VERIFY]`: if `maestro studio` still runs on your build, it is a legacy alias.

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

Agent-driven authoring: `maestro mcp` starts Maestro's MCP server so a coding agent can write, run, and debug flows directly `[VERIFY]`.

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

The official GitHub Action wraps the same thing: `mobile-dev-inc/action-maestro-cloud@v2.0.2` with `api-key: ${{ secrets.MAESTRO_API_KEY }}`, `project-id`, `app-file` `[VERIFY] the action tag`. Cloud runs have a ~15-minute soft limit per execution — split long journeys into parallelizable flows. Free alternative: run `maestro test --format JUNIT` on a self-hosted emulator.

## Integration in dev-flow

- Written by `rn-write-tests` into `.maestro/<flow-name>.yaml`; the skill does **not** bump `meta.json#phase`.
- One flow per user journey named after it (`sign-in`, `create-post`, `checkout`), factoring shared setup into `.maestro/common/`.
- `rn-add-screen` must land `testID`s as it generates the screen — retrofitting selectors afterwards is the expensive path.
- Wire the EAS Workflow when `rn-eas-build-submit-update` sets up build profiles; gate merges on the `smoke` tag.
- Never Detox (see `SKILL.md` anti-patterns): native build required, Expo-hostile.
