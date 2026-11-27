#!/usr/bin/env python3
"""check_handmade_ui.py — golden rule 3 without ESLint: refuse hand-built HTML the chosen library already ships.

Usage:
    python3 check_handmade_ui.py <root>              # scan the app code; exit 0 clean, 1 violations
    python3 check_handmade_ui.py --install <root>    # copy this file to <root>/scripts/ and chain it into `lint`
    python3 check_handmade_ui.py --wired <root>      # exit 0 if <root>'s `lint` script runs it, 1 if not
    python3 check_handmade_ui.py --self-test         # every rule refuses its case; the exceptions pass

Why it exists. Golden rule 3 is enforced by `@shadcn/lint` (`design/no-handmade-ui`) and the write-time guard.
Both are ESLint-shaped. A project that cannot run ESLint records `stack.design_lint = "none"` with a reason —
Agentic Factory did (typescript-eslint refused TypeScript 7, the repo lints with Biome) — and until 2026-11-27 that
reasoned opt-out took every enforcement of the rule with it. Six screens of that project were then built by hand
with Tailwind beside the registry it had chosen (ui-agent), and nobody noticed until the user did. This check has no
dependency but Python, so an opt-out of the lint is no longer an opt-out of the rule: `design_lint_gate.py` accepts
`design_lint: "none"` only with this check wired, or with its own recorded reason.

What it reads: every .tsx/.jsx in the app code — `app/`, `components/`, `src/` at the root and under `apps/*/` —
never `packages/ui` or `components/ui`, where the primitives themselves legitimately render raw elements.

What it refuses (each one a primitive every supported library ships):

    <table …>                           → Table
    <textarea …>                        → Textarea / InputGroupTextarea
    <select …>                          → Select / NativeSelect
    <input …> (not type="hidden")       → Input / PasswordInput / InputGroupInput
    <progress …> / role="progressbar"   → Progress
    <dialog …>                          → Dialog / Drawer / Sheet

A line that must stay hand-built says why, on the same line or the line above: `ui-exception: <reason>`. The
reason is the record; a bare marker is refused. It is a floor, not the lint: a `div` whose classes redraw a Card is
still only caught by `design/no-handmade-ui` and by review.
"""

from __future__ import annotations

import json
import re
import shutil
import sys
import tempfile
from pathlib import Path

RULES: list[tuple[str, re.Pattern[str], str]] = [
    ("table", re.compile(r"<table[\s>]"), "Table"),
    ("textarea", re.compile(r"<textarea[\s>]"), "Textarea or InputGroupTextarea"),
    ("select", re.compile(r"<select[\s>]"), "Select / NativeSelect"),
    ("input", re.compile(r"<input(?![^>]*type=\"hidden\")[\s>/]"), "Input, PasswordInput or InputGroupInput"),
    ("progress", re.compile(r"<progress[\s>]|role=\"progressbar\""), "Progress"),
    ("dialog", re.compile(r"<dialog[\s>]"), "Dialog, Drawer or Sheet"),
]
EXCEPTION = re.compile(r"ui-exception:\s*(\S.*)?")
SOURCE_DIRS = ("app", "components", "src")
SKIP_PARTS = {"node_modules", ".next", "dist", "build", ".output"}
SCRIPT_NAME = "check_handmade_ui.py"


def app_dirs(root: Path) -> list[Path]:
    bases = [root, *sorted(p for p in (root / "apps").glob("*") if p.is_dir())] if (root / "apps").is_dir() else [root]
    return [b / d for b in bases for d in SOURCE_DIRS if (b / d).is_dir()]


def files(root: Path) -> list[Path]:
    out: list[Path] = []
    for d in app_dirs(root):
        for path in sorted([*d.rglob("*.tsx"), *d.rglob("*.jsx")]):
            rel = path.relative_to(root).parts
            if SKIP_PARTS & set(rel) or "ui" in rel and "components" in rel[: rel.index("ui")]:
                continue  # build output, or components/ui: the primitives themselves
            out.append(path)
    return out


