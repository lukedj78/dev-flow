#!/usr/bin/env python3
"""scan.py — fast first-pass GDPR/AI-Act signal scanner for a project.

Walks a project tree, gathers boolean "signals" (does a control exist?), and
maps them to 9 of the 10 risk-register items (R1-R5, R7-R10). This is a
SIGNAL, not a verdict — the skill's model must verify every reported hit by
reading the code before putting it in the audit report (heuristics
over-report by design; false positives are cheaper than misses here).

R6 (Annex III high-risk classification / DPIA) is deliberately NOT scanned
here — "is this use case high-risk" is a product/legal judgment call, not a
grep-able code signal. Per SKILL.md's Remediate mode, R6 is always a
"flag only" item the model reasons about directly, never something this
script's signals dict resolves for it.

    python3 scan.py <project-root>        # prints JSON findings
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

# --- risk register: which signals mean a control is MISSING (a risk) ---------
# Each check: id, severity, article, title, and a predicate over the signals dict.
CHECKS = [
    ("R1", "H", "Art.15/17/20", "No data export / erasure (DSAR)",
     lambda s: s["has_auth"] and not (s["has_dsar_export"] and s["has_dsar_delete"])),
    ("R2", "H", "Art.6/7 ePrivacy", "No consent / cookie banner",
     lambda s: s["is_web"] and not s["has_consent"]),
    ("R3", "H", "Art.44+", "US default, no EU data residency",
     lambda s: s["has_us_default"] and not s["has_eu_region"]),
    ("R4", "M", "Art.5(1)(e)", "No retention/TTL policy",
     lambda s: (s["has_auth"] or s["has_agent"]) and not s["has_retention_doc"]),
    ("R5", "H", "AI-Act Art.50", "AI surface without AI-transparency disclosure",
     lambda s: s["has_ai_surface"] and not s["has_ai_disclosure"]),
    ("R7", "M", "Art.32", "PII in logs (raw console.error/console.log)",
     lambda s: s["has_raw_log"]),
    ("R8", "M", "Art.28", "No sub-processor register",
     lambda s: (s["has_auth"] or s["has_agent"]) and not s["has_subprocessors_doc"]),
    ("R9", "M", "Art.9", "Special-category data unguarded",
     lambda s: s["has_agent"] and not s["has_art9_guard"]),
    ("R10", "M", "AI-Act Art.5", "Memory/personalization not screened",
     lambda s: s["has_memory"] and not s["has_manip_guard"]),
]

SKIP_DIRS = {"node_modules", ".git", "dist", ".next", ".expo", "build", ".turbo", ".vercel", "ios", "android"}
CODE_SUFFIXES = {".ts", ".tsx", ".js", ".jsx", ".md", ".json", ".sql"}

PATTERNS = {
    "auth": re.compile(r"better-auth|@supabase/supabase-js|firebase/auth|createAuthClient|auth\.users|next-auth", re.I),
    "dsar_export": re.compile(r"export[_ ]?(my|user)?[_ ]?data|exportMyData|data[_-]?export|export_memories|gdpr[_-]?export", re.I),
    "dsar_delete": re.compile(r"delete[_ ]?account|deleteMyAccount|erase[_ ]?all|erase_all_memories|admin\.deleteUser|user\.delete\(", re.I),
    "consent": re.compile(r"cookie[_ -]?consent|CookieConsent|lib/consent|consentGiven|ConsentBanner", re.I),
    "eu_region": re.compile(r"eu-central|eu-west|europe-west|fra1|cdg1|arn1|dub1|region:\s*['\"]eu", re.I),
    "us_default": re.compile(r"iad1|us-east|neon\.tech|sfo1|pdx1", re.I),
    "ai_surface": re.compile(r"useEveAgent|withEve|MessageScroller|gpt-realtime|streamTranscribe|chat-and-typeset|agent/instructions", re.I),
    "ai_disclosure": re.compile(r"you are (chatting|interacting) with an ai|AI[- ]generated|this is an ai|parli con un'?assistente ai|ai[_ ]?disclosure", re.I),
    "raw_log": re.compile(r"console\.error\(\s*e\s*\)|console\.error\(\s*err\b|console\.log\(\s*token\b", re.I),
    "subprocessors_doc": re.compile(r"sub-?processor", re.I),
    "retention_doc": re.compile(r"retention|data[_ ]?retention|ttl policy", re.I),
    "agent": re.compile(r'"agent"\s*:\s*"eve"|defineAgent|eve/tools|agent/agent\.ts', re.I),
    "memory": re.compile(r"memoryStore|remember|list_memories|long-term memory", re.I),
    "art9_guard": re.compile(r"special[_ -]?categor|art\.?\s*9|health.*religion|sensitive data", re.I),
    "manip_guard": re.compile(r"manipulat|behavior[- ]?scoring|not for.*engagement", re.I),
    "web": re.compile(r'"framework"\s*:\s*"(next|monorepo)"|next\.config', re.I),
    "expo": re.compile(r'"framework"\s*:\s*"expo-rn"|expo-router|nativewind', re.I),
}


def scan(root: Path) -> dict:
    hits = {k: False for k in PATTERNS}
    for p in root.rglob("*"):
        if p.is_dir() or any(part in SKIP_DIRS for part in p.parts):
            continue
        if p.suffix not in CODE_SUFFIXES:
            continue
        try:
            text = p.read_text(errors="ignore")
        except OSError:
            continue
        for k, rx in PATTERNS.items():
            if not hits[k] and rx.search(text):
                hits[k] = True
    return {
        "has_auth": hits["auth"], "has_dsar_export": hits["dsar_export"], "has_dsar_delete": hits["dsar_delete"],
        "has_consent": hits["consent"], "has_eu_region": hits["eu_region"], "has_us_default": hits["us_default"],
        "has_ai_surface": hits["ai_surface"], "has_ai_disclosure": hits["ai_disclosure"], "has_raw_log": hits["raw_log"],
        "has_subprocessors_doc": hits["subprocessors_doc"], "has_retention_doc": hits["retention_doc"],
        "has_agent": hits["agent"], "has_memory": hits["memory"], "has_art9_guard": hits["art9_guard"],
        "has_manip_guard": hits["manip_guard"], "is_web": hits["web"], "is_mobile": hits["expo"],
    }


def evaluate(signals: dict) -> list[dict]:
    out = []
    for rid, sev, article, title, pred in CHECKS:
        if pred(signals):
            out.append({"id": rid, "severity": sev, "article": article, "title": title})
    return out


def main() -> None:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else ".")
    signals = scan(root)
    findings = evaluate(signals)
    print(json.dumps({"signals": signals, "findings": findings,
                      "note": "SIGNAL not verdict — verify each hit in code before reporting"}, indent=2))


if __name__ == "__main__":
    main()
