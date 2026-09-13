---
name: launch-audit
description: 'The fourth pre-deploy gate. `shadscan` asks whether the code is good, `compliance-audit` whether the data handling is lawful, `vercel-doctor` what it costs — this one asks **can a stranger find this, trust it, and buy from it?** Three surfaces nobody owns: **findable** (title + description on every route, robots, sitemap, favicon, social preview), **trustworthy** (privacy, terms, and the provider-identity block EU law requires on a commercial site), **convertible** (a CTA above the fold, reachable on mobile, a confirmation page after every form, analytics). Reports and routes; never blocks, never scores. Needs `stack.framework` in {next, monorepo} and `phase >= feature_complete`. Triggers: "launch audit", "è pronto per il lancio?", "pre-launch checklist", "controlla prima di pubblicare", "ready to launch". Not for: a11y (`shadscan`), GDPR risk (`compliance-audit`), cost (`vercel-doctor`), or writing the missing pages.'
---

# launch-audit — the gate that asks whether this is a business

`shadscan` asks whether the software is well made. `compliance-audit` asks whether the data handling
is lawful. `vercel-doctor` asks what it will cost. An app can pass all three and still have **no way
to buy, no company name, no address, and no page that says what happens to your money** — because
none of them look at that.

This gate looks at that, and only at that.

> **It reports. It never blocks, and it does not produce a score.** A number invites optimising the
> number; the output is a list of findings, each routed to whoever fixes it. Same posture as the
> other three gates, for the same reason.

## Contract

See `references/contracts.md` (vendored from `dev-flow`). Key facts:

- Reads `meta.json#stack.framework` — must be `"next"` or `"monorepo"` (operates in `apps/web/`).
- Requires `phase >= "feature_complete"`. Earlier is noise: half the routes do not exist yet.
- Writes `meta.json#launch_audit` (the run, its findings, and what was deliberately dismissed).
- Appends `history`. **Does not modify `phase`** — a gate reports, it does not advance the build.
- **Refuses for mobile.** An Expo app has a store listing, not a sitemap; that surface belongs to
  `rn-publishing-payments`. Say so and stop.

## The three questions

### 1. Findable — can anyone arrive?

| Check | Why it is not cosmetic |
|---|---|
| `title` **on every route**, not only the root | A route without one renders the layout's title in a tab and in every search result and every link preview |
| `description` on every public route | Absent, the engine invents one from the first text on the page |
| `robots` | Present *and correct* — a `Disallow: /` shipped from staging is the classic launch disaster, and it looks like nothing is wrong |
| `sitemap` | Present *and containing the public routes*, not just the root |
| Favicon set | The tab, the bookmark, the phone home screen |
| Social preview | `shadscan` checks the file exists. This checks it **resolves and has dimensions** — a broken OG image is a grey box in every share |
| No route indexable **by accident** | The mirror of the sitemap check: `/showcase`, `/playground`, `/styleguide` served publicly with no `noindex`. A title check passes it and a sitemap check passes it, so nobody looks at it |

⚠️ **The two that are dangerous rather than missing** are `robots` and `sitemap`: existing and wrong
is worse than absent, and no file-existence check can tell the difference. Read them.

### 2. Trustworthy — is there a company behind this?

This is where a marketing checklist turns out to be law. See `references/identity-block.md`.

- **Privacy policy page** — `compliance-audit` assesses whether the *handling* is lawful; nobody
  checked whether the page a user can read exists and is linked. Both are needed.
- **Terms / conditions of sale** — if money changes hands.
- **The provider identity block** — name, geographic address, email, trade register and number, VAT
  number. In the EU this is **Article 5 of Directive 2000/31/EC**, and it must be *"easily, directly
  and permanently accessible"*. Buried in a PDF is not compliant. The verbatim text is in the
  reference, because the enumerated list is what makes this checkable rather than a matter of taste.

### 3. Convertible — can they act?

| Check | The failure it catches |
|---|---|
| A CTA **above the fold** on the landing route | The product explains itself for two screens before offering anything |
| The CTA is **reachable on mobile** | It exists, and on a 375px viewport it is below three paragraphs and a hero image |
| Every CTA **lands somewhere that exists** | A button pointing at `/signup` when the route is `/sign-up` |
| A **confirmation page** after every form that submits | The form posts and the page sits there; the user submits three times |
| Analytics | Nobody knows whether anything above worked |

## Run, then route

```bash
python3 <skill>/scripts/scan_launch.py <project-root>            # signals
python3 <skill>/scripts/scan_launch.py <project-root> --json     # for an agent
```

The script **reports signals, never verdicts** — it cannot know that `/pricing` is intentionally
`noindex`, or that the CTA is in a component it did not resolve. Read each one against the code
before reporting it as a finding. `references/checks.md` says, per check, what a legitimate
false positive looks like.

Then route the real ones — this skill **finds**, it does not build:

| Finding | Who fixes it |
|---|---|
| Missing metadata, missing route, a page that must exist | `screenshot-to-page` |
| A form with no confirmation step | `forms` |
| Privacy/terms content, consent, the lawful basis | `compliance-audit` |
| A11y, loading and empty states, focus | `shadscan` |
| Image weight, LCP, what it costs | `vercel-doctor` |
| Analytics wiring | `module-add` |
| **The identity block** | **the user.** It is their company name, their address, their VAT number. This skill never invents one, and an invented one is worse than a missing one |

## `meta.json#launch_audit`

```json
{
  "launch_audit": {
    "ran_at": "<iso>",
    "findings": [{ "check": "route-title-missing", "where": "app/pricing/page.tsx", "routed_to": "screenshot-to-page" }],
    "dismissed": { "sitemap-missing-routes": "the /app/* routes are behind auth on purpose" }
  }
}
```

`dismissed` carries the **reason**, so the next run does not re-litigate a decision somebody already
made. A finding rejected without a reason comes back forever, and the report stops being read.

## What this skill does NOT do

- **Does not write the pages.** It finds that `/terms` is missing; `screenshot-to-page` builds it and
  a human supplies the text. Generated terms of sale are a liability, not a deliverable.
- **Does not invent the identity block.** Ever. See the routing table.
- **Does not re-check `shadscan` or `compliance-audit`.** Where they overlap, it defers and says so.
- **Does not score.** There is no number to optimise.
- **Does not block a deploy.** It reports before one.

## Reference files

- `references/checks.md` — every check: what it looks for, what a legitimate false positive looks
  like, and which skill owns the fix.
- `references/identity-block.md` — Article 5 of Directive 2000/31/EC verbatim, what each item means
  for a small company, and where the block goes.
