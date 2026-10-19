# The manual, part by part

Every part below is filled from what the repo really contains. The example is a small Next.js app, "Notes", with
better-auth and Drizzle; the shape is pstack's (MIT), the content is ours.

## SKILL.md — the six sections

### Launch

The command, the port, the env, and **how you know it is ready** — usable, not just answering. From an empty data
dir: migrations and seed included. A health check that passes while the database is still running its init scripts
is not ready.

> `PORT=3100 pnpm dev`, with `.env.verify` (copied from `.env.example`, database `notes_verify`). First run:
> `pnpm db:migrate && pnpm db:seed`. Ready when `curl -sf http://127.0.0.1:3100/api/health` returns `{"db":"ok"}`
> **and** `/sign-in` renders the `Sign in` button. Port 3100, not 3000: 3000 is the user's own dev server.
> Started PID and port are written to `.verification/run.json`. The same command is `verify-notes` in
> `.claude/launch.json`.

For a short-lived CLI there is no server: launch means build once, then start each drive in its own PTY session.

### Doctor

One read-only check that answers "is this instance worth driving?". Run it first, and again after anything
surprising — a failed drive, a page that did not change.

> `doctor.sh`, in the manual's scripts folder: the PID in `.verification/run.json` is alive; port 3100 is held by that PID; `/api/health`
> says `db: ok`; the build id in `/api/health` matches `.next/BUILD_ID`.

### Drive

The harness for this stack (`stack-recipes.md`) with the repo's **real** handles: ARIA roles and accessible names,
`data-` attributes, routes. Never coordinates or tab order — they change with the layout.

> The built-in browser at `http://127.0.0.1:3100`. Sign in as the seeded trainer (credentials: the project's seed, `seed.ts`,
> `TRAINER_EMAIL`). Buttons by accessible name (`New note`, `Save note`), fields by label (`Title`).

### Evidence

Where the proof goes and what counts. The standards are fixed (`verify_map.py` writes them); add what proof looks
like on this app.

> `.verification/evidence/<UTC timestamp>/`: the accessibility snapshot and a screenshot after the action, and the
> row read back with `pnpm db:query "select title from notes where title = 'Release checklist'"`.

For a web surface, add the render probe on the routes the feature touches, in each locale — its report and one
screenshot per width land in the evidence directory, and a FAIL there is a finding like any other:

> `node <skills>/app-verification/scripts/render_probe.mjs http://localhost:3100/it/notes --out .verification/evidence/<ts>/probe-it`

### Cleanup

Stop what this run started, by the PID and port it recorded — never `pkill node`. Remove scratch data. Keep the
evidence.

> Kill the PID in `.verification/run.json`; drop the rows the run created (`title like 'verify-%'`); leave
> `.verification/evidence/` alone.

### Isolation

Whether two instances can coexist, and what the manual refuses.

> Yes: one port and one database per run (`PORT`, `DATABASE_URL`). The manual never drives port 3000, which is the
> user's.

## features/README.md

Baseline preconditions (filled), then the fixed parts `verify_map.py` writes — driving conventions, proof and skip
reporting — and the index. With no screen inventory, it also lists the routes found and says the map was matched to
the stories by hand.

## features/US-N-slug.md

```markdown
# US-1 — As a trainer, I want to invite clients and see them, so that I manage them.

A trainer sends an invite by email; the client appears as "Invited" until they accept.

## Sub-features

- `us-1-loading` loading state of B2 Clients list
- `us-1-empty` empty state of B2 Clients list
- `us-1-invite` send an invite; `us-1-cancel` close the dialog without sending

## How to get to it (user POV)

- B2 Clients list — `/trainer/clients` (trainer)
- B3 Invite dialog — `dialog` (trainer), from the `Invite client` button

## Driving it with the built-in browser

Preconditions:

- Signed in as the seeded trainer; no client named `verify-anna@example.test`.

- **Open the dialog.** Choose `Invite client`. Click the button with accessible name `Invite client`. A dialog named
  `Invite a client` opens with focus on `Email`.
- **Send.** Fill `Email` with `verify-anna@example.test`, choose `Send invite`. A status `Invite sent` appears and
  the list shows `verify-anna@example.test` with the badge `Invited`.
- **Second view.** Reload `/trainer/clients`; the row is still there. Read it back:
  `select status from clients where email = 'verify-anna@example.test'` → `invited`.

## Gotchas

- The email goes through Resend in development too unless `RESEND_API_KEY` is empty — use the `.test` domain.
- The list is paginated at 20; search for the email instead of scrolling.
```

The four H2s are fixed and in this order; `check` refuses anything else. A story that does not apply to this surface (a web-only story in `verify-mobile`) keeps its file, with one line under Gotchas saying so and why: the map stays complete and nothing is driven in its name. A story whose precondition the seed cannot
provide is not shortened to pass: the journey reports the failure and the reason goes in Gotchas.
