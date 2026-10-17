"""The phase enum and its legacy aliases: the one copy every script in this folder imports.

The canonical list is the table in dev-flow/references/contracts.md (§`phase` enum), and
test_phases.py fails if this file drifts from it.

This used to be two tables. update_meta.py knew one alias (`module-added`), show_state.py
three, so a project reading `page-generated` routed as `page_generated` but moved as if it had
no phase at all: `set-phase idea_captured` went through with exit 0 (AUDIT.md §6.2).

Two copies of the enum still live outside this folder, because their skills install standalone:
`PHASES_BEFORE_SCAFFOLD` in design-md-to-app/scripts/setup_design_lint.py, checked by
test_phases.py, and `Phase` in contract-package/, checked by that package's own tests.
"""
from __future__ import annotations

# Index = monotonic position. Skills may set a phase >= the current one, never lower.
PHASES = [
    "empty",
    "idea_captured",
    "prd_drafted",
    "tasks_split",
    "design_extracted",
    # Monorepo-only mid-bootstrap checkpoint (turborepo root before apps are scaffolded)
    "monorepo_initialized",
    "scaffolded",
    "page_generated",
    "module_added",
    # Cross-stack terminal progression beyond module_added (web / mobile / agent / monorepo)
    "feature_complete",
    "deployed",
]

# Kebab-case spellings found in older meta.json files. They are read as their snake_case phase
# and never written: set-phase stores the canonical name.
ALIASES = {
    "module-added": "module_added",
    "page-generated": "page_generated",
    "design-extracted": "design_extracted",
}


def normalize(value: object) -> object:
    """The canonical spelling of `value` if it is a known alias, otherwise `value` unchanged."""
    return ALIASES.get(value, value) if isinstance(value, str) else value


def index(value: object) -> int | None:
    """Position of `value` in PHASES (aliases accepted), or None when it is not a phase at all."""
    value = normalize(value)
    return PHASES.index(value) if isinstance(value, str) and value in PHASES else None


def before(phase: str) -> list[str]:
    """Every phase that comes before `phase`, in order."""
    return PHASES[:PHASES.index(phase)]
