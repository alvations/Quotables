#!/usr/bin/env python3
"""Record a dispatched batch, a received/archived session, or a failed session in
sourcing/orchestrator_state.json. Run from the repository root.
  mark_dispatched.py dispatched batch_NNNN session_id
  mark_dispatched.py archived session_id
  mark_dispatched.py failed batch_NNNN session_id "reason"   (also removes it from dispatched)
  mark_dispatched.py status"""
import json, os, sys
p = 'sourcing/orchestrator_state.json'
st = json.load(open(p))
cmd = sys.argv[1]
if cmd == 'dispatched':
    st['dispatched'][sys.argv[2]] = sys.argv[3]
elif cmd == 'archived':
    if sys.argv[2] not in st['archived']: st['archived'].append(sys.argv[2])
elif cmd == 'failed':
    b, sid, why = sys.argv[2:5]
    st['failed'].append({'batch': b, 'session': sid, 'reason': why})
    if sid not in st['archived']: st['archived'].append(sid)
    st['dispatched'].pop(b, None)
json.dump(st, open(p, 'w'), indent=1)
inflight = sorted(b for b in st['dispatched'] if b not in st['received'])
done = set(st['dispatched']) | set(st['received'])
nxt = [f[:-4] for f in sorted(os.listdir('sourcing/batches')) if f[:-4] not in done]
print('received', len(st['received']), 'in flight', inflight, 'next', nxt[:3])
