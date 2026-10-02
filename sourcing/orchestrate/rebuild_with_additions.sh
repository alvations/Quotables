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
# Deep-search batches (batch_wNNN) re-source lines that are ALREADY in the corpus, so their
# findings go in before the additions are appended. apply_evidence.py adds to the column
# rather than rebuilding it, which is what keeps the additions' own sources intact.
if [ -s sourcing/evidence/web_deep_search.jsonl ]; then
  python3 sourcing/apply_evidence.py /tmp/corpus_base.txt /tmp/corpus_base_deep.txt \
          sourcing/evidence/web_deep_search.jsonl
  mv /tmp/corpus_base_deep.txt /tmp/corpus_base.txt
fi
# Children return rows twice over: a git push to sourcing/additions/, and a text relay that
# this session writes to sourcing/relay/. The git push is authoritative where it exists - it
# is the child's own latest state - so a relay file is only read for a batch that never
# managed to push, which is how a batch whose session died still reaches the corpus. Feeding
# both would fill the ledger with "duplicate within this run" rejections that mean nothing.
RELAY=()
for r in sourcing/relay/*.jsonl; do
  [ -e "$r" ] || continue
  [ -e "sourcing/additions/$(basename "$r")" ] || RELAY+=("$r")
done
python3 sourcing/validate_additions.py /tmp/corpus_base.txt /tmp/corpus_staged.txt \
        sourcing/audit/additions_ledger.tsv sourcing/additions/*.jsonl "${RELAY[@]}"
# Where a public-domain text was read and the quote found in it, that confirmation is folded
# in alongside the row's citation. It lives in its own ledger so the rebuild stays idempotent.
if [ -s sourcing/audit/fulltext_corroboration.tsv ]; then
  python3 sourcing/apply_corroboration.py /tmp/corpus_staged.txt \
          sourcing/audit/fulltext_corroboration.tsv /tmp/corpus_new.txt
else
  cp /tmp/corpus_staged.txt /tmp/corpus_new.txt
fi
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
