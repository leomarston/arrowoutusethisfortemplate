#!/usr/bin/env python3
"""Throwaway spike extractor: L32 from research/shots/003-L32-start.png -> spike level JSON.
Grid measured: pitch 53.5 px, cell (0,0) centre (80.0, 807.5) px, 20x20. Pink tape (#FF6298) hides
arrow ink; under a tape the arrows are assumed to run straight through (4 parallel arrows per tape)."""
import json, sys, os
import numpy as np
from PIL import Image, ImageDraw
HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, '../../../research/shots/003-L32-start.png')
im = np.asarray(Image.open(SRC).convert('RGB')).astype(int)
P, X0, Y0, N = 53.5, 80.0, 807.5, 20
cov = 1 - im.mean(2) / 255.0
R, G, B = im[..., 0], im[..., 1], im[..., 2]
pink = (R > 180) & (G < 170) & (B > 90) & (R - G > 60)
def px(c, r): return X0 + c * P, Y0 + r * P
def dark_at(x, y, rad=2):
    x, y = int(round(x)), int(round(y))
    return cov[y-rad:y+rad+1, x-rad:x+rad+1].mean() > 0.6
def pink_at(x, y, rad=3):
    x, y = int(round(x)), int(round(y))
    return pink[y-rad:y+rad+1, x-rad:x+rad+1].mean() > 0.3
occ = {}; tape = set()
for r in range(N):
    for c in range(N):
        x, y = px(c, r)
        if pink_at(x, y): occ[(c, r)] = True; tape.add((c, r))
        elif dark_at(x, y): occ[(c, r)] = True
def edge(a, b):
    (x1, y1), (x2, y2) = px(*a), px(*b)
    mx, my = (x1 + x2) / 2, (y1 + y2) / 2
    if pink_at(mx, my): return None      # unknown: decide later
    return dark_at(mx, my)
adj = {k: set() for k in occ}
unknown = []
for (c, r) in occ:
    for dc, dr in ((1, 0), (0, 1)):
        nb = (c + dc, r + dr)
        if nb not in occ: continue
        e = edge((c, r), nb)
        if e is None: unknown.append(((c, r), nb))
        elif e: adj[(c, r)].add(nb); adj[nb].add((c, r))
# tape: resolve unknown edges -> connect along the axis the bundle's arrows run (outside the tape)
for a, b in unknown:
    dc, dr = b[0] - a[0], b[1] - a[1]
    # look at the continuation beyond the tape on the same axis
    def run_axis(cell):
        return any((cell[0] + s * dc, cell[1] + s * dr) in adj.get(cell, set()) for s in (1, -1))
    horiz = dc != 0
    # a bundle under a vertical tape has horizontal arrows and vice versa; decide by neighbours outside
    lo = (a[0] - dc, a[1] - dr); hi = (b[0] + dc, b[1] + dr)
    ok = (lo in adj.get(a, set())) or (hi in adj.get(b, set())) or \
         (a not in tape and run_axis(a)) or (b not in tape and run_axis(b))
    if ok: adj[a].add(b); adj[b].add(a)
# head detection: perpendicular ink width at the cell centre, and which side the apex points to
def perp_width(c, r, horiz):
    x, y = px(c, r)
    x, y = int(round(x)), int(round(y))
    if horiz: return cov[y-22:y+23, x].sum()
    return cov[y, x-22:x+23].sum()
arrows = []; seen = set()
ends = [k for k in occ if len(adj[k]) <= 1]
problems = []
for k in adj:
    if len(adj[k]) > 2: problems.append(('branch', k, sorted(adj[k])))
for start in sorted(ends):
    if start in seen: continue
    path = [start]; seen.add(start); prev = None; cur = start
    while True:
        nxt = [n for n in adj[cur] if n != prev and n not in seen]
        if not nxt: break
        prev, cur = cur, nxt[0]; path.append(cur); seen.add(cur)
    arrows.append(path)
def head_score(path, end_index):
    cell = path[end_index]
    other = path[end_index - 1] if end_index == len(path) - 1 else path[1]
    d = (cell[0] - other[0], cell[1] - other[1])
    x, y = px(*cell)
    horiz = d[1] == 0
    # ink ahead of the centre along d, at +14 px: head triangle (width ~) vs round cap (nothing)
    ax, ay = x + d[0] * 14, y + d[1] * 14
    if horiz: w = cov[int(ay)-22:int(ay)+23, int(round(ax))].sum()
    else: w = cov[int(round(ay)), int(ax)-22:int(ax)+23].sum()
    return w, d
out = []
for path in arrows:
    if len(path) == 1:
        problems.append(('single', path)); continue
    w_end, d_end = head_score(path, len(path) - 1)
    w_start, d_start = head_score(path, 0)
    if w_start > w_end:
        path = path[::-1]; d = d_start; w_hi, w_lo = w_start, w_end
    else:
        d = d_end; w_hi, w_lo = w_end, w_start
    if w_hi < 8 or w_lo > 6: problems.append(('headambig', path[0], path[-1], round(w_hi,1), round(w_lo,1)))
    dname = {(1,0):'right',(-1,0):'left',(0,1):'down',(0,-1):'up'}[d]
    out.append({'cells': [list(p) for p in path], 'dir': dname})
tapes = []
# tape bundles: connected tape cells
tl = sorted(tape); used = set()
for t in tl:
    if t in used: continue
    grp = [t]; used.add(t); i = 0
    while i < len(grp):
        c, r = grp[i]; i += 1
        for n in ((c+1,r),(c-1,r),(c,r+1),(c,r-1)):
            if n in tape and n not in used: used.add(n); grp.append(n)
    cs = [g[0] for g in grp]; rs = [g[1] for g in grp]
    tapes.append({'cells': [list(g) for g in sorted(grp)], 'orientation': 'vertical' if max(rs)-min(rs) > max(cs)-min(cs) else 'horizontal'})
level = {'id': 32, 'source': 'research/shots/003-L32-start.png (spike extraction, not overlay-proved)',
         'cols': N, 'rows': N, 'timeLimit': 180, 'hearts': 3, 'arrows': out, 'tapes': tapes}
dst = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, '../App/L032.json')
os.makedirs(os.path.dirname(dst), exist_ok=True)
json.dump(level, open(dst, 'w'), indent=None, separators=(',', ':'))
print('arrows', len(out), 'cells', sum(len(a['cells']) for a in out), 'occupied', len(occ), 'tapes', tapes)
for p in problems: print('PROBLEM', p)
# overlay: draw our reading on top of the shot
ov = Image.open(SRC).convert('RGB'); d = ImageDraw.Draw(ov)
for a in out:
    pts = [px(*c) for c in a['cells']]
    d.line(pts, fill=(0, 200, 0), width=4)
    hx, hy = pts[-1]; d.ellipse([hx-7, hy-7, hx+7, hy+7], fill=(255, 0, 0))
    tx, ty = pts[0]; d.ellipse([tx-5, ty-5, tx+5, ty+5], fill=(0, 120, 255))
ov.crop((0, 700, 1178, 1950)).save(os.path.join(HERE, '../../../design/spike-shots/l32-extract-overlay.png'))
