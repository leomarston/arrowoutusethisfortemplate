#!/usr/bin/env python3
"""missing-3d lane proofs: OUR render next to its reference at GAME size (3 px per pt, the capture's scale).

    PY=~/.venvs/mf3d/bin/python
    $PY art/ui/recipes/m3d_proofs.py bundleBag bundleSpecial [--draft]     # -> art/ui/sheets/m3d_<id>.png

Row 1 (1x): [reference crop] [ours on the reference's ground colour] [ours IN PLACE over the capture at its frame
origin -- any size / placement error shows as the original peeking out]. Row 2: the same at 2x. The captures are
LOOKED AT only (the sheet is gitignored).
"""
from __future__ import annotations

import argparse
import os
import sys

import numpy as np
from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
APP = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
SHEETS = os.path.join(APP, "art", "ui", "sheets")
DRAFT = os.path.join(APP, "build", "ui-art", "m3d", "draft")

# id -> (shot, frame origin (x, y) pt on the shot, output dir, ground colour for column 2)
REFS = {
    "bundleSpecial": ("research/shots/meta-012-shop-top.png", (16, 200), "ui", "#FDA504"),
    "bundleBag": ("research/shots/meta-012-shop-top.png", (16, 480.4), "ui", "#F8E6D6"),
    "bundleBarrel": ("research/shots/meta-008-shop-scroll1.png", (16, 150.8), "ui", "#F8E6D6"),
    "bundleChest": ("research/shots/meta-008-shop-scroll1.png", (16, 354.6), "ui", "#F8E6D6"),
    "bundleSafe": ("research/shots/meta-008-shop-scroll1.png", (16, 558.1), "ui", "#F8E6D6"),
    "bundleCart": ("research/shots/meta-010-shop-scroll3.png", (16, 156.1), "ui", "#F8E6D6"),
    "rocketOfferScene": ("research/shots/163-rocket-race-offer.png", (32, 188), "art", "#1B1A5C"),
    "skyJumpIslandFar2": ("research/shots/069-skyjump-screen.png", (213, 214), "art", "#8EC0F4"),
    "iconSkyDrum": ("research/shots/meta-002-avatar-tap.png", (28, 538.5), "ui", "#0A2176"),
    "planetStage1": ("research/shots/163-rocket-race-offer.png", (62, 427), "ui", "#008CFF"),
    "planetStage2": ("research/shots/163-rocket-race-offer.png", (165, 427), "ui", "#0A2C81"),
    "planetStage3": ("research/shots/163-rocket-race-offer.png", (247, 427), "ui", "#0A2C81"),
    "heartBig3d": ("research/shots/meta-088-L062-hearts-out-1.png", (94.5, 309), "route3d", "#1A0606"),
    "fxFrostVignette": ("research/shots/meta-065-L062-after-hourglass.png", (0, 0), "ui", "#FFFFFF"),
    "weeklyContestLogo": ("research/shots/meta-013-leaderboard-weekly.png", (60, 193.5), "ui", "#0B2A8A"),
}


def ours(i, draft):
    if draft:
        return os.path.join(DRAFT, f"{i}.png")

    d = REFS[i][2] if i in REFS else "ui"
    if d == "route3d":
        return os.path.join(APP, "build", "ui-art", "route3d", f"{i[:-2]}.png")
    return os.path.join(APP, "art", "ui" if d == "ui" else "", "out", f"{i}@3x.png").replace("//", "/")


def sheet(i, draft=False, pad=6):
    shot, (ox, oy), _, ground = REFS[i]
    ref = Image.open(os.path.join(APP, shot)).convert("RGB")
    k = ref.width / 393.0
    im = Image.open(ours(i, draft)).convert("RGBA")
    fw, fh = im.width / 3, im.height / 3
    x0, y0, x1, y1 = ox - pad, oy - pad, ox + fw + pad, oy + fh + pad
    box = tuple(int(round(v * k)) for v in (x0, y0, x1, y1))
    crop = ref.crop(box)
    W, H = crop.size
    ours_im = im.resize((int(round(fw * k)), int(round(fh * k))), Image.LANCZOS)
    col2 = Image.new("RGB", (W, H), ground)
    col2.paste(ours_im, (int(round(pad * k)), int(round(pad * k))), ours_im)
    col3 = crop.copy()
    col3.paste(ours_im, (int(round(pad * k)), int(round(pad * k))), ours_im)
    row1 = [crop, col2, col3]
    row2 = [crop.resize((W * 2, H * 2), Image.LANCZOS), col3.resize((W * 2, H * 2), Image.LANCZOS)]
    out = Image.new("RGB", (max(W * 3 + 40, W * 4 + 30), H * 3 + 60), (40, 40, 48))
    for j, c in enumerate(row1):
        out.paste(c, (10 + j * (W + 10), 10))
    for j, c in enumerate(row2):
        out.paste(c, (10 + j * (W * 2 + 10), H + 40))
    d = ImageDraw.Draw(out)
    d.text((10, H + 20), f"{i}  frame {fw:.0f}x{fh:.0f} pt at ({ox}, {oy})  | ref | ours | ours in place", fill=(255, 255, 255))
    os.makedirs(SHEETS, exist_ok=True)
    p = os.path.join(SHEETS, f"m3d_{i}.png")
    out.save(p)
    return p


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("ids", nargs="+")
    ap.add_argument("--draft", action="store_true")
    a = ap.parse_args()
    for i in a.ids:
        print(sheet(i, a.draft))


if __name__ == "__main__":
    main()
