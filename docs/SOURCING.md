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

### Step 4: a second full-text pass over the quotes the web agents could not source

The web pass left 26,410 quotes without a first-hand source. Most are modern interview lines
with no published text to check, but a minority belong to authors the corpus itself shows to
be public-domain era, and for those the quote can be looked for in the work itself.

`build_gutenberg_jobs.py` decides where to look; it never assigns a source. An author counts
as public-domain era when the publication years already cited in their *sourced* quotes have a
median before 1930 - measured from the corpus, not from a hand-written list and not from
recollection. Those authors are matched against the Project Gutenberg catalogue (the
`hugovk/gutenberg-metadata` mirror; gutenberg.org itself is not reachable from this
environment), non-English editions are dropped, and each author is capped at 25 books.
GITenberg repository names are derived as `<title-slug>_<pg_id>`, a rule checked against 18
books already in the manifest before being used to generate new ones.

Three kinds of candidate are thrown out, because they are the ways this pass could invent a
source rather than find one:

- **name collisions.** "Tecumseh" matches William *Tecumseh* Sherman, which would have
  credited Sherman's memoirs to the Shawnee leader; "E. F. L. Wood, 1st Earl of Halifax"
  (20th century) matches George Savile, Marquess of Halifax (17th century).
- **derivative compilations.** "Widger's Quotations from the Project Gutenberg Editions of the
  Works of Mark Twain" is an excerpt collection: finding a line in it proves nothing about
  *which* Twain work the line came from. The same applies to dictionaries of quotations such
  as Bartlett - they *cite* a source, they are not one - so a quotation dictionary is only
  usable through its citations, never by locating a quote inside it. Gutenberg catalogues
  these digests under the author's own name, so `manifest_from_clones.py` drops them by title
  rather than relying on the author field.
- **collected-works volumes, when something better exists.** A quote found in "Complete Works
  of X" gets the collection as its work, which is coarse but not false. `dedupe_fulltext.py`
  drops such a hit only when the SAME quote was also found in an individual work - checked per
  quote, because Gutenberg does not carry every novel separately and for some lines the
  collection is the only copy.

Publication years are left off these sources. The catalogue carries no reliable date, and an
invented year in the sources column would be worse than no year at all, so a source from this
pass reads `Work, Chapter` rather than `Work (wrong year), Chapter`.

### Step 3: web search agents

Every line still without a source was handed, in batches of about 170, to parallel agents
running the prompt in `sourcing/AGENT_PROMPT.md` (the exact text sent for each batch is kept in
`sourcing/audit/prompts/`). Each agent uses the WebSearch tool only (fetching reference pages
was blocked), with at most two queries per quote:

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

The aggregator rule is not left to the agents' judgement. `web_to_evidence.py` re-checks every
row an agent called `sourced`: if each URL it cited is an aggregator domain, the row is
downgraded to `unverified`, its sources are dropped, and the downgrade is logged in
`sourcing/audit/strict_downgrades.tsv`. The raw files in `sourcing/web_results/` are left
exactly as the agents returned them, so the record of what each agent claimed stays intact and
the policy is applied in one auditable place. 399 rows were downgraded this way.

Agents returned their results over three channels, because none of them is reliable on its own:

1. **Artifact page.** The agent publishes its JSONL as a page and schedules a one-line
   notification to the parent, which reads the page and ingests it. This is the fastest channel
   and was used for most batches, but publishing is subject to a daily account-wide quota that a
   wide fan-out exhausts (it ran out twice during this run). Worse, once the quota is gone a
   republish silently keeps the *previous* version, so a notification can truthfully report 170
   rows while the page still holds 125. Every ingest is therefore checked row-by-row against the
   batch manifest before the batch is marked received; two truncated pages were caught this way.
2. **git push.** The agent commits its own `sourcing/web_results/batch_NNNN.jsonl` to the
   branch. This works only when the agent's permission classifier allows it, and whether it
   fires varies between otherwise identical sessions, so it cannot be relied on.
   `sourcing/orchestrate/make_sibling_prompt_git.py` generates this variant of the prompt.
