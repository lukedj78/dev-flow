#!/usr/bin/env python3
"""scan_promotion.py — scan a project for promotion candidates per Rule of Three

Web (Next.js — app/ supports private `_components/` folders): walks the
codebase, finds every component under app/**/_components/, counts imports
across the codebase, and reports a table of promotion candidates.

Mobile (Expo Router — app/ is routes-only, NO `_components/` convention:
every file under app/ becomes a real route, so app/<route>/_components/
would create a ghost route): walks components/<feature>/*.tsx instead
(excluding components/{ui,theme,shared}, which are not promotion
candidates), and reports duplicate copies across feature folders as the
promotion signal. [VERIFY] the no-underscore-skip assumption against the
installed expo-router version — there is an open upstream issue requesting
an underscore-skip convention matching Next.js.

See references/colocation-rules.md for the full web-vs-mobile model.

Usage:
    python3 scan_promotion.py <project-root>

Reads .workflow/meta.json to detect framework (next/expo-rn/monorepo).
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

MOBILE_EXCLUDED_TOP_LEVEL = {"ui", "theme", "shared"}


def read_meta(root: Path) -> dict:
    p = root / ".workflow" / "meta.json"
    if not p.exists():
        return {"stack": {"framework": "next"}}
    return json.loads(p.read_text())


# ---------------------------------------------------------------------------
# Web (Next.js) — app/**/_components/
# ---------------------------------------------------------------------------


def find_components_web(scan_root: Path) -> list[tuple[str, Path]]:
    results = []
    for comp_dir in scan_root.glob("app/**/_components"):
        for tsx in comp_dir.glob("*.tsx"):
            results.append((tsx.stem, tsx))
    return results


def detect_level_web(file_path: Path, scan_root: Path) -> str:
    rel = file_path.relative_to(scan_root)
    parts = rel.parts
    if len(parts) >= 4 and parts[-2] == "_components":
        depth = len(parts) - 3
        if depth == 1 and parts[1].startswith("("):
            return "L1"
    return "L0"


def detect_route_group(file_path: Path, scan_root: Path) -> str | None:
    rel = file_path.relative_to(scan_root)
    for part in rel.parts:
        if part.startswith("(") and part.endswith(")"):
            return part
    return None


def suggest_promotion_web(comp_name: str, importers: set, scan_root: Path) -> str:
    n = len(importers)
    if n <= 1:
        return "OK — stays"
    if n == 2:
        return "Wait the 3rd use (tolerated duplicate)"
    groups = set()
    for imp in importers:
        g = detect_route_group(imp, scan_root)
        if g:
            groups.add(g)
    if len(groups) <= 1:
        if groups:
            return "Promote to L1 - app/" + list(groups)[0] + "/_components/" + comp_name + ".tsx"
        return "Promote to L1 (no specific group)"
    return "Promote to L2 - components/shared/<dominio>/" + comp_name + ".tsx"


# ---------------------------------------------------------------------------
# Mobile (Expo Router) — components/<feature>/*.tsx, no app/_components/
# ---------------------------------------------------------------------------


def find_components_mobile(scan_root: Path) -> list[tuple[str, Path]]:
    """Candidates are files directly under components/<feature>/, one level
    deep. components/ui, components/theme, components/shared are excluded:
    the first two are special (never promoted), the last is already L2."""
    results = []
    comp_root = scan_root / "components"
    if not comp_root.exists():
        return results
    for feature_dir in sorted(p for p in comp_root.iterdir() if p.is_dir()):
        if feature_dir.name in MOBILE_EXCLUDED_TOP_LEVEL:
            continue
        for tsx in feature_dir.rglob("*.tsx"):
            results.append((tsx.stem, tsx))
    return results


def detect_feature_mobile(file_path: Path, scan_root: Path) -> str | None:
    rel = file_path.relative_to(scan_root)
    parts = rel.parts
    if len(parts) >= 2 and parts[0] == "components":
        return parts[1]
    return None


# ---------------------------------------------------------------------------
# Shared: usage counting (import grep) works the same on both platforms
# ---------------------------------------------------------------------------


def count_imports(component_name: str, scan_root: Path) -> set:
    importers = set()
    pattern = re.compile(r'from\s+["\'][^"\']*' + re.escape(component_name) + r'["\']')
    candidates = list(scan_root.glob("app/**/*.tsx")) + list(scan_root.glob("components/**/*.tsx"))
    for tsx in candidates:
        try:
            text = tsx.read_text()
        except Exception:
            continue
        if pattern.search(text):
            importers.add(tsx)
    return importers


# ---------------------------------------------------------------------------
# Report printing, per platform
# ---------------------------------------------------------------------------


def scan_one_root_web(scan_root: Path, label: str) -> None:
    print()
    print("## Promotion candidates in " + label)
    print()
    components = find_components_web(scan_root)
    if not components:
        print("(no _components/ folders found)")
        return

    by_name: dict[str, list[Path]] = {}
    for name, path in components:
        by_name.setdefault(name, []).append(path)

    rows = []
    for name in sorted(by_name.keys()):
        paths = by_name[name]
        source = paths[0]
        importers = count_imports(name, scan_root)
        level = detect_level_web(source, scan_root)
        if len(paths) > 1:
            level = "L0 (x" + str(len(paths)) + " duplicates)"
        suggestion = suggest_promotion_web(name, importers, scan_root)
        rows.append((name, len(importers), level, suggestion))

    print("| Component | Usages | Current level | Suggestion |")
    print("|---|---|---|---|")
    for row in rows:
        print("| `" + row[0] + "` | " + str(row[1]) + " | " + row[2] + " | " + row[3] + " |")


def scan_one_root_mobile(scan_root: Path, label: str) -> None:
    print()
    print("## Promotion candidates in " + label + " (Expo Router — components/<feature>/, no app/_components/)")
    print()
    components = find_components_mobile(scan_root)
    if not components:
        print("(no components/<feature>/ files found)")
        return

    by_name: dict[str, list[Path]] = {}
    for name, path in components:
        by_name.setdefault(name, []).append(path)

    rows = []
    for name in sorted(by_name.keys()):
        paths = by_name[name]
        features = sorted({detect_feature_mobile(p, scan_root) for p in paths})
        importers = count_imports(name, scan_root)

        if len(features) > 1:
            level = "L0 (x" + str(len(features)) + " feature copies)"
            suggestion = "Promote to L2 - components/shared/<dominio>/" + name + ".tsx"
        else:
            level = "L0"
            if len(paths) > 1:
                suggestion = "Duplicate filenames within the same feature folder - likely a mistake, not a promotion candidate"
            elif len(importers) <= 1:
                suggestion = "OK — stays"
            elif len(importers) == 2:
                suggestion = "Wait the 3rd use (tolerated duplicate — copy into a 2nd feature's components/<feature>/ if needed there)"
            else:
                suggestion = "Promote to L2 - components/shared/<dominio>/" + name + ".tsx"

        rows.append((name, len(importers), level, suggestion))

    print("| Component | Usages | Current level | Suggestion |")
    print("|---|---|---|---|")
    for row in rows:
        print("| `" + row[0] + "` | " + str(row[1]) + " | " + row[2] + " | " + row[3] + " |")


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: scan_promotion.py <project-root>", file=sys.stderr)
        return 1
    project_root = Path(sys.argv[1]).resolve()
    if not project_root.exists():
        print("Project root not found: " + str(project_root), file=sys.stderr)
        return 1

    meta = read_meta(project_root)
    framework = meta.get("stack", {}).get("framework", "next")

    print("# Promotion scan - " + project_root.name)
    print()
    print("Framework: `" + framework + "`")

    if framework == "monorepo":
        web = project_root / "apps" / "web"
        mobile = project_root / "apps" / "mobile"
        if web.exists():
            scan_one_root_web(web, "apps/web (web)")
        if mobile.exists():
            scan_one_root_mobile(mobile, "apps/mobile (mobile)")
    elif framework == "expo-rn":
        scan_one_root_mobile(project_root, framework)
    else:
        scan_one_root_web(project_root, framework)

    print()
    print("## Next step")
    print()
    print("To promote: `python3 promote.py <project-root> <ComponentName> [--target L1|L2] [--domain <dominio>]`")
    return 0


if __name__ == "__main__":
    sys.exit(main())
