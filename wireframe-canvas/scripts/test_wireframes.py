"""Tests for wireframes.py. Temp directories only: nothing real is read or written.

    cd wireframe-canvas/scripts && python3 -m unittest -v
"""

from __future__ import annotations

import io
import json
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

HERE = Path(__file__).resolve().parent
DEVFLOW = HERE.parents[1] / "dev-flow" / "scripts"
sys.path.insert(0, str(HERE))
import wireframes as wf  # noqa: E402

PRD = "## User stories\n- **US-1.** As a visitor…\n- **US-2.** As a traveller…\n- **US-3.** As an agency…\n"
INVENTORY = """# Inventory

## A — Public

| ID | Screen | Route | Roles | Stories | States |
|---|---|---|---|---|---|
| A1 | Home | `/` | visitor | US-1 | L |
| A2 | Sign in | `/sign-in` | all | US-2, US-3 | Er |

| Legend | Meaning |
|---|---|
| L | loading |
"""


ARGUMENT = """# Page argument

## Inventory
- Via dei Sette Portoni, the street the agency is named after
- the 1924 tram timetable framed in the office
- forty-two villages, each visited before it is sold
- the ferry at seven from Milazzo
- one guide per eight travellers, never more
- lemon groves of the Conca d'Oro
- the founders' grandmother's recipe book
- closed in August, when the island is for islanders

## Idea
Idea: On this page, the 1924 tram timetable becomes the itinerary format every trip is shown in.

## Competitor test
Competitor: Sicily Uncovered, two streets away.
Result: their trips have no timetable of their own — the sentence fails for them.

## Argument
| Section | Claim | Proof |
|---|---|---|
| Hero | Small groups that see the island by timetable | the timetable itinerary, real stops and times |
| Trips | Every village visited before it is sold | the 42 villages on the map, with visit dates |
"""


def run(*argv: str) -> tuple[int, str]:
    out, err = io.StringIO(), io.StringIO()
    with redirect_stdout(out), redirect_stderr(err):
        rc = wf.main(list(argv))
    return rc, out.getvalue() + err.getvalue()


