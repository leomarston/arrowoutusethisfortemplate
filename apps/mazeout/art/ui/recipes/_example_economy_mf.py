"""Economy and HUD props: coin (A-02), glossy hearts (A-03, A-04, A-08), stars (A-05), steel key (A-06), padlock (A-07).

SPEC-ui marks the hearts and stars "SVG"; we model them in 3D with the same toy rig instead (DECISION: the glossy
dome and the bevels then match the booster renders; the look to match is the crop). References (looked at only):
design/ui-crops/icon-coin.png, icon-heart-lives.png, icon-heart-star-lose.png, home-topbar-keychallenge.png,
icon-broken-heart.png, icon-star-gold.png, icon-star-grey.png, icon-key.png, icon-padlock-bar.png.
"""
import math

import numpy as np

from uikit import (FONT_ROUND, round_cone, F, SDF, SDF2, Part, box, capsule, circle2, cylinder, emboss, extrude, glyph2, gloss,
                   heart2, metal, pillow, polygon2, rect2, rounded_polygon2, satin, sphere, star2, torus, union)

VOXEL = 0.004

HEART_RED = "#CC0508"       # capture lit (203,3,3), shade (154,9,13)
COIN_GOLD = "#FFC400"       # capture face (252,214,0), edge (246,174,0)
STAR_GOLD = "#FDBB0E"       # SPEC-ui A-05 face #FCC617
STAR_RIM = "#DCE5EF"
STAR_EMPTY = "#AEBACA"      # SPEC-ui #ADB9C7
KEY_BLUE = "#2F86B8"
KEY_STEEL = "#AFB9D0"
LOCK_BODY = "#8FA2C0"
LOCK_SHACKLE = "#7488A8"
LOCK_HOLE = "#2A3B57"


def heart2d():
    """The heart outline: the classic parametric heart, tip softened, from a raster (blurred inside, no crease)."""
    from uikit import heart_curve, poly_mask, raster_sdf2
    pts = heart_curve(w=1.0)
    ext = (-0.62, -0.58, 0.62, 0.58)
    pts[:, 1] = np.where(pts[:, 1] < 0, pts[:, 1] * 0.93, pts[:, 1])
    return raster_sdf2(poly_mask(pts, ext, px=720, soften_px=18), ext, blur_px=26)


def heart_body(depth=0.72):
    """A balloon heart: the outline inflated with a quarter-ellipse rim as wide as the heart is thick."""
    return pillow(heart2d(), R=0.30, H=0.30 * depth)


def heart_mat():
    return gloss("heart_red", HEART_RED, rough=0.2, ior=1.5)


def heart():
    return [Part("heart", heart_body(), heart_mat())], VOXEL


def heart_infinite():
    body = heart_body()
    inf = _lemniscate(0.19, 0.056).translate(0, 0.05)
    mark = body.offset(0.028).intersect(extrude(inf, 0.5).translate(0, 0, 0.5), k=0.006)
    return [Part("heart", body, heart_mat()), Part("inf", mark, gloss("heart_inf", "#FFFFFF", rough=0.35), voxel=0.003)], VOXEL


def _lemniscate(a, t, n=64):
    """The infinity sign: a lemniscate of Bernoulli (half-width a) drawn with a stroke of width t."""
    from uikit import capsule2
    pts = []
    for k in range(n):
        th = 2 * math.pi * k / n
        d = 1 + math.sin(th) ** 2
        pts.append((a * math.cos(th) / d * 1.0, a * math.sin(th) * math.cos(th) / d * 1.25))
    s = None
    for i in range(n):
        seg = capsule2(pts[i], pts[(i + 1) % n], t / 2)
        s = seg if s is None else s.union(seg)
    return s


def heart_broken():
    body = heart_body()
    # a jagged crack from the top notch to the tip
    zig = [(0.0, 0.40), (0.0, 0.16), (-0.08, 0.05), (0.06, -0.08), (-0.05, -0.20), (0.03, -0.32), (0.0, -0.6)]
    gap = 0.018
    left = polygon2([(-1.0, 0.6)] + zig + [(-1.0, -0.6)]).offset(-gap)
    right = polygon2([(1.0, 0.6)] + zig + [(1.0, -0.6)]).offset(-gap)
    L = body.intersect(extrude(left, 0.5), k=0.01)
    R = body.intersect(extrude(right, 0.5), k=0.01)
    L = L.rotate_z(5).translate(-0.03, -0.015, 0.0)
    R = R.rotate_z(-2).translate(0.02, 0.005, 0.0)
    m = heart_mat()
    return [Part("left", L, m), Part("right", R, m)], VOXEL


# ------------------------------------------------------------------ stars

def star_outline(r=0.5, inner=0.52):
    return star2(5, r, r * inner, round=0.075, round_valley=0.07)


def star_socket(empty=True):
    rim_s = star_outline(0.5).offset(0.075)
    rim = pillow(rim_s, R=0.09, H=0.085)
    recess = extrude(star_outline(0.5).offset(0.012), 0.2).translate(0, 0, 0.2 + 0.03)
    rim = rim.subtract(recess, k=0.02)
    parts = [Part("rim", rim, gloss("star_rim", STAR_RIM, rough=0.3))]
    if empty:
        face = pillow(star_outline(0.5).offset(0.012), R=0.03, H=0.035).translate(0, 0, 0.0)
        parts.append(Part("face", face, satin("star_empty", STAR_EMPTY, rough=0.5)))
    return parts


