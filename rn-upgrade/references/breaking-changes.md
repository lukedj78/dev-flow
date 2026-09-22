> Snapshot date: **2026-08-26** for the rows below, **2026-09-22** for §SDK 58 (rows re-checked against `expo@57.0.16`'s `bundledNativeModules.json` and the packages' own `exports`). This table is illustrative, not exhaustive — the per-SDK breaking-changes list is only correct on `https://expo.dev/changelog` for the exact versions being crossed. Re-verify `[VERIFY]` rows before relying on them.

# Breaking-changes checklist

Walk this before declaring an upgrade done. For every row that applies to the project, confirm the migration happened and the corresponding manual test passed.

## Deprecated / split / renamed modules

| Old | New | Notes |
|---|---|---|
| `expo-av` | `expo-audio` + `expo-video` | `expo-av` was deprecated in SDK 53 and **removed in SDK 54** — confirmed: it is absent from `expo@57.0.16`'s `bundledNativeModules.json` (123 packages), where `expo-video` and `expo-audio` both appear, replaced by two focused packages: `expo-audio` for playback/recording, `expo-video` for video playback. Audio and video code must be split when migrating — they're no longer one API surface. |
| `expo-permissions` | per-module permission APIs | Long deprecated; each module (camera, location, notifications) now exposes its own `usePermissions`/`requestPermissionsAsync`. If still present in a project, this is a stale leftover, not a recent-SDK concern. |
| `expo-file-system/next` (was the new API) → **plain `expo-file-system`** · old code → **`expo-file-system/legacy`** | | ⚠️ **This row used to point the wrong way, and the cutover is done.** At `expo-file-system@57.0.5` the package exports exactly two entry points: `.` — which is now **the new API** — and `./legacy`. **There is no `/next` subpath any more**, so an import from `expo-file-system/next` fails outright, while an untouched legacy import from `expo-file-system` keeps resolving and silently gets the *new* API. Crossing into SDK 57: move old call sites to `/legacy` to buy time, or migrate them; leaving them bare is the one option that looks fine and isn't. |
| Old Expo Router APIs (e.g. pre-file-based conventions) | current Expo Router conventions | If the project predates Expo Router stabilizing, check `rn-expo-router/SKILL.md` for the current file-based routing shape. |

## Import-path and API shape changes to check every upgrade

- Search the codebase for imports from packages listed as removed/deprecated in the target SDK's changelog (`grep -rn "from 'expo-av'"` etc.) before assuming "it still builds so it's fine" — deprecated APIs often still work for one or two SDKs before hard removal.
- Check `app.json`/`app.config.*` config plugin entries against the plugin's current expected shape — plugin config schemas do change between majors.
- Check any native module with a config plugin (push notifications, Firebase, in-app purchases) for updated plugin option names.

## Manual test checklist (run after any deprecated-module migration)

- [ ] Camera: photo capture, video capture (if the app uses either).
- [ ] Audio: playback, recording (if migrated off `expo-av`).
- [ ] Video: playback, controls, fullscreen (if migrated off `expo-av`).
- [ ] Navigation: route transitions, deep links, back-gesture behavior (Expo Router internals can shift between SDKs even without an explicit changelog entry).
- [ ] Push notifications: permission prompt, foreground/background delivery (if config-plugin options changed).
- [ ] Any third-party native module the project depends on that has its own SDK-compatibility matrix (check that library's own changelog too — an Expo SDK bump can silently break a dependency that hasn't caught up).

## SDK 58 (beta) — the crossing to plan for

> Read off the official changelog <https://expo.dev/changelog/sdk-58-beta> (published 2026-09-15, read
> 2026-09-22). **SDK 58 is in beta**: `expo@latest` is still `57.0.24`, stable follows React Native
> 0.88 (an RC today). Full release notes only appear with the stable release, so re-read the page then.
> This section exists so the work is known in advance — every item below survives into the stable upgrade.

