#!/usr/bin/env python3
"""corners.py — session-2 add-on for the v552 CORNER obstacle (unlock L70: "Arrows turn when they hit the CORNER!"), without editing bot.py.
A corner = a blue-grey spring blob ('unknown' to bot.py) + a red diagonal plate. The plate's side = the facing diagonal s=(sx,sy).
Rule measured on L70/L71 (clips S2-L070-corner-first-use, S2-L071-corner-right-moving-turns-up): an arrow moving along d that enters the corner
cell from the plate side (d·s < 0) leaves it along d' = d - (d·s)s (left→up for s=(+1,-1)... etc.). From the back side it is blocked.
  python3 corners.py play2 --level N [--seconds S]   # bot.play2 with corner-aware rays (unknown corner blobs are not a stop reason)
  python3 corners.py read SHOT --level N              # print corners + plan
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import bot

_read = bot.read_board
def read_board(im, fit=None):
    b = _read(im, fit=fit) if fit is not None else _read(im)
    f = b['fit']; p = f['pitch']
    corners = {}
    keep = []
    for o in b['obstacles']:
        mr = o['mean_rgb']
        x0, y0, x1, y1 = o['bbox_px']
        spring = (o['kind'] == 'unknown' and 85 <= mr[0] <= 115 and 100 <= mr[1] <= 125 and 140 <= mr[2] <= 170
                  and (x1 - x0) < 1.3 * p and (y1 - y0) < 1.3 * p)
        if not spring:
            keep.append(o); continue
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        X0, Y0 = int(max(0, cx - 1.2 * p)), int(max(0, cy - 1.2 * p))
        win = im[Y0:int(cy + 1.2 * p), X0:int(cx + 1.2 * p)].astype(int)
        red = (win[..., 0] > 190) & (win[..., 1] < 100) & (win[..., 2] < 110)
        if red.sum() < 30:
            keep.append(o); continue
        ys, xs = np.nonzero(red); rx, ry = xs.mean() + X0, ys.mean() + Y0
        s = (1 if rx > cx else -1, 1 if ry > cy else -1)
        mx, my = (cx + rx) / 2, (cy + ry) / 2
        cell = (int(round((mx - f['x0']) / p)), int(round((my - f['y0']) / p)))
        corners[cell] = s
        o = dict(o, kind='corner', cells=[list(cell)], facing=s)
        keep.append(o)
    b['obstacles'] = keep
    b['corners'] = corners
    if corners:
        # pseudo-arrows traced on the plate, and the anomalies they raise
        b['arrows'] = [a for a in b['arrows'] if not all(tuple(c) in corners for c in a['cells'])]
        b['anomalies'] = [an for an in b['anomalies'] if not any(('[%d, %d]' % c) in an for c in corners)]
        b['door_cells'] = sorted(set(map(tuple, b.get('door_cells', []))) | set(corners))
        for i, a in enumerate(b['arrows']):
            a['id'] = i
    return b

_ray = bot.ray
def ray(board, a, info=None):
    corners = board.get('corners') or {}
    if not corners:
        return _ray(board, a, info)
    c_lo, r_lo, c_hi, r_hi = board['bounds']
    d = bot.DIRS[a['dir']]
    c, r = a['cells'][-1]
    out = []; turns = 0
    pipes = board.get('pipes', []); hops = 0
    while True:
        c, r = c + d[0], r + d[1]
        if c < c_lo - 1 or c > c_hi + 1 or r < r_lo - 1 or r > r_hi + 1:
            break
        if (c, r) in corners and turns < 6:
            s = corners[(c, r)]
            dot = d[0] * s[0] + d[1] * s[1]
            if dot < 0:
                d = (d[0] - dot * s[0], d[1] - dot * s[1]); turns += 1
                continue
            out.append((c, r)); continue           # back side: blocks (the corner cell is in door_cells)
        hit = None
        for k, pp in enumerate(pipes):
            if (c, r) in pp['cells']:
                hit = (k, pp); break
        if hit and hops < 4:
            k, pp = hit
            o = pp['ends'].get((c, r))
            if o is not None and (o[0] == -d[0] and o[1] == -d[1]) and len(pp['ends']) == 2:
                other = [e for e in pp['ends'] if e != (c, r)][0]
                d = pp['ends'][other]; c, r = other; hops += 1
                continue
        out.append((c, r))
    return out

bot.read_board = read_board
bot.ray = ray

if __name__ == '__main__':
    args = sys.argv[1:]
    if args[0] == 'read':
        from PIL import Image
        lvl = int(args[args.index('--level') + 1]) if '--level' in args else 0
        im = np.array(Image.open(args[1]).convert('RGB')).astype(np.int16)
        b = bot.apply_overrides(im, read_board(im), lvl)
        print('corners', b['corners'], 'arrows', len(b['arrows']), 'anomalies', b['anomalies'])
        print('unknown', [(o['bbox_px'], o['mean_rgb']) for o in b['obstacles'] if o['kind'] == 'unknown'])
        for u, c, xy in bot.plan(b):
            print(u['ids'], u['rep']['dir'], c, [round(v, 1) for v in xy], 'ray', ray(b, u['rep'])[:6])
    elif args[0] == 'play2':
        lvl = int(args[args.index('--level') + 1]); secs = float(args[args.index('--seconds') + 1]) if '--seconds' in args else 170
        print('result', bot.play2(lvl, secs))
