"""The wireframe-canvas gate, shared by update_meta.py (blocks) and show_state.py (warns).

No code is scaffolded before every screen has been drawn and the user has approved it: a screen
inventory mapped to the PRD's user stories, and one desktop (1440) plus one phone (390) artboard per
screen on a claude.ai Design canvas. `meta.json#wireframes` records it; the explicit opt-out is
`wireframes.skipped = true` with `wireframes.reason`. A missing block is undecided and does not pass.

Applies to every stack with a UI — everything except the agent-only topology (`framework: "agent"`),
which has no screens to draw. The checks are on meta.json and one file on disk, so this gate needs
no other skill installed; `wireframe-canvas/scripts/wireframes.py` writes the block.
"""

from __future__ import annotations

from pathlib import Path


def applies(meta: dict) -> bool:
    return (meta.get("stack") or {}).get("framework") != "agent"


def verify(root: Path, meta: dict) -> tuple[bool, str]:
    """(passes, explanation). Never raises."""
    if not applies(meta):
        return True, "wireframes not applicable: agent-only project, no screens"
    wf = meta.get("wireframes")
    if not isinstance(wf, dict) or not wf:
        return False, "meta.json#wireframes is missing: no screen has been drawn and approved yet."
    if wf.get("skipped") is True:
        if not str(wf.get("reason") or "").strip():
            return False, "the wireframe canvas is marked skipped without a reason."
        return True, f"wireframes skipped: {wf['reason']}"
    problems = []
    if not str(wf.get("canvas_url") or "").strip():
        problems.append("wireframes.canvas_url is empty: link the Design canvas the user reviewed.")
    inventory = str(wf.get("inventory") or "").strip()
    if not inventory:
        problems.append("wireframes.inventory is empty: the screen inventory is the list the canvas is checked against.")
    elif not (root / inventory).is_file():
        problems.append(f"wireframes.inventory points at {inventory}, which does not exist.")
    screens, artboards = wf.get("screens"), wf.get("artboards")
    if not isinstance(screens, int) or screens < 1:
        problems.append(f"wireframes.screens is {screens!r}; it must count the screens in the inventory.")
    elif not isinstance(artboards, int) or artboards < 2 * screens:
        problems.append(f"wireframes.artboards is {artboards!r} for {screens} screens: "
                        "every screen needs a desktop and a phone artboard.")
    if wf.get("approved_by_user") is not True or not str(wf.get("approved_at") or "").strip():
        problems.append("the canvas is not approved: approved_by_user must be true, with approved_at, "
                        "and only the user's own explicit yes sets it.")
    if problems:
        return False, "\n".join(problems)
    return True, f"wireframes approved {wf['approved_at']}: {screens} screens, {artboards} artboards"


def remedy(root: Path) -> str:
    script = Path(__file__).resolve().parents[2] / "wireframe-canvas" / "scripts" / "wireframes.py"
    run = f"python3 {script}" if script.exists() else "python3 wireframe-canvas/scripts/wireframes.py"
    return (f"  Fix:     run the wireframe-canvas skill, then {run} approve {root} --canvas-url <url>\n"
            f"  Opt out: {run} skip {root} --reason \"...\" — the reason is kept in meta.json")
