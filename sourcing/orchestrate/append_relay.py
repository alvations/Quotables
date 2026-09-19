#!/usr/bin/env python3
"""Append a text-relayed chunk of agent results to a batch's result file.

The children that cannot publish an artifact or push to git send their rows back as
plain text in `create_trigger` prompts, 25 rows to a chunk. Each chunk is saved to a
file and appended here rather than by hand, so every line is validated as JSON, ids
already held are skipped (chunks are sometimes replayed), and the running total is
checked against the batch manifest.

Usage: python3 append_relay.py <batch_name> <chunk.jsonl>
"""
import json, os, sys

batch, chunk = sys.argv[1], sys.argv[2]
out = f"sourcing/web_results/{batch}.jsonl"
have = set()
if os.path.exists(out):
    have = {json.loads(l)["id"] for l in open(out, encoding="utf8") if l.strip()}

new, dup = [], 0
for line in open(chunk, encoding="utf8"):
    line = line.strip()
    if not line:
        continue
    r = json.loads(line)          # a malformed relay must fail loudly, not half-append
    if r["id"] in have:
        dup += 1
        continue
    new.append(line)
    have.add(r["id"])

with open(out, "a", encoding="utf8") as f:
    for line in new:
        f.write(line + "\n")

expected = {int(l.split("\t")[0])
            for l in open(f"sourcing/batches/{batch}.tsv", encoding="utf8").read().splitlines()[1:]}
missing = len(expected - have)
print(f"{batch}: +{len(new)} new, {dup} duplicate; {len(have)}/{len(expected)} rows, "
      f"{missing} missing, complete={have == expected}")
