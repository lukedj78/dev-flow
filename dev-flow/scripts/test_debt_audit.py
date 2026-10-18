"""Tests for the debt audit: debt_model, debt_sources, debt_tests and debt_audit."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import debt_model as dm  # noqa: E402


def F(source: str, check: str, **kw) -> dm.Finding:
    return dm.Finding(source, check, "d", **kw)


class Tmp(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def write(self, rel: str, text: str = "") -> Path:
        p = self.root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")
        return p


class Model(Tmp):
    def test_band_table_rows(self) -> None:
        cases = [
            (F("app-security", "authz", severity="found"), "before-release"),
            (F("compliance", "R3", severity="H"), "before-release"),
            (F("compliance", "R5", severity="M"), "with-features"),
            (F("registry-intake", "K8", severity="block"), "before-release"),
            (F("observability", "errors"), "before-release"),
            (F("observability", "uptime"), "later"),
            (F("tests", "untested-mutation", severity="authz"), "before-release"),
            (F("tests", "untested-mutation"), "with-features"),
            (F("forms", "C", severity="HIGH"), "with-features"),
            (F("forms", "J", severity="LOW"), "later"),
            (F("shadscan", "r1", severity="fix"), "with-features"),
            (F("shadscan", "r2", severity="decide"), "later"),
            (F("vercel-doctor", "high", severity="high"), "with-features"),
            (F("vercel-doctor", "low", severity="low"), "later"),
            (F("launch-audit", "og", severity="missing"), "with-features"),
            (F("promote-component", "Card", severity="promote"), "later"),
        ]
        for f, band in cases:
            self.assertEqual(dm.band_for(f), band, f)

    def test_the_id_is_stable(self) -> None:
        self.assertEqual(F("app-security", "authz", file="app/a.ts", line=3).id, "app-security:authz:app/a.ts")
        self.assertEqual(F("compliance", "R3").id, "compliance:R3:-")

    def test_gate_acceptance_applies_per_check(self) -> None:
        fs = [F("app-security", "authz", file="app/a.ts", signal=True), F("app-security", "authz", file="app/b.ts", signal=True)]
        meta = {"security": {"findings": {"accepted": [{"check": "authz", "reason": "admin-only tool"}]}}}
        open_, kept, _ = dm.apply_decisions(fs, meta, {}, self.root)
        self.assertEqual(open_, [])
        self.assertEqual([k.kept for k in kept], ["admin-only tool", "admin-only tool"])

    def test_other_gate_keys(self) -> None:
        fs = [F("launch-audit", "og", severity="missing"), F("shadscan", "r1", severity="fix"), F("shadscan", "r2", severity="fix")]
        meta = {"launch_audit": {"dismissed": {"og": "not public yet"}},
                "shadscan": {"false_positives": {"r1": "custom focus ring"}, "rules_left_red": {"r2": "next sprint"}}}
        open_, kept, _ = dm.apply_decisions(fs, meta, {}, self.root)
        self.assertEqual(open_, [])
        self.assertEqual(sorted(k.kept for k in kept), ["custom focus ring", "next sprint", "not public yet"])

    def test_reviewed_verdicts_apply_per_id(self) -> None:
        self.write("app/a.ts", "a")
        self.write("app/b.ts", "b")
        self.write("app/c.ts", "c")
        fs = [F("app-security", "authz", file=f"app/{n}.ts", signal=True) for n in "abc"]
        reviewed = {
            fs[0].id: {"verdict": "confirmed", "reason": "", "hash": dm.file_hash(self.root, "app/a.ts")},
            fs[1].id: {"verdict": "accepted", "reason": "public data", "hash": dm.file_hash(self.root, "app/b.ts")},
            fs[2].id: {"verdict": "false_positive", "reason": "checked by proxy", "hash": dm.file_hash(self.root, "app/c.ts")},
        }
        open_, kept, _ = dm.apply_decisions(fs, {}, reviewed, self.root)
        self.assertEqual([(f.file, f.signal) for f in open_], [("app/a.ts", False)])
        self.assertEqual(sorted(k.kept for k in kept), ["checked by proxy", "public data"])

    def test_false_positive_returns_when_the_file_changes(self) -> None:
        self.write("app/c.ts", "c")
        f = F("app-security", "authz", file="app/c.ts", signal=True)
        reviewed = {f.id: {"verdict": "false_positive", "reason": "x", "hash": dm.file_hash(self.root, "app/c.ts")}}
        self.write("app/c.ts", "c changed")
        open_, kept, _ = dm.apply_decisions([f], {}, reviewed, self.root)
        self.assertEqual(kept, [])
        self.assertEqual(len(open_), 1)
        self.assertTrue(open_[0].signal)

    def test_compliance_flagged_stays_open(self) -> None:
        f = F("compliance", "R3", severity="H", signal=True)
        open_, kept, _ = dm.apply_decisions([f], {"compliance": {"flagged": ["R3"]}}, {}, self.root)
        self.assertEqual(kept, [])
        self.assertIn("legal decision", open_[0].detail)

    def test_corrupt_reviewed_is_ignored_with_a_note(self) -> None:
        f = F("app-security", "authz", file="app/a.ts", signal=True)
        open_, _, notes = dm.apply_decisions([f], {}, None, self.root)
        self.assertEqual(len(open_), 1)
        self.assertEqual(len(notes), 1)
        self.assertIn("reviewed.json", notes[0])

    def test_order_by_churn_then_source(self) -> None:
        fs = [F("forms", "A", file="a.ts"), F("forms", "B", file="b.ts"), F("forms", "C", file="c.ts")]
        out = dm.order(fs, {"b.ts": 9, "a.ts": 1})
        self.assertEqual([f.file for f in out], ["b.ts", "a.ts", "c.ts"])

    def test_order_without_churn_keeps_source_order(self) -> None:
        self.assertEqual(dm.churn(self.root), {})
        fs = [F("forms", "A", file="a.ts"), F("forms", "B", file="b.ts")]
        self.assertEqual(dm.order(fs, {}), fs)

    def test_churn_counts_commits_per_file(self) -> None:
        git = ["git", "-C", str(self.root), "-c", "user.email=t@t", "-c", "user.name=t"]
        subprocess.run(git[:3] + ["init", "-q"], check=True)
        for i in range(3):
            self.write("a.ts", str(i))
            subprocess.run(git + ["add", "-A"], check=True)
            subprocess.run(git + ["commit", "-qm", f"c{i}"], check=True)
        self.assertEqual(dm.churn(self.root).get("a.ts"), 3)

    def test_diff_runs(self) -> None:
        self.assertEqual(dm.diff_runs({"a", "b"}, {"b", "c"}), ({"c"}, {"a"}))


if __name__ == "__main__":
    unittest.main()
