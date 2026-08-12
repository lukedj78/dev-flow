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

# --- npm `latest` is the WRONG authority for an Expo project -----------------
#
# Expo SDK ships `bundledNativeModules.json`: the version of each native module
# that `expo install` resolves for that SDK. It is what an Expo app actually
# gets, and it lags npm `latest` on purpose — a native module has to match the
# SDK's compiled runtime.
#
# Checking these against npm produced a table where EVERY Expo-managed package
# was wrong, including `react-native-gesture-handler` pinned a whole major above
# what SDK 57 bundles (^3.1.0 vs ~2.32.0). Following npm here does not give you
# a newer project, it gives you one `expo install` disagrees with.
#
# So: for packages Expo bundles, the SDK is the source of truth. npm `latest`
# still governs the rest (typescript, zustand, @tanstack/react-query…), which
# Expo does not manage.
#
# Fetched via `npm pack` (the registry tarball), NOT unpkg.com: the manifest
# ships inside the package itself, and unpkg is a third-party CDN that some
# network policies block outright (it failed silently here — a 403 on the
# CONNECT tunnel — which used to make this function return {} and the caller
# fall back to plain `npm view` for EVERY package, Expo-managed or not. That
# fallback is the exact bug this script exists to prevent: silently
# recommending react-native-gesture-handler ^3.1.0 against an SDK that bundles
# ~2.32.0. `npm pack` hits registry.npmjs.org, which every environment this
# script has run in so far allows.
def expo_bundled(expo_version: str) -> dict[str, str]:
    """{package: version-range} that `expo install` resolves for this SDK."""
    import json
    import tarfile
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        result = subprocess.run(
            ["npm", "pack", f"expo@{expo_version}", "--silent", "--pack-destination", tmp],
            capture_output=True, text=True, timeout=60,
        )
        if result.returncode != 0:
            sys.stderr.write(f"! npm pack expo@{expo_version} failed: {result.stderr.strip()}\n")
            return {}
        tgz_name = result.stdout.strip().splitlines()[-1].strip()
        try:
            with tarfile.open(Path(tmp) / tgz_name) as tf:
                member = tf.extractfile("package/bundledNativeModules.json")
                if member is None:
                    sys.stderr.write(f"! {tgz_name} has no bundledNativeModules.json\n")
                    return {}
                return json.load(member)
        except (KeyError, OSError, json.JSONDecodeError) as e:
            sys.stderr.write(f"! could not read bundledNativeModules.json from {tgz_name}: {e}\n")
            return {}


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

    print("→ Resolving target versions…\n")

    # Expo first: its SDK version selects the bundled-native-module manifest
    # that governs every package Expo manages.
    expo_latest = npm_view("expo")
    bundled = expo_bundled(expo_latest) if expo_latest else {}
    if bundled:
        print(f"  authority for Expo-managed packages: expo@{expo_latest} bundledNativeModules\n")
    else:
        # Do NOT fall back to `npm view` for Expo-managed packages here — that
        # fallback used to run silently and recommend exactly the wrong-major
        # drift this script exists to catch (react-native-gesture-handler
        # ^3.1.0 against an SDK that bundles ~2.32.0). A stale report is worse
        # than no report.
        print("ERROR: could not read expo's bundledNativeModules.json — refusing to "
              "guess Expo-managed versions from plain npm `latest`. Re-run when "
              "the registry is reachable.")
        return 1

    print(f"{'PACKAGE':<35} {'TARGET':>15}  SOURCE")
    print(f"{'-' * 35} {'-' * 15:>15}  ------")

    latest: dict[str, str | None] = {}
    for pkg in PACKAGES:
        if pkg in bundled:
            # Keep Expo's own range operator: `~2.32.0` is narrower than `^2.32.0`,
            # and for a native module that difference is the whole point.
            v, src = bundled[pkg], "expo sdk"
        else:
            v, src = npm_view(pkg), "npm latest"
        latest[pkg] = v
        print(f"{pkg:<35} {v or '?':>15}  {src}")

    # Parse current state of the fundamentals file (canonical source)
    fundamentals_path = Path("rn-fundamentals/references/stack-defaults.md")
    if not fundamentals_path.exists():
        print(f"\nERROR: {fundamentals_path} not found. Run from the repo root.")
        return 1
    current = parse_current(fundamentals_path)

    print(f"\n→ Comparing against {fundamentals_path}…\n")
    print(f"{'PACKAGE':<35} {'CURRENT':>15} {'TARGET':>15}  {'DIFF'}")
    print(f"{'-' * 35} {'-' * 15:>15} {'-' * 15:>15}  {'----'}")

    changes: list[tuple[str, str, str, str]] = []  # (pkg, current, new_pinned, prefix)
    for pkg in PACKAGES:
        curr = current.get(pkg, "?")
        new = latest.get(pkg)
        if curr == "?" or new is None:
            print(f"{pkg:<35} {curr:>15} {new or '?':>15}  ? (skip)")
            continue
        prefix, bare = strip_prefix(curr)
        # When Expo dictates the range, its operator wins over ours.
        new_prefix, new_bare = strip_prefix(new)
        if new_prefix:
            prefix, new = new_prefix, new_bare
        else:
            new = new_bare

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
    if changes:
        print(f"→ {len(changes)} package(s) drifted.")
    else:
        print("→ All versions current.")

    if not apply:
        print("\nDry-run mode. To apply changes, re-run with --apply.")
        return 0

    # Note we still rewrite when nothing drifted: the snapshot line records when
    # the pins were last CHECKED, not when they last changed. Returning early on
    # a clean run left rn-bootstrap's date frozen while the versions were fine.
    print("\n→ Rewriting stack-defaults.md files…" if changes
          else "\n→ No version changes; refreshing the snapshot date…")
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    # re.M matters: in rn-bootstrap the snapshot line is the third line, not the
    # first, so without it that file's date silently stopped updating.
    snapshot_re = re.compile(r"^> Snapshot date: \d{4}-\d{2}-\d{2}\.", re.M)

    for target_str in TARGETS:
        target = Path(target_str)
        if not target.exists():
            print(f"  skip: {target} (not found)")
            continue
        text = target.read_text()
        for pkg, curr, new, prefix in changes:
            # Rewrite the version ON THAT PACKAGE'S ROW only. A bare
            # text.replace() of the version string hits every row that happens
            # to share it — `expo` and `expo-router` were both `^57.0.8`, so
            # updating one silently rewrote the other (and with the wrong range
            # operator, since Expo pins them differently).
            row = re.compile(rf"^(\| `{re.escape(pkg)}` \| )`{re.escape(curr)}`", re.M)
            text, n = row.subn(rf"\g<1>`{prefix}{new}`", text)
            if n != 1:
                sys.stderr.write(f"! {target}: expected 1 row for {pkg}, matched {n}\n")
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
