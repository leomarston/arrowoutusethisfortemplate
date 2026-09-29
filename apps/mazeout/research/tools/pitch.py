#!/usr/bin/env python3
"""pitch.py SHOT.png... -> grid pitch (pt) via the bot's comb fit on the ink mask (board band only)."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'bot'))
import bot, numpy as np
from PIL import Image
for f in sys.argv[1:]:
    im = np.array(Image.open(f).convert('RGB')).astype(np.int16)
    try:
        ink = bot.masks(im)[0] if isinstance(bot.masks(im), tuple) else bot.masks(im)
        fit = bot.fit_grid(ink)
        print(os.path.basename(f), 'pitch_px %.2f pitch_pt %.3f x0 %.1f y0 %.1f stroke %s resid %.2f' % (fit['pitch'], fit['pitch'] / bot.SCALE, fit['x0'], fit['y0'], fit.get('stroke'), fit.get('resid_px', -1)))
    except Exception as e:
        print(os.path.basename(f), 'ERR', e)
