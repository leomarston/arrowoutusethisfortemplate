# knob.py CLIP S E [y0 y1]: blue knob x-centre and green/grey track fractions in the toggle row (x 200..330)
import sys; sys.path.insert(0, '/Users/yago/Downloads/app-factory/apps/mazeout/research/motion-tools')
from mf import raw
import numpy as np
clip = sys.argv[1]; s = float(sys.argv[2]); e = float(sys.argv[3])
y0 = int(sys.argv[4]) if len(sys.argv) > 4 else 332; y1 = int(sys.argv[5]) if len(sys.argv) > 5 else 362
t, px = raw(clip, s, e, 393)
m = (t >= s) & (t <= e); t = t[m]; px = px[m].astype(int)
for i in range(len(t)):
    r = px[i][y0:y1, 200:330]
    R, G, B = r[..., 0], r[..., 1], r[..., 2]
    blue = (B > 190) & (R < 90) & (G > 90) & (G < 190)
    green = (G > 170) & (R < 150) & (B < 120)
    cols = np.where(blue.mean(axis=0) > 0.5)[0]
    kx = (cols.min() + cols.max()) / 2 + 200 if len(cols) else -1
    kw = (cols.max() - cols.min() + 1) if len(cols) else 0
    print(f'{t[i]:.3f} knobX {kx:6.1f} knobW {kw:3d} green {green.mean():.3f}')
