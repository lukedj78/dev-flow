# Case studies

Three projects built with the dev-flow suite. Each shows which skills were used and what was generated.

## Aetherfield — editorial SaaS landing

**Idea**: a quietly-opinionated platform-engineering SaaS landing page. Editorial voice, lime-green accent, Domine serif for display.

**Source for design**: a public Figma community file ("Aetherfield"). Read via `figma-to-design-md` Path C-bis (Playwright-assisted, since the file is community-public but no MCP/token was available).

**Skills used (in order)**:

1. `prd-from-idea` → `PROJECT.md` + `PRD.md` (one-page marketing site, no auth, no db).
2. `figma-to-design-md` (Path C-bis Playwright) → `DESIGN.md` with 11 colors extracted via k-means + visual font identification (Domine + Inter).
3. `design-md-to-app` → Next.js + shadcn + showcase + `MarketingShell` with `SiteTopNav` + `WordmarkFooter` (lime + olive wordmark).

**Output**:
- 1 marketing-style homepage with hero "Operational craft, on paper.", 3 feature cards, brand-banner CTA section.
- `/showcase` with 9-section design system reference.
- Lime brand wordmark in giant footer.

**Skills NOT used**: `prd-to-tasks` (1-page site, no need), `module-add` (static landing, no backend), `screenshot-to-page` (only 1 page, written by hand).

---

## Notarius — CRM per studi notarili italiani

**Idea**: a CRM for Italian notary studios. Anagrafica clienti, gestione pratiche, scadenzario, archivio documentale.

**Source for design**: a public Figma community file ("Phoenix CRM Legal Admin Dashboard"). The user was logged into Figma during the run, so `figma-to-design-md` was able to use the Variables panel directly.

**Skills used (in order)**:

1. `prd-from-idea` → `PROJECT.md` + `PRD.md` (5 user stories MVP, GDPR + multi-tenant constraints).
2. `prd-to-tasks` → `tasks.md` (17 tasks).
3. `figma-to-design-md` (Path C-bis Playwright + Variables panel) → `DESIGN.md` with 15 colors extracted EXACTLY from Figma Variables (no inference) + 10 typography levels.
4. `design-md-to-app` → Next.js + shadcn + theme system + `AppShell` with sidebar.
5. `screenshot-to-page` → home page with sidebar + 6 dashboard cards.
6. **Manual** → 6 placeholder routes (Pratiche, Clienti, Scadenze, Documenti, Timesheet, Impostazioni) using the `PlaceholderPage` component.
7. `module-add db` → Drizzle + Neon + multi-tenant schema (tenants/clients/practices/deadlines + audit_log).
8. `module-add auth` → better-auth + `/sign-in`.

**Output**:
- 12 routes (Dashboard / 6 placeholder / Showcase / Sign-in / api/auth + 2 internal).
- All HTTP 200, build green.
- Multi-tenant schema with 4 tables.
- Dark/light toggle with `D` keyboard shortcut.

**Skills NOT used**: `image-to-design-md` (Figma was used).

---

## Wisely — Wise-inspired multi-currency fintech

**Idea**: a Wise-clone. Multi-currency money transfers at mid-market rate. Bold billboard typography, lime CTA.

**Source for design**: a hand-written `DESIGN.md` provided by the user (pasted directly into the conversation). Wise Sans declared but flagged as proprietary — Inter used as open-source fallback.

**Skills used (in order)**:

1. `prd-from-idea` → `PROJECT.md` + `PRD.md` (5 user stories — send / multi-currency hold / activity / pricing / dashboard).
2. **Manual import** of user's `DESIGN.md` into `.workflow/DESIGN.md` (skipped `figma-to-design-md` and `image-to-design-md`).
3. `design-md-to-app` → Next.js + shadcn + theme + `MarketingShell` + `AppShell` + 12 routes.
4. **Manual** → page bodies (hero, pricing calculator, dashboard with balances, sign-in).
5. `module-add db` → Drizzle + Neon + schema (transfers/balances/beneficiaries/audit_log).
6. `module-add auth` → better-auth + `/sign-in`.

**Output**:
- 13 routes:
  - **Marketing**: `/`, `/personal`, `/business`, `/pricing` (with interactive calculator), `/help`, `/showcase`
  - **App**: `/dashboard`, `/send`, `/account`, `/transactions`, `/settings`
  - **Auth**: `/sign-in`, `/api/auth/[...all]`
- All HTTP 200, build green.
- Wise-style billboard hero ("Money beyond borders." at 126px, line-height 0.85).
- Lime CTA pill (`#9fe870`) with `scale(1.05)` hover + `scale(0.95)` active.
- Interactive pricing calculator with mid-market rate breakdown.
- Giant lime "wisely" wordmark in footer.

**Skills NOT used**: `figma-to-design-md`, `image-to-design-md` (DESIGN.md was hand-written), `prd-to-tasks` (skipped for brevity), `screenshot-to-page` (no Figma source = no screenshots).

---

## Patterns across the three

### What the suite is good at

1. **Pinning conventions early**. By the time you scaffold, the folder structure, the server-action shape, the showcase structure, and the theme system are decided — no debates downstream.
2. **Brand-specific output, not generic boilerplate**. The 3 showcases (Aetherfield, Notarius, Wisely) are visibly different despite using the same skill — because the DESIGN.md drives.
3. **Resumable**. You can stop after `prd-drafted` and pick back up days later. The orchestrator reads `meta.json#phase` and proposes the next step without re-asking.
4. **Standalone-skill-friendly**. `module-add db` works on a Notarius project AND on a Wisely project, because the contract is in `meta.json`.

### What the suite is NOT trying to be

- A code-gen tool that writes business logic. The skills generate **structure + UI shells + first-pass scaffolding**. Business logic stays human.
- A test framework. Each project has different testing needs.
- A CMS. Content is project-specific.
- A deploy automation. `module-add deploy` produces config; the actual deploy is the user's call.

### Which skills earn their keep

- **`design-md-to-app`** is the heaviest skill (77 KB) and the highest-leverage. It pins so many conventions in one shot that any inconsistency saved here pays off across every page added later.
- **`figma-to-design-md` Path C-bis** is the hidden gem. When the user is logged into Figma and the file has Variables, the skill extracts EXACTLY the brand palette in 30 seconds.
- **`module-add`** is small but load-bearing. The idempotency check + variant-references pattern means re-runs don't double-install.

### Which skills are most often skipped

- `prd-to-tasks` — when the project is simple enough that user stories are obvious, the task breakdown adds noise.
- `screenshot-to-page` — when there are no screenshots, or when there's only one (the home).
- `image-to-design-md` — when the user has Figma OR a hand-written DESIGN.md.

That's fine. The suite is designed so skills are **optional in sequence** — skip what doesn't apply, the orchestrator will route around.
