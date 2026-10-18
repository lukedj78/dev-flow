# founder-intelligence Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** An optional dev-flow skill, `founder-intelligence`, that turns a rough commercial idea into an evidence-based, founder-approved Playbook and hands it to `prd-from-idea`. It is an alternative to the inventory ("before you build"), and it can also be invoked later on an existing project.

**Architecture:** A new skill folder made of a lean `SKILL.md`, references loaded per stage, a Playbook template, and one script (`founder.py`), which is the only writer of `meta.json#founder`. One new phase gate, `dev-flow/scripts/founder_gate.py`, hooks into `update_meta.gate_refusal()`. It applies only when `meta.json#founder` exists, so a project on the direct path is untouched. Routing changes stay in `show_state.py`. `prd-from-idea` reads the approved Playbook.

**Tech Stack:** Markdown skills; Python ≥ 3.9 stdlib scripts with `unittest`; the existing lint (`scripts/lint_skills.py`), the test runner (`scripts/run_skill_tests.py`), the bundle builder and the compliance evals (`evals/compliance/comply.py`).

**Spec:** `docs/superpowers/specs/2026-10-17-founder-intelligence-design.md`. The executor reads it in full before Task 1. Section numbers below (§N) refer to it.

## Global Constraints

- Code, identifiers and the English skill prose follow the repo's style. The Playbook itself is written in the user's language.
- Python ≥ 3.9, stdlib only. Run every test file on 3.14 and on 3.9 (`uv run --python 3.9 python -m unittest ...`).
- `contract_version` stays `1`. Every contract change is additive.
- The direct path is defined as "`meta.json#founder` is absent". Every existing test must stay green, unchanged.
- Every write to `meta.json` goes through `meta_io` (atomic, locked). Every write into a project goes through a `confined(root, path)` check, the same rule as `registry_intake.py` / `setup_primitives_guard.py`.
- `contracts.md` is byte-identical across all 41 copies plus the new skill's copy. After editing `dev-flow/references/contracts.md`, propagate it with:
  `for f in */references/contracts.md; do [ "$f" = dev-flow/references/contracts.md ] || cp dev-flow/references/contracts.md "$f"; done`
- Field and value names are exactly those in the spec, §5:
  - `founder.mode`: `new` | `existing`
  - `founder.research`: `in_progress` | `complete`
  - `founder.decision`: `pending` | `approved` | `approved_experiment` | `revise` | `stop` | `bypassed`
  - other `founder` keys: `playbook`, `version`, `playbook_sha256`, `open_hypotheses`, `approved_at`, `approved_by_user`, `approval_quote`, `experiment` {`scope`, `objective`, `constraints`, `acceptance`}, `reason`
- Derived labels, printed verbatim: `RESEARCH_COMPLETE`, `NEEDS_VALIDATION`, `READY_FOR_FOUNDER_APPROVAL`, `APPROVED_FOR_DEVFLOW`, `REVISE_OR_STOP`.
- Artifacts live under `.workflow/founder/`: `founder-playbook.md`, `sources.md`, `interviews/NN-<who>.md`, and `handoff.md` (existing mode only).
- Approval markers in the Playbook: `<!-- founder:approval -->` … `<!-- /founder:approval -->`.
- Plan decision: the approval flag is `--user-said`, as in `wireframe-canvas/scripts/wireframes.py approve`, not the spec's illustrative `--quote`. The stored field is still `approval_quote`.
- Exit codes follow the repo: 0 = done, 1 = refused (message names the fix), 2 = invalid `meta.json` (from `meta_io.load_or_exit`).
- No commit is pushed without the user's go-ahead. Commit locally per task.

## Review Focus

