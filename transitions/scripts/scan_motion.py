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
import os
import re
import sys
from pathlib import Path

# --- line-level smells: (category, regex). First match wins per line. ---------
LINE_RULES = [
    ("transition-all", re.compile(r"transition-all\b|transition:\s*all\b")),
    ("layout-prop-anim", re.compile(r"transition:\s*(?:width|height|top|left|right|bottom|margin|padding|border-width)\b")),
    # Paint, not layout: no re-measuring, but a redraw every frame. box-shadow is the one people miss — swap it for
    # the opacity of a layer that carries the shadow, or `filter: drop-shadow()` (animation-standards.md §Frame budget).
    ("paint-prop-anim", re.compile(r"transition:\s*(?:box-shadow|border-radius)\b|\btransition-shadow\b")),
    # will-change promotes a layer and costs GPU memory: one property, on the element that animates, after a measured
    # shift. `all` or a list of properties is a layer budget nobody chose.
    ("will-change-broad", re.compile(r"will-change:\s*(?:all\b|[\w-]+\s*,\s*[\w-]+\s*,)")),
    ("magic-duration", re.compile(r"duration-\[\s*\d+\.?\d*m?s\s*\]|transition-duration:\s*\d|animation-duration:\s*\d")),
    # `ease-[var(--motion-…)]` is the *tokenized* form this skill asks for, so it
    # must not be reported as an inline easing. Only a literal bezier, or an
    # arbitrary easing that is not a var reference, is a smell.
    ("inline-easing", re.compile(r"cubic-bezier\(|ease-\[(?!\s*var\(--motion-)")),
]

# --- file-level: does the file animate at all, and does it guard reduced motion?
ANIM_MARKER = re.compile(
    r"\banimate-in\b|\banimate-out\b|\btransition-\w|@keyframes\b|\banimate=\{|\bfrom ['\"]motion/react['\"]|framer-motion|startViewTransition",
)
RM_MARKER = re.compile(
    # The last alternative matters: a file that composes its classes from
    # `lib/motion/transitions` inherits that library's `motion-reduce:`
    # fallbacks, and reporting it as unguarded punishes the file for doing
    # exactly what this skill asks. File-level detection cannot see through an
    # imported class string, so the import is the evidence.
    r"motion-reduce:|prefers-reduced-motion|useReducedMotion|from ['\"]@?[\w./-]*lib/motion/transitions['\"]",
)
# A Motion (Tier 3) import — informational; needs context to judge overkill.
TIER3_IMPORT = re.compile(r"from ['\"]motion/react['\"]|from ['\"]framer-motion['\"]")

# `.claude` holds agent worktrees (whole copies of the app): scanning them reports every hit once per worktree.
SKIP_DIRS = {"node_modules", ".git", "dist", ".next", ".expo", "build", ".turbo", ".vercel", "ios", "android", "coverage",
             ".claude"}
CODE_SUFFIXES = {".ts", ".tsx", ".js", ".jsx", ".css", ".scss"}

# The token layer is where the durations and beziers are *supposed* to live —
# flagging `lib/motion/tokens.ts` for containing a cubic-bezier told the reader
# the one file that is definitionally correct was the problem.
TOKEN_LAYER = ("lib/motion/", "lib/motion-config.")

# Copied-in vendor source: shadcn/Base-UI primitives and registry components land
# here by CLI, and their motion is upstream's. Still reported — a `transition-all`
# in a Button you own is real — but tagged `vendored: true`, because forty
# untouched preset files drowning six authored ones is how an audit gets ignored.
VENDORED = ("components/ui/", "lib/use-icon-animation.")


def provenance(rel: str) -> str:
    """`token-layer`, `vendored`, or `authored` — reported so hits can be ranked."""
    normalized = rel.replace("\\", "/")
    if normalized.startswith(TOKEN_LAYER):
        return "token-layer"
    if normalized.startswith(VENDORED):
        return "vendored"
    return "authored"


# A line that *defines* a motion token — `--motion-ease-standard: cubic-bezier(…)`
# — is the bridge this skill writes, not a smell. Same for the duration vars.
TOKEN_DEFINITION = re.compile(r"--motion-[\w-]+\s*:")

# `0.01ms` inside the global guard is the guard. Anything matching this is the
# reduced-motion neutraliser rather than a hand-picked duration.
GUARD_DURATION = re.compile(r"0\.01ms")


def classify_line(line: str) -> str | None:
    """Return the first smell category matching this line, or None if clean."""
    if TOKEN_DEFINITION.search(line) or GUARD_DURATION.search(line):
        return None
    for category, rx in LINE_RULES:
        if rx.search(line):
            return category
    return None


GLOBAL_WILL_CHANGE = re.compile(r"(?:^|[}\s,])(?:\*|html|body|:root)\s*\{[^}]*?will-change", re.S)
RAF = re.compile(r"\brequestAnimationFrame\s*\(")
# A React state setter called as a bare function: not a method (`.setProperty`), not a timer.
SET_STATE = re.compile(r"(?<![.\w])set(?!Timeout|Interval|Immediate)[A-Z]\w*\s*\(")
CSS_VAR_WRITE = re.compile(r"\.style\.setProperty\(\s*['\"`]--")
GESTURE = re.compile(r"pointermove|onPointerMove|onDrag|mousemove|onMouseMove|touchmove|onTouchMove|requestAnimationFrame|\bscroll\b", re.I)


