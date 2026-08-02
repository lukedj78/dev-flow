# GDPR + EU AI Act checklist & remediation recipes

The 10 risks the skill audits, each with: **what it is**, **audit signals** (what to look for / what `scan.py` flags — verify in code before reporting), **safe-fix** (auto-apply, reversible), and **flag** (decision — never auto-decide). **Not legal advice.**

Severity guide: **H** = likely non-compliance or store rejection · **M** = gap that needs a control · **L** = hardening.

---

## R1 — DSAR: data export & erasure · Art. 15/17/20 (+ Apple 5.1.1(v) / Play) · H

**Audit signals:** auth/user tables exist (`user`/`session`/`account`, Supabase `auth.users`, Firebase Auth) but no route/function for **account export** or **account deletion**; sign-in/out only. Mobile with an account and no in-app delete = **store-rejection risk**, not just GDPR.
**Safe-fix:**
- Web: `lib/server/account.actions.ts` with `exportMyData()` (gathers all rows for the current tenant/user → JSON) and `deleteMyAccount()` (erasure **cascade** across the user's tables, `archivedAt`→hard-delete after grace, revoke sessions), both re-checking tenancy; a `/settings/privacy` UI (reuse `forms`).
- Mobile: a `deleteAccount()` in the auth lib (Supabase → server function `supabase.auth.admin.deleteUser` + row cleanup; Firebase → `user.delete()` + Firestore cleanup) + a settings entry.
- eve agent: add `export_memories(scope)` and `erase_all_memories(scope)` tools (both `approval: always()`, scope from `requireTenantCaller(ctx)`) so a DSAR is end-to-end, not per-key `forget`.
**Flag:** grace period / legal-hold exceptions; whether soft-deleted rows count as erased for your basis.

## R2 — Consent & cookies · Art. 6/7, ePrivacy · H

**Audit signals:** no cookie-consent banner / `lib/consent`; `next-themes` or analytics set cookies/localStorage before consent; sign-up/auth forms with no ToS/privacy checkbox; the `forms` audit A–J doesn't check consent.
**Safe-fix:** a `CookieConsentBanner` + `lib/consent.ts` gate that blocks non-essential cookies/scripts until consent (default-decline non-essential); a consent-field pattern in the sign-up form; `/legal/privacy` + `/legal/cookies` page stubs (with the caveat banner).
**Flag:** the **lawful basis** per processing purpose and the exact consent copy — legal wording is a decision, not a scaffold.

## R3 — International transfer & EU data residency · Art. 44+ · H (eve) / M

**Audit signals:** `stack.db="neon-drizzle"`/`supabase`/`firebase` with no EU-region marker; `DATABASE_URL` = generic `*.neon.tech`; Vercel default `iad1`; `stack.agent="eve"` → prompts routed through the AI Gateway to US LLM providers (Anthropic/OpenAI/Google); voice audio → US.
**Safe-fix:** a note in `docs/compliance/` + `meta.json#compliance.data_residency` flag; a data-minimization pass so prompts/logs carry no unnecessary PII.
**Flag:** *which* EU region to pick (Neon/Vercel/Supabase project region) and whether **SCCs / adequacy / a provider DPA** are in place — a contractual/product decision. Note: self-hosting the eve app runtime does **not** relocate the LLM inference call.

## R4 — Retention, TTL & PII-scrubbing · Art. 5(1)(e) · H (eve) / M

**Audit signals:** durable stores with no TTL/cleanup — eve event-log + persisted `events` (full transcripts = personal data), `auditLog` metadata, `session`/`verification` tables, soft-deleted rows never purged, TanStack Query `PersistQueryClientProvider` (whole cache to AsyncStorage) not cleared on sign-out, uploaded files, realtime payloads, voice transcripts.
**Safe-fix:** a documented retention policy (`docs/compliance/retention.md`); a cleanup/TTL **job stub** tied to the R1 erasure path; purge persisted caches on sign-out; a `lib/log.ts` redaction helper.
**Flag:** the retention **periods** per data class (a product/legal decision).

## R5 — AI transparency & synthetic content · AI Act Art. 50 · H

**Audit signals:** a chat/agent/voice surface (eve `useEveAgent`, `chat-and-typeset` primitives, `module-voice`) whose only "AI" signal is an avatar/`"Assistant"` label; no first-turn/persistent disclosure; TTS output not labeled as AI-generated.
**Safe-fix:** bake an explicit "you're interacting with an AI system" disclosure into `agent/instructions.md` **and** the chat UI (persistent header or first message); label synthetic voice output as AI-generated where the platform doesn't already.
**Flag:** none usually — this is a hard requirement; only the copy/placement is adjustable.

## R6 — High-risk classification & DPIA · AI Act Annex III; GDPR Art. 35 · M/H

**Audit signals:** the product's domain touches **credit/creditworthiness, employment/recruitment, access to essential services, education/exam scoring, biometric categorization, law enforcement, migration** (from PRD/PROJECT.md or the app's purpose), yet no DPIA / risk-management artifact exists.
**Safe-fix:** if high-risk is suspected, drop `docs/compliance/dpia-template.md` (a blank DPIA scaffold) — do **not** fill it in.
**Flag:** the classification itself and the full Annex III conformity duties (risk management, data governance, accuracy/robustness, technical documentation, conformity assessment) — a decision + likely external counsel.

