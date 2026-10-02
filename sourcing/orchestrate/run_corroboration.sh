#!/bin/bash
# Re-run the full-text corroboration pass over whatever is currently in sourcing/additions/.
#
# Safe to re-run: the job list is rebuilt from the accepted rows each time, clones are reused
# when already present, and the ledgers are rewritten rather than appended, so running this
# twice produces the same three ledgers rather than duplicate rows.
#
# Needs rapidfuzz and unidecode (pip install rapidfuzz unidecode) and a scratch directory with
# room for the clones - roughly 1 GB per few hundred books.
set -e
cd "$(git rev-parse --show-toplevel)"
WORK="${1:?usage: run_corroboration.sh <scratch-dir>}"
mkdir -p "$WORK/books"

# The Project Gutenberg catalogue. gutenberg.org itself is not reachable from this
# environment; raw.githubusercontent.com is, so the hugovk mirror stands in for it.
[ -s "$WORK/gutenberg-metadata.json" ] || curl -sS -o "$WORK/gutenberg-metadata.json" \
  https://raw.githubusercontent.com/hugovk/gutenberg-metadata/main/gutenberg-metadata.json

python3 sourcing/corroborate_fulltext.py sourcing/audit/added_quotes.jsonl \
        "$WORK/gutenberg-metadata.json" "$WORK/corroborate_jobs.json"

# GITenberg names a repo <title-slug>_<pg_id>. Roughly half of Project Gutenberg is not
# mirrored there, so a failed clone is an ordinary outcome and is recorded, not retried.
python3 - "$WORK" <<'PY'
import json, os, subprocess, sys
W = sys.argv[1]
jobs = json.load(open(f"{W}/corroborate_jobs.json"))["jobs"]
for j in jobs:
    d = f"{W}/books/{j['pg_id']}"
    if os.path.isdir(d):
        continue
    subprocess.run(["git", "clone", "--depth", "1", "-q",
                    f"https://github.com/GITenberg/{j['gitenberg_repo']}", d],
                   stderr=subprocess.DEVNULL)
PY

python3 sourcing/corroborate_run.py "$WORK"
echo "ledgers rewritten: sourcing/audit/fulltext_corroboration.tsv, _books_corroboration.tsv, _searched_corroboration.tsv"
