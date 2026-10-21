#!/usr/bin/env python3
"""tokens.json -> DESIGN.md, plus the record of what we changed and why.

This is the only file that survives into the flow. Everything else the skill makes — the snapshot,
the guide, the slides, the video — exists so that a person can decide what this should say.

Two things it must get right, and they pull in opposite directions:

  * The DESIGN.md conforms to the Google design.md spec, whose token names are SEMANTIC
    (`colors.on-surface`, `typography.h1`). That is not a lapse from the numeric-scale rule: the
    rule governs the code, and `design-md-to-app` is what turns these names into shadcn's own slots
    (`--foreground`, `text-7xl`). Writing Tailwind slot names here would break the consumer.
  * Every value is one value. A spec file with two numbers per key cannot be read by anything. The
    measured-versus-chosen record is a SEPARATE file that nothing downstream reads — it exists for
    the person who comes back in two months and wonders whether 56px was a decision or a slip.

    make_design_md.py <tokens.json> --out <dir> [--measured <tokens.measured.json>] [--name X]
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

# Our measured role -> the spec's name, taken from design-md-to-app/references/shadcn-mapping.md so
# the round trip (page -> DESIGN.md -> shadcn variable) lands back on the slot it came from.
ROLE_TO_SPEC = {
    "background": "background",
    "foreground": "on-surface",
    "card": "surface-container",
    "muted-foreground": "on-surface-variant",
    "primary": "primary",
    "primary-foreground": "on-primary",
    "secondary": "secondary",
    "secondary-foreground": "on-secondary",
    "accent": "tertiary",
    "accent-foreground": "on-tertiary",
    "destructive": "error",
    "destructive-foreground": "on-error",
    "border": "outline",
    "ring": "surface-tint",
    "surface-inverse": "inverse-surface",
}

# A measured cluster gets its spec name from the tag it is mostly used on, and from its rank when
# the tag does not settle it. Sizes stay in px, exactly as measured.
TAG_TO_SPEC = {"h1": "h1", "h2": "h2", "h3": "h3", "h4": "h4", "h5": "h5", "h6": "h6",
               "p": "body-md", "li": "body-md", "label": "label", "a": "link",
               "button": "label", "small": "body-sm", "code": "code"}


def px(value) -> str:
    """`16.0px` is a measurement artefact, not a design value. Round-trip it to the integer when it
    is one, because the number lands in a spec file people read."""
    try:
        f = float(value)
    except (TypeError, ValueError):
        return str(value)
    return f"{int(f)}px" if f == int(f) else f"{round(f, 2)}px"


def yaml_scalar(value) -> str:
    """A scalar for the DESIGN.md front matter, which is agent input downstream.

    Always quoted, via `json.dumps`. The first version hand-rolled the quoting and a newline could
    end the value and start a KEY. The second tried to keep plain scalars where they looked safe,
    and that was still wrong in two ways a review caught: `#` mid-string opens a YAML comment, so
    `Inter #x` parses as `Inter` — a silent truncation; and U+0085, U+2028 and U+2029 are line
    breaks to a YAML parser while passing straight through a control-character filter that only
    looks below 0x20.

    Both were me defending something weak — `fontFamily: Inter` reads nicer than
    `fontFamily: "Inter"` — against a parser differential in a file another agent reads as
    instructions. JSON is a subset of YAML 1.2, `json.dumps` escapes everything that matters, and
    one rule with no exceptions is the only kind I can be sure of here.
    """
    s = str(value)
    s = "".join(c for c in s
                if ord(c) >= 0x20 and ord(c) not in (0x7F, 0x85, 0x2028, 0x2029))
    return json.dumps(s)


def typography_names(slots):
    """Assign one spec name per measured role, largest first, without ever reusing a name."""
    used, named = set(), []
    for rank, slot in enumerate(slots):
        candidate = None
        for tag in slot.get("tags", []):
            maybe = TAG_TO_SPEC.get(tag)
            if maybe and maybe not in used:
                candidate = maybe
                break
        if candidate is None:
            for fallback in (f"h{rank + 1}", "body-lg", "body-md", "body-sm", "label", "caption"):
                if fallback not in used:
                    candidate = fallback
                    break
        used.add(candidate)
        named.append((candidate, slot))
    return named


def frontmatter(tokens, name):
    lines = ["---", "version: alpha", f"name: {yaml_scalar(name)}"]
    origin = tokens["source"]["origin"] or "an unnamed source"
    lines.append(f"description: {yaml_scalar('Measured from ' + origin)}")

    roles = tokens["color"]["roles"]
    mapped = [(ROLE_TO_SPEC[r], roles[r]["value"]) for r in roles if r in ROLE_TO_SPEC]
    if mapped:
        lines.append("colors:")
        for spec_name, value in mapped:
            lines.append(f"  {spec_name}: {yaml_scalar(value)}")

    slots = tokens["typography"]["scale"]["slots"]
    if slots:
        lines.append("typography:")
        for spec_name, slot in typography_names(slots):
            lines.append(f"  {spec_name}:")
            lines.append(f"    fontFamily: {yaml_scalar(slot['family'])}")
            lines.append(f"    fontSize: {px(slot['size'])}")
            lines.append(f"    fontWeight: {slot['weight']}")
            if slot["lineHeightRatio"]:
                lines.append(f"    lineHeight: {slot['lineHeightRatio']}")
            if slot["tracking"]:
                lines.append(f"    letterSpacing: {slot['tracking']}em")
            if slot["textTransform"]:
                lines.append(f"    textTransform: {slot['textTransform']}")

    radii = tokens["radius"]["values"]
    if radii or tokens["radius"]["pill"]:
        lines.append("rounded:")
        for i, r in enumerate(radii[:4]):
            lines.append(f"  {['sm', 'md', 'lg', 'xl'][i]}: {px(r['px'])}")
        if tokens["radius"]["pill"]:
            lines.append("  full: 9999px")

    base = tokens["spacing"]["base"]
    if base:
        lines.append("spacing:")
        for v in tokens["spacing"]["onGrid"][:8]:
            lines.append(f"  s{int(v)}: {int(v)}px")

    lines.append("---")
    return "\n".join(lines)


def body(tokens, name, measured_note):
    roles = tokens["color"]["roles"]
    src = tokens["source"]
    scale = tokens["typography"]["scale"]

    def rows(pairs):
        return "\n".join(f"| {a} | {b} |" for a, b in pairs)

    colour_rows = "\n".join(
        f"| `{ROLE_TO_SPEC.get(r, r)}` | `{roles[r]['value']}` | `{roles[r].get('oklch') or ''}` "
        f"| {roles[r].get('why', '')} |"
        for r in roles)

    contrast_rows = "\n".join(
        f"| {c['pair']} | {c['ratio']} | {c['grade']} |" for c in tokens["contrast"]) or \
        "| — | — | no pair could be computed |"

    type_rows = "\n".join(
        f"| `{spec}` | {s['family']} | {px(s['size'])} | "
        f"{s['mobileSize'] or '—'} | {s['weight']} | {s['lineHeight'] or '—'} | "
        f"{s['tracking'] or 0}em |"
        for spec, s in typography_names(scale["slots"]))

    missing = "\n".join(f"- {m}" for m in tokens["missing"]) or "- Nothing."
    notes = "\n".join(f"- {n}" for n in tokens["notes"]) or "- None."

    motion = tokens.get("motion")
    motion_block = "Not observed: no control on the pages read declares a transition."
    if motion:
        d = ", ".join(f"{ms}ms (×{n})" for ms, n in motion["durations"][:3]) or "—"
        e = ", ".join(f"`{c}` (×{n})" for c, n in motion["easings"][:2]) or "—"
        motion_block = f"Durations: {d}. Easing: {e}."

    voice = tokens.get("voice")
    voice_block = "Not observed."
    if voice:
        voice_block = "\n".join(f"{i + 1}. {r}" for i, r in enumerate(voice["rules"]))

    comps = []
    for cname, data in tokens["components"].items():
        if not isinstance(data, dict):
            continue
        variants = data.get("variants") or []
        if not variants:
            continue
        flag = " **(inferred — not present on the pages read)**" if data.get("inferred") else ""
        lines = [f"**{cname}**{flag}", ""]
        for v in variants[:4]:
            ex = v["example"]
            radius = "pill" if ex.get("radiusIsPill") else f"{ex.get('radius')}px"
            lines.append(f"- {v['count']}× — ground `{ex.get('background') or 'transparent'}`, "
                         f"radius {radius}, padding {'/'.join(str(p) for p in ex.get('padding') or [])}"
                         + (f", border {ex.get('borderWidth')}px `{ex.get('borderColor')}`"
                            if ex.get("borderWidth") else ""))
        comps.append("\n".join(lines))
    components_block = "\n\n".join(comps) or "Not observed."

    bps = ", ".join(f"{b['edge']}-width {b['px']}px" for b in tokens["layout"]["breakpoints"]) or "—"

    return f"""
