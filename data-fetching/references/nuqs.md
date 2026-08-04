# URL state — nuqs (Next.js 16 App Router)

The **how**, not just "use nuqs". Doc-grounded against [nuqs.dev](https://nuqs.dev) — verified **nuqs@2.9.4** (2026-08). Canonical library for the **URL-state rung** in both `data-fetching` (rung 2) and `state-discipline` (rung 2). `[VERIFY]` every identifier against the installed version; this surface moves (`throttleMs` was **deprecated in 2.5.0** in favour of `limitUrlUpdates`, and the generic `nuqs/adapters/react-router` import is **removed in 3.0.0**).

**The division of labour**: the page stays an **async Server Component** reading the `searchParams` prop. nuqs owns the **client write side** — a typed, throttled replacement for hand-rolled `router.replace(...)`. It is not a data-fetching library.

## Install + adapter (mandatory)

```bash
pnpm add nuqs
```

Supported: `next@>=14.2.0` (app & pages routers), React SPA (`react@^18.3 || ^19`), Remix, React Router v6/v7/v8, TanStack Router. Next 16 + React 19 is comfortably inside the supported range.

```tsx
// app/layout.tsx — App Router adapter. Import path is exact.
import { NuqsAdapter } from 'nuqs/adapters/next/app';
import type { ReactNode } from 'react';

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html>
      <body>
        <NuqsAdapter>{children}</NuqsAdapter>
      </body>
    </html>
  );
}
```

Other adapters (same `NuqsAdapter` name, different path): `nuqs/adapters/next/pages`, `nuqs/adapters/next` (unified), `nuqs/adapters/react` (Vite SPA), `nuqs/adapters/remix`, `nuqs/adapters/react-router/v6|v7|v8`, `nuqs/adapters/tanstack-router`. Tests use `NuqsTestingAdapter` (see `nuqs.dev/docs/testing`).

> ⚠️ **The two gotchas that cost the most time.**
> 1. **No adapter → every hook throws.** `<NuqsAdapter>` is not optional and not auto-installed; wire it in the root layout the moment you add the dep.
> 2. **`shallow: true` is the default, and it does NOT re-render Server Components.** A filter that updates the URL but never refreshes the list is this. Any param the server reads must be `shallow: false`. Corollary: a Client Component using `useQueryState` inside a Server page must sit under a `<Suspense>` boundary or Next throws *"Missing Suspense boundary with useSearchParams"* — keep `page.tsx` a Server Component and put the client bits in their own file. `[VERIFY]` the Suspense requirement against Next 16.

## `useQueryState` — one param

```tsx
'use client';
import { useQueryState, parseAsInteger } from 'nuqs';

export function Pagination() {
  const [page, setPage] = useQueryState('page', parseAsInteger.withDefault(1)); // number, never null
  setPage(3);                 // value
  setPage((p) => p + 1);      // updater fn
  setPage(null);              // removes the key from the URL
}
```

- `useQueryState('name')` → `string | null` (no parser = plain string, nullable); `useQueryState('count', parseAsInteger)` → `number | null`.
- `.withDefault(x)` → non-nullable type **and** the fallback when the param is absent.

## `useQueryStates` — several params, one URL update

Use this whenever two or more params change together (filters + reset-to-page-1). Updates in the same event-loop tick are batched into a **single** history entry / server round-trip.

```tsx
'use client';
import { useQueryStates, parseAsInteger, parseAsStringLiteral } from 'nuqs';

const sortValues = ['asc', 'desc'] as const;

export function Filters() {
  const [{ page, sort }, setFilters] = useQueryStates(
    {
      page: parseAsInteger.withDefault(1),
      sort: parseAsStringLiteral(sortValues).withDefault('asc'),
    },
    { shallow: false, history: 'replace' },
  );

  // ONE URL update, one server round-trip:
  setFilters({ sort: 'desc', page: 1 });
  setFilters((prev) => ({ page: prev.page + 1 })); // updater form
  setFilters(null);                                // clears all keys in this object
}
```

`urlKeys` remaps long variable names to short URL keys: `useQueryStates({ latitude, longitude }, { urlKeys: { latitude: 'lat', longitude: 'lng' } })` → `?lat=…&lng=…`.

## Parsers

| Parser | Notes |
|---|---|
| `parseAsString` | no validation |
| `parseAsInteger` / `parseAsFloat` | base-10 int / float |
| `parseAsHex` / `parseAsIndex` | hex ints / 1-based↔0-based pagination offset |
| `parseAsBoolean` | |
| `parseAsStringLiteral(['asc','desc'] as const)` | union of string literals — **prefer this for tabs/sort** |
| `parseAsNumberLiteral([1,2,3])` | union of number literals |
| `parseAsStringEnum<Direction>(Object.values(Direction))` | TypeScript `enum`s |
| `parseAsArrayOf(parseAsInteger, ';')` | array, custom separator (default `,`) |
| `parseAsNativeArrayOf(parseAsInteger)` | repeated keys `?p=1&p=2` (nuqs ≥ 2.7.0) |
| `parseAsIsoDate` / `parseAsIsoDateTime` / `parseAsTimestamp` | date-only ISO (UTC midnight) / full ISO 8601 / ms epoch |
| `parseAsJson(schema)` | validated with a Standard Schema (Zod, Valibot, ArkType) or a sync validation fn |

All parsers chain `.withDefault(value)` and `.withOptions({ … })`. Import them from **`nuqs`** in Client Components and from **`nuqs/server`** in shared/server modules (no client runtime pulled in).

```ts
// custom parser
import { createParser } from 'nuqs';

const dateParser = createParser({
  parse: (value: string) => new Date(value.slice(0, 10)),
  serialize: (date: Date) => date.toISOString().slice(0, 10),
  eq: (a: Date, b: Date) => a.getTime() === b.getTime(), // needed for clearOnDefault on non-primitives
});
```

`createMultiParser({ parse: (values: string[]) => …, serialize: (v) => [..] })` handles repeated URL keys.

## Options — and when each one matters

Set them per-parser (`parseAsX.withOptions({…})`), per-hook (2nd/3rd arg), per-call (`setX(v, {…})`, wins), or app-wide on the adapter (`<NuqsAdapter defaultOptions={{…}}>`, nuqs ≥ 2.5.0).

- **`shallow`** (default `true`) — `true` = client-only, the server never hears about it. **`false` = notify the server**, so the App Router re-runs the page and Server Components re-render with the new `searchParams`. **In App Router, any param that drives server data must be `shallow: false`.** Keep `true` only for pure client UI (an open panel, a client-side-only view toggle).
- **`limitUrlUpdates`** — rate-limits **URL writes only**; the hook's state updates instantly so the input stays responsive. `throttle(ms)` (default behaviour, ~50ms / 120ms Safari; values < 50ms ignored; `+Infinity` disables URL writes) vs `debounce(ms)` — **debounce is the right one for a search box**, throttle for sliders/low-frequency. `defaultRateLimit` resets to default. ⚠️ The older **`throttleMs` is deprecated since 2.5.0** — migrate `{ throttleMs: 100 }` → `{ limitUrlUpdates: throttle(100) }`.
- **`history`** (default `'replace'`) — `'replace'` squashes into the current entry (right for filters/search: Back leaves the page). `'push'` adds an entry so Back steps through states — only for navigation-like state (tabs, modals). Never set `'push'` globally.
- **`clearOnDefault`** (default `true` since v2) — drops the key from the URL when the value equals the default, keeping URLs clean. Set `false` when the param must stay visible/explicit (e.g. a shared link that must pin `?sort=asc`).
- **`startTransition`** — pass React's `startTransition` so `isPending` stays true while the Server Component re-renders. Only meaningful with `shallow: false`.
- **`scroll`** (default `false`) — `true` scrolls to top on update; useful when paginating a long list.

```tsx
'use client';
import { useTransition } from 'react';
import { useQueryState, parseAsString, debounce } from 'nuqs';

export function SearchBox() {
  const [isLoading, startTransition] = useTransition();
  const [q, setQ] = useQueryState(
    'q',
    parseAsString.withDefault('').withOptions({ shallow: false, startTransition }),
  );

  return (
    <>
      <input value={q} onChange={(e) => setQ(e.target.value, {
        limitUrlUpdates: e.target.value === '' ? undefined : debounce(500),
      })} />
      {isLoading && <Spinner />}
    </>
  );
}
```

## Server side — same parsers, no prop drilling

Define the parsers **once** in a shared module imported by both sides. That single definition is the whole type-safety payoff: rename a key or change a type and both server and client fail to compile together.

```ts
// app/(app)/cases/search-params.ts   ← imported by BOTH server and client
import {
  createLoader, createSearchParamsCache, createSerializer,
  parseAsInteger, parseAsString, parseAsStringLiteral,
} from 'nuqs/server';

export const caseSearchParams = {
  q: parseAsString.withDefault(''),
  page: parseAsInteger.withDefault(1),
  sort: parseAsStringLiteral(['asc', 'desc'] as const).withDefault('asc'),
};

export const loadCaseSearchParams = createLoader(caseSearchParams);
export const caseSearchParamsCache = createSearchParamsCache(caseSearchParams);
export const serializeCaseSearchParams = createSerializer(caseSearchParams); // build <Link href={…}>
```

```tsx
// app/(app)/cases/page.tsx — stays a Server Component
import type { SearchParams } from 'nuqs/server';
import { loadCaseSearchParams } from './search-params';
import { listCases } from '@/lib/services/case.service';

export default async function CasesPage({
  searchParams,
}: {
  searchParams: Promise<SearchParams>; // async in Next 15+/16
}) {
  const { q, page, sort } = await loadCaseSearchParams(searchParams);
  const cases = await listCases({ q, page, sort });
  return <CasesTable cases={cases} />; // <Filters /> is the only "use client" leaf
}
```

`createSearchParamsCache` is the alternative when a **deeply nested** Server Component needs the params without prop drilling: `await caseSearchParamsCache.parse(searchParams)` in the page, then `caseSearchParamsCache.get('page')` / `.all()` anywhere below. Caveats from the docs: the cache is valid **only for the current page render**, works **only in Server Components**, is **App Router only**, and `.parse()` **must** run before any `.get()`.

## How this fits the dev-flow ladder

- **Server reads, client writes.** `data-fetching` rung 2 (and `state-discipline` rung 2): the page keeps `async function Page({ searchParams })` and `await`s the read; the `"use client"` leaf only *writes* the param via `useQueryState`/`useQueryStates` with `shallow: false`. You get SSR, streaming, caching, a shareable/bookmarkable URL and a working Back button for free.
- **You never install a data library for this.** No `useEffect`, no `useQuery`, no Server Action read. If you find yourself refetching in the client after a nuqs update, you forgot `shallow: false`.
- **Don't use nuqs when the state isn't shareable.** Dialog open/closed, hover, an in-flight uncommitted input, a "did the user dismiss this toast" flag — that's `useState` per `state-discipline`. Putting it in the URL makes it bookmarkable, back-button-visible, and shows up in analytics; that's a product decision, not a default.
- **Don't use nuqs to hold server data.** It stores the *query*, never the *result*. The result belongs to the Server Component (`data-fetching` rung 1).
- **Rung 4 still exists.** Polling / focus-refetch / third-party mutations remain TanStack Query territory; nuqs and TanStack Query coexist fine (URL param → query key).

## Sources

- Installation: <https://nuqs.dev/docs/installation> · Adapters: <https://nuqs.dev/docs/adapters>
- Basic usage: <https://nuqs.dev/docs/basic-usage> · `useQueryStates`: <https://nuqs.dev/docs/batching>
- Parsers: <https://nuqs.dev/docs/parsers/built-in> · Custom: <https://nuqs.dev/docs/parsers/making-your-own>
- Options: <https://nuqs.dev/docs/options> · Server-side: <https://nuqs.dev/docs/server-side> · Utilities: <https://nuqs.dev/docs/utilities>
- Troubleshooting: <https://nuqs.dev/docs/troubleshooting> · Testing: <https://nuqs.dev/docs/testing>
