#!/usr/bin/env python3
"""In-place A/B for UI art routes: erase the element from an untinted runner shot, paste OUR render at the measured
position, and compare against the untouched shot (looked at only; nothing from it is shipped).

    ~/.venvs/mf3d/bin/python art/ui/tools/compare_swap.py pauseButton heartHUD buttonGreen
    ~/.venvs/mf3d/bin/python art/ui/tools/compare_swap.py --all

Per case it writes art/ui/sheets/ab_<case>.png: the reference crop, then each route's swapped crop at capture scale
(3 px/pt = the size on the phone), then the same at 4x (nearest), with silhouette IoU and mean CIEDE2000 inside the
element. Plus art/ui/sheets/ab_context_<shot>.png: the full shot next to each route's swapped shot (half size).

Routes (whichever exist): svg = art/ui/out/<case>@3x.png, swiftui = build/ui-art/swiftui/<case>.png,
3d = build/ui-art/route3d/<case>.png.
"""
from __future__ import annotations

import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
UI = os.path.dirname(HERE)
APP = os.path.dirname(os.path.dirname(UI))
SHOTS = os.path.join(APP, "research", "shots")
SHEETS = os.path.join(UI, "sheets")
ROUTES = [("svg", os.path.join(UI, "out", "{}@3x.png")),
          ("swiftui", os.path.join(APP, "build", "ui-art", "swiftui", "{}.png")),
          ("3d", os.path.join(APP, "build", "ui-art", "route3d", "{}.png"))]
# a case can be compared on routes whose file lives elsewhere (the SVG candidate of a 3D-won case, and vice versa)
ROUTE_ALIASES = {"svg": os.path.join(APP, "build", "ui-art", "svgroute", "{}.png")}


def m_blue(r):
    return (r[..., 2] > 150) & (r[..., 2] - r[..., 0] > 80)


def m_heart(r):
    return ((r[..., 0] - r[..., 2]) > 60) | (r.mean(2) < 110)


def m_green(r):
    return (r[..., 1] > r[..., 2] + 25) & (r[..., 1] > r[..., 0] + 25)


def m_pink(r):
    return (r[..., 0] > 150) & (r[..., 0] - r[..., 1] > 60) & (r[..., 2] > 60)


def erase_tape_tl(shot):
    """White out the L32 top-left tape and its shadow, then redraw the 4 arrow shafts that run under it
    (rows 0-3 of the measured lattice: y = 807.1 + 53.59 k, stroke 11.5 px)."""
    shot[785:992, 150:226] = 255
    for k in range(4):
        yc = 807.1 + 53.59 * k
        y0, y1 = yc - 5.75, yc + 5.75
        for y in range(int(y0), int(y1) + 2):
            cov = max(0.0, min(y + 1, y1) - max(y, y0))
            shot[y, 150:226] = (255 * (1 - cov)).astype(shot.dtype) if hasattr(cov, "astype") else int(255 * (1 - cov))


def m_red(r):
    return (r[..., 0] > r[..., 2] + 40) & (r[..., 0] > r[..., 1] + 40)


# case -> shot, element bbox (x0, y0, x1, y1) px, mask fn, where OUR frame's origin goes, erase = (box, colour or
# "mask:<hex>"), crop for the sheet
CASES = {
    "pauseButton": dict(shot="003-L32-start.png", bbox=(1002, 204, 1122, 324), mask=m_blue, origin=(996, 200),
                        erase=[((985, 190, 1140, 345), (255, 255, 255))], crop=(960, 170, 1170, 360)),
    "heartHUD": dict(shot="003-L32-start.png", bbox=(603, 245, 691, 321), mask=m_heart, origin=(600, 243),
                     erase=[("mask", (189, 220, 255), 4)], crop=(585, 225, 715, 340)),
    "buttonGreen": dict(shot="007-L32-pause.png", bbox=(181, 1457, 556, 1724), mask=m_green, origin=(178, 1454),
                        erase=[("mask", (17, 56, 177), 2)], crop=(150, 1430, 590, 1750), label="Resume"),
    "tapeV4": dict(shot="003-L32-start.png", bbox=(161, 794, 214, 980), mask=m_pink, origin=(158, 791),
                   erase=[("fn", erase_tape_tl)], crop=(120, 770, 330, 1000)),
    "buttonRed": dict(shot="007-L32-pause.png", bbox=(619, 1457, 994, 1724), mask=m_red, origin=(616, 1454),
                      erase=[("mask", (17, 56, 177), 2)], crop=(590, 1430, 1030, 1750), label="Quit"),
}


def _font(size):
    for f in ("/System/Library/Fonts/Supplemental/Arial Bold.ttf", "/System/Library/Fonts/Helvetica.ttc"):
        if os.path.exists(f):
            return ImageFont.truetype(f, size)
    return ImageFont.load_default()


def swap(case, ours_png):
    c = CASES[case]
    shot = np.asarray(Image.open(os.path.join(SHOTS, c["shot"])).convert("RGB")).copy()
    x0, y0, x1, y1 = c["bbox"]
    for e in c["erase"]:
        if e[0] == "fn":
            e[1](shot)
            continue
        if e[0] == "mask":
            from scipy import ndimage
            sub = shot[y0 - 6:y1 + 6, x0 - 6:x1 + 6]
            m = c["mask"](sub.astype(int))
            m = ndimage.binary_dilation(m, iterations=e[2])
            sub[m] = e[1]
        else:
            (a, b, cc, d), col = e
            shot[b:d, a:cc] = col
    im = Image.fromarray(shot).convert("RGBA")
    o = Image.open(ours_png).convert("RGBA")
    im.alpha_composite(o, c["origin"])
    if c.get("label"):  # the label is live text in the app: same placeholder font on every route (not judged here)
        f = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial Rounded Bold.ttf", 80)
        d = ImageDraw.Draw(im)
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2 - 6
        stroke = (6, 106, 1) if case == "buttonGreen" else (110, 10, 10)
        d.text((cx, cy + 5), c["label"], font=f, anchor="mm", fill=stroke, stroke_width=6, stroke_fill=stroke)
        d.text((cx, cy), c["label"], font=f, anchor="mm", fill=(255, 251, 234), stroke_width=6, stroke_fill=stroke)
    return im.convert("RGB")


