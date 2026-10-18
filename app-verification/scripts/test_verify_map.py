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

    def test_stories_with_a_priority_or_a_colon(self) -> None:
        # found on Archi Studio: `- **US-1 (P1).** Come titolare …` — 46 stories read as 0
        prd = "- **US-1 (P1).** Come titolare, voglio creare lo studio.\n- **US-2:** As a client, I want to log.\n- **US-3** Uno.\n"
        self.assertEqual([sid for sid, _ in vm.stories(prd)], ["US-1", "US-2", "US-3"])
        self.assertEqual(vm.stories(prd)[0][1], "Come titolare, voglio creare lo studio.")

    def test_slug_takes_what_the_user_wants(self) -> None:
        # found on fit-coach: "I want a progress view" fell back to the whole sentence
        self.assertEqual(vm.slug("As a personal trainer, I want a progress view per client, so that I see trends."),
                         "a-progress-view-per-client")
        self.assertEqual(vm.slug("As a client, I want to log my meals, so that we follow it."), "log-my-meals")
        self.assertEqual(vm.slug("Trainers can export data."), "trainers-can-export-data")

    def test_slug_reads_italian_stories(self) -> None:
        # found on Archi Studio: every file was named `come-titolare-…` — "voglio" was not read as "I want"
        self.assertEqual(vm.slug("Come titolare di studio, voglio creare lo studio e invitare collaboratori, così che ognuno veda."),
                         "creare-lo-studio-e-invitare-collaboratori")
        self.assertEqual(vm.slug("Come architetto, voglio esportare in DXF, così da lavorare con altri."), "esportare-in-dxf")

    def test_sub_feature_ids_are_unique_and_clean(self) -> None:
        # found on Archi Studio: `us-1-error` four times (one per screen), `us-1-er (bloccato)` with spaces
        screens = [vm.Screen("A1", "A", "Accesso", "/sign-in", ["visitatore"], ["US-1"], ["Er"]),
                   vm.Screen("A2", "A", "Codice", "/sign-in/code", ["visitatore"], ["US-1"], ["Er", "Er (bloccato)"])]
        text = vm._feature_md("US-1", "Come titolare, voglio entrare.", screens)
        ids = [line.split("`")[1] for line in text.splitlines() if line.startswith("- `")]
        self.assertEqual(ids, ["us-1-a1-error", "us-1-a2-error", "us-1-a2-error-bloccato"])

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


class Surfaces(Fixture):
    """One manual per surface the project has, detected by surfaces.py (the user's decision, 2026-10-18)."""

    def web_and_mounted_agent(self) -> None:
        self.write(".workflow/PRD.md", PRD)
        self.write("package.json", '{"dependencies": {"next": "16.3.8", "eve": "1.0.0"}}')
        self.write("app/page.tsx", "export default function P() { return null }\n")
        self.write("next.config.ts", "export default withEve({})\n")
        self.write("agent/agent.ts", "export default {}\n")
        self.write("agent/tools/current_studio.ts", "export default {}\n")
        self.write("agent/tools/find_rooms.ts", "export default {}\n")

    def test_scaffold_every_surface(self) -> None:
        self.web_and_mounted_agent()
        results = vm.scaffold_all(self.root)
        self.assertEqual(sorted(r["path"] for r in results), [".claude/skills/verify-agent", ".claude/skills/verify-web"])
        agent = (self.root / ".claude/skills/verify-agent/SKILL.md").read_text(encoding="utf-8")
        launch = agent.split("## Launch")[1].split("## ")[0]
        self.assertIn("verify-web", launch)   # mounted: it starts with the web app, never on its own

    def test_agent_features_are_its_tools(self) -> None:
        self.web_and_mounted_agent()
        vm.scaffold_all(self.root)
        names = sorted(p.name for p in (self.root / ".claude/skills/verify-agent/features").glob("*.md"))
        self.assertEqual(names, ["README.md", "tool-current-studio.md", "tool-find-rooms.md"])

    def test_check_flags_a_missing_surface_manual(self) -> None:
        self.web_and_mounted_agent()
        vm.scaffold(self.root, "web")
        problems = vm.check_all(self.root)
        self.assertTrue(any("verify-agent" in p and "no manual" in p for p in problems), problems)

    def test_cli_without_app_does_every_surface(self) -> None:
        self.web_and_mounted_agent()
        out = io.StringIO()
        with redirect_stdout(out):
            vm.main(["scaffold", str(self.root)])
        self.assertIn("verify-web", out.getvalue())
        self.assertIn("verify-agent", out.getvalue())

    def test_rescaffold_adds_new_tools_to_the_index(self) -> None:
        # found on Archi Studio: PR #325 added five tools mid-run; the files arrived, the index kept listing one
        self.web_and_mounted_agent()
        vm.scaffold_all(self.root)
        self.write("agent/tools/measure.ts", "export default {}\n")
        vm.scaffold_all(self.root)
        index = (self.root / ".claude/skills/verify-agent/features/README.md").read_text(encoding="utf-8")
        self.assertIn("tool-measure.md", index)
        self.assertEqual(index.count("tool-current-studio.md"), 1)


