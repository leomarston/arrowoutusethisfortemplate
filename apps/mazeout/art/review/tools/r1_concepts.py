#!/usr/bin/env python3
"""R1 CONCEPTS (PLAN-P §4.2) — the D1 "Burrow Works" concept sheets, the palette mock, the logo restyle sketch, the
copygate recalibration and the one owner sheet.

    PY=~/.venvs/mf3d/bin/python
    nice -n 10 $PY art/review/tools/r1_concepts.py palette     # art/review/concepts/palette-D1.png (+ mock PNGs)
    nice -n 10 $PY art/review/tools/r1_concepts.py logo        # art/review/concepts/logo-LG1.png (+ 12 layer PNGs)
    nice -n 10 $PY art/review/tools/r1_concepts.py boss        # art/review/concepts/boss-v2.png
    nice -n 10 $PY art/review/tools/r1_concepts.py crew        # art/review/concepts/crew-digger.png (A | B | new, 1/3 thumbs)
    nice -n 10 $PY art/review/tools/r1_concepts.py icon        # art/review/concepts/icon-IC1.png (512 + 180/120/60/40 strip)
    nice -n 10 $PY art/review/tools/r1_concepts.py calib       # tools/copygate.json + art/review/concepts/copygate-calibration.json
    nice -n 10 $PY art/review/tools/r1_concepts.py owner       # art/review/concepts/OWNER-SHEET.png

Inputs: the route3d drafts of art/pipeline/items/char_concepts_d1.py (build/ui-art/route3d/concept_*.png), today's
shipped art (art/out, art/ui/out), our captures (build/compare/captures) and the original's shots (research/…: LOOKED AT
and measured by copygate only; never sampled into an asset). The palette mock is a per-FAMILY LCh remap of our own
captures that keeps each pixel's L* and relative chroma (the art-direction.md §7.3 codemod rule), i.e. a faithful preview
of what R9/A5 do to the code literals; it is not an asset.
"""
from __future__ import annotations

import json
import math
import os
import sys

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
APP = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, os.path.join(APP, "tools"))
import copygate as CG  # noqa: E402

OUT = os.path.join(APP, "art", "review", "concepts")
R3D = os.path.join(APP, "build", "ui-art", "route3d")
FONT_BOLD = "/System/Library/Fonts/Supplemental/Arial Bold.ttf"
FONT = "/System/Library/Fonts/Supplemental/Arial.ttf"
TITAN = os.path.join(APP, "..", "matchfactory", "design", "fonts", "TitanOne-Regular.ttf")   # OFL (OFL-TitanOne.txt)
PCD = os.path.join(APP, "App", "Resources", "Fonts", "PCDisplay-Black.ttf")                     # our Nunito (OFL)


def P(*a):
    return os.path.join(APP, *a)


def font(size, bold=True):
    try:
        return ImageFont.truetype(FONT_BOLD if bold else FONT, size)
    except Exception:
        return ImageFont.load_default()


