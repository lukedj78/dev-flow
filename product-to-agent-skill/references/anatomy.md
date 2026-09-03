# Anatomy of an agent-skill for a product

Section by section, with the rule each one encodes. Taken from
[`sleekdotdesign/agent-skills`](https://github.com/sleekdotdesign/agent-skills)
— MIT, 571★, one skill of 563 lines, read in full on 2026-09-03 — which is the
clearest published example of a service making itself drivable by a coding agent
without shipping an SDK for each one.

Read this before writing; it is the difference between a runbook and a docs dump.

---

## 1. Frontmatter — what it needs, before anyone installs it

```yaml
name: <product>-<verb>            # e.g. sleek-design-mobile-apps
description: Use when <the situations>, or when implementing <product> output in code.
compatibility: Requires <PRODUCT>_API_KEY. Network access limited to https://<host> only.
metadata:
  requires-env: <PRODUCT>_API_KEY
  allowed-hosts: https://<host>
```

The `compatibility` line and the `metadata` block are the part most people skip.
They let a reader — and a sandbox — know what the skill will reach for **before**
running it. Name the single host. If there are two, name two; if there are many,
the product probably needs a narrower key rather than a broader skill.

## 2. Overview — the four facts that unblock everything

Base URL, auth header, content type, and **where the machine-readable spec is**
(`/spec.json` and a browsable docs URL). That last one matters: it tells the agent
where to go for any contract detail the skill did not cover, instead of guessing.

Sleek adds one more line here that is pure field experience: *write the response
to a file and parse the file; don't pipe JSON through `echo`, because zsh expands
the escaped `\n` inside string values and breaks the body.*

## 3. Getting a credential — device flow before anything else

In order of preference:

1. **Device flow.** `POST /device/start` → the response carries a
   `verificationUrl`, a human-checkable `userCode`, a secret `deviceCode` and a
   poll `interval`. Show the user the URL and the code, tell them to confirm the
   code matches before approving, then poll `/device/poll` until it returns the
   key **once**. The agent never asks a human to paste a secret.
2. **A setup page** that does sign-in, plan and key creation in one place.
3. Bare "set the env var" — the fallback.

### Scopes

A table of scope → what it unlocks, and the instruction to create a key with
**only** the scopes the task needs. If the product has no scopes, that is a
finding to report to its owner, not a section to fake.

### Price

If the product charges, the price belongs here, in the same paragraph as the
first step that leads toward payment: the free tier and what it covers, then what
sustained use costs, monthly and yearly. The rule Sleek states and this file
adopts: **never let a payment step come as a surprise.**

## 4. Security & privacy — four lines, not a policy

Single host, HTTPS only, minimal scopes, and *what the product's servers fetch on
your behalf*. That last one is the one people forget: if the API takes image URLs
or webhook targets, its servers will fetch them, and the skill must say so.

## 5. The loop — the section that makes it a skill

Numbered steps, in the order an agent performs them, each carrying the rule that
stops it going wrong. Sleek's is three:

1. **Create the container** (a project) — and the note that variations mean
   separate containers, not one container with a confused history.
2. **Act, once, with the whole intent.** "Don't decompose the request; don't add
   details the user didn't ask for." An agent's instinct is to split work into
   small calls, and for a service that plans holistically that instinct produces
   worse output. If your product has that property, say it here in a sentence.
3. **Show the user the result.** Sleek's rule: the step is done only when the
   user has seen a screenshot of every screen the run created — *never complete a
   run silently.*

### Long operations

State the polling schedule (start 2s, back off to 5s, give up at 5 minutes), the
blocking alternative and its cap, and the exit conditions. Two rules worth
copying verbatim in shape:

- **An unreadable status is not "not done yet."** Stop and report, or the loop
  spins to its cap long after the run finished.
- **One run at a time**, if that is true of the product, with the conflict code
  the caller will get and how to clear it.

Then `idempotency-key` on re-sends, so a retry returns the existing run instead
of creating a second one.

## 6. Using the output in code

If the product returns something to be implemented, this section is what stops an
agent working from a picture:

- **The code is the implementation reference; the render is the visual target.**
  One tells you *how*, the other tells you *what it should look like*.
- **Which version.** If entities are versioned, say which one is current and how
  to pin — including the trap that `versions[i].version` is a number and
  `versions[i].id` is a string, and matching on the wrong one is silent.
- **The details that break fidelity**: the icon set and where to fetch it, the
  fonts and where they are declared, and the parts of the UI an agent forgets to
  carry over (Sleek names navigation explicitly: don't implement the screen and
  leave the default tab bar).
- **Don't route large payloads through your text output.** Pipe the response
  straight to a file with a shell command — it is faster and does not burn the
  context the agent needs to do the work.

## 7. Reference — endpoints, errors, pagination

A quick table of every endpoint, then one section each with real request and
response bodies. Then the **error shapes** (status → body → what to do) and
pagination. This is the part that reads like docs, and it comes *after* the loop
for a reason: an agent that reads top-down should learn the job before the
catalogue.

## 8. Common mistakes — the highest-value table in the file

Two columns: the mistake, and the fix. Every row is something that **actually
went wrong** while driving the product. Sleek's includes calling a screen
incomplete from a viewport screenshot when the content was below the fold, and
confusing two id fields that look alike.

This table cannot be written from imagination. It is the residue of having used
the thing, which is why the last step before shipping is to drive the product
through the file you just wrote.

---

## Two failure modes to check for before you ship

- **A skill that has never been executed.** Follow your own file literally,
  against the real product, and fix what it failed to say.
- **A skill that has drifted from its product.** Worse than no skill, because it
  fails with confidence. Note in the product's README that the file is part of
  the API's contract and changes with it.
