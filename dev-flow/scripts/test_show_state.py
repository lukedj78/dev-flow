"""Direct tests for show_state.py: the routing table, phase-behind-the-code, and the read-only checks.

    cd dev-flow/scripts && python3 -m unittest test_show_state -v

show_state is the deterministic half of the router: dev-flow/SKILL.md tells the agent what to do,
and this prints the proposal from meta.json. Until now nothing tested it, which is how an unknown
phase came to print five "scaffolded" warnings and then route as `empty`.
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
import phases  # noqa: E402
import show_state as ss  # noqa: E402


class Routing(unittest.TestCase):
    def test_every_entry_of_the_table_is_what_it_proposes(self) -> None:
        for fw, table in ss.PHASE_NEXT_BY_STACK.items():
            for phase, proposal in table.items():
                with self.subTest(fw=fw, phase=phase):
                    self.assertIn(phase, phases.PHASES)
                    self.assertEqual(ss.next_step(phase, fw), proposal)

    def test_the_common_phases_route_the_same_on_every_stack(self) -> None:
        for fw in ss.PHASE_NEXT_BY_STACK:
            for phase, proposal in ss.COMMON_NEXT.items():
                with self.subTest(fw=fw, phase=phase):
                    self.assertEqual(ss.next_step(phase, fw), proposal)

    def test_a_valid_phase_is_never_called_unknown(self) -> None:
        # A phase the contract defines but a stack never passes through (agent-only has no page_generated)
        # used to print "unknown phase — treat as empty: prd-from-idea": send a built project back to the PRD.
        for fw in ss.PHASE_NEXT_BY_STACK:
            for phase in phases.PHASES:
                with self.subTest(fw=fw, phase=phase):
                    self.assertNotIn("unknown phase", ss.next_step(phase, fw))

    def test_no_framework_means_next(self) -> None:
        self.assertEqual(ss.next_step("scaffolded", None), ss.PHASE_NEXT_BY_STACK["next"]["scaffolded"])

    def test_an_unrecognized_framework_is_not_guessed(self) -> None:
        self.assertIn("refuses to guess", ss.next_step("scaffolded", "astro"))

    def test_a_legacy_spelling_routes_like_the_canonical_one(self) -> None:
        for old, new in phases.ALIASES.items():
            with self.subTest(old=old):
                self.assertEqual(ss.next_step(old, "next"), ss.next_step(new, "next"))

    def test_an_unknown_phase_routes_as_empty(self) -> None:
        self.assertEqual(ss.next_step("shipping", "next"), ss.COMMON_NEXT["empty"])


class TestLayers(unittest.TestCase):
    def test_the_stack_test_enum(self) -> None:
        for good in ("vitest", "vitest+playwright", "jest-expo+rntl+maestro"):
            self.assertTrue(ss.test_layers_ok(good), good)
        for bad in ("playwright+vitest", "vitest+vitest", "jest", "", ["vitest"], None):
            self.assertFalse(ss.test_layers_ok(bad), bad)


class Fixture(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        (self.root / ".workflow").mkdir()

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def write(self, **meta) -> None:
        (self.root / ".workflow" / "meta.json").write_text(json.dumps({"history": [], **meta}))

    def show(self) -> subprocess.CompletedProcess:
        return subprocess.run([sys.executable, str(HERE / "show_state.py"), str(self.root)],
                              capture_output=True, text=True)


class Output(Fixture):
    def test_no_meta_json(self) -> None:
        r = self.show()
        self.assertEqual(r.returncode, 1)
        self.assertIn("init_workflow.py", r.stdout)

    def test_prints_the_proposal_for_the_stack(self) -> None:
        self.write(phase="tasks_split", stack={"framework": "expo-rn"})
        r = self.show()
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn(ss.PHASE_NEXT_BY_STACK["expo-rn"]["tasks_split"], r.stdout)

    def test_a_phase_behind_the_code_asks_to_realign(self) -> None:
        # smart-travel: phase design_extracted, three days of pages, every check switched off.
        self.write(phase="design_extracted", stack={"framework": "next"})
        (self.root / "app").mkdir()
        (self.root / "app" / "page.tsx").write_text("export default function P() { return null }")
        out = self.show().stdout
        self.assertIn("PHASE BEHIND THE CODE", out)
        self.assertIn("REALIGN THE PHASE", out)

    def test_an_agent_only_project_is_not_behind_its_code(self) -> None:
        self.write(phase="tasks_split", stack={"framework": "agent"})
        (self.root / "app").mkdir()
        (self.root / "app" / "page.tsx").write_text("")
        self.assertNotIn("PHASE BEHIND THE CODE", self.show().stdout)

    def test_a_malformed_stack_test_is_reported(self) -> None:
        self.write(phase="tasks_split", stack={"framework": "next", "test": ["vitest"]})
        self.assertIn("stack.test is an array", self.show().stdout)

    def test_a_stale_stack_lint_is_reported(self) -> None:
        self.write(phase="tasks_split", stack={"framework": "next", "lint": "biome"})
        (self.root / "package.json").write_text(json.dumps({"devDependencies": {"eslint": "9"}}))
        self.assertIn("stack.lint says biome, the repository runs eslint", self.show().stdout)


if __name__ == "__main__":
    unittest.main()
