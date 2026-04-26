"use server";

import { z } from "zod";
import { revalidatePath } from "next/cache";
import { and, eq, isNull } from "drizzle-orm";
import { db } from "@/lib/db";
import { practices, auditLog } from "@/lib/db/schema";

// ────────────────────────────────────────────────────────────────────────────
// Server actions for the "pratica" domain.
//
// Convention (per design-md-to-app §Server actions):
//   • All actions live under `lib/server/<domain>.ts` with `"use server"` at top.
//   • Each action is named for the verb it performs (createX / updateX / archiveX).
//   • Inputs are validated with Zod before doing anything.
//   • Return shape is always `ActionResult<T>` — `{ ok: true, data }` on success,
//     `{ ok: false, error }` on failure. No throws across the server boundary.
//   • After successful mutations, call `revalidatePath` for any route that
//     reads the affected data.
//   • Authorization (tenant scoping, RBAC) goes BEFORE the try/catch — it's
//     not a recoverable error, it's a 500. The user/tenant id MUST be
//     resolved before we attempt the DB call, AND it MUST be in every
//     WHERE clause to prevent cross-tenant data access.
//   • Every mutation writes to `auditLog` in the same transaction.
//   • The catch block logs the full error (server-side only) and returns a
//     scrubbed message to the client. Do not return raw `e.message` — it can
//     leak internals (driver names, query fragments, secrets).
// ────────────────────────────────────────────────────────────────────────────

export type ActionResult<T> =
  | { ok: true; data: T }
  | { ok: false; error: string; fieldErrors?: Record<string, string[]> };

// ─── Schemas ────────────────────────────────────────────────────────────────

const CreatePracticeSchema = z.object({
  title: z.string().min(3, "Il titolo deve avere almeno 3 caratteri").max(200),
  type: z.enum(["compravendita", "mutuo", "societa", "successione", "altro"]),
  plannedDate: z.coerce.date().optional(),
});

const UpdatePracticeSchema = z.object({
  id: z.coerce.number().int().positive(),
  title: z.string().min(3).max(200).optional(),
  status: z
    .enum(["open", "in_progress", "signed", "archived", "cancelled"])
    .optional(),
  plannedDate: z.coerce.date().optional(),
});

const ArchivePracticeSchema = z.object({
  id: z.coerce.number().int().positive(),
  reason: z.string().max(500).optional(),
});

// Re-export inferred types so consuming components import from a single source.
export type CreatePracticeInput = z.infer<typeof CreatePracticeSchema>;
export type UpdatePracticeInput = z.infer<typeof UpdatePracticeSchema>;
export type ArchivePracticeInput = z.infer<typeof ArchivePracticeSchema>;

// ─── Auth helpers (stub until module-add auth wires `auth.api.getSession()`) ─

async function getCurrentTenantId(): Promise<string> {
  // TODO: replace stub with the real call once `module-add auth` runs:
  //   import { auth } from "@/lib/auth";
  //   import { headers } from "next/headers";
  //   const session = await auth.api.getSession({ headers: await headers() });
  //   if (!session) throw new UnauthorizedError("No active session");
  //   return session.user.tenantId;
  throw new Error(
    "AUTH_NOT_WIRED: getCurrentTenantId() — implement after `module-add auth` runs"
  );
}

async function getCurrentUserId(): Promise<string> {
  throw new Error(
    "AUTH_NOT_WIRED: getCurrentUserId() — implement after `module-add auth` runs"
  );
}

function flattenZod(error: z.ZodError): {
  message: string;
  fieldErrors: Record<string, string[]>;
} {
  const flat = z.flattenError(error);
  return {
    message: "Dati non validi",
    fieldErrors: flat.fieldErrors as Record<string, string[]>,
  };
}

/**
 * Scrub server-side errors before returning to the client.
 * Never leak driver names, query fragments, or stack traces to the UI.
 * Always log the original on the server side first.
 */
function scrubError(prefix: string, e: unknown): string {
  // TODO: replace with structured logger (Pino, Sentry, Axiom) once
  //   `module-add observability` lands.
  console.error(`[${prefix}]`, e);
  return "Errore interno. Riprova tra qualche minuto.";
}

// ─── Actions ────────────────────────────────────────────────────────────────

