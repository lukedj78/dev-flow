# Debt Audit Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A dev-flow mode that composes the existing audits and a new test check into one ordered debt list (before-release / with-features / later), with what it could not see listed apart.

**Architecture:** One stdlib script, `dev-flow/scripts/debt_audit.py`, split into four modules by responsibility:
- `debt_model.py`: the finding, the band rules, decisions and order;
- `debt_sources.py`: scanners and recorded results;
- `debt_tests.py`: the test check;
- `debt_audit.py`: the CLI, the report and meta.

The sibling skills' scanners are called by path, in subprocesses. `show_state.py` proposes the mode from `deployed`.

**Tech Stack:** Python 3.9+ stdlib, `unittest`, the repo's existing `meta_io.py`, `surfaces.py`, `phases.py`.

**Spec:** `docs/superpowers/specs/2026-10-18-debt-audit-design.md`

## Global Constraints

- Stdlib only, Python 3.9+ (`from __future__ import annotations`; CI runs 3.9).
- Never edits the project's code; writes only `docs/debt/`, `.workflow/debt/`, `meta.json` (via `meta_io.locked`).
- Works without sibling skills installed: an absent, failing or timed-out source is `not checked` with the reason, never ok.
- Timeouts: app-security 1800 s, every other scanner 120 s.
- Bands: `before-release`, `with-features`, `later`; `not checked` is listed apart and never ordered.
- No coverage threshold, no overall score.
- Code, skill text and the generated report in English.
- A fresh app-security or compliance finding is a signal (`to_confirm`) until `.workflow/debt/reviewed.json` confirms it.
- Gate acceptances apply per check; `reviewed.json` applies per finding id; `compliance.flagged` stays open.

## Review Focus

1. **A project with no git history (or not a git repo).** Churn ordering falls back to source order without crashing. Test: Task 1 `test_order_without_churn_keeps_source_order`.
2. **A scanner that prints garbage or non-JSON.** That source is `not checked` with the reason, and the other sources still report. Test: Task 2 `test_garbage_output_is_not_checked`.
3. **A `false_positive` verdict whose file changed since.** The finding comes back as a signal. Test: Task 1 `test_false_positive_returns_when_the_file_changes`.
4. **A monorepo with two web surfaces.** The test check walks each surface and tags paths per surface. Test: Task 3 `test_each_web_surface_is_checked`.
5. **A corrupt `reviewed.json` or `manual.json`.** It is reported as `not checked` (manual) or ignored with a note (reviewed), never a crash. Test: Task 2 `test_corrupt_manual_is_not_checked` and Task 1 `test_corrupt_reviewed_is_ignored_with_a_note`.

---

### Task 1: The model — finding, bands, decisions, order

**Files:**
- Create: `dev-flow/scripts/debt_model.py`
- Test: `dev-flow/scripts/test_debt_audit.py`

**Interfaces:**
- Produces:
  - `@dataclass Finding(source: str, check: str, detail: str, file: str | None = None, line: int | None = None, severity: str = "", routed_to: str = "", signal: bool = False, stale: bool = False, band: str = "", kept: str = "")`, with property `id -> str` = `f"{source}:{check}:{file or '-'}"`.
  - `BAND_RULES: list[tuple[str, str, str, str]]`: (source, check-or-`*`, severity-or-`*`, band). The first match wins.
  - `band_for(f: Finding) -> str`.
  - `apply_decisions(findings: list[Finding], meta: dict, reviewed: dict, root: Path) -> tuple[list[Finding], list[Finding], list[str]]`, returning (open, kept, notes).
  - `order(findings: list[Finding], churn: dict[str, int]) -> list[Finding]`.
  - `churn(root: Path, days: int = 90) -> dict[str, int]`.
  - `diff_runs(previous_ids: set[str], current_ids: set[str]) -> tuple[set[str], set[str]]`, returning (new, closed).
  - `file_hash(root: Path, rel: str | None) -> str`.

