---
name: state-discipline
description: 'Apply React 19 / Next.js 16 state discipline — `useState` is the last resort, not the default: derive from props/URL/data, `key` to reset, `useMountEffect` for one-time external sync, never bare `useEffect`. Use when the user pastes `useState + useEffect + fetch`, reaches for `useState` to mirror a prop, hand-rolls a derived value via `useEffect + setState`, syncs state with URL via `useEffect`, or asks "should I add useState here?". Also owns the React 19 concurrent-state APIs — `useTransition`, `useOptimistic`, `useActionState`, `<Activity>` — including when described rather than named: keeping the UI responsive during a pending update, an optimistic UI, form action state, a hidden subtree that stays mounted. Refuses outside Next.js 16 App Router. Not for: server-data reads (use `data-fetching`), form field values (use `forms`), or React Native state patterns.'
---

# state-discipline — `useState` is the last resort

This skill governs **where state lives** in a Next.js 16 App Router / React 19 codebase. The framework's primitives (Server Components, URL `searchParams`, props, query libraries, controlled inputs, `useOptimistic`, `useTransition`) cover ~90% of "I need some state" cases. `useState` and `useEffect` are escape hatches for the last 10%.

The bug is silent: code that uses `useState` + `useEffect` to mirror a prop, derive a value, or sync with the URL **works** — until the source of truth changes and the mirror desyncs. No error, no warning, just wrong UI.

## When this skill applies

- The user pastes `useState + useEffect` and asks for review.
- The user is about to add `useEffect` (at all).
- The user is about to add `useState` to mirror a prop.
- The user asks "should I add `useState` here?".
- The user is about to add `useState` to hold form field values (route them to the `forms` skill).
- The user is about to add `useState` to hold server-fetched data (route them to the `data-fetching` skill).
- The user asks to **audit** a codebase against the React state rules.

## Contract

Follows the dev-flow contract — see `references/contracts.md`. Key facts:

- Reads `meta.json#stack.framework` and `stack.nextjs_version`. For monorepo, reads `stack.monorepo.web.*`.
- **Refuses** if `stack.framework ∉ {"next", "monorepo"}` or `stack.nextjs_version != "16"`. The principles transfer to other React 19 setups (Remix v3, plain React 19 + Vite, etc.) but the URL/Server-Component rungs do not — refuse rather than mis-apply.
- Appends `history` per refactor.
- Does **not** bump `phase`.

## Companion skills

- **`data-fetching`** — owns the "read data in Server Components, not in `useEffect`" rule. Every `useEffect` that fetches is a data-fetching problem first.
- **`forms`** — owns field state for forms. Every `useState` bound to `<input>`/`<Checkbox>`/`<Switch>` whose value persists is a forms problem first.

This skill owns everything left over: derived values, prop mirrors, UI toggles, optimistic UI, reset semantics, one-time external sync.

## The Rule

**Reach for `useState` only after exhausting these alternatives, in order:**

1. **Can it be derived?** Compute from props, URL, or other state during render. No `useEffect + setState`.
2. **Can it live in the URL?** `searchParams` for tabs, filters, ranges, pagination, sort, search query, modal-open, selected-item. Page stays a Server Component.
3. **Can it be a prop?** Lift state to the nearest common parent. Stop mirroring.
4. **Is it server state?** Use a query library (or — preferably — push it back to a Server Component per the `data-fetching` skill).
5. **Is it a one-shot side effect (after user click, after fetch resolves)?** Event handler. Not `useEffect`.
6. **Do you need to reset state when an identity changes?** Pass `key` to the component.
7. **Do you need one-time external sync at mount (DOM API, third-party widget, focus management)?** `useMountEffect` from `@/lib/hooks/use-mount-effect` — the project's explicit-intent escape hatch with a single `eslint-disable` localized to its definition.
8. **None of the above** → `useState` is honestly the right answer (transient UI like hover, dropdown-open without URL contract, animation in-progress, etc.). Use it and move on.

**Never bare `useEffect`.** Ban it via lint:

```json
// eslint config — no-restricted-syntax
{
  "selector": "CallExpression[callee.name='useEffect']",
  "message": "Bare useEffect is banned. Use the state-discipline skill ladder. For one-time external sync use useMountEffect."
}
```

The lint rule lives in the project; this skill is its conceptual source of truth.

## The eight rungs — with examples

