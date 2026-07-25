---
name: compliance-audit
description: 'Run a GDPR + EU AI Act compliance audit on an EXISTING dev-flow project (web / mobile / eve agent) and remediate the risks it finds. Two modes: Audit (scan the codebase + `meta.json#stack` against a 10-point risk register — DSAR export/erasure, consent/cookies, EU data residency & transfers, retention/TTL & PII-scrubbing, AI-transparency Art.50, high-risk Annex III classification, sub-processors, special-category data — and write `docs/compliance/audit-report.md` with severity + file:line evidence + article mapping) and Remediate (auto-apply the SAFE, mechanical mitigations — DSAR endpoints, cookie-consent banner + privacy page, AI-disclosure, retention config, PII-scrubbing, a sub-processor register generated from `meta.json#stack` — and FLAG the decision-requiring ones as TODOs, never deciding legal basis / region / high-risk for the user). Reuses module-add / forms / design-md-to-app where possible instead of reinventing. Horizontal capability: run it any time; dev-flow proposes it as a pre-deploy gate. Records a `compliance` block in meta.json; does NOT bump phase. Triggers: "audit GDPR", "compliance check", "AI Act", "siamo conformi?", "DSAR / cancellazione account / cookie consent / data residency", or dev-flow routing before feature_complete/deploy. Not for: legal advice or a DPIA sign-off (this produces engineering findings + a DPIA template, a DPO/lawyer confirms materiality), building features (use design-md-to-app / module-add / rn-*), or writing the PRD (prd-from-idea captures the high-risk question upstream).'
---

# compliance-audit — GDPR + EU AI Act audit & remediation for existing projects

Runs on a **project that already exists** (any dev-flow stack — Next.js web, Expo mobile, or an eve agent). It reads the codebase and `.workflow/meta.json#stack`, scores it against a fixed risk register, writes a report, and — on request — applies the safe mitigations while flagging the ones that need a human decision.

> **Not legal advice.** This produces *engineering* findings and remediations. A DPO / qualified counsel confirms materiality, legal basis, and high-risk classification per deployment. Every generated artifact carries that caveat.

## The 10-point risk register (canonical)

Full checklist + article mapping + remediation recipes in `references/gdpr-ai-act-checklist.md`. In short:

| ID | Risk | GDPR / AI Act |
|---|---|---|
| **R1** | No DSAR: data export / erasure (also Apple 5.1.1(v) + Play in-app account deletion) | Art. 15/17/20 |
| **R2** | No consent capture / cookie-consent banner | Art. 6/7, ePrivacy |
| **R3** | International transfer / EU data residency not addressed | Art. 44+ |
| **R4** | No retention/TTL + no PII-scrubbing (logs, event log, caches) | Art. 5(1)(e) |
| **R5** | No AI-transparency disclosure; synthetic voice unlabeled | AI Act Art. 50 |
| **R6** | High-risk use case never classified (DPIA) | AI Act Annex III; GDPR Art. 35 |
| **R7** | PII in server/app logs | Art. 32 |
| **R8** | Sub-processors not disclosed / no DPA register | Art. 28 |
| **R9** | Special-category data unguarded | Art. 9 |
| **R10** | Memory/personalization not screened for manipulation | AI Act Art. 5 |

## Read state, then pick a mode

1. Read `.workflow/meta.json` (`stack.framework`, `auth`, `db`, `agent`, `deploy`, …). If none, still run — infer the stack from the codebase and tell the user.
2. Run `python scripts/scan.py <project-root>` for a fast first-pass signal (grep-level markers per risk). **The scan is a signal, not a verdict** — verify every hit by reading the file before reporting it (avoid false positives).
3. Choose: **Audit** (report only) or **Remediate** (apply safe fixes + flag decisions). Both are idempotent — re-running detects existing remediations and skips.

## Audit mode

Goal: a truthful, actionable report — no changes to the app.

1. For each R#, gather evidence: scan hits **you verified** by reading the code, plus stack facts (e.g. `stack.db="neon-drizzle"` + no EU region marker → R3; `stack.agent="eve"` → check R5/R4/R9/R10 in the agent).
2. Write `<root>/docs/compliance/audit-report.md`: per finding → **ID · severity (H/M/L) · article · evidence (`file:line`) · what's missing · recommended fix (safe-fix or decision)**. Group by severity. Lead with a one-paragraph posture summary and the "not legal advice" caveat.
3. Update `meta.json#compliance` (see below) + append `history` (`{ "skill": "compliance-audit", "action": "audit" }`). **No phase bump.**

