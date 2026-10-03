# Resources already analysed — look here before searching or inventing

This file exists because the user hands these over **so that nobody has to search the web or build
from scratch a second time**. It is the lookup table: one row per resource we have read against its
primary sources, what it is for, where the detail lives, and what we decided.

**Consult it first.** Before a `WebSearch`, before opening a vendor's landing page, and before
hand-rolling a component, a provider comparison or a motion token scale, check whether the question
is already answered here. The detail files carry the traps; this table only tells you which one to
open. If the resource is here and it fits, the work starts at step 5 of
`SKILL.md` §*Resources the user hands over* — review run, traps resolved, one yes missing.

**Every row carries a date, and the date means "this was true then".** The oldest are 2026-08-26;
anything older than a couple of months is a row to re-read before leaning on it, because prices and
licences move — Polar's free tier went from 4% + $0.40 to 5% + $0.50 in a single release.

**A row is short when a detail file exists, and carries the facts when it is the only record.**
Most rows state the verdict and point at the file with the traps. A few — Higgsfield, Videorc,
pdfcn — have no file of their own, so the row *is* the record and is longer on purpose. Trimming
those would lose facts with nowhere to go.

**These verdicts assume no commercial use.** Today the setup runs on free tiers, with one paid
subscription, so several rows are cheap because nothing ships commercially. They are conditional,
and the condition is worth naming before it changes:

| Row | Today | The day something ships commercially |
|---|---|---|
| **mapcn**, adopted | the default CARTO tiles are fine | they need a **CARTO Enterprise licence**, or another tile provider — a decision taken before shipping, not after |
| **Remotion** (`~/projects/video`) | free | free for individuals, non-profits and for-profit organisations with **up to three employees**; a content factory is commercial by construction |
| `launch-audit`'s identity block | a lighter obligation | **Article 5 of Directive 2000/31/EC** addresses commercial sites: name, geographic address, trade register, VAT number, *"easily, directly and permanently accessible"* |
| Arc UI, unlumen, Skillry, Videorc Premium, the Creem and Polar fees | moot | they become numbers to decide |

**GDPR does not move with this.** It follows personal data, not commerce, so `compliance-audit`
stands exactly as it is.

**Keep it honest.** A row states a **verdict and a date**, not a vibe. When a resource is added, read
its licence file rather than a badge and its price as the page serves it. When a verdict changes —
a price moves, a licence changes, we adopt something we had refused — edit the row and the date.

## Components and registries (web)

