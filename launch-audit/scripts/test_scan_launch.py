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
                 "package.json": '{"name":"x"}'})
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

print(f"\n{len(PASS)} passed, {len(FAIL)} failed")
sys.exit(1 if FAIL else 0)
