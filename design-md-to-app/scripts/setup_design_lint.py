#!/usr/bin/env python3
"""Install and wire @shadcn/lint into a dev-flow web project, or check that it is.

    setup_design_lint.py <project-root>            install + wire + measure + record (idempotent)
    setup_design_lint.py <project-root> --check    verify only, change nothing (exit 1 if not)

Two topologies, detected from disk:

  monorepo   packages/eslint-config + a packages/ui with components.json. The plugin block
             goes into packages/eslint-config/design-system.js, spread only into the UI
             packages (apps/* with components.json, and packages/ui).
  single     components.json + eslint.config.* at the root. The block goes into
             eslint.design-system.mjs next to it, spread into the existing config.

Everything here was hit on a real project before it was written down — see
references/design-system-lint.md for the evidence behind each rule:

  - declared --shadow-* tokens are allowed by exact name, read from the theme when the
    config loads; "shadow-*" was verified to let shadow-pink-500 through
  - the vendored component directory is exempt from restyle / arbitrary values / static
    classes / unknown classes; no-raw-colors and no-inline-styles stay on inside it
  - chart.tsx (runtime CSS variables) and the showcase specimen (literal values on purpose)
    are exempt from the rules they legitimately break
  - carousel.tsx and hooks/use-mobile.ts fail react-hooks/set-state-in-effect as shadcn
    delivers them; they get a per-file override, never a rewrite
  - eslint-plugin-only-warn (shadcn's monorepo template) reports every rule as a warning,
    so the gate is --max-warnings in the lint script, not the rule severity

A fresh scaffold (phase before `scaffolded`) gets rules at "error" and must come out at 0
design-lint findings — the script fails and lists them rather than capping them away. An
existing app gets "warn" and a cap at today's measured count, which only ever goes down.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

VERSION = "0.1.0"
PLUGIN = "@shadcn/lint"
TAILWIND_UIS = {"shadcn", "base-ui", "coss"}
PHASES_BEFORE_SCAFFOLD = {"empty", "idea_captured", "prd_drafted", "tasks_split",
                          "design_extracted", "monorepo_initialized"}
AGENTS_BEGIN = "<!-- BEGIN:design-system-lint -->"
AGENTS_END = "<!-- END:design-system-lint -->"


# ---------------------------------------------------------------------------------------
# meta.json — applicability and the recorded decision
# ---------------------------------------------------------------------------------------

def load_meta(root: Path) -> dict:
    p = root / ".workflow" / "meta.json"
    return json.loads(p.read_text()) if p.exists() else {}


def ui_of(meta: dict) -> str | None:
    stack = meta.get("stack", {})
    return stack.get("ui") or (stack.get("monorepo", {}).get("web", {}) or {}).get("ui")


def applicability(meta: dict) -> tuple[bool, str]:
    """Whether the design lint applies. Mirrors update_meta.py's gate — keep in sync."""
    stack = meta.get("stack", {})
    fw = stack.get("framework")
    if fw not in {"next", "monorepo"}:
        return False, f"stack.framework={fw!r} — the design lint is for Next web apps"
    if fw == "monorepo" and (stack.get("monorepo", {}) or {}).get("topology") == "mobile-only":
        return False, "monorepo without a web app"
    ui = ui_of(meta)
    if ui and ui not in TAILWIND_UIS:
        return False, f"stack.ui={ui!r} does not render with Tailwind"
    return True, "applies"


# ---------------------------------------------------------------------------------------
# Topology
# ---------------------------------------------------------------------------------------

