> Sources: <https://modelcontextprotocol.io/> · `@modelcontextprotocol/sdk@1.30.0` (MIT) — the shipped
> `.d.ts`, not the docs site · `@better-auth/mcp@1.7.4` · and **a working implementation**:
> `~/projects/annotix` (`apps/web/app/mcp/route.ts`, `lib/mcp/server.ts`, 51 tools,
> `app/.well-known/`). Read **2026-09-13**. Everything here either ships in that repo or came out of
> making it work.

# module-add → `mcp` (publish the product as an MCP server)

`product-to-agent-skill` writes the runbook that lets a coding agent drive your HTTP API. This module
does the other thing: it makes the product **an MCP server**, so a client — Claude Code, Cursor,
Claude Desktop — discovers the tools itself, authenticates through your OAuth server, and calls them
without a human reading anything.

They are complementary, not alternatives. The runbook works for any API; MCP works for any client.
Most products want the runbook; a product whose users live inside a coding agent wants both.

## Decision first: your app, or the eve agent?

Two different things get called "an MCP server", and picking the wrong one costs a rewrite.

| | **`mcpChannel()`** (eve) | **`app/mcp/route.ts`** (this module) |
|---|---|---|
| What is published | the **agent** — one conversational surface | the **product** — your service functions, one tool each |
| Tools the client sees | `agent_start` / `agent_get` … | `list_datasets`, `start_extraction`, `get_credits` … |
| Where it lives | `eve/channels/mcp` — see `eve-agent/references/eve-capabilities.md` | a Next route handler in `apps/web` |
| Auth | the agent's channel auth | your OAuth server (`module-add auth` §MCP) |
| Reach for it when | the client should **talk to your agent** | the client should **use your product** |

This module is the second row. If what you want is "Claude Code can ask my agent things", stop here
and read the eve channel instead.

## Second decision: does this product need MCP at all?

Most do not, and the honest default is the cheaper artefact. **`product-to-agent-skill` §When to add
MCP carries the five signals** — users already in a terminal, an OAuth server you already have, more
than ~15–20 operations, something that can destroy data, a stable surface — with the rule that **two
are enough** and the destructive-operations one can justify it alone.

Read that before running this module. A product for consumers, or with five endpoints, or with only
API keys and no authorization server, should ship the runbook and stop.

## Prerequisites — auth is not optional and not last

`module-add auth` must have run **with the MCP section applied** (`@better-auth/mcp`, the resource
identifier, the scopes). An MCP endpoint without it is an unauthenticated API with tool descriptions
attached, and the tool descriptions make it *easier* to abuse, not harder.

Two things to fix in `lib/auth` before writing a route:

```ts
/** Scopes an MCP client can ask for. */
export const MCP_SCOPES = [
  "openid", "profile", "email", "offline_access",
  "data:read", "data:write",
] as const;
export const MCP_RESOURCE = `${appUrl}/mcp`;   // RFC 8707/9728 — tokens are audience-bound to it
```

```ts
plugins: [
  jwt(),                       // before mcp()
  mcp({
    loginPage: "/sign-in",
    consentPage: "/consent",
    resource: MCP_RESOURCE,
    scopes: [...MCP_SCOPES],
    accessTokenExpiresIn: 15 * 60,
    refreshTokenExpiresIn: 30 * 24 * 60 * 60,
    // CIMD (below) is the recommended path. Open registration is the fallback —
    // and today it is the one Claude Code expects.
    allowDynamicClientRegistration: process.env.AUTH_MCP_OPEN_REGISTRATION === "true",
    allowUnauthenticatedClientRegistration: process.env.AUTH_MCP_OPEN_REGISTRATION === "true",
  }),
  cimd({ fetchClientMetadataResource, metadataProfile: "mcp-2026-07-28" }),
  nextCookies(),               // must stay last: sets cookies from server actions
]
```

⚠️ **The registration decision is the security decision**, and it has a practical edge: CIMD verifies
client identity through domain ownership and is what MCP recommends, **but Claude Code currently
expects open RFC 7591 registration**. Putting it behind an env flag — off by default, on where the
client needs it — is how a real product resolves that without leaving `/oauth2/register` open
everywhere. Decide it out loud; do not drift into it.

## The `.well-known` trap, which costs an afternoon

Discovery documents must be served at the **site root**: `/.well-known/oauth-authorization-server`,
`/.well-known/openid-configuration`, `/.well-known/oauth-protected-resource` (and
`/.well-known/oauth-protected-resource/mcp`). better-auth serves them under its own base path
(`/api/auth/.well-known/…`), so root routes have to bridge — and **the two kinds bridge differently**:

```ts
// app/.well-known/_handler.ts
export function wellKnown(document: string) {
  return async function GET(request: Request) {
    if (document === "oauth-protected-resource") {
      // The MCP plugin matches this one on the RAW root path — forward unchanged.
      return getAuth().handler(new Request(request.url, { headers: request.headers }));
    }
    // The rest live under the auth base path — re-dispatch.
    const url = new URL(request.url);
    url.pathname = `/api/auth/.well-known/${document}`;
    return getAuth().handler(new Request(url, { headers: request.headers }));
  };
}
```

