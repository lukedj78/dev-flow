#!/usr/bin/env python3
"""Tests for the guide, the decision pages and the gate.

The security half of this file is not hypothetical. This skill's entire job is to read somebody
else's page and paste what it finds into HTML we hand to the user: a font family, a custom-property
name, a CTA label. Those are attacker-controlled strings by construction, and both escapes below
were missing in the first version.
"""

from __future__ import annotations

import json
import re
import tempfile
import unittest
from pathlib import Path

import analyze
import render_decision
import render_guide
import verify

HERE = Path(__file__).parent
FIXTURES = HERE / "fixtures"


def tokens():
    snaps = [json.loads((FIXTURES / f"snapshot-known-site-{w}.json").read_text())
             for w in (1440, 390)]
    return analyze.build_tokens(analyze.merge_snapshots(snaps, "site"))


class HostileInput(unittest.TestCase):
    """A measured page that wants out of the document it is measured into."""

    def setUp(self):
        self.t = tokens()

    def render(self):
        return render_guide.render(self.t, "Hostile")

    def test_a_font_family_cannot_close_the_style_element(self):
        """`font-family` is serialised by the browser WITH quotes, so `"</style><script>"` is a
        valid CSS value — and the HTML parser ends the element at `</style>` anyway."""
        self.t["typography"]["families"] = ["</style><script>alert(1)</script>", "Inter"]
        html = self.render()
        self.assertEqual(html.count("</style>"), 1)
        style = re.search(r"<style>(.*?)</style>", html, re.S).group(1)
        self.assertNotIn("</style", style)
        self.assertIn("\\3c /style", style)

    def test_a_value_that_opens_its_own_rule_is_refused_and_named(self):
        """Dropping it silently would read as `not observed`, which is a different fact."""
        self.t["shadows"] = ["0 1px 2px red; } body { display:none } .x {"]
        html = self.render()
        style = re.search(r"<style>(.*?)</style>", html, re.S).group(1)
        self.assertIn("refused as unsafe", style)
        self.assertNotIn("display:none", style)

    def test_a_token_value_cannot_close_the_script_element(self):
        self.t["declaredCustomProperties"]["--evil"] = "</script><script>alert(1)</script>"
        html = self.render()
        blob = re.search(r'id="tokens-json">(.*?)</script>', html, re.S).group(1)
        self.assertNotIn("</script", blob)
        self.assertIn("\\u003c", blob)
        self.assertEqual(html.count('id="tokens-json">'), 1)

    def test_a_cta_label_cannot_inject_an_attribute(self):
        voice = self.t.get("voice")
        if not voice:
            self.skipTest("no voice on this fixture")
        voice["quotes"] = [{"kind": "cta", "text": '"><img src=x onerror=alert(1)>'}]
        html = self.render()
        # The characters survive as text, which is correct and harmless. What must not survive is a
        # TAG: no unescaped `<img`, and no attribute boundary opened by the quote.
        self.assertNotIn("<img", html)
        self.assertIn("&lt;img", html)
        self.assertNotIn('"><img', html)

    def test_the_header_logo_cannot_inject_a_tag(self):
        """The third instance of the same class, and the one that proved the sweep was needed: the
        logo line built its HTML by concatenating str() calls, so a measured colour or size went in
        raw. Found by the review after two sibling fixes had already landed."""
        comps = self.t["components"]
        comps["header"] = {"height": 72, "sticky": True,
                           "logo": {"tag": "img", "width": '"><img src=x onerror=alert(1)>',
                                    "height": 28, "color": "</span><script>alert(2)</script>"}}
        html = self.render()
        self.assertNotIn("<img src=x", html)
        self.assertNotIn("<script>alert(2)", html)
        self.assertIn("&lt;img", html)

    def test_the_decision_page_is_escaped_too(self):
        """render_decision reuses render_guide's :root, so it inherits the fix — this proves it
        rather than assuming it."""
        self.t["typography"]["families"] = ["</style><script>alert(1)</script>"]
        page = render_decision.render(self.t, "contrast", "muted-foreground",
                                      "#9ca3af", "#707782", "q")
        self.assertEqual(page.count("</style>"), 1)


