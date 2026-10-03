# module-add → `payments` (Stripe)

Wire **Stripe** for subscriptions and one-time payments into an existing scaffold. Defaults: server-side `stripe` SDK, webhook receiver with signature verification, customer portal redirect, env-driven price IDs.

This is the **commerce backbone**: every customer-facing money flow goes through these primitives. The reference implementation is intentionally minimal — one webhook, one portal endpoint, one example page — because real billing UX is too project-specific to template.

## Before the implementation: processor or merchant of record

Stripe is a **payment processor**. The seller of record stays *you*, so VAT, GST and US sales-tax
registration and remittance are yours — Stripe Tax computes them, it does not assume the liability.
A **merchant of record** is the legal seller instead of you: it appears on the customer's statement,
issues the invoice, and collects and remits the tax in every jurisdiction it supports. For a
one-person SaaS selling across the EU and the US that difference is usually worth more than the fee
gap, and it is the question to settle before writing a webhook.

Fees and roles checked on **2026-09-30**:

| Option | Role | Fee | Legal seller |
|---|---|---|---|
| **Stripe** (implemented) | processor | per-region card pricing; Stripe Tax is an add-on | you |
| **Creem** | merchant of record | **3.9% + $0.40**, $0 monthly, $0 setup; payouts on the 1st and 15th, 0% on several methods; VAT/GST/sales tax in 50+ countries | [Armitage Labs OÜ](https://www.creem.io/terms), Tallinn, **Estonia** (reg. 16977866) |
| **Polar** | merchant of record | free Starter **5% + $0.50** since May 2026; Pro $20/mo at 3.8% + $0.40; organisations created before 2026-05-27 grandfathered at 4% + $0.40 | Polar Software, Inc., Delaware, **US** |
| Lemon Squeezy · Paddle | merchant of record | not re-checked in this pass — read the current page before quoting one | US · UK |

**Creem is the only merchant of record in this table established in the EU**, which is why it is
also a row in `dev-flow/references/eu-data-sovereignty.md` §4.8 — where the honest caveat lives:
EU-established and EU-hosted for servers (AWS Germany), but its DPA names Supabase (**US**) for the
database and several US sub-processors, so it is not an EU-only stack.

Two notes for whoever implements a variant. Creem publishes a `SKILL.md` at
`https://www.creem.io/SKILL.md`, which means it arrives as a third-party skill and goes through
`registry-intake`'s `skill-review` first — on 2026-09-30 it reported K2 (`brew install`), K3 (it
asks the agent to save it) and K7 (an unversioned URL). And the skill is marketing: the reason to
consider Creem is the Estonian establishment and the DPA, not the file. Nothing here is implemented
— follow `module-stubs.md`: a variant is written the first time a user asks for it.

## Idempotency check

Before doing anything, check whether payments are already wired:

1. `<project-root>/package.json` contains `"stripe"` in dependencies.
2. `<project-root>/lib/stripe.ts` exists.
3. `<project-root>/app/api/stripe/webhook/route.ts` exists.
4. `<project-root>/.env.local.example` contains `STRIPE_SECRET_KEY`.

If all four: tell the user it's installed, offer to add new event handlers to the webhook or rotate keys. Don't double-install.

## Prerequisites

- `meta.json#stack.auth` must be set. Stripe customers are mapped to your users — without auth there's nothing to map them to. If null, ask the user to run `module-add auth` first.
- `meta.json#stack.db` must be set. The mapping `user.id ↔ stripeCustomerId` and the cached subscription state live in your DB. If null, ask the user to run `module-add db` first.

## Install

```bash
cd <project-root>
pnpm add stripe @stripe/stripe-js @stripe/react-stripe-js
```

The Stripe CLI is needed for **local webhook forwarding** during dev. Tell the user to install it once globally:

```bash
brew install stripe/stripe-cli/stripe         # macOS
# or download from https://github.com/stripe/stripe-cli/releases
stripe login
```

## Files to write

### `lib/stripe.ts`

