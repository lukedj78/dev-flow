---
name: shadscan
description: 'Run shadscan on a React/shadcn app to find missing UI fundamentals — accessibility, interaction, empty/error/loading states, form wiring, responsive shell, production polish — then route each fix to the dev-flow skill that owns it. shadscan (https://www.shadscan.com/, an independent open-source CLI — npm package `@shadscan/cli`, MIT, github.com/TheOrcDev/shadscan; run with `npx --yes @shadscan/cli`) is a deterministic, read-only static audit: it does not start the app, edit files, call an AI model, upload source, or need secrets. It scores six categories out of 100 with file:line evidence, and its `--json` output carries an `agentHandoff` block where every actionable is tagged `disposition` (fix / decide / verify) and `confidence` (high / medium / low) with machine-checkable acceptance criteria. This skill wraps that run: it opens every `fix` item in the source before touching anything — on a real run only 2 of 9 survived that reading, because the tool is precise about one file and blind to composition — surfaces the `decide` items as product questions, verifies the advisories in code, and hands the real corrections to the owning skill (`forms` for form wiring, `transitions` for reduced-motion, `data-fetching` for Suspense/loading boundaries, `design-md-to-app` for shell/empty-state/SEO, `composition-patterns-guide` for anatomy). The UI-quality and accessibility counterpart to `compliance-audit` (legal gate) and `vercel-doctor` (cost gate) — the third pre-deploy gate. Horizontal capability; dev-flow proposes it at `feature_complete` and in the `deployed` maintenance loop. Records a `shadscan` block in meta.json; does NOT bump phase. Use when the user says "shadscan", "audit my UI", "check accessibility", "is this app accessible", "a11y audit", "missing loading/empty states", "UI quality check", or dev-flow routes here before a web deploy. Refuses for non-React / non-shadcn targets (mobile RN is out of scope). Not for: legal/privacy audit (use compliance-audit), Vercel cost (use vercel-doctor), designing the UI (use design-md-to-app), or writing tests (use write-tests).'
---

# shadscan — UI-quality & accessibility pre-deploy gate for React/shadcn apps

