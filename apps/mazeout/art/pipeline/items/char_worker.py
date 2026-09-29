"""The WORKERS: the original's capsule workers reproduced 1:1 as our own 3D models (SDF, smooth toy plastic), with
the body recoloured BLUE (OWNER DECISION 02:55; art/lanes/characters.md). Clothes and props keep the original's
colours (indigo shorts, brown leather belt, lilac-grey buckle + wrench, navy/green caps, black glasses) unless they
clash with the blue body (noted where adjusted).

Modelled from scratch from measurements of the captures (looked at only):
  002-home-L32 + store 7 (home): LEFT = navy cap + walkie-talkie + hand on hip (open laugh; 002 frame: eyes closed,
      leaning back, one foot kicked); RIGHT = green cap + big black square glasses + clipboard + pencil (half lids).
      Both stand ~115 pt tall (feet bottom y 1843 / 1837 px, body top ~1500 px); body ~190 px wide.
  store 8 / kickoff state.png (loading): the box carrier (arms up, gloves), the flyer holding a red arrow, the runner
      with glasses + notebook, background workers (top hat, burger).
  067 / 094 (avatars): party hat + red glasses, detective (deerstalker + moustache), burger, box carrier.

Body space: +Y up, feet bottom at y 0, +Z toward the viewer; the bean body is ~1.9 u tall (1 u = 171 phone px = 57 pt
on the home screen).
"""
from __future__ import annotations

import math

import numpy as np

import char_kit as K
from mesher import Material
from uikit import (Part, box, capsule, cylinder, ellipsoid, extrude, gloss, metal, polygon2, round_cone, satin,  # noqa: F401
                   sphere, torus, union)

VOXEL = 0.006
SCALE_PT = 57.0          # pt per unit on the home screen

# ------------------------------------------------------------------ BODY colourways (LUT over obscurance u)
# reference yellow (k-means on 002 / store 8): highlight #FECB39, lit #FBB510, shade #EE9B0D, deep #D07405 -- hue slides
# toward orange (warmer) and saturation rises into the shade. Ours keep that ladder in blue: bright azure lit, shade
# sliding toward a deeper cobalt, creases saturated ultramarine.
COLOURWAYS = {
    "blue": [(0.0, "#A6E6FF"), (0.22, "#62CAFF"), (0.42, "#36B0FF"), (0.6, "#1F8EF2"), (0.8, "#1264D6"), (1.0, "#0A3CA8")],
    "blue_v1": [(0.0, "#8ADBFF"), (0.22, "#48BCFF"), (0.42, "#25A2FB"), (0.6, "#1A84EE"), (0.8, "#0F5ED3"), (1.0, "#0839A6")],
    "cyan": [(0.0, "#9BEBFF"), (0.22, "#56D2FF"), (0.42, "#27B8F5"), (0.6, "#1596E0"), (0.8, "#0B6CC4"), (1.0, "#06439A")],
    "red": [(0.0, "#FF9C8A"), (0.22, "#FF6A55"), (0.42, "#F4442F"), (0.6, "#DC2E22"), (0.8, "#B81A18"), (1.0, "#860C12")],
}
SHORTS = [(0.0, "#6A73CF"), (0.4, "#4B55B6"), (0.7, "#3A4399"), (1.0, "#262C70")]
BELT = [(0.0, "#C0703A"), (0.45, "#9E5226"), (0.75, "#7E3C18"), (1.0, "#56260C")]
LILAC = "#A7ADDD"        # buckle + wrench (their lilac-grey metal)
NAVY = [(0.0, "#6E7FD0"), (0.45, "#4656A8"), (0.75, "#34428A"), (1.0, "#222C64")]
GREEN = [(0.0, "#7FD27A"), (0.45, "#43A348"), (0.75, "#2F8036"), (1.0, "#1C5A22")]
SPROUT = "#1D1B26"
GLOVE = [(0.0, "#8A8CA0"), (0.45, "#5E6074"), (0.75, "#46485A"), (1.0, "#2C2D3A")]   # the carriers' dark grey gloves
GLASSES = "#3A3B48"
EYE_WHITE = "#FBFAF6"
IRIS = "#3A2416"
PUPIL = "#100904"
LID_LINE = "#1E1A22"
MOUTH_IN = "#A8361A"
TONGUE = "#EE5A48"


def body_mat(colour):
    return K.skin(f"w_body_{colour}", COLOURWAYS[colour], None, vfn=None, rough=0.36, ior=1.30, clearcoat=0.25,
                  cc_rough=0.25)


def rot(axis, deg):
    return K.rotate_matrix(axis, deg)


# ------------------------------------------------------------------ the bean

def bean(girth=1.0, tall=1.0):
    """The capsule body: a tall bean, the dome slightly narrower than the belly, the front a little fuller.
    girth widens it (x and z): store 7's walkie worker is rounder (w/h ~0.8) than the glasses worker (~0.68).
    tall (director r2, the loading cast): stretches the LOWER body downward (the bottom moves below y 0.08; the face and
    the belt stay where they are)."""
    g = girth
    ry = 0.62 * tall
    lower = ellipsoid(0.58 * g, ry, 0.54 * g).translate(0, 0.70 - (ry - 0.62), 0.0)
    upper = ellipsoid(0.655 * g, 0.60, 0.54 * g).translate(0, 1.31, -0.01)
    return union(lower, upper, k=0.42)


