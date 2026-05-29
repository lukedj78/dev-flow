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


CORE = {"dev-flow", "prd-from-idea", "prd-to-tasks"}

WEB_FAMILY = {
    "figma-to-design-md", "image-to-design-md", "design-md-to-app",
    "screenshot-to-page", "module-add", "write-tests",
}

MOBILE_FAMILY = {
    "rn-fundamentals", "rn-styling", "rn-expo-router", "rn-bootstrap",
    "rn-components-apis", "rn-data-fetching", "rn-add-screen", "rn-write-tests",
    "rn-animations-gestures", "rn-push-notifications", "rn-backend",
    "rn-eas-build-submit-update", "rn-publishing-payments", "rn-module-add",
    "rn-eas-deploy",
}

KNOWLEDGE_RN = {
    "rn-fundamentals", "rn-styling", "rn-expo-router", "rn-components-apis",
    "rn-data-fetching", "rn-animations-gestures", "rn-push-notifications",
    "rn-backend", "rn-eas-build-submit-update", "rn-publishing-payments",
}

OPERATIVE_RN = {
    "rn-bootstrap", "rn-add-screen", "rn-write-tests", "rn-module-add",
    "rn-eas-deploy",
}


def family_of(name: str) -> str:
    if name in CORE:
        return "core"
    if name in MOBILE_FAMILY:
        return "mobile"
    return "web"


def role_of(name: str) -> str:
    if name == "dev-flow":
        return "orchestrator"
    if name in {"prd-from-idea", "prd-to-tasks"}:
        return "discovery"
    if name in KNOWLEDGE_RN:
        return "knowledge"
    if name in OPERATIVE_RN:
        return "operative"
    return "operative"  # web operatives default


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
            "core": sorted(s["name"] for s in skills if s["family"] == "core"),
            "web": sorted(s["name"] for s in skills if s["family"] == "web"),
            "mobile": sorted(s["name"] for s in skills if s["family"] == "mobile"),
        },
        "skills": sorted(skills, key=lambda s: (s["family"], s["name"])),
    }

    out = Path("skills.json")
    out.write_text(json.dumps(registry, indent=2, ensure_ascii=False) + "\n")
    print(f"✓ skills.json regenerated ({len(skills)} skills)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
