"""release_gate.py: it must be invisible on every project that did not opt in, and unbypassable on
the ones that did.

The first test is the load-bearing one. `release-intelligence` is an optional capability, and the way
an optional capability goes wrong is by quietly changing the projects that never asked for it — so the
gate is checked against a meta.json with no `release` field, with a null one, and with the capability
explicitly disabled. All three must pass without reading anything else.

    cd dev-flow/scripts && python3 -m unittest test_release_gate -v
"""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import release_gate  # noqa: E402

APPROVED = {"required": True, "granted_by_user": True, "quote": "vai", "at": "2026-11-06T10:00:00Z"}


def rel(**kw) -> dict:
    base = {"id": "REL-1", "environment": "production", "risk": "low",
            "approval": {"required": False, "granted_by_user": False, "quote": None},
            "rollout": {"current_percent": 0}}
    base.update(kw)
    return base


def meta(**kw) -> dict:
    return {"phase": "feature_complete", **kw}


def enabled(*releases, **block) -> dict:
    return meta(release={"enabled": True, "autonomy": "assisted", "releases": list(releases), **block})


class Root(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def verify(self, m: dict) -> tuple[bool, str]:
        return release_gate.verify(self.root, m)


class OptedOutProjectsAreUntouched(Root):
    def test_no_release_field_at_all_passes(self) -> None:
        passed, why = self.verify(meta())
        self.assertTrue(passed)
        self.assertIn("not enabled", why)

    def test_a_null_release_field_passes(self) -> None:
        self.assertTrue(self.verify(meta(release=None))[0])

    def test_an_explicitly_disabled_capability_passes(self) -> None:
        self.assertTrue(self.verify(meta(release={"enabled": False, "releases": []}))[0])

    def test_applies_is_false_without_the_field(self) -> None:
        self.assertFalse(release_gate.applies(meta()))

    def test_applies_is_true_once_enabled(self) -> None:
        self.assertTrue(release_gate.applies(enabled()))

    def test_a_block_that_is_not_an_object_is_checked_not_ignored(self) -> None:
        """A hand-edited `release` must not become a bypass by being unreadable."""
        self.assertTrue(release_gate.applies(meta(release="enabled, trust me")))
        passed, why = self.verify(meta(release="enabled, trust me"))
        self.assertFalse(passed)
        self.assertIn("edited by hand", why)


class ManifestRequired(Root):
    def test_enabled_with_no_manifest_is_refused(self) -> None:
        passed, why = self.verify(enabled())
        self.assertFalse(passed)
        self.assertIn("no Release Manifest", why)

    def test_a_manifest_for_another_environment_does_not_cover_production(self) -> None:
        passed, _ = self.verify(enabled(rel(environment="preview")))
        self.assertFalse(passed)

    def test_a_manifest_without_an_environment_counts_as_production(self) -> None:
        m = enabled({"id": "REL-1", "risk": "low", "rollout": {"current_percent": 100}})
        self.assertTrue(self.verify(m)[0])

    def test_releases_not_being_a_list_is_refused(self) -> None:
        passed, why = self.verify(meta(release={"enabled": True, "releases": "none"}))
        self.assertFalse(passed)
        self.assertIn("not a list", why)


class ApprovalWhereTheRiskAsksForIt(Root):
    def test_a_low_risk_release_needs_no_approval(self) -> None:
        self.assertTrue(self.verify(enabled(rel(risk="low")))[0])

    def test_a_medium_risk_release_needs_no_approval_at_this_gate(self) -> None:
        """The policy table may still ask for one to advance a stage; the phase crossing does not."""
        self.assertTrue(self.verify(enabled(rel(risk="medium")))[0])

    def test_a_high_risk_release_without_an_approval_is_refused(self) -> None:
        passed, why = self.verify(enabled(rel(risk="high")))
        self.assertFalse(passed)
        self.assertIn("nobody has approved it", why)

    def test_a_critical_release_without_an_approval_is_refused(self) -> None:
        self.assertFalse(self.verify(enabled(rel(risk="critical")))[0])

    def test_an_approved_high_risk_release_passes_and_the_quote_is_in_the_message(self) -> None:
        passed, why = self.verify(enabled(rel(risk="high", approval=APPROVED)))
        self.assertTrue(passed)
        self.assertIn("vai", why)

    def test_approved_with_no_quote_is_refused(self) -> None:
        passed, why = self.verify(enabled(rel(
            risk="high", approval={"required": True, "granted_by_user": True, "quote": ""})))
        self.assertFalse(passed)
        self.assertIn("approving itself", why)

    def test_approved_with_a_whitespace_quote_is_refused(self) -> None:
        self.assertFalse(self.verify(enabled(rel(
            risk="high", approval={"granted_by_user": True, "quote": "   "})))[0])

    def test_a_truthy_non_true_approval_flag_is_not_an_approval(self) -> None:
        """`"granted_by_user": "yes"` is a hand edit, and `is True` is why it does not pass."""
        self.assertFalse(self.verify(enabled(rel(
            risk="critical", approval={"granted_by_user": "yes", "quote": "ok"})))[0])

    def test_an_unknown_risk_level_is_refused_rather_than_waved_through(self) -> None:
        passed, why = self.verify(enabled(rel(risk="fine")))
        self.assertFalse(passed)
        self.assertIn("not a level this gate knows", why)

    def test_a_missing_risk_level_is_refused(self) -> None:
        m = enabled({"id": "REL-1", "environment": "production"})
        self.assertFalse(self.verify(m)[0])


class DestructiveMigrations(Root):
    def test_a_destructive_migration_without_a_quote_names_the_hazard(self) -> None:
        passed, why = self.verify(enabled(rel(risk="critical", destructive_migration=True)))
        self.assertFalse(passed)
        self.assertIn("approved", why.lower())

    def test_an_approved_destructive_migration_passes_and_says_so(self) -> None:
        passed, _ = self.verify(enabled(rel(risk="critical", destructive_migration=True,
                                            approval=APPROVED)))
        self.assertTrue(passed)


class TheNewestProductionReleaseDecides(Root):
    def test_an_older_approved_release_does_not_cover_a_newer_unapproved_one(self) -> None:
        m = enabled(rel(id="REL-1", risk="high", approval=APPROVED),
                    rel(id="REL-2", risk="critical"))
        passed, why = self.verify(m)
        self.assertFalse(passed)
        self.assertIn("REL-2", why)

    def test_a_newer_approved_release_is_what_is_read(self) -> None:
        m = enabled(rel(id="REL-1", risk="critical"),
                    rel(id="REL-2", risk="high", approval=APPROVED))
        self.assertTrue(self.verify(m)[0])


class Remedy(Root):
    def test_the_remedy_offers_the_plan_the_approval_and_the_opt_out(self) -> None:
        text = release_gate.remedy(self.root)
        self.assertIn("plan", text)
        self.assertIn("approve", text)
        self.assertIn("disable", text)


if __name__ == "__main__":
    unittest.main()
