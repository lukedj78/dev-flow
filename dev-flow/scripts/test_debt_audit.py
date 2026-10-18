"""Tests for the debt audit: debt_model, debt_sources, debt_tests and debt_audit."""

from __future__ import annotations

import io
import json
import os
import subprocess
import time
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import debt_model as dm  # noqa: E402
import debt_sources as ds  # noqa: E402
import debt_tests as dt  # noqa: E402
import debt_audit as da  # noqa: E402
import meta_io  # noqa: E402


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

    def test_compliance_flagged_is_never_kept_by_a_verdict(self) -> None:
        f = F("compliance", "R3", severity="H", signal=True)
        reviewed = {f.id: {"verdict": "accepted", "reason": "x", "hash": ""}}
        open_, kept, _ = dm.apply_decisions([f], {"compliance": {"flagged": ["R3"]}}, reviewed, self.root)
        self.assertEqual((len(open_), kept), (1, []))

    def test_a_lapsed_verdict_returns_as_a_signal_on_any_source(self) -> None:
        self.write("app/p.tsx", "a")
        f = F("launch-audit", "og", file="app/p.tsx", severity="missing")
        reviewed = {f.id: {"verdict": "accepted", "reason": "x", "hash": dm.file_hash(self.root, "app/p.tsx")}}
        self.write("app/p.tsx", "changed")
        open_, _, _ = dm.apply_decisions([f], {}, reviewed, self.root)
        self.assertTrue(open_[0].signal)

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

    def test_churn_paths_are_relative_to_the_project_inside_a_repo(self) -> None:
        git = ["git", "-C", str(self.root), "-c", "user.email=t@t", "-c", "user.name=t"]
        subprocess.run(git[:3] + ["init", "-q"], check=True)
        self.write("apps/web/a.ts", "1")
        subprocess.run(git + ["add", "-A"], check=True)
        subprocess.run(git + ["commit", "-qm", "c"], check=True)
        self.assertEqual(dm.churn(self.root / "apps/web").get("a.ts"), 1)

    def test_diff_runs(self) -> None:
        self.assertEqual(dm.diff_runs({"a", "b"}, {"b", "c"}), ({"c"}, {"a"}))


