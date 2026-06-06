---
name: promote-component
description: 'Use to refactor a React/RN component up the colocation hierarchy (L0 → L1 → L2) when its usage spreads across pages. Two modes: (1) "scan candidates" — analyzes the entire codebase, counts usages of every component under app/**/_components/, and reports a table of promotion candidates with the Rule of Three; (2) "promote <Component>" — moves the file to the right level, updates all imports across the codebase, runs tsc --noEmit to verify, and commits atomically. Reads .workflow/meta.json#stack.framework to honor next / expo-rn / monorepo conventions. Triggers on: "promote PostCard", "scan promotion candidates", "this component is used everywhere, lift it up", "questo componente è usato in più pagine, promuovilo", "refactor components/shared/". Not for: creating new components (use design-md-to-app or screenshot-to-page or rn-add-screen), splitting compound components into a folder (that''s a separate manual refactor), or moving files across different concerns (this skill is purely vertical promotion within the colocation hierarchy).'
---

# promote-component — Rule of Three automation

## Contract

See `references/contracts.md` (vendored from `dev-flow`). Key facts:
- Reads `<project-root>/.workflow/meta.json#stack.framework` (must be `"next"`, `"expo-rn"`, or `"monorepo"`).
- Reads `meta.json#stack.route_groups` (optional, helps detect the target level).
- Modifies code in `<project-root>/` (or `<project-root>/apps/<web|mobile>/` for monorepo).
- Does NOT modify `meta.json#phase`. Appends to `meta.json#history`.
- Always idempotent: re-running the scan reports the same candidates; re-running a promote on an already-promoted component does nothing.

## When this skill applies

- User says "scan promotion candidates" / "scansiona candidati promozione" → run the scan.
- User says "promote <Component>" / "promovi <Component>" → execute the move.
- The user is reviewing the codebase after a feature lands and wants to clean up duplication.

Orchestrator does NOT route here automatically — invoked on demand.

## Knowledge dependencies

- `composition-patterns-guide/SKILL.md` — the 7 Vercel composition rules + our colocation rules.
- `references/colocation-rules.md` — the canonical Rule of Three + L0/L1/L2 spec.

## Workflow — `scan` mode

### Step 1 — Detect framework + cwd

Read `meta.json#stack.framework`:
- `"next"` → cwd = project root.
- `"expo-rn"` → cwd = project root.
- `"monorepo"` → scan both `apps/web/` and `apps/mobile/` separately. Print two tables.

### Step 2 — Find every component under `app/**/_components/`

```bash
find app -type d -name "_components" -exec ls -1 {} \;
```

For each `.tsx` file in `_components/`, record:
- Component name (filename without extension)
- Source path (e.g., `app/(app)/posts/_components/PostCard.tsx`)
- Current level (L0: under a leaf route, L1: under `app/(group)/_components/`)

### Step 3 — Count usages

For every component, grep the codebase for imports referencing its file path or filename:

```bash
grep -rln "from .*['\"].*PostCard['\"]" app/ components/ --include="*.tsx" --include="*.ts"
```

Count distinct import sites (deduplicate by file).

### Step 4 — Compute suggestions per Rule of Three

| Usage count | Current level | Suggestion |
|---|---|---|
| 1 | L0 | OK — stays |
| 2 | L0 | Tolerated duplicate — wait the 3rd |
| 3+, all in same route group | L0 (in 2+ pages) | Promote to L1 (`app/(group)/_components/`) |
| 3+, across different route groups | L0 or L1 | Promote to L2 (`components/shared/<dominio>/`) |
| 2+, but on its way up | L1 → L2 | Promote to L2 |

### Step 5 — Print the report

```
Promotion candidates in apps/web/ (next):

| Component                  | Usages | Current level | Suggestion                              |
|----------------------------|--------|---------------|------------------------------------------|
| PostCard                   | 3      | L0            | Promote to L1 — app/(app)/_components/   |
| UserAvatar                 | 4      | L0            | Promote to L2 — components/shared/user/  |
| BillingSummary             | 2      | L0            | Wait the 3rd use                         |
| PricingTable               | 5      | L0            | Promote to L2 — components/shared/billing/ |
```

