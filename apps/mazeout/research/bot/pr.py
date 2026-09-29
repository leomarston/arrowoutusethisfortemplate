#!/usr/bin/env python3
"""pr.py OUT.png [--fit] — probe helper: phone shot → OUT.png, a 393x852 look copy (scratchpad/look.png),
optional grid fit (pitch pt, origin pt, stroke pt) and a HUD crop (scratchpad/hud.png: timer + hearts, 2x)."""
import sys, os, subprocess, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bot
import numpy as np
from PIL import Image
SP = '/private/tmp/claude-501/-Users-yago-Downloads-app-factory/67834757-7bc9-4e4f-a907-36f39cf8e3e8/scratchpad'
out = sys.argv[1]
t0 = time.time()
im = bot.shot(out)
print('shot at', time.strftime('%H:%M:%S'), 'took %.2fs' % (time.time() - t0))
Image.open(out).resize((393, 852)).save(SP + '/look.png')
S = bot.SCALE
Image.open(out).crop((int(80 * S), int(60 * S), int(320 * S), int(115 * S))).resize((480, 110)).save(SP + '/hud.png')
if '--fit' in sys.argv:
    ink, col = bot.masks(im)
    f = bot.fit_grid(ink)
    print('pitch_pt %.3f x0_pt %.2f y0_pt %.2f stroke_pt %.2f resid_px %.2f' % (f['pitch'] / S, f['x0'] / S, f['y0'] / S, f['stroke'] / S, f['resid_px']))
    ys, xs = np.nonzero(ink)
    print('ink bbox pt x %.1f-%.1f y %.1f-%.1f' % (xs.min() / S, xs.max() / S, ys.min() / S, ys.max() / S))
