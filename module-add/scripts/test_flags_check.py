"""flags_check.py: the three things a flags install gets wrong silently.

The cases worth a test are the ones that look fine and are not: a `FLAGS_SECRET` of the wrong length
(the SDK throws, and `precompute` stops working, which reads as "the page is just dynamic now"); a
LaunchDarkly install missing `EXPERIMENTATION_CONFIG`, whose name contains no hint of what it is for;
and a flag declared without `defaultValue`, which decides what every user sees during an outage.

Plus the invariant every checker in this suite shares: what it cannot see is `not checked`, never ok.

    cd module-add/scripts && python3 -m unittest test_flags_check -v
"""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from base64 import urlsafe_b64encode
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import flags_check as fc  # noqa: E402

GOOD_SECRET = urlsafe_b64encode(b"x" * 32).decode().rstrip("=")

DECL = """\
import { flag } from "flags/next";
import { ldAdapter, type LDContext } from "@flags-sdk/launchdarkly";

export const newCheckout = flag<boolean, LDContext>({
  key: "us-7-new-checkout",
  defaultValue: false,
  adapter: ldAdapter.variation(),
});
"""


class Project(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        (self.root / ".workflow").mkdir()
        self.write("package.json", json.dumps({
            "name": "demo",
            "dependencies": {"next": "16.4.5", "flags": "4.4.0", "@flags-sdk/launchdarkly": "1.1.1"},
        }))
        (self.root / "app").mkdir()
        self.write("app/page.tsx", "export default () => null\n")
        self.meta({"stack": {"framework": "next", "flags": "launchdarkly"}})
        self.write(".env.example", "\n".join([
            f"FLAGS_SECRET={GOOD_SECRET}",
            "EXPERIMENTATION_CONFIG=https://edge-config.vercel.com/ecfg_x?token=y",
            "LAUNCHDARKLY_CLIENT_SIDE_ID=65abc",
            "LAUNCHDARKLY_PROJECT_SLUG=demo",
        ]) + "\n")
        self.write("lib/flags.ts", DECL)
        self.write("docs/compliance/subprocessors.md", "| LaunchDarkly | feature flags | US |\n")

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def write(self, rel: str, text: str) -> None:
        p = self.root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text)

    def meta(self, data: dict) -> None:
        (self.root / ".workflow" / "meta.json").write_text(json.dumps(data))

    def run_check(self, provider: str | None = None) -> dict[str, fc.Finding]:
        return {f.check: f for f in fc.check(self.root, provider)}

    def status(self, check: str, provider: str | None = None) -> str:
        return self.run_check(provider)[check].status


class Wired(Project):
    def test_a_complete_install_is_clean(self) -> None:
        found = [f for f in fc.check(self.root) if f.status == "found"]
        self.assertEqual(found, [], [f.detail for f in found])

    def test_the_render_says_wired(self) -> None:
        self.assertIn("wired", fc.render(fc.check(self.root)))

    def test_exit_zero_when_clean(self) -> None:
        self.assertEqual(fc.main([str(self.root)]), 0)


class Secret(Project):
    def test_a_missing_secret_is_a_finding(self) -> None:
        self.write(".env.example", "LAUNCHDARKLY_CLIENT_SIDE_ID=x\n")
        self.assertEqual(self.status("flags-secret"), "found")

    def test_a_short_secret_is_a_finding_because_the_sdk_throws(self) -> None:
        short = urlsafe_b64encode(b"x" * 16).decode().rstrip("=")
        self.write(".env.example", f"FLAGS_SECRET={short}\n")
        f = self.run_check()["flags-secret"]
        self.assertEqual(f.status, "found")
        self.assertIn("32", f.detail)

    def test_a_non_base64_secret_is_a_finding(self) -> None:
        self.write(".env.example", "FLAGS_SECRET=not a secret at all!!\n")
        self.assertEqual(self.status("flags-secret"), "found")

    def test_a_placeholder_is_not_checked_never_ok(self) -> None:
        self.write(".env.example", "FLAGS_SECRET=\n")
        self.assertEqual(self.status("flags-secret"), "not checked")

    def test_an_interpolated_value_is_not_checked(self) -> None:
        self.write(".env.example", "FLAGS_SECRET=$FLAGS_SECRET\n")
        self.assertEqual(self.status("flags-secret"), "not checked")

    def test_not_checked_makes_the_render_say_so(self) -> None:
        self.write(".env.example", "FLAGS_SECRET=\n")
        self.assertIn("never a pass", fc.render(fc.check(self.root)))


