# balloony.py CLIP S E : balloon envelope (yellow-orange stripes) top / centroid y in x 240..392
import sys; sys.path.insert(0, '/Users/yago/Downloads/app-factory/apps/mazeout/research/motion-tools')
from mf import raw
import numpy as np
clip = sys.argv[1]; s = float(sys.argv[2]); e = float(sys.argv[3])
t, px = raw(clip, s, e, 393)
m = (t >= s) & (t <= e); t = t[m]; px = px[m].astype(int)
prev = None
for i in range(len(t)):
    r = px[i][250:, 240:392]
    R, G, B = r[..., 0], r[..., 1], r[..., 2]
    yel = (R > 225) & (G > 140) & (G < 205) & (B < 90)
    ys, xs = np.nonzero(yel)
    if len(ys) < 50: print(f'{t[i]:.3f} none'); continue
    top = np.percentile(ys, 1) + 250; cy = ys.mean() + 250
    line = f'top {top:6.1f} cy {cy:6.1f} n {len(ys)}'
    print(f'{t[i]:.3f} {line}')
