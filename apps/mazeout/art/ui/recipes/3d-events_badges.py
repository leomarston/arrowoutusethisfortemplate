"""3d-events lane: the home event badges (eventBadgeStreak / eventBadgeSkyJump / eventBadgeRocket) and the Rocket Race
rockets (rocketMine = the player, red-yellow; rocketOther = the simulated opponents, blue-white).

References (LOOKED AT only; nothing traced or sampled): home badges on research/shots/026 (Streak Race), 070 (Sky Jump,
joined), 168 (Rocket Race); race lanes on 178 / 167. All three badges share one base (measured on 168 / 026 / 070, pt):
  hex plaque   flat-top hexagon 67 wide x 58 tall, gold rim ~5.5 pt, inner panel per event (blue / navy space with
               stars / purple), standing behind the drum
  drum         53 wide x ~15 tall, per-event colour (blue #1966EE / purple #5B2FD9 / #6A43E3); the live timer
               ("9h 7m") is drawn by the app on its front -- never baked
  gold ring    59 wide, ~6 thick, under the drum
  seen ~11 deg from above.
Icons: two crossed chequered flags (navy #2E5896 / cream #F2EEE6) on light-blue poles with a cream wrap where they
cross; a red-nosed yellow rocket with a blue porthole (live count on the glass); the Sky Jump pad (pink cushion,
cream layers, gold band with a pink plate for the live count) on lilac clouds.
Race rockets (178): 64 pt across the fins, 74 pt nose to nozzle, a 20 pt flame; porthole ring 30 pt at 45 % down.

Units: 1 world unit = 40 pt (P(x) converts pt).
"""
from __future__ import annotations

import math

import numpy as np

from uikit import (F, SDF, Part, box, capsule, capped_cone, circle2, cylinder, ellipsoid, extrude, gloss, polygon2,
                   rect2, revolve, satin, sphere, spline_profile, textured, torus, union)

VOXEL = 0.0065
PT = 1.0 / 40.0


def P(x):
    return x * PT


# ------------------------------------------------------------------ the rocket (pt, nozzle bottom at y = -3, nose y = 44)

ROCKET_SCHEMES = {
    # body, body shade hint (unused by PBR), nose/band/fins, nozzle, porthole ring, glass
    "mine": dict(body="#FFB70A", red="#E5261C", nozzle="#1E57C8", ring="#1D4DB8", glass="#27B9FF"),
    "other": dict(body="#C9D5E6", red="#237FEC", nozzle="#1C4FB6", ring="#1D4DB8", glass="#27B9FF"),
}

NOSE_Y = 35.0      # nose cap from here up
BAND_Y = 12.5      # lower band from here down
PORT_Y = 22.5      # porthole centre


def rocket_body_sdf():
    prof = spline_profile([(0, 1.5), (12.2, 1.5), (15.2, 8.0), (15.8, 14.0), (15.0, 24.0), (12.8, 32.0), (9.2, 38.5),
                           (4.6, 42.6), (0.0, 43.8)], samples=120)
    return revolve(prof).scale(PT)


def rocket_parts(scheme="mine"):
    c = ROCKET_SCHEMES[scheme]
    body = rocket_body_sdf()
    big = P(200)
    nose = body.offset(P(0.35)).intersect(box(big, big, big).translate(0, P(NOSE_Y) + big, 0), k=P(0.4))
    band = body.offset(P(0.45)).intersect(box(big, big, big).translate(0, P(BAND_Y) - big, 0), k=P(0.4))
    mid = body
    # fins: a swept blade each side, in the image plane, rounded
    fin2 = polygon2([(P(12.0), P(21.5)), (P(18.0), P(17.0)), (P(22.6), P(9.5)), (P(24.4), P(1.0)), (P(23.6), P(-3.2)),
                     (P(19.0), P(-2.2)), (P(12.5), P(2.0))]).offset(P(1.1))
    finR = extrude(fin2, P(2.2), round=P(1.9))
    fins = union(finR, finR.transform(np.diag([-1.0, 1.0, 1.0])))
    nozzle = capped_cone(P(3.8), P(9.6), P(10.8), round=P(1.4)).translate(0, P(-2.0), 0)
    # the porthole: a dark-blue ring standing proud of the body, a glass dome inside
    zf = P(14.9)
    ring = torus(P(8.2), P(2.5)).rotate_x(90).scale_xyz(1, 1, 0.8).translate(0, P(PORT_Y), zf + P(0.4))
    glass = ellipsoid(P(6.6), P(6.6), P(2.8)).translate(0, P(PORT_Y), zf + P(0.4))
    return [
        Part("body", mid, gloss(f"rk_body_{scheme}", c["body"], rough=0.30, ior=1.40)),
        Part("nose", nose, gloss(f"rk_red_{scheme}", c["red"], rough=0.28, ior=1.40)),
        Part("band", band, gloss(f"rk_red_{scheme}", c["red"], rough=0.28, ior=1.40)),
        Part("fins", fins, gloss(f"rk_red_{scheme}", c["red"], rough=0.28, ior=1.40)),
        Part("nozzle", nozzle, gloss(f"rk_nozzle_{scheme}", c["nozzle"], rough=0.32, ior=1.38)),
        Part("ring", ring, gloss(f"rk_ring_{scheme}", c["ring"], rough=0.26, ior=1.42), voxel=0.0045),
        Part("glass", glass, gloss(f"rk_glass_{scheme}", c["glass"], rough=0.12, ior=1.50), voxel=0.0045),
    ]


