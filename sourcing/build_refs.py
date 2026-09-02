#!/usr/bin/env python3
"""Convert the gathered citation datasets into one refs.jsonl for match_offline.py.

Each dataset supplies (author, quote, source) where `source` names the first-hand work.
"""
import json, re, sys

def foba(path):
    """@foba/quotes-* npm packages: Wikiquote 'Sourced' entries. mark = citation text."""
    for l in open(path, encoding="utf8"):
        r = json.loads(l)
        mark = r["mark"].strip()
        if not mark or "citation needed" in mark.lower() or mark.lower().startswith(("attributed", "disputed", "misattributed")):
            continue
        yield {"author": r["figure"], "quote": r["quote"], "source": mark, "dataset": "wikiquote-via-@foba/quotes-" + r["src"]}

ROMAN = {"i":1,"ii":2,"iii":3,"iv":4,"v":5,"vi":6,"vii":7,"viii":8,"ix":9,"x":10,"xi":11,"xii":12}
def bartlett(path, label):
    """Bartlett's Familiar Quotations (Project Gutenberg text, parsed): author/work/locator."""
    for l in open(path, encoding="utf8"):
        r = json.loads(l)
        a = r["author"]
        if a in ("Old Testament", "New Testament", "Common Prayer", "Book Of Common Prayer"):
            continue
        work, loc = r.get("work"), r.get("locator") or ""
        loc = re.sub(r"\s+", " ", loc).strip().rstrip(".")
        if work:
            src = f"{work}, {loc}" if loc else work
        else:
            src = loc
        if not src or len(src) < 3:
            continue
        yield {"author": a, "quote": r["quote"], "source": src, "dataset": label}

if __name__ == "__main__":
    out = open(sys.argv[1], "w", encoding="utf8")
    n = 0
    for spec in sys.argv[2:]:
        kind, path = spec.split("=", 1)
        gen = {"foba": lambda p: foba(p), "bartlett16732": lambda p: bartlett(p, "bartlett-familiar-quotations-pg16732"),
               "bartlett27889": lambda p: bartlett(p, "bartlett-familiar-quotations-9th-ed-pg27889")}[kind](path)
        for rec in gen:
            out.write(json.dumps(rec, ensure_ascii=False) + "\n"); n += 1
    print(n, "reference records", file=sys.stderr)
