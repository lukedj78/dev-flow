"""freshness.py: the cases where a staleness check lies.

The point of this script is that a flat window is the wrong clock, so the tests that matter are the
ones about the clock:

- a prerelease and a pre-1.0 package get the short window even when npm says they are years old;
- a package first published last month gets the short window even at `2.1.0`;
- a file that talks about two packages is governed by the **tightest** of their windows, because the
  young one is what will make the file wrong first;
- a file with no date at all is reported, since that is the 232-file hole the script exists for;
- a registry that cannot answer is `not checked`, never a pass.

Plus the extraction, because a false positive costs trust faster than a false negative: the first
draft read the English *"from \"idea\" to \"running app\""* as a package.

    cd scripts && python3 -m unittest test_freshness -v
"""

from __future__ import annotations

import datetime as dt
import io
import sys
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))
import freshness as fr  # noqa: E402

TODAY = dt.date(2026, 11, 17)


class TestTheClock(unittest.TestCase):
    """window_for is the whole idea: maturity sets the window, not a constant."""

    def test_prerelease_gets_the_short_window_however_old(self):
        days, why = fr.window_for("4.2.0-beta.3", "2019-01-01", TODAY)
        self.assertEqual(days, fr.WINDOW_YOUNG)
        self.assertIn("prerelease", why)

    def test_pre_one_point_zero_gets_the_short_window(self):
        days, why = fr.window_for("0.22.0", "2020-01-01", TODAY)
        self.assertEqual(days, fr.WINDOW_YOUNG)
        self.assertIn("pre-1.0", why)

    def test_a_stable_version_published_last_month_is_still_young(self):
        days, why = fr.window_for("2.1.0", "2026-10-20", TODAY)
        self.assertEqual(days, fr.WINDOW_YOUNG, "28 days old is young whatever the version says")
        self.assertIn("days ago", why)

    def test_a_year_old_stable_package_gets_the_middle_window(self):
        days, _ = fr.window_for("3.0.1", "2025-11-17", TODAY)
        self.assertEqual(days, fr.WINDOW_MID)

    def test_an_old_stable_package_gets_the_long_window(self):
        days, why = fr.window_for("19.0.0", "2015-06-01", TODAY)
        self.assertEqual(days, fr.WINDOW_OLD)
        self.assertIn("two years", why)

    def test_an_unknown_version_is_treated_as_young_not_as_old(self):
        days, why = fr.window_for(None, None, TODAY)
        self.assertEqual(days, fr.WINDOW_YOUNG)
        self.assertIn("unknown", why)

    def test_a_malformed_created_date_does_not_crash_and_falls_back_on_the_version(self):
        days, _ = fr.window_for("19.0.0", "not-a-date", TODAY)
        self.assertEqual(days, fr.WINDOW_OLD)


class TestExtraction(unittest.TestCase):
    def test_subpaths_resolve_to_their_package(self):
        self.assertEqual(fr.package_of("@ui-sdk/react/primitive"), "@ui-sdk/react")
        self.assertEqual(fr.package_of("flags/next"), "flags")
        self.assertEqual(fr.package_of("eve"), "eve")

    def test_what_is_not_a_package_is_skipped(self):
        for spec in ("./local", "../up", "@/components/ui/button", "node:fs", "fs", "~/x",
                     "@workspace/ui", "react"):
            self.assertIsNone(fr.package_of(spec), spec)

    def test_english_prose_is_not_an_import(self):
        """The regression that named the bug: AGENTS.md says 'from "idea" to "running app"'."""
        text = 'to take a project from "idea" to "running app" without losing context'
        names = [fr.package_of(m.group(1) or m.group(2) or "")
                 for m in fr.IMPORT_RE.finditer(text)]
        self.assertEqual([n for n in names if n], [])

    def test_a_real_single_line_import_is_found(self):
        text = 'import { flag } from "flags/next"\n'
        names = [fr.package_of(m.group(1) or m.group(2) or "")
                 for m in fr.IMPORT_RE.finditer(text)]
        self.assertIn("flags", names)

    def test_a_multi_line_import_is_found_by_its_closing_brace(self):
        text = 'import {\n  createTransfer,\n  definePrimitive,\n} from "@ui-sdk/core"\n'
        names = [fr.package_of(m.group(1) or m.group(2) or "")
                 for m in fr.IMPORT_RE.finditer(text)]
        self.assertIn("@ui-sdk/core", names)

    def test_a_backticked_pin_is_read_with_its_version(self):
        m = fr.PINNED_RE.search("the floor is `@ui-sdk/core@0.1.0-beta.1` today")
        self.assertEqual(m.group(1), "@ui-sdk/core")
        self.assertEqual(m.group(2), "0.1.0-beta.1")

    def test_a_caret_range_keeps_only_the_version(self):
        m = fr.PINNED_RE.search("pinned at `chat@^4.42.0`")
        self.assertEqual(m.group(2), "^4.42.0")


