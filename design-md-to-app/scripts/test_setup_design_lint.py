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

import contextlib
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import setup_design_lint as sdl  # noqa: E402

DEVFLOW = HERE.parents[1] / "dev-flow" / "scripts"


def node_project() -> Path | None:
    """A project whose node_modules has eslint, eslint-config-next and @shadcn/lint, used read-only to run
    the generated rules (no network here). DESIGN_LINT_NODE_PROJECT names one; else ~/projects/* is searched."""
    env = os.environ.get("DESIGN_LINT_NODE_PROJECT")
    cands = [Path(env)] if env else sorted(Path.home().glob("projects/*"))
    for c in cands:
        if all((c / "node_modules" / p / "package.json").exists() for p in ("eslint", "eslint-config-next", "@shadcn/lint")):
            return c
    return None


RULE_RUNNER = """
import { createRequire } from "node:module"
import { readFileSync } from "node:fs"
import { pathToFileURL } from "node:url"
const [home, rules] = process.argv.slice(2)
const { Linter } = createRequire(home + "/package.json")("eslint")
const { designPlugin } = await import(pathToFileURL(rules).href)
const linter = new Linter({ configType: "flat" })
const config = [{ files: ["**/*.jsx"], languageOptions: { ecmaVersion: "latest", sourceType: "module",
  parserOptions: { ecmaFeatures: { jsx: true } } }, plugins: { design: designPlugin },
  rules: { "design/no-handmade-ui": "error", "design/no-card-in-card": "error" } }]
const cases = JSON.parse(readFileSync(0, "utf8"))
const out = {}
for (const [name, code] of Object.entries(cases))
  out[name] = linter.verify(code, config, { filename: "page.jsx" }).map((m) => m.fatal ? "FATAL " + m.message : `${m.ruleId}:${m.messageId}|${m.message}`)
process.stdout.write(JSON.stringify(out))
"""


def run_rules(src: str, cases: dict[str, str]) -> dict[str, list[str]]:
    """Lint each snippet with the design rules of a generated preset; {name: ["rule:messageId|message"]}."""
    home = node_project()
    with tempfile.TemporaryDirectory() as d:
        rules = Path(d) / "rules.mjs"
        rules.write_text(src[src.index(sdl.RULES_BEGIN):src.index(sdl.RULES_END)])
        runner = Path(d) / "run.mjs"
        runner.write_text(RULE_RUNNER)
        r = subprocess.run(["node", str(runner), str(home), str(rules)], input=json.dumps(cases),
                           capture_output=True, text=True, check=False)
        if r.returncode:
            raise AssertionError(r.stderr)
        return json.loads(r.stdout)

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
    # data residency and the wireframe canvas are decided at the same crossing; not under test here
    write(root, ".workflow/meta.json", {"project_slug": "t", "phase": phase,
                                        "stack": {"data_residency": "none", **stack},
                                        "wireframes": {"skipped": True, "reason": "not under test here"}})


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

    def test_preset_export_never_closes_existing_subpaths(self) -> None:
        # predictionleagues: no exports map, the app imports "@x/eslint-config/nextjs.js"
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            pkg = write(root, "cfg/package.json", {"name": "@x/eslint-config", "main": "base.js"})
            spec = sdl.export_preset(root / "cfg", root / "cfg/design-system.mjs")
            self.assertEqual(spec, "@x/eslint-config/design-system.mjs")
            self.assertNotIn("exports", json.loads(pkg.read_text()))
            write(root, "cfg/package.json", {"name": "@x/eslint-config", "exports": {"./base": "./base.js"}})
            self.assertEqual(sdl.export_preset(root / "cfg", root / "cfg/design-system.mjs"),
                             "@x/eslint-config/design-system")
            self.assertEqual(json.loads(pkg.read_text())["exports"],
                             {"./base": "./base.js", "./design-system": "./design-system.mjs"})

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

    def test_golden_rule_3_import_bans(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); single_app(root)
            (u,) = sdl.detect(root)
            src = sdl.preset_source({**u, "ui": "shadcn"}, "error")
            self.assertIn('"no-restricted-imports": ["error"', src)
            self.assertIn('ignores: ["components/ui/**"]', src, "the primitives themselves import their bases")
            for banned in ('"@mui/*"', '"/radix-ui"', '"@radix-ui/react-*"', '"@base-ui/react/*"', '"/cmdk"',
                           '"/input-otp"', '"/vaul"', '"/antd"'):
                self.assertIn(banned, src)
            # gitignore-style patterns: a slash-free name matches at any depth, so a bare "input-otp"
            # banned the project's own components/ui/input-otp (FITROOM, 2026-09-22)
            for bare in ('"input-otp"', '"vaul"', '"cmdk"', '"radix-ui"', '"antd"'):
                self.assertNotIn(bare, src, f"{bare} must be anchored with a leading slash")
            for allowed in ('"sonner"', '"recharts"', '"react-day-picker"'):
                self.assertNotIn(allowed, src, "shadcn's own docs import these from app code")
            base_ui = sdl.preset_source({**u, "ui": "base-ui"}, "error")
            self.assertIn('"@mui/*"', base_ui)
            self.assertNotIn('"@base-ui/react"', base_ui, "standalone Base UI: the headless primitives are the library")

    def test_package_cn_is_banned_only_where_lib_utils_configures_the_merge(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); single_app(root)
            (u,) = sdl.detect(root)
            write(root, "lib/utils.ts", 'export { cn } from "cn"\n')
            plain = sdl.preset_source({**u, "ui": "shadcn"}, "error")
            self.assertNotIn('"name": "cn"', plain, "a stock cn: the package import is the same function")
            write(root, "lib/utils.ts", 'import { createCn } from "cn/config"\n'
                                         'export const cn = createCn({ extend: { classGroups: {} } })\n')
            src = sdl.preset_source({**u, "ui": "shadcn"}, "error")
            self.assertIn('"name": "cn", "importNames": ["cn"]', src)
            self.assertIn('ignores: ["components/ui/**", "lib/utils.ts"]', src, "lib/utils itself builds cn from the package")
            self.assertIn('files: ["components/ui/**"]', src, "shadcn add writes the package import into the primitives")
            # one object per file set: a second no-restricted-imports on the same files would replace the bans
            app_block = src.split("// cn is configured in")[0]
            self.assertIn('"patterns"', app_block)
            self.assertIn('"paths"', app_block)
            write(root, "lib/utils.ts", 'import { extendTailwindMerge } from "tailwind-merge"\n')
            self.assertIn('"name": "cn"', sdl.preset_source({**u, "ui": "shadcn"}, "error"),
                          "a tailwind-merge config is a configured merge too")

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


