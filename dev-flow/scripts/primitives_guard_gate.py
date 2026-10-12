"""The primitives-guard gate, shared by update_meta.py (blocks) and show_state.py (warns).

Golden rule 3 (contracts.md), «the primitive renders the design»: on a dev-flow Next web app with a
Tailwind UI (shadcn, base-ui, coss) every piece of UI is a primitive from components/ui. Two things enforce it, and this gate
wants both:

  - the lint rule `design/no-handmade-ui` at "error" in the design-system preset (the whole tree, in CI)
  - the write-time guard: Claude Code hooks in `.claude/settings.json` running `scripts/guard/`, which
    refuse a Write/Edit that adds hand-made UI and stop an agent that added it through the shell

recorded as `stack.primitives_guard = "installed"`, or an explicit opt-out: `"none"` with
`stack_config.primitives_guard_reason`. Why it exists: smart-travel, 2026-10-12 — 238 hand-made elements
built in three days behind a green lint, because a raw <button> with Tailwind classes imports nothing.

The verification lives with the skill that installs it — design-md-to-app/scripts/setup_primitives_guard.py
--check, plus the rule check in setup_design_lint.py --check. Expo / React Native is not covered yet: the same
guard over NativeWind and the RN component set is an open gap (contracts.md, golden rule 3).
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import design_lint_gate


def applies(meta: dict) -> bool:
    return design_lint_gate.applies(meta)


def scripts_dir() -> Path | None:
    d = Path(__file__).resolve().parents[2] / "design-md-to-app" / "scripts"
    return d if (d / "setup_primitives_guard.py").exists() else None


def verify(root: Path, meta: dict) -> tuple[bool, str]:
    """(passes, explanation). Never raises."""
    if not applies(meta):
        return True, "primitives guard not applicable to this stack"
    stack = meta.get("stack") or {}
    if stack.get("primitives_guard") == "none":
        reason = (meta.get("stack_config") or {}).get("primitives_guard_reason")
        if reason:
            return True, f"primitives guard opted out: {reason}"
        return False, 'stack.primitives_guard is "none" without stack_config.primitives_guard_reason'
    # the guard runs the design lint's rules: a reasoned opt-out of the design lint (no Tailwind classes to
    # check) takes the guard with it. An opt-out without a reason is design_lint_gate's refusal to make.
    if stack.get("design_lint") == "none" and (meta.get("stack_config") or {}).get("design_lint_reason"):
        return True, f"primitives guard off with the design lint: {meta['stack_config']['design_lint_reason']}"
    d = scripts_dir()
    if d is None:
        return False, ("cannot verify the primitives guard: design-md-to-app/scripts/setup_primitives_guard.py "
                       "is not installed next to dev-flow")
    lines, ok = [], True
    out = subprocess.run([sys.executable, str(d / "setup_primitives_guard.py"), str(root), "--check"],
                         capture_output=True, text=True, check=False)
    ok &= out.returncode == 0
    lines.append((out.stdout + out.stderr).strip())
    # the rule itself: a guard over a preset without design/no-handmade-ui checks nothing
    sys.path.insert(0, str(d))
    try:
        import setup_design_lint as sdl
        for topo in sdl.detect(root):
            text = topo["preset"].read_text() if topo["preset"].exists() else ""
            if not sdl.HANDMADE_ERROR.search(text):
                ok = False
                lines.append(f"✗ {topo['preset'].relative_to(root)} has no design/no-handmade-ui at \"error\"")
    except Exception as e:  # noqa: BLE001 — a gate reports, never crashes the caller
        ok = False
        lines.append(f"✗ cannot read the design-system preset: {e}")
    return ok, "\n".join(l for l in lines if l)


def remedy(root: Path) -> str:
    d = scripts_dir()
    run = (f"python3 {d / 'setup_design_lint.py'} {root}" if d
           else "python3 design-md-to-app/scripts/setup_design_lint.py <root>")
    return (f"  Fix (one command — lint rule + guard + AGENTS.md section): {run}\n"
            '  Opt out: set stack.primitives_guard = "none" and stack_config.primitives_guard_reason in meta.json')