class Fixture(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        (self.root / ".workflow").mkdir()
        (self.root / "docs/wireframes").mkdir(parents=True)
        (self.root / ".workflow/PRD.md").write_text(PRD)
        self.inv = self.root / "docs/wireframes/screen-inventory.md"
        self.inv.write_text(INVENTORY)
        self.arg = self.root / "docs/wireframes/page-argument.md"
        self.arg.write_text(ARGUMENT)
        self.meta_path = self.root / ".workflow/meta.json"
        self.meta_path.write_text(json.dumps({"phase": "design_extracted", "history": [],
                                              "stack": {"framework": "expo-rn", "data_residency": "none"}}))

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def meta(self) -> dict:
        return json.loads(self.meta_path.read_text())

    def approve(self, *extra: str) -> tuple[int, str]:
        return run("approve", str(self.root), "--canvas-url", "https://claude.ai/artifact/x",
                   "--user-said", "approvato, procedi", *extra)


class Coverage(Fixture):
    def test_complete_inventory_passes_and_other_tables_are_ignored(self) -> None:
        rc, out = run("coverage", str(self.root))
        self.assertEqual(rc, 0, out)
        self.assertIn("2 screens", out)

    def test_a_story_without_a_screen_is_named(self) -> None:
        (self.root / ".workflow/PRD.md").write_text(PRD + "- **US-4.** As a supplier…\n")
        rc, out = run("coverage", str(self.root))
        self.assertEqual(rc, 1)
        self.assertIn("US-4", out)

    def test_an_empty_states_cell_is_a_gap(self) -> None:
        self.inv.write_text(INVENTORY.replace("| US-1 | L |", "| US-1 |  |"))
        rc, out = run("coverage", str(self.root))
        self.assertEqual(rc, 1)
        self.assertIn("A1", out)

    def test_screen_rows_in_a_table_without_states_are_named_not_dropped(self) -> None:
        # Measured on smart-travel 2026-10-10: two tables (emails, system states) had no States column
        # and 18 screens vanished from the count without a word.
        self.inv.write_text(INVENTORY + "\n| ID | Screen | Stories |\n|---|---|---|\n| M1 | Email | US-1 |\n")
        rc, out = run("coverage", str(self.root))
        self.assertEqual(rc, 1)
        self.assertIn("not counted: M1", out)


class Approve(Fixture):
    def test_approve_records_counts_and_the_users_words(self) -> None:
        rc, out = self.approve()
        self.assertEqual(rc, 0, out)
        w = self.meta()["wireframes"]
        self.assertEqual((w["screens"], w["artboards"], w["approved_by_user"]), (2, 4, True))
        self.assertEqual(w["approval_quote"], "approvato, procedi")
        self.assertIsNone(w["screenshots_posted_at"])

    def test_approve_refuses_an_incomplete_inventory(self) -> None:
        (self.root / ".workflow/PRD.md").write_text(PRD + "- **US-9.** …\n")
        self.assertEqual(self.approve()[0], 1)
        self.assertNotIn("wireframes", self.meta())

    def test_approve_refuses_too_few_artboards(self) -> None:
        self.assertEqual(self.approve("--artboards", "3")[0], 1)

    def test_skip_needs_a_reason(self) -> None:
        self.assertEqual(run("skip", str(self.root), "--reason", "  ")[0], 1)
        self.assertEqual(run("skip", str(self.root), "--reason", "one-screen tool")[0], 0)
        self.assertTrue(self.meta()["wireframes"]["skipped"])

    def test_approval_opens_the_scaffold_gate(self) -> None:
        def set_phase() -> int:
            return subprocess.run([sys.executable, str(DEVFLOW / "update_meta.py"), str(self.root),
                                   "set-phase", "scaffolded"], capture_output=True, text=True).returncode
        self.assertEqual(set_phase(), 1)
        self.approve()
        self.assertEqual(set_phase(), 0)


class Argument(Fixture):
    def test_a_complete_argument_passes(self) -> None:
        rc, out = run("argument", str(self.root))
        self.assertEqual(rc, 0, out)
        self.assertIn("✓", out)

    def test_a_short_inventory_is_named(self) -> None:
        self.arg.write_text(ARGUMENT.replace("- closed in August, when the island is for islanders\n", ""))
        rc, out = run("argument", str(self.root))
        self.assertEqual(rc, 1)
        self.assertIn("7 inventory items", out)

    def test_an_idea_without_becomes_is_named(self) -> None:
        self.arg.write_text(ARGUMENT.replace(" becomes the itinerary format", ", shown as the format"))
        rc, out = run("argument", str(self.root))
        self.assertEqual(rc, 1)
        self.assertIn("Idea:", out)

    def test_an_empty_competitor_test_is_named(self) -> None:
        self.arg.write_text(ARGUMENT.replace("Result: their trips have no timetable of their own — the sentence fails for them.", "Result:"))
        rc, out = run("argument", str(self.root))
        self.assertEqual(rc, 1)
        self.assertIn("Result:", out)

    def test_a_claim_without_proof_is_named(self) -> None:
        self.arg.write_text(ARGUMENT.replace("| the 42 villages on the map, with visit dates |", "|  |"))
        rc, out = run("argument", str(self.root))
        self.assertEqual(rc, 1)
        self.assertIn("Trips", out)

    def test_placeholders_are_gaps(self) -> None:
        self.arg.write_text(ARGUMENT.replace("Competitor: Sicily Uncovered, two streets away.", "Competitor: <TBD>"))
        rc, out = run("argument", str(self.root))
        self.assertEqual(rc, 1)

    def test_no_public_screen_needs_no_argument(self) -> None:
        self.inv.write_text(INVENTORY.replace("| visitor |", "| traveller |"))
        self.arg.unlink()
        rc, out = run("argument", str(self.root))
        self.assertEqual(rc, 0, out)
        self.assertIn("no public screen", out)
        rc, _ = self.approve()
        self.assertEqual(rc, 0)

    def test_the_idea_may_be_written_in_the_users_language_or_with_an_arrow(self) -> None:
        for idea in ("Idea: In questa pagina, l'orario del tram del 1924 diventa il formato di ogni viaggio.",
                     "Idea: the 1924 tram timetable → the itinerary format every trip is shown in.",
                     "**Idea:** On this page, the 1924 tram timetable becomes the itinerary format."):
            with self.subTest(idea):
                self.arg.write_text(ARGUMENT.replace(
                    "Idea: On this page, the 1924 tram timetable becomes the itinerary format every trip is shown in.", idea))
                rc, out = run("argument", str(self.root))
                self.assertEqual(rc, 0, out)

    def test_an_ellipsis_inside_real_content_is_not_a_placeholder(self) -> None:
        self.arg.write_text(ARGUMENT.replace("- closed in August, when the island is for islanders",
                                             "- closed Sundays… and all of August"))
        rc, out = run("argument", str(self.root))
        self.assertEqual(rc, 0, out)

    def test_the_argument_table_is_read_by_header_name(self) -> None:
        self.arg.write_text(ARGUMENT.replace("| Section | Claim | Proof |\n|---|---|---|",
                                             "| # | Proof | Section | Claim |\n|---|---|---|---|")
                            .replace("| Hero | Small groups that see the island by timetable | the timetable itinerary, real stops and times |",
                                     "| 1 | the timetable itinerary, real stops and times | Hero | Small groups that see the island by timetable |")
                            .replace("| Trips | Every village visited before it is sold | the 42 villages on the map, with visit dates |",
                                     "| 2 | the 42 villages on the map, with visit dates | Trips | Every village visited before it is sold |"))
        rc, out = run("argument", str(self.root))
        self.assertEqual(rc, 0, out)

    def test_a_missing_inventory_is_a_gap_not_a_pass(self) -> None:
        self.inv.unlink()
        rc, out = run("argument", str(self.root))
        self.assertEqual(rc, 1, out)
        self.assertIn("screen-inventory.md", out)

    def test_role_column_and_word_variants_count_as_public(self) -> None:
        for header, role in (("Role", "visitor"), ("Ruoli", "visitatore"), ("Roles", "visitors")):
            with self.subTest(header=header, role=role):
                self.inv.write_text(INVENTORY.replace("| Roles |", f"| {header} |").replace("| visitor |", f"| {role} |"))
                self.arg.unlink(missing_ok=True)
                rc, out = run("argument", str(self.root))
                self.assertEqual(rc, 1, out)

    def test_approve_refuses_a_public_area_without_an_argument(self) -> None:
        self.arg.unlink()
        rc, out = self.approve()
        self.assertEqual(rc, 1)
        self.assertIn("page-argument.md", out)
        self.assertNotIn("wireframes", self.meta())

    def test_approve_records_the_argument(self) -> None:
        rc, _ = self.approve()
        self.assertEqual(rc, 0)
        self.assertEqual(self.meta()["wireframes"]["argument"], "docs/wireframes/page-argument.md")

    def test_no_argument_needs_a_reason_and_is_recorded(self) -> None:
        self.arg.unlink()
        rc, _ = self.approve("--no-argument", "  ")
        self.assertEqual(rc, 1)
        rc, _ = self.approve("--no-argument", "the public site is the client's own agency")
        self.assertEqual(rc, 0)
        self.assertEqual(self.meta()["wireframes"]["argument"],
                         {"skipped": "the public site is the client's own agency"})


class Screenshots(Fixture):
    def test_targets_map_each_story_to_its_screens(self) -> None:
        rc, out = run("targets", str(self.root))
        t = json.loads(out)
        self.assertEqual([s["id"] for s in t["US-3"]], ["A2"])
        self.assertEqual(t["US-1"][0]["phone"], "docs/wireframes/png/A1-phone.png")

    def test_comments_go_to_every_issue_whose_story_maps_to_a_screen(self) -> None:
        (self.root / ".workflow/tasks.md").write_text(
            "## Epic: Auth (US-2) · S0\n\n"
            "- [ ] **Build the sign-in page** — from the artboard\n"
            "- [ ] **Wire the session** — server side\n\n"
            "## Epic: Home\n\n### US-1: As a visitor…\n\n- [ ] **Build the home** — hero first\n"
            "- [ ] **Unrelated chore** — no story\n")
        (self.root / ".workflow/github-issues.json").write_text(json.dumps(
            {"Build the sign-in page": 12, "Wire the session": 13, "Build the home": 14}))
        rc, out = run("comments", str(self.root), "--repo", "o/n", "--ref", "abc123", "--out", "c",
                      "--map", ".workflow/github-issues.json")
        self.assertEqual(rc, 0, out)
        plan = {c["issue"]: c["screens"] for c in json.loads(out)["comments"]}
        self.assertEqual(plan, {"12": ["A2"], "13": ["A2"], "14": ["A1"]})
        body = (self.root / "c/14.md").read_text()
        self.assertIn("https://github.com/o/n/blob/abc123/docs/wireframes/png/A1-phone.png?raw=true", body)

    def test_comments_use_the_tracker_issue_map(self) -> None:
        # scrum records issues by task_key in meta.json#tracker.issue_map, on Linear, Jira or GitHub
        sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scrum" / "scripts"))
        from task_key import task_key
        (self.root / ".workflow/tasks.md").write_text(
            "## Epic: Auth (US-2) · S0\n\n- [ ] **Build the sign-in page** — from the artboard\n"
            "## Epic: Home\n\n### US-1: As a visitor…\n\n- [ ] **Build the home** — hero first\n")
        meta = self.meta()
        meta["tracker"] = {"provider": "linear", "issue_map": {
            task_key("- [ ] **Build the sign-in page** — x"): "LUC-3", task_key("- [ ] **Build the home** — x"): "LUC-4"}}
        (self.root / ".workflow/meta.json").write_text(json.dumps(meta))
        rc, out = run("comments", str(self.root), "--out", "c")
        self.assertEqual(rc, 0, out)
        plan = {c["issue"]: c["screens"] for c in json.loads(out)["comments"]}
        self.assertEqual(plan, {"LUC-3": ["A2"], "LUC-4": ["A1"]})
        body = (self.root / "c/LUC-4.md").read_text()
        self.assertIn("docs/wireframes/png/A1-phone.png", body)
        self.assertNotIn("github.com", body)   # not GitHub: the agent attaches the files

    def test_posted_needs_approval_and_every_png(self) -> None:
        self.assertEqual(run("posted", str(self.root))[0], 1)
        self.approve()
        self.assertEqual(run("posted", str(self.root))[0], 1)
        png = self.root / "docs/wireframes/png"
        png.mkdir(parents=True)
        for i in ("A1", "A2"):
            for v in ("desktop", "phone"):
                (png / f"{i}-{v}.png").write_bytes(b"\x89PNG")
        self.assertEqual(run("pngs", str(self.root))[0], 0)
        self.assertEqual(run("posted", str(self.root))[0], 0)
        self.assertTrue(self.meta()["wireframes"]["screenshots_posted_at"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
