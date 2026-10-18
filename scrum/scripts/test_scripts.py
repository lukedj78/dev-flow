"""Tests for task_key.py and meta_tracker.py."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import meta_tracker as mt  # noqa: E402
from task_key import task_key  # noqa: E402

HERE = Path(__file__).resolve().parent


class TestTaskKey(unittest.TestCase):
    def test_stable_across_checkbox_state_and_whitespace(self):
        a = task_key("- [ ] **Wire login flow** — connect the form to better-auth")
        b = task_key("- [x]   **Wire login flow**  — connect the form to better-auth")
        self.assertEqual(a, b)

    def test_title_only_ignores_body(self):
        a = task_key("- [ ] **Wire login flow** — body one")
        b = task_key("- [ ] **Wire login flow** — a totally different body")
        self.assertEqual(a, b)

    def test_different_titles_differ(self):
        self.assertNotEqual(task_key("- [ ] **Wire login flow**"), task_key("- [ ] **Wire logout flow**"))

    def test_is_12_hex_chars(self):
        self.assertRegex(task_key("- [ ] **Anything**"), r"^[0-9a-f]{12}$")


LOGIN = task_key("- [ ] **Login** — x")


class Tracker(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        (self.root / ".workflow").mkdir()
        (self.root / ".workflow/tasks.md").write_text("## Epic: Auth\n\n- [ ] **Login** — x\n- [x] **Logout** — y\n",
                                                      encoding="utf-8")

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_choose_records_the_provider_only(self):
        self.assertEqual(mt.choose({}, "jira"), {"tracker": {"provider": "jira"}})
        with self.assertRaises(ValueError):
            mt.choose({}, "asana")

    def test_upsert_keeps_the_issue_map(self):
        m = mt.record_issues(mt.choose({}, "linear"), {LOGIN: "LUC-1"})
        m = mt.upsert(m, "linear", {"team_id": "T", "project_id": "P"}, "https://linear.app/x")
        self.assertEqual(m["tracker"]["issue_map"], {LOGIN: "LUC-1"})
        self.assertEqual(m["tracker"]["project"], {"team_id": "T", "project_id": "P"})
        self.assertIn("last_synced_at", m["tracker"])

    def test_record_issues_no_duplicates(self):
        m = mt.record_issues({}, {LOGIN: "#1"})
        m = mt.record_issues(m, {LOGIN: "#1"})
        self.assertEqual(m["tracker"]["issue_map"], {LOGIN: "#1"})

    def test_ensure_scrum_adds_severity_labels(self):
        m = mt.ensure_scrum({"scrum": {"labels": {"web": "frontend"}}})
        self.assertEqual(m["scrum"]["severity_labels"], {f"S{i}": f"severity: S{i}" for i in range(1, 5)})
        self.assertEqual(m["scrum"]["bug_label"], "bug")
        self.assertEqual(m["scrum"]["labels"], {"web": "frontend"})
        self.assertEqual(m["scrum"]["cadence_weeks"], 2)

    def test_migrate_linear_block(self):
        meta = {"linear": {"team_id": "T", "team_name": "N", "project_id": "P", "url": "u",
                           "issue_map": {LOGIN: "LUC-1"}, "last_synced_at": "2026-10-01T00:00:00Z"}}
        out, _ = mt.migrate(meta, self.root)
        self.assertNotIn("linear", out)
        t = out["tracker"]
        self.assertEqual((t["provider"], t["url"], t["issue_map"]), ("linear", "u", {LOGIN: "LUC-1"}))
        self.assertEqual(t["project"], {"team_id": "T", "team_name": "N", "project_id": "P"})
        self.assertEqual(t["last_synced_at"], "2026-10-01T00:00:00Z")

    def test_migrate_linear_into_a_chosen_provider(self):
        meta = {"tracker": {"provider": "linear"}, "linear": {"team_id": "T", "project_id": "P", "url": "u",
                                                              "issue_map": {LOGIN: "LUC-1"}}}
        out, _ = mt.migrate(meta, self.root)
        self.assertEqual(out["tracker"]["project"]["team_id"], "T")
        self.assertEqual(out["tracker"]["issue_map"], {LOGIN: "LUC-1"})
        self.assertNotIn("linear", out)

    def test_migrate_archistudio_shape(self):
        (self.root / ".workflow/github-issues.json").write_text(json.dumps({"Login": 7}), encoding="utf-8")
        meta = {"tracker": {"kind": "github", "repo": "o/archi", "issues": 1, "map": ".workflow/github-issues.json",
                            "bodies": ".workflow/issue-bodies/",
                            "scrum": {"sprint_weeks": 2, "capacity_hours": 30, "milestones": ["S1"],
                                      "plan": ".workflow/sprints.md"}}}
        out, _ = mt.migrate(meta, self.root)
        t = out["tracker"]
        self.assertEqual(t["provider"], "github")
        self.assertEqual(t["project"], {"repo": "o/archi"})
        self.assertEqual(t["issue_map"], {LOGIN: "#7"})
        self.assertEqual(t["bodies"], ".workflow/issue-bodies/")
        self.assertEqual(t["map"], ".workflow/github-issues.json")   # kept: the file is still there
        self.assertNotIn("kind", t)
        self.assertNotIn("scrum", t)
        self.assertEqual(out["scrum"]["cadence_weeks"], 2)
        self.assertEqual(out["scrum"]["capacity_hours"], 30)
        self.assertEqual(out["scrum"]["milestones"], ["S1"])
        self.assertEqual(out["scrum"]["plan"], ".workflow/sprints.md")

    def test_migrate_fit_room_shape(self):
        meta = {"tracker": {"kind": "github-issues", "linear": "opt-out (2026-09-22)", "repo": "o/fr",
                            "issue_map": {"Login": 7}}}
        out, _ = mt.migrate(meta, self.root)
        t = out["tracker"]
        self.assertEqual((t["provider"], t["project"], t["issue_map"]), ("github", {"repo": "o/fr"}, {LOGIN: "#7"}))
        self.assertEqual(t["linear"], "opt-out (2026-09-22)")

    def test_migrate_folds_a_lone_github_issues_file(self):
        # found on bidflow and smart-travel: make_issues.py's map, and nothing about it in meta.json
        (self.root / ".workflow/github-issues.json").write_text(json.dumps({"Login": 7}), encoding="utf-8")
        out, notes = mt.migrate({"phase": "tasks_split"}, self.root)
        t = out["tracker"]
        self.assertEqual((t["provider"], t["issue_map"], t["map"]), ("github", {LOGIN: "#7"}, ".workflow/github-issues.json"))
        self.assertTrue(any("github-issues.json" in n for n in notes), notes)

    def test_legacy_shape_sees_a_lone_github_issues_file(self):
        (self.root / ".workflow/github-issues.json").write_text("{}", encoding="utf-8")
        self.assertIn("github-issues.json", mt.legacy_shape({}, self.root))
        self.assertIsNone(mt.legacy_shape({"tracker": {"provider": "github", "map": ".workflow/github-issues.json",
                                                       "issue_map": {}}}, self.root))

    def test_migrate_keeps_unmatched_titles(self):
        meta = {"tracker": {"kind": "github", "repo": "o/r", "issue_map": {"Login": 7, "Gone": 9}}}
        out, notes = mt.migrate(meta, self.root)
        self.assertEqual(out["tracker"]["issue_map"], {LOGIN: "#7"})
        self.assertEqual(out["tracker"]["unmatched"], {"Gone": "#9"})
        self.assertTrue(any("Gone" in n for n in notes), notes)

    def test_migrate_is_idempotent(self):
        meta = {"tracker": {"kind": "github", "repo": "o/r", "issue_map": {"Login": 7}},
                "linear": {"team_id": "T"}}
        once, _ = mt.migrate(json.loads(json.dumps(meta)), self.root)
        twice, _ = mt.migrate(json.loads(json.dumps(once)), self.root)
        self.assertEqual(once, twice)

    def test_legacy_shape(self):
        self.assertIn("linear", mt.legacy_shape({"linear": {"team_id": "T"}}))
        self.assertIn("kind", mt.legacy_shape({"tracker": {"kind": "github"}}))
        self.assertIn("title", mt.legacy_shape({"tracker": {"provider": "github", "issue_map": {"Login": 7}}}))
        self.assertIsNone(mt.legacy_shape({"tracker": {"provider": "github", "issue_map": {LOGIN: "#7"}}}))
        self.assertIsNone(mt.legacy_shape({}))

    def test_cli_writes_under_the_lock(self):
        p = self.root / ".workflow/meta.json"
        sys.path.insert(0, str(HERE))
        import meta_io
        meta_io.write_json(p, {"phase": "tasks_split", "linear": {"team_id": "T", "issue_map": {LOGIN: "LUC-1"}}})
        r = subprocess.run([sys.executable, str(HERE / "meta_tracker.py"), str(p), "migrate"], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(meta_io.read_meta(p)["tracker"]["provider"], "linear")
        r = subprocess.run([sys.executable, str(HERE / "meta_tracker.py"), str(p), "choose", "--provider", "asana"],
                           capture_output=True, text=True)
        self.assertNotEqual(r.returncode, 0)


if __name__ == "__main__":
    unittest.main()