3. **Text relay.** The agent re-serialises its rows as compact one-line JSON and sends them to
   the parent in 25-row chunks as `create_trigger` messages;
   `sourcing/orchestrate/append_relay.py` appends each chunk, validating every line as JSON,
   skipping ids already held and reporting the running total against the manifest. Slow and
   token-hungry (about 90k tokens for a 170-row batch) but it works where the others do not.

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
cd .. && python3 sourcing/normalize_sources.py author-quote.txt author-quote.txt
```

The last step applies the corrections from the format audit of the finished corpus: a handful
of source strings that repeated the author's name as an attribution, carried a machine date
(`19610711`) instead of a readable one, or ran a paragraph of commentary where a citation
belongs. Two strings that reported a third party's attribution rather than a first-hand work
were dropped entirely, so those lines fall back to `[]` as the strict policy requires. Every
change is listed in `sourcing/audit/format_fixes.tsv`; the agents' own reports in
`sourcing/web_results/` and the evidence files are untouched.

## Continuing the web pass (resumable state)

Everything needed to resume the web pass lives in the repository, so a fresh clone can carry
on from the last commit without any external state:

| path | contents |
| --- | --- |
| `sourcing/batches/batch_NNNN.tsv` | the 227 batches of ~170 lines each (id, author, quote), most-quoted authors first, produced once by `make_batches.py`, plus the `NNNNb` recovery batches and the `batch_0228` cleanup batch written by hand from the ids left over |
| `sourcing/web_results/batch_NNNN.jsonl` | the raw JSONL returned by the agent that searched that batch (one object per line: id, status, sources, evidence, queries) |
| `sourcing/orchestrator_state.json` | which batches were dispatched (batch -> session id), received, which sessions were archived, and which runs failed and why |
| `sourcing/evidence/web_search_agents.jsonl` | the normalised union of all `web_results`, rebuilt by `web_to_evidence.py` |
| `sourcing/orchestrate/` | the scripts below |

Scripts (run from the repository root):

- `orchestrate/make_sibling_prompt.py batches/batch_NNNN.tsv batch_NNNN <parent session id>`
  prints the complete prompt for one searching session: rules, evidence policy, result format,
  the line numbers to process, and the return channel (publish the JSONL as a page titled
  `Quotables results batch_NNNN`, then schedule a one-line notification to the parent session).
  The session republishes its page every 20 rows so a run killed by a usage limit loses at
  most 20 rows.
- `orchestrate/handle_result.sh batch_NNNN <saved page.html>` extracts the JSONL into
  `web_results/`, marks the batch received, rebuilds the evidence file and the sources column.
- `orchestrate/mark_dispatched.py dispatched|archived|failed|status ...` records state changes.

Resume procedure after an interruption (usage limit, container loss):

1. `python3 sourcing/orchestrate/mark_dispatched.py status` lists batches in flight and the next
   undispatched ones.
2. For each batch in flight, check its session. If it finished, save its results page and run
   `handle_result.sh`. If it died, save whatever partial page it published, run
   `handle_result.sh` on that (rows it never reached simply stay absent), record it with
   `mark_dispatched.py failed`, and dispatch the batch again; `web_to_evidence.py` keeps one
   record per line, so a re-run of already-covered rows is harmless.
3. Dispatch the next batches with `make_sibling_prompt.py` and record them with
   `mark_dispatched.py dispatched`.
4. Commit `author-quote.txt`, `sourcing/evidence/`, `sourcing/web_results/` and
   `sourcing/orchestrator_state.json` after every ingested batch.

Rows the agents could not search (budget exhausted) are never written as `unverified`; they
stay absent from the evidence file and are picked up again by the resume procedure.

## Coverage

| step | lines with a source |
| --- | --- |
| citation datasets (foba Wikiquote extracts, Bartlett) | 198 (106 found by no other step) |
| verbatim location in Gutenberg full texts, first pass (94 works + Shakespeare) | 561 (539 found by no other step) |
| verbatim location in Gutenberg full texts, second and third passes (3,631 works, 316 authors) | 1,296 (228 found by no other step) |
| web-search agents (sourced) | 12,201 |
| web-search agents (misattributed, kept as `[]`) | 771 |
| **lines with at least one source, before the discovery phase** | **13,087 of 39,269 (33.3%)** |
| deep-search batches (batch_w001 to w010) over already-unsourced classical quotes | 629 |
| discovery phase: quotes added, each arriving with a first-hand source | 2,674 |
| of those, additionally confirmed verbatim in public-domain full text | 84 |
| **lines with at least one source** | **16,390 of 41,943 (39.1%)** |

The discovery phase moves the percentage without moving the unsourced count, because every
line it adds already carries a source: only the denominator grows. The deep-search batches are
the ones that move the unsourced count, since they re-search lines the corpus already held -
26,182 down to 25,553 so far - and they also produce findings that are not sources: 319 quotes
newly documented as misattributed, which keep `[]` as the strict policy requires. Those sit in
`sourcing/evidence/web_deep_search.jsonl` alongside the 1,358 the deeper search still could not
place.

The web pass is complete: all 39,269 lines were searched, in 239 batch runs (batches 0000 to
0227, plus eleven "b" recovery batches for the remainders of batches killed mid-run, plus one
22-row cleanup batch for rows whose original agent ran out of search budget). Every batch was
run under the strict evidence policy: only citation-tracking references count, and an
aggregator listing never does, even when it names a book. The raw agent statuses across the
whole corpus are 12,608 sourced, 667 misattributed and 25,486 unverified (the 22 `unsearched`
placeholders left by two earlier agents are superseded by batch_0228 and skipped at merge time);
`web_to_evidence.py` then downgraded 399 of the `sourced` rows to `unverified` because every
URL they cited was an aggregator (the full list is `sourcing/audit/strict_downgrades.tsv`),
leaving the 12,203 web-sourced lines above.

The full audit trail of the agents (prompts, searches, result pages, per-session ledger with
costs) is in `sourcing/audit/`: 305 sessions, about USD 3,526 in total. The full-text passes
have their own ledgers: `fulltext_books_*.tsv` lists every book queued, with a SHA-256 of the
exact text searched, and `fulltext_searched_*.tsv` records every (work, quote) pair compared,
hit or miss, with its score. The evidence files
record, for every sourced line, which step produced it and what it matched against.

## Adding quotes (the discovery phase)

Everything above is about sourcing quotes the corpus already held. A later phase went the
other way: agents searched for notable quotations *not* in the corpus, on condition that each
one arrived already carrying a first-hand source. That makes it the only part of this project
where a source is a precondition rather than a result, and it is riskier than sourcing for a
reason worth stating plainly. When sourcing, the quote text is fixed by the corpus and only
the citation is in question. When discovering, an agent could produce a line from its own
memory and then attach a real-looking citation to it - a misquote with a credible source,
which is worse for this corpus than no quote at all.

Every discovery prompt is therefore built around one rule: **both the quote text and its
citation must be read off the same page.** The prompts are in `sourcing/audit/prompts/`
(`batch_dNN.txt` for discovery, `batch_wNNN.txt` for the deeper re-search of quotes already
in the corpus), generated by `sourcing/orchestrate/make_discovery_prompt.py` and
`make_deep_search_prompt.py`. Categories were chosen to reach people the corpus underserved -
Nobel lecture laureates, jurists, astronauts, suffragists, mathematicians, and writers and
leaders of Africa, Asia, the Middle East and Latin America, among others; the full map of
batch to category is in `sourcing/discovery_state.json`.

### The gate

Nothing reaches the corpus without passing `sourcing/validate_additions.py`, which writes a
verdict for every row to `sourcing/audit/additions_ledger.tsv` - accepted and rejected alike,
with the reason. A row is rejected unless it has an author, a quote and at least one source;
the quote is 20 to 600 characters and at least four words; no field holds a control
character; at least one evidence URL is present and they are not all aggregators; the source
names a work rather than being a bare URL or a repeat of the author's name; and the quote is
not already in the corpus, under this author or any other, nor duplicated within the run.

Four further rules exist because reviewing the accepted rows found things the list above let
through:

- **Second-hand sources.** A source can name a real book and still not be first-hand. Two
  shapes are rejected: a third party's recollection of a remark, where the only work named
  belongs to somebody else ("recorded in *My Brain Is Open* (1998) by Bruce Schechter"), and
  a biography *of* the speaker, written by somebody else, as with Nelson's telescope line and
  Southey's *Life of Nelson*. The rule is deliberately narrow, because three neighbouring
  shapes have to survive it. An autobiography is the strongest first-hand source there is, so
  *Personal Memoirs of General U. S. Grant* and *The Memoirs of Marshal Zhukov* pass - only a
  *Life of* someone, by someone else, is caught. A self-report passes: Hillary recounting his
  own Everest line in his own book, Kay recounting his own 1971 remark in his own email. And a
  contemporaneous press record of a speech passes, which is what keeps Sojourner Truth's Akron
  remarks as Marius Robinson printed them in the *Anti-Slavery Bugle* three weeks later - the
  source scholarship prefers over the rewrite published twelve years afterwards.

- **Contested works.** A quote can be copied faithfully out of a book and still not be
  something the person said, if the book's own authenticity is disputed. Shostakovich's
  *Testimony* (1979) is the case that prompted the rule: Laurel Fay and Richard Taruskin showed
  that passages Volkov presents as dictated recollection reproduce articles Shostakovich had
  published earlier. A row resting on nothing but such a work is rejected with the reason.

- **Withdrawals.** `sourcing/audit/withdrawn_additions.tsv` lists rows pulled after a
  spot-check read an independent source, with the reason and what they were checked against,
  and the validator rejects anything listed there - so a withdrawal survives re-ingestion
  instead of returning on the next rebuild.

- **Hedged evidence.** A row whose evidence note hedges about *which* entry on a page the
  citation came from is rejected. This caught the one failure that no amount of checking
  whether a source "names a work" can: Gauss's "Mathematics is the queen of the sciences"
  arrived citing a Letter to Bessel (1826), a locator that really is on the Wikiquote page it
  cites - beside a different quote. The citation was real, the URL was real, and the pairing
  was wrong. Exactly one row in a thousand hedged that way, and it was that one.

### Corroborating added quotes against full text

Most added rows rest on a single citation-tracking page, overwhelmingly a Wikiquote sourced
section. That clears the bar, but it is one channel, and a page naming a book is still a page
talking about the book. Where the work is public domain the text itself can be read instead.

`sourcing/corroborate_fulltext.py` parses the work out of each row's source string and matches
it against the Project Gutenberg catalogue, requiring two shared author name tokens so a title
match can never credit one author's words to another. `sourcing/corroborate_run.py` then drives
`locate_fulltext.py` over each text, and `sourcing/apply_corroboration.py` writes what was
found into the source column *alongside* the original citation rather than in place of it: the
citation names the work as a scholar would, and the confirmation says the words are
demonstrably in that work's text at a named section, in a text whose digest is recorded.

Three outcomes matter, and the third is the reason to run it at all. *Confirmed*: the quote is
in the work the row names. *Relocated*: the quote is in a different work by the same author -
Keynes's line on money is in *A Tract on Monetary Reform* (1923), which the row had cited
through *Essays in Persuasion* (1931), the collection that reprints the essay; the Tract is
named first as the earlier appearance. *Not found*: no conclusion, and the row keeps the source
it has, because editions and translations differ and absence from one Gutenberg text is no
evidence against the attribution.

Reproduce it with `sourcing/orchestrate/run_corroboration.sh <scratch-dir>` (needs
`pip install rapidfuzz unidecode`, and roughly a gigabyte of scratch space per few hundred
books). Its ledgers are `fulltext_corroboration.tsv` (per quote, with the text digest),
`fulltext_books_corroboration.tsv` (every book, searched or not mirrored on GITenberg) and
`fulltext_searched_corroboration.tsv` (every comparison, hit or miss).

### Rebuilding

`sourcing/orchestrate/rebuild_with_additions.sh` rebuilds `author-quote.txt` from a fixed base
commit plus every file in `sourcing/additions/`, rather than appending to the current file.
That is deliberate: agents keep pushing rows while the pass runs, so the rebuild runs many
times, and rebuilding from the base means a re-run can neither double-add a quote nor fill the
ledger with "already in the corpus" rejections that are really an earlier run's own work.
`sourcing/orchestrate/sync_additions.sh` pulls what the agents pushed, resolving conflicts by
ownership rather than by taking one side wholesale.

`sourcing/orchestrate/refresh_counts.py` rewrites every count quoted in `README.md` and in the
coverage table above, reading them off the corpus and the evidence files rather than from a
previous version of the prose. Each ingest moves five or six of those figures, and editing them
by hand is how a published number drifts away from the file it describes. Run it after each
rebuild; `--check` reports staleness without writing, and exits non-zero, which is what a
pre-push check wants.

### Spot-checks

`sourcing/audit/addition_spotchecks.tsv` records rows checked by hand against a source
independent of the one the agent used, with the verdict. These are the project's own sampling
of its agents' work, not a claim about every row.

They have found two kinds of defect that no automatic check in this pipeline can see, because
both leave a real citation pointing at a real work:

- **The wrong line on the right page.** Gauss's "Mathematics is the queen of the sciences" was
  recorded against a citation that belonged to a neighbouring quotation on the same page. The
  reference existed, the URL resolved, and the pairing was still wrong. Two gates came out of
  this one: a row is rejected when its evidence hedges about which entry on the page it came
  from, and withdrawn pairings are kept in `withdrawn_additions.tsv` so they cannot return.
- **The right work, the wrong words.** A row read "The electric things have their life too"
  where *Do Androids Dream of Electric Sheep?* reads "The electric things have their lives,
  too", and Martha Graham's *This I Believe* essay was cited under the title of a different
  essay of hers. The book, the chapter and the author were right in both cases. Only reading
  the text catches this, which is the argument for sampling by hand rather than trusting the
  gate.

Of 14 checks, 12 confirmed and 2 found defects; both defects were corrected, and the failing
checks are recorded as failures rather than quietly fixed.

## Verifying the file

`sourcing/verify_corpus.py` checks `author-quote.txt` against every invariant this
documentation claims for it, and exits non-zero on any failure, so it can be wired into a
pre-push hook:

```
python3 sourcing/verify_corpus.py
41,620 lines / 15,856 sourced (38.1%) / 3,693 people
3 duplicate pair(s) inherited from the base corpus, left in place: 3916/3921, 20438/20459, 29147/29153
every invariant holds
```

It checks that every line has three tab-separated columns and no control characters, that
column 3 parses as a JSON list of strings, that no author or quote is empty, that no source
names an aggregator or is only a bare year, and that every evidence id points at a line that
exists.

The duplicate report is deliberately not a failure. Three (author, quote) pairs were already
duplicated in the corpus before this project touched it - Disraeli on means and leisure, Keats
on unheard melodies, Ovid on being asked - and they cannot be removed, because every id in
`sourcing/evidence/` is a line number into the base corpus and deleting a line would silently
repoint thousands of citations. A duplicate involving an *added* line does fail, since
`validate_additions.py` is supposed to reject those before they land.

## Known limits

- Twelve people are spelled two ways in the corpus, each an accented form against an ASCII
  flattening of it - Molière/Moliere, Čapek/Capek, Buñuel/Bunuel, Machiavelli with and
  without the grave, and so on. Every one of those pairs was in the file before this project
  began, and both spellings carry quotes. They are left alone: rewriting an author's name
  across the corpus is a decision for whoever owns the data, not for a sourcing pass, and the
  line numbers in `sourcing/evidence/` would survive a rename but the author index would
  change under anyone reading it. What the pipeline does guarantee is that no *added* row
  introduces or widens such a split: `validate_additions.py` folds an added author onto the
  spelling the corpus already uses, choosing the majority spelling where the corpus itself is
  inconsistent.
- Coverage is partial. Many lines in this corpus circulate only on aggregator sites and have
  no traceable origin; those keep `[]`. Lines that citation trackers flag as misattributed
  also keep `[]` (the finding is in the evidence file).
- Web-search evidence is only as good as the search snippet; Wikiquote, Quote Investigator
  and dictionary-of-quotations references were preferred, but a spot check before relying on
  any single line is advisable.
- Bartlett (1860s edition) and Gutenberg texts use the spelling and titles of their editions.
- Finding a quote verbatim in an author's book proves the line is *in* that book, not always
  that the author coined it: an author may be quoting someone else. Andrew Carnegie's
  autobiography, for example, contains "He that cannot reason is a fool..." but introduces it
  as an inscription he is repeating. The full-text steps therefore store the surrounding
  excerpt (`ref_quote`) in the evidence file, so the context is visible to anyone checking a
  line; they do not try to decide authorship, which is what the corpus's own author column
  asserts.
- Corpus quotes are often modernised versions of the original wording - Josh Billings'
  dialect spelling regularised, a nineteenth-century "a man...he" rewritten as "you". The
  fuzzy threshold (>= 92, or >= 97 under 30 characters) is what lets those match their
  source; every accepted match keeps its score and excerpt in the evidence file.
