"""Tests for render_probe.mjs: a real headless Chrome against two fixture pages.

    cd app-verification/scripts && python3 -m unittest test_render_probe

Skipped (and counted as skipped by run_skill_tests.py) without Node >= 22 or an installed Chrome/Chromium/Edge —
the probe needs both, and says so with exit code 3 (a page or runtime error is 4), checked on every machine with Node.
"""

from __future__ import annotations

import contextlib
import functools
import http.server
import json
import os
import threading
import shutil
import subprocess
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
PROBE = HERE / "render_probe.mjs"
FIXTURES = HERE / "fixtures" / "probe"
IDS = {"overflow-x", "headline-lines", "reduced-hidden", "font-fallback", "broken-image", "sidebar-phone"}  # + layout-shift, own fixture


@contextlib.contextmanager
def serve(directory: Path):
    """A throwaway HTTP server on 127.0.0.1 for pages that fetch (fetch() does not work from file://)."""
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(directory))
    handler.log_message = lambda *a, **k: None
    httpd = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{httpd.server_address[1]}"
    finally:
        httpd.shutdown()
        httpd.server_close()


def node_major() -> int:
    node = shutil.which("node")
    if not node:
        return 0
    out = subprocess.run([node, "--version"], capture_output=True, text=True).stdout.strip().lstrip("v")
    return int(out.split(".")[0]) if out else 0


