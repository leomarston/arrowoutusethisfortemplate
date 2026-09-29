"""Home lab scene (scene lane): homeBackdrop, homeConsole, homeCapsuleMachine, homeArrowPile{Full,Half,Low},
homePlatform. Rendered by scene_make.py (`$PY art/ui/recipes/scene_make.py home`).

Reference (LOOKED AT only): research/shots/002-home-L32.png (+ 026, 070, 168, 204 for the pile states), measured in
pt (px / 3) on gridded crops. Every object is modelled here from those measurements (SDF or analytic surfaces) and
rendered by mfrender; the structural walls are painted in code (gradients + soft bevels) -- nothing is sampled from,
traced over or copied out of the captures. Colours are hex values chosen against the reference's measured tones.

Units: 1 world unit = 10 pt at the object's own scale (each object is fitted into its measured screen box).
"""
from __future__ import annotations

import math

import numpy as np

from scene_kit import (Part, box, capped_cone, capsule, circle2, cylinder, ellipsoid, extrude, fillet_points, gloss, path_tube,
                       glass, grid_part, metal, polygon2, rect2, revolve, round_cone, rounded_polygon2, satin, sphere,
                       spline_profile, torus, union, rbox, mat, rot_x, rot_y, rot_z, SDF, SDF2, F, rgb, hexs, mix)

# ====================================================================== the platform (round dais on the floor)
# 002: inner disc x 5..388, y 596..735 (centre 196.5, 665); outer rim ellipse wider than the screen (~ -8..401),
# y 584..750. A wide shallow disc with a broad soft rim, glossy lilac-blue floor plastic. Analytic lathe mesh (an SDF
# of a 40-unit disc at a fine voxel took 80 s to mesh).

PLAT_R = 20.0          # outer radius (units)
PLAT_IN = 18.3         # inner (recessed) disc radius


def platform():
    from dataclasses import replace
    from scene_kit import lathe_part, planar_uv
    prof = [(0.0, -0.3), (PLAT_R - 0.3, -0.3), (PLAT_R, -0.1), (PLAT_R - 0.05, 0.18), (PLAT_R - 0.45, 0.38),
            (PLAT_R - 1.1, 0.42), (PLAT_IN + 0.4, 0.34), (PLAT_IN - 0.3, 0.16), (PLAT_IN - 1.2, 0.10), (6.0, 0.10), (0.0, 0.10)]
    m = satin("plat", "#BCC8EE", rough=0.45, ior=1.3)
    m = replace(m, texture=_platform_tex(), texture_size=512)
    return [lathe_part("plat", m, prof, n_seg=360, samples=220, uv_fn=planar_uv(-PLAT_R, -PLAT_R, 2 * PLAT_R))], 0.05


def _platform_tex():
    """Top-down albedo: the rim ring a light lilac, the inner disc blue-lilac, lighter toward the front (the room light
    pools on the near half) and bluer toward the back (the blue wall's reflection)."""
    def fn(u, v):
        x = (u - 0.5) * 2 * PLAT_R
        z = (v - 0.5) * 2 * PLAT_R            # +z = toward the viewer (front)
        r = np.sqrt(x * x + z * z)
        inner = np.clip((PLAT_IN + 0.15 - r) / 0.4, 0, 1)[..., None]
        back = np.clip(-z / PLAT_R, 0, 1)[..., None] ** 1.2
        front = np.clip(z / PLAT_R, 0, 1)[..., None]
        side = np.clip(np.abs(x) / PLAT_R, 0, 1)[..., None] ** 2
        c_in = rgb("#9FB3E6") * (1 - back * 0.55) + rgb("#7890DC") * back * 0.55
        c_in = c_in * (1 - front * 0.6) + rgb("#B3B6E0") * front * 0.6
        c_in = c_in * (1 - side * 0.25) + rgb("#95A3DC") * side * 0.25
        c_rim = rgb("#AEB9E8") * (1 - back * 0.45) + rgb("#8EA3E2") * back * 0.45
        return c_in * inner + c_rim * (1 - inner)
    return fn


# ====================================================================== the console (desk in front of the scientist)
# 002 (pt): top rim x 100..293 (the top plate's front edge y ~322 at the centre, back edge ~300), cream tub body down to
# y ~357 (it narrows: x ~118..276 at the bottom), blue round base y 355..372 (x ~128..262) with a 3-slot vent plate at
# the front; green dome button (ball r ~16 pt) on a grey-blue boss at (195, 320) on the tub's top front edge; on the
# top: red-ball joystick (123, 278) left, three red push buttons at x ~155/190/225 y ~297, a purple lever handle
# (240..265, 282..292) and a yellow slotted dome (250..283, 295..310) at the right.

CON_A = 10.0       # tub semi-axis x (units = 10 pt) -- director round 2: 9.7 read ~0.9x of 002's 193 pt rim
CON_B = 5.0        # tub semi-axis z (depth; 002 shows ~20 pt of the top surface behind the rim)
CON_H = 3.9        # belly height below the rim (002: belly 332..365 pt, a thick blue rim 317..332 above it)
RIM_H = 1.45       # the glossy blue rim band (002: ~15 pt tall, much thicker than round 1's 0.76-unit plate)


def _ellip(sdf3, b_over_a):
    """Squash a Y-revolved solid in z (elliptical plan). Distances shrink by at most the ratio: meshing is unaffected."""
    return sdf3.scale_xyz(1.0, 1.0, b_over_a)


def _belly_tex():
    """002's tub belly: pale cream-white under the rim turning warm pale yellow toward the bottom (round 1 was a flat
    cool cream). v runs up the tub (planar uv on y)."""
    def fn(u, v):
        t = np.clip(v, 0, 1)[..., None]
        lo, mid, hi = rgb("#F2D38E"), rgb("#F9E6B8"), rgb("#FDF5E6")
        c = np.where(t < 0.55, lo + (mid - lo) * (t / 0.55), mid + (hi - mid) * ((t - 0.55) / 0.45))
        return c * np.ones_like(u)[..., None]
    return fn


