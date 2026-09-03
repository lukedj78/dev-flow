/**
 * A refusal is a result, not an exception.
 *
 * A thrown error is a dead end: the model gets a failure it cannot reason about,
 * and in eve a throw inside a hook cascades to `turn.failed`. A blocked call
 * should come back as a NORMAL result that names its gate, so the model reads it,
 * understands why, and takes another route.
 *
 * ```ts
 * if (!seen.known(id)) {
 *   return blocked("provenance", "no read in this session returned that id");
 * }
 * ```
 *
 * Reserve throwing for the genuinely unrecoverable.
 */

export interface BlockedResult {
  readonly blocked: string;
  readonly detail: string;
  readonly retryable: boolean;
}

/**
 * @param gate  which rule stopped the call — `"provenance"`, `"memory-policy"`,
 *              `"quantity-cap"`. Name the rule, not the symptom.
 * @param detail what the model would need to do differently, in one sentence.
 * @param retryable whether a different call could succeed. Default true; set
 *              false when nothing the model does will help, so it stops trying.
 */
export function blocked(gate: string, detail: string, retryable = true): BlockedResult {
  return { blocked: gate, detail, retryable };
}

/** Type guard, for a caller that hands results on to something else. */
export function isBlocked(value: unknown): value is BlockedResult {
  return (
    typeof value === "object" &&
    value !== null &&
    typeof (value as BlockedResult).blocked === "string" &&
    typeof (value as BlockedResult).detail === "string"
  );
}
