#!/usr/bin/env python3
"""compose.py — Arrow Out App Store frames: one raw simulator capture + one caption -> one 1290x2796 store frame.

THE LOOK (S1: the category's convention -- their 8 store images -- drawn in OUR D1 style, nothing of theirs reused):
  * the raw capture FULL-BLEED: scaled to the frame width (1179 -> 1290 = x1.0942), anchored at the TOP;
  * a caption BAND over the bottom 400 px (14.3 %) in our nav bar's teal (ui.json colors.nav.bar family): a 3 px dark rim,
    a thin light top edge (#C3E6D8 -> #4EC4B3), a groove, a #2AC3B1 -> #048A81 face and a faint tone-on-tone pattern of OUR
    board's bent path-arrows (deterministic: every frame's band is identical);
  * ONE caption, verbatim from design/captions/<loc>.json (keyword N, case exactly as written; nothing else on the image):
    PCDisplay-Black for Latin; for ja / ko / zh-Hans the in-app cascade's faces Hiragino Sans W8 / Apple SD Gothic Neo Bold
    (grown 0.015 em: it is lighter than the other faces) / PingFang SC Heavy, per character like GameText's cascade (so
    "Arrow Out" stays PCDisplay in every locale). Treatment = the in-game label's (ui.json text.hud.levelTab.label): a
    white -> #FDEDCF fill ladder per line, a dark-teal #00393D outline (0.12 cap), a solid drop in the outline colour
    (0.08 cap) and a soft #00282B shadow;
  * the Dynamic Island the iPhone 16 simulator bakes into every capture is removed (see --island).

FRAMING THE RAW CAPTURES (for the capture step): the band covers raw y >= 2190 px (730 pt of 852) -- nothing that matters
may sit there (the in-game booster tray at 755-836 pt is covered, which is intended). Nothing is cropped at the top.
FRAME 5 (home) -- decision: full-bleed like frames 1-4, the band sits exactly over the bottom nav bar (Shop / Home /
Leaderboard tabs; nav top 772 pt). The Play button (its rim ends at 726 pt, 14 frame px above the band), the LEVEL plate, the
crew, the event badges and the HUD chips stay fully visible. Chosen over "scale the capture into the area above the band":
that shrinks the whole scene to 85 % and needs side fill, and breaks the full-bleed rhythm of the set.

CAPTION FIT: one line preferred, two lines max, never clipped (asserted; exit 1 otherwise), ONE size per locale: `set`
fits all five captions together -- the common scale is the smallest caption's fit (target: a 98 px Latin capital; CJK:
the reference glyph 国 / 국 at 1.28x that, one font size for every CJK caption of a locale); a caption whose one-line
capital would fall under 76 px (their captions: ~84 px) breaks into two balanced lines instead (e.g. it "Giochi senza /
pubblicità"); a caption that still cannot reach 0.70 keeps its own smaller size and is flagged (own_size) in
compose.json. Width limit: 1150 px incl. the outline (70 px margins).

USAGE
  # one locale's five frames (the normal path; captions from design/captions/<loc>.json, raws in frame order 1..5):
  python3 tools/store/compose.py set --locale de-DE --raws hero.png obstacles.png tap.png hard.png home.png \
        [--out-dir fastlane/screenshots/de-DE] [--home-plate art/out/homeWorkshop@3x.png] [--captions other.json]
      -> <out-dir>/01_iphone69.png .. 05_iphone69.png (1290x2796 RGB PNG, no alpha) + <out-dir>/compose.json
         (per frame: lines, scale, cap_px, island method + its measurements, caption box, sha1)
      --out-dir defaults to fastlane/screenshots/<locale>; --home-plate = the clean backdrop that fills the island on
      frame 5 (the island sits over the home art there); frames 1-4 fill it from the surrounding colour.
  # a single frame (its own fit, or --scale to force a locale's common scale from a set's compose.json):
  python3 tools/store/compose.py frame --raw cap.png --caption "Arrow Out" --locale en-US --out out.png \
        [--island auto|keep|flat|plate|smooth] [--plate clean.png] [--scale 0.8048]
  # a contact sheet to LOOK at (rows of images scaled to one height):
  python3 tools/store/compose.py sheet --out sheet.png --height 996 --row "label=a.png,b.png" --row "label2=c.png"
  Proof of the design: build/p/S1/design/make_proof.sh -> build/p/S1/design/proof.png.

--island (the black pill at the top centre of every 1179x2556 capture):
  auto   (default) flat -> plate -> smooth, the first that is safe; EXIT 1 when none is (never a smear over art)
  flat   the ring around the pill is one colour (spread <= 6: the white board screens) -> fill with it
  plate  fill from --plate (a clean, capture-sized image of the same background), matched to the capture per channel on
         the ring; refused when the ring residual is > 8/255 (e.g. something drawn over the backdrop near the island)
  smooth harmonic (Laplace) fill when the ring has no edges (max gradient <= 4: the Time Freeze frost vignette)
  keep   leave the island
Refuses (exit 1): a raw that is not 1179x2556 (or 1290x2796); a near-blank capture (> 97.5 % one colour: a launch or
placeholder frame); a caption that does not fit; a glyph no face has. LOOK at every frame anyway.
Requirements: macOS + Xcode (tools/store/textmask.swift, CoreText, compiled on first use into build/store-bin/textmask;
PingFang SC Heavy is read from the installed iOS 26 simulator runtime -- the Mac's own PingFang stops at Semibold), python3
with numpy, scipy, Pillow. ~2 s per frame.
"""
import argparse
import glob
import hashlib
import json
import os
import subprocess
import sys
import tempfile