def console():
    from dataclasses import replace
    k = CON_B / CON_A
    parts = []
    # tub: a wide bowl, nearly vertical under the rim, rounding in to ~0.63 of the rim radius at the bottom (002)
    prof = spline_profile([(0.0, -0.05), (5.9, -0.05), (7.7, 0.4), (8.9, 1.1), (9.6, 1.95), (9.9, 2.8),
                           (9.88, 3.45), (9.75, CON_H), (0.0, CON_H)], samples=80)
    tub = _ellip(revolve(prof), k)
    cream = replace(satin("con_cream", "#F9E6B8", rough=0.40, ior=1.30), texture=_belly_tex(), texture_size=256)
    parts.append(Part("tub", tub, cream, voxel=0.05,
                      uv=("planar", (-CON_A - 1, -0.1, 0.0), (1, 0, 0), (0, 1, 0), 1.0 / (CON_H + 0.2))))
    # rim: a thick rounded glossy blue band (a flattened ring) around the top, overhanging the belly a little
    rim = _ellip(cylinder(CON_A + 0.35, RIM_H / 2, round=0.62, center=(0, CON_H + RIM_H / 2 - 0.05, 0)), k)
    parts.append(Part("plate", rim, gloss("con_blue", "#1F8FF2", rough=0.22, ior=1.42), voxel=0.04))
    # top surface inside the rim: light blue-grey (002: the plate behind the buttons reads #C9D6F2)
    top = _ellip(cylinder(CON_A - 0.45, 0.06, round=0.05, center=(0, CON_H + RIM_H - 0.02, 0)), k)
    parts.append(Part("top", top, satin("con_top", "#CAD6F1", rough=0.4), voxel=0.03))
    # base: a blue drum under the tub, with a darker ring where it meets the tub
    base = _ellip(cylinder(5.9, 0.45, round=0.2, center=(0, -0.4, 0)), 5.2 / 6.8)      # 002: a short band 363..373 pt
    parts.append(Part("base", base, gloss("con_base", "#1E86EA", rough=0.3), voxel=0.05))
    # vent plate on the base front: a grey rounded plate with three dark slots
    zf = 5.2 * 5.9 / 6.8 - 0.1
    vent = rbox(3.3, 1.1, 0.5, 0.25, center=(0, -0.55, zf))
    for i in (-1, 0, 1):
        vent = vent.subtract(rbox(0.42, 0.75, 0.9, 0.2, center=(i * 0.85, -0.55, zf + 0.3)))
    parts.append(Part("vent", vent, satin("con_vent", "#C9D2E6", rough=0.35), voxel=0.02))
    slots = union(*[rbox(0.40, 0.7, 0.2, 0.18, center=(i * 0.85, -0.55, zf + 0.02)) for i in (-1, 0, 1)])
    parts.append(Part("slots", slots, satin("con_slot", "#2B3A78", rough=0.5), voxel=0.02))
    # green dome button on a grey-blue boss, on the tub's front top edge
    zfront = CON_B + 0.2
    yb = CON_H + 0.35                       # 002: the dome sits on the rim's front, its boss overlapping the belly
    boss = cylinder(2.25, 0.35, round=0.28).rotate_x(90).translate(0, yb - 0.25, zfront + 0.05)
    parts.append(Part("boss", boss, satin("con_boss", "#8E9FD6", rough=0.32, ior=1.35), voxel=0.03))
    ring = torus(1.9, 0.22).rotate_x(90).translate(0, yb - 0.25, zfront + 0.4)
    parts.append(Part("bossring", ring, satin("con_bossr", "#B4C0EA", rough=0.3), voxel=0.02))
    dome = sphere(1.72, center=(0, yb, zfront + 0.45))
    parts.append(Part("dome", dome, gloss("con_green", "#2FC62A", rough=0.18, ior=1.45), voxel=0.025))
    ytop = CON_H + RIM_H + 0.02
    # joystick (left, near the back): grey base, yellow collar, stem, red ball
    jx, jz = -6.9, -0.4
    parts.append(Part("joyBase", cylinder(1.05, 0.45, round=0.35, center=(jx, ytop + 0.35, jz)),
                      satin("con_grey", "#B7C0DA", rough=0.3), voxel=0.02))
    parts.append(Part("joyCollar", cylinder(0.42, 0.22, round=0.12, center=(jx, ytop + 1.05, jz)),
                      gloss("con_yellow", "#F6B81A", rough=0.3), voxel=0.015))
    parts.append(Part("joyStem", capsule((jx, ytop + 1.0, jz), (jx - 0.05, ytop + 2.4, jz), 0.2),
                      satin("con_stem", "#D5DAEA", rough=0.25), voxel=0.015))
    parts.append(Part("joyBall", sphere(0.95, center=(jx - 0.05, ytop + 2.75, jz)),
                      gloss("con_red", "#E3314A", rough=0.22, ior=1.45), voxel=0.02))
    # three red push buttons on grey bases, along an arc across the top
    for i, x in enumerate((-3.6, 0.0, 3.6)):
        z = -1.2 + 0.2 * abs(x) / 3.6
        parts.append(Part(f"btnBase{i}", cylinder(0.98, 0.18, round=0.12, center=(x, ytop + 0.12, z)),
                          satin(f"con_grey", "#B7C0DA", rough=0.3), voxel=0.02))
        parts.append(Part(f"btn{i}", cylinder(0.78, 0.28, round=0.22, center=(x, ytop + 0.5, z)),
                          gloss("con_red2", "#E0344C", rough=0.24, ior=1.45), voxel=0.02))
    # lever (right): a grey post with a purple handle lying toward the left
    lx, lz = 6.2, -0.8
    parts.append(Part("levBase", cylinder(0.75, 0.3, round=0.2, center=(lx, ytop + 0.25, lz)),
                      satin("con_grey", "#B7C0DA", rough=0.3), voxel=0.02))
    parts.append(Part("levPost", capsule((lx, ytop + 0.3, lz), (lx, ytop + 1.4, lz), 0.26),
                      satin("con_stem", "#D5DAEA", rough=0.25), voxel=0.015))
    parts.append(Part("levHandle", capsule((lx - 2.3, ytop + 1.55, lz + 0.2), (lx + 0.2, ytop + 1.6, lz), 0.5),
                      gloss("con_purple", "#9A5BE6", rough=0.26, ior=1.42), voxel=0.02))
    # yellow slotted dome at the right front of the top
    dx, dz = 7.1, 1.0
    dome2 = sphere(1.6, center=(dx, ytop - 0.55, dz)).intersect(box(3, 3, 3, center=(dx, ytop + 2.3, dz)))
    for i in (-1, 0, 1):
        dome2 = dome2.subtract(sphere(0.23, center=(dx + i * 0.6, ytop + 0.72, dz + 0.55)))
    parts.append(Part("dial", dome2, gloss("con_yellow", "#F6B81A", rough=0.3), voxel=0.02))
    return parts, 0.04


# ====================================================================== the capsule machine
# 002 (pt; world x = (sx - 195) / 10, y = (576 - sy) / 10): blue frame x 100..290, y 382..518 (r ~24 pt); window
# opening inset ~10 pt, a light glass-blue bezel ~7 pt, a deep blue cavity (back wall, lit floor with a two-panel hatch);
# a lilac-grey dispenser ring (x 163..228, y ~398..425) hanging from the cavity ceiling with a glowing cyan opening;
# a narrower housing under the window (x 130..262) down to the floor (y 576) with a dark recess for the live LEVEL
# plate (plate 147.5..246 x 536.8..569 pt, SPEC-ui home.levelPlate).

MA_HX, MA_Y0, MA_Y1, MA_R = 9.5, 5.8, 19.4, 2.4          # frame
OP_HX, OP_Y0, OP_Y1, OP_R = 8.7, 6.2, 18.7, 1.9          # opening (frame band ~8 pt)
IN_HX, IN_Y0, IN_Y1, IN_R = 7.7, 6.75, 18.0, 1.2          # bezel inner edge = cavity (bezel 10 pt sides, 7 top, 5 bottom)
CAV_Z = -4.4                                              # cavity back wall
SLANT_IN = 1.55                                           # slanted inner walls: back rectangle inset (units)
DISP = dict(x=0.05, y=16.3, z=-2.0, R=3.3, r_in=1.9, h=1.15, tilt=-20)


def _rr2(hx, y0, y1, r, cx=0.0):
    return rect2(hx, (y1 - y0) / 2, round=r).translate(cx, (y0 + y1) / 2)


