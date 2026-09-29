# panelw.py CLIP S E y0 y1 [mode] : left/right extent of the panel frame colour (purple or blue) in rows y0..y1 → width, centre
import sys; sys.path.insert(0, '/Users/yago/Downloads/app-factory/apps/mazeout/research/motion-tools')
from mf import raw
import numpy as np
clip = sys.argv[1]; s = float(sys.argv[2]); e = float(sys.argv[3]); y0, y1 = int(sys.argv[4]), int(sys.argv[5])
t, px = raw(clip, s, e, 393)
m = (t >= s) & (t <= e); t = t[m]; px = px[m].astype(int)
for i in range(len(t)):
    r = px[i][y0:y1]
    R, G, B = r[..., 0], r[..., 1], r[..., 2]
    frame = (B > 170) & (B > G + 60)
    colf = frame.mean(axis=0) > 0.5
    cols = np.where(colf)[0]
    if len(cols) < 5: print(f'{t[i]:.3f} none L {px[i].mean():.1f}'); continue
    print(f'{t[i]:.3f} x {cols.min():3d}-{cols.max():3d} w {cols.max()-cols.min()+1:3d} c {(cols.min()+cols.max())/2:6.1f} L {px[i].mean():.1f}')