class ReviewFixes(Fixture):
    """The final review of 2026-10-18: one test per finding, each reproduced before the fix."""

    def monorepo(self) -> None:
        self.write(".workflow/PRD.md", PRD)
        self.write("package.json", '{"private": true}')
        self.write("apps/web/package.json", '{"dependencies": {"next": "16"}}')
        self.write("apps/web/app/dashboard/page.tsx", "")
        self.write("apps/mobile/package.json", '{"dependencies": {"expo": "58"}}')
        self.write("apps/mobile/app.json", '{"expo": {}}')
        self.write("apps/mobile/app/index.tsx", "")
        self.write("apps/mobile/app/settings.tsx", "")

    def test_i3_routes_are_read_per_surface(self) -> None:
        self.monorepo()
        vm.scaffold_all(self.root)
        web = (self.root / ".claude/skills/verify-web/features/README.md").read_text(encoding="utf-8")
        mobile = (self.root / ".claude/skills/verify-mobile/features/README.md").read_text(encoding="utf-8")
        self.assertIn("`/dashboard`", web)
        self.assertIn("`/settings`", mobile)
        self.assertIn("`/`", mobile)

    def test_i4_check_refuses_stories_it_could_not_read(self) -> None:
        self.complete_manual()
        self.write(".workflow/PRD.md", PRD + "\n| US-7 | only in a table |\n")
        problems = vm.check(self.root)
        self.assertTrue(any("US-7" in p and "not read" in p for p in problems), problems)

    def test_i4_star_bullets_and_sub_numbers_are_stories(self) -> None:
        prd = "* **US-4.** As a user, I want to log in.\n- **US-3.1** As a user, I want to reset it.\n"
        self.assertEqual([sid for sid, _ in vm.stories(prd)], ["US-4", "US-3.1"])

    def test_i5_an_orphaned_manual_is_reported(self) -> None:
        self.monorepo()
        vm.scaffold_all(self.root)
        (self.root / "apps/web").rename(self.root / "apps/site")
        problems = vm.check_all(self.root)
        self.assertTrue(any("verify-web" in p and "no surface" in p for p in problems), problems)

    def test_m1_a_tool_named_index_something_is_a_tool(self) -> None:
        self.write("package.json", '{"dependencies": {"eve": "1"}}')
        self.write("agent/agent.ts", "")
        self.write("agent/tools/indexDocuments.ts", "")
        self.write("agent/tools/index.ts", "")
        vm.scaffold_all(self.root)
        names = sorted(p.name for p in (self.root / ".claude/skills/verify-agent/features").glob("tool-*.md"))
        self.assertEqual(names, ["tool-indexdocuments.md"])

    def test_m2_parallel_intercepting_and_private_segments_are_not_routes(self) -> None:
        for p in ("app/@modal/(.)photo/page.tsx", "app/photo/page.tsx", "app/_lib/page.tsx", "app/(..)x/page.tsx"):
            self.write(p, "")
        self.write("package.json", '{"dependencies": {"next": "16"}}')
        self.assertEqual(vm.routes(self.root), ["/photo"])

    def test_m3_the_no_stories_placeholder_goes_when_stories_arrive(self) -> None:
        self.write(".workflow/PRD.md", "# PRD\n")
        vm.scaffold(self.root)
        self.write(".workflow/PRD.md", PRD)
        vm.scaffold(self.root)
        index = (self.manual() / "features" / "README.md").read_text(encoding="utf-8")
        self.assertNotIn("(no stories in the PRD)", index)
        self.assertIn("US-2", index)

    def test_m4_gitignore_variants_git_accepts(self) -> None:
        import subprocess
        self.complete_manual()
        subprocess.run(["git", "init", "-q", str(self.root)], check=True)
        for pattern in ("/.verification/*\n", ".verification/evidence/\n"):
            self.write(".gitignore", pattern)
            self.assertFalse(any(".verification" in p and "gitignore" in p for p in vm.check(self.root)), pattern)

    def test_m6_an_unknown_app_name_is_refused(self) -> None:
        self.monorepo()
        out = io.StringIO()
        with redirect_stdout(out):
            code = vm.main(["scaffold", str(self.root), "--app", "wbe"])
        self.assertEqual(code, 2)
        self.assertIn("web", out.getvalue())
        self.assertFalse((self.root / ".claude/skills/verify-wbe").exists())

    def test_m7_a_story_file_without_a_slug_counts(self) -> None:
        self.complete_manual()
        f = self.manual() / "features"
        (f / "US-2-log-workout.md").rename(f / "US-2.md")
        self.edit_index("US-2-log-workout.md", "US-2.md")
        self.assertEqual([p for p in vm.check(self.root) if "US-2" in p], [])
        vm.scaffold(self.root)
        self.assertEqual(sorted(p.name for p in f.glob("US-2*")), ["US-2.md"])

    def edit_index(self, old: str, new: str) -> None:
        p = self.manual() / "features" / "README.md"
        p.write_text(p.read_text(encoding="utf-8").replace(old, new), encoding="utf-8")

    def test_m9_the_gitignore_problem_is_reported_once(self) -> None:
        self.monorepo()
        vm.scaffold_all(self.root)
        problems = [p for p in vm.check_all(self.root) if ".gitignore" in p]
        self.assertEqual(len(problems), 1, problems)

    def test_m10_placeholders_in_any_text_file(self) -> None:
        self.complete_manual()
        self.write(".claude/skills/verify-web/scripts/flow.yaml", "appId: <fill: bundle id>\n")
        self.write(".claude/skills/verify-web/scripts/helper.mjs", "// <fill: helper>\n")
        problems = vm.check(self.root)
        self.assertTrue(any("flow.yaml" in p and "<fill:" in p for p in problems), problems)
        self.assertTrue(any("helper.mjs" in p and "<fill:" in p for p in problems), problems)

    def test_m14_record_writes_meta_json_through_the_lock(self) -> None:
        self.write(".workflow/meta.json", json.dumps({"project_name": "Notes", "history": []}))
        block = {"skill": ".claude/skills/verify-web", "features": 2, "source": "routes", "proven_at": "2026-10-18T00:00:00Z",
                 "proven_feature": "US-1", "evidence": ".verification/evidence/x/", "maintained_at": None, "maintain_outcome": None}
        with redirect_stdout(io.StringIO()):
            self.assertEqual(vm.main(["record", str(self.root), "--json", json.dumps(block)]), 0)
        meta = json.loads((self.root / ".workflow/meta.json").read_text(encoding="utf-8"))
        self.assertEqual(meta["verification"]["proven_feature"], "US-1")
        self.assertIn("meta_digest", meta)   # written by meta_io, so show_state does not flag an outside edit

    def test_m14_record_refuses_a_block_without_the_contract_keys(self) -> None:
        self.write(".workflow/meta.json", json.dumps({"history": []}))
        with redirect_stdout(io.StringIO()):
            self.assertEqual(vm.main(["record", str(self.root), "--json", '{"skill": "x"}']), 2)
