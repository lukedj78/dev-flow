# module-add → `deploy` (Vercel project config)

Wire the **Vercel project configuration** for an existing Next.js 16 App Router scaffold: link the project, put `vercel.json` in the repo, get every env var into the right environment, pin the function region, and make monorepo builds behave.

## Scope — read this first

This module owns **the wiring**, not the shipping.

| Concern | Owner |
|---|---|
| `vercel.json` / `vercel.ts`, region choice, build settings, env-var plumbing, monorepo root directory | **this module** |
| Running the actual deploy, promotion to production, rollback, domains, post-deploy smoke | **`setup-deploy`** |
| Cost/perf gate before shipping (caching, function duration, image waste, dead code) | **`vercel-doctor`** |
| Legal/privacy gate before shipping (GDPR/AI-Act, incl. data residency) | **`compliance-audit`** |

Do not duplicate `setup-deploy` here. When the user says "deploy it", this module gets the project into a deployable shape and then **hands off**. The natural order at `feature_complete` is: `module-add deploy` (config exists) → `compliance-audit` + `vercel-doctor` (the two gates) → `setup-deploy` (ship).

> **Versions checked 2026-08**: Vercel CLI `58.4.4`. Docs: <https://vercel.com/docs/project-configuration>, <https://vercel.com/docs/environment-variables>, <https://vercel.com/docs/functions/configuring-functions/region>, <https://vercel.com/docs/monorepos>.

## Idempotency check

1. `<project-root>/vercel.json` (or `vercel.ts`) exists.
2. `<project-root>/.vercel/project.json` exists — the project is already linked.
3. `.gitignore` contains `.vercel`.
4. `meta.json#stack.deploy` is set.

If all four: tell the user it's wired, offer to re-check the env-var matrix or change the region. Don't re-link — re-linking silently repoints the directory at a different project, which is how people deploy staging code to prod.

## Prerequisites

- **At least one real route.** Deploying an empty scaffold produces a green checkmark that proves nothing. If the app has only the default page, say so and offer to run `screenshot-to-page` first.
- **`module-add ci` ideally already ran.** `vercel.json` and the CI workflow share env-var names; wiring them in opposite orders produces two drifting lists.
- **Run `deploy` last** among modules. It reads the configured stack — if `db`/`auth`/`storage` land afterwards, their env vars are missing from the matrix you just built.
- The Vercel CLI, invoked without a global install: `pnpm dlx vercel@latest <cmd>` (or `npx vercel`). A global `npm i -g vercel` also works; don't add `vercel` to the project's dependencies.

## Step 1 — Link the project

```bash
cd <project-root>
pnpm dlx vercel@latest link
```

Interactive: pick scope (team), then an existing project or create one. Non-interactive: `vercel link --yes --project <name>`. `--project` also reads from `VERCEL_PROJECT_ID`; the flag wins.

This writes `.vercel/project.json` (project id + org id). **Add `.vercel` to `.gitignore`** — it is machine-local link state, not shared config. Verify:

```bash
grep -qx '.vercel' .gitignore || echo '.vercel' >> .gitignore
```

**Monorepo**: run `vercel link --repo` from the **repository root** (not the app subdirectory) to link every app to its own Vercel project in one pass. Requires the Git integration. Note the plan cap on Vercel projects connected per Git repo: 25 (Hobby) / 150 (Pro).

## Step 2 — Write `vercel.json`

Keep it minimal. Vercel auto-detects Next.js and sets the build command, output directory and install command correctly — **overriding them is how builds break**. Only write what you actually need to differ from the defaults.

### The baseline this module writes

```json
{
  "$schema": "https://openapi.vercel.sh/vercel.json",
  "framework": "nextjs",
  "regions": ["fra1"]
}
```

That's it for a single-app project. `$schema` gives editor autocomplete and validation. `framework` pins the preset so a stray detection change can't silently switch it. `regions` is the one decision that genuinely matters — see Step 3.

### What to add only when there's a reason

