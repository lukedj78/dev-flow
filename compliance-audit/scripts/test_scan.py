"""Unit tests for scan.evaluate — the signals→findings mapping.

evaluate() is pure (dict in, list out) so we test the risk logic without a
filesystem. scan() is the I/O layer and is exercised by the smoke test.
"""
import unittest

from scan import evaluate, scan
from pathlib import Path
import tempfile
import os


def base_signals(**overrides):
    """A 'clean' project: no auth, no agent, no web — nothing to flag."""
    s = {
        "has_auth": False, "has_dsar_export": False, "has_dsar_delete": False,
        "has_consent": False, "has_eu_region": False, "has_us_default": False,
        "has_ai_surface": False, "has_ai_disclosure": False, "has_raw_log": False,
        "has_subprocessors_doc": False, "has_retention_doc": False,
        "has_agent": False, "has_memory": False, "has_art9_guard": False,
        "has_manip_guard": False, "is_web": False, "is_mobile": False,
        "has_cookie_analytics_before_consent": False,
    }
    s.update(overrides)
    return s


def ids(findings):
    return {f["id"] for f in findings}


class TestEvaluate(unittest.TestCase):
    def test_empty_project_is_clean(self):
        self.assertEqual(evaluate(base_signals()), [])

    def test_r1_auth_without_dsar_fires(self):
        self.assertIn("R1", ids(evaluate(base_signals(has_auth=True))))

    def test_r1_silenced_when_both_export_and_delete_present(self):
        s = base_signals(has_auth=True, has_dsar_export=True, has_dsar_delete=True)
        self.assertNotIn("R1", ids(evaluate(s)))

    def test_r1_still_fires_with_export_but_no_delete(self):
        s = base_signals(has_auth=True, has_dsar_export=True, has_dsar_delete=False)
        self.assertIn("R1", ids(evaluate(s)))

    def test_r2_web_without_consent_fires(self):
        self.assertIn("R2", ids(evaluate(base_signals(is_web=True))))

    def test_r2_silenced_with_consent(self):
        s = base_signals(is_web=True, has_consent=True)
        self.assertNotIn("R2", ids(evaluate(s)))

    def test_r3_us_default_without_eu_region_fires(self):
        self.assertIn("R3", ids(evaluate(base_signals(has_us_default=True))))

    def test_r3_silenced_when_eu_region_marked(self):
        s = base_signals(has_us_default=True, has_eu_region=True)
        self.assertNotIn("R3", ids(evaluate(s)))

    def test_r5_ai_surface_without_disclosure_fires(self):
        self.assertIn("R5", ids(evaluate(base_signals(has_ai_surface=True))))

    def test_r5_silenced_with_disclosure(self):
        s = base_signals(has_ai_surface=True, has_ai_disclosure=True)
        self.assertNotIn("R5", ids(evaluate(s)))

    def test_r7_raw_log_fires(self):
        self.assertIn("R7", ids(evaluate(base_signals(has_raw_log=True))))

    def test_r8_subprocessors_gate_on_auth_or_agent(self):
        self.assertIn("R8", ids(evaluate(base_signals(has_auth=True))))
        self.assertIn("R8", ids(evaluate(base_signals(has_agent=True))))
        self.assertNotIn("R8", ids(evaluate(base_signals())))  # no processors → no register needed

    def test_r8_silenced_with_register(self):
        s = base_signals(has_auth=True, has_subprocessors_doc=True)
        self.assertNotIn("R8", ids(evaluate(s)))

    def test_r9_agent_special_category_gate(self):
        self.assertIn("R9", ids(evaluate(base_signals(has_agent=True))))
        s = base_signals(has_agent=True, has_art9_guard=True)
        self.assertNotIn("R9", ids(evaluate(s)))

    def test_r10_memory_manipulation_gate(self):
        self.assertIn("R10", ids(evaluate(base_signals(has_memory=True))))
        s = base_signals(has_memory=True, has_manip_guard=True)
        self.assertNotIn("R10", ids(evaluate(s)))

    def test_eve_agent_project_fires_expected_cluster(self):
        # An eve agent with memory, no controls: R1? (no auth) no. R4 R8 R9 R10 yes.
        s = base_signals(has_agent=True, has_memory=True)
        got = ids(evaluate(s))
        self.assertEqual({"R4", "R8", "R9", "R10"}, got)

    def test_severity_and_article_present(self):
        for f in evaluate(base_signals(has_auth=True, is_web=True)):
            self.assertIn(f["severity"], {"H", "M", "L"})
            self.assertTrue(f["article"])


