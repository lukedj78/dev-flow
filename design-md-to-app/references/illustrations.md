# Illustrations — when, and only then, Koboyo

The **how**, doc-grounded against [koboyo.com/icons](https://koboyo.com/icons) and its [license](https://koboyo.com/icons/license). Koboyo is our default *illustration* source — **not** our icon set. `stack.illustrations = "koboyo"`. **License read off the page on 2026-08-26** — it is custom, not a standard OSS licence, so here it is
concretely. All **135,610** icons are free for personal **and commercial** use, **no attribution**, no
sign-up, no seat counts, no per-project fees. You may recolor, resize, crop, animate and modify them,
and embed them in products you sell — **including client work and templates** — *"as long as the icons
are part of something bigger rather than the product itself."*

⚠️ **The prohibitions are where a project can walk into a wall.** You may not resell or redistribute the
library (or a substantial part of it) as an icon collection; build a competing product with them — the
license names *icon library, canvas, whiteboard, diagramming, presentation or drawing app*; or bundle
them into **any app where they are the feature, or where users can pick, extract, download or
re-share them**.

That last clause is not an edge case. **A gallery, a picker, or an asset library is exactly the
disallowed shape** — if the product's value is that users browse and take away icons, Koboyo is the
wrong source no matter how the attribution is handled. Decide this before the assets are in the repo,
not at launch. `[VERIFY]` the terms again before shipping commercially — a custom licence can be
rewritten without a version bump.

## ⚠️ Restraint first — this is a deliberate choice, not a default reflex

An illustration is a **strong stylistic commitment**. Most products need very few, and some need none at all. Before adding one, three gates in order:

1. **Does DESIGN.md's visual language admit hand-drawn art?** A soft, editorial or playful brand: yes. An enterprise dashboard, a dense data tool, a hard-edged industrial or luxury brand: almost certainly no — hand-drawn illustration will read as borrowed from another product. **DESIGN.md decides, not convenience.** If the design has no illustration voice, the answer is a well-set empty state with type and spacing, not a picture.
2. **Is this a moment that deserves one?** Illustrations earn their place at *emotional pauses* — the first empty state, onboarding, a success milestone, a 404. They do not belong on every card, section header or list row.
3. **Would the same file work in a competitor's product?** If yes, it's decoration. Cut it or replace it with something specific to this domain.

**Budget it.** A product should ship a *handful* of illustrations, reused consistently, not one per screen. Ten different hand-drawn scenes across an app is the visual equivalent of ten fonts. When in doubt: **one fewer**.

This is the same rule as the anti-slop fallbacks (`anti-slop-fallbacks.md`) — generic art is worse than no art.

## Illustration ≠ icon

| | Use | Source |
|---|---|---|
| **UI icon** | a control, a status, an affordance — 16–24px, sits in the interface | `stack.icon_library` (lucide default) |
| **Animated icon** | a meaningful micro-interaction on an affordance | `animated-icons` skill |
| **Illustration / spot art** | a *moment* — empty state, onboarding, error, marketing hero | this file |

Never solve an icon problem with an illustration, or vice versa: a hand-drawn glyph inside a toolbar breaks the interface's rhythm.

## What Koboyo is

**71,262 free hand-drawn SVG icons**, categorised `face · mark · object · people · scene`. The `scene` and `people` sets are the illustration-shaped ones; the rest sit closer to spot art. Consistent single style across the whole library, which is what makes it usable — mixing illustration sets is the fastest way to look incoherent.

## ⚠️ The license boundary (read before you build)

Free for **personal and commercial** use, **no attribution required** (a link is "appreciated"). You may recolor, resize, crop, animate and modify. You may embed them in products you sell, including client work and templates — **"as long as the icons are part of something bigger rather than the product itself."**

You may **not**:
- resell or redistribute the library, or any substantial part, as an icon collection;
- build a competing product with them (an icon library);
- **bundle them into any app where they are the feature, or where users can pick, extract, download or re-share them.**

**That last clause is a hard stop for gallery/picker products.** A SaaS whose value *is* browsing, recoloring and downloading illustrations cannot source them from Koboyo — that is precisely the prohibited use, regardless of the free tier. Such products need permissively licensed sources (e.g. unDraw, or art you commission). If a project's PRD describes an asset gallery, flag this at design time, not at launch.

## Finding them — MCP, the agent-native path

Koboyo ships an **MCP server**, so the agent searches the library directly instead of you browsing a grid:

```bash
claude mcp add --transport http koboyo-icons https://api.koboyo.com/v1-mcp
```

⚠️ **It needs an API key.** The site's own MCP section reads *"Create a key, then your coding assistant
can search these icons"* — the bare `mcp add` above registers the server but will not authenticate.
Get the key from koboyo.com/icons ("Get your key") and pass it as the server's auth header.

Then ask for what the moment needs ("an empty mailbox", "two people reviewing a document") and the
agent returns candidates. Individual SVGs are also downloadable from the site. Endpoint checked on
2026-08-26: `https://api.koboyo.com/v1-mcp` answers **405 to a GET**, which is the expected reply from
a Streamable-HTTP MCP endpoint that wants POST — alive, not dead. `[VERIFY]` the transport/URL against
the site anyway; MCP endpoints move.

Whatever the path: **vendor the chosen SVGs into the repo** (`public/illustrations/` or `components/illustrations/`), don't hotlink. They become project assets you control, review and can recolor.

## Making them yours (or don't use them)

A dropped-in illustration in its stock colours is exactly the "borrowed from another product" failure. Bring it onto the design:

- **Recolor to the DESIGN.md palette.** Replace hardcoded fills with `currentColor` (then drive it from a text colour) or with your token vars, so the art inherits the theme and dark mode for free.
- **One accent, not five.** Reduce the palette to the brand's neutral + a single accent. Multicolour stock art fights every page it's on.
- **Match the stroke weight** to the icon set and the type. A 2px hand-drawn line next to a 1.5px lucide icon reads as a mistake.
- **Size deliberately** — an empty-state illustration is usually 120–200px, not a hero. Give it `aria-hidden="true"` when the adjacent copy already says everything; it's decorative.
- **Reduced motion**: if you animate one (per the `transitions` skill), it gets the same `prefers-reduced-motion` guard as everything else.

## Where they belong

| Surface | Guidance |
|---|---|
| **Empty state** | The canonical case — first-run especially. Pair with copy that says what to do next; the illustration carries tone, the text carries the action. `design-md-to-app` already scaffolds empty states with the planned-tasks list; the art is optional on top. |
| **Onboarding / success** | One per meaningful step at most. |
| **404 / error** | One, reused across error pages. |
| **Marketing / docs** | Where the brand voice allows it; keep to the same subset. |
| **Dashboards, tables, forms, settings** | No. Density and repetition are the enemy of illustration. |

## dev-flow integration

- Record `meta.json#stack.illustrations = "koboyo"` **only when a project actually adopts it** — `null` is the correct value for most products, and the honest default.
- Owned by `design-md-to-app` (the visual layer). The decision belongs at DESIGN.md time, alongside palette and type — not improvised mid-build.
- Mobile: the same restraint applies; vendor SVGs via `react-native-svg`.
