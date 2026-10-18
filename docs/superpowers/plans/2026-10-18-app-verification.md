# app-verification Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A dev-flow skill, `app-verification`, that writes into a project a manual (`.claude/skills/verify-<app>/`)
an agent follows to start the real app, drive one feature the way a user does, keep the proof, and shut down what it
started. It also keeps that manual true as the app changes.

**Architecture:** A stdlib script, `app-verification/scripts/verify_map.py`, does the mechanical part:
- `scaffold` writes the manual's skeleton and one feature file per PRD story, from the wireframe inventory, or from
  the routes when there is none;
- `check` refuses a manual that still has a gap.

The agent does the reading part: launch, selectors, results. It proves the manual once, live, guided by `SKILL.md`
and three references. dev-flow proposes the skill once there is something to drive, and `show_state` notes a manual
that is missing or older than the last change.

**Tech Stack:** Python 3.9+ stdlib (`re`, `pathlib`, `dataclasses`, `json`, `argparse`, `os`); `unittest`; Markdown.

**Spec:** `docs/superpowers/specs/2026-10-18-app-verification-design.md`

## Global Constraints

- The manual lives at `<project>/.claude/skills/verify-<app>/`, with:
  - `SKILL.md`;
  - `features/README.md`;
  - `features/<US-N>-<slug>.md`;
  - optionally `scripts/`.
- The six H2 sections of the generated `SKILL.md`, in this order: `Launch`, `Doctor`, `Drive`, `Evidence`, `Cleanup`,
  `Isolation`.
- The four H2 sections of every feature file, in this order: `Sub-features`, `How to get to it (user POV)`,
  `Driving it with <harness>` (the check matches the prefix `Driving it with`), `Gotchas`.
- The unfilled marker is exactly `<fill: …>`, matched by the regex `<fill:[^>]*>`. No other angle-bracket text counts
  as a placeholder, because commands and JSX contain `<…>`.
- Proof goes to `.verification/evidence/<UTC timestamp>/`, and `.verification/` must be listed in the project's
  `.gitignore`.
- Stories are parsed from PRD list items `- **US-N.** <sentence>`. Inventory rows come from the `wireframe-canvas`
  table `| ID | Screen | Route | Roles | Stories | States |`, under `## <letter> — <area>` headings.
- `scaffold` never overwrites an existing file. It reports it as kept.
- Nothing is committed in a user project. Create and maintain leave their files in the working tree.
- Never drive or stop an instance the run did not start. Never kill by process name.
- `meta.json#verification` has exactly the spec §5 shape:
  ```json
  {"skill", "features", "source": "wireframes|routes", "proven_at", "proven_feature", "evidence", "maintained_at", "maintain_outcome"}
  ```
  In a monorepo, `skill` is a list. No phase bump, ever; always a history entry.
- Attribution: pstack (Lauren Tan, MIT, `cursor/plugins/pstack`) is credited in `SKILL.md` Sources and in
  `resources.md`. Its text is rewritten, never copied.
- TAXONOMY entry: `"app-verification": ("core", "operative")`.
- The skill count goes from 54 to 55, and core from 12 to 13.

## Review Focus

1. **A PRD whose stories are only in a table**, not in `- **US-N.**` items (fit-coach has both): `scaffold` must take
   the list items only, never duplicate a story, and say "0 stories found" rather than writing nothing silently.
   Test owner: Task 1.
2. **A re-run of `scaffold` on a manual the agent has already filled**: nothing filled is lost, and a story added to
   the PRD since the first run gets its file. Test owner: Task 1.
3. **`<fill:` inside a fenced code block** is still a gap: `check` must not skip code blocks. Test owner: Task 1.
4. **A Next.js `app/[locale]/(group)/…` tree with no inventory**: the routes fallback strips route groups, keeps
   dynamic segments, and lists each route once. Test owner: Task 1.
5. **A project that is not a git repo, or that has no `.gitignore`**: `check` reports the evidence directory as not
   ignored. It must not crash, and must not pass. Test owner: Task 1.

