# module-add → `analytics` (traffic · product · advanced)

Measurement is **opt-in**. This module runs only when the user asks to measure usage — at the start, or later
when a prototype becomes a product. It wires one **level** at a time, and a level already on is skipped:

| Level | What it measures | With | New sub-processor |
|---|---|---|---|
| `traffic` | visits, pages, referrers, Web Vitals | Vercel Web Analytics + Speed Insights | none (Vercel is already one) |
| `product` | the activation event, D7/D30 retention, the PRD's events | an `analytics_events` table in the project's own database, `track()` from server actions, SQL | none: the data stays in the database's region |
| `advanced` | funnels with a UI, session replay, dashboards — on request | PostHog Cloud EU, or OpenPanel when `stack.data_residency = "eu-sovereign"` | one, registered |

Vercel Web Analytics and Plausible **cannot** compute D7/D30 retention: both drop the visitor identity after
24 hours. That is why the PRD's numbers come from `product`, not from `traffic` (checked 2026-10-18,
`dev-flow/references/eu-data-sovereignty.md` §4.9).

## Before anything: the levels and the targets

1. Read `meta.json#stack.analytics` (a list; absent or `[]` = not measuring yet) and ask which levels the user
   wants now. `traffic` alone is a fine answer for a prototype.
2. **`product` needs targets first.** Read `.workflow/PRD.md` `## Measurement`. If it is missing or says `TBD`,
   ask — in one batch — the moment a user first gets the value (the **activation event**), how many activated
   users should come back after a week and after a month (**D7/D30**), what would look like traction but is not
   (**false positives**), and which **events** to record. Write the section into PRD.md as a revision, in the
   contract's format (`dev-flow/references/contracts.md` §PRD.md):

   ```markdown
   ## Measurement

   Decided before launch, not after. Levels: traffic, product.

   - **Activation event**: `invoice_sent` — the user sent their first invoice (within 7 days of signup)
   - **Retention targets**: D7 ≥ 25 % · D30 ≥ 15 % of activated users (back on day 7 / day 30)
   - **False positives to watch**: sign-ups without an invoice; invoices sent only to themselves
   - **Events to instrument**: `invoice_sent` (send action) · `client_added` (clients form)
   ```

   Event names are `snake_case`, past-tense verbs, `^[a-z][a-z0-9_]*$`: they are keys, so they do not change.
   Example targets, if the user asks for one, are marked as examples — the user's numbers replace them.
3. **`product` needs a database** (`stack.db`). Without one, run `module-add db` first.

## Idempotency check

Per level:

- `traffic`: `package.json` has `@vercel/analytics` and `@vercel/speed-insights`, and `app/layout.tsx` renders
  `<Analytics />`.
- `product`: `lib/analytics/track.ts` exists and the schema has `analyticsEvents`.
- `advanced`: `package.json` has `posthog-js` (or `@openpanel/nextjs`).

A level already wired is reported, not reinstalled. Adding a level never touches the others.

## Prerequisites

- `traffic`: deployed on Vercel (`stack.deploy = "vercel"`). Works on Hobby; no custom events needed.
- `product`: `module-add db` (Drizzle + Neon, PGlite locally), and a signed-in user id in the server actions
  (`module-add auth`).
- `advanced`: the consent gate `lib/consent.ts` from `compliance-audit` if anything will be identified on the
  client.

## Install

```bash
pnpm add @vercel/analytics @vercel/speed-insights          # traffic
pnpm add posthog-js posthog-node                            # advanced, PostHog
pnpm add @openpanel/nextjs                                  # advanced, OpenPanel (eu-sovereign)
```

`product` installs nothing: it is the project's own database.

> **Checked 2026-10-18** with `npm view`: `@vercel/analytics` 2.0.1, `@vercel/speed-insights` 2.0.0,
> `posthog-js` 1.438.12, `posthog-node` 5.56.2, `@openpanel/nextjs` 1.5.1, `drizzle-orm` 0.45.4.

## Files to write — `traffic`

### `app/layout.tsx` (patch)

```tsx
import { Analytics } from "@vercel/analytics/next";
import { SpeedInsights } from "@vercel/speed-insights/next";

// inside <body>, after {children}; production only, so previews and dev do not count
{process.env.VERCEL_ENV === "production" && (
  <>
    <Analytics />
    <SpeedInsights />
  </>
)}
```

Cookieless; no consent banner is needed for it under Vercel's own description, which a DPO confirms. Since
`@vercel/analytics` 2 the script and intake paths are randomised, so no proxy is needed.

## Files to write — `product`

### `lib/db/schema.ts` (append)

