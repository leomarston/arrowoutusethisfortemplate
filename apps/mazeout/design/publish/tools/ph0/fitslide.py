import numpy as np
from scipy.optimize import least_squares
one = np.array([393, 359, 329, 299, 271, 245, 220, 197, 175, 155, 137, 120, 104, 90, 77, 65, 54, 45, 36, 29, 22, 16, 12, 8, 4, 2, 0], float)
two = np.array([786, 717, 657, 597, 541, 488, 439, 393, 350, 311, 274, 240, 208, 180, 154, 130, 108, 89, 72, 57, 44, 33, 23, 15, 9, 4, 0], float)
v2 = np.array([393, 359, 327, 297, 265, 244, 220, 196, 174, 154, 136, 120, 104, 90, 76, 64, 54, 44, 36, 28, 22, 16, 12, 8, 4, 2, 0], float)
def powfit(y, D):
    k = np.arange(len(y)); m = k >= 1   # frame 0 = the last still frame (motion starts after it)
    f = lambda p: D * np.clip(1 - (k[m]/60 - p[2]) / p[0], 0, 1) ** p[1] - y[m]
    r = least_squares(f, [0.5, 2.5, 0.005], bounds=([0.2, 1, -0.017], [1, 5, 0.017]))
    return r.x, np.sqrt((f(r.x)**2).mean())
for name, y, D in (('v582 1-page', one, 393), ('v582 2-page', two, 786), ('V2 (motion A3)', v2, 393)):
    (T, p, t0), rms = powfit(y, D)
    print(f'{name}: D(1-u)^p  T {T:.3f} s  p {p:.2f}  t0 {t0*1000:+.1f} ms  RMS {rms:.2f} pt')
    # the catalog's curve: p 2.56, T 0.50
    k = np.arange(len(y)); m = k >= 1
    f2 = lambda q: D * np.clip(1 - (k[m]/60 - q[0]) / 0.50, 0, 1) ** 2.56 - y[m]
    r2 = least_squares(f2, [0.0], bounds=([-0.017], [0.017]))
    print(f'   vs the catalog curve (T 0.50, p 2.56) with the best start: t0 {r2.x[0]*1000:+.1f} ms  RMS {np.sqrt((f2(r2.x)**2).mean()):.2f} pt  max {np.abs(f2(r2.x)).max():.1f}')
print('normalised 2-page/1-page max diff', np.abs(two/786 - one/393).max())
print('1-page v582 vs V2 max diff pt', np.abs(one - v2).max())
