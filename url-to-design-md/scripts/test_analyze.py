#!/usr/bin/env python3
"""Tests for analyze.py, against a page whose true values are written down.

The fixtures are two real snapshots of `fixtures/known-site.html`, captured at 1440 and 390 by the
real extractor in a real browser. Every expected number below is read off that HTML file, not off a
previous run of this code — a test that asserts what the code already does cannot catch anything.

Five of these exist because the code got them wrong first. Each of those says so, because a test
whose reason is forgotten is deleted by the next person who finds it inconvenient.
"""

from __future__ import annotations

import json
import unittest
from pathlib import Path

import analyze

HERE = Path(__file__).parent
FIXTURES = HERE / "fixtures"


def load(width):
    return json.loads((FIXTURES / f"snapshot-known-site-{width}.json").read_text())


class Colour(unittest.TestCase):
    def test_oklch_matches_the_reference_conversion(self):
        # Checked against the published OKLab matrices, not against our own output.
        self.assertEqual(analyze.to_oklch("#ffffff")[0], 1.0)
        self.assertEqual(analyze.to_oklch("#000000")[0], 0.0)
        l, c, h = analyze.to_oklch("#0b5fff")
        self.assertAlmostEqual(l, 0.5516, places=3)
        self.assertAlmostEqual(c, 0.2479, places=3)
        self.assertAlmostEqual(h, 262.15, places=1)

    def test_a_translucent_value_is_not_a_hex(self):
        self.assertIsNone(analyze.parse_hex("rgba(17, 24, 39, 0.06)"))
        self.assertIsNone(analyze.to_oklch("rgba(17, 24, 39, 0.06)"))

    def test_contrast_matches_the_wcag_formula(self):
        self.assertEqual(analyze.contrast("#ffffff", "#000000"), 21.0)
        self.assertEqual(analyze.wcag_grade(21.0), "AAA")
        self.assertEqual(analyze.wcag_grade(3.2), "fail")
        self.assertEqual(analyze.wcag_grade(3.2, large=True), "AA")


class Spacing(unittest.TestCase):
    def test_the_base_is_the_largest_step_that_still_explains_the_page(self):
        """Regression. The first version picked the base with the highest coverage, and 2 divides
        every even number, so it answered 2px for every site on earth — true and useless. The test
        page is a 4px system (it uses 6, 10, 12, 14), so 4 is the answer and 8 is not."""
        merged = analyze.merge_snapshots([load(1440), load(390)], "site")
        space = analyze.spacing_scale(merged, [])
        self.assertEqual(space["base"], 4)
        self.assertGreaterEqual(space["coverage"], 0.80)
        for value in (8, 12, 16, 24, 32, 48, 64):
            self.assertIn(value, space["onGrid"])

    def test_a_pure_eight_grid_is_read_as_eight(self):
        snap = load(1440)
        snap["spacing"] = {"padding": {"8": 10, "16": 10, "24": 10, "32": 10},
                           "margin": {"48": 5}, "gap": {"64": 5}}
        merged = analyze.merge_snapshots([snap], "site")
        self.assertEqual(analyze.spacing_scale(merged, [])["base"], 8)


class Typography(unittest.TestCase):
    def setUp(self):
        self.merged = analyze.merge_snapshots([load(1440), load(390)], "site")
        self.scale = analyze.type_scale(self.merged, [])

    def test_sizes_land_on_tailwind_slots_and_never_on_new_names(self):
        """The rule from contracts.md: redefine the slots shadcn's own primitives use, never add a
        parallel set of semantic names. The h1 is 72px at 1440, which is text-7xl."""
        slots = {s["slot"]: s for s in self.scale["slots"]}
        self.assertEqual(slots["text-7xl"]["size"], 72)
        self.assertEqual(slots["text-3xl"]["size"], 32)
        self.assertEqual(slots["text-base"]["size"], 16)
        self.assertEqual(slots["text-sm"]["size"], 14)
        known = {name for name, _ in analyze.TW_TEXT_SLOTS}
        for slot in self.scale["slots"]:
            self.assertIn(slot["slot"], known, "a name outside Tailwind's scale was invented")

    def test_the_two_viewports_produce_a_clamp_for_the_heading_only(self):
        """64px at 390 and 72px at 1440 is a responsive ramp; 16px at both is not, and emitting a
        clamp() for it would invent a behaviour the page does not have."""
        slots = {s["slot"]: s for s in self.scale["slots"]}
        self.assertEqual(slots["text-7xl"]["mobileSize"], 64)
        self.assertIsNotNone(slots["text-7xl"]["clamp"])
        self.assertIsNone(slots["text-base"]["clamp"])

    def test_a_scale_whose_steps_disagree_reports_no_ratio(self):
        """Regression. Averaging 2.25, 1.6, 1.25 and 1.143 produced 1.561 — a number that names no
        interval and describes nothing. A ratio is a fact only when the steps are uniform."""
        self.assertFalse(self.scale["uniform"])
        self.assertIsNone(self.scale["ratio"])
        self.assertIsNone(self.scale["nearestInterval"])
        self.assertIn("not uniform", self.scale["note"])

    def test_a_uniform_scale_is_named(self):
        rows = [{"family": "X", "size": s, "weight": "400", "lineHeight": s * 1.4,
                 "letterSpacing": 0, "chars": 100, "elements": 1, "tags": ["p"]}
                for s in (16, 20, 25, 31.25)]
        merged = {"typeByViewport": {1440: rows}}
        scale = analyze.type_scale(merged, [])
        self.assertTrue(scale["uniform"])
        self.assertEqual(scale["nearestInterval"], "major third")

    def test_near_identical_sizes_are_one_role(self):
        rows = [{"family": "X", "size": s, "weight": "400", "lineHeight": 24,
                 "letterSpacing": 0, "chars": 50, "elements": 1, "tags": ["p"]}
                for s in (16, 17, 17.6, 20)]
        clusters = analyze.cluster_sizes(rows)
        self.assertEqual(len(clusters), 2, "16/17/17.6 is one role, 20 is another")


