# Anti-slop fallbacks

When DESIGN.md is **silent** on a value, or when scaffolding pages **not present** in the source Figma (sign-in, /contact, /coaches index, journal placeholders), don't reach for the LLM's statistically average default — it tilts toward a recognizable "AI generic" aesthetic. This file pins better defaults.

Adapted from `taste-skill` (Leonxlnx/taste-skill), reduced to rules that are **CSS-portable** (no JS animation library required) and **compatible with Step 4.5c** (verbatim-Figma rule). These fallbacks fire **only** when the source is silent — they NEVER override a value the DESIGN.md or Figma source actually specifies.

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

### 2. Mobile viewport — `min-h-[100dvh]`, never `h-screen`

`h-screen` (which resolves to `100vh`) is broken on iOS Safari: the browser chrome (URL bar, bottom toolbar) is included in `100vh` but visible on screen, causing layout shift when the chrome retracts on scroll. Use `min-h-[100dvh]` (`100dvh` = dynamic viewport height) for hero sections, full-page modals, and any "this should fill the screen" intent.

This rule is **universal** — it applies even when Figma shows a full-viewport hero. The Figma value "full screen" in CSS means `100dvh`, not `100vh`.

### 3. Realistic placeholder data

When inventing data for stub routes (placeholder rows in a dashboard, sample journal posts, demo coach profiles), use organic-feeling values, not patterns the LLM defaults to:

- ❌ Names: "John Doe", "Jane Smith", "Sarah Chan" — recognized as AI defaults.
- ✅ Names: realistic but non-generic — "Marina Lourenço", "Tomás Capellini", "Eliška Novák", "Anne-Sophie Le Goff". Mix nationalities, surnames with diacritics, hyphenated forms.
- ❌ Brand names: "Acme", "Nexus", "SmartFlow", "Synergy", "Apex". Banned.
- ✅ Brand names: contextual + premium — "Performance Driven Gym", "Notarius", "Aetherfield", "Graphite".
- ❌ Stat values: `99%`, `99.99%`, `50%`, `1234`, `1,000,000`. Banned.
- ✅ Stat values: organic — `47.2%`, `3,847 members`, `+1 (312) 847-1928`, `$24,580`.
- ❌ Email/phone: `john@example.com`, `555-1234`. Banned **unless** Figma uses these as placeholders (then preserve verbatim per Step 4.5c).
- ✅ Email/phone: realistic format — `marina.lourenco@studio.gym`, `+39 02 9876 5432`.

### 4. Banned filler words in invented copy

When you must write copy for a TBD page (sign-in CTA, contact form, legal), avoid the AI marketing slop vocabulary:

- ❌ "Elevate", "Unleash", "Seamless", "Next-Gen", "Empower", "Streamline", "Game-changing", "Revolutionary", "Cutting-edge", "Best-in-class".
- ✅ Concrete verbs: "Sign in", "Send a message", "Read our terms", "Reset your password". Plain. Specific. No adjectives unless they're functional.

The Figma file's actual brand voice (extracted via Step 4.5c) is the authority. When inventing for TBD pages, copy the brand's tone register — terse, direct — and avoid generic SaaS-marketing register.

### 5. No Unsplash for invented stub photos

Unsplash links break (photo gets removed from CDN, ID changes silently). For TBD pages that need a placeholder image:

- ✅ `https://picsum.photos/seed/<deterministic-string>/<w>/<h>` — Lorem Picsum, deterministic via seed.
- ✅ Static SVG placeholder generated at build time (a tinted block with the alt text rendered as a label).
- ⚠️ Unsplash IDs are tolerated when the user has **already specified** them (e.g., perf-gym uses `lib/photos.ts` with curated Unsplash IDs). Don't rip those out — that's an existing decision, not a new default.

For new scaffolds where the user hasn't picked a photo source: default to Picsum-with-seed.

### 6. No 3-equal-card row layout

The "3 horizontal feature cards" pattern is the AI-generated default for "show 3 things" — and it's instantly recognizable as AI slop. When DESIGN.md says "3 features" or "3 benefits" without specifying layout, prefer:

- 2-column zig-zag (image left/right alternating).
- Asymmetric grid (`grid-cols-[2fr_1fr_1fr]`).
- Numbered vertical list with a single feature image to the side.
- Horizontal scroll on mobile, 2-up + 1 below on desktop.

This rule **bows** to Figma — if the source shows 3 equal cards, do 3 equal cards (verbatim wins). It applies only when scaffolding for an under-specified DESIGN.md.

### 7. Hardware acceleration in animations

When writing `transition` or `@keyframes` for invented motion (skeleton loaders, hover states, page enter), animate **only** `transform` and `opacity`. Never animate:

- `top` / `left` / `right` / `bottom` (forces layout)
- `width` / `height` (forces layout + paint)
- `margin` / `padding` (forces layout)
- `background-color` on large elements (forces full repaint)

Replace with:
- `top: 10px` → `transform: translateY(10px)`
- `width: 0 → 100%` → `transform: scaleX(0) → scaleX(1)` with `transform-origin: left`
- `background-color: red` on a hero → place a `transform: translateZ(0)` overlay div instead

This is universal CSS-best-practice and costs nothing to follow. `tw-animate-css` (already shipped via shadcn) follows this pattern in its built-in classes.

### 8. Tactile feedback on every interactive element

When writing buttons / links / pressable cards for invented pages, add `:active` feedback. Without it, clicks feel dead:

```tsx
className="active:scale-[0.98] active:-translate-y-[0.5px] transition-transform"
```

Or in Tailwind shorthand: `active:scale-[0.98]`. Pure CSS, no JS. Should land on every `<Button>`, `<Link>`-as-button, and clickable card surface.

### 9. Skeleton loaders, never spinners

When writing `app/loading.tsx` or any in-page loading state for invented routes, use **content-shaped skeletons** (a `<Skeleton>` rectangle the size of the heading, etc.) instead of generic circular spinners. shadcn ships `<Skeleton>` and `tw-animate-css` ships the shimmer animation — combine.

This is already pinned in `references/loading.template.tsx`. The fallback rule reinforces: never reach for `<Spinner />` or a `<Loader2 className="animate-spin" />` as a default.

### 10. Stagger via CSS cascade, not JS

When you need a staggered reveal of N items (3 cards, 6 nav links) on a page that doesn't otherwise need JS animation, use CSS:

```tsx
{items.map((item, i) => (
  <div
    key={item.id}
    className="opacity-0 animate-in fade-in slide-in-from-bottom-4 fill-mode-forwards"
    style={{ animationDelay: `${i * 80}ms`, animationDuration: "600ms" }}
  >
    {item.body}
  </div>
))}
```

Pure CSS. Zero JS bundle cost. Achieves taste-skill's "staggerChildren" feel. If the project later adds `module-add motion`, the wrappers in `components/motion/` replace this pattern, but for the default scaffold, CSS cascade is the fallback.

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
  ]
}
```

This way the reviewer can see at a glance every place an opinionated default was chosen — and override any of them with one DESIGN.md edit.
