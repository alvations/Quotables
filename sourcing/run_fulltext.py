#!/usr/bin/env python3
"""Run locate_fulltext.py for every work in gitenberg_manifest.json.
Usage: python3 run_fulltext.py author-quote.txt manifest.json evidence_out.jsonl"""
import json, os, re, subprocess, sys
corpus, manifest, out = sys.argv[1:4]
works = json.load(open(manifest))
if os.path.exists(out): os.remove(out)
here = os.path.dirname(os.path.abspath(__file__))
for w in works:
    tf = w.get("text_file") or ""
    if not os.path.isabs(tf): tf = os.path.join(w["path"], tf)
    if not os.path.exists(tf):
        cands = sorted([os.path.join(w["path"], f) for f in os.listdir(w["path"]) if f.endswith(".txt")], key=os.path.getsize, reverse=True)
        if not cands: print("no text for", w["repo"], file=sys.stderr); continue
        tf = cands[0]
    author_re = "^" + re.escape(w["author"]) + "$"
    subprocess.run([sys.executable, os.path.join(here, "locate_fulltext.py"), corpus, out, author_re,
                    w["work"], str(w.get("year") or 0), str(w["pg_id"]), tf], check=True)