def detect(root: Path) -> list[dict]:
    """Every place the lint has to be wired, as units.

    - shadcn monorepo (web-only / web+agent): one unit, preset in packages/eslint-config,
      spread into packages/ui and each app with a components.json
    - single app: the root itself, or — in a web+mobile monorepo, where apps/web is a full
      create-next-app with its own components.json and eslint config — each such app
    """
    cfg = root / "packages" / "eslint-config"
    ui = root / "packages" / "ui"
    if (cfg / "package.json").exists() and (ui / "components.json").exists():
        # An app renders the design system if it has its own components.json OR depends on the
        # UI package — bidmaster's apps/web has no components.json and consumes @<slug>/ui.
        # A package is only a target if it has an eslint config to spread into.
        ui_name = _pkg_name(ui)
        targets = [p for p in sorted((root / "apps").glob("*"))
                   if eslint_config_of(p) and ((p / "components.json").exists() or _depends_on(p, ui_name))]
        if eslint_config_of(ui):
            targets.append(ui)
        if not targets:
            # A unit with nothing to wire into is not a unit. Returning it made an earlier version
            # install, record "shadcn-lint" and pass --check on a project where nothing was wired.
            return []
        # ESM either way; .js only where the package says so, or Node warns and re-parses it
        esm = json.loads((cfg / "package.json").read_text()).get("type") == "module"
        return [{"kind": "monorepo", "config_pkg": cfg, "targets": targets,
                 "preset": cfg / ("design-system.js" if esm else "design-system.mjs"), "theme": theme_css(ui)}]
    units = []
    for d in [root, *sorted((root / "apps").glob("*"))]:
        if (d / "components.json").exists() and eslint_config_of(d):
            units.append({"kind": "single", "config_pkg": d, "targets": [d],
                          "preset": d / "eslint.design-system.mjs", "theme": theme_css(d)})
    return units


def _pkg_name(pkg: Path) -> str | None:
    try:
        return json.loads((pkg / "package.json").read_text()).get("name")
    except (OSError, json.JSONDecodeError):
        return None


def _depends_on(pkg: Path, name: str | None) -> bool:
    if not name:
        return False
    try:
        d = json.loads((pkg / "package.json").read_text())
    except (OSError, json.JSONDecodeError):
        return False
    return any(name in (d.get(k) or {}) for k in ("dependencies", "devDependencies", "peerDependencies"))


def why_undetected(root: Path) -> str:
    """Say exactly what is missing, instead of 'nothing found'."""
    if (root / "packages" / "eslint-config" / "package.json").exists() and (root / "packages" / "ui" / "components.json").exists():
        return ("shadcn monorepo layout found, but nothing to spread the preset into: packages/ui has "
                f"{'an' if eslint_config_of(root / 'packages' / 'ui') else 'no'} eslint config, and no app in "
                "apps/* has an eslint config together with a components.json or a dependency on the UI package")
    cands = [d for d in [root, *sorted((root / "apps").glob("*")), root / "packages" / "ui"]
             if (d / "components.json").exists()]
    if not cands:
        return "no components.json at the root, in apps/* or in packages/ui — run shadcn init first"
    notes = []
    for d in cands:
        rel = d.relative_to(root).as_posix() or "."
        lint = ""
        if (d / "package.json").exists():
            lint = json.loads((d / "package.json").read_text()).get("scripts", {}).get("lint", "")
        hint = (" — its lint script is `next lint`, which Next 16 removed; add the eslint.config.mjs "
                "create-next-app@16 writes first") if lint.strip().startswith("next lint") else ""
        notes.append(f"{rel} has components.json but no eslint.config.*{hint}")
    return "; ".join(notes)


def eslint_config_of(pkg: Path) -> Path | None:
    for name in ("eslint.config.mjs", "eslint.config.js", "eslint.config.ts"):
        if (pkg / name).exists():
            return pkg / name
    return None


def theme_css(pkg: Path) -> Path | None:
    try:
        css = json.loads((pkg / "components.json").read_text())["tailwind"]["css"]
    except (OSError, KeyError, json.JSONDecodeError):
        return None
    return (pkg / css) if css else None


def component_dir(pkg: Path) -> str:
    """The vendored primitives, as a glob relative to the package."""
    if (pkg / "src" / "components").is_dir() and pkg.name == "ui" and pkg.parent.name == "packages":
        return "src/components"
    try:
        alias = json.loads((pkg / "components.json").read_text())["aliases"]["ui"]
        rel = alias.split("/", 1)[1] if alias.startswith("@") and "/" in alias else alias
        if (pkg / rel).is_dir():
            return rel
        # "@/*" → "./src/*" in tsconfig: the alias names components/ui, the files are in src/
        if (pkg / "src" / rel).is_dir():
            return f"src/{rel}"
    except (OSError, KeyError, json.JSONDecodeError, IndexError):
        pass
    return "components/ui"


def only_warn(root: Path, topo: dict) -> bool:
    files = [*topo["config_pkg"].glob("*.js"), *topo["config_pkg"].glob("*.mjs")]
    files += [eslint_config_of(t) for t in topo["targets"]]
    return any(f and "only-warn" in f.read_text(errors="ignore") for f in files)


