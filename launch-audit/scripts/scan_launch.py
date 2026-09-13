#!/usr/bin/env python3
"""scan_launch.py — launch-readiness signals for a Next.js App Router project.

Signals, never verdicts. This script reads source; it cannot know that /pricing is
noindex on purpose, or that the CTA lives in a component it did not resolve. Every
finding here is a question for a human, and `references/checks.md` says, per check,
what a legitimate false positive looks like.

It is deliberately conservative: a check that cannot answer honestly reports
`unknown` rather than guessing. A scanner that cries wolf three times stops being read.

Usage:
  scan_launch.py <project-root> [--json]
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

OK, MISS, UNKNOWN = "ok", "missing", "unknown"


@dataclass
class Finding:
    check: str
    status: str
    detail: str
    where: list[str] = field(default_factory=list)
    routed_to: str | None = None


def app_dir(root: Path) -> Path | None:
    """The Next app directory — the project root, or apps/web in a monorepo."""
    for candidate in (root / "app", root / "src" / "app",
                      root / "apps" / "web" / "app", root / "apps" / "web" / "src" / "app"):
        if candidate.is_dir():
            return candidate
    return None


def public_pages(app: Path) -> list[Path]:
    """page.tsx files that are not obviously behind auth.

    `(app)`, `(dashboard)`, `(protected)` route groups and anything under an
    `admin`/`account` segment are treated as authenticated: a sitemap SHOULD omit
    them, so reporting them would be the false positive that kills the report.
    """
    private = re.compile(r"/\((app|dashboard|protected|private|auth)\)/|/(admin|account|settings)/")
    out = []
    for p in app.rglob("page.tsx"):
        rel = "/" + str(p.relative_to(app))
        if private.search(rel):
            continue
        out.append(p)
    return sorted(out)


def route_of(app: Path, page: Path) -> str:
    parts = [s for s in page.relative_to(app).parent.parts if not (s.startswith("(") and s.endswith(")"))]
    return "/" + "/".join(parts)


# Segments that name a page built for the team, not for a customer. Matched whole,
# never as substrings: `/developers` is not `/dev` and `/testimonials` is not `/test`.
INTERNAL_SEGMENTS = frozenset((
    "showcase", "styleguide", "style-guide", "design-system", "kitchen-sink",
    "playground", "sandbox", "debug", "internal", "dev", "test", "preview",
))


def _braced(text: str, start: int) -> str:
    """The `{ … }` block that opens at or after `start`, brace-matched."""
    i = text.find("{", start)
    if i < 0:
        return ""
    depth = 0
    for j in range(i, len(text)):
        if text[j] == "{":
            depth += 1
        elif text[j] == "}":
            depth -= 1
            if depth == 0:
                return text[i + 1:j]
    return ""


def _literal_arrays(text: str) -> list[str]:
    """Strings inside module-level `const NAME = [ … ]` declarations."""
    out: list[str] = []
    for arr in re.findall(r"\bconst\s+\w+\s*(?::[^=]+)?=\s*\[([^\]]*)\]", text):
        out += re.findall(r"[\"\'`]([A-Za-z0-9_-]+)[\"\'`]", arr)
    return out


def _resolve_import(spec: str, here: Path, alias_base: Path | None) -> Path | None:
    """A local module specifier as a file. Package imports resolve to None."""
    if spec.startswith("."):
        base = (here / spec).resolve()
    elif spec.startswith("@/") and alias_base is not None:
        base = (alias_base / spec[2:]).resolve()
    else:
        return None  # node_modules — not ours to read
    for cand in (base.with_suffix(".ts"), base.with_suffix(".tsx"),
                 base / "index.ts", base / "index.tsx"):
        if cand.is_file():
            return cand
    return None


def static_params(page: Path, alias_base: Path | None = None) -> list[str]:
    """The literal slugs a dynamic segment is pre-rendered with.

    `legal/[page]` is not an unknown when the page ships `generateStaticParams`:
    the slugs are a module-level array. Annotix put its privacy notice and its
    terms behind exactly that, and this scanner — matching route strings
    literally — called both missing. The two most alarming findings it can
    produce, both false, from one unread `const PAGES = [...]`.

    The list then moved to `lib/legal-pages.ts`, so the route and the sitemap
    could not drift apart, and both findings came straight back. So this follows
    **one** import hop: local modules only, and only those whose imported binding
    is actually used inside the `generateStaticParams` body — otherwise every
    unrelated array in every imported file would widen the vocabulary and turn a
    missing privacy page into a silent pass.

    Returns [] when the values are not literal (fetched, computed, two hops away).
    The caller then leaves the segment dynamic rather than guessing — a slug this
    cannot see is a slug it must not claim exists.
    """
    text = page.read_text(encoding="utf-8", errors="ignore")
    if "generateStaticParams" not in text:
        return []
    out = _literal_arrays(text)
    if out:
        return sorted(set(out))

    body = _braced(text, text.index("generateStaticParams"))
    for names, spec in re.findall(r"import\s+(?:type\s+)?\{([^}]*)\}\s*from\s*[\"\']([^\"\']+)[\"\']",
                                  text):
        bound = [n.split(" as ")[-1].strip() for n in names.split(",") if n.strip()]
        if not any(re.search(rf"\b{re.escape(n)}\b", body) for n in bound if n):
            continue
        target = _resolve_import(spec, page.parent, alias_base)
        if target is not None:
            out += _literal_arrays(target.read_text(encoding="utf-8", errors="ignore"))
    return sorted(set(out))


def _chain(page: Path, app: Path) -> list[Path]:
    """The page and every layout above it, up to and including app/.

    Path comparison is lexicographic, not ancestry — `d >= app` silently excluded
    every layout and made the scanner report a missing title on a page that
    inherits one. Caught by the test.
    """
    chain: list[Path] = [page]
    d = page.parent
    while True:
        chain.append(d / "layout.tsx")
        if d == app:
            break
        d = d.parent
    return chain


def chain_text(page: Path, app: Path) -> str:
    """Everything Next would consult to resolve this route's metadata."""
    return "\n".join(f.read_text(encoding="utf-8", errors="ignore")
                     for f in _chain(page, app) if f.is_file())


