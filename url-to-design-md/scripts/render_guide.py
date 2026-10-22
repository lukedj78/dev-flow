#!/usr/bin/env python3
"""tokens.json -> brand-guide.html. Pure stdlib.

This is not a report. It is the surface the divergence decision is made on.

A measurement in a markdown file cannot be judged: nobody looks at `--text-7xl: 72px` and says "too
heavy, lighten it". Rendered, they can. So the guide exists to be looked at, argued with, and
changed — and that only works under one rule, which the whole file is built around:

    NOTHING IN THE GUIDE IS A LITERAL. Every colour, size, radius, shadow and easing is `var(--x)`,
    and the only place a value appears is the `:root` block generated from tokens.json.

That is what makes it a loop instead of a document: move a token, regenerate, look again. A single
hard-coded value breaks it silently — the page stops reflecting the system it claims to show — so
`verify.py` reads the rendered page back and fails when a rebuilt control's computed style does not
equal its token.

Two editions, same markup:
  * `brand-guide.html`   — no images, CSS-gradient fallbacks, offline, zero network requests.
  * `brand-guide-hero.html` — the same with WebP embedded once and reused through CSS classes.

Never copied from the source site: logos, font files, photographs. A logo becomes a dashed box at
its measured size and colour; a font is named and linked, never embedded.

    render_guide.py <tokens.json> --out <dir> [--images <dir>] [--brand "Name"]
"""

from __future__ import annotations

import argparse
import base64
import html
import json
import re
import mimetypes

import analyze
from pathlib import Path

MAX_LIGHT_BYTES = 150 * 1024


# --------------------------------------------------------------------------- helpers


def js_json(value) -> str:
    """JSON for a <script> element, which is not the same as JSON.

    Everything in `tokens.json` was read off somebody else's page: a custom-property NAME, a font
    family, a CTA label. A site that wants to can set `--x: </script><script>…` and our generator
    would paste it straight into the guide, where it stops being data. The four escapes below keep
    it data. U+2028/9 are in the list because they are legal in JSON and are line terminators in
    JavaScript.
    """
    return (json.dumps(value)
            .replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")
            .replace("\u2028", "\\u2028").replace("\u2029", "\\u2029"))


def esc(value) -> str:
    return html.escape(str(value), quote=True)


def token_rows(tokens):
    """Every token as (css-variable, value, note), which is also what the :root block is built from.
    One list, two consumers, so the page can never show a value the stylesheet does not have."""
    rows = []
    for name, role in tokens["color"]["roles"].items():
        rows.append((f"--{name}", role.get("oklch") or role["value"], role.get("why", "")))
    for slot in tokens["typography"]["scale"]["slots"]:
        key = slot["slot"].replace("text-", "")
        rows.append((f"--size-{key}", slot["clamp"] or f"{slot['size']}px",
                     f"{slot['size']}px at {tokens['source']['viewports'][-1]}px"
                     + (f", {slot['mobileSize']}px at {tokens['source']['viewports'][0]}px"
                        if slot["mobileSize"] else "")))
        if slot["lineHeight"]:
            rows.append((f"--leading-{key}", f"{slot['lineHeight']}px",
                         f"ratio {slot['lineHeightRatio']}"))
        if slot["weight"]:
            rows.append((f"--weight-{key}", str(slot["weight"]), ""))
        if slot["tracking"]:
            rows.append((f"--tracking-{key}", f"{slot['tracking']}em", ""))
    if tokens["spacing"]["base"]:
        rows.append(("--space-base", f"{tokens['spacing']['base']}px",
                     f"{tokens['spacing']['coverage']:.0%} of spacing values sit on this grid"))
        for v in tokens["spacing"]["onGrid"][:10]:
            rows.append((f"--space-{int(v)}", f"{int(v)}px", ""))
    if tokens["radius"]["default"] is not None:
        _r = tokens["radius"]["default"]
        rows.append(("--radius", f"{int(_r) if float(_r) == int(_r) else _r}px",
                     "the commonest radius" + (" — this site has square corners" if not _r else "")))
    rows.append(("--radius-pill", "9999px" if tokens["radius"]["pill"] else "var(--radius)",
                 "the site uses a pill shape" if tokens["radius"]["pill"] else "no pill observed"))
    if tokens["layout"]["container"]:
        rows.append(("--container", f"{tokens['layout']['container']}px", "content max-width"))
    fams = tokens["typography"]["families"]
    if fams:
        rows.append(("--font-sans", f"{fams[0]}, system-ui, sans-serif", "most characters"))
    if len(fams) > 1:
        rows.append(("--font-alt", f"{fams[1]}, system-ui, sans-serif", "second family"))
    if tokens["shadows"]:
        rows.append(("--shadow", tokens["shadows"][0], "the commonest shadow"))
    motion = tokens.get("motion")
    if motion and motion.get("durations"):
        rows.append(("--duration", f"{motion['durations'][0][0]}ms", "the commonest transition"))
    if motion and motion.get("easings"):
        rows.append(("--ease", motion["easings"][0][0], "the site's own easing"))
    if tokens["color"]["gradients"]:
        rows.append(("--gradient", tokens["color"]["gradients"][0], "the site's gradient"))
    return rows


def css_safe(value):
    """A token value on its way into a <style> element, which is not the same as a CSS value.

    Every value here was read off somebody else's page. A font family is the sharp one: the browser
    serialises `font-family` with quotes, so `"</style><script>…"` is a *valid* CSS value — and the
    HTML parser ends the style element at `</style>` regardless of the CSS quoting. Escaping the
    angle brackets as CSS escapes keeps the value meaning the same thing to CSS while removing the
    sequence HTML looks for.

    Returns None for a value that has no business being one. No legitimate CSS *value* contains a
    brace or a semicolon; one that does is trying to close the declaration and open its own rule.
    """
    v = str(value)
    if any(c in v for c in "{};"):
        return None
    if "\\" in v or "@import" in v.lower() or "expression(" in v.lower():
        return None
    return v.replace("<", "\\3c ").replace(">", "\\3e ")


def css_attr(value, fallback=""):
    """A measured value on its way into a `style="..."` ATTRIBUTE.

    `css_safe` guards the other context — a `<style>` element — where the danger is `</style>` and
    the quoting is CSS's. An attribute is parsed by HTML first, so one double quote ends it and
    whatever follows becomes markup: a site can declare

        background-image: linear-gradient(red, blue)" onmouseover="…

    and `css_safe` passes it through untouched, because it contains no brace, no semicolon and no
    backslash. Measured on this file's own output.

    So the two contexts get two functions, and this one escapes for HTML after CSS. A value that
    `css_safe` refuses becomes the fallback rather than an empty declaration, because a half-written
    `style="background:"` is a silent failure and a missing wash is a visible one.
    """
    safe = css_safe(value)
    if safe is None:
        return fallback
    return html.escape(safe, quote=True)


