"""3d-hud lane: the rendered-look UI props (STYLE.md route B3) for the HUD, popups, bottom nav and rewards.

Every shape is an SDF written here from measurements taken by LOOKING at the references named in art/MANIFEST.json
(phone shots 003 / 013 / 016 / 020 / 023 / 025 / 026 / 033; nothing traced, nothing sampled into a texture). Colours are
hexes chosen here with the references' colours as targets (STYLE.md §D + the lane log art/lanes/3d-hud.md).

Cases (= manifest ids):
    boosterFreeze    frozen hourglass (the phone's LEFT booster), icon fills ~38 pt of the 56 pt frame (booster button size)
    boosterHint      glossy light bulb (RIGHT booster), same registration
    stopwatchBig     big blue stopwatch + blue glow (Out of Time!)
    heartBroken      broken glossy heart (Continue? / Level Failed!)
    coinStackReward  cluster of thick star coins + two twinkles (win popup "Rewards:")
    heartInfinite    red heart with a cream infinity sign (unlimited lives reward)
    navShop          orange basket with a star coin (bottom nav)
    navHome          yellow garage-house with an orange roof arch (bottom nav, raised tab)
    navTrophy        gold cup with an orange up-arrow (bottom nav)
    padlockGold      gold padlock (Claw ladder locked reward)
    coinPileSmall    small mound of coin stacks with a warm glow (Claw info overlay)
Authoring: +Y up, +Z toward the viewer, sizes ~1 unit. ui3d pose: pitch > 0 shows the TOP of a model, < 0 its bottom.
"""
import math

import numpy as np

from uikit import (F, SDF, SDF2, Part, box, capped_cone, capsule, circle2, cylinder, ellipsoid, extrude, gloss, glass,
                   heart_curve, path_tube, poly_mask, polygon2, raster_sdf2, rect2, revolve, round_cone, satin,
                   sphere, spline_profile, star2, torus, union, fillet_points)
from mesher import Material

VOXEL = 0.004

# ------------------------------------------------------------------ palette (targets from the references, see the lane log)
# A5 CODEMOD (2026-09-29): the blue / bulb / slate paints, BLUE_UI/BLUE_DEEP/SLATE/BULB and the Out of Time glow follow R9's
# chrome-blue -> D1 teal ladder (tools/palette_map.py, same L*); originals in build/p/A5/orig. Ice and every other paint unchanged.
GOLD = "#FFC21C"          # coin / trophy / padlock face
GOLD_SIDE = "#EC8C04"     # coin edges: the references' edges turn orange
GOLD_STAR = "#FFD440"
ORANGE = "#FF8A1E"        # nav basket / roof / trophy arrow family
ORANGE_LIGHT = "#FFA640"
RED_HEART = "#F42A1E"     # glossy hearts (face (242,38,26) lit, (184,4,0) shade)
RED_DEEP = "#8E0A0A"
CREAM = "#FFF0DE"
BLUE_UI = "#00968A"       # stopwatch bezel, hourglass caps, bulb base
BLUE_DEEP = "#007671"
SLATE = "#4B726D"         # stopwatch ticks + hand
ICE = "#86E4F4"           # hourglass glass
SNOW = "#F2FAFF"
BULB = "#D2E8E3"
YELLOW_HOUSE = "#FFCF26"


# ------------------------------------------------------------------ helpers

def lut(stops, n=256):
    """A 1-row texture: u in [0, 1] -> colour lerped between (u, hex) stops (v ignored)."""
    from palette import _rgb
    us = np.array([s[0] for s in stops], float)
    cs = np.array([_rgb(s[1]) for s in stops], float)

    def fn(u, v):
        out = np.stack([np.interp(u, us, cs[:, k]) for k in range(3)], -1)
        return out
    return fn


def painted(m: Material, stops, size=256):
    from dataclasses import replace
    return replace(m, texture=lut(stops), texture_size=size)


def stroke2(pts, width, closed=True):
    """A 2D stroke (round caps/joins) along a polyline, vectorised over the segments."""
    P = np.asarray(pts, F)
    A = P if closed else P[:-1]
    B = np.roll(P, -1, 0) if closed else P[1:]
    E = B - A
    EE = np.maximum((E * E).sum(1), 1e-12)
    r = F(width / 2)

    def fn(p):
        d = np.full(len(p), F(1e9), F)
        for a, e, ee in zip(A, E, EE):
            w = p - a
            h = np.clip((w @ e) / ee, 0, 1)
            q = w - h[:, None] * e
            d = np.minimum(d, (q * q).sum(1))
        return np.sqrt(d) - r
    return SDF2(fn, P.min(0) - width, P.max(0) + width)


def xform(sdf, R=np.eye(3), t=(0, 0, 0)):
    """World = R @ local + t (SDF.transform maps local -> world with R)."""
    return sdf.transform(np.asarray(R, float)).translate(*t)


def Rx(d):
    a = math.radians(d); c, s = math.cos(a), math.sin(a)
    return np.array([[1, 0, 0], [0, c, -s], [0, s, c]])


def Ry(d):
    a = math.radians(d); c, s = math.cos(a), math.sin(a)
    return np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]])


def Rz(d):
    a = math.radians(d); c, s = math.cos(a), math.sin(a)
    return np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]])


def star_shape(r):
    """The coin emblem: a chubby 5-point star with round tips and valleys."""
    return star2(5, r, r * 0.56, round=0.16 * r, round_valley=0.10 * r)


# ------------------------------------------------------------------ toon paint (the references' hue-shifted shading)
# The references darken toward a deeper SATURATED hue (yellow -> orange, red -> crimson), which the PBR falloff alone
# cannot do (it goes olive/brown, STYLE.md gotchas). Each part is painted from its own SDF: u = how much the surface
# turns away from the viewer (1 - n_view.z), v = its height on screen; the rig then only adds form and speculars.

