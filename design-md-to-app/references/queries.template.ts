/**
 * Server-side READ queries for the "pratica" domain.
 *
 * Convention (per design-md-to-app §Folder convention):
 *   • `lib/queries/<domain>.ts` holds READS — async functions called from
 *     React Server Components (page.tsx files).
 *   • `lib/server/<domain>.ts` (peer file) holds MUTATIONS — server actions
 *     called from forms.
 *   • Splitting reads vs writes makes data fetching cacheable separately
 *     and keeps the action surface minimal.
 *
 * Why no "use server" here:
 *   These functions are imported INTO RSC, not invoked AS server actions.
 *   They run on the server (because RSCs do), but the framework doesn't
 *   need the "use server" boundary marker.
 *
 * Multi-tenant safety:
 *   Same rule as server actions — every query MUST filter by tenantId.
 *   The auth resolver runs at the top of each query, NOT inside try/catch.
 *
 * Caching:
 *   Use Next's `unstable_cache` or `revalidateTag` for hot reads.
 *   Tag-based invalidation pairs naturally with `revalidatePath` from
 *   the matching server action.
 */
import { and, desc, eq, isNull } from "drizzle-orm";
import { db } from "@/lib/db";
import { practices } from "@/lib/db/schema";

// ─── Auth helper (replace stub after `module-add auth`) ─────────────────────

async function getCurrentTenantId(): Promise<string> {
  // TODO: replace with `auth.api.getSession({ headers: await headers() })`.
  throw new Error(
    "AUTH_NOT_WIRED: getCurrentTenantId() — implement after `module-add auth` runs"
  );
}

// ─── Queries ────────────────────────────────────────────────────────────────

/**
 * Returns the most recently updated practices for the current tenant.
 * Skips archived rows (soft-deleted via `archivedAt`).
 */
export async function getRecentPractices(limit = 20) {
  const tenantId = await getCurrentTenantId();

  return db
    .select({
      id: practices.id,
      title: practices.title,
      type: practices.type,
      status: practices.status,
      plannedDate: practices.plannedDate,
      createdAt: practices.createdAt,
    })
    .from(practices)
    .where(
      and(
        eq(practices.tenantId, tenantId),
        isNull(practices.archivedAt) // soft-delete filter
      )
    )
    .orderBy(desc(practices.createdAt))
    .limit(limit);
}

/**
 * Single-row lookup. Tenant-scoped — returns `null` if the id belongs to
 * a different tenant (don't 404 on cross-tenant access — same observable
 * behavior as not-found, no information leak about whether the id exists).
 */
export async function getPracticeById(id: number) {
  const tenantId = await getCurrentTenantId();

  const rows = await db
    .select()
    .from(practices)
    .where(and(eq(practices.id, id), eq(practices.tenantId, tenantId)))
    .limit(1);

  return rows[0] ?? null;
}

/**
 * Aggregate query: count by status, for the dashboard "practices by status"
 * card. Cached for 30 seconds since dashboards re-render often.
 */
export async function getPracticeCountsByStatus() {
  const tenantId = await getCurrentTenantId();

  // Drizzle doesn't have a direct `groupBy` aggregator helper without a
  // raw expression — for production, prefer `sql` template tag or pg's
  // `count(*) FILTER (WHERE ...)`. Keeping it simple here.
  const all = await db
    .select({ status: practices.status })
    .from(practices)
    .where(
      and(
        eq(practices.tenantId, tenantId),
        isNull(practices.archivedAt)
      )
    );

  const counts: Record<string, number> = {};
  for (const row of all) {
    counts[row.status] = (counts[row.status] ?? 0) + 1;
  }
  return counts;
}