class ColourRoles(unittest.TestCase):
    def setUp(self):
        self.merged = analyze.merge_snapshots([load(1440), load(390)], "site")
        self.missing = []
        self.roles = analyze.colour_roles(self.merged, self.missing)

    def test_every_role_matches_the_value_written_in_the_fixture(self):
        expected = {
            "background": "#ffffff", "foreground": "#374151", "card": "#f9fafb",
            "primary": "#0069e8", "primary-foreground": "#ffffff",
            "border": "#e5e7eb", "ring": "#0b5fff",
        }
        for role, value in expected.items():
            self.assertEqual(self.roles.get(role, {}).get("value"), value, f"role {role}")

    def test_the_primary_is_the_oklch_the_canvas_resolved(self):
        """Regression. `oklch(0.55 0.21 258)` came back unconverted because reading ctx.fillStyle
        round-trips CSS Color 4. Only painting the pixel resolves it, and #0069e8 is the proof."""
        self.assertEqual(self.roles["primary"]["value"], "#0069e8")
        self.assertIn("button", self.roles["primary"]["why"])

    def test_the_border_is_the_grey_and_not_the_headers_text_colour(self):
        """Regression. borderTopColor is defined even when borderTopWidth is 0, where it falls back
        to the element's `color`. The header has only a bottom border, so its #111827 text was
        recorded as a 1440px-wide border and outvoted the real #e5e7eb."""
        self.assertEqual(self.roles["border"]["value"], "#e5e7eb")

    def test_the_focus_ring_is_the_authored_one_and_not_the_browsers(self):
        """Regression, twice. Every focusable element reports an outline because the browser draws
        its own when the page does not — #e59700 here, the OS accent. The page declares
        `input:focus-visible`, so the input's ring is the site's and the button's is not."""
        self.assertEqual(self.roles["ring"]["value"], "#0b5fff")

    def test_a_page_that_authors_no_focus_rule_gets_no_ring(self):
        stripped = [dict(s) for s in (load(1440), load(390))]
        for s in stripped:
            s["states"] = dict(s["states"], focusDeclared=[])
        merged = analyze.merge_snapshots(stripped, "site")
        missing = []
        roles = analyze.colour_roles(merged, missing)
        self.assertNotIn("ring", roles)
        self.assertTrue(any("browser default" in m for m in missing))

    def test_unobserved_slots_are_named_and_never_filled(self):
        for slot in ("destructive", "popover", "accent"):
            self.assertNotIn(slot, self.roles)
            self.assertTrue(any(m.startswith(slot) for m in self.missing))


class Questions(unittest.TestCase):
    def setUp(self):
        self.merged = analyze.merge_snapshots([load(1440), load(390)], "site")
        self.tokens = analyze.build_tokens(self.merged)

    def test_no_contest_is_raised_over_a_role_the_document_decided(self):
        """Regression, and the worst kind this file can hold. `background` comes from the document's
        own computed background, not from the area-weighted palette — so comparing the two heaviest
        painted colours described a contest that never happened and asked the user to 'fix' a role
        that was already right. A questionnaire that invents doubt gets switched off exactly as fast
        as one that hides it."""
        self.assertEqual(self.tokens["color"]["roles"]["background"]["value"], "#ffffff")
        self.assertIn("document background", self.tokens["color"]["roles"]["background"]["why"])
        ids = [q["id"] for q in self.tokens["questions"]]
        self.assertNotIn("close:background", ids)

    def test_every_question_carries_evidence_options_and_a_default(self):
        """The default is the one that matters: a question that quietly did something is worse than
        no question."""
        self.assertTrue(self.tokens["questions"])
        for q in self.tokens["questions"]:
            self.assertTrue(q["evidence"], q["id"])
            self.assertGreaterEqual(len(q["options"]), 2, q["id"])
            self.assertTrue(q["default"], q["id"])

    def test_resolving_a_condition_removes_its_question(self):
        before = [q["id"] for q in self.tokens["questions"]]
        self.assertIn("missing:slots", before)
        cleared = dict(self.tokens, missing=[])
        after = [q["id"] for q in analyze.open_questions(cleared, self.merged)]
        self.assertNotIn("missing:slots", after)


