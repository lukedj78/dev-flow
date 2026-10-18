#!/usr/bin/env python3
"""github_sync.py — push tasks.md to GitHub Issues the scrum way: one issue per open task, recorded by task_key.

    github_sync.py <project-root> --repo OWNER/NAME [--milestone "Sprint 1 — <goal>"] [--footer TEXT] [--dry-run]

On GitHub a sprint is one milestone named by its goal, and every issue carries `priority: Pn` (the user's rule,
2026-10-14), plus `estimate: N` (Fibonacci, from the task's `Estimated:` hint) and the `area:` / `tipo:` labels.
The repository's existing labels are reused, compared without case; only missing ones are created. Each issue is
written into meta.json#tracker.issue_map (keyed by task_key) as soon as it exists, so a run that stops halfway resumes
without duplicates. `--dry-run` only reads (the label and milestone lists). Bodies are the skeleton the agent then
rewrites to `references/issue-standard.md`. Needs `gh` logged in. Stdlib only.
"""
import argparse
import json
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import meta_io  # noqa: E402
from meta_tracker import legacy_shape, migrate, record_issues  # noqa: E402
from task_key import task_key  # noqa: E402

PALETTE = ["0b5d57", "1d76db", "4a3fc9", "9a5b00", "0e8a16", "5319e7", "b60205", "d93f0b", "fbca04", "c5def5", "bfd4f2", "6e7781", "000000"]
TYPES = {"page": ("tipo: pagina", "0075ca"), "agent": ("tipo: agente", "4a3fc9"), "backend": ("tipo: backend", "1b6e43"),
         "spike": ("tipo: spike", "fef2c0"), "setup": ("tipo: setup", "6e7781")}
SKIP = ("Non-goals", "Open questions")
FIBONACCI = ((2, 1), (4, 2), (8, 3), (24, 5), (40, 8))
HOURS = {"h": 1, "d": 8, "w": 40}


def parse(text):
    tasks, epic, cur = [], None, None
    for line in text.splitlines():
        if line.startswith("## "):
            epic, cur = line[3:].strip(), None
            continue
        m = re.match(r"^- \[( |x)\] \*\*(.+?)\*\* — (.*)$", line)
        if m:
            cur = {"done": m.group(1) == "x", "title": m.group(2), "body": m.group(3), "epic": epic, "extra": [],
                   "line": line}
            tasks.append(cur)
        elif cur and line.startswith("  "):
            cur["extra"].append(line)
        elif line.strip() and not line.startswith("  "):
            cur = None
    return [t for t in tasks if t["epic"] and not t["epic"].startswith(SKIP)]


def area_label(epics_in_order, epic):
    name = re.sub(r"^Epic:\s*", "", epic)
    name = re.split(r" \(|·", name)[0].strip().lower()
    name = name.replace(",", "")  # GitHub rejects commas in label names (HTTP 422)
    return f"area: {name}"[:50], PALETTE[epics_in_order.index(epic) % len(PALETTE)]


def type_of(t):
    ex = "\n".join(t["extra"])
    if t["title"].lower().startswith("spike"):
        return TYPES["spike"]
    if "screenshot-to-page" in t["body"]:
        return TYPES["page"]
    if "agent/" in ex or "agent/" in t["body"]:
        return TYPES["agent"]
    if t["epic"].lower().startswith("setup"):
        return TYPES["setup"]
    return TYPES["backend"]


def body_of(t, tasks_path, extra_footer=""):
    out = [t["body"], ""] + [l[2:] for l in t["extra"]]
    out += ["", "---", f"Area: **{t['epic']}**", f"Tracked in `{tasks_path}`." + (" " + extra_footer if extra_footer else "")]
    return "\n".join(out)


def points(hint: str):
    """An `Estimated:` hint (`4h`, `2-8h`, `1d`, `2-3d`, `1w`) → the Fibonacci point (the upper bound decides); None
    when it is not a duration."""
    m = re.search(r"(\d+(?:\.\d+)?)\s*(?:-\s*(\d+(?:\.\d+)?))?\s*([hdw])", hint.lower())
    if not m:
        return None
    hours = float(m.group(2) or m.group(1)) * HOURS[m.group(3)]
    return next((p for limit, p in FIBONACCI if hours <= limit), 13)


def _hint(t, name):
    m = re.search(rf"{name}:\s*([^\n]+)", "\n".join(t["extra"]))
    return m.group(1).strip() if m else None


def gh(*args):
    return subprocess.run(["gh", *args], capture_output=True, text=True)


