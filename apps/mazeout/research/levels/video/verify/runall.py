#!/usr/bin/env python3
"""Third reader over every video start frame (and every elevator reveal frame) of levels 1-38.

usage: runall.py [LEVEL ...]    (default: all)   -> verify/thirdreader.json + a printed table
Compares verify/myread2.py (independent) with the batch files:
  V1 L1-10 -> levels/L0NN.json; V1 L11-20 -> levels/video/V1-L0NN.json; V2 L11-20 -> levels/video/V2-L0NN.json and levels/L0NN.json;
  V2 L21-31 -> levels/L0NN.json; V2 L32-38 -> levels/video/V2-L0NN.json.
"""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import myread2
import lvldiff

R = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))  # research/
FR = os.path.join(R, 'video-frames')
OUT = os.path.join(R, 'levels', 'video', 'verify')
OV = os.path.join(FR, 'work', 'verify', 'third')
os.makedirs(OV, exist_ok=True)
os.makedirs(os.path.join(OUT, 'third'), exist_ok=True)


def targets():
    t = []
    for n in range(1, 21):
        ref = f'levels/L{n:03d}.json' if n <= 10 else f'levels/video/V1-L{n:03d}.json'
        t.append(('V1', n, ref))
    for n in range(11, 39):
        if n <= 20:
            ref = f'levels/video/V2-L{n:03d}.json'
        elif n <= 31:
            ref = f'levels/L{n:03d}.json'
        else:
            ref = f'levels/video/V2-L{n:03d}.json'
        t.append(('V2', n, ref))
    return t


def pipes_of(d):
    return [dict(kind='pipe', cells=p['cells'], ends=p.get('ends'), counter=p.get('counter')) for p in d.get('pipes', [])]


def obst_lists(da, db):
    obA = [o for o in da.get('obstacles', []) if o['kind'] != 'elevator']
    obB = [o for o in db.get('obstacles', []) if o['kind'] != 'elevator']
    if db.get('pipes'):
        obB = [o for o in obB if o['kind'] != 'pipe'] + pipes_of(db)
    return obA, obB


def main(sel):
    res = {}
    rows = []
    for v, n, ref in targets():
        if sel and n not in sel:
            continue
        frame = os.path.join(FR, v, f'L{n:03d}-start.png')
        if not os.path.exists(frame):
            rows.append((v, n, 'NO FRAME'))
            continue
        mine = myread2.read(frame, 'auto', overlay=os.path.join(OV, f'{v}-L{n:03d}.png'))
        for o in mine['obstacles']:
            if o['kind'] in ('box', 'pipe'):
                x0, y0, x1, y1 = o['bbox_px']
                if o['kind'] == 'box':
                    dx, dy = (x1 - x0) * 0.2, (y1 - y0) * 0.2
                    bb = [int(x0 + dx), int(y0 + dy), int(x1 - dx), int(y1 - dy)]
                else:
                    bb = [x0, y0, x1, y1]
                o['counter_ocr'], _ = myread2.ocr_counter(frame, bb)
        json.dump(mine, open(os.path.join(OUT, 'third', f'{v}-L{n:03d}.json'), 'w'), indent=1)
        db = json.load(open(os.path.join(R, ref)))
        B = [a for a in db['arrows'] if a.get('layer', 1) == 1]
        obA, obB = obst_lists(mine, db)
        c = lvldiff.compare(mine['arrows'], B, obA, obB, False, mine['cols'], mine['rows'])
        c['elevators'] = lvldiff.compare_elevators(mine, db, c['shift'])
        c['ref'] = ref
        c['dims'] = [[mine['cols'], mine['rows']], [db['cols'], db['rows']]]
        c['anomalies'] = mine['anomalies']
        c['fit'] = mine['fit']
        # hidden layers: read each reveal frame, check every hidden arrow of that elevator is there
        hid = []
        for k, e in enumerate(db.get('elevators', []) or []):
            rf = os.path.join(FR, v, f'L{n:03d}-elevator{k}-reveal.png')
            if not os.path.exists(rf):
                hid.append({'elevator': k, 'error': 'no reveal frame'})
                continue
            mr = myread2.read(rf, 'auto', overlay=os.path.join(OV, f'{v}-L{n:03d}-elev{k}.png'))
            json.dump(mr, open(os.path.join(OUT, 'third', f'{v}-L{n:03d}-elev{k}.json'), 'w'), indent=1)
            allB = db['arrows']
            cc = lvldiff.compare(mr['arrows'], allB, (), (), False, mr['cols'], mr['rows'])
            ids_same = set()
            s = cc['shift']
            mine_keys = {tuple((q[0] + s[0], q[1] + s[1]) for q in a['cells']) for a in mr['arrows']}
            for a in allB:
                if tuple(tuple(q) for q in a['cells']) in mine_keys:
                    ids_same.add(a['id'])
            hids = e.get('hidden_arrow_ids', [])
            found = [i for i in hids if i in ids_same]
            # arrows in my reveal read that match no arrow of the level at all
            B_keys = {tuple(tuple(q) for q in a['cells']) for a in allB}
            extra = [a for a in mr['arrows'] if tuple((q[0] + s[0], q[1] + s[1]) for q in a['cells']) not in B_keys]
            hid.append({'elevator': k, 'hidden': len(hids), 'hidden_found': len(found),
                        'hidden_missing': [i for i in hids if i not in ids_same], 'extra_in_frame': len(extra),
                        'extra': [{'cells': a['cells'], 'dir': a['dir']} for a in extra][:12]})
        c['hidden_layers'] = hid
        res[f'{v}-L{n:03d}'] = c
        ob = c['obstacles']
        rows.append((v, n, f"{c['identical']}/{c['nB']} (mine {c['nA']})", f"dims {c['dims'][0]} vs {c['dims'][1]}",
                     f"obst {ob['same_cells']}/{ob['B']} (mine {ob['A']}) cnt {ob['same_counter']}",
                     f"elev {[m['jaccard'] for m in c['elevators']['match']]}",
                     f"hid {[(h.get('hidden_found'), h.get('hidden'), h.get('extra_in_frame')) for h in hid]}",
                     f"anom {len(mine['anomalies'])}"))
        print(*rows[-1], flush=True)
    name = 'thirdreader.json' if not sel else f'thirdreader-{"-".join(map(str, sel))}.json'
    json.dump(res, open(os.path.join(OUT, name), 'w'), indent=1)


if __name__ == '__main__':
    main([int(x) for x in sys.argv[1:]])
