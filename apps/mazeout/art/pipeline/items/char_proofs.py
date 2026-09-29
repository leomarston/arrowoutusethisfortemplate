#!/usr/bin/env python3
"""Characters lane proofs (r3, 2026-09-25): not a recipe (no ASSETS). Sheets -> art/ui/sheets/characters/ (gitignored).

    PY=~/.venvs/mf3d/bin/python                  # from apps/mazeout
    $PY art/pipeline/items/char_proofs.py loading <name> x0 y0 x1 y1 [k]   # ours (live layout) | store 8 | V1 t=0, a pt box
    $PY art/pipeline/items/char_proofs.py eyes x0 y0 x1 y1                 # eye-white blobs (pt) in ours / store 8 / V1
    $PY art/pipeline/items/char_proofs.py layout                           # rewrite art/out/char_loading_layout.json
    $PY art/pipeline/items/char_proofs.py idle [sci_home wk_homeR_blue wk_homeL_blue]
        # the home rigs at the SPEC-motion-audio 8.2 / ui.json puppet idle-loop extremes, composed the way PuppetStage
        # does (rect_pt, rotations about rig.json pivots, head group about neck, whole about feet, torso scaleY about
        # its track pivot); red = transparent px inside the filled silhouette (compare with the rest pose)
References (research/store, research/video refcrops) are looked at only.
"""

import os, sys, json
APP = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
os.chdir(APP)
sys.path.insert(0, "art/review/tools")
import gradeB_compose as G
from PIL import Image, ImageDraw, ImageFont
Image.MAX_IMAGE_PIXELS = None
SH = "art/ui/sheets/characters"
os.makedirs(SH, exist_ok=True)

def live_layout(write=False):
    """char_loading.layout() from the current sidecars (optionally rewrite art/out/char_loading_layout.json)."""
    for p in ("art/ui/tools", "art/pipeline", "art/pipeline/items"):
        if p not in sys.path:
            sys.path.insert(0, p)
    import char_loading as CL
    L = CL.layout()
    if write:
        json.dump(dict(note="loading screen (store 8 / kickoff state.png): frame top-left x/y in pt on the 393 x 852 "
                            "screen, z back -> front; placed so each character's eye midpoint sits on the original's",
                       characters=L), open("art/out/char_loading_layout.json", "w"), indent=1)
    return L


def compose(over=None, layout=None, logo=True):
    over = over or {}
    cv = G.img("art/out/loadingBackdrop@3x.png").copy()
    lay = layout or live_layout()
    for name, c in sorted(lay.items(), key=lambda kv: kv[1]["z"]):
        G.put(cv, G.img(over.get(name, f"art/out/{c['file']}")), c["x"], c["y"])
    if logo:
        lg = G.img("art/ui/out/logoArrowOut@3x.png")
        s = 197.0 / (299.33 - 8.67)
        G.put(cv, lg, 21 - 8.67 * s, 65 - 1.67 * s, 306 * s, 236 * s)
    return cv

def refs():
    s8 = G.img("research/store/iphone-8.png").resize((1179, round(2868 * 1179 / 1320)), Image.LANCZOS)
    v1 = G.img("build/ui-art/refcrops/loadingBackdrop.png")
    return s8, v1

def tri(ours, box, dst, k=3, labels=("ours", "store 8", "V1 t=0")):
    s8, v1 = refs()
    x0, y0, x1, y1 = box
    tiles = []
    for im in (ours, s8, v1):
        t = im.convert("RGB").crop((round(x0 * 3), round(y0 * 3), round(x1 * 3), round(y1 * 3)))
        if k != 3:
            t = t.resize((round(t.width * k / 3), round(t.height * k / 3)), Image.LANCZOS)
        tiles.append(t)
    W = sum(t.width for t in tiles) + 20 * 2
    out = Image.new("RGB", (W, tiles[0].height + 30), (236, 236, 240))
    d = ImageDraw.Draw(out)
    f = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial Bold.ttf", 18)
    x = 0
    for t, l in zip(tiles, labels):
        out.paste(t, (x, 30)); d.text((x + 4, 5), l, fill=(0, 0, 0), font=f); x += t.width + 20
    out.save(dst); print(dst, out.size)

