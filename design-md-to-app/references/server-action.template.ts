"use server";

import { z } from "zod";
import { revalidatePath } from "next/cache";
import { db } from "@/lib/db";
import { practices } from "@/lib/db/schema";
import { eq } from "drizzle-orm";

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
//     reads the affected data, so caches don't lie to the user.
//   • Authorization (tenant scoping, RBAC) goes here, BEFORE the DB call.
//     Stub: TODO once `module-add auth` integrates with these actions.
// ────────────────────────────────────────────────────────────────────────────

export type ActionResult<T> =
  | { ok: true; data: T }
  | { ok: false; error: string; fieldErrors?: Record<string, string[]> };

// ─── Schemas ────────────────────────────────────────────────────────────────

const CreatePracticeSchema = z.object({
  title: z.string().min(3, "Il titolo deve avere almeno 3 caratteri").max(200),
  type: z.enum([
    "compravendita",
    "mutuo",
    "societa",
    "successione",
    "altro",
  ]),
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

// ─── Helper ─────────────────────────────────────────────────────────────────

async function getCurrentTenantId(): Promise<string> {
  // TODO: wire up to the better-auth session once auth + tenant middleware
  // are in place. For now, a placeholder that callers handle as a hard error.
  throw new Error(
    "getCurrentTenantId() not yet wired — implement after `module-add auth` runs."
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

// ─── Actions ────────────────────────────────────────────────────────────────

export async function createPractice(
  input: z.input<typeof CreatePracticeSchema>
): Promise<ActionResult<{ id: number }>> {
  const parsed = CreatePracticeSchema.safeParse(input);
  if (!parsed.success) {
    const { message, fieldErrors } = flattenZod(parsed.error);
    return { ok: false, error: message, fieldErrors };
  }

  try {
    const tenantId = await getCurrentTenantId();
    const [row] = await db
      .insert(practices)
      .values({
        tenantId,
        title: parsed.data.title,
        type: parsed.data.type,
        plannedDate: parsed.data.plannedDate,
      })
      .returning({ id: practices.id });

    revalidatePath("/pratiche");
    return { ok: true, data: { id: row.id } };
  } catch (e) {
    return {
      ok: false,
      error: e instanceof Error ? e.message : "Errore sconosciuto",
    };
  }
}

export async function updatePractice(
  input: z.input<typeof UpdatePracticeSchema>
): Promise<ActionResult<{ id: number }>> {
  const parsed = UpdatePracticeSchema.safeParse(input);
  if (!parsed.success) {
    const { message, fieldErrors } = flattenZod(parsed.error);
    return { ok: false, error: message, fieldErrors };
  }

  try {
    const tenantId = await getCurrentTenantId();
    const { id, ...rest } = parsed.data;

    await db
      .update(practices)
      .set(rest)
      .where(eq(practices.id, id));
    // NOTE: tenant scoping must be enforced here once auth wires up:
    //   .where(and(eq(practices.id, id), eq(practices.tenantId, tenantId)))

    revalidatePath("/pratiche");
    revalidatePath(`/pratiche/${id}`);
    void tenantId; // suppress "unused" until the line above is enabled
    return { ok: true, data: { id } };
  } catch (e) {
    return {
      ok: false,
      error: e instanceof Error ? e.message : "Errore sconosciuto",
    };
  }
}

export async function archivePractice(
  input: z.input<typeof ArchivePracticeSchema>
): Promise<ActionResult<{ id: number }>> {
  const parsed = ArchivePracticeSchema.safeParse(input);
  if (!parsed.success) {
    const { message, fieldErrors } = flattenZod(parsed.error);
    return { ok: false, error: message, fieldErrors };
  }

  try {
    const tenantId = await getCurrentTenantId();
    void tenantId;

    await db
      .update(practices)
      .set({ status: "archived" })
      .where(eq(practices.id, parsed.data.id));

    revalidatePath("/pratiche");
    return { ok: true, data: { id: parsed.data.id } };
  } catch (e) {
    return {
      ok: false,
      error: e instanceof Error ? e.message : "Errore sconosciuto",
    };
  }
}
