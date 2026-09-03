# Staged writes — an agent that changes someone's data never writes

The shape for any agent whose job includes *changing* something a business owns: a price, a listing,
a booking, a rota, a published page. Not "ask before writing". **The agent has no write.** It has a
proposal, and a person has an approval.

Adapted from Anthropic's [commerce-agents](https://github.com/anthropics/commerce-agents)
(Apache 2.0), whose merchant agent is this pattern end to end. The code below is eve; the reasoning
is theirs, and the reason to take it is that they built the whole thing and then wrote *"nothing
places an order, charges a card, or changes a live listing"* at the top of the README.

Related: `eve-patterns.md` §2 (approvals per tenant), §8 (what an unattended run may do), §11
(untrusted content). This file is the concrete artefact those three imply.

## One interface is the only door

A deployment implements **one abstract surface per role**, and nothing else in the agent reaches its
systems. Two halves, and the asymmetry is the point:

| Half | Shape | Count in their merchant agent |
|---|---|---|
| **Reads** | plain methods returning records | 8 — performance, catalog, inventory, order health, pricing |
| **The change lifecycle** | five `stage*`, then `pending`, `apply`, `discard` | 8 |

Five ways to *propose*, one way to *apply*, one way to *discard*, one way to *list what is pending*.
There is no `updateListing`. The agent could not write if it wanted to, because the verb does not
exist on the interface it is handed.

```ts title="agent/lib/backend.ts"
export interface CatalogBackend {
  // ── reads ────────────────────────────────────────────────────────────────
  searchListings(ctx: OperatorContext, query: string): Promise<Listing[]>;
  getListing(ctx: OperatorContext, id: string): Promise<Listing | null>;
  getInventoryAlerts(ctx: OperatorContext): Promise<InventoryAlert[]>;
  getPricingContext(ctx: OperatorContext, id: string): Promise<PricingContext>;

  // ── propose ──────────────────────────────────────────────────────────────
  stageListingUpdate(ctx: OperatorContext, draft: ListingDraft): Promise<StagedChange>;
  stagePriceUpdate(ctx: OperatorContext, draft: PriceDraft): Promise<StagedChange>;
  stageInventoryAction(ctx: OperatorContext, draft: InventoryDraft): Promise<StagedChange>;

  // ── the lifecycle ────────────────────────────────────────────────────────
  getPendingChanges(ctx: OperatorContext): Promise<StagedChange[]>;
  applyChange(ctx: OperatorContext, changeId: string): Promise<StagedChange>;
  discardChange(ctx: OperatorContext, changeId: string, reason?: string): Promise<StagedChange>;
}
```

**A system you have not wired yet is a method that fails**, with a specific error, while its tool
stays registered — so prompt bytes do not change and the model gets a result it can read rather than
a missing capability it cannot explain. **A system the business does not have at all is absent**: a
config switch that removes the tool, its prompt lines and its grounding rule together, so the three
never disagree.

## The change record

```ts title="agent/lib/types.ts"
export type ChangeStatus = "staged" | "applied" | "discarded";
export type ActorKind = "operator" | "assistant";

export interface StagedChange {
  changeId: string;
  kind: "listing" | "price" | "inventory" | "promotion" | "campaign";
  status: ChangeStatus;
  summary: string;                    // <= 200 chars: what a person reads before approving
  items: ChangeItem[];                // field-by-field before/after

  createdAt: string;
  createdBy: string;                  // ALWAYS the operator principal
  createdByKind: ActorKind;           // whether the assistant drove it on their behalf

  appliedAt?: string;
  appliedBy?: string;                 // no `appliedByKind` — see below

  discardedAt?: string;
  discardedBy?: string;
  discardedByKind?: ActorKind;

  guardrailNotes: string[];           // what the backend flagged but did not refuse
  currency?: string;                  // backend-computed. The model never does the arithmetic
  marginBeforePct?: number | null;    // null when the cost is unknown — never assumed
  marginAfterPct?: number | null;
}
```

⚠️ **`appliedBy` has no `appliedByKind`, and that asymmetry is the whole design.** A change can be
*created* by the assistant on the operator's behalf, and *discarded* by either. It can only be
**applied by the operator**. If your record can express "the assistant applied this", you have not
built staged writes — you have built a delay.

**A money figure is `null` when it cannot be computed, never estimated.** Their comment says it
plainly: a margin *"is never computed from an assumed cost"*. A margin the model inferred is worse
than no margin, because it is the number the human uses to decide.

## Guardrails run twice

The backend checks its rules when the change is **staged**, and again when it is **applied**, under
the configuration in force *at apply time*.

