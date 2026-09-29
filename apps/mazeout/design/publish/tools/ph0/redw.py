# redw.py CLIP S E x0 y0 x1 y1 : red-blob width/height/centre inside the box (button press scale)
import sys; sys.path.insert(0, '/Users/yago/Downloads/app-factory/apps/mazeout/research/motion-tools')
from mf import raw
import numpy as np
clip = sys.argv[1]; s = float(sys.argv[2]); e = float(sys.argv[3]); x0, y0, x1, y1 = map(int, sys.argv[4:8])
t, px = raw(clip, s, e, 393)
m = (t >= s) & (t <= e); t = t[m]; px = px[m].astype(int)
for i in range(len(t)):
    r = px[i][y0:y1, x0:x1]
    red = (r[..., 0] > 170) & (r[..., 1] < 80) & (r[..., 2] < 90)
    ys, xs = np.nonzero(red)
    if len(xs) < 20: print(f'{t[i]:.3f} none'); continue
    print(f'{t[i]:.3f} w {xs.max()-xs.min()+1:3d} h {ys.max()-ys.min()+1:3d} cx {xs.mean()+x0:6.1f} cy {ys.mean()+y0:6.1f} n {len(xs)}')
