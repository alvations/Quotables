#!/bin/bash
# Pull children's pushes without letting a blunt merge strategy destroy either side's work.
#
# Ownership is clean, so conflicts have a correct answer rather than a preference:
#   sourcing/additions/<batch>.jsonl  - owned by that batch's child. It appends as it works,
#                                       so on a conflict the LONGER file is the later push and
#                                       the shorter one is a stale copy or my relay transcript.
#   author-quote.txt, ledgers         - owned by this session. Children never write them, so a
#                                       conflict here means my own rebase replay; keep mine.
# Never use `git pull -X ours/theirs` for this: during a rebase those are swapped relative to
# intuition, and picking the wrong side silently discards a child's finished research.
set -e
cd "$(git rev-parse --show-toplevel)"
git fetch -q origin quote-sources-column
if ! git rebase -q origin/quote-sources-column 2>/dev/null; then
  while read -r f; do
    case "$f" in
      sourcing/additions/*.jsonl)
        a=$(git show ":2:$f" 2>/dev/null | wc -l); b=$(git show ":3:$f" 2>/dev/null | wc -l)
        if [ "$a" -ge "$b" ]; then git show ":2:$f" > "$f"; else git show ":3:$f" > "$f"; fi
        echo "  additions conflict $f -> kept the longer side ($a vs $b lines)" ;;
      *) git checkout -q --theirs -- "$f" 2>/dev/null || git checkout -q --ours -- "$f" ;;
    esac
    git add "$f"
  done < <(git diff --name-only --diff-filter=U)
  GIT_EDITOR=true git -c user.name=alvations -c user.email=alvations@gmail.com rebase --continue >/dev/null
fi
echo "synced with origin"
