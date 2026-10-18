# app-security Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a fifth pre-deploy gate, `app-security`. It scans dependencies, secrets and Next.js-specific risks, guides a code-reading review, and offers Strix as an opt-in dynamic test. It reports and routes like the other four gates and never blocks.

**Architecture:** One new skill folder.
- `scripts/scan_security.py` (stdlib) has two halves:
  - wrappers for the external tools (OSV-Scanner or `pnpm audit`/`npm audit`, gitleaks, Semgrep), with their output parsers;
  - our own heuristic Next.js checks.

  Both feed a single list of findings, in the same shape `launch-audit` uses.
- The prose lives in `SKILL.md` plus three references: `review.md`, `dynamic.md` and `contracts.md`.
- The gate is wired into the same places that list the other four gates today.

**Tech Stack:** Python ≥ 3.9 stdlib with `unittest`; Markdown; recorded JSON tool outputs as fixtures. No tool runs in CI.

**Spec:** `docs/superpowers/specs/2026-10-18-app-security-design.md`. Read it in full before Task 1; §N below refers to it.

## Global Constraints

- **Statuses.** Exactly `OK = "ok"`, `FOUND = "found"`, `NOT_CHECKED = "not checked"`.
  - A missing tool, no network, or a tool error is `not checked`. It is never `ok`.
  - A run where no external tool ran must not print "clean" anywhere.
- **External tool commands**, exactly:
  - `osv-scanner scan source -r <root> --format json`. Exit codes: 0 clean, 1 vulnerabilities, 127 error, 128 no packages.
  - Fallback: `pnpm audit --json --prod` when there is a `pnpm-lock.yaml`, otherwise `npm audit --json --omit=dev`.
  - `gitleaks dir <root> --redact --report-format json --report-path <tmp>` and `gitleaks git <root> --redact --report-format json --report-path <tmp>`. Exit codes: 0 clean, 1 leaks, 126 bad flag.
  - `semgrep scan --config p/nextjs --config p/typescript --metrics off --json <root>`.
- **Semgrep rules are never copied into the repo.** They are fetched at run time.
- **Nothing is installed by the skill.** It prints the install command (`brew install osv-scanner gitleaks`, `pipx install semgrep`, `pipx install strix-agent`) and asks.
- **Strix** runs only on an explicit request, only against `localhost` or a preview of the user's own app, and never against production with real data. Docker and an LLM API key are required, and Strix does not use the Claude subscription.
- **Default session calls:** `getSession`, `getCurrentUserId`, `getCurrentTenantId`, `requireUser`, `verifySession`, `auth(`. A project adds its own in `meta.json#stack_config.security_session_calls` (a list of names).
- **Public env names never flagged:** names containing `ANON_KEY`, `PUBLISHABLE`, `POSTHOG_KEY`, `SITE_KEY`, `_URL`.
- **`meta.json#security`** has exactly the shape in spec §5. Each run writes it and appends a history entry; it never changes `phase`.
- **Dates:** Python ≥ 3.9. Run the new suite on 3.14 and on 3.9.
- **Commits:** commit locally per task. Push and the PR happen only on the user's go-ahead.

## Review Focus

1. **A tool that fails on its own.** No network, OSV exit 127/128, or gitleaks exit 126 must read `not checked`, not `found` and not `ok`. Test owner: Task 2.
2. **A monorepo** whose server actions live in `apps/web/` and `packages/api/`: both are scanned. Test owner: Task 1.
3. **A session check reached through the project's own helper** (`await requireOwner(id)`): a project that declares it in `stack_config.security_session_calls` is not flagged; an undeclared helper is. Test owner: Task 1.
4. **A secret only in git history**, already deleted from the working tree: it is reported, first, with "rotate it". Test owner: Task 2.
5. **An Expo project with no Next `app/` directory:** the Next.js checks report `not applicable` (status `ok`, detail saying so); `EXPO_PUBLIC_` secrets and dependencies are still checked. Test owner: Task 1.

