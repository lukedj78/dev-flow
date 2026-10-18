#!/usr/bin/env python3
"""meta_tracker.py — the `tracker` and `scrum` blocks of .workflow/meta.json, whatever the tracker.

    meta_tracker.py <meta.json> choose --provider linear|jira|github
    meta_tracker.py <meta.json> upsert --provider P --project '<json>' --url URL
    meta_tracker.py <meta.json> record-issues --mapping '{"<task_key>": "LUC-1"}'
    meta_tracker.py <meta.json> ensure-scrum
    meta_tracker.py <meta.json> migrate

Pure dict transforms plus a thin CLI that writes under meta_io's lock. `issue_map` is keyed by task_key(), so
re-syncing never duplicates an issue. `migrate` brings every older shape to the current one without dropping a key:
the `linear` block of linear-scrum, and the hand-written GitHub blocks (`kind`, `repo`, a map keyed by task title,
inline or in the file `map` names, a nested `scrum`). Titles it cannot find in tasks.md are kept in
`tracker.unmatched`.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import meta_io  # noqa: E402 — vendored copy of dev-flow/scripts/meta_io.py; lint_skills.py keeps the copies identical
from task_key import task_key  # noqa: E402

PROVIDERS = ("linear", "jira", "github")
KIND_TO_PROVIDER = {"github": "github", "github-issues": "github", "linear": "linear", "jira": "jira"}
DEFAULT_STATES = {
    "backlog": "Backlog", "todo": "Todo", "in_progress": "In Progress",
    "in_review": "In Review", "done": "Done", "blocked_label": "blocked",
}
TASK_KEY = re.compile(r"^[0-9a-f]{12}$")
TASK_LINE = re.compile(r"^\s*- \[[ xX]\]\s+\*\*(.+?)\*\*")
LINEAR_PROJECT_KEYS = ("team_id", "team_name", "project_id")
GITHUB_MAP = ".workflow/github-issues.json"   # make_issues.py's title → number map, often never named in meta.json


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def choose(meta: dict, provider: str) -> dict:
    """The tracker chosen at design time; the ids come at Setup."""
    if provider not in PROVIDERS:
        raise ValueError(f"provider must be one of {', '.join(PROVIDERS)}, not {provider!r}")
    meta.setdefault("tracker", {})["provider"] = provider
    return meta


def upsert(meta: dict, provider: str, project: dict, url: str) -> dict:
    t = choose(meta, provider)["tracker"]
    t["project"] = {**(t.get("project") or {}), **project}
    t["url"] = url
    t.setdefault("issue_map", {})
    t["last_synced_at"] = _now()
    return meta


def record_issues(meta: dict, mapping: dict) -> dict:
    t = meta.setdefault("tracker", {})
    t.setdefault("issue_map", {}).update(mapping)   # keyed by task_key → no duplicates
    t["last_synced_at"] = _now()
    return meta


def ensure_scrum(meta: dict) -> dict:
    s = meta.get("scrum") or {}
    s.setdefault("cadence_weeks", 2)
    s.setdefault("estimate_scale", "fibonacci")
    s.setdefault("velocity_target", None)
    s.setdefault("states", dict(DEFAULT_STATES))
    s.setdefault("labels", {})   # bucket → the tracker's own label, discovered at Setup
    s.setdefault("severity_labels", {f"S{i}": f"severity: S{i}" for i in range(1, 5)})
    s.setdefault("bug_label", "bug")
    meta["scrum"] = s
    return meta


def _titles(root: Path) -> dict[str, str]:
    """Bold task title → task_key, from tasks.md."""
    out: dict[str, str] = {}
    try:
        text = (root / ".workflow" / "tasks.md").read_text(encoding="utf-8")
    except OSError:
        return out
    for line in text.splitlines():
        m = TASK_LINE.match(line)
        if m:
            out.setdefault(m.group(1).strip(), task_key(line))
    return out


def _issue(value: object, provider: str | None) -> str:
    text = str(value).strip()
    return f"#{text}" if provider == "github" and text.isdigit() else text


def migrate(meta: dict, root: Path) -> tuple[dict, list[str]]:
    """Every older tracker shape → the current one. Never drops a key."""
    notes: list[str] = []
    t = dict(meta.get("tracker") or {})
    if "kind" in t:
        kind = t.pop("kind")
        t.setdefault("provider", KIND_TO_PROVIDER.get(str(kind), str(kind)))
        notes.append(f"`kind: {kind}` → `provider: {t['provider']}`")
    legacy = meta.pop("linear", None)
    if isinstance(legacy, dict) and t.get("provider") not in (None, "linear"):
        # another tracker was chosen: Linear's ids and keys must not leak into its map
        t.setdefault("legacy_linear", legacy)
        notes.append(f"the `linear` block is kept apart in tracker.legacy_linear — the project uses {t['provider']}")
    elif isinstance(legacy, dict):
        t.setdefault("provider", "linear")
        project = dict(t.get("project") or {})
        for k in LINEAR_PROJECT_KEYS:
            if k in legacy:
                project.setdefault(k, legacy[k])
        if project:
            t["project"] = project
        for k in ("url", "last_synced_at"):
            if k in legacy:
                t.setdefault(k, legacy[k])
        t["issue_map"] = {**(legacy.get("issue_map") or {}), **(t.get("issue_map") or {})}
        extra = {k: v for k, v in legacy.items() if k not in (*LINEAR_PROJECT_KEYS, "url", "last_synced_at", "issue_map")}
        if extra:
            t.setdefault("legacy_linear", extra)
        notes.append("moved the `linear` block into `tracker`")
    elif legacy is not None:
        t.setdefault("legacy_linear", legacy)
    if "repo" in t:
        t.setdefault("project", {}).setdefault("repo", t.pop("repo"))
    if "map" not in t and (root / GITHUB_MAP).is_file():
        if t.get("provider") in (None, "github"):
            t["map"] = GITHUB_MAP
            t.setdefault("provider", "github")
            notes.append(f"folded {GITHUB_MAP} (make_issues.py's map, not recorded in meta.json) into tracker.issue_map")
        else:
            notes.append(f"{GITHUB_MAP} ignored: the project uses {t['provider']}, not GitHub")
    provider = t.get("provider")
    raw = dict(t.get("issue_map") or {})
    map_file = t.get("map")
    if isinstance(map_file, str):
        try:
            from_file = json.loads((root / map_file).read_text(encoding="utf-8"))
            if isinstance(from_file, dict):
                raw = {**from_file, **raw}
        except (OSError, ValueError):
            notes.append(f"{map_file} could not be read — its entries are not in issue_map")
    titles = _titles(root)
    issue_map: dict[str, str] = {}
    unmatched: dict[str, str] = dict(t.get("unmatched") or {})
    for key, value in raw.items():
        if TASK_KEY.match(str(key)):
            issue_map[key] = _issue(value, provider)
        elif key in titles:
            issue_map[titles[key]] = _issue(value, provider)
            unmatched.pop(key, None)
        else:
            unmatched[key] = _issue(value, provider)
    if raw or "issue_map" in t:
        t["issue_map"] = issue_map
    if unmatched:
        t["unmatched"] = unmatched
        notes.append(f"{len(unmatched)} title(s) not in tasks.md, kept in tracker.unmatched: "
                     + ", ".join(sorted(unmatched)[:5]))
    nested = t.pop("scrum", None)
    if isinstance(nested, dict):
        s = meta.setdefault("scrum", {})
        for k, v in nested.items():
            s.setdefault("cadence_weeks" if k == "sprint_weeks" else k, v)
        notes.append("merged the nested tracker.scrum into scrum")
    if t:
        meta["tracker"] = t
    return meta, notes


def legacy_shape(meta: dict, root: Path | None = None) -> str | None:
    """Why the tracker block is in an older shape, or None."""
    t0 = meta.get("tracker") if isinstance(meta.get("tracker"), dict) else {}
    if root is not None and (root / GITHUB_MAP).is_file() and "map" not in t0 \
            and t0.get("provider") in (None, "github") and "kind" not in t0:
        return f"a {GITHUB_MAP} that meta.json#tracker does not record"
    if "linear" in meta:
        return "a legacy `linear` block (linear-scrum)"
    t = meta.get("tracker")
    if not isinstance(t, dict):
        return None
    if "kind" in t:
        return "`tracker.kind` instead of `tracker.provider`"
    if any(not TASK_KEY.match(str(k)) for k in (t.get("issue_map") or {})):
        return "an issue_map keyed by task title, not by task_key"
    return None


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("meta_path", type=Path)
    sub = ap.add_subparsers(dest="op", required=True)
    c = sub.add_parser("choose")
    c.add_argument("--provider", required=True, choices=PROVIDERS)
    u = sub.add_parser("upsert")
    u.add_argument("--provider", required=True, choices=PROVIDERS)
    u.add_argument("--project", required=True, help="JSON object of the tracker's ids")
    u.add_argument("--url", required=True)
    r = sub.add_parser("record-issues")
    r.add_argument("--mapping", required=True, help="JSON object task_key → issue key")
    sub.add_parser("ensure-scrum")
    sub.add_parser("migrate")
    a = ap.parse_args(argv)
    path = a.meta_path.resolve()
    with meta_io.locked(path.parent):
        meta = meta_io.load_or_exit(path)
        notes: list[str] = []
        if a.op == "choose":
            meta = choose(meta, a.provider)
        elif a.op == "upsert":
            meta = ensure_scrum(upsert(meta, a.provider, json.loads(a.project), a.url))
        elif a.op == "record-issues":
            meta = record_issues(meta, json.loads(a.mapping))
        elif a.op == "ensure-scrum":
            meta = ensure_scrum(meta)
        else:
            meta, notes = migrate(meta, path.parent.parent)
        meta_io.write_json(path, meta)
    for n in notes:
        print(f"· {n}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
