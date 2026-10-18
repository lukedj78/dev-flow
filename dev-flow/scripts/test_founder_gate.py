"""Tests for founder_gate.py and its two doors in update_meta.py. Temp directories only.

    cd dev-flow/scripts && python3 -m unittest test_founder_gate -v

Why this exists: on the founder path the founder's approval of the Playbook is what authorises a PRD.
Left to prose, an agent told "go straight to the PRD" would skip it. The gate applies only once
founder-intelligence has started (meta.json#founder exists), so the direct path does not change.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import founder_gate as gate  # noqa: E402
import meta_io  # noqa: E402

PLAYBOOK = ".workflow/founder/founder-playbook.md"


class Fixture(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        (self.root / ".workflow/founder").mkdir(parents=True)
        self.playbook = self.root / PLAYBOOK
        self.playbook.write_text("# Playbook\n\napproved text\n")
        self.meta_path = self.root / ".workflow/meta.json"

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def sha(self) -> str:
        return hashlib.sha256(self.playbook.read_bytes()).hexdigest()

    def approved(self, **over) -> dict:
        block = {"mode": "new", "research": "complete", "decision": "approved", "playbook": PLAYBOOK,
                 "version": 1, "playbook_sha256": self.sha(), "open_hypotheses": [],
                 "approved_at": "2026-10-17T10:00:00Z", "approved_by_user": True, "approval_quote": "sì, procedi"}
        block.update(over)
        return block

    def verify(self, founder) -> tuple[bool, str]:
        meta = {} if founder is None else {"founder": founder}
        return gate.verify(self.root, meta)


class Verify(Fixture):
    def test_absent_field_passes(self) -> None:
        self.assertTrue(self.verify(None)[0])

    def test_existing_mode_does_not_apply(self) -> None:
        self.assertFalse(gate.applies({"founder": {"mode": "existing", "decision": "pending"}}))
        self.assertTrue(self.verify({"mode": "existing", "decision": "pending"})[0])

    def test_pending_revise_stop_refuse_naming_the_decision(self) -> None:
        for decision in ("pending", "revise", "stop"):
            with self.subTest(decision=decision):
                ok, why = self.verify(self.approved(decision=decision))
                self.assertFalse(ok)
                self.assertIn(decision, why)

    def test_approved_passes_when_sha_matches(self) -> None:
        self.assertTrue(self.verify(self.approved())[0])

    def test_approved_experiment_passes(self) -> None:
        exp = {"scope": "landing page", "objective": "demand", "constraints": "2 weeks", "acceptance": "50 signups"}
        self.assertTrue(self.verify(self.approved(decision="approved_experiment", experiment=exp))[0])

    def test_playbook_changed_after_approval_refuses(self) -> None:
        block = self.approved()
        self.playbook.write_text(self.playbook.read_text() + "one more line\n")
        ok, why = self.verify(block)
        self.assertFalse(ok)
        self.assertIn("changed after approval", why)

    def test_playbook_missing_refuses_without_raising(self) -> None:
        block = self.approved()
        self.playbook.unlink()
        ok, why = self.verify(block)
        self.assertFalse(ok)
        self.assertIn(PLAYBOOK, why)

    def test_blank_quote_refuses(self) -> None:
        self.assertFalse(self.verify(self.approved(approval_quote="   "))[0])

    def test_not_approved_by_user_refuses(self) -> None:
        self.assertFalse(self.verify(self.approved(approved_by_user=False))[0])

    def test_bypassed_needs_a_reason(self) -> None:
        self.assertFalse(self.verify({"mode": "new", "decision": "bypassed", "reason": " "})[0])
        self.assertTrue(self.verify({"mode": "new", "decision": "bypassed", "reason": "internal tool after all"})[0])

    def test_malformed_block_refuses_without_raising(self) -> None:
        for bad in ("yes", ["approved"], [], {}, {"mode": "new", "decision": "maybe"},
                    self.approved(open_hypotheses="H1"), self.approved(playbook=None)):
            with self.subTest(bad=bad):
                ok, why = self.verify(bad)
                self.assertFalse(ok)
                self.assertTrue(why.strip())

    def test_remedy_names_the_script(self) -> None:
        text = gate.remedy(self.root)
        for word in ("founder.py", "approve", "decide", "bypass"):
            self.assertIn(word, text)


class Doors(Fixture):
    """The real update_meta.py, both doors, the other gates satisfied (the inventory is the only other one
    at the crossing into prd_drafted)."""

    def write(self, **meta) -> None:
        base = {"phase": "idea_captured", "history": [], "artifacts": {}, "stack": {},
                "inventory": {"verdict": "build", "searched": ["web"], "summary": "t"}}
        base.update(meta)
        self.meta_path.write_text(json.dumps(base))

    def run_door(self, *argv: str) -> subprocess.CompletedProcess:
        return subprocess.run([sys.executable, str(HERE / "update_meta.py"), str(self.root), *argv],
                              capture_output=True, text=True)

    DOORS = (("set-phase", "prd_drafted"), ("append-history", "--skill", "x", "--phase-after", "prd_drafted"))

    def test_both_doors_refuse_while_pending(self) -> None:
        self.write(founder=self.approved(decision="pending"))
        before = self.meta_path.read_bytes()
        for argv in self.DOORS:
            with self.subTest(door=argv[0]):
                r = self.run_door(*argv)
                self.assertEqual(r.returncode, 1, r.stdout)
                self.assertIn("founder", r.stderr.lower())
                self.assertEqual(self.meta_path.read_bytes(), before)

    def test_both_doors_pass_when_approved(self) -> None:
        for argv in self.DOORS:
            with self.subTest(door=argv[0]):
                self.write(founder=self.approved())
                r = self.run_door(*argv)
                self.assertEqual(r.returncode, 0, r.stderr)
                self.assertEqual(json.loads(self.meta_path.read_text())["phase"], "prd_drafted")

    def test_hand_moved_phase_is_still_checked(self) -> None:
        # Stamp checked_phase at idea_captured through a scripted write, then move the phase by hand.
        self.write(founder=self.approved(decision="pending"))
        r = self.run_door("append-history", "--skill", "stamp")
        self.assertEqual(r.returncode, 0, r.stderr)
        meta = json.loads(self.meta_path.read_text())
        self.assertEqual(meta_io.checked_phase(meta), "idea_captured")
        meta["phase"] = "tasks_split"
        self.meta_path.write_text(json.dumps(meta))
        r = self.run_door("set-phase", "design_extracted")
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("founder", r.stderr.lower())

    def test_direct_project_regression(self) -> None:
        self.write()   # no founder field: the direct path
        r = self.run_door("set-phase", "prd_drafted")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertNotIn("founder", (r.stdout + r.stderr).lower())


if __name__ == "__main__":
    unittest.main()
