"""Tests for surfaces.py — what a project is made of, detected in one place."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import surfaces as sf  # noqa: E402


class Fixture(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def write(self, rel: str, text: str = "") -> None:
        p = self.root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")

    def pkg(self, rel: str, deps: dict | None = None, **extra) -> None:
        self.write(f"{rel}/package.json" if rel else "package.json", json.dumps({"dependencies": deps or {}, **extra}))

    def kinds(self, meta: dict | None = None) -> list[tuple]:
        return [(s.kind, s.name, s.path, s.mounted_in) for s in sf.surfaces(self.root, meta)]


class Surfaces(Fixture):
    def test_next_app_is_web(self) -> None:
        self.pkg("", {"next": "16.3.8"})
        self.write("app/page.tsx", "export default function P() { return null }\n")
        self.assertEqual(self.kinds(), [("web", "web", ".", None)])

    def test_expo_by_app_config_is_mobile(self) -> None:
        self.pkg("", {"expo": "58.0.0", "expo-router": "6.0.0"})
        self.write("app.config.ts", "export default { expo: {} }\n")
        self.write("app/index.tsx", "export default function S() { return null }\n")
        self.assertEqual(self.kinds(), [("mobile", "mobile", ".", None)])

    def test_eve_agent_mounted_in_next(self) -> None:
        # Archi Studio: one Next app, eve's agent in agent/, served same-origin by withEve() under /eve/v1/*
        self.pkg("", {"next": "16.3.8", "eve": "1.0.0"})
        self.write("app/page.tsx", "export default function P() { return null }\n")
        self.write("agent/agent.ts", "export default {}\n")
        self.write("next.config.ts", "import { withEve } from 'eve/next'\nexport default withEve({})\n")
        self.assertEqual(self.kinds(), [("web", "web", ".", None), ("agent", "agent", "agent", "web")])

    def test_eve_agent_alone_is_launched_on_its_own(self) -> None:
        self.pkg("", {"eve": "1.0.0"})
        self.write("agent/agent.ts", "export default {}\n")
        # agent-only topology: eve owns the repo root, which is where it is launched from
        self.assertEqual(self.kinds(), [("agent", "agent", ".", None)])

    def test_monorepo_every_app(self) -> None:
        self.pkg("", {}, private=True)
        self.pkg("apps/web", {"next": "16.3.8"})
        self.write("apps/web/app/page.tsx", "")
        self.pkg("apps/mobile", {"expo": "58.0.0"})
        self.write("apps/mobile/app.json", '{"expo": {"name": "m"}}')
        self.pkg("apps/agent", {"eve": "1.0.0"})
        self.write("apps/agent/agent/agent.ts", "")
        self.write("apps/ml/pyproject.toml", "[project]\nname = 'ml'\n")
        meta = {"stack": {"framework": "monorepo", "monorepo": {"services": [
            {"name": "ml", "runtime": "python", "framework": "fastapi", "path": "apps/ml"}]}}}
        self.assertEqual(self.kinds(meta), [("agent", "agent", "apps/agent", None), ("api", "ml", "apps/ml", None),
                                            ("mobile", "mobile", "apps/mobile", None), ("web", "web", "apps/web", None)])

    def test_package_with_bin_is_cli(self) -> None:
        self.pkg("", {}, private=True)
        self.pkg("packages/tool", {}, name="@x/tool", bin={"tool": "bin/tool.js"})
        self.assertEqual(self.kinds(), [("cli", "tool", "packages/tool", None)])

    def test_unknown_app_with_dev_script_is_other(self) -> None:
        self.pkg("", {}, private=True)
        self.pkg("apps/docs", {"astro": "5.0.0"}, scripts={"dev": "astro dev"})
        self.assertEqual(self.kinds(), [("other", "docs", "apps/docs", None)])

    def test_shared_package_without_scripts_is_not_a_surface(self) -> None:
        self.pkg("", {}, private=True)
        self.pkg("packages/ui", {"react": "19.0.0"}, scripts={"lint": "eslint ."})
        self.pkg("packages/types", {})
        self.assertEqual(self.kinds(), [])

    def test_node_modules_never_scanned(self) -> None:
        self.pkg("", {"next": "16.3.8"})
        self.write("app/page.tsx", "")
        self.pkg("node_modules/some-cli", {}, bin={"x": "x.js"})
        self.assertEqual([k[0] for k in self.kinds()], ["web"])


class Helpers(Fixture):
    def test_is_expo_and_is_next_per_directory(self) -> None:
        self.pkg("apps/web", {"next": "16.3.8"})
        self.pkg("apps/mobile", {"expo": "58.0.0"})
        self.assertTrue(sf.is_next(self.root / "apps/web"))
        self.assertFalse(sf.is_expo(self.root / "apps/web"))
        self.assertTrue(sf.is_expo(self.root / "apps/mobile"))

    def test_source_roots(self) -> None:
        self.pkg("apps/web", {"next": "16"})
        self.pkg("packages/api", {})
        self.assertEqual([p.relative_to(self.root).as_posix() for p in sf.source_roots(self.root)],
                         [".", "apps/web", "packages/api"])


if __name__ == "__main__":
    unittest.main()