# {name}

**Unofficial measurement.** Every value below was read from the rendered pages of
`{src['origin']}` on {src['pageCount']} page(s), at {', '.join(str(v) + 'px' for v in src['viewports'])},
in {', '.join(src['schemes'])} mode. It is a record of what that site does, not a claim about what
this project should do.{measured_note}

Not affiliated with or endorsed by the owner of that site. Trademarks, logos, fonts and photographs
belong to their owners and are not reproduced here.

## Overview

A system of {len(roles)} colour roles and {len(scale['slots'])} type steps on a
{tokens['spacing']['base']}px spacing grid
({tokens['spacing']['coverage']:.0%} of measured spacing values sit on it).
{'The type steps are uniform at a ratio of ' + str(scale['ratio']) + (', a ' + scale['nearestInterval'] + '.' if scale['nearestInterval'] else '.') if scale['uniform'] else 'The type steps are not uniform, so no single ratio describes the scale.'}

## Colors

| Token | Hex | OKLCH | Evidence |
|---|---|---|---|
{colour_rows}

Share is painted area for grounds and characters for text, so a one-pixel border repeated on four
hundred rows does not outvote a hero.

### Contrast

| Pair | Ratio | WCAG |
|---|---|---|
{contrast_rows}

## Typography

| Token | Family | Desktop | Mobile | Weight | Line height | Tracking |
|---|---|---|---|---|---|---|
{type_rows}

