#!/usr/bin/env python3
"""Normalize web-agent result files (JSONL with id/status/sources/evidence/queries) into the
evidence format used by build_column.py: adds "line" (= id), "dataset": "web-search-agent",
"how": "web". Records keep their status so build_column.py can skip non-sourced rows.
Usage: python3 web_to_evidence.py out.jsonl in1.jsonl [in2.jsonl ...]"""
import json, sys
seen = set()
with open(sys.argv[1], "w", encoding="utf8") as fo:
    for p in sys.argv[2:]:
        for l in open(p, encoding="utf8"):
            l = l.strip()
            if not l: continue
            try: r = json.loads(l)
            except json.JSONDecodeError: continue
            if not isinstance(r, dict) or "id" not in r or r["id"] in seen: continue
            ev = " ".join(r.get("evidence") or [])
            if "NOT SEARCHED" in ev or (r.get("status") == "unverified" and not r.get("queries")):
                continue  # placeholder written when the search budget ran out: leave for a re-run
            seen.add(r["id"])
            r["line"] = int(r["id"]); r["dataset"] = "web-search-agent"; r["how"] = "web"
            fo.write(json.dumps(r, ensure_ascii=False) + "\n")
print(len(seen), "web records", file=sys.stderr)
