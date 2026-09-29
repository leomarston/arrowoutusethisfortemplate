#!/usr/bin/env python3
"""R2 CAST proofs + review sheets (PLAN-P §4.2). Sheets go to art/review/cast/ (committed like art/review/concepts/);
numbers to art/review/cast/proofs.json. Research shots / store frames are LOOKED AT only (copygate thumbnails).

    PY=~/.venvs/mf3d/bin/python        # from apps/mazeout
    $PY art/review/tools/r2_cast.py recompose            # rest layers vs the full render (ShellTests' metric) x 3 rigs
    $PY art/review/tools/r2_cast.py idle                 # every rig through its ui.json puppet loop (48 frames): holes
    $PY art/review/tools/r2_cast.py sheet boss|crew|swaps|figures|avatars
    $PY art/review/tools/r2_cast.py home                 # the cast in a D1 draft home composition + copygate vs 002
    $PY art/review/tools/r2_cast.py loading              # the loading cast in a D1 draft composition + copygate vs store 8
    $PY art/review/tools/r2_cast.py profile              # the 8 avatars in an Edit Profile page mock + copygate vs meta-003

The rigs keep the OLD rigs' layer / group / pivot names, so the idle proof drives them with the OLD rigs' ui.json
tracks (TRACKS below): exactly what A4 gets after its one mapping step (rig folder names).
"""
from __future__ import annotations

import json
import math
import os
import sys

APP = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
os.chdir(APP)
sys.path.insert(0, os.path.join(APP, "tools"))

import numpy as np  # noqa: E402
from PIL import Image, ImageDraw, ImageFilter, ImageFont  # noqa: E402
from scipy import ndimage  # noqa: E402

S = 3
OUT = "art/out"
DST = "art/review/cast"
os.makedirs(DST, exist_ok=True)
PROOFS = os.path.join(DST, "proofs.json")
RIGS = ["boss_home", "dig_homeL", "dig_homeR"]
OLD = {"boss_home": "sci_home", "dig_homeL": "wk_homeL_blue", "dig_homeR": "wk_homeR_blue"}
TRACKS = {r: f"char_{OLD[r]}_rig" for r in RIGS}
BG_D1 = (46, 90, 96)


def font(n):
    for p in ("/System/Library/Fonts/Supplemental/Arial Bold.ttf", "/System/Library/Fonts/Helvetica.ttc"):
        if os.path.exists(p):
            return ImageFont.truetype(p, n)
    return ImageFont.load_default()


def img(p):
    return Image.open(p).convert("RGBA")


def on(bg, im):
    b = Image.new("RGBA", im.size, tuple(bg) + (255,))
    b.alpha_composite(im)
    return b


def save_proof(key, val):
    d = json.load(open(PROOFS)) if os.path.exists(PROOFS) else {}
    d[key] = val
    json.dump(d, open(PROOFS, "w"), indent=1)


# ------------------------------------------------------------------ rigs

def load(rig):
    d = f"{OUT}/char_{rig}_rig"
    return d, json.load(open(f"{d}/rig.json"))


def pivot(rj, name):
    for L in rj["layers"]:
        if name in L.get("pivots_pt", {}):
            return L["pivots_pt"][name]
    return None


def compose_rest(rig):
    d, rj = load(rig)
    W, H = rj["frame_pt"]
    defaults = {g["default"] for g in rj.get("groups", {}).values()}
    cv = Image.new("RGBA", (round(W * S), round(H * S)), (0, 0, 0, 0))
    for L in sorted(rj["layers"], key=lambda l: l["z"]):
        if L.get("overlay") or (L.get("group") and L["name"] not in defaults):
            continue
        cv.alpha_composite(img(f"{d}/{L['file']}"), (round(L["rect_pt"][0] * S), round(L["rect_pt"][1] * S)))
    return cv, rj, d


def cmd_recompose():
    res = {}
    for rig in RIGS:
        cv, rj, d = compose_rest(rig)
        full = img(os.path.normpath(os.path.join(d, rj["full"])))
        bg = (98, 132, 214)
        a = np.asarray(on(bg, full).convert("RGB")).astype(float)
        b = np.asarray(on(bg, cv).convert("RGB")).astype(float)
        diff = np.abs(a - b).max(2)
        res[rig] = dict(mean_abs=round(float(np.abs(a - b).mean()), 3), max_channel_mean=round(float(diff.mean()), 3),
                        pct_gt40=round(float((diff > 40).mean() * 100), 3), layers=len(rj["layers"]),
                        rest=[L["name"] for L in rj["layers"] if not L.get("overlay") and (not L.get("group") or
                              L["name"] in {g["default"] for g in rj["groups"].values()})],
                        groups={g: v for g, v in rj.get("groups", {}).items()}, rig_proof=rj.get("proof"))
        print(rig, res[rig])
    save_proof("recompose", dict(note="default layers at rect_pt vs the full render, on (98,132,214); ShellTests pins "
                                      "mean <= 1/255 (its metric = mean abs RGB), the pipeline <= 2/255 and <= 1 % px > 40",
                                 rigs=res))


