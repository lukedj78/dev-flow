#!/usr/bin/env python3
"""The gate that cannot be argued with: rebuild a component from the tokens and count the pixels.

Everything else in this skill checks that the guide agrees with the tokens. That passes happily
while the TOKENS are wrong, and on adidas.it it did: thirteen of fourteen buttons were measured at
radius 0 — a famously square brand — the aggregation threw the zeros away, one 24px dot made the
system "pill", and every downstream check was satisfied because the guide faithfully drew the wrong
thing. Nothing in the pipeline objected. A person looked at it and said the buttons were wrong.

So: crop the real component out of a screenshot of the real page, rebuild the same box from the
exported tokens alone, and report the share of pixels that differ. A number, not an impression.

    pixel_check.py build   <tokens.json> --out <dir>   # writes rebuild.html from the tokens
    pixel_check.py compare --out <dir>                 # source-*.png vs rebuilt-*.png

The crops and the rebuilt shots are taken by `run-pixel-check.js` under Playwright, which is the
only part that needs a browser.
"""

from __future__ import annotations

import argparse
import html
import json
import sys
from pathlib import Path

# A component is "matched" below this share of differing pixels. It is deliberately not zero: text
# antialiasing and a one-pixel subpixel offset are not design errors. It IS tight enough that a pill
# against a square, or a wrong ground, blows straight through it.
MATCH_THRESHOLD = 0.08


def esc(v):
    return html.escape(str(v), quote=True)


def collect_components(snapshots):
    """Every button and card the measurement found, with where it was and how big."""
    out = []
    for snap in snapshots:
        page = snap.get("path") or "/"
        vw = snap["viewport"]["width"]
        for kind in ("buttons", "cards", "inputs"):
            group = (snap.get("candidates") or {}).get(kind) or {}
            n = 0
            for box in group.get("sample", [])[:6]:
                rect = box.get("rect")
                if not rect or rect["w"] < 40 or rect["h"] < 16:
                    continue          # too small to compare meaningfully
                out.append({
                    # numbered over the ELIGIBLE ones, so the ids line up with the crops the
                    # browser takes under the same filter
                    "id": f"{kind[:-1]}-{vw}-{n}",
                    "kind": kind[:-1],
                    "page": page,
                    "viewport": vw,
                    "rect": rect,
                    "measured": box,
                })
                n += 1
    return out


def rebuild_html(tokens, components):
    """Each component drawn from the TOKENS only, at the measured size.

    Deliberately not from `measured`: using the measured values would compare the page with itself
    and always pass. The whole question is whether the *tokens* — the thing that leaves this skill —
    are enough to put the pixels back.
    """
    import render_guide
    rows = render_guide.token_rows(tokens)
    roles = tokens["color"]["roles"]

    def role(name, fallback="transparent"):
        return roles.get(name, {}).get("value", fallback)

    radius = tokens["radius"]
    shape = "9999px" if radius.get("pill") else f"{radius.get('default') or 0}px"

    blocks = []
    for c in components:
        w, h = c["rect"]["w"], c["rect"]["h"]
        m = c["measured"]
        # Which TOKEN ROLE expresses this component? That is the whole question. Drawing every
        # button as `primary` compares a black button against a white one and teaches nothing —
        # measured on adidas.it, where three of four candidates were transparent or white and the
        # naive rebuild reported 90% difference for the wrong reason.
        ground = m.get("background")
        role_name = next((n for n, r in roles.items() if r.get("value") == ground), None)
        if ground and role_name is None:
            c["unexpressed"] = ground          # no token can draw this: a real gap, reported below
        fg = None
        if role_name:
            fg = role(role_name + "-foreground", None) or role("foreground", "#000")
        bg_css = role(role_name) if role_name else "transparent"

        border_px = m.get("borderWidth") or 0
        corner = ("9999px" if radius.get("pill")
                  else f"{radius.get('default') or 0}px")
        style = (f"background:{esc(bg_css)};"
                 f"color:{esc(fg or role('foreground', '#000'))};"
                 f"border-radius:{esc(corner)};"
                 + (f"border:{int(border_px)}px solid {esc(role('border', 'transparent'))};"
                    if border_px else "border:0;"))
        # The label is drawn with the TOKEN typography, not the measured one: the question is
        # whether the exported family, size, weight and tracking put the same letters in the same
        # places. Without it the comparison stops at the box and never tests the type at all.
        label = esc(m.get("label") or "")
        # Match the measured size to the nearest TOKEN step, so the comparison tests the exported
        # scale rather than feeding the measured value back in and passing by construction.
        font = (tokens["typography"]["families"] or ["system-ui"])[0]
        steps = tokens["typography"]["scale"]["slots"]
        measured_size = float(m.get("fontSize") or 16)
        step = min(steps, key=lambda s: abs(s["size"] - measured_size)) if steps else None
        tok_size = step["size"] if step else measured_size
        tok_weight = step["weight"] if step else (m.get("fontWeight") or 400)
        tok_track = (step["tracking"] or 0) if step else 0
        tok_case = (step.get("textTransform") or "none") if step else "none"
        blocks.append(
            f'<div class="shot" data-shot="{esc(c["id"])}" '
            f'style="width:{w}px;height:{h}px;{style}'
            f'font-family:{esc(font)},system-ui,sans-serif;'
            f'font-size:{esc(tok_size)}px;'
            f'font-weight:{esc(tok_weight)};'
            f'letter-spacing:{esc(tok_track)}em;'
            f'text-transform:{esc(tok_case)};'
            f'display:flex;align-items:center;justify-content:center;'
            f'overflow:hidden;box-sizing:border-box">{label}</div>')

    # The source's own faces, linked. Without them the type comparison would fail because the
    # browser substituted a font, which is a fact about this machine and not about the tokens.
    faces, _ = render_guide.font_faces(tokens, True)

    return f"""<!doctype html>
<html><head><meta charset="utf-8"><title>rebuild</title>
<style>
{faces}
  {render_guide.root_block(rows)}
  * {{ box-sizing: border-box; }}
  body {{ margin:0; background: {esc(role('background', '#fff'))}; }}
  .shot {{ margin: 0 0 24px; }}
</style></head>
<body>{''.join(blocks)}</body></html>
"""