---

### Task 1: The scanner's own Next.js checks

**Files:**
- Create: `app-security/scripts/scan_security.py`
- Create: `app-security/scripts/test_scan_security.py`

**Interfaces:**
- Produces:
  - `@dataclass Finding(check: str, status: str, detail: str, where: list[str] = [], routed_to: str | None = None)`
  - `code_findings(root: Path) -> list[Finding]`
  - `source_roots(root: Path) -> list[Path]`, which returns the app and package folders to scan: the root, `apps/*` and `packages/*` when they exist.
  - `session_calls(root: Path) -> list[str]`, the defaults plus `stack_config.security_session_calls`.
  - Check names, exactly: `server-action-unauthenticated`, `route-handler-unauthenticated`, `query-by-id-unscoped`, `action-returns-row`, `public-env-secret`, `server-only-missing`, `raw-sql`, `security-headers-missing`.
  - Routes:
    - `module-add auth` for unauthenticated actions and routes;
    - `the code owner` for unscoped queries, returned rows and raw SQL;
    - `the user` for env secrets (rotate them);
    - `vercel-deploy` for headers.

- [ ] **Step 1: Write the failing tests.** One fixture tree per case, built in a temp dir, matching the style of `launch-audit/scripts/test_scan_launch.py` or unittest:
  - `test_action_without_session_is_found`: an `app/actions.ts` with `"use server"` and `export async function deleteInvoice(id: string) { await db.delete(invoices).where(eq(invoices.id, id)) }` → `server-action-unauthenticated` found, with the file in `where`.
  - `test_action_with_session_is_ok`: the same function, but its body starts with `const userId = await getCurrentUserId()` → ok.
  - `test_declared_helper_is_a_session_call` (Review Focus 3): the body calls `await requireOwner(id)`. With `stack_config.security_session_calls=["requireOwner"]` in `.workflow/meta.json` → ok; without it → found.
  - `test_route_handler_post_without_session_is_found`, and `test_route_get_is_not_judged`: only POST, PUT, PATCH and DELETE handlers are judged.
  - `test_query_by_input_id_without_owner_filter_is_found`: `where(eq(invoices.id, id))` → found. `where(and(eq(invoices.id, id), eq(invoices.userId, userId)))` → ok.
  - `test_action_returning_a_row_is_found`: `return await db.insert(x).values(v).returning()` in a `"use server"` file → found.
  - `test_public_env_secret_is_found`: a `.env.example` with `NEXT_PUBLIC_STRIPE_SECRET_KEY=` → found. `NEXT_PUBLIC_SUPABASE_ANON_KEY=` and `NEXT_PUBLIC_POSTHOG_KEY=` → ok. `EXPO_PUBLIC_API_TOKEN=` → found.
  - `test_server_only_missing`: `lib/db/index.ts` without `import "server-only"` → found.
  - `test_raw_sql`: `sql.raw(\`select * from t where id = ${id}\`)` → found.
  - `test_security_headers`: no `headers()` in `next.config.*` and no CSP anywhere → found. A `next.config.ts` with `async headers()` that returns a `Content-Security-Policy` → ok.
  - `test_monorepo_packages_are_scanned` (Review Focus 2): the unauthenticated action is in `packages/api/src/actions.ts` → found.
  - `test_expo_project_skips_next_checks` (Review Focus 5): only `app.json` with expo, plus `.env` containing `EXPO_PUBLIC_SECRET=`. The Next checks are ok with `not applicable` in the detail; `public-env-secret` is found.
  - `test_node_modules_ignored`.
- [ ] **Step 2:** Run `cd app-security/scripts && python3 -m unittest test_scan_security -v`. Expected: FAIL (no module).
- [ ] **Step 3: Implement** the dataclass, the constants and the eight checks.
  - **Finding the action bodies.** A `"use server"` file is judged per exported function. Take the function's text from its declaration to the next top-level `export` or the end of the file, and look in it for any session call.
  - **Unscoped queries.** An `eq(<table>.id, <ident>)` is unscoped when the same `.where(...)` call has no `eq(<table>.(userId|tenantId|ownerId|orgId), …)`.
  - Every detail says the check is heuristic and must be verified by reading the code.
