#!/bin/bash
# Usage: sourcing/orchestrate/commit_progress.sh "message"
# Commits the sources column, evidence, raw results and orchestrator state, then tries to push.
set -e
cd "$(dirname "$0")/../.."
git add author-quote.txt sourcing/evidence sourcing/web_results sourcing/orchestrator_state.json sourcing/batches README.md docs sourcing
git -c user.name=alvations -c user.email=alvations@gmail.com commit -q -m "$1" || echo "nothing to commit"
git log --oneline -1
git push -u origin "$(git rev-parse --abbrev-ref HEAD)" 2>&1 | tail -1 || true