def machine():
    parts = []
    blue = gloss("ma_blue", "#2388F0", rough=0.25, ior=1.42)
    frame2 = _rr2(MA_HX, MA_Y0, MA_Y1, MA_R)
    open2 = _rr2(OP_HX, OP_Y0, OP_Y1, OP_R)
    # front frame ring (a soft pillow edge)
    ring = extrude(frame2.subtract(open2), 0.6, round=0.55).translate(0, 0, 0.5)
    # housing below the window, filleted into the frame (concave fillets at the frame's bottom corners)
    hous2 = _rr2(6.6, 0.0, 6.6, 1.7)
    hous = extrude(hous2, 0.85, round=0.55).translate(0, 0, 0.25)
    rec = extrude(_rr2(5.35, 0.42, 4.3, 1.55, cx=0.17), 0.5, round=0.3).translate(0, 0, 1.3)
    hous = hous.subtract(rec, k=0.12)
    body = ring.smooth_union(hous, k=1.1)
    parts.append(Part("frame", body, blue, voxel=0.035))
    # the recess floor (darker blue) behind the plate
    parts.append(Part("recess", extrude(_rr2(5.3, 0.45, 4.27, 1.5, cx=0.17), 0.1).translate(0, 0, 0.62),
                      satin("ma_recess", "#0F57C4", rough=0.4), voxel=0.03))
    # the glass-blue bezel between the opening and the cavity
    # a sloped glass-blue ring: its outer edge high (under the frame lip), falling toward the cavity
    inner2 = _rr2(IN_HX, IN_Y0, IN_Y1, IN_R)
    bez = extrude(open2.offset(0.1).subtract(inner2), 0.3, round=0.28).translate(0, 0, 0.25)
    parts.append(Part("bezel", bez, gloss("ma_bezel", "#98DCFA", rough=0.16, ior=1.45), voxel=0.03))
    # cavity: a box shell open at the front
    outer = extrude(_rr2(IN_HX + 0.6, IN_Y0 - 0.6, IN_Y1 + 0.6, IN_R + 0.5), (0.3 - CAV_Z) / 2 + 0.3).translate(
        0, 0, (0.3 + CAV_Z) / 2 - 0.3)
    cav = extrude(_rr2(IN_HX, IN_Y0, IN_Y1, IN_R), 3.0).translate(0, 0, CAV_Z + 3.0)
    shell = outer.subtract(cav)
    cut = CAV_Z + 0.12
    sides = shell.intersect(box(20, 20, 5, center=(0, 12, cut + 5)))
    back = shell.intersect(box(20, 20, 5, center=(0, 12, cut - 5)))
    parts.append(Part("cavitySides", sides, satin("ma_cavside", "#5AB0F0", rough=0.35, ior=1.3), voxel=0.04))
    # director round 2: 002 shows a THICK slanted light-cyan inner wall (~24 pt on the sides, ~22 pt at the top) between
    # the frame and the dark back wall; round 1's straight cavity walls were edge-on (a thin light ring). Three slanted
    # panels taper the cavity from the opening (IN) to a smaller back rectangle (inset SLANT_IN units).
    L = 0.2 - CAV_Z
    ang = math.degrees(math.atan2(SLANT_IN, L))
    ln = math.hypot(SLANT_IN, L) / 2
    hy = (IN_Y1 - IN_Y0) / 2
    zc = (0.2 + CAV_Z) / 2
    left = box(0.07, hy, ln, round=0.03).rotate_y(-ang).translate(-IN_HX + SLANT_IN / 2, (IN_Y0 + IN_Y1) / 2, zc)
    right = box(0.07, hy, ln, round=0.03).rotate_y(ang).translate(IN_HX - SLANT_IN / 2, (IN_Y0 + IN_Y1) / 2, zc)
    top = box(IN_HX, 0.07, ln, round=0.03).rotate_x(-ang).translate(0, IN_Y1 - SLANT_IN / 2, zc)
    parts.append(Part("slant", left.union(right).union(top),
                      gloss("ma_slant", "#8FD9F9", rough=0.22, ior=1.38), voxel=0.035))
    parts.append(Part("cavityBack", back, satin("ma_cavity", "#1F6EDC", rough=0.45, ior=1.25), voxel=0.04))
    # hatch on the cavity floor: two lighter panel outlines
    for cx in (-3.4, 3.4):
        rim = box(3.15, 0.035, 1.6, round=0.02, center=(cx, IN_Y0, -2.2)).subtract(
            box(3.0, 0.2, 1.45, center=(cx, IN_Y0, -2.2)))
        parts.append(Part(f"hatch{int(cx > 0)}", rim, satin("ma_hatch", "#5EB4F3", rough=0.4), voxel=0.012))
    parts += dispenser()
    return parts, 0.04


def dispenser(hold=False):
    """A fat lilac-grey lamp ring hanging under the cavity ceiling, tipped toward the viewer so its glowing cyan
    opening shows underneath (002: 65 x ~24 pt, glow ellipse under it)."""
    d = DISP
    pts = [(d["r_in"], -d["h"]), (d["R"] - 0.55, -d["h"]), (d["R"] - 0.08, -d["h"] + 0.4), (d["R"], 0.0),
           (d["R"] - 0.08, d["h"] - 0.4), (d["R"] - 0.55, d["h"]), (d["r_in"] + 0.3, d["h"]), (d["r_in"], d["h"] - 0.3)]
    ring = revolve(rounded_polygon2(pts, 0.25, n_arc=8))
    stem = cylinder(d["R"] - 1.0, 0.9, center=(0, d["h"] + 0.7, 0))
    body = ring.union(stem).rotate_x(d["tilt"]).translate(d["x"], d["y"], d["z"])
    parts = [Part("dispRing", body, gloss("ma_disp", "#BAC3E6", rough=0.2, ior=1.45), voxel=0.025)]
    if not hold:
        from dataclasses import replace
        glow = cylinder(d["r_in"] + 0.02, 0.12, center=(0, -d["h"] + 0.25, 0)).rotate_x(d["tilt"]).translate(d["x"], d["y"], d["z"])
        m = replace(mat("ma_glow", "#A8F4FF", rough=0.5), emissive="#4FD2FF")
        parts.append(Part("dispGlow", glow, m, voxel=0.02))
    return parts


def dispenser_hold():
    return dispenser(hold=True), 0.03


# ---------------------------------------------------------------------- glossy arrows for the pile
# Pile colours measured on 002's window (dark / mid / light pixels per hue): lilac #A55CCB/#D272EA, sky #0D97D6/#40C9F9,
# green #3EB502/#90E739, yellow #F0A822/#FEC402, orange #E16922/#FB9603. Per colour: face, lower-bevel shade, rim,
# upper-bevel highlight (the arrows3d painted-bevel method, our own copy with the pile's colours).
PILE_SHADES = {"lilac": ("#CF79EC", "#A558CC", "#7E3AAE", "#E7AAF8"),
               "sky": ("#35BCF6", "#0E8ED6", "#0A66B6", "#8ADFFB"),
               "green": ("#8BDF36", "#4FB812", "#2F8C08", "#BDF27E"),
               "yellow": ("#FEC205", "#F39D14", "#D9800E", "#FFE06A"),
               "orange": ("#FB8B0E", "#E4651A", "#B8480E", "#FFB35A")}


def _arrow2d():
    # director round 2: the chunky BLOCK arrow of 002's pile (3d-hud's 026 measurement: head length 0.58, shaft width
    # 0.54, shaft length 0.54 of the head width); round 1 used a longer, thinner shaft that read as a different arrow
    from arrows3d import arrow2d
    return arrow2d(shaft=0.54, t=0.27, hl=0.58)


def _pile_bevel(s2, lo, size, color, band, shades=None):
    face, shade, rim, hi = (rgb(c) for c in (shades or PILE_SHADES[color]))
    down = np.array([0.30, -1.0]); down /= np.linalg.norm(down)

    def fn(u, v):
        H, W = u.shape
        p = np.stack([lo[0] + u * size, lo[1] + v * size], -1).reshape(-1, 2).astype(np.float32)
        d = s2.fn(p).astype(np.float64)
        e = size / W
        gx = (s2.fn(p + np.array([e, 0], np.float32)) - s2.fn(p - np.array([e, 0], np.float32))) / (2 * e)
        gy = (s2.fn(p + np.array([0, e], np.float32)) - s2.fn(p - np.array([0, e], np.float32))) / (2 * e)
        g = np.stack([gx, gy], 1); g /= np.maximum(np.linalg.norm(g, axis=1, keepdims=True), 1e-6)
        facing = g @ down
        t = np.clip((d + band) / band, 0, 1); t = t * t * (3 - 2 * t)
        w_sh = t * np.clip(facing * 1.6 + 0.35, 0, 1)
        w_rim = np.clip((d + 0.25 * band) / (0.25 * band), 0, 1) * np.clip(facing * 1.6, 0, 1)
        w_hi = t * np.clip(-facing * 1.4 - 0.2, 0, 1) * 0.8
        col = face[None] * (1 - w_sh[:, None]) + shade[None] * w_sh[:, None]
        col = col * (1 - w_rim[:, None]) + rim[None] * w_rim[:, None]
        col = col * (1 - w_hi[:, None]) + hi[None] * w_hi[:, None]
        return col.reshape(H, W, 3)
    return fn


