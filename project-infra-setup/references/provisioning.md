# Provisioning with the Vercel CLI (verified 2026-10-03, CLI 60.1.3)

The user is logged in; check with `vercel whoami`, `vercel teams ls`, `vercel domains ls`. Run every command with `--cwd <project>` or from the project folder: the user's own terminal may start elsewhere ("Your codebase isn't linked").

## Decide before creating
- **Plan.** Vercel's fair-use terms restrict **Hobby to non-commercial personal use** and define commercial as any deployment serving the financial gain of anyone involved, a paid consultant writing the code included. A company tool is arguably commercial. It is the user's call; record it as a known risk to revisit when the prototype becomes real use. Hobby functions run at most 300 s (Pro 800 s).
- **Regions.** The default is **US (`iad1`)** for functions, Blob and Neon. Choose the EU region first and verify after.

## GitHub repository
```bash
gh repo create <owner>/<name> --private --description "…" --source . --remote origin --push
```
Initial commit by file name (never `git add -A`: other files may sit in the tree). **Scan the staged diff for secrets first**: key-looking assignments, `eyJ…`, `sk-`, `re_`, `npg_`, `ghp_`, `xox`; and check `git ls-files` shows no `.env`, `.env.local` or `.vercel`. `.gitignore` needs `.env*` **and** `!.env.example`, or the example is ignored. Optional, when the tracker is GitHub: `python3 scripts/make_issues.py --repo <owner>/<name> --tasks .workflow/tasks.md --map .workflow/github-issues.json` (one issue per task, resumable, 2 s apart, labels by area and type), then verify the totals from GitHub itself.

## Project
```bash
vercel project add <name>
vercel link --yes --project <name>      # writes .vercel/ and .env.local (OIDC token); adds both to .gitignore
```
Function region: `PATCH /v9/projects/<id>` with `{"resourceConfig":{"functionDefaultRegions":["fra1"]}}` via `vercel api … --input file`, then **read it back with `vercel api /v9/projects/<id>`** (`vercel project inspect` keeps showing `iad1`).
**Do not connect Git yet** (`vercel git connect`): the first push would publish the repo's documents at a public `*.vercel.app` URL. Connect when the app exists. Do not assign the custom domain before the first deploy.

## Postgres: Neon through the marketplace
```bash
vercel integration add neon --name <db> -m region=fra1 -m auth=false
```
- Metadata keys are not in `--help`. They are in `vercel api /v1/integrations/configuration/<icfg_id>/products` (`metadataSchema`). For Neon: `region` (Vercel region codes) and `auth` (**Neon Auth is on by default**: turn it off if the stack uses its own auth).
- **The region cannot be changed afterwards.** Omitting `-m region=` put the first database in Virginia. Fix: `vercel integration resource remove <db> --disconnect-all --yes`, recreate, and **verify** from `PGHOST` in `.env.local` (`…eu-central-1.aws.neon.tech`). Never print credentials.
- After removing a resource, delete its leftover variables from `.env.local`.
- The install adds `neondatabase/agent-skills` into the repo (`.agents/`, `.claude/skills/`, `skills-lock.json`), **every time**. Move them out of the repo and decide (see SKILL.md rule 3). Free plan: 1 GB per project; vector embeddings can fill it.
- A first-time marketplace integration returns `userActionRequired` with a `verification_uri`: a human accepts the terms in the browser. Neon needed no step because the team already had it.

## Files: Blob
```bash
vercel blob create-store <name> --access private --region fra1 --yes
```
Without `--yes` the CLI returns `confirmation_required` as JSON. It links the store and writes `BLOB_READ_WRITE_TOKEN`.

## Email: Resend
- **The marketplace route collided with an account the user already had** (their zone already held Resend records for another subdomain) and stalled in the browser. Prefer the existing account.
- The user creates a **Full access** key at resend.com and stores it themselves: `vercel env add RESEND_API_KEY --cwd <project>` (value hidden; choose all environments). Never in chat.
- Pull it (`vercel env pull .env.local --yes`) and call the API from a script that never prints it: `POST /domains {"name":"app.example.com","region":"eu-west-1"}` → records. Free plan: 3 domains.
- Records Resend returned for a sub-domain `app.example.com` of a zone `example.com`: TXT `resend._domainkey.app` (DKIM), MX `send.app` priority 10, TXT `send.app` (SPF), CNAME `rsend.app`. All on technical names, so they do not touch the site. Add each with `vercel dns add <zone> <name> <TYPE> <value> [priority]`, from a script (TXT values contain spaces and `=`). Works because the zone uses Vercel's nameservers.
- Verify: `POST /domains/<id>/verify`, then poll `GET /domains/<id>`; it took about 90 s.
- **Narrow the key**: `POST /api-keys {"name":"…-send","permission":"sending_access","domain_id":"<id>"}`; test it with a send to `delivered@resend.dev` (Resend's sink, never delivered to a real inbox); replace the variable in every environment (value on stdin, `--sensitive --force`); only then `DELETE /api-keys/<old id>`.
- Remove a half-installed marketplace integration with `vercel integration remove resend --yes` once it has no resources.

## Variables
```bash
printf '%s\n' "$VALUE" | vercel env add NAME production --sensitive --force   # same for preview, development
vercel env pull .env.local --yes
```
Generate secrets locally (`secrets.token_bytes(32)`) and pass them on stdin, never in arguments or chat. Config (non-secret) values use `--no-sensitive`. App URLs: production at the real domain, development at `http://localhost:3000`, preview left to Vercel.

## Record it
`data_residency.py add` one row per service (region, transfer basis, DPA "to verify"); `render`. Services without a known EU region are flagged, not blocked. Write `docs/infrastructure.md` (what, where, how, open risks, lessons): names and ids only, no values.