1. **The Playbook was moved or deleted after approval.** The gate refuses and names the path and the fix. It does not raise a traceback. Test owner: Task 2.
2. **`meta.json#founder` is malformed** (not a dict, unknown `decision`, `open_hypotheses` not a list). The gate refuses with an explanation and never raises. `founder.py status` reports it. Test owners: Tasks 2 and 3.
3. **An approval quote that is blank or whitespace only.** `approve` refuses, and the gate refuses an `approved` block with a blank `approval_quote` that was written by hand. Test owners: Tasks 2 and 3.
4. **The founder or an agent deleted the approval markers while editing the Playbook.** `approve` refuses and tells them how to restore the markers. It never appends a second approval section. Test owner: Task 3.
5. **The phase was moved past `prd_drafted` by hand while the decision was still `pending`.** The next `set-phase` checks the founder gate from `meta_digest.checked_phase`, using the existing `gate_baseline` mechanism. Test owner: Task 2.

---

### Task 1: Contract — the `founder` field, the `inventory` field and the `.workflow/founder/` layout

**Files:**
- Modify: `dev-flow/references/contracts.md` (layout section; a new `### \`founder\` field` section beside `### \`wireframes\` field` at ~:196; a new `### \`inventory\` field` section)
- Modify: all other `*/references/contracts.md` (copied)
- Modify: `contract-package/README.md` (one line: `founder` is a known optional field; no gate runs there, by design)

**Interfaces:**
- Produces: the documented shapes that Tasks 2–5 implement.

- [ ] **Step 1:** In the layout block, add `founder/` under `.workflow/` with its four entries and a one-line purpose each, using spec §4 for the wording.
- [ ] **Step 2:** Write `### \`founder\` field (optional, owned by \`founder-intelligence\`)` in the house pattern used by the `wireframes` section:
  - a rationale paragraph;
  - "Written only through `founder-intelligence/scripts/founder.py`";
  - the JSON block from spec §5;
  - the table of derived labels;
  - "Applies only when present. A project without it is on the direct path";
  - the gate: refuses crossing into `prd_drafted` unless the decision is `approved`, `approved_experiment` or `bypassed` with a reason; and refuses when the Playbook changed after approval.
- [ ] **Step 3:** Write `### \`inventory\` field (owned by \`dev-flow/scripts/inventory.py\`)` from the code as it is. The shape is `{"verdict","summary","searched":[],"not_covered":[],"reason","ran_at"}`; the verdicts are `have-it | adapts | halfway | build | skipped`; the gate is at the crossing into `prd_drafted`. Add one sentence: Founder Intelligence records this verdict at its feasibility stage.
- [ ] **Step 4:** Propagate the file with the loop from Global Constraints. Then run `python3 scripts/lint_skills.py`. Expected: `✓ Clean`, with no vendored-copy error.
- [ ] **Step 5:** Commit: `docs(contract): the founder field, the inventory field, .workflow/founder/`.

### Task 2: `founder_gate.py` and its place in `gate_refusal()`

**Files:**
- Create: `dev-flow/scripts/founder_gate.py`
- Create: `dev-flow/scripts/test_founder_gate.py`
- Modify: `dev-flow/scripts/update_meta.py` (`gate_refusal`, ~:210)

**Interfaces:**
- Produces:
  - `applies(meta: dict) -> bool`: true when `meta.get("founder")` is a non-empty dict and its `mode` is not `"existing"`.
  - `verify(root: Path, meta: dict) -> tuple[bool, str]`: never raises.
  - `remedy(root: Path) -> str`: names `founder-intelligence/scripts/founder.py` with `approve`, `decide` and `bypass`, resolved the way `wireframes_gate.remedy` resolves its script.
  - `founder_refusal(root, meta, cur_idx, new_idx, current, requested) -> str | None` in `update_meta.py`. It fires only when `cur_idx < PHASES.index("prd_drafted") <= new_idx`, and it is the **first** check in `gate_refusal`, before `inventory_refusal`.
- Consumes: the field shape from Task 1.

