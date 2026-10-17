> Sources: reactnative.dev/architecture, docs.expo.dev/get-started, codewithbeto.dev lessons 1-3 (free).

# Concepts — React Native + Expo

## RN vs React on the web (one-line each)

- **DOM**: there is none. JSX maps to native views (`<View>` → `UIView` on iOS / `android.view.View` on Android), not to `<div>`.
- **Styling**: no CSS cascade. Styles are JS objects (via `StyleSheet`, NativeWind, or inline). Layout is **Flexbox by default, in column direction** (web is row).
- **Events**: `onPress`, not `onClick`. `Pressable` is the modern primitive (NOT `TouchableOpacity` for new code).
- **Routing**: no `<a href>`. Use Expo Router (file-based, see `rn-expo-router`).
- **Persistence**: no `localStorage`. Use `AsyncStorage` or `expo-secure-store`.

## The bridge, JSI, Fabric, Hermes (what to actually know)

- **Old Architecture**: JS thread talks to native via a serialized "bridge". Async only, batching, sometimes laggy.
- **JSI (JavaScript Interface)**: replaces the bridge with direct C++ binding. Synchronous calls become possible.
- **Fabric**: the new UI renderer built on JSI. Concurrent rendering capable.
- **TurboModules**: native modules over JSI. Lazy-loaded.
- **Hermes**: the JS engine optimized for RN (smaller bundle, faster start). Default since SDK 49.
- **New Architecture = Fabric + TurboModules + Hermes**. Nothing to enable: since **SDK 55 it is always on and cannot be disabled**, and `newArchEnabled` is ignored (it is not even in `@expo/config-types@58.0.3`'s schema, checked 2026-10-17).

## Managed vs bare (TL;DR)

- **Managed**: `app.json` describes the native config; you don't touch Xcode/Android Studio. Expo prebuild generates native code on demand. 95% of apps.
- **Bare**: you own `ios/` and `android/` folders. Use when you need a native library Expo cannot wrap (rare).
- **Expo Go**: dev sandbox for managed apps with no custom native deps. Quick to start, can't load custom native modules. ⚠️ We ship **SDK 58**; the store Expo Go that supports it (SDK 58 only) is announced for the App Store and Google Play "within a few weeks" of 2026-10-15 — until then no store build opens our project (the App Store one was frozen at SDK 54 through SDK 57). Use a dev build. See `decision-tree.md` Q2.
- **Dev client** (`expo-dev-client`): custom Expo Go for your app, supports any native module. **This is the default** — start here rather than reaching for Expo Go.

## Sources

- https://reactnative.dev/architecture/landing-page
- https://docs.expo.dev/workflow/overview/
- https://docs.expo.dev/develop/development-builds/introduction/