```typescript
import Stripe from "stripe";
import { env } from "@/lib/env";

/**
 * Server-side Stripe client. Use ONLY from server actions, route handlers,
 * and RSC. Never import this from a client component — it would leak the
 * secret key into the bundle.
 *
 * The apiVersion is pinned. Stripe rolls forward; pinning protects you from
 * silent webhook payload changes. Bump deliberately when you're ready.
 *
 * The current SDK default is "2026-09-30.endive" (stripe-node 23.0.0, 2026-09-30)
 * — a fresh `stripe` install ships Endive types, so pinning an older literal like
 * "2026-08-26.dahlia" can throw a TS mismatch against the bundled types. Match
 * the pin to the installed SDK's types (or `stripe listen --latest-api-version`
 * to confirm your account). [VERIFY] on install.
 */
export const stripe = new Stripe(env.STRIPE_SECRET_KEY, {
  apiVersion: "2026-09-30.endive",
  typescript: true,
});
```

**stripe-node 23.0.0 (2026-09-30) — what breaks, beyond the pin.** Read this before upgrading an
existing project, because three of the four are silent:

- **Node 20 is the minimum.** Node 18 support is dropped — check the runtime before the SDK.
- **`verifyHeader()` / `verifyHeaderAsync()` now apply `Webhook.DEFAULT_TOLERANCE`** when
  `tolerance` is omitted; they previously skipped the timestamp check entirely. An omitted argument
  used to mean *no replay window* and now means *the default one*, so a test fixture with an old
  timestamp starts failing — which is the check working. The mirror image is the dangerous half:
  **passing `0` to `constructEvent` now really does skip the timestamp check**, where before `0`
  was treated as the default. Nobody should pass `0`; if a codebase does, it just lost its replay
  protection without a line changing.
- **`Stripe.constructEventWithoutVerification()` is removed** from the top-level client (it was
  added by mistake in 22.5.0). The method on `stripe.webhooks` remains — and the rule in this file
  stands: a webhook route verifies, full stop.
- **The `ErrorType` export is gone** — use `stripe.errors` / `Stripe.errors`, which works as both a
  type and a value. And **an incomplete or severed response body now throws `StripeConnectionError`
  instead of `StripeAPIError`**: retry logic that branched on the error class needs re-reading,
  since this is the class of failure that *is* worth retrying.
- Minor: `STRIPE_SUPPRESS_NOTICES=true` silences the SDK's test/sandbox notices — except for a
  detected AI agent, which still sees them. `Stripe.V2List<T>` lost the never-populated `object`,
  `has_more` and `url` fields.

### `lib/stripe-client.ts`

```typescript
"use client";
import { loadStripe, type Stripe as StripeClient } from "@stripe/stripe-js";
import { env } from "@/lib/env";

let stripePromise: Promise<StripeClient | null> | null = null;

/**
 * Client-side Stripe.js loader, memoized. Only used by routes/components that
 * mount Stripe Elements (card form, etc.) — for redirect-to-Checkout flows
 * you don't even need this.
 */
export function getStripe() {
  if (!stripePromise) {
    stripePromise = loadStripe(env.NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY);
  }
  return stripePromise;
}
```

### `app/api/stripe/webhook/route.ts` (Next App Router)

```typescript
import { headers } from "next/headers";
import { NextResponse } from "next/server";
import type Stripe from "stripe";
import { stripe } from "@/lib/stripe";
import { env } from "@/lib/env";

/**
 * Stripe webhook receiver.
 *
 * Two non-negotiable rules:
 *   1. ALWAYS verify the signature with `constructEvent`. A naked POST endpoint
 *      that trusts the body is a path to anyone billing your customers.
 *   2. ALWAYS return 200 quickly. Stripe retries on non-2xx for up to 3 days.
 *      Heavy work (sending emails, fanning out to multiple services) goes in a
 *      queue, not inline. For dev-flow's reference impl, we keep it inline —
 *      replace with a job runner when traffic grows.
 *
 * Local dev requires the Stripe CLI:
 *   stripe listen --forward-to localhost:3000/api/stripe/webhook
 * Then put the printed `whsec_...` in .env.local as STRIPE_WEBHOOK_SECRET.
 */
export async function POST(req: Request) {
  const body = await req.text();
  const signature = (await headers()).get("stripe-signature");

  if (!signature) {
    return NextResponse.json({ error: "missing signature" }, { status: 400 });
  }

  let event: Stripe.Event;
  try {
    event = stripe.webhooks.constructEvent(
      body,
      signature,
      env.STRIPE_WEBHOOK_SECRET
    );
  } catch (err) {
    const message = err instanceof Error ? err.message : "unknown error";
    return NextResponse.json(
      { error: `signature verification failed: ${message}` },
      { status: 400 }
    );
  }

  // Whitelist the events you actually care about. Stripe sends MANY event
  // types — silently ignoring the rest is the right default.
  switch (event.type) {
    case "checkout.session.completed": {
      const session = event.data.object as Stripe.Checkout.Session;
      // TODO: persist `session.customer` against your user, mark order paid.
      console.log("[stripe] checkout completed:", session.id);
      break;
    }
    case "customer.subscription.created":
    case "customer.subscription.updated":
    case "customer.subscription.deleted": {
      const sub = event.data.object as Stripe.Subscription;
      // TODO: upsert `subscriptions` table with status, current_period_end.
      console.log("[stripe] subscription:", event.type, sub.id, sub.status);
      break;
    }
    case "invoice.payment_failed": {
      const invoice = event.data.object as Stripe.Invoice;
      // TODO: notify the customer, flag the subscription as past_due.
      console.log("[stripe] payment failed:", invoice.id);
      break;
    }
    default:
      // Ignore — but log at debug level for visibility.
      break;
  }

  return NextResponse.json({ received: true });
}
```

