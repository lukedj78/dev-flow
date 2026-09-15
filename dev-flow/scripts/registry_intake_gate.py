"""The registry-intake gate, shared by update_meta.py (blocks) and show_state.py (warns).

A project that can pull third-party source through a shadcn-format registry — a Next web app
on a Tailwind UI (the same set the design lint covers) or an eve agent — does not move into
`scaffolded` until registry intake is enforced: `registry-lock.json`, the PreToolUse hook, and
nothing installed around them. The explicit opt-out is `stack.registry_intake = "none"` with
`stack_config.registry_intake_reason`. `null` means undecided, and undecided does not pass.

The verification lives with the skill that owns it —
registry-intake/scripts/registry_intake.py check — so there is one definition of "enforced".
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from design_lint_gate import applies as web_applies  # noqa: E402


def applies(meta: dict) -> bool:
    stack = meta.get("stack") or {}
    return web_applies(meta) or stack.get("agent") == "eve" or stack.get("framework") == "agent"


def checker() -> Path | None:
    candidate = Path(__file__).resolve().parents[2] / "registry-intake" / "scripts" / "registry_intake.py"
    return candidate if candidate.exists() else None


def verify(root: Path, meta: dict) -> tuple[bool, str]:
    """(passes, explanation). Never raises."""
    if not applies(meta):
        return True, "registry intake not applicable to this stack"
    stack = meta.get("stack") or {}
    if stack.get("registry_intake") == "none":
        reason = (meta.get("stack_config") or {}).get("registry_intake_reason")
        if reason:
            return True, f"registry intake opted out: {reason}"
        return False, 'stack.registry_intake is "none" without stack_config.registry_intake_reason'
    script = checker()
    if script is None:
        return False, ("cannot verify registry intake: registry-intake/scripts/registry_intake.py "
                       "is not installed next to dev-flow")
    out = subprocess.run([sys.executable, str(script), "check", str(root)],
                         capture_output=True, text=True, check=False)
    return out.returncode == 0, (out.stdout + out.stderr).strip()


def remedy(root: Path) -> str:
    script = checker()
    run = f"python3 {script} setup {root}" if script else "python3 registry-intake/scripts/registry_intake.py setup <root>"
    return (f"  Fix:     {run}\n"
            '  Opt out: set stack.registry_intake = "none" and stack_config.registry_intake_reason in meta.json')
