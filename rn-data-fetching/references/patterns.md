> Sources: tanstack.com/query v5 docs, internal opinion.

# Patterns and anti-patterns — data fetching

## Query key factories

Avoid scattering string-array literals across the codebase. Centralize:

```ts
// lib/query-keys.ts
export const queryKeys = {
  posts: {
    all: ["posts"] as const,
    list: (filter?: { status?: string }) => ["posts", "list", filter ?? {}] as const,
    detail: (id: string) => ["posts", "detail", id] as const,
  },
  users: {
    all: ["users"] as const,
    profile: (id: string) => ["users", "profile", id] as const,
  },
};

// usage
useQuery({ queryKey: queryKeys.posts.list({ status: "open" }), queryFn: ... });
queryClient.invalidateQueries({ queryKey: queryKeys.posts.all });
```

Pros: typo-proof, one place to grep, easy refactor.

## API client

A thin fetch wrapper that throws on non-2xx:

```ts
// lib/api.ts
const BASE_URL = process.env.EXPO_PUBLIC_API_URL!;

export async function api<T>(path: string, init?: RequestInit & { signal?: AbortSignal }): Promise<T> {
  const r = await fetch(`${BASE_URL}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...init?.headers,
    },
  });
  if (!r.ok) {
    const body = await r.text();
    throw new ApiError(r.status, body);
  }
  return r.json() as Promise<T>;
}

export class ApiError extends Error {
  constructor(public status: number, public body: string) {
    super(`API ${status}: ${body}`);
  }
}
```

Then queries become:

```ts
useQuery({
  queryKey: queryKeys.posts.list(),
  queryFn: ({ signal }) => api<Post[]>("/posts", { signal }),
});
```

## Mutations — always invalidate

```ts
const queryClient = useQueryClient();

const create = useMutation({
  mutationFn: (input: NewPost) => api<Post>("/posts", { method: "POST", body: JSON.stringify(input) }),
  onSuccess: () => {
    // Invalidate the list — UI refetches automatically
    queryClient.invalidateQueries({ queryKey: queryKeys.posts.all });
  },
});

// In the component
create.mutate({ title: "…" });
```

For mutations with sub-resources (e.g. liking a post = `/posts/:id/likes`), invalidate both the list and the detail:

```ts
queryClient.invalidateQueries({ queryKey: queryKeys.posts.detail(postId) });
queryClient.invalidateQueries({ queryKey: queryKeys.posts.list() });
```

## Optimistic updates

```ts
const like = useMutation({
  mutationFn: (postId: string) => api(`/posts/${postId}/likes`, { method: "POST" }),
  onMutate: async (postId) => {
    // Cancel any in-flight refetches so they don't overwrite our optimistic data
    await queryClient.cancelQueries({ queryKey: queryKeys.posts.detail(postId) });

    // Snapshot the previous value
    const previous = queryClient.getQueryData<Post>(queryKeys.posts.detail(postId));

    // Optimistically update
    queryClient.setQueryData<Post>(queryKeys.posts.detail(postId), (old) =>
      old ? { ...old, likeCount: old.likeCount + 1, likedByMe: true } : old,
    );

    return { previous };
  },
  onError: (_err, postId, ctx) => {
    // Rollback
    if (ctx?.previous) {
      queryClient.setQueryData(queryKeys.posts.detail(postId), ctx.previous);
    }
  },
  onSettled: (_data, _err, postId) => {
    // Refetch to be sure
    queryClient.invalidateQueries({ queryKey: queryKeys.posts.detail(postId) });
  },
});
```

## Infinite lists

```ts
const { data, fetchNextPage, hasNextPage, isFetchingNextPage } = useInfiniteQuery({
  queryKey: queryKeys.posts.list(),
  queryFn: ({ pageParam = 0, signal }) =>
    api<{ items: Post[]; nextCursor: number | null }>(`/posts?cursor=${pageParam}`, { signal }),
  initialPageParam: 0,
  getNextPageParam: (lastPage) => lastPage.nextCursor,
});

// Flatten pages for FlashList
const items = data?.pages.flatMap((p) => p.items) ?? [];

<FlashList
  data={items}
  renderItem={({ item }) => <Row item={item} />}
  estimatedItemSize={64}
  onEndReached={() => hasNextPage && !isFetchingNextPage && fetchNextPage()}
  onEndReachedThreshold={0.5}
/>
```

## Pull-to-refresh

```ts
const { data, refetch, isRefetching } = useQuery({ ... });

<FlashList
  data={data}
  refreshing={isRefetching}
  onRefresh={refetch}
  // ...
/>
```

## Dependent queries

```ts
const userQuery = useQuery({ queryKey: queryKeys.users.profile(userId), queryFn: ... });
const postsQuery = useQuery({
  queryKey: queryKeys.posts.list({ authorId: userQuery.data?.id }),
  queryFn: ...,
  enabled: !!userQuery.data, // don't fire until userQuery has data
});
```

## DON'T

- ❌ `useState + fetch + useEffect` for any data that benefits from cache/retry.
- ❌ Forgetting `signal` in `queryFn` — cancel-on-unmount is broken.
- ❌ Updating cache manually with `setQueryData` and skipping `invalidateQueries` — risks divergence from server.
- ❌ Triggering mutations from `useEffect` — mutations are user actions, run them in callbacks.
- ❌ Reading `data!` without checking `isSuccess` — TS will complain rightly.
- ❌ Building a query key string by concatenation: `queryKey: ["posts-" + status]` — use an array tuple.
