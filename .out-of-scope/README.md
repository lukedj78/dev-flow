# Out of scope — decisions *not* to build

Deliberate "no"s. Without this folder they live only in commit messages and chat history, and get re-litigated every few months — or worse, quietly reversed by someone who never saw the reasoning.

**Write an entry when**: we evaluated something real (a library, a tool, a restructuring, a skill someone suggested) and chose not to adopt it — especially when the thing is *good* and the answer is still no.

**Format** — one file per decision:

```markdown
# <thing>

**Decision**: not adopting / deferred / adopted in a reduced form
**Date**: YYYY-MM-DD

## What it is
## Why it was tempting
## Why not
## What would change our mind
```

That last section matters most: a "no" with a stated trigger is a decision; a "no" without one is a prejudice.

## Index

| Decision | Verdict | Date |
|---|---|---|
| [turbotunnel](turbotunnel.md) | not adopting | 2026-07-31 |
| [flat-skill-folders](flat-skill-folders.md) | keeping flat — no `skills/<family>/` nesting | 2026-08-02 |
| [ai-elements](ai-elements.md) | documented as an option, not the default | 2026-08-02 |
| [react-query-on-web](react-query-on-web.md) | stays the last rung, deliberately | 2026-08-02 |
| [changesets](changesets.md) | curated CHANGELOG instead | 2026-08-02 |

Watched-but-not-applied *upstream* items live in [`docs/vercel-changelog-watch.md`](../docs/vercel-changelog-watch.md) instead — that log is per changelog entry, this folder is per decision.
