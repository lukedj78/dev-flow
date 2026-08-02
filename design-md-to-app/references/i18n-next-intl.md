# i18n — next-intl (Next.js App Router)

The **how**, not just the "use next-intl". Doc-grounded (next-intl.dev, v3/v4) so we scaffold it right the first time. Golden rule 2: every frontend ships i18n from day one, minimum locales **en + it**. `[VERIFY]` every identifier against the installed next-intl version — this surface moves (e.g. `middleware.ts` was **renamed `proxy.ts`** in recent versions).

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
// proxy.ts  (project root — formerly middleware.ts; [VERIFY] the filename for your version)
import createMiddleware from 'next-intl/middleware';
import {routing} from './i18n/routing';

export default createMiddleware(routing);

export const config = {
  // run on everything except api, static, and files with an extension
  matcher: '/((?!api|trpc|_next|_vercel|.*\\..*).*)',
};
```

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

```tsx
// app/[locale]/layout.tsx — the locale segment root
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

Call `setRequestLocale(locale)` in **every** layout/page that renders translations, and add `generateStaticParams` (above). next-intl uses `cache()` to pass the locale without a `headers()` call, so pages stay statically renderable. Skip `setRequestLocale` → the route silently becomes dynamic.

## Without i18n routing (delta)

Drop `[locale]` segment, `routing.ts`, `navigation.ts`, and `proxy.ts`. `i18n/request.ts` returns a fixed/cookie-derived `locale`. Put `<NextIntlClientProvider>` in `app/layout.tsx`. Use plain `next/link`. Switch locale by writing a cookie + `revalidate`. Everything else (`useTranslations`, `getTranslations`, formatting) is identical.

## Integration in dev-flow

- Wired at **scaffold** by `design-md-to-app` (full-scaffold mode) — `stack.i18n="next-intl"`, `stack.locales=["en","it"]`.
- `forms` routes **all** form copy (labels, placeholders, errors via `mapFormError`) through `useTranslations` keys — never inline strings.
- Never hardcode a user-facing string anywhere; add the key as you write the component.