ARROW_SCALE = 4.5    # head width in units (~33 pt: 002's pile arrows are 32-35 pt across the head, 40-46 pt long)


def pile_arrow(color):
    from dataclasses import replace
    s2 = _arrow2d()
    lo2, hi2 = s2.lo, s2.hi
    c = (lo2 + hi2) / 2
    s2c = s2.translate(-c[0], -c[1])
    body = extrude(s2c, 0.16, round=0.12).scale(ARROW_SCALE)
    lo = (float(s2c.lo[0]) - 0.05, float(s2c.lo[1]) - 0.05)
    size = float(max(s2c.hi - s2c.lo)) + 0.1
    m = gloss(f"pa_{color}", PILE_SHADES[color][0], rough=0.28, ior=1.42)
    m = replace(m, texture=_pile_bevel(s2c, lo, size, color, band=0.12), texture_size=512)
    uv = ("planar", (lo[0] * ARROW_SCALE, lo[1] * ARROW_SCALE, 0.0), (1, 0, 0), (0, 1, 0), 1.0 / (size * ARROW_SCALE))
    return [Part("arrow", body, m, uv=uv)], 0.02


for _c in PILE_SHADES:
    globals()[f"pile_arrow_{_c}"] = (lambda c=_c: pile_arrow(c))

PILE_COLORS = list(PILE_SHADES)


# pile colour mix, weighted like 002's heap (lilac and sky most, lime least)
PILE_MIX = ["lilac"] * 6 + ["sky"] * 5 + ["yellow"] * 5 + ["orange"] * 4 + ["green"] * 4


def pile_layout(kind, seed=11):
    """Deterministic heap (director round 2, from 002 / 168 / 070 at 6 px/pt). 002's full heap is a WIDE, LOW, nearly
    flat-topped mound that fills the window from wall to wall (x 117..272 pt, top y ~425-440, resting on the window
    floor at y ~510) and nearly every arrow lies with its face toward the camera, rotated in its own plane, its lower
    wall showing. Round 1 peaked in the middle with arrows on edge and spilled out of the window: the rows below fill
    the cavity width in four depth rows (back rows higher), and the build holds out the machine so nothing crosses the
    bezel. kind: full; half (168: a lower heap + a falling column under the dispenser); low (070: ~6 arrows lying on
    the window floor + one emerging from the dispenser, its shaft showing)."""
    rng = np.random.default_rng({"full": seed, "half": seed + 1, "low": seed + 2}[kind])
    y0 = IN_Y0 + 0.15
    pts = []          # (x, y, z, pitch range)
    if kind == "full":
        rows = [(-3.7, 5.0, (-3.9, -0.5, 2.9, 5.9)),
                (-2.9, 4.2, (-5.6, -2.1, 1.3, 4.6)),
                (-2.05, 2.8, (-5.2, -1.6, 1.9, 5.5)),
                (-1.25, 1.35, (-5.4, -2.0, 1.6, 5.2))]      # front row at -1.25: a tipped arrow stays behind the bezel
        for z, dy, xs in rows:
            for x in xs:
                x = x + rng.uniform(-0.45, 0.45)
                side = max(0.0, -x - 4.4) * 1.0 + max(0.0, x - 5.8) * 0.8   # 002: flat from x 145 to 262 pt, rounded at the left wall            # the mound falls off a little at the walls
                pts.append((x, y0 + dy - side + rng.uniform(-0.3, 0.3), z + rng.uniform(-0.25, 0.25), (-34, -14)))
    elif kind == "half":
        rows = [(-3.0, 2.7, (-4.6, 1.6, 5.4)),
                (-2.1, 1.9, (-5.6, -1.9, 2.6, 5.9)),
                (-1.25, 0.95, (-4.8, -1.2, 2.2, 5.3))]
        for z, dy, xs in rows:
            for x in xs:
                x = x + rng.uniform(-0.4, 0.4)
                side = max(0.0, abs(x) - 4.8) * 0.5
                pts.append((x, y0 + dy - side + rng.uniform(-0.3, 0.3), z + rng.uniform(-0.2, 0.2), (-44, -18)))
    else:
        # 070: five arrows standing on the window floor, clustered centre-left to right, tipped back ~30 deg
        for x, y, z in ((-4.2, 1.1, -1.6), (-0.4, 1.3, -2.4), (0.9, 1.0, -1.3), (3.1, 1.25, -2.2), (4.3, 0.95, -1.3)):
            pts.append((x + rng.uniform(-0.25, 0.25), y0 + y, z, (-40, -24)))
    cols = list(PILE_MIX)
    rng.shuffle(cols)
    cols = (cols * 3)[:len(pts) + 6]
    res = []
    for i, (x, y, z, (p0, p1)) in enumerate(pts):
        roll = float(rng.uniform(0, 360))
        if kind == "full" and 55 < roll < 125:      # 002's heap has few arrows pointing straight up at its top
            roll += 75
        pitch = float(rng.uniform(p0, p1))
        yaw = float(rng.uniform(-14, 14))
        res.append((cols[i], dict(pos=(x, y, z), R=(rot_y(yaw) @ rot_x(pitch) @ rot_z(roll)).tolist())))
    d = DISP
    k = len(pts)
    if kind == "half":
        # 168: a falling column under the dispenser, two arrows (orange over sky), pointing down-ish
        for j, (dy, rl, c) in enumerate(((-2.5, -100, "orange"), (-4.7, -75, "sky"))):
            res.append((c, dict(pos=(d["x"] + 0.3 * j - 0.1, d["y"] + dy, d["z"] + 0.5),
                                R=(rot_x(-12) @ rot_z(rl)).tolist())))
        res.append(("lilac", dict(pos=(d["x"], d["y"] - 0.95, d["z"] + 0.1), R=(rot_x(-8) @ rot_z(-90)).tolist())))
    if kind == "low":
        # 070: one arrow half out of the dispenser, pointing down, its shaft still inside the ring
        res.append(("green", dict(pos=(d["x"], d["y"] - 1.35, d["z"] + 0.1), R=(rot_x(-8) @ rot_z(90)).tolist())))
    return res


def machine_hold():
    """The machine without its glow disc: the pile's holdout, so the heap is clipped by the frame and bezel exactly as
    the window shows it (round 1 had no holdout for the full heap and it spilled ~20 pt onto the bezel)."""
    parts, v = machine()
    return [p for p in parts if p.name != "dispGlow"], v


# ====================================================================== backdrop objects (wall-mounted, 3D)
# Registered to the screen: world X = sx / 10, Y = -sy / 10 (sx, sy in pt on the 393 x 852 screen), Z toward the viewer
# with the wall at Z = 0. Rendered together in ONE sprite whose bounds are the screen rectangle, so every object lands
# at its measured position; 2D shadows are added in the composite. Measurements on 002 (gridded crops, pt):
#   P1 left striped pipe  x 40..62 (r 11), stripes from the top to ~y 180, blue below, bends into a wall socket y ~222
#   P2 left blue pipe     x 80..108 (r 14), grey collar y 0..15, orange collar y 122..134, purple elbow into a round
#                         flange centred (100, 165) r ~24
#   P3 right pipe         x 330..355 (r 12.5), purple valve wheel (340, 18) r 22, grey section y 28..58, blue, orange
#                         collar 124..137, striped 137..198, orange collar 198..206, U-bend (bottom y ~226), left leg x 301
#                         up to y ~104 where it turns into a flange (296, 104)
#   P4 right-mid pipe     purple from the right edge at y ~284 (r 14) to x 362, a dark joint, a copper bell 322..358
#                         into a flange (333, 296) r ~22
#   vents (247, 190) and (58, 432) r 17; indicator lamps green (308, 440), red (308, 458) r 6.5
#   railings on the deck rim: tube y ~333 (r 4) from the screen edge to x 75 / 318 where it bends down to the rim,
#   a T-post at x 35 / 358 with grey sleeves

