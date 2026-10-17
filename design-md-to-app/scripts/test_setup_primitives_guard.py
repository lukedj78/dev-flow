"""Tests for setup_primitives_guard.py and the write-time guard it installs.

Two halves:
  - Install: what lands where, that a re-run changes nothing, that .claude/settings.json keeps every hook
    already in it, that --check fails on each missing piece. No node needed.
  - Guard: the hook itself, run with node against a fixture app whose node_modules is a symlink to a real
    project's (read-only; no network). Refused writes, allowed writes, a file with old findings that is not
    blocked, the Stop check through git. Skipped when no such project is found.

    cd design-md-to-app/scripts && python3 -m unittest test_setup_primitives_guard
"""

from __future__ import annotations

import contextlib
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import setup_design_lint as sdl  # noqa: E402
import setup_primitives_guard as spg  # noqa: E402
from test_setup_design_lint import meta, node_project, single_app, shadcn_monorepo, write  # noqa: E402


def quiet(fn, *a):
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        return fn(*a)


def scaffold(root: Path, phase: str = "scaffolded") -> None:
    """A single app with its preset written, as setup_design_lint.py leaves it before calling the guard."""
    single_app(root)
    write(root, "components/ui/button.tsx", "export function Button() { return null }\n")
    write(root, "components/ui/card.tsx", "export function Card() { return null }\n")
    meta(root, phase, framework="next", ui="shadcn", design_lint="shadcn-lint")
    (u,) = sdl.detect(root)
    u["preset"].write_text(sdl.stamp(sdl.preset_source({**u, "ui": "shadcn"}, "error")))