| Resource | For | Verdict | Detail |
|---|---|---|---|
| **mapcn** | maps, MapLibre GL | **adopted** · `stack.maps = "mapcn"`. ⚠️ default CARTO tiles need an Enterprise licence for commercial use — swap the provider before shipping (2026-08-26) | `design-md-to-app/references/maps-mapcn.md` |
| **React Flow** (`@xyflow/react`) | node graphs the user acts on | **adopted** · `stack.graphs = "react-flow"`. A read-only graph that fits the screen is cards, not a canvas (2026-09-15) | `design-md-to-app/references/react-flow.md` |
| **audiocn** (`@audiocn`) | audio UI: meters, faders, knobs, waveforms | **option, install after accepting C1** — its twelve audio tokens are a vocabulary DESIGN.md lacks; re-derive the values from DESIGN.md. MIT. `@base-ui/react` only with `fader`/`audio-player` (2026-10-02) | `design-md-to-app/references/audio-audiocn.md` |
| **gauge-ui** | gauges and dials, bounded ranges with zones | **option, cleanest we have read** — review clean, zero npm deps, no colour of its own. ⚠️ the read-only gauge carries no ARIA; `Control` does. MIT. **Considered and rejected against it: `antoniolago/react-gauge-component`** (201 stars, MIT, alive) — it is an npm dependency that pulls **d3 ^7.9.0** and unpacks to **776 KB** to draw an arc and a needle, it themes through its own props instead of inheriting the page's colour, and it has no draggable dial. gauge-ui is fourteen files of source you own, with nothing underneath (2026-10-03) | `design-md-to-app/references/gauge-gauge-ui.md` |
| **pdfcn**, **emailcn**, **ogimagecn**, **mcpcn** | PDFs, email templates, OG images, MCP | **options through `registry-intake`** — emailcn is the documented first choice for email templates. pdfcn live with **101 items** (48 ui, 40 blocks, 9 themes, 4 lib); ⚠️ its apex 308-redirects, so the registry URL needs `www.pdfcn.dev` (2026-10-03) | `design-md-to-app/SKILL.md`, `module-add/references/module-email.md` |
| **Koboyo** | hand-drawn illustrations | **option, default `null`** — an illustration is a stylistic commitment, only where DESIGN.md's language admits it (2026-08-26) | `design-md-to-app/references/illustrations.md` |
| **Coss/UI** (`@coss/*`) | design system on Base UI | **adopted as a 4th UI option** · `stack.ui = "coss"`, the one registry allowed `trust: "live"`. Live at `coss.com/ui/r/registry.json` with **579 items** (56 ui, 510 blocks, 6 lib, 3 font, 2 style, 2 hook) (2026-10-03) | `coss-ui/` |
| **React Bits** (`@react-bits`) | animated components | **port the motion, do not install** — asks `motion@^12` where we run 13 (D7), and one `SwipeToast` line is 1070 chars (S6). Take the `TS-TW` twin (2026-09-27) | `transitions/references/motion-catalogues.md` |
| **Watermelon UI** | 1,178 components | **port, do not install** — every item ships twice; **take the `-base` twin**, the other hardcodes `#3E3E43` and `text-[15px]` (2026-09-27) | `transitions/references/motion-catalogues.md` |
| **unlumen UI** (`@unlumen-ui`) | 80 animated components | **port, do not install** — installs under `components/unlumen-ui/`, a second namespace (golden rule 3). Pro $119 one-time (2026-09-27) | `transitions/references/motion-catalogues.md` |
| **Loading** | ~24 loaders | **reference only** — MIT; the discipline it teaches is skeleton over spinner (2026-09-27) | `transitions/references/motion-catalogues.md` |
| **Arc UI** (`@uiarc`) | 138 components, 83 blocks | **do not install** — `arc-foundation` defines 97 tokens on `:root` (C2) and every component ships a CSS Module our design lint cannot see. Licence good for agency work: $129/yr or $199 once, Pro source may ship inside a client deliverable (2026-09-30) | `transitions/references/motion-catalogues.md` |
| **agentcn** | eve tools from a registry | **blocked, and it is the worked example** — every tool declares `needsApproval`, which eve's loader rejects, so five side-effecting tools carry an approval that never loads (2026-09-15) | `registry-intake/SKILL.md` |
| **evex** | eve registry | **option through `registry-intake`**; porting eve code by hand is `eve-registry-porting`. Live at `www.evex.sh/r/registry.json` with 23 items; ⚠️ **`evex.dev` is a different, parked domain** — a typo lands on a lander, not the registry (2026-10-03) | `registry-intake/SKILL.md` |
| **AI Elements** | chat UI for eve | **option** — the default stays shadcn chat primitives (2026-09-01) | `eve-agent/references/ai-elements.md` |
| **nuqs** | URL state | **adopted** where filter state belongs in the URL (2026-08-26) | `data-fetching/references/nuqs.md` |

## Mobile

| Resource | For | Verdict | Detail |
|---|---|---|---|
| **mapcn-rn** | maps in Expo/RN | **adopted** · `stack.maps = "mapcn-rn"`. ⚠️ native modules → dev build, not Expo Go (2026-08-26) | `rn-components-apis/references/maps-mapcn-rn.md` |
| **Expo Device Hub** | seeing the app on a simulator | **not adopted** — the gap "the agent cannot see the mobile app" stays open; candidates Argent, agent-device (2026-09-08) | memory `reference_expo_device_hub` |

## Agent skills and mods (third party)

