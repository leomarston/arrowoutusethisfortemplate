#!/usr/bin/env python3
"""Side-by-side sheets for art/MANIFEST.json entries: OUR art next to its reference crop, at GAME size.

    ~/.venvs/mf3d/bin/python art/tools/manifest_sheets.py tapeV4 doorW4H8     # -> art/ui/sheets/m_<id>.png
    ~/.venvs/mf3d/bin/python art/tools/manifest_sheets.py --group board        # + art/ui/sheets/m_board.jpg (contact)
    ~/.venvs/mf3d/bin/python art/tools/manifest_sheets.py --all                # every entry with a ref + an output
    ~/.venvs/mf3d/bin/python art/tools/manifest_sheets.py --draft tapeV4       # compare build/ui-art/draft/<case>.png

Row 1 (game size, 3 px per pt, the capture's scale):
  [reference crop (looked at only)] [ours on the reference's backdrop colour, same framing] [ours IN PLACE: pasted
  over the capture at its anchor -- any size / position error shows as the original peeking out] [alpha checker]
Row 2: the same three at 2x for detail.
Game size: a board sprite (entry pitch_pt) is scaled by ref.pitch_pt / pitch_pt (the level's fit pitch); other
entries by ref.scale (default 1). Anchors: entry anchor_pt (inside our frame, default its centre) lands on
ref.anchor_pt (absolute pt in the shot, default the centre of ref.box_pt). swiftui / code entries use `preview`
(a rendered PNG, e.g. build/ui-art/swiftui/heartHUD.png) when they have one.
"""
from __future__ import annotations

import argparse
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import manifest as MF  # noqa: E402

import numpy as np  # noqa: E402
from PIL import Image, ImageDraw, ImageFont  # noqa: E402

APP, ART = MF.APP, MF.ART
SHEETS = os.path.join(ART, "ui", "sheets")
PAD_PT = 6


def _font(size):
    for f in ("/System/Library/Fonts/Supplemental/Arial Bold.ttf", "/System/Library/Fonts/Helvetica.ttc"):
        if os.path.exists(f):
            return ImageFont.truetype(f, size)
    return ImageFont.load_default()


def ours_path(e, draft=False):
    if e.get("rig") and e.get("file"):          # a cut-out rig: its proof composite, else the full render next to it
        d = MF.app_path(e["file"])
        rj = os.path.join(d, "rig.json")
        if os.path.isfile(rj):
            import json
            full = json.load(open(rj)).get("full") or ""
            cands = [os.path.normpath(os.path.join(d, full))] if full.endswith(".png") else \
                [os.path.join(os.path.dirname(d.rstrip("/")), f"{full}@3x.png"), os.path.join(d, f"{full}@3x.png")]
            for cand in cands:
                if full and os.path.isfile(cand):
                    return cand
    if draft:
        src = e.get("source") or ""
        case = src.rsplit(":", 1)[-1] if ":" in src else e["id"]
        p = os.path.join(APP, "build", "ui-art", "draft", f"{case}.png")
        return p if os.path.exists(p) else None
    for k in ("file", "preview"):
        if e.get(k) and os.path.isfile(MF.app_path(e[k])):
            return MF.app_path(e[k])
    return None


