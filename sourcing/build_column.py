#!/usr/bin/env python3
"""Merge evidence files into the third column of author-quote.txt.

Usage: python3 build_column.py author-quote.txt out.txt evidence1.jsonl [evidence2.jsonl ...]

Every evidence record is {"line": <1-based line number>, "source": "<first-hand source string>", ...}.
Records with status "misattributed" or "unverified" (from the web agents) contribute nothing.
The output keeps columns 1-2 untouched and writes column 3 as a JSON list of unique source
strings (in order of first appearance); lines without evidence get [].
"""
import json, sys
from collections import defaultdict

def load(paths):
    by_line = defaultdict(list)
    for p in paths:
        for l in open(p, encoding="utf8"):
            l = l.strip()
            if not l:
                continue
            r = json.loads(l)
            if r.get("status") in ("misattributed", "unverified"):
                continue
            srcs = r.get("sources") if "sources" in r else [r.get("source")]
            for s in srcs or []:
                s = (s or "").strip()
                if s and s not in by_line[r["line"]]:
                    by_line[r["line"]].append(s)
    return by_line

def main(inp, outp, *evidence):
    by_line = load(evidence)
    n = i = 0
    src_lines = open(inp, encoding="utf8").read().splitlines()  # read fully first: inp may equal outp
    with open(outp, "w", encoding="utf8") as fo:
        for i, line in enumerate(src_lines, 1):
            cols = line.rstrip("\n").split("\t")[:2]
            srcs = by_line.get(i, [])
            if srcs:
                n += 1
            fo.write("\t".join(cols) + "\t" + json.dumps(srcs, ensure_ascii=False) + "\n")
    print(f"{n} of {i} lines carry at least one source", file=sys.stderr)

if __name__ == "__main__":
    main(*sys.argv[1:])