def W(sx, sy, z=0.0):
    return (sx / 10.0, -sy / 10.0, z)


def _open_fillet(pts, r, n=10):
    """Round the interior corners of an open 3D polyline with radius r (units)."""
    P = [np.asarray(p, float) for p in pts]
    out = [P[0]]
    for i in range(1, len(P) - 1):
        a, b, c = P[i - 1], P[i], P[i + 1]
        u = (a - b) / np.linalg.norm(a - b)
        w = (c - b) / np.linalg.norm(c - b)
        ang = math.acos(float(np.clip(u @ w, -1, 1)))
        if ang > math.pi - 1e-3:
            out.append(b)
            continue
        t = r / math.tan(ang / 2)
        t = min(t, 0.49 * np.linalg.norm(a - b), 0.49 * np.linalg.norm(c - b))
        p0, p1 = b + u * t, b + w * t
        for k in range(n + 1):
            s = k / n
            q = (1 - s) ** 2 * p0 + 2 * (1 - s) * s * b + s * s * p1   # quadratic Bezier (close to an arc)
            out.append(q)
    out.append(P[-1])
    return out


def tube(pts, r, bend=None):
    pts = _open_fillet(pts, bend if bend is not None else r * 1.6)
    return path_tube(pts, [r] * len(pts))


def _stripe_tex(c1="#8A5EDB", c2="#E2DAF6", starts=2, duty=0.6):
    def fn(u, v):
        t = (u * starts + v) % 1.0
        # soft edges (anti-aliased stripes)
        e = 0.02
        m = np.clip((t - 0.0) / e, 0, 1) * np.clip((duty - t) / e, 0, 1)
        m = np.maximum(m, 0)
        return rgb(c1)[None, None] * m[..., None] + rgb(c2)[None, None] * (1 - m[..., None])
    return fn


def striped_cyl(name, sx, sy0, sy1, r_pt, z, period_pt=17.0):
    from dataclasses import replace
    x, y0, y1 = sx / 10, -sy0 / 10, -sy1 / 10
    c = cylinder(r_pt / 10, abs(y0 - y1) / 2, center=(x, (y0 + y1) / 2, z))
    m = replace(gloss(f"{name}_mat", "#8A5EDB", rough=0.3, ior=1.4), texture=_stripe_tex(), texture_size=512)
    uv = ("cyl", (x, y1, z), (0, 1, 0), 10.0 / period_pt)
    return Part(name, c, m, uv=uv, voxel=0.03)


def collar(name, sx, sy, r_pt, h_pt, z, color, axis="y"):
    c = cylinder(r_pt / 10, h_pt / 20, round=min(0.12, h_pt / 50), center=(0, 0, 0))
    if axis == "x":
        c = c.rotate_z(90)
    return Part(name, c.translate(sx / 10, -sy / 10, z), gloss(f"col_{color}", color, rough=0.28, ior=1.42), voxel=0.025)


def flange(name, sx, sy, r_pt, color="#7A78CC", socket="#3C3A8E"):
    """A round wall plate with a dark socket where a pipe enters the wall."""
    plate = cylinder(r_pt / 10, 0.12, round=0.1).rotate_x(90).translate(sx / 10, -sy / 10, 0.12)
    return [Part(name, plate, satin(f"fl_{name}", color, rough=0.35, ior=1.3), voxel=0.03)]


BLUE_PIPE = "#3D86E8"
PURPLE_PIPE = "#7F57D9"
ORANGE = "#EE9030"
GREY_COLLAR = "#98A1C8"


def pipes_left():
    parts = []
    z1 = 1.25
    # P1: stripes down to 180, orange joint, blue down to 214, then into the wall
    parts.append(striped_cyl("p1stripe", 51, -8, 182, 11, z1))
    parts.append(collar("p1col", 51, 185, 12.5, 7, z1, ORANGE))
    p1 = tube([W(51, 186, z1), W(51, 214, z1), W(51, 222, -0.4)], 1.1, bend=1.2)
    parts.append(Part("p1blue", p1, gloss("pipe_blue", BLUE_PIPE, rough=0.26, ior=1.42), voxel=0.03))
    parts += flange("p1fl", 51, 222, 17)
    # P2: blue from the top to 122, grey collar at the top, orange collar, purple elbow into its flange
    z2 = 1.6
    p2 = tube([W(94, -8, z2), W(94, 124, z2)], 1.4)
    parts.append(Part("p2blue", p2, gloss("pipe_blue", BLUE_PIPE, rough=0.26, ior=1.42), voxel=0.03))
    parts.append(collar("p2grey", 94, 6, 15.5, 16, z2, GREY_COLLAR))
    parts.append(collar("p2ring", 94, -3, 16.5, 6, z2, "#2E7BE0"))
    parts.append(collar("p2col", 94, 128, 16.2, 12, z2, ORANGE))
    p2e = tube([W(94, 132, z2), W(94, 160, z2), W(100, 168, -0.2)], 1.45, bend=1.5)
    parts.append(Part("p2purple", p2e, gloss("pipe_purple", PURPLE_PIPE, rough=0.26, ior=1.42), voxel=0.03))
    parts += flange("p2fl", 100, 166, 24)
    return parts, 0.03


def pipes_right():
    parts = []
    z3 = 1.35
    # valve wheel in front of the pipe top
    vx, vy, vz = 340, 18, 2.9
    wheel = torus(1.9, 0.33).rotate_x(90)
    for a in (90, 210, 330):
        ca, sa = math.cos(math.radians(a)), math.sin(math.radians(a))
        wheel = wheel.union(capsule((0, 0, 0), (1.9 * ca, 1.9 * sa, 0), 0.24))
    wheel = wheel.union(cylinder(0.55, 0.3, round=0.2).rotate_x(90))
    parts.append(Part("valve", wheel.translate(vx / 10, -vy / 10, vz), gloss("valve", "#8C63DA", rough=0.25, ior=1.42), voxel=0.025))
    parts.append(Part("valveStem", cylinder(0.3, 0.8).rotate_x(90).translate(vx / 10, -vy / 10, vz - 0.9),
                      satin("valveStem", "#6A5BB8"), voxel=0.03))
    # the pipe: grey upper section, blue, orange collar, stripes, orange collar
    parts.append(Part("p3grey", cylinder(1.35, 1.85, round=0.1, center=(34.2, -4.3, z3)),
                      satin("p3grey", "#8D96C0", rough=0.33), voxel=0.03))
    p3 = tube([W(342, 52, z3), W(342, 128, z3)], 1.25)
    parts.append(Part("p3blue", p3, gloss("pipe_blue", BLUE_PIPE, rough=0.26, ior=1.42), voxel=0.03))
    parts.append(collar("p3col1", 342, 130.5, 14.5, 12, z3, ORANGE))
    parts.append(striped_cyl("p3stripe", 342, 136, 198, 12.5, z3))
    parts.append(collar("p3col2", 342, 201, 14.5, 8, z3, ORANGE))
    # U-bend and the left leg up into a flange
    u = tube([W(342, 203, z3), W(342, 226, z3), W(301, 226, z3), W(301, 106, z3), W(296, 100, -0.3)], 1.15, bend=2.0)
    parts.append(Part("p3u", u, gloss("pipe_blue", BLUE_PIPE, rough=0.26, ior=1.42), voxel=0.03))
    parts += flange("p3fl", 296, 101, 15)
    # P4: purple from the right edge into a copper bell and its flange
    z4 = 1.5
    p4 = tube([W(405, 283, z4), W(362, 285, z4)], 1.45)
    parts.append(Part("p4purple", p4, gloss("pipe_purple", PURPLE_PIPE, rough=0.26, ior=1.42), voxel=0.03))
    parts.append(collar("p4joint", 360, 285, 16.5, 7, z4, "#5B3FAF", axis="x"))
    bell = tube([W(357, 286, z4), W(340, 289, z4), W(335, 295, -0.2)], 1.45, bend=1.5)
    parts.append(Part("p4copper", bell, gloss("copper", "#A98579", rough=0.34, ior=1.36), voxel=0.03))
    parts += flange("p4fl", 333, 296, 22)
    return parts, 0.03


