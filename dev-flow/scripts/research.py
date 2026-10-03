#!/usr/bin/env python3
"""The outside half of the inventory step: has somebody already built this, and what broke for them.

    research.py status
    research.py repos   <query> [--min-stars 20] [--limit 10]
    research.py reddit  <query> [--sub <name>] [--limit 10]
    research.py thread  <url>  [--limit 40]
    research.py hn      <query> [--min-points 50] [--limit 10]
    research.py post    <url>
    research.py read    <url>  [--chars 12000]
    research.py papers  <query> [--limit 8]

`references/before-you-build.md` step 4 is the method; this is the four commands of it that a
`WebSearch` does badly — a whole Reddit thread, an X post, a paper's abstract, a page as clean
markdown. GitHub goes through `gh`, which the user already has authenticated.

Stdlib only. No API key, no account, nothing written to disk. Reads only: every call is a GET.

## The two rules it enforces, which is why it exists rather than a copied script

**It never turns "I could not look" into "there is nothing".** Each command exits **0** when the
channel answered, **3** when it answered and had nothing, and **4** when it could not be reached —
and `before-you-build.md` says an unreachable channel is written into the PRD as *not covered*. A
search tool that returns an empty list on a 429 is the same bug as a QA check that reports `pass`
when the decode failed: it converts ignorance into a fact.

**It refuses to send an internal address to a third party.** `read` renders a page through
`r.jina.ai`, which means the URL and the page reach a company that is not us. A client's internal
host must never go there, so loopback, the private IPv4 ranges, and the `.local`/`.internal`/`.test`
suffixes are refused outright — `--force` does not override them, because the mistake it would
enable is the one that cannot be taken back.

Written for dev-flow rather than borrowed: the method is adapted from `piano` (Martes AI, recorded
in `references/resources.md`), the code is ours, because that skill ships with no licence and its
text could not enter a repository we deliver.
"""

from __future__ import annotations

import argparse
import ipaddress
import json
import re
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

UA = "dev-flow-research/1.0 (+https://github.com/lukedj78/dev-flow)"
TIMEOUT = 25

ANSWERED, EMPTY, UNREACHABLE = 0, 3, 4

# A reader proxy is a third party. These never reach one, and `--force` does not reach them either.
PRIVATE_SUFFIXES = (".local", ".internal", ".test", ".localhost", ".lan", ".home.arpa")


def get(url: str, accept: str = "application/json") -> tuple[int, str]:
    """(status, body). status 0 means the request itself never completed."""
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": accept})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:  # noqa: S310 — https, fixed hosts
            return r.status, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, ""
    except Exception:  # noqa: BLE001 — DNS, TLS, timeout: all "could not look"
        return 0, ""


def unreachable(channel: str, status: int) -> int:
    why = {0: "no answer (DNS, TLS or timeout)", 429: "rate-limited (429)"}.get(status, f"HTTP {status}")
    print(f"{channel}: could not look — {why}.")
    print("  Write it into the plan as a channel not covered. It is not the same as finding nothing.")
    return UNREACHABLE


def nothing(channel: str, query: str) -> int:
    print(f"{channel}: answered, nothing matched {query!r}. Try other words before concluding.")
    return EMPTY


def is_internal(url: str) -> str | None:
    """The reason this host must not be handed to a third party, or None."""
    host = (urllib.parse.urlparse(url).hostname or "").lower()
    if not host:
        return "no hostname"
    if host == "localhost" or host.endswith(PRIVATE_SUFFIXES):
        return f"{host} is a local or internal name"
    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        return None
    if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved:
        return f"{host} is a private address"
    return None


def freshness(iso_day: str) -> str:
    """A repo stopped a year ago is read for the idea, not adopted."""
    try:
        age = (time.time() - time.mktime(time.strptime(iso_day, "%Y-%m-%d"))) / 86400
    except ValueError:
        return "unknown"
    return "alive" if age < 90 else ("warm" if age < 365 else "stopped")


# ---------------------------------------------------------------------------------------------
# the channels


