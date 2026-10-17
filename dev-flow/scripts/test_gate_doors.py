"""Every phase gate holds at both doors: `set-phase` and `append-history --phase-after`.

    cd dev-flow/scripts && python3 -m unittest test_gate_doors -v

Why this exists: `append-history --phase-after` checked two of the six gates. A project with no
data-residency decision was refused by `set-phase deployed` and moved to `deployed` by
`append-history --phase-after deployed`, exit 0 (AUDIT.md §6.2). The bootstrap templates for Codex,
Gemini and generic runtimes move phase through append-history, so on those runtimes that was the
normal path, not a back door.
"""

from __future__ import annotations

import argparse
import io
import json
import subprocess
import sys
import tempfile
import types
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import update_meta  # noqa: E402

GATES = ["inventory_gate", "wireframes_gate", "data_residency_gate", "design_lint_gate",
         "registry_intake_gate", "primitives_guard_gate"]


def stub(name: str, passes: bool) -> types.ModuleType:
    m = types.ModuleType(name)
    m.verify = lambda root, meta: (passes, "ok" if passes else f"{name} says no")
    m.remedy = lambda root: f"  Fix: {name} remedy"
    return m


class Fixture(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        (self.root / ".workflow").mkdir()
        self.meta_path = self.root / ".workflow" / "meta.json"

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def write(self, **meta) -> None:
        self.meta_path.write_text(json.dumps({"history": [], "artifacts": {}, **meta}))

    def meta(self) -> dict:
        return json.loads(self.meta_path.read_text())


class BothDoors(Fixture):
    """Stub every gate to pass except one, and walk a project from `empty` to `deployed` through each door."""

    def door(self, which: str, target: str) -> tuple[int, str]:
        ns = argparse.Namespace(project_root=self.root)
        if which == "set-phase":
            ns.phase, ns.allow_regress, fn = target, False, update_meta.cmd_set_phase
        else:
            ns.skill, ns.inputs, ns.outputs, ns.phase_after = "test", "{}", "[]", target
            fn = update_meta.cmd_append_history
        err = io.StringIO()
        with redirect_stderr(err), redirect_stdout(io.StringIO()):
            rc = fn(ns)
        return rc, err.getvalue()

    def test_each_gate_refuses_through_both_doors(self) -> None:
        for failing in GATES:
            for which in ("set-phase", "append-history"):
                with self.subTest(gate=failing, door=which):
                    self.write(phase="empty")
                    mods = {g: stub(g, g != failing) for g in GATES}
                    with mock.patch.dict(sys.modules, mods):
                        rc, err = self.door(which, "deployed")
                    self.assertEqual(rc, 1, f"{which} let {failing} through")
                    self.assertIn(f"{failing} says no", err)
                    self.assertIn(f"{failing} remedy", err)
                    self.assertEqual(self.meta()["phase"], "empty")
                    self.assertEqual(self.meta()["history"], [])

    def test_both_doors_open_when_every_gate_passes(self) -> None:
        for which in ("set-phase", "append-history"):
            with self.subTest(door=which):
                self.write(phase="empty")
                with mock.patch.dict(sys.modules, {g: stub(g, True) for g in GATES}):
                    rc, err = self.door(which, "deployed")
                self.assertEqual(rc, 0, err)
                self.assertEqual(self.meta()["phase"], "deployed")

    def test_a_history_entry_that_does_not_move_the_phase_is_not_gated(self) -> None:
        # rn-upgrade and rn-write-tests record a run at the current phase; nothing crosses, nothing to hold.
        self.write(phase="module_added")
        with mock.patch.dict(sys.modules, {g: stub(g, False) for g in GATES}):
            rc, err = self.door("append-history", "module_added")
        self.assertEqual(rc, 0, err)
        self.assertEqual(len(self.meta()["history"]), 1)

    def test_both_doors_give_the_same_refusal(self) -> None:
        out = {}
        for which in ("set-phase", "append-history"):
            self.write(phase="empty")
            with mock.patch.dict(sys.modules, {g: stub(g, g != "data_residency_gate") for g in GATES}):
                out[which] = self.door(which, "deployed")[1]
        self.assertEqual(out["set-phase"], out["append-history"])


class TheAuditCase(Fixture):
    """The real reproduction, with the real gates: no data-residency decision, everything else opted out."""

    def test_append_history_no_longer_moves_past_an_undecided_residency(self) -> None:
        self.write(phase="empty",
                   inventory={"verdict": "skipped", "reason": "test"},
                   wireframes={"skipped": True, "reason": "test"},
                   stack={"framework": "next", "ui": "shadcn", "data_residency": None})
        for argv in (["set-phase", "deployed"],
                     ["append-history", "--skill", "x", "--phase-after", "deployed"]):
            with self.subTest(argv=argv[0]):
                r = subprocess.run([sys.executable, str(HERE / "update_meta.py"), str(self.root), *argv],
                                   capture_output=True, text=True)
                self.assertEqual(r.returncode, 1, r.stdout)
                self.assertIn("data-residency decision", r.stderr)
                self.assertEqual(self.meta()["phase"], "empty")


if __name__ == "__main__":
    unittest.main()