```typescript
import { index, jsonb, pgTable, serial, text, timestamp } from "drizzle-orm/pg-core";

export const analyticsEvents = pgTable(
  "analytics_events",
  {
    id: serial("id").primaryKey(),
    userId: text("user_id").notNull(),
    name: text("name").notNull(),
    props: jsonb("props").$type<Record<string, unknown>>(),
    createdAt: timestamp("created_at", { withTimezone: true }).notNull().defaultNow(),
  },
  (t) => [index("analytics_events_user_idx").on(t.userId, t.createdAt), index("analytics_events_name_idx").on(t.name)],
);
```

Then `pnpm drizzle-kit generate && pnpm drizzle-kit migrate`. The rows are keyed by the user id, so they follow
the account: the DSAR deletion path (`compliance-audit` R1) deletes them with the user.

### `lib/analytics/events.ts`

Generated from the PRD's **Events to instrument**, plus `signed_up`, which every project has:

```typescript
export const EVENTS = ["signed_up", "invoice_sent", "client_added"] as const;
export type AnalyticsEvent = (typeof EVENTS)[number];
export const ACTIVATION_EVENT: AnalyticsEvent = "invoice_sent";
```

A misspelt event no longer compiles. A new event goes into the PRD first, then here.

### `lib/analytics/track.ts`

```typescript
import "server-only";
import { db } from "@/lib/db";
import { analyticsEvents } from "@/lib/db/schema";
import type { AnalyticsEvent } from "./events";

/** Record a product event for a signed-in user. Never throws: measurement must not break the action. */
export async function track(userId: string, event: AnalyticsEvent, props?: Record<string, unknown>): Promise<void> {
  if (process.env.VERCEL_ENV && process.env.VERCEL_ENV !== "production" && process.env.ANALYTICS_DEV !== "1") return;
  try {
    await db.insert(analyticsEvents).values({ userId, name: event, props: props ?? null });
  } catch (error) {
    console.warn("analytics: event not recorded", event, error instanceof Error ? error.message : error);
  }
}
```

**`signed_up` is the signup.** Record it where the account is created, so that a user who signs up and does
nothing else still counts — that is the false positive the PRD watches, and without it activation reads as
100 %. With better-auth (`module-add auth`), in `lib/auth.ts`:

```typescript
databaseHooks: {
  user: { create: { after: async (user) => { await track(user.id, "signed_up"); } } },
},
```