class HandWrittenAgentsSection(unittest.TestCase):
    def test_no_second_copy(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            write(root, "AGENTS.md", "# Rules\n\n## Design-system lint\n\nOur own words.\n")
            with contextlib.redirect_stdout(io.StringIO()):
                sdl.write_agents(root, "gate")
            text = (root / "AGENTS.md").read_text()
            self.assertEqual(text.lower().count("design-system lint"), 1)
            self.assertNotIn(sdl.AGENTS_BEGIN, text)
            # annotix: no heading, the paragraph names the plugin
            write(root, "AGENTS.md", "# Agents\n\n`apps/web` runs `@shadcn/lint`, the design-system lint.\n")
            with contextlib.redirect_stdout(io.StringIO()):
                sdl.write_agents(root, "gate")
            self.assertNotIn(sdl.AGENTS_BEGIN, (root / "AGENTS.md").read_text())


class ComponentDir(unittest.TestCase):
    def test_src_layout_behind_the_alias(self) -> None:
        # idea-validator: components.json says @/components/ui, tsconfig maps @/* to ./src/*
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); single_app(root)
            (root / "components" / "ui").rmdir()
            (root / "src" / "components" / "ui").mkdir(parents=True)
            self.assertEqual(sdl.component_dir(root), "src/components/ui")
            (u,) = sdl.detect(root)
            self.assertIn('ignores: ["src/components/ui/**"]', sdl.preset_source({**u, "ui": "shadcn"}, "warn"))
            self.assertIn('"src/app/**/showcase/**"', sdl.preset_source({**u, "ui": "shadcn"}, "warn"))