class Components(unittest.TestCase):
    def setUp(self):
        self.merged = analyze.merge_snapshots([load(1440), load(390)], "site")
        self.tokens = analyze.build_tokens(self.merged)

    def test_the_button_painted_on_a_child_was_found(self):
        """The CTA's paint is on a span inside the <a>. An extractor that reads the anchor finds no
        background and no radius, which is the commonest way to miss a site's primary action."""
        self.assertTrue(self.tokens["components"]["button"]["paintedOnChild"])

    def test_the_pill_radius_is_distinguished_from_the_px_radius(self):
        self.assertTrue(self.tokens["radius"]["pill"])
        self.assertEqual(self.tokens["radius"]["default"], 12.0)

    def test_motion_is_read_from_the_controls(self):
        motion = self.tokens["motion"]
        self.assertEqual(motion["durations"][0][0], 180)
        self.assertIn("cubic-bezier(0.2, 0, 0, 1)", motion["easings"][0][0])

    def test_the_container_and_the_breakpoints_are_the_declared_ones(self):
        self.assertEqual(self.tokens["layout"]["container"], 1280.0)
        self.assertEqual([b["px"] for b in self.tokens["layout"]["breakpoints"]], [768, 1024])

    def test_the_cross_origin_stylesheet_is_reported_not_dropped(self):
        """A channel that could not be read must never look like a channel that said nothing."""
        self.assertTrue(any("cross-origin" in n for n in self.tokens["notes"]))


class Privacy(unittest.TestCase):
    def test_app_mode_keeps_no_strings(self):
        """A signed-in app shows customer names and invoice numbers. The shape of the text is what
        the voice rules are derived from; the strings themselves must not reach the snapshot."""
        snap = load(1440)
        self.assertTrue(snap["text"]["samples"], "site mode does keep samples")
        app = dict(snap, mode="app")
        app["text"] = dict(app["text"], samples=[])
        merged = analyze.merge_snapshots([app], "app")
        voice = analyze.voice(merged, [])
        self.assertEqual(voice["quotes"], [])
        self.assertIsNotNone(voice["stats"]["headingWords"])
        self.assertTrue(voice["rules"])

    def test_the_consent_banner_never_reached_the_measurement(self):
        """#22c55e is the Accept-all button's green and it exists only inside the banner. If it is
        in the palette, the whole measurement is of a third party's design sitting on the brand's."""
        snap = load(1440)
        self.assertGreaterEqual(snap["counts"]["skippedConsent"], 2)
        for group in snap["colors"].values():
            for row in group:
                self.assertNotIn(row["value"], ("#22c55e", "#052e16", "#1f2937"))


class ModeDifference(unittest.TestCase):
    def test_site_mode_dedupes_repeated_chrome_and_app_mode_does_not(self):
        """The same rule, opposite outcomes. On a site the header repeats on every page and would
        outvote the content; in an app the sidebar IS the product and deduplicating it throws away
        the thing the run was for."""
        a, b = load(1440), dict(load(1440), path="/second")
        site = analyze.merge_snapshots([a, b], "site")
        app = analyze.merge_snapshots([dict(a, mode="app"), dict(b, mode="app")], "app")
        repeated = next(r for r in site["colors"]["background"] if r["pages"] == 2)
        same_in_app = next(r for r in app["colors"]["background"] if r["value"] == repeated["value"])
        self.assertLess(repeated["weight"], same_in_app["weight"])


class Outputs(unittest.TestCase):
    def setUp(self):
        merged = analyze.merge_snapshots([load(1440), load(390)], "site")
        self.tokens = analyze.build_tokens(merged)

    def test_the_shadcn_theme_lists_what_it_did_not_observe(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "shadcn.css"
            analyze.write_shadcn(self.tokens, path)
            css = path.read_text()
        self.assertIn("NOT OBSERVED", css)
        self.assertIn("--primary: oklch(", css)
        self.assertNotIn("--destructive:", css, "an unobserved slot must not be written")
        self.assertIn("@theme inline", css)

    def test_every_token_carries_the_evidence_that_chose_it(self):
        for name, role in self.tokens["color"]["roles"].items():
            self.assertTrue(role.get("why"), f"{name} has no evidence")
            self.assertIn("confidence", role)


if __name__ == "__main__":
    unittest.main(verbosity=2)
