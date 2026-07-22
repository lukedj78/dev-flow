---
name: coss-ui
description: 'Set up or extend a Next.js web app with Coss/UI — the official Cal.com design system, built on Base UI + Tailwind CSS v4, installed through the shadcn CLI via the namespaced `@coss/*` registry (copy-paste-and-own source). Two modes: Init (scaffold a new/empty project with `shadcn init @coss/style` — components, neutral tokens, sidebar vars, Inter/Geist fonts) and Add (pull primitives `@coss/ui`, single components `@coss/<name>`, or particles into an already-scaffolded project). Because Coss tokens are the SAME CSS variables as shadcn/ui, DESIGN.md tokens override them directly in globals.css. Integrates with the dev-flow contract: sets `meta.json#stack.ui = "coss"` (+ `ui_base = "base"`). Triggers: "usa Coss/UI", "coss.com/ui", "Cal.com design system", "aggiungi un componente Coss", "init @coss/style", "scaffold con Coss UI", or dev-flow routing when `stack.ui = "coss"`. Not for: writing the DESIGN.md (use figma-to-design-md / image-to-design-md), the generic Next.js scaffold internals (design-md-to-app owns those), backend modules (module-add), or React Native (RN uses NativeWind, not Coss). Caveats: requires Tailwind CSS v4 and carries a mixed MIT/AGPLv3 license — see references/deps-and-license.md.'
---

# coss-ui — Coss/UI (Cal.com design system) for a dev-flow project

This skill owns the **Coss/UI side** of a web project: installing and extending Coss components (the Cal.com design system on **Base UI** + **Tailwind v4**) through the **shadcn CLI** `@coss/*` registry, and keeping Coss's tokens reconciled with the project's `DESIGN.md`. It **composes with** `design-md-to-app` (which owns the generic Next.js scaffold) — it does not re-implement it.

## The one rule that matters most

**Never invent the Coss commands or registry.** The source of truth is the live docs at <https://coss.com/ui/docs> (get-started + each component page shows its exact `pnpm dlx shadcn@latest add @coss/<name>` command) and the repo `cosscom/coss`. Confirm the exact command, the `components.json#registries` config for the `@coss` namespace, and the current registry URL **before** running anything. Coss is young; treat this skill as the workflow + conventions, not a frozen copy of the API. Anything marked `[VERIFY]` must be checked against the live docs first.

## Why Coss fits dev-flow (and when to pick it)

Coss/UI rides the **same machinery** dev-flow already uses: shadcn CLI v4 + `components.json` + **CSS-variable tokens with the same names as shadcn/ui**. So the DESIGN.md → tokens pipeline works unchanged; Coss just supplies the default token set (`@coss/colors-neutral`) plus a curated Base-UI component/particle registry. It is a UI-library choice **inside the shadcn / Base-UI family**, recorded as `stack.ui = "coss"` (with `ui_base = "base"`, since Coss is built on Base UI).

Pick Coss when the user wants the Cal.com aesthetic/DX, a Base-UI foundation, and an AI-first copy-paste kit. **Two caveats make it a deliberate choice, not a default:**

- **Tailwind CSS v4 is required** — Coss does not work on v3.
- **Mixed license**: MIT for the copy-paste primitives (`apps/ui`, `apps/origin`), **AGPLv3** elsewhere. Fine for OSS/internal; a real decision for closed-source products. See `references/deps-and-license.md`.

## Preconditions

- `stack.framework` is `"next"` (App Router) or `"monorepo"` (operate in `apps/web/`). Next.js 16 target, per dev-flow.
- **Tailwind CSS v4** available (or being set up). If the project pins Tailwind v3, stop and flag it — Coss needs v4.
- The shadcn CLI is usable (`pnpm dlx shadcn@latest`). No `components.json` is required up front for `init @coss/style`; for `add @coss/*` on an existing project, the `@coss` registry namespace must be resolvable (see `references/coss-registry.md`).

## Read state, then pick a mode

Run `python scripts/check_coss_state.py <project-root>` (or inspect manually). It reports:
- **No app yet / no Coss markers** → **Init mode**.
- **App scaffolded, Coss already installed** (`@coss` in `components.json#registries`, `@base-ui/react` in deps, Coss token block in `globals.css`) → **Add mode**.

Do **one** logical operation per invocation, then stop. Both modes are idempotent — re-adding an existing component is detected and skipped.