export async function createPractice(
  input: CreatePracticeInput
): Promise<ActionResult<{ id: number }>> {
  // 1. Validate input — return { ok: false } with fieldErrors on failure.
  const parsed = CreatePracticeSchema.safeParse(input);
  if (!parsed.success) {
    const { message, fieldErrors } = flattenZod(parsed.error);
    return { ok: false, error: message, fieldErrors };
  }

  // 2. Resolve auth context BEFORE try/catch. If auth is broken, this
  //    crashes the request handler with a 500 — that's correct (it's not a
  //    recoverable error and the user should see a generic Next.js error
  //    boundary, not a leaked internal message).
  const tenantId = await getCurrentTenantId();
  const userId = await getCurrentUserId();

  // 3. Mutate + audit + revalidate.
  try {
    const result = await db.transaction(async (tx) => {
      const [row] = await tx
        .insert(practices)
        .values({
          tenantId,
          title: parsed.data.title,
          type: parsed.data.type,
          plannedDate: parsed.data.plannedDate,
        })
        .returning({ id: practices.id });

      await tx.insert(auditLog).values({
        tenantId,
        userId,
        action: "create",
        entity: "practice",
        entityId: String(row.id),
        metadata: JSON.stringify({ title: parsed.data.title }),
      });

      return row;
    });

    revalidatePath("/pratiche");
    return { ok: true, data: { id: result.id } };
  } catch (e) {
    return { ok: false, error: scrubError("createPractice", e) };
  }
}

export async function updatePractice(
  input: UpdatePracticeInput
): Promise<ActionResult<{ id: number }>> {
  const parsed = UpdatePracticeSchema.safeParse(input);
  if (!parsed.success) {
    const { message, fieldErrors } = flattenZod(parsed.error);
    return { ok: false, error: message, fieldErrors };
  }

  const tenantId = await getCurrentTenantId();
  const userId = await getCurrentUserId();

  try {
    const { id, ...rest } = parsed.data;

    await db.transaction(async (tx) => {
      // CRITICAL: tenant scoping is enforced in the WHERE clause.
      // Without `eq(practices.tenantId, tenantId)`, ANY authenticated user
      // could mutate ANY practice — a cross-tenant data breach.
      const updated = await tx
        .update(practices)
        .set(rest)
        .where(and(eq(practices.id, id), eq(practices.tenantId, tenantId)))
        .returning({ id: practices.id });

      if (updated.length === 0) {
        throw new Error("NOT_FOUND_OR_WRONG_TENANT");
      }

      await tx.insert(auditLog).values({
        tenantId,
        userId,
        action: "update",
        entity: "practice",
        entityId: String(id),
        metadata: JSON.stringify(rest),
      });
    });

    revalidatePath("/pratiche");
    revalidatePath(`/pratiche/${parsed.data.id}`);
    return { ok: true, data: { id: parsed.data.id } };
  } catch (e) {
    return { ok: false, error: scrubError("updatePractice", e) };
  }
}

export async function archivePractice(
  input: ArchivePracticeInput
): Promise<ActionResult<{ id: number }>> {
  const parsed = ArchivePracticeSchema.safeParse(input);
  if (!parsed.success) {
    const { message, fieldErrors } = flattenZod(parsed.error);
    return { ok: false, error: message, fieldErrors };
  }

  const tenantId = await getCurrentTenantId();
  const userId = await getCurrentUserId();

  try {
    await db.transaction(async (tx) => {
      const updated = await tx
        .update(practices)
        .set({ status: "archived" })
        .where(
          and(
            eq(practices.id, parsed.data.id),
            eq(practices.tenantId, tenantId),
            // Only archive if not already archived (idempotency on retry).
            isNull(practices.archivedAt)
          )
        )
        .returning({ id: practices.id });

      if (updated.length === 0) {
        // Either already archived OR wrong tenant — both treated as no-op
        // success to keep the action idempotent.
        return;
      }

      await tx.insert(auditLog).values({
        tenantId,
        userId,
        action: "archive",
        entity: "practice",
        entityId: String(parsed.data.id),
        metadata: JSON.stringify({ reason: parsed.data.reason }),
      });
    });

    revalidatePath("/pratiche");
    return { ok: true, data: { id: parsed.data.id } };
  } catch (e) {
    return { ok: false, error: scrubError("archivePractice", e) };
  }
}
