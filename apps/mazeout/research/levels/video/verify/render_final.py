#!/usr/bin/env python3
"""Draw a level JSON over its own start frame (verifier's look sheet): red centre lines through the model's cells, a red head
triangle, a white tail dot; boxes yellow outline + counter, pipes magenta cells + black mouth dots with an out tick, ties green
outline, elevator platform orange outline; hidden-layer arrows drawn on the reveal frame (second panel).
usage: render_final.py LEVEL.json OUT.png [--frame F] [--scale S]"""
import json, sys, argparse
from PIL import Image, ImageDraw

PX = 592.0 / 393.0
D = {'up': (0, -1), 'down': (0, 1), 'left': (-1, 0), 'right': (1, 0)}


def draw(im, d, arrows, p, ox, oy, obst=True):
    dr = ImageDraw.Draw(im)
    C = lambda c: (ox + c[0] * p, oy + c[1] * p)
    if obst:
        for o in d['obstacles']:
            cs = o['cells']
            if not cs:
                continue
            xs = [c[0] for c in cs]; ys = [c[1] for c in cs]
            x0, y0 = C((min(xs), min(ys))); x1, y1 = C((max(xs), max(ys)))
            box = [x0 - p / 2, y0 - p / 2, x1 + p / 2, y1 + p / 2]
            if o['kind'] in ('box', 'curtain'):
                dr.rectangle(box, outline=(255, 200, 0), width=3)
                dr.text((box[0] + 3, box[1] + 2), str(o.get('counter')), fill=(255, 0, 0))
            elif o['kind'] == 'tape_pink':
                dr.rectangle(box, outline=(0, 200, 0), width=2)
            elif o['kind'] == 'elevator':
                dr.rectangle(box, outline=(255, 120, 0), width=2)
        for pp in d.get('pipes', []):
            for c in pp['cells']:
                x, y = C(c)
                dr.rectangle([x - p / 4, y - p / 4, x + p / 4, y + p / 4], outline=(230, 0, 230), width=2)
            for e in pp.get('ends', []):
                x, y = C(e['cell'])
                dx, dy = D[e['out']]
                dr.ellipse([x - 4, y - 4, x + 4, y + 4], fill=(0, 0, 0))
                dr.line([(x, y), (x + dx * p * 0.6, y + dy * p * 0.6)], fill=(0, 0, 0), width=3)
    for a in arrows:
        pts = [C(c) for c in a['cells']]
        dr.line(pts, fill=(255, 0, 0), width=2)
        x, y = pts[-1]
        dx, dy = D[a['dir']]
        tip = (x + dx * 0.42 * p, y + dy * 0.42 * p)
        dr.polygon([tip, (x - dy * 0.22 * p, y + dx * 0.22 * p), (x + dy * 0.22 * p, y - dx * 0.22 * p)], outline=(255, 0, 0))
        tx, ty = pts[0]
        dr.ellipse([tx - 2.5, ty - 2.5, tx + 2.5, ty + 2.5], fill=(255, 255, 255), outline=(255, 0, 0))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('json')
    ap.add_argument('out')
    ap.add_argument('--frame')
    ap.add_argument('--root', default='.')
    a = ap.parse_args()
    d = json.load(open(a.json))
    frame = a.frame or d.get('frame') or d.get('shot')
    import os
    fp = frame if os.path.isabs(frame) else os.path.join(a.root, frame.replace('research/', '', 1))
    im = Image.open(fp).convert('RGB')
    p = d['pitch_pt'] * PX
    ox, oy = d['origin_pt'][0] * PX, d['origin_pt'][1] * PX
    start = [x for x in d['arrows'] if x.get('layer', 1) == 1]
    draw(im, d, start, p, ox, oy)
    y0 = int(max(0, oy - p)); y1 = int(min(im.height, oy + d['rows'] * p))
    panels = [im.crop((0, y0, im.width, y1))]
    for k, e in enumerate(d.get('elevators') or []):
        rf = e.get('reveal_frame')
        if not rf:
            continue
        rim = Image.open(os.path.join(a.root, rf.replace('research/', '', 1))).convert('RGB')
        hid = [x for x in d['arrows'] if x.get('under_elevator') == k]
        draw(rim, d, hid, p, ox, oy, obst=False)
        panels.append(rim.crop((0, y0, rim.width, y1)))
    W = sum(pn.width for pn in panels) + 10 * (len(panels) - 1)
    out = Image.new('RGB', (W, panels[0].height), 'white')
    x = 0
    for pn in panels:
        out.paste(pn, (x, 0)); x += pn.width + 10
    out.save(a.out)


if __name__ == '__main__':
    main()