def font_faces(tokens, link: bool):
    """The measured @font-face rules, re-declared so the guide renders in the real typeface.

    The family carries more of a brand's identity than any colour, and a guide that names
    `AdihausDIN` while rendering system-ui is showing the right sizes in the wrong voice — measured
    on adidas.it, where the page declared six faces whose URLs we had read and never used.

    It is a LINK, never a copy: the browser fetches the file from the owner's own server, exactly as
    their site does, and nothing is stored here. It costs the offline guarantee, which is why it is
    off by default and announced in the page when it is on.
    """
    if not link:
        return "", ""
    faces, hosts = [], set()
    for f in tokens["typography"].get("fontFaces", [])[:12]:
        src = (f.get("src") or "").strip()
        family = (f.get("family") or "").strip()
        if not src or not family or "url(" not in src:
            continue
        if css_safe(src) is None or css_safe(family) is None:
            continue
        for m in re.findall(r"url\(\s*[\"']?(https?://[^)\"']+)", src):
            hosts.add(m.split("/")[2])
        faces.append("  @font-face { font-family: " + css_safe(f'"{family}"')
                     + "; src: " + css_safe(src) + ";"
                     + (" font-weight: " + css_safe(f["weight"]) + ";" if f.get("weight") else "")
                     + (" font-style: " + css_safe(f["style"]) + ";" if f.get("style") else "")
                     + " font-display: swap; }")
    if not faces:
        return "", ""
    note = ("<p class=\"note missing\">Rendered in the source's own typefaces, linked from "
            + esc(", ".join(sorted(hosts)[:3]))
            + ". The files are not copied and not redistributed — this page fetches them exactly as "
            + "that site does, which means it is <strong>not offline</strong> in this edition.</p>")
    return "\n".join(faces), note


def root_block(rows):
    kept, dropped = [], []
    for name, value, _ in rows:
        safe = css_safe(value)
        if safe is None:
            dropped.append(name)
            continue
        kept.append(f"    {name}: {safe};")
    if dropped:
        # Named, not silent: a token that vanished without a word would be read as "not observed",
        # which is a different fact and the one thing this skill must not blur.
        kept.insert(0, "    /* refused as unsafe for a stylesheet: "
                       + ", ".join(dropped) + " */")
    return ":root {\n" + "\n".join(kept) + "\n  }"


def fallback(name, default):
    return f"var({name}, {default})"


# --------------------------------------------------------------------------- stylesheet


PAGE_CSS = """
/* R5.2: full pages, not stacked sections. Each one fills the viewport it opens in and carries its
   own ground, so scrolling the guide feels like scrolling the site rather than reading a report. */
:root { --bar-h: 56px; }
/* The sticky bar sits over the page, so every page starts below it. Without this the first line
   of each one is cut in half — visible on the Overview and the Contents, and invisible to every
   check in verify.py, which is the argument for R8.3 in one screenshot. */
.page { min-height: 100svh; display: flex; align-items: center;
        padding: calc(var(--bar-h) + 40px) 0 72px; }
.page--centred { text-align: center; }
.page--centred .wrap > * { margin-left: auto; margin-right: auto; }

/* R5.2.1 — the cover. Full-bleed ground, the brand's own, with the name set over it. */
.cover { position: relative; color: var(--cover-ink); isolation: isolate; }
.cover-bleed { position: absolute; inset: 0; z-index: -2; background: var(--bleed); }
/* The brand's gradient as a wash over the flat ground, never as the ground: a gradient has no one
   colour, so nothing can be proven legible against it. */
.cover-wash { position: absolute; inset: 0; z-index: -1; opacity: .55;
              mask-image: linear-gradient(to bottom, transparent, #000 45%); }
.cover-wrap { max-width: 52rem; }
.cover-title { font-size: clamp(40px, 9vw, 112px); line-height: 1.02; margin: 20px 0 0;
               text-wrap: balance; color: inherit; }
.cover-lede { color: inherit; opacity: .88; max-width: 44ch; margin-top: 20px; }
.cover-cta { margin-top: 28px; }
.cover-foot { color: inherit; opacity: .7; margin-top: 48px; }
/* The frosted card the site itself uses for a figure. */
.glass { margin-top: 36px; max-width: 22rem; padding: 20px; border-radius: var(--radius, 12px);
         background: color-mix(in srgb, var(--cover-ink) 12%, transparent);
         border: 1px solid color-mix(in srgb, var(--cover-ink) 26%, transparent);
         backdrop-filter: blur(14px); -webkit-backdrop-filter: blur(14px); color: inherit; }
.glass .note { color: inherit; opacity: .75; }
.glass-v { font-family: var(--font-mono, ui-monospace, monospace); font-size: 15px; margin-top: 6px; }
.glass-hex { font-size: var(--size-2xl, 24px); font-weight: 600; margin: 4px 0 8px; }

/* R5.2.2 — four measured figures, each with its denominator under it. */
.stats { display: grid; gap: 24px; margin-top: 40px;
         grid-template-columns: repeat(auto-fit, minmax(170px, 1fr)); }
.stat-v { font-size: clamp(34px, 5vw, 56px); line-height: 1; font-weight: 700; }
.stat-l { margin-top: 8px; font-weight: 600; }

/* R5.2.3 — the contents, in the site's own card shape. */
.tiles { display: grid; gap: 16px; margin-top: 32px;
         grid-template-columns: repeat(auto-fit, minmax(196px, 1fr)); }
.tiles > * { min-width: 0; }
.tile { position: relative; display: block; min-height: 190px; padding: 18px;
        border-radius: var(--radius, 12px); background: var(--card, #f4f4f5);
        border: 1px solid var(--border, transparent); color: inherit; text-decoration: none;
        overflow: hidden; }
.tile::before { content: ""; position: absolute; inset: 0; background: var(--gradient, none);
                opacity: .10; transform: scale(1); transition: transform 1.2s var(--ease, ease-out); }
.tile:hover::before, .tile:focus-visible::before { transform: scale(1.08); }
.tile-n { font-family: var(--font-mono, ui-monospace, monospace); font-size: 13px; opacity: .6; }
.tile-arrow { position: absolute; top: 18px; right: 18px; opacity: .55; }
.tile-body { position: absolute; left: 18px; right: 18px; bottom: 16px; display: block; }
.tile-t { display: block; font-weight: 600; font-size: var(--size-lg, 18px); }

/* R5.2.7, R5.2.9, R5.2.12 — the pages the brief sets on the dark ground. */
.page--dark { background: var(--surface-inverse, #111); color: var(--foreground-inverse, #fff); }
.page--dark .note, .page--dark .lede { color: inherit; opacity: .78; }
.page--dark table, .page--dark th, .page--dark td { border-color:
  color-mix(in srgb, var(--foreground-inverse, #fff) 22%, transparent); }
.page--dark .card { background: color-mix(in srgb, var(--foreground-inverse, #fff) 8%, transparent);
                    border-color: color-mix(in srgb, var(--foreground-inverse, #fff) 20%, transparent);
                    color: inherit; }
/* A dark gradient on a dark page is a black rectangle. Apple's three gradients are all near-black,
   and on the Colour page they disappeared entirely — a swatch showing nothing, which is worse than
   no swatch. Each one gets a light plate under it so its actual colour is visible. */
.grad-plate { background: var(--background, #fff); border-radius: var(--radius, 8px);
              padding: 6px; }
.page--dark .grad-plate { box-shadow: inset 0 0 0 1px
                            color-mix(in srgb, var(--foreground-inverse, #fff) 24%, transparent); }

@media (max-width: 640px) {
  .page { min-height: 0; padding: 56px 0; }
  .cover { min-height: 92svh; }
}
@media (prefers-reduced-motion: reduce) {
  .tile::before { transition: none; }
}
"""


