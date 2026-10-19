# Anti-slop fallbacks

When DESIGN.md is **silent** on a value, or when scaffolding pages **not present** in the source Figma (sign-in, /contact, /coaches index, journal placeholders), don't reach for the LLM's statistically average default — it tilts toward a recognizable "AI generic" aesthetic. This file pins better defaults.

Adapted from `taste-skill` (Leonxlnx/taste-skill, MIT) — v1 for rules 1–10, v2.1.1 (re-read 2026-10-19) for the
corrections to rules 3, 5, 6, 9, 10 and for rules 12–13 — reduced to rules that are **CSS-portable** (no JS animation library required) and **compatible with Step 4.5c** (verbatim-Figma rule). These fallbacks fire **only** when the source is silent — they NEVER override a value the DESIGN.md or Figma source actually specifies.

## When these rules apply

✅ **Apply** in these cases:
- DESIGN.md frontmatter doesn't define `colors.<token>`, `typography.<level>`, or `radius.<level>` — and library defaults aren't expressive enough.
- Body-only DESIGN.md (no YAML frontmatter) where prose is vague (e.g., "use a clean dark theme").
- Pages NOT in Figma at all — sign-in, contact, journal articles, coach bios, legal — the ones that get a `<TbdBanner>`.
- Stub data (placeholder users, fake metrics, sample emails, demo schedules).

❌ **Do NOT apply** when:
- The Figma source shows a specific value (font, color, layout, copy). Step 4.5c (verbatim-Figma) wins. Always.
- DESIGN.md frontmatter defines the token explicitly. Use the token, not the fallback.
- The user explicitly asked for an alternative (e.g., "I want pure black").

## The rules

### 1. No pure black

`#000000` reads as harsh, especially on OLED screens and against off-white backgrounds. Use:

- **Off-black**: `#0a0a0a` / `oklch(0.145 0 0)` (Tailwind `zinc-950`).
- For "ink" CSS variable in dark-on-light contexts: prefer `var(--foreground)` over hardcoded values so light/dark theme flip works.

When DESIGN.md says "primary text on light background" without a hex, use off-black, not pure black. When it says "the deepest shadow color", same.

### 2. Mobile viewport — never `h-screen`, and `dvh` vs `svh` is not interchangeable

`h-screen` (which resolves to `100vh`) is broken on iOS Safari: `100vh` is the *largest* viewport — the height with the browser chrome collapsed — so on load, with the URL bar visible, a `100vh` element overflows by the height of that bar and a bottom-pinned button sits underneath it.

**Corrected 2026-10-04: which unit replaces it depends on what the element is.**

- **`100dvh` for an app shell, a drawer, a full-page modal** — anything that should track the visible area as the chrome shows and hides.
- **`100svh` for a hero or a first screen** — the *smallest* the viewport gets, so nothing is ever cut off. `dvh` resizes as the URL bar collapses, which is correct for an app shell and **causes a layout shift on marketing content mid-scroll**. This file used to prescribe `dvh` for heroes specifically; that was the one case where it is the wrong unit.
- `lvh` is the old `vh` — you almost never want it.

The rule against `h-screen` is still **universal**: it applies even when Figma shows a full-viewport hero. "Full screen" in CSS means `dvh` or `svh`, never `vh`.

The rest of the web-on-a-phone layer — the hover state that sticks after a tap, the grey flash, inputs that zoom the page, the 300 ms tap delay, pull-to-refresh, the notch, long-press selecting a button's label, a carousel that scrolls the page instead — is **`references/mobile-web.md`**, including the four-line baseline to ship before the first component.

### 3. Sample data, yes — invented proof, never

Two kinds of invented content, and they are not the same thing.

**Sample data** fills a screen so the design is seen at full density: rows in a dashboard, demo coach profiles,
sample journal posts, a menu's dishes when the brief has none. It is expected, it is realistic, and every piece of it
goes into `fallbacks_applied` so the client can swap it.

**Proof** is what a visitor reads as a fact about the business: how many customers it has, how they rate it, who
trusts it, what the press said, which logos use it, a business statistic on a public page. **Proof is never
invented.** The slot ships empty with a `TBD` (or is left out of the page) and the hand-off lists it under
`proof_left_empty`. *Corrected 2026-10-19:* this rule used to recommend "organic" statistics such as `3,847 members`
for any invented number. On a public page that is fake proof made to look measured — the more convincing it is, the
more likely it ships. taste-skill v2 draws the same line ("proof is never invented").

For sample data, use organic-feeling values, not the patterns the LLM defaults to:

