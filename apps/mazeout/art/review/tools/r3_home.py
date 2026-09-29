#!/usr/bin/env python3
"""R3 HOME proofs (PLAN-P §4.2; owner items 4 + 15; SPEC ruling 46). Sheets -> art/review/home/, numbers ->
art/review/home/proofs.json. Research shots are LOOKED AT only (copygate thumbnails).

    PY=~/.venvs/mf3d/bin/python        # from apps/mazeout
    $PY art/review/tools/r3_home.py compose [--state claw|plain|both]   # the composed home at real size + copygate vs 002
    $PY art/review/tools/r3_home.py overlap                             # signpost boards pairwise (mesh samples vs SDF)
    $PY art/review/tools/r3_home.py signpost                            # export home_signpost_rig from the renders
    $PY art/review/tools/r3_home.py badges                              # export the 3 badge rigs from their renders
    $PY art/review/tools/r3_home.py idle                                # the signpost + badge loops, every 1/30 s: holes
    $PY art/review/tools/r3_home.py rects                               # UI rects vs the art's reserved regions
    $PY art/review/tools/r3_home.py sheet                               # review sheets (1x, 1/3 thumbnails, real size)
    $PY art/review/tools/r3_home.py manifest                            # art/lanes/home.entries.json (scratch manifest)

The composition is today's (ruling 46): back -> front = homeWorkshop, boss torso+head, homeScaffold, boss arms, homeFloor,
homeCabinet + the signpost rig, LEVEL plate + Play (UI), the two Diggers, the top bar, the Claw bar + badges, the nav.
UI rects come from ui.json frames.home (never moved); the UI itself is a MOCK in D1 tokens (A5's codemod does the real one).
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import sys

APP = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
os.chdir(APP)
for p in ("tools", "art/ui/recipes", "art/ui/tools", "art/pipeline", "art/pipeline/items"):
    sys.path.insert(0, os.path.join(APP, p))

import numpy as np  # noqa: E402
from PIL import Image, ImageDraw, ImageFilter, ImageFont  # noqa: E402

S = 3
OUT = "art/out"
UIOUT = "art/ui/out"
DST = "art/review/home"
EV = "build/p/R3"
os.makedirs(DST, exist_ok=True)
os.makedirs(EV, exist_ok=True)
PROOFS = os.path.join(DST, "proofs.json")
THEIRS = "research/shots/002-home-L32.png"
UI = json.load(open("App/Resources/Tuning/ui.json"))
FR = UI["frames"]["home"]

# the boss at today's (centred) spot: ruling 46 keeps the composition; eyeMid = the scientist's (205.84, 212.51)
BOSS_PLACE = (109.0, 176.0)      # whole pt (homeScaffold registers to the pixel); art/lanes/home.handoff.json


def img(p):
    return Image.open(p).convert("RGBA")


def paste_pt(cv, im, x, y):
    cv.alpha_composite(im, (round(x * S), round(y * S)))


def save_proof(key, val):
    d = json.load(open(PROOFS)) if os.path.exists(PROOFS) else {}
    d[key] = val
    json.dump(d, open(PROOFS, "w"), indent=1)


def font(n):
    return ImageFont.truetype("App/Resources/Fonts/PCDisplay-Black.ttf", round(n * S))


# ------------------------------------------------------------------ rigs (R2's cast)

def rig_dir(name):
    return f"{OUT}/{name}"


def rig_compose(name, keep=None, t=None):
    """Default layers (or those `keep(name)` accepts) at rect_pt, on a frame-size canvas."""
    d = rig_dir(name)
    rj = json.load(open(f"{d}/rig.json"))
    W, H = rj["frame_pt"]
    defaults = {g["default"] for g in rj.get("groups", {}).values()}
    cv = Image.new("RGBA", (round(W * S), round(H * S)), (0, 0, 0, 0))
    for L in sorted(rj["layers"], key=lambda l: l["z"]):
        if L.get("overlay") or (L.get("group") and L["name"] not in defaults):
            continue
        if keep and not keep(L["name"]):
            continue
        cv.alpha_composite(img(f"{d}/{L['file']}"), (round(L["rect_pt"][0] * S), round(L["rect_pt"][1] * S)))
    return cv, rj


# ------------------------------------------------------------------ the scene pieces (real renders, else labelled drafts)

def _cached_paint():
    """homeWorkshop's painted structure (50 s at 3x) cached by the recipe's hash (the proof uses the SHIPPED file when
    it exists)."""
    src = open("art/ui/recipes/scene_home_d1.py", "rb").read()
    key = hashlib.sha1(src).hexdigest()[:12]
    p = f"{EV}/paint_{key}.png"
    if not os.path.exists(p):
        import scene_home_d1 as H
        H.paint_workshop().image().save(p)
    return img(p)


def piece(name, draft):
    for p in (f"{OUT}/{name}@3x.png", f"{UIOUT}/{name}@3x.png", f"build/ui-art/scene/draft/{name}.png"):
        if os.path.exists(p):
            return img(p), True
    return draft(), False


def draft_cabinet():
    """Placeholder for homeCabinet + the signpost (flat shapes at the cabinet frame), until the renders land."""
    x0, y0 = 95, 365
    cv = Image.new("RGBA", (206 * S, 215 * S), (0, 0, 0, 0))
    d = ImageDraw.Draw(cv)

    def rr(a, b, c, e, r, fill, outline=None, w=0):
        d.rounded_rectangle(((a - x0) * S, (b - y0) * S, (c - x0) * S, (e - y0) * S), r * S, fill=fill, outline=outline,
                            width=round(w * S))
    rr(130, 500, 262, 577, 16, (0xC9, 0x8A, 0x4A), (0x6A, 0x3E, 0x1C), 2)
    rr(100, 381, 290, 518, 24, (0xC9, 0x8A, 0x4A), (0x6A, 0x3E, 0x1C), 2.5)
    rr(110, 391, 280, 508, 16, (0xD8, 0xA4, 0x41))
    rr(116, 397, 274, 502, 12, (0x16, 0x2C, 0x2E))
    rr(147.5, 536.8, 245.9, 569.2, 12, (0x3E, 0x24, 0x10))
    d.ellipse(((196 - 13 - x0) * S, (398 - y0) * S, (196 + 13 - x0) * S, (424 - y0) * S), fill=(0xFF, 0xCF, 0x6B))
    rr(192, 420, 200, 502, 2, (0x9A, 0x61, 0x30))
    cols = [(0xFF, 0x8F, 0x1F), (0xFF, 0xC5, 0x26), (0x3F, 0xC3, 0x9C), (0xF2, 0x55, 0x3F), (0x7F, 0xE6, 0xFF)]
    for i, (yy, side) in enumerate(((430, 1), (448, -1), (466, 1), (484, -1), (499, 1))):
        a, b = (200, 262) if side > 0 else (130, 192)
        rr(a, yy - 7, b, yy + 7, 4, cols[i])
    return cv


def draft_floor():
    cv = Image.new("RGBA", (393 * S, 182 * S), (0, 0, 0, 0))
    d = ImageDraw.Draw(cv)
    d.ellipse(((-12) * S, (584 - 576) * S, 405 * S, (750 - 576) * S), fill=(0x6A, 0x3E, 0x1C))
    d.ellipse(((-4) * S, (590 - 576) * S, 397 * S, (742 - 576) * S), fill=(0xC9, 0x8A, 0x4A))
    return cv


def scaffold_image():
    """homeScaffold when rendered, else R2's char_bossStation (the rig camera; rail clipped at the frame)."""
    p = f"{OUT}/homeScaffold@3x.png"
    if os.path.exists(p):
        return img(p), True
    return img("build/ui-art/route3d/char_bossStation.png"), False


# ------------------------------------------------------------------ the UI mock (D1 tokens, unchanged rects)

TEAL, RIM, DARK = (0x17, 0xB3, 0xA3), (0x0B, 0x8A, 0x83), (0x05, 0x3F, 0x43)
TANG, TANG2, CREAM = (0xFF, 0xB4, 0x22), (0xD0, 0x6A, 0x06), (0xFF, 0xFB, 0xEF)
PILL = (0xD4, 0xF4, 0xEC)


