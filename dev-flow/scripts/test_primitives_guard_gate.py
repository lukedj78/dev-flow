"""Tests for primitives_guard_gate.py, its use in update_meta.py set-phase, and show_state.py's
phase-behind-the-code warning.

    cd dev-flow/scripts && python3 -m unittest test_primitives_guard_gate
"""

from __future__ import annotations

import contextlib
import io
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import primitives_guard_gate as gate  # noqa: E402
import show_state  # noqa: E402

DMTA = HERE.parents[1] / "design-md-to-app" / "scripts"


def write(root: Path, rel: str, content) -> None:
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(content, indent=2) + "\n" if isinstance(content, dict) else content)


def web_app(root: Path, phase: str, **stack) -> None:
    write(root, "package.json", {"name": "app", "scripts": {"lint": "eslint --max-warnings 0"},
                                 "devDependencies": {"@shadcn/lint": "0.1.0"}})
    write(root, "components.json", {"tailwind": {"css": "app/globals.css"}, "aliases": {"ui": "@/components/ui"}})
    write(root, "eslint.config.mjs", "export default [\n]\n")
    write(root, "app/globals.css", "@theme inline {\n}\n")
    write(root, "components/ui/button.tsx", "export function Button() { return null }\n")
    write(root, ".workflow/meta.json", {"project_slug": "t", "phase": phase, "stack": {
        "framework": "next", "ui": "shadcn", "data_residency": "none", "registry_intake": "none", **stack},
        "stack_config": {"registry_intake_reason": "not under test here"},
        "wireframes": {"skipped": True, "reason": "not under test here"}})


def retrofit(root: Path) -> None:
    """setup_design_lint.py <root> — the one command dev-flow proposes — with ESLint stubbed out."""
    sys.path.insert(0, str(DMTA))
    import setup_design_lint as sdl
    original = sdl.run_eslint
    sdl.run_eslint = lambda t: []
    try:
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            assert sdl.setup(root) == 0
    finally:
        sdl.run_eslint = original


def set_phase(root: Path, phase: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(HERE / "update_meta.py"), str(root), "set-phase", phase],
                          capture_output=True, text=True, check=False)


def state(root: Path) -> str:
    return subprocess.run([sys.executable, str(HERE / "show_state.py"), str(root)],
                          capture_output=True, text=True, check=False).stdout


class Gate(unittest.TestCase):
    def test_not_applicable_off_tailwind_web(self) -> None:
        for stack in ({"framework": "expo-rn"}, {"framework": "agent"}, {"framework": "next", "ui": "mui"}):
            with self.subTest(stack=stack):
                self.assertTrue(gate.verify(Path("/nonexistent"), {"stack": stack})[0])

    def test_opt_outs_need_a_reason(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            m = {"stack": {"framework": "next", "ui": "shadcn", "primitives_guard": "none"}}
            self.assertFalse(gate.verify(root, m)[0])
            m["stack_config"] = {"primitives_guard_reason": "spike"}
            self.assertTrue(gate.verify(root, m)[0])
            # a reasoned design-lint opt-out takes the guard with it (no rule to run)
            m = {"stack": {"framework": "next", "ui": "shadcn", "design_lint": "none"},
                 "stack_config": {"design_lint_reason": "CSS modules, no Tailwind classes"}}
            self.assertTrue(gate.verify(root, m)[0])

    def test_refuses_scaffolded_and_every_later_phase_until_retrofitted(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); web_app(root, "module_added", design_lint="shadcn-lint")
            for phase in ("module_added", "feature_complete", "deployed"):
                with self.subTest(phase=phase):
                    r = set_phase(root, phase)
                    self.assertEqual(r.returncode, 1, r.stderr)
                    self.assertIn("setup_design_lint.py", r.stderr)
            retrofit(root)
            self.assertTrue(gate.verify(root, json.loads((root / ".workflow/meta.json").read_text()))[0])
            r = set_phase(root, "feature_complete")
            self.assertEqual(r.returncode, 0, r.stderr)

    def test_guard_without_the_rule_does_not_pass(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); web_app(root, "scaffolded")
            retrofit(root)
            preset = root / "eslint.design-system.mjs"
            preset.write_text(preset.read_text().replace('"design/no-handmade-ui": "error"', '"design/no-handmade-ui": "off"'))
            ok, why = gate.verify(root, json.loads((root / ".workflow/meta.json").read_text()))
            self.assertFalse(ok)
            self.assertIn("no-handmade-ui", why)


class PhaseBehindCode(unittest.TestCase):
    def test_warns_and_routes_to_realignment(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); web_app(root, "design_extracted")
            write(root, "app/page.tsx", "export default function P() { return null }\n")
            write(root, "components/trips/row.tsx", "export function Row() { return null }\n")
            self.assertEqual(show_state.app_code(root), (1, 1), "components/ui is not app code")
            out = state(root)
            self.assertIn("PHASE BEHIND THE CODE", out)
            self.assertIn("No check is being proposed", out)
            self.assertIn("REALIGN THE PHASE", out)
            self.assertIn("setup_design_lint.py", out)
            self.assertIn("set-phase page_generated", out)
            self.assertIn("PRIMITIVES GUARD", out, "the gates are shown although the phase is early")

    def test_silent_without_code_or_past_scaffolded(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); web_app(root, "design_extracted")
            self.assertNotIn("PHASE BEHIND", state(root), "only the vendored primitives: no app code yet")
            write(root, "app/page.tsx", "export default function P() { return null }\n")
            m = json.loads((root / ".workflow/meta.json").read_text())
            m["phase"] = "page_generated"
            write(root, ".workflow/meta.json", m)
            self.assertNotIn("PHASE BEHIND", state(root))

    def test_monorepo_apps_count(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            write(root, "apps/web/app/(app)/trips/page.tsx", "x")
            write(root, "apps/web/node_modules/pkg/app/page.tsx", "x")
            self.assertEqual(show_state.app_code(root), (1, 0))


if __name__ == "__main__":
    unittest.main()
