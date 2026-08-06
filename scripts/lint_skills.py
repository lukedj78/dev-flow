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
  8. Capabilities named in body headings / `shadcn add` commands are also named
     in the description — skills are selected on the description, so a capability
     it never mentions is unreachable.
  9. Bare-backtick skill names at a routing marker ("invoke", "route to",
     "hands off to", "that's") point at a skill that exists - check 6 only
     catches the <name>/SKILL.md form, so a dangling name in prose used to
     survive.

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


# --- check 8: capabilities must be reachable from the description ---------
#
# Skills are selected on the frontmatter `description:`, never on the body. A
# capability documented in a section whose name never appears in the description
# is unreachable — the skill will not load for the request that needs it, and we
# will hand-roll the thing the section exists to prevent. (This is not
# hypothetical: `<Questionnaire />` shipped that way.)
#
# Signal: an artifact NAMED IN A HEADING, or installed by an explicit `add`
# command, is the author declaring "this skill delivers this thing" — so a user
# will one day ask for it by that name.
#
# Distinguishing a user-invocable capability from an internal artifact is not
# mechanically decidable, so internals are listed explicitly below rather than
# guessed at — same principle as TAXONOMY in build_skills_registry.py.
INTERNAL_ARTIFACTS: dict[str, set[str]] = {
    # <skill>: {tokens that are implementation details, not things a user asks for}
    "forms": {"formactions"},  # internal toolkit component, never requested by name
}

HEADING_RE = re.compile(r"^#{2,3}\s+(.+)$", re.M)
BACKTICKED_RE = re.compile(r"`([^`]+)`")
ADD_CMD_RE = re.compile(r"shadcn(?:@latest)?\s+add\s+([@\w/-]+)")
JSX_RE = re.compile(r"^<\s*(\w+)\s*/?>$")
IDENT_RE = re.compile(r"^[A-Za-z][\w-]{2,}$")


def _capability_tokens(text: str) -> set[str]:
    """Artifacts this skill declares it delivers, as lowercase tokens."""
    tokens: set[str] = set()
    for heading in HEADING_RE.findall(text):
        for raw in BACKTICKED_RE.findall(heading):
            raw = raw.strip()
            jsx = JSX_RE.match(raw)
            if jsx:
                tokens.add(jsx.group(1).lower())
            elif IDENT_RE.match(raw) and "." not in raw:
                tokens.add(raw.lower())
    for item in ADD_CMD_RE.findall(text):
        if item.startswith("-"):  # a flag, not an item
            continue
        # `@ns/item` is reachable if the description names either half
        tokens.add(item.lstrip("@").replace("/", " ").strip().lower())
    return tokens


def check_capability_reachable(skill_md: Path) -> None:
    name = skill_md.parent.name
    text = skill_md.read_text()
    parts = text.split("---", 2)
    if len(parts) < 3:
        return  # frontmatter check already reported it
    try:
        fm = yaml.safe_load(parts[1])
    except yaml.YAMLError:
        return
    if not isinstance(fm, dict) or not fm.get("description"):
        return
    desc = fm["description"].lower()
    allowed = INTERNAL_ARTIFACTS.get(name, set())

    for token in sorted(_capability_tokens(text)):
        if token in allowed:
            continue
        # a multi-word token (from `@ns/item`) is reachable if any part is named
        if any(part in desc for part in token.split()):
            continue
        warn(
            f"{skill_md}: body documents `{token}` but the description never names it — "
            f"the skill will not load for a request that asks for it by name "
            f"(add the trigger word, or list it in INTERNAL_ARTIFACTS)"
        )


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


# Routing markers: prose that hands work to another skill. A kebab-case token
# in backticks right after one of these is a sibling skill, not a package —
# which is how `setup-deploy` stayed routed-to for months without existing
# (check_skill_references only sees `<name>/SKILL.md` paths).
#
# Deliberately narrow. A bare "→ `x`" is NOT a marker: this repo uses arrows
# for token → Tailwind-class mappings ("accent → `bg-accent`"), and a bare
# "use `x`" is almost always an npm package. Both produced only false
# positives. Verbs that name a hand-off do not.
ROUTING_REF_RE = re.compile(
    r"(?:invoke|invokes|invoked|"
    r"route to|routes to|routed to|routing to|"
    r"hand(?:s|ed)? off to|delegate to|delegates to|defer to|defers to|"
    r"that's|that is)\s+`([a-z][a-z0-9]*(?:-[a-z0-9]+)+)`",
    re.IGNORECASE,
)

# Kebab-case names that appear at a routing marker but are NOT our skills —
# external CLIs or packages. Add a line here when a legitimate external name
# trips the check.
ROUTING_REF_ALLOWLIST: frozenset[str] = frozenset({
    "vercel-doctor",   # a skill AND the upstream CLI it wraps; cited both ways
})


def check_routing_references(path: Path, all_skills: set[str]) -> None:
    """Check #9 — bare-backtick skill names at a routing marker must exist."""
    text = path.read_text(errors="ignore")
    for m in ROUTING_REF_RE.finditer(text):
        name = m.group(1)
        if name in all_skills or name in ROUTING_REF_ALLOWLIST:
            continue
        err(
            f"{path}: routes to `{name}` but no such skill exists "
            f"(add it to ROUTING_REF_ALLOWLIST in lint_skills.py if it is an "
            f"external package or CLI)"
        )


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
        check_capability_reachable(skill_md)
        check_routing_references(skill_md, all_skills)

        refs_dir = root / skill / "references"
        if refs_dir.exists():
            for ref in refs_dir.glob("*.md"):
                check_no_absolute_paths(ref)
                check_phase_normalization(ref)
                check_skill_references(ref, all_skills)
                check_routing_references(ref, all_skills)

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