(`databaseHooks.user.create.after(user, context)`, checked in `@better-auth/core`'s types, better-auth 1.7.10.)

Then call it from the server action where the thing happens, after it succeeded:

```typescript
await sendInvoice(invoice);
await track(session.user.id, "invoice_sent", { amount: invoice.total });
```

### `lib/analytics/metrics.ts` and the `metrics` script

The SQL is `module-add/assets/analytics/metrics.sql` — copy it to `lib/analytics/metrics.sql`. Two queries:
activation rate per weekly signup cohort, and D7/D30 retention of activated users per cohort (definitions in
the file's header). Verified on Postgres (PGlite) on 2026-10-18 against known rows.

```typescript
import "server-only";
import { readFileSync } from "node:fs";
import { join } from "node:path";
import { sql } from "drizzle-orm";
import { db } from "@/lib/db";
import { ACTIVATION_EVENT } from "./events";

const [ACTIVATION_SQL, RETENTION_SQL] = readFileSync(join(process.cwd(), "lib/analytics/metrics.sql"), "utf8")
  .split(/;\s*\n/)
  .map((q) => q.replace(/^(\s*--.*\n)*/, "").trim())
  .filter(Boolean);

function bind(query: string) {
  const [before, after] = query.split(":activation");
  return sql`${sql.raw(before)}${ACTIVATION_EVENT}${sql.raw(after)}`;
}

export async function activation() {
  return (await db.execute(bind(ACTIVATION_SQL))).rows;
}

export async function retention() {
  return (await db.execute(bind(RETENTION_SQL))).rows;
}
```

`<project-root>/scripts/metrics.ts` prints both tables (`console.table`), and `package.json` gets
`"metrics": "tsx scripts/metrics.ts"`. Retention is `retained_dN / eligible_dN`: a user counts for D7 only once
their day 7 has passed, so a young cohort does not read as 0 %. A user is activated when the activation event
happens within 7 days of signup; change the window in `metrics.sql` and in the PRD line together.

An admin page that shows them is the project's call. On Vercel, the `.sql` file is not traced into the function
bundle by default: add it to `outputFileTracingIncludes` in `next.config.ts`
(`{ "/admin/metrics": ["./lib/analytics/metrics.sql"] }`), or inline the two queries as strings.

## Files to write — `advanced`

### PostHog (EU)

`instrumentation-client.ts`:

```typescript
import posthog from "posthog-js";

posthog.init(process.env.NEXT_PUBLIC_POSTHOG_KEY!, {
  api_host: "/ingest",                 // the rewrite below; never a path called /analytics
  ui_host: "https://eu.posthog.com",
  cookieless_mode: "on_reject",        // nothing captured or stored until the user decides
  defaults: "2026-05-30",
});
```

`next.config.ts` rewrites — the EU host is written explicitly; `@posthog/next` is pre-release and defaults to
the **US** host:

```typescript
async rewrites() {
  return [
    { source: "/ingest/static/:path*", destination: "https://eu-assets.i.posthog.com/static/:path*" },
    { source: "/ingest/:path*", destination: "https://eu.i.posthog.com/:path*" },
  ];
},
skipTrailingSlashRedirect: true,
```

`cookieless_mode` also needs **Cookieless server hash mode** switched on in the PostHog project settings. On
consent, opt in and only then identify — through the gate `compliance-audit` writes:

```typescript
import { hasConsent } from "@/lib/consent";
if (hasConsent("analytics")) {
  posthog.opt_in_capturing();
  posthog.identify(user.id);
} else {
  posthog.opt_out_capturing();   // still counted with PostHog's server-side hash, nothing stored
}
```

(`"always"` never stores anything but is not meant for identified users; PostHog's data-collection docs,
read 2026-10-18.)

Server side, `track()` can forward the same event so the names stay one list. **This sends identified
events of signed-in users to a US-controlled processor**: forward only for users who consented on the client
(store the choice with the user), or not at all — whether identified analytics of logged-in users needs consent
is the DPO's call (`compliance-audit` R11).

```typescript
import { PostHog } from "posthog-node";
const ph = new PostHog(process.env.POSTHOG_KEY!, { host: "https://eu.i.posthog.com", flushAt: 1, flushInterval: 0 });
ph.capture({ distinctId: userId, event, properties: props });
await ph.shutdown();   // serverless: flush before the function ends
```

### OpenPanel (`eu-sovereign`)

Self-hosted is the strict choice. `OpenPanelComponent` from `@openpanel/nextjs` in the layout, server events with
the client secret, and `createRouteHandler` from `@openpanel/nextjs/server` as the proxy. Cookieless by design.
The OpenPanel cloud (Hetzner, Germany) puts Cloudflare (US) at the edge: accept it only if the user does, and
register it as a transfer.

### Data residency (step 1b)

```bash
python3 dev-flow/scripts/data_residency.py add <root> --name PostHog --service "Product analytics" \
  --data "usage events, user id after consent" --region eu-central-1 --transfer scc --us-controlled --by module-add
```

OpenPanel self-hosted is not a sub-processor (it runs on your infrastructure); its cloud is
`--name OpenPanel --region fsn1 --transfer scc --eu-alternative`.

## Environment variables

Append to `.env.local.example`, per level used:

```
# advanced — PostHog EU (https://eu.posthog.com, project settings)
NEXT_PUBLIC_POSTHOG_KEY=phc_xxx
POSTHOG_KEY=phc_xxx
# product — also record from Vercel preview deployments (default: production and local dev only)
ANALYTICS_DEV=
```

`traffic` and `product` need no keys.

## Verification

```bash
pnpm typecheck
pnpm build
pnpm tsx -e "import('./lib/analytics/track').then(m => m.track('test-user', 'invoice_sent'))"
pnpm metrics      # the two tables, with the test user in this week's cohort
```

`traffic` shows up in the Vercel dashboard after the first production deploy.

## Update meta.json

Add the level to the list; never remove another:

```json
{ "stack": { "analytics": ["traffic", "product"] } }
```

With `advanced`, also `"analytics_provider": "posthog"` (or `"openpanel"`).

## Known caveats

- **Vercel custom events need the Pro plan.** `product` does not use them, so Hobby is enough.
- **Retention needs a stable id.** `product` uses the signed-in user's id; anonymous visitors are counted by
  `traffic` and are not part of D7/D30.
- **`@posthog/next` defaults to the US host.** Always write `eu.i.posthog.com`.
- **Do not name the proxy path `/analytics`** — ad blockers match it.
- **`track()` never throws.** It records in production and in local development (where `VERCEL_ENV` is unset),
  and skips Vercel previews unless `ANALYTICS_DEV=1`, so a preview's test clicks do not count as users.
- **Expo apps** use `rn-module-add analytics`; in a monorepo the event list lives in the shared package so web
  and mobile cannot drift.
