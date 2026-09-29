"""v552 win sequence (S1-L50-win-seq-1, unskipped, 60/30 fps): per frame, the background luminance (dim), the vacated-
dot colour state (rainbow wave), the sign / OUT! presence (bbox of saturated blue & purple & white-3D in the logo band),
confetti count, and the win-panel presence. -> out/winscan_v552.txt"""
import os, sys
import numpy as np
from scipy import ndimage
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mf
t, px = mf.raw('S1-L50-win-seq-1.mov', 0.3, 10.0, width=131, crop=[0, 0, 393, 852], tag='winv552')
S = 131 / 393
out = ['t      bgLum(y640-700,x150-250)  dotSat(board)  dotHueMean  blueSign(px)  purple(px)  white3D(px) bboxWhite(x0-x1)  panelBlue  confetti']
prev = None
for k in range(len(t)):
    f = px[k].astype(int); R, G, B = f[..., 0], f[..., 1], f[..., 2]
    mx = f.max(-1); mn = f.min(-1); sat = mx - mn
    bg = f[int(640 * S):int(700 * S), int(150 * S):int(250 * S)].mean()
    board = np.zeros_like(sat, bool); board[int(180 * S):int(620 * S), int(40 * S):int(353 * S)] = True
    dots = board & (sat > 60) & (mx > 150)
    hue = np.degrees(np.arctan2(np.sqrt(3) * (G - B), 2 * R - G - B)) % 360
    blue = (B > 200) & (R < 80) & (G > 90) & (G < 190); blue[:int(150 * S)] = False; blue[int(770 * S):] = False
    purp = (R > 120) & (B > 180) & (G < 80)
    wh = (mn > 225) & (bg < 200)
    whx = np.where(wh[int(200 * S):int(500 * S)].any(0))[0]
    panel = ((B > 200) & (R < 60) & (G > 80) & (G < 130))[int(300 * S):int(600 * S)].sum()
    conf = ((sat > 100) & (bg < 120))[int(450 * S):int(760 * S)].sum()
    out.append(f'{t[k]:.3f}  {bg:6.1f}  {dots.sum():5d}  {hue[dots].mean() if dots.sum() else float("nan"):6.1f}  {blue.sum():5d}  {purp.sum():5d}  {wh.sum():5d} {(whx.min()/S if len(whx) else float("nan")):6.1f}-{(whx.max()/S if len(whx) else float("nan")):6.1f}  {panel:5d}  {conf:5d}')
open(os.path.join(mf.SP, 'out', 'winscan_v552.txt'), 'w').write('\n'.join(out) + '\n')
print('\n'.join(out[::2]))
