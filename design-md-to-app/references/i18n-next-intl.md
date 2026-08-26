# i18n — next-intl (Next.js App Router)

The **how**, not just the "use next-intl". Doc-grounded (next-intl.dev, v3/v4) so we scaffold it right the first time. Golden rule 2: every frontend ships i18n from day one, minimum locales **en + it**. Verified end-to-end against **`next-intl@4.13.7`** and **`next@16.3.3`** (2026-08-26). `[VERIFY]` again on upgrade — this surface moves, and it moves in ways that look cosmetic: the *project file* `middleware.ts` became `proxy.ts` (Next 16) while the *package subpath* `next-intl/middleware` did not.

## Decide the mode first

- **With i18n routing** (locale in the URL: `/en/…`, `/it/…`) — a top-level `[locale]` segment. **Default for public/marketing/SEO-facing sites** (shareable localized URLs, `hreflang`). More setup.
- **Without i18n routing** (single set of routes, locale resolved from cookie/header) — no `[locale]` segment. Good for **internal tools / apps behind auth** where the URL needn't carry the locale.

Pick per project; below is the **with-routing** setup (the fuller one) plus the without-routing delta.

## Install + plugin

```bash
pnpm add next-intl
```

```ts
// next.config.ts
import type {NextConfig} from 'next';
import createNextIntlPlugin from 'next-intl/plugin';

const nextConfig: NextConfig = {};
const withNextIntl = createNextIntlPlugin();   // points at ./i18n/request.ts by default
export default withNextIntl(nextConfig);
```

## The files (with i18n routing)

```ts
// i18n/routing.ts — single source of truth for locales
import {defineRouting} from 'next-intl/routing';

export const routing = defineRouting({
  locales: ['en', 'it'],     // golden-rule minimum; add more per project
  defaultLocale: 'en',
});
```

```ts
// i18n/navigation.ts — locale-aware navigation (use THESE, not next/link / next/navigation)
import {createNavigation} from 'next-intl/navigation';
import {routing} from './routing';

export const {Link, redirect, usePathname, useRouter, getPathname} =
  createNavigation(routing);
```

```ts
// proxy.ts  (project root — Next 16's new name for middleware.ts; see the note below)
import createMiddleware from 'next-intl/middleware';
import {routing} from './i18n/routing';

export default createMiddleware(routing);

export const config = {
  // run on everything except api, static, and files with an extension
  matcher: '/((?!api|trpc|_next|_vercel|.*\\..*).*)',
};
```

**Two names, and only one of them moved.** From `next@16.3.3`'s own shipped docs
(`dist/docs/…/file-conventions/proxy.md`): *"the `middleware` file convention is deprecated and has
been renamed to `proxy`"*, in **v16.0.0**. Both constants still exist in the build, so the old file is
recognised — deprecated, not removed — and there is a codemod:

```bash
npx @next/codemod@canary middleware-to-proxy .
```

Two things the rename drags along, and neither is cosmetic:

- **The exported function renames too** — `export function middleware()` → `export function proxy()`.
  Not an issue for the next-intl file above, which is a `export default createMiddleware(routing)`.
- **Proxy defaults to the Node.js runtime** (middleware defaulted to Edge), and the `runtime`
  config option **is not available in a Proxy file — setting it throws**. If you had pinned a runtime
  in `middleware.ts`, the codemod's rename is the easy half.

What did **not** rename is the **package subpath**: at `next-intl@4.13.7` the import is still
`createMiddleware from 'next-intl/middleware'`. Renaming that import because you renamed the file is
the mistake this note exists to prevent.

```ts
// i18n/request.ts — per-request config the plugin loads
import {getRequestConfig} from 'next-intl/server';
import {hasLocale} from 'next-intl';
import {routing} from './routing';

export default getRequestConfig(async ({requestLocale}) => {
  const requested = await requestLocale;
  const locale = hasLocale(routing.locales, requested) ? requested : routing.defaultLocale;
  return {
    locale,
    messages: (await import(`../messages/${locale}.json`)).default,
  };
});
```