def probe(*args: str, env: dict | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(["node", str(PROBE), *args], capture_output=True, text=True, timeout=180,
                          env={**os.environ, **(env or {})})


def has_browser() -> bool:
    if node_major() < 22:
        return False
    return probe("--find-browser").returncode == 0


NODE_OK = node_major() >= 22
BROWSER = NODE_OK and PROBE.exists() and has_browser()


@unittest.skipUnless(NODE_OK, "render_probe.mjs needs Node >= 22")
class Input(unittest.TestCase):
    def test_a_non_url_is_refused(self) -> None:
        r = probe("not a url")
        self.assertEqual(r.returncode, 2, r.stderr)

    def test_no_browser_is_a_clear_exit_3(self) -> None:
        r = probe((FIXTURES / "clean.html").as_uri(), env={"CHROME_PATH": "/nonexistent/chrome"})
        self.assertEqual(r.returncode, 3, r.stdout + r.stderr)
        self.assertNotRegex(r.stderr, r"(?m)^\s+at \S")  # a sentence, not a stack trace
        self.assertIn("CHROME_PATH", r.stderr)


@unittest.skipUnless(BROWSER, "no Chrome/Chromium/Edge found (set CHROME_PATH)")
class Measure(unittest.TestCase):
    def run_json(self, name: str, *extra: str) -> dict:
        r = probe((FIXTURES / name).as_uri(), "--json", *extra)
        self.assertEqual(r.returncode, 0, r.stderr)
        return json.loads(r.stdout)

    def test_every_defect_is_found(self) -> None:
        report = self.run_json("broken.html")
        found = {f["id"] for f in report["findings"]}
        self.assertEqual(found, IDS, json.dumps(report["findings"], indent=1))

    def test_findings_name_their_width_and_elements(self) -> None:
        report = self.run_json("broken.html")
        overflow = [f for f in report["findings"] if f["id"] == "overflow-x"]
        self.assertEqual({f["width"] for f in overflow}, {1440, 768, 390})
        self.assertTrue(any("wide" in el for f in overflow for el in f["elements"]), overflow)
        sidebar = [f for f in report["findings"] if f["id"] == "sidebar-phone"]
        self.assertEqual({f["width"] for f in sidebar}, {390})

    def test_the_clean_page_and_its_look_alikes_report_nothing(self) -> None:
        report = self.run_json("clean.html")
        self.assertEqual(report["findings"], [], json.dumps(report["findings"], indent=1))

    def test_a_class_added_by_script_does_not_hide_reduced_hidden(self) -> None:
        report = self.run_json("reveal-js.html", "--widths", "1440")
        self.assertEqual({f["id"] for f in report["findings"]}, {"reduced-hidden"}, report["findings"])

    def test_a_fragment_url_loads_both_passes(self) -> None:
        r = probe((FIXTURES / "clean.html").as_uri() + "#pricing", "--json", "--widths", "390", "--timeout", "20")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(json.loads(r.stdout)["findings"], [])

    def test_a_redirect_is_reported_with_the_final_url(self) -> None:
        report = self.run_json("redirect.html", "--widths", "390")
        self.assertTrue(report["final_url"].endswith("clean.html"), report)
        self.assertIn("redirected", " ".join(report["notes"]))

    def test_a_page_that_cannot_load_is_exit_4_not_3(self) -> None:
        r = probe("http://127.0.0.1:9/", "--widths", "390", "--timeout", "10")
        self.assertEqual(r.returncode, 4, r.stdout + r.stderr)
        self.assertNotRegex(r.stderr, r"(?m)^\s+at \S")

    def test_the_throwaway_profile_is_removed(self) -> None:
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            for _ in range(3):
                r = probe((FIXTURES / "clean.html").as_uri(), "--widths", "390", env={"TMPDIR": tmp})
                self.assertEqual(r.returncode, 0, r.stderr)
            self.assertEqual([p.name for p in Path(tmp).iterdir() if p.name.startswith("render-probe-")], [])

    def test_a_guessed_skeleton_is_a_layout_shift_naming_the_block_to_size(self) -> None:
        report = self.run_json("skeleton-shift.html", "--widths", "1440")
        shifts = [f for f in report["findings"] if f["id"] == "layout-shift"]
        self.assertEqual(len(shifts), 1, report["findings"])
        self.assertEqual(shifts[0]["level"], "FAIL")
        # the victim moved, and the block above it is the one to size
        self.assertTrue(any("below" in el and "pushed by" in el and "list" in el for el in shifts[0]["elements"]),
                        shifts)
        self.assertGreater(report["cls"]["1440"], 0.1)

    def test_skeletons_seen_are_reported_with_their_boxes(self) -> None:
        report = self.run_json("skeleton-shift.html", "--widths", "1440")
        seen = report["skeletons"]["1440"]
        self.assertEqual(len(seen), 1, seen)
        self.assertEqual(seen[0]["height"], 40)

    def test_a_shift_after_the_settle_time_is_still_measured(self) -> None:
        report = self.run_json("late-shift.html", "--widths", "1440")
        self.assertIn("layout-shift", {f["id"] for f in report["findings"]}, report)

    def test_cls_is_the_worst_session_window_not_the_sum(self) -> None:
        report = self.run_json("two-windows.html", "--widths", "1440")
        self.assertNotIn("layout-shift", {f["id"] for f in report["findings"]}, report)
        self.assertLess(report["cls"]["1440"], 0.05, report)

    def test_delay_keeps_a_client_fetch_skeleton_on_screen(self) -> None:
        with serve(FIXTURES) as base:
            url = f"{base}/fetch-skeleton.html"
            r = probe(url, "--json", "--widths", "1440", "--delay", "orders.json=800")
            self.assertEqual(r.returncode, 0, r.stderr)
            report = json.loads(r.stdout)
            self.assertIn("layout-shift", {f["id"] for f in report["findings"]}, report)
            self.assertEqual(len(report["skeletons"]["1440"]), 1)

    def test_delay_is_validated(self) -> None:
        self.assertEqual(probe((FIXTURES / "clean.html").as_uri(), "--delay", "no-equals").returncode, 2)
        self.assertEqual(probe((FIXTURES / "clean.html").as_uri(), "--delay", "x=abc").returncode, 2)

    def test_strict_turns_a_fail_into_exit_1(self) -> None:
        r = probe((FIXTURES / "broken.html").as_uri(), "--strict", "--widths", "390")
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertIn("FAIL", r.stdout)

    def test_out_writes_the_report_and_one_screenshot_per_width(self) -> None:
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            r = probe((FIXTURES / "clean.html").as_uri(), "--widths", "390,1440", "--out", tmp)
            self.assertEqual(r.returncode, 0, r.stderr)
            names = sorted(p.name for p in Path(tmp).iterdir())
            self.assertEqual(names, ["probe-1440.png", "probe-390.png", "probe.json"])


if __name__ == "__main__":
    unittest.main()