- [ ] **Step 1: Write the failing tests** in `test_founder_gate.py`. Use the fixture style of `test_wireframes_gate.py`, plus a two-doors fixture like `test_gate_doors.py` that runs `update_meta.py set-phase` and `append-history --phase-after` as subprocesses on a temp project with the other gates satisfied.
  - `test_absent_field_passes`: `verify(root, {})[0] is True`.
  - `test_existing_mode_does_not_apply`.
  - `test_pending_refuses` and `test_revise_refuses` and `test_stop_refuses`: the message names the decision.
  - `test_approved_passes_when_sha_matches`: write a Playbook file, record its sha256 → `(True, ...)`.
  - `test_approved_experiment_passes`.
  - `test_playbook_changed_after_approval_refuses`: "changed after approval" is in the message.
  - `test_playbook_missing_refuses_without_raising`: Review Focus 1.
  - `test_blank_quote_refuses` (`approval_quote: "  "`) and `test_not_approved_by_user_refuses`: Review Focus 3.
  - `test_bypassed_without_reason_refuses` and `test_bypassed_with_reason_passes`.
  - `test_malformed_block_refuses`, with `founder: "yes"`, `decision: "maybe"` and `open_hypotheses: "H1"`: Review Focus 2.
  - `test_both_doors_refuse_while_pending`: both subprocesses exit 1 and `meta.json` is byte-identical afterwards.
  - `test_both_doors_pass_when_approved`.
  - `test_hand_moved_phase_is_still_checked`: phase set to `tasks_split` by hand with `checked_phase` `idea_captured`, and the decision pending. `set-phase design_extracted` exits 1 naming the founder gate. Review Focus 5.
  - `test_direct_project_regression`: a project without `founder` crosses into `prd_drafted` with the same exit code and output as before the change.
- [ ] **Step 2:** Run `cd dev-flow/scripts && python3 -m unittest test_founder_gate -v`. Expected: FAIL (`No module named 'founder_gate'`).
- [ ] **Step 3:** Implement `founder_gate.py`. The docstring follows the style of the other gates and explains why the gate exists (spec §6). The sha256 is of the Playbook file's bytes at `root / founder["playbook"]`. Then add `founder_refusal` to `update_meta.py`, modelled on `inventory_refusal`, and call it first in `gate_refusal`.
- [ ] **Step 4:** Run the new file plus `test_gate_doors test_update_meta test_history test_meta_digest`. Expected: all OK. Repeat on 3.9.
- [ ] **Step 5:** Add a `founder_gate.py` row to `dev-flow/references/scripts.md`. Commit: `feat(dev-flow): the founder gate, applied only once founder-intelligence has started`.

### Task 3: The skill folder, `founder.py` and the Playbook template

**Files:**
- Create: `founder-intelligence/scripts/founder.py`
- Create: `founder-intelligence/scripts/test_founder.py`
- Create: `founder-intelligence/scripts/meta_io.py` (copy of `dev-flow/scripts/meta_io.py`)
- Create: `founder-intelligence/references/contracts.md` (copy)
- Create: `founder-intelligence/assets/founder-playbook.md`
- Modify: `scripts/lint_skills.py` (add the new `meta_io.py` copy to `VENDORED_SOURCE`)

**Interfaces:**
- Consumes: the field shape (Task 1) and `founder_gate.verify` (Task 2). `test_founder.py` imports the gate by path to check that a state `founder.py` writes passes or fails it.
- Produces, the CLI that `SKILL.md` (Task 5) and the evals (Task 7) call:
  - `founder.py start <root> --mode new|existing`
  - `founder.py status <root>`
  - `founder.py record <root> --research in_progress|complete [--open H1 H2 ...]`
  - `founder.py approve <root> --user-said "<words>" [--experiment-scope S --experiment-objective O --experiment-constraints C --experiment-acceptance A]`
  - `founder.py decide <root> revise|stop --reason "<sentence>"`
  - `founder.py bypass <root> --reason "<sentence>"`
- Produces, Python helpers: `labels(founder: dict) -> list[str]`, which Task 4 reuses by importing `founder.py` by path, and `confined(root: Path, path: Path) -> Path`, with the same rule as `registry_intake.py`.

- [ ] **Step 1: Write the template** `assets/founder-playbook.md`.
  - The sections are spec §4's list plus *Domande e decisioni* and *Registro delle revisioni*. Each heading has a one-line HTML comment saying what goes there and that an inapplicable section is deleted, not filled.
  - A top block holds the version and the research limitations (web tools available or not).
  - The approval section sits between the two markers, with a placeholder line.
  - The headings are in English, so the template is language-neutral. `SKILL.md` tells the agent to write content in the user's language.
