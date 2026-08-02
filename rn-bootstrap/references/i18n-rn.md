# i18n — i18next + react-i18next + expo-localization (Expo / React Native)

The **how**, not just "use i18next". Doc-grounded (docs.expo.dev, i18next.com, react.i18next.com) so we scaffold it right the first time. Golden rule 2: every frontend ships i18n from day one, minimum locales **en + it**, `stack.locales = ["en","it"]`, default `en`, **zero hardcoded user-facing strings**. Web sibling: `design-md-to-app/references/i18n-next-intl.md`.

Verified versions (npm registry, 2026-08-02) — `[VERIFY]` on every bump:

| Package | Version | Install with |
|---|---|---|
| `expo-localization` | `57.0.1` (SDK 57 line) | `npx expo install` |
| `i18next` | `26.3.6` | `npm install` |
| `react-i18next` | `17.0.11` | `npm install` |
| `@formatjs/intl-pluralrules` | `6.3.13` | `npm install` |
| `@react-native-async-storage/async-storage` | `3.1.1` | `npx expo install` |

## Library choice

Expo's localization guide does **not** crown one winner: its worked example uses `i18n-js`, and it lists as alternatives **Lingui**, **fbtee**, **React i18next** ("stable, well-maintained library based on i18next") and **Intlayer**. So "i18next is the officially recommended path" is *not* something the docs say — `[VERIFY]` if you ever cite it that way.

Our default is **i18next + react-i18next** anyway, deliberately:

- **i18next + react-i18next** ← *dev-flow default*. Namespaces, plurals, Intl-backed formatters, runtime `changeLanguage`, same mental model as the web side.
- **expo-localization + i18n-js** — the guide's own minimal example. Fine for a throwaway demo; no namespaces, thinner plural/format story.
- **Lingui** — macro/extractor-based, compile-time catalogs, smaller runtime. Pick it when the team wants extraction from source instead of hand-maintained key files.
- **fbtee / Intlayer** — also listed by Expo (Intlayer: per-component, extractor, bundle-size focus). Niche; only on explicit request.

## ⚠️ The gotcha: Hermes has no `Intl.PluralRules` — plurals silently degrade

Hermes gives you `Intl` on all platforms (Expo guide: "If you're using Hermes in your app, you can use the `Intl` API on all platforms"), **but `Intl.PluralRules` is still unimplemented** — `facebook/hermes#1462` is open as of this writing (`[VERIFY]`, it may land). i18next's docs are blunt: "In environments without Intl.PluralRules support you need to polyfill it (notably React Native: the Hermes engine still does not implement `Intl.PluralRules`)" and "Since i18next v24 there is no fallback: without Intl only English-style `_one`/`_other` forms resolve."

The old escape hatch is gone too: in i18next 26 the type for `compatibilityJSON` accepts **only `'v4'`** — `compatibilityJSON: 'v3'` is no longer valid. So: **polyfill, always**, imported *before* the init runs, using `/polyfill-force` because "The polyfill conditional detection code runs very slowly on Android" (FormatJS).

Symptom if you skip it: en/it look fine (both `one`/`other`), then you add `ru`/`pl`/`ar` and every plural silently falls back to the English shape. That's why it goes in at scaffold, not later.

## Install

```bash
# native modules → npx expo install (pins an SDK-57-compatible version)
npx expo install expo-localization @react-native-async-storage/async-storage

# pure JS → npm
npm install i18next react-i18next @formatjs/intl-pluralrules
```

