# Scrum Trackers Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `linear-scrum` becomes `scrum`, which runs the same scrum method on Linear, Jira or GitHub. It records the choice in `meta.json#tracker`, migrates every existing shape without losing data, and adds bug triage with severities.

**Architecture:** One skill, with tracker-neutral scripts:
- `task_key.py`;
- `meta_tracker.py`;
- `github_sync.py`, because GitHub runs through the `gh` CLI;
- `jira_estimate.py`, for the story points only REST can write;
- a reference per tracker for the MCP-driven parts.

dev-flow, `prd-from-idea` and every skill that names `linear-scrum` move to the neutral name and the `tracker` block.

**Tech Stack:** Python 3.9+ stdlib, `unittest`, `gh` (faked in tests via `PATH`), a local `http.server` faking Jira REST.

**Spec:** `docs/superpowers/specs/2026-10-18-scrum-trackers-design.md`

## Global Constraints

- Stdlib only, Python 3.9+. Never a token in chat:
  - Jira REST reads `JIRA_EMAIL` and `JIRA_API_TOKEN` from the environment;
  - GitHub uses `gh auth`;
  - Linear and Jira MCP use the user's OAuth.
- On GitHub, a sprint is **one milestone per sprint, named by its goal**, and priority is the label `priority: Pn` on every issue (the user's rule, 2026-10-14). No Projects v2.
- `meta.json#tracker = {provider, project{…}, url, issue_map{task_key: key}, last_synced_at}`. Writes go through `meta_io.locked`. `migrate` never drops a key; titles it cannot match go to `tracker.unmatched`.
- Severity labels are S1–S4, plus the `bug` label. Existing labels on an adopted repo are reused; only missing ones are created.
- Triage stops once the issue sits in the right sprint. `scrum` never touches app code. No user personal data goes into issues.
- The tracker is not a product sub-processor (no `data_residency.py add`).
- Code and skill text are in English.

## Review Focus

1. **A hand-written `tracker` block with a title-keyed map whose titles were since edited in `tasks.md`.** The unmatched entries are kept in `tracker.unmatched`, and Sync does not create duplicates for the matched ones. Test: Task 1 `test_migrate_keeps_unmatched_titles`.
2. **`gh` failing midway through `github_sync.py`.** The issues already created are recorded before the exit, so a re-run resumes without duplicating them. Test: Task 2 `test_a_failure_midway_keeps_what_was_created`.
3. **A repo that already has `priority: P1` or `area: x` labels.** No duplicate label is created, and the existing names are used. Test: Task 2 `test_existing_labels_are_reused`.
4. **Missing Jira credentials, or a 401 from Jira.** Exit 2 with what to set, and the token is never printed. Test: Task 3 `test_missing_credentials_exit_2_without_echo` and `test_401_names_the_cause`.
5. **A project with both a legacy `linear` block and a `tracker.provider` chosen at design time.** `migrate` merges them into one block and the Linear ids survive. Test: Task 1 `test_migrate_linear_into_a_chosen_provider`.

---

### Task 1: `scrum` skill — rename, `meta_tracker.py`

**Files:**
- Rename `linear-scrum/` → `scrum/` (`git mv`). Inside it, remove `scripts/meta_linear.py` and create `scripts/meta_tracker.py`.
- Modify `scrum/scripts/test_scripts.py`.
- Modify `scripts/lint_skills.py`: the vendored meta_io pair list, `linear-scrum` → `scrum`.
- Modify `dev-flow/scripts/test_meta_io.py:149-160`: the path, and the `ensure-scrum` op.

**Interfaces:**
- Produces pure functions, plus a CLI with the same names (`meta_tracker.py <meta.json> <op>`):
  - `choose(meta, provider: str) -> dict`, with provider in `{"linear", "jira", "github"}` and anything else raising `ValueError`;
  - `upsert(meta, provider, project: dict, url: str) -> dict`;
  - `record_issues(meta, mapping: dict) -> dict`;
  - `ensure_scrum(meta) -> dict`, which keeps the old defaults and adds `severity_labels{S1..S4: "severity: Sn"}` and `bug_label: "bug"`;
  - `migrate(meta, root: Path) -> tuple[dict, list[str]]`, returning the new meta and notes;
  - `legacy_shape(meta) -> str | None`, which says why the block is old, or None.

- [ ] **Step 1: Write the failing tests** (class `Tracker` in `test_scripts.py`; the existing task_key tests stay):

```python
def test_choose_records_the_provider_only(self)            # {} → {"tracker": {"provider": "jira"}}; choose(meta,"asana") raises ValueError
def test_upsert_keeps_the_issue_map(self)
def test_record_issues_no_duplicates(self)
def test_ensure_scrum_adds_severity_labels(self)            # scrum.severity_labels == {"S1":"severity: S1",…}; bug_label "bug"; existing labels untouched
def test_migrate_linear_block(self)                         # {"linear":{team_id,team_name,project_id,url,issue_map}} → tracker{provider:"linear", project{team_id,team_name,project_id}, url, issue_map}; "linear" key gone
def test_migrate_linear_into_a_chosen_provider(self)        # tracker{provider:"linear"} + linear{…} → one tracker with the ids
def test_migrate_archistudio_shape(self)                    # tracker{kind:"github", repo, map:".workflow/github-issues.json", bodies, scrum{sprint_weeks:2, capacity_hours:30, milestones:[…]}}
    # + tasks.md with "- [ ] **Login** — x" and the map file {"Login": 7} → provider "github", project.repo, issue_map {task_key("- [ ] **Login** — x"): "#7"},
    #   bodies kept, top-level scrum.cadence_weeks 2, scrum.capacity_hours 30, scrum.milestones kept, "kind" gone
def test_migrate_fit_room_shape(self)                       # tracker{kind:"github-issues", repo, linear:"opt-out…", issue_map{"Login": 7}} → issue_map by task_key, the "linear" note kept
def test_migrate_keeps_unmatched_titles(self)               # map {"Gone": 9} not in tasks.md → tracker.unmatched == {"Gone": "#9"}
def test_migrate_is_idempotent(self)                        # migrate(migrate(m)) == migrate(m)
def test_legacy_shape(self)                                 # "linear" block / kind / title-keyed map → a reason; the new shape → None
def test_cli_writes_under_the_lock(self)
```

- [ ] **Step 2: Run them, expect failure:** `cd scrum/scripts && python3 -m unittest test_scripts` → ERROR, no module `meta_tracker`.
- [ ] **Step 3: Implement `meta_tracker.py`.**
  - A title-keyed map is one whose keys are not 12-hex strings.
  - Keys are matched to `tasks.md` by recomputing `task_key` for each `- [ ]` / `- [x]` line whose bold title equals the map key.
  - GitHub numbers become `"#N"`.
- [ ] **Step 4: Run, expect pass.** Also run `python3 -m unittest discover -s dev-flow/scripts -p test_meta_io.py`.
- [ ] **Step 5: Commit** `feat(scrum): linear-scrum becomes scrum — meta_tracker.py and the migration of every tracker shape`

### Task 2: GitHub — `github_sync.py`

**Files:**
- Create `scrum/scripts/github_sync.py` and `scrum/scripts/test_github_sync.py`.
- Modify `project-infra-setup/scripts/make_issues.py`: a shim that prints the new command and calls `github_sync.main` with the mapped arguments.
- Modify `project-infra-setup/scripts/test_project_infra_setup.py`: the parse, type and area tests move with the code, and the shim test stays.

**Interfaces:**
- Consumes `meta_tracker.record_issues` and `task_key.task_key`.
- Produces:
  - `parse(text) -> list[dict]`, moved from make_issues;
  - `plan(tasks, issue_map, existing_labels: set[str]) -> dict` → `{"create": [...], "labels": {name: color}}`;
  - `main(argv) -> int`, with CLI `github_sync.py <root> --repo O/N [--milestone "Sprint 1 — <goal>"] [--dry-run] [--pause S]`.
- Behaviour:
  - Labels: `area:` / `tipo:` from the old rules, `estimate: N` from the task's `Estimated:` hint mapped to Fibonacci, and `priority: Pn` from the task's `Priority:` hint, defaulting to P2.
  - Existing labels come from `gh label list --json name --limit 500`.
  - After each issue is created, the map entry is written into meta (`record_issues`).
  - Bodies follow `references/issue-standard.md`'s skeleton, and the agent rewrites them to the standard afterwards (as today).

- [ ] **Step 1: Write the failing tests** with a fake `gh` script on `PATH` that logs argv to a file and answers from fixtures:

```python
def test_dry_run_calls_nothing_that_writes(self)
def test_creates_missing_issues_and_records_them_by_task_key(self)   # meta.tracker.issue_map has task_key → "#12"
def test_a_rerun_creates_nothing(self)
def test_existing_labels_are_reused(self)                            # fake label list has "priority: P1","area: auth" → no `label create` for them
def test_estimate_and_priority_labels(self)                          # "Estimated: 4h"→"estimate: 3" (mapping as scrum-model.md), "Priority: P1"→"priority: P1"
def test_milestone_is_passed_when_given(self)
def test_a_failure_midway_keeps_what_was_created(self)               # fake gh fails on the 2nd create → exit 1, first recorded in meta
def test_make_issues_shim_still_works(self)
```

- [ ] **Step 2: Run, expect failure.**
- [ ] **Step 3: Implement**, moving `parse`, `area_label`, `type_of` and `body_of` from make_issues.
- [ ] **Step 4: Run, expect pass.** Also run the project-infra-setup suite.
- [ ] **Step 5: Commit** `feat(scrum): github_sync.py — issues by task_key, the user's milestone and priority rule, existing labels reused`

### Task 3: Jira — `jira_estimate.py`

**Files:**
- Create `scrum/scripts/jira_estimate.py` and `scrum/scripts/test_jira_estimate.py`.

**Interfaces:**
- Produces `estimate(site: str, board_id: str, key: str, points: float, email: str, token: str, opener=urllib.request.urlopen) -> int` (the HTTP status), and `main(argv) -> int`, with CLI `jira_estimate.py <root> --key ABC-1 --points 3`.
  - Site and board come from `meta.tracker.project.site` / `.board_id`.
  - Credentials come from the env vars `JIRA_EMAIL` / `JIRA_API_TOKEN`.
  - It sends `PUT https://<site>/rest/agile/1.0/issue/<key>/estimation?boardId=<id>` with body `{"value": "<points>"}`, Basic auth.

- [ ] **Step 1: Write the failing tests** against a local `http.server` thread. The site is passed as `http://127.0.0.1:<port>` through an injectable base URL in `estimate`.

```python
def test_sends_the_estimation_put_with_basic_auth(self)    # path, query boardId, JSON body, Authorization header decodes to email:token
def test_missing_credentials_exit_2_without_echo(self)     # no env → exit 2, stderr names JIRA_EMAIL/JIRA_API_TOKEN, token value never printed
def test_401_names_the_cause(self)                         # server answers 401 → exit 1, message says the token or email is wrong; token not in output
def test_missing_board_in_meta_is_explained(self)
```

- [ ] **Step 2: Run, expect failure.**
- [ ] **Step 3: Implement.**
- [ ] **Step 4: Run, expect pass.**
- [ ] **Step 5: Commit** `feat(scrum): jira_estimate.py — story points through Jira's estimation endpoint, token from the environment`

### Task 4: The skill text — modes, adapters, triage, issue standard

**Files:**
- Modify `scrum/SKILL.md`: name, description, modes Choose / Setup / Adopt / Sync / Triage, the provider switch, and Definition of Done.
- Rename `scrum/references/linear-mcp.md` → `scrum/references/linear.md`.
- Create:
  - `scrum/references/jira.md`: the Rovo MCP tools listed in the spec, the order of operations, `jira_estimate.py`, and what to verify on the first real use;
  - `scrum/references/github.md`: `gh`, milestones, labels, `github_sync.py`, velocity from closed milestones;
  - `scrum/references/triage.md`: the severity table, the four steps, and the no-personal-data rule;
  - `scrum/references/issue-standard.md`: moved from `project-infra-setup/references/provisioning.md` §"Issues written to the standard", which becomes a pointer.
- Modify `scrum/references/scrum-model.md` (neutral wording, severity) and `project-infra-setup/SKILL.md` + `references/provisioning.md` (the repo stays theirs; issues and sprints point to `scrum`).

- [ ] **Step 1:** Write the files above.
- [ ] **Step 2:** Run `python3 scripts/lint_skills.py` → `✓ Clean`. The description must stay under 1024 characters.
- [ ] **Step 3: Commit** `docs(scrum): one method, three adapters, a triage mode, and the issue standard for every tracker`

### Task 5: dev-flow, the contract, `prd-from-idea`, `show_state`

**Files:**
- Modify `dev-flow/references/contracts.md`: replace the `linear` / `scrum` section with `tracker` / `scrum` (spec §2, migration note), then propagate it to every copy.
- Modify `dev-flow/scripts/show_state.py`:
  - the four `tasks_split` routing strings → `scrum (Setup)`;
  - new `tracker_line(meta) -> str | None`, which notes a legacy shape via the same rule as `meta_tracker.legacy_shape`, re-implemented inline, three checks;
  - after `prd_drafted`, when no `tracker.provider` is set, it notes "Tracker: not chosen".
- Modify `dev-flow/scripts/test_show_state.py`: add class `Tracker`.
- Modify:
  - `dev-flow/SKILL.md`: the policy line and the Step 2 text, then run `sync_routing_table.py`;
  - `dev-flow/references/policies.md:17`;
  - `merge-conflicts.md`;
  - `eu-data-sovereignty.md`: Jira and GitHub rows.
- Modify `prd-from-idea/SKILL.md`: one interview question, "Where do we manage the work?", with defaults (the tracker the project or client already uses, otherwise Linear), recorded with `meta_tracker.py choose`.
- Modify `prd-from-idea/references/scope-check.md:5,53`.

**Interfaces:**
- Consumes the `tracker` shape from Task 1.
- Produces `tracker_line(meta: dict) -> str | None`.

- [ ] **Step 1: Write the failing tests** (class `Tracker` in `test_show_state.py`):

```python
def test_legacy_linear_block_is_noted(self)
def test_hand_written_github_block_is_noted(self)      # kind / title-keyed map
def test_not_chosen_after_prd(self)                     # phase tasks_split, no tracker → "Tracker: not chosen"
def test_chosen_and_current_is_silent(self)
def test_tasks_split_routes_to_scrum(self)              # every topology's tasks_split row contains "scrum (Setup)" and not "linear-scrum"
```

- [ ] **Step 2: Run, expect failure.**
- [ ] **Step 3: Implement.** Then propagate the contract:

```bash
for f in */references/contracts.md; do [ "$f" != dev-flow/references/contracts.md ] && cp dev-flow/references/contracts.md "$f"; done
python3 scripts/sync_routing_table.py
```

- [ ] **Step 4: Run** `python3 -m unittest discover -s dev-flow/scripts -p 'test_*.py'` → OK.
- [ ] **Step 5: Commit** `feat(dev-flow): the tracker is chosen at design time; scrum on the chosen one; legacy shapes noted`

### Task 6: Everything else that names linear-scrum

**Files:**
- Text only, neutral name and wording:
  - `prd-to-tasks/SKILL.md`;
  - `spec-review/SKILL.md:65`;
  - `compliance-audit/references/gdpr-ai-act-checklist.md:79`: the tracker as the team's tool, not a product sub-processor;
  - `eve-agent` (wording only where it means the PM tool);
  - `README.md`, `AUDIT.md` (leave it as a dated audit), `docs/loop-engineering.md` (a note that it is Linear-only);
  - `scripts/build_skills_registry.py:59`, `scripts/build_plugin_manifest.py:40`;
  - `.obsidian/graph.json`, if it is tracked.
- Code changes:
  - `install.sh`: a `RETIRED=(linear-scrum)` list whose installed copies are removed after the existing backup, with the output line "removed retired skill linear-scrum (now scrum)";
  - `uninstall.sh`: both names;
  - `scripts/test_install.py`: a new test;
  - `wireframe-canvas/scripts/wireframes.py`: `comments` reads `meta.tracker.issue_map` when `--map` is absent, and keys bodies by issue key (task_key from the task line). The raw-URL images stay GitHub-only, and for other providers the body names the PNG paths for the agent to attach;
  - `wireframe-canvas/scripts/test_wireframes.py`: a test;
  - `wireframe-canvas/SKILL.md`.
- `CHANGELOG.md`.

- [ ] **Step 1: Write the failing tests:**
  - `test_install.py`: `test_a_retired_skill_is_removed_after_backup`, where a fake installed `linear-scrum` is gone, the backup contains it, and the output names it.
  - `test_wireframes.py`: `test_comments_use_the_tracker_issue_map`, where the meta has `tracker.issue_map` keyed by task_key and the bodies are keyed by `"#7"` / `"LUC-3"`.
- [ ] **Step 2: Run, expect failure.**
- [ ] **Step 3: Implement**, and edit the text files.
- [ ] **Step 4:** `git grep -n "linear-scrum" -- ':!docs' ':!dist' ':!CHANGELOG.md' ':!AUDIT.md'` must print nothing outside history notes. Then run `python3 scripts/lint_skills.py` and `python3 scripts/run_skill_tests.py`.
- [ ] **Step 5: Commit** `refactor: every skill names scrum and reads meta.json#tracker; install retires linear-scrum`

### Task 7: The real run

- [ ] **Step 1:** Copy the `.workflow/` directories of archistudio, fit-room, bidflow, smart-travel and hostitaly into the scratchpad. Never write to the projects themselves.
- [ ] **Step 2:** Run `meta_tracker.py <copy>/meta.json migrate` on each, and compare before/after:
  - every old key is still present somewhere;
  - the issue_map size plus unmatched equals the old map size;
  - a second migrate changes nothing.
- [ ] **Step 3:** Run `github_sync.py <archistudio copy root> --repo <its repo> --dry-run` with the real `gh`. It is read-only, because `--dry-run` only lists labels. Expected: 0 issues to create, and no duplicate labels proposed.
- [ ] **Step 4:** For each defect found, write a red test, then the fix, then commit with a ledger ruling.

### Task 8: Whole-branch verification, review, PR

- [ ] Run:
  - `python3 scripts/lint_skills.py`;
  - `python3 scripts/run_skill_tests.py`;
  - `python3 evals/compliance/comply.py selftest`;
  - the three `--check` builders;
  - the new suites on 3.9: `cd scrum/scripts && uv run -q --python 3.9 python -m unittest discover -p 'test_*.py'`.
- [ ] Then:
  - the final review on the most capable model, including this plan's Review Focus;
  - one fix pass, minors included;
  - push, PR, merge at green CI;
  - update the memory `project_linear_scrum_skill.md` to the new name and policy.