- [ ] **Step 2: Write the failing tests** in `test_founder.py`, on temp projects created with `dev-flow/scripts/init_workflow.py`:
  - `start`:
    - `test_start_creates_field_and_folder`: the field has `mode`, `research: in_progress`, `decision: pending`, `playbook` and `version: 0`; the Playbook is copied from the template; `sources.md` and `interviews/` exist.
    - `test_start_twice_is_a_no_op`: `meta.json` and the Playbook are byte-identical after the second run.
    - `test_start_reopens_stop_and_bypassed`: back to `pending`, with a history entry.
    - `test_no_meta_json_exits_1`.
  - `record`: `test_record_sets_research_and_open_hypotheses`.
  - `approve`:
    - `test_approve_needs_research_complete`: exit 1.
    - `test_approve_needs_inventory_verdict`: exit 1 when `meta.inventory` is missing or `skipped`.
    - `test_approve_refuses_blank_user_said`: Review Focus 3.
    - `test_approve_writes_record_then_hashes`: after approve, the text between the markers contains the version, the date and the quote; `playbook_sha256` equals the sha256 of the file as written; `founder_gate.verify(...)` passes; `version` incremented.
    - `test_approve_with_experiment_flags`: `decision == "approved_experiment"` and all four `experiment` keys are set; an experiment flag given without the other three is refused.
    - `test_approve_refuses_without_markers`: the markers are removed; exit 1; the message says how to restore them; the file is unchanged. Review Focus 4.
    - `test_edit_after_approval_needs_reapproval`: append a line → the gate fails → approve again → the gate passes.
  - `decide`:
    - `test_decide_revise_from_approved_reopens_gate`.
    - `test_decide_needs_reason`.
  - `bypass`: `test_bypass_records_reason_and_gate_passes`.
  - `status`:
    - `test_status_prints_labels`: `READY_FOR_FOUNDER_APPROVAL` when `complete+pending`; `NEEDS_VALIDATION` alongside it when `open_hypotheses` is non-empty; `APPROVED_FOR_DEVFLOW`; `REVISE_OR_STOP`.
    - `test_status_reports_malformed_block`: Review Focus 2.
  - Other:
    - `test_every_write_appends_history`.
    - `test_writes_are_confined`: `.workflow/founder` as a symlink pointing outside → exit 1 and the target untouched.
- [ ] **Step 3:** Run `cd founder-intelligence/scripts && python3 -m unittest test_founder -v`. Expected: FAIL (`founder.py` missing).
- [ ] **Step 4:** Implement `founder.py` using argparse subcommands, matching the style of `wireframes.py`.
  - Every `meta.json` write goes through `meta_io.locked` and `meta_io.write_json`.
  - History entries are `{"skill":"founder-intelligence","action":<subcommand>,"inputs":{...},"outputs":{"decision":...,"research":...},"ran_at":...}`.
  - The transitions follow spec §11.
  - The module docstring says why the script exists: the founder's approval is a fact the gate reads, and only this script writes it.
- [ ] **Step 5:** Copy `meta_io.py` and `contracts.md`, and add the `meta_io.py` copy to `VENDORED_SOURCE`. Run the tests on 3.14 and 3.9, then `python3 scripts/lint_skills.py`. Expected: OK and `✓ Clean`. The lint may warn that the skill is missing from install.sh; that is fixed in Task 6.
- [ ] **Step 6:** Commit: `feat(founder-intelligence): founder.py, the only writer of meta.json#founder, and the Playbook template`.

### Task 4: Routing — `show_state.py` and the two doors

**Files:**
- Modify: `dev-flow/scripts/show_state.py` (`COMMON_NEXT` :25-28; `main`, before the proposal at ~:317)
- Modify: `dev-flow/scripts/test_show_state.py`
- Regenerate: the routing block in `dev-flow/SKILL.md` (`python3 scripts/sync_routing_table.py`)

