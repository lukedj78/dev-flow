"""Tests for scope.py — check the PRD's scope rules, record a scope decision in the PRD."""

from __future__ import annotations

import io
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import scope as sc  # noqa: E402

RULES = """## Scope rules

- **A new feature enters the MVP when**: three test users hit the same wall.
- **Not before launch, whatever the evidence**: a second payment provider.
- **Who decides**: the user.
"""

PRD = """# Notes — PRD

## User stories (MVP)

- **US-1.** As a trainer, I want to invite clients.

## Non-goals

- An admin panel.

""" + RULES + """
## Open questions

- None.
"""


class Check(unittest.TestCase):
    def test_rules_complete(self) -> None:
        self.assertEqual(sc.check(PRD), [])

    def test_rules_missing_section(self) -> None:
        problems = sc.check(PRD.replace(RULES, ""))
        self.assertTrue(any("## Scope rules" in p for p in problems), problems)

    def test_rules_placeholder_line(self) -> None:
        for bad in ("- **Who decides**: <the user, or the named owner>", "- **Who decides**:"):
            problems = sc.check(PRD.replace("- **Who decides**: the user.", bad))
            self.assertTrue(any("Who decides" in p for p in problems), (bad, problems))

    def test_rules_anywhere_in_an_italian_prd(self) -> None:
        # fit-coach writes `## Fuori ambito`, not `## Non-goals`
        prd = "# PRD\n\n## Fuori ambito\n\n- Pagamenti.\n\n" + RULES
        self.assertEqual(sc.check(prd), [])


class Record(unittest.TestCase):
    def test_record_creates_the_section_at_the_end(self) -> None:
        out = sc.record(PRD, "2026-10-18", "export to CSV", "defer", "one request, the rule asks for three", "user")
        self.assertTrue(out.rstrip().endswith("| 2026-10-18 | export to CSV | defer | one request, the rule asks for three | user |"))
        self.assertIn("## Scope changes\n\n| Date | Request | Decision | Evidence / reason | Decided by |", out)
        self.assertTrue(out.startswith(PRD.rstrip("\n")))   # nothing above it changed

    def test_record_appends_to_an_existing_table_not_last(self) -> None:
        once = sc.record(PRD, "2026-10-18", "export", "defer", "r1", "user") + "\n## Appendix\n\nNotes.\n"
        twice = sc.record(once, "2026-10-19", "dark mode", "add", "the user said do it anyway", "user")
        self.assertEqual(twice.count("## Scope changes"), 1)
        table = twice.split("## Scope changes")[1].split("## Appendix")[0]
        self.assertIn("| 2026-10-18 | export |", table)
        self.assertIn("| 2026-10-19 | dark mode | add |", table)
        self.assertTrue(twice.rstrip().endswith("Notes."))

    def test_record_escapes_pipes_and_folds_newlines(self) -> None:
        out = sc.record(PRD, "2026-10-18", "filter a|b", "reject", "a non-goal\nsecond line", "user")
        row = out.rstrip().splitlines()[-1]
        self.assertEqual(row, "| 2026-10-18 | filter a\\|b | reject | a non-goal second line | user |")

    def test_record_refuses_an_unknown_decision(self) -> None:
        with self.assertRaises(ValueError):
            sc.record(PRD, "2026-10-18", "x", "maybe", "r", "user")


