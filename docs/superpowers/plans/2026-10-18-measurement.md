# Measurement Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Opt-in measurement for dev-flow projects, in three levels that can each be switched on at any time: traffic, product and advanced. Covered here: a *Measurement* section in the PRD, an `analytics` module for web (`module-add`) and for Expo (`rn-module-add`), and checks that apply only to projects that measure.

**Architecture:** The levels are recorded in a new contract key, `stack.analytics`, as a list of the active levels.
- **Traffic** is Vercel Web Analytics plus Speed Insights.
- **Product** is an `analytics_events` table in the project's own database, a server-side `track()` and SQL for activation and D7/D30 retention. It adds no sub-processor.
- **Advanced** is PostHog EU, or OpenPanel when the project's data residency is `eu-sovereign`.

The modules are prose references, following the pattern of the other modules. The mechanical parts are Python checks with unittests in `launch-audit`, `compliance-audit` and `data_residency.py`.

**Tech Stack:** Markdown skills; Python ≥ 3.9 stdlib scripts and their tests; TypeScript snippets type-checked on probe apps; Postgres SQL verified with PGlite in a scratch folder.

**Spec:** `docs/superpowers/specs/2026-10-18-measurement-design.md`. Read it in full before Task 1. Section numbers below (§N) refer to it.

## Global Constraints

- **Measurement is opt-in.** A project without `stack.analytics`, or with `[]`, is not measuring.
  - No skill asks about measurement twice.
  - No check counts it as a gap.
  - `launch-audit` reports it as "not requested".
- **Contract.**
  - `stack.analytics` is a list whose values are drawn from `"traffic"`, `"product"`, `"advanced"`. Absent or `[]` means not requested.
  - `stack.analytics_provider` is `"posthog" | "openpanel"`, and is set only when `"advanced"` is in the list.
  - `contract_version` stays `1`.
  - The edited `contracts.md` is propagated with: `for f in */references/contracts.md; do [ "$f" = dev-flow/references/contracts.md ] || cp dev-flow/references/contracts.md "$f"; done`
- **PRD section**, heading exactly `## Measurement`. Lines exactly:
  - `Levels: <comma list>`
  - `**Activation event**: \`<event_name>\``
  - `**Retention targets**: D7 ≥ <n> % · D30 ≥ <n> %`
  - `**False positives to watch**:`
  - `**Events to instrument**:`
- **Event names** are `snake_case`, past-tense verbs (e.g. `invoice_sent`), and match `^[a-z][a-z0-9_]*$`.
- **Product table** `analytics_events`, with columns `id`, `user_id`, `name`, `props` (JSON), `created_at`.
- **Web file paths:** `lib/analytics/events.ts`, `lib/analytics/track.ts`, `lib/analytics/metrics.ts`, script `npm run metrics`.
- **PostHog** always has its EU host written explicitly (`eu.i.posthog.com`); never rely on `@posthog/next`'s US default. Package versions checked on 2026-10-18:
  - `posthog-js` 1.438.12, `posthog-node` 5.56.2, `posthog-react-native` 4.81.2;
  - `@vercel/analytics` 2.0.1;
  - `@openpanel/nextjs` 1.5.1, `@openpanel/react-native` 1.4.1.
- **No sending** from preview or development (`VERCEL_ENV`).
- **On Firebase, product events go to Firestore** plus a Node metrics script, never Google Analytics for Firebase.
- **`launch-audit` stays web-only.** The mobile checks become lines in the `rn-eas-deploy` checklist.
- **Python ≥ 3.9, stdlib.** Run each changed suite on 3.14 and on 3.9 (`uv run -q --python 3.9 …`).
- **Commits:** commit locally per task; push and the PR only on the user's go-ahead.

## Review Focus

