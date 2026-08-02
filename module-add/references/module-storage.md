# module-add → `storage` (Vercel Blob — default)

Wire **Vercel Blob** as the file-storage layer of an existing scaffold. Defaults: one private store, a `lib/storage/blob.ts` helper with size/type limits enforced **server-side**, auth-gated uploads, and a `files` table that associates every blob with the user who uploaded it.

**Why Blob is the default here, not UploadThing or S3.** dev-flow's default deploy target is Vercel (`stack.deploy = "vercel"`). Blob is same-platform: no second vendor, no second dashboard or billing relationship, no extra sub-processor to add to the GDPR register that `compliance-audit` builds, and credentials arrive automatically on the linked Vercel project (OIDC — no long-lived secret in your env). UploadThing and S3 remain documented alternatives at the bottom of this file — pick them only when the user explicitly asks.

> **Versions checked 2026-08**: `@vercel/blob@2.6.1`. Docs: <https://vercel.com/docs/vercel-blob> and <https://vercel.com/docs/vercel-blob/using-blob-sdk>.

## Idempotency check

Before doing anything, check whether storage is already wired:

1. `<project-root>/package.json` contains `"@vercel/blob"` in `dependencies`.
2. `<project-root>/lib/storage/blob.ts` exists.
3. `<project-root>/app/api/upload/route.ts` exists (the client-upload token handshake).
4. `<project-root>/.env.local.example` contains `BLOB_READ_WRITE_TOKEN`.

If all four: tell the user it's installed, offer to add a new upload surface or re-pull the env vars (`vercel env pull`). Don't double-install.

## Prerequisites

- **`auth` is strongly recommended.** Without it, `onBeforeGenerateToken` has nobody to authenticate and your upload route allows **anonymous writes to your store**. The Vercel docs are explicit about this: *"You must authenticate and authorize the user inside this function. If you skip this step, your upload route allows anonymous uploads to your Blob store."* If `stack.auth` is null, ask before proceeding.
- **`db` is recommended.** Blob stores bytes; it does not know which user owns which file. The `files` table below is what makes an upload queryable and deletable (DSAR erasure needs this).
- Framework: Next.js 16 App Router. The client-upload route handler and Server Action shapes below assume it.

## Out-of-band setup (the user does this, before the code runs)

1. Create the store: project → **Storage** tab → **Create Database** → **Blob** → **Continue** → set access to **Private** or **Public** → name it → **Create a new Blob store**.
   - **This choice is permanent.** *"You cannot change it after the creation of a blob store."* Private = read requires auth and is delivered through your Functions via `get()`. Public = anyone with the URL can read, delivered straight from the blob URL. **Default to Private** for anything user-generated; use Public only for assets you'd happily put on a CDN anyway (marketing images, public avatars).
2. Choose the **region** at creation time — also permanent. Stores can be created in any of the 20 Vercel regions. **For EU projects pick an EU region** (`fra1` Frankfurt, `cdg1` Paris, `dub1` Dublin, `arn1` Stockholm, `lhr1` London). See the GDPR note below.
3. Select the environments that get the token. **Production** and **Preview** are preselected; **also tick Development** if the user wants to work with the store locally, otherwise `vercel env pull` won't produce the Blob vars.
4. Connect the store to the project (store → **Projects** tab → **Connect to Project**) so the project gets OIDC credentials instead of relying on the static token.
5. Locally: `vercel env pull` (requires `vercel link` — see `references/module-deploy.md`).

## Install

```bash
cd <project-root>
pnpm add @vercel/blob
```

No dev dependencies. No CLI needed beyond the `vercel` CLI the user already has for `env pull`.

## Environment variables

Creating + connecting a store populates these on the Vercel project automatically. Append to `.env.local.example` so a fresh clone knows what to pull:

