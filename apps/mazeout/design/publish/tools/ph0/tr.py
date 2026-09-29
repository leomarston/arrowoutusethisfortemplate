# tr.py CLIP S E [WIDTH] [crop x,y,w,h] : per-frame distance to the first and last frame in [S,E] (0..1), + mean luminance
import sys; sys.path.insert(0, '/Users/yago/Downloads/app-factory/apps/mazeout/research/motion-tools')
from mf import raw
import numpy as np
clip = sys.argv[1]; s = float(sys.argv[2]); e = float(sys.argv[3]); w = int(sys.argv[4]) if len(sys.argv) > 4 else 66
crop = [float(v) for v in sys.argv[5].split(',')] if len(sys.argv) > 5 else None
t, px = raw(clip, 0, 999, w, crop=crop)
m = (t >= s) & (t <= e); t = t[m]; px = px[m].astype(np.float32)
a, b = px[0], px[-1]
for i in range(len(t)):
    da = np.abs(px[i] - a).mean() / 255; db = np.abs(px[i] - b).mean() / 255
    dp = np.abs(px[i] - px[i-1]).mean() / 255 if i else 0
    L = px[i].mean()
    print(f'{t[i]:.3f} dFirst {da:.3f} dLast {db:.3f} dPrev {dp:.3f} L {L:.1f}')
