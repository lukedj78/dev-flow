"""Direct tests for update_meta.py: record-artifact, and the edges of set-phase and append-history.

    cd dev-flow/scripts && python3 -m unittest test_update_meta -v

Concurrency, phases, gates and history have their own files (test_meta_io, test_phases,
test_gate_doors, test_history). This one covers what is left: what record-artifact stores, what it
refuses, and the input errors of the other two operations. Every refusal must leave meta.json as it was.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent


def sha(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


class Fixture(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.outside = Path(self._tmp.name)
        self.root = self.outside / "proj"
        (self.root / ".workflow").mkdir(parents=True)
        self.meta_path = self.root / ".workflow" / "meta.json"
        self.meta_path.write_text(json.dumps({
            "phase": "idea_captured", "history": [], "artifacts": {},
            "inventory": {"verdict": "skipped", "reason": "test"}, "custom": {"kept": True},
        }))

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def meta(self) -> dict:
        return json.loads(self.meta_path.read_text())

    def update(self, *argv: str) -> subprocess.CompletedProcess:
        return subprocess.run([sys.executable, str(HERE / "update_meta.py"), str(self.root), *argv],
                              capture_output=True, text=True)

    def assert_refused_cleanly(self, r: subprocess.CompletedProcess, before: str, code: int = 1) -> None:
        self.assertEqual(r.returncode, code, r.stdout)
        self.assertNotIn("Traceback", r.stderr)
        self.assertEqual(self.meta_path.read_text(), before)


class RecordArtifact(Fixture):
    def test_records_hash_producer_and_time(self) -> None:
        (self.root / "DESIGN.md").write_text("v1")
        r = self.update("record-artifact", "--path", "DESIGN.md", "--produced-by", "image-to-design-md")
        self.assertEqual(r.returncode, 0, r.stderr)
        a = self.meta()["artifacts"]["DESIGN.md"]
        self.assertEqual((a["sha256"], a["produced_by"]), (sha("v1"), "image-to-design-md"))
        self.assertIn("produced_at", a)

    def test_recording_again_replaces_the_entry(self) -> None:
        f = self.root / "DESIGN.md"
        f.write_text("v1")
        self.update("record-artifact", "--path", "DESIGN.md", "--produced-by", "a")
        f.write_text("v2")
        self.update("record-artifact", "--path", "./sub/../DESIGN.md", "--produced-by", "b")
        arts = self.meta()["artifacts"]
        self.assertEqual(list(arts), ["DESIGN.md"])  # one entry, key normalized
        self.assertEqual((arts["DESIGN.md"]["sha256"], arts["DESIGN.md"]["produced_by"]), (sha("v2"), "b"))

    def test_derived_from_snapshots_the_inputs(self) -> None:
        (self.root / "DESIGN.md").write_text("tokens")
        (self.root / "registry.json").write_text("{}")
        r = self.update("record-artifact", "--path", "registry.json", "--produced-by", "design-md-to-app",
                        "--derived-from", "DESIGN.md")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(self.meta()["artifacts"]["registry.json"]["derived_from"],
                         [{"path": "DESIGN.md", "sha256": sha("tokens")}])

    def test_keeps_fields_it_does_not_know(self) -> None:
        (self.root / "f.txt").write_text("x")
        self.update("record-artifact", "--path", "f.txt", "--produced-by", "t")
        self.assertEqual(self.meta()["custom"], {"kept": True})

    def test_a_missing_file_is_refused(self) -> None:
        before = self.meta_path.read_text()
        self.assert_refused_cleanly(self.update("record-artifact", "--path", "nope.md", "--produced-by", "t"), before)

    def test_a_missing_input_is_refused(self) -> None:
        (self.root / "out.json").write_text("{}")
        before = self.meta_path.read_text()
        r = self.update("record-artifact", "--path", "out.json", "--produced-by", "t", "--derived-from", "nope.md")
        self.assert_refused_cleanly(r, before)

    def test_paths_outside_the_project_are_refused_without_a_traceback(self) -> None:
        secret = self.outside / "secret.txt"
        secret.write_text("s")
        (self.root / "link.txt").symlink_to(secret)
        (self.root / "f.txt").write_text("x")
        cases = {
            "absolute": ["--path", str(secret)],
            "dot-dot": ["--path", "../secret.txt"],
            "symlink out": ["--path", "link.txt"],
            "input outside": ["--path", "f.txt", "--derived-from", "../secret.txt"],
        }
        for name, argv in cases.items():
            with self.subTest(name):
                before = self.meta_path.read_text()
                r = self.update("record-artifact", *argv, "--produced-by", "t")
                self.assert_refused_cleanly(r, before)
                self.assertIn("outside the project", r.stderr)


class Inputs(Fixture):
    def test_no_meta_json(self) -> None:
        os.remove(self.meta_path)
        r = self.update("set-phase", "prd_drafted")
        self.assertEqual(r.returncode, 1)
        self.assertIn("init_workflow.py", r.stderr)

    def test_set_phase_to_a_phase_that_does_not_exist(self) -> None:
        before = self.meta_path.read_text()
        r = self.update("set-phase", "tasks_ready")
        self.assert_refused_cleanly(r, before)
        self.assertIn("Unknown phase", r.stderr)

    def test_append_history_with_malformed_json(self) -> None:
        before = self.meta_path.read_text()
        for flag in ("--inputs", "--outputs"):
            with self.subTest(flag):
                self.assert_refused_cleanly(self.update("append-history", "--skill", "x", flag, "{nope"), before)

    def test_append_history_to_a_phase_that_does_not_exist(self) -> None:
        before = self.meta_path.read_text()
        r = self.update("append-history", "--skill", "x", "--phase-after", "tasks_ready")
        self.assert_refused_cleanly(r, before, code=2)

    def test_append_history_stores_inputs_and_outputs(self) -> None:
        r = self.update("append-history", "--skill", "prd-from-idea",
                        "--inputs", '{"idea": "x"}', "--outputs", '["PRD.md"]')
        self.assertEqual(r.returncode, 0, r.stderr)
        h = self.meta()["history"][-1]
        self.assertEqual((h["inputs"], h["outputs"]), ({"idea": "x"}, ["PRD.md"]))


if __name__ == "__main__":
    unittest.main()