class DownstreamInput(unittest.TestCase):
    """The DESIGN.md is read by another agent. A value that breaks out of its scalar is not a
    rendering bug there, it is an instruction."""

    def test_a_font_family_cannot_open_a_yaml_key(self):
        import make_design_md
        hostile = 'Inter"\nmalicious: "injected'
        out = make_design_md.yaml_scalar(hostile)
        self.assertNotIn("\n", out)
        self.assertTrue(out.startswith('"') and out.endswith('"'))

    def test_control_characters_are_stripped(self):
        import make_design_md
        self.assertNotIn("\x00", make_design_md.yaml_scalar("a\x00b"))
        self.assertNotIn("\x1b", make_design_md.yaml_scalar("a\x1b[31mb"))

    def test_a_plain_value_stays_unquoted(self):
        import make_design_md
        self.assertEqual(make_design_md.yaml_scalar("Inter"), "Inter")
        self.assertEqual(make_design_md.yaml_scalar("#0b5fff"), '"#0b5fff"')


class DecisionPaths(unittest.TestCase):
    def test_the_token_name_cannot_escape_the_output_directory(self):
        """`--token ../../x` would write outside --out, in a tool whose job is to be pointed at
        untrusted material."""
        import re as _re
        scrubbed = _re.sub(r"[^A-Za-z0-9._-]+", "-", "../../etc/passwd")[:60].strip("-.")
        self.assertNotIn("/", scrubbed)
        self.assertFalse(scrubbed.startswith("."))


class Guide(unittest.TestCase):
    def setUp(self):
        self.t = tokens()
        self.html = render_guide.render(self.t, "Known Site")

    def test_the_guide_holds_no_literal_colour_outside_root(self):
        """The rule the whole loop rests on: move a token, the page changes. One literal and it
        silently stops being true."""
        style = re.search(r"<style>(.*?)</style>", self.html, re.S).group(1)
        rules = re.sub(r":root\s*\{.*?\}", "", style, flags=re.S)
        literals = re.findall(r"(?<!-)\b(?:background|color|border-radius)\s*:\s*(#[0-9a-fA-F]{3,8})\s*[;}]",
                              rules)
        self.assertEqual(literals, [], "a hard-coded colour breaks the regenerate loop")

    def test_the_rebuild_controls_are_present_for_the_gate(self):
        for control in ("button", "button-secondary", "card", "input"):
            self.assertIn(f'data-rebuild="{control}"', self.html)

    def test_the_unofficial_label_is_on_bar_cover_and_footer(self):
        self.assertGreaterEqual(self.html.count("Unofficial analysis"), 3)

    def test_the_review_band_asks_what_the_measurement_raised(self):
        self.assertIn('id="review"', self.html)
        self.assertIn("to decide", self.html)
        for q in self.t["questions"]:
            self.assertIn("If you say nothing", self.html)
            break

    def test_an_answered_question_disappears_from_the_band(self):
        """The questions are conditions, not a checklist: resolving one removes it."""
        before = len(self.t["questions"])
        ground = self.t["color"]["roles"]["background"]["value"]
        grey = self.t["color"]["roles"]["muted-foreground"]["value"]
        fixed, ratio = analyze.adjust_for_contrast(grey, ground, 4.5)
        self.t["color"]["roles"]["muted-foreground"]["value"] = fixed
        for c in self.t["contrast"]:
            if c["pair"].startswith("muted-foreground"):
                c["ratio"], c["grade"] = ratio, analyze.wcag_grade(ratio)
        snaps = [json.loads((FIXTURES / f"snapshot-known-site-{w}.json").read_text())
                 for w in (1440, 390)]
        merged = analyze.merge_snapshots(snaps, "site")
        after = analyze.open_questions(self.t, merged)
        self.assertLess(len(after), before)
        self.assertFalse(any(q["id"].startswith("contrast:") for q in after))

    def test_the_js_gate_keeps_the_page_readable_without_script(self):
        """`.reveal { opacity: 0 }` ungated means a blank page when the script fails — and it would
        still pass an 'opens offline with no requests' check."""
        style = re.search(r"<style>(.*?)</style>", self.html, re.S).group(1)
        self.assertIn(".js .reveal", style)
        self.assertNotIn("\n  .reveal {", style)


