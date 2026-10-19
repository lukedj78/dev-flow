"""Unit tests for scan_motion — the motion-audit heuristics.

classify_line() and missing_reduced_motion() are pure; scan() is the I/O layer
exercised by the smoke tests.
"""
import tempfile
import unittest
from pathlib import Path

from scan_motion import classify_line, frame_smells, missing_reduced_motion, provenance, scan


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


class TestPaintAndLayers(unittest.TestCase):
    """Re-read of emilkowalski/skills' animation-performance (2026-10-11): box-shadow and border-radius are paint, not
    layout; will-change is a last resort on the animating element, never everything."""

    def test_box_shadow_is_paint_not_layout(self):
        self.assertEqual(classify_line("  transition: box-shadow 200ms ease;"), "paint-prop-anim")

    def test_tailwind_transition_shadow_is_paint(self):
        self.assertEqual(classify_line('className="transition-shadow hover:shadow-lg"'), "paint-prop-anim")

    def test_border_radius_is_paint(self):
        self.assertEqual(classify_line("  transition: border-radius 150ms;"), "paint-prop-anim")

    def test_width_is_still_layout(self):
        self.assertEqual(classify_line("  transition: width 200ms ease;"), "layout-prop-anim")

    def test_will_change_all_or_a_list_is_broad(self):
        self.assertEqual(classify_line("  will-change: all;"), "will-change-broad")
        self.assertEqual(classify_line("  will-change: transform, opacity;"), "will-change-broad")

    def test_will_change_on_the_animating_element_is_fine(self):
        self.assertIsNone(classify_line('className="will-change-transform"'))
        self.assertIsNone(classify_line("  will-change: transform;"))


class TestFrameSmells(unittest.TestCase):
    def test_will_change_on_a_global_selector(self):
        css = "body {\n  margin: 0;\n  will-change: transform;\n}\n.card { color: red }"
        self.assertEqual([c for _, c, _ in frame_smells(css)], ["will-change-broad"])

    def test_set_state_in_a_frame_loop(self):
        code = ("function tick() {\n  setY((y) => y + 1);\n  requestAnimationFrame(tick);\n}\n"
                "requestAnimationFrame(tick);")
        self.assertEqual([c for _, c, _ in frame_smells(code)], ["state-per-frame"])

    def test_set_state_in_an_inline_loop(self):
        code = "const loop = () => requestAnimationFrame(() => {\n  setX(x + 1);\n  requestAnimationFrame(loop);\n});"
        self.assertEqual([c for _, c, _ in frame_smells(code)], ["state-per-frame"])

    def test_a_one_shot_frame_is_not_per_frame(self):
        # annotix: open a dialog on the next frame after mount — once, not every frame
        self.assertEqual(frame_smells("const id = window.requestAnimationFrame(() => setOpen(true))"), [])

    def test_a_setter_near_but_outside_the_frame_callback_is_fine(self):
        # smart-travel: a state setter a few lines after an unrelated rAF
        code = "requestAnimationFrame(() => el.focus());\nconst setNights = (k, n) => setRows((c) => c);"
        self.assertEqual(frame_smells(code), [])

    def test_set_property_is_not_a_state_setter(self):
        code = "function tick() {\n  root.style.setProperty('--x', '1px');\n  requestAnimationFrame(tick);\n}"
        self.assertNotIn("state-per-frame", [c for _, c, _ in frame_smells(code)])

    def test_a_ref_write_inside_request_animation_frame_is_fine(self):
        code = "requestAnimationFrame(() => {\n  ref.current.style.transform = `translateY(${y}px)`;\n});"
        self.assertEqual(frame_smells(code), [])

    def test_css_variable_written_from_a_gesture(self):
        code = "function onPointerMove(e) {\n  el.style.setProperty('--swipe-amount', `${dy}px`);\n}"
        self.assertEqual([c for _, c, _ in frame_smells(code)], ["css-var-per-frame"])

    def test_css_variable_set_once_is_fine(self):
        self.assertEqual(frame_smells("root.style.setProperty('--brand', color);"), [])

    def test_scan_reports_frame_smells_with_their_line_and_skips_agent_worktrees(self):
        loop = "export function Drag() {\n  function tick() {\n    setY((y) => y + 1);\n    requestAnimationFrame(tick);\n  }\n}\n"
        with tempfile.TemporaryDirectory() as d:
            Path(d, "drag.tsx").write_text(loop)
            Path(d, ".claude/worktrees/agent-x").mkdir(parents=True)
            Path(d, ".claude/worktrees/agent-x/drag.tsx").write_text(loop)
            hits = [(f["file"], f["line"], f["category"]) for f in scan(Path(d))]
            self.assertIn(("drag.tsx", 3, "state-per-frame"), hits)
            self.assertFalse(any(h[0].startswith(".claude") for h in hits), hits)


