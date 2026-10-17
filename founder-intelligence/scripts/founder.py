#!/usr/bin/env python3
"""The founder path's state as commands: the only writer of meta.json#founder.

    founder.py start   <root> --mode new|existing     create the field and .workflow/founder/ (no-op if present;
                                                       reopens a project left at stop or bypassed)
    founder.py status  <root>                         labels, open hypotheses, whether the Playbook changed since approval
    founder.py record  <root> --research in_progress|complete [--open H1 H2 ...]
    founder.py approve <root> --user-said "<the founder's words>"
                       [--experiment-scope S --experiment-objective O --experiment-constraints C --experiment-acceptance A]
    founder.py decide  <root> revise|stop --reason "<sentence>"
    founder.py bypass  <root> --reason "<sentence>"   leave the founder path for the direct one

Why this exists: on the founder path, the founder's approval of the Playbook is what authorises a PRD, and
`dev-flow/scripts/founder_gate.py` reads it at the crossing into `prd_drafted`. The approval is only worth
checking if it cannot be recorded without the founder's words, before the research is complete, or without
the inventory verdict the gate would otherwise ask for, and if the hash covers the Playbook as it stands
after the approval record is written into it. Stdlib only. Exit 0 done, 1 refused, 2 invalid meta.json.
"""

from __future__ import annotations

import argparse
import hashlib
import sys
from datetime import datetime, timezone
from pathlib import Path

import meta_io  # vendored copy of dev-flow/scripts/meta_io.py — lint_skills.py keeps the copies identical

HERE = Path(__file__).resolve().parent
TEMPLATE = HERE.parent / "assets" / "founder-playbook.md"
FOUNDER_DIR = ".workflow/founder"
PLAYBOOK = f"{FOUNDER_DIR}/founder-playbook.md"
BEGIN, END = "<!-- founder:approval -->", "<!-- /founder:approval -->"
MODES = ("new", "existing")
RESEARCH = ("in_progress", "complete")
DECISIONS = ("pending", "approved", "approved_experiment", "revise", "stop", "bypassed")
APPROVED = ("approved", "approved_experiment")
VERDICTS = ("have-it", "adapts", "halfway", "build")
EXPERIMENT = ("scope", "objective", "constraints", "acceptance")
SOURCES_HEAD = ("# Sources\n\n| # | URL | Read on | Published | What it supports | Decisions that depend on it |\n"
                "|---|---|---|---|---|---|\n")


class Refused(Exception):
    """A request this script will not carry out; the message names the fix."""


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def confined(root: Path, path: Path) -> Path:
    """The path, if it lands inside the project once every symlink on the way is followed; else refuse.
    The same rule as registry-intake's and the primitives guard's setup: checked right before each write."""
    if not path.resolve().is_relative_to(root.resolve()):
        raise Refused(f"{path} resolves to {path.resolve()}, outside the project {root}. A symlink on the way "
                      "would make this write land there; remove it and run again.")
    return path


def labels(founder: dict) -> list[str]:
    """The readiness labels people read, derived from the two axes (research, decision)."""
    out = []
    decision = founder.get("decision")
    if founder.get("research") == "complete":
        out.append("RESEARCH_COMPLETE")
        if decision == "pending":
            out.append("READY_FOR_FOUNDER_APPROVAL")
    if decision in APPROVED:
        out.append("APPROVED_FOR_DEVFLOW")
    elif decision in ("revise", "stop"):
        out.append("REVISE_OR_STOP")
    if founder.get("open_hypotheses"):
        out.append("NEEDS_VALIDATION")
    return out


def problems(founder: object) -> list[str]:
    """What is wrong with a block edited by hand. Empty when it is well formed."""
    if not isinstance(founder, dict):
        return [f"meta.json#founder is {type(founder).__name__}, not an object"]
    out = []
    for key, allowed in (("mode", MODES), ("research", RESEARCH), ("decision", DECISIONS)):
        if founder.get(key) not in allowed:
            out.append(f"founder.{key} is {founder.get(key)!r}; expected one of {', '.join(allowed)}")
    if not isinstance(founder.get("open_hypotheses", []), list):
        out.append("founder.open_hypotheses is not a list")
    return out


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class Project:
    def __init__(self, root: Path) -> None:
        self.root = root.resolve()
        self.meta_path = self.root / ".workflow" / "meta.json"
        if not self.meta_path.is_file():
            raise Refused(f"No .workflow/meta.json at {self.root}: run dev-flow/scripts/init_workflow.py first.")

    def load(self) -> dict:
        return meta_io.load_or_exit(self.meta_path)

    def founder(self, meta: dict) -> dict:
        founder = meta.get("founder")
        if founder is None:
            raise Refused(f"the founder path was not started here: run founder.py start {self.root} --mode new|existing")
        bad = problems(founder)
        if bad:
            raise Refused("meta.json#founder was edited by hand and is not valid:\n  " + "\n  ".join(bad))
        return founder

    def save(self, meta: dict, action: str, inputs: dict) -> None:
        founder = meta.get("founder") or {}
        meta.setdefault("history", []).append({
            "skill": "founder-intelligence", "action": action, "inputs": inputs,
            "outputs": {"decision": founder.get("decision"), "research": founder.get("research"),
                        "version": founder.get("version")},
            "phase_after": meta.get("phase"), "ran_at": now_iso()})
        meta["updated_at"] = now_iso()
        meta_io.write_json(confined(self.root, self.meta_path), meta)


