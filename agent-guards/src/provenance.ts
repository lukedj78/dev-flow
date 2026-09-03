/**
 * A write accepts only ids a read actually produced.
 *
 * The model naming `A-4471` is not evidence that `A-4471` exists, or that this
 * caller may touch it. The id may be invented, or copied out of a poisoned tool
 * result. So: remember what the session's reads returned, and refuse the rest.
 *
 * This is a different defence from scoping arguments to `auth`. That one stops
 * the model choosing WHOSE record to touch. This one stops it touching a record
 * NO READ EVER SURFACED. You want both, and neither is authorization: whether
 * the caller owns the record stays a check against your own store.
 *
 * The store is injected rather than imported, so the same guard works over eve's
 * `defineState`, a Redis handle, or a plain object in a test:
 *
 * ```ts
 * import { defineState } from "eve/context";
 * const slot = defineState("shop.seen", () => ({ ids: [] as string[] }));
 * export const seen = createProvenance({
 *   get: () => slot.get().ids,
 *   set: (ids) => slot.update(() => ({ ids })),
 * });
 * ```
 */

export interface ProvenanceStore {
  get(): readonly string[];
  set(ids: string[]): void;
}

export interface ProvenanceOptions {
  store: ProvenanceStore;
  /**
   * How many ids to keep, newest first. Default 200.
   *
   * The cap is why this is safe to run for a long session, and also why a
   * dropped id needs a fresh read rather than failing mysteriously: say so in
   * the refusal.
   */
  cap?: number;
}

export interface Provenance {
  /** Record ids a read just returned. Newest first, de-duplicated, capped. */
  remember(ids: readonly string[]): void;
  /** Has a read in this session returned this id? */
  known(id: string): boolean;
  /** Every id currently remembered, newest first. */
  all(): readonly string[];
  /** Which of these ids have no provenance. Empty means the write may proceed. */
  unknown(ids: readonly string[]): string[];
}

const DEFAULT_CAP = 200;

export function createProvenance(options: ProvenanceOptions): Provenance {
  const { store } = options;
  const cap = options.cap ?? DEFAULT_CAP;
  if (!Number.isInteger(cap) || cap < 1) {
    throw new Error("createProvenance: cap must be a positive integer, got " + cap);
  }

  return {
    remember(ids) {
      const incoming = ids.filter((id) => typeof id === "string" && id.length > 0);
      if (incoming.length === 0) return;
      const merged = [...new Set([...incoming, ...store.get()])].slice(0, cap);
      store.set(merged);
    },
    known(id) {
      return store.get().includes(id);
    },
    all() {
      return store.get();
    },
    unknown(ids) {
      const seen = new Set(store.get());
      return ids.filter((id) => !seen.has(id));
    },
  };
}
