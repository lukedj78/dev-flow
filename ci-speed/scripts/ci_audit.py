#!/usr/bin/env python3
"""ci_audit.py — where a repository's CI time goes, from its real runs.

Reads the last N completed GitHub Actions runs with `gh` (the user's own login, nothing else)
and splits every job into three buckets:

  waiting  the job was created and no runner had taken it yet (started_at - created_at)
  setup    the steps that prepare the work: the runner's own setup, checkout, toolchain,
           cache restore and save, dependency install, and the post-steps
  running  every other step: lint, typecheck, build, tests — the work itself

and reports each bucket at p50 and p95, per job and in total, plus the feedback time a pull
request waits for (its run's creation to its last job's end). The biggest bucket is named:
it is the one to fix first.

A step is put in `setup` by its name (SETUP below). A repository that names its steps its own
way can pass --setup-pattern; the classification used is printed, so a wrong guess is visible.

Usage:
  ci_audit.py <owner/repo> [--runs 150] [--event pull_request] [--json] [--setup-pattern REGEX]
  ci_audit.py --from-file runs.json [--json]     (the same data, saved: what the tests read)
"""

from __future__ import annotations

import argparse
import json
import math
import re
import subprocess
import sys
from datetime import datetime

SETUP = re.compile(
    r"^(set up job|post |complete job|run actions/checkout|checkout|"
    r".*\b(setup|set up|install|cache|restore|toolchain)\b)",
    re.I,
)


