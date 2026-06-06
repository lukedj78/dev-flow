# Anti-pattern catalog — `data-fetching`

Six red ❌ → green ✅ pairs. Each is verified against Next.js 16 App Router docs. Sources cited inline.

---

## 1. Reading data via Server Action in `useEffect`

❌ **Red — sequential POST queue, no SSR, no streaming, no cache, double-fetch in dev Strict Mode:**

```tsx
"use client";
import { useEffect, useState } from "react";
import { getCases } from "@/lib/actions/cases.actions"; // "use server"

export default function CasesPage() {
  const [cases, setCases] = useState<Case[]>([]);
  useEffect(() => {
    getCases().then(setCases);
  }, []);
  return <CasesTable cases={cases} />;
}
```

✅ **Green — async Server Component, fetch on the server, stream HTML:**

```tsx
// app/(app)/cases/page.tsx
import { listCases } from "@/lib/services/case.service";

export default async function CasesPage() {
  const cases = await listCases();
  return <CasesTable cases={cases} />;
}
```

> *"Server Functions are designed for server-side **mutations**, and the client currently dispatches and awaits them **one at a time**. […] If you need parallel data fetching, use data fetching in Server Components."* — Next.js docs `mutating-data.mdx`

**No `useEffect` — ever.** Even the rare "fire a mutation on mount" case (e.g., a view counter that calls a Server Action when the page loads) does not use `useEffect` here. Per the `state-discipline` skill, that's `useMountEffect` — the project's escape-hatch helper:

```tsx
"use client";
import { useMountEffect } from "@/lib/hooks/use-mount-effect";
import { incrementViews } from "@/lib/actions/views.actions";

export function ViewCounter() {
  useMountEffect(() => { incrementViews(); });
  return null;
}
```

Even then, ask first: does this need to run on the client at all? A view increment usually runs inside the page Server Component (no client component, no hook). Reach for `useMountEffect` only when you genuinely need a browser-side trigger.

---

## 2. Filter / tab / range state in `useState`, refetched via Server Action

❌ **Red — page becomes a Client Component to host filter state; every chip click hits a queued POST:**

```tsx
"use client";
import { useEffect, useState } from "react";
import { getCases } from "@/lib/actions/cases.actions";

export default function CasesPage() {
  const [status, setStatus] = useState<"open" | "closed">("open");
  const [cases, setCases] = useState<Case[]>([]);
  useEffect(() => {
    getCases({ status }).then(setCases);
  }, [status]);
  return /* filters + table */;
}
```

✅ **Green — filter state lives in the URL `searchParams`; Server Component re-renders with fresh data; URL is shareable; back button works:**

```tsx
// app/(app)/cases/page.tsx — Server Component
import { listCases } from "@/lib/services/case.service";
import { CasesFilters } from "./_components/cases-filters";

export default async function CasesPage({
  searchParams,
}: {
  searchParams: Promise<{ status?: string }>;
}) {
  const { status = "open" } = await searchParams;
  const cases = await listCases({ status });
  return (
    <>
      <CasesFilters value={status} />
      <CasesTable cases={cases} />
    </>
  );
}
```

```tsx
// _components/cases-filters.tsx — small Client Component, pushes to URL
"use client";
import { usePathname, useRouter, useSearchParams } from "next/navigation";

export function CasesFilters({ value }: { value: string }) {
  const router = useRouter();
  const pathname = usePathname();
  const sp = useSearchParams();
  const set = (status: string) => {
    const next = new URLSearchParams(sp);
    next.set("status", status);
    router.replace(`${pathname}?${next}`, { scroll: false });
  };
  return /* chips that call set(...) */;
}
```

> Server Components receive `searchParams` as an async prop in Next.js 16; changing the URL re-runs the Server Component on the server. — Next.js docs `fetching-data.mdx`

---

## 3. Manually re-running a read after a mutation

❌ **Red — reach for `setState` after every mutation, ship list-management code to the client:**

```tsx
"use client";
import { listCases, deleteCase } from "@/lib/actions/cases.actions";

export function CasesList() {
  const [cases, setCases] = useState<Case[]>([]);
  useEffect(() => { listCases().then(setCases); }, []);

  async function handleDelete(id: string) {
    await deleteCase(id);
    const fresh = await listCases(); // 2nd POST, sequential, no cache
    setCases(fresh);
  }
  /* … */
}
```

✅ **Green — mutate, call `revalidatePath` / `revalidateTag` / `refresh` inside the action; the Server Component re-renders with fresh data:**

```ts
// lib/actions/cases.actions.ts
"use server";
import { revalidatePath } from "next/cache";
import { requireOrgPermission } from "@/lib/auth";
import { deleteCase as deleteCaseService } from "@/lib/services/case.service";

export async function deleteCaseAction(id: string) {
  await requireOrgPermission("org:cases:delete");
  await deleteCaseService(id);
  revalidatePath("/cases");
}
```

```tsx
// _components/delete-case-button.tsx
"use client";
import { useTransition } from "react";
import { deleteCaseAction } from "@/lib/actions/cases.actions";

export function DeleteCaseButton({ id }: { id: string }) {
  const [pending, start] = useTransition();
  return (
    <button disabled={pending} onClick={() => start(() => deleteCaseAction(id))}>
      {pending ? "Deleting…" : "Delete"}
    </button>
  );
}
```

