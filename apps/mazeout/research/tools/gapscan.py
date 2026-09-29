#!/usr/bin/env python3
"""gapscan.py SHOT LEVEL — list candidates for the gap clips on a start board (corner-aware bot read):
LONG = blocked arrows whose first blocker is >= 5 empty cells away (bump long-gap); FREE = free single arrows (combo);
PAR = pairs of free parallel straight arrows side by side (hit tolerance). Prints JSON on the last line."""
import sys, json
shot, lvl = sys.argv[1], int(sys.argv[2])
sys.argv = ['x']; sys.path.insert(0, '/Users/yago/Downloads/app-factory/apps/mazeout/research/bot')
import corners, bot, numpy as np
from PIL import Image
im = np.array(Image.open(shot).convert('RGB')).astype(np.int16)
b = bot.apply_overrides(im, bot.read_board(im), lvl)
occ = {tuple(c): a['id'] for a in b['arrows'] for c in a['cells']}
doors = set(map(tuple, b.get('door_cells', []))); taped = bot.taped_ids(b)
long_, free = [], []
for a in b['arrows']:
    if a['id'] in taped: continue
    r = bot.ray(b, a); gap = None
    for i, c in enumerate(r):
        if (c in occ and occ[c] != a['id']) or c in doors: gap = i; break
    cell, xy = bot.tap_point(b, a)
    if gap is None: free.append(dict(id=a['id'], dir=a['dir'], n=len(a['cells']), tap=[round(v, 1) for v in xy], cells=a['cells']))
    elif gap >= 5: long_.append(dict(id=a['id'], dir=a['dir'], gap=gap, n=len(a['cells']), tap=[round(v, 1) for v in xy]))
f = b['fit']; p = f['pitch']
def P(c): return [round((f['x0'] + c[0] * p) / bot.SCALE, 1), round((f['y0'] + c[1] * p) / bot.SCALE, 1)]
par = []
straight = [x for x in free if len({c[0] for c in x['cells']}) == 1 or len({c[1] for c in x['cells']}) == 1]
for i, x in enumerate(straight):
    for y in straight[i + 1:]:
        if x['dir'] != y['dir']: continue
        if x['dir'] in ('up', 'down'):
            if abs(x['cells'][0][0] - y['cells'][0][0]) == 1 and set(c[1] for c in x['cells']) & set(c[1] for c in y['cells']):
                rows = sorted(set(c[1] for c in x['cells']) & set(c[1] for c in y['cells']))
                r = rows[len(rows) // 2]; xa, xb = P((x['cells'][0][0], r)), P((y['cells'][0][0], r))
                par.append(dict(ids=[x['id'], y['id']], a=xa, b=xb, pitch_pt=round(p / bot.SCALE, 2)))
        else:
            if abs(x['cells'][0][1] - y['cells'][0][1]) == 1 and set(c[0] for c in x['cells']) & set(c[0] for c in y['cells']):
                cols = sorted(set(c[0] for c in x['cells']) & set(c[0] for c in y['cells']))
                cc = cols[len(cols) // 2]; xa, xb = P((cc, x['cells'][0][1])), P((cc, y['cells'][0][1]))
                par.append(dict(ids=[x['id'], y['id']], a=xa, b=xb, pitch_pt=round(p / bot.SCALE, 2)))
print('LONG', long_[:8]); print('FREE', [(x['id'], x['dir'], x['n'], x['tap']) for x in free]); print('PAR', par[:6])
print(json.dumps(dict(long=long_, free=[dict(id=x['id'], tap=x['tap'], n=x['n']) for x in free], par=par, pitch_pt=round(p / bot.SCALE, 2))))
