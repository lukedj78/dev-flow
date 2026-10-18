"""Tests for verify_map.py — the manual's skeleton from the inventory, and the check that refuses gaps."""

from __future__ import annotations

import io
import json
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import verify_map as vm  # noqa: E402

PRD = """# Notes — PRD

## Fasi

| M1 | Basics | US-1 |

## User stories (MVP)

- **US-1.** As a trainer, I want to invite clients and see them, so that I manage them.
  - Acceptance: an invited client appears in the list.
- **US-2.** As a client, I want to log today's workout, so that my trainer follows me.
"""

INVENTORY = """# Screen inventory

## A — Public site

| ID | Screen | Route | Roles | Stories | States |
|---|---|---|---|---|---|
| A1 | Home (hero, search, featured trips) | `/` | visitor | US-6, US-48 | L |
| A2 | Destinations index | `/destinations` | visitor | US-55 | L, E |
"""


class Fixture(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def write(self, rel: str, text: str) -> Path:
        p = self.root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")
        return p

    def manual(self) -> Path:
        return self.root / ".claude" / "skills" / "verify-web"

    def complete_manual(self) -> None:
        """A manual with nothing left to fill: the shape check() must accept."""
        self.write(".workflow/PRD.md", PRD)
        self.write(".gitignore", "node_modules\n.verification/\n")
        m = ".claude/skills/verify-web"
        sections = "\n\n".join(f"## {s}\n\nFilled {s.lower()} text." for s in vm.SECTIONS)
        self.write(f"{m}/SKILL.md", "---\nname: verify-web\ndescription: Drive Notes web.\n---\n\n# Verify Notes\n\n"
                   + sections + "\n\nRun `scripts/doctor.sh` first. Evidence goes to `.verification/evidence/`.\n")
        doctor = self.write(f"{m}/scripts/doctor.sh", "#!/bin/sh\ncurl -sf http://127.0.0.1:3000/ >/dev/null\n")
        doctor.chmod(0o755)
        body = ("\n\n## Sub-features\n\n- `a` one.\n\n## How to get to it (user POV)\n\n- `/`\n\n"
                "## Driving it with the browser\n\nPreconditions: none.\n\n## Gotchas\n\n- none.\n")
        self.write(f"{m}/features/US-1-invite-clients.md", "# Invite clients\n\nText." + body)
        self.write(f"{m}/features/US-2-log-workout.md", "# Log workout\n\nText." + body)
        self.write(f"{m}/features/README.md", "# Map\n\n- [Invite](./US-1-invite-clients.md)\n- [Log](./US-2-log-workout.md)\n")


class Parsing(Fixture):
    def test_stories_from_list_items_only(self) -> None:
        prd = ("| M1 | x | US-1 |\n\n- **US-1.** As a trainer, I want to invite.\n"
               "- **US-2.** As a client, I want to log.\n- **US-1.** As a trainer, I want to invite.\n")
        self.assertEqual(vm.stories(prd), [("US-1", "As a trainer, I want to invite."),
                                           ("US-2", "As a client, I want to log.")])

    def test_slug_takes_what_the_user_wants(self) -> None:
        # found on fit-coach: "I want a progress view" fell back to the whole sentence
        self.assertEqual(vm.slug("As a personal trainer, I want a progress view per client, so that I see trends."),
                         "a-progress-view-per-client")
        self.assertEqual(vm.slug("As a client, I want to log my meals, so that we follow it."), "log-my-meals")
        self.assertEqual(vm.slug("Trainers can export data."), "trainers-can-export-data")

    def test_inventory_rows(self) -> None:
        rows = vm.inventory(INVENTORY)
        self.assertEqual(rows[0], vm.Screen("A1", "A — Public site", "Home (hero, search, featured trips)", "/",
                                            ["visitor"], ["US-6", "US-48"], ["L"]))
        self.assertEqual(rows[1].states, ["L", "E"])

    def test_routes_strip_groups_keep_dynamic(self) -> None:
        for p in ("app/[locale]/(marketing)/page.tsx", "app/[locale]/(trainer)/trainer/plans/[id]/page.tsx",
                  "app/[locale]/(trainer)/trainer/plans/page.tsx", "app/[locale]/(auth)/layout.tsx"):
            self.write(p, "export default function P() { return null }\n")
        # found on fit-coach: the user sees /trainer/plans — a leading [locale] segment is the i18n prefix, not a page
        self.assertEqual(vm.routes(self.root), ["/", "/trainer/plans", "/trainer/plans/[id]"])


    def test_routes_of_an_expo_router_app(self) -> None:
        self.write("package.json", '{"dependencies": {"expo": "58.0.0", "expo-router": "6.0.0"}}')
        for p in ("app/_layout.tsx", "app/(tabs)/index.tsx", "app/(tabs)/settings.tsx", "app/plan/[id].tsx", "app/+not-found.tsx"):
            self.write(p, "export default function S() { return null }\n")
        self.assertEqual(vm.routes(self.root), ["/", "/plan/[id]", "/settings"])

class Scaffold(Fixture):
    def test_scaffold_from_inventory(self) -> None:
        self.write(".workflow/PRD.md", PRD)
        self.write("docs/wireframes/screen-inventory.md", INVENTORY.replace("US-6, US-48", "US-1"))
        r = vm.scaffold(self.root)
        self.assertEqual(r["source"], "wireframes")
        self.assertEqual(r["stories"], 2)
        us1 = next((self.manual() / "features").glob("US-1-*.md")).read_text(encoding="utf-8")
        how = us1.split("## How to get to it (user POV)")[1].split("## ")[0]
        self.assertIn("A1", how)
        self.assertIn("`/`", how)
        self.assertIn("loading", us1.split("## Sub-features")[1].split("## ")[0])
        skill = (self.manual() / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("name: verify-web", skill)
        for s in vm.SECTIONS:
            self.assertIn(f"\n## {s}\n", skill)

    def test_scaffold_falls_back_to_routes(self) -> None:
        self.write(".workflow/PRD.md", PRD)
        self.write("app/clients/page.tsx", "export default function P() { return null }\n")
        r = vm.scaffold(self.root)
        self.assertEqual(r["source"], "routes")
        readme = (self.manual() / "features" / "README.md").read_text(encoding="utf-8")
        self.assertIn("no screen inventory", readme)
        self.assertIn("/clients", readme)

    def test_scaffold_keeps_filled_files_and_adds_new_stories(self) -> None:
        self.write(".workflow/PRD.md", PRD)
        vm.scaffold(self.root)
        us1 = next((self.manual() / "features").glob("US-1-*.md"))
        us1.write_text("filled", encoding="utf-8")
        self.write(".workflow/PRD.md", PRD + "- **US-3.** As a client, I want to message my trainer.\n")
        r = vm.scaffold(self.root)
        self.assertEqual(us1.read_text(encoding="utf-8"), "filled")
        self.assertTrue(list((self.manual() / "features").glob("US-3-*.md")))
        self.assertIn(str(us1.relative_to(self.root)), r["kept"])

    def test_scaffold_with_no_stories_says_so(self) -> None:
        self.write(".workflow/PRD.md", "# PRD\n\nNo stories here.\n")
        self.assertEqual(vm.scaffold(self.root)["stories"], 0)
        out = io.StringIO()
        with redirect_stdout(out):
            vm.main(["scaffold", str(self.root)])
        self.assertIn("0 stories found", out.getvalue())


class Check(Fixture):
    def test_check_passes_a_complete_manual(self) -> None:
        self.complete_manual()
        self.assertEqual(vm.check(self.root), [])
        with redirect_stdout(io.StringIO()):
            self.assertEqual(vm.main(["check", str(self.root)]), 0)

    def assertFlags(self, needle: str) -> None:
        problems = vm.check(self.root)
        self.assertTrue(any(needle in p for p in problems), problems)
        with redirect_stdout(io.StringIO()):
            self.assertEqual(vm.main(["check", str(self.root)]), 1)

    def edit(self, rel: str, old: str, new: str) -> None:
        p = self.manual() / rel
        p.write_text(p.read_text(encoding="utf-8").replace(old, new), encoding="utf-8")

    def test_fill_marker_inside_a_code_block(self) -> None:
        self.complete_manual()
        self.edit("SKILL.md", "Filled launch text.", "```bash\n<fill: launch command>\n```")
        self.assertFlags("<fill:")

    def test_missing_section(self) -> None:
        self.complete_manual()
        self.edit("SKILL.md", "## Doctor\n\nFilled doctor text.", "")
        self.assertFlags("Doctor")

    def test_story_without_a_feature_file(self) -> None:
        self.complete_manual()
        self.write(".workflow/PRD.md", PRD + "- **US-3.** As a client, I want to message.\n")
        self.assertFlags("US-3")

    def test_script_not_executable(self) -> None:
        self.complete_manual()
        (self.manual() / "scripts" / "doctor.sh").chmod(0o644)
        self.assertFlags("doctor.sh")

    def test_script_never_named(self) -> None:
        self.complete_manual()
        self.edit("SKILL.md", "Run `scripts/doctor.sh` first.", "Run the doctor first.")
        self.assertFlags("doctor.sh")

    def test_evidence_not_ignored(self) -> None:
        self.complete_manual()
        self.write(".gitignore", "node_modules\n")
        self.assertFlags(".verification")

    def test_no_gitignore(self) -> None:
        self.complete_manual()
        (self.root / ".gitignore").unlink()
        self.assertFlags(".verification")

    def test_feature_sections_out_of_order(self) -> None:
        self.complete_manual()
        p = self.manual() / "features" / "US-2-log-workout.md"
        p.write_text("# Log\n\n## Gotchas\n\n- x\n\n## Sub-features\n\n- y\n\n## How to get to it (user POV)\n\n- /\n\n"
                     "## Driving it with the browser\n\n- z\n", encoding="utf-8")
        self.assertFlags("US-2-log-workout.md")

    def test_feature_not_linked_from_the_index(self) -> None:
        self.complete_manual()
        self.edit("features/README.md", "- [Log](./US-2-log-workout.md)\n", "")
        self.assertFlags("US-2-log-workout.md")

    def test_cli_json(self) -> None:
        self.complete_manual()
        self.edit("SKILL.md", "Filled launch text.", "<fill: launch command>")
        out = io.StringIO()
        with redirect_stdout(out):
            vm.main(["check", str(self.root), "--json"])
        self.assertTrue(json.loads(out.getvalue())["problems"])


if __name__ == "__main__":
    unittest.main()
