"""dev-flow-contract — filesystem contract for agent-driven SDLC.

This package is the portable, runtime-independent core of dev-flow. The
Claude Code skills (and any future tool that wants to read/write a
`.workflow/` folder) depend on these primitives.

Public API:
    init_workflow(root, name=None)         → create .workflow/ + seed meta.json
    load_meta(root)                        → Meta dataclass
    save_meta(root, meta)                  → write meta.json
    record_artifact(root, path, produced_by, derived_from=None)
                                           → SHA-256 + register under meta#artifacts
    set_phase(root, phase, allow_regress=False)
                                           → forward-only phase bump
    append_history(root, skill, inputs, outputs, phase_after=None)
                                           → structured run record
    check_drift(root)                      → DriftReport with per-artifact status

Types:
    Phase           — enum of valid phase values
    Meta            — full meta.json shape
    Artifact        — single artifact entry
    Stack           — stack choices
    DriftRow        — one row in a drift report
    DriftReport     — full drift report (has_drift + rows)
"""
from .core import (
    Artifact,
    DerivedFrom,
    DriftReport,
    DriftRow,
    Meta,
    Phase,
    Stack,
    append_history,
    check_drift,
    init_workflow,
    load_meta,
    record_artifact,
    save_meta,
    set_phase,
    sha256_file,
)

__version__ = "0.1.0"

__all__ = [
    "__version__",
    "Phase",
    "Meta",
    "Stack",
    "Artifact",
    "DerivedFrom",
    "DriftRow",
    "DriftReport",
    "init_workflow",
    "load_meta",
    "save_meta",
    "record_artifact",
    "set_phase",
    "append_history",
    "check_drift",
    "sha256_file",
]
