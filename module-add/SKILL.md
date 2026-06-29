---
name: module-add
description: 'Wire a backend or infrastructure module (auth, database, payments, email, file storage, deploy config) into an already-scaffolded app. Reads `.workflow/meta.json#stack` for the chosen tech (better-auth, drizzle+neon, stripe, resend, vercel, etc.) and modifies the codebase at the project root to install + configure the module end-to-end. Always idempotent — running twice does not duplicate config. Use when the user says "add auth", "wire up the database", "set up Stripe", "add file uploads", "configure deploy", "module aggiungi auth", or the orchestrator routes here from phase `scaffolded` / `page_generated`. Not for: scaffolding the app (`design-md-to-app`) or building UI (`screenshot-to-page`).'
---

# module-add — wire a backend/infra module into the scaffold

This skill is the bridge between a styled-but-empty app and a functional product. Every "module" follows the same shape: install packages, generate config, write a small reference implementation (one route or one server function), update `meta.json#stack` to record the choice, and bump phase.

**Modules supported in v1**:

| Module | Default tech | Reference file | Status |
|---|---|---|---|
| `auth` | better-auth (email/password + magic link) | `references/module-auth.md` | ✅ implemented |
| `db` | Drizzle ORM + Neon Postgres | `references/module-db.md` | ✅ implemented |
| `payments` | Stripe (subscriptions + one-time) | `references/module-payments.md` | ✅ implemented |
| `email` | Resend + React Email | `references/module-email.md` | ✅ implemented |
| `test` | Vitest + Testing Library + Playwright | `references/module-test.md` | ✅ implemented |
| `ci` | husky + lint-staged + GitHub Actions | `references/module-ci.md` | ✅ implemented |
| `motion` | Motion (rebranded framer-motion) + opinionated wrappers | `references/module-motion.md` | ✅ implemented |
| `storage` | UploadThing | `references/module-stubs.md` | 🚧 planned — contributions welcome |
| `deploy` | Vercel | `references/module-stubs.md` | 🚧 planned — contributions welcome |
| `voice` | AI Gateway realtime (`@ai-sdk/gateway` + `experimental_useRealtime`) | `references/module-stubs.md` | 🚧 planned — experimental API |
| `realtime` | Vercel Functions WebSockets (`experimental_upgradeWebSocket`) | `references/module-stubs.md` | 🚧 planned — experimental API |

The user can override any default. If they say "add auth with Clerk", read `references/module-auth.md` for the Clerk variant if present; otherwise refuse and explain — better-auth is the default and adding new variants is a contract change.

For modules marked "stub", the reference file gives the shape (packages, env vars, out-of-band steps) but doesn't provide the install templates. Implement the stub on first request — copy `module-auth.md` or `module-db.md` as the structural template and fill in.

## When this skill applies

- A `<project-root>/` exists (`phase >= scaffolded`).
- The user names a module: "add auth", "wire the db", "add stripe", "set up resend".
- The orchestrator routes here from `scaffolded` or `page_generated`.

## Contract

This skill follows the dev-flow contract — see `references/contracts.md`. Key facts:
- Reads `<root>/.workflow/meta.json#stack` to honor existing choices.
- Modifies `<project-root>/` (installs deps, writes config, writes one example route or function).
- Updates `meta.json#stack` to record the module's tech choice (e.g., `stack.auth = "better-auth"`).
- Sets `phase = "module_added"` (only if current phase is earlier in the enum).
- **Idempotent**: re-running the same module check whether it's already wired and skips/updates instead of duplicating.

## Monorepo awareness

Before Step 1: check `meta.json#stack.framework`.

- If `"monorepo"`: this skill operates inside `apps/web/` (cwd = `<project-root>/apps/web/`) for web-specific modules (motion, email server actions, queries), AND inside `packages/api/` for modules consumed by both apps (auth, db, storage, realtime, payments — these are backend client wiring, not web-specific UI). Run `monorepo-sync-types` after `db` and `auth` modules to propagate types to `packages/shared/`.
- If `"next"` / `"vite-react"` / `"remix"` / `"astro"` / etc.: operate at project root (current behavior, unchanged).
- If `"expo-rn"`: refuse — use `rn-module-add` instead.

For the monorepo case, "install + generate" means: install npm packages into the appropriate workspace (`pnpm add --filter @<slug>/web` or `pnpm add --filter @<slug>/api`), and generate code into the right sub-folder. Use the workspace-relative paths in all references below.

## Workflow

### Step 1 — Determine the target module + tech

The user tells you which module (one per invocation: `auth`, `db`, etc.). Sub-decision: which tech?

- If `meta.json#stack.<module>` is set, use that tech. Don't ask again.
- If not set, propose the default from the table above with a one-line rationale ("Suggerisco better-auth perché è leggero, self-hosted, e si integra naturalmente con Drizzle"), then accept whatever the user picks.

If the user picks a tech the skill doesn't have a reference file for, refuse and offer to add it (i.e., they want a new variant — that's a contract update, not a runtime choice).

### Step 2 — Read the variant reference

Open `references/module-<name>.md` for the chosen module. The reference is the source of truth for the install steps and the file paths. Read it end-to-end before doing anything.

