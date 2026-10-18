# Evidence

The Playbook is only as useful as the line it draws between what is known and what is hoped. Every material
claim carries one of five classes; every fact has a row in `.workflow/founder/sources.md`.

| Class | Means | Example |
|---|---|---|
| `[source]` | a verified fact, with URL and the date it was read | a competitor's public price |
| `[founder]` | stated by the founder | "I can reach 40 law firms" |
| `[interview]` | from notes of real interviews in `interviews/` | "3 of 5 reconcile by hand every Friday" |
| `[estimate]` | a calculation from stated inputs, shown | SOM = segment × assumed penetration |
| `[hypothesis]` | to be tested | "they would pay €50 a month" |

## Rules

- **No precision without a method.** TAM, SAM, SOM, market share, conversion and revenue figures appear only
  as `[estimate]` with every input and its class visible, or with the source that publishes them and its
  methodology. A missing figure is written as missing.
- **Read before citing.** No quotation, page number or claim is attributed to a source that was not opened
  in this session. A source that could not be reached is listed as not read.
- **Prefer primary and recent.** Vendor pages for prices and features, filings and official statistics for
  markets, changelogs for products; note the publication date for anything that changes.
- **Both directions.** Evidence against the idea gets the same care and the same space as evidence for it. A
  synthesis whose supporting list is much longer than its challenging list is checked: does the asymmetry
  come from the data, or from what was hoped?
- **Never simulated.** Interviews, survey results, testimonials, sign-ups, purchases and letters of intent
  exist only if the founder provides them.
- **No tools, say so.** Without web search, the Playbook's header says it, and every `[source]` that could not
  be verified becomes `[hypothesis]`.

## `sources.md`

One row per source, numbered so the Playbook can cite `[source 7]`:

| # | URL | Read on | Published | What it supports | Decisions that depend on it |
|---|---|---|---|---|---|
| 7 | https://… | 2026-10-17 | 2026-09 | Competitor X charges €49/user/month | §10 indicative price |

When a decision changes because a source turned out wrong, the row says so and the revision log records it.
