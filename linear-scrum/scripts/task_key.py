#!/usr/bin/env python3
"""task_key.py — derive a stable identity key for a tasks.md checkbox line.

The key goes into meta.json#linear.issue_map so re-running Setup/Sync never
creates a duplicate Linear issue for the same task. It is derived from the task
TITLE only (the text before the ` — ` body separator), normalized so that
checkbox state, bold markers, case, and whitespace do not change it.
"""
from __future__ import annotations

import hashlib
import re
import sys


def task_key(line: str) -> str:
    s = line.strip()
    s = re.sub(r"^-\s*\[[ xX]\]\s*", "", s)   # drop "- [ ] " / "- [x] "
    s = s.split(" — ")[0]                       # title before the em-dash body
    s = s.replace("**", "").strip()             # drop bold markers
    s = re.sub(r"\s+", " ", s).lower()          # collapse whitespace, case-fold
    return hashlib.sha1(s.encode("utf-8")).hexdigest()[:12]


if __name__ == "__main__":
    for arg in sys.argv[1:]:
        print(task_key(arg))
