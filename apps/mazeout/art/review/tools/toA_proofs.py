#!/usr/bin/env python3
"""Lane "to-A" (round 4) proofs: every id pasted IN ITS SCREEN at game size, round 3 (before) next to round 4 (after).

    ~/.venvs/mf3d/bin/python art/review/tools/toA_proofs.py iconStopwatchFrozen rankWings1 ...
    -> art/ui/sheets/toA/t_<id>.png  (gitignored)

Row 1, GAME SIZE (3 px per pt = the capture's scale): the capture around the element (ref box + a context margin) |
round 3 pasted in place | round 4 pasted in place. Row 2, ZOOM x3 of the ref box only (to NAME a difference already
seen at 1x): capture | round 3 | round 4. Placement = manifest_sheets' rule (entry anchor_pt -> ref anchor_pt, ref
scale / pitch). The entry comes from art/lanes/to-A.entries.json when it is there, else MANIFEST.json. The round-3 file
is build/ui-art/lanes/toA/before/<file name> (copied before the lane touched anything).
"""
from __future__ import annotations

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ART = os.path.normpath(os.path.join(HERE, "..", ".."))
APP = os.path.dirname(ART)
sys.path.insert(0, os.path.join(ART, "tools"))
import manifest as MF  # noqa: E402
from PIL import Image, ImageDraw, ImageFont  # noqa: E402

LANE = os.path.join(ART, "lanes", "to-A.entries.json")
BEFORE = os.path.join(APP, "build", "ui-art", "lanes", "toA", "before")
OUT = os.path.join(ART, "ui", "sheets", "toA")


def _font(size):
    for f in ("/System/Library/Fonts/Supplemental/Arial Bold.ttf", "/System/Library/Fonts/Helvetica.ttc"):
        if os.path.exists(f):
            return ImageFont.truetype(f, size)
    return ImageFont.load_default()


def entry(i):
    if os.path.exists(LANE):
        for e in json.load(open(LANE)).get("entries", []):
            if e["id"] == i:
                base = MF.by_id(MF.load())[i]
                base.update(e)
                return base
    return MF.by_id(MF.load())[i]


def crop_ref(e, pad_pt):
    return MF.ref_crop(e, pad_pt=pad_pt)[0]


def crop_origin(e, pad_pt):
    """The crop's real top-left in shot pt: ref_crop clamps at the shot's edge (a context margin past x 0 or y 0)."""
    r = e["ref"]
    _, k = MF.ref_image(r)
    bx0, by0, _, _ = MF.ref_box_pt(r)
    return max(0, round((bx0 - pad_pt) * k)) / k, max(0, round((by0 - pad_pt) * k)) / k


def placed(e, img_path, pad_pt, ref):
    r = e["ref"]
    o = Image.open(img_path).convert("RGBA")
    scale = (r["pitch_pt"] / e["pitch_pt"]) if (e.get("pitch_pt") and r.get("pitch_pt")) else r.get("scale", 1.0)
    og = o.resize((max(1, round(o.width * scale)), max(1, round(o.height * scale))), Image.LANCZOS)
    fw, fh = (e.get("size_pt") or [o.width / 3, o.height / 3])
    ax, ay = e.get("anchor_pt") or [fw / 2, fh / 2]
    bx0, by0, bx1, by1 = MF.ref_box_pt(r)
    rax, ray = r.get("anchor_pt") or [(bx0 + bx1) / 2, (by0 + by1) / 2]
    ox, oy = crop_origin(e, pad_pt)
    px = round((rax - ox) * 3 - ax * 3 * scale)
    py = round((ray - oy) * 3 - ay * 3 * scale)
    im = ref.convert("RGBA")
    layer = Image.new("RGBA", im.size, (0, 0, 0, 0))
    layer.paste(og, (px, py), og)
    im.alpha_composite(layer)
    return im.convert("RGB")


def proof(i, ctx_pt=None, zoom=3, after=None, before=None):
    e = entry(i)
    bx0, by0, bx1, by1 = MF.ref_box_pt(e["ref"])
    bw, bh = bx1 - bx0, by1 - by0
    ctx = ctx_pt if ctx_pt is not None else max(18.0, 0.6 * max(bw, bh))
    after = after or MF.app_path(e["file"])
    before = before or os.path.join(BEFORE, os.path.basename(e["file"]))
    big = crop_ref(e, ctx)
    small = crop_ref(e, 2)
    row1 = [("capture (game size)", big.convert("RGB")),
            ("round 3 in place", placed(e, before, ctx, big) if os.path.exists(before) else big.convert("RGB")),
            ("round 4 in place", placed(e, after, ctx, big))]
    zs = lambda im: im.resize((im.width * zoom, im.height * zoom), Image.LANCZOS)
    row2 = [("capture x%d" % zoom, zs(small.convert("RGB"))),
            ("round 3 x%d" % zoom, zs(placed(e, before, 2, small)) if os.path.exists(before) else zs(small)),
            ("round 4 x%d" % zoom, zs(placed(e, after, 2, small)))]
    f = _font(15)
    W = max(20 + sum(t.width + 16 for _, t in row1), 20 + sum(t.width + 16 for _, t in row2), 600)
    H = 40 + 24 + row1[0][1].height + 30 + row2[0][1].height + 20
    out = Image.new("RGB", (W, H), (236, 236, 240))
    d = ImageDraw.Draw(out)
    d.text((20, 10), f"{i}  frame {e.get('size_pt')} pt  ref {MF.ref_label(e['ref'])}  (to-A round 4)",
           fill=(20, 20, 30), font=_font(17))
    x, y = 20, 40
    for lab, t in row1:
        d.text((x, y), lab, fill=(40, 40, 50), font=f)
        out.paste(t, (x, y + 20))
        x += t.width + 16
    x, y = 20, 40 + 24 + row1[0][1].height + 10
    for lab, t in row2:
        d.text((x, y), lab, fill=(40, 40, 50), font=f)
        out.paste(t, (x, y + 20))
        x += t.width + 16
    os.makedirs(OUT, exist_ok=True)
    dst = os.path.join(OUT, f"t_{i}.png")
    out.save(dst)
    return dst


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("ids", nargs="+")
    ap.add_argument("--ctx", type=float, default=None, help="context margin in pt (default 0.6 x the ref box, >= 18)")
    ap.add_argument("--zoom", type=int, default=3)
    ap.add_argument("--after", default=None, help="compare this file instead of the entry's output (a candidate)")
    a = ap.parse_args()
    for i in a.ids:
        print(proof(i, a.ctx, a.zoom, a.after))