Severity values used by sources (Task 2):
- app-security: `found`;
- compliance: `H` / `M`;
- registry-intake: `block` / `review`;
- observability: `errors` / `logs` / `uptime` as the check;
- recipes: `HIGH` / `MEDIUM` / `LOW`;
- shadscan: `fix` / `verify` / `decide`;
- vercel-doctor: `high` / `medium` / `low`;
- launch-audit: `missing`;
- promote-component: `promote`;
- tests: check `untested-mutation`, severity `authz` when an app-security authz finding shares the file.

- [ ] **Step 1: Write the failing tests** (class `Model`)

```python
def test_band_table_rows(self):
    cases = [(F("app-security","authz",severity="found"),"before-release"),
             (F("compliance","R3",severity="H"),"before-release"), (F("compliance","R5",severity="M"),"with-features"),
             (F("registry-intake","K8",severity="block"),"before-release"),
             (F("observability","errors"),"before-release"), (F("observability","uptime"),"later"),
             (F("tests","untested-mutation",severity="authz"),"before-release"),
             (F("tests","untested-mutation"),"with-features"),
             (F("forms","C",severity="HIGH"),"with-features"), (F("forms","J",severity="LOW"),"later"),
             (F("shadscan","r1",severity="fix"),"with-features"), (F("shadscan","r2",severity="decide"),"later"),
             (F("vercel-doctor","high",severity="high"),"with-features"), (F("vercel-doctor","low",severity="low"),"later"),
             (F("launch-audit","og",severity="missing"),"with-features"), (F("promote-component","Card",severity="promote"),"later")]
    for f, band in cases: self.assertEqual(dm.band_for(f), band, f)
def test_gate_acceptance_applies_per_check(self):   # security.findings.accepted [{check, reason}]
    # two authz findings on different files, meta accepts check "authz" → both kept, kept == the reason
def test_reviewed_verdicts_apply_per_id(self):       # confirmed → signal False; accepted → kept; false_positive → kept
def test_false_positive_returns_when_the_file_changes(self):  # verdict stored with hash; file edited → open, signal True
def test_compliance_flagged_stays_open(self):        # meta.compliance.flagged ["R3"] → open, detail mentions "legal decision"
def test_corrupt_reviewed_is_ignored_with_a_note(self):  # reviewed = None (caller failed to parse) → notes has one line
def test_order_by_churn_then_source(self):           # churn {"b.ts": 9, "a.ts": 1} → b before a; ties keep input order
def test_order_without_churn_keeps_source_order(self):   # churn({}) on a non-git tmp dir == {} and order is unchanged
def test_diff_runs(self):  # ({"a","b"}, {"b","c"}) → ({"c"}, {"a"})
```

`F` is a test helper building `dm.Finding(source, check, "d", **kw)`.

- [ ] **Step 2: Run them, expect failure**

Run: `cd dev-flow/scripts && python3 -m unittest test_debt_audit.Model`
Expected: ERROR `No module named 'debt_model'`

- [ ] **Step 3: Implement `debt_model.py`** with the interfaces above.
  - `churn` runs `git -C root log --since=<days>.days --name-only --pretty=format:` and returns `{}` on any error.
  - `apply_decisions` reads these meta keys: `security.findings.accepted`, `launch_audit.dismissed` (dict check→reason), `shadscan.false_positives` and `shadscan.rules_left_red` (dict rule→reason), and `compliance.flagged`.
  - Verdicts in `reviewed` are `{id: {verdict, reason, at, hash}}`.

- [ ] **Step 4: Run them, expect pass**

Run: `cd dev-flow/scripts && python3 -m unittest test_debt_audit.Model`
Expected: OK

- [ ] **Step 5: Commit** `feat(dev-flow): debt model — one finding shape, fixed bands, decisions and churn order`

### Task 2: The sources — scanners and recorded results

**Files:**
- Create: `dev-flow/scripts/debt_sources.py`
- Test: `dev-flow/scripts/test_debt_audit.py` (class `Sources`)

