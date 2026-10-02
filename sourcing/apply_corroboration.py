#!/usr/bin/env python3
"""Fold full-text confirmations into the source column of the corpus.

An added quote arrives citing a work, usually on the strength of one citation-tracking page.
Where the work is public domain, `corroborate_fulltext.py` and `locate_fulltext.py` go and
read the text, and `sourcing/audit/fulltext_corroboration.tsv` records what was found. This
script writes that finding into the corpus alongside the original citation rather than in
place of it, because the two say different things and both are worth keeping: the citation
names the work and its locator as a scholar would, and the confirmation says the words are
demonstrably in that work's text, at a named section, in a text whose digest is recorded.

A `relocated` verdict means the quote was found in a DIFFERENT work by the same author -
Keynes's line on money turns up in A Tract on Monetary Reform, which the row cited through
the 1931 collection that reprints it. There the located work is named first, as the earlier
appearance, and the row's original citation is kept after it.

Usage: apply_corroboration.py author-quote.txt fulltext_corroboration.tsv out.txt
"""
import csv, json, re, sys, unicodedata


def key(s):
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "", s)


def confirmation(row):
    """The sentence recording that the words are in the text itself."""
    work, _, locator = row["located"].partition(", ")
    where = f", {locator}" if locator else ""
    return (f"verbatim in the Project Gutenberg text of {work}{where} "
            f"(PG {row['pg_id']}, text sha256 {row['text_sha256'][:12]})")


def main(corpus, corroboration, out):
    byq = {}
    for row in csv.DictReader(open(corroboration, encoding="utf8"), delimiter="\t"):
        byq[(key(row["author"]), key(row["quote"]))] = row

    applied = relocated = 0
    with open(out, "w", encoding="utf8") as f:
        for line in open(corpus, encoding="utf8"):
            a, q, col = line.rstrip("\n").split("\t")
            row = byq.get((key(a), key(q)))
            if row:
                srcs = json.loads(col) if col.strip() else []
                conf = confirmation(row)
                if conf not in srcs:
                    if row["verdict"] == "relocated":
                        srcs.insert(0, conf); relocated += 1
                    else:
                        srcs.append(conf)
                    applied += 1
                col = json.dumps(srcs, ensure_ascii=False)
            f.write(f"{a}\t{q}\t{col}\n")
    print(f"{applied} rows gained a full-text confirmation "
          f"({relocated} of them naming an earlier work than the row cited)")


if __name__ == "__main__":
    main(*sys.argv[1:4])
