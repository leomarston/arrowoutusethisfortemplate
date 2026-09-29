#!/usr/bin/env python3
"""vsheet — contact sheet of exact frames (via vgrab) for looking at a moment.
  python3 vsheet.py V START END STEP [--crop x y w h] [--width W] [--cols N] [--out PATH] [--marks t:x:y,...]
Crop in FULL-RES px. Marks draw a red ring at (x,y) on the frame nearest t (taps from the index)."""
import os, sys, subprocess, tempfile, shutil
from PIL import Image, ImageDraw
HERE = os.path.dirname(os.path.abspath(__file__))
a = sys.argv[1:]
def opt(n, k=1, d=None):
    if n in a:
        i = a.index(n); v = a[i + 1:i + 1 + k]; del a[i:i + 1 + k]; return v if k > 1 else v[0]
    return d
crop = opt('--crop', 4); width = int(opt('--width', 1, 220)); cols = int(opt('--cols', 1, 8)); out = opt('--out')
marks = opt('--marks')
V, s, e, st = a[0], float(a[1]), float(a[2]), float(a[3])
ts = []
t = s
while t <= e + 1e-6:
    ts.append(round(t, 3)); t += st
tmp = tempfile.mkdtemp()
subprocess.run([os.path.join(HERE, 'vgrab'), V, tmp, '--quiet'] + ['%.3f:f%03d' % (t, i) for i, t in enumerate(ts)], check=True)
mk = []
if marks:
    for m in marks.split(','):
        tt, x, y = m.split(':'); mk.append((float(tt), float(x), float(y)))
tiles = []
for i, t in enumerate(ts):
    im = Image.open(os.path.join(tmp, 'f%03d.png' % i)).convert('RGB')
    ox = oy = 0
    if crop:
        x, y, w, h = map(int, crop); im = im.crop((x, y, x + w, y + h)); ox, oy = x, y
    dr = ImageDraw.Draw(im)
    for (tt, x, y) in mk:
        if abs(tt - t) <= st / 2 + 1e-6:
            dr.ellipse([x - ox - 22, y - oy - 22, x - ox + 22, y - oy + 22], outline=(255, 0, 0), width=4)
    sc = width / im.width
    im = im.resize((width, int(im.height * sc)))
    ImageDraw.Draw(im).text((3, 3), '%.2f' % t, fill=(255, 0, 0))
    tiles.append(im)
shutil.rmtree(tmp)
h = max(t.height for t in tiles)
rows = (len(tiles) + cols - 1) // cols
S = Image.new('RGB', (cols * width, rows * h), 'white')
for i, im in enumerate(tiles):
    S.paste(im, ((i % cols) * width, (i // cols) * h))
out = out or os.path.join(HERE, '..', 'video-frames', 'probe', 'sheet_%s_%.2f-%.2f.png' % (V, s, e))
S.save(out); print(out, S.size)
