---
name: wireframe-canvas
description: 'The step between DESIGN.md and the scaffold, on every project with a UI: a screen inventory mapped to the PRD''s user stories, then every screen drawn as a desktop (1440) and a phone (390) artboard on a claude.ai Design canvas, high fidelity in DESIGN.md with real copy, one canvas page per area, reviewed area by area. No scaffold until the user approves the canvas — `update_meta.py set-phase` refuses it. After approval, a PNG of every artboard is committed and commented on each GitHub or Linear issue whose story maps to the screen. Writes `meta.json#wireframes`. Use when dev-flow routes here from `design_extracted`, or the user says "wireframe", "tutte le schermate", "disegna le schermate", "artboard", "canvas", "screen inventory", "mockup di ogni pagina". Not for: extracting a DESIGN.md (`figma-to-design-md`, `image-to-design-md`), building pages (`screenshot-to-page`, `rn-add-screen`), or agent-only projects (no screens).'
---

# wireframe-canvas — every screen, drawn and approved, before any code

A standing rule of the user's (2026-10-10): **no feature code and no scaffold until every screen of
the product exists as an artboard and the user has approved the set.** A screen discovered while
coding costs a route, a layout and a review; on the canvas it costs a frame. And the issue tracker
gets the overall picture, so whoever picks up an issue sees the screen it builds.

## Contract

See `references/contracts.md` (vendored from `dev-flow`). Key facts:

- Reads `.workflow/PRD.md` (the `US-N` stories), `.workflow/tasks.md`, `.workflow/DESIGN.md`, `meta.json#stack`.
- Writes `docs/wireframes/screen-inventory.md`, `docs/wireframes/png/<ID>-desktop.png` / `<ID>-phone.png`,
  and `meta.json#wireframes` through `scripts/wireframes.py` — never by hand.
- **Does not bump `phase`.** It appends `history`. The scaffold skill bumps it, and `set-phase` refuses
  to cross into `monorepo_initialized` / `scaffolded` until `wireframes` is approved or skipped with a reason
  (`dev-flow/scripts/wireframes_gate.py`). Projects already past `scaffolded` are not asked retroactively;
  `show_state.py` flags them.
- Every stack with a UI: `next`, `expo-rn`, `monorepo`. **Refuses `framework: "agent"`** — no screens.
- Needs `DESIGN.md` first: the artboards are drawn in it, not in a placeholder grey.

## Step 1 — The screen inventory

`docs/wireframes/screen-inventory.md`: every route and screen of every epic, grouped by area (one `##`
per area, letter-prefixed), one table per area:

```markdown
## A — Public site

| ID | Screen | Route | Roles | Stories | States |
|---|---|---|---|---|---|
| A1 | Home (hero, search, featured trips) | `/` | visitor | US-6, US-48 | L |
| A2 | Destinations index | `/destinations` | visitor | US-55 | L, E |
```

- **ID** is stable (`A1`, `B12`): it names the artboards, the PNGs and the issue comments.
- **Stories** lists the PRD's `US-N`; **States** lists the ones the screen has — `L` loading, `E` empty,
  `Er` error, `S` success — or `—`. Dialogs, sheets, banners and inline cards that change the flow are rows
  too (Route `dialog`, `overlay`, `panel`).
