"""Overview contact sheet: ovs.py CLIP STEP [START END WIDTH COLS CROP(x,y,w,h pt)] -> ../motion-frames/ov_*.jpg
Picks the last REAL frame at or before each step time (media PTS)."""
import sys
from mf import *
name = sys.argv[1]; step = float(sys.argv[2])
s = float(sys.argv[3]) if len(sys.argv) > 3 else 0; e = float(sys.argv[4]) if len(sys.argv) > 4 else 999
width = int(sys.argv[5]) if len(sys.argv) > 5 else 131
cols = int(sys.argv[6]) if len(sys.argv) > 6 else 10
crop = [float(v) for v in sys.argv[7].split(',')] if len(sys.argv) > 7 else None
t, px = raw(name, 0, 999, width, crop=crop)
idx = []
if step <= 0:
    idx = [i for i in range(len(t)) if s <= t[i] <= e]
else:
    for x in np.arange(max(s, t[0]), min(e, t[-1]) + 1e-6, step):
        i = int(np.searchsorted(t, x + 1e-6) - 1); idx.append(max(i, 0))
os.makedirs(os.path.join(SP, '..', 'motion-frames'), exist_ok=True)
tag = '' if crop is None else '_c' + '-'.join(str(int(c)) for c in crop)
out = os.path.join(SP, '..', 'motion-frames', f'ov_{name[:-4]}_{s}-{e}_{step}{tag}.jpg')
sheet([Image.fromarray(px[i]) for i in idx], [f'{t[i]:.3f}' for i in idx], out, cols=cols)
print(out, len(idx))
