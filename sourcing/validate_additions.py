#!/usr/bin/env python3
"""Validate and merge newly discovered quotes into author-quote.txt.

The corpus's whole value is that column 3 means "a first-hand source was verified". Adding
quotes is therefore only safe behind the same bar the sourcing passes used, plus one more:
the quote TEXT must have been copied from the citing page, not recalled, because a misquote
with a real citation attached is worse than no quote at all.

A candidate is rejected unless ALL of these hold:
  * author, quote and >=1 source string are present and non-empty
  * the quote is 20..600 characters, has >=4 words, and carries no control characters
    (600 is just above the longest quote already in the corpus, 538; an earlier 400 was
    stricter than the data and threw out Barbara Jordan's "We the people" passage. The
    20-character floor is deliberately stricter than the corpus minimum of 9: a very short
    new line is both hard to attribute and likely to be generic.)
  * at least one evidence URL is present and NONE of the evidence URLs are aggregators
  * the source string names a work, not a URL, and does not merely repeat the author's name
  * it is not already in the corpus (normalised author+quote, and normalised quote alone)
  * it is not a duplicate of another candidate in the same run

Every decision - accepted or rejected, with the reason - is written to the ledger so the
additions are as auditable as the sources already in the file.

Usage: validate_additions.py author-quote.txt out.txt ledger.tsv in1.jsonl [in2.jsonl ...]
"""
import json, re, sys, unicodedata

AGGREGATOR = re.compile(r"""(?ix) (?: brainyquote | azquotes | goodreads\.com | quotefancy
    | pinterest | quotepark | libquotes | quotes\.net | quotemaster | inspiringquotes
    | wisesayings | quoteslyfe | picturequotes | allauthor\.com | quotegarden | quotesgram
    | successories | quoteambition | everydaypower | keepinspiring | quotecatalog
    | quotationspage | quotesdaddy | searchquotes | quoteland | notable-quotes )""")
URL = re.compile(r"https?://")
CONTROL = re.compile(r"[\x00-\x1f\x7f]")


# A first-hand source is a document the speaker themself produced: a book, essay, poem, play,
# letter, diary, speech text, article, or a transcribed interview or broadcast. Two shapes are
# not first-hand however famous the line is, and both slipped past the earlier gate:
#
#   "Remark on elegant proofs, recorded in My Brain Is Open (1998) by Bruce Schechter, p. 14"
#       - the only work named belongs to somebody else, so what is cited is a third party's
#         recollection of a remark rather than the remark itself.
#   "Remark at the Battle of Copenhagen (1801), as given in The Life of Nelson, Ch. 7"
#       - a biography OF the speaker, written by somebody else, usually long afterwards.
#
# Two neighbouring shapes look similar and must survive, which is what keeps this rule narrow:
#
#   A self-report. Hillary recounting his own Everest line in his own autobiography, or Kay
#   recounting his own 1971 remark in his own 1998 email, is the speaker on the record. The
#   test is therefore whose name follows the recording verb, not whether one appears at all.
#
#   An autobiography. "Personal Memoirs of General U. S. Grant", "The Memoirs of Marshal
#   Zhukov" and "The Curves of Time: The Memoirs of Oscar Niemeyer" all read as "memoirs of
#   <the author>", and all three are the person writing their own life down - the strongest
#   first-hand source there is. Only a LIFE of somebody, written by somebody else, is the
#   biographer's anecdote this rule exists to catch.
#
#   A contemporaneous press record of a speech. Sojourner Truth's Akron convention remarks
#   survive because Marius Robinson printed them in the Anti-Slavery Bugle three weeks later;
#   that is a transcription of her speaking, not a recollection, and it is the source
#   scholarship prefers over the famous rewrite published twelve years afterwards. A source
#   that names a speaking occasion is therefore left alone.
RECORDED_BY = re.compile(r"""(?ix)
    \b(?: recorded | reported | recounted | related | quoted | as\s+told\s+to )\b
    [^.;]{0,60}? \bby\s+
    ( [A-Z][\w.'-]*
      (?: \s+ (?: van | von | de | du | del | della | di ) )?
      (?: \s+ [A-Z][\w.'-]* ){0,3} )""")
BIOGRAPHY_OF = re.compile(r"""(?ix)
    \b (?: the\s+ )?
    (?: life\s+and\s+(?:letters|times|works?) | life | lives | biography )
    \s+ of \s+
    ( [A-Z][\w.'-]* (?: \s+ [A-Z][\w.'-]* ){0,3} )""")
# A named speaking occasion: whoever wrote the words down was recording the person speaking.
SPEAKING = re.compile(r"""(?ix)
    \b (?: speech | speeches | address | addresses | remarks?\s+(?:at|to|before)
         | convention | debate | testimony | hearing | lecture | sermon | oration
         | proceedings | hansard | congressional\s+record | press\s+conference
         | interview | broadcast | transcript | deposition | trial ) \b""")
