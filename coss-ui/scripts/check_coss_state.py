#!/usr/bin/env python3
"""check_coss_state.py — decide Init vs Add mode for the coss-ui skill.

Inspects a project for Coss/UI install markers and reports which mode applies:
  - "add"  → Coss is already installed (a component/particle add is next).
  - "init" → Coss is not installed yet (scaffold + install is next).

The classification is a pure function over a markers dict (unit-testable); the
CLI builds the markers from a project root and prints a small JSON report.

Markers that mean "Coss is installed":
  - the `@coss` namespace is present in components.json#registries, OR
  - `@base-ui/react` is a dependency (Coss is built on Base UI), OR
  - globals.css carries a Coss token block (`@coss` reference or the sidebar
    variables Coss ships).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path


def classify(markers: dict) -> str:
    """add if any Coss marker is present, else init."""
    if (markers.get("has_coss_registry")
            or markers.get("has_base_ui_dep")
            or markers.get("has_coss_tokens")):
        return "add"
    return "init"


def _read_json(p: Path) -> dict:
    try:
        return json.loads(p.read_text())
    except (OSError, ValueError):
        return {}


def read_markers(root: Path) -> dict:
    pkg = _read_json(root / "package.json")
    deps = {}
    deps.update(pkg.get("dependencies", {}) or {})
    deps.update(pkg.get("devDependencies", {}) or {})

    components = _read_json(root / "components.json")
    registries = components.get("registries", {}) or {}

    globals_css = ""
    for candidate in ("app/globals.css", "src/app/globals.css",
                      "apps/web/app/globals.css", "styles/globals.css"):
        f = root / candidate
        if f.exists():
            try:
                globals_css = f.read_text()
            except OSError:
                globals_css = ""
            break

    return {
        "has_app": (root / "package.json").exists(),
        "has_coss_registry": any(k == "@coss" or "coss" in str(v).lower()
                                 for k, v in registries.items()),
        "has_base_ui_dep": "@base-ui/react" in deps,
        "has_coss_tokens": "@coss" in globals_css,
    }


def main() -> None:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else ".")
    markers = read_markers(root)
    report = {"mode": classify(markers), **markers}
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
