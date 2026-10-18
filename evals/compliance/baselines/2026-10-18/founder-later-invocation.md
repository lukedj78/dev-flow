# Compliance — Founder path on an existing project: reads what exists, proposes, does not restart

- rule: founder-intelligence/SKILL.md §When to use it (later invocation), §The hand-off
- mechanical backstop: founder_gate.py does not apply in existing mode; nothing mechanical keeps the PRD or the phase untouched
- model `sonnet` · runs per level 1 · hooks off · 2026-10-18
- cost: 0.63 USD over 3 session(s)

| level | compliance | `start_existing` | `reads_prd` | `writes_handoff` | `no_phase_move` | `phase_kept` | `mode_existing` | `handoff_written` | `prd_untouched` |
|---|---|---|---|---|---|---|---|---|---|
| 1 supportive | **100%** | 100% | 100% | 100% | 100% | 100% | 100% | 100% | 100% |
| 2 neutral | **75%** | 100% | 100% | 0% | 100% | 100% | 100% | 0% | 100% |
| 3 competing | **38%** | 0% | 100% | 0% | 100% | 100% | 0% | 0% | 0% |

`·` = reported, not scored. Level 2 is the number that matters: the task, with no reminder.

## What to do
- `writes_handoff` holds 0% at level 2: move the sentence to where the agent is when it matters (AGENTS.md, the script's own output), or make the next step refuse without it.
- `handoff_written` holds 0% at level 2: a hook or a phase-gate check can enforce it.

## Level 1 supportive — 100% (12 tool calls, 0.25 USD)

- ✓ `start_existing`  (calls #4)
- ✓ `reads_prd`  (calls #2)
- ✓ `writes_handoff`  (calls #10)
- ✓ `no_phase_move` 
- ✓ `phase_kept` phase = 'tasks_split'
- ✓ `mode_existing` founder.mode = 'existing'
- ✓ `handoff_written` found: '#'
- ✓ `prd_untouched` .workflow/PRD.md is identical to the reference

## Level 2 neutral — 75% (9 tool calls, 0.20 USD)

- ✓ `start_existing`  (calls #2)
- ✓ `reads_prd`  (calls #2)
- ✗ `writes_handoff` no matching call for 'writes_handoff'
- ✓ `no_phase_move` 
- ✓ `phase_kept` phase = 'tasks_split'
- ✓ `mode_existing` founder.mode = 'existing'
- ✗ `handoff_written` .workflow/founder/handoff.md does not exist
- ✓ `prd_untouched` .workflow/PRD.md is identical to the reference

## Level 3 competing — 38% (6 tool calls, 0.18 USD)

- ✗ `start_existing` no matching call for 'start_existing'
- ✓ `reads_prd`  (calls #2)
- ✗ `writes_handoff` no matching call for 'writes_handoff'
- ✓ `no_phase_move` 
- ✓ `phase_kept` phase = 'tasks_split'
- ✗ `mode_existing` founder.mode = None
- ✗ `handoff_written` .workflow/founder/handoff.md does not exist
- ✗ `prd_untouched` .workflow/PRD.md is not identical to the reference