def ui_mock(cv, claw=True, badges=("streak", "rocket", "sky"), nav_art=None, badge_art=None):
    """The home UI at ui.json's rects as flat D1-token shapes (a MOCK of A5's codemod output) + the real raster icons
    (coin, heart, gear glyph; the nav icons / event badges passed in = R3's new art)."""
    dr = ImageDraw.Draw(cv)

    def rr(r, rad, fill, outline=None, width=0):
        x, y, w, h = r
        dr.rounded_rectangle((x * S, y * S, (x + w) * S, (y + h) * S), rad * S, fill=fill, outline=outline, width=round(width * S))
    rr(FR["avatarButton"], 13, TEAL, DARK, 2.5)
    a = FR["avatarButton"]
    rr((a[0] + 9, a[1] + 9, a[2] - 18, a[3] - 18), 8, (150, 170, 176))
    rr(FR["coinPill"], 13.7, PILL, DARK, 2)
    rr(FR["livesPill"], 13.7, PILL, DARK, 2)
    rr(FR["gearButton"], 11, TEAL, DARK, 2.5)
    for art, key in (("iconCoin", "coinIconArt"), ("iconPlusGreen", "plusBadgeArt"), ("heartLives", "livesHeartArt"),
                     ("glyphGear", "gearButton")):
        p = f"{UIOUT}/{art}@3x.png"
        if os.path.exists(p):
            x, y, w, h = FR[key]
            im = img(p).resize((round(w * S), round(h * S)), Image.LANCZOS)
            if art == "glyphGear":
                im = img(p)
                im = im.resize((round(im.width * 0.62), round(im.height * 0.62)), Image.LANCZOS)
                cv.alpha_composite(im, (round((x + w / 2) * S - im.width / 2), round((y + h / 2) * S - im.height / 2)))
                continue
            cv.alpha_composite(im, (round(x * S), round(y * S)))
    dr.text(((FR["coinPill"][0] + 45) * S, (FR["coinPill"][1] + 13.7) * S), "2240", font=font(19), fill=DARK, anchor="mm")
    dr.text(((FR["livesPill"][0] + 44) * S, (FR["livesPill"][1] + 13.7) * S), "Full", font=font(19), fill=DARK, anchor="mm")
    if claw:
        x, y, w, h = FR["clawBar"]
        rr((x, y, w, h), h / 2, (0x0B, 0x5A, 0x55), DARK, 2)
        rr((x + 40, y + 6, 150, h - 12), (h - 12) / 2, TANG)
        dr.text(((x + w / 2) * S, (y + h / 2) * S), "0/1", font=font(18), fill=CREAM, anchor="mm", stroke_width=round(1.2 * S),
                stroke_fill=DARK)
    slots = [190.8, 293.6, 390.3]
    lift = 0 if claw else 73.4
    for i, b in enumerate(badges):
        y = slots[i] - lift - 0.6
        if badge_art and b in badge_art:
            cv.alpha_composite(badge_art[b], (round(6.7 * S), round(y * S)))
        else:
            dr.ellipse((14 * S, (y + 6) * S, 90 * S, (y + 82) * S), fill=TEAL, outline=DARK, width=3 * S)
        dr.text((47.3 * S, (y + 71) * S), "9h 42m" if b == "streak" else "Join", font=font(12), fill=CREAM, anchor="mm",
                stroke_width=round(1.0 * S), stroke_fill=DARK)
    # LEVEL caption + plate
    x, y, w, h = FR["levelPlate"]
    rr((x, y, w, h), 12, (0xE3, 0xA5, 0x5B), (0x6A, 0x35, 0x10), 2.2)
    rr((x + 3, y + 3, w - 6, h / 2 - 2), 9, (0xF2, 0xC2, 0x7E))
    dr.text(((x + w / 2) * S, (FR["levelCaption"][1] + 8.3) * S), "LEVEL", font=font(13), fill=CREAM, anchor="mm",
            stroke_width=round(1.2 * S), stroke_fill=(0x6A, 0x35, 0x10))
    dr.text(((x + w / 2) * S, (y + h / 2 + 1) * S), "32", font=font(27), fill=CREAM, anchor="mm", stroke_width=round(1.6 * S),
            stroke_fill=(0x6A, 0x35, 0x10))
    # Play
    x, y, w, h = FR["playFrame"]
    rr((x, y, w, h), 36, (0x0B, 0x8A, 0x83), DARK, 2.5)
    x, y, w, h = FR["playButton"]
    rr((x, y, w, h), 30, TANG2)
    rr((x + 3, y + 2, w - 6, h - 9), 28, TANG)
    rr((x + 14, y + 7, w - 28, 22), 11, (0xFF, 0xD2, 0x6A))
    dr.text(((x + w / 2) * S, (y + h / 2) * S), "Play", font=font(50), fill=CREAM, anchor="mm", stroke_width=round(2.6 * S),
            stroke_fill=(0x8A, 0x3F, 0x00))
    # nav
    x, y, w, h = FR["navBar"]
    dr.rectangle((0, y * S, 393 * S, 852 * S), fill=TEAL)
    dr.rectangle((0, y * S, 393 * S, (y + 3) * S), fill=DARK)
    rr(FR["navHomeTab"], 16, (0x7F, 0xEA, 0xDB), DARK, 2.5)
    if nav_art:
        for key, im in nav_art.items():
            x, y, w, h = FR[key]
            cv.alpha_composite(im.resize((round(w * S), round(h * S)), Image.LANCZOS), (round(x * S), round(y * S)))
    t = FR["navHomeTab"]
    dr.text(((t[0] + t[2] / 2) * S, 818 * S), "Home", font=font(15), fill=CREAM, anchor="mm", stroke_width=round(1.2 * S),
            stroke_fill=DARK)
    return cv


# ------------------------------------------------------------------ composition

R9_HOME = "build/p/R9/preview/home-L32-mapped.png"


def ui_r9(cv, claw=True, badges=("streak",), nav_art=None, badge_art=None):
    """UI variant 2 for the gate: the home UI as R9's palette map renders it (build/p/R9/preview/home-L32-mapped.png, a
    1x preview of A5's codemod on today's capture), cut out at ui.json's rects and pasted over the scene, + R3's own
    nav icons and badges. A second opinion next to the flat mock (neither is the final A5 UI)."""
    src = Image.open(R9_HOME).convert("RGBA").resize((393 * S, 852 * S), Image.LANCZOS)

    def cut(r, pad=1.5, rad=10):
        x, y, w, h = r
        box = (round((x - pad) * S), round((y - pad) * S), round((x + w + pad) * S), round((y + h + pad) * S))
        im = src.crop(box)
        m = Image.new("L", im.size, 0)
        ImageDraw.Draw(m).rounded_rectangle((0, 0, im.width - 1, im.height - 1), round(rad * S), fill=255)
        cv.paste(im, box[:2], m)
    for k, rad in (("avatarButton", 14), ("gearButton", 12), ("coinPill", 13), ("livesPill", 13), ("coinIconArt", 19),
                   ("livesHeartArt", 16), ("plusBadgeArt", 11), ("levelPlate", 12), ("levelCaption", 4), ("playFrame", 36)):
        cut(FR[k], rad=rad)
    x, y, w, h = FR["navBar"]
    band = src.crop((0, round(y * S), 393 * S, 852 * S))
    cv.paste(band, (0, round(y * S)))
    cut(FR["navHomeTab"], pad=0.5, rad=16)
    if nav_art:
        # R9's preview still carries today's icons: clear their boxes to the bar colour before R3's icons go on
        dr0 = ImageDraw.Draw(cv)
        for key in ("navShop", "navTrophy"):
            bx, by, bw, bh = FR[key]
            col = src.getpixel((round((bx - 4) * S), round((by + bh / 2) * S)))
            dr0.rounded_rectangle((bx * S, by * S, (bx + bw) * S, (by + bh) * S), 8 * S, fill=col)
    if claw:
        dr = ImageDraw.Draw(cv)
        x, y, w, h = FR["clawBar"]
        dr.rounded_rectangle((x * S, y * S, (x + w) * S, (y + h) * S), h / 2 * S, fill=(0x0B, 0x5A, 0x55), outline=DARK, width=2 * S)
        dr.rounded_rectangle(((x + 40) * S, (y + 6) * S, (x + 190) * S, (y + h - 6) * S), (h - 12) / 2 * S, fill=TANG)
    slots = [190.8, 293.6, 390.3]
    lift = 0 if claw else 73.4
    for i, b in enumerate(badges):
        if badge_art and b in badge_art:
            cv.alpha_composite(badge_art[b], (round(6.7 * S), round((slots[i] - lift - 0.6) * S)))
    if nav_art:
        for key, im in nav_art.items():
            x, y, w, h = FR[key]
            cv.alpha_composite(im.resize((round(w * S), round(h * S)), Image.LANCZOS), (round(x * S), round(y * S)))
    return cv


