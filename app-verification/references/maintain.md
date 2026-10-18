# maintain — keeping the manual true

A manual rots the moment the app changes. The unit of rigour is the feature, not every sentence: every feature
file is read against the source, and every feature is driven live at least once.

## Outcomes

Pick one and say which:

- **clean** — every feature had source and live coverage; nothing to change.
- **changed** — corrections to the manual, proven, left in the working tree (never committed in the user's project).
- **blocked** — coverage could not finish, or a proven correction could not be made safely. Say exactly what blocked
  it.

## Edit scope

Only the manual's own directory: its SKILL.md, `features/`, its scripts. Never product code. A behaviour the manual
describes that the app no longer has is one of two things:

| What it is | What you do |
|---|---|
| the manual is wrong about how the feature works today | fix the manual |
| the feature works, but the manual cannot drive it | fix the manual's harness (a script stays executable and named in SKILL.md) |
| the feature is broken | **a product regression**: report it to the user; it never goes into the manual as the new truth |

## The pass

1. **Index hygiene.** Read `features/README.md`, glob its siblings, fix missing, extra, duplicate or dead entries.
   Run `verify_map.py scaffold` to add the file of any story added to the PRD since the last run.
2. **Source wave.** One read-only subagent per feature file, in parallel. Each explains how the feature works from
   source, flags where the manual drifted (with file:line), and returns one live recipe. They never drive the app and
   never edit files.
3. **Reconcile.** Every feature has a summary. Merge the recipes into as few app states as practical. Spot-check the
   drift they cite. Sweep recent changes for user-facing surfaces missing from the map — a concrete source path, or
   it is not missing.
4. **Live pass**, required even when the source looks clean. You alone drive, following the manual's own Launch
   (one long-lived instance for a server or UI; a fresh session per drive for a short CLI). Every feature at least
   once. Three invariants, whatever fails:
   1. never drive an instance you have not health-checked since it last surprised you — doctor before the first
      drive, after every failed drive, and where doctor cannot see the failure (a wedged UI on a healthy process),
      reset or relaunch;
   2. the evidence captured so far survives every cleanup, checked where it is supposed to be;
   3. nothing a drive started outlives its usefulness — clean the residue of a failed attempt, never the user's
      instance.

   A feature you cannot reach is `verified-unreachable` only with the concrete prerequisite (an entitlement, an
   external account, an OS) and the route you tried; if the manual omits that prerequisite, that is drift. A doctor
   failure caused by the manual being wrong is drift: fix it and retry once before calling the pass `blocked`.
5. **Triage**, as the table above.
6. **Report**: the outcome, the features covered, the unreachable ones with their prerequisites, the drift fixed, the
   regressions found. Update `meta.json#verification.maintained_at` and `maintain_outcome`, and append history. Run
   `verify_map.py check` before saying `changed`.
