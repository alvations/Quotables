#!/usr/bin/env python3
"""Check author-quote.txt against every invariant this project claims for it.

The counts in README.md say what the corpus contains; this says whether the file is actually
shaped the way the documentation promises. It is the last gate before a push, and it exits
non-zero on any failure so it can be wired into a hook.

Checks, in order:
  1. three tab-separated columns on every line, and no control characters anywhere
  2. column 3 parses as a JSON list of strings
  3. no empty author and no empty quote
  4. no duplicate (author, quote) pair among the added lines (base-corpus
     duplicates are reported, not failed - see the note in the code)
  5. no source string names an aggregator domain
  6. no source string is only a bare year or a bare author name
  7. every evidence id that claims a corpus line is in range

Usage: verify_corpus.py [corpus]
"""
import glob
import json
import re
import sys
import unicodedata

PATH = sys.argv[1] if len(sys.argv) > 1 else "author-quote.txt"

AGGREGATORS = re.compile(
    r"(?i)\b(?:brainyquote|azquotes|quotefancy|goodreads|quotemaster|quotegarden"
    r"|quoteambition|libquotes|quotesgram|picturequotes|everydaypower|quotlr"
    r"|wisesayings|searchquotes|quotetab|inspiringquotes|quotepark|quotewise)\b")
BARE_YEAR = re.compile(r"^\(?(?:1[0-9]{3}|20[0-9]{2}|c\.\s*\d+)\)?$")

failures = []


def fail(line_no, msg):
    failures.append(f"line {line_no}: {msg}")


rows = []
with open(PATH, encoding="utf-8") as fh:
    for i, line in enumerate(fh, 1):
        line = line.rstrip("\n")
        parts = line.split("\t")
        if len(parts) != 3:
            fail(i, f"{len(parts)} columns, expected 3")
            continue
        author, quote, raw = parts
        for field, name in ((author, "author"), (quote, "quote"), (raw, "sources")):
            bad = [c for c in field
                   if unicodedata.category(c) == "Cc" and c not in "\t\n"]
            if bad:
                fail(i, f"control character {bad[0]!r} in {name}")
        if not author.strip():
            fail(i, "empty author")
        if not quote.strip():
            fail(i, "empty quote")
        try:
            sources = json.loads(raw)
        except json.JSONDecodeError as exc:
            fail(i, f"column 3 is not JSON: {exc}")
            continue
        if not isinstance(sources, list) or any(not isinstance(s, str) for s in sources):
            fail(i, "column 3 is not a list of strings")
            continue
        for s in sources:
            if AGGREGATORS.search(s):
                fail(i, f"source names an aggregator: {s[:60]!r}")
            if BARE_YEAR.match(s.strip()):
                fail(i, f"source is only a year: {s!r}")
            if s.strip().lower() == author.strip().lower():
                fail(i, "source is just the author's name")
        rows.append((author, quote, sources))

# The base corpus contains a handful of lines duplicated before this project touched it.
# They cannot be removed: every id in sourcing/evidence/ is a line number into the base
# corpus, so deleting a line would silently repoint thousands of citations. They are
# therefore reported rather than failed. A duplicate that involves an ADDED line is a real
# failure, because validate_additions.py is supposed to reject those.
BASE = 39269
seen = {}
base_dupes = []
for i, (author, quote, _) in enumerate(rows, 1):
    key = (author.strip().lower(), " ".join(quote.split()).lower())
    first = seen.get(key)
    if first is None:
        seen[key] = i
    elif i > BASE or first > BASE:
        fail(i, f"duplicate of line {first}, and one of them is an added line")
    else:
        base_dupes.append((first, i))

for path in sorted(glob.glob("sourcing/evidence/*.jsonl")):
    for line in open(path, encoding="utf-8"):
        line = line.strip()
        if not line:
            continue
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            failures.append(f"{path}: unparseable line")
            continue
        rid = rec.get("id")
        if isinstance(rid, int) and not 1 <= rid <= len(rows):
            failures.append(f"{path}: evidence id {rid} is outside 1..{len(rows)}")

total = len(rows)
sourced = sum(1 for _, _, s in rows if s)
people = len({a for a, _, _ in rows})
print(f"{total:,} lines / {sourced:,} sourced ({sourced / total * 100:.1f}%) / {people:,} people")
if base_dupes:
    print(f"{len(base_dupes)} duplicate pair(s) inherited from the base corpus, left in place: "
          + ", ".join(f"{a}/{b}" for a, b in base_dupes))
if failures:
    print(f"\n{len(failures)} FAILURES:")
    for f in failures[:40]:
        print("  " + f)
    if len(failures) > 40:
        print(f"  ... and {len(failures) - 40} more")
    sys.exit(1)
print("every invariant holds")