def cmd_build(args):
    tokens = json.loads(args.tokens.read_text(encoding="utf-8"))
    snaps = [json.loads(p.read_text(encoding="utf-8"))
             for p in sorted(args.out.glob("snapshot-*.json"))]
    if not snaps:
        print(f"no snapshot-*.json in {args.out}", file=sys.stderr)
        return 2
    components = collect_components(snaps)
    if not components:
        print("the snapshots carry no component rects — re-measure with the current extract.js",
              file=sys.stderr)
        return 2
    (args.out / "components.json").write_text(json.dumps(components, indent=2), encoding="utf-8")
    (args.out / "rebuild.html").write_text(rebuild_html(tokens, components), encoding="utf-8")
    print(f"{len(components)} component(s) -> {args.out}/components.json, rebuild.html")
    for c in components[:8]:
        print(f"  {c['id']:<14} {c['kind']:<7} {c['rect']['w']}x{c['rect']['h']} on {c['page']}")
    return 0


def cmd_compare(args):
    try:
        from PIL import Image, ImageChops
    except ImportError:
        print("Pillow is needed for the pixel comparison "
              "(the repo already requires it for image-to-design-md)", file=sys.stderr)
        return 2

    rows, missing = [], []
    for src in sorted(args.out.glob("source-*.png")):
        ident = src.stem[len("source-"):]
        rebuilt = args.out / f"rebuilt-{ident}.png"
        if not rebuilt.is_file():
            missing.append(ident)
            continue
        a = Image.open(src).convert("RGB")
        b = Image.open(rebuilt).convert("RGB")
        if a.size != b.size:
            b = b.resize(a.size)
        diff = ImageChops.difference(a, b).convert("L")
        # a pixel counts as different when it is off by more than a little: antialiasing on text
        # moves values by a few units and is not a design error
        hist = diff.histogram()
        differing = sum(hist[25:])          # off by more than antialiasing moves it
        share = differing / (a.size[0] * a.size[1])
        rows.append((ident, share, a.size))

    if missing:
        print(f"  {len(missing)} component(s) have no rebuilt shot: {', '.join(missing[:6])}")
    if not rows:
        print("nothing to compare — run run-pixel-check.js first", file=sys.stderr)
        return 2

    rows.sort(key=lambda r: -r[1])
    worst = rows[0][1]
    matched = sum(1 for _, s, _ in rows if s <= MATCH_THRESHOLD)
    print(f"{matched}/{len(rows)} component(s) within {MATCH_THRESHOLD:.0%} differing pixels\n")
    for ident, share, size in rows:
        mark = "✓" if share <= MATCH_THRESHOLD else "✗"
        print(f"  {mark} {ident:<16} {share:6.1%} differ   {size[0]}x{size[1]}")
    if worst > MATCH_THRESHOLD:
        print(f"\nThe worst is {worst:.1%}. A component rebuilt from the tokens that does not land "
              f"on the original is a token that is wrong — not a rendering detail.")
    return 0 if matched == len(rows) else 1


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build")
    b.add_argument("tokens", type=Path)
    b.add_argument("--out", type=Path, required=True)
    b.set_defaults(fn=cmd_build)
    c = sub.add_parser("compare")
    c.add_argument("--out", type=Path, required=True)
    c.set_defaults(fn=cmd_compare)
    args = ap.parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    raise SystemExit(main())
