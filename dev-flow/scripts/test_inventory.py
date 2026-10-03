"""Tests for inventory.py and inventory_gate.py. Temp directories only: nothing real is read or written.

    cd dev-flow/scripts && python3 -m unittest test_inventory -v
"""

from __future__ import annotations

import io
import json
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import inventory as inv  # noqa: E402
import inventory_gate as gate  # noqa: E402


def scan(root: Path, *keywords: str, missing: bool = False) -> tuple[int, str]:
    out = io.StringIO()
    argv = ["scan", *keywords,
            "--skills", str(root / "skills"),
            "--plugins", str(root / ("nope" if missing else "plugins")),
            "--projects", str(root / "projects"),
            "--resources", str(root / "resources.md")]
    with redirect_stdout(out):
        rc = inv.main(argv)
    return rc, out.getvalue()


class Fixture(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        for d in ("skills/some-skill", "plugins", "projects/bidmaster/.workflow"):
            (self.root / d).mkdir(parents=True)
        (self.root / "skills/some-skill/SKILL.md").write_text("---\nname: some-skill\n---\nDoes invoicing.\n")
        (self.root / "projects/bidmaster/.workflow/PROJECT.md").write_text("# BidMaster\nHandles tender and RFP work.\n")
        (self.root / "resources.md").write_text("| mapcn | maps | adopted |\n")

    def tearDown(self) -> None:
        self._tmp.cleanup()


class Scan(Fixture):
    def test_finds_another_project_on_the_machine(self) -> None:
        # The case that started this: a project with the same idea sat in ~/projects and nobody looked.
        rc, out = scan(self.root, "tender")
        self.assertEqual(rc, inv.ANSWERED)
        self.assertIn("bidmaster", out)

    def test_finds_an_installed_skill_and_a_resource_row(self) -> None:
        self.assertIn("some-skill", scan(self.root, "invoicing")[1])
        self.assertIn("mapcn", scan(self.root, "maps")[1])

    def test_a_keyword_matches_a_word_start_not_the_inside_of_a_word(self) -> None:
        (self.root / "projects/bidmaster/.workflow/PROJECT.md").write_text("A site that looks abbandonato.\n")
        self.assertEqual(scan(self.root, "bando")[0], inv.EMPTY)
        (self.root / "projects/bidmaster/.workflow/PROJECT.md").write_text("Many tenders to handle.\n")
        self.assertEqual(scan(self.root, "tender")[0], inv.ANSWERED)

    def test_answered_with_nothing_is_its_own_code(self) -> None:
        rc, out = scan(self.root, "zzzzqqqq")
        self.assertEqual(rc, inv.EMPTY)
        self.assertIn("Searched:", out)

    def test_a_root_that_cannot_be_read_is_not_found_nothing(self) -> None:
        rc, out = scan(self.root, "tender", missing=True)
        self.assertEqual(rc, inv.UNREACHABLE)
        self.assertIn("NOT COVERED", out)

    def test_scan_writes_nothing(self) -> None:
        before = sorted(p.relative_to(self.root) for p in self.root.rglob("*"))
        scan(self.root, "tender")
        self.assertEqual(before, sorted(p.relative_to(self.root) for p in self.root.rglob("*")))


class Gate(unittest.TestCase):
    def test_no_inventory_is_refused(self) -> None:
        self.assertFalse(gate.verify(Path("."), {})[0])
        self.assertFalse(gate.verify(Path("."), {"inventory": {}})[0])

    def test_unknown_verdict_is_refused(self) -> None:
        self.assertFalse(gate.verify(Path("."), {"inventory": {"verdict": "maybe", "searched": ["x"]}})[0])

    def test_a_verdict_without_what_was_searched_is_refused(self) -> None:
        self.assertFalse(gate.verify(Path("."), {"inventory": {"verdict": "build", "searched": []}})[0])

    def test_a_complete_inventory_passes_even_when_the_verdict_is_have_it(self) -> None:
        self.assertTrue(gate.verify(Path("."), {"inventory": {"verdict": "have-it", "searched": ["~/projects"]}})[0])

    def test_skipping_needs_a_reason_and_is_then_allowed(self) -> None:
        self.assertFalse(gate.verify(Path("."), {"inventory": {"verdict": "skipped"}})[0])
        self.assertTrue(gate.verify(Path("."), {"inventory": {"verdict": "skipped", "reason": "throwaway spike"}})[0])


class SetPhase(unittest.TestCase):
    """The gate where phase actually moves — both doors."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        (self.root / ".workflow").mkdir()
        self.meta = {"project_slug": "t", "phase": "idea_captured", "stack": {}, "history": []}
        self.write()

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def write(self) -> None:
        (self.root / ".workflow" / "meta.json").write_text(json.dumps(self.meta))

    def phase(self) -> str:
        return json.loads((self.root / ".workflow" / "meta.json").read_text())["phase"]

    def update(self, *args: str) -> subprocess.CompletedProcess:
        return subprocess.run([sys.executable, str(HERE / "update_meta.py"), str(self.root), *args],
                              capture_output=True, text=True)

    def test_set_phase_refuses_without_inventory(self) -> None:
        r = self.update("set-phase", "prd_drafted")
        self.assertEqual(r.returncode, 1)
        self.assertIn("inventory", r.stderr)
        self.assertEqual(self.phase(), "idea_captured")

    def test_append_history_is_not_a_back_door(self) -> None:
        r = self.update("append-history", "--skill", "prd-from-idea", "--phase-after", "prd_drafted")
        self.assertEqual(r.returncode, 1)
        self.assertEqual(self.phase(), "idea_captured")
        self.assertEqual(json.loads((self.root / ".workflow" / "meta.json").read_text())["history"], [])

    def test_recorded_inventory_lets_the_phase_move(self) -> None:
        rc = subprocess.run([sys.executable, str(HERE / "inventory.py"), "record", str(self.root),
                             "--verdict", "halfway", "--searched", "skills", "projects"],
                            capture_output=True, text=True).returncode
        self.assertEqual(rc, 0)
        self.assertEqual(self.update("set-phase", "prd_drafted").returncode, 0)
        self.assertEqual(self.phase(), "prd_drafted")

    def test_a_project_already_past_the_threshold_is_not_asked_retroactively(self) -> None:
        self.meta["phase"] = "prd_drafted"
        self.write()
        self.assertEqual(self.update("set-phase", "tasks_split").returncode, 0)

    def test_record_refuses_a_skip_without_a_reason(self) -> None:
        r = subprocess.run([sys.executable, str(HERE / "inventory.py"), "record", str(self.root),
                            "--verdict", "skipped"], capture_output=True, text=True)
        self.assertEqual(r.returncode, 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