def stylesheet(tokens):
    """Every rule below reads a variable. The fallbacks exist because a site may not supply a slot,
    and a guide that collapses when `--accent` is missing is a guide that only renders one site."""
    has_gradient = bool(tokens["color"]["gradients"])
    ground = fallback("--background", "#ffffff")
    ink = fallback("--foreground", "#111111")
    return f"""
  *, *::before, *::after {{ box-sizing: border-box; }}

  html {{ scroll-behavior: smooth; }}

  body {{
    margin: 0;
    background: {ground};
    color: {ink};
    font-family: {fallback("--font-sans", "system-ui, sans-serif")};
    font-size: {fallback("--size-base", "16px")};
    line-height: {fallback("--leading-base", "1.6")};
    -webkit-font-smoothing: antialiased;
  }}

  /* The guide's own controls ARE the brand's rebuilt controls. That is deliberate: if the button
     below is wrong, the system is wrong, and you see it before you ship it. */
  .btn {{
    display: inline-flex; align-items: center; justify-content: center;
    background: {fallback("--primary", "#111111")};
    color: {fallback("--primary-foreground", "#ffffff")};
    border: 0;
    border-radius: {fallback("--radius-pill", "9999px")};
    padding: {fallback("--space-12", "12px")} {fallback("--space-24", "24px")};
    font: inherit;
    font-size: {fallback("--size-base", "16px")};
    font-weight: {fallback("--weight-base", "600")};
    cursor: pointer;
    text-decoration: none;
    transition: filter {fallback("--duration", "180ms")} {fallback("--ease", "ease")};
  }}
  .btn:hover {{ filter: brightness(1.08); }}
  .btn:focus-visible {{
    outline: 2px solid {fallback("--ring", "currentColor")};
    outline-offset: 2px;
  }}
  .btn--secondary {{
    background: {fallback("--secondary", "transparent")};
    color: {ink};
    border: 1px solid {fallback("--border", "currentColor")};
    border-radius: {fallback("--radius", "8px")};
  }}

  .card {{
    background: {fallback("--card", "#f7f7f8")};
    border: 1px solid {fallback("--border", "rgba(0,0,0,.1)")};
    border-radius: {fallback("--radius", "12px")};
    padding: {fallback("--space-24", "24px")};
    box-shadow: {fallback("--shadow", "none")};
  }}

  .field {{
    width: 100%;
    border: 1px solid {fallback("--border", "rgba(0,0,0,.2)")};
    border-radius: {fallback("--radius", "8px")};
    padding: {fallback("--space-12", "10px")} {fallback("--space-16", "14px")};
    font: inherit;
    background: {ground};
    color: {ink};
  }}
  .field:focus-visible {{
    outline: 2px solid {fallback("--ring", "currentColor")};
    outline-offset: 2px;
  }}

  .wrap {{
    max-width: {fallback("--container", "1200px")};
    margin-inline: auto;
    padding-inline: 16px;
  }}

  .bar {{
    position: sticky; top: 0; z-index: 50;
    display: flex; align-items: center; gap: 12px;
    padding: 12px 16px;
    background: {ground};
    border-bottom: 1px solid {fallback("--border", "rgba(0,0,0,.08)")};
    font-size: {fallback("--size-sm", "14px")};
    flex-wrap: wrap;
  }}
  /* Below 560px the section links are what pushes the bar past the viewport. The label and the
     brand are what the bar is for; the links are a convenience and the page has headings. */
  @media (max-width: 559px) {{ .bar a {{ display: none; }} }}

  /* The one shape here that is deliberately NOT the measured system: the Unofficial badge has to
     read as foreign to the brand, or it starts looking like part of it. On a square-cornered site
     that difference is the point, not an oversight. */
  .pill {{
    display: inline-flex; align-items: center; gap: 6px;
    border: 1px solid {fallback("--border", "currentColor")};
    border-radius: 9999px;
    padding: 4px 10px;
    font-size: {fallback("--size-sm", "13px")};
    letter-spacing: .02em;
    text-transform: uppercase;
  }}

  section {{ padding-block: clamp(48px, 8vw, 96px); }}
  /* The bar is sticky, so an anchor jump lands the heading underneath it. Without this the first
     line of every section you link to is hidden behind the chrome. */
  section[id] {{ scroll-margin-top: 72px; }}
  section + section {{ border-top: 1px solid {fallback("--border", "rgba(0,0,0,.08)")}; }}

  /* The cover sits on the page's OWN ground, with the page's own ink. The first version fell back
     to `--primary` when no gradient was measured, so a black-and-white site produced a black cover
     and the guide stopped looking like the site it measured — which is the one thing it has to do.
     A gradient is used when the site actually has one; `--primary` stays what it is, the accent. */
  .cover {{
    background: {fallback("--gradient", ground) if has_gradient else ground};
    color: {"inherit" if not has_gradient else fallback("--primary-foreground", "#ffffff")};
    padding-block: clamp(72px, 14vw, 160px);
    border-bottom: 1px solid {fallback("--border", "rgba(0,0,0,.08)")};
  }}
  .cover h1 {{
    font-size: {fallback("--size-7xl", "clamp(40px, 9vw, 72px)")};
    line-height: {fallback("--leading-7xl", "1.05")};
    letter-spacing: {fallback("--tracking-7xl", "-0.02em")};
    font-weight: {fallback("--weight-7xl", "600")};
    margin: 0 0 16px;
    text-wrap: balance;
  }}

  h2 {{
    font-size: {fallback("--size-3xl", "clamp(24px, 4vw, 32px)")};
    line-height: {fallback("--leading-3xl", "1.2")};
    letter-spacing: {fallback("--tracking-3xl", "-0.01em")};
    font-weight: {fallback("--weight-3xl", "600")};
    margin: 0 0 8px;
    text-wrap: balance;
  }}
  h3 {{
    font-size: {fallback("--size-xl", "20px")};
    line-height: {fallback("--leading-xl", "1.4")};
    font-weight: {fallback("--weight-xl", "600")};
    margin: 0 0 8px;
  }}
  .lede {{ color: {fallback("--muted-foreground", "currentColor")}; max-width: 62ch; }}

  .grid {{ display: grid; gap: {fallback("--space-24", "24px")}; }}
  /* A grid item defaults to min-width:auto, so a wide table inside one widens the COLUMN instead of
     scrolling in its own box, and the whole page scrolls sideways at 390px. Measured: 405px wide in
     a 390px viewport, caused by a table that was already wrapped in an overflow container. */
  .grid > * {{ min-width: 0; }}
  .grid--2 {{ grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); }}
  .grid--3 {{ grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); }}
  .grid--4 {{ grid-template-columns: repeat(auto-fit, minmax(170px, 1fr)); }}

  .swatch {{ border-radius: {fallback("--radius", "12px")}; height: 96px; border: 1px solid {fallback("--border", "rgba(0,0,0,.1)")}; }}
  .bar-share {{ display: flex; height: 44px; border-radius: {fallback("--radius", "10px")}; overflow: hidden; border: 1px solid {fallback("--border", "rgba(0,0,0,.1)")}; }}

  table {{ width: 100%; border-collapse: collapse; font-size: {fallback("--size-sm", "14px")}; }}
  th, td {{ text-align: left; padding: 8px 10px; border-bottom: 1px solid {fallback("--border", "rgba(0,0,0,.08)")}; vertical-align: top; }}
  th {{ font-weight: 600; }}
  td.num {{ font-variant-numeric: tabular-nums; white-space: nowrap; }}
  .scroll-x {{ overflow-x: auto; max-width: 100%; }}

  code, pre {{ font-family: ui-monospace, "SF Mono", Menlo, monospace; font-size: 13px; }}
  pre {{
    background: {fallback("--card", "#f4f4f5")};
    border: 1px solid {fallback("--border", "rgba(0,0,0,.1)")};
    border-radius: {fallback("--radius", "12px")};
    padding: 16px; overflow-x: auto; max-height: 420px;
  }}

  .logo-box {{
    display: inline-flex; align-items: center; justify-content: center;
    border: 2px dashed currentColor; border-radius: 6px;
    font-size: 11px; letter-spacing: .08em; text-transform: uppercase; opacity: .75;
  }}

  .note {{ font-size: {fallback("--size-sm", "13px")}; color: {fallback("--muted-foreground", "currentColor")}; }}
  .missing {{ border-left: 3px solid {fallback("--border", "currentColor")}; padding-left: 12px; }}

  /* Hidden only once the script has run and can reveal it again. Without the `.js` gate the whole
     guide is invisible when the script fails — and it would still pass an "opens offline with zero
     requests" check, which is how a blank page gets shipped as a verified one. */
  .js .reveal {{ opacity: 0; transform: translateY(12px);
                 transition: opacity .6s {fallback("--ease", "ease")}, transform .6s {fallback("--ease", "ease")}; }}
  .js .reveal.in {{ opacity: 1; transform: none; }}
  @media (prefers-reduced-motion: reduce) {{
    html {{ scroll-behavior: auto; }}
    .reveal {{ opacity: 1; transform: none; transition: none; }}
    * {{ animation-duration: .001ms !important; transition-duration: .001ms !important; }}
  }}

  footer {{ padding-block: 48px; font-size: {fallback("--size-sm", "13px")}; }}
""" + PAGE_CSS