def workshop():
    p = f"{OUT}/homeWorkshop@3x.png"
    if os.path.exists(p):
        return img(p), True
    return _cached_paint(), False


def compose(state="claw", with_ui=True, t=None, extra=None, ui="mock"):
    """The composed home (1179 x 2556 px). Returns (image, notes: which pieces are drafts)."""
    notes = {}
    wall, ok = workshop()
    notes["homeWorkshop"] = ok
    cv = wall.copy()
    if extra and extra.get("objects") is not None:
        cv.alpha_composite(extra["objects"])
    bx, by = BOSS_PLACE
    th, _ = rig_compose("char_boss_home_rig", keep=lambda n: not n.startswith("arm"))
    paste_pt(cv, th, bx, by)
    sc, ok = scaffold_image()
    notes["homeScaffold"] = ok
    if ok:
        x, y, _, _ = SCAFFOLD_FRAME
        paste_pt(cv, sc, x, y)
    else:
        paste_pt(cv, sc, bx, by)
    ar, _ = rig_compose("char_boss_home_rig", keep=lambda n: n.startswith("arm"))
    paste_pt(cv, ar, bx, by)
    fl, ok = piece("homeFloor", draft_floor)
    notes["homeFloor"] = ok
    paste_pt(cv, fl, 0, 576)
    cab, ok = piece("homeCabinet", draft_cabinet)
    notes["homeCabinet"] = ok
    paste_pt(cv, cab, 95, 365)
    sp = signpost_full()
    notes["homeSignpost"] = sp is not None
    if sp is not None:
        paste_pt(cv, sp[0], *sp[1])
    ui_layer = Image.new("RGBA", cv.size, (0, 0, 0, 0))
    for rig in ("char_dig_homeL_rig", "char_dig_homeR_rig"):
        r, rj = rig_compose(rig)
        pl = rj["placement_pt"]
        paste_pt(cv, r, pl["x"], pl["y"])
    if with_ui:
        badges = ("streak", "rocket", "sky") if state == "claw" else ("streak",)
        fn = ui_r9 if ui == "r9" else ui_mock
        cv = fn(cv, claw=(state == "claw"), badges=badges, nav_art=nav_images(), badge_art=badge_images())
    return cv, notes


SCAFFOLD_FRAME = (109, 176, 191, 192)     # homeScaffold's frame (pt) = scene_home_d1.F_SCAFFOLD


def signpost_full():
    d = f"{OUT}/home_signpost_rig"
    if not os.path.exists(f"{d}/rig.json"):
        return None
    im, rj = rig_compose("home_signpost_rig")
    return im, (rj["placement_pt"]["x"], rj["placement_pt"]["y"])


def nav_images():
    out = {}
    for key, art in (("navShop", "navCart"), ("navHomeIcon", "navLodge"), ("navTrophy", "navCup")):
        p = f"{UIOUT}/{art}@3x.png"
        if os.path.exists(p):
            out[key] = img(p)
    return out


def badge_images():
    out = {}
    for k, art in (("streak", "badgeHotStreak"), ("rocket", "badgeRocketRally"), ("sky", "badgeCloudHop")):
        p = f"{OUT}/{art}@3x.png"
        if os.path.exists(p):
            out[k] = img(p)
    return out


def gate(ours, theirs=THEIRS, kind="screen", crop=None):
    import copygate as CG
    cfg = CG.load_config()
    m = CG.measure(ours, theirs, crop=crop, cmin=CG.kind_cmin(cfg, kind))
    j = CG.judge(m, kind, cfg)
    return dict(ours=ours, theirs=theirs, kind=kind, crop=crop, ssim=round(m["ssim"], 3), overlap=round(m["overlap"], 3),
                pass_=j["pass"])


def cmd_compose(states=("claw", "plain")):
    res = []
    notes = None
    for st in states:
        cv, notes = compose(st)
        dst = f"{DST}/home-{st}.png"
        cv.convert("RGB").save(dst, optimize=True)
        cv.convert("RGB").resize((393, 852), Image.LANCZOS).save(f"{DST}/home-{st}-1x.png")
        res.append(dict(state=st, **gate(dst)))
        cv2, _ = compose(st, ui="r9")
        dst2 = f"{DST}/home-{st}-r9ui.png"
        cv2.convert("RGB").save(dst2, optimize=True)
        res.append(dict(state=st + " (UI = R9's palette-map preview)", **gate(dst2)))
        res.append(dict(state=st + " scene band y152-618", **gate(dst, crop=[0, 152, 393, 466])))
        noui, _ = compose(st, with_ui=False)
        p2 = f"{EV}/home-{st}-noui.png"
        noui.convert("RGB").save(p2)
        res.append(dict(state=st + " (no UI: the art alone)", **gate(p2)))
    for r in res:
        print(r)
    save_proof("compose", dict(note="the composed home at real size (1179 x 2556) vs 002 (v552 home), kind screen: "
                                    "SSIM < 0.30 and chroma overlap < 0.55. The UI is a D1-token MOCK at ui.json's rects.",
                               pieces_rendered=notes, gates=res))
    return res


def placeholder_objects():
    """DRAFT ONLY (planning, never shipped): today's wall-object render with its blues / lilacs pushed to copper / brass,
    to stand in for homeWorkshop's objects until the D1 objects render lands."""
    im = img("build/ui-art/scene/raw/homeObjects.png").resize((1179, 2556), Image.LANCZOS)
    a = np.asarray(im).astype(np.float64) / 255
    rgb_ = a[..., :3]
    l = rgb_ @ np.array([0.299, 0.587, 0.114])
    cu = np.array([0.80, 0.46, 0.24])
    br = np.array([0.85, 0.65, 0.27])
    out = np.clip((cu * 0.55 + br * 0.45)[None, None] * (0.35 + 1.1 * l[..., None]), 0, 1)
    a[..., :3] = out
    return Image.fromarray((a * 255).astype(np.uint8), "RGBA")


def cmd_overlap(voxel=0.008):
    """Item 4's gate: every arrow board (core + painted faces) of the signpost vs every other board, the post (with its
    foot, band and finial), the lantern and the other boards' brackets: surface samples of one (marching cubes at
    `voxel` u) evaluated in the other's SDF. PASS = no sample inside another solid (min signed distance >= 0; 1 u = 40
    pt, so 0.001 u = 0.04 pt). A board's own bracket is its mount and is not tested against the post it is bolted to."""
    import char_home_signpost as HS
    from mesher import mc_mesh
    from uikit import union
    tuples = HS.all_parts()
    by = {n: s_ for n, s_, _, _ in tuples}
    solids = {f"board{i + 1}": union(by[f"board{i + 1}"], by[f"boardFace{i + 1}"]) for i in range(len(HS.BOARDS))}
    others = dict(solids)
    others["post"] = union(by["post"], by["postBand"], by["finial"], by["foot"])
    others["lantern"] = union(by["lanternBrass"], by["lanternGlass"])
    brackets = {f"bracket{i + 1}": union(by[f"bracket{i + 1}"], by[f"bolts{i + 1}"]) for i in range(len(HS.BOARDS))}
    pairs, worst = {}, 1e9
    samples = {}
    for a, sa in list(solids.items()) + [("lantern", others["lantern"])] + list(brackets.items()):
        v, _ = mc_mesh(sa, voxel)
        samples[a] = np.asarray(v, np.float32)
    for a, va in samples.items():
        for b, sb in others.items():
            if a == b or (a.startswith("bracket") and b == "post") or (a.startswith("bracket") and b == "board" + a[7:]):
                continue
            d = float(sb(va).min())
            pairs[f"{a}->{b}"] = round(d, 4)
            worst = min(worst, d)
    ok = worst >= 0.0
    res = dict(boards=len(solids), samples={k: int(len(v)) for k, v in samples.items()}, voxel_u=voxel, pt_per_u=HS.SCALE_PT,
               min_signed_distance_u=round(worst, 4), min_clearance_pt=round(worst * HS.SCALE_PT, 2), pass_=bool(ok),
               closest=sorted(pairs.items(), key=lambda kv: kv[1])[:6])
    print(json.dumps(res, indent=1))
    save_proof("overlap", dict(note="signpost: every board vs every other board, the post, the lantern; every bracket vs "
                                    "the other boards (its own board and the post are its mount). PASS = no surface sample "
                                    "inside another solid.", **res, pairs=pairs))
    # the heap it replaces, for the record: today's pile would fail (scene_home.pile_layout, no penetration test)
    return ok


