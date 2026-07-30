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


if __name__ == "__main__":
    unittest.main()
