#!/usr/bin/env python3
r"""lint_skills.py — sanity-check every skill in the repo

Checks:
  1. Every */SKILL.md has valid YAML frontmatter with `name` + `description`.
  2. The `name:` field matches the directory name.
  3. The `description:` field has both "Triggers" and "Not for:" markers (style guide).
  3b. The `description:` fits in 1024 characters — the Agent Skills spec cap.
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
  10. Every skill in the taxonomy is mentioned in the README catalogue, in
     either form it uses (a `### \`name\`` prose section or a `| \`name\` |`
     table row). Adding a skill and forgetting the README is silent otherwise.
  11. Skill counts stated in prose (README, CONTEXT, the map, the installers)
     match reality — total and per family.

(The published site — `docs/index.html` + `docs/skills/` — is generated separately:
run `python3 scripts/build_site.py --check`.)

Exit codes:
  0 = clean (notes are informational and never change the exit code)
  1 = warnings only
  2 = errors (broken frontmatter, missing files, etc.)

Run from the repo root.
"""
from __future__ import annotations

import json
import os
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
NOTES: list[str] = []
SKILL_NAMES: set[str] = set()

# --- check 3b: description length ------------------------------------------
#
# The Agent Skills spec (https://agentskills.io/specification) caps
# `description` at 1024 characters, and Agent Plugins v1.0.0 §7.1 requires a
# client to SKIP a skill that does not conform. Over the cap, the skill is not
# "a bit long" — it silently does not exist for the agent.
#
# This collides with our own style guide, which asks every description to carry
# its triggers and a "Not for:" clause: that is what pushed 14 of the 42 over.
# All 14 have since been cut back, and not one trigger phrase was lost — the
# length was explanation duplicated from the body, not triggers. So the escape
# hatch below is EMPTY, and shortening is the only remedy.
#
# GRANDFATHERED may only SHRINK, never grow. A skill not on the list going over
# the cap is an error, and an entry that no longer needs the exemption is an
# error too — so the list cannot go stale.
DESC_MAX = 1024
DESC_WARN = 900

GRANDFATHERED_LONG_DESC: set[str] = set()


def err(msg: str) -> None:
    ERRORS.append(msg)


def warn(msg: str) -> None:
    WARNINGS.append(msg)


def note(msg: str) -> None:
    """Informational only — reported, but never changes the exit code."""
    NOTES.append(msg)


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
    desc_len = len(desc)
    if desc_len > DESC_MAX:
        if name in GRANDFATHERED_LONG_DESC:
            note(
                f"{skill_md}: description is {desc_len} chars, over the {DESC_MAX} cap "
                f"(grandfathered — a spec-conforming client skips this skill entirely)"
            )
        else:
            err(
                f"{skill_md}: description is {desc_len} chars, over the {DESC_MAX} cap of "
                f"the Agent Skills spec — a conforming client will skip this skill. Shorten it "
                f"(do not add it to GRANDFATHERED_LONG_DESC: that list only shrinks)"
            )
    elif name in GRANDFATHERED_LONG_DESC:
        err(
            f"{skill_md}: description now fits in {desc_len}/{DESC_MAX} chars — drop "
            f"'{name}' from GRANDFATHERED_LONG_DESC in scripts/lint_skills.py"
        )
    elif desc_len > DESC_WARN:
        note(
            f"{skill_md}: description is {desc_len} chars, close to the {DESC_MAX} cap "
            f"(over it, a conforming client skips the skill)"
        )
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
#
# DELIBERATELY NARROW — do not "improve" this by widening it. Both obvious
# extensions were prototyped against the corpus and measured; both are
# net-negative:
#
#   references/*.md headings  → 185 findings across 37 skills. ~150 of them are
#       one cause: `references/contracts.md` is vendored into 30 skills
#       byte-identically, and its headings (`artifacts`, `linear`/`scrum`,
#       `phase`, `stack`) document the CONTRACT SCHEMA, not capabilities. The
#       rest are structural or prose headings (`await`, `https`, `h-screen`).
#       Reference headings organise a document; SKILL.md headings declare what
#       the skill does. Only the second is a reachability signal.
#
#   npm/pnpm/yarn/bun install → 8 findings, almost all dependencies rather than
#       capabilities (`next@latest`, `typescript@`, `next-themes`) plus flags
#       leaking through the regex. `shadcn add <item>` is different in kind: its
#       argument is always a NAMED USER-FACING COMPONENT, which is exactly the
#       thing someone asks for by name.
#
# Scope is the whole value here. A check that fires 185 times is a check nobody
# reads — see the shadscan skill on advisory fatigue for the same lesson.
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