def face_parts(b, eyes="open", look=(0.0, 0.0), mouth="open", eye_c=(0.178, 1.40), eye_r=(0.172, 0.212, 0.125),
               tilt=0.0, mouth_y=0.98, mouth_w=0.34, brows=(0.10, 0.0), mouth_h=0.25, teeth_w=0.66, mouth_z=0.10, lid_w=1.0):
    """Eyes (white bulbs, big dark iris, glint), the thick dark upper lid line (open), body-coloured lids (half /
    closed) with a dark lash line, and the mouth ("open": the big D with two front teeth + tongue; "smile": a closed
    smile groove; "grin": a small open smile)."""
    out = dict(eyes=[], irises=[], pupils=[], glints=[], lidline=[], lids=[], sockets=[], brows=[])
    ex0, ey0 = eye_c
    rx, ry, rz = eye_r
    for sx in (-1, 1):
        ex, ey = sx * ex0, ey0 + sx * tilt
        ez = K.surface_z_of(b, ex, ey)
        c = np.array([ex, ey, ez - rz * 0.35])
        e = ellipsoid(rx, ry, rz).translate(*c)
        out["eyes"].append(e)
        out["sockets"].append(ellipsoid(rx * 1.08, ry * 1.06, rz * 1.15).translate(*c))
        lx, ly = look
        d = K.unit([lx * rx, ly * ry, rz])
        sp = c + d * np.array([rx, ry, rz])
        out["irises"].append(e.offset(0.002).intersect(sphere(0.085).translate(*sp)))
        out["pupils"].append(e.offset(0.004).intersect(sphere(0.052).translate(*sp)))
        g = c + K.unit(d + np.array([0.30, 0.35, 0.0])) * np.array([rx, ry, rz])
        out["glints"].append(sphere(0.022).translate(*(g + d * 0.008)))
        out["glints"].append(sphere(0.010).translate(*(c + K.unit(d + np.array([-0.3, -0.3, 0])) * np.array([rx, ry, rz]) + d * 0.008)))
        shell = ellipsoid(rx + 0.014, ry + 0.014, rz + 0.014).translate(*c)
        # the black brow: a short thick capsule floating above the eye (raised = surprised / happy)
        braise, btilt = brows
        bc = np.array([ex + sx * 0.03, ey + ry + 0.10 + braise * (1.0 if sx > 0 else 0.6), 0.0])
        bc[2] = K.surface_z_of(b, bc[0], bc[1]) + 0.012
        bd = K.unit([1.0, sx * btilt, 0.0])
        out["brows"].append(capsule(tuple(bc - bd * 0.09), tuple(bc + bd * 0.09), 0.055))
        # r3: "wink" (SPEC-motion-audio §15.4 eyes_wink): the screen-right eye closed (happy arc), the other open
        em = ("closed" if sx > 0 else "open") if eyes == "wink" else eyes
        if em == "open":
            # the dark upper lid line: a tube hugging the top contour of the eye, thick in the middle
            a = np.linspace(math.radians(15), math.radians(165), 9)
            px = c[0] + np.cos(a) * (rx + 0.002)
            py = c[1] + np.sin(a) * (ry + 0.002)
            pz = np.array([K.surface_z_of(shell, x, y) for x, y in zip(px, py)]) - 0.016
            rr = (0.010 + 0.017 * np.sin(a) ** 2) * lid_w
            out["lidline"].append(K.limb(np.stack([px, py, pz], 1), rr, k=0.006))
        else:
            cut = ey + (0.05 * ry if em == "half" else -1.2 * ry)
            lid = shell.intersect(box(0.4, 0.4, 0.4).translate(ex, cut + 0.4, c[2]), k=0.012)
            out["lids"].append(lid)
            a = np.linspace(-0.95, 0.95, 13)
            if em == "half":
                xs = ex + a * (rx + 0.01) * math.sqrt(max(0.0, 1 - ((cut - ey) / ry) ** 2))
                ys = np.full_like(xs, cut) - 0.004
            else:
                xs = ex + a * (rx + 0.008)
                ys = ey - 0.015 - 0.05 * (1 - a ** 2)       # happy closed arc
            zs = np.array([K.surface_z_of(shell, x, y) for x, y in zip(xs, ys)])
            out["lidline"].append(K.limb(np.stack([xs, ys, zs - 0.006], 1), np.full(len(xs), 0.017), k=0.006))
    for k_ in ("eyes", "irises", "pupils", "glints", "lidline", "lids", "sockets", "brows"):
        out[k_] = union(*out[k_]) if out[k_] else None
    zf = K.surface_z_of(b, 0.0, mouth_y)
    if mouth == "open":
        top = mouth_y + 0.12
        cav = ellipsoid(mouth_w, mouth_h, 0.32).translate(0, top - 0.02, zf - 0.10).intersect(
            box(0.7, 0.4, 0.6).translate(0, top - 0.4, zf), k=0.03)
        inner = ellipsoid(mouth_w * 0.97, mouth_h - 0.01, 0.26).translate(0, top - 0.03, zf - 0.36).intersect(
            box(0.7, 0.4, 0.6).translate(0, top + 0.01 - 0.4, zf))
        teeth = union(*[box(0.050, 0.040, 0.04, round=0.016).translate(sx * 0.056 - 0.03, top - 0.032, zf - 0.07) for sx in (-1, 1)])
        tongue = ellipsoid(mouth_w * 0.60, 0.10, 0.18).translate(0.05, top - mouth_h + 0.015, zf - 0.27)
        out.update(cavity=cav, inner=inner, teeth=teeth, tongue=tongue)
    elif mouth == "laugh":
        # director round 2 (V1 t=0 loading cast): a WIDE open smile -- the upper lip rises toward the corners and ONE
        # continuous tooth band follows it (the "open" D with two separate front teeth read as buck teeth)
        from sdf import SDF as _S

        def below(y0, curv):
            return _S(lambda p: ((p[:, 1] - (y0 + curv * p[:, 0] ** 2)) * 0.85).astype(np.float32), [-3, -3, -3], [3, 3, 3])
        top = mouth_y + 0.12
        cv = 1.15
        cav = ellipsoid(mouth_w, mouth_h, 0.32).translate(0, top - 0.02, zf - mouth_z).intersect(below(top, cv), k=0.03)
        inner = ellipsoid(mouth_w * 0.97, mouth_h - 0.01, 0.26).translate(0, top - 0.03, zf - 0.26 - mouth_z).intersect(below(top + 0.01, cv))
        if teeth_w > 0:
            band = ellipsoid(mouth_w * teeth_w, 0.30, 0.30).translate(0, top - 0.02, zf - 0.01 - mouth_z)
            teeth = band.intersect(below(top - 0.008, cv)).subtract(below(top - 0.062, cv), k=0.008)
        else:                     # r3: no teeth (the fist runner's closed-corner grin) -- a speck buried in the mouth
            teeth = sphere(0.004).translate(0, top - 0.10, zf - 0.40 - mouth_z)
        tongue = ellipsoid(mouth_w * 0.60, 0.10 + 0.25 * max(0.0, mouth_h - 0.30), 0.18).translate(
            0.03, top - mouth_h + 0.02 + 0.5 * max(0.0, mouth_h - 0.30), zf - 0.17 - mouth_z)
        out.update(cavity=cav, inner=inner, teeth=teeth, tongue=tongue)
    elif mouth in ("smile", "grin"):
        xs = np.linspace(-mouth_w * 0.75, mouth_w * 0.75, 17)
        tt = xs / (mouth_w * 0.75)
        ys = mouth_y + 0.03 + 0.07 * tt ** 2
        zs = np.array([K.surface_z_of(b, x, y) for x, y in zip(xs, ys)])
        rr = 0.020 * np.clip(1 - tt ** 2, 0, 1) ** 0.5 + 0.010
        out["groove"] = K.limb(np.stack([xs, ys, zs + 0.006], 1), rr, k=0.012)
        out["smileline"] = K.limb(np.stack([xs, ys, zs - 0.006], 1), rr * 0.6, k=0.008)
    return out


