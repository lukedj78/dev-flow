"""Tests for check_ui_registry.py: each rule against the shape that broke the 2026-11-26 install, and its fix."""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import check_ui_registry as c  # noqa: E402

BASE = "https://ds.example/r/"
V = "0.1.0-beta.17"


def item(name, deps=(), reg=(), files=(), type_="registry:ui"):
    return {"name": name, "type": type_, "dependencies": list(deps), "registryDependencies": list(reg), "files": list(files)}


def ui_file(path, content="export const x = 1\n", type_="registry:ui"):
    return {"path": path, "type": type_, "content": content}


class Items(unittest.TestCase):
    def run_items(self, served, names, version=V):
        return c.check_items(BASE, names, version, get=lambda url: served[url.rsplit("/", 1)[1].removesuffix(".json")])

    def codes(self, findings):
        return sorted({f["code"] for f in findings})

    def test_a_clean_item_and_its_dependencies(self):
        served = {
            "button": item("button", [f"@ui-sdk/react@{V}", "cva@0.7.1"], [f"{BASE}utils.json"], [ui_file("ui/button.tsx")]),
            "utils": item("utils", ["cn@0.5.2"], type_="registry:lib"),
        }
        self.assertEqual(self.run_items(served, ["button"]), [])

    def test_stops_on_another_ui_sdk_version_and_a_second_behaviour_library(self):
        served = {"x": item("x", ["@ui-sdk/react@0.1.0-beta.6", "@shadcn/react@0.3.1", "@radix-ui/react-slot@1.0.0"])}
        found = self.run_items(served, ["x"])
        self.assertEqual(self.codes(found), ["U1", "U2"])
        self.assertTrue(all(f["level"] == "stop" for f in found))

    def test_warns_on_unpinned_dependencies_and_css_outside_a_theme(self):
        served = {
            "map": item("map", ["geojson", "leaflet@^1.9.0"], files=[ui_file("styles/map.css", "")]),
            "theme": item("theme", files=[ui_file("styles/dark.css", "")], type_="registry:theme"),
        }
        found = self.run_items(served, ["map", "theme"])
        self.assertEqual(self.codes(found), ["U3", "U4"])
        self.assertTrue(all(f["where"] == "map" for f in found), "a theme may ship CSS")

    def test_stops_on_a_block_copied_as_is_and_on_a_local_origin(self):
        block = ui_file("blocks/login/form.tsx", "'use client'\nimport { Card } from '@/components/ui/card'\n", "registry:file")
        served = {
            "login": item("login", reg=["http://localhost:5174/r/card.json"], files=[block], type_="registry:block"),
            "card": item("card"),
        }
        found = self.run_items(served, ["login"])
        self.assertEqual(self.codes(found), ["U5", "U6"])
        self.assertEqual(len([f for f in found if f["code"] == "U6"]), 1, "one finding per local origin")

    def test_warns_on_handlers_without_use_client(self):
        served = {"f": item("f", files=[ui_file("f.tsx", "export function F() { return <form onSubmit={() => {}} /> }\n")])}
        self.assertEqual(self.codes(self.run_items(served, ["f"])), ["U7"])
        served["f"]["files"][0]["content"] = "'use client'\n" + served["f"]["files"][0]["content"]
        self.assertEqual(self.run_items(served, ["f"]), [])


class Project(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        w = lambda rel, data: (self.root / rel).parent.mkdir(parents=True, exist_ok=True) or (self.root / rel).write_text(
            data if isinstance(data, str) else json.dumps(data)
        )
        self.w = w
        w("package.json", {"name": "mono", "devDependencies": {"turbo": "2.0.0"}})
        w("packages/ui/package.json", {"name": "@workspace/ui", "dependencies": {"@ui-sdk/react": V}})
        w("packages/ui/components.json", {"tailwind": {"css": "src/styles/globals.css"}})
        w("packages/ui/src/styles/globals.css", f'{c.LAYER_ORDER}\n@import "tailwindcss";\n@layer ui-sdk {{}}\n')
        w("apps/web/package.json", {"name": "web", "dependencies": {"next": "16.4.6", "react": "19.3.1", "@ui-sdk/react": V}})
        w("apps/web/components.json", {"aliases": {"lib": "@workspace/ui/lib", "ui": "@workspace/ui/components"}})
        w("apps/web/app/page.tsx", "import { Button } from '@workspace/ui/components/button'\nimport Link from 'next/link'\n")
        w("apps/web/components/agent/bridge.ts", "import { createAgent } from '@ui-sdk/react/agent'\n")

    def tearDown(self):
        self.tmp.cleanup()

    def codes(self):
        return sorted({f["code"] for f in c.check_project(self.root)})

    def test_the_fixed_monorepo_is_clean(self):
        self.assertEqual(self.codes(), [])

    def test_the_template_lib_alias(self):
        self.w("apps/web/components.json", {"aliases": {"lib": "@/lib"}})
        self.assertEqual(self.codes(), ["P1"])

    def test_the_layer_order_missing_or_after_tailwind(self):
        self.w("packages/ui/src/styles/globals.css", '@import "tailwindcss";\n@layer ui-sdk {}\n')
        self.assertEqual(self.codes(), ["P2"])
        self.w("packages/ui/src/styles/globals.css", f'@import "tailwindcss";\n{c.LAYER_ORDER}\n')
        self.assertEqual(self.codes(), ["P2"])

    def test_two_copies_of_ui_sdk_core(self):
        self.w("pnpm-lock.yaml", "packages:\n\n  '@ui-sdk/core@0.1.0-beta.17':\n    x: 1\n\n  '@ui-sdk/core@0.1.0-beta.16':\n    x: 1\n")
        self.assertEqual(self.codes(), ["P3"])

    def test_an_app_file_importing_what_only_packages_ui_declares(self):
        self.w("apps/web/package.json", {"name": "web", "dependencies": {"next": "16.4.6", "react": "19.3.1"}})
        self.assertEqual(self.codes(), ["P4"])

    def test_an_alias_import_left_unrewritten(self):
        self.w("apps/web/components/blocks/login.tsx", "import { Card } from '@/components/ui/card'\n")
        self.assertEqual(self.codes(), ["P5"])


if __name__ == "__main__":
    unittest.main()
