#!/usr/bin/env python3
"""Extract the JSONL from a downloaded results artifact (raw HTML with <pre id="jsonl">).
Usage: python3 ingest_artifact.py page.html out.jsonl"""
import html, json, re, sys
raw = open(sys.argv[1], encoding="utf8", errors="replace").read()
m = re.search(r'<pre id="jsonl">(.*?)</pre>', raw, re.S)
body = html.unescape(m.group(1)) if m else raw
n = 0
with open(sys.argv[2], "w", encoding="utf8") as fo:
    for line in body.splitlines():
        line = line.strip()
        if not line.startswith("{"): continue
        try: r = json.loads(line)
        except json.JSONDecodeError: continue
        if "id" in r and "status" in r:
            fo.write(json.dumps(r, ensure_ascii=False) + "\n"); n += 1
print(n, "rows", file=sys.stderr)
