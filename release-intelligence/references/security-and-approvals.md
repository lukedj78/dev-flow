# Security, authorization and approvals

## 🔴 A successful analysis is not an authorisation

The sentence this whole file exists to enforce. An agent that has classified a release, drawn up a
rollout plan and read a clean health report has produced **information**. None of it is permission to
change what strangers are served.

Mechanically, that means: every mutating operation passes through `policy.py`, whose verdict is one of
`auto`, `approval`, `recommend` or `never` — and the agent may not substitute its own judgement for
that verdict, in either direction.

## The table

`release.py <root> policy` prints it for the project. In `automated` mode:

| operation | low | medium | high | critical |
|---|---|---|---|---|
| `risk_assessment`, `release_planning`, `flag_proposal`, `health_check`, `verification` | auto | auto | auto | auto |
| `rollout_pause`, `rollout_abort` | **auto** | **auto** | **auto** | **auto** |
| `cleanup_pr` | auto | auto | auto | approval |
| `flag_create` | auto | approval | approval | approval |
| `rollout_advance` | auto | approval | approval | approval |
| `flag_rollback` | auto | auto | approval | approval |
| `deployment_rollback` | auto | approval | approval | approval |
| `destructive_db_migration`, `flag_delete`, `production_data_change` | **approval** | **approval** | **approval** | **approval** |

In `assisted` mode every row except the read-only and always-auto ones becomes `approval`. In
`advisory` mode they become `recommend` — described, not prepared. In `disabled`, `never`.

### The two rows no configuration can change

1. **`rollout_pause` and `rollout_abort` are always `auto`.** A safety control that waits for a human
   who is asleep is not a safety control. This is the asymmetry that makes progressive delivery worth
   having: advancing needs proof and often a person; retreating needs neither.
2. **`destructive_db_migration`, `flag_delete` and `production_data_change` are never `auto`.** Not
   "discouraged" — the code has them in `NEVER_AUTO`, and the best verdict they can reach is
   `approval`. They are not forbidden; they are **not the agent's to decide**.

### A config file is not an authorisation

`meta.json#release.required_approvals` lets a project **tighten** any row:

```json
"required_approvals": { "rollout_advance": "approval", "cleanup_pr": "approval" }
```

An entry that would **loosen** a row is ignored, and `policy.override_ignored()` says so out loud.
`{"destructive_db_migration": "auto"}` in `meta.json` does not make it auto — because a file in the
repository is not a person's decision, and anyone who can open a PR can edit that file.

## What an approval has to contain

Modelled on `founder-intelligence`, which already solved this for the Playbook:

```bash
python3 release-intelligence/scripts/release.py <root> approve REL-… --user-said "vai, ma fermati al 25%"
```

- **`--user-said` is required.** An approval with no quote is the agent approving its own release, and
  both `release.py approve` and `dev-flow/scripts/release_gate.py` refuse it.
- **The quote is the user's own words**, not a paraphrase and not a summary. It is what makes an
  approval re-readable six weeks later, and it is what distinguishes "they said yes to this" from
  "someone concluded they would have".
- **`granted_by_user` is checked with `is True`.** A hand-edited `"yes"` is not an approval.
- **An approval covers one release id.** It does not carry forward to the next one, and an older
  approved release does not cover a newer unapproved one — tested.

## Relation to dev-flow's intervention levels

dev-flow already has an autonomy model: **intervention levels 1–4**
(`dev-flow/references/contracts.md` §Intervention levels), derived from *who is able to check a
finding* — never from the agent's impression of the diff. This skill does **not** replace it and does
not introduce a second scale.

| | Intervention level | This skill's autonomy mode |
|---|---|---|
| Question | who presses **merge** on this diff | what the agent may do to **production** after the merge |
| Set by | `spec-review`, per piece of work | the user, once, per project |
| Recorded | `meta.json#spec_review.level` | `meta.json#release.autonomy` |

They meet in one place: `spec_review.level >= 3` is a **risk signal** in `risk.py` — a diff a person
had to settle is a release that carries a judgement, and that raises the floor. One vocabulary feeding
the other, rather than two competing ones.

## Tokens and credentials

| Credential | Where it lives | Never |
|---|---|---|
| Flag **SDK key** / client-side id | the app's env, wired by `module-add`; the client-side id may reach the browser by design | — |
| Flag **management token** (LaunchDarkly service token) | the user's own shell, or a CI secret | **never in the app's env, never in a bundle, never in chat, never in a file this skill writes** |
| Observability token | `module-add observability` wired the DSN; this skill reads numbers, not APIs | — |
| `CRON_SECRET`, webhook secrets | `module-add deploy` | — |

Three rules that follow:

- **This skill holds no credential and makes no provider call.** It produces the plan — which
  instruction, which environment, which weights — and the user or the project's own reviewed code
  runs it. That is why `references/provider-launchdarkly.md` is a transcription of verified endpoints
  rather than a client.
- **Health evidence is passed in, not fetched.** The decision stays auditable from `meta.json` alone,
  and no observability token is needed here.
- **A management token is scoped and short-lived** where the provider supports it. A token that can
  archive a flag in production should not be the token a preview deployment holds.

## Provider-side approvals, where they exist

If the team already uses LaunchDarkly's **approval requests**
(`POST …/approval-requests`, `…/{id}/reviews`, `…/{id}/apply` — verified in its OpenAPI), an
`approval` verdict should become a request **there**, not a message in chat. The audit trail then
lives where auditors look, and the provider enforces it rather than this skill trusting itself.

Record the request id on the release event. The user's quote still goes in the manifest: two records
of the same decision, in the two places people will look.

## Audit trail

Every operation lands on the release's `events` list with a timestamp — including the ones that were
**refused**. A refused stage keeps the evidence that failed it, which is how "why did this sit at 5%
for two days" has an answer later.

What makes it trustworthy rather than decorative:

- writes go through `meta_io`'s lock, so two writers cannot erase each other;
- `meta_digest` marks the file when it is edited outside the scripts, so a hand-edited manifest can
  be told from a recorded one;
- `release_gate.py` refuses a `release` block that is not an object, or a `releases` that is not a
  list, rather than ignoring it — an unreadable block must not become a bypass.

## What is deliberately not here

- **No incident register of its own.** A bug goes to `scrum` Triage with a severity; a scope question
  goes through `prd-from-idea/references/scope-check.md`. One register for work, and it is the tracker.
- **No per-release secret storage.** If a release needs a new secret, that is `project-infra-setup`,
  which confirms each outward step and never puts a secret through chat.
- **No DPIA or sub-processor reasoning.** Adding a flag provider adds a sub-processor; recording it is
  `compliance-audit`'s register and `dev-flow/references/eu-data-sovereignty.md`'s procedure. This
  skill only says *that it happened*.
