#!/usr/bin/env python3
"""test_scan_launch.py — fixtures for scan_launch.py.

Two halves, and the second is the one that matters. Finding a missing sitemap is
easy; the tests that earn their place are the ones asserting the scanner does NOT
report something — metadata inherited from a layout, a robots.ts that branches on
the environment, authenticated routes absent from a sitemap on purpose. A scanner
that cries wolf three times stops being read, so the false positives are the suite.

Usage: python3 test_scan_launch.py
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from scan_launch import scan  # noqa: E402

PASS, FAIL = [], []


def check(name: str, cond: bool) -> None:
    (PASS if cond else FAIL).append(name)
    print(("  ok   " if cond else "  FAIL ") + name)


def status(findings, check_name: str) -> str | None:
    return next((f.status for f in findings if f.check == check_name), None)


def detail(findings, check_name: str) -> str:
    return next((f.detail for f in findings if f.check == check_name), "")


def build(root: Path, files: dict[str, str]) -> None:
    for rel, body in files.items():
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(body, encoding="utf-8")


PAGE_BARE = "export default function Page() { return <main/> }\n"
PAGE_META = ("export const metadata = {\n  title: 'Pricing',\n  description: 'What it costs',\n}\n"
             + PAGE_BARE)

print("== it finds what is missing ==")
with tempfile.TemporaryDirectory() as d:
    root = Path(d)
    build(root, {"app/page.tsx": PAGE_BARE, "app/pricing/page.tsx": PAGE_BARE,
                 "package.json": '{"name":"x"}',
                 ".workflow/meta.json": '{"stack": {"analytics": ["traffic"]}}'})
    f = scan(root)
    check("no metadata → title reported", status(f, "route-title-missing") == "missing")
    check("no metadata → description reported", status(f, "route-description-missing") == "missing")
    check("no robots → reported", status(f, "robots-missing") == "missing")
    check("no sitemap → reported", status(f, "sitemap-missing") == "missing")
    check("no favicon → reported", status(f, "favicon-incomplete") == "missing")
    check("no og image → reported", status(f, "social-preview") == "missing")
    check("no privacy route → reported", status(f, "privacy-page-missing") == "missing")
    check("no terms route → reported", status(f, "terms-page-missing") == "missing")
    check("no identity route → reported", status(f, "identity-block-missing") == "missing")
    check("no analytics dep → reported", status(f, "analytics-absent") == "missing")
    check("no internal route → nothing claimed", status(f, "internal-route-indexable") == "ok")
    check("identity block routes to the user",
          next(x.routed_to for x in f if x.check == "identity-block-missing") == "the user")

print("\n== it does NOT cry wolf ==")
with tempfile.TemporaryDirectory() as d:
    root = Path(d)
    build(root, {
        # title/description come from the LAYOUT — a page without an export is fine
        "app/layout.tsx": "export const metadata = { title: 'Acme', description: 'A shop' }\n",
        "app/page.tsx": PAGE_BARE,
        "app/docs/page.tsx": PAGE_BARE,
        # robots disallows everything, but branches on the environment
        "app/robots.ts": ("export default function robots() {\n"
                          "  return process.env.VERCEL_ENV === 'production'\n"
                          "    ? { rules: { userAgent: '*', allow: '/' } }\n"
                          "    : { rules: { userAgent: '*', disallow: '/' } }\n}\n"),
        "app/sitemap.ts": "export default function sitemap() { return ['/', '/docs'] }\n",
        "app/icon.png": "x", "app/apple-icon.png": "x",
        "app/opengraph-image.tsx": "export default function OG() {}\n",
        "app/privacy/page.tsx": PAGE_META,
        "app/terms/page.tsx": PAGE_META,
        "app/legal/page.tsx": PAGE_META,
        "package.json": '{"dependencies":{"@vercel/analytics":"^1"}}',
    })
    f = scan(root)
    check("metadata inherited from layout → NOT reported", status(f, "route-title-missing") == "ok")
    check("env-branched robots → not a hard finding",
          status(f, "robots-blocks-everything") in {"ok", "unknown"})
    check("favicon + apple-icon → ok", status(f, "favicon-incomplete") == "ok")
    check("og image present → ok", status(f, "social-preview") == "ok")
    check("privacy route found → ok", status(f, "privacy-page-missing") == "ok")
    check("terms route found → ok", status(f, "terms-page-missing") == "ok")
    check("legal route counts as identity → ok", status(f, "identity-block-missing") == "ok")
    check("analytics dependency → ok", status(f, "analytics-absent") == "ok")

with tempfile.TemporaryDirectory() as d:
    root = Path(d)
    build(root, {
        "app/layout.tsx": "export const metadata = { title: 'A', description: 'B' }\n",
        "app/page.tsx": PAGE_BARE,
        # authenticated routes SHOULD be absent from a sitemap
        "app/(app)/dashboard/page.tsx": PAGE_BARE,
        "app/admin/users/page.tsx": PAGE_BARE,
        "app/sitemap.ts": "export default function sitemap() { return ['/'] }\n",
        "package.json": "{}",
    })
    f = scan(root)
    check("authenticated routes not demanded in the sitemap",
          status(f, "sitemap-missing-routes") == "ok")

with tempfile.TemporaryDirectory() as d:
    root = Path(d)
    build(root, {
        "app/layout.tsx": "export const metadata = { title: 'A', description: 'B' }\n",
        "app/page.tsx": PAGE_BARE,
        "app/sitemap.ts": ("export default async function sitemap() {\n"
                           "  const posts = await getPosts()\n"
                           "  return posts.map(p => ({ url: p.slug }))\n}\n"),
        "package.json": "{}",
    })
    f = scan(root)
    check("dynamic sitemap → unknown, not a false finding",
          status(f, "sitemap-missing-routes") == "unknown")

# The three regressions that a real project found, each with its false-positive twin.
# Annotix produced six findings from these and every one of them was wrong.
LEGAL_DYNAMIC = """const PAGES = ["privacy", "cookies", "terms"] as const
export function generateStaticParams() {
  return PAGES.map((page) => ({ page }))
}
export default function Page() { return <main/> }
"""

with tempfile.TemporaryDirectory() as d:
    root = Path(d)
    build(root, {
        "app/layout.tsx": "export const metadata = { title: 'A', description: 'B' }\n",
        "app/page.tsx": PAGE_BARE,
        "app/legal/[page]/page.tsx": LEGAL_DYNAMIC,
        "package.json": "{}",
    })
    f = scan(root)
    check("privacy behind generateStaticParams → NOT reported",
          status(f, "privacy-page-missing") == "ok")
    check("terms behind generateStaticParams → NOT reported",
          status(f, "terms-page-missing") == "ok")
    check("the slugs are shown as the evidence",
          "privacy" in detail(f, "privacy-page-missing"))

with tempfile.TemporaryDirectory() as d:
    root = Path(d)
    build(root, {
        "app/layout.tsx": "export const metadata = { title: 'A', description: 'B' }\n",
        "app/page.tsx": PAGE_BARE,
        # a dynamic route whose slugs are fetched: the scanner must NOT claim they exist
        "app/legal/[page]/page.tsx": ("export async function generateStaticParams() {\n"
                                      "  return (await getPages()).map((page) => ({ page }))\n}\n"
                                      + PAGE_BARE),
        "package.json": "{}",
    })
    f = scan(root)
    check("slugs it cannot read → privacy still reported, never assumed",
          status(f, "privacy-page-missing") == "missing")

# One hop, because the list moves out of the page the moment the sitemap needs it
# too — which is exactly what fixing the sitemap finding did to annotix.
SHARED = 'export const LEGAL_PAGES = ["privacy", "terms"] as const\n'

with tempfile.TemporaryDirectory() as d:
    root = Path(d)
    build(root, {
        "app/layout.tsx": "export const metadata = { title: 'A', description: 'B' }\n",
        "app/page.tsx": PAGE_BARE,
        "lib/legal-pages.ts": SHARED,
        "app/legal/[page]/page.tsx": ('import { LEGAL_PAGES } from "@/lib/legal-pages"\n'
                                      "export function generateStaticParams() {\n"
                                      "  return LEGAL_PAGES.map((page) => ({ page }))\n}\n"
                                      + PAGE_BARE),
        "package.json": "{}",
    })
    f = scan(root)
    check("slugs behind an @/ import → followed one hop",
          status(f, "privacy-page-missing") == "ok")

with tempfile.TemporaryDirectory() as d:
    root = Path(d)
    build(root, {
        "app/layout.tsx": "export const metadata = { title: 'A', description: 'B' }\n",
        "app/page.tsx": PAGE_BARE,
        "app/legal/[page]/pages.ts": SHARED,
        "app/legal/[page]/page.tsx": ('import { LEGAL_PAGES } from "./pages"\n'
                                      "export function generateStaticParams() {\n"
                                      "  return LEGAL_PAGES.map((page) => ({ page }))\n}\n"
                                      + PAGE_BARE),
        "package.json": "{}",
    })
    f = scan(root)
    check("slugs behind a relative import → followed one hop",
          status(f, "privacy-page-missing") == "ok")

with tempfile.TemporaryDirectory() as d:
    root = Path(d)
    build(root, {
        "app/layout.tsx": "export const metadata = { title: 'A', description: 'B' }\n",
        "app/page.tsx": PAGE_BARE,
        # an unrelated module that happens to contain the word — the binding is
        # never used inside generateStaticParams, so following it would turn a
        # missing privacy page into a silent pass
        "lib/nav.ts": 'export const FOOTER = ["privacy", "terms"] as const\n',
        "app/legal/[page]/page.tsx": ('import { FOOTER } from "@/lib/nav"\n'
                                      'import { getSlugs } from "some-package"\n'
                                      "export async function generateStaticParams() {\n"
                                      "  return (await getSlugs()).map((page) => ({ page }))\n}\n"
                                      + PAGE_BARE),
        "package.json": "{}",
    })
    f = scan(root)
    check("an import the body never uses → NOT followed, privacy still reported",
          status(f, "privacy-page-missing") == "missing")

with tempfile.TemporaryDirectory() as d:
    root = Path(d)
    build(root, {
        "app/layout.tsx": "export const metadata = { title: 'A', description: 'B' }\n",
        "app/page.tsx": PAGE_BARE,
        "app/showcase/page.tsx": PAGE_BARE,
        "package.json": "{}",
    })
    f = scan(root)
    check("an internal route left public → reported",
          status(f, "internal-route-indexable") == "missing")

with tempfile.TemporaryDirectory() as d:
    root = Path(d)
    build(root, {
        "app/layout.tsx": "export const metadata = { title: 'A', description: 'B' }\n",
        "app/page.tsx": PAGE_BARE,
        # three ways of having already thought about it
        "app/showcase/page.tsx": "export const metadata = { robots: { index: false } }\n" + PAGE_BARE,
        "app/playground/page.tsx": PAGE_BARE,
        "app/robots.ts": ("export default function robots() {\n"
                          "  return { rules: { userAgent: '*', disallow: ['/playground'] } }\n}\n"),
        # whole-segment matching: these are product pages that merely contain the words
        "app/developers/page.tsx": PAGE_BARE,
        "app/testimonials/page.tsx": PAGE_BARE,
        "package.json": "{}",
    })
    f = scan(root)
    check("noindex on the internal route → NOT reported",
          status(f, "internal-route-indexable") == "ok")
    check("/developers and /testimonials are not /dev and /test",
          status(f, "internal-route-indexable") == "ok")

FORM_PRIMITIVE = ("export function FormField() {\n"
                  "  return <form.Field name={name}>{(f) => <input/>}</form.Field>\n}\n")
FORM_ROUTER = ("export function SignIn() {\n"
               "  const router = useRouter()\n"
               "  return <form onSubmit={async () => { await go(); router.push(next) }} />\n}\n")
FORM_SILENT = "export function Contact() { return <form onSubmit={send} /> }\n"

with tempfile.TemporaryDirectory() as d:
    root = Path(d)
    build(root, {
        "app/layout.tsx": "export const metadata = { title: 'A', description: 'B' }\n",
        "app/page.tsx": PAGE_BARE,
        "lib/forms/FormField.tsx": FORM_PRIMITIVE,
        "package.json": "{}",
    })
    f = scan(root)
    check("<form.Field is a render prop, not a form → NOT reported",
          status(f, "form-without-confirmation") == "ok")
    check("and it is not counted as a form at all",
          detail(f, "form-without-confirmation").startswith("all 0 "))

with tempfile.TemporaryDirectory() as d:
    root = Path(d)
    build(root, {
        "app/layout.tsx": "export const metadata = { title: 'A', description: 'B' }\n",
        "app/page.tsx": PAGE_BARE,
        "components/sign-in-form.tsx": FORM_ROUTER,
        "package.json": "{}",
    })
    f = scan(root)
    check("router.push counts as a success path",
          status(f, "form-without-confirmation") == "ok")

with tempfile.TemporaryDirectory() as d:
    root = Path(d)
    build(root, {
        "app/layout.tsx": "export const metadata = { title: 'A', description: 'B' }\n",
        "app/page.tsx": PAGE_BARE,
        "components/contact-form.tsx": FORM_SILENT,
        "package.json": "{}",
    })
    f = scan(root)
    check("a form that really does go silent is still reported",
          status(f, "form-without-confirmation") == "missing")

print("\n== it refuses to guess ==")
with tempfile.TemporaryDirectory() as d:
    root = Path(d)
    build(root, {"app/page.tsx": PAGE_META, "package.json": "{}"})
    f = scan(root)
    check("above-the-fold is unknown, never 'missing'", status(f, "cta-above-the-fold") == "unknown")
with tempfile.TemporaryDirectory() as d:
    root = Path(d)
    build(root, {"package.json": "{}"})
    f = scan(root)
    check("no app/ directory → unknown, and nothing else asserted",
          len(f) == 1 and f[0].status == "unknown")

print("== somebody else's brand on our page ==")
VISA = "export function VisaLogo() { return <svg/> }\n"
VISA_ATTRIB = "/* Artwork: Simple Icons (CC0-1.0). Visa is a trademark of its respective owner. */\n" + VISA
with tempfile.TemporaryDirectory() as d:
    root = Path(d)
    build(root, {"app/page.tsx": PAGE_META, "package.json": "{}",
                 "components/logos/visa.tsx": VISA, "components/logos/mastercard.tsx": VISA})
    f = scan(root)
    check("marks with no provenance → unknown, for a human",
          status(f, "third-party-marks") == "unknown")
    check("it names them", "2 of 2" in detail(f, "third-party-marks"))
with tempfile.TemporaryDirectory() as d:
    root = Path(d)
    build(root, {"app/page.tsx": PAGE_META, "package.json": "{}",
                 "components/logos/visa.tsx": VISA_ATTRIB})
    f = scan(root)
    check("a mark that records its source → ok", status(f, "third-party-marks") == "ok")
with tempfile.TemporaryDirectory() as d:
    root = Path(d)
    # `brand/` is OUR mark. Reporting it as a trademark risk is the false positive that would
    # teach people to stop reading this report.
    build(root, {"app/page.tsx": PAGE_META, "package.json": "{}",
                 "components/shared/brand/fitroom-logo.tsx": "export const Lockup = () => <svg/>\n"})
    f = scan(root)
    check("our own logo under brand/ is never a finding", status(f, "third-party-marks") == "ok")
with tempfile.TemporaryDirectory() as d:
    root = Path(d)
    build(root, {"app/page.tsx": PAGE_META, "package.json": "{}",
                 "node_modules/pkg/logos/stripe.tsx": VISA,
                 ".claude/worktrees/copy/components/logos/visa.tsx": VISA})
    f = scan(root)
    check("a dependency's logos and a worktree copy are not ours to audit",
          status(f, "third-party-marks") == "ok")


print("\n== measurement: only where the project chose to measure ==")
MEASURED = """# PRD\n\n## Measurement\n\nDecided before launch, not after. Levels: traffic, product.\n\n- **Activation event**: `invoice_sent` — the first invoice goes out\n- **Retention targets**: D7 ≥ 25 % · D30 ≥ 15 % of activated users\n- **False positives to watch**: sign-ups without an invoice\n- **Events to instrument**: `invoice_sent` (send action)\n"""
TBD = MEASURED.replace("D7 ≥ 25 %", "D7 ≥ <TBD — needs user input>")
NO_EVENT = MEASURED.replace("- **Activation event**: `invoice_sent` — the first invoice goes out\n", "")


