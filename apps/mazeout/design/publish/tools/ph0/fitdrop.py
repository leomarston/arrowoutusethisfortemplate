import numpy as np
from scipy.optimize import least_squares
# band top offsets from rest (234) per frame, first moving frame = k 1 (2.297); k 0 = 2.280 at rest
y = np.array([0, -27, -39, -11, 29, 79, 137, 201, 269, 339, 410, 479, 545, 606], float)
k = np.arange(len(y))
def inback(p):
    T, s, D, t0 = p; u = np.clip((k/60 + t0)/T, 0, 1); c3 = s + 1
    return D * (c3*u**3 - s*u**2)
r = least_squares(lambda p: inback(p) - y, [0.35, 1.7, 1000, 0.0], bounds=([0.1, 0, 300, -0.017], [1.5, 6, 5000, 0.017]))
print('easeInBack: T %.3f s  s %.2f  D %.0f  t0 %+.4f  RMS %.2f' % (*r.x, np.sqrt(((inback(r.x)-y)**2).mean())))
print(np.round(inback(r.x), 1))
# exit up after X (cancel): band bottom offsets (R1a 4.959 rest .. )
up = np.array([0, -73, -137, -199, -258, -312, -362, -408, -451, -489, -523, -553, -580, -602, -620, -635], float)
k2 = np.arange(len(up))
def outq(p, pw):
    T, D, t0 = p; u = np.clip((k2/60 + t0)/T, 0, 1)
    return -D * (1 - (1-u)**pw)
for pw in (2, 3):
    r2 = least_squares(lambda p: outq(p, pw) - up, [0.3, 660, 0.0], bounds=([0.1, 600, -0.017], [1, 1500, 0.017]))
    print('X-exit up, easeOut pow %d: T %.3f  D %.0f  t0 %+.4f  RMS %.2f' % (pw, *r2.x, np.sqrt(((outq(r2.x, pw)-up)**2).mean())))
best = None
for T in np.arange(0.15, 1.2, 0.01):
    for s in np.arange(0.2, 4, 0.05):
        for t0 in (-0.008, 0, 0.008, 0.017):
            u = np.clip((k/60 + t0)/T, 0, 1); b = (s+1)*u**3 - s*u**2
            if (b**2).sum() == 0: continue
            D = (b*y).sum()/(b*b).sum()
            e = np.sqrt(((D*b - y)**2).mean())
            if best is None or e < best[0]: best = (e, T, s, t0, D)
print('grid easeInBack: RMS %.2f T %.2f s %.2f t0 %+.3f D %.0f' % best)
e, T, s, t0, D = best; u = np.clip((k/60 + t0)/T, 0, 1); print(np.round(D*((s+1)*u**3 - s*u**2), 0))