SCHEMES = {
    "gold": dict(top="#FFE453", mid="#FFC81F", bot="#FFA40E", etop="#FFB21A", ebot="#EC7A06"),
    "goldDeep": dict(top="#FFD23A", mid="#FFB81A", bot="#FF980C", etop="#F7A012", ebot="#E06A04"),
    "orange": dict(top="#FFAE48", mid="#FF8C1E", bot="#FA740F", etop="#FF8A20", ebot="#E4580A"),
    "yellow": dict(top="#FFE564", mid="#FFD12B", bot="#FFBC1A", etop="#FFC21E", ebot="#F09A10"),
    "red": dict(top="#F4322C", mid="#DE1419", bot="#C40C15", etop="#B00A13", ebot="#7C050D"),
    "blue": dict(top="#00A295", mid="#00847D", bot="#00706D", etop="#007571", ebot="#035553"),
    "bulb": dict(top="#D9ECE8", mid="#C0DED8", bot="#A6D4CE", etop="#70C2BD", ebot="#4FA79E"),
    "ice": dict(top="#94ECFB", mid="#4ACFEF", bot="#33C0EA", etop="#2AB0E4", ebot="#1088D0"),
    "cream": dict(top="#FFF6E8", mid="#FFEEDB", bot="#F8E2CA", etop="#F6DFC4", ebot="#E6C7A6"),
    "slate": dict(top="#5A8781", mid="#4C746F", bot="#436965", etop="#436965", ebot="#3E5552"),
    "arrowRed": dict(top="#FF8A3C", mid="#FF6219", bot="#F2500E", etop="#F4581A", ebot="#D23E08"),
    # director r2: 026's house orange is deeper than the basket's (roof face ~#F8740F, edge ~#D9530A)
    "orangeHouse": dict(top="#FF9A36", mid="#F77A16", bot="#EE640C", etop="#F06A12", ebot="#D04C06"),
    # to-A r4: 026's house body is a warm yellow (#FFC800-ish, orange-ish low), not the lemon "yellow"
    "yellowHouse": dict(top="#FFD21E", mid="#FFBE12", bot="#FFA80A", etop="#FFB012", ebot="#EC8A0A"),
}

# a flatter, brighter toy rig than ui3d.RIG: the painted colours carry the hue shift, the lights only add form
PROP_LIGHT = dict(key_lux=2100.0, key_dir=(0.45, -0.55, -0.70), fill_lux=900.0, fill_color=(1.0, 0.97, 0.94),
                  fill_dir=(0.1, 0.8, -0.6), rim_lux=1100.0, ibl_exp=-0.80,
                  extra=[dict(type="directional", direction=[0.05, -0.12, -1.0], intensity=700.0, color=[1.0, 1.0, 1.0], shadow=False)])


def _view(yaw, pitch, roll):
    return Rz(roll) @ Rx(pitch) @ Ry(yaw)


def toon_texture(sc, e0=0.30, e1=0.95):
    from palette import _rgb
    c = {k: np.asarray(_rgb(v), float) for k, v in sc.items()}

    def fn(u, v):
        v3 = v[..., None]
        lo = c["bot"] + (c["mid"] - c["bot"]) * np.clip(v3 * 2, 0, 1)
        face = np.where(v3 < 0.5, lo, c["mid"] + (c["top"] - c["mid"]) * np.clip(v3 * 2 - 1, 0, 1))
        edge = c["ebot"] + (c["etop"] - c["ebot"]) * v3
        t = np.clip((u - e0) / (e1 - e0), 0, 1)[..., None]
        t = t * t * (3 - 2 * t)
        return face * (1 - t) + edge * t
    return fn


def tpart(name, sdf, scheme, y0, y1, view=(0, 0, 0), rough=0.28, ior=1.42, voxel=None, e0=0.30, e1=0.95, opacity=1.0):
    """A Part painted with a toon scheme; y0..y1 = the model's height range in VIEW space (bottom -> top)."""
    from dataclasses import replace
    from sdf import normals as _normals
    R = _view(*view)

    def uvf(v):
        n = _normals(sdf, v.astype(F), eps=0.003)
        nv = n @ R.T
        yv = (v @ R.T)[:, 1]
        u = np.clip(1 - nv[:, 2], 0, 1)
        vv = np.clip((yv - y0) / (y1 - y0), 0, 1)
        return np.stack([u, vv], 1)
    sc = SCHEMES[scheme] if isinstance(scheme, str) else scheme
    m = Material(name, sc["mid"], roughness=rough, ior=ior, opacity=opacity)
    m = replace(m, texture=toon_texture(sc, e0, e1), texture_size=128)
    return Part(name, sdf, m, uv=("fn", uvf), voxel=voxel)


# ------------------------------------------------------------------ coins (shared by coinStackReward, navShop, coinPileSmall)

def coin_sdf(R=0.5, T=0.13, emblem=True, back=True):
    """A thick coin facing +Z: rounded edge, a raised rim around a recessed field, a raised chubby star (both faces)."""
    body = cylinder(R, T, round=min(0.07, T * 0.6)).transform(Rx(90))
    field = cylinder(R * 0.72, 0.3).transform(Rx(90))
    body = body.subtract(field.translate(0, 0, T + 0.3 - 0.035), k=0.03)
    if back:
        body = body.subtract(field.translate(0, 0, -(T + 0.3 - 0.035)), k=0.03)
    parts = [body]
    if emblem:
        st = extrude(star_shape(R * 0.56), 0.055, round=0.045)
        parts.append(st.translate(0, 0, T - 0.035))
        if back:
            parts.append(st.translate(0, 0, -(T - 0.035)))
    return union(*parts, k=0.012)


def coin_part(name, R=0.5, T=0.13, Rw=np.eye(3), t=(0, 0, 0), emblem=True, back=True, voxel=None):
    """One coin posed in the model: face and field gold, the edge band painted orange (uv from the LOCAL z)."""
    k = R / 0.5                                   # built at the canonical R 0.5 (recess/emblem depths), then scaled
    s = xform(coin_sdf(0.5, T / k, emblem, back).scale(k), Rw, t)
    Rw = np.asarray(Rw, float); tt = np.asarray(t, float)

    def uvf(v):
        loc = (v - tt) @ Rw                      # local coords (row form)
        rad = np.sqrt(loc[:, 0] ** 2 + loc[:, 1] ** 2)
        z = np.abs(loc[:, 2])
        side = np.clip((R * 0.93 - rad) / (R * 0.12), 0, 1)       # 1 inside the face, 0 on the edge
        face = np.clip((z - T * 0.35) / (T * 0.45), 0, 1)
        u = 1 - np.maximum(side, face) * 0.999
        star = (rad < R * 0.6) & (z > T - 0.036 * k)
        field = (rad < R * 0.70) & (z > T * 0.5)
        u = np.where(star, 0.0, np.where(field, 0.3, u * 0.9 + 0.1))
        return np.stack([u, np.zeros_like(u) + 0.5], 1)
    m = painted(gloss(f"{name}_gold", GOLD, rough=0.26, ior=1.45),
                [(0.0, GOLD_STAR), (0.1, GOLD), (0.3, "#FFAC10"), (0.55, "#FFB814"), (1.0, GOLD_SIDE)])
    return Part(name, s, m, uv=("fn", uvf), voxel=voxel, min_tris=10 ** 9)   # no decimation: round rims + clean paint


