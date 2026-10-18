#!/usr/bin/env python3
"""fake_ingest.py — a local stand-in for Sentry's ingest, to prove events leave the app without an account.

    python3 fake_ingest.py serve --port 9010 --out .verification/ingest   # DSN: http://public@localhost:9010/1
    python3 fake_ingest.py summary .verification/ingest

`serve` accepts the two routes the Sentry SDKs post to — `POST /api/<project>/envelope/` and `/api/<project>/store/`
— decodes gzip/deflate bodies (the Node SDK compresses), and writes each event as one JSON file. `summary` counts
them and says which releases they carry and whether any email address or Authorization value got through: the two
things the module promises (release correlation, nothing personal by default).

It answers 200 to everything it can parse and stores nothing else. Local only: it binds 127.0.0.1. Stdlib only.
"""

from __future__ import annotations

import argparse
import gzip
import json
import re
import sys
import zlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
AUTHORIZATION = re.compile(r'"authorization"\s*:\s*"[^"]+', re.I)


def decode(body: bytes, encoding: str | None) -> bytes:
    enc = (encoding or "").lower()
    if enc == "gzip" or body[:2] == b"\x1f\x8b":
        return gzip.decompress(body)
    if enc == "deflate":
        try:
            return zlib.decompress(body)
        except zlib.error:
            return zlib.decompress(body, -zlib.MAX_WBITS)
    return body


def parse_envelope(body: bytes) -> list[dict]:
    """The event and transaction payloads of a Sentry envelope: a header line, then items, each an item-header line
    and a payload of `length` bytes (or up to the next newline when no length is given)."""
    out = []
    pos = body.find(b"\n")
    if pos < 0:
        return out
    pos += 1
    while pos < len(body):
        end = body.find(b"\n", pos)
        end = len(body) if end < 0 else end
        try:
            item = json.loads(body[pos:end] or b"{}")
        except ValueError:
            break
        pos = end + 1
        length = item.get("length")
        if length is None:
            stop = body.find(b"\n", pos)
            stop = len(body) if stop < 0 else stop
        else:
            stop = pos + int(length)
        payload, pos = body[pos:stop], stop + 1
        if item.get("type") in ("event", "transaction"):
            try:
                out.append(json.loads(payload))
            except ValueError:
                pass
    return out


def make_server(port: int, out: Path) -> ThreadingHTTPServer:
    out.mkdir(parents=True, exist_ok=True)

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self) -> None:   # noqa: N802
            raw = self.rfile.read(int(self.headers.get("Content-Length") or 0))
            try:
                body = decode(raw, self.headers.get("Content-Encoding"))
                events = parse_envelope(body) if "/envelope" in self.path else [json.loads(body)]
            except (OSError, ValueError, zlib.error):
                events = []
            for ev in events:
                name = f"{ev.get('event_id') or len(list(out.glob('*.json')))}.json"
                (out / name).write_text(json.dumps(ev, indent=1), encoding="utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b"{}")

        def log_message(self, *args) -> None:   # quiet
            pass

    return ThreadingHTTPServer(("127.0.0.1", port), Handler)


def summary(out: Path) -> dict:
    events = [json.loads(p.read_text(encoding="utf-8")) for p in sorted(out.glob("*.json"))]
    text = "\n".join(json.dumps(e) for e in events)
    return {
        "events": len(events),
        "releases": sorted({str(e.get("release")) for e in events if e.get("release")}),
        "levels": sorted({str(e.get("level")) for e in events if e.get("level")}),
        "messages": [((e.get("exception") or {}).get("values") or [{}])[-1].get("value") or e.get("message") for e in events],
        "emails": bool(EMAIL.search(text)),
        "authorization": bool(AUTHORIZATION.search(text)),
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="op", required=True)
    s = sub.add_parser("serve")
    s.add_argument("--port", type=int, default=9010)
    s.add_argument("--out", type=Path, default=Path(".verification/ingest"))
    m = sub.add_parser("summary")
    m.add_argument("out", type=Path)
    a = ap.parse_args(argv)
    if a.op == "serve":
        server = make_server(a.port, a.out)
        print(f"fake ingest on http://127.0.0.1:{a.port} — DSN http://public@localhost:{a.port}/1 — events in {a.out}")
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass
        return 0
    print(json.dumps(summary(a.out), indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
