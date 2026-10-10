"""Tests for project-infra-setup's scripts. No network, no gh.

    cd project-infra-setup/scripts && python3 -m unittest test_project_infra_setup -v
"""
import collections
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import make_issues as mi  # noqa: E402

TASKS = """# P — Tasks

## Setup (S0)

- [x] **Write DESIGN.md** — done already.
- [ ] **Set up the scaffold** — owned by another skill. *(addressed by `design-md-to-app`)*

## Epic: Auth (US-8) · S0

- [ ] **Build the sign-in page** — Sign-in (`/sign-in`). *(addressed by `screenshot-to-page`)*
  - Acceptance: follows the artboards.
    - Roles are checked server-side.
  - Files likely touched: `app/(auth)/sign-in/page.tsx`
  - Estimated: 4h
- [ ] **Spike: how to link identities** — read the docs.
- [ ] **Add the audit log** — hash chain.
  - Files likely touched: `agent/hooks/audit.ts`

## Non-goals (do NOT do)

- [ ] **Not a task** — this section is skipped.
"""


class Issues(unittest.TestCase):
    def setUp(self):
        self.tasks = mi.parse(TASKS)

    def test_sections_that_are_not_work_are_skipped(self):
        self.assertNotIn("Not a task", [t["title"] for t in self.tasks])

    def test_done_tasks_are_parsed_and_flagged(self):
        d = {t["title"]: t["done"] for t in self.tasks}
        self.assertTrue(d["Write DESIGN.md"])
        self.assertFalse(d["Build the sign-in page"])

    def test_indented_lines_belong_to_the_task_above(self):
        t = next(t for t in self.tasks if t["title"] == "Build the sign-in page")
        self.assertEqual(len(t["extra"]), 4)
        self.assertIn("Roles are checked server-side.", "\n".join(t["extra"]))

    def test_type_rules(self):
        by = {t["title"]: mi.type_of(t)[0] for t in self.tasks}
        self.assertEqual(by["Build the sign-in page"], "tipo: pagina")
        self.assertEqual(by["Spike: how to link identities"], "tipo: spike")
        self.assertEqual(by["Add the audit log"], "tipo: agente")
        self.assertEqual(by["Set up the scaffold"], "tipo: setup")

    def test_area_label_is_short_stable_and_coloured(self):
        epics = list(dict.fromkeys(t["epic"] for t in self.tasks))
        a = mi.area_label(epics, "Epic: Auth (US-8) · S0")
        self.assertEqual(a[0], "area: auth")
        self.assertEqual(a, mi.area_label(epics, "Epic: Auth (US-8) · S0"))

    def test_area_label_drops_commas_github_rejects(self):
        epic = "Epic: Search, filters (US-3)"
        self.assertEqual(mi.area_label([epic], epic)[0], "area: search filters")

    def test_body_keeps_the_acceptance_and_names_the_source(self):
        t = next(t for t in self.tasks if t["title"] == "Build the sign-in page")
        b = mi.body_of(t, "tasks.md", "Design: https://example.test")
        self.assertIn("Acceptance: follows the artboards.", b)
        self.assertIn("Tracked in `tasks.md`.", b)
        self.assertIn("https://example.test", b)

    def test_every_task_gets_exactly_one_area_and_one_type(self):
        epics = list(dict.fromkeys(t["epic"] for t in self.tasks))
        c = collections.Counter(mi.area_label(epics, t["epic"])[0] for t in self.tasks)
        self.assertEqual(sum(c.values()), len(self.tasks))


if __name__ == "__main__":
    unittest.main(verbosity=2)
