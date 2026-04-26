#!/usr/bin/env python3
"""Property-based eval runner for dev-flow's deterministic scripts.

Each fixture is a JSON file at `evals/<skill>/expected/<name>.json`:

    {
      "skill": "image-to-design-md",
      "fixture": "synthetic-light",
      "input": "evals/image-to-design-md/inputs/synthetic-light.png",
      "command": "python3 image-to-design-md/scripts/quantize_palette.py {input} --k 8",
      "assertions": [
        { "type": "palette_size_between", "min": 4, "max": 12 },
        { "type": "contains_color", "hex": "#0066cc", "tolerance_de": 8 }
      ]
    }

The runner shells out to `command`, captures stdout, parses out hex colors
(`#rrggbb` or `rrggbb`), and runs each assertion against the resulting palette.
For the `stable_across_runs` assertion it re-runs the command N times and
compares pairwise palettes via ΔE.

Run with:
    python3 evals/run_evals.py
    python3 evals/run_evals.py --skill image-to-design-md --verbose
    python3 evals/run_evals.py --ci    # exit nonzero on first failure
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from itertools import combinations
from pathlib import Path
from typing import Any

# Make `from lib.color import …` work whether we're invoked from repo root
# or from inside evals/. Drop evals/ on sys.path.
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from lib.color import RGB, delta_e76, lightness, parse_hex, to_hex  # noqa: E402

REPO_ROOT = HERE.parent
HEX_PATTERN = re.compile(r"#?([0-9a-fA-F]{6})\b")


# ---------------------------------------------------------------------------
# Output parsing — extract a palette of RGB tuples from a command's stdout.
# Heuristics: capture every `#rrggbb` or `rrggbb` token, dedupe preserving
# order. If the script prints structured JSON, prefer that.
# ---------------------------------------------------------------------------


def parse_palette_from_stdout(stdout: str) -> list[RGB]:
    # First: try JSON output. quantize_palette.py prints a JSON object with
    # "palette": ["#aabbcc", …] in some modes.
    try:
        data = json.loads(stdout.strip())
        if isinstance(data, dict) and "palette" in data:
            return [parse_hex(c) for c in data["palette"]]
        if isinstance(data, list) and all(isinstance(c, str) for c in data):
            return [parse_hex(c) for c in data]
    except (json.JSONDecodeError, ValueError):
        pass

    # Fallback: regex over plain text. Useful for human-readable output.
    seen: set[str] = set()
    palette: list[RGB] = []
    for match in HEX_PATTERN.finditer(stdout):
        hexstr = match.group(1).lower()
        if hexstr in seen:
            continue
        seen.add(hexstr)
        palette.append(parse_hex(hexstr))
    return palette


# ---------------------------------------------------------------------------
# Command execution
# ---------------------------------------------------------------------------


def run_command(command: str, input_path: Path) -> str:
    """Substitute {input} placeholder and run from repo root."""
    cmd = command.replace("{input}", str(input_path.resolve()))
    result = subprocess.run(
        cmd,
        shell=True,
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"Command failed (exit {result.returncode}): {cmd}\n"
            f"--- stdout ---\n{result.stdout}\n--- stderr ---\n{result.stderr}"
        )
    return result.stdout


# ---------------------------------------------------------------------------
# Assertion handlers — each returns (passed: bool, message: str).
# ---------------------------------------------------------------------------


def _palette_size_between(palette: list[RGB], a: dict[str, Any]) -> tuple[bool, str]:
    n = len(palette)
    lo, hi = a["min"], a["max"]
    return (lo <= n <= hi, f"got {n}, want {lo}..{hi}")


def _palette_size_exact(palette: list[RGB], a: dict[str, Any]) -> tuple[bool, str]:
    n = len(palette)
    return (n == a["value"], f"got {n}, want {a['value']}")


def _contains_color(palette: list[RGB], a: dict[str, Any]) -> tuple[bool, str]:
    target = parse_hex(a["hex"])
    tol = a.get("tolerance_de", 5)
    if not palette:
        return (False, "palette empty")
    distances = [(delta_e76(target, c), c) for c in palette]
    closest_de, closest = min(distances)
    ok = closest_de <= tol
    return (
        ok,
        f"closest to {a['hex']} is {to_hex(closest)} ΔE={closest_de:.1f} (tol={tol})",
    )


def _background_lightness_above(palette: list[RGB], a: dict[str, Any]) -> tuple[bool, str]:
    if not palette:
        return (False, "palette empty")
    # Heuristic: most-area color is usually first in the palette emitted by
    # quantize_palette.py (ordered by cluster size desc). Take the first.
    bg = palette[0]
    L = lightness(bg)
    return (L >= a["value"], f"first-color L*={L:.1f}, want ≥ {a['value']} ({to_hex(bg)})")


def _background_lightness_below(palette: list[RGB], a: dict[str, Any]) -> tuple[bool, str]:
    if not palette:
        return (False, "palette empty")
    bg = palette[0]
    L = lightness(bg)
    return (L <= a["value"], f"first-color L*={L:.1f}, want ≤ {a['value']} ({to_hex(bg)})")


def _no_near_white(palette: list[RGB], a: dict[str, Any]) -> tuple[bool, str]:
    threshold = a.get("threshold", 95)
    near_whites = [(to_hex(c), lightness(c)) for c in palette if lightness(c) > threshold]
    if not near_whites:
        return (True, f"no color with L* > {threshold}")
    return (False, f"{len(near_whites)} near-white(s): {near_whites}")


def _stable_across_runs(palette: list[RGB], a: dict[str, Any], *, command: str, input_path: Path) -> tuple[bool, str]:
    """Re-run the command N times. Compare every pair of palettes by mean
    pairwise ΔE. Fails if any pair exceeds max_delta_e on average."""
    runs = a.get("runs", 3)
    threshold = a.get("max_delta_e", 5)
    palettes = [palette]
    for _ in range(runs - 1):
        try:
            stdout = run_command(command, input_path)
        except RuntimeError as e:
            return (False, f"command failed during stability run: {e}")
        palettes.append(parse_palette_from_stdout(stdout))

    # For each pair of runs, compute the mean of (each color in run-A's
    # nearest distance to a color in run-B). Asymmetric but fine as a proxy.
    def mean_nearest(p1: list[RGB], p2: list[RGB]) -> float:
        if not p1 or not p2:
            return float("inf")
        return sum(min(delta_e76(c1, c2) for c2 in p2) for c1 in p1) / len(p1)

    worst = 0.0
    worst_idx = (0, 0)
    for (i, p1), (j, p2) in combinations(enumerate(palettes), 2):
        d = max(mean_nearest(p1, p2), mean_nearest(p2, p1))
        if d > worst:
            worst, worst_idx = d, (i, j)
    return (worst <= threshold, f"worst pair (runs {worst_idx}) ΔE={worst:.2f}, want ≤ {threshold}")


def _output_contains_yaml_key(palette: list[RGB], a: dict[str, Any], *, stdout: str) -> tuple[bool, str]:
    key = a["key"]
    # Match `key:` at line start (or under `---` frontmatter).
    return (
        bool(re.search(rf"^{re.escape(key)}\s*:", stdout, re.MULTILINE)),
        f"key {key!r} {'present' if key in stdout else 'absent'}",
    )


def _output_section_present(palette: list[RGB], a: dict[str, Any], *, stdout: str) -> tuple[bool, str]:
    name = a["name"]
    pattern = rf"^#{{1,6}}\s+.*{re.escape(name)}"
    return (
        bool(re.search(pattern, stdout, re.MULTILINE | re.IGNORECASE)),
        f"section {name!r} {'found' if re.search(pattern, stdout, re.MULTILINE | re.IGNORECASE) else 'missing'}",
    )


ASSERTION_HANDLERS = {
    "palette_size_between": _palette_size_between,
    "palette_size_exact": _palette_size_exact,
    "contains_color": _contains_color,
    "background_lightness_above": _background_lightness_above,
    "background_lightness_below": _background_lightness_below,
    "no_near_white": _no_near_white,
    "stable_across_runs": _stable_across_runs,
    "output_contains_yaml_key": _output_contains_yaml_key,
    "output_section_present": _output_section_present,
}


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------


def discover_fixtures(skill_filter: str | None) -> list[Path]:
    evals_root = HERE
    paths = []
    for skill_dir in sorted(p for p in evals_root.iterdir() if p.is_dir() and p.name not in {"lib", "__pycache__"}):
        if skill_filter and skill_dir.name != skill_filter:
            continue
        expected = skill_dir / "expected"
        if not expected.exists():
            continue
        paths.extend(sorted(expected.glob("*.json")))
    return paths


def run_fixture(fixture_path: Path, *, verbose: bool, ci: bool) -> tuple[int, int]:
    """Run one fixture. Returns (passed_count, total_count)."""
    spec = json.loads(fixture_path.read_text())
    skill = spec["skill"]
    name = spec["fixture"]
    command = spec["command"]
    input_path = REPO_ROOT / spec["input"]

    if not input_path.exists():
        print(f"  ✗ {skill}/{name}  input missing: {input_path}")
        return (0, len(spec.get("assertions", [])))

    print(f"  · {skill}/{name}")

    try:
        stdout = run_command(command, input_path)
    except RuntimeError as e:
        print(f"      command failed: {e}")
        return (0, len(spec.get("assertions", [])))

    palette = parse_palette_from_stdout(stdout)
    if verbose:
        print(f"      palette: {[to_hex(c) for c in palette]}")

    passed = 0
    for assertion in spec.get("assertions", []):
        atype = assertion["type"]
        handler = ASSERTION_HANDLERS.get(atype)
        if handler is None:
            print(f"      ? unknown assertion type: {atype}")
            continue
        # Pass kwargs only to handlers that accept them.
        if atype == "stable_across_runs":
            ok, msg = handler(palette, assertion, command=command, input_path=input_path)
        elif atype in {"output_contains_yaml_key", "output_section_present"}:
            ok, msg = handler(palette, assertion, stdout=stdout)
        else:
            ok, msg = handler(palette, assertion)
        icon = "✓" if ok else "✗"
        if ok or verbose:
            print(f"      {icon} {atype} — {msg}")
        else:
            print(f"      {icon} {atype} — {msg}")
        if ok:
            passed += 1
        elif ci:
            return (passed, len(spec["assertions"]))

    return (passed, len(spec.get("assertions", [])))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--skill", default=None, help="Run only fixtures for this skill")
    ap.add_argument("--verbose", action="store_true", help="Show palette + every assertion")
    ap.add_argument("--ci", action="store_true", help="Exit nonzero on first failure")
    args = ap.parse_args()

    fixtures = discover_fixtures(args.skill)
    if not fixtures:
        print("No fixtures found.")
        return 0

    print(f"Found {len(fixtures)} fixture(s):")
    total_passed = 0
    total = 0
    for fx in fixtures:
        passed, n = run_fixture(fx, verbose=args.verbose, ci=args.ci)
        total_passed += passed
        total += n
        if args.ci and passed != n:
            print(f"\nCI mode — first failure at {fx.name}, exiting.")
            return 1

    print()
    print(f"Summary: {total_passed}/{total} assertions passed.")
    return 0 if total_passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
