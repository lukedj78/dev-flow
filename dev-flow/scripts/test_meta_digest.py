"""A hand edit of meta.json is recognised, and a phase moved by hand does not skip the gates.

    cd dev-flow/scripts && python3 -m unittest test_meta_digest -v

Why this exists: the contract allows editing meta.json directly as a fallback, and nothing told such an
edit from a scripted write. A phase moved by hand skipped every gate, and the next `set-phase` did not
check them either, since it started from the phase already "reached". In a 5-session compliance trial
(2026-10-17) one agent rewrote meta.json with inline Python. Every write through meta_io now stamps
`meta_digest`: a hash of the content, and the last phase the gates checked.
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
import meta_io  # noqa: E402


class Fixture(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        (self.root / ".workflow").mkdir()
        (self.root / "f.txt").write_text("x")
        self.meta_path = self.root / ".workflow" / "meta.json"
        # A Next app on shadcn with every gate but data residency satisfied, so a refusal names that gate.
        self.meta_path.write_text(json.dumps({
            "phase": "design_extracted", "history": [], "artifacts": {},
            "stack": {"framework": "next", "ui": "shadcn", "design_lint": "none", "registry_intake": "none",
                      "primitives_guard": "none", "data_residency": None},
            "stack_config": {"design_lint_reason": "t", "registry_intake_reason": "t", "primitives_guard_reason": "t"},
            "inventory": {"verdict": "skipped", "reason": "t"}, "wireframes": {"skipped": True, "reason": "t"},
        }))

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def meta(self) -> dict:
        return json.loads(self.meta_path.read_text())

    def hand_edit(self, **changes) -> None:
        meta = self.meta()
        for key, value in changes.items():
            if key == "stack":
                meta["stack"].update(value)
            else:
                meta[key] = value
        self.meta_path.write_text(json.dumps(meta))   # not through meta_io: what an agent's inline Python does

    def script(self, *argv: str) -> subprocess.CompletedProcess:
        return subprocess.run([sys.executable, str(HERE / argv[0]), *argv[1:]], capture_output=True, text=True)

    def show(self) -> str:
        return self.script("show_state.py", str(self.root)).stdout

    def stamp(self) -> None:
        r = self.script("update_meta.py", str(self.root), "append-history", "--skill", "stamp")
        self.assertEqual(r.returncode, 0, r.stderr)


class Digest(Fixture):
    def test_a_scripted_write_stamps_the_digest(self) -> None:
        self.stamp()
        d = self.meta()["meta_digest"]
        self.assertEqual(d["checked_phase"], "design_extracted")
        self.assertEqual(d["sha256"], meta_io.digest_of(self.meta()))
        self.assertNotIn("changed outside", self.show())

    def test_a_file_from_before_the_field_raises_nothing(self) -> None:
        self.assertNotIn("changed outside", self.show())
        self.assertNotIn("without the gates", self.show())

    def test_reformatting_is_not_an_edit(self) -> None:
        self.stamp()
        self.meta_path.write_text(json.dumps(self.meta(), indent=4, sort_keys=True))  # what prettier might do
        self.assertNotIn("changed outside", self.show())

    def test_a_hand_edit_is_reported_until_the_next_scripted_write(self) -> None:
        self.stamp()
        self.hand_edit(stack={"email": "resend"})
        self.assertIn("changed outside", self.show())
        self.stamp()
        self.assertNotIn("changed outside", self.show())


class HandMovedPhase(Fixture):
    def setUp(self) -> None:
        super().setUp()
        self.stamp()                                   # checked at design_extracted
        self.hand_edit(phase="scaffolded")             # moved by hand past the residency gate

    def test_it_is_named(self) -> None:
        out = self.show()
        self.assertIn("without the gates", out)
        self.assertIn("design_extracted", out)

    def test_the_next_set_phase_checks_the_gates_it_skipped(self) -> None:
        r = self.script("update_meta.py", str(self.root), "set-phase", "page_generated")
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("data-residency decision", r.stderr)
        self.assertEqual(self.meta()["phase"], "scaffolded")

    def test_append_history_at_the_hand_set_phase_is_gated_too(self) -> None:
        r = self.script("update_meta.py", str(self.root), "append-history", "--skill", "x", "--phase-after", "scaffolded")
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("data-residency decision", r.stderr)

    def test_another_scripted_write_does_not_launder_it(self) -> None:
        r = self.script("update_meta.py", str(self.root), "record-artifact", "--path", "f.txt", "--produced-by", "t")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(self.meta()["meta_digest"]["checked_phase"], "design_extracted")
        r = self.script("update_meta.py", str(self.root), "set-phase", "page_generated")
        self.assertEqual(r.returncode, 1)

    def test_once_the_gate_passes_the_phase_is_checked(self) -> None:
        self.hand_edit(stack={"data_residency": "eu"})
        r = self.script("update_meta.py", str(self.root), "set-phase", "page_generated")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(self.meta()["meta_digest"]["checked_phase"], "page_generated")
        self.assertNotIn("without the gates", self.show())


if __name__ == "__main__":
    unittest.main()