def rocket_model(scheme):
    return lambda: (rocket_parts(scheme), VOXEL)


def flame(im, frac_top=0.755):
    """Our painted exhaust under the nozzle (soft puffs: a white-yellow core, orange puffs, a red-orange rim), drawn
    below the lowest opaque point of the body column."""
    from PIL import Image as _I, ImageDraw as _D, ImageFilter as _Fl
    a = np.asarray(im.getchannel("A"))
    H, W = a.shape
    cols = np.nonzero(a.max(0) > 40)[0]
    cx = (cols.min() + cols.max()) / 2
    band = a[:, int(cx - W * 0.05):int(cx + W * 0.05)]
    rows = np.nonzero(band.max(1) > 40)[0]
    y0 = rows.max() - 2
    s = W / 68.0 * 1.0          # px per pt at this frame
    lay = _I.new("RGBA", (W, H), (0, 0, 0, 0))
    d = _D.Draw(lay)
    rng = np.random.default_rng(7)
    puffs = [(0, 5.0, 7.6, (255, 92, 38, 240)), (-3.8, 9.5, 5.8, (250, 104, 44, 235)), (3.6, 10.5, 5.6, (255, 98, 40, 235)),
             (-1.2, 14.5, 5.2, (248, 116, 52, 220)), (2.0, 17.5, 4.0, (240, 124, 62, 190))]
    for dx, dy, r, col in puffs:
        d.ellipse([cx + (dx - r) * s, y0 + (dy - r) * s, cx + (dx + r) * s, y0 + (dy + r) * s], fill=col)
    lay = lay.filter(_Fl.GaussianBlur(0.9 * s))
    core = _I.new("RGBA", (W, H), (0, 0, 0, 0))
    d2 = _D.Draw(core)
    for dx, dy, r, col in [(0, 3.8, 6.6, (255, 214, 100, 255)), (0, 5.8, 5.2, (255, 252, 226, 255)), (0.5, 10.0, 4.0, (255, 238, 170, 255)),
                           (-2.4, 8.5, 3.0, (255, 246, 200, 245))]:
        d2.ellipse([cx + (dx - r) * s, y0 + (dy - r) * s, cx + (dx + r) * s, y0 + (dy + r) * s], fill=col)
    core = core.filter(_Fl.GaussianBlur(0.6 * s))
    lay.alpha_composite(core)
    del rng
    lay.alpha_composite(im)
    return lay


# ------------------------------------------------------------------ the badge base (pt; ring bottom at y = 0)

BADGE = {
    "streak": dict(drum="#1966EE", panel="#1D5FE0", panel2="#2C74F2", stars=False),
    "rocket": dict(drum="#5B2FD9", panel="#1B1C80", panel2="#2A24A8", stars=True),
    "sky": dict(drum="#6A43E3", panel="#4A2EA8", panel2="#5B3CC4", stars=False),
}
GOLD = "#FFB20E"
HEX_W2 = 33.5      # hexagon half width (vertex to vertex 67 pt)
HEX_H2 = 29.0      # half height (flat top / bottom)
HEX_CY = 48.5      # hexagon centre height
HEX_Z = -13.0      # behind the drum centre
RIM = 5.6