Font files are named, never copied. Where a family is not available, name a substitute explicitly
rather than letting the stack fall through silently.

## Layout

- Container: {tokens['layout']['container'] or '—'}px
- Spacing base: {tokens['spacing']['base'] or '—'}px — scale {', '.join(str(int(v)) for v in tokens['spacing']['onGrid'][:8])}
- Breakpoints: {bps}

## Elevation & Depth

{chr(10).join('- `' + s + '`' for s in tokens['shadows']) or '- No box-shadow was observed.'}

## Shapes

- Default radius: {tokens['radius']['default'] or '—'}px
- Pill shape in use: {'yes' if tokens['radius']['pill'] else 'no'}

## Motion

{motion_block}

## Components

{components_block}

## Voice and tone

{voice_block}

## Do's and Don'ts

- **Do** treat every value here as a starting point with a date on it, not as a target.
- **Do** record what you changed and why, in `design-source.md` beside this file.
- **Don't** ship this system unchanged. It is somebody else's, and a measurement does not transfer
  the right to use it.
- **Don't** fill in a slot listed below as not observed. A value nobody measured, sitting in a
  measured file, is indistinguishable from one that was.

## Not observed

{missing}

## Method and limits

{notes}

Computed styles were read from the rendered DOM, not from the authored stylesheet: a stylesheet
declares what is possible, the DOM says what is painted.
"""


def divergence(measured, final, name):
    """The record of the conversation, written once, at the moment of the decision."""
    rows, changed = [], 0

    def add(key, a, b, note=""):
        nonlocal changed
        same = str(a) == str(b)
        if not same:
            changed += 1
        rows.append(f"| `{key}` | `{a}` | `{b}` | {'kept' if same else '**changed**'} | {note} |")

    for role, data in final["color"]["roles"].items():
        before = measured["color"]["roles"].get(role, {}).get("value", "—")
        # The reason lives on the token, written when the decision was taken. Carrying it across is
        # the difference between a diff and a record.
        why = data.get("why", "") if str(before) != str(data["value"]) else ""
        add(f"color.{role}", before, data["value"], why)

    mslots = {s["slot"]: s for s in measured["typography"]["scale"]["slots"]}
    for slot in final["typography"]["scale"]["slots"]:
        m = mslots.get(slot["slot"], {})
        add(f"type.{slot['slot']}", px(m.get("size", "—")), px(slot["size"]))
        # The responsive end is its own decision, and it was invisible here: a run that moved the
        # mobile size from 64 to 52 and left the desktop alone wrote a record saying `kept`. A
        # decision taken and not recorded is the one thing this file exists to prevent.
        if slot.get("mobileSize") or m.get("mobileSize"):
            add(f"type.{slot['slot']} @mobile",
                px(m.get("mobileSize", "—")), px(slot.get("mobileSize", "—")))

    add("spacing.base", px(measured["spacing"]["base"]), px(final["spacing"]["base"]))
    add("radius.default", px(measured["radius"]["default"]), px(final["radius"]["default"]))

    import analyze
    drift = analyze.slop_drift(final, measured)
    drift_block = ""
    if drift:
        lines = "\n".join(f"| `{k}` | {move} | {why} |" for k, move, why in drift)
        drift_block = f"""

