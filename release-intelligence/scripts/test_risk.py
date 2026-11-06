"""risk.py: the deterministic floor is a floor, and what it cannot see is never a pass.

Each test builds a real git repository, because the signals are read from `git diff` and a mocked
diff would test the mock. The cases that matter are the asymmetries: a destructive migration must
reach `critical` from one `+` line, an unreadable diff must appear in `not_checked` rather than
resolving to `low`, and a pre-existing `DROP TABLE` that this release does not add must NOT raise it.
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import risk  # noqa: E402


def git(root: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=root, check=True,
                   capture_output=True, text=True)


class Repo(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        git(self.root, "init", "-q", "-b", "main")
        git(self.root, "config", "user.email", "t@example.com")
        git(self.root, "config", "user.name", "t")
        self.write("README.md", "start\n")
        self.commit("base")
        git(self.root, "checkout", "-q", "-b", "feature")

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def write(self, rel: str, text: str) -> None:
        p = self.root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text)

    def meta(self, block: dict) -> None:
        self.write(".workflow/meta.json", json.dumps(block))

    def commit(self, msg: str) -> None:
        git(self.root, "add", "-A")
        git(self.root, "commit", "-q", "-m", msg)

    def assess(self, **kw):
        return risk.assess(self.root, base=kw.pop("base", "main"), **kw)


class Levels(Repo):
    def test_a_copy_change_is_low(self) -> None:
        self.write("app/page.tsx", "export default () => <p>ciao</p>\n")
        self.commit("copy")
        a = self.assess()
        self.assertEqual(a.level, "low")
        self.assertTrue(a.reversible)

    def test_a_route_handler_is_medium(self) -> None:
        self.write("app/api/items/route.ts", "export async function GET() {}\n")
        self.commit("api")
        a = self.assess()
        self.assertEqual(a.level, "medium")
        self.assertIn("api", [s.id for s in a.signals])

    def test_auth_is_high(self) -> None:
        self.write("lib/auth.ts", "export const auth = {}\n")
        self.commit("auth")
        self.assertEqual(self.assess().level, "high")

    def test_the_proxy_is_high_because_it_runs_before_every_request(self) -> None:
        self.write("proxy.ts", "export function proxy() {}\n")
        self.commit("proxy")
        self.assertEqual(self.assess().level, "high")

    def test_an_additive_migration_is_critical_but_not_destructive(self) -> None:
        self.write("drizzle/0001_add.sql", "ALTER TABLE users ADD COLUMN nickname text;\n")
        self.commit("migration")
        a = self.assess()
        self.assertEqual(a.level, "critical")
        self.assertFalse(a.destructive_migration)
        self.assertFalse(a.reversible)  # the code rolls back, the schema does not

    def test_a_dropped_column_is_a_destructive_migration(self) -> None:
        self.write("drizzle/0002_drop.sql", "ALTER TABLE users DROP COLUMN nickname;\n")
        self.commit("drop")
        a = self.assess()
        self.assertEqual(a.level, "critical")
        self.assertTrue(a.destructive_migration)
        ids = [s.id for s in a.signals]
        self.assertIn("destructive_migration", ids)

    def test_add_column_not_null_without_default_is_caught(self) -> None:
        """Postgres rejects it on a non-empty table: a failed deploy, and it is this release's fault."""
        self.write("drizzle/0003.sql", "ALTER TABLE users ADD COLUMN tier text NOT NULL;\n")
        self.commit("not null")
        self.assertTrue(self.assess().destructive_migration)

    def test_add_column_with_a_default_is_not_flagged(self) -> None:
        self.write("drizzle/0004.sql", "ALTER TABLE users ADD COLUMN tier text NOT NULL DEFAULT 'free';\n")
        self.commit("default")
        a = self.assess()
        self.assertFalse(a.destructive_migration)
        self.assertEqual(a.level, "critical")  # still a migration

    def test_a_pre_existing_drop_is_not_this_releases_risk(self) -> None:
        """Only the `+` lines of the diff count, or every release after a destructive one inherits it."""
        self.write("drizzle/0001_old.sql", "DROP TABLE legacy;\n")
        git(self.root, "checkout", "-q", "main")
        self.commit("old migration on main")
        git(self.root, "checkout", "-q", "feature")
        git(self.root, "merge", "-q", "main")
        self.write("app/page.tsx", "x\n")
        self.commit("copy only")
        a = self.assess()
        self.assertFalse(a.destructive_migration)
        self.assertEqual(a.level, "low")


