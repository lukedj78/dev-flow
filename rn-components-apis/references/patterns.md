> Sources: reactnative.dev/docs/components-and-apis, docs.expo.dev SDK reference, internal opinion.

# Patterns — RN core components + platform APIs

## Touchables — always `Pressable`

```tsx
import { Pressable, Text } from "react-native";

<Pressable
  onPress={handle}
  className="px-4 py-2 rounded-full bg-primary active:opacity-80"
  hitSlop={8}
>
  <Text className="text-white font-semibold">Save</Text>
</Pressable>
```

- `hitSlop` for small targets (icons): widen the touch zone without enlarging the visual.
- `active:opacity-80` via NativeWind for pressed feedback (or use `({ pressed }) => ...` callback for fine control).
- Never `<TouchableOpacity>` / `<TouchableHighlight>` / `<TouchableWithoutFeedback>`.

## Images — `expo-image`

```tsx
import { Image } from "expo-image";

<Image
  source={{ uri: "https://example.com/avatar.jpg" }}
  style={{ width: 96, height: 96, borderRadius: 48 }}
  contentFit="cover"
  placeholder={{ blurhash: "L6Pj0^jE.AyE_3t7t7R**0o#DgR4" }}
  transition={200}
/>
```

- Both `width` AND `height` mandatory (or `aspectRatio`).
- `placeholder` with a blurhash for remote images (generate at build time or hardcode for stable assets).
- `contentFit` instead of deprecated `resizeMode`.

## Lists — `FlashList`

```tsx
import { FlashList } from "@shopify/flash-list";

<FlashList
  data={items}
  renderItem={({ item }) => <Row item={item} />}
  estimatedItemSize={64}
  keyExtractor={(item) => item.id}
  ItemSeparatorComponent={() => <View className="h-px bg-zinc-200 dark:bg-zinc-800" />}
  onEndReached={loadMore}
  onEndReachedThreshold={0.5}
/>
```

- `estimatedItemSize` is REQUIRED — picks recycling pool size.
- For variable-size items, give a representative average.
- For grids: `numColumns={2}`.

## Keyboard avoidance

```tsx
import { KeyboardAvoidingView, Platform, ScrollView } from "react-native";

<KeyboardAvoidingView
  behavior={Platform.select({ ios: "padding", android: "height" })}
  keyboardVerticalOffset={Platform.select({ ios: 0, android: 24 })}
  className="flex-1"
>
  <ScrollView contentContainerClassName="p-4 gap-3" keyboardShouldPersistTaps="handled">
    {/* form fields */}
  </ScrollView>
</KeyboardAvoidingView>
```

- `behavior` MUST be set (different per platform).
- `keyboardShouldPersistTaps="handled"` lets users tap buttons inside the scroll without dismissing the keyboard first.

## Window dimensions — never at module top

```tsx
// ❌ wrong
import { Dimensions } from "react-native";
const { width } = Dimensions.get("window");

// ✅ correct
import { useWindowDimensions } from "react-native";
function MyComponent() {
  const { width, height } = useWindowDimensions();
  // recomputes on rotation, foldables, multi-window
}
```

## Platform-specific code

```tsx
import { Platform } from "react-native";

// Inline values: use Platform.select (typed, exhaustive)
const padding = Platform.select({ ios: 16, android: 12, default: 16 });

// Component branching: prefer the .ios.tsx / .android.tsx file convention
// Metro picks the right one automatically.

// Logic branching when truly different: Platform.OS, but extract to a helper.
```

## Linking — open external URLs / mail / phone / app

```tsx
import { Linking, Alert } from "react-native";

async function open(url: string) {
  const supported = await Linking.canOpenURL(url);
  if (!supported) {
    Alert.alert("Cannot open", url);
    return;
  }
  await Linking.openURL(url);
}

// Examples
open("https://example.com");
open("mailto:hello@example.com?subject=Hi");
open("tel:+391234567890");
open("sms:+391234567890&body=ciao");
```

## AppState — pause/resume timers and queries

```tsx
import { AppState } from "react-native";
import { useEffect } from "react";

useEffect(() => {
  const sub = AppState.addEventListener("change", (next) => {
    if (next === "active") {
      // refetch, restart polling
    } else if (next === "background") {
      // pause work
    }
  });
  return () => sub.remove();
}, []);
```

TanStack Query has built-in `refetchOnAppFocus` — prefer that over manual listeners when possible.