**Interfaces:**
- Consumes: `Finding` (Task 1).
- Produces:
  - `@dataclass Source(name: str, status: str, reason: str = "")`, with status `fresh | stale | missing | not checked`.
  - `SKILLS_ROOT: Path`, which is `Path(__file__).resolve().parents[2]`. Tests override it with a tmp dir of fake scanners.
  - `SCANNERS: dict[str, tuple[str, list[str], int, Callable[[str], list[Finding]]]]`: name → (relative script path, args after root, timeout, parser).
  - `run_scanners(root: Path, meta: dict, skip: set[str], web: bool) -> tuple[list[Finding], list[Source]]`.
  - `recorded(root: Path, meta: dict, last_change: str | None) -> tuple[list[Finding], list[Source]]` (shadscan, vercel-doctor).
  - `manual(root: Path) -> tuple[list[Finding], Source]` (reads `.workflow/debt/manual.json`).
  - `last_material_change(meta: dict) -> tuple[str | None, str | None]`, returning (ran_at, skill). It uses `show_state.MATERIAL_SKILLS`, imported, not copied.

| name | script | args | parser keeps |
|---|---|---|---|
| app-security | `app-security/scripts/scan_security.py` | `--json` | `status == "found"` → one Finding per `where[]` entry (or one with file None), `signal=True`, severity `found`, check = `check` |
| launch-audit | `launch-audit/scripts/scan_launch.py` | `--json` | `status == "missing"`, web only |
| observability | `module-add/scripts/observability_check.py` | `--json` (+ `--all` when `stack.observability` is empty) | `found`, check = level; `not checked` rows become notes on the Source |
| compliance | `compliance-audit/scripts/scan.py` | — | `findings[]`: check = `id`, severity, `signal=True`, file None |
| registry-intake | `registry-intake/scripts/registry_intake.py` | `check` | exit 1 → one Finding per non-empty line, severity `block`; exit 0 → none; skipped (Source not checked, reason "no registry-lock.json") when the project has no `registry-lock.json` |
| promote-component | `promote-component/scripts/scan_promotion.py` | — | markdown table rows whose Suggestion starts with `Promote`, severity `promote`, check = component |

`recorded`:
- shadscan reads `docs/ui/shadscan.json` → `agentHandoff.actionables[]`, with check = rule id, severity = `disposition`, file and line from `file:line`. Missing file → Source `missing`. `meta.shadscan.last_run_at` older than `last_change` → `stale` and every finding has `stale=True`.
- vercel-doctor reads `meta.vercel_doctor.findings{high,medium,low}`: one Finding per non-zero count, check = severity, detail `"<n> <severity> findings — docs/vercel/doctor-report.md"`. Staleness is computed the same way.

- [ ] **Step 1: Write the failing tests** with fake scanners written into a tmp `SKILLS_ROOT`.

```python
def test_app_security_found_rows_become_signals(self):    # fake prints [{"check":"authz","status":"found","detail":"x","where":["app/a.ts:3"]}]
    # → one Finding file "app/a.ts", line 3, signal True; Source status "fresh"
def test_missing_skill_is_not_checked(self):               # no script at the path → Source("app-security","not checked","not installed")
def test_garbage_output_is_not_checked(self):              # fake prints "boom" → not checked, reason mentions "output"
def test_timeout_is_not_checked(self):                     # SCANNERS timeout patched to 1, fake sleeps 3 → not checked "timed out"
def test_skip_is_not_checked(self):                        # skip={"app-security"} → not checked "skipped"
def test_observability_runs_all_levels_when_none_chosen(self):  # fake echoes argv; assert "--all" passed when stack.observability empty
def test_registry_intake_without_lock_is_skipped(self)
def test_promote_rows_parsed(self):                        # a two-row table, one "Promote to L2", one "OK — stays" → one Finding
def test_shadscan_stale_and_missing(self)
def test_vercel_counts_become_rows(self)                   # {"high":0,"medium":2,"low":1} → 2 findings
def test_corrupt_manual_is_not_checked(self)               # manual.json = "{" → Source not checked
def test_last_material_change(self)                        # history: module-add 2026-10-01, spec-review 2026-10-05 → ("2026-10-01…","module-add")
```

- [ ] **Step 2: Run, expect failure** — `python3 -m unittest test_debt_audit.Sources` → ERROR no module `debt_sources`.