def cmd_repos(a) -> int:
    if not shutil.which("gh"):
        print("gh is not installed. `brew install gh && gh auth login`, or search by hand:")
        print(f"  site:github.com {a.query}")
        return UNREACHABLE
    out = subprocess.run(
        ["gh", "search", "repos", a.query, "--sort", "stars", "--limit", str(a.limit),
         "--stars", f">={a.min_stars}",
         "--json", "fullName,description,stargazersCount,pushedAt,license,url"],
        capture_output=True, text=True, timeout=90,
    )
    if out.returncode != 0:
        print(f"github: could not look — gh failed: {out.stderr.strip()[:300]}")
        return UNREACHABLE
    repos = json.loads(out.stdout or "[]")
    if not repos:
        return nothing("github", a.query)
    for r in repos:
        day = (r.get("pushedAt") or "")[:10]
        lic = (r.get("license") or {}).get("key") or "no licence"
        print(f"- {r['fullName']} | {r['stargazersCount']} stars | pushed {day} ({freshness(day)}) | {lic}")
        print(f"  {r['url']}")
        if r.get("description"):
            print(f"  {r['description'][:200]}")
    return ANSWERED


def cmd_reddit(a) -> int:
    q = {"q": a.query, "size": str(a.limit), "sort": "desc", "sort_type": "score"}
    if a.sub:
        q["subreddit"] = a.sub
    status, body = get("https://api.pullpush.io/reddit/search/submission/?" + urllib.parse.urlencode(q))
    if status != 200:
        return unreachable("reddit", status)
    posts = (json.loads(body) or {}).get("data") or []
    if not posts:
        return nothing("reddit", a.query)
    for p in posts:
        print(f"- [{p.get('score', 0)}↑ {p.get('num_comments', 0)} comments] r/{p.get('subreddit')} — {p.get('title', '')[:140]}")
        print(f"  https://www.reddit.com{p.get('permalink', '')}")
    print("\nThe post is the success story; the comments are the rest. Open the thread.")
    return ANSWERED


def cmd_thread(a) -> int:
    m = re.search(r"/comments/([a-z0-9]+)", a.url)
    if not m:
        print("thread: that is not a Reddit thread URL (expected /comments/<id>/).")
        return UNREACHABLE
    status, body = get(f"https://api.pullpush.io/reddit/search/comment/?link_id=t3_{m.group(1)}&size={a.limit}&sort=desc&sort_type=score")
    if status != 200:
        return unreachable("reddit", status)
    comments = (json.loads(body) or {}).get("data") or []
    if not comments:
        return nothing("reddit thread", a.url)
    for c in comments:
        text = re.sub(r"\s+", " ", c.get("body") or "").strip()
        print(f"- [{c.get('score', 0)}↑] {text[:420]}")
    return ANSWERED


def cmd_hn(a) -> int:
    url = ("https://hn.algolia.com/api/v1/search?" +
           urllib.parse.urlencode({"query": a.query, "hitsPerPage": str(a.limit),
                                   "numericFilters": f"points>={a.min_points}"}))
    status, body = get(url)
    if status != 200:
        return unreachable("hacker news", status)
    hits = (json.loads(body) or {}).get("hits") or []
    if not hits:
        return nothing("hacker news", a.query)
    for h in hits:
        print(f"- [{h.get('points', 0)} points, {h.get('num_comments', 0)} comments] {(h.get('title') or '')[:140]}")
        if h.get("url"):
            print(f"  {h['url']}")
        print(f"  https://news.ycombinator.com/item?id={h.get('objectID')}")
    return ANSWERED


def cmd_post(a) -> int:
    m = re.search(r"(?:twitter|x)\.com/[^/]+/status/(\d+)", a.url)
    if not m:
        print("post: that is not an X post URL (expected /status/<id>).")
        return UNREACHABLE
    status, body = get(f"https://api.fxtwitter.com/status/{m.group(1)}")
    if status != 200:
        return unreachable("x", status)
    t = (json.loads(body) or {}).get("tweet") or {}
    if not t:
        return nothing("x", a.url)
    author = (t.get("author") or {}).get("screen_name", "?")
    print(f"@{author} · {t.get('created_at', '')}")
    print(re.sub(r"\n{3,}", "\n\n", t.get("text") or ""))
    print(f"\n{t.get('likes', 0)} likes · {t.get('replies', 0)} replies · {t.get('retweets', 0)} reposts")
    print("A builder saying it works is an experience to verify, not a source.")
    return ANSWERED