## Remediate mode

Goal: apply the **safe, mechanical** mitigations; **flag** the decisions. Reuse existing skills — don't reinvent.

**Auto-apply (safe / reversible):**
- **R1 DSAR** — scaffold an account **data-export** + **erasure** endpoint following the project's own server-action / auth pattern (web: `lib/server/account.actions.ts` + `/settings/privacy` route; mobile: a `deleteAccount()` in the auth lib; eve agent: `export_memories` + `erase_all_memories` tools per `references/gdpr-ai-act-checklist.md`). Wire the erasure cascade across the tenant's tables. Where `module-add auth` / `rn-module-add` / `forms` own the surface, invoke/extend them rather than hand-rolling.
- **R2 consent** — a `CookieConsentBanner` + `lib/consent.ts` gate (blocks non-essential cookies/scripts until consent) + a `/legal/privacy` + `/legal/cookies` page stub. Mobile: log the push/ATT consent decision.
- **R5 AI-disclosure** — a first-turn/persistent "you're interacting with an AI" disclosure (eve: into `agent/instructions.md` + the chat header; voice: a label on synthetic audio).
- **R4 retention/scrubbing** — a `lib/log.ts` redaction helper (replace raw `console.error(e)` with a scrubbed logger) + a documented retention policy + a TTL/cleanup job stub tied to erasure; purge persisted caches on sign-out.
- **R8 sub-processors** — generate `docs/compliance/subprocessors.md` **from `meta.json#stack`** (LLM provider, Vercel, Neon/Supabase/Firebase, Resend, Linear, RevenueCat, Expo push…), each with role + a DPA-link TODO.
- **R9/R10 guardrails** — extend the eve memory guardrail (special-category + anti-manipulation) where an agent exists.

**Flag only (needs a product/legal decision — never decide it):** as `TODO(compliance)` entries in the report + inline:
- **R3** which EU region (Neon/Vercel/Supabase) and whether SCCs/adequacy apply.
- **R6** whether the use case is Annex III high-risk → if suspected, drop a **DPIA template** at `docs/compliance/dpia-template.md`, don't fill it in.
- **R9** the Art. 9 legal basis / explicit-consent flow; **R2** the exact consent copy & lawful basis.

After remediating: rewrite `audit-report.md` with each finding marked `fixed` / `flagged`, list applied changes, update `meta.json#compliance`, append `history`. Every change is a reviewable diff.

## `meta.json#compliance` block

```jsonc
"compliance": {
  "last_audit_at": "<ISO>",
  "findings": { "high": 0, "medium": 0, "low": 0 },
  "remediated": ["R1","R2","R5","R7","R8"],
  "flagged": ["R3","R6"],
  "data_residency": "eu" | "us" | null,
  "high_risk": true | false | null
}
```

## dev-flow hook

Horizontal capability — invoke any time. dev-flow **proposes it as a pre-deploy gate** when a project reaches `feature_complete` (before shipping), and in the `deployed` maintenance loop (re-audit after changes). It records `meta.json#compliance` + `history` and **never bumps `phase`** (like the discipline skills and `linear-scrum`).

## Definition of Done

- **Audit**: `docs/compliance/audit-report.md` exists, every reported finding was verified in code (no raw scan noise), `meta.json#compliance` populated.
- **Remediate**: safe fixes applied as reviewable diffs and marked `fixed`; decisions marked `flagged` with a DPIA template when high-risk is suspected; a re-run is a no-op for already-fixed items.
- Script green: `cd compliance-audit/scripts && python3 -m unittest test_scan`.

## What this skill does NOT do

- **Not legal advice / not a DPIA sign-off** — it produces findings + a DPIA *template*; a DPO/lawyer confirms.
- **Doesn't decide** region, legal basis, or high-risk classification — it flags them.
- **Doesn't build product features** (use `design-md-to-app` / `module-add` / `rn-*`); it adds only the compliance controls.
- **Doesn't bump `phase`.**

## Reference files

- `references/gdpr-ai-act-checklist.md` — the R1–R10 checklist, article mapping, and per-risk remediation recipes (safe-fix vs flag).
- `references/contracts.md` — the `.workflow/` dev-flow contract (vendored).
