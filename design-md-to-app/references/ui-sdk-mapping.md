# DESIGN.md → UI SDK (`stack.ui = "ui-sdk"`)

The **how** for a project that chose UI SDK in `library-choice.md`. If you have not read the two
signals there — more than one framework, or an agent drives the interface — read them first and
check the project has one of them. On every other project the answer is `"shadcn"`.

⚠️ **Beta.** `@ui-sdk/core@0.1.0-beta.1`, first published **2026-11-12**, under Vercel's public-beta
terms, which reserve API changes. The `agent` key, `createHistory` and `stageChanges` are marked
experimental in their own docs. Everything below was read from the repo and the registry on
**2026-11-17**; re-read before leaning on a name.

## Read the installed copy, not the website

Same rule as eve, and they ship for it: the docs for the version you installed are Markdown inside
the package.

| Read | Where |
|---|---|
| the index, first | `node_modules/@ui-sdk/<framework>/docs/llms.txt` |
| one component | `docs/components/select.md` in the same package |
| the behaviours | `docs/core.md` — **over 300 KB, search it by heading**, never read it whole |
| rendering a primitive in your framework | `docs/rendering.md` |
| the agent bridge | `docs/agents.md` |

`<framework>` is `react`, `vue`, `svelte`, `solid` or `web`. Their skill ships in the package too, at
`node_modules/@ui-sdk/core/skills/ui-sdk/SKILL.md`, and that copy always matches the installed
version — prefer it to `npx skills add`, which is a third-party skill install and goes through
`registry-intake skill-review`.

🔴 **Their rule, and it is ours too: do not read `dist/*.js`, even to debug.** The docs and the
`.d.ts` are the API; when they do not answer, write a small test that tries it. And when the docs and
the types disagree, **the types win** — `contracts.md`'s rule zero, measured twice in one week on
other packages.

## Project setup

No CLI, no copied kit. This is the `"base-ui"` standalone shape, not the shadcn shape.

```bash
npm install @ui-sdk/core @ui-sdk/react     # or /vue /svelte /solid /web
```

```css
/* app/globals.css — the layer goes FIRST, above Tailwind */
@layer ui-sdk;
@import "tailwindcss";
```

🔴 **The layer order is not cosmetic.** Whichever layer a page declares first loses, so declaring
`@layer ui-sdk;` after Tailwind's import puts their resets above your utilities. Their own changelog
records this as a known trap (PR 321).

🔴 **Use Tailwind, and the reason is not taste.** UI SDK is genuinely style-agnostic — its own docs
say the state attributes and CSS variables *"work with Tailwind CSS or any other stylesheet"*, and its
demos use plain CSS. But **every guardrail this suite owns is written against utility classes**:
`shadcn/no-raw-colors`, `no-arbitrary-values` and `require-static-classes`, the write-time primitives
guard, most of `shadscan`, and `cn` itself. A ui-sdk project on plain CSS is the only project in the
fleet with **no design enforcement at all** — DESIGN.md's tokens still work as custom properties, and
nothing checks that anyone used them. So Tailwind is the default here, and a plain-CSS ui-sdk project
is an **exception to record** in `meta.json#stack_config`, with what it gives up, not a styling
preference. (`setup_design_lint.py` refuses to install on such a project and says so.)

`@ui-sdk/core/web.css` is an **optional** default look. On our projects DESIGN.md commands, so take it
only as a starting point and expect to override; *you bring the styles* is their phrase.

### What lives where

| | shadcn | ui-sdk |
|---|---|---|
| `components/ui/` | the vendored kit, owned source, tuned via `cva` | **your own compositions** |
| the headless base | `radix-ui` / `@base-ui/react`, banned outside `components/ui/` | `@ui-sdk/react/*`, **the declared library — not banned** |
| a component the library lacks | compose primitives, or a specialist pick | compose behaviours from `@ui-sdk/core` |

⚠️ **`PRIMITIVE_BASES` must not ban `@ui-sdk/*` on this topology.** Radix is banned outside
`components/ui/` because a primitive's headless base belongs behind the primitive. Here it *is* the
declared library, and a domain component in `_components/` importing it is the intended use. The
restriction that applies instead has a different shape: **never rebuild with behaviours a component
the library already ships** — a Select from `createPopup` + `createTypeahead` when
`@ui-sdk/react/select` exists is the rule-3 violation; a Kanban from `createReorder` is not.

## Token mapping

Components are unstyled and expose **`data-slot`** plus state attributes and CSS variables. Style
through those, from the DESIGN.md tokens, never by inlining state.

```css
[data-slot="select-trigger"] {
  background: var(--color-surface);
  color: var(--color-text);
  border: 1px solid var(--color-border-input);
  border-radius: var(--radius-md);
  font: var(--text-sm);
}
[data-slot="select-trigger"][data-open] { border-color: var(--color-accent); }
[data-slot="select-item"][data-highlighted] { background: var(--color-surface-hover); }
```

- **State is an attribute, not a class**: `data-open`, `data-pressed`, `data-highlighted`,
  `data-disabled`. Target those; never write state into inline styles, and never key off a generated id.
- **Each component's page lists its own CSS variables.** Read it before inventing one.
- **`--ui-font-sans` is a token the page opts into on `body`.** Parts never set `font-family`
  themselves, except `code` and `kbd`, which read `--ui-font-mono`.