class Install(unittest.TestCase):
    def test_installs_everything_and_rerun_changes_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); scaffold(root)
            self.assertFalse(spg.check(root)[0])
            self.assertEqual(quiet(spg.install, root), 0)
            ok, lines = spg.check(root)
            self.assertTrue(ok, lines)
            for f in ("primitives-guard.mjs", "eslint.guard.mjs"):
                self.assertEqual((root / "scripts/guard" / f).read_bytes(), (spg.ASSETS / f).read_bytes())
            (unit,) = json.loads((root / "scripts/guard/guard.json").read_text())["units"]
            self.assertEqual(unit["dir"], ".")
            self.assertEqual(unit["preset"], "eslint.design-system.mjs")
            self.assertEqual(unit["components"], "components/ui")
            self.assertIn("components/ui/**", unit["ignores"])
            self.assertEqual(unit["rules"]["design/no-handmade-ui"], "error")
            self.assertIn(spg.BEGIN, (root / "AGENTS.md").read_text())
            self.assertEqual(json.loads((root / ".workflow/meta.json").read_text())["stack"]["primitives_guard"], "installed")
            snapshot = {p: p.read_bytes() for p in root.rglob("*") if p.is_file()}
            quiet(spg.install, root)
            self.assertEqual({p: p.read_bytes() for p in root.rglob("*") if p.is_file()}, snapshot, "idempotent")

    def test_settings_are_merged_never_replaced(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); scaffold(root)
            mine = {"permissions": {"allow": ["Bash(pnpm lint)"]},
                    "hooks": {"PreToolUse": [{"matcher": "Bash", "hooks": [{"type": "command", "command": "node x.mjs"}]}],
                              "PostToolUse": [{"matcher": "Edit", "hooks": [{"type": "command", "command": "prettier"}]}]}}
            write(root, ".claude/settings.json", mine)
            quiet(spg.install, root)
            quiet(spg.install, root)
            s = json.loads((root / ".claude/settings.json").read_text())
            self.assertEqual(s["permissions"], mine["permissions"])
            self.assertEqual(s["hooks"]["PostToolUse"][0], mine["hooks"]["PostToolUse"][0], "existing hook kept first")
            self.assertEqual(len(s["hooks"]["PostToolUse"]), 2, "the guard's Bash post hook added once")
            self.assertEqual(s["hooks"]["PreToolUse"][0], mine["hooks"]["PreToolUse"][0], "existing hook kept first")
            self.assertEqual(len(s["hooks"]["PreToolUse"]), 3, "the guard's Write and Bash hooks added once each")
            self.assertEqual(len(s["hooks"]["Stop"]), 1)
            self.assertEqual(len(s["hooks"]["SubagentStop"]), 1)

    def test_invalid_settings_are_not_overwritten(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); scaffold(root)
            write(root, ".claude/settings.json", "{ not json")
            with self.assertRaises(SystemExit):
                quiet(spg.install, root)
            self.assertEqual((root / ".claude/settings.json").read_text(), "{ not json")

    def test_check_names_each_missing_piece(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); scaffold(root)
            quiet(spg.install, root)
            s = json.loads((root / ".claude/settings.json").read_text())
            del s["hooks"]["Stop"]
            write(root, ".claude/settings.json", s)
            (root / "scripts/guard/eslint.guard.mjs").write_text("// edited\n")
            ok, problems = spg.check(root)
            self.assertFalse(ok)
            self.assertTrue(any("Stop hook" in p for p in problems), problems)
            self.assertTrue(any("eslint.guard.mjs differs" in p for p in problems), problems)
            quiet(spg.install, root)
            self.assertTrue(spg.check(root)[0], "a re-run repairs it")

    def test_claude_md_gets_the_section_only_when_it_does_not_import_agents(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); scaffold(root)
            write(root, "CLAUDE.md", "@AGENTS.md\n")
            quiet(spg.install, root)
            self.assertEqual((root / "CLAUDE.md").read_text(), "@AGENTS.md\n")
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); scaffold(root)
            write(root, "CLAUDE.md", "# Project rules\n")
            quiet(spg.install, root)
            self.assertIn(spg.BEGIN, (root / "CLAUDE.md").read_text())

    def test_refuses_without_the_rule_in_the_preset(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); scaffold(root)
            (root / "eslint.design-system.mjs").write_text("export const designSystemConfig = []\n")
            self.assertEqual(quiet(spg.install, root), 1)
            self.assertFalse((root / "scripts/guard").exists())

    def test_opt_out_and_other_stacks(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); scaffold(root)
            m = json.loads((root / ".workflow/meta.json").read_text())
            m["stack"]["primitives_guard"] = "none"
            write(root, ".workflow/meta.json", m)
            self.assertFalse(spg.check(root)[0], "an opt-out needs its reason")
            m["stack_config"] = {"primitives_guard_reason": "throwaway spike, deleted Friday"}
            write(root, ".workflow/meta.json", m)
            self.assertTrue(spg.check(root)[0])
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); meta(root, "scaffolded", framework="expo-rn")
            self.assertTrue(spg.check(root)[0], "mobile: not applicable (an open gap, contracts.md)")

    def test_monorepo_units_point_at_the_shared_preset_and_packages_ui(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); shadcn_monorepo(root)
            (u,) = sdl.detect(root)
            u["preset"].write_text(sdl.preset_source({**u, "ui": "shadcn"}, "error"))
            units = spg.guard_units(root, [u])
            self.assertEqual(sorted(x["dir"] for x in units), ["apps/web", "packages/ui"])
            self.assertTrue(all(x["preset"] == "packages/eslint-config/design-system.mjs" for x in units))
            self.assertTrue(all(x["components"] == "packages/ui/src/components" for x in units))
            ui = next(x for x in units if x["dir"] == "packages/ui")
            self.assertIn("src/components/**", ui["ignores"])