Each reference describes:
1. **Install commands** — packages to add, optional dev deps, environment variables to set.
2. **Config files** — paths and templates (e.g., `<project-root>/lib/auth.ts`, `drizzle.config.ts`).
3. **Schema or migration setup** — for `db`, the Drizzle schema folder layout; for `payments`, the webhook secret rotation.
4. **Reference implementation** — exactly one route or server function showing the module in use (e.g., a `/sign-in` page for auth, a `/api/stripe/webhook` for payments). The user can copy-paste-evolve from there.
5. **Idempotency check** — how to detect the module is already installed (typically a `package.json` dependency check + a config file check). On re-run, skip install + config but offer to regenerate the reference implementation if the user asks.
6. **Environment variables required** — list with descriptions; write a `.env.local.example` entry, never the real values.

### Step 3 — Apply the changes

Run install commands. Write config files from the templates. Write the reference implementation. Update `.env.local.example`.

If the framework-specific path conventions differ (Next App Router vs. Vite vs. Remix), the variant reference handles it — don't hand-edit paths in the skill body.

**Never run `npm install` for a non-reference module.** Stick to what the variant reference declares. If the user wants additional libraries, that's a separate `module-add` invocation or a manual step.

### Step 4 — Verify

After install + config:

- Run `npm run build` in `<project-root>/`. If it fails, the most common cause is a missing env var (placeholders accepted) — fix the placeholder and retry once. If still failing, stop and tell the user what's missing.
- For modules that need a connection (db, stripe, email), do **not** try to actually connect — that requires real credentials the user will set in `.env.local`. Just verify the code compiles and imports resolve.
- For `db`, run `drizzle-kit push` against a placeholder URL to confirm the schema is valid syntactically. If `drizzle-kit` requires a real URL, skip this and tell the user "run `npm run db:push` once your `DATABASE_URL` is set".

### Step 5 — Update state and report

Update `.workflow/meta.json`:
- if current phase is earlier than `module_added`, set `phase = "module_added"`. (Phase is monotonic — running `module-add` multiple times keeps the phase, just appends to history.)
- record the chosen tech: `stack.<module> = "<tech>"`.
- bump `updated_at`.
- append history:
  ```json
  {
    "skill": "module-add",
    "ran_at": "<now>",
    "inputs": {"module": "auth", "tech": "better-auth"},
    "outputs": ["lib/auth.ts", "lib/auth-client.ts", "app/api/auth/[...all]/route.ts", "app/sign-in/page.tsx", ".env.local.example"],
    "phase_before": "<prev>",
    "phase_after": "module_added"
  }
  ```

Tell the user:
- What was installed and where (paths).
- Required environment variables, with a pointer to `.env.local.example`.
- The reference implementation route/function (so they know where to start customizing).
- Any out-of-band steps the user must do themselves (create a Neon project, get a Stripe API key, configure DNS for Resend, etc.) — be concrete and link to the relevant dashboard.
- Next-step proposal: another `module-add` for a different module, or `screenshot-to-page` to keep building UI.

## Important constraints

- **One module per invocation.** "Add auth and db" is two runs — keep history clean.
- **Idempotent.** Re-running `module-add auth` on a project that already has it should detect, skip install, and offer to regenerate examples or rotate env vars — not double-install.
- **No real credentials.** Always use placeholders in `.env.local.example`. The user fills `.env.local` themselves.
- **Don't pick alternative tech silently.** If the variant reference doesn't cover the user's tech of choice, refuse and explain.
- **Preserve user code.** If the user has already written something at the path the reference implementation would land (e.g., they made a custom `/sign-in` page), don't overwrite. Ask, or write to `<route>-example/` instead.
- **Stay within `<project-root>/`.** Don't touch other parts of `.workflow/`. Other skills own those.

## Cross-module dependencies

Some modules depend on others. If the user runs them out of order, the skill must:

- `auth` requires `db`. If `stack.db` is `null`, ask: "auth needs a database to store sessions. Set up `db` first?" and route there before `auth`.
- `payments` requires `auth` and `db`. Same pattern.
- `email` is independent.
- `storage` is mostly independent (some providers integrate with auth for signed URLs, but it's optional).
- `test` is independent — best run after `db` so server-action smoke tests have a schema to mock against, but works without it.
- `ci` is mostly independent — works best after `test` (so CI has tests to run) but writes a workflow that gracefully skips test steps when none exist.
- `motion` is fully independent — pure UI concern, no backend dependency. Run only when a project genuinely needs JS-driven motion (gestures, magnetic hover, shared-element transitions); for plain reveal-on-scroll, `tw-animate-css` (already installed via shadcn) is enough and lighter.
- `deploy` should be last — it reads the configured stack and produces deploy config.

When dependencies are missing, **ask, don't block silently.** "I see you're trying to add auth but there's no database yet. Want me to set up `db` (Neon + Drizzle) first, then come back to auth?"


## Folder structure rules (canonical)

When this skill wires a module, respect the canonical folder structure (spec: `docs/superpowers/specs/2026-06-06-folder-structure-refactor.md`):

- **`auth` module**: UI components (sign-in form, sign-up form) go in `app/(auth)/_components/`. Auth client + helpers go in `lib/auth/`. The `<AuthGuard>` redirect lives in `app/(app)/layout.tsx`.
- **`db` module**: client + schema in `lib/db/`. No components written by this module.
- **`payments` module**: client wiring in `lib/payments/`. UI (paywall, checkout button) suggested in `app/(app)/<context>/_components/` or page-specific. Pricing comparison table eventually promotes to `components/shared/billing/PricingTable.tsx`.
- **`storage` module**: client in `lib/storage/`. Upload UI co-located with the page that uses it.
- **`email` module**: server-side only; no components.
- **`deploy` module**: config files at project root only.
