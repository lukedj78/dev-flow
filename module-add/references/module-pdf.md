# module-add → `pdf` (document generation)

Wire **PDF generation** into an existing scaffold: a renderer, the pdfcn component registry
on top of it, and one route that returns a document. The target is the ordinary product
requirement — an invoice, a report, a contract, a certificate — not a print stylesheet.

Default: **Forme** + the `@pdfcn/forme/*` registry. Read *Choosing the renderer* before
accepting that default; it is a stack decision and stack decisions are never taken silently.

## Why not a headless browser

The reflex answer to "generate a PDF" is Puppeteer or Playwright rendering a page and calling
`page.pdf()`. It works, and it costs a Chromium per invocation: a cold start measured in
seconds, a bundle that fights every serverless size limit, and a font stack that differs
between your laptop and the runtime. Both renderers below exist to avoid exactly that —
Takumi's npm description is literally *"Render paged PDFs from JSX, HTML, and CSS. No headless
browser."*

Keep the browser path in mind for one case: a document that must match an existing **web
page** pixel for pixel. Then the page *is* the spec, and re-authoring it as PDF components is
the more expensive road.

## Choosing the renderer

| | **Forme** | **Takumi** |
|---|---|---|
| Packages | `@formepdf/react`, `@formepdf/core`, `@formepdf/cli` | `takumi-pdf`, `@takumi-rs/core`, `@takumi-rs/helpers` |
| Engine | WASM | Rust — native bindings *and* WASM |
| Licence | MIT | MIT OR Apache-2.0 |
| Version (2026-09-10) | `0.22.0` | `takumi-pdf@0.14.3`, `@takumi-rs/*@2.13.7` |
| Also does | PDF only | OG images — the `@takumi-rs/*` line is an image renderer that gained PDF |
| Notable | a CLI with **live preview** while you author | native bindings where the platform allows |

Both are **pre-1.0 on the PDF path**. Say that out loud before the user builds an invoicing
flow on one: the API can move under you, and the mitigation is that pdfcn components are
copied into the repo, so a breaking change is a diff you own rather than an upgrade you take.

Pick Forme when the document is the product and authoring loop speed matters (the CLI's live
preview is a real advantage). Pick Takumi when the project already renders OG images with
`@takumi-rs/*`, or when native bindings matter for throughput.

## pdfcn — the component layer

