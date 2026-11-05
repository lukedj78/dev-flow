"""lint_skills.py's stale-marker check: a dated claim is stale only when nothing on its line re-dates it.

The rule flagged the OLDEST marker in a file, which made a re-check unrecordable: writing
"checked 2026-08-26, re-checked 2026-11-05" left the note firing on the 08-26 half, so the only way to
silence it was to delete the history. Measured on 2026-11-05 — thirteen files had been re-verified that
day and all thirteen still reported as 71 days old. The question the check should ask is not "is there an
old date here" but "is the newest date on this line old".
"""

from __future__ import annotations

import datetime
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lint_skills as ls  # noqa: E402

TODAY = datetime.date(2026, 11, 5)


class StaleMarkers(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        ls.ERRORS.clear()
        ls.WARNINGS.clear()
        ls.NOTES.clear()
        self._lines = ls.subprocess_lines
        # the check reads `git ls-files`; in a temp dir there is no repo, so serve the files directly
        ls.subprocess_lines = lambda root, cmd: ["doc.md"]

    def tearDown(self) -> None:
        ls.subprocess_lines = self._lines
        self._tmp.cleanup()

    def write(self, text: str) -> None:
        (self.root / "doc.md").write_text(text)

    def run_check(self) -> list[str]:
        ls.NOTES.clear()
        ls.check_stale_markers(self.root, today=TODAY)
        return list(ls.NOTES)

    def test_an_old_date_alone_on_its_line_is_flagged(self) -> None:
        self.write("The endpoint 404s (checked 2026-08-26).\n")
        self.assertEqual(len(self.run_check()), 1)

    def test_a_fresh_date_alone_on_its_line_passes(self) -> None:
        self.write("The endpoint 404s (checked 2026-11-05).\n")
        self.assertEqual(self.run_check(), [])

    def test_a_recheck_on_the_same_line_clears_the_old_date(self) -> None:
        """The case the old rule got wrong, and the reason this file exists."""
        self.write("The endpoint 404s (checked 2026-08-26, re-checked 2026-11-05).\n")
        self.assertEqual(self.run_check(), [])

    def test_a_recheck_that_is_itself_old_is_still_flagged(self) -> None:
        self.write("The endpoint 404s (checked 2026-05-01, re-checked 2026-06-02).\n")
        notes = self.run_check()
        self.assertEqual(len(notes), 1)
        self.assertIn("2026-06-02", notes[0])  # the newest date is the one that is stale

    def test_a_fresh_date_on_another_line_does_not_clear_an_old_one(self) -> None:
        """Freshness is per line, not per file — otherwise one re-check silences the whole document."""
        self.write("Claim A (checked 2026-08-26).\n\nClaim B (checked 2026-11-05).\n")
        notes = self.run_check()
        self.assertEqual(len(notes), 1)
        self.assertIn("2026-08-26", notes[0])

    def test_a_record_file_is_exempt(self) -> None:
        """A watch-log row says what was true on a date; re-dating it would falsify the record."""
        self.assertIn("docs/vercel-changelog-watch.md", ls.STALE_EXEMPT)
        self.assertTrue("docs/vercel-changelog-watch.md".startswith(ls.STALE_EXEMPT))

    def test_several_stale_lines_report_once_with_a_count(self) -> None:
        self.write("A (checked 2026-08-26).\nB (checked 2026-07-01).\nC (checked 2026-06-01).\n")
        notes = self.run_check()
        self.assertEqual(len(notes), 1)
        self.assertIn("+2 more", notes[0])
        self.assertIn("2026-06-01", notes[0])  # the oldest line leads


if __name__ == "__main__":
    unittest.main()
