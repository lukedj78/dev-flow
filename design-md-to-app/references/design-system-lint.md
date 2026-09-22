# Design-system lint — `@shadcn/lint`

> Sources: [shadcn-ui/lint](https://github.com/shadcn-ui/lint) README, `SETUP.md`, `docs/adoption.md`,
> `docs/how-it-works.md`, `docs/rules/no-raw-colors.md` · npm `@shadcn/lint@0.1.0` (the only published
> version, 2026-09-14) · peer `eslint >=9.30.0` · `node >=20.19` · Tailwind v4 · **shadcn/ui not
> required**, so it applies to `stack.ui` = `shadcn`, `base-ui` and `coss` alike. Written **2026-09-14**.
> Everything marked *verified* below was run, not read.

## It is automated — use the script

```bash
python3 design-md-to-app/scripts/setup_design_lint.py <project-root>          # install, wire, cap, record
python3 design-md-to-app/scripts/setup_design_lint.py <project-root> --check  # verify only
```

`design-md-to-app` runs it at Step 4.10; `monorepo-bootstrap` runs it at Step 8, after the workspace
is installed. `dev-flow/scripts/update_meta.py set-phase scaffolded` runs `--check` and **refuses the
phase** until it passes or `stack.design_lint = "none"` is recorded with
`stack_config.design_lint_reason`; `show_state.py` flags projects that are already past it. The rest
of this file is the evidence each rule in the script was written from.

What the script was run against before it was committed, from scratch each time:

| Project | Topology | Result |
|---|---|---|
| gym-saas at the commit before its lint was added | shadcn monorepo, `only-warn` | caps 0 / 0, lint green, identical to the hand-made commit; second run changes nothing |
| a copy of notarius-crm | single app, no `only-warn`, already built | 113 findings, cap 114, 2 pre-existing errors reported and not blocked on |
| the same copy set to `design_extracted` | fresh single app | **refused** — 113 findings listed, nothing recorded, `--check` still failing |
| a web+mobile fixture (notarius as `apps/web`) | `apps/web` as a single app inside a workspace | installed with `--filter`, same numbers as the copy |
| desko | web app with no ESLint at all | `--check` names the cause: `next lint`, which Next 16 removed |

Running it on the single app turned up two things the hand-wired projects had not: shadcn's
`sidebar.tsx` fails `react-hooks/purity` (`Math.random` during render) under `eslint-config-next`,
and the first version installed and wired the plugin **before** discovering pre-existing errors, then
exited — leaving a project wired but uncapped and unrecorded. Pre-existing errors on an existing app
are now reported and the run continues; only a fresh scaffold is refused, and only after reporting.

`design-md-to-app/scripts/test_setup_design_lint.py` (18 tests, no network, run in CI) covers the
decisions: topology detection, where the spread lands and that it lands once, that the cap is
replaced not appended, that the policy never allows `shadow-*` or turns raw colours off in the
component directory, and that `set-phase` refuses an unwired app — including a jump straight past
`scaffolded` — while letting a reasoned opt-out, other stacks and later transitions through.

## Why it exists in this skill

This skill writes the theme — colours, the type scale, radii — from DESIGN.md, then hands the app to
agents that write classes against it. Nothing used to check that they did. A real project produced by
this pipeline ended up with **zero `--text-*` tokens and 531 `text-[…]` literals**, found only by
running this linter against it for ten minutes. A grep catches that once; a linter catches it the
moment an agent writes the class.

What makes it fit an agent loop is the error, not the check. TypeScript says what is forbidden;
this says what to do and where:

```text
"rounded-full" is not allowed on <Button>: <Button> owns its shape.
Use a variant: default, outline, secondary, ghost, destructive, link.
Add a new variant in packages/ui/src/components/button.tsx only if the design explicitly
calls for a treatment none of these provides.
```

Its value is **while an agent writes**. Run once against a finished hand-tuned app it reports mostly
policy disagreement — see §Retrofitting for what that looks like and how to adopt anyway.

## Install

One dev dependency, in **the package that owns the lint configuration**:

| Topology | Where it is installed | Where the plugin is registered |
|---|---|---|
| single Next app | the app | `eslint.config.mjs` |
| monorepo (`monorepo-bootstrap`) | `packages/eslint-config` | the preset the web app extends (`next-js`) |

```bash
pnpm add -D @shadcn/lint          # in the owning package; pnpm is strict, so not at the root
```

**Keep the framework's parser setup and add to it** — do not replace the config. Next already
configures ESLint; extend it:

```js
// eslint.config.mjs — what create-next-app@16 generates, plus the plugin.
// In a monorepo the same blocks go into the preset the web app extends.
import { defineConfig, globalIgnores } from "eslint/config"
import nextVitals from "eslint-config-next/core-web-vitals"
import nextTs from "eslint-config-next/typescript"
import { plugin as shadcn } from "@shadcn/lint"

export default defineConfig([
  ...nextVitals,
  ...nextTs,
  {
    files: ["**/*.{ts,tsx}"],
    plugins: { shadcn },
    rules: {
      "shadcn/no-restyle": ["error", { allow: ["layout"] }],
      "shadcn/no-raw-colors": ["error", { allow: [/* declared shadow tokens, see below */] }],
      "shadcn/no-arbitrary-values": ["error", { allow: ["layout"] }],
      "shadcn/no-inline-styles": "error",
      "shadcn/require-static-classes": "error",
      "shadcn/no-unknown-classes": "warn",
    },
  },
  // components style themselves — the adoption guide's own override
  {
    files: ["components/ui/**"],                 // monorepo: "src/components/**" in packages/ui
    rules: {
      "shadcn/no-restyle": "off",
      "shadcn/no-arbitrary-values": "off",
      "shadcn/require-static-classes": "off",
      // the registry's own variant strings trip it — see §Severity
      "shadcn/no-unknown-classes": "off",
    },
  },
  // shadcn's chart injects per-series CSS variables at runtime
  { files: ["components/ui/chart.tsx"], rules: { "shadcn/no-inline-styles": "off" } },
  // the type specimen renders literal values on purpose (see SKILL.md §showcase)
  {
    files: ["app/**/showcase/**"],
    rules: { "shadcn/no-inline-styles": "off", "shadcn/no-arbitrary-values": "off" },
  },
  globalIgnores([".next/**", "out/**", "build/**", "next-env.d.ts"]),
])
```

The Next half is the file `create-next-app@16` writes (`eslint-config-next/core-web-vitals` +
`eslint-config-next/typescript` inside `defineConfig`) — keep it, add to it. In a monorepo that
already has a shared preset, spread that preset instead: in annotix the working form was
`...nextJsConfig` from `@annotix/eslint-config/next-js`, and importing `@typescript-eslint/parser`
directly from `apps/web` failed because pnpm does not hoist it there.

### Monorepo: a separate preset, spread only where UI is rendered

What worked on annotix (committed `e4008bc`): a `packages/eslint-config/design-system.js` exporting the
plugin block and the overrides, added to the package's `exports`, and spread **only** into
`apps/web/eslint.config.js` and `packages/ui/eslint.config.js` —
`export default [...nextJsConfig, ...designSystemConfig]`. `packages/api` and `packages/shared` are
never asked about Tailwind classes they do not write. Overrides can live in the shared file because
each glob matches only in the package where it exists: `src/components/**` in `packages/ui`,
`app/**/showcase/**` in `apps/web`.

The shadow allow-list is read **from the theme when the config loads**, not typed into it:

```js
function declaredShadows() {
  try {
    const css = readFileSync(new URL("../ui/src/styles/globals.css", import.meta.url), "utf8")
    const theme = css.match(/@theme[^{]*\{([\s\S]*?)\n\}/)?.[1] ?? ""
    return [...theme.matchAll(/--shadow-([a-z0-9-]+)\s*:/g)].map((m) => `shadow-${m[1]}`)
  } catch {
    return []
  }
}
// "shadcn/no-raw-colors": ["warn", { allow: declaredShadows() }]
```

Adding a shadow to the theme then never produces a lint finding nobody understands. Reported
`shadow-float` count on annotix after the change: 0.

### ⚠️ `eslint-plugin-only-warn` makes every rule a warning

The shadcn monorepo template's `packages/eslint-config/base.js` loads `eslint-plugin-only-warn`.
annotix and gym-saas have it; eve-hospitality and bidmaster, scaffolded differently, do not. With it,
**`"error"` reports as a warning and `pnpm lint` never fails** — on annotix, before this plugin,
`0 errors` on a repo with 40 findings. A rule at `error` in that repo is a suggestion.

So the gate is the warning count, per UI package:

| Project | `lint` script |
|---|---|
| new scaffold with `only-warn` | `eslint --max-warnings 0` — this *is* "error from day one" there |
| retrofit | `eslint --max-warnings <today's measured total>`, lowered as findings are fixed, never raised |

*Verified* on annotix: caps at 1114 (`apps/web`) and 9 (`packages/ui`), one `bg-pink-500` added to a
page → `ESLint found too many warnings`, lint fails; file restored → passes. A cap of 0 also means the
pre-existing warnings count — on a fresh scaffold that is the carousel's
`react-hooks/set-state-in-effect`, which is why it has to be decided before the cap goes in.

*Verified* on gym-saas as a fresh scaffold: `--max-warnings 0` in both packages, green; a
`bg-pink-500` in app code fails it, and so does one inserted into `badge.tsx`'s `cva(...)` string —
the component-directory override switches off restyle and arbitrary values, not `no-raw-colors`.
Break-test a primitive through its `cva` string: primitives have no `className="…"` to insert into,
and a test that silently edits nothing reports "not caught" about a file it never changed.

Do not remove `only-warn` to "restore" errors without looking: it would turn every other rule in
the repo into a hard failure at once.

**Discovery needs no settings** when `components.json` exists: the linter reads its `tailwind.css`
for the theme (following `@import`s), its aliases for the component directory, and workspace package
`exports` for shared components. On annotix it resolved `@annotix/ui/components/button` to
`packages/ui/src/components/button.tsx` from `apps/web` with no configuration.

## Severity on a new scaffold: `error` from day one

The adoption guide's `warn` → `error` ladder is for codebases with a backlog. A scaffold has none, and
a guardrail is worth most before the first violation exists, so every core rule starts at `error`.
`no-unknown-classes` starts at `warn`: classes supplied by another stylesheet may need an `allow`.

*Verified* by running the config block above **verbatim** — extracted from this file, not retyped —
over a fixture holding the **61 shadcn primitives** of a real `base-nova` scaffold, its theme, a
showcase page and a page written to violate:

| | Result |
|---|---|
| `rounded-full` on `<Button>`, `bg-pink-500`, `text-[17px]` | **error** each, with the fix named — `text-[17px]` suggests `text-base (16px), text-lg (18px)` from the *redefined* scale |
| `shadow-float` (declared in `@theme`, allow-list derived from it) · `mt-4 w-full` (`layout`) | pass |
| showcase specimen, `chart.tsx`, the component directory | pass — every override holds |
| shadcn/lint on the 61 primitives | **0 errors**, 7 `no-unknown-classes` warnings |

The two rules that stay on inside the component directory fire twice on stock primitives, both in
`chart.tsx` (a `<style>` element for per-series CSS variables, an inline `backgroundColor` on the
tooltip indicator) — hence its override. The 7 warnings are `cn-input-otp`, a registry marker class,
and six variant strings in `navigation-menu.tsx` such as `xs:w-(--popup-width)` and
`data-[ending-style]:easing-[ease]` that the linter says generate no CSS. They may be dead classes
upstream; that was not confirmed by rendering. On gym-saas a further one appeared, `toaster` in
`sonner.tsx`. At `warn` they would not fail a normal lint — but under `eslint-plugin-only-warn` with
`--max-warnings 0` (§ below) **every warning fails it**, so a clean scaffold would not pass. That is why
`no-unknown-classes` is off inside the vendored component directory in the block above: those strings
are the registry's, not the agent's to fix. It stays on for app code, where a misspelled class is
exactly what it should catch.

⚠️ **Errors that are not shadcn/lint's.** `components/ui/carousel.tsx` fails
`eslint-config-next`'s `react-hooks/set-state-in-effect` (a synchronous `setState` inside an effect).
A scaffold that runs `shadcn add --all` therefore does not pass `pnpm lint` on Next 16 *before* this
plugin is added. With `AGENTS.md` telling agents to fix every error, the first agent to run lint will
rewrite a vendored primitive. Decide it once at scaffold time — override the rule for that file with a
comment, or drop the carousel if the product does not need it — rather than leaving it to the agent.
The same rule fails `hooks/use-mobile.ts`, which `shadcn add sidebar` drops into the **app**, not the
UI package (found on gym-saas). What was applied there, per package config and commented:

```js
{
  files: ["src/components/carousel.tsx"],        // packages/ui — "hooks/use-mobile.ts" in apps/web
  rules: { "react-hooks/set-state-in-effect": "off" },
},
```

An override rather than a rewrite: re-adding the component from the registry must not silently bring
back a failure an agent would then "fix" by editing vendored code.

## A flood of "unknown class" warnings means the theme did not build

`no-unknown-classes` asks the project's own Tailwind whether a class generates CSS, so it needs the
theme to build — every `@import` resolved. When one does not (`tw-animate-css` or `shadcn/tailwind.css`
not installed yet), the linter says so in **one line** and falls back to its bundled grammar:

```text
[@shadcn/lint] The Tailwind theme at app/globals.css could not be built
(@import "tw-animate-css" could not be resolved …); no-unknown-classes is using the grammar
bundled with @shadcn/lint there until it can.
```

On the fixture above that turned 7 warnings into **129** — every `data-open:fade-in-0` and
`zoom-in-95` in the primitives. Read the first line of the output before any of the rest, and run
lint after `pnpm install`, never before it.

## "This project's cn is 0.2.4"

On a project that uses the `cn` package (shadcn's newer `lib/utils`), the linter checks its version:

```text
[@shadcn/lint] This project's cn is 0.2.4. The linter's grammar needs cn 0.2.6 or later, so it used
its bundled cn 0.2.6 instead. Update cn to lint with the grammar your app merges with.
```

Not an error and not a false result — it lints with its own copy. Upgrade `cn` in the UI package so
the grammar the lint checks against is the one the app actually merges classes with.

## The shadow-token trap — verified, with the fix

`no-raw-colors` reads `--color-*` declarations in `@theme`. A **custom shadow token declared the
standard Tailwind v4 way** —

```css
@theme inline { --shadow-float: 0 4px 16px rgb(15 17 21 / 0.08); }
```

— generates a real `shadow-float` utility, and the linter reports it anyway:

```text
"shadow-float" is not a declared theme color. Use one of: primary.
```

`shadow-*` also accepts colours, and a name it cannot find among `--color-*` is read as an undeclared
colour. Built-in shadows (`shadow-lg`) are not affected. Reproduced on a minimal fixture, not only on
annotix.

**Allow each declared shadow by exact name, never by wildcard:**

| Policy | `shadow-float` | `shadow-pink-500` (a raw colour) |
|---|---|---|
| `allow: ["shadow-float"]` | passes ✅ | **reported** ✅ |
| `allow: ["shadow-*"]` | passes | **passes** ❌ — the wildcard opens the hole the rule exists to close |

Generate the list from the theme rather than typing it — every `--shadow-<name>` inside `@theme`
becomes `"shadow-<name>"` in the `allow` array — so adding a shadow to DESIGN.md never produces a
lint error nobody understands, and a raw colour on a shadow is still caught.

## Golden rule 3 — the import bans

`@shadcn/lint` checks how primitives are *styled*; nothing in it checks whether they are *used*. The
preset adds ESLint's own `no-restricted-imports` for golden rule 3 (`references/contracts.md`), on every
`.ts`/`.tsx` file **except the component directory**, where the primitives legitimately import their bases:

- **Undeclared component libraries** — `@mui/*`, `@chakra-ui/*`, `antd`, `@mantine/*`,
  `@headlessui/react`, `@heroui/*`, `@nextui-org/*`, `react-bootstrap`, `primereact`, `flowbite-react`,
  `@ark-ui/*`, `@fluentui/*`, `@blueprintjs/*`, `semantic-ui-react`, `@radix-ui/themes`. A second design
  system in a shadcn project is the violation itself.
- **The primitives' headless bases** — `radix-ui`, `@radix-ui/react-*`, `@base-ui/react`,
  `@base-ui-components/react`, `react-aria-components`, `vaul`, `cmdk`, `input-otp`. App code that imports
  `Dialog` from `radix-ui` instead of `components/ui/dialog` forks the primitive's behaviour. Skipped for
  `stack.ui = "base-ui"`, where the headless primitives are the library.

⚠️ **Slash-free names are written anchored — `/input-otp`, not `input-otp`.** The patterns are
gitignore-style, so a name without a slash matches that path segment *at any depth*: a bare `input-otp`
also banned the project's own `@/components/ui/input-otp` (shadcn ships `components/ui/input-otp.tsx`)
with the golden-rule message, and a bare `vaul` would ban any `…/vaul/…` path. The leading slash anchors
the name to the import root: the package and its subpaths (`input-otp/dist/…`) stay banned, local paths
that merely contain the name do not. `setup_design_lint.py` anchors every slash-free entry itself;
scoped names and `radix-ui/*` already contain a slash and are anchored by the gitignore rules. Measured
with eslint 10.11 on FITROOM, 2026-09-22. A preset generated before that date needs a re-run.

Not banned, on purpose: `sonner` (`toast` is called from app code in shadcn's own docs), `recharts`
(charts compose it with `ChartContainer`), `react-day-picker` (its `DateRange` type is used by callers).

Every package name was checked on npm on 2026-09-15, and the patterns were measured at **zero hits**
outside the component directory across nine projects before the rule was turned on. On gym-saas a probe
file importing `radix-ui`, `@base-ui/react/popover` and `@mui/material/Button` produced three findings
with the golden-rule message; `sonner` produced none, and the 60+ primitives in `packages/ui` stayed clean.

**A configured `cn`: the package import is banned too, primitives included.** When `lib/utils.ts`
(or `src/lib/utils.ts`) builds its `cn` with `createCn` (`cn/config`) or `extendTailwindMerge`, the
preset adds `paths: [{ name: "cn", importNames: ["cn"] }]` to the same rule, on every file except that
utils file, **and a second block on the component directory**. Since September 2026 `shadcn add`
writes `import { cn } from "cn"` into the primitives, and there the stock instance would bypass the
project's merge config: the same class-dropping bug the config exists to prevent. `cn/config` and
`{ clsx } from "cn"` stay allowed. With a stock `lib/utils.ts` nothing is added, because the package's
`cn` is the same function. Checked on ESLint 9.39.4: `import { cn } from "cn"` is reported;
`cn/config`, `@/lib/utils` and `{ clsx } from "cn"` are not. Why: `shadcn-mapping.md` §cn.

The rule is core ESLint, so a project's own `no-restricted-imports` later in its config **replaces** this
one (flat config does not merge rule options). If the project needs its own list, extend the preset's
patterns there instead of redefining the rule.

## Agents

Put the lint command in `package.json` and this line in the project's `AGENTS.md`:

```md
After making changes, run `pnpm lint` and fix all errors.
```

The upstream evals claim nearly every task reaches zero violations after one correction round, at
10–48% lower cost than rules alone. Those are **their numbers on their fixtures**; the mechanism is
the part worth relying on — an error that names the fix is one round, an error that only forbids is
several.

## Exceptions

An intentional exception lives next to the code, with a reason:

```tsx
// eslint-disable-next-line shadcn/no-raw-colors -- partner brand colour, approved by design
<span className="bg-amber-400">Sponsor</span>
```

`rg "eslint-disable.*shadcn/"` lists them. A class that keeps needing an exception is a token or a
variant DESIGN.md is missing — fix it there, not in the disable comment.

## Retrofitting an existing project

Do not switch everything to `error` on a codebase that grew without it. Measured on annotix before
its type scale was moved into the theme:

```text
1749 findings across 133 files
  no-arbitrary-values 850 · no-restyle 733 · no-inline-styles 125 · require-static-classes 22 · no-raw-colors 19
```

Most of that was deliberate choices, not defects — and the smallest rule's 19 were ten shadow-token
reports (§ above) and nine literal colours in a theme *picker*, where the palette is the content.
Yet inside the 850 sat the real finding: 531 `text-[…]` literals meaning a missing type scale.

What that looked like on annotix once installed, after its type scale moved into the theme:
`no-arbitrary-values` **850 → 193**, `no-raw-colors` 19 → 10 (the shadow reports gone), 1074 findings
in `apps/web`, 7 in `packages/ui`.

So: rules at `warn`, `eslint . --max-warnings <measured count>` in CI so the number can only go
down, fix repeated patterns first (a missing token beats 500 one-line edits), and promote each rule to
`error` as it reaches zero. dev-flow proposes this in the `deployed` maintenance loop, never as a
blocking gate.

## Record it

`meta.json#stack.design_lint = "shadcn-lint"` once installed and registered. `null` means the project
opted out, which is a decision to record, not an omission.
