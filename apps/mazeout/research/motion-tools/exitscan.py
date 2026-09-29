"""Exit colour census in the owner's videos. Tap = onset of the grey release ripple (neutral grey disc on the light board).
For each tap: time, gap to the previous tap, and the hue classes of saturated non-idle pixels that APPEAR 0.12-0.40 s later
within 90 pt of the tap (cyan = the phone's blue exit, violet, magenta, warm = red/orange/yellow, green).
Processes 20 s chunks, one frame at a time (memory-light).
Usage: exitscan.py A|B START END [FPS]  -> out/exitscan_{key}_{S}_{E}.txt"""
import sys, os
import numpy as np
from scipy import ndimage
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import yt, mf
key = sys.argv[1]; S = float(sys.argv[2]); E = float(sys.argv[3]); FPS = float(sys.argv[4]) if len(sys.argv) > 4 else 30
W = 100; s = W / 393.0
NAMES = ['cyan', 'violet', 'magenta', 'warm', 'green']

def masks(fr8):
    f = fr8.astype(np.int16)
    mx = f.max(-1); mn = f.min(-1); L = f.mean(-1)
    grey = (mx - mn < 14) & (L > 120) & (L < 228)
    sat = (mx - mn > 90) & (mx > 150)
    fr = f.astype(np.float32) / 255
    cmax = fr.max(-1); cmin = fr.min(-1); d = cmax - cmin + 1e-6
    h = np.where(cmax == fr[..., 0], ((fr[..., 1] - fr[..., 2]) / d) % 6,
                 np.where(cmax == fr[..., 1], (fr[..., 2] - fr[..., 0]) / d + 2, (fr[..., 0] - fr[..., 1]) / d + 4)) * 60
    G = f[..., 1]
    m = {'cyan': sat & (h >= 188) & (h <= 206) & (G >= 150), 'violet': sat & (h > 245) & (h <= 295),
         'magenta': sat & (h > 295) & (h <= 350), 'warm': sat & ((h > 350) | (h < 70)), 'green': sat & (h >= 70) & (h < 170)}
    return grey, m

T = []; GR = []; M = {n: [] for n in NAMES}
c = S
while c < E:
    t, px = yt.raw(key, c, min(c + 20, E), W, fps=FPS, crop=[0, 130, 393, 610])
    for i in range(len(t)):
        if T and t[i] <= T[-1] + 1e-4: continue
        g, m = masks(px[i]); T.append(t[i]); GR.append(g)
        for n in NAMES: M[n].append(m[n])
    del px
    c += 20
T = np.array(T)
# new grey pixels vs 3 frames earlier (static grey UI cancels out)
ng = np.array([0] * 3 + [int((GR[i] & ~GR[i - 3]).sum()) for i in range(3, len(T))])
taps = []
last = -9
for i in range(3, len(T)):
    if ng[i] >= 5 and ng[i - 1] < 3 and T[i] - last > 0.12:
        last = T[i]
        newg = GR[i] & ~GR[i - 3]
        lab, n = ndimage.label(newg)
        sizes = ndimage.sum(newg, lab, range(1, n + 1)); k = int(np.argmax(sizes)) + 1
        yy, xx = np.where(lab == k)
        taps.append((i, T[i], xx.mean() / s, yy.mean() / s + 130))
yy, xx = np.mgrid[0:GR[0].shape[0], 0:GR[0].shape[1]]
lines = []; prev = None
for (i, tt, x, y) in taps:
    near = ((xx / s - x) ** 2 + (yy / s + 130 - y) ** 2) < 90 ** 2
    j0 = max(i - 2, 0)
    a = np.searchsorted(T, tt + 0.12); b = np.searchsorted(T, tt + 0.40)
    cnt = {}
    for n in NAMES:
        before = M[n][j0] & near
        best = 0
        for j in range(a, max(b, a + 1)):
            if j < len(T): best = max(best, int((M[n][j] & near & ~before).sum()))
        cnt[n] = int(best / s / s)
    top = max(cnt, key=cnt.get)
    kind = 'rainbow' if cnt['green'] > 8 and cnt['warm'] > 8 else (top if cnt[top] > 8 else '?')
    gap = tt - prev if prev is not None else -1
    prev = tt
    lines.append(f"{tt:9.3f} tap ({x:5.1f},{y:5.1f}) gap {gap:6.2f}s  " + ' '.join(f"{n} {cnt[n]:4d}" for n in NAMES) + f" -> {kind}")
out = os.path.join(mf.SP, 'out', f'exitscan_{key}_{int(S)}_{int(E)}.txt')
open(out, 'w').write('\n'.join(lines) + '\n')
print('\n'.join(lines))
