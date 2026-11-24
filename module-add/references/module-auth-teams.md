# Module: auth — Better Auth with organizations, teams as workspaces, and the three controls

For a product where **organization = the customer** and **workspace = a team inside it**, with our own
workspace roles, one `authorize()` every tool and service runs, and the bridge to an eve agent. Builds
on `module-auth.md` (sign-in, sessions, the base install); read that first.

Every block below type-checked and its tests ran on 2026-11-24 with better-auth 1.7.28, in a monorepo
whose `boundaries.json` lets `auth` depend on `db`, `contracts` and `config`.

## What Better Auth gives, and what it does not

- `organization` plugin with **`teams: { enabled: true }`**: organizations, members with an
  organization role, teams, team members, the active organization and **active team** on the session.
- **A team member has no role.** `teamMember` is `{ id, teamId, userId, createdAt }` (read in
  `dist/plugins/organization/schema.d.mts`). So the **workspace role is ours**: a table
  `workspace_member_roles (workspace_id = team id, user_id, role)` in `packages/db`, with the RLS block
  of `module-db-postgres.md` because it carries `workspace_id`.
- `createAccessControl` (`better-auth/plugins/access`) to declare the actions and the roles that may
  do them. Application code checks **actions**, never role names.
- Better Auth's own tables (user, session, organization, member, team…) are generated with its CLI.
  `[VERIFY]` the CLI that matches the installed version: on 2026-11-24 `@better-auth/cli` was at
  1.4.21 while `better-auth` was at 1.7.28. Those tables are keyed by organization, not workspace, so
  they are outside the workspace RLS by design; only our tables with `workspace_id` get it.

## Where it goes

Monorepo with `boundaries.json`: **`packages/auth`** (depends on `db`). Single app: `lib/auth/`.

```bash
pnpm --filter @<slug>/auth add --save-exact better-auth
```

## Files

```ts title="src/permissions.ts"
import { createAccessControl } from "better-auth/plugins/access";

/** What can be done inside a workspace. Extend this list; never check role names in application code. */
export const statements = {
  workspace: ["read", "manage"],
  project: ["read", "create", "update", "delete"],
  capability: ["use", "configure"],
  approval: ["decide"],
} as const;

export const ac = createAccessControl(statements);

export const roles = {
  owner: ac.newRole({
    workspace: ["read", "manage"],
    project: ["read", "create", "update", "delete"],
    capability: ["use", "configure"],
    approval: ["decide"],
  }),
  admin: ac.newRole({
    workspace: ["read", "manage"],
    project: ["read", "create", "update", "delete"],
    capability: ["use", "configure"],
    approval: ["decide"],
  }),
  member: ac.newRole({
    workspace: ["read"],
    project: ["read", "create", "update"],
    capability: ["use"],
    approval: ["decide"],
  }),
  viewer: ac.newRole({ workspace: ["read"], project: ["read"] }),
};

export type WorkspaceRole = keyof typeof roles;
export type Action = {
  [R in keyof typeof statements]: { resource: R; action: (typeof statements)[R][number] };
}[keyof typeof statements];
```

```ts title="src/auth.ts"
import type { Db } from "@<slug>/db";
import { betterAuth } from "better-auth";
import { drizzleAdapter } from "better-auth/adapters/drizzle";
import { organization } from "better-auth/plugins";
import { ac, roles } from "./permissions.ts";

// Organization = the customer; Team = the workspace. Teams carry no member role in Better Auth,
// so the workspace role lives in our table workspace_member_roles (packages/db).
export function createAuth(db: Db) {
  return betterAuth({
    database: drizzleAdapter(db, { provider: "pg" }),
    emailAndPassword: { enabled: true },
    plugins: [organization({ ac, roles, teams: { enabled: true } })],
  });
}
```

