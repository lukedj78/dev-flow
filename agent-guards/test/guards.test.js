import test from "node:test";
import assert from "node:assert/strict";
import { createProvenance, validateFact, blocked, isBlocked } from "../dist/index.js";

// A plain object stands in for eve's defineState. That the store is injected is
// the point: the guard is testable without a runtime.
function memoryStore(initial = []) {
  let ids = [...initial];
  return { get: () => ids, set: (next) => { ids = next; } };
}

test("an id no read produced is unknown", () => {
  const seen = createProvenance({ store: memoryStore() });
  assert.equal(seen.known("A-4471"), false);
  seen.remember(["A-4471"]);
  assert.equal(seen.known("A-4471"), true);
});

test("unknown() names exactly the ids without provenance", () => {
  const seen = createProvenance({ store: memoryStore() });
  seen.remember(["a", "b"]);
  assert.deepEqual(seen.unknown(["a", "c", "b", "d"]), ["c", "d"]);
  assert.deepEqual(seen.unknown(["a", "b"]), [], "an all-known write must not be refused");
});

test("the newest ids win when the cap is reached", () => {
  const seen = createProvenance({ store: memoryStore(), cap: 3 });
  seen.remember(["a", "b", "c"]);
  seen.remember(["d"]);
  assert.deepEqual(seen.all(), ["d", "a", "b"]);
  assert.equal(seen.known("c"), false, "the oldest id should have been dropped");
});

test("remembering the same id twice does not consume two slots", () => {
  const seen = createProvenance({ store: memoryStore(), cap: 2 });
  seen.remember(["a"]);
  seen.remember(["a"]);
  seen.remember(["b"]);
  assert.deepEqual(seen.all(), ["b", "a"]);
});

test("empty and non-string ids are ignored rather than stored", () => {
  const seen = createProvenance({ store: memoryStore() });
  seen.remember(["", null, undefined, "ok"]);
  assert.deepEqual(seen.all(), ["ok"]);
});

test("a cap that is not a positive integer is refused at build time", () => {
  assert.throws(() => createProvenance({ store: memoryStore(), cap: 0 }));
  assert.throws(() => createProvenance({ store: memoryStore(), cap: 1.5 }));
});

test("a plain preference is accepted", () => {
  assert.deepEqual(validateFact({ key: "size", value: "usually a medium" }), { ok: true });
});

test("length limits are enforced on both key and value", () => {
  assert.equal(validateFact({ key: "k".repeat(65), value: "v" }).ok, false);
  assert.equal(validateFact({ key: "k", value: "v".repeat(201) }).ok, false);
  assert.equal(validateFact({ key: "", value: "v" }).ok, false);
  assert.equal(validateFact({ key: "k", value: "   " }).ok, false);
});

test("a closed category set is enforced only when given", () => {
  const cats = ["preference", "context"];
  assert.equal(validateFact({ key: "k", value: "v", category: "preference" }, { categories: cats }).ok, true);
  assert.equal(validateFact({ key: "k", value: "v", category: "secrets" }, { categories: cats }).ok, false);
  assert.equal(validateFact({ key: "k", value: "v" }, { categories: cats }).ok, false);
  assert.equal(validateFact({ key: "k", value: "v" }).ok, true, "no category set means any is fine");
});

test("identifier-shaped values are refused by default", () => {
  const cases = [
    "sk-live-9f2a4c8e1b7d0a35",
    "ghp_AbCdEfGhIjKlMnOpQrStUvWx",
    "d41d8cd98f00b204e9800998ecf8427e",
    "4111 1111 1111 1111",
    "aVeryLongOpaqueIdentifierWithNoSpaces123",
  ];
  for (const value of cases) {
    assert.equal(validateFact({ key: "k", value }).ok, false, "accepted: " + value);
  }
});

test("prose that merely contains a number is not identifier-shaped", () => {
  const fine = ["prefers window seats", "allergic to shellfish", "budget around 250 euros"];
  for (const value of fine) {
    assert.equal(validateFact({ key: "k", value }).ok, true, "refused: " + value);
  }
});

test("the identifier check can be turned off for a slot that exists to hold ids", () => {
  const value = "d41d8cd98f00b204e9800998ecf8427e";
  assert.equal(validateFact({ key: "k", value }, { refuseIdentifierShaped: false }).ok, true);
});

test("extra blocked patterns are checked", () => {
  const policy = { blockedPatterns: [/competitor/i] };
  assert.equal(validateFact({ key: "k", value: "likes Competitor Inc" }, policy).ok, false);
});

test("a refusal carries the gate that produced it and reads as a result", () => {
  const r = blocked("provenance", "no read in this session returned that id");
  assert.equal(r.blocked, "provenance");
  assert.equal(r.retryable, true);
  assert.ok(isBlocked(r));
  assert.equal(isBlocked({ ok: 1 }), false);
  assert.equal(blocked("cap", "at the limit", false).retryable, false);
});
