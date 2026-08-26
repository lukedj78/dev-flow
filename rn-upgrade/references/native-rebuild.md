> Snapshot date: 2026-07-23 (link targets re-checked 2026-08-26). Command flags can change between Expo SDK majors — re-verify `[VERIFY]`-tagged items against `https://docs.expo.dev/workflow/upgrading-expo-sdk-walkthrough/` or MCP Expo (`https://mcp.expo.dev/mcp`) before running on an unfamiliar SDK.

# Native rebuild: CNG vs bare workflow

Whether an upgrade needs a native rebuild step depends entirely on which workflow the project uses. Get this wrong and you either waste time regenerating folders that don't need it, or ship a build with stale native code.

## Detecting which one you have

```bash
test -d ios && test -d android && echo "bare (native folders present)" || echo "CNG (no native folders — generated on demand)"
```

- **CNG (Continuous Native Generation)** — the Expo default and recommended mode for all new projects (see `rn-fundamentals/SKILL.md`). No `ios/`/`android/` in the repo (or they're gitignored). Native projects are generated fresh from `app.json` + config plugins whenever `expo prebuild`, `expo run:ios/android`, or an EAS Build runs.
- **Bare workflow** — `ios/`/`android/` are checked into the repo and hand-maintained (or were generated once and diverged from pure config-plugin control, e.g. custom native code added directly).

## CNG projects: what to do

**Nothing, by default.** Do not run `expo prebuild --clean` as part of an SDK upgrade — it's wasted work, since:

- Local dev (`expo start`) doesn't need native folders at all for JS-only changes.
- `expo run:ios` / `expo run:android` regenerate native folders on the fly from the current `app.json`, already reflecting the new SDK's templates.
- EAS Build always runs prebuild server-side from a clean state.

If the user wants to inspect the generated native project locally for debugging (not part of a routine upgrade), that's a separate explicit request:

```bash
npx expo prebuild --clean   # only on explicit ask, not as a default upgrade step
```

Running this unprompted risks accidentally committing generated `ios/`/`android/` folders into a project that intentionally keeps them out of git.

## Bare workflow projects: full rebuild required

```bash
npx expo prebuild --clean
cd ios && pod install --repo-update
cd ../android && ./gradlew clean
```

Why each step matters:

- `expo prebuild --clean` regenerates `ios/`/`android/` from `app.json` + installed config plugins, wiping any hand-edits that aren't captured by a plugin. **Warn the user before running this** if the project has manual native edits not expressed as config plugins — those edits will be lost and must be re-applied or converted to a plugin.
- `pod install --repo-update` (not plain `pod install`) refreshes the local CocoaPods spec repo cache. After an SDK bump, new native module versions often need podspecs that aren't in a stale local cache — omitting `--repo-update` is the most common cause of "pod install succeeded, build still fails."
- `./gradlew clean` clears cached Gradle build outputs referencing the old native module versions. Skipping it can produce confusing stale-artifact build errors on Android.

## After either path

Regardless of CNG or bare, a fresh native build (`eas build --profile development` or `expo run:ios/android`) is required after any SDK bump before trusting the app — JS bundle changes are covered by `expo start`, but native module version bumps are not visible until a real native build runs.