# ------------------------------------------------------------------ motion data (proposed ui.json puppet blocks)

def _extreme_keys(period, amp, phase, cycle, t0=0.0, t1=None):
    """Sine-like keyframes for PuppetStage ('sine' = easeInOutSine per segment): keys at the extremes (+-amp) of a wave of
    `period` with `phase` (fraction of a period), plus the cycle ends at the wave's value there (the loop closes because
    the active span holds a whole number of periods, or the wave is parked at 0 outside [t0, t1])."""
    t1 = cycle if t1 is None else t1
    ts, vs = [0.0], [0.0 if t0 > 0 else round(amp * math.sin(2 * math.pi * phase), 3)]
    if t0 > 0:
        ts.append(round(t0, 3)); vs.append(0.0)
    k = math.ceil((t0 / period - phase) * 2 - 0.5)
    while True:
        tk = (k / 2 + 0.25 - phase) * period
        if tk >= t1 - 1e-6:
            break
        if tk > t0 + 1e-6:
            ts.append(round(tk, 3)); vs.append(round(amp * (1 if k % 2 == 0 else -1), 3))
        k += 1
    if t1 < cycle:
        ts.append(round(t1, 3)); vs.append(0.0)
    ts.append(round(cycle, 3)); vs.append(vs[0])
    return ts, vs


def signpost_tracks(rj):
    """home_signpost_rig idle: every board sways +-2 deg about its hinge on its own period (art-direction §4.3: 2.8-3.6 s,
    desynchronised) -- the cycle is 36 s so each period fits a whole number of times (13 / 12 / 11 / 10 / 12 waves);
    the lantern swings +-3 deg about its hook on a 3.6 s period."""
    cycle = 36.0
    # t = 0 sits on an extreme of every wave (phase 0.25 / 0.75), so every key is an extreme and the loop is seamless
    per = {"board1": (36 / 13, 0.25), "board2": (3.0, 0.75), "board3": (36 / 11, 0.75), "board4": (3.6, 0.25), "board5": (36 / 12, 0.25)}
    tracks = []
    piv = {L["name"]: L.get("pivots_pt", {}) for L in rj["layers"]}
    for name, (P_, ph) in per.items():
        ts, vs = _extreme_keys(P_, 2.0, ph, cycle)
        tracks.append(dict(layer=name, prop="rotation", t=ts, v=vs, curve="sine", pivot=piv[name]["hinge"]))
    ts, vs = _extreme_keys(3.6, 3.0, 0.75, cycle)
    tracks.append(dict(layer="lantern", prop="rotation", t=ts, v=vs, curve="sine", pivot=piv["lantern"]["hook"]))
    return dict(cycle=cycle, tracks=tracks)


def signpost_refill(rj, duration=1.2):
    """The refill (one-shot; HomeScene.requestRefill() / takeRefill() stay the trigger, 1.2 s = home.pileRefill): the
    boards start hidden (scaleX 0 about the hinge) and flip in one after another, top to bottom, 0.15 s each with a 6 %
    overshoot (scaleX 0 -> 1.06 -> 1.0, keyTimes 0 / 0.7 / 1, easeOut), a light haptic tick as each lands; then the post
    knocks once (base translateY 0 -> +1.2 -> 0 pt over 0.12 s). Needs a `scaleX` key path (transform.scale.x) in
    HomeCentrepiece (PuppetStage has rotation / scaleY / translateY)."""
    piv = {L["name"]: L.get("pivots_pt", {}) for L in rj["layers"]}
    boards = [L["name"] for L in rj["layers"] if L["name"].startswith("board")]
    steps = []
    for i, b in enumerate(boards):
        start = round(0.10 + i * 0.18, 3)
        steps.append(dict(layer=b, prop="scaleX", pivot=piv[b]["hinge"], begin=start, duration=0.15, values=[0.0, 1.06, 1.0],
                          keyTimes=[0.0, 0.7, 1.0], curve="easeOut", haptic=dict(at=round(start + 0.105, 3), kind="light", intensity=0.45)))
    knock_at = round(0.10 + len(boards) * 0.18 + 0.02, 3)
    return dict(duration=duration, hiddenAtStart=boards, steps=steps,
                knock=dict(layer="base", prop="translateY", begin=knock_at, duration=0.12, values=[0.0, 1.2, 0.0],
                           keyTimes=[0.0, 0.35, 1.0], curve="easeInOut"))


def badge_tracks(kind, rj):
    """v582 home idle (motion-catalog §11.5, §6.4): Hot Streak pennants flutter (1.25 s) for 10 s of a 16 s cycle; the
    Rocket Rally rocket lifts 8 pt (up 0.55 s, hold 1.0 s, down 0.75 s) every 12 s with a flickering exhaust; the Cloud
    Hop drum hops 5 pt (0.25 s up easeOut, 0.25 s down easeIn) in bursts, the clouds bob +-0.8 pt."""
    piv = {L["name"]: L.get("pivots_pt", {}) for L in rj["layers"]}
    if kind == "hotstreak":
        cycle = 16.0
        tl, vl = _extreme_keys(1.25, 4.0, 0.0, cycle, t0=1.0, t1=11.0)
        tr_, vr = _extreme_keys(1.25, -4.0, 0.12, cycle, t0=1.0, t1=11.0)
        return dict(cycle=cycle, tracks=[dict(layer="pennantL", prop="rotation", t=tl, v=vl, curve="sine", pivot=piv["pennantL"]["pole"]),
                                         dict(layer="pennantR", prop="rotation", t=tr_, v=vr, curve="sine", pivot=piv["pennantR"]["pole"])])
    if kind == "rocketrally":
        cycle = 12.0
        t = [0.0, 1.90, 2.45, 3.45, 4.20, 12.0]
        v = [0.0, 0.0, -8.0, -8.0, 0.0, 0.0]
        curves = ["linear", "sineOut", "linear", "sine", "linear"]
        tracks = [dict(layer="rocket", prop="translateY", t=t, v=v, curve=curves),
                  dict(layer="exhaustA", prop="translateY", t=t, v=v, curve=curves),
                  dict(layer="exhaustB", prop="translateY", t=t, v=v, curve=curves)]
        ft, fv = [0.0, 1.70], ["", "exhaustA"]
        x = 1.80
        while x < 4.30:
            ft.append(round(x, 2)); fv.append("exhaustB" if len(fv) % 2 == 0 else "exhaustA"); x += 0.10
        ft.append(4.30); fv.append("")
        tracks.append(dict(layer="exhaust", prop="overlay", t=ft, v=fv, curve="discrete"))
        return dict(cycle=cycle, tracks=tracks)
    if kind == "cloudhop":
        cycle = 12.0
        hops = [1.2, 2.1, 3.0, 4.6, 5.8, 7.0, 7.9, 8.8]
        t, v, c = [0.0], [0.0], []
        for h in hops:
            t += [h, round(h + 0.25, 3), round(h + 0.5, 3)]
            v += [0.0, -5.0, 0.0]
            c += ["linear", "sineOut", "sineIn"]
        t.append(cycle); v.append(0.0); c.append("linear")
        ct, cv_ = _extreme_keys(4.0, 0.8, 0.1, cycle)
        return dict(cycle=cycle, tracks=[dict(layer="drum", prop="translateY", t=t, v=v, curve=c),
                                         dict(layer="clouds", prop="translateY", t=ct, v=cv_, curve="sine")])
    raise KeyError(kind)