def cmd_read(a) -> int:
    if why := is_internal(a.url):
        print(f"read: refused — {why}.")
        print("  This renders the page through r.jina.ai, a third party. An internal address never goes there.")
        print("  Fetch it yourself with WebFetch, or read it in a browser.")
        return UNREACHABLE
    status, body = get("https://r.jina.ai/" + a.url, accept="text/plain")
    if status != 200:
        return unreachable("reader", status)
    if not body.strip():
        return nothing("reader", a.url)
    print(body[:a.chars])
    if len(body) > a.chars:
        print(f"\n… cut at {a.chars} characters of {len(body)}.")
    return ANSWERED


def cmd_papers(a) -> int:
    url = ("https://api.openalex.org/works?" +
           urllib.parse.urlencode({"search": a.query, "per-page": str(a.limit),
                                   # relevance, not citation count: sorting by citations on a
                                   # `search` buries the topic under whatever the field cites most
                                   # (a RAG query came back with SciPy and Quantum Espresso).
                                   "sort": "relevance_score:desc"}))
    status, body = get(url)
    if status != 200:
        return unreachable("openalex", status)
    works = (json.loads(body) or {}).get("results") or []
    if not works:
        return nothing("openalex", a.query)
    for w in works:
        oa = (w.get("open_access") or {}).get("oa_url")
        print(f"- [{w.get('cited_by_count', 0)} citations, {w.get('publication_year', '?')}] {(w.get('title') or '')[:150]}")
        print(f"  {oa or w.get('doi') or w.get('id')}")
    return ANSWERED


# pullpush answers 429 to a very common word and 200 to a selective one, whatever `size` and `Accept`
# say — measured 2026-10-03: `test` and `hello` 429, `tender` and `procurement` 200. A probe on a
# common word reports the channel dead while real searches get through, so it asks a selective one.
REDDIT_PROBE_WORD = "procurement"


def cmd_status(_a) -> int:
    checks = [
        ("github (gh)", None),
        ("reddit (pullpush)", f"https://api.pullpush.io/reddit/search/submission/?q={REDDIT_PROBE_WORD}&size=1"),
        ("x (fxtwitter)", "https://api.fxtwitter.com/status/20"),
        ("hacker news", "https://hn.algolia.com/api/v1/search?query=test&hitsPerPage=1"),
        ("reader (r.jina.ai)", "https://r.jina.ai/https://example.com"),
        ("openalex", "https://api.openalex.org/works?search=test&per-page=1"),
    ]
    dead = 0
    for name, url in checks:
        if url is None:
            if not shutil.which("gh"):
                print(f"  {name:22} not installed")
                dead += 1
                continue
            ok = subprocess.run(["gh", "auth", "status"], capture_output=True, text=True, timeout=30).returncode == 0
            print(f"  {name:22} {'authenticated' if ok else 'installed, not authenticated'}")
            dead += 0 if ok else 1
            continue
        status, _ = get(url, accept="*/*")
        print(f"  {name:22} {'alive' if status == 200 else f'unreachable ({status or 'no answer'})'}")
        dead += 0 if status == 200 else 1
    print("\nThe general web is WebSearch and WebFetch: there is no search engine here, because every")
    print("good one wants a key. A channel that is silent goes into the plan as not covered.")
    return ANSWERED if dead == 0 else EMPTY


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("status")
    s = sub.add_parser("repos"); s.add_argument("query"); s.add_argument("--min-stars", type=int, default=20); s.add_argument("--limit", type=int, default=10)
    s = sub.add_parser("reddit"); s.add_argument("query"); s.add_argument("--sub"); s.add_argument("--limit", type=int, default=10)
    s = sub.add_parser("thread"); s.add_argument("url"); s.add_argument("--limit", type=int, default=40)
    s = sub.add_parser("hn"); s.add_argument("query"); s.add_argument("--min-points", type=int, default=50); s.add_argument("--limit", type=int, default=10)
    s = sub.add_parser("post"); s.add_argument("url")
    s = sub.add_parser("read"); s.add_argument("url"); s.add_argument("--chars", type=int, default=12000)
    s = sub.add_parser("papers"); s.add_argument("query"); s.add_argument("--limit", type=int, default=8)
    args = ap.parse_args(argv)
    return {"status": cmd_status, "repos": cmd_repos, "reddit": cmd_reddit, "thread": cmd_thread,
            "hn": cmd_hn, "post": cmd_post, "read": cmd_read, "papers": cmd_papers}[args.cmd](args)


if __name__ == "__main__":
    sys.exit(main())