def hex2(w2, h2, r):
    pts = [(-w2, 0), (-w2 / 2, h2), (w2 / 2, h2), (w2, 0), (w2 / 2, -h2), (-w2 / 2, -h2)]
    k = r / math.sin(math.radians(60))    # shrink so the rounded outline keeps the vertex-to-vertex size
    pts2 = [(x * (1 - k / w2), y * (1 - k / w2)) for x, y in pts]
    return polygon2([(P(x), P(y)) for x, y in pts2]).offset(P(r))


def panel_texture(base, top, stars):
    b = np.array([int(base[i:i + 2], 16) for i in (1, 3, 5)]) / 255
    t = np.array([int(top[i:i + 2], 16) for i in (1, 3, 5)]) / 255
    rng = np.random.default_rng(3)
    sx, sy, sr = rng.uniform(0, 1, 26), rng.uniform(0, 1, 26), rng.uniform(0.004, 0.010, 26)

    def fn(u, v):
        col = b[None, None] * (1 - v[..., None]) + t[None, None] * v[..., None]
        if stars:
            for x, y, r in zip(sx, sy, sr):
                d = np.hypot(u - x, v - y)
                a = np.clip(1 - d / r, 0, 1)[..., None] ** 1.5
                col = col * (1 - a * 0.8) + np.array([0.75, 0.80, 1.0])[None, None] * a * 0.8
        return col
    return fn


def base_parts(kind):
    c = BADGE[kind]
    ring = cylinder(P(29.5), P(3.3), round=P(3.0)).translate(0, P(3.3), 0)
    drum = cylinder(P(26.4), P(7.6), round=P(2.6)).translate(0, P(5.2 + 7.6), 0)
    outer = hex2(HEX_W2, HEX_H2, 5.0)
    inner = hex2(HEX_W2 - RIM, HEX_H2 - RIM, 3.2)
    rim = extrude(outer, P(2.6), round=P(2.2)).subtract(extrude(inner, P(4.0)), k=P(1.0))
    rim = rim.translate(0, P(HEX_CY), P(HEX_Z))
    panel = extrude(inner.offset(P(0.6)), P(1.0), round=P(0.6)).translate(0, P(HEX_CY), P(HEX_Z - 0.8))
    lo = P(HEX_CY - HEX_H2); span = P(2 * HEX_H2)
    panel_mat = textured(gloss(f"panel_{kind}", c["panel"], rough=0.45, ior=1.25),
                         panel_texture(c["panel"], c["panel2"], c["stars"]), size=256)
    panel_uv = ("planar", (P(-HEX_W2), lo, 0.0), (1.0 / (2 * P(HEX_W2)), 0, 0), (0, 1.0 / span, 0), 1.0)
    return [
        Part("ring", ring, gloss("badge_gold", GOLD, rough=0.26, ior=1.45)),
        Part("drum", drum, gloss(f"drum_{kind}", c["drum"], rough=0.30, ior=1.38)),
        Part("hexrim", rim, gloss("badge_gold", GOLD, rough=0.26, ior=1.45), voxel=0.0055),
        Part("panel", panel, panel_mat, uv=panel_uv),
    ]


# ------------------------------------------------------------------ Streak Race: crossed chequered flags

NAVY = (0x2E / 255, 0x58 / 255, 0x96 / 255)
CREAM = (0xF2 / 255, 0xEE / 255, 0xE6 / 255)


def checker(cols=3.4, rows=2.0):
    n, c = np.array(NAVY), np.array(CREAM)

    def fn(u, v):
        a = np.floor(u * cols) + np.floor(v * rows)
        m = (a % 2)[..., None]
        return n[None, None] * m + c[None, None] * (1 - m)
    return fn