### 1. Derive, don't store-and-sync

❌ **Red — mirror a prop into state, sync via `useEffect`:**

```tsx
function FullName({ first, last }: { first: string; last: string }) {
  const [full, setFull] = useState("");
  useEffect(() => {
    setFull(`${first} ${last}`);
  }, [first, last]);
  return <span>{full}</span>;
}
```

✅ **Green — derive during render:**

```tsx
function FullName({ first, last }: { first: string; last: string }) {
  const full = `${first} ${last}`;
  return <span>{full}</span>;
}
```

If the derivation is expensive: `useMemo`. Still no `useEffect`.

### 2. URL state for shareable / back-button-correct state

❌ **Red — filter state in `useState`, page becomes `"use client"`:**

```tsx
"use client";
function CasesPage() {
  const [status, setStatus] = useState<"open" | "closed">("open");
  // …re-fetch via Server Action on status change…
}
```

✅ **Green — filter state in URL, page stays Server Component:**

```tsx
// app/(app)/cases/page.tsx
export default async function CasesPage({
  searchParams,
}: {
  searchParams: Promise<{ status?: string }>;
}) {
  const { status = "open" } = await searchParams;
  const cases = await listCases({ status });
  return <CasesView cases={cases} status={status} />;
}
```

The chip-row Client Component writes the param. Free streaming, free cache, shareable URL, back-button works.

