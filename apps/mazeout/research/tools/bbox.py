#!/usr/bin/env python3
"""bbox.py SHOT... -> bounding box (pt) of board content (non-white pixels) inside the board band y 125-745 pt, x 0-393."""
import sys, numpy as np
from PIL import Image
s = 1178 / 393
for f in sys.argv[1:]:
    a = np.array(Image.open(f).convert('RGB')).astype(int)
    band = a[int(125 * s):int(745 * s)]
    m = (band.min(2) < 200)
    # ignore booster buttons area (y > 745 excluded already) and HUD (y < 125 excluded)
    ys, xs = np.nonzero(m)
    print(f.split('/')[-1], 'content bbox pt x %.1f-%.1f y %.1f-%.1f' % (xs.min() / s, xs.max() / s, ys.min() / s + 125, ys.max() / s + 125), 'frac', round(m.mean(), 3))
