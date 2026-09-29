#!/usr/bin/env python3
"""lbcrop.py SHOT OUT [y0 y1] — leaderboard list crop: rank+avatar+name (x 0-260 pt) and the score column (x 300-393 pt) side by side, 2x of pt."""
import sys
from PIL import Image
S = 1178 / 393
im = Image.open(sys.argv[1]); y0, y1 = (float(sys.argv[3]), float(sys.argv[4])) if len(sys.argv) > 4 else (190, 790)
a = im.crop((0, int(y0 * S), int(270 * S), int(y1 * S))); b = im.crop((int(300 * S), int(y0 * S), 1178, int(y1 * S)))
k = 1.2 / S
a = a.resize((int(a.width * k), int(a.height * k))); b = b.resize((int(b.width * k), int(b.height * k)))
W = Image.new('RGB', (a.width + b.width + 6, a.height), 'white'); W.paste(a, (0, 0)); W.paste(b, (a.width + 6, 0)); W.save(sys.argv[2])