1. **A PRD whose Measurement says `TBD`, or has no activation event, in a project with `product`.** `measurement-targets` reports it and points to `prd-from-idea`; it never says OK. Test owner: Task 2.
2. **A project measuring only `traffic`.** No targets are demanded and `activation-instrumented` is not run (traffic has no targets). Test owner: Task 2.
3. **A monorepo.** `launch-audit` reads `.workflow/` at the project root while the code lives in `apps/web`. Both the PRD and the `track('<event>'` search must resolve. Test owner: Task 2.
4. **A PostHog init in one file and the consent gate in another.** The compliance check works per init file, so a project-wide consent string does not silence it. Equally, an init that imports the consent gate is not flagged. Test owner: Task 3.
5. **`stack.analytics_provider` set while `advanced` is not in the list.** This is a hand edit. The register check still names the implied provider, and `launch-audit` does not crash. Test owners: Tasks 1 and 2.

---

### Task 1: Contract, sub-processor register, residency reference

**Files:**
- Modify: `dev-flow/references/contracts.md`. In §stack, add the bullets for `analytics` and `analytics_provider`; in the Recommended-defaults table, add one row. Then copy the file to every `*/references/contracts.md`.
- Modify: `dev-flow/scripts/data_residency.py`. Add two entries to `IMPLIED` (around line 56): `("analytics_provider", "posthog"): "PostHog"` and `("analytics_provider", "openpanel"): "OpenPanel"`.
- Modify: `dev-flow/references/eu-data-sovereignty.md` §4.9 (lines 181-189).
  - Add a column `Retention D7/D30` (yes/no).
  - Add a row for Vercel Web Analytics, marked traffic only, no retention, cookieless.
  - Add a row for OpenPanel as the `eu-sovereign` default.
  - Mark Plausible, Pirsch and Vercel as having no retention.
- Test: `dev-flow/scripts/test_data_residency.py`

**Interfaces:**
- Produces: the contract shape in Global Constraints. Tasks 2, 4, 5 and 6 read `stack.analytics` and `stack.analytics_provider`.

