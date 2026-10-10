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