def flag_part(name, top, bottom, side, length=27.0, height=27.0, wave=2.2, slope=-8.0):
    """A cloth flag attached to the pole segment near `top` (pt), flying to `side` (-1 left / +1 right)."""
    top = np.array(top, float); bottom = np.array(bottom, float)
    up = (top - bottom); up /= np.linalg.norm(up)
    # local frame: x = outward (perpendicular to the pole in the image plane, toward `side`), y = along the pole
    out = np.array([up[1], -up[0], 0.0]) * side
    if out[0] * side < 0:
        out = -out
    rot = math.radians(slope * side)
    out = out * math.cos(rot) + up * math.sin(rot)
    out /= np.linalg.norm(out)
    t = 1.8                                                      # cloth thickness (pt)
    L, Hh = length, height

    def local(p):
        # p (N,3) in pt; the flag's frame starts at `top` (the cloth's upper corner at the pole)
        q = p - top
        x = q @ out; y = q @ up; z = q[:, 2] - 1.5
        # the wave: z displacement growing away from the pole
        z = z - wave * np.sin(x / L * math.pi * 1.6) * np.clip(x / 6, 0, 1)
        r = 1.2
        qx = np.abs(x - L / 2) - (L / 2 - r)
        qy = np.abs(y + Hh / 2) - (Hh / 2 - r)
        d2 = np.hypot(np.maximum(qx, 0), np.maximum(qy, 0)) + np.minimum(np.maximum(qx, qy), 0) - r
        return np.maximum(d2, np.abs(z) - t / 2) * 0.75      # 0.75: the wave stretches the field

    lo = np.minimum(top, top + out * L - up * Hh) - 8
    hi = np.maximum(top, top + out * L - up * Hh) + 8
    lo = np.minimum(lo, top - up * Hh - 8); hi = np.maximum(hi, top + out * L + 8)

    def fn(p):
        q = p / PT
        return (local(q) * PT).astype(F)
    s = SDF(fn, np.r_[lo[:2], -8] * PT, np.r_[hi[:2], 8] * PT)
    s = s.offset(P(0.5))
    uv = ("planar", tuple((top * PT).tolist()), tuple((out / (L * PT)).tolist()), tuple((up / (Hh * PT)).tolist()), 1.0)
    return Part(name, s, textured(satin(f"flag_{name}", "#F2EEE6", rough=0.42, ior=1.25), _flag_tex(), size=256), uv=uv,
                voxel=0.0045)


def _flag_tex():
    base = checker(2.7, 2.0)

    def fn(u, v):
        # u in [0, 1] outward; v in [-1, 0] down the pole
        # (the texture is defined on [0, 1]^2; the cloth's uv v runs -1..0 and the sampler wraps it into 0..1)
        return base(np.clip(u, 0, 0.999), np.clip(v, 0, 0.999))
    return fn


def flags_parts():
    # poles (pt): screen measurements on 026 relative to the badge centre (x - 48.5) and ring bottom (272 - y)
    left_top, left_bot = (-11.0, 73.5, 1.0), (4.0, 24.5, 1.0)       # the pole whose flag flies LEFT
    right_top, right_bot = (11.5, 73.5, -1.0), (-6.5, 24.5, -1.0)   # the pole whose flag flies RIGHT
    pole_mat = gloss("pole", "#8CCBFF", rough=0.22, ior=1.45)
    poles = union(capsule(tuple(P(v) for v in left_top), tuple(P(v) for v in left_bot), P(3.5)),
                  capsule(tuple(P(v) for v in right_top), tuple(P(v) for v in right_bot), P(3.5)))
    caps = union(sphere(P(3.6), tuple(P(v) for v in left_top)), sphere(P(3.6), tuple(P(v) for v in right_top)))
    # the cream wrap where the poles cross
    cross = (-1.2, 40.0, 0.2)
    wrap = cylinder(P(5.4), P(2.4), round=P(1.4)).rotate_z(8).translate(*[P(v) for v in cross])
    fl = flag_part("flagL", (-10.3, 70.0, 3.2), left_bot, -1, length=35.0, height=35.0, wave=4.4, slope=14.0)
    fr = flag_part("flagR", (10.8, 70.0, 1.2), right_bot, +1, length=36.0, height=35.0, wave=4.4, slope=9.0)
    return [Part("poles", poles, pole_mat, voxel=0.0045), Part("caps", caps, pole_mat, voxel=0.0045),
            Part("wrap", wrap, satin("wrap", "#F2EEE6", rough=0.4)), fl, fr]


# ------------------------------------------------------------------ Sky Jump: the pad on clouds