def package_manager(root: Path) -> str:
    for lock, pm in (("pnpm-lock.yaml", "pnpm"), ("bun.lock", "bun"), ("bun.lockb", "bun"),
                     ("yarn.lock", "yarn"), ("package-lock.json", "npm")):
        if (root / lock).exists():
            return pm
    return "npm"


# ---------------------------------------------------------------------------------------
# The preset — one template for both topologies
# ---------------------------------------------------------------------------------------

# Golden rule 3 — UI is composed only from the declared library's primitives. Two import bans,
# both verified on npm 2026-09-15 and measured at zero hits outside the UI directory across nine
# of our projects before being turned on:
# - component libraries a Tailwind/shadcn project never declares (a second design system)
FOREIGN_UI_LIBRARIES = ["@mui/*", "@chakra-ui/*", "antd", "antd/*", "@mantine/*", "@headlessui/react",
                        "@heroui/*", "@nextui-org/*", "react-bootstrap", "primereact", "primereact/*",
                        "flowbite-react", "@ark-ui/*", "@fluentui/*", "@blueprintjs/*", "semantic-ui-react",
                        "@radix-ui/themes"]
# - the headless bases the vendored primitives are built on: only components/ui may import them,
#   so app code cannot fork a primitive's behaviour by going around it. Libraries whose app-level
#   imports shadcn's own docs show (sonner's toast, recharts, react-day-picker types) are not here.
PRIMITIVE_BASES = ["radix-ui", "radix-ui/*", "@radix-ui/react-*", "@base-ui/react", "@base-ui/react/*",
                   "@base-ui-components/react", "@base-ui-components/react/*", "react-aria-components",
                   "vaul", "cmdk", "input-otp"]


def primitives_rule(topo: dict, severity: str) -> str:
    comp_globs = sorted({f"{component_dir(t)}/**" for t in topo["targets"]})
    patterns = [{"group": FOREIGN_UI_LIBRARIES,
                 "message": "Golden rule 3: this project's UI library is the one in meta.json#stack. "
                            "A second component library is not composed in; record an exception if it must be."}]
    # standalone Base UI has no components/ui: there the headless primitives ARE the library
    if topo.get("ui") != "base-ui":
        patterns.append({"group": PRIMITIVE_BASES,
                         "message": "Golden rule 3: import the primitive from components/ui, not its headless base "
                                    "— going around it forks the primitive's behaviour."})
    return f'''  // Golden rule 3 (contracts.md): compose the declared library's primitives, never go around them
  {{
    files: ["**/*.{{ts,tsx}}"],
    ignores: {json.dumps(comp_globs)},
    rules: {{ "no-restricted-imports": ["{severity}", {{ patterns: {json.dumps(patterns)} }}] }},
  }},
'''


