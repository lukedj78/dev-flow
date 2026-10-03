# Resources already analysed — look here before searching or inventing

This file exists because the user hands these over **so that nobody has to search the web or build
from scratch a second time**. It is the lookup table: one row per resource we have read against its
primary sources, what it is for, where the detail lives, and what we decided.

**Consult it first.** Before a `WebSearch`, before opening a vendor's landing page, and before
hand-rolling a component, a provider comparison or a motion token scale, check whether the question
is already answered here. The detail files carry the traps; this table only tells you which one to
open. If the resource is here and it fits, the work starts at step 5 of
`SKILL.md` §*Resources the user hands over* — review run, traps resolved, one yes missing.

**Keep it honest.** A row states a **verdict and a date**, not a vibe. When a resource is added, read
its licence file rather than a badge and its price as the page serves it. When a verdict changes —
a price moves, a licence changes, we adopt something we had refused — edit the row and the date.

## Components and registries (web)

| Resource | For | Verdict | Detail |
|---|---|---|---|
| **mapcn** | maps, MapLibre GL | **adopted** · `stack.maps = "mapcn"`. ⚠️ default CARTO tiles need an Enterprise licence for commercial use — swap the provider before shipping | `design-md-to-app/references/maps-mapcn.md` |
| **React Flow** (`@xyflow/react`) | node graphs the user acts on | **adopted** · `stack.graphs = "react-flow"`. A read-only graph that fits the screen is cards, not a canvas | `design-md-to-app/references/react-flow.md` |
| **audiocn** (`@audiocn`) | audio UI: meters, faders, knobs, waveforms | **option, install after accepting C1** — its twelve audio tokens are a vocabulary DESIGN.md lacks; re-derive the values from DESIGN.md. MIT. `@base-ui/react` only with `fader`/`audio-player` (2026-10-02) | `design-md-to-app/references/audio-audiocn.md` |
| **gauge-ui** | gauges and dials, bounded ranges with zones | **option, cleanest we have read** — review clean, zero npm deps, no colour of its own. ⚠️ the read-only gauge carries no ARIA; `Control` does. MIT (2026-10-03) | `design-md-to-app/references/gauge-gauge-ui.md` |
| **pdfcn**, **emailcn**, **ogimagecn**, **mcpcn** | PDFs, email templates, OG images, MCP | **options through `registry-intake`** — emailcn is the documented first choice for email templates | `design-md-to-app/SKILL.md`, `module-add/references/module-email.md` |
| **Koboyo** | hand-drawn illustrations | **option, default `null`** — an illustration is a stylistic commitment, only where DESIGN.md's language admits it | `design-md-to-app/references/illustrations.md` |
| **Coss/UI** (`@coss/*`) | design system on Base UI | **adopted as a 4th UI option** · `stack.ui = "coss"`, the one registry allowed `trust: "live"` | `coss-ui/` |
| **React Bits** (`@react-bits`) | animated components | **port the motion, do not install** — asks `motion@^12` where we run 13 (D7), and one `SwipeToast` line is 1070 chars (S6). Take the `TS-TW` twin | `transitions/references/motion-catalogues.md` |
| **Watermelon UI** | 1,178 components | **port, do not install** — every item ships twice; **take the `-base` twin**, the other hardcodes `#3E3E43` and `text-[15px]` | `transitions/references/motion-catalogues.md` |
| **unlumen UI** (`@unlumen-ui`) | 80 animated components | **port, do not install** — installs under `components/unlumen-ui/`, a second namespace (golden rule 3). Pro $119 one-time | `transitions/references/motion-catalogues.md` |
| **Loading** | ~24 loaders | **reference only** — MIT; the discipline it teaches is skeleton over spinner | `transitions/references/motion-catalogues.md` |
| **Arc UI** (`@uiarc`) | 138 components, 83 blocks | **do not install** — `arc-foundation` defines 97 tokens on `:root` (C2) and every component ships a CSS Module our design lint cannot see. Licence good for agency work: $129/yr or $199 once, Pro source may ship inside a client deliverable | `transitions/references/motion-catalogues.md` |
| **agentcn** | eve tools from a registry | **blocked, and it is the worked example** — every tool declares `needsApproval`, which eve's loader rejects, so five side-effecting tools carry an approval that never loads | `registry-intake/SKILL.md` |
| **evex** | eve registry | **option through `registry-intake`**; porting eve code by hand is `eve-registry-porting` | `registry-intake/SKILL.md` |
| **AI Elements** | chat UI for eve | **option** — the default stays shadcn chat primitives | `eve-agent/references/ai-elements.md` |
| **nuqs** | URL state | **adopted** where filter state belongs in the URL | `data-fetching/references/nuqs.md` |

