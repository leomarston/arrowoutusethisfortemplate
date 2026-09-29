#!/usr/bin/env python3
"""Loading-scene lane: how close the BACKDROP is to the original, where the backdrop shows.

    PY=~/.venvs/mf3d/bin/python; $PY art/ui/recipes/loading_scene_metric.py [backdrop.png ...]

Composes each backdrop with our cast + logo (as LoadingScreen draws them) and measures mean / p90 CIEDE2000 against
store 8 registered on the phone frame (loading_scene_proofs.store8_on_phone) at 1/3 scale (1 px per pt), only on
pixels no character, no logo and no black registration border covers, per region. The cast differs by design (blue
workers, pink scientist), so it is masked out; this number is about the backdrop alone."""
from __future__ import annotations

import json
import os
import sys

import numpy as np
from PIL import Image
from skimage.color import deltaE_ciede2000, rgb2lab

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import loading_scene_proofs as P  # noqa: E402

REGIONS = {"all": (0, 0, 393, 852), "ceiling": (0, 0, 393, 150), "press": (0, 150, 150, 440),
           "opening": (150, 150, 393, 480), "conveyor": (0, 440, 90, 600), "floor": (0, 560, 393, 852)}


def cover_mask():
    lay = json.load(open(os.path.join(P.OUT, "char_loading_layout.json")))["characters"]
    cov = np.zeros((2556, 1179))
    for c in lay.values():
        a = np.asarray(Image.open(os.path.join(P.OUT, c["file"])).convert("RGBA"))[..., 3] / 255.0
        x, y = round(c["x"] * 3), round(c["y"] * 3)
        h, w = a.shape
        x0, y0, x1, y1 = max(0, x), max(0, y), min(1179, x + w), min(2556, y + h)
        cov[y0:y1, x0:x1] = np.maximum(cov[y0:y1, x0:x1], a[y0 - y:y1 - y, x0 - x:x1 - x])
    logo = Image.open(os.path.join(P.UIOUT, "logoArrowOut@3x.png")).convert("RGBA").resize((round(206.8 * 3), round(160.1 * 3)))
    a = np.asarray(logo)[..., 3] / 255.0
    x, y = round(20.0 * 3), round(66.7 * 3)
    cov[y:y + a.shape[0], x:x + a.shape[1]] = np.maximum(cov[y:y + a.shape[0], x:x + a.shape[1]], a)
    cov[:, 1150:] = 1.0                      # store 8 does not reach the phone's right edge after registration
    cov[2290:2440, 380:760] = 1.0            # the live "Loading" label
    from scipy import ndimage
    return ndimage.maximum_filter(cov, size=9) < 0.02


def main():
    paths = sys.argv[1:] or [os.path.join(P.OUT, "loadingBackdrop@3x.png")]
    vis = cover_mask()[1::3, 1::3]
    ref = np.asarray(P.store8_on_phone().resize((393, 852), Image.LANCZOS)).astype(np.float64) / 255
    lr = rgb2lab(ref)
    for p in paths:
        o = np.asarray(Image.open(p).convert("RGB").resize((393, 852), Image.LANCZOS)).astype(np.float64) / 255
        de = deltaE_ciede2000(rgb2lab(o), lr)
        row = []
        for nm, (x0, y0, x1, y1) in REGIONS.items():
            m = vis[y0:y1, x0:x1]
            d = de[y0:y1, x0:x1][m]
            row.append(f"{nm} {d.mean():5.2f}/{np.percentile(d, 90):5.2f} ({m.mean() * 100:3.0f}%)")
        print(os.path.basename(p) + ":  " + "  ".join(row))


if __name__ == "__main__":
    main()
