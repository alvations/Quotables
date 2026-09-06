"""Parse Project Gutenberg #16732 (Bartlett, Familiar Quotations, early edition) into JSONL
records {author, work, locator, quote, source}.  Format in the text:

    AUTHOR NAME.            (all-caps heading, ends with '.')
    <work heading>          (all caps, e.g. TEMPEST.)  -- Shakespeare only
    <source line>           (e.g. 'Act i. Sc. 2.'  or  '_Essay on Man. Epistle i._'  or 'Job xix. 25.')
    <blank>
    <quote lines...>
    <blank><blank>
"""
import json, re, sys
path = sys.argv[1]
lines = [l.rstrip('\r\n') for l in open(path, encoding='latin-1')]
# body between START and INDEX
start = next(i for i,l in enumerate(lines) if l.startswith('*** START'))
idx=[i for i,l in enumerate(lines) if i>start and l.strip().upper()=='INDEX' or l.strip().upper()=='INDEX.']
end = idx[-1] if idx else next(i for i,l in enumerate(lines) if l.startswith('*** END'))
body = lines[start:end]
caps = re.compile(r"^[A-Z][A-Z .,'&;:()\-\xc0-\xff]*\.?$")
author = None; work = None; src = None; last_work = None
records = []
i = 0
blocks = []
# split into paragraphs
para=[]; 
for l in body:
    if l.strip()=='' :
        if para: blocks.append(para); para=[]
    else: para.append(l)
if para: blocks.append(para)
def is_caps(p):
    return len(p)==1 and caps.match(p[0]) and len(p[0])>2 and not p[0].startswith('*')
date_re = re.compile(r"^(\d{4}|Born \d{4}|\d{4}-\d{4}|\d{4}\.|\d{4}-\d{4}\.)")
for bi, p in enumerate(blocks):
    text = ' '.join(x.strip() for x in p)
    if text.startswith('*       *'): continue
    if is_caps(p) or (len(p)==2 and caps.match(p[0].strip()) and date_re.match(p[1].strip())):
        t = p[0].strip().rstrip('.')
        nxt = blocks[bi+1] if bi+1 < len(blocks) else []
        has_date = (len(p)==2 and date_re.match(p[1].strip())) or (nxt and date_re.match(nxt[0].strip()))
        if has_date or author is None or t in ('SHAKESPEARE','OLD TESTAMENT','NEW TESTAMENT','COMMON PRAYER','BOOK OF COMMON PRAYER','MILTON','DRYDEN','POPE','SAMUEL BUTLER'):
            author = t; work = None; last_work = None
        else:
            work = t; last_work = None
        src = None
        continue
    if date_re.match(text) and len(text) < 30: continue
    if len(p)<=2 and len(text)<90 and (text.startswith('_') or re.search(r"\b(Act|Sc\.|Line|Book|Canto|Part|Chap|Epistle|Sat\.|Ode|[ivxlc]+\.|\d)", text)) and not text.endswith(',') and not text[0].islower() and (text.endswith('.') or text.endswith('_')):
        m = re.match(r"^_([^_]+)_\.?\s*(.*)$", text.strip())
        if m:
            last_work = m.group(1).strip().rstrip('.')
            rest = m.group(2).strip()
            src = (last_work + ', ' + rest) if rest else last_work
        elif work is None and last_work and re.match(r"^(St\.|Stanza|Line|Book|Canto|Part|Chap|Act|Sc\.|Epistle|Sat\.|Ode|[ivxlc]+\.|\d)", text):
            src = last_work + ', ' + text.strip('_ ')
        else:
            src = text.strip('_ ').replace('_','')
        continue
    if author is None or src is None: continue
    q = re.sub(r"\s+"," ", text).strip()
    records.append({'author':author.title(), 'work':work.title() if work else None, 'locator':src, 'quote':q})
    src = None
with open(sys.argv[2],'w') as fo:
    for r in records: fo.write(json.dumps(r, ensure_ascii=False)+'\n')
print(len(records), 'records;', len({r['author'] for r in records}), 'authors')
import collections
print(collections.Counter(r['author'] for r in records).most_common(15))
for r in records[1000:1004]: print(r)