## R7 — PII in logs · Art. 32 · M

**Audit signals:** `console.error(e)` / `console.log(<errorOrToken>)` on the server or in shipped RN code; raw backend error `detail`/`title` toasted to the client; realtime message payloads logged.
**Safe-fix:** a `lib/log.ts` (or RN equivalent) with a redaction step; replace raw `console.error(e)` with the scrubbing logger; strip PII from error text before it reaches a toast or a third-party sink.
**Flag:** none.

## R8 — Sub-processors & DPA · Art. 28 · M

**Audit signals:** third parties receiving personal data — LLM provider(s), Vercel (host/AI Gateway/Sandbox/Connect), Neon/Supabase/Firebase, Resend, Linear (via `linear-scrum`), RevenueCat, Expo push relay — with no sub-processor register or DPA note.
**Safe-fix:** **generate `docs/compliance/subprocessors.md` from `meta.json#stack`** — one row per provider (service, data categories, region, DPA-link `TODO`). It's a standing customer-facing artifact, not one-time setup.
**Flag:** obtaining/verifying each DPA.

## R9 — Special-category data · Art. 9 · M/H

**Audit signals:** an agent/memory or forms that can collect health, religion, political opinion, sexual orientation, union membership, biometric/genetic, racial/ethnic data (eve memory guardrail lists only secrets; voice = biometric-adjacent).
**Safe-fix:** extend the eve memory guardrail to refuse Art. 9 data unless an explicit-consent flow exists; treat voice as potentially biometric.
**Flag:** the Art. 9(2) legal basis + explicit-consent implementation.

## R10 — Memory & manipulation · AI Act Art. 5 · M

**Audit signals:** durable per-user memory/personalization used (or usable) to build behavior-scoring or engagement-optimizing features against the user's interest.
**Safe-fix:** add a guardrail line to the memory instructions: "memory is for user-requested continuity, not for behavior-scoring or manipulative personalization."
**Flag:** product review of any personalization that steers user behavior.

---

## Cross-cutting notes

- **Credit where due — don't over-report.** Strong controls already common in dev-flow projects: fail-closed auth, tenant isolation, per-tenant encrypted secrets, RLS, security headers, secure-store, eve approval/HITL (Art. 14 oversight), eve durable event log (Art. 12 traceability). Report these as *satisfied*, not as gaps.
- **Reuse, don't reinvent:** where `module-add` (auth/db/email/storage), `forms`, `design-md-to-app`, or `rn-module-add` own the surface, invoke/extend them for the fix instead of hand-rolling.
- **For `stack.agent = "eve"` projects, two eve recipes are the safe-fix** (`eve-agent/references/eve-patterns.md`): the **audit-hook** (#5) is Art. 12 traceability + the R7-safe way to record agent activity (store event *shape*/ids, not PII payloads); the **read-vs-egress data boundary** (#6) is the concrete control for R3 (no customer text in third-party/LLM calls), R7 (nothing sensitive logged) and R4 (nothing from a record into the sandbox `/workspace`). When auditing an eve agent, check these exist before flagging R3/R7.
- **Every generated artifact** (report, subprocessors, retention, DPIA, privacy pages) carries the **"not legal advice — DPO/counsel must confirm"** caveat.
