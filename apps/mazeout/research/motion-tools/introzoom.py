"""v552 level intro: the board zooms out to its fit scale while the arrows draw in (tail -> head).
Scale per frame = median thickness of the cyan pipe tubes (1 cell wide) and of the black strokes, vs the settled frame;
fixed point from the pipes' top edge; ink (black px) fraction vs settled; HUD / booster presence. -> out/introzoom.txt"""
import os, sys
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mf
out = []
def P(s):
    print(s); out.append(s)
def runs(mask, axis):
    m = mask if axis == 0 else mask.T
    L = []
    for col in m.T:
        d = np.diff(np.concatenate([[0], col.astype(int), [0]]))
        st = np.where(d == 1)[0]; en = np.where(d == -1)[0]
        L += list(en - st)
    return np.array(L)
def cyan(f):
    R, G, B = f[..., 0], f[..., 1], f[..., 2]
    return (B > 200) & (G > 150) & (R < 150) & (B - R > 90)
SC = 2
for clip, t0 in (('S1-L48-play-intro.mov', 0.30), ('S1-L49-play-intro-superhard.mov', 0.36)):
    t, px = mf.raw(clip, t0, 3.9, width=393 * SC, crop=[0, 0, 393, 852], tag=clip + 'iz3')
    def meas(f):
        f = f.astype(int); c = cyan(f); c[:130 * SC] = False; c[770 * SC:] = False
        blk = f.mean(2) < 90; blk[:150 * SC] = False; blk[770 * SC:] = False
        rc = runs(c, 0); rc = rc[(rc > 3)]            # vertical runs of cyan (thickness of horizontal tube parts)
        rb = runs(blk, 1); rb = rb[(rb > 2) & (rb < 40)]  # horizontal runs of black (thickness of vertical strokes)
        ys = np.where(c.any(1))[0]
        top = ys[0] / SC if len(ys) else np.nan
        xs = np.where(c.any(0))[0]
        return (np.median(rc) / SC if len(rc) > 20 else np.nan, np.median(rb) / SC if len(rb) > 20 else np.nan, top,
                xs[0] / SC if len(xs) else np.nan, blk.sum(), f[:140 * SC, :, :].mean(), ((f[770 * SC:, :, 1] > 180) & (f[770 * SC:, :, 0] < 100)).sum())
    F = meas(px[-1])
    P(f'== {clip}: settled tube thickness {F[0]:.2f} pt, stroke {F[1]:.2f} pt, pipes top y {F[2]:.1f}, cyan left x {F[3]:.1f}')
    P('   t      s_tube  s_stroke  top_y  fixed_y   ink/final  topLum  boosterPx')
    for k in range(len(t)):
        if t[k] > 1.8 and k % 4: continue
        m = meas(px[k])
        s = m[0] / F[0]
        fy = (m[2] - s * F[2]) / (1 - s) if abs(1 - s) > 0.02 else np.nan
        P(f'   {t[k]:.3f}  {s:6.3f}  {m[1]/F[1]:6.3f}  {m[2]:6.1f}  {fy:7.1f}   {m[4]/F[4]:6.3f}   {m[5]:6.1f}  {m[6]}')
open(os.path.join(mf.SP, 'out', 'introzoom.txt'), 'w').write('\n'.join(out) + '\n')