import numpy as np
from PIL import Image, ImageDraw, ImageFilter
from scipy import ndimage
from scipy.sparse import lil_matrix
from scipy.sparse.linalg import splu

HERE = os.path.dirname(os.path.abspath(__file__))
APP = os.path.abspath(os.path.join(HERE, "..", ".."))
FRAME_W, FRAME_H = 1290, 2796

# ---- style (frame px). Colours from App/Resources/Tuning/ui.json and the D1 chrome ladder (design/publish/palette). ----
STYLE = {
    "band_h": 400,                 # 14.3 % of the frame; on home it covers exactly the nav bar (Play's rim ends 14 px above)
    "rim_dark": "#053F43",         # D1 outline, the 3 px line that separates the band from a white board
    "edge": ["#C3E6D8", "#8FE3D3", "#4EC4B3"],   # the thin light top edge (nav tabLine -> nav highlight), 12 px
    "edge_h": 12,
    "groove": "#00605B",           # nav tabGroove: a 3 px dark line under the light edge
    "face": [(0.00, "#2AC3B1"), (0.20, "#1DB4A3"), (0.60, "#0A9E92"), (1.00, "#048A81")],  # nav bar face ladder, lifted
    "pattern_dark": "#004F4C", "pattern_alpha": 0.11,
    "pattern_light": "#7FEADB", "pattern_light_alpha": 0.06, "pattern_blur": 2.2,
    "text_fill": [(0.0, "#FFFFFF"), (0.38, "#FFFDF8"), (0.72, "#FFF4E0"), (1.0, "#FDEDCF")],  # levelTab.label ladder, whiter top
    "text_outline": "#00393D",     # text.hud.levelTab.label.outline
    "shadow": "#00282B", "shadow_alpha": 0.55,
    "margin_x": 70,                # caption side margin (text never wider than 1290 - 2*70 = 1150 px incl. outline)
    "cap_h": 98,                   # target height of a Latin capital in the frame (their caption: ~84 px)
    "cjk_gain": 1.28,              # CJK size: the reference glyph's (国 / 국) ink height relative to cap_h -- kana and hangul
                                   # sit inside the em box and read smaller than Latin capitals of the same ink height
    "embolden_em": {"ko": 0.015},  # Apple SD Gothic Neo Bold (iOS's heaviest Korean face) is lighter than the other faces:
                                   # grow its Hangul glyphs by 0.015 em so the locales carry about the same weight (S1 compose:
                                   # 0.03 closed the counters of dense syllables -- 탈출, 없 -- into blobs at thumbnail size)
    "outline_k": 0.12,             # outline radius / cap_h
    "drop_k": 0.08,                # solid drop (outline colour) offset / cap_h
    "shadow_dy_k": 0.16, "shadow_blur_k": 0.10,
    "line_gap_k": 0.50,            # two-line gap / cap_h (between the optical boxes)
    "one_line_floor": 0.776,       # one line down to a 76 px capital (their caption: ~84 px); below that -> two lines
    "own_size_floor": 0.70,        # a caption that cannot reach this even on two lines keeps its own size (flagged)
}
SS = 3  # text supersampling

FONT_LATIN = os.path.join(APP, "App", "Resources", "Fonts", "PCDisplay-Black.ttf")


def pingfang_spec():
    """PingFang SC Heavy = the iOS 26 runtime's PingFangUI.ttc face .PingFangSC-Medium at wght 900 (the Mac's copy stops at 600)."""
    pats = ["/Library/Developer/CoreSimulator/Volumes/iOS_*/Library/Developer/CoreSimulator/Profiles/Runtimes/iOS *.simruntime/"
            "Contents/Resources/RuntimeRoot/System/Library/PrivateFrameworks/FontServices.framework/CorePrivate/PingFangUI.ttc"]
    hits = sorted(h for p in pats for h in glob.glob(p))
    if not hits:
        sys.exit("compose.py: no iOS simulator runtime PingFangUI.ttc found (needed for PingFang SC Heavy, zh-Hans)")
    return f"{hits[-1]}|.PingFangSC-Medium|900"


CASCADE = {"ja": ["-|HiraginoSans-W8"], "ko": ["-|AppleSDGothicNeo-Bold"], "zh-Hans": None}  # zh filled lazily


def cascade_for(locale):
    if locale == "zh-Hans":
        return [pingfang_spec()]
    return CASCADE.get(locale) or []


def hex_rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


