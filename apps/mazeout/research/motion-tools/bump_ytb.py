"""Bump measurements in YT-B (older blue-skin build, 60 fps): red screen-edge vignette (green channel at the left edge vs
inside), heart redness, and the bumped arrow's axis profile for the 1249 event. out/bump_YTB.txt"""
import os, sys
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import yt, mf
L = []
for (a, b) in [(1235.0, 1235.8), (1249.2, 1250.0)]:
    t, px = yt.raw('B', a, b, 393, fps=240)
    L.append(f'# event {a}: edge G (x0-4, x14-18, x40-44 pt, y300-600), centre G, heart2/heart3 red fraction')
    for i in range(len(t)):
        f = px[i].astype(float)
        e = f[300:600, 0:4].mean((0, 1)); e2 = f[300:600, 14:18].mean((0, 1)); e3 = f[300:600, 40:44].mean((0, 1)); c = f[300:600, 190:200].mean((0, 1))
        h3 = f[80:95, 280:296].reshape(-1, 3); h2 = f[80:95, 244:260].reshape(-1, 3)
        r3 = ((h3[:, 0] > 190) & (h3[:, 1] < 90)).mean(); r2 = ((h2[:, 0] > 190) & (h2[:, 1] < 90)).mean()
        L.append(f"{t[i]:.3f} edgeG {e[1]:5.1f} {e2[1]:5.1f} {e3[1]:5.1f} centreG {c[1]:5.1f} heart2 {r2:.2f} heart3 {r3:.2f}")
t, px = yt.raw('B', 1249.2, 1249.75, 400, fps=240, crop=[100, 320, 100, 100])
L.append('# 1249 event: ink along the bumped arrow axis x=134.25 pt, rows 345..390 pt (1 char = 1 pt; # ink, o light)')
for i in range(len(t)):
    f = px[i].astype(int); line = ''
    for ypt in np.arange(345, 391, 1.0):
        r = int((ypt - 320) * 4); p = f[r, 135:140].mean(0); R, G, B = p; Lm = p.mean()
        line += '#' if ((B - R > 45 and Lm < 225) or Lm < 150) else ('o' if Lm < 235 else '.')
    L.append(f"{t[i]:.3f} {line}")
open(os.path.join(mf.SP, 'out', 'bump_YTB.txt'), 'w').write('\n'.join(L) + '\n')
print(len(L), 'lines')
