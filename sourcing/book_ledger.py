#!/usr/bin/env python3
"""Record every book this project tried to search, whether or not it arrived.

The point of the ledger is that "we searched Gutenberg" is not an auditable claim. This
writes one row per book that was QUEUED, so the record distinguishes:

  fetched      the GITenberg repository existed, cloned, and had a plain-text file
  no-text      the repository existed but carried no usable .txt
  unavailable  GITenberg does not mirror that Project Gutenberg book (about half of them)
  excluded     deliberately left out, with the reason - name collisions and derivative
               excerpt collections, the two ways this pass could have invented a source

For every fetched book it records the byte count and a SHA-256 of the exact text that was
searched, so a later run can prove it searched the same bytes. The text itself is not
committed: the ~1,500 books run to several GB, and the pg_id plus checksum plus the
GITenberg URL already make the content reproducible.

Usage: book_ledger.py <jobs.json> <fetch.log> <clone dir> <out.tsv> [excluded.json]
"""
import glob, hashlib, json, os, sys

jobs_path, log_path, clone_dir, out = sys.argv[1:5]
# {repo: reason} - the reason is written into the ledger so an exclusion is never silent
excluded = json.load(open(sys.argv[5])) if len(sys.argv) > 5 else {}
if isinstance(excluded, list):
    excluded = {r: "excluded" for r in excluded}

jobs = json.load(open(jobs_path))
status = {}
for line in open(log_path, encoding="utf8"):
    parts = line.split()
    if len(parts) == 2 and parts[0] in ("OK", "MISS", "NOTXT"):
        status[parts[1]] = parts[0]

rows = []
for j in jobs:
    repo = j["repo"]
    path = os.path.join(clone_dir, repo)
    st, nbytes, digest, textfile, why = "unavailable", "", "", "", ""
    if repo in excluded:
        st, why = "excluded", excluded[repo]
    elif os.path.isdir(path):
        texts = sorted(glob.glob(os.path.join(path, "*.txt")), key=os.path.getsize, reverse=True)
        if texts:
            st, textfile = "fetched", os.path.basename(texts[0])
            data = open(texts[0], "rb").read()
            nbytes, digest = len(data), hashlib.sha256(data).hexdigest()
        else:
            st = "no-text"
    elif status.get(repo) == "OK":
        st = "no-text"
    rows.append((j.get("author", ""), j["pg_id"], j["title"], repo, st, why, nbytes, digest, textfile))

rows.sort(key=lambda r: (r[0], r[1]))
with open(out, "w", encoding="utf8") as f:
    f.write("author\tpg_id\ttitle\tgitenberg_repo\tstatus\treason\tbytes\tsha256\ttext_file\n")
    for r in rows:
        f.write("\t".join(str(x) for x in r) + "\n")

tally = {}
for r in rows:
    tally[r[4]] = tally.get(r[4], 0) + 1
print(f"{len(rows)} books in ledger: " + ", ".join(f"{v} {k}" for k, v in sorted(tally.items())),
      file=sys.stderr)
searched = sum(int(r[6]) for r in rows if r[6])
print(f"{searched/1e6:.1f} MB of text searched", file=sys.stderr)
