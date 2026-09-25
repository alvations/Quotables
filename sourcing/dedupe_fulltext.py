#!/usr/bin/env python3
"""Collapse full-text hits that name the same work more than once for one quote.

A quote can legitimately match several works: Marden reused a sentence across two books, and
a poem is reprinted in two collections. Those are real and both are kept. What is not real is
the same work counted twice because Gutenberg carries it in more than one edition, or because
two passages resolved to headings that differ only in punctuation:

    The Notebooks of Leonardo Da Vinci - Complete, MORALS
    The Notebooks of Leonardo Da Vinci - Volume 2, MORALS
    Far from the Madding Crowd, BOLDWOOD IN MEDITATION--REGRET
    Far from the Madding Crowd, BOLDWOOD IN MEDITATION -- REGRET

Works are keyed on the title with edition suffixes (- Complete, - Volume N, Part N) removed
and punctuation flattened. Within a group the best-scoring record wins; ties prefer the one
that has a locator, then the shorter title, so "Complete" loses to the named volume only when
the volume scored higher.

Usage: dedupe_fulltext.py in.jsonl out.jsonl
"""
import collections, json, re, sys

EDITION = re.compile(r"(?i)\s*[—–-]+\s*(complete|volume\s+[ivxlcdm\d]+|part\s+[ivxlcdm\d]+)\s*$")
# a collected-works volume: accurate as a source, but it names the collection rather than the
# novel, so it loses to a hit in the individual work for the SAME quote
OMNIBUS = re.compile(r"(?i)\b(complete\s+(project\s+gutenberg\s+)?works|complete\s+writings)\b")


def work_key(source):
    work = source.split(", ", 1)[0]
    prev = None
    while prev != work:                      # "- Volume 1 - Complete" needs two passes
        prev, work = work, EDITION.sub("", work)
    return re.sub(r"[^a-z0-9]+", " ", work.lower()).strip()


def rank(rec):
    has_loc = ", " in rec["source"]
    return (rec.get("score", 0), has_loc, -len(rec["source"]))


rows = [json.loads(l) for l in open(sys.argv[1], encoding="utf8") if l.strip()]
groups = collections.defaultdict(list)
for r in rows:
    groups[(r["line"], work_key(r["source"]))].append(r)

kept = [max(v, key=rank) for v in groups.values()]

# Per quote, drop the omnibus when the same quote was also found in an individual work.
# Checking per quote rather than per author matters: Meredith has 91 individual works on
# Gutenberg but not The Egoist, so for that line the collected works is the only copy and
# must be kept - a coarse source beats no source, and it is not a false one.
by_line = collections.defaultdict(list)
for r in kept:
    by_line[r["line"]].append(r)
final, shadowed = [], 0
for line, recs in by_line.items():
    specific = [r for r in recs if not OMNIBUS.search(r["source"].split(", ")[0])]
    if specific and len(specific) < len(recs):
        shadowed += len(recs) - len(specific)
        recs = specific
    final += recs
kept = final
kept.sort(key=lambda r: (r["line"], r["source"]))
with open(sys.argv[2], "w", encoding="utf8") as f:
    for r in kept:
        f.write(json.dumps(r, ensure_ascii=False) + "\n")

print(f"{len(rows)} hits -> {len(kept)} after collapsing duplicate editions "
      f"({len(rows) - len(kept)} dropped, of which {shadowed} omnibus hits superseded by the "
      f"individual work)", file=sys.stderr)
