#!/usr/bin/env python3
"""to-A lane: fxFrostVignette IN ITS SCREEN. The frost is drawn between the board and the HUD, so pasting it over 065
(which already shows the frost) doubles it. Instead: 058 (the same L62 board at the start, no frost) +
ours, with the HUD put back on top where 065 shows the HUD unfrosted (coloured pixels in the HUD bands where 065 ~= 058).

    ~/.venvs/mf3d/bin/python art/review/tools/toA_frost_proof.py [candidate.png]
    -> art/ui/sheets/toA/t_fxFrostVignette_screen.png (065 | round 3 | round 4 at half size) and _corners.png (1x crops)
"""
import os
import sys

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
APP = os.path.normpath(os.path.join(HERE, "..", "..", ".."))
SH = os.path.join(APP, "research", "shots")
OUT = os.path.join(APP, "art", "ui", "sheets", "toA")


def compose(base, frost, hud):
    b = base.astype(np.float64) / 255
    f = np.asarray(Image.open(frost).convert("RGBA").resize((base.shape[1], base.shape[0]), Image.LANCZOS)).astype(np.float64) / 255
    a = f[..., 3:4]
    o = b * (1 - a) + f[..., :3] * a
    o = np.where(hud[..., None], b, o)
    return (np.clip(o, 0, 1) * 255).astype(np.uint8)


def main():
    cand = sys.argv[1] if len(sys.argv) > 1 else os.path.join(APP, "art", "ui", "out", "fxFrostVignette@3x.png")
    before = os.path.join(APP, "build", "ui-art", "lanes", "toA", "before", "fxFrostVignette@3x.png")
    c65 = np.asarray(Image.open(os.path.join(SH, "meta-065-L062-after-hourglass.png")).convert("RGB"))
    c64 = np.asarray(Image.open(os.path.join(SH, "meta-058-L062-start.png")).convert("RGB"))
    k = c65.shape[1] / 393
    diff = np.abs(c65.astype(int) - c64.astype(int)).sum(2)
    Y = np.arange(c65.shape[0])[:, None] / k
    X = np.arange(c65.shape[1])[None, :] / k
    bands = (Y < 132) | (Y > 780)
    hud = bands & (diff < 40) & ~(c64.min(2) > 235)     # the HUD elements only (not the white page behind them)
    # grow the HUD mask a little (anti-aliased edges) but only inside the bands
    from scipy import ndimage
    hud = ndimage.binary_opening(hud, iterations=2)
    hud = ndimage.binary_dilation(hud, iterations=2) & bands & (diff < 90)
    r3 = compose(c64, before, hud)
    r4 = compose(c64, cand, hud)
    os.makedirs(OUT, exist_ok=True)
    tiles = [c65, r3, r4]
    h, w = c65.shape[:2]
    half = [Image.fromarray(t).resize((w // 2, h // 2), Image.LANCZOS) for t in tiles]
    sheet = Image.new("RGB", (3 * (w // 2) + 40, h // 2), (236, 236, 240))
    for i, t in enumerate(half):
        sheet.paste(t, (i * (w // 2 + 20), 0))
    p1 = os.path.join(OUT, "t_fxFrostVignette_screen.png")
    sheet.save(p1)
    # 1x (game size) crops: top-left corner, left edge middle, bottom-right corner
    boxes = [(0, 0, 130, 230), (0, 380, 90, 520), (263, 700, 393, 852)]
    rows = []
    for (x0, y0, x1, y1) in boxes:
        bx = [round(v * k) for v in (x0, y0, x1, y1)]
        row = [Image.fromarray(t).crop(bx) for t in tiles]
        rows.append(row)
    W = sum(r.width for r in rows[0]) + 40
    Hh = sum(r[0].height for r in rows) + 20 * len(rows)
    cs = Image.new("RGB", (max(W, 10), Hh), (236, 236, 240))
    yy = 0
    for row in rows:
        xx = 0
        for t in row:
            cs.paste(t, (xx, yy))
            xx += t.width + 20
        yy += row[0].height + 20
    p2 = os.path.join(OUT, "t_fxFrostVignette_corners.png")
    cs.save(p2)
    print(p1)
    print(p2)


if __name__ == "__main__":
    main()
