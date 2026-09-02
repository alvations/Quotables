#!/usr/bin/env python3
"""Locate corpus quotes verbatim inside a public-domain full text (Project Gutenberg
plain text) and emit evidence records naming the work and the nearest section heading.

Usage:
  python3 locate_fulltext.py author-quote.txt evidence_out.jsonl "<Author regex>" \
      "<Work title>" <year-or-0> <pg_id> <text_file> [--shakespeare]

Method: every line of the text is normalized (lower-case, ASCII, punctuation stripped) and
joined into one string. For each corpus quote by the author, 3-token shingles of the
normalized quote are looked up in that string; the positions with most shingle hits become
candidates, and rapidfuzz partial_ratio_alignment scores the quote against a window there.
A hit is accepted when the alignment score is >= 92 (>= 97 for quotes under 30 characters,
which must effectively be exact). The section heading is the nearest preceding line that
looks like a heading (ACT/SCENE, CHAPTER/BOOK/PART/ESSAY/LETTER n, an all-capitals title,
or a sonnet number). With --shakespeare the work title is taken from the table of contents
of Gutenberg #100 and the locator is "Act X, Scene Y" (or "Sonnet N").
"""
import bisect, json, re, sys
from collections import Counter
from rapidfuzz import fuzz
from norm import norm, norm_author

ROMAN = {"i":1,"ii":2,"iii":3,"iv":4,"v":5,"vi":6,"vii":7,"viii":8,"ix":9,"x":10}
HEAD_RE = re.compile(r"^\s*(CHAPTER|BOOK|PART|ESSAY|LETTER|SECTION|CANTO|ACT|SCENE|VOLUME|APHORISM|Chapter|Book|Part|Essay|Letter|Section|Canto|Act|Scene|Aphorism)\b")
ACTSCENE_RE = re.compile(r"ACT\s+([IVXLC]+|\d+)\.?\s*SCENE\s+([IVXLC]+|\d+)", re.I)
ACT_RE = re.compile(r"^\s*ACT\s+([IVXLC]+|\d+)\b", re.I)
SCENE_RE = re.compile(r"^\s*SCENE\s+([IVXLC]+|\d+)\b", re.I)

def roman_to_int(s):
    s = s.lower()
    if s.isdigit(): return int(s)
    vals = {'i':1,'v':5,'x':10,'l':50,'c':100}
    total = 0
    for i, ch in enumerate(s):
        v = vals.get(ch, 0)
        if i + 1 < len(s) and v < vals.get(s[i+1], 0): total -= v
        else: total += v
    return total

def is_caps_heading(line):
    s = line.strip()
    if not (3 <= len(s) <= 60) or s.endswith((",", ";", ":", "-")):
        return False
    if HEAD_RE.match(s):
        return True
    letters = re.sub(r"[^A-Za-z]", "", s)
    return bool(letters) and letters.upper() == letters and len(letters) >= 3 and len(letters) >= 0.5 * len(s)

def load_text(path, shakespeare):
    raw = open(path, encoding="utf8", errors="replace").read().split("\n")
    # trim Gutenberg header/footer
    start = next((i for i, l in enumerate(raw) if l.startswith("*** START")), 0)
    end = next((i for i, l in enumerate(raw) if l.startswith("*** END")), len(raw))
    lines = raw[start+1:end]
    works = []  # (line_idx, title)
    if shakespeare:
        ci = next(i for i, l in enumerate(lines) if l.strip() == "Contents")
        titles = []
        for l in lines[ci+1:ci+200]:
            s = l.strip()
            if titles and s == titles[0]:
                break  # the body of the first work begins here
            if s and s.upper() == s and len(s) > 3:
                titles.append(s)
        titles = list(dict.fromkeys(titles))
        body_start = ci + 1 + len(titles) + 2
        seen = set()
        for i in range(body_start, len(lines)):
            s = lines[i].strip().rstrip(':')
            if s in titles and s not in seen and len(lines[i]) - len(lines[i].lstrip()) <= 1:
                works.append((i, s)); seen.add(s)
        missing = [t for t in titles if t not in seen]
        if missing:
            print("work titles not found in body:", missing, file=sys.stderr)
    return lines, works

def build_index(lines):
    normed = [norm(l) for l in lines]
    offsets = []; pos = 0; parts = []
    for n in normed:
        offsets.append(pos); parts.append(n + " "); pos += len(n) + 1
    return "".join(parts), offsets