- [ ] **Step 3: Implement `debt_sources.py`.**
  - Subprocesses: `subprocess.run([sys.executable, script, str(root), *args], capture_output=True, text=True, timeout=t)`.
  - Any `OSError`, `TimeoutExpired`, `ValueError` or `KeyError` becomes `not checked` with the reason.

- [ ] **Step 4: Run, expect pass**, then also run `python3 -m unittest test_debt_audit` (Model still green).

- [ ] **Step 5: Commit** `feat(dev-flow): debt sources — the sibling scanners by path, shadscan and vercel-doctor as recorded`

### Task 3: The test check — untested mutations and coverage

**Files:**
- Create: `dev-flow/scripts/debt_tests.py`
- Test: `dev-flow/scripts/test_debt_audit.py` (class `TestCheck`)

**Interfaces:**
- Consumes: `Finding`, `Source`; `surfaces.surfaces(root, meta)`.
- Produces:
  - `mutations(base: Path) -> list[str]`: relative paths of `"use server"` files and `app/**/route.ts|js` exporting `POST|PUT|PATCH|DELETE`, plus files containing a Drizzle `.insert(` / `.update(` / `.delete(`.
  - `tested_by(base: Path, rel: str) -> str | None`: `"unit"`, `"e2e"` or None.
  - `page_url(rel_page: str) -> str`: `app/[locale]/(marketing)/plans/[id]/page.tsx` → `/plans/[id]`; drop `(group)` segments and leading dynamic segments; `[x]` in the middle stays and matches any segment in an e2e string.
  - `coverage(base: Path) -> tuple[dict | None, str]`: reads `coverage/coverage-summary.json` and returns `({"total": pct, "files": {rel: pct}}, "")`, or `(None, reason)`, where the reason contains the exact command for the stack (Vitest: `pnpm add -D @vitest/coverage-v8` then `pnpm vitest run --coverage --coverage.reporter=json-summary`; Jest: `npx jest --coverage --coverageReporters=json-summary`).
  - `check(root: Path, meta: dict, authz_files: set[str]) -> tuple[list[Finding], list[Source]]`, with one Finding `tests:untested-mutation` per untested file (severity `authz` when the file is in `authz_files`) and Sources `tests` and `coverage`.
- "Unit" means a `*.test.*` or `*.spec.*` file outside `e2e/` that imports the file (relative, or by the `@/` alias) or names its path without extension. "e2e" means a spec under `e2e/` or `tests/e2e/` whose text contains `page_url(...)` of a page importing the file.

- [ ] **Step 1: Write the failing tests**

```python
def test_server_action_without_test_is_found(self)
def test_unit_import_counts(self)                  # tests/plan.test.ts imports "@/app/actions/plan" → tested "unit"
def test_e2e_visit_counts(self)                    # app/[locale]/(app)/plans/page.tsx imports the action; e2e/plans.spec.ts has goto("/plans") → "e2e"
def test_page_url(self)                            # the example above, and app/page.tsx → "/"
def test_read_only_route_is_not_a_mutation(self)   # route.ts exporting only GET → not listed
def test_authz_on_the_same_file_raises_severity(self)
def test_coverage_summary_is_read(self)            # {"total":{"lines":{"pct":61.5}}, "/abs/app/a.ts":{"lines":{"pct":0}}} → total 61.5, files {"app/a.ts": 0}
def test_no_coverage_names_the_command(self)       # stack.test "vitest+playwright" → reason contains "@vitest/coverage-v8"
def test_each_web_surface_is_checked(self)         # monorepo apps/web + apps/admin, an untested action in each → two findings, paths prefixed by the surface
def test_mobile_is_not_applicable(self)            # expo project → Source tests "not applicable"
```

- [ ] **Step 2: Run, expect failure** (no module `debt_tests`).
- [ ] **Step 3: Implement `debt_tests.py`.** Prune `node_modules`, `.next`, `.git`, `dist`, `build` and `coverage` with `os.walk`.
- [ ] **Step 4: Run, expect pass.**
- [ ] **Step 5: Commit** `feat(dev-flow): debt test check — mutations without a test, e2e visits count, coverage when it exists`