# ------------------------------------------------------------------ limbs

def arm(shoulder, elbow, wrist, r=(0.135, 0.12, 0.11)):
    return K.limb([np.asarray(shoulder, float), np.asarray(elbow, float), np.asarray(wrist, float)], list(r), k=0.05)


def hand(wrist, d, palm_n, mode="open", r=0.14, thumb_side=1):
    """Cartoon 4-finger hands: "open" (relaxed), "grip" (wrapped around a handle), "fist", "wave" (spread)."""
    if mode == "fist":
        return K.hand(wrist, d, palm_n, r=r, fingers=3, finger_len=0.70, finger_r=0.46, spread=22, curl=140,
                      thumb_side=thumb_side, thumb_angle=75, k=0.25)
    if mode == "grip":
        return K.hand(wrist, d, palm_n, r=r, fingers=4, finger_len=0.85, finger_r=0.40, spread=16, curl=95,
                      thumb_side=thumb_side, thumb_angle=55, k=0.25)
    if mode == "wave":
        return K.hand(wrist, d, palm_n, r=r, fingers=4, finger_len=1.05, finger_r=0.38, spread=24, curl=12,
                      thumb_side=thumb_side, thumb_angle=60, k=0.25)
    return K.hand(wrist, d, palm_n, r=r, fingers=4, finger_len=0.95, finger_r=0.40, spread=18, curl=40,
                  thumb_side=thumb_side, thumb_angle=55, k=0.25)


def leg_foot(hip, foot, toe_dir=(0, 0, 1), r=0.12, fs=1.0):
    """A short stub leg and a rounded bare foot (body colour). fs scales the foot (the loading cast's chunky feet)."""
    hip = np.asarray(hip, float)
    foot = np.asarray(foot, float)
    leg = capsule(tuple(hip), tuple(foot + np.array([0, 0.10, 0])), r)
    td = K.unit(toe_dir)
    R = K.frame_from(td, [0, 1, 0])     # y = toe direction
    ft = ellipsoid(0.15 * fs, 0.25 * fs, 0.115 * fs).transform(R).translate(*(foot + td * 0.07 * fs + np.array([0, 0.02, 0])))
    return union(leg, ft, k=0.06)


def leg_chunky(hip, knee, ankle, toe_dir=(0, 0, 1), sole_n=(0, -1, 0), r=0.19, foot=(0.20, 0.30, 0.16)):
    """characters r3 (store 8 / V1 loading cast): a SHORT, THICK leg -- hip -> knee -> ankle, radius r tapering a little --
    ending in a big rounded SHOE-like foot (body colour, as theirs): an ellipsoid (half-width, half-length along the
    toe, half-height) with a flattened sole, the toe rounder than the heel. sole_n = where the sole faces (a running
    foot kicked up shows its sole to the camera)."""
    hip, knee, ankle = (np.asarray(p, float) for p in (hip, knee, ankle))
    leg = K.limb([hip, knee, ankle], [r, r * 0.96, r * 0.90], k=0.05)
    td = K.unit(toe_dir)
    sn = np.asarray(sole_n, float)
    sn = K.unit(sn - td * np.dot(sn, td))
    R = K.frame_from(td, -sn)            # y = toe direction, z = up out of the instep (away from the sole)
    fw, fl, fh = foot
    c = ankle + td * fl * 0.42 + (-sn) * fh * 0.10
    body_ = ellipsoid(fw, fl, fh).transform(R).translate(*c)
    toe = ellipsoid(fw * 1.04, fl * 0.62, fh * 1.08).transform(R).translate(*(c + td * fl * 0.36))
    sole_cut = box(1.0, 1.0, 1.0).transform(R).translate(*(c + sn * (fh * 0.82 + 1.0)))
    ft = union(body_, toe, k=fh * 0.6).subtract(sole_cut, k=fh * 0.35)
    return union(leg, ft, k=0.07)


# ------------------------------------------------------------------ clothes + belt kit

def clothes(b, belt_y=0.62, lean_front=0.0, bottom=0.12):
    shorts = b.offset(0.032).intersect(box(1.2, (belt_y - bottom) / 2, 1.2).translate(0, (belt_y + bottom) / 2, 0), k=0.02)
    belt = b.offset(0.055).intersect(box(1.2, 0.058, 1.2).translate(0, belt_y + 0.02, 0), k=0.012)
    return shorts, belt


def buckle_at(b, x, y, size=0.11):
    z = K.surface_z_of(b, x, y) + 0.05
    n = K.unit([x * 0.9, 0.0, 1.0])
    R = K.frame_from([0, 1, 0], n)
    ring = box(size, size * 0.78, 0.022, round=0.022).subtract(box(size * 0.56, size * 0.36, 0.1, round=0.012))
    prong = box(0.012, size * 0.36, 0.014, round=0.006)
    return union(ring, prong).transform(R).translate(x, y, z)


def pouch_at(b, x, y):
    z = K.surface_z_of(b, x, y) + 0.06
    n = K.unit([x * 1.2, 0.0, 1.0])
    R = K.frame_from([0, 1, 0], n)
    body_ = box(0.075, 0.09, 0.04, round=0.025).transform(R).translate(x, y - 0.02, z)
    flap = box(0.078, 0.035, 0.044, round=0.018).transform(R).translate(x, y + 0.055, z + 0.004)
    stud = sphere(0.017).translate(*(np.array([x, y + 0.045, z]) + n * 0.05))
    return union(body_, flap, k=0.01), stud


def wrench_at(b, x, y, angle=-12.0, scale=1.0):
    """(x, y) = where the wrench's HEAD sits (just above the belt); the handle runs down behind the belt."""
    y = y - 0.16 * scale
    """An open-end wrench tucked behind the belt: shaft + a C-shaped head (extruded 2D) facing up."""
    z = K.surface_z_of(b, x, y) + 0.075
    n = K.unit([x * 0.9, 0.0, 1.0])
    s = scale
    shaft = extrude(polygon2([(-0.028 * s, -0.20 * s), (0.028 * s, -0.20 * s), (0.030 * s, 0.10 * s), (-0.030 * s, 0.10 * s)]), 0.016 * s)
    head_ring = extrude(polygon2([(math.cos(a) * 0.085 * s, 0.16 * s + math.sin(a) * 0.085 * s) for a in np.linspace(0, 2 * math.pi, 28, endpoint=False)]), 0.018 * s)
    jaw = extrude(polygon2([(-0.034 * s, 0.14 * s), (0.034 * s, 0.14 * s), (0.05 * s, 0.30 * s), (-0.05 * s, 0.30 * s)]), 0.05 * s)
    head = head_ring.subtract(jaw)
    ring2 = extrude(polygon2([(math.cos(a) * 0.05 * s, -0.20 * s + math.sin(a) * 0.05 * s) for a in np.linspace(0, 2 * math.pi, 24, endpoint=False)]), 0.016 * s)
    hole = extrude(polygon2([(math.cos(a) * 0.022 * s, -0.20 * s + math.sin(a) * 0.022 * s) for a in np.linspace(0, 2 * math.pi, 16, endpoint=False)]), 0.05 * s)
    w = union(shaft, head, ring2, k=0.012).subtract(hole)
    R = K.frame_from([0, 1, 0], n) @ rot((0, 0, 1), angle)
    return w.transform(R).translate(x, y, z)


