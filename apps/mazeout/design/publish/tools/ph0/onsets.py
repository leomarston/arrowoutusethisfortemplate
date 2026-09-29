# onsets.py CLIP S E "x,y;x,y" [half] : first frame where a crop around each point changes vs the frame at S
import sys; sys.path.insert(0, '/Users/yago/Downloads/app-factory/apps/mazeout/research/motion-tools')
from mf import raw
import numpy as np
clip = sys.argv[1]; s = float(sys.argv[2]); e = float(sys.argv[3])
pts = [tuple(map(float, p.split(','))) for p in sys.argv[4].split(';')]
h = int(sys.argv[5]) if len(sys.argv) > 5 else 8
t, px = raw(clip, s, e, 393)
m = (t >= s) & (t <= e); t = t[m]; px = px[m].astype(int)
for (x, y) in pts:
    x, y = int(x), int(y)
    c = px[:, y-h:y+h, x-h:x+h]
    d = np.abs(c - c[0]).mean(axis=(1, 2, 3))
    dp = np.r_[0, np.abs(np.diff(c, axis=0)).mean(axis=(1, 2, 3))]
    on = np.where(d > 12)[0]
    print(f'({x},{y}) first change > 12 at', f'{t[on[0]]:.3f}' if len(on) else 'never', '| series (t:dprev>6):', ' '.join(f'{t[i]:.3f}:{dp[i]:.0f}' for i in range(len(t)) if dp[i] > 6)[:900])
