"""The founder-intelligence gate, shared by update_meta.py (blocks) and show_state.py (reports).

On the founder path, the founder's approval of the Playbook is what authorises a PRD: research,
competitors, business model and MVP scope are settled first, and a person, not the agent, decides to
build. Left to prose, an agent told "go straight to the PRD" would skip that step, so it is checked
where phase moves: crossing into `prd_drafted`, through both doors.

Applies only once founder-intelligence has started (`meta.json#founder` exists) and only in `mode:
"new"`. A project without the field is on the direct path, and this gate does not concern it; on an
existing project (`mode: "existing"`) the PRD already exists and the result is `handoff.md` instead.
`founder-intelligence/scripts/founder.py` writes the block; this file only reads it and the Playbook.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

DECISIONS = ("pending", "approved", "approved_experiment", "revise", "stop", "bypassed")


def applies(meta: dict) -> bool:
    founder = meta.get("founder")
    if not founder:
        return False
    return not (isinstance(founder, dict) and founder.get("mode") == "existing")


def verify(root: Path, meta: dict) -> tuple[bool, str]:
    """(passes, explanation). Never raises."""
    if not applies(meta):
        return True, "founder gate not applicable: the founder path was not started, or this is an existing project"
    founder = meta["founder"]
    if not isinstance(founder, dict):
        return False, f"meta.json#founder is {type(founder).__name__}, not an object: it was edited by hand."
    decision = founder.get("decision")
    if decision not in DECISIONS:
        return False, f"meta.json#founder.decision is {decision!r}; expected one of {', '.join(DECISIONS)}."
    if not isinstance(founder.get("open_hypotheses", []), list):
        return False, "meta.json#founder.open_hypotheses is not a list: it was edited by hand."
    if decision == "bypassed":
        if not str(founder.get("reason") or "").strip():
            return False, "the founder path is marked bypassed without a reason."
        return True, f"founder path bypassed: {founder['reason']}"
    if decision not in ("approved", "approved_experiment"):
        return False, (f"the founder's decision is {decision!r}: the Playbook has not been approved, "
                       "and only the founder's explicit yes authorises a PRD.")
    if founder.get("approved_by_user") is not True or not str(founder.get("approval_quote") or "").strip():
        return False, "the approval has no founder quote: approved_by_user must be true, with the founder's own words."
    rel = founder.get("playbook")
    if not isinstance(rel, str) or not rel.strip():
        return False, "meta.json#founder.playbook is empty: the approval does not say which Playbook it covers."
    path = root / rel
    if not path.is_file():
        return False, f"the approved Playbook {rel} is not on disk: it was moved or deleted after approval."
    try:
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError as e:
        return False, f"the approved Playbook {rel} cannot be read ({e})."
    if digest != founder.get("playbook_sha256"):
        return False, (f"the Playbook {rel} changed after approval: the founder approved another version. "
                       "Show them the change and approve again.")
    label = "for a limited experiment" if decision == "approved_experiment" else "for development"
    return True, f"Playbook v{founder.get('version')} approved {label} on {founder.get('approved_at')}"


def remedy(root: Path) -> str:
    script = Path(__file__).resolve().parents[2] / "founder-intelligence" / "scripts" / "founder.py"
    run = f"python3 {script}" if script.exists() else "python3 founder-intelligence/scripts/founder.py"
    return (f"  Fix:     finish the Playbook with the founder, then {run} approve {root} --user-said \"<their words>\"\n"
            f"  Or:      {run} decide {root} revise|stop --reason \"...\"  — the founder's decision, recorded\n"
            f"  Opt out: {run} bypass {root} --reason \"...\" — back to the direct path, the reason is kept")
