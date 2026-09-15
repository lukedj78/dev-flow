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

React Email 6.0 unified the components, render, and preview CLI into a single `react-email` package — `@react-email/components` is deprecated (`npm i react-email`). Import template primitives from `"react-email"`, including `render` and `Tailwind`.

> **Checked 2026-09-15** on a real project (Hostitaly): `resend@6.28.1`, `react-email@6.9.5`, the emailcn
> registry at `https://emailcn.run/r/registry.json` (338 items), better-auth 1.7.5.

## Templates: emailcn first, then hand-written — always React Email with `<Tailwind>`

⚠️ **Two rules, both learned by breaking them.**

1. **Styles go through React Email's `<Tailwind>` component.** Not inline `style={{}}` objects, and **never a
   design-lint exemption added to make inline styles pass**. `<Tailwind>` inlines the classes at render time
   (a rendered verification email came out with 16 `style=` attributes and zero `class=`), so the output is
   as email-safe as hand-written inline styles, while the source stays reviewable and on the token scale.
   An agent that hits a lint conflict in `emails/` **stops and asks** — an exemption is a deviation from this
   reference, not an implementation detail.
2. **Look in emailcn before writing a template.** Ecosystem-first, same as maps → mapcn.

### emailcn — the shadcn-format registry of email blocks

[emailcn](https://www.emailcn.run) ships React Email (also MJML React and JSX Email) components and blocks
styled with Tailwind through a theme object. It is a **third-party registry**, so it goes through
`registry-intake`, never a direct `shadcn add`:

```bash
S=<skills>/registry-intake/scripts/registry_intake.py
python3 $S review  <root> @emailcn/react-email/block-auth-magic-link-default --registry '@emailcn=https://emailcn.run/r/{name}.json'
python3 $S allow   <root> @emailcn 'https://emailcn.run/r/{name}.json' --reason "transactional email blocks" --by <user>
python3 $S approve <root> @emailcn/react-email/block-auth-magic-link-default --by <user>
python3 $S install <root> @emailcn/react-email/block-auth-magic-link-default -- --yes
```

What is actually there (read from `registry.json`, not from the marketing page, which lists neither names nor
the registry URL):

| Need | Item (`react-email/…`) | Note |
|---|---|---|
| Magic link | `block-auth-magic-link-default` (also `-raycast`, `-stripe`) | |
| One-time code | `block-auth-otp-default` (also `-twitch`) | |
| Password reset | `block-auth-password-reset-default` (also `-dropbox`, `-notion`) | |
| Invitation | `block-invite-default` (also `-vercel`) | |
| **Email verification** | **none** | derive your own `auth-verify-email.tsx` from the magic-link block (same shape: heading, body, one button, expiry), same project theme, its own copy |
| Theme | `theme-default`, `theme-<brand>` (airbnb, apple, linear, notion, stripe, vercel…) | a `registryDependency` of every block |
| Fonts | `default-fonts` (Inter), `tech-fonts` (Geist), … | `<Head>` helpers |

What an install brings, and what to change before shipping:

- **Files land in `components/email/`** (`<block>.tsx`, `email-theme.ts`, `theme-<id>.ts`, `email-assets.ts`),
  not in `emails/`. Point `email dev --dir` at the folder you keep.
- **Theme = an `EmailTheme` object** passed to `createEmailTailwindConfig(theme)` inside `<Tailwind config>`.
  **Author a project theme from DESIGN.md tokens** (`components/email/theme-<project>.ts`) and switch the
  import; never ship `theme-default` (generic grey) or a brand-lookalike theme (`theme-stripe`, `theme-linear`
  — copying another company's look is exactly the generic output the design rules forbid).
- **Copy is hard-coded English** (`"Sign in to {_productName}"`). Golden rule 2 applies to emails: turn every
  string into a prop and fill it from i18n messages in the sender.
- **`email-assets.ts` points at remote image hosts** (emailcn.run, Unsplash, icons8, picsum, placehold.co) —
  `registry-intake` reports it as S4. They serve previews. **Never send remote images you do not own**: a
  third-party image in an email is an open-tracking beacon for that host (GDPR). Host your logo yourself or
  send none.
- `[VERIFY]` whether the project's design-system lint recognises the theme's class names (`bg-bg`,
  `text-foreground-muted`, `text-primary-fg`…). If it flags them, ask before exempting `components/email/`.

### Writing one by hand

When no block fits, keep the same shape: `<Tailwind config={…}>` around the document, a Tailwind config built
from DESIGN.md tokens with `pixelBasedPreset`, and **the app's own token names** (`surface`, `on-surface`,
`primary`, `primary-foreground`…) so the design lint recognises the classes — with literal hex values, because
email clients read neither CSS variables nor `globals.css`. Give every template `PreviewProps` for `email dev`.

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

## Testing without real recipients

- **Resend's shared test sender (`onboarding@resend.dev`) only delivers to the Resend account owner's own
  address.** Until a domain is verified, a send to anyone else is rejected; say so in the hand-off.
- **Use Resend's test inboxes to prove the API path without writing to a person**: `delivered@resend.dev`
  (accepted and delivered), `bounced@resend.dev` (hard bounce). A real send to `delivered@resend.dev` is a
  better verification than "it compiles".
- **Render and check the HTML** with `await render(element)` and `await render(element, { plainText: true })`
  (both from `react-email`); send both `html` and `text`.
- **Verify the key without sending**: `resend.domains.list()` returns the account's domains (an empty list is
  fine) or an auth error.

