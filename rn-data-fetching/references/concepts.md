> Sources: tanstack.com/query, reactnative.dev networking, codewithbeto.dev lessons 7-8 (free).

# Concepts — data fetching in React Native

## Why not just `fetch + useEffect`

The naive pattern looks like this:

```tsx
const [data, setData] = useState<Post[] | null>(null);
const [loading, setLoading] = useState(true);
const [error, setError] = useState<Error | null>(null);

useEffect(() => {
  setLoading(true);
  fetch("/api/posts")
    .then((r) => r.json())
    .then(setData)
    .catch(setError)
    .finally(() => setLoading(false));
}, []);
```

It has six well-known bugs:

1. **No cancel on unmount** — if the user navigates away mid-request, `setData` fires on an unmounted component (React warns; in older versions it leaked memory).
2. **No retry** on transient network errors.
3. **No dedup** — two components mounting in parallel each fire a request.
4. **No cache** — re-mount = re-fetch from scratch.
5. **No refetch-on-focus** — opening the app from background shows stale data.
6. **Stale closures** — if `useEffect` depends on a value that changes, you race against the previous fetch.

TanStack Query fixes all six in one library.

## TanStack Query mental model

- **Queries** are *server state*: data that lives outside React. They have a unique `queryKey` (an array). The library tracks fetch state (`idle`/`loading`/`success`/`error`/`refetching`), holds the latest result in a cache, and refetches based on `staleTime` / focus / network reconnect.
- **Mutations** are *user actions* that change server state (POST/PUT/PATCH/DELETE). They don't have a key. They expose `mutate(input)` and lifecycle callbacks (`onMutate`/`onSuccess`/`onError`/`onSettled`) for optimistic updates and cache invalidation.
- **Query keys** are like cache keys: identical key = identical data. Two components with the same key share the cache and the in-flight request.

## Query key conventions

Hierarchical arrays from broad to specific:

```ts
["posts"]                              // all post-related queries (broadest)
["posts", "list"]                      // the list view
["posts", "list", { status: "open" }]  // filtered list
["posts", "detail", id]                // one post
["users", "profile", userId]
```

Why hierarchical: `invalidateQueries({ queryKey: ["posts"] })` invalidates EVERYTHING under that prefix (lists + details + filters) in one call.

## staleTime vs cacheTime (gcTime in v5)

- `staleTime` (default `0`): for how long is data considered fresh. Fresh = no refetch on focus/mount.
- `gcTime` (default `5 * 60_000`): for how long do we keep unused data in memory before garbage collecting.

Rule of thumb:
- Read-mostly data (profile, settings) → `staleTime: 5 * 60_000` (5 min).
- Frequently-changing (feed, notifications) → `staleTime: 30_000` (30 sec).
- Real-time-ish (chat, presence) → `staleTime: 0` + websocket/realtime (out of scope here).

## Cancel-on-unmount

TanStack Query automatically aborts the underlying fetch when a query observer (a `useQuery` hook) unmounts and no other observer holds the same key. **You do not need to write `AbortController` logic manually** as long as you pass `signal` to `fetch`:

```ts
useQuery({
  queryKey: ["posts"],
  queryFn: ({ signal }) => fetch("/api/posts", { signal }).then((r) => r.json()),
});
```

## Loading and error states

TanStack Query exposes status fields:

- `isLoading`: first load, no data yet.
- `isFetching`: any refetch (including background revalidation).
- `isError` + `error`: terminal error after retries exhausted.
- `isSuccess` + `data`: have data.

UI pattern:

```tsx
const { data, isLoading, isError, error, refetch } = useQuery({ ... });

if (isLoading) return <Loading />;
if (isError) return <ErrorView error={error} onRetry={refetch} />;
return <List data={data!} />;
```

For background refetches, use `isFetching` to show a small spinner WITHOUT replacing the list.

## Refetch on focus (mobile-specific)

By default TanStack Query refetches when the window regains focus (web). On RN, hook `focusManager` to `AppState` so it does the same on app foreground:

```ts
import { AppState } from "react-native";
import { focusManager } from "@tanstack/react-query";

AppState.addEventListener("change", (state) => {
  focusManager.setFocused(state === "active");
});
```

This is done once in the root layout — see `tanstack-query-rn.md`.

## Sources

- https://tanstack.com/query/v5/docs/framework/react/overview
- https://tanstack.com/query/v5/docs/framework/react/guides/queries
- https://tanstack.com/query/v5/docs/framework/react/guides/mutations
- https://tanstack.com/query/v5/docs/framework/react/react-native
