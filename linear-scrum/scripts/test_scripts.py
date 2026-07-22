import unittest
from task_key import task_key


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


if __name__ == "__main__":
    unittest.main()
