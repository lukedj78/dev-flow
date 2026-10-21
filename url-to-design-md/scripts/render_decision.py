#!/usr/bin/env python3
"""One decision, drawn side by side, so the question can be seen instead of read.

"`muted-foreground` is 2.54:1" is a sentence about a colour. Nobody can answer it. The same two
greys printed on the real ground, in the real typeface, at the real size, answer themselves in a
second — and that is the whole reason this file exists.

It reuses `render_guide`'s stylesheet and `:root`, so a specimen here is made of exactly the same
variables as the guide. A purpose-built comparison with its own styling would be a third renderer
showing a design that exists nowhere, which is the mistake the video made.

    render_decision.py <tokens.json> --out <dir> --kind contrast --token muted-foreground \\
        --proposed "#707782"

Kinds:
    contrast  two colours on the real ground, with their ratios and grades
    type      one type step at its current and proposed size, in context
    colour    two values of any colour token, on a swatch and in the components that use it
    spacing   the same card at the current and proposed base unit
"""

from __future__ import annotations

import argparse
import html
import json
import re
from pathlib import Path

import analyze
import render_guide


def esc(v):
    return html.escape(str(v), quote=True)


def specimen_contrast(tokens, token_name, current, proposed):
    ground = tokens["color"]["roles"].get("background", {}).get("value", "#ffffff")
    rows = []
    for label, value in (("Now, as measured", current), ("Proposed", proposed)):
        if not value:
            continue
        ratio = analyze.contrast(value, ground)
        grade = analyze.wcag_grade(ratio)
        rows.append(f"""
      <div class="card" style="background:{esc(ground)}">
        <div class="note" style="color:{esc(value)}">{esc(label)}</div>
        <p style="color:{esc(value)};font-size:var(--size-base,16px);margin:8px 0 0">
          The quick brown fox jumps over the lazy dog, and this is the size and the weight the
          page actually uses for secondary text.</p>
        <p style="color:{esc(value)};font-size:var(--size-sm,14px);margin:8px 0 0">
          And this is the smaller one, which is where a weak contrast is felt first.</p>
        <div style="margin-top:16px;display:flex;gap:10px;align-items:center">
          <code>{esc(value)}</code>
          <span class="pill" style="border-color:{esc(value)};color:{esc(value)}">
            {esc(ratio)}:1 · {esc(grade)}</span>
        </div>
      </div>""")
    return "".join(rows)


def specimen_type(tokens, slot_name, current, proposed):
    slot = next((s for s in tokens["typography"]["scale"]["slots"]
                 if s["slot"] == slot_name), None)
    if slot is None:
        return "<p class='note'>no such type step</p>"
    rows = []
    for label, size in (("Now, as measured", current), ("Proposed", proposed)):
        if size is None:
            continue
        rows.append(f"""
      <div class="card">
        <div class="note">{esc(label)} — {esc(int(size) if size == int(size) else size)}px</div>
        <div style="font-size:{esc(size)}px;line-height:{esc(slot['lineHeightRatio'] or 1.15)};
                    font-weight:{esc(slot['weight'])};
                    letter-spacing:{esc(slot['tracking'] or 0)}em;margin-top:8px">
          Ship the thing you measured</div>
        <p class="note" style="margin-top:12px">on a 390px screen that is about
          {esc(max(1, round(390 / (size * 0.5))))} characters per line
          {esc('— under 15 is where a headline starts breaking badly' if 390 / (size * 0.5) < 15 else '')}</p>
      </div>""")
    return "".join(rows)


