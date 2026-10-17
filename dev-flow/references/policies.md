# dev-flow policies

Read the one that applies before acting on it; the index is in `SKILL.md` §Step 2.
Moved out of `dev-flow/SKILL.md` on 2026-10-17 to cut the router's every-turn cost; SKILL.md keeps an
index line pointing here. The text is unchanged.

## Step 2 policies

**Inventory policy — before you build, look.** The cheapest step in the flow and the one most often skipped: **does this already exist?** Follow **`references/before-you-build.md`** — the house first (installed skills and commands, scripts on disk, `references/resources.md`, the project's own `.workflow/`), then **the tools already paid for**, then the Claude ecosystem, then outside with the evidence typed as *shipped source · code · official source · experience* — and **for a default, a limit or anything about what leaves the machine, the shipped artefact outranks the page describing it** (`npm pack` needs no install; the page states the intent, the compiled `dist` states the behaviour). It runs **before** `prd-from-idea` on a new idea, **before** `module-add` on a new capability, and **before** writing a new skill — and it closes with a verdict in one line: *we already have it · it exists outside and adapts · it exists halfway · it does not exist*. **"We already have it" is the best outcome and the most frequent**, and it is written down anyway, because in six months it saves doing the search again. The verdict lands in `resources.md` when it is a third-party resource, or in the PRD under *what exists already* when it is a build.

**Wireframe policy — every screen before any code.** The user's standing rule (2026-10-10), for every project with a UI. Between `design_extracted` and the scaffold, `wireframe-canvas` builds `docs/wireframes/screen-inventory.md` (every route and screen of every epic, mapped to the PRD's `US-N` stories, with roles and loading/empty/error/success states; every story maps to ≥1 screen), then draws one **desktop (1440)** and one **phone (390)** artboard per screen on a claude.ai **Design** canvas (`Artifact action:"quickstart" intent:"design"`), high fidelity in DESIGN.md with real copy in the user's language, one canvas page per area, reviewed by the user area by area. **No feature code and no scaffold until the user explicitly approves the canvas**: `update_meta.py set-phase` refuses `monorepo_initialized` / `scaffolded` until `meta.json#wireframes` is approved, or skipped with a reason. After approval, a PNG of every artboard goes to `docs/wireframes/png/` and is commented on each GitHub or Linear issue whose story maps to the screen (`wireframes.screenshots_posted_at`). Agent-only projects have no screens and are not affected.

**Infrastructure policy.** `project-infra-setup` sets up the project's **third-party environments from the CLI**: the GitHub repo, the Vercel project and its region, marketplace connectors (Neon, Blob, Resend), DNS and domains, environment variables and secrets, and the sub-processor register. Propose it **when a module is about to need an account that does not exist yet** (`module-add db | email | storage | deploy`), or when the user asks to configure Vercel, Neon, Resend or a domain. It is **outward-facing**: each repo, project, database, DNS record and key is confirmed with the user one at a time; secrets never go through chat; the region of every service is checked before and after creating it; anything a tool installs on its own (integrations drop third-party agent skills into the repo) is reviewed first. It does not bump `phase`; it appends `history`. Code that uses the services stays with `module-add`; deploying stays with `vercel-deploy`.

**Project-management policy (Linear + scrum).** Every project is run in **Linear with agile scrum** unless the user explicitly opts out. When `tasks.md` exists (phase `tasks_split`, or `prd_drafted` once tasks are generated), propose `linear-scrum` **Setup**. `linear-scrum` is also a **horizontal capability** — invoke it any time for **Sync** (push new tasks, plan the sprint, report velocity), regardless of `phase`. It records `meta.json#linear` + `#scrum` and appends `history`, but never bumps `phase` and never gates progression. For an existing project already partly in Linear, `linear-scrum` **Adopt** backfills the link.

