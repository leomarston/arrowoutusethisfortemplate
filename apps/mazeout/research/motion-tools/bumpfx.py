"""v552 bump side effects: the red screen-edge vignette (colour at the edge + depth profile, left edge = clean white),
and the breaking 3rd heart (red-pixel count, centroid, bbox) per real frame. -> out/bumpfx_v552.txt"""
import os, sys
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mf
out = []
def P(s):
    print(s); out.append(s)
for clip, tc in [('S1-L47-bump-1.mov', 0.449), ('S1-L48-bump-2.mov', 0.400)]:
    P(f'== {clip} (contact frame {tc})')
    t, px = mf.raw(clip, tc - 0.05, tc + 0.45, width=240, crop=[0, 430, 80, 30], tag=clip + 'vig')   # 3 px/pt
    P('   vignette, left edge, row-mean RGB at x = 0.2 / 5 / 10 / 20 / 30 / 45 pt from the edge')
    for k in range(len(t)):
        f = px[k].astype(float).mean(0)
        cols = [int(v * 3) for v in (0.2, 5, 10, 20, 30, 45)]
        P(f'   {t[k]:.3f}  ' + '  '.join('(%d,%d,%d)' % tuple(f[c]) for c in cols))
    t, px = mf.raw(clip, tc - 0.05, tc + 0.6, width=180, crop=[262, 66, 60, 90], tag=clip + 'h3')   # 3 px/pt
    P('   heart 3 region x 262-322, y 66-156 pt: red px (R>190,G<110) count/9 = pt^2, centroid, bbox (pt)')
    for k in range(len(t)):
        f = px[k].astype(int); m = (f[:, :, 0] > 190) & (f[:, :, 1] < 110) & (f[:, :, 2] < 130)
        ys, xs = np.where(m)
        if len(ys) == 0:
            P(f'   {t[k]:.3f}  0'); continue
        P(f'   {t[k]:.3f}  {m.sum()/9:6.1f}  c=({262+xs.mean()/3:.1f},{66+ys.mean()/3:.1f})  x {262+xs.min()/3:.1f}-{262+xs.max()/3:.1f}  y {66+ys.min()/3:.1f}-{66+ys.max()/3:.1f}')
open(os.path.join(mf.SP, 'out', 'bumpfx_v552.txt'), 'w').write('\n'.join(out) + '\n')