def _balanced(text: str, start: int, open_ch: str, close_ch: str) -> int:
    """Index just past the bracket that closes the one at `start`."""
    depth = 0
    for i in range(start, len(text)):
        if text[i] == open_ch:
            depth += 1
        elif text[i] == close_ch:
            depth -= 1
            if depth == 0:
                return i + 1
    return len(text)


def _function_body(text: str, name: str) -> tuple[int, int] | None:
    m = re.search(rf"function\s+{re.escape(name)}\s*\(|(?:const|let|var)\s+{re.escape(name)}\s*=", text)
    if not m:
        return None
    brace = text.find("{", m.end())
    if brace == -1:
        return None
    return brace, _balanced(text, brace, "{", "}")


def frame_smells(text: str) -> list[tuple[int, str, str]]:
    """File-level smells that a single line cannot show: (line, category, text).

    - will-change on `*` / html / body / :root — every element promoted;
    - a React state setter inside a requestAnimationFrame **loop** (a callback that schedules the next frame, inline or
      by name) — a re-render per frame; write ref.style or a motion value instead. A one-shot frame (open a dialog
      after mount) is not per frame;
    - a CSS custom property written from a gesture or frame loop — it inherits, so every descendant recalculates
      style each frame (set `transform` on the element directly).
    Signals, not verdicts: read the code before reporting.
    """
    lines = text.splitlines()
    line_of = lambda offset: text.count("\n", 0, offset)
    out: list[tuple[int, str, str]] = []
    for m in GLOBAL_WILL_CHANGE.finditer(text):
        at = line_of(m.end())
        out.append((at + 1, "will-change-broad", lines[at].strip()[:120]))
    flagged: set[int] = set()
    for m in RAF.finditer(text):
        arg_start, arg_end = m.end() - 1, _balanced(text, m.end() - 1, "(", ")")
        arg = text[arg_start + 1:arg_end - 1].strip()
        if re.fullmatch(r"[A-Za-z_$][\w$]*", arg):
            span = _function_body(text, arg)
            loops = span and re.search(rf"requestAnimationFrame\s*\(\s*{re.escape(arg)}\s*\)", text[span[0]:span[1]])
        else:
            span = (arg_start, arg_end)
            loops = RAF.search(text, arg_start + 1, arg_end)
        if not span or not loops:
            continue
        setter = SET_STATE.search(text, span[0], span[1])
        if setter and line_of(setter.start()) not in flagged:
            at = line_of(setter.start())
            flagged.add(at)
            out.append((at + 1, "state-per-frame", lines[at].strip()[:120]))
    for i, line in enumerate(lines):
        if CSS_VAR_WRITE.search(line) and any(GESTURE.search(l) for l in lines[max(0, i - 8):i + 1]):
            out.append((i + 1, "css-var-per-frame", line.strip()[:120]))
    return sorted(out)


def missing_reduced_motion(text: str) -> bool:
    """True if the file animates but has no reduced-motion fallback anywhere."""
    return bool(ANIM_MARKER.search(text)) and not RM_MARKER.search(text)


def scan(root: Path) -> list[dict]:
    findings: list[dict] = []
    # os.walk, pruning SKIP_DIRS before descending — rglob walked every node_modules and dropped it afterwards.
    paths = []
    for here, dirs, names in os.walk(root):
        dirs[:] = sorted(d for d in dirs if d not in SKIP_DIRS)
        paths += [Path(here) / n for n in names]
    for p in sorted(paths):
        if p.suffix not in CODE_SUFFIXES:
            continue
        try:
            text = p.read_text(errors="ignore")
        except OSError:
            continue
        rel = str(p.relative_to(root))
        origin = provenance(rel)
        first_anim_line = None
        for i, line in enumerate(text.splitlines(), start=1):
            if first_anim_line is None and ANIM_MARKER.search(line):
                first_anim_line = i
            cat = classify_line(line)
            if cat:
                findings.append({"file": rel, "line": i, "category": cat, "text": line.strip()[:120], "provenance": origin})
            if TIER3_IMPORT.search(line):
                findings.append({"file": rel, "line": i, "category": "tier3-import-review", "text": line.strip()[:120], "provenance": origin})
        for line_no, cat, snippet in frame_smells(text):
            findings.append({"file": rel, "line": line_no, "category": cat, "text": snippet, "provenance": origin})
        if missing_reduced_motion(text):
            findings.append({"file": rel, "line": first_anim_line or 1,
                             "category": "no-reduced-motion",
                             "text": "file animates without a prefers-reduced-motion fallback",
                             "provenance": origin})
    return findings


def main() -> None:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else ".")
    findings = scan(root)
    by_cat: dict[str, int] = {}
    by_origin: dict[str, int] = {}
    for f in findings:
        by_cat[f["category"]] = by_cat.get(f["category"], 0) + 1
        by_origin[f["provenance"]] = by_origin.get(f["provenance"], 0) + 1
    print(json.dumps({
        "summary": by_cat,
        # Read `authored` first: those are the hits someone on this project wrote.
        # `vendored` is copied-in preset source, `token-layer` is where the raw
        # values legitimately live.
        "by_provenance": by_origin,
        "findings": findings,
        "note": "SIGNAL not verdict — verify each hit in code before reporting; rank by provenance",
    }, indent=2))


if __name__ == "__main__":
    main()
