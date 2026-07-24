# GDPR & EU AI Act — compliance assessment of the dev-flow skills

> **Date:** 2026-07-24 · **Status:** risk assessment (living doc).
> **This is NOT legal advice.** It is a structured engineering risk review. GDPR/AI-Act compliance depends on the *deployed product* — its real data, purposes, legal basis, and configuration — not on tooling in the abstract. A DPO / qualified counsel must sign off before relying on any of this.

## Scope

Two questions:
1. Do the **skills themselves** violate GDPR / the AI Act? (They are horizontal, neutral tooling.)
2. Do the **scaffolds they generate** — and our **developments** built on them — create compliance risk by omitting required controls?

## Verdict

The skills **do not violate** the regulations — they are neutral tooling. The real exposure is that **default scaffolds under-provision compliance controls**, so a product built with them can end up non-compliant unless the deployer deliberately adds consent, data-subject rights (DSAR/erasure), retention, AI disclosure, and EU data residency. Several eve patterns already *help* (security, tenant isolation, human-in-the-loop, audit logging).

## GDPR

**Strengths already in the design**
- **Art. 32 (security):** eve fail-closed auth, multi-tenant isolation (`tenantId` from the verified session, never model input), per-tenant encrypted secrets, approval-gating; `eve-registry-porting` enforces a tenant-safe checklist.
- **Art. 25 (privacy by design) — partial:** the multi-tenant-memory pattern explicitly forbids storing passwords/tokens/payment data/one-time codes and states retention/export/deletion are "bounded by product policy" — privacy-aware, but **advisory**, not enforced.
- **Accountability/logging:** eve's durable event log + instrumentation give traceability.

**Gaps / risks (default scaffolds omit these)**
| # | Area | Article(s) | Risk |
|---|---|---|---|
| G1 | Legal basis & consent; cookie/ePrivacy | 6, 7; ePrivacy | `forms`/`module-add auth` collect PII without consent capture; no cookie-consent banner scaffolded |
| G2 | Data-subject rights (access/export/erasure/rectification) | 15–17, 20 | no DSAR export / erasure endpoints generated; eve long-term memory has `forget` but no DSAR flow |
| G3 | Data minimization & retention | 5(1)(c),(e) | Drizzle schemas + eve event-log (full conversations = personal data) without TTL / scrubbing |
| G4 | International transfers / residency | 44+ | Neon, Vercel, AI Gateway → US; prompts (may contain PII) go to US LLM providers; EU regions not surfaced |
| G5 | Sub-processors / DPA | 28 | LLM providers, Vercel, Neon, Linear (linear-scrum), PostHog/Mixpanel — DPAs + register not prompted |
| G6 | PII in logs/telemetry | 5, 32 | app logs + analytics may capture PII without scrubbing |
| G7 | Automated decision-making | 22 | agents that act (Gym Coach, BidMaster) may make consequential decisions without safeguards |
| G8 | Special categories | 9 | Hospitality (guest data), health-adjacent apps — no special-category handling |

## EU AI Act

Our skills are **horizontal**, so the risk is that they let someone build a **high-risk** AI system (Annex III: employment, credit, essential services, biometrics) **without** the required safeguards. No skill inherently enables **prohibited practices (Art. 5)** — no social scoring, no emotion recognition, no realtime biometric ID (`streamTranscribe` is STT, not emotion recognition).

**Strengths**
- **Human oversight (Art. 14):** eve approval / HITL is exactly the control high-risk systems need.
- **Traceability (Art. 12):** durable event log + instrumentation.
- **Deployer obligations:** already codified in `eve-agent`'s `references/eve-concepts.md` §Responsible use.

**Gaps / risks**
| # | Area | Article | Risk |
|---|---|---|---|
| A1 | Transparency | 50 | chatbots must disclose they are AI; synthetic voice (TTS `module-voice`) must be labeled — not enforced in scaffolds |
| A2 | Risk classification not triggered | (Annex III) | `prd-from-idea` never asks "is this high-risk?"; a project can be born high-risk without activating risk-mgmt/data-governance/accuracy/conformity |
| A3 | Profiling via memory | — | long-term memory + profiles risky if used for consequential decisions without oversight |
| A4 | GPAI | 53+ | model-provider obligation, not ours — but verify the chosen provider's EU posture |

## Development-level hotspots (from project memory)

