---
name: promote-component
description: 'Use to refactor a React/RN component up the colocation hierarchy (L0 → L1 → L2) when its usage spreads across pages. Two modes: "scan candidates" counts every component''s usages across the codebase and reports the promotion candidates against the Rule of Three; "promote <Component>" moves the file to the right level, updates all imports. Reads `.workflow/meta.json#stack.framework` to honor next / expo-rn / monorepo conventions. Triggers on: "promote PostCard", "scan promotion candidates", "this component is used everywhere, lift it up", "questo componente è usato in più pagine, promuovilo", "refactor components/shared/". Not for: creating new components (use design-md-to-app or screenshot-to-page or rn-add-screen), splitting compound components into a folder, or moving files across different concerns — this is purely vertical promotion.'
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

## Web vs mobile targets (read this first)

**Next.js App Router** supports `_`-prefixed private folders — `app/<route>/_components/` is a valid non-routable convention there. **Expo Router does not**: every file under `app/` (aside from a short reserved list) becomes a real route, so `app/<route>/_components/` would create a ghost route on mobile, not a private folder. **Settled upstream, not pending**: the request ([expo/expo#44696](https://github.com/expo/expo/issues/44696)) was closed **`won't fix`** on 2026-06-01 — Expo Router wants components outside `app/` by design. Confirmed mechanically at `expo-router@57.0.16`: no underscore rule in the route scanner. Treat mobile `app/` as routes-only, permanently. See `references/colocation-rules.md`.

Consequently this skill uses **different scan/target paths per platform** — see `references/colocation-rules.md` for the full model and rationale. Summary:

| | Web (`stack.framework == "next"`, or `apps/web` in a monorepo) | Mobile (`stack.framework == "expo-rn"`, or `apps/mobile` in a monorepo) |
|---|---|---|
| Candidate scan root | `app/**/_components/*.tsx` | `components/<feature>/*.tsx` (excludes `components/{ui,theme,shared}`) |
| L0 target | `app/<route>/_components/<Component>.tsx` | `components/<feature>/<Component>.tsx` |
| L1 target | `app/(group)/_components/<Component>.tsx` | same folder as L0 (no separate L1 path on mobile — see colocation-rules.md) |
| L2 target | `components/shared/<dominio>/<Component>.tsx` | `components/shared/<dominio>/<Component>.tsx` (identical) |

Everything below is written generically ("the platform's `_components/`-or-`components/<feature>/` root") — substitute per the table above. The scripts (`scripts/scan_promotion.py`, `scripts/promote.py`) branch on `meta.json#stack.framework` automatically.

## Workflow — `scan` mode

### Step 1 — Detect framework + cwd

Read `meta.json#stack.framework`:
- `"next"` → cwd = project root, scan `app/**/_components/`.
- `"expo-rn"` → cwd = project root, scan `components/<feature>/` (excluding `components/{ui,theme,shared}`).
- `"monorepo"` → scan `apps/web/` with the web rules and `apps/mobile/` with the mobile rules, separately. Print two tables.

### Step 2 — Find every promotion candidate

**Web**:
```bash
find app -type d -name "_components" -exec ls -1 {} \;
```
For each `.tsx` file in `_components/`, record component name, source path (e.g., `app/(app)/posts/_components/PostCard.tsx`), and current level (L0: under a leaf route, L1: under `app/(group)/_components/`).

**Mobile**:
```bash
find components -mindepth 2 -maxdepth 2 -name "*.tsx" | grep -vE '/(ui|theme|shared)/'
```
For each match, record component name, source path (e.g., `components/posts/PostCard.tsx`), and which feature folder(s) hold a copy of that name (duplicates across feature folders are the mobile promotion signal — see Step 4).

### Step 3 — Count usages

For every component, grep the codebase for imports referencing its file path or filename (both platforms):

```bash
grep -rln "from .*['\"].*PostCard['\"]" app/ components/ --include="*.tsx" --include="*.ts"
```

Count distinct import sites (deduplicate by file).

### Step 4 — Compute suggestions per Rule of Three

**Web**:

| Usage count | Current level | Suggestion |
|---|---|---|
| 1 | L0 | OK — stays |
| 2 | L0 | Tolerated duplicate — wait the 3rd |
| 3+, all in same route group | L0 (in 2+ pages) | Promote to L1 (`app/(group)/_components/`) |
| 3+, across different route groups | L0 or L1 | Promote to L2 (`components/shared/<dominio>/`) |
| 2+, but on its way up | L1 → L2 | Promote to L2 |

**Mobile** (mobile has no separate L1 path — see colocation-rules.md):

| Copies across feature folders | Suggestion |
|---|---|
| 1 | OK — stays |
| 2 | Tolerated duplicate — wait the 3rd |
| 3+, reconcilable to one feature/domain | Merge duplicates into one `components/<feature>/<Component>.tsx` |
| 3+, spanning different business domains | Promote to L2 (`components/shared/<dominio>/`) |

### Step 5 — Print the report

```
Promotion candidates in apps/web/ (next):

| Component                  | Usages | Current level | Suggestion                              |
|----------------------------|--------|---------------|------------------------------------------|
| PostCard                   | 3      | L0            | Promote to L1 — app/(app)/_components/   |
| UserAvatar                 | 4      | L0            | Promote to L2 — components/shared/user/  |
| BillingSummary             | 2      | L0            | Wait the 3rd use                         |
| PricingTable               | 5      | L0            | Promote to L2 — components/shared/billing/ |

Promotion candidates in apps/mobile/ (expo-rn):

| Component                  | Usages | Current level | Suggestion                                |
|----------------------------|--------|---------------|--------------------------------------------|
| PostCard                   | 3      | L0            | Promote to L2 — components/shared/post/    |
| SettingsRow                | 2      | L0            | Wait the 3rd use                           |
```

Ask the user: "Vuoi promuoverne alcuni? (Y/n, oppure dimmi quali)".

## Workflow — `promote <Component>` mode

### Step 1 — Locate the source file

**Web**: find the file matching `<Component>` under `app/**/_components/`.
**Mobile**: find the file matching `<Component>` under `components/<feature>/` (excluding `components/{ui,theme,shared}`).

If multiple matches (e.g., two copies at L0):
- The "canonical" copy is the older / most-complete one.
- Diff the two; flag any divergence to the user for resolution.

### Step 2 — Determine target level

If invoked without an explicit target, recompute from usage/copy distribution:
- **Web**: same route group, 3+ usages → L1: `app/(group)/_components/<Component>.tsx`. Different groups, 3+ usages → L2: `components/shared/<dominio>/<Component>.tsx`.
- **Mobile**: copies in 3+ feature folders reconcilable to one domain → merge into `components/<feature>/<Component>.tsx` (no move, dedupe only). Copies spanning different business domains → L2: `components/shared/<dominio>/<Component>.tsx`.

Ask the user for `<dominio>` if not obvious (either platform). If an explicit target is provided ("promote PostCard to L2 in components/shared/post/"), honor it.

### Step 3 — Move the file

**Web**:
```bash
# L0 → L1 (same group)
git mv app/(app)/posts/_components/PostCard.tsx app/(app)/_components/PostCard.tsx

# L0 → L2 (cross-group)
mkdir -p components/shared/post
git mv app/(app)/posts/_components/PostCard.tsx components/shared/post/PostCard.tsx
```

**Mobile** (never touches `app/` — components never live there):
```bash
# Dedupe (3rd use reconciled to one feature) — keep the canonical copy in place, remove the others
rm components/profile/PostCard.tsx   # duplicate removed, canonical stays at components/posts/PostCard.tsx

# L0 → L2 (cross-domain)
mkdir -p components/shared/post
git mv components/posts/PostCard.tsx components/shared/post/PostCard.tsx
```

If duplicates existed at L0 (the "2 copies" case), also `rm` them (both platforms).

### Step 4 — Update all imports

Scan all `.tsx` / `.ts` files in `app/` and `components/`, find imports referencing the OLD path or filename, rewrite to the NEW path. Applies identically on both platforms — the import-rewrite step never assumes a platform-specific path shape.

Pattern types:
- Web: `from "@/app/(app)/posts/_components/PostCard"` → `from "@/components/shared/post/PostCard"`
- Mobile: `from "@/components/posts/PostCard"` → `from "@/components/shared/post/PostCard"`
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
