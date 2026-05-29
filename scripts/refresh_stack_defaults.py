#!/usr/bin/env python3
"""refresh_stack_defaults.py — refresh the pinned RN/Expo versions

Queries npm for the latest stable version of every package listed in
rn-fundamentals/references/stack-defaults.md, prints a drift report, and
(with --apply) rewrites both rn-fundamentals/ and rn-bootstrap/
stack-defaults.md to match.

Usage:
    ./scripts/refresh-stack-defaults.sh                   # dry-run, print diff
    ./scripts/refresh-stack-defaults.sh --apply           # rewrite the files

Always run from the repo root.
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path
from datetime import datetime, timezone

# Packages to track. Order matches the table column order in stack-defaults.md.
PACKAGES = [
    "expo",
    "react-native",
    "react",
    "typescript",
    "expo-router",
    "nativewind",
    "tailwindcss",
    "zustand",
    "@tanstack/react-query",
    "react-native-reanimated",
    "react-native-gesture-handler",
    "react-native-safe-area-context",
    "expo-image",
    "@shopify/flash-list",
]

# Packages we deliberately pin BELOW latest. The script honors these — it will
# warn if the major has advanced but won't auto-update.
PINNED_BELOW = {
    "tailwindcss": {"max_major": 3, "reason": "NativeWind v4 incompatible with TW 4"},
}

TARGETS = [
    "rn-fundamentals/references/stack-defaults.md",
    "rn-bootstrap/references/stack-defaults.md",
]

ROW_RE = re.compile(r"^\| `(?P<pkg>[^`]+)` *\| `(?P<ver>[^`]+)`")


def npm_view(pkg: str) -> str | None:
    try:
        result = subprocess.run(
            ["npm", "view", pkg, "version"],
            capture_output=True, text=True, timeout=20,
        )
        if result.returncode != 0:
            return None
        return result.stdout.strip().splitlines()[-1].strip()
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return None


def parse_current(path: Path) -> dict[str, str]:
    """Return {package: version-with-prefix} parsed from the stack-defaults table."""
    current = {}
    if not path.exists():
        return current
    for line in path.read_text().splitlines():
        m = ROW_RE.match(line)
        if m:
            current[m.group("pkg")] = m.group("ver")
    return current


def strip_prefix(ver: str) -> tuple[str, str]:
    """Return (prefix, bare-version). Prefix is '^', '~', or ''."""
    if ver.startswith("^") or ver.startswith("~"):
        return ver[0], ver[1:]
    return "", ver


def major_of(ver: str) -> int:
    try:
        return int(ver.split(".", 1)[0])
    except (ValueError, IndexError):
        return -1


def main() -> int:
    apply = "--apply" in sys.argv[1:]

    print("→ Querying npm for latest stable versions…\n")
    print(f"{'PACKAGE':<35} {'LATEST':>15}")
    print(f"{'-' * 35} {'-' * 15:>15}")

    latest: dict[str, str | None] = {}
    for pkg in PACKAGES:
        v = npm_view(pkg)
        latest[pkg] = v
        print(f"{pkg:<35} {v or '?':>15}")

    # Parse current state of the fundamentals file (canonical source)
    fundamentals_path = Path("rn-fundamentals/references/stack-defaults.md")
    if not fundamentals_path.exists():
        print(f"\nERROR: {fundamentals_path} not found. Run from the repo root.")
        return 1
    current = parse_current(fundamentals_path)

    print(f"\n→ Comparing against {fundamentals_path}…\n")
    print(f"{'PACKAGE':<35} {'CURRENT':>15} {'LATEST':>15}  {'DIFF'}")
    print(f"{'-' * 35} {'-' * 15:>15} {'-' * 15:>15}  {'----'}")

    changes: list[tuple[str, str, str, str]] = []  # (pkg, current, new_pinned, prefix)
    for pkg in PACKAGES:
        curr = current.get(pkg, "?")
        new = latest.get(pkg)
        if curr == "?" or new is None:
            print(f"{pkg:<35} {curr:>15} {new or '?':>15}  ? (skip)")
            continue
        prefix, bare = strip_prefix(curr)

        # Honor PINNED_BELOW
        pin = PINNED_BELOW.get(pkg)
        if pin and major_of(new) > pin["max_major"]:
            print(f"{pkg:<35} {curr:>15} {new:>15}  ⚠ pinned (max major {pin['max_major']}: {pin['reason']})")
            continue

        if bare == new:
            print(f"{pkg:<35} {curr:>15} {new:>15}  ✓")
        else:
            print(f"{pkg:<35} {curr:>15} {new:>15}  ✗ drift")
            changes.append((pkg, curr, new, prefix))

    print()
    if not changes:
        print("→ All versions current. No changes needed.")
        return 0

    print(f"→ {len(changes)} package(s) drifted.")

    if not apply:
        print("\nDry-run mode. To apply changes, re-run with --apply.")
        return 0

    print("\n→ Rewriting stack-defaults.md files…")
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    snapshot_re = re.compile(r"^> Snapshot date: \d{4}-\d{2}-\d{2}\.")

    for target_str in TARGETS:
        target = Path(target_str)
        if not target.exists():
            print(f"  skip: {target} (not found)")
            continue
        text = target.read_text()
        for pkg, curr, new, prefix in changes:
            text = text.replace(f"`{curr}`", f"`{prefix}{new}`")
        text = snapshot_re.sub(f"> Snapshot date: {today}.", text)
        target.write_text(text)
        print(f"  ✓ {target}")

    print(
        "\n→ Done. Review the diff with: git diff rn-fundamentals/ rn-bootstrap/\n"
        "  If happy, commit with:\n"
        "    git add rn-fundamentals/references/stack-defaults.md "
        "rn-bootstrap/references/stack-defaults.md\n"
        '    git commit -m "chore: refresh RN stack-defaults to current npm latest"'
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