class Rerun(unittest.TestCase):
    """Re-running on a project that already has the lint must not loosen it."""

    def run_unit(self, root: Path, warnings: int, fresh: bool = False) -> int:
        (u,) = sdl.detect(root)
        u["ui"] = "shadcn"
        original = sdl.run_eslint
        sdl.run_eslint = lambda t: [{"ruleId": "no-console", "severity": 1, "message": "x", "file": "a", "line": 1}] * warnings
        try:
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                rc, _ = sdl.setup_unit(root, u, fresh)
        finally:
            sdl.run_eslint = original
        return rc

    def app(self, root: Path, cap: int | None) -> None:
        single_app(root)
        pkg = json.loads((root / "package.json").read_text())
        pkg["devDependencies"] = {"@shadcn/lint": "0.1.0"}
        pkg["scripts"]["lint"] = "eslint" + (f" --max-warnings {cap}" if cap is not None else "")
        write(root, "package.json", pkg)

    def test_severity_is_kept_after_the_phase_moves_past_scaffolded(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); self.app(root, cap=0)
            (u,) = sdl.detect(root)
            u["preset"].write_text(sdl.preset_source(u, "error"))
            self.assertEqual(self.run_unit(root, warnings=0, fresh=False), 0)
            self.assertEqual(sdl.existing_severity(u["preset"]), "error")

    def test_cap_never_rises_on_a_rerun(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); self.app(root, cap=3)
            self.run_unit(root, warnings=5)
            self.assertEqual(sdl.existing_cap(root), 3, "5 measured > cap 3: the cap stays")
            self.run_unit(root, warnings=2)
            self.assertEqual(sdl.existing_cap(root), 2, "fewer warnings lower it")
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); self.app(root, cap=None)
            self.run_unit(root, warnings=4)
            self.assertEqual(sdl.existing_cap(root), 4, "no previous cap: measured")


