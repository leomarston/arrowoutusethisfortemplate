#!/usr/bin/env python3
"""Palette sampler: median sRGB of small boxes on the UNTINTED runner shots (003 HUD/board, 007 Paused panel above
its scrim, 002 home), plus k-means clusters for multi-tone parts. Writes art/ui/sheets/palette.png (swatch + the
sampled spot) and prints the table STYLE.md quotes.

    python3 art/tools/sample_palette.py
"""
import os

import numpy as np
from PIL import Image, ImageDraw, ImageFont

APP = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SHOTS = os.path.join(APP, "research", "shots")

# name -> (shot, x, y) in capture px (median of a 7 x 7 box)
SPOTS = [
    # board (003, 004)
    ("board.ground", "003", 600, 600), ("board.ink", "003", 120, 807), ("board.vacatedDot", "004", 80, 1611),
    # HUD (003)
    ("hud.coinPill.fill", "003", 305, 140), ("hud.coinPill.digits", "003", 230, 130), ("hud.coin.rim", "003", 66, 130),
    ("hud.coin.face", "003", 112, 146), ("hud.coin.star", "003", 97, 124),
    ("hud.squareButton.face", "003", 1080, 300), ("hud.squareButton.rimTop", "003", 1061, 207),
    ("hud.squareButton.lip", "003", 1061, 318), ("hud.squareButton.glyph", "003", 1045, 260),
    ("hud.panel.fill", "003", 760, 335), ("hud.panel.topEdge", "003", 760, 187), ("hud.panel.bottomEdge", "003", 760, 356),
    ("hud.timerPill.fill", "003", 540, 300), ("hud.timer.digits", "003", 480, 285), ("hud.stopwatch.ring", "003", 283, 285),
    ("hud.stopwatch.face", "003", 305, 305), ("hud.levelTab.fill", "003", 470, 196), ("hud.levelTab.edge", "003", 590, 226),
    ("hud.heart.face", "003", 660, 275), ("hud.heart.spec", "003", 630, 270),
    # booster bar (003)
    ("booster.tray.fill", "003", 20, 2380), ("booster.tray.edge", "003", 243, 2380), ("booster.well", "003", 42, 2330),
    ("booster.green.face", "003", 64, 2330), ("booster.green.rim", "003", 50, 2400), ("booster.badge.red", "003", 172, 2432),
    # Paused panel (007, drawn above the scrim: untinted)
    ("panel.frame.blue", "007", 70, 1300), ("panel.frame.inner", "007", 589, 1421), ("panel.rivet", "007", 70, 924),
    ("panel.ribbon.top", "007", 589, 640), ("panel.ribbon.bottom", "007", 589, 790), ("panel.cream.fill", "007", 589, 1152),
    ("panel.cream.border", "007", 160, 1152), ("panel.toggle.green", "007", 640, 1070), ("panel.toggle.knob", "007", 890, 1030),
    ("panel.close.red", "007", 1040, 770), ("panel.scrim.overWhite", "007", 589, 2048),
    # home (002)
    ("home.play.face", "002", 330, 2060), ("home.levelPlate.green", "002", 470, 1660), ("home.topPill.fill", "002", 590, 200),
    ("home.gearButton.face", "002", 1024, 173), ("home.nav.blue", "002", 55, 2364), ("home.nav.homeTab", "002", 436, 2364),
    ("home.floor", "002", 1018, 2182), ("home.wall.cream", "002", 55, 1182), ("home.wall.blueBand", "002", 91, 1509),
    ("home.machine.blue", "002", 345, 1273),
]
SHOT = {"003": "003-L32-start.png", "004": "004-L32-after-first.png", "007": "007-L32-pause.png", "002": "002-home-L32.png"}


def main():
    ims = {k: np.asarray(Image.open(os.path.join(SHOTS, v)).convert("RGB")) for k, v in SHOT.items()}
    rows = []
    for name, s, x, y in SPOTS:
        box = ims[s][y - 3:y + 4, x - 3:x + 4].reshape(-1, 3)
        med = np.median(box, 0).astype(int)
        spread = int(np.abs(box.astype(int) - med).max())
        hx = "#%02X%02X%02X" % tuple(med)
        rows.append((name, s, x, y, hx, spread))
        print(f"| {name:28s} | {s} ({x}, {y}) | `{hx}` | {'flat' if spread < 12 else f'gradient +-{spread}'} |")
    # swatch sheet
    f = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial.ttf", 16)
    W, rh = 900, 44
    out = Image.new("RGB", (W, rh * len(rows) + 20), (240, 240, 244))
    d = ImageDraw.Draw(out)
    for i, (name, s, x, y, hx, sp) in enumerate(rows):
        yy = 10 + i * rh
        crop = Image.fromarray(ims[s]).crop((x - 20, y - 20, x + 21, y + 21)).resize((40, 40), Image.NEAREST)
        out.paste(crop, (10, yy))
        d.rectangle([14 + 18, yy + 18, 14 + 22, yy + 22], outline=(255, 0, 255))
        d.rectangle([60, yy, 100, yy + 40], fill=hx)
        d.text((115, yy + 12), f"{name}  {hx}  ({s} @ {x},{y})  {'flat' if sp < 12 else f'+-{sp}'}", fill=(20, 20, 30), font=f)
    dst = os.path.join(APP, "art", "ui", "sheets", "palette.png")
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    out.save(dst)
    print(dst)


if __name__ == "__main__":
    main()
