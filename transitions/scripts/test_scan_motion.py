"""Unit tests for scan_motion — the motion-audit heuristics.

classify_line() and missing_reduced_motion() are pure; scan() is the I/O layer
exercised by the smoke tests.
"""
import tempfile
import unittest
from pathlib import Path

from scan_motion import classify_line, missing_reduced_motion, scan


class TestClassifyLine(unittest.TestCase):
    def test_clean_line(self):
        self.assertIsNone(classify_line('<div className="flex gap-2">'))

    def test_tokenized_line_is_clean(self):
        # references a CSS var, not a magic number → not flagged
        self.assertIsNone(classify_line('className="duration-[var(--motion-duration-base)]"'))

    def test_magic_duration_tailwind(self):
        self.assertEqual(classify_line('className="transition duration-[237ms]"'), "magic-duration")

    def test_magic_duration_css(self):
        self.assertEqual(classify_line("  transition-duration: 300ms;"), "magic-duration")

    def test_inline_cubic_bezier(self):
        self.assertEqual(classify_line("transition: transform 200ms cubic-bezier(0.2,0,0,1);"), "inline-easing")

    def test_inline_ease_arbitrary(self):
        self.assertEqual(classify_line('className="ease-[cubic-bezier(0.4,0,1,1)]"'), "inline-easing")

    def test_transition_all(self):
        self.assertEqual(classify_line('className="transition-all duration-200"'), "transition-all")

    def test_layout_prop_transition(self):
        self.assertEqual(classify_line("  transition: width 200ms ease;"), "layout-prop-anim")

    def test_first_match_wins_transition_all_before_duration(self):
        # transition-all is the more important smell; rule order puts it first
        self.assertEqual(classify_line('className="transition-all duration-[500ms]"'), "transition-all")


class TestMissingReducedMotion(unittest.TestCase):
    def test_no_animation_no_finding(self):
        self.assertFalse(missing_reduced_motion('<div className="flex gap-2">plain</div>'))

    def test_animation_without_fallback_flags(self):
        self.assertTrue(missing_reduced_motion('<div className="animate-in fade-in">x</div>'))

    def test_animation_with_motion_reduce_ok(self):
        self.assertFalse(missing_reduced_motion('<div className="animate-in fade-in motion-reduce:animate-none">x</div>'))

    def test_animation_with_media_query_ok(self):
        css = "@keyframes shake { from {} to {} }\n@media (prefers-reduced-motion: reduce) { .shake { animation: none } }"
        self.assertFalse(missing_reduced_motion(css))

    def test_motion_react_without_usereducedmotion_flags(self):
        self.assertTrue(missing_reduced_motion('import { motion } from "motion/react"\nanimate={{ opacity: 1 }}'))

    def test_motion_react_with_usereducedmotion_ok(self):
        self.assertFalse(missing_reduced_motion('import { useReducedMotion } from "motion/react"\nanimate={{ opacity: 1 }}'))


class TestScanSmoke(unittest.TestCase):
    def _cats(self, findings):
        return {f["category"] for f in findings}

    def test_scan_flags_magic_and_missing_rm(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "Card.tsx").write_text('export const C = () =>\n <div className="animate-in fade-in duration-[237ms]">x</div>')
            cats = self._cats(scan(root))
            self.assertIn("magic-duration", cats)
            self.assertIn("no-reduced-motion", cats)

    def test_scan_clean_tokenized_file_has_no_findings(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "Ok.tsx").write_text(
                'export const C = () =>\n'
                ' <div className="animate-in fade-in duration-[var(--motion-duration-base)] motion-reduce:animate-none">x</div>')
            self.assertEqual(scan(root), [])

    def test_scan_skips_node_modules(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            nm = root / "node_modules" / "pkg"
            nm.mkdir(parents=True)
            (nm / "a.tsx").write_text('className="duration-[999ms]"')
            self.assertEqual(scan(root), [])

    def test_scan_flags_tier3_import(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "M.tsx").write_text('import { motion } from "motion/react"\n<motion.div animate={{opacity:1}} className="motion-reduce:animate-none"/>')
            self.assertIn("tier3-import-review", self._cats(scan(root)))

    # ── precision: what the scan must NOT report ─────────────────────────────
    # Each of these was a real false positive from the first run against a live
    # project, where forty preset files and the token layer itself buried six
    # authored hits.

    def test_tokenized_easing_is_not_an_inline_easing(self):
        """`ease-[var(--motion-ease-*)]` is the form this skill asks for."""
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "a.tsx").write_text(
                'className="animate-in ease-[var(--motion-ease-standard)] motion-reduce:animate-none"')
            self.assertNotIn("inline-easing", self._cats(scan(root)))

    def test_literal_arbitrary_easing_is_still_flagged(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "a.tsx").write_text(
                'className="animate-in ease-[cubic-bezier(.17,.67,.83,.67)] motion-reduce:animate-none"')
            self.assertIn("inline-easing", self._cats(scan(root)))

    def test_token_definition_line_is_not_a_smell(self):
        """The CSS-var bridge is where the beziers legitimately live."""
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "globals.css").write_text(
                ":root { --motion-ease-standard: cubic-bezier(0.2, 0, 0, 1); "
                "--motion-duration-base: 200ms; }")
            self.assertEqual(scan(root), [])

    def test_reduced_motion_guard_is_not_a_magic_duration(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "globals.css").write_text(
                "@media (prefers-reduced-motion: reduce) { * { transition-duration: 0.01ms !important; } }")
            self.assertNotIn("magic-duration", self._cats(scan(root)))

    def test_importing_the_library_counts_as_guarded(self):
        """A file composing its classes from the tokenized library inherits the
        library's `motion-reduce:` fallbacks; file-level detection cannot see
        through an imported string, so the import is the evidence."""
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "Card.tsx").write_text(
                'import { hoverLift } from "@/lib/motion/transitions";\n'
                'export const C = () => <div className={hoverLift}>x</div>;')
            self.assertNotIn("no-reduced-motion", self._cats(scan(root)))

    # ── provenance: ranking, so an audit stays readable ─────────────────────

    def test_provenance_separates_vendored_from_authored(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "components" / "ui").mkdir(parents=True)
            (root / "components" / "ui" / "button.tsx").write_text('className="transition-all"')
            (root / "app").mkdir()
            (root / "app" / "page.tsx").write_text('className="transition-all"')
            origins = {f["file"]: f["provenance"] for f in scan(root)}
            self.assertEqual(origins["components/ui/button.tsx"], "vendored")
            self.assertEqual(origins["app/page.tsx"], "authored")

    def test_provenance_marks_the_token_layer(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "lib" / "motion").mkdir(parents=True)
            (root / "lib" / "motion" / "tokens.ts").write_text(
                'export const ease = { standard: "cubic-bezier(0.2, 0, 0, 1)" };')
            found = scan(root)
            self.assertTrue(found)
            self.assertEqual(found[0]["provenance"], "token-layer")


if __name__ == "__main__":
    unittest.main()