# ------------------------------------------------------------------ hats, glasses, sprouts

def sprouts(b, xs=(-0.13, 0.13), y_top=1.86, lean=(0.0, 0.0)):
    out = []
    for i, x in enumerate(xs):
        a = np.array([x, y_top - 0.08, K.surface_z_of(b, x, y_top - 0.06) - 0.10])
        m = a + np.array([x * 0.25, 0.12, 0.0])
        t = m + np.array([x * 0.55 + lean[0], 0.07, 0.03 + lean[1]])
        out.append(K.limb([a, m, t], [0.050, 0.046, 0.042], k=0.02))
    return union(*out)


def cap(b, tilt=(0.0, 0.0, 14.0), brim_yaw=-35.0, top=1.90, size=1.0):
    """A small baseball cap on the top of the head (002/s7: it sits on the upper-left, tilted): a rounded crown hugging
    the dome, a short brim, a button on top. tilt (x, y, z deg) about the head top."""
    s = size
    crown = ellipsoid(0.44 * s, 0.26 * s, 0.42 * s).translate(0, top - 0.10, -0.02).intersect(
        box(1, 0.3, 1).translate(0, top - 0.17 + 0.3, 0), k=0.02)
    band = ellipsoid(0.445 * s, 0.07, 0.425 * s).translate(0, top - 0.17, -0.02)
    brim = ellipsoid(0.30 * s, 0.030, 0.24 * s).translate(0, top - 0.19, 0.36 * s).intersect(
        box(1, 1, 0.5).translate(0, top - 0.19, 0.36 * s + 0.5 - 0.08 * s))
    brim = brim.transform(rot((1, 0, 0), -8)).transform(rot((0, 1, 0), brim_yaw))
    button = sphere(0.04).translate(0, top + 0.16 * s - 0.01, -0.02)
    out = union(crown, band, brim, k=0.03)
    R = rot((0, 0, 1), tilt[2]) @ rot((1, 0, 0), tilt[0])
    piv = np.array([0, top - 0.25, 0])
    return out.translate(*(-piv)).transform(R).translate(*piv), button.translate(*(-piv)).transform(R).translate(*piv)


def square_glasses(b, eye_c=(0.24, 1.44), size=(0.255, 0.235), thick=0.068):
    """Big black square glasses: two rounded-square frames in front of the eyes, a bridge, temples back to the sides."""
    ex, ey = eye_c
    parts = []
    for sx in (-1, 1):
        cx = sx * (size[0] + 0.03)
        cz = K.surface_z_of(b, cx, ey) + 0.10
        n = K.unit([sx * 0.18, 0.0, 1.0])
        R = K.frame_from([0, 1, 0], n)
        w, h = size
        outer = box(w, h, 0.028, round=0.07)
        inner = box(w - thick, h - thick, 0.2, round=0.045)
        parts.append(outer.subtract(inner).transform(R).translate(cx, ey, cz))
        t0 = np.array([sx * (cx * sx + w * 0.95), ey + 0.06, cz - 0.02])
        t1 = np.array([sx * 0.56, ey + 0.06, K.surface_z_of(b, sx * 0.50, ey + 0.06) - 0.12])
        parts.append(K.limb([t0, t1], [0.022, 0.020], k=0.01))
    bz = K.surface_z_of(b, 0.0, ey + 0.04) + 0.10
    parts.append(K.limb([np.array([-0.06, ey + 0.05, bz]), np.array([0, ey + 0.065, bz + 0.01]),
                         np.array([0.06, ey + 0.05, bz])], [0.028, 0.028, 0.028], k=0.01))
    return union(*parts)


# ------------------------------------------------------------------ props

def walkie(center, up=(0, 1, 0), facing=(0, 0, 1), s=1.0, suffix=""):
    """The walkie-talkie (002/s7): a navy rounded box, a speaker grid of dark dots, a red button, a stubby antenna."""
    R = K.frame_from(up, facing)
    c = np.asarray(center, float)
    body_ = box(0.085 * s, 0.155 * s, 0.050 * s, round=0.035 * s)
    btn = cylinder(0.034 * s, 0.012 * s, round=0.008 * s).rotate_x(90).translate(0, -0.055 * s, 0.052 * s)
    dots = [sphere(0.011 * s).translate(dx * s, dy * s, 0.046 * s) for dx in (-0.03, 0.0, 0.03) for dy in (0.03, 0.065, 0.10)]
    ant = capsule((-0.045 * s, 0.14 * s, -0.01 * s), (-0.045 * s, 0.27 * s, -0.01 * s), 0.014 * s)
    knob = capsule((0.03 * s, 0.15 * s, 0.0), (0.03 * s, 0.17 * s, 0.0), 0.02 * s)

    def xf(x):
        return x.transform(R).translate(*c)
    return dict(walkie=xf(union(body_, knob, k=0.01)), wbutton=xf(btn), wdots=xf(union(*dots)), wantenna=xf(ant))


def clipboard(center, up=(0, 1, 0), facing=(0, 0, 1), s=1.0, suffix=""):
    R = K.frame_from(up, facing)
    c = np.asarray(center, float)
    board = box(0.20 * s, 0.26 * s, 0.022 * s, round=0.018 * s)
    paper = box(0.175 * s, 0.215 * s, 0.008 * s, round=0.006 * s).translate(0.004 * s, -0.022 * s, 0.027 * s)
    rings = [torus(0.032 * s, 0.0085 * s).rotate_y(90).translate(dx * s, 0.235 * s, 0.01 * s) for dx in (-0.10, -0.035, 0.03, 0.095)]

    def xf(x):
        return x.transform(R).translate(*c)
    return dict(board=xf(board), paper=xf(paper), rings=xf(union(*rings)))


