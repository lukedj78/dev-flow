# TanStack Query — the mobile production default (Expo + RN)

The **how**, not just "use TanStack Query". Doc-grounded against `tanstack.com/query/latest` (React Native page, mutations, optimistic updates, infinite queries, `createAsyncStoragePersister`, `persistQueryClient`). Verified `@tanstack/react-query` **5.101.4** (2026-08) — the repo pins `^5` (see `rn-fundamentals/references/stack-defaults.md`). `[VERIFY]` every identifier against the installed version.

## Why this is the DEFAULT here, not a last resort

On the web, `data-fetching` says: async Server Components first, SWR/React Query only as an escape hatch. **React Native has no Server Components and no server render** — every screen is a client component and every read is a network call from the device. So the web escape hatch becomes the mobile baseline: TanStack Query owns *all* server state (cache, dedup, retry, cancel, refetch, offline). `fetch + useEffect` stays didactic-only (rule 1 of `SKILL.md`).

## Install

```bash
npx expo install @tanstack/react-query @react-native-community/netinfo -- --legacy-peer-deps
# optional persistence
npx expo install @tanstack/react-query-persist-client \
  @tanstack/query-async-storage-persister \
  @react-native-async-storage/async-storage -- --legacy-peer-deps
```

## Provider + the RN-specific wiring

The docs call out two managers that **do nothing on RN unless you bridge them yourself**: `onlineManager` (there is no `navigator.onLine`) and `focusManager` (there is no `window` focus event).

```tsx
// app/_layout.tsx — one QueryClient per app, at the root layout (rule 2)
import "../global.css";
import { useEffect, useState } from "react";
import { AppState, Platform, type AppStateStatus } from "react-native";
import { Stack } from "expo-router";
import NetInfo from "@react-native-community/netinfo";
import { QueryClient, QueryClientProvider, focusManager, onlineManager } from "@tanstack/react-query";

// Online status — registered once, at module scope.
onlineManager.setEventListener((setOnline) =>
  NetInfo.addEventListener((state) => setOnline(!!state.isConnected)),
);

function onAppStateChange(status: AppStateStatus) {
  if (Platform.OS !== "web") focusManager.setFocused(status === "active");
}

export default function RootLayout() {
  const [client] = useState(() => new QueryClient({
    defaultOptions: {
      queries: {
        retry: 2,
        staleTime: 60_000,          // rule 5 — avoid refetch-on-focus storms
        refetchOnReconnect: true,   // dead without onlineManager above
        refetchOnWindowFocus: true, // dead without the AppState bridge below
      },
      mutations: { retry: 0 },
    },
  }));

  useEffect(() => {
    const sub = AppState.addEventListener("change", onAppStateChange);
    return () => sub.remove();
  }, []);

  return (
    <QueryClientProvider client={client}>
      <Stack />
    </QueryClientProvider>
  );
}
```

`useState(() => new QueryClient())` — one instance across Fast Refresh. Expo alternative to NetInfo: `expo-network`'s `addNetworkStateListener` + `getNetworkStateAsync()` (also documented on the RN page).

## Query keys, queries, mutations, invalidation

Keys are arrays, hierarchical, most specific filter last (rule 3). Centralize them so invalidation can't typo:

```ts
// lib/query-keys.ts
export const qk = {
  posts: {
    all: ["posts"] as const,
    list: (filter: string) => ["posts", "list", { filter }] as const,
    detail: (id: string) => ["posts", "detail", id] as const,
  },
};
```

```tsx
const { data, isPending, isError, error } = useQuery({
  queryKey: qk.posts.list(filter),
  queryFn: async ({ signal }) => {          // always forward `signal` → cancel on unmount
    const r = await fetch(`${API}/posts?filter=${filter}`, { signal });
    if (!r.ok) throw new Error(`HTTP ${r.status}`);
    return (await r.json()) as Post[];
  },
});

const queryClient = useQueryClient();
const { mutate } = useMutation({
  mutationFn: (input: NewPost) => api.createPost(input),
  onSuccess: () => queryClient.invalidateQueries({ queryKey: qk.posts.all }), // rule 4
});
```

`invalidateQueries({ queryKey: ["posts"] })` matches **every** key that starts with `["posts"]` — that is why the hierarchy matters.

## Optimistic updates (`onMutate` + rollback)

The docs' "via the cache" pattern: cancel in-flight refetches → snapshot → write optimistically → return the snapshot → restore it in `onError` → `invalidateQueries` in `onSettled`.

```tsx
useMutation({
  mutationFn: updateTodo,
  onMutate: async (newTodo) => {
    await queryClient.cancelQueries({ queryKey: qk.posts.all });
    const previous = queryClient.getQueryData<Post[]>(qk.posts.all);
    queryClient.setQueryData<Post[]>(qk.posts.all, (old = []) => [...old, newTodo]);
    return { previous };                        // becomes the rollback context
  },
  onError: (_err, _newTodo, ctx) => queryClient.setQueryData(qk.posts.all, ctx?.previous),
  onSettled: () => queryClient.invalidateQueries({ queryKey: qk.posts.all }),
});
```

