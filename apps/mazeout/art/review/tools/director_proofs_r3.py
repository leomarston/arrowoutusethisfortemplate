#!/usr/bin/env python3
"""Art director round 3: the proof sheets of the director's own fixes, at game size (3 px per pt) and 2x, written to
art/ui/sheets/director3/ (gitignored). References are LOOKED AT only (never sampled into an asset).

    PY=~/.venvs/mf3d/bin/python; cd apps/mazeout
    $PY art/review/tools/director_proofs_r3.py            # heart_088, skulls, logo_049, planets_163, shop_bundles
The lanes' own proofs: art/ui/sheets/m_<id>.png (manifest_sheets.py), m3d_<id>.png (art/ui/recipes/m3d_proofs.py),
polish/ (polish_proofs.py), characters/ (art/pipeline/items/char_proofs.py).
"""
import os
import sys

from PIL import Image, ImageDraw

APP = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
sys.path.insert(0, os.path.join(APP, "art", "tools"))
import manifest as MF  # noqa: E402

OUT = os.path.join(APP, "art", "ui", "sheets", "director3")
UI = os.path.join(APP, "art", "ui", "out")


def shot(name):
    return Image.open(os.path.join(APP, "research", "shots", name)).convert("RGBA")


def crop(im, x0, y0, x1, y1, z=1.0):
    k = im.width / 393.0          # phone shots: 393 pt wide
    c = im.crop((round(x0 * k), round(y0 * k), round(x1 * k), round(y1 * k)))
    return c.resize((round((x1 - x0) * 3 * z), round((y1 - y0) * 3 * z)), Image.LANCZOS)


def in_place(base, art, fx, fy, fw, fh):
    k = base.width / 393.0
    b = base.copy()
    a = Image.open(art).convert("RGBA").resize((round(fw * k), round(fh * k)), Image.LANCZOS)
    b.alpha_composite(a, (round(fx * k), round(fy * k)))
    return b


def on(bg, art, z=1.0):
    a = Image.open(art).convert("RGBA")
    b = Image.new("RGBA", a.size, bg + (255,))
    b.alpha_composite(a)
    return b.resize((round(a.width * z), round(a.height * z)), Image.LANCZOS)


def sheet(name, rows, title):
    """rows: list of lists of (label, image)."""
    W = max(sum(t.width + 12 for _, t in r) + 12 for r in rows)
    H = 34 + sum(max(t.height for _, t in r) + 26 for r in rows)
    out = Image.new("RGB", (W, H), (236, 236, 240))
    d = ImageDraw.Draw(out)
    d.text((12, 8), title, fill=(20, 20, 30))
    y = 34
    for r in rows:
        x = 12
        for lab, t in r:
            d.text((x, y), lab, fill=(40, 40, 50))
            out.paste(t.convert("RGB"), (x, y + 16))
            x += t.width + 12
        y += max(t.height for _, t in r) + 26
    os.makedirs(OUT, exist_ok=True)
    p = os.path.join(OUT, name)
    out.save(p, optimize=True)
    print(p)


def heart():
    s = shot("meta-088-L062-hearts-out-1.png")
    box = (90, 300, 305, 492)
    ip = in_place(s, os.path.join(UI, "heartBig@3x.png"), 99.5, 316, 194, 164)
    sheet("heart_088.png", [[("088 (looked at only)", crop(s, *box)), ("heartBig in place", crop(ip, *box))],
                            [("088 2x", crop(s, *box, z=2)), ("ours 2x", crop(ip, *box, z=2))]],
          "heartBig at game size (frame 194 x 164 at (99.5, 316) on meta-088)")


def skulls():
    s1, s2 = shot("037-L34-win.png"), shot("063-L039-end-popup.png")
    rows = [[("037", crop(s1, 101, 117.5, 131, 149.5)), ("iconSkull", on((200, 10, 20), os.path.join(UI, "iconSkull@3x.png"))),
             ("063", crop(s2, 95.5, 114, 133.5, 152)), ("iconSkullBones", on((110, 20, 210), os.path.join(UI, "iconSkullBones@3x.png")))],
            [("037 6x", crop(s1, 101, 117.5, 131, 149.5, z=2)), ("ours 6x", on((200, 10, 20), os.path.join(UI, "iconSkull@3x.png"), 2)),
             ("063 6x", crop(s2, 95.5, 114, 133.5, 152, z=2)),
             ("ours 6x", on((110, 20, 210), os.path.join(UI, "iconSkullBones@3x.png"), 2))]]
    sheet("skulls.png", rows, "win-tag skulls at game size (row 1) and 2x")


def logo():
    s = shot("049-L036-end.png")
    ours = on((30, 30, 34), os.path.join(UI, "logoArrowOut@3x.png"))
    ref = crop(s, 44, 292, 350, 528).resize(ours.size, Image.LANCZOS)
    sheet("logo_049.png", [[("049 (the original's logo, looked at only)", ref), ("logoArrowOut", ours)]],
          "logo at 1:1 (306 x 236 pt frame)")


def planets():
    s = shot("163-rocket-race-offer.png")
    rows = []
    for i, (fx, fy, fw, fh) in enumerate([(62, 427, 60, 60), (165, 427, 60, 60), (247, 427, 104, 60)], 1):
        box = (fx - 6, fy - 6, fx + fw + 6, fy + fh + 6)
        ip = in_place(s, os.path.join(UI, f"planetStage{i}@3x.png"), fx, fy, fw, fh)
        rows.append([(f"163 stage {i}", crop(s, *box, z=2)), ("ours in place", crop(ip, *box, z=2))])
    sheet("planets_163.png", rows, "stage planets on 163 at 2x (frames from art/lanes/missing-3d.md)")


def shop():
    rows = []
    for i in ("bundleSpecial", "bundleBag", "bundleBarrel", "bundleChest", "bundleSafe", "bundleCart"):
        p = os.path.join(APP, "art", "ui", "sheets", f"m3d_{i}.png")
        if os.path.exists(p):
            im = Image.open(p)
            rows.append([(i + " (m3d_proofs: ref | ours | in place, game size)", im.crop((0, 0, im.width, round(im.height * 0.33))))])
    if rows:
        sheet("shop_bundles.png", rows, "shop bundle art (run art/ui/recipes/m3d_proofs.py first)")


if __name__ == "__main__":
    heart(); skulls(); logo(); planets(); shop()