- [ ] **Step 4:** Run the suite on 3.14 and 3.9. Expected: OK.
- [ ] **Step 5:** Commit: `feat(app-security): the scanner's own Next.js checks`.

### Task 2: External tools — dependencies, secrets, static analysis

**Files:**
- Modify: `app-security/scripts/scan_security.py`
- Create: `app-security/scripts/fixtures/{osv.json, pnpm-audit.json, npm-audit.json, gitleaks.json, semgrep.json}`. These are recorded outputs, trimmed to two findings each, written by hand from each tool's documented schema.
- Modify: `app-security/scripts/test_scan_security.py`

**Interfaces:**
- Consumes: `Finding` and the status constants from Task 1.
- Produces:
  - `tool_findings(root: Path, run=subprocess.run, which=shutil.which) -> list[Finding]`, with check names `dependencies`, `secrets-working-tree`, `secrets-history` and `static-analysis`;
  - `scan(root: Path, run=..., which=...) -> list[Finding]`, which returns the tool findings followed by `code_findings`;
  - `main(argv) -> int`, with `--json`. The printed report lists `secrets-history` first when it is found and adds "rotate it — deleting the file does not remove it from history". Its last line counts found and not checked separately.

- [ ] **Step 1: Write the failing tests.** Use an injected `which` and `run` returning `CompletedProcess` with the fixture text:
  - `test_no_tools_means_not_checked`: `which` always returns `None` and there is no network → all four tool checks are `not checked`, and the printed report contains no "clean".
  - `test_osv_findings_parsed`: fixture with exit 1 → `dependencies` found, two packages listed. Exit 0 → ok.
  - `test_osv_errors_are_not_checked` (Review Focus 1): exit 127 → not checked, and exit 128 → not checked.
  - `test_falls_back_to_pnpm_then_npm_audit`: OSV absent, `pnpm-lock.yaml` present → the `pnpm audit` command is the one run. With no lockfile → `npm audit`. A non-JSON or empty output (no network) → not checked.
  - `test_gitleaks_working_tree_and_history` (Review Focus 4): working tree exit 0 and history exit 1 with the fixture → `secrets-working-tree` ok, `secrets-history` found. In the printed report, `secrets-history` comes first and the line contains "rotate".
  - `test_gitleaks_bad_flag_is_not_checked`: exit 126.
  - `test_semgrep_results_parsed`, and `test_semgrep_absent_is_not_checked`.
  - `test_commands_are_exactly_the_documented_ones`: assert the argv passed to `run` for each tool equals the Global Constraints commands. The report path is a temp file and is excluded from the comparison.
- [ ] **Step 2:** Run the suite. Expected: the new tests FAIL.
- [ ] **Step 3: Implement** the runners and parsers.
  - Parse only fields that exist in the tools' JSON schemas:
    - OSV: `results[].packages[].vulnerabilities[].id`
    - npm and pnpm: `metadata.vulnerabilities` or `advisories`
    - gitleaks: a list of `{File, RuleID}`
    - semgrep: `results[].check_id` / `path`
  - Every subprocess call has `timeout=600` and `capture_output=True`. A timeout reads not checked.
- [ ] **Step 4:** Run the suite on 3.14 and 3.9. Expected: OK.
- [ ] **Step 5:** Commit: `feat(app-security): dependencies, secrets and static analysis through the tools that exist`.

### Task 3: The skill's prose and the contract