> ⚠️ **On Next.js 16.3+ prefer `next/root-params`.** Next 16.3 exposes the root `[locale]` param to any
> server context, so you read it **once** in `i18n/request.ts` instead of threading a call through every
> layout and page.
>
> **Correction, verified against `next-intl@4.13.7` (2026-08-26): the deprecated thing is
> `requestLocale`, not `setRequestLocale`.** The `@deprecated` tag sits on the **`requestLocale` param of
> `getRequestConfig`** — *"Please migrate to `next/root-params`"* — while `setRequestLocale` is still
> exported clean from `next-intl/server` with no deprecation marker. This file previously named the wrong
> one, which sends you grepping for a symbol that still works and concluding the note is stale. What to
> remove is the `{requestLocale}` destructure below; what to keep working with is the export.
>
> ```ts
> // i18n/request.ts — Next 16.3+ form
> import * as rootParams from 'next/root-params';
> import {getRequestConfig} from 'next-intl/server';
> import {hasLocale} from 'next-intl';
> import {notFound} from 'next/navigation';
> import {routing} from './routing';
>
> export default getRequestConfig(async () => {
>   const paramValue = await rootParams.locale();
>   if (!hasLocale(routing.locales, paramValue)) notFound();
>   return {locale: paramValue, messages: (await import(`../messages/${paramValue}.json`)).default};
> });
> ```
>
> Then the layout keeps `generateStaticParams` (**still required**) but drops both `setRequestLocale` and the manual `hasLocale` check, reading the locale with `getLocale()` from `next-intl/server` for `<html lang>`.
>
> **Caveat:** `next/root-params` does **not** work in **Route Handlers or Server Actions** — pass the locale explicitly there and feed it into `getRequestConfig`. On Next 16.0–16.2 the `requestLocale` + `setRequestLocale` form above is still the correct one.

```tsx
// app/[locale]/layout.tsx — the locale segment root (Next 16.0–16.2 form;
// on 16.3+ drop setRequestLocale + the hasLocale check — see the root-params note above)
import {setRequestLocale} from 'next-intl/server';
import {hasLocale, NextIntlClientProvider} from 'next-intl';
import {notFound} from 'next/navigation';
import {routing} from '@/i18n/routing';

export function generateStaticParams() {
  return routing.locales.map((locale) => ({locale}));   // enables static rendering per locale
}

export default async function LocaleLayout({
  children, params,
}: {children: React.ReactNode; params: Promise<{locale: string}>}) {
  const {locale} = await params;                 // params is async in Next 16
  if (!hasLocale(routing.locales, locale)) notFound();
  setRequestLocale(locale);                       // MUST precede any useTranslations/getTranslations
  return (
    <html lang={locale}>
      <body>
        <NextIntlClientProvider>{children}</NextIntlClientProvider>
      </body>
    </html>
  );
}
```

```jsonc
// messages/en.json                     // messages/it.json mirrors the same keys
{ "HomePage": { "title": "Hello world!", "cta": "Get started" } }
```

## Using translations

```tsx
// Server Component (async) — preferred; pairs with the data-fetching "Server Components first" rule
import {getTranslations} from 'next-intl/server';
export default async function HomePage() {
  const t = await getTranslations('HomePage');
  return <h1>{t('title')}</h1>;
}

// Client Component
'use client';
import {useTranslations} from 'next-intl';
function Cta() {
  const t = useTranslations('HomePage');
  return <button>{t('cta')}</button>;
}
```

- **Navigation**: import `Link`, `redirect`, `useRouter`, `usePathname` from `@/i18n/navigation` (locale-aware), **never** from `next/link` / `next/navigation` in localized routes.
- **Formatting**: `useFormatter()` (`format.dateTime`, `format.number`, `format.relativeTime`, `format.list`) for locale-correct dates/numbers/currency — don't hand-format.
- **Rich text / plurals**: ICU syntax in the message (`{count, plural, one {# item} other {# items}}`), and `t.rich('key', {b: (c) => <b>{c}</b>})` for embedded markup.

## Static rendering

**Next 16.0–16.2:** call `setRequestLocale(locale)` in **every** layout/page that renders translations, and add `generateStaticParams` (above). next-intl uses `cache()` to pass the locale without a `headers()` call, so pages stay statically renderable; skipping it silently makes the route dynamic. **Next 16.3+:** `setRequestLocale` is deprecated — the `next/root-params` form above removes this whole footgun (one read in `i18n/request.ts`, nothing to forget per page). `generateStaticParams` is still required either way.

## Without i18n routing (delta)

Drop `[locale]` segment, `routing.ts`, `navigation.ts`, and `proxy.ts`. `i18n/request.ts` returns a fixed/cookie-derived `locale`. Put `<NextIntlClientProvider>` in `app/layout.tsx`. Use plain `next/link`. Switch locale by writing a cookie + `revalidate`. Everything else (`useTranslations`, `getTranslations`, formatting) is identical.

## Integration in dev-flow

- Wired at **scaffold** by `design-md-to-app` (full-scaffold mode) — `stack.i18n="next-intl"`, `stack.locales=["en","it"]`.
- `forms` routes **all** form copy (labels, placeholders, errors via `mapFormError`) through `useTranslations` keys — never inline strings.
- Never hardcode a user-facing string anywhere; add the key as you write the component.
