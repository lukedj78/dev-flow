# Compliance — Founder path on an existing project: reads what exists, proposes, does not restart

- rule: founder-intelligence/SKILL.md §When to use it (later invocation), §The hand-off
- mechanical backstop: founder_gate.py does not apply in existing mode; nothing mechanical keeps the PRD or the phase untouched
- model `sonnet` · runs per level 1 · hooks off · 2026-10-18
- cost: 0.20 USD over 1 session(s)

| level | compliance | `start_existing` | `reads_prd` | `writes_handoff` | `no_phase_move` | `phase_kept` | `mode_existing` | `handoff_written` | `prd_untouched` |
|---|---|---|---|---|---|---|---|---|---|
| 2 neutral | **100%** | 100% | 100% | 100% | 100% | 100% | 100% | 100% | 100% |

`·` = reported, not scored. Level 2 is the number that matters: the task, with no reminder.

## What to do
Every scored check holds at level 2. Nothing to promote.

## Level 2 neutral — 100% (14 tool calls, 0.20 USD)

- ✓ `start_existing`  (calls #8)
- ✓ `reads_prd`  (calls #3)
- ✓ `writes_handoff`  (calls #13)
- ✓ `no_phase_move` 
- ✓ `phase_kept` phase = 'tasks_split'
- ✓ `mode_existing` founder.mode = 'existing'
- ✓ `handoff_written` found: '#'
- ✓ `prd_untouched` .workflow/PRD.md is identical to the reference
