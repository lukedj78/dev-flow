> Sources: reactnative.dev best practices, docs.expo.dev, codewithbeto.dev lessons 5-6 (free).

# Patterns and anti-patterns at the foundational level

## Project layout (mandatory)

```
my-app/
├── app/                  # Expo Router file-based routes
│   ├── _layout.tsx
│   └── index.tsx
├── components/           # presentational + reusable components
├── lib/                  # framework-agnostic helpers (api client, supabase, utils)
├── store/                # Zustand stores
├── types/                # shared TS types
├── assets/               # images, fonts
├── tailwind.config.js
├── global.css            # NativeWind v4 entry CSS
├── app.json
├── tsconfig.json
└── package.json
```

## DO

- ✅ Use `Pressable` for new touchable components.
- ✅ Wrap every root screen in `SafeAreaView` (from `react-native-safe-area-context`).
- ✅ Use `expo-image` for static and remote images (gives caching and placeholders).
- ✅ Use `@shopify/flash-list` for any list with > 20 items or unknown length.
- ✅ Use TypeScript paths (e.g. `@/components/Button`) configured in `tsconfig.json`.
- ✅ Read env vars only via `process.env.EXPO_PUBLIC_*` (public) or expo-constants (build-time secrets).

## DON'T

- ❌ Use `TouchableOpacity` / `TouchableHighlight` in new code — `Pressable` covers all cases.
- ❌ Hardcode magic numbers — pull from `tailwind.config.js` tokens.
- ❌ Use `Image` from `react-native` — use `expo-image`.
- ❌ Use `FlatList` for long lists — use `FlashList`.
- ❌ Use `react-navigation` directly — Expo Router wraps it.
- ❌ Use `console.log` in shipped code — use `expo-dev-tools` logging.
- ❌ Use `dimensions = Dimensions.get('window')` at module top-level — recompute on `useWindowDimensions` to handle rotation/foldables.

## When the rules clash with the course (codewithbeto)

The course teaches `TouchableOpacity`, `Image`, `FlatList`, and `StyleSheet` in the free lessons because they are simpler for beginners. In this skill set, **prefer the modern alternative** (`Pressable`, `expo-image`, `FlashList`, NativeWind). The course concepts still apply 1:1.
