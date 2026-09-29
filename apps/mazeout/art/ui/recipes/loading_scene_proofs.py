#!/usr/bin/env python3
"""Loading-scene lane: the FULL composed loading screen next to the two references at the same scale.

    PY=~/.venvs/mf3d/bin/python                       # from apps/mazeout
    $PY art/ui/recipes/loading_scene_proofs.py [--tag r4] [--backdrop path]

Ours = art/out/loadingBackdrop@3x.png + the characters (art/out/char_loading_layout.json, z back -> front) +
logoArrowOut at the shell's `loading.logo` rect (20, 66.7, 206.8 x 160.1 pt) + the "Loading..." label (PC Display
Black 26.8 pt, white, #82251F outline, baseline 792.7, centre x 187.2) -- what LoadingScreen.swift draws on the
393 x 852 reference phone. References (LOOKED AT only, never sampled into an asset):
  - research/kickoff/state.png: the owner's phone at first launch (1178 x 2556, under the iOS alert's dim);
  - research/store/iphone-8.png REGISTERED onto the phone frame: the phone's loading art is store 8 scaled by 0.8925
    (store pt -> phone pt) and shifted (-6.5, -0.5) pt (normalised cross-correlation 0.993 on the regions the alert
    does not cover; measured by this lane), so store 8 shows the parts the alert hides at the phone's exact scale.

Writes (gitignored) art/ui/sheets/loading_scene/:
  full_<tag>.png        [before |] ours | state.png | store 8 registered, game size (3 px per pt), + a 1/3 copy
  <crop>_<tag>.png      press (1.5x), conveyor (2x), top (1x), right (1x), floor (0.8x): [before |] ours | store 8
  backdrop_<tag>.png    the backdrop alone next to store 8 (1/3 size)
"""
from __future__ import annotations

import argparse
import json
import os

from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
APP = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
OUT = os.path.join(APP, "art", "out")
UIOUT = os.path.join(APP, "art", "ui", "out")
SHEETS = os.path.join(APP, "art", "ui", "sheets", "loading_scene")
FONT = os.path.join(APP, "App", "Resources", "Fonts", "PCDisplay-Black.ttf")
LABEL_FONT = "/System/Library/Fonts/Supplemental/Arial Bold.ttf"

S8_SCALE = 0.8925            # store 8 pt -> phone pt
S8_OFF_PT = (-6.5, -0.5)     # phone pt of store 8's origin


def store8_on_phone():
    s8 = Image.open(os.path.join(APP, "research", "store", "iphone-8.png")).convert("RGB")
    w, h = round(s8.width * S8_SCALE), round(s8.height * S8_SCALE)
    im = s8.resize((w, h), Image.LANCZOS)
    cv = Image.new("RGB", (1179, 2556), (0, 0, 0))
    cv.paste(im, (round(S8_OFF_PT[0] * 3), round(S8_OFF_PT[1] * 3)))
    return cv


def state_png():
    return Image.open(os.path.join(APP, "research", "kickoff", "state.png")).convert("RGB").resize((1179, 2556), Image.LANCZOS)


def label_layer():
    """'Loading...' as LoadingScreen draws it (white face, #82251F outline 0.88 pt + a 0.39 pt drop)."""
    lay = Image.new("RGBA", (1179, 2556), (0, 0, 0, 0))
    if not os.path.exists(FONT):
        return lay
    size = 26.8 * 3
    f = ImageFont.truetype(FONT, round(size))
    d = ImageDraw.Draw(lay)
    word = "Loading"
    w = d.textlength(word, font=f)
    left = 187.2 * 3 - w / 2
    base = 792.7 * 3
    asc = f.getmetrics()[0]
    xy = (left, base - asc)
    ow = round(0.88 * 3 * 2)
    d.text((xy[0], xy[1] + 0.39 * 3 * 2), word + "..", font=f, fill=(0x82, 0x25, 0x1F, 255), stroke_width=ow,
           stroke_fill=(0x82, 0x25, 0x1F, 255))
    d.text(xy, word + "..", font=f, fill=(255, 255, 255, 255), stroke_width=ow, stroke_fill=(0x82, 0x25, 0x1F, 255))
    return lay