def preset_source(topo: dict, severity: str) -> str:
    theme = topo["theme"]
    theme_rel = Path(os_relpath(theme, topo["preset"].parent)).as_posix() if theme else ""
    comp_globs = sorted({f"{component_dir(t)}/**" for t in topo["targets"]})
    chart_globs = sorted({f"{component_dir(t)}/chart.tsx" for t in topo["targets"]})
    s = severity
    return f'''// Written by design-md-to-app/scripts/setup_design_lint.py — edit the policy here,
// re-run the script to re-wire. See design-md-to-app/references/design-system-lint.md.
import {{ readFileSync }} from "node:fs"
import {{ plugin as shadcn }} from "{PLUGIN}"

// Every --shadow-<name> in @theme generates a real shadow-<name> utility, but no-raw-colors
// reads only --color-* and reports it as an undeclared colour. Allow each by exact name,
// read from the theme so a new shadow never produces a finding nobody understands.
// Never "shadow-*": verified to let shadow-pink-500 through.
function declaredShadows() {{
  try {{
    const css = readFileSync(new URL({json.dumps(theme_rel)}, import.meta.url), "utf8")
    const theme = css.match(/@theme[^{{]*\\{{([\\s\\S]*?)\\n\\}}/)?.[1] ?? ""
    return [...theme.matchAll(/--shadow-([a-z0-9-]+)\\s*:/g)].map((m) => `shadow-${{m[1]}}`)
  }} catch {{
    return []
  }}
}}

/** @type {{import("eslint").Linter.Config[]}} */
export const designSystemConfig = [
  {{
    files: ["**/*.{{ts,tsx}}"],
    plugins: {{ shadcn }},
    rules: {{
      "shadcn/no-restyle": ["{s}", {{ allow: ["layout"] }}],
      "shadcn/no-raw-colors": ["{s}", {{ allow: declaredShadows() }}],
      "shadcn/no-arbitrary-values": ["{s}", {{ allow: ["layout"] }}],
      "shadcn/no-inline-styles": "{s}",
      "shadcn/require-static-classes": "{s}",
      "shadcn/no-unknown-classes": "warn",
    }},
  }},
{primitives_rule(topo, s)}  // the vendored primitives own their appearance; the registry's own variant strings trip
  // no-unknown-classes. no-raw-colors and no-inline-styles stay on.
  {{
    files: {json.dumps(comp_globs)},
    rules: {{
      "shadcn/no-restyle": "off",
      "shadcn/no-arbitrary-values": "off",
      "shadcn/require-static-classes": "off",
      "shadcn/no-unknown-classes": "off",
    }},
  }},
  // shadcn's chart injects per-series CSS variables at runtime
  {{ files: {json.dumps(chart_globs)}, rules: {{ "shadcn/no-inline-styles": "off" }} }},
  // the DESIGN.md type specimen renders literal values on purpose
  {{
    files: ["app/**/showcase/**", "src/app/**/showcase/**"],
    rules: {{ "shadcn/no-inline-styles": "off", "shadcn/no-arbitrary-values": "off" }},
  }},
  // shadcn delivers these failing react-hooks/set-state-in-effect: an override, never a
  // rewrite, so re-adding them from the registry cannot bring the failure back
  {{
    files: {json.dumps(sorted({f"{component_dir(t)}/carousel.tsx" for t in topo["targets"]}) + ["**/hooks/use-mobile.ts"])},
    rules: {{ "react-hooks/set-state-in-effect": "off" }},
  }},
  // sidebar's skeleton calls Math.random during render (react-hooks/purity) as delivered
  {{
    files: {json.dumps(sorted({f"{component_dir(t)}/sidebar.tsx" for t in topo["targets"]}))},
    rules: {{ "react-hooks/purity": "off" }},
  }},
]
'''


def os_relpath(target: Path, start: Path) -> str:
    import os
    return os.path.relpath(target, start)


# ---------------------------------------------------------------------------------------
# Wiring — text edits that are safe to repeat
# ---------------------------------------------------------------------------------------

def wire_config(cfg: Path, import_from: str) -> bool:
    """Import designSystemConfig and spread it into the exported array. Idempotent."""
    s = cfg.read_text()
    if "designSystemConfig" in s:
        return False
    line = f'import {{ designSystemConfig }} from "{import_from}"\n'
    imports = list(re.finditer(r"^import .*$", s, re.M))
    at = imports[-1].end() + 1 if imports else 0
    s = s[:at] + line + s[at:]

    # create-next-app@16: defineConfig([ ... globalIgnores(...) ])
    m = re.search(r"((?:\n[ \t]*//[^\n]*)*)\n([ \t]*)globalIgnores\(", s)
    if m:
        # before the comments that describe globalIgnores, not between them and it
        s = s[:m.start()] + f"\n{m.group(2)}...designSystemConfig," + s[m.start():]
    else:
        # shadcn monorepo template: `export default <name>`
        m2 = re.search(r"export default (\w+)\s*$", s, re.M)
        if m2:
            s = s[:m2.start()] + f"export default [...{m2.group(1)}, ...designSystemConfig]" + s[m2.end():]
        else:
            m3 = re.search(r"(\n)(\]\s*\)?\s*;?\s*\n*(export default \w+\s*;?\s*)?)$", s)
            if not m3:
                raise SystemExit(f"cannot find where to spread the preset in {cfg} — wire it by hand")
            s = s[:m3.start()] + "\n  ...designSystemConfig," + s[m3.start():]
    cfg.write_text(s)
    return True


