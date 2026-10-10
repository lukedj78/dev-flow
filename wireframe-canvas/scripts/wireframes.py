#!/usr/bin/env python3
"""The wireframe step as commands: check the screen inventory, record the user's approval, track the PNGs.

    wireframes.py coverage <root>                      every PRD story maps to >= 1 screen; every row has states
    wireframes.py approve  <root> --canvas-url <url> --user-said "<their words>" [--artboards N]
    wireframes.py skip     <root> --reason "..."       explicit opt-out, kept in meta.json
    wireframes.py pngs     <root>                      which docs/wireframes/png/<ID>-{desktop,phone}.png are missing
    wireframes.py targets  <root>                      story -> screens -> PNGs, as JSON
    wireframes.py comments <root> --repo O/N --ref <sha> --out <dir> [--map .workflow/github-issues.json]
                                                       one comment body per issue whose story maps to a screen
    wireframes.py posted   <root>                      record wireframes.screenshots_posted_at

`approve` and `skip` write `meta.json#wireframes`, which `dev-flow/scripts/update_meta.py set-phase` checks
before a project leaves `design_extracted` for the scaffold. Stdlib only. Exit 0 ok, 1 refused or gaps.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

INVENTORY = "docs/wireframes/screen-inventory.md"
PNG_DIR = "docs/wireframes/png"
STORY = re.compile(r"\bUS-\d+\b")
SCREEN_ID = re.compile(r"^[A-Z]{1,3}\d{1,3}[a-z]?$")


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def load(root: Path) -> tuple[Path, dict]:
    path = root / ".workflow" / "meta.json"
    if not path.is_file():
        sys.exit(f"No .workflow/meta.json at {root}")
    return path, json.loads(path.read_text())


def save(path: Path, meta: dict) -> None:
    meta["updated_at"] = now_iso()
    path.write_text(json.dumps(meta, indent=2, ensure_ascii=False) + "\n")


def cells(line: str) -> list[str]:
    return [c.strip() for c in line.strip().strip("|").split("|")]


def parse_inventory(text: str) -> list[dict]:
    """Rows of every table whose header has ID, Stories and States columns. Other tables are ignored."""
    rows, header = [], None
    for line in text.splitlines():
        if not line.lstrip().startswith("|"):
            header = None
            continue
        c = cells(line)
        if header is None:
            low = [x.lower() for x in c]
            if "id" in low and "stories" in low and "states" in low:
                header = low
            continue
        if all(set(x) <= set("-: ") for x in c):
            continue
        row = dict(zip(header, c))
        if SCREEN_ID.match(row.get("id", "")):
            rows.append({"id": row["id"], "screen": row.get("screen", ""), "stories": STORY.findall(row.get("stories", "")),
                         "states": row.get("states", "")})
    return rows


def prd_stories(root: Path) -> list[str]:
    prd = root / ".workflow" / "PRD.md"
    if not prd.is_file():
        return []
    return sorted(set(STORY.findall(prd.read_text())), key=lambda s: int(s[3:]))


def coverage(root: Path, inventory: str) -> tuple[list[dict], list[str]]:
    """(rows, problems)."""
    path = root / inventory
    if not path.is_file():
        return [], [f"{inventory} does not exist"]
    rows = parse_inventory(path.read_text())
    problems = []
    if not rows:
        problems.append(f"{inventory} has no screen rows (a table with ID | … | Stories | … | States columns)")
    ids = [r["id"] for r in rows]
    dupes = sorted({i for i in ids if ids.count(i) > 1})
    if dupes:
        problems.append(f"duplicate screen IDs: {', '.join(dupes)}")
    stories = prd_stories(root)
    if not stories:
        problems.append(".workflow/PRD.md has no US-N user stories to map the screens to")
    mapped = {s for r in rows for s in r["stories"]}
    missing = [s for s in stories if s not in mapped]
    if missing:
        problems.append(f"user stories with no screen: {', '.join(missing)}")
    unknown = sorted(mapped - set(stories), key=lambda s: int(s[3:]))
    if stories and unknown:
        problems.append(f"stories in the inventory that the PRD does not define: {', '.join(unknown)}")
    parsed = set(ids)
    skipped = sorted({c[0] for line in path.read_text().splitlines() if line.lstrip().startswith("|")
                      for c in [cells(line)] if c and SCREEN_ID.match(c[0]) and c[0] not in parsed})
    if skipped:
        problems.append("screen rows in tables without ID, Stories and States columns, so not counted: "
                        + ", ".join(skipped))
    no_states = [r["id"] for r in rows if not r["states"]]
    if no_states:
        problems.append(f"rows with an empty States cell (write — when a screen has none): {', '.join(no_states)}")
    return rows, problems


def missing_pngs(root: Path, rows: list[dict]) -> list[str]:
    return [f"{PNG_DIR}/{r['id']}-{v}.png" for r in rows for v in ("desktop", "phone")
            if not (root / PNG_DIR / f"{r['id']}-{v}.png").is_file()]


def cmd_coverage(a: argparse.Namespace) -> int:
    rows, problems = coverage(a.root, a.inventory)
    print(f"{len(rows)} screens, {len(prd_stories(a.root))} PRD stories, inventory {a.inventory}")
    for p in problems:
        print(f"  ✗ {p}")
    if not problems:
        print("  ✓ every story maps to at least one screen")
    return 1 if problems else 0


def cmd_approve(a: argparse.Namespace) -> int:
    rows, problems = coverage(a.root, a.inventory)
    if problems:
        print("Refused: the inventory is not complete, so the canvas cannot be.", file=sys.stderr)
        for p in problems:
            print(f"  ✗ {p}", file=sys.stderr)
        return 1
    artboards = a.artboards if a.artboards is not None else 2 * len(rows)
    if artboards < 2 * len(rows):
        print(f"Refused: {artboards} artboards for {len(rows)} screens — each needs desktop 1440 and phone 390.",
              file=sys.stderr)
        return 1
    if not a.user_said.strip():
        print("Refused: --user-said must quote the user's approval.", file=sys.stderr)
        return 1
    path, meta = load(a.root)
    wf = {k: v for k, v in (meta.get("wireframes") or {}).items() if k not in ("skipped", "reason")}
    wf.update({"canvas_url": a.canvas_url, "inventory": a.inventory, "screens": len(rows), "artboards": artboards,
               "approved_at": now_iso(), "approved_by_user": True, "approval_quote": a.user_said.strip()})
    wf.setdefault("screenshots_posted_at", None)
    meta["wireframes"] = wf
    save(path, meta)
    print(f"wireframes approved: {len(rows)} screens, {artboards} artboards, {a.canvas_url}")
    return 0


def cmd_skip(a: argparse.Namespace) -> int:
    if not a.reason.strip():
        print("Refused: a skip needs a reason.", file=sys.stderr)
        return 1
    path, meta = load(a.root)
    meta["wireframes"] = {"skipped": True, "reason": a.reason.strip(), "recorded_at": now_iso()}
    save(path, meta)
    print(f"wireframes skipped: {a.reason.strip()}")
    return 0


def cmd_pngs(a: argparse.Namespace) -> int:
    rows, _ = coverage(a.root, a.inventory)
    missing = missing_pngs(a.root, rows)
    print(f"{2 * len(rows) - len(missing)}/{2 * len(rows)} PNGs present in {PNG_DIR}/")
    for m in missing:
        print(f"  ✗ {m}")
    return 1 if missing or not rows else 0


def cmd_targets(a: argparse.Namespace) -> int:
    rows, _ = coverage(a.root, a.inventory)
    out: dict[str, list[dict]] = {}
    for r in rows:
        for s in r["stories"]:
            out.setdefault(s, []).append({"id": r["id"], "screen": r["screen"],
                                          "desktop": f"{PNG_DIR}/{r['id']}-desktop.png",
                                          "phone": f"{PNG_DIR}/{r['id']}-phone.png"})
    print(json.dumps(dict(sorted(out.items(), key=lambda kv: int(kv[0][3:]))), indent=2, ensure_ascii=False))
    return 0


def task_stories(tasks_md: str) -> list[dict]:
    """prd-to-tasks format: `## Epic: … (US-n)` headings, optional `### US-n:` headings, `- [ ] **Title** — body`.
    A task inherits the stories named by its epic heading and its story heading, plus any in its own text."""
    out, epic, story, cur = [], [], [], None
    for line in tasks_md.splitlines():
        if line.startswith("## "):
            epic, story, cur = STORY.findall(line), [], None
        elif line.startswith("### "):
            story, cur = STORY.findall(line), None
        elif m := re.match(r"^- \[( |x)\] \*\*(.+?)\*\* — (.*)$", line):
            cur = {"title": m.group(2), "stories": list(dict.fromkeys(epic + story + STORY.findall(line)))}
            out.append(cur)
        elif cur and line.startswith("  "):
            cur["stories"] = list(dict.fromkeys(cur["stories"] + STORY.findall(line)))
        elif line.strip():
            cur = None
    return out


def comment_body(screens: list[dict], repo: str, ref: str) -> str:
    base = f"https://github.com/{repo}/blob/{ref}"
    lines = ["**Wireframes** — approved canvas, the screens this issue's user story touches.", ""]
    for r in screens:
        lines += [f"### {r['id']} · {r['screen']}", "",
                  f"![{r['id']} desktop]({base}/{PNG_DIR}/{r['id']}-desktop.png?raw=true)",
                  f"![{r['id']} phone]({base}/{PNG_DIR}/{r['id']}-phone.png?raw=true)", ""]
    lines.append(f"Inventory: [`{INVENTORY}`]({base}/{INVENTORY})")
    return "\n".join(lines) + "\n"


def cmd_comments(a: argparse.Namespace) -> int:
    rows, _ = coverage(a.root, a.inventory)
    by_story: dict[str, list[dict]] = {}
    for r in rows:
        for s_ in r["stories"]:
            by_story.setdefault(s_, []).append(r)
    tasks_path = a.root / a.tasks
    if not tasks_path.is_file():
        print(f"Refused: {a.tasks} does not exist.", file=sys.stderr)
        return 1
    issue_map = json.loads((a.root / a.map).read_text()) if a.map else {}
    out = a.out if a.out.is_absolute() else a.root / a.out
    out.mkdir(parents=True, exist_ok=True)
    plan, unmapped = [], []
    for t in task_stories(tasks_path.read_text()):
        screens = list({r["id"]: r for s_ in t["stories"] for r in by_story.get(s_, [])}.values())
        if not screens:
            continue
        key = str(issue_map.get(t["title"], "")) if a.map else t["title"]
        if not key:
            unmapped.append(t["title"])
            continue
        name = re.sub(r"[^A-Za-z0-9]+", "-", key).strip("-")[:60] or "task"
        (out / f"{name}.md").write_text(comment_body(screens, a.repo, a.ref))
        plan.append({"issue": key, "title": t["title"], "screens": [r["id"] for r in screens], "body": str(out / f"{name}.md")})
    print(json.dumps({"comments": plan, "tasks_without_an_issue": unmapped}, indent=2, ensure_ascii=False))
    return 0


def cmd_posted(a: argparse.Namespace) -> int:
    path, meta = load(a.root)
    wf = meta.get("wireframes") or {}
    if wf.get("approved_by_user") is not True:
        print("Refused: the canvas is not approved yet; screenshots go on the issues after approval.", file=sys.stderr)
        return 1
    rows, _ = coverage(a.root, wf.get("inventory") or a.inventory)
    missing = missing_pngs(a.root, rows)
    if missing:
        print(f"Refused: {len(missing)} PNGs missing, e.g. {missing[0]}", file=sys.stderr)
        return 1
    wf["screenshots_posted_at"] = now_iso()
    meta["wireframes"] = wf
    save(path, meta)
    print(f"wireframes.screenshots_posted_at = {wf['screenshots_posted_at']}")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="op", required=True)
    specs = {
        "coverage": cmd_coverage, "approve": cmd_approve, "skip": cmd_skip,
        "pngs": cmd_pngs, "targets": cmd_targets, "comments": cmd_comments, "posted": cmd_posted,
    }
    for name, fn in specs.items():
        p = sub.add_parser(name)
        p.add_argument("root", type=Path)
        p.add_argument("--inventory", default=INVENTORY)
        if name == "approve":
            p.add_argument("--canvas-url", required=True)
            p.add_argument("--user-said", required=True, help="the user's approval, quoted")
            p.add_argument("--artboards", type=int, default=None)
        if name == "comments":
            p.add_argument("--repo", required=True, help="OWNER/NAME, for the image URLs")
            p.add_argument("--ref", required=True, help="the commit SHA that holds the PNGs (pinned, not a branch)")
            p.add_argument("--out", type=Path, required=True, help="directory for the comment bodies")
            p.add_argument("--tasks", default=".workflow/tasks.md")
            p.add_argument("--map", default=None, help="task title -> issue number (make_issues.py's map); "
                                                       "omitted, bodies are keyed by task title")
        if name == "skip":
            p.add_argument("--reason", required=True)
        p.set_defaults(func=fn)
    a = ap.parse_args(argv)
    a.root = a.root.resolve()
    return a.func(a)


if __name__ == "__main__":
    sys.exit(main())
