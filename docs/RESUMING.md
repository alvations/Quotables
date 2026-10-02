# Resuming this work

Everything below is derived from the repository, not from anyone's memory of the run. The
branch is self-contained: a fresh session needs this file, the scripts in `sourcing/`, and
nothing else.

## First, get on the right branch

A new container may clone the repository onto a different branch whose `author-quote.txt`
still has only two columns. The three-column corpus lives on **`quote-sources-column`**:

```
git fetch origin quote-sources-column && git checkout quote-sources-column
head -1 author-quote.txt | awk -F'\t' '{print NF}'     # must print 3
```

Never commit a two-column corpus over the three-column one. `sourcing/verify_corpus.py` will
refuse it, which is the backstop, but checking the branch first is cheaper.

## State as of the last ingest

| | |
|---|---|
| corpus | 41,943 lines, 16,390 sourced (39.1%), 3,785 people |
| unsourced | 25,553 |
| documented misattributions (kept as `[]`) | 771 |
| rows added by the discovery phase | 2,674 |
| base commit the rebuild starts from | `sourcing/discovery_state.json` → `corpus_base_commit` |

`python3 sourcing/orchestrate/refresh_counts.py --check` recomputes all of that from the data
and exits non-zero if any published number has drifted. Run it before trusting this table.

## The ingest cycle

Three idempotent steps. Run them in this order, as often as you like:

```
sourcing/orchestrate/sync_additions.sh          # pull what children pushed (refuses a dirty tree)
python3 sourcing/web_to_evidence.py sourcing/evidence/web_deep_search.jsonl \
        sourcing/web_results/batch_w*.jsonl sourcing/relay_web/batch_w*.jsonl
sourcing/orchestrate/rebuild_with_additions.sh  # validate + rebuild from the base commit
python3 sourcing/orchestrate/refresh_counts.py  # rewrite every published count
```

Then commit and push. A push rejected as non-fast-forward means a child pushed in the
meantime: sync and retry, never force. Do not run `build_column.py` for additions; the rebuild
script is the only supported path, and it rebuilds from a fixed base so a re-run cannot
double-add a quote.

Where a batch pushed to `sourcing/web_results/` AND relayed into `sourcing/relay_web/`, the
pushed file wins; the relay copy is kept as the record of what was reported and when. The
rebuild applies that rule itself for `sourcing/relay/`, and the `web_to_evidence.py` invocation
above is written to be given both directories because the ids do not collide.

## What is left to do

1. **402 corpus lines were handed to a deep-search batch and never searched.** Ids, batches and
   reasons are in `sourcing/audit/unsearched_deep_search.txt` (regenerated from the prompts and
   the result files, so it cannot drift). 17 ran out of search budget; 385 belong to batches
   `w009`, `w012`-`w016`, which were stopped before they got that far. These are the cheapest
   remaining win: the lines are already chosen and known to be unsourced.
2. **1,358 lines the deep search examined and could not place.** Any further attempt needs a
   source the agents could not see - a scanned book, a subscription archive - not another pass
   over the same quotation sites.
3. **25,553 lines still carry `[]`.** Some of those are quotations no first-hand source exists
   for; the strict policy means they stay empty rather than take an aggregator's word.
4. **Pre-generated, never dispatched:** nothing. Prompts `batch_w001`-`w016` were all used. A
   new deep-search batch is made with `sourcing/orchestrate/make_deep_search_prompt.py`, and a
   new discovery batch with `make_discovery_prompt.py`.

## Two decisions that are the repository owner's to make

Both would move line numbers or repoint citations, so they were left alone:

- **Twelve people are spelled two ways** in the corpus, each an accented form against an ASCII
  flattening of it. Additions now adopt whichever spelling the corpus uses more often
  (`validate_additions.py`), but the existing rows were not merged.
- **Three pairs of lines are duplicated** in the base corpus: 3916/3921, 20438/20459,
  29147/29153. `verify_corpus.py` reports them rather than failing, because every `id` in
  `sourcing/evidence/` is a line number into the base corpus and deleting a line would
  silently repoint thousands of citations.

## Rules the run was held to

- **Strict evidence only.** A citation-tracking reference that names a specific work, or a
  verbatim match in the work itself. An aggregator never counts, even when it names a book -
  `web_to_evidence.py` re-checks this and logs every downgrade to
  `sourcing/audit/strict_downgrades.tsv`. Sources must be first-hand: an autobiography, diary,
  letter or contemporaneous transcription, not a third party's recollection. Never write a
  source from recall.
- **Commits are authored `alvations <alvations@gmail.com>`**, with no co-author or session
  trailers, and no model identifier anywhere in repository content. A hook may ask to re-author
  a commit; decline it.
- No "claude" in branch names or tracked content.
- Every prompt sent to a child goes in `sourcing/audit/prompts/`, every child in
  `sourcing/audit/sessions.jsonl` with its real cost, every accepted and rejected row in
  `sourcing/audit/additions_ledger.tsv`.
- Do not open a pull request unless asked.

## Hazards worth knowing before dispatching anything

- **Usage limits, not crashes, are what kills a fan-out.** On 2026-10-02 a seven-day limit
  stopped all twelve live children three minutes after dispatch and nine lost everything,
  because only three had pushed. `get_session` shows `status: "rejected"` with
  `rateLimitType: "seven_day"` and a `resetsAt` timestamp: the container, clone and context all
  survive, so re-wake the session with a one-shot `create_trigger` just after the reset. Tell
  children to push every 15 rows; a killed turn relays nothing.
- **The relay is not redundant.** 278 rows arrived only as text messages from children that
  were archived before they could push, several of them after the run was declared finished.
  Transcribe a relayed payload into `sourcing/relay/` or `sourcing/relay_web/` *before* doing
  anything else with it, and keep the message verbatim in `sourcing/audit/relay_payloads/`.
- **Sessions created before the branch carried push credentials cannot push.** Prefer a fresh
  `create_session` for new work; re-waking is for a session that stalled.
- **The egress proxy blocks** wikiquote.org, archive.org, gutenberg.org and books.google.com,
  and `WebFetch` altogether. Children must use the `WebSearch` tool and reason over its
  snippets. Two sessions lost a whole run to this.
- `SendMessage` cannot reach these sessions; `create_trigger` with a `persistent_session_id`
  can.

## Checking the work

```
python3 sourcing/verify_corpus.py author-quote.txt
python3 sourcing/orchestrate/refresh_counts.py --check
```

The first asserts every invariant the documentation claims - three tab-separated columns, no
control characters, column three a JSON list of strings, no aggregator or bare-year source, no
duplicate added line, every evidence id in range - and is the gate the rebuild runs before it
is allowed to replace `author-quote.txt`. The second proves the published numbers match the
data. Both must pass before a push.

A gate cannot catch two defect classes that spot-checking found, so keep spot-checking: a
misquote carrying a correct citation, and a correct quote filed under the wrong work by the
same author. Append each check, pass or fail, to `sourcing/audit/addition_spotchecks.tsv`;
of 18 checks, 16 confirmed and 2 found real defects.