def pencil(tip, direction, length=0.34, r=0.030, suffix=""):
    d = K.unit(direction)
    tip = np.asarray(tip, float)
    cone_end = tip + d * 0.07
    wood = round_cone(tuple(tip + d * 0.012), tuple(cone_end), 0.006, r * 0.95)
    lead = sphere(0.009).translate(*(tip + d * 0.006))
    shaft = capsule(tuple(cone_end), tuple(tip + d * (length - 0.06)), r)
    ferrule = capsule(tuple(tip + d * (length - 0.06)), tuple(tip + d * (length - 0.025)), r * 1.06)
    eraser = capsule(tuple(tip + d * (length - 0.025)), tuple(tip + d * length), r * 1.0)
    return dict(pwood=wood, plead=lead, pshaft=shaft, pferrule=ferrule, peraser=eraser)


PROP_MATS = {
    "walkie": ("#2F3F92", 0.34), "wbutton": ("#EC3438", 0.28), "wdots": ("#141A3C", 0.5), "wantenna": ("#20284E", 0.4),
    "board": ("#A8392A", 0.42), "paper": ("#F6F2E8", 0.6), "rings": ("#5E93E6", 0.3),
    "pwood": ("#F2C58E", 0.5), "plead": ("#2A2A30", 0.4), "pshaft": ("#3D84EA", 0.32), "pferrule": ("#C9CCD8", 0.3),
    "peraser": ("#F28CA3", 0.45),
}
# r3: the fist runner's SPIRAL NOTEBOOK (store 8 / V1): the clipboard geometry (board + pages + top rings) in a brown
# cover, cream pages and lilac-grey metal rings (their notebook; the home clipboard keeps its red board)
NOTEBOOK_MATS = {"board": ("#B7692F", 0.5), "paper": ("#F7EEDA", 0.62), "rings": ("#A5ABCB", 0.28)}


# ------------------------------------------------------------------ the assembler

def worker(spec, colour="blue", only=None):
    """spec: dict(eyes, look, mouth, hat ("navy"|"green"|None), glasses (bool), sprouts (bool), arms (dict L/R:
    (shoulder, elbow, wrist, hand dir, palm normal, mode)), feet (L/R foot points, toe dirs), props (list of
    (kind, kwargs)), lean (roll, pitch) deg about the feet, belt kit). Returns (parts, voxel) in body space."""
    g = spec.get("girth", 1.0)
    tl = spec.get("tall", 1.0)
    b = bean(g, tl)
    F = face_parts(b, eyes=spec.get("eyes", "open"), look=spec.get("look", (0, 0)), mouth=spec.get("mouth", "open"),
                   tilt=spec.get("eye_tilt", 0.0), mouth_w=spec.get("mouth_w", 0.30), mouth_y=spec.get("mouth_y", 1.02),
                   # r3: face_kw passes face_parts keys through (mouth_h, teeth_w, mouth_z, eye_c, eye_r, brows). NOTE: the
                   # older specs' top-level eye_c / eye_r / mouth_h / brows were never passed here (face_parts used its
                   # defaults); they stay unpassed so every shipped render is unchanged -- use face_kw to opt in
                   **spec.get("face_kw", {}))
    skin = b
    if F.get("cavity") is not None:
        skin = skin.subtract(F["cavity"], k=0.03)
    if F.get("groove") is not None:
        skin = skin.subtract(F["groove"], k=0.012)
    skin = skin.subtract(F["sockets"].offset(-0.03), k=0.02)
    bm = body_mat(colour)
    shorts, belt = clothes(b, belt_y=spec.get("belt_y", 0.62), bottom=0.12 - 1.24 * (tl - 1.0))
    limbs = []
    arm_parts = {}
    for side, tag in ((-1, "L"), (1, "R")):
        A = spec["arms"][tag]
        sh, el, wr, hd, pn, mode = A
        push = np.array([side * (spec.get("arm_push", 0.07) + (g - 1.0) * 0.62), 0.0, 0.0])  # the bean was widened after posing
        sh, el, wr = (np.asarray(sh, float) + push, np.asarray(el, float) + push, np.asarray(wr, float) + push)
        a = arm(sh, el, wr, r=spec.get("arm_r", (0.135, 0.12, 0.11)))
        h = hand(np.asarray(wr, float), hd, pn, mode=mode, thumb_side=-side if tag == "L" else side,
                 r=spec.get("hand_r", {}).get(tag, 0.14))
        if spec.get("gloves"):
            arm_parts[tag] = a
            arm_parts["hand" + tag] = h
        else:
            arm_parts[tag] = union(a, h, k=0.04)
    if spec.get("legs"):         # r3: chunky running legs (hip, knee, ankle, toe dir, sole normal) + shoe feet
        legs = [leg_chunky(*spec["legs"][t], r=spec.get("leg_r", 0.19), foot=spec.get("shoe", (0.20, 0.30, 0.16)))
                for t in ("L", "R")]
    else:
        legs = [leg_foot(spec["feet"][t][0], spec["feet"][t][1], spec["feet"][t][2], r=spec.get("leg_r", 0.12),
                         fs=spec.get("foot_s", 1.0)) for t in ("L", "R")]
    body_sdf = union(skin, *legs, k=0.05)
    parts = [Part("body", body_sdf, bm, voxel=0.007),
             Part("armL", arm_parts["L"], bm, voxel=0.005), Part("armR", arm_parts["R"], bm, voxel=0.005),
             *[Part("hand" + t, arm_parts["hand" + t], K.skin("w_glove", GLOVE, None, vfn=None, rough=0.5, ior=1.25),
                    voxel=0.004) for t in ("L", "R") if "hand" + t in arm_parts],
             Part("eyes", F["eyes"], gloss("w_eye", EYE_WHITE, rough=0.20, ior=1.45), voxel=0.003),
             Part("irises", F["irises"], gloss("w_iris", IRIS, rough=0.2, ior=1.45), voxel=0.0025),
             Part("pupils", F["pupils"], gloss("w_pupil", PUPIL, rough=0.15, ior=1.5), voxel=0.0025),
             Part("glints", F["glints"], Material("w_glint", "#FFFFFF", roughness=0.3, emissive="#FFFFFF"), voxel=0.002),
             Part("lidline", F["lidline"], satin("w_lidline", LID_LINE, rough=0.45), voxel=0.003),
             Part("brows", F["brows"], gloss("w_brow", SPROUT, rough=0.35), voxel=0.003),
             Part("shorts", shorts, K.skin("w_shorts", SHORTS, None, vfn=None, rough=0.62, ior=1.22), voxel=0.006),
             Part("belt", belt, K.skin("w_belt", BELT, None, vfn=None, rough=0.5, ior=1.25), voxel=0.004)]
    if F["lids"] is not None:
        parts.append(Part("lids", F["lids"], bm, voxel=0.003))
    if F.get("cavity") is not None:
        parts += [Part("mouth", F["inner"], Material("w_mouth", MOUTH_IN, roughness=0.5, ior=1.25, emissive="#3A0A04"), voxel=0.004),
                  Part("teeth", F["teeth"], Material("w_teeth", "#FFFFFF", roughness=0.3, ior=1.4, emissive="#6A6A6A"), voxel=0.003),
                  Part("tongue", F["tongue"], Material("w_tongue", TONGUE, roughness=0.4, ior=1.3, emissive="#40100A"), voxel=0.004)]
    if F.get("smileline") is not None:
        parts.append(Part("smileline", F["smileline"], satin("w_smile", "#0B2E78", rough=0.5), voxel=0.003))
    kit = spec.get("belt", dict(buckle=(-0.16, 0.64), pouch=(-0.46, 0.60), wrench=(0.30, 0.66)))
    if kit.get("buckle"):
        parts.append(Part("buckle", buckle_at(b, *kit["buckle"]), metal("w_lilac", LILAC, rough=0.3), voxel=0.003))
    if kit.get("pouch"):
        pch, stud = pouch_at(b, *kit["pouch"])
        parts += [Part("pouch", pch, K.skin("w_belt", BELT, None, vfn=None, rough=0.5, ior=1.25), voxel=0.004),
                  Part("stud", stud, metal("w_lilac", LILAC, rough=0.3), voxel=0.002)]
    if kit.get("wrench"):
        parts.append(Part("wrench", wrench_at(b, *kit["wrench"], scale=kit.get("wrench_scale", 1.5)), metal("w_lilac", LILAC, rough=0.3),
                          voxel=0.0025))
    if spec.get("no_brows"):
        parts = [p for p in parts if p.name != "brows"]
    if spec.get("sprouts", False):
        parts.append(Part("sprouts", sprouts(b, xs=spec.get("sprout_x", (-0.13, 0.13))), gloss("w_sprout", SPROUT, rough=0.35),
                          voxel=0.004))
    if spec.get("hat") in ("navy", "green"):
        c, btn = cap(b, tilt=spec.get("hat_tilt", (0, 0, 14)), brim_yaw=spec.get("brim_yaw", -35), size=spec.get("hat_size", 1.0))
        ramp = NAVY if spec["hat"] == "navy" else GREEN
        parts += [Part("cap", c, K.skin(f"w_cap_{spec['hat']}", ramp, None, vfn=None, rough=0.55, ior=1.22), voxel=0.005),
                  Part("capbutton", btn, satin("w_capbtn", "#2A2D40" if spec["hat"] == "green" else "#28336E", rough=0.4),
                       voxel=0.003)]
    if spec.get("glasses"):
        parts.append(Part("glasses", square_glasses(b, eye_c=spec.get("eye_c", (0.24, 1.40)), **spec.get("glasses_kw", {})),
                          gloss("w_glasses", GLASSES, rough=0.3, ior=1.4),
                          voxel=0.003))
    import char_props as CP
    for i, (kind, kw) in enumerate(spec.get("props", [])):
        if kind == "arrow":
            kw = dict(kw)
            col = kw.pop("colour")
            nm = kw.pop("name", f"arrow{i}")
            sd = CP.place(CP.arrow_sdf(**kw.pop("shape", {})), kw["center"], kw.get("up", (0, 1, 0)), kw.get("facing", (0, 0, 1)))
            parts.append(Part(nm, sd, CP.arrow_mat(col), voxel=0.005))
            continue
        if kind == "box":
            shell, dark, tape = CP.cardboard_box(**kw.get("shape", {}))
            Rb = K.frame_from(kw.get("up", (0, 1, 0)), kw.get("facing", (0, 0, 1)))
            c = np.asarray(kw["center"], float)
            parts += [Part("box", shell.transform(Rb).translate(*c), K.skin("w_box", CP.BOX, None, vfn=None, rough=0.7, ior=1.2),
                           voxel=0.006),
                      Part("boxtape", tape.transform(Rb).translate(*c), satin("w_tape", "#C58E52", rough=0.45), voxel=0.004)]
            if dark is not None:
                parts.append(Part("boxholes", dark.transform(Rb).translate(*c), satin("w_boxhole", "#2A2230", rough=0.6),
                                  voxel=0.004))
            continue
        P = {"walkie": walkie, "clipboard": clipboard, "notebook": clipboard, "pencil": pencil}[kind](**kw)
        for nm, sd in P.items():
            col, rg = (NOTEBOOK_MATS if kind == "notebook" else PROP_MATS)[nm]
            parts.append(Part(nm + kw.get("suffix", ""), sd, gloss(f"w_{nm}", col, rough=rg), voxel=0.003))
    # lean the whole figure about the feet
    roll, pitch = spec.get("lean", (0.0, 0.0))
    if roll or pitch:
        Rl = rot((0, 0, 1), roll) @ rot((1, 0, 0), pitch)
        for p in parts:
            p.sdf = p.sdf.transform(Rl)
    fld = K.field_for(("worker", repr(sorted((k, repr(v)) for k, v in spec.items())), colour), parts)
    K.shade(parts, field=fld)
    if only is not None:
        parts = [p for p in parts if p.name in only]
    return parts, VOXEL


