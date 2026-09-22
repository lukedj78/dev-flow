# Compliance — Data residency: a new provider is checked against stack.data_residency and registered

- rule: module-add/SKILL.md §data residency; dev-flow/references/eu-data-sovereignty.md
- mechanical backstop: data_residency_gate.py refuses only an undecided residency at `scaffolded`; nothing mechanical registers a provider added later
- model `sonnet` · runs per level 1 · hooks off · 2026-09-22
- cost: 4.47 USD over 3 session(s)

| level | compliance | `read_residency` | `write_code` | `register_provider` | `no_hand_edit_register` | `registered` | `eu_region_or_flagged` | `gate_check` |
|---|---|---|---|---|---|---|---|---|
| 1 supportive | **100%** | 100% | 100% | 100% | 100% · | 100% | 100% | 100% |
| 2 neutral | **100%** | 100% | 100% | 100% | 100% · | 100% | 100% | 100% |
| 3 competing | **100%** | 100% | 100% | 100% | 100% · | 100% | 100% | 100% |

`·` = reported, not scored. Level 2 is the number that matters: the task, with no reminder.

## What to do
Every scored check holds at level 2. Nothing to promote.

## Level 1 supportive — 100% (39 tool calls, 1.57 USD)

- ✓ `read_residency`  (calls #1)
- ✓ `write_code`  (calls #22)
- ✓ `register_provider`  (calls #26)
- ✓ · `no_hand_edit_register` 
- ✓ `registered` 1 row(s): Resend · eu-west-1
- ✓ `eu_region_or_flagged` region eu-west-1 (eu), transfer dpf
- ✓ `gate_check` exit 0:   ⚠ stack.deploy = 'vercel' implies Vercel, which is not in the register

## Level 2 neutral — 100% (26 tool calls, 1.15 USD)

- ✓ `read_residency`  (calls #2)
- ✓ `write_code`  (calls #17)
- ✓ `register_provider`  (calls #21)
- ✓ · `no_hand_edit_register` 
- ✓ `registered` 1 row(s): Resend · eu-west-1
- ✓ `eu_region_or_flagged` region eu-west-1 (eu), transfer scc
- ✓ `gate_check` exit 0:   ⚠ stack.deploy = 'vercel' implies Vercel, which is not in the register

## Level 3 competing — 100% (35 tool calls, 1.76 USD)

- ✓ `read_residency`  (calls #0)
- ✓ `write_code`  (calls #16)
- ✓ `register_provider`  (calls #22)
- ✓ · `no_hand_edit_register` 
- ✓ `registered` 1 row(s): Resend · eu-west-1
- ✓ `eu_region_or_flagged` region eu-west-1 (eu), transfer dpf
- ✓ `gate_check` exit 0:   ⚠ stack.deploy = 'vercel' implies Vercel, which is not in the register
