# How the `sources` column was built

`author-quote.txt` now has three tab-separated columns:

| column | content |
| --- | --- |
| 1 | author (unchanged) |
| 2 | quote (unchanged) |
| 3 | JSON list of strings: first-hand sources for the quote, `[]` when none has been verified |

A *first-hand source* is the work in which the named author originally wrote or said the
line: a book, essay, poem, play (with act/scene), speech, letter, article, interview or a
contemporary's first-hand record of a remark (e.g. Boswell's *Life of Johnson*). Pages that
merely repeat a quote (quote aggregators, social media, "quotes" blogs) are never listed as a
source. When evidence shows a quote is misattributed or apocryphal, the list stays empty; the
finding is kept in the evidence files under `sourcing/evidence/`.

Every source string is the work title, the year of first publication when known, and a
locator when the evidence gives one, e.g.

```
"The Tragedy of Macbeth, Act 1, Scene 7"
"Man and Superman (1903), 'Maxims for Revolutionists'"
"Remark to James Boswell (15 May 1783), recorded in Boswell's Life of Samuel Johnson (1791)"
```

The author's name is not repeated inside the string because column 1 carries it.

## Pipeline

Everything lives in `sourcing/`. The steps are independent; each writes evidence records
(`{"line": <1-based line in author-quote.txt>, "source"/"sources": ..., "dataset": ..., ...}`)
and `build_column.py` merges them into column 3.

### Step 1: public citation datasets (offline)

Networking in the environment that produced this branch only allowed github.com, the npm
registry and PyPI, so the data had to come from those hosts. What was used:

| dataset | what it is | how it was obtained |
| --- | --- | --- |
| `@foba/quotes-{literature,economics,entrepreneur,financial,management,creativity}` (npm, MIT) | 3,288 Wikiquote "Sourced" entries for 78 authors; each record carries Wikiquote's citation text (`mark`) | `curl https://registry.npmjs.org/@foba/quotes-<name>/-/quotes-<name>-0.6.1.tgz`, then a regex pass over `dist/index.cjs` (`sourcing/build_refs.py` reads the extracted JSONL) |
| Bartlett, *Familiar Quotations* (Project Gutenberg #16732, via the GITenberg GitHub mirror `GITenberg/Familiar-Quotations_16732`) | 1,432 quotations with work and locator (act/scene, line, stanza) for 128 authors | `git clone --depth 1 https://github.com/GITenberg/Familiar-Quotations_16732`; parsed by the text-format parser described in `sourcing/build_refs.py` |

Discovery searches that led to these (all run with the WebSearch tool):
`github wikiquote dump parsed json dataset quotes with sources citations`,
`"wikiquote" dataset paper github "quotes" "citations" OR "sourced" corpus english release`,
`Bartlett's Familiar Quotations Project Gutenberg ebook number`,
`GITenberg github Bartlett Familiar Quotations repository`,
plus npm registry searches (`https://registry.npmjs.org/-/v1/search?text=wikiquote`) that
surfaced the `@foba` packages. Repositories that only contain parsers but no data
(heyseth/wickedQuotes, ScatteredRay/QuoteDB, t-kuculo/QuoteKG, sgottsch/WikiquoteDumper) and
datasets without citations (ceshine/wickedQuotes, lukin0110/quotes, Quotes-500K) were checked
and rejected. James Wood's *Dictionary of Quotations* (Gutenberg #48105) was cloned but not
used: it cites only author names, not works.

`match_offline.py` normalizes author names and quote text (Unicode to ASCII, lower case,
punctuation stripped) and accepts a reference only when the author matches and the text is
identical, one contains the other (>= 40 characters), or rapidfuzz `token_set_ratio >= 93` and
`partial_ratio >= 95` with a length ratio between 0.5 and 2.

### Step 2: verbatim location in public-domain full texts (offline)

For authors whose works are public domain, the quote is looked up directly in the original
text (Project Gutenberg plain text cloned from GITenberg mirrors). `locate_fulltext.py`
indexes 3-word shingles of the normalized text, scores candidates with rapidfuzz
`partial_ratio_alignment` (accepted at >= 92, or >= 97 for quotes under 30 characters) and
reports the work and the nearest section heading (for Shakespeare: play title from the table
of contents of Gutenberg #100 and `Act n, Scene m`, or `Sonnet n`). This is the strongest
evidence in the corpus: the line is found in the work itself.

Texts used are listed in `sourcing/gitenberg_manifest.json` (Gutenberg id, GITenberg
repository, edition/translation note).

### Step 3: web search agents

Every line still without a source was handed, in batches of 150, to parallel agents running
the prompt in `sourcing/AGENT_PROMPT.md`. Each agent uses the WebSearch tool only (fetching
reference pages was blocked), with at most two queries per quote:

1. `"<exact quote>" <author>`
2. `"<distinctive 6-10 word fragment>" source | wikiquote | quote investigator`

The agent accepts a source only when a citation-tracking reference (Wikiquote's sourced
sections, Quote Investigator, wist.info, Wikipedia with a footnote, Oxford/Yale dictionaries
of quotations, Bartlett's/Bartleby, a publisher's or library page for the work, Google Books,
the original periodical, or the transcript of the speech/interview) names the specific work.
Aggregators are not evidence. Results are `sourced`, `misattributed` (evidence says the author
never said it, or someone else did) or `unverified`. Batches were ordered by author frequency
so the most-quoted authors were processed first. Every result, including the URLs and a
one-line note of what the evidence said, is in `sourcing/evidence/web_search_agents.jsonl`.

## Reproducing

```
pip install rapidfuzz unidecode
cd sourcing
python3 build_refs.py refs.jsonl foba=foba_quotes.jsonl bartlett16732=bartlett16732.jsonl
python3 match_offline.py ../author-quote.txt refs.jsonl evidence/offline_dictionaries.jsonl
python3 locate_fulltext.py ../author-quote.txt evidence/gutenberg_fulltext_shakespeare.jsonl \
    '^(William )?Shakespeare$' "Complete Works" 0 100 <path to Gutenberg 100 text> --shakespeare
python3 web_to_evidence.py evidence/web_search_agents.jsonl <agent result files>
python3 build_column.py ../author-quote.txt ../author-quote.txt evidence/*.jsonl
```

## Continuing the web pass

The environment caps WebSearch at 200 calls per session (shared by all sub-agents of that
session), so one session sources roughly 100 lines. To continue:

1. `python3 sourcing/make_batches.py author-quote.txt web_batches 100 sourcing/evidence/*.jsonl`
   writes the remaining lines, most-quoted authors first, as `web_batches/batch_NNNN.tsv`.
2. In a session with `CLAUDE_CODE_MAX_WEB_SEARCHES_PER_SESSION` raised (or one fresh session
   per batch), run the prompt in `sourcing/AGENT_PROMPT.md` on a batch; it writes
   `web_results/batch_NNNN.jsonl`.
3. `python3 sourcing/web_to_evidence.py sourcing/evidence/web_search_agents.jsonl web_results/*.jsonl`
   then `python3 sourcing/build_column.py author-quote.txt author-quote.txt sourcing/evidence/*.jsonl`.

Rows the agents could not search (budget exhausted) are never written as `unverified`; they
simply stay absent from the evidence file and are picked up by the next `make_batches.py` run.

## Coverage

See the statistics section of the README. The evidence files record, for every sourced line,
which step produced it and what it matched against.

## Known limits

- Coverage is partial. Many lines in this corpus circulate only on aggregator sites and have
  no traceable origin; those keep `[]`. Lines that citation trackers flag as misattributed
  also keep `[]` (the finding is in the evidence file).
- Web-search evidence is only as good as the search snippet; Wikiquote, Quote Investigator
  and dictionary-of-quotations references were preferred, but a spot check before relying on
  any single line is advisable.
- Bartlett (1860s edition) and Gutenberg texts use the spelling and titles of their editions.
