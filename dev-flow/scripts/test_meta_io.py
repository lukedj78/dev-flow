"""Tests for meta_io.py and the scripts that write meta.json through it. Temp directories only.

    cd dev-flow/scripts && python3 -m unittest test_meta_io -v

Why these exist: meta.json used to be written with a plain `write_text` and no lock. Twenty
`append-history` runs in parallel kept 11 to 15 entries, every process exiting 0, and a reader
running alongside the writer saw an empty file 30 times in 1,100 reads (AUDIT.md §6.2).
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import threading
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import meta_io  # noqa: E402

N = 20


def run(*argv: str) -> subprocess.Popen:
    return subprocess.Popen([sys.executable, *argv], stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)


def wait_all(procs: list[subprocess.Popen]) -> list[tuple[int, str]]:
    return [(p.wait(), p.stderr.read().decode()) for p in procs]


class Fixture(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name) / "proj"
        self.root.mkdir()
        subprocess.run([sys.executable, str(HERE / "init_workflow.py"), str(self.root), "--name", "P"],
                       check=True, capture_output=True)
        self.meta_path = self.root / ".workflow" / "meta.json"

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def meta(self) -> dict:
        return json.loads(self.meta_path.read_text())

    def assert_all_ok(self, results: list[tuple[int, str]]) -> None:
        for rc, err in results:
            self.assertEqual(rc, 0, err)


class AtomicWrite(Fixture):
    def test_leaves_valid_json_and_no_temp_file(self) -> None:
        meta_io.write_json(self.meta_path, {"phase": "empty", "history": []})
        self.assertEqual(self.meta()["phase"], "empty")
        self.assertEqual(sorted(p.name for p in self.meta_path.parent.iterdir()), ["meta.json"])

    def test_a_reader_never_sees_a_partial_file(self) -> None:
        # ~1 MB, so a non-atomic write is slow enough for the reader to land inside it.
        big = {"phase": "empty", "history": [{"skill": "x" * 100, "i": i} for i in range(8000)]}
        stop = threading.Event()

        def writer() -> None:
            while not stop.is_set():
                meta_io.write_json(self.meta_path, big)

        t = threading.Thread(target=writer)
        t.start()
        bad = 0
        try:
            for _ in range(500):
                try:
                    json.loads(self.meta_path.read_text())
                except json.JSONDecodeError:
                    bad += 1
        finally:
            stop.set()
            t.join()
        self.assertEqual(bad, 0)

    def test_lock_is_a_no_op_without_a_workflow_dir(self) -> None:
        # The callers report a missing meta.json themselves; the lock must not invent the folder.
        missing = Path(self._tmp.name) / "nowhere"
        with meta_io.locked(missing):
            pass
        self.assertFalse(missing.exists())


class Concurrency(Fixture):
    def setUp(self) -> None:
        super().setUp()
        subprocess.run([sys.executable, str(HERE / "inventory.py"), "record", str(self.root),
                        "--verdict", "skipped", "--reason", "test"], check=True, capture_output=True)

    def test_parallel_update_meta_runs_lose_nothing(self) -> None:
        for i in range(N):
            (self.root / f"f{i}.txt").write_text(str(i))
        procs = [run(str(HERE / "update_meta.py"), str(self.root), "append-history", "--skill", f"s-{i}")
                 for i in range(N)]
        procs += [run(str(HERE / "update_meta.py"), str(self.root), "record-artifact",
                      "--path", f"f{i}.txt", "--produced-by", "test") for i in range(N)]
        self.assert_all_ok(wait_all(procs))
        m = self.meta()
        self.assertEqual(sorted(h["skill"] for h in m["history"] if h["skill"].startswith("s-")),
                         sorted(f"s-{i}" for i in range(N)))
        self.assertEqual(len(m["artifacts"]), N)

    def test_different_writers_do_not_clobber_each_other(self) -> None:
        # inventory.py and data_residency.py write meta.json themselves, not through update_meta.py.
        procs = []
        for i in range(N // 2):
            procs.append(run(str(HERE / "update_meta.py"), str(self.root), "append-history", "--skill", f"s-{i}"))
            procs.append(run(str(HERE / "data_residency.py"), "add", str(self.root),
                             "--name", f"Vendor{i}", "--service", "svc", "--data", "email", "--region", "eu-west-1"))
        procs.append(run(str(HERE / "inventory.py"), "record", str(self.root),
                         "--verdict", "build", "--searched", "skills"))
        self.assert_all_ok(wait_all(procs))
        m = self.meta()
        self.assertEqual(len([h for h in m["history"] if h["skill"].startswith("s-")]), N // 2)
        self.assertEqual(len(m["compliance"]["sub_processors"]), N // 2)
        self.assertEqual(m["inventory"]["verdict"], "build")

    def test_parallel_init_creates_one_valid_file(self) -> None:
        fresh = Path(self._tmp.name) / "fresh"
        fresh.mkdir()
        procs = [run(str(HERE / "init_workflow.py"), str(fresh), "--name", f"P{i}") for i in range(10)]
        self.assert_all_ok(wait_all(procs))
        m = json.loads((fresh / ".workflow" / "meta.json").read_text())
        self.assertEqual(m["phase"], "empty")
        self.assertEqual(sorted(p.name for p in (fresh / ".workflow").iterdir()), ["meta.json"])

    def test_writers_in_other_skills_take_the_same_lock(self) -> None:
        # Six scripts outside dev-flow write meta.json, each through its own vendored meta_io.py.
        # Each one runs here alongside update_meta.py, and every change must survive.
        repo = HERE.parent.parent
        root = str(self.root)

        def call(skill: str, code: str) -> subprocess.Popen:
            return run("-c", f"import sys; from pathlib import Path; "
                             f"sys.path.insert(0, {str(repo / skill / 'scripts')!r}); {code}")

        meta_path = str(self.meta_path)
        procs = [run(str(HERE / "update_meta.py"), root, "append-history", "--skill", f"s-{i}") for i in range(N)]
        procs += [
            run(str(repo / "wireframe-canvas/scripts/wireframes.py"), "skip", root, "--reason", "test"),
            run(str(repo / "linear-scrum/scripts/meta_linear.py"), meta_path, "ensure-scrum"),
            call("forms", f"import scaffold_lib_forms as m; m.append_history(Path({meta_path!r}), 'tanstack', [])"),
            call("design-md-to-app", f"import setup_design_lint as m; m.record(Path({root!r}))"),
            call("design-md-to-app", f"import setup_primitives_guard as m; m.record(Path({root!r}))"),
            call("registry-intake", f"import registry_intake as m; m.record(Path({root!r}), 'enforced')"),
        ]
        self.assert_all_ok(wait_all(procs))
        m = self.meta()
        self.assertEqual(len([h for h in m["history"] if h["skill"].startswith("s-")]), N)
        self.assertIn("forms", [h["skill"] for h in m["history"]])
        self.assertTrue(m["wireframes"]["skipped"])
        self.assertIn("cadence_weeks", m["scrum"])
        self.assertEqual(m["stack"]["design_lint"], "shadcn-lint")
        self.assertEqual(m["stack"]["primitives_guard"], "installed")
        self.assertEqual(m["stack"]["registry_intake"], "enforced")


if __name__ == "__main__":
    unittest.main()
