"""Tests for setup_design_lint.py and the phase gate that relies on it.

No network and no ESLint here: these cover the decisions and the text edits — which
topology a project is, where the preset is spread, that re-running changes nothing, that
the policy never opens the holes it was written to close, and that `set-phase scaffolded`
refuses an unwired project. The install-and-measure path was verified on real projects
(gym-saas before its lint commit, a copy of notarius-crm, a web+mobile fixture) and is
recorded in references/design-system-lint.md.

    cd design-md-to-app/scripts && python3 -m unittest test_setup_design_lint
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import setup_design_lint as sdl  # noqa: E402

DEVFLOW = HERE.parents[1] / "dev-flow" / "scripts"

NEXT16_CONFIG = """import { defineConfig, globalIgnores } from "eslint/config";
import nextVitals from "eslint-config-next/core-web-vitals";
import nextTs from "eslint-config-next/typescript";

const eslintConfig = defineConfig([
  ...nextVitals,
  ...nextTs,
  // Override default ignores of eslint-config-next.
  globalIgnores([
    // Default ignores of eslint-config-next:
    ".next/**",
    "next-env.d.ts",
  ]),
]);

export default eslintConfig;
"""

SHADCN_MONOREPO_CONFIG = """import { config } from "@workspace/eslint-config/react-internal"