### Task 4: `debt_audit.py` — collect, show, the report, the record

**Files:**
- Create: `dev-flow/scripts/debt_audit.py`
- Test: `dev-flow/scripts/test_debt_audit.py` (class `Collect`)

**Interfaces:**
- Consumes: Tasks 1–3; `meta_io.locked`, `meta_io.read_meta`, `meta_io.write_json`.
- Produces:
  - `collect(root: Path, skip: set[str] = frozenset(), now: str | None = None) -> dict`, which returns the `meta.json#debt_audit` block it wrote;
  - CLI: `debt_audit.py collect <root> [--skip NAME ...] [--json]` and `debt_audit.py show <root>`;
  - files: `.workflow/debt/findings.json` = `{"run_at", "open": [...], "kept": [...], "not_checked": [...], "sources": {...}}`, and `docs/debt/debt-audit.md`.
- The meta block holds exactly the spec §5 keys: `last_run_at`, `bands{before_release, with_features, later}`, `to_confirm`, `not_checked[]`, `sources{}`, `new`, `closed`, `report`.
- History entry `{skill: "dev-flow", action: "debt-audit", ran_at}`. It never touches `phase`.
- Report sections in order:
  1. `# Debt audit — <date>`;
  2. `## Before the next release`;
  3. `## With the features that touch these files`;
  4. `## Later`;
  5. `## Not checked`;
  6. `## Kept on purpose`;
  7. `## Since the last audit` (new / closed).

  Each row is `- [to confirm] file:line — detail (source/check → routed_to)`, where `[to confirm]` appears only for signals and `[stale]` for stale sources.

- [ ] **Step 1: Write the failing tests**, with `debt_sources.SKILLS_ROOT` patched to fake scanners.

```python
def test_collect_writes_the_three_outputs(self)    # meta.debt_audit keys == spec §5 keys; findings.json; report has the seven headings
def test_meta_is_written_under_the_lock(self)      # patch meta_io.locked to record entry → called once with root/".workflow"
def test_phase_and_other_keys_untouched(self)      # meta before/after differ only in debt_audit + history
def test_second_run_reports_new_and_closed(self)
def test_before_release_counts_only_confirmed(self)  # one signal + one confirmed → bands.before_release == 1, to_confirm == 1
def test_show_without_a_run_says_so(self)          # exit 1, "no debt audit yet"
def test_cli_json(self)
```

- [ ] **Step 2: Run, expect failure.**
- [ ] **Step 3: Implement `debt_audit.py`.**
  - Read `reviewed.json`. On a parse error pass `None`, which Task 1 turns into a note.
  - Compute `authz_files` from app-security findings with check `authz` (or any check whose name contains `auth`).
  - Load the previous `findings.json` ids for `diff_runs`.
- [ ] **Step 4: Run, expect pass**, then run the whole `python3 -m unittest test_debt_audit`.
- [ ] **Step 5: Commit** `feat(dev-flow): debt_audit.py — collect and show, the report and meta.json#debt_audit`

### Task 5: dev-flow wiring, contract, citations, gate counts

**Files:**
- Modify:
  - `dev-flow/scripts/show_state.py`: add `debt_line(meta, root)`, print it in `main()` next to `observability_line`, and change the four `deployed` rows of `PHASE_NEXT_BY_STACK` so they start with `dev-flow debt audit (docs/debt/debt-audit.md), then`;
  - `dev-flow/scripts/test_show_state.py`: add class `Debt`;
  - `dev-flow/SKILL.md`: a "Debt audit" mode section (when, the two commands, the review loop with `reviewed.json` and `manual.json`, proposing before-release as tasks). Then run `python3 scripts/sync_routing_table.py`;
  - `dev-flow/references/contracts.md`: the `debt_audit` block with the spec §5 example, then propagate to every `*/references/contracts.md`;
  - `prd-to-tasks/SKILL.md`: revise mode also accepts a `debt:<id>` citation;
  - gate counts → "five pre-deploy gates" in `compliance-audit/SKILL.md`, `launch-audit/SKILL.md` (description and body), `vercel-doctor/SKILL.md`, `shadscan/SKILL.md` (description), `README.md`, `AUDIT.md`;
  - `README.md` (a dev-flow line for the mode) and `CHANGELOG.md`.
