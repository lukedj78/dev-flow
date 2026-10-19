---
name: app-verification
description: 'Give a project a manual for proving its features on the real app, written once and kept true: `.claude/skills/verify-<app>/` with how to launch it until it is usable, a read-only doctor check, how to drive it with the repo''s real selectors, what counts as proof and where it goes, how to stop only what it started — plus one feature file per PRD story, seeded from the wireframe screen inventory, and a headless-Chrome render probe (overflow, wrapped headings, text hidden under reduced motion). Two modes: create (scaffold, fill from the code, prove it live once, record `meta.json#verification`) and maintain (re-read every feature from source, drive them all live, fix the manual, report real regressions). Web, Expo and eve. Triggers: "verify the app", "prova che funziona", "verification skill", "come si avvia l''app per provarla", "maintain the verify skill", "il manuale di verifica è aggiornato?". Not for: writing tests (write-tests), UI audits (shadscan), security (app-security), deploying (vercel-deploy).'
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
   python3 <skills>/app-verification/scripts/verify_map.py scaffold <project-root>
   ```

   **One manual per surface the project has**, found by `surfaces.py`, the one module that decides what a project
   is made of (canonical in `dev-flow/scripts/`, vendored here). It walks the root, the declared workspaces
   (`pnpm-workspace.yaml`, `package.json#workspaces`) and `apps/*` / `packages/*`:

   | Kind | What counts |
   |---|---|
   | `web` | a route directory (`app/`, `src/app/`, `pages/`) with `next` |
   | `mobile` | Expo |
   | `agent` | eve |
   | `api` | a non-JS service listed in `stack.monorepo.services` (the meta.json list `monorepo-add-python-service` writes) |
   | `cli` | a `bin`, in an app or at the root |
   | `other` | an app with a `start` or `dev` script |

   A shared package in `packages/*` (a component library, a db package with a migration `bin`, anything whose `dev`
   is `tsc -w`) is not a surface unless `stack_config.verification_surfaces` lists its path. A single app is named
   after its kind (`verify-web`); an app in a workspace is named after its directory (`verify-admin`), and the agent
   it serves becomes `verify-admin-agent`. Two surfaces never share a name. An agent mounted in the web app
   (`withEve()`) gets a manual whose Launch points to the web's: it never starts on its own.

   `--app <name>` forces one surface, and a name the project does not have is refused with the list of the ones it
   has. For a UI surface, scaffold writes one feature file per story in `.workflow/PRD.md` (`- **US-N.** …`, `*`
   bullets and sub-numbers like `US-3.1` too). A story that does not apply to this surface, such as a web-only story
   in `verify-mobile`, keeps a one-line file saying so. For an agent it writes one file per tool; for an api, cli or
   other surface, one journey file to fill.

   With `docs/wireframes/screen-inventory.md` the files arrive with their screens, routes, roles and states
   (loading, empty, error, success). Without it, the index lists the surface's own routes and says so. Everything
   that needs the code is a `<fill: …>`. Re-running never overwrites: a filled file is kept, and a new story or tool
   gets its file and its line in the index.

   Scaffold also writes one instruction into the project's agent file — `AGENTS.md`, else `CLAUDE.md`, else a new
   `AGENTS.md` — in a block marked `<!-- app-verification:start/end -->`: before saying a feature works, prove it
   with these manuals. The block is rewritten in place on every run, so it always names the current manuals, and
   everything else in the file is left as it was. `check` reports it if it is missing.
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
   python3 <skills>/app-verification/scripts/verify_map.py check <project-root>
   ```

   Every surface first: a surface with no manual is a problem of its own (`verify-agent: no manual for the agent
   surface at agent`).

   It refuses a `<fill: …>` left anywhere, a missing section, a story without a file, a feature file out of shape or
   missing from the index, a script that is not executable or that SKILL.md never names, an evidence directory git
   does not ignore. Unfilled features beyond the first few stay as they are and fail the check: say how many remain.
7. **Record** the `verification` block through the contract's lock, then append the run:

   ```bash
   python3 <skills>/app-verification/scripts/verify_map.py record <project-root> --json '<the block below>'
   python3 dev-flow/scripts/update_meta.py <project-root> append-history --skill app-verification
   ```

   `record` refuses a block that is missing any of the contract's keys.

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

## The render probe — what a screenshot does not tell you

`scripts/render_probe.mjs` opens a page in headless Chrome at 1440, 768 and 390 px and measures what no source scan
can see: the page wider than the viewport (and the elements causing it), a heading on more than two lines, text that
stays invisible with reduced motion on, a declared font that never loaded, an image that loaded with no picture, a
sidebar covering a phone.

```bash
node <skills>/app-verification/scripts/render_probe.mjs http://localhost:<port>/<route> [--widths 1440,768,390] \
    [--out .verification/evidence/<UTC timestamp>/probe] [--json] [--strict]
```

- **Give it the dev server's URL**, or a `file://` path for a static page. It serves no files of its own — a probe
  that served the working directory would expose `.env` to every script the page loads.
- **Per locale**: run it on `/en/...` and `/it/...` — the two-line headline rule is about the longest one.
- Needs Node ≥ 22 and an installed Chrome, Chromium or Edge (`CHROME_PATH`). No dependency, a throwaway profile
  removed on every exit, nothing written outside `--out`. Exit 0 (a measurement), 1 with `--strict` and a FAIL,
  2 bad input, **3 the environment** (no browser, Node too old — skip, and say so), **4 the page** (it would not load
  or timed out — a broken run, never a skip). `--timeout` (default 60 s) leaves room for a cold `next dev` compile.
- A client-side redirect is followed and reported: the report's `final_url` and a `redirected` note say which page
  was measured.
- A finding is a lead, read like shadscan's: open the element, decide, fix the cause. Never hide an element from the
  probe to make it pass.

The manual's Evidence section names it for the routes a feature touches (`references/manual.md`), and
`design-md-to-app` runs it at its 375 px verification. The idea comes from taste-skill v2's inspector
(Leonxlnx/taste-skill, MIT); the code and the rules are ours.

## Rules

- **Never drive or stop an instance you did not start.** Record the PID and the port at launch; stop those. Never by
  process name. If the user's dev server is already on the port, launch on another one or ask.
- **Never weaken a journey to make it pass.** A missing precondition is a failure, and its reason goes in the
  feature's Gotchas.
- **Never commit in the project.** Create and maintain leave their files in the working tree; the user sees them in
  the diff and decides.
- **Credentials never in chat or in the manual.** Test accounts come from the project's seed or example files, and the
  manual names the file, not the password.
- **Prove one commit.** Record `git rev-parse HEAD` at launch and have the doctor fail if it moves: a project in
  active development can be merged into or switched under the run (Archi Studio, 2026-10-18: `main` moved two PRs
  mid-run, files vanished, the page reloaded). When it moves, stop, clean up, relaunch — or verify in a separate
  `git worktree` nobody else touches.
- **Leave the project as you found it.** A custom build directory (`NEXT_DIST_DIR`) makes `next dev` add it to
  `tsconfig.json`'s `include`: record whether the file was clean at launch and restore it at Cleanup.
- **Prefer the project's isolated test stack** when it has one (an in-memory database, a fixed sign-in code, a mock
  model): no shared data to clean, and an agent proven for free. Archi Studio's Playwright config had all three.
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
- `scripts/render_probe.mjs` + `scripts/test_render_probe.py` (fixtures in `scripts/fixtures/probe/`) — the render probe.
- `references/contracts.md` — the `.workflow/` dev-flow contract (vendored).
