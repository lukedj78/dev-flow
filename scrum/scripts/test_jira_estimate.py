"""Tests for jira_estimate.py, against a local HTTP server standing in for Jira."""

from __future__ import annotations

import base64
import io
import json
import os
import sys
import tempfile
import threading
import unittest
from contextlib import redirect_stderr, redirect_stdout
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import jira_estimate as je  # noqa: E402
import meta_io  # noqa: E402

TOKEN = "ATATT-secret-token-value"


class FakeJira(unittest.TestCase):
    status = 204

    def setUp(self) -> None:
        self.seen: list[dict] = []
        test = self

        class Handler(BaseHTTPRequestHandler):
            def do_PUT(self):  # noqa: N802
                body = self.rfile.read(int(self.headers.get("Content-Length") or 0))
                test.seen.append({"path": self.path, "auth": self.headers.get("Authorization"),
                                  "type": self.headers.get("Content-Type"), "body": json.loads(body or b"{}")})
                self.send_response(test.status)
                self.end_headers()

            def log_message(self, *a):
                pass

        self.server = HTTPServer(("127.0.0.1", 0), Handler)
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.site = f"http://127.0.0.1:{self.server.server_address[1]}"
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        (self.root / ".workflow").mkdir()
        meta_io.write_json(self.root / ".workflow/meta.json",
                           {"tracker": {"provider": "jira", "project": {"site": self.site, "board_id": "7", "project_key": "ABC"}}})
        self._env = {k: os.environ.get(k) for k in ("JIRA_EMAIL", "JIRA_API_TOKEN", "JIRA_SITE")}
        os.environ["JIRA_SITE"] = self.site   # the local fake is allowed only because the user's environment names it

    def tearDown(self) -> None:
        self.server.shutdown()
        self.server.server_close()
        self._tmp.cleanup()
        for k, v in self._env.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v

    def run_cli(self, *args: str) -> tuple[int, str]:
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = je.main([str(self.root), *args])
        return code, out.getvalue() + err.getvalue()

    def test_sends_the_estimation_put_with_basic_auth(self) -> None:
        os.environ.update({"JIRA_EMAIL": "me@example.com", "JIRA_API_TOKEN": TOKEN})
        code, _ = self.run_cli("--key", "ABC-1", "--points", "3")
        self.assertEqual(code, 0)
        req = self.seen[0]
        self.assertEqual(req["path"], "/rest/agile/1.0/issue/ABC-1/estimation?boardId=7")
        self.assertEqual(req["body"], {"value": "3"})
        self.assertEqual(req["type"], "application/json")
        self.assertEqual(base64.b64decode(req["auth"].split()[1]).decode(), f"me@example.com:{TOKEN}")

    def test_missing_credentials_exit_2_without_echo(self) -> None:
        os.environ.pop("JIRA_EMAIL", None)
        os.environ["JIRA_API_TOKEN"] = TOKEN
        code, out = self.run_cli("--key", "ABC-1", "--points", "3")
        self.assertEqual(code, 2)
        self.assertIn("JIRA_EMAIL", out)
        self.assertNotIn(TOKEN, out)
        self.assertEqual(self.seen, [])

    def test_401_names_the_cause(self) -> None:
        FakeJira.status = 401
        try:
            os.environ.update({"JIRA_EMAIL": "me@example.com", "JIRA_API_TOKEN": TOKEN})
            code, out = self.run_cli("--key", "ABC-1", "--points", "3")
        finally:
            FakeJira.status = 204
        self.assertEqual(code, 1)
        self.assertIn("401", out)
        self.assertIn("JIRA_API_TOKEN", out)
        self.assertNotIn(TOKEN, out)

    def test_credentials_go_only_to_atlassian_or_the_site_the_user_named(self) -> None:
        # meta.json is in the repository: a cloned project must not be able to send the token elsewhere
        os.environ.update({"JIRA_EMAIL": "me@example.com", "JIRA_API_TOKEN": TOKEN})
        os.environ.pop("JIRA_SITE")
        code, out = self.run_cli("--key", "ABC-1", "--points", "3")   # meta points at 127.0.0.1, not named by the user
        self.assertEqual(code, 2)
        self.assertEqual(self.seen, [])
        self.assertNotIn(TOKEN, out)
        for site in ("evil.example.com", "http://acme.atlassian.net", "acme.atlassian.net.evil.com"):
            with self.assertRaises(ValueError, msg=site):
                je.allowed_base(site)
        self.assertEqual(je.allowed_base("acme.atlassian.net"), "https://acme.atlassian.net")
        self.assertEqual(je.allowed_base("https://acme.atlassian.net/"), "https://acme.atlassian.net")

    def test_key_and_board_cannot_reshape_the_url(self) -> None:
        os.environ.update({"JIRA_EMAIL": "me@example.com", "JIRA_API_TOKEN": TOKEN})
        code, _ = self.run_cli("--key", "ABC-1/../../x", "--points", "3")
        self.assertEqual(code, 2)
        meta_io.write_json(self.root / ".workflow/meta.json",
                           {"tracker": {"provider": "jira", "project": {"site": self.site, "board_id": "7?x=1"}}})
        code, _ = self.run_cli("--key", "ABC-1", "--points", "3")
        self.assertEqual(code, 2)
        self.assertEqual(self.seen, [])

    def test_missing_board_in_meta_is_explained(self) -> None:
        meta_io.write_json(self.root / ".workflow/meta.json", {"tracker": {"provider": "jira", "project": {"site": self.site}}})
        os.environ.update({"JIRA_EMAIL": "me@example.com", "JIRA_API_TOKEN": TOKEN})
        code, out = self.run_cli("--key", "ABC-1", "--points", "3")
        self.assertEqual(code, 2)
        self.assertIn("board_id", out)


if __name__ == "__main__":
    unittest.main()
