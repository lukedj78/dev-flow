#!/usr/bin/env python3
"""A local collector: the page POSTs its snapshot and it lands on disk.

Why this exists. A browser can get a measurement out of a page in three ways, and two of them are
bad. Returning it to the agent costs ~22 KB of context per page per viewport, which is fine once and
wrong twenty times. Downloading it drops files in someone's ~/Downloads, which is their folder and
not a side effect to take quietly. This is the third way: for any page the browser loads over http —
a local dev server, a preview, the fixtures here — `extract.js` POSTs straight here and the file is
written where it belongs, with nothing passing through the agent and nothing left behind.

It does not work for a remote https page: mixed content forbids that page from reaching a localhost
endpoint, and that is a browser rule, not a gap here. Those pages use the download path, and the
caller moves the file immediately.

    collect.py --out <dir> [--serve <dir>] [--port 8781]

Deliberate limits, because this listens on a socket:
  * binds 127.0.0.1 only, never 0.0.0.0;
  * accepts POST on exactly one path, /collect;
  * refuses a body over 8 MB and anything that is not a JSON object carrying our schema;
  * writes only inside --out, with a name built from the snapshot's own fields, never from a
    client-supplied path. A collector that writes where the request tells it to is a file-write
    primitive on the loopback interface.
"""

from __future__ import annotations

import argparse
import base64
import binascii
import json
import re
import sys
from datetime import datetime, timezone
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

MAX_BODY = 8 * 1024 * 1024
MAX_ASSET_BODY = 96 * 1024 * 1024          # a minute of 1080p60 webm does not fit in 8 MB
SCHEMA = 1
SAFE = re.compile(r"[^A-Za-z0-9._-]+")

# What an asset may be. A collector that writes any extension the client names is a file-drop on the
# loopback interface; this one writes four kinds and nothing else.
ASSET_KINDS = {"png": ".png", "jpeg": ".jpg", "webp": ".webp", "webm": ".webm"}


def safe_name(snapshot) -> str:
    """Build the filename from the snapshot's own fields, scrubbed. Never from the request."""
    if snapshot.get("kind") == "verify":
        width = int(snapshot.get("viewport", {}).get("width") or 0)
        return f"verify-{width}.json"
    host = SAFE.sub("-", str(snapshot.get("origin") or "unknown"))[:60].strip("-")
    path = SAFE.sub("-", str(snapshot.get("path") or "/")).strip("-") or "root"
    mode = "app" if snapshot.get("mode") == "app" else "site"
    width = int(snapshot.get("viewport", {}).get("width") or 0)
    scheme = "dark" if snapshot.get("colorScheme") == "dark" else "light"
    return f"snapshot-{host}-{path[:40]}-{mode}-{scheme}-{width}.json"


class Collector(SimpleHTTPRequestHandler):
    out_dir: Path
    written: list

    def do_POST(self):                                    # noqa: N802 (http.server's spelling)
        if self.path.rstrip("/") != "/collect":
            self.send_error(404, "only /collect accepts a POST")
            return
        try:
            length = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            self.send_error(411, "Content-Length required")
            return
        if length <= 0 or length > MAX_ASSET_BODY:
            self.send_error(413, f"body must be 1..{MAX_ASSET_BODY} bytes")
            return

        raw = self.rfile.read(length)
        try:
            snapshot = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as e:
            self.send_error(400, f"not JSON: {e}")
            return
        if not isinstance(snapshot, dict) or snapshot.get("schema") != SCHEMA:
            self.send_error(422, f"not a snapshot of schema {SCHEMA}")
            return

        if snapshot.get("kind") == "asset":
            self._write_asset(snapshot, len(raw))
            return
        if length > MAX_BODY:
            self.send_error(413, f"a JSON snapshot must be 1..{MAX_BODY} bytes")
            return

        target = self.out_dir / safe_name(snapshot)
        # resolve() then check containment: belt and braces against a name that escapes --out
        if self.out_dir.resolve() not in target.resolve().parents:
            self.send_error(400, "refusing to write outside --out")
            return
        target.write_text(json.dumps(snapshot, indent=2), encoding="utf-8")
        self.written.append(target)

        body = json.dumps({"ok": True, "file": target.name, "bytes": len(raw)}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self._cors()
        self.end_headers()
        self.wfile.write(body)
        stamp = datetime.now(timezone.utc).strftime("%H:%M:%S")
        print(f"[{stamp}] collected {target.name} ({len(raw)} bytes) "
              f"from {snapshot.get('url', '?')}", flush=True)

    def _write_asset(self, payload, raw_len):
        """A slide or a video, base64 in a JSON envelope. The NAME comes from our own allow-list
        and a scrubbed label, never from a client-supplied path or extension."""
        kind = str(payload.get("format") or "").lower()
        if kind not in ASSET_KINDS:
            self.send_error(422, f"format must be one of {sorted(ASSET_KINDS)}")
            return
        label = SAFE.sub("-", str(payload.get("label") or "asset"))[:48].strip("-") or "asset"
        try:
            blob = base64.b64decode(payload.get("data") or "", validate=True)
        except (binascii.Error, ValueError) as e:
            self.send_error(400, f"data is not base64: {e}")
            return
        if not blob:
            self.send_error(422, "empty asset")
            return

        target = self.out_dir / f"{label}{ASSET_KINDS[kind]}"
        if self.out_dir.resolve() not in target.resolve().parents:
            self.send_error(400, "refusing to write outside --out")
            return
        target.write_bytes(blob)
        self.written.append(target)

        body = json.dumps({"ok": True, "file": target.name, "bytes": len(blob)}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self._cors()
        self.end_headers()
        self.wfile.write(body)
        stamp = datetime.now(timezone.utc).strftime("%H:%M:%S")
        print(f"[{stamp}] collected {target.name} ({len(blob) / 1024:.0f} KB)", flush=True)

    def do_OPTIONS(self):                                 # noqa: N802
        self.send_response(204)
        self._cors()
        self.end_headers()

    def _cors(self):
        # Any http origin may POST: the point is to collect from a dev server on another port. It
        # binds to loopback, so "any origin" means any page this machine's browser already has open.
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")

    def log_message(self, fmt, *args):
        pass                                              # the POST handler prints what matters


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", type=Path, required=True, help="where snapshots are written")
    ap.add_argument("--serve", type=Path, default=None,
                    help="also serve this directory over http (for local fixtures or a static page)")
    ap.add_argument("--port", type=int, default=8781)
    args = ap.parse_args(argv)

    args.out.mkdir(parents=True, exist_ok=True)
    serve_dir = (args.serve or args.out).resolve()

    Collector.out_dir = args.out.resolve()
    Collector.written = []

    def build(*a, **kw):
        return Collector(*a, directory=str(serve_dir), **kw)

    server = ThreadingHTTPServer(("127.0.0.1", args.port), build)
    print(f"collector on http://127.0.0.1:{args.port}/collect -> {args.out}", flush=True)
    print(f"serving {serve_dir}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print(f"\nstopped after {len(Collector.written)} snapshot(s)", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
