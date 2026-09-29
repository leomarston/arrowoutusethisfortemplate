"""Exit kinematics fit, pass 2: pass-1 exits (exitfit.D, 5 exits) + 6 new v552 exits from exittrack.py (L47 44-cell
head-tap snake, L52 x3, L50 x2). Shared s(tau) in CELLS, per-exit release t0 bounded by the last still / first moved
frame. Reports the exp model, per-exit RMS, and linear T = a + b*d over every (distance, time) pair. -> out/exitfit2.txt"""
import os, sys, re
import numpy as np
from scipy.optimize import least_squares
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import exitfit
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'out')
D = dict(exitfit.D)
NEW = {  # name: (pitch, use 'head' or 'tail', label)
 'L47-headtap': (17.87, 'tail', 'L47 44-cell snake, head tap, right (fit 17.87)'),
 'L52-a': (26.199, 'head', 'L52 2-cell, left (fit 26.2), 1st of 3 taps'),
 'L52-b': (26.199, 'head', 'L52 5-cell, left, 2nd tap +0.58 s'),
 'L52-c': (26.199, 'head', 'L52 42-cell, down, 3rd tap (violet)'),
 'L50-box': (28.07, 'head', 'L50 6-cell, right (fit/max 28.07)'),
 'L50-last': (28.07, 'head', 'L50 11-cell, right, last arrow'),
}
for n, (pitch, which, lab) in NEW.items():
    rows = []
    for l in open(os.path.join(OUT, f'exittrack_{n}.txt')):
        m = re.match(r'\s+([\d.]+)\s+([-\d.]+)\s+([-\d.nan]+)\s+([-\d.]+)\s+([-\d.nan]+)', l)
        if m: rows.append(tuple(float(x) for x in m.groups()))
    hdr = open(os.path.join(OUT, f'exittrack_{n}.txt')).read()
    rayend = float(re.search(r'visible until s=([\d.]+)', hdr).group(1)); head0 = float(re.search(r'rest head tip s=([\d.]+)', hdr).group(1))
    lim = rayend - head0 - 1.0
    i1 = next(i for i, r in enumerate(rows) if r[3] != 0 or r[4] != 0)
    lo, hi = rows[i1 - 1][0], rows[i1][0]
    pts = []; best = -1
    for r in rows[i1:]:
        dsp = r[3] if which == 'head' else r[4]
        if which == 'head' and dsp >= lim: break
        if which == 'tail' and (r[0] > 1.0 or dsp < best - 2): continue
        best = max(best, dsp); pts.append((r[0], dsp))
    D[lab] = (pitch, lo, hi, pts)
names = list(D)
lines = []
def P(s):
    print(s); lines.append(s)
def s_model(tau, q):
    v0, vmax, T = q; tau = np.maximum(tau, 0)
    return vmax * tau - (vmax - v0) * T * (1 - np.exp(-tau / T))
def resid(p, subset, loss_pts=False):
    q, t0s = p[:3], p[3:]; r = []
    for j, n in enumerate(subset):
        pitch, lo, hi, pts = D[n]
        t = np.array([a for a, b in pts]); s = np.array([b for a, b in pts]) / pitch
        r.append(s_model(t - t0s[j], q) - s)
    return np.concatenate(r)
def fit(subset):
    t0 = [(D[n][1] + D[n][2]) / 2 for n in subset]
    r = least_squares(resid, [5, 64, 0.3] + t0, bounds=([0, 10, 0.01] + [D[n][1] - 0.02 for n in subset], [60, 200, 3] + [D[n][2] for n in subset]),
                      args=(subset,), loss='soft_l1', f_scale=0.2)
    return r
r = fit(names); q = r.x[:3]; t0s = r.x[3:]; res = resid(r.x, names)
P(f'== exp model over {len(names)} exits / {len(res)} samples: v0 {q[0]:.2f} c/s, vmax {q[1]:.2f} c/s, T {q[2]:.3f} s; RMS {np.sqrt((res**2).mean()):.3f} cells (robust soft-L1 fit)')
k = 0; pairs = []
for j, n in enumerate(names):
    pitch, lo, hi, pts = D[n]; m = len(pts); rr = res[k:k + m]; k += m
    P(f'   {n:52s} n={m:3d} t0={t0s[j]:.3f} [{lo:.3f},{hi:.3f}] d_max {max(b for a,b in pts)/pitch:5.1f} c  rms {np.sqrt((rr**2).mean()):.3f} c  max {abs(rr).max():.3f} c')
    for a, b in pts:
        pairs.append((b / pitch, a - t0s[j], n))
# leave-new-out check: pass-1 params predicting the new exits
old = list(exitfit.D); rO = fit(old); qO = rO.x[:3]
P(f'== pass-1-only fit (5 exits): v0 {qO[0]:.2f} vmax {qO[1]:.2f} T {qO[2]:.3f}; predicting the 6 NEW exits (their t0 refitted alone):')
for n in [x for x in names if x not in old]:
    pitch, lo, hi, pts = D[n]
    t = np.array([a for a, b in pts]); s = np.array([b for a, b in pts]) / pitch
    best = min(((np.sqrt(((s_model(t - t0, qO) - s) ** 2).mean())), t0) for t0 in np.arange(lo - 0.02, hi + 1e-9, 0.001))
    P(f'   {n:52s} rms {best[0]:.3f} c (t0 {best[1]:.3f})')
d = np.array([p[0] for p in pairs]); T = np.array([p[1] for p in pairs])
P(f'== linear T = a + b*d over (distance cells, time since release s) pairs; {len(set(p[2] for p in pairs))} exits')
for lo_d, hi_d in ((0, 45), (2, 45), (5, 45), (1, 12)):
    m = (d >= lo_d) & (d <= hi_d)
    A = np.vstack([np.ones(m.sum()), d[m]]).T; c, *_ = np.linalg.lstsq(A, T[m], rcond=None)
    rms = np.sqrt(((A @ c - T[m]) ** 2).mean())
    P(f'   {lo_d:>2}..{hi_d} cells: T = {c[0]:.3f} + {c[1]:.4f}*d   n={m.sum()}  RMS {rms*1000:.1f} ms')
P('== T(d) from the exp model (time from release until the HEAD has travelled d cells)')
from scipy.optimize import brentq
row = []
for dd in (0.5, 1, 2, 3, 4, 5, 6, 8, 10, 12, 15, 20, 25, 30, 40, 50, 60, 80):
    row.append(f'{dd}:{brentq(lambda x: s_model(x, q) - dd, 0, 5):.3f}')
P('   ' + '  '.join(row))
P('   velocity c/s: ' + '  '.join(f'{x:.2f}s:{q[1] - (q[1]-q[0])*np.exp(-x/q[2]):.1f}' for x in (0, 0.05, 0.1, 0.2, 0.3, 0.5, 0.7, 1.0, 1.5)))
open(os.path.join(OUT, 'exitfit2.txt'), 'w').write('\n'.join(lines) + '\n')