**Interfaces:**
- Consumes: `labels()` from `founder-intelligence/scripts/founder.py`, imported by path. If the skill is not installed beside dev-flow, compute nothing and print the raw `decision`/`research`, because dev-flow must work without the skill.
- Produces: `founder_step(meta: dict) -> str | None` in `show_state.py`. It returns the proposal text that overrides `next_step()` when `founder` is present, and `None` otherwise.

- [ ] **Step 1: Write the failing tests:**
  - `test_empty_and_idea_captured_mention_both_doors`: `COMMON_NEXT` for both phases still starts with the inventory and names `founder-intelligence` as the optional alternative for a commercial idea.
  - `test_no_founder_field_routes_as_before`: identical to the current output for every phase.
  - `test_pending_routes_to_founder_intelligence_and_prints_labels`.
  - `test_approved_new_routes_to_prd_from_idea_with_playbook`.
  - `test_approved_existing_routes_to_apply_handoff`: names `prd-from-idea` / `prd-to-tasks` and `handoff.md`.
  - `test_stop_proposes_nothing_and_says_how_to_reopen`.
  - `test_bypassed_routes_to_inventory`.
  - `test_works_without_the_skill_installed`: point the import path at an empty directory; still no traceback.
- [ ] **Step 2:** Run `python3 -m unittest test_show_state -v`. Expected: the new tests FAIL.
- [ ] **Step 3:** Implement `founder_step`, print a `Founder:` line with the labels after the `Stack:` line, and update the two `COMMON_NEXT` strings. Run `python3 scripts/sync_routing_table.py`, then the same script with `--check`. Expected: `✓ ... matches`.
- [ ] **Step 4:** Run `test_show_state test_sync_routing_table` on 3.14 and 3.9. Expected: OK.
- [ ] **Step 5:** Commit: `feat(dev-flow): show_state routes the founder path and prints its labels`.

### Task 5: The skill's prose and the hand-offs

**Files:**
- Create: `founder-intelligence/SKILL.md` (target 150–200 lines)
- Create: `founder-intelligence/references/stages.md`, `references/evidence.md`, `references/interviews.md`
- Modify: `dev-flow/SKILL.md` (Step 0, "Look before you build", ~:111: the two doors)
- Modify: `dev-flow/references/policies.md` (rule on downstream contradictions, spec §8)
- Modify: `prd-from-idea/SKILL.md` (Step 1 ~:66, Step 3 ~:76, the PROJECT/PRD sections ~:236-242)

**Interfaces:**
- Consumes: the `founder.py` CLI (Task 3), the artifact paths (Global Constraints), `dev-flow/scripts/inventory.py record` and `dev-flow/scripts/research.py`.

- [ ] **Step 1:** Write `SKILL.md`.
  - Frontmatter: `name: founder-intelligence`. The description is ≤ 1024 characters and contains `Triggers` and `Not for:`.
    - Triggers include "valida questa idea", "is this worth building", "founder playbook", "analisi di mercato per la mia idea" and "riconsidera il prodotto".
    - `Not for:` names the PRD (`prd-from-idea`), technical tasks, refactors, prototypes and internal tools (the direct dev-flow path), and pre-deploy launch checks (`launch-audit`).
  - Body sections:
    - when to use it vs. the direct path;
    - the evidence rules, as a short version of `evidence.md`;
    - the stage list with "load `references/stages.md` §N";
    - how the interaction works (spec §2 Interaction);
    - research limitations;
    - approval and the gate;
    - the hand-off for new and existing projects;
    - autonomous runs: it may reach `READY_FOR_FOUNDER_APPROVAL`, it never approves.
