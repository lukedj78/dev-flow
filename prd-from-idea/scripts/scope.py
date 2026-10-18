#!/usr/bin/env python3
"""scope.py — the PRD's scope rules, and the record of every scope decision.

    python3 scope.py check  <project-root>
    python3 scope.py record <project-root> --request "…" --decision add|defer|reject|experiment --reason "…"
                            [--by user] [--date YYYY-MM-DD]

A request the PRD does not contain passes a short check before it becomes work (`references/scope-check.md`): is it
already in the PRD, does it contradict a Non-goal, does it meet the evidence written in `## Scope rules`, what does
it displace. The user decides; `record` writes the decision as one row of `## Scope changes`, the only place it is
written (plus a history entry: `update_meta.py append-history --skill prd-from-idea`). `check` reports a PRD whose
`## Scope rules` is missing or still has an unfilled line. Nothing here blocks anything.

Stdlib only.
"""

from __future__ import annotations

import argparse
import re
import sys
from datetime import date as _date
from pathlib import Path

RULE_LINES = ("A new feature enters the MVP when", "Not before launch, whatever the evidence", "Who decides")
DECISIONS = ("add", "defer", "reject", "experiment")
RULES_HEADING = "## Scope rules"
CHANGES_HEADING = "## Scope changes"
TABLE_HEAD = "| Date | Request | Decision | Evidence / reason | Decided by |\n|---|---|---|---|---|"


def _section(prd: str, heading: str) -> str | None:
    """The body of a `## …` section, up to the next `## ` heading; None when the section is absent."""
    m = re.search(rf"^{re.escape(heading)}\s*$", prd, re.M)
    if not m:
        return None
    nxt = re.search(r"^## ", prd[m.end():], re.M)
    return prd[m.end():m.end() + nxt.start()] if nxt else prd[m.end():]


def check(prd: str) -> list[str]:
    body = _section(prd, RULES_HEADING)
    if body is None:
        return [f"PRD has no `{RULES_HEADING}` — the evidence that lets a new feature in is not written down "
                "(prd-from-idea, revise mode; on the founder path, copy Playbook §12)"]
    problems = []
    for label in RULE_LINES:
        m = re.search(rf"^\s*-\s*\*\*{re.escape(label)}\*\*\s*:(.*)$", body, re.M)
        value = m.group(1).strip() if m else ""
        if not m:
            problems.append(f"`{RULES_HEADING}`: the line `{label}` is missing")
        elif not value or re.fullmatch(r"<[^>]*>|TBD.*|…", value):
            problems.append(f"`{RULES_HEADING}`: `{label}` is still to fill")
    return problems


def _cell(text: str) -> str:
    return " ".join(text.split()).replace("|", "\\|")


def record(prd: str, date: str, request: str, decision: str, reason: str, by: str) -> str:
    """The PRD with one more row in `## Scope changes`; the section is created at the end the first time."""
    if decision not in DECISIONS:
        raise ValueError(f"decision is one of {', '.join(DECISIONS)}, not {decision!r}")
    row = f"| {_cell(date)} | {_cell(request)} | {decision} | {_cell(reason)} | {_cell(by)} |"
    m = re.search(rf"^{re.escape(CHANGES_HEADING)}\s*$", prd, re.M)
    if not m:
        return prd.rstrip("\n") + f"\n\n{CHANGES_HEADING}\n\n{TABLE_HEAD}\n{row}\n"
    nxt = re.search(r"^## ", prd[m.end():], re.M)
    end = m.end() + nxt.start() if nxt else len(prd)
    body = prd[m.end():end].rstrip("\n")
    if "| Date |" not in body:
        body = body + f"\n\n{TABLE_HEAD}"
    tail = prd[end:]
    return prd[:m.end()] + body + "\n" + row + "\n" + ("\n" + tail if tail else "")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("op", choices=("check", "record"))
    ap.add_argument("project_root", type=Path)
    ap.add_argument("--request")
    ap.add_argument("--decision", choices=DECISIONS)
    ap.add_argument("--reason")
    ap.add_argument("--by", default="user")
    ap.add_argument("--date", default=_date.today().isoformat())
    a = ap.parse_args(argv)
    path = a.project_root / ".workflow" / "PRD.md"
    if not path.is_file():
        if a.op == "record":
            print(f"no PRD at {path}", file=sys.stderr)
            return 2
        return 0   # nothing to apply the rules to yet
    prd = path.read_text(encoding="utf-8")
    if a.op == "check":
        problems = check(prd)
        print("\n".join(problems) if problems else "Scope rules complete.")
        return 1 if problems else 0
    if not (a.request and a.decision and a.reason):
        print("record needs --request, --decision and --reason", file=sys.stderr)
        return 2
    path.write_text(record(prd, a.date, a.request, a.decision, a.reason, a.by), encoding="utf-8")
    print(f"recorded in {CHANGES_HEADING}: {a.decision} — {a.request}. Append history: "
          f"update_meta.py {a.project_root} append-history --skill prd-from-idea")
    return 0


if __name__ == "__main__":
    sys.exit(main())
