#!/bin/bash
# Usage: sourcing/orchestrate/handle_result.sh batch_NNNN /path/to/saved-results-page.html
# Run from the repository root. Extracts the JSONL from a batch results page into
# sourcing/web_results/batch_NNNN.jsonl, marks the batch received in
# sourcing/orchestrator_state.json, rebuilds the evidence file and the sources column,
# and prints the next batch to dispatch.
set -e
cd "$(dirname "$0")/../.."
python3 sourcing/orchestrate/ingest_artifact.py "$2" "sourcing/web_results/$1.jsonl"
# audit trail: keep the page exactly as the agent published it
mkdir -p sourcing/audit/raw_pages && cp "$2" "sourcing/audit/raw_pages/$1.html"
python3 - "$1" <<'PY'
import json, sys, os
p = 'sourcing/orchestrator_state.json'
st = json.load(open(p))
b = sys.argv[1]
if b not in st['received']: st['received'].append(b)
json.dump(st, open(p, 'w'), indent=1)
done = set(st['dispatched']) | set(st['received'])
nxt = [f[:-4] for f in sorted(os.listdir('sourcing/batches')) if f[:-4] not in done]
print('received', len(st['received']), 'dispatched', len(st['dispatched']), 'next:', nxt[0] if nxt else 'NONE')
PY
python3 sourcing/web_to_evidence.py sourcing/evidence/web_search_agents.jsonl sourcing/web_results/*.jsonl
python3 sourcing/build_column.py author-quote.txt author-quote.txt sourcing/evidence/*.jsonl
# audit trail: refresh the per-batch tallies
python3 sourcing/orchestrate/batch_summary.py > sourcing/audit/batch_summary.tsv