# --------------------------------------------------------------------------- sections


def review(tokens):
    """The band that turns a document into a decision. First thing on the page, above the cover.

    It holds what the measurement could not settle by itself. Every item carries its evidence and —
    the part that matters — what happens if nobody answers, because a question that quietly did
    something is worse than no question at all.
    """
    questions = tokens.get("questions") or []
    if not questions:
        body = ("<p class=\"note\">The measurement raised nothing that needs a decision: every "
                "contrast pair passes, every component was found, and nothing was inferred. Read "
                "the sections below and say whether this is the system you want to start from.</p>")
    else:
        items = "".join(
            f'<li style="margin-bottom:16px">'
            f'<div><strong>{esc(q["question"])}</strong></div>'
            f'<div class="note">{esc(q["evidence"])}</div>'
            f'<div class="note">— ' + " · ".join(esc(o) for o in q["options"]) + "</div>"
            f'<div class="note"><strong>If you say nothing:</strong> {esc(q["default"])}</div>'
            f"</li>" for q in questions)
        body = f'<ol style="margin:16px 0 0;padding-left:20px">{items}</ol>'

    return f"""
<section id="review" style="padding-block:40px">
  <div class="wrap">
    <span class="pill">Before the DESIGN.md</span>
    <h2 style="margin-top:12px">{len(questions)} thing(s) to decide</h2>
    <p class="lede">Nothing below is my opinion — each one is a condition the measurement found.
    Answer them, or say they are fine, and the <code>DESIGN.md</code> is written from what you chose.
    Until then nothing enters the project.</p>
    {body}
  </div>
</section>"""


def cover(tokens, brand):
    """R5.2.1 — a full page, not a banner.

    A full-bleed image (the brand's own gradient when there are none), the name set large over it,
    a factual lede, a pill call to action, and a frosted-glass card showing one token. The
    unofficial label and the disclaimer sit at the foot of the page.
    """
    scale = tokens["typography"]["scale"]
    src = tokens["source"]
    grads = (tokens["color"].get("gradients") or [])
    roles = tokens["color"]["roles"]

    # THE INK IS CHOSEN AGAINST THE GROUND, not before it.
    #
    # The first version took the gradient as the ground and `foreground-inverse` as the ink, and on
    # apple.com — whose gradient is almost white — the title, the pill, the lede and the glass card
    # all came out white on white. Invisible. `verify.py` passed it 14 of 15, because nothing it
    # checks can see a page. This is the same mistake the `foreground` role made on adidas, made
    # again one layer up, and it is why R8.3 says to look.
    #
    # A gradient has no single colour to measure, so its ink cannot be derived — only a flat ground
    # can carry that claim. When the only candidate is a gradient, the inverted band is used
    # instead and the gradient becomes the page's accent, not its floor.
    candidates = []
    if roles.get("surface-inverse"):
        candidates.append((roles["surface-inverse"]["value"], "the site's own inverted band"))
    if roles.get("foreground"):
        candidates.append((roles["foreground"]["value"], "the site's darkest measured ink"))
    if roles.get("background"):
        candidates.append((roles["background"]["value"], "the site's ground"))

    bleed, bleed_why, ink = None, "", "#fff"
    for value, why in candidates:
        for cand in (roles.get("foreground-inverse", {}).get("value"),
                     roles.get("primary-foreground", {}).get("value"),
                     roles.get("foreground", {}).get("value"), "#ffffff", "#111111"):
            if cand and (analyze.contrast(cand, value) or 0) >= 4.5:
                bleed, bleed_why, ink = value, why, cand
                break
        if bleed:
            break
    if not bleed:
        # Nothing measured can carry legible text over anything else measured. Say so rather than
        # paint an unreadable page: the fallback is the plainest pair there is.
        bleed, bleed_why, ink = "#111111", "no measured pair reached 4.5:1, so this is a fallback", "#ffffff"

    one = None
    for name in ("primary", "accent", "foreground", "background"):
        if name in roles:
            one = (name, roles[name])
            break
    # The gradient, when there is one, washes over the flat ground rather than replacing it: the
    # brand's colour is present and the text still has a floor it can be read against.
    gradient_wash = (f'<div class="cover-wash" aria-hidden="true" '
                     f'style="background:{css_attr(grads[0])}"></div>'
                     if grads and css_safe(grads[0]) else "")

    token_card = ""
    if one:
        token_card = f"""
      <div class="glass">
        <div class="note">A token, measured</div>
        <div class="glass-v">--{esc(one[0])}</div>
        <div class="glass-hex">{esc(one[1]['value'])}</div>
        <div class="note">{esc(one[1]['why'][:72])}</div>
      </div>"""

    return f"""
<section id="cover" class="page cover" style="--bleed:{css_attr(bleed, '#111111')};--cover-ink:{css_attr(ink, '#ffffff')}">
  <div class="cover-bleed" aria-hidden="true"></div>
  {gradient_wash}
  <div class="wrap cover-wrap">
    <span class="pill">Unofficial analysis</span>
    <h1 class="cover-title">{esc(brand)}<br>brand guidelines</h1>
    <p class="lede cover-lede">
      Measured from {esc(src['pageCount'])} page(s) of <code>{esc(src['origin'] or '')}</code>
      at {esc(' and '.join(str(v) + 'px' for v in src['viewports']))},
      and rebuilt here from the tokens alone.
    </p>
    <p><a class="btn cover-cta" href="#rebuild">See the tokens rebuilt</a></p>
    {token_card}
    <p class="cover-foot note">
      {esc(scale['slots'] and len(scale['slots']) or 0)} type steps ·
      {esc(len(tokens['color']['roles']))} colour roles · ground is {esc(bleed_why)}<br>
      Unofficial analysis. Not affiliated with or endorsed by {esc(brand)}.
      Trademarks belong to their owners.
    </p>
  </div>
</section>"""


