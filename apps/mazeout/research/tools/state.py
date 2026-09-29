#!/usr/bin/env python3
"""state.py SHOT.png → prints one word: home | level | paused | win | popup (unknown overlay) — pixel heuristics."""
import sys
import numpy as np
from PIL import Image
a = np.array(Image.open(sys.argv[1]).convert('RGB')).astype(int)
S = 1178 / 393
def patch(x0, y0, x1, y1): return a[int(y0 * S):int(y1 * S), int(x0 * S):int(x1 * S)].reshape(-1, 3)
p = patch(120, 645, 270, 690); play = ((p[:, 1] > 180) & (p[:, 0] < 150) & (p[:, 2] < 120)).mean()
q = patch(340, 76, 364, 100); pause_blue = ((q[:, 2] > 110) & (q[:, 2] > q[:, 0] + 60)).mean()
g = patch(80, 515, 165, 545); resume = ((g[:, 1] > 150) & (g[:, 0] < 120) & (g[:, 2] < 120)).mean()
t = patch(120, 215, 270, 245); orange = ((t[:, 0] > 200) & (t[:, 1] > 120) & (t[:, 2] < 90)).mean()
c = patch(110, 515, 280, 560); cont = ((c[:, 1] > 180) & (c[:, 0] < 150) & (c[:, 2] < 120)).mean()
h = patch(100, 250, 290, 300); perfect = ((h[:, 0] > 220) & (h[:, 1] > 220) & (h[:, 2] > 200)).mean()
if play > 0.4 and pause_blue < 0.25:
    print('home')
elif pause_blue > 0.25:
    print('level')
elif resume > 0.3 and orange > 0.05:
    print('paused')
elif cont > 0.3:
    print('win' if perfect > 0.05 else 'popup-green')
else:
    print('popup')