# ------------------------------------------------------------------------------------------------ text rendering (CoreText)
def textmask_bin():
    src = os.path.join(HERE, "textmask.swift")
    out = os.path.join(APP, "build", "store-bin", "textmask")
    if not os.path.exists(out) or os.path.getmtime(out) < os.path.getmtime(src):
        os.makedirs(os.path.dirname(out), exist_ok=True)
        subprocess.run(["swiftc", "-O", src, "-o", out], check=True)
    return out


_TM_CACHE = {}


def render_line(text, size, locale):
    """-> (mask float32 [0,1] at size, metrics dict). size in px of the final (supersampled) raster."""
    key = (text, round(size, 3), locale)
    if key in _TM_CACHE:
        return _TM_CACHE[key]
    with tempfile.TemporaryDirectory() as td:
        png = os.path.join(td, "m.png")
        cmd = [textmask_bin(), "--text", text, "--size", f"{size:.3f}", "--primary", FONT_LATIN, "--out", png]
        for c in cascade_for(locale):
            cmd += ["--cascade", c]
        r = subprocess.run(cmd, capture_output=True, text=True)
        if r.returncode != 0:
            sys.exit(f"compose.py: textmask failed for {text!r}: {r.stderr.strip()}")
        m = json.loads(r.stdout)
        mask = np.asarray(Image.open(png).convert("L"), dtype=np.float32) / 255.0
    _TM_CACHE[key] = (mask, m)
    return mask, m


REF = 200.0  # measuring size


CJK_REF = {"ja": "国", "zh-Hans": "国", "ko": "국"}  # one full-height glyph per face: every CJK caption of a locale gets ONE size


def measure(text, locale):
    """Ink width and optical height per px of font size, from one render at REF. Latin: the cap-height box; CJK: the
    reference glyph's ink (not the caption's own tallest glyph, so a kana-only caption is not blown up)."""
    mask, m = render_line(text, REF, locale)
    cols = np.where(mask.max(axis=0) > 0.02)[0]
    ink_w = (cols[-1] - cols[0] + 1) if len(cols) else 0
    cjk = any(r["font"] != "PCDisplay-Black" for r in m["runs"])
    if cjk and locale in CJK_REF and text != CJK_REF[locale]:
        opt = measure(CJK_REF[locale], locale)["opt"]
    else:
        opt = (m["optical"][1] - m["optical"][0]) / REF
    w = ink_w / REF + (2 * STYLE["embolden_em"].get(locale, 0) if cjk else 0)
    return {"w": w, "opt": opt, "cjk": cjk}


def target_opt(meas):
    return STYLE["cap_h"] * (STYLE["cjk_gain"] if meas["cjk"] else 1.0)


def splits(text):
    """Candidate two-line splits: at spaces; for a caption with no space and CJK glyphs, between any two characters."""
    words = text.split(" ")
    if len(words) > 1:
        return [(" ".join(words[:i]), " ".join(words[i:])) for i in range(1, len(words))]
    if any(ord(c) > 0x2E7F for c in text) and len(text) > 1:
        return [(text[:i], text[i:]) for i in range(1, len(text))]
    return []


def fit(text, locale):
    """-> dict(one=scale on one line, two=(scale, split) or None). scale = share of the target height (<= 1)."""
    m = measure(text, locale)
    size_full = target_opt(m) / m["opt"]  # font px that hits the target optical height

    def scale_for(w_per_px):
        # largest s <= 1 with w_per_px * size_full * s <= max_text_w(s); max_text_w is linear in s -> solve directly
        a = w_per_px * size_full
        s = (FRAME_W - 2 * STYLE["margin_x"]) / (a + 2 * STYLE["outline_k"] * STYLE["cap_h"])
        return min(1.0, s)

    one = scale_for(m["w"])
    best2 = None
    for a, b in splits(text):
        w = max(measure(a, locale)["w"], measure(b, locale)["w"])
        s = scale_for(w)
        bal = abs(measure(a, locale)["w"] - measure(b, locale)["w"])
        if best2 is None or (s, -bal) > (best2[0], -best2[2]):
            best2 = (s, (a, b), bal)
    return {"one": one, "two": (best2[0], best2[1]) if best2 else None, "meas": m, "size_full": size_full}


def plan_set(captions, locale):
    """Choose lines + one common scale for a locale's captions. -> list of dict(lines, scale, own)."""
    fits = [fit(c, locale) for c in captions]
    choice = []
    for f in fits:
        if f["one"] >= STYLE["one_line_floor"] or not f["two"]:
            choice.append((f["one"], None))
        else:
            s2, sp = f["two"]
            choice.append((s2, sp) if s2 > f["one"] else (f["one"], None))
    common_pool = [s for s, _ in choice if s >= STYLE["own_size_floor"]]
    common = min(common_pool) if common_pool else min(s for s, _ in choice)
    plans = []
    for (s, sp), c, f in zip(choice, captions, fits):
        own = bool(s < common)
        scale = s if own else common
        # with the (smaller) common scale a two-line caption may now fit on one line: prefer one line
        if sp is not None and f["one"] >= scale:
            sp = None
        plans.append({"caption": c, "lines": [c] if sp is None else list(sp), "scale": round(scale, 4), "own_size": own,
                      "fit_one_line": round(f["one"], 4), "fit_two_lines": round(f["two"][0], 4) if f["two"] else None})
    return plans


