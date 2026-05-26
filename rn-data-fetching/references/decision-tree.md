> Sources: tanstack.com/query v5 docs, internal opinion.

# Decision tree — data fetching

## Q1: Should I use TanStack Query or just fetch?

```
Is the data:
├── from a network request → TanStack Query. Always.
├── computed locally (e.g. derived state) → useMemo, no library.
├── stored locally (AsyncStorage / SecureStore) → custom hook, no library.
└── real-time push (websocket / Supabase realtime) → TanStack Query +
                                                     setQueryData on incoming events.
```

`fetch + useEffect` is ONLY for: an example in a tutorial, or a one-off bootstrap call before the QueryClient mounts (rare).

## Q2: Query or mutation?

```
Does this call READ data (GET)?
├── YES → useQuery
└── NO (POST/PUT/PATCH/DELETE) → useMutation
```

A query whose result depends on user input (e.g. typed search) is still a query, with the input in the key:
`queryKey: queryKeys.posts.search(debouncedQuery)`.

## Q3: How long should `staleTime` be?

```
How fast does the data change in reality?
├── Almost never (settings, profile)        → staleTime: 5 * 60_000  (5 min)
├── Often (feed, list)                       → staleTime: 30_000      (30 sec)
├── Constantly (chat, notifications counter) → staleTime: 0 + realtime channel
└── User-driven only (forms, drafts)         → staleTime: Infinity, manual invalidation
```

`refetchInterval` is rarely the right answer in mobile — battery cost. Prefer realtime or pull-to-refresh.

## Q4: Optimistic update or wait for server?

```
Is the action low-risk and frequent (likes, votes, toggles)?
├── YES → optimistic. Pattern in patterns.md.
└── NO  → wait for server, show spinner, then invalidate.
```

Optimistic is great UX for likes / follows / read state. Bad for irreversible actions (deletes, payments).

## Q5: Single list or paginated / infinite?

```
Will the list realistically grow beyond 50-100 items?
├── NO  → useQuery + render all at once
└── YES → useInfiniteQuery + FlashList with onEndReached
```

## Q6: Where do I show the loading state?

```
First load (no data yet):
├── isLoading → blocking skeleton or spinner.

Refetch (have stale data):
├── isFetching → tiny inline spinner. NEVER replace the list.

Mutation in progress:
├── mutation.isPending → disable the button + show spinner inline.
```

Never render `null` or `undefined` to the user — always a skeleton or a placeholder.

## Q7: Error handling

```
Error type?
├── Network (offline / timeout)     → retry automatically (TanStack does it), then show "no connection".
├── 4xx user error (validation)     → don't retry. Show the field-level error.
├── 401/403 auth                    → redirect to /sign-in (clear cache).
├── 5xx server                      → retry once or twice, then show "something went wrong, try again".
```

Custom retry logic per query:

```ts
useQuery({
  queryKey: [...],
  queryFn: ...,
  retry: (failureCount, error) => {
    if (error instanceof ApiError && error.status >= 400 && error.status < 500) return false;
    return failureCount < 3;
  },
});
```
