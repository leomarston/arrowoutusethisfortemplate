"""Fit the v552 intro zoom-out on the clean window (pipes top edge visible, 0.549..1.47 s) with three laws; the
scale is about the board centre (y 439.26). Input: the t/top_y table in out/introdraw_L48.txt. -> out/introfit_L48.txt"""
import os, re
import numpy as np
from scipy.optimize import least_squares
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'out')
rows = [tuple(map(float, m.groups())) for m in re.finditer(r'\n\s+([\d.]+)\s+([\d.]+)\s+[\d.]+\s+[\d.]+', open(os.path.join(OUT, 'introdraw_L48.txt')).read())]
t = np.array([r[0] for r in rows]); y = np.array([r[1] for r in rows])
m = (y > 150.5) & (t < 1.47); t, y = t[m], y[m]
cy, yF = 439.26, 223.33
s = (cy - y) / (cy - yF)
lines = [f'clean frames {len(t)} ({t[0]:.3f}..{t[-1]:.3f}); s = (439.26 - top_y) / (439.26 - 223.33)']
TC = 0.375   # hard-cut frame (first level frame 0.383, last home frame 0.366)
def fit(name, f, q0, lb, ub):
    r = least_squares(lambda q: f(q, t) - s, q0, bounds=(lb, ub))
    res = f(r.x, t) - s
    lines.append(f'== {name}: params {np.round(r.x, 4).tolist()}  RMS {np.sqrt((res**2).mean())*1000:.2f} milli-scale (x{cy-yF:.0f} pt = {np.sqrt((res**2).mean())*(cy-yF):.2f} pt); s(cut {TC}) = {f(r.x, np.array([TC]))[0]:.3f}; s(0.8) {f(r.x, np.array([0.8]))[0]:.3f}; 1% at t = {next((x for x in np.arange(0.4, 3, 0.001) if f(r.x, np.array([x]))[0] < 1.01), np.nan):.3f}')
    return r.x
fit('exponential s = 1 + A exp(-(t-TC)/tau)', lambda q, t: 1 + q[0] * np.exp(-(t - TC) / q[1]), [0.5, 0.3], [0, 0.01], [5, 5])
fit('critically damped spring from rest at TC: s = 1 + A(1 + w(t-TC)) exp(-w(t-TC))', lambda q, t: 1 + q[0] * (1 + q[1] * (t - TC)) * np.exp(-q[1] * (t - TC)), [0.5, 5], [0, 0.1], [5, 50])
fit('ease-out power, ends at TC + D: s = 1 + A (1-u)^n', lambda q, t: 1 + q[0] * (1 - np.clip((t - TC) / q[1], 0, 1)) ** q[2], [0.5, 1.2, 2], [0, 0.3, 0.5], [5, 5, 12])
lines.append('   t      s_meas')
for a, b in zip(t[::3], s[::3]): lines.append(f'   {a:.3f}  {b:.4f}')
open(os.path.join(OUT, 'introfit_L48.txt'), 'w').write('\n'.join(lines) + '\n'); print('\n'.join(lines[:5]))
