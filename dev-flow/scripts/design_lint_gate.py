"""The design-lint gate, shared by update_meta.py (blocks) and show_state.py (warns).

A dev-flow Next web app on a Tailwind UI (shadcn, base-ui, coss, and ui-sdk styled with
Tailwind) does not move into `scaffolded` until `@shadcn/lint` is wired, or the project has
recorded an explicit opt-out: `stack.design_lint = "none"` with `stack_config.design_lint_reason`.
`null` means undecided, and undecided does not pass.

An opt-out of the lint is not an opt-out of golden rule 3 (2026-11-27). It passes only with the
ESLint-free floor wired — design-md-to-app/scripts/check_handmade_ui.py in the project's `lint`,
and clean — or with its own reason, `stack_config.handmade_ui_check_reason`. Agentic Factory opted
out of the lint for a good reason (typescript-eslint refused TypeScript 7) and the opt-out took all
enforcement with it: six screens were built by hand beside the registry it had chosen. The same
project showed the second hole: this gate left ui-sdk out while setup_design_lint.py applied to
it, so a ui-sdk project was never asked at all.

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
# Mirrors setup_design_lint.py: ui-sdk applies when the project styles with Tailwind, its default. The gate
# reads meta alone, so — as setup_design_lint.applicability does without a root — it assumes Tailwind.
STYLE_AGNOSTIC_UIS = {"ui-sdk"}


def applies(meta: dict) -> bool:
    """Keep in sync with applicability() in setup_design_lint.py."""
    stack = meta.get("stack") or {}
    fw = stack.get("framework")
    if fw not in {"next", "monorepo"}:
        return False
    if fw == "monorepo" and ((stack.get("monorepo") or {}).get("topology") == "mobile-only"):
        return False
    ui = stack.get("ui") or ((stack.get("monorepo") or {}).get("web") or {}).get("ui")
    return not ui or ui in TAILWIND_UIS or ui in STYLE_AGNOSTIC_UIS


def floor_checker() -> Path | None:
    candidate = Path(__file__).resolve().parents[2] / "design-md-to-app" / "scripts" / "check_handmade_ui.py"
    return candidate if candidate.exists() else None


def floor(root: Path, meta: dict) -> tuple[bool, str]:
    """Golden rule 3 without the lint: check_handmade_ui.py wired into `lint` and clean, or a recorded reason."""
    reason = (meta.get("stack_config") or {}).get("handmade_ui_check_reason")
    if reason:
        return True, f"hand-made UI check opted out too: {reason}"
    script = floor_checker()
    if script is None:
        return False, ("the design lint is opted out and design-md-to-app/scripts/check_handmade_ui.py, which "
                       "replaces it, is not installed next to dev-flow")
    wired = subprocess.run([sys.executable, str(script), "--wired", str(root)],
                           capture_output=True, text=True, check=False)
    if wired.returncode != 0:
        return False, ("the design lint is opted out and nothing else enforces golden rule 3: "
                       "check_handmade_ui.py is not in the project's `lint` script")
    scan = subprocess.run([sys.executable, str(script), str(root)], capture_output=True, text=True, check=False)
    return scan.returncode == 0, (scan.stdout + scan.stderr).strip()


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
        if not reason:
            return False, 'stack.design_lint is "none" without stack_config.design_lint_reason'
        ok, why = floor(root, meta)
        return ok, f"design lint opted out: {reason}; {why}"
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
            '  Opt out: set stack.design_lint = "none" and stack_config.design_lint_reason in meta.json,\n'
            '           then wire the rule without ESLint: '
            f'python3 {floor_checker() or "design-md-to-app/scripts/check_handmade_ui.py"} --install {root}')
