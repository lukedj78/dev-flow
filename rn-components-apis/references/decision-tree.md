> Sources: reactnative.dev, shopify.github.io/flash-list, internal opinion.

# Decision tree — RN core components

## Q1: Which list primitive?

```
How many items, max?
├── ≤ 10 items, static  → ScrollView + .map() (simple, no recycling needed)
├── ≤ 20 items, dynamic → FlashList (overkill is fine, future-proof)
└── > 20 / unknown      → FlashList. Mandatory. FlatList is slower at scale.

Are items grouped by header (sections)?
├── YES → FlashList with section data + ItemSeparatorComponent or a custom render
└── NO  → flat FlashList
```

Never use `SectionList` — `FlashList` covers the use case with better perf.

## Q2: Which touchable?

```
Always Pressable. No exceptions in this skill set.
```

Why: `Pressable` is the only modern primitive. It exposes both `onPress` and the `pressed` state via render prop, supports `hitSlop`, and handles edge cases (long-press, double-tap) without a separate component.

`TouchableOpacity`, `TouchableHighlight`, `TouchableWithoutFeedback` are legacy.

## Q3: Image — local asset or remote URL?

```
Source type?
├── Local require()           → `expo-image` (`source={require("./asset.png")}`)
├── Remote URL string         → `expo-image` (`source={{ uri }}` with placeholder)
└── Vector / SVG              → `react-native-svg` (a separate dep — out of scope here, see rn-add-screen if needed)
```

Always `expo-image` for raster. Never `Image` from `react-native`.

## Q4: How to show a long-press menu / context menu?

```
Platform-native menu acceptable?
├── YES → expo-haptics + Pressable with onLongPress + a custom Modal
└── NEED REAL native menu → out of scope for Wave 2; in Wave 3 we'll add a skill for native modules
```

## Q5: TextInput with masked input (e.g. phone, money)?

```
Use `react-native-mask-text` or `expo-checkbox` for checkboxes. For the masked input:
- Light masking → onChangeText callback with manual regex
- Heavy masking → react-native-mask-text (small lib, well-maintained)
```

## Q6: Modal vs bottom sheet?

```
Use case?
├── Quick confirmation, dismiss-on-tap-outside → expo-router modal route (see rn-expo-router)
├── Persistent drawer-style sheet              → @gorhom/bottom-sheet (a dep, but standard)
└── Native iOS action sheet                    → expo's ActionSheet wrapper
```

For Wave 2 we recommend modal routes via Expo Router (already in rn-expo-router). `@gorhom/bottom-sheet` is a separate decision when you actually need a sheet — adopt then.