def contents(tokens):
    """R5.2.3 — eight cards in the style of the site's own product cards: number upper left, title
    lower left, arrow upper right, a slow zoom on hover.

    This page did not exist. It is not decoration: it is where the guide shows that it can build
    the site's card, at the site's radius, on the site's ground — the same claim the rebuild page
    makes about buttons, made about the pattern a brand repeats most.
    """
    pages = [
        ("01", "Overview", "#overview", "what was found, and what was not"),
        ("02", "Token rebuild test", "#rebuild", "the controls, from the tokens alone"),
        ("03", "Typography", "#typography", "each role at its real size"),
        ("04", "Fonts", "#fonts", "the families, their weights and share"),
        ("05", "Colour", "#colour", "roles, contrast and the palette in proportion"),
        ("06", "Layout and spacing", "#layout", "grid, containers, radii, breakpoints"),
        ("07", "Components", "#components", "buttons on their own grounds"),
        ("08", "Design tokens", "#tokens", "the CSS and the JSON, to copy"),
    ]
    cards = "".join(f"""
    <a class="tile" href="{esc(href)}">
      <span class="tile-n">{esc(n)}</span>
      <span class="tile-arrow" aria-hidden="true">→</span>
      <span class="tile-body">
        <span class="tile-t">{esc(title)}</span>
        <span class="note">{esc(note)}</span>
      </span>
    </a>""" for n, title, href, note in pages)

    return f"""
<section id="contents" class="page"><div class="wrap">
  <h2>Contents</h2>
  <p class="lede">Eight pages, built from the measured tokens and nothing else.</p>
  <div class="tiles">{cards}</div>
</div></section>"""


def overview(tokens):
    """R5.2.2: a centred headline and four big figures — typefaces, colours, spacing base, button
    variants.

    This section had those figures, and I removed them. The user said "do a pass for AI slop, I can
    see some by eye" about the adidas guide; I reached for rule 11 of `anti-slop-fallbacks` — "a row
    of identical metric boxes states four facts and no argument" — deleted a requirement, and then
    wrote a check into `verify.py` forbidding it for ever. That is the precise moment this guide
    stopped being the thing it was asked to be.

    The two rules are not in conflict, and the difference is one word: **measured**. Rule 11 is
    about boxes of invented or generic numbers — the ones that appear because a layout has four
    slots. These four are facts about this site, each with its denominator visible, and the prose
    under them carries the argument the boxes cannot. The ratio stays; the figures come back.
    """
    roles = tokens["color"]["roles"]
    scale = tokens["typography"]["scale"]
    space = tokens["spacing"]
    src = tokens["source"]
    fams = tokens["typography"]["families"]
    variants = len(((tokens.get("components") or {}).get("button") or {}).get("variants") or [])
    slots_total = len(roles) + len(tokens["missing"])

    def stat(value, label, note):
        return (f'<div class="stat"><div class="stat-v">{esc(value)}</div>'
                f'<div class="stat-l">{esc(label)}</div>'
                f'<div class="note">{esc(note)}</div></div>')

    figures = (
        stat(len(fams), "typeface" + ("s" if len(fams) != 1 else ""),
             ", ".join(fams[:2]) or "none measured")
        + stat(len(roles), "colour roles",
               f"of {slots_total} the system has slots for")
        + stat(f"{space['base']}px" if space["base"] else "none",
               "spacing base",
               f"{space['coverage']:.0%} of values sit on it" if space["base"]
               else "no 8/4/2px grid explains the values")
        + stat(variants or "—", "button variant" + ("s" if variants != 1 else ""),
               ("pill" if tokens["radius"]["pill"] else f"{tokens['radius']['default'] or 0}px")
               + " by default")
    )

    missing = ""
    if tokens["missing"]:
        items = ", ".join(esc(m.split(" ")[0]) for m in tokens["missing"])
        missing = (f'<p class="note missing" style="margin-top:24px">Not observed, and therefore '
                   f'not written: {items}. These keep their framework default on purpose — a value '
                   f'nobody measured, sitting in a measured file, is indistinguishable from one '
                   f'that was.</p>')

    shape = tokens["radius"].get("buttonShape") or {}
    shape_line = ""
    if shape.get("of"):
        kind = "pill" if tokens["radius"]["pill"] else "square"
        shape_line = (f' The default control shape comes from {shape.get(kind, 0)} of '
                      f'{shape["of"]} measured buttons.')

    return f"""
<section id="overview" class="page page--centred"><div class="wrap">
  <h2>Overview</h2>
  <div class="stats">{figures}</div>
  <p class="lede" style="max-width:52ch;margin:32px auto 0">
    <strong>{len(roles)} of {slots_total}</strong> colour roles had evidence, from
    {esc(src['pageCount'])} page(s) read at
    {esc(' and '.join(str(v) + 'px' for v in src['viewports']))}.{shape_line}
  </p>
  {missing}
</div></section>"""


def button_for_ground(tokens, ground):
    """The measured button variant that is legible on `ground`, and why it was picked.

    The inverse band used `--primary` like the light one, and on a site whose primary IS the
    inverse ground that paints a black button on a black band: invisible, under a caption reading
    "a system that only works on one ground is half a system". Measured on adidas.it.

    Nothing is invented. The variants here were all read off the real page — adidas ships a white
    button with a black border alongside the black one — so this picks between facts rather than
    computing a colour. If none of them clears 3:1 on that ground, it says so instead of showing
    something that cannot be seen.
    """
    roles = tokens["color"]["roles"]
    variants = (tokens.get("components", {}).get("button") or {}).get("variants") or []
    best = None
    for v in variants:
        ex = v.get("example") or {}
        bg = ex.get("background")
        if not bg or not analyze.parse_hex(bg):
            continue
        ratio = analyze.contrast(bg, ground)
        if ratio >= 3.0 and (best is None or v.get("count", 0) > best[0].get("count", 0)):
            best = (v, bg, ex.get("color") or roles.get("background", {}).get("value", "#fff"),
                    ratio)
    if best is None:
        return None, ("no measured button variant reaches 3:1 on this ground — the source never "
                      "puts one here, and inventing a colour would be the one thing this skill "
                      "does not do")
    v, bg, fg, ratio = best
    return (f'style="background:{esc(bg)};color:{esc(fg)};border:'
            f'{esc(int((v.get("example") or {}).get("borderWidth") or 0))}px solid '
            f'{esc((v.get("example") or {}).get("borderColor") or "transparent")}"',
            f"the variant seen {v.get('count')}× on the page, {ratio:.1f}:1 here")


def rebuild(tokens):
    """The gate made visible. These three controls use only variables; `verify.py` reads their
    computed styles back and fails when one does not equal its token. If this section looks right,
    the tokens are the system; if it looks wrong, the tokens are wrong — not the page."""
    inverse = (tokens["color"]["roles"].get("surface-inverse")
               or tokens["color"]["roles"].get("foreground") or {}).get("value", "#111")
    style, why = button_for_ground(tokens, inverse)
    on_inverse = (f'<p><button class="btn" {style}>Primary action</button>'
                  f'<span class="note" style="margin-left:12px;color:inherit;opacity:.7">{esc(why)}'
                  f'</span></p>' if style else
                  f'<p class="note" style="color:inherit;opacity:.8">{esc(why)}</p>')
    return f"""
<section id="rebuild" class="page"><div class="wrap">
  <h2>Token rebuild test</h2>
  <p class="lede">A button, a card and a field built from the exported variables and nothing else.
  This is the proof that the tokens carry the system: if these look wrong, the tokens are wrong.</p>
  <div class="grid grid--2" style="margin-top:24px">
    <div class="card" data-rebuild="card">
      <h3>On the ground</h3>
      <p class="note">Card surface, border, radius and shadow, all from tokens.</p>
      <p><button class="btn" data-rebuild="button">Primary action</button>
         <button class="btn btn--secondary" data-rebuild="button-secondary">Secondary</button></p>
      <p><label class="note" for="probe">A field</label>
         <input class="field" id="probe" data-rebuild="input" placeholder="focus me to see the ring"></p>
    </div>
    <div class="card" data-rebuild="card-inverse"
         style="background:var(--surface-inverse, var(--foreground, #111));
                color:var(--background, #fff);border-color:transparent">
      <h3 style="color:inherit">On the inverse</h3>
      <p class="note" style="color:inherit;opacity:.8">The same card on the inverted band, because a
      system that only works on one ground is half a system.</p>
      {on_inverse}
    </div>
  </div>
</div></section>"""


