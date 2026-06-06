> Sources: docs/superpowers/specs/2026-06-06-folder-structure-refactor.md (canonical spec)

# Colocation rules (full spec)

(Identical content to `promote-component/references/colocation-rules.md` — kept in sync between the two skills.)

## 3 levels intra-app

```
L0  app/<route>/_components/<Component>.tsx       page-private (default)
L1  app/(group)/_components/<Component>.tsx       route-group shared
L2  components/shared/<dominio>/<Component>.tsx   globally shared
```

Plus 2 special folders:
- `components/ui/` — design system primitives (Button, Card, Input). Untouched after `shadcn add --all`.
- `components/theme/` — ThemeProvider, ModeToggle, useThemeColor.

## Rule of Three

| Stage | Action |
|---|---|
| 1st use | Create at L0 — inside the page's `_components/`. |
| 2nd use | **COPY** the file into the second page's `_components/`. Tolerated duplicate. |
| 3rd use | **Promote** — call `promote-component` skill. |

## How to choose L1 vs L2

- Same route group, 3+ uses → L1
- Different route groups, 3+ uses → L2 (ask user for `<dominio>` if not obvious)

## Compound components

A compound (`<Card>` + `<Card.Header>` + `<Card.Body>`) lives **as one unit** at a single level. Promote the whole compound together.

- ≤ 250 lines → single file with multiple exports.
- > 250 lines → folder with `index.ts` barrel.

## Cross-platform (monorepo)

`packages/shared/` accepts ONLY: types, Zod schemas, pure functions, data hooks. **No JSX**. Web and mobile UI are rewritten in each app, sharing only the logic.

## Quick decision tree

```
Need to put a component somewhere?
│
├─ Primitive (Button, Card)? → components/ui/
├─ Theme system? → components/theme/
├─ Used by 1 page? → L0 → app/<route>/_components/
├─ Used by 2 pages? → keep duplicate, wait
├─ Used by 3+ pages, same group? → L1
└─ Used by 3+ pages, cross-group? → L2 → components/shared/<dominio>/
```
