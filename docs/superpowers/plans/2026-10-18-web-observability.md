# Web observability Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A module, `module-add observability`, that gives a dev-flow web app error tracking, structured logs and an
uptime check, one level at a time, region-aware and private by default, with a mobile counterpart in
`rn-module-add`. A stdlib check proves each level is wired, and a local fake ingest proves events really leave the
app.

**Architecture:**
- The how-to is a reference, like every module: `module-add/references/module-observability.md`, and
  `rn-module-add/references/module-observability.md` for mobile.
- Two stdlib scripts in `module-add/scripts/`:
  - `observability_check.py` reads a project and reports, per active level, what is missing;
  - `fake_ingest.py` is a local Sentry-compatible receiver that records the envelopes it gets, for the account-free
    proof.
- dev-flow, `vercel-deploy` and `show_state` propose the module and read the check. Nothing blocks.

**Tech Stack:** Python 3.9+ stdlib; the templates are TypeScript for Next.js 16, using `@sentry/nextjs` 11.8.0 and
`@sentry/react-native`.

**Spec:** `docs/superpowers/specs/2026-10-18-web-observability-design.md`

## Global Constraints

- **Levels:** `stack.observability` is a list of `errors`, `logs` and `uptime`. `stack.observability_provider` is
  `{ "errors": "sentry | glitchtip", "logs": "axiom | betterstack | none", "uptime": "sentry | betterstack" }`.
- **Version:** `@sentry/nextjs` is pinned at `11.8.0`, checked 2026-10-18 (MIT, peer `next ^16.0.0-0`).
- **Region:** with `stack.data_residency` set to `eu` or `eu-sovereign`, the errors DSN host must end in
  `.ingest.de.sentry.io`, or be the project's GlitchTip host when `observability_provider.errors = "glitchtip"`. A US
  host (`.ingest.sentry.io` without `.de`, or `.ingest.us.sentry.io`) is a finding.
- **Privacy defaults:**
  - `sendDefaultPii: false`, with no Replay integration;
  - `beforeSend` drops request bodies, cookies and authorization headers, and redacts emails and `token=`/`code=`
    query values.
- **Release correlation:** `release: process.env.VERCEL_GIT_COMMIT_SHA` and `environment: process.env.VERCEL_ENV`.
- **No account is ever created** on the user's behalf. `SENTRY_AUTH_TOKEN` and the DSN go through
  `project-infra-setup`, never chat.
- **The health route** `app/api/health/route.ts` returns `{ ok, db, release }`, with 200 or 503, and no personal data.
- **No gate:** the module is proposed before the first production deploy, and at every deploy while it is missing.
- **Nothing is committed** in a user project.

## Review Focus