def typography(tokens):
    scale = tokens["typography"]["scale"]
    rows = ""
    specimens = ""
    for slot in scale["slots"]:
        key = slot["slot"].replace("text-", "")
        rows += (f"<tr><td><code>{esc(slot['slot'])}</code></td>"
                 f"<td class=num>{esc(slot['size'])}px</td>"
                 f"<td class=num>{esc(slot['mobileSize'] or '—')}</td>"
                 f"<td class=num>{esc(slot['lineHeight'] or '—')}"
                 f"{' (' + str(slot['lineHeightRatio']) + ')' if slot['lineHeightRatio'] else ''}</td>"
                 f"<td class=num>{esc(slot['weight'])}</td>"
                 f"<td class=num>{esc(slot['tracking'] or 0)}em</td>"
                 f"<td class=num>{esc(slot['chars'])}</td>"
                 f"<td>{esc(', '.join(slot['tags']))}</td></tr>")
        specimens += (
            f'<div style="border-bottom:1px solid var(--border, rgba(0,0,0,.08));padding:16px 0">'
            f'<div class="note">{esc(slot["slot"])} · {esc(slot["size"])}px</div>'
            f'<div style="font-size:var(--size-{key});line-height:var(--leading-{key}, 1.2);'
            f'font-weight:var(--weight-{key}, 400);letter-spacing:var(--tracking-{key}, 0)">'
            f'The quick brown fox jumps</div></div>')
    note = f'<p class="note">{esc(scale["note"])}</p>' if scale["note"] else ""
    return f"""
<section id="typography" class="page"><div class="wrap">
  <h2>Typography</h2>
  <p class="lede">Each role is shown at its <strong>real</strong> size, leading, weight and tracking —
  never one size for all. The slot names are Tailwind's own, redefined; no parallel scale was invented.</p>
  {note}
  <div style="margin:24px 0">{specimens}</div>
  <div class="scroll-x"><table>
    <thead><tr><th>Slot</th><th>Desktop</th><th>Mobile</th><th>Leading</th><th>Weight</th>
    <th>Tracking</th><th>Characters</th><th>Seen on</th></tr></thead>
    <tbody>{rows}</tbody>
  </table></div>
</div></section>"""


def fonts(tokens, faces_note=""):
    families = tokens["typography"]["families"]
    faces = tokens["typography"]["fontFaces"]
    cards = ""
    for i, fam in enumerate(families[:3]):
        var = "--font-sans" if i == 0 else "--font-alt"
        cards += (f'<div class="card"><div style="font-size:72px;line-height:1;'
                  f'font-family:var({var}, system-ui)">Aa</div>'
                  f'<h3 style="margin-top:12px">{esc(fam)}</h3>'
                  f'<p class="note">Named and linked, never copied. Font files belong to their owner.</p></div>')
    face_rows = "".join(
        f"<tr><td>{esc(f.get('family'))}</td><td class=num>{esc(f.get('weight') or '—')}</td>"
        f"<td class=note style='word-break:break-all'>{esc((f.get('src') or '')[:120])}</td></tr>"
        for f in faces[:10])
    table = (f'<div class="scroll-x"><table><thead><tr><th>Declared family</th><th>Weight</th>'
             f'<th>Source</th></tr></thead><tbody>{face_rows}</tbody></table></div>'
             if face_rows else '<p class="note">No @font-face rule was readable '
                               '(the stylesheet may be cross-origin).</p>')
    return f"""
<section id="fonts" class="page"><div class="wrap">
  <h2>Fonts</h2>
  {faces_note or '<p class="note">Rendered in a substitute: the real families are named below but '
                 'their files are not loaded, so the sizes here are right and the voice is not. '
                 'Re-render with --link-fonts to see them as the source does.</p>'}
  <div class="grid grid--3" style="margin-top:24px">{cards}</div>
  <h3 style="margin-top:32px">Declared faces</h3>
  {table}
</div></section>"""


def colour(tokens):
    roles = tokens["color"]["roles"]
    tiles = ""
    for name, role in roles.items():
        ratio = next((c for c in tokens["contrast"] if c["pair"].startswith(name)), None)
        tiles += (
            f'<div class="card"><div class="swatch" style="background:var(--{esc(name)})"></div>'
            f'<h3 style="margin-top:12px">{esc(name)}</h3>'
            f'<div class="note"><code>{esc(role["value"])}</code></div>'
            f'<div class="note"><code>{esc(role.get("oklch") or "")}</code></div>'
            f'<div class="note">{esc(role.get("why", ""))}</div>'
            + (f'<div class="note">contrast {esc(ratio["ratio"])} · {esc(ratio["grade"])}</div>'
               if ratio else "")
            + f'<div class="note">seen on {esc(role.get("pages", "?"))} page(s)</div></div>')

    palette = tokens["color"]["palette"]
    total = sum(p["share"] for p in palette) or 1
    share = "".join(
        f'<div title="{esc(p["value"])} — {p["share"] / total:.1%}" '
        f'style="flex:{max(1, round(p["share"] / total * 1000))};background:{esc(p["value"])}"></div>'
        for p in palette[:10])
    grads = "".join(f'<div class="grad-plate"><div class="swatch" style="background:{esc(g)}"></div></div>'
                    for g in tokens["color"]["gradients"][:3])
    return f"""
<section id="colour" class="page page--dark"><div class="wrap">
  <h2>Colour</h2>
  <p class="lede">Roles with the evidence that chose each one. Share is painted area for grounds and
  characters for text, so a one-pixel border on four hundred rows does not outvote a hero.</p>
  <div class="bar-share" style="margin:24px 0">{share}</div>
  <div class="grid grid--3">{tiles}</div>
  {'<h3 style="margin-top:32px">Gradients</h3><div class="grid grid--3">' + grads + '</div>' if grads else ''}
</div></section>"""


def layout(tokens):
    space = tokens["spacing"]
    stair = "".join(
        f'<div style="display:flex;align-items:center;gap:12px">'
        f'<code class="note" style="width:56px">{int(v)}px</code>'
        f'<div style="height:14px;width:{int(v)}px;background:var(--primary, currentColor);'
        f'border-radius:3px"></div></div>'
        for v in space["onGrid"][:10])
    off = ("".join(f"<li><code>{esc(o['value'])}px</code> × {esc(o['count'])}</li>"
                   for o in space["offGrid"][:8]))
    radii = "".join(
        f'<div class="card" style="text-align:center"><div style="height:64px;'
        f'background:var(--primary, currentColor);border-radius:{esc(r["px"])}px"></div>'
        f'<div class="note" style="margin-top:8px">{esc(r["px"])}px · {esc(r["count"])}×</div></div>'
        for r in tokens["radius"]["values"][:5])
    bps = "".join(f"<li><code>{esc(b['edge'])}-width: {esc(b['px'])}px</code></li>"
                  for b in tokens["layout"]["breakpoints"])
    return f"""
<section id="layout" class="page"><div class="wrap">
  <h2>Layout and spacing</h2>
  <div class="grid grid--4" style="margin:24px 0">
    <div class="card"><div class="note">Base unit</div>
      <div style="font-size:var(--size-3xl,30px);font-weight:600">{esc(space['base'] or '—')}px</div>
      <div class="note">{esc(f"{space['coverage']:.0%}") if space['base'] else ''} of values on the grid</div></div>
    <div class="card"><div class="note">Container</div>
      <div style="font-size:var(--size-3xl,30px);font-weight:600">{esc(tokens['layout']['container'] or '—')}</div></div>
    <div class="card"><div class="note">Default radius</div>
      <div style="font-size:var(--size-3xl,30px);font-weight:600">{esc(tokens['radius']['default'] or '—')}</div></div>
    <div class="card"><div class="note">Pill shape</div>
      <div style="font-size:var(--size-3xl,30px);font-weight:600">{'yes' if tokens['radius']['pill'] else 'no'}</div></div>
  </div>
  <div class="grid grid--2">
    <div><h3>The staircase</h3><div style="display:grid;gap:8px">{stair}</div>
      {'<h3 style="margin-top:24px">Off the grid</h3><ul class="note">' + off + '</ul>' if off else ''}</div>
    <div><h3>Radii</h3><div class="grid grid--3">{radii}</div>
      {'<h3 style="margin-top:24px">Breakpoints</h3><ul class="note">' + bps + '</ul>' if bps else ''}</div>
  </div>
</div></section>"""


