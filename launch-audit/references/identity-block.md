> Source: **Directive 2000/31/EC, Article 5** — read verbatim from EUR-Lex on **2026-09-13**:
> <https://eur-lex.europa.eu/eli/dir/2000/31/oj/eng>. Implemented nationally (Germany's *Impressum*,
> Italy's obligations under D.lgs. 70/2003, and so on), so the national rule can add to this list and
> never subtracts from it. `[VERIFY]` the national implementation for the country of establishment.
> **This is not legal advice and this skill does not give any** — it points at an enumerated list and
> asks whether the site has one.

# The provider identity block

"Real contact address" reads like a line from a marketing checklist. In the EU it is a statutory
requirement with an enumerated list, and that is what makes it checkable at all — the difference
between *"the site should feel trustworthy"* (a matter of taste) and *"these seven items are either
present or they are not"*.

## What the Directive actually says

Article 5(1), verbatim:

> Member States shall ensure that the service provider shall render **easily, directly and permanently
> accessible** to the recipients of the service and competent authorities, at least the following
> information:
>
> (a) the name of the service provider;
> (b) the geographic address at which the service provider is established;
> (c) the details of the service provider, including his electronic mail address, which allow him to
> be contacted rapidly and communicated with in a direct and effective manner;
> (d) where the service provider is registered in a trade or similar public register, the trade
> register in which the service provider is entered and his registration number, or equivalent means
> of identification in that register;
> (e) where the activity is subject to an authorisation scheme, the particulars of the relevant
> supervisory authority;
> (f) as concerns the regulated professions: any professional body or similar institution with which
> the service provider is registered, the professional title and the Member State where it has been
> granted, a reference to the applicable professional rules in the Member State of establishment and
> the means to access them;
> (g) where the service provider undertakes an activity that is subject to VAT, the identification
> number referred to in Article 22(1) of […] Directive 77/388/EEC.

## Reading it for a small company

| Item | What it means in practice | Applies when |
|---|---|---|
| (a) name | The **legal** name, not the brand. "Acme S.r.l.", not "Acme" | always |
| (b) geographic address | A real postal address. A PO box is not a geographic address, and neither is a city | always |
| (c) contact | An **email address**, plus anything else. The test in the text is *"rapidly and… direct and effective"* — a contact form alone has been held not to satisfy it | always |
| (d) trade register | Chamber of commerce / companies house: which register, and the number | when registered |
| (e) supervisory authority | Licensed activities — finance, insurance, health, gambling | when licensed |
| (f) regulated professions | Lawyers, doctors, architects, accountants: body, title, granting Member State, applicable rules | when regulated |
| (g) VAT number | The VAT identification number | when VAT-registered |

For a typical SaaS or shop run by a small company: **(a), (b), (c), (d), (g)**. Five items.

## "Easily, directly and permanently accessible"

Three words, three failures, and each one is checkable:

- **Easily** — reachable from every page, which in practice means the footer. Findable from the home
  page only is not "easily" for someone who landed on a product page from a search result.
- **Directly** — a link, not a chatbot, not a PDF download, not a form that emails you the details.
- **Permanently** — a static route. Not a modal, not a tooltip, not something behind sign-in.

The shape that satisfies all three is dull and that is the point: a `/legal` or `/imprint` route,
linked in the footer of the layout so it is on every page.

## Where it goes, and what this skill will not do

**In `app/(marketing)/legal/` or `/imprint`, linked from the footer in the layout.** Next's route
groups make this one file and one link.

**This skill never writes the block.** It reports whether one exists and whether the items are there.
The content is the user's legal name, their registered address, their VAT number — and **an invented
one is materially worse than a missing one**: a missing block is an omission, a wrong registration
number is a false statement on a commercial website.

So the finding reads *"no identity block found; Article 5 lists (a)(b)(c)(d)(g) for a company like
this — supply them and `screenshot-to-page` will place them"*, and then the skill stops.

## The overlap with `compliance-audit`, stated so neither skill assumes the other did it

They ask different questions about the same page and both answers are needed:

| | `compliance-audit` | this skill |
|---|---|---|
| Privacy policy | is the **handling** lawful — basis, retention, DSAR, transfers (R1–R10) | does a **page** exist, is it linked, is it reachable |
| Identity block | not in scope | (a)–(g), present or not |

A product can hold a perfect lawful basis and publish nothing a user can read. It can also publish a
beautiful policy describing handling it does not do. Two gates, because they are two failures.
