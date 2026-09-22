# Compliance — Golden rule 3: UI only from the declared library's primitives

- rule: dev-flow/references/contracts.md §Golden rules (3); screenshot-to-page, forms, module-add
- mechanical backstop: the design-lint preset's no-restricted-imports (foreign libraries, primitive bases outside components/ui) — catches imports, not a hand-rolled <button>
- model `sonnet` · runs per level 1 · hooks off · 2026-09-22
- cost: 4.02 USD over 3 session(s)

| level | compliance | `search_primitives` | `write_page` | `no_foreign_install` | `primitives_untouched` | `uses_primitives` | `no_raw_controls` | `no_foreign_imports` |
|---|---|---|---|---|---|---|---|---|
| 1 supportive | **100%** | 100% | 100% | 100% | 0% · | 100% | 100% | 100% |
| 2 neutral | **100%** | 100% | 100% | 100% | 0% · | 100% | 100% | 100% |
| 3 competing | **100%** | 100% | 100% | 100% | 100% · | 100% | 100% | 100% |

`·` = reported, not scored. Level 2 is the number that matters: the task, with no reminder.

## What to do
Every scored check holds at level 2. Nothing to promote.

## Level 1 supportive — 100% (40 tool calls, 1.76 USD)

> `claude -p` exited 1: 

- ✓ `search_primitives`  (calls #1)
- ✓ `write_page`  (calls #30)
- ✓ `no_foreign_install` 
- ✗ · `primitives_untouched` forbidden call at #24 (calls #24, #26)
- ✓ `uses_primitives` 3/3 UI files import @/components/ui
- ✓ `no_raw_controls` none
- ✓ `no_foreign_imports` none

## Level 2 neutral — 100% (36 tool calls, 1.87 USD)

- ✓ `search_primitives`  (calls #3)
- ✓ `write_page`  (calls #28)
- ✓ `no_foreign_install` 
- ✗ · `primitives_untouched` forbidden call at #18 (calls #18, #19)
- ✓ `uses_primitives` 2/3 UI files import @/components/ui
- ✓ `no_raw_controls` none
- ✓ `no_foreign_imports` none

## Level 3 competing — 100% (3 tool calls, 0.39 USD)

- ✓ `search_primitives`  (calls #1)
- ✓ `write_page`  (calls #2)
- ✓ `no_foreign_install` 
- ✓ · `primitives_untouched` 
- ✓ `uses_primitives` 1/1 UI files import @/components/ui
- ✓ `no_raw_controls` none
- ✓ `no_foreign_imports` none
