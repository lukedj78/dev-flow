---
name: rn-data-fetching
description: 'Use when fetching data from APIs in React Native: choosing between fetch+useEffect (didactic only) and TanStack Query (production default), wiring the QueryClient provider, building queries / mutations / optimistic updates / paginated and infinite lists / cache invalidation / refetch on focus, handling loading and error states, AsyncStorage persistence, offline-first behavior. Triggers on: "fetch posts from API", "infinite scroll", "optimistic mutation", "cache invalidation", "loading state". Not for: styling lists (rn-styling), backend setup (rn-backend, Wave 3 — provider-agnostic), GraphQL clients (out of scope).'
---

# rn-data-fetching — guardrail for data fetching in React Native + Expo

## The 5 rules (non-negotiable)

1. **TanStack Query is the default** for any data that comes from the network. `fetch + useEffect` is acceptable ONLY in didactic examples or for one-off bootstrap calls (e.g. reading a config at app start).
2. **One `QueryClient` per app, mounted at the root layout.** Never instantiate per-screen.
3. **Query keys are arrays**, hierarchical, with the most specific filter last: `["posts", "list", { filter }]`. NEVER stringly-typed keys.
4. **Every mutation invalidates the queries it affects**. Use `queryClient.invalidateQueries({ queryKey: [...] })` in `onSuccess`. Optimistic updates use `onMutate` + `onError` rollback.
5. **`staleTime` ≥ 60_000 ms is the default** to avoid refetch-on-focus storms. Tune per query based on freshness need.

## Quick decision tree

- "Should I use fetch or TanStack Query?" → `references/decision-tree.md`
- "How do I set up TanStack Query in a fresh Expo app?" → `references/tanstack-query-setup.md`
- "What's the right query key shape, the right cancel pattern, the right loading state?" → `references/patterns.md`
- "Show me a working query / mutation / infinite scroll example" → `references/examples/`
- "Why does my fetch race on unmount?" → `references/concepts.md`

## Common anti-patterns (NEVER do)

- ❌ `useEffect(() => { fetch(...).then(setData) }, [])` for production data — no retry, no dedup, no cancel.
- ❌ `useState<Data | null>(null)` + `useState<boolean>(false)` for loading — let TanStack Query own server state.
- ❌ `queryKey: "posts"` as a string — must be an array.
- ❌ Calling `setData` after the component unmounts — TanStack Query handles cancel automatically.
- ❌ Mutation that updates the server but does NOT `invalidateQueries` — UI shows stale data.
- ❌ Refetching on every navigation — set `staleTime` per query.

## Sources

- Course: codewithbeto.dev/rnCourse — lesson 7 "Fetching Data from an API" + lesson 8 "Rendering Lists and TypeScript" (free).
- Official: https://tanstack.com/query/v5/docs/framework/react/overview
- Official: https://tanstack.com/query/v5/docs/framework/react/guides/mutations
- Official: https://docs.expo.dev/develop/development-builds/use-development-builds/