Add the config plugin (required for the localization module's build-time config):

```json
// app.json
{ "expo": { "plugins": ["expo-localization"] } }
```

## Locale files — `locales/en.json`, `locales/it.json`

Mirror the keys exactly. One file per locale, namespaced by top-level object (default namespace is `translation`).

```jsonc
// locales/en.json                        // locales/it.json mirrors every key
{
  "common":  { "cancel": "Cancel", "save": "Save" },
  "home":    {
    "title": "Hello, {{name}}!",          // interpolation: {{var}}
    "items_one": "{{count}} item",        // i18next JSON v4 plural suffixes
    "items_other": "{{count}} items",
    "updated": "Updated {{date, datetime(dateStyle: medium)}}",
    "total":   "{{amount, currency(currency: EUR)}}"
  }
}
```

Plural suffixes are `_zero | _one | _two | _few | _many | _other` per CLDR category, and "The variable name must be `count`. And it must be present: `i18next.t('key', {count: 1});`".

## The init module — `lib/i18n.ts`

```ts
// lib/i18n.ts — side-effectful: importing this module configures i18next.
import '@formatjs/intl-pluralrules/polyfill-force';   // MUST come before i18next init
import '@formatjs/intl-pluralrules/locale-data/en';
import '@formatjs/intl-pluralrules/locale-data/it';

import { getLocales } from 'expo-localization';
import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';
import AsyncStorage from '@react-native-async-storage/async-storage';

import en from '../locales/en.json';
import it from '../locales/it.json';

export const LOCALE_KEY = 'app.locale';
export const supportedLngs = ['en', 'it'] as const;
export const defaultNS = 'translation';
export const resources = {
  en: { translation: en },
  it: { translation: it },
} as const;

// getLocales() is synchronous and "Guaranteed to contain at least 1 element".
const deviceLng = getLocales()[0]?.languageCode ?? 'en';

i18n
  .use(initReactI18next)          // "passes the i18n instance to react-i18next"
  .init({
    resources,
    defaultNS,
    lng: supportedLngs.includes(deviceLng as any) ? deviceLng : 'en',
    fallbackLng: 'en',            // i18next's own default is 'dev' — always set this
    supportedLngs,
    interpolation: { escapeValue: false },  // React already escapes; escapeValue defaults to true
  });

/** Apply the user's stored choice, if any. Call once at startup. */
export async function restoreStoredLocale() {
  const stored = await AsyncStorage.getItem(LOCALE_KEY);
  if (stored && stored !== i18n.language && (supportedLngs as readonly string[]).includes(stored)) {
    await i18n.changeLanguage(stored);
  }
}

/** Change language and persist it. */
export async function setLocale(lng: (typeof supportedLngs)[number]) {
  await i18n.changeLanguage(lng);
  await AsyncStorage.setItem(LOCALE_KEY, lng);
}

export default i18n;
```

**Storage: AsyncStorage, not SecureStore.** A language preference is not a secret. AsyncStorage is documented as "an asynchronous, **unencrypted**, persistent, key-value storage API" — exactly right here. `expo-secure-store` encrypts but exists for tokens/credentials; its docs warn that "Large payloads can be rejected by the underlying platform" (~2048 bytes historically on iOS) and that its sync methods "block the JavaScript thread". Overkill for a two-letter string.

## Where to import it — `app/_layout.tsx`

The root layout is the Expo Router entry point: it "is rendered before any other route in your app" and is where init code that used to live in `App.jsx` goes (fonts, theme providers, splash screen). Import `lib/i18n` **first**, so i18next is configured before any screen calls `useTranslation`.

```tsx
// app/_layout.tsx
import '../lib/i18n';                       // side-effect import — must be first
import { useEffect, useState } from 'react';
import { Stack } from 'expo-router';
import { restoreStoredLocale } from '../lib/i18n';

export default function RootLayout() {
  const [ready, setReady] = useState(false);
  useEffect(() => { restoreStoredLocale().finally(() => setReady(true)); }, []);
  if (!ready) return null;                  // or keep the splash screen up
  return <Stack />;
}
```

Resources are bundled (no HTTP backend), so translations resolve synchronously and you do **not** need `<Suspense>`. If you ever add a backend, either wrap in `<Suspense>` or pass `useSuspense: false` and gate on the returned `ready` flag.

## Usage

```tsx
import { useTranslation } from 'react-i18next';
import { Text } from 'react-native';

export default function Home({ name, count }: { name: string; count: number }) {
  const { t, i18n } = useTranslation();                       // default namespace
  // useTranslation('home') | useTranslation(['home','common'])         // one / several namespaces
  // useTranslation('translation', { keyPrefix: 'home' })               // nested prefix
  return (
    <>
      <Text className="text-xl">{t('home.title', { name })}</Text>
      <Text>{t('home.items', { count })}</Text>
    </>
  );
}
```

- Interpolation: `{{what}}` in the message, values as the second arg — `i18next.t('key', { what: 'i18next' })`.
- Plurals: pass `count`; i18next picks `_one` / `_other` / … via `Intl.PluralRules` (polyfilled above).
- Never build a sentence by concatenating `t()` calls — one key per sentence, variables via interpolation.

## Formatting dates / numbers / currency

Use i18next's **built-in Intl-backed formatters** (since v21.3): `number`, `currency`, `datetime`, `relativetime`, `list`. Syntax inside the message:

```
"{{val, number}}"
"{{val, number(minimumFractionDigits: 2)}}"      // semicolon-delimited option list
```

Options can also come from `t('key', { formatParams: { val: { minimumFractionDigits: 3 } } })`. Custom formatters: `i18next.services.formatter.add('lowercase', (value, lng, options) => value.toLowerCase())` — "Make sure you add your custom format function AFTER the i18next.init() call."

Raw `Intl` works too under Hermes; the Expo guide notes that passing `default` as the locale string makes `Intl` use the device's locale, "so you don't need to rely on `expo-localization`". But `Intl` "do[es] not provide information about the device or current locale" — for locale *data* (currency code, separators, units, first weekday) read `expo-localization`:

```ts
import { getLocales, getCalendars } from 'expo-localization';
const { languageTag, languageCode, regionCode, textDirection,
        digitGroupingSeparator, decimalSeparator, measurementSystem,
        currencyCode, currencySymbol, temperatureUnit } = getLocales()[0];
const { calendar, timeZone, uses24hourClock, firstWeekday } = getCalendars()[0];
```

`useLocales()` / `useCalendars()` are the hook forms — they re-render when the user changes OS settings. **Never hand-format** a date or a price.

## Changing language at runtime

`i18n.changeLanguage('it')` (or our `setLocale`) — react-i18next re-renders every component subscribed via `useTranslation`; no reload needed. Persist the choice (see `setLocale`) or the app snaps back to the device locale on next launch. Strings captured outside a component (module-level constants, `t()` called at import time) will **not** update — always call `t` inside render.

## RTL

Layout direction follows React Native's `I18nManager`. `I18nManager.isRTL` is "A boolean value indicating whether the app is currently in RTL layout mode"; `allowRTL(bool)` and `forceRTL(bool)` are documented as taking effect "on the next application start, not immediately" and being "persisted across app restarts". Hence the Expo guide's override:

```tsx
if (shouldBeRTL !== I18nManager.isRTL && Platform.OS !== 'web') {
  I18nManager.allowRTL(shouldBeRTL);
  I18nManager.forceRTL(shouldBeRTL);
  Updates.reloadAsync();          // expo-updates — the flip needs a reload
}
```

`[VERIFY] SDK boundary`: the Expo guide's RTL section says it "describes the behavior in **SDK 58 and later**. On previous versions, RTL support was enabled by default, except in Expo Go where it was disabled." We are on **SDK 57** → RTL is on by default but **disabled inside Expo Go**; test RTL in a dev build. The plugin props `supportsRTL: false` / `forcesRTL: true` appear on the unversioned guide but are **not** in the SDK 57 API reference — `[VERIFY]` against your installed `expo-localization` first.

en + it are both LTR, so RTL is dormant for the default set — but write layouts with `start`/`end` (not `left`/`right`) so adding `ar`/`he` is a locale-file job, not a re-layout.

## TypeScript (cheap, do it)

```ts
// i18next.d.ts — typed keys for t(); needs `strict` (or strictNullChecks) in tsconfig, TS ≥ 5
import { resources, defaultNS } from './lib/i18n';
declare module 'i18next' {
  interface CustomTypeOptions {
    defaultNS: typeof defaultNS;
    resources: (typeof resources)['en'];
  }
}
```

## Integration in dev-flow

- Wired at **scaffold** by `rn-bootstrap` — records `stack.i18n = "i18next"` and `stack.locales = ["en","it"]` (default `en`) in `.workflow/meta.json`.
- Every screen produced by `rn-add-screen` uses `useTranslation` keys; **no inline user-facing strings**, ever. Add the key to *both* `locales/en.json` and `locales/it.json` in the same edit — a missing `it` key falls back to English and ships as a silent regression.
- `rn-module-add` copy (auth errors, payment states, push permission prompts) goes through keys too.
- Mirrors the web side: same golden rule, same locale set, different library (`next-intl` there, `i18next` here).