**Files:**
- Create: `app-security/SKILL.md`, `app-security/references/review.md`, `app-security/references/dynamic.md`, and `app-security/references/contracts.md` (a copy of the canonical contract)
- Modify: `dev-flow/references/contracts.md`. Add a `### \`security\` field (owned by \`app-security\`)` section with the spec §5 JSON and the `stack_config.security_session_calls` key, then propagate the file to every `*/references/contracts.md`.
- Modify: `dev-flow/references/resources.md`. Add a Strix row under the tools section: price (free CLI, LLM tokens on the user's key), what it does, its limits (Docker, authorized targets only), install with `pipx install strix-agent`, checked 2026-10-18.

**Interfaces:**
- Consumes: the scanner CLI (`python3 app-security/scripts/scan_security.py <root> [--json]`) and its check names (Tasks 1–2).

- [ ] **Step 1:** Write `SKILL.md`.
  - **Frontmatter:** `name: app-security`. The description is ≤ 1024 characters and contains `Triggers` and `Not for:`.
    - Triggers: "security review", "è sicura l'app?", "controllo di sicurezza prima del deploy", "IDOR", "secrets in the repo", "pentest".
    - `Not for:` GDPR and legal (`compliance-audit`), UI quality (`shadscan`), cost (`vercel-doctor`), launch readiness (`launch-audit`), a diff-only review (Claude Code's `/security-review`), third-party registry code (`registry-intake`).
  - **Body:**
    - the three levels from spec §1;
    - run the scanner, then read the code with `references/review.md` on every flagged file and on every action and route;
    - tools missing → print the install command and ask (spec §7);
    - the dynamic level → `references/dynamic.md`;
    - record `meta.json#security`, with `accepted` holding the user's reasons;
    - never bump `phase`; never block;
    - Expo and eve notes;
    - "the fifth pre-deploy gate", with how it differs from the other four.
- [ ] **Step 2:** Write `review.md`, ordered by OWASP Top 10:2025, following spec §3: A01, A02, A03, A05, A07, data over-exposure, Expo, eve.
  - Each entry has what to look at, a right example and a wrong example in the dev-flow stack (better-auth `getCurrentUserId()`, Drizzle, Zod), and a link to the source: the Next.js Data Security guide, OWASP, the API Security Top 10 BOLA page.
  - Mention `/security-review` as an optional pass on the branch diff.
- [ ] **Step 3:** Write `dynamic.md`, following spec §4:
  1. the authorization rule, written first and stated to the user before any run;
  2. prerequisites;
  3. a test user created for the run;
  4. `strix --target <local or preview URL> --instruction "<two test accounts…>" -n`;
  5. how proven findings enter the report and `meta.json#security.dynamic`;
  6. cost: tokens on the user's provider key.
- [ ] **Step 4:** Write the contract section and propagate it, then add the resources row. Run `python3 scripts/lint_skills.py`. Expected: `✓ Clean`, apart from the registration warnings fixed in Task 5.
- [ ] **Step 5:** Commit: `feat(app-security): the skill, its review checklist and the opt-in dynamic level`.

### Task 4: The fifth gate in the flow

**Files:**
- Modify: `dev-flow/SKILL.md`
  - line ~189: "Propose the four pre-deploy gates" becomes five, adding `app-security` (technical security, any stack);
  - lines ~199-203: add a capability line `**Security** — app-security, the fifth pre-deploy gate`;
  - the routing table is regenerated in Step 3.
- Modify: `dev-flow/scripts/show_state.py`
  - `PHASE_NEXT_BY_STACK`: add `app-security` to the `feature_complete` and `deployed` strings for `next` (`:38-39`), `monorepo` (`:59-60`) and `expo-rn` (`:48-49`);
  - add it to `agent` (`:66-67`) too, because eve agents have dependencies and secrets.
- Modify: `dev-flow/scripts/test_show_state.py`. Add `test_feature_complete_proposes_app_security_on_every_stack`.
- Modify: `vercel-deploy/SKILL.md`. At `:3` and `:70-78`, "four gates" becomes five and the step reads `meta.json#security` too. In the routing tables at `:20-22` and in the maintenance loop at `:244`, list all five.
- Modify: `rn-eas-deploy/references/deploy-checklist.md`. One line: `app-security` ran, with dependencies and secrets checked and no `EXPO_PUBLIC_` secret.
- Modify: `dev-flow/references/policies.md`. Add a `**Security policy (app code).**` paragraph after the UI-quality policy. At `:31`, "four" becomes "five".
- Modify: `spec-review/SKILL.md:83`. The pre-deploy gates are now five.
- Modify: `shadscan/SKILL.md`. The description's "four pre-deploy gates" becomes five.
- Modify: `README.md:1249`, and any other "four pre-deploy gates" that `grep -rn "four pre-deploy\|four gates"` finds outside `dist/`, `docs/skills` and the CHANGELOG.

- [ ] **Step 1:** Write the failing `show_state` test: for each stack, `next_step("feature_complete", fw)` contains `app-security`. Run it. Expected: FAIL.
- [ ] **Step 2:** Make all the edits listed above.
- [ ] **Step 3:** Run `python3 scripts/sync_routing_table.py`, then the same with `--check`. Run `cd dev-flow/scripts && python3 -m unittest test_show_state`. Then `grep -rn "four pre-deploy\|four gates" --include='*.md' . | grep -v -E "dist/|docs/skills|CHANGELOG|AUDIT|docs/superpowers"`. Expected: tests OK and the grep empty.
- [ ] **Step 4:** Commit: `feat(dev-flow): app-security, the fifth pre-deploy gate, in routing and in vercel-deploy`.

### Task 5: Registration, CHANGELOG, bundles

**Files:**
- Modify: `install.sh`, `uninstall.sh` (`SKILLS`), and `scripts/build_skills_registry.py` (`TAXONOMY`: `"app-security": ("core", "operative")`, the same family and role as `compliance-audit`).
- Modify: `README.md` (catalogue section and family count, skill count 53→54), `docs/dev-flow-skill-map.html` (a row and the counts), and every count lint check 11 reports.
- Modify: `CHANGELOG.md` (one Added entry).
- Regenerate: `scripts/regenerate.sh` (skills.json, docs, plugin manifests), then the bundles.

- [ ] **Step 1:** Make the edits. Run `bash scripts/regenerate.sh`, then `python3 scripts/lint_skills.py` until it is clean.
- [ ] **Step 2:** Run `python3 scripts/build_skill_bundles.py` and its `--check`. Expected: `✓ dist/ matches the sources (54 bundles)`.
- [ ] **Step 3:** Run `python3 scripts/run_skill_tests.py` and `python3 scripts/test_install.py`. Expected: all pass, including `app-security`'s suite.
- [ ] **Step 4:** Commit: `chore: register app-security across installers, registry, README and counts`.

### Task 6: Whole-branch verification and a run on a real project

- [ ] **Step 1:** Run lint, every suite, `--check` on the bundles and on the routing table, and `comply.py selftest`. Run the app-security suite on 3.9 as well.
- [ ] **Step 2: Real project, read-only.** Run `python3 app-security/scripts/scan_security.py ~/projects/fit-coach` (and one more Next project from `~/projects`), with the tools as installed today.
  - Expected: no traceback, the tool checks `not checked` (the tools are absent), and Next.js findings listed.
  - Read three of the findings in the code and record which are true and which are false positives.
  - A check whose false positives dominate is narrowed, with a test, before the review.
- [ ] **Step 3:** Report: files changed, the real-project result (true and false positives), that no tool was installed, and that Strix was not run.

## Spec coverage

| Spec | Task |
|---|---|
| §1 Levels | 1, 2 (scan), 3 (review, dynamic) |
| §2 Scanner | 1, 2 |
| §3 Checklist | 3 |
| §4 Strix | 3 (`dynamic.md`, resources row) |
| §5 `meta.json#security` | 3 |
| §6 In the flow | 4 |
| §7 Missing tools | 2 (not checked), 3 (install command and asking) |
| Tests | 1, 2, 4, 6 |