def pad_parts():
    y0 = 20.0                                       # the drum top
    clouds = []
    for (x, y, z, r) in [(-27, 27, 5, 7.0), (-18, 28, 11, 8.0), (-7, 27, 14, 8.5), (7, 27, 14, 8.5), (18, 28, 11, 8.0),
                         (27, 27, 5, 7.0), (-22, 31, -4, 7.5), (0, 31, 3, 9.5), (22, 31, -4, 7.5), (-11, 32, 5, 7.5),
                         (11, 32, 5, 7.5)]:
        clouds.append(sphere(P(r), (P(x), P(y), P(z))))
    cloud = union(*clouds, k=P(2.5))
    # the pad: stacked cream layers (a lower and an upper puffy ring), a gold band between them, a pink cushion top
    cy = 45.0
    lower = cylinder(P(25.5), P(4.2), round=P(4.0)).translate(0, P(cy - 7.0), 0)
    band = cylinder(P(25.9), P(2.9), round=P(1.3)).translate(0, P(cy - 1.2), 0)
    upper = cylinder(P(24.6), P(3.9), round=P(3.7)).translate(0, P(cy + 3.8), 0)
    cushion = cylinder(P(22.6), P(3.0), round=P(2.9)).translate(0, P(cy + 8.4), 0)
    # the plate on the band's front (the live count sits on it): a rounded square, gold rim, pink face
    zf = P(25.6)
    plate_rim = extrude(rect2(P(9.6), P(11.0), round=P(3.4)), P(1.8), round=P(1.3)).translate(0, P(cy), zf + P(0.4))
    plate = extrude(rect2(P(7.2), P(8.6), round=P(2.5)), P(1.1), round=P(0.9)).translate(0, P(cy), zf + P(1.8))
    return [
        Part("clouds", cloud, satin("cloud", "#DCC6F2", rough=0.55, ior=1.15)),
        Part("lower", lower, gloss("pad_cream", "#F6EEF0", rough=0.36, ior=1.32)),
        Part("upper", upper, gloss("pad_cream", "#F6EEF0", rough=0.36, ior=1.32)),
        Part("band", band, gloss("badge_gold", GOLD, rough=0.26, ior=1.45)),
        Part("cushion", cushion, gloss("pad_pink", "#F04685", rough=0.30, ior=1.38)),
        Part("plateRim", plate_rim, gloss("badge_gold", GOLD, rough=0.26, ior=1.45), voxel=0.0045),
        Part("plate", plate, gloss("plate_pink", "#E62E6B", rough=0.30, ior=1.38), voxel=0.0045),
    ]


# ------------------------------------------------------------------ models

def badge_rocket():
    parts = base_parts("rocket")
    # the rocket stands on the drum: nozzle bottom at the drum top (y = 20 pt); badge rocket 52 pt nose to nozzle
    s = 57.0 / 47.0
    for p in rocket_parts("mine"):
        p.sdf = p.sdf.scale(s).translate(0, P(20.0 + 3.8 * s - 3.0), P(-2.0))
        p.name = "rk_" + p.name
        parts.append(p)
    return parts, VOXEL


def badge_streak():
    return base_parts("streak") + flags_parts(), VOXEL


def badge_sky():
    return base_parts("sky") + pad_parts(), VOXEL


MODELS = {
    "rocket_mine": rocket_model("mine"),
    "rocket_other": rocket_model("other"),
    "badge_rocket": badge_rocket,
    "badge_streak": badge_streak,
    "badge_sky": badge_sky,
}

BADGE_LIGHT = dict(fill_color=(1.0, 0.85, 0.6), fill_lux=560.0, key_lux=3100.0, ibl_exp=-0.7)
BADGE_FRAME = (80, 84)


def _badge(model, w, h, base=2.0):
    W, H = BADGE_FRAME
    return dict(model=model, yaw=0, pitch=11, frame=BADGE_FRAME, fill=(w / W, h / H),
                align=(0.5, (H - base - h) / (H - h)), fov=14, light=BADGE_LIGHT)


# race rockets: 64 x 74 pt body (fins, nose to nozzle) in a 68 x 98 frame, the flame painted below
def _rocket(model):
    return dict(model=model, yaw=0, pitch=4, frame=(68, 98), fill=(64 / 68, 74 / 98), align=(0.5, 2.0 / 24.0), fov=14,
                light=BADGE_LIGHT, post_fit=flame)


ASSETS = {
    "eventBadgeStreak": _badge("badge_streak", 76, 77),
    "eventBadgeSkyJump": _badge("badge_sky", 70, 80),
    "eventBadgeRocket": _badge("badge_rocket", 67, 79),
    "rocketMine": _rocket("rocket_mine"),
    "rocketOther": _rocket("rocket_other"),
}