def _metadata_object(text: str) -> str | None:
    """The body of `export const metadata = { … }`, brace-matched.

    A regex ending in `\\n}` only matches a multi-line object, so a perfectly normal
    one-liner — `export const metadata = { title: 'Acme' }` — read as no metadata at
    all, and the scanner reported a missing title on a page that has one. Count the
    braces instead.
    """
    m = re.search(r"export\s+const\s+metadata\b[^=]*=\s*\{", text)
    if not m:
        return None
    depth, start = 0, m.end() - 1
    for i in range(start, len(text)):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                return text[start + 1:i]
    return None


def has_metadata(page: Path, app: Path, key: str) -> bool:
    """`key` ('title' | 'description') supplied by the page or any layout above it.

    Next resolves metadata up the segment tree, so a page without an export is not
    a page without a title — checking only the page produces a wrong finding on
    every well-built docs section.
    """
    for f in _chain(page, app):
        if not f.is_file():
            continue
        text = f.read_text(encoding="utf-8", errors="ignore")
        if "generateMetadata" in text:
            return True
        body = _metadata_object(text)
        if body and re.search(rf"\b{key}\s*:", body):
            return True
    return False


def scan(root: Path) -> list[Finding]:
    app = app_dir(root)
    if app is None:
        return [Finding("app-directory", UNKNOWN,
                        "no Next app/ directory found — is this a Next.js App Router project?")]
    found: list[Finding] = []
    pages = public_pages(app)
    src = app.parent

    # --- findable ---------------------------------------------------------
    for key, check in (("title", "route-title-missing"), ("description", "route-description-missing")):
        bad = [route_of(app, p) for p in pages if not has_metadata(p, app, key)]
        found.append(Finding(check, MISS if bad else OK,
                             f"{len(bad)} public route(s) with no {key} in their metadata chain"
                             if bad else f"every public route resolves a {key}",
                             bad[:10], "screenshot-to-page" if bad else None))

    robots = next((p for p in (app / "robots.ts", app / "robots.txt", src / "public" / "robots.txt")
                   if p.is_file()), None)
    robots_text = robots.read_text(encoding="utf-8", errors="ignore") if robots else ""
    if robots is None:
        found.append(Finding("robots-missing", MISS, "no robots.ts or public/robots.txt", [],
                             "screenshot-to-page"))
    else:
        text = robots_text
        blocks = re.search(r'disallow\s*[:=]\s*["\']?/["\']?\s*$', text, re.I | re.M) or \
                 re.search(r'disallow:\s*\[?\s*["\']/["\']\s*\]?', text, re.I)
        env_gated = bool(re.search(r"NODE_ENV|VERCEL_ENV", text))
        found.append(Finding(
            "robots-blocks-everything",
            MISS if (blocks and not env_gated) else (UNKNOWN if blocks else OK),
            "robots disallows everything and nothing branches on the environment — "
            "this is the launch failure that looks like nothing is wrong"
            if (blocks and not env_gated) else
            "robots disallows everything but branches on the environment — read it" if blocks else
            "robots does not blanket-disallow",
            [str(robots.relative_to(root))]))

    sitemap = next((p for p in (app / "sitemap.ts", src / "public" / "sitemap.xml") if p.is_file()), None)
    if sitemap is None:
        found.append(Finding("sitemap-missing", MISS, "no sitemap.ts or public/sitemap.xml", [],
                             "screenshot-to-page"))
    else:
        text = sitemap.read_text(encoding="utf-8", errors="ignore")
        dynamic = bool(re.search(r"\.map\(|await |for\s*\(", text))
        listed = [route_of(app, p) for p in pages
                  if route_of(app, p) != "/" and route_of(app, p) not in text]
        found.append(Finding(
            "sitemap-missing-routes",
            UNKNOWN if dynamic else (MISS if listed else OK),
            "the sitemap is built dynamically — read it rather than trusting this check"
            if dynamic else
            (f"{len(listed)} public route(s) not named in the sitemap" if listed
             else "every public route appears in the sitemap"),
            listed[:10], "screenshot-to-page" if (listed and not dynamic) else None))

    # The mirror of sitemap-missing-routes: a route that should NOT be found, and is.
    # Annotix shipped /showcase — the living reference for its DESIGN.md — as a public
    # 200 with no noindex, reachable by any crawler. Nothing else here looks for that,
    # because every other check asks whether a page can be found.
    internal = []
    for page in pages:
        route = route_of(app, page)
        segs = [x.lower() for x in route.strip("/").split("/") if x]
        hits = [x for x in segs if x in INTERNAL_SEGMENTS]
        if not hits:
            continue
        if any(x in robots_text.lower() for x in hits):
            continue  # named in robots — somebody already thought about it
        if re.search(r"noindex|index\s*:\s*false", chain_text(page, app), re.I):
            continue
        internal.append(route)
    found.append(Finding("internal-route-indexable", MISS if internal else OK,
                         f"{len(internal)} route(s) named for the team are public, not in robots "
                         "and not noindex" if internal
                         else "no internal-looking route is left publicly indexable",
                         internal[:10], "screenshot-to-page" if internal else None))

    icons = [n for n in ("icon.tsx", "icon.png", "icon.svg", "favicon.ico") if (app / n).is_file()]
    apple = [n for n in ("apple-icon.tsx", "apple-icon.png") if (app / n).is_file()]
    found.append(Finding("favicon-incomplete", OK if (icons and apple) else MISS,
                         f"icons: {icons or 'none'} · apple-icon: {apple or 'none'}", [],
                         None if (icons and apple) else "screenshot-to-page"))

    og = [p for p in app.rglob("opengraph-image.*")]
    found.append(Finding("social-preview", OK if og else MISS,
                         f"{len(og)} opengraph-image file(s)" if og
                         else "no opengraph-image — every share renders a grey box",
                         [str(p.relative_to(root)) for p in og[:5]],
                         None if og else "screenshot-to-page"))

    # --- trustworthy ------------------------------------------------------
    # A dynamic route serves the slugs it pre-renders: `/legal/[page]` over
    # ["privacy","terms",…] IS the privacy page. Matching the route string alone
    # reported both as missing on a project that had both. See static_params().
    vocabulary: dict[str, str] = {}
    for p in pages:
        r = route_of(app, p)
        slugs = static_params(p, src) if "[" in r else []
        label = f"{r} ({', '.join(slugs)})" if slugs else r
        vocabulary[label] = f"{r} {' '.join(slugs)}".lower()

    def route_like(*words: str) -> list[str]:
        return [label for label, hay in vocabulary.items() if any(w in hay for w in words)]

    for check, words, owner in (
        ("privacy-page-missing", ("privacy", "privacidad", "privacy-policy"), "screenshot-to-page"),
        ("terms-page-missing", ("terms", "termini", "conditions", "tos"), "screenshot-to-page"),
        ("identity-block-missing", ("legal", "imprint", "impressum", "chi-siamo", "about"), "the user"),
    ):
        hits = route_like(*words)
        found.append(Finding(check, OK if hits else MISS,
                             f"found: {', '.join(hits)}" if hits else "no such route",
                             hits, None if hits else owner))

    # --- convertible ------------------------------------------------------
    # A CTA above the fold is a RENDERED property. Saying "missing" from source
    # would be guessing, so this reports unknown and asks for a browser.
    found.append(Finding("cta-above-the-fold", UNKNOWN,
                         "above-the-fold is a rendered property — open the landing route at 1280px "
                         "and at 375px and look. This script will not guess."))

    # `<form\b` also matches `<form.Field` and `<form.Subscribe` — TanStack Form's
    # render-prop components — so every form PRIMITIVE in a form toolkit read as a
    # form with no success path. Require the tag to actually end.
    is_form = re.compile(r"<form(?=[\s/>])|useActionState|action=\{")
    # A success path is not only a toast. `router.push` after a sign-in and
    # `router.refresh` after an in-place settings save are both confirmations — and
    # on a settings form a confirmation *page* would be the wrong fix, so a scanner
    # that demands one is asking for a regression.
    has_success = re.compile(r"toast|redirect\(|router\.(push|replace|refresh)\(|"
                             r"success|thank|confirm", re.I)
    forms, silent = [], []
    for p in src.rglob("*.tsx"):
        if "node_modules" in str(p):
            continue
        text = p.read_text(encoding="utf-8", errors="ignore")
        if not is_form.search(text):
            continue
        forms.append(p)
        if not has_success.search(text):
            silent.append(str(p.relative_to(root)))
    found.append(Finding("form-without-confirmation", MISS if silent else OK,
                         f"{len(silent)} of {len(forms)} form file(s) show no success path"
                         if silent else f"all {len(forms)} form file(s) show a success path",
                         silent[:10], "forms" if silent else None))

    pkg = src / "package.json"
    deps = ""
    if pkg.is_file():
        deps = pkg.read_text(encoding="utf-8", errors="ignore")
    analytics = re.search(r"@vercel/analytics|posthog|plausible|umami|@segment|gtag|google-analytics",
                          deps, re.I)
    found.append(Finding("analytics-absent", OK if analytics else MISS,
                         f"found {analytics.group(0)}" if analytics
                         else "no analytics package in dependencies", [],
                         None if analytics else "module-add"))
    return found


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("project_root", type=Path)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    root = args.project_root.resolve()
    if not root.is_dir():
        print(f"not a directory: {root}", file=sys.stderr)
        return 2

    findings = scan(root)
    if args.json:
        print(json.dumps([f.__dict__ for f in findings], indent=2))
        return 0

    mark = {OK: "·", MISS: "!", UNKNOWN: "?"}
    print(f"launch signals for {root}\n")
    for f in findings:
        print(f"  {mark[f.status]} {f.check}: {f.detail}")
        for w in f.where:
            print(f"      {w}")
        if f.routed_to:
            print(f"      → {f.routed_to}")
    missing = sum(1 for f in findings if f.status == MISS)
    unknown = sum(1 for f in findings if f.status == UNKNOWN)
    print(f"\n{missing} to look at, {unknown} this script cannot answer.")
    print("Signals, not verdicts. references/checks.md says what a legitimate false positive "
          "looks like for each one — read the code before reporting any of them.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
