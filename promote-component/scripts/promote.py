#!/usr/bin/env python3
"""promote.py — move a component up the colocation hierarchy + rewrite imports

Usage:
    python3 promote.py <project-root> <ComponentName> [--target L1|L2] [--domain <dominio>]

Reads .workflow/meta.json#stack.framework to pick the right source/target
convention:

- Web (Next.js, "next"): components live under app/**/_components/; L1 is
  app/(group)/_components/, L2 is components/shared/<dominio>/.
- Mobile (Expo Router, "expo-rn"): app/ is routes-only — Expo Router has no
  private-folder convention (every file under app/ becomes a real route,
  unlike Next.js's `_`-prefix skip), so components live under
  components/<feature>/ instead. There's no separate physical L1 target on
  mobile (see references/colocation-rules.md): the "L1" outcome is a dedupe
  back into a single components/<feature>/ file, and L2 is
  components/shared/<dominio>/ (same path shape as web).

If --target is omitted, it's inferred from the current usage distribution
(same group/feature → dedupe or L1, multiple groups/features → L2).
If --domain is omitted for L2 promotion, the script asks the user.

Steps (both platforms):
1. Find the component file(s) at the platform's L0 root.
2. Decide target path.
3. git mv (or dedupe-in-place, mobile "L1") the file.
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

MOBILE_EXCLUDED_TOP_LEVEL = {"ui", "theme", "shared"}


def read_meta(root: Path) -> dict:
    p = root / ".workflow" / "meta.json"
    if not p.exists():
        return {"stack": {"framework": "next"}}
    try:
        return json.loads(p.read_text())
    except Exception:
        return {"stack": {"framework": "next"}}


# ---------------------------------------------------------------------------
# Shared helpers (import scanning/rewriting is identical on both platforms)
# ---------------------------------------------------------------------------


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


def verify_and_commit(root: Path, target_level: str, name: str, no_commit: bool) -> int:
    if (root / "package.json").exists():
        rc = run(["npx", "tsc", "--noEmit"], cwd=root)
        if rc != 0:
            print("⚠ tsc reported errors. Inspect and fix; if unrecoverable, run: git restore .", file=sys.stderr)
            return rc

    if not no_commit:
        run(["git", "add", "-A"], cwd=root)
        msg = f"refactor: promote {name} to {target_level}"
        run(["git", "commit", "-m", msg], cwd=root)
        print(f"✓ committed: {msg}")
    return 0


# ---------------------------------------------------------------------------
# Web (Next.js) — app/**/_components/
# ---------------------------------------------------------------------------


def find_component_files_web(scan_root: Path, name: str) -> list:
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


def promote_web(root: Path, name: str, target_arg: str | None, domain: str | None, no_commit: bool) -> int:
    matches = find_component_files_web(root, name)
    if not matches:
        print(f"Component {name!r} not found under app/**/_components/.", file=sys.stderr)
        return 1

    source = matches[0]
    if len(matches) > 1:
        print(f"Found {len(matches)} copies of {name}:")
        for m in matches:
            print("  " + str(m.relative_to(root)))
        print("Using the first as canonical. Others will be removed.")

    importers = find_importers(name, root)
    groups = set()
    for imp in importers:
        g = detect_route_group_from_path(imp, root)
        if g:
            groups.add(g)

    target_level = target_arg
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
        if domain is None:
            print(f"L2 promotion requires --domain. E.g. for {name} → 'post', 'user', 'billing'.", file=sys.stderr)
            return 1
        target_path = root / "components" / "shared" / domain / (name + ".tsx")

    if source == target_path:
        print(f"Already at target {target_path}. Nothing to do.")
        return 0

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

    rewritten = rewrite_imports(importers, [str(m.relative_to(root)) for m in matches], target_path, root, name)
    print(f"✓ rewrote {rewritten} import(s)")

    return verify_and_commit(root, target_level, name, no_commit)


# ---------------------------------------------------------------------------
# Mobile (Expo Router) — components/<feature>/*.tsx, no app/_components/
# ---------------------------------------------------------------------------


def find_component_files_mobile(scan_root: Path, name: str) -> list:
    """Search components/<feature>/<Name>.tsx across all feature folders,
    excluding components/{ui,theme,shared} (special / already-L2)."""
    matches = []
    comp_root = scan_root / "components"
    if not comp_root.exists():
        return matches
    for feature_dir in sorted(p for p in comp_root.iterdir() if p.is_dir()):
        if feature_dir.name in MOBILE_EXCLUDED_TOP_LEVEL:
            continue
        for tsx in feature_dir.rglob(name + ".tsx"):
            matches.append(tsx)
    return matches


def promote_mobile(root: Path, name: str, target_arg: str | None, domain: str | None, no_commit: bool) -> int:
    matches = find_component_files_mobile(root, name)
    if not matches:
        print(
            f"Component {name!r} not found under components/<feature>/ "
            "(excluding components/{ui,theme,shared}). Note: Expo Router has no "
            "app/<route>/_components/ convention — mobile components never live under app/.",
            file=sys.stderr,
        )
        return 1

    source = matches[0]
    if len(matches) > 1:
        print(f"Found {len(matches)} copies of {name} across feature folders:")
        for m in matches:
            print("  " + str(m.relative_to(root)))
        print("Using the first as canonical. Others will be removed.")

    features = sorted({m.relative_to(root).parts[1] for m in matches})

    target_level = target_arg
    if target_level is None:
        target_level = "L2" if len(features) >= 2 else "L1"

    if target_level == "L2":
        if domain is None:
            print(f"L2 promotion requires --domain. E.g. for {name} → 'post', 'user', 'billing'.", file=sys.stderr)
            return 1
        target_path = root / "components" / "shared" / domain / (name + ".tsx")
    else:
        # Mobile "L1" has no separate physical target — it's a dedupe back
        # into the single canonical components/<feature>/ file (see
        # references/colocation-rules.md for why L0/L1 collapse on mobile).
        target_path = source

    if source == target_path and len(matches) == 1:
        print(f"Already at target {target_path}. Nothing to do.")
        return 0

    if target_path != source:
        target_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(source), str(target_path))
        print(f"✓ moved {source.relative_to(root)} → {target_path.relative_to(root)}")
    elif target_level == "L1":
        print(f"✓ keeping canonical copy at {target_path.relative_to(root)} (mobile L1 = dedupe, not a move)")

    importers = find_importers(name, root)
    duplicates_removed = 0
    for m in matches[1:]:
        if m.exists() and m != target_path:
            m.unlink()
            duplicates_removed += 1
    if duplicates_removed:
        print(f"✓ removed {duplicates_removed} duplicate(s)")

    old_paths = [str(m.relative_to(root)) for m in matches]
    rewritten = rewrite_imports(importers, old_paths, target_path, root, name)
    print(f"✓ rewrote {rewritten} import(s)")

    return verify_and_commit(root, target_level, name, no_commit)


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

    meta = read_meta(root)
    framework = meta.get("stack", {}).get("framework", "next")

    if framework == "expo-rn":
        return promote_mobile(root, name, args.target, args.domain, args.no_commit)
    # "monorepo" is not resolved to a specific apps/{web,mobile} root here —
    # the caller is expected to pass the concrete app root (e.g.
    # <project-root>/apps/mobile) in that case. Anything else defaults to
    # the web convention (matches scan_promotion.py's default).
    return promote_web(root, name, args.target, args.domain, args.no_commit)


if __name__ == "__main__":
    sys.exit(main())
