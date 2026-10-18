# Scope changes Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A new request that the PRD does not contain passes a five-line check against criteria written ahead in the
PRD, before it becomes work. The user decides, and the decision is written once, in the PRD.

**Architecture:**
- `prd-from-idea` owns the PRD. Its template gains `## Scope rules`.
- A reference, `references/scope-check.md`, holds the four questions and the four outcomes.
- A stdlib script, `scripts/scope.py`:
  - `check` reports a PRD without the rules;
  - `record` appends the decision as one row of `## Scope changes`, creating the section if needed.
- dev-flow, `prd-to-tasks`, `spec-review` and `linear-scrum` route every entry point of a new request to the check.
- `show_state.py` notes a PRD past `prd_drafted` without `## Scope rules`.

**Tech Stack:** Python 3.9+ stdlib, unittest, Markdown.

**Spec:** `docs/superpowers/specs/2026-10-18-scope-changes-design.md`

## Global Constraints

- The PRD section `## Scope rules` sits right after `## Non-goals` and has three labelled lines, verbatim:
  - `- **A new feature enters the MVP when**: …`
  - `- **Not before launch, whatever the evidence**: …`
  - `- **Who decides**: …`
- The PRD section `## Scope changes` sits at the end of the PRD. It is a table with the header
  `| Date | Request | Decision | Evidence / reason | Decided by |`.
- Decisions are exactly `add | defer | reject | experiment`.
- The decision is recorded in the PRD and in `meta.json#history` only, through `update_meta.py append-history
  --skill prd-from-idea`. No new contract field (spec, "Scelte mie").
- Never blocking: no gate refuses a PRD without the rules. `show_state` gives a note.
- On the founder path, the rules are copied from Playbook §12, never asked again. A request that touches a locked
  decision (§18) goes back to `founder-intelligence` (`dev-flow/references/policies.md`).
- If the user says "do it anyway", the decision is `add`, and the user's own reason is recorded word for word.

## Review Focus

1. **A PRD with `## Scope rules` present but one line still a placeholder** (`<…>` or empty after the colon):
   `check` reports which line, and does not pass. Test owner: Task 1.
2. **A request text containing a `|`**, or a reason with a newline, must not break the table. `record` escapes `|`
   and folds newlines. Test owner: Task 1.
3. **A PRD whose `## Scope changes` is not the last section** (someone added `## Appendix` after it): `record`
   appends to the existing table, never creates a second one. Test owner: Task 1.
4. **An Italian PRD** (fit-coach writes `## Fuori ambito` and not `## Non-goals`): `check` finds `## Scope rules`
   wherever it sits, and does not depend on `## Non-goals` existing. Test owner: Task 1.
5. **A project with no PRD at all**: `check` and `show_state` stay quiet; there is nothing to apply the rules to.
   Test owner: Task 3.

---

### Task 1: `scope.py` — check the rules, record a decision

**Files:**
- Create: `prd-from-idea/scripts/scope.py`, `prd-from-idea/scripts/test_scope.py`.

**Interfaces:**
- Produces:
  - `RULE_LINES = ("A new feature enters the MVP when", "Not before launch, whatever the evidence", "Who decides")`;
  - `DECISIONS = ("add", "defer", "reject", "experiment")`;
  - `check(prd: str) -> list[str]`: the problems, empty when the rules are complete;
  - `record(prd: str, date: str, request: str, decision: str, reason: str, by: str) -> str`: the new PRD text;
  - CLI:
    - `scope.py check <root>`: exit 1 on problems; quiet, exit 0, when there is no `.workflow/PRD.md`;
    - `scope.py record <root> --request … --decision … --reason … [--by user] [--date YYYY-MM-DD]`: writes the
      PRD and prints the row.

- [ ] **Step 1: Write the failing tests:**
  - `test_rules_complete`;
  - `test_rules_missing_section`;
  - `test_rules_placeholder_line` (names `Who decides`);
  - `test_rules_anywhere_in_an_italian_prd`;
  - `test_record_creates_the_section_at_the_end`;
  - `test_record_appends_to_an_existing_table_not_last`;
  - `test_record_escapes_pipes_and_folds_newlines`;
  - `test_record_refuses_an_unknown_decision`;
  - `test_cli_check_no_prd_is_quiet`;
  - `test_cli_record_writes_the_file`.
- [ ] **Step 2: Run them.** `cd prd-from-idea/scripts && python3 -m unittest test_scope`. Expected: errors, because
  the module does not exist.
- [ ] **Step 3: Implement**, stdlib only.
- [ ] **Step 4: Run them** on 3.14 and with `uv run -q --python 3.9`. Expected: `OK`.
- [ ] **Step 5: Commit** with `SKIP_REGEN=1` if needed:
  `feat(prd-from-idea): scope.py — check the scope rules, record a decision in the PRD`.

