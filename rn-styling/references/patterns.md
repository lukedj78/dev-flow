> Sources: NativeWind v4 docs, reactnative.dev, internal opinion.

# Patterns and anti-patterns — styling

## Layout

### DO

- ✅ Root screen pattern:
  ```tsx
  <SafeAreaView className="flex-1 bg-white dark:bg-zinc-900">
    <ScrollView className="flex-1" contentContainerClassName="p-4 gap-4">
      {/* content */}
    </ScrollView>
  </SafeAreaView>
  ```
- ✅ Spacing between siblings via `gap-*` (NativeWind v4 supports it), not margins.
- ✅ `useWindowDimensions()` inside the component (not at module level).

### DON'T

- ❌ `flex: 1` without `flexDirection` explicit when ambiguous.
- ❌ Nested `ScrollView` (use one outer, multiple inner `<View>`).
- ❌ Fixed pixel heights for "% of screen" intent — use `dimensions.height * 0.5`.

## Color & theme

### DO

- ✅ Always pair light + dark: `bg-white dark:bg-zinc-900`, `text-zinc-900 dark:text-zinc-50`.
- ✅ Define semantic tokens in `tailwind.config.js` (`bg-background`, `bg-card`, `bg-primary`) — map to DESIGN.md.

### DON'T

- ❌ Hex literals inline: `style={{ color: '#0ea5e9' }}` → use `text-primary`.
- ❌ Forgetting the dark variant when introducing a new colored element.

## Typography

### DO

- ✅ Limit to 3-5 type scale steps defined in `tailwind.config.js` (`text-xs`, `text-sm`, `text-base`, `text-lg`, `text-2xl`).
- ✅ Load fonts via `expo-font` in `app/_layout.tsx`, surface via Tailwind `fontFamily`.

### DON'T

- ❌ `fontFamily: 'Helvetica'` literal in a component — Tailwind token only.
- ❌ Mixing system font + custom font without a fallback chain.

## Images

### DO

- ✅ `expo-image` for ALL images (static + remote):
  ```tsx
  import { Image } from 'expo-image';
  <Image source={uri} style={{ width: 200, height: 200 }} contentFit="cover" />
  ```
- ✅ Provide a `placeholder` (blurhash or local thumbnail) for remote.

### DON'T

- ❌ `import { Image } from 'react-native'` for remote — no caching.
- ❌ Setting only width OR only height — `expo-image` needs both (or `aspectRatio`).

## Lists

### DO

- ✅ `FlashList` for any list > 20 items or unknown length:
  ```tsx
  import { FlashList } from '@shopify/flash-list';
  <FlashList data={items} renderItem={({ item }) => <Row item={item} />} estimatedItemSize={64} />
  ```

### DON'T

- ❌ `FlatList` for long lists — slower at scale.
- ❌ `ScrollView` + `.map()` for any list with > 10 items.