Ask the user: "Vuoi promuoverne alcuni? (Y/n, oppure dimmi quali)".

## Workflow — `promote <Component>` mode

### Step 1 — Locate the source file

Find the file matching `<Component>` under `app/**/_components/`. If multiple matches (e.g., two copies at L0):
- The "canonical" copy is the older / most-complete one.
- Diff the two; flag any divergence to the user for resolution.

### Step 2 — Determine target level

If invoked without an explicit target, recompute from usage count + group distribution:
- Same group, 3+ usages → L1: `app/(group)/_components/<Component>.tsx`.
- Different groups, 3+ usages → L2: `components/shared/<dominio>/<Component>.tsx`. Ask user for `<dominio>` if not obvious.

If explicit target provided ("promote PostCard to L2 in components/shared/post/"), honor it.

### Step 3 — Move the file

```bash
# L0 → L1 (same group)
git mv app/(app)/posts/_components/PostCard.tsx app/(app)/_components/PostCard.tsx

# L0 → L2 (cross-group)
mkdir -p components/shared/post
git mv app/(app)/posts/_components/PostCard.tsx components/shared/post/PostCard.tsx
```

If duplicates existed at L0 (the "2 copies" case), also `rm` them.

### Step 4 — Update all imports

Scan all `.tsx` / `.ts` files in `app/` and `components/`, find imports referencing the OLD path or filename, rewrite to the NEW path.

Pattern types:
- `from "@/app/(app)/posts/_components/PostCard"` → `from "@/components/shared/post/PostCard"`
- `from "./PostCard"` (siblings) → resolve to absolute, then rewrite
- `from "../PostCard"` (parent) → idem

Use a TypeScript-aware import rewrite (e.g., `ts-morph` Python equivalent via jscodeshift or simple regex with care).

### Step 5 — Verify with tsc

```bash
npx tsc --noEmit
```

Must pass. If it fails:
1. Inspect the error: usually a path that wasn't rewritten.
2. Fix it manually.
3. Re-verify.

If still failing after 2 attempts, ROLLBACK the move (`git restore`) and report to the user.

### Step 6 — Commit + history

```bash
git add -A
git commit -m "refactor: promote <Component> from <old-level> to <new-level>"
```

Append to `meta.json#history`:
```json
{
  "skill": "promote-component",
  "ran_at": "<iso>",
  "inputs": {"component": "PostCard", "from": "L0 (3 sites)", "to": "L2", "domain": "post"},
  "outputs": {"new_path": "components/shared/post/PostCard.tsx", "imports_updated": 3}
}
```

## Common anti-patterns (NEVER do)

- ❌ Promote at the 2nd use — wait the 3rd. The premature abstraction is more expensive than the duplicate.
- ❌ Move without rewriting imports — broken project.
- ❌ Promote a compound component piece by piece — the whole compound moves together, always.
- ❌ Use generic domain names (`shared/common/`, `shared/misc/`) — use the business domain.
- ❌ Promote across route groups WITHOUT going to L2 — if 2+ groups use it, it MUST live in `components/shared/`.
- ❌ Skip the tsc verification — silent broken imports propagate.

## Updating meta.json (recommended pattern)

```bash
python3 .../dev-flow/scripts/update_meta.py <project-root> append-history \
    --skill 'promote-component' --inputs '{"component": "<X>"}' --outputs '{"new_path": "<path>"}'
```

## Sources

- Spec: `docs/superpowers/specs/2026-06-06-folder-structure-refactor.md`
- Sandi Metz, "The Wrong Abstraction" (2016): https://sandimetz.com/blog/2016/1/20/the-wrong-abstraction
- "Rule of Three" pattern: documented in "The Pragmatic Programmer" + multiple refactoring books.
