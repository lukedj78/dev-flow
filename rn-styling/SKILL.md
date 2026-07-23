---
name: rn-styling
description: 'Use when styling React Native + Expo components: choosing between StyleSheet/NativeWind/inline, wiring NativeWind v4 from DESIGN.md tokens, handling Flexbox in RN (column-by-default, not row), safe-area insets, dark mode, responsive design with useWindowDimensions, optimized images via expo-image, performant lists via FlashList, and choosing NativeWind vs real native components via @expo/ui (SwiftUI/Jetpack Compose). Triggers on: "style this screen", "add dark mode", "fix safe area", "import design tokens", "set up NativeWind", "native settings screen", "@expo/ui", or when an agent is about to write StyleSheet/className in an RN file. Not for: building screens end-to-end (rn-add-screen, Wave 2), navigation (rn-expo-router), animations (rn-animations-gestures, Wave 3), or web styling (Next.js stack).'
---

# rn-styling — guardrail for styling in React Native + Expo

## The 5 rules (non-negotiable)

1. **NativeWind v4 is the default**. `StyleSheet` only for performance-critical paths (per-frame animations etc.).
2. **No magic numbers**. Every spacing/color/radius/font value comes from `tailwind.config.js` (which mirrors the project's DESIGN.md tokens).
3. **SafeArea mandatory on every root screen**. Use `SafeAreaView` from `react-native-safe-area-context` (NOT the one from `react-native`).
4. **Dark mode via `useColorScheme` + Tailwind `dark:` variant**. Never `Appearance.getColorScheme()` at module top-level.
5. **Optimized primitives**: `expo-image` instead of `Image`; `@shopify/flash-list` for any list > 20 items.

## Quick decision tree

- "Should I style this with NativeWind or StyleSheet?" → `references/decision-tree.md`
- "How do I set up NativeWind v4 from scratch?" → `references/nativewind-setup.md`
- "Why does Flexbox behave differently than on the web?" → `references/concepts.md`
- "What are the common patterns and anti-patterns?" → `references/patterns.md`
- "Show me a real example" → `references/examples/`
- "I need this screen to *feel* native, not just look styled" (grouped settings, native toggle/picker/slider, real bottom sheet) → this isn't a styling question, it's `references/expo-ui.md` (`@expo/ui`) — real SwiftUI/Jetpack Compose components, not RN primitives.

## NativeWind vs `@expo/ui` — two different tools

- **NativeWind** (this skill's default) styles RN's own primitives (`View`, `Text`, …) with utility classes. It changes how things *look*.
- **`@expo/ui`** (see `references/expo-ui.md`, `[VERIFY]` against mcp.expo.dev) renders **actual native components** — SwiftUI on iOS, Jetpack Compose on Android — not styled primitives. Reach for it when a screen needs to genuinely behave like a native settings/picker/sheet screen, not when it just needs the right colors and spacing.
- They compose: an `@expo/ui` tree can sit inside a NativeWind-styled screen. Don't use `@expo/ui` as a general-purpose styling system, and don't expect NativeWind classes to apply inside its native components.

## Common anti-patterns (NEVER do)

- ❌ `style={{ padding: 16 }}` with a magic number — pull from token.
- ❌ Root `<View>` without `SafeAreaView` from `react-native-safe-area-context`.
- ❌ `import "tailwindcss"` directly in code — only NativeWind imports.
- ❌ `Appearance.getColorScheme()` at module level — use `useColorScheme()` hook.
- ❌ `Image` from `react-native` for remote URIs — use `expo-image`.
- ❌ `flex: 1` on root + scroll without `contentContainerStyle` on `ScrollView` — content gets clipped.

## Sources

- Course: codewithbeto.dev/rnCourse — lesson 10 "Styling Your App" (free).
- Official: https://docs.expo.dev/develop/user-interface/styling/
- Official: https://www.nativewind.dev/ (v4)
- Official: https://github.com/AppAndFlow/react-native-safe-area-context
- Official: https://docs.expo.dev/versions/latest/sdk/ui/ (`@expo/ui`) — `[VERIFY]` exact import paths/SDK floor via mcp.expo.dev, see `references/expo-ui.md`