`[VERIFY]` recent 5.x docs show an extra trailing `context` argument on every callback (`onError: (err, vars, onMutateResult, context) => context.client.setQueryData(...)`). The `useQueryClient()` form above works on all of v5 — prefer it unless you have checked the installed version.

## Infinite / paginated lists + FlashList

```tsx
const { data, fetchNextPage, hasNextPage, isFetchingNextPage } = useInfiniteQuery({
  queryKey: qk.posts.all,
  queryFn: async ({ pageParam, signal }) => {
    const r = await fetch(`${API}/posts?cursor=${pageParam}`, { signal });
    return (await r.json()) as { data: Post[]; nextCursor: number | null };
  },
  initialPageParam: 0,                       // required in v5
  getNextPageParam: (lastPage) => lastPage.nextCursor ?? undefined,
});

<FlashList
  data={data?.pages.flatMap((p) => p.data) ?? []}
  keyExtractor={(p) => p.id}
  renderItem={({ item }) => <PostCard post={item} />}
  onEndReachedThreshold={0.5}
  onEndReached={() => { if (hasNextPage && !isFetchingNextPage) fetchNextPage(); }}
  ListFooterComponent={isFetchingNextPage ? <ActivityIndicator /> : null}
/>
```

`getNextPageParam` returning `undefined` (or `null`) is what sets `hasNextPage: false`. FlashList v2 no longer needs `estimatedItemSize` `[VERIFY]`.

## Refetch when a screen regains focus

`refetchOnWindowFocus` covers app foregrounding; **navigating back to a screen is a different event**. Expo Router re-exports `useFocusEffect` and `useIsFocused`:

```tsx
// hooks/use-refresh-on-focus.ts — skip the first call, it duplicates the mount fetch
const firstTime = useRef(true);
useFocusEffect(useCallback(() => {
  if (firstTime.current) { firstTime.current = false; return; }
  queryClient.refetchQueries({ queryKey, stale: true, type: "active" });
}, [queryClient, queryKey]));
```

To *pause* an off-screen query instead, pass `subscribed: useIsFocused()` to `useQuery`.

## AsyncStorage persistence (cache survives app restart)

```tsx
// app/_layout.tsx — PersistQueryClientProvider replaces QueryClientProvider
import AsyncStorage from "@react-native-async-storage/async-storage";
import { PersistQueryClientProvider } from "@tanstack/react-query-persist-client";
import { createAsyncStoragePersister } from "@tanstack/query-async-storage-persister";

// options: key (default "REACT_QUERY_OFFLINE_CACHE"), throttleTime (default 1000), serialize, deserialize, retry
export const persister = createAsyncStoragePersister({ storage: AsyncStorage });

const [client] = useState(() => new QueryClient({
  defaultOptions: { queries: { gcTime: 1000 * 60 * 60 * 24 } }, // ≥ maxAge, or entries are GC'd before restore
}));

<PersistQueryClientProvider
  client={client}
  persistOptions={{ persister, maxAge: 1000 * 60 * 60 * 24, buster: APP_BUILD_ID }}
>
  <Stack />
</PersistQueryClientProvider>
```

`buster` is a free cache invalidation lever: change the string (app version, schema version) and the whole persisted cache is discarded via `persister.removeClient()`. Limit *what* gets written with `persistOptions.dehydrateOptions.shouldDehydrateQuery: (query) => boolean` (default: successful queries only) `[VERIFY]`.

## ⚠️ Purge the persisted cache on sign-out — it holds personal data

`createAsyncStoragePersister` writes the **entire dehydrated cache** — profiles, orders, messages, anything a query returned — into AsyncStorage as **plaintext JSON**, under one key, with no expiry beyond `maxAge`. It survives sign-out and is readable by the next user of the device. Under GDPR that is personal data at rest with no lawful basis once the session ends.

```ts
// lib/auth.ts — every sign-out path must run this
export async function signOut() {
  await api.signOut();
  queryClient.clear();               // in-memory cache
  await persister.removeClient();    // persisted snapshot (Persister interface)
  await SecureStore.deleteItemAsync("session_token");
}
```

Corollary (already in `tanstack-query-rn.md`): **never** put tokens or credentials in the persisted cache — they belong in `expo-secure-store`. Persist non-sensitive read caches only, and treat `shouldDehydrateQuery` as an allowlist for anything regulated.

## Integration in dev-flow

- Installed at scaffold by `rn-bootstrap` (`stack.framework="expo-rn"`); the provider lands in `app/_layout.tsx`.
- `rn-add-screen` wires every screen that reads the network through `useQuery` / `useInfiniteQuery` — never `useState` + `useEffect` + `fetch`.
- `rn-module-add` supplies the `queryFn` transport (Supabase / Firebase / REST / tRPC); the query layer above is provider-agnostic.
- `rn-write-tests` mocks the `queryFn` and asserts UI, never the query result shape.
- The sign-out purge is a **release blocker** for any app storing user data — check it before `rn-eas-build-submit-update`.
