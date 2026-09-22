#!/usr/bin/env python3
"""Pick Project Gutenberg books worth searching for the quotes that are still unsourced.

The web pass leaves ~26k quotes without a first-hand source. Most are modern interview
soundbites with no published text to check, but a substantial minority belong to
public-domain authors whose works CAN be checked verbatim - which is the strongest evidence
this project accepts, because the quote is found in the work itself rather than in a page
that talks about it.

This script decides which books to fetch. It never assigns a source; it only says where to
look. `locate_fulltext.py` then does the actual matching, and a quote is sourced only if it
is found in the text.

Method
------
1. An author counts as public-domain-era when the publication years already cited in their
   SOURCED quotes have a median before 1930. This is measured from the corpus itself rather
   than from a hand-written list or from recollection.
2. Those authors are matched against the Gutenberg catalog (hugovk/gutenberg-metadata, a
   mirror of the PG catalogue; gutenberg.org itself is not reachable from this environment).
   A match requires TWO shared name tokens, or an exact single-token match for authors who
   are mononyms in both the corpus and the catalogue (Aesop, Voltaire, Plutarch, Confucius).
3. Single-token matches are then audited by hand, because this is where misattribution
   creeps in: "Tecumseh" matches William *Tecumseh* Sherman, which would have credited
   Sherman's memoirs to the Shawnee leader. Confirmed collisions are listed in EXCLUDE.
4. Non-English editions are dropped (the corpus is English) and each author is capped at
   MAX_BOOKS so one prolific novelist cannot crowd out everyone else.

Repository names follow GITenberg's convention, `<title-slug>_<pg_id>`, which was verified
against 18 books already in gitenberg_manifest.json before being used to generate new ones.

Usage: build_gutenberg_jobs.py author-quote.txt gutenberg-metadata.json jobs.json
"""
import collections, json, re, statistics, sys, unicodedata

MAX_BOOKS = 25
PD_CUTOFF = 1930
# author names whose single-token catalogue match is a different person
EXCLUDE_AUTHORS = {"Tecumseh"}          # -> William Tecumseh Sherman
YEAR = re.compile(r"\b(1[0-9]{3}|20[0-2][0-9])\b")


def tokens(s):
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower()
    return set(re.sub(r"[^a-z ]", " ", s).split())


def slug(title):
    t = unicodedata.normalize("NFKD", title).encode("ascii", "ignore").decode()
    return re.sub(r"[^A-Za-z0-9]+", "-", t).strip("-")


def main(corpus, catalog, out):
    years, unsourced = collections.defaultdict(list), collections.Counter()
    for line in open(corpus, encoding="utf8"):
        author, _, col3 = line.rstrip("\n").split("\t")
        sources = json.loads(col3)
        if sources:
            for s in sources:
                years[author] += [int(y) for y in YEAR.findall(s)]
        else:
            unsourced[author] += 1

    public_domain = {a for a, ys in years.items()
                     if ys and statistics.median(ys) < PD_CUTOFF and unsourced[a]
                     and a not in EXCLUDE_AUTHORS}

    pg = json.load(open(catalog))
    by_author = collections.defaultdict(list)
    for pid, rec in pg.items():
        for name in rec.get("author") or []:
            by_author[frozenset(tokens(name))].append(pid)

    jobs = []
    for author in sorted(public_domain, key=lambda a: -unsourced[a]):
        ours, books = tokens(author), []
        for key, pids in by_author.items():
            shared = key & ours
            # two shared tokens, or a mononym that matches exactly on both sides
            if len(shared) >= 2 or (len(shared) == 1 and len(key) == 1 and len(ours) == 1):
                books += pids
        for pid in books[:MAX_BOOKS]:
            rec = pg[pid]
            langs = rec.get("language") or []
            if langs and not any("en" in str(x) for x in langs):
                continue
            title = (rec.get("title") or [""])[0].split("\n")[0]
            if not title:
                continue
            jobs.append({"author": author, "pg_id": int(pid), "title": title,
                         "repo": f"{slug(title)}_{pid}", "unsourced": unsourced[author]})

    json.dump(jobs, open(out, "w"), indent=1)
    authors = {j["author"] for j in jobs}
    print(f"{len(public_domain)} public-domain-era authors with unsourced quotes", file=sys.stderr)
    print(f"{len(jobs)} books queued across {len(authors)} authors, "
          f"covering {sum(unsourced[a] for a in authors)} unsourced quotes", file=sys.stderr)


if __name__ == "__main__":
    main(*sys.argv[1:4])