# ------------------------------------------------------------------ hearts

def heart_outline(yscale=0.9, tip=0.93, soften=18, blur=26):
    """The heart silhouette (width 1): the classic parametric heart, lower half pulled to a firmer tip, as a smooth
    2D distance field (from a raster, blurred inside so the pillow has no crease)."""
    pts = heart_curve(w=1.0)
    pts[:, 1] *= yscale
    pts[:, 1] = np.where(pts[:, 1] < 0, pts[:, 1] * tip, pts[:, 1])
    ext = (-0.62, -0.60, 0.62, 0.60)
    return raster_sdf2(poly_mask(pts, ext, px=720, soften_px=soften), ext, blur_px=blur)


def heart_body(yscale=0.9, depth=0.30, R=0.30, tip=0.93):
    s2 = heart_outline(yscale, tip)
    return extrude(s2, R, round=R).scale_xyz(1, 1, depth / R)


HEART_VIEW = (4, -4, 0)


def heart_broken():
    """The heart split by a lightning-bolt crack from the notch to the tip (measured on 016, heart width = 1):
    the right half sits in front, the halves part a little at the top; a dark-red wall fills the crack."""
    ys = 0.95
    body = heart_body(ys, depth=0.27, tip=0.97)
    zig = [(-0.03, 0.62), (-0.03, 0.28), (-0.10, 0.15), (0.04, 0.06), (-0.065, -0.10), (0.012, -0.19), (-0.012, -0.62)]
    gap = 0.012
    left = polygon2([(-1.0, 0.62)] + zig + [(-1.0, -0.62)]).offset(-gap)
    right = polygon2([(1.0, 0.62)] + zig + [(1.0, -0.62)]).offset(-gap)
    L = body.intersect(extrude(left, 0.6), k=0.012)
    Rr = body.intersect(extrude(right, 0.6), k=0.012)
    L = xform(L, Rz(2.5), (-0.012, 0.006, -0.004))
    Rr = xform(Rr, Rz(-1.2), (0.008, -0.002, 0.004))
    wall2 = stroke2(zig, 0.075, closed=False)
    wall = body.offset(-0.035).intersect(extrude(wall2, 0.6))
    return [tpart("heart_l", L, "red", -0.46, 0.42, HEART_VIEW, rough=0.3, ior=1.45, e0=0.18),
            tpart("heart_r", Rr, "red", -0.46, 0.42, HEART_VIEW, rough=0.3, ior=1.45, e0=0.18),
            Part("crack", wall, satin("crack", RED_DEEP, rough=0.5), voxel=0.003)], VOXEL


def lemniscate_pts(a=0.2, sy=1.25, n=96):
    out = []
    for k in range(n):
        th = 2 * math.pi * k / n
        d = 1 + math.sin(th) ** 2
        out.append((a * math.cos(th) / d, a * math.sin(th) * math.cos(th) / d * sy))
    return out


INF_VIEW = (0, -4, 0)


def heart_infinite():
    """Plump glossy heart (033) with a raised cream infinity sign sitting in a shallow recess."""
    full = heart_body(1.02, depth=0.31, R=0.29, tip=0.98)
    inf2 = stroke2(lemniscate_pts(0.218, 1.42), 0.078).translate(0, 0.07)
    prism = extrude(inf2.offset(0.022), 0.6).translate(0, 0, 0.6)
    body = union(full.subtract(prism), full.offset(-0.03), k=0.012)      # a 0.03 recess that follows the surface
    mark = full.offset(-0.012).intersect(extrude(inf2, 0.6).translate(0, 0, 0.6), k=0.006)
    return [tpart("heart", body, "red", -0.48, 0.44, INF_VIEW, rough=0.26, ior=1.45, e0=0.18),
            tpart("inf_cream", mark, "cream", -0.1, 0.2, INF_VIEW, rough=0.34, ior=1.35, voxel=0.003)], VOXEL


# ------------------------------------------------------------------ stopwatch (013)

SW_VIEW = (-16, -4, -13)


def stopwatch():
    R, T = 0.5, 0.19
    bezel = cylinder(R, T, round=0.17).transform(Rx(90))
    dial_r = 0.315
    well = cylinder(dial_r, 0.4).transform(Rx(90)).translate(0, 0, 0.4 + T - 0.075)
    bezel = bezel.subtract(well, k=0.06)
    zf = T - 0.075
    dial = cylinder(dial_r + 0.01, 0.03, round=0.012).transform(Rx(90)).translate(0, 0, zf - 0.02)
    ticks = []
    for ang in (90, 0, 270, 180):
        a = math.radians(ang)
        p0 = (0.205 * math.cos(a), 0.205 * math.sin(a), zf + 0.016)
        p1 = (0.25 * math.cos(a), 0.25 * math.sin(a), zf + 0.016)
        ticks.append(capsule(p0, p1, 0.043))
    hub = cylinder(0.115, 0.032, round=0.028).transform(Rx(90)).translate(0, 0, zf + 0.03)
    ha = math.radians(-42)
    tip = (0.235 * math.cos(ha), 0.235 * math.sin(ha))
    nrm = (-math.sin(ha), math.cos(ha))
    hand2 = polygon2(fillet_points([(0.085 * nrm[0], 0.085 * nrm[1]), tip, (-0.085 * nrm[0], -0.085 * nrm[1])],
                                   [0.03, 0.02, 0.03], n_arc=6))
    hand = extrude(hand2, 0.018, round=0.014).translate(0, 0, zf + 0.035)
    slate = union(*ticks, hub, hand)
    # crown: orange stem + blue cap at 12, leaning 8 deg clockwise
    Rc = Rz(0)
    stem = xform(cylinder(0.085, 0.06, round=0.02), Rc, Rc @ np.array([0, 0.53, 0]))
    cap = xform(cylinder(0.19, 0.085, round=0.065), Rc, Rc @ np.array([0, 0.645, 0]))
    # side button at ~2:00: blue collar + orange cap, radial
    Rs = Rz(-62)
    collar = xform(cylinder(0.092, 0.05, round=0.03), Rs, Rs @ np.array([0, 0.52, 0]))
    btn = xform(cylinder(0.11, 0.07, round=0.05), Rs, Rs @ np.array([0, 0.615, 0]))
    return [tpart("sw_bezel", bezel, "blue", -0.52, 0.52, SW_VIEW),
            Part("dial", dial, gloss("sw_dial", "#F4F6FA", rough=0.4, ior=1.3)),
            tpart("sw_slate", slate, "slate", -0.3, 0.3, SW_VIEW, rough=0.36, voxel=0.003),
            tpart("sw_cap", union(cap, collar), "blue", 0.3, 0.75, SW_VIEW),
            tpart("sw_stem", union(stem, btn), "orange", 0.3, 0.75, SW_VIEW)], VOXEL


