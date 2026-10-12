#!/usr/bin/env python3
"""Install the write-time primitives guard into a dev-flow web project, or check that it is.

    setup_primitives_guard.py <project-root>            install + wire + record (idempotent)
    setup_primitives_guard.py <project-root> --check    verify only, change nothing (exit 1 if not)

Golden rule 3 (dev-flow contracts.md), «the primitive wins»: every piece of UI is a primitive from the
declared library, used as it is. The lint rule design/no-handmade-ui (written by setup_design_lint.py)
finds hand-made UI after the fact; this guard refuses it **while the agent writes**:

  scripts/guard/primitives-guard.mjs   PreToolUse on Write|Edit|MultiEdit — refuses (exit 2) a write that
                                       adds a design/no-handmade-ui or design/no-card-in-card finding;
                                       Stop / SubagentStop — the same on every changed .tsx against HEAD
  scripts/guard/eslint.guard.mjs       the two rules only, imported from the project's preset (~1 s a file)
  scripts/guard/guard.json             the units: app dir, preset, primitives dir, ignores, rules
  .claude/settings.json                the hooks, merged into what is there, nothing removed
  AGENTS.md (and CLAUDE.md if it does not import AGENTS.md)   the rule every agent reads first

and records `stack.primitives_guard = "installed"`. Opt-out: `"none"` with
`stack_config.primitives_guard_reason`. Why: smart-travel, 2026-10-12 — 238 hand-made elements built in
three days against a green lint, 57 of 71 buttons in one night of parallel agents. The guard ran there
first (commit 6127a7c); this is it generalised (units for a monorepo, parser resolved through pnpm).

Normally run by setup_design_lint.py, after the preset exists; standalone it is the retrofit for a project
whose preset already has the rule.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import setup_design_lint as sdl  # noqa: E402

ASSETS = HERE.parent / "assets" / "guard"
GUARD_DIR = Path("scripts") / "guard"
COPIED = ("primitives-guard.mjs", "eslint.guard.mjs")
CMD = 'node "$CLAUDE_PROJECT_DIR"/scripts/guard/primitives-guard.mjs'
HOOKS = {
    "PreToolUse": {"matcher": "Write|Edit|MultiEdit",
                   "hooks": [{"type": "command", "command": f"{CMD} pre", "timeout": 30}]},
    "Stop": {"hooks": [{"type": "command", "command": f"{CMD} stop", "timeout": 60}]},
    "SubagentStop": {"hooks": [{"type": "command", "command": f"{CMD} stop", "timeout": 60}]},
}
BEGIN = "<!-- BEGIN:primitives-first -->"
END = "<!-- END:primitives-first -->"


def agents_section(components: str) -> str:
    return f"""{BEGIN}
# UI: only the primitives (golden rule 3, «the primitive wins»)

Every piece of UI is a primitive from `{components}/`, used as it is: list that directory and read
design-md-to-app's `references/primitives-first.md` (pattern → primitive) before writing any component. No
hand-written `<button>`, `<label>`, `<input>`, `<a>`, `<hr>`, `<img>`, `<details>`, no hand-written ARIA role
(tab, radio, menu…), and no `div`/`span` whose classes redraw a Card, Badge, Alert or Separator. When a board
looks slightly different from the primitive, the primitive wins and the board is corrected. **When no
primitive or existing variant fits, stop and ask the user** — propose the variant for DESIGN.md; never write
the element by hand, never `eslint-disable`. Allowed raw: an element passed as a primitive's `render` (or
under `asChild`), an `<a>` styled by `buttonVariants` (download, `tel:`, `mailto:`), a hidden or file input,
an sr-only table, an exception recorded in the preset's `designExceptions` with its reason.

