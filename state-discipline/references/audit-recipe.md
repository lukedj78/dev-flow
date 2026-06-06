# Audit recipe — `state-discipline`

Run when the user asks: "audit against state-discipline", "find every useEffect", "scan for prop mirrors", "/audit-state".

**Do not modify code during the audit.** Produce a report only.

---

## Step 1 — confirm scope

```bash
jq -r '.stack.framework, .stack.nextjs_version' .workflow/meta.json
jq -r '.dependencies.next' package.json
```

Refuse if not Next 16 / App Router.

### Lint baseline

Check if the `no-restricted-syntax` rule banning bare `useEffect` is already in place:

```bash
rg -n "CallExpression\[callee\.name='useEffect'\]" eslint.config.* .eslintrc.*
```

If not, that's a top-of-report finding — the lint rule prevents regression. Add it as part of the fix plan.

---

## Step 2 — scan for violations

### A. Bare `useEffect` (not `useMountEffect`) — HIGH

```bash
# All useEffect call sites
rg -n --type=tsx --type=ts -e '\buseEffect\(' \
  -g '!node_modules' -g '!.next' -g '!lib/hooks/use-mount-effect.*'
```

Every hit needs a rung-1-to-7 justification. The only legitimate landing point is `useMountEffect` (rung 7).

### B. `useState` mirroring a prop (with sync `useEffect`) — HIGH

```bash
# useState initialized from a prop, followed by useEffect that setsState from the same prop
rg -n --type=tsx -B1 -A6 -e 'useState\(\s*\w+\s*\)' \
  -g '!node_modules' -g '!.next' \
  | rg -B4 -A4 -e 'useEffect.*set\w+\(\s*\w+'
```

The pattern: `const [x, setX] = useState(propX); useEffect(() => setX(propX), [propX])`. Wrong — derive or `key`.

### C. Derived value computed via `useEffect + setState` — MEDIUM

```bash
# useEffect calling setState with an expression that doesn't reference network/IO
rg -n --type=tsx -B2 -A6 -e 'useEffect' \
  -g '!node_modules' -g '!.next' \
  | rg -B4 -A4 -e 'setState\(' -e 'set\w+\(' \
  | rg -v -e 'fetch\|await\|then\|subscribe'
```

If the effect's body is pure computation → derive during render (or `useMemo` if expensive).

### D. URL-shaped state in `useState` — HIGH

```bash
# Client components with useState whose name suggests URL-shape concerns
rg -n --type=tsx -B1 -A4 \
  -e 'useState.*(?:tab|filter|page|range|sort|search|query|status|category)' \
  -g '!node_modules' -g '!.next'
```

Open each candidate. If the state drives a fetch or affects what's rendered "globally" → URL.

### E. `useEffect` calling `setState` to react to its own state — MEDIUM

```bash
# useEffect with a state variable in deps AND setState in the body for the same variable
rg -n --type=tsx -B1 -A8 -e 'useEffect' \
  -g '!node_modules' -g '!.next' \
  | rg -B4 -A4 -e 'set\w+\(.*\w+'
```

Inspect by eye — these are subtle. If the effect reads a state var and sets it (or a derived one) → derive during render instead.

### F. Side effect (toast/navigate) inside `useEffect` triggered by a flag — MEDIUM

```bash
rg -n --type=tsx -B1 -A6 -e 'useEffect' \
  -g '!node_modules' -g '!.next' \
  | rg -B4 -A4 -e 'toast\.' -e 'router\.push\|router\.replace'
```

Toasts and navigations belong in event handlers (rung 5), not effects triggered by state flags.

### G. Hand-rolled optimistic UI (no `useOptimistic`) — LOW

```bash
rg -n --type=tsx -B1 -A6 \
  -e 'setState.*pending:\s*true' \
  -e 'setState.*sending:\s*true' \
  -e 'setMsgs.*pending' \
  -g '!node_modules' -g '!.next'
```

If the file doesn't import `useOptimistic` from React → refactor to use it.

### H. Reset-on-identity via `useEffect` instead of `key` — MEDIUM

```bash
# useEffect with a single dep that calls setState to a default value
rg -n --type=tsx -B1 -A6 -e 'useEffect.*\[\s*\w+Id\s*\]' \
  -g '!node_modules' -g '!.next' \
  | rg -B4 -A4 -e 'setState\(\s*(""|null|0|\[\]|\{\})' -e 'set\w+\(\s*(""|null|0|\[\]|\{\})'
```

The pattern: `useEffect(() => setX(""), [userId])`. Wrong — `<Comp key={userId} />` instead.

---

## Step 3 — produce the report

Markdown grouped by violation kind (A–H). For each finding:

- File path + line.
- 3–5 line excerpt.
- Which rung from the SKILL.md ladder it should land on.
- Corrected approach in one sentence.
- Severity per the table above.

Summary table:

```
| Violation | High | Medium | Low | Total |
|---|---|---|---|---|
| A — Bare useEffect            | n | – | – | n |
| B — useState mirroring a prop | n | – | – | n |
| C — Derived via useEffect+setState | – | n | – | n |
| D — URL-shaped state in useState | n | – | – | n |
| E — useEffect setState chain     | – | n | – | n |
| F — Side effect in useEffect from flag | – | n | – | n |
| G — Hand-rolled optimistic UI    | – | – | n | n |
| H — Reset-via-useEffect not key  | – | n | – | n |
| Total | N | N | N | N |
```

---

## Step 4 — recommended fix order

1. **Add the lint rule** (Step 1 finding) — `no-restricted-syntax` on `useEffect`. Prevents regression while you fix.
2. **B + H** — straightforward refactors (derive / key). High-impact, mechanical.
3. **A** — surveys all `useEffect` sites; each gets either deleted (rungs 1–6) or renamed to `useMountEffect` (rung 7).
4. **D** — URL migration. UX change; one filter set per commit; screenshot diff.
5. **C + E** — derivation refactors. Reduce re-render churn.
6. **F** — move side effects to event handlers. Often co-located with bug fixes.
7. **G** — `useOptimistic` adoption. Low priority unless the optimistic UI has known race-condition bugs.

---

## Step 5 — offer next steps

1. **Enable the lint rule** — single PR.
2. **Fix one violation kind across the codebase** — pick B first (highest signal).
3. **Fix one component at a time** — top-down through the report.
4. **Open a tracking issue** — GitHub issue with checklist; suggest a "useEffect-ectomy" milestone.

Wait for user to choose.
