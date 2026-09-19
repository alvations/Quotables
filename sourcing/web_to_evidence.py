#!/usr/bin/env python3
"""Normalize web-agent result files (JSONL with id/status/sources/evidence/queries) into the
evidence format used by build_column.py: adds "line" (= id), "dataset": "web-search-agent",
"how": "web". Records keep their status so build_column.py can skip non-sourced rows.

Also enforces the strict evidence policy that the batch prompts state: an aggregator page is
not evidence "even when it names a book". A `sourced` row whose URL evidence is *entirely*
aggregator domains is downgraded to `unverified` here rather than in the raw batch files, so
`sourcing/web_results/` stays a verbatim record of what each agent reported. Every downgrade is
listed in sourcing/audit/strict_downgrades.tsv.

Usage: python3 web_to_evidence.py out.jsonl in1.jsonl [in2.jsonl ...]"""
import json, re, sys, os

AGGREGATOR = re.compile(r"""(?ix) (?: brainyquote | azquotes | goodreads\.com | quotefancy
    | pinterest | quotepark | libquotes | quotes\.net | quotemaster | inspiringquotes
    | wisesayings | quoteslyfe | picturequotes | allauthor\.com | quotegarden | quotesgram
    | successories | quoteambition | everydaypower | keepinspiring | quotecatalog )""")
URL = re.compile(r"https?://")

seen = set()
downgrades = []
with open(sys.argv[1], "w", encoding="utf8") as fo:
    for p in sys.argv[2:]:
        batch = os.path.basename(p).replace(".jsonl", "")
        for l in open(p, encoding="utf8"):
            l = l.strip()
            if not l: continue
            try: r = json.loads(l)
            except json.JSONDecodeError: continue
            if not isinstance(r, dict) or "id" not in r or r["id"] in seen: continue
            ev = " ".join(r.get("evidence") or [])
            if (r.get("status") == "unsearched" or "NOT SEARCHED" in ev
                    or (r.get("status") == "unverified" and not r.get("queries"))):
                continue  # placeholder written when the search budget ran out: a later
                          # cleanup batch carries the real result for these ids
            if r.get("status") == "sourced":
                urls = [e for e in (r.get("evidence") or []) if URL.match(e)]
                if urls and all(AGGREGATOR.search(e) for e in urls):
                    downgrades.append((batch, r["id"], "; ".join(r.get("sources") or []), urls[0]))
                    r["status"] = "unverified"
                    r["reported_status"] = "sourced"
                    r["sources"] = []
                    r.setdefault("evidence", []).append(
                        "downgraded by strict policy: aggregator-only evidence")
            seen.add(r["id"])
            r["line"] = int(r["id"]); r["dataset"] = "web-search-agent"; r["how"] = "web"
            fo.write(json.dumps(r, ensure_ascii=False) + "\n")

with open("sourcing/audit/strict_downgrades.tsv", "w", encoding="utf8") as fd:
    fd.write("batch\tline\treported_source\tevidence_url\n")
    for row in sorted(downgrades):
        fd.write("\t".join(str(x) for x in row) + "\n")
print(len(seen), "web records", file=sys.stderr)
print(len(downgrades), "aggregator-only sources downgraded", file=sys.stderr)