class TestClassification(unittest.TestCase):
    """The regression that matters: the first run called 150 records "behind".

    Every sentence here is real text from this repo, and every one of them would have been edited —
    wrongly — by the first version of this script.
    """

    def kind(self, text):
        m = fr.PINNED_RE.search(text)
        return fr.claim_kind(text, m.start(), m.end(), m.group(2))

    def test_a_version_in_which_a_feature_landed_is_a_reference(self):
        self.assertEqual(self.kind("since `motion@13.4.0`, the declarative `<AnimateView>`"), "reference")

    def test_somebody_elses_requirement_is_a_reference(self):
        self.assertEqual(self.kind("React Bits asks `motion@^12` where we run 13"), "reference")

    def test_the_version_whose_docs_were_read_is_a_reference(self):
        self.assertEqual(self.kind("from `next@16.3.3`'s own shipped docs"), "reference")

    def test_a_bugs_upper_bound_is_a_reference(self):
        self.assertEqual(self.kind("Up to `next@16.4.2`, cookies written on an Edge route"), "reference")

    def test_what_someone_elses_template_ships_is_a_reference(self):
        self.assertEqual(self.kind("shadcn's own chatbot-template ships `next@16.3.6`"), "reference")

    def test_a_floor_is_a_pin(self):
        self.assertEqual(self.kind("the version floor is `chat@4.42.0` today"), "pin")

    def test_what_we_run_is_a_pin(self):
        self.assertEqual(self.kind("we run `motion@14.0.0` across the fleet"), "pin")

    def test_an_explicit_pin_is_a_pin(self):
        self.assertEqual(self.kind("pinned at `eve@0.91.0` until 1.0 ships"), "pin")

    def test_a_caret_range_is_always_a_reference(self):
        """A range is a requirement or a floor — never the exact version someone runs."""
        self.assertEqual(self.kind("we install `zod@^3.0.0` here"), "reference")

    def test_ambiguous_wording_defaults_to_reference(self):
        """A wrong 'behind' edits true text; a wrong 'reference' only asks for a re-read."""
        self.assertEqual(self.kind("see `zod@3.22.0` for the shape"), "reference")