def checker(size, s=12):
    ck = Image.new("RGB", size, (255, 255, 255))
    d = ImageDraw.Draw(ck)
    for y in range(0, size[1], s):
        for x in range(0, size[0], s):
            if (x // s + y // s) % 2:
                d.rectangle([x, y, x + s - 1, y + s - 1], fill=(214, 214, 218))
    return ck


def sheet(e, draft=False, dest=None):
    ref, _ = MF.ref_crop(e, pad_pt=PAD_PT)
    op = ours_path(e, draft)
    if ref is None or op is None:
        return None
    r = e["ref"]
    o = Image.open(op).convert("RGBA")
    if draft and e.get("size_pt"):   # drafts are low-res: bring them to the frame size first
        o = o.resize((round(e["size_pt"][0] * 3), round(e["size_pt"][1] * 3)), Image.LANCZOS)
    scale = (r["pitch_pt"] / e["pitch_pt"]) if (e.get("pitch_pt") and r.get("pitch_pt")) else r.get("scale", 1.0)
    og = o.resize((max(1, round(o.width * scale)), max(1, round(o.height * scale))), Image.LANCZOS)
    fw, fh = (e.get("size_pt") or [o.width / 3, o.height / 3])
    ax, ay = e.get("anchor_pt") or [fw / 2, fh / 2]
    bx0, by0, bx1, by1 = MF.ref_box_pt(r)
    rax, ray = r.get("anchor_pt") or [(bx0 + bx1) / 2, (by0 + by1) / 2]
    # where our frame's top-left goes inside the crop (px at 3 px/pt)
    px = round((rax - (bx0 - PAD_PT)) * 3 - ax * 3 * scale)
    py = round((ray - (by0 - PAD_PT)) * 3 - ay * 3 * scale)
    arr = np.asarray(ref).reshape(-1, 3)
    edge = np.concatenate([np.asarray(ref)[0], np.asarray(ref)[-1], np.asarray(ref)[:, 0], np.asarray(ref)[:, -1]])
    bg = tuple(int(v) for v in np.median(edge, 0))
    solo = Image.new("RGBA", ref.size, bg + (255,))
    solo.alpha_composite(og, (px, py)) if (px >= 0 and py >= 0) else solo.paste(og, (px, py), og)
    inplace = ref.convert("RGBA")
    if px >= 0 and py >= 0:
        inplace.alpha_composite(og, (px, py))
    else:
        inplace.paste(og, (px, py), og)
    ck = checker(ref.size)
    ck.paste(og, (px, py), og)
    tiles = [("reference (looked at only)", ref.convert("RGB")), ("ours, game size", solo.convert("RGB")),
             ("ours in place over the capture", inplace.convert("RGB")), ("alpha", ck)]
    f = _font(15)
    z = 2
    W1 = 20 + sum(t.width + 16 for _, t in tiles)
    W2 = 20 + sum(t.width * z + 16 for _, t in tiles[:3])
    W = max(W1, W2, 700)
    H = 60 + ref.height + 40 + ref.height * z + 20
    out = Image.new("RGB", (W, H), (236, 236, 240))
    d = ImageDraw.Draw(out)
    sz = "x".join(str(v) for v in e.get("size_pt", [])) or "-"
    title = (f"{e['id']}  ({e['family']} / {e['route']}, frame {sz} pt, {os.path.relpath(op, APP)})   "
             f"game scale {scale:.3f}   ref {MF.ref_label(r)}")
    d.text((20, 8), title, fill=(20, 20, 30), font=_font(17))
    x = 20
    for lab, t in tiles:
        d.text((x, 36), lab, fill=(40, 40, 50), font=f)
        out.paste(t, (x, 56))
        x += t.width + 16
    x = 20
    y2 = 56 + ref.height + 30
    for lab, t in tiles[:3]:
        out.paste(t.resize((t.width * z, t.height * z), Image.LANCZOS), (x, y2))
        x += t.width * z + 16
    d = dest or SHEETS
    os.makedirs(d, exist_ok=True)
    dst = os.path.join(d, f"m_{e['id']}{'_draft' if draft else ''}.png")
    out.save(dst, optimize=True)
    return dst


def contact(name, paths, width=1400, max_h=9000):
    """Stack the sheets (each scaled to <= `width` px wide) into art/ui/sheets/m_<name>[_pN].jpg pages of <= max_h px."""
    Image.MAX_IMAGE_PIXELS = None
    rows = []
    for p in paths:
        if not p:
            continue
        r = Image.open(p).convert("RGB")
        if r.width > width:
            r = r.resize((width, max(1, round(r.height * width / r.width))), Image.LANCZOS)
        rows.append(r)
    if not rows:
        return None
    pages, cur, h = [], [], 0
    for r in rows:
        if cur and h + r.height > max_h:
            pages.append(cur); cur, h = [], 0
        cur.append(r); h += r.height
    pages.append(cur)
    outs = []
    for k, pg in enumerate(pages):
        out = Image.new("RGB", (max(r.width for r in pg), sum(r.height for r in pg)), (236, 236, 240))
        y = 0
        for r in pg:
            out.paste(r, (0, y)); y += r.height
        dst = os.path.join(SHEETS, f"m_{name}{'' if len(pages) == 1 else f'_p{k + 1}'}.jpg")
        out.save(dst, quality=85, optimize=True)
        outs.append(dst)
    return ", ".join(outs)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("ids", nargs="*")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--group")
    ap.add_argument("--draft", action="store_true")
    ap.add_argument("--manifest", help="another manifest file (tests)")
    a = ap.parse_args()
    if a.manifest:
        MF.use_manifest(a.manifest)
    m = MF.load()
    es = m["entries"]
    if a.group:
        es = [e for e in es if e.get("group") == a.group]
    elif not a.all:
        es = [e for e in es if e["id"] in set(a.ids)]
    made = []
    for e in es:
        p = sheet(e, a.draft)
        print(p or f"  (no sheet for {e['id']}: needs ref.shot + ref.box_pt and an output)")
        if p:
            made.append(p)
    if a.group and made:
        print(contact(a.group + ("_draft" if a.draft else ""), made))


if __name__ == "__main__":
    main()