def meta(levels, **extra) -> str:
    import json
    return json.dumps({"stack": {"analytics": levels, **extra}})


with tempfile.TemporaryDirectory() as d:
    root = Path(d)
    build(root, {"app/page.tsx": PAGE_META, "package.json": '{"name":"x"}', ".workflow/meta.json": '{"stack": {}}'})
    f = scan(root)
    check("not measuring → analytics not requested", status(f, "analytics-absent") == "not requested")
    check("not measuring → targets not requested", status(f, "measurement-targets") == "not requested")
    check("not measuring → activation not requested", status(f, "activation-instrumented") == "not requested")

with tempfile.TemporaryDirectory() as d:
    root = Path(d)
    build(root, {"app/page.tsx": PAGE_META, "package.json": '{"dependencies":{"@vercel/analytics":"^2"}}',
                 ".workflow/meta.json": meta(["traffic"])})
    f = scan(root)
    check("traffic only → analytics ok", status(f, "analytics-absent") == "ok")
    check("traffic only → no targets demanded", status(f, "measurement-targets") == "ok"
          and "traffic only" in detail(f, "measurement-targets"))
    check("traffic only → activation not checked", status(f, "activation-instrumented") == "not requested")

for prd, label in ((None, "no Measurement section"), (TBD, "TBD in a target"), (NO_EVENT, "no activation event")):
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        files = {"app/page.tsx": PAGE_META, "package.json": '{"name":"x"}',
                 "lib/analytics/track.ts": "export async function track() {}\n",
                 ".workflow/meta.json": meta(["product"])}
        if prd is not None:
            files[".workflow/PRD.md"] = prd
        build(root, files)
        f = scan(root)
        check(f"product, {label} → targets missing", status(f, "measurement-targets") == "missing")
        check(f"product, {label} → routed to prd-from-idea",
              next(x.routed_to for x in f if x.check == "measurement-targets") == "prd-from-idea")