def vent_model():
    """A round grille: a light blue torus rim, four horizontal slats over a dark recess (r = 1.7 units = 17 pt)."""
    parts = []
    rim = torus(1.45, 0.3).rotate_x(90).translate(0, 0, 0.3)
    plate = cylinder(1.72, 0.12, round=0.1).rotate_x(90).translate(0, 0, 0.1)
    parts.append(Part("ventRim", rim.union(plate), gloss("vent_rim", "#A9C4EE", rough=0.26, ior=1.4), voxel=0.02))
    parts.append(Part("ventHole", cylinder(1.3, 0.05).rotate_x(90).translate(0, 0, 0.22),
                      satin("vent_hole", "#5A6FB8", rough=0.5), voxel=0.02))
    slats = union(*[capsule((-1.25 * math.sqrt(max(0.05, 1 - (yy / 1.3) ** 2)), yy, 0.36),
                            (1.25 * math.sqrt(max(0.05, 1 - (yy / 1.3) ** 2)), yy, 0.36), 0.14)
                    for yy in (-0.78, -0.26, 0.26, 0.78)])
    parts.append(Part("ventSlats", slats, gloss("vent_slat", "#B3CBF1", rough=0.3, ior=1.4), voxel=0.015))
    return parts, 0.02


def lamps():
    from dataclasses import replace
    parts = []
    for name, sy, col, em in (("lampG", 440, "#35C83A", "#0B5A10"), ("lampR", 458, "#EA2D3C", "#5A0A10")):
        base = cylinder(0.72, 0.1, round=0.08).rotate_x(90).translate(30.8, -sy / 10, 0.1)
        parts.append(Part(name + "Base", base, satin("lamp_base", "#C9B6AE", rough=0.4), voxel=0.015))
        dome = sphere(0.62, center=(30.8, -sy / 10, 0.05))
        parts.append(Part(name, dome, replace(gloss(name, col, rough=0.18, ior=1.48), emissive=em), voxel=0.012))
    return parts, 0.015


def railings():
    parts = []
    blue = gloss("rail_blue", "#2F92F0", rough=0.24, ior=1.42)
    grey = gloss("rail_grey", "#C7D1EA", rough=0.25, ior=1.4)
    z = 2.2
    for side in (-1, 1):
        def X(sx):
            return sx if side < 0 else 393 - sx
        tub = tube([W(X(-10), 333, z), W(X(66), 333, z), W(X(78), 350, z)], 0.42, bend=1.1)
        parts.append(Part(f"rail{side}", tub, blue, voxel=0.02))
        post = capsule(W(X(35), 334, z), W(X(35), 348, z), 0.34)
        parts.append(Part(f"post{side}", post, blue, voxel=0.02))
        parts.append(Part(f"sleeve{side}", cylinder(0.62, 0.42, round=0.2, center=W(X(35), 334, z)).rotate_z(0) if False else
                          cylinder(0.62, 0.42, round=0.2).rotate_z(90).translate(*W(X(35), 333.5, z)), grey, voxel=0.015))
        parts.append(Part(f"foot{side}", cylinder(0.72, 0.18, round=0.12, center=W(X(35), 348.5, z)), grey, voxel=0.015))
        parts.append(Part(f"foot2{side}", cylinder(0.72, 0.18, round=0.12, center=W(X(78), 350.5, z)), grey, voxel=0.015))
    return parts, 0.02


MODELS = {"platform": platform, "console": console, "machine": machine, "dispenser_hold": dispenser_hold,
          "machine_hold": machine_hold,
          "pipes_left": pipes_left, "pipes_right": pipes_right, "vent": vent_model, "lamps": lamps, "railings": railings}
MODELS.update({f"pile_arrow_{c}": globals()[f"pile_arrow_{c}"] for c in PILE_SHADES})


# ====================================================================== builds (manifest id -> image at frame x 3)
import sys as _sys  # noqa: E402
from scene_kit import Canvas, fit_box, rig, shadow_of  # noqa: E402

_M = _sys.modules[__name__]

# frames (screen pt, x0 y0 x1 y1) -- measured on 002; see art/lanes/scene.md for the proposed manifest sizes
F_CONSOLE = (95, 266, 309, 375)
F_PLATFORM = (0, 576, 393, 758)


def _local(box, frame):
    return (box[0] - frame[0], box[1] - frame[1], box[2] - frame[0], box[3] - frame[1])


def build_console(ctx):
    ims = ctx.render({"console": dict(scene=[(_M, "console", dict(pitch=16))], fov=14, px=1500, light=rig(shadow=False))})
    cv = Canvas(F_CONSOLE[2] - F_CONSOLE[0], F_CONSOLE[3] - F_CONSOLE[1])
    # director round 2: fitted by WIDTH to 002's rim span (the rim x 100..293 pt = the render's widest row), bottom
    # of the base at y 373
    spr, (x, y) = fit_box(ims["console"], _local((99.0, 262.0, 294.0, 373.0), F_CONSOLE), mode="width", align=(0.5, 1.0))
    cv.over(spr, x=x, y=y)
    return cv.image()


def build_platform(ctx):
    ims = ctx.render({"platform": dict(scene=[(_M, "platform", dict(pitch=21.5))], fov=10, px=1800, light=rig())})
    cv = Canvas(F_PLATFORM[2] - F_PLATFORM[0], F_PLATFORM[3] - F_PLATFORM[1])
    spr, (x, y) = fit_box(grade(ims["platform"], gain=(1.0, 1.0, 0.97), lift=(0.07, 0.065, 0.04), sat=0.95),
                          _local((-9, 583.5, 402, 751), F_PLATFORM), mode="stretch")
    cv.over(spr, x=x, y=y)
    # the workers' soft contact shadows (002: a violet-blue pool under each worker's feet); the workers stand still on
    # the home screen (placement_pt feet anchors in their rig.json), so the shadows are baked here
    X, Y = cv.X + F_PLATFORM[0], cv.Y + F_PLATFORM[1]
    for fx, fy in ((79.1, 613.2), (315.9, 612.9)):
        g = np.exp(-(((X - fx) / 30.0) ** 2 + ((Y - fy - 1.5) / 7.0) ** 2) * 1.4)
        core = np.exp(-(((X - fx) / 18.0) ** 2 + ((Y - fy - 1.0) / 4.0) ** 2) * 1.6)
        cv.multiply(np.clip(g * 0.7 + core * 0.45, 0, 1), "#3E3F9A", 0.85)
    return cv.image()


BUILDS = {"homeConsole": build_console, "homePlatform": build_platform}


# ---------------------------------------------------------------------- machine + pile builds (registered renders)
import json as _json  # noqa: E402
import os as _os  # noqa: E402
from scene_kit import BUILD as _BUILD, alpha_bbox, scene_bounds  # noqa: E402
from PIL import Image as _Image  # noqa: E402

F_MACHINE = (95, 365, 301, 580)
F_PILE = (104, 402, 290, 528)
MACH_BOX = (100.0, 381.3, 290.0, 576.8)          # the machine's silhouette on 002
MACH_VIEW = (0, 11.0)                             # camera looks down 11 deg: the cavity floor + hatch show (070)
MACH_LIGHT = dict(key_lux=2200.0, fill_lux=800.0, shadow=False)


