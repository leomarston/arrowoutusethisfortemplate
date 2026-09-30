#!/usr/bin/env python3
"""Flag workflow agents that are unfinished (no StructuredOutput call yet) and whose transcript has been idle for N minutes.
usage: stallcheck.py MINUTES wf_id [wf_id ...]   (pass only the workflows that are still running)"""
import json, os, sys, time, glob
# The session's workflow transcripts: $STALLCHECK_DIR if set, else the most recently written
# ~/.claude/projects/*/*/subagents/workflows folder (the live session's), never a hard-coded session id.
BASE = os.environ.get('STALLCHECK_DIR') or max(
    glob.glob(os.path.expanduser('~/.claude/projects/*/*/subagents/workflows')) or [''], key=lambda p: os.path.getmtime(p) if p else 0)
LIMIT = float(sys.argv[1]); now = time.time()
for wid in sys.argv[2:]:
    newest = {}
    for meta in glob.glob(f'{BASE}/{wid}/agent-*.meta.json'):
        d = json.load(open(meta)).get('description')
        t = meta[:-len('.meta.json')] + '.jsonl'
        if not os.path.exists(t): continue
        if d not in newest or os.path.getmtime(t) > os.path.getmtime(newest[d]): newest[d] = t   # a resumed agent supersedes its stopped copy
    for d, t in newest.items():
        finished = False                          # a real StructuredOutput tool_use in one of the last assistant messages (not the
        for line in open(t, 'rb').read().splitlines()[-40:]:   # marker text anywhere: a huge result pushed it out of a byte window)
            try:
                m = json.loads(line)
            except Exception:
                continue
            c = (m.get('message') or {}).get('content')
            if m.get('type') == 'assistant' and isinstance(c, list) and any(
                    b.get('type') == 'tool_use' and b.get('name') == 'StructuredOutput' for b in c if isinstance(b, dict)):
                finished = True
        age = (now - os.path.getmtime(t)) / 60
        state = 'done' if finished else ('STALL?' if age > LIMIT else 'active')
        print(f'{state:7s} {wid} {d}: idle {age:.0f} min')
