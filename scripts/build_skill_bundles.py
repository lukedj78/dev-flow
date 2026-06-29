#!/usr/bin/env python3
"""build_skill_bundles.py — (re)package every skill folder into dist/<name>.skill

A `.skill` file is a plain zip of the skill folder's CONTENTS (files at the zip
root, no folder prefix): SKILL.md + references/ + scripts/ + assets/. The evals/
directory and junk (.DS_Store, __pycache__, *.pyc) are excluded — they're not
needed at runtime.

Run from the repo root. Re-run whenever a SKILL.md / references / scripts / assets
change, so dist/ never drifts from source.

    python3 scripts/build_skill_bundles.py            # rebuild all
    python3 scripts/build_skill_bundles.py dev-flow   # rebuild one (or several)
"""
from __future__ import annotations

import sys
import zipfile
from pathlib import Path

# Folders at the repo root that are NOT skills (mirror build_skills_registry.py).
NOT_SKILLS = {"docs", "dist", "evals", "contract-package", "scripts", "bootstrap"}
# Per-skill subdirectories / files never included in a bundle.
EXCLUDE_DIRS = {"evals", "__pycache__", ".pytest_cache", "node_modules"}
EXCLUDE_NAMES = {".DS_Store"}
EXCLUDE_SUFFIXES = {".pyc"}


def skill_dirs(root: Path) -> list[Path]:
    out = []
    for skill_md in sorted(root.glob("*/SKILL.md")):
        name = skill_md.parent.name
        if name.startswith(".") or name in NOT_SKILLS:
            continue
        out.append(skill_md.parent)
    return out


def should_skip(rel_parts: tuple[str, ...], name: str) -> bool:
    if any(part in EXCLUDE_DIRS for part in rel_parts):
        return True
    if name in EXCLUDE_NAMES:
        return True
    if any(name.endswith(s) for s in EXCLUDE_SUFFIXES):
        return True
    return False


def build_one(skill_dir: Path, dist: Path) -> tuple[str, int]:
    out = dist / f"{skill_dir.name}.skill"
    files = []
    for path in sorted(skill_dir.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(skill_dir)
        if should_skip(rel.parts[:-1], rel.name):
            continue
        files.append((path, rel))
    # Deterministic write (sorted), normal deflate.
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zf:
        for path, rel in files:
            zf.write(path, arcname=str(rel))
    return skill_dir.name, len(files)


def main() -> int:
    root = Path(".")
    dist = root / "dist"
    dist.mkdir(exist_ok=True)

    wanted = set(sys.argv[1:])
    dirs = skill_dirs(root)
    if wanted:
        dirs = [d for d in dirs if d.name in wanted]
        missing = wanted - {d.name for d in dirs}
        for m in sorted(missing):
            sys.stderr.write(f"WARN: no skill folder '{m}' (skipped)\n")

    if not dirs:
        sys.stderr.write("No skill folders to package.\n")
        return 1

    total = 0
    for d in dirs:
        name, n = build_one(d, dist)
        total += 1
        print(f"  ✓ dist/{name}.skill  ({n} files)")
    print(f"✓ packaged {total} skill bundle(s) into dist/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
