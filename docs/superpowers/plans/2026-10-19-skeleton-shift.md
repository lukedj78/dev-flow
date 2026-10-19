# Skeleton audit — implementation plan

> For agentic workers: superpowers:executing-plans. Steps use `- [ ]`.

**Goal:** skeletons sized to the real loaded UI, and proof that the page does not jump when they are replaced.
**Spec:** the user's prompt (2026-10-19) — "Audit my skeleton UIs. First measure my loaded UIs in different states
with Playwright, then size my Skeleton components to those real UIs" — and the review of it in the same session:
which states, a verifiable criterion (CLS), re-measure after, where skeletons live, our constraints.

## Global constraints
- shadcn `<Skeleton>` only (golden rule 3); sizes on the Tailwind/theme scale, never `h-[37px]`; the skeleton uses
  the loaded UI's containers (grid, padding, gaps); en + it; code in English.
- Target: CLS ≤ 0.05 per route and width (web-vitals "good" is 0.1).

## Review focus
1. Transform-only entrances and scrolling must not count as layout shift.
2. A matching skeleton (same box sizes) reports nothing; a mismatched one names the elements that moved.
3. `--throttle` must not leak into the reduced-motion pass or slow the default run.
4. Shifts right after user input (`hadRecentInput`) are excluded, as web-vitals does.

### Task 1: `layout-shift` in render_probe.mjs
**Files:** `app-verification/scripts/render_probe.mjs`, `test_render_probe.py`, fixtures `skeleton-shift.html`
(skeleton replaced by taller content) and a matching skeleton added to `clean.html`.
**Produces:** finding id `layout-shift` (WARN > 0.05, FAIL > 0.1) with the moved elements; report field
`cls` per width; `--throttle slow|fast-3g|<kbps>` option (Network.emulateNetworkConditions, normal pass only).
- [ ] Tests: broken skeleton → `layout-shift` with an element named; clean (with matching skeleton) → nothing;
  `--throttle fast-3g` accepted, `--throttle bogus` exit 2.
- [ ] Run → FAIL. Implement (PerformanceObserver `layout-shift`, buffered, sum of values without recent input,
  sources' nodes → paths). Run → PASS. Commit.

### Task 2: the skeleton audit, wired
**Files:** new `design-md-to-app/references/skeleton-audit.md`; `design-md-to-app/SKILL.md` (loading row, 375 px
verification), `references/loading.template.tsx` (comment: a placeholder shape until measured), anti-slop rule 9,
`app-verification/SKILL.md` probe list, README, CHANGELOG; `test_templates.py` keeps the template on the scale.
- [ ] Write the reference (states, widths, locales, measure loaded → rebuild → re-measure, rules, report).
- [ ] Wire it; regenerate; full suite green; commit.