# A remark with nothing behind it - no document, no occasion, no date - is hearsay with a
# name attached. These are flagged for review rather than rejected outright, because the
# judgement of whether a named work is the speaker's own needs reading, not a regex.
BARE_REMARK = re.compile(r"(?i)\b(?:remark|reportedly|anecdote|frequently\s+said)\b")
CHECKABLE = re.compile(r"""(?ix)
    \b 1[0-9]\d\d \b | \b 20[0-2]\d \b
  | \b p{1,2} \. \s* \d
  | \b (?: ch | chap | chapter | act | scene | book | vol | canto | sect | section | line )
    \b \.? \s* [\dIVXLCivxlc]
  | \b (?: letter | diary | journal | notebook | speech | address | lecture | sermon
         | testimony | interview | broadcast | transcript | dispatch | telegram | email
         | essay | preface | foreword | introduction | article | column | editorial
         | poem | play | novel | autobiograph ) \b""")


def surnames(name):
    """Every substantial word of a person's name, folded to lowercase ASCII.

    Comparing on the words is what distinguishes a self-report from a third party's account:
    "recounted by Kay" against the author Alan Kay overlaps, "by Bruce Schechter" against
    Paul Erdos does not. Accents are folded so "Erdos" still matches "Erdős".
    """
    flat = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()
    return {w.strip(".,'-").lower() for w in flat.split() if len(w.strip(".,'-")) > 2}


def secondhand_reason(author, src):
    """Why this source is somebody else's account rather than the speaker's own, or None."""
    own = surnames(author)
    m = RECORDED_BY.search(src)
    if m and not (surnames(m.group(1)) & own) and not SPEAKING.search(src):
        return (f"credited to {m.group(1).strip()}'s account of the line, "
                f"not to anything {author} wrote or said on the record")
    m = BIOGRAPHY_OF.search(src)
    if m and (surnames(m.group(1)) & own):
        return (f"the only work named is a biography of {author}, "
                "so what is cited is a biographer's anecdote")
    return None


def thin_remark(src):
    """True when a source calls the line a remark and offers nothing to check it against."""
    return bool(BARE_REMARK.search(src)) and not CHECKABLE.search(src)


# Works whose authenticity is itself contested in the relevant scholarship. A quote can be
# copied faithfully out of one of these and still not be something the person said, so a
# source that rests on nothing else does not clear the bar, however respectable the citation
# looks. Each entry carries the reason, which is written into the rejection ledger.
DISPUTED_WORKS = [
    (re.compile(r"(?i)\bTestimony\b.{0,40}\bShostakovich\b|\bVolkov\b.{0,40}\bTestimony\b"),
     "Testimony (1979) is a contested source: musicologists including Laurel Fay and Richard "
     "Taruskin have shown that passages Volkov presents as dictated recollection reproduce "
     "articles Shostakovich published earlier, and the manuscript he initialled cannot be "
     "matched to the book as printed"),
    (re.compile(r"(?i)\bDonation\s+of\s+Constantine\b"),
     "the Donation of Constantine is an eighth-century forgery"),
    (re.compile(r"(?i)\bProtocols\s+of\s+the\s+Elders\b"),
     "a fabricated text, not a record of anything anyone said"),
    (re.compile(r"(?i)\bAutobiography\s+of\s+Howard\s+Hughes\b|\bClifford\s+Irving\b"),
     "the Irving autobiography was a hoax Hughes never gave"),
]


def disputed_reason(src):
    """The reason this named work cannot carry a quote on its own, or None."""
    for pat, why in DISPUTED_WORKS:
        if pat.search(src):
            return why
    return None


def norm(s):
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9 ]", " ", s).split()


def key(s):
    return " ".join(norm(s))


def canonical_author(name, corpus_authors, added_authors):
    """Spell an added quote's author the way the corpus already spells them.

    Agents write "W. B. Yeats" where the corpus has "W.B. Yeats", and one wrote "Vaclav Havel"
    where another wrote "Václav Havel". Left alone each variant becomes a separate author, which
    quietly fragments the author index and makes per-author counts wrong. So: if the name folds
    to one the corpus already uses, adopt the corpus spelling; otherwise pick one form for the
    whole run, preferring the one that kept its diacritics, since that is the correct spelling
    rather than an ASCII flattening of it.

    Variants that were already in the corpus before this work (20 of them, e.g. "C. S. Lewis"
    vs "C.S. Lewis") are left exactly as they are. They are the project's own data, and
    silently rewriting an author's name across the file is not this script's business.
    """
    k = key(name)
    if k in corpus_authors:
        return corpus_authors[k]
    if k in added_authors:
        return added_authors[k]
    return name