def white_blobs(im, box, smax=0.20, vmin=0.86, min_px=150, top=3):
    """Near-white blobs (eye whites) inside box (pt) -> [(x0, x1, y0, y1, cx, cy, px)] in pt."""
    import numpy as np
    from scipy import ndimage
    x0, y0, x1, y1 = [round(v * 3) for v in box]
    a = np.asarray(im.convert("RGB"))[y0:y1, x0:x1].astype(float) / 255
    mx, mn = a.max(2), a.min(2)
    s = np.where(mx > 0, (mx - mn) / np.maximum(mx, 1e-6), 0)
    m = ndimage.binary_opening((s < smax) & (mx > vmin), iterations=2)
    lab, n = ndimage.label(m)
    out = []
    for i in range(1, n + 1):
        yy, xx = np.nonzero(lab == i)
        if len(yy) < min_px:
            continue
        out.append((round((xx.min() + x0) / 3, 1), round((xx.max() + x0) / 3, 1), round((yy.min() + y0) / 3, 1),
                    round((yy.max() + y0) / 3, 1), round((xx.mean() + x0) / 3, 1), round((yy.mean() + y0) / 3, 1), len(yy)))
    return sorted(out, key=lambda t: -t[-1])[:top]


def eye_report(box, over=None, label=""):
    s8, v1 = refs()
    ours = compose(over or {}, logo=False)
    for nm, im in (("ours", ours), ("store8", s8), ("V1", v1)):
        print(label, nm, white_blobs(im, box))


import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy import ndimage
S = 3
OUT = "art/out"

def load(rig):
    d = f"{OUT}/char_{rig}_rig"
    return d, json.load(open(f"{d}/rig.json"))

def pivot(rj, name):
    for L in rj["layers"]:
        if name in L.get("pivots_pt", {}):
            return L["pivots_pt"][name]
    return None

def xform(im, x0, y0, W, H, ops):
    """place layer image at (x0, y0) pt on a W x H pt canvas, then apply ops [(kind, arg, pivot)] in order."""
    cv = Image.new("RGBA", (round(W * S), round(H * S)), (0, 0, 0, 0))
    cv.alpha_composite(im, (round(x0 * S), round(y0 * S)))
    for kind, a, p in ops:
        if kind == "rot" and a:
            cv = cv.rotate(-a, resample=Image.BICUBIC, center=(p[0] * S, p[1] * S))
        elif kind == "ty" and a:
            cv = cv.transform(cv.size, Image.AFFINE, (1, 0, 0, 0, 1, -a * S), resample=Image.BICUBIC)
        elif kind == "sy" and a != 1.0:
            py = p[1] * S
            cv = cv.transform(cv.size, Image.AFFINE, (1, 0, 0, 0, 1 / a, py - py / a), resample=Image.BICUBIC)
    return cv

def rig_compose(rig, pose, part=None):
    """pose: dict(members={group: member}, overlays=[names], rot={layer: deg}, head=(ty, deg), whole=deg, torso_sy=s)."""
    d, rj = load(rig)
    W, H = rj["frame_pt"]
    groups = rj.get("groups", {})
    chosen = {g: pose.get("members", {}).get(g, v["default"]) for g, v in groups.items()}
    neck = pivot(rj, "neck")
    feet = pivot(rj, "feet")
    cv = Image.new("RGBA", (round(W * S), round(H * S)), (0, 0, 0, 0))
    is_worker = feet is not None
    for L in sorted(rj["layers"], key=lambda l: l.get("z", 0)):
        n = L["name"]
        if part and not part(n):
            continue
        if L.get("overlay"):
            if n not in pose.get("overlays", []):
                continue
        elif L.get("group") and chosen[L["group"]] != n:
            continue
        im = Image.open(f"{d}/{L['file']}").convert("RGBA")
        ops = []
        if n == "torso" and pose.get("torso_sy"):
            ops.append(("sy", pose["torso_sy"], (95.3, 164.0)))
        if n in pose.get("rot", {}):
            ops.append(("rot", pose["rot"][n], L["pivots_pt"]["shoulder"]))
        in_head = (not is_worker) and (L.get("group") == "head" or L.get("parent") == "head")
        if in_head and pose.get("head"):
            ty, deg = pose["head"]
            ops.append(("rot", deg, neck))
            ops.append(("ty", ty, None))
        if is_worker and pose.get("whole"):
            ops.append(("rot", pose["whole"], feet))
        cv.alpha_composite(xform(im, L["rect_pt"][0], L["rect_pt"][1], W, H, ops))
    return cv, rj

def holes(cv, thr=0.5):
    a = np.asarray(cv)[..., 3] / 255.0
    solid = a > thr
    filled = ndimage.binary_fill_holes(ndimage.binary_closing(solid, iterations=2))
    h = filled & (a < 0.9)
    h = ndimage.binary_opening(h, iterations=1)
    lab, n = ndimage.label(h)
    sizes = ndimage.sum(h, lab, range(1, n + 1)) if n else []
    return int(h.sum()), [int(s) for s in sorted(sizes, reverse=True)[:5]], h

def font(n):
    return ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial Bold.ttf", n)

