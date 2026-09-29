"""v552 intro draw-in (S1-L48-play-intro): each arrow's polyline mapped through the fitted zoom (easeOutCubic
s: 1.493 -> 1 over 1.350 s from the cut t=0.375, about the board centre); per frame the inked prefix from the tail
(fraction of the length) and whether the head triangle is present. -> out/introdraw2_L48.txt"""
import os, sys, json
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mf
SC = 3; TC, S0, D, N = 0.375, 1.4931, 1.3501, 3.0049
d = json.load(open(os.path.join(mf.SP, '..', 'levels', 'L048.json'))); p = d['pitch_pt']; ox, oy = d['origin_pt']
cx0 = ox + (d['cols'] - 1) * p / 2; cy0 = oy + (d['rows'] - 1) * p / 2
t, px = mf.raw('S1-L48-play-intro.mov', 0.36, 1.6, width=393 * SC, crop=[0, 0, 393, 852], tag='idraw2')
def sc(tt):
    u = np.clip((tt - TC) / D, 0, 1); return 1 + (S0 - 1) * (1 - u) ** N
# fine offset: fit a global (dx, dy) on the last frame (s ~ 1)
kF = len(t) - 1
allS = []
for a in d['arrows']:
    pts = [np.array((ox + c * p, oy + r * p)) for c, r in a['cells']]
    for u0, u1 in zip(pts[:-1], pts[1:]):
        for k in np.arange(0, 1, 0.25): allS.append(u0 + (u1 - u0) * k)
allS = np.array(allS)
best = (-1, 0, 0)
for dx in np.arange(-4, 4.01, 0.5):
    for dy in np.arange(-4, 4.01, 0.5):
        X = allS[:, 0] + dx; Y = allS[:, 1] + dy
        v = px[kF][np.clip((Y * SC).astype(int), 0, px.shape[1] - 1), np.clip((X * SC).astype(int), 0, px.shape[2] - 1)].astype(int).mean(-1)
        q = (v < 100).mean()
        if q > best[0]: best = (q, dx, dy)
_, DX, DY = best
lines = [f'board offset vs JSON ({DX:+.1f},{DY:+.1f}) pt, coverage {best[0]:.3f} on the settled frame']
lines.append('arrow cells | per-frame inked prefix fraction at t = ' + ' '.join(f'{x:.2f}' for x in t[::3]))
summary = []
for a in d['arrows']:
    pts = [np.array((ox + c * p + DX, oy + r * p + DY)) for c, r in a['cells']]
    S = []
    for u0, u1 in zip(pts[:-1], pts[1:]):
        for k in np.arange(0, 1, 0.05): S.append(u0 + (u1 - u0) * k)
    S.append(pts[-1]); S = np.array(S)
    fr = []
    for k in range(len(t)):
        s = sc(t[k]); X = cx0 + s * (S[:, 0] - cx0); Y = cy0 + s * (S[:, 1] - cy0)
        ok = (X > 1) & (X < 392) & (Y > 1) & (Y < 851)
        if not ok.all(): fr.append(np.nan); continue
        v = px[k][(Y * SC).astype(int), (X * SC).astype(int)].astype(int).mean(-1)
        ink = v < 110
        pre = len(ink) if ink.all() else int(np.argmin(ink))
        fr.append(pre / len(ink))
    fr = np.array(fr)
    lines.append(f'{a["id"]:3d} {len(a["cells"]):3d} | ' + ' '.join('  .  ' if np.isnan(x) else f'{x:5.2f}' for x in fr[::3]))
    def when(th):
        w = np.where(fr >= th)[0]; return t[w[0]] if len(w) else np.nan
    vis = ~np.isnan(fr)
    summary.append((len(a['cells']), when(0.25), when(0.5), when(0.75), when(0.98), t[vis][0] if vis.any() else np.nan))
summary = np.array(summary)
lines.append('== summary: time to 25 / 50 / 75 / 98 % drawn (median over arrows fully on screen from the first level frame)')
full = summary[:, 5] < 0.39
for lo, hi in ((2, 4), (5, 7), (8, 12), (13, 45)):
    m = full & (summary[:, 0] >= lo) & (summary[:, 0] <= hi)
    if m.sum(): lines.append(f'   {lo}-{hi} cells (n={m.sum()}): ' + '  '.join(f'{q}%: {np.nanmedian(summary[m, i]):.3f}' for q, i in ((25, 1), (50, 2), (75, 3), (98, 4))))
m = full & ~np.isnan(summary[:, 4])
if m.sum() > 3:
    c = np.polyfit(summary[m, 0], summary[m, 4], 1); lines.append(f'   98% time vs cells: {c[1]:.3f} + {c[0]*1000:.2f} ms/cell (n={m.sum()})')
    c = np.polyfit(summary[m, 0], summary[m, 2], 1); lines.append(f'   50% time vs cells: {c[1]:.3f} + {c[0]*1000:.2f} ms/cell')
open(os.path.join(mf.SP, 'out', 'introdraw2_L48.txt'), 'w').write('\n'.join(lines) + '\n')
print('\n'.join(lines[:2])); print('\n'.join(lines[-8:]))
