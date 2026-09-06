# `asc` — the App Store Connect CLI, and what an agent may do with it

Optional. Everything in `rn-eas-deploy` works without it. This file exists because two
steps of a release that this skill used to call *manual* are not manual any more, and
because the tool can do things an agent must **not** do unattended.

> ⚠️ `[VERIFY]` on every command below. They are transcribed from the project's README, not
> executed — running them needs an Apple Developer account and an App Store Connect API key,
> which this repo does not have. The first person to run one on a real app should correct
> this file from what actually happened.

## What it is

[`rorkai/App-Store-Connect-CLI`](https://github.com/rorkai/App-Store-Connect-CLI) — a CLI in
Go, MIT, over the App Store Connect API. Independent, not affiliated with Apple. The binary
is `asc`; install with Homebrew or the install script.

It ships **its own agent skills** ([rorkai/app-store-connect-cli-skills](https://github.com/rorkai/app-store-connect-cli-skills),
MIT), installed by `asc install-skills`, which checks out a pinned reviewed commit, verifies
every file, rolls back on failure, and needs only `git` (no Node, no npx, no repo scripts).
**Do not restate its command surface here.** Their skills teach the commands; this file owns
the part that is dev-flow's to decide.

`[VERIFY]` The CLI's README says 23 skills; `skills/` in that repo holds **25** directories
(read 2026-09-06). Not a problem — just do not quote a count.

Two of theirs are worth knowing before writing anything of our own, because they change what
is true here:

- **`asc-release-flow` already gates the dangerous step.** Its preconditions say: *"Require a
  dry run before a mutating high-level command, then require `--confirm` for submission."* So
  the pack is not reckless, and our table below is not a correction of it — it is the same
  instinct, stated as a rule about *who decides* rather than a flag.
- **`asc-revenuecat-catalog-sync`** overlaps `rn-publishing-payments`'s RevenueCat rule.
  Nobody has reconciled the two; if a project uses both, read that skill before assuming ours
  is the whole story.

## The boundary — what an agent may run

This is the reason this file exists. `asc` can submit an app to Apple review and rewrite a
live public listing. Gate on reversibility, exactly as `eve-patterns.md` §8f does:

| Command | Treatment | Why |
|---|---|---|
| `asc review status`, `asc review doctor`, `asc submit status`, `asc builds list`, `asc versions list`, `asc apps info` | **free** | reads. An agent should run these unprompted when a deploy is in flight |
| `asc testflight feedback`, `asc testflight crashes` | **free** | reads, and the most useful thing here — tester reports and crashes as text an agent can act on |
| `asc metadata apply`, `asc screenshots upload/apply`, `asc builds add-groups` | **ask first** | writes to a listing real people read, or to a tester group |
| `asc publish appstore`, `asc release stage`, `asc submit` | **never unattended** | submits to Apple review. Outward-facing, slow to undo, and a rejection is charged to the account's history |
| `asc signing sync` | **ask first** | touches certificates and profiles; a wrong sync breaks every build machine |

The rule behind the table: reads are free, writes to something the public sees stop for a
human, and *submitting to review is a human decision that an agent prepares but never
takes*. State it that way to the user rather than quoting the table.

## Where it changes this skill's workflow

**Step 8, "the user must release the build manually in the store dashboard".** That
sentence predates this tool. With `asc` the release is scriptable:

```bash
asc review doctor              # blockers BEFORE submitting — the step people skip
asc release stage              # preview the staging plan
asc publish appstore           # upload + attach + submit   ← human decision
asc submit status              # poll afterwards
asc review status              # blockers, if it comes back
```

Keep the manual path documented anyway: it is what someone without `asc` does, and it is
the fallback when the API is having a bad day (`asc auth doctor` exists for a reason).

**Step 8, first submission: there is still no API for creating the app record.** The command
surface has `asc apps info` and `asc apps list` and **no `asc apps create`**. Their own
`asc-app-create-ui` skill says it plainly — *"there is no public API for app creation"* — and
solves it by **driving the web form with browser automation** instead, which is a path we can
now take too (`agent-browser`, Playwright).

If you go that way, adopt their guardrails rather than inventing your own; they are the right
ones and they match this repo's rules on acting for a user:

- never export or store cookies;
- visible browser session only, never headless;
- **pause for a human confirmation before clicking "Create"**;
- never auto-retry a failed Create.

Preconditions they list: the bundle ID must already be registered in the Developer portal,
the user must be signed in (2FA included), and name (≤30 chars), SKU, platform, primary
language and access level must be known up front.

**Store metadata and screenshots.** `rn-publishing-payments` says *which* assets are needed
(6.9" or 6.5" iPhone, 13" iPad only if you ship iPad, real screenshots per guideline
2.3.10). It does not say how to get them up there, because until now the answer was "by
hand":

```bash
asc metadata init              # scaffold the metadata files
asc metadata apply             # push them
asc metadata keywords
asc screenshots plan           # what is missing
asc screenshots matrix         # required sizes per device
asc screenshots upload
```

## Credentials — treat the `.p8` as a production secret

`asc auth login` takes `--key-id`, `--issuer-id` and `--private-key /path/to/AuthKey.p8`.
An individual API key has no issuer ID: omit it and pass `--key-type individual`.

Two facts that matter for `compliance-audit`:

- By default the key goes into the **OS keychain**. Good.
- In CI, a headless shell, or anywhere without keychain access, `--bypass-keychain` puts it
  in a **config file on disk** instead. That is a stored credential with an audit trail
  obligation, and it must never be in the repo. Prefer a CI secret mounted at run time and
  deleted after.

`asc auth status --validate` and `asc auth doctor` verify the key without spending a
submission on finding out.

## Telemetry

On by default: pseudonymous command-level usage — CLI version, OS, command path, duration,
outcome class, HTTP status on failure, sometimes a sanitised flag *name*. The project states
it excludes raw arguments, flag values, error messages, response bodies, credentials, keys,
Apple account / team / issuer IDs, app and bundle IDs, usernames, hostnames, repo names and
file paths.

Disable with `asc telemetry disable`, or `ASC_TELEMETRY_DISABLED=1` / `DO_NOT_TRACK=1` —
they honour the standard variable. For a client project, turn it off and say you did.

## What this does not replace

EAS still builds and still submits. `asc` is not a second build system, and pointing both at
the same release is how you get two builds racing for the same version. The division that
holds: **EAS produces and uploads the artifact; `asc` reads and manages what App Store
Connect knows about it.**
