#!/usr/bin/env python3
"""Run every skill's test suite: each `<skill>/scripts/test_*.py` tracked by git, plus the repo's own
`scripts/test_*.py` (the installers).

    python3 scripts/run_skill_tests.py            # all of them
    python3 scripts/run_skill_tests.py dev-flow   # only the suites of these skills

Why this exists: CI named its test files one by one, and on 2026-10-17 it ran 4 of 17. The other 13
existed and passed, and one regression in the wireframes or primitives-guard gate, both of which
`set-phase` enforces, would have gone through green (AUDIT.md §6.1). Discovering the files means a new
suite runs the day it is committed, with nobody remembering to add a line.

A suite fails when its runner exits non-zero, and also when it ran **zero tests**, because a file that
tests nothing is indistinguishable from one that passes. Skips are counted and printed: the design-lint
and primitives-guard suites skip their node cases without a real eslint install, and a skip must not
read as a pass.

Each suite runs in its own folder with `python3 -m unittest <module>`, the way its docstring says to.
A file that does not import unittest (launch-audit's) is a plain script and runs as one.
"""
from __future__ import annotations

import re
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def suites(only: list[str]) -> list[Path]:
    out = subprocess.run(["git", "ls-files", "*/scripts/test_*.py", "scripts/test_*.py"], cwd=ROOT,
                         capture_output=True, text=True, check=True).stdout.split()
    # <skill>/scripts/test_x.py or scripts/test_x.py, nothing deeper; `scripts` selects the repo's own
    paths = [ROOT / p for p in sorted(set(out)) if p.count("/") in (1, 2)]
    return [p for p in paths if not only or (p.parts[-3] if p.parent.parent != ROOT else "scripts") in only]


def run(path: Path) -> tuple[bool, str]:
    uses_unittest = re.search(r"^import unittest|^from unittest", path.read_text(), re.M)
    cmd = [sys.executable, "-m", "unittest", path.stem] if uses_unittest else [sys.executable, path.name]
    r = subprocess.run(cmd, cwd=path.parent, capture_output=True, text=True)
    out = r.stdout + r.stderr
    if r.returncode != 0:
        return False, out
    if uses_unittest:
        ran = re.search(r"^Ran (\d+) tests?", out, re.M)
        if not ran or ran.group(1) == "0":
            return False, out + "\n(ran zero tests: a suite that tests nothing is not a pass)"
        skipped = re.search(r"skipped=(\d+)", out)
        return True, f"{ran.group(1)} tests" + (f", {skipped.group(1)} skipped" if skipped else "")
    last = out.strip().splitlines()[-1] if out.strip() else "no output"
    return True, last


def main(argv: list[str]) -> int:
    found = suites(argv)
    if not found:
        print(f"no test suites found{' for ' + ', '.join(argv) if argv else ''}", file=sys.stderr)
        return 1
    failed = []
    for path in found:
        t = time.monotonic()
        ok, detail = run(path)
        name = str(path.relative_to(ROOT))
        if ok:
            print(f"✓ {name}  ({detail}, {time.monotonic() - t:.1f}s)")
        else:
            failed.append(name)
            print(f"✗ {name}\n" + "\n".join(f"    {line}" for line in detail.strip().splitlines()[-30:]))
    print(f"\n{len(found) - len(failed)}/{len(found)} suites passed")
    if failed:
        print("failed: " + ", ".join(failed))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