```ts title="src/authorize.ts"
import { type Action, roles, statements, type WorkspaceRole } from "./permissions.ts";

/**
 * The three controls (person, capability, workspace). Every tool and every service call runs this
 * at execution time: hiding a tool from the model is not authorizing it.
 */
export type AuthorizeInput = {
  /**
   * The person — or the workspace's service identity for schedules and other work with no person.
   * workspaceRole is read FRESH from workspace_member_roles on every call, never from the session:
   * a session keeps its active team after the person is removed from it.
   */
  person: { kind: "user" | "service"; id: string; workspaceRole: WorkspaceRole | null };
  /**
   * The capability doing the work: its capability.json permissions. Omit it ONLY for an action no
   * capability performs (a person in the UI). A tool that omits it skips the second control.
   */
  capability?: { id: string; allow: readonly string[]; deny: readonly string[] };
  /** Workspace-level rules: actions switched off for everyone in this workspace. */
  workspace: { id: string; disabledActions: readonly string[] };
};

export type Decision =
  | { allowed: true }
  | { allowed: false; deniedBy: "person" | "capability" | "workspace"; reason: string };

export type AuditSink = (entry: {
  workspaceId: string;
  actorId: string;
  action: string;
  decision: Decision;
}) => void | Promise<void>;

const key = (a: Action) => `${a.resource}:${a.action}`;

export async function authorize(input: AuthorizeInput, action: Action, audit: AuditSink): Promise<Decision> {
  const k = key(action);
  const decision = decide(input, action, k);
  if (!decision.allowed)
    await audit({ workspaceId: input.workspace.id, actorId: input.person.id, action: k, decision });
  return decision;
}

function decide(input: AuthorizeInput, action: Action, k: string): Decision {
  // Fail closed on anything the statements do not declare (a runtime string such as "__proto__").
  if (
    !Object.hasOwn(statements, action.resource) ||
    !(statements[action.resource] as readonly string[]).includes(action.action)
  )
    return { allowed: false, deniedBy: "person", reason: `unknown action ${k}` };
  const role = input.person.workspaceRole;
  let personOk = false;
  try {
    personOk =
      role !== null &&
      Object.hasOwn(roles, role) &&
      roles[role].authorize({ [action.resource]: [action.action] } as Parameters<
        (typeof roles)[WorkspaceRole]["authorize"]
      >[0]).success;
  } catch {
    personOk = false;
  }
  if (!personOk)
    return {
      allowed: false,
      deniedBy: "person",
      reason: role ? `role ${role} cannot ${k}` : "not a member of this workspace",
    };
  if (input.capability && (input.capability.deny.includes(k) || !input.capability.allow.includes(k)))
    return { allowed: false, deniedBy: "capability", reason: `capability ${input.capability.id} does not allow ${k}` };
  if (input.workspace.disabledActions.includes(k))
    return { allowed: false, deniedBy: "workspace", reason: `${k} is switched off in this workspace` };
  return { allowed: true };
}
```

- **Hiding is not authorizing.** An agent that cannot see a tool can still be steered into a code path
  that calls the service behind it; the service runs `authorize()` again.
- **Schedules and other work with no person** run as the workspace's **service identity**
  (`person.kind = "service"`), with a role chosen for that job — never as the last user who touched it.
- The `AuditSink` writes to the audit table (`packages/services` or `platform`). Every refusal is
  recorded; allowed actions are audited where the domain requires it, not here.

```ts title="src/eve.ts"
/**
 * The bridge from the app's session to eve's principal. The agent's AuthFn (agent/channels/eve.ts) calls
 * this with the Better Auth session it verified; tools read the result from ctx.session.auth.current.attributes.
 * Identity comes from the session, never from the model or from a header the client sets.
 */
export type AppSession = {
  user: { id: string };
  session: { activeOrganizationId?: string | null; activeTeamId?: string | null };
};

export type EvePrincipal = {
  authenticator: "app";
  principalId: string;
  principalType: "user";
  attributes: { userId: string; organizationId: string; workspaceId: string };
};

export function toEveAuth(s: AppSession | null): EvePrincipal | null {
  const organizationId = s?.session.activeOrganizationId;
  const workspaceId = s?.session.activeTeamId;
  if (!s || !organizationId || !workspaceId) return null; // no active workspace → not this channel's caller
  return {
    authenticator: "app",
    principalId: s.user.id,
    principalType: "user",
    attributes: { userId: s.user.id, organizationId, workspaceId },
  };
}
```

