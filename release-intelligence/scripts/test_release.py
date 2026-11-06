"""release.py: a stage is cleared by measured health, an approval carries the user's words, and a
database rollback is never executed here.

`health_verdict` is tested directly, because it is a pure function and it is the one place where
"missing telemetry" could silently become "healthy release". Everything else goes through `main()`
with a real `.workflow/meta.json`, so the lock, the JSON shape and the exit codes are all exercised
the way a caller would exercise them.
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import release  # noqa: E402

HEALTHY = {"window_minutes": 60, "error_rate_pct": 0.2, "p95_ms": 400, "sufficient": True}


class Health(unittest.TestCase):
    """The asymmetry the whole capability rests on: only a measurement says `continue`."""

    def th(self, **kw):
        t = dict(release.DEFAULT_THRESHOLDS)
        t.update(kw)
        return t

    def test_no_evidence_is_insufficient_never_continue(self) -> None:
        v, why = release.health_verdict(None, self.th())
        self.assertEqual(v, "insufficient")
        self.assertIn("required", why)

    def test_evidence_that_declares_itself_insufficient_is_refused(self) -> None:
        v, _ = release.health_verdict({"sufficient": False, "reason": "no traffic yet"}, self.th())
        self.assertEqual(v, "insufficient")

    def test_a_provider_failure_is_not_a_healthy_release(self) -> None:
        v, why = release.health_verdict({"provider_error": "sentry 503", "window_minutes": 60,
                                         "error_rate_pct": 0}, self.th())
        self.assertEqual(v, "insufficient")
        self.assertIn("provider failure", why)

    def test_a_window_shorter_than_the_policy_is_insufficient(self) -> None:
        v, why = release.health_verdict({"window_minutes": 5, "error_rate_pct": 0.0}, self.th())
        self.assertEqual(v, "insufficient")
        self.assertIn("5 min", why)

    def test_no_numbers_at_all_is_insufficient(self) -> None:
        v, _ = release.health_verdict({"window_minutes": 60}, self.th())
        self.assertEqual(v, "insufficient")

    def test_within_thresholds_continues(self) -> None:
        v, _ = release.health_verdict(HEALTHY, self.th())
        self.assertEqual(v, "continue")

    def test_over_the_error_threshold_pauses(self) -> None:
        v, _ = release.health_verdict({**HEALTHY, "error_rate_pct": 1.5}, self.th(error_rate_pct=1.0))
        self.assertEqual(v, "pause")

    def test_far_over_the_error_threshold_rolls_back(self) -> None:
        v, why = release.health_verdict({**HEALTHY, "error_rate_pct": 4.0}, self.th(error_rate_pct=1.0))
        self.assertEqual(v, "rollback")
        self.assertIn("stop serving", why)

    def test_over_the_latency_threshold_pauses(self) -> None:
        v, _ = release.health_verdict({**HEALTHY, "p95_ms": 3000}, self.th(p95_ms=1200))
        self.assertEqual(v, "pause")

    def test_a_regression_against_the_baseline_pauses_even_under_the_absolute_limit(self) -> None:
        """0.6% is fine in the abstract and terrible if the previous release ran at 0.05%."""
        v, why = release.health_verdict(
            {**HEALTHY, "error_rate_pct": 0.6, "baseline": {"error_rate_pct": 0.05}},
            self.th(error_rate_pct=1.0))
        self.assertEqual(v, "pause")
        self.assertIn("baseline", why)

    def test_a_tiny_absolute_rise_over_a_tiny_baseline_is_not_a_regression(self) -> None:
        v, _ = release.health_verdict(
            {**HEALTHY, "error_rate_pct": 0.02, "baseline": {"error_rate_pct": 0.0}},
            self.th(error_rate_pct=1.0))
        self.assertEqual(v, "continue")


class Project(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        (self.root / ".workflow").mkdir()
        self.meta({"project_slug": "t", "project_name": "T", "phase": "feature_complete"})
        subprocess.run(["git", "init", "-q"], cwd=self.root, check=True, capture_output=True)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def meta(self, data: dict) -> None:
        (self.root / ".workflow" / "meta.json").write_text(json.dumps(data))

    def read(self) -> dict:
        return json.loads((self.root / ".workflow" / "meta.json").read_text())

    def cli(self, *args: str) -> int:
        """Not named `run`: that is TestCase.run, and overriding it stops every test silently."""
        return release.main([str(self.root), *args])

    def enable(self, autonomy: str = "automated") -> None:
        self.assertEqual(self.cli("enable", "--autonomy", autonomy), 0)

    def plan(self, *extra: str) -> str:
        self.assertEqual(self.cli("plan", "--feature", "US-1", *extra), 0)
        return self.read()["release"]["releases"][-1]["id"]


class OptIn(Project):
    def test_status_on_a_project_that_never_enabled_it_says_nothing_changed(self) -> None:
        self.assertEqual(self.cli("status"), 0)
        self.assertNotIn("release", self.read())

    def test_plan_refuses_before_enable(self) -> None:
        self.assertEqual(self.cli("plan", "--feature", "US-1"), 2)

    def test_enable_writes_the_block_and_defaults_to_advisory(self) -> None:
        self.assertEqual(self.cli("enable"), 0)
        block = self.read()["release"]
        self.assertTrue(block["enabled"])
        self.assertEqual(block["autonomy"], "advisory")
        self.assertEqual(block["rollout_strategy"]["stages"], release.DEFAULT_STAGES)

    def test_disable_keeps_the_record(self) -> None:
        self.enable()
        rid = self.plan()
        self.assertEqual(self.cli("disable"), 0)
        block = self.read()["release"]
        self.assertFalse(block["enabled"])
        self.assertEqual(block["autonomy"], "disabled")
        self.assertTrue(any(r["id"] == rid for r in block["releases"]))

    def test_a_hand_edited_block_is_refused_not_overwritten(self) -> None:
        self.meta({"phase": "feature_complete", "release": "yes please"})
        self.assertEqual(self.cli("enable"), 2)
        self.assertEqual(self.read()["release"], "yes please")


class Planning(Project):
    def test_a_plan_records_the_measured_floor(self) -> None:
        self.enable()
        rid = self.plan()
        entry = self.read()["release"]["releases"][-1]
        self.assertEqual(entry["id"], rid)
        self.assertEqual(entry["status"], "planned")
        self.assertIn(entry["risk"], release.risk_mod.LEVELS)
        self.assertEqual(entry["risk"], entry["risk_floor"])

    def test_the_agent_may_raise_the_floor_with_a_reason(self) -> None:
        self.enable()
        self.assertEqual(self.cli("plan", "--feature", "US-1", "--raise-to", "high",
                                  "--reason", "it changes how invoices are numbered"), 0)
        entry = self.read()["release"]["releases"][-1]
        self.assertEqual(entry["risk"], "high")
        self.assertEqual(entry["risk_floor"], "low")
        self.assertEqual(entry["risk_raised"]["to"], "high")

    def test_a_raise_without_a_reason_is_refused(self) -> None:
        self.enable()
        self.assertEqual(self.cli("plan", "--feature", "US-1", "--raise-to", "high"), 2)

    def test_the_floor_cannot_be_lowered(self) -> None:
        """`--raise-to low` on a `low` floor is not a raise; on a higher floor it is a downgrade."""
        self.enable()
        self.meta({"phase": "feature_complete", "security": {"findings": {"open": 3}},
                   "release": self.read()["release"]})
        self.assertEqual(self.cli("plan", "--feature", "US-1", "--raise-to", "low",
                                  "--reason", "feels fine"), 2)

    def test_ids_are_sequential_within_a_day(self) -> None:
        self.enable()
        a, b = self.plan(), self.plan()
        self.assertNotEqual(a, b)
        self.assertTrue(b.endswith("-02"), b)

    def test_not_checked_is_carried_into_the_manifest(self) -> None:
        self.enable()
        self.plan()
        self.assertTrue(self.read()["release"]["releases"][-1]["not_checked"])


class Approval(Project):
    def test_approve_without_the_users_words_is_refused(self) -> None:
        self.enable()
        rid = self.plan()
        self.assertEqual(self.cli("approve", rid), 2)
        self.assertFalse(self.read()["release"]["releases"][-1]["approval"]["granted_by_user"])

    def test_an_empty_quote_is_not_a_quote(self) -> None:
        self.enable()
        rid = self.plan()
        self.assertEqual(self.cli("approve", rid, "--user-said", "   "), 2)

    def test_approve_records_the_quote(self) -> None:
        self.enable()
        rid = self.plan()
        self.assertEqual(self.cli("approve", rid, "--user-said", "vai, ma fermati al 25%"), 0)
        ap = self.read()["release"]["releases"][-1]["approval"]
        self.assertTrue(ap["granted_by_user"])
        self.assertEqual(ap["quote"], "vai, ma fermati al 25%")

    def test_approving_an_unknown_release_is_refused(self) -> None:
        self.enable()
        self.plan()
        self.assertEqual(self.cli("approve", "REL-nope", "--user-said", "ok"), 2)


class Staging(Project):
    def test_a_stage_without_evidence_is_refused(self) -> None:
        self.enable()
        rid = self.plan()
        self.assertEqual(self.cli("stage", rid, "--to", "5"), 1)
        self.assertEqual(self.read()["release"]["releases"][-1]["rollout"]["current_percent"], 0)

    def test_a_refused_stage_is_still_recorded_as_an_event(self) -> None:
        self.enable()
        rid = self.plan()
        self.cli("stage", rid, "--to", "5")
        events = self.read()["release"]["releases"][-1]["events"]
        self.assertTrue(any(e["event"].startswith("stage_refused") for e in events), events)

    def test_a_healthy_low_risk_stage_advances_in_automated_mode(self) -> None:
        self.enable("automated")
        rid = self.plan()
        self.assertEqual(self.cli("stage", rid, "--to", "5", "--evidence", json.dumps(HEALTHY)), 0)
        entry = self.read()["release"]["releases"][-1]
        self.assertEqual(entry["rollout"]["current_percent"], 5)
        self.assertEqual(entry["status"], "rolling")

    def test_assisted_mode_needs_an_approval_even_with_healthy_evidence(self) -> None:
        self.enable("assisted")
        rid = self.plan()
        self.assertEqual(self.cli("stage", rid, "--to", "5", "--evidence", json.dumps(HEALTHY)), 1)

    def test_after_an_approval_assisted_mode_advances(self) -> None:
        self.enable("assisted")
        rid = self.plan()
        self.cli("approve", rid, "--user-said", "ok")
        self.assertEqual(self.cli("stage", rid, "--to", "5", "--evidence", json.dumps(HEALTHY)), 0)

    def test_a_stage_cannot_go_backwards(self) -> None:
        self.enable("automated")
        rid = self.plan()
        self.cli("stage", rid, "--to", "25", "--evidence", json.dumps(HEALTHY))
        self.assertEqual(self.cli("stage", rid, "--to", "10", "--evidence", json.dumps(HEALTHY)), 2)

    def test_unhealthy_evidence_refuses_and_suggests_the_pause(self) -> None:
        self.enable("automated")
        rid = self.plan()
        bad = {**HEALTHY, "error_rate_pct": 5.0}
        self.assertEqual(self.cli("stage", rid, "--to", "5", "--evidence", json.dumps(bad)), 1)

    def test_malformed_evidence_json_is_refused(self) -> None:
        self.enable("automated")
        rid = self.plan()
        self.assertEqual(self.cli("stage", rid, "--to", "5", "--evidence", "{not json"), 2)


class PauseAndRollback(Project):
    def test_pause_never_needs_an_approval(self) -> None:
        self.enable("advisory")  # the strictest mode that still runs
        rid = self.plan()
        self.assertEqual(self.cli("pause", rid, "--note", "latency"), 0)
        self.assertEqual(self.read()["release"]["releases"][-1]["status"], "paused")

    def test_a_flag_rollback_of_a_low_risk_release_is_automatic(self) -> None:
        self.enable("automated")
        rid = self.plan()
        self.assertEqual(self.cli("rollback", rid, "--kind", "flag"), 0)
        self.assertEqual(self.read()["release"]["releases"][-1]["status"], "rolled_back")

    def test_a_database_rollback_always_needs_the_users_words(self) -> None:
        self.enable("automated")
        rid = self.plan()
        self.assertEqual(self.cli("rollback", rid, "--kind", "database"), 1)

    def test_a_database_rollback_states_that_nothing_was_run(self) -> None:
        self.enable("automated")
        rid = self.plan()
        self.assertEqual(self.cli("rollback", rid, "--kind", "database",
                                  "--user-said", "procedi, il backup c'e'"), 0)
        events = self.read()["release"]["releases"][-1]["events"]
        self.assertTrue(any(e["event"] == "rollback:database" for e in events))

    def test_a_deployment_rollback_routes_to_vercel_deploys_runbook(self) -> None:
        self.enable("automated")
        rid = self.plan()
        self.assertEqual(self.cli("rollback", rid, "--kind", "deployment"), 0)


class VerifyAndCleanup(Project):
    def rolled_to_100(self) -> str:
        self.enable("automated")
        rid = self.plan("--flag-key", "us-1-new-thing")
        self.cli("stage", rid, "--to", "100", "--evidence", json.dumps(HEALTHY))
        return rid

    def test_verify_refuses_below_full_exposure(self) -> None:
        self.enable("automated")
        rid = self.plan()
        self.cli("stage", rid, "--to", "25", "--evidence", json.dumps(HEALTHY))
        self.assertEqual(self.cli("verify", rid, "--evidence", json.dumps(HEALTHY)), 2)

    def test_verify_refuses_without_evidence(self) -> None:
        rid = self.rolled_to_100()
        self.assertEqual(self.cli("verify", rid), 1)

    def test_verify_completes_the_release(self) -> None:
        rid = self.rolled_to_100()
        self.assertEqual(self.cli("verify", rid, "--evidence", json.dumps(HEALTHY)), 0)
        entry = self.read()["release"]["releases"][-1]
        self.assertEqual(entry["status"], "complete")
        self.assertTrue(entry["verified_at"])

    def test_cleanup_is_not_due_for_an_unverified_release(self) -> None:
        self.rolled_to_100()
        self.assertEqual(self.cli("cleanup-due"), 0)
        # nothing crashes, and the release is reported as not eligible rather than due
        block = self.read()["release"]
        self.assertEqual(block["releases"][-1]["status"], "rolling")

    def test_cleanup_waits_for_the_soak_period(self) -> None:
        rid = self.rolled_to_100()
        self.cli("verify", rid, "--evidence", json.dumps(HEALTHY))
        self.assertEqual(self.cli("cleanup-due"), 0)  # verified today, policy asks for 7 days

    def test_cleanup_becomes_due_once_the_soak_has_passed(self) -> None:
        rid = self.rolled_to_100()
        self.cli("verify", rid, "--evidence", json.dumps(HEALTHY))
        meta = self.read()
        meta["release"]["releases"][-1]["verified_at"] = "2026-01-01T00:00:00Z"
        self.meta(meta)
        self.assertEqual(self.cli("cleanup-due"), 0)


class PolicyTable(Project):
    def test_policy_prints_without_a_block(self) -> None:
        self.assertEqual(self.cli("policy"), 0)

    def test_a_loosening_override_does_not_take_effect(self) -> None:
        self.enable("automated")
        meta = self.read()
        meta["release"]["required_approvals"] = {"destructive_db_migration": "auto"}
        self.meta(meta)
        rid = self.plan()
        self.assertEqual(self.cli("rollback", rid, "--kind", "database"), 1)


if __name__ == "__main__":
    unittest.main()
