"""Tests for phases.py: one phase enum and one alias table, for every script that reads or moves a phase.

    cd dev-flow/scripts && python3 -m unittest test_phases -v

Why these exist: show_state.py and update_meta.py kept separate alias tables. show_state read
`page-generated` as `page_generated`; update_meta did not know it, treated it as index -1, and
allowed `set-phase idea_captured` from a project that had pages, with exit 0 (AUDIT.md §6.2).
"""

from __future__ import annotations

import importlib.util
import json
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
sys.path.insert(0, str(HERE))
import phases  # noqa: E402
import show_state  # noqa: E402


def contract_phases() -> list[str]:
    text = (HERE.parent / "references" / "contracts.md").read_text()
    section = re.search(r"### `phase` enum \(canonical\)(.+?)(?=\n### )", text, re.S)
    assert section, "contracts.md has no '### `phase` enum (canonical)' section"
    return [r for r in re.findall(r"^\| *`([a-z_]+)`", section.group(1), re.M) if r != "phase"]


class OneDefinition(unittest.TestCase):
    def test_the_enum_is_the_contract_table(self) -> None:
        self.assertEqual(phases.PHASES, contract_phases())

    def test_aliases_point_at_real_phases(self) -> None:
        for old, new in phases.ALIASES.items():
            self.assertIn(new, phases.PHASES, old)
            self.assertNotIn(old, phases.PHASES)

    def test_show_state_pre_code_set_is_everything_before_the_scaffold(self) -> None:
        self.assertEqual(show_state.PRE_CODE_PHASES - {""}, set(phases.before("scaffolded")))

    def test_the_copy_in_design_md_to_app_matches(self) -> None:
        # design-md-to-app installs standalone and keeps its own copy of this set.
        src = REPO / "design-md-to-app" / "scripts" / "setup_design_lint.py"
        spec = importlib.util.spec_from_file_location("setup_design_lint", src)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        self.assertEqual(mod.PHASES_BEFORE_SCAFFOLD, set(phases.before("scaffolded")))

    def test_normalize_and_index(self) -> None:
        self.assertEqual(phases.normalize("module-added"), "module_added")
        self.assertEqual(phases.normalize("scaffolded"), "scaffolded")
        self.assertEqual(phases.index("page-generated"), phases.PHASES.index("page_generated"))
        self.assertIsNone(phases.index("shipping"))
        self.assertIsNone(phases.index(3))
        self.assertIsNone(phases.index(None))


class Fixture(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        (self.root / ".workflow").mkdir()
        self.meta_path = self.root / ".workflow" / "meta.json"

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def write(self, phase) -> None:
        # inventory on record, so the only thing under test is phase handling
        self.meta_path.write_text(json.dumps({
            "phase": phase, "history": [], "artifacts": {}, "stack": {},
            "inventory": {"verdict": "skipped", "reason": "test"},
        }))

    def phase(self):
        return json.loads(self.meta_path.read_text())["phase"]

    def update(self, *argv: str) -> subprocess.CompletedProcess:
        return subprocess.run([sys.executable, str(HERE / "update_meta.py"), str(self.root), *argv],
                              capture_output=True, text=True)


class Writes(Fixture):
    def test_a_legacy_spelling_cannot_be_regressed_through(self) -> None:
        for legacy in phases.ALIASES:
            with self.subTest(legacy=legacy):
                self.write(legacy)
                r = self.update("set-phase", "idea_captured")
                self.assertEqual(r.returncode, 1, r.stdout)
                self.assertIn("regression refused", r.stderr)
                self.assertEqual(self.phase(), legacy)

    def test_every_legacy_spelling_is_accepted_as_a_target_and_written_snake_case(self) -> None:
        for legacy, canonical in phases.ALIASES.items():
            with self.subTest(legacy=legacy):
                self.write("empty")
                if phases.PHASES.index(canonical) >= phases.PHASES.index("monorepo_initialized"):
                    continue  # past the wireframes gate; the target spelling is what is under test
                r = self.update("set-phase", legacy)
                self.assertEqual(r.returncode, 0, r.stderr)
                self.assertEqual(self.phase(), canonical)

    def test_an_unknown_current_phase_is_not_moved_without_allow_regress(self) -> None:
        # It may be a phase a newer contract added: moving it is a regression nobody can see.
        for bad in ("shipping", 3, None):
            with self.subTest(bad=bad):
                self.write(bad)
                r = self.update("set-phase", "idea_captured")
                self.assertEqual(r.returncode, 1, r.stdout)
                self.assertIn("not a phase", r.stderr)
                self.assertEqual(self.phase(), bad)
                r = self.update("set-phase", "idea_captured", "--allow-regress")
                self.assertEqual(r.returncode, 0, r.stderr)
                self.assertEqual(self.phase(), "idea_captured")

    def test_append_history_does_not_move_an_unknown_phase(self) -> None:
        self.write("shipping")
        r = self.update("append-history", "--skill", "x", "--phase-after", "idea_captured")
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertEqual(self.phase(), "shipping")
        r = self.update("append-history", "--skill", "x")  # recording a run without a phase still works
        self.assertEqual(r.returncode, 0, r.stderr)

    def test_a_missing_phase_is_empty(self) -> None:
        self.meta_path.write_text(json.dumps({"history": [], "inventory": {"verdict": "skipped", "reason": "t"}}))
        r = self.update("set-phase", "idea_captured")
        self.assertEqual(r.returncode, 0, r.stderr)


class Reads(Fixture):
    def show(self) -> str:
        return subprocess.run([sys.executable, str(HERE / "show_state.py"), str(self.root)],
                              capture_output=True, text=True).stdout

    def test_an_unknown_phase_is_read_as_empty_with_a_warning(self) -> None:
        # It used to print five "missing on a scaffolded project" warnings and then route as empty.
        self.write("shipping")
        out = self.show()
        self.assertIn("not a phase", out)
        self.assertNotIn("on a scaffolded project", out)
        self.assertIn("prd-from-idea", out)

    def test_a_legacy_spelling_routes_like_the_canonical_one(self) -> None:
        self.write("page-generated")
        self.assertNotIn("not a phase", self.show())


if __name__ == "__main__":
    unittest.main()