# ------------------------------------------------------------------ boosters (003)

HG_VIEW = (-5, 30, -28)


def hourglass():
    """Frozen hourglass (003): two blue caps, a fat cyan glass double bulb, a snow layer on the top cap with icicles
    hanging over its right rim (screen), a snow lump + one drip on the bottom cap's front rim."""
    capR, capH, cy = 0.40, 0.07, 0.50
    top = cylinder(capR, capH, round=0.05, center=(0, cy, 0))
    bot = cylinder(capR, capH, round=0.05, center=(0, -cy, 0))
    # the classic hourglass glass: wide where it meets the caps, funnelling to a narrow waist (revolved profile)
    prof = spline_profile([(0.0, -0.46), (0.29, -0.46), (0.30, -0.36), (0.26, -0.22), (0.15, -0.10), (0.065, 0.0),
                           (0.15, 0.10), (0.26, 0.22), (0.30, 0.36), (0.29, 0.46), (0.0, 0.46)], samples=80)
    bulbs = revolve(prof)
    rng = np.random.default_rng(3)
    y0 = cy + capH
    blobs = [cylinder(capR - 0.04, 0.03, round=0.028, center=(0.02, y0 + 0.01, 0.01))]
    for _ in range(7):
        a = rng.uniform(0, 2 * math.pi); rr = rng.uniform(0.05, 0.26)
        blobs.append(ellipsoid(0.12, 0.045, 0.12, center=(rr * math.cos(a), y0 + 0.03, -rr * math.sin(a))))
    drips = []
    for ang, ln, r0 in ((5, 0.40, 0.07), (-30, 0.20, 0.056)):
        a = math.radians(ang)
        x, z = (capR + 0.005) * math.cos(a), -(capR + 0.005) * math.sin(a)
        drips.append(round_cone((x, y0 + 0.01, z), (x * 1.04, y0 - ln, z * 1.04), r0, r0 * 0.8))
    snow_top = union(*blobs, *drips, k=0.045)
    lip = []
    for ang in np.linspace(-115, -25, 5):
        a = math.radians(ang)
        lip.append(ellipsoid(0.085, 0.05, 0.07, center=((capR - 0.01) * math.cos(a), -cy + capH + 0.01, -(capR - 0.01) * math.sin(a))))
    a = math.radians(-70)
    x, z = (capR + 0.012) * math.cos(a), -(capR + 0.012) * math.sin(a)
    lip.append(round_cone((x, -cy + capH + 0.01, z), (x * 1.03, -cy - 0.09, z * 1.03), 0.05, 0.042))
    snow_bot = union(*lip, k=0.07)
    snow = satin("hg_snow", SNOW, rough=0.42, ior=1.3)
    return [tpart("hg_caps", union(top, bot), "blue", -0.7, 0.7, HG_VIEW),
            tpart("hg_glass", bulbs, "ice", -0.45, 0.45, HG_VIEW, rough=0.08, ior=1.5, opacity=0.82, e0=0.4),
            Part("snowTop", snow_top, snow), Part("snowBot", snow_bot, snow)], VOXEL


BULB_VIEW = (0, 6, 0)


def bulb():
    """Glossy light bulb: pale-blue glass with a faint blue filament, an orange-gold collar, a blue threaded base."""
    glass_s = union(sphere(0.40, center=(0, 0.16, 0)),
                    capped_cone(0.16, 0.185, 0.29, center=(0, -0.13, 0)), k=0.09)
    glass_s = glass_s.intersect(box(0.5, 0.5, 0.5, center=(0, 0.1, 0)))
    collar = cylinder(0.238, 0.078, round=0.06, center=(0, -0.335, 0))
    base = union(cylinder(0.172, 0.09, round=0.03, center=(0, -0.46, 0)),
                 torus(0.172, 0.03, center=(0, -0.42, 0)), torus(0.165, 0.03, center=(0, -0.50, 0)),
                 capped_cone(0.045, 0.14, 0.06, round=0.025, center=(0, -0.575, 0)), k=0.012)
    zz = [(-0.15, 0.13), (-0.10, 0.22), (-0.05, 0.13), (0.0, 0.23), (0.05, 0.13), (0.10, 0.22), (0.15, 0.13)]
    fil = path_tube([(x, y, 0.06) for x, y in zz], [0.018] * len(zz))
    wires = union(capsule((-0.15, 0.13, 0.06), (-0.07, -0.18, 0.02), 0.016), capsule((0.15, 0.13, 0.06), (0.07, -0.18, 0.02), 0.016))
    return [tpart("bulb_glass", glass_s, "bulb", -0.30, 0.56, BULB_VIEW, rough=0.14, ior=1.45, opacity=0.94, e0=0.28),
            Part("filament", union(fil, wires), satin("bulb_fil", "#6E90D6", rough=0.4), voxel=0.003),
            tpart("bulb_collar", collar, "goldDeep", -0.40, -0.25, BULB_VIEW),
            tpart("bulb_base", base, "blue", -0.62, -0.36, BULB_VIEW)], VOXEL


# ------------------------------------------------------------------ unconfirmed boosters (owner video V1, 4-booster bar; not on v552)

