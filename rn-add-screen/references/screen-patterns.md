> Sources: synthesized from rn-styling, rn-expo-router, rn-data-fetching, rn-components-apis patterns.

# Canonical screen patterns (for rn-add-screen)

Five templates cover ~90% of mobile app screens. Pick one, fill in the blanks, never mix unless the requirement is genuinely hybrid.

## 1. List screen (FlashList + TanStack Query)

Use for: feed, search results, inbox, any "many items, scroll, refresh".

```tsx
// app/posts/index.tsx
import { Text, Pressable, ActivityIndicator } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { FlashList } from "@shopify/flash-list";
import { useQuery } from "@tanstack/react-query";
import { Link } from "expo-router";
import { queryKeys } from "@/lib/query-keys";
import { api } from "@/lib/api";

type Post = { id: string; title: string; author: string };

export default function PostsScreen() {
  const { data, isLoading, isError, refetch, isRefetching } = useQuery({
    queryKey: queryKeys.posts.list(),
    queryFn: ({ signal }) => api<Post[]>("/posts", { signal }),
    staleTime: 30_000,
  });

  if (isLoading)
    return (
      <SafeAreaView className="flex-1 items-center justify-center">
        <ActivityIndicator />
      </SafeAreaView>
    );

  if (isError)
    return (
      <SafeAreaView className="flex-1 items-center justify-center p-4 gap-3">
        <Text>Could not load posts.</Text>
        <Pressable onPress={() => refetch()} className="px-4 py-2 rounded-full bg-primary">
          <Text className="text-white">Retry</Text>
        </Pressable>
      </SafeAreaView>
    );

  return (
    <SafeAreaView className="flex-1 bg-background dark:bg-background-dark">
      <FlashList
        data={data ?? []}
        keyExtractor={(item) => item.id}
        refreshing={isRefetching}
        onRefresh={refetch}
        renderItem={({ item }) => (
          <Link href={{ pathname: "/posts/[id]", params: { id: item.id } }} asChild>
            <Pressable className="px-4 py-3 border-b border-zinc-200 dark:border-zinc-800">
              <Text className="text-base font-semibold">{item.title}</Text>
              <Text className="text-sm text-zinc-600 dark:text-zinc-400">by {item.author}</Text>
            </Pressable>
          </Link>
        )}
      />
    </SafeAreaView>
  );
}
```

FlashList v2 auto-sizes items — no `estimatedItemSize` prop needed (that was required in v1, now deprecated).

## 2. Detail screen (typed search params + query)

Use for: any "tap on list item → see details" screen.

```tsx
// app/posts/[id].tsx
import { Text, View, ScrollView, ActivityIndicator } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { useLocalSearchParams } from "expo-router";
import { useQuery } from "@tanstack/react-query";
import { queryKeys } from "@/lib/query-keys";
import { api } from "@/lib/api";

type Params = { id: string };
type Post = { id: string; title: string; body: string; author: string };

export default function PostDetail() {
  const { id } = useLocalSearchParams<Params>();
  const { data, isLoading } = useQuery({
    queryKey: queryKeys.posts.detail(id),
    queryFn: ({ signal }) => api<Post>(`/posts/${id}`, { signal }),
  });

  if (isLoading || !data)
    return (
      <SafeAreaView className="flex-1 items-center justify-center">
        <ActivityIndicator />
      </SafeAreaView>
    );

  return (
    <SafeAreaView className="flex-1 bg-background dark:bg-background-dark">
      <ScrollView contentContainerClassName="p-4 gap-4">
        <Text className="text-2xl font-semibold">{data.title}</Text>
        <Text className="text-sm text-zinc-600 dark:text-zinc-400">by {data.author}</Text>
        <Text className="text-base">{data.body}</Text>
      </ScrollView>
    </SafeAreaView>
  );
}
```

## 3. Form screen (KeyboardAvoidingView + mutation)

Use for: sign-in, sign-up, create-post, edit-profile, settings.

