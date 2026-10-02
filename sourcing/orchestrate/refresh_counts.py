#!/usr/bin/env python3
"""Rewrite the counts in README.md and docs/SOURCING.md from the corpus itself.

Every ingest moves five or six numbers that are quoted in prose, and editing them by hand is
how a published figure drifts away from the file it describes. This recomputes all of them
the way the project defines them - words are counted over the author and quote columns only,
a line counts as sourced when its third column is not the empty JSON list - and substitutes
them in place.

Usage: refresh_counts.py [--check]
   --check reports what would change and exits 1 if anything would, which is what a
   pre-push sanity check wants.
"""
import glob
import json
import re
import subprocess
import sys

ROWS = [l.rstrip("\n").split("\t") for l in open("author-quote.txt")]
TOTAL = len(ROWS)
SOURCED = sum(1 for r in ROWS if len(r) > 2 and r[2].strip() not in ("", "[]"))
UNSOURCED = TOTAL - SOURCED
PEOPLE = len({r[0] for r in ROWS})
WORDS = int(subprocess.run("cut -f1,2 author-quote.txt | wc -w", shell=True,
                           capture_output=True, text=True).stdout.strip())


def evidence_rows():
    for path in glob.glob("sourcing/evidence/*.jsonl"):
        for line in open(path):
            line = line.strip()
            if not line:
                continue
            try:
                yield path, json.loads(line)
            except json.JSONDecodeError:
                continue


MISATTRIBUTED = set()
DEEP = {"sourced": set(), "misattributed": set(), "unverified": set()}
for path, r in evidence_rows():
    i = r.get("id")
    status = r.get("status")
    if path.endswith("web_deep_search.jsonl") and status in DEEP and isinstance(i, int):
        DEEP[status].add(i)
    if status == "misattributed" and isinstance(i, int):
        if 1 <= i <= TOTAL and ROWS[i - 1][2].strip() in ("", "[]"):
            MISATTRIBUTED.add(i)

BASE = 39269  # the corpus as it stood when the discovery phase began
ADDED = TOTAL - BASE

PCT = f"{SOURCED / TOTAL * 100:.1f}"
UNPCT = f"{UNSOURCED / TOTAL * 100:.1f}"

SUBS = [
    ("README.md", r"^ - [\d,]+ quotes with$", f" - {TOTAL:,} quotes with"),
    ("README.md", r"^ - [\d,]+ words from$", f" - {WORDS:,} words from"),
    ("README.md", r"^ - [\d,]+ people$", f" - {PEOPLE:,} people"),
    ("README.md", r"^ - [\d,]+ quotes \([\d.]+%\) carry a verified first-hand source; "
                  r"[\d,]+ \([\d.]+%\) do not:$",
     f" - {SOURCED:,} quotes ({PCT}%) carry a verified first-hand source; "
     f"{UNSOURCED:,} ({UNPCT}%) do not:"),
    ("README.md", r"^   they were searched without finding one, and [\d,]+ of them are "
                  r"recorded as misattributed$",
     f"   they were searched without finding one, and {len(MISATTRIBUTED):,} of them are "
     "recorded as misattributed"),
    ("docs/SOURCING.md", r"^\| web-search agents \(misattributed, kept as `\[\]`\) \| [\d,]+ \|$",
     f"| web-search agents (misattributed, kept as `[]`) | {len(MISATTRIBUTED):,} |"),
    ("docs/SOURCING.md", r"^\| deep-search batches \(batch_w001 to w\d+\) over already-unsourced "
                         r"classical quotes \| [\d,]+ \|$",
     None),  # filled in below, the batch range is part of the label
    ("docs/SOURCING.md", r"^\| discovery phase: quotes added, each arriving with a first-hand "
                         r"source \| [\d,]+ \|$",
     f"| discovery phase: quotes added, each arriving with a first-hand source | {ADDED:,} |"),
    ("docs/SOURCING.md", r"^\| \*\*lines with at least one source\*\* \| \*\*[\d,]+ of [\d,]+ "
                         r"\([\d.]+%\)\*\* \|$",
     f"| **lines with at least one source** | **{SOURCED:,} of {TOTAL:,} ({PCT}%)** |"),
    ("docs/SOURCING.md", r"26,182 down to [\d,]+ so far - and they also produce findings that "
                         r"are not sources: [\d,]+ quotes",
     f"26,182 down to {UNSOURCED:,} so far - and they also produce findings that are not "
     f"sources: {len(DEEP['misattributed']):,} quotes"),
    ("docs/SOURCING.md", r"`sourcing/evidence/web_deep_search\.jsonl` alongside the [\d,]+ the "
                         r"deeper search still could not",
     f"`sourcing/evidence/web_deep_search.jsonl` alongside the {len(DEEP['unverified']):,} the "
     "deeper search still could not"),
]

changed = []
for path in ("README.md", "docs/SOURCING.md"):
    text = open(path).read()
    before = text
    for p, pattern, replacement in SUBS:
        if p != path:
            continue
        if replacement is None:
            # the deep-search row keeps its batch range, only the count moves
            def fix(m):
                return re.sub(r"\| [\d,]+ \|$", f"| {len(DEEP['sourced']):,} |", m.group(0))
            text = re.sub(pattern, fix, text, flags=re.M)
            continue
        text = re.sub(pattern, replacement.replace("\\", "\\\\"), text, flags=re.M)
    if text != before:
        changed.append(path)
        if "--check" not in sys.argv:
            open(path, "w").write(text)

print(f"{TOTAL:,} quotes / {SOURCED:,} sourced ({PCT}%) / {PEOPLE:,} people / {WORDS:,} words / "
      f"{UNSOURCED:,} unsourced / {len(MISATTRIBUTED):,} documented misattributions")
print(f"deep search: {len(DEEP['sourced']):,} sourced, {len(DEEP['misattributed']):,} "
      f"misattributed, {len(DEEP['unverified']):,} unverified")
if "--check" in sys.argv:
    if changed:
        print("stale counts in: " + ", ".join(changed))
        sys.exit(1)
    print("counts are current")
else:
    print("rewrote: " + (", ".join(changed) if changed else "nothing, already current"))