def _machine_spec():
    return dict(scene=[(_M, "machine", dict(center=False))], view=MACH_VIEW, fov=12, px=1500, light=rig(**MACH_LIGHT))


def _map_path(ctx):
    return _os.path.join(_BUILD, f"machine_map{'_draft' if ctx.draft else ''}.json")


def _paste_mapped(im, bb, frame):
    """Map the raw render's machine bbox `bb` (px) onto MACH_BOX (pt) and return the part inside `frame` (pt)."""
    x0, y0, x1, y1 = MACH_BOX
    sx = (x1 - x0) * 3 / (bb[2] - bb[0])
    sy = (y1 - y0) * 3 / (bb[3] - bb[1])
    W, H = im.size
    big = im.resize((max(1, round(W * sx)), max(1, round(H * sy))), _Image.LANCZOS)
    ox = round(x0 * 3 - bb[0] * sx - frame[0] * 3)
    oy = round(y0 * 3 - bb[1] * sy - frame[1] * 3)
    cv = Canvas(frame[2] - frame[0], frame[3] - frame[1])
    cv.over(big, x=ox, y=oy)
    return cv.image()


def build_machine(ctx):
    spec = _machine_spec()
    ims = ctx.render({"machine": spec})
    im = ims["machine"]
    bb = alpha_bbox(im)
    _json.dump(dict(bb=bb, bounds=im.info["cam"]["bounds"], size=im.size), open(_map_path(ctx), "w"))
    out = _paste_mapped(im, bb, F_MACHINE)
    # glass sheen: two soft highlights in the window's upper corners (002: a bright blob top-left, a smaller one
    # top-right) -- painted, the renderer has no glass pane here
    cv = Canvas(F_MACHINE[2] - F_MACHINE[0], F_MACHINE[3] - F_MACHINE[1])
    cv.over(out)
    X, Y = cv.X + F_MACHINE[0], cv.Y + F_MACHINE[1]
    for cx, cy, rx, ry, a in ((126, 402, 9, 6, 0.55), (265, 400, 6, 4, 0.35)):
        g = np.exp(-(((X - cx) / rx) ** 2 + ((Y - cy) / ry) ** 2) * 1.6)
        cv.screen(g, "#E8F7FF", a)
    return cv.image()


def _pile_build(kind):
    def fn(ctx):
        mp = _map_path(ctx)
        if not _os.path.exists(mp):
            build_machine(ctx)
        info = _json.load(open(mp))
        spec = _machine_spec()
        items = [(_M, f"pile_arrow_{c}", pose) for c, pose in pile_layout(kind)]
        pspec = dict(scene=items, view=MACH_VIEW, fov=12, px=spec["px"], bounds=info["bounds"],
                     aspect=info["size"][0] / info["size"][1], light=rig(**dict(MACH_LIGHT, shadow=True)))
        pspec["holdout"] = [(_M, "machine_hold", dict(center=False))]
        ims = ctx.render({f"pile_{kind}": pspec})
        im = ims[f"pile_{kind}"]
        assert im.size == tuple(info["size"]), (im.size, info["size"])
        return _paste_mapped(im, info["bb"], F_PILE)
    return fn


BUILDS.update({"homeCapsuleMachine": build_machine, "homeArrowPileFull": _pile_build("full"),
               "homeArrowPileHalf": _pile_build("half"), "homeArrowPileLow": _pile_build("low")})


# ---------------------------------------------------------------------- the backdrop: painted structure + objects
from scene_kit import (aa, blur, d_ellipse, noise2, smooth, stops_interp, grade, sprite_array)  # noqa: E402


def ledge_y(x):
    """The tank's bottom lip (top edge): 233 at the screen sides, bowing down ~15 pt at the centre."""
    return 233.0 + 15.0 * (1 - ((x - 196.5) / 196.5) ** 2)


def rim_y(x):
    """The deck rim (top edge): 350 at the sides, 362 at the centre."""
    return 350.0 + 12.0 * (1 - ((x - 196.5) / 196.5) ** 2)


CREAM_BOTTOM = 478.0
FLOOR_Y = 575.0