# --- check 10: the README catalogue covers every skill ----------------------
#
# The catalogue is 400+ lines of HAND-WRITTEN prose — Input / Output / how it
# works — plus compact table rows for the families where a section each would
# be 160 lines of scroll. That prose is an asset; generating it from
# skills.json would trade it for a thinner table. So this does NOT generate
# anything. It checks the one thing that silently rots: a skill gets added and
# nobody adds it to the README. (`coss-ui` had been missing for months.)
#
# Both documentation depths count. The reverse direction is deliberately NOT
# checked: those tables also list `module-add` module names (auth, db, ci, …)
# which are not skills, so "extra" rows are normal and flagging them would be
# noise.
CATALOGUE_START = "## The 44 skills, in detail"
CATALOGUE_END = "## How the skills compose"
PROSE_RE = re.compile(r"^### `([a-z][a-z0-9-]+)`", re.M)
ROW_RE = re.compile(r"^\| `([a-z][a-z0-9-]+)`", re.M)


def check_readme_catalogue(readme: Path, all_skills: set[str]) -> None:
    if not readme.exists():
        warn(f"{readme}: not found (skipping catalogue check)")
        return
    text = readme.read_text()
    # The heading carries the count, so match on the stable half.
    m = re.search(r"^## The (\d+) skills, in detail$", text, re.M)
    if not m:
        warn(f"{readme}: no '## The N skills, in detail' heading (skipping catalogue check)")
        return
    claimed = int(m.group(1))
    if claimed != len(all_skills):
        err(f"{readme}: catalogue heading says {claimed} skills, {len(all_skills)} exist on disk")
    try:
        section = text[m.start():text.index(CATALOGUE_END, m.start())]
    except ValueError:
        warn(f"{readme}: catalogue has no '{CATALOGUE_END}' terminator (skipping)")
        return
    documented = set(PROSE_RE.findall(section)) | set(ROW_RE.findall(section))
    for skill in sorted(all_skills - documented):
        err(
            f"{readme}: `{skill}` exists but the catalogue never mentions it — "
            f"add a `### `{skill}`` section or a table row to its family"
        )


# --- check 11: stated counts must match reality ----------------------------
#
# The count is written out in ~20 places across five files, and it went stale
# three times in one week — each time only partly, because a grep for "43
# skills" misses "There are 43.", "packaging of all 43" and "Install all 43
# dev-flow skills (5 core + ...)". The family breakdown rots on its own too:
# adding `spec-review` moved the total to 44 everywhere and left "5 core" in
# both installers.
#
# Totals are matched by an EXPLICIT list of phrasings rather than a generic
# `(\d+) skills` regex. That regex was tried and is unusable: family counts use
# the same wording ("the 15 web-stack skills"), and CONTEXT.md's "33 skills"
# is the vendored-contract copy count, not a skill count. Adding a new phrasing
# here is a one-line change; drowning the check in false positives is not
# recoverable.
#
# One quirk to know when writing ABOUT this check: it scans prose, so prose
# that quotes a stale count as an example trips it — the README described
# check 11 by reproducing two of the phrasings it had caught, and the check
# dutifully flagged them. Describe such examples rather than reproducing them
# verbatim. The alternative (teaching the check to recognise an example) makes
# it cleverer and less trustworthy, which is the wrong trade for a guard.
FAMILIES = "core|web|agent|mobile|monorepo|refactor"
COUNT_FILES = ["README.md", "CONTEXT.md", "docs/dev-flow-skill-map.html",
               "install.sh", "uninstall.sh"]
TOTAL_PATTERNS = [
    r"\b(\d+) skills \(", r"containing (\d+) skills", r"[Ss]hould print (\d+)",
    r"all (\d+) skills", r"map of the (\d+) skills", r"my-skills — (\d+) skills",
    r'class="g">(\d+) skills', r"The (\d+) skills, in detail", r"All (\d+), by function",
    r"registry of all (\d+) skills", r"across all (\d+) skills", r"There are (\d+)\.",
    r"(\d+) skill folders", r"Install all (\d+) dev-flow skills",
    r"Remove all (\d+) dev-flow skills", r"suite is (\d+) skills",
    r"packaging of all (\d+)", r"one of our (\d+) skills", r"exercising all (\d+) skills",
    # The skill-map's metric card is a bare number with no adjacent word, so no
    # prose pattern above could ever match it. It sat at 44 for a full release.
    r'>skills</div><div class="v"[^>]*>(\d+)<',
]
# A family name followed by a dash introduces a list, not a count ("2 agent — eve").
FAMILY_COUNT_RE = re.compile(rf"\b(\d+)\s+({FAMILIES})\b(?!\s*[-–—]\s*)", re.I)


