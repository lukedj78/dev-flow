# module-add → planned variants (not yet implemented)

The references below describe modules that are **planned** but not yet wired into `module-add`. Each gives the structural shape (packages, env vars, prerequisites, out-of-band steps) so a contributor — or a future Claude session — can implement it from the cues here.

If the user invokes `module-add` for one of these and the full reference doesn't exist yet, **stop and tell them** — don't improvise. Improvising leads to half-wired modules that look done but break in production. The right path is: implement the full reference (copying the structure of `module-auth.md` / `module-db.md` / `module-payments.md` / `module-email.md`), commit, then run.

---

## Recently implemented (no longer stubs)

- **`storage`** → `references/module-storage.md`. Vercel Blob is the default; UploadThing and S3 + presigned URLs are documented alternatives.
- **`deploy`** → `references/module-deploy.md`. Vercel project config (link, `vercel.json`, per-environment env vars, region, monorepo root directory). Alternative targets (Fly.io, Cloudflare Pages, Render, Railway) are still unimplemented variants — see the note at the end of that file.

---

## Currently open stubs

None. Every module listed in `module-add/SKILL.md` has a full reference file.

The remaining unimplemented work is **alternative variants inside existing modules**, not new modules:

| Module | Implemented variant | Unimplemented alternatives |
|---|---|---|
| `auth` | better-auth | Clerk, Auth.js, WorkOS |
| `db` | Drizzle + Neon | Prisma, Supabase, PlanetScale |
| `payments` | Stripe | Polar, Lemon Squeezy, Paddle |
| `email` | Resend + React Email | Postmark, SES, Loops (marketing — different module entirely) |
| `storage` | Vercel Blob | UploadThing and S3 are sketched in `module-storage.md`; Cloudflare R2, Supabase Storage are not |
| `deploy` | Vercel | Fly.io, Cloudflare Pages, Render, Railway |

## When to implement these

Implement on demand: the first time a user asks for that specific variant. Don't preemptively implement all of them — references that go stale (Stripe API version drift, SDK renames, env-var consolidations) hurt more than a missing variant. Implement the variant fully — including the install templates and the reference implementation — when the user asks for it.

Always update, in this order:
1. The variant's reference file (`references/module-<name>.md`) — add the variant section.
2. `module-add/SKILL.md` — the module table, if the module's default changed.
3. `dist/` — re-package the skill.
4. README — same flip.