def star_gold_parts():
    s = star_outline(0.5)
    body = pillow(s, R=0.13, H=0.11).translate(0, 0, 0.055)
    return [Part("star", body, gloss("star_gold", STAR_GOLD, rough=0.26, ior=1.42))]


def star_gold():
    return star_socket(empty=False) + star_gold_parts(), VOXEL


def star_grey():
    return star_socket(empty=True), VOXEL


def star_plain():
    return star_gold_parts(), VOXEL


# ------------------------------------------------------------------ coin

def coin():
    R, T = 0.5, 0.085
    reeds = 72

    def ridged(p):
        ang = np.arctan2(p[:, 2], p[:, 0])
        return np.cos(ang * reeds).astype(F)
    edge = cylinder(R, T, round=0.05).rotate_x(90)
    body = SDF(lambda p, f=edge.fn: f(p) - F(0.006) * np.clip(ridged(p[:, [0, 2, 1]]), -1, 1) * (np.abs(p[:, 2]) < T * 0.7), edge.lo - 0.01, edge.hi + 0.01)
    # recessed field inside a raised lip, on the front face
    field = cylinder(R * 0.78, 0.2).rotate_x(90).translate(0, 0, T + 0.2 - 0.022)
    body = body.subtract(field, k=0.02)
    dollar = glyph2("$", 0.64).offset(0.02)
    mark = extrude(dollar, 0.03, round=0.022).translate(0, 0, T - 0.01)
    m = gloss("coin_gold", COIN_GOLD, rough=0.28, ior=1.42)
    return [Part("coin", body, m), Part("dollar", mark, gloss("coin_mark", "#F8AE00", rough=0.26, ior=1.42), voxel=0.003)], VOXEL


# ------------------------------------------------------------------ key and padlock

def key():
    bow2 = rect2(0.25, 0.25, round=0.09)
    bow = extrude(bow2, 0.075, round=0.05).translate(0, 0.44, 0)
    bow = bow.subtract(extrude(rect2(0.17, 0.17, round=0.06), 0.2).translate(0, 0.44, 0.2 + 0.045), k=0.02)
    hole = cylinder(0.045, 0.3).rotate_x(90).translate(0.02, 0.50, 0)
    bow = bow.subtract(hole, k=0.012)
    collar = box(0.12, 0.04, 0.06, round=0.03).translate(0, 0.17, 0)
    shaft2 = rect2(0.09, 0.24, round=0.045).translate(0, -0.05)
    teeth = [rect2(0.05, 0.026, round=0.014).translate(0.11, -0.22 + 0.08 * k) for k in range(3)]
    s = shaft2
    for t in teeth:
        s = s.union(t)
    notch = rect2(0.022, 0.17).translate(-0.03, -0.12)
    shaft = extrude(s, 0.045, round=0.03).subtract(extrude(notch, 0.2).translate(0, 0, 0.2 + 0.02), k=0.01)
    return [Part("bow", bow, gloss("key_bow", KEY_BLUE, rough=0.32)),
            Part("collar", collar, metal("key_collar", KEY_STEEL)),
            Part("shaft", shaft, metal("key_steel", KEY_STEEL))], VOXEL


def padlock():
    body = box(0.31, 0.25, 0.13, round=0.1).translate(0, -0.12, 0)
    shackle = torus(0.19, 0.055).rotate_x(90).intersect(box(0.4, 0.3, 0.2).translate(0, 0.3, 0)).translate(0, 0.12, -0.02)
    legs = union(capsule((-0.19, 0.12, -0.02), (-0.19, 0.0, -0.02), 0.055), capsule((0.19, 0.12, -0.02), (0.19, 0.0, -0.02), 0.055))
    hole2 = circle2(0.065).translate(0, -0.07).union(rect2(0.03, 0.08, round=0.02).translate(0, -0.15))
    hole = body.offset(0.004).intersect(extrude(hole2, 0.3).translate(0, 0, 0.3), k=0.004)
    return [Part("body", body.subtract(extrude(hole2.offset(-0.012), 0.2).translate(0, 0, 0.2 + 0.1), k=0.006),
                 gloss("lock_body", LOCK_BODY, rough=0.34)),
            Part("hole", hole, satin("lock_hole", LOCK_HOLE)),
            Part("shackle", union(shackle, legs), metal("lock_shackle", LOCK_SHACKLE))], VOXEL


MODELS = dict(heart=heart, heart_infinite=heart_infinite, heart_broken=heart_broken, star_gold=star_gold,
              star_grey=star_grey, coin=coin, key=key, padlock=padlock)

ASSETS = {
    "coin": dict(model="coin", yaw=-14, pitch=-8, frame=(48, 48), fill=0.96),
    "heart": dict(model="heart", yaw=10, pitch=-4, roll=-8, frame=(48, 42), fill=0.96),
    "heartBig": dict(model="heart", yaw=8, pitch=-4, frame=(95, 85), fill=0.96),
    "heartInfinite": dict(model="heart_infinite", yaw=8, pitch=-4, frame=(48, 42), fill=0.96),
    "heartBroken": dict(model="heart_broken", yaw=8, pitch=-4, frame=(120, 105), fill=0.96),
    "starGold": dict(model="star_gold", yaw=0, pitch=-6, frame=(79, 77), fill=0.97),
    "starGrey": dict(model="star_grey", yaw=0, pitch=-6, frame=(79, 77), fill=0.97),
    "keyIcon": dict(model="key", yaw=12, pitch=-6, roll=30, frame=(35, 45), fill=0.86, outline=("#BFD0E6", 7)),
    "padlock": dict(model="padlock", yaw=8, pitch=-4, frame=(33, 40), fill=0.96),
}