## Mobile

| Resource | For | Verdict | Detail |
|---|---|---|---|
| **mapcn-rn** | maps in Expo/RN | **adopted** · `stack.maps = "mapcn-rn"`. ⚠️ native modules → dev build, not Expo Go | `rn-components-apis/references/maps-mapcn-rn.md` |
| **Expo Device Hub** | seeing the app on a simulator | **not adopted** — the gap "the agent cannot see the mobile app" stays open; candidates Argent, agent-device | memory `reference_expo_device_hub` |

## Agent skills and mods (third party)

| Resource | For | Verdict | Detail |
|---|---|---|---|
| **`skills` CLI** (vercel-labs, MIT) | installing third-party skills | **the install path, and the user runs it** — the hook refuses `skills add` from the agent; `skill-review` → the user installs → `skill-approve` pins the sha256 | `dev-flow/references/external-skills.md`, `registry-intake/SKILL.md` |
| **shadcn's own skills** (`shadcn`, `improve`) | component work, codebase audits | **installed globally, reviewed 2026-09-30** — `improve` clean, `shadcn` needs a human (no frontmatter licence, `--force` on presets). Both were months stale; updated. Global installs sit outside every lock | `registry-intake/SKILL.md` §limits |
| **Skillry** | design-led skills, paid | **do not adopt** — their own page says it is not for teams with a mature design system. $9.99/mo, $79/yr, $169 once; output sellable, package not redistributable | `dev-flow/references/external-skills.md` |
| **motion-video-kit** | commercial films, critic loop | **reference, free MIT** — two gates taken (frozen frames, loudness); the business playbook stays theirs | `dev-flow/references/external-skills.md` |
| **Claude Code mods** | panes, bands, tool-call hooks | **build our own, install nobody's** — three wanted: collision guard, a band for the dev-flow gates, a cache-expiry handoff button. **No gate exists for mods**, which can deny tool calls, read `$.env` and call the network; `claude plugin validate` lists what a module touches | this file, until a `mod-review` exists |

## Services and providers

| Resource | For | Verdict | Detail |
|---|---|---|---|
| **Creem** | payments, merchant of record | **option, the only EU-established MoR we have** — Armitage Labs OÜ (Tallinn), 3.9% + $0.40, no monthly. ⚠️ AWS Germany for servers but Supabase (US) for the database (2026-09-30) | `module-add/references/module-payments.md`, `dev-flow/references/eu-data-sovereignty.md` §4.8 |
| **Polar** | payments, merchant of record | **option** — free tier went to 5% + $0.50 in May 2026; Delaware entity, hosting not published | same |
| **Mollie**, **Adyen** | EU payment processors | **options, but not merchants of record** — they do not solve VAT | `dev-flow/references/eu-data-sovereignty.md` §4.8 |
| **Jev** (`experimental_evaluate`) | typed decisions, guards | **adopted where the state carries no personal data** — it is a model, so residency depends on how it is used; minimisation is the control | `eve-agent/references/eve-patterns.md` §13 |
| **Rizzo Flow** | self-hosted decision engine, Jev-compatible API | **option for confidentiality, not for cost** — Apache-2.0; Vercel has no GPU, Scaleway L4 ≈ €575/month | `eve-agent/references/eve-patterns.md` §13, memory `reference_rizzo_flow` |
| **rizzo-pii + osiria** | Italian legal PII | **adopted in Annotix** — three lessons in `eve-patterns` §6, `compliance-audit` R4 | memory `reference_rizzo_pii` |
| **Higgsfield** | AI image and video, 29 models | **not for a pipeline, option as a second adapter** — real API (`api.higgsfield.ai`, async + webhook), per-second pricing, but our Seedance 1.5 Pro 480p at $0.0121/s on the zero-markup Vercel gateway is cheaper than anything listed. Its unique value is Wan, LTX, MiniMax H3 and Genjutsu motion transfer | this file; `~/projects/video` carries the numbers |
| **Videorc** | screen recording, multistream | **tool, not a dependency** — AGPL-3.0 desktop app, free local 4K recording; Premium $39/mo or $32.50/mo yearly for cloud AI. Where our faceless-first rule says "screen recordings first", this is the recorder. Its `skills-lock.json` is where we got the hashed-skill idea | this file |

## Not a resource, a lesson

| | |
|---|---|
| **`skills-lock.json`** (seen in Videorc and audiocn) | a lockfile pinning third-party instruction files by **content hash** — the primitive our `skill-approve` now implements. Their `computedHash` is not reproducible from outside, so we compute our own |
| **`claude plugin validate`** | lists statically what a mod hooks, which env vars it reads and what the engine would refuse — the review handle a future `mod-review` should use |
