# The page argument — before the public area is drawn

A public page built from a template looks like the average of every page: a centred headline, three feature cards,
a logo strip, a testimonial, pricing, a call to action. Nothing in it is wrong and nothing in it was decided. What
separates a page people remember from that average is rarely the styling: it is **an idea taken from the client's
own world**, and **sections that each make one claim and prove it**.

So before the first public artboard is drawn, write down what this page argues. It takes ten minutes, and it is what
the canvas, the copy and the review are measured against afterwards.

Adapted from taste-skill v2.1.1 (Leonxlnx/taste-skill, MIT — the subject inventory, the idea sentence, the competitor
test, the argument) and fitted to dev-flow: real copy in the user's language, i18n, the primitives as they are.

## When

When `docs/wireframes/screen-inventory.md` has a screen whose **Roles** include `visitor` — a home, a landing page,
a pricing or product page, a public listing. **Every screen a person sees before signing in carries the role
`visitor`** in the inventory, whatever the PRD calls them ("guest", "prospect"): it is the word the checker reads
(`visitors`, `visitatore`, `visitatori` count too, and the column may be headed Roles, Role, Ruoli or Ruolo). A dashboard-only project has none, and `wireframes.py argument` says so.
`wireframes.py approve` refuses public screens without a complete argument, unless `--no-argument "<reason>"`
records why (the public site is the client's existing one; the only public screen is a sign-in).

## The file — `docs/wireframes/page-argument.md`

Labels in English, fixed (the checker reads them); the content in the user's language, like every artboard.

```markdown
# Page argument

## Inventory
- <eight to twelve things that belong to this client and to no competitor>

## Idea
Idea: On this page, <something of the subject> becomes <the device the page is built on>.

## Competitor test
Competitor: <the nearest real competitor>
Result: <why the sentence does not work for them — or the rewrite it forced>

## Argument
| Section | Claim | Proof |
|---|---|---|
| Hero | <the one thing a visitor must understand> | <what on the page shows it> |

## Live thing
<optional: the one thing a visitor can do on the page, built from the idea>
```

`python3 wireframe-canvas/scripts/wireframes.py argument <root>` checks it: at least eight inventory items, an
`Idea:` line that links the two halves — *becomes*, or the same word in the user's language (*diventa*, *devient*,
*wird*, *se convierte en*), or an arrow `→` — both competitor lines, an Argument table with `Section`, `Claim` and
`Proof` columns (other columns and any order are fine) where every row has all three, and no `<placeholder>` or
`TBD` left. Labels may be bold (`**Idea:**`).

## The parts

**Inventory — eight to twelve things only this client has.** Its name and what the name means; its street, its
neighbourhood and what that place looks like; the numbers that are really in the brief (rooms, seats, minutes to the
sea, the year, the price); the constraint it lives with (one batch a month, closed in winter, by appointment); its
materials and colours; its rituals and hours; the printed things of its world (a timetable, a label, a ticket). For a
SaaS product: the job it replaces, the artefact it produces (the invoice, the report, the plan), the one number its
users check every morning, the workflow it cuts from ten steps to two. Every item comes from the PRD, PROJECT.md,
the Playbook or the user — never invented (`prd-from-idea`'s rule: `<TBD>` before a guess).

**Idea — one sentence.** "On this page, **[something from the inventory]** becomes **[the device]**." Places to look:
what the thing produces (put the real output on the page as material); its object or shape; its name; its place; its
ritual (a sequence the page can follow as it scrolls); the printed artefact of its world. "Clean and modern" is not an
idea.

**Competitor test.** Put the nearest real competitor in the sentence. If it still works, the idea belongs to the
category, not to the client: rewrite it from a more specific inventory item. A loaf of bread is every bakery; the seven
doors of the street this one is named after are only this one.

**Argument — one claim per section, each with its proof.** The claims decide which sections exist and in what order.
**A section with no claim is cut** — that is how the stock sequence (hero, logos, three features, testimonial,
pricing, CTA) never happens by default. The proof is something the page shows: the product's real interface, the real
timetable, the real price with what it includes. **Proof is never invented** (`design-md-to-app/references/
anti-slop-fallbacks.md` rule 3): no customer counts, ratings, quotes or logos the client did not supply. A claim whose
only proof would be invented is a claim the page cannot make yet — leave it out, or mark the slot `TBD` and say so.

**Live thing (optional).** One thing a visitor can do, made from the idea: set the loan and read the real monthly
figure; type a name and see it set in the product's output; pick a date and see what is open. It uses real content,
works with a thumb on a phone, has a plain fallback, and never blocks reading. One, not a playground.

## How it reaches the canvas

- **Every public section is drawn from its argument row**, in that order, and is named in the layer by its claim.
- **Software shows itself.** A screen of the product on a public page is drawn as the real screen, from the project's
  own primitives with sample data that adds up — never a "dashboard" of grey bars. It is the strongest picture a
  software page has.
- **Headlines: two lines at most, at 390 px, in the longest locale.** Italian runs 15–30% longer than English: draw the
  phone artboard with the longer text, and when a headline only fits in one language, rewrite it — do not shrink it
  below its slot. A forced break is a `t.rich` tag in the message, never a `<br>` in one language
  (`design-md-to-app/references/i18n-next-intl.md` §Headlines in every locale).
- **One supporting sentence right under the headline** that says plainly what the thing is, and one primary action
  named for what it does.
- **The idea reaches every section**, pricing, FAQ and footer included — the commonest failure is a distinctive first
  screen followed by stock blocks.

## Reviewing a public area — eight questions, no score

Ask them of the area's artboards before showing them to the user, and fix what fails. They are questions, not a
gate: the user's eye decides (`SKILL.md` Step 2.5).

1. **Five seconds on the first screen**: can a stranger say what this is and what to do?
2. **Does every section answer its argument row** — and is there a section with no claim that should go?
3. **Competitor test on the screens**: with the competitor's name and logo swapped in, would the page still work?
4. **One dominant thing per screen**: is each desktop screen a poster with one thing large, or a grid of equals?
5. **Neighbouring sections**: does any section share its neighbour's layout? Are there three identical cards in a
   row (anti-slop rule 6)?
6. **Is any proof invented** — a count, a rating, a quote, a logo — or any picture a stand-in that will ship?
7. **The phone artboards in the longer locale**: two-line headlines, nothing cut at the screen edge, the primary
   action reachable with a thumb?
8. **Is anything there only to decorate** — an eyebrow above a heading carrying what the heading should, a gradient,
   a glow, numbering on sections that are not a sequence (anti-slop rule 11)?
