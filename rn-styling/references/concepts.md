> Sources: reactnative.dev/docs/flexbox, docs.expo.dev styling, codewithbeto.dev lesson 10 (free).

# Concepts — styling in React Native

## Flexbox: column by default

In RN, the default `flexDirection` is `column` (web defaults to `row`). This trips up every web developer. Always explicit: write `flexDirection: 'row'` (or `flex-row` in NativeWind) when you want horizontal.

```tsx
<View className="flex-1 flex-col">     {/* default, but be explicit */}
  <Text>top</Text>
  <Text>bottom</Text>
</View>

<View className="flex-1 flex-row">     {/* horizontal */}
  <Text>left</Text>
  <Text>right</Text>
</View>
```

## Units: no px, no em, no rem

Numbers are **density-independent pixels** (DIPs). `padding: 16` ≈ `16dp`. Tailwind's spacing scale (`p-4` = 16, `p-2` = 8, etc.) maps to the same numeric values.

For percent-of-parent, use a string: `width: '50%'`. For percent-of-screen, use `useWindowDimensions()` (NOT `Dimensions.get('window')` at module top-level).

## Safe area: why and where

iPhones with notches and Androids with cutouts have non-touchable insets at top/bottom. Wrap root screens in `SafeAreaView` from `react-native-safe-area-context` (NOT the deprecated one from `react-native`):

```tsx
import { SafeAreaView } from 'react-native-safe-area-context';

export default function Screen() {
  return (
    <SafeAreaView className="flex-1 bg-white dark:bg-zinc-900" edges={['top', 'bottom']}>
      {/* content */}
    </SafeAreaView>
  );
}
```

`edges` lets you opt out of inset on sides where the parent already handles it (e.g. tab bar covers `bottom`).

## Dark mode: reactive only

```tsx
// ❌ wrong — not reactive to runtime theme change
import { Appearance } from 'react-native';
const theme = Appearance.getColorScheme();

// ✅ correct — re-renders on theme change
import { useColorScheme } from 'react-native';
function Foo() {
  const colorScheme = useColorScheme(); // 'light' | 'dark' | null
  // …
}
```

With NativeWind, prefer the `dark:` variant — no hook needed:

```tsx
<View className="bg-white dark:bg-zinc-900">
  <Text className="text-zinc-900 dark:text-zinc-50">hello</Text>
</View>
```

## Tokens: DESIGN.md → tailwind.config.js

The project's `DESIGN.md` is the source of truth for colors, spacing, radii, type scale. The bootstrap step generates `tailwind.config.js` from it. NEVER hardcode a color or spacing value in a component; if you need a value that's not in the config, add it to `DESIGN.md` and re-run the generator.

## Sources

- https://reactnative.dev/docs/flexbox
- https://reactnative.dev/docs/style (the Expo `develop/user-interface/styling/` page 404s as of 2026-08-26; see `color-themes/`, `safe-areas/`, `fonts/` for the Expo-side topics)
- https://github.com/AppAndFlow/react-native-safe-area-context