SQ_VIEW = (0, -22, 24)


def set_square():
    """Yellow set-square (V1 t 30 s): a rounded right triangle plate with a triangular window, tick grooves along one
    leg, orange walls (painted by the toon scheme)."""
    tri = [(-0.48, 0.46), (-0.48, -0.46), (0.55, -0.46)]
    outer = polygon2(fillet_points(tri, [0.09, 0.09, 0.09], n_arc=8))
    inner = polygon2(fillet_points([(-0.26, 0.06), (-0.26, -0.26), (0.08, -0.26)], [0.04, 0.04, 0.04], n_arc=6))
    plate = extrude(outer, 0.07, round=0.045).subtract(extrude(inner, 0.3), k=0.02)
    ticks = [box(0.012, 0.05 if i % 2 else 0.08, 0.2, center=(-0.40 + 0.09 * i, -0.46 + (0.05 if i % 2 else 0.08) - 0.01, 0.2 + 0.07 - 0.02))
             for i in range(1, 10)]
    plate = plate.subtract(union(*ticks), k=0.004)
    return [tpart("square", plate, "goldDeep", -0.5, 0.5, SQ_VIEW)], VOXEL


RING_VIEW = (0, 18, 0)


def ring_stack():
    """Ring-stack toy (V1 t 30 s): a yellow base disc, two blue rings on a blue post, a blue ball on top."""
    base = capped_cone(0.07, 0.46, 0.40, round=0.05, center=(0, -0.40, 0))
    ring1 = torus(0.25, 0.13, center=(0, -0.20, 0))
    ring2 = torus(0.16, 0.115, center=(0, 0.02, 0))
    post = cylinder(0.08, 0.2, center=(0, 0.0, 0))
    ball = sphere(0.19, center=(0, 0.28, 0))
    return [tpart("ring_base", base, "gold", -0.5, -0.3, RING_VIEW),
            tpart("ring_blue", union(ring1, ring2, post, ball, k=0.02), "blue", -0.3, 0.45, RING_VIEW)], VOXEL


# ------------------------------------------------------------------ nav icons (026)

SHOP_VIEW = (0, 10, 0)


def basket():
    """Orange shop basket (tapered tub, thick rim band, three slots) with a star coin standing in it."""
    tub = box(0.43, 0.25, 0.26, round=0.11).taper(-0.25, 0.25, 0.80, 1.0).translate(0, -0.08, 0)
    slots = []
    for x in (-0.19, 0.0, 0.19):
        slots.append(box(0.052, 0.115, 0.2, round=0.05, center=(x * 0.93, -0.10, 0.39)))
    tub = tub.subtract(union(*slots), k=0.02)
    rim = box(0.49, 0.075, 0.30, round=0.07, center=(0, 0.20, 0))
    body = union(tub, rim, k=0.02)
    cz = coin_part("coin", R=0.30, T=0.075, Rw=Rx(-10), t=(0, 0.38, -0.02), back=False)
    return [tpart("basket", body, "orange", -0.35, 0.3, SHOP_VIEW), cz], VOXEL


HOUSE_VIEW = (0, 4, 0)


def house():
    """Yellow garage-house (026 raised Home tab): arch-topped block inside a THICK orange roof arch whose ends flare
    outward, a big round window, an orange garage frame with a cream roller door, a wide cream chimney under an orange
    cap, orange plinths."""
    from uikit import arc2
    # director round 2 (026 at 4 px/pt: the raised icon is 74 x 82 pt, the yellow body ~0.88 of the eave span, a thick
    # arch, a big door arch and wide orange corner blocks): body widened 0.80 -> 0.96, arch/eaves/door/feet thickened
    # to-A r4 (026 at 12 px/pt, registered on the frame): the roof arch is ELLIPTICAL -- same top (outer ~0.675) and
    # span, but its ends / eaves sit ~8 pt (0.16 u) HIGHER than round 3's semicircle (026: eaves at shot y 766-778), so
    # the arch reads flatter; the band keeps its 0.25 thickness; the body's top follows it. The door frame is ~24 %
    # wider (026: 39 pt outer, door 25 pt) and the roller door a darker cream-beige with brown slat lines.
    def ell2(rx, ry, cx=0.0, cy=0.0):
        k = min(rx, ry)

        def fn(p):
            q = (p - np.array([cx, cy], F)) / np.array([rx, ry], F)
            return ((np.sqrt((q * q).sum(1)) - 1.0) * k).astype(F)
        return SDF2(fn, np.array([cx - rx, cy - ry]), np.array([cx + rx, cy + ry]))
    ay, arx, ary, at = 0.18, 0.655, 0.495, 0.25
    ring = ell2(arx, ary, 0, ay).subtract(ell2(arx - at, ary - at, 0, ay))
    cutb = rect2(1.0, 0.6).translate(0, ay - 0.6 - 0.02)        # keep the upper half (+ a hair below the centre line)
    roof2 = ring.subtract(cutb)
    eave = rect2(0.12, 0.10, round=0.08)
    roof2 = roof2.union(eave.translate(-0.60, ay - 0.04)).union(eave.translate(0.60, ay - 0.04))
    body2 = rect2(0.48, 0.39).translate(0, -0.21).union(ell2(0.50, 0.36, 0, ay))
    body = extrude(body2, 0.15, round=0.08)
    roof = extrude(roof2, 0.22, round=0.09)
    chim = box(0.235, 0.09, 0.10, round=0.035, center=(0, 0.71, -0.03))     # to-A r4: 026's cream chimney is wide
    chim_cap = box(0.27, 0.075, 0.14, round=0.062, center=(0, 0.84, -0.03))
    win_ring = torus(0.13, 0.055).transform(Rx(90)).translate(0, 0.20, 0.15)
    win_glass = cylinder(0.105, 0.02).transform(Rx(90)).translate(0, 0.20, 0.135)
    frame2 = rect2(0.37, 0.30, round=0.15).translate(0, -0.33).subtract(rect2(0.25, 0.27, round=0.035).translate(0, -0.38))
    frame = extrude(frame2, 0.07, round=0.05).translate(0, 0, 0.13)
    door = box(0.25, 0.26, 0.02, round=0.01, center=(0, -0.38, 0.135))
    feet = union(box(0.15, 0.125, 0.18, round=0.06, center=(-0.40, -0.515, 0.02)),
                 box(0.15, 0.125, 0.18, round=0.06, center=(0.40, -0.515, 0.02)))

    def stripes(u, v):
        from palette import _rgb
        a = np.asarray(_rgb("#E2C8AA")); b = np.asarray(_rgb("#B08864"))
        t = ((v * 4.0) % 1.0)
        line = np.clip(1 - np.abs(t - 0.08) / 0.06, 0, 1)
        return a[None, None] * (1 - line[..., None]) + b[None, None] * line[..., None]
    from dataclasses import replace
    door_m = replace(satin("house_door", "#E2C8AA", rough=0.45), texture=stripes, texture_size=256)
    uvd = ("planar", (0.0, -0.64, 0.0), (1, 0, 0), (0, 1, 0), 1.0 / 0.52)
    return [tpart("house_yellow", body, "yellowHouse", -0.62, 0.52, HOUSE_VIEW),
            tpart("house_orange", union(roof, chim_cap, win_ring, frame, feet), "orangeHouse", -0.66, 0.92, HOUSE_VIEW),
            tpart("house_chim", chim, "cream", 0.62, 0.80, HOUSE_VIEW, rough=0.45),
            Part("window", win_glass, gloss("house_glass", "#4FAEFF", rough=0.2, ior=1.45)),
            Part("door", door, door_m, uv=uvd)], VOXEL