**Compliance policy (GDPR + EU AI Act).** `compliance-audit` is a **horizontal capability** — invoke it any time to audit an existing project against the 10-point GDPR/AI-Act risk register (DSAR, consent, EU data residency, retention/PII, AI-transparency, high-risk, sub-processors…) and, on request, apply the **safe** remediations while flagging the legal decisions. dev-flow **proposes it as a pre-deploy gate**: when a project reaches `feature_complete` (before `vercel-deploy` / `rn-eas-deploy` / `eve deploy`), and again in the `deployed` maintenance loop (re-audit after material changes). It records `meta.json#compliance` + appends `history`, **never bumps `phase`**, and never *blocks* deploy on its own — it surfaces findings so the user decides. Especially relevant when `stack.agent = "eve"` (AI-transparency + memory/residency risks) or the product handles user accounts (DSAR + Apple/Play deletion). Not legal advice — it produces engineering findings + a DPIA template, a DPO/counsel confirms.

**Cost/perf policy (Vercel).** `vercel-doctor` is the **cost/performance sibling** of `compliance-audit` — a horizontal pre-deploy gate for web projects on Vercel. It wraps the third-party `vercel-doctor` CLI (scans a Next.js codebase for costly Vercel patterns — caching that defeats the CDN, dead code, function duration, image waste, excessive invocations, config), applies the safe mechanical fixes, and **routes the real fixes to the owning skill** (`data-fetching` for caching/invocations, `design-md-to-app` for images). Proposed at `feature_complete` (beside `compliance-audit`) and in the `deployed` loop. Records `meta.json#vercel_doctor` + `history`, **never bumps `phase`**, never blocks deploy on its own. Refuses for non-Vercel/non-Next targets.

**Review policy (spec + conventions).** `spec-review` reads the **change**, not the finished artefact — which is what separates it from the four pre-deploy gates. Two axes in parallel sub-agents, **never merged**: *Spec* (does the diff implement what `.workflow/PRD.md` + `tasks.md` asked?) and *Standards* (does it obey the golden rules, the declared `meta.json#stack`, and the discipline skills — with a Fowler smell baseline as the floor). One combined verdict would let either axis hide behind the other: code can follow every convention and build the wrong feature, or build exactly the right feature ignoring the stack the project declared. Propose it **when a chunk of work lands — a page, a module, a PR, a batch of agent branches — regardless of the phase recorded in `meta.json`**, not only before shipping and not only at `page_generated` / `module_added`: a spec finding is cheapest while the branch is open, and a phase left behind must not switch the review off (smart-travel built for three days at `design_extracted`, and `spec-review` was never proposed). Records `meta.json#spec_review`; **never bumps `phase`**; never blocks. It is **not** Claude Code's built-in `/code-review`: that one reviews code generically and knows nothing about `.workflow/`. Without a `.workflow/`, `spec-review` refuses and points there instead.

