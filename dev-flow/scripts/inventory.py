#!/usr/bin/env python3
"""The inventory step as a command: look before you build, and write down that you looked.

    inventory.py scan   <keyword> [<keyword> ...]     step 1 of references/before-you-build.md, mechanically
    inventory.py record <project-root> --verdict V --searched S [S ...] [--not-covered N ...] [--summary T]

`scan` searches the places a person forgets: installed skills, plugins, **the other projects on this
machine** (name, PROJECT.md, PRD.md, README, package.json) and `references/resources.md`. It always
prints what it searched, and which root it could not read, so "found nothing" is never confused with
"could not look". `record` writes the verdict to `meta.json#inventory`, which `set-phase` checks before
a project leaves `idea_captured` (see inventory_gate.py).

Exit codes, same as research.py: 0 answered with hits, 3 answered and empty, 4 a root could not be read.
Stdlib only. `scan` reads and prints; it writes nothing.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

ANSWERED, EMPTY, UNREACHABLE = 0, 3, 4

VERDICTS = ("have-it", "adapts", "halfway", "build", "skipped")

HOME = Path.home()
HERE = Path(__file__).resolve().parent
PRUNE = {"node_modules", ".git", ".next", ".turbo", "dist", "build", "__pycache__", ".venv"}
PROJECT_FILES = (".workflow/PROJECT.md", ".workflow/PRD.md", ".workflow/meta.json", "README.md", "package.json")
MAX_PLUGIN_FILES = 3000
TOP = 8


def read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def match(text: str, keywords: list[str]) -> tuple[list[str], str]:
    """The keywords found in `text` and the first line carrying one.

    A keyword matches at the start of a word, not inside one: `tender` finds `tenders`, but `bando`
    does not find `abbandonato` or `abandoned` — the false hit that buried the real one on first run.
    """
    patterns = {k: re.compile(r"(?<!\w)" + re.escape(k), re.IGNORECASE) for k in keywords}
    found = [k for k, p in patterns.items() if p.search(text)]
    if not found:
        return [], ""
    for line in text.splitlines():
        if any(patterns[k].search(line) for k in found):
            return found, line.strip()[:160]
    return found, ""


def rank(hits: list[tuple[Path, list[str], str]]) -> list[tuple[Path, list[str], str]]:
    return sorted(hits, key=lambda h: (-len(h[1]), str(h[0])))[:TOP]


def scan_skills(root: Path, keywords: list[str]) -> list[tuple[Path, list[str], str]]:
    hits = []
    for skill in sorted(root.glob("*/SKILL.md")):
        found, line = match(read(skill), keywords)
        if found:
            hits.append((skill, found, line))
    return hits


def scan_plugins(root: Path, keywords: list[str]) -> list[tuple[Path, list[str], str]]:
    hits, seen = [], 0
    for base, dirs, files in os.walk(root, followlinks=True):
        dirs[:] = [d for d in dirs if d not in PRUNE]
        if "SKILL.md" in files:
            seen += 1
            found, line = match(read(Path(base) / "SKILL.md"), keywords)
            if found:
                hits.append((Path(base) / "SKILL.md", found, line))
        if seen >= MAX_PLUGIN_FILES:
            break
    return hits


def scan_projects(root: Path, keywords: list[str]) -> list[tuple[Path, list[str], str]]:
    hits = []
    for project in sorted(p for p in root.iterdir() if p.is_dir() and not p.name.startswith(".")):
        text = project.name + "\n" + "\n".join(read(project / f) for f in PROJECT_FILES)
        found, line = match(text, keywords)
        if found:
            hits.append((project, found, line or project.name))
    return hits


def scan_resources(path: Path, keywords: list[str]) -> list[tuple[Path, list[str], str]]:
    hits = []
    for line in read(path).splitlines():
        found, _ = match(line, keywords)
        if found:
            hits.append((path, found, line.strip()[:160]))
    return hits


def cmd_scan(a: argparse.Namespace) -> int:
    sources = [
        ("installed skills", a.skills, scan_skills),
        ("plugins", a.plugins, scan_plugins),
        ("projects on this machine", a.projects, scan_projects),
        ("resources already analysed", a.resources, scan_resources),
    ]
    keywords = a.keywords
    print(f"inventory scan — keywords: {', '.join(keywords)}\n")
    total, blind = 0, []
    for label, root, fn in sources:
        if not root.exists():
            blind.append(f"{label} ({root})")
            print(f"## {label}: NOT COVERED — {root} does not exist\n")
            continue
        try:
            hits = rank(fn(root, keywords))
        except OSError as e:
            blind.append(f"{label} ({root}: {e.strerror})")
            print(f"## {label}: NOT COVERED — {root}: {e.strerror}\n")
            continue
        total += len(hits)
        print(f"## {label}: {len(hits)} hit(s) in {root}")
        for path, found, line in hits:
            print(f"- {path}  [{', '.join(found)}]")
            if line:
                print(f"    {line}")
        print()
    print("Searched: " + ", ".join(label for label, root, _ in sources if root.exists()))
    if blind:
        print("Not covered: " + "; ".join(blind))
        print("  Write these into the plan. It is not the same as finding nothing.")
    print("\nSteps 2-4 (tools already paid for, the Claude ecosystem, outside) are not done by this command:")
    print("  see references/before-you-build.md, and research.py for the outside half.")
    if blind:
        return UNREACHABLE
    return ANSWERED if total else EMPTY


def cmd_record(a: argparse.Namespace) -> int:
    meta_path = a.project_root.resolve() / ".workflow" / "meta.json"
    if not meta_path.exists():
        sys.stderr.write(f"No {meta_path}. Run init_workflow.py first.\n")
        return 1
    if a.verdict == "skipped" and not (a.reason or "").strip():
        sys.stderr.write("--verdict skipped needs --reason: a skipped inventory is allowed, an unexplained one is not.\n")
        return 1
    if a.verdict != "skipped" and not a.searched:
        sys.stderr.write("--searched is required: name what you looked at, including the channels that gave nothing.\n")
        return 1
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    meta["inventory"] = {
        "verdict": a.verdict,
        "summary": a.summary or "",
        "searched": a.searched or [],
        "not_covered": a.not_covered or [],
        "reason": a.reason or "",
        "ran_at": now,
    }
    meta.setdefault("history", []).append({
        "skill": "dev-flow",
        "action": "inventory",
        "inputs": {"searched": a.searched or [], "not_covered": a.not_covered or []},
        "outputs": {"verdict": a.verdict},
        "phase_after": meta.get("phase", "empty"),
        "ran_at": now,
    })
    meta["updated_at"] = now
    meta_path.write_text(json.dumps(meta, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"inventory recorded: {a.verdict}")
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("scan", help="step 1: search the house, mechanically")
    s.add_argument("keywords", nargs="+", help="two or three words for the same idea; one term finds half the things")
    s.add_argument("--skills", type=Path, default=HOME / ".claude" / "skills")
    s.add_argument("--plugins", type=Path, default=HOME / ".claude" / "plugins")
    s.add_argument("--projects", type=Path, default=HOME / "projects")
    s.add_argument("--resources", type=Path, default=HERE.parent / "references" / "resources.md")

    r = sub.add_parser("record", help="write the verdict into meta.json#inventory")
    r.add_argument("project_root", type=Path)
    r.add_argument("--verdict", required=True, choices=VERDICTS)
    r.add_argument("--summary")
    r.add_argument("--searched", nargs="*")
    r.add_argument("--not-covered", nargs="*", dest="not_covered")
    r.add_argument("--reason", help="required with --verdict skipped")

    a = p.parse_args(argv)
    return {"scan": cmd_scan, "record": cmd_record}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
