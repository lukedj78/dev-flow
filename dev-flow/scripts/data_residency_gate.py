"""The data-residency gate, shared by update_meta.py (blocks) and show_state.py (warns).

Every project decides where its data lives before `scaffolded` — the point where modules start wiring
providers. `stack.data_residency` is "eu", "eu-sovereign" or "none"; null is undecided and does not pass.
That decision is the only thing this gate enforces: providers without an EU region are flagged in the
register by data_residency.py and never block a phase.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from data_residency import RESIDENCY, check  # noqa: E402


def applies(meta: dict) -> bool:
    return True


def verify(root: Path, meta: dict) -> tuple[bool, str]:
    residency = (meta.get("stack") or {}).get("data_residency")
    if residency not in RESIDENCY:
        return False, "stack.data_residency is undecided"
    try:
        res = check(root)
    except SystemExit as e:  # no meta.json
        return False, str(e)
    notes = [f"data residency: {residency}"] + [f"⚠ {w}" for w in res["warnings"]] + [f"⚑ {f}" for f in res["flags"]]
    return True, "\n".join(notes)


def remedy(root: Path) -> str:
    script = Path(__file__).resolve().parent / "data_residency.py"
    return (f"  Fix: python3 {script} decide {root} --eu-subjects yes|no --categories <list> "
            "--residency-obligations yes|no --avoid-cloud-act yes|no\n"
            "  The questions and what each answer implies: dev-flow/references/eu-data-sovereignty.md")