**Write the URL with `nuqs`, not hand-rolled `router.replace`.** Verified against **`nuqs@2.10.1`** (2026-08-26): its `peerDependencies.next` is `>=14.2.0` with **no upper bound**, so Next 16 needs no opt-in and no special handling. `debounce(timeMs)` and `throttle(timeMs)` are both exported and both return a `LimitUrlUpdates`, which is what `limitUrlUpdates` takes. [`nuqs`](https://nuqs.dev) (v2) is the ecosystem-first, type-safe URL-state library — `useQueryState`/`useQueryStates` behave like `useState` but persist to the URL, with typed parsers, built-in **URL-update rate limiting** (`limitUrlUpdates: debounce(…)` — hand-rolled per-keystroke `router.replace` on a search box is the classic jank), and `useTransition` support. The page stays a Server Component reading the `searchParams` prop (above) — nuqs only owns the **client write side**:

```tsx
"use client";
import { useQueryState, parseAsStringEnum } from "nuqs";
// chip row — one typed param, synced to ?status=
const [status, setStatus] = useQueryState(
  "status",
  parseAsStringEnum(["open", "closed"]).withDefault("open"),
);
// setStatus("closed") updates the URL; the Server Component above re-renders with new data
```

One-time setup: wrap the root layout in `<NuqsAdapter>` (from `nuqs/adapters/next/app`). For type-safe server reads in nested components without prop-drilling, `createSearchParamsCache([...])`. The hand-rolled `router.replace(\`?\${next}\`)` is a fine fallback when you don't want the dependency, but for anything beyond a single boolean, prefer nuqs.

### 3. Lift state, don't mirror

❌ **Red — child mirrors parent's state:**

```tsx
function Child({ value }: { value: string }) {
  const [local, setLocal] = useState(value);
  useEffect(() => setLocal(value), [value]);
  // …
}
```

✅ **Green — read the prop:**

```tsx
function Child({ value }: { value: string }) {
  // …read `value` directly
}
```

If the child needs to edit, lift the setter to the parent too.

### 4. Server state belongs on the server (or in a query library)

See the `data-fetching` skill. If you must keep it client-side (polling / focus refetch / third-party-mutated data), use SWR or React Query — they own staleness, dedup, retry, error states. Do not re-implement with `useState + useEffect`.

### 5. Side effect after user click → event handler, not `useEffect`

❌ **Red — set a "submitted" flag then react in `useEffect`:**

```tsx
function Form() {
  const [submitted, setSubmitted] = useState(false);
  useEffect(() => {
    if (submitted) {
      toast.success("Saved!");
      setSubmitted(false);
    }
  }, [submitted]);
  return <button onClick={() => setSubmitted(true)}>Save</button>;
}
```

✅ **Green — do it in the click handler:**

```tsx
function Form() {
  return (
    <button onClick={() => { void save(); toast.success("Saved!"); }}>
      Save
    </button>
  );
}
```

### 6. Reset state on identity change → `key`, not `useEffect`

❌ **Red — reset internal state via `useEffect` on prop change:**

```tsx
function ProfileForm({ userId }: { userId: string }) {
  const [draft, setDraft] = useState("");
  useEffect(() => {
    setDraft(""); // reset when userId changes
  }, [userId]);
  // …
}
```

✅ **Green — let React unmount/remount via `key`:**

```tsx
<ProfileForm key={userId} userId={userId} />
```

The child gets fresh state on every `userId` change. No effect, no race.

**Want to keep the state instead of resetting it?** `key` always throws the subtree away. If the goal is the opposite — hide a tab/panel but keep its scroll position, form draft, or component state alive for when it's shown again — reach for `<Activity>` instead of `key`. See "`<Activity>` — hide without resetting" below.

### 7. One-time external sync → `useMountEffect`

For unavoidable mount-only side effects (DOM API, third-party widget init, focus management), use `useMountEffect` — a thin wrapper around `useEffect(fn, [])` with explicit intent:

```tsx
// lib/hooks/use-mount-effect.ts
import { useEffect } from "react";
export function useMountEffect(fn: () => void | (() => void)) {
  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(fn, []);
}
```

```tsx
"use client";
import { useMountEffect } from "@/lib/hooks/use-mount-effect";

export function FocusOnMount() {
  const ref = useRef<HTMLInputElement>(null);
  useMountEffect(() => { ref.current?.focus(); });
  return <input ref={ref} />;
}
```

The `eslint-disable` lives in **one** place. Every consumer site is grep-able by `useMountEffect`.

**Cleaner alternative when the effect reads fresh props/state: `useEffectEvent`.** `useMountEffect`'s `eslint-disable` is a blunt instrument — it silences the exhaustive-deps check for the whole effect body, so if the effect also needs to *read* a prop or piece of state without re-firing when that value changes, there's no clean way to say so. `useEffectEvent` (from `react`) solves exactly this: it wraps the part of the effect that must always see the latest values but must never itself be a reactive dependency.

```tsx
"use client";
import { useEffect, useEffectEvent } from "react";

export function ChatRoom({ roomId, theme }: { roomId: string; theme: string }) {
  const onConnected = useEffectEvent(() => {
    showNotification("Connected!", theme); // always reads the LATEST theme
  });

  useEffect(() => {
    const connection = createConnection(roomId);
    connection.on("connected", () => onConnected());
    connection.connect();
    return () => connection.disconnect();
  }, [roomId]); // theme is NOT a dependency — onConnected reads it fresh, no re-connect on theme change
}
```

Use `useMountEffect` for genuinely mount-only, no-fresh-reads side effects (focus on mount, one-shot third-party init). Reach for `useEffectEvent` when the effect must stay subscribed/connected across renders but a piece of its logic needs to read current props/state without becoming a re-run trigger. **Stable since React 19.2** (shipped alongside `<Activity>` and `cacheSignal`; current stable 19.2.x) — import `useEffectEvent` from `react`, not the `experimental_` prefix. On React 19.0/19.1 the prefixed form is still required.

### 8. Honest `useState` — the last 10%

Some state really is local, transient, has no URL contract, isn't derivable, isn't server state:

- Hover / focus state for visual feedback (when CSS `:hover` doesn't fit).
- Dropdown-open / tooltip-open when there's no URL reason to share it.
- Animation in-progress flags.
- "Show more" toggle inside a card.

For these, `useState` is honest. Use it. Don't over-engineer.

## Optimistic UI — `useOptimistic`, not hand-rolled

❌ **Red — bookkeeping the "real" state by hand:**

```tsx
const [msgs, setMsgs] = useState(initial);
async function onSend(text: string) {
  setMsgs((m) => [...m, { text, pending: true }]);
  await sendMessage(text);
  setMsgs(await listMessages()); // re-read by hand
}
```

✅ **Green — `useOptimistic` + `revalidatePath` inside the action:**

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
    addOptimistic({ id: crypto.randomUUID(), text });
    await sendMessage(text); // revalidatePath('/chat') inside the action
  }
  return /* render optimisticMsgs */;
}
```

## Transitions — `useTransition` for non-blocking updates

When a state update triggers heavy re-render (filter a large list, switch tabs that re-render charts), wrap in `useTransition` so the UI stays responsive:

```tsx
"use client";
import { useTransition, useState } from "react";

