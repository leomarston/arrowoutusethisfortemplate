#!/usr/bin/env python3
"""render_levels.py — contact sheets of bundle-schema levels (a LOOK tool for design review; not an overlay proof).

  python3 design/tools/render_levels.py design/levels.json 62 63 64 ... --out design/tools/work/sheet.png
  python3 design/tools/render_levels.py design/tools/work/imported.json 32 39 --out ...

Black arrows with heads; hidden arrows (under doors / on elevator layer 2) are drawn faint; doors blue with their order
number, boxes purple with the counter, pipes cyan with the counter at `counter_at`, tapes pink, keys gold, the elevator
platform grey, corners teal.
"""
import json
import sys

from PIL import Image, ImageDraw, ImageFont

COL = dict(door=(95, 166, 242), box=(180, 83, 238), pipe=(120, 210, 250), tape=(215, 33, 105), key=(255, 190, 40),
           elevator=(170, 180, 195), corner=(40, 190, 190))


def draw_level(lvl, cell=14, title=None):
    W, H = lvl['cols'], lvl['rows']
    pad = 22
    im = Image.new('RGB', (W * cell + 2 * pad, H * cell + 2 * pad + 14), 'white')
    dr = ImageDraw.Draw(im)

    def xy(c):
        return (pad + c[0] * cell + cell / 2, pad + 14 + c[1] * cell + cell / 2)
    for o in lvl.get('obstacles', []):
        k = o['kind']
        if k in ('door', 'box', 'elevator'):
            for c in o['cells']:
                x, y = xy(c)
                dr.rectangle([x - cell / 2, y - cell / 2, x + cell / 2, y + cell / 2], fill=COL[k])
    for o in lvl.get('obstacles', []):
        if o['kind'] == 'pipe':
            pts = [xy(c) for c in o['cells']]
            dr.line(pts, fill=COL['pipe'], width=max(3, int(cell * 0.8)))
            for e in o['ends']:
                x, y = xy(e['cell'])
                dr.ellipse([x - 3, y - 3, x + 3, y + 3], fill=(240, 166, 6))
    for a in lvl['arrows']:
        pts = [xy(c) for c in a['cells']]
        hidden = a.get('hidden_by') is not None
        colr = (190, 190, 190) if hidden else (0, 0, 0)
        w = max(2, int(cell * 0.22))
        dr.line(pts, fill=colr, width=w)
        hx, hy = pts[-1]
        d = a['dir']
        s = cell * 0.36
        if d == 'right':
            tri = [(hx + s, hy), (hx - s * 0.5, hy - s * 0.85), (hx - s * 0.5, hy + s * 0.85)]
        elif d == 'left':
            tri = [(hx - s, hy), (hx + s * 0.5, hy - s * 0.85), (hx + s * 0.5, hy + s * 0.85)]
        elif d == 'up':
            tri = [(hx, hy - s), (hx - s * 0.85, hy + s * 0.5), (hx + s * 0.85, hy + s * 0.5)]
        else:
            tri = [(hx, hy + s), (hx - s * 0.85, hy - s * 0.5), (hx + s * 0.85, hy - s * 0.5)]
        dr.polygon(tri, fill=colr)
    for o in lvl.get('obstacles', []):
        k = o['kind']
        if k == 'tape':
            for c in o['cells']:
                x, y = xy(c)
                dr.rectangle([x - cell * 0.45, y - cell * 0.45, x + cell * 0.45, y + cell * 0.45], outline=COL['tape'],
                             width=3)
        if k == 'key':
            for c in o['cells'][:1]:
                x, y = xy(c)
                dr.ellipse([x - cell * 0.4, y - cell * 0.4, x + cell * 0.4, y + cell * 0.4], fill=COL['key'])
        if k in ('box', 'door'):
            cs = o['cells']
            x = sum(xy(c)[0] for c in cs) / len(cs)
            y = sum(xy(c)[1] for c in cs) / len(cs)
            label = str(o.get('counter')) if k == 'box' else 'D%d' % o.get('order', 0)
            dr.text((x - 6, y - 5), label, fill='white')
        if k == 'corner':                           # the plate (red) across the facing diagonal, the spring (teal) behind
            sx, sy = {'downRight': (1, -1), 'downLeft': (-1, -1), 'upRight': (1, 1), 'upLeft': (-1, 1)}[o['turn']]
            x, y = xy(o['cells'][0])
            dr.ellipse([x - sx * cell * 0.3 - 3, y - sy * cell * 0.3 - 3, x - sx * cell * 0.3 + 3, y - sy * cell * 0.3 + 3],
                       fill=COL['corner'])
            dr.line([(x + sy * cell * 0.5, y - sx * cell * 0.5), (x - sy * cell * 0.5, y + sx * cell * 0.5)],
                    fill=(230, 40, 40), width=max(2, int(cell * 0.25)))
        if k == 'pipe' and o.get('counter_at'):
            x, y = xy(o['counter_at'])
            dr.rectangle([x - 6, y - 6, x + 6, y + 6], fill=(205, 77, 0))
            dr.text((x - 3, y - 5), str(o.get('counter')), fill='white')
    t = title or 'L%d %s %s %dx%d t%d' % (lvl['level'], lvl.get('source', ''), lvl.get('tag', ''), W, H, lvl['timer_s'])
    dr.text((pad, 4), t, fill=(0, 0, 0))
    return im


def sheet(levels, cols=4, cell=12):
    ims = [draw_level(l, cell) for l in levels]
    w = max(i.width for i in ims)
    h = max(i.height for i in ims)
    rows = (len(ims) + cols - 1) // cols
    out = Image.new('RGB', (w * cols, h * rows), (235, 235, 235))
    for k, im in enumerate(ims):
        out.paste(im, ((k % cols) * w, (k // cols) * h))
    return out


def load_levels(path):
    d = json.load(open(path))
    if isinstance(d, list):
        return d
    return d['levels']


if __name__ == '__main__':
    args = sys.argv[1:]
    out = 'sheet.png'
    if '--out' in args:
        i = args.index('--out')
        out = args[i + 1]
        args = args[:i] + args[i + 2:]
    path, nums = args[0], [int(x) for x in args[1:]]
    lv = {l['level']: l for l in load_levels(path)}
    sel = [lv[n] for n in nums] if nums else list(lv.values())
    sheet(sel).save(out)
    print(out)
