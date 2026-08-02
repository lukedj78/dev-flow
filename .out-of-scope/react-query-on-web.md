# Promoting TanStack Query on the web

**Decision**: it stays the **last rung** of the read ladder, deliberately
**Date**: 2026-08-02

## What it is
TanStack Query (`@tanstack/react-query`) as a general client-side data layer for the Next.js web apps, the way it is the default on mobile.

## Why it was tempting
It's excellent, it's already in the suite (it *is* the mobile default in `rn-data-fetching`), and it would make one pattern serve both stacks.

## Why not
On the web we have React Server Components. `data-fetching` walks four rungs — Server Component → URL `searchParams` → `Promise<T>` + `use()` + `<Suspense>` → Route Handler + TanStack Query — and each rung down gives up something real: SSR, streaming, request dedup, caching, parallelism. Reaching for a client data layer first is how a Next.js app quietly becomes a slower SPA.

So rung 4 is not a ranking of library quality. It's "the server can't do this for you": interval polling, refetch-on-focus, data mutated by a third party outside your app. For those, TanStack Query *is* the recommended choice at that rung (over SWR).

The asymmetry with mobile is intentional and worth stating plainly: React Native has no Server Components, so rungs 1–3 don't exist there and the same library is correctly the default.

## What would change our mind
Nothing about the library. Only a change in the platform — if the RSC read path stopped covering the common cases, the ladder itself would need rewriting, not just its last rung.