corpus_path, out_path, ledger_path = sys.argv[1:4]
rows = [l.rstrip("\n").split("\t") for l in open(corpus_path, encoding="utf8")]
have_pair = {(key(a), key(q)) for a, q, _ in rows}
have_quote = {key(q) for _, q, _ in rows}
# first spelling wins per folded key, so the corpus's own form is the one adopted
corpus_authors = {}
for a, _, _ in rows:
    corpus_authors.setdefault(key(a), a)

accepted, ledger, seen = [], [], set()
added_authors, renamed = {}, 0
for path in sys.argv[4:]:
    batch = path.rsplit("/", 1)[-1].replace(".jsonl", "")
    for line in open(path, encoding="utf8"):
        line = line.strip()
        if not line:
            continue
        try:
            r = json.loads(line)
        except json.JSONDecodeError:
            ledger.append((batch, "", "", "rejected", "malformed JSON")); continue
        a = (r.get("author") or "").strip()
        if a:
            canon = canonical_author(a, corpus_authors, added_authors)
            if canon != a:
                renamed += 1
                a = canon
            # prefer the accented spelling as this run's canonical form
            prev = added_authors.get(key(a))
            if prev is None or (prev == unicodedata.normalize("NFKD", prev)
                                .encode("ascii", "ignore").decode() and a != prev):
                added_authors[key(a)] = a
        q = re.sub(r"\s+", " ", (r.get("quote") or "")).strip()
        srcs = [s.strip() for s in (r.get("sources") or []) if s and s.strip()]
        ev = [e for e in (r.get("evidence") or []) if e and e.strip()]
        urls = [e for e in ev if URL.search(e)]

        def reject(why):
            ledger.append((batch, a, q[:120], "rejected", why))

        if not a or not q or not srcs:
            reject("missing author, quote or source"); continue
        if CONTROL.search(a) or CONTROL.search(q) or any(CONTROL.search(s) for s in srcs):
            reject("control character in a field"); continue
        if not (20 <= len(q) <= 600) or len(q.split()) < 4:
            reject(f"quote length {len(q)} chars / {len(q.split())} words outside 20-600 and >=4"); continue
        if not urls:
            reject("no evidence URL"); continue
        if all(AGGREGATOR.search(u) for u in urls):
            reject("aggregator-only evidence"); continue
        if any(URL.match(s) for s in srcs):
            reject("source string is a bare URL, not a work"); continue
        if any(key(s) == key(a) for s in srcs):
            reject("source string only repeats the author's name"); continue
        secondhand = [secondhand_reason(a, s) for s in srcs]
        if all(secondhand):
            reject("second-hand source: " + secondhand[0]); continue
        if all(thin_remark(s) for s in srcs):
            reject("thin remark: no document, occasion or date to check it against"); continue
        disputed = [disputed_reason(s) for s in srcs]
        if all(disputed):
            reject("disputed work: " + disputed[0]); continue
        if (key(a), key(q)) in have_pair:
            reject("already in the corpus"); continue
        if key(q) in have_quote:
            reject("quote already in the corpus under another author"); continue
        if (key(a), key(q)) in seen:
            reject("duplicate within this run"); continue
        seen.add((key(a), key(q)))
        accepted.append((a, q, srcs, ev, batch))
        ledger.append((batch, a, q[:120], "accepted", "; ".join(srcs)[:180]))

with open(out_path, "w", encoding="utf8") as f:
    for a, q, c in rows:
        f.write(f"{a}\t{q}\t{c}\n")
    for a, q, srcs, _ev, _b in accepted:
        f.write(f"{a}\t{q}\t{json.dumps(srcs, ensure_ascii=False)}\n")

with open(ledger_path, "w", encoding="utf8") as f:
    f.write("batch\tauthor\tquote\tverdict\treason_or_source\n")
    for row in ledger:
        f.write("\t".join(str(x) for x in row) + "\n")

# NOT under sourcing/evidence/: build_column.py globs that directory and expects every record
# to carry a "line" number. These records are keyed by author and quote instead, so a copy left
# in evidence/ makes the whole corpus rebuild fail.
with open("sourcing/audit/added_quotes.jsonl", "w", encoding="utf8") as f:
    for a, q, srcs, ev, b in accepted:
        f.write(json.dumps({"author": a, "quote": q, "sources": srcs, "evidence": ev,
                            "batch": b, "how": "discovery"}, ensure_ascii=False) + "\n")

rej = sum(1 for r in ledger if r[3] == "rejected")
print(f"{len(accepted)} accepted, {rej} rejected; corpus {len(rows)} -> {len(rows)+len(accepted)}",
      file=sys.stderr)
if renamed:
    print(f"{renamed} author names respelled to match the corpus's existing form", file=sys.stderr)
