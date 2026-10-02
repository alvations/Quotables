#!/usr/bin/env python3
"""Search each corroboration job's text for the added quotes, and write the three ledgers.

Called by orchestrate/run_corroboration.sh once the job list is built and the GITenberg
clones are in place. It does no matching of its own: locate_fulltext.py does that, and this
only drives it, compares each hit against the work the row claimed, and records the result.

Usage: corroborate_run.py <scratch-dir>
"""
import glob, hashlib, json, os, re, subprocess, sys, unicodedata


def fold(s):
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower()
    return {w for w in re.sub(r"[^a-z0-9]+", " ", s).split() if len(w) > 2}


def author_regex(names):
    """Match the corpus spelling of any author who claimed this book, on surname."""
    parts = []
    for n in names:
        flat = unicodedata.normalize("NFKD", n).encode("ascii", "ignore").decode()
        words = [w for w in flat.split() if len(w) > 2]
        parts.append(re.escape(words[-1] if words else flat))
    return "(" + "|".join(sorted(set(parts))) + ")"


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def main(work):
    jobs = json.load(open(f"{work}/corroborate_jobs.json", encoding="utf8"))["jobs"]
    added = [json.loads(l) for l in open("sourcing/audit/added_quotes.jsonl", encoding="utf8")
             if l.strip()]

    # A corpus-shaped file of just the added rows, so locate_fulltext.py can look for them.
    with open(f"{work}/added.tsv", "w", encoding="utf8") as f:
        for r in added:
            f.write(f"{r['author']}\t{r['quote']}\t[]\n")

    # The largest .txt in each clone is the book; the rest is repo furniture.
    texts = {}
    for j in jobs:
        d = f"{work}/books/{j['pg_id']}"
        cands = [p for p in glob.glob(f"{d}/*.txt")
                 if not re.search(r"(?i)readme|license|metadata", p)]
        if cands:
            texts[j["pg_id"]] = max(cands, key=os.path.getsize)

    ev, tr = f"{work}/corroborate_evidence.jsonl", f"{work}/corroborate_trace.tsv"
    for p in (ev, tr):
        if os.path.exists(p):
            os.remove(p)

    searched = 0
    for j in jobs:
        t = texts.get(j["pg_id"])
        if not t:
            continue
        year = re.search(r"\b1[0-9]\d\d\b", " ".join(j["titles_claimed"]))
        r = subprocess.run(
            ["python3", "sourcing/locate_fulltext.py", f"{work}/added.tsv", ev,
             author_regex(j["authors"]), j["catalog_title"].splitlines()[0],
             year.group(0) if year else "0", j["pg_id"], t, "--trace", tr],
            capture_output=True, text=True)
        if r.returncode == 0:
            searched += 1
        else:
            tail = (r.stderr.strip().splitlines() or ["?"])[-1]
            print(f"  [{j['pg_id']}] failed: {tail[:120]}")
    print(f"{searched} of {len(jobs)} books searched "
          f"({len(jobs) - len(texts)} not mirrored on GITenberg)")

    hits = [json.loads(l) for l in open(ev, encoding="utf8")] if os.path.exists(ev) else []
    byid = {j["pg_id"]: j for j in jobs}
    digests = {pid: sha256(p) for pid, p in texts.items()}

    rows = []
    for h in hits:
        r = added[h["line"] - 1]
        pid = h["dataset"].split("pg")[-1]
        claimed = " | ".join(r["sources"])
        # "confirmed" when the located work is the one the row names; "relocated" when the
        # quote is really in a different work by the same author, which is the outcome no
        # amount of web corroboration would have caught.
        verdict = ("confirmed" if fold(h["source"].split(",")[0]) & fold(claimed)
                   else "relocated")
        rows.append({"verdict": verdict, "author": r["author"], "quote": r["quote"],
                     "claimed_source": claimed, "located": h["source"], "pg_id": pid,
                     "score": h["score"], "gitenberg_repo": byid[pid]["gitenberg_repo"],
                     "text_sha256": digests.get(pid, "")})

    cols = ["verdict", "author", "quote", "claimed_source", "located", "pg_id", "score",
            "gitenberg_repo", "text_sha256"]
    with open("sourcing/audit/fulltext_corroboration.tsv", "w", encoding="utf8") as f:
        f.write("\t".join(cols) + "\n")
        for r in sorted(rows, key=lambda r: (r["verdict"], r["author"])):
            f.write("\t".join(str(r[c]).replace("\t", " ") for c in cols) + "\n")

    with open("sourcing/audit/fulltext_books_corroboration.tsv", "w", encoding="utf8") as f:
        f.write("pg_id\tcatalog_author\tcatalog_title\tgitenberg_repo\tstatus"
                "\tquotes_claimed\tbytes\tsha256\n")
        for j in sorted(jobs, key=lambda j: -j["quotes"]):
            p = texts.get(j["pg_id"])
            f.write(f"{j['pg_id']}\t{j['catalog_author']}\t{j['catalog_title'].splitlines()[0]}\t"
                    f"{j['gitenberg_repo']}\t{'searched' if p else 'not-mirrored-on-gitenberg'}\t"
                    f"{j['quotes']}\t{os.path.getsize(p) if p else 0}\t"
                    f"{digests.get(j['pg_id'], '')}\n")

    # Every comparison made, hit or miss, so the trail shows what was looked at rather than
    # only what was found.
    with open("sourcing/audit/fulltext_searched_corroboration.tsv", "w", encoding="utf8") as f:
        f.write("pg_id\twork\tadded_row\tverdict\tscore\n")
        if os.path.exists(tr):
            f.write(open(tr, encoding="utf8").read())

    n_conf = sum(1 for r in rows if r["verdict"] == "confirmed")
    print(f"{n_conf} quotes confirmed in the work their row names, "
          f"{len(rows) - n_conf} located in a different work by the same author")


if __name__ == "__main__":
    main(sys.argv[1])
