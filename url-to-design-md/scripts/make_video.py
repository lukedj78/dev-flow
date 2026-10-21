#!/usr/bin/env python3
"""A recorded webm -> an mp4 anyone can play, with the frame accounting printed.

Kept although the scene-engine video was removed on 2026-10-21: this file is about transcoding ANY
browser recording and stating honestly how many frames survived it, which is what the eventual
guide recording will need too. See references/artifacts.md for why the scene video went.

Why this file says more than `ffmpeg -i in.webm out.mp4`:

The browser renders every frame deliberately — `captureStream(0)` emits nothing on its own, and the
engine calls `requestFrame()` once per frame it has drawn. That makes the DRAWING exact. It does not
make the RECORDING exact: MediaRecorder stamps frames with the wall clock, so when the encoder falls
behind, two drawn frames can land on one timestamp and one of them is gone.

Measured 2026-10-21 on a 22-second 1080p clip: 1320 frames drawn, 1173 kept. **11% dropped.**

So this does not claim frame accuracy. It counts what arrived, prints the gap, and transcodes at a
fixed rate so the duration is right. For a deck of eased text and cross-dissolves a dropped frame is
invisible, and that is the honest reason it is acceptable here — not a claim that it did not happen.
If a run ever needs every frame, the path is PNG-per-frame into ffmpeg, and it costs one file per
frame; this does not pretend to be that.

    make_video.py <recording.webm> --out <dir> [--fps 60] [--expected 2700]
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path


def ffprobe(path: Path):
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-count_frames", "-select_streams", "v:0",
         "-show_entries", "stream=codec_name,width,height,nb_read_frames",
         "-show_entries", "format=duration",
         "-of", "json", str(path)],
        capture_output=True, text=True, check=True).stdout
    data = json.loads(out)
    stream = (data.get("streams") or [{}])[0]
    return {
        "codec": stream.get("codec_name"),
        "width": stream.get("width"),
        "height": stream.get("height"),
        "frames": int(stream.get("nb_read_frames") or 0),
        "duration": float((data.get("format") or {}).get("duration") or 0),
    }


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("recording", type=Path)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--fps", type=int, default=60)
    ap.add_argument("--crf", type=int, default=14)
    ap.add_argument("--expected", type=int, default=None,
                    help="frames the engine drew, so the drop can be stated rather than guessed")
    args = ap.parse_args(argv)

    if shutil.which("ffmpeg") is None:
        print("ffmpeg is not on PATH: the webm is still a playable file, "
              "but nothing here can transcode it", file=sys.stderr)
        return 2
    if not args.recording.is_file():
        print(f"{args.recording}: not a file", file=sys.stderr)
        return 2

    before = ffprobe(args.recording)
    args.out.mkdir(parents=True, exist_ok=True)
    target = args.out / (args.recording.stem + ".mp4")

    cmd = [
        "ffmpeg", "-y", "-v", "error",
        "-i", str(args.recording),
        "-r", str(args.fps),
        "-c:v", "libx264", "-preset", "slow", "-crf", str(args.crf),
        "-pix_fmt", "yuv420p",
        "-color_range", "tv", "-colorspace", "bt709",
        "-color_primaries", "bt709", "-color_trc", "bt709",
        "-movflags", "+faststart",
        "-an",
        str(target),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        print(proc.stderr.strip() or "ffmpeg failed", file=sys.stderr)
        return 1

    after = ffprobe(target)
    print(f"recorded : {before['codec']} {before['width']}x{before['height']}  "
          f"{before['frames']} frames  {before['duration']:.2f}s  "
          f"{args.recording.stat().st_size / 1024 / 1024:.1f} MB")
    print(f"written  : h264 {after['width']}x{after['height']}  "
          f"{after['frames']} frames  {after['duration']:.2f}s  "
          f"{target.stat().st_size / 1024 / 1024:.1f} MB  -> {target}")

    if args.expected:
        kept = before["frames"]
        dropped = args.expected - kept
        pct = dropped / args.expected * 100 if args.expected else 0
        verdict = "exact" if dropped <= 0 else f"{dropped} frame(s) dropped by the recorder ({pct:.1f}%)"
        print(f"accounting: {args.expected} drawn, {kept} recorded — {verdict}")
        if pct > 25:
            print("  ⚠ over a quarter of the frames never reached the file. The motion in this clip "
                  "is not what the engine drew: re-record with a lower bitrate or a shorter clip.")
    else:
        print("accounting: --expected not given, so the drop cannot be stated. "
              "A clip whose frame loss is unknown should not be called frame-accurate.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
