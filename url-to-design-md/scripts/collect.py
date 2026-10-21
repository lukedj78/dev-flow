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
import secrets
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

    # send_error's second argument is the HTTP STATUS LINE, which must encode as latin-1. An em
    # dash in it raises inside the handler, the connection dies, and a refusal looks like a crash —
    # measured here on 2026-10-21. Reason phrases stay short and ASCII; the prose goes in `explain`.
    def _drain(self):
        """Read and discard the body before refusing.

        Replying before the client has finished sending resets the connection, and curl reports
        `000` — which reads as "the server is down", not "the request was refused". A rejection
        must look like a rejection.
        """
        try:
            length = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            return
        remaining = min(length, MAX_ASSET_BODY)
        while remaining > 0:
            chunk = self.rfile.read(min(65536, remaining))
            if not chunk:
                break
            remaining -= len(chunk)

    def _authorised(self) -> bool:
        """Three gates, because a loopback socket is not a boundary.

        Any page the browser has open can POST to 127.0.0.1 — that is what CORS is for, and a
        wildcard turns it off. So: a per-run secret in the path, which a page that was not handed
        the URL cannot guess; an Origin that is echoed back only when the secret checked out,
        never `*`; and a Host that must be loopback, which is what stops a DNS-rebinding page from
        reaching this socket under its own origin.
        """
        host = (self.headers.get("Host") or "").split(":")[0]
        if host not in ("127.0.0.1", "localhost", "[::1]", "::1"):
            self._drain()
            self.send_error(403, "Forbidden", "this collector answers on loopback only")
            return False
        want = f"/collect/{self.token}"
        if not secrets.compare_digest(self.path.rstrip("/"), want):
            self._drain()
            self.send_error(404, "Not Found",
                            "the collect URL carries this run's token")
            return False
        return True

    def do_POST(self):                                    # noqa: N802 (http.server's spelling)
        if not self._authorised():
            return
        try:
            length = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            self.send_error(411, "Length Required", "Content-Length is required")
            return
        if length <= 0 or length > MAX_ASSET_BODY:
            self.send_error(413, "Payload Too Large", f"body must be 1..{MAX_ASSET_BODY} bytes")
            return

        raw = self.rfile.read(length)
        try:
            snapshot = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as e:
            self.send_error(400, "Bad Request", f"not JSON: {e}")
            return
        if not isinstance(snapshot, dict) or snapshot.get("schema") != SCHEMA:
            self.send_error(422, "Unprocessable Content", f"not a snapshot of schema {SCHEMA}")
            return

        if snapshot.get("kind") == "asset":
            self._write_asset(snapshot, len(raw))
            return
        if length > MAX_BODY:
            self.send_error(413, "Payload Too Large", f"a JSON snapshot must be 1..{MAX_BODY} bytes")
            return

        target = self.out_dir / safe_name(snapshot)
        # resolve() then check containment: belt and braces against a name that escapes --out
        if self.out_dir.resolve() not in target.resolve().parents:
            self.send_error(400, "Bad Request", "refusing to write outside --out")
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
            self.send_error(422, "Unprocessable Content", f"format must be one of {sorted(ASSET_KINDS)}")
            return
        label = SAFE.sub("-", str(payload.get("label") or "asset"))[:48].strip("-") or "asset"
        try:
            blob = base64.b64decode(payload.get("data") or "", validate=True)
        except (binascii.Error, ValueError) as e:
            self.send_error(400, "Bad Request", f"data is not base64: {e}")
            return
        if not blob:
            self.send_error(422, "Unprocessable Content", "empty asset")
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
        if not self._authorised():
            return
        self.send_response(204)
        self._cors()
        self.end_headers()

    def _cors(self):
        # Echo the caller's origin, never `*`, and only from a request that already proved it knows
        # this run's token. The page needs a dev server on another port to be able to POST; it does
        # not need every page on the machine to be able to.
        origin = self.headers.get("Origin")
        if origin:
            self.send_header("Access-Control-Allow-Origin", origin)
            self.send_header("Vary", "Origin")
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
    ap.add_argument("--token", default=None,
                    help="reuse a token instead of generating one (for a scripted re-run)")
    args = ap.parse_args(argv)

    args.out.mkdir(parents=True, exist_ok=True)
    serve_dir = (args.serve or args.out).resolve()

    Collector.out_dir = args.out.resolve()
    Collector.written = []
    Collector.token = args.token or secrets.token_urlsafe(24)

    def build(*a, **kw):
        return Collector(*a, directory=str(serve_dir), **kw)

    server = ThreadingHTTPServer(("127.0.0.1", args.port), build)
    collect_url = f"http://127.0.0.1:{args.port}/collect/{Collector.token}"
    print(f"collect URL (pass this to extract.js as `collect`):\n  {collect_url}", flush=True)
    print(f"writing to {args.out}", flush=True)
    print(f"serving {serve_dir}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print(f"\nstopped after {len(Collector.written)} snapshot(s)", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