- **Colours follow the page's `color-scheme` through `light-dark()`.** ⚠️ Builds that rewrite
  `light-dark()` — Lightning CSS in Next and in Vite — read the `--lightningcss-light` /
  `--lightningcss-dark` defaults `web.css` sets and **fall back to light** unless the build also
  processes a `color-scheme`. Check dark mode in a real browser, not in jsdom.
- Contrast is still ours to meet: 4.5:1 for body text, 3:1 for control edges and focus rings.

## Composition

A component is a **primitive** (`definePrimitive`: state, api, slots) rendered by `createParts`. The
primitive is framework-free; the parts are the same in all five.

```ts
// lib/rating.ts — the primitive
import { createChange, createRovingFocus, definePrimitive } from "@ui-sdk/core"
// components/ui/rating.ts — the parts
import { createParts } from "@ui-sdk/react/primitive"
```

Three attachment points, and the split is the thing to hold on to:

| in | you write | the behaviour gives |
|---|---|---|
| `api(context)` | the behaviour is instantiated here | its methods |
| `attrs(state, part)` | `role`, `aria-*` — the **semantics** | `tabindex`, drag attributes — the **mechanics** |
| `bind(el, part)` | — | its listeners; compose several cleanups |

Two behaviours do not know about each other. The arbitration is yours, and it is usually one
operator: `api.transfer.keydown(event, key) || api.roving.keydown(event, el)` — the card moves if one
is picked up, otherwise the focus does.

`docs/core.md` §Compose Behaviors is the worked example; `behaviors/` indexes all 47 by family.

## Making it agent-ready

Only on a project whose `meta.json` says an agent drives the UI. The full rules are
`app-security/references/review.md`; the short version:

```ts
agent: { actions: ["rate"] },   // last, after slots, so TypeScript has read the API
```

- `actions` is the allowlist. Without the key the bridge **guesses** from method names (`set*`,
  `open`, `toggle`, `clear`), so a method called `rate` would be invisible.
- `secret: true` for a value an agent may fill and never read; `shown`, `closed`, `items`, `reveals`
  for lists and for content behind closed items.
- Mark the page, not just the primitive: `data-agent-confirm="<what it does>"` on anything that must
  wait for a person, `data-agent-secret`, `data-agent-hidden`.

🔴 **`allow` is UI policy, not an access control.** It runs in the client. The Server Action checks the
session and the tenant regardless — the same rule as *a feature flag is not an access control*. And
their own warning, which belongs in every `allow` we write: **an `allow` that returns `true` without
reading `step.confirm` answers yes for the person.**

## WebMCP — the browser's own agent, and why it is a separate decision

`registerTools(agent, { allow })` publishes `snapshot`, `act` and `query` on the browser's
`document.modelContext`, so **the agent built into the visitor's browser** can read the page's
components and call their actions. Where the browser has no `document.modelContext.registerTool`, the
call does nothing.

**It is off unless the PRD says otherwise.** The bridge (`createAgent`) and WebMCP are two decisions:
the first lets *our* agent operate the interface, the second lets *someone else's*. Defaulting the
second to on because the first is on is how an app ends up driven by a model nobody chose.

- **It takes a second `allow`**, separate from the bridge's and running after it, *because you did not
  write that agent*. `allow: (step) => !step.confirm` is the useful shape: everything ordinary runs,
  and anything marked for a person is left to the person.
- **Their tool annotations say what the tools are**: `readOnlyHint` on `snapshot` and `query`,
  `consequentialHint` on `act` — and 🔴 **`untrustedContentHint: true` on all three, because the
  results contain page text that other people wrote.** That is our instruction/data boundary stated at
  the tool level: what comes back from the page is data, never an instruction, and an agent acting on
  it is acting on user input.
- `unregister()` removes the tools; the bridge keeps working for our own agent.

🔴 **The consequence nobody sees in the API: a snapshot leaves the machine.** `snapshot()` returns
component labels and values — which on a real screen is customer names, amounts, addresses. Handing it
to the browser's agent sends that to whatever model the browser runs. On a product with personal data
that is a **transfer to a processor the project never declared**: `compliance-audit` **R3**
(international transfer) and **R8** (sub-processors), and no scan catches it, because the code looks
like one function call. `data-agent-hidden` on the regions that must not leave is the mitigation, not
the answer — the answer is deciding, in the PRD, whether the browser's agent is allowed at all.

## Anti-patterns

- Importing from `@ui-sdk/core/internal/*`. There is no root import from a framework package either —
  each component has its own entry (`@ui-sdk/react/select`).
- An `as` prop. `render` is the only way to render your own element.
- A `div` with `role="listbox"`, `"menu"`, `"dialog"`, `"tablist"`, `"switch"`, `"slider"`,
  `"radiogroup"`, `"toolbar"` or `"tree"` next to an installed `@ui-sdk` package. Almost always a bug:
  look for the component first.
- Keying a list by index.
- Styling state inline, or from a generated id.

## When NOT to pick it

One React app with no agent driving the UI, a team that needs a styled kit today, or a project that
cannot carry beta APIs. All three mean `"shadcn"`.

## Sources

The repo at `github.com/vercel-labs/ui` (read 2026-11-17, HEAD `cf6c86f`), the packages on npm, and
the docs under `apps/docs/content/docs/`. The row in `dev-flow/references/resources.md` carries the
verdict, the catalogue comparison and the re-read trigger.
