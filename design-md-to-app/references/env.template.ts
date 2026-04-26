import { z } from "zod";

/**
 * Validated environment variables. Imported once at boot; throws with a
 * clear message if any required variable is missing or malformed.
 *
 * Pattern (per design-md-to-app §Env validation):
 *   - Schema declared at module top.
 *   - `.parse(process.env)` runs at import time — failure crashes the
 *     process before serving the first request.
 *   - All consumers import `env.X` instead of `process.env.X`, getting
 *     the inferred type for free.
 *
 * Each `module-add` run extends this file with its own required vars.
 */
const schema = z.object({
  // ─── App ─────────────────────────────────────────────────────────────────
  NODE_ENV: z.enum(["development", "production", "test"]).default("development"),
  NEXT_PUBLIC_APP_URL: z
    .string()
    .url("NEXT_PUBLIC_APP_URL must be a valid URL")
    .default("http://localhost:3000"),

  // ─── Database (added by `module-add db`) ─────────────────────────────────
  // Marked optional so dev `pnpm dev` boots without a DB; in production
  // we re-validate via `if (env.NODE_ENV === "production") …` below.
  DATABASE_URL: z
    .string()
    .url("DATABASE_URL must be a valid postgres URL")
    .startsWith("postgres", "DATABASE_URL must start with postgres:// or postgresql://")
    .optional(),

  // ─── Auth (added by `module-add auth`) ───────────────────────────────────
  BETTER_AUTH_SECRET: z
    .string()
    .min(32, "BETTER_AUTH_SECRET must be at least 32 chars (run `openssl rand -base64 32`)")
    .optional(),
  BETTER_AUTH_URL: z.string().url().optional(),
});

const parsed = schema.safeParse(process.env);

if (!parsed.success) {
  console.error("❌ Invalid environment variables:");
  for (const [key, err] of Object.entries(parsed.error.flatten().fieldErrors)) {
    console.error(`  • ${key}: ${(err as string[]).join(", ")}`);
  }
  throw new Error("Environment validation failed — see logs above. Check .env.local against .env.local.example.");
}

const raw = parsed.data;

// In production, all module-required vars must be present.
if (raw.NODE_ENV === "production") {
  const missing: string[] = [];
  if (raw.DATABASE_URL === undefined) missing.push("DATABASE_URL");
  if (raw.BETTER_AUTH_SECRET === undefined) missing.push("BETTER_AUTH_SECRET");
  if (missing.length > 0) {
    throw new Error(
      `Missing production env vars: ${missing.join(", ")}. Set them in your hosting provider (Vercel/Fly/etc.).`
    );
  }
}

export const env = raw;
export type Env = typeof env;