def specimen_colour(tokens, token_name, current, proposed):
    """A ground is judged by what sits on it, never by a rectangle.

    The first version drew a swatch and a button filled with the token, which for a BACKGROUND means
    a button the colour of the page — invisible, and it made both candidates look equally bad for a
    reason that had nothing to do with either. A ground gets a miniature page instead: heading, body,
    a card, the real primary button. An action colour still gets the button, because that is where
    an action colour lives.
    """
    roles = tokens["color"]["roles"]
    GROUNDS = ("background", "card", "secondary", "muted", "popover", "surface-inverse")
    ink = roles.get("foreground", {}).get("value", "#111111")
    mute = roles.get("muted-foreground", {}).get("value", ink)
    line = roles.get("border", {}).get("value", "rgba(0,0,0,.12)")
    action = roles.get("primary", {}).get("value", "#333333")
    on_action = roles.get("primary-foreground", {}).get("value", "#ffffff")

    rows = []
    for label, value in (("Now, as measured", current), ("Proposed", proposed)):
        if not value:
            continue
        if token_name in GROUNDS:
            readable = analyze.contrast(ink, value)
            grade = analyze.wcag_grade(readable)
            body = f"""
        <div style="background:{esc(value)};border:1px solid {esc(line)};
                    border-radius:var(--radius,12px);padding:20px">
          <div style="font-size:var(--size-3xl,28px);line-height:1.15;font-weight:600;
                      color:{esc(ink)}">A heading on this ground</div>
          <p style="color:{esc(ink)};margin:10px 0 0">Body text at the size the page actually uses,
            so the ground is judged by what sits on it.</p>
          <p style="color:{esc(mute)};margin:6px 0 16px;font-size:var(--size-sm,14px)">
            And the secondary text, which is where a weak ground is felt first.</p>
          <span style="display:inline-block;background:{esc(action)};color:{esc(on_action)};
                       padding:10px 20px;border-radius:var(--radius-pill,9999px);
                       font-weight:600">Primary action</span>
        </div>
        <div style="margin-top:12px"><code>{esc(value)}</code>
          <span class="pill" style="margin-left:8px">text {esc(readable)}:1 · {esc(grade)}</span></div>"""
        else:
            body = f"""
        <div class="swatch" style="background:{esc(value)};margin-bottom:12px"></div>
        <span style="display:inline-block;background:{esc(value)};color:{esc(on_action)};
                     padding:10px 20px;border-radius:var(--radius-pill,9999px);
                     font-weight:600">Primary action</span>
        <div style="margin-top:12px"><code>{esc(value)}</code>
          <span class="note">{esc(analyze.oklch_css(value) or '')}</span></div>"""
        rows.append(f'<div class="card"><div class="note">{esc(label)}</div>{body}</div>')
    return "".join(rows)


def specimen_spacing(tokens, _token, current, proposed):
    rows = []
    for label, base in (("Now, as measured", current), ("Proposed", proposed)):
        if base is None:
            continue
        b = float(base)
        rows.append(f"""
      <div class="card" style="padding:{b * 3}px">
        <div class="note">{esc(label)} — base {esc(int(b) if b == int(b) else b)}px</div>
        <h3 style="margin:{b}px 0 {b}px">A card at this rhythm</h3>
        <p style="margin:0 0 {b * 2}px">Padding, the gap under the heading and the space before the
          button are all multiples of the base. This is what the grid feels like.</p>
        <span class="btn">Action</span>
      </div>""")
    return "".join(rows)



def specimen_scale(tokens, _token, current, proposed):
    """The measured steps against the same steps regularised onto one ratio. Seeing both as type,
    at their real sizes, is the only way to judge whether the jumps are deliberate or accidental."""
    slots = tokens["typography"]["scale"]["slots"]
    if not slots:
        return "<p class='note'>no type scale</p>"
    base = min(s["size"] for s in slots)
    ratio = float(proposed or 1.25)
    rows = []
    for label, sizes in (
            ("Now, as measured", [s["size"] for s in slots]),
            (f"Regularised at {ratio}", [round(base * ratio ** i, 1)
                                         for i in range(len(slots) - 1, -1, -1)])):
        steps = "".join(
            f'<div style="font-size:{min(sz, 56)}px;line-height:1.15;font-weight:600;'
            f'margin-bottom:4px">{sz}px <span class="note" style="font-size:12px">'
            f'{esc(slots[i]["slot"])}</span></div>'
            for i, sz in enumerate(sizes))
        jumps = [round(sizes[i] / sizes[i + 1], 2) for i in range(len(sizes) - 1)]
        rows.append(f"""
      <div class="card">
        <div class="note">{esc(label)}</div>
        <div style="margin-top:12px">{steps}</div>
        <p class="note" style="margin-top:12px">steps {esc(jumps)}</p>
      </div>""")
    return "".join(rows)


