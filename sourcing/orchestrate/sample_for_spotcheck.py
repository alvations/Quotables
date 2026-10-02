#!/usr/bin/env python3
"""Draw a reproducible random sample of accepted additions to verify by hand.

The validator can only check shape - fields present, no aggregator, not a duplicate. It cannot
tell whether the quote is really in the work the agent named. That needs a person (or this
session) reading an independent source, so it is done on a sample and the result is written to
sourcing/audit/addition_spotchecks.tsv.

The sample is stratified by batch and seeded, so the same command reproduces the same sample
and a reader can tell which rows were checked and which were taken on the validator's word.

Usage: sample_for_spotcheck.py <n per batch> [seed]
"""
import glob, json, random, sys

n = int(sys.argv[1]) if len(sys.argv) > 1 else 2
seed = int(sys.argv[2]) if len(sys.argv) > 2 else 20261002

by_batch = {}
for path in sorted(glob.glob("sourcing/additions/*.jsonl")):
    batch = path.rsplit("/", 1)[-1].replace(".jsonl", "")
    rows = [json.loads(l) for l in open(path, encoding="utf8") if l.strip()]
    if rows:
        by_batch[batch] = rows

rng = random.Random(seed)
for batch in sorted(by_batch):
    for r in rng.sample(by_batch[batch], min(n, len(by_batch[batch]))):
        print(f"{batch}\t{r['author']}\t{r['quote'][:90]}\t{(r.get('sources') or ['?'])[0][:80]}")
