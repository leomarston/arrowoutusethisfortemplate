"""Scan the owner's videos for heart losses: red-heart count in the HUD pill (crop x190-330, y55-115 pt) at 4 fps.
Prints every change of the red-heart count (with the in-level state); out/hearts_scan_{A,B}.txt"""
import sys, os
import numpy as np
from scipy import ndimage
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import yt, mf
key = sys.argv[1]
dur = {'A': 505, 'B': 1683}[key]
fps = float(sys.argv[2]) if len(sys.argv) > 2 else 4
res = []
for s in range(0, dur, 150):
    t, px = yt.raw(key, s, min(s + 150, dur), 140, fps=fps, crop=[190, 55, 140, 60])
    for i in range(len(t)):
        f = px[i].astype(int); R, G, B = f[..., 0], f[..., 1], f[..., 2]
        red = (R > 190) & (G < 90) & (B < 90)
        lab, n = ndimage.label(red)
        blobs = [(len(np.where(lab == k)[0]), np.where(lab == k)[1].mean()) for k in range(1, n + 1)]
        blobs = [b for b in blobs if b[0] > 40]
        res.append((t[i], len(blobs), [int(b[0]) for b in blobs], [int(b[1]) for b in blobs]))
out = []
prev = None
for (tt, n, sz, xs) in res:
    if n != prev:
        out.append(f"{tt:8.2f} red hearts {n} sizes {sz} x {xs}")
        prev = n
open(os.path.join(mf.SP, 'out', f'hearts_scan_{key}.txt'), 'w').write('\n'.join(out) + '\n')
print('\n'.join(out))