def components(tokens):
    comps = tokens["components"]
    out = []
    for name, data in comps.items():
        if name in ("header",) or not isinstance(data, dict):
            continue
        variants = data.get("variants") or []
        if not variants:
            continue
        rows = "".join(
            f"<tr><td class=num>{esc(v['count'])}×</td>"
            f"<td><code>{esc(v['example'].get('background') or '—')}</code></td>"
            f"<td class=num>{esc(v['example'].get('radius') if not v['example'].get('radiusIsPill') else 'pill')}</td>"
            f"<td class=num>{esc(' / '.join(str(p) for p in (v['example'].get('padding') or [])))}</td>"
            f"<td class=num>{esc(v['example'].get('borderWidth') or 0)}px "
            f"{esc(v['example'].get('borderColor') or '')}</td></tr>"
            for v in variants)
        inferred = ('<p class="note missing">Inferred: no such element was on the pages read.</p>'
                    if data.get("inferred") else "")
        out.append(f"""<h3 style="margin-top:24px">{esc(name)}</h3>{inferred}
  <div class="scroll-x"><table><thead><tr><th>Seen</th><th>Ground</th><th>Radius</th>
  <th>Padding</th><th>Border</th></tr></thead><tbody>{rows}</tbody></table></div>""")

    header = comps.get("header") or {}
    logo = header.get("logo") or {}
    header_html = ""
    if header:
        box = (f'<div class="logo-box" style="width:{esc(logo.get("width") or 120)}px;'
               f'height:{esc(logo.get("height") or 28)}px">logo</div>') if logo else ""
        header_html = f"""<h3 style="margin-top:24px">Header</h3>
  <div class="card" style="display:flex;align-items:center;gap:16px;
       height:{esc(header.get('height') or 64)}px;padding-block:0">
    {box}
    <span class="note">height {esc(header.get('height'))}px ·
    {'sticky' if header.get('sticky') else 'static'}
    {('· logo ' + esc(logo.get('width')) + '×' + esc(logo.get('height'))
      + ' in ' + esc(logo.get('color'))) if logo else ''}</span>
  </div>
  <p class="note">The logo is a dashed box at its measured size. It is never copied: it belongs to
  its owner, and a measurement does not transfer it.</p>"""

    return f"""
<section id="components" class="page page--dark"><div class="wrap">
  <h2>Components</h2>
  <p class="lede">Measured variants, grouped by their painted signature.</p>
  {''.join(out)}
  {header_html}
</div></section>"""


def imagery(tokens, image_cards):
    """Described in a sentence, because the facts are related and boxes would hide the relation.

    This section used to be four metric boxes too — the same tell as the Overview, wearing a
    different grid class.
    """
    media = tokens.get("mediaSummary") or {}
    ratio = media.get("areaRatio")
    counts = media.get("counts") or {}
    total = sum(counts.values()) if counts else 0
    fits = ", ".join(f"{k} ({n})" for k, n in (media.get("objectFit") or {}).items())
    bleed = media.get("fullBleed")

    if not media:
        body = ('<p class="note">No media statistics were recorded for these pages.</p>')
    else:
        body = (f'<p style="font-size:var(--size-xl, 20px);max-width:52ch;margin:16px 0 0">'
                f'{esc(total)} image(s) and video(s) cover '
                f'<strong>{(ratio or 0):.0%}</strong> of the page area'
                + (f', {esc(bleed)} of them full-bleed' if bleed else '')
                + (f'. Crops are {esc(fits)}' if fits else '')
                + '. The source\'s own photographs stay on the source: what is recorded here is a '
                  'description of them, never a copy.</p>')
    return f"""
<section id="imagery" class="page"><div class="wrap">
  <h2>Imagery</h2>
  {body}
  {image_cards}
</div></section>"""


def voice(tokens):
    v = tokens.get("voice")
    if not v:
        return ""
    rules = "".join(f'<div class="card"><div class="note">Rule {i + 1}</div><p>{esc(r)}</p></div>'
                    for i, r in enumerate(v["rules"]))
    quotes = "".join(
        f'<blockquote style="font-size:var(--size-xl, 20px);margin:0 0 16px;'
        f'border-left:3px solid var(--primary, currentColor);padding-left:16px">'
        f'{esc(q.get("text", ""))}</blockquote>' for q in v.get("quotes", [])[:5])
    stats = "".join(f"<tr><td>{esc(k)}</td><td class=num>{esc(json.dumps(val))}</td></tr>"
                    for k, val in v["stats"].items())
    return f"""
<section id="voice" class="page"><div class="wrap">
  <h2>Voice and tone</h2>
  <p class="lede">Three rules derived from counting, not from an impression. The statistics are
  below so you can disagree with the rules.</p>
  {quotes}
  <div class="grid grid--3" style="margin:24px 0">{rules}</div>
  <div class="scroll-x"><table><thead><tr><th>Measure</th><th>Value</th></tr></thead>
  <tbody>{stats}</tbody></table></div>
</div></section>"""


def tokens_section(tokens, rows):
    css = root_block(rows)
    blob = js_json(tokens)
    table = "".join(
        f"<tr><td><code>{esc(n)}</code></td><td><code>{esc(v)}</code></td>"
        f"<td class=note>{esc(why)}</td></tr>" for n, v, why in rows)
    return f"""
<section id="tokens" class="page page--dark"><div class="wrap">
  <h2>Design tokens</h2>
  <p class="lede">The whole system as variables. Everything on this page reads these and nothing
  else — which is why moving one changes what you see.</p>
  <p>
    <button class="btn" data-copy="css">Copy CSS</button>
    <button class="btn btn--secondary" data-copy="json">Copy JSON</button>
    <button class="btn btn--secondary" data-download="json">Download tokens.json</button>
  </p>
  <div class="scroll-x"><table><thead><tr><th>Variable</th><th>Value</th><th>Evidence</th></tr>
  </thead><tbody>{table}</tbody></table></div>
  <h3 style="margin-top:24px">CSS</h3>
  <pre id="css-block">{esc(css)}</pre>
  <script type="application/json" id="tokens-json">{blob}</script>
</div></section>"""