def set_lint_script(pkg: Path, cap: int) -> None:
    p = pkg / "package.json"
    text = p.read_text()
    d = json.loads(text)
    cur = d.get("scripts", {}).get("lint", "eslint")
    base = re.sub(r"\s*--max-warnings\s+\d+", "", cur).strip() or "eslint"
    new = f"{base} --max-warnings {cap}"
    if cur == new:
        return
    # edit the one value in place so the file keeps its formatting
    escaped = json.dumps(cur)
    if escaped in text:
        p.write_text(text.replace(f'"lint": {escaped}', f'"lint": {json.dumps(new)}', 1))
    else:
        d.setdefault("scripts", {})["lint"] = new
        p.write_text(json.dumps(d, indent=2) + "\n")


def write_agents(root: Path, gate: str) -> None:
    body = f"""{AGENTS_BEGIN}
# Design-system lint

After making changes, run the lint and fix what it reports. `@shadcn/lint` names the token or
variant to use instead — a raw colour points at a declared theme colour, `rounded-full` on a
`<Button>` points at its variants. Follow the message rather than silencing it. A class that keeps
needing an exception is a token or a variant DESIGN.md is missing: raise it instead.

{gate}

Do not edit the vendored primitives to silence a finding there.
{AGENTS_END}
"""
    p = root / "AGENTS.md"
    s = p.read_text() if p.exists() else ""
    if AGENTS_BEGIN in s:
        s = re.sub(re.escape(AGENTS_BEGIN) + r".*?" + re.escape(AGENTS_END) + r"\n?", body, s, flags=re.S)
    else:
        s = (s.rstrip() + "\n\n" if s.strip() else "") + body
    p.write_text(s)


def record(root: Path) -> None:
    p = root / ".workflow" / "meta.json"
    if not p.exists():
        return
    text = p.read_text()
    m = json.loads(text)
    if m.get("stack", {}).get("design_lint") == "shadcn-lint":
        return
    m.setdefault("stack", {})["design_lint"] = "shadcn-lint"
    p.write_text(json.dumps(m, indent=2, ensure_ascii=False) + "\n")
    prettier = root / "node_modules" / ".bin" / "prettier"
    if prettier.exists():  # keep the project's own JSON formatting
        subprocess.run([str(prettier), "--write", str(p)], capture_output=True, check=False)


# ---------------------------------------------------------------------------------------
# Measuring
# ---------------------------------------------------------------------------------------

def run_eslint(pkg: Path) -> list[dict]:
    exe = pkg / "node_modules" / ".bin" / "eslint"
    cmd = [str(exe)] if exe.exists() else ["npx", "--no-install", "eslint"]
    out = subprocess.run([*cmd, ".", "-f", "json"], cwd=pkg, capture_output=True, text=True, check=False)
    for line in out.stderr.splitlines():
        if line.startswith("[@shadcn/lint]"):
            print(f"      {line}")
    try:
        rows = json.loads(out.stdout)
    except json.JSONDecodeError:
        raise SystemExit(f"eslint did not produce a report in {pkg}:\n{out.stderr[-1500:]}")
    return [{"file": str(Path(r["filePath"]).relative_to(pkg)), **m} for r in rows for m in r["messages"]]


# ---------------------------------------------------------------------------------------
# Check
# ---------------------------------------------------------------------------------------

def check(root: Path) -> tuple[bool, list[str]]:
    meta = load_meta(root)
    ok, why = applicability(meta)
    if not ok:
        return True, [f"not applicable: {why}"]
    decision = meta.get("stack", {}).get("design_lint")
    if decision == "none":
        reason = (meta.get("stack_config", {}) or {}).get("design_lint_reason")
        return (True, [f"opted out: {reason}"]) if reason else (
            False, ['stack.design_lint is "none" but stack_config.design_lint_reason is empty — an opt-out needs its reason'])
    problems = []
    if decision != "shadcn-lint":
        problems.append('stack.design_lint is not set — run setup_design_lint.py, or record "none" with a reason')
    units = detect(root)
    if not units:
        problems.append(why_undetected(root))
        return False, problems
    for topo in units:
        pkg = json.loads((topo["config_pkg"] / "package.json").read_text())
        where = topo["config_pkg"].relative_to(root).as_posix() or "."
        if not topo["targets"]:
            problems.append(f"{where}: no package to wire the preset into")
        if PLUGIN not in {**pkg.get("dependencies", {}), **pkg.get("devDependencies", {})}:
            problems.append(f"{PLUGIN} is not installed in {where}")
        if not topo["preset"].exists():
            problems.append(f"{topo['preset'].relative_to(root)} is missing")
        for t in topo["targets"]:
            cfg = eslint_config_of(t)
            if "designSystemConfig" not in cfg.read_text():
                problems.append(f"{cfg.relative_to(root)} does not spread designSystemConfig")
            lint = json.loads((t / "package.json").read_text()).get("scripts", {}).get("lint", "")
            if only_warn(root, topo) and "--max-warnings" not in lint:
                problems.append(f"{(t / 'package.json').relative_to(root)}: eslint-plugin-only-warn is on, so "
                                "the lint script needs --max-warnings to gate anything")
    return not problems, problems or [f"design lint wired ({len(units)} unit{'s' if len(units) > 1 else ''})"]