```tsx
// app/(auth)/sign-in.tsx
import { useState } from "react";
import { Text, TextInput, Pressable, KeyboardAvoidingView, Platform, ScrollView } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { useMutation } from "@tanstack/react-query";
import { useRouter } from "expo-router";
import { api } from "@/lib/api";

export default function SignInScreen() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const router = useRouter();

  const signIn = useMutation({
    mutationFn: () => api<{ token: string }>("/auth/sign-in", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    }),
    onSuccess: () => router.replace("/(app)"),
  });

  return (
    <SafeAreaView className="flex-1 bg-background dark:bg-background-dark">
      <KeyboardAvoidingView
        behavior={Platform.select({ ios: "padding", android: "height" })}
        className="flex-1"
      >
        <ScrollView contentContainerClassName="p-4 gap-4" keyboardShouldPersistTaps="handled">
          <Text className="text-2xl font-semibold">Welcome back</Text>

          <TextInput
            value={email}
            onChangeText={setEmail}
            placeholder="Email"
            autoCapitalize="none"
            autoComplete="email"
            keyboardType="email-address"
            className="px-3 py-3 rounded-lg border border-zinc-300 dark:border-zinc-700 text-zinc-900 dark:text-zinc-50"
          />

          <TextInput
            value={password}
            onChangeText={setPassword}
            placeholder="Password"
            secureTextEntry
            autoCapitalize="none"
            autoComplete="password"
            className="px-3 py-3 rounded-lg border border-zinc-300 dark:border-zinc-700 text-zinc-900 dark:text-zinc-50"
          />

          {signIn.isError && (
            <Text className="text-red-600 dark:text-red-400">
              {(signIn.error as Error).message}
            </Text>
          )}

          <Pressable
            onPress={() => signIn.mutate()}
            disabled={signIn.isPending || !email || !password}
            className="px-4 py-3 rounded-full bg-primary active:opacity-80 disabled:opacity-50"
          >
            <Text className="text-center text-white font-semibold">
              {signIn.isPending ? "Signing in…" : "Sign in"}
            </Text>
          </Pressable>
        </ScrollView>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}
```

## 4. Modal screen

Declared in the parent `_layout.tsx`:

```tsx
// app/_layout.tsx (root)
<Stack>
  <Stack.Screen name="(tabs)" options={{ headerShown: false }} />
  <Stack.Screen name="filters" options={{ presentation: "modal", title: "Filters" }} />
</Stack>
```

```tsx
// app/filters.tsx
import { Text, View, Pressable } from "react-native";
import { useRouter } from "expo-router";

export default function FiltersModal() {
  const router = useRouter();
  return (
    <View className="flex-1 bg-background dark:bg-background-dark p-4 gap-4">
      <Text className="text-xl font-semibold">Filters</Text>
      {/* filter controls */}
      <Pressable
        onPress={() => router.back()}
        className="self-end px-4 py-2 rounded-full bg-primary"
      >
        <Text className="text-white">Apply</Text>
      </Pressable>
    </View>
  );
}
```

Modals do NOT need `SafeAreaView` — the modal presentation already accounts for safe area on iOS. On Android, add `edges={['top']}` if the modal is full-bleed.

## 5. Auth-gated screen (inside `(app)/` group)

```tsx
// app/(app)/_layout.tsx
import { Redirect, Stack } from "expo-router";
import { useUser } from "@/lib/auth";

export default function ProtectedLayout() {
  const user = useUser();
  if (user === undefined) return null; // still loading
  if (user === null) return <Redirect href="/(auth)/sign-in" />;
  return <Stack />;
}
```

Then any screen at `app/(app)/...` is protected. The screen file itself contains only its content — no auth check needed inside.

## Route → file mapping (cheat sheet)

| URL | File |
|---|---|
| `/` | `app/index.tsx` |
| `/about` | `app/about.tsx` |
| `/profile/abc` | `app/profile/[id].tsx` |
| `/posts/abc/comments` | `app/posts/[id]/comments.tsx` |
| `/(tabs)/feed` | `app/(tabs)/feed.tsx` (URL strips group) |
| `/(auth)/sign-in` | `app/(auth)/sign-in.tsx` |
| `*` (not found) | `app/+not-found.tsx` |

## When you need to pull out a component

If the screen has > ~120 lines or contains a sub-piece that would be reused, extract to `components/<feature>/` (L0) — NEVER into `app/`, since Expo Router has no private-folder convention there (every file under `app/` is a route; see SKILL.md "Folder structure rules"):

```
components/posts/
├── PostCard.tsx
├── EmptyState.tsx
└── LoadingScreen.tsx
```

Components NEVER import from `expo-router` directly (no `Link`, no `useRouter` inside leaf components). Pass `onPress` / `href` as props so they stay reusable.
