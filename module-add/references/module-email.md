# module-add → `email` (Resend + React Email)

Wire **Resend** for transactional emails (welcome, password reset, receipt, alert) using **React Email** for templates. Defaults: a single `sendEmail()` helper, one welcome template as reference, dev-mode redirect to a test address to prevent accidental emails to real users.

This is **transactional email only**. Marketing/newsletters belong in a CRM (Loops, Customer.io, Klaviyo) — different consent model, different deliverability profile, different abuse vectors. Don't mix the two through the same channel.

## Idempotency check

Before doing anything, check whether email is already wired:

1. `<project-root>/package.json` contains `"resend"` and `"react-email"` in dependencies.
2. `<project-root>/lib/email.ts` exists.
3. `<project-root>/emails/` directory exists (template folder).
4. `<project-root>/.env.local.example` contains `RESEND_API_KEY`.

If all four: tell the user it's installed, offer to add a new template or rotate the API key. Don't double-install.

## Prerequisites

None hard-required. Works standalone — but most projects send email *for* something, so realistically you'll have run `module-add auth` first (welcome emails, password resets).

## Install

```bash
cd <project-root>
pnpm add resend react-email
```

React Email 6.0 unified the components, render, and preview CLI into a single `react-email` package — `@react-email/components` is deprecated (`npm i react-email`). Import template primitives from `"react-email"`.

## Files to write

### `lib/email.ts`

```typescript
import { Resend } from "resend";
import { env } from "@/lib/env";
import type { ReactElement } from "react";

const resend = new Resend(env.RESEND_API_KEY);

/**
 * Send a transactional email.
 *
 * Three rules baked in:
 *   1. In non-production, redirect ALL outgoing mail to RESEND_DEV_TO if set.
 *      Without this, a forgotten test triggers a real email to a real user
 *      the first time you run a backfill in staging.
 *   2. Always include a `tag` so Resend's dashboard groups deliveries by
 *      template — needed when you debug a deliverability dip.
 *   3. Return `{ ok: false, error }` on failure; never throw across the
 *      server-action boundary. Mirrors the lib/server/<domain>.ts convention.
 *
 * Usage:
 *   await sendEmail({
 *     to: "user@example.com",
 *     subject: "Welcome",
 *     react: <WelcomeEmail name="Marco" />,
 *     tag: "welcome",
 *   });
 */
type SendEmailParams = {
  to: string | string[];
  subject: string;
  react: ReactElement;
  tag: string;
  replyTo?: string;
};

type SendEmailResult =
  | { ok: true; id: string }
  | { ok: false; error: string };

export async function sendEmail(params: SendEmailParams): Promise<SendEmailResult> {
  const isProd = process.env.NODE_ENV === "production";
  const devTo = env.RESEND_DEV_TO;

  // Redirect in non-prod to prevent leaking real customers.
  const to =
    !isProd && devTo
      ? Array.isArray(devTo) ? devTo : [devTo]
      : Array.isArray(params.to) ? params.to : [params.to];

  try {
    const result = await resend.emails.send({
      from: env.RESEND_FROM_EMAIL,
      to,
      subject: !isProd ? `[${process.env.NODE_ENV ?? "dev"}] ${params.subject}` : params.subject,
      react: params.react,
      replyTo: params.replyTo,
      tags: [{ name: "template", value: params.tag }],
    });

    if (result.error) {
      return { ok: false, error: result.error.message };
    }

    return { ok: true, id: result.data?.id ?? "" };
  } catch (e) {
    const message = e instanceof Error ? e.message : "unknown error";
    return { ok: false, error: message };
  }
}
```

### `emails/welcome.tsx` (reference template)

```tsx
import {
  Body,
  Container,
  Head,
  Heading,
  Html,
  Link,
  Preview,
  Section,
  Tailwind,
  Text,
} from "react-email";

/**
 * Welcome email — minimal reference template.
 *
 * Uses react-email, which renders to HTML compatible with the
 * lowest-common-denominator email clients (Gmail, Outlook 2007+, Yahoo).
 * The `Tailwind` wrapper lets you use a subset of Tailwind classes that get
 * inlined at render time — DON'T expect arbitrary CSS to work.
 */
type WelcomeEmailProps = {
  name: string;
  ctaUrl: string;
};

export function WelcomeEmail({ name, ctaUrl }: WelcomeEmailProps) {
  return (
    <Html>
      <Head />
      <Preview>Welcome to the platform — let&apos;s get you started.</Preview>
      <Tailwind>
        <Body className="bg-white font-sans">
          <Container className="mx-auto max-w-[560px] px-6 py-10">
            <Heading className="text-[28px] font-semibold text-neutral-900">
              Welcome, {name}.
            </Heading>
            <Text className="text-[16px] text-neutral-700 leading-relaxed">
              Thanks for joining. Your account is ready — pick up where you
              signed up by opening the dashboard.
            </Text>
            <Section className="mt-8">
              <Link
                href={ctaUrl}
                className="inline-block rounded-md bg-neutral-900 px-5 py-3 text-[14px] font-medium text-white no-underline"
              >
                Open dashboard
              </Link>
            </Section>
            <Text className="mt-12 text-[12px] text-neutral-500">
              If you didn&apos;t create this account, ignore this email — no
              further action is needed.
            </Text>
          </Container>
        </Body>
      </Tailwind>
    </Html>
  );
}

export default WelcomeEmail;
```