## Authentication emails (better-auth)

- Send verification and magic-link emails from the auth config callbacks through one function
  (`sendAuthEmail({ kind, to, url })`), not from pages.
- **Locale**: the link carries the `callbackURL` of the page that started the flow (`/it/today`); read the
  first segment, check it against the locale list, then load messages. Never build an import path from an
  unchecked segment.
- **Local development** may also print the link to the server log (only when no `VERCEL_ENV` is set);
  **deployed without `RESEND_API_KEY` the flow must fail**, never succeed silently with the link lost.
- **Errors never contain the link or the address**: the link is a credential, the address personal data.
- The dev redirect (`RESEND_DEV_TO`) must be off in production by an explicit check
  (`VERCEL_ENV === "production"`), not only by `NODE_ENV`: preview deployments also run with
  `NODE_ENV=production`.

## Inbound email and webhooks

Resend delivers inbound email and delivery events as signed webhooks (Svix).

```typescript
// app/api/webhooks/resend/route.ts
const payload = await request.text() // the raw body: parsing first breaks the signature
const event = new Resend(apiKey).webhooks.verify({
  payload,
  headers: {
    id: request.headers.get("svix-id") ?? "",
    timestamp: request.headers.get("svix-timestamp") ?? "",
    signature: request.headers.get("svix-signature") ?? "",
  },
  webhookSecret,
})
```

- `verify` takes **an object of the three Svix headers**, not the `Headers` instance (a type error at 6.28.1).
- **The SDK constructor needs `RESEND_API_KEY` even to verify**: check both settings up front, answer `503` and
  log which one is missing; otherwise a missing key surfaces as `invalid_signature` with nothing in the logs.
- Fail closed: no secret → `503`; bad signature → `400`, logging only the error kind.
- Log the **event type only**: payloads carry addresses and message bodies.
- If the table that stores inbound messages does not exist yet, acknowledge verified events without storing
  or logging content, and say so.

## Layered projects

When adapters live in a layer that may not import React (for example `src/integrations/**` under an
import-boundary lint), **render in the caller and pass `html` + `text` through the port**. The provider adapter
then depends on nothing but the SDK, and the template stays with the UI code.

## Environment variables

Append to `.env.local.example`:

```
# Resend — sign up at https://resend.com (free tier: 3000 emails/month)
RESEND_API_KEY=re_xxx
RESEND_FROM_EMAIL=onboarding@yourdomain.com
# In dev/staging, all outgoing emails get redirected here. Leave empty in prod.
RESEND_DEV_TO=your-personal-email@gmail.com
# Signing secret of the Resend webhook (inbound email, delivery events)
RESEND_WEBHOOK_SECRET=whsec_xxx
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
- **Inbound email** (replies routed back to your app, e.g., for support): see §Inbound email and webhooks above for the verification; storing and routing the messages is product work.
- **Resend's EU region is a sending region chosen per domain** (`eu-west-1`), set when the domain is created; the account and API stay in the US. Record Resend in the sub-processor register with its transfer basis (`dev-flow/references/eu-data-sovereignty.md`).
- **Marketing email is a different module.** If the user asks for "newsletter" or "drip campaign", redirect them to a CRM (Loops, Customer.io). Same SDK shape, vastly different consent + deliverability requirements (CAN-SPAM, GDPR, double opt-in).
