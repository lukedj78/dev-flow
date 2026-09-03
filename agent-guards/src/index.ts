/**
 * agent-guards — the five mechanical defences an agent needs when its tools
 * return text nobody at your company wrote.
 *
 * Zero runtime dependencies, framework-agnostic. The eve wiring is in
 * `eve-agent/references/eve-patterns.md` §11; nothing here imports eve.
 */
export { createFence, truncate } from "./fence.js";
export type { FenceOptions } from "./fence.js";

export { createProvenance } from "./provenance.js";
export type { Provenance, ProvenanceOptions, ProvenanceStore } from "./provenance.js";

export { validateFact } from "./memory.js";
export type { FactInput, FactPolicy, FactVerdict } from "./memory.js";

export { blocked, isBlocked } from "./result.js";
export type { BlockedResult } from "./result.js";
