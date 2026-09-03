/**
 * Bound what a model may write into durable memory.
 *
 * A memory capability gives you scope and a size cap. What a fact may *contain*
 * is still yours, and the failure mode is not a wrong answer: it is a secret that
 * outlives the session that leaked it. A token, a card number, an order id that
 * will be stale next week — none of them belong in something recalled for months.
 *
 * The default refusal is deliberately shape-based rather than a denylist of
 * providers. You cannot enumerate every credential format; you can notice that a
 * value looks like an identifier and nothing else.
 */

export interface FactInput {
  key: string;
  value: string;
  category?: string;
}

export interface FactPolicy {
  /** Max key length. Default 64. */
  maxKeyChars?: number;
  /** Max value length. Default 200. */
  maxValueChars?: number;
  /** The closed set of allowed categories. Omit to accept any non-empty string. */
  categories?: readonly string[];
  /**
   * Refuse values that look like an identifier rather than a preference.
   * Default true. Turn it off only when the slot exists to hold ids, and then
   * scope that slot narrowly.
   */
  refuseIdentifierShaped?: boolean;
  /** Extra patterns to refuse, checked against the value. */
  blockedPatterns?: readonly RegExp[];
}

export type FactVerdict =
  | { ok: true }
  | { ok: false; reason: string };

/** Long unbroken runs of base62/hex, key-like prefixes, and card-shaped digits. */
const IDENTIFIER_SHAPED: readonly RegExp[] = [
  /\b[A-Za-z0-9_-]{24,}\b/,
  /\b(?:sk|pk|rk|api|key|token|bearer|ghp|gho|xox[baprs])[-_][A-Za-z0-9_-]{8,}\b/i,
  /\b[0-9a-f]{32,}\b/i,
  /\b(?:\d[ -]?){13,19}\b/,
];

const DEFAULTS = {
  maxKeyChars: 64,
  maxValueChars: 200,
  refuseIdentifierShaped: true,
} as const;

/**
 * Check one fact before it is stored. Returns a verdict rather than throwing,
 * so the caller can put the reason in the tool result the model reads.
 *
 * ```ts
 * const verdict = validateFact({ key, value, category }, { categories: ["preference", "context", "constraint"] });
 * if (!verdict.ok) return blocked("memory-policy", verdict.reason);
 * ```
 */
export function validateFact(fact: FactInput, policy: FactPolicy = {}): FactVerdict {
  const maxKey = policy.maxKeyChars ?? DEFAULTS.maxKeyChars;
  const maxValue = policy.maxValueChars ?? DEFAULTS.maxValueChars;
  const refuseIds = policy.refuseIdentifierShaped ?? DEFAULTS.refuseIdentifierShaped;

  const key = (fact.key ?? "").trim();
  const value = (fact.value ?? "").trim();

  if (key.length === 0) return { ok: false, reason: "the key is empty" };
  if (key.length > maxKey) {
    return { ok: false, reason: "the key is longer than " + maxKey + " characters" };
  }
  if (value.length === 0) return { ok: false, reason: "the value is empty" };
  if (value.length > maxValue) {
    return { ok: false, reason: "the value is longer than " + maxValue + " characters" };
  }

  if (policy.categories) {
    if (!fact.category || !policy.categories.includes(fact.category)) {
      return {
        ok: false,
        reason:
          "category must be one of " + policy.categories.join(", ") +
          ", got " + JSON.stringify(fact.category ?? null),
      };
    }
  }

  if (refuseIds) {
    for (const pattern of IDENTIFIER_SHAPED) {
      if (pattern.test(value)) {
        return {
          ok: false,
          reason:
            "the value looks like an identifier or credential, which does not belong in durable memory",
        };
      }
    }
  }

  for (const pattern of policy.blockedPatterns ?? []) {
    if (pattern.test(value)) {
      return { ok: false, reason: "the value matches a blocked pattern for this slot" };
    }
  }

  return { ok: true };
}