- Create: `dev-flow/references/debt-audit.md`, the user-facing band table (it repeats `BAND_RULES`), the `reviewed.json` and `manual.json` formats, and the coverage commands.

**Interfaces:**
- Consumes: `meta.debt_audit` (Task 4), `last_material_change` (Task 2).
- Produces: `debt_line(meta: dict, root: Path) -> str | None`.

- [ ] **Step 1: Write the failing tests** (class `Debt` in `test_show_state.py`)

```python
def test_silent_before_deployed(self)                  # phase feature_complete → None
def test_never_audited(self)                           # deployed, no debt_audit → contains "never audited" and "dev-flow debt audit"
def test_stale_after_a_material_change(self)           # debt_audit.last_run_at 2026-10-01, history module-add 2026-10-05 → contains "older than module-add"
def test_before_release_count(self)                    # fresh, bands.before_release 2, to_confirm 1 → contains "2 to fix" and "1 to confirm"
def test_clean_and_fresh_is_silent(self)               # all zero → None
def test_deployed_rows_start_with_the_debt_audit(self) # every topology's "deployed" row startswith "dev-flow debt audit"
```

- [ ] **Step 2: Run, expect failure** — `python3 -m unittest discover -s dev-flow/scripts -p test_show_state.py`.
- [ ] **Step 3: Implement `debt_line`, the routing rows, and the docs above.** Then propagate the contracts:

```bash
for f in */references/contracts.md; do [ "$f" != dev-flow/references/contracts.md ] && cp dev-flow/references/contracts.md "$f"; done
python3 scripts/sync_routing_table.py
```

- [ ] **Step 4: Run** `python3 -m unittest discover -s dev-flow/scripts -p 'test_*.py'`, then `python3 scripts/lint_skills.py`. Expected: OK and `✓ Clean`.
- [ ] **Step 5: Commit** `feat(dev-flow): propose the debt audit after deploy; debt:<id> is a task citation; five gates everywhere`

### Task 6: The real run on a copy of fit-coach

**Files:** no repo file unless a defect is found (each fix starts with a red test in its module's class).

- [ ] **Step 1:** Copy `~/projects/fit-coach` to the scratchpad, excluding `node_modules`, `.git`, `.next` and `.claude`, then `git init` with a single commit so churn has history. Run `pnpm install`.
- [ ] **Step 2:** Run `python3 dev-flow/scripts/debt_audit.py collect <copy> --skip app-security`. Expected:
  - three band headings;
  - `tests` fresh, with every untested mutation listed or none;
  - `coverage` not checked with the Vitest command;
  - app-security under not checked, reason "skipped".
- [ ] **Step 3:** Run `collect <copy>` without `--skip` (network allowed). Expected: app-security `fresh`, and its findings marked `[to confirm]`.
- [ ] **Step 4:** In the copy only, run `pnpm add -D @vitest/coverage-v8` and `pnpm vitest run --coverage --coverage.reporter=json-summary`, then `collect` again. Expected: `coverage` fresh, total percentage shown.
- [ ] **Step 5:** Commit any fixes with a ledger ruling each: `fix(dev-flow): debt audit proven on a real app — <defects>`.

### Task 7: Whole-branch verification, review, PR

- [ ] Run:
  - `python3 scripts/lint_skills.py`;
  - `python3 scripts/run_skill_tests.py`;
  - `python3 evals/compliance/comply.py selftest`;
  - `python3 scripts/build_agent_plugin.py --check`, `python3 scripts/sync_routing_table.py --check`, `python3 scripts/build_skill_bundles.py --check`;
  - `cd dev-flow/scripts && uv run -q --python 3.9 python -m unittest test_debt_audit test_show_state`.
- [ ] Then:
  - the final review on the most capable model, including this plan's Review Focus;
  - one fix pass, minors included (the user's rule);
  - push, PR, and merge at green CI.