def check_stated_counts(root: Path, all_skills: set[str]) -> None:
    try:
        registry = json.loads((root / "skills.json").read_text())
    except Exception:
        warn("skills.json unreadable — skipping the stated-count check")
        return
    total = len(all_skills)
    per_family: dict[str, int] = {}
    for entry in registry.get("skills", []):
        per_family[entry["family"]] = per_family.get(entry["family"], 0) + 1

    for rel in COUNT_FILES:
        path = root / rel
        if not path.exists():
            continue
        text = path.read_text(errors="ignore")
        for pattern in TOTAL_PATTERNS:
            for m in re.finditer(pattern, text):
                if int(m.group(1)) != total:
                    err(f"{path}: \"{m.group(0).strip()}\" — there are {total} skills")
        for m in FAMILY_COUNT_RE.finditer(text):
            fam = m.group(2).lower()
            if fam in per_family and int(m.group(1)) != per_family[fam]:
                err(f"{path}: \"{m.group(0)}\" — there are {per_family[fam]} {fam} skills")


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


# ---------------------------------------------------------------------------
# Check 12 — installed vs repo.
#
# The repo is the source of truth, but the agent loads ~/.claude/skills. Those
# two drift the moment you edit here and forget `./install.sh`, and nothing
# else notices: the linter passes (the repo is fine), the skill fires (a copy
# exists), and it is simply the wrong text. One real run found 25 of 43
# installed skills stale — every one of them corrected earlier that same day.
#
# NOTES, never errors: a CI runner has no skills directory, and a divergence
# is a fact about this machine, not a defect in the commit. Warnings would
# fail the build (main() exits 1 on any), which is why this is not one.
# ---------------------------------------------------------------------------
def check_installed_in_sync(root: Path, all_skills: set[str]) -> None:
    skills_dir = Path(
        os.environ.get("CLAUDE_SKILLS_DIR", Path.home() / ".claude" / "skills")
    ).expanduser()
    if not skills_dir.is_dir():
        return  # not installed here (CI, or another platform) — nothing to compare

    def files_of(base: Path) -> dict[str, bytes]:
        out: dict[str, bytes] = {}
        for f in list(base.glob("SKILL.md")) + sorted(base.glob("references/**/*.md")):
            try:
                out[str(f.relative_to(base))] = f.read_bytes()
            except OSError:
                pass
        return out

    stale, missing = [], []
    for name in sorted(all_skills):
        src, dest = root / name, skills_dir / name
        if not (dest / "SKILL.md").exists():
            missing.append(name)
            continue
        if files_of(src) != files_of(dest):
            stale.append(name)

    # A `<name>.bak` left inside the skills dir still carries a SKILL.md that
    # declares the SAME `name:`, so the harness registers both and the stale
    # copy competes for triggering. install.sh stopped creating these on
    # 2026-08-28; older ones linger until removed.
    shadows = sorted(
        d.name for d in skills_dir.glob("*.bak")
        if d.is_dir() and (d / "SKILL.md").exists()
    )

    if stale:
        shown = ", ".join(stale[:8]) + (f" … +{len(stale) - 8}" if len(stale) > 8 else "")
        note(
            f"{len(stale)} installed skill(s) differ from this repo — the agent is loading "
            f"the older text: {shown}. Run ./install.sh"
        )
    if missing:
        shown = ", ".join(missing[:8]) + (f" … +{len(missing) - 8}" if len(missing) > 8 else "")
        note(f"{len(missing)} skill(s) exist here but are not installed: {shown}. Run ./install.sh")
    if shadows:
        shown = ", ".join(shadows[:8]) + (f" … +{len(shadows) - 8}" if len(shadows) > 8 else "")
        note(
            f"{len(shadows)} stale `.bak` folder(s) in {skills_dir} still declare a live "
            f"skill name and will be registered alongside it: {shown}. Remove them"
        )


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

    check_readme_catalogue(root / "README.md", all_skills)
    check_stated_counts(root, all_skills)
    check_installer_skills(root / "install.sh", all_skills)
    check_installer_skills(root / "uninstall.sh", all_skills)
    check_installed_in_sync(root, all_skills)

    print()
    if ERRORS:
        print(f"✗ {len(ERRORS)} error(s):")
        for e in ERRORS:
            print(f"  E {e}")
    if WARNINGS:
        print(f"⚠ {len(WARNINGS)} warning(s):")
        for w in WARNINGS:
            print(f"  W {w}")
    if NOTES:
        print(f"· {len(NOTES)} note(s) — informational, do not fail the build:")
        for n in NOTES:
            print(f"  N {n}")
    if not ERRORS and not WARNINGS:
        print("✓ All clean." if not NOTES else "✓ Clean (notes above).")

    return 2 if ERRORS else (1 if WARNINGS else 0)


if __name__ == "__main__":
    sys.exit(main())
