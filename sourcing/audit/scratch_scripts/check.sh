#!/bin/bash
# usage: check.sh name...  -> prints OK/NO per name
for n in "$@"; do
  if GIT_TERMINAL_PROMPT=0 timeout 40 git ls-remote -q "https://github.com/GITenberg/$n" HEAD >/dev/null 2>&1; then echo "OK $n"; else echo "NO $n"; fi
done
