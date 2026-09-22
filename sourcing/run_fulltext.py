#!/usr/bin/env python3
"""Run locate_fulltext.py for every work in a gitenberg manifest.

Usage: run_fulltext.py author-quote.txt manifest.json evidence_out.jsonl [trace.tsv]

With a trace file, every (work, quote) pair that was actually compared is recorded - hits and
misses alike - so the audit trail shows what was searched, not just what was found."""
import json, os, re, subprocess, sys
corpus, manifest, out = sys.argv[1:4]
trace = sys.argv[4] if len(sys.argv) > 4 else None
works = json.load(open(manifest))
if os.path.exists(out): os.remove(out)
if trace and os.path.exists(trace): os.remove(trace)
if trace:
    with open(trace, "w", encoding="utf8") as fh:
        fh.write("pg_id\twork\tcorpus_line\tverdict\tscore\n")
here = os.path.dirname(os.path.abspath(__file__))
for w in works:
    tf = w.get("text_file") or ""
    if not os.path.isabs(tf): tf = os.path.join(w["path"], tf)
    if not os.path.exists(tf):
        cands = sorted([os.path.join(w["path"], f) for f in os.listdir(w["path"]) if f.endswith(".txt")], key=os.path.getsize, reverse=True)
        if not cands: print("no text for", w["repo"], file=sys.stderr); continue
        tf = cands[0]
    author_re = "^" + re.escape(w["author"]) + "$"
    cmd = [sys.executable, os.path.join(here, "locate_fulltext.py"), corpus, out, author_re,
           w["work"], str(w.get("year") or 0), str(w["pg_id"]), tf]
    if trace: cmd += ["--trace", trace]
    subprocess.run(cmd, check=True)