[pdfcn](https://www.pdfcn.dev) is a **shadcn-format registry** of PDF components. Not a
dependency: the components are copied into the repo the same way shadcn's are.

Register the namespace once in `components.json`:

```json
{
  "registries": {
    "@pdfcn": "https://pdfcn.dev/r/{name}.json"
  }
}
```

Then add items, namespaced by renderer:

```bash
npx shadcn@latest add @pdfcn/forme/text        # Forme base
npx shadcn@latest add @pdfcn/takumi/text       # Takumi base
npx shadcn@latest add @pdfcn/forme/invoice-minimal   # a block = a whole template
```

The registry holds **79 items** (checked 2026-09-10): 48 components — 24 mirrored across both
bases — 20 blocks, 9 themes, 2 libs. Components declare their own dependencies, so adding one
pulls the matching renderer and the shared theme utilities.

What the 24 cover, and why the list is the interesting part: `Text`, `Heading`, `Table`,
`DataTable`, `KeyValue`, `List`, `Card`, `Alert`, `Badge`, `Divider`, `Section`, `Stack`,
`Link`, `PdfImage`, `QrCode`, `Signature`, `Graph` (bar/line/area drawn as SVG), `Watermark`,
`Form` — plus the four that only exist because this is paged media: **`PageBreak`,
`PageHeader`, `PageFooter`, `PageNumber`, and `KeepTogether`** (keeps its children on one
page). Those five are the ones you would otherwise discover the hard way.

Nine themes ship as presets (`professional`, `modern`, `minimal`, `executive`, `corporate`,
`elegant`, `vivid`, `forest`, `blueprint`). Treat them as a starting point and reconcile with
the project's DESIGN.md — a document that looks nothing like the app is a bug, not a theme.

## Usage shape

```tsx
import { Document, Page } from "@formepdf/react";
import { PdfcnThemeProvider } from "@/components/pdf/theme-provider";
import { Text } from "@/components/pdf/text";

export function Invoice() {
  return (
    <Document>
      <Page size="A4">
        <PdfcnThemeProvider>
          <Text variant="xl">Invoice</Text>
        </PdfcnThemeProvider>
      </Page>
    </Document>
  );
}
```

`Document` and `Page` come from the **renderer**; everything inside comes from pdfcn, and the
component API is identical across both bases — which is what makes switching renderers a
change of two imports rather than a rewrite.

⚠️ `[VERIFY]` The install guide's example imports from `@/components/pdf/*` while the registry
doc says components install into `components/ui/`. Read where the CLI actually put them
before writing imports; do not copy the path from either doc.

## Where it runs

PDF generation is **server work**. A Route Handler that returns the bytes:

```ts
// app/api/invoices/[id]/route.ts — shape only; check the renderer's current render API
export async function GET(_: Request, { params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const bytes = await renderInvoice(id);          // renderer call
  return new Response(bytes, {
    headers: {
      "content-type": "application/pdf",
      "content-disposition": `attachment; filename="invoice-${id}.pdf"`,
    },
  });
}
```

Three rules that are not obvious:

1. **Authorize the route like any other read.** An invoice endpoint keyed only on an id is a
   customer-data leak with a filename attached. Same session check as every other read — see
   `module-auth.md`.
2. **Never build the document from request input.** The route takes an id, loads the record,
   and renders from the record. A PDF assembled out of query parameters is a forgery
   generator on your domain.
3. **Fonts are the recurring failure.** Both engines need the font bytes, and a face that
   resolves locally will not resolve in a serverless runtime. Bundle the fonts you use and
   load them explicitly; do not rely on a system font existing.

## Idempotency check

Before doing anything, check whether the module is already wired:

1. `package.json` contains `@formepdf/react` or `takumi-pdf`.
2. `components.json` has a `registries` entry for `@pdfcn`.
3. A pdfcn component file exists (wherever the CLI put it).

All three: report it as installed, and offer to add components or a block instead of
re-running. Never re-register the namespace — a duplicate `registries` key silently wins or
loses depending on order.

## Licence — check before you ship

The renderers are clear: Forme **MIT**, Takumi **MIT OR Apache-2.0**.

**pdfcn's own components are not.** The site states no licence, and no public repository was
found (checked 2026-09-10). Since the shadcn model *copies source into your repo*, that source
becomes part of the product. For anything commercial, resolve the licence before shipping —
ask the maintainer, or treat the components as a reference implementation and write your own
from the same registry JSON. `compliance-audit` should flag this if it appears in a project.

## Recording the choice

Set `meta.json#stack.pdf` to `"forme"` or `"takumi"` and append `history`. Same shape as
`shaders` — an optional key that exists only once the capability actually ships, so a project
that never generates a document carries no key at all.

## Common mistakes

| Mistake | What happens |
|---|---|
| Puppeteer because it is familiar | a Chromium per invocation, cold starts in seconds, size limits, and fonts that differ per runtime |
| Treating the PDF as a print stylesheet of a page | paged media has page breaks, repeating headers and orphan control; CSS print gets you most of the way and then stops |
| No `KeepTogether` around a signature block or a total | the row that must not split, splits — always at the worst moment |
| Rendering from query parameters | anyone can generate an official-looking document on your domain |
| An unauthenticated `/api/invoices/[id]` | enumerable customer data, packaged for download |
| Assuming a system font | works locally, renders as a fallback (or nothing) in the runtime |
| Taking a pdfcn theme as-is | a document that looks unrelated to the app it came from |
| Shipping commercially without resolving the licence | copied source of unstated licence inside a paid product |

## What this module does NOT do

- **Does not read PDFs.** Ingesting a PDF brief is `anydoc` (see `prd-from-idea`), the other
  direction entirely.
- **Does not do e-signature.** `Signature` draws a signature *block*; legal signing is a
  service (DocuSign, Dropbox Sign) and a separate decision.
- **Does not do React Native.** Neither renderer targets RN.