**iOS 27 — the app is resizable, and that is not optional.** iOS 27 requires the UIKit scene-based life
cycle and makes iPhone apps resizable; apps built with the iOS 27 SDK get both automatically.

- `npx expo prebuild` now generates `SceneDelegate.swift` and a `UIApplicationSceneManifest` entry, and
  the `UIWindow` is created by the scene delegate. **Bare projects and hand-edited `AppDelegate.swift`
  need the migration** (Expo's scene life-cycle migration guide).
- **`ScreenOrientation.lockAsync` may have no effect while the app is resizable**, and `requireFullScreen`
  no longer opts an app out of resizing. A portrait lock is no longer a layout guarantee: any screen can
  arrive wide, and on a foldable it can change while open. Check the screens that assumed one aspect
  ratio — media players, camera overlays, signature pads, anything absolutely positioned.
- Expo packages no longer read geometry from `UIScreen.main`; `expo-modules-core` has scene-aware helpers.
  Project code that measures the screen instead of the window inherits the same bug.

**React Native 0.87/0.88 — the Strict TypeScript API is the default.** Deep imports from
`react-native/Libraries/*` are type errors, and ref types changed shape (`ViewInstance`,
`TextInputInstance`). The escape hatch is `"customConditions": ["react-native", "react-native-legacy-deep-imports"]`
in `tsconfig.json`, **removed after 0.88** — so it buys one cycle, not a decision. RN also removed
`InteractionManager` (use `requestIdleCallback`), the `Touchable` root export, the `NativeMethods` types,
`Modal`'s `animated` prop and `StatusBar`'s `backgroundColor` / `translucent` /
`networkActivityIndicatorVisible`; `ImageBackground` is deprecated in favour of a `View` with an
absolutely positioned `Image`.

**Everything else worth a grep before upgrading:**

| Package | Change |
|---|---|
| `expo-router` | navigation core reworked: deterministic route keys, dispatch deferred until after commit, and **most of the forked react-navigation API surface removed**. `@expo/ui` and `expo-symbols` become optional peer dependencies. Data loaders, SSR and middleware are now stable. |
| `expo-file-system` | `File.write()` is **async** and returns a promise; `File.writeSync()` keeps the old behaviour. |
| `expo-sqlite` | libSQL support removed (`syncLibSQL()`, `libSQLOptions` gone). |
| `expo-notifications` | foreground notifications are **shown by default** unless `setNotificationHandler` says otherwise. |
| `expo-localization` | iOS no longer force-enables RTL from the device locale; layout direction follows `I18nManager`. |
| `@expo/ui` | iOS top-aligns content instead of centring; `HStack`/`VStack`/`GlassEffectContainer` use SwiftUI's default spacing unless `spacing={0}`; Android `RNHostView` drops `style` for modifiers. |
| `expo-media-library` | iOS `Asset.getUri()` resolves the current Photos version of a video (`AssetUriVersion.ORIGINAL` for the old behaviour). |
| `@expo/fingerprint` | default preset is now `balanced`. |
| Android template | **R8 on by default** in release builds (`android.enableMinifyInReleaseBuilds=true`). Libraries relying on reflection may need ProGuard keep rules; opt out through `expo-build-properties`. |
| Expo CLI | every command now **sets `NODE_ENV`** before loading `.env` files, ignoring an inherited value: `NODE_ENV=test npx expo start` now loads `.env.development`, not `.env.test`. |

**Manual tests this crossing adds:** rotate and resize every screen on iOS 27 (including a foldable
simulator if available), a release Android build with R8 on, a foreground notification, and any
`.env`-dependent command whose mode you used to set from the outside.

## Where to find the authoritative list

Do not rely on memory or on this file's table alone for a specific SDK crossing — always cross-check:

1. `https://expo.dev/changelog` — the target SDK's full release notes, "Breaking Changes" section.
2. MCP Expo (`https://mcp.expo.dev/mcp`), if available, for current guidance.
3. The official `expo/skills` repo's `expo-upgrade` skill, if installed — it's the closest thing to a maintained per-SDK source.
