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


if __name__ == "__main__":
    unittest.main()
