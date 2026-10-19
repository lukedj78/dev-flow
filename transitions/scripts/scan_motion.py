#!/usr/bin/env python3
"""scan_motion.py — fast first-pass signal for the `transitions` motion audit.

Walks a web project and flags ad-hoc / un-tokenized / a11y-unsafe / frame-budget motion. Three
layers of check:
  * line-level smells (magic durations, inline easings, transition-all, layout- and paint-
    prop transitions, a broad will-change) — classify_line()
  * file-level frame smells a line cannot show (will-change on a global selector, React state
    set inside a requestAnimationFrame loop, a CSS variable written from a gesture) — frame_smells()
  * file-level a11y smell (a file that animates but ships no prefers-reduced-motion fallback)
    — missing_reduced_motion()

This is a SIGNAL, not a verdict — heuristics over-report. The skill must verify
every hit by reading the code before it lands in the report.

    python3 scan_motion.py <project-root>      # prints JSON findings
"""
from __future__ import annotations

import bisect
import json
import os
import re
import sys
from pathlib import Path

# --- line-level smells: (category, regex). First match wins per line. ---------
# A transition declaration in any syntax: CSS `transition:` / `transition-property:` (property lists included),
# CSS-in-JS `transition: "…"`, Tailwind `transition-[…]`.
_DECL = r"""transition(?:-property)?\s*:\s*["'`]?[^;"'`}\n]*"""
_ARB = r"transition-\[[^\]]*"
_LAYOUT = r"(?<![\w-])(?:width|height|min-height|max-height|min-width|max-width|top|left|right|bottom|margin|padding|border-width)(?![\w-])"
_PAINT = r"(?<![\w-])(?:box-shadow|border-radius)(?![\w-])"
LINE_RULES = [
    ("transition-all", re.compile(r"transition-all\b|transition:\s*[\"'`]?all\b")),
    ("layout-prop-anim", re.compile(rf"{_DECL}{_LAYOUT}|{_ARB}{_LAYOUT}")),
    # Paint, not layout: no re-measuring, but a redraw every frame. box-shadow is the one people miss — fade a layer
    # that carries the final shadow instead (animation-standards.md §Frame budget). shadcn's own primitives animate
    # their focus ring this way (`transition-[color,box-shadow]`): reported, labelled vendored, left alone.
    ("paint-prop-anim", re.compile(rf"{_DECL}{_PAINT}|{_ARB}{_PAINT}|\btransition-shadow\b")),
    # will-change promotes a layer and costs GPU memory: one property, on the element that animates, after a measured
    # shift. `all` or a list of two or more properties is a layer budget nobody chose.
    ("will-change-broad", re.compile(r"""will-change:\s*(?:all\b|[\w-]+\s*,)|will-change-\[[^\]]*,|willChange\s*:\s*["'`](?:all\b|[^"'`]*,)""")),
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
    # In a monorepo the same shadcn source lives under an app or the shared package: apps/web/components/ui/,
    # packages/ui/src/components/ (the official shadcn monorepo layout).
    if "/components/ui/" in normalized or re.match(r"packages/[\w.-]+/src/components/", normalized):
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


RAF = re.compile(r"\brequestAnimationFrame\s*\(")
USE_ANIMATION_FRAME = re.compile(r"\buseAnimationFrame\s*\(")   # Motion's hook: its callback runs every frame
SETTER_CALL = re.compile(r"(?<![.\w$])(set[A-Z][\w$]*)\s*\(|\bthis\.setState\s*\(")
LOCAL_SETTER_DEF = re.compile(r"\bfunction\s+(set[A-Z][\w$]*)\s*\(|\b(?:const|let|var)\s+(set[A-Z][\w$]*)\s*=")
NOT_STATE = {"setTimeout", "setInterval", "setImmediate"}
CSS_VAR_WRITE = re.compile(r"\.style\.setProperty\(\s*['\"`]--")
# A custom property in a JSX style object whose value is not a plain string literal: `"--swipe-amount": `${d}px``.
CSS_VAR_STYLE = re.compile(r"""["']--[\w-]+["']\s*:\s*(?!["'][^"'`]*["']\s*[,}])""")
GESTURE = re.compile(r"""pointermove|onPointerMove|onDrag\w*|mousemove|onMouseMove|touchmove|onTouchMove|onWheel|onScroll|"""
                     r"""addEventListener\(\s*["'](?:scroll|wheel|resize)|requestAnimationFrame|useAnimationFrame|useScroll""", re.I)
GLOBAL_SELECTOR = re.compile(r"^(?:\*(?:::?[\w-]+)?|html|body|:root)$")
_OPEN, _CLOSE = "([{", ")]}"


SPECIAL = re.compile(r"//|/\*|['\"`]")


def _spans(text: str) -> list[tuple[int, int, str]]:
    """(start, end, kind) of every comment ("c") and string or template contents ("s"), jumping from one special
    character to the next. A quote opens a string only after an operator or at a line start: an apostrophe in JSX text
    ("Don't") is not a string."""
    spans, i, n = [], 0, len(text)
    while True:
        m = SPECIAL.search(text, i)
        if not m:
            return spans
        i, tok = m.start(), m.group()
        if tok == "//":
            j = text.find("\n", i)
            j = n if j == -1 else j
            spans.append((i, j, "c")); i = j; continue
        if tok == "/*":
            j = text.find("*/", i + 2)
            j = n if j == -1 else j + 2
            spans.append((i, j, "c")); i = j; continue
        k = i - 1
        while k >= 0 and text[k] in " \t":
            k -= 1
        if not (tok == "`" or k < 0 or text[k] in "=(,:[{}!&|?+-*/%<;\n" or text[max(0, k - 5):k + 1].endswith("return")):
            i += 1; continue
        j = i + 1
        while j < n and text[j] != tok:
            if text[j] == "\\":
                j += 1
            elif text[j] == "\n" and tok != "`":
                break
            j += 1
        spans.append((i + 1, min(j, n), "s"))
        i = j + 1


def _masks(text: str) -> tuple[str, str]:
    """(comments and strings blanked, comments only blanked) — same length and newlines, so brackets and words inside
    them stop counting while offsets and line numbers stay true."""
    full, comments = list(text), list(text)
    for a, b, kind in _spans(text):
        for k in range(a, b):
            if text[k] != "\n":
                full[k] = " "
                if kind == "c":
                    comments[k] = " "
    return "".join(full), "".join(comments)


def _balanced(masked: str, start: int) -> int:
    """Index just past the bracket that closes the one at `start` (masked text: no strings or comments)."""
    depth = 0
    for i in range(start, len(masked)):
        if masked[i] in _OPEN:
            depth += 1
        elif masked[i] in _CLOSE:
            depth -= 1
            if depth == 0:
                return i + 1
    return len(masked)


def _expression_end(masked: str, start: int) -> int:
    """End of an arrow function's expression body: the first `;` or newline at bracket depth 0."""
    depth = 0
    for i in range(start, len(masked)):
        ch = masked[i]
        if ch in _OPEN:
            depth += 1
        elif ch in _CLOSE:
            if depth == 0:
                return i
            depth -= 1
        elif ch in ";\n" and depth == 0:
            return i
    return len(masked)


DEFINITION = re.compile(r"\bfunction\s+([A-Za-z_$][\w$]*)\s*(?=\()|\b(?:const|let|var)\s+([A-Za-z_$][\w$]*)\s*(?::[^=;]+?)?=(?!=)")


def _definition_index(masked: str) -> dict[str, int]:
    """name → offset of its first `function name(` / `const name =`, in one pass (a search per name was quadratic)."""
    index: dict[str, int] = {}
    for m in DEFINITION.finditer(masked):
        index.setdefault(m.group(1) or m.group(2), m.start())
    return index


def _function_body(masked: str, name: str, index: dict[str, int] | None = None) -> tuple[int, int] | None:
    """The body span of a function called `name`: a declaration, a (typed) const/let/var arrow or function expression,
    or a class field / method."""
    n = re.escape(name)
    pos = index.get(name, 0) if index is not None else 0
    if index is not None and name not in index:
        pos = None
    m = re.compile(rf"\bfunction\s+{n}\s*(?=\()").search(masked, pos) if pos is not None else None
    if m:
        params_end = _balanced(masked, m.end())
        brace = masked.find("{", params_end)
        return (brace, _balanced(masked, brace)) if brace != -1 else None
    m = ((re.compile(rf"\b(?:const|let|var)\s+{n}\s*(?::[^=;]+?)?=(?!=)\s*").search(masked, pos) if pos is not None else None)
         or re.search(rf"(?<![\w.$]){n}\s*=(?![=>])\s*(?=(?:async\s*)?(?:\(|function\b|[\w$]+\s*=>))", masked))
    if m:
        k = m.end()
        fn = re.match(r"(?:async\s*)?function\b[^(]*", masked[k:])
        if fn:
            params_end = _balanced(masked, k + fn.end())
            brace = masked.find("{", params_end)
            return (brace, _balanced(masked, brace)) if brace != -1 else None
        arrow = masked.find("=>", k)
        if arrow == -1:
            return None
        body = arrow + 2
        while body < len(masked) and masked[body] in " \t\n":
            body += 1
        if body < len(masked) and masked[body] == "{":
            return body, _balanced(masked, body)
        return body, _expression_end(masked, body)
    m = re.search(rf"(?<![\w.$]){n}\s*(?=\([^)]*\)\s*\{{)", masked)   # class method `tick() {`
    if m:
        brace = masked.find("{", _balanced(masked, m.end()))
        return brace, _balanced(masked, brace)
    return None


def frame_smells(text: str) -> list[tuple[int, str, str]]:
    """File-level smells that a single line cannot show: (line, category, text).

    - will-change on `*` / html / body / :root (in any selector list) — every element promoted;
    - React state set inside a requestAnimationFrame **loop** — a callback that schedules itself again, inline or by
      name, or Motion's useAnimationFrame — a re-render per frame; write ref.style or a Motion value instead. Every
      setter in the loop is reported. A one-shot frame (or a double rAF that waits for a paint) is not per frame, and
      a local helper named set… is not state;
    - a CSS custom property written from a gesture or frame handler (style.setProperty, or a dynamic value in a JSX
      style object in a file with one) — it inherits, so every descendant recalculates style each frame.
    Signals, not verdicts: read the code before reporting.
    """
    masked, no_comments = _masks(text)
    lines = text.splitlines()
    starts = [0] + [m.end() for m in re.finditer("\n", text)]
    line_of = lambda offset: bisect.bisect_right(starts, offset) - 1
    found: dict[tuple[int, str], str] = {}
    def hit(offset: int, cat: str) -> None:
        at = line_of(offset)
        found.setdefault((at + 1, cat), lines[at].strip()[:120] if at < len(lines) else "")

    # The rule that holds each `will-change`: walk back to its `{` and the selector before it (a regex over a whole JS
    # file backtracks quadratically, so only the few places that mention it are read).
    for m in re.finditer(r"will-change", no_comments):
        brace = no_comments.rfind("{", 0, m.start())
        if brace == -1 or "}" in no_comments[brace:m.start()]:
            continue
        sel_start = max(no_comments.rfind("}", 0, brace), no_comments.rfind(";", 0, brace), no_comments.rfind("{", 0, brace)) + 1
        if any(GLOBAL_SELECTOR.match(s.strip()) for s in no_comments[sel_start:brace].split(",")):
            hit(m.start(), "will-change-broad")

    local_helpers = {a or b for a, b in LOCAL_SETTER_DEF.findall(masked)}
    bodies: dict[str, tuple[int, int] | None] = {}
    index = _definition_index(masked)
    def body_of(name: str):
        if name not in bodies:
            bodies[name] = _function_body(masked, name, index)
        return bodies[name]
    def report_setters(span: tuple[int, int]) -> None:
        for s in SETTER_CALL.finditer(masked, span[0], span[1]):
            name = s.group(1)
            if name is None or (name not in NOT_STATE and name not in local_helpers):
                hit(s.start(), "state-per-frame")

    for m in USE_ANIMATION_FRAME.finditer(masked):
        report_setters((m.end() - 1, _balanced(masked, m.end() - 1)))
    for m in RAF.finditer(masked):
        arg_start = m.end() - 1
        arg_end = _balanced(masked, arg_start)
        arg = masked[arg_start + 1:arg_end - 1].strip()
        named = re.fullmatch(r"(?:this\.)?([A-Za-z_$][\w$]*)", arg)
        if named:
            name = named.group(1)
            span = body_of(name)
            if span and re.search(rf"requestAnimationFrame\s*\(\s*(?:this\.)?{re.escape(name)}\s*\)", masked[span[0]:span[1]]):
                report_setters(span)
            continue
        # Inline callback: a loop only when it re-schedules the function that encloses this very call.
        for nested in re.finditer(r"requestAnimationFrame\s*\(\s*(?:this\.)?([A-Za-z_$][\w$]*)\s*\)", masked[arg_start:arg_end]):
            span = body_of(nested.group(1))
            if span and span[0] <= m.start() < span[1]:
                report_setters((arg_start, arg_end))
                break

    gesture_file = bool(GESTURE.search(no_comments))
    no_comment_lines = no_comments.splitlines()
    for i, line in enumerate(lines):
        if "--" not in line:
            continue
        code_line = no_comment_lines[i] if i < len(no_comment_lines) else ""
        if CSS_VAR_WRITE.search(code_line) and any(GESTURE.search(l) for l in no_comment_lines[max(0, i - 25):i + 1]):
            found.setdefault((i + 1, "css-var-per-frame"), line.strip()[:120])
        elif CSS_VAR_STYLE.search(code_line) and gesture_file:
            found.setdefault((i + 1, "css-var-per-frame"), line.strip()[:120])
    return sorted((line, cat, snippet) for (line, cat), snippet in found.items())


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
        seen = {(f["line"], f["category"]) for f in findings if f["file"] == rel}
        for line_no, cat, snippet in frame_smells(text):
            if (line_no, cat) not in seen:   # a global `will-change: all` is both a line and a file smell
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
