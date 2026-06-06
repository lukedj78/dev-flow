> Sources: docs/superpowers/specs/2026-06-06-folder-structure-refactor.md, Next.js project-structure docs, Sandi Metz "The Wrong Abstraction"

# Colocation rules — the canonical model

## 3 levels, intra-app

```
L0  app/<route>/_components/<Component>.tsx       page-private (default)
L1  app/(group)/_components/<Component>.tsx       route-group shared
L2  components/shared/<dominio>/<Component>.tsx   globally shared
```

Plus 2 special folders that don't follow the L0/L1/L2 progression:
- `components/ui/` — design system primitives (Button, Card, Input). Untouched after `shadcn add --all`.
- `components/theme/` — ThemeProvider, ModeToggle, useThemeColor. Never duplicated.

## Rule of Three — when to promote

| Stage | Action |
|---|---|
| 1st use | Create at L0 — inside the page's `_components/`. |
| 2nd use | **COPY** the file into the second page's `_components/`. Tolerated duplicate. |
| 3rd use | **Promote** — call this skill (`promote-component`). |

**Why wait the 3rd**: at the 2nd copy, the differences between the two versions are usually hidden. By the 3rd use you have enough evidence to know what's truly shared vs what's page-specific. Premature abstraction is more expensive than maintaining 2 copies briefly.

## How to choose L1 vs L2

After the 3rd use:
- If all 3 uses are in pages of the **same route group** (e.g., all under `(app)/`): promote to L1 → `app/(app)/_components/`.
- If the 3 uses span **different route groups** (e.g., one in `(marketing)`, one in `(auth)`, one in `(app)`): promote to L2 → `components/shared/<dominio>/`.

**Asking the user for the domain**: when promoting to L2, the `<dominio>` folder name reflects the business domain of the component. Examples:
- `PostCard` → `components/shared/post/`
- `UserAvatar` → `components/shared/user/`
- `PricingTable` → `components/shared/billing/`
- `EmptyState` → if it's a generic primitive without a domain, suggest `components/shared/common/` reluctantly (better: ask if it's UI library material → `components/ui/`).

## Compound components — always together

A compound component (`<Card>` + `<Card.Header>` + `<Card.Body>`) lives **as one unit** at a single level. Promote the whole compound together, never split.

- Up to ~250 lines → single file: `PostCard.tsx` with multiple exports.
- Over ~250 lines → folder: `PostCard/` with `index.ts` barrel + `Header.tsx`, `Body.tsx`, `Footer.tsx`. Import path stays clean via the barrel.

## Cross-platform (monorepo) — separate rule

`packages/shared/` accepts ONLY:
- Types (TS interfaces, type aliases)
- Zod schemas / validators
- Pure functions (no React imports)
- Hooks that return data (no JSX)

`packages/shared/` REJECTS:
- Any `.tsx` file
- Components that return JSX
- Anything that imports from `react-dom`, `react-native`, or any UI library

When a component is "shared cross-platform" semantically:
- The TYPES go in `packages/shared/`
- The VALIDATORS go in `packages/shared/validators/`
- The UI is REWRITTEN twice — once in `apps/web/components/` (DOM) and once in `apps/mobile/components/` (Native). Both import the shared logic.

## Anti-patterns

- ❌ Naming: `shared/`, `common/`, `global/`, `misc/`, `utils/`, `helpers/` as `<dominio>` value at L2. Use the business domain.
- ❌ Cross-group imports: `(app)/posts/page.tsx` importing from `(marketing)/_components/`. If you need it, promote.
- ❌ Premature promotion: lifting to L2 at the 2nd use. Trust the duplicate.
- ❌ Splitting a compound: `Card.tsx` in L1, `Card.Header.tsx` in L0. Unmaintainable.
- ❌ JSX in `packages/shared/`: never. Only logic.
- ❌ Skipping `tsc --noEmit` after a move: silent broken imports.

## Quick reference — decision tree

```
Need to put a component somewhere?
│
├─ Is it a UI primitive (Button, Card, Input)?
│   └─ Yes → components/ui/ (untouched after shadcn init)
│
├─ Is it part of the theme system (ThemeProvider, ModeToggle)?
│   └─ Yes → components/theme/
│
├─ Is it used by just one page?
│   └─ Yes → L0 → app/<route>/_components/
│
├─ Is it used by 2 pages?
│   └─ Yes → keep both at L0 (tolerated duplicate). Wait.
│
├─ Is it used by 3+ pages of the same route group?
│   └─ Yes → L1 → app/(group)/_components/
│
└─ Is it used by 3+ pages across multiple route groups?
    └─ Yes → L2 → components/shared/<dominio>/
```