with tempfile.TemporaryDirectory() as d:
    root = Path(d)
    build(root, {"app/page.tsx": PAGE_META, "package.json": '{"name":"x"}',
                 "lib/analytics/track.ts": "export async function track() {}\n",
                 ".workflow/meta.json": meta(["product"]), ".workflow/PRD.md": MEASURED})
    f = scan(root)
    check("product wiring counts as analytics", status(f, "analytics-absent") == "ok")
    check("complete Measurement → targets ok", status(f, "measurement-targets") == "ok")
    check("activation event not in code → missing", status(f, "activation-instrumented") == "missing")
    check("activation missing → routed to module-add analytics",
          next(x.routed_to for x in f if x.check == "activation-instrumented") == "module-add analytics")
    build(root, {"app/actions.ts": "await track(userId, 'invoice_sent', { amount })\n"})
    check("activation event tracked → ok", status(scan(root), "activation-instrumented") == "ok")

with tempfile.TemporaryDirectory() as d:  # monorepo: .workflow at the root, the app in apps/web
    root = Path(d)
    build(root, {"apps/web/app/page.tsx": PAGE_META, "apps/web/package.json": '{"name":"web"}',
                 "apps/web/lib/analytics/track.ts": "export async function track() {}\n",
                 "apps/web/app/actions.ts": 'await track(u, "invoice_sent")\n',
                 ".workflow/meta.json": meta(["product"]), ".workflow/PRD.md": MEASURED})
    f = scan(root)
    check("monorepo → targets read from the root", status(f, "measurement-targets") == "ok")
    check("monorepo → activation found in apps/web", status(f, "activation-instrumented") == "ok")

