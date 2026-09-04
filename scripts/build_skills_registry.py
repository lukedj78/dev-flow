#!/usr/bin/env python3
"""build_skills_registry.py — regenerate skills.json from the 24 SKILL.md files

Output: skills.json at repo root, with:
  - schema_version, generated_at, generated_by
  - skill_count
  - families: {core: [...], web: [...], mobile: [...]}
  - skills: list of {name, family, role, description, skill_file,
    references, scripts, skill_md_lines, bundle}

Run from the repo root. Re-run any time SKILL.md frontmatter or references
change to keep the registry fresh. (Also called by CI — see
.github/workflows/registry-check.yml.)

Roles taxonomy:
  - orchestrator: dev-flow
  - discovery: prd-from-idea, prd-to-tasks
  - knowledge: rn-* lean docs (10 RN skills)
  - operative: all others (web skills + 5 RN operatives + bootstrap)

Families taxonomy:
  - core: stack-agnostic (dev-flow + prd-from-idea + prd-to-tasks)
  - web: Next.js / Astro / Vite + shadcn/Base-UI/MUI + module-add
  - mobile: Expo + RN + NativeWind (all rn-* skills)
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

try:
    import yaml
except ImportError:
    sys.stderr.write("PyYAML required. Install with: pip install pyyaml\n")
    sys.exit(1)


# ---------------------------------------------------------------------------
# THE TAXONOMY — single source of truth for every skill's family and role.
#
# Six families, matching README.md and install.sh exactly. Every skill on disk
# MUST appear here: an unclassified skill is a build ERROR, never a silent
# default (a silent "web" fallback is how rn-upgrade once ended up filed as a
# web skill). Adding a skill? Add its row here in the same commit.
#
# family: core | web | agent | mobile | monorepo | refactor
# role:   orchestrator | discovery | operative | knowledge
# ---------------------------------------------------------------------------
TAXONOMY: dict[str, tuple[str, str]] = {
    # --- core (7): stack-agnostic, used by every stack -----------------------
    "dev-flow":                     ("core", "orchestrator"),
    "prd-from-idea":                ("core", "discovery"),
    "prd-to-tasks":                 ("core", "discovery"),
    "linear-scrum":                 ("core", "operative"),
    "compliance-audit":             ("core", "operative"),
    "spec-review":                  ("core", "operative"),
    "product-to-agent-skill":       ("core", "operative"),
    # --- web (16): Next.js 16 App Router ------------------------------------
    "figma-to-design-md":           ("web", "discovery"),
    "image-to-design-md":           ("web", "discovery"),
    "design-md-to-app":             ("web", "operative"),
    "coss-ui":                      ("web", "operative"),
    "screenshot-to-page":           ("web", "operative"),
    "module-add":                   ("web", "operative"),
    "write-tests":                  ("web", "operative"),
    "forms":                        ("web", "operative"),
    "data-fetching":                ("web", "knowledge"),
    "state-discipline":             ("web", "knowledge"),
    "transitions":                  ("web", "knowledge"),
    "animated-icons":           ("web", "operative"),
    "vercel-doctor":                ("web", "operative"),
    "shadscan":                     ("web", "operative"),
    "vercel-deploy":                ("web", "operative"),
    "vgpu-shaders":                 ("web", "operative"),
    # --- agent (2): the eve engine ------------------------------------------
    "eve-agent":                    ("agent", "operative"),
    "eve-registry-porting":         ("agent", "operative"),
    # --- mobile (16): Expo + React Native -----------------------------------
    "rn-fundamentals":              ("mobile", "knowledge"),
    "rn-styling":                   ("mobile", "knowledge"),
    "rn-expo-router":               ("mobile", "knowledge"),
    "rn-components-apis":           ("mobile", "knowledge"),
    "rn-data-fetching":             ("mobile", "knowledge"),
    "rn-animations-gestures":       ("mobile", "knowledge"),
    "rn-push-notifications":        ("mobile", "knowledge"),
    "rn-backend":                   ("mobile", "knowledge"),
    "rn-eas-build-submit-update":   ("mobile", "knowledge"),
    "rn-publishing-payments":       ("mobile", "knowledge"),
    "rn-bootstrap":                 ("mobile", "operative"),
    "rn-add-screen":                ("mobile", "operative"),
    "rn-write-tests":               ("mobile", "operative"),
    "rn-module-add":                ("mobile", "operative"),
    "rn-eas-deploy":                ("mobile", "operative"),
    "rn-upgrade":                   ("mobile", "operative"),
    # --- monorepo (3): turborepo + shared packages --------------------------
    "monorepo-bootstrap":           ("monorepo", "operative"),
    "monorepo-add-shared-package":  ("monorepo", "operative"),
    "monorepo-sync-types":          ("monorepo", "operative"),
    # --- refactor (2): stack-agnostic composition ---------------------------
    "promote-component":            ("refactor", "operative"),
    "composition-patterns-guide":   ("refactor", "knowledge"),
}

FAMILY_ORDER = ["core", "web", "agent", "mobile", "monorepo", "refactor"]


def classify(name: str) -> tuple[str, str]:
    """Return (family, role). Unknown skill => hard failure, never a default."""
    try:
        return TAXONOMY[name]
    except KeyError:
        raise SystemExit(
            f"ERROR: skill '{name}' is not in the TAXONOMY in {__file__}.\n"
            f"       Every skill must be classified explicitly — add a row for it\n"
            f"       (family: {'|'.join(FAMILY_ORDER)}) and keep README.md +\n"
            f"       install.sh counts in sync."
        )


def family_of(name: str) -> str:
    return classify(name)[0]


def role_of(name: str) -> str:
    return classify(name)[1]


def truncate(text: str, n: int = 300) -> str:
    return text if len(text) <= n else text[:n] + "..."


def main() -> int:
    root = Path(".")
    skill_md_files = sorted(root.glob("*/SKILL.md"))
    skills = []

    for skill_md in skill_md_files:
        name = skill_md.parent.name
        if name.startswith(".") or name in {"docs", "dist", "evals", "contract-package", "scripts"}:
            continue
        try:
            text = skill_md.read_text()
        except Exception as e:
            sys.stderr.write(f"WARN: cannot read {skill_md}: {e}\n")
            continue

        parts = text.split("---", 2)
        if len(parts) < 3:
            sys.stderr.write(f"WARN: {skill_md} has no frontmatter, skipping\n")
            continue

        try:
            fm = yaml.safe_load(parts[1]) or {}
        except yaml.YAMLError as e:
            sys.stderr.write(f"WARN: {skill_md} has invalid YAML frontmatter: {e}\n")
            continue

        refs_dir = skill_md.parent / "references"
        refs = sorted(p.name for p in refs_dir.glob("*.md")) if refs_dir.exists() else []

        scripts_dir = skill_md.parent / "scripts"
        scripts = []
        if scripts_dir.exists():
            scripts = sorted(
                p.name for p in scripts_dir.iterdir()
                if p.is_file() and p.name != ".gitkeep"
            )

        skills.append({
            "name": fm.get("name", name),
            "family": family_of(name),
            "role": role_of(name),
            "description": truncate(fm.get("description", "")),
            "skill_file": f"{name}/SKILL.md",
            "references": refs,
            "scripts": scripts,
            "skill_md_lines": len(text.splitlines()),
            "bundle": f"dist/{name}.skill",
        })

    registry = {
        "schema_version": "1.0",
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "generated_by": "scripts/build_skills_registry.py",
        "skill_count": len(skills),
        "families": {
            fam: sorted(s["name"] for s in skills if s["family"] == fam)
            for fam in FAMILY_ORDER
        },
        "skills": sorted(
            skills, key=lambda s: (FAMILY_ORDER.index(s["family"]), s["name"])
        ),
    }

    out = Path("skills.json")
    out.write_text(json.dumps(registry, indent=2, ensure_ascii=False) + "\n")
    print(f"✓ skills.json regenerated ({len(skills)} skills)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
