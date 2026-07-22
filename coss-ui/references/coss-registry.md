# Coss/UI registry cookbook

How Coss/UI is installed through the **shadcn CLI**. **Verify every command and the registry config against the live docs** (<https://coss.com/ui/docs/get-started> and each component page) before running — Coss is young and the registry URL/namespace can change. `[VERIFY]` markers below flag what could not be confirmed offline.

## The model

Coss is **copy-paste-and-own**: *"instead of installing a package, you get the source code."* You pull TSX source into your repo via the shadcn CLI (or copy it by hand, or pull it over MCP into Claude Code / Cursor). It ships three tiers:

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
// components.json  — [VERIFY] exact URL/shape against the live docs
{
  "registries": {
    "@coss": "https://coss.com/ui/r/{name}.json"
  }
}
```

`init @coss/style` on a fresh project is expected to set this up for you. `[VERIFY]` the exact registry base URL (`https://coss.com/ui/r/...` was **not** confirmed offline) and whether the namespace is auto-registered vs. needs the manual `components.json` entry above.

## MCP option (AI-first)

Coss is "built for developers and AI": components can be pulled **over MCP** directly into Claude Code / Cursor. If a Coss MCP server is connected in the session, prefer it for discovery + insertion (it hands you the current source without guessing commands). `[VERIFY]` the MCP server URL/config against the live docs — it was not confirmed offline.

## Prereqs

- **Tailwind CSS v4** (hard requirement — Coss does not work on v3).
- `@base-ui/react` — comes in via `@coss/ui`.
- A React project (Next.js App Router for dev-flow).

## Idempotency

Before `add @coss/<name>`, check whether the component already exists in `components/ui/` (and whether `@coss` is already in `components.json#registries`). Re-adding is a no-op — don't duplicate. `scripts/check_coss_state.py` reports the install state for the Init-vs-Add decision.