def violations(root: Path) -> list[str]:
    found: list[str] = []
    for path in files(root):
        lines = path.read_text(encoding="utf-8").splitlines()
        for i, line in enumerate(lines):
            for name, pattern, use in RULES:
                if not pattern.search(line):
                    continue
                here = EXCEPTION.search(line) or (EXCEPTION.search(lines[i - 1]) if i else None)
                # The reason, without the comment's own closing marks: `{/* ui-exception: */}` has none.
                reason = re.sub(r"[\s*/}]+$", "", here.group(1) or "") if here else ""
                if reason:
                    continue
                why = " (an exception needs its reason)" if here else ""
                found.append(f"{path.relative_to(root)}:{i + 1}: hand-built <{name}> — use {use}{why}")
    return found


def lint_script(root: Path) -> str:
    try:
        return json.loads((root / "package.json").read_text(encoding="utf-8")).get("scripts", {}).get("lint", "")
    except (OSError, ValueError):
        return ""


def wired(root: Path) -> bool:
    return SCRIPT_NAME in lint_script(root) and (root / "scripts" / SCRIPT_NAME).exists()


def install(root: Path) -> int:
    pkg = root / "package.json"
    if not pkg.exists():
        print(f"no package.json at {root}")
        return 2
    (root / "scripts").mkdir(exist_ok=True)
    shutil.copyfile(Path(__file__), root / "scripts" / SCRIPT_NAME)
    data = json.loads(pkg.read_text(encoding="utf-8"))
    scripts = data.setdefault("scripts", {})
    step = f"python3 scripts/{SCRIPT_NAME} ."
    if SCRIPT_NAME not in scripts.get("lint", ""):
        scripts["lint"] = f"{scripts['lint']} && {step}" if scripts.get("lint") else step
        pkg.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"installed: scripts/{SCRIPT_NAME}, chained into `lint`")
    found = violations(root)
    if found:
        print(f"{len(found)} hand-built element(s) to replace or justify now:")
        for v in found:
            print(f"  {v}")
    return 0


def self_test() -> int:
    cases = {
        "apps/web/app/bad.tsx": '<table className="x">\n<textarea />\n<select>\n<input type="text" />\n'
        '<progress />\n<div role="progressbar" />\n<dialog open>\n',
        "apps/web/app/ok.tsx": '<input type="hidden" name="a" />\n'
        "{/* ui-exception: the browser's own file picker */}\n<input type=\"file\" />\n",
        "apps/web/app/bare.tsx": "<table> {/* ui-exception: */}\n",
        "apps/web/components/ui/table.tsx": "<table>\n",
        "packages/ui/src/components/table.tsx": "<table>\n",
    }
    failures: list[str] = []
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        for name, text in cases.items():
            (root / name).parent.mkdir(parents=True, exist_ok=True)
            (root / name).write_text(text, encoding="utf-8")
        got = violations(root)
        bad = [v for v in got if "bad.tsx" in v]
        if len(bad) != 7:
            failures.append(f"expected 7 refusals in bad.tsx, got {len(bad)}: {bad}")
        if [v for v in got if "ok.tsx" in v]:
            failures.append("a hidden input or a reasoned exception was refused")
        bare = [v for v in got if "bare.tsx" in v]
        if len(bare) != 1 or "needs its reason" not in bare[0]:
            failures.append(f"a bare exception marker was not refused: {bare}")
        if [v for v in got if "/ui/" in v]:
            failures.append("a primitive under components/ui or packages/ui was scanned")
        (root / "package.json").write_text('{"scripts": {"lint": "biome check ."}}\n', encoding="utf-8")
        if wired(root):
            failures.append("reported wired before --install")
        install(root)
        if not wired(root) or "biome check . && python3 scripts/" not in lint_script(root):
            failures.append(f"--install did not chain into lint: {lint_script(root)!r}")
    for f in failures:
        print(f"self-test FAILED: {f}")
    if not failures:
        print("self-test ok: 7 refusals; hidden input, reasoned exception and primitives allowed; "
              "bare marker refused; --install chains into lint")
    return 1 if failures else 0


def main(argv: list[str]) -> int:
    args = argv[1:]
    if args[:1] == ["--self-test"]:
        return self_test()
    if args[:1] == ["--install"]:
        return install(Path(args[1] if len(args) > 1 else ".").resolve())
    if args[:1] == ["--wired"]:
        return 0 if wired(Path(args[1] if len(args) > 1 else ".").resolve()) else 1
    root = Path(args[0] if args else ".").resolve()
    found = violations(root)
    for v in found:
        print(v)
    if found:
        print(f"handmade ui: {len(found)} hand-built element(s) the UI library already ships (golden rule 3)")
        return 1
    print("handmade ui: clean")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