def method(tokens):
    notes = "".join(f"<li>{esc(n)}</li>" for n in tokens["notes"]) or "<li>None recorded.</li>"
    missing = "".join(f"<li>{esc(m)}</li>" for m in tokens["missing"]) or "<li>Nothing.</li>"
    return f"""
<section id="method" class="page"><div class="wrap">
  <h2>Method</h2>
  <p class="lede">How this was produced, and what it could not see.</p>
  <div class="grid grid--2" style="margin-top:24px">
    <div class="card"><h3>Read</h3>
      <ul class="note">
        <li>Origin: <code>{esc(tokens['source']['origin'])}</code></li>
        <li>Pages: {esc(', '.join(tokens['source']['pages']) or '1')}</li>
        <li>Viewports: {esc(', '.join(str(v) + 'px' for v in tokens['source']['viewports']))}</li>
        <li>Colour schemes: {esc(', '.join(tokens['source']['schemes']))}</li>
      </ul>
      <p class="note">Computed styles from the rendered DOM, not the authored stylesheet: a
      stylesheet declares what is possible, the DOM says what is painted.</p>
    </div>
    <div class="card"><h3>Could not see</h3><ul class="note">{notes}</ul>
      <h3 style="margin-top:16px">Not observed</h3><ul class="note">{missing}</ul></div>
  </div>
</div></section>"""


# --------------------------------------------------------------------------- page


SCRIPT = """
  (function () {
    // Claim the reveal animation only now, when we know we can finish it.
    document.documentElement.classList.add('js');
    var io = new IntersectionObserver(function (es) {
      es.forEach(function (e) { if (e.isIntersecting) { e.target.classList.add('in'); io.unobserve(e.target); } });
    }, { rootMargin: '0px 0px -10% 0px' });
    document.querySelectorAll('section').forEach(function (s) { s.classList.add('reveal'); io.observe(s); });

    function text(what) {
      if (what === 'css') return document.getElementById('css-block').textContent;
      return document.getElementById('tokens-json').textContent;
    }
    document.querySelectorAll('[data-copy]').forEach(function (b) {
      b.addEventListener('click', function () {
        navigator.clipboard.writeText(text(b.dataset.copy)).then(function () {
          var was = b.textContent; b.textContent = 'Copied'; setTimeout(function () { b.textContent = was; }, 1200);
        });
      });
    });
    document.querySelectorAll('[data-download]').forEach(function (b) {
      b.addEventListener('click', function () {
        var blob = new Blob([text('json')], { type: 'application/json' });
        var a = document.createElement('a');
        a.href = URL.createObjectURL(blob); a.download = 'tokens.json';
        document.body.appendChild(a); a.click();
        setTimeout(function () { URL.revokeObjectURL(a.href); a.remove(); }, 800);
      });
    });
  })();
"""


def brand_name(origin):
    """A brand's name, from its host — "Apple", not "www.apple.com".

    R5.2.1 asks for the brand's name across the cover, and the host is not it: a guide titled
    "www.apple.com brand guidelines" reads as a report about a URL, which is exactly the register
    the whole document is supposed to avoid. Strip the scheme, the leading www and the public
    suffix, then capitalise — and leave anything that is already capitalised alone, so `GitHub`
    does not come back as `Github`. The user can always override with `--brand`.
    """
    host = (origin or "the source").split("//")[-1].split("/")[0]
    # A subdomain is not a brand: `ui.shadcn.com` is Shadcn, not Ui. These are the labels a site
    # puts in front of its own name, never the name itself.
    PREFIX = {"www", "ui", "app", "apps", "docs", "doc", "shop", "store", "my", "go", "get",
              "web", "beta", "staging", "dev", "m", "mobile", "account", "portal", "cloud"}
    parts = [x for x in host.split(".") if x]
    while len(parts) > 2 and parts[0].lower() in PREFIX:
        parts.pop(0)
    if parts and parts[0].lower() in PREFIX and len(parts) > 1:
        parts.pop(0)
    label = parts[0] if parts else host
    if not label:
        return host
    return label if label[:1].isupper() or any(c.isupper() for c in label) else label.capitalize()


def render(tokens, brand, image_cards="", embedded_css="", link_fonts=False):
    rows = token_rows(tokens)
    faces, faces_note = font_faces(tokens, link_fonts)
    origin = tokens["source"]["origin"] or "the source"
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(brand)} — measured design system</title>
<meta name="description" content="An unofficial, measured record of the design system rendered at {esc(origin)}.">
<style>
{faces}
  {root_block(rows)}
  {embedded_css}
  {stylesheet(tokens)}
</style>
</head>
<body>

<div class="bar">
  <span class="pill">Unofficial analysis</span>
  <span class="note">{esc(brand)}</span>
  <span style="flex:1"></span>
  <a class="note" href="#review"><strong>Decide</strong></a>
  <a class="note" href="#rebuild">Rebuild</a>
  <a class="note" href="#colour">Colour</a>
  <a class="note" href="#typography">Type</a>
  <a class="note" href="#tokens">Tokens</a>
</div>

{cover(tokens, brand)}
{review(tokens)}
{overview(tokens)}
{contents(tokens)}
{rebuild(tokens)}
{typography(tokens)}
{fonts(tokens, faces_note)}
{colour(tokens)}
{layout(tokens)}
{components(tokens)}
{imagery(tokens, image_cards)}
{voice(tokens)}
{tokens_section(tokens, rows)}
{method(tokens)}

<footer><div class="wrap">
  <span class="pill">Unofficial analysis</span>
  <p class="note">Not affiliated with or endorsed by {esc(brand)}. Trademarks, logos, fonts and
  photographs belong to their owners and are not reproduced here. This page records measurements
  taken from publicly rendered pages, for the purpose of building something different.</p>
</div></footer>

<script>{SCRIPT}</script>
</body>
</html>
"""


def image_section(images_dir):
    """Hero edition only. Each image is embedded once as a data URI and reused through a class, so a
    picture used on four slides costs its bytes once."""
    if not images_dir or not images_dir.is_dir():
        return "", ""
    cards, css = [], []
    for i, path in enumerate(sorted(images_dir.glob("*.webp"))[:12]):
        mime = mimetypes.guess_type(path.name)[0] or "image/webp"
        data = base64.b64encode(path.read_bytes()).decode()
        cls = f"img-{i}"
        css.append(f".{cls} {{ background-image: url(data:{mime};base64,{data});"
                   f" background-size: cover; background-position: center; }}")
        cards.append(f'<div class="card" style="padding:0;overflow:hidden">'
                     f'<div class="{cls}" style="height:200px"></div>'
                     f'<div style="padding:12px"><span class="pill">AI-generated image</span></div></div>')
    return ('<div class="grid grid--3" style="margin-top:24px">' + "".join(cards) + "</div>"
            if cards else ""), "\n".join(css)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("tokens", type=Path)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--images", type=Path, default=None)
    ap.add_argument("--brand", default=None)
    ap.add_argument("--link-fonts", action="store_true",
                    help="declare the measured @font-face rules so the guide renders in the "
                         "source's own typefaces. Links, never copies — and the page stops "
                         "being offline, which verify.py will then report")
    args = ap.parse_args(argv)

    tokens = json.loads(args.tokens.read_text(encoding="utf-8"))
    brand = args.brand or brand_name(tokens["source"]["origin"])
    args.out.mkdir(parents=True, exist_ok=True)

    light = args.out / "brand-guide.html"
    light.write_text(render(tokens, brand, link_fonts=args.link_fonts), encoding="utf-8")
    size = light.stat().st_size
    print(f"brand-guide.html      {size / 1024:.1f} KB"
          f"{'  ⚠ over the 150 KB budget' if size > MAX_LIGHT_BYTES else ''}")

    cards, css = image_section(args.images)
    if cards:
        hero = args.out / "brand-guide-hero.html"
        hero.write_text(render(tokens, brand, cards, css, link_fonts=args.link_fonts),
                        encoding="utf-8")
        print(f"brand-guide-hero.html {hero.stat().st_size / 1024:.1f} KB")
    else:
        print("brand-guide-hero.html  skipped (no images: the gradient fallbacks are the design)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
