# track.py CLIP x0 y0 x1 y1 colour [step] : top y and centroid of a colour class inside the box, sampled every STEP s
import sys; sys.path.insert(0, '/Users/yago/Downloads/app-factory/apps/mazeout/research/motion-tools')
from mf import raw
import numpy as np
clip = sys.argv[1]; x0, y0, x1, y1 = map(int, sys.argv[2:6]); col = sys.argv[6]; step = float(sys.argv[7]) if len(sys.argv) > 7 else 0
t, px = raw(clip, 0, 999, 393)
last = -9
for i in range(len(t)):
    if t[i] - last < step: continue
    last = t[i]
    r = px[i][y0:y1, x0:x1].astype(int); R, G, B = r[..., 0], r[..., 1], r[..., 2]
    if col == 'red': m = (R > 180) & (G < 90) & (B < 90)
    elif col == 'yellow': m = (R > 220) & (G > 140) & (G < 210) & (B < 90)
    elif col == 'purple': m = (B > 150) & (R > 110) & (G < 90)
    else: m = (R > 230) & (G > 230) & (B > 230)
    ys, xs = np.nonzero(m)
    if len(ys) < 10: print(f'{t[i]:.3f} none'); continue
    print(f'{t[i]:.3f} top {np.percentile(ys, 2) + y0:6.1f} cy {ys.mean() + y0:6.1f} n {len(ys)}')