def _record(meta_path: Path, mapping: dict, repo: str) -> None:
    """The issue, and — when not yet recorded — that the project is on GitHub, in this repo."""
    with meta_io.locked(meta_path.parent):
        meta = record_issues(meta_io.read_meta(meta_path), mapping)
        t = meta["tracker"]
        t.setdefault("provider", "github")
        t.setdefault("project", {}).setdefault("repo", repo)
        meta_io.write_json(meta_path, meta)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("root", type=Path)
    ap.add_argument("--repo", required=True)
    ap.add_argument("--milestone", help="the sprint's milestone, named by its goal; created when missing")
    ap.add_argument("--footer", default="", help="one line appended to every issue (e.g. a link to the design)")
    ap.add_argument("--pause", type=float, default=2.0, help="seconds between creations (GitHub content limits)")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args(argv)

    meta_path = a.root / ".workflow" / "meta.json"
    tasks_path = a.root / ".workflow" / "tasks.md"
    meta = meta_io.load_or_exit(meta_path)
    why = legacy_shape(meta, a.root)
    if why:
        # an older map (make_issues.py's file, a title-keyed or `linear` block) must be read first, or every issue
        # already on GitHub would be created again; --dry-run migrates in memory only
        print(f"meta.json has {why} — migrating it first (nothing is dropped)")
        if a.dry_run:
            meta, notes = migrate(meta, a.root)
        else:
            with meta_io.locked(meta_path.parent):
                meta, notes = migrate(meta_io.read_meta(meta_path), a.root)
                meta_io.write_json(meta_path, meta)
        for n in notes:
            print(f"  · {n}")
    t = meta.get("tracker") or {}
    if t.get("provider") not in (None, "github"):
        print(f"refused: this project's tracker is {t['provider']} (meta.json#tracker.provider), not GitHub", file=sys.stderr)
        return 2
    repo = (t.get("project") or {}).get("repo")
    if repo and repo.lower() != a.repo.lower():
        print(f"refused: meta.json#tracker.project.repo is {repo}, not {a.repo}", file=sys.stderr)
        return 2
    issue_map = t.get("issue_map") or {}
    tasks = [t for t in parse(tasks_path.read_text(encoding="utf-8")) if not t["done"]]
    todo = [t for t in tasks if task_key(t["line"]) not in issue_map]
    epics = list(dict.fromkeys(t["epic"] for t in tasks))

    r = gh("label", "list", "--repo", a.repo, "--json", "name", "--limit", "500")
    if r.returncode:
        print("could not list labels:", r.stderr.strip())
        return 1
    existing = {x["name"].lower(): x["name"] for x in json.loads(r.stdout or "[]")}

    def label(name: str, color: str, wanted: dict) -> str:
        """The repo's own spelling when it has the label; otherwise the name, queued for creation."""
        if name.lower() in existing:
            return existing[name.lower()]
        wanted[name] = color
        return name

    wanted: dict = {}
    plans = []
    defaulted = []
    for t in todo:
        names = [label(*area_label(epics, t["epic"]), wanted), label(*type_of(t), wanted)]
        pts = points(_hint(t, "Estimated") or "")
        if pts:
            names.append(label(f"estimate: {pts}", "c5def5", wanted))
        if not _hint(t, "Priority"):
            defaulted.append(t["title"])
        prio = (_hint(t, "Priority") or "P2").split()[0].upper()
        names.append(label(f"priority: {prio if re.fullmatch(r'P[0-3]', prio) else 'P2'}", "d93f0b", wanted))
        plans.append((t, names))

    milestone_missing = False
    if a.milestone:
        r = gh("api", "--paginate", "--jq", ".[].title", f"repos/{a.repo}/milestones?state=all&per_page=100")
        if r.returncode:
            print("could not list milestones:", r.stderr.strip())
            return 1
        milestone_missing = a.milestone not in {line.strip() for line in r.stdout.splitlines()}

    print(f"{len(tasks)} open tasks, {len(issue_map)} already on GitHub, {len(todo)} to create; "
          f"{len(wanted)} label(s) to create" + (f"; milestone {a.milestone!r} to create" if milestone_missing else ""))
    if defaulted:
        print(f"⚠ {len(defaulted)} task(s) have no `Priority:` hint and get priority: P2 — set the bands (P1–P3) "
              "in tasks.md or on the issues: " + ", ".join(defaulted[:10]) + (" …" if len(defaulted) > 10 else ""))
    unmatched = (meta.get("tracker") or {}).get("unmatched") or {}
    if unmatched:
        print(f"⚠ {len(unmatched)} issue(s) whose title is no longer in tasks.md (tracker.unmatched) — an edited title "
              "would be created again: link each with meta_tracker.py record-issues first: "
              + ", ".join(f"{k} → {v}" for k, v in list(unmatched.items())[:10]))
    if a.dry_run:
        for t, names in plans:
            print(f"  + {t['title']}  [{', '.join(names)}]")
        return 0

    for name, color in wanted.items():
        r = gh("label", "create", name, "--repo", a.repo, "--color", color)
        if r.returncode:
            print("label failed:", name, r.stderr.strip())
            return 1
    if milestone_missing:
        r = gh("api", f"repos/{a.repo}/milestones", "-f", f"title={a.milestone}")
        if r.returncode:
            print("milestone failed:", a.milestone, r.stderr.strip())
            return 1

    with tempfile.TemporaryDirectory() as tmp:
        body_file = Path(tmp) / "body.md"
        for i, (t, names) in enumerate(plans, 1):
            body_file.write_text(body_of(t, tasks_path.name, a.footer), encoding="utf-8")
            args = ["issue", "create", "--repo", a.repo, "--title", t["title"], "--body-file", str(body_file)]
            for n in names:
                args += ["--label", n]
            if a.milestone:
                args += ["--milestone", a.milestone]
            r = gh(*args)
            if r.returncode:
                print(f"FAILED at {i}/{len(plans)}: {t['title']}\n{r.stderr.strip()}\n"
                      "Everything created so far is recorded: run again to resume.")
                return 1
            number = r.stdout.strip().rsplit("/", 1)[-1]
            _record(meta_path, {task_key(t["line"]): f"#{number}"}, a.repo)
            print(f"{i}/{len(plans)} #{number} {t['title']}", flush=True)
            if a.pause:
                time.sleep(a.pause)
    print(f"done: {len(issue_map) + len(plans)} issues recorded in meta.json#tracker.issue_map")
    return 0


if __name__ == "__main__":
    sys.exit(main())
