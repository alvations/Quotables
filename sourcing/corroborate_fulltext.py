#!/usr/bin/env python3
"""Decide which public-domain works to fetch in order to CORROBORATE added quotes.

Every added quote already names a work, and most of them rest on a single citation-tracking
page - overwhelmingly a Wikiquote sourced section. That clears the project's evidence bar,
but it is one channel, and a page that names a book is still a page talking about the book.
Where the work itself is public domain, the text can be read instead, which is the strongest
evidence this project accepts: the quote is found in the work rather than in a page about it.

This script never assigns or changes a source. It only says which book to fetch and which
added quotes to look for inside it. `locate_fulltext.py` does the matching, and a row is
corroborated only if the quote is actually found in the text.

Three outcomes are worth having, and the third is the reason to run this at all:
  confirmed  - the quote is in the work the row names. The source gains a second, stronger
               channel and stops depending on Wikiphrasing.
  relocated  - the quote is in a DIFFERENT work by the same author. The row named the wrong
               book, which no amount of web corroboration would have caught.
  not found  - no conclusion. Editions differ, translations differ, and a quote absent from
               the Gutenberg text of a work may still be in the work. Absence is not disproof,
               so the row keeps the source it has.

Usage: corroborate_fulltext.py added_quotes.jsonl gutenberg-metadata.json jobs.json
"""
import json, re, sys, unicodedata
from collections import defaultdict

# Words that carry no identifying weight in a title match, so that "An Inquiry into the Nature
# and Causes of the Wealth of Nations" and the catalogue's "The Wealth of Nations" still meet.
STOP = {"a", "an", "the", "of", "and", "or", "in", "on", "to", "for", "with", "by", "from",
        "into", "its", "his", "her", "their", "being", "upon", "concerning", "inquiry",
        "essay", "essays", "treatise", "discourse", "volume", "vol", "complete", "works",
        "selected", "collected", "part", "first", "second", "new", "edition"}


def fold(s):
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", " ", s).strip()


def toks(s):
    return [w for w in fold(s).split() if w not in STOP and len(w) > 2]


def work_title(src):
    """The work a source string names, with the locator trimmed off.

    A source reads like "An Inquiry into the Nature and Causes of the Wealth of Nations
    (1776), Book I, Chapter II" or "Walden (1854), 'Economy'". The title is what comes
    before the first year in parentheses, or before the first locator word if there is no
    year. Sources that name no work at all (a bare speech occasion) return None.
    """
    s = src.strip()
    s = re.split(r"\s*\((?:c\.\s*)?1[0-9]\d\d|\s*\(20[0-2]\d", s)[0]
    s = re.split(r",\s*(?:Book|Bk|Ch|Chap|Chapter|Part|Vol|Volume|Act|Scene|Canto|Letter|"
                 r"Essay|Section|Sect|Aphorism|p\.|pp\.|no\.|line)\b", s, flags=re.I)[0]
    s = re.sub(r"^(?:from|in|his|her|their)\s+", "", s, flags=re.I).strip(" ,;:.—-")
    # An occasion is not a work: "Speech to the House of Commons", "Letter to Mrs Dunbar".
    if re.match(r"(?i)^(speech|address|remarks?|lecture|sermon|interview|letter|telegram|"
                r"diary|journal|testimony|broadcast|press)\b", s):
        return None
    return s if len(toks(s)) >= 1 else None


def author_tokens(name):
    return {w for w in fold(name).split() if len(w) > 2}


def main(added, catalog, out):
    rows = [json.loads(l) for l in open(added, encoding="utf8") if l.strip()]

    # What to look for: (author, work title) -> the quotes claiming it.
    want = defaultdict(list)
    for r in rows:
        for s in r.get("sources") or []:
            t = work_title(s)
            if t:
                want[(r["author"], t)].append(r["quote"])
                break

    pg = json.load(open(catalog, encoding="utf8"))
    # Index the catalogue by author token so each wanted title is matched against that
    # author's books only - a title match across the whole catalogue would credit one
    # author's words to another, which is the single failure this must not produce.
    by_token = defaultdict(list)
    for pid, meta in pg.items():
        langs = meta.get("language") or []
        if langs and "en" not in langs:
            continue
        for a in meta.get("author") or []:
            for w in author_tokens(a):
                by_token[w].append((pid, a, meta))

    jobs = {}
    unmatched = []
    for (author, title), quotes in sorted(want.items()):
        atoks = author_tokens(author)
        if not atoks:
            continue
        cands = {}
        for w in atoks:
            for pid, a, meta in by_token.get(w, []):
                cands[pid] = (a, meta)
        best = None
        ttoks = set(toks(title))
        for pid, (a, meta) in cands.items():
            # The author must share two name tokens, so "Smith" alone never matches.
            if len(author_tokens(a) & atoks) < 2:
                continue
            for cat_title in (meta.get("title") or []):
                ctoks = set(toks(cat_title))
                if not ctoks or not ttoks:
                    continue
                # Every identifying word of the catalogue title must appear in the source's
                # title, or vice versa: that lets "The Wealth of Nations" meet Smith's full
                # eighteenth-century title without letting two unrelated books meet.
                if ctoks <= ttoks or ttoks <= ctoks:
                    score = len(ctoks & ttoks)
                    if best is None or score > best[0]:
                        best = (score, pid, a, cat_title)
        if best is None:
            unmatched.append({"author": author, "title": title, "quotes": len(quotes)})
            continue
        _, pid, cat_author, cat_title = best
        slug = re.sub(r"[^A-Za-z0-9]+", "-", cat_title).strip("-")
        jobs.setdefault(pid, {
            "pg_id": pid, "catalog_author": cat_author, "catalog_title": cat_title,
            "gitenberg_repo": f"{slug}_{pid}", "authors": [], "titles_claimed": [], "quotes": 0,
        })
        j = jobs[pid]
        if author not in j["authors"]:
            j["authors"].append(author)
        if title not in j["titles_claimed"]:
            j["titles_claimed"].append(title)
        j["quotes"] += len(quotes)

    out_obj = {"jobs": sorted(jobs.values(), key=lambda j: -j["quotes"]), "unmatched": unmatched}
    json.dump(out_obj, open(out, "w", encoding="utf8"), indent=1, ensure_ascii=False)
    tot = sum(j["quotes"] for j in out_obj["jobs"])
    print(f"{len(out_obj['jobs'])} books to fetch, covering {tot} added quotes")
    print(f"{len(unmatched)} (author, work) pairs with no public-domain match "
          f"({sum(u['quotes'] for u in unmatched)} quotes) - mostly works still in copyright")


if __name__ == "__main__":
    main(*sys.argv[1:4])