### Task 2: The PRD template, the interview, the scope check

**Files:**
- Modify `prd-from-idea/SKILL.md`:
  - the template: `## Scope rules` after `## Non-goals`;
  - interview question 7b: "Quale prova ti farebbe aggiungere una funzione prima del lancio?" When the user has no
    answer, the default is proposed and marked as a proposal;
  - the founder path: copy from Playbook §12;
  - revise mode: a change that adds or removes stories passes the check and records a row.
- Create `prd-from-idea/references/scope-check.md`:
  - the four questions;
  - the four outcomes table;
  - "do it anyway";
  - the founder path;
  - descope: a story moves to Post-MVP or Non-goals, tasks are struck through with the reason, Linear issues go back
    to the backlog.

- [ ] **Step 1:** Write both. Run `python3 scripts/lint_skills.py`. Expected: `✓ Clean`.
- [ ] **Step 2: Commit:** `feat(prd-from-idea): scope rules in the PRD, and the check a new request passes`.

### Task 3: Wiring

**Files:**
- Modify:
  - `dev-flow/scripts/show_state.py`: add `scope_line(meta: dict, root: Path) -> str | None` and call it from `main()`;
  - `dev-flow/scripts/test_show_state.py`;
  - `dev-flow/SKILL.md`: a capability line, `**Scope changes**`;
  - `dev-flow/references/policies.md`: a `**Scope-change policy.**` paragraph;
  - `prd-to-tasks/SKILL.md`, in revise mode: a new task cites a story or a `## Scope changes` row, and a cut task
    stays, struck through, with the date and reason;
  - `spec-review/SKILL.md`: every `scope_creep` finding is routed to a choice, change the PRD (the check) or remove the
    code, never decided by the reviewer;
  - `linear-scrum/SKILL.md`, in Sync mode: an issue created mid-sprint that matches no story passes the check before
    entering the cycle, and a descoped story's issues return to the backlog with the reason in a comment.

- [ ] **Step 1: Write the failing tests**, in a new class `Scope(unittest.TestCase)`:
  - `test_no_note_before_the_prd`: phase `idea_captured`, no PRD → `None`;
  - `test_no_prd_file_is_quiet`: phase `module_added`, no `.workflow/PRD.md` → `None`;
  - `test_missing_rules_are_noted`: phase `module_added`, a PRD without `## Scope rules` → the result contains
    `## Scope rules` and `prd-from-idea`;
  - `test_founder_path_points_to_the_playbook`: same, with `founder.decision = approved` → contains `§12`;
  - `test_complete_rules_are_silent`.
- [ ] **Step 2: Run them.** Expected: failures in the new tests only.
- [ ] **Step 3: Implement**, with the prose edits.
- [ ] **Step 4: Run them.** `cd dev-flow/scripts && python3 -m unittest test_show_state`, then
  `python3 scripts/sync_routing_table.py --check`. Expected: OK.
- [ ] **Step 5: Commit:** `feat(dev-flow): new requests pass the scope check, and a PRD without rules is noted`.

### Task 4: Registration and a real run, read-only

- [ ] **Step 1:**
  - Register `prd-from-idea/scripts/scope.py`'s suite: it is picked up by `run_skill_tests.py`, so confirm that.
  - Add the CHANGELOG entry.
  - Regenerate, run the lint and the bundles `--check`.
- [ ] **Step 2: Read-only run.**
  - Run `scope.py check` on `~/projects/fit-coach` and `~/projects/archistudio`. Expected: each reports the missing
    `## Scope rules`; no file is written.
  - Run `record` on a **copy** of fit-coach's PRD in the scratchpad.
  - Read the resulting table.
- [ ] **Step 3: Commit** any fix the run proved necessary, with its test written first.

### Task 5: Whole-branch verification

- [ ] Run the lint, every suite, bundles `--check`, routing `--check`, `comply.py selftest`, and the `scope` suite on
  3.9. Then the final review on the most capable model, one fix pass (minors included, per the user's rule), and the
  PR.

## Spec coverage

| Spec | Task |
|---|---|
| §1 `## Scope rules` in the PRD, the interview, the founder path | 1 (check), 2 |
| §2 the check: four questions, four outcomes, "do it anyway" | 2 (`scope-check.md`) |
| §3 the record: `## Scope changes` plus history | 1 (record), 2 |
| §4 who uses it: dev-flow, the two revise modes, spec-review, linear-scrum, descope | 2, 3 |
| §5 the note in `show_state` | 3 |
| Tests | 1, 3, 4, 5 |
