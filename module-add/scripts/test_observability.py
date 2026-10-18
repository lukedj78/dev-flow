"""Tests for observability_check.py and fake_ingest.py."""

from __future__ import annotations

import gzip
import io
import json
import socket
import sys
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from contextlib import redirect_stdout
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fake_ingest as fi  # noqa: E402
import observability_check as oc  # noqa: E402

OPTIONS = """import type { BrowserOptions } from "@sentry/nextjs"
export const options = {
  dsn: "https://abc@o1.ingest.de.sentry.io/2",
  release: process.env.VERCEL_GIT_COMMIT_SHA,
  environment: process.env.VERCEL_ENV,
  sendDefaultPii: false,
  beforeSend: scrub,
}
"""


class Fixture(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def write(self, rel: str, text: str = "") -> None:
        p = self.root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")

    def web(self) -> None:
        self.write("package.json", json.dumps({"dependencies": {"next": "16.4.1", "@sentry/nextjs": "11.8.0"}}))
        self.write("app/page.tsx", "export default function P() { return null }\n")

    def complete_errors(self) -> None:
        self.web()
        self.write("lib/observability/options.ts", OPTIONS)
        self.write("instrumentation.ts", 'import * as Sentry from "@sentry/nextjs"\nexport async function register() {\n'
                   '  await import("./sentry.server.config")\n}\nexport const onRequestError = Sentry.captureRequestError\n')
        self.write("instrumentation-client.ts", 'import * as Sentry from "@sentry/nextjs"\nimport { options } from "./lib/observability/options"\nSentry.init(options)\n')
        self.write("app/global-error.tsx", '"use client"\nimport * as Sentry from "@sentry/nextjs"\nexport default function G({ error }) {\n  Sentry.captureException(error)\n}\n')
        self.write("app/error.tsx", '"use client"\nimport * as Sentry from "@sentry/nextjs"\nexport default function E({ error }) {\n  Sentry.captureException(error)\n}\n')

    def found(self, meta: dict | None = None, all_levels: bool = False) -> list[str]:
        meta = meta if meta is not None else {"stack": {"observability": ["errors"], "data_residency": "eu"}}
        return [f.detail for f in oc.check(self.root, meta, all_levels) if f.status == "found"]

    def statuses(self, meta: dict, all_levels: bool = False) -> dict:
        out: dict = {}
        for f in oc.check(self.root, meta, all_levels):
            out.setdefault(f.level, set()).add(f.status)
        return out


class ErrorsLevel(Fixture):
    def test_complete_errors_level_passes(self) -> None:
        self.complete_errors()
        self.assertEqual(self.found(), [])

    def test_each_missing_piece_is_found(self) -> None:
        cases = {
            "onRequestError": lambda: self.write("instrumentation.ts", "export async function register() {}\n"),
            "instrumentation-client": lambda: (self.root / "instrumentation-client.ts").unlink(),
            "global-error": lambda: (self.root / "app/global-error.tsx").unlink(),
            "error.tsx": lambda: self.write("app/error.tsx", '"use client"\nexport default function E({ error }) {\n  console.error(error)\n}\n'),
            "release": lambda: self.write("lib/observability/options.ts", OPTIONS.replace("  release: process.env.VERCEL_GIT_COMMIT_SHA,\n", "")),
        }
        for needle, damage in cases.items():
            with self.subTest(needle):
                self.complete_errors()
                damage()
                self.assertTrue(any(needle in d for d in self.found()), (needle, self.found()))

    def test_existing_instrumentation_is_kept(self) -> None:
        # Review Focus 1: an instrumentation.ts that already registers @vercel/otel or eve keeps doing so
        self.complete_errors()
        self.write("instrumentation.ts", 'import { registerOTel } from "@vercel/otel"\nimport * as Sentry from "@sentry/nextjs"\n'
                   'export async function register() {\n  registerOTel({ serviceName: "app" })\n  await import("./sentry.server.config")\n}\n'
                   "export const onRequestError = Sentry.captureRequestError\n")
        self.assertEqual(self.found(), [])

    def test_us_dsn_in_an_eu_project_is_found(self) -> None:
        self.complete_errors()
        self.write("lib/observability/options.ts", OPTIONS.replace("o1.ingest.de.sentry.io", "o1.ingest.us.sentry.io"))
        self.assertTrue(any("region" in d for d in self.found()), self.found())
        self.write("lib/observability/options.ts", OPTIONS.replace("o1.ingest.de.sentry.io", "o1.ingest.sentry.io"))
        self.assertTrue(any("region" in d for d in self.found()), self.found())

    def test_dsn_from_env_is_read_or_not_checked(self) -> None:
        # Review Focus 2: the DSN is a variable; its value may be in .env.example, or nowhere
        self.complete_errors()
        self.write("lib/observability/options.ts", OPTIONS.replace('"https://abc@o1.ingest.de.sentry.io/2"', "process.env.NEXT_PUBLIC_SENTRY_DSN"))
        self.assertIn("not checked", self.statuses({"stack": {"observability": ["errors"], "data_residency": "eu"}})["errors"])
        self.write(".env.example", "NEXT_PUBLIC_SENTRY_DSN=https://abc@o1.ingest.us.sentry.io/2\n")
        self.assertTrue(any("region" in d for d in self.found()), self.found())
        self.write(".env.example", "NEXT_PUBLIC_SENTRY_DSN=https://abc@o1.ingest.de.sentry.io/2\n")
        self.assertEqual(self.found(), [])

    def test_glitchtip_host_is_accepted_when_declared(self) -> None:
        self.complete_errors()
        self.write("lib/observability/options.ts", OPTIONS.replace("o1.ingest.de.sentry.io", "errors.example.eu"))
        meta = {"stack": {"observability": ["errors"], "data_residency": "eu-sovereign",
                          "observability_provider": {"errors": "glitchtip"}}}
        self.assertEqual(self.found(meta), [])

    def test_send_default_pii_true_is_found(self) -> None:
        self.complete_errors()
        self.write("lib/observability/options.ts", OPTIONS.replace("sendDefaultPii: false", "sendDefaultPii: true"))
        self.assertTrue(any("sendDefaultPii" in d for d in self.found()), self.found())

    def test_replay_integration_is_found(self) -> None:
        self.complete_errors()
        self.write("instrumentation-client.ts", 'import * as Sentry from "@sentry/nextjs"\n'
                   "Sentry.init({ ...options, integrations: [Sentry.replayIntegration()] })\n")
        self.assertTrue(any("Replay" in d for d in self.found()), self.found())

    def test_pii_setting_not_visible(self) -> None:
        # Review Focus 3: options come through a spread and no literal sendDefaultPii exists anywhere
        self.complete_errors()
        self.write("lib/observability/options.ts", OPTIONS.replace("  sendDefaultPii: false,\n", "  ...shared,\n"))
        self.assertIn("not checked", self.statuses({"stack": {"observability": ["errors"], "data_residency": "eu"}})["errors"])

    # The three below came from the real run on a copy of fit-coach (Task 5).
    def test_error_boundary_under_a_locale_segment_counts(self) -> None:
        self.complete_errors()
        text = (self.root / "app/error.tsx").read_text(encoding="utf-8")
        (self.root / "app/error.tsx").unlink()
        self.write("app/[locale]/error.tsx", text)
        self.assertEqual(self.found(), [])
        self.write("app/[locale]/error.tsx", '"use client"\nexport default function E({ error }) {\n  console.error(error)\n}\n')
        self.assertTrue(any("error.tsx" in d for d in self.found()), self.found())

    def test_with_sentry_config_from_the_package_root_is_found(self) -> None:
        # @sentry/nextjs 11 exports withSentryConfig from "@sentry/nextjs/config" only: the root import fails the build
        self.complete_errors()
        self.write("next.config.ts", 'import { withSentryConfig } from "@sentry/nextjs"\nexport default withSentryConfig({}, {})\n')
        self.assertTrue(any("@sentry/nextjs/config" in d for d in self.found()), self.found())
        self.write("next.config.ts", 'import { withSentryConfig } from "@sentry/nextjs/config"\nexport default withSentryConfig({}, {})\n')
        self.assertEqual(self.found(), [])

    def test_a_csp_that_blocks_the_dsn_host_is_found(self) -> None:
        self.complete_errors()
        csp = 'export const headers = ["default-src \'self\'", "connect-src \'self\' {}", "frame-ancestors \'none\'"]\n'
        self.write("next.config.ts", csp.format("https://api.example.com"))
        self.assertTrue(any("connect-src" in d for d in self.found()), self.found())
        for allowed in ("https:", "https://*.ingest.de.sentry.io", "https://o1.ingest.de.sentry.io"):
            self.write("next.config.ts", csp.format(allowed))
            self.assertEqual(self.found(), [], allowed)
        # a tunnel posts to the app itself, so 'self' is enough
        self.write("next.config.ts", csp.format("https://api.example.com") + 'export const s = { tunnelRoute: "/monitoring" }\n')
        self.assertEqual(self.found(), [])

    def test_a_csp_in_a_template_literal_is_read_up_to_the_interpolation(self) -> None:
        self.complete_errors()
        self.write("next.config.ts", 'const h = [`connect-src \'self\' https:${dev ? " http://127.0.0.1:9010" : ""}`]\n')
        self.assertEqual(self.statuses({"stack": {"observability": ["errors"], "data_residency": "eu"}})["errors"], {"ok"})


class OtherLevels(Fixture):
    def test_logs_level_needs_logger_and_request_id(self) -> None:
        self.web()
        meta = {"stack": {"observability": ["logs"]}}
        found = self.found(meta)
        self.assertTrue(any("lib/log.ts" in d for d in found), found)
        self.write("lib/log.ts", "export const log = { info() {} }\n")
        self.assertTrue(any("x-request-id" in d for d in self.found(meta)), self.found(meta))
        self.write("proxy.ts", 'export function proxy(req) { req.headers.set("x-request-id", crypto.randomUUID()) }\n')
        self.assertEqual(self.found(meta), [])

    def test_uptime_level_needs_health_route(self) -> None:
        self.web()
        meta = {"stack": {"observability": ["uptime"]}}
        self.assertTrue(any("api/health" in d for d in self.found(meta)), self.found(meta))
        self.write("app/api/health/route.ts", "export async function GET() { return Response.json({ ok: true }) }\n")
        self.assertEqual(self.found(meta), [])

    def test_all_flag_checks_every_level(self) -> None:
        self.complete_errors()
        self.assertEqual(set(self.statuses({"stack": {}}, all_levels=True)), {"errors", "logs", "uptime"})

    def test_expo_project_is_not_applicable(self) -> None:
        # Review Focus 5
        self.write("package.json", json.dumps({"dependencies": {"expo": "58.0.0"}}))
        self.write("app.json", '{"expo": {}}')
        self.write("app/index.tsx", "")
        findings = oc.check(self.root, {"stack": {"observability": ["errors"]}})
        self.assertTrue(all(f.status == "not applicable" for f in findings), findings)
        self.assertTrue(any("rn-module-add observability" in f.detail for f in findings), findings)

    def test_cli_exit_code(self) -> None:
        self.web()
        self.write(".workflow/meta.json", json.dumps({"stack": {"observability": ["uptime"]}}))
        with redirect_stdout(io.StringIO()):
            self.assertEqual(oc.main([str(self.root)]), 1)
        self.write("app/api/health/route.ts", "export async function GET() {}\n")
        with redirect_stdout(io.StringIO()):
            self.assertEqual(oc.main([str(self.root)]), 0)


def envelope(event: dict) -> bytes:
    payload = json.dumps(event).encode()
    return b"\n".join([json.dumps({"event_id": event["event_id"]}).encode(),
                       json.dumps({"type": "event", "length": len(payload)}).encode(), payload])


class FakeIngest(Fixture):
    EVENT = {"event_id": "a" * 32, "release": "abc123", "level": "error",
             "exception": {"values": [{"type": "Error", "value": "boom"}]}}

    def test_parse_envelope_plain_and_gzip(self) -> None:
        # Review Focus 4: the Node SDK gzips envelopes
        self.assertEqual(fi.parse_envelope(envelope(self.EVENT))[0]["release"], "abc123")
        self.assertEqual(fi.parse_envelope(gzip.decompress(gzip.compress(envelope(self.EVENT))))[0]["level"], "error")
        self.assertEqual(fi.decode(gzip.compress(envelope(self.EVENT)), "gzip"), envelope(self.EVENT))

    def test_fake_ingest_records_and_summarises(self) -> None:
        with socket.socket() as s:
            s.bind(("127.0.0.1", 0))
            port = s.getsockname()[1]
        out = self.root / "events"
        server = fi.make_server(port, out)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        try:
            body = gzip.compress(envelope(self.EVENT))
            req = urllib.request.Request(f"http://127.0.0.1:{port}/api/1/envelope/", data=body, method="POST",
                                         headers={"Content-Encoding": "gzip", "Content-Type": "application/x-sentry-envelope"})
            self.assertEqual(urllib.request.urlopen(req, timeout=5).status, 200)
        finally:
            server.shutdown()
            server.server_close()
        self.assertEqual(len(list(out.glob("*.json"))), 1)
        s = fi.summary(out)
        self.assertEqual(s["events"], 1)
        self.assertEqual(s["releases"], ["abc123"])
        self.assertFalse(s["emails"])
        self.assertFalse(s["authorization"])

    def test_summary_flags_personal_data(self) -> None:
        out = self.root / "events"
        out.mkdir()
        leaky = dict(self.EVENT, user={"email": "anna@example.com"}, request={"headers": {"Authorization": "Bearer x"}})
        (out / "1.json").write_text(json.dumps(leaky), encoding="utf-8")
        s = fi.summary(out)
        self.assertTrue(s["emails"])
        self.assertTrue(s["authorization"])


if __name__ == "__main__":
    unittest.main()


class IngestSafety(Fixture):
    """Security review of 2026-10-18: the event_id came from the request and named the file (path traversal), and
    any web page could post to the local server."""

    def serve(self):
        with socket.socket() as s:
            s.bind(("127.0.0.1", 0))
            port = s.getsockname()[1]
        out = self.root / "events"
        server = fi.make_server(port, out)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        return port, out

    def post(self, port: int, body: bytes, origin: str | None = None) -> int:
        headers = {"Content-Type": "application/x-sentry-envelope"}
        if origin:
            headers["Origin"] = origin
        req = urllib.request.Request(f"http://127.0.0.1:{port}/api/1/envelope/", data=body, method="POST", headers=headers)
        try:
            return urllib.request.urlopen(req, timeout=5).status
        except urllib.error.HTTPError as e:
            return e.code

    def test_a_traversal_event_id_stays_inside(self) -> None:
        port, out = self.serve()
        evil = dict(FakeIngest.EVENT, event_id="../../escaped")
        self.assertEqual(self.post(port, envelope(evil)), 200)
        self.assertFalse((self.root / "escaped.json").exists())
        self.assertFalse((self.root.parent / "escaped.json").exists())
        files = list(out.glob("*.json"))
        self.assertEqual(len(files), 1)
        self.assertRegex(files[0].name, r"^[0-9a-f]{32}\.json$")

    def test_a_foreign_origin_is_refused(self) -> None:
        port, out = self.serve()
        self.assertEqual(self.post(port, envelope(FakeIngest.EVENT), origin="https://evil.example"), 403)
        self.assertEqual(list(out.glob("*.json")), [])

    def test_the_apps_own_localhost_origin_is_accepted(self) -> None:
        port, out = self.serve()
        self.assertEqual(self.post(port, envelope(FakeIngest.EVENT), origin="http://localhost:3313"), 200)
        self.assertEqual(len(list(out.glob("*.json"))), 1)

    def test_an_oversized_body_is_refused(self) -> None:
        # refused before it is read: the client sees 413, or the connection closed under it — never a stored event
        port, out = self.serve()
        try:
            code = self.post(port, b"x" * (fi.MAX_BODY + 1))
        except urllib.error.URLError:
            code = 413
        self.assertEqual(code, 413)
        self.assertEqual(list(out.glob("*.json")), [])

    def test_a_chunked_body_is_read(self) -> None:
        # found by the real run: @sentry/nextjs 11.8.0 posts with Transfer-Encoding: chunked and no Content-Length
        import http.client
        port, out = self.serve()
        conn = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
        body = envelope(FakeIngest.EVENT)
        conn.request("POST", "/api/1/envelope/?sentry_key=public", body=iter([body[:20], body[20:]]),
                     headers={"Content-Type": "application/x-sentry-envelope"}, encode_chunked=True)
        self.assertEqual(conn.getresponse().status, 200)
        conn.close()
        self.assertEqual(len(list(out.glob("*.json"))), 1)
