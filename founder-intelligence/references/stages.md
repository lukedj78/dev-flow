# The stages

Load one section at a time. Each says what it is for, what it reads, what it writes into the Playbook and
when it is done. The exercises are adapted from Anthropic's *The Founder's Playbook* (May 2026, Idea and MVP
stages), paraphrased. Go back to an earlier stage when a finding changes the direction; redo only that one.

## 1. Intake

**For:** start useful work from whatever the founder gave, even three lines.
**Reads:** the founder's message; in `existing` mode PROJECT.md, PRD.md, tasks.md and the code's shape.
**Writes:** §2 (the idea as stated, unchanged), first notes in §3–4, and §18 with what is missing.
**Done when:** idea, problem, suspected users, proposed solution, differentiation, objectives, constraints
and the known assumptions are written down, each marked known or missing. No questionnaire first.

## 2. Testable problem hypothesis

**For:** turn an observation into something a conversation can confirm or refute.
**Writes:** §3. "People struggle with X" is an observation; *who* has it, *how often*, *how severely* and
*what they do today* make it a hypothesis.
**Done when:** the hypothesis names a specific group and a measurable pain. If it cannot, say which part is
missing; that is the first question for the founder.

## 3. Devil's advocate

**For:** find the strongest case against before the interviews, so they are open questions rather than a
search for confirmation.
**Writes:** §8 counter-analysis, first draft: negative market signals, failed competitors, customer
behaviour that contradicts the idea, structural obstacles.
**Done when:** the three strongest reasons the idea could fail are written, each with what would show it.

## 4. Founder interview

**For:** what only the founder knows: why this, what success means to them, expertise and unfair
advantages, access to customers and channels, budget, time, geography, risk tolerance, monetisation
preferences, existing assets and commitments, willingness to validate before building.
**How:** batches of three or four questions, the reason given when it is not obvious, nothing research can
answer, nothing §18 already records.
**Writes:** §2, §18 (each answer with its date).
**Done when:** the answers that change the direction are in; the rest is listed as open.

## 5. Market and competitors

**For:** who else solves this, how, and how well.
**How:** web search and `dev-flow/scripts/research.py` (`reddit`, `hn`, `read`, `papers`, `repos`);
`references/evidence.md` for every number.
- Competitors **by tier**: direct, indirect, substitutes (including manual work and doing nothing),
  possible acquirers, adjacent players who could move in. For each tier, argue why it could win; write the
  threat that is hardest to dismiss, not the easiest.
- Positioning, target customer, features, **observed** prices, distribution.
- **Review mining**: recurring complaints existing solutions have not resolved. If the hypothesis answers
  one of them, that is evidence of fit; if it answers none, that is worth knowing too. **The sources, the
  verbatim-and-linked rule and the thin-theme threshold are in stage 6** — this bullet and that one are
  the same work seen from two sides, so do it once and cite it twice.
- **Where to read a competitor's features, in order of value.** The **help centre or docs** is the most
  complete feature list that exists, and it is written by the vendor. The **pricing page** says which of
  those features *matter*, because those are the ones it gates. Then the changelog (what the team thinks is
  worth announcing), the app-store listing (a screenshot of every key screen), public walkthrough videos
  (the real flow, click by click) and the public API docs (the data model, almost for free). The marketing
  site is last: it is the only one written to persuade you.
- Three external trends (regulatory, technological, demographic) for the next two years, each a tailwind
  or a headwind for this hypothesis.
- Market size only with its method: TAM/SAM/SOM with every input visible and pressure-tested, or "no reliable
  data" stated.
**Writes:** §6, `sources.md`.
**Done when:** each tier has named players with sources, and the gaps in the data are stated.

## 6. Customer discovery

**For:** the evidence the Idea stage turns on: conversations with real people. The skill prepares and
synthesises; **it never interviews and never simulates**. Use `references/interviews.md`.
**Writes:** §5; the kit (who to talk to, where to find them, the questions); syntheses as notes arrive in
`interviews/`.
**Done when:** the kit is ready and handed over. If no interview has happened yet, §5 says so and the
validation roadmap (stage 12) carries the interviews as the first experiment.

**First, when the competitor already exists: read what its users wrote.** Interviews are the evidence this
stage turns on, and they are also the slowest thing in the Playbook — so a product with an incumbent has a
free rung below them that this skill used to walk past. Public reviews are `[review]` evidence
(`references/evidence.md`), and they are read, never scraped: the product's App Store and Google Play
pages, G2, Capterra and Trustpilot filtered to 1–3 stars as well, Reddit (`"X alternative"`,
`"switched from X"`), Hacker News, and the product's own public roadmap or feature-request board with its
vote counts. Where an official public feed exists it is the better door — Apple's customer-reviews RSS, the
Hacker News Algolia API, Reddit's own API within its terms. Read its changelog too, so the Playbook does
not propose fixing something shipped last month.

