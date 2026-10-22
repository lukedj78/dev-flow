#!/usr/bin/env python3
"""The run log (gist §9): what was read, what it cost, and every assumption.

A measurement without its conditions is an opinion with numbers in it. Six months from now the
question about this DESIGN.md will not be "what does it say" — that is in the file — but "what was
the site like when you read it, how much of it did you see, and what did you have to assume".

Nothing here is computed twice: it is assembled from the snapshots, the tokens and whatever the
output directory already holds.

    run_log.py --out <dir> [--started <iso>] [--note "..."]
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path


def human_bytes(n):
    return f"{n / 1024:.0f} KB" if n < 1024 * 1024 else f"{n / 1024 / 1024:.1f} MB"


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--started", default=None, help="ISO timestamp the run began")
    ap.add_argument("--note", action="append", default=[],
                    help="anything a person decided that the files cannot show; repeatable")
    ap.add_argument("--image-cost", type=float, default=0.0)
    args = ap.parse_args(argv)

    snaps = []
    for p in sorted(args.out.glob("snapshot-*.json")):
        try:
            snaps.append((p, json.loads(p.read_text(encoding="utf-8"))))
        except (OSError, json.JSONDecodeError):
            continue
    if not snaps:
        print(f"no snapshots in {args.out}", file=__import__("sys").stderr)
        return 2

    tokens = {}
    tp = args.out / "tokens.json"
    if tp.is_file():
        tokens = json.loads(tp.read_text(encoding="utf-8"))

    first = snaps[0][1]
    captured = sorted(s.get("capturedAt", "") for _, s in snaps)
    elements = sum(s["counts"]["visible"] for _, s in snaps)
    skipped = sum(s["counts"]["skippedConsent"] for _, s in snaps)
    hidden = sum(s["counts"]["skippedHidden"] for _, s in snaps)
    opaque = sum(s.get("declared", {}).get("opaqueSheets", 0) for _, s in snaps)
    sheets = sum(s.get("declared", {}).get("sheets", 0) for _, s in snaps)
    focused = sum(1 for _, s in snaps if s.get("documentHasFocus"))

    rows = "\n".join(
        f"| `{s.get('path') or '/'}` | {s['viewport']['width']}×{s['viewport']['height']} | "
        f"{s.get('colorScheme')} | {s['counts']['visible']} | "
        f"{s['counts']['skippedConsent']} | "
        f"{s.get('declared', {}).get('opaqueSheets', 0)}/{s.get('declared', {}).get('sheets', 0)} | "
        f"{'yes' if s.get('documentHasFocus') else '**no**'} | {human_bytes(p.stat().st_size)} |"
        for p, s in snaps)

    artefacts = []
    for name in ("tokens.json", "tokens.css", "shadcn.css", "tokens.dtcg.json",
                 "brand-guide.html", "brand-guide-hero.html", "DESIGN.md",
                 "design-source.md", "prompts.json", "media.html"):
        f = args.out / name
        if f.is_file():
            artefacts.append(f"| `{name}` | {human_bytes(f.stat().st_size)} |")
    slides = list(args.out.glob("slide-*.png"))
    if slides:
        artefacts.append(f"| `slide-*.png` | {len(slides)} files, "
                         f"{human_bytes(sum(s.stat().st_size for s in slides))} |")
    images = list((args.out / "images").glob("*.webp")) if (args.out / "images").is_dir() else []
    if images:
        artefacts.append(f"| `images/*.webp` | {len(images)} files, "
                         f"{human_bytes(sum(i.stat().st_size for i in images))} |")

    notes = {n for _, s in snaps for n in s.get("notes", [])}
    missing = tokens.get("missing", [])
    questions = tokens.get("questions", [])

    assumed = [
        "Pages were chosen by the user, not scored automatically — a page nobody opened is a page "
        "this system does not describe.",
        f"Viewports: {', '.join(str(v) + 'px' for v in sorted({s['viewport']['width'] for _, s in snaps}))}. "
        "Anything between them is interpolated by the `clamp()`, not measured.",
        f"Colour schemes read: {', '.join(sorted({s.get('colorScheme', '?') for _, s in snaps}))}.",
    ]
    if opaque:
        assumed.append(
            f"{opaque} of {sheets} stylesheets were cross-origin, so custom-property names, "
            f"`@media` breakpoints and `@font-face` sources from those were not readable. The "
            f"computed values were — that part is unaffected.")
    if focused < len(snaps):
        assumed.append(
            f"{len(snaps) - focused} capture(s) ran without document focus, so their focus states "
            f"were deliberately not written rather than recorded as absent.")
    if skipped:
        assumed.append(f"{skipped} element(s) were excluded as consent UI — a third party's design "
                       f"sitting on the brand's.")
    assumed += list(args.note)

    started = args.started or (captured[0] if captured else "—")
    log = f"""# Run log

**Source**: `{first.get('origin')}` · **mode**: `{first.get('mode')}`
**Started**: {started} · **Last capture**: {captured[-1] if captured else '—'}
**Written**: {datetime.now(timezone.utc).isoformat(timespec='seconds')}

## What was read

| Page | Viewport | Scheme | Visible elements | Consent excluded | Opaque sheets | Focus | Snapshot |
|---|---|---|---|---|---|---|---|
{rows}

{len(snaps)} capture(s), **{elements} visible elements** in total ({hidden} skipped as hidden,
{skipped} as consent UI).

## What came out

| Artefact | Size |
|---|---|
{chr(10).join(artefacts) or '| — | nothing written yet |'}

{'**Image spend this run: ' + f'{args.image_cost:.2f}' + '**' if args.image_cost else
 'No images were generated (the gradient fallbacks are the design).'}

## What was assumed

{chr(10).join('- ' + a for a in assumed)}

## What the measurement could not see

{chr(10).join('- ' + n for n in sorted(notes)) or '- Nothing was reported.'}

## What was not observed, and therefore not written

{chr(10).join('- ' + m for m in missing) or '- Nothing.'}

## What still needed a decision

{chr(10).join(f"- [{q['kind']}] {q['question']}" for q in questions) or
 '- The measurement raised nothing that needed one.'}

---

A measurement without its conditions is an opinion with numbers in it. The question six months from
now is not what this system says — that is in the DESIGN.md — but how much of the site was seen,
and what had to be taken on trust.
"""
    target = args.out / "run-log.md"
    target.write_text(log, encoding="utf-8")
    print(f"{target}  ({len(snaps)} capture(s), {elements} elements, "
          f"{len(missing)} slot(s) unobserved, {len(questions)} open question(s))")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
