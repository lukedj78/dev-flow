#!/usr/bin/env python3
"""The imagery half (gist §5): prompts, three modes, and WebP.

Why a guide needs this at all, measured rather than assumed: on adidas.it — a brand whose pages are
photography with type on top — a guide with no images read as nothing to do with the source, and
that was the first thing the user said on seeing it. Colour and type alone do not carry a brand that
is made of pictures.

**Nothing is ever copied from the measured site.** The source's photographs stay on the source. What
is taken is a *description* of its photography — crop, fill, how much of the page is media, what the
alt text is about — and new subjects are written from that description. The suffix on every prompt
exists to keep letters, logos and screens out of the result, because an AI image carrying a
half-legible wordmark is exactly the thing that turns a measurement into a knock-off.

Three modes, the gist's own:

    none    the default. CSS-gradient fallbacks in every slot; the guide is complete without images.
    manual  print the prompts, the user generates them wherever they like, `--import` picks them up.
    api     a provider adapter, the key from `.env`, never logged, cost printed per image.

    images.py prompts  <tokens.json> --out <dir>
    images.py import   --out <dir> [--from <dir>]
    images.py generate <tokens.json> --out <dir> --provider <name>   # reads the key from .env
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

# The nine slots the guide and the slides have places for. `hero` is the cover; the rest sit at the
# head of a section each. Aspect ratios match where they land, so nothing is cropped twice.
SLOTS = [
    ("hero", "16:9", "the cover: the most characteristic thing in this brand's world"),
    ("horizon", "16:9", "the typography chapter: open space, a long horizon, room for text"),
    ("object", "1:1", "colour: a studio still life, one object, controlled light"),
    ("street", "4:5", "voice and tone: people, unposed, the brand's own register"),
    ("sky", "16:9", "a clean background with almost nothing in it"),
    ("glass", "4:3", "components: orderly material, repeated forms, visible structure"),
    ("grid", "1:1", "layout: something naturally gridded, seen straight on"),
    ("tokens", "16:9", "the tokens chapter: abstract, quiet, no focal point"),
    ("outro", "16:9", "the closing frame: wider, emptier, the subject leaving"),
]

# Appended to every prompt. Without it a generator cheerfully writes a wordmark into the corner.
SUFFIX = ("photorealistic, no text, letters, logos, brand marks, cards or app screens, "
          "no watermarks, no signage")

PROVIDERS = {
    # name: (env var for the key, endpoint, how the body is shaped)
    "openai": ("OPENAI_API_KEY", "https://api.openai.com/v1/images/generations", "openai"),
    "gemini": ("GEMINI_API_KEY",
               "https://generativelanguage.googleapis.com/v1beta/models/"
               "imagen-3.0-generate-002:predict", "gemini"),
    "fal": ("FAL_KEY", "https://fal.run/fal-ai/flux/dev", "fal"),
    "replicate": ("REPLICATE_API_TOKEN", "https://api.replicate.com/v1/predictions", "replicate"),
}


# --------------------------------------------------------------------------- prompts


def describe_photography(tokens):
    """What the measurement knows about the source's pictures, in words a prompt can use."""
    media = tokens.get("mediaSummary") or {}
    facts = []
    ratio = media.get("areaRatio")
    if isinstance(ratio, (int, float)):
        facts.append("media covers about {:.0%} of the page".format(ratio))
    fits = media.get("objectFit") or {}
    if "cover" in fits:
        facts.append("images are cropped to fill, not letterboxed")
    if media.get("fullBleed"):
        facts.append(f"{media['fullBleed']} full-bleed image(s) per page")
    themes = media.get("altThemes") or []
    if themes:
        facts.append("alt text is about: " + ", ".join(themes[:6]))
    return facts


def write_prompts(tokens, out: Path):
    roles = tokens["color"]["roles"]
    palette = ", ".join(r["value"] for r in tokens["color"]["palette"][:4])
    facts = describe_photography(tokens)
    origin = tokens["source"]["origin"] or "the source"

    style = (f"Colour world: {palette}. "
             f"Ground {roles.get('background', {}).get('value', '—')}, "
             f"ink {roles.get('foreground', {}).get('value', '—')}, "
             f"accent {roles.get('primary', {}).get('value', '—')}. ")
    if facts:
        style += "Observed on the source: " + "; ".join(facts) + ". "

    prompts = {
        "$note": ("Written from a DESCRIPTION of the source's photography, never from its images. "
                  "New subjects in a comparable register — nothing here reproduces anything from "
                  f"{origin}."),
        "$style": style,
        "$suffix": SUFFIX,
        "slots": [
            {"slot": slot, "aspectRatio": ratio,
             "prompt": f"{intent}. {style}{SUFFIX}",
             "resolution": "2000x1125" if ratio == "16:9" else "1400x1400",
             "status": "pending"}
            for slot, ratio, intent in SLOTS
        ],
    }
    out.mkdir(parents=True, exist_ok=True)
    path = out / "prompts.json"
    path.write_text(json.dumps(prompts, indent=2), encoding="utf-8")
    return path, prompts