class Cli(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_cli_check_no_prd_is_quiet(self) -> None:
        out = io.StringIO()
        with redirect_stdout(out):
            self.assertEqual(sc.main(["check", str(self.root)]), 0)
        self.assertEqual(out.getvalue(), "")

    def test_cli_record_writes_the_file(self) -> None:
        (self.root / ".workflow").mkdir()
        (self.root / ".workflow" / "PRD.md").write_text(PRD, encoding="utf-8")
        with redirect_stdout(io.StringIO()):
            code = sc.main(["record", str(self.root), "--request", "export", "--decision", "experiment",
                            "--reason", "test with two studios", "--date", "2026-10-18"])
        self.assertEqual(code, 0)
        text = (self.root / ".workflow" / "PRD.md").read_text(encoding="utf-8")
        self.assertIn("| 2026-10-18 | export | experiment | test with two studios | user |", text)

    def test_cli_check_reports_and_fails(self) -> None:
        (self.root / ".workflow").mkdir()
        (self.root / ".workflow" / "PRD.md").write_text(PRD.replace(RULES, ""), encoding="utf-8")
        with redirect_stdout(io.StringIO()):
            self.assertEqual(sc.main(["check", str(self.root)]), 1)



SKILL = (Path(__file__).resolve().parents[1] / "SKILL.md").read_text(encoding="utf-8")


class SkillWiring(unittest.TestCase):
    """The PRD template and the check must say the same thing, and the check runs when the PRD is written."""

    def test_the_template_has_exactly_the_lines_the_check_reads(self) -> None:
        # a guard against drift: rename a label in one place and every new PRD would fail the check
        template = SKILL[SKILL.index("## Scope rules\n"):]
        template = template[:template.index("\n## ", 1)]
        problems = sc.check(template)
        self.assertEqual(len(problems), 3, problems)
        self.assertTrue(all("still to fill" in p for p in problems), problems)

    def test_step_5_runs_the_check_before_handing_off(self) -> None:
        step5 = SKILL[SKILL.index("### Step 5"):SKILL.index("### Step 6")]
        self.assertIn("scripts/scope.py check", step5)


if __name__ == "__main__":
    unittest.main()


class ReviewFixes(unittest.TestCase):
    """The final review of 2026-10-18, one test per finding."""

    def with_first(self, value: str) -> str:
        return PRD.replace("- **A new feature enters the MVP when**: three test users hit the same wall.",
                           f"- **A new feature enters the MVP when**:{value}")

    def test_i2_any_placeholder_is_unfilled(self) -> None:
        for value in (" TBD", " tbd", " …", " ...", " TODO", " <evidence> or three users", ' <the evidence, e.g. "x > y">'):
            self.assertTrue(any("A new feature enters the MVP when" in p for p in sc.check(self.with_first(value))), value)

    def test_i2_an_empty_line_never_borrows_the_next(self) -> None:
        problems = sc.check(self.with_first(""))
        self.assertTrue(any("A new feature enters the MVP when" in p for p in problems), problems)

    def test_unfilled_predicate_is_exported(self) -> None:
        self.assertTrue(sc.unfilled("<x>"))
        self.assertFalse(sc.unfilled("three users ask for it"))

    def test_i3_a_row_lands_right_after_the_table(self) -> None:
        prd = PRD + ("\n## Scope changes\n\n| Date | Request | Decision | Evidence / reason | Decided by |\n|---|---|---|---|---|\n"
                     "| 2026-10-01 | a | defer | r | user |\n\nNote: rows are newest last.\n\n## Tech\n\nx\n")
        out = sc.record(prd, "2026-10-18", "b", "add", "r2", "user")
        section = out.split("## Scope changes")[1].split("## Tech")[0]
        self.assertIn("| 2026-10-01 | a | defer | r | user |\n| 2026-10-18 | b | add | r2 | user |\n", section)
        self.assertIn("Note: rows are newest last.", section)

    def test_i4_a_heading_with_extra_text_is_the_same_section(self) -> None:
        prd = PRD + ("\n## Scope changes (log)\n\n| Date | Request | Decision | Evidence / reason | Decided by |\n"
                     "|---|---|---|---|---|\n| 2026-10-01 | a | defer | r | user |\n")
        out = sc.record(prd, "2026-10-18", "b", "add", "r2", "user")
        self.assertEqual(out.count("## Scope changes"), 1)
        rules = PRD.replace("## Scope rules", "## Scope rules (MVP)")
        self.assertEqual(sc.check(rules), [])

    def test_m8_the_date_is_validated(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".workflow").mkdir()
            (root / ".workflow" / "PRD.md").write_text(PRD, encoding="utf-8")
            err = io.StringIO()
            from contextlib import redirect_stderr
            with redirect_stdout(io.StringIO()), redirect_stderr(err):
                code = sc.main(["record", str(root), "--request", "x", "--decision", "add", "--reason", "r", "--date", "foo"])
            self.assertEqual(code, 2)
            self.assertNotIn("| foo |", (root / ".workflow" / "PRD.md").read_text(encoding="utf-8"))