| Key | Add when |
|---|---|
| `functions` | one route needs a different region, memory or `maxDuration` than the rest |
| `functionFailoverRegions` | Enterprise, and you need multi-region redundancy. Must differ from `regions` |
| `headers` | security headers (CSP, HSTS) that Next's `next.config` isn't already emitting |
| `crons` | the app has scheduled jobs |
| `redirects` / `rewrites` | prefer Next's `next.config.ts` for app-level routing; use `vercel.json` only for platform-level cases |
| `installCommand` | monorepo filtered installs (see Step 5) |
| `relatedProjects` | a frontend project that must reference a sibling backend project's preview URL |
| `ignoreCommand` | the built-in "skip unaffected projects" doesn't cover your repo |

Per-function overrides look like this — the shape is worth knowing even if you don't write it now:

```json
{
  "$schema": "https://openapi.vercel.sh/vercel.json",
  "regions": ["fra1"],
  "functions": {
    "app/api/heavy-report/route.ts": { "maxDuration": 120 }
  }
}
```

A per-function `regions` **completely overrides** the project-level value for that function; it does not merge.

Every `redirect`, `rewrite` and `header` entry counts against the **2048 routes per deployment** limit. A programmatic redirect table will hit it.

There is also a `vercel.ts` variant (same properties, evaluated at build time, useful for generating config from env). **One config file per project** — you cannot have both.

## Step 3 — Region (the GDPR-relevant decision)

**Vercel Functions default to `iad1` (Washington, D.C., USA) for all new projects.** For an EU-facing product this is a finding, not a detail: `compliance-audit` **R3** (Art. 44+, international transfer / EU data residency) flags exactly this US-default residency.

EU regions:

| Code | Location |
|---|---|
| `fra1` | Frankfurt, Germany |
| `cdg1` | Paris, France |
| `dub1` | Dublin, Ireland |
| `arn1` | Stockholm, Sweden |
| `lhr1` | London, UK (post-Brexit — adequacy, not EU) |

**Pick the region closest to the database, not to the users.** Static assets are served from 126 PoPs regardless; what the region controls is where your functions execute, and a function that round-trips to a Postgres on another continent pays that latency on every query. Neon/Blob/Vercel regions should agree.

Plan caps: **Hobby = single region**, Pro = 5, Enterprise = all. *"Deploying to more regions than your plan allows causes the deployment to fail before the build step."*

Set it in `vercel.json` (`"regions": ["fra1"]`), in the dashboard (**Settings → Functions → Function Regions**), or per-deploy with `vercel --regions fra1`. `vercel.json` is what this module writes — it's the version-controlled one.

**Record the choice.** When the region is EU, set `meta.json#compliance.data_residency = "eu"`; `compliance-audit` reads it and R3 stops being an open finding. Routing Middleware is deployed to all regions regardless of this setting — mention it if the middleware touches personal data.

## Step 4 — Environment variables per environment

Vercel has three system environments — **Production**, **Preview**, **Development** — plus optional custom environments. A variable is scoped to one or more of them.

- **Production**: applied to the next production deployment (push to the production branch, or `vercel --prod`).
- **Preview**: applied to deployments from any non-production branch. Can be scoped to **a specific branch**, and a branch-specific value **overrides** the general preview value of the same name — so you don't have to duplicate the whole set per branch.
- **Development**: what `vercel dev` uses and what `vercel env pull` downloads into a local `.env` file.

### The wiring this module does

1. Read `<project-root>/.env.local.example` — it is the canonical list, written by every other module (`db` → `DATABASE_URL`, `auth` → `BETTER_AUTH_SECRET`, `email` → `RESEND_API_KEY`, `storage` → `BLOB_READ_WRITE_TOKEN`…).
2. For each var, decide the environment matrix and **tell the user** which ones must differ per environment rather than being copied:
   - **Must differ**: `DATABASE_URL` (never point preview at the production DB), `BETTER_AUTH_URL` / `NEXT_PUBLIC_APP_URL`, any webhook secret (Stripe test vs live), `RESEND_DEV_TO` (set in preview/dev, empty in production).
   - **Can be shared**: read-only third-party keys, feature flags.