# --------------------------------------------------------------------------- webp


def to_webp(src: Path, dst: Path, wide: bool) -> bool:
    """Re-encode with cwebp, 2000px for wide images and 1400px for the rest, as the gist says.

    ffmpeg is the fallback because a machine that can transcode video can usually do this too; if
    neither is present the file is copied unchanged and said so, rather than silently skipped.
    """
    target = 2000 if wide else 1400
    if shutil.which("cwebp"):
        cmd = ["cwebp", "-quiet", "-q", "82", "-resize", str(target), "0",
               str(src), "-o", str(dst)]
    elif shutil.which("ffmpeg"):
        cmd = ["ffmpeg", "-y", "-v", "error", "-i", str(src),
               "-vf", f"scale='min({target},iw)':-2", "-c:v", "libwebp", "-q:v", "82", str(dst)]
    else:
        shutil.copyfile(src, dst.with_suffix(src.suffix))
        print(f"  {src.name}: neither cwebp nor ffmpeg on PATH — copied as-is, not re-encoded")
        return False
    return subprocess.run(cmd, capture_output=True).returncode == 0


# --------------------------------------------------------------------------- modes


def cmd_prompts(args):
    tokens = json.loads(args.tokens.read_text(encoding="utf-8"))
    path, prompts = write_prompts(tokens, args.out)
    print(f"{path}  ({len(prompts['slots'])} slots)")
    print()
    for s in prompts["slots"]:
        print(f"  [{s['slot']}]  {s['aspectRatio']}  {s['resolution']}")
        print(f"    {s['prompt'][:150]}…")
    print()
    print("manual mode: generate these wherever you like, drop them in "
          f"{args.out / 'images'}/<slot>.png, then run `images.py import --out {args.out}`.")
    return 0


def cmd_import(args):
    src_dir = args.from_dir or (args.out / "images")
    if not src_dir.is_dir():
        print(f"{src_dir}: not a directory — nothing to import", file=sys.stderr)
        return 2
    images = args.out / "images"
    images.mkdir(parents=True, exist_ok=True)
    known = {slot for slot, _, _ in SLOTS}
    manifest, unmatched = [], []

    for path in sorted(src_dir.iterdir()):
        if path.suffix.lower() not in (".png", ".jpg", ".jpeg", ".webp"):
            continue
        slot = path.stem.lower()
        if slot not in known:
            unmatched.append(path.name)
            continue
        ratio = next(r for s, r, _ in SLOTS if s == slot)
        dst = images / f"{slot}.webp"
        ok = to_webp(path, dst, wide=(ratio == "16:9"))
        manifest.append({"slot": slot, "file": dst.name, "source": path.name,
                         "reencoded": ok,
                         "bytes": dst.stat().st_size if dst.exists() else None})
        print(f"  {slot:<9} <- {path.name}  "
              f"{(dst.stat().st_size // 1024) if dst.exists() else '?'} KB")

    (args.out / "images-manifest.json").write_text(
        json.dumps({"images": manifest, "unmatched": unmatched}, indent=2), encoding="utf-8")
    if unmatched:
        # Named, not dropped: a file that did not match a slot would otherwise look like a file
        # that was never there.
        print(f"\n  {len(unmatched)} file(s) matched no slot and were left alone: "
              f"{', '.join(unmatched[:6])}")
        print(f"  slots are: {', '.join(sorted(known))}")
    print(f"\n{len(manifest)} image(s) ready in {images}")
    return 0


def _request(url, body, headers, timeout=180):
    req = urllib.request.Request(url, data=json.dumps(body).encode(), headers=headers)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode())