def render_caption(lines, scale, locale):
    """-> RGBA PIL image of the finished caption (fill + outline + drop + soft shadow), tight with padding; its optical box."""
    cap = STYLE["cap_h"] * scale
    R = STYLE["outline_k"] * cap
    drop = STYLE["drop_k"] * cap
    pad = int(R + drop + STYLE["shadow_dy_k"] * cap + 3 * STYLE["shadow_blur_k"] * cap + 8)
    rendered = []
    for ln in lines:
        m = measure(ln, locale)
        size = target_opt(m) / m["opt"] * scale
        mask, met = render_line(ln, size * SS, locale)
        grow = STYLE["embolden_em"].get(locale, 0) * size * SS if m["cjk"] else 0
        if grow > 0:
            d = ndimage.distance_transform_edt(mask <= 0.5)
            mask = np.maximum(mask, np.clip(grow - d + 0.5, 0, 1)).astype(np.float32)
        rendered.append((mask, met))
    gap = STYLE["line_gap_k"] * cap * SS
    # stack on the supersampled canvas, aligning optical boxes, centred horizontally by ink
    boxes = []
    y = 0.0
    for mask, met in rendered:
        o0, o1 = met["optical"]
        boxes.append((mask, met, y - o0))  # mask top y on the canvas
        y += (o1 - o0) + gap
    opt_total = y - gap
    inks = []
    for mask, met, top in boxes:
        cols = np.where(mask.max(axis=0) > 0.02)[0]
        inks.append((cols[0], cols[-1]))
    width = max(b - a + 1 for a, b in inks)
    P = pad * SS
    top_min = min(t for _, _, t in boxes)
    bot_max = max(t + mk.shape[0] for mk, _, t in boxes)
    H = int(np.ceil(bot_max - top_min)) + 2 * P
    W = int(width) + 2 * P
    H += (-H) % SS
    W += (-W) % SS
    canvas = np.zeros((H, W), np.float32)
    for (mask, met, top), (a, b) in zip(boxes, inks):
        x0 = P + (width - (b - a + 1)) // 2 - a
        y0 = int(round(top - top_min)) + P
        h, w = mask.shape
        cx0, cy0 = max(0, x0), max(0, y0)
        sub = mask[cy0 - y0:min(h, H - y0), cx0 - x0:min(w, W - x0)]
        canvas[cy0:cy0 + sub.shape[0], cx0:cx0 + sub.shape[1]] = np.maximum(
            canvas[cy0:cy0 + sub.shape[0], cx0:cx0 + sub.shape[1]], sub)
    opt_top_ss = P + (boxes[0][2] - top_min) + boxes[0][1]["optical"][0]
    # outline by distance transform on the supersampled binary glyphs (round joins), then box-downsample -> anti-aliased
    inside = canvas > 0.5
    dist = ndimage.distance_transform_edt(~inside)
    outl = np.clip(R * SS - dist + 0.5, 0, 1)
    outl = np.maximum(outl, canvas)

    def down(a):
        return a.reshape(H // SS, SS, W // SS, SS).mean(axis=(1, 3))

    fill_a, out_a = down(canvas), down(outl)
    h, w = fill_a.shape
    # fill ladder (vertical, over the optical box)
    y_top = opt_top_ss / SS
    y_bot = y_top + opt_total / SS
    stops = STYLE["text_fill"]
    # the fill ladder runs over EACH line's optical box (as the in-game labels do), not over the whole block
    line_boxes = [((P + (top - top_min) + met["optical"][0]) / SS, (P + (top - top_min) + met["optical"][1]) / SS)
                  for _, met, top in boxes]
    rows = np.arange(h, dtype=np.float32)
    t = np.zeros(h, np.float32)
    for k, (a0, a1) in enumerate(line_boxes):
        lo = -1e9 if k == 0 else (line_boxes[k - 1][1] + a0) / 2
        hi = 1e9 if k == len(line_boxes) - 1 else (a1 + line_boxes[k + 1][0]) / 2
        sel = (rows >= lo) & (rows < hi)
        t[sel] = np.clip((rows[sel] - a0) / max(1.0, a1 - a0), 0, 1)
    pos = np.array([p for p, _ in stops], np.float32)
    cols = np.array([hex_rgb(c) for _, c in stops], np.float32)
    ramp = np.stack([np.interp(t, pos, cols[:, k]) for k in range(3)], axis=1)  # h x 3
    fill_rgb = np.repeat(ramp[:, None, :], w, axis=1)
    oc = np.array(hex_rgb(STYLE["text_outline"]), np.float32)
    sc = np.array(hex_rgb(STYLE["shadow"]), np.float32)
    # layers: soft shadow, solid drop, outline, fill
    di = int(round(drop))
    drop_a = np.zeros_like(out_a)
    drop_a[di:, :] = out_a[:h - di, :] if di > 0 else out_a
    sh = np.zeros_like(out_a)
    sdy = int(round(STYLE["shadow_dy_k"] * cap))
    sh[sdy:, :] = np.maximum(out_a, drop_a)[:h - sdy, :]
    sh = ndimage.gaussian_filter(sh, STYLE["shadow_blur_k"] * cap) * STYLE["shadow_alpha"]
    rgb = np.zeros((h, w, 3), np.float32)
    a = np.zeros((h, w), np.float32)

    def over(rgb, a, crgb, ca):
        na = ca + a * (1 - ca)
        nrgb = (crgb * ca[..., None] + rgb * a[..., None] * (1 - ca[..., None])) / np.maximum(na[..., None], 1e-6)
        return nrgb, na

    rgb, a = over(rgb, a, np.broadcast_to(sc, (h, w, 3)), sh)
    rgb, a = over(rgb, a, np.broadcast_to(oc * 0.78, (h, w, 3)), drop_a)
    rgb, a = over(rgb, a, np.broadcast_to(oc, (h, w, 3)), out_a)
    rgb, a = over(rgb, a, fill_rgb, fill_a)
    img = Image.fromarray(np.dstack([np.clip(rgb, 0, 255), np.clip(a * 255, 0, 255)]).astype(np.uint8), "RGBA")
    ys, xs = np.nonzero(np.maximum(out_a, drop_a) > 0.15)  # the visible lettering (outline + drop), not the soft shadow
    return img, (y_top, y_bot), {"cap_px": round(cap, 1), "outline_px": round(R, 1), "drop_px": di,
                                 "ink_box": (int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max()))}