# ---------------------------------------------------------------------------------------
# Setup
# ---------------------------------------------------------------------------------------

def setup(root: Path) -> int:
    meta = load_meta(root)
    ok, why = applicability(meta)
    if not ok:
        print(f"skipped — {why}")
        return 0
    units = detect(root)
    if not units:
        print(f"cannot wire the design lint: {why_undetected(root)}", file=sys.stderr)
        return 2
    fresh = meta.get("phase", "empty") in PHASES_BEFORE_SCAFFOLD
    any_warn_only, failed = False, False
    for topo in units:
        topo["ui"] = ui_of(meta)
        rc, warn_only = setup_unit(root, topo, fresh)
        any_warn_only |= warn_only
        failed |= rc != 0
    if failed:
        print("  not recorded — fix the above and re-run (the script is idempotent)", file=sys.stderr)
        return 1

    gate = ("Every rule in this repo reports as a warning (eslint-plugin-only-warn), so the gate is the "
            "`--max-warnings` cap in each UI package's lint script. Never raise it to make a change "
            "pass; lower it when findings are fixed." if any_warn_only else
            "The lint script carries a `--max-warnings` cap. Never raise it to make a change pass; "
            "lower it when findings are fixed.")
    write_agents(root, gate)
    record(root)
    print("  AGENTS.md updated · meta.json stack.design_lint = shadcn-lint")
    return 0


def export_preset(config_pkg: Path, preset: Path) -> str:
    """Make the preset importable from the config package; return the specifier."""
    p = config_pkg / "package.json"
    d = json.loads(p.read_text())
    if "exports" not in d:
        # no exports map means every file is importable by path; adding one would
        # close every subpath the apps already import (e.g. "…/nextjs.js")
        return f"{d['name']}/{preset.name}"
    if d["exports"].get("./design-system") != f"./{preset.name}":
        d["exports"]["./design-system"] = f"./{preset.name}"
        p.write_text(json.dumps(d, indent=2) + "\n")
    return f"{d['name']}/design-system"


def existing_severity(preset: Path) -> str | None:
    """The severity a previous run wrote. A re-run never downgrades it: a project scaffolded at
    "error" is past `scaffolded` afterwards, and reading only the phase would turn it to "warn"."""
    if not preset.exists():
        return None
    m = re.search(r'"shadcn/no-inline-styles":\s*"(error|warn)"', preset.read_text())
    return m.group(1) if m else None


def existing_cap(pkg: Path) -> int | None:
    try:
        lint = json.loads((pkg / "package.json").read_text()).get("scripts", {}).get("lint", "")
    except (OSError, json.JSONDecodeError):
        return None
    m = re.search(r"--max-warnings[ =](\d+)", lint)
    return int(m.group(1)) if m else None


