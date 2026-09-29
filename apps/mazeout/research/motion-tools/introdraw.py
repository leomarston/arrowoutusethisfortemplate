"""v552 level intro, part 2 (S1-L48-play-intro): (a) board scale s(t) from the top edge of the pipe tubes (cyan) in a
column band, zoom about the board centre (fit s(t) = 1 + (s0-1)(1-u)^n, u = (t-ts)/D, ts = the hard-cut frame);
(b) per-arrow draw-in: fraction of each arrow's polyline that is inked, mapped through the fitted zoom.
-> out/introdraw_L48.txt"""
import os, sys, json
import numpy as np
from scipy.optimize import least_squares
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mf
out = []
def P(s):
    print(s); out.append(s)
clip = 'S1-L48-play-intro.mov'; SC = 3
d = json.load(open(os.path.join(mf.SP, '..', 'levels', 'L048.json'))); p = d['pitch_pt']; ox, oy = d['origin_pt']
t, px = mf.raw(clip, 0.36, 2.2, width=393 * SC, crop=[0, 0, 393, 852], tag='idraw')
def cyan(f):
    R, G, B = f[..., 0].astype(int), f[..., 1].astype(int), f[..., 2].astype(int)
    return (B > 200) & (G > 150) & (R < 150) & (B - R > 90)
# settled frame: top edge of cyan in each column band
fin = px[-1]; cf = cyan(fin); cf[:150 * SC] = False
cols = np.where(cf.any(0))[0]
bandF = None
for y in np.where(cf.any(1))[0]:
    if cf[y].sum() >= 10 * SC: bandF = y / SC; break
P(f'settled pipes top y = {bandF:.2f} pt; board centre y (JSON) = {oy + (d["rows"]-1)*p/2:.2f}, x = {ox + (d["cols"]-1)*p/2:.2f}')
rows = []
for k in range(len(t)):
    c = cyan(px[k]); c[:150 * SC] = False; c[800 * SC:] = False
    ys = np.where(c.any(1))[0]
    if len(ys) == 0: continue
    # topmost cyan row with a substantial run (>= 10 pt wide)
    top = None
    for y in ys:
        if c[y].sum() >= 10 * SC: top = y / SC; break
    if top is None: continue
    rows.append((t[k], top))
tt = np.array([r[0] for r in rows]); ty = np.array([r[1] for r in rows])
cy0 = oy + (d['rows'] - 1) * p / 2
for label, fixc in (('centre = board centre (JSON)', True), ('centre free', False)):
    def model(q, t):
        s0, D, n, ts = q[:4]; c = cy0 if fixc else q[4]
        u = np.clip((t - ts) / D, 0, 1)
        s = 1 + (s0 - 1) * (1 - u) ** n
        return c + s * (bandF - c), s
    q0 = [1.6, 1.1, 2.0, 0.38] + ([] if fixc else [430])
    lb = [1.01, 0.2, 0.5, 0.30] + ([] if fixc else [300]); ub = [4, 3, 6, 0.55] + ([] if fixc else [600])
    m = (tt > 0.39) & (tt < 2.2) & (ty > 150.5) & (ty < 240)
    r = least_squares(lambda q: model(q, tt[m])[0] - ty[m], q0, bounds=(lb, ub))
    res = model(r.x, tt[m])[0] - ty[m]
    P(f'== zoom fit ({label}): s0 {r.x[0]:.3f} at ts {r.x[3]:.3f}, D {r.x[1]:.3f} s, ease-out power n {r.x[2]:.2f}' + ('' if fixc else f', centre y {r.x[4]:.1f}') + f'; RMS {np.sqrt((res**2).mean()):.2f} pt over {m.sum()} frames')
    if fixc: qz = r.x
P('   t      top_y   model   s(t)')
for a, b in zip(tt, ty):
    if a > 1.75: break
    u = np.clip((a - qz[3]) / qz[1], 0, 1); s = 1 + (qz[0] - 1) * (1 - u) ** qz[2]
    P(f'   {a:.3f}  {b:6.1f}  {cy0 + s*(bandF-cy0):6.1f}  {s:.3f}')
# (b) per-arrow draw-in through the zoom (about the board centre)
cx0 = ox + (d['cols'] - 1) * p / 2
P('== draw-in: per arrow, fraction of the polyline (tail->head) inked; first/half/full times')
res_rows = []
for a in d['arrows']:
    pts = [np.array((ox + c * p, oy + r * p)) for c, r in a['cells']]
    S = []
    for u0, u1 in zip(pts[:-1], pts[1:]):
        for k in np.arange(0, 1, 0.1): S.append(u0 + (u1 - u0) * k)
    S.append(pts[-1]); S = np.array(S)
    fr = []
    for k in range(len(t)):
        u = np.clip((t[k] - qz[3]) / qz[1], 0, 1); s = 1 + (qz[0] - 1) * (1 - u) ** qz[2]
        X = cx0 + s * (S[:, 0] - cx0); Y = cy0 + s * (S[:, 1] - cy0)
        ok = (X > 1) & (X < 392) & (Y > 150) & (Y < 770)
        if ok.mean() < 0.9: fr.append(np.nan); continue
        ii = np.clip((Y * SC).astype(int), 0, px.shape[1] - 1); jj = np.clip((X * SC).astype(int), 0, px.shape[2] - 1)
        v = px[k][ii, jj].astype(int).mean(-1)
        ink = v < 100
        # drawn part = longest inked prefix from the tail
        pre = np.argmin(ink) if not ink.all() else len(ink)
        fr.append(pre / len(ink))
    fr = np.array(fr)
    def first(th):
        w = np.where(fr >= th)[0]
        return t[w[0]] if len(w) else np.nan
    res_rows.append((len(a['cells']), first(0.02), first(0.5), first(0.97), a['id']))
res_rows.sort()
for n, f0, f5, f1, aid in res_rows:
    P(f'   arrow {aid:3d} cells {n:3d}: 2% {f0:.3f}  50% {f5:.3f}  97% {f1:.3f}')
L = np.array([r[0] for r in res_rows]); F1 = np.array([r[3] for r in res_rows]); F5 = np.array([r[2] for r in res_rows])
m = ~np.isnan(F1)
if m.sum() > 3:
    c = np.polyfit(L[m], F1[m], 1); P(f'   complete time vs length: t97 = {c[1]:.3f} + {c[0]*1000:.2f} ms/cell (n={m.sum()}), spread {np.nanstd(F1):.3f} s')
m = ~np.isnan(F5)
if m.sum() > 3:
    c = np.polyfit(L[m], F5[m], 1); P(f'   half time vs length: t50 = {c[1]:.3f} + {c[0]*1000:.2f} ms/cell')
open(os.path.join(mf.SP, 'out', 'introdraw_L48.txt'), 'w').write('\n'.join(out) + '\n')