- **Desko** (office presence) → **employee monitoring**: worker data, purpose limitation, information/works-council — sensitive GDPR area.
- **EVE Hospitality** → guest PII, possible special categories → DSAR + retention critical.
- **BidMaster** (banking/insurance RFP), **Gym SaaS** (Coach *executes actions*) → potential consequential automated decisions → check AI-Act high-risk + GDPR Art. 22.

## Recommendations (guardrails — not yet applied)

1. A **privacy/compliance-by-design reference** that `module-add auth/db` and `design-md-to-app` follow: consent, DSAR export + erasure endpoints, retention config, privacy policy + cookie consent, data minimization, **EU region option** (Neon/Vercel), sub-processor list/DPA.
2. **AI disclosure** in chat scaffolds + the eve agent (Art. 50); **label synthetic content** (voice).
3. **eve memory/log:** enforce retention + erasure + **PII-scrubbing**; **DSAR export of memory**.
4. **Risk-classification prompt** in `prd-from-idea`: high-risk (credit/employment/essential services/biometrics)? → activate the AI-Act high-risk checklist.
5. **Explicit caveat** (aligned with eve responsible-use): skills produce scaffolds, **not** legal compliance; the deployer is responsible.

## Per-skill audit

The findings below come from a per-skill review (parallel agents) against the GDPR + AI-Act checklists above. Each finding names the skill, the control it touches, whether it's a risk or OK, severity, and a specific fix.

Run: 4 parallel read-only agents over web-data, web-scaffold, eve-agent, and mobile skill batches (2026-07-24). Consolidated below.

### Cross-cutting risk register (ranked)

| # | Risk | Sev | Skills / scaffolds affected | Fix (owner) |
|---|---|---|---|---|
| R1 | **No DSAR: export / erasure never scaffolded** (Art 15/17/20). Also an **Apple 5.1.1(v) + Google Play** in-app-account-deletion *store-rejection* risk, not just GDPR. | **H** | module-auth, forms, module-db, data-fetching · rn-module-add, rn-backend, rn-publishing-payments · eve memory (only single-key `forget`) | Scaffold `export`/`deleteAccount` endpoints + erasure cascade; eve `export_memories`/`erase_all_memories`; RN `deleteAccount` wiring; store checklist item |
| R2 | **No consent capture / cookie banner** (Art 6/7, ePrivacy). | **H** | design-md-to-app (no cookie banner; `next-themes` writes silently), forms (no consent checkbox; audit A–J misses it), module-auth (no ToS/privacy checkbox), rn-push/ATT (consent not logged) | Scaffold `CookieConsentBanner` + `lib/consent.ts`; consent-field pattern in forms/auth; log push/ATT consent |
| R3 | **International transfer / EU residency never flagged** (Art 44+). | **H** (eve) / M | eve (prompts→US LLM via AI Gateway), module-voice (audio→US), module-db (Neon US default), module-storage (Vercel `iad1` as "latency"), rn-module-add/rn-backend (Supabase/Firebase region) | Flag transfer + require DPA/SCC; surface EU-region option in stack; data-minimize prompts |
| R4 | **No retention / TTL / PII-scrubbing** (Art 5(1)(e)). | **H** (eve) / M | eve event-log + persisted `events` (full transcripts), module-db soft-delete (no purge), module-auth sessions, module-storage files, module-realtime payloads, rn-data-fetching AsyncStorage cache, module-voice transcripts | Retention policy + deletion job tied to R1; purge persisted caches on sign-out; log TTL |
| R5 | **AI transparency (Art 50) absent** — no "you are talking to an AI" disclosure; synthetic voice unlabeled. | **H** | eve-agent (chat + `instructions.md`), design-md-to-app chat-and-typeset (avatar only), module-voice, screenshot-to-page (inherits) | Mandatory first-turn/persistent AI disclosure; label synthetic audio |
| R6 | **High-risk classification never triggered** (AI Act Annex III). | **M/H** | prd-from-idea (interview has no high-risk Q), prd-to-tasks (no compliance rung), eve-agent (domains named only as approval triggers) | Add high-risk + personal-data questions to prd-from-idea; a "Privacy & compliance" decomposition rung |
| R7 | **PII in server logs** (Art 32). | **M** | design-md-to-app (`console.error(e)`), forms (raw `detail` in toast), module-realtime, rn-push (`console.log(token)`) | Redaction step / scrubbing note before any log sink |
| R8 | **Sub-processors not disclosed** (Art 28). | **M** | eve (LLM providers, Vercel), linear-scrum (Linear US), module-email (Resend), rn-push (Expo relay), rn-publishing-payments (RevenueCat) | Sub-processor register + DPA note; `meta.json#stack` already = a machine-readable inventory |
| R9 | **Special-category data unguarded** (Art 9). | **M/H** | eve memory (guardrail lists secrets, not Art 9 data), module-voice (biometric-adjacent) | Extend guardrail to Art 9; explicit-consent path |
| R10 | **Memory/personalization not screened for manipulation** (AI Act Art 5). | **M** | eve-patterns §3 memory | Guardrail against behavior-scoring / manipulative personalization |