| Resource | For | Verdict | Detail |
|---|---|---|---|
| **`skills` CLI** (vercel-labs, MIT) | installing third-party skills | **the install path, and the user runs it** — the hook refuses `skills add` from the agent; `skill-review` → the user installs → `skill-approve` pins the sha256. Verified at `skills@1.7.0` (2026-09-30) | `dev-flow/references/external-skills.md`, `registry-intake/SKILL.md` |
| **shadcn's own skills** (`shadcn`, `improve`) | component work, codebase audits | **installed globally, reviewed 2026-09-30** — `improve` clean, `shadcn` needs a human (no frontmatter licence, `--force` on presets). Both were months stale; updated. Global installs sit outside every lock | `registry-intake/SKILL.md` §limits |
| **piano** (Martes AI) | turning an idea or a recurring chore into a plan, **after checking whether the thing already exists** | **its inventory stage taken and rewritten as `before-you-build.md`; the skill itself not installed** — stages 1 and 3 duplicate `prd-from-idea` and `brainstorming`, it writes plans outside `.workflow/`, and it ships with no licence (K8), so its text cannot enter a repo we deliver. Its last section also tells the agent to **rewrite the skill's own file** whenever the user corrects a plan, which under a content hash reports drift at the first correction. Its research script was read line by line — stdlib only, GET only, no key, writes nothing, `subprocess` solely for `gh` — and **none of it was copied**: `dev-flow/scripts/research.py` is ours, written against the same public endpoints, which are facts about those services rather than its work (2026-10-03) | this file |
| **Skillry** | design-led skills, paid | **do not adopt** — their own page says it is not for teams with a mature design system. $9.99/mo, $79/yr, $169 once; output sellable, package not redistributable (2026-09-30) | `dev-flow/references/external-skills.md` |
| **motion-video-kit** | commercial films, critic loop | **reference, free MIT** — two gates taken (frozen frames, loudness); the business playbook stays theirs (2026-09-30) | `dev-flow/references/external-skills.md` |
| **Claude Code mods** | panes, bands, tool-call hooks | **not dev-flow's work** — built and reviewed in a dedicated session, never from inside a project's flow. **No intake gate exists for them**, and they are the most powerful of the three third-party categories: see the lesson below (2026-10-03) | the mods session |

## Services and providers

| Resource | For | Verdict | Detail |
|---|---|---|---|
| **Creem** | payments, merchant of record | **option, the only EU-established MoR we have** — Armitage Labs OÜ (Tallinn), 3.9% + $0.40, no monthly. ⚠️ AWS Germany for servers but Supabase (US) for the database (2026-09-30) | `module-add/references/module-payments.md`, `dev-flow/references/eu-data-sovereignty.md` §4.8 |
| **Polar** | payments, merchant of record | **option** — free tier went to 5% + $0.50 in May 2026; Delaware entity, hosting not published (2026-09-30) | same |
| **Mollie**, **Adyen** | EU payment processors | **options, but not merchants of record** — they do not solve VAT (2026-09-15) | `dev-flow/references/eu-data-sovereignty.md` §4.8 |
| **Jev** (`experimental_evaluate`) | typed decisions, guards | **adopted where the state carries no personal data** — it is a model, so residency depends on how it is used; minimisation is the control (2026-09-22) | `eve-agent/references/eve-patterns.md` §13 |
| **Rizzo Flow** | self-hosted decision engine, Jev-compatible API | **option for confidentiality, not for cost** — Apache-2.0; Vercel has no GPU, Scaleway L4 ≈ €575/month (2026-09-22) | `eve-agent/references/eve-patterns.md` §13, memory `reference_rizzo_flow` |
| **rizzo-pii + osiria** | Italian legal PII | **adopted in Annotix** — three lessons in `eve-patterns` §6, `compliance-audit` R4 (2026-08-26) | memory `reference_rizzo_pii` |
| **Higgsfield** | AI image and video, 29 models | **not for a pipeline, option as a second adapter** — real API (`api.higgsfield.ai`, async + webhook), per-second pricing, but our Seedance 1.5 Pro 480p at $0.0121/s on the zero-markup Vercel gateway is cheaper than anything listed. Its unique value is Wan, LTX, MiniMax H3 and Genjutsu motion transfer (2026-09-30) | this file; `~/projects/video` carries the numbers |
| **Videorc** | screen recording, multistream | **tool, not a dependency** — AGPL-3.0 desktop app, free local 4K recording; Premium $39/mo or $32.50/mo yearly for cloud AI. Where our faceless-first rule says "screen recordings first", this is the recorder. Its `skills-lock.json` is where we got the hashed-skill idea (2026-09-30) | this file |

## Not a resource, a lesson

| | |
|---|---|
| **`skills-lock.json`** (seen in Videorc and audiocn) | a lockfile pinning third-party instruction files by **content hash** — the primitive our `skill-approve` now implements. Their `computedHash` is not reproducible from outside, so we compute our own (2026-09-30 in Videorc, 2026-10-02 in audiocn) |
| **A mod outranks a registry item and a skill** | it runs inside the client: a `tool.call` hook can **deny** a call, `$.env.get` reads environment variables, `$.http.fetch` calls any host, and `$.store` persists across sessions. `registry-intake` governs the other two categories; for mods there is no gate. **`claude plugin validate`** is the handle one would use: it lists statically what a module hooks, which variables it reads and writes, and what the engine would refuse — before any session loads it (2026-10-03) |
