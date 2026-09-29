# slide.py CLIP "tShop,tHome,tLead" S E : camera offset c on the 3-page strip [Shop | Home | Leaderboard] per frame (pt, 0 = Shop, 393 = Home, 786 = Lead)
import sys; sys.path.insert(0, '/Users/yago/Downloads/app-factory/apps/mazeout/research/motion-tools')
from mf import raw
import numpy as np
clip = sys.argv[1]; tref = [float(v) for v in sys.argv[2].split(',')]; s = float(sys.argv[3]); e = float(sys.argv[4])
t, px = raw(clip, 0, 999, 393)
g = px.astype(np.float32).mean(axis=3)[:, 110:740:3, :]      # rows 110..740 (skip top HUD + bottom nav), every 3rd
refs = [g[int(np.argmin(np.abs(t - x)))] for x in tref]
strip = np.concatenate(refs, axis=1)                           # H x 1179
m = (t >= s) & (t <= e)
prev = None
for i in np.where(m)[0]:
    f = g[i]
    best = None
    for c in range(0, 787, 3):
        d = np.abs(strip[:, c:c + 393] - f).mean()
        if best is None or d < best[0]: best = (d, c)
    c0 = best[1]
    for c in range(max(0, c0 - 3), min(786, c0 + 3) + 1):
        d = np.abs(strip[:, c:c + 393] - f).mean()
        if d < best[0]: best = (d, c)
    print(f'{t[i]:.3f} c {best[1]:4d} err {best[0]:5.1f}')