---

### Task 1: `verify_map.py` — scaffold and check

**Files:**
- Create: `app-verification/scripts/verify_map.py` (stdlib, same layout as `app-security/scripts/`)
- Test: `app-verification/scripts/test_verify_map.py`

**Interfaces:**
- Produces:
  - `stories(prd: str) -> list[tuple[str, str]]`: `(id, sentence)` pairs, in PRD order, deduplicated.
  - `@dataclass Screen(id: str, area: str, name: str, route: str, roles: list[str], stories: list[str], states: list[str])`
  - `inventory(text: str) -> list[Screen]`
  - `routes(root: Path) -> list[str]`: Next `app/**/page.(tsx|ts|jsx|js)` and `src/app/**`; Expo `app/**/*.tsx`
    without `_layout`, `+not-found` or `+html`. Route groups `(x)` are dropped, dynamic segments `[x]` kept, each
    route listed once, sorted.
  - `scaffold(root: Path, app: str = "web") -> dict`: returns
    `{"path": str, "source": "wireframes"|"routes", "written": [str], "kept": [str], "stories": int}`.
  - `check(root: Path, app: str = "web") -> list[str]`: problems, empty when the manual is complete.
  - CLI: `verify_map.py scaffold|check <root> [--app web] [--json]`. `check` exits 1 when there are problems.

- [ ] **Step 1: Write the failing tests** in `test_verify_map.py`. Each test builds a temporary project.
  - `test_stories_from_list_items_only`: a PRD with a table row `| M1 | … | US-1 |` and items `- **US-1.** As a trainer…`
    and `- **US-2.** As a client…` gives `[("US-1", "As a trainer…"), ("US-2", "As a client…")]`.
  - `test_inventory_rows`: the two-row `A — Public site` table from `wireframe-canvas/SKILL.md` gives `Screen("A1",
    "A — Public site", "Home (hero, search, featured trips)", "/", ["visitor"], ["US-6", "US-48"], ["L"])`, and A2 has
    states `["L", "E"]`.
  - `test_routes_strip_groups_keep_dynamic`: pages at `app/[locale]/(marketing)/page.tsx`,
    `app/[locale]/(trainer)/trainer/plans/[id]/page.tsx` and `app/[locale]/(trainer)/trainer/plans/page.tsx` give
    `["/[locale]", "/[locale]/trainer/plans", "/[locale]/trainer/plans/[id]"]`.
  - `test_scaffold_from_inventory`:
    - with a PRD of 2 stories and an inventory mapping A1 to US-1, `source == "wireframes"`;
    - `features/US-1-*.md` exists, and its `How to get to it (user POV)` names `A1` and `/`;
    - its `Sub-features` lists `L` as `loading`;
    - `SKILL.md` has the six H2s and frontmatter `name: verify-web`.
  - `test_scaffold_falls_back_to_routes`: with no inventory, `source == "routes"`, `features/README.md` says
    `no screen inventory`, and the routes are listed in it.
  - `test_scaffold_keeps_filled_files_and_adds_new_stories`:
    - scaffold, then replace one feature file's content with `filled`, then add US-3 to the PRD and scaffold again;
    - the filled file still reads `filled`, `US-3-*.md` exists, and `kept` contains the filled file.
  - `test_scaffold_with_no_stories_says_so`: a PRD with no story items gives `stories == 0`, and the CLI prints
    `0 stories found`.
  - `test_check_flags_each_gap`. Start from a complete manual (a test helper writes one). Then each of these, one at a
    time, makes `check` return a problem naming it:
    - a `<fill: launch command>` inside a fenced block in `SKILL.md`;
    - the `Doctor` section removed;
    - a PRD story with no feature file;
    - `scripts/doctor.sh` not executable;
    - `scripts/doctor.sh` executable but never named in `SKILL.md`;
    - `.gitignore` missing `.verification/`;
    - no `.gitignore` at all;
    - a feature file with `Gotchas` before `Sub-features`;
    - a feature file not linked from `features/README.md`.
  - `test_check_passes_a_complete_manual`: the helper's complete manual gives `[]`, and the CLI exits 0.
  - `test_cli_json`: `check --json` prints `{"problems": [...]}`.

