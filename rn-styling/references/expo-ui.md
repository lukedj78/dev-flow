> Sources: official `expo-ui` skill (community-published, mirrors Expo's own guidance), docs.expo.dev/versions/latest/sdk/ui/. **Re-verified 2026-08-26 against `@expo/ui@57.0.14`** (`npm pack` + the `exports` map) and the live
SDK page. `[VERIFY]` again on an SDK major — this API is young and names/paths have already shifted
once (see the "community" vs "drop-in-replacements" note below).

⚠️ **Two different "current" versions, and they disagree by a patch.** The docs page says
*Recommended version: `~57.0.14`* (which is also npm `latest`), while `expo@57.0.16`'s
`bundledNativeModules.json` — what `npx expo install` actually resolves — pins **`~57.0.13`**. Take the
SDK's pin; the docs page tracks the package, not your SDK.

# `@expo/ui` — real native components, not styling

`@expo/ui` renders **actual native UI**: SwiftUI on iOS, Jetpack Compose on Android — and the docs list **tvOS** as a third supported platform, which this file previously omitted. This is a different axis from everything else in this skill — NativeWind and `StyleSheet` both style React Native's own primitives (`View`, `Text`, …), which are themselves a cross-platform abstraction. `@expo/ui` bypasses that abstraction entirely: you get the platform's own controls, not a styled lookalike.

## When to reach for it (vs NativeWind)

| Need | Use |
|---|---|
| Utility-first styling of RN primitives (spacing, color, layout, dark mode) | **NativeWind** (rest of this skill) |
| A screen that should *feel* native to each OS — grouped settings list, native toggle/switch, native picker/slider, a real action sheet or bottom sheet | **`@expo/ui`** |
| Custom native modules, Expo Router navigation, Reanimated-driven animation, data fetching | **Neither** — out of scope for `@expo/ui`, see `rn-expo-router`, `rn-animations-gestures`, `data-fetching` |

`@expo/ui` is not a replacement for NativeWind and not a competitor to `rn-components-apis`' core-component guidance — it's a third option you pull in specifically when a screen needs to look and behave like a first-party iOS/Android screen (Settings-app-style grouped sections, native `Picker`/`Slider`, a real `BottomSheet`), not when you just need a themed `View`.

## Three levels — import paths verified against the `exports` map of `@expo/ui@57.0.14`

1. **Universal components** — `import { Host, Column, Row, Button, Text, List } from '@expo/ui'`
   Re-verified at **57.0.14** (`build/universal/index.d.ts`, a barrel of `export *` lines — grep the file, not the package): the root exports 19: `Host`, `Column`, `Row`, `Text`, `Button`, `ScrollView`, `Switch`, `Slider`, `Checkbox`, `BottomSheet`, `Collapsible`, `FieldGroup`, `Icon`, `List`, `ListItem`, `Picker`, `Spacer`, `State`, `TextInput` (plus `RNHostView`).
   One component tree that renders on iOS, Android, and web.

   **The "SDK 56+ floor" was hearsay — the docs badge the package `Included in Expo Go`.** No floor is
   stated on the page and no dev client is required for this layer. Checked that the badge actually
   discriminates rather than being boilerplate: on the same doc template, `expo-notifications` and
   `expo-dev-client` show no such badge, `@expo/ui` does.
   `Host` is the root wrapper every `@expo/ui` tree needs — **verified**: it is exported from the root (`build/universal/index.d.ts`), so always import it from `@expo/ui`, never from the platform-specific subpaths below.

2. **Per-platform layers** — iOS-only vs Android-only, and they **will crash if imported on the wrong platform**:
   - `import { ... } from '@expo/ui/swift-ui'` — iOS only.
   - `import { ... } from '@expo/ui/jetpack-compose'` — Android only.
   - Each has a **`/modifiers` companion** — `@expo/ui/swift-ui/modifiers`, `@expo/ui/jetpack-compose/modifiers` — the platform-native styling escape hatch (a SwiftUI/Compose modifier chain, not a style object). Same platform restriction applies.
   - There is also a **`@expo/ui/babel-plugin`** subpath. Neither of these was documented here before; both are in the `exports` map at 57.0.14.
   - Importing either on the other platform fails at runtime with an error along the lines of **"Unable to get view config"** — not a build-time TypeScript error, so it's easy to ship by accident.
   - Mitigation: split platform-specific trees into `.ios.tsx` / `.android.tsx` files, placed under `components/` (**not** `app/` — Expo Router does not support platform-extension route files), or guard with `Platform.OS` checks. This is the same `.ios.tsx`/`.android.tsx` split pattern used elsewhere in the RN skills for platform divergence, just non-negotiable here because the failure mode is a runtime crash, not a lint warning.

3. **Drop-in replacements** — API-compatible swaps for existing community libraries, backed by native `@expo/ui` primitives underneath.
   - **Settled: the subpath is `@expo/ui/community/<name>`.** Re-verified against the `exports` map at **57.0.14** — `drop-in-replacements/` **does not exist** and never did; the two "sources disagreeing" were one source and one guess. Still exactly eight: `bottom-sheet`, `datetime-picker`, `masked-view`, `menu`, `pager-view`, `picker`, `segmented-control`, `slider`.
   - Example target: a `BottomSheet` drop-in for `@gorhom/bottom-sheet`, wrapping `ModalBottomSheet` (Jetpack Compose) on Android and SwiftUI's `BottomSheet` on iOS. Note a plain `BottomSheet` **also** ships in the universal layer, so check which one you want before reaching for `community/bottom-sheet`.

## Not for

- Custom native modules (that's the Expo Modules API, a different tool entirely).
- Expo Router navigation — `@expo/ui` has no navigation primitives.
- Reanimated-driven animation — `@expo/ui` components are native controls, not animatable RN views.
- Data fetching — orthogonal concern, see `data-fetching`.

## Quick self-check before using `@expo/ui`

- Am I trying to make RN primitives *look* native (color/spacing/motion)? → Not this. Use NativeWind.
- Do I need an actual native control (grouped settings section, native slider/picker, real action sheet/bottom sheet)? → `@expo/ui`, universal layer first, per-platform layer only if the universal one doesn't cover it.
- Did I just import `@expo/ui/swift-ui` or `@expo/ui/jetpack-compose` in a file with no `.ios.`/`.android.` split and no `Platform.OS` guard? → Fix before it crashes on the other platform.
