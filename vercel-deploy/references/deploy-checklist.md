# vercel-deploy → pre-flight checklist

Everything to verify **before** the first `vercel deploy` of a run. Work down the list; each item states what to check, not just what to run.

> **Versions checked 2026-08-04**: Vercel CLI `58.5.1`. Docs: <https://vercel.com/docs/cli/deploying-from-cli>, <https://vercel.com/docs/cli/list>, <https://vercel.com/docs/environment-variables>, <https://vercel.com/docs/deployment-protection>, <https://vercel.com/docs/skew-protection>.

## 1. The project is configured, not just scaffolded

| Check | Command / file | Why it blocks |
|---|---|---|
| project linked | `.vercel/project.json` exists | without it the CLI would offer to create a *new* project mid-deploy |
| `.vercel` gitignored | `grep -qx '.vercel' .gitignore` | it is machine-local link state; committing it repoints other people's CLI |
| config present | `vercel.json` (or `vercel.ts`, never both) | region and framework preset are pinned there |
| deploy module ran | `meta.json#stack.deploy === "vercel"` | otherwise the env matrix was never built |
| at least one real route | the app is not just the scaffold's default page | a green checkmark on an empty app proves nothing |

Any miss → `module-add deploy`, not an improvised fix here.

## 2. The three gates

| Gate | meta.json key | What "stale" means |
|---|---|---|
| `compliance-audit` | `meta.json#compliance` | ran before the last module that touched personal data (auth, db, email, storage) |
| `vercel-doctor` | `meta.json#vercel_doctor` | ran before the last material change to routes, caching or images |
| `shadscan` | `meta.json#shadscan` | ran before the last material change to components, forms or motion |

Report the state, offer the re-run, **do not block**. If the user ships with an open finding, name the finding in the final summary so it is on the record.

The one finding worth restating out loud at deploy time is **R3 (EU data residency)**: Vercel Functions default to `iad1` (Washington, D.C.). If `vercel.json#regions` is a US region and the product is EU-facing, this is the last moment before it becomes a production fact.

## 3. The build you are about to ship

```bash
pnpm build
```

Run the *project's* build, the same one Vercel runs. If it fails locally it will fail on the platform — with a slower feedback loop and a burnt deployment.

Optional, when you want the platform's exact build output:

```bash
pnpm dlx vercel@latest build
```

Do **not** follow it with `vercel deploy --prebuilt` for a Next.js app unless you know the build reads no System Environment Variables — with `--prebuilt` they are missing at build time. Prebuilt deploys also need a custom deployment ID for Skew Protection to keep working, because the build-time id must match the one Vercel assigns at deploy time.

## 4. The environment-variable matrix

```bash
pnpm dlx vercel@latest env ls
```

Read the output against `.env.local.example`. Three failure modes, in order of how often they bite:

1. **A var exists in Production but not Preview.** The PR preview 500s while local and prod are fine. This is the most common deploy-day bug.
2. **A var is shared that must differ.** `DATABASE_URL` pointing preview at the production database is a data-loss bug waiting for someone to run a destructive test. Also: `BETTER_AUTH_URL` / `NEXT_PUBLIC_APP_URL`, Stripe webhook secrets (test vs live), `RESEND_DEV_TO`.
3. **A var changed but nothing was redeployed.** *"Any change you make to environment variables are not applied to previous deployments, they only apply to new deployments."* Changing a value requires a redeploy to take effect.

Sensitive values (the default for production, preview and custom environments) cannot be read back — `env ls` shows the name, not the value. Verifying "is it correct" is therefore impossible from the CLI; verify **presence** here and correctness in the smoke test.

## 5. First deploy or release?

```bash
pnpm dlx vercel@latest ls --prod
```

- **Empty** → first deploy. *"The first deployment of a new project is always a production deployment, even when you run `vercel` without `--prod`."* There is no preview-first option. Plan accordingly: deploy, verify on the generated `*.vercel.app` URL, attach the custom domain afterwards.
- **Non-empty** → release. Preview → smoke → `--prod --skip-domain` → smoke → `promote`.

Useful filters while checking: `vercel ls --status READY`, `vercel ls --environment=staging`, `vercel ls -m githubCommitSha=<sha>`.

## 6. Deployment Protection, so the smoke test is not a surprise

Read the current state instead of guessing:

```bash
pnpm dlx vercel@latest project protection --format json
```

Standard Protection (Vercel Authentication) is available on every plan and protects preview and generated deployment URLs while leaving the production domain public. If it is on, a preview URL asks for a Vercel login before rendering — expected, not a bug.

Two consequences worth checking before shipping:

- Anything fetching `VERCEL_URL` / `NEXT_PUBLIC_VERCEL_URL` should target the domain the user actually requested instead; under Standard Protection the generated production URL is restricted. Client-side, a relative `fetch('/some/path')` is the fix and carries the auth cookie automatically.
- Protecting the **production** domain requires Pro or Enterprise. On Hobby, production is public — do not promise the user a private production deploy.

## 7. Skew Protection (know its state, don't change it blind)

Projects created after 19 November 2024 on a supported framework — Next.js included — have Skew Protection **on by default**; Next.js 14.1.4+ built on Vercel needs no extra configuration. It pins framework-managed requests (static assets, client navigations, Server Actions, prefetches) to the deployment that served the page, so a user mid-session does not hit a half-new server.

What it does **not** do: pin full-page navigations. A hard refresh after a deploy gets the latest production deployment, and the client triggers a reload on version mismatch. That is the intended behaviour for most apps. Long-lived sessions (exams, calls, multi-step wizards) can pin document navigations with the `__vdpl` cookie — a deliberate change, not something to enable during a deploy.

Default **Maximum Age** is one day, configurable up to the project's retention policy. Custom max age and non-production environments are Pro/Enterprise.

Toggling it from the CLI, if you must:

```bash
pnpm dlx vercel@latest project protection enable <project> --skew
pnpm dlx vercel@latest project protection enable <project> --skew --skew-max-age 604800
```

**The two numbers are both real, and they belong to different doors.** Confirmed against
`vercel@59.6.2`'s own flag definition: `--skew-max-age` is documented as *"When enabling with
`--skew`, max age in seconds for skew protection (**default 2592000, 30 days**)"* — while the Skew
Protection docs give **one day** for the dashboard. So enabling through the CLI and enabling through
the dashboard do not land on the same value, and neither page is wrong. **Read the value back rather
than assuming either**, and prefer passing `--skew-max-age` explicitly so the number is in the diff
instead of in whoever's memory enabled it.

Three more things the CLI enforces, worth knowing before an autonomous loop tries them:

- **`--skew-max-age` only works with `enable`.** With `disable` the CLI refuses outright — *"can only
  be used with `project protection enable`"* — and points at `project protection disable … --skew`.
- **The value is a positive integer of seconds**, nothing else: no `7d`, no float. The error text's own
  example is `604800`.
- **What you read back is `skewProtectionMaxAge`**, one of six protection keys the command reports
  (`passwordProtection`, `ssoProtection`, `skewProtectionMaxAge`, `customerSupportCodeVisibility`,
  `gitForkProtection`, `protectionBypass`).

`[VERIFY]` again on a CLI major — this surface gained agent-shaped errors (structured reason + a
suggested next command) recently, so it is being actively worked on.

## 8. Ready

All eight green → Step 5 of `SKILL.md` (preview) or Step 6 (staged production) depending on §5.