class TestReviewFindings(unittest.TestCase):
    """Cases from the final review of the animation-performance merge (2026-10-19), each verified failing first."""

    def cats(self, code):
        return [c for _, c, _ in frame_smells(code)]

    def test_double_raf_one_shot_is_not_a_loop(self):
        self.assertEqual(frame_smells("requestAnimationFrame(() => requestAnimationFrame(() => setVisible(true)))"), [])

    def test_every_setter_in_the_loop_is_reported(self):
        code = ("function tick(now) {\n  if (done) {\n    setSeries(end);\n  }\n  setDisplay(value);\n"
                "  if (!done) frame = requestAnimationFrame(tick);\n}")
        self.assertEqual([(l, c) for l, c, _ in frame_smells(code)], [(3, "state-per-frame"), (5, "state-per-frame")])

    def test_typed_arrow_loop(self):
        code = "const tick: FrameRequestCallback = (t) => {\n  setV(t);\n  id = requestAnimationFrame(tick);\n};"
        self.assertEqual(self.cats(code), ["state-per-frame"])

    def test_function_with_destructured_params(self):
        code = "function tick({ x }: P) {\n  setX(x);\n  requestAnimationFrame(tick);\n}"
        self.assertEqual(self.cats(code), ["state-per-frame"])

    def test_brackets_in_strings_and_comments_do_not_stretch_the_span(self):
        code = ('requestAnimationFrame(() => { setLabel(":("); });\n'
                "// closes the menu (see #12\n"
                "const a = 1;\nrequestAnimationFrame(() => el.focus());\nsetN(2);")
        self.assertEqual(frame_smells(code), [])

    def test_use_animation_frame_runs_every_frame(self):
        self.assertEqual(self.cats("useAnimationFrame((t) => {\n  setR(t / 10);\n});"), ["state-per-frame"])

    def test_class_component_loop(self):
        code = ("class Spin extends React.Component {\n  tick = () => {\n    this.setState({ a: 1 });\n"
                "    requestAnimationFrame(this.tick);\n  };\n}")
        self.assertEqual(self.cats(code), ["state-per-frame"])

    def test_a_local_helper_named_set_is_not_state(self):
        code = ("function setTransform(el, y) { el.style.transform = `translateY(${y}px)`; }\n"
                "function tick() {\n  setTransform(el, y);\n  requestAnimationFrame(tick);\n}")
        self.assertEqual(frame_smells(code), [])

    def test_vaul_style_object_from_a_gesture(self):
        code = ("const onPointerMove = (e) => setDragged(e.clientY - start);\n"
                "return <div style={{ \"--swipe-amount\": `${dragged}px` }} onPointerMove={onPointerMove} />;")
        self.assertEqual(self.cats(code), ["css-var-per-frame"])

    def test_on_scroll_handler_counts_as_a_gesture(self):
        code = "<div onScroll={() => {\n  el.style.setProperty('--y', `${el.scrollTop}px`);\n}} />"
        self.assertEqual(self.cats(code), ["css-var-per-frame"])

    def test_a_comment_mentioning_scroll_is_not_a_gesture(self):
        code = "// keep the header below the scroll area\nuseEffect(() => {\n  root.style.setProperty('--header-h', `${h}px`);\n}, [h]);"
        self.assertEqual(frame_smells(code), [])

    def test_global_will_change_is_reported_once_and_star_lists_count(self):
        self.assertEqual(self.cats("body { will-change: all; }"), ["will-change-broad"])
        self.assertEqual(self.cats("*, *::before {\n  will-change: transform;\n}"), ["will-change-broad"])


class TestMonorepoAndScale(unittest.TestCase):
    def test_shadcn_components_in_a_monorepo_are_vendored(self):
        for rel in ("apps/web/components/ui/button.tsx", "packages/ui/src/components/slider.tsx",
                    "packages/ui/src/components/ui/dialog.tsx", "components/ui/checkbox.tsx"):
            with self.subTest(rel):
                self.assertEqual(provenance(rel), "vendored")
        self.assertEqual(provenance("apps/web/components/shared/card.tsx"), "authored")

    def test_a_large_file_stays_fast(self):
        import time
        chunk = "function tick%d() {\n  setV(v);\n  requestAnimationFrame(tick%d);\n}\n" + "const filler = 1;\n" * 120
        text = "".join(chunk % (i, i) for i in range(200))
        start = time.time()
        self.assertEqual(len(frame_smells(text)), 200)
        # guards against the quadratic shapes (10 s and more), not against a slow CI machine
        self.assertLess(time.time() - start, 3.0)


class TestPropertyLists(unittest.TestCase):
    def test_paint_props_in_lists_and_every_syntax(self):
        for line in ("transition: opacity 200ms, box-shadow 200ms;", "transition-property: box-shadow;",
                     'transition: "box-shadow 200ms"', 'className="transition-[box-shadow]"',
                     'className="transition-[color,box-shadow]"'):
            with self.subTest(line):
                self.assertEqual(classify_line(line), "paint-prop-anim")

    def test_layout_props_in_lists(self):
        self.assertEqual(classify_line("transition: opacity 200ms, height 300ms;"), "layout-prop-anim")
        self.assertEqual(classify_line('className="transition-[height]"'), "layout-prop-anim")

    def test_will_change_lists_in_every_syntax(self):
        for line in ("will-change: transform, opacity;", 'className="will-change-[transform,opacity]"',
                     "willChange: 'transform, opacity'"):
            with self.subTest(line):
                self.assertEqual(classify_line(line), "will-change-broad")

    def test_transition_colors_and_transform_are_clean(self):
        self.assertIsNone(classify_line('className="transition-colors"'))
        self.assertIsNone(classify_line("transition: transform 200ms, opacity 200ms;"))


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
