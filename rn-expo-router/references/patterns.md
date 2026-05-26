> Sources: docs.expo.dev/router/advanced, internal opinion.

# Patterns and anti-patterns — Expo Router

## Navigation

### DO

- ✅ `useRouter()` for imperative navigation:
  ```tsx
  const router = useRouter();
  router.push({ pathname: "/profile/[id]", params: { id: "abc" } });
  router.back();
  router.replace("/");
  ```
- ✅ `<Link>` for declarative:
  ```tsx
  <Link href={{ pathname: "/profile/[id]", params: { id: "abc" } }}>View profile</Link>
  ```
- ✅ `useLocalSearchParams<T>()` for typed dynamic segment / query params.

### DON'T

- ❌ `useNavigation()` from `@react-navigation/native` — Expo Router has its own primitives.
- ❌ Raw-string `router.push('/profile/abc')` — typed routes catch typos.
- ❌ Multiple nested navigators when a group + single navigator would do.

## Modals

A modal is a screen with `presentation: 'modal'`. Live under any layout.

```tsx
// app/_layout.tsx
<Stack>
  <Stack.Screen name="(tabs)" options={{ headerShown: false }} />
  <Stack.Screen name="settings-modal" options={{ presentation: "modal" }} />
</Stack>
```

```tsx
// app/settings-modal.tsx
import { View, Text } from "react-native";
export default function SettingsModal() {
  return <View><Text>Modal content</Text></View>;
}
```

Open via `router.push('/settings-modal')`.

## Auth gating

Pattern: protected group `(app)` with a `_layout.tsx` that redirects.

```tsx
// app/(app)/_layout.tsx
import { Redirect, Stack } from "expo-router";
import { useUser } from "@/lib/auth"; // your auth hook (see rn-backend Wave 3, provider-agnostic)

export default function ProtectedLayout() {
  const user = useUser();
  if (!user) return <Redirect href="/(auth)/sign-in" />;
  return <Stack />;
}
```

## Search params

```tsx
import { useLocalSearchParams } from "expo-router";

type Params = { id: string; tab?: "info" | "posts" };

export default function Profile() {
  const { id, tab = "info" } = useLocalSearchParams<Params>();
  return <Text>{id} - {tab}</Text>;
}
```

For non-route screens that observe URL changes, use `useGlobalSearchParams` (re-renders on any change).

## Anti-patterns

- ❌ Putting `<Tabs.Screen>` inside the screen component instead of the layout — won't work, Tabs ignores it.
- ❌ Two `_layout.tsx` at the same level — only one is allowed per directory.
- ❌ Defining a route AND a group with the same name (`profile.tsx` + `(profile)/`) — collision.
- ❌ Using `window.location` for URL parsing — use `usePathname()` from expo-router.
