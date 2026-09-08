#!/usr/bin/env python3
"""Append one agent-session record to the audit ledger sourcing/audit/sessions.jsonl.
Usage: record_session.py <session> <batch> <outcome> <detail> <cost_usd> <input_tokens> <output_tokens> <artifact_url|-> [created]"""
import json, sys, datetime
s, b, outcome, detail, cost, tin, tout, art = sys.argv[1:9]
created = sys.argv[9] if len(sys.argv) > 9 else datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%MZ")
rec = {"session": s, "batch": b, "model": "claude-fable-5-1", "created": created, "outcome": outcome,
       "detail": detail, "cost_usd": float(cost), "input_tokens": int(tin), "output_tokens": int(tout),
       "artifact": None if art == "-" else art}
with open("sourcing/audit/sessions.jsonl", "a") as f:
    f.write(json.dumps(rec) + "\n")
print("recorded", s, b)