SHADSCAN = {"agentHandoff": {"actionables": [
    {"findingId": "custom-controls-have-labels", "disposition": "fix", "title": "Fix custom controls have accessible labels",
     "evidence": [{"filePath": "app/a.tsx", "line": 180, "message": "SelectTrigger has no accessible label."},
                  {"filePath": "app/b.tsx", "line": 12, "message": "Switch has no accessible label."}]},
    {"findingId": "command-menu", "disposition": "decide", "title": "Decide whether the app needs a command menu",
     "evidence": []}]}}


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

    def test_a_timeout_kills_the_whole_process_group(self) -> None:
        pidfile = self.root / "grandchild.pid"
        self.fake("app-security", f"import subprocess\np = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(30)'])\n"
                  f"open({str(pidfile)!r}, 'w').write(str(p.pid))\ntime.sleep(30)")
        rel, args, _, parse = ds.SCANNERS["app-security"]
        ds.SCANNERS["app-security"] = (rel, args, 2, parse)
        self.run_only("app-security")
        pid = int(pidfile.read_text())
        time.sleep(0.5)
        with self.assertRaises(ProcessLookupError):
            os.kill(pid, 0)

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
        self.assertEqual(srcs["observability"].status, "partial")

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

    def test_registry_failure_is_not_checked(self) -> None:
        (self.proj / "registry-lock.json").write_text("{}", encoding="utf-8")
        self.fake("registry-intake", "sys.exit(2)")
        self.assertEqual(self.run_only("registry-intake")[1]["registry-intake"].status, "not checked")
        self.fake("registry-intake", "raise RuntimeError('boom')")
        self.assertEqual(self.run_only("registry-intake")[1]["registry-intake"].status, "not checked")

    def test_each_registry_problem_is_its_own_finding(self) -> None:
        (self.proj / "registry-lock.json").write_text("{}", encoding="utf-8")
        self.fake("registry-intake", 'print("✗ registry intake:\\n  hook missing\\n  snapshot drifted: ui/button"); sys.exit(1)')
        fs, _ = self.run_only("registry-intake")
        self.assertEqual(len({f.id for f in fs}), 2)

    def test_promote_crash_is_not_checked(self) -> None:
        self.fake("promote-component", "raise RuntimeError('boom')")
        self.assertEqual(self.run_only("promote-component")[1]["promote-component"].status, "not checked")

    def test_promote_rows_parsed(self) -> None:
        self.fake("promote-component", 'print("# Promotion scan")\nprint("| Component | Usages | Current level | Suggestion |")\nprint("|---|---|---|---|")\n'
                  'print("| `Card` | 4 | L0 | Promote to L2 - components/shared/<dominio>/Card.tsx |")\n'
                  'print("| `Row` | 1 | L0 | OK — stays |")')
        fs, _ = self.run_only("promote-component")
        self.assertEqual([(f.check, f.severity) for f in fs], [("Card", "promote")])

    def test_shadscan_stale_and_missing(self) -> None:
        fs, srcs = ds.recorded(self.proj, {}, None)
        self.assertEqual({s.name: s.status for s in srcs}["shadscan"], "missing")
        p = self.proj / "docs/ui/shadscan.json"
        p.parent.mkdir(parents=True)
        p.write_text(json.dumps(SHADSCAN), encoding="utf-8")
        meta = {"shadscan": {"last_run_at": "2026-10-01T00:00:00Z"}}
        fs, srcs = ds.recorded(self.proj, meta, "2026-10-05T00:00:00Z")
        shad = [f for f in fs if f.source == "shadscan"]
        # the real shape (annotix, shadscan 0.9): findingId, and one finding per evidence entry
        self.assertEqual([(f.check, f.severity, f.file, f.line, f.stale) for f in shad], [
            ("custom-controls-have-labels", "fix", "app/a.tsx", 180, True),
            ("custom-controls-have-labels", "fix", "app/b.tsx", 12, True),
            ("command-menu", "decide", None, None, True)])
        self.assertIn("SelectTrigger has no accessible label", shad[0].detail)
        self.assertEqual(len({f.id for f in shad}), 3)
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

    def test_a_manual_row_with_a_bad_file_is_dropped_with_a_note(self) -> None:
        (self.proj / ".workflow/debt").mkdir(parents=True)
        (self.proj / ".workflow/debt/manual.json").write_text(json.dumps([
            {"source": "forms", "check": "C", "file": 12, "detail": "x"},
            {"source": "forms", "check": "D", "file": "app/f.tsx", "detail": "y"}]), encoding="utf-8")
        fs, src = ds.manual(self.proj)
        self.assertEqual([f.check for f in fs], ["D"])
        self.assertEqual(src.status, "partial")

    def test_no_manual_is_missing(self) -> None:
        self.assertEqual(ds.manual(self.proj)[1].status, "missing")

    def test_timestamps_compare_as_instants(self) -> None:
        self.assertFalse(ds._older("2026-10-05T10:00:00+00:00", "2026-10-05T10:00:00Z"))
        self.assertTrue(ds._older("2026-10-05T09:00:00+00:00", "2026-10-05T10:00:00Z"))

    def test_write_tests_counts_as_a_change_for_the_debt_audit(self) -> None:
        meta = {"history": [{"skill": "write-tests", "ran_at": "2026-10-07T00:00:00Z"}]}
        self.assertEqual(ds.last_material_change(meta), ("2026-10-07T00:00:00Z", "write-tests"))

    def test_last_material_change(self) -> None:
        meta = {"history": [{"skill": "module-add", "ran_at": "2026-10-01T00:00:00Z"},
                            {"skill": "spec-review", "ran_at": "2026-10-05T00:00:00Z"}]}
        self.assertEqual(ds.last_material_change(meta), ("2026-10-01T00:00:00Z", "module-add"))
        self.assertEqual(ds.last_material_change({}), (None, None))


ACTION = '"use server"\nimport { db } from "@/lib/db"\nexport async function createPlan() { await db.insert(plans).values({}) }\n'


