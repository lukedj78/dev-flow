"""lint_skills.py's vendored-copy check: a copy that drifts or disappears fails the lint (it is how three skills
share dev-flow's surfaces.py and meta_io.py while each installs standalone)."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lint_skills as ls  # noqa: E402


class Vendored(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        ls.ERRORS.clear()
        ls.WARNINGS.clear()
        self.saved = list(ls.VENDORED_SOURCE)
        ls.VENDORED_SOURCE[:] = [("dev-flow/scripts/surfaces.py", "app-verification/scripts/surfaces.py")]
        (self.root / "dev-flow/scripts").mkdir(parents=True)
        (self.root / "dev-flow/scripts/surfaces.py").write_text("x = 1\n")

    def tearDown(self) -> None:
        ls.VENDORED_SOURCE[:] = self.saved
        self._tmp.cleanup()

    def test_a_deleted_copy_is_an_error(self) -> None:
        # final review of app-verification (2026-10-18): deleting a vendored copy only warned, so the lint passed
        ls.check_vendored_source(self.root)
        self.assertTrue(any("surfaces.py" in e for e in ls.ERRORS), (ls.ERRORS, ls.WARNINGS))

    def test_a_drifted_copy_is_an_error(self) -> None:
        (self.root / "app-verification/scripts").mkdir(parents=True)
        (self.root / "app-verification/scripts/surfaces.py").write_text("x = 2\n")
        ls.check_vendored_source(self.root)
        self.assertTrue(any("differs" in e for e in ls.ERRORS), ls.ERRORS)

    def test_an_identical_copy_passes(self) -> None:
        (self.root / "app-verification/scripts").mkdir(parents=True)
        (self.root / "app-verification/scripts/surfaces.py").write_text("x = 1\n")
        ls.check_vendored_source(self.root)
        self.assertEqual(ls.ERRORS, [])


if __name__ == "__main__":
    unittest.main()
