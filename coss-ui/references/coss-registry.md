# Coss/UI registry cookbook

How Coss/UI is installed through the **shadcn CLI**. **Verify every command and the registry config against the live docs** (<https://coss.com/ui/docs/get-started> and each component page) before running — Coss is young and the registry URL/namespace can change. `[VERIFY]` markers below flag what could not be confirmed offline.

## The model

Coss is **copy-paste-and-own**: *"instead of installing a package, you get the source code."* You pull TSX source into your repo via the shadcn CLI, or copy it by hand. It ships three tiers:

- **primitives / atoms** — the 60+ base components (Button, Dialog, Combobox, Table, …), built on `@base-ui/react`.
- **particles** — ~500 pre-built variations/compositions.
- **style** — the whole design system bundle (components + neutral tokens + sidebar vars + base styles + fonts).

## Exact commands (verbatim from the docs — re-verify)

| Purpose | Command |
|---|---|
| **New project** (recommended): all components + neutral colors + sidebar vars + base styles + fonts (Inter, Geist Mono) | `pnpm dlx shadcn@latest init @coss/style` |
| **Existing project**, full setup | `pnpm dlx shadcn@latest add @coss/style` |
| UI **primitives** only (Base UI) | `pnpm dlx shadcn@latest add @coss/ui` |
| Primitives **+ color tokens** | `pnpm dlx shadcn@latest add @coss/ui @coss/colors-neutral` |
| A **single component** | `pnpm dlx shadcn@latest add @coss/button` |
| Any component / particle | `pnpm dlx shadcn@latest add @coss/<name>` (copy the exact command from that item's docs page) |

`npm` / `yarn` work with the same `dlx`/`add` structure.

## The `@coss` namespace

`@coss/*` is a **shadcn CLI v4 namespaced registry** reference. For `add @coss/<name>` to resolve on an existing project, the `@coss` namespace must be known to the CLI — typically via a `registries` entry in `components.json`:

```jsonc
// components.json — registry base URL confirmed 2026-07 (re-check if it changes); exact config below still [VERIFY]
{
  "registries": {
    "@coss": "https://coss.com/ui/r/{name}.json"
  }
}
```

The registry base URL `https://coss.com/ui/r/{name}.json` was **re-confirmed live 2026-08-12** (HTTP 200 on `button.json`) — re-check if it changes. `init @coss/style` on a fresh project is expected to set this up for you. `[VERIFY]` the exact `components.json#registries` shape above and whether the namespace is auto-registered vs. needs the manual entry.

## AI-first claim

Coss markets itself as "built for developers and AI" and ships an `npx skills add cosscom/coss` agent-skills installer, but no official MCP server for Claude Code/Cursor is documented — do not assume one exists or instruct users to "pull components over MCP".

## Prereqs

- **Tailwind CSS v4** (hard requirement — Coss does not work on v3).
- `@base-ui/react` — comes in via `@coss/ui`.
- A React project (Next.js App Router for dev-flow).

## Idempotency

Before `add @coss/<name>`, check whether the component already exists in `components/ui/` (and whether `@coss` is already in `components.json#registries`). Re-adding is a no-op — don't duplicate. `scripts/check_coss_state.py` reports the install state for the Init-vs-Add decision.