# ------------------------------------------------------------------------------------------------------------ the band
def _arrow_shapes():
    """Our board's path-arrows as polylines in grid units (a bent path + its head at the last point)."""
    return [
        [(0, 0), (3, 0)],
        [(0, 0), (2, 0), (2, 1.5)],
        [(0, 0), (0, 1), (1.5, 1), (1.5, 0)],
        [(0, 0), (1, 0), (1, 1), (2.5, 1)],
        [(0, 0), (0, 1.2), (2, 1.2)],
        [(0, 1), (0, 0), (1.2, 0), (1.2, 1), (2.4, 1), (2.4, 0.2)],
    ]


def _draw_arrow(d, pts, unit, width, color, ox, oy, rot):
    import math
    ca, sa = round(math.cos(rot)), round(math.sin(rot))
    P = [(ox + (x * ca - y * sa) * unit, oy + (x * sa + y * ca) * unit) for x, y in pts]
    d.line(P, fill=color, width=width, joint="curve")
    r = width / 2
    for x, y in (P[0],):
        d.ellipse([x - r, y - r, x + r, y + r], fill=color)
    (x1, y1), (x2, y2) = P[-2], P[-1]
    L = max(1e-6, ((x2 - x1) ** 2 + (y2 - y1) ** 2) ** 0.5)
    ux, uy = (x2 - x1) / L, (y2 - y1) / L
    hl, hw = width * 2.4, width * 1.7
    tip = (x2 + ux * hl * 0.6, y2 + uy * hl * 0.6)
    base = (x2 - ux * hl * 0.4, y2 - uy * hl * 0.4)
    d.polygon([tip, (base[0] - uy * hw, base[1] + ux * hw), (base[0] + uy * hw, base[1] - ux * hw)], fill=color)


_BAND = None


def band_image():
    global _BAND
    if _BAND is not None:
        return _BAND
    H, W = STYLE["band_h"], FRAME_W
    y = np.arange(H, dtype=np.float32)
    rim, eh = 3, STYLE["edge_h"]
    body0 = rim + eh + 3
    face = np.zeros((H, 3), np.float32)
    t = np.clip((y - body0) / (H - body0), 0, 1)
    fpos = [p for p, _ in STYLE["face"]]
    fcol = np.array([hex_rgb(c) for _, c in STYLE["face"]], np.float32)
    for k in range(3):
        face[:, k] = np.interp(t, fpos, fcol[:, k])
    img = Image.fromarray(np.repeat(face[:, None, :], W, axis=1).astype(np.uint8), "RGB")
    # pattern (supersampled 2x, deterministic)
    rng = np.random.default_rng(20260929)
    S2 = 2
    pat_d = Image.new("L", (W * S2, H * S2), 0)
    pat_l = Image.new("L", (W * S2, H * S2), 0)
    dd, dl = ImageDraw.Draw(pat_d), ImageDraw.Draw(pat_l)
    shapes = _arrow_shapes()
    unit, width = 34 * S2, 12 * S2
    cell = 150 * S2
    import math
    for gy in range(-1, H * S2 // cell + 2):
        for gx in range(-1, W * S2 // cell + 2):
            ox = gx * cell + (gy % 2) * cell / 2 + rng.uniform(-18, 18) * S2
            oy = gy * cell + body0 * S2 + rng.uniform(-14, 14) * S2
            sh = shapes[rng.integers(len(shapes))]
            rot = rng.integers(4) * math.pi / 2
            light = rng.random() < 0.28
            _draw_arrow(dl if light else dd, sh, unit, width, 255, ox, oy, rot)
    pat_d = pat_d.resize((W, H), Image.LANCZOS).filter(ImageFilter.GaussianBlur(STYLE["pattern_blur"]))
    pat_l = pat_l.resize((W, H), Image.LANCZOS).filter(ImageFilter.GaussianBlur(STYLE["pattern_blur"]))
    arr = np.asarray(img, np.float32)
    ad = np.asarray(pat_d, np.float32)[..., None] / 255 * STYLE["pattern_alpha"]
    al = np.asarray(pat_l, np.float32)[..., None] / 255 * STYLE["pattern_light_alpha"]
    arr = arr * (1 - ad) + np.array(hex_rgb(STYLE["pattern_dark"]), np.float32) * ad
    arr = arr * (1 - al) + np.array(hex_rgb(STYLE["pattern_light"]), np.float32) * al
    # top: dark rim, light edge (3-stop ladder), groove + a soft inner shadow into the face
    arr[:rim] = hex_rgb(STYLE["rim_dark"])
    ecol = np.array([hex_rgb(c) for c in STYLE["edge"]], np.float32)
    for i in range(eh):
        tt = i / max(1, eh - 1)
        arr[rim + i] = [np.interp(tt, np.linspace(0, 1, len(ecol)), ecol[:, k]) for k in range(3)]
    arr[rim + eh:rim + eh + 3] = hex_rgb(STYLE["groove"])
    for i in range(14):
        a = 0.28 * (1 - i / 14) ** 2
        arr[body0 + i] = arr[body0 + i] * (1 - a) + np.array(hex_rgb(STYLE["groove"]), np.float32) * a
    _BAND = (Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), "RGB"), body0)
    return _BAND


