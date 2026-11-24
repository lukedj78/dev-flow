"""The package-boundaries gate, used by update_meta.py at the crossing into `scaffolded`.

A monorepo that declares its boundaries (`boundaries.json` at the root — topology "web-agent-inapp",
or any project that adopted it) does not reach `scaffolded` while they are violated: the boundaries
are the reason that topology exists, and a scaffold that already breaks them only gets worse.

The check is monorepo-bootstrap's own `check_boundaries.py`, never the project's copy: the project's
file is code the repository controls, and running it here would let a cloned repo run anything at
set-phase — or pass the gate with `exit 0`. The project's copy is what its `pnpm lint` and CI run;
`show_state`-style drift between the two is the project's to fix. A project without
`boundaries.json` is not affected.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def _topology(meta: object) -> object:
    stack = meta.get("stack") if isinstance(meta, dict) else None
    mono = stack.get("monorepo") if isinstance(stack, dict) else None
    return mono.get("topology") if isinstance(mono, dict) else None


def applies(root: Path, meta: dict) -> bool:
    return (root / "boundaries.json").is_file() or _topology(meta) == "web-agent-inapp"


def checker() -> Path | None:
    """The skill's copy only. Never the project's: see the module docstring."""
    candidate = Path(__file__).resolve().parents[2] / "monorepo-bootstrap" / "scripts" / "check_boundaries.py"
    return candidate if candidate.is_file() else None


def verify(root: Path, meta: dict) -> tuple[bool, str]:
    """(passes, explanation). Never raises."""
    if not applies(root, meta):
        return True, "no boundaries.json — package boundaries not declared"
    if not (root / "boundaries.json").is_file():
        return False, "topology web-agent-inapp but no boundaries.json at the root"
    script = checker()
    if not script:
        return False, "monorepo-bootstrap/scripts/check_boundaries.py not found — reinstall the skills"
    try:
        r = subprocess.run([sys.executable, str(script), str(root)], capture_output=True, text=True, timeout=120)
    except (OSError, subprocess.SubprocessError) as exc:
        return False, f"check_boundaries.py could not run: {exc}"
    if r.returncode == 0:
        return True, "boundaries clean"
    out = (r.stdout or "")[:20000]
    lines = [l for l in out.splitlines() if l.startswith("BOUNDARY:")] or out.splitlines() or [(r.stderr or "")[:2000].strip()]
    return False, "\n".join(lines[:20])


def remedy(root: Path) -> str:
    return ("  Fix the imports or dependencies above, or change boundaries.json first if the rule is what should change\n"
            "  (monorepo-bootstrap/references/boundaries.md). Check: python3 scripts/check_boundaries.py .")