- Walk the PRD story by story, then the roles (each role's home, settings, empty first run), then the
  edges (auth, invite, legal, 404, offline on mobile).

Check it — every story maps to at least one screen, IDs are unique, no empty States cell:

```bash
python3 wireframe-canvas/scripts/wireframes.py coverage <root>
python3 dev-flow/scripts/update_meta.py <root> record-artifact --path docs/wireframes/screen-inventory.md \
    --produced-by wireframe-canvas --derived-from .workflow/PRD.md
```

Show the user the inventory (counts per area, any story you were unsure about) before drawing.

## Step 2 — The canvas, area by area

1. `Artifact action:"quickstart" intent:"design"` — it names the **Design** type and the design systems.
   Create the canvas from that type, titled `<Project> · wireframes`, and follow the instructions the
   create result returns for filling it. Do not guess the type's file format.
2. **One canvas page per area** of the inventory (`A — Public site`, `B — Authentication`, …).
3. **Two artboards per screen**: desktop **1440** wide and phone **390** wide, labelled
   `<ID> · <Screen> · desktop` / `· phone`. The States column is drawn as well — extra artboards beside the
   pair (`A2 · empty · phone`). The pair is the minimum the gate counts.
4. **High fidelity in DESIGN.md**: its colours, type scale, radius and spacing, and the primitives the
   project will compose (golden rule 3) — a canvas that draws a component the library does not have is a
   promise the scaffold cannot keep. **Real copy in the user's language**, no lorem ipsum, realistic data.
5. **Work one area at a time.** Finish an area, give the user the canvas link and the page, and stop for
   their review. Apply the changes; move on only when they say the area is right. Append a `history`
   entry per reviewed area (`--skill wireframe-canvas --inputs '{"area": "A", "artboards": 26}'`).

## Step 3 — Approval

Only the user's own explicit yes for the **whole** canvas approves it. Then:

```bash
python3 wireframe-canvas/scripts/wireframes.py approve <root> --canvas-url <url> --user-said "<their words>"
```

It re-runs the coverage check, counts the screens, and refuses fewer than two artboards per screen
(`--artboards N` when the states add more). In an autonomous run this is never derived: stop with
*"needs a human: approve the wireframe canvas"* and leave the canvas link.

**Opting out** is allowed and visible — a one-screen internal tool, a pure API with a status page:

```bash
python3 wireframe-canvas/scripts/wireframes.py skip <root> --reason "<why this project has no screens to draw>"
```

## Step 4 — After approval: screenshots on the issues

1. **Render a PNG of every artboard** at its native width (1440 / 390), by screenshotting the canvas in
   a browser, into `docs/wireframes/png/<ID>-desktop.png` and `<ID>-phone.png`.
   `wireframes.py pngs <root>` lists what is missing; it must print none.
2. **Commit them by name** (`git add docs/wireframes/`, never `git add -A`) and push. Note the commit SHA:
   the image links are pinned to it, so a later edit of a PNG does not rewrite an old comment.
3. **Write the comment bodies** — one per issue whose user story (the `Stories` column, matched through the
   task's epic heading, its `### US-N` heading or its own text in `tasks.md`) maps to a screen:

   ```bash
   python3 wireframe-canvas/scripts/wireframes.py comments <root> --repo <owner>/<name> --ref <sha> \
       --out .workflow/wireframe-comments --map .workflow/github-issues.json
   ```

   It prints the plan (issue → screens → body file). Show the user the count and one body, then post —
   comments are posted on the user's behalf, so confirm once for the batch:
   **GitHub** `gh issue comment <n> --body-file <file>`, 2 s apart. **Linear**: resolve each task to its
   issue through `meta.json#linear.issue_map` (`linear-scrum`'s `task_key`; run `comments` without
   `--map` to key bodies by task title), attach the PNGs to the issue with the Linear connector and
   comment the body.
4. Record it: `python3 wireframe-canvas/scripts/wireframes.py posted <root>` → `wireframes.screenshots_posted_at`.

Then hand back to dev-flow: `design-md-to-app` (web), `rn-bootstrap` (mobile), `monorepo-bootstrap`.

## When the screens change later

A new screen after approval is a new inventory row and a new artboard pair first, then code. Re-run
`approve` (same URL) so the counts are current, and comment the new PNGs on the issues they touch.
`screenshot-to-page` and `rn-add-screen` take the approved artboard PNG as their input.

## Bundled

`scripts/wireframes.py` (`coverage`, `approve`, `skip`, `pngs`, `targets`, `comments`, `posted`; stdlib
only) + `scripts/test_wireframes.py`; `references/contracts.md`. The gate itself is
`dev-flow/scripts/wireframes_gate.py`, so dev-flow enforces it without this skill installed.
