> Sources: docs/superpowers/specs/2026-06-06-folder-structure-refactor.md, Next.js project-structure docs, Expo Router docs, Sandi Metz "The Wrong Abstraction"

# Colocation rules — the canonical model

## Web vs mobile: two different physical targets, one shared model

The **Rule of Three promotion model** (L0 → L1 → L2, promote at the 3rd use) is identical on web and mobile. The **physical target paths are NOT identical**, because of one hard platform fact:

- **Next.js App Router** treats any `_`-prefixed folder under `app/` as non-routable. `app/<route>/_components/` is a valid, first-class private-folder convention there.
- **Expo Router has no equivalent convention.** Every file placed under `app/` (aside from a short reserved list — `_layout.tsx`, `+not-found.tsx`, etc.) is registered as a real route. `app/<route>/_components/PostCard.tsx` does not create a private folder on Expo — it creates a ghost route at that path. **[VERIFY]** against the installed `expo-router` version: there is an open upstream issue requesting an underscore-skip convention matching Next.js; until it ships, treat `app/` as zero-tolerance for non-route files.

This is why the two platforms need distinct target paths for the same conceptual levels:

```
                          WEB (Next.js — `_components/` valid)         MOBILE (Expo Router — this file governs it)
L0  page-private          app/<route>/_components/<Component>.tsx      components/<feature>/<Component>.tsx
L1  route-group shared     app/(group)/_components/<Component>.tsx      components/<feature>/<Component>.tsx  (same physical
                                                                          folder as L0 — Expo has no route-group-scoped
                                                                          component folder; see note below)
L2  globally shared        components/shared/<dominio>/<Component>.tsx  components/shared/<dominio>/<Component>.tsx  (identical)
```

**Why L0 and L1 collapse to the same physical folder on mobile**: on web, a route group (`(app)/`) is itself a folder inside `app/`, so `_components/` can be scoped to that group. On mobile, components live entirely outside `app/`, organized by *feature* (not by route group) — there is no folder that represents "shared within this route group but not global" the way `app/(group)/_components/` does on web. The promotion from L0 → L1 on mobile is therefore not a *move*; it's a **dedupe**: the 2nd use copies the file into the second feature's `components/<feature>/` folder (tolerated duplicate), and reaching the 3rd use is the signal to either merge duplicates back into one shared feature file (still `components/<feature>/`) or — if the uses genuinely span different business domains — jump straight to L2.

Plus 2 special folders that don't follow the L0/L1/L2 progression (identical on both platforms):
- `components/ui/` — design system primitives (Button, Card, Input). Untouched after `shadcn add --all` (web) / after the NativeWind primitives are wired (mobile).
- `components/theme/` — ThemeProvider, ModeToggle, useThemeColor. Never duplicated.

## Rule of Three — when to promote

| Stage | Web | Mobile |
|---|---|---|
| 1st use | Create at L0 — `app/<route>/_components/`. | Create at L0 — `components/<feature>/`. |
| 2nd use | **COPY** the file into the second page's `_components/`. Tolerated duplicate. | **COPY** the file into the second feature's `components/<feature>/`. Tolerated duplicate. |
| 3rd use | **Promote** — call this skill (`promote-component`). | **Promote** — call this skill (`promote-component`); it resolves to L2 (mobile has no separate L1 target — see above). |

**Why wait the 3rd**: at the 2nd copy, the differences between the two versions are usually hidden. By the 3rd use you have enough evidence to know what's truly shared vs what's page-specific. Premature abstraction is more expensive than maintaining 2 copies briefly.

## How to choose L1 vs L2 (web) / when to promote to L2 (mobile)

**Web**, after the 3rd use:
- If all 3 uses are in pages of the **same route group** (e.g., all under `(app)/`): promote to L1 → `app/(app)/_components/`.
- If the 3 uses span **different route groups** (e.g., one in `(marketing)`, one in `(auth)`, one in `(app)`): promote to L2 → `components/shared/<dominio>/`.

