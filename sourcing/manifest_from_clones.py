#!/usr/bin/env python3
"""Build a gitenberg-style manifest from the book clones that actually arrived.

GITenberg does not mirror every Project Gutenberg book, so roughly half the repositories
named in jobs.json do not exist. This walks the clone directory, keeps the ones that came
down with a usable plain-text file, and writes the manifest that run_fulltext.py consumes.

The `year` is left at 0 on purpose: the Gutenberg catalogue used here carries no reliable
publication date, and inventing one would put an unverified fact into the sources column.
locate_fulltext.py omits the year when it is 0, so the source reads "Work, Chapter" rather
than "Work (wrong-year), Chapter".

Usage: manifest_from_clones.py jobs.json <clone dir> manifest.json
"""
import glob, json, os, sys

jobs_path, clone_dir, out = sys.argv[1:4]
jobs = {j["repo"]: j for j in json.load(open(jobs_path))}

manifest, missing_text = [], 0
for path in sorted(glob.glob(os.path.join(clone_dir, "*"))):
    if not os.path.isdir(path):
        continue
    job = jobs.get(os.path.basename(path))
    if not job:
        continue
    texts = sorted(glob.glob(os.path.join(path, "*.txt")), key=os.path.getsize, reverse=True)
    if not texts:
        missing_text += 1
        continue
    manifest.append({"author": job["author"], "work": job["title"], "year": 0,
                     "pg_id": job["pg_id"], "repo": job["repo"], "path": path,
                     "text_file": os.path.basename(texts[0]),
                     "note": "fetched for the second full-text pass"})

json.dump(manifest, open(out, "w"), indent=1)
print(f"{len(manifest)} works with text ({missing_text} clones had no .txt)", file=sys.stderr)
print(f"{len({m['author'] for m in manifest})} authors", file=sys.stderr)