A write-time guard enforces it (`.claude/settings.json` → `scripts/guard/primitives-guard.mjs`): a Write or
Edit that adds hand-made UI is refused with the primitive to use, and an agent cannot finish with hand-made UI
added through the shell. The lint rule `design/no-handmade-ui` checks the whole tree. A green lint or a
screenshot that matches the board is not proof of conformity: a hand-made button identical to the board
passes both.
{END}
"""


# ---------------------------------------------------------------------------------------
# Units
# ---------------------------------------------------------------------------------------

def guard_units(root: Path, units: list[dict]) -> list[dict]:
    """One entry per UI package the lint is spread into, with paths relative to the project root."""
    out = []
    for topo in units:
        # in a shadcn monorepo the primitives live in packages/ui; the apps import them from there
        ui_pkg = next((t for t in topo["targets"] if t.parent.name == "packages"), topo["targets"][0])
        components = (ui_pkg / sdl.component_dir(ui_pkg)).relative_to(root).as_posix()
        rules = {"design/no-handmade-ui": "error"}
        if sdl.card_in_card_applies(root):
            rules["design/no-card-in-card"] = "error"
        for t in topo["targets"]:
            out.append({
                "dir": t.relative_to(root).as_posix() or ".",
                "preset": topo["preset"].relative_to(root).as_posix(),
                "components": components,
                "ignores": [f"{sdl.component_dir(t)}/**", *sdl.HANDMADE_IGNORES],
                "rules": rules,
            })
    return out


# ---------------------------------------------------------------------------------------
# Wiring — safe to repeat
# ---------------------------------------------------------------------------------------

def write_if_changed(p: Path, text: str) -> bool:
    if p.exists() and p.read_text() == text:
        return False
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text)
    return True


def copy_assets(root: Path) -> list[str]:
    changed = []
    for name in COPIED:
        dst = root / GUARD_DIR / name
        if not dst.exists() or dst.read_bytes() != (ASSETS / name).read_bytes():
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ASSETS / name, dst)
            changed.append(name)
    return changed


def has_guard_hook(entries: list, event: str) -> bool:
    for e in entries or []:
        for h in (e or {}).get("hooks", []) or []:
            if "primitives-guard.mjs" in (h or {}).get("command", ""):
                return event != "PreToolUse" or re.search(r"\bWrite\b", (e or {}).get("matcher", "")) is not None
    return False


def merge_settings(root: Path) -> bool:
    """Add the three hooks to .claude/settings.json without removing or reordering anything."""
    p = root / ".claude" / "settings.json"
    try:
        data = json.loads(p.read_text()) if p.exists() else {}
    except json.JSONDecodeError as e:
        raise SystemExit(f"{p} is not valid JSON ({e}) — fix it by hand; the guard's hooks were not merged")
    hooks = data.setdefault("hooks", {})
    changed = False
    for event, entry in HOOKS.items():
        entries = hooks.setdefault(event, [])
        if not has_guard_hook(entries, event):
            entries.append(json.loads(json.dumps(entry)))
            changed = True
    if changed:
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")
    return changed


def write_section(p: Path, body: str, create: bool) -> str:
    s = p.read_text() if p.exists() else ""
    if not s and not create:
        return "absent"
    if BEGIN in s:
        new = re.sub(re.escape(BEGIN) + r".*?" + re.escape(END) + r"\n?", lambda _: body, s, flags=re.S)
    elif re.search(r"^#+\s*UI: only the .*primitives", s, re.M):
        return "hand-written"  # the project's own section (smart-travel wrote one first): left as is
    else:
        new = (s.rstrip() + "\n\n" if s.strip() else "") + body
    if new == s:
        return "unchanged"
    p.write_text(new)
    return "written"


def write_agents(root: Path, components: str) -> list[str]:
    body = agents_section(components)
    notes = [f"AGENTS.md: {write_section(root / 'AGENTS.md', body, create=True)}"]
    claude = root / "CLAUDE.md"
    # create-next-app@16 writes CLAUDE.md as `@AGENTS.md`: the section reaches Claude through the import
    if claude.exists() and "@AGENTS.md" not in claude.read_text():
        notes.append(f"CLAUDE.md: {write_section(claude, body, create=False)}")
    return notes


def record(root: Path) -> None:
    p = root / ".workflow" / "meta.json"
    if not p.exists():
        return
    m = json.loads(p.read_text())
    if m.get("stack", {}).get("primitives_guard") == "installed":
        return
    m.setdefault("stack", {})["primitives_guard"] = "installed"
    p.write_text(json.dumps(m, indent=2, ensure_ascii=False) + "\n")


def install(root: Path, units: list[dict] | None = None) -> int:
    meta = sdl.load_meta(root)
    ok, why = sdl.applicability(meta)
    if not ok:
        print(f"guard skipped — {why}")
        return 0
    units = units if units is not None else sdl.detect(root)
    if not units:
        print(f"cannot install the guard: {sdl.why_undetected(root)}", file=sys.stderr)
        return 2
    missing = [u["preset"] for u in units if not u["preset"].exists()
               or "designPlugin" not in u["preset"].read_text()]
    if missing:
        print("cannot install the guard: no designPlugin in " + ", ".join(str(m.relative_to(root)) for m in missing)
              + " — run setup_design_lint.py first (it writes the rule and calls this script)", file=sys.stderr)
        return 1
    gunits = guard_units(root, units)
    copied = copy_assets(root)
    cfg = write_if_changed(root / GUARD_DIR / "guard.json", json.dumps({"units": gunits}, indent=2) + "\n")
    hooks = merge_settings(root)
    notes = write_agents(root, gunits[0]["components"])
    record(root)
    print(f"  guard: {'copied ' + ', '.join(copied) if copied else 'scripts unchanged'} · guard.json "
          f"{'written' if cfg else 'unchanged'} · hooks {'merged' if hooks else 'already there'} · "
          + " · ".join(notes) + " · stack.primitives_guard = installed")
    return 0


# ---------------------------------------------------------------------------------------
# Check
# ---------------------------------------------------------------------------------------

def check(root: Path) -> tuple[bool, list[str]]:
    meta = sdl.load_meta(root)
    ok, why = sdl.applicability(meta)
    if not ok:
        return True, [f"guard not applicable: {why}"]
    decision = (meta.get("stack") or {}).get("primitives_guard")
    if decision == "none":
        reason = (meta.get("stack_config") or {}).get("primitives_guard_reason")
        return (True, [f"guard opted out: {reason}"]) if reason else (
            False, ['stack.primitives_guard is "none" without stack_config.primitives_guard_reason'])
    problems = []
    if decision != "installed":
        problems.append('stack.primitives_guard is not "installed"')
    for name in COPIED:
        f = root / GUARD_DIR / name
        if not f.exists():
            problems.append(f"{GUARD_DIR / name} is missing")
        elif f.read_bytes() != (ASSETS / name).read_bytes():
            problems.append(f"{GUARD_DIR / name} differs from design-md-to-app/assets/guard/{name}")
    try:
        gunits = json.loads((root / GUARD_DIR / "guard.json").read_text())["units"]
    except (OSError, KeyError, json.JSONDecodeError):
        gunits = []
        problems.append(f"{GUARD_DIR / 'guard.json'} is missing or unreadable")
    for u in gunits:
        preset = root / u.get("preset", "")
        if not preset.is_file() or "designPlugin" not in preset.read_text():
            problems.append(f"guard unit {u.get('dir')}: {u.get('preset')} does not export designPlugin")
        if "design/no-handmade-ui" not in (u.get("rules") or {}):
            problems.append(f"guard unit {u.get('dir')}: design/no-handmade-ui is not among its rules")
    try:
        hooks = json.loads((root / ".claude" / "settings.json").read_text()).get("hooks", {})
    except (OSError, json.JSONDecodeError):
        hooks = {}
    for event in HOOKS:
        if not has_guard_hook(hooks.get(event, []), event):
            problems.append(f".claude/settings.json has no {event} hook running primitives-guard.mjs")
    text = "".join((root / f).read_text() for f in ("AGENTS.md", "CLAUDE.md") if (root / f).exists())
    if BEGIN not in text and not re.search(r"^#+\s*UI: only the .*primitives", text, re.M):
        problems.append("AGENTS.md has no primitives-first section")
    return not problems, problems or ["primitives guard installed"]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("project_root", type=Path)
    ap.add_argument("--check", action="store_true", help="verify only; exit 1 if not installed")
    args = ap.parse_args()
    root = args.project_root.resolve()
    if args.check:
        ok, lines = check(root)
        for line in lines:
            print(("✓ " if ok else "✗ ") + line)
        return 0 if ok else 1
    return install(root)


if __name__ == "__main__":
    sys.exit(main())
