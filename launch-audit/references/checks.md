> Sources: Next.js App Router metadata (`node_modules/next/dist/docs/`, the version-matched copy the
> framework ships) · Directive 2000/31/EC Art. 5 (see `identity-block.md`) · the checks `shadscan`
> already owns, read from `shadscan/SKILL.md` so this file does not duplicate them.
> Written **2026-09-13**.

# The checks — what each looks for, and how it is wrong

Every check here **produces a signal**. The script cannot read intent, so each entry below names the
legitimate reason a finding might be nothing. Read the code before reporting one.

The rule this file exists to enforce: **a finding nobody can dismiss with a reason is a finding that
stops being read.** Three false positives and the whole report becomes noise.

---

## Findable

### `route-title-missing` · `route-description-missing`
**Looks for**: a public route whose `page.tsx` exports neither `metadata` nor `generateMetadata`, and
whose segment has no `layout.tsx` supplying one.

**Legitimately fine when**: the route is a redirect, an API-shaped page, or a segment that inherits a
title from a parent layout *on purpose* (a docs section where the layout builds `%s | Docs`). Next
resolves metadata up the segment tree — a missing export is not a missing title.

**Routes to**: `screenshot-to-page`.

### `robots-blocks-everything`
**Looks for**: `Disallow: /` with no qualification, or `robots.ts` returning `{ rules: { disallow: "/" } }`.

**Why it is first on the list**: this is the launch failure that looks like nothing is wrong. The
site is up, it is fast, it is beautiful, and it is invisible for as long as nobody thinks to check.
It arrives by being copied from staging.

**Legitimately fine when**: the deploy genuinely is staging. Check `NODE_ENV`/`VERCEL_ENV` branching
before reporting — a `robots.ts` that disallows everything except in production is correct.

### `sitemap-missing-routes`
**Looks for**: public routes in `app/` that the sitemap does not list.

**Legitimately fine when**: they are behind auth, they are `noindex` on purpose, or they are
`(marketing)` route-group duplicates of a canonical URL. Authenticated routes **should** be absent —
report only the public ones.

### `internal-route-indexable`
**Looks for**: the mirror image of the check above — a route that should **not** be found, and is.
A whole segment named `showcase`, `styleguide`, `design-system`, `playground`, `sandbox`, `debug`,
`internal`, `dev`, `test`, `preview` or `kitchen-sink`, served publicly with no `noindex` in its
metadata chain and no mention in `robots`.

**Why it is not covered by the others**: every other findable check asks whether a page *can* be
found. This one exists because annotix shipped `/showcase` — the living reference for its
`DESIGN.md`, complete with sample copy and component states — as a public 200 that any crawler could
index. The title check passed it (it inherits one from the root layout) and the sitemap check passed
it (it is correctly absent). Nothing looked at it.

**Legitimately fine when**: the segment is the product — `/playground` on a developer tool, `/demo`
on a SaaS. Matching is whole-segment, so `/developers` is not `/dev` and `/testimonials` is not
`/test`; a real hit means the word *is* the segment.

**Routes to**: `screenshot-to-page` — a `robots` line or `export const metadata = { robots: { index: false } }`.

### `favicon-incomplete`
**Looks for**: `app/icon.*` / `favicon.ico`, and `apple-icon.*` for the iOS home screen.

**Legitimately fine when**: an internal tool nobody bookmarks. Say that out loud rather than fixing it.

### `social-preview-broken`
`shadscan`'s `social-preview-present` checks the **file exists**. This checks it **resolves and has
dimensions** — an `opengraph-image.tsx` that throws at build renders a grey box in every share, and
file-existence cannot see that.

**Legitimately fine when**: never, really. A broken OG image has no upside.

---

## Trustworthy

### `privacy-page-missing` · `terms-page-missing`
**Looks for**: a route and a link to it from the layout footer.

**Legitimately fine when**: an internal tool with no external users (privacy); no money changes hands
and there is no account (terms).