- [ ] **Step 1:** Write `test_analytics_provider_is_implied`, modeled on `test_missing_rows_and_config_regions`.
  - Project `data_residency="eu"`, `analytics=["traffic","advanced"]`, `analytics_provider="posthog"`: `dr.check(root)["warnings"]` contains `"implies PostHog"`.
  - Same with `"openpanel"` → `"implies OpenPanel"`.
  - A project with `analytics=["product"]` and no provider adds no analytics warning (Review Focus 5's other side).
  - Use the existing `project()` helper; add `analytics` and `analytics_provider` keys to `stack` if the helper only takes keyword stack keys.
- [ ] **Step 2:** Run `cd dev-flow/scripts && python3 -m unittest test_data_residency -v`. Expected: the new test FAILS (no warning).
- [ ] **Step 3:** Add the two `IMPLIED` entries. Write the contract bullets, in the house format:
  - `` `analytics` (optional — only when the user asks to measure): list of "traffic" | "product" | "advanced"; absent or [] = not requested ``
  - `` `analytics_provider` ("posthog" | "openpanel", only with "advanced") ``
  - Each bullet carries a how-to path to `module-add/references/module-analytics.md`.

  Add the defaults row: analytics → traffic: Vercel Web Analytics; product: own DB; advanced: PostHog EU / OpenPanel (eu-sovereign). Then do the §4.9 table edits.
- [ ] **Step 4:** Propagate `contracts.md`. Run the data_residency tests on 3.14 and 3.9 and `python3 scripts/lint_skills.py`. Expected: OK, `✓ Clean`.
- [ ] **Step 5:** Commit: `feat(contract): stack.analytics levels and provider; analytics providers in the register`.

### Task 2: `launch-audit` — measurement checks that apply only when the project measures

**Files:**
- Modify: `launch-audit/scripts/scan_launch.py` (the analytics block at lines 417-427, and `scan()`)
- Modify: `launch-audit/references/checks.md` (`analytics-absent` at line 175; add `measurement-targets` and `activation-instrumented`), `launch-audit/SKILL.md` (the routes table at line 95)
- Test: `launch-audit/scripts/test_scan_launch.py`

**Interfaces:**
- Consumes: `stack.analytics`, from `<root>/.workflow/meta.json`. The project root is the `scan()` argument, also in a monorepo where `app_dir` is `apps/web/app`.
- Produces:
  - `read_measurement(root: Path) -> dict | None`. It parses `## Measurement` from `<root>/.workflow/PRD.md` into `{"levels": [...], "activation": str|None, "d7": str|None, "d30": str|None}`, or returns `None` when the section is absent.
  - Status value `NOT_REQUESTED = "not requested"`, beside `OK`, `MISS` and `UNKNOWN`.

- [ ] **Step 1: Write the failing tests**, in the file's `check(...)` style, with temp projects built with `build()`:
  - **Not measuring** (meta without `analytics`): `analytics-absent` is `"not requested"`, and `measurement-targets` and `activation-instrumented` are `"not requested"`. The existing test `"no analytics dep → reported"` changes: that fixture gets `stack.analytics=["traffic"]` so it still asserts `missing`.
  - `analytics=["traffic"]` with `@vercel/analytics` in `package.json`: `analytics-absent` is ok, and `measurement-targets` is ok with detail containing `"traffic only"` (Review Focus 2).
  - `analytics=["product"]` and:
    - no `## Measurement` → `measurement-targets` missing, routed to `prd-from-idea`;
    - a section with `TBD` in D7 → missing (Review Focus 1);
    - a complete section with `` `invoice_sent` `` and no `track(` in the code → `activation-instrumented` missing, routed to `module-add analytics`;
    - `track(userId, 'invoice_sent'` in `app/actions.ts` → ok;
    - a `lib/analytics/track.ts` file counts as product wiring for `analytics-absent`.
  - **Monorepo** (Review Focus 3): `.workflow/` at the root, `apps/web/app/page.tsx`, and `track(u, "invoice_sent"` in `apps/web/app/actions.ts` → ok.
  - `@openpanel/nextjs` in deps → `analytics-absent` ok.
  - `analytics_provider="posthog"` without `advanced` → no exception, findings still produced (Review Focus 5).
- [ ] **Step 2:** Run `python3 launch-audit/scripts/test_scan_launch.py`. Expected: the new checks FAIL.
- [ ] **Step 3: Implement.**
  - Read `meta.json` with `json` and tolerate a missing or invalid file: treat it as not measuring.
  - `analytics-absent` regex: add `@openpanel/`; route to `module-add analytics`.
  - `measurement-targets` applies only when `"product"` is in the levels. A value counts as missing when it is `None` or contains `TBD`.
  - `activation-instrumented` searches `*.ts`/`*.tsx` under `app.parent` (excluding `node_modules`) for `track(` followed on the same line by the quoted event name.
- [ ] **Step 4:** Run the test file on 3.14 and 3.9. Expected: all pass. Update `checks.md` with the two checks (looks for / routes to / legitimately fine when) and the routes table in `SKILL.md`.
- [ ] **Step 5:** Commit: `feat(launch-audit): measurement checks only where the project chose to measure`.

### Task 3: `compliance-audit` — a client analytics SDK that sets identifiers before consent

**Files:**
- Modify: `compliance-audit/scripts/scan.py` (`CHECKS`, `PATTERNS`, `scan()` and the returned signals)
- Modify: `compliance-audit/references/gdpr-ai-act-checklist.md` (R2's audit signal, lines 18-22) and `compliance-audit/SKILL.md` (the risk register row)
- Test: `compliance-audit/scripts/test_scan.py`

**Interfaces:**
- Produces:
  - New signal `has_cookie_analytics_before_consent: bool`.
  - New check `("R11", "H", "Art.6/7 ePrivacy", "Client analytics sets identifiers before consent", lambda s: s["has_cookie_analytics_before_consent"])`.
  - `base_signals()` in the test gains the key, default `False`.

- [ ] **Step 1: Write the failing tests.**
  - Pure: `evaluate(base_signals(has_cookie_analytics_before_consent=True))` contains R11; the clean project does not.
  - Filesystem, using `scan(root)` on temp trees:
    - `instrumentation-client.ts` with `posthog.init('k', { api_host: '/ph' })` → signal True;
    - same file with `cookieless_mode: 'always'` → False;
    - same file importing from `@/lib/consent` → False;
    - the init without a gate, plus a `CookieConsent` component in another file → still True (Review Focus 4);
    - only `@vercel/analytics` `<Analytics />` → False;
    - only `@openpanel/nextjs` → False (cookieless).
- [ ] **Step 2:** Run `cd compliance-audit/scripts && python3 -m unittest test_scan -v`. Expected: the new tests FAIL.
- [ ] **Step 3: Implement.** Do a per-file pass inside the existing walk. A file that matches `posthog\.init\(` and matches neither `cookieless_mode` nor `consent` (case-insensitive) sets the signal. Add R11 to `CHECKS`. In the checklist and `SKILL.md`, R11 is described as heuristic and verified by reading the init.
- [ ] **Step 4:** Run the suite on 3.14 and 3.9. Expected: OK.
- [ ] **Step 5:** Commit: `feat(compliance-audit): flag a client analytics SDK initialised before consent`.

### Task 4: `module-add analytics` (web)

**Files:**
- Create: `module-add/references/module-analytics.md`
- Create: `module-add/assets/analytics/metrics.sql` (the canonical activation and retention SQL, Postgres)
- Modify: `module-add/SKILL.md`
  - In the modules table (lines 12-27), add the row `| \`analytics\` | Vercel Web Analytics (traffic) · own-DB events (product) · PostHog EU / OpenPanel (advanced) | \`references/module-analytics.md\` | ✅ implemented |`.
  - Add a cross-module dependency line: `product` needs `db`.
- Modify: `module-add/references/module-deploy.md:251`, a one-line pointer to the module for the `VERCEL_ENV` rule.

**Interfaces:**
- Consumes:
  - the contract (Task 1);
  - the PRD `## Measurement` format (Global Constraints);
  - `data_residency.py add` (existing);
  - the consent gate `lib/consent.ts` from `compliance-audit`.
- Produces:
  - `track(userId: string, event: AnalyticsEvent, props?: Record<string, unknown>): Promise<void>` in `lib/analytics/track.ts`. It never throws.
  - `type AnalyticsEvent` in `lib/analytics/events.ts`, generated from the PRD list.
  - `activation(cohortDays)` and `retention()` in `lib/analytics/metrics.ts`, which wrap `metrics.sql`.
  - All of these are named in Task 5 (mobile parity) and Task 6 (`prd-from-idea`, the routing).

- [ ] **Step 1:** Write `metrics.sql`. It holds two queries over `analytics_events` and the users' signup time, which is the first event or the users table, stated in the file:
  - activation rate per weekly signup cohort;
  - D7 and D30 retention of activated users per cohort, where retained on D*n* means an event in the window `[signup + n days, signup + n+1 days)` (the definition is stated in the file).
- [ ] **Step 2: Verify the SQL on real Postgres.** In a fresh scratch folder:
  1. `npm init -y && npm i @electric-sql/pglite`;
  2. a script creates the table, inserts 3 users with known dates (one activated and back on day 7 and day 30, one activated and never back, one never activated), runs `metrics.sql`;
  3. assert activation 2/3, D7 1/2, D30 1/2.

  Expected: the asserted numbers. Record the command and the output in the ledger. Nothing is added to the repo's dependencies.
- [ ] **Step 3:** Write `module-analytics.md` in the skeleton of `module-email.md`: idempotency check, prerequisites, install, files to write, environment variables, verification, update meta.json, known caveats. It has one part per level, as in spec §5.
  - **Before anything else:** read `stack.analytics`. If the PRD has no `## Measurement` and the request includes `product`, ask the metric questions and write the section into PRD.md as a revision (spec §3), then continue.
  - **Traffic:** `@vercel/analytics/next` `<Analytics />` and `@vercel/speed-insights/next` `<SpeedInsights />`, guarded on `VERCEL_ENV === 'production'`.
  - **Product:**
    - the Drizzle schema for `analytics_events`;
    - `events.ts`, a union type generated from the PRD list;
    - `track.ts`: a server-only insert, never throws, no-op outside production unless `ANALYTICS_DEV=1`;
    - `metrics.ts`, which wraps `metrics.sql`, and the `metrics` npm script;
    - a note that rows follow account deletion (DSAR).
  - **Advanced:** spec §5 verbatim decisions:
    - PostHog EU, `instrumentation-client.ts`, cookieless for anonymous traffic, `identify()` only behind the consent gate;
    - rewrites on a neutral path, `posthog-node` with `flushAt: 1, flushInterval: 0` and `await shutdown()`;
    - OpenPanel self-hosted for `eu-sovereign`;
    - `track()` forwards to the provider;
    - step 1b: `data_residency.py add`.
  - **Update meta.json:** add the level to `stack.analytics` without removing others; set `analytics_provider` only with `advanced`.
  - **Caveats:**
    - Vercel custom events need Pro, and product does not use them;
    - `@posthog/next` defaults to US;
    - do not name the proxy path `/analytics`.
- [ ] **Step 4: Type-check the TypeScript snippets** from the reference (`events.ts`, `track.ts` with a stubbed `db`, `metrics.ts`) in a scratch Next app with `tsc --noEmit`. Use a fresh `create-next-app` in the scratchpad if none exists. Expected: no errors. Record the result.
- [ ] **Step 5:** Run `python3 scripts/lint_skills.py`. Expected: `✓ Clean`; fix any stated module count it reports. Commit: `feat(module-add): analytics module — traffic, product from the project's own database, advanced on request`.

### Task 5: `rn-module-add analytics` and the mobile release checks

**Files:**
- Create: `rn-module-add/references/module-analytics.md`
- Modify: `rn-module-add/SKILL.md`. In the module list and the Contract bullets, add: `analytics` module → `meta.json#stack.analytics` (and `analytics_provider`).
- Modify: `rn-module-add/references/module-matrix.md`. New `## analytics` table with the provider rows Supabase, Firebase, Custom REST and tRPC, plus a PostHog RN row (advanced).
- Modify: `rn-eas-deploy/references/deploy-checklist.md`. Two lines that apply only when `stack.analytics` is non-empty:
  - Measurement targets present in the PRD without TBD (when `product` is on);
  - the activation event appears in a `track(` call.
- Modify: `rn-publishing-payments/references/review-guidelines.md`. One line: with `product` or `advanced`, declare analytics data in the App Store privacy label and in Play Data safety.

**Interfaces:**
- Consumes: the event naming, the PRD format and the `track()` signature from Task 4. On mobile the user id comes from the auth module, so the signature is `track(event, props?)`.

- [ ] **Step 1:** Write the reference, following spec §8.
  - Traffic: not applicable; App Store Connect and Play Console provide it, and the module says so and installs nothing.
  - Product, per backend:
    - **Supabase:** table plus the RLS insert policy `with check (user_id = auth.uid())`; `track()` inserts through the existing Supabase client; the metrics are the same SQL as `module-add/assets/analytics/metrics.sql`, by reference.
    - **Firebase:** Firestore collection plus a security rule allowing a create only when `request.resource.data.user_id == request.auth.uid`; a Node metrics script with the Admin SDK.
    - **Custom REST / tRPC:** `POST /events` or a procedure calling the backend's `track()`. In a monorepo the backend is the web product level.
  - The catalogue lives in the monorepo's shared package when one exists.
  - `track()` never blocks; events are queued in memory and in AsyncStorage while offline, and flushed on reconnect.
  - Advanced: `posthog-react-native` via `npx expo install`, the EU host explicit, `identify()` after in-app consent; no ATT prompt (no advertising identifier); OpenPanel RN for `eu-sovereign`.
  - The reminder about the store privacy labels.
- [ ] **Step 2: Type-check** the Supabase variant's `events.ts` and `track.ts` (a typed client stub is fine) with `npx tsc --noEmit` in the Expo SDK 58 probe app. If the probe app is gone, scaffold one with `rn-bootstrap/scripts/init-expo-app.sh`. Expected: no errors. RLS and Firestore rules are not executed: state it.
- [ ] **Step 3:** Matrix, `SKILL.md`, checklist and review-guidelines edits. Run `python3 scripts/lint_skills.py`. Expected: `✓ Clean`.
- [ ] **Step 4:** Commit: `feat(rn-module-add): analytics module for Expo — product per backend, advanced with PostHog RN`.

### Task 6: Where measurement is chosen — `prd-from-idea`, Founder Intelligence, dev-flow

**Files:**
- Modify: `prd-from-idea/SKILL.md`:
  - Step 3: one question after Q5, *"Do you want to measure how the product is used?"*. No ends the subject. Yes asks the activation moment, the D7/D30 targets, the false positives and the events.
  - The PRD.md template: an optional `## Measurement` section, in the Global Constraints format, after *User stories*.
  - The founder-path paragraph: locked metrics go to `## Measurement`, and the levels start as `traffic, product`.
  - Autonomous runs: no measurement without an explicit request.
- Modify: `founder-intelligence/references/stages.md` §9: the metrics use the Measurement format and the event naming rule.
- Modify: `dev-flow/SKILL.md`. One line in the maintenance or horizontal capabilities: "measure usage / aggiungi gli analytics" → `module-add analytics` (web) or `rn-module-add analytics` (Expo), at any phase.
- Modify: `dev-flow/references/contracts.md` §PRD.md, one bullet: the optional Measurement section. Propagate.

- [ ] **Step 1:** Make the edits. Run `python3 scripts/lint_skills.py`. Expected: `✓ Clean`, including check 20, the shared-trigger reciprocity. If a trigger phrase is shared, add the reciprocal `Not for:`.
- [ ] **Step 2:** Commit: `feat(prd-from-idea): an optional Measurement section, asked once; founder path and routing`.

### Task 7: Registration, CHANGELOG, bundles

**Files:**
- Modify: `README.md`. Add the module to the `module-add` catalogue section, and replace the line "Analytics / observability. Too project-specific to template." (line 1490) with a pointer to the module, keeping observability as future work.
- Modify: `CHANGELOG.md`, one Added entry.
- Regenerate: the bundles, through the pre-commit hook or `python3 scripts/build_skill_bundles.py`.

- [ ] **Step 1:** Make the edits. Run `python3 scripts/build_skill_bundles.py`, then `--check`. Expected: `✓ dist/ matches the sources`.
- [ ] **Step 2:** Run `python3 scripts/run_skill_tests.py`. Expected: every suite passes.
- [ ] **Step 3:** Commit: `docs: measurement in the README and CHANGELOG`.

### Task 8: Whole-branch verification

- [ ] **Step 1:** Run `python3 scripts/lint_skills.py`, `python3 scripts/run_skill_tests.py`, `python3 scripts/build_skill_bundles.py --check`, `python3 scripts/sync_routing_table.py --check` and `python3 evals/compliance/comply.py selftest`. Then run the launch-audit, compliance-audit and data_residency suites on 3.9. Expected: all clean or passing.
- [ ] **Step 2:** By hand, run `launch-audit/scripts/scan_launch.py` on a temp project with no `analytics` and confirm "not requested". Then run it with `analytics=["traffic","product"]`, a complete Measurement section and a `track` call, and confirm OK.
- [ ] **Step 3:** Report: files changed; the PGlite SQL result and the two `tsc` results (or that they were not run); what was not executed (RLS and Firestore rules).

## Spec coverage

| Spec | Task |
|---|---|
| Decisions 1–4 (opt-in, later activation, Vercel-centred mix, React Native) | 2, 4, 5, 6 |
| §1 Levels | 4, 5 |
| §2 Contract, `IMPLIED` | 1 |
| §3 How it is switched on (start, founder path, later, autonomous) | 4 (later), 6 |
| §4 Measurement section | 6, format in Global Constraints |
| §5 Web module, §4.9 residency table | 4, 1 |
| §6 launch-audit | 2 |
| §7 compliance-audit | 3 |
| §8 React Native, store labels, mobile release checks | 5 |
| §9 Founder Intelligence | 6 |
| Tests | 1, 2, 3, 4 (PGlite, tsc), 5 (tsc), 8 |
