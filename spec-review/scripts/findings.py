#!/usr/bin/env python3
"""findings.py — the review's findings as data, so an iteration can be told from a repetition.

    python3 findings.py <root> open     --fixed-point main --profile standard
    python3 findings.py <root> add      --axis risk --severity high --category rollback \
                                       --file lib/db/schema.ts --line 42 --summary "..." [--needs-human]
    python3 findings.py <root> resolve  F3 --as fixed      --note "..." [--sha abc1234]
    python3 findings.py <root> resolve  F4 --as rejected   --note "why it is not a defect"
    python3 findings.py <root> resolve  F5 --as accepted   --user-said "their words"
    python3 findings.py <root> iterate                     # close the round, open the next one
    python3 findings.py <root> status [--json]
    python3 findings.py <root> close    --level 3

**Why this exists.** `spec-review` reported three columns of prose and stopped. Prose cannot answer the
three questions an iterative review needs: *which finding is this*, *was it fixed or argued away*, and
*has it come back*. Without them a second pass is indistinguishable from a first one, and a reviewer
that re-reports a finding the implementer already rejected loops forever.

**Three rules in code, each with its own test:**

1. **A round cannot be closed while a finding needs a human.** `iterate` refuses, naming them. The
   escalation is the point of the loop, not an exception to it — a disagreement about a product
   decision or an ambiguous requirement is the user's, and inventing a resolution is the failure mode
   this guards.
2. **The iteration cap is real.** `iterate` refuses past `max_iterations` (default 3) and says what to
   do instead: the open findings go to the user with the level, which is what `finishing-a-feature.md`
   already does at level 3. A review that cannot converge in three rounds has found something a round
   will not settle.
3. **`accepted` requires the user's own words.** A trade accepted out loud is, a month later,
   indistinguishable from something nobody noticed — the rule `contracts.md` states for intervention
   level 3, enforced here instead of hoped for.

A **reopened** finding is counted, not silently re-added: the same `(axis, category, file, line,
summary)` landing again after being resolved increments `reopened` and restores it. That count is the
single most useful number for judging a review's own quality, which is why `evals/review-quality/`
reads it.

Writes `meta.json#spec_review` through the vendored `meta_io` lock. Never bumps `phase`. Stdlib only.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import meta_io  # noqa: E402 — vendored copy of dev-flow/scripts/meta_io.py: the lock every meta.json writer takes

AXES = ("spec", "standards", "risk")
SEVERITIES = ("critical", "high", "medium", "low", "info")
RESOLUTIONS = ("fixed", "rejected", "accepted", "deferred", "open")
#: Review depth. A profile changes how many rounds and how deep the briefs go — it never removes a
#: check. `contracts.md` §Intervention levels is why: a level is defined by who can check a finding,
#: so "it is a small change" cannot subtract a check that a person would still have to make.
PROFILES = {"light": 1, "standard": 3, "strict": 5}
DEFAULT_PROFILE = "standard"

#: A finding at or above this severity, left open, keeps the review from reading as converged.
BLOCKING = ("critical", "high")


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def head_sha(root: Path) -> str | None:
    """The commit the review actually looked at. Without it nothing can count what landed since —
    which is how archistudio reached 200 merged PRs with no review and a healthy-looking state."""
    try:
        r = subprocess.run(["git", "rev-parse", "HEAD"], cwd=root, capture_output=True,
                           text=True, timeout=15)
    except (OSError, subprocess.SubprocessError):
        return None
    return r.stdout.strip() or None if r.returncode == 0 else None


def fingerprint(f: dict) -> str:
    """Identity of a finding across rounds: the axis, what it is about, and where. Not its wording —
    a reviewer rephrasing the same defect must not create a second finding."""
    parts = [str(f.get(k) or "") for k in ("axis", "category", "file", "line")]
    parts.append((f.get("summary") or "").strip().lower()[:120])
    return hashlib.sha256("\0".join(parts).encode("utf-8")).hexdigest()[:12]


def meta_path(root: Path) -> Path:
    return root / ".workflow" / "meta.json"


def load(root: Path) -> dict:
    try:
        meta = json.loads(meta_path(root).read_text())
    except (OSError, ValueError):
        return {}
    return meta if isinstance(meta, dict) else {}


def block_of(meta: dict) -> dict | None:
    b = meta.get("spec_review")
    return b if isinstance(b, dict) else None


def save(root: Path, mutate) -> list[str]:
    path = meta_path(root)
    if not path.is_file():
        return [f"no {path}: spec-review records into the project's own contract, it does not create one"]
    with meta_io.locked(root / ".workflow"):
        try:
            meta = meta_io.read_meta(path)
        except Exception as e:  # noqa: BLE001 — report, never crash on a bad file
            return [f"{path} could not be read: {e}"]
        existing = meta.get("spec_review")
        if existing is not None and not isinstance(existing, dict):
            return [f"meta.json#spec_review is {type(existing).__name__}, not an object: it was edited by hand"]
        block = existing or {}
        problems = mutate(block)
        if problems:
            return problems
        meta["spec_review"] = block
        meta["updated_at"] = now()
        meta_io.write_json(path, meta)
    return []


def findings_of(block: dict) -> list[dict]:
    got = block.get("findings")
    return [f for f in got if isinstance(f, dict)] if isinstance(got, list) else []


def open_findings(block: dict) -> list[dict]:
    return [f for f in findings_of(block) if f.get("resolution", "open") == "open"]


def needs_human(block: dict) -> list[dict]:
    return [f for f in open_findings(block) if f.get("needs_human") is True]


def blocking_open(block: dict) -> list[dict]:
    return [f for f in open_findings(block) if f.get("severity") in BLOCKING]


def max_iterations(block: dict) -> int:
    given = block.get("max_iterations")
    if isinstance(given, int) and given > 0:
        return given
    return PROFILES.get(block.get("profile", DEFAULT_PROFILE), PROFILES[DEFAULT_PROFILE])


# --- commands --------------------------------------------------------------

def cmd_open(root: Path, a) -> tuple[int, str]:
    if a.profile not in PROFILES:
        return 2, f"--profile must be one of {', '.join(PROFILES)}"

    def mutate(b: dict) -> list[str]:
        b["last_run_at"] = now()
        b["fixed_point"] = a.fixed_point
        b["profile"] = a.profile
        b["max_iterations"] = a.max_iterations or PROFILES[a.profile]
        b["iteration"] = 1
        b["head_sha"] = head_sha(root)
        b.pop("skipped", None)        # a real run replaces a recorded skip
        b.setdefault("findings", [])
        b.setdefault("rounds", [])
        b.setdefault("reopened", 0)
        b["axes_not_run"] = list(a.axes_not_run or [])
        return []

    problems = save(root, mutate)
    if problems:
        return 2, "\n".join(problems)
    b = block_of(load(root)) or {}
    return 0, (f"review opened against {a.fixed_point} · profile {a.profile} · "
               f"up to {b.get('max_iterations')} round(s). `add` the findings, then `iterate` or `close`.")


def cmd_add(root: Path, a) -> tuple[int, str]:
    if a.axis not in AXES:
        return 2, f"--axis must be one of {', '.join(AXES)}"
    if a.severity not in SEVERITIES:
        return 2, f"--severity must be one of {', '.join(SEVERITIES)}"
    if not (a.summary or "").strip():
        return 2, "--summary is required: a finding with no statement is not a finding"
    if a.line is not None and not a.file:
        return 2, "--line without --file: a line reference needs the file it is in"

    result: dict[str, str] = {}

    def mutate(b: dict) -> list[str]:
        if not b:
            return ["no review is open: run `open --fixed-point <ref>` first"]
        candidate = {"axis": a.axis, "category": a.category, "file": a.file, "line": a.line,
                     "summary": a.summary.strip()}
        fp = fingerprint(candidate)
        existing = next((f for f in findings_of(b) if f.get("fingerprint") == fp), None)
        if existing is not None:
            if existing.get("resolution", "open") == "open":
                result["id"] = existing["id"]
                result["note"] = "already open in this review — not added twice"
                return []
            # It was resolved and is back: that is a reopen, and the count is what evals read.
            existing["resolution"] = "open"
            existing["reopened_at"] = now()
            existing["reopen_count"] = int(existing.get("reopen_count", 0)) + 1
            existing["found_in_round"] = b.get("iteration", 1)
            b["reopened"] = int(b.get("reopened", 0)) + 1
            result["id"] = existing["id"]
            result["note"] = (f"REOPENED (it was {existing.get('previous_resolution', 'resolved')}): "
                              f"the same finding is back after being closed")
            return []
        n = len(findings_of(b)) + 1
        entry = {
            "id": f"F{n}",
            "fingerprint": fp,
            "axis": a.axis,
            "severity": a.severity,
            "category": a.category,
            "file": a.file,
            "line": a.line,
            "summary": a.summary.strip(),
            "evidence": a.evidence,
            "impact": a.impact,
            "suggestion": a.suggestion,
            "confidence": a.confidence,
            "needs_human": bool(a.needs_human),
            "resolution": "open",
            "found_in_round": b.get("iteration", 1),
            "found_at": now(),
        }
        b.setdefault("findings", []).append(entry)
        result["id"] = entry["id"]
        return []

    problems = save(root, mutate)
    if problems:
        return 2, "\n".join(problems)
    msg = f"{result.get('id')} recorded ({a.axis}/{a.severity})"
    if result.get("note"):
        msg += f"\n  {result['note']}"
    if a.needs_human:
        msg += "\n  flagged for a human: the round cannot be closed until it is answered"
    return 0, msg


def cmd_resolve(root: Path, a) -> tuple[int, str]:
    if a.as_ not in RESOLUTIONS or a.as_ == "open":
        return 2, f"--as must be one of {', '.join(r for r in RESOLUTIONS if r != 'open')}"
    if a.as_ == "accepted" and not (a.user_said or "").strip():
        return 2, ("accepting a finding needs --user-said: an acceptance given out loud is, a month "
                   "later, indistinguishable from something nobody noticed")
    if a.as_ == "rejected" and not (a.note or "").strip():
        return 2, "--note is required to reject a finding: say why it is not a defect"

    def mutate(b: dict) -> list[str]:
        f = next((x for x in findings_of(b) if x.get("id") == a.finding_id), None)
        if f is None:
            return [f"no finding {a.finding_id} in meta.json#spec_review.findings"]
        if f.get("resolution", "open") != "open":
            return [f"{a.finding_id} is already {f['resolution']!r}"]
        f["previous_resolution"] = a.as_
        f["resolution"] = a.as_
        f["resolved_at"] = now()
        f["resolved_in_round"] = b.get("iteration", 1)
        f["resolution_note"] = (a.note or "").strip() or None
        f["resolution_quote"] = (a.user_said or "").strip() or None
        f["resolution_sha"] = a.sha
        if a.as_ == "accepted":
            f["needs_human"] = False
        return []

    problems = save(root, mutate)
    if problems:
        return 2, "\n".join(problems)
    tail = ""
    if a.as_ == "accepted":
        tail = "\n  write it into the PR too: an acceptance that lives only here is not visible to a reviewer"
    return 0, f"{a.finding_id} resolved as {a.as_}.{tail}"


def cmd_iterate(root: Path, a) -> tuple[int, str]:
    meta = load(root)
    b = block_of(meta)
    if not b:
        return 2, "no review is open"
    pending = needs_human(b)
    if pending:
        lines = ["cannot iterate: these findings need a person, and the loop does not resolve them:"]
        lines += [f"  {f['id']} [{f.get('severity')}] {f.get('summary')}" for f in pending]
        lines += ["", "Answer each one, then `resolve <id> --as fixed|rejected|accepted`.",
                  "A disagreement about a product decision or an ambiguous requirement is the user's; "
                  "inventing a resolution is what this refusal prevents."]
        return 1, "\n".join(lines)

    cap = max_iterations(b)
    current = int(b.get("iteration", 1))
    if current >= cap:
        still = open_findings(b)
        lines = [f"iteration cap reached ({cap}, profile {b.get('profile', DEFAULT_PROFILE)}): "
                 f"this review does not converge by looping."]
        if still:
            lines.append(f"  {len(still)} finding(s) still open:")
            lines += [f"    {f['id']} [{f.get('severity')}] {f.get('summary')}" for f in still[:10]]
        lines += ["", "Take them to the user with the level (`close --level 3`). "
                  "`finishing-a-feature.md` §5 is what happens next."]
        return 1, "\n".join(lines)

    def mutate(blk: dict) -> list[str]:
        blk.setdefault("rounds", []).append({
            "round": current,
            "closed_at": now(),
            "found": len([f for f in findings_of(blk) if f.get("found_in_round") == current]),
            "resolved": len([f for f in findings_of(blk) if f.get("resolved_in_round") == current]),
            "open_at_close": len(open_findings(blk)),
        })
        blk["iteration"] = current + 1
        return []

    problems = save(root, mutate)
    if problems:
        return 2, "\n".join(problems)
    return 0, (f"round {current} closed, round {current + 1} of {cap} open. "
               "Re-review the updated diff; a finding that comes back is counted as reopened.")


def cmd_close(root: Path, a) -> tuple[int, str]:
    if a.level not in (1, 2, 3, 4):
        return 2, "--level must be 1, 2, 3 or 4 (contracts.md, Intervention levels)"
    meta = load(root)
    b = block_of(meta)
    if not b:
        return 2, "no review is open"
    # `contracts.md` §Intervention levels defines level 1 as "**zero** findings on Spec, Standards and
    # Risk" — zero, not zero serious ones. An earlier draft of this function blocked only critical/high,
    # which let a review with an open `low` finding close at level 1, i.e. the agent merging a diff that
    # still had something open on it. Found by walking the cycle on a real project, 2026-11-06.
    still_open = open_findings(b)
    if a.level == 1 and still_open:
        lines = [f"cannot close at level 1: {len(still_open)} finding(s) are still open, of any severity."]
        lines += [f"  {f['id']} [{f.get('severity')}] {f.get('summary')}" for f in still_open[:10]]
        lines += ["", "`contracts.md` defines level 1 as zero findings on all three axes — zero, not zero "
                  "serious ones. Resolve them (fixed, rejected with a reason, or accepted with the user's "
                  "words), or close at level 2 or 3."]
        return 1, "\n".join(lines)

    hard = blocking_open(b)
    if a.level == 2 and hard:
        lines = [f"cannot close at level 2: {len(hard)} critical/high finding(s) are still open."]
        lines += [f"  {f['id']} [{f.get('severity')}] {f.get('summary')}" for f in hard[:10]]
        lines += ["", "Level 2 means the agent merges unless the user objects, and it is for mechanical "
                  "findings ALREADY FIXED on the branch. An unresolved high finding is exactly the case "
                  "that is not the agent's to wave through — fix it, or close at level 3 and ask."]
        return 1, "\n".join(lines)

    if a.level in (1, 2) and needs_human(b):
        return 1, (f"cannot close at level {a.level}: a finding is flagged as needing a human, which is the "
                   "definition of level 3. `contracts.md`: if any criterion needed a human eye, the work "
                   "is not level 1 — by definition, not by judgement.")

    def mutate(blk: dict) -> list[str]:
        blk["level"] = a.level
        blk["closed_at"] = now()
        blk["head_sha"] = head_sha(root)
        blk.setdefault("rounds", []).append({
            "round": int(blk.get("iteration", 1)), "closed_at": now(), "final": True,
            "open_at_close": len(open_findings(blk)),
        })
        return []

    problems = save(root, mutate)
    if problems:
        return 2, "\n".join(problems)
    return 0, f"review closed at level {a.level}. {render(load(root))}"


def cmd_skip(root: Path, a) -> tuple[int, str]:
    """Record that the review was NOT run, with who said so. `finishing-a-feature.md`: an unrun review
    and a clean review must never look the same — and relying on the agent to remember to write that
    down is what left archistudio with 200 unreviewed PRs."""
    if not (a.user_said or "").strip():
        return 2, ("--user-said is required: a skipped review is the user's decision, and recording it "
                   "without their words makes it indistinguishable from the agent deciding to skip itself")

    sha = head_sha(root)

    def mutate(b: dict) -> list[str]:
        b["skipped"] = {"at": now(), "head_sha": sha, "quote": a.user_said.strip(),
                        "reason": (a.reason or "").strip() or None}
        b["last_run_at"] = None
        b.pop("level", None)
        return []

    problems = save(root, mutate)
    if problems:
        return 2, "\n".join(problems)
    return 0, (f"review recorded as SKIPPED on {sha[:7] if sha else '<no sha>'}, by the user.\n"
               "  Write it on the PR too — the next session must be able to tell an unread diff "
               "from a clean one.")


def render(meta: dict) -> str:
    b = block_of(meta)
    if b is None:
        return "no review recorded on this project"
    if isinstance(b.get("skipped"), dict) and not b.get("findings"):
        s = b["skipped"]
        return (f"review SKIPPED on {str(s.get('head_sha') or '')[:7]} — “{s.get('quote')}”"
                + (f" ({s['reason']})" if s.get("reason") else "")
                + "\n  This diff was never read. An unrun review and a clean review must not look the same.")
    fs = findings_of(b)
    by_axis = {ax: [f for f in fs if f.get("axis") == ax] for ax in AXES}
    lines = [f"review: round {b.get('iteration', 1)}/{max_iterations(b)} · profile "
             f"{b.get('profile', DEFAULT_PROFILE)} · against {b.get('fixed_point')}"
             + (f" · level {b['level']}" if b.get("level") else " · not closed")]
    for ax in AXES:
        got = by_axis[ax]
        op = [f for f in got if f.get("resolution", "open") == "open"]
        lines.append(f"  {ax:10} {len(got)} finding(s), {len(op)} open")
        for f in op[:5]:
            where = f" {f['file']}:{f['line']}" if f.get("file") and f.get("line") else (
                f" {f['file']}" if f.get("file") else "")
            lines.append(f"      {f['id']} [{f.get('severity')}]{where} {f.get('summary')}"
                         + ("  ⚠ needs a human" if f.get("needs_human") else ""))
    if b.get("axes_not_run"):
        lines.append(f"  NOT RUN: {', '.join(b['axes_not_run'])} — "
                     "an unrun axis and a clean axis must never look the same")
    if b.get("reopened"):
        lines.append(f"  reopened: {b['reopened']} — a finding that came back after being closed")
    return "\n".join(lines)


def cmd_status(root: Path, a) -> tuple[int, str]:
    meta = load(root)
    if a.json:
        return 0, json.dumps(block_of(meta) or {}, indent=2)
    return 0, render(meta)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("project_root", type=Path)
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("open")
    p.add_argument("--fixed-point", required=True)
    p.add_argument("--profile", default=DEFAULT_PROFILE, choices=sorted(PROFILES))
    p.add_argument("--max-iterations", type=int, default=None)
    p.add_argument("--axes-not-run", nargs="*", default=None)

    p = sub.add_parser("add")
    p.add_argument("--axis", required=True, choices=AXES)
    p.add_argument("--severity", required=True, choices=SEVERITIES)
    p.add_argument("--category", default=None)
    p.add_argument("--file", default=None)
    p.add_argument("--line", type=int, default=None)
    p.add_argument("--summary", required=True)
    p.add_argument("--evidence", default=None)
    p.add_argument("--impact", default=None)
    p.add_argument("--suggestion", default=None)
    p.add_argument("--confidence", default=None, choices=("high", "medium", "low"))
    p.add_argument("--needs-human", action="store_true")

    p = sub.add_parser("resolve")
    p.add_argument("finding_id")
    p.add_argument("--as", dest="as_", required=True,
                   choices=[r for r in RESOLUTIONS if r != "open"])
    p.add_argument("--note", default=None)
    p.add_argument("--user-said", default=None)
    p.add_argument("--sha", default=None)

    sub.add_parser("iterate")

    p = sub.add_parser("skip", help="record that the user chose not to run the review")
    p.add_argument("--user-said", default=None)
    p.add_argument("--reason", default=None)

    p = sub.add_parser("close")
    p.add_argument("--level", type=int, required=True)

    p = sub.add_parser("status")
    p.add_argument("--json", action="store_true")

    a = ap.parse_args(argv)
    root = a.project_root
    if not root.is_dir():
        print(f"not a directory: {root}", file=sys.stderr)
        return 2
    handler = {"open": cmd_open, "add": cmd_add, "resolve": cmd_resolve, "iterate": cmd_iterate,
               "close": cmd_close, "status": cmd_status, "skip": cmd_skip}[a.cmd]
    code, message = handler(root.resolve(), a)
    print(message, file=sys.stderr if code else sys.stdout)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
