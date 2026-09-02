#!/usr/bin/env python3
"""Write TSV batches (id, author, quote) of the corpus lines that still have no evidence,
most-quoted authors first, for the web-search agents (see AGENT_PROMPT.md).
Usage: python3 make_batches.py author-quote.txt out_dir [batch_size] evidence1.jsonl [...]"""
import collections, json, os, sys
corpus, out_dir = sys.argv[1], sys.argv[2]
rest = sys.argv[3:]
size = int(rest[0]) if rest and rest[0].isdigit() else 150
evidence = [p for p in rest if not p.isdigit()]
rows = [l.rstrip("\n").split("\t") for l in open(corpus, encoding="utf8")]
done = set()
for p in evidence:
    for l in open(p, encoding="utf8"):
        l = l.strip()
        if l: done.add(json.loads(l)["line"])
cnt = collections.Counter(r[0] for r in rows)
todo = [(i, r[0], r[1]) for i, r in enumerate(rows, 1) if i not in done]
todo.sort(key=lambda t: (-cnt[t[1]], t[1], t[0]))
os.makedirs(out_dir, exist_ok=True)
for k in range(0, len(todo), size):
    with open(os.path.join(out_dir, f"batch_{k // size + 1:04d}.tsv"), "w", encoding="utf8") as f:
        f.write("id\tauthor\tquote\n")
        for i, a, q in todo[k:k + size]:
            f.write(f"{i}\t{a}\t{q}\n")
print(f"{len(todo)} lines without evidence -> {(len(todo) + size - 1) // size} batches in {out_dir}", file=sys.stderr)
