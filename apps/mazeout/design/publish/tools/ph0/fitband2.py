import numpy as np
from scipy.optimize import least_squares
y = np.array([-576, -497, -415, -333, -254, -179, -112, -56, -14, 14, 26, 28], float)  # frames 0..11 (F = first band frame)
k = np.arange(len(y))
def bez(x1, y1, x2, y2, u):
    # solve x(s)=u by bisection, return y(s)
    lo = np.zeros_like(u); hi = np.ones_like(u)
    for _ in range(50):
        s = (lo + hi) / 2
        xs = 3*(1-s)**2*s*x1 + 3*(1-s)*s*s*x2 + s**3
        lo = np.where(xs < u, s, lo); hi = np.where(xs >= u, s, hi)
    s = (lo + hi) / 2
    return 3*(1-s)**2*s*y1 + 3*(1-s)*s*s*y2 + s**3
def model(p):
    x1, y1, x2, y2, T, t0, D0 = p       # starts at -D0 at time -t0 (before F), reaches +28 at T - t0
    u = np.clip((k/60 + t0) / T, 0, 1)
    return -D0 + (D0 + 28) * bez(x1, y1, x2, y2, u)
for D0 in (638, None):
    if D0:
        f = lambda p: model([*p, D0]) - y; p0 = [0.3, 0.3, 0.6, 1.0, 0.2, 0.017]; lb = [0, -1, 0, 0, 0.1, 0]; ub = [1, 2, 1, 2, 0.4, 0.05]
    else:
        f = lambda p: model(p) - y; p0 = [0.3, 0.3, 0.6, 1.0, 0.2, 0.017, 650]; lb = [0, -1, 0, 0, 0.1, 0, 600]; ub = [1, 2, 1, 2, 0.4, 0.1, 900]
    r = least_squares(f, p0, bounds=(lb, ub)); res = f(r.x)
    print('D0', D0, 'params', np.round(r.x, 4), 'RMS %.2f max %.1f' % (np.sqrt((res**2).mean()), np.abs(res).max()))
    print('  model', np.round(model(r.x if D0 is None else [*r.x, D0]), 1))