TROPHY_VIEW = (0, -4, 0)


def trophy():
    """Gold trophy cup (026): a tall rim band over a full U bowl, thick C handles, a short thick neck, a pillow knot,
    a wide flat foot; a big orange up-arrow embossed on the bowl."""
    prof = spline_profile([(0.0, -0.10), (0.17, -0.09), (0.29, -0.02), (0.35, 0.10), (0.37, 0.22), (0.375, 0.35), (0.0, 0.35)], samples=60)
    bowl = revolve(prof)
    rim = cylinder(0.41, 0.09, round=0.06, center=(0, 0.43, 0))
    neck = cylinder(0.10, 0.05, center=(0, -0.14, 0))
    knot = cylinder(0.175, 0.05, round=0.048, center=(0, -0.215, 0))
    neck2 = cylinder(0.10, 0.045, center=(0, -0.29, 0))
    foot = cylinder(0.33, 0.075, round=0.07, center=(0, -0.385, 0))
    hs = []
    for sx in (-1, 1):
        th = np.linspace(math.radians(105), math.radians(-100), 14)
        cx, cy, rx, ry = 0.40, 0.19, 0.155, 0.15
        pts = [(sx * (cx + rx * math.cos(a)), cy + ry * math.sin(a), 0.0) for a in th]
        pts[0] = (sx * 0.33, 0.35, 0.0); pts[-1] = (sx * 0.30, 0.03, 0.0)
        hs.append(path_tube(pts, [0.072] * len(pts)))
    cup = union(bowl, rim, neck, knot, neck2, foot, *hs, k=0.03)
    arr2 = polygon2(fillet_points([(0, 0.17), (0.17, 0.005), (0.078, 0.005), (0.078, -0.15), (-0.078, -0.15), (-0.078, 0.005), (-0.17, 0.005)],
                                  [0.035, 0.035, 0.012, 0.025, 0.025, 0.012, 0.035], n_arc=6)).translate(0, 0.165)
    mark = cup.offset(0.026).intersect(extrude(arr2, 0.6).translate(0, 0, 0.6), k=0.01)
    return [tpart("trophy_gold", cup, "gold", -0.46, 0.52, TROPHY_VIEW),
            tpart("trophy_arrow", mark, "arrowRed", 0.0, 0.34, TROPHY_VIEW, voxel=0.003)], VOXEL


# ------------------------------------------------------------------ Claw (023, 025)

LOCK_VIEW = (0, 3, 0)


def padlock():
    """Chunky gold padlock (023): a pillowy sack-shaped body, a short thick shackle, a recessed keyhole."""
    b2 = polygon2(fillet_points([(-0.40, 0.36), (0.40, 0.36), (0.47, -0.36), (-0.47, -0.36)], [0.22, 0.22, 0.30, 0.30], n_arc=10))
    body = extrude(b2, 0.19, round=0.18).translate(0, -0.12, 0)
    shackle = torus(0.19, 0.092).transform(Rx(90)).translate(0, 0.30, -0.02).intersect(box(0.4, 0.2, 0.2, center=(0, 0.47, 0)))
    legs = union(capsule((-0.19, 0.30, -0.02), (-0.19, 0.12, -0.02), 0.092), capsule((0.19, 0.30, -0.02), (0.19, 0.12, -0.02), 0.092))
    hole2 = circle2(0.088).translate(0, -0.05).union(polygon2([(-0.04, -0.08), (0.04, -0.08), (0.065, -0.27), (-0.065, -0.27)]))
    hole2 = hole2.offset(0.008)
    body = body.subtract(extrude(hole2, 0.3).translate(0, 0, 0.3 + 0.19 - 0.05), k=0.015)
    floor = extrude(hole2.offset(0.012), 0.02).translate(0, 0, 0.19 - 0.063)
    return [tpart("lock_gold", body, "gold", -0.48, 0.24, LOCK_VIEW),
            tpart("lock_shackle", union(shackle, legs, k=0.02), "goldDeep", 0.12, 0.60, LOCK_VIEW),
            Part("hole", floor, satin("lock_hole", "#9A3206", rough=0.5))], VOXEL


def coin_reward():
    """The win-popup reward cluster (020): big thick star coins packed tight -- a coin standing tilted back at the
    back-left, a flat pair at the back-right, a flat trio at the left, a big standing coin in front at the right, a
    flat pair peeking out at the far right. Coins lie with their face up (Rx -90); standing ones face the viewer."""
    parts = []
    R, T = 0.33, 0.08
    k = 0
    for (x, y, z, n, yaw) in ((0.26, 0.18, -0.32, 2, 10), (-0.40, -0.28, -0.02, 3, -20), (0.58, -0.08, -0.14, 2, 30)):
        for i in range(n):
            parts.append(coin_part(f"c{k}", R, T, Rw=Ry(yaw + 9 * i) @ Rx(-90 + 4 * i), t=(x + 0.015 * i, y + i * 2 * T * 0.97, z)))
            k += 1
    parts.append(coin_part(f"c{k}", 0.38, 0.09, Rw=Ry(18) @ Rx(-26) @ Rz(12), t=(-0.24, 0.24, -0.12))); k += 1
    parts.append(coin_part(f"c{k}", 0.38, 0.09, Rw=Ry(-18) @ Rx(-12) @ Rz(-8), t=(0.22, -0.17, 0.24))); k += 1
    return parts, VOXEL