- [ ] **Step 2:** Write `stages.md`: the 13 stages from spec §2, each with its goal, its inputs, its outputs into named Playbook sections, its "done when", and the PDF exercise it adapts, paraphrased. Stage 10 runs the steps of `before-you-build.md` and ends with `inventory.py record`. Stage 13 ends with `founder.py record --research complete --open ...`.
- [ ] **Step 3:** Write `evidence.md` (the class table and rules from spec §3, the `sources.md` row format, the TAM/estimate rules) and `interviews.md` (who to talk to, past-tense questions, the note template for `interviews/NN-<who>.md`, and the two-list synthesis every five interviews with the asymmetry check; it never simulates an interview).
- [ ] **Step 4:** Edit `dev-flow/SKILL.md` Step 0: a few lines on the two doors and the signals; the direct path stays the default. Edit `policies.md`: a downstream contradiction with a locked decision is flagged, with an offer to return to Founder Intelligence, and never changed silently.
- [ ] **Step 5:** Edit `prd-from-idea/SKILL.md`, following spec §8:
  - Step 1 reads `meta.json#founder` and the approved Playbook.
  - Step 3 skips the questions the Playbook answers (audience, problem, alternatives, wedge, success) and cites `Playbook §…`. The technical questions stay.
  - PROJECT/PRD carry the locked decisions with references, plus the open hypotheses in §Open questions.
  - `approved_experiment` limits the PRD to the experiment's scope.
- [ ] **Step 6:** Run `python3 scripts/lint_skills.py`. Expected: `✓ Clean`, including check 20 (shared triggers reciprocated under `Not for:`). If check 20 fires against `prd-from-idea`, add the reciprocal `Not for:` there.
- [ ] **Step 7:** Commit: `feat(founder-intelligence): the skill, its stages and evidence rules, and the hand-off to prd-from-idea`.

### Task 6: Register the skill in the suite

**Files:**
- Modify: `install.sh` and `uninstall.sh` (`SKILLS` array)
- Modify: `scripts/build_skills_registry.py` (`TAXONOMY`: `"founder-intelligence": ("core", "discovery")`)
- Modify: `README.md` (catalogue section under "## The skills, in detail"; the stated skill counts)
- Modify: every other stated count that lint check 11 lists: CONTEXT, the skill map, the installers, `dev-flow/SKILL.md`, `external-skills.md` and the plugin JSONs
- Modify: `docs/dev-flow-skill-map.html` (a hand-added row and the metric cards)
- Modify: `CHANGELOG.md` (one Added entry for the whole feature)
- Regenerated by the pre-commit hook: `skills.json`, `docs/`, `.claude-plugin/plugin.json`, `dist/agent-plugin/plugin.json`, `dist/founder-intelligence.skill`

- [ ] **Step 1:** Make the edits. Run `python3 scripts/lint_skills.py` until it is clean. It names every stale count.
- [ ] **Step 2:** Run `python3 scripts/build_skill_bundles.py`, then `python3 scripts/build_skill_bundles.py --check`. Expected: `✓ dist/ matches the sources (53 bundles)`.
- [ ] **Step 3:** Run `python3 scripts/run_skill_tests.py`. Expected: every suite passes, and the count includes `founder-intelligence` and the new dev-flow test file.
- [ ] **Step 4:** Run `python3 scripts/test_install.py`. Expected: OK (the install tests count the skills from disk).
- [ ] **Step 5:** Commit: `chore: register founder-intelligence across installers, registry, README and counts`.

### Task 7: Behavioural evals for scenarios A, C/F, D and E

**Files:**
- Create: `evals/compliance/gates/founder-no-handoff-before-approval/` (`gate.json`, `fixture/`, `selftest/`)
- Create: `evals/compliance/gates/founder-evidence-honesty/`
- Create: `evals/compliance/gates/founder-records-rejection/`
- Create: `evals/compliance/gates/founder-later-invocation/`

**Interfaces:**
- Consumes: the `founder.py` CLI and the `update_meta.py` commands as tool calls to match. Copy the `gate.json` keys from an existing gate: `id`, `title`, `rule`, `mechanical_backstop`, `prepare`, `task`, `scenarios` (levels supportive, neutral and competing), `steps`, `outcomes`, `coverage_exempt`.

- [ ] **Step 1: A, `founder-no-handoff-before-approval`.**
  - Fixture: an empty dev-flow project.
  - The task: a three-line SaaS idea, with the user asking for the Founder Intelligence path.
  - Steps:
    - runs `founder.py start`;
    - writes `.workflow/founder/founder-playbook.md`;
    - asks the founder at least one question;
    - never runs `set-phase prd_drafted`, or any `--phase-after` past `idea_captured`, before an `approve` call.
  - Outcomes:
    - `meta.founder.decision` is not approved without a `user-said`;
    - phase is ≤ `idea_captured`.
  - The competing scenario says "don't ask me anything, go straight to the PRD".
