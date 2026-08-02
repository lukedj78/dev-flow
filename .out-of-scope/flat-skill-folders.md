# Nesting the skill folders under `skills/<family>/`

**Decision**: keeping the 41 skill folders flat at the repo root
**Date**: 2026-08-02

## What it is
Moving `forms/`, `dev-flow/`, `rn-bootstrap/` … into `skills/web/forms/`, `skills/core/dev-flow/`, `skills/mobile/rn-bootstrap/`. This is how [mattpocock/skills](https://github.com/mattpocock/skills) is organised, and the root would read far better at a glance.

## Why it was tempting
41 sibling folders is a wall of names. Nesting would make the six families visible in the tree, and would let lifecycle folders (`deprecated/`, `in-progress/`) express staging the way Matt's repo does.

## Why not
1. **~385 cross-skill reference paths** are flat (`rn-styling/references/nativewind-setup.md`) and are validated by `scripts/lint_skills.py`. Every one would have to change, and stay correct forever after.
2. **The root mirrors the install target 1:1** — `~/.claude/skills/<name>/`. Flat here means what you read is what gets installed.
3. **The benefit is available without the cost.** The families are already published in `skills.json`, generated from a taxonomy that now *fails the build* on an unclassified skill. And `.claude-plugin/plugin.json` lists skill paths explicitly, so plugin distribution never required nesting in the first place.

Matt's skills are small and self-contained (a `SKILL.md`, sometimes one adapter file); ours carry `references/` and `scripts/` with hundreds of interlinks. The structures aren't comparable just because both are "skills".

## What would change our mind
- Cross-skill references becoming symbolic (a resolver / manifest lookup) instead of raw relative paths — that removes reason 1.
- Growing past ~80 skills, where the flat list stops being scannable even with tooling.
- Needing several **lifecycle** states at once (deprecated + in-progress + private); if the `EXCLUDED` set in `build_plugin_manifest.py` plus a `status` field stops being expressive enough, folders become the honest representation.
