#!/usr/bin/env python3
"""vbatch — extract + verify + replay a list of levels, one process, sequential (memory-safe).
  python3 vbatch.py V1:5 V2:21 V2:32 ...   |   python3 vbatch.py all
Prints one line per level and writes video-frames/work/extract/batch-summary.json."""
import json, os, sys, traceback
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vextract as vx

args = sys.argv[1:]
if args == ['all']:
    args = []
    for V in ('V1', 'V2'):
        args += ['%s:%d' % (V, L['level']) for L in vx.load_index(V)]
out = []
for a in args:
    V, n = a.split(':'); n = int(n)
    try:
        js, base = vx.extract_level(V, n)
        rp = vx.replay(V, n)
        st = rp['stats']
        row = dict(video=V, level=n, arrows=len(js['arrows']), hidden=st.get('hidden_layer_arrows', 0), grid=[js['cols'], js['rows']],
                   pitch_pt=js['pitch_pt'], iou=js['verify']['ink_iou'], iou_tol1=js['verify']['ink_iou_tol1px'],
                   anomalies=len(js['anomalies']), obstacles=sorted({o['kind'] for o in js['obstacles']}),
                   taps=st['taps'], consistent=st['consistent'], inconsistent=st['inconsistent'],
                   unexplained_stays=st['unexplained_stays'], miss=st['miss'], left_at_end=len(st['left_at_end']),
                   bumps=st['bump_blocked'] + st['bump_free'])
    except Exception as e:
        row = dict(video=V, level=n, error=repr(e)[:200])
        traceback.print_exc()
    out.append(row)
    print(json.dumps(row), flush=True)
sp = os.path.join(vx.WORK, 'extract', 'batch-summary.json')
prev = json.load(open(sp)) if os.path.exists(sp) else []
keep = {(r['video'], r['level']): r for r in prev}
for r in out:
    keep[(r['video'], r['level'])] = r
json.dump(sorted(keep.values(), key=lambda r: (r['video'], r['level'])), open(sp, 'w'), indent=1)
