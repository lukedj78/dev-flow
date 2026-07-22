import unittest
from task_key import task_key
from meta_linear import ensure_scrum, upsert_linear, record_issues


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
        a = task_key("- [ ] **Wire login flow**")
        b = task_key("- [ ] **Wire logout flow**")
        self.assertNotEqual(a, b)

    def test_is_12_hex_chars(self):
        k = task_key("- [ ] **Anything**")
        self.assertRegex(k, r"^[0-9a-f]{12}$")


class TestMetaLinear(unittest.TestCase):
    def base(self):
        return {"project_slug": "demo", "phase": "tasks_split", "history": []}

    def test_upsert_linear_sets_block(self):
        m = upsert_linear(self.base(), team_id="T", team_name="Lucadigerlando",
                          project_id="P", url="http://x")
        self.assertEqual(m["linear"]["team_id"], "T")
        self.assertEqual(m["linear"]["project_id"], "P")
        self.assertEqual(m["linear"]["issue_map"], {})

    def test_record_issues_merges_no_dup(self):
        m = upsert_linear(self.base(), team_id="T", team_name="N",
                          project_id="P", url="u")
        m = record_issues(m, {"abc": "LUC-1"})
        m = record_issues(m, {"abc": "LUC-1", "def": "LUC-2"})  # re-run + new
        self.assertEqual(m["linear"]["issue_map"], {"abc": "LUC-1", "def": "LUC-2"})

    def test_ensure_scrum_defaults(self):
        m = ensure_scrum(self.base())
        self.assertEqual(m["scrum"]["cadence_weeks"], 2)
        self.assertEqual(m["scrum"]["estimate_scale"], "fibonacci")
        self.assertEqual(m["scrum"]["states"]["blocked_label"], "blocked")

    def test_ensure_scrum_is_idempotent(self):
        m = ensure_scrum(self.base())
        m["scrum"]["velocity_target"] = 13     # user-set value must survive
        m2 = ensure_scrum(m)
        self.assertEqual(m2["scrum"]["velocity_target"], 13)


if __name__ == "__main__":
    unittest.main()
