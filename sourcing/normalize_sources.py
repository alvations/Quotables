#!/usr/bin/env python3
"""Normalize the source strings in column 3 of author-quote.txt.

`build_column.py` writes the sources exactly as the agents reported them. A format audit of
the finished corpus (see sourcing/audit/format_fixes.tsv) found a small number of strings that
break the format the spec states - work title, year, locator - or that are not first-hand
sources at all. This script applies those corrections, keyed on the exact source string so a
string that appears on several lines is fixed on all of them.

It runs AFTER build_column.py, so a full rebuild of the corpus is:

    python3 sourcing/web_to_evidence.py sourcing/evidence/web_search_agents.jsonl sourcing/web_results/*.jsonl
    python3 sourcing/build_column.py author-quote.txt author-quote.txt sourcing/evidence/*.jsonl
    python3 sourcing/normalize_sources.py author-quote.txt author-quote.txt

Only formatting is changed, with two exceptions listed under DROP: strings that report a
third-hand attribution rather than a first-hand work. Those lines fall back to `[]`, which is
what the strict evidence policy requires. The agents' own reports stay untouched in
sourcing/web_results/ and the evidence files, so nothing is lost.

Usage: normalize_sources.py <in.txt> <out.txt>
"""
import json, sys

# exact source string -> replacement
REWRITE = {
    # the author's name is column 1's job; these repeat it as an attribution rather than as
    # part of a work's title (titles that genuinely begin with the name are left alone)
    "Alexandra Daddario, interview by Chris Wallace, Interview Magazine (5 June 2014)":
        "Interview by Chris Wallace, Interview Magazine (5 June 2014)",

    # YYYYMMDD is a machine date; the spec asks for a readable locator
    "New York Journal-American (19610711)":
        "New York Journal-American (11 July 1961)",
    "Interview in Chicago Tribune (19160525)":
        "Interview in Chicago Tribune (25 May 1916)",
    "PBS “Interview:  On freedom and free markets” Commanding Heights series (20001001)":
        "PBS, ‘Interview: On freedom and free markets’, Commanding Heights series (1 October 2000)",
    "Observer  (19740922), also in Oxford Dictionary of Modern Quotes, Third Edition, "
    "Elizabeth Knowles, edit., Oxford University Press (2007) p124":
        "Observer (22 September 1974), also in Oxford Dictionary of Modern Quotes, "
        "3rd ed., Elizabeth Knowles (ed.), Oxford University Press (2007), p. 124",

    "1990s. As quoted in Fortune (19981109); also quoted in \"TIME digital 50\" in "
    "TIME digital archive (1999)":
        "As quoted in Fortune (9 November 1998); also quoted in \u2018TIME digital 50\u2019, "
        "TIME digital archive (1999)",
    "As quoted in \"Rules That Warren Buffett Lives By\" by  Stephanie Loiacono at "
    "Yahoo Finance (20100223)":
        "As quoted in \u2018Rules That Warren Buffett Lives By\u2019 by Stephanie Loiacono, "
        "Yahoo Finance (23 February 2010)",

    # a source string is a citation, not a commentary; the surrounding note is kept in the
    # evidence file, where it belongs
    "Hemingway's famous phrase in a letter to F. Scott Fitzgerald (19260420), published in "
    "Ernest Hemingway: Selected Letters 1917–1961 (1981) edited by Carlos Baker. In the "
    "letter, he wrote that he was \"not referring to guts but to something else.\" The phrase "
    "was later used by Dorothy Parker in a profile of Hemingway, \"The Artist's Reward,\" in "
    "the New Yorker (19291130)":
        "Letter to F. Scott Fitzgerald (20 April 1926), published in Ernest Hemingway: "
        "Selected Letters 1917–1961 (1981), ed. Carlos Baker",
}

# not first-hand: someone else reporting that the author said it. The strict policy treats
# these as unverified, so the line falls back to [].
DROP = {
    "Attributed to de Gaulle by Romain Gary in Life magazine (9 May 1969)",
    "Attributed saying, recorded in Souvenirs de J. Laffitte (1844)",
}

src, dst = sys.argv[1], sys.argv[2]
lines = open(src, encoding="utf8").read().splitlines()
rewritten = dropped = 0
log = []
out = []
for n, line in enumerate(lines, 1):
    author, quote, col3 = line.split("\t")
    sources = json.loads(col3)
    new = []
    for s in sources:
        if s in DROP:
            dropped += 1
            log.append((n, "dropped", s, ""))
            continue
        r = REWRITE.get(s, s)
        if r != s:
            rewritten += 1
            log.append((n, "rewritten", s, r))
        new.append(r)
    out.append(f"{author}\t{quote}\t{json.dumps(new, ensure_ascii=False)}")

open(dst, "w", encoding="utf8").write("\n".join(out) + "\n")
with open("sourcing/audit/format_fixes.tsv", "w", encoding="utf8") as f:
    f.write("line\taction\tbefore\tafter\n")
    for row in log:
        f.write("\t".join(str(x) for x in row) + "\n")
print(f"{rewritten} source strings rewritten, {dropped} dropped as not first-hand", file=sys.stderr)
