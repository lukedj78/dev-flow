"""Tests for founder.py, the only writer of meta.json#founder. Temp projects only.

    cd founder-intelligence/scripts && python3 -m unittest test_founder -v

Why this exists: the founder's approval is a fact the phase gate reads (dev-flow/scripts/founder_gate.py).
If the script that records it could approve without the founder's words, before the research is done,
or hash a Playbook it then edits, the gate would check nothing.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
FOUNDER = HERE / "founder.py"
PLAYBOOK = ".workflow/founder/founder-playbook.md"


def load_gate():
    spec = importlib.util.spec_from_file_location("founder_gate_for_test", REPO / "dev-flow/scripts/founder_gate.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


gate = load_gate()


class Fixture(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name) / "proj"
        self.root.mkdir()
        subprocess.run([sys.executable, str(REPO / "dev-flow/scripts/init_workflow.py"), str(self.root)],
                       check=True, capture_output=True)
        self.meta_path = self.root / ".workflow/meta.json"

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def run_founder(self, *argv: str) -> subprocess.CompletedProcess:
        return subprocess.run([sys.executable, str(FOUNDER), *argv], capture_output=True, text=True)

    def ok(self, *argv: str) -> subprocess.CompletedProcess:
        r = self.run_founder(*argv)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        return r

    def meta(self) -> dict:
        return json.loads(self.meta_path.read_text())

    def founder(self) -> dict:
        return self.meta()["founder"]

    def set_meta(self, **changes) -> None:
        meta = self.meta()
        meta.update(changes)
        self.meta_path.write_text(json.dumps(meta))

    def ready(self) -> None:
        """Started, research complete, inventory recorded: what approve needs."""
        self.ok("start", str(self.root), "--mode", "new")
        self.ok("record", str(self.root), "--research", "complete")
        self.set_meta(inventory={"verdict": "build", "searched": ["web"], "summary": "see Playbook §13"})

    def playbook(self) -> Path:
        return self.root / PLAYBOOK


class Start(Fixture):
    def test_start_creates_field_and_folder(self) -> None:
        self.ok("start", str(self.root), "--mode", "new")
        f = self.founder()
        self.assertEqual((f["mode"], f["research"], f["decision"], f["playbook"], f["version"]),
                         ("new", "in_progress", "pending", PLAYBOOK, 0))
        self.assertEqual(self.playbook().read_text(), (HERE.parent / "assets/founder-playbook.md").read_text())
        self.assertTrue((self.root / ".workflow/founder/sources.md").is_file())
        self.assertTrue((self.root / ".workflow/founder/interviews").is_dir())

    def test_start_twice_is_a_no_op(self) -> None:
        self.ok("start", str(self.root), "--mode", "new")
        self.playbook().write_text("# my work\n")
        before = (self.meta_path.read_bytes(), self.playbook().read_bytes())
        self.ok("start", str(self.root), "--mode", "new")
        self.assertEqual((self.meta_path.read_bytes(), self.playbook().read_bytes()), before)

    def test_start_reopens_stop_and_bypassed(self) -> None:
        for closing in (["decide", str(self.root), "stop", "--reason", "no market"],
                        ["bypass", str(self.root), "--reason", "internal tool"]):
            with self.subTest(closing=closing[0]):
                self.ok("start", str(self.root), "--mode", "new")
                self.ok(*closing)
                n = len(self.meta()["history"])
                self.ok("start", str(self.root), "--mode", "new")
                self.assertEqual(self.founder()["decision"], "pending")
                self.assertEqual(len(self.meta()["history"]), n + 1)

    def test_no_meta_json_exits_1(self) -> None:
        empty = Path(self._tmp.name) / "empty"
        empty.mkdir()
        r = self.run_founder("start", str(empty), "--mode", "new")
        self.assertEqual(r.returncode, 1)
        self.assertNotIn("Traceback", r.stderr)


class Record(Fixture):
    def test_record_sets_research_and_open_hypotheses(self) -> None:
        self.ok("start", str(self.root), "--mode", "new")
        self.ok("record", str(self.root), "--research", "complete", "--open", "H2", "H5")
        self.assertEqual((self.founder()["research"], self.founder()["open_hypotheses"]), ("complete", ["H2", "H5"]))

    def test_record_before_start_is_refused(self) -> None:
        r = self.run_founder("record", str(self.root), "--research", "complete")
        self.assertEqual(r.returncode, 1)
        self.assertIn("start", r.stderr)


class Approve(Fixture):
    def test_approve_needs_research_complete(self) -> None:
        self.ok("start", str(self.root), "--mode", "new")
        self.set_meta(inventory={"verdict": "build", "searched": ["web"], "summary": "x"})
        r = self.run_founder("approve", str(self.root), "--user-said", "sì")
        self.assertEqual(r.returncode, 1)
        self.assertIn("research", r.stderr)

    def test_approve_needs_inventory_verdict(self) -> None:
        self.ready()
        for inventory in (None, {"verdict": "skipped", "reason": "x"}):
            with self.subTest(inventory=inventory):
                meta = self.meta()
                meta.pop("inventory", None)
                if inventory:
                    meta["inventory"] = inventory
                self.meta_path.write_text(json.dumps(meta))
                r = self.run_founder("approve", str(self.root), "--user-said", "sì")
                self.assertEqual(r.returncode, 1)
                self.assertIn("inventory.py record", r.stderr)

    def test_approve_refuses_blank_user_said(self) -> None:
        self.ready()
        r = self.run_founder("approve", str(self.root), "--user-said", "   ")
        self.assertEqual(r.returncode, 1)
        self.assertNotEqual(self.founder()["decision"], "approved")

    def test_approve_writes_record_then_hashes(self) -> None:
        self.ready()
        self.ok("approve", str(self.root), "--user-said", "sì, procedi con lo sviluppo")
        f = self.founder()
        text = self.playbook().read_text()
        block = text.split("<!-- founder:approval -->")[1].split("<!-- /founder:approval -->")[0]
        self.assertIn("sì, procedi con lo sviluppo", block)
        self.assertIn("v1", block)
        self.assertEqual(f["playbook_sha256"], hashlib.sha256(self.playbook().read_bytes()).hexdigest())
        self.assertEqual((f["decision"], f["version"], f["approved_by_user"]), ("approved", 1, True))
        self.assertTrue(gate.verify(self.root, self.meta())[0])

    def test_approve_with_experiment_flags(self) -> None:
        self.ready()
        self.ok("approve", str(self.root), "--user-said", "solo la landing",
                "--experiment-scope", "landing page", "--experiment-objective", "demand",
                "--experiment-constraints", "2 weeks", "--experiment-acceptance", "50 signups")
        f = self.founder()
        self.assertEqual(f["decision"], "approved_experiment")
        self.assertEqual(sorted(f["experiment"]), ["acceptance", "constraints", "objective", "scope"])

    def test_partial_experiment_flags_are_refused(self) -> None:
        self.ready()
        r = self.run_founder("approve", str(self.root), "--user-said", "ok", "--experiment-scope", "landing")
        self.assertEqual(r.returncode, 1)
        self.assertEqual(self.founder()["decision"], "pending")

    def test_approve_refuses_without_markers(self) -> None:
        self.ready()
        self.playbook().write_text("# Playbook without the approval markers\n")
        before = self.playbook().read_bytes()
        r = self.run_founder("approve", str(self.root), "--user-said", "sì")
        self.assertEqual(r.returncode, 1)
        self.assertIn("<!-- founder:approval -->", r.stderr)
        self.assertEqual(self.playbook().read_bytes(), before)
        self.assertEqual(self.founder()["decision"], "pending")

    def test_edit_after_approval_needs_reapproval(self) -> None:
        self.ready()
        self.ok("approve", str(self.root), "--user-said", "sì")
        self.playbook().write_text(self.playbook().read_text() + "\none more line\n")
        self.assertFalse(gate.verify(self.root, self.meta())[0])
        self.ok("approve", str(self.root), "--user-said", "sì, anche con la modifica")
        self.assertTrue(gate.verify(self.root, self.meta())[0])
        self.assertEqual(self.founder()["version"], 2)


class Decide(Fixture):
    def test_decide_revise_from_approved_reopens_gate(self) -> None:
        self.ready()
        self.ok("approve", str(self.root), "--user-said", "sì")
        self.ok("decide", str(self.root), "revise", "--reason", "il segmento è sbagliato")
        self.assertEqual((self.founder()["decision"], self.founder()["reason"]), ("revise", "il segmento è sbagliato"))
        self.assertFalse(gate.verify(self.root, self.meta())[0])

    def test_decide_needs_reason(self) -> None:
        self.ok("start", str(self.root), "--mode", "new")
        r = self.run_founder("decide", str(self.root), "stop", "--reason", " ")
        self.assertEqual(r.returncode, 1)


class Bypass(Fixture):
    def test_bypass_records_reason_and_gate_passes(self) -> None:
        self.ok("start", str(self.root), "--mode", "new")
        self.ok("bypass", str(self.root), "--reason", "it is an internal tool after all")
        self.assertEqual(self.founder()["decision"], "bypassed")
        self.assertTrue(gate.verify(self.root, self.meta())[0])


class Status(Fixture):
    def labels_for(self, **founder) -> str:
        base = {"mode": "new", "research": "in_progress", "decision": "pending", "playbook": PLAYBOOK,
                "version": 0, "open_hypotheses": []}
        base.update(founder)
        self.set_meta(founder=base)
        return self.ok("status", str(self.root)).stdout

    def test_status_prints_labels(self) -> None:
        self.ok("start", str(self.root), "--mode", "new")
        out = self.labels_for(research="complete")
        self.assertIn("RESEARCH_COMPLETE", out)
        self.assertIn("READY_FOR_FOUNDER_APPROVAL", out)
        self.assertNotIn("NEEDS_VALIDATION", out)
        self.assertIn("NEEDS_VALIDATION", self.labels_for(research="complete", open_hypotheses=["H1"]))
        self.assertIn("APPROVED_FOR_DEVFLOW", self.labels_for(research="complete", decision="approved"))
        self.assertIn("REVISE_OR_STOP", self.labels_for(decision="stop", reason="x"))

    def test_status_at_ready_says_how_to_record_each_decision(self) -> None:
        self.ok("start", str(self.root), "--mode", "new")
        out = self.labels_for(research="complete")
        for cmd in ("approve", "decide", "revise", "bypass"):
            self.assertIn(cmd, out.split("Labels:")[1])

    def test_start_existing_names_handoff(self) -> None:
        out = self.ok("start", str(self.root), "--mode", "existing").stdout
        self.assertIn("handoff.md", out)

    def test_status_reports_malformed_block(self) -> None:
        self.set_meta(founder={"mode": "new", "decision": "maybe"})
        r = self.run_founder("status", str(self.root))
        self.assertEqual(r.returncode, 1)
        self.assertIn("maybe", r.stdout + r.stderr)
        self.assertNotIn("Traceback", r.stderr)

    def test_status_and_approve_refuse_other_hand_edits_without_traceback(self) -> None:
        self.ready()
        good = self.founder()
        for bad in ({"open_hypotheses": [1, 2]}, {"decision": "approved", "playbook": None},
                    {"playbook": 7}, {"version": "x"}):
            with self.subTest(bad=bad):
                block = dict(good)
                block.update(bad)
                if bad.get("playbook", "keep") is None:
                    block.pop("playbook")
                self.set_meta(founder=block)
                for argv in (("status", str(self.root)), ("approve", str(self.root), "--user-said", "sì")):
                    r = self.run_founder(*argv)
                    self.assertEqual(r.returncode, 1, (argv, r.stdout, r.stderr))
                    self.assertNotIn("Traceback", r.stderr)

    def test_labels_helper(self) -> None:
        spec = importlib.util.spec_from_file_location("founder_mod", FOUNDER)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        self.assertEqual(mod.labels({"research": "complete", "decision": "pending", "open_hypotheses": ["H1"]}),
                         ["RESEARCH_COMPLETE", "READY_FOR_FOUNDER_APPROVAL", "NEEDS_VALIDATION"])
        self.assertEqual(mod.labels({"research": "in_progress", "decision": "revise"}), ["REVISE_OR_STOP"])


class Records(Fixture):
    def test_every_write_appends_history(self) -> None:
        self.ready()
        n = len(self.meta()["history"])
        self.ok("approve", str(self.root), "--user-said", "sì")
        last = self.meta()["history"][-1]
        self.assertEqual(len(self.meta()["history"]), n + 1)
        self.assertEqual((last["skill"], last["action"], last["outputs"]["decision"]),
                         ("founder-intelligence", "approve", "approved"))

    def test_writes_are_confined(self) -> None:
        outside = Path(self._tmp.name) / "outside"
        outside.mkdir()
        (self.root / ".workflow/founder").symlink_to(outside)
        r = self.run_founder("start", str(self.root), "--mode", "new")
        self.assertEqual(r.returncode, 1)
        self.assertIn("outside the project", r.stderr)
        self.assertEqual(list(outside.iterdir()), [])


if __name__ == "__main__":
    unittest.main()