class TestCheck(Tmp):
    def web(self, base: str = "") -> None:
        pre = f"{base}/" if base else ""
        self.write(f"{pre}package.json", json.dumps({"dependencies": {"next": "16.3.8"}}))
        self.write(f"{pre}app/page.tsx", "export default function P() { return null }\n")

    def untested(self, meta: dict | None = None, authz: set | None = None) -> list[str]:
        fs, _ = dt.check(self.root, meta or {}, authz or set())
        return [f.file for f in fs]

    def test_server_action_without_test_is_found(self) -> None:
        self.web()
        self.write("app/actions/plan.ts", ACTION)
        self.assertEqual(self.untested(), ["app/actions/plan.ts"])

    def test_unit_import_counts(self) -> None:
        self.web()
        self.write("app/actions/plan.ts", ACTION)
        self.write("tests/plan.test.ts", 'import { createPlan } from "@/app/actions/plan"\n')
        self.assertEqual(self.untested(), [])
        self.assertEqual(dt.tested_by(self.root, "app/actions/plan.ts"), "unit")

    def test_relative_import_counts(self) -> None:
        self.web()
        self.write("app/actions/plan.ts", ACTION)
        self.write("app/actions/plan.test.ts", 'import { createPlan } from "./plan"\n')
        self.assertEqual(dt.tested_by(self.root, "app/actions/plan.ts"), "unit")

    def test_e2e_visit_counts(self) -> None:
        self.web()
        self.write("app/actions/plan.ts", ACTION)
        self.write("app/[locale]/(app)/plans/page.tsx", 'import { createPlan } from "@/app/actions/plan"\n')
        self.write("e2e/plans.spec.ts", 'await page.goto("/plans")\n')
        self.assertEqual(dt.tested_by(self.root, "app/actions/plan.ts"), "e2e")
        self.assertEqual(self.untested(), [])

    def test_e2e_visit_to_another_page_does_not_count(self) -> None:
        self.web()
        self.write("app/actions/plan.ts", ACTION)
        self.write("app/[locale]/(app)/plans/page.tsx", 'import { createPlan } from "@/app/actions/plan"\n')
        self.write("e2e/home.spec.ts", 'await page.goto("/plansx")\nawait page.goto("/")\n')
        self.assertIsNone(dt.tested_by(self.root, "app/actions/plan.ts"))

    def test_a_locale_prefixed_url_counts(self) -> None:
        # next-intl's default localePrefix is "always": the spec visits /en/plans
        self.web()
        self.write("app/[locale]/plans/actions.ts", ACTION)
        self.write("app/[locale]/plans/page.tsx", 'import { createPlan } from "./actions"\n')
        self.write("e2e/plans.spec.ts", 'await page.goto("/en/plans")\n')
        self.assertEqual(dt.tested_by(self.root, "app/[locale]/plans/actions.ts"), "e2e")

    def test_an_absolute_url_counts(self) -> None:
        self.web()
        self.write("app/actions/plan.ts", ACTION)
        self.write("app/plans/page.tsx", 'import { createPlan } from "@/app/actions/plan"\n')
        self.write("e2e/plans.spec.ts", 'await page.goto("http://localhost:3000/plans")\n')
        self.assertEqual(dt.tested_by(self.root, "app/actions/plan.ts"), "e2e")

    def test_a_catch_all_matches_many_segments(self) -> None:
        self.web()
        self.write("app/actions/plan.ts", ACTION)
        self.write("app/docs/[...slug]/page.tsx", 'import { createPlan } from "@/app/actions/plan"\n')
        self.write("e2e/docs.spec.ts", 'await page.goto("/docs/a/b/c")\n')
        self.assertEqual(dt.tested_by(self.root, "app/actions/plan.ts"), "e2e")

    def test_playwright_test_dir_is_read(self) -> None:
        # Playwright's default testDir is ./tests: those specs are e2e, not unit tests
        self.web()
        self.write("playwright.config.ts", 'export default defineConfig({ testDir: "./tests/browser" })\n')
        self.write("app/actions/plan.ts", ACTION)
        self.write("app/plans/page.tsx", 'import { createPlan } from "@/app/actions/plan"\n')
        self.write("tests/browser/plans.spec.ts", 'await page.goto("/plans")\n')
        self.assertEqual(dt.tested_by(self.root, "app/actions/plan.ts"), "e2e")

    def test_route_detection_needs_an_app_folder(self) -> None:
        self.web()
        self.write("lib/myapp/route.ts", "export async function POST() {}\n")
        self.assertEqual(dt.mutations(self.root), [])

    def test_naming_the_path_needs_a_boundary(self) -> None:
        self.web()
        self.write("lib/plans.ts", "export const save = () => db.insert(plans).values({})\n")
        self.write("tests/u.test.ts", 'import { x } from "@/lib/plans-utils"\n')
        self.assertIsNone(dt.tested_by(self.root, "lib/plans.ts"))

    def test_page_url(self) -> None:
        self.assertEqual(dt.page_url("app/[locale]/(marketing)/plans/[id]/page.tsx"), "/plans/[id]")
        self.assertEqual(dt.page_url("app/page.tsx"), "/")
        self.assertEqual(dt.page_url("src/app/(app)/settings/page.tsx"), "/settings")

    def test_dynamic_segment_matches_any_value(self) -> None:
        self.web()
        self.write("app/actions/plan.ts", ACTION)
        self.write("app/plans/[id]/page.tsx", 'import { createPlan } from "@/app/actions/plan"\n')
        self.write("e2e/plan.spec.ts", "await page.goto(`/plans/42`)\n")
        self.assertEqual(dt.tested_by(self.root, "app/actions/plan.ts"), "e2e")

    def test_read_only_route_is_not_a_mutation(self) -> None:
        self.web()
        self.write("app/api/health/route.ts", "export async function GET() { return Response.json({}) }\n")
        self.write("app/api/items/route.ts", "export async function POST() { return Response.json({}) }\n")
        self.assertEqual(dt.mutations(self.root), ["app/api/items/route.ts"])

    def test_a_drizzle_write_outside_actions_is_a_mutation(self) -> None:
        self.web()
        self.write("lib/plans.ts", "export const save = () => db.update(plans).set({})\n")
        self.write("lib/read.ts", "export const list = () => db.select().from(plans)\n")
        self.assertEqual(dt.mutations(self.root), ["lib/plans.ts"])

    def test_authz_on_the_same_file_raises_severity(self) -> None:
        self.web()
        self.write("app/actions/plan.ts", ACTION)
        fs, _ = dt.check(self.root, {}, {"app/actions/plan.ts"})
        self.assertEqual(fs[0].severity, "authz")

    def test_coverage_summary_is_read(self) -> None:
        self.web()
        self.write("coverage/coverage-summary.json", json.dumps({
            "total": {"lines": {"pct": 61.5}}, str(self.root / "app/a.ts"): {"lines": {"pct": 0}}}))
        cov, why = dt.coverage(self.root)
        self.assertEqual((cov, why), ({"total": 61.5, "files": {"app/a.ts": 0}}, ""))

    def test_no_coverage_names_the_command(self) -> None:
        self.web()
        _, srcs = dt.check(self.root, {"stack": {"test": "vitest+playwright"}}, set())
        cov = {s.name: s for s in srcs}["coverage"]
        self.assertEqual(cov.status, "not checked")
        self.assertIn("@vitest/coverage-v8", cov.reason)
        self.assertIn("json-summary", cov.reason)
        # found on fit-coach: one red test file and Vitest writes no summary at all
        self.assertIn("--coverage.reportOnFailure=true", cov.reason)

    def test_jest_command(self) -> None:
        self.web()
        _, srcs = dt.check(self.root, {"stack": {"test": "jest-expo+rntl"}}, set())
        self.assertIn("--coverageReporters=json-summary", {s.name: s for s in srcs}["coverage"].reason)

    def test_each_web_surface_is_checked(self) -> None:
        self.write("package.json", json.dumps({"private": True}))
        for app in ("web", "admin"):
            self.web(f"apps/{app}")
            self.write(f"apps/{app}/app/actions/x.ts", ACTION)
        self.assertEqual(sorted(self.untested()), ["apps/admin/app/actions/x.ts", "apps/web/app/actions/x.ts"])

    def test_node_modules_and_tests_are_not_mutations(self) -> None:
        self.web()
        self.write("node_modules/pkg/a.ts", ACTION)
        self.write("app/actions/plan.test.ts", ACTION)
        self.assertEqual(dt.mutations(self.root), [])

    # found by the real run on a copy of fit-coach (Task 6)
    def test_generated_code_is_not_read(self) -> None:
        self.web()
        self.write(".eve/compile/authored-modules/x.mjs", ACTION)
        self.write(".output/server/chunk.mjs", ACTION)
        self.write(".vercel/output/fn.mjs", ACTION)
        self.assertEqual(dt.mutations(self.root), [])

    def test_seed_scripts_are_not_app_mutations(self) -> None:
        self.web()
        self.write("scripts/demo/seed.ts", "await db.insert(users).values([])\n")
        self.write("drizzle/seed.ts", "await db.insert(users).values([])\n")
        self.assertEqual(dt.mutations(self.root), [])

    def test_e2e_reaches_a_library_through_the_action_a_page_uses(self) -> None:
        self.web()
        self.write("lib/server/plans.ts", "export const save = () => db.insert(plans).values({})\n")
        self.write("app/actions/plan.ts", '"use server"\nimport { save } from "@/lib/server/plans"\nexport async function createPlan() { await save() }\n')
        self.write("app/[locale]/(app)/plans/page.tsx", 'import { createPlan } from "@/app/actions/plan"\n')
        self.write("e2e/plans.spec.ts", 'await page.goto("/plans")\n')
        self.assertEqual(dt.tested_by(self.root, "lib/server/plans.ts"), "e2e")

    def test_e2e_calling_a_route_directly_counts(self) -> None:
        self.web()
        self.write("app/api/items/[id]/route.ts", "export async function DELETE() { return new Response(null) }\n")
        self.write("e2e/items.spec.ts", "await request.delete(`/api/items/${id}`)\n")
        self.assertEqual(dt.tested_by(self.root, "app/api/items/[id]/route.ts"), "e2e")

    def test_import_cycles_end(self) -> None:
        self.web()
        self.write("lib/a.ts", 'import { b } from "./b"\nexport const a = () => db.insert(t).values({})\n')
        self.write("lib/b.ts", 'import { a } from "./a"\nexport const b = 1\n')
        self.assertIsNone(dt.tested_by(self.root, "lib/a.ts"))

    def test_mobile_is_not_applicable(self) -> None:
        self.write("package.json", json.dumps({"dependencies": {"expo": "58.0.0"}}))
        self.write("app.json", '{"expo": {"name": "m"}}')
        fs, srcs = dt.check(self.root, {}, set())
        self.assertEqual(fs, [])
        self.assertEqual({s.name: s for s in srcs}["tests"].status, "not applicable")


