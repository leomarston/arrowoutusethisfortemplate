#!/usr/bin/env python3
"""batch C (levels 21-30). Obstacle timeline for one level: presence (break time) + counter readings (OCR when the badge crop changes).
  obst.py N [--fps 4] [--json J] [--t0 T] [--t1 T]  -> levelsC/V2-L0NN-obst.json + contact sheet of counter crops
"""
import json, os, sys, subprocess, re, shutil
import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage
MZ = '/Users/yago/Downloads/app-factory/apps/mazeout'
sys.path.insert(0, MZ + '/research/video-tools')
import vextract as vx
WORK = MZ + '/research/video-frames/work/levelsC'
SCR = os.path.join(WORK, 'tmp')
os.makedirs(SCR, exist_ok=True)

a = sys.argv[1:]
n = int(a[0])
def opt(k, d=None, cast=str):
    return cast(a[a.index(k) + 1]) if k in a else d
fps = opt('--fps', 4.0, float)
jp = opt('--json', os.path.join(WORK, 'V2-L%03d.json' % n))
js = json.load(open(jp))
L = vx.level_entry('V2', n)
t0 = opt('--t0', L['t_board'] - 0.05, float); t1 = opt('--t1', L['t_clear'] + 0.6, float)
times = list(np.arange(t0, t1, 1.0 / fps))
fdir = os.path.join(SCR, 'fr-L%03d' % n)
paths = vx.grab('V2', times, fdir, jpg=True)
fp = js['fit_px']; p = fp['pitch']
im0 = vx.load(os.path.join(MZ, js['frame']))

obs = []
for k, o in enumerate(js['obstacles']):
    if o['kind'] not in ('box', 'curtain', 'pipe'):
        continue
    raw = [(c[0] + fp['c0'], c[1] + fp['r0']) for c in o['cells']]
    # counter digits: white compact blobs inside the bbox on the start frame
    x0, y0, x1, y1 = o['bbox_px']
    sub = im0[y0:y1, x0:x1]
    wh = sub.min(2) > 225
    lab, nb = ndimage.label(wh)
    boxes = []
    for j, sl in enumerate(ndimage.find_objects(lab)):
        hh, ww = sl[0].stop - sl[0].start, sl[1].stop - sl[1].start
        if 0.15 * p <= hh <= 0.9 * p and ww <= 0.9 * p and (lab[sl] == j + 1).sum() >= 10:
            boxes.append((sl[1].start, sl[0].start, sl[1].stop, sl[0].stop))
    cb = None
    if boxes:
        boxes.sort(key=lambda b: -(b[3] - b[1]))
        ref = boxes[0]
        row = [b for b in boxes if abs((b[1] + b[3]) / 2 - (ref[1] + ref[3]) / 2) < 0.3 * p]
        bx0 = min(b[0] for b in row); by0 = min(b[1] for b in row); bx1 = max(b[2] for b in row); by1 = max(b[3] for b in row)
        m = int(0.3 * p) + 2
        cb = [x0 + bx0 - m, y0 + by0 - m, x0 + bx1 + m, y0 + by1 + m]
        cx = (cb[0] + cb[2]) // 2
        half = max(cb[2] - cb[0], int(1.4 * p)) // 2 + 2      # room for 2 digits
        cb = [cx - half, cb[1], cx + half, cb[3]]
    if '--cbox' in a:
        for i_ in [i for i, x in enumerate(a) if x == '--cbox']:
            if int(a[i_ + 1]) == k:
                cb = [int(v) for v in a[i_ + 2:i_ + 6]]
    obs.append(dict(k=k, kind=o['kind'], counter0=o.get('counter'), cells=raw, bbox=o['bbox_px'], counter_box=cb, series=[], readings=[]))

prev_crop = {}
for t, pth in zip(times, paths):
    im = vx.load(pth)
    pres = vx.obstacle_presence(im, js, [[(c[0] - fp['c0'], c[1] - fp['r0']) for c in ob['cells']] for ob in obs])
    for ob, v in zip(obs, pres):
        ob['series'].append(round(v, 2))
        if ob['counter_box'] is None or v < 0.3:
            continue
        x0, y0, x1, y1 = ob['counter_box']
        crop = im[y0:y1, x0:x1].astype(float)
        pc = prev_crop.get(ob['k'])
        if pc is None or np.abs(crop - pc).mean() > 5:
            val = vx.ocr_counter(pth, ob['counter_box'], pad=0)
            ob['readings'].append([round(float(t), 3), val])
            keep = os.path.join(SCR, 'cc-L%03d-o%d-%07d.png' % (n, ob['k'], int(t * 1000)))
            Image.open(pth).crop((x0, y0, x1, y1)).resize(((x1 - x0) * 2, (y1 - y0) * 2)).save(keep)
            ob.setdefault('crops', []).append(keep)
        prev_crop[ob['k']] = crop
for ob in obs:
    ser = ob['series']
    brk = next((i for i in range(len(ser)) if ser[i] < 0.3 and all(s < 0.3 for s in ser[i:i + 3])), None)
    ob['t_break'] = round(float(times[brk]), 3) if brk is not None else None
    ob['presence_first'] = ser[0]
    # collapse readings
    rd = []
    for t, v in ob['readings']:
        if not rd or rd[-1][1] != v:
            rd.append([t, v])
    ob['readings_collapsed'] = rd
out = dict(level=n, fps=fps, t0=t0, t1=t1, obstacles=[{k: v for k, v in ob.items() if k not in ('series', 'crops')} for ob in obs],
           series={ob['k']: ob['series'] for ob in obs}, times=[round(float(t), 3) for t in times])
json.dump(out, open(os.path.join(WORK, 'V2-L%03d-obst.json' % n), 'w'), indent=1)
# contact sheet of counter crops per obstacle
for ob in obs:
    cr = ob.get('crops', [])
    if not cr:
        continue
    ims = [Image.open(c) for c in cr]
    w = max(i.width for i in ims); h = max(i.height for i in ims) + 14
    cols = 12
    rows = (len(ims) + cols - 1) // cols
    sheet = Image.new('RGB', (cols * w, rows * h), (255, 255, 255))
    dr = ImageDraw.Draw(sheet)
    for i, (im_, (t, v)) in enumerate(zip(ims, ob['readings'])):
        x, y = (i % cols) * w, (i // cols) * h
        sheet.paste(im_, (x, y + 14))
        dr.text((x + 2, y + 1), '%.2f:%s' % (t, v), fill=(255, 0, 0))
    sheet.save(os.path.join(WORK, 'V2-L%03d-obst%d-counter-sheet.png' % (n, ob['k'])))
    for c in cr:
        os.remove(c)
shutil.rmtree(fdir)
for ob in obs:
    print(ob['kind'], 'k', ob['k'], 'counter0', ob['counter0'], 'break', ob['t_break'], 'presence0', ob['presence_first'])
    print('   readings', ob['readings_collapsed'])
