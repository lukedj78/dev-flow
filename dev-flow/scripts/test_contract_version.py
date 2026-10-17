"""meta.json records the contract version it conforms to, and an older script does not rewrite a newer file.

    cd dev-flow/scripts && python3 -m unittest test_contract_version -v

Why this exists: nothing said which version of the contract a meta.json was written under (AUDIT.md
§6.2). Compatibility rested on tolerant reads alone, so a script that predates a contract change could
rewrite a newer file and misread fields it does not know the meaning of. The field makes a future
migration possible and that rewrite refusable.
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
        self.meta_path = self.root / ".workflow" / "meta.json"

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def write(self, **extra) -> None:
        self.meta_path.write_text(json.dumps({
            "phase": "idea_captured", "history": [], "artifacts": {}, "stack": {},
            "inventory": {"verdict": "skipped", "reason": "test"}, **extra}))

    def meta(self) -> dict:
        return json.loads(self.meta_path.read_text())

    def run_script(self, *argv: str) -> subprocess.CompletedProcess:
        return subprocess.run([sys.executable, str(HERE / argv[0]), *argv[1:]], capture_output=True, text=True)


class ContractVersion(Fixture):
    def test_init_records_the_current_version(self) -> None:
        fresh = self.root / "fresh"
        fresh.mkdir()
        self.run_script("init_workflow.py", str(fresh))
        meta = json.loads((fresh / ".workflow" / "meta.json").read_text())
        self.assertEqual(meta["contract_version"], meta_io.CONTRACT_VERSION)

    def test_a_file_from_before_the_field_gets_it_on_the_next_write(self) -> None:
        self.write()
        r = self.run_script("update_meta.py", str(self.root), "append-history", "--skill", "x")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(self.meta()["contract_version"], meta_io.CONTRACT_VERSION)

    def test_a_newer_file_is_not_rewritten(self) -> None:
        newer = meta_io.CONTRACT_VERSION + 1
        self.write(contract_version=newer)
        before = self.meta_path.read_text()
        for argv in (["update_meta.py", str(self.root), "append-history", "--skill", "x"],
                     ["update_meta.py", str(self.root), "set-phase", "prd_drafted"],
                     ["inventory.py", "record", str(self.root), "--verdict", "skipped", "--reason", "x"]):
            with self.subTest(argv=argv[:3]):
                r = self.run_script(*argv)
                self.assertEqual(r.returncode, 2, r.stdout)
                self.assertIn("newer", r.stderr)
                self.assertNotIn("Traceback", r.stderr)
                self.assertEqual(self.meta_path.read_text(), before)

    def test_a_newer_file_can_still_be_read(self) -> None:
        self.write(contract_version=meta_io.CONTRACT_VERSION + 1)
        r = self.run_script("show_state.py", str(self.root))
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("newer contract", r.stdout)

    def test_a_version_that_is_not_an_integer_is_invalid(self) -> None:
        self.write(contract_version="1.0")
        r = self.run_script("update_meta.py", str(self.root), "append-history", "--skill", "x")
        self.assertEqual(r.returncode, 2)
        self.assertIn("contract_version", r.stderr)


if __name__ == "__main__":
    unittest.main()