META_KEYS = {"last_run_at", "bands", "to_confirm", "not_checked", "sources", "new", "closed", "report"}
HEADINGS = ["# Debt audit", "## Before the next release", "## With the features that touch these files", "## Later",
            "## Tests", "## Not checked", "## Kept on purpose", "## Since the last audit"]


class Collect(Tmp):
    """The sibling scanners are fakes in a tmp SKILLS_ROOT; only app-security is installed."""

    def setUp(self) -> None:
        super().setUp()
        self.skills = self.root / "skills"
        self.proj = self.root / "proj"
        self._saved = ds.SKILLS_ROOT
        ds.SKILLS_ROOT = self.skills
        self.write("proj/package.json", json.dumps({"dependencies": {"next": "16.3.8"}}))
        self.write("proj/app/page.tsx", "export default function P() { return null }\n")
        self.meta = {"phase": "deployed", "stack": {"framework": "next", "observability": ["errors"]},
                     "history": [{"skill": "module-add", "ran_at": "2026-10-01T00:00:00Z"}], "custom": {"keep": 1}}
        (self.proj / ".workflow").mkdir()
        meta_io.write_json(self.proj / ".workflow/meta.json", self.meta)
        self.security([("server-action-unauthenticated", "app/actions/plan.ts:3")])

    def tearDown(self) -> None:
        ds.SKILLS_ROOT = self._saved
        super().tearDown()

    def security(self, hits: list[tuple[str, str]]) -> None:
        rows = [{"check": c, "status": "found", "detail": "no session check", "where": [w]} for c, w in hits]
        self.write("skills/app-security/scripts/scan_security.py", f"import json\nprint(json.dumps({rows!r}))\n")

    def meta_now(self) -> dict:
        return meta_io.read_meta(self.proj / ".workflow/meta.json")

    def test_collect_writes_the_three_outputs(self) -> None:
        block = da.collect(self.proj, now="2026-10-18T12:00:00Z")
        self.assertEqual(set(block), META_KEYS)
        self.assertEqual(self.meta_now()["debt_audit"], block)
        data = json.loads((self.proj / ".workflow/debt/findings.json").read_text(encoding="utf-8"))
        self.assertEqual(set(data), {"run_at", "open", "kept", "not_checked", "sources", "notes"})
        report = (self.proj / "docs/debt/debt-audit.md").read_text(encoding="utf-8")
        positions = [report.find(h) for h in HEADINGS]
        self.assertTrue(all(p >= 0 for p in positions), positions)
        self.assertEqual(positions, sorted(positions))
        self.assertIn("[to confirm] app/actions/plan.ts:3", report)

    def test_meta_is_written_under_the_lock(self) -> None:
        calls = []
        real = meta_io.locked
        def spy(d):
            calls.append(d)
            return real(d)
        meta_io.locked = spy
        try:
            da.collect(self.proj)
        finally:
            meta_io.locked = real
        self.assertEqual(calls, [(self.proj / ".workflow").resolve()])

    def test_phase_and_other_keys_untouched(self) -> None:
        before = self.meta_now()
        da.collect(self.proj)
        after = self.meta_now()
        changed = {k for k in set(before) | set(after) if before.get(k) != after.get(k)}
        self.assertEqual(changed - {"updated_at", "meta_digest", "contract_version"}, {"debt_audit", "history"})
        self.assertEqual(after["history"][-1]["skill"], "dev-flow")
        self.assertEqual(after["history"][-1]["action"], "debt-audit")
        self.assertEqual(after["phase"], "deployed")

    def test_second_run_reports_new_and_closed(self) -> None:
        da.collect(self.proj)
        self.security([("raw-sql", "lib/q.ts:9")])
        block = da.collect(self.proj)
        self.assertEqual((block["new"], block["closed"]), (1, 1))

    def test_before_release_counts_only_confirmed(self) -> None:
        self.security([("server-action-unauthenticated", "app/actions/a.ts:1"), ("raw-sql", "lib/b.ts:2")])
        self.write("proj/app/actions/a.ts", "a")
        (self.proj / ".workflow/debt").mkdir(parents=True)
        fid = "app-security:server-action-unauthenticated:app/actions/a.ts"
        (self.proj / ".workflow/debt/reviewed.json").write_text(json.dumps(
            {fid: {"verdict": "confirmed", "reason": "", "hash": dm.file_hash(self.proj, "app/actions/a.ts")}}), encoding="utf-8")
        block = da.collect(self.proj)
        self.assertEqual((block["bands"]["before_release"], block["to_confirm"]), (1, 1))

    def test_not_installed_sources_are_listed_as_not_checked(self) -> None:
        block = da.collect(self.proj)
        self.assertIn("compliance", block["not_checked"])
        self.assertEqual(block["sources"]["app-security"], "fresh")

    def test_without_meta_the_report_is_still_written(self) -> None:
        (self.proj / ".workflow/meta.json").unlink()
        block = da.collect(self.proj)
        self.assertTrue((self.proj / "docs/debt/debt-audit.md").is_file())
        self.assertFalse((self.proj / ".workflow/meta.json").exists())
        self.assertEqual(set(block), META_KEYS)

    def test_rows_with_the_same_id_are_merged(self) -> None:
        # launch-audit reports one check with many `where` entries and no file: one finding, every place in its detail
        self.write("skills/launch-audit/scripts/scan_launch.py", "import json\nprint(json.dumps([{'check': 'sitemap', "
                   "'status': 'missing', 'detail': '3 routes', 'where': ['/a', '/b', '/c']}]))\n")
        da.collect(self.proj)
        data = json.loads((self.proj / ".workflow/debt/findings.json").read_text(encoding="utf-8"))
        ids = [r["id"] for r in data["open"]]
        self.assertEqual(len(ids), len(set(ids)), ids)
        row = next(r for r in data["open"] if r["id"] == "launch-audit:sitemap:-")
        for place in ("/a", "/b", "/c"):
            self.assertIn(place, row["detail"])
        self.assertEqual(row["detail"].count("3 routes"), 1, row["detail"])

    def test_a_scanner_that_saw_only_part_is_partial(self) -> None:
        # found on fit-coach: gitleaks and Semgrep missing inside app-security, and the report said nothing
        self.write("skills/app-security/scripts/scan_security.py", "import json\nprint(json.dumps([{'check': 'secrets-history', "
                   "'status': 'not checked', 'detail': 'gitleaks not installed', 'where': []}]))\n")
        block = da.collect(self.proj)
        self.assertEqual(block["sources"]["app-security"], "partial")
        self.assertIn("app-security", block["not_checked"])
        report = (self.proj / "docs/debt/debt-audit.md").read_text(encoding="utf-8")
        nc = report[report.index("## Not checked"):report.index("## Kept on purpose")]
        self.assertIn("gitleaks not installed", nc)

    def test_the_report_shows_the_test_figures(self) -> None:
        # found on fit-coach: coverage read "fresh" and its percentage appeared nowhere
        self.write("proj/coverage/coverage-summary.json", json.dumps({"total": {"lines": {"pct": 42.3}}}))
        da.collect(self.proj)
        report = (self.proj / "docs/debt/debt-audit.md").read_text(encoding="utf-8")
        tests = report[report.index("## Tests"):report.index("## Not checked")]
        self.assertIn("42.3% lines", tests)
        self.assertIn("files write data", tests)

    def test_a_source_that_did_not_run_closes_nothing(self) -> None:
        da.collect(self.proj)
        block = da.collect(self.proj, skip={"app-security"})
        self.assertEqual(block["closed"], 0)

    def test_a_finding_moved_to_kept_is_not_closed(self) -> None:
        da.collect(self.proj)
        self.write("proj/app/actions/plan.ts", "x")
        fid = "app-security:server-action-unauthenticated:app/actions/plan.ts"
        (self.proj / ".workflow/debt/reviewed.json").write_text(json.dumps(
            {fid: {"verdict": "accepted", "reason": "r", "hash": dm.file_hash(self.proj, "app/actions/plan.ts")}}), encoding="utf-8")
        self.assertEqual(da.collect(self.proj)["closed"], 0)

    def test_an_invalid_meta_stops_before_anything_runs(self) -> None:
        (self.proj / ".workflow/meta.json").write_text('{"history": {}}', encoding="utf-8")
        with self.assertRaises(SystemExit) as e:
            da.collect(self.proj)
        self.assertEqual(e.exception.code, 2)
        self.assertFalse((self.proj / "docs/debt/debt-audit.md").exists())

    def test_findings_carry_the_hash_a_verdict_needs(self) -> None:
        self.write("proj/app/actions/plan.ts", "x")
        da.collect(self.proj)
        rows = json.loads((self.proj / ".workflow/debt/findings.json").read_text(encoding="utf-8"))["open"]
        row = next(r for r in rows if r["file"] == "app/actions/plan.ts")
        self.assertEqual(row["hash"], dm.file_hash(self.proj, "app/actions/plan.ts"))
        (self.proj / ".workflow/debt/reviewed.json").write_text(json.dumps(
            {row["id"]: {"verdict": "false_positive", "reason": "r", "hash": row["hash"]}}), encoding="utf-8")
        da.collect(self.proj)
        data = json.loads((self.proj / ".workflow/debt/findings.json").read_text(encoding="utf-8"))
        self.assertIn(row["id"], [r["id"] for r in data["kept"]])

    def test_an_accepted_authz_check_does_not_raise_a_mutation(self) -> None:
        self.write("proj/app/actions/plan.ts", ACTION)
        self.meta["security"] = {"findings": {"accepted": [{"check": "server-action-unauthenticated", "reason": "r"}]}}
        meta_io.write_json(self.proj / ".workflow/meta.json", self.meta)
        da.collect(self.proj)
        rows = json.loads((self.proj / ".workflow/debt/findings.json").read_text(encoding="utf-8"))["open"]
        row = next(r for r in rows if r["source"] == "tests")
        self.assertEqual(row["band"], "with-features")

    def test_missing_sources_are_in_not_checked_and_the_report_agrees(self) -> None:
        block = da.collect(self.proj)
        self.assertIn("shadscan", block["not_checked"])
        report = (self.proj / "docs/debt/debt-audit.md").read_text(encoding="utf-8")
        self.assertNotIn("Every source ran.", report)

    def test_show_without_a_run_says_so(self) -> None:
        out = io.StringIO()
        with redirect_stdout(out):
            code = da.main(["show", str(self.proj)])
        self.assertEqual(code, 1)
        self.assertIn("no debt audit yet", out.getvalue())

    def test_cli_json(self) -> None:
        out = io.StringIO()
        with redirect_stdout(out):
            code = da.main(["collect", str(self.proj), "--json", "--skip", "promote-component"])
        self.assertEqual(code, 0)
        self.assertEqual(set(json.loads(out.getvalue())), META_KEYS)


if __name__ == "__main__":
    unittest.main()
