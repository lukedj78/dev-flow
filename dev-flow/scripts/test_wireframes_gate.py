"""Tests for wireframes_gate.py and its two doors in update_meta.py. Temp directories only.

    cd dev-flow/scripts && python3 -m unittest test_wireframes_gate -v
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import wireframes_gate as gate  # noqa: E402

APPROVED = {"canvas_url": "https://claude.ai/artifact/x", "inventory": "docs/wireframes/screen-inventory.md",
            "screens": 3, "artboards": 6, "approved_at": "2026-10-10T10:00:00Z", "approved_by_user": True}


class Verify(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        (self.root / "docs/wireframes").mkdir(parents=True)
        (self.root / "docs/wireframes/screen-inventory.md").write_text("# inventory\n")

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def ok(self, wf: dict | None, framework: str = "next") -> bool:
        meta = {"stack": {"framework": framework}}
        if wf is not None:
            meta["wireframes"] = wf
        return gate.verify(self.root, meta)[0]

    def test_missing_block_is_undecided_and_refused(self) -> None:
        self.assertFalse(self.ok(None))

    def test_an_approved_canvas_passes(self) -> None:
        self.assertTrue(self.ok(APPROVED))

    def test_not_approved_by_the_user_is_refused(self) -> None:
        self.assertFalse(self.ok({**APPROVED, "approved_by_user": False}))
        self.assertFalse(self.ok({**APPROVED, "approved_at": None}))

    def test_every_screen_needs_desktop_and_phone(self) -> None:
        self.assertFalse(self.ok({**APPROVED, "artboards": 5}))

    def test_the_inventory_must_exist_on_disk(self) -> None:
        self.assertFalse(self.ok({**APPROVED, "inventory": "docs/wireframes/nope.md"}))

    def test_skip_needs_a_reason(self) -> None:
        self.assertFalse(self.ok({"skipped": True}))
        self.assertTrue(self.ok({"skipped": True, "reason": "internal CLI, one screen"}))

    def test_agent_only_has_no_screens(self) -> None:
        self.assertTrue(self.ok(None, framework="agent"))

    def test_mobile_is_covered(self) -> None:
        self.assertFalse(self.ok(None, framework="expo-rn"))


class Doors(unittest.TestCase):
    """set-phase and append-history --phase-after both check it; the scaffold gates are opted out here."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        (self.root / ".workflow").mkdir()
        self.meta = {"project_slug": "t", "phase": "design_extracted", "history": [],
                     "stack": {"framework": "expo-rn", "data_residency": "none"}}
        self.write()

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def write(self) -> None:
        (self.root / ".workflow/meta.json").write_text(json.dumps(self.meta))

    def phase(self) -> str:
        return json.loads((self.root / ".workflow/meta.json").read_text())["phase"]

    def update(self, *args: str) -> subprocess.CompletedProcess:
        return subprocess.run([sys.executable, str(HERE / "update_meta.py"), str(self.root), *args],
                              capture_output=True, text=True, check=False)

    def test_set_phase_refuses_the_scaffold_without_a_canvas(self) -> None:
        r = self.update("set-phase", "scaffolded")
        self.assertEqual(r.returncode, 1)
        self.assertIn("wireframe canvas", r.stderr)
        self.assertIn("wireframes.py", r.stderr)
        self.assertEqual(self.phase(), "design_extracted")

    def test_the_monorepo_checkpoint_is_already_code(self) -> None:
        self.meta["stack"]["framework"] = "monorepo"
        self.write()
        self.assertEqual(self.update("set-phase", "monorepo_initialized").returncode, 1)

    def test_append_history_is_not_a_back_door(self) -> None:
        r = self.update("append-history", "--skill", "rn-bootstrap", "--phase-after", "scaffolded")
        self.assertEqual(r.returncode, 1)
        self.assertEqual(self.phase(), "design_extracted")

    def test_approval_or_a_reasoned_skip_lets_it_move(self) -> None:
        self.meta["wireframes"] = {"skipped": True, "reason": "a one-screen internal tool"}
        self.write()
        r = self.update("set-phase", "scaffolded")
        self.assertEqual(r.returncode, 0, r.stderr)

    def test_a_project_already_past_the_scaffold_is_not_asked_retroactively(self) -> None:
        self.meta["phase"] = "scaffolded"
        self.write()
        self.assertEqual(self.update("set-phase", "page_generated").returncode, 0)

    def test_planning_phases_are_not_gated(self) -> None:
        self.meta["phase"] = "prd_drafted"
        self.meta["inventory"] = {"verdict": "skipped", "reason": "test"}
        self.write()
        self.assertEqual(self.update("set-phase", "design_extracted").returncode, 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