### Optional: `package.json` script for previewing templates

```json
{
  "email:dev": "email dev --dir emails"
}
```

`pnpm email:dev` opens a localhost preview at http://localhost:3000 (default port 3000 — pass `--port 3001` if it conflicts with your Next dev server) where every template in `emails/` is rendered live with hot-reload. Critical for iterating on layout — testing email rendering by sending real emails is slow and noisy.

### Wiring into a server action (example)

In `lib/server/users.ts` or wherever your sign-up flow lives:

```typescript
import { sendEmail } from "@/lib/email";
import { WelcomeEmail } from "@/emails/welcome";

// inside your createUser action, after the insert succeeds:
await sendEmail({
  to: user.email,
  subject: "Welcome to <project-name>",
  react: <WelcomeEmail name={user.name} ctaUrl={`${env.NEXT_PUBLIC_APP_URL}/dashboard`} />,
  tag: "welcome",
});
```

The send is **fire-and-forget** for transactional UX — you don't want the user's sign-up to fail because the email provider blipped. Log the `{ ok: false }` case to your monitoring; don't surface it to the user.

## Environment variables

Append to `.env.local.example`:

```
# Resend — sign up at https://resend.com (free tier: 3000 emails/month)
RESEND_API_KEY=re_xxx
RESEND_FROM_EMAIL=onboarding@yourdomain.com
# In dev/staging, all outgoing emails get redirected here. Leave empty in prod.
RESEND_DEV_TO=your-personal-email@gmail.com
```

Extend `lib/env.ts` to validate (Zod block):

```typescript
RESEND_API_KEY: z.string().startsWith("re_"),
RESEND_FROM_EMAIL: z.string().email(),
RESEND_DEV_TO: z.string().email().optional(),
```

Tell the user to:
1. Sign up at https://resend.com (free tier is enough to start).
2. **Verify a sending domain** (https://resend.com/domains): add the DNS records Resend gives you (DKIM + SPF). Without this, your emails go to spam from day one. The default `@resend.dev` domain works for testing but is not for production.
3. Get an API key from https://resend.com/api-keys.
4. Set `RESEND_FROM_EMAIL` to an address on your verified domain (e.g., `noreply@yourdomain.com`).
5. Put their personal email in `RESEND_DEV_TO` so dev/staging mail comes to them, not real users.

## Verification

After install + write:

```bash
pnpm typecheck
pnpm build
pnpm email:dev    # opens template preview
```

To send a real test email (requires real `RESEND_API_KEY` in `.env.local`):

```bash
pnpm tsx -e "
import { sendEmail } from './lib/email';
import { WelcomeEmail } from './emails/welcome';
sendEmail({
  to: process.env.RESEND_DEV_TO!,
  subject: 'Test',
  react: WelcomeEmail({ name: 'Test User', ctaUrl: 'https://example.com' }),
  tag: 'test',
}).then(console.log);
"
```

## Update meta.json

```json
{
  "stack": {
    "email": "resend"
  }
}
```

## Known caveats

- **Domain verification is the make-or-break step.** A verified domain with DKIM+SPF lands in inbox; an unverified one goes to spam. The user *will* skip this — flag it red in the hand-off message and re-flag every time they say "my emails aren't arriving".
- **The Tailwind subset in react-email is small.** Flex+grid work; transforms, animations, custom vars don't. Don't try to reuse your app's `globals.css` here — email CSS is a different beast.
- **Don't render emails from a client component.** Always invoke `sendEmail()` from server actions / route handlers / cron jobs. The Resend SDK works in client code but doing so leaks `RESEND_API_KEY` into your bundle.
- **One-off vs. fanout**: this reference handles one-off transactional sends. For batch (e.g., "notify 10k users about an outage"), use `resend.batch.send()` and respect the rate limit (10 req/s per key by default). For very high fanout, consider a queue (BullMQ + Redis, or Resend's webhook → SQS → worker pattern).
- **Inbound email** (replies routed back to your app, e.g., for support): Resend supports it via `addresses.create` + webhooks. Out of scope for this reference — open a separate `module-add` invocation when needed.
- **Marketing email is a different module.** If the user asks for "newsletter" or "drip campaign", redirect them to a CRM (Loops, Customer.io). Same SDK shape, vastly different consent + deliverability requirements (CAN-SPAM, GDPR, double opt-in).
