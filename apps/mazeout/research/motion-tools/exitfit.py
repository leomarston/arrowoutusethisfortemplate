"""Exit kinematics fit. Head/tail path-distance samples (pt) measured with headtrack.py / track1.py (see motion.md §1),
converted to CELLS with each level's pitch, fitted with a shared s(tau) and a per-clip release time t0 (bounded by the last
unchanged and the first changed frame). Prints parameters, RMS, residuals and a T(d) table."""
import numpy as np
from scipy.optimize import least_squares
D = {
 # clip: (pitch_pt, t_last_unchanged, t_first_changed, [(t, s_pt), ...])
 'P02-A (L32 0.786x, 26-cell snake, up)': (14.04, 0.482, 0.499, [
   (0.499,2.0),(0.549,12.5),(0.566,17.5),(0.582,23.0),(0.599,28.5),(0.616,34.5),(0.632,41.5),(0.682,65.0),(0.699,73.5),
   (0.715,82.5),(0.732,92.0),(0.749,102.0),(0.765,112.0),(0.815,144.0),(0.832,155.5),(0.849,167.0),(0.865,178.5),
   (0.882,190.5),(0.898,203.0),(0.998,280.5),(1.015,294.0),(1.032,308.0),
   # tail frames: s = 683.5 - tail_y
   (1.082,350.0),(1.098,364.5),(1.115,379.0),(1.131,393.5),(1.148,408.5),(1.165,423.5),(1.215,470.5),(1.231,484.5),
   (1.248,500.5),(1.265,515.5),(1.281,531.0)]),
 'P02-B (L32 0.786x, 2nd tap, right)': (14.04, 1.265, 1.281, [
   (1.281,2.5),(1.298,5.5),(1.364,21.5),(1.398,31.0),(1.414,38.0),(1.431,44.5),(1.448,52.5),(1.464,60.0),(1.514,87.0),
   (1.531,96.5),(1.547,106.5),(1.564,116.5),(1.581,127.0),(1.597,138.0)]),
 'P01 (L32 0.786x, 4-cell, right)': (14.04, 1.947, 1.964, [
   (1.964,2.0),(1.980,4.0),(1.997,8.5),(2.013,12.5),(2.030,17.0),(2.047,22.5),(2.063,28.5),(2.080,34.5),(2.097,41.5),
   (2.113,48.5),(2.130,56.5)]),
 'L33 key arrow (fit, up)': (17.857, 0.516, 0.532, [
   (0.532,2.5),(0.566,11.0),(0.582,16.0),(0.599,22.0),(0.616,29.0),(0.632,36.0),(0.649,44.0),(0.666,53.0),(0.682,62.0),
   (0.699,72.0),(0.716,84.0),(0.732,93.5),(0.749,105.0),(0.765,117.0),(0.782,129.5),(0.799,142.5),(0.815,156.0),
   (0.832,169.5),(0.849,183.5),(0.865,198.0),(0.882,212.5),(0.899,227.5),(0.915,242.5),(0.932,258.5),(0.965,290.5)]),
 'L35 pipe arrow (fit 28.09, right->pipe->down)': (28.092, 0.250, 0.266, [
   (0.266,4.5),(0.283,10.0),(0.299,16.5),(0.316,24.5),(0.333,34.0),(0.349,44.5),(0.366,56.5),(0.383,69.0),(0.399,83.0),
   (0.416,97.5),(0.433,113.0),
   # inside the pipe, vertical leg (tube centre x~352, corner at y~201): s = 243.5 + (y-201)
   (0.566,273.0),(0.582,296.5),(0.599,320.5),(0.616,345.0),(0.649,395.5),(0.666,421.0),(0.682,447.5),(0.699,474.5),(0.715,502.0)]),
}
names = list(D)
def unpack(p, model):
    k = {'exp': 3, 'cap': 3, 'quad': 2}[model]
    return p[:k], p[k:]
def s_model(tau, q, model):
    tau = np.maximum(tau, 0)
    if model == 'exp':
        v0, vmax, T = q
        return vmax * tau - (vmax - v0) * T * (1 - np.exp(-tau / T))
    if model == 'cap':
        v0, a, vmax = q
        tc = max((vmax - v0) / a, 0)
        return np.where(tau < tc, v0 * tau + 0.5 * a * tau ** 2, v0 * tc + 0.5 * a * tc ** 2 + vmax * (tau - tc))
    v0, a = q
    return v0 * tau + 0.5 * a * tau ** 2
def resid(p, model, subset):
    q, t0s = unpack(p, model)
    r = []
    for j, n in enumerate(subset):
        pitch, lo, hi, pts = D[n]
        t = np.array([a for a, b in pts]); s = np.array([b for a, b in pts]) / pitch
        r.append(s_model(t - t0s[j], q, model) - s)
    return np.concatenate(r)
def fit(model, subset):
    q0 = {'exp': [5, 64, 0.3], 'cap': [5, 150, 64], 'quad': [5, 150]}[model]
    lb = {'exp': [0, 10, 0.01], 'cap': [0, 1, 10], 'quad': [0, 0]}[model]
    ub = {'exp': [60, 200, 3], 'cap': [60, 2000, 200], 'quad': [100, 2000]}[model]
    t0 = [(D[n][1] + D[n][2]) / 2 for n in subset]
    tl = [D[n][1] - 0.02 for n in subset]; th = [D[n][2] for n in subset]
    r = least_squares(resid, q0 + t0, bounds=(lb + tl, ub + th), args=(model, subset))
    return r
if __name__ == '__main__':
    for model in ('exp', 'cap', 'quad'):
        r = fit(model, names)
        q, t0s = unpack(r.x, model)
        res = resid(r.x, model, names)
        print(f"== model {model}: params {np.round(q,3)}  RMS {np.sqrt((res**2).mean()):.3f} cells over {len(res)} samples")
        k = 0
        for j, n in enumerate(names):
            m = len(D[n][3]); rr = res[k:k + m]; k += m
            print(f"   {n:48s} t0={t0s[j]:.3f} (window {D[n][1]:.3f}..{D[n][2]:.3f})  rms {np.sqrt((rr**2).mean()):.3f} c  max {abs(rr).max():.3f} c")
    # leave-one-zoom-out check in PT units would fail if motion were screen-space: fit in pt instead
    print('== same exp model but in POINTS (screen-space hypothesis):')
    Dc = {n: (1.0,) + D[n][1:] for n in names}
    saved = dict(D); D.update(Dc)
    r = fit('exp', names); res = resid(r.x, 'exp', names)
    print('   params', np.round(r.x[:3], 2), f'RMS {np.sqrt((res**2).mean()):.2f} pt')
    D.update(saved)
    # T(d) table from the exp fit
    r = fit('exp', names); q, _ = unpack(r.x, 'exp')
    print('== T(d): time from release until the head has travelled d cells (exp model)')
    tau = np.linspace(0, 3, 30001); s = s_model(tau, q, 'exp')
    for d in (1, 2, 3, 5, 8, 10, 15, 20, 25, 30, 40, 50, 60, 80):
        print(f"   d={d:3d} cells  T={tau[np.searchsorted(s, d)]:.3f} s")
    print('== velocity profile (cells/s):', ' '.join(f"{x:.2f}s:{(q[1]-(q[1]-q[0])*np.exp(-x/q[2])):.1f}" for x in (0, .05, .1, .2, .3, .4, .5, .7, 1.0)))
