---
name: rn-components-apis
description: 'Use when working with React Native core components (View, Text, ScrollView, FlatList, TextInput, Pressable, Modal, KeyboardAvoidingView, SafeAreaView) or platform APIs (Platform, Dimensions, useWindowDimensions, Linking, AppState). Triggers on: "which RN component should I use", "ScrollView vs FlatList", "how do I handle keyboard avoidance", "platform-specific code", "open external URL". Not for: styling (rn-styling), navigation (rn-expo-router), data fetching (rn-data-fetching), animations (rn-animations-gestures, Wave 3).'
---

# rn-components-apis — guardrail for RN core components + platform APIs

## The 5 rules (non-negotiable)

1. **`Pressable` for any touchable** — never `TouchableOpacity` / `TouchableHighlight` / `TouchableWithoutFeedback` in new code.
2. **`expo-image` for any image** — never `Image` from `react-native` (no caching).
3. **`@shopify/flash-list` for lists** with > 20 items or unknown length — never `FlatList` at scale.
4. **`useWindowDimensions()` hook** in the component — never `Dimensions.get('window')` at module top-level (fails on rotation/foldables).
5. **`Platform.select({ ios, android })`** for platform-specific styles or behavior — never `Platform.OS === ...` ternaries scattered across the file.

## Quick decision tree

- "Which list primitive?" → `references/decision-tree.md` (ScrollView/FlatList/FlashList/SectionList)
- "Which touchable?" → always `Pressable`. See `references/patterns.md` for the canonical button pattern.
- "How do I open an external URL / mail / phone?" → `references/patterns.md` (Linking section)
- "Keyboard avoidance pattern?" → `references/patterns.md` (KeyboardAvoidingView + Android quirks)
- "I need a **map** in this screen" → `references/maps-mapcn-rn.md` (**mapcn-rn**, the ecosystem-first default: MapLibre/Mapbox RN + NativeWind). ⚠️ native modules → needs a **dev build, not Expo Go**. Record `stack.maps = "mapcn-rn"`.
- "None of these core components feel native enough for this screen" → these are all *RN* primitives (a JS abstraction over both platforms). For real native controls instead — SwiftUI on iOS, Jetpack Compose on Android (grouped settings sections, native picker/slider, real sheets) — that's `@expo/ui`, a different tool. See `rn-styling/references/expo-ui.md` (`[VERIFY]` against mcp.expo.dev) for the full breakdown; this skill's guidance still applies whenever you're using `View`/`Text`/`ScrollView`/etc. as-is.

## Common anti-patterns (NEVER do)

- ❌ `<TouchableOpacity onPress={...}>` → `<Pressable onPress={...}>`
- ❌ `<Image source={{ uri }} />` from `react-native` → `import { Image } from "expo-image"`
- ❌ `<FlatList data={items}>` for any list that may grow → `<FlashList data={items}>` (FlashList v2 auto-sizes — no `estimatedItemSize`)
- ❌ `const { width } = Dimensions.get('window')` at module top — use `useWindowDimensions()` inside the component
- ❌ `<KeyboardAvoidingView>` without explicit `behavior` prop — broken on Android. Use `Platform.select({ ios: "padding", android: "height" })`

## Sources

- Course: codewithbeto.dev/rnCourse — "Components and APIs" module (paid, distilled from docs).
- Official: https://reactnative.dev/docs/components-and-apis
- Official: https://docs.expo.dev/versions/latest/sdk/image/
- Official: https://shopify.github.io/flash-list/
- Official: https://docs.expo.dev/versions/latest/sdk/ui/ (`@expo/ui` — native alternative to these components; see `rn-styling/references/expo-ui.md`)