- [ ] **Step 2: Run them.**
  Run: `cd app-verification/scripts && python3 -m unittest test_verify_map`
  Expected: errors, because `verify_map` does not exist.

- [ ] **Step 3: Implement `verify_map.py`.**
  - The slug is the first six words of the story's action (the text after `I want to`, or the whole sentence),
    lowercased, non-alphanumerics to `-`.
  - The skeleton's text:
    - `SKILL.md` has one `<fill: …>` per section, saying what goes there (the spec §1 table).
    - The `Evidence` section states the proof standards in full: the spec §«Cosa prendiamo», standards bullet.
    - `features/README.md` is filled text, apart from the index and the baseline preconditions:
      - the baseline preconditions are `<fill: …>`;
      - the driving conventions: ARIA roles and accessible names first, literal commands, restore seeded data,
        never remove proof;
      - the proof rules: action plus resulting state, a second view of a mutation, an unreachable path reported with
        its unmet precondition, never verified through a different entry point.
    - The state letters map as `L` → loading, `E` → empty, `Er` → error, `S` → success.

- [ ] **Step 4: Run them.** Same command. Expected: `OK`. Then `uv run -q --python 3.9 python -m unittest
  test_verify_map`. Expected: `OK`.

- [ ] **Step 5: Commit.** Use `SKIP_REGEN=1`, because the skill has no `SKILL.md` yet. Message:
  `feat(app-verification): verify_map.py — the manual's skeleton from the inventory, and a check that refuses gaps`.

### Task 2: The skill, its references, the contract and registration

**Files:**
- Create:
  - `app-verification/SKILL.md`;
  - `app-verification/references/manual.md`: the six sections and the feature-file shape, each with what a filled
    one looks like, using a shortened version of the pstack Notes example rewritten for a Next.js app;
  - `app-verification/references/stack-recipes.md`: the spec §3 table expanded into one recipe each for web, Expo,
    eve and monorepo, naming the Claude Code tools (browser preview from `.claude/launch.json`, iOS simulator) and
    the repo harness that takes precedence (Playwright, Maestro);
  - `app-verification/references/maintain.md`: spec §4 maintain, steps 1–5, the three invariants, the triage table,
    and the outcomes `clean`, `changed`, `blocked`;
  - `app-verification/references/contracts.md` (the vendored copy).
- Modify:
  - `dev-flow/references/contracts.md`: a `### \`verification\` field (owned by \`app-verification\`)` section with
    the spec §5 JSON, plus the monorepo list form. Propagate it to every `*/references/contracts.md`.
  - `dev-flow/references/resources.md`: a pstack row under "Agent skills and mods (third party)". Verdict:
    **extracted, not installed**. MIT. What we took, what we did not and why. Checked 2026-10-18.
- Register in the same commit, because the pre-commit hook refuses a skill that is not registered (the app-security
  Task 3 ruling):
  - `install.sh`, `uninstall.sh`;
  - `TAXONOMY`;
  - the README catalogue row and section, and the counts 54 → 55 and core 12 → 13;
  - the skill map row and counts;
  - `.claude-plugin/marketplace.json`;
  - the CHANGELOG `Added` entry;
  - the bundle.

**Interfaces:**
- Consumes: the CLI of Task 1.

