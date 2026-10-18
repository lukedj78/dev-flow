---
name: app-security
description: 'Check whether an app''s own code can be attacked before it ships — vulnerable dependencies, secrets in the code and in git history, Next.js authorization gaps (Server Actions and route handlers without a session check, queries by id with no owner filter — IDOR), data over-exposure, secrets in public env vars, raw SQL — then read the flagged code against an OWASP checklist, with an opt-in dynamic level (Strix) that proves exploits against the app running locally. The fifth pre-deploy gate, beside compliance-audit, vercel-doctor, shadscan and launch-audit; reports and routes, never blocks. Triggers: "security review", "è sicura l''app?", "controllo di sicurezza prima del deploy", "IDOR", "secrets in the repo", "pentest". Not for: GDPR and legal (compliance-audit), UI quality (shadscan), cost (vercel-doctor), launch readiness (launch-audit), a review of one branch diff (Claude Code''s /security-review), third-party registry code (registry-intake).'
---

# app-security — can this code be attacked?

The fifth pre-deploy gate. The other four ask different questions, and none of them asks this one:

| Gate | Question |
|---|---|
| `compliance-audit` | is it legal? |
| `vercel-doctor` | what will it cost? |
| `shadscan` | is the UI complete and accessible? |
| `launch-audit` | can a stranger find it, trust it and buy from it? |
| **`app-security`** | **can someone use it to read or change what is not theirs?** |

No gate replaces another. A product can pass all four others with every Server Action open to anyone who
sends a POST.

## Three levels

| Level | What | With what | When |
|---|---|---|---|
| **scan** | dependencies, secrets, static analysis, our own Next.js checks | `scripts/scan_security.py`, which calls OSV-Scanner (or `pnpm audit` / `npm audit`), gitleaks and Semgrep when they are installed | every run |
| **review** | object-level authorization, data over-exposure, input validation, auth configuration, headers | you, reading the code with `references/review.md` | every run: on every flagged file, and on **every** Server Action and mutating route, flagged or not |
| **dynamic** | real exploits against the running app | Strix, in Docker, against `next start` locally or a preview | **only when the user asks**: before a first public launch, with sensitive data or payments — `references/dynamic.md` |

## Run

1. **Scan.**

   ```bash
   python3 <skills>/app-security/scripts/scan_security.py <project-root>          # the report
   python3 <skills>/app-security/scripts/scan_security.py <project-root> --json   # for the agent
   ```

   It finds the app at the root and in `apps/*` and `packages/*` of a monorepo. Each check reports
   **found**, **ok**, **not checked**, or **not applicable** (the Next.js checks on an Expo app). A missing tool, no network, a timeout or output that does not
   parse is *not checked*, never ok, and the report never calls a project clean. A secret found in git
   history comes first: it must be **rotated**, because deleting the file leaves it in every clone.

2. **Missing tools: propose, ask, never install alone.** The report prints the command for each one
   (`brew install osv-scanner`, `brew install gitleaks`, `pipx install semgrep`). Ask the user once for
   all of them. Without them the scan still runs our own checks and the dependency fallback (`pnpm audit`
   / `npm audit`, which need the network), and says what it could not look at. Semgrep downloads its
   rules at run time: their licence forbids shipping them, so this skill never contains one.

3. **Review.** The Next.js checks are **heuristics, and say so**: a regex cannot follow a helper across
   files. Open every flagged file and read it with `references/review.md`. Then read every exported
   Server Action and every `POST`/`PUT`/`PATCH`/`DELETE` handler, flagged or not, because the dangerous
   case — a session check that does not check *ownership* — passes every check here. A finding goes in
   the report only after you have read the code that makes it real.

   On a large project, read in this order: actions and routes that write; queries by id; what reaches
   `"use client"` components; the rest.

4. **Dynamic, only on request.** Read `references/dynamic.md` before anything else. It starts with the
   authorization rule, which you state to the user before any run.