Get this wrong and the symptom is not an error: the client simply cannot discover the server, and
says something unhelpful about being unable to connect.

## The route handler

```ts
// app/mcp/route.ts
export const runtime = "nodejs";

const handler = requireMcpAuth(
  getAuth(),
  async (request, claims) => {
    const userId = typeof claims.sub === "string" ? claims.sub : null;
    if (!userId) return jsonRpcError(-32001, "token has no subject", 401);

    const org = await resolveOrganization(userId, request.headers.get("x-<slug>-org"));
    if (!org) return jsonRpcError(-32002, "the user belongs to no organization", 403);

    const scopes = typeof claims.scope === "string" ? claims.scope.split(" ") : [];

    const transport = new WebStandardStreamableHTTPServerTransport({
      sessionIdGenerator: undefined,   // stateless
      enableJsonResponse: true,
    });
    const server = create<Name>McpServer();
    await server.connect(transport);
    try {
      return await runWithApiContext(
        { organizationId: org.id, userId, actorType: "mcp_client", role: org.role,
          scopes: scopes.includes("data:write") ? ["data:read", "data:write"] : ["data:read"] },
        () => transport.handleRequest(request),
      );
    } finally {
      void transport.close().catch(() => undefined);
    }
  },
  { resource: MCP_RESOURCE, requiredScopes: ["data:read"] },
);

export const GET = handler;
export const POST = handler;
export const DELETE = handler;
```

Four decisions in there, each with a reason:

- **Stateless — a fresh server per request, no session ids.** A serverless function is not a place to
  keep a session, and MCP does not require one for a tool server.
- **`enableJsonResponse: true`, and this is the subtle one.** With JSON the whole response is produced
  *before* the `Response` is returned, so closing the transport in `finally` is safe. **With SSE the
  body streams after the return and that same `close()` cuts it mid-flight** — a bug that looks like
  a flaky client.
- **Identity comes from the token, tenancy from the token plus a header.** `claims.sub` is the user;
  the organization is their only one, or the one named by `X-<slug>-Org` when they belong to several.
  Never from a tool argument — that is the model choosing whose data to read.
- **Scopes narrow the capability, in the context.** A token without `data:write` produces a
  read-only context, so a write tool fails at the boundary rather than inside a query.

## The tool surface

One tool per service function, **named after the REST resources**, so a client that already read your
OpenAPI document recognises them. Annotix registers 51 this way.

```ts
const tool = (name, description, inputSchema, run) =>
  server.registerTool(name, {
    description,
    inputSchema,
    // Hosts use these to decide what needs confirmation (MCP tool annotations).
    annotations: {
      readOnlyHint:     /^(list|get|estimate|preview)_/.test(name),
      destructiveHint:  /^(delete|archive|cancel|revoke|unassign)_/.test(name),
      idempotentHint:   true,
    },
  }, run);
```

**Deriving the annotations from the verb prefix is the trick worth stealing.** They are what a host
uses to decide whether to ask the human before running a tool, and hand-setting them on 51 tools means
getting one wrong — the one that deletes something. Make the naming convention carry it, then the
convention is the safety property.

Results carry both shapes, because clients differ:

```ts
function ok(data: unknown): CallToolResult {
  return {
    content: [{ type: "text", text: JSON.stringify(data, null, 2) }],
    structuredContent: isPlainObject(data) ? data : { value: data },
  };
}
```

And a file is a **`resource_link`**, not a base64 blob in the transcript:

```ts
content: [{ type: "resource_link", uri: url, name, mimeType }]
```

## How you know it works

One integration test that lists the tools and runs a **read/write round trip inside the request
context** is worth more than unit tests per tool: it exercises auth, the context binding, the
transport and the schemas at once, and it is the only thing that catches a tool that works in
isolation and reads the wrong tenant in place.

Then the real client. Point Claude Code at the deployed URL and ask it to do something. The failure
you are looking for is not a stack trace — it is a tool nobody can call because its description does
not say what it needs.

## Common mistakes

| Mistake | What happens |
|---|---|
| SSE transport with `close()` in `finally` | the body is cut mid-stream; looks like a flaky client, not a bug in your code |
| Tenant id as a tool argument | the model picks whose data to read. Take it from the token |
| No `requireMcpAuth` | an unauthenticated API whose tool descriptions make it easier to abuse |
| Discovery documents only under `/api/auth/…` | the client cannot discover the server and says something unhelpful |
| Hand-set tool annotations | one of fifty is wrong, and it is the destructive one |
| Base64 files in tool results | the transcript fills with a PDF; use `resource_link` |
| Open registration by default | anyone can register a client on your authorization server |
| `nextCookies()` not last | server actions stop setting cookies, and sign-in breaks in a way unrelated to MCP |

## What this module does NOT do

- **Not the tools' business logic.** It wires the endpoint and the shape; the service functions
  already exist (that is the point of naming them after the REST resources).
- **Not `product-to-agent-skill`.** That writes the runbook for the HTTP API. Ship both when the
  product's users live inside a coding agent.
- **Not the eve channel.** See the decision table at the top.