That second check is not belt-and-braces. **Time passed between the two.** The price floor may have
moved, the stock may be gone, the promotion may have ended, the operator's scope may have been
narrowed. A change approved against yesterday's rules is not approved against today's, and the only
moment that matters is the moment the write happens.

⚠️ **And re-running the rules is only half of it.** A change is staged against a *state*, and the
diff the operator approved was a diff from that state. If the value moved in between — someone else
edited the listing, another change touched the same variant — then applying it writes a diff nobody
approved, even though every rule still passes. So the second check has two halves:

```ts
for (const item of change.items) {
  const current = currentValue(item.targetId, item.field);
  if (current !== null && String(current) !== String(item.before)) {
    violations.push(`${item.field} is now ${current}, not ${item.before} as when this was staged`);
  }
}
// …then re-run the rules themselves.
```

This is optimistic concurrency, and it is the half that is easy to leave out because nothing fails
without it — the write simply lands on top of someone else's. It was missing from this file until a
reference implementation's own test asked for the scenario and the code let it through.

```ts title="agent/tools/apply_change.ts"
import { defineTool } from "eve/tools";
import { z } from "zod";
import { blocked } from "../lib/guards";
import { seenChanges } from "../lib/provenance";
import { backend } from "../lib/backend";

export default defineTool({
  description:
    "Apply a change the operator has approved. Only accepts a change_id this session surfaced.",
  inputSchema: z.object({ changeId: z.string() }),
  async execute({ changeId }, ctx) {
    if (!seenChanges.known(changeId)) {
      return blocked("provenance", "no tool in this session returned that change id");
    }
    try {
      return await backend.applyChange(operatorFrom(ctx), changeId);
    } catch (e) {
      if (e instanceof GuardrailViolation) {
        // Staged under one set of rules, applied under another. Say which.
        return blocked("guardrail", e.violations.join("; "), false);
      }
      throw e;
    }
  },
});
```

## Where eve's approval fits, and where it does not

eve's approval (`never()` / `once()` / `always()`) parks a **tool call** until a person answers. That
is the right mechanism for `apply`, and the wrong one for the whole pattern, for two reasons.

**An approval is per turn; a staged change outlives the session.** A person may approve tomorrow,
from the portal, without a conversation open. So the queue lives in your store, keyed by `changeId`,
and eve's approval is one *route* to answering it — not the record.

**And an approval prompt shows the model's words.** A staged change shows the **backend's** computed
before/after, its currency, its margin. That is what a person should read before saying yes: the
diff, not the sentence describing it.

So: `stage*` tools need no approval — they write nothing. `apply` carries `always()` when the channel
has a human on it, and in an unattended run it is **not offered at all** (§8b: an approval nobody can
answer must be denied, not parked).

## Provenance, and the distinction that is easy to miss

Staging accepts only ids this session's reads returned — `eve-patterns.md` §11b, `createProvenance`
in `guards.ts`. But their merchant agent keeps **two** maps, and the reason is worth copying:

- `seenListings` — ids that *any* read surfaced, including a search row.
- `readListings` — ids whose **full record** was fetched.

`stagePriceUpdate` needs the first. `stageListingUpdate` needs the second, **because a content edit is
staged against the full record and a search row carries only part of it** — so a change built from a
search row would quietly blank the fields the row never contained.

That is not a security rule, it is a correctness one, and it comes from the same map.

## The reads that must happen first

A question about performance answered from memory is a fabrication with a confident tone, and an
`apply` request with nothing staged is a request to apply something that does not exist. Both start
from the matching read.

eve has no `tool_choice` (§11c). The port is `defineDynamic` at `turn.started`: recognise the class
of request, then inject the instruction naming the required first read — or narrow the tool set so
that read is the only path. **Keep the recognising lexicon in config**, never in the prompt: adding a
synonym must not invalidate the cache.

## What this pattern buys, in one line each

- **The blast radius of a prompt injection is a proposal**, which a person reads before it is real.
- **The audit trail is the record**, not a log you hope someone reads: who proposed, who approved, when.
- **The demo is safe by construction** — theirs ships four verticals and still nothing writes.
- **The unattended case has an obvious answer**: stage, notify, stop.

## What it costs

Two writes where the business had one, a queue to store, and a surface where a person reads pending
changes. If the change is genuinely reversible and low-stakes — a draft, a note, a preference on the
caller's own record — this is ceremony. Reach for it when the write is **someone else's data, hard to
undo, or expensive to get wrong**, which in a multi-tenant SaaS is most of them.
