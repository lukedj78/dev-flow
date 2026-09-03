# Audit recipe — "audit the motion in this codebase"

Invoked when the user asks to review a whole codebase against the motion discipline (not to add one transition — that's Apply mode). Read-only until the user approves fixes.

## 1. First-pass signal

```
python transitions/scripts/scan_motion.py <project-root>
```

It greps for the smells below and prints a JSON list of `file:line` hits per category. **It is a signal, not a verdict** — heuristics over-report. Verify every hit by reading the code before it lands in the report.

## 2. What counts as a finding

| Smell | Why | Fix (mode) |
|---|---|---|
| **Magic-number duration** — `duration-[237ms]`, `transition-duration: 237ms`, `animate={{…, duration: 0.24}}` not from a token | drifts page-to-page; no single feel | Refine → nearest token |
| **Inline easing** — `cubic-bezier(...)` or `ease-[...]` literal in a component | same drift | Refine → `ease.*` token |
| **No reduced-motion path** — a `transition`/`@keyframes`/Motion effect with no `motion-reduce:` / `useReducedMotion()` / media-query fallback | a11y + vestibular-safety regression | Apply the fallback |
| **Animating layout props** — `transition-all`, keyframes on `width`/`height`/`top`/`left`/`box-shadow` | main-thread thrash | rewrite on `transform`/`opacity` (Tier 1) or lift to Tier 2/3 |
| **Tier-3 for a Tier-0 job** — `motion/react` import used only for a fade/slide | ~40kb + forced `"use client"` for nothing | downgrade to `tw-animate-css` |
| **`transition-all`** | animates every property, including layout | scope to `transition-transform`/`transition-opacity`/`transition-colors` |
| **Un-tokenized `@keyframes`** in component CSS | should live in the library, tokenized | move to `lib/motion/`, reference vars |

## 3. Report shape

Group by severity: **A11y** (missing reduced-motion) → **Performance** (layout props, `transition-all`) → **Consistency** (magic numbers, inline easings) → **Weight** (Tier-3 overkill). Per finding: `file:line`, the smell, the token/tier it should use, and the one-line fix. Lead with a posture summary (is there a token layer at all? is `stack.motion.tokens` true?).

## 4. Refine order (when the user approves)

1. **Scaffold the token layer first** if missing (Setup) — you can't refine to tokens that don't exist.
2. **A11y fixes** — add every missing `prefers-reduced-motion` fallback. Highest leverage, lowest risk.
3. **Performance** — `transition-all` → scoped; layout-prop animations → transform/opacity.
4. **Consistency** — magic numbers/easings → nearest token (round to the token scale; if a value has no near token, propose adding one to `tokens.ts` rather than snapping hard).
5. **Weight** — downgrade Tier-3-for-a-fade to Tier 0.

Each refine is a reviewable diff. A re-run of the scan should return no findings for already-fixed files (idempotent). Update `stack.motion.last_audit_at` and append `history`.


## Read the scan by provenance, not top to bottom

`scan_motion.py` tags every finding with a `provenance` and reports a
`by_provenance` count. Ranking by it is the difference between an audit someone
acts on and one they close:

| `provenance` | What it is | What to do |
|---|---|---|
| `authored` | code someone on this project wrote | **this is the audit** — verify and fix |
| `vendored` | copied-in preset source (`components/ui/**`, registry components) | note it; fix only what you have already customised, and say the global guard covers the rest |
| `token-layer` | `lib/motion/**`, `lib/motion-config.*` | expected — these files *are* where the raw values live |

On a real shadcn project the first run came back **58 vendored, 5 token-layer,
15 authored**: forty untouched preset files were burying the six hits that
mattered. The fix is ranking, not a shorter rule set.

Three categories are informational rather than smells, and the scan now knows it:
a `--motion-*` custom property carrying a `cubic-bezier` is the **bridge**, a
`0.01ms` is the reduced-motion **guard**, and a file importing from
`lib/motion/transitions` inherits that library's `motion-reduce:` fallbacks — so
none of the three is reported. `tier3-import-review` stays informational by
design: it asks you to judge whether Motion was the right tier, and the answer is
often yes.