5. **Report, then route.** One list, most severe first: secrets in history, then proven exploits, then
   authorization, then the rest. Each finding names the file and line, why it is real (what you read),
   and who fixes it:

   | Finding | Routed to |
   |---|---|
   | an action or route with no session or ownership check | `module-add auth` for the helper; the code owner for the call |
   | a query by id with no owner filter, a raw row returned | the code owner, with the fix from `review.md` |
   | a secret in the code, in history or in a public variable | **the user**: rotate first, then move it to the environment |
   | no security headers or CSP | `vercel-deploy` (headers in `next.config.ts`) |
   | a vulnerable dependency | the user: upgrade, or record why not |
   | a third-party component | `registry-intake` |

   This skill proposes fixes and does not apply them silently. Apply one when the user says so, and
   re-run the scan afterwards.

6. **Record** the `security` block by editing `.workflow/meta.json` directly, as `launch-audit` does with its own
   block, then append the run with `dev-flow/scripts/update_meta.py <root> append-history --skill app-security`.
   **Never bump `phase`, never block the deploy.** A risk the user decides to keep goes in
   `findings.accepted` with **their** reason, so the next run does not raise it again as new:

   ```json
   "security": {
     "last_run_at": "<ISO-8601 UTC>",
     "tools": { "deps": "osv-scanner", "secrets": "not-run", "static": "not-run" },
     "findings": { "open": 3, "fixed": 5, "accepted": [{ "check": "public-env-secret", "reason": "…" }] },
     "dynamic": null
   }
   ```

## A project's own session helpers

The scan accepts a call to `getSession`, `getCurrentUserId`, `getCurrentTenantId`, `requireUser`,
`verifySession` or `auth(` inside the body as a session check. A project with its own helper declares it
once, and the scan reads it:

```json
"stack_config": { "security_session_calls": ["requireMember", "withOrg"] }
```

Only a **bare call** counts: a helper named in a comment does not, and neither does a method of the same name
(`db.update(` is not a helper called `update`). A function of the project that itself takes the session counts as
a session check too, but only in a file that **imports** it, or in the file that defines it; a local function
with the same name shadows it.

## Expo and eve

- **Expo.** The Next.js checks do not apply and are skipped (the scan detects Expo from `app.json`, `app.config.*`, or `expo` without `next` in `package.json`). The
  dependency and secret scans apply in full, and so does the mobile part of `review.md`: tokens in
  `expo-secure-store`, never in AsyncStorage, and nothing secret in `EXPO_PUBLIC_`, which ships in plain
  text inside the app bundle.
- **eve agents.** The agent's own defenses — identity taken from the channel, approvals on every side
  effect, guards — are `eve-agent`'s (`eve-agent/references/eve-patterns.md` §1–2). Here, check only that
  the tools an agent calls reach data through the same owner-scoped access layer as the app.

## Relationship to other skills

- **`vercel-deploy`** keeps the Next.js version floor against known CVEs: that is about the version, not
  the code, and this skill points to it rather than repeating it.
- **`module-add auth`** owns the session helpers (`lib/auth-server.ts`). This skill checks that they are
  called, and that ownership is checked as well.
- **`registry-intake`** owns third-party component code. A finding inside `vendor/registry/` goes there.
- **`compliance-audit`** owns the law. A leaked personal record is a security finding here and a possible
  breach notification there; say both.
- **Claude Code's `/security-review`** reviews only the current branch's diff, and needs an `origin`
  remote. It is a useful extra pass on a pull request, not a replacement for this gate, which reads the
  whole app.

## Definition of done

- The scan ran, and every check that could not run is reported as not checked, with the install command.
- Every flagged file, and every Server Action and mutating route, was read with `review.md`.
- Every finding in the report names what made it real; rejected flags are dropped, with no padding.
- `meta.json#security` written, with the user's reason on every accepted risk; `history` appended;
  `phase` unchanged.

## Reference files

- `references/review.md` — the checklist, ordered by OWASP Top 10:2025, with right and wrong examples.
- `references/dynamic.md` — the opt-in Strix level: authorization first, then how to run it.
- `references/contracts.md` — the `.workflow/` dev-flow contract (vendored).
