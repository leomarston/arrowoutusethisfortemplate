#!/usr/bin/env python3
"""Family C side-by-sides (art spike): reference | 3D route | SVG route, at the reference's scale.

    ~/.venvs/mf3d/bin/python art/ui/tools/compare_c.py arrow      # -> art/ui/sheets/c_arrow.png
    ~/.venvs/mf3d/bin/python art/ui/tools/compare_c.py worker     # -> art/ui/sheets/c_worker.png

arrow: the three icon arrows composited on white at the icon's measured head sizes and tip positions (3D renders
from build/ui-art/route3d/arrowIcon*.png, SVG = art/ui/out/arrowIcon@3x.png or build/ui-art/svgroute/).
worker: our worker renders next to the reference workers at home-screen size (002: ~110 pt tall).
References are looked at only.
"""
from __future__ import annotations

import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
UI = os.path.dirname(HERE)
APP = os.path.dirname(os.path.dirname(UI))
B = os.path.join(APP, "build", "ui-art")
SHEETS = os.path.join(UI, "sheets")


def _font(size):
    return ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial Bold.ttf", size)


def _first(*paths):
    for p in paths:
        if os.path.exists(p):
            return p
    return None


def place_arrow(canvas, png, tip_x, cy, head_h, direction=1):
    """Scale a render so its head height (alpha bbox height) = head_h and put its tip at (tip_x, cy)."""
    im = Image.open(png).convert("RGBA")
    a = np.asarray(im.getchannel("A"))
    ys, xs = np.nonzero(a > 40)
    im = im.crop((xs.min(), ys.min(), xs.max() + 1, ys.max() + 1))
    s = head_h / im.height
    im = im.resize((round(im.width * s), round(im.height * s)), Image.LANCZOS)
    x = tip_x - im.width if direction > 0 else tip_x
    y = round(cy - im.height / 2)
    # soft drop shadow like the icon's (grey, below)
    sh = Image.new("RGBA", im.size, (58, 42, 32, 0))
    sh.putalpha(im.getchannel("A").filter(ImageFilter.GaussianBlur(9)).point(lambda v: int(v * 0.16)))
    canvas.alpha_composite(sh, (x, y + 12))
    canvas.alpha_composite(im, (x, y))


def arrow_sheet():
    ref = Image.open(os.path.join(APP, "research", "store", "icon-1024.png")).convert("RGBA")
    c3 = Image.new("RGBA", (1024, 1024), (254, 254, 254, 255))
    for name, tip, cy, hh, d in (("Yellow", 584, 262, 405, 1), ("Red", 510, 508.5, 408, -1), ("Blue", 584, 755.5, 422, 1)):
        p = os.path.join(B, "route3d", f"arrowIcon{name}.png")
        if os.path.exists(p):
            place_arrow(c3, p, tip, cy, hh, d)
    svg = _first(os.path.join(UI, "out", "arrowIcon@3x.png"), os.path.join(B, "svgroute", "arrowIcon.png"))
    cols = [("reference: store icon (looked at only)", ref), ("3D route (SDF -> USDZ -> mfrender)", c3)]
    if svg:
        cols.append(("SVG route (gradients + offset-stroke bevels)", Image.open(svg).convert("RGBA")))
    # row 1: whole icon at 512; row 2: the yellow head at 1:1
    t = 512
    W = 30 + len(cols) * (t + 30)
    out = Image.new("RGB", (W, 60 + t + 60 + 420 + 30), (236, 236, 240))
    d = ImageDraw.Draw(out)
    for i, (lab, im) in enumerate(cols):
        x = 30 + i * (t + 30)
        d.text((x, 20), lab, fill=(20, 20, 30), font=_font(18))
        out.paste(im.convert("RGB").resize((t, t), Image.LANCZOS), (x, 50))
        crop = im.convert("RGB").crop((200, 30, 700, 530)).resize((420, 420), Image.LANCZOS)
        out.paste(crop, (x + 46, 60 + t + 50))
    d.text((30, 60 + t + 18), "1:1 detail of the yellow head (icon px 200..700)", fill=(20, 20, 30), font=_font(18))
    os.makedirs(SHEETS, exist_ok=True)
    dst = os.path.join(SHEETS, "c_arrow.png")
    out.save(dst, optimize=True)
    return dst


def worker_sheet():
    refs = [("reference: home 002 left worker", os.path.join(APP, "art", "ref", "worker_left_home.png")),
            ("reference: home 002 right worker", os.path.join(APP, "art", "ref", "worker_right_home.png"))]
    ours = [("ours, 3D route", _first(os.path.join(B, "route3d", "workerHome.png"))),
            ("ours, SVG route", _first(os.path.join(UI, "out", "workerHome@3x.png"), os.path.join(B, "svgroute", "workerHome.png")))]
    ours = [(l, p) for l, p in ours if p]
    H = 390
    bg = (98, 132, 214)
    tiles = []
    for lab, p in refs:
        im = Image.open(p).convert("RGB")
        tiles.append((lab, im.resize((round(im.width * H / im.height), H), Image.LANCZOS)))
    for lab, p in ours:
        im = Image.open(p).convert("RGBA")
        a = np.asarray(im.getchannel("A")); ys, xs = np.nonzero(a > 20)
        im = im.crop((xs.min(), ys.min(), xs.max() + 1, ys.max() + 1))
        s = (H - 30) / im.height                          # our worker at the reference's on-screen height (~340 px)
        im = im.resize((round(im.width * s), round(im.height * s)), Image.LANCZOS)
        cv = Image.new("RGBA", (im.width + 40, H), bg + (255,))
        cv.alpha_composite(im, (20, H - im.height - 12))
        tiles.append((lab, cv.convert("RGB")))
    W = 30 + sum(t.width + 30 for _, t in tiles)
    out = Image.new("RGB", (W, H + 70 + H // 3 + 40), (236, 236, 240))
    d = ImageDraw.Draw(out)
    x = 30
    for lab, t in tiles:
        d.text((x, 20), lab, fill=(20, 20, 30), font=_font(16))
        out.paste(t, (x, 50))
        small = t.resize((t.width // 3, t.height // 3), Image.LANCZOS)   # the size a 1x screen would show
        out.paste(small, (x, 50 + H + 20))
        x += t.width + 30
    d.text((30, 50 + H + 2), "below: 1/3 size (a thumbnail-size read of the silhouette)", fill=(20, 20, 30), font=_font(14))
    dst = os.path.join(SHEETS, "c_worker.png")
    out.save(dst, optimize=True)
    return dst


if __name__ == "__main__":
    what = sys.argv[1:] or ["arrow", "worker"]
    for w in what:
        print({"arrow": arrow_sheet, "worker": worker_sheet}[w]())