POSES = {
    "sci_home": [
        ("rest", {}),
        ("breathe peak: torso 1.012, head -0.8 pt +0.5deg, arms -1.2/+1.2", dict(torso_sy=1.012, head=(-0.8, 0.5), rot=dict(armL=-1.2, armR=1.2))),
        ("head +1.6deg (t 0.79), -0.4 pt", dict(torso_sy=1.006, head=(-0.4, 1.6), rot=dict(armL=-0.6, armR=0.6))),
        ("head -0.6deg (t 2.37) + lidsHalf", dict(torso_sy=1.006, head=(-0.4, -0.6), rot=dict(armL=-0.6, armR=0.6), overlays=["lidsHalf"])),
        ("lidsClosed (blink, t 2.15)", dict(torso_sy=1.008, head=(-0.5, -0.2), overlays=["lidsClosed"])),
        ("armR_point + headOpen (store 7 pose)", dict(members=dict(armR="armR_point", head="headOpen"), rot=dict(armR_point=1.2))),
    ],
    "wk_homeR_blue": [
        ("rest (eyes_half, body_smile)", {}),
        ("look up -4deg, eyes_open, body_open, clipboard +3", dict(whole=-4.0, members=dict(eyes="eyes_open", body="body_open"), rot=dict(armL=3.0))),
        ("nod +3deg, eyes_closed", dict(whole=3.0, members=dict(eyes="eyes_closed"), rot=dict(armL=3.0))),
        ("writing: pencil +6, board -2, sway +1", dict(whole=1.0, rot=dict(armR=6.0, armL=-2.0))),
        ("writing: pencil -6, sway -1", dict(whole=-1.0, rot=dict(armR=-6.0, armL=-2.0))),
    ],
    "wk_homeL_blue": [
        ("rest (eyes_open, body_smile)", {}),
        ("talk: body_open, walkie -4, sway +1.5", dict(whole=1.5, members=dict(body="body_open"), rot=dict(armR=-4.0))),
        ("think -4deg total, eyes_half", dict(whole=-4.0, members=dict(eyes="eyes_half"))),
        ("wink beat: eyes_closed", dict(whole=-2.5, members=dict(eyes="eyes_closed"))),
        ("wave armL -25 (ui.json)", dict(whole=-1.5, rot=dict(armL=-25.0))),
        ("wave armL -5", dict(whole=1.5, rot=dict(armL=-5.0))),
        ("NEW eyes_wink (§15.4)", dict(whole=-2.5, members=dict(eyes="eyes_wink"))),
        ("NEW armL_wave member", dict(whole=1.5, members=dict(armL="armL_wave"))),
        ("armL_wave +10deg (swing)", dict(whole=-1.5, members=dict(armL="armL_wave", body="body_open"), rot=dict(armL_wave=10.0))),
        ("armL_wave -10deg (swing)", dict(whole=1.5, members=dict(armL="armL_wave"), rot=dict(armL_wave=-10.0))),
    ],
}

def idle_sheet(rig, tag="", bg=(58, 100, 214)):
    rows = []
    for label, pose in POSES[rig]:
        cv, rj = rig_compose(rig, pose)
        tot, big, h = holes(cv)
        rows.append((label, cv, tot, big, h))
    W, H = rows[0][1].size
    k = 1.0
    out = Image.new("RGB", (len(rows) * (W + 20) + 20, H + 150), (236, 236, 240))
    d = ImageDraw.Draw(out)
    x = 20
    for label, cv, tot, big, h in rows:
        b = Image.new("RGBA", cv.size, bg + (255,))
        b.alpha_composite(cv)
        hm = Image.fromarray((h * 255).astype(np.uint8))
        red = Image.new("RGBA", cv.size, (255, 40, 40, 255))
        b.paste(red, (0, 0), hm)
        out.paste(b.convert("RGB"), (x, 90))
        words = label.split(", ")
        d.text((x, 8), "\n".join(words[:3]), fill=(0, 0, 0), font=font(15))
        d.text((x, 70), f"holes {tot} px {big}", fill=(200, 0, 0) if tot > 30 else (0, 110, 0), font=font(15))
        x += W + 20
        print(rig, "|", label, "| holes", tot, big)
    dst = f"art/ui/sheets/characters/idle_{rig}{tag}.png"
    out.save(dst)
    print(dst)


if __name__ == "__main__":
    cmd, args = sys.argv[1], sys.argv[2:]
    if cmd == "loading":
        k = float(args[5]) if len(args) > 5 else 3
        tri(compose(), tuple(float(v) for v in args[1:5]), f"{SH}/{args[0]}.png", k=k)
    elif cmd == "eyes":
        eye_report(tuple(float(v) for v in args[:4]))
    elif cmd == "layout":
        print(json.dumps(live_layout(write=True), indent=1))
    elif cmd == "idle":
        for r in (args or POSES):
            idle_sheet(r)
