#!/usr/bin/env python3
"""Merge web-agent evidence records into the source column, without rebuilding it.

build_column.py writes the whole third column from the evidence files it is given, which is
right for the original pass and wrong now: the corpus also carries the discovery additions,
whose sources live in sourcing/additions/ rather than in any evidence file, and a full rebuild
would blank them. This script instead adds each evidence record's sources to the line it names
and leaves every other line alone, so a later deep-search batch can be folded in on its own.

Only `sourced` records change anything. A `misattributed` record is a finding, not a source -
the line keeps `[]`, which is what the strict policy requires - and an `unverified` record
says the search found nothing. Both stay in the evidence file as the record of what was
looked at; neither touches the corpus.

Line numbers refer to the corpus as the original pass numbered it, and the additions are
appended after those lines rather than interleaved, so the numbering still holds. A record
pointing past the end of the file is reported and skipped rather than guessed at.

Usage: apply_evidence.py author-quote.txt out.txt evidence1.jsonl [evidence2.jsonl ...]
"""
import json, sys
from collections import defaultdict


def main(corpus, out, *evidence):
    add = defaultdict(list)
    skipped = []
    for path in evidence:
        for line in open(path, encoding="utf8"):
            line = line.strip()
            if not line:
                continue
            r = json.loads(line)
            if r.get("status") != "sourced":
                continue
            n = r.get("line") or r.get("id")
            for s in r.get("sources") or []:
                s = " ".join(str(s).split())
                if s and s not in add[n]:
                    add[n].append(s)

    rows = [l.rstrip("\n").split("\t") for l in open(corpus, encoding="utf8")]
    touched = 0
    with open(out, "w", encoding="utf8") as f:
        for i, parts in enumerate(rows, 1):
            a, q, col = parts[0], parts[1], parts[2] if len(parts) > 2 else "[]"
            new = add.pop(i, None)
            if new:
                srcs = json.loads(col) if col.strip() else []
                before = len(srcs)
                for s in new:
                    if s not in srcs:
                        srcs.append(s)
                if len(srcs) != before:
                    touched += 1
                col = json.dumps(srcs, ensure_ascii=False)
            f.write(f"{a}\t{q}\t{col}\n")
    for n in sorted(add):
        skipped.append(n)
    print(f"{touched} lines gained a source from the deep-search evidence")
    if skipped:
        print(f"  {len(skipped)} records pointed past the end of the corpus and were skipped: "
              f"{skipped[:10]}{'...' if len(skipped) > 10 else ''}")


if __name__ == "__main__":
    main(*sys.argv[1:])
