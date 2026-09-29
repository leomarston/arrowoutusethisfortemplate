# badges.py CLIP : activity intervals per home badge region (consecutive-frame diff > thr), + balloon badge top y
import sys; sys.path.insert(0, '/Users/yago/Downloads/app-factory/apps/mazeout/research/motion-tools')
from mf import raw
import numpy as np
clip = sys.argv[1]
t, px = raw(clip, 0, 999, 393)
px = px.astype(np.int16)
regs = {'streakFlags': (8, 185, 80, 70), 'rocket': (8, 290, 80, 75), 'skyDrum': (8, 390, 80, 75), 'balloonBadge': (305, 185, 85, 75),
        'clawToken': (30, 105, 50, 45), 'scientist': (130, 180, 140, 130), 'workerL': (25, 490, 110, 120), 'workerR': (255, 490, 110, 120), 'play': (100, 630, 195, 80)}
for name, (x, y, w, h) in regs.items():
    c = px[:, y:y+h, x:x+w]
    d = np.r_[0, np.abs(np.diff(c, axis=0)).mean(axis=(1, 2, 3))]
    act = d > float(sys.argv[2]) if len(sys.argv) > 2 else d > 1.0
    ivs = []; on = None
    for i in range(len(t)):
        if act[i] and on is None: on = i
        if not act[i] and on is not None:
            if t[i-1] - t[on] >= 0.05: ivs.append((t[on], t[i-1]))
            on = None
    if on is not None: ivs.append((t[on], t[-1]))
    # merge gaps < 0.15 s
    mg = []
    for a, b in ivs:
        if mg and a - mg[-1][1] < 0.15: mg[-1] = (mg[-1][0], b)
        else: mg.append((a, b))
    print(f'{name:12s} active {sum(b-a for a,b in mg):5.2f}s of {t[-1]-t[0]:.1f}: ' + ' '.join(f'{a:.2f}-{b:.2f}' for a, b in mg))