@unittest.skipUnless(node_project(), "needs node + an eslint install (DESIGN_LINT_NODE_PROJECT)")
class HandmadeUi(unittest.TestCase):
    """design/no-handmade-ui (R90) and design/no-card-in-card (R38), run with ESLint on the generated source.
    Every category is reported; every allowed case is not. smart-travel, 2026-10-12: 238 elements a green
    lint did not see, because a raw element imports nothing."""

    def src(self, ui: str = "shadcn", base: str = "base") -> str:
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); single_app(root)
            (u,) = sdl.detect(root)
            return sdl.preset_source({**u, "ui": ui}, "error", base=base)

    REPORTED = {
        # raw elements, one per entry in the mapping
        **{f"raw <{el}>": f"export const X = () => <{el} className=\"p-2\" />"
           for el in ("button", "label", "select", "textarea", "hr", "details", "summary", "dialog",
                      "progress", "meter", "table", "img")},
        "raw <input type=text>": 'export const X = () => <input type="text" />',
        "raw <a>": 'export const X = () => <a href="/trips" className="underline">Trips</a>',
        # hand-written ARIA roles
        **{f"role {r}": f'export const X = () => <div role="{r}" />'
           for r in ("tab", "tablist", "radio", "radiogroup", "checkbox", "switch", "menu", "menuitem",
                     "listbox", "option", "dialog", "tooltip", "progressbar", "separator")},
        # classes that redraw a primitive
        "card": 'export const X = () => <div className="rounded-xl border p-4" />',
        "card at a breakpoint": 'export const X = () => <div className="md:rounded-2xl md:border" />',
        "card with ring": 'export const X = () => <section className="rounded-lg ring-1 ring-border" />',
        "badge": 'export const X = () => <span className="rounded-full bg-muted px-2 text-xs">New</span>',
        "alert": 'export const X = () => <div className="rounded-lg bg-destructive/10 p-3 text-sm">!</div>',
        "alert soft token": 'export const X = () => <div className="bg-warning-soft/60 px-4 py-2">!</div>',
        "alert banner role status": 'export const X = () => <div role="status" className="border-b bg-warning-soft">!</div>',
        "separator": 'export const X = () => <div className="h-px w-full bg-border" />',
    }
    ALLOWED = {
        "primitive": 'import { Button } from "@/components/ui/button"\nexport const X = () => <Button>Go</Button>',
        "render prop": 'export const X = () => <Item render={<button type="button" />}>Row</Item>',
        "asChild child": 'export const X = () => <Button asChild><a href="/x">Go</a></Button>',
        "buttonVariants <a>": 'export const X = () => <a href="tel:+39" className={cn(buttonVariants({ variant: "outline" }))}>Call</a>',
        "file input": 'export const X = () => <input type="file" className="sr-only" />',
        "hidden input": 'export const X = () => <input type="hidden" name="id" value="1" />',
        "sr-only table": 'export const X = () => <table className="sr-only"><tbody /></table>',
        "next/og file": 'import { ImageResponse } from "next/og"\nexport const X = () => <img src="/a.png" />',
        "react-email file": 'import { Html } from "@react-email/components"\nexport const X = () => <hr />',
        "icon medallion": 'export const X = () => <div className="flex size-16 rounded-full bg-success-soft" />',
        "tinted strip without padding": 'export const X = () => <div className="absolute inset-0 bg-info-soft" />',
        "plain layout div": 'export const X = () => <div className="flex gap-4 rounded-xl bg-muted p-4" />',
        "solid status dot": 'export const X = () => <span className="size-2 rounded-full bg-success" />',
        "svg parts": 'export const X = () => <svg><path d="M0" /><rect /></svg>',
    }

    def test_every_category_is_reported(self) -> None:
        out = run_rules(self.src(), self.REPORTED)
        for name, msgs in out.items():
            with self.subTest(name):
                self.assertTrue(any(m.startswith("design/no-handmade-ui:") for m in msgs), (name, msgs))
                self.assertTrue(all("R90" in m for m in msgs))

    def test_allowed_cases_are_not(self) -> None:
        out = run_rules(self.src(), self.ALLOWED)
        for name, msgs in out.items():
            with self.subTest(name):
                self.assertEqual(msgs, [], name)

    def test_card_in_card(self) -> None:
        out = run_rules(self.src(), {
            "card in card": "export const X = () => <Card><div className='rounded-xl border p-4' /></Card>",
            "Card in Card": "export const X = () => <Card><CardContent><Card /></CardContent></Card>",
            "dialog in card (portal)": "export const X = () => <Card><DialogContent /></Card>",
            "choice tile in card": "export const X = () => <Card><label className='rounded-xl border p-4 has-[:checked]:ring-2'><RadioGroupItem /></label></Card>",
            "inset alert in card": "export const X = () => <Card><Alert inset /></Card>",
            "card in a render prop": "export const X = () => <Card><Popover trigger={<Card />} /></Card>",
        })
        self.assertTrue(any("no-card-in-card" in m for m in out["card in card"]))
        self.assertTrue(any("no-card-in-card" in m for m in out["Card in Card"]))
        for name in ("dialog in card (portal)", "inset alert in card", "card in a render prop"):
            self.assertEqual([m for m in out[name] if "no-card-in-card" in m], [], name)
        # the tile is a raw <label> (R90 says FieldLabel) but never a nested card (R38)
        self.assertEqual([m for m in out["choice tile in card"] if "no-card-in-card" in m], [])

    def test_messages_name_the_library_primitives(self) -> None:
        cases = {"meter": "export const X = () => <meter />", "card": "export const X = () => <div className='rounded-xl border' />",
                 "menu": "export const X = () => <div role='menu' />", "a": "export const X = () => <a href='/x' />"}
        shadcn = run_rules(self.src("shadcn", "base"), cases)
        self.assertIn("CardContent", shadcn["card"][0])
        self.assertIn("DropdownMenu", shadcn["menu"][0])
        self.assertIn("render={", shadcn["a"][0])
        self.assertIn("@/components/ui", shadcn["a"][0], "the import path comes from components.json")
        radix = run_rules(self.src("shadcn", "radix"), cases)
        self.assertIn("asChild", radix["a"][0])
        coss = run_rules(self.src("coss"), cases)
        self.assertIn("Meter", coss["meter"][0])
        self.assertIn("CardPanel", coss["card"][0])
        self.assertIn("Menu", coss["menu"][0])
        self.assertNotIn("DropdownMenu", coss["menu"][0])
        base_ui = run_rules(self.src("base-ui"), cases)
        self.assertIn("wrapper", base_ui["card"][0])

    def test_recorded_exception_turns_a_file_off(self) -> None:
        src = self.src()
        self.assertIn("export const designExceptions = [", src)
        self.assertIn("...designExceptions,", src)