# the ui.json loop of the OLD rig drives the new one (same names)

def _tracks(rig):
    u = json.load(open("App/Resources/Tuning/ui.json"))
    return u["puppet"][TRACKS[rig]]


def _val(tr, t):
    ts, vs = tr["t"], tr["v"]
    if t <= ts[0]:
        return vs[0]
    for i in range(len(ts) - 1):
        if ts[i] <= t <= ts[i + 1]:
            if isinstance(vs[i], str) or tr["prop"] in ("member", "overlay"):
                return vs[i]
            u = (t - ts[i]) / max(ts[i + 1] - ts[i], 1e-9)
            return vs[i] + (vs[i + 1] - vs[i]) * u
    return vs[-1]


def _xform(im, x0, y0, W, H, ops):
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


def compose_at(rig, t):
    """PuppetStage's model: whole = rotation about feet (workers), head group + lids about neck (+ translateY), a
    layer's rotation about its shoulder (or the track pivot), torso scaleY about the track pivot, member / overlay swaps."""
    d, rj = load(rig)
    W, H = rj["frame_pt"]
    P = _tracks(rig)
    feet, neck = pivot(rj, "feet"), pivot(rj, "neck")
    is_worker = feet is not None
    chosen = {g: v["default"] for g, v in rj.get("groups", {}).items()}
    overlay, whole, head_ty, head_rot = "", 0.0, 0.0, 0.0
    rot, sy, piv = {}, {}, {}
    for tr in P["tracks"]:
        v = _val(tr, t)
        if tr["prop"] == "member":
            chosen[tr["layer"]] = v
        elif tr["prop"] == "overlay":
            overlay = v
        elif tr["layer"] == "whole" and tr["prop"] == "rotation":
            whole += v
        elif tr["layer"] == "head":
            if tr["prop"] == "translateY":
                head_ty += v
            elif tr["prop"] == "rotation":
                head_rot += v
        elif tr["prop"] == "rotation":
            rot[tr["layer"]] = rot.get(tr["layer"], 0.0) + v
            if tr.get("pivot"):
                piv[tr["layer"]] = tr["pivot"]
        elif tr["prop"] == "scaleY":
            sy[tr["layer"]] = v
            piv[tr["layer"]] = tr.get("pivot")
    cv = Image.new("RGBA", (round(W * S), round(H * S)), (0, 0, 0, 0))
    for L in sorted(rj["layers"], key=lambda l: l["z"]):
        n = L["name"]
        if L.get("overlay"):
            if n != overlay:
                continue
        elif L.get("group") and chosen.get(L["group"]) != n:
            continue
        ops = []
        if n in sy:
            ops.append(("sy", sy[n], piv[n]))
        if n in rot:
            ops.append(("rot", rot[n], piv.get(n) or L.get("pivots_pt", {}).get("shoulder")))
        in_head = (not is_worker) and (L.get("group") == "head" or L.get("parent") == "head")
        if in_head:
            ops.append(("rot", head_rot, neck))
            ops.append(("ty", head_ty, None))
        if is_worker and whole:
            ops.append(("rot", whole, feet))
        cv.alpha_composite(_xform(img(f"{d}/{L['file']}"), L["rect_pt"][0], L["rect_pt"][1], W, H, ops))
    return cv, dict(t=round(t, 3), chosen=chosen, overlay=overlay, whole=round(whole, 2), rot={k: round(v, 2) for k, v in rot.items()})


def holes(cv, thr=0.5):
    a = np.asarray(cv)[..., 3] / 255.0
    solid = a > thr
    filled = ndimage.binary_fill_holes(ndimage.binary_closing(solid, iterations=2))
    h = filled & (a < 0.9)
    h = ndimage.binary_opening(h, iterations=1)
    return int(h.sum()), h