- [ ] **Step 1: Write `SKILL.md`.**
  - The description is ≤ 1024 characters and has `Triggers` and `Not for:`.
    - Triggers: "verify the app", "prova che funziona", "verification skill", "come si avvia l'app per provarla",
      "maintain the verify skill", "il manuale di verifica è aggiornato?".
    - Not for: writing tests (`write-tests`), UI audits (`shadscan`), security (`app-security`), deploying
      (`vercel-deploy`).
  - The body:
    - the problem;
    - the two modes, create (spec §4, steps 1–7) and maintain (pointing to `references/maintain.md`);
    - the rules: never drive what you did not start, never commit in the project, never weaken a journey, a manual
      never run is a draft;
    - what to record in `meta.json#verification`: edit the block directly, plus
      `update_meta.py <root> append-history --skill app-verification`;
    - relationships: `write-tests` (a proven journey becomes a test), `wireframe-canvas` (the inventory feeds the
      map), `superpowers:verification-before-completion`;
    - Sources, with pstack.

- [ ] **Step 2:** Write the three references, the contract section, the `resources.md` row and the registration.
  Run `bash scripts/regenerate.sh`, then `python3 scripts/lint_skills.py`. Expected: `✓ Clean`.

- [ ] **Step 3:** Run `python3 scripts/build_skill_bundles.py app-verification`, then `--check`. Expected: `✓ dist/
  matches the sources (55 bundles)`. The 43 `contracts.md` copies change, so the hook rebuilds those bundles too.

- [ ] **Step 4: Commit.**
  `feat(app-verification): the skill, its manual and stack references, the contract field and registration`.

### Task 3: Wiring into dev-flow

**Files:**
- Modify `dev-flow/scripts/show_state.py`:
  - add `verification_line(meta: dict, root: Path) -> str | None`;
  - call it from `main()` beside the other notes;
  - in `PHASE_NEXT_BY_STACK`, mention `app-verification create` in `page_generated` (next, expo-rn, monorepo) and in
    `scaffolded` (agent), and `app-verification maintain` in `feature_complete` (every stack, before the gates).
- Modify:
  - `dev-flow/scripts/test_show_state.py`;
  - `dev-flow/SKILL.md`: a capability line, `**Verification** — app-verification`, and the routing table regenerated;
  - `dev-flow/references/policies.md`: a `**Proof policy.**` paragraph with the proof standards, valid without the
    manual;
  - `spec-review/SKILL.md`: one line, where it reports "not proven", pointing to the manual;
  - `write-tests/SKILL.md`: one line, saying a proven journey and its recipe are the starting point for a test;
  - `wireframe-canvas/SKILL.md`: one line, saying the inventory also feeds `app-verification`'s map.