export function HeavyTabs() {
  const [tab, setTab] = useState("a");
  const [pending, startTransition] = useTransition();
  return (
    <button onClick={() => startTransition(() => setTab("b"))}>
      {pending ? "Loading…" : "Tab B"}
    </button>
  );
}
```

For URL-state transitions, wrap the `router.replace` call in `startTransition` — `pending` becomes the loading state.

## `useActionState` — where it lands relative to the ladder

`useActionState` (React 19) is neither a new rung nor a replacement for any of the 8 — it's the primitive for **pending/error state of a single Server Action invocation** when the full `forms` toolkit (Zod schema, dirty/valid gating, baseline reset) is overkill: a one-button action (archive, delete, resend-invite, like), not a multi-field form.

```tsx
"use client";
import { useActionState } from "react";
import { archiveClient } from "@/lib/server/clienti";

export function ArchiveButton({ id }: { id: number }) {
  const [state, formAction, isPending] = useActionState(archiveClient, { ok: true });
  return (
    <form action={formAction}>
      <input type="hidden" name="id" value={id} />
      <button disabled={isPending}>{isPending ? "Archiving…" : "Archive"}</button>
      {!state.ok && <p className="text-error">{state.error}</p>}
    </form>
  );
}
```

- **Multi-field form with validation, dirty tracking, Save-button gating?** That's the `forms` skill's job — `useActionState` alone doesn't give you field-level dirty/valid state.
- **Single action, no fields (or hidden-only fields), just need pending + the action's returned result?** `useActionState` is the honest, minimal answer — don't hand-roll `useState` + `useTransition` + manual error bookkeeping to reinvent it (that's rung-8-gone-wrong: a `useState` that's really re-implementing a framework primitive).
- Don't reach for `useOptimistic` here unless the button also needs an instant UI flip before the action resolves — the two compose (`useOptimistic` for the instant flip, `useActionState` for the pending/error of the underlying action).

## `<Activity>` — hide without resetting (alternative to `key`)

`key` (rung 6) is for **resetting** state when identity changes — React throws the old subtree away and mounts a fresh one. `<Activity>` (React 19.2) is for the opposite need: **hide a subtree from the screen while keeping its state, DOM, and effects' cleanup alive**, so switching back doesn't lose scroll position, an in-progress form draft, or an expensive-to-rebuild tree (an inactive chat tab, an offscreen wizard step, a background route in a tab-like UI).

```tsx
import { Activity } from "react";