def cmd_generate(args):
    """The api mode. Deliberately cautious, because this one spends the user's money.

    The key is read from the environment or a `.env` beside the output, never from an argument that
    would land in a shell history, and never printed. Every job id is written to disk BEFORE the
    image is fetched, so a crash cannot lose something already paid for. Cost is printed per image.
    """
    if args.provider not in PROVIDERS:
        print(f"unknown provider; one of {sorted(PROVIDERS)}", file=sys.stderr)
        return 2
    env_var, endpoint, shape = PROVIDERS[args.provider]

    key = os.environ.get(env_var)
    if not key:
        dotenv = args.out / ".env"
        if dotenv.is_file():
            for line in dotenv.read_text(encoding="utf-8").splitlines():
                if line.startswith(env_var + "="):
                    key = line.split("=", 1)[1].strip().strip("'\"")
    if not key:
        print(f"{env_var} is not set. Export it in your own shell or put it in {args.out / '.env'};"
              f" never paste it into chat.", file=sys.stderr)
        return 2

    tokens = json.loads(args.tokens.read_text(encoding="utf-8"))
    prompts_path = args.out / "prompts.json"
    if not prompts_path.is_file():
        prompts_path, _ = write_prompts(tokens, args.out)
    prompts = json.loads(prompts_path.read_text(encoding="utf-8"))

    images = args.out / "images"
    images.mkdir(parents=True, exist_ok=True)
    jobs_path = args.out / "image-jobs.json"
    jobs = json.loads(jobs_path.read_text()) if jobs_path.is_file() else {}

    spent = 0.0
    for slot in prompts["slots"]:
        name = slot["slot"]
        if (images / f"{name}.webp").exists() and not args.force:
            print(f"  {name:<9} already present, skipped")
            continue
        try:
            if shape == "openai":
                body = {"model": args.model or "gpt-image-1", "prompt": slot["prompt"],
                        "size": "1536x1024" if slot["aspectRatio"] == "16:9" else "1024x1024",
                        "n": 1}
                headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
            elif shape == "gemini":
                body = {"instances": [{"prompt": slot["prompt"]}],
                        "parameters": {"sampleCount": 1, "aspectRatio": slot["aspectRatio"]}}
                headers = {"x-goog-api-key": key, "Content-Type": "application/json"}
            elif shape == "fal":
                body = {"prompt": slot["prompt"], "image_size": "landscape_16_9"}
                headers = {"Authorization": f"Key {key}", "Content-Type": "application/json"}
            else:  # replicate
                body = {"version": args.model or "", "input": {"prompt": slot["prompt"]}}
                headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}

            result = _request(endpoint, body, headers)
            # the id goes to disk BEFORE anything is downloaded: a crash must not lose a paid job
            jobs[name] = {"provider": args.provider, "at": time.time(),
                          "id": str(result.get("id") or result.get("request_id") or "")[:120]}
            jobs_path.write_text(json.dumps(jobs, indent=2), encoding="utf-8")

            raw = _extract_image(result)
            if raw is None:
                print(f"  {name:<9} provider returned no image (job recorded in {jobs_path.name})")
                continue
            tmp = images / f"{name}.src"
            tmp.write_bytes(raw)
            to_webp(tmp, images / f"{name}.webp", wide=(slot["aspectRatio"] == "16:9"))
            tmp.unlink(missing_ok=True)
            cost = args.cost_per_image
            spent += cost
            print(f"  {name:<9} written  ({(images / f'{name}.webp').stat().st_size // 1024} KB"
                  + (f", ~{cost:.3f} per image, ~{spent:.2f} so far)" if cost else ")"))
        except (urllib.error.URLError, urllib.error.HTTPError, ValueError, KeyError) as e:
            print(f"  {name:<9} FAILED: {type(e).__name__} {str(e)[:100]}")

    print(f"\nimages in {images}; jobs recorded in {jobs_path.name}")
    if args.cost_per_image:
        print(f"approximate spend this run: {spent:.2f}")
    return 0


def _extract_image(result):
    import base64
    for key in ("data", "predictions", "images", "output"):
        item = result.get(key)
        if isinstance(item, list) and item:
            first = item[0]
            if isinstance(first, dict):
                for b64 in ("b64_json", "bytesBase64Encoded", "image"):
                    if first.get(b64):
                        return base64.b64decode(first[b64])
                if first.get("url"):
                    with urllib.request.urlopen(first["url"], timeout=120) as r:
                        return r.read()
            elif isinstance(first, str) and first.startswith("http"):
                with urllib.request.urlopen(first, timeout=120) as r:
                    return r.read()
    return None


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    p1 = sub.add_parser("prompts", help="write prompts.json from the measurement")
    p1.add_argument("tokens", type=Path)
    p1.add_argument("--out", type=Path, required=True)
    p1.set_defaults(fn=cmd_prompts)

    p2 = sub.add_parser("import", help="pick up images generated elsewhere and re-encode to WebP")
    p2.add_argument("--out", type=Path, required=True)
    p2.add_argument("--from", dest="from_dir", type=Path, default=None)
    p2.set_defaults(fn=cmd_import)

    p3 = sub.add_parser("generate", help="call a provider; the key comes from the environment")
    p3.add_argument("tokens", type=Path)
    p3.add_argument("--out", type=Path, required=True)
    p3.add_argument("--provider", required=True, choices=sorted(PROVIDERS))
    p3.add_argument("--model", default=None)
    p3.add_argument("--cost-per-image", type=float, default=0.0,
                    help="what one image costs on this plan, so the run can print what it spent")
    p3.add_argument("--force", action="store_true")
    p3.set_defaults(fn=cmd_generate)

    args = ap.parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    raise SystemExit(main())