# ------------------------------------------------------------------------------------------------ the Dynamic Island
def find_island(rgb):
    h, w, _ = rgb.shape
    k = w / 1179.0
    y1, x0, x1 = int(220 * k), int(250 * k), int(930 * k)
    win = rgb[:y1, x0:x1]
    black = (win.max(axis=2) < 24)
    lab, n = ndimage.label(black)
    best = None
    for sl_i, sl in enumerate(ndimage.find_objects(lab)):
        if sl is None:
            continue
        bh, bw = sl[0].stop - sl[0].start, sl[1].stop - sl[1].start
        cx = x0 + (sl[1].start + sl[1].stop) / 2
        if 250 * k <= bw <= 460 * k and 70 * k <= bh <= 150 * k and abs(cx - w / 2) < 60 * k:
            area = (lab[sl] == sl_i + 1).sum()
            if area > 0.7 * bw * bh and (best is None or area > best[0]):
                best = (area, (sl[0].start, sl[1].start + x0, sl[0].stop, sl[1].stop + x0))
    return best[1] if best else None


def island_mask(shape, box, grow):
    y0, x0, y1, x1 = box
    m = Image.new("L", (shape[1], shape[0]), 0)
    r = (y1 - y0) / 2 + grow
    ImageDraw.Draw(m).rounded_rectangle([x0 - grow, y0 - grow, x1 - 1 + grow, y1 - 1 + grow], radius=r, fill=255)
    return np.asarray(m) > 127


def harmonic_fill(img, mask):
    """Solve Laplace's equation inside mask with the surrounding pixels as the boundary (per channel)."""
    ys, xs = np.nonzero(mask)
    idx = -np.ones(mask.shape, np.int64)
    idx[ys, xs] = np.arange(len(ys))
    A = lil_matrix((len(ys), len(ys)))
    b = np.zeros((len(ys), img.shape[2]))
    for i, (y, x) in enumerate(zip(ys, xs)):
        A[i, i] = 4
        for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            yy, xx = y + dy, x + dx
            if mask[yy, xx]:
                A[i, idx[yy, xx]] = -1
            else:
                b[i] += img[yy, xx]
    lu = splu(A.tocsc())
    out = img.copy()
    for c in range(img.shape[2]):
        out[ys, xs, c] = lu.solve(b[:, c])
    return out


