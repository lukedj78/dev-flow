# Incident recovery — three different rollbacks, and what each one leaves behind

Written to be read at 2am by someone who did not ship the release. Start at the top.

## 0. Pause first

```bash
python3 release-intelligence/scripts/release.py <root> pause REL-… --note "<what you saw>"
```

It needs no approval in any autonomy mode, it costs nothing, and it buys the time to answer the next
question properly. If a rolling release is mid-flight, **aborting it is faster than rolling back** —
`pnpm dlx vercel@latest rolling-release abort` stops the traffic shift instead of re-pointing domains
after the fact (`vercel-deploy/references/rollback-runbook.md`).

## 1. Is it even the release?

```bash
pnpm dlx vercel@latest logs --environment production --status-code 5xx --since 30m
```

**If the errors predate the deploy, rolling back costs you the fix and changes nothing.** This is the
first question in `vercel-deploy`'s runbook too, and it is first for a reason: the expensive mistake
in an incident is not acting slowly, it is acting on the wrong layer.

Check in this order — each is cheap and each rules out a whole class:

1. **Timing.** Did the error rate move at the deploy, at the stage advance, or neither?
2. **Cohort.** Are the errors only in the flagged cohort? If they are everywhere, the flag is not the
   cause and turning it off will not help.
3. **Dependency.** Is a provider down? A third party's incident looks exactly like your regression,
   and both the flag and the deployment are innocent.
4. **Load.** Did traffic change? A release that is fine at 5% and breaks at 50% is a capacity
   problem, not a correctness one, and rolling back hides it until the next peak.

## 2. Choose the layer — they undo different things

| Kind | Command | Undoes | Does **not** undo |
|---|---|---|---|
| **flag** | `release.py <root> rollback REL-… --kind flag` | which branch new evaluations choose | anything the new branch already did — emails, rows, charges. And nothing about the schema |
| **deployment** | `vercel rollback <url>` (runbook) | the code that is served | env vars, cron entries, config — the deployment returns as it was *built*. And nothing about the schema |
| **database** | **nothing here runs it** | — | — |

Decide by what is broken, not by what is fastest:

- **the new code path is wrong, the old one is fine** → flag. Seconds, no rebuild, reversible.
- **the deployment itself is wrong** (build, config, a dependency, something outside the feature) →
  deployment rollback.
- **the schema is wrong** → neither. A forward migration, by a person.

🔴 **Never reach for a flag rollback on a release whose manifest says
`reversible_by_deployment_rollback: false`.** It will look like it worked — the UI goes back — and
the schema change is still live underneath, now being read by code that does not expect it.

## 3. The deployment rollback, and its trap

Run it from the runbook, not from memory. The one thing to carry in your head:

> **After a rollback, Vercel turns off auto-assignment of production domains.** New pushes to the
> production branch build, go green, and **do not go live.**

Someone pushing a hotfix and watching it "deploy successfully" with no effect is in this state. The
undo is `vercel promote <url>`, which both ships the fix and restores normal behaviour. Say it in the
channel before anyone else discovers it.

Plan limits matter here: on **Hobby** you can roll back only to the immediately previous production
deployment. Know that before you need it.

## 4. The database — the one this skill refuses

`release.py rollback --kind database` **records the decision and prints the procedure. It executes
nothing, in any autonomy mode, at any risk level**, and no project configuration can change that
(`policy.py`'s `NEVER_AUTO`).

What to do instead, in order:

1. **Stop the writes** — flag off, or the deployment rolled back. Containment before repair.
2. **Establish the restore point.** What is the backup, how old is it, and what is lost between it
   and now? On Neon: the branch's point-in-time window. **Say the number out loud** before anyone
   proposes a plan.
3. **Decide repair vs restore.** A forward migration that fixes the shape is almost always right. A
   restore loses every write since the restore point, including everybody else's.
4. **Write the forward migration** as its own `critical` release, with its own manifest and its own
   approval, and rehearse it on a Neon branch with real volume first.
5. **Never `DELETE` or `TRUNCATE` to tidy up during an incident.** That is a second incident on top
   of the first one, and it is unrecoverable.

## 5. Record it while it is fresh

```bash
python3 release-intelligence/scripts/release.py <root> rollback REL-… --kind flag --note "5xx on /api/checkout, cohort only"
```

The event lands on the release with its timestamp, the kind, the note and — where an approval was
required — the user's words. That is the artefact the retro reads. The alternative, a decision taken
in a thread, is indistinguishable a month later from a decision nobody took.

Then, and only then, the loop back into the backlog: what the incident revealed goes through
`prd-from-idea/references/scope-check.md` if it is a change of scope, or `scrum` Triage with a
severity if it is a bug. **Not into a document only this skill reads** — dev-flow has one register
for work, and it is the tracker.

## What makes the next incident cheaper

Three things, each of which is cheap before and impossible during:

- **the release tag on every event** (`module-add observability`), or "did it start with the deploy"
  has no answer;
- **a proven verification manual for the feature** (`app-verification`), so the first question after
  a rollback — *is the old path actually working?* — is one command instead of a guess;
- **the manifest**, which says what shipped, at what risk, who agreed, and whether a migration is
  underneath. Written in five seconds at plan time; irreplaceable at 2am.