⚠️ **The active team is a session value, not a membership.** Better Auth checks membership when the
active team is **set**; removing the person from the team later does not clear it from an existing
session or its cookie cache. So the principal's `workspaceId` says which workspace the caller
*chose*, and `authorize()` decides whether they still *belong* to it: every tool reads the role fresh
from `workspace_member_roles` (no row → `workspaceRole: null` → refused). For a stricter AuthFn, check
the membership there too and return null when it is gone.

In the agent (`apps/web/agent/channels/eve.ts`), the `AuthFn` verifies the app session and returns
`toEveAuth(session)`; tools then read `ctx.session.auth.current.attributes.workspaceId`. Add session
ownership in the same file (`eve-agent/references/eve-patterns.md` §1bis).

## Tests

```ts title="test/authorize.test.ts"
import { describe, expect, it } from "vitest";
import { authorize } from "../src/authorize.ts";
import { toEveAuth } from "../src/eve.ts";

const audit: unknown[] = [];
const sink = (e: unknown) => void audit.push(e);
const ws = { id: "ws-a", disabledActions: [] as string[] };
const member = { kind: "user" as const, id: "u1", workspaceRole: "member" as const };
const cap = { id: "code-review", allow: ["project:read", "project:update"], deny: [] as string[] };

describe("three controls", () => {
  it("allows when person, capability and workspace all allow", async () => {
    expect(
      await authorize(
        { person: member, capability: cap, workspace: ws },
        { resource: "project", action: "update" },
        sink,
      ),
    ).toEqual({ allowed: true });
  });
  it("person denies: viewer cannot update", async () => {
    const d = await authorize(
      { person: { ...member, workspaceRole: "viewer" }, workspace: ws },
      { resource: "project", action: "update" },
      sink,
    );
    expect(d).toMatchObject({ allowed: false, deniedBy: "person" });
  });
  it("person denies: not a member of the workspace", async () => {
    const d = await authorize(
      { person: { ...member, workspaceRole: null }, workspace: ws },
      { resource: "project", action: "read" },
      sink,
    );
    expect(d).toMatchObject({ allowed: false, deniedBy: "person" });
  });
  it("capability denies what its contract does not allow", async () => {
    const d = await authorize(
      { person: member, capability: cap, workspace: ws },
      { resource: "project", action: "create" },
      sink,
    );
    expect(d).toMatchObject({ allowed: false, deniedBy: "capability" });
  });
  it("capability deny wins over allow", async () => {
    const d = await authorize(
      { person: member, capability: { ...cap, deny: ["project:update"] }, workspace: ws },
      { resource: "project", action: "update" },
      sink,
    );
    expect(d).toMatchObject({ allowed: false, deniedBy: "capability" });
  });
  it("workspace rule denies", async () => {
    const d = await authorize(
      { person: member, workspace: { ...ws, disabledActions: ["project:update"] } },
      { resource: "project", action: "update" },
      sink,
    );
    expect(d).toMatchObject({ allowed: false, deniedBy: "workspace" });
  });
  it("fails closed on an action the statements do not declare", async () => {
    const d = await authorize({ person: member, workspace: ws }, { resource: "__proto__", action: "x" } as never, sink);
    expect(d).toMatchObject({ allowed: false });
  });
  it("every refusal is audited, an allowed action is not", () => {
    expect(audit).toHaveLength(6);
  });
});

describe("toEveAuth", () => {
  it("builds the principal from the session's active organization and team", () => {
    expect(
      toEveAuth({ user: { id: "u1" }, session: { activeOrganizationId: "o1", activeTeamId: "ws-a" } })?.attributes,
    ).toEqual({ userId: "u1", organizationId: "o1", workspaceId: "ws-a" });
  });
  it("returns null with no active workspace", () => {
    expect(toEveAuth({ user: { id: "u1" }, session: { activeOrganizationId: "o1", activeTeamId: null } })).toBeNull();
  });
});
```

## Done when

- `pnpm --filter @<slug>/auth test` green: each of the three controls denies on its own, a capability's
  `deny` wins over its `allow`, every refusal is audited, `toEveAuth` refuses a session with no active
  workspace;
- `workspace_member_roles` has RLS (`module-add/scripts/check_rls.py` covers it like any table with
  `workspace_id`);
- `meta.json#stack.auth = "better-auth"`, history `{ "skill": "module-add", "action": "add-auth", "inputs": { "variant": "teams" } }`.