def cmd_idle(n=48):
    res = {}
    for rig in RIGS:
        P = _tracks(rig)
        rest, _, _ = compose_rest(rig)
        h0, _ = holes(rest)
        cyc = P["cycle"]
        rows, worst = [], (0, None)
        for i in range(n):
            t = cyc * i / n
            cv, st = compose_at(rig, t)
            h, hm = holes(cv)
            rows.append((t, cv, h, hm, st))
            if h - h0 > worst[0]:
                worst = (h - h0, round(t, 3))
        res[rig] = dict(cycle=cyc, frames=n, rest_holes_px=h0, max_extra_holes_px=worst[0], at_t=worst[1],
                        tracks=len(P["tracks"]), driven_by=TRACKS[rig])
        # a strip of 8 frames (every 6th) with holes in red
        pick = rows[::max(1, n // 8)][:8]
        W, H = pick[0][1].size
        out = Image.new("RGB", (8 * (W + 12) + 12, H + 60), (236, 236, 240))
        dr = ImageDraw.Draw(out)
        for k, (t, cv, h, hm, st) in enumerate(pick):
            b = on(BG_D1, cv)
            red = Image.new("RGBA", cv.size, (255, 40, 40, 255))
            b.paste(red, (0, 0), Image.fromarray((hm * 255).astype(np.uint8)))
            out.paste(b.convert("RGB"), (12 + k * (W + 12), 50))
            dr.text((12 + k * (W + 12), 6), f"t {t:.2f}s holes {h} (rest {h0})\n{','.join(v for v in st['chosen'].values())}",
                    fill=(20, 20, 30), font=font(13))
        out.save(f"{DST}/idle_{rig}.png", optimize=True)
        print(rig, res[rig])
    save_proof("idle", dict(note="each rig driven through the OLD rig's ui.json puppet loop (same layer names), 48 frames "
                                 "per cycle, composed as PuppetStage does; holes = transparent px inside the filled "
                                 "silhouette (the proof: no frame has more than the rest pose + tolerance)", rigs=res))


# ------------------------------------------------------------------ sheets

def sheet_rows(rows, title, dst, third=True, bg=(236, 236, 240)):
    W = max(20 + sum(t.width + 20 for _, t in tiles) for _, tiles in rows)
    hs = [max(t.height for _, t in tiles) for _, tiles in rows]
    H = 60 + sum(h + 64 + (h // 3 + 16 if third else 0) for h in hs)
    out = Image.new("RGB", (max(W, 900), H), bg)
    dr = ImageDraw.Draw(out)
    dr.text((20, 16), title, fill=(20, 20, 30), font=font(22))
    y = 60
    for (lab, tiles), h in zip(rows, hs):
        dr.text((20, y), lab, fill=(20, 20, 30), font=font(17))
        x = 20
        for cap, t in tiles:
            dr.text((x, y + 22), cap, fill=(60, 60, 70), font=font(14))
            out.paste(t.convert("RGB"), (x, y + 44))
            if third:
                out.paste(t.convert("RGB").resize((max(1, t.width // 3), max(1, t.height // 3)), Image.LANCZOS), (x, y + 52 + h))
            x += t.width + 20
        y += h + 64 + (h // 3 + 16 if third else 0)
    out.save(dst, optimize=True)
    print(dst)


def sil(im):
    a = np.asarray(im)[..., 3] > 100
    o = np.full(a.shape + (3,), 238, np.uint8)
    o[a] = (30, 30, 30)
    return Image.fromarray(o)


def cmd_sheet(which):
    if which == "boss":
        old = on((59, 92, 180), img(f"{OUT}/char_sci_home@3x.png"))
        new_rest, _, _ = compose_rest("boss_home")
        st = "build/ui-art/route3d/char_bossStation.png"
        new = Image.new("RGBA", new_rest.size, BG_D1 + (255,))
        _, rj = load("boss_home")
        torso_head, _ = _part_compose("boss_home", lambda n: not n.startswith("arm"))
        arms, _ = _part_compose("boss_home", lambda n: n.startswith("arm"))
        new.alpha_composite(torso_head)
        if os.path.exists(st):
            new.alpha_composite(img(st))
        new.alpha_composite(arms)
        head_box = (100, 0, 470, 290)
        rows = [("today (lab light) | boss v2 (D1 light, same camera / frame / scale; scaffold = char_bossStation between "
                 "the torso/head stage and the arms stage, as homeConsole today)", [("today", old), ("boss v2 + station", new)]),
                ("heads at 2x", [("today", old.crop(head_box).resize((740, 580), Image.LANCZOS)),
                                 ("v2", new.crop(head_box).resize((740, 580), Image.LANCZOS))])]
        sheet_rows(rows, "BOSS v2 -- old -> new (R2 production; muzzle = banded strand blend, fang x1.4)", f"{DST}/boss.png")
    elif which == "crew":
        A = on(BG_D1, img(f"{OUT}/char_sci_home@3x.png"))
        B = on(BG_D1, img(f"{OUT}/char_wk_homeL_blue@3x.png"))
        L = on(BG_D1, img(f"{OUT}/char_dig_homeL@3x.png"))
        R = on(BG_D1, img(f"{OUT}/char_dig_homeR@3x.png"))
        rows = [("calibration card at game size (3 px/pt): A = our pink boss (the owner's 'art'), B = today's worker ('dough'), "
                 "and the two new home Diggers", [("A: boss (fur)", A), ("B: today's worker", B), ("NEW Digger L (shovel)", L),
                                                   ("NEW Digger R (map)", R)]),
                ("silhouettes (1/3 read)", [(n, sil(img(p)).resize((img(p).width // 3, img(p).height // 3), Image.LANCZOS))
                                            for n, p in (("A", f"{OUT}/char_sci_home@3x.png"), ("B", f"{OUT}/char_wk_homeL_blue@3x.png"),
                                                         ("L", f"{OUT}/char_dig_homeL@3x.png"), ("R", f"{OUT}/char_dig_homeR@3x.png"))]),
                ("Digger heads at 2x", [(n, on(BG_D1, img(p)).crop(bx).resize(((bx[2] - bx[0]) * 2, (bx[3] - bx[1]) * 2), Image.LANCZOS))
                                        for n, p, bx in (("L", f"{OUT}/char_dig_homeL@3x.png", (120, 20, 380, 240)),
                                                         ("R", f"{OUT}/char_dig_homeR@3x.png", (80, 20, 340, 240)))])]
        sheet_rows(rows, "CREW -- the Diggers next to the A/B calibration card", f"{DST}/crew.png", third=False)
    elif which == "swaps":
        rows = []
        for rig in RIGS:
            _, rj = load(rig)
            groups = rj.get("groups", {})
            tiles = []
            if rig == "boss_home":
                for names, cap in (({"torso", "armL", "armR", "headSmile"}, "rest"), ({"torso", "armL", "armR", "headSmile", "lidsHalf"}, "lidsHalf"),
                                   ({"torso", "armL", "armR", "headSmile", "lidsClosed"}, "lidsClosed"),
                                   ({"torso", "armL", "armR_point", "headOpen"}, "headOpen + armR_point"),
                                   ({"torso", "armL", "armR_point", "headOpen", "lidsClosed"}, "laugh")):
                    tiles.append((cap, on(BG_D1, _names_compose(rig, names))))
            else:
                base = {L["name"] for L in rj["layers"] if not L.get("group") and not L.get("overlay")}
                for body in groups["body"]["members"]:
                    for eyes in groups["eyes"]["members"]:
                        arms = {groups["armL"]["default"]} if "armL" in groups else set()
                        tiles.append((f"{body.split('_')[1]}+{eyes.split('_')[1]}", on(BG_D1, _names_compose(rig, base | {body, eyes} | arms))))
                if "armL" in groups:
                    for m in groups["armL"]["members"]:
                        tiles.append((m, on(BG_D1, _names_compose(rig, base | {groups["body"]["default"], groups["eyes"]["default"], m}))))
            rows.append((f"{rig}: swap groups", [(c, t.resize((t.width * 2 // 3, t.height * 2 // 3), Image.LANCZOS)) for c, t in tiles]))
        sheet_rows(rows, "RIG SWAPS -- every group member composed (the puppet's states)", f"{DST}/swaps.png", third=False)
    elif which in ("figures", "avatars"):
        ids = (["bossLoading", "digCart", "digFlyer", "digPop1", "digPop2", "digClawPair", "digRacers", "digBalloon"] if which == "figures"
               else ["avatarMiner", "avatarMapper", "avatarSleuth", "avatarLunch", "avatarBoss", "avatarConfetti", "avatarStrong", "avatarSleepy"])
        tiles = []
        for i in ids:
            p = f"{OUT}/char_{i}@3x.png"
            if os.path.exists(p):
                tiles.append((i, on(BG_D1, img(p))))
        if which == "figures":
            rows = [("loading figures (game size)", tiles[:5]), ("event figures (game size)", tiles[5:])]
        else:
            rows = [("avatars at the manifest size (64 pt = 192 px), Edit Profile slot order", tiles),
                    ("at 30 pt (rows / race chips)", [(n, t.resize((90, 90), Image.LANCZOS)) for n, t in tiles])]
        sheet_rows(rows, f"{which.upper()} (R2)", f"{DST}/{which}.png")


def _names_compose(rig, names):
    d, rj = load(rig)
    W, H = rj["frame_pt"]
    cv = Image.new("RGBA", (round(W * S), round(H * S)), (0, 0, 0, 0))
    for L in sorted(rj["layers"], key=lambda l: l["z"]):
        if L["name"] in names:
            cv.alpha_composite(img(f"{d}/{L['file']}"), (round(L["rect_pt"][0] * S), round(L["rect_pt"][1] * S)))
    return cv


def _part_compose(rig, keep):
    _, rj = load(rig)
    defaults = {g["default"] for g in rj.get("groups", {}).values()}
    names = {L["name"] for L in rj["layers"] if keep(L["name"]) and not L.get("overlay") and (not L.get("group") or L["name"] in defaults)}
    return _names_compose(rig, names), rj


# ------------------------------------------------------------------ composed proofs (+ copygate)

def paste_pt(cv, im, x, y):
    cv.alpha_composite(im, (round(x * S), round(y * S)))


def _grad(W, H, c0, c1, axis=1, gamma=1.0):
    t = np.linspace(0, 1, H if axis == 1 else W) ** gamma
    a = np.asarray(c0, float)[None] * (1 - t[:, None]) + np.asarray(c1, float)[None] * t[:, None]
    if axis == 1:
        return np.repeat(a[:, None, :], W, 1)
    return np.repeat(a[None, :, :], H, 0)


def d1_home_draft():
    """A DRAFT D1 burrow backdrop (R3 HOME paints the real one): teal-grey rock, a warm daylight shaft from the top
    right, timber props + a cross-beam, a round tunnel mouth, a packed-earth floor with a plank pad. Only here to put
    the cast in a D1 context for the copy gate; never shipped."""
    W, H = 393 * S, 852 * S
    a = _grad(W, H, (0x4E, 0x7F, 0x86), (0x1B, 0x3A, 0x40), gamma=0.9)
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    shaft = np.clip(1 - np.abs((xx - (W * 0.78 - (yy * 0.35))) / (W * 0.16)), 0, 1) * np.clip(1 - yy / (H * 0.62), 0, 1)
    a = a + shaft[..., None] * (np.array([0xFF, 0xF1, 0xCF]) - a) * 0.45
    # tunnel mouth
    tm = np.hypot((xx - W * 0.50) / (W * 0.20), (yy - H * 0.40) / (H * 0.085))
    a = np.where((tm < 1.0)[..., None], a * 0.25 + np.array([10, 18, 20]) * 0.75, a)
    ring = (tm >= 1.0) & (tm < 1.16)
    a = np.where(ring[..., None], np.array([0x7E, 0x4E, 0x27]) * 0.9, a)
    # floor
    fl = yy > H * 0.676
    a = np.where(fl[..., None], _grad(W, H, (0xB8, 0x89, 0x5A), (0x6C, 0x4A, 0x2C)), a)
    pad = np.hypot((xx - W * 0.5) / (W * 0.42), (yy - H * 0.80) / (H * 0.07)) < 1.0
    a = np.where(pad[..., None], np.array([0xD9, 0xA4, 0x62]), a)
    im = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8)).convert("RGBA")
    dr = ImageDraw.Draw(im)
    for x0 in (0.03, 0.90):
        dr.rectangle((W * x0, H * 0.12, W * (x0 + 0.07), H * 0.676), fill=(0xB9, 0x7A, 0x3E))
    dr.rectangle((0, H * 0.12, W, H * 0.145), fill=(0xE0, 0xA8, 0x62))
    for lx, ly in ((0.10, 0.20), (0.88, 0.30)):
        dr.ellipse((W * lx - 18, H * ly - 18, W * lx + 18, H * ly + 18), fill=(0xFF, 0xCF, 0x6B))
    return im.filter(ImageFilter.GaussianBlur(1.2))


def _ui_d1_mock(cv):
    """The home UI at its UNCHANGED rects (ruling 37b; ui.json frames.home), drawn as flat D1-token shapes (teal chrome
    #17B3A3, tangerine CTA #FFB422 -> #FF9A12, cream labels): a MOCK of what A5's palette codemod produces, so the
    proof carries the UI's structure without today's backdrop pixels (R1's remapped capture has them round every
    element)."""
    dr = ImageDraw.Draw(cv)
    f = lambda n: ImageFont.truetype("App/Resources/Fonts/PCDisplay-Black.ttf", round(n * S))   # noqa: E731

    def rr(x, y, w, h, r, fill, outline=None, width=0):
        dr.rounded_rectangle((x * S, y * S, (x + w) * S, (y + h) * S), r * S, fill=fill, outline=outline, width=round(width * S))
    teal, rim, dark = (0x17, 0xB3, 0xA3), (0x0B, 0x8A, 0x83), (0x05, 0x3F, 0x43)
    tang, tang2, cream = (0xFF, 0xB4, 0x22), (0xD0, 0x6A, 0x06), (0xFF, 0xFB, 0xEF)
    rr(12, 45, 54, 54, 12, teal, dark, 2.5)                       # avatar tile
    rr(22, 55, 34, 34, 8, (150, 170, 176))
    for x0, w in ((74, 112), (196, 124)):                         # coins / lives pills
        rr(x0, 52, w, 36, 18, (0xD4, 0xF4, 0xEC), dark, 2)
    dr.ellipse((68 * S, 46 * S, 110 * S, 94 * S), fill=(0xFF, 0xC8, 0x2E), outline=(0x9E, 0x6A, 0x00), width=2 * S)
    dr.ellipse((188 * S, 46 * S, 232 * S, 94 * S), fill=(0xF2, 0x55, 0x3F), outline=(0x8A, 0x1E, 0x12), width=2 * S)
    dr.text((150 * S, 70 * S), "2240", font=f(20), fill=dark, anchor="mm")
    dr.text((278 * S, 70 * S), "Full", font=f(20), fill=dark, anchor="mm")
    rr(332, 45, 50, 50, 12, teal, dark, 2.5)                      # settings
    rr(19, 107, 355, 44, 22, (0xD4, 0xF4, 0xEC), dark, 2)         # the event bar
    rr(23, 111, 190, 36, 18, tang)
    dr.ellipse((14 * S, 196 * S, 96 * S, 278 * S), fill=teal, outline=dark, width=3 * S)   # a home event badge
    rr(147.5, 518.8, 98.4, 50.2, 14, (0xF0, 0xB8, 0x6A), (0x9E, 0x5F, 0x24), 2.5)          # LEVEL plank
    dr.text((196.7 * S, 530 * S), "LEVEL", font=f(12), fill=cream, anchor="mm")
    dr.text((196.7 * S, 552 * S), "32", font=f(26), fill=cream, anchor="mm", stroke_width=round(1.5 * S), stroke_fill=(0x6A, 0x35, 0x10))
    rr(82.7, 620.5, 228.3, 105.5, 34, tang2)                      # Play
    rr(88, 624, 218, 92, 30, tang)
    dr.text((196.8 * S, 670 * S), "Play", font=f(48), fill=cream, anchor="mm", stroke_width=round(2.5 * S), stroke_fill=(0x8A, 0x3F, 0x00))
    dr.rectangle((0, 752 * S, 393 * S, 852 * S), fill=teal)       # nav bar
    dr.rectangle((0, 752 * S, 393 * S, 756 * S), fill=dark)
    rr(146, 730, 101, 122, 18, (0x7F, 0xEA, 0xDB), dark, 2.5)
    for cx in (60, 196.5, 333):
        dr.ellipse(((cx - 24) * S, 772 * S, (cx + 24) * S, 820 * S), fill=(0xFF, 0xCB, 0x2F), outline=dark, width=2 * S)
    return cv


def _gate(ours, theirs, kind, crop=None):
    import copygate as CG
    cfg = CG.load_config()
    m = CG.measure(ours, theirs, crop=crop, cmin=CG.kind_cmin(cfg, kind))
    j = CG.judge(m, kind, cfg)
    return dict(ours=ours, theirs=theirs, kind=kind, crop=crop, ssim=round(m["ssim"], 3), overlap=round(m["overlap"], 3),
                pass_=j["pass"])


def cmd_home():
    cv = d1_home_draft()
    for rig in RIGS:
        _, rj = load(rig)
        pl = rj["placement_pt"]
        if rig == "boss_home":
            th, _ = _part_compose(rig, lambda n: not n.startswith("arm"))
            paste_pt(cv, th, pl["x"], pl["y"])
            st = "build/ui-art/route3d/char_bossStation.png"
            if os.path.exists(st):
                paste_pt(cv, img(st), pl["x"], pl["y"])
            ar, _ = _part_compose(rig, lambda n: n.startswith("arm"))
            paste_pt(cv, ar, pl["x"], pl["y"])
        else:
            r, _, _ = compose_rest(rig)
            paste_pt(cv, r, pl["x"], pl["y"])
    _ui_d1_mock(cv)
    dst = f"{DST}/home-proof-D1draft.png"
    cv.convert("RGB").save(dst, optimize=True)
    res = [_gate(dst, "research/shots/002-home-L32.png", "screen"),
           _gate(dst, "research/shots/002-home-L32.png", "screen", crop=[0, 152, 393, 466]),
           _gate("art/review/concepts/home-mock-D1-cast.png", "research/shots/002-home-L32.png", "screen")]
    for r in res:
        print(r)
    save_proof("home", dict(note="the cast (3 rigs + the registered scaffold) at their D1 placements on a DRAFT burrow "
                                 "backdrop + a flat D1-token UI mock at the unchanged rects; R3 HOME replaces the backdrop and adds the Signpost. "
                                 "Row 2 = the scene band only (y 152..618, the UI rects excluded but the LEVEL plate). "
                                 "Row 3 = R1's mock (new cast on TODAY's composition) for reference.", gates=res, sheet=dst))


def d1_loading_draft():
    """A DRAFT tunnel-exit backdrop (R4 LOADING paints the real one): daylight at the top, rock walls converging,
    an earth floor rushing toward the camera. Never shipped."""
    W, H = 393 * S, 852 * S
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    a = _grad(W, H, (0x2E, 0x59, 0x61), (0x1B, 0x3A, 0x40))
    sky = np.hypot((xx - W * 0.5) / (W * 0.62), (yy - H * 0.20) / (H * 0.30))
    a = a + np.clip(1.1 - sky, 0, 1)[..., None] ** 1.2 * (np.array([0xFF, 0xF1, 0xCF]) - a)
    fl = yy > H * 0.62
    a = np.where(fl[..., None], _grad(W, H, (0xC7, 0x9A, 0x6A), (0x7E, 0x56, 0x34)), a)
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8)).convert("RGBA").filter(ImageFilter.GaussianBlur(1.5))


def cmd_loading():
    sys.path[:0] = ["art/ui/tools", "art/pipeline", "art/pipeline/items"]
    lay = {"char_digPop2": dict(x=228.0, y=430.0, z=-2), "char_bossLoading": dict(x=-14.0, y=238.0, z=-1),
           "char_digFlyer": dict(x=208.0, y=168.0, z=0), "char_digPop1": dict(x=-14.0, y=532.0, z=1),
           "char_digCart": dict(x=96.0, y=468.0, z=2)}
    cv = d1_loading_draft()
    for name, c in sorted(lay.items(), key=lambda kv: kv[1]["z"]):
        p = f"{OUT}/{name}@3x.png"
        if os.path.exists(p):
            paste_pt(cv, img(p), c["x"], c["y"])
    lg = "art/review/concepts/logo-LG1.png"
    if os.path.exists(lg):
        logo = img(lg)
        s = (300 * S) / logo.width
        logo = logo.resize((round(logo.width * s), round(logo.height * s)), Image.LANCZOS)
        cv.alpha_composite(logo, ((393 * S - logo.width) // 2, round(40 * S)))
    dr = ImageDraw.Draw(cv)
    f = ImageFont.truetype("App/Resources/Fonts/PCDisplay-Black.ttf", 27 * S)
    dr.text((393 * S / 2, 790 * S), "Loading..", font=f, fill=(255, 251, 239), anchor="mm", stroke_width=3 * S // 2,
            stroke_fill=(20, 60, 64))
    dst = f"{DST}/loading-proof-D1draft.png"
    cv.convert("RGB").save(dst, optimize=True)
    res = [_gate(dst, "research/store/iphone-8.png", "screen")]
    for r in res:
        print(r)
    save_proof("loading", dict(note="the 5 loading figures at the draft layout (char_cast_d1.LOADING_LAYOUT) on a DRAFT "
                                    "tunnel-exit backdrop + R1's LG-1 logo sketch centred top + 'Loading..' (R4 LOADING "
                                    "owns backdrop + layout, R6 the logo)", gates=res, sheet=dst))


def cmd_profile():
    """The 8 avatars in an Edit Profile page MOCK (D1 page teal, teal frames): not the app's page (A5's codemod
    produces that); a check that the portrait set + plates move away from theirs."""
    W, H = 393 * S, 852 * S
    cv = Image.fromarray(_grad(W, H, (0x15, 0x51, 0x58), (0x0C, 0x34, 0x3A)).astype(np.uint8)).convert("RGBA")
    dr = ImageDraw.Draw(cv)
    ids = ["avatarMiner", "avatarMapper", "avatarSleuth", "avatarLunch", "avatarBoss", "avatarConfetti", "avatarStrong", "avatarSleepy"]
    cells = [None] + ids
    x0, y0, step = 60, 330, 92
    for i, c in enumerate(cells):
        cx, cy = x0 + (i % 3) * step, y0 + (i // 3) * step
        dr.rounded_rectangle((cx * S - 9, cy * S - 9, (cx + 64) * S + 9, (cy + 64) * S + 9), 14 * S, fill=(0x17, 0xB3, 0xA3))
        if c and os.path.exists(f"{OUT}/char_{c}@3x.png"):
            paste_pt(cv, img(f"{OUT}/char_{c}@3x.png"), cx, cy)
        elif c is None:
            dr.rounded_rectangle((cx * S, cy * S, (cx + 64) * S, (cy + 64) * S), 10 * S, fill=(150, 170, 176))
    dst = f"{DST}/profile-proof-mock.png"
    cv.convert("RGB").save(dst, optimize=True)
    res = [_gate(dst, "research/shots/meta-003-profile-edit.png", "page")]
    for r in res:
        print(r)
    save_proof("profile", dict(note="page kind (overlap with chroma_min 8; SSIM informative); a MOCK page, not the app's",
                               gates=res, sheet=dst))


# ------------------------------------------------------------------ no-intersection gate for arrow sets (art-direction §4.3)

def cmd_overlap(tol=0.01):
    """Every arrow board of the loading cart vs every other: surface samples of one (marching cubes at 0.012) evaluated
    in the others' SDFs; FAIL if any point is deeper than `tol` (0.01 u ~ 0.7 pt at the cart's 72 pt/u)."""
    sys.path[:0] = ["art/ui/tools", "art/pipeline", "art/pipeline/items"]
    import char_cast_d1 as CC
    from mesher import mc_mesh
    from uikit import union
    sets = {"digCart": CC.boards(CC._CART_BOARDS, tag="c")}
    res = {}
    for name, parts in sets.items():
        boards = {}
        for n, sdf_, _, _ in parts:
            key = "".join(ch for ch in n if ch.isdigit())
            boards.setdefault(key, []).append(sdf_)
        bs = {k: union(*v) for k, v in boards.items()}
        worst = {}
        for a, sa in bs.items():
            v, _ = mc_mesh(sa, 0.012)
            for b, sb in bs.items():
                if a == b:
                    continue
                d = sb(np.asarray(v, np.float32))
                worst[f"{a}->{b}"] = round(float(d.min()), 4)
        mn = min(worst.values()) if worst else 1.0
        res[name] = dict(boards=len(bs), min_signed_distance=mn, pass_=mn > -tol, pairs=worst)
        print(name, res[name])
    save_proof("overlap", dict(note="arrow boards pairwise: min SDF of one board at another's surface samples (> -0.01 u = "
                                    "no visible interpenetration)", sets=res))


# ------------------------------------------------------------------ lane scratch manifest (the director merges it)

CAST = [
    # id, group, source, file, purpose, screen, replaces, extra
    ("boss", "characters", "art/pipeline/items/char_boss.py:boss_home", "art/out/char_boss_home_rig",
     "the pink boss v2 (furry pink ears, blush muzzle, amber eyes, fang, teal foreman coat, goggles) at the scaffold", "home", "scientist",
     dict(rig=True)),
    ("diggerShovel", "characters", "art/pipeline/items/char_crew_d1.py:dig_homeL", "art/out/char_dig_homeL_rig",
     "Digger (velvet fur, hard hat + headlamp, hi-vis vest) with a shovel over the shoulder, waving member", "home left",
     "workerWalkie", dict(rig=True)),
    ("diggerMap", "characters", "art/pipeline/items/char_crew_d1.py:dig_homeR", "art/out/char_dig_homeR_rig",
     "Digger with goggles down reading a tunnel map, marking it with a pencil", "home right", "workerClipboard", dict(rig=True)),
    ("bossLoading", "characters", "art/pipeline/items/char_cast_d1.py:char_bossLoading", "art/out/char_bossLoading@3x.png",
     "the boss behind a mossy rock raising a glowing lantern, pointing the way out", "loading", "scientistLoading", {}),
    ("digCart", "characters", "art/pipeline/items/char_cast_d1.py:char_digCart", "art/out/char_digCart@3x.png",
     "a mine cart of painted arrow boards rolling at the camera, a Digger riding its front", "loading", "workerCarrier", {}),
    ("digFlyer", "characters", "art/pipeline/items/char_cast_d1.py:char_digFlyer", "art/out/char_digFlyer@3x.png",
     "a Digger tossed up holding a big arrow board, hard hat flying off", "loading", "workerFlyer", {}),
    ("digPop1", "characters", "art/pipeline/items/char_cast_d1.py:char_digPop1", "art/out/char_digPop1@3x.png",
     "a Digger bursting out of a dig hole, both paws up", "loading", "workerFist", {}),
    ("digPop2", "characters", "art/pipeline/items/char_cast_d1.py:char_digPop2", "art/out/char_digPop2@3x.png",
     "a goggles-down Digger peeking out of a dig hole, trowel raised", "loading", "workerRunners + workerCrowdLeft", {}),
    ("digClawPair", "characters", "art/pipeline/items/char_cast_d1.py:char_digClawPair", "art/out/char_digClawPair@3x.png",
     "two Diggers cheering (claw-machine event header; cut at the bottom by design)", "claw event", "workerClawPair",
     dict(full_bleed=True)),
    ("digRacers", "characters", "art/pipeline/items/char_cast_d1.py:char_digRacers", "art/out/char_digRacers@3x.png",
     "three Diggers riding mine carts on short track stretches, near -> far (streak-race header)", "streak event",
     "workerRacers", dict(full_bleed=True)),
    ("digBalloon", "characters", "art/pipeline/items/char_cast_d1.py:char_digBalloon", "art/out/char_digBalloon@3x.png",
     "a Digger waving from a wicker basket, rope stubs up to the balloon (balloon event)", "balloon event", None, {}),
] + [(i, "avatars", f"art/pipeline/items/char_cast_d1.py:char_{i}", f"art/out/char_{i}@3x.png", f"avatar portrait ({i[6:]})",
      "profile, leaderboards, races, top bar", old, dict(full_bleed=True))
     for i, old in (("avatarMiner", "avatarWalkie"), ("avatarMapper", "avatarCapGlasses"), ("avatarSleuth", "avatarDetective"),
                    ("avatarLunch", "avatarBurger"), ("avatarBoss", "avatarScientist"), ("avatarConfetti", "avatarParty"),
                    ("avatarStrong", "avatarNotebook"), ("avatarSleepy", "avatarBoxHead"))]


def cmd_manifest():
    ents = []
    for i, grp, src, f, purpose, screen, old, extra in CAST:
        path = f + "/rig.json" if extra.get("rig") else f
        if not os.path.exists(path):
            print("missing", i, path)
            continue
        if extra.get("rig"):
            rj = json.load(open(path))
            size = rj["frame_pt"]
            notes = (f"R2 CAST (D1). Rig {len(rj['layers'])} layers, groups {sorted(rj['groups'])}, proof {rj['proof']}; "
                     f"placement {rj['placement_pt']['x']}, {rj['placement_pt']['y']} (D1 draft; R3 owns the spot). "
                     f"Same layer/group/pivot names as the rig it replaces.")
        else:
            w, h = Image.open(path).size
            size = [round(w / 3, 2), round(h / 3, 2)]
            notes = "R2 CAST (D1)."
        e = dict(id=i, family="3d", route="C1", group=grp, purpose=purpose, screen=screen, size_pt=size,
                 size_px=[round(size[0] * 3), round(size[1] * 3)], source=src, file=f, status="done", owner="characters",
                 notes=notes + (f" Replaces {old} (slot) at A4's mapping step." if old else " New (the balloon event)."))
        e.update({k: v for k, v in extra.items()})
        ents.append(e)
    json.dump(dict(version=1, title="R2 CAST lane entries (D1 cast; scratch manifest for art_batch / manifest_sheets / "
                                     "manifest_check --lanes; the art director merges them into art/MANIFEST.json; the ids they "
                                     "replace are named in each entry's notes and in art/lanes/cast.handoff.json)",
                   entries=ents), open("art/lanes/cast.entries.json", "w"), indent=1)
    print(len(ents), "entries -> art/lanes/cast.entries.json")


if __name__ == "__main__":
    cmd, args = sys.argv[1], sys.argv[2:]
    {"recompose": lambda: cmd_recompose(), "idle": lambda: cmd_idle(), "home": lambda: cmd_home(),
     "loading": lambda: cmd_loading(), "profile": lambda: cmd_profile(), "manifest": lambda: cmd_manifest(), "overlap": lambda: cmd_overlap(),
     "sheet": lambda: [cmd_sheet(a) for a in args]}[cmd]()