```
# Vercel Blob — created via the project's Storage tab, then `vercel env pull`.
# Preferred (OIDC): short-lived, auto-rotated. Present when the store is CONNECTED to the project.
BLOB_STORE_ID=store_xxxxxxxxxxxx
VERCEL_OIDC_TOKEN=<pulled by `vercel env pull`, rotates automatically>
# Fallback: long-lived static token. Required for `handleUpload` (client uploads) — OIDC is NOT accepted there.
BLOB_READ_WRITE_TOKEN=vercel_blob_rw_xxxxxxxx
# Only when using presigned-URL uploads / webhook callbacks — `[VERIFY]` against the
# current docs before relying on it; this path is newer than the two above.
BLOB_WEBHOOK_PUBLIC_KEY=
```

Credential resolution order in the SDK, first match wins: (1) an explicit `token` option, (2) OIDC — `oidcToken`/`VERCEL_OIDC_TOKEN` **paired with** `storeId`/`BLOB_STORE_ID`, (3) `process.env.BLOB_READ_WRITE_TOKEN`, (4) throw.

Extend `lib/env.ts` (Zod block):

```typescript
BLOB_READ_WRITE_TOKEN: z.string().min(1),
BLOB_STORE_ID: z.string().optional(),
```

Don't validate `VERCEL_OIDC_TOKEN` — it is injected by the platform at build/runtime and absent in plain local shells.

## Server upload vs client upload — pick per surface, not per project

| | Server upload (`put()`) | Client upload (`upload()` + `handleUpload`) |
|---|---|---|
| Path | browser → your Function → Blob | browser → Blob (your Function only signs a token) |
| Size ceiling | **4.5 MB** — Vercel's request body size limit on Functions | 5 TB (`maximumSizeInBytes`), multipart recommended > 100 MB |
| Code | one Server Action | a Client Component + a route handler |
| Cost | incurs Fast Data Transfer on the way in | *"Client uploads have no data transfer charges."* |
| Use for | avatars, small PDFs, CSV imports | video, audio, large images, anything user-chosen |

