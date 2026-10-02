#!/bin/bash
# Rebuild author-quote.txt from the pre-additions base plus every additions file.
#
# Idempotent on purpose: children keep pushing to sourcing/additions/ and the relay keeps
# delivering rows, so this runs many times. Rebuilding from a fixed base rather than appending
# to the current file means a re-run can neither double-add a quote nor fill the ledger with
# "already in the corpus" rejections that are really just an earlier run's own work.
set -e
cd "$(git rev-parse --show-toplevel)"
BASE=$(python3 -c "import json;print(json.load(open('sourcing/discovery_state.json'))['corpus_base_commit'])")
git show "$BASE:author-quote.txt" > /tmp/corpus_base.txt
python3 sourcing/validate_additions.py /tmp/corpus_base.txt /tmp/corpus_new.txt \
        sourcing/audit/additions_ledger.tsv sourcing/additions/*.jsonl
python3 - <<'PY'
import json
n=s=0
for i,l in enumerate(open('/tmp/corpus_new.txt',encoding='utf8'),1):
    p=l.rstrip('\n').split('\t'); n+=1
    assert len(p)==3, f"line {i} has {len(p)} columns"
    for t in json.loads(p[2]):
        assert not any(c in t for c in '\r\n\t'), f"line {i}: control char in source"
    if json.loads(p[2]): s+=1
print(f"verified {n:,} lines, {s:,} sourced")
PY
cp /tmp/corpus_new.txt author-quote.txt
