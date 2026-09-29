#!/usr/bin/env python3
"""sheet.py OUT.png W SHOT... -> side-by-side contact sheet, each shot resized to width W (keeps aspect)."""
import sys
from PIL import Image
out, w = sys.argv[1], int(sys.argv[2]); ims = [Image.open(f).convert('RGB') for f in sys.argv[3:]]
ims = [im.resize((w, int(im.height * w / im.width))) for im in ims]
c = Image.new('RGB', (w * len(ims), max(i.height for i in ims)), 'white')
for i, im in enumerate(ims): c.paste(im, (i * w, 0))
c.save(out)
