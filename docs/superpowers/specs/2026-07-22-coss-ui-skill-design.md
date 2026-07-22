# `coss-ui` — Coss/UI (Cal.com design system) as a dev-flow UI option

> Design doc — 2026-07-22. Status: **approved** (autonomous goal), building to merge.
> Part of the dev-flow skill family (web).

## What Coss/UI is (research)

**Coss/UI** (<https://coss.com/ui>, repo `cosscom/coss`, ~10.3k★) is the **official design system of Cal.com**:

- A **copy-paste-and-own** React component library — *"instead of installing a package, you get the source code."*
- Built **on top of Base UI** (`@base-ui/react`), styled with **Tailwind CSS v4**.
- **60+ components** (primitives) + **500 "particles"** (pre-built variations) + atoms.
- **Installed via the shadcn CLI** using **namespaced registry references** (`@coss/*`), or manual copy, or **over MCP** into Claude Code / Cursor.
- **Design tokens are CSS variables — the same variable names as shadcn/ui** — implemented with Tailwind, fully overridable in the global stylesheet. This is the load-bearing fact for dev-flow: Coss tokens are shadcn-compatible.

### Exact commands (verbatim from the docs)

| Purpose | Command |
|---|---|
| New project (recommended): all components + neutral colors + sidebar vars + base styles + fonts (Inter, Geist Mono) | `pnpm dlx shadcn@latest init @coss/style` |
| Existing project, full setup | `pnpm dlx shadcn@latest add @coss/style` |
| UI primitives only (Base UI) | `pnpm dlx shadcn@latest add @coss/ui` |
| Primitives + color tokens | `pnpm dlx shadcn@latest add @coss/ui @coss/colors-neutral` |
| A single component | `pnpm dlx shadcn@latest add @coss/button` |

Requires **Tailwind CSS v4** and a React project. `@base-ui/react` comes in via `@coss/ui`.

### Licensing

Repo uses a **mixed license**: **MIT** for `apps/origin/` and `apps/ui/`, **AGPLv3** for other directories. → the copy-paste primitives (`apps/ui`) are MIT-safe; anything sourced from the AGPL parts carries copyleft obligations. A skill must flag this so users don't unknowingly pull AGPL code into a proprietary product.

## Is it correct to put it in dev-flow? — analysis

**Yes**, as a **UI-library option inside the shadcn / Base-UI family**, not a new paradigm. Rationale:

1. **Same machinery dev-flow already speaks**: shadcn CLI v4 + `components.json` + CSS-variable tokens. `design-md-to-app` already scaffolds via the shadcn CLI and installs tokens from DESIGN.md through `registry.json`.
2. **Tokens are shadcn-identical** → the DESIGN.md → tokens pipeline works unchanged. Coss just supplies the **default** token set (`@coss/colors-neutral`) + a curated Base-UI component/particle registry; DESIGN.md values override them in `globals.css`.
3. **Built on Base UI**, which dev-flow already supports (`stack.ui = "base-ui"`, and `stack.ui = "shadcn"` + `stack.ui_base = "base"`). Coss ≈ "shadcn-on-Base-UI + Cal.com's registry & tokens".
4. **AI-first + MCP-available** → aligns with the ecosystem-first ethos ([[feedback_eve_ecosystem_first]]): don't reinvent a component kit, adopt a registry.

**Placement**: a new `stack.ui` value **`coss`**, owned by a dedicated skill `coss-ui`. `design-md-to-app` lists Coss as a 4th library choice and hands off to `coss-ui` for the Coss-specific wiring. It is a **deliberate** choice, gated by two caveats:
- **Tailwind v4 required** (Coss won't work on v3).
- **Mixed MIT/AGPLv3 license** — fine for OSS/internal, a real decision for closed-source products.

## Scope of the `coss-ui` skill

Owns the **Coss/UI side** of a web dev-flow project: installing/adding Coss components via the `@coss/*` registry and reconciling Coss's tokens with DESIGN.md. It **never** rewrites the generic scaffold that `design-md-to-app` owns; it composes with it. Two modes:

- **Init mode** — new/empty (or standalone) project → `shadcn init @coss/style` (Tailwind v4 + tokens + fonts), reconcile DESIGN.md tokens into `globals.css`, set `meta.json#stack.ui = "coss"` + `ui_base = "base"`, phase → `scaffolded`, `/showcase` optional.
- **Add mode** — already-scaffolded project → add primitives (`@coss/ui`), specific components (`@coss/<name>`), or particles; keep tokens reconciled. Idempotent (detect existing Coss install).

Out of scope: writing DESIGN.md (that's the image/figma-to-design-md skills), the generic Next.js scaffold internals (design-md-to-app), backend modules (module-add), mobile (RN uses NativeWind).

## Files

**Create** `coss-ui/`:
- `SKILL.md` — frontmatter (Triggers + Not for:) + Init/Add modes + DESIGN.md reconciliation + dev-flow contract + Tailwind-v4 + license caveat + DoD.
- `references/coss-registry.md` — the exact `@coss/*` commands, the namespaced-registry mechanism (`components.json#registries`), components vs particles vs atoms, MCP option. `[VERIFY]` the exact registry URL / `components.json` config against the live docs.
- `references/design-md-reconciliation.md` — Coss tokens = shadcn CSS vars → how DESIGN.md overrides them; relationship to `design-md-to-app`'s `registry.json` token install.
- `references/deps-and-license.md` — Tailwind v4, `@base-ui/react`, mixed MIT/AGPLv3, when Coss is the right/wrong choice.
- `references/contracts.md` — vendored copy of the `.workflow/` contract.
- `scripts/check_coss_state.py` — inspect a project for Coss install markers (`components.json#registries` has `@coss`, `@base-ui/react` in deps, Coss token block in `globals.css`) → report Init vs Add. Pure, unit-tested.
- `scripts/test_check_coss_state.py` — unit tests over fixture dicts.

**Modify:**
- `dev-flow/SKILL.md` — add `coss` to the stack `ui` options and note `design-md-to-app` hands off to `coss-ui`.
- `design-md-to-app/SKILL.md` — Step 2 library pick: add Coss as a 4th option with a one-line rationale + pointer to `coss-ui`.
- `install.sh`, `uninstall.sh`, `README.md`, `skills.json` (regenerated), `dist/coss-ui.skill` (regenerated).

## Definition of Done

- `check_coss_state.py` unit tests green; lint clean (skill registered, cross-refs resolve); `dist/coss-ui.skill` built; `skills.json` includes `coss-ui` (family `web`).
- Skill documents the exact verbatim `@coss/*` commands, the Tailwind-v4 requirement, and the license caveat, with `[VERIFY]` on anything not confirmable offline (exact registry URL, MCP endpoint).

## Open questions (resolved here)

1. **New `ui` value vs. shadcn sub-flag** → **new `stack.ui = "coss"`** (Coss is a whole design system, not just a registry namespace).
2. **Does `coss-ui` scaffold or only add?** → **both** (Init + Add), mirroring eve-agent's Scaffold/Capability split.
3. **Skill name** → `coss-ui`.
