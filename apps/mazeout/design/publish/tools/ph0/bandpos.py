# bandpos.py CLIP S E : per frame, the purple/blue band extent at the screen edges (x 3..12 pt) and the red button's centroid y
import sys; sys.path.insert(0, '/Users/yago/Downloads/app-factory/apps/mazeout/research/motion-tools')
from mf import raw
import numpy as np
clip = sys.argv[1]; s = float(sys.argv[2]); e = float(sys.argv[3])
t, px = raw(clip, s, e, 393)
m = (t >= s) & (t <= e); t = t[m]; px = px[m].astype(int)
for i in range(len(t)):
    f = px[i]
    edge = f[:, 3:12]
    R, G, B = edge[..., 0], edge[..., 1], edge[..., 2]
    band = ((B > 150) & (B > G + 70)).mean(axis=1) > 0.6   # purple or blue band rows
    rows = np.where(band)[0]
    top = rows.min() if len(rows) else -1; bot = rows.max() if len(rows) else -1
    mid = f[:, 120:270]
    red = (mid[..., 0] > 190) & (mid[..., 1] < 90) & (mid[..., 2] < 90)
    ry = np.where(red.any(axis=1))[0]
    rc = (np.nonzero(red)[0].mean() if red.sum() > 50 else -1)
    wid = red.sum(axis=0); cols = np.where(wid > 0)[0]
    rw = (cols.max() - cols.min() + 1) if len(cols) else 0
    L = f.mean()
    print(f'{t[i]:.3f} band {top:4d}-{bot:4d} ({len(rows):3d} rows) redC {rc:6.1f} redW {rw:3d} L {L:5.1f}')