def remove_island(rgb, mode, plate=None):
    """-> (rgb, report). rgb float32 HxWx3."""
    if mode == "keep":
        return rgb, {"island": "kept"}
    box = find_island(rgb)
    if box is None:
        return rgb, {"island": "none found"}
    hole = island_mask(rgb.shape, box, 3)
    ring = island_mask(rgb.shape, box, 16) & ~island_mask(rgb.shape, box, 5)
    rp = rgb[ring]
    tried = []
    order = [mode] if mode != "auto" else ["flat", "plate", "smooth"]
    for m in order:
        if m == "flat":
            spread = float(np.percentile(rp, 99, axis=0).max() - np.percentile(rp, 1, axis=0).min())
            if spread <= 6:
                out = rgb.copy()
                out[hole] = np.median(rp, axis=0)
                return out, {"island": "flat", "box": box, "ring_spread": round(spread, 1)}
            tried.append(f"flat: ring spread {spread:.0f} > 6")
        elif m == "plate":
            if plate is None:
                tried.append("plate: no --plate")
                continue
            pl = plate.astype(np.float32)
            gains = []
            fit_rgb = np.zeros_like(rgb)
            for c in range(3):
                X = np.stack([pl[ring][:, c], np.ones(ring.sum())], axis=1)
                coef, *_ = np.linalg.lstsq(X, rp[:, c], rcond=None)
                gains.append([round(float(v), 3) for v in coef])
                fit_rgb[..., c] = pl[..., c] * coef[0] + coef[1]
            resid = float(np.sqrt(((fit_rgb[ring] - rp) ** 2).mean()))
            if resid <= 8:
                soft = ndimage.gaussian_filter(island_mask(rgb.shape, box, 4).astype(np.float32), 1.5)
                soft = np.maximum(soft, hole.astype(np.float32))[..., None]
                out = rgb * (1 - soft) + fit_rgb * soft
                return out, {"island": "plate", "box": box, "ring_rms": round(resid, 2), "gain_offset": gains}
            tried.append(f"plate: ring rms {resid:.1f} > 8")
        elif m == "smooth":
            g = rgb.mean(axis=2)
            # the Laplace fill reads only the 1-px layer just outside the hole (grow 3); check a 4..10 px ring around it, not the
            # plate ring (5..16): a diacritic poking up from the level tab 13 px under the pill (sk 'Úroveň 84') is no smear risk
            near = island_mask(rgb.shape, box, 10) & ~island_mask(rgb.shape, box, 3)
            grad = np.hypot(ndimage.sobel(g, 0), ndimage.sobel(g, 1))[near] / 8  # per-pixel intensity step
            rough = float(grad.max())  # frost vignette ~1; any drawn edge (a rail, a plank seam) >> 4
            if rough <= 4:
                y0, x0, y1, x1 = box
                sl = (slice(max(0, y0 - 24), y1 + 24), slice(max(0, x0 - 24), x1 + 24))
                out = rgb.copy()
                out[sl] = harmonic_fill(rgb[sl], hole[sl])
                return out, {"island": "smooth", "box": box, "ring_max_grad": round(rough, 1)}
            tried.append(f"smooth: ring has edges (max gradient {rough:.0f} > 4)")
    sys.exit("compose.py: cannot remove the Dynamic Island safely (" + "; ".join(tried) +
             ") -> pass --plate <clean background> or --island keep")


# ------------------------------------------------------------------------------------------------------------ frame
def load_raw(path):
    im = Image.open(path).convert("RGB")
    w, h = im.size
    if (w, h) not in ((1179, 2556), (1290, 2796)):
        sys.exit(f"compose.py: {path} is {w}x{h}; expected a 1179x2556 simulator capture (or 1290x2796)")
    return np.asarray(im, np.float32)


