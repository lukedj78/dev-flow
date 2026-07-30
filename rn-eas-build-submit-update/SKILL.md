---
name: rn-eas-build-submit-update
description: 'Use for cloud builds and OTA updates of an Expo + RN app via EAS: configuring eas.json profiles (development/preview/production), managing credentials (APNs key, Android keystore) without committing them to git, submitting builds to App Store Connect / Google Play via EAS Submit, shipping JS-only fixes via EAS Update with channels/branches, EAS Workflows for CI. Triggers on: "set up EAS Build", "OTA update", "EAS Submit", "configure eas.json", "deploy to Play Store / TestFlight". Not for: store metadata/screenshots/IAP (rn-publishing-payments), scaffolding (rn-bootstrap), or the end-to-end deploy orchestration (rn-eas-deploy).'
---

# rn-eas-build-submit-update — guardrail for EAS Build / Submit / Update / Workflows

## The 5 rules (non-negotiable)

1. **3 profiles in `eas.json`**: `development` (dev client, internal), `preview` (TestFlight / Play Internal — test on real devices), `production` (the store). NEVER ship from a profile not pre-tested in preview.
2. **Credentials server-side via `eas credentials`**. NEVER commit `.p12`, `.p8`, `*.keystore`, `*.jks`, or `google-services.json` for production accounts. EAS holds them; local Apple/Google CLI never touches them.
3. **OTA only for JS-only changes**. If the diff touches `app.json` config plugins, native modules, or anything that would change `prebuild` output → it's a new build, not an Update.
4. **Channels separate environments**. `preview` channel for QA, `production` channel for end users. Ship updates to `preview` first, promote to `production` only after smoke-test.
5. **`expo-updates` config in `app.json`** is the source of truth for runtime version (`runtimeVersion: { policy: "appVersion" }` or `"sdkVersion"`). Mismatched runtime versions = OTAs ignored.

## Quick decision tree

- "Build, Submit, or Update — which do I need now?" → `references/decision-tree.md`
- "How do I write the eas.json profiles?" → `references/eas-json.md`
- "How do credentials work — where does the cert live?" → `references/credentials.md`
- "How do I set up EAS Workflows for CI?" → `references/workflows.md`
- "Did the build/OTA I just shipped actually land OK — do I need a hotfix or rollback?" → `rn-eas-deploy/references/observability.md` (EAS Observe for build performance, EAS Update Insights for OTA rollout health)

## Common anti-patterns (NEVER do)

- ❌ Committing certificates / keystores to git.
- ❌ `eas build --profile production` without ever having built `--profile preview` for that commit.
- ❌ `eas update --channel production` without `--branch <name>` and without testing on `preview` channel first.
- ❌ Updating `app.json` config plugins and shipping via OTA — fails silently or crashes on user devices.
- ❌ Bumping `version` in `app.json` without also bumping `ios.buildNumber` / `android.versionCode` — store reject.
- ❌ `expo-updates` with default `runtimeVersion` (none) — OTA gets applied to incompatible native builds → crash.
- ❌ Promoting an update to the `production` channel and never checking `eas channel:insights` / `eas update:insights` afterwards — see `rn-eas-deploy/references/observability.md`.

## Sources

- Course: codewithbeto.dev/rnCourse — EAS Build/Submit/Update/Workflows modules (paid).
- Official: https://docs.expo.dev/eas/
- Official: https://docs.expo.dev/eas-update/introduction/
- Official: https://docs.expo.dev/eas/workflows/get-started/
- Observability (post-Update health): `rn-eas-deploy/references/observability.md`, https://github.com/expo/skills (`eas-update-insights`)
