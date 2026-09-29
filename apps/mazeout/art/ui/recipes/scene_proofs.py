"""Composed proofs for the scene lane (our layers only, next to the reference at the same scale).

    $PY art/ui/recipes/scene_make.py proof home [--draft]    # -> art/ui/sheets/scene_home_proof.png

The home proof stacks, back to front: homeBackdrop, the scientist rig's torso + head (characters lane), homeConsole,
the scientist's arms, homePlatform, homeCapsuleMachine, homeArrowPileFull, the two workers (characters lane) -- every
layer at its frame / placement_pt. UI chrome (top bar, LEVEL plate, Play, nav) is NOT drawn: those are SwiftUI; the proof
shows only art. The right panel is research/shots/002 (looked at only) at the same scale.
"""
from __future__ import annotations

import json
import os

from PIL import Image, ImageDraw, ImageFont

import scene_kit as K

SHEETS = os.path.join(K.UI, "sheets")


def _layer(path_out, path_draft, draft):
    p = path_draft if (draft and os.path.exists(path_draft)) else path_out
    return Image.open(p).convert("RGBA") if os.path.exists(p) else None


def _rig_layers(name, which):
    d = os.path.join(K.OUT, f"char_{name}_rig")
    rj = json.load(open(os.path.join(d, "rig.json")))
    px, py = rj["placement_pt"]["x"], rj["placement_pt"]["y"]
    out = []
    for L in rj["layers"]:
        if L.get("overlay") or (L.get("group") and not L.get("default")):
            continue
        if which(L["name"]):
            x, y, w, h = L["rect_pt"]
            out.append((Image.open(os.path.join(d, L["file"])).convert("RGBA"), (round((px + x) * 3), round((py + y) * 3))))
    return out


def home_stack(draft=False, pile="homeArrowPileFull"):
    D = os.path.join(K.BUILD, "draft")

    def L(i):
        return _layer(os.path.join(K.OUT, f"{i}@3x.png"), os.path.join(D, f"{i}.png"), draft)
    import scene_home as H
    frames = {"homeBackdrop": H.F_BACKDROP, "homeConsole": H.F_CONSOLE, "homePlatform": H.F_PLATFORM,
              "homeCapsuleMachine": H.F_MACHINE, pile: H.F_PILE}
    cv = Image.new("RGBA", (1179, 2556), (0, 0, 0, 255))

    def put(i):
        im = L(i)
        if im is not None:
            f = frames[i]
            cv.alpha_composite(im, (f[0] * 3, f[1] * 3))
    put("homeBackdrop")
    for im, xy in _rig_layers("sci_home", lambda n: not n.startswith("arm")):
        cv.alpha_composite(im, xy)
    put("homeConsole")
    for im, xy in _rig_layers("sci_home", lambda n: n.startswith("arm")):
        cv.alpha_composite(im, xy)
    put("homePlatform")
    put("homeCapsuleMachine")
    put(pile)
    for w in ("wk_homeL_blue", "wk_homeR_blue"):
        for im, xy in _rig_layers(w, lambda n: True):
            cv.alpha_composite(im, xy)
    return cv


def proof_home(draft=False):
    ours = home_stack(draft)
    ref = Image.open(os.path.join(K.APP, "research", "shots", "002-home-L32.png")).convert("RGBA").resize((1179, 2556))
    W = 1179 * 2 + 60
    out = Image.new("RGB", (W, 2556 + 70), (236, 236, 240))
    d = ImageDraw.Draw(out)
    f = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial Bold.ttf", 34)
    d.text((20, 16), "ours: scene layers + characters rigs (no UI chrome)" + (" [draft]" if draft else ""), fill=(20, 20, 30), font=f)
    d.text((1179 + 40, 16), "reference 002 (looked at only)", fill=(20, 20, 30), font=f)
    out.paste(ours.convert("RGB"), (20, 70))
    out.paste(ref.convert("RGB"), (1179 + 40, 70))
    os.makedirs(SHEETS, exist_ok=True)
    dst = os.path.join(SHEETS, f"scene_home_proof{'_draft' if draft else ''}.png")
    out.save(dst, optimize=True)
    small = out.resize((out.width // 2, out.height // 2), Image.LANCZOS)
    small.save(dst.replace(".png", "_half.png"))
    return dst


def loading_stack(draft=False):
    D = os.path.join(K.BUILD, "draft")
    bd = _layer(os.path.join(K.OUT, "loadingBackdrop@3x.png"), os.path.join(D, "loadingBackdrop.png"), draft)
    cv = bd.copy()
    lay = json.load(open(os.path.join(K.OUT, "char_loading_layout.json")))["characters"]
    for name, c in sorted(lay.items(), key=lambda kv: kv[1]["z"]):
        im = Image.open(os.path.join(K.OUT, c["file"])).convert("RGBA")
        cv.alpha_composite(im, (round(c["x"] * 3), round(c["y"] * 3)))
    return cv


def proof_loading(draft=False):
    ours = loading_stack(draft)
    ref = Image.open(os.path.join(K.APP, "build", "ui-art", "refcrops", "loadingBackdrop.png")).convert("RGBA").resize((1179, 2556))
    out = Image.new("RGB", (1179 * 2 + 60, 2556 + 70), (236, 236, 240))
    d = ImageDraw.Draw(out)
    f = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial Bold.ttf", 34)
    d.text((20, 16), "ours: loadingBackdrop + characters (logo, text not drawn)" + (" [draft]" if draft else ""), fill=(20, 20, 30), font=f)
    d.text((1179 + 40, 16), "reference V1 t=0 (looked at only)", fill=(20, 20, 30), font=f)
    out.paste(ours.convert("RGB"), (20, 70))
    out.paste(ref.convert("RGB"), (1179 + 40, 70))
    dst = os.path.join(SHEETS, f"scene_loading_proof{'_draft' if draft else ''}.png")
    out.save(dst, optimize=True)
    out.resize((out.width // 2, out.height // 2), Image.LANCZOS).save(dst.replace(".png", "_half.png"))
    return dst
