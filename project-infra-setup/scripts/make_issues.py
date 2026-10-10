#!/usr/bin/env python3
"""Create one GitHub issue per task in a tasks.md. Resumable: a JSON map (task title -> issue number) records progress.

    make_issues.py --repo OWNER/NAME --tasks .workflow/tasks.md --map .workflow/github-issues.json [--dry-run]

Reads `## Epic` headings and `- [ ] **Title** — body` lines (the prd-to-tasks format). Labels are created from the
heading ("area: <heading>") and from a simple type rule. Skips tasks already ticked `[x]`. Pauses 2 s between
creations to stay under GitHub's content-creation limits. Needs `gh` logged in. Writes nothing but the map.
"""
import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
import time

PALETTE = ["0b5d57", "1d76db", "4a3fc9", "9a5b00", "0e8a16", "5319e7", "b60205", "d93f0b", "fbca04", "c5def5", "bfd4f2", "6e7781", "000000"]
TYPES = {"page": ("tipo: pagina", "0075ca"), "agent": ("tipo: agente", "4a3fc9"), "backend": ("tipo: backend", "1b6e43"),
         "spike": ("tipo: spike", "fef2c0"), "setup": ("tipo: setup", "6e7781")}
SKIP = ("Non-goals", "Open questions")


def parse(text):
    tasks, epic, cur = [], None, None
    for line in text.splitlines():
        if line.startswith("## "):
            epic, cur = line[3:].strip(), None
            continue
        m = re.match(r"^- \[( |x)\] \*\*(.+?)\*\* — (.*)$", line)
        if m:
            cur = {"done": m.group(1) == "x", "title": m.group(2), "body": m.group(3), "epic": epic, "extra": []}
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


def gh(*args):
    return subprocess.run(["gh", *args], capture_output=True, text=True)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--repo", required=True)
    ap.add_argument("--tasks", required=True)
    ap.add_argument("--map", required=True, dest="map_path")
    ap.add_argument("--footer", default="", help="one line appended to every issue (e.g. a link to the design)")
    ap.add_argument("--pause", type=float, default=2.0)
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args(argv)

    tasks = [t for t in parse(open(a.tasks, encoding="utf-8").read()) if not t["done"]]
    epics = list(dict.fromkeys(t["epic"] for t in tasks))
    mp = json.load(open(a.map_path)) if os.path.exists(a.map_path) else {}
    labels = {}
    for t in tasks:
        al, ty = area_label(epics, t["epic"]), type_of(t)
        labels[al[0]], labels[ty[0]] = al[1], ty[1]
    print(f"{len(tasks)} tasks, {len(labels)} labels, {len(mp)} already created")
    if a.dry_run:
        return 0
    for name, color in labels.items():
        r = gh("label", "create", name, "--repo", a.repo, "--color", color, "--force")
        if r.returncode:
            print("label failed:", name, r.stderr.strip()); return 1
    with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False, encoding="utf-8") as bf:
        path = bf.name
    for i, t in enumerate(tasks, 1):
        if t["title"] in mp:
            continue
        open(path, "w", encoding="utf-8").write(body_of(t, os.path.basename(a.tasks), a.footer))
        r = gh("issue", "create", "--repo", a.repo, "--title", t["title"], "--body-file", path,
               "--label", area_label(epics, t["epic"])[0], "--label", type_of(t)[0])
        if r.returncode:
            print(f"FAILED at {i}/{len(tasks)}: {t['title']}\n{r.stderr.strip()}"); return 1
        mp[t["title"]] = int(r.stdout.strip().rsplit("/", 1)[-1])
        json.dump(mp, open(a.map_path, "w"), indent=2, ensure_ascii=False)
        print(f"{i}/{len(tasks)} #{mp[t['title']]} {t['title']}", flush=True)
        time.sleep(a.pause)
    print("done:", len(mp), "issues")
    return 0


if __name__ == "__main__":
    sys.exit(main())
