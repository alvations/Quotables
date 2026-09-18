#!/usr/bin/env python3
"""Build the self-contained prompt for one batch session, git return channel.

Same research rules as make_sibling_prompt.py, but the child returns its results
by committing sourcing/web_results/<batch>.jsonl to the quote-sources-column
branch instead of publishing an Artifact. Written 2026-09-18 after the account's
artifact-publishing quota was exhausted mid-run, which stranded the results of
batches 0180-0187 inside their containers.

Usage: python3 make_sibling_prompt_git.py batch.tsv batch_name parent_session_id > prompt.txt
"""
import sys
batch, name, parent = sys.argv[1:4]
rows = open(batch, encoding="utf8").read().splitlines()[1:]
ids = [r.split("\t")[0] for r in rows]
print(f"""You are sourcing quotations for a corpus. Batch name: {name}. Work autonomously; nobody will answer questions.

## Goal
For each row of your batch (see "Rows" at the end: a list of line numbers of the corpus file, each line being author<TAB>quote), find the FIRST-HAND original source: the specific book, essay, poem, play (act/scene), speech, letter, article, interview or recording in which the named author originally wrote or said it. A page that merely repeats the quote is NOT a source.

## Tools and budget
- Use the WebSearch tool only for research. Do not use WebFetch (reference sites are blocked). Do NOT use the Artifact tool at all: artifact publishing is rate-limited and will fail.
- This session allows at most 200 web searches in total, and they are all you get. Use ONE search per row: the exact quote (or its first 12 words) in double quotes plus the author's name. Only when the first search is clearly promising but incomplete may you spend a second search on that row, and never if fewer than (rows remaining) searches are left. If the search tool reports that no search was performed, stop searching immediately and report the remaining rows as `unsearched`.
- Process rows in the order listed. Do not skip rows. Do not stop early except when the budget is exhausted.

## What counts as evidence
Accept a source only when a citation-tracking reference identifies a specific work: Wikiquote's sourced/"Quotes" sections with a work cited, Quote Investigator, wist.info, Wikipedia with a footnote, Oxford/Yale dictionaries of quotations, Bartlett's, Bartleby, a publisher's or library page for the work, Google Books, the original periodical, the transcript or recording of the speech or interview, or a contemporary's first-hand record (e.g. Boswell's Life of Johnson). Aggregator sites (BrainyQuote, Goodreads, AZQuotes, QuoteFancy, Pinterest, quote blogs) are NOT evidence even when they name a book. If Wikiquote lists it only under Unsourced/Attributed/Disputed, or only aggregators turn up: `unverified`. If evidence shows it is misattributed or apocryphal: `misattributed` with an empty sources list and the finding in evidence.

## Result format
One JSON object per row, one per line (JSONL):
{{"id": <line number>, "status": "sourced"|"misattributed"|"unverified"|"unsearched", "sources": ["<Title of work> (<year>), <locator>", ...], "evidence": ["<URL> - <one-line note>", ...], "queries": ["<query>"]}}
Source strings: work title, year of first publication when known, locator (chapter, act/scene, section, page, date) when the evidence gives one, e.g. "The House at Pooh Corner (1928), ch. 6" or "Letter to Thomas Jefferson (28 June 1813)" or "Man and Superman (1903), 'Maxims for Revolutionists'". Omit the author's name. Never invent a title, year or locator; never put a Wikiquote/Quote Investigator URL in sources (those go in evidence). For `unsearched` rows: sources [], evidence [], queries [].

## Setup (do this first)
    git clone https://github.com/alvations/Quotables /home/user/quotables-repo
    cd /home/user/quotables-repo && git checkout quote-sources-column
Read your rows from `/home/user/quotables-repo/author-quote.txt` (extract them with a short Python script that prints the numbered lines).

## Returning the results (essential)
Keep the results in `/home/user/{name}-results.jsonl` as you go, appending every 10 rows. Push what you have after row 60, after row 120, and again when every row has a line, so partial progress survives if this session is stopped by a usage limit. Each push is:

    cd /home/user/quotables-repo
    git pull --rebase origin quote-sources-column
    cp /home/user/{name}-results.jsonl sourcing/web_results/{name}.jsonl
    git add sourcing/web_results/{name}.jsonl
    git -c user.name=alvations -c user.email=alvations@gmail.com commit -m "Sources: {name} web results"
    git push origin quote-sources-column

If the push is rejected, run `git pull --rebase origin quote-sources-column` and push again, up to 8 attempts with a short sleep between; other sessions are pushing their own files to the same branch, so rejections are normal. Never modify author-quote.txt or any file other than `sourcing/web_results/{name}.jsonl`, and never force-push.

When the final push has succeeded, notify the parent session by calling the `create_trigger` tool of the remote-session MCP server with:
     name: "git results {name}"
     persistent_session_id: "{parent}"
     run_once_at: an RFC3339 UTC time 2 minutes in the future (run `date -u +%Y-%m-%dT%H:%M:%SZ` for the current time)
     initiation: "human_schedule"
     prompt: exactly "GIT RESULTS {name} rows=<n> sourced=<n> misattributed=<n> unverified=<n> unsearched=<n>"
If create_trigger fails, retry once after 30 seconds, then carry on regardless.
Your final reply must be that same one line. Do not paste the JSONL into the reply.

## Rows
Your rows are the following 1-based line numbers of `author-quote.txt` ({len(ids)} rows); the `id` of each result is the line number. Process them in the order listed:
{",".join(ids)}""")