class Retrofit(unittest.TestCase):
    """dev-flow's one-command retrofit is setup_design_lint.py: the rule, then the guard."""

    def test_setup_calls_the_guard(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); single_app(root)
            pkg = json.loads((root / "package.json").read_text())
            pkg["devDependencies"] = {"@shadcn/lint": "0.1.0"}
            write(root, "package.json", pkg)
            meta(root, "module_added", framework="next", ui="shadcn")
            original = sdl.run_eslint
            sdl.run_eslint = lambda t: []
            try:
                self.assertEqual(quiet(sdl.setup, root), 0)
                self.assertEqual(quiet(sdl.setup, root), 0)
            finally:
                sdl.run_eslint = original
            ok, lines = sdl.check(root)
            self.assertTrue(ok, lines)
            self.assertTrue(spg.check(root)[0])


@unittest.skipUnless(node_project(), "needs node + a project with eslint, eslint-config-next, @shadcn/lint")
class Guard(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        scaffold(self.root)
        (self.root / "node_modules").symlink_to(node_project() / "node_modules")
        quiet(spg.install, self.root)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def hook(self, mode: str, event: dict) -> subprocess.CompletedProcess:
        return subprocess.run(["node", str(self.root / "scripts/guard/primitives-guard.mjs"), mode],
                              input=json.dumps(event), capture_output=True, text=True, check=False,
                              cwd=self.root, env={**os.environ, "CLAUDE_PROJECT_DIR": str(self.root)})

    def write_event(self, rel: str, content: str) -> dict:
        return {"tool_name": "Write", "tool_input": {"file_path": str(self.root / rel), "content": content}}

    PAGE = 'import { Button } from "@/components/ui/button"\n\nexport default function Page() {\n  return <Button>Go</Button>\n}\n'

    def test_refuses_a_write_that_adds_hand_made_ui(self) -> None:
        for rel, body in (("app/page.tsx", "<button className=\"px-2\">Go</button>"),
                          ("components/trips/row.tsx", "<div className=\"rounded-xl border p-4\" />"),
                          ("components/trips/tabs.tsx", "<div role=\"tab\" />")):
            with self.subTest(rel):
                r = self.hook("pre", self.write_event(rel, f"export default function X() {{\n  return {body}\n}}\n"))
                self.assertEqual(r.returncode, 2, r.stderr)
                self.assertIn("Write refused", r.stderr)
                self.assertIn("stop and ask the user", r.stderr)
                self.assertIn("button, card", r.stderr, "names the primitives in components/ui")

    def test_allows_primitives_composition_and_the_vendored_directory(self) -> None:
        ok = {
            "app/page.tsx": self.PAGE,
            "app/x/page.tsx": 'export default function X() {\n  return <Item render={<button type="button" />} />\n}\n',
            "components/ui/thing.tsx": "export function Thing() {\n  return <button />\n}\n",
            "app/x/page.test.tsx": "export const t = <button />\n",
            "lib/notes.md": "<button>",
        }
        for rel, content in ok.items():
            with self.subTest(rel):
                r = self.hook("pre", self.write_event(rel, content))
                self.assertEqual(r.returncode, 0, r.stderr)

    def test_a_file_with_old_findings_is_not_blocked_but_a_new_one_is(self) -> None:
        legacy = "export default function X() {\n  return (\n    <div>\n      <button>Old</button>\n      <p>Text</p>\n    </div>\n  )\n}\n"
        write(self.root, "components/legacy.tsx", legacy)
        path = str(self.root / "components/legacy.tsx")
        edit = {"tool_name": "Edit", "tool_input": {"file_path": path, "old_string": "<p>Text</p>", "new_string": "<p>Other text</p>"}}
        self.assertEqual(self.hook("pre", edit).returncode, 0, "an unrelated edit to a legacy file")
        fix = {"tool_name": "Edit", "tool_input": {"file_path": path, "old_string": "<button>Old</button>", "new_string": "<Button>Old</Button>"}}
        self.assertEqual(self.hook("pre", fix).returncode, 0, "converting it is never blocked")
        worse = {"tool_name": "MultiEdit", "tool_input": {"file_path": path, "edits": [
            {"old_string": "<p>Text</p>", "new_string": "<p>Text</p>\n      <label>Name</label>"}]}}
        r = self.hook("pre", worse)
        self.assertEqual(r.returncode, 2, r.stderr)
        self.assertIn("<label>", r.stderr)
        self.assertNotIn("<button>", r.stderr, "only what the edit adds is reported")

    def test_stop_catches_what_the_shell_wrote(self) -> None:
        git = lambda *a: subprocess.run(["git", *a], cwd=self.root, capture_output=True, text=True, check=True)  # noqa: E731
        git("init", "-q")
        git("-c", "user.email=t@t", "-c", "user.name=t", "commit", "-q", "--allow-empty", "-m", "init")
        write(self.root, "app/page.tsx", self.PAGE)
        self.assertEqual(self.hook("stop", {}).returncode, 0)
        write(self.root, "components/sep.tsx", "export const Sep = () => <hr className=\"my-4\" />\n")
        r = self.hook("stop", {})
        self.assertEqual(r.returncode, 2, r.stderr)
        self.assertIn("components/sep.tsx", r.stderr)
        self.assertEqual(self.hook("stop", {"stop_hook_active": True}).returncode, 0, "never loops")

    def init_repo(self) -> None:
        git = lambda *a: subprocess.run(["git", *a], cwd=self.root, capture_output=True, text=True, check=True)  # noqa: E731
        git("init", "-q")
        git("-c", "user.email=t@t", "-c", "user.name=t", "commit", "-q", "--allow-empty", "-m", "init")

    def test_a_shell_write_is_caught_right_after_the_command(self) -> None:
        # The 5-session trial of 2026-10-17: every agent wrote its files with `cat > … <<'EOF'`, which the
        # Write/Edit hook never sees; only `stop` caught it, at the end of the turn (AUDIT.md P1-32).
        self.init_repo()
        write(self.root, "components/legacy.tsx", "export const L = () => <button>Old</button>\n")
        bash = {"session_id": "s1", "tool_name": "Bash", "tool_input": {"command": "cat > components/sep.tsx <<'EOF' …"}}
        self.assertEqual(self.hook("bash-pre", bash).returncode, 0)
        write(self.root, "components/sep.tsx", "export const Sep = () => <hr className=\"my-4\" />\n")
        r = self.hook("bash-post", bash)
        self.assertEqual(r.returncode, 2, r.stderr)
        self.assertIn("components/sep.tsx", r.stderr)
        self.assertNotIn("legacy.tsx", r.stderr, "only what this command touched")

    def test_only_what_the_command_added_is_reported(self) -> None:
        self.init_repo()
        before = "export const R = () => (\n  <div>\n    <button>Old</button>\n  </div>\n)\n"
        write(self.root, "components/row.tsx", before)
        bash = {"session_id": "s2", "tool_name": "Bash", "tool_input": {"command": "sed -i …"}}
        self.hook("bash-pre", bash)
        write(self.root, "components/row.tsx", before.replace("  </div>", "    <p>x</p>\n  </div>"))
        self.assertEqual(self.hook("bash-post", bash).returncode, 0, "the old <button> was there before the command")

    def test_a_command_that_touches_no_ui_file_is_silent(self) -> None:
        self.init_repo()
        bash = {"session_id": "s3", "tool_name": "Bash", "tool_input": {"command": "ls && echo hi > notes.md"}}
        self.hook("bash-pre", bash)
        write(self.root, "notes.md", "<button>")
        r = self.hook("bash-post", bash)
        self.assertEqual(r.returncode, 0, r.stderr)

    def test_without_a_snapshot_the_post_hook_stays_out_of_the_way(self) -> None:
        self.init_repo()
        write(self.root, "components/sep.tsx", "export const Sep = () => <hr />\n")
        bash = {"session_id": "never-pre", "tool_name": "Bash", "tool_input": {"command": "true"}}
        self.assertEqual(self.hook("bash-post", bash).returncode, 0, "stop still catches it at the end")


if __name__ == "__main__":
    unittest.main()
