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
    python3 scripts/build_skill_bundles.py --check    # verify dist/ against the sources, write nothing

`--check` exists because only the pre-commit hook kept the bundles in step, and the hook exists only in
clones that installed it. On 2026-10-03 twelve of fifty-one were wrong, dev-flow's short fifteen files.
It compares CONTENT, entry by entry, not zip bytes: a zip stores file times, so an identical rebuild
never compares equal byte for byte.
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


def bundle_files(skill_dir: Path) -> list[tuple[Path, Path]]:
    """(path on disk, path inside the bundle) for every file that goes into the skill's bundle."""
    files = []
    for path in sorted(skill_dir.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(skill_dir)
        if should_skip(rel.parts[:-1], rel.name):
            continue
        files.append((path, rel))
    return files


def check(root: Path) -> list[str]:
    """Every way dist/ can differ from the skill folders; empty means in step."""
    problems = []
    dirs = skill_dirs(root)
    names = {d.name for d in dirs}
    for stray in sorted((root / "dist").glob("*.skill")):
        if stray.stem not in names:
            problems.append(f"dist/{stray.name}: no skill folder '{stray.stem}' any more — delete the bundle")
    for d in dirs:
        bundle = root / "dist" / f"{d.name}.skill"
        if not bundle.exists():
            problems.append(f"dist/{d.name}.skill: missing")
            continue
        want = {str(rel): path.read_bytes() for path, rel in bundle_files(d)}
        with zipfile.ZipFile(bundle) as zf:
            have = {n: zf.read(n) for n in zf.namelist() if not n.endswith("/")}
        for n in sorted(want.keys() - have.keys()):
            problems.append(f"dist/{d.name}.skill: lacks {n}")
        for n in sorted(have.keys() - want.keys()):
            problems.append(f"dist/{d.name}.skill: has {n}, which the source no longer does")
        for n in sorted(want.keys() & have.keys()):
            if want[n] != have[n]:
                problems.append(f"dist/{d.name}.skill: {n} differs from the source")
    return problems


def build_one(skill_dir: Path, dist: Path) -> tuple[str, int]:
    out = dist / f"{skill_dir.name}.skill"
    files = bundle_files(skill_dir)
    # Deterministic write (sorted), normal deflate.
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zf:
        for path, rel in files:
            zf.write(path, arcname=str(rel))
    return skill_dir.name, len(files)


def main() -> int:
    root = Path(".")
    dist = root / "dist"
    dist.mkdir(exist_ok=True)

    if sys.argv[1:] == ["--check"]:
        problems = check(root)
        for p in problems:
            print(f"  ✗ {p}")
        if problems:
            print(f"\n{len(problems)} difference(s). Rebuild with: python3 scripts/build_skill_bundles.py "
                  "<skill> (or no argument for all), then commit dist/.")
            return 1
        print(f"✓ dist/ matches the sources ({len(skill_dirs(root))} bundles)")
        return 0

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
