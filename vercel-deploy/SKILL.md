---
name: vercel-deploy
description: 'Use to ship a Next.js 16 App Router project to production on Vercel end-to-end: verify the pre-deploy gates ran, reproduce the platform build locally, deploy a preview and smoke-test it, create a *staged* production deployment (`vercel --prod --skip-domain`) that serves no traffic yet, promote it to Current (`vercel promote`), attach and verify the custom domains + DNS, and hand the user a rollback runbook. Reads `.workflow/meta.json` — requires `stack.framework` in {`next`, `monorepo`} and `phase >= feature_complete`. Sets `stack.deploy = "vercel"` and `phase = "deployed"` on success. Idempotent: re-running detects what already shipped and skips it. Triggers on: "deploy", "ship it", "go live", "push to production", "manda in produzione", "attacca il dominio", "rollback the deploy". Not for: writing the Vercel project config — `vercel.json`, region, env-var matrix, monorepo root directory are `module-add deploy` (run it first); the three pre-deploy gates — cost/perf (`vercel-doctor`), legal/privacy (`compliance-audit`), UI quality + a11y (`shadscan`); GitHub Actions and git hooks (`module-add ci`); shipping an Expo/RN app (`rn-eas-deploy`); shipping an eve agent (`eve deploy`).'
---

# vercel-deploy — ship the web app to production on Vercel

The web counterpart of `rn-eas-deploy`. It is the **only** skill that moves a web project to `phase = "deployed"`.

> **Versions checked 2026-08-04**: Vercel CLI `58.5.1`. Docs: <https://vercel.com/docs/cli/deploy>, <https://vercel.com/docs/cli/deploying-from-cli>, <https://vercel.com/docs/cli/promote>, <https://vercel.com/docs/cli/rollback>, <https://vercel.com/docs/deployments/promoting-a-deployment>, <https://vercel.com/docs/instant-rollback>, <https://vercel.com/docs/git>, <https://vercel.com/docs/domains/working-with-domains/add-a-domain>.

## Scope — read this first

This skill **ships**. It does not configure.

| Concern | Owner |
|---|---|
| `vercel.json`, function region, env-var matrix per environment, monorepo Root Directory, project linking | **`module-add deploy`** — run it first |
| husky, lint-staged, GitHub Actions | **`module-add ci`** |
| cost/perf gate before shipping | **`vercel-doctor`** |
| legal/privacy gate before shipping | **`compliance-audit`** |
| UI-quality / accessibility gate before shipping | **`shadscan`** |
| preview → smoke → staged production → promote, domains + DNS, rollback, `phase = "deployed"` | **this skill** |

If `vercel.json` or `.vercel/project.json` is missing, do not improvise them here — say so and route to `module-add deploy`. Two skills writing the same config is how the region silently changes between runs.

## Contract

See `references/contracts.md`. Key facts:
- Reads `<project-root>/.workflow/meta.json#stack.framework` — must be `"next"` or `"monorepo"`.
- Requires `meta.json#phase >= "feature_complete"`.
- Sets `meta.json#stack.deploy = "vercel"` and `phase = "deployed"` **only after** the production domain actually serves the deployment.
- Records `stack_config.production_url` + `stack_config.vercel_project` and appends `history`.
- Idempotent: re-running on an already-deployed project becomes a *release* run (deploy → promote), and skips domain setup that is already verified.

## When this skill applies

- Phase is `feature_complete` (or `deployed`, for subsequent releases).
- The user says: "deploy", "ship it", "go live", "manda in produzione".
- The orchestrator routes here from `dev-flow`.

## Monorepo awareness

If `meta.json#stack.framework === "monorepo"`, the web app lives at `apps/web/` and the Vercel project's **Root Directory** is already set to `apps/web` by `module-add deploy`. Consequence: **run the CLI from the repository root**, not from `apps/web/` — with Root Directory configured the CLI is already scoped. `vercel.json` stays in `apps/web/`.

The mobile side ships separately via `rn-eas-deploy`, the agent side via `eve deploy`. All three can be at different points; `phase = "deployed"` for the project means every side that exists has shipped — say which sides remain.

---

## Workflow

### Step 1 — Preconditions

Read `.workflow/meta.json`. Abort with a specific message if:

- `stack.framework === "expo-rn"` → this is `rn-eas-deploy`'s job.
- `stack.framework` is neither `next` nor `monorepo` → refuse; alternative deploy targets are a stack decision, not a flag (see `module-add/references/module-deploy.md` § *Alternative deploy targets*).
- `phase < "feature_complete"` → the build isn't done; say which phase it is and what closes the gap.
- `stack.deploy !== "vercel"` or `<project-root>/.vercel/project.json` is missing → run `module-add deploy` first.

Then confirm the CLI can see the project:

```bash
pnpm dlx vercel@latest whoami            # who the CLI is logged in as
pnpm dlx vercel@latest project inspect   # details of the *linked* project
```

Never `vercel link` from this skill. Re-linking silently repoints the directory at a different project — that is how staging code reaches production.

### Step 2 — Confirm the three gates ran (propose, never block)

Read `meta.json#compliance` (legal), `meta.json#vercel_doctor` (cost/perf) and `meta.json#shadscan` (UI quality + a11y).

- Missing → tell the user which gate has never run and offer to run it now.
- Present but older than the last material change (compare against `history`) → offer a re-run.
- Present and current → state the findings summary in one line and move on.

No gate blocks a deploy. Report and let the user decide — that is the existing policy for all three, and this skill does not tighten it.

### Step 3 — Reproduce the platform build locally

```bash
pnpm build                                   # the same build Vercel will run
pnpm dlx vercel@latest env ls                # every expected var, in every expected environment
```

Two things to actually check in the `env ls` output, not just print:

- Every var the app reads exists in **Preview**, not only Production. A missing preview var is the single most common cause of "works locally and in prod, PR preview 500s".
- Vars that must differ per environment actually differ — `DATABASE_URL` above all. See `references/deploy-checklist.md`.

If `pnpm build` fails, stop. Do not deploy a build you could not reproduce.

### Step 4 — First deploy or subsequent release?

```bash
pnpm dlx vercel@latest ls --prod
```

This decides the path, and the difference is documented behaviour, not a preference:

> *"The first deployment of a new project is always a production deployment, even when you run `vercel` without `--prod`."*

- **No production deployment yet → path A (first deploy).** There is no way to make the first deployment a preview. Tell the user plainly: the first deploy goes to production, so smoke-testing happens *after* it exists and *before* the custom domain points at it. Attach domains in Step 9, after the deployment is verified — a `*.vercel.app` URL nobody knows is a safe place to be wrong.
- **A production deployment exists → path B (release).** Steps 5–8 in full.

### Step 5 — Preview deploy + smoke test (path B only)

```bash
pnpm dlx vercel@latest deploy
```

`stdout` is always the deployment URL — capture it. Then smoke-test the actual flows the release touches (auth, the changed route, one write path), not just "the homepage 200s".

If the project has **Deployment Protection** enabled — Standard Protection is the Hobby default and protects preview URLs — the URL asks for a Vercel login before it renders. That is expected; log in rather than "fixing" it. Note that with Standard Protection the generated production URL is restricted too, so anything reading `VERCEL_URL` / `NEXT_PUBLIC_VERCEL_URL` for a fetch must target the requested domain instead.

Do not proceed until the user confirms the preview is good.

### Step 6 — Staged production deployment

```bash
pnpm dlx vercel@latest deploy --prod --skip-domain
```

This creates a **production** deployment — real production env vars, real production build — that is **not** assigned to the custom domains. Production traffic keeps going to the current deployment.

`--skip-domain` must be used with `--prod`, and it overrides the project's **Auto-assign Custom Production Domains** setting for this deployment.

This is the safe shape and the one the docs point at: `vercel alias` explicitly is *not* the recommended way to put a deployment on a production domain — `--prod --skip-domain` → `promote` → `rollback` is.

### Step 7 — Smoke-test the staged deployment

The staged URL runs with production environment variables against production data. Re-check the same flows as Step 5, plus anything that behaves differently in production: payment webhooks against live keys, transactional email, anything branching on `VERCEL_ENV === "production"`.

This is the last cheap moment. After Step 8 the fix is a rollback.

### Step 8 — Promote to Current

```bash
pnpm dlx vercel@latest promote <staged-deployment-url>
```

The promotion assigns the production domains **without a rebuild**. Default timeout is `3m`; `--timeout=0` returns immediately and lets it finish server-side.

Verify it took:

```bash
pnpm dlx vercel@latest promote status
pnpm dlx vercel@latest ls --prod
```

A deployment that has been promoted once **cannot be promoted again** — to go back to it later you roll back, not promote.

### Step 9 — Custom domains (idempotent)

Skip entirely if `vercel domains verify` already reports the project's domains as configured.

Otherwise follow `references/domains-dns.md`. The short version:

```bash
pnpm dlx vercel@latest domains add <domain> <project>
pnpm dlx vercel@latest domains verify <domain> --project <project> --format=json
```

The DNS records themselves are added at the registrar, by the user — this skill reads the required records out of `domains verify` / the dashboard and hands them over. It never invents record values: the apex is an **A** record and each subdomain has a **project-specific CNAME target**, so a hardcoded `*.vercel-dns-*.com` value is always wrong for someone.

Vercel recommends `www` as the primary domain with a redirect from the apex, because the DNS spec forbids CNAME on an apex and a CNAME gives the CDN more control over incoming traffic. Say so, then do what the user decides — an apex-primary setup with an A record is explicitly supported.