- ❌ Names: "John Doe", "Jane Smith", "Sarah Chan" — recognized as AI defaults.
- ✅ Names: realistic but non-generic — "Marina Lourenço", "Tomás Capellini", "Eliška Novák", "Anne-Sophie Le Goff". Mix nationalities, surnames with diacritics, hyphenated forms.
- ❌ Brand names: "Acme", "Nexus", "SmartFlow", "Synergy", "Apex". Banned.
- ✅ Brand names: contextual + premium — "Performance Driven Gym", "Notarius", "Aetherfield", "Graphite".
- ❌ Stat values: `99%`, `99.99%`, `50%`, `1234`, `1,000,000`. Banned.
- ✅ Stat values **in sample data** (an app screen's rows and charts): organic — `47.2%`, `3,847 rows`, `$24,580`.
  Never the same figure as a claim on a public page ("3,847 members trust us"): that is proof.
- ❌ Email/phone: `john@example.com`, `555-1234`. Banned **unless** Figma uses these as placeholders (then preserve verbatim per Step 4.5c).
- ✅ Email/phone: realistic format — `marina.lourenco@studio.gym`, `+39 02 9876 5432`.

### 4. Banned filler words in invented copy

When you must write copy for a TBD page (sign-in CTA, contact form, legal), avoid the AI marketing slop vocabulary:

- ❌ "Elevate", "Unleash", "Seamless", "Next-Gen", "Empower", "Streamline", "Game-changing", "Revolutionary", "Cutting-edge", "Best-in-class".
- ✅ Concrete verbs: "Sign in", "Send a message", "Read our terms", "Reset your password". Plain. Specific. No adjectives unless they're functional.

The Figma file's actual brand voice (extracted via Step 4.5c) is the authority. When inventing for TBD pages, copy the brand's tone register — terse, direct — and avoid generic SaaS-marketing register.

### 5. Pictures: the real thing first, a placeholder last and logged

A random photo is a placeholder with extra steps: it says nothing about this client and it ships, because nobody
remembers it was a stand-in. When the source has no picture for a slot, take the first that exists:

1. **The project's own** pictures, product shots, footage.
2. **For software, a real fragment of the product** — a crop of an actual screen built from the project's own
   primitives, with sample data that adds up. Never a "dashboard" of grey bars.
3. **Drawn in code from the subject** — its objects, its material, its interface — in the palette's real colours, one
   consistent flat language (`references/illustrations.md` for libraries and licences).
4. **Type and colour alone**: a field of the brand colour with the headline set large beats a stock picture.
5. **`https://picsum.photos/seed/<deterministic-string>/<w>/<h>` only as a draft**, logged in `fallbacks_applied`
   with `"replace_before_launch": true` and listed in the hand-off. Never on a page declared done.

- ❌ Unsplash for invented stubs: links break (the photo is removed, the ID changes silently).
- ⚠️ Unsplash IDs are tolerated when the user has **already specified** them (e.g., perf-gym uses `lib/photos.ts`
  with curated Unsplash IDs). Don't rip those out — that's an existing decision, not a new default.

*Corrected 2026-10-19:* Picsum-with-seed used to be the default. It is now the last resort, after taste-skill v2's
order of preference (own → real fragment → drawn → type alone).

### 6. No 3-equal-card row layout

The "3 horizontal feature cards" pattern is the AI-generated default for "show 3 things" — and it's instantly recognizable as AI slop. When DESIGN.md says "3 features" or "3 benefits" without specifying layout, prefer:

- 2-column zig-zag (image left/right alternating).
- Asymmetric grid (`grid-cols-[2fr_1fr_1fr]`).
- One large item and two smaller ones beside it, ordered by importance.
- A plain list with a single feature image to the side — numbered only if the items are a sequence the reader follows
  in order (rule 11).

*Corrected 2026-10-19:* this list used to offer a "numbered vertical list" — which rule 11 bans for non-sequential
items — and "horizontal scroll on mobile", which on a phone reads as a row cut off at the screen edge.

This rule **bows** to Figma — if the source shows 3 equal cards, do 3 equal cards (verbatim wins). It applies only when scaffolding for an under-specified DESIGN.md.

### 7. Hardware acceleration in animations

When writing `transition` or `@keyframes` for invented motion (skeleton loaders, hover states, page enter), animate **only** `transform` and `opacity`. Never animate:

- `top` / `left` / `right` / `bottom` (forces layout)
- `width` / `height` (forces layout + paint)
- `margin` / `padding` (forces layout)
- `background-color` on large elements (a repaint wherever the browser does not composite it)
- `box-shadow` / `border-radius` (a repaint every frame — the shadow is the one people miss)

Replace with:
- `top: 10px` → `transform: translateY(10px)`
- `width: 0 → 100%` → `transform: scaleX(0) → scaleX(1)` with `transform-origin: left`
- `background-color: red` on a hero → fade the **opacity** of an overlay in the target colour
- a growing `box-shadow` on hover → fade the opacity of a pseudo-element that carries the final shadow (or `filter: drop-shadow()`)

*Corrected 2026-10-19:* the background swap used to say "a `transform: translateZ(0)` overlay" — promoting a layer
changes nothing about the colour change; animating the overlay's opacity is what makes it composite-only. And no
`will-change` by default: only after a measured shift, on the animating element (`transitions/references/
animation-standards.md` §Frame budget).

This is universal CSS-best-practice and costs nothing to follow. `tw-animate-css` (already shipped via shadcn) follows this pattern in its built-in classes.

### 8. Tactile feedback on every interactive element

When writing buttons / links / pressable cards for invented pages, add `:active` feedback. Without it, clicks feel dead:

```tsx
className="active:scale-[0.98] active:-translate-y-[0.5px] transition-transform"
```

Or in Tailwind shorthand: `active:scale-[0.98]`. Pure CSS, no JS. Should land on every `<Button>`, `<Link>`-as-button, and clickable card surface.

### 9. Skeleton loaders, never spinners

When writing `app/loading.tsx` or any in-page loading state for invented routes, use **content-shaped skeletons** (a `<Skeleton>` rectangle the size of the heading, etc.) instead of generic circular spinners. shadcn's `<Skeleton>` pulses with Tailwind's core `animate-pulse` (opacity only) — that is the whole animation. **No moving gradient sweep** ("shimmer") on a skeleton: it is a decorative gradient (rule 11), and `tw-animate-css` ships none (`transitions/references/tw-animate-css.md`). *Corrected 2026-10-19:* this rule used to say it did. (The one sanctioned sweep is the chat status marker on a running line — `references/chat-and-typeset.md` — a state, not decoration, and it stops under reduced motion.)

This is already pinned in `references/loading.template.tsx`. **Content-shaped means measured**, not guessed: once the
route has data, `references/skeleton-audit.md` sizes each skeleton to the loaded UI and proves the page does not jump
(CLS ≤ 0.05, the render probe's `layout-shift`). The fallback rule reinforces: never reach for `<Spinner />` or a `<Loader2 className="animate-spin" />` as a default.

### 10. Stagger via CSS cascade, not JS

When you need a staggered reveal of N items (3 cards, 6 nav links) on a page that doesn't otherwise need JS animation, use CSS:

```tsx
{items.map((item, i) => (
  <div
    key={item.id}
    className="animate-in fade-in slide-in-from-bottom-4 fill-mode-both motion-reduce:animate-none"
    style={{ animationDelay: `${i * 60}ms`, animationDuration: "600ms" }}
  >
    {item.body}
  </div>
))}
```

Pure CSS. Zero JS bundle cost. Achieves taste-skill's "staggerChildren" feel. Three details carry it:

- **No `opacity-0` on the element.** `tw-animate-css`'s `enter` keyframe has only a `from` frame: it animates *from*
  `fade-in`'s opacity 0 *to the element's own opacity*. Put `opacity-0` on the element and the entrance runs 0 → 0 —
  the content is invisible for everyone, with or without reduced motion (`check.py`: `hidden-for-everyone`).
- **`fill-mode-both`** holds the `from` frame during `animationDelay`, so later items do not flash in before their
  turn, and keeps the end state after.
- **`motion-reduce:animate-none`**: a reduced-motion user gets the items in place at once — visible, because nothing
  else hides them.

*Corrected 2026-10-19 (final review of the taste-skill port):* this rule shipped `opacity-0 animate-in … fill-mode-forwards`,
which hides the content for every visitor; `transitions/references/motion-library.md` already had the right form.
A custom keyframe that does end at opacity 1 (`animate-[fade-up_…_forwards]` on an `opacity-0` element) is the other
shape, and there `motion-reduce:opacity-100` is the half that matters (`hidden-without-reduced-motion`; the render
probe measures it on the running page as `reduced-hidden`). The gap is 30–80 ms
(`transitions/references/animation-standards.md`), and a stagger never blocks interaction while it plays. If the
project later adds `module-add motion`, the wrappers in `components/motion/` replace this pattern, but for the default
scaffold, CSS cascade is the fallback.

### 11. Composition reflexes — the tells that are structural, not textual

Rules 1–10 catch invented **data and copy**. These catch invented **layout**: arrangements a model
reaches for when the source does not say what the shape should be. A page can pass every rule above
and still read as generated, because the giveaway is the silhouette.

When the source is silent, do not ship:

- **Centred hero paragraph followed by a card grid.** The single most recognizable shape on the web.
- **A row of identical metric boxes** where one composed relationship — a comparison, a trend, a
  ratio with its denominator visible — would say more. Four numbers in four boxes state four facts
  and no argument.
- **Cards inside cards**, or a border added to rescue a hierarchy that type and spacing should
  already carry. A border is a last resort, not a separator of first choice.
- **A badge or pill for ordinary metadata.** A date is a date. `<Badge>` is for status that changes.
- **Numbered section markers (01 / 02 / 03)** unless the content is genuinely a sequence the reader
  must follow in order. Numbering non-sequential sections is decoration wearing information's clothes.
- **All-caps tracked eyebrows** above every heading.
- **Decorative gradients, glows, blobs, mesh backgrounds, glassmorphism, ornamental shadows.**
- **A rounded dark rectangle wrapped around every chart.** The chart is the content; the box is not.
- **Icon tiles chosen for texture** — mixed icon families, oversized glyphs, an icon per bullet.
- **Charts that carry no comparison**, legends where a direct label on the mark would read better,
  colour used where it encodes nothing.
- **The same section silhouette repeated** for sections that answer different questions. If three
  sections look identical, the reader learns to skip two of them.
- **Repeated summary / recommendation / conclusion blocks** that restate one another.

**The counter-rule, which matters as much.** Do not overcorrect into a sterile template — black,
white, hairline rules, enormous margins, nothing happening. Avoiding the defaults is not the same as
avoiding decisions. Restraint means precise hierarchy, real typographic contrast, deliberate
alignment and one intentional tension. An empty page is not a restrained page.

**Priority.** Like rule 6, every item here **bows to the source**. If Figma or the screenshots show a
centred hero over a card grid, build a centred hero over a card grid — Step 4.5c wins, always. These
apply only where the source is silent and something has to be invented.

### 12. Numbers and charts in app screens

Most of our projects are products with dashboards, and a dashboard is where invented layout shows first. When the
source is silent (adapted from taste-skill v2's app-screen rules):

- **A delta's colour says good or bad, not up or down.** Rising churn is red. A zero or undefined change is neutral
  grey with no arrow. A change from nothing is "+4 (new)", never "+100%".
- **Figures right-aligned in their column and `tabular-nums`**, so digits line up and a column can be read down.
- **One figure in one place.** The same number in a KPI card, a chart caption and a table header is three things to
  keep in sync and one to trust. The figure that answers the screen's question may sit one step larger than its
  siblings (`text-3xl` against `text-2xl`), never in a different face.
- **Charts are shadcn Chart** (golden rule 3), configured — not replaced:
  - at most **four hues**, taken from the `--chart-*` tokens: one accent for the series that matters, neutrals for
    the rest; colour encodes a series or nothing;
  - **no gradient area fill** — a solid `--chart-*` fill at low opacity (`check.py`: `chart-gradient-fill`); the
    shadcn area-chart examples ship a `linearGradient`, so remove it when copying one;
  - a direct label on the line or bar beats a legend; one finding stated in the title beats "Revenue";
  - straight segments without point markers unless the points are the data.
- **An empty section keeps its frame and its heading**, with one line saying why it is empty and the action that fills
  it. A panel that disappears when empty moves everything below it.
- **Sample figures add up.** Rows sum to the total shown; a percentage has its denominator.

### 13. Copy shape — what an invented sentence should look like

Rule 4 bans words; this bans shapes. When the brand voice (Step 4.5c) does not decide it:

- **A headline is a statement about this product**, not a slogan that fits any product: "Invoices out in two
  minutes" — not "Work smarter". Put the nearest competitor's name in it: if it still works, rewrite it.
- **Two lines at most, at every width, in the longest locale** — Italian runs 15–30% longer than English
  (`references/i18n-next-intl.md` §Headlines in every locale).
- **One supporting sentence right under the headline** that says plainly what the thing is and does.
- **A button names what it does** ("Send the invoice"), never "Get started" or "Learn more" alone.
- **No eyebrow label above a heading to carry information the heading should carry.** (The showcase's section
  eyebrows are part of its specimen format and stay.)
- More English tells to avoid in invented copy: "In today's fast-paced world", "Say goodbye to", "Take X to the next
  level", "Whether you're X or Y", "Unlock", "Supercharge", "Effortless", "Look no further".

## Hand-off

When the scaffold runs, log every fallback you used to `_design-md-mapping.json` under a `fallbacks_applied` key:

```json
{
  "fallbacks_applied": [
    {
      "rule": "no pure black",
      "where": "ink CSS variable",
      "value": "oklch(0.145 0 0)",
      "reason": "DESIGN.md did not specify primary text color"
    },
    {
      "rule": "realistic placeholder data",
      "where": "lib/queries/coaches.ts",
      "value": "Marina Lourenço, Tomás Capellini, Eliška Novák, Anne-Sophie Le Goff",
      "reason": "Coaches page not in source Figma — invented per Step 4.5c TBD policy"
    }
  ],
  "proof_left_empty": [
    {
      "where": "app/(marketing)/page.tsx — customer-stories section",
      "reason": "no customer quotes or counts supplied; slot shows the TBD banner"
    }
  ]
}
```

This way the reviewer can see at a glance every place an opinionated default was chosen — and override any of them with one DESIGN.md edit.