**Parallel build policy (several agents at once).** When the orchestrator fans a build out to sub-agents or worktrees — one PR per screen, one branch per issue — the speed multiplies whatever each agent gets wrong, because every agent copies the neighbouring file. smart-travel, one night: 24 PRs, 57 of the 71 hand-made buttons the later audit found, each PR adding 1–9 elements copied from the file next to it; an agent's report even said the badge was a span «because Badge has no variant», and the orchestrator read it and merged. So, every time:
1. **Every brief carries golden rule 3 and its lint rule, verbatim**: «Every piece of UI is a primitive from `components/ui/` (read `design-md-to-app/references/primitives-first.md` first). When the board differs, tune the primitive's `cva` variant and DESIGN.md tokens until it matches pixel by pixel — never accept the drift, never rebuild the look with call-site classes; a new variant goes into DESIGN.md first. No raw `<button>`/`<label>`/`<a>`/`<hr>`/`<img>`/`<details>`, no hand-written role, no `div`/`span` redrawing a Card/Badge/Alert/Separator — `design/no-handmade-ui` reports it and the write-time guard refuses it. If no primitive can render it without a fork, stop and report it; do not write it by hand and do not `eslint-disable` it. Converting an existing screen: screenshot before and after, and the pixel diff must be zero.» The guard must be installed before the fan-out (`setup_design_lint.py --check`): it is what stops a sub-agent while it writes.
2. **Before accepting any PR or agent diff, the orchestrator runs on it**: the project's lint on the changed files (`design/no-handmade-ui` must be zero on them), **`spec-review`'s Standards axis**, and a search for raw elements in the added lines — `git diff <base>... -U0 -- '*.tsx' | grep -E '^\+.*<(button|label|input|select|textarea|hr|details|summary|dialog|progress|meter|table|img|a)[ >/]|^\+.*role="(tab|radio|checkbox|switch|menu|menuitem|listbox|option|dialog|tooltip|progressbar|separator)"'`. Any hit is sent back, not merged.
3. **An agent report that says a primitive "had no variant" is a stop, not a note**: nothing that works around it is merged; the variant is added (DESIGN.md first, then the `cva`) and the user is told which one.
4. **A green lint and screenshots that match the boards are never accepted as proof of conformity to the primitives** — a hand-made button identical to the board passes both. The proof is the rule at zero on the diff and no raw element in it — **and**, for a converted or new screen, a pixel diff at zero against the board or the before-screenshot: primitives used as they ship pass the lint while the screen drifts (smart-travel, 2026-10-12: the user rejected the converted screens).

**UI-quality policy (accessibility + fundamentals).** `shadscan` is one of the **four pre-deploy gates**: `compliance-audit` reads the **legal** surface, `vercel-doctor` the **cost** surface, `shadscan` the **UI** one, and `launch-audit` the **commercial** one (can a stranger find it, trust it, buy from it). It wraps the third-party `@shadscan/cli` — a deterministic, read-only static audit of a React/shadcn app across six categories (Foundation, Interaction, States, Accessibility, Forms, Production Polish) scored out of 100 with file:line evidence — applies the high-confidence fixes, surfaces the product `decide` items to the user, and **routes the real corrections to the owning skill** (`forms` for form wiring, `transitions` for reduced-motion, `data-fetching` for Suspense/loading boundaries, `design-md-to-app` for shell/empty-state/metadata, `composition-patterns-guide` for anatomy). It is the only thing in dev-flow that can **mechanically verify our own contract landed** — that the `prefers-reduced-motion` guard `transitions` mandates and the error association `forms` prescribes are actually in the built UI. Proposed at `feature_complete` and in the `deployed` loop. Records `meta.json#shadscan` + `history`, **never bumps `phase`**, never blocks deploy on its own. **Never optimise for the score** — adding unused infrastructure to raise the number is a regression that scores well. Web only (DOM/React rules); refuses for `expo-rn`.

