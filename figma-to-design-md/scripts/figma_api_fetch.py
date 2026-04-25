#!/usr/bin/env python3
"""Fetch sections of a Figma file via the REST API and print JSON to stdout.

Reads the personal access token from the FIGMA_ACCESS_TOKEN environment
variable. Use with the figma-to-design-md skill.

Usage:
    python3 figma_api_fetch.py <FILE_KEY> --section <section> [--node-id <id>]

Sections:
    meta        File metadata (name, lastModified, version)
    styles      Color/text/effect/grid styles (metadata only)
    variables   Local variables and modes — most useful for tokens
    components  Components in the file
    componentsets  Component sets (variant groups)
    file        Whole document tree (large; prefer node-id)
    node        Subtree for a specific node-id (requires --node-id)
    image       Render a node as PNG; prints the temporary URL

Exit codes:
    0 on success, 1 on missing token / bad args, 2 on HTTP error.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

API_BASE = "https://api.figma.com/v1"


def fetch(path: str, token: str, params: dict | None = None) -> dict:
    url = f"{API_BASE}{path}"
    if params:
        url += "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"X-Figma-Token": token})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        sys.stderr.write(f"HTTP {e.code} on {url}\n{body}\n")
        sys.exit(2)
    except urllib.error.URLError as e:
        sys.stderr.write(f"Network error: {e.reason}\n")
        sys.exit(2)


def section_meta(file_key: str, token: str) -> dict:
    full = fetch(f"/files/{file_key}", token, {"depth": 1})
    return {
        "name": full.get("name"),
        "lastModified": full.get("lastModified"),
        "version": full.get("version"),
        "role": full.get("role"),
        "editorType": full.get("editorType"),
    }


def section_styles(file_key: str, token: str) -> dict:
    return fetch(f"/files/{file_key}/styles", token)


def section_variables(file_key: str, token: str) -> dict:
    return fetch(f"/files/{file_key}/variables/local", token)


def section_components(file_key: str, token: str) -> dict:
    return fetch(f"/files/{file_key}/components", token)


def section_component_sets(file_key: str, token: str) -> dict:
    return fetch(f"/files/{file_key}/component_sets", token)


def section_file(file_key: str, token: str) -> dict:
    return fetch(f"/files/{file_key}", token)


def section_node(file_key: str, token: str, node_id: str) -> dict:
    return fetch(f"/files/{file_key}/nodes", token, {"ids": node_id})


def section_image(file_key: str, token: str, node_id: str, scale: float = 2.0) -> dict:
    return fetch(
        f"/images/{file_key}",
        token,
        {"ids": node_id, "format": "png", "scale": str(scale)},
    )


SECTIONS = {
    "meta": lambda k, t, n: section_meta(k, t),
    "styles": lambda k, t, n: section_styles(k, t),
    "variables": lambda k, t, n: section_variables(k, t),
    "components": lambda k, t, n: section_components(k, t),
    "componentsets": lambda k, t, n: section_component_sets(k, t),
    "file": lambda k, t, n: section_file(k, t),
    "node": lambda k, t, n: section_node(k, t, n),
    "image": lambda k, t, n: section_image(k, t, n),
}


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch sections of a Figma file.")
    parser.add_argument("file_key", help="Figma file key (from the URL)")
    parser.add_argument(
        "--section",
        required=True,
        choices=sorted(SECTIONS.keys()),
        help="Which slice of the file to fetch",
    )
    parser.add_argument(
        "--node-id",
        default=None,
        help="Node ID, required for --section node and --section image",
    )
    parser.add_argument(
        "--pretty",
        action="store_true",
        help="Pretty-print JSON (default: compact)",
    )
    args = parser.parse_args()

    token = os.environ.get("FIGMA_ACCESS_TOKEN")
    if not token:
        sys.stderr.write(
            "FIGMA_ACCESS_TOKEN not set. Generate one at "
            "https://www.figma.com/developers/api#access-tokens\n"
        )
        sys.exit(1)

    if args.section in {"node", "image"} and not args.node_id:
        sys.stderr.write(f"--node-id is required for --section {args.section}\n")
        sys.exit(1)

    handler = SECTIONS[args.section]
    result = handler(args.file_key, token, args.node_id)

    if args.pretty:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
