# Coss/UI registry cookbook

How Coss/UI is installed through the **shadcn CLI**. **Verify every command against the live docs** (<https://coss.com/ui/docs/get-started>, 200 on 2026-08-26) before running — Coss is young and the registry URL/namespace can change. The registry *shape* below (base URL, namespace chain, item counts, fonts) was confirmed against `coss.com/ui/r/*.json` on **2026-08-26**; what remains unverifiable offline is the CLI's own behaviour, i.e. whether `init` writes the `registries` entry for you.

## The model

Coss is **copy-paste-and-own**: *"instead of installing a package, you get the source code."* You pull TSX source into your repo via the shadcn CLI, or copy it by hand. It ships three tiers:

Counted off `https://coss.com/ui/r/registry.json` on **2026-08-26** — **577 items**, and the tiers map
onto the item `type` exactly:

| Tier | `type` | Count |
|---|---|---|
| **primitives / atoms** — Button, Dialog, Combobox, Table, … on `@base-ui/react` (npm `1.7.0`) | `registry:ui` | **56** (of which `@coss/ui` pulls **54**) |
| **particles** — pre-built variations/compositions | `registry:block` | **508** |
| **style** — the design-system bundle | `registry:style` | 2 (`style`, `colors-neutral`) |
| fonts · lib · hooks | `registry:font` / `:lib` / `:hook` | 3 / 6 / 2 |

("60+ base components" was a rounding in the wrong direction — it is 56 published, 54 bundled.)

## Exact commands (verbatim from the docs — re-verify)

| Purpose | Command |
|---|---|
| **New project** (recommended): all components + neutral colors + sidebar vars + base styles + **three** font slots (below) | `pnpm dlx shadcn@latest init @coss/style` |
| **Existing project**, full setup | `pnpm dlx shadcn@latest add @coss/style` |
| UI **primitives** only (Base UI) | `pnpm dlx shadcn@latest add @coss/ui` |
| Primitives **+ color tokens** | `pnpm dlx shadcn@latest add @coss/ui @coss/colors-neutral` |
| A **single component** | `pnpm dlx shadcn@latest add @coss/button` |
| Any component / particle | `pnpm dlx shadcn@latest add @coss/<name>` (copy the exact command from that item's docs page) |

`npm` / `yarn` work with the same `dlx`/`add` structure.

## The `@coss` namespace

`@coss/*` is a **shadcn CLI v4 namespaced registry** reference. For `add @coss/<name>` to resolve on an existing project, the `@coss` namespace must be known to the CLI — typically via a `registries` entry in `components.json`:

```jsonc
// components.json — base URL and shape both confirmed live 2026-08-26
{
  "registries": {
    "@coss": "https://coss.com/ui/r/{name}.json"
  }
}
```

Base URL re-confirmed **2026-08-26**: `button.json`, `style.json` and `registry.json` all 200.

**The namespace is not optional, and the registry proves it.** `@coss/style`'s own
`registryDependencies` are `["utils", "@coss/ui", "@coss/fonts"]`, and `@coss/ui`'s are 54 entries all
written `@coss/<name>`. So the resolution chain is `style → @coss/ui → 54 × @coss/*`: unless the CLI can
resolve `@coss`, the very first install fails on its own dependencies. `init @coss/style` writing the
entry for you is the expected path on a fresh project; on an **existing** one, add it yourself first.

What `@coss/style` actually brings, read off the item: npm deps `@base-ui/react`,
`class-variance-authority`, `lucide-react`; `cssVars` under `theme` / `light` / `dark`; and **no files
of its own** — it is a manifest, everything arrives through its dependencies.

## AI-first claim

Coss markets itself as "built for developers and AI" and ships an `npx skills add cosscom/coss` agent-skills installer, but no official MCP server for Claude Code/Cursor is documented — do not assume one exists or instruct users to "pull components over MCP".

## Prereqs

- **Tailwind CSS v4** (hard requirement — Coss does not work on v3).
- `@base-ui/react` — comes in via `@coss/ui`.
- A React project (Next.js App Router for dev-flow).

## Idempotency

Before `add @coss/<name>`, check whether the component already exists in `components/ui/` (and whether `@coss` is already in `components.json#registries`). Re-adding is a no-op — don't duplicate. `scripts/check_coss_state.py` reports the install state for the Init-vs-Add decision.