def ours(backdrop=None, with_logo=True, with_label=True, with_cast=True):
    bd = Image.open(backdrop or os.path.join(OUT, "loadingBackdrop@3x.png")).convert("RGBA")
    cv = bd.copy()
    if with_cast:
        lay = json.load(open(os.path.join(OUT, "char_loading_layout.json")))["characters"]
        for name, c in sorted(lay.items(), key=lambda kv: kv[1]["z"]):
            im = Image.open(os.path.join(OUT, c["file"])).convert("RGBA")
            cv.alpha_composite(im, (round(c["x"] * 3), round(c["y"] * 3)))
    if with_logo:
        logo = Image.open(os.path.join(UIOUT, "logoArrowOut@3x.png")).convert("RGBA")
        logo = logo.resize((round(206.8 * 3), round(160.1 * 3)), Image.LANCZOS)
        cv.alpha_composite(logo, (round(20.0 * 3), round(66.7 * 3)))
    if with_label:
        cv.alpha_composite(label_layer())
    return cv.convert("RGB")


def _sheet(panels, titles, pad=24, top=60):
    w = sum(p.width for p in panels) + pad * (len(panels) + 1)
    h = max(p.height for p in panels) + top + pad
    out = Image.new("RGB", (w, h), (236, 236, 240))
    d = ImageDraw.Draw(out)
    f = ImageFont.truetype(LABEL_FONT, 30)
    x = pad
    for p, t in zip(panels, titles):
        out.paste(p, (x, top))
        d.text((x, 14), t, fill=(20, 20, 30), font=f)
        x += p.width + pad
    return out


def crop_pt(im, box, k=1.0):
    x0, y0, x1, y1 = (round(v * 3) for v in box)
    c = im.crop((x0, y0, x1, y1))
    if k != 1.0:
        c = c.resize((round(c.width * k), round(c.height * k)), Image.LANCZOS)
    return c


CROPS = {   # name: (box pt, zoom)
    "press": ((0, 140, 170, 440), 1.5),
    "conveyor": ((0, 400, 130, 600), 2.0),
    "top": ((0, 0, 393, 300), 1.0),
    "right": ((180, 150, 393, 520), 1.0),
    "floor": ((0, 560, 393, 852), 0.8),
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", default="now")
    ap.add_argument("--backdrop", default=None)
    ap.add_argument("--before", default=None, help="an older backdrop to show as a first column (e.g. round 3's)")
    a = ap.parse_args()
    os.makedirs(SHEETS, exist_ok=True)
    o = ours(a.backdrop)
    st = state_png()
    s8 = store8_on_phone()
    cols, names = [o, st, s8], ["ours (backdrop + cast + logo + label)", "state.png (phone, under the alert)",
                                "store 8 registered on the phone (x0.8925)"]
    if a.before:
        cols.insert(0, ours(a.before))
        names.insert(0, "before (" + os.path.basename(a.before) + ")")
    full = _sheet(cols, names)
    p = os.path.join(SHEETS, f"full_{a.tag}.png")
    full.save(p)
    full.resize((full.width // 3, full.height // 3), Image.LANCZOS).save(p.replace(".png", "_third.png"))
    for nm, (box, k) in CROPS.items():
        panels = [crop_pt(o, box, k), crop_pt(s8, box, k)]
        titles = ["ours", "store 8 (registered)"]
        if a.before:
            panels.insert(0, crop_pt(cols[0], box, k))
            titles.insert(0, "before")
        _sheet(panels, titles).save(os.path.join(SHEETS, f"{nm}_{a.tag}.png"))
    ob = ours(a.backdrop, with_logo=False, with_label=False, with_cast=False)
    bd = _sheet([ob.resize((393, 852), Image.LANCZOS), s8.resize((393, 852), Image.LANCZOS)], ["backdrop alone", "store 8"])
    bd.save(os.path.join(SHEETS, f"backdrop_{a.tag}.png"))
    print(p)


if __name__ == "__main__":
    main()