**Interfaces:**
- Consumes: `meta.json#verification` (Task 2's contract).
- Produces: `verification_line`, which returns `None` when there is nothing to say. Otherwise:
  - with no manual: `Verification: no manual yet — app-verification create`;
  - with a stale manual: `Verification: the manual predates the last change (<skill> at <ran_at>) — app-verification
    maintain`.

  Wording is free inside those two meanings.

- [ ] **Step 1: Write the failing tests** in a new class `Verification(Fixture)`.
  - `test_no_note_before_there_is_something_to_drive`: phase `scaffolded`, framework `next`, no manual → `None`.
  - `test_missing_manual_is_noted`: phase `page_generated`, no `verification` block and no
    `.claude/skills/verify-*` → the result contains `app-verification create`.
  - `test_manual_on_disk_without_meta_is_not_missing`: `.claude/skills/verify-web/SKILL.md` exists, but `meta` has no
    block → the result does not contain `create`.
  - `test_stale_manual_is_noted`:
    - `verification.proven_at = 2026-10-01T00:00:00Z`;
    - history has `{"skill": "module-add", "ran_at": "2026-10-10T00:00:00Z"}`;
    - the result contains `maintain`.

    The skills that count as a material change are `module-add`, `screenshot-to-page`, `rn-add-screen`,
    `rn-module-add` and `eve-agent`.
  - `test_fresh_manual_is_silent`: `maintained_at` is later than every material history entry → `None`.
  - `test_agent_projects_from_scaffolded`: framework `agent`, phase `scaffolded`, no manual → the result contains
    `create`.
  - `test_routing_mentions_verification`: `next_step("page_generated", "next")` contains `app-verification`, and
    `next_step("feature_complete", fw)` contains it for every fw in `PHASE_NEXT_BY_STACK`.

- [ ] **Step 2: Run them.**
  Run: `cd dev-flow/scripts && python3 -m unittest test_show_state`
  Expected: failures and errors in the new tests only.

- [ ] **Step 3:** Implement, and make the six prose edits.

- [ ] **Step 4: Run them.**
  - `cd dev-flow/scripts && python3 -m unittest test_show_state`. Expected: `OK`.
  - `python3 scripts/sync_routing_table.py`, then the same with `--check`. Expected: `✓ … matches show_state.py`.

- [ ] **Step 5: Commit.**
  `feat(dev-flow): propose app-verification once there is something to drive, and note a stale manual`.

### Task 4: The real run on fit-coach

**Files:**
- In `~/projects/fit-coach`, left **uncommitted**:
  - `.claude/skills/verify-web/`;
  - `.claude/launch.json`, only if it is missing;
  - `.gitignore` gains `.verification/`;
  - `.workflow/meta.json#verification` plus a history entry.
- In this repo: any fix that the run proves necessary, with a test.

- [ ] **Step 1: Read-only first.**
  - Run `python3 app-verification/scripts/verify_map.py scaffold ~/projects/fit-coach --json`.
  - Expected:
    - `source: "routes"`, because fit-coach has no inventory;
    - `stories: 12`;
    - 12 feature files;
    - no traceback.
  - Then run `check`. Expected: problems listing the `<fill:` markers.

- [ ] **Step 2: Fill and prove.** Follow `app-verification/SKILL.md` create mode as written, on fit-coach.
  - Fill Launch, Doctor, Drive, Evidence, Cleanup and Isolation from the repo: `package.json`, `.env.example`, the
    seed scripts, the routes.
  - Fill US-1 and two more features.
  - Prove one feature live in the built-in browser:
    1. launch;
    2. doctor;
    3. drive;
    4. evidence written;
    5. cleanup;
    6. evidence still present.
  - Test credentials come from fit-coach's own seed or example files, never typed in chat, and are recorded in the
    project's seed or example-config file.
  - If the app cannot start as it is (database, secrets), stop and report precisely what is missing. Do not invent
    a stand-in. A stand-in's extra steps must be listed as unverified.

- [ ] **Step 3: Run `check`.** Expected: `[]`. Then write `meta.json#verification` and the history entry.

- [ ] **Step 4: Fix what the run found.** Every place where the skill's instructions or the script led the run
  wrong gets a ruling in the ledger and a fix with a test written first. Commit:
  `fix(app-verification): what the first real run on fit-coach taught`.
  Skip the commit if there was nothing to fix.

### Task 5: Whole-branch verification

- [ ] **Step 1:** Run, and read the output of, each of these:
  - the lint;
  - every suite;
  - bundles `--check`;
  - routing `--check`;
  - `python3 evals/compliance/comply.py selftest`;
  - the `verify_map` suite on 3.9.
- [ ] **Step 2: Report.**
  - the files changed;
  - the fit-coach result: which feature was proven, where the evidence is, and what is still unfilled;
  - that nothing was committed in fit-coach;
  - every ruling.

## Spec coverage

| Spec | Task |
|---|---|
| §1 Manual layout and six sections | 1 (skeleton, check), 2 (`manual.md`) |
| §2 Feature map from the inventory, routes fallback | 1 |
| §3 Stack recipes | 2 (`stack-recipes.md`) |
| §4 create steps 1–7 | 1 (scaffold, check), 2 (`SKILL.md`), 4 (live proof) |
| §4 maintain | 2 (`maintain.md`) |
| §5 `meta.json#verification` | 2 (contract), 4 (written) |
| §6 In the flow | 3 |
| Tests | 1, 3, 4, 5 |
| Attribution, MIT | 2 |
