"""Tests for research.py. No network: `get` is stubbed, and `gh` is never called.

    cd dev-flow/scripts && python3 -m unittest test_research -v
"""

from __future__ import annotations

import io
import json
import sys
import unittest
from contextlib import redirect_stdout
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import research as rs  # noqa: E402


def run(argv: list[str], answers: list[tuple[int, str]] | None = None) -> tuple[int, str]:
    """Run the CLI with `get` returning the queued (status, body) pairs."""
    queue = list(answers or [])
    rs.get = lambda url, accept="application/json": queue.pop(0) if queue else (0, "")
    out = io.StringIO()
    with redirect_stdout(out):
        rc = rs.main(argv)
    return rc, out.getvalue()


class InternalAddresses(unittest.TestCase):
    """`read` hands the URL to r.jina.ai, a third party. A client's internal host never goes there."""

    def test_refused_and_named(self) -> None:
        for url, word in [
            ("http://localhost:3000/admin", "localhost"),
            ("https://127.0.0.1/x", "127.0.0.1"),
            ("https://10.0.0.5/report", "10.0.0.5"),
            ("https://192.168.1.9:8080/", "192.168.1.9"),
            ("https://172.16.4.2/", "172.16.4.2"),
            ("http://intranet.cliente.local/fatture", "intranet.cliente.local"),
            ("https://billing.acme.internal/", "billing.acme.internal"),
        ]:
            with self.subTest(url=url):
                rc, out = run(["read", url])
                self.assertEqual(rc, rs.UNREACHABLE)
                self.assertIn("refused", out)
                self.assertIn(word, out)
                self.assertIn("third party", out)

    def test_a_public_url_is_not_refused(self) -> None:
        rc, out = run(["read", "https://example.com/post"], [(200, "# Hello")])
        self.assertEqual(rc, rs.ANSWERED)
        self.assertIn("Hello", out)

    def test_the_check_is_on_the_host_not_the_string(self) -> None:
        # a public host whose path merely mentions a private one stays allowed
        self.assertIsNone(rs.is_internal("https://example.com/docs/localhost-setup"))
        self.assertIsNone(rs.is_internal("https://10-0-0-5.example.com/"))


class NeverInventsAnAnswer(unittest.TestCase):
    """"I could not look" and "there is nothing" are different facts and different exit codes."""

    def test_rate_limited_is_unreachable_not_empty(self) -> None:
        rc, out = run(["reddit", "invoice renaming"], [(429, "")])
        self.assertEqual(rc, rs.UNREACHABLE)
        self.assertIn("could not look", out)
        self.assertIn("rate-limited", out)
        self.assertIn("not covered", out)

    def test_no_answer_at_all_is_unreachable(self) -> None:
        rc, out = run(["hn", "prompt caching"], [(0, "")])
        self.assertEqual(rc, rs.UNREACHABLE)
        self.assertIn("no answer", out)

    def test_answered_with_nothing_is_its_own_code(self) -> None:
        rc, out = run(["hn", "a phrase nobody wrote"], [(200, json.dumps({"hits": []}))])
        self.assertEqual(rc, rs.EMPTY)
        self.assertIn("nothing matched", out)
        self.assertNotIn("could not look", out)

    def test_results_exit_zero(self) -> None:
        body = json.dumps({"hits": [{"title": "Prompt caching", "points": 300, "num_comments": 72,
                                     "url": "https://e.dev/p", "objectID": "1"}]})
        rc, out = run(["hn", "prompt caching"], [(200, body)])
        self.assertEqual(rc, rs.ANSWERED)
        self.assertIn("Prompt caching", out)


class Parsing(unittest.TestCase):
    def test_a_url_that_is_not_a_thread_is_refused_before_the_request(self) -> None:
        rc, out = run(["thread", "https://www.reddit.com/r/macapps/"])
        self.assertEqual(rc, rs.UNREACHABLE)
        self.assertIn("not a Reddit thread", out)

    def test_a_url_that_is_not_a_post_is_refused_before_the_request(self) -> None:
        rc, out = run(["post", "https://x.com/someone"])
        self.assertEqual(rc, rs.UNREACHABLE)
        self.assertIn("not an X post", out)

    def test_both_x_and_twitter_hosts_are_read(self) -> None:
        tweet = json.dumps({"tweet": {"text": "hi", "author": {"screen_name": "jack"},
                                      "created_at": "2006", "likes": 1, "replies": 0, "retweets": 0}})
        for url in ["https://x.com/jack/status/20", "https://twitter.com/jack/status/20"]:
            with self.subTest(url=url):
                rc, out = run(["post", url], [(200, tweet)])
                self.assertEqual(rc, rs.ANSWERED)
                self.assertIn("@jack", out)


class Freshness(unittest.TestCase):
    """A repo stopped a year ago is read for the idea, not adopted — so the age is named."""

    def test_the_three_states(self) -> None:
        import time
        day = lambda d: time.strftime("%Y-%m-%d", time.localtime(time.time() - d * 86400))  # noqa: E731
        self.assertEqual(rs.freshness(day(10)), "alive")
        self.assertEqual(rs.freshness(day(200)), "warm")
        self.assertEqual(rs.freshness(day(500)), "stopped")
        self.assertEqual(rs.freshness("not a date"), "unknown")


if __name__ == "__main__":
    unittest.main(verbosity=2)