# ------------------------------------------------------------------ home poses (002 / store 7)
# LEFT worker (navy cap + walkie): stands turned a little to screen right, eyes up-right on the walkie held beside the
# face, mouth open (talking/laughing), the other fist on the hip.
HOME_L = dict(
    eyes="open", look=(0.50, 0.12), mouth="open", mouth_w=0.40, mouth_h=0.29, hat="navy", hat_tilt=(0, 0, 28), brim_yaw=-45,
    glasses=False, hat_size=0.90, girth=1.14, eye_c=(0.20, 1.44), eye_r=(0.185, 0.225, 0.13),
    brows=(0.06, 0.25),
    arms=dict(L=((-0.52, 1.00, 0.04), (-0.70, 0.84, 0.10), (-0.56, 0.72, 0.30), (0.6, -0.4, 0.5), (0.3, 0.0, 1.0), "fist"),
              R=((0.52, 1.02, 0.04), (0.76, 0.98, 0.20), (0.76, 1.22, 0.30), (0.0, 1.0, 0.1), (-1.0, 0.0, 0.2), "grip")),
    feet=dict(L=((-0.22, 0.30, 0.0), (-0.25, 0.0, 0.08), (-0.2, 0, 1)), R=((0.22, 0.30, 0.0), (0.26, 0.0, 0.08), (0.2, 0, 1))),
    props=[("walkie", dict(center=(0.94, 1.44, 0.38), up=(0.15, 1.0, 0.0), facing=(-0.35, 0.0, 1.0), s=1.75))],
    belt=dict(buckle=(0.14, 0.64), pouch=(-0.42, 0.62), wrench=(-0.16, 0.80), wrench_scale=1.25),
    lean=(-4.0, 0.0),
)
# RIGHT worker (green cap + glasses): the clipboard held up at the screen-left, writing with the pencil, half lids.
HOME_R = dict(
    eyes="half", look=(-0.35, -0.25), mouth="smile", hat="green", hat_tilt=(0, 0, -32), brim_yaw=60, glasses=True,
    hat_size=0.90, brows=(0.20, -0.1), eye_c=(0.25, 1.44),
    arms=dict(L=((-0.50, 1.02, 0.02), (-0.70, 0.80, 0.26), (-0.56, 0.98, 0.46), (0.3, 1.0, 0.2), (1.0, 0.0, 0.3), "grip"),
              R=((0.50, 1.00, 0.02), (0.58, 0.74, 0.34), (0.20, 0.86, 0.56), (-1.0, 0.25, 0.1), (0.0, 0.3, 1.0), "grip")),
    feet=dict(L=((-0.22, 0.34, 0.0), (-0.27, 0.0, 0.08), (-0.25, 0, 1)), R=((0.22, 0.34, 0.0), (0.26, 0.0, 0.08), (0.1, 0, 1))),
    props=[("clipboard", dict(center=(-0.59, 1.02, 0.64), up=(0.25, 1.0, -0.15), facing=(0.55, 0.0, 1.0), s=1.3)),
           ("pencil", dict(tip=(-0.30, 0.98, 0.72), direction=(1.0, 0.45, 0.1)))],
    belt=dict(buckle=(-0.10, 0.64), pouch=(0.42, 0.60), wrench=None),
    lean=(3.0, 0.0),
)

