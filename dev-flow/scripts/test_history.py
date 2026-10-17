"""History tells the truth about phase: every change is recorded, and nothing records a change that did not happen.

    cd dev-flow/scripts && python3 -m unittest test_history -v

Why this exists: `set-phase` changed the phase without a history entry, and `append-history
--phase-after X` recorded X even when X was behind the current phase and was not applied. So the
history could name a phase the project never had, and miss the moves it did make (AUDIT.md §6.2).
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent


class Fixture(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        (self.root / ".workflow").mkdir()
        self.meta_path = self.root / ".workflow" / "meta.json"
        # inventory on record, so phase handling is the only thing under test
        self.meta_path.write_text(json.dumps({
            "phase": "idea_captured", "history": [], "artifacts": {}, "stack": {},
            "inventory": {"verdict": "skipped", "reason": "test"},
        }))

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def meta(self) -> dict:
        return json.loads(self.meta_path.read_text())

    def update(self, *argv: str) -> subprocess.CompletedProcess:
        return subprocess.run([sys.executable, str(HERE / "update_meta.py"), str(self.root), *argv],
                              capture_output=True, text=True)

    def assert_history_matches_phase(self) -> None:
        moves = [h for h in self.meta()["history"] if h.get("phase_after") is not None]
        if moves:
            self.assertEqual(moves[-1]["phase_after"], self.meta()["phase"])


class SetPhase(Fixture):
    def test_a_phase_change_is_recorded(self) -> None:
        r = self.update("set-phase", "tasks_split", "--skill", "prd-to-tasks")
        self.assertEqual(r.returncode, 0, r.stderr)
        h = self.meta()["history"][-1]
        self.assertEqual((h["skill"], h["action"]), ("prd-to-tasks", "set-phase"))
        self.assertEqual((h["phase_before"], h["phase_after"]), ("idea_captured", "tasks_split"))
        self.assertIn("ran_at", h)
        self.assert_history_matches_phase()

    def test_without_skill_the_entry_still_says_what_moved_it(self) -> None:
        self.update("set-phase", "prd_drafted")
        self.assertEqual(self.meta()["history"][-1]["skill"], "set-phase")

    def test_setting_the_current_phase_records_nothing(self) -> None:
        self.update("set-phase", "idea_captured")
        self.assertEqual(self.meta()["history"], [])

    def test_a_refused_change_records_nothing(self) -> None:
        r = self.update("set-phase", "empty")  # regression, no --allow-regress
        self.assertEqual(r.returncode, 1)
        self.assertEqual(self.meta()["history"], [])

    def test_a_reset_is_visible(self) -> None:
        r = self.update("set-phase", "empty", "--allow-regress")
        self.assertEqual(r.returncode, 0, r.stderr)
        h = self.meta()["history"][-1]
        self.assertTrue(h["allow_regress"])
        self.assertEqual((h["phase_before"], h["phase_after"]), ("idea_captured", "empty"))
        self.assert_history_matches_phase()


class AppendHistory(Fixture):
    def test_a_phase_behind_the_current_one_is_not_recorded_as_reached(self) -> None:
        self.update("set-phase", "tasks_split")
        r = self.update("append-history", "--skill", "late", "--phase-after", "prd_drafted")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("stays", r.stderr)
        h = self.meta()["history"][-1]
        self.assertEqual(h["phase_after"], "tasks_split")
        self.assertEqual(h["phase_requested"], "prd_drafted")
        self.assertEqual(self.meta()["phase"], "tasks_split")
        self.assert_history_matches_phase()

    def test_a_forward_move_is_recorded_as_before(self) -> None:
        r = self.update("append-history", "--skill", "prd-from-idea", "--phase-after", "prd_drafted")
        self.assertEqual(r.returncode, 0, r.stderr)
        h = self.meta()["history"][-1]
        self.assertEqual((h["phase_before"], h["phase_after"]), ("idea_captured", "prd_drafted"))
        self.assertNotIn("phase_requested", h)

    def test_a_run_without_a_phase_claims_none(self) -> None:
        self.update("append-history", "--skill", "forms")
        self.assertIsNone(self.meta()["history"][-1]["phase_after"])

    def test_history_and_phase_agree_after_any_sequence(self) -> None:
        for argv in (["set-phase", "prd_drafted"],
                     ["append-history", "--skill", "a", "--phase-after", "tasks_split"],
                     ["append-history", "--skill", "b", "--phase-after", "prd_drafted"],
                     ["append-history", "--skill", "c"],
                     ["set-phase", "design_extracted"],
                     ["set-phase", "prd_drafted", "--allow-regress"]):
            with self.subTest(argv=argv):
                r = self.update(*argv)
                self.assertEqual(r.returncode, 0, r.stderr)
                self.assert_history_matches_phase()


if __name__ == "__main__":
    unittest.main()
