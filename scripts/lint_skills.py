#!/usr/bin/env python3
"""lint_skills.py — sanity-check every skill in the repo

Checks:
  1. Every */SKILL.md has valid YAML frontmatter with `name` + `description`.
  2. The `name:` field matches the directory name.
  3. The `description:` field has both "Triggers" and "Not for:" markers (style guide).
  4. No SKILL.md or references/*.md cites the absolute path `~/my-skills/`
     (portability — skills must work from any install dir).
  5. Phase values cited in skill text use snake_case (no `module-added` etc.).
  6. All cross-references to sibling skills (`<name>/SKILL.md` style) point at
     a sibling that actually exists.
  7. Every skill listed in install.sh / uninstall.sh exists on disk.

Exit codes:
  0 = clean
  1 = warnings only
  2 = errors (broken frontmatter, missing files, etc.)

Run from the repo root.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    sys.stderr.write("PyYAML required. Install with: pip install pyyaml\n")
    sys.exit(2)


ERRORS: list[str] = []
WARNINGS: list[str] = []
SKILL_NAMES: set[str] = set()


def err(msg: str) -> None:
    ERRORS.append(msg)


def warn(msg: str) -> None:
    WARNINGS.append(msg)


def collect_skill_names(root: Path) -> set[str]:
    return {p.parent.name for p in root.glob("*/SKILL.md")}


def check_frontmatter(skill_md: Path) -> None:
    name = skill_md.parent.name
    text = skill_md.read_text()
    parts = text.split("---", 2)
    if len(parts) < 3:
        err(f"{skill_md}: no YAML frontmatter (missing --- delimiters)")
        return
    try:
        fm = yaml.safe_load(parts[1])
    except yaml.YAMLError as e:
        err(f"{skill_md}: frontmatter is not valid YAML: {e}")
        return
    if not isinstance(fm, dict):
        err(f"{skill_md}: frontmatter is not a mapping")
        return
    if "name" not in fm:
        err(f"{skill_md}: frontmatter missing required `name:` field")
    elif fm["name"] != name:
        err(f"{skill_md}: frontmatter name={fm['name']!r} != directory {name!r}")
    if "description" not in fm:
        err(f"{skill_md}: frontmatter missing required `description:` field")
        return
    desc = fm["description"]
    if not desc:
        err(f"{skill_md}: empty description")
        return
    desc_lower = desc.lower()
    has_invocation_marker = any(m in desc_lower for m in (
        "trigger", "use when", "use whenever", "use to ", "use this", "use for ",
    ))
    if not has_invocation_marker:
        warn(f"{skill_md}: description has no 'Triggers on:' / 'Use when' / 'Use to' marker (style guide)")
    if "not for" not in desc_lower:
        warn(f"{skill_md}: description has no 'Not for:' clause (style guide)")


def check_no_absolute_paths(path: Path) -> None:
    text = path.read_text(errors="ignore")
    if "~/my-skills/" in text:
        err(f"{path}: contains hardcoded `~/my-skills/` (skills must be path-portable)")


KEBAB_PHASE_RE = re.compile(r"\bmodule-added\b")


def check_phase_normalization(path: Path) -> None:
    # contracts.md (the canonical schema) and the operative SKILL.md "Updating
    # meta.json" section both intentionally cite "module-added" to document
    # it as a legacy alias accepted by update_meta.py. Skip the check there.
    if path.name == "contracts.md":
        return
    text = path.read_text(errors="ignore")
    # If the only occurrences are inside backticks of the alias normalization
    # block (which mentions both spellings together), skip — that's documentation,
    # not actual usage.
    alias_doc_re = re.compile(r"`module-added`\s*(?:→|->|to)\s*`module_added`")
    text_without_alias_doc = alias_doc_re.sub("", text)
    if KEBAB_PHASE_RE.search(text_without_alias_doc):
        warn(f"{path}: cites legacy kebab `module-added` (use `module_added`)")


SKILL_REF_RE = re.compile(r"`([a-z][a-z0-9-]+)/(SKILL\.md|references/[a-z0-9-]+\.md)`")


def check_skill_references(path: Path, all_skills: set[str]) -> None:
    text = path.read_text(errors="ignore")
    for m in SKILL_REF_RE.finditer(text):
        skill_name = m.group(1)
        if skill_name not in all_skills:
            # Not a sibling skill ref (could be a path inside the project)
            continue
        rel_path = Path(skill_name) / m.group(2)
        if not rel_path.exists():
            err(f"{path}: references {m.group(0)} but {rel_path} does not exist")


def check_installer_skills(installer_path: Path, all_skills: set[str]) -> None:
    if not installer_path.exists():
        warn(f"{installer_path}: not found (skipping installer check)")
        return
    text = installer_path.read_text()
    # Extract entries from SKILLS=(...) block, tolerating bash comments
    m = re.search(r"SKILLS=\((.*?)\n\)", text, re.DOTALL)
    if not m:
        warn(f"{installer_path}: no SKILLS=(...) block found")
        return
    block = m.group(1)
    # Strip bash comments
    block_clean = re.sub(r"#.*$", "", block, flags=re.MULTILINE)
    listed = re.findall(r"^\s*([a-z][a-z0-9-]+)\s*$", block_clean, re.MULTILINE)
    listed_set = set(listed)
    missing_on_disk = listed_set - all_skills
    missing_in_installer = all_skills - listed_set
    for s in missing_on_disk:
        err(f"{installer_path}: lists `{s}` but it does not exist on disk")
    for s in missing_in_installer:
        warn(f"{installer_path}: misses `{s}` (exists on disk but not in installer)")


def main() -> int:
    root = Path(".")
    all_skills = collect_skill_names(root)
    if not all_skills:
        sys.stderr.write("No SKILL.md found. Run from repo root.\n")
        return 2

    print(f"→ Linting {len(all_skills)} skills…")

    for skill in sorted(all_skills):
        skill_md = root / skill / "SKILL.md"
        check_frontmatter(skill_md)
        check_no_absolute_paths(skill_md)
        check_phase_normalization(skill_md)
        check_skill_references(skill_md, all_skills)

        refs_dir = root / skill / "references"
        if refs_dir.exists():
            for ref in refs_dir.glob("*.md"):
                check_no_absolute_paths(ref)
                check_phase_normalization(ref)
                check_skill_references(ref, all_skills)

    check_installer_skills(root / "install.sh", all_skills)
    check_installer_skills(root / "uninstall.sh", all_skills)

    print()
    if ERRORS:
        print(f"✗ {len(ERRORS)} error(s):")
        for e in ERRORS:
            print(f"  E {e}")
    if WARNINGS:
        print(f"⚠ {len(WARNINGS)} warning(s):")
        for w in WARNINGS:
            print(f"  W {w}")
    if not ERRORS and not WARNINGS:
        print("✓ All clean.")

    return 2 if ERRORS else (1 if WARNINGS else 0)


if __name__ == "__main__":
    sys.exit(main())
