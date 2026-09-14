# Design-system lint — `@shadcn/lint`

> Sources: [shadcn-ui/lint](https://github.com/shadcn-ui/lint) README, `SETUP.md`, `docs/adoption.md`,
> `docs/how-it-works.md`, `docs/rules/no-raw-colors.md` · npm `@shadcn/lint@0.1.0` (the only published
> version, 2026-09-14) · peer `eslint >=9.30.0` · `node >=20.19` · Tailwind v4 · **shadcn/ui not
> required**, so it applies to `stack.ui` = `shadcn`, `base-ui` and `coss` alike. Written **2026-09-14**.
> Everything marked *verified* below was run, not read.

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
upstream; that was not confirmed by rendering. At `warn` they do not fail the lint — do not let an
agent "fix" vendored primitives to silence them.

⚠️ **One error on the same fixture is not shadcn/lint's.** `components/ui/carousel.tsx` fails
`eslint-config-next`'s `react-hooks/set-state-in-effect` (a synchronous `setState` inside an effect).
A scaffold that runs `shadcn add --all` therefore does not pass `pnpm lint` on Next 16 *before* this
plugin is added. With `AGENTS.md` telling agents to fix every error, the first agent to run lint will
rewrite a vendored primitive. Decide it once at scaffold time — override the rule for that file with a
comment, or drop the carousel if the product does not need it — rather than leaving it to the agent.

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

So: rules at `warn`, `eslint . --max-warnings <measured count>` in CI so the number can only go
down, fix repeated patterns first (a missing token beats 500 one-line edits), and promote each rule to
`error` as it reaches zero. dev-flow proposes this in the `deployed` maintenance loop, never as a
blocking gate.

## Record it

`meta.json#stack.design_lint = "shadcn-lint"` once installed and registered. `null` means the project
opted out, which is a decision to record, not an omission.