### Per-skill snapshot

| Skill | Top gaps | Notable strength |
|---|---|---|
| **eve-agent** (+refs) | R5, R1, R4, R3, R9, R10 | **Human oversight (approval/HITL)** + **audit log** + **Art 32** (fail-closed auth, tenant isolation, per-tenant encrypted secrets, sandbox) |
| **design-md-to-app** | R2, R1, R3, R7, R4 | Security headers (CSP/HSTS/…), `env.ts`, `error.tsx` no-leak, tenant-scoped server actions |
| **module-add auth** | R1, R2, R4 | Throw/return split; `getCurrentTenantId()`; secrets via placeholders |
| **module-add db** | R3, R4, R1 | Optional **Postgres RLS**; dev-vs-prod migration guard |
| **module-add email** | R8, R2 | `RESEND_DEV_TO` redirect; server-only key |
| **module-add voice** | R5, R3, R9, R2 | Gateway key never in browser (short-lived token); rate-limit note |
| **module-add storage/realtime** | R4, R1, R3, R7 | MIME server-validation; WS abuse-prevention |
| **forms** | R2, R7, R1 | Server-action re-validation; client-can't-import-service boundary |
| **data-fetching** | R7, R1 | `requireOrgPermission` single read chokepoint |
| **state-discipline** | — (clean) | Minimization by architecture (ephemeral only) |
| **prd-from-idea / prd-to-tasks** | R6, R2 | "Don't invent" TBD discipline; `*(addressed by …)*` tagging |
| **linear-scrum** | R8, R7 | Idempotency bounds data pushed; small blast radius |
| **coss-ui** | — | **Model pattern**: openly discloses the MIT/AGPLv3 license split — the disclosure discipline the GDPR/AI-Act gaps should copy |
| **rn-module-add / rn-backend** | R1, R3 | Secure-store tokens, sign-out clears all, bcrypt/Argon2id, enumeration-safe 401 |
| **rn-publishing-payments** | R1 (store deletion), R8 | **Privacy label must match reality**; real-screenshot rule; SDK-collection audit |
| **rn-push-notifications** | R2, R8, R4 | Permission-at-the-right-moment; token never in AsyncStorage; anti-`console.log(token)` |
| **rn-data-fetching** | R4 | Persistence opt-in, not default; cancel-on-unmount |
| **rn-fundamentals / rn-styling** | — (clean) | Narrow scope; `EXPO_PUBLIC_*` boundary |

### What already helps (credit)

- **Art 32 security** is the best-covered dimension repo-wide: fail-closed auth, tenant isolation, per-tenant encrypted secrets, RLS, secure-store, security headers, server-only keys, enumeration-safe auth.
- **Art 14 human oversight**: eve approval/HITL is a first-class, *required* mechanic (idempotency needs it too).
- **Art 12 traceability**: eve durable append-only event log + Vercel Agent Runs + eval reporters.
- **Disclosure discipline exists** — `coss-ui` (license split) and `rn-publishing-payments` (label-must-match-reality) prove the authors flag legal trade-offs when they choose to; the pattern just wasn't applied to privacy/AI-Act.

### Highest-leverage fixes (feed the remediation skill)

1. **R1 DSAR** — one `export`+`erase` pattern, wired in `module-add auth` (web) + `rn-module-add` (mobile) + eve memory + `rn-publishing-payments` checklist. *(Biggest single win — GDPR + store-rejection.)*
2. **R5 AI disclosure** — mandatory in eve `instructions.md` + chat/voice scaffolds.
3. **R2 consent** — `CookieConsentBanner` + consent-field pattern.
4. **R6 upstream capture** — high-risk + personal-data questions in `prd-from-idea`; compliance rung in `prd-to-tasks`.
5. **R3/R4** — EU-region option in the stack + a retention/scrubbing convention.
6. **R8** — auto-generate a sub-processor register from `meta.json#stack` (which already records providers).

**Not legal advice.** These are engineering gaps; a DPO/counsel confirms materiality and legal basis per deployment.

