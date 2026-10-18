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
import debt_sources as ds  # noqa: E402


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


class Sources(Tmp):
    """Fake scanners live in a tmp SKILLS_ROOT, at the same relative paths as the real ones."""

    def setUp(self) -> None:
        super().setUp()
        self.skills = self.root / "skills"
        self.proj = self.root / "proj"
        self.proj.mkdir()
        self._saved = (ds.SKILLS_ROOT, dict(ds.SCANNERS))
        ds.SKILLS_ROOT = self.skills

    def tearDown(self) -> None:
        ds.SKILLS_ROOT, saved = self._saved
        ds.SCANNERS.clear()
        ds.SCANNERS.update(saved)
        super().tearDown()

    def fake(self, name: str, body: str) -> None:
        rel = ds.SCANNERS[name][0]
        p = self.skills / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("import json, sys, time\n" + body + "\n", encoding="utf-8")

    def run_only(self, name: str, meta: dict | None = None, skip: set | None = None, web: bool = True):
        for other in list(ds.SCANNERS):
            if other != name:
                del ds.SCANNERS[other]
        fs, srcs = ds.run_scanners(self.proj, meta or {}, skip or set(), web)
        return fs, {s.name: s for s in srcs}

    def test_app_security_found_rows_become_signals(self) -> None:
        self.fake("app-security", 'print(json.dumps([{"check": "server-action-unauthenticated", "status": "found", '
                  '"detail": "x", "where": ["app/a.ts:3 createPlan"], "routed_to": "app-security"}, '
                  '{"check": "raw-sql", "status": "ok", "detail": "", "where": []}]))')
        fs, srcs = self.run_only("app-security")
        self.assertEqual([(f.file, f.line, f.signal, f.check) for f in fs],
                         [("app/a.ts", 3, True, "server-action-unauthenticated")])
        self.assertEqual(srcs["app-security"].status, "fresh")

    def test_a_dependency_hit_has_no_file(self) -> None:
        self.fake("app-security", 'print(json.dumps([{"check": "dependencies", "status": "found", "detail": "1 advisory", '
                  '"where": ["next@16.0.0: high — cache leak"]}]))')
        fs, _ = self.run_only("app-security")
        self.assertIsNone(fs[0].file)
        self.assertIn("next@16.0.0", fs[0].detail)

    def test_missing_skill_is_not_checked(self) -> None:
        _, srcs = self.run_only("app-security")
        self.assertEqual((srcs["app-security"].status, srcs["app-security"].reason), ("not checked", "not installed"))

    def test_garbage_output_is_not_checked(self) -> None:
        self.fake("app-security", 'print("boom")')
        _, srcs = self.run_only("app-security")
        self.assertEqual(srcs["app-security"].status, "not checked")
        self.assertIn("output", srcs["app-security"].reason)

    def test_timeout_is_not_checked(self) -> None:
        self.fake("app-security", "time.sleep(3)")
        rel, args, _, parse = ds.SCANNERS["app-security"]
        ds.SCANNERS["app-security"] = (rel, args, 1, parse)
        _, srcs = self.run_only("app-security")
        self.assertEqual(srcs["app-security"].status, "not checked")
        self.assertIn("timed out", srcs["app-security"].reason)

    def test_skip_is_not_checked(self) -> None:
        self.fake("app-security", 'print("[]")')
        _, srcs = self.run_only("app-security", skip={"app-security"})
        self.assertEqual((srcs["app-security"].status, srcs["app-security"].reason), ("not checked", "skipped"))

    def test_launch_audit_is_web_only(self) -> None:
        self.fake("launch-audit", 'print(json.dumps([{"check": "og-image", "status": "missing", "detail": "x", "where": []}]))')
        fs, srcs = self.run_only("launch-audit")
        self.assertEqual([(f.check, f.severity) for f in fs], [("og-image", "missing")])
        _, srcs = self.run_only("launch-audit", web=False)
        self.assertEqual(srcs["launch-audit"].status, "not applicable")

    def test_observability_runs_all_levels_when_none_chosen(self) -> None:
        self.fake("observability", 'print(json.dumps([{"level": "errors", "status": "found", "detail": "--all" in sys.argv and "all" or "some"}]))')
        fs, _ = self.run_only("observability", meta={"stack": {}})
        self.assertEqual([(f.check, f.detail) for f in fs], [("errors", "all")])
        fs, _ = self.run_only("observability", meta={"stack": {"observability": ["errors"]}})
        self.assertEqual(fs[0].detail, "some")

    def test_observability_not_checked_rows_become_notes(self) -> None:
        self.fake("observability", 'print(json.dumps([{"level": "errors", "status": "not checked", "detail": "region"}]))')
        fs, srcs = self.run_only("observability")
        self.assertEqual(fs, [])
        self.assertIn("region", srcs["observability"].reason)

    def test_compliance_findings_are_signals(self) -> None:
        self.fake("compliance", 'print(json.dumps({"signals": {}, "findings": [{"id": "R3", "severity": "H", "article": "44", "title": "residency"}]}))')
        fs, _ = self.run_only("compliance")
        self.assertEqual([(f.check, f.severity, f.signal, f.file) for f in fs], [("R3", "H", True, None)])

    def test_registry_intake_without_lock_is_skipped(self) -> None:
        self.fake("registry-intake", 'print("✗ registry intake:\\n  bad"); sys.exit(1)')
        fs, srcs = self.run_only("registry-intake")
        self.assertEqual(fs, [])
        self.assertEqual(srcs["registry-intake"].status, "not checked")
        (self.proj / "registry-lock.json").write_text("{}", encoding="utf-8")
        fs, srcs = self.run_only("registry-intake")
        self.assertEqual([(f.detail, f.severity) for f in fs], [("bad", "block")])

    def test_promote_rows_parsed(self) -> None:
        self.fake("promote-component", 'print("| Component | Usages | Current level | Suggestion |")\nprint("|---|---|---|---|")\n'
                  'print("| `Card` | 4 | L0 | Promote to L2 - components/shared/<dominio>/Card.tsx |")\n'
                  'print("| `Row` | 1 | L0 | OK — stays |")')
        fs, _ = self.run_only("promote-component")
        self.assertEqual([(f.check, f.severity) for f in fs], [("Card", "promote")])

    def test_shadscan_stale_and_missing(self) -> None:
        fs, srcs = ds.recorded(self.proj, {}, None)
        self.assertEqual({s.name: s.status for s in srcs}["shadscan"], "missing")
        p = self.proj / "docs/ui/shadscan.json"
        p.parent.mkdir(parents=True)
        p.write_text(json.dumps({"agentHandoff": {"actionables": [
            {"ruleId": "a11y-label", "disposition": "fix", "file": "app/page.tsx:12", "title": "button without a label"}]}}),
            encoding="utf-8")
        meta = {"shadscan": {"last_run_at": "2026-10-01T00:00:00Z"}}
        fs, srcs = ds.recorded(self.proj, meta, "2026-10-05T00:00:00Z")
        shad = [f for f in fs if f.source == "shadscan"]
        self.assertEqual([(f.check, f.severity, f.file, f.line, f.stale) for f in shad],
                         [("a11y-label", "fix", "app/page.tsx", 12, True)])
        self.assertEqual({s.name: s.status for s in srcs}["shadscan"], "stale")

    def test_vercel_counts_become_rows(self) -> None:
        meta = {"vercel_doctor": {"last_run_at": "2026-10-06T00:00:00Z", "findings": {"high": 0, "medium": 2, "low": 1}}}
        fs, srcs = ds.recorded(self.proj, meta, "2026-10-05T00:00:00Z")
        vd = [f for f in fs if f.source == "vercel-doctor"]
        self.assertEqual([(f.check, f.stale) for f in vd], [("medium", False), ("low", False)])
        self.assertEqual({s.name: s.status for s in srcs}["vercel-doctor"], "fresh")

    def test_manual_findings_are_read(self) -> None:
        (self.proj / ".workflow/debt").mkdir(parents=True)
        (self.proj / ".workflow/debt/manual.json").write_text(json.dumps([
            {"source": "forms", "check": "C", "severity": "HIGH", "file": "app/f.tsx", "line": 4, "detail": "no dirty gating"}]),
            encoding="utf-8")
        fs, src = ds.manual(self.proj)
        self.assertEqual([(f.source, f.check, f.file) for f in fs], [("forms", "C", "app/f.tsx")])
        self.assertEqual(src.status, "fresh")

    def test_corrupt_manual_is_not_checked(self) -> None:
        (self.proj / ".workflow/debt").mkdir(parents=True)
        (self.proj / ".workflow/debt/manual.json").write_text("{", encoding="utf-8")
        fs, src = ds.manual(self.proj)
        self.assertEqual((fs, src.status), ([], "not checked"))

    def test_no_manual_is_missing(self) -> None:
        self.assertEqual(ds.manual(self.proj)[1].status, "missing")

    def test_last_material_change(self) -> None:
        meta = {"history": [{"skill": "module-add", "ran_at": "2026-10-01T00:00:00Z"},
                            {"skill": "spec-review", "ran_at": "2026-10-05T00:00:00Z"}]}
        self.assertEqual(ds.last_material_change(meta), ("2026-10-01T00:00:00Z", "module-add"))
        self.assertEqual(ds.last_material_change({}), (None, None))


if __name__ == "__main__":
    unittest.main()
