"""boundaries_gate: no boundaries.json passes; declared and clean passes; declared and violated refuses."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import boundaries_gate  # noqa: E402


def write(root: Path, rel: str, data) -> None:
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(data if isinstance(data, str) else json.dumps(data), encoding="utf-8")


class BoundariesGate(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def declare(self) -> None:
        write(self.root, "boundaries.json", {"scope": "@t", "packages": {
            "packages/db": {"may_depend_on": []},
            "capabilities/*": {"may_depend_on": ["contracts"]},
        }})
        write(self.root, "packages/db/package.json", {"name": "@t/db"})
        write(self.root, "capabilities/a/package.json", {"name": "@t/capability-a"})

    def test_not_declared_passes(self) -> None:
        passed, _ = boundaries_gate.verify(self.root, {"stack": {"framework": "next"}})
        self.assertTrue(passed)

    def test_inapp_topology_without_file_refuses(self) -> None:
        passed, why = boundaries_gate.verify(self.root, {"stack": {"monorepo": {"topology": "web-agent-inapp"}}})
        self.assertFalse(passed)
        self.assertIn("no boundaries.json", why)

    def test_malformed_meta_does_not_raise(self) -> None:
        for meta in ({"stack": "x"}, {"stack": {"monorepo": ["x"]}}, [], None):
            passed, _ = boundaries_gate.verify(self.root, meta)
            self.assertTrue(passed)

    def test_project_copy_is_never_run(self) -> None:
        self.declare()
        write(self.root, "capabilities/a/package.json", {"name": "@t/capability-a", "dependencies": {"@t/db": "workspace:*"}})
        write(self.root, "scripts/check_boundaries.py", "raise SystemExit(0)\n")  # a hostile copy that always passes
        passed, _ = boundaries_gate.verify(self.root, {})
        self.assertFalse(passed)

    def test_clean_passes(self) -> None:
        self.declare()
        passed, why = boundaries_gate.verify(self.root, {})
        self.assertTrue(passed, why)

    def test_violation_refuses(self) -> None:
        self.declare()
        write(self.root, "capabilities/a/package.json", {"name": "@t/capability-a", "dependencies": {"@t/db": "workspace:*"}})
        passed, why = boundaries_gate.verify(self.root, {})
        self.assertFalse(passed)
        self.assertIn("capabilities/a/package.json", why)


if __name__ == "__main__":
    unittest.main()