class TestReport(unittest.TestCase):
    """run() on a fake repo, with npm faked: no network in the suite."""

    def setUp(self):
        self.files = {}
        self.npm = {}

        def tracked():
            return list(self.files)

        def facts(name, cache):
            return self.npm.get(name, {"error": "not in the fake registry"})

        self.patches = [
            mock.patch.object(fr, "tracked_markdown", tracked),
            mock.patch.object(fr, "npm_facts", facts),
            mock.patch.object(fr.Path, "read_text",
                              lambda self, **kw: self._fake_text),  # replaced below
        ]
        # Simpler: patch inventory's reader by writing real files in a temp root.
        self.patches.pop()
        import tempfile
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.patches.append(mock.patch.object(fr, "ROOT", Path(self.tmp.name)))
        for p in self.patches:
            p.start()
            self.addCleanup(p.stop)

    def write(self, rel, body):
        path = Path(self.tmp.name) / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(body, encoding="utf-8")
        self.files[rel] = True

    def kinds(self, report, kind):
        return [f for f in report["findings"] if f["kind"] == kind]

    def test_an_undated_file_naming_a_package_is_reported(self):
        self.write("a/SKILL.md", 'import { x } from "zod"\n')
        self.npm["zod"] = {"version": "4.0.0", "created": "2020-01-01"}
        report = fr.run(today=TODAY)
        self.assertEqual(len(self.kinds(report, "undated")), 1)

    def test_a_dated_file_inside_its_window_is_quiet(self):
        self.write("a/SKILL.md", 'Verified 2026-11-10.\nimport { x } from "zod"\n')
        self.npm["zod"] = {"version": "4.0.0", "created": "2015-01-01"}  # long window
        report = fr.run(today=TODAY)
        self.assertEqual(report["findings"], [])

    def test_a_young_package_makes_a_recent_date_overdue(self):
        """Eight days is fine for react and late for a beta — this is the whole point."""
        self.write("a/SKILL.md", 'Verified 2026-11-09.\nimport { x } from "@ui-sdk/core"\n')
        self.npm["@ui-sdk/core"] = {"version": "0.1.0-beta.1", "created": "2026-11-12"}
        report = fr.run(today=TODAY)
        overdue = self.kinds(report, "overdue")
        self.assertEqual(len(overdue), 1)
        self.assertEqual(overdue[0]["window_days"], fr.WINDOW_YOUNG)
        self.assertEqual(overdue[0]["age_days"], 8)

    def test_the_tightest_window_governs_a_file_naming_two_packages(self):
        self.write("a/SKILL.md",
                   'Verified 2026-10-01.\nimport { a } from "zod"\nimport { b } from "@ui-sdk/core"\n')
        self.npm["zod"] = {"version": "4.0.0", "created": "2015-01-01"}
        self.npm["@ui-sdk/core"] = {"version": "0.1.0-beta.1", "created": "2026-11-12"}
        report = fr.run(today=TODAY)
        overdue = self.kinds(report, "overdue")
        self.assertEqual(len(overdue), 1, "one finding for the file, driven by the young package")
        self.assertEqual(overdue[0]["package"], "@ui-sdk/core")
        self.assertEqual(overdue[0]["window_days"], fr.WINDOW_YOUNG)

    def test_a_pin_behind_npm_is_reported_with_both_versions(self):
        self.write("a/SKILL.md", 'Verified 2026-11-16. Pinned at `zod@3.22.0`.\n')
        self.npm["zod"] = {"version": "4.0.0", "created": "2015-01-01"}
        report = fr.run(today=TODAY)
        behind = self.kinds(report, "behind")
        self.assertEqual(len(behind), 1)
        self.assertEqual((behind[0]["ours"], behind[0]["npm"]), ("3.22.0", "4.0.0"))

    def test_a_matching_pin_is_quiet(self):
        self.write("a/SKILL.md", 'Verified 2026-11-16. Pinned at `zod@4.0.0`.\n')
        self.npm["zod"] = {"version": "4.0.0", "created": "2015-01-01"}
        self.assertEqual(self.kinds(fr.run(today=TODAY), "behind"), [])

    def test_a_registry_that_cannot_answer_is_not_checked_never_ok(self):
        self.write("a/SKILL.md", 'Verified 2026-11-16.\nimport { x } from "mystery-pkg"\n')
        report = fr.run(today=TODAY)
        self.assertEqual(len(self.kinds(report, "not checked")), 1)
        self.assertEqual(report["checked"]["mystery-pkg"]["status"], "not checked")
        self.assertNotIn("ok", report["checked"]["mystery-pkg"]["status"])

    def test_an_unreachable_package_does_not_make_the_file_look_fresh(self):
        """A file whose only package could not be checked gets no 'undated'/'overdue' verdict —
        because the window is unknown — but it must not read as verified either."""
        self.write("a/SKILL.md", 'import { x } from "mystery-pkg"\n')
        report = fr.run(today=TODAY)
        self.assertEqual(self.kinds(report, "overdue"), [])
        self.assertTrue(self.kinds(report, "not checked"))

    def test_exempt_files_are_left_alone(self):
        self.write("CHANGELOG.md", 'import { x } from "zod"\n')
        self.npm["zod"] = {"version": "4.0.0", "created": "2015-01-01"}
        # tracked_markdown is faked, so filter the way the real one does
        with mock.patch.object(fr, "tracked_markdown",
                               lambda: [f for f in self.files if not f.startswith(fr.EXEMPT)]):
            self.assertEqual(fr.run(today=TODAY)["findings"], [])

    def test_offline_reports_the_inventory_and_claims_nothing(self):
        self.write("a/SKILL.md", 'Verified 2026-11-16.\nimport { x } from "zod"\n')
        report = fr.run(offline=True, today=TODAY)
        self.assertEqual(report["checked"]["zod"]["status"], "not checked")
        self.assertEqual(self.kinds(report, "overdue"), [])

    def test_exit_zero_when_only_things_to_re_read(self):
        self.write("a/SKILL.md", 'import { x } from "zod"\n')
        self.npm["zod"] = {"version": "4.0.0", "created": "2015-01-01"}
        out = io.StringIO()
        with redirect_stdout(out):
            code = fr.main([])
        self.assertEqual(code, 0, "old is a reason to re-read, not proof of error")
        self.assertIn("UNDATED", out.getvalue())


if __name__ == "__main__":
    unittest.main()