class HandmadeUiConfig(unittest.TestCase):
    """The preset carries the rule at "error" whatever the phase, and --check refuses one without it."""

    def test_rule_always_error_and_card_in_card_follows_design_md(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); single_app(root)
            (u,) = sdl.detect(root)
            warn = sdl.preset_source({**u, "ui": "shadcn"}, "warn")
            self.assertIn('"design/no-handmade-ui": "error"', warn, "an existing app gets the rule at error too")
            self.assertIn('"design/no-card-in-card": "warn"', warn)
            self.assertIn('"components/ui/**"', warn.split("plugins: { design: designPlugin }")[0])
            self.assertIn('"**/emails/**"', warn)
            write(root, ".workflow/DESIGN.md", "## Cards\n\nCards may nest on the dashboard.\n")
            self.assertFalse(sdl.card_in_card_applies(root))
            off = sdl.preset_source({**u, "ui": "shadcn"}, "error", card_in_card=False)
            self.assertNotIn('"design/no-card-in-card": "error"', off)
            self.assertIn('"design/no-handmade-ui": "error"', off)

    def test_untouched_preset_is_regenerated_edited_one_gets_injected(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); single_app(root)
            (u,) = sdl.detect(root)
            u["ui"] = "shadcn"
            gen = sdl.stamp(sdl.preset_source(u, "error"))
            self.assertTrue(sdl.untouched(gen))
            # a recorded exception does not count as an edit, and survives the regeneration
            exc = gen.replace("export const designExceptions = [\n",
                              'export const designExceptions = [\n  { files: ["components/map/marks.tsx"], rules: { "design/no-handmade-ui": "off" } }, // MapLibre\n')
            self.assertTrue(sdl.untouched(exc))
            again = sdl.stamp(sdl.preset_source(u, "error", exceptions=sdl.recorded_exceptions(exc)))
            self.assertIn("components/map/marks.tsx", again)
            self.assertFalse(sdl.untouched(gen + "\nexport const i18nConfig = []\n"))
            # a legacy preset (no fingerprint, the project's own blocks): injected, nothing dropped
            legacy = ('import { plugin as shadcn } from "@shadcn/lint"\n\n/** @type {import("eslint").Linter.Config[]} */\n'
                      'export const designSystemConfig = [\n  { files: ["**/*.{ts,tsx}"], plugins: { shadcn } },\n]\n'
                      "export const i18nConfig = []\n")
            inj = sdl.inject_design_rules(legacy, u, "warn", "base", True)
            self.assertIn("export const designPlugin", inj)
            self.assertIn('"design/no-handmade-ui": "error"', inj)
            self.assertIn("export const i18nConfig = []", inj)
            self.assertLess(inj.index("export const designPlugin"), inj.index("export const designSystemConfig"))
            self.assertEqual(sdl.inject_design_rules(inj, u, "warn", "base", True), inj, "idempotent")
            self.assertIsNone(sdl.inject_design_rules("export default []\n", u, "warn", "base", True))

    def test_check_fails_without_the_rule(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); single_app(root)
            meta(root, "scaffolded", framework="next", ui="shadcn", design_lint="shadcn-lint")
            pkg = json.loads((root / "package.json").read_text())
            pkg["devDependencies"] = {"@shadcn/lint": "0.1.0"}
            write(root, "package.json", pkg)
            (u,) = sdl.detect(root)
            sdl.wire_config(root / "eslint.config.mjs", "./eslint.design-system.mjs")
            old = sdl.preset_source({**u, "ui": "shadcn"}, "error")
            before_r90 = old[:old.index(sdl.RULES_BEGIN)] + old[old.index(sdl.RULES_END) + len(sdl.RULES_END):]
            u["preset"].write_text(before_r90.replace('"design/no-handmade-ui": "error"', ""))
            ok, problems = sdl.check(root)
            self.assertFalse(ok)
            self.assertTrue(any("design/no-handmade-ui" in p for p in problems), problems)
            self.assertTrue(any("write-time guard" in p for p in problems), problems)


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
                "framework": "next", "ui": "shadcn", "design_lint": "none", "registry_intake": "none",
                "data_residency": "none"},
                "stack_config": {"design_lint_reason": "prototype, thrown away",
                                 "registry_intake_reason": "the same crossing gates registry intake; not under test here"},
                "wireframes": {"skipped": True, "reason": "not under test here"}})
            self.assertEqual(self.set_phase(root, "scaffolded").returncode, 0)
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            meta(root, "design_extracted", framework="expo-rn")
            self.assertEqual(self.set_phase(root, "scaffolded").returncode, 0)

    def test_gates_later_transitions_too(self) -> None:
        # golden rule 3 (R90): a project past `scaffolded` without the lint rule and the write-time guard is
        # refused at every later phase too, and show_state names the one-command retrofit
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); single_app(root)
            meta(root, "module_added", framework="next", ui="shadcn")
            r = self.set_phase(root, "feature_complete")
            self.assertEqual(r.returncode, 1)
            self.assertIn("design lint", r.stderr)
            out = subprocess.run([sys.executable, str(DEVFLOW / "show_state.py"), str(root)],
                                 capture_output=True, text=True, check=False).stdout
            self.assertIn("Design lint missing", out)
            self.assertIn("PRIMITIVES GUARD", out)
            self.assertIn("setup_design_lint.py", out)


if __name__ == "__main__":
    unittest.main()
