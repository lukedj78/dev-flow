"""install.sh and uninstall.sh against a throwaway HOME: what they write, what they keep, what they restore.

    python3 scripts/test_install.py        (or: cd scripts && python3 -m unittest test_install -v)

Why this exists: nothing ran the installers. uninstall.sh deleted a user's own `bootstrap/` skill and
any AGENTS.md / GEMINI.md / .cursorrules in the skills folder; install.sh overwrote those files without
a backup; and the README promised an uninstall that restores the previous version, which it no longer
did (AUDIT.md §6.3). Every case runs with HOME pointed at a temp dir, never at the real one.
"""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SKILL_COUNT = len([d for d in REPO.glob("*/SKILL.md")])


class Fixture(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.home = Path(self._tmp.name) / "home with space"
        self.home.mkdir()

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def sh(self, script: str, *args: str) -> subprocess.CompletedProcess:
        env = {k: v for k, v in os.environ.items() if k not in ("CLAUDE_SKILLS_DIR", "DEV_FLOW_SKILLS_DIR")}
        env["HOME"] = str(self.home)
        return subprocess.run(["bash", str(REPO / script), *args], cwd=REPO, env=env,
                              capture_output=True, text=True)

    def install(self, *args: str) -> subprocess.CompletedProcess:
        r = self.sh("install.sh", *args)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        return r

    def uninstall(self, *args: str) -> subprocess.CompletedProcess:
        r = self.sh("uninstall.sh", *args)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        return r

    def backups(self, skills: Path) -> list[Path]:
        return sorted(skills.parent.glob(skills.name + "-backup-*"))


# Where each runtime's install lands, and the bootstrap file it drops (install.sh's own table).
PLATFORMS = {
    "claude": (".claude/skills", None),
    "codex": (".codex/dev-flow-skills", "AGENTS.md"),
    "copilot": (".config/gh-copilot/skills", None),
    "gemini": (".gemini/skills", "GEMINI.md"),
    "cursor": (".dev-flow-skills", ".cursorrules"),
    "generic": (".dev-flow-skills", "system-prompt.md"),
}


class EveryPlatform(Fixture):
    """The same round trip on all six runtimes. This proves the install, not that each runtime then loads
    the skills: four of them are still "scaffolded, not validated" (install.sh --list-platforms)."""

    def test_install_reinstall_uninstall(self) -> None:
        for platform, (where, bootstrap) in PLATFORMS.items():
            with self.subTest(platform=platform):
                skills = self.home / where
                mine = skills / "my-own-skill" / "SKILL.md"
                mine.parent.mkdir(parents=True, exist_ok=True)
                mine.write_text("---\nname: my-own-skill\n---\n")
                self.install("--platform", platform)
                self.install("--platform", platform)
                self.assertEqual(len([d for d in skills.glob("*/SKILL.md")]), SKILL_COUNT + 1)
                self.assertTrue((skills / "bootstrap" / "tool-mappings.md").is_file())
                if bootstrap:
                    self.assertEqual((skills / bootstrap).read_bytes(),
                                     (REPO / "bootstrap" / "templates" / bootstrap).read_bytes())
                self.assertEqual(list(skills.glob("*.bak")), [])
                self.uninstall("--platform", platform)
                self.assertEqual(sorted(p.name for p in skills.iterdir()), ["my-own-skill"])


class Claude(Fixture):
    def setUp(self) -> None:
        super().setUp()
        self.skills = self.home / ".claude" / "skills"

    def test_install_then_uninstall_leaves_nothing_of_ours(self) -> None:
        self.install()
        self.assertEqual(len([d for d in self.skills.glob("*/SKILL.md")]), SKILL_COUNT)
        self.uninstall()
        self.assertEqual(sorted(p.name for p in self.skills.iterdir()), [])

    def test_a_user_skill_named_bootstrap_survives(self) -> None:
        mine = self.skills / "bootstrap" / "SKILL.md"
        mine.parent.mkdir(parents=True)
        mine.write_text("---\nname: bootstrap\n---\nmine\n")
        self.install()
        self.uninstall()
        self.assertEqual(mine.read_text(), "---\nname: bootstrap\n---\nmine\n")
        self.assertFalse((self.skills / "bootstrap" / "tool-mappings.md").exists())

    def test_a_tool_mappings_file_edited_after_install_is_kept(self) -> None:
        self.install()
        edited = self.skills / "bootstrap" / "tool-mappings.md"
        edited.write_text(edited.read_text() + "\nmy note\n")
        r = self.uninstall()
        self.assertTrue(edited.exists())
        self.assertIn("kept", r.stdout)

    def test_restore_brings_back_the_version_install_replaced(self) -> None:
        notes = self.skills / "forms" / "MYNOTES.md"
        notes.parent.mkdir(parents=True)
        (self.skills / "forms" / "SKILL.md").write_text("---\nname: forms\n---\nold\n")
        notes.write_text("my notes")
        self.install()
        self.assertFalse(notes.exists())  # moved to the backup, not lost
        self.assertEqual(len(self.backups(self.skills)), 1)
        r = self.uninstall("--restore")
        self.assertEqual(notes.read_text(), "my notes")
        self.assertIn("restored", r.stdout)
        self.assertFalse((self.skills / "dev-flow").exists())  # had no previous version

    def test_only_the_three_newest_backups_are_kept_and_a_hand_made_one_is_never_touched(self) -> None:
        manual = self.skills.parent / "skills-backup-manual"   # a folder the user made: same prefix, no timestamp
        (manual / "forms").mkdir(parents=True)
        (manual / "forms" / "SKILL.md").write_text("mine")
        self.install()
        for _ in range(4):           # each run backs up the previous install into a new timestamped folder
            time.sleep(1.1)          # the folder name has one-second resolution
            self.install()
        stamped = [b for b in self.backups(self.skills) if b.name != "skills-backup-manual"]
        self.assertEqual(len(stamped), 3)
        self.assertEqual((manual / "forms" / "SKILL.md").read_text(), "mine")
        r = self.uninstall("--restore")
        self.assertIn(stamped[-1].name, r.stdout)   # restores from the newest timestamped backup, not "manual"
        self.assertEqual((manual / "forms" / "SKILL.md").read_text(), "mine")

    def test_without_restore_uninstall_says_where_the_backup_is(self) -> None:
        (self.skills / "forms").mkdir(parents=True)
        (self.skills / "forms" / "SKILL.md").write_text("old")
        self.install()
        r = self.uninstall()
        self.assertIn("--restore", r.stdout)

    def test_a_retired_skill_is_removed_after_backup(self) -> None:
        # linear-scrum became scrum: a stale copy would compete for the same triggers
        old = self.skills / "linear-scrum"
        old.mkdir(parents=True)
        (old / "SKILL.md").write_text("---\nname: linear-scrum\n---\n")
        r = self.install()
        self.assertFalse(old.exists())
        self.assertTrue((self.skills / "scrum" / "SKILL.md").is_file())
        self.assertTrue(any((b / "linear-scrum" / "SKILL.md").is_file() for b in self.backups(self.skills)))
        self.assertIn("linear-scrum", r.stdout)
        self.assertIn("scrum", r.stdout)

    def test_a_retired_bak_inside_the_skills_dir_goes_too(self) -> None:
        # installs before 2026-08-28 left `<name>.bak` inside the skills dir, registered as a duplicate skill
        bak = self.skills / "linear-scrum.bak"
        bak.mkdir(parents=True)
        (bak / "SKILL.md").write_text("---\nname: linear-scrum\n---\n")
        self.install()
        self.assertFalse(bak.exists())

    def test_uninstall_removes_a_retired_name_and_restore_brings_it_back(self) -> None:
        old = self.skills / "linear-scrum"
        old.mkdir(parents=True)
        (old / "SKILL.md").write_text("---\nname: linear-scrum\n---\n")
        self.install()                       # moves linear-scrum into the backup
        (self.skills / "linear-scrum").mkdir()   # a stray copy left by something else
        r = self.uninstall("--restore")
        self.assertIn("linear-scrum", r.stdout)
        self.assertTrue((self.skills / "linear-scrum" / "SKILL.md").is_file())   # the backed-up version, restored

    def test_installing_twice_is_clean(self) -> None:
        self.install()
        self.install()
        self.assertEqual(len([d for d in self.skills.glob("*/SKILL.md")]), SKILL_COUNT)
        self.assertEqual(list(self.skills.glob("*.bak")), [])

    def test_uninstall_twice_is_harmless(self) -> None:
        self.install()
        self.uninstall()
        self.uninstall()

    def test_platform_without_a_value_says_so(self) -> None:
        for script in ("install.sh", "uninstall.sh"):
            with self.subTest(script=script):
                r = self.sh(script, "--platform")
                self.assertEqual(r.returncode, 2)
                self.assertIn("--platform needs a value", r.stdout + r.stderr)


class HostHints(Fixture):
    """The fix a missing Python package gets must work on the Python found: Homebrew's refuses pip (PEP 668)."""

    def fake_host(self, managed: bool) -> dict:
        root = Path(self._tmp.name) / "brewroot"
        bin_ = root / "bin"
        bin_.mkdir(parents=True)
        (bin_ / "python3").write_text(
            "#!/bin/sh\ncase \"$*\" in\n  *'import yaml'*) exit 0;;\n  *'import PIL'*) exit 1;;\n"
            f"  *EXTERNALLY*) {'echo managed' if managed else 'echo'}; exit 0;;\nesac\nexit 0\n")
        (bin_ / "brew").write_text(f"#!/bin/sh\n[ \"$1\" = --prefix ] && echo {root}\nexit 0\n")
        for f in bin_.iterdir():
            f.chmod(0o755)
        return {"PATH": f"{bin_}{os.pathsep}{os.environ['PATH']}"}

    def run_install(self, env_extra: dict) -> str:
        env = {k: v for k, v in os.environ.items() if k not in ("CLAUDE_SKILLS_DIR", "DEV_FLOW_SKILLS_DIR")}
        env.update(HOME=str(self.home), **env_extra)
        r = subprocess.run(["bash", str(REPO / "install.sh")], cwd=REPO, env=env, capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        return r.stdout

    def test_homebrew_python_is_told_to_use_brew(self) -> None:
        out = self.run_install(self.fake_host(managed=True))
        self.assertIn("brew install pillow", out)
        self.assertNotIn("pip3 install pillow", out)

    def test_a_python_that_takes_pip_is_told_pip(self) -> None:
        out = self.run_install(self.fake_host(managed=False))
        self.assertIn("python3 -m pip install pillow", out)


class Codex(Fixture):
    def setUp(self) -> None:
        super().setUp()
        self.skills = self.home / ".codex" / "dev-flow-skills"
        self.agents = self.skills / "AGENTS.md"

    def test_an_existing_agents_md_is_backed_up_before_install_overwrites_it(self) -> None:
        self.skills.mkdir(parents=True)
        self.agents.write_text("my own AGENTS.md")
        self.install("--platform", "codex")
        self.assertNotEqual(self.agents.read_text(), "my own AGENTS.md")
        saved = [b / "AGENTS.md" for b in self.backups(self.skills)]
        self.assertEqual([p.read_text() for p in saved if p.exists()], ["my own AGENTS.md"])
        self.uninstall("--platform", "codex", "--restore")
        self.assertEqual(self.agents.read_text(), "my own AGENTS.md")

    def test_an_agents_md_edited_after_install_is_kept_by_uninstall(self) -> None:
        self.install("--platform", "codex")
        self.agents.write_text(self.agents.read_text() + "\n- my rule\n")
        r = self.uninstall("--platform", "codex")
        self.assertTrue(self.agents.exists())
        self.assertIn("kept", r.stdout)

    def test_an_untouched_bootstrap_is_removed(self) -> None:
        self.install("--platform", "codex")
        self.uninstall("--platform", "codex")
        self.assertFalse(self.agents.exists())
        self.assertEqual(sorted(p.name for p in self.skills.iterdir()), [])

    def test_an_install_from_before_the_manifest_is_still_cleaned_safely(self) -> None:
        # No .dev-flow-installed: files equal to the current templates go, anything else stays.
        self.install("--platform", "codex")
        (self.skills / ".dev-flow-installed").unlink()
        self.uninstall("--platform", "codex")
        self.assertFalse(self.agents.exists())


class Projects(Fixture):
    """--projects re-runs the setup of the projects that already have a dev-flow hook.

    Each project runs its hook from a committed copy, and `check` refuses the next phase while that copy
    differs from the installed skill. Every skill update meant one setup per project by hand (8 on
    2026-10-17). The flag is opt-in, and touches only projects that already have a hook.
    """

    def setUp(self) -> None:
        super().setUp()
        self.skills = self.home / ".claude/skills"
        self.projects = self.home / "projects"
        self.governed = self.projects / "governed"
        (self.governed / ".claude/hooks").mkdir(parents=True)
        (self.governed / ".claude/hooks/registry_intake.py").write_text("# an old copy\n")
        self.plain = self.projects / "plain"
        self.plain.mkdir(parents=True)

    def test_a_stale_hook_is_refreshed(self) -> None:
        r = self.install("--projects", str(self.projects))
        hook = (self.governed / ".claude/hooks/registry_intake.py").read_text()
        self.assertEqual(hook, (self.skills / "registry-intake/scripts/registry_intake.py").read_text())
        self.assertIn("governed: registry-intake ✓", r.stdout)
        self.assertIn("Nothing was committed", r.stdout)

    def test_a_project_without_a_hook_is_not_touched(self) -> None:
        r = self.install("--projects", str(self.projects))
        self.assertEqual(list(self.plain.iterdir()), [])
        self.assertNotIn("plain", r.stdout)

    def test_without_the_flag_no_project_is_touched(self) -> None:
        r = self.install()
        self.assertEqual((self.governed / ".claude/hooks/registry_intake.py").read_text(), "# an old copy\n")
        self.assertNotIn("Refreshing project hooks", r.stdout)

    def test_a_failing_setup_is_named_and_does_not_fail_the_install(self) -> None:
        broken = self.projects / "broken"
        (broken / ".claude/hooks").mkdir(parents=True)
        (broken / ".claude/hooks/registry_intake.py").write_text("# an old copy\n")
        (broken / "vendor/registry").mkdir(parents=True)
        (broken / "vendor/registry/stray.json").write_text("{}")   # in vendor/ but not in the lock: check fails
        r = self.install("--projects", str(self.projects))
        self.assertIn("broken: registry-intake ✗", r.stdout)
        self.assertIn("stray.json", r.stdout)
        self.assertIn("governed: registry-intake ✓", r.stdout)

    def test_a_guard_setup_that_skips_says_so(self) -> None:
        guarded = self.projects / "guarded"
        (guarded / "scripts/guard").mkdir(parents=True)
        (guarded / "scripts/guard/primitives-guard.mjs").write_text("// old\n")
        r = self.install("--projects", str(self.projects))
        # no Next app here, so the guard's setup skips itself (exit 0): that is not a refresh, and must not read as one
        self.assertIn("guarded: primitives-guard skipped (stack.framework=None", r.stdout)
        self.assertEqual((guarded / "scripts/guard/primitives-guard.mjs").read_text(), "// old\n")

    def test_a_project_whose_hook_is_a_symlink_is_skipped(self) -> None:
        # a cloned repo could point its hook path at a file of the user's; setup would overwrite it
        victim = self.home / "precious.txt"
        victim.write_text("mine\n")
        cloned = self.projects / "cloned"
        (cloned / ".claude/hooks").mkdir(parents=True)
        (cloned / ".claude/hooks/registry_intake.py").symlink_to(victim)
        r = self.install("--projects", str(self.projects))
        self.assertEqual(victim.read_text(), "mine\n")
        self.assertIn("cloned: skipped — .claude/hooks/registry_intake.py is a symlink out of the project", r.stdout)
        self.assertIn("governed: registry-intake ✓", r.stdout)

    def test_a_symlink_on_a_file_setup_learned_later_is_caught_too(self) -> None:
        # no list of paths to keep up to date: .prettierignore was not on the first one
        victim = self.home / "precious.txt"
        victim.write_text("mine\n")
        cloned = self.projects / "cloned"
        (cloned / ".claude/hooks").mkdir(parents=True)
        (cloned / ".claude/hooks/registry_intake.py").write_text("# old\n")
        (cloned / ".prettierignore").symlink_to(victim)
        r = self.install("--projects", str(self.projects))
        self.assertEqual(victim.read_text(), "mine\n")
        self.assertIn("cloned: skipped — .prettierignore", r.stdout)

    def test_a_symlinked_project_folder_is_skipped(self) -> None:
        elsewhere = self.home / "elsewhere"
        (elsewhere / ".claude/hooks").mkdir(parents=True)
        (elsewhere / ".claude/hooks/registry_intake.py").write_text("# old\n")
        (self.projects / "linked").symlink_to(elsewhere)
        r = self.install("--projects", str(self.projects))
        self.assertEqual((elsewhere / ".claude/hooks/registry_intake.py").read_text(), "# old\n")
        self.assertIn("linked: skipped — the project folder itself", r.stdout)

    def test_a_chain_of_in_project_links_ending_outside_deep_down_is_caught(self) -> None:
        # .claude -> a/b/c/d, and a/b/c/d/hooks -> outside: the outside link sits four levels down
        victim = self.home / "precious"
        victim.mkdir()
        cloned = self.projects / "cloned"
        deep = cloned / "a/b/c/d"
        deep.mkdir(parents=True)
        (deep / "hooks").symlink_to(victim)
        (cloned / ".claude").symlink_to(deep)
        (victim / "registry_intake.py").write_text("mine\n")
        r = self.install("--projects", str(self.projects))
        self.assertEqual((victim / "registry_intake.py").read_text(), "mine\n")
        self.assertIn("cloned: skipped — a/b/c/d/hooks", r.stdout)

    def test_a_link_into_an_unscanned_folder_is_caught(self) -> None:
        cloned = self.projects / "cloned"
        (cloned / "node_modules/pkg/hooks").mkdir(parents=True)
        (cloned / "node_modules/pkg/hooks/registry_intake.py").write_text("# old\n")
        (cloned / ".claude").symlink_to(cloned / "node_modules/pkg")
        r = self.install("--projects", str(self.projects))
        self.assertIn("cloned: skipped — .claude", r.stdout)

    def test_symlinks_inside_the_project_and_in_node_modules_are_fine(self) -> None:
        (self.governed / "docs").mkdir()
        (self.governed / "README.md").write_text("x")
        (self.governed / "docs/README.md").symlink_to(self.governed / "README.md")
        (self.governed / "node_modules/.bin").mkdir(parents=True)
        (self.governed / "node_modules/.bin/tool").symlink_to(self.home)
        r = self.install("--projects", str(self.projects))
        self.assertIn("governed: registry-intake ✓", r.stdout)

    def test_a_missing_directory_is_refused_before_installing(self) -> None:
        r = self.sh("install.sh", "--projects", str(self.home / "nope"))
        self.assertEqual(r.returncode, 2)
        self.assertIn("not a directory", r.stdout)
        self.assertFalse(self.skills.exists())

    def test_no_project_with_a_hook_says_so(self) -> None:
        r = self.install("--projects", str(self.plain))
        self.assertIn("no project with a dev-flow hook", r.stdout)


if __name__ == "__main__":
    unittest.main()
