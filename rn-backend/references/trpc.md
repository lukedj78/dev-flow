> Sources: https://trpc.io/docs, https://trpc.io/docs/client/react/
> Verified **2026-08-26** against `@trpc/{client,server,react-query}@11.18.0` — v11 is current. `[VERIFY]` on a major.

# tRPC — end-to-end typed backend

Use when: your backend IS Node (Express / Fastify / Next.js API routes / Hono), you want types to flow automatically server → client without code generation, and you're OK with the Node lock-in.

## Why tRPC over plain REST

- **Types**: change a procedure on the server, the client gets a TypeScript error immediately.
- **No schema file**: types are inferred from your code. No OpenAPI, no GraphQL schema, no `gen types`.
- **TanStack Query integration**: every procedure becomes a `useQuery` / `useMutation` automatically.

## Tradeoffs

- Server must be Node/TypeScript. (Server in Python? tRPC is not for you.)
- HTTP boundary is JSON; tRPC doesn't replace OpenAPI if you have external consumers.
- Custom REST is simpler for very small APIs (< 5 endpoints).

## 1. Server (assumed already set up — out of scope of this skill)

```ts
// server/router.ts
import { initTRPC } from "@trpc/server";
import { z } from "zod";

const t = initTRPC.context<{ userId: string | null }>().create();

const isAuthed = t.middleware(({ ctx, next }) => {
  if (!ctx.userId) throw new TRPCError({ code: "UNAUTHORIZED" });
  return next({ ctx: { userId: ctx.userId } });
});

const protectedProcedure = t.procedure.use(isAuthed);

export const appRouter = t.router({
  posts: t.router({
    list: protectedProcedure.query(({ ctx }) => db.posts.findMany({ where: { authorId: ctx.userId } })),
    create: protectedProcedure
      .input(z.object({ title: z.string(), body: z.string() }))
      .mutation(({ ctx, input }) => db.posts.create({ data: { ...input, authorId: ctx.userId } })),
  }),
});

export type AppRouter = typeof appRouter;
```

## 2. Client install (RN side)

```bash
npx expo install @trpc/client @trpc/react-query @trpc/server superjson -- --legacy-peer-deps
```

(`superjson` lets you ship `Date`, `Map`, `Set`, `BigInt` across the wire without manual serialization.)

## 3. `lib/trpc.ts`

```ts
import { createTRPCReact, httpBatchLink } from "@trpc/react-query";
import type { AppRouter } from "../../server/router"; // path to your server router types
import { useAuthStore } from "@/store/auth";

export const trpc = createTRPCReact<AppRouter>();

export function makeTrpcClient() {
  return trpc.createClient({
    links: [
      httpBatchLink({
        url: `${process.env.EXPO_PUBLIC_API_URL}/trpc`,
        headers() {
          const token = useAuthStore.getState().accessToken;
          return token ? { Authorization: `Bearer ${token}` } : {};
        },
      }),
    ],
  });
}
```

## 4. Root layout — providers

```tsx
// app/_layout.tsx
import { useState } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { trpc, makeTrpcClient } from "@/lib/trpc";
import { Stack } from "expo-router";
import "../global.css";

export default function RootLayout() {
  const [queryClient] = useState(() => new QueryClient());
  const [trpcClient] = useState(() => makeTrpcClient());

  return (
    <trpc.Provider client={trpcClient} queryClient={queryClient}>
      <QueryClientProvider client={queryClient}>
        <Stack />
      </QueryClientProvider>
    </trpc.Provider>
  );
}
```

## 5. Use a query

```tsx
// app/posts/index.tsx
import { trpc } from "@/lib/trpc";

export default function PostsScreen() {
  const { data, isLoading } = trpc.posts.list.useQuery();
  // data is fully typed!
  // ...
}
```

## 6. Use a mutation

```tsx
const create = trpc.posts.create.useMutation({
  onSuccess: () => trpc.useUtils().posts.list.invalidate(),
});

create.mutate({ title: "Hi", body: "..." }); // input is typed
```

## 7. Auth handling

Same architecture as `patterns.md`: Zustand store holds the access token; the `headers()` function in `httpBatchLink` reads it on every request. Refresh-on-401 needs a custom link:

```ts
import { TRPCClientError, TRPCLink } from "@trpc/client";
import { observable } from "@trpc/server/observable";

const refreshLink: TRPCLink<AppRouter> = () => ({ op, next }) => observable((observer) => {
  // ...wraps next(op), catches 401, refreshes, retries once.
  // Pattern: https://trpc.io/docs/client/links  (⚠️ the old `/links/customLink` URL 404s — 2026-08-26)
});
```

For brevity we omit the full link here. The complete recipe is in the tRPC docs under **Client → Links** (<https://trpc.io/docs/client/links>); the per-link pages live one level down, e.g. `/links/httpBatchLink`.

## 8. SSE / subscriptions (real-time)

If your tRPC server supports subscriptions:

```ts
import { wsLink, createWSClient } from "@trpc/client";

const wsClient = createWSClient({ url: `${process.env.EXPO_PUBLIC_WS_URL}/trpc` });

const trpcClient = trpc.createClient({
  links: [
    splitLink({
      condition: (op) => op.type === "subscription",
      true: wsLink({ client: wsClient }),
      false: httpBatchLink({ /* ... */ }),
    }),
  ],
});
```

## Gotchas

- **Path import**: client imports `import type { AppRouter } from "../../server/router"`. In a monorepo, set up TypeScript paths. In a polyrepo, publish the type as a private package.
- **superjson**: required for non-primitive types. Configure BOTH server and client with the same transformer.
- **Bundle size**: tRPC ships ~20kb gzipped on the client. Acceptable.
- **Cold start**: the first request opens a connection — slight delay. Subsequent calls are batched.
