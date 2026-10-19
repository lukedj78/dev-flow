"""Tests for render_probe.mjs: a real headless Chrome against two fixture pages.

    cd app-verification/scripts && python3 -m unittest test_render_probe

Skipped (and counted as skipped by run_skill_tests.py) without Node >= 22 or an installed Chrome/Chromium/Edge —
the probe needs both, and says so with exit code 3, which the last test checks on every machine with Node.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
PROBE = HERE / "render_probe.mjs"
FIXTURES = HERE / "fixtures" / "probe"
IDS = {"overflow-x", "headline-lines", "reduced-hidden", "font-fallback", "broken-image", "sidebar-phone"}


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