def label(im, text, size=28, fill=(30, 30, 30), bg=None, pad=10):
    f = font(size)
    d = ImageDraw.Draw(im)
    w = d.textlength(text, font=f)
    out = Image.new("RGB", (max(im.width, int(w) + 2 * pad), im.height + size + 2 * pad), bg or (255, 255, 255))
    out.paste(im.convert("RGB"), (0, size + 2 * pad))
    ImageDraw.Draw(out).text((pad, pad // 2), text, fill=fill, font=f)
    return out


def hstack(ims, gap=24, bg=(255, 255, 255), valign="top"):
    H = max(i.height for i in ims)
    W = sum(i.width for i in ims) + gap * (len(ims) - 1)
    out = Image.new("RGB", (W, H), bg)
    x = 0
    for i in ims:
        y = 0 if valign == "top" else (H - i.height if valign == "bottom" else (H - i.height) // 2)
        out.paste(i.convert("RGB"), (x, y))
        x += i.width + gap
    return out


def vstack(ims, gap=24, bg=(255, 255, 255)):
    W = max(i.width for i in ims)
    H = sum(i.height for i in ims) + gap * (len(ims) - 1)
    out = Image.new("RGB", (W, H), bg)
    y = 0
    for i in ims:
        out.paste(i.convert("RGB"), (0, y))
        y += i.height + gap
    return out


def title_block(title, sub, width, size=40):
    f1, f2 = font(size), font(int(size * 0.55), bold=False)
    lines = []
    d0 = ImageDraw.Draw(Image.new("RGB", (10, 10)))
    for para in sub.split("\n"):
        words, cur = para.split(), ""
        for w in words:
            t = (cur + " " + w).strip()
            if d0.textlength(t, font=f2) > width - 40:
                lines.append(cur)
                cur = w
            else:
                cur = t
        lines.append(cur)
    lh = int(size * 0.55 * 1.35)
    im = Image.new("RGB", (width, size + 30 + lh * len(lines) + 10), (255, 255, 255))
    d = ImageDraw.Draw(im)
    d.text((20, 10), title, fill=(20, 20, 20), font=f1)
    for i, ln in enumerate(lines):
        d.text((20, size + 24 + i * lh), ln, fill=(70, 70, 70), font=f2)
    return im


def on_bg(im, color):
    im = im.convert("RGBA")
    base = Image.new("RGBA", im.size, tuple(color) + (255,))
    base.alpha_composite(im)
    return base.convert("RGB")


def scaled(im, f):
    return im.resize((max(1, round(im.width * f)), max(1, round(im.height * f))), Image.LANCZOS)


# ================================================================== colour maths

def rgb2lab(a):
    return CG.rgb2lab(np.asarray(a, np.float64))


def lab2rgb(lab):
    L, a, b = lab[..., 0], lab[..., 1], lab[..., 2]
    fy = (L + 16) / 116
    fx = fy + a / 500
    fz = fy - b / 200

    def finv(t):
        return np.where(t ** 3 > 0.008856, t ** 3, (t - 16 / 116) / 7.787)
    xyz = np.stack([finv(fx) * 0.95047, finv(fy), finv(fz) * 1.08883], -1)
    m = np.array([[3.240479, -1.537150, -0.498535], [-0.969256, 1.875992, 0.041556], [0.055648, -0.204043, 1.057311]])
    c = xyz @ m.T
    c = np.where(c > 0.0031308, 1.055 * np.clip(c, 0, None) ** (1 / 2.4) - 0.055, 12.92 * c)
    return np.clip(c * 255, 0, 255)


def hex_lab(h):
    h = h.lstrip("#")
    return rgb2lab(np.array([[int(h[i:i + 2], 16) for i in (0, 2, 4)]], float))[0]


def lch(lab):
    return lab[..., 0], np.hypot(lab[..., 1], lab[..., 2]), np.degrees(np.arctan2(lab[..., 2], lab[..., 1])) % 360


# D1 token families (art-direction.md §3.1 "UI colour shift"): theirs-anchor -> D1-anchor. A pixel whose hue lies in the
# family window is rotated by the anchors' hue difference and its chroma scaled by their chroma ratio; L* is kept
# (the §7.3 codemod rule). `rect` limits a family to an element (the ribbon's yellow must not touch the coin's gold).
FAMILIES = [
    dict(name="chrome-blue", src="#0192FF", dst="#17B3A3", hw=38.0, cmin=10.0),
    dict(name="cta-green", src="#00E400", dst="#FFB422", hw=32.0, cmin=14.0),
    dict(name="ribbon-yellow", src="#FFCF00", dst="#F0B86A", hw=22.0, cmin=20.0, rect_key="ribbon"),
    dict(name="ribbon-orange", src="#F29400", dst="#C98A45", hw=14.0, cmin=25.0, rect_key="ribbon"),
]


def recolor(img, rects=None):
    """Per-family LCh remap of an RGB(A) capture (see FAMILIES). rects: {rect_key: (x, y, w, h) pt on a 393-pt screen}."""
    im = img.convert("RGB")
    a = np.asarray(im).astype(np.float64)
    lab = rgb2lab(a)
    L, C, h = lch(lab)
    s = im.width / 393.0
    yy, xx = np.mgrid[0:im.height, 0:im.width]
    out_a, out_b = lab[..., 1].copy(), lab[..., 2].copy()
    wsum = np.zeros_like(L)
    for fam in FAMILIES:
        sl, dl = hex_lab(fam["src"]), hex_lab(fam["dst"])
        _, sc, sh = (float(v[0]) for v in lch(sl[None]))
        _, dc, dh = (float(v[0]) for v in lch(dl[None]))
        dhue = float((dh - sh + 180) % 360 - 180)
        cr = float(dc / sc)
        dist = np.abs((h - sh + 180) % 360 - 180)
        w = np.clip(1 - (dist - fam["hw"] * 0.6) / (fam["hw"] * 0.4), 0, 1) * np.clip((C - fam["cmin"]) / 8.0, 0, 1)
        if fam.get("rect_key"):
            r = (rects or {}).get(fam["rect_key"])
            if r is None:
                continue
            x, y, ww, hh = [v * s for v in r]
            w = w * ((xx >= x) & (xx < x + ww) & (yy >= y) & (yy < y + hh))
        nh = np.radians(h + dhue)
        nc = C * cr
        out_a = out_a * (1 - w) + (nc * np.cos(nh)) * w
        out_b = out_b * (1 - w) + (nc * np.sin(nh)) * w
        wsum += w
    new = np.stack([L, out_a, out_b], -1)
    rgb = lab2rgb(new)
    return Image.fromarray(rgb.astype(np.uint8), "RGB")


PAUSE_RECTS = {"ribbon": (55, 185, 285, 100)}


def cmd_palette():
    os.makedirs(OUT, exist_ok=True)
    ours = Image.open(P("build/compare/captures/pause-en.png"))
    theirs = Image.open(P("research/shots/007-L32-pause.png"))
    mock = recolor(ours, PAUSE_RECTS)
    mock.save(os.path.join(OUT, "palette-D1-pause.png"))
    hud = Image.open(P("build/compare/captures/hud-L32-en.png"))
    hud_mock = recolor(hud, {})
    hud_mock.save(os.path.join(OUT, "palette-D1-hud.png"))
    hud_theirs = Image.open(P("research/shots/003-L32-start.png"))
    W = 393 * 2
    col = []
    for im, cap in ((ours, "ours today"), (mock, "D1 palette mock"), (theirs, "the original (v552)")):
        col.append(label(scaled(im.convert("RGB"), W / im.width), cap, 30))
    row1 = hstack(col, 30)
    strip = []
    for im, cap in ((hud, "HUD today"), (hud_mock, "HUD D1 mock"), (hud_theirs, "HUD original")):
        c = scaled(im.convert("RGB"), W / im.width).crop((0, 40 * 2, W, 125 * 2))
        c2 = scaled(im.convert("RGB"), W / im.width).crop((0, 750 * 2, W, 830 * 2))
        strip.append(label(vstack([c, c2], 6), cap, 30))
    row2 = hstack(strip, 30)
    reg = {s["id"]: s["regions"] for s in json.load(open(P("tools/compare/regions.json")))["shots"]}
    m_today = CG.measure(P("build/compare/captures/pause-en.png"), P("research/shots/007-L32-pause.png"))
    m_today["chrome"] = CG.chrome_delta(P("build/compare/captures/pause-en.png"), P("research/shots/007-L32-pause.png"), reg["pause"])
    m_mock = CG.measure(os.path.join(OUT, "palette-D1-pause.png"), P("research/shots/007-L32-pause.png"))
    m_mock["chrome"] = CG.chrome_delta(os.path.join(OUT, "palette-D1-pause.png"), P("research/shots/007-L32-pause.png"), reg["pause"])
    note = (f"copygate vs 007 — today: SSIM {m_today['ssim']:.3f}, overlap {m_today['overlap']:.3f}, chrome ΔE00 median "
            f"{m_today['chrome']['median']:.1f};  D1 mock: SSIM {m_mock['ssim']:.3f}, overlap {m_mock['overlap']:.3f}, chrome ΔE00 "
            f"median {m_mock['chrome']['median']:.1f}.  Family remap keeps L* (chrome blue → teal #17B3A3, go-green → tangerine #FFB422, "
            "ribbon yellow → honey wood #F0B86A; red Quit, cream card, hearts, coins untouched). The ribbon's PLANK shape and the "
            "chrome's shape shift are component changes (A5), not shown here.")
    hdr = title_block("D1 palette mock — Paused + HUD", note, row1.width)
    sheet = vstack([hdr, row1, row2], 20)
    sheet.save(os.path.join(OUT, "palette-D1.png"))
    json.dump(dict(today=m_today, mock=m_mock), open(os.path.join(OUT, "palette-D1.json"), "w"), indent=1, default=float)
    print("palette:", note)


# ================================================================== LG-1 "Signpost plank" logo sketch (layer contract kept)

LW, LH = 918, 708          # logoArrowOut@3x canvas (306 x 236 pt)


def _noise2(h, w, scale, seed):
    rng = np.random.default_rng(seed)
    g = rng.random((h // scale + 3, w // scale + 3))
    im = Image.fromarray((g * 255).astype(np.uint8)).resize((w + 3 * scale, h + 3 * scale), Image.BICUBIC)
    return np.asarray(im, np.float32)[:h, :w] / 255.0


def _noise_aniso(h, w, sx, sy, seed):
    rng = np.random.default_rng(seed)
    g = rng.random((h // sy + 3, w // sx + 3))
    im = Image.fromarray((g * 255).astype(np.uint8)).resize(((w // sx + 3) * sx, (h // sy + 3) * sy), Image.BICUBIC)
    return np.asarray(im, np.float32)[:h, :w] / 255.0


def _wood(h, w, c_light, c_dark, seed=1, freq=0.11, warp=14.0, angle=0.0):
    """Planed timber: grain lines running along x (slow waves + knots of density), thin long streaks, pores."""
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    wave = _noise_aniso(h, w, 180, 40, seed) * warp + _noise_aniso(h, w, 70, 14, seed + 1) * warp * 0.35
    t = (yy * math.cos(angle) - xx * math.sin(angle)) * freq + wave
    s = (0.5 + 0.5 * np.sin(t)) ** 4
    streak = _noise_aniso(h, w, 90, 2, seed + 2)
    pores = _noise_aniso(h, w, 6, 1, seed + 3)
    k = np.clip(s * 0.62 + (streak - 0.5) * 0.45 + (pores - 0.5) * 0.12 + 0.18, 0, 1)[..., None]
    a, b = np.array(c_light, np.float32), np.array(c_dark, np.float32)
    return a * (1 - k) + b * k


def _hex(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def _mask(poly, size, blur=0):
    m = Image.new("L", size, 0)
    ImageDraw.Draw(m).polygon(poly, fill=255)
    if blur:
        m = m.filter(ImageFilter.GaussianBlur(blur))
    return m


def _wobble(pts, amp, seed):
    rng = np.random.default_rng(seed)
    out = []
    for i, (x, y) in enumerate(pts):
        out.append((x + rng.normal(0, amp), y + rng.normal(0, amp)))
    return out


def _dense(poly, step=6.0):
    out = []
    for i in range(len(poly)):
        (x0, y0), (x1, y1) = poly[i], poly[(i + 1) % len(poly)]
        n = max(1, int(math.hypot(x1 - x0, y1 - y0) / step))
        for k in range(n):
            out.append((x0 + (x1 - x0) * k / n, y0 + (y1 - y0) * k / n))
    return out


def _round_poly(pts, r, n=6):
    out = []
    m = len(pts)
    for i in range(m):
        p0, p1, p2 = np.array(pts[i - 1], float), np.array(pts[i], float), np.array(pts[(i + 1) % m], float)
        a, b = p0 - p1, p2 - p1
        la, lb = np.linalg.norm(a), np.linalg.norm(b)
        rr = min(r, la / 2.2, lb / 2.2)
        s0, s1 = p1 + a / la * rr, p1 + b / lb * rr
        for k in range(n + 1):
            t = k / n
            q = (1 - t) ** 2 * s0 + 2 * (1 - t) * t * p1 + t ** 2 * s1
            out.append(tuple(q))
    return out


def _slab(poly, face_rgb, side_rgb, depth, grain=None, seed=0, edge_dark=(40, 22, 10), bevel=10):
    """A board: side (extrusion, `depth` px straight down, darker), face (wood/paint), a soft inner bevel, a dark outline."""
    size = (LW, LH)
    lay = Image.new("RGBA", size, (0, 0, 0, 0))
    fm = _mask(poly, size)
    side = Image.new("RGBA", size, tuple(side_rgb) + (255,))
    sm = Image.new("L", size, 0)
    for k in range(depth, 0, -1):
        sm.paste(255, (0, 0), fm.transform(size, Image.AFFINE, (1, 0, 0, 0, 1, -k)))
    shade = np.asarray(sm, np.float32) / 255.0
    sidearr = np.asarray(side, np.float32).copy()
    yy = np.mgrid[0:LH, 0:LW][0].astype(np.float32)
    sidearr[..., :3] *= (0.92 - 0.10 * _noise2(LH, LW, 20, seed + 5))[..., None]
    sidearr[..., 3] = shade * 255
    lay.alpha_composite(Image.fromarray(sidearr.astype(np.uint8), "RGBA"))
    face = np.zeros((LH, LW, 4), np.float32)
    if grain is not None:
        face[..., :3] = grain
    else:
        face[..., :3] = np.array(face_rgb, np.float32)
    fa = np.asarray(fm, np.float32) / 255.0
    inner = np.asarray(fm.filter(ImageFilter.GaussianBlur(bevel)), np.float32) / 255.0
    up = np.asarray(fm.transform(size, Image.AFFINE, (1, 0, 0, 0, 1, 7)).filter(ImageFilter.GaussianBlur(bevel * 0.6)), np.float32) / 255.0
    dn = np.asarray(fm.transform(size, Image.AFFINE, (1, 0, 0, 0, 1, -7)).filter(ImageFilter.GaussianBlur(bevel * 0.6)), np.float32) / 255.0
    lit = np.clip(fa - up, 0, 1)
    dark = np.clip(fa - dn, 0, 1)
    face[..., :3] = face[..., :3] * (0.82 + 0.18 * inner[..., None]) + 60 * lit[..., None] - 55 * dark[..., None]
    face[..., 3] = fa * 255
    lay.alpha_composite(Image.fromarray(np.clip(face, 0, 255).astype(np.uint8), "RGBA"))
    # outline
    ol = fm.filter(ImageFilter.MaxFilter(5))
    om = np.clip(np.asarray(ol, np.float32) - np.asarray(fm, np.float32) + shade * 0, 0, 255)
    o = Image.new("RGBA", size, tuple(edge_dark) + (0,))
    oa = np.asarray(o).copy()
    oa[..., 3] = om.astype(np.uint8)
    lay.alpha_composite(Image.fromarray(oa, "RGBA"))
    return lay


def _glyph_layer(ch, fnt, xy, rot, face_top, face_bot, ext_top, ext_bot, depth, outline, ow=9):
    """One letter as a LAYER: extrusion (straight down), dark outline, face gradient + inner bevel (the logo pipeline's
    Ext/Face pair idea, flattened for the sketch)."""
    size = (LW, LH)
    tmp = Image.new("L", (600, 600), 0)
    d = ImageDraw.Draw(tmp)
    bb = d.textbbox((0, 0), ch, font=fnt)
    d.text((300 - (bb[0] + bb[2]) / 2, 300 - (bb[1] + bb[3]) / 2), ch, fill=255, font=fnt)
    tmp = tmp.rotate(rot, resample=Image.BICUBIC)
    m = Image.new("L", size, 0)
    m.paste(tmp, (int(xy[0] - 300), int(xy[1] - 300)))
    lay = Image.new("RGBA", size, (0, 0, 0, 0))
    fat = m.filter(ImageFilter.MaxFilter(ow | 1))
    # extrusion
    ext = Image.new("L", size, 0)
    for k in range(depth, 0, -1):
        ext = ImageChops.lighter(ext, fat.transform(size, Image.AFFINE, (1, 0, 0, 0, 1, -k)))
    yy = np.mgrid[0:LH, 0:LW][0].astype(np.float32)
    y0, y1 = xy[1] - 80, xy[1] + 110
    t = np.clip((yy - y0) / (y1 - y0), 0, 1)[..., None]
    extc = np.array(ext_top, np.float32) * (1 - t) + np.array(ext_bot, np.float32) * t
    ea = np.zeros((LH, LW, 4), np.float32)
    ea[..., :3] = extc
    ea[..., 3] = np.asarray(ext, np.float32)
    lay.alpha_composite(Image.fromarray(ea.astype(np.uint8), "RGBA"))
    # outline (around the face) = the fat mask in the outline colour
    oa = np.zeros((LH, LW, 4), np.float32)
    oa[..., :3] = np.array(outline, np.float32)
    oa[..., 3] = np.asarray(fat, np.float32)
    lay.alpha_composite(Image.fromarray(oa.astype(np.uint8), "RGBA"))
    # face with a vertical gradient and a puffy inner bevel
    y0, y1 = xy[1] - 70, xy[1] + 70
    t = np.clip((yy - y0) / (y1 - y0), 0, 1)[..., None]
    fc = np.array(face_top, np.float32) * (1 - t) + np.array(face_bot, np.float32) * t
    fa = np.asarray(m, np.float32) / 255.0
    up = np.asarray(m.transform(size, Image.AFFINE, (1, 0, 0, 0, 1, 6)).filter(ImageFilter.GaussianBlur(4)), np.float32) / 255.0
    dn = np.asarray(m.transform(size, Image.AFFINE, (1, 0, -4, 0, 1, -8)).filter(ImageFilter.GaussianBlur(5)), np.float32) / 255.0
    fc = fc + 45 * np.clip(fa - up, 0, 1)[..., None] - 60 * np.clip(fa - dn, 0, 1)[..., None]
    face = np.zeros((LH, LW, 4), np.float32)
    face[..., :3] = fc
    face[..., 3] = fa * 255
    lay.alpha_composite(Image.fromarray(np.clip(face, 0, 255).astype(np.uint8), "RGBA"))
    return lay


def _rope(p0, p1, width=16, seed=0):
    size = (LW, LH)
    lay = Image.new("RGBA", size, (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    x0, y0 = p0
    x1, y1 = p1
    n = int(math.hypot(x1 - x0, y1 - y0) / 3)
    pts = []
    for k in range(n + 1):
        t = k / n
        sag = math.sin(t * math.pi) * 10
        pts.append((x0 + (x1 - x0) * t + sag * 0.3, y0 + (y1 - y0) * t))
    d.line(pts, fill=(58, 34, 16, 255), width=width + 6, joint="curve")
    d.line(pts, fill=(214, 178, 120, 255), width=width, joint="curve")
    # twist: diagonal strand shadows
    for k in range(0, n, 3):
        x, y = pts[k]
        d.line([(x - width * 0.45, y - 3), (x + width * 0.45, y + 4)], fill=(150, 112, 62, 255), width=3)
    d.line([(p[0] - width * 0.25, p[1]) for p in pts], fill=(240, 214, 164, 200), width=3)
    return lay


def logo_layers():
    """-> ordered [(layer_id, role, RGBA)]: the LOGO-SPEC contract = bottom sign, hanger, top plate, 5 ARROW letters,
    4 OUT! glyphs (paint order)."""
    # ---- bottom sign: a mint-painted plank ARROW with a notched tail (a real signpost arm), tilted -3 deg
    ax0, ay0, ax1, ay1, htip, hover = 130, 420, 690, 610, 845, 40
    acx, acy = (ax0 + htip) / 2, (ay0 + ay1) / 2
    notch = 70
    arrow = [(ax0, ay0), (ax1, ay0), (ax1, ay0 - hover), (htip, acy), (ax1, ay1 + hover), (ax1, ay1), (ax0, ay1), (ax0 + notch, acy)]
    t = math.radians(-3)
    arrow = [(acx + (x - acx) * math.cos(t) - (y - acy) * math.sin(t), acy + (x - acx) * math.sin(t) + (y - acy) * math.cos(t)) for x, y in arrow]
    arrow = _round_poly(arrow, 22)
    arrow = _wobble(_dense(arrow, 10), 1.3, 3)
    paint = _wood(LH, LW, _hex("#5FD3B0"), _hex("#3FC39C"), seed=11, freq=0.09, warp=8)
    paint = paint * 0.85 + np.array(_hex("#3FC39C"), np.float32) * 0.15
    sign = _slab(arrow, None, _hex("#7E4E27"), 26, grain=paint, seed=11, edge_dark=(28, 52, 44))
    # painted edge line + two chips showing the timber under the paint
    d = ImageDraw.Draw(sign)
    inner = _round_poly([(ax0 + 22, ay0 + 22), (ax1 - 6, ay0 + 22), (ax1 - 6, ay0 - hover + 34), (htip - 44, acy),
                         (ax1 - 6, ay1 + hover - 34), (ax1 - 6, ay1 - 22), (ax0 + 22, ay1 - 22), (ax0 + notch + 16, acy)], 14)
    inner = [(acx + (x - acx) * math.cos(t) - (y - acy) * math.sin(t), acy + (x - acx) * math.sin(t) + (y - acy) * math.cos(t)) for x, y in inner]
    d.line(inner + inner[:1], fill=(30, 138, 108, 255), width=5)
    for cx, cy, r in ((200, 440, 12), (640, 596, 9), (760, 470, 7)):
        d.ellipse((cx - r, cy - r * 0.6, cx + r, cy + r * 0.6), fill=(201, 142, 78, 255))
    layers = [("logoSignPurple", "bottom sign (mint plank arrow, notched tail)", sign)]
    # ---- hanger: two rope loops
    hang = Image.new("RGBA", (LW, LH), (0, 0, 0, 0))
    for x in (300, 575):
        hang.alpha_composite(_rope((x - 12, 300), (x + 4, 440), 15, seed=x))
        hang.alpha_composite(_rope((x + 22, 300), (x + 30, 436), 15, seed=x + 1))
    layers.append(("logoPegs", "hanger (two rope loops)", hang))
    # ---- top plate: carved honey-wood plank, irregular carved edge, grain, 4 iron bolts, no white rim
    plate = [(40, 70), (878, 50), (895, 120), (870, 330), (60, 350), (28, 250)]
    plate = _round_poly(plate, 40)
    plate = _wobble(_dense(plate, 12), 2.4, 7)
    wood = _wood(LH, LW, _hex("#EDB977"), _hex("#B97A3E"), seed=21, freq=0.075, warp=16, angle=0.03)
    top = _slab(plate, None, _hex("#7E4E27"), 30, grain=wood, seed=21, edge_dark=(58, 30, 14), bevel=14)
    d = ImageDraw.Draw(top)
    for bx, by in ((78, 100), (842, 84), (838, 305), (90, 318)):
        d.ellipse((bx - 15, by - 15, bx + 15, by + 15), fill=(58, 60, 66, 255))
        d.ellipse((bx - 11, by - 11, bx + 9, by + 9), fill=(112, 116, 124, 255))
        d.ellipse((bx - 7, by - 8, bx - 1, by - 2), fill=(196, 200, 206, 255))
    layers.append(("logoSignBlue", "top plate (carved honey-wood plank + iron bolts)", top))
    # ---- words (Titan One, OFL): ARROW cream/teal-extrusion; OUT! sunflower/burnt-orange
    ft = ImageFont.truetype(TITAN, 205)
    fo = ImageFont.truetype(TITAN, 150)
    xs = [150, 300, 452, 610, 770]
    ys = [195, 190, 192, 189, 193]
    tilts = [5, -3, 2, -4, 4]
    for i, ch in enumerate("ARROW"):
        lay = _glyph_layer(ch, ft, (xs[i], ys[i]), tilts[i], _hex("#FFF7E3"), _hex("#FFE3A8"), _hex("#17857A"),
                           _hex("#0E5A55"), 30, _hex("#3A1E0E"), ow=11)
        layers.append((["logoLetterA", "logoLetterR1", "logoLetterR2", "logoLetterO", "logoLetterW"][i], f"letter {ch}", lay))
    xo = [318, 438, 548, 632]
    for i, ch in enumerate("OUT!"):
        lay = _glyph_layer(ch, fo, (xo[i], 522 + (0 if i < 3 else -3)), [-3, 2, -2, 5][i], _hex("#FFD84A"), _hex("#FFB714"),
                           _hex("#D8800F"), _hex("#A65A08"), 24, _hex("#3A1E0E"), ow=11)
        layers.append((["logoOutO", "logoOutU", "logoOutT", "logoOutBang"][i], f"glyph {ch}", lay))
    return layers


def cmd_logo():
    os.makedirs(os.path.join(OUT, "logo-LG1-layers"), exist_ok=True)
    L = logo_layers()
    comp = Image.new("RGBA", (LW, LH), (0, 0, 0, 0))
    # drop shadow of the whole logo (as today's)
    for lid, role, im in L:
        comp.alpha_composite(im)
        im.save(os.path.join(OUT, "logo-LG1-layers", f"{lid}.png"))
    comp.save(os.path.join(OUT, "logo-LG1.png"))
    today = Image.open(P("art/ui/out/logoArrowOut@3x.png")).convert("RGBA")
    theirs = Image.open(P("research/store/iphone-8.png")).convert("RGB")
    s8 = theirs.width / 440.0
    th_crop = theirs.crop((int(25 * s8), int(70 * s8), int(240 * s8), int(242 * s8)))
    bg = (18, 70, 76)
    col = [label(on_bg(scaled(today, 0.6), bg), "today", 26), label(on_bg(scaled(comp, 0.6), bg), "LG-1 sketch (D1)", 26),
           label(scaled(th_crop, 551 / th_crop.width), "the original (store 8, looked at)", 26)]
    row = hstack(col, 24)
    thumbs = []
    for lid, role, im in L:
        bb = im.getbbox()
        t = on_bg(im.crop(bb), (235, 235, 235))
        t = scaled(t, min(150 / t.width, 110 / t.height))
        c = Image.new("RGB", (160, 150), (255, 255, 255))
        c.paste(t, ((160 - t.width) // 2, (120 - t.height) // 2))
        ImageDraw.Draw(c).text((4, 128), lid.replace("logo", ""), fill=(40, 40, 40), font=font(15))
        thumbs.append(c)
    strip = hstack(thumbs, 8)
    note = ("The layer contract is kept: bottom sign (still id logoSignPurple), hanger (logoPegs), top plate (logoSignBlue), "
            "5 ARROW letters, 4 OUT! glyphs, same paint order, so LOGO-SPEC's tracks regenerate from anchors (R6). Changed: "
            "shape (carved plank, notched signpost arrow), material (timber + paint, no white rim, no glossy plate), colour "
            "(cream/teal ARROW, sunflower/orange OUT!), hanger (rope, not pegs) and typeface (Titan One, OFL, instead of "
            "the Nunito match). Sketch in PIL: the R6 art is regenerated by gen_icons.py with Ext/Face/Flat pairs.")
    sheet = vstack([title_block("Logo restyle LG-1 “Signpost plank” — keeps ARROW OUT! + the 12-layer contract", note, row.width),
                    row, label(strip, "the 12 layers (paint order) = the motion contract", 24)], 16)
    sheet.save(os.path.join(OUT, "logo-LG1-sheet.png"))
    print("logo: wrote", len(L), "layers")


# ================================================================== boss old -> new

def cmd_boss():
    old = Image.open(P("art/out/char_sci_home@3x.png")).convert("RGBA")
    new = Image.open(os.path.join(R3D, "concept_bossV2_home.png")).convert("RGBA")
    bg_old, bg_new = (58, 91, 176), (46, 89, 97)
    row = hstack([label(on_bg(old, bg_old), "today (rig full render, lab light)", 26),
                  label(on_bg(new, bg_new), "boss v2 (D1 light, same camera / frame / pose)", 26)], 30)
    z = 2
    box_ = (130, 20, 450, 300)
    heads = hstack([label(scaled(on_bg(old, bg_old).crop(box_), z), "today, head 2x", 24),
                    label(scaled(on_bg(new, bg_new).crop(box_), z), "v2, head 2x", 24)], 30)
    thumbs = hstack([label(on_bg(scaled(old, 1 / 3), bg_old), "1/3", 20), label(on_bg(scaled(new, 1 / 3), bg_new), "1/3", 20)], 30)
    note = ("Ruling 38 minimal set: two short curved ivory horns (2 soft growth rings) instead of the crown tuft; a blush "
            "muzzle patch (its own fur + LUT; the edge is still grainy at 2x: R2 blends it); amber eyes; one snaggle fang; teal canvas foreman coat (placket, brass buttons, rounded corduroy "
            "collar, rolled sleeves, blueprint roll in the breast pocket) instead of lab coat + lanyard + badge + pen; goggles "
            "pushed up between the horns; a timber scaffold rail + brass lever instead of the console; paws grip rail/lever "
            "(not both flat). Kept: the pink strand fur, face, smile, fur ladder, size and role.")
    sheet = vstack([title_block("Boss v2 — old → new", note, max(row.width, heads.width)), row, heads, thumbs], 16)
    sheet.save(os.path.join(OUT, "boss-v2.png"))
    print("boss sheet written")


# ================================================================== crew calibration card

def cmd_crew():
    sci = Image.open(P("art/out/char_sci_home@3x.png")).convert("RGBA")
    wk = Image.open(P("art/out/char_wk_homeL_blue@3x.png")).convert("RGBA")
    dg = Image.open(os.path.join(R3D, "concept_digger_hero.png")).convert("RGBA")
    bg = (46, 89, 97)
    cells = [label(on_bg(sci, (58, 91, 176)), "A: our pink boss (fur) — calibration", 24),
             label(on_bg(wk, (58, 91, 176)), "B: today's worker (\"dough\")", 24),
             label(on_bg(dg, bg), "NEW: Digger crew hero (velvet fur)", 24)]
    row = hstack(cells, 30, valign="bottom")
    th = []
    for im, b in ((sci, (58, 91, 176)), (wk, (58, 91, 176)), (dg, bg)):
        t = on_bg(scaled(im, 1 / 3), b)
        a = np.asarray(scaled(im, 1 / 3))[..., 3] > 128
        sil = Image.fromarray(np.where(a, 30, 235).astype(np.uint8)).convert("RGB")
        th.append(hstack([t, sil], 8))
    trow = hstack([label(t, "1/3 size + silhouette", 20) for t in th], 30, valign="bottom")
    zoom = hstack([label(scaled(on_bg(dg, bg).crop((130, 20, 360, 250)), 2), "Digger head 2x (fur, sockets, lids, brows, nose)", 22),
                   label(scaled(on_bg(wk, (58, 91, 176)).crop((80, 20, 310, 240)), 2), "today's worker head 2x", 22)], 30)
    note = ("Same game scale as the home workers (57 pt/u, 3 px/pt). A-bar R1-R8 check in the R1 report: velvet strand fur on "
            "every body surface (R1); vest/belt/hat/goggles/claws/pads meet the fur at constructed edges (R2); >= 6 materials "
            "from gloss eyes (0.18) to fabric vest (0.78), no clearcoat on fur (R3); eyes in sockets under fur lids with fur "
            "brows + 2 glints (R4); head/snout/hat/paws read at 1/3 (R5); CHAR_LIGHT family, rim 1150 lx (R6); vest = shell with "
            "arm holes + V opening + binding tape + zip + stripe (R7); rig split is R2's job (R8).")
    sheet = vstack([title_block("Crew hero — the Digger next to the A/B calibration card", note, row.width), row, trow, zoom], 16)
    sheet.save(os.path.join(OUT, "crew-digger.png"))
    print("crew sheet written")


# ================================================================== icon

def cmd_icon():
    ic = Image.open(os.path.join(R3D, "concept_iconIC1.png")).convert("RGB")
    ic.save(os.path.join(OUT, "icon-IC1-512.png"))
    today = Image.open(P("art/out/appIcon1024.png")).convert("RGB")
    theirs = Image.open(P("research/store/icon-1024.png")).convert("RGB")

    def rounded(im, px):
        im = im.resize((px, px), Image.LANCZOS)
        m = Image.new("L", (px, px), 0)
        ImageDraw.Draw(m).rounded_rectangle((0, 0, px - 1, px - 1), radius=int(px * 0.225), fill=255)
        out = Image.new("RGBA", (px, px), (0, 0, 0, 0))
        out.paste(im, (0, 0), m)
        return out
    strips = []
    for wall, name in (((236, 236, 240), "light wallpaper"), ((28, 30, 36), "dark wallpaper")):
        cells = []
        for px in (180, 120, 60, 40):
            c = Image.new("RGB", (px + 30, 210), wall)
            c.paste(rounded(ic, px), (15, 15), rounded(ic, px))
            cells.append(c)
        strips.append(label(hstack(cells, 0, bg=wall), f"IC-1 at 180 / 120 / 60 / 40 px — {name}", 22))
    big = hstack([label(rounded(ic, 512).convert("RGB") if False else on_bg(rounded(ic, 512), (255, 255, 255)), "IC-1 draft (512)", 26),
                  label(on_bg(rounded(today, 256), (255, 255, 255)), "today", 26),
                  label(on_bg(rounded(theirs, 256), (255, 255, 255)), "the original (looked at)", 26)], 30)
    m = CG.measure(os.path.join(OUT, "icon-IC1-512.png"), P("research/store/icon-1024.png"))
    m0 = CG.measure(P("art/out/appIcon1024.png"), P("research/store/icon-1024.png"))
    note = (f"copygate vs the original's store icon — today: SSIM {m0['ssim']:.3f} / overlap {m0['overlap']:.3f}; IC-1: SSIM "
            f"{m['ssim']:.3f} / overlap {m['overlap']:.3f} (icon gate SSIM < 0.25, overlap < 0.40). One chunky tangerine arrow "
            "bursting out of a maze block's doorway, a Digger clinging to it, the hard hat flying off, teal ground with an "
            "embossed maze. No white ground, no three-arrow row, no text.")
    sheet = vstack([title_block("Icon draft IC-1 “Out the Door”", note, big.width), big] + strips, 16)
    sheet.save(os.path.join(OUT, "icon-IC1.png"))
    print("icon:", note)


# ================================================================== copygate recalibration

def _matte_theirs(img, box_pt, shot_w_pt=393.0, bg=(128, 128, 128)):
    """Crude character matte on the original's shot (LOOKED-AT reference, used only for the metric): pixels close to the
    crop's border colour statistics (the lab wall) go to neutral grey."""
    im = img.convert("RGB")
    s = im.width / shot_w_pt
    x, y, w, h = box_pt
    c = im.crop((int(x * s), int(y * s), int((x + w) * s), int((y + h) * s)))
    a = np.asarray(c).astype(np.float64)
    lab = rgb2lab(a)
    border = np.concatenate([lab[:4].reshape(-1, 3), lab[-4:].reshape(-1, 3), lab[:, :4].reshape(-1, 3), lab[:, -4:].reshape(-1, 3)])
    med = np.median(border, 0)
    d = np.linalg.norm(lab - med, axis=-1)
    fg = d > 18
    from scipy import ndimage
    fg = ndimage.binary_opening(fg, iterations=2)
    fg = ndimage.binary_fill_holes(fg)
    lbl, n = ndimage.label(fg)
    if n:
        sizes = ndimage.sum(fg, lbl, range(1, n + 1))
        fg = lbl == (1 + int(np.argmax(sizes)))
    out = np.where(fg[..., None], a, np.array(bg, float))
    return Image.fromarray(out.astype(np.uint8)), fg


def _on_grey(path_or_im, bg=(128, 128, 128)):
    im = path_or_im if isinstance(path_or_im, Image.Image) else Image.open(path_or_im)
    return on_bg(im.convert("RGBA"), bg)


def _measure_images(a, b):
    tmp = os.path.join(APP, "build", "r1", "calib")
    os.makedirs(tmp, exist_ok=True)
    pa, pb = os.path.join(tmp, "_a.png"), os.path.join(tmp, "_b.png")
    a.save(pa)
    b.save(pb)
    return CG.measure(pa, pb)


def _crop_fit(im, target_size, bg=(128, 128, 128)):
    """Fit an RGB(A) image into target_size keeping aspect (centred) on bg."""
    im = im.convert("RGBA")
    tw, th = target_size
    k = min(tw / im.width, th / im.height)
    r = scaled(im, k)
    out = Image.new("RGBA", target_size, tuple(bg) + (255,))
    out.alpha_composite(r, ((tw - r.width) // 2, (th - r.height) // 2))
    return out.convert("RGB")


def cmd_calib():
    os.makedirs(OUT, exist_ok=True)
    cfg = json.load(open(CG.CONFIG))
    rows = []

    def add(pid, kind, role, m, note=""):
        m = dict(m)
        m.update(id=pid, kind=kind, role=role, note=note)
        rows.append(m)
        print(f"{pid:<40s} {kind:<9s} {role:<8s} ssim {m['ssim']:.3f} overlap {m['overlap']:.3f}")
    # --- screens (the documented §2.1 set, re-measured) + the D1 mock
    for pid, a, b, es, eo, role in CG.CALIBRATION:
        kind = "screen"
        m = CG.measure(a, b)
        add(pid, kind, role, m, "art-direction.md §2.1")
    reg = {s["id"]: s["regions"] for s in json.load(open(P("tools/compare/regions.json")))["shots"]}
    for cm in (0.0, 8.0):
        tag = "" if cm else " [no chroma_min]"
        m = CG.measure(os.path.join(OUT, "palette-D1-pause.png"), P("research/shots/007-L32-pause.png"), cmin=cm)
        m["chrome"] = CG.chrome_delta(os.path.join(OUT, "palette-D1-pause.png"), P("research/shots/007-L32-pause.png"), reg["pause"])
        add("D1-pause-mock-vs-007" + tag, "popup", "concept", m, "per-family LCh remap of pause-en (palette mock)")
        m = CG.measure(P("build/compare/captures/pause-en.png"), P("research/shots/007-L32-pause.png"), cmin=cm)
        m["chrome"] = CG.chrome_delta(P("build/compare/captures/pause-en.png"), P("research/shots/007-L32-pause.png"), reg["pause"])
        add("today-pause-vs-007" + tag, "popup", "copy", m)
        m = CG.measure(os.path.join(OUT, "palette-D1-hud.png"), P("research/shots/003-L32-start.png"), crop=[0, 40, 393, 85], cmin=cm)
        add("D1-hud-mock-vs-003" + tag, "hud", "concept", m, "HUD band crop 0,40,393,85 pt")
        m = CG.measure(P("build/compare/captures/hud-L32-en.png"), P("research/shots/003-L32-start.png"), crop=[0, 40, 393, 85], cmin=cm)
        add("today-hud-vs-003" + tag, "hud", "copy", m, "HUD band crop 0,40,393,85 pt")
    hm = os.path.join(OUT, "home-mock-D1-cast.png")
    if os.path.exists(hm):
        add("D1-home-mock(palette+cast)-vs-002", "screen", "concept", CG.measure(hm, P("research/shots/002-home-L32.png")),
            "today's composition, D1 palette + new cast (home-mock-D1.png): expected to FAIL on SSIM until R3")
        add("today-home-L32-vs-002", "screen", "copy", CG.measure(P("build/compare/captures/home-L32-en.png"), P("research/shots/002-home-L32.png")))
    # --- icon (+ 12 unrelated factory icons as controls: what "not a copy" scores on this metric)
    for a in ("partylights", "whitenoise", "hearup", "hiddendevice", "twocam", "storagecleaner", "pomodoro", "strobelight",
              "ledbanner", "trackdetect", "mater", "vincam"):
        ip = os.path.join(APP, "..", a, "App", "Assets.xcassets", "AppIcon.appiconset", "AppIcon.png")
        if os.path.exists(ip):
            add(f"control-icon-{a}", "icon", "control", CG.measure(ip, P("research/store/icon-1024.png")), "an unrelated factory app icon")
    add("today-icon-vs-store", "icon", "copy", CG.measure(P("art/out/appIcon1024.png"), P("research/store/icon-1024.png")))
    add("IC1-draft-vs-store", "icon", "concept", CG.measure(os.path.join(OUT, "icon-IC1-512.png"), P("research/store/icon-1024.png")))
    # --- logo: each on the same teal backdrop vs the store-8 logo crop (their backdrop is part of their art)
    theirs8 = Image.open(P("research/store/iphone-8.png")).convert("RGB")
    s8 = theirs8.width / 440.0
    th_logo = theirs8.crop((int(25 * s8), int(70 * s8), int(240 * s8), int(242 * s8)))
    tsize = th_logo.size
    lg_today = _crop_fit(Image.open(P("art/ui/out/logoArrowOut@3x.png")), tsize, (128, 128, 128))
    lg_new = _crop_fit(Image.open(os.path.join(OUT, "logo-LG1.png")), tsize, (128, 128, 128))
    th_logo_m, _ = _matte_theirs(theirs8, (25, 70, 215, 172), 440.0)
    th_logo_m = th_logo_m.resize(tsize)
    add("today-logo-vs-store8", "logo", "copy", _measure_images(lg_today, th_logo_m), "both on grey (theirs: border-colour matte)")
    add("LG1-sketch-vs-store8", "logo", "concept", _measure_images(lg_new, th_logo_m), "both on grey (theirs: border-colour matte)")
    # --- characters: ours (alpha) on grey vs theirs (border-colour matte) on grey, same crop aspect
    th002 = Image.open(P("research/shots/002-home-L32.png"))
    sci_box = (126, 170, 172, 132)            # 002 scientist incl. console top (pt)
    th_sci, _ = _matte_theirs(th002, sci_box)
    old = Image.open(P("art/out/char_sci_home@3x.png"))
    new = Image.open(os.path.join(R3D, "concept_bossV2_home.png"))
    add("today-boss-vs-002", "character", "copy", _measure_images(_crop_fit(old, th_sci.size), th_sci))
    add("bossV2-vs-002", "character", "concept", _measure_images(_crop_fit(new, th_sci.size), th_sci))
    wk_box = (8, 480, 118, 140)              # 002 left worker (pt)
    th_wk, _ = _matte_theirs(th002, wk_box)
    wk = Image.open(P("art/out/char_wk_homeL_blue@3x.png"))
    dg = Image.open(os.path.join(R3D, "concept_digger_hero.png"))
    add("today-worker-vs-002", "character", "copy", _measure_images(_crop_fit(wk, th_wk.size), th_wk))
    add("digger-vs-002", "character", "concept", _measure_images(_crop_fit(dg, th_wk.size), th_wk))
    # --- controls: unrelated characters (ours vs ours) must pass
    add("control-sci-vs-worker", "character", "control", _measure_images(_crop_fit(old, (300, 300)), _crop_fit(wk, (300, 300))))
    add("control-digger-vs-boss", "character", "control", _measure_images(_crop_fit(dg, (300, 300)), _crop_fit(new, (300, 300))))
    json.dump(dict(rows=rows), open(os.path.join(OUT, "copygate-calibration.json"), "w"), indent=1, default=float)
    return rows


def cmd_owner():
    """One sheet for the owner: boss old -> new, crew hero, icon, palette, logo."""
    W = 2400
    bg = (46, 89, 97)
    old = Image.open(P("art/out/char_sci_home@3x.png")).convert("RGBA")
    new = Image.open(os.path.join(R3D, "concept_bossV2_home.png")).convert("RGBA")
    dg = Image.open(os.path.join(R3D, "concept_digger_hero.png")).convert("RGBA")
    wk = Image.open(P("art/out/char_wk_homeL_blue@3x.png")).convert("RGBA")
    ic = Image.open(os.path.join(OUT, "icon-IC1-512.png")).convert("RGB")
    logo = Image.open(os.path.join(OUT, "logo-LG1.png")).convert("RGBA")
    logo_old = Image.open(P("art/ui/out/logoArrowOut@3x.png")).convert("RGBA")
    pause_old = Image.open(P("build/compare/captures/pause-en.png")).convert("RGB")
    pause_new = Image.open(os.path.join(OUT, "palette-D1-pause.png")).convert("RGB")
    F = font(34)

    def cap(im, t, size=30):
        return label(im, t, size)
    arrow = Image.new("RGB", (90, 200), (255, 255, 255))
    ImageDraw.Draw(arrow).polygon([(10, 80), (55, 80), (55, 55), (85, 100), (55, 145), (55, 120), (10, 120)], fill=(60, 60, 60))
    r1 = hstack([cap(on_bg(scaled(old, 1.2), (58, 91, 176)), "1  BOSS — today"), arrow,
                 cap(on_bg(scaled(new, 1.2), bg), "boss v2 (horns, blush muzzle, amber eyes, tooth, foreman coat, scaffold)"),
                 cap(on_bg(scaled(dg, 1.4), bg), "2  CREW — the Digger (velvet fur)"),
                 cap(on_bg(scaled(wk, 0.7), (58, 91, 176)), "today's worker")], 30, valign="bottom")
    ic_r = ic.resize((420, 420), Image.LANCZOS)
    m = Image.new("L", (420, 420), 0)
    ImageDraw.Draw(m).rounded_rectangle((0, 0, 419, 419), radius=95, fill=255)
    icr = Image.new("RGB", (420, 420), (255, 255, 255))
    icr.paste(ic_r, (0, 0), m)
    small = Image.new("RGB", (220, 420), (255, 255, 255))
    for i, px in enumerate((120, 60, 40)):
        t = ic.resize((px, px), Image.LANCZOS)
        mm = Image.new("L", (px, px), 0)
        ImageDraw.Draw(mm).rounded_rectangle((0, 0, px - 1, px - 1), radius=int(px * 0.225), fill=255)
        small.paste(t, (50, [20, 170, 260][i]), mm)
    def popup_crop(im):
        k = im.width / 393.0
        top = im.crop((0, int(40 * k), im.width, int(118 * k)))
        mid = im.crop((0, int(180 * k), im.width, int(640 * k)))
        return scaled(vstack([top, mid], 6, bg=(40, 40, 40)), 0.30)
    r2 = hstack([cap(hstack([icr, small], 10), "3  ICON IC-1 “Out the Door” (512 draft; 120/60/40)"),
                 cap(hstack([popup_crop(pause_old), popup_crop(pause_new)], 16), "4  PALETTE — HUD + Paused: today | D1 mock"),
                 cap(vstack([on_bg(scaled(logo_old, 0.40), bg), on_bg(scaled(logo, 0.40), bg)], 12),
                     "5  LOGO — today (top) | LG-1 sketch (same 12 layers)")], 40, valign="top")
    hdr = title_block("Arrow Out — D1 “Burrow Works” concept pack (R1 drafts)",
                      "Direction D1 is already decided (ruling 38) and proceeds; this sheet is for your eye. Everything shown "
                      "is our own model/drawing; the original is not on this sheet. Drafts: shading, poses and the icon "
                      "composition are iterated in R2/R5/R6.", max(r1.width, r2.width), 46)
    sheet = vstack([hdr, r1, r2], 30)
    if sheet.width > W:
        sheet = scaled(sheet, W / sheet.width)
    sheet.save(os.path.join(OUT, "OWNER-SHEET.png"))
    print("owner sheet", sheet.size)


# ================================================================== composed home mock (palette + new cast on today's home)

def _fill_masked(im, mask, iters=250):
    """Clean plate inside `mask` (bool HxW) on a bounded crop: heavy blur of the known pixels, then neighbour relaxation."""
    from scipy import ndimage
    a = np.asarray(im.convert("RGB")).astype(np.float32)
    ys, xs = np.where(mask)
    if not len(ys):
        return im.convert("RGB")
    y0, y1, x0, x1 = max(0, ys.min() - 40), min(a.shape[0], ys.max() + 41), max(0, xs.min() - 40), min(a.shape[1], xs.max() + 41)
    sub, m = a[y0:y1, x0:x1].copy(), mask[y0:y1, x0:x1]
    w = (~m).astype(np.float32)
    num = ndimage.gaussian_filter(sub * w[..., None], (30, 30, 0))
    den = ndimage.gaussian_filter(w, 30)[..., None]
    sub[m] = (num / np.maximum(den, 1e-4))[m]
    k = np.array([[0, 1, 0], [1, 0, 1], [0, 1, 0]], np.float32) / 4
    for _ in range(iters):
        nb = np.stack([ndimage.convolve(sub[..., c], k, mode="nearest") for c in range(3)], -1)
        sub[m] = nb[m]
    a[y0:y1, x0:x1] = sub
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))


def cmd_homemock():
    base = Image.open(P("build/compare/captures/home-L32-en.png")).convert("RGB")
    s = base.width / 393.0
    rigs = {r: json.load(open(P("art/out", r, "rig.json"))) for r in ("char_sci_home_rig", "char_wk_homeL_blue_rig", "char_wk_homeR_blue_rig")}
    olds = {"char_sci_home_rig": "art/out/char_sci_home@3x.png", "char_wk_homeL_blue_rig": "art/out/char_wk_homeL_blue@3x.png",
            "char_wk_homeR_blue_rig": "art/out/char_wk_homeR_blue@3x.png"}
    from scipy import ndimage
    mask = np.zeros((base.height, base.width), bool)
    for r, f in olds.items():
        pl = rigs[r]["placement_pt"]
        im = Image.open(P(f)).convert("RGBA")
        im = scaled(im, s / 3)
        a = np.asarray(im)[..., 3] > 25
        x0, y0 = round(pl["x"] * s), round(pl["y"] * s)
        h, w = a.shape
        mask[y0:y0 + h, x0:x0 + w] |= a[:max(0, min(h, base.height - y0)), :max(0, min(w, base.width - x0))]
    mask = ndimage.binary_dilation(mask, iterations=4)
    plate = _fill_masked(base, mask)
    mock = recolor(plate, {}).convert("RGBA")
    boss = scaled(Image.open(os.path.join(R3D, "concept_bossV2_home.png")).convert("RGBA"), s / 3)
    pl = rigs["char_sci_home_rig"]["placement_pt"]
    mock.alpha_composite(boss, (round(pl["x"] * s), round(pl["y"] * s)))
    dg = scaled(Image.open(os.path.join(R3D, "concept_digger_hero.png")).convert("RGBA"), s / 3)
    for r, flip in (("char_wk_homeL_blue_rig", False), ("char_wk_homeR_blue_rig", True)):
        pl = rigs[r]["placement_pt"]
        im = dg.transpose(Image.FLIP_LEFT_RIGHT) if flip else dg
        feet_x_pt = 72.7 if not flip else 150 - 72.7
        # the Digger's feet: frame x 72.7 pt, y 131.6 pt; the workers' feet anchor: frame (67.7, 122.5) pt
        fx = pl["x"] + (67.7 if not flip else 150 - 67.7) - feet_x_pt
        fy = pl["y"] + 122.5 - 131.6
        mock.alpha_composite(im, (round(fx * s), round(fy * s)))
    mock = mock.convert("RGB")
    mock.save(os.path.join(OUT, "home-mock-D1-cast.png"))
    m0 = CG.measure(P("build/compare/captures/home-L32-en.png"), P("research/shots/002-home-L32.png"))
    m1 = CG.measure(os.path.join(OUT, "home-mock-D1-cast.png"), P("research/shots/002-home-L32.png"))
    W = 393 * 2
    row = hstack([label(scaled(base, W / base.width), "home today", 30), label(scaled(mock, W / mock.width), "palette + new cast (backdrop NOT redesigned)", 30),
                  label(scaled(Image.open(P("research/shots/002-home-L32.png")).convert("RGB"), W / 1178), "the original (002)", 30)], 30)
    note = (f"copygate screen vs 002 — today: SSIM {m0['ssim']:.3f} / overlap {m0['overlap']:.3f}; palette + cast only: SSIM "
            f"{m1['ssim']:.3f} / overlap {m1['overlap']:.3f} (screen gate SSIM < 0.30, overlap < 0.55). The composition (lab walls, "
            "console, capsule machine, dais) is still today's: R3's new burrow backdrop + Signpost centrepiece is what has to "
            "move SSIM. Mock only: old characters removed by a clean-plate fill, the Digger mirrored for the right slot.")
    vstack([title_block("Composed home mock — how far palette + cast alone go", note, row.width), row], 16).save(
        os.path.join(OUT, "home-mock-D1.png"))
    json.dump(dict(today=m0, mock=m1), open(os.path.join(OUT, "home-mock-D1.json"), "w"), indent=1, default=float)
    print(note)


# ================================================================== copygate.json (R1 recalibration)

KINDS_R1 = {
    "screen": dict(ssim_max=0.30, overlap_max=0.55, chrome_de00_min=None, chroma_min=0.0),
    "popup": dict(ssim_max=None, overlap_max=0.55, chrome_de00_min=25, chroma_min=8.0),
    "page": dict(ssim_max=None, overlap_max=0.55, chrome_de00_min=25, chroma_min=8.0),
    "hud": dict(ssim_max=None, overlap_max=0.55, chrome_de00_min=None, chroma_min=8.0),
    "icon": dict(ssim_max=0.25, overlap_max=0.40, chrome_de00_min=None, chroma_min=0.0),
    "logo": dict(ssim_max=0.30, overlap_max=0.55, chrome_de00_min=None, chroma_min=0.0),
    "character": dict(ssim_max=None, overlap_max=None, chrome_de00_min=None, chroma_min=0.0),
    "board": dict(ssim_max=None, overlap_max=None, chrome_de00_min=None, chroma_min=0.0),
}


def _stats(rows, kind, role, key):
    v = [r[key] for r in rows if r["kind"] == kind and r["role"] == role and not r["id"].endswith("[no chroma_min]")]
    return [round(min(v), 3), round(float(np.median(v)), 3), round(max(v), 3), len(v)] if v else None


def cmd_writecfg():
    cal = json.load(open(os.path.join(OUT, "copygate-calibration.json")))["rows"]
    old = json.load(open(CG.CONFIG))
    judged = []
    cfg = dict(old)
    cfg["kinds"] = KINDS_R1
    for r in cal:
        if r["id"].endswith("[no chroma_min]"):
            continue
        j = CG.judge(r, r["kind"], cfg)
        exp = {"copy": False, "concept": True, "control": True}[r["role"]]
        if r["id"].startswith("D1-home-mock"):
            exp = False        # today's composition: SSIM must still fail until R3 replaces the backdrop/layout
        judged.append(dict(id=r["id"], kind=r["kind"], role=r["role"], ssim=round(r["ssim"], 3), overlap=round(r["overlap"], 3),
                           chrome_de00=(round(r["chrome"]["median"], 1) if r.get("chrome") else None), gate_pass=j["pass"],
                           expected_pass=exp, agrees=(j["pass"] == exp),
                           counted=not (r["kind"] == "character" or (r["kind"] == "icon" and r["role"] == "control")),
                           note=("informative kind (no thresholds): see sources.character" if r["kind"] == "character" else
                                 "unrelated-icon control: documents the icon metric's false-fail rate (sources.icon)"
                                 if (r["kind"] == "icon" and r["role"] == "control") else r.get("note", ""))))
    st = {k: {role: dict(ssim=_stats(cal, k, role, "ssim"), overlap=_stats(cal, k, role, "overlap"))
              for role in ("copy", "concept", "control")} for k in ("screen", "popup", "hud", "icon", "logo", "character")}
    cfg.update({
        "about": old["about"] + " kinds[*].chroma_min: pixels with CIELAB chroma below it are left out of both chroma "
                                "histograms (tools/copygate.py measure(cmin=...)).",
        "status": "R1 2026-09-28 (PLAN-P R1 CONCEPTS): recalibrated on the D1 concept renders + mocks; numbers, pairs and "
                  "the reasoning per kind in art/review/concepts/copygate-calibration.json (+ .png sheets beside it)",
        "sources": {
            "screen": "UNCHANGED default SSIM < 0.30 and overlap < 0.55. §2.1 copies fail (SSIM 0.47-0.93), unrelated controls pass "
                      "(0.12-0.18 / 0.13-0.51). R1 home mock (today's composition + D1 palette + new cast): overlap 0.84 -> ~0.19 "
                      "but SSIM ~0.54 = still FAILS: SSIM follows the composition, so the home/Loading pass only with R3/R4's new "
                      "backdrop + layout (as intended).",
            "popup": "chroma_min 8 ADDED: ~51 % of the Paused frame is the neutral dim over the board, identical in both games, which "
                     "alone kept the overlap near 0.5-0.65 whatever the chrome colours (D1 palette mock 0.654 without it). With it: "
                     "today 0.759 (copy, fails) vs D1 mock ~0.36 (passes). Chrome ΔE00 > 25 kept (today 2.1 / mock 25.8: THIN margin "
                     "because 2 of the 6 pause ui regions are the red X + cream card, unchanged by design; A5 should land >= 30). "
                     "SSIM informative only (centred panel = genre constant; mock 0.915 vs today 0.928).",
            "page": "same rule as popup (not re-measured on a page render in R1; the codemod moves the same families)",
            "hud": "NEW kind for the HUD band (pairs pass crop 0,40,393,85 pt): positions are 1:1 by ruling 37(b) so SSIM stays "
                   "~0.91 (informative); overlap with chroma_min 8: today ~0.89 (copy) vs D1 mock ~0.10.",
            "icon": "thresholds unchanged (SSIM < 0.25, overlap < 0.40) but LOW DISCRIMINATION: 12 unrelated factory icons score "
                    "SSIM 0.05-0.43 / overlap 0.06-0.61 and 7 of 12 would FAIL; today's copied icon (0.319 / 0.254) sits inside "
                    "that range and is caught only by SSIM. A PASS is necessary, not sufficient: the icon rules (art-direction §5: "
                    "no white ground, no three-arrow row, no parallel off-edge arrows), G4b and the owner decide. IC-1 draft passes "
                    "both (SSIM ~0.21, overlap ~0.07).",
            "logo": "unchanged default; the copy is caught by overlap (today 0.665 vs store 8), the LG-1 sketch passes (~0.11 / ~0.19). "
                    "SSIM is low even for the copy (a different word), so the logo gate rests on overlap + G4b; art §2.1's "
                    "silhouette-IoU rule is not implemented.",
            "character": "INFORMATIVE ONLY (was undefined): on isolated character crops (ours alpha on grey vs a border-colour matte of "
                         "theirs on grey) the metric does not discriminate - our OWN unrelated characters score SSIM 0.42-0.48 / "
                         "overlap 0.58-0.66, higher than the known 1:1 copies (0.32-0.34 / 0.44-0.55), and the new Digger (0.333) "
                         "would fail an SSIM < 0.30 rule. Characters are judged IN CONTEXT (screen kind on the composed home / "
                         "Loading / event pages), by the A-bar grades and by G4b's blind adversarial review.",
            "board": old["sources"].get("board", ""),
        },
        "calibration": dict(date="2026-09-28", by="R1 CONCEPTS", stats_min_median_max_n=st, pairs=judged),
    })
    if "hud*" in cfg.get("sweep_kinds", {}):
        cfg["sweep_kinds_note"] = ("sweep captures are full frames: hud*/L5/fx-*/ftue* stay 'board'; G4a pairs for the HUD use kind "
                                   "'hud' with crop [0, 40, 393, 85]")
    with open(CG.CONFIG, "w") as f:
        json.dump(cfg, f, indent=1, ensure_ascii=False)
    bad = [j for j in judged if not j["agrees"] and j["counted"]]
    doc = [j for j in judged if not j["agrees"] and not j["counted"]]
    print(f"copygate.json written: {len(judged)} calibration pairs; counted disagreements {len(bad)}: {[b['id'] for b in bad]}; "
          f"documented (uncounted) disagreements {len(doc)}: {[b['id'] for b in doc]}")


def main(argv):
    cmd = argv[0] if argv else ""
    fn = {"palette": cmd_palette, "logo": cmd_logo, "boss": cmd_boss, "crew": cmd_crew, "icon": cmd_icon,
          "calib": cmd_calib, "owner": cmd_owner, "homemock": cmd_homemock, "writecfg": cmd_writecfg}.get(cmd)
    if fn is None:
        print(__doc__)
        return 2
    fn()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
