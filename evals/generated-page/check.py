#!/usr/bin/env python3
"""check.py — grade a generated app against the rules the skill that generated it states.

The third kind of check in this repo, and the one that was missing:

    lint_skills.py       is a skill still well-formed?          (the source)
    run_evals.py         do the deterministic scripts hold?     (the tools)
    check.py             did the generation follow its own rules? (the output)

Nothing here judges taste. Every rule below is one a reviewer could point at in a
diff, drawn from `design-md-to-app/references/anti-slop-fallbacks.md` and the
mandatory steps in that skill — which is the whole point: a rule the generator
states and nobody counts is a rule that quietly stops being followed.

    python3 evals/generated-page/check.py ~/projects/my-app
    python3 evals/generated-page/check.py ~/projects/my-app --json
    python3 evals/generated-page/check.py ~/projects/my-app --baseline before.json
    python3 evals/generated-page/check.py --selftest

Exit code is 0 by default: this is a measurement, not a gate. `--fail-on high`
turns it into one, which is what you want in a project's own CI rather than here.

Not shadscan. `shadscan` audits a React app for UI fundamentals — a11y, empty and
error states, responsive shell — and is the right tool for "is this app any good".
This asks a narrower question: did `design-md-to-app` obey `design-md-to-app`?
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

CODE_SUFFIXES = {".tsx", ".ts", ".jsx", ".js", ".css", ".mdx"}
# `.claude` holds agent worktrees (whole copies of the app) and project skills: grading them counts
# every finding once per worktree — the first run of the copy checks reported smart-travel three times.
SKIP_DIRS = {"node_modules", ".next", ".git", "dist", "build", ".turbo", "coverage", ".vercel", ".claude"}

# Vendored by the shadcn / Base UI CLI, not written by the generation. Grading them
# grades upstream: the first real run spent 20 of 26 findings inside components/ui/,
# every one of them someone else's code. `--include-vendored` turns them back on.
VENDORED = ("components/ui/", "packages/ui/src/components/ui/", "src/components/ui/")


@dataclass
class Finding:
    check: str
    severity: str
    file: str
    line: int
    excerpt: str
    note: str = ""


@dataclass
class Target:
    """Everything a check may look at, read once."""

    root: Path
    files: list[tuple[Path, str]] = field(default_factory=list)
    include_vendored: bool = False

    def code(self):
        for path, text in self.files:
            if path.suffix in CODE_SUFFIXES:
                yield path, text

    def copy(self):
        """Where a visitor's words live: code and the **English** message catalogues (the copy patterns are
        English — "elevate" is filler in en.json and an ordinary adjective in it.json). Tests and the showcase
        (the design system's specimen page, ours, not the client's copy) are not copy."""
        for path, text in self.files:
            rel = self.rel(path)
            if any(m in rel for m in NOT_COPY):
                continue
            if path.suffix in CODE_SUFFIXES or (_is_messages(path) and _english(path)):
                yield path, text

    def rel(self, path: Path) -> str:
        try:
            return str(path.relative_to(self.root))
        except ValueError:
            return str(path)

    def has(self, *names: str) -> bool:
        return any((self.root / n).exists() for n in names)

    def named(self, *names: str) -> list[Path]:
        """Loaded files with one of these names, anywhere under the root."""
        return [p for p, _ in self.files if p.name in names]


def _skipped(path: Path, include_vendored: bool = False) -> bool:
    if any(part in SKIP_DIRS for part in path.parts):
        return True
    if include_vendored:
        return False
    posix = path.as_posix()
    return any(marker in posix for marker in VENDORED)


def _is_messages(path: Path) -> bool:
    return path.suffix == ".json" and "messages" in path.parts


def _english(path: Path) -> bool:
    """messages/en.json, messages/en-US.json, messages/en/Account.json."""
    parts = path.parts[path.parts.index("messages") + 1:]
    return bool(parts) and parts[0].split(".")[0].lower().split("-")[0] == "en"


NOT_COPY = ("__tests__/", ".test.", ".spec.", "tests/", "e2e/", "showcase")


def load(root: Path, include_vendored: bool = False) -> Target:
    target = Target(root=root, include_vendored=include_vendored)
    # os.walk, pruning SKIP_DIRS before descending: rglob walked every node_modules and dropped it
    # afterwards, and one real project took over two minutes to grade.
    paths = []
    for here, dirs, names in os.walk(root):
        dirs[:] = sorted(d for d in dirs if d not in SKIP_DIRS)
        paths += [Path(here) / n for n in names]
    for path in sorted(paths):
        if _skipped(path, include_vendored):
            continue
        if path.suffix not in CODE_SUFFIXES and path.name not in {"package.json"} and not _is_messages(path):
            continue
        try:
            target.files.append((path, path.read_text(encoding="utf-8", errors="replace")))
        except OSError:
            continue
    return target


# ─── the rules ────────────────────────────────────────────────────────────────
#
# Each is (id, severity, human description, fn). A rule earns its place only if a
# reviewer could point at the line it fires on. Anything that needs taste to
# adjudicate belongs in the blind A/B in README.md, not here.

CHECKS: list[tuple[str, str, str, object]] = []


def check(cid: str, severity: str, description: str):
    def wrap(fn):
        CHECKS.append((cid, severity, description, fn))
        return fn

    return wrap


def _scan(target: Target, pattern: re.Pattern, cid: str, severity: str, note="", source=None):
    out = []
    for path, text in (source if source is not None else target.code()):
        for m in pattern.finditer(text):
            line = text.count("\n", 0, m.start()) + 1
            excerpt = text.splitlines()[line - 1].strip()[:120] if text else ""
            out.append(Finding(cid, severity, target.rel(path), line, excerpt, note))
    return out


# `bg-black/10` is a scrim, not the page's ink — rule 1 is about the ground and the
# text, so an explicitly transparent black is left alone.
PURE_BLACK = re.compile(
    r"#000000\b|#000\b|\boklch\(\s*0\s+0\s+0\s*\)|\bbg-black(?![\w/-])|\btext-black(?![\w/-])")


# Severity depends on where it sits. `#000` inside a className or a CSS declaration
# is the page's ink and is what rule 1 is about; the same string as a fallback in a
# colour-picker's data model is data, and the first field run produced four of those
# from one SVG recolouring engine. Both are reported — one is worth acting on.
INK_CONTEXT = re.compile(r"className|class=|style|--[a-z-]+\s*:|\b(?:color|background|fill|stroke|border)\b",
                         re.IGNORECASE)


@check("pure-black", "medium", "pure #000 instead of an off-black (rule 1)")
def pure_black(t):
    findings = _scan(t, PURE_BLACK, "pure-black", "medium",
                     "use #0a0a0a / oklch(0.145 0 0), or var(--foreground) so the theme flip works")
    for f in findings:
        if not INK_CONTEXT.search(f.excerpt):
            f.severity = "low"
            f.note = ("not in an ink position — a colour-data default rather than the page's ink. "
                      "Legitimate to dismiss; counted so the dismissal is deliberate.")
    return findings


H_SCREEN = re.compile(r"\bh-screen\b|\bmin-h-screen\b")


@check("h-screen", "high", "h-screen / min-h-screen instead of min-h-[100dvh] (rule 2)")
def h_screen(t):
    return _scan(t, H_SCREEN, "h-screen", "high",
                 "mobile browser chrome makes 100vh taller than the viewport; 100dvh for a shell, 100svh for a hero")


PLACEHOLDER_NAMES = re.compile(r"\bJohn Doe\b|\bJane Smith\b|\bJane Doe\b|\bSarah Chan\b|\bJohn Smith\b")


@check("placeholder-name", "high", "a recognised AI-default person name (rule 3)")
def placeholder_name(t):
    return _scan(t, PLACEHOLDER_NAMES, "placeholder-name", "high",
                 "realistic and non-generic instead — mixed nationalities, diacritics, hyphens")


PLACEHOLDER_BRANDS = re.compile(r"\bAcme\b|\bNexus\b|\bSmartFlow\b|\bSynergy\b|\bApex\b")


@check("placeholder-brand", "high", "a banned filler brand name (rule 3)")
def placeholder_brand(t):
    return _scan(t, PLACEHOLDER_BRANDS, "placeholder-brand", "high",
                 "contextual and premium instead — the product's own world, not a stock word")


ROUND_STATS = re.compile(r'["\'>\s(](?:99\.99%|99%|50%|1,000,000|1234)["\'<\s),]')


@check("round-stat", "medium", "a too-round invented statistic (rule 3)")
def round_stat(t):
    return _scan(t, ROUND_STATS, "round-stat", "medium",
                 "sample data in an app screen: unround values, logged in fallbacks_applied. A statistic on a "
                 "public page is proof, and proof is never invented (rule 3)")


PLACEHOLDER_CONTACT = re.compile(r"\b\w+@example\.com\b|\b555-\d{4}\b")


@check("placeholder-contact", "medium", "example.com / 555- contact detail (rule 3)")
def placeholder_contact(t):
    return _scan(t, PLACEHOLDER_CONTACT, "placeholder-contact", "medium",
                 "realistic format instead — unless the Figma source shows it, which wins (Step 4.5c)")


FILLER_WORDS = re.compile(
    r"\b(Elevate|Unleash|Seamless|Seamlessly|Next-Gen|Empower|Streamline|"
    r"Game-changing|Revolutionary|Cutting-edge|Best-in-class|Supercharge|Effortless|Effortlessly)\b"
    r"|\bfast-paced world\b|\bnext level\b|\bLook no further\b|\bSay goodbye to\b", re.IGNORECASE)


@check("filler-word", "medium", "marketing filler in invented copy (rules 4 and 13)")
def filler_word(t):
    found = _scan(t, FILLER_WORDS, "filler-word", "medium",
                  "concrete verbs: 'Sign in', 'Send a message', 'Reset your password'", source=t.copy())
    return [f for f in found if not f.excerpt.startswith(COMMENT_PREFIXES)]


UNSPLASH = re.compile(r"images\.unsplash\.com|source\.unsplash\.com")


@check("unsplash-stub", "low", "Unsplash used for an invented stub photo (rule 5)")
def unsplash_stub(t):
    return _scan(t, UNSPLASH, "unsplash-stub", "low",
                 "picsum.photos/seed/<stable>/w/h is deterministic; tolerated when the user chose it")


# Deliberately narrow. The first field run matched Base UI class strings like
# `h-(--positioner-height)` next to the word `animate` and reported nine phantom
# violations, so this now wants a real declaration: a Tailwind utility that names
# the property, a CSS `transition`/`animation` shorthand listing it, or a
# @keyframes block that assigns it.
LAYOUT_PROPS = r"top|left|right|bottom|width|height|margin|padding"
LAYOUT_ANIMATION = re.compile(
    rf"\btransition-\[[^\]]*\b(?:{LAYOUT_PROPS})\b[^\]]*\]"
    rf"|\b(?:transition|animation)\s*:\s*[^;{{}}\n]*\b(?:{LAYOUT_PROPS})\b"
    rf"|@keyframes[^{{]*\{{[^}}]*\b(?:{LAYOUT_PROPS})\s*:", re.IGNORECASE)


@check("layout-animation", "medium", "animating a property that forces layout (rule 7)")
def layout_animation(t):
    return _scan(t, LAYOUT_ANIMATION, "layout-animation", "medium",
                 "animate transform and opacity only; translateY instead of top, scaleX instead of width")


SPINNER = re.compile(r"<Spinner\b|\bLoader2\b|\banimate-spin\b")


@check("spinner-default", "low", "a spinner where a content-shaped skeleton belongs (rule 9)")
def spinner_default(t):
    findings = []
    for path, text in t.code():
        if path.name not in {"loading.tsx", "loading.jsx"}:
            continue
        for m in SPINNER.finditer(text):
            line = text.count("\n", 0, m.start()) + 1
            findings.append(Finding("spinner-default", "low", t.rel(path), line,
                                    text.splitlines()[line - 1].strip()[:120],
                                    "<Skeleton> shaped like the content it replaces"))
    return findings


NUMBERED_EYEBROW = re.compile(r">\s*0[1-9]\s*<|\"0[1-9]\"\s*,\s*\"0[1-9]\"")


@check("numbered-sections", "low", "01 / 02 / 03 markers on non-sequential sections (rule 11)")
def numbered_sections(t):
    return _scan(t, NUMBERED_EYEBROW, "numbered-sections", "low",
                 "number a sequence the reader must follow in order; otherwise it is decoration")


DECORATIVE_GRADIENT = re.compile(r"\bbg-gradient-to-[a-z]{1,2}\b|\bbackdrop-blur\b|\bbg-clip-text\b")


@check("decorative-surface", "low", "gradient / glass surface where the source did not ask for one (rule 11)")
def decorative_surface(t):
    return _scan(t, DECORATIVE_GRADIENT, "decorative-surface", "low",
                 "bows to the source: if Figma shows it, keep it (Step 4.5c) — this only flags invented ones")


# Proof is what a visitor reads as a fact about the business: how many customers, how they rate
# it, who trusts it. A generator that writes "Trusted by 3,847 teams" has written a claim the
# client never made, and the more organic it looks the more likely it ships (rule 3).
INVENTED_PROOF = re.compile(
    r"\b(?:trusted|loved|relied on) by\b"
    r"|\bjoin(?:ed)?\s+(?:over\s+|more than\s+)?\d+(?:[,.]\d+)*\s*[kKM]?\+?"
    r"|\b\d+(?:[,.]\d+)*\s*[kKM]?\+?\s+(?:happy\s+|satisfied\s+)?(?:customers|clients|teams|companies|businesses)\b"
    r"|★{3,}|\b[1-5]\.\d\s*/\s*5\b|\b[1-5]\s*/\s*5\s+(?:stars|rating)\b|\bout of 5 stars\b", re.IGNORECASE)


@check("invented-proof", "medium", "proof written by the generator: customer counts, ratings, 'trusted by' (rule 3)")
def invented_proof(t):
    found = _scan(t, INVENTED_PROOF, "invented-proof", "medium",
                  "leave the slot empty with a TBD, or out, and list it in the hand-off — "
                  "unless the client supplied the figure, in which case cite where it came from", source=t.copy())
    return [f for f in found if not f.excerpt.startswith(COMMENT_PREFIXES)]


COMMENT_PREFIXES = ("*", "//", "/*", "{/*")
WATERMARK = re.compile(r"Generated by design-md-to-app")


@check("generator-watermark", "medium", "the generator's signature on a client's page (design-md-to-app footer)")
def generator_watermark(t):
    findings = []
    for f in _scan(t, WATERMARK, "generator-watermark", "medium",
                   "provenance lives in _design-md-mapping.json and /showcase, not on the client's site"):
        comment = f.excerpt.startswith(COMMENT_PREFIXES)
        if not comment and "showcase" not in f.file:
            findings.append(f)
    return findings


# A class string that starts content invisible and relies on an animation to show it. Without a
# motion-reduce: variant, a reduced-motion user (or a failed animation) keeps the content hidden.
CLASS_STRING = re.compile(r"""(?:className|class)\s*=\s*(?:\{\s*)?(["'`])(.*?)\1""", re.S)


@check("hidden-without-reduced-motion", "medium", "content starts at opacity-0 with no reduced-motion path (rule 10)")
def hidden_without_reduced_motion(t):
    findings = []
    for path, text in t.code():
        for m in CLASS_STRING.finditer(text):
            classes = m.group(2).split()
            if ("opacity-0" in classes and any(c.startswith("animate-") for c in classes)
                    and not any(c.startswith("motion-reduce:") for c in classes)):
                line = text.count("\n", 0, m.start()) + 1
                findings.append(Finding("hidden-without-reduced-motion", "medium", t.rel(path), line,
                                        text.splitlines()[line - 1].strip()[:120],
                                        "add motion-reduce:animate-none motion-reduce:opacity-100"))
    return findings


CHART_MODULE = re.compile(r"""from\s+["'](?:recharts|@/components/ui/chart|[^"']*/ui/chart)["']""")
GRADIENT_DEF = re.compile(r"<linearGradient\b|<radialGradient\b")
URL_FILL = re.compile(r"""fill\s*=\s*\{?\s*["'`]url\(#""")


@check("chart-gradient-fill", "low", "a chart area filled with a gradient (rule 12)")
def chart_gradient_fill(t):
    findings = []
    for path, text in t.code():
        if CHART_MODULE.search(text) and URL_FILL.search(text):
            findings += _scan(t, GRADIENT_DEF, "chart-gradient-fill", "low",
                              "a solid --chart-* fill at low opacity; the gradient is decoration (rule 11)",
                              source=[(path, text)])
    return findings


# ─── absences ─────────────────────────────────────────────────────────────────
#
# The rules above find something that should not be there. These find something
# that should be and is not, which is the failure mode nobody notices: a missing
# file produces no diff to review.


def _absent(cid: str, severity: str, note: str) -> list[Finding]:
    return [Finding(cid, severity, ".", 0, "(absent)", note)]


@check("i18n-missing", "high", "no i18n wiring, or fewer than the two required locales")
def i18n_missing(t):
    pkg = t.root / "package.json"
    declared = "next-intl" in pkg.read_text(errors="replace") if pkg.exists() else False
    messages = {p.stem for p, _ in t.files if _is_messages(p) and p.parent.name == "messages"}
    if not declared and not messages:
        return _absent("i18n-missing", "high",
                       "every frontend ships i18n (next-intl on web), minimum en + it")
    missing = {"en", "it"} - messages
    if missing:
        return _absent("i18n-missing", "high",
                       f"locale file(s) missing: {', '.join(sorted(missing))}")
    return []


@check("theme-missing", "high", "no dark/light theme system")
def theme_missing(t):
    for _, text in t.code():
        if "next-themes" in text or "ThemeProvider" in text or re.search(r"\bdark:", text):
            return []
    return _absent("theme-missing", "high",
                   "Step 4.6 is mandatory: both modes plus a toggle, unless the DESIGN.md opts out")


@check("robustness-missing", "medium", "no error.tsx / loading.tsx at any route level")
def robustness_missing(t):
    if t.named("error.tsx", "error.jsx"):
        if t.named("loading.tsx", "loading.jsx"):
            return []
    return _absent("robustness-missing", "medium",
                   "Step 4.8: an unhandled throw renders the framework's default error page")


@check("active-feedback-missing", "low", "no :active feedback anywhere on interactive elements")
def active_feedback_missing(t):
    for _, text in t.code():
        if "active:" in text:
            return []
    return _absent("active-feedback-missing", "low",
                   "rule 8: without it a click feels dead — active:scale-[0.98] costs nothing")


# ─── running ──────────────────────────────────────────────────────────────────

SEVERITIES = ["high", "medium", "low"]


def run(root: Path, include_vendored: bool = False) -> list[Finding]:
    target = load(root, include_vendored)
    findings: list[Finding] = []
    for cid, severity, _desc, fn in CHECKS:
        try:
            findings.extend(fn(target))
        except Exception as exc:  # a broken check must not look like a clean run
            findings.append(Finding(cid, "high", ".", 0, "(check raised)",
                                    f"{type(exc).__name__}: {exc}"))
    order = {s: i for i, s in enumerate(SEVERITIES)}
    findings.sort(key=lambda f: (order.get(f.severity, 9), f.check, f.file, f.line))
    return findings


def summarize(findings: list[Finding]) -> dict:
    by_check: dict[str, int] = {}
    by_severity: dict[str, int] = {s: 0 for s in SEVERITIES}
    for f in findings:
        by_check[f.check] = by_check.get(f.check, 0) + 1
        by_severity[f.severity] = by_severity.get(f.severity, 0) + 1
    return {"total": len(findings), "by_severity": by_severity, "by_check": by_check}


def report(findings: list[Finding], summary: dict, baseline: dict | None) -> None:
    if not findings:
        print("✓ no mechanical failures found")
    for f in findings:
        where = f.file if f.line == 0 else f"{f.file}:{f.line}"
        print(f"  [{f.severity:<6}] {f.check:<24} {where}")
        if f.excerpt and f.excerpt != "(absent)":
            print(f"           {f.excerpt}")
        if f.note:
            print(f"           → {f.note}")
    s = summary["by_severity"]
    print(f"\n{summary['total']} mechanical failure(s): "
          f"{s['high']} high · {s['medium']} medium · {s['low']} low")

    if baseline is None:
        return
    before, after = baseline["total"], summary["total"]
    delta = after - before
    arrow = "→" if delta == 0 else ("↓" if delta < 0 else "↑")
    print(f"baseline {before} {arrow} {after} ({delta:+d})")
    moved = []
    for cid in sorted(set(baseline["by_check"]) | set(summary["by_check"])):
        b, a = baseline["by_check"].get(cid, 0), summary["by_check"].get(cid, 0)
        if b != a:
            moved.append(f"  {cid:<24} {b} → {a}")
    if moved:
        print("per check:")
        print("\n".join(moved))
    else:
        print("no check moved — a count that does not move is not evidence of improvement")


# ─── self-test ────────────────────────────────────────────────────────────────
#
# The rule this whole session kept re-learning: a check nobody has watched fail is
# not a check. `fixtures/bad/` breaks every rule once, `fixtures/good/` breaks
# none. Every id must fire on the first and stay silent on the second — a check
# that cannot do both is either dead or a false-positive generator.


def selftest() -> int:
    here = Path(__file__).parent
    bad, good = run(here / "fixtures" / "bad"), run(here / "fixtures" / "good")
    fired = {f.check for f in bad}
    ids = [cid for cid, *_ in CHECKS]

    silent = [c for c in ids if c not in fired]
    noisy = sorted({f.check for f in good})

    for cid in ids:
        mark = "✓" if cid in fired and cid not in noisy else "✗"
        print(f"  {mark} {cid}")
    if silent:
        print(f"\n✗ never fired on fixtures/bad: {', '.join(silent)}", file=sys.stderr)
    if noisy:
        print(f"✗ fired on fixtures/good (false positive): {', '.join(noisy)}", file=sys.stderr)
    if silent or noisy:
        return 1
    print(f"\n✓ all {len(ids)} checks fire on bad and stay silent on good")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("root", nargs="?", help="the generated app to grade")
    ap.add_argument("--json", action="store_true", help="machine-readable, for a baseline file")
    ap.add_argument("--baseline", help="a previous --json run to compare against")
    ap.add_argument("--fail-on", choices=SEVERITIES, help="exit 1 at or above this severity")
    ap.add_argument("--selftest", action="store_true", help="check the checks against the fixtures")
    args = ap.parse_args()

    if args.selftest:
        return selftest()
    if not args.root:
        ap.error("give a directory to grade, or --selftest")

    root = Path(args.root).expanduser()
    if not root.is_dir():
        sys.stderr.write(f"not a directory: {root}\n")
        return 2

    findings = run(root)
    summary = summarize(findings)

    if args.json:
        print(json.dumps({"root": str(root), **summary,
                          "findings": [f.__dict__ for f in findings]}, indent=2))
    else:
        baseline = None
        if args.baseline:
            baseline = json.loads(Path(args.baseline).read_text())
        report(findings, summary, baseline)

    if args.fail_on:
        cutoff = SEVERITIES.index(args.fail_on)
        if any(SEVERITIES.index(f.severity) <= cutoff for f in findings):
            return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
