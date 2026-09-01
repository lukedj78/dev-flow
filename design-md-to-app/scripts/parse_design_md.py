#!/usr/bin/env python3
"""Parse a DESIGN.md file (Google design.md spec) into normalized JSON.

Usage:
    python parse_design_md.py path/to/DESIGN.md

Output (stdout): JSON with shape:
    {
      "frontmatter": { "name": ..., "colors": {...}, "typography": {...}, ... },
      "resolved_components": { "<name>": { ...resolved literal values... } },
      "body_sections": { "Overview": "...", "Colors": "...", ... },
      "warnings": [ "duplicate section: Colors", ... ]
    }

Token references like "{colors.primary}" inside the components block are
resolved against the frontmatter so downstream theme code can write literal
values. Unknown tokens are reported in `warnings`.

Exits non-zero on hard parse errors (malformed YAML, unreadable file). Soft
issues (missing referenced tokens, duplicate non-fatal sections) are surfaced
in `warnings` so the caller can show them to the user.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:
    sys.stderr.write(
        "Missing dependency: pyyaml. Install with `pip install pyyaml` or "
        "`uv tool install pyyaml`.\n"
    )
    sys.exit(2)


FRONTMATTER_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*\n?(.*)\Z", re.DOTALL)
TOKEN_REF_RE = re.compile(r"\{([a-zA-Z0-9_.\-]+)\}")
HEADING_RE = re.compile(r"^##\s+(.+?)\s*$", re.MULTILINE)

# Frontmatter keys that only a Google design.md carries. One of these present is
# what separates a design system from any other Markdown file with frontmatter.
DESIGN_TOKEN_KEYS = frozenset(
    {
        "colors", "typography", "spacing", "radius", "shadows", "borders",
        "components", "theme", "themes", "fonts", "motion", "breakpoints",
        "elevation", "opacity", "icons", "layout", "grid", "tokens",
    }
)


def reject_if_not_design_md(frontmatter: dict[str, Any], path: Path) -> None:
    """Refuse a file that is Markdown-with-frontmatter but not a design system.

    `design.md` now names two unrelated things. Ours is the Google design.md
    spec: token blocks in the frontmatter. Vercel publishes a *brand guidance
    Agent Skill* at https://vercel.com/design.md whose frontmatter is exactly
    `name` + `description`, and any Agent Skill anywhere has that same shape.

    Fed one of those, this parser used to exit 0 with empty tokens — which
    downstream reads as "body-only DESIGN.md, vague prose", the case
    anti-slop-fallbacks.md answers by inventing every value. The app gets
    scaffolded, nothing warns, and not one token comes from the file.
    """
    if not frontmatter or "description" not in frontmatter:
        return  # no frontmatter, or no description: the body-only path, handled below
    if DESIGN_TOKEN_KEYS & set(frontmatter):
        return  # carries at least one token block — it is a design system
    sys.stderr.write(
        f"{path}: this is not a Google design.md.\n"
        f"  Its frontmatter is {sorted(frontmatter)} — `description` and no token "
        f"block ({', '.join(sorted(DESIGN_TOKEN_KEYS))}).\n"
        "  That is the shape of an Agent Skill, not of a design system. The name "
        "`design.md` is used for both:\n"
        "    - Google design.md  — token blocks in frontmatter; what this pipeline reads.\n"
        "    - an Agent Skill    — `name` + `description`; e.g. https://vercel.com/design.md,\n"
        "                          brand guidance for an agent, carrying no tokens at all.\n"
        "  Parsing it would yield zero tokens, downstream would treat that as a vague\n"
        "  body-only DESIGN.md, and every value in the app would be invented.\n"
    )
    raise SystemExit(2)


def split_frontmatter(text: str) -> tuple[dict[str, Any], str]:
    """Split YAML frontmatter from markdown body. Body may be empty."""
    m = FRONTMATTER_RE.match(text)
    if not m:
        # No frontmatter — body only.
        return {}, text
    raw_yaml, body = m.group(1), m.group(2)
    try:
        data = yaml.safe_load(raw_yaml) or {}
    except yaml.YAMLError as e:
        raise SystemExit(f"Malformed YAML frontmatter: {e}")
    if not isinstance(data, dict):
        raise SystemExit("YAML frontmatter must be a mapping at the top level.")
    return data, body


def resolve_ref(ref_path: str, frontmatter: dict[str, Any]) -> Any:
    """Resolve a dotted token path like 'colors.primary' against the frontmatter.

    Returns None if the path doesn't resolve.
    """
    parts = ref_path.split(".")
    cur: Any = frontmatter
    for p in parts:
        if not isinstance(cur, dict) or p not in cur:
            return None
        cur = cur[p]
    return cur


def resolve_value(value: Any, frontmatter: dict[str, Any], warnings: list[str]) -> Any:
    """Recursively resolve token references in a value.

    Strings of the exact form "{a.b.c}" become the referenced value (which may
    itself be a dict, e.g. for typography references). Embedded refs inside
    longer strings are substituted with their stringified form.
    """
    if isinstance(value, str):
        stripped = value.strip()
        if stripped.startswith("{") and stripped.endswith("}") and stripped.count("{") == 1:
            ref = stripped[1:-1]
            resolved = resolve_ref(ref, frontmatter)
            if resolved is None:
                warnings.append(f"Unresolved token reference: {{{ref}}}")
                return value
            # Recurse — the resolved value might itself contain refs.
            return resolve_value(resolved, frontmatter, warnings)
        # Embedded refs inside a longer string.
        def repl(m: re.Match[str]) -> str:
            ref = m.group(1)
            resolved = resolve_ref(ref, frontmatter)
            if resolved is None:
                warnings.append(f"Unresolved token reference: {{{ref}}}")
                return m.group(0)
            return str(resolved)
        return TOKEN_REF_RE.sub(repl, value)
    if isinstance(value, dict):
        return {k: resolve_value(v, frontmatter, warnings) for k, v in value.items()}
    if isinstance(value, list):
        return [resolve_value(v, frontmatter, warnings) for v in value]
    return value


def parse_body_sections(body: str) -> tuple[dict[str, str], list[str]]:
    """Split markdown body into sections keyed by H2 heading.

    Returns (sections, warnings). Duplicate headings are flagged per spec.
    """
    sections: dict[str, str] = {}
    warnings: list[str] = []
    matches = list(HEADING_RE.finditer(body))
    if not matches:
        # No H2 sections — return whole body under "_prelude" if non-empty.
        text = body.strip()
        if text:
            sections["_prelude"] = text
        return sections, warnings

    # Capture any prelude before the first heading.
    if matches[0].start() > 0:
        prelude = body[: matches[0].start()].strip()
        if prelude:
            sections["_prelude"] = prelude

    for i, m in enumerate(matches):
        heading = m.group(1).strip()
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(body)
        content = body[start:end].strip()
        if heading in sections:
            warnings.append(f"Duplicate section heading: {heading!r}")
            # Per the spec, duplicate top-level sections should be rejected.
            # We surface as warning rather than crash — the caller can decide.
            sections[f"{heading} (duplicate {i})"] = content
        else:
            sections[heading] = content
    return sections, warnings


def resolve_components(frontmatter: dict[str, Any], warnings: list[str]) -> dict[str, Any]:
    """Resolve every value inside the `components` block to literals."""
    components = frontmatter.get("components")
    if not isinstance(components, dict):
        return {}
    return {name: resolve_value(props, frontmatter, warnings) for name, props in components.items()}


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        sys.stderr.write("Usage: parse_design_md.py path/to/DESIGN.md\n")
        return 2
    path = Path(argv[1])
    if not path.is_file():
        sys.stderr.write(f"File not found: {path}\n")
        return 2

    text = path.read_text(encoding="utf-8")
    frontmatter, body = split_frontmatter(text)
    body_sections, body_warnings = parse_body_sections(body)
    warnings: list[str] = list(body_warnings)
    reject_if_not_design_md(frontmatter, path)
    resolved_components = resolve_components(frontmatter, warnings)
    if not (DESIGN_TOKEN_KEYS & set(frontmatter or {})):
        warnings.append(
            "no token block in frontmatter — body-only DESIGN.md. Downstream must "
            "apply design-md-to-app/references/anti-slop-fallbacks.md rather than "
            "invent values freely."
        )

    out = {
        "frontmatter": frontmatter,
        "resolved_components": resolved_components,
        "body_sections": body_sections,
        "warnings": warnings,
    }
    # `default=str` because PyYAML turns an unquoted `created: 2026-05-09` into a
    # datetime.date, which json.dump cannot serialize: it raised after already
    # streaming half the object to stdout, so the caller got truncated JSON and a
    # traceback. Dates are metadata here, never tokens — stringifying is lossless
    # for every consumer.
    json.dump(out, sys.stdout, indent=2, ensure_ascii=False, default=str)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
