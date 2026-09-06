#!/bin/bash
set -e
cd /home/user/Quotables
OUT=/tmp/claude-0/-home-user-Quotables/117bd328-976a-5d02-8fb9-619302fe0316/scratchpad/bundle
rm -rf "$OUT"; mkdir -p "$OUT"
git bundle create "$OUT/quotables-sources-branch.bundle" master..quote-sources-column quote-sources-column 2>/dev/null
tar czf "$OUT/quotables-sources-files.tar.gz" author-quote.txt README.md docs sourcing
ls -la "$OUT"
