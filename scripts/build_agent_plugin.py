#!/usr/bin/env python3
"""Build dist/agent-plugin/ — the suite as an Agent Plugins v1.0.0 package.

A third distribution format alongside .claude-plugin/plugin.json (Claude Code)
and dist/*.skill (single-skill bundles). Same 43 skills, same TAXONOMY, packaged
the way the vendor-neutral standard wants them:

    dist/agent-plugin/
    ├── plugin.json          # $schema + name + metadata, closed field set
    └── skills/
        ├── forms/SKILL.md
        └── …

The repo root stays FLAT — see .out-of-scope/flat-skill-folders.md. That decision
predates Agent Plugins and its third reason ("plugin.json lists skill paths
explicitly, so distribution never required nesting") no longer holds: the spec
fixes the locations and reads no path list. Building the nested layout instead of
adopting it keeps both true.

Spec: https://agent-plugins.org/ — https://github.com/agentplugins/agent-plugins-spec
Requirements enforced here, with the section that demands them:

  §6.1  the manifest is `plugin.json` at the plugin ROOT (not .claude-plugin/)
  §6.2  the field set is CLOSED — an unknown top-level field is reported and
        ignored by clients, so `displayName` and `skills` are dropped rather
        than carried over from the Claude Code manifest
  §6.3  `$schema` is REQUIRED and must be the canonical 1.0.0 identifier;
        missing it, a client rejects the whole plugin
  §7.1  skills are discovered ONLY as immediate children of `skills/`, each
        conforming to the Agent Skills spec — a non-conforming skill is skipped
        by the client, silently, so this script fails the build instead
  §5.2  every packaged path must resolve INSIDE the plugin root: symlinks are
        materialised, and anything pointing outside is a hard error

No mcp.json: the suite ships no MCP servers. §6.2 says an absent component
location is not an error.

Usage:  python3 scripts/build_agent_plugin.py [--check]
        --check  build to a temp dir and verify the tracked plugin.json matches
                 (CI / pre-commit), exit 1 if not
"""
from __future__ import annotations

import json
import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_plugin_manifest import EXCLUDED, MANIFEST_META  # noqa: E402
from build_skills_registry import FAMILY_ORDER, TAXONOMY  # noqa: E402
from lint_skills import DESC_MAX  # noqa: E402

SCHEMA = "https://agent-plugins.org/schemas/1.0.0/plugin.schema.json"

# §6.2 — the only permitted top-level fields. `extensions` is deliberately not
# emitted: client-specific data belongs under a reverse-domain namespace, and we
# have no documented namespace to claim for Claude Code.
ALLOWED_FIELDS = (
    "$schema", "name", "version", "description", "author",
    "homepage", "repository", "license", "keywords", "extensions",
)
ALLOWED_AUTHOR_FIELDS = ("name", "email", "url")

# Never packaged — mirrors build_skill_bundles.py.
EXCLUDE_DIRS = {"evals", "__pycache__", ".pytest_cache", "node_modules"}
EXCLUDE_NAMES = {".DS_Store"}
EXCLUDE_SUFFIXES = {".pyc"}


def manifest() -> dict:
    """MANIFEST_META filtered to the closed field set, with $schema first."""
    out = {"$schema": SCHEMA}
    for field in ALLOWED_FIELDS:
        if field == "$schema" or field not in MANIFEST_META:
            continue
        value = MANIFEST_META[field]
        if field == "author":
            value = {k: v for k, v in value.items() if k in ALLOWED_AUTHOR_FIELDS}
        out[field] = value
    return out


def skill_names() -> list[str]:
    """Ship order mirrors skills.json: by family, then alphabetically."""
    names = [n for n in TAXONOMY if n not in EXCLUDED]
    names.sort(key=lambda n: (FAMILY_ORDER.index(TAXONOMY[n][0]), n))
    return names


def packaged_files(skill_dir: Path, errors: list[str]) -> list[tuple[Path, Path]]:
    """(source, path relative to the skill dir) for everything that ships.

    A dangling symlink is reported rather than skipped: `is_file()` is False for
    one, so it would otherwise vanish from the package without a word.
    """
    out = []
    for path in sorted(skill_dir.rglob("*")):
        rel = path.relative_to(skill_dir)
        if any(part in EXCLUDE_DIRS for part in rel.parts):
            continue
        if rel.name in EXCLUDE_NAMES or any(rel.name.endswith(s) for s in EXCLUDE_SUFFIXES):
            continue
        if path.is_symlink() and not path.exists():
            errors.append(f"{path}: dangling symlink → {path.readlink()}")
            continue
        if path.is_file():
            out.append((path, rel))
    return out


