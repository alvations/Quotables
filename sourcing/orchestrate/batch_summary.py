#!/usr/bin/env python3
"""Print per-batch status tallies of sourcing/web_results/batch_*.jsonl as TSV (audit trail)."""
import json, glob, os, collections
print("batch\trows\tsourced\tmisattributed\tunverified\tunsearched")
tot = collections.Counter()
for f in sorted(glob.glob("sourcing/web_results/batch_*.jsonl")):
    c = collections.Counter(json.loads(l)["status"] for l in open(f))
    tot.update(c)
    print(f"{os.path.basename(f)[:-6]}\t{sum(c.values())}\t{c['sourced']}\t{c['misattributed']}\t{c['unverified']}\t{c['unsearched']}")
print(f"TOTAL\t{sum(tot.values())}\t{tot['sourced']}\t{tot['misattributed']}\t{tot['unverified']}\t{tot['unsearched']}")