def cmd_start(a: argparse.Namespace, p: Project) -> int:
    with meta_io.locked(p.meta_path.parent):
        meta = p.load()
        founder = meta.get("founder")
        if founder is not None:
            p.founder(meta)
            if founder["decision"] not in ("stop", "bypassed"):
                print(f"already started ({founder['mode']}, decision {founder['decision']}); nothing changed")
                return 0
            founder["decision"] = "pending"
            p.save(meta, "start", {"reopened_from": founder.get("reason")})
            print("reopened: decision is pending again")
            return 0
        folder = confined(p.root, p.root / FOUNDER_DIR)
        (confined(p.root, folder / "interviews")).mkdir(parents=True, exist_ok=True)
        keep = confined(p.root, folder / "interviews" / ".gitkeep")
        if not keep.exists():
            keep.write_text("")
        playbook = confined(p.root, p.root / PLAYBOOK)
        if not playbook.exists():
            playbook.write_text(TEMPLATE.read_text())
        sources = confined(p.root, folder / "sources.md")
        if not sources.exists():
            sources.write_text(SOURCES_HEAD)
        meta["founder"] = {"mode": a.mode, "research": "in_progress", "decision": "pending",
                           "playbook": PLAYBOOK, "version": 0, "open_hypotheses": []}
        p.save(meta, "start", {"mode": a.mode})
    print(f"started ({a.mode}): {PLAYBOOK}, {FOUNDER_DIR}/sources.md, {FOUNDER_DIR}/interviews/")
    return 0


def cmd_status(a: argparse.Namespace, p: Project) -> int:
    meta = p.load()
    founder = meta.get("founder")
    if founder is None:
        print("founder path not started: this project is on the direct path")
        return 0
    bad = problems(founder)
    if bad:
        print("meta.json#founder is not valid:\n  " + "\n  ".join(bad))
        return 1
    print(f"Founder:  {founder['mode']} · research {founder['research']} · decision {founder['decision']} "
          f"· Playbook v{founder.get('version', 0)}")
    print(f"Labels:   {' · '.join(labels(founder)) or '(none)'}")
    if founder.get("open_hypotheses"):
        print(f"Open:     {', '.join(founder['open_hypotheses'])}")
    if founder["decision"] in APPROVED:
        path = p.root / founder["playbook"]
        if not path.is_file() or sha256(path) != founder.get("playbook_sha256"):
            print("⚠ the Playbook changed after approval (or is missing): the founder must approve it again")
    if founder.get("reason"):
        print(f"Reason:   {founder['reason']}")
    return 0


def cmd_record(a: argparse.Namespace, p: Project) -> int:
    with meta_io.locked(p.meta_path.parent):
        meta = p.load()
        founder = p.founder(meta)
        founder["research"] = a.research
        if a.open is not None:
            founder["open_hypotheses"] = list(a.open)
        p.save(meta, "record", {"research": a.research, "open": a.open})
    print(f"research {a.research} · open hypotheses: {', '.join(founder['open_hypotheses']) or 'none'}")
    return 0


def approval_block(version: int, at: str, quote: str, experiment: dict | None) -> str:
    lines = [f"Approved v{version} on {at} by the founder: “{quote}”"]
    if experiment:
        lines.append("Approved for a limited experiment only:")
        lines += [f"- {k}: {experiment[k]}" for k in EXPERIMENT]
    return "\n".join(lines)


