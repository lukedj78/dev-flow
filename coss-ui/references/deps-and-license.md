# Coss/UI — dependencies, requirements, and license

## Requirements

- **Tailwind CSS v4** — a hard requirement. Coss/UI does **not** work on Tailwind v3. If the project pins v3, stop and tell the user; migrating to v4 is a prerequisite, not something this skill does silently.
- **`@base-ui/react`** — Coss is built on Base UI; the dependency comes in via `@coss/ui`. This makes Coss a member of the Base-UI family (record `stack.ui_base = "base"`).
- **React + Next.js App Router** (Next 16 target for dev-flow).
- **shadcn CLI** (`pnpm dlx shadcn@latest`) for the `@coss/*` registry.

## License — read before shipping to a closed-source product

The `cosscom/coss` repo uses a **mixed license**:

- **MIT** — `apps/origin/` and `apps/ui/` (the copy-paste component source you actually pull).
- **AGPLv3** — the other directories.

Implication: the primitives you copy into your app from the MIT parts are safe for proprietary use. But **AGPLv3 is strong copyleft** — if any code sourced from the AGPL parts ends up in a product you distribute or run as a network service, the AGPL obligations (source disclosure) attach. 

**This skill surfaces the split; it does not give legal advice.** For an OSS or internal project this is usually a non-issue. For a closed-source SaaS, confirm that everything you pull comes from the MIT-licensed component source before adopting Coss. `[VERIFY]` the current license mapping against the repo `LICENSE` files — it can change.

## When Coss is the right pick

- The user wants the **Cal.com aesthetic/DX** or an **AI-first, MCP-friendly** copy-paste kit.
- A **Base UI** foundation is desired (MUI-team accessibility, headless).
- Tailwind v4 is in play (or acceptable to adopt).

## When to pick something else

- **Tailwind v3 locked** → not an option; use standard shadcn or Base UI.
- **Closed-source product with strict license hygiene** and uncertainty about which parts are MIT → prefer plain shadcn (MIT) unless you can confirm the MIT boundary.
- **Material design language / heavy data-grid needs** → MUI.
- **React Native / mobile** → NativeWind (Coss is web-only).

Related dev-flow UI choices: `design-md-to-app` (shadcn Radix|Base, standalone Base UI, MUI). Coss is the "shadcn-CLI on Base UI + Cal.com registry & tokens" option, recorded as `stack.ui = "coss"`.