def stack_sdf(x, z, n, r, t):
    """A stack of n coins as ONE field: a rounded cylinder with a groove at every interior coin boundary."""
    H = n * t
    base = cylinder(r, H / 2, round=t * 0.42, center=(x, H / 2, z))
    bf = base.fn
    c = np.array([x, 0, z], F)
    tf, rf = F(t), F(r)

    def fn(p):
        d = bf(p)
        q = p - c
        rxz = np.sqrt(q[:, 0] ** 2 + q[:, 2] ** 2)
        yy = q[:, 1] / tf
        k = np.round(yy)
        fr = (yy - k) * tf
        dent = np.sqrt((rxz - rf) ** 2 + fr ** 2) - tf * 0.3
        inner = (k >= 1) & (k <= n - 1)
        return np.where(inner, np.maximum(d, -dent), d).astype(F)
    return SDF(fn, base.lo, base.hi)


def coin_pile():
    """A mound of coin stacks (025): stacks on a jittered grid inside an ellipse, heights from a mound curve, a few
    loose coins leaning on top. One SDF (union with box culling) + a per-vertex face/edge paint."""
    rng = np.random.default_rng(7)
    r, t = 0.075, 0.03
    tops = []
    fields = []
    for gz in np.arange(-0.30, 0.31, 0.12):
        row = int(round((gz + 0.30) / 0.12))
        for gx in np.arange(-0.78, 0.79, 0.13):
            x = gx + rng.uniform(-0.02, 0.02) + (0.065 if row % 2 else 0.0)
            z = gz + rng.uniform(-0.02, 0.02)
            q = (x / 0.80) ** 2 + (z / 0.34) ** 2
            if q > 1:
                continue
            n = max(1, int(round(2 + 20 * (1 - q) ** 0.9 * (1.0 - 0.30 * (z / 0.34)) + rng.uniform(-1.8, 1.8))))
            fields.append(stack_sdf(x, z, n, r, t))
            tops.append((x, z, t * n))
    top_arr = np.array(tops)
    loose = []
    for (x, z, ang, yaw) in ((-0.12, 0.10, 55, 20), (0.20, 0.06, 40, -30), (-0.34, 0.14, 35, 60)):
        near = [h for (sx, sz, h) in tops if abs(sx - x) < 0.12 and abs(sz - z) < 0.12]
        hh = max(near) if near else 0.1
        loose.append(xform(cylinder(r * 1.05, t * 0.5, round=t * 0.42), Ry(yaw) @ Rx(ang), (x, hh + 0.035, z)))
    s = union(*fields, *loose, k=0.0, pad=0.03)
    # coins standing on edge against the front of the mound, faces (with a star) toward the viewer
    front = []
    for (x, z, rz) in ((-0.42, 0.28, 8), (0.10, 0.33, -6), (0.46, 0.25, 12)):
        front.append(coin_part(f"front{len(front)}", r * 1.25, t * 0.55, Rw=Rx(-12) @ Rz(rz), t=(x, r * 1.25, z + 0.04), back=False, voxel=0.0025))

    def uvf(v):
        from scipy.spatial import cKDTree
        tree = cKDTree(top_arr[:, [0, 1]])
        d, idx = tree.query(v[:, [0, 2]])
        top = top_arr[idx, 2]
        face = (v[:, 1] > top - 0.005) & (d < r * 0.8)
        high = v[:, 1] > top + 0.015
        fr = (v[:, 1] / t) % 1.0
        groove = np.clip(1 - np.minimum(fr, 1 - fr) / 0.22, 0, 1)
        u = np.where(face | high, 0.1, 0.55 + 0.45 * groove)
        return np.stack([u, np.zeros_like(u) + 0.5], 1)
    m = painted(gloss("pile_gold", GOLD, rough=0.28, ior=1.45),
                [(0.0, GOLD_STAR), (0.1, GOLD), (0.55, "#FFB412"), (1.0, "#D97E04")])
    return [Part("pile", s, m, uv=("fn", uvf), voxel=0.003)] + front, 0.003


# ------------------------------------------------------------------ post (2D, ours): glow + twinkles

def _glow(color, alpha, radius, center=(0.5, 0.5), squash=1.0):
    """fn(PIL RGBA) -> RGBA: a soft radial glow UNDER the art (radius in frame fractions)."""
    def post(im):
        from PIL import Image
        W, H = im.size
        yy, xx = np.mgrid[0:H, 0:W]
        dx = (xx + 0.5) / W - center[0]
        dy = ((yy + 0.5) / H - center[1]) / squash
        d = np.sqrt(dx * dx + dy * dy) / radius
        a = np.clip(1 - d, 0, 1) ** 2.2 * alpha
        from palette import _rgb
        c = np.asarray(_rgb(color)) * 255
        g = np.zeros((H, W, 4), np.float32)
        g[..., :3] = c
        g[..., 3] = a * 255
        base = Image.fromarray(g.astype(np.uint8), "RGBA")
        base.alpha_composite(im)
        return base
    return post


def _twinkles(spots):
    """fn(PIL RGBA) -> RGBA: 4-point white twinkles (ours, drawn here) at (x, y, size) frame fractions."""
    def post(im):
        from PIL import Image
        W, H = im.size
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
        acc = np.zeros((H, W), np.float32)
        for (fx, fy, fs) in spots:
            cx, cy, s = fx * W, fy * H, fs * W
            dx, dy = np.abs(xx - cx) / s, np.abs(yy - cy) / s
            star = np.clip(1 - (np.sqrt(dx) + np.sqrt(dy)) * 1.0, 0, 1) ** 1.2
            core = np.exp(-((dx * dx + dy * dy) * 30))
            acc = np.maximum(acc, np.maximum(star, core * 0.9))
        ov = np.zeros((H, W, 4), np.float32)
        ov[..., 0] = 255; ov[..., 1] = 255; ov[..., 2] = 255
        ov[..., 3] = np.clip(acc, 0, 1) * 255
        # a faint blue-white bloom around each twinkle
        out = im.copy()
        out.alpha_composite(Image.fromarray(ov.astype(np.uint8), "RGBA"))
        return out
    return post