### `app/api/stripe/portal/route.ts`

```typescript
import { NextResponse } from "next/server";
import { stripe } from "@/lib/stripe";
import { env } from "@/lib/env";
import { getCurrentUserId } from "@/lib/auth-server";

/**
 * Customer portal redirect. Looks up the user's stripeCustomerId, creates a
 * billing-portal session, and returns a 303 redirect to the hosted page.
 *
 * The portal lets the customer manage payment methods, view invoices, cancel,
 * upgrade, etc. — Stripe owns the UI, you own the redirect.
 *
 * Replace `getStripeCustomerId()` with your real lookup once you have a
 * `users.stripeCustomerId` column.
 */
export async function POST() {
  let userId: string;
  try {
    userId = await getCurrentUserId();
  } catch {
    return NextResponse.json({ error: "unauthorized" }, { status: 401 });
  }

  const customerId = await getStripeCustomerId(userId);
  if (!customerId) {
    return NextResponse.json(
      { error: "no Stripe customer for this user — purchase something first" },
      { status: 400 }
    );
  }

  const session = await stripe.billingPortal.sessions.create({
    customer: customerId,
    return_url: `${env.NEXT_PUBLIC_APP_URL}/billing`,
  });

  return NextResponse.redirect(session.url, 303);
}

// Replace this stub with a real DB query once `module-add db` has run.
async function getStripeCustomerId(_userId: string): Promise<string | null> {
  throw new Error(
    "getStripeCustomerId not wired — add a `stripeCustomerId` column to your users table and replace this stub"
  );
}
```

### `app/billing/page.tsx` (reference UI)

The import below assumes `stack.ui = "shadcn"` (the default). Read `meta.json#stack.ui` before writing this file: for `"mui"` swap in MUI's `Button`; for `"base-ui"` (standalone Base UI) or `"coss"` (Coss/UI) the button still comes from `components/ui/button` or `@coss/ui` respectively — same import shape as shadcn, different source package, so match whichever registry the project already uses rather than assuming shadcn's default path.

```tsx
import Link from "next/link";
import { Button } from "@/components/ui/button";

/**
 * Billing page — minimal reference. Real billing UX shows:
 *   - current plan + status (active / past_due / canceled)
 *   - next renewal date
 *   - upgrade / downgrade buttons that POST to a checkout-session route
 *   - a link to the customer portal (handled below)
 *
 * The form below opens a hosted Stripe Customer Portal. For new purchases
 * (a user without a subscription yet), build a separate `/api/stripe/checkout`
 * route that creates a Checkout Session — see Stripe docs § Subscriptions.
 */
export default function BillingPage() {
  return (
    <main className="mx-auto max-w-2xl px-6 py-16 space-y-8">
      <div className="space-y-3">
        <p className="text-[12px] tracking-wide uppercase font-mono text-on-surface-variant">
          Account · Billing
        </p>
        <h1 className="text-[40px] font-semibold leading-tight">
          Manage your subscription.
        </h1>
        <p className="text-on-surface-variant">
          Update payment methods, view invoices, or cancel your plan in the
          Stripe Customer Portal.
        </p>
      </div>

      <form action="/api/stripe/portal" method="POST">
        <Button type="submit">Open billing portal</Button>
      </form>

      <p className="text-[13px] text-on-surface-variant">
        Need a different plan?{" "}
        <Link href="/pricing" className="underline hover:text-on-surface">
          See pricing
        </Link>
        .
      </p>
    </main>
  );
}
```

