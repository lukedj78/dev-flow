---
name: shadscan
description: 'Run shadscan on a React/shadcn app to find missing UI fundamentals — accessibility, interaction, empty/error/loading states, form wiring, responsive shell, production polish — then route each fix to the dev-flow skill that owns it. shadscan (https://www.shadscan.com/, an independent open-source CLI — npm package `@shadscan/cli`, MIT, github.com/TheOrcDev/shadscan; run with `npx --yes @shadscan/cli`) is a deterministic, read-only static audit: it does not start the app, edit files, call an AI model, upload source, or need secrets. It scores six categories out of 100 with file:line evidence, and its `--json` output carries an `agentHandoff` block where every actionable is tagged `disposition` (fix / decide / verify) and `confidence` (high / medium / low) with machine-checkable acceptance criteria. This skill wraps that run: it applies the high-confidence `fix` items, surfaces the `decide` items as product questions, verifies the advisories in code, and hands the real corrections to the owning skill (`forms` for form wiring, `transitions` for reduced-motion, `data-fetching` for Suspense/loading boundaries, `design-md-to-app` for shell/empty-state/SEO, `composition-patterns-guide` for anatomy). The UI-quality and accessibility counterpart to `compliance-audit` (legal gate) and `vercel-doctor` (cost gate) — the third pre-deploy gate. Horizontal capability; dev-flow proposes it at `feature_complete` and in the `deployed` maintenance loop. Records a `shadscan` block in meta.json; does NOT bump phase. Use when the user says "shadscan", "audit my UI", "check accessibility", "is this app accessible", "a11y audit", "missing loading/empty states", "UI quality check", or dev-flow routes here before a web deploy. Refuses for non-React / non-shadcn targets (mobile RN is out of scope). Not for: legal/privacy audit (use compliance-audit), Vercel cost (use vercel-doctor), designing the UI (use design-md-to-app), or writing tests (use write-tests).'
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
npx --yes @shadscan/cli                                  # scan ./ , human output
npx --yes @shadscan/cli --json > docs/ui/shadscan.json   # machine-readable report — USE THIS
npx --yes @shadscan/cli --fail-under 80                  # CI gate: non-zero below the threshold
```

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
2. **Run** `npx --yes @shadscan/cli --json --no-interactive > docs/ui/shadscan.json`. Read
   `score`, `grade`, `categories[]`, and — critically — **`coverage.source`**. If coverage is not
   `"complete"`, the scan saw only part of the source and the score is not comparable to a previous run;
   say so instead of reporting a number.
3. **Triage from `agentHandoff.actionables`, not from the human output.** Every actionable carries a
   `disposition` and a `confidence`. Act on the pair, never on the score:

   | `disposition` | `confidence` | What you do |
   |---|---|---|
   | `fix` | `high` | **Apply it.** A confirmed defect with file:line evidence. |
   | `fix` | `medium` / `low` | Open the file, confirm the defect is real, *then* fix. |
   | `decide` | any | **Do not invent an answer** — it's a product question ("should this app have a command menu?"). Surface it to the user with the trade-off and move on. |
   | `verify` | any | Read the code and confirm. Many are advisories that **did not reduce the score**; a `pass` you can't reproduce is a finding about the detector, not the app. |

   Each actionable ships `acceptanceCriteria` — machine-checkable, including a re-run of the rule and the
   project's own gates (`verification.projectGates`, e.g. `pnpm lint`, `pnpm typecheck`, `pnpm build`).
   **Run those gates after fixing** and report any you were not authorised to run.

   🚫 **Never optimise for the score.** shadscan says this itself, and it is the rule that keeps this gate
   honest: *do not add unused infrastructure solely to increase the audit score*, and *do not edit solely
   to force score-neutral static advisories to report pass*. A command menu nobody asked for is a
   regression that scores well. If a fix has no user-facing benefit, it is a `decide`, not a `fix`.
4. **Apply the mechanical accessibility fixes** here — a missing `alt`, a suppressed focus ring
   (`outline-none` with no `focus-visible:` replacement), a positive `tabindex`, an unlabelled control,
   a heading level skipped. These are unambiguous and belong to nobody else.
5. **Route the rest** to the owning skill rather than hand-fixing (table above). Don't re-implement
   `forms`' error-association pattern or `data-fetching`'s boundary ladder inside this skill.
6. **Persist**: keep `docs/ui/shadscan.json` (+ the human report if useful), update `meta.json#shadscan`,
   append `history`. **No phase bump.**

### Trust calibration — what a real run showed

Run against a live Next 16 + eve project (**64/100, grade D**, 59 rules evaluated: 28 pass, 12 fail,
11 not-applicable, 8 advisory; 17 actionables — 9 `fix`, 7 `verify`, 4 `decide`). Two spot-checks against
the source, both **true positives**:

- `components/ui/combobox.tsx:271` — `className={cn("min-w-16 flex-1 outline-none", …)}`: the focus
  outline is suppressed with no `focus-visible` replacement anywhere in that class string.
- `components/chat/ChatInput.tsx:29` — the form's `onSubmit` calls `submit()` with no pending state, no
  disabled trigger, no progress: double-submit is one impatient click away.

This is the **opposite** of the failure mode documented in `vercel-doctor` (whose `knip` dead-code pass
flagged 58% of a codebase, all false). shadscan resolves nothing speculatively — it reports what is
present in the file it names. **Still open the file**, but expect it to be right, and weight the
disposition/confidence pair rather than second-guessing every hit.

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
  "fixed": ["focus-visible-not-suppressed","images-have-alt"],
  "decisions_open": ["command-menu-present"],   // disposition=decide, awaiting the user
  "routed": { "forms": ["async-action-pending-state"],
              "data-fetching": ["suspense-fallback-useful"],
              "design-md-to-app": ["mobile-nav-present","social-preview-present"] }
}
```

⚠️ **Only compare scores within the same `rulesetVersion`.** A new ruleset adds rules; a score that
"dropped" across versions may be the same app measured against more checks.

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
- Every `fix` actionable either applied or explicitly declined with a reason; every `decide` surfaced to
  the user as an open question; every `verify` checked in code.
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