function Tabs({ activeTab }: { activeTab: "chat" | "settings" }) {
  return (
    <>
      <Activity mode={activeTab === "chat" ? "visible" : "hidden"}>
        <ChatPanel />
      </Activity>
      <Activity mode={activeTab === "settings" ? "visible" : "hidden"}>
        <SettingsPanel />
      </Activity>
    </>
  );
}
```

Rule of thumb: **`key` = reset, `<Activity>` = preserve.** If a bug report says "my draft disappeared when I switched tabs and came back," that's a `key`-shaped reset where `<Activity>` was needed. **Stable since React 19.2** — available from `react` directly (current stable 19.2.x). On React 19.0/19.1 it was canary-only, so check the project's version before reaching for it.

## Red flags / rationalizations

| Rationalization | Counter |
|---|---|
| "I just need to keep the prop in state so I can edit it locally." | Lift the setter, or use `key` to reset on identity change. Mirroring desyncs. |
| "I'll `useEffect` to compute X from Y." | Derive during render. If expensive: `useMemo`. |
| "I need to fetch on mount." | Server Component (`data-fetching` rung 1). Or `useMountEffect` if genuinely client-side. |
| "I need to sync state to URL on every change — `useEffect` is fine." | Backwards. Make URL the source of truth; read it server-side via the `searchParams` prop; write it client-side via `nuqs` `useQueryState` (typed + throttled) — or hand-rolled `router.replace` for a single param. The "sync" disappears. |
| "I'll `useEffect` to reset state when the user changes." | `key={userId}` on the component. |
| "I'll show a toast in `useEffect` after submit." | Toast in the click handler. |
| "I'll store the dropdown-open state in URL." | Don't — local UI state with no shareable contract belongs in `useState`. Rung 8. |
| "I need `useEffect` for a third-party library." | `useMountEffect` if mount-only. If it has its own subscription model, follow its docs (often a hook the library provides). |
| "useOptimistic is overkill, I'll just `setState`." | `useOptimistic` is the rung. Manual setState + manual re-read is anti-pattern data-fetching #6. |

## Reset semantics — quick table

| What changes | How to reset state |
|---|---|
| Prop identity (`userId`, `recordId`) | `key={prop}` on the component |
| Route segment | Built-in via React — different segment renders a different subtree |
| Manual user action (Clear button) | Event handler that calls the setter(s) |
| Form save success | The `forms` skill's hook resets baseline automatically — see `forms` |
| Server data refresh | `revalidatePath` / `revalidateTag` — see `data-fetching` |

## Workflow

### Step 1 — verify the contract

Read `.workflow/meta.json`. Confirm `stack.framework ∈ {"next", "monorepo"}` and `stack.nextjs_version = "16"`. Else refuse.

### Step 2 — diagnose the call site

For a `useState + useEffect` pair, walk the 8 rungs top-down. For a bare `useEffect`, demand a rung-7 justification (`useMountEffect`) or refuse.

### Step 3 — refactor

Apply the matching rung's green pattern. If routing to a sibling skill (`forms` for field state, `data-fetching` for server reads), say so and stop.

### Step 4 — append history

```json
{
  "skill": "state-discipline",
  "ran_at": "<now>",
  "outputs": ["<file>"],
  "phase_before": "<unchanged>",
  "phase_after": "<unchanged>"
}
```

## Audit mode

When the user asks "audit against state-discipline" / "find every useEffect" / "scan for prop mirrors", produce a report. The audit recipe lives in `references/audit-recipe.md`.

Violation kinds:

| Code | Violation | Severity |
|---|---|---|
| A | Bare `useEffect` (not `useMountEffect`) | high |
| B | `useState` mirroring a prop (with sync `useEffect`) | high |
| C | Derived value computed via `useEffect + setState` | medium |
| D | URL-shaped state (tabs / filters / pagination) in `useState` | high |
| E | `useEffect` calling `setState` to react to its own state | medium |
| F | Side effect (toast, navigate) inside `useEffect` triggered by a flag | medium |
| G | Hand-rolled optimistic UI (no `useOptimistic`) | low |
| H | Reset-on-identity via `useEffect` instead of `key` | medium |

## Sources

**Verified 2026-08-26 against `react@19.2.8`.** All five concurrent-state APIs this skill leans on —
`useEffectEvent`, `Activity`, `useOptimistic`, `useActionState`, `useTransition` — are exported under
their **stable** names, with no `unstable_` or `experimental_` variants alongside them. So the ladder
below carries no canary hedge. (Note `expo@57.0.16` pins React at `19.2.3`, one patch behind npm; both
are past the 19.2 stabilisation, so nothing here changes on RN — and RN has no URL rung anyway.)
All ten cited URLs resolve.

Derived from the `nextjs-usestate` skill from **[lusentis/next-skills](https://github.com/lusentis/next-skills)** (MIT-licensed), adapted to the dev-flow contract and renamed to `state-discipline` since the rules cover all state, not only `useState`. The eight-rung ladder, the `useMountEffect` escape-hatch contract, the `key`-for-reset discipline, the lint rule, and the red-flag catalog are preserved.

- Original: <https://github.com/lusentis/next-skills/tree/main/skills/nextjs-usestate>
- React docs (You Might Not Need an Effect): <https://react.dev/learn/you-might-not-need-an-effect>
- React docs (`useOptimistic`): <https://react.dev/reference/react/useOptimistic>
- React docs (`useTransition`): <https://react.dev/reference/react/useTransition>
- React docs (`key`): <https://react.dev/learn/preserving-and-resetting-state>
- React docs (`useActionState`): <https://react.dev/reference/react/useActionState>
- React docs (`useEffectEvent`) — **stable since React 19.2**: <https://react.dev/reference/react/useEffectEvent>
- React docs (`<Activity>`) — **stable since React 19.2**: <https://react.dev/reference/react/Activity>
- **`data-fetching/references/nuqs.md`** — the doc-grounded how-to for rung 2 (URL state) with `nuqs`: hooks, parsers, options, server-side cache. Read it before wiring URL state — don't improvise the API.

## When in doubt

Walk the 8 rungs top-down. Stop at the first that fits. Reaching rung 8 too often is the signal you're skipping rungs 1–4.
