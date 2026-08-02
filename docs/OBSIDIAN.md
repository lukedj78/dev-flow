# Using this repo as an Obsidian vault

The skills are a **second brain** (contract §Knowledge principle). This repo is ~260 interlinked markdown files, so it works as an [Obsidian](https://obsidian.md) vault directly — no export, no duplication. The files stay plain markdown that renders on GitHub; Obsidian is just a better lens on them.

## Open it

**Obsidian → Open folder as vault → select this repo's root.** That's it — `.obsidian/` is committed, so the ignore filters and graph colors come with it.

Obsidian rewrites the files in `.obsidian/` as you change settings. Commit those changes only when they're an improvement for everyone; otherwise `git checkout .obsidian/` to reset. Your workspace layout (`workspace.json`) is personal and stays untracked.

## Start here

| Note | What it is |
|---|---|
| **[knowledge-index](knowledge-index.md)** | the **MOC** — every domain we're expert in → its doc-grounded how-to → the upstream to re-verify |
| [../README](../README.md) | the product view: what the 41 skills are and how to install them |
| [../dev-flow/references/contracts.md](../dev-flow/references/contracts.md) | rule zero, the golden rules, the `meta.json` schema — the load-bearing document |
| [vercel-changelog-watch](vercel-changelog-watch.md) | the dated log of ecosystem watch passes |

Pin `knowledge-index.md` as your home note (right-click the tab → Pin).

## How the vault is laid out

```
<skill-name>/SKILL.md          41 of these — the skill itself (frontmatter = name + description)
<skill-name>/references/*.md   the doc-grounded how-tos and recipes it reads
docs/                          cross-cutting docs, this file, the knowledge index, assets
scripts/ bootstrap/ evals/     tooling, templates, eval fixtures
dist/                          generated .skill bundles — EXCLUDED from the vault
```

The 41 skill folders are deliberately **flat** at the root: that mirrors the install target (`~/.claude/skills/<name>/`) and keeps ~385 cross-skill links working. The logical grouping into six families lives in `skills.json` (generated from the taxonomy in `scripts/build_skills_registry.py`), not in the folder tree.

## What's configured

- **Markdown links, not wikilinks.** `useMarkdownLinks: true` + `newLinkFormat: relative` — so anything Obsidian creates still renders correctly on GitHub. Please keep it that way: `[[wikilinks]]` would break the GitHub view.
- **Ignore filters**: `dist/`, `.git/`, `node_modules/`, `.claude/`, and the Python source under `contract-package/` — they'd only add noise to search and the graph.
- **Graph colors**: docs grey · core amber · mobile+monorepo green · eve purple · every `SKILL.md` blue. The graph then reads as "skills and the knowledge they pull in".

## What it's good for

- **Graph view** — see which references a skill actually pulls in, and spot orphans (a reference nothing links to is usually a reference nobody reads).
- **Backlinks** — open `dev-flow/references/contracts.md` and see all 41 skills that vendor it; open a how-to and see which skills depend on it.
- **Search** — full-text across every skill at once, which is how you check "do we already document X?" before writing it (rule zero: don't invent what we already know).
- **Periodic refresh** — walk `knowledge-index.md`, open each how-to, re-verify its upstream, note the pass.

## Caveats

- **Don't let Obsidian move files.** Renaming a note updates links inside the vault, but `install.sh`, `skills.json`, the build scripts and the linter all key off folder names. Rename a skill only through the normal repo workflow (and re-run the build + lint).
- **`dist/*.skill` are archives**, not notes — they're excluded on purpose; regenerate them with `python3 scripts/build_skill_bundles.py`.
- **The linter is still the source of truth** for cross-reference validity: `python3 scripts/lint_skills.py`. Obsidian's "unresolved links" is a hint, not the gate.