class Contrast(unittest.TestCase):
    def test_darkening_holds_hue_and_chroma(self):
        """Darkening in sRGB turns a blue-grey into a different colour. The user asked for the same
        colour with less light."""
        fixed, ratio = analyze.adjust_for_contrast("#9ca3af", "#ffffff", 4.5)
        self.assertGreaterEqual(ratio, 4.5)
        before, after = analyze.to_oklch("#9ca3af"), analyze.to_oklch(fixed)
        self.assertLess(after[0], before[0], "it must get darker")
        self.assertAlmostEqual(after[1], before[1], delta=0.01, msg="chroma moved")
        self.assertAlmostEqual(after[2], before[2], delta=3.0, msg="hue moved")

    def test_an_unreachable_target_returns_none_rather_than_a_different_colour(self):
        """A mid grey ground caps the achievable contrast at about 5:1 whichever way you move, so
        21 cannot be reached. (White ON white CAN reach it — by going to black — which is why that
        is not the case to test.)"""
        fixed, best = analyze.adjust_for_contrast("#808080", "#808080", 21.0)
        self.assertIsNone(fixed)
        self.assertIsNotNone(best)
        self.assertLess(best, 21.0)

    def test_it_lightens_on_a_dark_ground(self):
        fixed, ratio = analyze.adjust_for_contrast("#555555", "#111111", 4.5)
        self.assertIsNotNone(fixed)
        self.assertGreater(analyze.to_oklch(fixed)[0], analyze.to_oklch("#555555")[0])


class Gate(unittest.TestCase):
    def test_an_unrun_in_page_check_fails_rather_than_being_skipped(self):
        """A verification that was not obtained must never look like one that passed."""
        t = tokens()
        with tempfile.TemporaryDirectory() as d:
            guide = Path(d) / "brand-guide.html"
            guide.write_text(render_guide.render(t, "Known Site"), encoding="utf-8")
            res = verify.Result()
            verify.static_checks(guide, False, res)
            verify.inpage_checks(Path(d) / "missing.json", t, res)
        failed = [c["check"] for c in res.failed]
        self.assertIn("in-page checks were obtained", failed)

    def test_a_guide_with_a_literal_fails_the_static_gate(self):
        t = tokens()
        html = render_guide.render(t, "X").replace(
            "  .swatch {", "  .injected { background: #ff0000; }\n  .swatch {")
        with tempfile.TemporaryDirectory() as d:
            guide = Path(d) / "g.html"
            guide.write_text(html, encoding="utf-8")
            res = verify.Result()
            verify.static_checks(guide, False, res)
        self.assertIn("the stylesheet holds no literal colour outside :root",
                      [c["check"] for c in res.failed])

    def test_an_external_reference_fails_the_offline_check(self):
        t = tokens()
        html = render_guide.render(t, "X").replace(
            "</head>", '<link rel="stylesheet" href="https://fonts.example/x.css"></head>')
        with tempfile.TemporaryDirectory() as d:
            guide = Path(d) / "g.html"
            guide.write_text(html, encoding="utf-8")
            res = verify.Result()
            verify.static_checks(guide, False, res)
        self.assertIn("opens offline, no external reference", [c["check"] for c in res.failed])


if __name__ == "__main__":
    unittest.main(verbosity=2)