**Animated icons.** `animated-icons` adds one Motion-animated Heroicon from the `@heroicons-animated/*` shadcn registry (ecosystem-first: don't hand-animate an SVG). It requires the `motion` runtime (`module-add motion`) and enforces the `transitions` reduced-motion discipline the raw components lack. Web only; horizontal; no phase bump.

The orchestrator must propose, not impose. After deciding, **tell the user the proposed next step in one sentence**, and ask for confirmation before invoking (in an autonomous run — §Autonomous runs — write the proposal into the report and continue). Example: *"You're at `design_extracted` (DESIGN.md + 6 screenshots in place). I propose running `design-md-to-app` to scaffold a Next.js + shadcn project. OK to proceed, or do you want to add modules / change stack first?"*

## Shipping the product's own agent-skill

Every product this flow builds may end up with an API. One that only its own
frontend calls is an implementation detail. One that **somebody else's coding
agent could drive** is a distribution channel — and it needs a single artefact to
be usable: a skill file telling that agent how the product works.

**Raise it once, at `feature_complete` → `deployed`,** when all three hold:

1. the product has a callable surface that is not only its own frontend —
   route handlers under `app/api/`, an OpenAPI spec, a public eve agent
   (`stack.agent = "eve"`), or an MCP server; **and**
2. there is a deployed origin to put in the file; **and**
3. `meta.json#stack.agent_skill` is not set yet.

Then say it plainly, once: *"your product is something a coding agent could
drive — want me to write its agent-skill, so your users can install it and use
`<product>` from Claude Code or Cursor?"* If yes, route to
**`product-to-agent-skill`**.

⚠️ **What it produces belongs to the product, not to dev-flow.** The file lands
in `<product-repo>/skills/`, ships and versions with that product, and is aimed
at whoever installs *that* repo. It is never added to dev-flow's own skills,
never copied into `~/.claude/skills/`, and never listed in `install.sh` —
the same relationship dev-flow has with the `app/` it builds and does not own.

Don't raise it when the API exists only to serve the product's own pages: a
skill describing an internal route handler is a lie with a nice table in it.

## Resources the user hands over — analyse, record, then actually use

The user pastes a URL: a component registry, a library, an agent skill, a mod, a service, an article.
That is not small talk and it is not a request for a summary — it is **material for the product**, and
it is handed over for one reason: **so that nobody has to search the web or build the same thing from
scratch a second time.** The work has two halves. Documenting it is the first. Using it when the need
arrives is the second, and the one that gets skipped.

**`references/resources.md` is the index of everything already analysed** — every registry, library,
skill, mod, provider and model, with its verdict, its date and which file carries the detail. **Read
it before a `WebSearch`, before opening a vendor's page, and before hand-rolling** a component, a
provider comparison or a motion scale: the answer is often already there, read against primary
sources, with the traps written down. This rule is retroactive — it covers everything analysed in
past months, not only the resource that arrived today.

Every new resource ends with **a row in that index**, whatever the verdict. A refusal is worth as much
as an adoption: Arc UI's row exists so nobody re-reads it in three months and reaches the same
conclusion from zero.

**On arrival.**

1. **Classify it**, because the gate differs: a shadcn-format registry → `registry-intake review`; a
   third-party agent skill → `registry-intake skill-review`; a **mod** (a Claude Code plugin) → not dev-flow's:
   mods are built and reviewed in their own session, and no intake gate exists for them — say both; a paid service → the three-option comparison (DIY / self-hosted / managed),
   price first, privacy separated from lock-in; a technique or article → no code, so a reference or
   nothing.
2. **Read primary sources, never the landing page.** The registry item's own JSON, the `LICENSE` file
   rather than GitHub's badge (gauge-ui and audiocn are MIT in a lowercase `license.md`, which GitHub
   reports as *"Other"*), the DPA's sub-processor annex, the pricing page as served.
3. **Record it where the need will arise**, not in a general list. A component domain →
   `design-md-to-app/references/<domain>-<name>.md` **plus a row in that skill's routing table**; a
   motion catalogue → `transitions/references/motion-catalogues.md`; a provider that processes personal
   data → `dev-flow/references/eu-data-sovereignty.md`; a third-party skill → `external-skills.md`. The
   test is simple: the next person meets it **when they need it**, not when they go browsing. Then the
   row in `references/resources.md`, which is what makes it findable at all.
4. **Price first, licence as a dated fact you checked.**

**When the need arrives — this is the half that matters.**

5. **Do not stop at "it is an option".** Carry the work to the point where **only one yes is missing**:
   the review run, the report shown, and the traps already resolved — the `aria-label` gauge-ui's
   read-only gauge does not carry, audiocn's twelve tokens re-derived from DESIGN.md. Then ask the one
   question the gate requires, install, and **show the thing working**.
6. **The gates do not move.** `allow`, `approve` and `skill-approve` stay the user's decisions and the
   hook still asks — that rule was measured and it holds. What changes is that the request arrives with
   everything else already done, never as *"shall I start?"*.
7. **If it is the wrong answer here, say so in one line and proceed** with the alternative. Do not
   reopen the analysis each time the subject comes up.

A resource analysed and never applied is research nobody bought. The reference is the means; the
working result is the deliverable.