# a WARM rim (owner 02:55: separate the blue body from the blue lab) from the right-back, stronger than the scientist's
# cool one; the fill stays neutral-cool so the body keeps its blue in the shade
WORKER_LIGHT_BLUE = K.light(rim_color=(1.0, 0.80, 0.55), rim_lux=2600.0, rim_dir=(-0.80, -0.25, 0.55),
                            fill_color=(0.85, 0.92, 1.0))
# director r2 (orchestrator d / grader B): on the composed home the right (glasses) worker's lit body measured only
# ~8 luminance levels above the royal-blue lab behind it (the left ~22): the home rigs get a stronger warm rim and a
# brighter key so both bodies separate by value AND a warm edge (the blue itself stays the owner's choice)
WORKER_LIGHT_HOME = K.light(rim_color=(1.0, 0.80, 0.55), rim_lux=4200.0, rim_dir=(-0.80, -0.25, 0.55),
                            fill_color=(0.85, 0.92, 1.0), key_lux=2200.0)
HOME_FRAME_W = (150, 132)       # pt: a worker + its prop (walkie / clipboard), feet to cap top, with margins
WVIEW = K.view_bounds(HOME_FRAME_W, scale_pt=SCALE_PT, center=(0.0, 1.04), zr=(-0.8, 1.0), margin=1.0)
WPOSE_L = dict(yaw=18, pitch=6, center=False)
WPOSE_R = dict(yaw=-18, pitch=6, center=False)

MODELS = {}
ASSETS = {}
for _c in ("blue", "blue_v1", "cyan", "red"):
    MODELS[f"w_homeL_{_c}"] = (lambda c=_c: worker(HOME_L, c))
    MODELS[f"w_homeR_{_c}"] = (lambda c=_c: worker(HOME_R, c))
    ASSETS[f"char_wk_homeL_{_c}_test"] = dict(scene=[(f"w_homeL_{_c}", WPOSE_L)], dest="route3d", bounds=WVIEW,
                                                frame=HOME_FRAME_W, fov=18, light=WORKER_LIGHT_BLUE, no_fit=True)
    ASSETS[f"char_wk_homeR_{_c}_test"] = dict(scene=[(f"w_homeR_{_c}", WPOSE_R)], dest="route3d", bounds=WVIEW,
                                                frame=HOME_FRAME_W, fov=18, light=WORKER_LIGHT_BLUE, no_fit=True)


# ------------------------------------------------------------------ home rigs (cut-out puppets) + placement
# placement: s7/002 standing workers -- LEFT feet centre (237, 1838) px, RIGHT (947, 1837) px (phone px; 1 pt = 2.997 px)
# v6 (checked on the composed home against the phone's REST frames 026 / 035 / meta-056 -- 002 is mid-animation):
# their feet bottoms sit at y 1835-1840 px and their green cap top at 1472-1488 px; ours (anchored as above) landed
# ~21 px lower (the feet anchor is the sole centre at y 0, but the toes project below it at pitch 6) with the same
# 356 px height, and the left worker's feet ~20 px left of theirs (feet x 191..343 vs 174..311), the right ~8 px.
FEET_FIX_PX = dict(L=(20.0, -21.0), R=(8.0, -21.0))
FEET_L_PT = ((237 + FEET_FIX_PX["L"][0]) * 393 / 1178, (1838 + FEET_FIX_PX["L"][1]) * 393 / 1178)
FEET_R_PT = ((947 + FEET_FIX_PX["R"][0]) * 393 / 1178, (1837 + FEET_FIX_PX["R"][1]) * 393 / 1178)
BODY_PARTS = {"body", "shorts", "belt", "buckle", "pouch", "stud", "wrench", "cap", "capbutton", "brows", "sprouts",
              "mouth", "teeth", "tongue", "smileline"}
EYE_PARTS = {"eyes", "irises", "pupils", "glints", "lidline", "lids"}
WALKIE = {"walkie", "wbutton", "wdots", "wantenna"}
CLIP = {"board", "paper", "rings"}
PENCIL = {"pwood", "plead", "pshaft", "pferrule", "peraser"}


def _spec_with(base, **kw):
    s = dict(base)
    s.update({k: v for k, v in kw.items() if v is not None})
    return s


