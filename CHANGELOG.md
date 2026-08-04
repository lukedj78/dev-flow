# Changelog

All notable changes to the dev-flow skill suite. Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versioning is [semver](https://semver.org/) on the **suite as a whole** (the version in `.claude-plugin/plugin.json`).

What a bump means here:
- **major** — a breaking change to the `.workflow/` contract (phase enum, `meta.json` schema, a skill's inputs/outputs) that existing projects must migrate for.
- **minor** — new skills, new capabilities, new doc-grounded references, non-breaking contract additions.
- **patch** — fixes to existing guidance, upstream re-verification, docs.

## [Unreleased]

_Nothing yet._

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