BADGES = [("hotstreak", "badgeHotStreak", "eventBadgeStreak", "streakRace"),
          ("rocketrally", "badgeRocketRally", "eventBadgeRocket", "rocketRace"),
          ("cloudhop", "badgeCloudHop", "eventBadgeSkyJump", "skyJump")]


def _paint_exhaust(W, H, cx, y0, variant):
    """The rocket's exhaust (painted, like 3d-events_badges.flame): a white-yellow core under the nozzle, tangerine
    puffs, cream smoke puffs spreading on the pedestal. variant 0 / 1 = the two flicker frames."""
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    s = S
    rng = np.random.default_rng(11 + variant)
    k = 1.0 + 0.12 * variant
    smoke = [(-9.5, 7.5, 5.2), (9.0, 7.0, 5.0), (-4.5, 9.5, 5.8), (4.8, 9.8, 5.6), (-14.0, 5.5, 3.6), (13.5, 5.2, 3.4)]
    for dx, dy, r in smoke:
        r2 = r * (1.0 + 0.08 * variant)
        d.ellipse([cx + (dx - r2) * s, y0 + (dy - r2) * s, cx + (dx + r2) * s, y0 + (dy + r2) * s], fill=(0xF6, 0xEC, 0xDC, 215))
    lay = lay.filter(ImageFilter.GaussianBlur(0.8 * s))
    fl = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d2 = ImageDraw.Draw(fl)
    for dx, dy, r, col in [(0, 3.0 * k, 5.4, (255, 128, 30, 235)), (-2.4, 5.4 * k, 3.6, (255, 150, 40, 225)),
                           (2.2, 5.8 * k, 3.4, (255, 140, 36, 225))]:
        d2.ellipse([cx + (dx - r) * s, y0 + (dy - r) * s, cx + (dx + r) * s, y0 + (dy + r) * s], fill=col)
    fl = fl.filter(ImageFilter.GaussianBlur(0.7 * s))
    core = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d3 = ImageDraw.Draw(core)
    for dx, dy, r, col in [(0, 2.2 * k, 3.6, (255, 226, 120, 255)), (0, 3.6 * k, 2.6, (255, 250, 228, 255))]:
        d3.ellipse([cx + (dx - r) * s, y0 + (dy - r) * s, cx + (dx + r) * s, y0 + (dy + r) * s], fill=col)
    core = core.filter(ImageFilter.GaussianBlur(0.5 * s))
    lay.alpha_composite(fl)
    lay.alpha_composite(core)
    del rng
    return lay


def cmd_badges():
    """After rig.py exported the badge rigs: add the rocket's two painted exhaust overlays (flicker pair) behind the
    rocket, record the live-text anchors, write the proposed motion into each rig dir's motion.json (A4 copies it to
    ui.json puppet.<rig>)."""
    out = {}
    for kind, full, old, event in BADGES:
        d = f"{OUT}/badge_{kind}_rig"
        if not os.path.exists(f"{d}/rig.json"):
            print("missing", d)
            continue
        rj = json.load(open(f"{d}/rig.json"))
        if kind == "rocketrally" and not any(L["name"].startswith("exhaust") for L in rj["layers"]):
            noz = next(L for L in rj["layers"] if L["name"] == "rocket")["pivots_pt"]["nozzle"]
            W, H = [round(v * S) for v in rj["frame_pt"]]
            new = []
            for vi, nm in enumerate(("exhaustA", "exhaustB")):
                im = _paint_exhaust(W, H, noz[0] * S, (noz[1] - 0.4) * S, vi)
                bb = im.getbbox()
                im.crop(bb).save(f"{d}/{nm}@3x.png", optimize=True)
                new.append(dict(name=nm, file=f"{nm}@3x.png", rect_pt=[round(bb[0] / S, 3), round(bb[1] / S, 3),
                                                                       round((bb[2] - bb[0]) / S, 3), round((bb[3] - bb[1]) / S, 3)],
                                pivots_pt={"nozzle": noz}, overlay=True, parent="rocket",
                                note="painted exhaust (flicker frame): shown by the overlay track during the lift-off, "
                                     "moves with the rocket (same translateY track)"))
            layers = [rj["layers"][0]] + new + rj["layers"][1:]
            for z, L in enumerate(layers):
                L["z"] = z
            rj["layers"] = layers
            json.dump(rj, open(f"{d}/rig.json", "w"), indent=1)
        mot = badge_tracks(kind, rj)
        json.dump(mot, open(f"{d}/motion.json", "w"), indent=1)
        side = json.load(open(f"{OUT}/{full}.json")) if os.path.exists(f"{OUT}/{full}.json") else {}
        out[kind] = dict(rig=f"badge_{kind}_rig", full=full, replaces=old, event=event,
                         layers=[(L["name"], L.get("overlay", False)) for L in rj["layers"]], anchors=side)
        print(kind, out[kind])
    save_proof("badges", out)


def cmd_signpost_motion():
    d = f"{OUT}/home_signpost_rig"
    rj = json.load(open(f"{d}/rig.json"))
    json.dump(dict(idle=signpost_tracks(rj), refill=signpost_refill(rj)), open(f"{d}/motion.json", "w"), indent=1)
    print("wrote", f"{d}/motion.json")


# ------------------------------------------------------------------ idle proof (PuppetStage's model, every 1/30 s)

def _bez(p1x, p1y, p2x, p2y, u):
    """CAMediaTimingFunction(controlPoints:) evaluated at x = u (Newton on the x curve)."""
    t = u
    for _ in range(8):
        x = 3 * (1 - t) ** 2 * t * p1x + 3 * (1 - t) * t * t * p2x + t ** 3
        dx = 3 * (1 - t) ** 2 * p1x + 6 * (1 - t) * t * (p2x - p1x) + 3 * t * t * (1 - p2x)
        if abs(dx) < 1e-6:
            break
        t = min(1, max(0, t - (x - u) / dx))
    return 3 * (1 - t) ** 2 * t * p1y + 3 * (1 - t) * t * t * p2y + t ** 3


CURVES = {"sine": (0.37, 0, 0.63, 1), "sineOut": (0.61, 1, 0.88, 1), "sineIn": (0.12, 0, 0.39, 0), "easeInOut": (0.42, 0, 0.58, 1),
          "linear": None}


def track_value(tr, t):
    ts, vs = tr["t"], tr["v"]
    if tr["prop"] in ("overlay", "member"):
        v = vs[0]
        for ti, vi in zip(ts, vs):
            if t >= ti:
                v = vi
        return v
    if t <= ts[0]:
        return vs[0]
    curves = tr["curve"] if isinstance(tr["curve"], list) else [tr["curve"]] * (len(ts) - 1)
    for i in range(len(ts) - 1):
        if ts[i] <= t <= ts[i + 1]:
            u = (t - ts[i]) / max(ts[i + 1] - ts[i], 1e-9)
            c = CURVES.get(curves[i])
            e = u if c is None else _bez(*c, u)
            return vs[i] + (vs[i + 1] - vs[i]) * e
    return vs[-1]


def pose_rig(d, rj, mot, t):
    """Compose the rig at time t with PuppetStage's semantics (rotation about the track pivot, additive translateY,
    one overlay at a time)."""
    W, H = rj["frame_pt"]
    rot, ty, piv, overlay = {}, {}, {}, ""
    for tr in mot["tracks"]:
        v = track_value(tr, t)
        if tr["prop"] == "overlay":
            overlay = v
        elif tr["prop"] == "rotation":
            rot[tr["layer"]] = v
            piv[tr["layer"]] = tr.get("pivot")
        elif tr["prop"] == "translateY":
            ty[tr["layer"]] = v
    cv = Image.new("RGBA", (round(W * S), round(H * S)), (0, 0, 0, 0))
    moved = {}
    for L in sorted(rj["layers"], key=lambda l: l["z"]):
        n = L["name"]
        if L.get("overlay") and n != overlay:
            continue
        lay = Image.new("RGBA", cv.size, (0, 0, 0, 0))
        lay.alpha_composite(img(f"{d}/{L['file']}"), (round(L["rect_pt"][0] * S), round(L["rect_pt"][1] * S)))
        if rot.get(n):
            p = piv[n]
            lay = lay.rotate(-rot[n], resample=Image.BICUBIC, center=(p[0] * S, p[1] * S))
        if ty.get(n):
            lay = lay.transform(lay.size, Image.AFFINE, (1, 0, 0, 0, 1, -ty[n] * S), resample=Image.BICUBIC)
        if rot.get(n) or ty.get(n):
            moved[n] = lay
        cv.alpha_composite(lay)
    return cv, moved