with tempfile.TemporaryDirectory() as d:
    root = Path(d)
    build(root, {"app/page.tsx": PAGE_META, "package.json": '{"dependencies":{"@openpanel/nextjs":"^1"}}',
                 ".workflow/meta.json": meta(["advanced"], analytics_provider="openpanel")})
    f = scan(root)
    check("OpenPanel dependency → analytics ok", status(f, "analytics-absent") == "ok")
    check("advanced without product → no targets demanded, not 'not requested'",
          status(f, "measurement-targets") == "ok")

with tempfile.TemporaryDirectory() as d:  # a provider without the advanced level: a hand edit, not a crash
    root = Path(d)
    build(root, {"app/page.tsx": PAGE_META, "package.json": '{"name":"x"}',
                 ".workflow/meta.json": meta([], analytics_provider="posthog")})
    f = scan(root)
    check("provider without advanced → findings, no crash", status(f, "analytics-absent") is not None)

with tempfile.TemporaryDirectory() as d:  # an unreadable meta.json is "not measuring", not a traceback
    root = Path(d)
    build(root, {"app/page.tsx": PAGE_META, "package.json": '{"name":"x"}', ".workflow/meta.json": "{oops"})
    check("invalid meta.json → not requested", status(scan(root), "analytics-absent") == "not requested")