def clean_name(value: str | None) -> str:
    """A job's name as data: a workflow file sets it, and a pull request from a fork can change it.

    Control characters, newlines, table pipes and backticks go, and it is cut to 80 characters,
    so it reads as one cell of the report and never as text addressed to whoever reads it.
    """
    text = "".join(c if c.isprintable() else " " for c in (value or "?"))
    text = re.sub(r"[|`<>]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return (text[:80] + "…") if len(text) > 80 else (text or "?")


def parse_time(value: str | None) -> datetime | None:
    if not value:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def seconds(start: str | None, end: str | None) -> float | None:
    a, b = parse_time(start), parse_time(end)
    if a is None or b is None:
        return None
    return max(0.0, (b - a).total_seconds())


def percentile(values: list[float], p: float) -> float | None:
    """Nearest-rank percentile: a value that was actually observed, never an interpolation."""
    if not values:
        return None
    ordered = sorted(values)
    rank = max(1, math.ceil(p / 100 * len(ordered)))
    return ordered[rank - 1]


def split_job(job: dict, setup: re.Pattern[str] = SETUP) -> dict[str, float] | None:
    """One job's seconds in each bucket; None for a job that never ran (skipped, cancelled early)."""
    if job.get("conclusion") == "skipped":
        return None
    waiting = seconds(job.get("created_at"), job.get("started_at"))
    total = seconds(job.get("started_at"), job.get("completed_at"))
    if waiting is None or total is None:
        return None
    in_setup = 0.0
    for step in job.get("steps") or []:
        took = seconds(step.get("started_at"), step.get("completed_at"))
        if took is not None and setup.match(step.get("name") or ""):
            in_setup += took
    in_setup = min(in_setup, total)
    return {"waiting": waiting, "setup": in_setup, "running": total - in_setup}


def audit(runs: list[dict], setup: re.Pattern[str] = SETUP) -> dict:
    """The buckets per job name and in total, at p50 and p95, and the pull requests' feedback time."""
    per_job: dict[str, dict[str, list[float]]] = {}
    feedback: list[float] = []
    for run in runs:
        ends = []
        for job in run.get("jobs") or []:
            split = split_job(job, setup)
            if split is None:
                continue
            ends.append(job.get("completed_at"))
            bucket = per_job.setdefault(clean_name(job.get("name")), {"waiting": [], "setup": [], "running": []})
            for key, value in split.items():
                bucket[key].append(value)
        last = max((parse_time(e) for e in ends if e), default=None)
        if run.get("event") == "pull_request" and last is not None:
            took = seconds(run.get("created_at"), last.isoformat())
            if took is not None:
                feedback.append(took)

    def summary(values: dict[str, list[float]]) -> dict:
        return {k: {"p50": percentile(v, 50), "p95": percentile(v, 95), "n": len(v)} for k, v in values.items()}

    jobs = {name: summary(b) for name, b in sorted(per_job.items())}
    totals = {key: sum((j[key]["p50"] or 0) for j in jobs.values()) for key in ("waiting", "setup", "running")}
    biggest = max(totals, key=totals.get) if any(totals.values()) else None
    return {
        "runs": len(runs),
        "jobs": jobs,
        "totals_p50": totals,
        "biggest": biggest,
        "feedback": {"p50": percentile(feedback, 50), "p95": percentile(feedback, 95), "n": len(feedback)},
        "setup_pattern": setup.pattern,
    }


def gh(path: str) -> dict:
    out = subprocess.run(["gh", "api", path], check=True, capture_output=True, text=True).stdout
    return json.loads(out)


def fetch(repo: str, count: int, event: str | None) -> list[dict]:
    """The last `count` completed runs with their jobs, through the user's own `gh` login."""
    runs: list[dict] = []
    page = 1
    while len(runs) < count:
        query = f"repos/{repo}/actions/runs?status=completed&per_page=100&page={page}" + (f"&event={event}" if event else "")
        batch = gh(query).get("workflow_runs") or []
        if not batch:
            break
        runs.extend(batch)
        page += 1
    runs = runs[:count]
    for run in runs:
        run["jobs"] = gh(f"repos/{repo}/actions/runs/{run['id']}/jobs?per_page=100").get("jobs") or []
    return runs


def fmt(value: float | None) -> str:
    if value is None:
        return "—"
    return f"{value:.0f}s" if value < 120 else f"{value / 60:.1f}m"


def report(result: dict) -> str:
    lines = [
        f"{result['runs']} runs. Pull request feedback: p50 {fmt(result['feedback']['p50'])}, p95 {fmt(result['feedback']['p95'])} ({result['feedback']['n']} runs).",
        "",
        "| Job | waiting p50 / p95 | setup p50 / p95 | running p50 / p95 | runs |",
        "|---|---|---|---|---|",
    ]
    for name, job in result["jobs"].items():
        cells = [f"{fmt(job[k]['p50'])} / {fmt(job[k]['p95'])}" for k in ("waiting", "setup", "running")]
        lines.append(f"| {name} | {' | '.join(cells)} | {job['waiting']['n']} |")
    totals = result["totals_p50"]
    lines += [
        "",
        "Sum of the jobs' p50: " + ", ".join(f"{k} {fmt(v)}" for k, v in totals.items()) + ".",
        f"Fix first: **{result['biggest']}**." if result["biggest"] else "No job ran: nothing to measure.",
        f"Setup steps were matched by: {result['setup_pattern']}",
    ]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("repo", nargs="?", help="owner/repo")
    parser.add_argument("--runs", type=int, default=150)
    parser.add_argument("--event", default=None, help="only runs of this event, e.g. pull_request")
    parser.add_argument("--from-file", help="runs saved as JSON (a list of runs, each with its jobs)")
    parser.add_argument("--setup-pattern", help="a regex for the names of setup steps")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    if not args.repo and not args.from_file:
        parser.error("say the repository (owner/repo) or --from-file")
    setup = re.compile(args.setup_pattern, re.I) if args.setup_pattern else SETUP
    if args.from_file:
        with open(args.from_file, encoding="utf-8") as f:
            runs = json.load(f)
    else:
        try:
            runs = fetch(args.repo, args.runs, args.event)
        except (subprocess.CalledProcessError, FileNotFoundError) as error:
            print(f"gh could not read the runs: {error}", file=sys.stderr)
            return 2
    result = audit(runs, setup)
    print(json.dumps(result, indent=2) if args.json else report(result))
    return 0


if __name__ == "__main__":
    sys.exit(main())
