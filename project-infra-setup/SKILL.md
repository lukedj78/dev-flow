---
name: project-infra-setup
description: 'Set up a project''s third-party environments from the command line: the GitHub repo, the Vercel project (region, environment variables, Git link), marketplace connectors (Neon Postgres, Blob storage, Resend email), DNS records and domains, secrets handled without ever pasting them in chat, and the sub-processor register. Use when the user says "configura Vercel / Neon / Resend", "crea il progetto su Vercel", "collega il repo a Vercel", "configura il dominio / i DNS per le email", "variabili d''ambiente", "ambienti di terze parti", "setup dell''infrastruttura", or before `module-add` (db, email, storage, deploy) needs an account that does not exist yet. Checks the region of every service before and after creating it, and confirms each outward step. Not for: wiring the code (`module-add`), deploying (`vercel-deploy`), or the PRD, design and tasks (other skills).'
---

# project-infra-setup — the third-party environments, from the CLI

Everything outside the codebase that a project needs before `module-add` can wire it: **Git, Vercel, the connectors (Neon, Resend, Blob), DNS, secrets**. Done once per project, in a fixed order, with the traps already written down. Worked on BidFlow (2026-10-03). The commands and findings are in `references/provisioning.md`; this file is the order and the rules.

It owns the **accounts and the CLI-level resources**. It does not write application code (`module-add` owns that), does not deploy (`vercel-deploy` owns that), and does not touch the PRD, design or tasks.

## Rules (they held up)
1. **Every outward step is confirmed, one at a time**: create the repo, create the project, create a database, write a DNS record, create or revoke a key, send a test email. A "yes" to the plan is not a "yes" to each step.
2. **Check the region of every service before and after creating it.** The default is US (`iad1`) for functions, Blob and Neon, and a database region **cannot be changed afterwards**. Read it back from the service (`PGHOST`, the project API), not from the CLI's summary.
3. **Secrets never go through chat.** The user types them in their own terminal (`vercel env add NAME --cwd <project>`), or you generate and set them yourself from stdin without printing. Narrow every key you can (a send-only key limited to the domain), prove it works against the provider's sink address, then revoke the broad one.
4. **Whatever a tool installs on its own is reviewed before it stays.** Marketplace integrations drop third-party agent skills into the repo (`.agents/`, `.claude/skills/`, `skills-lock.json`), every time. Move them out, read them, let the user decide (`registry-intake skill-review`). They steer an agent toward the vendor's stack.
5. **Read the plan's terms for the use the project really has.** Vercel Hobby is restricted to non-commercial personal use; a company tool is arguably commercial. It is the user's decision: record it as a known risk to revisit, do not decide for them and do not keep asking.
6. **Reuse what exists.** Look at `vercel whoami`, `vercel teams ls`, `vercel domains ls`, the DNS zone and the integrations first. A Resend account already in the zone beat the marketplace route, which collided with it.
7. **Do not connect Git to Vercel before the app exists** (the first push would publish the repo's documents at a public URL), and do not assign the custom domain before the first deploy.
8. **Say what failed and what you got wrong** (a database that landed in the wrong region was deleted and recreated), and what you did not look at.

## The sequence
0. **Inspect.** Who is logged in, which team and plan, which domains and DNS records, which integrations and resources already exist. Run the inventory (`dev-flow`'s `inventory.py scan`) if the project is new.
1. **Decide** with the user: plan, regions (EU first), the domain and sub-domain, whether email goes through the marketplace or an existing account, the tracker (GitHub Issues or Linear).
2. **GitHub repo.** Private, initial commit by file name, **secret scan on the staged diff before pushing** (`.gitignore` must ignore `.env*` and allow `!.env.example`). Optional, when the user chose GitHub as the tracker: one issue per task with `scripts/make_issues.py` (resumable, tested), labels by area and type, the map committed.
3. **Vercel project and region.** `vercel project add`, `vercel link --yes`, the function region through the project API, read back.
4. **Postgres (Neon).** `vercel integration add neon -m region=fra1 -m auth=false`; metadata keys come from the API, not `--help`; verify the region from `PGHOST`; quarantine the skills it installs.
5. **Files (Blob).** `vercel blob create-store … --access private --region fra1 --yes`.
6. **Email (Resend) and DNS.** Domain in the EU region through the API, records added with `vercel dns add`, verify, narrow the key, test against the sink, remove a half-installed marketplace integration.
7. **Variables.** Secrets on stdin with `--sensitive --force` for production, preview and development; config values without; `vercel env pull .env.local`; app URLs differ by environment.
8. **Register and write down.** `data_residency.py add` one row per service; `docs/infrastructure.md` with what exists, where, how, the open risks and the lessons (names and ids only, no values).
9. **Hand over.** Git link and domain assignment wait for the first deploy: say so, and name what is still the user's call.

## Not covered
Code that uses these services (`module-add db | email | storage | deploy`), the deploy itself (`vercel-deploy`), the cost gate (`vercel-doctor`), and legal sign-off on processors and transfer bases (`compliance-audit`, a DPO). Stripe, Supabase and other connectors follow the same rules but are not worked out here.

## Bundled
`references/provisioning.md` (commands, findings, traps), `scripts/make_issues.py` (+ test), `references/contracts.md`.
