#!/usr/bin/env python3
"""Build a shadcn `registry.json` from a DESIGN.md.

Reads `<root>/.workflow/DESIGN.md`, parses the YAML frontmatter, and
emits `<root>/registry.json` ready to be passed to
`npx shadcn@latest init <path>`.

Per the dev-flow contract: the codebase lives at the project root,
NOT inside `.workflow/`. So `registry.json` (a codebase artifact
shadcn reads) goes at the root too.

Usage:
    python3 build_registry.py <project-root>
        [--app-dir .]
        [--out registry.json]
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    sys.stderr.write("Missing PyYAML: pip install pyyaml\n")
    sys.exit(1)


HEX_RE = re.compile(r'^#([0-9a-fA-F]{6})([0-9a-fA-F]{2})?$')


def hex_to_hsl(hex_: str) -> str:
    """Convert #rrggbb to 'H S% L%' shadcn-style channel triple."""
    m = HEX_RE.match(hex_)
    if not m:
        return "0 0% 0%"
    r, g, b = (int(m.group(1)[i:i+2], 16) / 255.0 for i in (0, 2, 4))
    mx, mn = max(r, g, b), min(r, g, b)
    l = (mx + mn) / 2
    if mx == mn:
        h = s = 0.0
    else:
        d = mx - mn
        s = d / (2 - mx - mn) if l > 0.5 else d / (mx + mn)
        if mx == r:
            h = ((g - b) / d) + (6 if g < b else 0)
        elif mx == g:
            h = ((b - r) / d) + 2
        else:
            h = ((r - g) / d) + 4
        h /= 6
    return f"{round(h * 360)} {round(s * 100)}% {round(l * 100)}%"


def split_frontmatter(text: str) -> tuple[dict, str]:
    if not text.startswith('---'):
        return {}, text
    parts = text.split('\n---', 1)
    if len(parts) < 2:
        return {}, text
    fm_text = parts[0][3:].lstrip('\n')
    body = parts[1].split('\n', 1)[1] if '\n' in parts[1] else ''
    try:
        fm = yaml.safe_load(fm_text) or {}
    except yaml.YAMLError as e:
        sys.stderr.write(f"YAML parse error in DESIGN.md frontmatter: {e}\n")
        sys.exit(2)
    return fm, body


def derive_dark_mode(light: dict[str, str]) -> dict[str, str]:
    """Naive light → dark inversion: invert L for surfaces/foregrounds, keep brand."""
    BRAND = {'primary', 'secondary', 'tertiary', 'accent', 'destructive', 'error', 'warning', 'success', 'ring'}
    dark = {}
    for k, v in light.items():
        if any(b in k for b in BRAND) and 'foreground' not in k:
            dark[k] = v
            continue
        try:
            h, s, l = v.split()
            l_pct = float(l.rstrip('%'))
            inverted = max(0, 100 - l_pct)
            dark[k] = f"{h} {s} {inverted:.0f}%"
        except (ValueError, AttributeError):
            dark[k] = v
    return dark


def build_registry(design_md: Path, project_slug: str) -> dict:
    fm, _body = split_frontmatter(design_md.read_text(encoding='utf-8'))

    colors = fm.get('colors') or {}
    typography = fm.get('typography') or {}
    rounded = fm.get('rounded') or {}
    spacing = fm.get('spacing') or {}

    # --- cssVars.light ---
    light = {}
    for name, value in colors.items():
        if isinstance(value, str) and value.startswith('#'):
            light[name] = hex_to_hsl(value)

    # If colors don't include the canonical shadcn pair {background, foreground},
    # derive sensible defaults so init doesn't fall back to neutral grey.
    if 'background' not in light and 'surface' in light:
        light['background'] = light['surface']
    if 'foreground' not in light and 'on-surface' in light:
        light['foreground'] = light['on-surface']

    # --- cssVars.theme (font + radius) ---
    theme_vars = {}
    families = sorted({v.get('fontFamily') for v in typography.values() if isinstance(v, dict) and v.get('fontFamily')})
    for i, fam in enumerate(families):
        slug = re.sub(r'[^a-z0-9]+', '-', fam.lower()).strip('-')
        theme_vars[f"font-{slug}"] = f"var(--font-{slug})"
    if rounded.get('md'):
        theme_vars['radius'] = rounded['md']
    elif rounded.get('sm'):
        theme_vars['radius'] = rounded['sm']

    # --- tailwind.config.theme.extend ---
    tw_extend = {}
    if families:
        tw_extend['fontFamily'] = {
            re.sub(r'[^a-z0-9]+', '-', fam.lower()).strip('-'):
                [f"var(--font-{re.sub(r'[^a-z0-9]+', '-', fam.lower()).strip('-')})", "sans-serif"]
            for fam in families
        }
    if rounded:
        tw_extend['borderRadius'] = {k: v for k, v in rounded.items() if isinstance(v, str)}
    if spacing:
        tw_extend['spacing'] = {k: (v if isinstance(v, str) else f"{v}px") for k, v in spacing.items()}

    # --- assemble ---
    css_vars = {}
    if theme_vars:
        css_vars['theme'] = theme_vars
    if light:
        css_vars['light'] = light
        css_vars['dark'] = derive_dark_mode(light)

    item = {
        "name": "design-system",
        "type": "registry:style",
    }
    if css_vars:
        item['cssVars'] = css_vars
    if tw_extend:
        item['tailwind'] = {"config": {"theme": {"extend": tw_extend}}}

    return {
        "$schema": "https://ui.shadcn.com/schema/registry.json",
        "name": f"{project_slug}-design-system",
        "items": [item],
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    ap.add_argument('project_root', type=Path)
    ap.add_argument('--app-dir', default='.', help='Path to the codebase root, relative to project root (default: ".", per the contract codebase is at root)')
    ap.add_argument('--out', default='registry.json', help='Output filename, relative to app dir (default: registry.json)')
    args = ap.parse_args()

    root = args.project_root.resolve()
    design_md = root / '.workflow' / 'DESIGN.md'
    if not design_md.exists():
        sys.stderr.write(f"DESIGN.md not found at {design_md}\n")
        return 1

    meta_path = root / '.workflow' / 'meta.json'
    project_slug = 'project'
    if meta_path.exists():
        try:
            project_slug = json.loads(meta_path.read_text()).get('project_slug') or project_slug
        except json.JSONDecodeError:
            pass

    registry = build_registry(design_md, project_slug)

    out_path = root / args.app_dir / args.out
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(registry, indent=2, ensure_ascii=False) + "\n")

    item = registry['items'][0]
    n_colors = len((item.get('cssVars') or {}).get('light') or {})
    n_fonts = len([k for k in (item.get('cssVars') or {}).get('theme', {}) if k.startswith('font-')])
    print(f"Wrote {out_path}")
    print(f"  colors: {n_colors}  font families: {n_fonts}  radius: {bool((item.get('cssVars') or {}).get('theme', {}).get('radius'))}")
    return 0


if __name__ == '__main__':
    sys.exit(main())