Sort them into three ranked lists — **what they hate**, **what is missing**, **what is unsolved** (a whole
job or group the product ignores: *"useless for therapists"*) — each item with its count, its number of
sources and one or two linked quotes. The third list is the one that becomes positioning in stage 7.

🔴 **Then read the low ratings that matched no theme, by hand.** A themed list only finds what the themes
already name, so the complaint nobody has a word for yet sits in the leftovers — and that is the one worth
having. This is also what keeps the stage from turning into a word-frequency count.

**It does not shorten the interview kit.** It aims it: every theme becomes a question whose answer the
reviews cannot give, starting with whether the complaint is worth money.

## 7. Opportunity and positioning

**Writes:** §8–9: problem statement, first segment, value proposition, why customers would switch, switching
barriers, defensibility, and the counter-analysis completed with what stages 5–6 found.
**Consider explicitly** whether the better outcome is to narrow, change segment, change model, postpone or
stop, and write the recommendation with its reason.
**Done when:** the positioning fits in two sentences and the strongest case against is answered or
recorded as open.

## 8. Business model and economics

**Writes:** §10–11: buyer versus user, pricing model and indicative price (with competitors' observed prices
as anchors), revenue streams, acquisition channels and their cost, gross margin drivers (hosting, AI
inference, APIs, storage, support), founder workload, retention and churn assumptions, break-even, three
scenarios with the assumptions they rest on and the sensitivity that matters.
**Rule:** every number carries its class. A profitable spreadsheet is not a validated model.
**Done when:** the scenarios can be recomputed by someone else from what is written.

## 9. MVP scope and measurement

**For:** the smallest credible product or experiment that tests the most important assumptions. Cheap code
does not justify scope.
**Writes:** §12:
- core problem, primary journeys, essential capabilities;
- **explicit exclusions**, and the evidence that would justify adding a feature (amendment criteria);
- external dependencies, operational and support needs;
- **metrics decided before launch**: the activation event, retention targets at 7 and 30 days, and what a
  false positive would look like (sign-ups without activation, revenue without retention) — in the PRD's
  `## Measurement` format (event names `snake_case`, past tense: `invoice_sent`), because `prd-from-idea` copies
  them there unchanged;
- what a prototype, landing page or manual service can test first.
**Not** a PRD: no user stories, no screens. Those are `prd-from-idea`'s.
**Done when:** a reader can say what the MVP deliberately does not do.

## 10. Feasibility, and what already exists

**For:** strategic feasibility, and the inventory verdict this path owes the gate.
**Writes:** §13–14: architectural constraints, external APIs and data, data quality, security and privacy,
regulation that applies (flag what needs a specialist; `compliance-audit` does the engineering audit later),
cost drivers, reliability, lock-in and critical dependencies.
**What already exists:** run steps 1–4 of `dev-flow/references/before-you-build.md` (in the house, tools
already paid for, the Claude ecosystem, outside, with `research.py repos`), then record the verdict:

```bash
python3 dev-flow/scripts/inventory.py record <root> --verdict have-it|adapts|halfway|build \
    --searched <channels> [--not-covered <channels>] --summary "see founder-playbook.md §13"
```

**Not** an implementation plan: architecture, repository setup and tasks belong to dev-flow.
**Done when:** the critical risks and unknowns are listed and the verdict is recorded.

## 11. Go-to-market

**Writes:** §15: first segment and how to reach its first customers, channels, message, pricing and packaging
experiments, landing-page or prototype experiments, partnerships, launch milestones, activation and retention
metrics, the conditions for expanding beyond the first segment. Publishing is not distribution.
**Done when:** the first ten customers have a named route.

## 12. Validation roadmap and risk register

**Writes:** §16–17. One row per critical hypothesis: id (`H1`…), why it matters, evidence so far,
confidence and its reason, the cheapest credible test, the success criterion decided **before** running it,
the result (only if run), the next action. Tests already run are kept apart from proposed ones. Risks:
commercial, product, technical, operational, financial, regulatory.
**Done when:** the most consequential untested hypothesis has a test the founder can run this week.

## 13. Synthesis and readiness

**For:** a Playbook a founder can decide on.
- Resolve contradictions; recheck the claims the decisions rest on and their links; find assumptions written
  as facts by mistake.
- Write §1 last: problem, users, answer, strongest evidence, strongest reason against, recommendation.
- List the decisions the founder must take, and mark the ones they have taken as **locked** in §18.
- Record: `founder.py record <root> --research complete --open <untested critical H-ids>`.
**Done when:** `founder.py status` shows `READY_FOR_FOUNDER_APPROVAL`, and the presentation states that
research complete is not validation.
