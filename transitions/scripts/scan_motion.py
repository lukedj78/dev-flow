#!/usr/bin/env python3
"""scan_motion.py — fast first-pass signal for the `transitions` motion audit.

Walks a web project and flags ad-hoc / un-tokenized / a11y-unsafe motion. Two
layers of check:
  * line-level smells (magic durations, inline easings, transition-all, layout-
    prop transitions) — classify_line()
  * file-level smell (a file that animates but ships no prefers-reduced-motion
    fallback) — missing_reduced_motion()

This is a SIGNAL, not a verdict — heuristics over-report. The skill must verify
every hit by reading the code before it lands in the report.

    python3 scan_motion.py <project-root>      # prints JSON findings
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

# --- line-level smells: (category, regex). First match wins per line. ---------
LINE_RULES = [
    ("transition-all", re.compile(r"transition-all\b|transition:\s*all\b")),
    ("layout-prop-anim", re.compile(r"transition:\s*(?:width|height|top|left|right|bottom|margin|padding|box-shadow)\b")),
    ("magic-duration", re.compile(r"duration-\[\s*\d+\.?\d*m?s\s*\]|transition-duration:\s*\d|animation-duration:\s*\d")),
    ("inline-easing", re.compile(r"cubic-bezier\(|ease-\[")),
]

# --- file-level: does the file animate at all, and does it guard reduced motion?
ANIM_MARKER = re.compile(
    r"\banimate-in\b|\banimate-out\b|\btransition-\w|@keyframes\b|\banimate=\{|\bfrom ['\"]motion/react['\"]|framer-motion|startViewTransition",
)
RM_MARKER = re.compile(
    r"motion-reduce:|prefers-reduced-motion|useReducedMotion",
)
# A Motion (Tier 3) import — informational; needs context to judge overkill.
TIER3_IMPORT = re.compile(r"from ['\"]motion/react['\"]|from ['\"]framer-motion['\"]")

SKIP_DIRS = {"node_modules", ".git", "dist", ".next", ".expo", "build", ".turbo", ".vercel", "ios", "android", "coverage"}
CODE_SUFFIXES = {".ts", ".tsx", ".js", ".jsx", ".css", ".scss"}


def classify_line(line: str) -> str | None:
    """Return the first smell category matching this line, or None if clean."""
    for category, rx in LINE_RULES:
        if rx.search(line):
            return category
    return None


def missing_reduced_motion(text: str) -> bool:
    """True if the file animates but has no reduced-motion fallback anywhere."""
    return bool(ANIM_MARKER.search(text)) and not RM_MARKER.search(text)


def scan(root: Path) -> list[dict]:
    findings: list[dict] = []
    for p in sorted(root.rglob("*")):
        if p.is_dir() or any(part in SKIP_DIRS for part in p.parts):
            continue
        if p.suffix not in CODE_SUFFIXES:
            continue
        try:
            text = p.read_text(errors="ignore")
        except OSError:
            continue
        rel = str(p.relative_to(root))
        first_anim_line = None
        for i, line in enumerate(text.splitlines(), start=1):
            if first_anim_line is None and ANIM_MARKER.search(line):
                first_anim_line = i
            cat = classify_line(line)
            if cat:
                findings.append({"file": rel, "line": i, "category": cat, "text": line.strip()[:120]})
            if TIER3_IMPORT.search(line):
                findings.append({"file": rel, "line": i, "category": "tier3-import-review", "text": line.strip()[:120]})
        if missing_reduced_motion(text):
            findings.append({"file": rel, "line": first_anim_line or 1,
                             "category": "no-reduced-motion", "text": "file animates without a prefers-reduced-motion fallback"})
    return findings


def main() -> None:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else ".")
    findings = scan(root)
    by_cat: dict[str, int] = {}
    for f in findings:
        by_cat[f["category"]] = by_cat.get(f["category"], 0) + 1
    print(json.dumps({"summary": by_cat, "findings": findings,
                      "note": "SIGNAL not verdict — verify each hit in code before reporting"}, indent=2))


if __name__ == "__main__":
    main()