Once a domain is configured it is **automatically applied to the latest production deployment**.

### Step 10 — Post-deploy verification + rollback runbook

```bash
curl -sS -o /dev/null -w '%{http_code}\n' https://<production-domain>/
pnpm dlx vercel@latest inspect <deployment-url>
```

Then hand the user the rollback runbook from `references/rollback-runbook.md` — in the message, not just as a file path. The single fact that must be said out loud:

> After a rollback, Vercel turns **off** auto-assignment of production domains. Pushes to the production branch stop going live until you `vercel promote` a deployment.

Someone who rolls back at 2am without knowing that spends the next hour wondering why their fix isn't deploying.

### Step 11 — Update meta.json + commit

```json
{
  "stack": { "deploy": "vercel" },
  "stack_config": {
    "vercel_project": "<project-name>",
    "production_url": "https://<production-domain>",
    "production_region": "<fra1|iad1|…>"
  },
  "phase": "deployed",
  "history": [
    { "skill": "vercel-deploy", "ran_at": "<iso>", "deployment": "<url>", "domains": ["…"] }
  ]
}
```

Set `phase = "deployed"` **only after Step 10 confirms the production domain serves the new deployment**. A promote that timed out client-side is not a deploy.

Commit: `release: deploy <version> to production on Vercel`.

### Step 12 — Print the next-steps summary

- Production URL, and the deployment id now serving it.
- Which gates ran, and any finding the user chose to ship with.
- The rollback command, verbatim.
- For a monorepo: which sides have shipped and which have not (`rn-eas-deploy` for mobile, `eve deploy` for the agent).
- The maintenance loop: re-run `compliance-audit` + `vercel-doctor` + `shadscan` after material changes.

---

## Common anti-patterns (NEVER do)

- ❌ `vercel --prod` straight at a project that already serves traffic. Stage it, smoke it, promote it.
- ❌ `vercel alias` to put a deployment on the production domain. The docs name `promote`/`rollback` as the preferred production commands.
- ❌ `--prebuilt` for a Next.js app whose build reads System Environment Variables — they are missing at build time with that flag.
- ❌ `vercel link` from this skill. Linking belongs to `module-add deploy`.
- ❌ `phase = "deployed"` before the production domain actually serves the deployment.
- ❌ Assuming a rollback restores environment variables. It does not rebuild: env vars and cron jobs revert to the state of the rolled-back deployment.
- ❌ Leaving a project in a rolled-back state without telling the user that pushes to the production branch no longer go live.
- ❌ Hardcoding a `*.vercel-dns-*.com` CNAME target. It is per project.
- ❌ Deploying an app whose only route is the scaffold's default page. A green checkmark on an empty app proves nothing.

## References

- `references/deploy-checklist.md` — the pre-flight list: gates, build, env-var matrix, first-deploy vs release.
- `references/domains-dns.md` — apex vs `www`, A/CNAME records, verification, redirects, when `alias` is still right.
- `references/rollback-runbook.md` — instant rollback, plan limits, the auto-assign trap, undoing a rollback.
- `module-add/references/module-deploy.md` — the configuration this skill assumes exists.

## Updating meta.json (recommended pattern)

When this skill modifies state (artifact written, phase advanced, history appended), use the canonical script when available:

```bash
# Wherever dev-flow is installed (e.g. ~/.claude/skills/dev-flow/), invoke:
python3 .../dev-flow/scripts/update_meta.py <project-root> set-phase deployed
python3 .../dev-flow/scripts/update_meta.py <project-root> append-history \
    --skill 'vercel-deploy' --inputs '{...}' --outputs '{...}' --phase-after deployed
```

The script enforces phase monotonicity, normalizes legacy kebab-case aliases, and writes the canonical sha256 + timestamp into `meta.json#artifacts`. **Fall back to direct JSON editing only if the script is not on PATH** (and warn the user).

## Sources

- Vercel CLI: <https://vercel.com/docs/cli/deploy>, <https://vercel.com/docs/cli/deploying-from-cli>, <https://vercel.com/docs/cli/promote>, <https://vercel.com/docs/cli/rollback>, <https://vercel.com/docs/cli/alias>, <https://vercel.com/docs/cli/domains>, <https://vercel.com/docs/cli/list>, <https://vercel.com/docs/cli/inspect>
- Platform: <https://vercel.com/docs/deployments/promoting-a-deployment>, <https://vercel.com/docs/instant-rollback>, <https://vercel.com/docs/git>, <https://vercel.com/docs/deployment-protection>
- Domains: <https://vercel.com/docs/domains/working-with-domains/add-a-domain>, <https://vercel.com/docs/domains/working-with-domains/deploying-and-redirecting>
