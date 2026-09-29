#!/usr/bin/env python3
"""probe.py SHOT.png — list FREE arrows with tap candidates for input-model probes:
id, dir, n cells, head/tail/middle points (pt), and for each body cell of a straight run the perpendicular clearance
(how many empty cells on each side before other ink)."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bot
import numpy as np
from PIL import Image
im = np.array(Image.open(sys.argv[1]).convert('RGB')).astype(np.int16)
b = bot.read_board(im)
f = b['fit']; p = f['pitch']; S = bot.SCALE
occ = {}
for a in b['arrows']:
    for c in a['cells']:
        occ[tuple(c)] = a['id']
for c in b.get('door_cells', []):
    occ[tuple(c)] = 'door'
def P(c):
    return round((f['x0'] + c[0] * p) / S, 1), round((f['y0'] + c[1] * p) / S, 1)
print('pitch_pt %.2f arrows %d anomalies %s' % (p / S, len(b['arrows']), b['anomalies']))
frees = bot.free_arrows(b)
blocked = [a for a in b['arrows'] if a not in frees]
def desc(a, tag):
    cs = [tuple(c) for c in a['cells']]
    d = bot.DIRS[a['dir']]
    tip = (cs[-1][0] + 0.37 * d[0], cs[-1][1] + 0.37 * d[1])
    out = []
    for i in range(1, len(cs) - 1):
        u = (cs[i][0] - cs[i - 1][0], cs[i][1] - cs[i - 1][1]); v = (cs[i + 1][0] - cs[i][0], cs[i + 1][1] - cs[i][1])
        if u != v:
            continue
        perp = (u[1], u[0])
        cl = []
        for s in (1, -1):
            k = 0
            while k < 4 and (cs[i][0] + s * (k + 1) * perp[0], cs[i][1] + s * (k + 1) * perp[1]) not in occ:
                k += 1
            cl.append(k)
        out.append((cs[i], P(cs[i]), 'perp', perp, 'clear+-', cl))
    ray = bot.ray(b, a)
    blk = [occ[c] for c in ray if c in occ]
    print(tag, a['id'], a['dir'], 'n', len(cs), 'tail', P(cs[0]), 'head', P(cs[-1]), 'tip', P(tip), 'blockers', blk[:3])
    for o in out:
        if max(o[-1]) >= 1:
            print('    straight', o)
for a in frees:
    desc(a, 'FREE')
if '--blocked' in sys.argv:
    for a in blocked:
        desc(a, 'BLOCKED')
