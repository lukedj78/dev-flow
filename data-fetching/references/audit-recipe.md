# Audit recipe — `data-fetching`

Run when the user asks: "audit my codebase against data-fetching", "scan for read anti-patterns", "find every useEffect that fetches", "/audit-data-fetching".

**Do not modify code during the audit.** Produce a report only.

---

## Step 1 — confirm scope

```bash
# meta.json sanity
jq -r '.stack.framework, .stack.nextjs_version' .workflow/meta.json

# Next 16
jq -r '.dependencies.next' package.json

# App Router only — refuse if pages/ exists
ls pages/ 2>&1
```

If pages/ exists or `nextjs_version` is not 16 → refuse, explain why, stop.

---

## Step 2 — scan for violations

### A. `useEffect` calling a Server Action (`getX` / `listX` / `findX`) — HIGH

```bash
# Files importing both a "use server" action AND useEffect
rg -l --type=tsx --type=ts -e '"use server"' lib/actions/ \
  | xargs -I{} basename {} .ts | sed 's/\.actions$//' \
  > /tmp/action-files.txt

rg -n --type=tsx -B2 -A6 -e 'useEffect' \
  -g '!node_modules' -g '!.next' \
  | rg -B6 -A4 -e 'from\s+["'\''"]@/lib/actions/'
```

Open each candidate by eye — confirm the action being called is a read (`getX`/`listX`/`findX`), not a legitimate mutation triggered on mount.

### B. `useState + useEffect + fetch` in a Client Component — HIGH

```bash
rg -n --type=tsx -B2 -A10 -e 'useEffect' \
  -g '!node_modules' -g '!.next' \
  | rg -B6 -A4 -e 'fetch\(' -e 'useState'
```

The pattern: a Client Component that holds `useState<X[]>([])` + `useEffect(() => fetch(...).then(setX), [])`. Classic — should be a Server Component or `use(promise)` + Suspense.

### C. Filter/tab state in `useState` causing client-side refetch loop — HIGH

```bash
rg -n --type=tsx -B2 -A8 -e 'useEffect.*\[\s*\w+\s*\]' \
  -g '!node_modules' -g '!.next' \
  | rg -B6 -A4 -e 'fetch\(' -e 'getCases\|getX\|listX'
```

If the effect's dependency array references a state variable that drives a fetch → the user typed "I want filter state in useState and refetch on change". Move to URL `searchParams`.

### D. `"use server"` file containing read-only `getX` / `listX` / `findX` — MEDIUM

```bash
# Find functions in lib/actions/ whose name starts with get/list/find/fetch
rg -n --type=ts -e '^export\s+async\s+function\s+(get|list|find|fetch)' lib/actions/
```

These should live in `lib/services/` (server-only code; no `"use server"` directive). Action files reserve for mutations.

### E. `await` in Server Component then pass to Client (no `<Suspense>` streaming) — MEDIUM

```bash
# async page that imports a Client Component
rg -ln --type=tsx -e '^export\s+default\s+async\s+function' app/ \
  | xargs -I{} rg -lH --type=tsx -e '"use client"' {} 2>/dev/null
```

Open each candidate. If the page does `const x = await fetch...; return <ClientComponent x={x}>` without a `<Suspense>` wrapper, it's pattern E: streaming is blocked. Refactor to pass `xPromise` and let the client `use(xPromise)`.

### F. Manual list re-read after mutation (no `revalidatePath`/`revalidateTag`) — HIGH

```bash
# Pattern: await action(); then await listX() then setState
rg -n --type=tsx -B1 -A6 -e 'await\s+\w+Action' \
  -g '!node_modules' -g '!.next' \
  | rg -B4 -A4 -e 'setState\|setMsgs\|setItems\|setCases\|setUsers'
```

Cross-check the corresponding `"use server"` files for `revalidatePath` / `revalidateTag` / `refresh` — if they don't call any, that's the bug. The client shouldn't re-read; the action should invalidate.

```bash
# Actions missing revalidate*
rg -L 'revalidatePath\|revalidateTag\|refresh' lib/actions/*.actions.ts
```

### G. Route Handler + SWR for a read that should be a Server Component — MEDIUM

```bash
# Route handlers
find app/api -name 'route.ts' -o -name 'route.tsx' | head -20

# Client components using SWR/React Query
rg -ln -e "from\s+['\"]swr['\"]" -e "from\s+['\"]@tanstack/react-query['\"]" \
  -g '!node_modules' -g '!.next'
```

For each pairing, ask: is the data per-user / per-org? Does it require polling or focus refetch? If neither — it should be a Server Component (pattern 1), and the route handler + SWR are deadweight.

---

## Step 3 — produce the report

Markdown grouped by violation kind (A–G). For each finding:

- File path + line.
- 3–5 line excerpt.
- Which rule it violates (link to matching SKILL.md / anti-patterns.md pattern).
- Corrected approach in one sentence.
- Severity.

Summary table:

```
| Violation | High | Medium | Total |
|---|---|---|---|
| A — useEffect+action     | n | – | n |
| B — useState+useEffect+fetch | n | – | n |
| C — Filter state in useState | n | – | n |
| D — Read action in lib/actions/ | – | n | n |
| E — await blocks streaming | – | n | n |
| F — Manual re-read after mutation | n | – | n |
| G — Route Handler + SWR misuse | – | n | n |
| Total | N | N | N |
```

---

## Step 4 — recommended fix order

1. **D** first — moving `getX` to `lib/services/` is mechanical and unblocks the rest.
2. **A + B + F** — refactor pages to async Server Components (the migration ladder rung 1). One file per commit.
3. **C** — URL `searchParams` migration (rung 2). One filter set per commit; each is a UX change so worth a screenshot.
4. **E** — wrap in `<Suspense>` + pass unawaited promise. Smaller diff, often one line.
5. **G** — convert Route Handler + SWR → Server Component. Last; not all G are bugs (polling cases legitimately need it).

---

## Step 5 — offer next steps (do not execute unprompted)

1. **Fix one violation kind across the codebase** — pick D for the quickest win.
2. **Fix one page at a time** — top-down through the report.
3. **Open a tracking issue** — GitHub issue with checklist.

Wait for the user to choose.
