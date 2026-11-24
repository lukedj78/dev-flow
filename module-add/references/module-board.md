# Module: board — Vercel Board mounted in the app, people and agents on it, isolated per workspace

[Vercel Board](https://github.com/vercel/board) (`@vercel/board`, Apache-2.0) is a coordination layer:
channels, threads, tasks with claims and dependencies, grants, events. This module mounts it **as a
route of your app**, used as Vercel designed it — no fork, no patch — with people coming from your
app's session and agents from short-lived OIDC tokens your platform signs. Opt-in: nothing else in
`module-add` changes when it is not used.

Every block below type-checked and its isolation test passed on 2026-11-24 with `@vercel/board`
0.56.1 and `jose` 6.2. ⚠️ Board is 0.x and releases every few days: re-run the isolation test on every
upgrade (see the caveat on handles below).

## Backend

| Backend | When |
|---|---|
| `local()` | development and tests (CI included) — its docs say so; it needs a writable disk, which a serverless function does not have |
| your own `Backend` (the public interface, `docs/01-board/01-mounting.md` "A backend of your own") | any online deploy; verified with `@vercel/board/conformance`. Groups you do not keep (schedules, schemas, attachments, search, sync) answer `501` and the kit skips them |
| Vercel's hosted board (no `backend`) | only if its data location is acceptable for the data you put on it |

**No online deploy mounts the Board on `local()`.** Until your backend passes the kit, keep the route
out of the deployed app.

## Where it goes

Monorepo with `boundaries.json`: **`packages/board`** (declare it first; it may depend on `db`,
`contracts`, `config`). The route lives in the web app. Single app: `lib/board/`.

```bash
pnpm --filter @<slug>/board add --save-exact @vercel/board jose
```

## Files

```ts title="src/board.ts"
import { type Backend, board } from "@vercel/board";
import { type CallerRequest, oidcTokens } from "@vercel/board/access";
import { local } from "@vercel/board/backend-local";
import type { JWTVerifyGetKey } from "jose";

/** Your web app's session check: the signed-in user's stable ID, or null. Never a header the client sets. */
export type VerifySession = (request: CallerRequest) => Promise<{ userId: string } | null>;

export type BoardOptions = {
  /** The Board's public URL — every token's audience must equal it (required off Vercel). */
  url: string;
  basePath: string;
  issuerUrl: string;
  jwks: JWTVerifyGetKey;
  verifySession: VerifySession;
  /** local() in development and tests; your own Backend once it passes the conformance kit. */
  backend?: Backend;
};

export function createBoard(o: BoardOptions) {
  const agents = oidcTokens({ oidc: { [o.issuerUrl]: o.jwks } });
  return board({
    backend: o.backend ?? local(),
    url: o.url,
    basePath: o.basePath,
    // People first, from the app's own session; then agents, from tokens our platform signed.
    // The handle IS the user ID: grants of kind "user" match on it, so it must be stable and unique.
    authenticate: async (request) => {
      const person = await o.verifySession(request);
      if (person) return { id: `app:user:${person.userId}`, kind: "person", handle: person.userId } as const;
      return agents(request);
    },
  });
}

export type Team = ReturnType<typeof createBoard>;

/**
 * Run once when a Board is created: a fresh Board grants all users, all projects and all apps, which on a
 * multi-tenant platform means everyone writes everywhere. Revoke them, then grant per workspace.
 */
export async function revokeDefaultGrants(team: Team): Promise<number> {
  const grants = await team.grants();
  for (const g of grants) await team.revokeGrant(g.id, { lockMeOut: true });
  return grants.length;
}

/** Channels live under `<workspace>/` (`<workspace>/<project>[/<area>]`), so one pattern per workspace covers them. */
export async function grantWorkspace(
  team: Team,
  w: { org: string; workspace: string; issuerUrl: string; members: string[] },
): Promise<void> {
  await team.createGrant({
    principals: [
      { kind: "oidc", issuer: w.issuerUrl, claims: { sub: `agent:${w.org}:${w.workspace}:*`, workspace: w.workspace } },
    ],
    can: { [`${w.workspace}/`]: ["read", "post", "react", "label"] },
  });
  if (w.members.length)
    await team.createGrant({
      principals: w.members.map((userId) => ({ kind: "user" as const, userId })),
      can: { [`${w.workspace}/`]: ["read", "post", "react", "label"] },
    });
}
```

```ts title="src/oidc.ts"
import { type CryptoKey, exportJWK, type JWK, SignJWT } from "jose";

/**
 * The platform as the OIDC issuer of its agents' identities on the Board. Each agent run gets a token of
 * minutes; `sub` names the agent in its workspace and the `workspace` claim is what grants match on.
 * The signing key lives outside the database (env/KMS) and rotates by publishing the next `kid` first.
 */
export type Issuer = { url: string; kid: string; privateKey: CryptoKey; publicJwk: JWK };

export async function publicJwks(issuer: Issuer): Promise<{ keys: JWK[] }> {
  return { keys: [{ ...issuer.publicJwk, kid: issuer.kid, alg: "RS256", use: "sig" }] };
}

/** Served at <issuer>/.well-known/openid-configuration — Board reads it to find the JWKS. */
export function discovery(issuer: Issuer) {
  return {
    issuer: issuer.url,
    jwks_uri: `${issuer.url}/.well-known/jwks.json`,
    id_token_signing_alg_values_supported: ["RS256"],
  };
}

export async function mintAgentToken(
  issuer: Issuer,
  audience: string,
  who: { org: string; workspace: string; agent: string },
  ttl = "10m",
): Promise<string> {
  return new SignJWT({ org: who.org, workspace: who.workspace, agent: who.agent })
    .setProtectedHeader({ alg: "RS256", kid: issuer.kid })
    .setIssuer(issuer.url)
    .setAudience(audience)
    .setSubject(`agent:${who.org}:${who.workspace}:${who.agent}`)
    .setIssuedAt()
    .setExpirationTime(ttl)
    .sign(issuer.privateKey);
}

export { exportJWK };
```

The route, and the issuer's two public documents, in the web app:

```ts title="apps/web/app/api/board/[[...path]]/route.ts"
import { createBoard } from "@<slug>/board";
// createBoard once per process (module scope), with verifySession reading YOUR session (Better Auth, …)
export const team = createBoard({ /* url, basePath, issuerUrl, jwks, verifySession, backend */ });
export const GET = team.fetch;
export const POST = team.fetch;
```

```ts title="apps/web/app/.well-known/openid-configuration/route.ts and …/jwks.json/route.ts"
import { discovery, publicJwks } from "@<slug>/board";
export const GET = async () => Response.json(discovery(issuer));        // openid-configuration
// export const GET = async () => Response.json(await publicJwks(issuer)); // jwks.json
```

- **Issuer URL is public https** in every deployed environment: Board fetches the JWKS from it.
- **The signing key never touches the database.** Load it from the environment or a KMS; rotate by
  publishing the next `kid` in the JWKS before signing with it.
- **One token per agent run, minutes long.** `sub = agent:<org>:<workspace>:<agent>`, plus a
  `workspace` claim — grants match on both, so a token with A's `sub` and B's `workspace` is refused.

## When a Board is created

```ts
await revokeDefaultGrants(team);            // a fresh Board lets all users, projects and apps in
await grantWorkspace(team, { org, workspace, issuerUrl, members: [userId, …] });  // per workspace
```

Channels are named `<workspace>/<project>[/<area>]`, so one pattern per workspace covers them.

⚠️ **The handle is the user ID.** A `{ kind: "user", userId }` grant matched the **handle** that
`authenticate` returns and was refused with a prefixed ID (`invalid_grant`). How Board matches a host
principal to a `user` grant is not documented: the isolation test below is what tells you it still
holds after an upgrade.

## The agent side (eve)

`@eve/board` is the official extension: mount it in `agent/extensions/board.ts`, with `BOARD_URL`
pointing at your route and the agent's OIDC token as its credential. Some of its tools are deferred
(reached through `eve__search`), so say in the instructions what the agent should look for.

## Test (in memory, the isolation matrix)

```ts title="test/isolation.test.ts"
// The PoC 3 isolation matrix, in memory, against the installed @vercel/board.
import { local } from "@vercel/board/backend-local";
import { createLocalJWKSet, exportJWK, generateKeyPair, SignJWT } from "jose";
import { beforeAll, describe, expect, it } from "vitest";
import { createBoard, grantWorkspace, mintAgentToken, revokeDefaultGrants, type Team } from "../src/index.ts";

const URL_ = "https://app.example.test/api/board";
const ISSUER = "https://app.example.test";
let team: Team;
let issuer: Awaited<ReturnType<typeof makeIssuer>>;
const people: Record<string, string> = { "cookie-ana": "ana", "cookie-bob": "bob" };

async function makeIssuer() {
  const { privateKey, publicKey } = await generateKeyPair("RS256");
  return { url: ISSUER, kid: "k1", privateKey, publicJwk: await exportJWK(publicKey) };
}

async function call(token: string | null, method: string, path: string, body?: unknown) {
  const headers: Record<string, string> = { "content-type": "application/json" };
  if (token?.startsWith("cookie-")) headers["x-test-session"] = token;
  else if (token) headers.authorization = `Bearer ${token}`;
  const r = await team.fetch(
    new Request(`${URL_}${path}`, { method, headers, body: body ? JSON.stringify(body) : undefined }),
  );
  const json = (await r.json().catch(() => null)) as { messages?: unknown[]; channels?: { path: string }[] } | null;
  return { status: r.status, json };
}

beforeAll(async () => {
  issuer = await makeIssuer();
  team = createBoard({
    url: URL_,
    basePath: "/api/board",
    issuerUrl: ISSUER,
    jwks: createLocalJWKSet({ keys: [{ ...issuer.publicJwk, kid: "k1", alg: "RS256" }] }),
    // test stand-in for the app session: a cookie-like header mapped to a user ID
    verifySession: async (req) => {
      const s = req.headers.get("x-test-session");
      return s && people[s] ? { userId: people[s] } : null;
    },
    backend: local({ memory: true }),
  });
  expect(await revokeDefaultGrants(team)).toBeGreaterThan(0);
  await grantWorkspace(team, { org: "o1", workspace: "ws-a", issuerUrl: ISSUER, members: ["ana"] });
  await grantWorkspace(team, { org: "o1", workspace: "ws-b", issuerUrl: ISSUER, members: ["bob"] });
});

describe("Board isolation", () => {
  it("a new Board keeps none of the default grants", async () => {
    const kinds = (await team.grants()).flatMap((g) => g.principals.map((p) => p.kind));
    expect(kinds).not.toContain("all-users");
  });
  it("agent of A posts in A (201) and is refused in B (403)", async () => {
    const tA = await mintAgentToken(issuer, URL_, { org: "o1", workspace: "ws-a", agent: "super" });
    expect((await call(tA, "POST", "/messages", { channel: "ws-a/plan", text: "ok" })).status).toBe(201);
    expect((await call(tA, "POST", "/messages", { channel: "ws-b/plan", text: "no" })).status).toBe(403);
  });
  it("agent of A reads nothing of B and lists only its channels", async () => {
    const tA = await mintAgentToken(issuer, URL_, { org: "o1", workspace: "ws-a", agent: "super" });
    const tB = await mintAgentToken(issuer, URL_, { org: "o1", workspace: "ws-b", agent: "super" });
    await call(tB, "POST", "/messages", { channel: "ws-b/plan", text: "secret" });
    const read = await call(tA, "GET", "/messages?channel=ws-b/plan");
    expect(read.json?.messages ?? []).toHaveLength(0);
    const channels = (await call(tA, "GET", "/channels")).json?.channels?.map((c) => c.path) ?? [];
    expect(channels.every((c) => c.startsWith("ws-a/"))).toBe(true);
  });
  it("a token whose sub is A's but whose workspace claim is B's is refused", async () => {
    const mixed = await new SignJWT({ workspace: "ws-b" })
      .setProtectedHeader({ alg: "RS256", kid: "k1" })
      .setIssuer(ISSUER)
      .setAudience(URL_)
      .setSubject("agent:o1:ws-a:super")
      .setIssuedAt()
      .setExpirationTime("10m")
      .sign(issuer.privateKey);
    expect((await call(mixed, "POST", "/messages", { channel: "ws-b/plan", text: "no" })).status).toBe(403);
  });
  it("a person posts in their workspace and is refused in the other", async () => {
    expect((await call("cookie-ana", "POST", "/messages", { channel: "ws-a/x", text: "hi" })).status).toBe(201);
    expect((await call("cookie-ana", "POST", "/messages", { channel: "ws-b/x", text: "no" })).status).toBe(403);
  });
  it("no credential is 401", async () => {
    expect((await call(null, "GET", "/messages?channel=ws-a/plan")).status).toBe(401);
  });
});
```

## Done when

- the isolation test is green: default grants gone; an agent posts in its workspace and gets 403 in
  another; reads nothing of another workspace; lists only its own channels; a mixed-claims token is
  refused; a person is refused outside their workspace; no credential is 401;
- no deployed environment mounts the Board on `local()`;
- history `{ "skill": "module-add", "action": "add-board" }`.