## Init mode (new / empty project)

Goal: a runnable app with Coss/UI installed and its tokens reconciled to `DESIGN.md`.

1. Read `node_modules`/docs and confirm the current init flow (`references/coss-registry.md`). Confirm **Tailwind v4**.
2. Scaffold the framework if absent — hand the generic Next.js scaffold to `design-md-to-app` (dev-flow contract), OR, for a Coss-first empty project, run the recommended one-shot:
   ```bash
   pnpm dlx shadcn@latest init @coss/style
   ```
   This installs all UI components, the neutral color system, sidebar variables, base styles, and the default fonts (Inter, Geist Mono). `[VERIFY]` the exact behavior against the live get-started page.
3. **Reconcile with `DESIGN.md`** (if present). Coss tokens are the same CSS variables as shadcn/ui, so DESIGN.md values override Coss's neutral defaults **in `globals.css`** — do not fork Coss's token structure, override its values. Follow `references/design-md-reconciliation.md`; this is the exact `registry.json` token-install path `design-md-to-app` already uses, with `@coss/colors-neutral` as the base being overridden.
4. Wire the dark/light toggle and the rest of the standard scaffold via `design-md-to-app`'s mandatory steps (theme toggle, error/loading boundaries, folder convention) — Coss primitives slot into `components/ui/` like any shadcn primitive.
5. Update `.workflow/meta.json`: `stack.ui = "coss"`, `stack.ui_base = "base"`, `stack.css_variables = true`, bump `phase` to `scaffolded` (only forward), append `history` (`{ "skill": "coss-ui", "action": "init" }`).

## Add mode (existing scaffolded project)

Goal: add ONE thing — a primitive set, a component, or particles — idempotently.

1. Ensure the `@coss` registry is resolvable in `components.json` (`references/coss-registry.md`). If not configured, add it once.
2. Add exactly what was asked, using the verbatim command from the component's docs page:
   - primitives: `pnpm dlx shadcn@latest add @coss/ui`
   - one component: `pnpm dlx shadcn@latest add @coss/<name>` (e.g. `@coss/button`, `@coss/combobox`)
   - tokens only: `pnpm dlx shadcn@latest add @coss/colors-neutral`
   - particles: per the particle's docs command.
3. Keep tokens reconciled — if the add pulled a fresh token block, re-apply the DESIGN.md overrides (`references/design-md-reconciliation.md`).
4. **Prefer the Coss/Base-UI primitive over hand-rolled components** — the same mandate `design-md-to-app` enforces for shadcn: scan `components/ui/*` before authoring anything custom.
5. Append `history` (`{ "skill": "coss-ui", "action": "add-<name>" }`). No phase bump.

## Definition of Done (per run)

- **Init**: `pnpm --filter web lint typecheck build` (or the app's equivalent) exits 0; the app runs; Coss primitives are in `components/ui/`; `globals.css` carries the DESIGN.md-reconciled tokens; `meta.json#stack.ui = "coss"`.
- **Add**: the requested component/primitive/particle is present and imports resolve; a re-run detects it and skips (idempotent).
- Script stays green: `cd coss-ui/scripts && python3 -m unittest test_check_coss_state`.

## What this skill does NOT do

- Doesn't write the `DESIGN.md` (use `figma-to-design-md` / `image-to-design-md`).
- Doesn't own the generic Next.js scaffold internals (theme toggle, error boundaries, folder convention) — those are `design-md-to-app`'s; this skill composes with them.
- Doesn't wire backend modules (`module-add`) or build React Native (RN uses NativeWind, not Coss).
- Doesn't silently ship AGPLv3 code into a closed-source product — it surfaces the license split first.
- Doesn't work on Tailwind v3.

## Reference files

- `references/coss-registry.md` — exact `@coss/*` commands, the namespaced-registry mechanism, components vs particles vs atoms, AI-first claim (no official MCP server documented).
- `references/design-md-reconciliation.md` — Coss tokens = shadcn CSS vars; how DESIGN.md overrides them; tie-in to `design-md-to-app`'s `registry.json` install.
- `references/deps-and-license.md` — Tailwind v4, `@base-ui/react`, the MIT/AGPLv3 split, when Coss is the right/wrong pick.
- `references/contracts.md` — the `.workflow/` dev-flow contract (vendored copy).
