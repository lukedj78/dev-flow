"""Tests for github_sync.py, against a fake `gh` on PATH that logs every call."""

from __future__ import annotations

import json
import os
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import github_sync as gs  # noqa: E402
import meta_io  # noqa: E402
from task_key import task_key  # noqa: E402

TASKS = """# Tasks

## Epic: Auth (US-1)

- [ ] **Login** — the form signs a user in
  - Estimated: 4h
  - Priority: P1
- [ ] **Logout** — ends the session
  - Estimated: 2-3d
- [x] **Done already** — shipped

## Non-goals

- [ ] **Not work** — never created
"""

FAKE_GH = r'''#!/usr/bin/env python3
import json, os, sys
d = os.environ["FAKE_GH_DIR"]
args = sys.argv[1:]
with open(os.path.join(d, "calls.log"), "a") as f:
    f.write(json.dumps(args) + "\n")
if args[:2] == ["label", "list"]:
    print(json.dumps([{"name": n} for n in json.loads(os.environ.get("FAKE_GH_LABELS", "[]"))]))
elif args[:1] == ["api"] and "milestones" in args[1] and "-f" not in args:
    print(json.dumps([{"title": t, "number": i + 1} for i, t in enumerate(json.loads(os.environ.get("FAKE_GH_MILESTONES", "[]")))]))
elif args[:2] == ["issue", "create"]:
    counter = os.path.join(d, "n")
    n = int(open(counter).read()) if os.path.exists(counter) else 100
    fail_on = int(os.environ.get("FAKE_GH_FAIL_ON", "0"))
    if fail_on and n - 99 == fail_on:
        sys.stderr.write("HTTP 502\n"); sys.exit(1)
    open(counter, "w").write(str(n + 1))
    print(f"https://github.com/o/r/issues/{n}")
'''