def rig_for(name, base, pose, feet_pt, colour, arm_l_extra=(), arm_r_extra=(), mouths=("open", "smile"),
            eyes_default="open", glasses=False, view=None, eye_members=("open", "half", "closed"), arm_l_alts=None):
    """arm_l_alts (r3): {member name: armL tuple} extra armL group members (e.g. the idle loop's WAVE: SPEC-motion-audio
    §8.2 left worker); the layer "armL" stays the default, so the app's rotation track keeps its target."""
    def factory(only=None, eyes=None, mouth=None, armL=None):
        sp = _spec_with(base, eyes=eyes, mouth=mouth)
        if armL is not None:
            sp["arms"] = dict(sp["arms"], L=armL)
        return worker(sp, colour, only=only)
    feet = [0.0, 0.0, 0.08]
    lo = [dict(name=f"body_{m}", parts=BODY_PARTS, kw=dict(mouth=m), group="body", default=(m == base.get("mouth")),
               pivots={"feet": feet, "neck": [0.0, 1.0, 0.0]}, note=f"the bean + clothes, mouth {m}") for m in mouths]
    lo += [dict(name=f"eyes_{e}", parts=EYE_PARTS, kw=dict(eyes=e), holdout=BODY_PARTS, group="eyes",
                default=(e == eyes_default), parent="body", pivots={"eyes": [0.0, 1.44, 0.45]},
                note=f"eyes {e} (swap group: blink = open -> half -> closed -> open)") for e in eye_members]
    if glasses:
        lo.append(dict(name="glasses", parts={"glasses"}, parent="body", pivots={"eyes": [0.0, 1.44, 0.45]}))
    lo += [dict(name="armL", parts={"armL"} | set(arm_l_extra), holdout=BODY_PARTS, pivots={"shoulder": [-0.59, 1.0, 0.04]},
                parent="body", **(dict(group="armL", default=True) if arm_l_alts else {}))]
    for m, arm_ in (arm_l_alts or {}).items():
        lo.append(dict(name=m, parts={"armL"} | set(arm_l_extra), kw=dict(armL=arm_), holdout=BODY_PARTS,
                       pivots={"shoulder": [-0.59, 1.0, 0.04]}, parent="body", group="armL",
                       note="idle-loop wave (r3): the free arm raised, open hand"))
    lo += [
           dict(name="armR", parts={"armR"} | set(arm_r_extra), holdout=BODY_PARTS, pivots={"shoulder": [0.59, 1.02, 0.04]},
                parent="body")]
    spec = K.explicit_rig(MODELS, ASSETS, name, factory, HOME_FRAME_W, view or WVIEW, pose, WORKER_LIGHT_HOME, lo,
                          full_kw={}, full_anchors={"feet": feet})
    spec["place"] = dict(anchor="feet", at=feet_pt)
    return spec


# the shipped rigs (manifest sources): wk_homeL_blue, wk_homeR_blue
RIGS = {}
for _c in ("blue",):
    # the rounder walkie worker holds the walkie further out: his frame is centred 0.16 u to the right
    # r2: the rest frames (026 / 035) show the walkie worker with a CLOSED smile -> body_smile is the default layer
    RIGS[f"wk_homeL_{_c}"] = rig_for(f"wk_homeL_{_c}", dict(HOME_L, mouth="smile"), WPOSE_L, FEET_L_PT, _c,
                                     arm_r_extra=WALKIE, mouths=("smile", "open"),
                                     eye_members=("open", "half", "closed", "wink"),
                                     arm_l_alts={"armL_wave": ((-0.52, 1.00, 0.04), (-0.84, 1.16, 0.16), (-0.82, 1.54, 0.28),
                                                               (0.05, 1.0, 0.15), (0.25, 0.0, 1.0), "wave")},
                                     view=K.view_bounds(HOME_FRAME_W, scale_pt=SCALE_PT, center=(0.16, 1.04), zr=(-0.8, 1.0),
                                                        margin=1.0))
    RIGS[f"wk_homeR_{_c}"] = rig_for(f"wk_homeR_{_c}", HOME_R, WPOSE_R, FEET_R_PT, _c, arm_l_extra=CLIP,
                                     arm_r_extra=PENCIL, mouths=("smile", "open"), eyes_default="half", glasses=True)


# ------------------------------------------------------------------ colour decision sheet (char_make.py sheet wk_colour)

def _placed(case, feet_pt):
    import json as _json
    import os as _os
    from PIL import Image as _I
    im = _I.open(_os.path.join(K.ART, "out", f"{case}@3x.png")).convert("RGBA")
    anc = _json.load(open(_os.path.join(K.ART, "out", f"{case}.json")))["feet"][0]
    return im, feet_pt[0] - anc[0], feet_pt[1] - anc[1]


def _placed_test(side, c, feet_pt):
    """The route3d test renders share the full case's view; their feet anchor = the blue full case's."""
    import json as _json
    import os as _os
    from PIL import Image as _I
    im = _I.open(_os.path.join(K.APP, "build", "ui-art", "route3d", f"char_wk_home{side}_{c}_test.png")).convert("RGBA")
    anc = _json.load(open(_os.path.join(K.ART, "out", f"char_wk_home{side}_blue.json")))["feet"][0]
    return im, feet_pt[0] - anc[0], feet_pt[1] - anc[1]


def home_plate(shot_rel="research/shots/002-home-L32.png"):
    """002 with the original workers wiped by a diffusion fill (sheet-only clean plate)."""
    from PIL import Image as _I, ImageDraw as _D
    base = K.shot(shot_rel)
    m = _I.new("L", base.size, 0)
    d = _D.Draw(m)
    d.rounded_rectangle((0, 1470, 392, 1862), 40, fill=255)
    d.rounded_rectangle((748, 1478, 1090, 1856), 40, fill=255)
    # keep the capsule machine + level plate (they overlap the rectangles)
    d.rounded_rectangle((300, 1150, 760, 1720), 30, fill=0)
    return K.diffuse_fill(base, np.asarray(m) > 128), base


def _sheet_colour():
    import os as _os
    rig_dir = _os.path.join(K.ART, "out", "char_sci_home_rig")
    plate, base = home_plate()
    sci, rj = K.layer_composite(rig_dir, {"torso", "armL", "armR", "headSmile"})
    pl = rj["placement_pt"]
    from char_scientist import console_mask_002
    from PIL import Image as _I
    rows = []
    tiles = [("reference 002 (looked at only)", base.crop((0, 380, 1178, 1900)))]
    for c in ("blue_v1", "cyan", "blue"):
        ctx = K.on_shot(plate, sci, pl["x"], pl["y"])
        ctx = _I.composite(plate, ctx, console_mask_002(plate.size))
        for side, fp in (("L", FEET_L_PT), ("R", FEET_R_PT)):
            im, x, y = _placed(f"char_wk_home{side}_{c}", fp) if c == "blue" else _placed_test(side, c, fp)
            ctx = K.on_shot(ctx, im, x, y)
        tiles.append((f"ours: workers {c.upper()} (clean plate = their workers wiped)", ctx.crop((0, 380, 1178, 1900))))
    rows.append(("home composition at game size", tiles))
    return rows, ("WORKER COLOURWAY on the home screen: blue v1 | cyan-blue | BLUE final (lighter azure + warm rim) -- "
                  "owner 02:55: workers are BLUE; red not rendered")


SHEETS = {"wk_colour": _sheet_colour}


def leaned(spec, p):
    """A body-space point moved by the spec's lean (the same transform worker() applies to every part)."""
    roll, pitch = spec.get("lean", (0.0, 0.0))
    Rl = rot((0, 0, 1), roll) @ rot((1, 0, 0), pitch)
    return (Rl @ np.asarray(p, float)).tolist()