3. Emit the commands — **do not run them**; they take secret values interactively and the user owns their credentials:
   ```bash
   pnpm dlx vercel@latest env add DATABASE_URL production
   pnpm dlx vercel@latest env add DATABASE_URL preview
   pnpm dlx vercel@latest env add DATABASE_URL development
   pnpm dlx vercel@latest env ls
   ```
   Per-branch: `vercel env add <name> preview <gitbranch>`. From a file: `vercel env add <name> production < ./secret.txt`. Update in place: `vercel env update <name> <environment>`.
4. Tell them to pull locally: `pnpm dlx vercel@latest env pull` (writes `.env` from the **Development** environment; `--environment=preview` for preview values). If they use `vercel build` / `vercel dev`, `vercel pull` is the right command instead — it also fetches project settings into `.vercel/`.

**Sensitive by default**: `vercel env add` now defaults to `sensitive` for production, preview and custom environments — those values cannot be read back in the dashboard or via `vercel env ls`. Development stays `encrypted` (the API disallows sensitive there). `--no-sensitive` opts out unless team policy forbids it. Tell the user: **write the value down before adding it**, because they will not get it back.

Limits worth stating: **1000 variables per environment per project**, and **64 KB total** per deployment (also the max size of any single variable; 5 KB per variable for the `edge` runtime).

### System environment variables (use these instead of hardcoding URLs)

Enable **Settings → Environment Variables → "Enable access to System Environment Variables"**. Then:

- `VERCEL_ENV` — `production` | `preview` | `development`. The correct branch condition; do **not** use `NODE_ENV` (it's `production` in preview builds too).
- `VERCEL_URL` — this deployment's `*.vercel.app` domain, no scheme. Unstable per deployment.
- `VERCEL_PROJECT_PRODUCTION_URL` — the project's production domain, **always set even in preview**. This is the one to use for OG-image URLs, canonical links and anything that must point at production.
- `VERCEL_BRANCH_URL` — the `*-git-*.vercel.app` branch domain.
- `VERCEL_GIT_COMMIT_SHA`, `VERCEL_GIT_COMMIT_REF`, `VERCEL_REGION`, `VERCEL_DEPLOYMENT_ID` (Skew Protection), `VERCEL_OIDC_TOKEN` (Secure Backend Access — also how `@vercel/blob` authenticates).

Concretely, prefer:

```typescript
export const appUrl =
  process.env.NEXT_PUBLIC_APP_URL ??
  (process.env.VERCEL_PROJECT_PRODUCTION_URL
    ? `https://${process.env.VERCEL_PROJECT_PRODUCTION_URL}`
    : "http://localhost:3000");
```

over a hardcoded domain that breaks on every preview.

## Step 5 — Monorepo / turborepo

If `meta.json#stack.framework === "monorepo"`, the web app lives at `apps/web/`.

- **Root Directory** (project **Settings → Build and Deployment → Root Directory**) must be set to `apps/web`. Consequence: *"Your app will not be able to access files outside of that directory. You also cannot use `..` to move up a level."* Shared packages must be real workspace dependencies, not relative imports upward.
- With Root Directory set, the CLI is also scoped — run plain `vercel`, not `vercel apps/web`.
- **Skipping unaffected projects** is automatic when the repo qualifies: GitHub-connected, npm/yarn/pnpm/bun workspaces, every package has a unique `name`, and inter-package dependencies are declared in each `package.json`. If those hold, a commit touching only `apps/mobile` will not rebuild `apps/web` — and unlike Ignored Build Step it doesn't burn a concurrent build slot. Toggle under Root Directory → **Skip deployment**.
- If the repo doesn't qualify (mixed languages, unusual layout), fall back to the **Ignored Build Step** / `ignoreCommand`. For Turborepo, `turbo query` in the Ignored Build Step gives more precise selection.
- **Filtered installs**: set a custom Install Command in the app's `vercel.json` so only that app's workspace deps install. Faster builds, and it surfaces missing dependency declarations early.
- **`vercel.json` lives in the app directory** (`apps/web/vercel.json`), alongside the Root Directory — not at the repo root.
- **Cross-project references**: `"relatedProjects": ["prj_..."]` in the app's `vercel.json` makes sibling projects' preview + production hosts available via `VERCEL_RELATED_PROJECTS`, read with `@vercel/related-projects`. Max 3, same repo, **CLI deployments not supported**. This is the right answer to "how does the preview frontend find the preview backend" — better than hardcoding a URL per environment. Under Turborepo Strict Mode, add `VERCEL_RELATED_PROJECTS` to `turbo.json`.