def cmd_approve(a: argparse.Namespace, p: Project) -> int:
    quote = (a.user_said or "").strip()
    if not quote:
        raise Refused("--user-said must quote the founder's own approval; nobody else can give it.")
    given = {k: (getattr(a, f"experiment_{k}") or "").strip() for k in EXPERIMENT}
    if any(given.values()) and not all(given.values()):
        missing = ", ".join(f"--experiment-{k}" for k, v in given.items() if not v)
        raise Refused(f"a limited experiment needs all four of scope, objective, constraints, acceptance: missing {missing}")
    experiment = given if all(given.values()) else None
    with meta_io.locked(p.meta_path.parent):
        meta = p.load()
        founder = p.founder(meta)
        if founder["decision"] in ("stop", "bypassed"):
            raise Refused(f"the decision is {founder['decision']}: reopen with founder.py start {p.root} first")
        if founder["research"] != "complete":
            raise Refused("research is still in progress: finish the stages and run founder.py record "
                          "--research complete before asking for approval")
        inv = meta.get("inventory") or {}
        if inv.get("verdict") not in VERDICTS or not inv.get("searched"):
            raise Refused("no inventory verdict yet: at the feasibility stage run dev-flow/scripts/inventory.py record "
                          "<root> --verdict have-it|adapts|halfway|build --searched <channels> --summary <Playbook §13>")
        path = confined(p.root, p.root / founder["playbook"])
        if not path.is_file():
            raise Refused(f"the Playbook {founder['playbook']} is not on disk")
        text = path.read_text()
        if text.count(BEGIN) != 1 or text.count(END) != 1 or text.index(BEGIN) > text.index(END):
            raise Refused(f"the Playbook needs exactly one approval section between {BEGIN} and {END}; restore "
                          "the two marker lines (see assets/founder-playbook.md §20) and run approve again")
        version = int(founder.get("version") or 0) + 1
        at = now_iso()
        i, j = text.index(BEGIN) + len(BEGIN), text.index(END)
        path.write_text(text[:i] + "\n" + approval_block(version, at, quote, experiment) + "\n" + text[j:])
        founder.update({"decision": "approved_experiment" if experiment else "approved", "version": version,
                        "playbook_sha256": sha256(path), "approved_at": at, "approved_by_user": True,
                        "approval_quote": quote})
        if experiment:
            founder["experiment"] = experiment
        else:
            founder.pop("experiment", None)
        p.save(meta, "approve", {"user_said": quote, "experiment": experiment})
    print(f"approved v{version} ({founder['decision']}); dev-flow can move on to prd-from-idea")
    return 0


def cmd_decide(a: argparse.Namespace, p: Project) -> int:
    reason = (a.reason or "").strip()
    if not reason:
        raise Refused("--reason is required: the founder's decision is kept with why they took it")
    with meta_io.locked(p.meta_path.parent):
        meta = p.load()
        founder = p.founder(meta)
        founder["decision"], founder["reason"] = a.decision, reason
        p.save(meta, "decide", {"decision": a.decision, "reason": reason})
    print(f"recorded: {a.decision} — {reason}")
    return 0


def cmd_bypass(a: argparse.Namespace, p: Project) -> int:
    reason = (a.reason or "").strip()
    if not reason:
        raise Refused("--reason is required: leaving the founder path is kept with why")
    with meta_io.locked(p.meta_path.parent):
        meta = p.load()
        founder = p.founder(meta)
        founder["decision"], founder["reason"] = "bypassed", reason
        p.save(meta, "bypass", {"reason": reason})
    print(f"bypassed — {reason}. The direct path starts with the inventory (dev-flow/references/before-you-build.md).")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name, fn in (("start", cmd_start), ("status", cmd_status), ("record", cmd_record),
                     ("approve", cmd_approve), ("decide", cmd_decide), ("bypass", cmd_bypass)):
        sp = sub.add_parser(name)
        sp.add_argument("root", type=Path)
        sp.set_defaults(func=fn)
        if name == "start":
            sp.add_argument("--mode", choices=MODES, required=True)
        elif name == "record":
            sp.add_argument("--research", choices=RESEARCH, required=True)
            sp.add_argument("--open", nargs="*")
        elif name == "approve":
            sp.add_argument("--user-said", required=True)
            for k in EXPERIMENT:
                sp.add_argument(f"--experiment-{k}")
        elif name == "decide":
            sp.add_argument("decision", choices=("revise", "stop"))
            sp.add_argument("--reason", required=True)
        elif name == "bypass":
            sp.add_argument("--reason", required=True)
    a = ap.parse_args(argv)
    try:
        return a.func(a, Project(a.root))
    except Refused as e:
        print(f"Refused: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