/** @type {import("eslint").Linter.Config} */
export default config
"""

COMPONENTS_APP = {"tailwind": {"css": "app/globals.css"}, "aliases": {"ui": "@/components/ui"}}
COMPONENTS_UI = {"tailwind": {"css": "src/styles/globals.css"}, "aliases": {"ui": "@workspace/ui/components"}}


def write(root: Path, rel: str, content: str | dict) -> Path:
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(content, indent=2) + "\n" if isinstance(content, dict) else content)
    return p


def meta(root: Path, phase: str, **stack) -> None:
    write(root, ".workflow/meta.json", {"project_slug": "t", "phase": phase, "stack": stack})


def single_app(root: Path) -> None:
    write(root, "package.json", {"name": "app", "scripts": {"lint": "eslint"}, "devDependencies": {}})
    write(root, "components.json", COMPONENTS_APP)
    write(root, "eslint.config.mjs", NEXT16_CONFIG)
    write(root, "app/globals.css", '@import "tailwindcss";\n@theme inline {\n  --shadow-float: 0 1px 2px red;\n}\n')
    (root / "components" / "ui").mkdir(parents=True)


def shadcn_monorepo(root: Path, only_warn: bool = True) -> None:
    write(root, "packages/eslint-config/package.json",
          {"name": "@workspace/eslint-config", "exports": {"./base": "./base.js"}, "devDependencies": {}})
    write(root, "packages/eslint-config/base.js",
          'import onlyWarn from "eslint-plugin-only-warn"\n' if only_warn else "export const config = []\n")
    write(root, "packages/ui/package.json", {"name": "@workspace/ui", "scripts": {"lint": "eslint"}})
    write(root, "packages/ui/components.json", COMPONENTS_UI)
    write(root, "packages/ui/eslint.config.js", SHADCN_MONOREPO_CONFIG)
    write(root, "packages/ui/src/styles/globals.css", "@theme inline {\n}\n")
    (root / "packages/ui/src/components").mkdir(parents=True)
    write(root, "apps/web/package.json", {"name": "web", "scripts": {"lint": "eslint"}})
    write(root, "apps/web/components.json", {"tailwind": {"css": ""}, "aliases": {"ui": "@workspace/ui/components"}})
    write(root, "apps/web/eslint.config.js", SHADCN_MONOREPO_CONFIG.replace("config", "nextJsConfig").replace(
        "react-internal", "next-js"))


class Applicability(unittest.TestCase):
    def test_matrix(self) -> None:
        cases = [
            ({"framework": "next", "ui": "shadcn"}, True),
            ({"framework": "next", "ui": "base-ui"}, True),
            ({"framework": "next", "ui": "coss"}, True),
            ({"framework": "next", "ui": None}, True),  # undecided UI still has to decide the lint
            ({"framework": "next", "ui": "mui"}, False),
            ({"framework": "expo-rn"}, False),
            ({"framework": "agent"}, False),
            ({"framework": "monorepo", "monorepo": {"topology": "web-mobile", "web": {"ui": "shadcn"}}}, True),
            ({"framework": "monorepo", "monorepo": {"web": {"ui": "mui"}}}, False),
        ]
        for stack, expected in cases:
            with self.subTest(stack=stack):
                self.assertEqual(sdl.applicability({"stack": stack})[0], expected)


class Detection(unittest.TestCase):
    def test_single_app_at_root(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); single_app(root)
            units = sdl.detect(root)
            self.assertEqual([u["kind"] for u in units], ["single"])
            self.assertEqual(units[0]["preset"].name, "eslint.design-system.mjs")

    def test_shadcn_monorepo_is_one_unit_spread_into_web_and_ui(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); shadcn_monorepo(root)
            (u,) = sdl.detect(root)
            self.assertEqual(u["kind"], "monorepo")
            self.assertEqual(sorted(t.relative_to(root).as_posix() for t in u["targets"]), ["apps/web", "packages/ui"])
            self.assertTrue(sdl.only_warn(root, u))
            self.assertEqual(u["preset"].name, "design-system.mjs", "no \"type\": \"module\" → .mjs")
            cfg = root / "packages/eslint-config/package.json"
            write(root, "packages/eslint-config/package.json", {**json.loads(cfg.read_text()), "type": "module"})
            self.assertEqual(sdl.detect(root)[0]["preset"].name, "design-system.js")

    def test_app_that_consumes_the_ui_package_without_its_own_components_json(self) -> None:
        # bidmaster: apps/web has an eslint config and depends on @x/ui but no components.json;
        # packages/ui has components.json but no eslint config
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); shadcn_monorepo(root)
            (root / "packages/ui/eslint.config.js").unlink()
            (root / "apps/web/components.json").unlink()
            web = json.loads((root / "apps/web/package.json").read_text())
            web["dependencies"] = {"@workspace/ui": "workspace:*"}
            write(root, "apps/web/package.json", web)
            (u,) = sdl.detect(root)
            self.assertEqual([t.relative_to(root).as_posix() for t in u["targets"]], ["apps/web"])

    def test_no_target_means_no_unit_and_check_fails(self) -> None:
        # the defect: a unit with zero targets installed, recorded and passed --check
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); shadcn_monorepo(root, only_warn=False)
            (root / "packages/ui/eslint.config.js").unlink()
            (root / "apps/web/components.json").unlink()   # and no dependency on the UI package
            self.assertEqual(sdl.detect(root), [])
            self.assertIn("nothing to spread the preset into", sdl.why_undetected(root))
            meta(root, "scaffolded", framework="monorepo", design_lint="shadcn-lint")
            self.assertFalse(sdl.check(root)[0], "a recorded decision with nothing wired must not pass")
            r = subprocess.run([sys.executable, str(HERE / "setup_design_lint.py"), str(root)],
                               capture_output=True, text=True, check=False)
            self.assertEqual(r.returncode, 2, "must refuse before installing anything")
            self.assertNotIn("install:", r.stdout)

    def test_web_mobile_app_in_a_subfolder(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            write(root, "package.json", {"name": "root"})
            single_app(root / "apps" / "web")
            write(root, "apps/mobile/package.json", {"name": "mobile"})
            (u,) = sdl.detect(root)
            self.assertEqual(u["config_pkg"].relative_to(root).as_posix(), "apps/web")

    def test_nothing_to_wire_names_next_lint(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            write(root, "apps/web/components.json", COMPONENTS_APP)
            write(root, "apps/web/package.json", {"name": "web", "scripts": {"lint": "next lint"}})
            self.assertEqual(sdl.detect(root), [])
            self.assertIn("`next lint`", sdl.why_undetected(root))


class Wiring(unittest.TestCase):
    def test_next16_config_spread_above_the_ignores_comment_and_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            cfg = write(Path(d), "eslint.config.mjs", NEXT16_CONFIG)
            self.assertTrue(sdl.wire_config(cfg, "./eslint.design-system.mjs"))
            text = cfg.read_text()
            self.assertIn('import { designSystemConfig } from "./eslint.design-system.mjs"', text)
            lines = text.splitlines()
            spread = next(i for i, l in enumerate(lines) if "...designSystemConfig" in l)
            self.assertIn("Override default ignores", lines[spread + 1], "the comment must stay with globalIgnores")
            self.assertFalse(sdl.wire_config(cfg, "./eslint.design-system.mjs"))
            self.assertEqual(cfg.read_text().count("...designSystemConfig"), 1)

    def test_shadcn_template_export(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            cfg = write(Path(d), "eslint.config.js", SHADCN_MONOREPO_CONFIG)
            sdl.wire_config(cfg, "@workspace/eslint-config/design-system")
            self.assertIn("export default [...config, ...designSystemConfig]", cfg.read_text())

    def test_lint_cap_replaced_not_appended(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            pkg = Path(d)
            write(pkg, "package.json", {"name": "x", "scripts": {"lint": "eslint --max-warnings 9", "dev": "next"}})
            sdl.set_lint_script(pkg, 4)
            scripts = json.loads((pkg / "package.json").read_text())["scripts"]
            self.assertEqual(scripts["lint"], "eslint --max-warnings 4")
            self.assertEqual(scripts["dev"], "next")

    def test_agents_block_replaced_and_foreign_blocks_kept(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            write(root, "AGENTS.md", "<!-- BEGIN:nextjs-agent-rules -->\nnext\n<!-- END:nextjs-agent-rules -->\n")
            sdl.write_agents(root, "gate one")
            sdl.write_agents(root, "gate two")
            text = (root / "AGENTS.md").read_text()
            self.assertEqual(text.count(sdl.AGENTS_BEGIN), 1)
            self.assertIn("gate two", text)
            self.assertNotIn("gate one", text)
            self.assertIn("BEGIN:nextjs-agent-rules", text)


class Policy(unittest.TestCase):
    """The preset must never open the holes it exists to close."""

    def preset(self) -> str:
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); single_app(root)
            (u,) = sdl.detect(root)
            return sdl.preset_source(u, "error")

    def test_shadows_by_exact_name_never_wildcard(self) -> None:
        src = self.preset()
        self.assertIn("allow: declaredShadows()", src)
        self.assertNotIn('"shadow-*"', src.replace('Never "shadow-*"', ""))

    def test_component_directory_keeps_raw_colours_on(self) -> None:
        src = self.preset()
        block = src[src.index('files: ["components/ui/**"]'):]
        block = block[:block.index("\n  },")]
        self.assertIn('"shadcn/no-unknown-classes": "off"', block)
        self.assertNotIn("no-raw-colors", block)
        self.assertNotIn("no-inline-styles", block)

    def test_delivered_broken_files_are_scoped(self) -> None:
        src = self.preset()
        self.assertIn('"components/ui/carousel.tsx"', src)
        self.assertIn('"**/hooks/use-mobile.ts"', src)
        self.assertIn('"components/ui/sidebar.tsx"', src)
        self.assertNotIn('"**/carousel.tsx"', src)


class Check(unittest.TestCase):
    def test_decisions(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); single_app(root)
            meta(root, "design_extracted", framework="next", ui="shadcn")
            self.assertFalse(sdl.check(root)[0], "undecided must not pass")
            meta(root, "design_extracted", framework="next", ui="shadcn", design_lint="none")
            self.assertFalse(sdl.check(root)[0], "an opt-out without a reason must not pass")
            m = json.loads((root / ".workflow/meta.json").read_text())
            m["stack_config"] = {"design_lint_reason": "custom CSS, no Tailwind classes"}
            write(root, ".workflow/meta.json", m)
            self.assertTrue(sdl.check(root)[0])
            meta(root, "design_extracted", framework="next", ui="mui")
            self.assertTrue(sdl.check(root)[0])

    def test_only_warn_needs_a_cap(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); shadcn_monorepo(root)
            meta(root, "scaffolded", framework="monorepo", design_lint="shadcn-lint")
            ok, problems = sdl.check(root)
            self.assertFalse(ok)
            self.assertTrue(any("--max-warnings" in p for p in problems))


class PhaseGate(unittest.TestCase):
    def set_phase(self, root: Path, phase: str) -> subprocess.CompletedProcess:
        return subprocess.run([sys.executable, str(DEVFLOW / "update_meta.py"), str(root), "set-phase", phase],
                              capture_output=True, text=True, check=False)

    def test_refuses_an_unwired_app_and_names_the_fix(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); single_app(root)
            meta(root, "design_extracted", framework="next", ui="shadcn")
            r = self.set_phase(root, "scaffolded")
            self.assertEqual(r.returncode, 1)
            self.assertIn("setup_design_lint.py", r.stderr)
            self.assertEqual(json.loads((root / ".workflow/meta.json").read_text())["phase"], "design_extracted")

    def test_refuses_jumping_past_scaffolded(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); single_app(root)
            meta(root, "design_extracted", framework="next", ui="shadcn")
            self.assertEqual(self.set_phase(root, "page_generated").returncode, 1)

    def test_allows_a_reasoned_opt_out_and_other_stacks(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); single_app(root)
            write(root, ".workflow/meta.json", {"phase": "design_extracted", "stack": {
                "framework": "next", "ui": "shadcn", "design_lint": "none"},
                "stack_config": {"design_lint_reason": "prototype, thrown away"}})
            self.assertEqual(self.set_phase(root, "scaffolded").returncode, 0)
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            meta(root, "design_extracted", framework="expo-rn")
            self.assertEqual(self.set_phase(root, "scaffolded").returncode, 0)

    def test_does_not_gate_later_transitions(self) -> None:
        # projects that predate the gate keep moving; show_state warns about them instead
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); single_app(root)
            meta(root, "module_added", framework="next", ui="shadcn")
            self.assertEqual(self.set_phase(root, "feature_complete").returncode, 0)
            out = subprocess.run([sys.executable, str(DEVFLOW / "show_state.py"), str(root)],
                                 capture_output=True, text=True, check=False).stdout
            self.assertIn("Design lint missing", out)


if __name__ == "__main__":
    unittest.main()