def heading_for(lines, works, li, shakespeare):
    work = None
    if works:
        k = bisect.bisect_right([w[0] for w in works], li) - 1
        work = works[k][1] if k >= 0 else None
    if shakespeare:
        if work and "SONNET" in work:
            for j in range(li, max(-1, li-40), -1):
                s = lines[j].strip()
                if s.isdigit(): return work, f"Sonnet {int(s)}"
            return work, None
        act = scene = None
        wstart = works[bisect.bisect_right([w[0] for w in works], li) - 1][0] if works else 0
        for j in range(li, wstart - 1, -1):
            s = lines[j]
            m = ACTSCENE_RE.search(s)
            if m:
                act = roman_to_int(m.group(1))
                if scene is None: scene = roman_to_int(m.group(2))
                break
            m = SCENE_RE.match(s)
            if m and scene is None: scene = roman_to_int(m.group(1)); continue
            m = ACT_RE.match(s)
            if m: act = roman_to_int(m.group(1)); break
        if act and scene: return work, f"Act {act}, Scene {scene}"
        if act: return work, f"Act {act}"
        return work, None
    for j in range(li, max(-1, li-4000), -1):
        s = lines[j]
        if is_caps_heading(s) and not s.strip().isdigit():
            h = re.sub(r"\s+", " ", s.strip()).rstrip(".")
            if h.startswith(("'", '"', "\u2018", "\u201c")) or len(re.sub(r"[^A-Za-z]", "", h)) < 3:
                continue  # signature lines and stray marks are not section headings
            return work, h[:70]
    return work, None

def title_case(t):
    words = t.replace("\u2019", "'").split()
    small = {"of", "and", "the", "a", "in", "to", "or", "for"}
    out = []
    for i, w in enumerate(words):
        lw = w.lower()
        out.append(lw if (lw in small and i > 0) else lw[:1].upper() + lw[1:])
    return " ".join(out).replace("'S", "'s")

def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    shakespeare = "--shakespeare" in sys.argv
    corpus, out_path, author_re, work_title, year, pg_id, text_file = args[:7]
    year = int(year)
    lines, works = load_text(text_file, shakespeare)
    big, offsets = build_index(lines)
    are = re.compile(author_re, re.I)
    out = open(out_path, "a", encoding="utf8")
    n_hit = n_try = 0
    for li_c, line in enumerate(open(corpus, encoding="utf8"), 1):
        author, quote = line.rstrip("\n").split("\t")[:2]
        if not are.search(author): continue
        nq = norm(quote)
        toks = nq.split()
        if len(toks) < 2: continue
        n_try += 1
        # candidate positions via 3-token shingles (2-token for very short quotes)
        k = 3 if len(toks) >= 3 else 2
        votes = Counter()
        for i in range(len(toks) - k + 1):
            sh = " " + " ".join(toks[i:i+k]) + " "
            p = big.find(sh); c = 0
            while p != -1 and c < 300:
                votes[(p - i * 6) // 300] += 1; c += 1
                p = big.find(sh, p + 1)
        if not votes: continue
        best = None
        for bucket, _ in votes.most_common(6):
            s = max(0, bucket * 300 - len(nq)); e = min(len(big), bucket * 300 + 300 + 2 * len(nq))
            al = fuzz.partial_ratio_alignment(nq, big[s:e])
            if al is None: continue
            if best is None or al.score > best[0]:
                best = (al.score, s + al.dest_start, s + al.dest_end)
        if not best: continue
        score, ds, de = best
        thr = 97 if len(nq) < 30 else 92
        if score < thr: continue
        li = bisect.bisect_right(offsets, ds) - 1
        work, loc = heading_for(lines, works, li, shakespeare)
        wt = title_case(work) if (shakespeare and work) else work_title
        src = wt + (f" ({year})" if year else "")
        if loc: src += ", " + loc
        excerpt = re.sub(r"\s+", " ", " ".join(lines[max(0, li-1):li+2]).strip())[:300]
        out.write(json.dumps({"line": li_c, "author": author, "source": src,
                              "dataset": f"gutenberg-fulltext:pg{pg_id}", "ref_quote": excerpt,
                              "score": int(score), "how": "fulltext"}, ensure_ascii=False) + "\n")
        n_hit += 1
    out.close()
    print(f"{work_title}: {n_hit} located of {n_try} quotes tried", file=sys.stderr)

if __name__ == "__main__":
    main()