def paint_backdrop():
    cv = Canvas(393, 852, color="#6F6CB8")
    X, Y = cv.X, cv.Y
    h, w = cv.h, cv.w
    col = np.zeros((h, w, 3))
    # --- tank wall: horizontal cylinder shading, bright blue glow down the middle, dark violet right edge
    top_row = stops_interp(X, [(0, "#5C55A0"), (18, "#6C66AE"), (70, "#7677BD"), (125, "#7883C3"), (160, "#6C92D4"),
                               (200, "#63A2DD"), (238, "#6E95D6"), (275, "#7488CB"), (322, "#6563B3"),
                               (360, "#48449A"), (393, "#2F2B7C")])
    low_row = stops_interp(X, [(0, "#5E5AA6"), (18, "#6F6BB6"), (70, "#7C80C6"), (125, "#7F8FCF"), (160, "#7EA9E2"),
                               (200, "#8BBDEA"), (238, "#80A6DF"), (275, "#7A90D2"), (322, "#6A6CBC"),
                               (360, "#4D4AA2"), (393, "#34307F")])
    t = smooth(Y, 20, 190)[..., None]
    tank = top_row * (1 - t) + low_row * t
    col[:] = tank
    # --- lower wall (under the ledge, down to the rim)
    lw = stops_interp(X, [(0, "#464690"), (60, "#474B96"), (140, "#4A509C"), (200, "#474E9A"), (280, "#3F4594"),
                          (340, "#373888"), (393, "#28236E")])
    ly = ledge_y(X)
    below = Y > ly + 9
    col[below] = lw[below]
    # --- cream wall
    ry = rim_y(X)
    cream = stops_interp(X, [(0, "#C7A99C"), (22, "#D6BCA9"), (75, "#EFDCC7"), (130, "#F2E2CF"), (200, "#EBDCCB"),
                             (270, "#E6D4C3"), (325, "#DCC8B8"), (365, "#C2AAA6"), (393, "#AE949A")])
    cm = (Y > ry + 10) & (Y <= CREAM_BOTTOM)
    col[cm] = cream[cm]
    # --- blue band
    blue_top = stops_interp(X, [(0, "#2C92F2"), (100, "#3398F2"), (200, "#3A9AEE"), (300, "#258AF0"), (393, "#1177EC")])
    blue_bot = stops_interp(X, [(0, "#1C7FE8"), (100, "#2284E6"), (200, "#2A88E2"), (300, "#1A7CE4"), (393, "#0C6BE0")])
    tb = smooth(Y, CREAM_BOTTOM, FLOOR_Y)[..., None]
    bm = (Y > CREAM_BOTTOM) & (Y <= FLOOR_Y)
    blue = blue_top * (1 - tb) + blue_bot * tb
    col[bm] = blue[bm]
    # --- floor: the wall's blue reflection near the base, then lilac, lighter toward the viewer
    fl = stops_interp(Y, [(575, "#5A6CB6"), (590, "#7485C8"), (615, "#A8B4E2"), (700, "#C1C6EA"), (852, "#D2CFEC")])
    side = (np.abs(X - 196.5) / 196.5) ** 2
    fl = fl * (1 - 0.12 * side[..., None]) + rgb("#9C98D2") * 0.12 * side[..., None]
    fm = Y > FLOOR_Y
    col[fm] = fl[fm]
    cv.a[..., :3] = col
    cv.a[..., 3] = 1.0

    # ---------------- details
    # tank: panel seams (vertical) and one horizontal seam with rivets near the top
    for sx in (12, 132, 193, 254, 315, 376):
        d = np.abs(X - sx)
        on = (Y < ly - 1)
        cv.multiply(aa(d - 0.5, 0.5) * on, "#3E3C92", 0.24)
        cv.screen(aa(np.abs(X - sx - 1.3) - 0.4, 0.5) * on, "#C9D4FF", 0.12)
    hs = aa(np.abs(Y - 33) - 0.5, 0.45) * (Y < ly)
    cv.multiply(hs, "#3E3C92", 0.32)
    cv.screen(aa(np.abs(Y - 34.3) - 0.4, 0.45), "#C9D4FF", 0.18)
    for rx in (5, 124, 262, 386):
        for ry_ in (27, 39):
            r = np.sqrt((X - rx) ** 2 + (Y - ry_) ** 2)
            cv.multiply(aa(np.sqrt((X - rx - 0.5) ** 2 + (Y - ry_ - 0.6) ** 2) - 1.9, 0.5), "#34307E", 0.35)
            cv.screen(aa(r - 1.6, 0.4), "#B7BCF2", 0.45)
    # soft ambient occlusion above the ledge + the ledge itself (a rounded lilac lip)
    ao = smooth(Y, ly - 16, ly) * (Y <= ly)
    cv.multiply(ao, "#4B479E", 0.35)
    lip = (Y > ly) & (Y <= ly + 9)
    lipcol = stops_interp(X, [(0, "#A3A1E2"), (120, "#B4B6EE"), (200, "#B3B8EE"), (300, "#8E8AD6"), (393, "#5E56AC")])
    tl = np.clip((Y - ly) / 9.0, 0, 1)
    shade = (1 - 0.18 * tl ** 1.5)[..., None]
    lipc = lipcol * shade
    cv.a[..., :3] = np.where(lip[..., None], lipc, cv.a[..., :3])
    cv.multiply(aa(np.abs(Y - ly) - 0.5, 0.5), "#3A3790", 0.55)          # dark line on top of the lip
    cv.screen(aa(np.abs(Y - ly - 1.8) - 0.6, 0.5), "#E4E6FF", 0.35)      # its highlight
    cv.multiply(aa(np.abs(Y - ly - 9.2) - 0.6, 0.6), "#262070", 0.5)      # the lip's lower edge
    # lower wall: AO under the lip, panel seams, rivets at the left
    cv.multiply(smooth(-(Y - ly - 9), -14, 0) * (Y > ly + 9) * (Y < ry), "#2A2670", 0.35)
    for sx in (128, 330):
        on = (Y > ly + 10) & (Y < ry)
        cv.multiply(aa(np.abs(X - sx) - 0.5, 0.45) * on, "#232062", 0.35)
        cv.screen(aa(np.abs(X - sx - 1.2) - 0.4, 0.45) * on, "#8D93E0", 0.18)
    for rx, ry_ in ((5, 252), (5, 306), (388, 262), (388, 318)):
        r = np.sqrt((X - rx) ** 2 + (Y - ry_) ** 2)
        cv.multiply(aa(np.sqrt((X - rx - 0.5) ** 2 + (Y - ry_ - 0.6) ** 2) - 2.0, 0.5), "#1E1A5C", 0.4)
        cv.screen(aa(r - 1.7, 0.4), "#8F95DD", 0.5)
    # deck rim: glossy blue bar, highlight on top, dark lower edge, shadow on the cream wall
    rb = ry + 11.0
    rimm = (Y > ry) & (Y <= rb)
    tr = np.clip((Y - ry) / 11.0, 0, 1)
    rimcol = stops_interp(tr, [(0, "#9AD3FB"), (0.12, "#64B6F8"), (0.45, "#45A3F4"), (0.8, "#2586E6"), (1.0, "#166CD6")])
    cv.a[..., :3] = np.where(rimm[..., None], rimcol, cv.a[..., :3])
    cv.multiply(aa(np.abs(Y - rb) - 0.6, 0.5), "#0B3E9E", 0.6)
    cv.multiply(smooth(-(Y - rb), -9, 0) * (Y > rb) * (Y < CREAM_BOTTOM), "#6F4F5E", 0.35)
    # cream wall: vertical panel seams, slight mottling
    for sx in (60, 340):
        on = (Y > rb) & (Y < CREAM_BOTTOM)
        cv.multiply(aa(np.abs(X - sx) - 0.6, 0.5) * on, "#8C6E68", 0.45)
        cv.screen(aa(np.abs(X - sx - 1.4) - 0.5, 0.5) * on, "#FFF6EA", 0.35)
    nz = noise2(h, w, 90, seed=3)
    cm2 = ((Y > rb) & (Y < CREAM_BOTTOM)).astype(float)
    cv.a[..., :3] *= (1 + 0.018 * nz * cm2)[..., None]
    # cream -> blue boundary: a light lip on the blue band's top edge and a shadow line
    cv.multiply(aa(np.abs(Y - CREAM_BOTTOM) - 0.7, 0.5), "#0A4CB4", 0.55)
    cv.screen(aa(np.abs(Y - CREAM_BOTTOM - 2.0) - 0.8, 0.6), "#9AD2FF", 0.55)
    cv.multiply(smooth(-(Y - CREAM_BOTTOM - 3), -10, 0) * (Y > CREAM_BOTTOM + 3) * (Y < FLOOR_Y), "#0D4CB0", 0.18)
    # blue band base: dark line where it meets the floor
    cv.multiply(aa(np.abs(Y - FLOOR_Y) - 0.8, 0.6), "#12307E", 0.55)
    cv.multiply(smooth(Y, FLOOR_Y - 12, FLOOR_Y) * (Y <= FLOOR_Y) * (Y > CREAM_BOTTOM), "#0F4AB0", 0.25)
    # overall vignette (the corners of the room fall off into violet)
    vx = ((X - 196.5) / 196.5) ** 2
    vy = ((Y - 380) / 470) ** 2
    cv.multiply(np.clip(vx * 0.5 + vy * 0.2, 0, 1), "#3A2C7A", 0.16)
    return cv


F_BACKDROP = (0, 0, 393, 852)


def _objects_spec(px):
    c = dict(center=False)
    return dict(scene=[(_M, "pipes_left", c), (_M, "pipes_right", c), (_M, "railings", c), (_M, "lamps", c),
                       (_M, "vent", dict(center=False, pos=W(247, 190, 0.0))),
                       (_M, "vent", dict(center=False, pos=W(58, 432, 0.0)))],
                bounds=((0.0, -85.2, -1.0), (39.3, 0.0, 3.6)), aspect=393 / 852, margin=1.0, fov=3.0, px=px,
                light=rig(key_lux=2000.0, fill_lux=650.0))


def build_backdrop(ctx):
    ims = ctx.render({"homeObjects": _objects_spec(2556 * 1.3)})
    obj = ims["homeObjects"].resize((1179, 2556), _Image.LANCZOS)
    cv = paint_backdrop()
    # the capsule machine's soft shadow on the cream wall / blue band (it stands against the wall; static)
    mp = _os.path.join(K_OUT, "homeCapsuleMachine@3x.png")
    if ctx.draft and _os.path.exists(_os.path.join(_BUILD, "draft", "homeCapsuleMachine.png")):
        mp = _os.path.join(_BUILD, "draft", "homeCapsuleMachine.png")
    if _os.path.exists(mp):
        mim = _Image.open(mp).convert("RGBA").resize(((F_MACHINE[2] - F_MACHINE[0]) * 3, (F_MACHINE[3] - F_MACHINE[1]) * 3))
        sh, (ox, oy) = shadow_of(mim, 6, 9, 14, 0.55, color="#3B2A6A", grow_px=6)
        cv.over(sh, x=F_MACHINE[0] * 3 + ox, y=F_MACHINE[1] * 3 + oy)
    # objects: soft shadows on the wall (light from the upper left front), then the objects
    sh, (ox, oy) = shadow_of(obj, 7, 8, 7, 0.42, color="#1F1760")
    cv.over(sh, x=ox, y=oy)
    cv.over(obj)
    return cv.image()


from scene_kit import OUT as K_OUT  # noqa: E402

BUILDS["homeBackdrop"] = build_backdrop