def specimen_fallback(tokens, _token, _current, _proposed):
    """What the unobserved slots will look like. shadcn's defaults are not neutral — they are a
    design somebody else chose — and the only honest way to accept them is to see them."""
    missing = [m.split(" ")[0] for m in tokens["missing"] if not m.startswith(("ring",))]
    written = list(tokens["color"]["roles"])
    DEFAULTS = {"destructive": "oklch(0.577 0.245 27.325)", "popover": "oklch(1 0 0)",
                "accent": "oklch(0.97 0 0)", "muted": "oklch(0.97 0 0)",
                "card-foreground": "oklch(0.145 0 0)", "input": "oklch(0.922 0 0)",
                "secondary-foreground": "oklch(0.205 0 0)",
                "popover-foreground": "oklch(0.145 0 0)",
                "accent-foreground": "oklch(0.205 0 0)",
                "destructive-foreground": "oklch(0.985 0 0)"}
    tiles = "".join(
        f'<div style="text-align:center">'
        f'<div class="swatch" style="background:{esc(DEFAULTS.get(m, "#dddddd"))};height:64px"></div>'
        f'<div class="note" style="margin-top:6px">{esc(m)}</div></div>'
        for m in missing[:10])
    kept = "".join(
        f'<div style="text-align:center">'
        f'<div class="swatch" style="background:var(--{esc(k)});height:64px"></div>'
        f'<div class="note" style="margin-top:6px">{esc(k)}</div></div>'
        for k in written[:10])
    return f"""
      <div class="card">
        <div class="note">Measured on this site — {len(written)} slot(s)</div>
        <div class="grid grid--4" style="margin-top:12px">{kept}</div>
      </div>
      <div class="card">
        <div class="note">Not observed — {len(missing)} slot(s), these are shadcn's own defaults</div>
        <div class="grid grid--4" style="margin-top:12px">{tiles}</div>
        <p class="note" style="margin-top:12px">A default is a design somebody else chose. Accepting
        it is fine; not seeing it first is not.</p>
      </div>"""


KINDS = {"contrast": specimen_contrast, "type": specimen_type,
         "colour": specimen_colour, "spacing": specimen_spacing,
         "scale": specimen_scale, "fallback": specimen_fallback}



def render(tokens, kind, token_name, current, proposed, question):
    rows = render_guide.token_rows(tokens)
    body = KINDS[kind](tokens, token_name, current, proposed)
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Decision — {esc(token_name)}</title>
<style>
  {render_guide.root_block(rows)}
  {render_guide.stylesheet(tokens)}
  .pair {{ display:grid; gap:20px; grid-template-columns:repeat(auto-fit,minmax(300px,1fr));
           margin-top:20px; }}
  .pair > * {{ min-width:0; }}
  section {{ padding-block: 28px; }}
</style></head>
<body>
<section><div class="wrap">
  <span class="pill">Decision</span>
  <h2 style="margin-top:10px">{esc(token_name)}</h2>
  <p class="lede">{esc(question)}</p>
  <div class="pair">{body}</div>
</div></section>
</body></html>
"""


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("tokens", type=Path)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--kind", choices=sorted(KINDS), required=True)
    ap.add_argument("--token", required=True, help="the token or type slot under discussion")
    ap.add_argument("--current", default=None, help="defaults to the value in tokens.json")
    ap.add_argument("--proposed", default=None)
    ap.add_argument("--question", default="")
    args = ap.parse_args(argv)

    tokens = json.loads(args.tokens.read_text(encoding="utf-8"))

    current = args.current
    if current is None:
        if args.kind == "type":
            slot = next((s for s in tokens["typography"]["scale"]["slots"]
                         if s["slot"] == args.token), None)
            current = slot["size"] if slot else None
        elif args.kind == "spacing":
            current = tokens["spacing"]["base"]
        else:
            current = tokens["color"]["roles"].get(args.token, {}).get("value")

    proposed = args.proposed
    if proposed is None and args.kind == "contrast":
        ground = tokens["color"]["roles"].get("background", {}).get("value", "#ffffff")
        proposed, _ = analyze.adjust_for_contrast(current, ground, 4.5)

    cast = float if args.kind in ("type", "spacing") else str
    args.out.mkdir(parents=True, exist_ok=True)
    # The token name comes from the command line and lands in a FILENAME. `--token ../../x` would
    # write outside --out, which is a path traversal in a tool whose whole job is to be pointed at
    # untrusted material. Scrubbed to the characters a token name can actually have.
    safe_token = re.sub(r"[^A-Za-z0-9._-]+", "-", str(args.token))[:60].strip("-.") or "token"
    target = args.out / f"decision-{args.kind}-{safe_token}.html"
    target.write_text(render(tokens, args.kind, args.token,
                             cast(current) if current is not None else None,
                             cast(proposed) if proposed is not None else None,
                             args.question), encoding="utf-8")
    print(f"{target}  ({current} -> {proposed})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
