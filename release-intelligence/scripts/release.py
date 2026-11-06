#!/usr/bin/env python3
"""release.py — the Release Manifest in `meta.json#release`, and the transitions it allows.

    python3 release.py <root> enable  [--autonomy advisory|assisted|automated] [--flag-provider ...]
    python3 release.py <root> disable
    python3 release.py <root> plan    --feature US-7 [--base ref] [--raise-to high --reason "..."]
    python3 release.py <root> approve REL-... --user-said "their words"
    python3 release.py <root> stage   REL-... --to 25 --evidence '<json>'
    python3 release.py <root> pause   REL-... [--note "..."]
    python3 release.py <root> rollback REL-... --kind flag|deployment|database [--user-said "..."]
    python3 release.py <root> verify  REL-... --evidence '<json>'
    python3 release.py <root> status  [--json]
    python3 release.py <root> cleanup-due
    python3 release.py <root> policy

**Opt-in, and invisible when off.** Without `meta.json#release` nothing in dev-flow changes: the gate
does not apply, `show_state.py` says nothing, and every other skill behaves exactly as before. `enable`
is the only thing that creates the block, and it is the user's decision.

**The three refusals that are the point of this script**, each with its own test:

1. **`stage` never advances on elapsed time.** It requires `--evidence`, and the evidence must clear
   the project's thresholds *and* cover at least the configured observation window. No evidence, or
   evidence that says it could not measure, is `insufficient` — which is a refusal, not a pass.
   Missing telemetry has never been proof that a release is healthy.
2. **`approve` requires the user's own words.** `--user-said` carries them into the manifest, the same
   shape `founder-intelligence` uses for the Playbook. An agent cannot approve its own release.
3. **`rollback --kind database` is never executed here.** It records the decision and prints the
   procedure; the migration itself is run by a person following `references/database-migrations.md`.
   Disabling a flag does not undo a schema change, and this script will not pretend otherwise.

Writes go through the vendored `meta_io` lock, like every writer of the contract. Never bumps `phase`
— that stays `vercel-deploy`'s / `rn-eas-deploy`'s to set. Stdlib only.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import meta_io  # noqa: E402 — vendored copy of dev-flow/scripts/meta_io.py: the lock every meta.json writer takes
import policy  # noqa: E402
import risk as risk_mod  # noqa: E402

STATUSES = ("planned", "approved", "rolling", "paused", "complete", "rolled_back", "abandoned")

#: Stage percentages. A starting point, not a universal default — a product with 400 weekly users
#: cannot learn anything from 1%, and a payment flow should not jump 25 → 100.
DEFAULT_STAGES = [1, 5, 25, 50, 100]

DEFAULT_THRESHOLDS = {
    "error_rate_pct": 1.0,
    "p95_ms": 1200,
    "min_observation_minutes": 30,
    # Above this multiple of the threshold the verdict is `rollback` rather than `pause`.
    "rollback_multiple": 2.0,
}

DEFAULT_CLEANUP = {"min_days_at_100": 7}


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def parse_ts(value: object) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


# --- reading and writing the block -----------------------------------------

def meta_path(root: Path) -> Path:
    return root / ".workflow" / "meta.json"


def load(root: Path) -> tuple[dict, dict | None]:
    """(meta, release block or None). A missing or unreadable meta.json is ({}, None), never a crash."""
    try:
        meta = json.loads(meta_path(root).read_text())
    except (OSError, ValueError):
        return {}, None
    if not isinstance(meta, dict):
        return {}, None
    block = meta.get("release")
    return meta, block if isinstance(block, dict) else None


def save(root: Path, mutate) -> list[str]:
    """Apply `mutate(release_block)` under the lock. Returns problems; [] means it was written."""
    path = meta_path(root)
    if not path.is_file():
        return [f"no {path}: run dev-flow's init_workflow.py first — release-intelligence "
                "records into the project's own contract, it does not create one"]
    with meta_io.locked(root / ".workflow"):
        try:
            meta = meta_io.read_meta(path)
        except Exception as e:  # noqa: BLE001 — meta_io raises its own InvalidMeta; report, never crash
            return [f"{path} could not be read: {e}"]
        block = meta.get("release")
        if block is not None and not isinstance(block, dict):
            return [f"meta.json#release is {type(block).__name__}, not an object: it was edited by hand"]
        block = block or {}
        problems = mutate(block)
        if problems:
            return problems
        meta["release"] = block
        meta["updated_at"] = now()
        meta_io.write_json(path, meta)
    return []


def settings(block: dict) -> dict:
    out = dict(DEFAULT_THRESHOLDS)
    given = block.get("thresholds")
    if isinstance(given, dict):
        out.update({k: v for k, v in given.items() if isinstance(v, (int, float))})
    return out


def stages_of(block: dict) -> list[int]:
    s = (block.get("rollout_strategy") or {}).get("stages")
    if isinstance(s, list) and s and all(isinstance(x, int) and 0 < x <= 100 for x in s):
        return sorted(set(s))
    return list(DEFAULT_STAGES)


def find(block: dict, release_id: str) -> dict | None:
    for r in block.get("releases") or []:
        if isinstance(r, dict) and r.get("id") == release_id:
            return r
    return None


def newest(block: dict, environment: str | None = None) -> dict | None:
    rels = [r for r in (block.get("releases") or []) if isinstance(r, dict)]
    if environment:
        rels = [r for r in rels if r.get("environment") == environment]
    return rels[-1] if rels else None


# --- release health --------------------------------------------------------

def health_verdict(evidence: object, thresholds: dict) -> tuple[str, str]:
    """(`continue` | `pause` | `rollback` | `insufficient`, why). Never raises.

    `insufficient` is the default answer, not an error case: every path that cannot *prove* health
    lands here, and `stage` refuses on it. This is the one rule the spec is built around — missing
    telemetry must never read as a healthy release.
    """
    if not isinstance(evidence, dict):
        return "insufficient", "no evidence was passed: --evidence '<json>' is required to advance"
    if evidence.get("sufficient") is False:
        return "insufficient", ("the evidence declares itself insufficient "
                                f"({evidence.get('reason') or 'no reason given'})")
    if evidence.get("provider_error"):
        return "insufficient", (f"the observability provider failed: {evidence['provider_error']} — "
                                "a provider failure is not a healthy release")

    window = evidence.get("window_minutes")
    need = thresholds.get("min_observation_minutes", 30)
    if not isinstance(window, (int, float)):
        return "insufficient", "the evidence has no window_minutes: nothing says how long it watched"
    if window < need:
        return "insufficient", (f"the evidence covers {window} min, the project asks for at least {need}: "
                                "a stage is not cleared by waiting less than the window")

    err = evidence.get("error_rate_pct")
    p95 = evidence.get("p95_ms")
    if not isinstance(err, (int, float)) and not isinstance(p95, (int, float)):
        return "insufficient", ("the evidence carries neither error_rate_pct nor p95_ms: "
                                "there is no signal to judge")

    multiple = thresholds.get("rollback_multiple", 2.0)
    reasons: list[str] = []
    verdict = "continue"

    if isinstance(err, (int, float)):
        limit = thresholds.get("error_rate_pct", 1.0)
        if err > limit * multiple:
            return "rollback", (f"error rate {err}% is over {multiple}× the {limit}% threshold: "
                                "stop serving this release")
        if err > limit:
            verdict = "pause"
            reasons.append(f"error rate {err}% is over the {limit}% threshold")

    if isinstance(p95, (int, float)):
        limit = thresholds.get("p95_ms", 1200)
        if p95 > limit:
            verdict = "pause"
            reasons.append(f"p95 {p95}ms is over the {limit}ms threshold")

    # Baseline comparison, when the previous stable release gave us numbers to compare against.
    base = evidence.get("baseline")
    if isinstance(base, dict) and verdict == "continue":
        b_err = base.get("error_rate_pct")
        if isinstance(err, (int, float)) and isinstance(b_err, (int, float)) and b_err >= 0:
            if err > b_err * 2 and err - b_err > 0.1:
                verdict = "pause"
                reasons.append(f"error rate {err}% is more than double the baseline's {b_err}%, "
                               "even though it is under the absolute threshold")

    if verdict == "continue":
        return "continue", (f"within thresholds over {window} min"
                            + (f" (err {err}%)" if isinstance(err, (int, float)) else "")
                            + (f" (p95 {p95}ms)" if isinstance(p95, (int, float)) else ""))
    return verdict, "; ".join(reasons)


# --- commands --------------------------------------------------------------

def cmd_enable(root: Path, a: argparse.Namespace) -> tuple[int, str]:
    def mutate(block: dict) -> list[str]:
        if a.autonomy and a.autonomy not in policy.AUTONOMY:
            return [f"--autonomy must be one of {', '.join(policy.AUTONOMY)}"]
        block["enabled"] = True
        block.setdefault("autonomy", "advisory")
        if a.autonomy:
            block["autonomy"] = a.autonomy
        for key, value in (("flag_provider", a.flag_provider),
                           ("observability_provider", a.observability_provider),
                           ("deploy_provider", a.deploy_provider),
                           ("scm_provider", a.scm_provider)):
            if value is not None:
                block[key] = None if value == "none" else value
            else:
                block.setdefault(key, None)
        block.setdefault("rollout_strategy", {"stages": list(DEFAULT_STAGES)})
        block.setdefault("thresholds", dict(DEFAULT_THRESHOLDS))
        block.setdefault("cleanup_policy", dict(DEFAULT_CLEANUP))
        block.setdefault("migration_policy", "expand-contract")
        block.setdefault("releases", [])
        block["updated_at"] = now()
        return []

    problems = save(root, mutate)
    if problems:
        return 2, "\n".join(problems)
    _, block = load(root)
    return 0, ("release-intelligence enabled.\n\n" + policy.table(block.get("autonomy", "advisory"),
                                                                  block.get("required_approvals"))
               + "\n\nNothing executes until a release is planned. `plan` next.")


def cmd_disable(root: Path, a: argparse.Namespace) -> tuple[int, str]:
    def mutate(block: dict) -> list[str]:
        if not block:
            return ["release-intelligence was never enabled on this project: nothing to disable"]
        block["enabled"] = False
        block["autonomy"] = "disabled"
        block["updated_at"] = now()
        return []

    problems = save(root, mutate)
    if problems:
        return 2, "\n".join(problems)
    return 0, ("release-intelligence disabled. The manifests are kept as a record; the gate no longer "
               "applies and dev-flow behaves exactly as it does on a project that never enabled it.")


def next_id(block: dict, day: str) -> str:
    same = [r for r in (block.get("releases") or [])
            if isinstance(r, dict) and str(r.get("id", "")).startswith(f"REL-{day}")]
    return f"REL-{day}-{len(same) + 1:02d}"


def cmd_plan(root: Path, a: argparse.Namespace) -> tuple[int, str]:
    meta, block = load(root)
    if not block or not block.get("enabled"):
        return 2, ("release-intelligence is not enabled on this project. "
                   "`release.py <root> enable` first — it is opt-in by design.")
    if a.raise_to and a.raise_to not in risk_mod.LEVELS:
        return 2, f"--raise-to must be one of {', '.join(risk_mod.LEVELS)}"
    if a.raise_to and not (a.reason or "").strip():
        return 2, "--raise-to needs --reason: an unexplained raise is not reviewable"

    assessment = risk_mod.assess(root, base=a.base, include_working=a.include_working, meta=meta)
    level = assessment.level
    raised = None
    if a.raise_to:
        if risk_mod.worse(level, a.raise_to) != a.raise_to:
            return 2, (f"--raise-to {a.raise_to} is not higher than the measured floor {level}. "
                       "The floor only goes up; to argue it down, fix the signal the scan found.")
        raised, level = {"from": assessment.level, "to": a.raise_to, "reason": a.reason}, a.raise_to

    rid_holder: dict[str, str] = {}

    def mutate(b: dict) -> list[str]:
        rid = next_id(b, datetime.now(timezone.utc).strftime("%Y-%m-%d"))
        rid_holder["id"] = rid
        verdict = policy.decide("rollout_advance", level, b.get("autonomy", "advisory"),
                                b.get("required_approvals"))
        entry = {
            "id": rid,
            "feature": a.feature,
            "environment": a.environment,
            "commit": head_commit(root),
            "pr": a.pr,
            "description": a.description,
            "risk": level,
            "risk_floor": assessment.level,
            "risk_raised": raised,
            "risk_signals": [s.id for s in assessment.signals],
            "not_checked": assessment.not_checked,
            "reversible_by_deployment_rollback": assessment.reversible,
            "destructive_migration": assessment.destructive_migration,
            "approval": {"required": verdict != "auto", "granted_by_user": False,
                         "quote": None, "at": None},
            "flag": ({"key": a.flag_key, "provider": b.get("flag_provider"), "created": False}
                     if a.flag_key else None),
            "rollout": {"stages": stages_of(b), "current_percent": 0, "steps": []},
            "status": "planned",
            "planned_at": now(),
            "verified_at": None,
            "events": [],
        }
        b.setdefault("releases", []).append(entry)
        b["updated_at"] = now()
        return []

    problems = save(root, mutate)
    if problems:
        return 2, "\n".join(problems)
    _, block = load(root)
    entry = find(block, rid_holder["id"])
    return 0, render_release(entry, block) + "\n\n" + risk_mod.render(assessment)


def head_commit(root: Path) -> str | None:
    try:
        r = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=root,
                           capture_output=True, text=True, timeout=15)
    except (OSError, subprocess.SubprocessError):
        return None
    return r.stdout.strip() or None if r.returncode == 0 else None


def cmd_approve(root: Path, a: argparse.Namespace) -> tuple[int, str]:
    if not (a.user_said or "").strip():
        return 2, ("--user-said is required: an approval without the user's own words is the agent "
                   "approving its own release. Ask them, then record what they said.")

    def mutate(b: dict) -> list[str]:
        entry = find(b, a.release_id)
        if entry is None:
            return [f"no release {a.release_id} in meta.json#release.releases"]
        if entry.get("status") not in ("planned", "paused"):
            return [f"{a.release_id} is {entry.get('status')!r}: only a planned or paused release is approved"]
        entry["approval"] = {"required": True, "granted_by_user": True,
                             "quote": a.user_said.strip(), "at": now()}
        entry["status"] = "approved"
        entry.setdefault("events", []).append({"at": now(), "event": "approved", "by": "user"})
        b["updated_at"] = now()
        return []

    problems = save(root, mutate)
    if problems:
        return 2, "\n".join(problems)
    return 0, f"{a.release_id} approved, with the user's words recorded. `stage --to <percent> --evidence ...` next."


def cmd_stage(root: Path, a: argparse.Namespace) -> tuple[int, str]:
    meta, block = load(root)
    if not block:
        return 2, "release-intelligence is not enabled on this project"
    entry = find(block, a.release_id)
    if entry is None:
        return 2, f"no release {a.release_id}"

    try:
        evidence = json.loads(a.evidence) if a.evidence else None
    except ValueError as e:
        return 2, f"--evidence is not valid JSON ({e})"

    th = settings(block)
    verdict, why = health_verdict(evidence, th)
    if verdict != "continue":
        lines = [f"stage refused: {verdict.upper()} — {why}"]
        if verdict == "insufficient":
            lines.append("")
            lines.append("A stage is cleared by measured health, never by elapsed time. Collect the window, "
                         "or pause the rollout and say so.")
        else:
            lines.append("")
            lines.append(f"Record it: release.py {root} pause {a.release_id} --note \"{why}\""
                         if verdict == "pause" else
                         f"Record it: release.py {root} rollback {a.release_id} --kind flag")
        # A refused advance is still an event worth keeping: it is the audit trail of the decision.
        # Six weeks later, "why did this sit at 5% for two days" has an answer only if this is written.
        def record_refusal(b: dict) -> list[str]:
            _append_event(b, a.release_id, {"at": now(), "event": f"stage_refused:{verdict}",
                                            "to_percent": a.to, "why": why, "evidence": evidence})
            return []

        save(root, record_refusal)
        return 1, "\n".join(lines)

    autonomy = block.get("autonomy", "advisory")
    decision = policy.decide("rollout_advance", entry.get("risk", "critical"), autonomy,
                             block.get("required_approvals"))
    if decision != "auto" and entry.get("approval", {}).get("granted_by_user") is not True:
        return 1, (f"stage refused: the policy says {decision!r} for a {entry.get('risk')} release in "
                   f"{autonomy} mode, and no approval is recorded.\n"
                   f"  {policy.explain('rollout_advance', entry.get('risk', 'critical'), autonomy, block.get('required_approvals'))}\n"
                   f"  Fix: release.py {root} approve {a.release_id} --user-said \"<their words>\"")

    def mutate(b: dict) -> list[str]:
        e = find(b, a.release_id)
        if e is None:
            return [f"no release {a.release_id}"]
        if e.get("status") not in ("approved", "rolling", "planned"):
            return [f"{a.release_id} is {e.get('status')!r}: it is not rolling"]
        current = e.get("rollout", {}).get("current_percent", 0)
        if a.to <= current:
            return [f"{a.release_id} is already at {current}%: --to must be higher "
                    "(use `pause` or `rollback` to reduce exposure, which is what those commands are for)"]
        e["rollout"]["current_percent"] = a.to
        e["rollout"].setdefault("steps", []).append(
            {"at": now(), "to_percent": a.to, "verdict": verdict, "why": why, "evidence": evidence})
        e["status"] = "rolling"
        b["updated_at"] = now()
        return []

    problems = save(root, mutate)
    if problems:
        return 2, "\n".join(problems)
    tail = ("  this was the last stage — `verify` it before any cleanup."
            if a.to >= 100 else f"  next stage: {next_stage(stages_of(block), a.to)}%")
    return 0, f"{a.release_id} advanced to {a.to}% ({why}).\n{tail}"


def _append_event(block: dict, release_id: str, event: dict) -> None:
    entry = find(block, release_id)
    if entry is not None:
        entry.setdefault("events", []).append(event)
        block["updated_at"] = now()


def next_stage(stages: list[int], current: int) -> int | None:
    for s in stages:
        if s > current:
            return s
    return None


def cmd_pause(root: Path, a: argparse.Namespace) -> tuple[int, str]:
    def mutate(b: dict) -> list[str]:
        e = find(b, a.release_id)
        if e is None:
            return [f"no release {a.release_id}"]
        e["status"] = "paused"
        e.setdefault("events", []).append({"at": now(), "event": "paused", "note": a.note})
        b["updated_at"] = now()
        return []

    problems = save(root, mutate)
    if problems:
        return 2, "\n".join(problems)
    entry = find(load(root)[1] or {}, a.release_id) or {}
    at = (entry.get("rollout") or {}).get("current_percent", "?")  # a hand-edited block must not crash a pause
    return 0, (f"{a.release_id} paused at {at}%. "
               "Pausing never needs approval — that asymmetry is deliberate.")


ROLLBACK_KINDS = ("flag", "deployment", "database")


def cmd_rollback(root: Path, a: argparse.Namespace) -> tuple[int, str]:
    if a.kind not in ROLLBACK_KINDS:
        return 2, f"--kind must be one of {', '.join(ROLLBACK_KINDS)}"
    meta, block = load(root)
    if not block:
        return 2, "release-intelligence is not enabled on this project"
    entry = find(block, a.release_id)
    if entry is None:
        return 2, f"no release {a.release_id}"
    autonomy = block.get("autonomy", "advisory")
    action = {"flag": "flag_rollback", "deployment": "deployment_rollback",
              "database": "destructive_db_migration"}[a.kind]
    decision = policy.decide(action, entry.get("risk", "critical"), autonomy,
                             block.get("required_approvals"))
    if decision != "auto" and not (a.user_said or "").strip():
        return 1, (f"a {a.kind} rollback of a {entry.get('risk')} release needs the user's yes "
                   f"({decision!r}).\n  {policy.explain(action, entry.get('risk', 'critical'), autonomy)}\n"
                   f"  Fix: re-run with --user-said \"<their words>\"")

    def mutate(b: dict) -> list[str]:
        e = find(b, a.release_id)
        if e is None:
            return [f"no release {a.release_id}"]
        e["status"] = "rolled_back"
        e["rollout"]["current_percent"] = 0 if a.kind == "flag" else e["rollout"].get("current_percent", 0)
        e.setdefault("events", []).append(
            {"at": now(), "event": f"rollback:{a.kind}", "quote": (a.user_said or "").strip() or None,
             "note": a.note})
        b["updated_at"] = now()
        return []

    problems = save(root, mutate)
    if problems:
        return 2, "\n".join(problems)
    out = [f"{a.release_id} recorded as rolled back ({a.kind})."]
    if a.kind == "deployment":
        out += ["", "The deployment rollback itself is `vercel-deploy`'s runbook, not this script's:",
                "  vercel-deploy/references/rollback-runbook.md — including the trap that a rollback turns",
                "  off auto-assignment of production domains, so the next push goes green and does not go live."]
    if a.kind == "database":
        out += ["", "⚠️ NOTHING WAS RUN AGAINST THE DATABASE, and this script never will.",
                "  A deployment rollback restores code and leaves the schema. The recovery is a new,",
                "  forward migration written and run by a person: references/database-migrations.md.",
                "  Confirm the backup and the restore point BEFORE touching production data."]
    if a.kind == "flag":
        out += ["", "Turning the flag off restores the previous behaviour for new evaluations only.",
                "  Work the old code already did (emails sent, rows written, payments taken) stays done."]
    return 0, "\n".join(out)


def cmd_verify(root: Path, a: argparse.Namespace) -> tuple[int, str]:
    meta, block = load(root)
    if not block:
        return 2, "release-intelligence is not enabled on this project"
    try:
        evidence = json.loads(a.evidence) if a.evidence else None
    except ValueError as e:
        return 2, f"--evidence is not valid JSON ({e})"
    verdict, why = health_verdict(evidence, settings(block))
    if verdict != "continue":
        return 1, (f"not verified: {verdict.upper()} — {why}\n"
                   "A release is complete when its health was measured at full exposure, "
                   "not when the last stage was set.")

    def mutate(b: dict) -> list[str]:
        e = find(b, a.release_id)
        if e is None:
            return [f"no release {a.release_id}"]
        if e.get("rollout", {}).get("current_percent", 0) < 100:
            return [f"{a.release_id} is at {e['rollout'].get('current_percent', 0)}%: "
                    "a release is verified at full exposure, not part-way"]
        e["status"] = "complete"
        e["verified_at"] = now()
        e.setdefault("events", []).append({"at": now(), "event": "verified", "why": why,
                                           "evidence": evidence})
        b["updated_at"] = now()
        return []

    problems = save(root, mutate)
    if problems:
        return 2, "\n".join(problems)
    days = (block.get("cleanup_policy") or DEFAULT_CLEANUP).get("min_days_at_100", 7)
    return 0, (f"{a.release_id} verified and complete ({why}).\n"
               f"  Cleanup becomes due after {days} days at 100%: `cleanup-due`.")


def flag_key_in_source(root: Path, key: str) -> list[str]:
    """Files that still mention the flag key. Evidence that cleanup is a code change, not just an API call.

    `-F` because a flag key is a literal, not a pattern: `git grep` is regex by default, so a key
    containing `.` would match more files than it should and make cleanup look bigger than it is.
    """
    try:
        r = subprocess.run(["git", "grep", "-l", "-F", "--", key], cwd=root,
                           capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.SubprocessError):
        return []
    return [p for p in r.stdout.split() if not p.startswith(".workflow/")] if r.returncode == 0 else []


def cmd_cleanup_due(root: Path, a: argparse.Namespace) -> tuple[int, str]:
    meta, block = load(root)
    if not block:
        return 2, "release-intelligence is not enabled on this project"
    days = (block.get("cleanup_policy") or DEFAULT_CLEANUP).get("min_days_at_100", 7)
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    due, waiting, blocked = [], [], []
    for e in block.get("releases") or []:
        if not isinstance(e, dict) or not e.get("flag"):
            continue
        key = e["flag"].get("key")
        if e.get("status") != "complete":
            blocked.append(f"{e.get('id')} ({key}): status {e.get('status')!r} — not verified at 100%")
            continue
        ts = parse_ts(e.get("verified_at"))
        if ts is None or ts > cutoff:
            waiting.append(f"{e.get('id')} ({key}): verified {e.get('verified_at')}, "
                           f"the policy asks for {days} days at 100%")
            continue
        hits = flag_key_in_source(root, key) if key else []
        due.append((e.get("id"), key, hits))

    out = []
    if due:
        out.append("DUE — the flag has outlived its purpose:")
        for rid, key, hits in due:
            out.append(f"  {rid}: {key}")
            if hits:
                out.append(f"    the key is still in {len(hits)} file(s): the cleanup is a code change first, "
                           "then the flag is archived")
                for h in hits[:8]:
                    out.append(f"      {h}")
            else:
                out.append("    the key no longer appears in the source: the code path is already gone")
            out.append("    ⚠️ Before archiving, confirm with the provider that nothing still EVALUATES it. "
                       "A grep sees this repo, not the other clients that may read the same flag.")
    if waiting:
        out.append("")
        out.append("WAITING — verified, not yet old enough:")
        out += [f"  {w}" for w in waiting]
    if blocked:
        out.append("")
        out.append("NOT ELIGIBLE — a flag is not retired before its release is verified:")
        out += [f"  {b}" for b in blocked]
    if not out:
        out = ["no flagged release on this project: nothing to clean up"]
    return 0, "\n".join(out)


def render_release(e: dict | None, block: dict) -> str:
    if not e:
        return "no release recorded"
    lines = [f"{e.get('id')}  {e.get('status', '?').upper()}  risk {str(e.get('risk', '?')).upper()}"
             f"  {e.get('environment')}  feature {e.get('feature')}"]
    if e.get("risk_raised"):
        r = e["risk_raised"]
        lines.append(f"  risk raised {r.get('from')} → {r.get('to')}: {r.get('reason')}")
    if e.get("destructive_migration"):
        lines.append("  ⚠️ destructive migration: a deployment rollback will NOT undo it")
    elif not e.get("reversible_by_deployment_rollback", True):
        lines.append("  ⚠️ includes a migration: the code rolls back, the schema does not")
    ap = e.get("approval") or {}
    if ap.get("required"):
        lines.append(f"  approval: {'GRANTED' if ap.get('granted_by_user') else 'REQUIRED, not granted'}"
                     + (f" — “{ap.get('quote')}”" if ap.get("quote") else ""))
    flag = e.get("flag")
    if flag:
        lines.append(f"  flag: {flag.get('key')} ({flag.get('provider') or 'no provider recorded'})"
                     f"{'' if flag.get('created') else ' — not created yet'}")
    ro = e.get("rollout") or {}
    lines.append(f"  exposure: {ro.get('current_percent', 0)}%  stages {ro.get('stages')}")
    if e.get("not_checked"):
        lines.append(f"  NOT CHECKED ({len(e['not_checked'])}):")
        for u in e["not_checked"]:
            lines.append(f"    - {u}")
    return "\n".join(lines)


def cmd_status(root: Path, a: argparse.Namespace) -> tuple[int, str]:
    meta, block = load(root)
    if block is None:
        return 0, ("release-intelligence is not enabled on this project. Nothing in dev-flow is affected: "
                   "no gate applies and no skill behaves differently.\n"
                   "  Enable it:  release.py <root> enable --autonomy advisory")
    if a.json:
        return 0, json.dumps(block, indent=2)
    on = block.get("enabled") is True
    out = [f"release-intelligence: {'ON' if on else 'OFF'}  autonomy {block.get('autonomy')}",
           f"  providers: flags={block.get('flag_provider')} obs={block.get('observability_provider')} "
           f"deploy={block.get('deploy_provider')} scm={block.get('scm_provider')}",
           f"  thresholds: {settings(block)}", ""]
    rels = [r for r in (block.get("releases") or []) if isinstance(r, dict)]
    if not rels:
        out.append("no release planned yet")
    for e in rels[-5:]:
        out.append(render_release(e, block))
        out.append("")
    return 0, "\n".join(out).rstrip()


def cmd_policy(root: Path, a: argparse.Namespace) -> tuple[int, str]:
    _, block = load(root)
    block = block or {}
    return 0, policy.table(block.get("autonomy", "advisory"), block.get("required_approvals"))


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("project_root", type=Path)
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("enable")
    p.add_argument("--autonomy", default=None, choices=policy.AUTONOMY)
    p.add_argument("--flag-provider", default=None)
    p.add_argument("--observability-provider", default=None)
    p.add_argument("--deploy-provider", default=None)
    p.add_argument("--scm-provider", default=None)

    sub.add_parser("disable")

    p = sub.add_parser("plan")
    p.add_argument("--feature", required=True, help="the PRD story or task id this release ships")
    p.add_argument("--environment", default="production")
    p.add_argument("--description", default=None)
    p.add_argument("--pr", type=int, default=None)
    p.add_argument("--base", default=None)
    p.add_argument("--include-working", action="store_true")
    p.add_argument("--flag-key", default=None)
    p.add_argument("--raise-to", default=None, choices=risk_mod.LEVELS)
    p.add_argument("--reason", default=None)

    p = sub.add_parser("approve")
    p.add_argument("release_id")
    p.add_argument("--user-said", default=None)

    p = sub.add_parser("stage")
    p.add_argument("release_id")
    p.add_argument("--to", type=int, required=True)
    p.add_argument("--evidence", default=None)

    p = sub.add_parser("pause")
    p.add_argument("release_id")
    p.add_argument("--note", default=None)

    p = sub.add_parser("rollback")
    p.add_argument("release_id")
    p.add_argument("--kind", required=True, choices=ROLLBACK_KINDS)
    p.add_argument("--user-said", default=None)
    p.add_argument("--note", default=None)

    p = sub.add_parser("verify")
    p.add_argument("release_id")
    p.add_argument("--evidence", default=None)

    p = sub.add_parser("status")
    p.add_argument("--json", action="store_true")

    sub.add_parser("cleanup-due")
    sub.add_parser("policy")

    a = ap.parse_args(argv)
    root = a.project_root
    if not root.is_dir():
        print(f"not a directory: {root}", file=sys.stderr)
        return 2
    root = root.resolve()
    handler = {
        "enable": cmd_enable, "disable": cmd_disable, "plan": cmd_plan, "approve": cmd_approve,
        "stage": cmd_stage, "pause": cmd_pause, "rollback": cmd_rollback, "verify": cmd_verify,
        "status": cmd_status, "cleanup-due": cmd_cleanup_due, "policy": cmd_policy,
    }[a.cmd]
    code, message = handler(root, a)
    print(message, file=sys.stderr if code else sys.stdout)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
