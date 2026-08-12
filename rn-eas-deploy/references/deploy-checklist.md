> Sources: synthesized from rn-eas-build-submit-update + rn-publishing-payments.

# Deploy checklist — `rn-eas-deploy` runs through this

Print this to the user before deploy, asking them to confirm each. Block on missing items.

## Code quality

- [ ] `npx tsc --noEmit` passes (zero errors).
- [ ] `npm test -- --runInBand --bail` passes.
- [ ] `npx expo doctor` exits 0 (or only documented warnings).
- [ ] No `console.log` in shipped code (use `expo-dev-tools` logging, dev-only).
- [ ] No hardcoded localhost URLs or dev secrets.

## Configuration

- [ ] `app.json#expo.version` bumped (semver).
- [ ] `app.json#expo.runtimeVersion = { "policy": "appVersion" }` set.
- [ ] `app.json#expo.scheme` set to a kebab-case identifier.
- [ ] `app.json#expo.experiments.typedRoutes = true`.
- [ ] ~~`app.json#expo.newArchEnabled`~~ — nothing to check: always on since SDK 55, and the key is ignored.
- [ ] All `expo.plugins` listed: `expo-router`, `expo-notifications` (if push), `@react-native-firebase/app` (if Firebase), `expo-build-properties` (if Firebase or RevenueCat), etc.
- [ ] `ios.bundleIdentifier` + `android.package` set to your real reverse-DNS.

## Credentials

- [ ] iOS distribution certificate + provisioning profile in EAS (`eas credentials --platform ios`).
- [ ] iOS APNs key in EAS (if push notifications used).
- [ ] Android upload keystore in EAS + **backed up locally and offline** (`eas credentials --platform android` → Download).
- [ ] Google Play service account JSON at `<root>/google-play-service-account.json` (gitignored).
- [ ] `GoogleService-Info.plist` + `google-services.json` at project root (if Firebase).
- [ ] All `EXPO_PUBLIC_*` env vars defined in EAS Secrets for the `production` profile.

## Assets

- [ ] `./assets/icon.png` 1024×1024.
- [ ] `./assets/adaptive-icon.png` 1024×1024 (Android adaptive).
- [ ] `./assets/splash.png` for splash screen.
- [ ] `./store-assets/ios/screenshots/` populated — **6.9" (1320×2868) or 6.5"**, one of the two, plus **13" iPad (2064×2752)** if you ship iPad. 12.9" iPad is legacy/optional.
- [ ] `./store-assets/android/screenshots/phone/` populated.
- [ ] `./store-assets/android/feature-graphic.png` (1024×500).
- [ ] Marketing copy in `./store-assets/descriptions/<locale>.md` for each supported locale.

## Store listings (one-time per app)

- [ ] App Store Connect: app created with the correct bundle ID.
- [ ] App Store Connect: privacy policy URL set.
- [ ] App Store Connect: privacy nutrition label filled.
- [ ] App Store Connect: age rating questionnaire completed.
- [ ] App Store Connect: pricing set (free / paid tier).
- [ ] App Store Connect: any IAP / subscription products created and APPROVED.
- [ ] Play Console: app created with the correct package name.
- [ ] Play Console: privacy policy URL set.
- [ ] Play Console: Data safety form filled (must match what SDKs collect).
- [ ] Play Console: content rating questionnaire completed.
- [ ] Play Console: pricing & distribution country list set.

## Smoke-tested on `preview`

- [ ] `eas build --profile preview --platform all` produced installable artifacts.
- [ ] Installed on at least 1 iOS device + 1 Android device.
- [ ] Cold-start app, sign in, hit the core feature, sign out, sign back in — works.
- [ ] Tested on a low-end Android (Android Go-class if your target audience includes them).
- [ ] Tested offline (airplane mode) — graceful fallback.
- [ ] Tested with a real push notification (from https://expo.dev/notifications).
- [ ] Tested an IAP / subscription purchase in sandbox (if applicable).

## Monitoring (first-week safety net)

- [ ] Crash reporting enabled (Sentry / Bugsnag / etc.) in production build.
- [ ] OTA update channel `production` ready (can ship JS fixes within minutes if needed).
- [ ] Backend health dashboard accessible to the team.

## Reject heuristics (review will fail if any are TRUE)

- [ ] No screenshot with fake content / marketing illustration.
- [ ] No mention of competitors by name in description.
- [ ] No demo-account login that the reviewer can use (provide one in App Store Connect's review notes).
- [ ] No "this is a beta" disclaimer that exposes the user to broken features.
- [ ] No request for ATT permission before showing app value.
- [ ] No purchase outside IAP for digital goods (iOS).
- [ ] No missing "Restore Purchases" button on paywall (iOS, IAP).
- [ ] No Sign in with Apple gap if other 3rd party auth offered (iOS).

If any of these is TRUE → fix before submitting.

## Final check

- [ ] User has explicitly confirmed: "ship it". The skill never auto-ships.