> *"This ensures the UI displays the latest data after the mutation completes."* — Next.js docs `mutating-data.mdx`

**Three variants — pick the narrowest:**

- `revalidatePath('/cases')` — invalidate by route segment.
- `revalidateTag('cases')` — invalidate by tag (when a service uses `fetch(..., { next: { tags: ['cases'] } })` or React's `cache()` with tags).
- `refresh()` from `next/cache` — refresh the client router cache for the current route. Useful when the mutation happens on the same page.

---

## 4. `"use server"` file containing read-only `getX` / `listX` / `findX`

❌ **Red — Server Action whose only job is to `SELECT`. Invites `useEffect`-driven reads:**

```ts
// lib/actions/cases.actions.ts
"use server";
import { db } from "@/lib/db";
import { cases } from "@/lib/db/schema";

export async function getCases() {
  return db.select().from(cases);
}
```

✅ **Green — read logic lives in `lib/services/`, called directly from Server Components. Actions wrap services for mutations only:**

```ts
// lib/services/case.service.ts
import { db } from "@/lib/db";
import { cases } from "@/lib/db/schema";
import { requireOrgPermission } from "@/lib/auth";

export async function listCases(filters: CaseFilters = {}) {
  await requireOrgPermission("org:cases:read");
  return db.select().from(cases).where(/* … */);
}
```

```tsx
// app/(app)/cases/page.tsx
import { listCases } from "@/lib/services/case.service";

export default async function Page() {
  const cases = await listCases();
  return <CasesTable cases={cases} />;
}
```

Service stays the single source of truth. Mutation actions in `lib/actions/` import the service for the write side. No duplication, clear responsibilities.

---

## 5. Promise-awaited then handed to a Client Component, blocking streaming

❌ **Red — `await` in parent forces the whole subtree to wait before any HTML streams:**

```tsx
import { listCases } from "@/lib/services/case.service";
import CasesTable from "./_components/cases-table"; // "use client"

export default async function Page() {
  const cases = await listCases(); // entire page waits
  return <CasesTable cases={cases} />;
}
```

✅ **Green — pass the unawaited `Promise<T>`; consume with `use()` + `<Suspense>` so the shell streams immediately:**

```tsx
// app/(app)/cases/page.tsx — Server Component
import { Suspense } from "react";
import { listCases } from "@/lib/services/case.service";
import CasesTable from "./_components/cases-table";

export default function Page() {
  const casesPromise = listCases(); // do NOT await
  return (
    <Suspense fallback={<CasesTableSkeleton />}>
      <CasesTable casesPromise={casesPromise} />
    </Suspense>
  );
}
```

```tsx
// _components/cases-table.tsx
"use client";
import { use } from "react";

export default function CasesTable({
  casesPromise,
}: {
  casesPromise: Promise<Case[]>;
}) {
  const cases = use(casesPromise);
  return /* interactive UI */;
}
```

> *"You can use React's `use` API to stream data from the server to client. […] The Client Component should be wrapped in a `<Suspense>` boundary, which displays a fallback while the promise is being resolved."* — Next.js docs `fetching-data.mdx`

---

## 6. Optimistic UI built with manual `useState` + Server Action read-back

❌ **Red — bookkeeping the "real" state by hand, easy to desync:**

```tsx
"use client";
import { useState } from "react";
import { sendMessage, listMessages } from "@/lib/actions/chat.actions";

export function Thread({ initial }: { initial: Message[] }) {
  const [msgs, setMsgs] = useState(initial);
  async function onSend(text: string) {
    setMsgs((m) => [...m, { text, pending: true }]);
    await sendMessage(text);
    setMsgs(await listMessages()); // re-read via action — anti-pattern #1 too
  }
  /* … */
}
```

✅ **Green — `useOptimistic`; the action does the mutation + `revalidatePath`, the optimistic value bridges the gap:**

```tsx
"use client";
import { useOptimistic } from "react";
import { sendMessage } from "@/lib/actions/chat.actions";

export function Thread({ initial }: { initial: Message[] }) {
  const [optimisticMsgs, addOptimistic] = useOptimistic(
    initial,
    (state, draft: Message) => [...state, { ...draft, pending: true }],
  );
  async function onSend(text: string) {
    addOptimistic({ id: crypto.randomUUID(), text, pending: true });
    await sendMessage(text); // revalidatePath('/chat') inside the action
  }
  return /* render optimisticMsgs */;
}
```

> *"`useOptimistic` is a React Hook that lets you optimistically update the UI."* — React docs

The optimistic state survives until the next render after `revalidatePath` resolves; React reconciles automatically.

---

## When to use which pattern — summary

| Scenario | Pattern |
|---|---|
| Initial data for a page | 1 (Server Component) |
| Filter / tab / pagination / sort | 2 (URL `searchParams`) |
| Mutation → list refresh | 3 (`revalidatePath` inside the action) |
| Read function shape | 4 (`lib/services/`, NOT `lib/actions/`) |
| Client widget needs server data at mount | 5 (`Promise<T>` + `use()` + `<Suspense>`) |
| Optimistic UI for sends/likes/toggles | 6 (`useOptimistic`) |
| Polling / focus refetch / 3rd-party-mutated | Route Handler + SWR (last resort, see SKILL.md pattern 4) |
