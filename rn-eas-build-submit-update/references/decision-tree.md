> Sources: https://docs.expo.dev/eas/, https://docs.expo.dev/eas-update/.

# Decision tree — Build / Submit / Update

## Q1: I changed some code. Build, Update, or nothing?

```
What did I change?
├── JS / TS only (components, hooks, lib)            → EAS Update (OTA)
├── tailwind.config.js (regenerated)                  → EAS Update (still JS at runtime)
├── Image assets (./assets/*)                         → EAS Update (assets travel in the bundle)
│
├── package.json with a new native module (any pkg
│   that requires "expo prebuild" or has iOS/Android
│   folder requirements)                              → NEW BUILD (eas build)
├── app.json config plugins                           → NEW BUILD
├── app.json plugin params, scheme, bundleIdentifier  → NEW BUILD
├── Min iOS/Android version                           → NEW BUILD
└── eas.json env vars used at build-time              → NEW BUILD
```

## Q2: Which build profile?

```
What am I about to do with this build?
├── Run locally / on my own devices, fast iteration  → development (Expo Dev Client)
├── Send to teammates / QA / stakeholders             → preview (internal distribution)
└── Submit to App Store / Play Store                  → production
```

## Q3: I have a JS-only fix. EAS Update — which channel?

```
Who needs the fix?
├── My internal team only                            → --channel preview (or --channel development)
├── My beta testers on TestFlight / Play Internal    → --channel preview
└── End users on the live store version              → --channel production
```

Workflow:
1. `eas update --branch fix-x --channel preview --message "fix: x"`.
2. Verify on a `preview` profile build (internal device).
3. `eas update --branch fix-x --channel production --message "fix: x"` to promote.

## Q4: How does runtimeVersion work?

```
app.json:
{
  "expo": {
    "runtimeVersion": { "policy": "appVersion" }   ← OTAs target builds with same app version
  }
}
```

Possible policies:
- `appVersion` (recommended): runtime = app's marketing version (e.g. `"1.2.0"`). Bump app version → next OTA only reaches new builds.
- `sdkVersion`: runtime = Expo SDK version. Useful if your JS is compatible with multiple app versions.
- A specific string: full manual control. Avoid unless you know why.

If you forget to set `runtimeVersion`, OTAs may reach builds with incompatible native code → silent crashes. ALWAYS set it.

## Q5: Submit — what do I need first?

```
Have you ever submitted this app to the store?
├── NO (first submission)
│   1. Create the app listing in App Store Connect / Play Console (manual one-time).
│   2. Fill metadata (rn-publishing-payments covers this).
│   3. Run eas submit --profile production --platform ios (and android).
│
└── YES (update of existing app)
    1. Bump app version in app.json.
    2. eas build --profile production --platform all.
    3. eas submit --profile production --platform all (auto picks the latest build).
```

## Q6: Build failed. What now?

```
Look at the EAS build logs (linked in the CLI output).

Common failures:
├── "Missing entitlement"      → check eas credentials for that profile
├── "Version code conflict"    → autoIncrement: true OR bump versionCode manually
├── "Module not compatible"    → a native module needs a newer RN; check package version
├── "Pod install failed"       → npx expo install <package> (re-resolves correct version)
├── "Out of memory"            → split your build (rare in 2026 with modern EAS runners)
└── "Code signing error"       → eas credentials → re-link or generate
```

## Q7: How often to ship OTA updates?

```
Updates are great BUT also risky (no review, instant push to all users).

Cadence guidance:
├── Critical bug fix              → push immediately (after preview smoke)
├── Feature flag flip             → OK any time
├── Small UI tweak                → batch with the next planned update
├── Anything that changes UX     → ship through normal review cycle (build + submit)
```

Don't ship "silent" OTAs that change visible behavior — users get confused. Use feature flags + a server-controlled rollout.
