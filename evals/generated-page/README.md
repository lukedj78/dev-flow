# generated-page — grading the output, not the source

The third question this repo asks, and the one it could not answer until now.

| | asks | runs against |
|---|---|---|
| `lint_skills.py` | is a skill still well-formed? | the source |
| `run_evals.py` | do the deterministic scripts still hold? | the tools |
| **`check.py`** | **did the generation follow its own rules?** | **the output** |

Everything in `design-md-to-app` — the anti-slop rules, the mandatory steps — is a
promise about generated code that **nothing was counting**. A rule the generator
states and nobody measures is a rule that quietly stops being followed, and the
first person to notice is whoever inherits the app.

**Not `shadscan`.** That audits a React app for UI fundamentals — accessibility,
empty and error states, responsive shell — and is the right tool for *is this app
any good*. This asks something narrower and more embarrassing: **did
`design-md-to-app` obey `design-md-to-app`?**

## Use

```bash
python3 evals/generated-page/check.py ~/projects/my-app          # read it
python3 evals/generated-page/check.py ~/projects/my-app --json > before.json
# …change the skill, regenerate…
python3 evals/generated-page/check.py ~/projects/my-app --baseline before.json
```

Exit code is **0 by default** — this is a measurement, not a gate. `--fail-on high`
turns it into one, which belongs in a project's own CI rather than in this repo's.

`components/ui/**` is skipped: those files come from the shadcn / Base UI CLI, and
grading them grades upstream. `--include-vendored` turns them back on.

## The sixteen checks

Twelve find something that should not be there — `h-screen`, `#000` in an ink
position, `John Doe`, `Acme`, `99.99%`, `john@example.com`, marketing filler,
Unsplash for a stub photo, a layout-forcing animation, a spinner where a skeleton
belongs, `01 / 02 / 03` on non-sequential sections, an invented gradient.

Four find something that should be there and is not, which is the failure mode
nobody catches in review because **a missing file produces no diff**: i18n with both
required locales, a dark/light theme system, `error.tsx` + `loading.tsx`, and
`:active` feedback anywhere at all.

Severity is about what to do, not how bad it looks. `pure-black` is `medium` inside
a `className` or a CSS declaration and `low` as a bare string, because a colour
default in a picker's data model is data, not the page's ink — reported so the
dismissal is deliberate, demoted so the number stays worth reading.

## Self-test — the checks are checked

```bash
python3 evals/generated-page/check.py --selftest
```

`fixtures/bad/` breaks every rule exactly once; `fixtures/good/` breaks none. Every
check must fire on the first **and** stay silent on the second. A check that cannot
do both is either dead or a false-positive generator, and both look identical in a
report. CI runs this on every push.

**Field findings become fixtures.** The first real run produced 26 findings on one
project, of which 20 were inside vendored primitives — `bg-black/10` scrims and Base
UI's `h-(--positioner-height)` sitting next to the word `animate`. That noise is now
`fixtures/good/components/ui/dialog.tsx`, so the same false positive cannot come
back. Do the same with the next one.

## The matched comparison

The point of a count is the *difference* between two of them. One run tells you
nothing: every generated app has findings, and the absolute number is a property of
the app as much as of the skill.

1. Pick a project and record a baseline **before** touching the skill (`--json`).
2. Make the change. Regenerate the same scenario, same inputs.
3. Re-measure with `--baseline`. Read the per-check deltas, not the total.

If no check moved, the change is not an improvement in anything this file measures —
which may still be true and is worth saying out loud rather than assuming.

## Scenarios

A comparison is only matched if the inputs are. These are the recurring shapes; keep
one project per scenario and regenerate *that* one:

| # | scenario | what it exercises |
|---|---|---|
| 1 | token-rich `DESIGN.md`, light theme | the easy path — frontmatter tokens resolve, nothing is invented |
| 2 | body-only `DESIGN.md`, prose only | the anti-slop fallbacks, hardest: every value is a decision |
| 3 | `DESIGN.md` + `.workflow/screenshots/` | Step 4.5b/c — verbatim copy, never invent |
| 4 | single-mode opt-out (dark-committed) | the theme check must not fire on a deliberate choice |
| 5 | monorepo topology | `packages/ui` paths, the vendored skip, i18n at the app level |

They are **defined here, not shipped as fixtures**: each needs an agent run, an
install and minutes of wall clock, so they cannot live in CI. What lives in CI is the
self-test.

## What this cannot do

**It only catches failures someone already wrote down.** Every check here exists
because a rule exists; a page can pass all sixteen and still be bad in a way nobody
has named yet. Treat a clean run as "no *known* mechanical failure", never as "good".

**And it says nothing about whether the page is any good.** Hierarchy, whether the
composition suits the material, whether the copy earns its place — none of that is
mechanical. For that, the honest instrument is a **blind A/B**: generate the same
scenario twice, strip anything identifying which run is which, and have a person pick
the better page without knowing which is the change. Do it with more than one
scenario, because a single pair is a coin flip. That half stays human, and pretending
otherwise is how a number starts standing in for a judgement it never made.
