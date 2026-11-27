"""design_lint_gate.py: the two holes Agentic Factory fell through (2026-11-27).

1. A ui-sdk web app was never asked: the gate left ui-sdk out while setup_design_lint.py applied to it.
2. A reasoned `design_lint: "none"` took every enforcement of golden rule 3 with it. Now it passes only with
   check_handmade_ui.py wired into `lint` and clean, or with `stack_config.handmade_ui_check_reason`.
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import design_lint_gate as gate  # noqa: E402

CHECK = Path(__file__).resolve().parents[2] / "design-md-to-app" / "scripts" / "check_handmade_ui.py"


def meta(ui: str = "ui-sdk", **config: str) -> dict:
    return {
        "stack": {
            "framework": "monorepo",
            "design_lint": "none",
            "monorepo": {"topology": "web-agent-inapp", "web": {"framework": "next", "ui": ui}},
        },
        "stack_config": {"design_lint_reason": "typescript-eslint refuses TypeScript 7", **config},
    }


class DesignLintGate(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        (self.root / "apps/web/app").mkdir(parents=True)
        (self.root / "apps/web/app/page.tsx").write_text("export default () => <main />\n")
        (self.root / "package.json").write_text(json.dumps({"scripts": {"lint": "biome check ."}}))

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def install(self) -> None:
        subprocess.run([sys.executable, str(CHECK), "--install", str(self.root)], capture_output=True, check=True)

    def test_a_ui_sdk_web_app_is_asked(self) -> None:
        self.assertTrue(gate.applies(meta("ui-sdk")))
        self.assertTrue(gate.applies(meta("shadcn")))
        self.assertFalse(gate.applies(meta("mui")))

    def test_a_reasoned_opt_out_alone_no_longer_passes(self) -> None:
        ok, why = gate.verify(self.root, meta())
        self.assertFalse(ok)
        self.assertIn("nothing else enforces golden rule 3", why)

    def test_the_opt_out_passes_with_the_check_wired_and_clean(self) -> None:
        self.install()
        ok, why = gate.verify(self.root, meta())
        self.assertTrue(ok, why)

    def test_a_wired_check_with_hand_built_ui_does_not_pass(self) -> None:
        self.install()
        (self.root / "apps/web/app/list.tsx").write_text("<table>\n")
        ok, why = gate.verify(self.root, meta())
        self.assertFalse(ok)
        self.assertIn("hand-built <table>", why)

    def test_the_check_has_its_own_recorded_opt_out(self) -> None:
        ok, why = gate.verify(self.root, meta(handmade_ui_check_reason="no web UI yet"))
        self.assertTrue(ok, why)

    def test_an_opt_out_without_its_reason_still_fails(self) -> None:
        m = meta()
        del m["stack_config"]["design_lint_reason"]
        self.assertFalse(gate.verify(self.root, m)[0])


if __name__ == "__main__":
    unittest.main()
