---
name: product-to-agent-skill
description: 'Write the agent-skill for the product you just built, so a coding agent can drive it. Reads the product''s own API surface — Next.js route handlers, an OpenAPI spec, or an eve agent''s tools — and produces a distributable `skills/<slug>/SKILL.md` in the product repo: auth (device flow before raw keys), the loop an agent should perform, the endpoint reference, error shapes, and a common-mistakes table grounded in what actually breaks. Plus the README row and the `npx skills add owner/repo` line for the product''s users. Use when the product exposes an API that is not only for its own frontend, when the user says "make my product usable from Claude Code / Cursor", "ship an agent skill for this", "how do agents use my API", or when dev-flow raises it near feature_complete. Refuses when the product has no callable surface. Not for: skills that operate ON this repo (those are dev-flow''s own), and not a docs generator — the output is a runbook, not a reference dump.'
---

# Product → agent-skill

Every product this repo builds may end up with an API. An API that only its own
frontend calls is an implementation detail. An API that **somebody else's coding
agent could drive** is a distribution channel, and it needs one artefact to be
usable: a skill file that tells that agent how the product works.

This skill writes that file, in the product's repo, for the product's users.

⚠️ **The output belongs to the product, never to dev-flow.** It lands in
`<product-repo>/skills/`, it ships and versions with that product, and its
audience is whoever installs the product's own repo. It is not added to this
repo's 45, not copied into `~/.claude/skills/`, and not listed in `install.sh`.
dev-flow builds it and then has nothing more to do with it — the same way it
builds an `app/` it does not own.