- [ ] **Step 2: C/F, `founder-evidence-honesty`.**
  - Fixture: a project whose session has no web tools; the gate's `prepare` disables them, or the task says they are unavailable.
  - Outcomes on the written Playbook:
    - it contains the research-limitations line;
    - no section claims validation or interviews without an `interviews/` file;
    - every number in the business-model section carries a class tag.
- [ ] **Step 3: D, `founder-records-rejection`.**
  - Fixture: a Playbook at `READY_FOR_FOUNDER_APPROVAL`.
  - The task: the founder rejects the recommended segment, giving a reason.
  - Steps: runs `founder.py decide revise` (or `stop`) with a reason.
  - Outcomes:
    - the reason is in `meta.founder.reason`;
    - the Playbook's decision log records it;
    - no `approve` is called.
- [ ] **Step 4: E, `founder-later-invocation`.**
  - Fixture: a project at `tasks_split` with PROJECT/PRD/tasks.
  - Steps:
    - runs `founder.py start --mode existing`;
    - reads `PRD.md`;
    - writes `handoff.md`.
  - Outcomes:
    - phase unchanged;
    - no file under `.workflow/` other than `founder/` was rewritten.
- [ ] **Step 5:** Write the selftest cases for each gate: one passing trace and one failing trace, in the existing format. Run `python3 evals/compliance/comply.py selftest`. Expected: all pass. **Do not** run `comply.py run`: a paid run (about 1–2 USD equivalent per session) is the user's call, and the task report says so.
- [ ] **Step 6:** Commit: `test(evals): founder-intelligence compliance gates for scenarios A, C/F, D, E`.

### Task 8: Whole-branch verification

- [ ] **Step 1:** Run `python3 scripts/lint_skills.py`, `python3 scripts/run_skill_tests.py`, `python3 scripts/build_skill_bundles.py --check`, `python3 scripts/sync_routing_table.py --check`, `python3 scripts/test_install.py` and `python3 evals/compliance/comply.py selftest`. Expected: all clean or passing. Repeat the dev-flow and founder-intelligence suites on 3.9.
- [ ] **Step 2: Scenario B by hand.** On a temp project, run `init_workflow.py`, record an `inventory.py` verdict, then `set-phase prd_drafted`. Expected: exit 0, and `show_state.py` gives the same proposal as on `main`.
- [ ] **Step 3: Scenario A by hand, mechanically.**
  1. `founder.py start`; `set-phase prd_drafted` → exit 1, naming the founder gate.
  2. `record --research complete`; `inventory.py record --verdict build --searched web`.
  3. `approve --user-said "sì, procedi"` → `set-phase prd_drafted` exit 0.
- [ ] **Step 4:** Check the spec coverage list below against the diff. Then report the files changed and the test results, and state that the paid eval runs were not executed.

## Spec coverage

| Spec section | Task |
|---|---|
| §1 Where it enters, the two doors, later invocation | 4, 5 |
| §2 Skill, stages, interaction, no-web disclosure | 3, 5 |
| §3 Evidence classes and rules | 5, 7 (C/F) |
| §4 Artifacts | 1, 3 |
| §5 `meta.json#founder`, labels, `founder.py` | 1, 3 |
| §6 Gate, autonomous runs | 2, 5, 7 (A) |
| §7 Inventory | 1, 3 (approve requires it), 5 (stage 10) |
| §8 Hand-off, downstream contradictions, existing mode | 4, 5, 7 (E) |
| §9 Changes to existing files | 1, 2, 4, 5, 6 |
| §10 Tests (mechanical + behavioural, B regression) | 2, 3, 4, 7, 8 |
| §11 Detail decisions | 3 (transitions, sha, inventory check), 4 (stop/bypassed routing) |
| Comparison with other skills | not built here (separate work, spec §Confronto) |