### Schema additions for Drizzle

Append to `lib/db/schema.ts` (created by `module-add db`):

```typescript
import { pgTable, serial, text, timestamp, integer, uniqueIndex, index } from "drizzle-orm/pg-core";
import { users } from "./schema"; // assumes module-add auth has run

export const subscriptions = pgTable(
  "subscriptions",
  {
    id: serial("id").primaryKey(),
    userId: text("user_id").notNull().references(() => users.id, { onDelete: "cascade" }),
    stripeCustomerId: text("stripe_customer_id").notNull(),
    stripeSubscriptionId: text("stripe_subscription_id").notNull(),
    stripePriceId: text("stripe_price_id").notNull(),
    status: text("status").notNull(), // active, past_due, canceled, incomplete, etc.
    currentPeriodEnd: timestamp("current_period_end").notNull(),
    cancelAtPeriodEnd: integer("cancel_at_period_end").notNull().default(0),
    createdAt: timestamp("created_at").defaultNow().notNull(),
    updatedAt: timestamp("updated_at").defaultNow().notNull(),
  },
  (table) => ({
    subscriptionUnique: uniqueIndex("subscriptions_stripe_id_unique").on(table.stripeSubscriptionId),
    userIdx: index("subscriptions_user_idx").on(table.userId),
  })
);
```

Also add `stripeCustomerId: text("stripe_customer_id")` (nullable) to your `users` table — needed by `getStripeCustomerId()`.

Run `pnpm db:push` (dev) or `pnpm db:generate && pnpm db:migrate` (prod) to apply.

## Environment variables

Append to `.env.local.example`:

```
# Stripe — get keys from https://dashboard.stripe.com/test/apikeys
STRIPE_SECRET_KEY=sk_test_xxx
STRIPE_WEBHOOK_SECRET=whsec_xxx
NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY=pk_test_xxx
```

Also extend `lib/env.ts` to validate these (Zod block):

```typescript
STRIPE_SECRET_KEY: z.string().startsWith("sk_"),
STRIPE_WEBHOOK_SECRET: z.string().startsWith("whsec_"),
NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY: z.string().startsWith("pk_"),
```

Tell the user to:
1. Register a Stripe account (free until they go live).
2. Grab test-mode keys from the dashboard.
3. Run `stripe listen --forward-to localhost:3000/api/stripe/webhook` in a separate terminal during dev — copy the printed `whsec_...` into `.env.local`.
4. For production: register the webhook URL in the Stripe dashboard (https://dashboard.stripe.com/webhooks) and use the **production** `whsec_` from there.

## Verification

After install + write:

```bash
pnpm typecheck
pnpm build
```

Build must succeed with the placeholder env vars. To test the webhook locally:

```bash
# Terminal 1
pnpm dev

# Terminal 2
stripe listen --forward-to localhost:3000/api/stripe/webhook

# Terminal 3
stripe trigger checkout.session.completed
```

You should see `[stripe] checkout completed: cs_test_...` in your dev server logs.

## Update meta.json

```json
{
  "stack": {
    "payments": "stripe"
  }
}
```

## Known caveats

- **Never log raw event bodies in production**. They contain customer email, last4, sometimes addresses. The reference impl uses `console.log` for visibility — swap to a structured logger that scrubs PII before shipping.
- **Webhook handlers must be idempotent**. Stripe will retry on non-2xx responses up to 3 days. If your handler creates a row, use `INSERT ... ON CONFLICT DO NOTHING` keyed on `event.id`. Otherwise duplicate events = duplicate side effects.
- **The `apiVersion` pin is load-bearing**. Removing it makes Stripe roll your account forward silently and your TypeScript types may diverge from the runtime payload. Bump deliberately, never accidentally.
- **The reference UI assumes a single-tier subscription**. Real pricing UX (multiple plans, annual/monthly toggle, seat-based) is too project-specific — don't templatize it. Use Stripe's `pricing-table` web component for a fast first version.
- **PCI scope**: by using Stripe Checkout / Elements, you stay in PCI-DSS SAQ-A scope (lowest). Don't try to take card numbers on your own form — that drags you into SAQ-D and you don't want to be there.