def check_containment(source: Path, skill_dir: Path, errors: list[str]) -> None:
    """§5.2 — a symlink may not carry a path out of the plugin root."""
    if source.resolve().is_relative_to(skill_dir.resolve()):
        return
    errors.append(
        f"{source}: resolves to {source.resolve()}, outside the skill directory — "
        f"§5.2 requires every packaged path to stay inside the plugin root"
    )


def check_skill(skill_dir: Path, errors: list[str]) -> None:
    """§7.1 — a skill a client would skip must fail the build here instead."""
    import yaml

    name = skill_dir.name
    skill_md = skill_dir / "SKILL.md"
    if not skill_md.is_file():
        errors.append(f"{skill_md}: missing (§7.1 discovers skills by SKILL.md)")
        return
    parts = skill_md.read_text().split("---", 2)
    if len(parts) < 3:
        errors.append(f"{skill_md}: no YAML frontmatter")
        return
    try:
        fm = yaml.safe_load(parts[1]) or {}
    except yaml.YAMLError as e:
        errors.append(f"{skill_md}: frontmatter is not valid YAML: {e}")
        return
    if fm.get("name") != name:
        errors.append(f"{skill_md}: frontmatter name={fm.get('name')!r} != directory {name!r}")
    desc = fm.get("description") or ""
    if not desc:
        errors.append(f"{skill_md}: empty description")
    elif len(desc) > DESC_MAX:
        errors.append(
            f"{skill_md}: description is {len(desc)} chars, over the {DESC_MAX} cap — "
            f"a conforming client would skip this skill (see check 3b in lint_skills.py)"
        )


def build(out_dir: Path) -> tuple[int, int]:
    root = Path(__file__).resolve().parent.parent
    errors: list[str] = []
    names = skill_names()

    if out_dir.exists():
        shutil.rmtree(out_dir)
    skills_dir = out_dir / "skills"
    skills_dir.mkdir(parents=True)

    file_count = 0
    for name in names:
        skill_dir = root / name
        if not skill_dir.is_dir():
            errors.append(f"{name}: in TAXONOMY but not on disk")
            continue
        check_skill(skill_dir, errors)
        target = skills_dir / name
        target.mkdir()
        for source, rel in packaged_files(skill_dir, errors):
            check_containment(source, skill_dir, errors)
            dest = target / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            # copy the CONTENT: a symlink must not survive into the package
            shutil.copyfile(source, dest, follow_symlinks=True)
            file_count += 1

    (out_dir / "plugin.json").write_text(json.dumps(manifest(), indent=2, ensure_ascii=False) + "\n")

    if errors:
        shutil.rmtree(out_dir)
        for e in errors:
            sys.stderr.write(f"  E {e}\n")
        sys.stderr.write(f"✗ {len(errors)} error(s) — package not written\n")
        raise SystemExit(2)

    return len(names), file_count


def main() -> int:
    root = Path(__file__).resolve().parent.parent
    tracked = root / "dist" / "agent-plugin" / "plugin.json"

    if "--check" in sys.argv:
        with tempfile.TemporaryDirectory() as tmp:
            build(Path(tmp) / "agent-plugin")
            fresh = json.dumps(manifest(), indent=2, ensure_ascii=False) + "\n"
        if not tracked.exists() or tracked.read_text() != fresh:
            sys.stderr.write(
                "::error::dist/agent-plugin/plugin.json is out of date. "
                "Run scripts/build_agent_plugin.py and commit the result.\n"
            )
            return 1
        print("✓ agent-plugin manifest is up to date, and the package builds clean.")
        return 0

    skills, files = build(root / "dist" / "agent-plugin")
    print(f"✓ dist/agent-plugin/ built — {skills} skills, {files} files, Agent Plugins 1.0.0")
    print("  plugin.json is tracked; skills/ is generated (see .gitignore)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
