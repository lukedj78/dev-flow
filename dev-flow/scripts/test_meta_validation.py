"""A meta.json that is not valid is refused cleanly by every script, and never rewritten.

    cd dev-flow/scripts && python3 -m unittest test_meta_validation -v

Why this exists: no script checked the file's shape. Malformed or empty JSON gave a raw traceback in
every one of them, init included; `history: {}` or `artifacts: []` crashed some and were rewritten by
others, which saved whatever junk they found (AUDIT.md §6.2). check_drift crashed on an artifact
recorded without a hash, which two real projects in ~/projects have.
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

def meta_io_sha(path: Path) -> str:
    import hashlib
    return hashlib.sha256(path.read_bytes()).hexdigest()


GOOD = {"phase": "idea_captured", "history": [], "artifacts": {}, "stack": {},
        "inventory": {"verdict": "skipped", "reason": "test"}}

BAD = {
    "malformed JSON": '{"phase": "empty",',
    "empty file": "",
    "a JSON array": "[]",
    "history is an object": json.dumps({**GOOD, "history": {}}),
    "history is null": json.dumps({**GOOD, "history": None}),
    "artifacts is a list": json.dumps({**GOOD, "artifacts": []}),
    "stack is a list": json.dumps({**GOOD, "stack": []}),
    "stack_config is a string": json.dumps({**GOOD, "stack_config": "x"}),
    "an artifact entry is a string": json.dumps({**GOOD, "artifacts": {"f.txt": "abc"}}),
}

# Every command of every dev-flow script that reads meta.json.
COMMANDS = {
    "show_state": ["show_state.py", "{root}"],
    "check_drift": ["check_drift.py", "{root}"],
    "set-phase": ["update_meta.py", "{root}", "set-phase", "prd_drafted"],
    "append-history": ["update_meta.py", "{root}", "append-history", "--skill", "x"],
    "record-artifact": ["update_meta.py", "{root}", "record-artifact", "--path", "f.txt", "--produced-by", "x"],
    "init_workflow": ["init_workflow.py", "{root}"],
    "inventory record": ["inventory.py", "record", "{root}", "--verdict", "skipped", "--reason", "x"],
    "data_residency add": ["data_residency.py", "add", "{root}", "--name", "V", "--service", "s", "--data", "d"],
    "data_residency decide": ["data_residency.py", "decide", "{root}", "--eu-subjects", "yes",
                              "--residency-obligations", "no", "--avoid-cloud-act", "no"],
}


class Fixture(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        (self.root / ".workflow").mkdir()
        (self.root / "f.txt").write_text("x")
        self.meta_path = self.root / ".workflow" / "meta.json"

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def run_cmd(self, argv: list[str]) -> subprocess.CompletedProcess:
        argv = [a.replace("{root}", str(self.root)) for a in argv]
        return subprocess.run([sys.executable, str(HERE / argv[0]), *argv[1:]], capture_output=True, text=True)


class EveryScriptRefusesCleanly(Fixture):
    def test_the_matrix(self) -> None:
        for case, text in BAD.items():
            for name, argv in COMMANDS.items():
                with self.subTest(case=case, command=name):
                    self.meta_path.write_text(text)
                    r = self.run_cmd(argv)
                    self.assertEqual(r.returncode, 2, r.stdout + r.stderr)
                    self.assertNotIn("Traceback", r.stderr)
                    self.assertIn("not a valid meta.json", r.stderr)
                    self.assertEqual(self.meta_path.read_text(), text, "the file was rewritten")

    def test_a_valid_file_still_works_everywhere(self) -> None:
        for name, argv in COMMANDS.items():
            with self.subTest(command=name):
                self.meta_path.write_text(json.dumps(GOOD))
                r = self.run_cmd(argv)
                self.assertNotIn("Traceback", r.stderr)
                self.assertNotIn("not a valid meta.json", r.stderr)


class ReadMeta(Fixture):
    def test_the_reason_is_specific(self) -> None:
        self.meta_path.write_text(json.dumps({**GOOD, "history": {}}))
        with self.assertRaises(meta_io.InvalidMeta) as e:
            meta_io.read_meta(self.meta_path)
        self.assertIn("history", str(e.exception))
        self.assertIn("not an array", str(e.exception))  # JSON's words: the reader is editing JSON

    def test_phase_is_left_to_the_phase_logic(self) -> None:
        # A wrong phase is refused by update_meta and repaired with set-phase --allow-regress,
        # which needs the file to load.
        for phase in ("shipping", 3, None):
            self.meta_path.write_text(json.dumps({**GOOD, "phase": phase}))
            self.assertEqual(meta_io.read_meta(self.meta_path)["phase"], phase)

    def test_missing_containers_are_fine(self) -> None:
        self.meta_path.write_text(json.dumps({"phase": "empty"}))
        self.assertEqual(meta_io.read_meta(self.meta_path), {"phase": "empty"})


class CheckDrift(Fixture):
    def drift(self, artifacts: dict) -> subprocess.CompletedProcess:
        self.meta_path.write_text(json.dumps({**GOOD, "artifacts": artifacts}))
        return self.run_cmd(["check_drift.py", "{root}", "--json", "--exit-nonzero-on-drift"])

    def test_an_artifact_without_a_hash_is_reported_not_a_crash(self) -> None:
        # idea-validator and predictionleagues have entries like this one.
        r = self.drift({"f.txt": {"produced_by": "design-md-to-app", "produced_at": "2026-05-04T20:55:00Z"}})
        self.assertNotIn("Traceback", r.stderr)
        self.assertEqual(r.returncode, 1)
        self.assertEqual(json.loads(r.stdout)["rows"][0]["status"], "unhashed")

    def test_inputs_recorded_as_bare_paths_still_propagate(self) -> None:
        # predictionleagues writes derived_from as ["path"], not [{"path", "sha256"}]; it crashed the check.
        (self.root / "DESIGN.md").write_text("tokens")
        r = self.drift({
            "DESIGN.md": {"sha256": "0" * 64, "produced_by": "x"},                       # drifted
            "f.txt": {"sha256": meta_io_sha(self.root / "f.txt"), "produced_by": "y", "derived_from": ["DESIGN.md"]},
        })
        self.assertNotIn("Traceback", r.stderr)
        rows = {row["path"]: row["status"] for row in json.loads(r.stdout)["rows"]}
        self.assertEqual(rows, {"DESIGN.md": "self-drift", "f.txt": "upstream-stale"})

    def test_a_key_outside_the_project_is_not_read(self) -> None:
        r = self.drift({"/etc/hosts": {"sha256": "0" * 64, "produced_by": "x"}})
        self.assertNotIn("Traceback", r.stderr)
        row = json.loads(r.stdout)["rows"][0]
        self.assertEqual(row["status"], "outside")


if __name__ == "__main__":
    unittest.main()