## Drift towards the generic — {len(drift)} value(s)

These moved **away from the source and towards the look that AI-generated design keeps landing on**
(`design-md-to-app/references/anti-slop-fallbacks.md` owns the subject). Only drift is listed: a
site that genuinely uses one of these is that site, and saying otherwise would punish an accurate
measurement. Each of these was something else when measured and is now a stock value — which may be
exactly what was wanted, and then this table is the record of choosing it.

| Key | Moved | What it is |
|---|---|---|
{lines}
"""

    return f"""# Where this design came from, and how far we moved

Measured from `{measured['source']['origin']}` on {measured['source']['pageCount']} page(s),
{measured['source']['viewports']}.

This file is the record of one conversation. Nothing downstream reads it: `design-md-to-app` reads
`DESIGN.md`, which carries one value per key, as a spec must. This exists for the person who comes
back in two months, looks at a number, and cannot tell a decision from a slip.

**{changed} of {len(rows)} values were changed.** A row marked *kept* is also a decision — it says
somebody looked at it and left it, which is not the same as nobody looking.

| Key | Measured | Ours | | Why |
|---|---|---|---|---|
{chr(10).join(rows)}

{drift_block}
## The part a table cannot hold

Write here, in prose, what you were trying to get away from and what you were trying to keep. The
numbers above record *what* moved; this is the only place that records *why* — and in a dispute
about whether this design is someone else's, it is the paragraph that matters.

> _(to be written at the moment of the decision, not later)_
"""


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("tokens", type=Path)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--measured", type=Path, default=None,
                    help="the untouched tokens.json from the first run, for the divergence record")
    ap.add_argument("--name", default=None)
    args = ap.parse_args(argv)

    final = json.loads(args.tokens.read_text(encoding="utf-8"))
    origin = final["source"]["origin"] or "measured-system"
    name = args.name or origin.split("//")[-1].split("/")[0]

    args.out.mkdir(parents=True, exist_ok=True)
    note = ""
    if args.measured:
        measured = json.loads(args.measured.read_text(encoding="utf-8"))
        path = args.out / "design-source.md"
        path.write_text(divergence(measured, final, name), encoding="utf-8")
        note = ("\n\nWhat was measured and what we chose differ; the record of every difference is "
                "in `design-source.md` beside this file.")
        print(f"design-source.md written -> {path}")
    else:
        print("no --measured given: no divergence record was written. "
              "A DESIGN.md with no record of what moved cannot be told from a clone.")

    design = args.out / "DESIGN.md"
    design.write_text(frontmatter(final, name) + body(final, name, note), encoding="utf-8")
    print(f"DESIGN.md written -> {design} ({design.stat().st_size / 1024:.1f} KB)")
    if final["missing"]:
        print(f"  not observed and therefore not written: {len(final['missing'])} slot(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
