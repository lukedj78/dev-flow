# Changelog

All notable changes to the dev-flow skill suite. Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versioning is [semver](https://semver.org/) on the **suite as a whole** (the version in `.claude-plugin/plugin.json`).

What a bump means here:
- **major** — a breaking change to the `.workflow/` contract (phase enum, `meta.json` schema, a skill's inputs/outputs) that existing projects must migrate for.
- **minor** — new skills, new capabilities, new doc-grounded references, non-breaking contract additions.
- **patch** — fixes to existing guidance, upstream re-verification, docs.

## [Unreleased]

### Changed
- **`heroicons-animated` → `animated-icons`** — the skill now covers **two** registries, so the old
  name had started to lie. [heroicons-animated](https://www.heroicons-animated.com/) (316 icons) and
  [hugeicons-animated](https://hugeicons-animated.com/) (165 icons), both MIT, both on `motion`, both
  copied into your repo as source. One skill rather than two: the procedure is identical and only the
  base URL changes. **Choose the registry by the project's static icon set, never by the icon count** —
  an animated Heroicon beside Hugeicons outlines is a different drawing. One structural difference to
  know: hugeicons items import a shared `lib/use-icon-animation.ts` (`registry:lib`), so an item is
  **not** always one file, and a hand-copied icon without the hook will not compile.
- **`lib/utils.ts` now defaults to [`cn`](https://github.com/shadcn-ui/cn)** instead of the
  `clsx` + `tailwind-merge` helper `shadcn init` writes — a compiled drop-in, same API, zero
  dependencies. Safe ahead of the CLI for a reason that was checked rather than assumed: the
  components `shadcn add` writes import **only `cn` from `@/lib/utils`**, so what sits behind that
  name was always ours to pick. Existing projects migrate with
  `npx shadcn@latest migrate cn --dry-run`; rolling back is two commands. Tailwind v4 only, and
  never `cn build` in a published component library.

### Added
- **`spec-review`** (core · operative) — reviews a **diff** on the two axes a dev-flow project can check that a generic reviewer cannot: **Spec** (does it implement what `.workflow/PRD.md` + `tasks.md` asked?) and **Standards** (does it obey the golden rules, the declared `meta.json#stack`, the discipline skills, with a Fowler smell baseline as the floor). Two parallel sub-agents, reported side by side and **never merged** — a change can follow every convention while building the wrong feature, or build the right feature ignoring the declared stack, and one verdict lets either hide behind the other. **44 skills** now: **6 core** · 15 web · 2 agent · 16 mobile · 3 monorepo · 2 refactor.

  Adapted from [Matt Pocock's `code-review`](https://github.com/mattpocock/skills) (MIT) and [the essay behind it](https://www.aihero.dev/skills-code-review); the two-axis split, the parallel sub-agents and the smell baseline are his. What is ours is the half his skill has to search for — his step 2 is four fallbacks ending in "ask the user where the spec is", while a dev-flow project keeps the spec and the standards **at known paths**. Deliberately **not** named `code-review`: Claude Code ships that name, and his own write-up lists the collision as a known problem — the same class of clash `setup-deploy` had with a third-party skill.

  It is **not a fourth pre-deploy gate**. The three gates read the finished artefact; this reads the *change*, so dev-flow proposes it at `page_generated` / `module_added` — a spec finding is cheapest while the branch is still open.
- **`framework: "agent"`** — the agent-only topology is now a first-class contract value: an eve agent at the repo root, no web app, surfaces elsewhere (Slack, email, GitHub, Linear). Closes a decision left open when `kody-eve-template` showed that `agent: "eve"` does **not** imply a monorepo. `eve-agent` gains **layout C** (agent at root, no `apps/*`, no `packages/types`) and, uniquely in this topology, **bumps `phase` to `scaffolded`** — it is the bootstrap skill there, the counterpart of `design-md-to-app` and `rn-bootstrap`, and without it the phase would never advance. Subsequent capability additions still only append to `history`.

  The 17 skills that guard on `framework` were **deliberately left untouched**: refusing an agent-only project is the correct answer, not a bug — `forms`, `data-fetching`, `shadscan` and the rest exist to build and audit a frontend that isn't there. `dev-flow` gains a routing row and is told not to apologise for their absence.
- **§Topology policy** in `dev-flow` — when an agent is in scope, three shapes are possible and the *project* picks: ① single web app (default), ② monorepo, ③ agent-only. Starting at ① costs nothing (`monorepo-bootstrap` promotes later; moving `agent/` is a directory move). Choosing ② up front costs workspace overhead for a second app that may never ship — so ask what the second consumer is; no answer means ①.
- **`shadscan`** — the **third pre-deploy gate**, completing the trio: legal (`compliance-audit`) · cost (`vercel-doctor`) · **UI quality + accessibility**. It wraps the third-party [`@shadscan/cli`](https://www.shadscan.com/) (MIT, deterministic and read-only — no app start, no file edits, no LLM, no source upload, no secrets), which scores a React/shadcn app out of 100 across Foundation · Interaction · States · Accessibility · Forms · Production Polish with file:line evidence. The skill reads the `--json` report's `agentHandoff` block — where each actionable carries a **`disposition`** (`fix` / `decide` / `verify`), a **`confidence`**, and machine-checkable acceptance criteria — applies the confirmed defects, surfaces the `decide` items to the user as product questions, and routes the real corrections to the owning skill (`forms`, `transitions`, `data-fetching`, `design-md-to-app`, `composition-patterns-guide`). Records `meta.json#shadscan`; no phase bump; web only.

  This closes a real hole: two of shadscan's rules are **verbatim our own contract** — `animations-respect-reduced-motion` is the core rule of `transitions`, and the label / error-association rules are what `forms` prescribes. Nothing in the suite could previously verify that the UI we prescribe actually got built.

  Verified by running it end-to-end on a live Next 16 + eve project: **64/100 (grade D)**, 59 rules, 17 actionables (9 `fix` · 7 `verify` · 4 `decide`) → **70/100 (C)** after the fixes. The skill carries the anti-gaming rule shadscan states itself: **never add unused infrastructure to raise the score**.

  **The run rewrote the skill's trust guidance.** Opening all 9 `fix` items in the source left **2 standing**. shadscan invents nothing — every string it quoted was really there — but it cannot follow a prop across a component boundary, climb to a wrapper, see through a Base UI `render` prop, or know that a subtree renders to WebGL instead of the DOM. A focus ring "suppressed" by an input whose wrapper carries `focus-within:ring`, a pending state lifted into the parent, a `fallback={null}` inside a `<Canvas>`, a label missing from a design-system primitive: all reported, none defects. **The better-composed the codebase, the more false positives.** So the skill now calibrates trust by *the kind of question a rule asks* — *does this file exist?* is reliable, *is this component semantically complete?* is not — and states plainly that `confidence` is not a precision estimate (`high` items split 2 true / 3 false).

  It also records the case where **the fix is real and the rule stays red**: a header that hid its whole `<nav>` below `sm` left one route unreachable on a phone; keeping the links visible fixed it, but `mobile-nav-present` still fails because the detector wants a trigger+panel pair. Ship the fix, leave the rule red, write down why — adding a hamburger for two links is the anti-gaming rule in textbook form.
- **`docs/knowledge-index.md` §Pre-deploy gates** — the two gates that wrap an external CLI now have a row each, because their flags and report schema move independently of us.
- **`vercel-deploy`** (web · operative) — the skill that actually ships a Next.js 16 project to Vercel, and the only one that sets `phase = "deployed"` for web. Preview → smoke → **staged** production (`vercel --prod --skip-domain`) → `vercel promote` → domains + DNS, plus a rollback runbook. It ships; it does not configure — `vercel.json`, region and the env-var matrix stay with `module-add deploy`, and a missing config routes there instead of being improvised. Grounded in the CLI docs' own *Preferred production commands*, which name `--skip-domain` / `promote` / `rollback` over `vercel alias`. References: `deploy-checklist.md`, `domains-dns.md`, `rollback-runbook.md`. **43 skills** now: 5 core · **15 web** · 2 agent · 16 mobile · 3 monorepo · 2 refactor.
- **Lint check #8** — bare-backtick skill references at a routing marker (`→ \`x\``, `invoke \`x\``, `use \`x\``…) are now verified against the skills on disk. Check #6 only saw `` `<name>/SKILL.md` `` paths, which is why a dangling reference could survive in prose.

### Changed
- The suite is **44 skills** (6 core · 15 web). `dev-flow` proposes all three gates at `feature_complete` and re-runs them in the `deployed` loop, and proposes `spec-review` earlier — when a chunk of work lands.
- `transitions` non-negotiable #2 (`prefers-reduced-motion`) is now labelled **machine-checkable**, pointing at the rule that verifies it; `forms` audit mode notes that passing *our conventions* does not imply passing the *user-facing outcome* (a textbook TanStack Form with no `<FormLabel>` passes the greps and fails the gate).
- **Contract**: the `feature_complete` row now routes web to `vercel-deploy`. Re-vendored to all 30 skills.
- Every reference to `setup-deploy` — a skill that was routed to but **never existed**, in `dev-flow`, `module-add`, `vercel-doctor` and the contract — now points at `vercel-deploy`. The name changed for two reasons: `setup-deploy` collides with an unrelated third-party skill of the same name that installs to `~/.claude/skills/`, and the *setup* has always belonged to `module-add deploy`.
- `dev-flow`'s README routing block no longer marks `feature_complete` / `deployed` as "(expo-rn only)" — web and the eve agent have owners there too.

## [1.0.0] — 2026-08-02

First **versioned** release. The suite has been in daily use since 2026-04-25 (183 commits); this is the point it became installable as a Claude Code plugin and started carrying a version.

### Added
- **Plugin distribution** — `.claude-plugin/plugin.json` + `marketplace.json`. Install with `/plugin marketplace add lukedj78/dev-flow` then `/plugin install dev-flow@dev-flow`, with automatic updates. `install.sh` remains for Codex / Copilot / Gemini / Cursor. The manifest's skill allowlist is **generated** from the canonical taxonomy (`scripts/build_plugin_manifest.py`), so it cannot drift.
- **41 skills** across six families: 5 core · 13 web · 2 agent · 16 mobile · 3 monorepo · 2 refactor.
- **`compliance-audit`** — GDPR + EU AI Act audit of an existing project (10-point risk register) with safe auto-remediation and flagged legal decisions; proposed as a pre-deploy gate.
- **`vercel-doctor`** — cost/performance pre-deploy gate; detects costly Vercel patterns and routes the real fixes to the owning skill.
- **`transitions`** — one tokenized motion system (cheapest-tier-first, `prefers-reduced-motion` always).
- **`heroicons-animated`** — Motion-animated Heroicons from the shadcn registry, with the accessibility guard the upstream components lack.
- **Knowledge principle (contract rule zero)** — the skills are a doc-grounded second brain: never invent an API; every "use library X" ships the *how* from X's official docs; `[VERIFY]` on fast-moving surfaces; periodic re-verification.
- **Golden rules** — ① all code (identifiers, constants, comments) is written in English, independent of the conversation language; ② every frontend ships i18n from day one (web `next-intl`, mobile the RN stack), minimum locales `en` + `it`, no hardcoded user-facing copy.
- **11 doc-grounded how-tos** for the library defaults: next-intl, i18n on RN, nuqs, Vercel Blob storage, Vercel deploy config, TanStack Query on RN, Zustand, Maestro, tw-animate-css, AI Elements, and maps (mapcn / mapcn-rn).
- **`docs/knowledge-index.md`** — the map of every how-to and the upstream to re-verify.
- **Obsidian vault** — committed `.obsidian/` config (markdown links, ignore filters, graph coloured by family) + `docs/OBSIDIAN.md`.
- **eve**: the `eve add` / `eve registry` integrations CLI, Slack `onMessage`/`onEvent` hooks and `ctx.cancel()`/`ctx.reset()` session controls, plus the audit-hook and read-vs-egress governance recipes.

### Changed
- **Contract**: `feature_complete` and `deployed` are now **cross-stack** (they were mobile-only, which meant the web compliance gate never fired); `monorepo_initialized` added to the phase enum.
- **Taxonomy**: family/role now come from one explicit map with **fail-fast** on an unclassified skill — the previous silent `"web"` fallback had misfiled `rn-upgrade` as web and flattened core/agent/monorepo/refactor skills into web.
- `nuqs` adopted as the canonical URL-state library for the "URL state" rung in `data-fetching` and `state-discipline`.
- Monorepo web token sharing now detects **Tailwind v4** (CSS-first `@theme`) with the v3 JS preset as fallback.
- Repository root cleaned: 41 skill folders + 6 support directories + 5 files (test artefacts, stray bundles and an empty `apps/` removed — all previously untracked).

### Fixed
Upstream verification caught guidance that was wrong in practice:
- `vercel-doctor` was documented without its required **path argument** — the real invocation is `npx -y vercel-doctor@latest .`.
- `mapcn` installs as a single namespaced item (`shadcn add @mapcn/map`), not per-component registry URLs; **`mapcn-rn` has no `init` command** at all.
- `tw-animate-css` ships **no shimmer utility** — the skeleton recipe now uses `animate-pulse` or a Tier-1 keyframe.
- FlashList v2 **deprecated** `estimatedItemSize` — "No longer used" (it was documented as required); Reanimated `Layout` → `LinearTransition`; Gesture Handler relabelled v3.
- React Native Firebase namespaced API → modular (rnfirebase.io: the namespaced API "is being completely removed in v22"; current major is v26); `@testing-library/jest-native` dropped (matchers are built into RNTL); Supabase session store moved off SecureStore (2 KB value limit truncates sessions).
- React Email 6 unified `@react-email/components` into `react-email`; `@hookform/resolvers` bumped to ^5 for Zod 4; Stripe `apiVersion` refreshed.
- nuqs `throttleMs` is deprecated in favour of `limitUrlUpdates: debounce(…)`; i18next dropped the v3 JSON format in **v24** — `compatibilityJSON` has accepted only `'v4'` since, on 26 as on 24 (Hermes still needs the `@formatjs/intl-pluralrules` polyfill).
- Two pairs of contradictory duplicate references consolidated to a single source of truth (Maestro setup, TanStack Query setup).

[Unreleased]: https://github.com/lukedj78/dev-flow/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/lukedj78/dev-flow/releases/tag/v1.0.0
