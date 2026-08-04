#!/usr/bin/env python3
"""Generate .claude-plugin/plugin.json from the canonical TAXONOMY.

The plugin manifest's `skills` array is an explicit allowlist of what ships.
Generating it from the same TAXONOMY that drives skills.json means the two can
never disagree, and a skill that isn't classified can't silently ship.

Schema grounded in the official reference:
https://code.claude.com/docs/en/plugins-reference
  - `name` is the only required field.
  - `skills` is a string|array of paths. A path pointing at a directory that
    contains SKILL.md directly registers that one skill, and its invocation
    name comes from the SKILL.md frontmatter `name`.
  - Unrecognized top-level fields are ignored by Claude Code.

Usage:  python3 scripts/build_plugin_manifest.py [--check]
        --check  verify the on-disk manifest matches (CI / pre-commit), exit 1 if not
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_skills_registry import FAMILY_ORDER, TAXONOMY  # noqa: E402

# --- metadata (edit here; bump VERSION on release, see CHANGELOG.md) ---------
VERSION = "1.0.0"

MANIFEST_META = {
    "name": "dev-flow",
    "displayName": "dev-flow",
    "version": VERSION,
    "description": (
        "An end-to-end product-development skill suite: one filesystem contract "
        "(.workflow/meta.json) and 42 skills that take an idea to production — "
        "web (Next.js 16), mobile (Expo/RN), an eve agent engine, Linear/scrum, "
        "plus GDPR/AI-Act and Vercel-cost pre-deploy gates."
    ),
    "author": {"name": "lucadigerlando", "url": "https://github.com/lukedj78"},
    "homepage": "https://github.com/lukedj78/dev-flow",
    "repository": "https://github.com/lukedj78/dev-flow",
    "license": "MIT",
    "keywords": [
        "dev-flow", "skills", "nextjs", "expo", "react-native",
        "shadcn", "eve", "agent", "monorepo", "gdpr", "scrum",
    ],
}

# Skills deliberately NOT shipped (work-in-progress / deprecated). Keeping the
# folder in the repo while withholding it from the manifest is how a skill is
# staged or retired — see .out-of-scope/README.md.
EXCLUDED: set[str] = set()


def build() -> dict:
    names = [n for n in TAXONOMY if n not in EXCLUDED]
    # stable order: by family, then alphabetically — mirrors skills.json
    names.sort(key=lambda n: (FAMILY_ORDER.index(TAXONOMY[n][0]), n))
    return {**MANIFEST_META, "skills": [f"./{n}" for n in names]}


def main() -> int:
    root = Path(__file__).resolve().parent.parent
    out = root / ".claude-plugin" / "plugin.json"
    manifest = build()

    # every listed skill must actually exist on disk with a SKILL.md
    missing = [s for s in manifest["skills"] if not (root / s[2:] / "SKILL.md").is_file()]
    if missing:
        sys.stderr.write(f"ERROR: manifest lists skills with no SKILL.md: {missing}\n")
        return 1

    rendered = json.dumps(manifest, indent=2) + "\n"

    if "--check" in sys.argv:
        current = out.read_text() if out.exists() else ""
        if current != rendered:
            sys.stderr.write(
                "ERROR: .claude-plugin/plugin.json is out of date.\n"
                "       Run: python3 scripts/build_plugin_manifest.py\n"
            )
            return 1
        print(f"✓ plugin.json up to date ({len(manifest['skills'])} skills)")
        return 0

    out.parent.mkdir(exist_ok=True)
    out.write_text(rendered)
    print(f"✓ .claude-plugin/plugin.json regenerated ({len(manifest['skills'])} skills, v{VERSION})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