def assert_rendered(rgb, path):
    """Refuse a blank / launch-screen frame (memory screenshots-verify-content-not-count)."""
    small = rgb[::8, ::8].reshape(-1, 3)
    q = (small // 12).astype(np.int32)
    keys = q[:, 0] * 10000 + q[:, 1] * 100 + q[:, 2]
    _, counts = np.unique(keys, return_counts=True)
    top = counts.max() / len(keys)
    if top > 0.975:
        sys.exit(f"compose.py: {path} looks blank ({top:.1%} of the pixels are one colour)")
    return round(float(top), 3)


def compose(raw_path, lines, scale, locale, out_path, island="auto", plate_path=None):
    rgb = load_raw(raw_path)
    blank_share = assert_rendered(rgb, raw_path)
    plate = None
    if plate_path:
        p = Image.open(plate_path).convert("RGB")
        if p.size != (rgb.shape[1], rgb.shape[0]):
            p = p.resize((rgb.shape[1], rgb.shape[0]), Image.LANCZOS)
        plate = np.asarray(p, np.float32)
    rgb, rep = remove_island(rgb, island, plate)
    im = Image.fromarray(np.clip(rgb + 0.5, 0, 255).astype(np.uint8), "RGB")
    sh = round(im.height * FRAME_W / im.width)
    im = im.resize((FRAME_W, sh), Image.LANCZOS)
    frame = Image.new("RGB", (FRAME_W, FRAME_H), (255, 255, 255))
    frame.paste(im.crop((0, 0, FRAME_W, min(sh, FRAME_H))), (0, 0))
    band, body0 = band_image()
    by = FRAME_H - STYLE["band_h"]
    frame.paste(band, (0, by))
    cap_img, (o0, o1), cap_rep = render_caption(lines, scale, locale)
    # centre the optical box in the band's face
    cy = by + body0 + (STYLE["band_h"] - body0) / 2
    x = (FRAME_W - cap_img.width) // 2
    y = int(round(cy - (o0 + o1) / 2))
    # never clipped: the visible caption (outline alpha) must sit inside the band's face and the side margins
    ib = cap_rep.pop("ink_box")
    vis = (x + ib[0], y + ib[1], x + ib[2], y + ib[3])
    if vis[0] < STYLE["margin_x"] - 1 or vis[2] > FRAME_W - STYLE["margin_x"] or vis[1] < by + body0 + 6 or vis[3] > FRAME_H - 6:
        sys.exit(f"compose.py: caption {lines} does not fit the band: {vis}")
    frame.paste(cap_img, (x, y), cap_img)
    assert frame.size == (FRAME_W, FRAME_H) and frame.mode == "RGB"
    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    frame.save(out_path, optimize=True)
    return dict(rep, lines=lines, scale=scale, caption_box=[int(v) for v in vis], blank_share=blank_share, **cap_rep,
                raw=os.path.relpath(os.path.abspath(raw_path), APP) if os.path.abspath(raw_path).startswith(APP) else raw_path,
                out=out_path, sha1=hashlib.sha1(open(out_path, "rb").read()).hexdigest()[:12])


# ------------------------------------------------------------------------------------------------------------ sheet
def sheet(rows, out, height, gap=24, label_h=56):
    from PIL import ImageFont
    font = ImageFont.truetype(FONT_LATIN, 34)
    tiles = []
    for label, paths in rows:
        ims = []
        for p in paths:
            im = Image.open(p).convert("RGB")
            ims.append(im.resize((round(im.width * height / im.height), height), Image.LANCZOS))
        tiles.append((label, ims))
    W = max(sum(i.width for i in ims) + gap * (len(ims) + 1) for _, ims in tiles)
    H = sum(height + label_h + gap for _ in tiles) + gap
    sh = Image.new("RGB", (W, H), (38, 42, 44))
    d = ImageDraw.Draw(sh)
    y = gap
    for label, ims in tiles:
        d.text((gap, y + 8), label, fill=(235, 235, 235), font=font)
        x = gap
        for im in ims:
            sh.paste(im, (x, y + label_h))
            x += im.width + gap
        y += label_h + height + gap
    sh.save(out, optimize=True)


# ------------------------------------------------------------------------------------------------------------ CLI
def captions_for(locale):
    p = os.path.join(APP, "design", "captions", f"{locale}.json")
    return [c["headline"] for c in json.load(open(p))["captions"]]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("set")
    s.add_argument("--locale", required=True)
    s.add_argument("--raws", nargs=5, required=True)
    s.add_argument("--out-dir")
    s.add_argument("--home-plate", default=os.path.join(APP, "art", "out", "homeWorkshop@3x.png"))
    s.add_argument("--captions", help="override: a captions JSON (default design/captions/<locale>.json)")
    f = sub.add_parser("frame")
    f.add_argument("--raw", required=True)
    f.add_argument("--caption", required=True)
    f.add_argument("--locale", required=True)
    f.add_argument("--out", required=True)
    f.add_argument("--island", default="auto", choices=["auto", "keep", "flat", "plate", "smooth"])
    f.add_argument("--plate")
    f.add_argument("--scale", type=float, help="force the common scale (0-1] of a locale's set")
    k = sub.add_parser("sheet")
    k.add_argument("--out", required=True)
    k.add_argument("--height", type=int, default=996)
    k.add_argument("--row", action="append", required=True, help="label=a.png,b.png")
    a = ap.parse_args()

    if a.cmd == "set":
        caps = ([c["headline"] for c in json.load(open(a.captions))["captions"]] if a.captions else captions_for(a.locale))
        if len(caps) != 5:
            sys.exit(f"compose.py: {a.locale} has {len(caps)} captions, need 5")
        out_dir = a.out_dir or os.path.join(APP, "fastlane", "screenshots", a.locale)
        plans = plan_set(caps, a.locale)
        reports = []
        for i, (raw, plan) in enumerate(zip(a.raws, plans), 1):
            out = os.path.join(out_dir, f"{i:02d}_iphone69.png")
            plate = a.home_plate if i == 5 else None
            rep = compose(raw, plan["lines"], plan["scale"], a.locale, out, "auto", plate)
            rep.update({k2: plan[k2] for k2 in ("caption", "own_size", "fit_one_line", "fit_two_lines")})
            reports.append(rep)
            print(f"{out}: {plan['lines']} scale {plan['scale']} island {rep['island']}")
        json.dump({"locale": a.locale, "style": STYLE, "frames": reports}, open(os.path.join(out_dir, "compose.json"), "w"),
                  indent=1, ensure_ascii=False, default=lambda o: o.item() if hasattr(o, "item") else str(o))
    elif a.cmd == "frame":
        if a.scale:
            f1 = fit(a.caption, a.locale)
            lines = [a.caption] if f1["one"] >= a.scale or not f1["two"] else list(f1["two"][1])
            scale = a.scale
        else:
            p = plan_set([a.caption], a.locale)[0]
            lines, scale = p["lines"], p["scale"]
        rep = compose(a.raw, lines, scale, a.locale, a.out, a.island, a.plate)
        print(json.dumps(rep, ensure_ascii=False, default=lambda o: o.item() if hasattr(o, "item") else str(o)))
    elif a.cmd == "sheet":
        rows = []
        for r in a.row:
            label, _, paths = r.partition("=")
            rows.append((label, [p for p in paths.split(",") if p]))
        sheet(rows, a.out, a.height)
        print(a.out)


if __name__ == "__main__":
    main()