def setup_unit(root: Path, topo: dict, fresh: bool) -> tuple[int, bool]:
    warn_only = only_warn(root, topo)
    severity = existing_severity(topo["preset"]) or ("error" if fresh else "warn")
    where = topo["config_pkg"].relative_to(root).as_posix() or "."
    print(f"{topo['kind']} ({where}) · {'fresh scaffold' if fresh else 'existing app'} · "
          f"only-warn={'yes' if warn_only else 'no'} · rules at {severity}")

    # 1. install, in the package that owns the lint config
    pm = package_manager(root)
    pkg_json = json.loads((topo["config_pkg"] / "package.json").read_text())
    if PLUGIN not in {**pkg_json.get("dependencies", {}), **pkg_json.get("devDependencies", {})}:
        in_workspace = topo["config_pkg"] != root
        if in_workspace and pm == "pnpm":
            cmd = ["pnpm", "--filter", pkg_json["name"], "add", "-D", f"{PLUGIN}@{VERSION}"]
        else:
            cmd = {"pnpm": ["pnpm", "add", "-D"], "bun": ["bun", "add", "-d"], "yarn": ["yarn", "add", "-D"],
                   "npm": ["npm", "install", "-D"]}[pm] + [f"{PLUGIN}@{VERSION}"]
        print("  install:", " ".join(cmd))
        r = subprocess.run(cmd, cwd=root if in_workspace and pm == "pnpm" else topo["config_pkg"],
                           capture_output=True, text=True, check=False)
        if r.returncode:
            print(r.stdout[-1500:], r.stderr[-1500:], file=sys.stderr)
            return 1, warn_only

    # 2. the preset, and the export in a monorepo
    topo["preset"].write_text(preset_source(topo, severity))
    if topo["kind"] == "monorepo":
        import_from = export_preset(topo["config_pkg"], topo["preset"])
    else:
        import_from = f"./{topo['preset'].name}"

    # 3. wire each UI package
    for t in topo["targets"]:
        changed = wire_config(eslint_config_of(t), import_from)
        print(f"  {'wired' if changed else 'already wired'}: {eslint_config_of(t).relative_to(root)}")

    # 4. measure
    failed = False
    for t in topo["targets"]:
        msgs = run_eslint(t)
        design = [m for m in msgs if (m.get("ruleId") or "").startswith("shadcn/")]
        fatal = [m for m in msgs if m.get("fatal")]
        name = t.relative_to(root).as_posix() or "."
        if fatal:
            print(f"  {name}: {len(fatal)} file(s) failed to parse", file=sys.stderr)
            failed = True
            continue
        if (fresh or severity == "error") and design:
            print(f"  {name}: {len(design)} design-lint finding(s) on a fresh scaffold — fix them, "
                  "do not cap them:", file=sys.stderr)
            for m in design[:15]:
                print(f"    {m['file']}:{m['line']}  {m['ruleId']}  {m['message'][:110]}", file=sys.stderr)
            failed = True
            continue
        # warnings that already exist and are not the design lint's (a fresh scaffold's design
        # findings were refused above), so the cap gates new ones without failing a healthy app
        cap = len([m for m in msgs if m.get("severity") == 1])
        # the cap only ever goes down: a re-run that measures more warnings than the cap allows
        # reports them and keeps the cap — raising it here would hide a regression
        previous = existing_cap(t)
        if previous is not None and cap > previous:
            name_ = t.relative_to(root).as_posix() or "."
            print(f"  {name_}: {cap} warning(s) measured, cap stays at {previous} — the lint fails until "
                  f"{cap - previous} are fixed (never raise the cap to make it pass)")
            cap = previous
        errors = [m for m in msgs if m.get("severity") == 2]
        if errors:
            lines = [f"    {m['file']}:{m['line']}  {m.get('ruleId')}  {m['message'].splitlines()[0][:100]}"
                     for m in errors[:10]]
            if fresh:
                # a scaffold must lint clean; these came with it and have to be decided now
                print(f"  {name}: {len(errors)} error(s) on a fresh scaffold that are not the design "
                      "lint's — resolve them before the phase moves:", file=sys.stderr)
                print("\n".join(lines), file=sys.stderr)
                failed = True
                continue
            # an existing app whose lint was already red: not ours to block on. The cap gates
            # warnings; these errors fail the lint on their own, exactly as they did before.
            print(f"  {name}: note — {len(errors)} error(s) already present and not the design lint's "
                  "(the lint was failing before this ran):")
            print("\n".join(lines))
        set_lint_script(t, cap)
        print(f"  {name}: {len(design)} design-lint finding(s), lint capped at --max-warnings {cap}")
    return (1 if failed else 0), warn_only


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("project_root", type=Path)
    ap.add_argument("--check", action="store_true", help="verify only; exit 1 if not wired")
    args = ap.parse_args()
    root = args.project_root.resolve()
    if args.check:
        ok, lines = check(root)
        for line in lines:
            print(("✓ " if ok else "✗ ") + line)
        return 0 if ok else 1
    return setup(root)


if __name__ == "__main__":
    sys.exit(main())