def metrics(case, a_rgb, b_rgb):
    from skimage.color import deltaE_ciede2000, rgb2lab
    c = CASES[case]
    x0, y0, x1, y1 = c["bbox"]
    pad = 6
    A = np.asarray(a_rgb)[y0 - pad:y1 + pad, x0 - pad:x1 + pad].astype(int)
    B = np.asarray(b_rgb)[y0 - pad:y1 + pad, x0 - pad:x1 + pad].astype(int)
    ma, mb = c["mask"](A), c["mask"](B)
    iou = (ma & mb).sum() / max(1, (ma | mb).sum())
    both = ma & mb
    la, lb = rgb2lab(A[both][None] / 255.0), rgb2lab(B[both][None] / 255.0)
    de = deltaE_ciede2000(la, lb)[0]
    return iou, float(np.mean(de)), float(np.percentile(de, 90))


def sheet(case, label_font=None):
    c = CASES[case]
    ref = Image.open(os.path.join(SHOTS, c["shot"])).convert("RGB")
    cols = [("reference (runner shot, looked at only)", ref, None)]
    for name, pat in ROUTES:
        p = pat.format(case)
        if not os.path.exists(p) and name in ROUTE_ALIASES:
            p = ROUTE_ALIASES[name].format(case)
        if os.path.exists(p):
            sw = swap(case, p)
            cols.append((name, sw, metrics(case, ref, sw)))
    crop = c["crop"]
    tiles = []
    for name, im, met in cols:
        cr = im.crop(crop)
        z = cr.resize((cr.width * 3, cr.height * 3), Image.NEAREST)
        tiles.append((name, met, cr, z))
    f = _font(20)
    W1 = sum(t[2].width for t in tiles) + 30 * (len(tiles) + 1)
    W2 = sum(t[3].width for t in tiles) + 30 * (len(tiles) + 1)
    W = max(W1, W2)
    H = 70 + tiles[0][2].height + 50 + tiles[0][3].height + 30
    out = Image.new("RGB", (W, H), (236, 236, 240))
    d = ImageDraw.Draw(out)
    d.text((30, 10), f"{case}: game size (capture scale, 3 px/pt)  |  below: 3x zoom", fill=(20, 20, 30), font=f)
    x = 30
    for name, met, cr, z in tiles:
        lab = name if met is None else f"{name}: IoU {met[0]:.3f}  dE00 {met[1]:.1f} (p90 {met[2]:.1f})"
        d.text((x, 42), lab, fill=(20, 20, 30), font=_font(16))
        out.paste(cr, (x, 70))
        x += cr.width + 30
    x = 30
    y2 = 70 + tiles[0][2].height + 50
    for name, met, cr, z in tiles:
        out.paste(z, (x, y2))
        x += z.width + 30
    os.makedirs(SHEETS, exist_ok=True)
    dst = os.path.join(SHEETS, f"ab_{case}.png")
    out.save(dst, optimize=True)
    return dst, [(n, m) for n, _, m in cols if m]


def context(shot, cases):
    ref = Image.open(os.path.join(SHOTS, shot)).convert("RGB")
    cols = [("reference", ref)]
    for name, pat in ROUTES:
        im = ref
        ok = False
        for case in cases:
            p = pat.format(case)
            if not os.path.exists(p) and name in ROUTE_ALIASES:
                p = ROUTE_ALIASES[name].format(case)
            if os.path.exists(p):
                c = CASES[case]
                base = np.asarray(im).copy()
                tmp = swap(case, p)
                # swap() starts from the untouched shot; merge only this element's crop box
                a, b, cc, dd = c["crop"]
                base[b:dd, a:cc] = np.asarray(tmp)[b:dd, a:cc]
                im = Image.fromarray(base)
                ok = True
        if ok:
            cols.append((name, im))
    h = 1100
    tiles = [(n, im.crop((0, 0, 1178, 2556)).resize((round(1178 * h / 2556), h), Image.LANCZOS)) for n, im in cols]
    out = Image.new("RGB", (sum(t.width for _, t in tiles) + 30 * (len(tiles) + 1), h + 60), (236, 236, 240))
    d = ImageDraw.Draw(out)
    x = 30
    for n, t in tiles:
        d.text((x, 16), n, fill=(20, 20, 30), font=_font(22))
        out.paste(t, (x, 50))
        x += t.width + 30
    dst = os.path.join(SHEETS, f"ab_context_{os.path.splitext(shot)[0]}.png")
    out.save(dst, optimize=True)
    return dst


if __name__ == "__main__":
    names = sys.argv[1:]
    if not names or names == ["--all"]:
        names = list(CASES)
    for n in names:
        dst, met = sheet(n)
        print(dst, " ".join(f"{r}: IoU {m[0]:.3f} dE00 {m[1]:.2f}/{m[2]:.2f}" for r, m in met))
    shots = {}
    for n in names:
        shots.setdefault(CASES[n]["shot"], []).append(n)
    for s, cs in shots.items():
        print(context(s, cs))