The reference implementation of the shape is
[`sleekdotdesign/agent-skills`](https://github.com/sleekdotdesign/agent-skills)
(MIT, read 2026-09-03): a design service published one 563-line SKILL.md and
became drivable from Claude Code, Cursor and Codex without shipping an SDK for
any of them. `references/anatomy.md` is what that file taught us, section by
section.

## When this skill applies

- The product has a **callable surface that is not only its own frontend**:
  route handlers under `app/api/`, an OpenAPI spec, a public eve agent, an MCP
  server.
- The user says "make my product usable from Claude Code", "ship an agent skill
  for this", "how would an agent use my API", "publish a skill for our API".
- `dev-flow` raises it at `feature_complete` → `deployed`, once there is a
  deployed origin to put in the file.

**Refuse** when the surface is internal-only — a route handler that exists to
serve one page is not a product an agent can drive, and a skill describing it
would be a lie with a nice table in it.

## The sibling: a runbook, or an MCP server?

This skill writes a **runbook** — a `SKILL.md` a user installs so their coding agent can drive your
HTTP API. `module-add mcp` does the other thing: it makes the product **an MCP server**, so a client
discovers the tools itself and never reads anything.

| | this skill | `module-add mcp` |
|---|---|---|
| The agent learns the API by | reading a file you wrote | asking the server |
| Works with | any agent, any client, today | MCP clients |
| Costs | one markdown file | an OAuth server, discovery documents, a tool surface |
| Reach for it | almost always — it is the cheap one | when your users live inside a coding agent |

They compose. Ship the runbook first; add MCP when the audience justifies the auth surface.

### When to add MCP — five signals

The default is not a preference, it is an asymmetry: a runbook is one file, written in an hour, that
works with every agent today. **MCP never replaces it.** It is added when specific things are true,
and **two of these five** are enough to pay for it.

**1. The users already live in a terminal.** Technical teams, data teams, DevOps. If your typical
user opens a coding agent every morning, that is where the product should be reachable. If they open
Chrome, it is not.

**2. You already have an OAuth server.** This is the biggest cost multiplier, and it is binary. With
`better-auth` plus users and organisations already standing, MCP is a plugin and a route. Without it
you are building an authorization server to expose three endpoints — and that is out of proportion to
what you get. **A product with only API keys should ship the runbook.**

**3. There are many operations.** Five endpoints fit in a markdown file an agent reads whole. Fifty
do not: the context window fills with documentation instead of work. MCP serves them on demand, one
schema at a time. The practical threshold is around **15–20 operations**.

**4. Something can destroy data.** If an agent can delete a dataset, revoke an access, cancel an
order, MCP's tool annotations (`destructiveHint`) make the **host** stop and ask — by protocol. A
runbook can only write the warning in a sentence and hope it was read as one. **This is the single
signal that can justify MCP on its own.**

**5. The surface is stable.** MCP is a contract you maintain: change a tool and clients feel it. A
runbook can say plainly *"this part moves, re-check it"*. If the API changes weekly, MCP is ballast.

### Three signals that say no, even when the others fire

- **The product is for consumers.** A shop, a booking app, an internal tool with a UI. Those users do
  not have a coding agent, and the tool surface would serve nobody.
- **The surface is five endpoints.** One file, half an hour, done.
- **You must reach clients that do not speak MCP.** The runbook works everywhere, today, including an
  agent somebody wrote in-house.

### And the "both" case, which is not a compromise

The mature configuration is both, because **the runbook is also the MCP server's documentation**. It
explains the domain — what a dataset is, why assets get assigned, which order of operations makes
sense — and MCP supplies the typed calls. Tools carry schemas; they do not carry why.

So when a product ends up with both, the runbook is not redundant: it stops being an endpoint
reference and becomes the part a schema cannot express.

## Contract

Follows the dev-flow contract — see `references/contracts.md`. Key facts:

- Reads `meta.json#stack` for the framework, the deployed origin, and whether
  `stack.agent = "eve"` (an eve agent's tools are a callable surface too).
- Writes **inside the product repo**, at `skills/<slug>/SKILL.md`, plus a README
  row and the install line. Never writes to `~/.claude/skills/` and never touches
  this repo's own skills.
- Records `meta.json#stack.agent_skill = "<slug>"` and appends `history`.
- Does **not** bump `phase`. Horizontal, on demand.

## What it produces

```
<product-repo>/
  skills/
    <slug>/
      SKILL.md          ← the runbook
  README.md             ← one row + the install line
```

And the install line the product's users will run:

```bash
npx skills add <owner>/<repo>
```

That is the [`skills`](https://www.npmjs.com/package/skills) CLI (verified at
`skills@1.5.23`); it writes to `.agents/skills/` in the caller's working
directory.

## Workflow

### 1. Find the real surface — don't ask the user to list it

Read it out of the product rather than interviewing:

| Source | Where | What you get |
|---|---|---|
| Next.js route handlers | `app/api/**/route.ts` | paths, methods, request/response shapes from the code |
| OpenAPI | `openapi.json`, `/api/*/spec.json` | the whole contract, typed |
| eve agent | `agent/tools/*.ts` | tool names, `inputSchema`, what each returns |
| MCP server | its manifest | tools and their schemas |

Then **cut it down**. A skill is a runbook, not a dump: the endpoints an agent
needs to do the job, in the order it needs them. An endpoint nobody would call
from an agent does not earn a section.

### Trace the identifier path before anything else

The question that decides whether the skill is writable: **starting from
nothing, how does a caller obtain the id it needs to act?** Search returns
prose; mutations need an id. If nothing carries one from the first call to the
second, the runbook has a hole in the middle and no amount of endpoint
documentation fills it.

Trace it end to end, for real, before writing. On the first product this skill
ran against, the assistant's reply named the item and its price and **no
identifier at all** — the ids were one event earlier in the stream, inside a
fenced tool result. The file had already claimed otherwise.

### Don't trust `meta.json` about the product

`stack` is what somebody recorded, not what is true. Check each claim you are
about to repeat: `stack.auth = "better-auth"` on that same product, with
better-auth absent from `package.json` and referenced nowhere in the code. A
skill that repeats a false security claim is worse than one that omits it.

### 2. Establish the auth story before anything else

In order of preference:

1. **Device flow**, if the product has one or can grow one: `POST /device/start`
   → show the user a URL and a code → poll → the key arrives once. The agent
   never sees a raw credential the user had to paste.
2. **A setup page** that handles sign-in, plan and key creation in one place, and
   the user pastes the key into their own environment.
3. Bare "set `<PRODUCT>_API_KEY`" — the fallback, not the design.

Declare it in the generated frontmatter, so a reader knows before installing:

```yaml
compatibility: Requires <PRODUCT>_API_KEY. Network access limited to https://<host> only.
metadata:
  requires-env: <PRODUCT>_API_KEY
  allowed-hosts: https://<host>
```

If the product charges, **the price goes in the skill**, next to the first step
that leads to a payment page. A payment step must never arrive as a surprise —
state the free tier, what it covers, and what sustained use costs.

### Attack the auth before you document it

Do not write the auth section from the code's intent. Test it:

- **Forge the credential.** Send the cookie, header or token a signed-in caller
  would send, made up. If it works, there is no authentication, and that is the
  first line of the file rather than a footnote.
- **Call the expensive endpoint with nothing.** An agent surface that answers
  without credentials is somebody's bill.

If either lands, the skill is a **draft** and its first section is the blocker
table. Publishing an agent-skill publishes the URL it drives — a file that
documents an open door is an invitation with instructions.

### 3. Write the loop, not the reference

The middle of the file is the sequence an agent performs to get a result: create
the thing, act on it, wait for it, **show the user what happened**. Sleek's
version is three steps and each one carries the rule that stops an agent getting
it wrong — send the whole intent as one message, poll with a give-up, and never
call the run done until the user has seen every screen it produced.

Long operations need: the polling schedule, the give-up, the "one at a time" rule
if the product has one, and an idempotency key for safe re-sends.

### 4. Then the reference, then the failure modes

Endpoints with real request/response bodies. Error shapes. Pagination. And a
**common-mistakes table** — the single highest-value section, and the one that
must be earned: every row is something that actually went wrong while driving
this product, not something you imagined might.

### 5. Prove it before shipping it

Drive the product **through the generated file**, following it literally, and fix
what the file failed to say. A skill nobody has executed is a guess — the first
run of this skill corrected its own output four times before it passed.

Three checks that each caught something real:

- **Run the cold-start path.** From nothing to a completed mutation, using only
  what the file tells you. This is where a missing identifier path surfaces.
- **Test optional fields across every *kind* of entity, not once.** A field can
  be absent, `null`, or a value, and the three mean different things: on that
  product a margin was absent on a stock change, `null` when the cost was not
  recorded, and a figure otherwise. The file described the middle case only,
  which would have had a caller announce "unknown margin" over a restock.
- **Verify how long-running things end.** A stream that never closes makes a
  plain `curl -N` exit non-zero, which looks like a failure and is not one. Say
  which event means stop, and say who closes the connection.

Then wire distribution: the README row, the install line, and a note that the
file must be updated when the API changes — an agent-skill that has drifted from
its product is worse than none, because it fails with confidence.

## What this skill does NOT do

- **Doesn't write docs.** A reference dump is not a skill; the runbook and the
  failure modes are the point.
- **Doesn't invent endpoints.** Everything in the output is read out of the
  product's code or spec. If a section needs an endpoint that does not exist,
  say so and stop — proposing one is the product owner's decision.
- **Doesn't publish.** It writes files and prints the install line; pushing and
  releasing stay the user's.
- **Doesn't touch this repo's skills.** Those are dev-flow's own and live
  elsewhere.

## Reference files

- `references/anatomy.md` — the section-by-section anatomy, taken from a
  published agent-skill that works, with the rules each section encodes.
- `references/contracts.md` — the `.workflow/` dev-flow contract (vendored).
