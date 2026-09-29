"""FTUE tutorial hand (YT-A L1-4 stage 1): yellow hand bbox per frame (pt). out/hand_YTA.txt"""
import os, sys
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import yt, mf
t, px = yt.raw('A', 0.7, 3.8, 393, fps=240, crop=[0, 150, 393, 450])
L = []
for i in range(len(t)):
    f = px[i].astype(int); R, G, B = f[..., 0], f[..., 1], f[..., 2]
    ys, xs = np.where((R > 220) & (G > 150) & (G < 225) & (B < 110))
    L.append(f"{t[i]:.2f} " + (f"hand x {xs.min()}-{xs.max()} y {ys.min()+150}-{ys.max()+150} h {ys.max()-ys.min()} n {len(xs)}" if len(xs) > 30 else "hand -"))
open(os.path.join(mf.SP, 'out', 'hand_YTA.txt'), 'w').write('\n'.join(L) + '\n'); print(len(L))
