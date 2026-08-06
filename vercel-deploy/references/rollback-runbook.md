# vercel-deploy → rollback runbook

Hand this to the user at the end of every deploy. It is written to be read at 2am by someone who did not run the deploy.

> **Versions checked 2026-08-04**: Vercel CLI `58.5.1`. Docs: <https://vercel.com/docs/instant-rollback>, <https://vercel.com/docs/cli/rollback>, <https://vercel.com/docs/cli/promote>, <https://vercel.com/docs/deployments/promoting-a-deployment>.

## Roll back now

```bash
pnpm dlx vercel@latest rollback <deployment-id-or-url>
pnpm dlx vercel@latest rollback status
```

It is instantaneous: Vercel points the domains back at an existing deployment. **No rebuild happens.**

`--timeout` only controls how long the CLI waits; the rollback proceeds regardless. `--timeout 0` returns immediately.

Dashboard equivalent: project overview → **Instant Rollback** on the Production Deployment tile, or the ⋮ menu on any row in **Deployments**.

## The trap — read this before you roll back

**After a rollback, Vercel turns off auto-assignment of production domains.** New pushes to the production branch will build, go green, and **not go live**. The site keeps serving the rolled-back deployment.

This is deliberate — it stops the bad deployment from immediately re-winning — but it is the single most confusing part of the flow. Someone pushing a hotfix and watching it "deploy successfully" with no effect is in this state.

**Undo it by promoting a deployment:**

```bash
pnpm dlx vercel@latest promote <deployment-id-or-url>
```

That promotes the deployment *and* re-enables auto-assignment of production domains. Dashboard equivalent: **Undo Rollback** on the production deployment tile.

## What a rollback does *not* restore

Because there is no rebuild, the rolled-back deployment comes back exactly as it was built:

- **Environment variables are not re-applied.** Changing a var in project settings and rolling back does not combine into "old code, new secrets". The deployment keeps the values it was built and deployed with.
- **Cron jobs revert** to the state of the rolled-back deployment.
- **Configuration may be stale** in general — treat the whole deployment as a snapshot, not as "current code minus one commit".
- **Custom aliases set with `vercel alias` are not included**, because they are not part of the project's domain settings. They come back only if they were on the previous production deployment.
- **External state does not roll back.** A database migration that ran during the bad deploy is still applied. If the release included a destructive migration, a rollback restores the code and leaves the schema — decide that before you press it.

## What you can roll back to

| Plan | Eligible targets |
|---|---|
| **Hobby** | the immediately previous production deployment, only |
| **Pro / Enterprise** | any deployment previously aliased to a production domain |

Passing an older id on Hobby fails with: `To roll back further than the previous production deployment, upgrade to pro`.

**Only deployments that have served production are eligible.** A preview deployment that was never promoted cannot be rolled back to — promote it instead (which does a full rebuild, and asks for confirmation because it is a preview; `--yes` skips the prompt).

Who can do it: on Pro/Enterprise, Owners, Members and Developers; also any Project Administrator, or anyone holding the **Full Production Deployment** permission on an access group.

## Deployment states, so the dashboard makes sense

- **Staged** — built for production, no domain assigned. Created by `vercel --prod --skip-domain`, or by a push to the production branch while *Auto-assign Custom Production Domains* is off. Can be promoted.
- **Promoted** — was staged, then promoted. **A deployment can only be promoted once.** To return to it later, roll back to it.
- **Current** — the deployment the production domains actually serve.

## Decision order during an incident

1. **Is it the deployment?** `vercel logs --environment production --status-code 5xx --since 15m`. If the errors predate the deploy, rolling back will not help and will cost you the fix.
2. **Did the release include a migration or an external side effect?** If yes, decide what the rollback leaves behind *before* running it.
3. **Roll back.** `vercel rollback <previous-production-url>`.
4. **Say it out loud, in the channel**: production is on a rolled-back deployment, and pushes to the production branch are not going live until someone promotes.
5. **Fix forward**, then `vercel promote <fixed-deployment-url>` — which both ships the fix and restores normal behaviour.
6. **Record it**: append to `meta.json#history` what shipped, what broke, and what was rolled back to. The next person deploying this project reads that file.

## Useful while diagnosing

```bash
pnpm dlx vercel@latest ls --prod                      # what has served production
pnpm dlx vercel@latest inspect <url>                  # deployment metadata
pnpm dlx vercel@latest inspect <url> --logs           # build logs
pnpm dlx vercel@latest logs --level error --since 1h  # request logs (default window: 24h)
pnpm dlx vercel@latest logs --follow                  # live stream, up to 5 minutes
```

Runtime logs are kept **1 hour** on Hobby — on that plan, capture before you fix, or the evidence is gone.