1. **A project with an `instrumentation.ts` that already exists** (for example `@vercel/otel` or eve's): the module
   adds `onRequestError` and the Sentry init without removing what is there, and the check accepts a
   `register()` that does both. Test owner: Task 1, the check's half.
2. **A DSN read from an env var** (`process.env.NEXT_PUBLIC_SENTRY_DSN`) rather than a literal: the region check
   reads `.env.example` / `.env.local` names and values when the code holds only the variable name, and says
   "region not checked" (not "ok") when no value is visible. Test owner: Task 1.
3. **`sendDefaultPii` set through a variable or a spread** (`...sharedOptions`): the check must not pass silently. When
   it cannot see the literal, it reports "privacy setting not visible" so a human reads it. Test owner: Task 1.
4. **The fake ingest receiving a gzip- or deflate-encoded envelope.** The Sentry SDK compresses on Node. It must
   decode it, not record garbage. Test owner: Task 1.
5. **An Expo project:** the web check reports "not a web project" for the web levels and points to
   `rn-module-add observability`, and never asks for `global-error.tsx` in an Expo app. Test owner: Task 1.

---

### Task 1: `observability_check.py` and `fake_ingest.py`

**Files:**
- Create:
  - `module-add/scripts/observability_check.py`;
  - `module-add/scripts/fake_ingest.py`;
  - `module-add/scripts/test_observability.py`;
  - `module-add/scripts/surfaces.py`, a vendored copy registered in `VENDORED_SOURCE`.

**Interfaces:**
- Produces:
  - `check(root: Path, meta: dict | None = None) -> list[Finding]`, where
    `Finding(level: str, status: "ok" | "found" | "not checked" | "not applicable", detail: str)`. The levels come
    from `meta.stack.observability`, or all three when it is called with `--all`.
  - CLI: `observability_check.py <root> [--all] [--json]`. It exits 1 when any finding has status `found`.
  - `fake_ingest.py serve --port 9010 --out <dir>`: accepts `POST /api/<project>/envelope/` and
    `/api/<project>/store/`, decodes gzip and deflate, and writes one JSON file per event to `<dir>`.
  - `fake_ingest.py summary <dir>`: prints a count, the releases, the levels, and whether any email address or
    `Authorization` value appears.
  - `parse_envelope(body: bytes) -> list[dict]`.

- [ ] **Step 1: Write the failing tests.**
  - `test_complete_errors_level_passes`;
  - `test_each_missing_piece_is_found`: `instrumentation.ts` without `onRequestError`, no
    `instrumentation-client.ts`, no `global-error.tsx`, an `error.tsx` that only `console.error`s, no `release`;
  - `test_existing_instrumentation_is_kept` (Review Focus 1);
  - `test_us_dsn_in_an_eu_project_is_found`;
  - `test_dsn_from_env_is_read_or_not_checked` (Review Focus 2);
  - `test_send_default_pii_true_is_found`;
  - `test_replay_integration_is_found`;
  - `test_pii_setting_not_visible` (Review Focus 3);
  - `test_logs_level_needs_logger_and_request_id`;
  - `test_uptime_level_needs_health_route`;
  - `test_expo_project_is_not_applicable` (Review Focus 5);
  - `test_parse_envelope_plain_and_gzip` (Review Focus 4);
  - `test_fake_ingest_records_and_summarises`: start the server on a free port in a thread, post a gzip envelope,
    then check the file written and the summary counts.
- [ ] **Step 2: Run them.** `cd module-add/scripts && python3 -m unittest test_observability`. Expected: errors.
- [ ] **Step 3: Implement**, stdlib only (`http.server`, `gzip`, `zlib`, `json`, `re`).
- [ ] **Step 4: Run them** on 3.14 and 3.9. Expected: OK.
- [ ] **Step 5: Commit** with `SKIP_REGEN=1` if needed:
  `feat(module-add): observability_check.py and a local fake ingest for the account-free proof`.

### Task 2: The web module — reference, templates, contract

**Files:**
- Create `module-add/references/module-observability.md`, with three sections, one per level, each stating what it
  installs, the exact files, and the check:
  - **errors:** `npm i @sentry/nextjs@11.8.0`; `instrumentation.ts`, with `register()` importing the server and edge
    configs and `export const onRequestError = Sentry.captureRequestError`; `instrumentation-client.ts`;
    `sentry.server.config.ts` and `sentry.edge.config.ts` sharing one `lib/observability/options.ts` (DSN, release,
    environment, `sendDefaultPii: false`, `beforeSend`); `next.config.ts` wrapped with `withSentryConfig`, with the
    source maps upload; `app/global-error.tsx`; the region rule; the GlitchTip variant;
  - **logs:** `lib/log.ts`; `x-request-id` set in `proxy.ts`, and tagged on the scope; the drain options for Pro, and
    the Hobby one-hour truth;
  - **uptime:** `app/api/health/route.ts`; the Sentry Uptime or Better Stack monitor steps;
  - **the proof:** `fake_ingest.py serve`, the DSN `http://public@localhost:9010/1`, two provoked errors (a Server
    Action and a client component), then `summary`.
- Create `design-md-to-app/references/global-error.template.tsx`.
- Modify:
  - `design-md-to-app/references/error.template.tsx`: report the error with `Sentry.captureException` when the
    module is present, and close the TODO;
  - `module-add/SKILL.md`: the module table row, `observability`, by level, with its reference; the description
    triggers (`"add error tracking"`, `"monitoring"`, `"aggiungi sentry"`, `"osservabilità"`);
  - `dev-flow/references/contracts.md`: `stack.observability` and `stack.observability_provider`, beside
    `analytics`, then propagated;
  - `dev-flow/references/eu-data-sovereignty.md` §4.9: a pointer to the module, re-checked 2026-10-18.

- [ ] **Step 1:** Write them. Run `python3 scripts/lint_skills.py`. Expected: `✓ Clean`.
- [ ] **Step 2: Commit:** `feat(module-add): observability — errors, structured logs and uptime, by level`.

### Task 3: The mobile module

**Files:**
- Create `rn-module-add/references/module-observability.md`: `@sentry/react-native` with the Expo config plugin,
  source maps in EAS builds, the same region and privacy rules, and `ObserveErrorBoundary` kept for EAS Observe.
- Modify:
  - `rn-module-add/SKILL.md`: the table row and the triggers;
  - `rn-eas-deploy/SKILL.md` and `rn-eas-deploy/references/observability.md`: "if configured" becomes a pointer to
    `rn-module-add observability`.
- [ ] **Step 1:** Write them, run the lint (`✓ Clean`), then commit:
  `feat(rn-module-add): observability — crash reporting for Expo, region-aware`.

### Task 4: Wiring

**Files:**
- Modify:
  - `dev-flow/scripts/show_state.py` and `test_show_state.py`: add `observability_line(meta: dict, root: Path) ->
    str | None` and call it from `main()`. At `feature_complete` or later, on a web or monorepo stack with an empty
    `stack.observability`, it returns a note pointing to `module-add observability`; otherwise `None`.
  - `dev-flow/SKILL.md`: a capability line.
  - `dev-flow/references/policies.md`: an `**Observability policy.**` paragraph.
  - `vercel-deploy/SKILL.md`, step 2: read `stack.observability`, run `observability_check.py`, and offer the module
    when it is empty, without blocking.
  - `module-add/references/module-email.md:274`: "your monitoring" points to `lib/log.ts`.
  - `README.md`: the non-goals line at `:1504` moves into the catalogue.
  - `CHANGELOG.md`.
- [ ] **Step 1: Write the failing tests:**
  - `test_no_note_before_feature_complete`;
  - `test_missing_observability_noted_on_web`;
  - `test_expo_points_to_rn_module_add`;
  - `test_present_is_silent`.
- [ ] **Step 2:** Run them. Expected: failures in the new tests only.
- [ ] **Step 3:** Implement, then make the prose edits.
- [ ] **Step 4:** Run `test_show_state`, routing `--check` and the lint. Expected: OK and `✓ Clean`.
- [ ] **Step 5: Commit:** `feat(dev-flow): propose observability before the first deploy, and read its check`.

### Task 5: The real run, account-free

- [ ] **Step 1: Make a copy.** In a scratch copy of fit-coach (`cp -R`, without `node_modules`, then `pnpm install
  --frozen-lockfile`), or in a git worktree, apply the `errors` level as the reference says. The DSN points to
  `fake_ingest.py serve`. Never touch the project's own checkout.
- [ ] **Step 2: Run the check.** `observability_check.py <copy> --all` reports `errors` as ok, and `logs` and
  `uptime` as found until those levels are applied.
- [ ] **Step 3: Start the app and provoke the errors.** Start the copy on its own port. Throw in a Server Action and
  in a client component. Then run `fake_ingest.py summary`. Expected:
  - 2 or more events;
  - the release is the copy's commit SHA;
  - no email address and no `Authorization` value.
- [ ] **Step 4: Fix and record.** Every defect the run finds gets a test first, then a fix. Record each one as a
  ruling, and commit.

### Task 6: Whole-branch verification

- [ ] Run the lint, every suite, bundles `--check`, routing `--check`, `comply.py selftest`, and the new suite on 3.9.
  Then:
  - the final review on the most capable model;
  - one fix pass, minors included, per the user's rule;
  - the PR, merged when CI is green.

## Spec coverage

| Spec | Task |
|---|---|
| §1 Levels and contract | 2 |
| §2 errors | 1 (check), 2 |
| §3 logs | 1, 2 |
| §4 uptime | 1, 2 |
| §5 mobile | 3 |
| §6 the check | 1, 4 |
| §7 the account-free proof | 1 (`fake_ingest`), 5 |
| §8 the flow | 4 |
| Tests | 1, 4, 5, 6 |
