"""findings.py: the three refusals that make an iterative review different from a repeated one.

A loop that cannot escalate, cannot stop, or cannot tell a reopened finding from a new one is not a
review cycle — it is a way to spend tokens until the agent agrees with itself. Each of those three is
a refusal in code here, and each gets its own test.
"""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import findings as fd  # noqa: E402


class Review(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        (self.root / ".workflow").mkdir()
        (self.root / ".workflow" / "meta.json").write_text(
            json.dumps({"project_slug": "t", "phase": "module_added"}))

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def cli(self, *args: str) -> int:
        """Not named `run`: that is TestCase.run, and overriding it stops every test silently."""
        return fd.main([str(self.root), *args])

    def block(self) -> dict:
        return json.loads((self.root / ".workflow" / "meta.json").read_text())["spec_review"]

    def by_id(self, fid: str) -> dict:
        return next(f for f in self.block()["findings"] if f["id"] == fid)

    def open_review(self, profile: str = "standard") -> None:
        self.assertEqual(self.cli("open", "--fixed-point", "main", "--profile", profile), 0)

    def add(self, **kw) -> int:
        args = ["add", "--axis", kw.pop("axis", "spec"), "--severity", kw.pop("severity", "medium"),
                "--summary", kw.pop("summary", "a finding")]
        for k, v in kw.items():
            if v is True:
                args.append(f"--{k.replace('_', '-')}")
            elif v is not None:
                args += [f"--{k.replace('_', '-')}", str(v)]
        return self.cli(*args)


class Opening(Review):
    def test_add_before_open_is_refused(self) -> None:
        self.assertEqual(self.add(), 2)

    def test_open_records_the_cap_from_the_profile(self) -> None:
        self.open_review("light")
        self.assertEqual(self.block()["max_iterations"], 1)
        self.open_review("strict")
        self.assertEqual(self.block()["max_iterations"], 5)

    def test_a_hand_edited_block_is_refused(self) -> None:
        (self.root / ".workflow" / "meta.json").write_text(json.dumps({"spec_review": "clean"}))
        self.assertEqual(self.cli("open", "--fixed-point", "main"), 2)

    def test_axes_not_run_is_carried(self) -> None:
        self.assertEqual(self.cli("open", "--fixed-point", "main", "--axes-not-run", "spec"), 0)
        self.assertEqual(self.block()["axes_not_run"], ["spec"])

    def test_an_unrun_axis_is_shown_as_distinct_from_clean(self) -> None:
        self.cli("open", "--fixed-point", "main", "--axes-not-run", "spec")
        self.assertIn("NOT RUN", fd.render(fd.load(self.root)))


class Adding(Review):
    def test_a_finding_needs_a_summary(self) -> None:
        self.open_review()
        self.assertEqual(self.cli("add", "--axis", "spec", "--severity", "low", "--summary", "  "), 2)

    def test_a_line_without_a_file_is_refused(self) -> None:
        self.open_review()
        self.assertEqual(self.add(line=42), 2)

    def test_ids_are_sequential(self) -> None:
        self.open_review()
        self.add(summary="one")
        self.add(summary="two")
        self.assertEqual([f["id"] for f in self.block()["findings"]], ["F1", "F2"])

    def test_the_same_finding_twice_in_one_round_is_not_duplicated(self) -> None:
        self.open_review()
        self.add(summary="same thing", file="a.ts", line=1)
        self.add(summary="SAME THING", file="a.ts", line=1)   # wording and case must not matter
        self.assertEqual(len(self.block()["findings"]), 1)

    def test_a_rephrased_finding_is_still_the_same_finding(self) -> None:
        self.open_review()
        self.add(summary="x" * 200, file="a.ts", line=1)
        self.add(summary="x" * 200 + " and some more words", file="a.ts", line=1)
        self.assertEqual(len(self.block()["findings"]), 1)


class Escalation(Review):
    def test_a_round_cannot_close_while_a_finding_needs_a_human(self) -> None:
        self.open_review()
        self.add(summary="is this the product decision we want?", needs_human=True)
        self.assertEqual(self.cli("iterate"), 1)
        self.assertEqual(self.block()["iteration"], 1)

    def test_answering_it_unblocks_the_round(self) -> None:
        self.open_review()
        self.add(summary="ambiguous requirement", needs_human=True)
        self.assertEqual(self.cli("resolve", "F1", "--as", "accepted", "--user-said", "va bene cosi"), 0)
        self.assertEqual(self.cli("iterate"), 0)
        self.assertEqual(self.block()["iteration"], 2)

    def test_level_one_is_refused_while_a_finding_needs_a_human(self) -> None:
        self.open_review()
        self.add(summary="needs a decision", severity="low", needs_human=True)
        self.assertEqual(self.cli("close", "--level", "1"), 1)

    def test_level_three_can_close_with_it_open(self) -> None:
        self.open_review()
        self.add(summary="needs a decision", severity="low", needs_human=True)
        self.assertEqual(self.cli("close", "--level", "3"), 0)
        self.assertEqual(self.block()["level"], 3)


class TheCap(Review):
    def test_light_converges_in_one_round(self) -> None:
        self.open_review("light")
        self.assertEqual(self.cli("iterate"), 1)

    def test_standard_stops_at_three(self) -> None:
        self.open_review("standard")
        self.assertEqual(self.cli("iterate"), 0)
        self.assertEqual(self.cli("iterate"), 0)
        self.assertEqual(self.cli("iterate"), 1)
        self.assertEqual(self.block()["iteration"], 3)

    def test_the_cap_refusal_names_what_to_do_instead(self) -> None:
        self.open_review("light")
        self.add(summary="still open")
        import io
        from contextlib import redirect_stderr
        err = io.StringIO()
        with redirect_stderr(err):
            self.cli("iterate")
        self.assertIn("close --level 3", err.getvalue())

    def test_an_explicit_max_overrides_the_profile(self) -> None:
        self.assertEqual(self.cli("open", "--fixed-point", "main", "--max-iterations", "2"), 0)
        self.assertEqual(self.block()["max_iterations"], 2)

    def test_each_closed_round_is_recorded(self) -> None:
        self.open_review()
        self.add(summary="one")
        self.cli("iterate")
        self.assertEqual(self.block()["rounds"][0]["round"], 1)
        self.assertEqual(self.block()["rounds"][0]["found"], 1)


class Resolving(Review):
    def test_rejecting_needs_a_reason(self) -> None:
        self.open_review()
        self.add(summary="style preference")
        self.assertEqual(self.cli("resolve", "F1", "--as", "rejected"), 2)

    def test_accepting_needs_the_users_words(self) -> None:
        self.open_review()
        self.add(summary="a trade worth making")
        self.assertEqual(self.cli("resolve", "F1", "--as", "accepted"), 2)
        self.assertEqual(self.cli("resolve", "F1", "--as", "accepted", "--user-said", "accetto, lo scriviamo"), 0)
        self.assertEqual(self.by_id("F1")["resolution_quote"], "accetto, lo scriviamo")

    def test_fixing_can_carry_the_sha_that_fixed_it(self) -> None:
        self.open_review()
        self.add(summary="a real bug")
        self.assertEqual(self.cli("resolve", "F1", "--as", "fixed", "--sha", "abc1234"), 0)
        self.assertEqual(self.by_id("F1")["resolution_sha"], "abc1234")

    def test_resolving_twice_is_refused(self) -> None:
        self.open_review()
        self.add(summary="x")
        self.cli("resolve", "F1", "--as", "fixed")
        self.assertEqual(self.cli("resolve", "F1", "--as", "rejected", "--note", "actually fine"), 2)

    def test_resolving_an_unknown_finding_is_refused(self) -> None:
        self.open_review()
        self.assertEqual(self.cli("resolve", "F9", "--as", "fixed"), 2)


class Reopening(Review):
    def test_a_finding_that_comes_back_is_counted_not_re_added(self) -> None:
        self.open_review()
        self.add(summary="the same defect", file="a.ts", line=7)
        self.cli("resolve", "F1", "--as", "fixed")
        self.cli("iterate")
        self.add(summary="the same defect", file="a.ts", line=7)
        b = self.block()
        self.assertEqual(len(b["findings"]), 1)
        self.assertEqual(b["reopened"], 1)
        self.assertEqual(self.by_id("F1")["resolution"], "open")
        self.assertEqual(self.by_id("F1")["reopen_count"], 1)

    def test_a_reopened_finding_is_reported(self) -> None:
        self.open_review()
        self.add(summary="x", file="a.ts", line=1)
        self.cli("resolve", "F1", "--as", "fixed")
        self.cli("iterate")
        self.add(summary="x", file="a.ts", line=1)
        self.assertIn("reopened", fd.render(fd.load(self.root)))

    def test_a_rejected_finding_coming_back_also_counts(self) -> None:
        """The reviewer re-reporting what the implementer argued away is the loop's own failure mode."""
        self.open_review()
        self.add(summary="x", file="a.ts", line=1)
        self.cli("resolve", "F1", "--as", "rejected", "--note", "not a defect")
        self.cli("iterate")
        self.add(summary="x", file="a.ts", line=1)
        self.assertEqual(self.block()["reopened"], 1)


class Closing(Review):
    def test_level_one_is_refused_with_an_open_high_finding(self) -> None:
        self.open_review()
        self.add(severity="high", summary="authorization missing on the route")
        self.assertEqual(self.cli("close", "--level", "1"), 1)

    def test_level_two_is_refused_too(self) -> None:
        self.open_review()
        self.add(severity="critical", summary="secret in the diff")
        self.assertEqual(self.cli("close", "--level", "2"), 1)

    def test_level_one_passes_once_it_is_fixed(self) -> None:
        self.open_review()
        self.add(severity="high", summary="authorization missing")
        self.cli("resolve", "F1", "--as", "fixed", "--sha", "abc")
        self.assertEqual(self.cli("close", "--level", "1"), 0)

    def test_an_open_low_finding_does_not_block_level_two(self) -> None:
        self.open_review()
        self.add(severity="low", summary="a naming nit")
        self.assertEqual(self.cli("close", "--level", "2"), 0)

    def test_an_open_low_finding_DOES_block_level_one(self) -> None:
        """`contracts.md` defines level 1 as zero findings — zero, not zero serious ones.

        Found by walking the cycle on a real project on 2026-11-06: an earlier draft blocked only
        critical/high, so a review with an open `low` finding closed at level 1 and the agent merged a
        diff that still had something open on it.
        """
        self.open_review()
        self.add(severity="low", summary="a naming nit")
        self.assertEqual(self.cli("close", "--level", "1"), 1)

    def test_level_one_passes_once_the_low_finding_is_resolved(self) -> None:
        self.open_review()
        self.add(severity="info", summary="a wording preference")
        self.cli("resolve", "F1", "--as", "rejected", "--note", "no documented standard covers it")
        self.assertEqual(self.cli("close", "--level", "1"), 0)

    def test_level_two_is_refused_while_a_finding_needs_a_human(self) -> None:
        """Level 2 is 'merge unless the user objects'; something needing a decision is level 3."""
        self.open_review()
        self.add(severity="low", summary="which variant should this use?", needs_human=True)
        self.assertEqual(self.cli("close", "--level", "2"), 1)

    def test_an_invalid_level_is_refused(self) -> None:
        self.open_review()
        self.assertEqual(self.cli("close", "--level", "5"), 2)


class Status(Review):
    def test_status_on_a_project_with_no_review(self) -> None:
        self.assertEqual(self.cli("status"), 0)
        self.assertIn("no review recorded", fd.render(fd.load(self.root)))

    def test_status_json_is_the_block(self) -> None:
        self.open_review()
        self.assertEqual(self.cli("status", "--json"), 0)

    def test_the_report_groups_by_axis(self) -> None:
        self.open_review()
        self.add(axis="risk", severity="high", summary="one-way door: the migration drops a column")
        out = fd.render(fd.load(self.root))
        for ax in fd.AXES:
            self.assertIn(ax, out)


class ProfilesNeverSubtractAChecK(unittest.TestCase):
    def test_a_profile_only_sets_the_round_cap(self) -> None:
        """The profile is review DEPTH. It must not be a way to drop an axis or a severity rule —
        `contracts.md` defines a level by who can check a finding, which a diff's size cannot change."""
        self.assertEqual(sorted(fd.PROFILES), ["light", "standard", "strict"])
        self.assertTrue(all(isinstance(v, int) and v >= 1 for v in fd.PROFILES.values()))
        self.assertEqual(fd.BLOCKING, ("critical", "high"))


if __name__ == "__main__":
    unittest.main()
