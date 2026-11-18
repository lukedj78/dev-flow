# DESIGN.md → UI SDK (`stack.ui = "ui-sdk"`)

The **how** for a project that chose UI SDK in `library-choice.md`. If you have not read the two
signals there — more than one framework, or an agent drives the interface — read them first and
check the project has one of them. On every other project the answer is `"shadcn"`.

⚠️ **Beta, and moving fast.** First published **2026-11-12** at `0.1.0-beta.1`; the copy measured for
this file is **`@ui-sdk/core@0.1.0-beta.6`** (Apache-2.0), installed 2026-11-19 — **six prereleases in
seven days**. Vercel's public-beta terms reserve API changes, and the `agent` key, `createHistory` and
`stageChanges` are marked experimental in their own docs. The prose below was written against the repo
on 2026-11-17 and **re-measured against the installed package on 2026-11-19**: all 12 named identifiers
(`definePrimitive`, `createParts`, `createChange`, `createRovingFocus`, `createPopup`, `createTypeahead`,
`createReorder`, `createHistory`, `stageChanges`, `createAgent`, `registerTools`, `agentTools`) are still
declared in the `.d.ts`, and every `data-*` marker and CSS variable named here is still in the shipped
docs. Two doc paths had moved and are corrected below. **At this cadence, re-measure rather than trust
this block** — the fastest check is the identifier sweep, not a read.

## Read the installed copy, not the website

Same rule as eve, and they ship for it: the docs for the version you installed are Markdown inside
the package.

🔴 **Which package a file lives in is the thing to get right, and `llms.txt` is not an index.** Both
mistakes were in this table until measured against the installed beta.6 on 2026-11-19:

| Read | Where, exactly |
|---|---|
| one component | `@ui-sdk/<framework>/docs/components/select.md` — the **framework** package |
| rendering a primitive | `@ui-sdk/<framework>/docs/rendering.md` — the **framework** package, not core |
| the behaviours | `@ui-sdk/core/docs/core.md` — **8,084 lines / 387 KB. Search it by heading; never read it whole** |
| the agent bridge | `@ui-sdk/core/docs/agents.md` (76 KB) — `@ui-sdk/react/docs/agents.md` also exists |
| the default stylesheet | `@ui-sdk/core/web.css`, which the export map resolves to `dist/web.css` |

⚠️ **`docs/llms.txt` is not a table of contents.** Its first line says *"ui-sdk Core docs, as one
file"*, and it is **8,084 lines — the same length as `core.md`**. Opening it "first, for the index"
reads 387 KB of prose into context. There is no index file; go to the page you need.

`<framework>` is `react`, `vue`, `svelte`, `solid` or `web`. Their skill ships in the package too, at
`node_modules/@ui-sdk/core/skills/ui-sdk/SKILL.md` (6.4 KB), and that copy always matches the installed
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

**One allocation, upward: eight behaviours are covered exactly by four primitives, and the four by
one domain component. The seams of the middle tier fall in the gaps of the lower one; the top tier
has no seam, and is the only tier you author.** That sentence is the whole model, and the drawing
below is the same sentence for a reader who prefers to look.

![The three tiers of UI SDK: eight behaviour units covered exactly by four primitives, the four
covered by one domain component, with the top tier hatched as the only one authored here.](../assets/ui-sdk-layers.svg)

