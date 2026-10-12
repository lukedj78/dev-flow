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

Golden rule 3, the half no import shows (R90, smart-travel 2026-10-12 — 238 hand-made elements behind a
green lint): the preset also defines `designPlugin` with design/no-handmade-ui (always "error") and
design/no-card-in-card, then setup calls setup_primitives_guard.py, which installs the write-time guard
(Claude Code hooks). --check fails without either. A preset the project has edited is not replaced: the
two rules are injected into it (the fingerprint line says whether it is still this script's output).

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


def anchored(group: list[str]) -> list[str]:
    """Anchor slash-free package names ("input-otp" → "/input-otp").

    `no-restricted-imports` patterns are gitignore-style: a name without a slash matches that
    segment at ANY depth, so "input-otp" also banned the project's own primitive
    `@/components/ui/input-otp` (shadcn ships components/ui/input-otp.tsx), and "vaul" would ban
    any `…/vaul/…` path. A leading slash anchors it to the import root: the package and its
    subpaths stay banned, local paths that merely contain the name are not. Names that already
    contain a slash (scoped packages, `radix-ui/*`) are anchored by gitignore rules already.
    Verified with eslint 10.11 on 2026-09-22 (FITROOM).
    """
    return [p if "/" in p else f"/{p}" for p in group]


# A `cn` taught the project's own theme (a type scale tailwind-merge's stock tables file under
# text-color). Since Sep 2026 shadcn's registry imports `cn` from the `cn` package directly, which is
# the *stock* instance: in a project like this, every freshly added primitive would bypass the config
# and silently drop classes it keeps apart. There — and only there — the package import is banned.
MERGE_CONFIG = re.compile(r"\b(createCn|extendTailwindMerge)\b")


def configured_cn(topo: dict) -> list[str]:
    """lib/utils files (relative to their package) that export a configured cn."""
    out = set()
    for t in topo["targets"]:
        for rel in ("lib/utils.ts", "src/lib/utils.ts"):
            f = t / rel
            if f.is_file() and MERGE_CONFIG.search(f.read_text(errors="ignore")):
                out.add(rel)
    return sorted(out)


def primitives_rule(topo: dict, severity: str) -> str:
    comp_globs = sorted({f"{component_dir(t)}/**" for t in topo["targets"]})
    utils = configured_cn(topo)
    cn_paths = [{"name": "cn", "importNames": ["cn"],
                 "message": "This project configures class merging in lib/utils (its own type scale): import cn from "
                            "there. The package's cn uses the stock tables and silently drops classes the config keeps "
                            "apart. `shadcn add` writes the package import since Sep 2026: rewrite it."}] if utils else []
    patterns = [{"group": anchored(FOREIGN_UI_LIBRARIES),
                 "message": "Golden rule 3: this project's UI library is the one in meta.json#stack. "
                            "A second component library is not composed in; record an exception if it must be."}]
    # standalone Base UI has no components/ui: there the headless primitives ARE the library
    if topo.get("ui") != "base-ui":
        patterns.append({"group": anchored(PRIMITIVE_BASES),
                         "message": "Golden rule 3: import the primitive from components/ui, not its headless base "
                                    "— going around it forks the primitive's behaviour."})
    options = {"patterns": patterns, **({"paths": cn_paths} if cn_paths else {})}
    out = f'''  // Golden rule 3 (contracts.md): compose the declared library's primitives, never go around them
  {{
    files: ["**/*.{{ts,tsx}}"],
    ignores: {json.dumps(comp_globs + utils)},
    rules: {{ "no-restricted-imports": ["{severity}", {json.dumps(options)}] }},
  }},
'''
    if cn_paths:
        # one flat-config object per file set: a later "no-restricted-imports" replaces an earlier one, never merges
        out += f'''  // cn is configured in {", ".join(utils)}: the primitives import it from there too
  {{
    files: {json.dumps(comp_globs)},
    rules: {{ "no-restricted-imports": ["{severity}", {json.dumps({"paths": cn_paths})}] }},
  }},
'''
    return out


# ---------------------------------------------------------------------------------------
# Golden rule 3, the half no import ban can see — design/no-handmade-ui (R90) and
# design/no-card-in-card (R38). smart-travel, 2026-10-12: after three days of agents building
# against a green lint, an audit found 238 hand-made elements where a primitive existed — 84
# div-cards, 62 <button>, 34 <label>, 22 alert boxes, 14 <a>, 11 span-badges. A raw element with
# Tailwind classes imports nothing, so the import bans above could not see one of them; and
# shadcn/no-restyle punishes restyling a primitive, which made writing the element by hand the
# path of least resistance whenever a board did not match a variant. The rule below is the one
# smart-travel's eslint.design-system.mjs runs (238 findings, no false positive among the
# allowed cases), generalised: the primitive names come from the library's mapping.
# ---------------------------------------------------------------------------------------

def ui_base_of(meta: dict, topo: dict) -> str:
    """base | radix | aria — how a primitive composes a foreign element (render vs asChild)."""
    ui = topo.get("ui")
    if ui in {"coss", "base-ui"}:
        return "base"
    base = (meta.get("stack") or {}).get("ui_base")
    if base:
        return base
    try:
        style = json.loads((topo["targets"][0] / "components.json").read_text()).get("style", "")
    except (OSError, IndexError, json.JSONDecodeError):
        style = ""
    return "radix" if style and not style.startswith("base-") else "base"


def ui_import_path(topo: dict) -> str:
    """Where the primitives are imported from, as the messages should say it."""
    for t in topo["targets"]:
        try:
            return json.loads((t / "components.json").read_text())["aliases"]["ui"]
        except (OSError, KeyError, json.JSONDecodeError):
            continue
    return "components/ui"


def library_primitives(ui: str | None, base: str) -> dict:
    """The primitive each hand-made pattern should have been, per library.

    shadcn (any base) and coss share most names; coss calls the card body CardPanel, the menu Menu
    and the tab TabsTab, and has Meter. Standalone Base UI has no Card, Badge, Alert or Table: the
    project wraps them in components/ui itself, so the message names the wrapper to use or add."""
    c = "asChild" if base == "radix" else "render={<…/>}"
    if ui == "coss":
        raw = {
            "button": f"Button (variant link for a link in a sentence), Toggle/ToggleGroup for a chip, or a primitive's {c} for a clickable row",
            "label": "Label, or the label part of Field (a choice tile is a Label around a Radio/Checkbox)",
            "input": "Input, InputGroup, NumberField, Checkbox, Switch or RadioGroup",
            "select": "Select or Combobox", "textarea": "Textarea", "hr": "Separator",
            "details": "Collapsible or Accordion", "summary": "CollapsibleTrigger or AccordionTrigger",
            "dialog": "Dialog, Sheet or AlertDialog", "progress": "Progress", "meter": "Meter", "table": "Table",
            "img": "next/image (Image), or Avatar for a person or an organisation",
            "a": f"next/link (Link), Button with {c} for a link styled as a button, buttonVariants on the <a> (a download, tel:, mailto:)",
        }
        roles = {"menu": "Menu", "menuitem": "Menu", "tab": "Tabs (TabsTab)", "tablist": "Tabs (TabsList)",
                 "tabpanel": "Tabs (TabsPanel)", "listbox": "Select, Combobox or Autocomplete",
                 "option": "Select, Combobox or Autocomplete", "meter": "Meter"}
        card = "Card (CardPanel), or Frame / Empty"
    elif ui == "base-ui":
        raw = {
            "button": "the Button wrapper (Toggle/ToggleGroup for a chip)", "label": "Field.Label inside a Field wrapper",
            "input": "the Input / Checkbox / Switch / Radio / NumberField wrappers", "select": "the Select or Combobox wrapper",
            "textarea": "Field.Control render={<textarea/>} in the Field wrapper", "hr": "the Separator wrapper",
            "details": "the Collapsible or Accordion wrapper", "summary": "the Collapsible / Accordion trigger",
            "dialog": "the Dialog or AlertDialog wrapper", "progress": "the Progress wrapper", "meter": "the Meter wrapper",
            "table": "the Table wrapper (add it to components/ui if missing)",
            "img": "next/image (Image), or the Avatar wrapper",
            "a": "next/link (Link), or a wrapper's render={<a/>} for a link styled as a control",
        }
        roles = {"menu": "the Menu wrapper", "menuitem": "the Menu wrapper", "tab": "the Tabs wrapper",
                 "tablist": "the Tabs wrapper", "tabpanel": "the Tabs wrapper", "listbox": "the Select or Combobox wrapper",
                 "option": "the Select or Combobox wrapper", "meter": "the Meter wrapper"}
        card = "the Card wrapper in components/ui (add it there, from DESIGN.md, if it does not exist)"
    else:  # shadcn, on base / radix / aria
        raw = {
            "button": f"Button (variant link for a link in a sentence), Toggle/ToggleGroup for a chip, Item {c} for a clickable row or tile",
            "label": "Label, or FieldLabel inside a Field (a choice tile is FieldLabel around Field orientation=\"horizontal\" with RadioGroupItem/Checkbox)",
            "input": "Input, InputGroup, Checkbox, Switch, RadioGroup or InputOTP",
            "select": "Select or NativeSelect", "textarea": "Textarea", "hr": "Separator",
            "details": "Collapsible or Accordion", "summary": "CollapsibleTrigger or AccordionTrigger",
            "dialog": "Dialog, Sheet, Drawer or AlertDialog", "progress": "Progress", "meter": "Progress", "table": "Table",
            "img": "next/image (Image), or Avatar for a person or an organisation",
            "a": f"next/link (Link) or Button {c} (internal), Button variant link with {c} (a link in a sentence), buttonVariants on the <a> (a download, tel:, mailto:)",
        }
        roles = {"menu": "DropdownMenu", "menuitem": "DropdownMenu", "tab": "Tabs", "tablist": "Tabs", "tabpanel": "Tabs",
                 "listbox": "Select or Combobox", "option": "Select or Combobox", "meter": "Progress"}
        card = "Card (CardContent, size sm), Item for a row, or Empty for a dashed placeholder"
    w = "" if ui == "base-ui" else " "
    shared_roles = {"radio": "RadioGroup or ToggleGroup", "radiogroup": "RadioGroup or ToggleGroup",
                    "checkbox": "Checkbox or Toggle", "switch": "Switch", "dialog": "Dialog", "tooltip": "Tooltip",
                    "progressbar": "Progress", "separator": "Separator"}
    if ui == "base-ui":
        shared_roles = {k: f"the {v.split(' or ')[0]} wrapper" for k, v in shared_roles.items()}
    return {
        "raw": raw,
        "roles": {**shared_roles, **roles},
        "card": card + " — the primitive's radius and ring or border, not a copy.",
        "badge": ("the Badge wrapper" if ui == "base-ui" else "Badge") + f"{w}with one of the variants declared in badge.tsx",
        "alert": ("the Alert wrapper" if ui == "base-ui" else "Alert") + " (its variants), or the field's error part for a field's message",
        "separator": ("the Separator wrapper" if ui == "base-ui" else "Separator") + " (orientation vertical for a column rule)",
    }


# The overlay parts that render in a portal (not inside the card they are written in) and the boxes,
# across shadcn's and coss's names.
BOX_COMPONENTS = ["Card", "Alert", "Frame", "PopoverContent", "DialogContent", "SheetContent", "DrawerContent",
                  "AlertDialogContent", "PopoverPopup", "DialogPopup", "SheetPopup", "AlertDialogPopup", "ResponsiveDialog"]
OVERLAYS = [b for b in BOX_COMPONENTS if b not in {"Card", "Alert", "Frame"}]
CHOICE_COMPONENTS = ["RadioGroupItem", "Radio", "Checkbox", "Switch", "Toggle", "ToggleGroupItem"]

RULES_BEGIN = "// BEGIN:design-rules — written by setup_design_lint.py (R38, R90)"
RULES_END = "// END:design-rules"

DESIGN_RULES_JS = r'''// BEGIN:design-rules — written by setup_design_lint.py (R38, R90)
// R38 «No card inside a card»: a box — a Card, or an element whose static className draws a full border or a
// shadow with a rounded corner — never sits inside another box written in the same component. Inside a card,
// groups are rows with dividers, titled sections, or a soft background with neither border nor shadow.
// Choice tiles (a <label>, role radio/checkbox, a RadioGroupItem/Checkbox inside, or a checked-state class)
// are controls and allowed. Only unprefixed classes count: `md:border` is the page's frame at a breakpoint.
const BOX_COMPONENTS = new Set(__BOXES__)
const OVERLAYS = new Set(__OVERLAYS__)
const CHOICE_COMPONENTS = new Set(__CHOICES__)
function staticClass(node) {
  const attr = node.openingElement.attributes.find((a) => a.type === "JSXAttribute" && a.name?.name === "className")
  if (!attr?.value) return ""
  const parts = []
  const visit = (n) => {
    if (!n) return
    if (n.type === "Literal" && typeof n.value === "string") parts.push(n.value)
    else if (n.type === "TemplateLiteral") n.quasis.forEach((q) => parts.push(q.value.cooked ?? ""))
    else if (n.type === "JSXExpressionContainer") visit(n.expression)
    else if (n.type === "CallExpression") n.arguments.forEach(visit)
    else if (n.type === "ConditionalExpression") { visit(n.consequent); visit(n.alternate) }
    else if (n.type === "LogicalExpression") visit(n.right)
  }
  visit(attr.value)
  return parts.join(" ")
}
const nameOf = (node) => (node.openingElement.name.type === "JSXIdentifier" ? node.openingElement.name.name : node.openingElement.name.type === "JSXMemberExpression" ? node.openingElement.name.property.name : "")
const attrOf = (node, name) => node.openingElement.attributes.find((a) => a.type === "JSXAttribute" && a.name?.name === name)
const literalAttr = (node, name) => {
  const v = attrOf(node, name)?.value
  return v?.type === "Literal" ? v.value : v?.type === "JSXExpressionContainer" && v.expression.type === "Literal" ? v.expression.value : undefined
}
function isChoice(node) {
  const name = nameOf(node)
  if (name === "label" || CHOICE_COMPONENTS.has(name)) return true
  const role = literalAttr(node, "role")
  if (["radio", "checkbox", "option", "switch", "tab"].includes(role)) return true
  return /has-\[[^\]]*:checked\]|has-data-checked|has-aria-checked|aria-pressed:|data-checked:|aria-checked:/.test(staticClass(node))
}
function isBox(node) {
  const name = nameOf(node)
  // a project Alert that drops its border inside a card (an `inset` variant)
  if (name === "Alert" && attrOf(node, "inset")) return false
  if (BOX_COMPONENTS.has(name)) return true
  if (!/^[a-z]/.test(name) && name !== "Link") return false
  const tokens = staticClass(node).split(/\s+/)
  const rounded = tokens.some((c) => /^rounded(-(md|lg|xl|2xl|3xl|4xl))?$/.test(c))
  const border = tokens.some((c) => /^border(-[0-9])?$/.test(c)) && !tokens.includes("border-dashed") && !tokens.includes("border-transparent")
  const shadow = tokens.some((c) => /^shadow(-(xs|sm|md|lg|xl|2xl|card|float))?$/.test(c))
  return rounded && (border || shadow)
}
const cardInCard = {
  meta: { type: "suggestion", messages: { nested: "R38 «No card inside a card»: this {{child}} sits inside the {{parent}} box above it. Inside a card, use rows with dividers, a titled section, or a soft background (bg-muted, no border or shadow). Choice tiles are allowed." } },
  create(context) {
    return {
      JSXElement(node) {
        // an overlay (dialog, sheet, popover) renders in a portal: not inside the card it is written in
        if (!isBox(node) || isChoice(node) || OVERLAYS.has(nameOf(node))) return
        for (let p = node.parent; p; p = p.parent) {
          if (p.type === "JSXAttribute") return // a render prop or slot: another tree
          if (p.type !== "JSXElement") continue
          if (isChoice(p)) return
          if (isBox(p)) {
            context.report({ node: node.openingElement, messageId: "nested", data: { child: nameOf(node), parent: nameOf(p) } })
            return
          }
        }
      },
    }
  },
}

// R90 «The primitive wins» (golden rule 3, dev-flow contracts.md): every piece of UI is a primitive from
// __WHERE__, used as it is. A raw element, a hand-written ARIA role, or a <div>/<span> whose classes redraw a
// primitive (a card, a badge, an alert, a separator) is reported with the primitive to use. When a board
// differs from the primitive, the primitive wins and the board is corrected; a missing variant STOPS the
// work — it is proposed in DESIGN.md and the user decides — it never licenses an element by hand.
// Allowed: an element passed as a primitive's `render` (or the child of an `asChild`), an <a> styled by
// buttonVariants (downloads, tel:, mailto:), a hidden or file input, an sr-only data table, a file that
// renders no DOM (next/og, react-email, react-pdf), and an exception recorded below with its reason.
// A tinted box counts as an alert only with padding or role status/alert: a size-16 icon medallion on
// bg-success-soft, or a swipe action's uncovered strip, is not one.
const RAW = __RAW__
const ROLE_PRIMITIVE = __ROLES__
const NON_DOM = /^(next\/og|@vercel\/og|satori|@react-email\/|react-email|@react-pdf\/|@formepdf\/|react-native|@react-three\/fiber)/
/** Passed as a primitive's `render` (or any other prop), or the child an `asChild` primitive renders as. */
function isComposed(node) {
  const parent = node.parent
  if (parent?.type === "JSXElement" && /^[A-Z]/.test(nameOf(parent)) && attrOf(parent, "asChild")) return true
  for (let p = parent; p; p = p.parent) {
    if (p.type === "JSXAttribute") return true
    if (p.type === "JSXElement" || p.type === "JSXFragment") return false
  }
  return false
}
function callsVariants(node) {
  const v = attrOf(node, "className")?.value
  let found = false
  const visit = (n) => {
    if (!n || found) return
    if (n.type === "CallExpression") {
      if (n.callee.type === "Identifier" && /Variants$/.test(n.callee.name)) found = true
      else n.arguments.forEach(visit)
    } else if (n.type === "JSXExpressionContainer") visit(n.expression)
    else if (n.type === "ConditionalExpression") { visit(n.consequent); visit(n.alternate) }
    else if (n.type === "LogicalExpression") { visit(n.left); visit(n.right) }
  }
  visit(v)
  return found
}
/** The classes without breakpoint/state prefixes: `md:rounded-xl md:border` still draws a card. */
const bareTokens = (node) => staticClass(node).split(/\s+/).filter(Boolean).map((c) => c.split(":").pop())
const handmade = {
  meta: {
    type: "problem",
    messages: __MESSAGES__,
  },
  create(context) {
    let nonDom = false
    return {
      ImportDeclaration(node) {
        if (NON_DOM.test(String(node.source.value))) nonDom = true
      },
      JSXElement(node) {
        const el = nameOf(node)
        if (nonDom || !/^[a-z]/.test(el) || isComposed(node)) return
        if (RAW[el]) {
          if (el === "a" && callsVariants(node)) return
          if (el === "input" && ["file", "hidden"].includes(literalAttr(node, "type"))) return
          if (el === "table" && /\bsr-only\b/.test(staticClass(node))) return
          context.report({ node: node.openingElement, messageId: "raw", data: { el, use: RAW[el] } })
          return
        }
        const role = literalAttr(node, "role")
        if (typeof role === "string" && ROLE_PRIMITIVE[role]) {
          context.report({ node: node.openingElement, messageId: "role", data: { role, use: ROLE_PRIMITIVE[role] } })
          return
        }
        const t = bareTokens(node)
        const has = (re) => t.some((c) => re.test(c))
        if (has(/^(h-px|w-px)$/) && has(/^bg-/)) return context.report({ node: node.openingElement, messageId: "separator" })
        if (has(/^bg-(destructive|danger|error|warning|success|info)(-(soft|subtle|muted)(\/\d+)?|\/\d+)$/) && (has(/^p[xy]?-/) || role === "status" || role === "alert") && !has(/^rounded-full$/) && el !== "span") return context.report({ node: node.openingElement, messageId: "alert" })
        if (el === "span" && has(/^rounded(-(sm|md|full))?$/) && has(/^px-/) && has(/^text-(2xs|xs)$/) && has(/^bg-/)) return context.report({ node: node.openingElement, messageId: "badge" })
        if (has(/^rounded-(lg|xl|2xl|3xl)$/) && has(/^(border|border-[0-9]|ring-1)$/)) context.report({ node: node.openingElement, messageId: "card" })
      },
    }
  },
}
export const designPlugin = { rules: { "no-card-in-card": cardInCard, "no-handmade-ui": handmade } }

// Recorded exceptions: a file that legitimately draws outside the primitives (map marks inside MapLibre,
// a canvas), each with its reason. Kept verbatim when the script re-runs. Never for a missing variant.
// BEGIN:recorded-exceptions
export const designExceptions = [
  // { files: ["components/map/map-marks.tsx"], rules: { "design/no-handmade-ui": "off" } }, // reason
]
// END:recorded-exceptions
// END:design-rules
'''

# the DESIGN.md specimen (app/showcase) renders swatches and state matrices on purpose, with helpers vendored
# from shadcn's own skill (assets/showcase/, kept diffable against upstream): a specimen, not product UI
HANDMADE_IGNORES = ["**/*.test.{tsx,jsx}", "**/*.spec.{tsx,jsx}", "**/*.stories.{tsx,jsx}", "**/emails/**",
                    "app/**/showcase/**", "src/app/**/showcase/**"]
CARD_IN_CARD_OPT_OUT = re.compile(
    r"cards?\s+(may|can)\s+nest|nested\s+cards?\s+(are\s+)?allowed|design-lint:\s*allow\s+card-in-card", re.I)


def card_in_card_applies(root: Path) -> bool:
    """R38 is on unless DESIGN.md says cards may nest. Nesting boxes is the most common way a generated
    screen reads as generated (a border inside a border inside a border), and smart-travel's DESIGN.md
    made it a rule after the first review; a design that wants nested cards says so in one line."""
    for p in (root / ".workflow" / "DESIGN.md", root / "DESIGN.md"):
        if p.exists() and CARD_IN_CARD_OPT_OUT.search(p.read_text(errors="ignore")):
            return False
    return True


def design_rules_source(topo: dict, base: str = "base", exceptions: str | None = None) -> str:
    lib = library_primitives(topo.get("ui"), base)
    where = ui_import_path(topo)
    messages = {
        "raw": f"R90 «The primitive wins»: a hand-written <{{{{el}}}}>. Use {{{{use}}}} from {where}. No primitive or variant fits: stop and ask — propose the variant in DESIGN.md, never draw it by hand.",
        "role": f"R90 «The primitive wins»: role=\"{{{{role}}}}\" written by hand. Use {{{{use}}}} from {where}.",
        "card": f"R90 «The primitive wins»: these classes redraw a card. Use {lib['card']}",
        "badge": f"R90 «The primitive wins»: these classes redraw a badge. Use {lib['badge']} — a missing one is proposed in DESIGN.md, never drawn by hand.",
        "alert": f"R90 «The primitive wins»: these classes redraw an alert. Use {lib['alert']}.",
        "separator": f"R90 «The primitive wins»: these classes redraw a separator. Use {lib['separator']}.",
    }
    src = (DESIGN_RULES_JS
           .replace("__BOXES__", json.dumps(BOX_COMPONENTS))
           .replace("__OVERLAYS__", json.dumps(OVERLAYS))
           .replace("__CHOICES__", json.dumps(CHOICE_COMPONENTS))
           .replace("__WHERE__", where)
           .replace("__RAW__", json.dumps(lib["raw"], ensure_ascii=False))
           .replace("__ROLES__", json.dumps(lib["roles"], ensure_ascii=False))
           .replace("__MESSAGES__", json.dumps(messages, ensure_ascii=False)))
    if exceptions is not None:
        src = re.sub(r"// BEGIN:recorded-exceptions\n.*?// END:recorded-exceptions\n",
                     lambda _: exceptions, src, flags=re.S)
    return src


def recorded_exceptions(preset_text: str) -> str | None:
    m = re.search(r"// BEGIN:recorded-exceptions\n.*?// END:recorded-exceptions\n", preset_text, re.S)
    return m.group(0) if m else None


def design_rules_config(topo: dict, card_severity: str, card_in_card: bool) -> str:
    comp_globs = sorted({f"{component_dir(t)}/**" for t in topo["targets"]})
    rules = {"design/no-handmade-ui": "error"}
    if card_in_card:
        rules["design/no-card-in-card"] = card_severity
    return f'''  // Golden rule 3, the half no import shows: a hand-made element where a primitive exists (R90, always
  // "error"), and no card inside a card (R38{"" if card_in_card else " — off: DESIGN.md lets cards nest"}).
  {{
    files: ["**/*.{{tsx,jsx}}"],
    ignores: {json.dumps(comp_globs + HANDMADE_IGNORES)},
    plugins: {{ design: designPlugin }},
    rules: {json.dumps(rules)},
  }},
  ...designExceptions,
'''


def preset_source(topo: dict, severity: str, *, base: str = "base", card_in_card: bool = True,
                  exceptions: str | None = None) -> str:
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

{design_rules_source(topo, base, exceptions)}
/** @type {{import("eslint").Linter.Config[]}} */
export const designSystemConfig = [
{design_rules_config(topo, s, card_in_card)}  {{
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


FINGERPRINT = re.compile(r"^// fingerprint: ([0-9a-f]{16})\n", re.M)
HANDMADE_ERROR = re.compile(r'"design/no-handmade-ui"\s*:\s*(\[\s*)?"error"')


def _fingerprint_of(text: str) -> str:
    import hashlib
    body = FINGERPRINT.sub("", text)
    body = re.sub(r"// BEGIN:recorded-exceptions\n.*?// END:recorded-exceptions\n", "", body, flags=re.S)
    return hashlib.sha256(body.encode()).hexdigest()[:16]


def stamp(src: str) -> str:
    """Mark the preset as this script's output: a re-run may replace it only while the mark still matches."""
    first, second, rest = src.split("\n", 2)
    return f"{first}\n{second}\n// fingerprint: {_fingerprint_of(src)}\n{rest}"


def untouched(text: str) -> bool:
    """Written by this script and not edited since — the recorded-exceptions block aside, which is kept."""
    m = FINGERPRINT.search(text)
    return bool(m) and m.group(1) == _fingerprint_of(text)


def inject_design_rules(text: str, topo: dict, severity: str, base: str, card_in_card: bool) -> str | None:
    """Add R90/R38 to a preset this script may not replace (edited by the project, or older than the
    fingerprint): the plugin before designSystemConfig, its block first inside the array. Everything the
    project wrote stays. None when there is no `export const designSystemConfig = [` to anchor on."""
    if "no-handmade-ui" in text:
        return text
    m = re.search(r"^(?:/\*\*[^\n]*\*/\n)?export const designSystemConfig\s*=\s*\[\n", text, re.M)
    if not m:
        return None
    head = text[:m.start()] + design_rules_source(topo, base) + "\n"
    decl = m.group(0)
    return head + decl + design_rules_config(topo, severity, card_in_card) + text[m.end():]


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
    elif re.search(r"^#+\s*Design[- ]system lint\b", s, re.M | re.I) or "@shadcn/lint" in s:
        # a section written by hand before this script existed (annotix, gym-saas): it is the
        # project's own, so leave it rather than appending a second copy under markers
        print("  AGENTS.md already has a design-system lint section without markers — left as is")
        return
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
        # golden rule 3's other half: a raw element imports nothing, so without this rule a green lint says
        # nothing about primitives (smart-travel, 238 hand-made elements behind a green lint)
        if topo["preset"].exists():
            text = topo["preset"].read_text()
            if not HANDMADE_ERROR.search(text) or "export const designPlugin" not in text:
                problems.append(f"{topo['preset'].relative_to(root)} has no design/no-handmade-ui at \"error\" "
                                "(golden rule 3, R90) — re-run setup_design_lint.py to add it")
    import setup_primitives_guard
    g_ok, g_lines = setup_primitives_guard.check(root)
    if not g_ok:
        problems += [f"write-time guard: {line}" for line in g_lines]
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
    # the same rule at write time: hooks that refuse hand-made UI while the agent writes it
    import setup_primitives_guard
    return setup_primitives_guard.install(root, units)


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

    # 2. the preset, and the export in a monorepo. Replaced only while it is this script's untouched
    # output; a preset the project edited (or one older than the fingerprint) keeps its own policy and
    # gets the R90/R38 rules injected — smart-travel's carries i18n and brand-logo blocks a rewrite would drop.
    meta = load_meta(root)
    base, card = ui_base_of(meta, topo), card_in_card_applies(root)
    existing = topo["preset"].read_text() if topo["preset"].exists() else None
    if existing is None or untouched(existing):
        exceptions = recorded_exceptions(existing) if existing else None
        new = stamp(preset_source(topo, severity, base=base, card_in_card=card, exceptions=exceptions))
        if new != existing:
            topo["preset"].write_text(new)
    else:
        injected = inject_design_rules(existing, topo, severity, base, card)
        if injected is None:
            print(f"  {topo['preset'].relative_to(root)}: edited by the project and no `export const "
                  "designSystemConfig = [` to add design/no-handmade-ui to — add it by hand "
                  "(references/design-system-lint.md §Hand-made UI)", file=sys.stderr)
            return 1, warn_only
        if injected != existing:
            topo["preset"].write_text(injected)
            print(f"  {topo['preset'].relative_to(root)}: edited by the project — kept, design/no-handmade-ui "
                  "and design/no-card-in-card injected")
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
        design = [m for m in msgs if (m.get("ruleId") or "").startswith(("shadcn/", "design/"))]
        handmade = [m for m in msgs if (m.get("ruleId") or "").startswith("design/") and m.get("severity") == 2]
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
        if handmade:
            # an existing app: the rule is "error" from the day it lands, so the lint stays red until they are
            # replaced by primitives — the retrofit's work list, never an eslint-disable and never a cap
            print(f"  {name}: {len(handmade)} hand-made UI finding(s) (design/no-handmade-ui, design/no-card-in-card) "
                  "— the lint fails until each is a primitive; a missing variant is proposed in DESIGN.md:")
            for m in handmade[:15]:
                print(f"    {m['file']}:{m['line']}  {m['ruleId']}  {m['message'][:110]}")
        errors = [m for m in msgs if m.get("severity") == 2 and not (m.get("ruleId") or "").startswith("design/")]
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