class TestAnalyticsBeforeConsent(unittest.TestCase):
    """R11: a client analytics SDK that sets identifiers before the user has consented. Judged per init file,
    so a consent banner somewhere else in the project does not silence an init that ignores it."""

    INIT = "import posthog from 'posthog-js'\nposthog.init('phc_x', { api_host: '/ph' })\n"

    def signal(self, files: dict) -> bool:
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            for rel, body in files.items():
                (root / rel).parent.mkdir(parents=True, exist_ok=True)
                (root / rel).write_text(body)
            return scan(root)["has_cookie_analytics_before_consent"]

    def test_r11_fires_on_the_signal(self):
        self.assertIn("R11", ids(evaluate(base_signals(has_cookie_analytics_before_consent=True))))
        self.assertNotIn("R11", ids(evaluate(base_signals())))

    def test_an_init_with_cookies_and_no_gate_is_flagged(self):
        self.assertTrue(self.signal({"instrumentation-client.ts": self.INIT}))

    def test_cookieless_mode_is_not_flagged(self):
        init = self.INIT.replace("api_host: '/ph'", "api_host: '/ph', cookieless_mode: 'always'")
        self.assertFalse(self.signal({"instrumentation-client.ts": init}))

    def test_an_init_behind_the_consent_gate_is_not_flagged(self):
        init = "import { hasConsent } from '@/lib/consent'\n" + self.INIT
        self.assertFalse(self.signal({"instrumentation-client.ts": init}))

    def test_a_comment_mentioning_consent_does_not_silence_the_init(self):
        for comment in ("// TODO: consent\n", "/* ask for consent later */\n", "{/* consent banner goes here */}\n"):
            with self.subTest(comment=comment):
                self.assertTrue(self.signal({"instrumentation-client.ts": comment + self.INIT}))

    def test_a_banner_elsewhere_does_not_silence_the_init(self):
        self.assertTrue(self.signal({"instrumentation-client.ts": self.INIT,
                                     "components/cookie-banner.tsx": "export function CookieConsent() {}\n"}))

    def test_the_expo_provider_and_the_node_client_are_judged_too(self):
        provider = 'import { PostHogProvider } from "posthog-react-native"\n<PostHogProvider apiKey={k} options={{ host: "https://eu.i.posthog.com" }} />\n'
        self.assertTrue(self.signal({"app/_layout.tsx": provider}))
        gated = provider.replace("options={{", "options={{ defaultOptIn: false, ").replace("<PostHogProvider", "// consent first\n<PostHogProvider")
        self.assertFalse(self.signal({"app/_layout.tsx": gated}))
        rn_client = 'import PostHog from "posthog-react-native"\nexport const ph = new PostHog(k, { host: h })\n'
        self.assertTrue(self.signal({"lib/posthog.ts": rn_client}))

    def test_the_server_sdk_is_not_a_device_identifier(self):
        server = 'import { PostHog } from "posthog-node"\nconst ph = new PostHog(k, { host: h })\n'
        self.assertFalse(self.signal({"lib/analytics/track.ts": server}))

    def test_vercel_analytics_and_openpanel_are_not_flagged(self):
        self.assertFalse(self.signal({"app/layout.tsx": "import { Analytics } from '@vercel/analytics/next'\n<Analytics />\n"}))
        self.assertFalse(self.signal({"app/layout.tsx": "import { OpenPanelComponent } from '@openpanel/nextjs'\n"}))


class TestScanSmoke(unittest.TestCase):
    def test_scan_detects_auth_and_missing_dsar(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "meta.json").write_text('{"framework":"next"}')
            (root / "auth.ts").write_text('import { betterAuth } from "better-auth"')
            signals = scan(root)
            self.assertTrue(signals["has_auth"])
            self.assertTrue(signals["is_web"])
            self.assertFalse(signals["has_dsar_delete"])
            self.assertIn("R1", ids(evaluate(signals)))

    def test_scan_skips_node_modules(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            nm = root / "node_modules" / "pkg"
            nm.mkdir(parents=True)
            (nm / "index.ts").write_text('betterAuth()')
            self.assertFalse(scan(root)["has_auth"])


if __name__ == "__main__":
    unittest.main()
