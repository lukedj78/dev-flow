#!/usr/bin/env python3
"""promote.py — move a component up the colocation hierarchy + rewrite imports

Usage:
    python3 promote.py <project-root> <ComponentName> [--target L1|L2] [--domain <dominio>]

If --target is omitted, it's inferred from the current usage distribution
(same group → L1, multiple groups → L2).
If --domain is omitted for L2 promotion, the script asks the user.

Steps:
1. Find the component file(s) under app/**/_components/<Name>.tsx.
2. Decide target path.
3. git mv the file.
4. Find every .tsx/.ts in app/ and components/ that imports the OLD path,
   rewrite to NEW path.
5. Run npx tsc --noEmit.
6. Commit atomically.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path


def find_component_files(scan_root: Path, name: str) -> list:
    matches = []
    for tsx in scan_root.glob("app/**/_components/*.tsx"):
        if tsx.stem == name:
            matches.append(tsx)
    return matches


def detect_route_group_from_path(file_path: Path, scan_root: Path) -> str | None:
    rel = file_path.relative_to(scan_root)
    for part in rel.parts:
        if part.startswith("(") and part.endswith(")"):
            return part
    return None


def find_importers(comp_name: str, scan_root: Path) -> list:
    importers = []
    pattern = re.compile(r'from\s+["\'][^"\']*' + re.escape(comp_name) + r'["\']')
    candidates = list(scan_root.glob("app/**/*.tsx")) + \
                 list(scan_root.glob("app/**/*.ts")) + \
                 list(scan_root.glob("components/**/*.tsx")) + \
                 list(scan_root.glob("components/**/*.ts"))
    for f in candidates:
        try:
            if pattern.search(f.read_text()):
                importers.append(f)
        except Exception:
            continue
    return importers


def rewrite_imports(importers: list, old_paths: list, new_path: Path, scan_root: Path, comp_name: str) -> int:
    """Rewrite each importer's import statement to point at new_path."""
    new_rel = "@/" + str(new_path.relative_to(scan_root)).replace(".tsx", "").replace(os.sep, "/")
    count = 0
    for f in importers:
        try:
            text = f.read_text()
        except Exception:
            continue
        original = text
        # Replace any import from a path ending in /<comp_name>" or /<comp_name>'
        text = re.sub(
            r'from\s+(["\'])([^"\']*' + re.escape(comp_name) + r')(["\'])',
            r'from \1' + new_rel + r'\3',
            text,
        )
        if text != original:
            f.write_text(text)
            count += 1
    return count


def run(cmd: list, cwd: Path) -> int:
    return subprocess.run(cmd, cwd=cwd).returncode


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project_root", type=Path)
    parser.add_argument("component_name", type=str)
    parser.add_argument("--target", choices=["L1", "L2"], default=None)
    parser.add_argument("--domain", type=str, default=None,
                        help="Domain folder name (for L2 promotion, e.g. 'post')")
    parser.add_argument("--no-commit", action="store_true",
                        help="Don't auto-commit; leave changes staged")
    args = parser.parse_args()

    root = args.project_root.resolve()
    name = args.component_name

    # 1. Find source files
    matches = find_component_files(root, name)
    if not matches:
        print(f"Component {name!r} not found under app/**/_components/.", file=sys.stderr)
        return 1

    source = matches[0]
    if len(matches) > 1:
        print(f"Found {len(matches)} copies of {name}:")
        for m in matches:
            print("  " + str(m.relative_to(root)))
        print("Using the first as canonical. Others will be removed.")

    # 2. Determine target
    importers = find_importers(name, root)
    groups = set()
    for imp in importers:
        g = detect_route_group_from_path(imp, root)
        if g:
            groups.add(g)

    target_level = args.target
    if target_level is None:
        if len(groups) <= 1 and groups:
            target_level = "L1"
        else:
            target_level = "L2"

    if target_level == "L1":
        if not groups:
            print("L1 promotion requires a route group; none detected.", file=sys.stderr)
            return 1
        group = list(groups)[0]
        target_path = root / "app" / group / "_components" / (name + ".tsx")
    else:
        # L2
        domain = args.domain
        if domain is None:
            print(f"L2 promotion requires --domain. E.g. for {name} → 'post', 'user', 'billing'.", file=sys.stderr)
            return 1
        target_path = root / "components" / "shared" / domain / (name + ".tsx")

    if source == target_path:
        print(f"Already at target {target_path}. Nothing to do.")
        return 0

    # 3. Move + remove duplicates
    target_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(source), str(target_path))
    print(f"✓ moved {source.relative_to(root)} → {target_path.relative_to(root)}")

    duplicates_removed = 0
    for m in matches[1:]:
        if m.exists():
            m.unlink()
            duplicates_removed += 1
    if duplicates_removed:
        print(f"✓ removed {duplicates_removed} duplicate(s)")

    # 4. Rewrite imports
    old_paths = [str(m.relative_to(root)) for m in matches]
    rewritten = rewrite_imports(importers, old_paths, target_path, root, name)
    print(f"✓ rewrote {rewritten} import(s)")

    # 5. tsc verify
    if (root / "package.json").exists():
        rc = run(["npx", "tsc", "--noEmit"], cwd=root)
        if rc != 0:
            print(f"⚠ tsc reported errors. Inspect and fix; if unrecoverable, run: git restore .", file=sys.stderr)
            return rc

    # 6. Commit
    if not args.no_commit:
        run(["git", "add", "-A"], cwd=root)
        msg = f"refactor: promote {name} to {target_level}"
        run(["git", "commit", "-m", msg], cwd=root)
        print(f"✓ committed: {msg}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
