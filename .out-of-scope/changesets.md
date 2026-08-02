# Changesets for versioning

**Decision**: a hand-curated `CHANGELOG.md` instead
**Date**: 2026-08-02

## What it is
[Changesets](https://github.com/changesets/changesets) — the npm-ecosystem workflow where each PR adds a changeset file and a bot assembles the changelog and version bump. Used by `mattpocock/skills`.

## Why it was tempting
It removes the "who forgot to update the changelog" failure mode, and it's the standard for multi-package repos.

## Why not
It solves a problem we don't have. Changesets shine when **many packages version independently**; dev-flow versions as **one suite** — the 41 skills share a contract and are installed together, so there is exactly one version number, in `.claude-plugin/plugin.json`.

The cost is real: a Node toolchain (`package.json`, `node_modules`, a CI bot) in a repo whose only runtime dependency today is Python for the build scripts.

Our changelog entries are also editorial in a way generated ones aren't — the valuable lines are "this guidance was *wrong*, here's what upstream actually does", which no bot derives from a diff.

## What would change our mind
Splitting the suite into independently versioned plugins (say, `dev-flow-web` and `dev-flow-mobile` shipping on different cadences). At that point per-package versioning is the actual problem changesets solve, and we should adopt it rather than hand-maintain N changelogs.
