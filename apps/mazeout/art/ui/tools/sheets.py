#!/usr/bin/env python3
"""Side-by-side sheets: the reference crop (art/ref, research/shots or research/store, looked at only) next to our
art/ui/out/<case>@3x.png, both at capture scale (3 px per pt), our art on the reference's backdrop colour.

    python3 art/ui/tools/sheets.py boosterVacuum coin ...     # -> art/ui/sheets/<case>.png
    python3 art/ui/tools/sheets.py --all                      # every case in REFS that has an output
    python3 art/ui/tools/sheets.py --contact <name> cases...  # stack rows into art/ui/sheets/contact_<name>.png
    python3 art/ui/tools/sheets.py --draft boosterVacuum      # compare the draft render (build/ui-art/draft)
"""
from __future__ import annotations

import argparse
import os
import sys

from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
UI = os.path.dirname(HERE)
APP = os.path.dirname(os.path.dirname(UI))
OUT = os.path.join(UI, "out")
SHEETS = os.path.join(UI, "sheets")
DRAFT = os.path.join(APP, "build", "ui-art", "draft")
CROPS = os.path.join(APP, "art", "ref")
SHOTS = os.path.join(APP, "research", "shots")
WEB = os.path.join(APP, "research", "store")

# case -> (reference image, crop box in its pixels or None, backdrop RGB for our art, display pt size (w, h) or None)
# Display size = how big the game draws it (the capture's measured size), so the right column shows our art at the
# same on-screen size as the reference. Reference files are searched in art/ref, research/shots, research/store.
REFS = {
    "heartHUD": ("003-L32-start.png", (585, 225, 715, 340), (189, 220, 255), (31, 27)),
    "tapeV4": ("003-L32-start.png", (150, 785, 225, 990), (255, 255, 255), (20, 65)),
}

GROUPS = {
    "spike": ["heartHUD", "tapeV4"],
}
PT = 3  # px per pt


def ref_path(name):
    for d in (CROPS, SHOTS, WEB):
        p = os.path.join(d, name)
        if os.path.exists(p):
            return p
    return None


def _font(size):
    for f in ("/System/Library/Fonts/Supplemental/Arial Bold.ttf", "/System/Library/Fonts/Helvetica.ttc"):
        if os.path.exists(f):
            return ImageFont.truetype(f, size)
    return ImageFont.load_default()


def ours_path(case, draft=False):
    p = os.path.join(DRAFT, f"{case}.png") if draft else os.path.join(OUT, f"{case}@3x.png")
    return p if os.path.exists(p) else None


def sheet(case, draft=False, max_h=520, dest=None):
    if case not in REFS:
        ref, box, bg, disp = None, None, (60, 70, 90), None
    else:
        ref, box, bg, disp = REFS[case]
    ours = ours_path(case, draft)
    if not ours:
        return None
    o = Image.open(ours).convert("RGBA")
    if disp:  # show ours at its on-screen size (3 px/pt), aspect-fitted into the display frame
        fw, fh = disp[0] * PT, disp[1] * PT
        s = min(fw / o.width, fh / o.height)
        o = o.resize((max(1, round(o.width * s)), max(1, round(o.height * s))), Image.LANCZOS)
    tiles = []
    if ref and ref_path(ref):
        r = Image.open(ref_path(ref)).convert("RGB")
        if box:
            r = r.crop(box)
        tiles.append(("reference (looked at only)", r))
    ob = Image.new("RGB", (o.width + 40, o.height + 40), bg)
    ob.paste(o, (20, 20), o)
    tiles.append((f"ours: {case}@3x.png {Image.open(ours).size[0]}x{Image.open(ours).size[1]}", ob))
    # a checker version shows the alpha edge
    ck = Image.new("RGB", ob.size, (255, 255, 255))
    d = ImageDraw.Draw(ck)
    for y in range(0, ck.height, 16):
        for x in range(0, ck.width, 16):
            if (x // 16 + y // 16) % 2:
                d.rectangle([x, y, x + 15, y + 15], fill=(215, 215, 215))
    ck.paste(o, (20, 20), o)
    tiles.append(("alpha", ck))
    H = min(max_h, max(t.height for _, t in tiles))
    scaled = [(lab, t.resize((max(1, round(t.width * H / t.height)), H), Image.LANCZOS)) for lab, t in tiles]
    W = sum(t.width for _, t in scaled) + 20 * (len(scaled) + 1)
    out = Image.new("RGB", (W, H + 50), (238, 238, 240))
    dr = ImageDraw.Draw(out)
    x = 20
    f = _font(18)
    for lab, t in scaled:
        out.paste(t, (x, 40))
        dr.text((x, 12), lab, fill=(30, 30, 40), font=f)
        x += t.width + 20
    d = dest or SHEETS
    os.makedirs(d, exist_ok=True)
    dst = os.path.join(d, f"{case}{'_draft' if draft else ''}.png")
    out.save(dst, optimize=True)
    return dst


def contact(name, cases, draft=False, max_h=520):
    tmp = os.path.join(APP, "build", "ui-art", "sheetrows")
    rows = [Image.open(p) for p in (sheet(c, draft, max_h=max_h, dest=tmp) for c in cases) if p]
    if not rows:
        return None
    W = max(r.width for r in rows)
    H = sum(r.height for r in rows)
    out = Image.new("RGB", (W, H), (238, 238, 240))
    y = 0
    for r in rows:
        out.paste(r, (0, y)); y += r.height
    if draft:
        dst = os.path.join(DRAFT, f"contact_{name}.png")
        out.save(dst, optimize=True)
    else:  # the committed sheets are JPEG to keep the repo light
        os.makedirs(SHEETS, exist_ok=True)
        dst = os.path.join(SHEETS, f"{name}.jpg")
        out.save(dst, quality=84, optimize=True)
    return dst


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("cases", nargs="*")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--draft", action="store_true")
    ap.add_argument("--contact")
    ap.add_argument("--groups", action="store_true", help="write art/ui/sheets/<group>.png for every group")
    a = ap.parse_args()
    if a.groups:
        for g, cs in GROUPS.items():
            print(contact(g, cs, max_h=380 if g not in ("scenes", "home") else 700))
        raise SystemExit
    cases = a.cases
    if a.all:
        cases = sorted(f[:-7] for f in os.listdir(OUT) if f.endswith("@3x.png"))
    if a.contact:
        print(contact(a.contact, cases, a.draft))
    else:
        for c in cases:
            print(sheet(c, a.draft))