> ⚠️ **The drawing is for a person reading this file on GitHub.** An agent reads the sentence above
> and skips the image, and this repo's site generator does not render images either — so the picture
> never carries a fact the prose does not. Composed under
> [Plotter](https://github.com/pasqualevitiello/plotter)'s grammar (MIT, `resources.md` has the row)
> and passed by its `check.py`; it names `Cal Sans` and falls back to the host's sans-serif, since the
> font is not vendored here.


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
components and call their actions.

⚠️ **Today it reaches almost nobody — which is the reason to decide it now, not later.**
`document.modelContext` is **not supported natively by any major browser**. It is an early preview in
Chromium: **146.0.7672.0 or newer** *and* the `chrome://flags/#enable-webmcp-testing` flag, against a
Community Group draft that is not standards-track (checked 2026-11-18). So the code ships inert and
starts working when a flag flips somewhere you do not control. Feature-detect with
`if ('modelContext' in document)`, and read the next paragraph as a decision about the future, not a
measurement of today.

**It is off unless the PRD says otherwise.** The bridge (`createAgent`) and WebMCP are two decisions:
the first lets *our* agent operate the interface, the second lets *someone else's*. Defaulting the
second to on because the first is on is how an app ends up driven by a model nobody chose.

- **It takes a second `allow`**, separate from the bridge's and running after it, *because you did not
  write that agent*. `allow: (step) => !step.confirm` is the useful shape: everything ordinary runs,
  and anything marked for a person is left to the person.
- **Their tool annotations say what the tools are**: `readOnlyHint` on `snapshot` and `query`,
  `consequentialHint` on `act`, and `untrustedContentHint: true` on all three. ⚠️ **That third one is
  their choice, and a conservative one** — the annotation's own meaning is narrower: it marks a tool
  whose result is content **the site does not control**, such as user-generated text or a third party's
  API response, and WebMCP's own example sets it `false` for first-party data. UI SDK cannot know which
  your page is, so it marks all three. 🔴 **Our instruction/data boundary does not rest on it**: what
  comes back from the page is data and never an instruction, whoever wrote it, and an agent acting on it
  is acting on user input. The annotation tells the other agent; keeping the rule is ours.
- **`consequentialHint` asks, it does not gate.** It invites the agent to confirm, blocks nothing on its
  own, and a browser older than the hint never prompts at all. Keep whatever in-app confirmation the
  action already warranted — the same rule as `allow` being UI policy.
- **There is no `unregister()` method — `registerTools` returns an unnamed function.** Read from the
  installed types (`core/dist/page/agent/agent.d.ts`, beta.6): `registerTools(agent, { allow }): () => void`.
  The name is whatever the caller binds it to, and their own docs bind it to HMR disposal:
  ```ts
  const unregister = registerTools(agent, { allow })
  if (import.meta.hot) import.meta.hot.dispose(unregister)
  ```
  ⚠️ **What that function does inside is still unmeasured, and the way to measure it is not to read it.**
  The browser method it would be the obvious wrapper for is **gone**: WebMCP removed `unregisterTool()`,
  `provideContext()` and `clearContext()`, and deprecated `navigator.modelContext` in Chromium 150; a
  tool is withdrawn by aborting an `AbortSignal` passed at registration. Their docs do not say which
  path they take, `dist/*.js` is not ours to read, so the answer is the three-line test — on the first
  project that ships this, in a Chromium with the flag:
  ```js
  const un = registerTools(agent, { allow: () => true })
  document.modelContext.getTools()   // the three are there
  un(); document.modelContext.getTools()   // still there?
  ```
  **If they are still there, it is a leak you believe you closed**: `snapshot` keeps reading the page
  after you navigated away from the data. The HMR binding is weak evidence it works — a dead cleanup
  would break their own quickstart on every save — but evidence is not the test.
- **`exposedTo` is a WebMCP capability their wrapper does not surface, and that is good news.** The raw
  API can expose a tool to **named origins in the frame tree**, through a mutual opt-in with
  `getTools({ fromOrigins: [...] })`. ⚠️ Measured on the installed beta.6: **`exposedTo` appears in zero
  files** of `@ui-sdk/core` and `@ui-sdk/react`, docs and types alike — so `registerTools` registers
  same-origin only and there is no cross-origin surface to declare. It becomes ours to think about only
  if they add the option, or if a project calls `document.modelContext.registerTool` directly instead of
  going through the bridge. Then it is the snapshot declaration again, one frame across:
  `compliance-audit` **R8**, and it matters wherever `iframe-canvas` puts our UI in a frame.

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

The **platform** facts in §WebMCP — the preview status, the Chromium version and flag, the removed
`unregisterTool()`/`provideContext()`/`clearContext()`, `exposedTo` and the annotation definitions —
are from `GoogleChrome/modern-web-guidance` (`guides/webmcp/`, read 2026-11-18, HEAD `64a6d70`,
CC-BY 4.0), not from UI SDK, which describes its own wrapper. When the two disagree about what the
browser does, the platform source wins; when they disagree about what `registerTools` does, read the
installed `.d.ts`.

**Re-measured 2026-11-19 against `@ui-sdk/core@0.1.0-beta.6` installed in `~/projects/ui-sdk-search`
and `~/projects/fornitori`** — docs and `.d.ts` only, never `dist/*.js`. That pass is what found the
two moved doc paths, `llms.txt` not being an index, `exposedTo` being absent from their wrapper, and
`unregister()` not being a method. 🔴 **The lesson for the next reader of this file: three of those
four were written from the vendor's own docs about the vendor's own wrapper, and the installed package
contradicted them inside two days.** A beta on six prereleases in a week is measured, not cited.
