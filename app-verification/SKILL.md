---
name: app-verification
description: 'Give a project a manual for proving its features on the real app, written once and kept true: `.claude/skills/verify-<app>/` with how to launch it until it is usable, a read-only doctor check, how to drive it with the repo''s real selectors, what counts as proof and where it goes, how to stop only what the run started — plus one feature file per PRD story, seeded from the wireframe screen inventory. Two modes: create (scaffold, fill from the code, prove it live once, record `meta.json#verification`) and maintain (re-read every feature from source, drive them all live, fix the manual, report real regressions). Web, Expo and eve. Triggers: "verify the app", "prova che funziona", "verification skill", "come si avvia l''app per provarla", "maintain the verify skill", "il manuale di verifica è aggiornato?". Not for: writing tests (write-tests), UI audits (shadscan), security (app-security), deploying (vercel-deploy).'
---

# app-verification — a manual to prove features on the real app

Every time an agent has to show that something works on the running app, it starts from nothing: how to start it,
when it is really ready, which user to sign in as, where to look, how to stop without killing the user's own dev
server. What it learns is gone at the end of the session, and the next agent guesses — and a guess is how a page that
merely rendered becomes "verified".

This skill writes that knowledge down **once, inside the project**, as a skill Claude Code finds by itself:
`.claude/skills/verify-<app>/`. The manual is for the next agent, read cold mid-task by someone who has never seen
the app, not for a person.

## The manual

```
.claude/skills/verify-<app>/
├── SKILL.md                 # Launch · Doctor · Drive · Evidence · Cleanup · Isolation
├── features/README.md       # baseline preconditions, driving conventions, proof rules, index
├── features/US-N-<slug>.md  # one per PRD story: Sub-features · How to get to it · Driving it with · Gotchas
└── scripts/                 # only if needed: executable, and named in SKILL.md
```

What each part holds, with filled examples: `references/manual.md`. How to drive each stack (web, Expo, eve,
monorepo): `references/stack-recipes.md`.

## create

1. **Interview the repo, not the user.** What a user touches, how it starts (the repo's own scripts first), how it can
   be driven (an existing Playwright or Maestro setup before a generic recipe), what can be observed, whether two
   instances can run side by side. Ask the user only what the code cannot tell you.
2. **If the app does not start as it is, say so precisely** — the missing env var, the database it cannot reach —
   before writing a line. A manual written over a broken base teaches wrong steps.
3. **Scaffold.**

   ```bash
   python3 <skills>/app-verification/scripts/verify_map.py scaffold <project-root> [--app web|mobile|agent]
   ```

   One feature file per `- **US-N.** …` story in `.workflow/PRD.md`. With `docs/wireframes/screen-inventory.md` the
   files arrive with their screens, routes, roles and states (loading, empty, error, success); without it the index
   lists the app's routes and says so. Everything that needs the code is a `<fill: …>`. Re-running never overwrites:
   a filled file is kept, a new story gets its file.
4. **Fill** the six sections, the index's baseline, and the first 3–5 features — US-1 first — from the code: the real
   command, the real accessible names, the real end state. Add the launch command to the project's `.claude/launch.json` under the
   name the Launch section gives, so Claude Code's preview tools and the manual start the app the same way. ⚠ The
   preview tools read the launch.json of the **session's root**: a session opened in another directory (a skills
   repo, a parent folder) needs the same entry there, with a `cd` into the project — found on fit-coach. Add
   `.verification/` to the project's `.gitignore`.
5. **Prove it.** Follow the manual as written: launch, doctor, drive **one** feature end to end, save the evidence,
   clean up — then check the evidence is still there. Fix what failed, and run the cleanup after every failed
   attempt too, so a broken try does not strand a process or a port. **A manual that was never run is a draft.** If
   you proved it on a stand-in (a local database instead of the real one), list what the stand-in did that the real
   target will not: those steps are unverified.
6. **Check.**

   ```bash
   python3 <skills>/app-verification/scripts/verify_map.py check <project-root> [--app …]
   ```

   It refuses a `<fill: …>` left anywhere, a missing section, a story without a file, a feature file out of shape or
   missing from the index, a script that is not executable or that SKILL.md never names, an evidence directory git
   does not ignore. Unfilled features beyond the first few stay as they are and fail the check: say how many remain.
7. **Record** the `verification` block by editing `.workflow/meta.json` directly, then append the run:
   `python3 dev-flow/scripts/update_meta.py <root> append-history --skill app-verification`.

   ```json
   "verification": { "skill": ".claude/skills/verify-web", "features": 12, "source": "routes",
                     "proven_at": "<ISO-8601 UTC>", "proven_feature": "US-1",
                     "evidence": ".verification/evidence/<timestamp>/", "maintained_at": null, "maintain_outcome": null }
   ```

## maintain

The app changes; the manual rots. Proposed at `feature_complete` and after material changes. One pass: index
hygiene, one read-only source reader per feature in parallel, one live session that drives every feature, triage,
and an outcome — `clean`, `changed` or `blocked`. It edits only the manual: a behaviour the manual describes that the
app no longer has is either drift (fix the manual) or a **regression** (report it to the user, never paper over it).
The full pass, with its three invariants: `references/maintain.md`.

## Rules

- **Never drive or stop an instance you did not start.** Record the PID and the port at launch; stop those. Never by
  process name. If the user's dev server is already on the port, launch on another one or ask.
- **Never weaken a journey to make it pass.** A missing precondition is a failure, and its reason goes in the
  feature's Gotchas.
- **Never commit in the project.** Create and maintain leave their files in the working tree; the user sees them in
  the diff and decides.
- **Credentials never in chat or in the manual.** Test accounts come from the project's seed or example files, and the
  manual names the file, not the password.
- **Not a gate.** It never bumps `phase` and never blocks a deploy.

## Relationship to other skills

- **`write-tests`** — a proven journey, with its recipe, is the best starting point for a Playwright or e2e test that
  repeats it in CI. Propose it.
- **`wireframe-canvas`** — its screen inventory is what seeds the feature map; a project with one gets a map that
  already knows its screens and states.
- **`superpowers:verification-before-completion`** — asks for proof before "done"; this manual is how that proof is
  obtained on this app.
- **`spec-review`** — when it finds behaviour nobody proved, the manual is where the proof comes from.

## Sources

The method is adapted from pstack's `create-verification-skill` and `maintain-verification-skill` by Lauren Tan
(MIT, `cursor/plugins/pstack`, read 2026-10-18), rewritten for dev-flow: the feature map comes from the wireframe
inventory and the PRD stories instead of being reconstructed, the manual lives in `.claude/skills/`, and nothing is
committed in the user's project.

## Reference files

- `references/manual.md` — the six sections and the feature-file shape, each with a filled example.
- `references/stack-recipes.md` — driving and proving on web, Expo, eve and in a monorepo.
- `references/maintain.md` — the maintain pass.
- `references/contracts.md` — the `.workflow/` dev-flow contract (vendored).