class Sync(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self._tmp.name)
        self.root = self.dir / "proj"
        (self.root / ".workflow").mkdir(parents=True)
        (self.root / ".workflow/tasks.md").write_text(TASKS, encoding="utf-8")
        meta_io.write_json(self.root / ".workflow/meta.json", {"phase": "tasks_split", "tracker": {"provider": "github"}})
        bin_ = self.dir / "bin"
        bin_.mkdir()
        gh = bin_ / "gh"
        gh.write_text(FAKE_GH, encoding="utf-8")
        gh.chmod(gh.stat().st_mode | stat.S_IEXEC)
        self.env = {"PATH": f"{bin_}{os.pathsep}{os.environ['PATH']}", "FAKE_GH_DIR": str(self.dir)}
        self._saved = {k: os.environ.get(k) for k in ("PATH", "FAKE_GH_DIR", "FAKE_GH_LABELS", "FAKE_GH_FAIL_ON",
                                                     "FAKE_GH_MILESTONES")}
        os.environ.update(self.env)

    def tearDown(self) -> None:
        for k, v in self._saved.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        self._tmp.cleanup()

    def run_sync(self, *extra: str) -> int:
        return gs.main([str(self.root), "--repo", "o/r", "--pause", "0", *extra])

    def calls(self) -> list[list[str]]:
        log = self.dir / "calls.log"
        return [json.loads(l) for l in log.read_text().splitlines()] if log.exists() else []

    def writes(self) -> list[list[str]]:
        return [c for c in self.calls() if c[:2] in (["label", "create"], ["issue", "create"])
                or (c[:1] == ["api"] and "-f" in c)]

    def issue_map(self) -> dict:
        return meta_io.read_meta(self.root / ".workflow/meta.json")["tracker"].get("issue_map", {})

    def test_dry_run_calls_nothing_that_writes(self) -> None:
        self.assertEqual(self.run_sync("--dry-run"), 0)
        self.assertEqual(self.writes(), [])
        self.assertEqual(self.issue_map(), {})

    def test_creates_missing_issues_and_records_them_by_task_key(self) -> None:
        self.assertEqual(self.run_sync(), 0)
        created = [c for c in self.calls() if c[:2] == ["issue", "create"]]
        self.assertEqual([c[c.index("--title") + 1] for c in created], ["Login", "Logout"])
        self.assertEqual(self.issue_map(), {task_key("- [ ] **Login** — x"): "#100", task_key("- [ ] **Logout** — x"): "#101"})

    def test_a_rerun_creates_nothing(self) -> None:
        self.run_sync()
        before = len([c for c in self.calls() if c[:2] == ["issue", "create"]])
        self.assertEqual(self.run_sync(), 0)
        self.assertEqual(len([c for c in self.calls() if c[:2] == ["issue", "create"]]), before)

    def test_existing_labels_are_reused(self) -> None:
        os.environ["FAKE_GH_LABELS"] = json.dumps(["priority: P1", "Area: Auth"])
        self.run_sync()
        made = [c[2] for c in self.calls() if c[:2] == ["label", "create"]]
        self.assertNotIn("priority: P1", made)
        self.assertFalse(any(m.lower() == "area: auth" for m in made), made)
        login = next(c for c in self.calls() if c[:2] == ["issue", "create"] and "Login" in c)
        self.assertIn("Area: Auth", login)   # the repo's own spelling

    def test_estimate_and_priority_labels(self) -> None:
        self.run_sync()
        by_title = {c[c.index("--title") + 1]: c for c in self.calls() if c[:2] == ["issue", "create"]}
        self.assertIn("estimate: 2", by_title["Login"])     # 4h → half a day → 2
        self.assertIn("priority: P1", by_title["Login"])
        self.assertIn("estimate: 5", by_title["Logout"])    # 2-3 days → 5
        self.assertIn("priority: P2", by_title["Logout"])   # the default

    def test_points(self) -> None:
        for hint, pts in (("1h", 1), ("2h", 1), ("4h", 2), ("2-8h", 3), ("1d", 3), ("2-3d", 5), ("1w", 8), ("3w", 13)):
            self.assertEqual(gs.points(hint), pts, hint)
        self.assertIsNone(gs.points("soon"))

    def test_milestone_is_passed_and_created_when_missing(self) -> None:
        self.run_sync("--milestone", "Sprint 1 — sign in")
        created = [c for c in self.calls() if c[:2] == ["issue", "create"]]
        self.assertTrue(all("Sprint 1 — sign in" in c for c in created))
        self.assertTrue(any(c[:1] == ["api"] and "-f" in c and "title=Sprint 1 — sign in" in c for c in self.calls()))

    def test_an_existing_milestone_is_not_recreated(self) -> None:
        os.environ["FAKE_GH_MILESTONES"] = json.dumps(["Sprint 1 — sign in"])
        self.run_sync("--milestone", "Sprint 1 — sign in")
        self.assertFalse(any(c[:1] == ["api"] and "-f" in c for c in self.calls()))

    def test_a_failure_midway_keeps_what_was_created(self) -> None:
        os.environ["FAKE_GH_FAIL_ON"] = "2"
        self.assertEqual(self.run_sync(), 1)
        self.assertEqual(self.issue_map(), {task_key("- [ ] **Login** — x"): "#100"})
        os.environ["FAKE_GH_FAIL_ON"] = "0"
        self.assertEqual(self.run_sync(), 0)
        self.assertEqual(len(self.issue_map()), 2)

    def test_make_issues_shim_still_works(self) -> None:
        shim = HERE.parents[1] / "project-infra-setup/scripts/make_issues.py"
        r = subprocess.run([sys.executable, str(shim), "--repo", "o/r", "--tasks", str(self.root / ".workflow/tasks.md"),
                            "--map", str(self.root / ".workflow/github-issues.json"), "--pause", "0"],
                           capture_output=True, text=True, env={**os.environ})
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(len(self.issue_map()), 2)
        self.assertIn("github_sync.py", r.stdout + r.stderr)


if __name__ == "__main__":
    unittest.main()