Default to **server upload** for small, known-small files (it's one function and a form). Switch to **client upload** the moment the file could exceed 4.5 MB — the failure mode otherwise is a 413 that only shows up in production with a real user's file.

## Files to write

### `lib/storage/blob.ts` — the one place limits live

```typescript
import { del, head, list, put, type PutBlobResult } from "@vercel/blob";

/**
 * Upload policy. Enforced SERVER-SIDE here and mirrored into the client-upload
 * token in app/api/upload/route.ts. Never trust the browser's claimed size or
 * MIME type — `File.type` is attacker-controlled.
 */
export const MAX_UPLOAD_BYTES = 4 * 1024 * 1024; // 4 MB — under Vercel's 4.5 MB body limit
export const ALLOWED_CONTENT_TYPES = [
  "image/jpeg",
  "image/png",
  "image/webp",
  "application/pdf",
] as const;

/** All user uploads live under this prefix so `list({ prefix })` can sweep them. */
export const UPLOAD_PREFIX = "uploads";

export type UploadResult =
  | { ok: true; blob: PutBlobResult }
  | { ok: false; error: string };

/**
 * Server-side upload (Server Action / Route Handler).
 *
 * Three rules baked in:
 *   1. Size + MIME are re-checked here, after the browser.
 *   2. `addRandomSuffix: true` — blobs are immutable by default and two users
 *      uploading "avatar.jpg" must not collide. Without it, `put()` THROWS on a
 *      duplicate pathname (`allowOverwrite` defaults to false).
 *   3. Path is namespaced by ownerId, so a DSAR erasure is a prefix sweep.
 *
 * Returns `{ ok: false }` instead of throwing — mirrors the lib/server/<domain>.ts
 * convention for business errors.
 */
export async function uploadFile(params: {
  file: File;
  ownerId: string;
}): Promise<UploadResult> {
  const { file, ownerId } = params;

  if (file.size > MAX_UPLOAD_BYTES) {
    return { ok: false, error: "FILE_TOO_LARGE" };
  }
  if (!ALLOWED_CONTENT_TYPES.includes(file.type as never)) {
    return { ok: false, error: "UNSUPPORTED_FILE_TYPE" };
  }

  try {
    const blob = await put(`${UPLOAD_PREFIX}/${ownerId}/${file.name}`, file, {
      access: "private",
      addRandomSuffix: true,
      contentType: file.type,
      // cacheControlMaxAge: 60 * 60 * 24 * 30, // default is one month; min 60s
    });
    return { ok: true, blob };
  } catch (e) {
    return { ok: false, error: e instanceof Error ? e.message : "UPLOAD_FAILED" };
  }
}

/** Delete by URL or pathname. `del()` never throws on a missing blob. */
export async function deleteFile(urlOrPathname: string | string[]) {
  await del(urlOrPathname);
}

/** Metadata: { size, uploadedAt, pathname, contentType, ... }. Throws BlobNotFoundError. */
export async function getFileMetadata(urlOrPathname: string) {
  return await head(urlOrPathname);
}

/** Every blob a user owns — the read side of a DSAR export. */
export async function listUserFiles(ownerId: string) {
  return await list({ prefix: `${UPLOAD_PREFIX}/${ownerId}/` });
}
```

The `access` option is **required on every call** even though the store already decides private vs public — Vercel made it explicit on purpose so the security context is visible at the call site. Keep it matching your store; a mismatch is a runtime error, not a silent downgrade.

### `lib/db/schema.ts` — append the `files` table

Blob does not track ownership for you. Without this table you cannot answer "which files does this user own", which is exactly what a DSAR export/erasure needs.

```typescript
export const files = pgTable("files", {
  id: uuid("id").primaryKey().defaultRandom(),
  ownerId: text("owner_id").notNull().references(() => user.id, { onDelete: "cascade" }),
  pathname: text("pathname").notNull().unique(), // stable key for del()
  url: text("url").notNull(),
  downloadUrl: text("download_url").notNull(),
  contentType: text("content_type").notNull(),
  sizeBytes: integer("size_bytes").notNull(),
  createdAt: timestamp("created_at").defaultNow().notNull(),
});
```

Store the **pathname** as the durable identifier and the `url` for rendering. `put()` / `upload()` return `{ pathname, contentType, contentDisposition, url, downloadUrl, etag }` — note there is **no `size`** in that payload; get it from the incoming `File.size` (server upload) or a `head()` call (client upload).

### `lib/server/uploads.ts` — server-upload Server Action

```typescript
"use server";

import { db } from "@/lib/db";
import { files } from "@/lib/db/schema";
import { getCurrentUserId } from "@/lib/auth-server";
import { uploadFile } from "@/lib/storage/blob";

export async function uploadAvatar(formData: FormData) {
  const ownerId = await getCurrentUserId(); // throws UNAUTHORIZED — a system error, not a field error

  const file = formData.get("file");
  if (!(file instanceof File) || file.size === 0) {
    return { ok: false as const, error: "NO_FILE" };
  }

  const result = await uploadFile({ file, ownerId });
  if (!result.ok) return result;

  await db.insert(files).values({
    ownerId,
    pathname: result.blob.pathname,
    url: result.blob.url,
    downloadUrl: result.blob.downloadUrl,
    contentType: result.blob.contentType,
    sizeBytes: file.size,
  });

  return { ok: true as const, url: result.blob.url };
}
```

### `app/api/upload/route.ts` — client-upload token handshake

This is the route `upload()` calls to get a short-lived client token. **It is the security boundary.**

```typescript
import { head } from "@vercel/blob";
import { handleUpload, type HandleUploadBody } from "@vercel/blob/client";
import { NextResponse } from "next/server";
import { db } from "@/lib/db";
import { files } from "@/lib/db/schema";
import { getCurrentUserId } from "@/lib/auth-server";
import { ALLOWED_CONTENT_TYPES, MAX_UPLOAD_BYTES } from "@/lib/storage/blob";

export async function POST(request: Request): Promise<NextResponse> {
  const body = (await request.json()) as HandleUploadBody;

  try {
    const jsonResponse = await handleUpload({
      body,
      request,
      onBeforeGenerateToken: async (pathname, clientPayload) => {
        // Authenticate + authorize HERE. Skipping this makes the store world-writable.
        const ownerId = await getCurrentUserId();

        return {
          allowedContentTypes: [...ALLOWED_CONTENT_TYPES],
          maximumSizeInBytes: MAX_UPLOAD_BYTES,
          addRandomSuffix: true,
          // Never trust clientPayload for identity — only for a validated foreign key.
          tokenPayload: JSON.stringify({ ownerId, clientPayload }),
        };
      },
      onUploadCompleted: async ({ blob, tokenPayload }) => {
        // NOTE: this callback does NOT fire on localhost — Vercel Blob calls it
        // from the outside. Use a tunnel (ngrok/cloudflared) to exercise it locally.
        const { ownerId } = JSON.parse(tokenPayload ?? "{}");
        const meta = await head(blob.url);

        await db.insert(files).values({
          ownerId,
          pathname: blob.pathname,
          url: blob.url,
          downloadUrl: blob.downloadUrl,
          contentType: blob.contentType,
          sizeBytes: meta.size,
        });
      },
    });

    return NextResponse.json(jsonResponse);
  } catch (error) {
    return NextResponse.json(
      { error: error instanceof Error ? error.message : String(error) },
      { status: 400 },
    );
  }
}
```

`handleUpload` **requires a static read-write token** — *"OIDC tokens are not sufficient for `handleUpload`."* So `BLOB_READ_WRITE_TOKEN` must be present even on a store connected via OIDC.

### Reference UI: an upload control co-located with its page

Per the folder-structure rules, the upload UI lives next to the page that uses it — e.g. `app/(app)/settings/_components/avatar-upload.tsx` — not in a global `components/` folder. Write it to match `meta.json#stack.ui` (shadcn / base-ui / coss → HTML-native `<input type="file">` + the library's Button; `mui` → MUI `Button component="label"`).

```tsx
"use client";

import { useState } from "react";
import { upload } from "@vercel/blob/client";
import { ALLOWED_CONTENT_TYPES, MAX_UPLOAD_BYTES } from "@/lib/storage/blob";

export function AvatarUpload() {
  const [status, setStatus] = useState<"idle" | "uploading" | "done" | "error">("idle");
  const [progress, setProgress] = useState(0);
  const [url, setUrl] = useState<string | null>(null);

  async function onChange(event: React.ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (!file) return;

    // Client-side checks are UX only. The route handler re-enforces both.
    if (file.size > MAX_UPLOAD_BYTES) return setStatus("error");

    setStatus("uploading");
    try {
      const blob = await upload(file.name, file, {
        access: "private",
        handleUploadUrl: "/api/upload",
        contentType: file.type,
        multipart: file.size > 100 * 1024 * 1024, // recommended above 100 MB
        onUploadProgress: ({ percentage }) => setProgress(percentage),
      });
      setUrl(blob.url);
      setStatus("done");
    } catch {
      setStatus("error");
    }
  }

  return (
    <div className="flex flex-col gap-2">
      <input
        type="file"
        accept={ALLOWED_CONTENT_TYPES.join(",")}
        onChange={onChange}
        disabled={status === "uploading"}
      />
      {status === "uploading" && <progress value={progress} max={100} />}
      {status === "error" && <p className="text-destructive text-sm">Upload failed.</p>}
      {status === "done" && url && <p className="text-sm text-muted-foreground">Uploaded.</p>}
    </div>
  );
}
```

For a drag-and-drop dropzone, wrap this in a `onDrop`/`onDragOver` container — Blob ships no UI component. If the user wants a prebuilt dropzone with progress and previews out of the box, that's the honest reason to reach for UploadThing instead (see alternatives).

### Serving private blobs

A private blob's URL is not publicly readable. Deliver it through a Function:

```typescript
// app/api/files/[...pathname]/route.ts
import { get } from "@vercel/blob";
import { getCurrentUserId } from "@/lib/auth-server";

export async function GET(_: Request, ctx: { params: Promise<{ pathname: string[] }> }) {
  const ownerId = await getCurrentUserId();
  const { pathname } = await ctx.params;
  const key = pathname.join("/");

  // Authorize: the path is namespaced by ownerId, so this is the check.
  if (!key.startsWith(`uploads/${ownerId}/`)) return new Response("Not found", { status: 404 });

  // get() returns null when the blob doesn't exist; otherwise a discriminated
  // union on statusCode — { statusCode, stream, headers, blob }.
  const result = await get(key, { access: "private" });
  if (!result || result.statusCode !== 200) return new Response("Not found", { status: 404 });

  return new Response(result.stream, {
    headers: {
      "Content-Type": result.blob.contentType,
      "Cache-Control": "private, max-age=3600",
    },
  });
}
```

You control browser caching yourself via the `Cache-Control` header on **your** response — the CDN cache in front of the store is a separate layer.

## GDPR note (read this before shipping)

- **R3 — data residency.** A Blob store has a region fixed at creation and **cannot be changed afterwards**. `compliance-audit` R3 flags US-default residency; the Vercel default region for compute is `iad1` (Washington, D.C.). For an EU product, create the store in `fra1` / `cdg1` / `dub1` / `arn1` and **record it** so R3 has an answer: set `meta.json#compliance.data_residency = "eu"` and note the region in `docs/compliance/`.
- **R4 — retention / erasure.** `del()` is the erasure path. Wire it into the account-deletion flow: `listUserFiles(userId)` → `del(pathnames)` → delete the `files` rows. Without this, deleting a user leaves their uploads in the store forever.
- Blob is a **sub-processor** only in the sense that it's Vercel — which is already in the register if you deploy there. That is the whole reason it's the default here.

## Verification

```bash
pnpm typecheck
pnpm build
```

Do **not** attempt a real upload during install — it needs a real store and real credentials. Instead tell the user:

1. `vercel env pull` to get `BLOB_READ_WRITE_TOKEN` + `BLOB_STORE_ID` locally.
2. `pnpm dev`, open the page with the upload control, upload a small file.
3. Verify in the dashboard: project → **Storage** → the store → **Browser** → paste the blob URL → **Lookup**. Metadata (name, path, size, uploaded date, content type) should appear.
4. `onUploadCompleted` **will not fire on localhost** — the DB row won't appear until you test through a tunnel or a preview deployment. Expected; say so up front or the user will file it as a bug.

## Update meta.json

```json
{
  "stack": {
    "storage": "vercel-blob"
  }
}
```

## Known caveats

- **4.5 MB request body limit** on Vercel Functions kills server uploads of anything larger. This is a platform limit, not an SDK one — the fix is client uploads, not a bigger function.
- **`allowOverwrite` defaults to `false`.** A second `put()` at the same pathname **throws**. Either `addRandomSuffix: true` (recommended, and what this reference does) or generate unique pathnames yourself. Reaching for `allowOverwrite: true` is usually a design smell — treat blobs as immutable.
- **Caching is aggressive.** Blobs are cached by the CDN for up to **one month** by default, and a delete or overwrite takes **up to 60 seconds** to propagate; browsers keep serving the old bytes longer than that. Bust with a query param (`?v=<timestamp>`) or, for private blobs read server-side, `get(..., { useCache: false })`.
- **Never trust the client's MIME type.** `File.type` comes from the browser. `allowedContentTypes` in `onBeforeGenerateToken` is the enforcement point for client uploads; the explicit check in `uploadFile()` is the one for server uploads. Both are required — they cover different paths.
- **Orphaned blobs are your problem.** An upload that completes but whose owning record is never created leaves bytes you pay for. Schedule a prune: `list({ prefix })`, left-join against `files`, `del()` the unmatched ones older than ~24h. `del()` is free of charge (it counts for rate limits, not billing).
- **Billing shape**: `put()`, `upload()`, `copy()`, `list()` are *advanced operations*; `head()` and a cache-MISS URL read are *simple operations*. **Browsing the store in the Vercel dashboard costs operations too** — a refreshed file browser is a `list()`. Worth knowing before someone blames the app for an ops spike.
- **Private vs public is permanent per store.** If the user picks wrong, the fix is a new store plus a copy, not a setting.
- **`onUploadCompleted` never fires on localhost.** Design the flow so a missing callback degrades gracefully (e.g. reconcile on next page load) rather than leaving a half-created record.

---

# Alternatives (only when the user explicitly asks)

These are **not** the default. Each gets a pointer, not a recipe — implement from the vendor's current docs at the time of asking, because both drift faster than this file does.

## UploadThing

**Pick it when**: you want the prebuilt DX — a typed file router with per-type size/count limits, and drop-in `<UploadButton>` / `<UploadDropzone>` components with progress, previews and error states already styled. If "I don't want to build the dropzone" is the actual requirement, this is the honest answer.

- **Packages**: `uploadthing` (7.7.4 as of 2026-08), `@uploadthing/react` (7.3.3). React 19 supported.
- **Env var**: `UPLOADTHING_TOKEN` — a single base64 token. (v6's `UPLOADTHING_SECRET` + `UPLOADTHING_APP_ID` were **replaced** by it in v7; if you find those in an existing project, it's on v6.)
- **Shape**: `createUploadthing()` file router in `app/api/uploadthing/core.ts` with `f({ image: { maxFileSize: "4MB", maxFileCount: 1 } }).middleware(...).onUploadComplete(...)`; `createRouteHandler({ router })` from `uploadthing/next` in `app/api/uploadthing/route.ts`; `generateUploadButton<OurFileRouter>()` / `generateUploadDropzone` from `@uploadthing/react`.
- **Auth gate**: `.middleware()` — throw `UploadThingError("Unauthorized")` when there's no session. Same boundary as Blob's `onBeforeGenerateToken`.
- **Styling**: Tailwind v3 → wrap the config with `withUt` from `uploadthing/tw`. **Tailwind v4 → `@import "uploadthing/tw/v4";` in your CSS** (the package exports `./tw/v4` → `tw/v4.css`, a set of `@custom-variant` rules). Not using Tailwind → `import "@uploadthing/react/styles.css"`.
- **Gotcha**: on the returned file object, `file.url` and `file.appUrl` are **deprecated and will be removed in v9** — use **`file.ufsUrl`**. Server-side cleanup is `UTApi().deleteFiles(keys)`.
- **Trade-off**: a second vendor — separate dashboard, separate billing, an extra sub-processor for the GDPR register, and its own region/residency story to answer for R3.
- Docs: <https://docs.uploadthing.com/getting-started/appdir>, <https://docs.uploadthing.com/api-reference/ut-api>

## S3 + presigned URLs

**Pick it when**: the user must own the bucket — an existing AWS estate, a contractual/residency requirement Blob can't satisfy, or a hard "no managed file vendor" rule. Also the right call when files are consumed by other AWS services (Lambda, Athena, Glacier lifecycle).

- **Packages**: `@aws-sdk/client-s3` + `@aws-sdk/s3-request-presigner` (3.1101.0 as of 2026-08).
- **Env vars**: `AWS_REGION`, `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `S3_BUCKET`. Prefer OIDC federation from Vercel over static keys where possible.
- **Shape**: server generates a presigned `PUT` with `getSignedUrl(s3, new PutObjectCommand({ Bucket, Key, ContentType }), { expiresIn })`; the browser `PUT`s the file straight at that URL. *"A presigned URL is limited by the permissions of the user who creates it"* — so the IAM policy on the signing identity is the real access control. Max expiry with SigV4 is **7 days**.
- **CORS is mandatory** for browser `PUT`s. The S3 console takes JSON only:
  ```json
  [
    {
      "AllowedHeaders": ["*"],
      "AllowedMethods": ["PUT", "POST", "GET"],
      "AllowedOrigins": ["https://your-app.example.com"],
      "ExposeHeaders": ["ETag", "x-amz-request-id"],
      "MaxAgeSeconds": 3000
    }
  ]
  ```
- **Gotchas**: the `Content-Type` used at upload time **must match** the one you signed with or you get `SignatureDoesNotMatch`; clock skew produces the same error; block public access and serve via CloudFront or presigned `GET` rather than making the bucket public.
- **Trade-off**: the most control, the most surface — IAM, CORS, lifecycle rules, and CDN are all now yours to get right. Budget real time for it; don't pick it to save money on a small project.
- Docs: <https://docs.aws.amazon.com/AmazonS3/latest/userguide/PresignedUrlUploadObject.html>, <https://docs.aws.amazon.com/AmazonS3/latest/userguide/ManageCorsUsing.html>
