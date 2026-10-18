"""Tests for the debt audit: debt_model, debt_sources, debt_tests and debt_audit."""

from __future__ import annotations

import io
import json
import subprocess
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

    def test_mobile_is_not_applicable(self) -> None:
        self.write("package.json", json.dumps({"dependencies": {"expo": "58.0.0"}}))
        self.write("app.json", '{"expo": {"name": "m"}}')
        fs, srcs = dt.check(self.root, {}, set())
        self.assertEqual(fs, [])
        self.assertEqual({s.name: s for s in srcs}["tests"].status, "not applicable")


META_KEYS = {"last_run_at", "bands", "to_confirm", "not_checked", "sources", "new", "closed", "report"}
HEADINGS = ["# Debt audit", "## Before the next release", "## With the features that touch these files", "## Later",
            "## Not checked", "## Kept on purpose", "## Since the last audit"]


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
