"""policy.py: the two asymmetries, and the fact that a config file is not an authorisation.

The table itself is boring to test row by row; what is worth a test is every way the table could be
made to say `auto` when it must not — an unknown risk level, an unreadable autonomy mode, a project
config asking for more freedom, and the two rows whose verdict no mode may change.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import policy  # noqa: E402


class Asymmetries(unittest.TestCase):
    def test_pausing_is_auto_in_every_mode(self) -> None:
        for mode in ("advisory", "assisted", "automated"):
            for risk in policy.RISKS:
                self.assertEqual(policy.decide("rollout_pause", risk, mode), "auto",
                                 f"{mode}/{risk}: a pause that waits for a human is not a safety control")

    def test_aborting_is_auto_in_every_mode(self) -> None:
        self.assertEqual(policy.decide("rollout_abort", "critical", "advisory"), "auto")

    def test_a_destructive_migration_is_never_auto(self) -> None:
        for mode in ("advisory", "assisted", "automated"):
            for risk in policy.RISKS:
                self.assertNotEqual(policy.decide("destructive_db_migration", risk, mode), "auto",
                                    f"{mode}/{risk}")

    def test_deleting_a_flag_is_never_auto(self) -> None:
        self.assertNotEqual(policy.decide("flag_delete", "low", "automated"), "auto")

    def test_changing_production_data_is_never_auto(self) -> None:
        self.assertNotEqual(policy.decide("production_data_change", "low", "automated"), "auto")


class Modes(unittest.TestCase):
    def test_disabled_executes_nothing(self) -> None:
        self.assertEqual(policy.decide("flag_create", "low", "disabled"), "never")

    def test_disabled_still_allows_reading(self) -> None:
        """Risk assessment writes nothing; refusing it would make the disabled mode useless for advice."""
        self.assertEqual(policy.decide("risk_assessment", "critical", "disabled"), "auto")

    def test_advisory_prepares_nothing(self) -> None:
        self.assertEqual(policy.decide("flag_create", "low", "advisory"), "recommend")

    def test_assisted_prepares_and_asks(self) -> None:
        self.assertEqual(policy.decide("flag_create", "low", "assisted"), "approval")

    def test_automated_runs_low_risk_only(self) -> None:
        self.assertEqual(policy.decide("rollout_advance", "low", "automated"), "auto")
        self.assertEqual(policy.decide("rollout_advance", "medium", "automated"), "approval")

    def test_a_flag_rollback_is_auto_up_to_medium_because_it_is_cheap_to_undo(self) -> None:
        self.assertEqual(policy.decide("flag_rollback", "medium", "automated"), "auto")
        self.assertEqual(policy.decide("flag_rollback", "high", "automated"), "approval")

    def test_an_unreadable_mode_is_the_cautious_one(self) -> None:
        self.assertEqual(policy.decide("flag_create", "low", "YOLO"), "recommend")

    def test_an_unknown_risk_reads_as_critical(self) -> None:
        self.assertEqual(policy.decide("rollout_advance", "unknown-level", "automated"), "approval")


class Overrides(unittest.TestCase):
    def test_a_project_may_tighten(self) -> None:
        self.assertEqual(
            policy.decide("rollout_advance", "low", "automated", {"rollout_advance": "approval"}),
            "approval")

    def test_a_project_may_not_loosen(self) -> None:
        self.assertEqual(
            policy.decide("destructive_db_migration", "critical", "automated",
                          {"destructive_db_migration": "auto"}),
            "approval")

    def test_a_loosening_override_is_reported_not_silent(self) -> None:
        msg = policy.override_ignored("destructive_db_migration", "critical", "automated",
                                      {"destructive_db_migration": "auto"})
        self.assertIsNotNone(msg)
        self.assertIn("not an authorisation", msg)

    def test_a_nonsense_override_is_reported(self) -> None:
        msg = policy.override_ignored("flag_create", "low", "assisted", {"flag_create": "sure"})
        self.assertIsNotNone(msg)
        self.assertIn("not one of", msg)

    def test_a_tightening_override_is_not_reported_as_ignored(self) -> None:
        self.assertIsNone(policy.override_ignored("rollout_advance", "low", "automated",
                                                  {"rollout_advance": "approval"}))


class Rendering(unittest.TestCase):
    def test_explain_names_the_never_automated_rule(self) -> None:
        self.assertIn("never automated", policy.explain("destructive_db_migration", "low", "automated"))

    def test_the_table_covers_every_action_and_risk(self) -> None:
        t = policy.table("automated")
        for a in list(policy.READ_ONLY) + list(policy.ALWAYS_AUTO) + list(policy.NEVER_AUTO):
            self.assertIn(f"`{a}`", t)
        self.assertIn("| low | medium | high | critical |", t)


if __name__ == "__main__":
    unittest.main()