UNFILLED = MEASURED.replace("`invoice_sent` — the first invoice goes out", "`<event_name>` — <what the user has done>") \
                   .replace("D7 ≥ 25 % · D30 ≥ 15 %", "D7 ≥ <n> % · D30 ≥ <n> %")
with tempfile.TemporaryDirectory() as d:  # the template left unfilled is not a target
    root = Path(d)
    build(root, {"app/page.tsx": PAGE_META, "package.json": '{"name":"x"}',
                 "lib/analytics/track.ts": "export async function track() {}\n",
                 ".workflow/meta.json": meta(["product"]), ".workflow/PRD.md": UNFILLED})
    check("unfilled template placeholders → targets missing", status(scan(root), "measurement-targets") == "missing")

with tempfile.TemporaryDirectory() as d:  # src/ layout: the dependencies are in the root package.json
    root = Path(d)
    build(root, {"src/app/page.tsx": PAGE_META, "package.json": '{"dependencies":{"@vercel/analytics":"^2"}}',
                 ".workflow/meta.json": meta(["traffic"])})
    check("src/ layout → root package.json read", status(scan(root), "analytics-absent") == "ok")

for call, label in (("await track(\n  userId,\n  'invoice_sent',\n)", "a call over several lines"),
                    ("await track(userId, ACTIVATION_EVENT)", "the ACTIVATION_EVENT constant")):
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        build(root, {"app/page.tsx": PAGE_META, "package.json": '{"name":"x"}',
                     "lib/analytics/track.ts": "export async function track() {}\n",
                     "app/actions.ts": call + "\n",
                     ".workflow/meta.json": meta(["product"]), ".workflow/PRD.md": MEASURED})
        check(f"activation tracked with {label} → ok", status(scan(root), "activation-instrumented") == "ok")

with tempfile.TemporaryDirectory() as d:  # the printed report, not only scan(): "not requested" must render
    import subprocess
    root = Path(d)
    build(root, {"app/page.tsx": PAGE_META, "package.json": '{"name":"x"}', ".workflow/meta.json": '{"stack": {}}'})
    r = subprocess.run([sys.executable, str(Path(__file__).parent / "scan_launch.py"), str(root)],
                       capture_output=True, text=True)
    check("report renders 'not requested' without crashing",
          r.returncode == 0 and "analytics-absent: measurement not requested" in r.stdout)

print(f"\n{len(PASS)} passed, {len(FAIL)} failed")
sys.exit(1 if FAIL else 0)