⚠️ **A dynamic route serves the slugs it pre-renders.** `legal/[page]` with
`generateStaticParams` over `["privacy", "terms", …]` *is* the privacy page, and the scanner reads
those literals and shows them as the evidence. This is the regression annotix found: matching the
route string alone produced the two most alarming findings this skill can make, both false.

It follows **one import hop**, because the list leaves the page the moment the sitemap needs it too —
fixing the sitemap finding on annotix moved `LEGAL_PAGES` into `lib/legal-pages.ts` and both false
findings came straight back. The hop is local modules only (`./x`, `@/x`), and only those whose
imported binding actually appears inside the `generateStaticParams` body: follow every import and an
unrelated array two files away turns a genuinely missing privacy page into a silent pass, which is
the worse failure.

Two hops, a fetch, or a computed list leave the check reporting `missing`. **A slug it cannot see is
a slug it must not claim exists** — the conservative direction here is to keep crying wolf, not to
stop.

**Routes to**: `screenshot-to-page` for the page, **the user** for the words. Generated terms of sale
are a liability, not a deliverable — see `identity-block.md`.

⚠️ **Do not restate `compliance-audit`.** It asks whether the handling is lawful; this asks whether a
page exists. Both, never one instead of the other.

### `identity-block-missing`
**Looks for**: a legal/imprint route, linked from every page, containing the Article 5 items.

**Legitimately fine when**: the company is established outside the EU **and** does not offer services
into it. Establishment is the test, not where the server is.

**Routes to**: **the user**, always. This skill never writes a registration number.

---

## Convertible

### `no-cta-above-the-fold`
**Looks for**: on the landing route, an anchor or button leading to the primary action (sign-up,
purchase, contact, demo) within the first viewport.

**Legitimately unreliable**, and this is the check most likely to be wrong: "above the fold" is a
rendered-layout property and the script reads source. A CTA inside a `<Hero>` component it did not
resolve looks missing. **Verify in a browser before reporting** — and that is cheap now, because
`agent-browser` or the preview can answer it in one screenshot.

### `cta-unreachable-on-mobile`
**Looks for**: the same CTA, at a 375px viewport, still within the first screen.

This is the one worth checking by rendering rather than reading. A hero that is one screen on a
laptop is three on a phone, and the button lands under the fold on the device where most traffic is.

### `cta-target-missing`
**Looks for**: a CTA whose `href` does not match any route in `app/`.

**Legitimately fine when**: it is an external URL, an anchor (`#pricing`), or a dynamic segment the
matcher did not expand. Everything else is a dead button on the most important element of the page.

### `form-without-confirmation`
**Looks for**: a form that submits with no success route, no success state, no `router.push` /
`router.refresh`, and no toast.

**Legitimately fine when**: the success state is inline and the script did not resolve it — common
with `useActionState`. Read the component.

⚠️ **Two ways this used to be wrong, both found on annotix, six findings and six false.** A
`<form>` matcher anchored on `<form\b` also matches `<form.Field>` and `<form.Subscribe>` — TanStack
Form's render-prop components — so every primitive in a form toolkit read as a form with no success
path. And `router.refresh()` after an in-place settings save **is** the confirmation: demanding a
confirmation *page* there would be asking for a regression.

**Routes to**: `forms`, which owns submit-state discipline.

### `analytics-absent`
**Looks for**: any analytics wiring at all.

**Legitimately fine when**: deliberately not measuring — a privacy-forward product may decide this,
and that is a decision, not an oversight. Record it in `dismissed` with the reason.

**Routes to**: `module-add`.

---

## What this file deliberately does not check

Owned elsewhere, and re-checking them would produce two reports that disagree:

| | Owner |
|---|---|
| alt text, focus rings, labels, empty and loading states, `not-found` route | `shadscan` |
| lawful basis, consent capture, retention, DSAR, transfers, sub-processors | `compliance-audit` |
| image weight, LCP, function cost, bandwidth | `vercel-doctor` |
| whether the build matches the PRD | `spec-review` |

When a finding lands in one of those, this skill **names the owner and stops**. It does not offer a
second opinion.