class ProviderEnv(Project):
    def test_the_launchdarkly_variable_nobody_guesses_is_checked(self) -> None:
        self.write(".env.example", "\n".join([
            f"FLAGS_SECRET={GOOD_SECRET}",
            "LAUNCHDARKLY_CLIENT_SIDE_ID=65abc",
            "LAUNCHDARKLY_PROJECT_SLUG=demo",
        ]) + "\n")
        f = self.run_check()["env:EXPERIMENTATION_CONFIG"]
        self.assertEqual(f.status, "found")
        self.assertIn("assertEnv", f.detail)

    def test_edge_config_needs_only_its_own_variable(self) -> None:
        self.meta({"stack": {"framework": "next", "flags": "edge-config"}})
        self.write("package.json", json.dumps({
            "dependencies": {"next": "16.4.5", "flags": "4.4.0", "@flags-sdk/edge-config": "0.2.0"}}))
        self.write(".env.example", f"FLAGS_SECRET={GOOD_SECRET}\nEDGE_CONFIG=https://x\n")
        found = [f.check for f in fc.check(self.root) if f.status == "found"]
        self.assertEqual(found, [], found)

    def test_edge_config_needs_no_subprocessor_entry(self) -> None:
        self.meta({"stack": {"framework": "next", "flags": "edge-config"}})
        self.assertEqual(self.status("subprocessor"), "not applicable")

    def test_an_unknown_provider_is_not_checked_rather_than_passed(self) -> None:
        self.meta({"stack": {"framework": "next", "flags": "homegrown"}})
        self.assertEqual(self.status("provider"), "not checked")

    def test_the_provider_can_come_from_the_release_block(self) -> None:
        self.meta({"stack": {"framework": "next"}, "release": {"flag_provider": "launchdarkly"}})
        self.assertEqual(self.run_check()["provider"].detail, "provider: launchdarkly")

    def test_no_provider_anywhere_is_a_finding(self) -> None:
        self.meta({"stack": {"framework": "next"}})
        self.assertEqual(self.status("provider"), "found")


class Packages(Project):
    def test_a_missing_flags_package_is_a_finding(self) -> None:
        self.write("package.json", json.dumps({"dependencies": {"next": "16.4.5"}}))
        self.assertEqual(self.status("package"), "found")

    def test_the_adapter_is_a_separate_dependency(self) -> None:
        self.write("package.json", json.dumps({"dependencies": {"next": "16.4.5", "flags": "4.4.0"}}))
        f = self.run_check()["adapter-package"]
        self.assertEqual(f.status, "found")
        self.assertIn("ships no adapters", f.detail)


class Declaration(Project):
    def test_a_missing_declaration_file_is_a_finding(self) -> None:
        (self.root / "lib" / "flags.ts").unlink()
        self.assertEqual(self.status("declaration-file"), "found")

    def test_a_file_with_no_flag_is_a_finding(self) -> None:
        self.write("lib/flags.ts", "export const nothing = 1;\n")
        self.assertEqual(self.status("declaration-file"), "found")

    def test_a_flag_without_an_explicit_default_is_a_finding(self) -> None:
        self.write("lib/flags.ts", DECL.replace("  defaultValue: false,\n", ""))
        f = self.run_check()["default-value"]
        self.assertEqual(f.status, "found")
        self.assertIn("provider is unreachable", f.detail)

    def test_a_flag_declared_in_a_client_component_is_a_finding(self) -> None:
        self.write("app/bad.tsx", '"use client";\n' + DECL)
        f = self.run_check()["client-declaration"]
        self.assertEqual(f.status, "found")
        self.assertIn("bundle", f.detail)


class Subprocessor(Project):
    def test_a_hosted_provider_missing_from_the_register_is_a_finding(self) -> None:
        self.write("docs/compliance/subprocessors.md", "| Resend | email | EU |\n")
        self.assertEqual(self.status("subprocessor"), "found")

    def test_no_register_at_all_is_a_finding(self) -> None:
        (self.root / "docs" / "compliance" / "subprocessors.md").unlink()
        self.assertEqual(self.status("subprocessor"), "found")


class NotAWebProject(unittest.TestCase):
    def test_a_project_with_no_web_surface_is_not_applicable(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".workflow").mkdir()
            (root / ".workflow" / "meta.json").write_text(json.dumps({"stack": {"framework": "expo-rn"}}))
            (root / "package.json").write_text(json.dumps({"dependencies": {"expo": "58"}}))
            (root / "app.json").write_text('{"expo": {}}')
            findings = fc.check(root)
            self.assertEqual([f.status for f in findings], ["not applicable"])
            self.assertEqual(fc.main([str(root)]), 0)


class EnvNamesAreTheShippedOnes(unittest.TestCase):
    """These strings are the contract with the adapters; a typo here makes the checker lie."""

    def test_launchdarkly_reads_three_variables(self) -> None:
        self.assertEqual(fc.PROVIDER_ENV["launchdarkly"],
                         ("EXPERIMENTATION_CONFIG", "LAUNCHDARKLY_CLIENT_SIDE_ID", "LAUNCHDARKLY_PROJECT_SLUG"))

    def test_every_provider_maps_to_its_package(self) -> None:
        for p in fc.PROVIDER_ENV:
            self.assertEqual(fc.PROVIDER_PACKAGE[p], f"@flags-sdk/{p}")


if __name__ == "__main__":
    unittest.main()