def cmd_idle(fps=30):
    """Every rig through its proposed loop at 30 fps: (signpost) every board stays inside the cabinet's window (its
    pixels over the cabinet's opaque frame / bezel = 0) and nothing leaves the rig frame; (badges) the moving layer
    stays inside the badge's 80 x 84 slot + the lift headroom; strips for the sheet."""
    res = {}
    # signpost
    d = f"{OUT}/home_signpost_rig"
    if os.path.exists(f"{d}/rig.json"):
        rj = json.load(open(f"{d}/rig.json"))
        mot = json.load(open(f"{d}/motion.json"))["idle"]
        pl = rj["placement_pt"]
        cab = img(f"{OUT}/homeCabinet@3x.png") if os.path.exists(f"{OUT}/homeCabinet@3x.png") else None
        W, H = rj["frame_pt"]
        win = None
        if cab is not None:
            # the window = the cabinet's interior: pixels INSIDE the bezel ring (flood from the window centre over the
            # non-frame pixels); frame / bezel = what a board must never cover
            ca = np.asarray(cab).astype(np.float32)
            lum = ca[..., :3] @ np.array([0.299, 0.587, 0.114])
            from scipy import ndimage
            x0, y0 = round((pl["x"] - 95) * S), round((pl["y"] - 365) * S)
            inner = np.zeros(lum.shape, bool)
            inner[round((396 - 365) * S):round((509 - 365) * S), round((117 - 95) * S):round((276 - 95) * S)] = True
            # the bezel / frame inside that box: brass + honey pixels (bright, warm) hugging the edge
            win = inner
            win_rig = np.zeros((round(H * S), round(W * S)), bool)
            ys0, xs0 = max(0, -y0), max(0, -x0)
            sub = win[max(0, y0):max(0, y0) + win_rig.shape[0], max(0, x0):max(0, x0) + win_rig.shape[1]]
            win_rig[ys0:ys0 + sub.shape[0], xs0:xs0 + sub.shape[1]] = sub
        worst_out, worst_frame, frames = 0, 0, []
        n = int(mot["cycle"] * fps)
        for i in range(0, n, 3):
            t = i / fps
            cv, moved = pose_rig(d, rj, mot, t)
            a = np.asarray(cv)[..., 3] > 24
            if win is not None:
                outside = a & ~win_rig
                worst_out = max(worst_out, int(outside.sum()))
            edge = a[0].any() or a[-1].any() or a[:, 0].any() or a[:, -1].any()
            worst_frame = max(worst_frame, int(edge))
            if i % (fps * 3) == 0:
                frames.append(cv)
        res["signpost"] = dict(cycle=mot["cycle"], samples=len(range(0, n, 3)), px_outside_window_max=worst_out,
                               touches_frame_edge=bool(worst_frame), pass_=(worst_out == 0 and not worst_frame))
        strip = Image.new("RGBA", (sum(f.width for f in frames[:8]) + 10 * 9, frames[0].height + 20), (22, 44, 46, 255))
        x = 10
        for f in frames[:8]:
            strip.alpha_composite(f, (x, 10)); x += f.width + 10
        strip.convert("RGB").save(f"{DST}/idle-signpost.png")
    for kind, full, old, event in BADGES:
        d = f"{OUT}/badge_{kind}_rig"
        if not os.path.exists(f"{d}/motion.json"):
            continue
        rj = json.load(open(f"{d}/rig.json"))
        mot = json.load(open(f"{d}/motion.json"))
        n = int(mot["cycle"] * fps)
        top, frames = 999, []
        for i in range(0, n, 2):
            cv, _ = pose_rig(d, rj, mot, i / fps)
            a = np.asarray(cv)[..., 3] > 24
            ys = np.nonzero(a.any(1))[0]
            top = min(top, int(ys.min()) if len(ys) else 999)
            if i % (fps // 2 * 3) == 0 and len(frames) < 10:
                frames.append(cv)
        res[kind] = dict(cycle=mot["cycle"], top_px_min=top, top_pt_min=round(top / S, 2), pass_=top > 0)
        strip = Image.new("RGBA", (sum(f.width for f in frames) + 10 * (len(frames) + 1), frames[0].height + 20), (18, 96, 92, 255))
        x = 10
        for f in frames:
            strip.alpha_composite(f, (x, 10)); x += f.width + 10
        strip.convert("RGB").save(f"{DST}/idle-{kind}.png")
    print(json.dumps(res, indent=1))
    save_proof("idle", res)


# ------------------------------------------------------------------ lane manifest + A4 handoff

HOME_ENTRIES = [
    # id, source, file, size_pt, purpose, replaces, extra
    ("homeWorkshop", "art/ui/recipes/scene_home_d1.py:homeWorkshop", "art/out/homeWorkshop@3x.png", [393, 852],
     "the home's back wall + floor (D1: teal plank wall under a bolted header beam, copper pipes + brass valve / portholes, "
     "timber ledge, stone courses, timber deck beam + rope rails, honey plank wainscot, stone plinth, packed earth)",
     "homeBackdrop", dict(full_bleed=True)),
    ("homeScaffold", "art/ui/recipes/scene_home_d1.py:homeScaffold", "art/out/homeScaffold@3x.png", [191, 192],
     "the boss's station: R2's timber scaffold rail + brass lever (char_bossStation, the rig camera), rail ends rounded, "
     "posts carried down onto the deck beam; drawn between the boss's torso/head and his arms", "homeConsole", {}),
    ("homeFloor", "art/ui/recipes/scene_home_d1.py:homeFloor", "art/out/homeFloor@3x.png", [393, 182],
     "the round plank work-pad in an iron hoop on the packed-earth floor (carries the Play frame; the Diggers' contact "
     "shadows baked)", "homePlatform", dict(full_bleed=True)),
    ("homeCabinet", "art/ui/recipes/scene_home_d1.py:homeCabinet", "art/out/homeCabinet@3x.png", [206, 215],
     "the timber cabinet (today's machine silhouette): brass bezel + rivets, brass corner plates, dark timber inner walls, "
     "a deep-teal planked back wall, the LEVEL plate recess; the signpost stands inside", "homeCapsuleMachine", {}),
    ("homeSignpost", "art/pipeline/items/char_home_signpost.py:home_signpost", "art/out/homeSignpost@3x.png", [190, 128],
     "the centrepiece (owner item 4), full render: a carved post, five painted arrow boards each on its own iron "
     "bracket, a lantern on the post's hook (no two arrows can touch)", "homeArrowPileFull", {}),
    ("homeSignpostLayers", "art/pipeline/items/char_home_signpost.py:home_signpost", "art/out/home_signpost_rig", [190, 128],
     "the centrepiece as layers (base, lantern, board1..5; pivots hinge / hook): idle sway + the refill flip-in",
     "homeArrowPileHalf + homeArrowPileLow (+ the refill's arrowGlossy drop sprites in HomeScene)", dict(rig=True)),
    ("badgeHotStreak", "art/ui/recipes/3d-home_d1.py:badgeHotStreak", "art/out/badgeHotStreak@3x.png", [80, 84],
     "Hot Streak home badge (full render): brass-rimmed teal medallion, crossed timber poles with tangerine / coral "
     "pennants (flame mark), timber drum with the teal text band", "eventBadgeStreak", {}),
    ("badgeRocketRally", "art/ui/recipes/3d-home_d1.py:badgeRocketRally", "art/out/badgeRocketRally@3x.png", [80, 84],
     "Rocket Rally home badge (full render): a teal riveted rocket, tangerine nose + fins, a brass porthole (live rank)",
     "eventBadgeRocket", {}),
    ("badgeCloudHop", "art/ui/recipes/3d-home_d1.py:badgeCloudHop", "art/out/badgeCloudHop@3x.png", [80, 84],
     "Cloud Hop home badge (full render): a bounce drum (tangerine hide top, teal laced shell, brass tag for the live "
     "count) on cream clouds", "eventBadgeSkyJump", {}),
    ("badgeHotStreakLayers", "art/ui/recipes/3d-home_d1.py:badge_hotstreak", "art/out/badge_hotstreak_rig", [80, 84],
     "Hot Streak badge as layers: body, pennantL, pennantR (pivots `pole`): the flutter", None, dict(rig=True)),
    ("badgeRocketRallyLayers", "art/ui/recipes/3d-home_d1.py:badge_rocketrally", "art/out/badge_rocketrally_rig", [80, 84],
     "Rocket Rally badge as layers: body, exhaustA / exhaustB (painted flicker overlays), rocket: the lift-off", None,
     dict(rig=True)),
    ("badgeCloudHopLayers", "art/ui/recipes/3d-home_d1.py:badge_cloudhop", "art/out/badge_cloudhop_rig", [80, 84],
     "Cloud Hop badge as layers: body, drum, clouds: the hop + cloud bob", None, dict(rig=True)),
    ("navCart", "art/ui/recipes/3d-home_d1.py:navCart", "art/ui/out/navCart@3x.png", [62, 62],
     "bottom-nav Shop: a tangerine mine cart on iron wheels heaped with star coins", "navShop", {}),
    ("navLodge", "art/ui/recipes/3d-home_d1.py:navLodge", "art/ui/out/navLodge@3x.png", [80, 86],
     "bottom-nav Home (raised tab): a plank lodge, steep teal shingle roof, round tangerine door, brass-capped chimney",
     "navHome", {}),
    ("navCup", "art/ui/recipes/3d-home_d1.py:navCup", "art/ui/out/navCup@3x.png", [68, 62],
     "bottom-nav Leaderboard (+ the Weekly header icon): a gold cup with a teal star emblem on a timber plinth",
     "navTrophy", {}),
]


def cmd_manifest():
    ents = []
    for i, src, f, size, purpose, old, extra in HOME_ENTRIES:
        path = f + "/rig.json" if extra.get("rig") else f
        if not os.path.exists(path):
            print("missing", i, path)
            continue
        e = dict(id=i, family="3d", route="C1" if (i.startswith("home") and "Layers" not in i) or i == "homeSignpostLayers" else "B3",
                 group="home", purpose=purpose, screen="home", size_pt=size, size_px=[size[0] * 3, size[1] * 3], source=src,
                 file=f, status="done", owner="scene" if i.startswith("home") else "3d-hud",
                 notes="R3 HOME (D1, ruling 46: today's composition, restyled)." +
                       (f" Replaces {old} at A4's mapping step (art/lanes/home.handoff.json)." if old else
                        " Layered companion of the full render (A4: PuppetStage-style loops)."))
        if extra.get("rig"):
            rj = json.load(open(path))
            e["notes"] += f" Rig {len(rj['layers'])} layers {[L['name'] for L in rj['layers']]}; proof {rj.get('proof')}."
        e.update({k: v for k, v in extra.items()})
        ents.append(e)
    json.dump(dict(version=1, title="R3 HOME lane entries (D1 home scene, signpost centrepiece, event badges as layers, nav "
                                     "icons; scratch manifest for manifest_check --lanes; the art director merges them into "
                                     "art/MANIFEST.json; the ids they replace are in each entry's notes and in "
                                     "art/lanes/home.handoff.json)", entries=ents), open("art/lanes/home.entries.json", "w"), indent=1)
    print(len(ents), "entries -> art/lanes/home.entries.json")


def cmd_handoff():
    """art/lanes/home.handoff.json: everything A4 (and A5 / the director) needs to switch the home to R3's art."""
    def rj_of(d):
        return json.load(open(f"{d}/rig.json")) if os.path.exists(f"{d}/rig.json") else None
    sp = rj_of(f"{OUT}/home_signpost_rig")
    spm = json.load(open(f"{OUT}/home_signpost_rig/motion.json")) if os.path.exists(f"{OUT}/home_signpost_rig/motion.json") else None
    badges = {}
    proofs = json.load(open(PROOFS)) if os.path.exists(PROOFS) else {}
    for kind, full, old, event in BADGES:
        d = f"{OUT}/badge_{kind}_rig"
        r = rj_of(d)
        m = json.load(open(f"{d}/motion.json")) if os.path.exists(f"{d}/motion.json") else None
        badges[kind] = dict(event=event, replaces=old, full=f"art/out/{full}@3x.png (UIArt case {full})", rig=f"art/out/badge_{kind}_rig",
                            layers=[L["name"] for L in r["layers"]] if r else None,
                            live_anchors_pt=(proofs.get("badges", {}).get(kind, {}) or {}).get("anchors"),
                            puppet_block=m)
    h = dict(
        about="R3 HOME (PLAN-P §4.2; owner items 4 + 8 + 15; ruling 46) -> A4 ART-INTEG (then A5 for the palette). Today's "
              "composition and object types, restyled D1; every file is NEW (nothing existing was changed); the ids they "
              "replace become NOT-SHIPPED at A4's step (grep Tests/ UITests/ App/ Packages/ first).",
        ids={"homeBackdrop": "homeWorkshop", "homeConsole": "homeScaffold", "homePlatform": "homeFloor",
             "homeCapsuleMachine": "homeCabinet", "homeArrowPileFull/Half/Low (+ ArrowPileView's arrowGlossy* drops)":
                 "home_signpost_rig (+ homeSignpost@3x.png, the full render, for the preload)",
             "navShop": "navCart", "navHome": "navLodge", "navTrophy": "navCup (also WeeklyViews.swift:34 + SocialModel.swift:174)",
             "eventBadgeStreak": "badgeHotStreak (+ badge_hotstreak_rig)", "eventBadgeRocket": "badgeRocketRally (+ badge_rocketrally_rig)",
             "eventBadgeSkyJump": "badgeCloudHop (+ badge_cloudhop_rig)"},
        home_scene=dict(
            order_back_to_front=[
                "homeWorkshop (full bleed 393 x 852; replaces homeBackdrop)",
                "Puppet(char_boss_home_rig, .excluding(scientistArms))",
                "homeScaffold at ui.json home.scene.console = [109, 176, 191, 192] (the key name kept: ShellTests.swift:205 requires it; value was [95, 266, 214, 109])",
                "Puppet(char_boss_home_rig, .only(scientistArms))",
                "homeFloor at home.scene.platform [0, 576, 393, 182] (unchanged rect)",
                "homeCabinet at home.scene.capsuleMachine [95, 365, 206, 215] (unchanged rect)",
                "HomeCentrepiece(home_signpost_rig) at the rig's placement_pt (replaces ArrowPileView; home.scene.arrowPile = [placement.x, placement.y, 190, 128], key kept for ShellTests:205)",
                "HomeLevelControls (LEVEL plate + Play: rects UNCHANGED)",
                "Puppet(char_dig_homeL_rig), Puppet(char_dig_homeR_rig)", "HomeReturnDim, top bar, HomeEventLayer, nav (unchanged)"],
            boss_placement=dict(frame_top_left=list(BOSS_PLACE), eyeMid=[205.61, 211.99],
                                how="ruling 46: today's centred spot (the scientist's (109.23, 176.52), rounded to whole pt so "
                                    "homeScaffold registers to the pixel); set by char_boss.HOME_EYEMID_PT = (205.61, 211.99) + "
                                    "char_make.py rig boss_home --skip-render (BOSS-EARS / R3 after BOSS-EARS's queue)"),
            diggers="R2's placements kept (feet (70, 606) and (318, 606)); homeFloor bakes their contact shadows there",
            preload="HomeView.art: [.homeWorkshop, .homeFloor, .homeScaffold, .homeCabinet, .homeSignpost, ... navCart, navLodge, navCup]",
            base_color="ui.json tokens home.base (the fill behind the backdrop) 0x7D8BC3 -> 0x23565A (D1 wall teal; A5's codemod may own it)"),
        signpost=dict(rig="art/out/home_signpost_rig", placement=sp["placement_pt"] if sp else None,
                      layers=[(L["name"], L.get("pivots_pt")) for L in sp["layers"]] if sp else None,
                      puppet_block_idle=(spm or {}).get("idle"), refill=(spm or {}).get("refill"),
                      notes=["Idle = a PuppetStage loop as-is (rotation about each track's pivot; cycle 36 s): add "
                             "ui.json puppet.home_signpost_rig = puppet_block_idle, draw it with PuppetStage(rig) like the crew.",
                             "Refill (HomeScene.requestRefill / takeRefill stay the trigger, 1.2 s = home.pileRefill): the "
                             "boards hide (scaleX 0 about their hinge) and flip in top -> bottom with a light haptic tick each "
                             "(motion-catalog / art-direction §4.3); needs a transform.scale.x key path next to PuppetStage's "
                             "three, render-server CAKeyframeAnimations (0 main-thread work), a new token = one refill.",
                             "Item 4 gate: art/review/tools/r3_home.py overlap (no board surface sample inside another board, "
                             "the post or the lantern) + idle (every sway frame stays inside the cabinet window)."]),
        badges=dict(per_event=badges,
                    notes=["EventBadge draws ArtImage(art: kind.art) today: switch the 3 cases to the new full renders, and "
                           "for the idle loops (OD5 / ruling 39) draw the layers with PuppetStage (rig + ui.json "
                           "puppet.badge_<event>_rig = puppet_block); the badge ZStack keeps its 80 x 84 frame.",
                           "The live number that sits ON the moving part (Rocket Rally rank on the porthole, Cloud Hop count on "
                           "the drum's tag) must ride with it: apply the same translateY track to that text (or host the text in "
                           "the moving CALayer). Anchors measured on the renders: live_anchors_pt.",
                           "Rocket Rally exhaust = two painted overlay layers (exhaustA / exhaustB) swapped every 0.10 s by the "
                           "overlay track during the lift (PuppetStage's `overlay` prop: one overlay at a time) and moved by "
                           "the same translateY track as the rocket.",
                           "Stagger (motion-catalog §6.4): the three loops have their own cycles (16 / 12 / 12 s, phases in the "
                           "blocks); A4 may offset their begin (PuppetMotion.phase) so at most two move at once."]),
        nav=dict(frames="unchanged ui.json rects (home.navShop / navHomeIcon / navTrophy + the Sel variants)",
                 files=["art/ui/out/navCart@3x.png (62 x 62)", "art/ui/out/navLodge@3x.png (80 x 86)",
                        "art/ui/out/navCup@3x.png (68 x 62)"]),
        not_shipped_after_A4=["homeBackdrop", "homeConsole", "homePlatform", "homeCapsuleMachine", "homeArrowPileFull",
                              "homeArrowPileHalf", "homeArrowPileLow", "navShop", "navHome", "navTrophy", "eventBadgeStreak",
                              "eventBadgeRocket", "eventBadgeSkyJump"],
        evidence=dict(proofs="art/review/home/proofs.json", sheets="art/review/home/*.png",
                      lane_manifest="art/lanes/home.entries.json"),
    )
    json.dump(h, open("art/lanes/home.handoff.json", "w"), indent=1)
    print("wrote art/lanes/home.handoff.json")


def cmd_rects():
    """UI rects unchanged: ui.json frames.home vs the committed build (git HEAD) = 0 pt diff; and the art's reserved
    regions line up: the LEVEL plate rect sits inside the cabinet's dark recess, the Play frame on the work-pad, the
    left badge column over plain wall (no pipe joint / lamp brighter than the wall under a badge's text)."""
    import subprocess
    head = json.loads(subprocess.run(["git", "show", "build/mazeout:apps/mazeout/App/Resources/Tuning/ui.json"], capture_output=True,
                                     text=True, cwd=os.path.join(APP, "..", "..")).stdout)["frames"]["home"]
    now = UI["frames"]["home"]
    diffs = {}
    for k in sorted(set(head) | set(now)):
        a, b = head.get(k), now.get(k)
        if a != b:
            diffs[k] = dict(head=a, now=b)
    res = dict(rects_compared=len(set(head) | set(now)), changed=diffs, max_diff_pt=0 if not diffs else "see changed")
    cab = f"{OUT}/homeCabinet@3x.png"
    if os.path.exists(cab):
        a = np.asarray(img(cab)).astype(np.float32)
        x, y, w, h = FR["levelPlate"]
        sub = a[round((y - 365) * S):round((y + h - 365) * S), round((x - 95) * S):round((x + w - 95) * S)]
        lum = sub[..., :3] @ np.array([0.299, 0.587, 0.114])
        res["levelPlate_on_recess"] = dict(alpha_min=int(sub[..., 3].min()), luma_median=round(float(np.median(lum)), 1),
                                           note="the plate covers the cabinet's recess: opaque and dark behind it")
    print(json.dumps(res, indent=1))
    save_proof("rects", res)


def cmd_sheet():
    """Review sheets: the composed home (both states) at 1x next to TODAY's home (ours, build-4), 1/3 thumbnails, and
    the new pieces on their own (signpost, badges, nav) at real size."""
    f = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial Bold.ttf", 22)
    shots = []
    for lab, pth in (("today (build-4)", "build/fixa1/shots/v11-home.png"), ("R3 D1 - Claw week", f"{DST}/home-claw.png"),
                     ("R3 D1 - no ladder event", f"{DST}/home-plain.png")):
        if os.path.exists(pth):
            shots.append((lab, Image.open(pth).convert("RGB").resize((393, 852), Image.LANCZOS)))
    W = sum(s_.width for _, s_ in shots) + 20 * (len(shots) + 1)
    sh = Image.new("RGB", (W, 852 + 70), (236, 236, 240))
    d = ImageDraw.Draw(sh)
    x = 20
    for lab, im in shots:
        sh.paste(im, (x, 50)); d.text((x, 14), lab, font=f, fill=(20, 20, 20)); x += im.width + 20
    sh.save(f"{DST}/sheet-home.png")
    # thumbnails at 1/3 (the owner's "does it read at a glance")
    th = Image.new("RGB", (W // 3 + 40, 852 // 3 + 50), (236, 236, 240))
    x = 10
    for lab, im in shots:
        th.paste(im.resize((131, 284), Image.LANCZOS), (x, 30)); x += 141
    th.save(f"{DST}/sheet-home-thumbs.png")
    # the pieces
    pieces = []
    for p_ in (f"{OUT}/homeSignpost@3x.png", f"{OUT}/badgeHotStreak@3x.png", f"{OUT}/badgeRocketRally@3x.png",
               f"{OUT}/badgeCloudHop@3x.png", f"{UIOUT}/navCart@3x.png", f"{UIOUT}/navLodge@3x.png", f"{UIOUT}/navCup@3x.png"):
        if os.path.exists(p_):
            pieces.append(img(p_))
    if pieces:
        Wp = sum(p_.width for p_ in pieces) + 20 * (len(pieces) + 1)
        Hp = max(p_.height for p_ in pieces) + 40
        pc = Image.new("RGBA", (Wp, Hp), (0x1D, 0x5E, 0x5A, 255))
        x = 20
        for p_ in pieces:
            pc.alpha_composite(p_, (x, 20)); x += p_.width + 20
        pc.convert("RGB").save(f"{DST}/sheet-pieces.png")
    print("sheets ->", DST)


def cmd_mock():
    obj = placeholder_objects()
    res = []
    for st in ("claw", "plain"):
        for ui in ("mock", "r9"):
            cv, notes = compose(st, extra=dict(objects=obj), ui=ui)
            dst = f"{EV}/mock-{st}-{ui}.png"
            cv.convert("RGB").save(dst)
            cv.convert("RGB").resize((393, 852), Image.LANCZOS).save(f"{EV}/mock-{st}-{ui}-1x.png")
            res.append(dict(state=st, ui=ui, **gate(dst)))
    for r in res:
        print(r)


if __name__ == "__main__":
    cmd, args = (sys.argv[1], sys.argv[2:]) if len(sys.argv) > 1 else ("compose", [])
    if cmd == "compose":
        cmd_compose()
    elif cmd == "mock":
        cmd_mock()
    elif cmd == "rects":
        cmd_rects()
    elif cmd == "sheet":
        cmd_sheet()
    elif cmd == "handoff":
        cmd_handoff()
    elif cmd == "manifest":
        cmd_manifest()
    elif cmd == "badges":
        cmd_badges()
    elif cmd == "signpost":
        cmd_signpost_motion()
    elif cmd == "idle":
        cmd_idle()
    elif cmd == "overlap":
        sys.exit(0 if cmd_overlap() else 1)