def _satgrade(s_keep=0.15, dh=-0.012, dv=0.04):
    """fn(PIL RGBA) -> RGBA (FIX-V2 F-01, 2026-09-27): the phone's nav icons are fully saturated (S median 0.96-0.98 on
    meta-001 / 026) where our toon renders came out at 0.76-0.77 and a hair yellower: saturated pixels (weight
    smoothstep(0.25, 0.50, S)) go to S' = 1 - (1 - S)·s_keep, hue + dh, value × (1 - dv); whites / creams / highlights keep.
    Same maths as build/fixv2/tools/navgrade.py, which graded the shipped navShop / navHome / navTrophy PNGs in place."""
    def post(im):
        from PIL import Image
        a = np.asarray(im.convert("RGBA")).astype(np.float64) / 255.0
        rgb, alpha = a[..., :3], a[..., 3:]
        mx = rgb.max(-1); mn = rgb.min(-1); d = mx - mn
        s = np.where(mx > 0, d / np.maximum(mx, 1e-9), 0)
        r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
        m = d > 1e-9
        rc = np.where(m, (mx - r) / np.maximum(d, 1e-9), 0); gc = np.where(m, (mx - g) / np.maximum(d, 1e-9), 0)
        bc = np.where(m, (mx - b) / np.maximum(d, 1e-9), 0)
        h = np.where(r == mx, bc - gc, np.where(g == mx, 2.0 + rc - bc, 4.0 + gc - rc))
        h = np.where(m, (h / 6.0) % 1.0, 0)
        t = np.clip((s - 0.25) / 0.25, 0, 1); w = t * t * (3 - 2 * t)
        s2 = s + w * ((1 - (1 - s) * s_keep) - s); h2 = (h + w * dh) % 1.0; v2 = mx * (1 - dv * w)
        i = np.floor(h2 * 6).astype(int) % 6; f = h2 * 6 - np.floor(h2 * 6)
        p_ = v2 * (1 - s2); q = v2 * (1 - f * s2); tt = v2 * (1 - (1 - f) * s2)
        out = np.zeros_like(rgb)
        for k, (R, G, B) in enumerate([(v2, tt, p_), (q, v2, p_), (p_, v2, tt), (p_, q, v2), (tt, p_, v2), (v2, p_, q)]):
            sel = i == k
            out[..., 0][sel] = R[sel]; out[..., 1][sel] = G[sel]; out[..., 2][sel] = B[sel]
        res = np.concatenate([out, alpha], -1)
        return Image.fromarray(np.clip(res * 255 + 0.5, 0, 255).astype(np.uint8), "RGBA")
    return post


def _chain(*fns):
    def post(im):
        for f in fns:
            im = f(im)
        return im
    return post


MODELS = dict(set_square=set_square, ring_stack=ring_stack, hourglass=hourglass, bulb=bulb, stopwatch=stopwatch, heart_broken=heart_broken, heart_infinite=heart_infinite,
              basket=basket, house=house, trophy=trophy, padlock=padlock, coin_reward=coin_reward, coin_pile=coin_pile)

# fills/aligns register each prop with its reference at scale 1 (manifest_sheets pastes the frame centre on the ref box
# centre): measured object sizes in pt are in the lane log
def _A(model, view, **kw):
    kw.setdefault("light", PROP_LIGHT)
    return dict(model=model, yaw=view[0], pitch=view[1], roll=view[2], **kw)


ASSETS = {
    "boosterFreeze": _A("hourglass", HG_VIEW, frame=(56, 56), fill=(0.66, 0.72), align=(0.5, 0.52)),
    "boosterHint": _A("bulb", BULB_VIEW, frame=(56, 56), fill=(0.66, 0.80), align=(0.5, 0.5)),
    "stopwatchBig": _A("stopwatch", SW_VIEW, frame=(225, 225), fill=0.975, align=(0.46, 0.54),
                       post_fit=_glow("#00706D", 0.6, 0.52, center=(0.56, 0.52))),
    "heartBroken": _A("heart_broken", HEART_VIEW, frame=(160, 132), fill=0.955, outline=("#8C0C10", 3)),
    "coinStackReward": _A("coin_reward", (-6, 24, 0), frame=(110, 100), fill=(0.88, 0.95), align=(0.56, 0.5),
                          post_fit=_twinkles([(0.055, 0.38, 0.05), (0.975, 0.34, 0.022)])),
    "heartInfinite": _A("heart_infinite", INF_VIEW, frame=(92, 84), fill=(0.85, 0.80), align=(0.48, 0.45)),
    "navShop": _A("basket", SHOP_VIEW, frame=(62, 62), fill=(0.88, 0.88), post_fit=_satgrade()),
    "navHome": _A("house", HOUSE_VIEW, frame=(80, 86), fill=(0.93, 0.95), post_fit=_satgrade()),   # director r2: 026's icon is 74 x 82 pt
    "navTrophy": _A("trophy", TROPHY_VIEW, frame=(68, 62), fill=(0.84, 0.92), align=(0.5, 0.52), fov=10, post_fit=_satgrade()),
    "padlockGold": _A("padlock", LOCK_VIEW, frame=(44, 54), fill=(0.90, 0.92), align=(0.5, 0.66), outline=("#B04008", 3)),
    # unconfirmed (V1 only): 40 pt frames, icon ~30 pt like the 4-bar's buttons
    "boosterPointer": _A("set_square", SQ_VIEW, frame=(40, 40), fill=(0.94, 0.94), align=(0.45, 0.45)),
    "boosterDome": _A("ring_stack", RING_VIEW, frame=(40, 40), fill=(0.86, 0.94), align=(0.45, 0.45)),
    "coinPileSmall": _A("coin_pile", (0, 12, 0), frame=(68, 56), fill=(0.95, 0.70), align=(0.5, 0.86),
                        post_fit=_glow("#FFB02A", 0.95, 0.62, center=(0.5, 0.45), squash=0.72)),
}
