# module-add → not-yet-implemented variants

The following module references are **stubs**. Use them as scaffolding cues if/when the user requests them. The pattern is the same as `module-auth.md` and `module-db.md` — copy the section structure (Idempotency check / Prerequisites / Install / Files to write / Env vars / Update meta.json / Known caveats) and fill in.

If the user invokes `module-add` for one of these and the variant reference doesn't exist yet, **stop and tell them** — don't improvise. Improvising leads to half-wired modules that look done but break in production.

---

## `module-payments` — Stripe

**Default**: Stripe with subscription + one-time payment patterns. Webhook receiver at `/api/stripe/webhook`. Customer portal redirect handler at `/api/stripe/portal`. Reference UI: a `/billing` page using `@stripe/react-stripe-js`.

**Prerequisites**: `auth` (to know who's the customer) and `db` (to map user → stripeCustomerId).

**Packages**: `stripe`, `@stripe/stripe-js`, `@stripe/react-stripe-js`.

**Env vars**: `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET`, `NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY`.

**Out-of-band steps**: register a Stripe account, get test keys, install Stripe CLI for local webhook forwarding (`stripe listen --forward-to localhost:3000/api/stripe/webhook`).

---

## `module-email` — Resend

**Default**: Resend with React Email for templates. Single transactional helper at `lib/email.ts` exposing `sendEmail({ to, template, props })`.

**Prerequisites**: none (independent).

**Packages**: `resend`, `react-email`, `@react-email/components`.

**Env vars**: `RESEND_API_KEY`, `RESEND_FROM_EMAIL`.

**Out-of-band steps**: create a Resend account, verify a sending domain (DNS records), get an API key.

---

## `module-storage` — UploadThing

**Default**: UploadThing for file uploads (images, documents). Reference UI: a `/upload` example page with the UploadThing button.

**Alternative**: S3 (requires AWS credentials) — handle as a separate variant when needed.

**Prerequisites**: `auth` is recommended (to gate uploads to signed-in users).

**Packages**: `uploadthing`, `@uploadthing/react`.

**Env vars**: `UPLOADTHING_SECRET`, `UPLOADTHING_APP_ID`.

**Out-of-band steps**: register an UploadThing account, configure a file router with size/type limits.

---

## `module-deploy` — Vercel

**Default**: Vercel via `vercel.json` config + GitHub Actions for CI. Detects framework from `meta.json#stack.framework` and writes the appropriate `vercel.json`.

**Prerequisites**: at least one route should exist (so the deploy isn't deploying an empty scaffold).

**Packages**: none (Vercel CLI is global — `npm install -g vercel`).

**Env vars**: lifted from the existing `.env.local.example` and instructed to be set via the Vercel dashboard or `vercel env`.

**Out-of-band steps**: run `vercel link`, push to GitHub, configure preview/production environments in the Vercel dashboard.

**Alternative deploy targets**: Fly.io, Cloudflare Pages, Render — each is a separate variant when the user asks.

---

## When to implement these

Implement a stub on demand: the first time a user says "module-add payments" or similar. Don't preemptively implement all of them — references that go stale (e.g., Stripe API version drift) hurt more than the missing variant.