class Size(Repo):
    def test_a_large_diff_reaches_the_medium_band(self) -> None:
        for i in range(16):
            self.write(f"components/site/c{i}.tsx", "export const C = () => null\n")
        self.commit("many")
        a = self.assess()
        self.assertEqual(a.level, "medium")
        self.assertIn("size", [s.id for s in a.signals])

    def test_the_bands_are_configurable(self) -> None:
        for i in range(16):
            self.write(f"components/site/c{i}.tsx", "export const C = () => null\n")
        self.meta({"release": {"risk_policy": {"size_bands": {"medium": 100}}}})
        self.commit("many")
        self.assertEqual(self.assess().level, "low")


class Policy(Repo):
    def test_a_project_can_relevel_a_signal(self) -> None:
        self.write("app/api/items/route.ts", "export async function GET() {}\n")
        self.meta({"release": {"risk_policy": {"paths": {"api": "critical"}}}})
        self.commit("api")
        self.assertEqual(self.assess().level, "critical")

    def test_a_project_can_drop_a_signal_with_null(self) -> None:
        self.write("app/api/items/route.ts", "export async function GET() {}\n")
        self.meta({"release": {"risk_policy": {"paths": {"api": None}}}})
        self.commit("api")
        self.assertEqual(self.assess().level, "low")

    def test_an_invalid_level_in_the_policy_keeps_the_default(self) -> None:
        """A typo must not silence a signal — that is the whole failure mode of a configurable table."""
        self.write("lib/auth.ts", "export const auth = {}\n")
        self.meta({"release": {"risk_policy": {"paths": {"auth": "harmless"}}}})
        self.commit("auth")
        self.assertEqual(self.assess().level, "high")


class MetaEvidence(Repo):
    def test_open_security_findings_raise_the_release(self) -> None:
        self.write("app/page.tsx", "x\n")
        self.meta({"security": {"findings": {"open": 2}, "tools": {"deps": "osv-scanner"}},
                   "verification": {"proven_at": "2026-11-01T00:00:00Z"}})
        self.commit("copy with findings")
        a = self.assess()
        self.assertEqual(a.level, "high")
        self.assertIn("security_findings", [s.id for s in a.signals])

    def test_a_scanner_that_did_not_run_is_unchecked_not_clean(self) -> None:
        self.write("app/page.tsx", "x\n")
        self.meta({"security": {"findings": {"open": 0}, "tools": {"secrets": "not-run"}},
                   "verification": {"proven_at": "2026-11-01T00:00:00Z"}})
        self.commit("copy")
        a = self.assess()
        self.assertEqual(a.level, "low")
        self.assertTrue(any("secrets" in u for u in a.not_checked), a.not_checked)

    def test_no_security_block_at_all_is_reported_as_unchecked(self) -> None:
        self.write("app/page.tsx", "x\n")
        self.commit("copy")
        a = self.assess()
        self.assertTrue(any("app-security has never run" in u for u in a.not_checked), a.not_checked)

    def test_a_missing_verification_manual_is_unchecked(self) -> None:
        self.write("app/page.tsx", "x\n")
        self.commit("copy")
        self.assertTrue(any("verification" in u for u in self.assess().not_checked))

    def test_spec_review_level_three_raises_to_medium(self) -> None:
        self.write("app/page.tsx", "x\n")
        self.meta({"spec_review": {"level": 3},
                   "security": {"findings": {"open": 0}, "tools": {"deps": "osv-scanner"}},
                   "verification": {"proven_at": "2026-11-01T00:00:00Z"}})
        self.commit("copy")
        self.assertEqual(self.assess().level, "medium")


class Blindness(Repo):
    def test_an_unresolvable_base_is_reported_not_silently_low(self) -> None:
        """A release classified `low` because nothing could be read is the failure this guards."""
        self.write("drizzle/0001.sql", "DROP TABLE users;\n")
        self.commit("drop")
        a = risk.assess(self.root, base=None) if risk.detect_base(self.root) is None else None
        if a is None:  # `main` exists in this fixture, so force the no-base path explicitly
            a = risk.assess(self.root, base="does-not-exist")
        self.assertTrue(a.not_checked, "a diff that could not be read must say so")

    def test_worse_treats_an_unknown_level_as_low(self) -> None:
        self.assertEqual(risk.worse("typo", "medium"), "medium")
        self.assertEqual(risk.worse("typo", "typo"), "low")

    def test_render_always_states_that_the_level_is_a_floor(self) -> None:
        self.write("app/page.tsx", "x\n")
        self.commit("copy")
        self.assertIn("FLOOR", risk.render(self.assess()))


if __name__ == "__main__":
    unittest.main()