**Mobile**, after the 3rd use (i.e., copies exist in 3+ `components/<feature>/` folders, or usage count reaches 3 within a single feature):
- If all copies are effectively the same feature/domain: merge back into a single `components/<feature>/<Component>.tsx` (no L2 needed — this is the mobile "L1" outcome, same physical location as L0).
- If the copies span genuinely different business domains: promote to L2 → `components/shared/<dominio>/`.

**Asking the user for the domain**: when promoting to L2 (either platform), the `<dominio>` folder name reflects the business domain of the component. Examples:
- `PostCard` → `components/shared/post/`
- `UserAvatar` → `components/shared/user/`
- `PricingTable` → `components/shared/billing/`
- `EmptyState` → if it's a generic primitive without a domain, suggest `components/shared/common/` reluctantly (better: ask if it's UI library material → `components/ui/`).

## Compound components — always together

A compound component (`<Card>` + `<Card.Header>` + `<Card.Body>`) lives **as one unit** at a single level. Promote the whole compound together, never split.

- Up to ~250 lines → single file: `PostCard.tsx` with multiple exports.
- Over ~250 lines → folder: `PostCard/` with `index.ts` barrel + `Header.tsx`, `Body.tsx`, `Footer.tsx`. Import path stays clean via the barrel.

## Cross-platform (monorepo) — separate rule

**Delegate to `monorepo-add-shared-package` when the promotion is cross-platform.** This skill's script (`promote-component`) only moves files between the intra-app L0/L1/L2 levels above (web: `app/**/_components/` ↔ `components/shared/`; mobile: `components/<feature>/` ↔ `components/shared/`) — it does not create or wire a `packages/` workspace. If the 3rd use crosses `apps/web` and `apps/mobile` (not just route groups or features within one app) and what's shared is types, Zod schemas, pure functions, or data hooks, stop here and hand off to `monorepo-add-shared-package` to scaffold/extend the `packages/shared/` workspace; come back to `promote-component` only for the per-platform UI rewrite that still needs L0/L1/L2 placement in each app (per its own platform's target paths above).

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
- The UI is REWRITTEN twice — once in `apps/web/components/` (DOM, per the web target paths) and once in `apps/mobile/components/` (Native, per the mobile target paths). Both import the shared logic.

## Anti-patterns

- ❌ Naming: `shared/`, `common/`, `global/`, `misc/`, `utils/`, `helpers/` as `<dominio>` value at L2. Use the business domain.
- ❌ Cross-group imports (web): `(app)/posts/page.tsx` importing from `(marketing)/_components/`. If you need it, promote.
- ❌ `app/<route>/_components/` on **mobile** — Expo Router has no private-folder convention; this creates a ghost route, not a private folder. Use `components/<feature>/` instead.
- ❌ Premature promotion: lifting to L2 at the 2nd use. Trust the duplicate.
- ❌ Splitting a compound: `Card.tsx` in L1, `Card.Header.tsx` in L0. Unmaintainable.
- ❌ JSX in `packages/shared/`: never. Only logic.
- ❌ Skipping `tsc --noEmit` after a move: silent broken imports.

## Quick reference — decision tree

### Web (Next.js, `_components/` valid)

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

### Mobile (Expo Router — app/ is routes-only, no `_components/`)

```
Need to put a component somewhere?
│
├─ Is it a UI primitive (Button, Card, Input)?
│   └─ Yes → components/ui/ (untouched after NativeWind primitives are wired)
│
├─ Is it part of the theme system (ThemeProvider, useThemeColor)?
│   └─ Yes → components/theme/
│
├─ Is it used by just one screen?
│   └─ Yes → L0 → components/<feature>/
│
├─ Is it used by 2 screens in the same feature?
│   └─ Yes → keep the single copy in components/<feature>/. Not a promotion case.
│
├─ Is it used by 2 screens across different features?
│   └─ Yes → COPY into the second feature's components/<feature>/ (tolerated duplicate). Wait.
│
├─ Is it used by 3+ screens, all reconcilable to one feature/domain?
│   └─ Yes → merge duplicates into one components/<feature>/<Component>.tsx
│
└─ Is it used by 3+ screens spanning genuinely different business domains?
    └─ Yes → L2 → components/shared/<dominio>/
```
