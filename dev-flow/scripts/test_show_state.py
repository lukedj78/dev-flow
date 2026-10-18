"""Direct tests for show_state.py: the routing table, phase-behind-the-code, and the read-only checks.

    cd dev-flow/scripts && python3 -m unittest test_show_state -v

show_state is the deterministic half of the router: dev-flow/SKILL.md tells the agent what to do,
and this prints the proposal from meta.json. Until now nothing tested it, which is how an unknown
phase came to print five "scaffolded" warnings and then route as `empty`.
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import phases  # noqa: E402
import show_state as ss  # noqa: E402


class Routing(unittest.TestCase):
    def test_every_entry_of_the_table_is_what_it_proposes(self) -> None:
        for fw, table in ss.PHASE_NEXT_BY_STACK.items():
            for phase, proposal in table.items():
                with self.subTest(fw=fw, phase=phase):
                    self.assertIn(phase, phases.PHASES)
                    self.assertEqual(ss.next_step(phase, fw), proposal)

    def test_the_common_phases_route_the_same_on_every_stack(self) -> None:
        for fw in ss.PHASE_NEXT_BY_STACK:
            for phase, proposal in ss.COMMON_NEXT.items():
                with self.subTest(fw=fw, phase=phase):
                    self.assertEqual(ss.next_step(phase, fw), proposal)

    def test_a_valid_phase_is_never_called_unknown(self) -> None:
        # A phase the contract defines but a stack never passes through (agent-only has no page_generated)
        # used to print "unknown phase — treat as empty: prd-from-idea": send a built project back to the PRD.
        for fw in ss.PHASE_NEXT_BY_STACK:
            for phase in phases.PHASES:
                with self.subTest(fw=fw, phase=phase):
                    self.assertNotIn("unknown phase", ss.next_step(phase, fw))

    def test_no_framework_means_next(self) -> None:
        self.assertEqual(ss.next_step("scaffolded", None), ss.PHASE_NEXT_BY_STACK["next"]["scaffolded"])

    def test_feature_complete_proposes_app_security_on_every_stack(self) -> None:
        # the fifth pre-deploy gate applies to every stack: all of them have dependencies and secrets
        for fw in ss.PHASE_NEXT_BY_STACK:
            for phase in ("feature_complete", "deployed"):
                self.assertIn("app-security", ss.next_step(phase, fw), (fw, phase))

    def test_an_unrecognized_framework_is_not_guessed(self) -> None:
        self.assertIn("refuses to guess", ss.next_step("scaffolded", "astro"))

    def test_a_legacy_spelling_routes_like_the_canonical_one(self) -> None:
        for old, new in phases.ALIASES.items():
            with self.subTest(old=old):
                self.assertEqual(ss.next_step(old, "next"), ss.next_step(new, "next"))

    def test_an_unknown_phase_routes_as_empty(self) -> None:
        self.assertEqual(ss.next_step("shipping", "next"), ss.COMMON_NEXT["empty"])


class TestLayers(unittest.TestCase):
    def test_the_stack_test_enum(self) -> None:
        for good in ("vitest", "vitest+playwright", "jest-expo+rntl+maestro"):
            self.assertTrue(ss.test_layers_ok(good), good)
        for bad in ("playwright+vitest", "vitest+vitest", "jest", "", ["vitest"], None):
            self.assertFalse(ss.test_layers_ok(bad), bad)


class Fixture(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        (self.root / ".workflow").mkdir()

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def write(self, **meta) -> None:
        (self.root / ".workflow" / "meta.json").write_text(json.dumps({"history": [], **meta}))

    def show(self) -> subprocess.CompletedProcess:
        return subprocess.run([sys.executable, str(HERE / "show_state.py"), str(self.root)],
                              capture_output=True, text=True)


class Output(Fixture):
    def test_no_meta_json(self) -> None:
        r = self.show()
        self.assertEqual(r.returncode, 1)
        self.assertIn("init_workflow.py", r.stdout)

    def test_prints_the_proposal_for_the_stack(self) -> None:
        self.write(phase="tasks_split", stack={"framework": "expo-rn"})
        r = self.show()
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn(ss.PHASE_NEXT_BY_STACK["expo-rn"]["tasks_split"], r.stdout)

    def test_a_phase_behind_the_code_asks_to_realign(self) -> None:
        # smart-travel: phase design_extracted, three days of pages, every check switched off.
        self.write(phase="design_extracted", stack={"framework": "next"})
        (self.root / "app").mkdir()
        (self.root / "app" / "page.tsx").write_text("export default function P() { return null }")
        out = self.show().stdout
        self.assertIn("PHASE BEHIND THE CODE", out)
        self.assertIn("REALIGN THE PHASE", out)

    def test_an_agent_only_project_is_not_behind_its_code(self) -> None:
        self.write(phase="tasks_split", stack={"framework": "agent"})
        (self.root / "app").mkdir()
        (self.root / "app" / "page.tsx").write_text("")
        self.assertNotIn("PHASE BEHIND THE CODE", self.show().stdout)

    def test_a_malformed_stack_test_is_reported(self) -> None:
        self.write(phase="tasks_split", stack={"framework": "next", "test": ["vitest"]})
        self.assertIn("stack.test is an array", self.show().stdout)

    def test_a_stale_stack_lint_is_reported(self) -> None:
        self.write(phase="tasks_split", stack={"framework": "next", "lint": "biome"})
        (self.root / "package.json").write_text(json.dumps({"devDependencies": {"eslint": "9"}}))
        self.assertIn("stack.lint says biome, the repository runs eslint", self.show().stdout)


class FounderPath(unittest.TestCase):
    """The founder path: dev-flow proposes it, never requires it, and routes by the founder's decision."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        (self.root / ".workflow/founder").mkdir(parents=True)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def meta(self, phase="idea_captured", **founder) -> dict:
        base = {"mode": "new", "research": "complete", "decision": "pending",
                "playbook": ".workflow/founder/founder-playbook.md", "version": 1, "open_hypotheses": []}
        base.update(founder)
        return {"phase": phase, "stack": {}, "founder": base}

    def show(self, meta: dict) -> str:
        (self.root / ".workflow/meta.json").write_text(json.dumps({"history": [], "artifacts": {}, **meta}))
        r = subprocess.run([sys.executable, str(HERE / "show_state.py"), str(self.root)], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        return r.stdout

    def test_empty_and_idea_captured_mention_both_doors(self) -> None:
        for phase in ("empty", "idea_captured"):
            with self.subTest(phase=phase):
                text = ss.COMMON_NEXT[phase]
                self.assertTrue(text.startswith(("ask the user", "prd-from-idea")))
                self.assertIn("inventory first", text)   # the direct door is still named
                self.assertIn("founder-intelligence", text)
                self.assertIn("ask the user", text)

    def test_no_founder_field_routes_as_before(self) -> None:
        for phase in phases.PHASES:
            with self.subTest(phase=phase):
                self.assertIsNone(ss.founder_step({"phase": phase}, self.root))

    def test_pending_routes_to_founder_intelligence_and_prints_labels(self) -> None:
        out = self.show(self.meta())
        self.assertIn("READY_FOR_FOUNDER_APPROVAL", out)
        self.assertIn("Next step proposal", out)
        self.assertIn("founder-intelligence", out.split("Next step proposal")[1])

    def test_approved_new_routes_to_prd_from_idea_with_playbook(self) -> None:
        import hashlib
        pb = self.root / ".workflow/founder/founder-playbook.md"
        pb.write_text("approved\n")
        step = ss.founder_step(self.meta(decision="approved", approved_by_user=True, approval_quote="sì",
                                         playbook_sha256=hashlib.sha256(pb.read_bytes()).hexdigest()), self.root)
        self.assertIn("prd-from-idea", step)
        self.assertIn("founder-playbook.md", step)

    def test_approved_but_changed_playbook_asks_for_reapproval(self) -> None:
        # The gate would refuse prd_drafted; proposing the PRD would waste a whole PRD before the refusal.
        pb = self.root / ".workflow/founder/founder-playbook.md"
        pb.write_text("approved text\n")
        import hashlib
        meta = self.meta(decision="approved", playbook_sha256=hashlib.sha256(pb.read_bytes()).hexdigest(),
                         approved_by_user=True, approval_quote="sì")
        self.assertIn("prd-from-idea", ss.founder_step(meta, self.root))
        pb.write_text("approved text\nedited after\n")
        step = ss.founder_step(meta, self.root)
        self.assertNotIn("prd-from-idea,", step)
        self.assertIn("approve", step)
        pb.unlink()
        self.assertIn("approve", ss.founder_step(meta, self.root))

    def test_ready_for_approval_proposes_presenting_not_continuing(self) -> None:
        step = ss.founder_step(self.meta(research="complete", decision="pending"), self.root)
        self.assertIn("present the Playbook to the founder", step)
        self.assertNotIn("continue the Playbook", step)
        self.assertIn("continue the Playbook", ss.founder_step(self.meta(research="in_progress"), self.root))

    def test_approved_new_past_the_prd_routes_normally(self) -> None:
        self.assertIsNone(ss.founder_step(self.meta(phase="tasks_split", decision="approved"), self.root))

    def test_approved_existing_routes_to_apply_handoff(self) -> None:
        step = ss.founder_step(self.meta(phase="tasks_split", mode="existing", decision="approved"), self.root)
        for word in ("handoff.md", "prd-from-idea", "prd-to-tasks"):
            self.assertIn(word, step)

    def test_stop_proposes_nothing_and_says_how_to_reopen(self) -> None:
        step = ss.founder_step(self.meta(decision="stop", reason="no market"), self.root)
        self.assertIn("stopped", step)
        self.assertIn("founder.py start", step)
        self.assertNotIn("prd-from-idea", step)

    def test_bypassed_routes_to_inventory(self) -> None:
        self.assertIsNone(ss.founder_step(self.meta(phase="empty", decision="bypassed", reason="x"), self.root))
        out = self.show(self.meta(phase="empty", decision="bypassed", reason="internal tool"))
        self.assertIn("inventory first", out.split("Next step proposal")[1])

    def test_a_null_founder_field_is_the_direct_path(self) -> None:
        out = self.show({"phase": "empty", "stack": {}, "founder": None})
        self.assertNotIn("Founder:", out)
        self.assertIn("ask the user", out.split("Next step proposal")[1])

    def test_labels_do_not_grow_sys_path(self) -> None:
        before = list(sys.path)
        for _ in range(3):
            ss.founder_labels(self.meta()["founder"])
        added = [p for p in sys.path if p not in before]
        self.assertLessEqual(len(added), 1)
        self.assertEqual(sys.path.count(str(ss.FOUNDER_SCRIPT.parent)), 1 if ss.FOUNDER_SCRIPT.is_file() else 0)

    def test_works_without_the_skill_installed(self) -> None:
        saved = ss.FOUNDER_SCRIPT
        ss.FOUNDER_SCRIPT = self.root / "nowhere" / "founder.py"
        try:
            self.assertIn("pending", ss.founder_line(self.meta()["founder"]))
            self.assertIn("founder-intelligence", ss.founder_step(self.meta(), self.root))
        finally:
            ss.FOUNDER_SCRIPT = saved


if __name__ == "__main__":
    unittest.main()


class Verification(unittest.TestCase):
    """app-verification: a manual once there is something to drive, and a note when it is older than the code."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def line(self, **meta):
        meta.setdefault("history", [])
        return ss.verification_line(meta, self.root)

    def test_no_note_before_there_is_something_to_drive(self) -> None:
        self.assertIsNone(self.line(phase="scaffolded", stack={"framework": "next"}))

    def test_missing_manual_is_noted(self) -> None:
        self.assertIn("app-verification create", self.line(phase="page_generated", stack={"framework": "next"}))

    def test_manual_on_disk_without_meta_is_not_missing(self) -> None:
        skill = self.root / ".claude" / "skills" / "verify-web" / "SKILL.md"
        skill.parent.mkdir(parents=True)
        skill.write_text("---\nname: verify-web\n---\n")
        self.assertNotIn("create", self.line(phase="page_generated", stack={"framework": "next"}) or "")

    def test_stale_manual_is_noted(self) -> None:
        out = self.line(phase="module_added", stack={"framework": "next"},
                        verification={"skill": ".claude/skills/verify-web", "proven_at": "2026-10-01T00:00:00Z"},
                        history=[{"skill": "module-add", "ran_at": "2026-10-10T00:00:00Z"}])
        self.assertIn("maintain", out)

    def test_fresh_manual_is_silent(self) -> None:
        self.assertIsNone(self.line(phase="module_added", stack={"framework": "next"},
                                    verification={"proven_at": "2026-10-01T00:00:00Z", "maintained_at": "2026-10-12T00:00:00Z"},
                                    history=[{"skill": "module-add", "ran_at": "2026-10-10T00:00:00Z"},
                                             {"skill": "spec-review", "ran_at": "2026-10-13T00:00:00Z"}]))

    def test_missing_manual_named_per_surface(self) -> None:
        # Archi Studio / fit-coach: a Next app serving an eve agent has two surfaces, so two manuals
        (self.root / "package.json").write_text('{"dependencies": {"next": "16.3.8", "eve": "1.0.0"}}')
        (self.root / "agent").mkdir()
        (self.root / "agent" / "agent.ts").write_text("export default {}\n")
        skill = self.root / ".claude" / "skills" / "verify-web" / "SKILL.md"
        skill.parent.mkdir(parents=True)
        skill.write_text("---\nname: verify-web\n---\n")
        out = self.line(phase="page_generated", stack={"framework": "next"})
        self.assertIn("verify-agent", out)
        self.assertNotIn("verify-web", out.split("missing")[-1] if "missing" in out else out)

    def manual(self, name: str) -> None:
        skill = self.root / ".claude" / "skills" / f"verify-{name}" / "SKILL.md"
        skill.parent.mkdir(parents=True)
        skill.write_text(f"---\nname: verify-{name}\n---\n")

    def test_i5_an_orphaned_manual_is_named(self) -> None:
        # final review: apps/web renamed to apps/site — the filled verify-web must not sit there unmentioned
        (self.root / "package.json").write_text('{"dependencies": {"next": "16"}}')
        (self.root / "app").mkdir()
        self.manual("web")
        self.manual("old-admin")
        out = self.line(phase="page_generated", stack={"framework": "next"},
                        verification={"proven_at": "2026-10-18T00:00:00Z"})
        self.assertIn("verify-old-admin", out)
        self.assertIn("no surface", out)

    def test_m11_a_manual_never_proven_is_a_draft(self) -> None:
        (self.root / "package.json").write_text('{"dependencies": {"next": "16"}}')
        (self.root / "app").mkdir()
        self.manual("web")
        out = self.line(phase="page_generated", stack={"framework": "next"})
        self.assertIn("not proven", out)

    def test_agent_projects_from_scaffolded(self) -> None:
        self.assertIn("create", self.line(phase="scaffolded", stack={"framework": "agent"}))

    def test_routing_mentions_verification(self) -> None:
        self.assertIn("app-verification", ss.next_step("page_generated", "next"))
        for fw in ss.PHASE_NEXT_BY_STACK:
            self.assertIn("app-verification", ss.next_step("feature_complete", fw), fw)


class Scope(unittest.TestCase):
    """A PRD past prd_drafted without `## Scope rules` gets a note — never a block."""

    RULES = ("## Scope rules\n\n- **A new feature enters the MVP when**: three users ask.\n"
             "- **Not before launch, whatever the evidence**: billing.\n- **Who decides**: the user.\n")

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        (self.root / ".workflow").mkdir()

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def prd(self, text: str) -> None:
        (self.root / ".workflow" / "PRD.md").write_text(text, encoding="utf-8")

    def test_no_note_before_the_prd(self) -> None:
        self.prd("# PRD\n")
        self.assertIsNone(ss.scope_line({"phase": "idea_captured"}, self.root))

    def test_no_prd_file_is_quiet(self) -> None:
        self.assertIsNone(ss.scope_line({"phase": "module_added"}, self.root))

    def test_missing_rules_are_noted(self) -> None:
        self.prd("# PRD\n\n## Non-goals\n\n- x\n")
        out = ss.scope_line({"phase": "module_added"}, self.root)
        self.assertIn("## Scope rules", out)
        self.assertIn("prd-from-idea", out)

    def test_founder_path_points_to_the_playbook(self) -> None:
        self.prd("# PRD\n")
        out = ss.scope_line({"phase": "prd_drafted", "founder": {"decision": "approved"}}, self.root)
        self.assertIn("§12", out)

    def test_complete_rules_are_silent(self) -> None:
        self.prd("# PRD\n\n" + self.RULES)
        self.assertIsNone(ss.scope_line({"phase": "module_added"}, self.root))

    def test_i1_show_state_and_scope_check_agree(self) -> None:
        # final review: two implementations disagreed on TBD, …, an empty line, a partly edited placeholder
        values = [" TBD", " …", "", " <evidence> or three users", ' <the evidence, e.g. "x > y">', " tbd", " three users ask"]
        for value in values:
            text = "# PRD\n\n" + self.RULES.replace("- **A new feature enters the MVP when**: three users ask.",
                                                 f"- **A new feature enters the MVP when**:{value}")
            self.prd(text)
            noted = ss.scope_line({"phase": "module_added"}, self.root) is not None
            self.assertEqual(noted, value.strip() not in ("three users ask",), value)


class Tracker(unittest.TestCase):
    """The tracker is chosen at design time; an older tracker shape is noted until scrum migrates it."""

    def test_legacy_linear_block_is_noted(self) -> None:
        out = ss.tracker_line({"phase": "tasks_split", "linear": {"team_id": "T"}})
        self.assertIn("meta_tracker.py", out)
        self.assertIn("linear", out)

    def test_hand_written_github_block_is_noted(self) -> None:
        self.assertIn("kind", ss.tracker_line({"phase": "tasks_split", "tracker": {"kind": "github", "repo": "o/r"}}))
        out = ss.tracker_line({"phase": "tasks_split", "tracker": {"provider": "github", "issue_map": {"Login": 7}}})
        self.assertIn("title", out)

    def test_not_chosen_after_prd(self) -> None:
        self.assertIn("Tracker: not chosen", ss.tracker_line({"phase": "tasks_split"}))
        self.assertIsNone(ss.tracker_line({"phase": "idea_captured"}))

    def test_chosen_and_current_is_silent(self) -> None:
        self.assertIsNone(ss.tracker_line({"phase": "tasks_split", "tracker": {"provider": "jira"}}))
        self.assertIsNone(ss.tracker_line({"phase": "deployed", "tracker": {"provider": "github",
                                                                            "issue_map": {"0123456789ab": "#7"}}}))

    def test_tasks_split_routes_to_scrum(self) -> None:
        for topology, rows in ss.PHASE_NEXT_BY_STACK.items():
            self.assertIn("scrum (Setup)", rows["tasks_split"], topology)
            self.assertNotIn("linear-scrum", rows["tasks_split"], topology)


class Debt(unittest.TestCase):
    """After deploy, dev-flow proposes the debt audit, and re-proposes it when a material change makes it old."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def meta(self, phase: str = "deployed", block: dict | None = None, history: list | None = None) -> dict:
        m = {"phase": phase, "stack": {"framework": "next"}, "history": history or []}
        if block is not None:
            m["debt_audit"] = block
        return m

    def block(self, before: int = 0, confirm: int = 0, at: str = "2026-10-10T00:00:00Z") -> dict:
        return {"last_run_at": at, "bands": {"before_release": before, "with_features": 0, "later": 0},
                "to_confirm": confirm, "not_checked": [], "sources": {}, "new": 0, "closed": 0,
                "report": "docs/debt/debt-audit.md"}

    def test_silent_before_deployed(self) -> None:
        self.assertIsNone(ss.debt_line(self.meta("feature_complete"), self.root))

    def test_never_audited(self) -> None:
        out = ss.debt_line(self.meta(), self.root)
        self.assertIn("never audited", out)
        self.assertIn("dev-flow debt audit", out)

    def test_stale_after_a_material_change(self) -> None:
        out = ss.debt_line(self.meta(block=self.block(at="2026-10-01T00:00:00Z"),
                                     history=[{"skill": "module-add", "ran_at": "2026-10-05T00:00:00Z"}]), self.root)
        self.assertIn("older than module-add", out)

    def test_new_tests_make_the_audit_old(self) -> None:
        out = ss.debt_line(self.meta(block=self.block(at="2026-10-01T00:00:00Z"),
                                     history=[{"skill": "write-tests", "ran_at": "2026-10-05T00:00:00Z"}]), self.root)
        self.assertIn("older than write-tests", out)

    def test_same_instant_in_two_formats_is_not_stale(self) -> None:
        out = ss.debt_line(self.meta(block=self.block(at="2026-10-05T10:00:00+00:00"),
                                     history=[{"skill": "module-add", "ran_at": "2026-10-05T10:00:00Z"}]), self.root)
        self.assertIsNone(out)

    def test_before_release_count(self) -> None:
        out = ss.debt_line(self.meta(block=self.block(before=2, confirm=1)), self.root)
        self.assertIn("2 to fix", out)
        self.assertIn("1 to confirm", out)

    def test_clean_and_fresh_is_silent(self) -> None:
        self.assertIsNone(ss.debt_line(self.meta(block=self.block()), self.root))

    def test_deployed_rows_start_with_the_debt_audit(self) -> None:
        for topology, rows in ss.PHASE_NEXT_BY_STACK.items():
            self.assertTrue(rows["deployed"].startswith("dev-flow debt audit"), topology)


class Observability(unittest.TestCase):
    """Before the first production deploy a web app with no error tracking gets a note — never a block."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def web(self) -> None:
        (self.root / "package.json").write_text('{"dependencies": {"next": "16"}}')
        (self.root / "app").mkdir()

    def test_no_note_before_feature_complete(self) -> None:
        self.web()
        self.assertIsNone(ss.observability_line({"phase": "module_added", "stack": {"framework": "next"}}, self.root))

    def test_missing_observability_noted_on_web(self) -> None:
        self.web()
        out = ss.observability_line({"phase": "feature_complete", "stack": {"framework": "next"}}, self.root)
        self.assertIn("module-add observability", out)

    def test_expo_points_to_rn_module_add(self) -> None:
        (self.root / "package.json").write_text('{"dependencies": {"expo": "58"}}')
        (self.root / "app.json").write_text('{"expo": {}}')
        out = ss.observability_line({"phase": "deployed", "stack": {"framework": "expo-rn"}}, self.root)
        self.assertIn("rn-module-add observability", out)

    def test_present_is_silent(self) -> None:
        self.web()
        self.assertIsNone(ss.observability_line({"phase": "deployed", "stack": {"framework": "next", "observability": ["errors"]}}, self.root))
