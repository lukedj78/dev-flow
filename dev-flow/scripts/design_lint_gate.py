"""The design-lint gate, shared by update_meta.py (blocks) and show_state.py (warns).

A dev-flow Next web app on a Tailwind UI (shadcn, base-ui, coss) does not move into
`scaffolded` until `@shadcn/lint` is wired, or the project has recorded an explicit
opt-out: `stack.design_lint = "none"` with `stack_config.design_lint_reason`. `null`
means undecided, and undecided does not pass.

The verification itself lives with the skill that owns the lint —
design-md-to-app/scripts/setup_design_lint.py --check — so there is one definition of
"wired". This file only finds it, runs it, and decides applicability without it, so a
mobile or MUI project never needs design-md-to-app to be installed.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

TAILWIND_UIS = {"shadcn", "base-ui", "coss"}


def applies(meta: dict) -> bool:
    """Keep in sync with applicability() in setup_design_lint.py."""
    stack = meta.get("stack") or {}
    fw = stack.get("framework")
    if fw not in {"next", "monorepo"}:
        return False
    if fw == "monorepo" and ((stack.get("monorepo") or {}).get("topology") == "mobile-only"):
        return False
    ui = stack.get("ui") or ((stack.get("monorepo") or {}).get("web") or {}).get("ui")
    return not ui or ui in TAILWIND_UIS


def checker() -> Path | None:
    # skills sit side by side: ~/.claude/skills/<name>/, the repo root, or a plugin's skills/
    candidate = Path(__file__).resolve().parents[2] / "design-md-to-app" / "scripts" / "setup_design_lint.py"
    return candidate if candidate.exists() else None


def verify(root: Path, meta: dict) -> tuple[bool, str]:
    """(passes, explanation). Never raises."""
    if not applies(meta):
        return True, "design lint not applicable to this stack"
    stack = meta.get("stack") or {}
    if stack.get("design_lint") == "none":
        reason = (meta.get("stack_config") or {}).get("design_lint_reason")
        if reason:
            return True, f"design lint opted out: {reason}"
        return False, 'stack.design_lint is "none" without stack_config.design_lint_reason'
    script = checker()
    if script is None:
        return False, ("cannot verify the design lint: design-md-to-app/scripts/setup_design_lint.py "
                       "is not installed next to dev-flow")
    out = subprocess.run([sys.executable, str(script), str(root), "--check"],
                         capture_output=True, text=True, check=False)
    text = (out.stdout + out.stderr).strip()
    return out.returncode == 0, text


def remedy(root: Path) -> str:
    script = checker()
    run = f"python3 {script} {root}" if script else "python3 design-md-to-app/scripts/setup_design_lint.py <root>"
    return (f"  Fix:     {run}\n"
            '  Opt out: set stack.design_lint = "none" and stack_config.design_lint_reason in meta.json')