Runs on a web project that **already exists** and uses **shadcn**. It wraps the third-party
[shadscan](https://www.shadscan.com/) CLI — a deterministic static audit of *UI fundamentals* — and turns
its report into applied fixes, routing each finding to the skill that owns it.

This is the gate that covers what neither sibling can see. `compliance-audit` reads the legal surface,
`vercel-doctor` reads the cost surface; **nothing in dev-flow mechanically verified that the UI we
prescribe actually got built** — that the reduced-motion guard `transitions` mandates is really there,
that the form errors `forms` specifies are really rendered, that a route has a loading boundary at all.

> **Third-party tool.** shadscan is **not** an official shadcn product — it's an independent open-source
> project by [TheOrcDev](https://github.com/TheOrcDev/shadscan), published to npm as **`@shadscan/cli`**
> (bin `shadscan`, **MIT**). Verified against the npm registry + repo README (at time of writing:
> **0.9.0**, ruleset `2026.07.41`, report `schemaVersion 9` — the report shape is versioned, re-check it).
> From the README, verbatim: *"The default scan is deterministic and read-only. It does not start the app,
> edit files, call an AI model, upload source, or require application secrets."* That makes it safe to run
> on a private codebase without the `--offline` dance `vercel-doctor` needs.

## Verified invocation + flags

```bash
npx --yes @shadscan/cli                                       # explore: latest, human output
npx --yes @shadscan/cli@0.9.0 --json --no-interactive \
  > docs/ui/shadscan.json                                     # audit: PINNED — the mode this skill uses
npx --yes @shadscan/cli@0.9.0 --fail-under 70 --no-interactive # CI gate: pinned + ratcheted
```

⚠️ **Pin the version for anything you will compare.** `npx --yes @shadscan/cli` resolves to latest *on
every call* — during a single session it went 0.9.0 → 0.10.0 (ruleset `2026.07.41` → `2026.07.42`, 59
rules → 60), silently making a before/after diff a comparison across two different rulesets. shadscan
knows this: the `verification.shadscanCommand` it emits in its own acceptance criteria is **already
pinned** (`pnpm dlx @shadscan/cli@0.9.0 --json`). Follow it. Pin the baseline run, pin the re-run, and
only drop the pin when you deliberately want the newer ruleset — then re-baseline instead of diffing.

`pnpm dlx @shadscan/cli` and `bunx @shadscan/cli` work identically. Supported frameworks (per the README):
**Next.js, Vite, TanStack Start, Laravel, Astro, React Router** — it auto-detects the adapter and reports
it (`framework.adapter`, e.g. `next-app-router`) plus how confident it is that the project is shadcn at all.

| Flag | Effect |
|---|---|
| `[path]` | project directory to scan (default `.`) |
| `--json` | machine-readable report — **the mode this skill uses** |
| `--format <human\|json\|prompt>` | output shape |
| `--prompt` | print only a paste-ready remediation prompt for an agent |
| `--fail-under <score>` | exit non-zero below the score, **or when unassessed / partial source coverage** |
| `--category <category>` | run one audit category only |
| `--list-projects` / `--project <path>` | inspect / pick one workspace package instead of pooling them all |
| `--no-roast` / `--roast` | neutral copy vs. the snarky one-liners (roast is on by default in human output) |
| `--no-interactive` | disable follow-up prompts (**use in CI and in any agent run**) |
| `--apply` + `--agent <claude\|codex\|grok>` | hand the remediation prompt to an installed coding-agent CLI |
| `-V, --version` / `-h, --help` | version / help |
| `setup [path]` | write an explicit project integration |
| `mcp [paths...]` | serve shadscan as an **MCP server over stdio** for coding agents |

If a flag above is rejected, the CLI has moved — run `npx --yes @shadscan/cli --help` and use what it
reports rather than guessing.

⚠️ **Do not use `--apply`.** It shells out to another agent CLI to do the work. You *are* the agent —
read the JSON, triage it against the rules below, and apply the fixes yourself with the owning skill's
knowledge. `--apply` throws away the routing that makes this skill worth anything.

## The six categories (weights are the score, out of 100)

| Category | Weight | What it checks | Who fixes it in dev-flow |
|---|---:|---|---|
| **Foundation** | 20 | `components.json` parses, theme provider mounted in the shell, theme hydration safe, toast provider mounted | **`design-md-to-app`** (shell + providers), **`coss-ui`** when `stack.ui = "coss"` |
| **Interaction** | 20 | command menu present + `Cmd/Ctrl+K` bound, mobile nav trigger + controlled panel, responsive shell, keyboard navigation | **`design-md-to-app`** (it owns the shell/layout from DESIGN.md) |
| **States** | 20 | empty state, error state with retry, `not-found` recovery, route loading boundary, useful Suspense fallback | **`data-fetching`** (boundaries, Suspense, `loading.tsx`) + `design-md-to-app` (the *designed* state) |
| **Accessibility** | 20 | alt text, colour contrast, focus-visible not suppressed, dialog focus trap, heading structure, no positive `tabindex`, labels | **this skill** (mechanical) — icon a11y → **`heroicons-animated`**, motion → **`transitions`** |
| **Forms and Data Entry** | 10 | validation wired to the form, field errors rendered, invalid fields associated with their errors, async action pending state | **`forms`** |
| **Production Polish** | 10 | metadata title + description, social preview image, public SEO files, no starter copy left behind | **`design-md-to-app`** (metadata) + the deploy step |

Two rules deserve a name-check because they enforce **our own contract**:
`animations-respect-reduced-motion` is verbatim the core rule of the `transitions` skill, and
`forms-have-labels` / `invalid-fields-associated-with-errors` are what `forms` prescribes. shadscan is
the first thing in dev-flow that can *prove* those landed.

## Run, then route

1. **Preconditions.** `meta.json#stack.framework ∈ {"next","monorepo"}` and the project uses shadcn
   (`components.json` present). Refuse for `expo-rn` — the rules are DOM/React-web only. In a monorepo,
   `--list-projects` first, then `--project <path>` per app; pooling every package produces one
   meaningless blended score.
2. **Run** `npx --yes @shadscan/cli@<pinned> --json --no-interactive > docs/ui/shadscan.json`. Read
   `score`, `grade`, `categories[]`, and — critically — **`coverage.source`**. If coverage is not
   `"complete"`, the scan saw only part of the source and the score is not comparable to a previous run;
   say so instead of reporting a number.
3. **Triage from `agentHandoff.actionables`, not from the human output.** Every actionable carries a
   `disposition` and a `confidence`. Act on the pair, never on the score:

   | `disposition` | What you do |
   |---|---|
   | `fix` | **Open the file and the code around it. Every time, whatever the confidence.** Fix only what survives that reading — on a real run 7 of 9 did not. See §Trust calibration for which rule kinds to disbelieve. |
   | `decide` | **Do not invent an answer** — it's a product question ("should this app have a command menu?"). Surface it to the user with the trade-off and move on. |
   | `verify` | Read the code and confirm. Many are advisories that **did not reduce the score**; a `pass` you can't reproduce is a finding about the detector, not the app. |

   ⚠️ **`confidence` is not a precision estimate — don't gate the work on it.** Measured on a real run,
   `high` items split 2 true / 3 false. What predicts correctness is the *kind of question the rule asks*
   (does a file exist? vs. is this component semantically complete?), not the label shadscan attaches.

   Each actionable ships `acceptanceCriteria` — machine-checkable, including a re-run of the rule and the
   project's own gates (`verification.projectGates`, e.g. `pnpm lint`, `pnpm typecheck`, `pnpm build`).
   **Run those gates after fixing** and report any you were not authorised to run.

   🚫 **Never optimise for the score.** shadscan says this itself, and it is the rule that keeps this gate
   honest: *do not add unused infrastructure solely to increase the audit score*, and *do not edit solely
   to force score-neutral static advisories to report pass*. A command menu nobody asked for is a
   regression that scores well. If a fix has no user-facing benefit, it is a `decide`, not a `fix`.
4. **Apply the fixes that survived step 3** here when they belong to nobody else — a missing file
   (`not-found.tsx`, `opengraph-image.tsx`, `robots`/`sitemap`), a genuinely missing `alt`, a positive
   `tabindex`, a heading level skipped.

   ⚠️ Two of those look mechanical and are not: a **suppressed focus ring** is only a defect if no
   ancestor carries `focus-within:`/`has-[…]:focus` — check the wrapper first; an **unlabelled control**
   inside `components/ui/` is usually a design-system primitive, where the label is the consumer's job
   and adding one inside is the wrong fix.

   When a fix creates a new surface, finish it: an `opengraph-image` without `metadataBase` resolves to
   `localhost` and shows nothing in production, and `ImageResponse` (Satori) **does not support `ch`
   units** — a `maxWidth: "20ch"` silently collapses and renders one word per line, through a green
   build. **Look at the generated image**, don't trust the exit code.
5. **Route the rest** to the owning skill rather than hand-fixing (table above). Don't re-implement
   `forms`' error-association pattern or `data-fetching`'s boundary ladder inside this skill.
6. **Persist**: keep `docs/ui/shadscan.json` (+ the human report if useful), update `meta.json#shadscan`,
   append `history`. **No phase bump.**

### ⚠️ Trust calibration — what a real run actually showed

Run against a live Next 16 + eve project: **64/100, grade D**, 59 rules (28 pass, 12 fail, 11
not-applicable, 8 advisory), 17 actionables — 9 `fix`, 7 `verify`, 4 `decide`. Every `fix` was opened in
the source. **Two of the nine survived.**

The seven that did not, and why — this table is the skill's real content:

| Finding | Why it was wrong |
|---|---|
| `focus-visible-not-suppressed` | the inner input's `outline-none` is deliberate; the **wrapper** carries `focus-within:ring-3` |
| `async-action-pending-state` | the parent passes `disabled={busy}` and renders a `Spinner` — pending state is **lifted**, not absent |
| `suspense-fallback-useful` | the `fallback={null}` is inside a **WebGL `<Canvas>`**, where DOM nodes are illegal; `null` is correct |
| `links-have-accessible-names` | the link is a **Base UI `render` prop**; the accessible name arrives as the parent's children |
| `empty-state-present` | the "data-backed collection" is a **static table authored by hand** |
| `validation-wired-to-form` | a chat composer needs no form library |
| `forms-have-labels` | flagged a **design-system primitive**; a primitive carries no label, its consumer does |

**The pattern: shadscan is precise about what one file contains, and blind to composition.** It never
resolves speculatively — every string it quoted was really there — but it cannot follow a prop across a
component boundary, climb to a wrapper, see through a `render` prop, or know that a subtree renders to
WebGL instead of the DOM. **The better-composed the codebase, the more false positives it produces.**

So trust it by *what kind of question the rule asks*:

| Rule kind | Examples | Trust |
|---|---|---|
| **Does this file exist?** | `not-found-route-present`, `social-preview-present`, `public-app-seo-files-present`, `shadcn-config-present` | **high** — no code comprehension needed; both true positives were of this kind |
| **What is in this one file, self-contained?** | `no-positive-tabindex`, `images-have-alt` on a literal `<img>` | medium — usually right |
| **Is this component semantically complete?** | pending state, empty state, labels, focus rings, Suspense fallbacks | **low — assume wrong until the surrounding composition proves otherwise** |

Read the **parent, the wrapper and the render target** before touching anything in the third row. Cost of
being wrong is asymmetric: a missed finding is a small gap, a "fix" applied to a false positive damages
working code and its author's trust in the gate.

This is a *different* failure mode from `vercel-doctor`'s, not a milder one. There, `knip` invented
import graphs and flagged 58% of a codebase as dead. Here nothing is invented — the tool simply cannot
see past the file boundary, and good composition is what puts the answer on the other side of it.

### When the fix is real but the rule stays red

`mobile-nav-present` failed on a header that hid its whole `<nav>` below `sm` with no replacement — a
real defect: on a phone one route was unreachable. The fix was to keep two links visible and let the
wordmark step aside, verified at 375 px. **The rule still failed**: the detector looks for a trigger +
controlled panel pair, and does not recognise the "keep links visible in an explicit small-screen layout"
alternative that its own remediation text offers.

The correct outcome is the one that feels wrong: **ship the fix, leave the rule red, write down why.**
Adding a hamburger menu for two links to turn the rule green is the textbook case of the anti-gaming rule
above. When a remediation's stated alternative is not what the detector checks, the detector is the
narrower of the two — follow the user's interest, not the score.

## `meta.json#shadscan` block

```jsonc
"shadscan": {
  "last_run_at": "<ISO>",
  "engine_version": "0.9.0",     // report.engineVersion
  "ruleset_version": "2026.07.41", // report.rulesetVersion — the score only compares within a ruleset
  "coverage": "complete",        // report.coverage.source — anything else invalidates the score
  "score": 0,                    // 0-100
  "grade": "D",
  "categories": { "foundation": 0, "interaction": 0, "states": 0,
                  "accessibility": 0, "forms": 0, "production-polish": 0 },
  "fixed": ["not-found-route-present","social-preview-present"],
  "decisions_open": ["command-menu-present"],   // disposition=decide, awaiting the user
  // Opened, read, and rejected — with the reason, so the next run doesn't re-litigate them.
  "false_positives": {
    "focus-visible-not-suppressed": "wrapper carries focus-within:ring",
    "suspense-fallback-useful": "inside a WebGL <Canvas>; null is correct"
  },
  // Real fix shipped, rule still red because the detector checks something narrower.
  "rules_left_red": {
    "mobile-nav-present": "links kept visible at <sm; detector wants a trigger+panel pair"
  },
  "routed": { "forms": ["field-errors-rendered"],
              "data-fetching": ["route-loading-boundary-present"],
              "design-md-to-app": ["theme-hydration-safe"] }
}
```

⚠️ **Only compare scores within the same `rulesetVersion`.** A new ruleset adds rules; a score that
"dropped" across versions may be the same app measured against more checks. This is not theoretical — see
the pinning warning above; it fired on the very first real before/after. **Assert `rulesetVersion` equality
in code before reporting a delta**, rather than trusting that two runs minutes apart used the same tool.

## dev-flow hook

Horizontal capability — run any time. dev-flow **proposes it as a pre-deploy gate** at `feature_complete`,
completing the trio: `compliance-audit` (legal) · `vercel-doctor` (cost) · **`shadscan` (UI quality + a11y)**.
Re-run it in the `deployed` maintenance loop to catch UI regressions. It records `meta.json#shadscan` +
`history` and **never bumps `phase`**. It never *blocks* the deploy on its own — it surfaces the score and
the open decisions so the user decides.

**In CI** the natural form is `npx --yes @shadscan/cli --json --no-interactive --fail-under <N>`, with `N`
set to the score already achieved (a ratchet), not to an aspirational number. `--fail-under` also fails on
partial coverage, which is the behaviour you want.

## Ecosystem-first: shadscan ships its own agent skills

The repo carries `.agents/skills/` — read them from source rather than paraphrasing:

- **`migrate-radix-to-base/`** (SKILL.md + 9 reference files) — a Radix → **Base UI** migration guide.
  Directly relevant: our contract makes Base UI the default `ui_base`, so this is the upstream-maintained
  path for a project still on Radix. Prefer it over writing our own migration notes.
- **`shadcn/rules/`** — base-vs-radix, chat, composition, forms, icons, styling.

Consistent with rule zero: when the tool ships the knowledge, use the tool's copy.

## Relationship to other skills

- **`compliance-audit`** / **`vercel-doctor`** — the sibling gates. Same shape: `feature_complete`
  pre-deploy, no phase bump, "auto-fix safe + route/flag the rest". Different surface: legal, cost, UI.
- **`transitions`** — owns `prefers-reduced-motion`. shadscan **detects** the violation, `transitions`
  **defines** the fix (tokenised motion, cheapest tier first).
- **`forms`** — owns validation wiring, error rendering and error association. Route every `forms`
  category finding there.
- **`data-fetching`** — owns Suspense boundaries, `loading.tsx` and the read ladder behind the *States*
  category.
- **`design-md-to-app`** / **`coss-ui`** — own the shell, providers, responsive layout and metadata:
  most of *Foundation*, *Interaction* and *Production Polish*.
- **`composition-patterns-guide`** — owns component anatomy (input groups, item grouping, alert anatomy).
- **`write-tests`** — complementary, not overlapping: shadscan is static and finds *missing* fundamentals;
  tests assert *behaviour*. A shadscan fix is a good prompt for a regression test.

## Definition of Done

- `docs/ui/shadscan.json` written; `meta.json#shadscan` populated with score, grade, per-category
  breakdown, **ruleset version** and **coverage**.
- Every `fix` actionable **opened in the source**, then either applied or declined **with the reason
  recorded** (which parent/wrapper/render target made it a false positive); every `decide` surfaced to
  the user as an open question; every `verify` checked in code.
- Any fix that is real but leaves its rule red is **shipped anyway and documented** — in the commit
  message and in `meta.json#shadscan.rules_left_red`, so the next run doesn't re-litigate it.
- The project's own gates (`verification.projectGates`) run green after the fixes — or the ones you
  couldn't run named explicitly.
- Nothing was added purely to move the number.

## What this skill does NOT do

- **Not a legal/privacy audit** — that's `compliance-audit`. **Not a cost audit** — that's `vercel-doctor`.
- **Doesn't design the UI** — it checks that the built UI has its fundamentals; `design-md-to-app` designs.
- **Doesn't cover mobile** — the rules are DOM/React-web; Expo/RN has no equivalent here.
- **Doesn't use `--apply`** — the routing to owning skills is the whole point.
- **Doesn't bump `phase`**, and never blocks deploy by itself.

## Sources

- Official site: https://www.shadscan.com/
- Repo + rules (`packages/cli/src/rules/`, 62 rules) + bundled agent skills: https://github.com/TheOrcDev/shadscan
- npm: https://www.npmjs.com/package/@shadscan/cli

## Reference files

- `references/contracts.md` — the `.workflow/` dev-flow contract (vendored).
