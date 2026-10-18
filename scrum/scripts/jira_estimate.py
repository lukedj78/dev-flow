#!/usr/bin/env python3
"""jira_estimate.py — set a Jira issue's story points through the board's estimation endpoint.

    JIRA_EMAIL=… JIRA_API_TOKEN=… jira_estimate.py <project-root> --key ABC-1 --points 3

The Atlassian MCP creates issues, moves them and runs sprints, but writing story points through `editJiraIssue` is
not proven (custom fields). Jira's own `PUT /rest/agile/1.0/issue/{key}/estimation?boardId=` writes the board's
estimation field even when it is not on the edit screen. The site and board come from
meta.json#tracker.project (`site`, `board_id`); the credentials only from the environment, never from the command
line or the chat, and they are never printed. Exit 0 set, 1 refused by Jira, 2 missing input. Stdlib only.
"""
from __future__ import annotations

import argparse
import base64
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import meta_io  # noqa: E402

CAUSES = {401: "JIRA_EMAIL or JIRA_API_TOKEN is wrong (create a token at id.atlassian.com → Security)",
          403: "the account may not edit this issue, or the board is not a scrum board",
          404: "no such issue, or the board_id in meta.json#tracker.project is not this issue's board"}


def _base(site: str) -> str:
    site = site.rstrip("/")
    return site if site.startswith(("http://", "https://")) else f"https://{site}"


def estimate(site: str, board_id: str, key: str, points: float, email: str, token: str,
             opener=urllib.request.urlopen) -> int:
    """PUT the estimate; the HTTP status (an HTTPError's code included)."""
    value = str(int(points)) if float(points).is_integer() else str(points)
    req = urllib.request.Request(
        f"{_base(site)}/rest/agile/1.0/issue/{key}/estimation?boardId={board_id}",
        data=json.dumps({"value": value}).encode(), method="PUT",
        headers={"Content-Type": "application/json", "Accept": "application/json",
                 "Authorization": "Basic " + base64.b64encode(f"{email}:{token}".encode()).decode()})
    try:
        with opener(req, timeout=30) as r:
            return r.status
    except urllib.error.HTTPError as e:
        return e.code


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("root", type=Path)
    ap.add_argument("--key", required=True, help="the issue key, e.g. ABC-12")
    ap.add_argument("--points", required=True, type=float)
    a = ap.parse_args(argv)
    email, token = os.environ.get("JIRA_EMAIL"), os.environ.get("JIRA_API_TOKEN")
    missing = [n for n, v in (("JIRA_EMAIL", email), ("JIRA_API_TOKEN", token)) if not v]
    if missing:
        print(f"set {' and '.join(missing)} in the environment (never on the command line or in the chat)", file=sys.stderr)
        return 2
    project = ((meta_io.load_or_exit(a.root / ".workflow" / "meta.json").get("tracker") or {}).get("project") or {})
    absent = [k for k in ("site", "board_id") if not project.get(k)]
    if absent:
        print(f"meta.json#tracker.project has no {' or '.join(absent)} — the scrum Setup records them "
              "(listJiraBoards gives the board id)", file=sys.stderr)
        return 2
    try:
        status = estimate(str(project["site"]), str(project["board_id"]), a.key, a.points, email, token)
    except (urllib.error.URLError, OSError) as e:
        print(f"could not reach {project['site']}: {getattr(e, 'reason', e)}", file=sys.stderr)
        return 1
    if 200 <= status < 300:
        print(f"{a.key}: {a.points:g} point(s)")
        return 0
    print(f"Jira answered {status}: {CAUSES.get(status, 'see the response in Jira')}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