## Step 6 — Preview deployments

Nothing to configure in code — every push to a non-production branch produces a preview URL, and pull requests get a comment with the URLs of all connected projects. What this module does is make previews *correct*:

- Confirm every var the app reads is present in the **Preview** environment, not only Production. A missing preview var is the single most common cause of "it works locally and in prod but the PR preview 500s".
- Point preview at non-production data — a branch/dev database, Stripe test keys, `RESEND_DEV_TO` set so mail doesn't reach real users.
- Mention **Deployment Protection** if previews would expose unreleased work. Note that `VERCEL_URL` *"cannot be used in conjunction with Standard Deployment Protection"*.

## Verification

```bash
pnpm build                                   # the same build Vercel will run
pnpm dlx vercel@latest env ls                # every expected var, in every expected environment
pnpm dlx vercel@latest build                 # optional: reproduce the platform build locally
```

Do **not** run `vercel deploy` from this module — deploying is `setup-deploy`'s job, and a surprise production deploy is not a verification step. Also check `.vercel/` is gitignored and `vercel.json` parses (`$schema` gives you this in-editor).

## Update meta.json

```json
{
  "stack": {
    "deploy": "vercel"
  }
}
```

Phase: `module_added` (monotonic — never bump toward `deployed` here; only `setup-deploy` earns that).

## Hand-off message

Tell the user, concretely:

1. Files written: `vercel.json`, `.gitignore` entry.
2. The env-var matrix: which vars go to which environments, and **which must differ** between production and preview.
3. The region chosen and why — and if it's US-default, that `compliance-audit` R3 will flag it.
4. The two gates to run before shipping: **`vercel-doctor`** (cost/perf) and **`compliance-audit`** (GDPR/AI-Act).
5. Then `setup-deploy` to actually ship.

## Known caveats

- **Don't override the Build/Install/Output commands for Next.js.** Vercel detects them. Every custom `buildCommand` this repo has seen in the wild was working around a problem better fixed elsewhere.
- **`NODE_ENV` is `production` in preview builds.** Branch on `VERCEL_ENV`. Getting this wrong is how test emails reach customers and how analytics counts preview traffic.
- **Hobby plan realities**: single function region, 1 concurrent build, 100 deployments/day, runtime logs kept 1 hour, and Vercel does **not** support connecting a Hobby project to a Git-organization repository. Included usage on Hobby: 100 GB Fast Data Transfer, 1M function invocations, 4 CPU-hrs Active CPU per month.
- **Sensitive env vars are write-only.** Once added, the value cannot be read back — rotation, not recovery, is the fix.
- **Env-var changes don't retroactively apply.** *"Any change you make to environment variables are not applied to previous deployments, they only apply to new deployments."* Changing a var requires a redeploy to take effect.
- **`vercel.json` and `vercel.ts` are mutually exclusive.** One config file per project.
- **Edge runtime is not free lunch.** `export const runtime = "edge"` cuts cold starts but breaks anything using `node:` builtins, native modules, or a Node-only DB driver. `@neondatabase/serverless` works over HTTP; a raw `pg` pool does not belong on edge. Also: 5 KB per env var on edge instead of 64 KB total.
- **Build time cap is 45 minutes**, and the deployment source upload cap is 100 MB (Hobby) / 1 GB (Pro), max 15,000 source files.

## Alternative deploy targets

Fly.io (containers, colocated Postgres), Cloudflare Pages/Workers (edge-first), Render, Railway. Each is a **separate variant** — implement one only when a user asks, copying this file's structure. They are not drop-in: Next.js on Vercel gets ISR, Image Optimization, Skew Protection and the Fluid compute model that the rest of dev-flow (`data-fetching`, `vercel-doctor`) assumes. Moving off Vercel is a stack decision, not a config flag — treat it as a contract change and say so.
