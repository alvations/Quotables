#!/bin/bash
# wrapper: ingest a batch page via the repo script, then commit
set -e
cd /home/user/Quotables
sourcing/orchestrate/handle_result.sh "$1" "$2"
