import sys; sys.path.insert(0, '/Users/yago/Downloads/app-factory/apps/mazeout/research/motion-tools')
from mf import raw
import numpy as np
clip = sys.argv[1]; s = float(sys.argv[2]); e = float(sys.argv[3])
t, px = raw(clip, s, e, 393)
m = (t >= s) & (t <= e); t = t[m]; px = px[m].astype(int)
for i in range(len(t)):
    r = px[i][680:760, :]; R, G, B = r[..., 0], r[..., 1], r[..., 2]
    pu = (B > 150) & (R > 100) & (R < 200) & (G < 80)        # the balloon's purple stripes
    ys, xs = np.nonzero(pu)
    g = px[i][790:805, :]; gr = ((g[..., 1] > 170) & (g[..., 0] < 150) & (g[..., 2] < 110)).any(axis=0)
    gx = np.where(gr)[0]
    print(f'{t[i]:.3f} balloonX {xs.mean() if len(xs) > 20 else -1:6.1f} n {len(xs)} greenFillRight {gx.max() if len(gx) else -1}')
