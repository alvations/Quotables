#!/usr/bin/env python3
"""Offline matcher: align every line of author-quote.txt with citation datasets
(reference quotes that carry a first-hand source) and emit evidence records.

Usage: python3 match_offline.py author-quote.txt refs.jsonl evidence_offline.jsonl

refs.jsonl records: {"author": str, "quote": str, "source": str, "dataset": str}
Output records:     {"line": int, "author": str, "source": str, "dataset": str,
                     "ref_quote": str, "score": int, "how": "exact|contains|fuzzy"}
Only matches judged reliable are emitted:
  exact     normalized text identical
  contains  corpus quote (>= 40 normalized chars) is a substring of the reference, or vice versa
  fuzzy     rapidfuzz token_set_ratio >= 93 and partial_ratio >= 95, length ratio within 0.5..2
"""
import json, re, sys
from collections import defaultdict
from rapidfuzz import fuzz
from norm import norm, norm_author

def author_keys(name):
    """Keys under which an author is indexed: full normalized name and last token."""
    n = norm_author(name)
    toks = n.split()
    keys = {n}
    if toks:
        keys.add(toks[-1])
    return keys, n

def same_author(a, b):
    """True when two normalized author names plausibly denote the same person."""
    if a == b:
        return True
    ta, tb = a.split(), b.split()
    if not ta or not tb or ta[-1] != tb[-1]:
        return False
    # One name is a sub-sequence of the other (e.g. 'shakespeare' vs 'william shakespeare',
    # 'r w emerson' vs 'ralph waldo emerson' handled by initials check)
    short, long_ = (ta, tb) if len(ta) <= len(tb) else (tb, ta)
    if all(t in long_ for t in short):
        return True
    # initials: first letters agree
    if all(any(l.startswith(s[0]) for l in long_) for s in short):
        return True
    return False

def main(corpus_path, refs_path, out_path):
    refs = [json.loads(l) for l in open(refs_path, encoding="utf8")]
    by_last = defaultdict(list)
    for r in refs:
        r["_nq"] = norm(r["quote"])
        r["_na"] = norm_author(r["author"])
        toks = r["_na"].split()
        if toks:
            by_last[toks[-1]].append(r)
    out = open(out_path, "w", encoding="utf8")
    n_hit = 0
    for i, line in enumerate(open(corpus_path, encoding="utf8"), 1):
        parts = line.rstrip("\n").split("\t")
        author, quote = parts[0], parts[1]
        na = norm_author(author)
        toks = na.split()
        if not toks:
            continue
        cands = [r for r in by_last.get(toks[-1], []) if same_author(na, r["_na"])]
        if not cands:
            continue
        nq = norm(quote)
        if len(nq) < 12:
            continue
        best = None
        for r in cands:
            rq = r["_nq"]
            if nq == rq:
                score, how = 100, "exact"
            elif len(nq) >= 40 and nq in rq:
                score, how = 99, "contains"
            elif len(rq) >= 40 and rq in nq:
                score, how = 98, "contains"
            else:
                lr = len(nq) / max(1, len(rq))
                if not (0.5 <= lr <= 2.0):
                    continue
                ts = fuzz.token_set_ratio(nq, rq)
                if ts < 93:
                    continue
                pr = fuzz.partial_ratio(nq, rq)
                if pr < 95:
                    continue
                score, how = int(min(ts, pr)), "fuzzy"
            if best is None or score > best[0]:
                best = (score, how, r)
        if best:
            score, how, r = best
            n_hit += 1
            out.write(json.dumps({"line": i, "author": author, "source": r["source"],
                                  "dataset": r["dataset"], "ref_quote": r["quote"],
                                  "score": score, "how": how}, ensure_ascii=False) + "\n")
    out.close()
    print(f"matched {n_hit} lines", file=sys.stderr)

if __name__ == "__main__":
    main(*sys.argv[1:4])
