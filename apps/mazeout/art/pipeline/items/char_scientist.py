"""The SCIENTIST: the original's top monster reproduced 1:1 as our own 3D model (SDF skin + strand fur), recoloured
PINK (owner update 02:33). Modelled from scratch from measurements of the captures (looked at only):

  002-home-L32 (phone, 1178 px = 393 pt)  head incl. fur: x 486..754 px (widest at y 670), top 540 (skin ~555, crown
      tuft to 530), jowl bottom 784; eyes (whites) L 571..608 x 600..646, R 624..665 x 607..656; pupils at the bottom
      inner side (looking down at the console); brows L 574..611 x 576..589, R 635..672 x 581..608; closed smile
      540..702 px wide, corners y ~662-670, lowest y 677; head rolled ~8 deg clockwise (right eye lower).
  store 7 (open laugh + finger up), store 8 (running with arrows), 067/094 avatars (head + coat on pink).

Head space: the jowl bottom at y 0 -> world y HEAD_Y; 1 unit = 200 phone px = 66.8 pt (the head is 1.33 u wide
incl. tufts). +Y up, +Z toward the viewer.
"""
from __future__ import annotations

import math

import numpy as np

import char_fur as FUR
import char_kit as K
from mesher import Material
from uikit import (Part, box, capsule, ellipsoid, extrude, gloss, metal, polygon2, revolve, round_cone, satin, sphere,  # noqa: F401
                   spline_profile, torus, union)

VOXEL = 0.006
SCALE_PT = 66.8          # pt per unit on the home screen
HEAD_Y = 1.30            # world y of the jowl bottom (the body sits below)

# ------------------------------------------------------------------ palette: candy PINK (reference purple fur for
# comparison: k-means #DB88F4 / #CA6BEA / #B351D8 / #953FC3 / #7D2DB1 / #4B1D6C, median H 283 S 0.62 V 0.84 on 002).
# Ours keeps the reference's saturation/value ladder (shadows deeper + more saturated) at hue ~333 (candy pink), lifted
# ~5 % in value so it reads warm and candy-like, not raspberry.
P_HL, P_LIT, P_MID, P_SHADE, P_DEEP, P_UNDER = "#FFA8C8", "#FF8AB9", "#FA6BA9", "#EB5098", "#D13684", "#B22470"
P_BROW, P_BROW2, P_BROWHL = "#801953", "#61103F", "#A3316E"
# fur LUT rows (v): 0 = underside/deep root, 0.35 = root, 1 = tip; columns (u): obscurance convex -> crease
FUR_STOPS = [(0.0, [(0.0, P_SHADE), (0.5, P_DEEP), (1.0, P_UNDER)]),
             (0.35, [(0.0, P_LIT), (0.35, P_MID), (0.6, P_SHADE), (1.0, P_DEEP)]),
             (1.0, [(0.0, P_HL), (0.35, P_LIT), (0.6, P_MID), (1.0, P_SHADE)])]
BROW_STOPS = [(0.0, [(0.0, P_BROW2), (1.0, "#4A0C30")]), (0.35, [(0.0, P_BROW), (1.0, P_BROW2)]),
              (1.0, [(0.0, P_BROWHL), (1.0, P_BROW)])]
SKIN = [(0.0, P_MID), (0.5, P_SHADE), (0.8, P_DEEP), (1.0, P_UNDER)]


def _lift(hexc, v=1.12, s=1.08):
    import colorsys
    r, g, b = K.hexrgb(hexc)
    h, ss, vv = colorsys.rgb_to_hsv(r, g, b)
    r, g, b = colorsys.hsv_to_rgb(h, min(1.0, ss * s), min(1.0, vv * v))
    return "#%02X%02X%02X" % tuple(int(round(c * 255)) for c in (r, g, b))


def _lift_stops(stops, **kw):
    return [(v, [(u, _lift(c, **kw)) for u, c in row]) for v, row in stops]


# characters r3 -- the LOADING scientist (store 8 / V1): their fur reads lighter + more saturated than ours at game size
# (theirs median S 0.67 V 0.82 on store 8, ours S 0.60 V 0.73 with the home ladder under the loading light), so the
# loading style lifts the same pink ladder (hue kept); brows are a deep fur tone there, not near-black
FUR_STOPS_LOAD = _lift_stops(FUR_STOPS)
SKIN_LOAD = [(u, _lift(c)) for u, c in SKIN]
BROW_STOPS_LOAD = [(0.0, [(0.0, "#A42E72"), (1.0, "#86225E")]), (0.35, [(0.0, "#BC4286"), (1.0, "#A42E72")]),
                   (1.0, [(0.0, "#D65C9C"), (1.0, "#BC4286")])]
BROW_SKIN_LOAD = [(0.0, "#BC4286"), (0.5, "#A42E72"), (1.0, "#86225E")]
TONGUE_LOAD = "#E23A55"


def pal(style):
    if style == "load":
        return dict(fur=FUR_STOPS_LOAD, skin=SKIN_LOAD, brow=BROW_STOPS_LOAD, browskin=BROW_SKIN_LOAD, tongue=TONGUE_LOAD)
    return dict(fur=FUR_STOPS, skin=SKIN, brow=BROW_STOPS, browskin=BROW_SKIN, tongue=TONGUE)
BROW_SKIN = [(0.0, P_BROW), (0.5, P_BROW2), (1.0, "#4A0C30")]
LIP = "#94215A"
MOUTH_IN = "#6A1440"     # the open mouth's dark inside (reference: a dark maroon-violet)
TONGUE = "#D8336F"
EYE_WHITE = "#F6F3F8"
IRIS = "#4A2A66"         # the reference's dark violet-brown iris (kept: an accessory colour, not the body)
PUPIL = "#120A16"


# ------------------------------------------------------------------ head

def _profile(style="home"):
    """Skin half-width r vs height h above the jowl bottom (the fur adds ~0.03-0.06 outside; tufts more)."""
    if style == "load":
        # r3 (store 8, rows measured about the eye line at 90 pt/u): the same jowls, a TALLER, fuller dome (their skin
        # top ~0.40 u above the eye centre, ours 0.335; half-widths 0.28 at h 1.06, 0.32 at 0.95)
        # r3 v2: the upper head measured ~0.17 u narrower than theirs at the brows -> fuller shoulders of the dome
        return [(0.0, 0.035), (0.20, 0.050), (0.36, 0.125), (0.46, 0.215), (0.535, 0.315), (0.575, 0.42), (0.59, 0.50),
                (0.58, 0.58), (0.54, 0.655), (0.48, 0.735), (0.445, 0.82), (0.415, 0.915), (0.375, 1.005), (0.315, 1.08),
                (0.21, 1.15), (0.0, 1.20)]
    pts = [(0.0, 0.035), (0.20, 0.050), (0.36, 0.125), (0.46, 0.215), (0.535, 0.315), (0.575, 0.42), (0.585, 0.50),
           (0.565, 0.58), (0.50, 0.655), (0.42, 0.735), (0.365, 0.82), (0.325, 0.915), (0.283, 1.005),
           (0.19, 1.085), (0.0, 1.125)]
    return pts


def head_skin_raw(style="home"):
    s = revolve(spline_profile(_profile(style), samples=96)).scale_xyz(1.0, 1.0, 0.86)
    # the face is a little fuller in front at the cheeks/jowls, flatter at the back
    cheeks = ellipsoid(0.46, 0.26, 0.30).translate(0, 0.44, 0.17)
    return union(s, cheeks, k=0.12)


def surface_z(s, x, y, z0=1.5):
    return K.surface_z_of(s, x, y, z0)


EYES = [dict(c=(-0.140, 0.790), r=(0.108, 0.140, 0.090)), dict(c=(0.140, 0.790), r=(0.112, 0.146, 0.092))]
SMILE_X = (-0.37, 0.40)
# v6: the head roll tilts the smile; theirs (002) keeps the smile nearly level while the eyes tilt ~8.6 deg, so the
# groove is counter-tilted in head space (right corner raised)
SMILE_TILT = 0.10


def face(skin, mouth="smile", look=(0.10, -0.62), style="home"):
    """Eyes (white bulbs with iris/pupil/glint looking at `look` = (x, y) in eye-radius units), brow ridges, and the
    mouth: "smile" = the closed smile groove (002), "open" = the open laugh (store 7 / 8)."""
    out = {}
    eyes, irises, pupils, glints, sockets = [], [], [], [], []
    for i, E in enumerate(EYES):
        ex, ey = E["c"]
        sx = -1 if i == 0 else 1
        ez = surface_z(skin, ex, ey)
        rx, ry, rz = E["r"]
        c = np.array([ex, ey, ez - rz * 0.05])
        eye = ellipsoid(rx, ry, rz).translate(*c)
        eyes.append(eye)
        sockets.append(ellipsoid(rx * 1.12, ry * 1.10, rz * 1.2).translate(*c))
        # iris / pupil caps on the eyeball, toward the look direction (inward-down for 002: looking at the console)
        lx, ly = look
        lxx = -sx * abs(lx) if lx >= 0 else sx * abs(lx)       # lx > 0 = converge (look near, inward)
        d = K.unit([lxx * rx, ly * ry, rz * 1.0])
        sp = c + d * np.array([rx, ry, rz]) * 1.0              # ~ on the ellipsoid surface
        irises.append(eye.offset(0.0015).intersect(sphere(0.060).translate(*sp)))
        pupils.append(eye.offset(0.0030).intersect(sphere(0.037).translate(*sp)))
        gp = c + K.unit(d + np.array([-0.30, 0.34, 0.0])) * np.array([rx, ry, rz]) * 1.0
        glints.append(sphere(0.0165).translate(*(gp + d * 0.006)))
        glints.append(sphere(0.006).translate(*(c + K.unit(d + np.array([0.30, -0.30, 0.0])) * np.array([rx, ry, rz]))))
    out.update(eyes=union(*eyes), irises=union(*irises), pupils=union(*pupils), glints=union(*glints),
               sockets=union(*sockets))
    # brows: a thick dark arch hugging the top of each eye (002: 0.19 u wide, 0.065 thick, touching the eye)
    brows = []
    for i, E in enumerate(EYES):
        ex, ey = E["c"]
        rx, ry, _ = E["r"]
        sx = -1 if i == 0 else 1
        a = np.linspace(-1.0, 1.0, 9)
        xs = ex + sx * 0.012 + a * rx * 0.60
        ys = ey + ry * 1.00 + 0.045 + 0.038 * (1 - a ** 2) - 0.006 * (a * sx)   # a friendly raised arch (v6: shorter, higher)
        if style == "load":      # r3 (store 8): raised well clear of the eyes, wider and thinner
            xs = ex + sx * 0.03 + a * rx * 0.80
            ys = ey + ry * 1.00 + 0.10 + 0.040 * (1 - a ** 2) + 0.010 * (a * sx)
        zs = np.array([surface_z(skin, x, y) for x, y in zip(xs, ys)])
        pts = np.stack([xs, ys, zs + 0.004], 1)
        rr = 0.022 + 0.022 * (1 - a ** 2) ** 0.6
        if style == "load":
            rr = rr * 0.58
        brows.append(K.limb(pts, rr, k=0.02))
    out["brows"] = union(*brows)
    out["brow_pts"] = np.array([[E["c"][0], E["c"][1] + E["r"][1] * 1.00 + 0.05] for E in EYES])
    # mouth
    xs = np.linspace(SMILE_X[0], SMILE_X[1], 21)
    tt = (xs - (SMILE_X[0] + SMILE_X[1]) / 2) / ((SMILE_X[1] - SMILE_X[0]) / 2)
    if mouth == "smile":
        ys = 0.535 + 0.075 * tt ** 2 + 0.030 * tt ** 8 + SMILE_TILT * xs
        zs = np.array([surface_z(skin, x, y) for x, y in zip(xs, ys)])
        rr = 0.012 * np.clip(1 - tt ** 2, 0, 1) ** 0.5 + 0.008
        groove = K.limb(np.stack([xs, ys, zs + 0.006], 1), rr, k=0.012)
        line = K.limb(np.stack([xs, ys, zs - 0.004], 1), rr * 0.60, k=0.008)
        out.update(groove=groove, lipline=line, smile=np.stack([xs, ys, zs], 1))
    elif mouth == "open":
        # the open laugh (store 7 / 8): a wide D -- flat upper lip with the upper teeth under it, round bottom, a dark
        # inside, the tongue on the floor
        zf = surface_z(skin, 0.0, 0.48)
        top = 0.655
        # the upper lip rises toward the corners (a smile): the flat top is a gentle upward arc, not a plane
        lipcut = SDF_arc_top(top, 0.55)
        cav = ellipsoid(0.40, 0.29, 0.34).translate(0, top - 0.02, zf - 0.10).intersect(lipcut, k=0.02)
        # the back wall of the mouth: its front must stay BEHIND the teeth (a solid "inner" in front of them hid them)
        inner = ellipsoid(0.40, 0.29, 0.26).translate(0, top - 0.03, zf - 0.34).intersect(SDF_arc_top(top + 0.01, 0.55))
        teeth = union(*[box(0.068, 0.052, 0.05, round=0.028).translate(sx * 0.074, top - 0.030, zf - 0.075)
                        for sx in (-1, 1)]).intersect(SDF_arc_top(top - 0.004, 0.55))
        tongue = ellipsoid(0.23, 0.11, 0.20).translate(0.02, top - 0.270, zf - 0.24)
        out.update(cavity=cav, inner=inner, teeth=teeth, tongue=tongue)
    elif mouth == "grin":
        # director round 2 -- V1 t=0 / store 8 loading: a BIG OPEN SMILE, not round 1's shouting D with two buck
        # teeth: a wide crescent whose upper lip rises toward the corners, ONE continuous upper tooth band following
        # the lip, a red tongue low in the opening, a dark inside
        zf = surface_z(skin, 0.0, 0.50)
        top = 0.60
        curv = 1.00
        cav = ellipsoid(0.35, 0.175, 0.30).translate(0, top - 0.03, zf - 0.10).intersect(SDF_arc_top(top, curv), k=0.02)
        inner = ellipsoid(0.34, 0.17, 0.22).translate(0, top - 0.04, zf - 0.30).intersect(SDF_arc_top(top + 0.01, curv))
        # the tooth band: the middle ~60 % of the upper lip, thin (V1: a white strip under the lip, not a white lip)
        band = ellipsoid(0.215, 0.20, 0.30).translate(0, top - 0.03, zf - 0.12)
        teeth = band.intersect(SDF_arc_top(top - 0.008, curv)).subtract(SDF_arc_top(top - 0.052, curv), k=0.008)
        tongue = ellipsoid(0.19, 0.075, 0.17).translate(0.015, top - 0.140, zf - 0.19)
        out.update(cavity=cav, inner=inner, teeth=teeth, tongue=tongue)
    elif mouth == "crescent":
        # r3 -- store 8 / V1 loading, measured about the eye line (90 pt/u): a wide CRESCENT smile, corners up at the
        # eye bottoms (x +-0.27, y 0.63), the upper lip dipping to y 0.52 at the middle, a deep round bottom at 0.32;
        # a short tooth band (0.23 wide, two teeth) hanging under the lip centre; a red tongue low in the opening
        x0 = 0.02
        zf = surface_z(skin, x0, 0.50)
        # v3 (raw render at 4x next to store 8): the upper lip was flat over its middle -- theirs curves all the way
        # from the teeth up into the cheeks (a banana crescent); the tooth plate read thick; the tongue sat too high
        y0, cv = 0.50, 1.55
        arc = SDF_arc_top(y0, cv).translate(x0, 0, 0)
        cav = ellipsoid(0.34, 0.20, 0.24).translate(x0, 0.49, zf - 0.08).intersect(arc, k=0.02)
        inner = ellipsoid(0.33, 0.19, 0.20).translate(x0, 0.48, zf - 0.24).intersect(
            SDF_arc_top(y0 + 0.01, cv).translate(x0, 0, 0))
        band = ellipsoid(0.100, 0.20, 0.16).translate(x0 + 0.01, 0.49, zf - 0.10)
        teeth = band.intersect(SDF_arc_top(y0 - 0.006, cv).translate(x0, 0, 0)).subtract(
            SDF_arc_top(y0 - 0.044, cv).translate(x0, 0, 0), k=0.008).subtract(box(0.004, 0.06, 0.3).translate(x0 + 0.012, 0.47, zf))
        tongue = ellipsoid(0.17, 0.08, 0.15).translate(x0 + 0.02, 0.355, zf - 0.15)
        out.update(cavity=cav, inner=inner, teeth=teeth, tongue=tongue)
    return out


def SDF_arc_top(y0, curv):
    """Half-space below the arc y = y0 + curv * x^2 (an SDF bound: the vertical distance x 0.9)."""
    from sdf import SDF as _S
    return _S(lambda p: ((p[:, 1] - (y0 + curv * p[:, 0] ** 2)) * 0.85).astype(np.float32), [-2, -2, -2], [2, 2, 2])


def lids(skin, F, eyes="half"):
    """Blink/half-lid shells over the eyes: the eyeball grown by 0.012, cut by a plane (half) or whole (closed), plus
    a dark lash crease along the lid edge (closed: a happy downward arc)."""
    shells, creases = [], []
    for i, E in enumerate(EYES):
        ex, ey = E["c"]
        rx, ry, rz = E["r"]
        ez = surface_z(skin, ex, ey)
        c = np.array([ex, ey, ez - rz * 0.05])
        shell = ellipsoid(rx + 0.012, ry + 0.012, rz + 0.012).translate(*c)
        if eyes == "half":
            cut = ey + ry * 0.05
            shell = shell.intersect(box(0.3, 0.3, 0.3).translate(ex, cut + 0.3, c[2]), k=0.01)
            a = np.linspace(-0.95, 0.95, 11)
            xs = ex + a * (rx + 0.008) * np.sqrt(np.clip(1 - (cut - ey) ** 2 / ry ** 2, 0, 1))
            ys = np.full_like(xs, cut)
        else:
            a = np.linspace(-0.92, 0.92, 11)
            xs = ex + a * (rx + 0.008)
            ys = ey - 0.01 - 0.035 * (1 - a ** 2)          # the happy closed arc (^ ^)
        zs = np.array([surface_z(shell, x, y) for x, y in zip(xs, ys)])
        creases.append(K.limb(np.stack([xs, ys, zs - 0.004], 1), np.full(len(xs), 0.0085), k=0.004))
        shells.append(shell)
    return union(*shells), union(*creases)


def head_parts(mouth="smile", look=(0.14, -0.40), style="home"):
    skin0 = head_skin_raw(style)
    F = face(skin0, mouth=mouth, look=look, style=style)
    skin = skin0
    if mouth == "smile":
        skin = skin.subtract(F["groove"], k=0.012)
    elif "cavity" in F:
        skin = skin.subtract(F["cavity"], k=0.03)
    skin = skin.subtract(F["sockets"].offset(-0.02), k=0.02)
    F["skin0"] = skin0
    return skin, F


# ------------------------------------------------------------------ groom

def groom(P, N, F, rng, style="home"):
    """comb, length, lift, width per root (head space)."""
    M = len(P)
    x, y, z = P[:, 0], P[:, 1], P[:, 2]
    face_c = np.array([0.0, 0.66, 0.45])
    radial = P - face_c
    radial[:, 2] *= 0.3
    comb = K.unit(radial) * 0.9 + np.array([0, -0.35, 0])[None]
    # above the brows the fur flows up and back toward the crown
    up = np.clip((y - 0.86) / 0.12, 0, 1)[:, None]
    comb = comb * (1 - up) + np.array([0.0, 1.0, -0.55])[None] * up
    comb = comb + np.array([0.18, 0, 0])[None] * up        # the crown leans right (002)
    L = np.full(M, 0.040)
    L += 0.030 * np.clip((0.70 - y) / 0.4, 0, 1)           # longer on the jowls
    side = np.abs(x) / 0.6
    ty = np.where(x < 0, 0.60, 0.64)          # v6: lower cheek tufts (002: widest at y 669 L / ~700 R px)
    tlen = np.where(x < 0, 0.09, 0.11)         # v6: the left tuft stuck out 25 px past theirs
    tdrop = -0.4
    if style == "load":
        # r3 (store 8): a big wispy flare sweeping out + UP on the right side at the eye line, a shorter wisp low on
        # the left cheek
        ty = np.where(x < 0, 0.55, 0.74)
        tlen = np.where(x < 0, 0.10, 0.22)
        tdrop = np.where(x < 0, -0.25, 0.45)[:, None]
    tuft = np.exp(-((y - ty) / 0.11) ** 2) * np.clip((side - 0.66) / 0.2, 0, 1)
    L += tlen * tuft
    comb = comb + np.array([0, 1.0, 0])[None] * tdrop * tuft[:, None] + np.sign(x)[:, None] * np.array([1.0, 0, 0])[None] * tuft[:, None]
    L *= 0.8 + 0.4 * rng.random(M)
    lift = 0.40 + 0.35 * tuft
    # near the eyes and the smile: short, combed away from them
    for E in EYES:
        ex, ey = E["c"]
        d = np.hypot((x - ex) / 0.13, (y - ey) / 0.155)
        near = np.clip(1.6 - d, 0, 1)
        L *= 1 - 0.55 * near
    if "cavity" in F:
        # around the open mouth: very short fur combed AWAY from the opening (else the lip fur droops over the teeth)
        from sdf import gradient as _grad
        P32 = np.asarray(P, np.float32)
        dc = F["cavity"](P32)
        # r3 load: a wider fur-free rim so the crescent's corners stay open (the cheek fur hid them -> read as an "O")
        near = np.clip(1 - dc / (0.13 if style == "load" else 0.09), 0, 1)
        L *= 1 - (0.93 if style == "load" else 0.85) * near
        away = K.unit(_grad(F["cavity"], P32, 0.004).astype(float))
        comb = comb * (1 - near[:, None]) + away * near[:, None] * 2.0
    if "smile" in F:
        from scipy.spatial import cKDTree
        dd, _ = cKDTree(F["smile"]).query(P)
        near = np.clip(1 - dd / 0.05, 0, 1)
        L *= 1 - 0.6 * near
    W = np.full(M, 0.0066) * (0.8 + 0.4 * rng.random(M))
    return comb, L, lift, W


def density(F):
    """Root density: none inside the eye sockets, none on the brow ridges (their own dark fur), none in the groove."""
    def fn(p):
        w = np.ones(len(p))
        for i, E in enumerate(EYES):
            ex, ey = E["c"]
            rx, ry, _ = E["r"]
            d = np.hypot((p[:, 0] - ex) / (rx * 1.05), (p[:, 1] - ey) / (ry * 1.05))
            w *= np.where((d < 1.0) & (p[:, 2] > 0.1), 0.0, 1.0)
        if "cavity" in F:
            w *= (F["cavity"](np.asarray(p, np.float32)) > 0.012).astype(float)
        return w
    return fn


def brow_mask(F):
    """Roots of the dark brow fur: on the brow arches (within ~0.03 of their surface)."""
    br = F["brows"]

    def fn(p):
        d = br(np.asarray(p, np.float32))
        return ((d < 0.025) & (np.asarray(p)[:, 2] > 0.1)).astype(float)
    return fn


# ------------------------------------------------------------------ the model

def _view_dir(pose):
    import uikit
    R = uikit.rot_z(pose.get("roll", 0)) @ uikit.rot_x(pose.get("pitch", 0)) @ uikit.rot_y(pose.get("yaw", 0))
    return R.T @ np.array([0.0, 0.0, 1.0])


def head_parts_xf(Rw, tw, view_w, mouth="smile", look=(0.14, -0.40), n_strands=40000, seed=3, extra_field=(),
                  field_key=None, eyes="open", style="home"):
    """The head's parts placed in the world by head-space -> world  p' = Rw p + tw. view_w: unit vector toward the
    camera in the MODEL's world frame (before ui3d's pose). extra_field: the rest of the character's parts, so the
    obscurance of the head fur knows about the coat collar under the jowls."""
    skin_h, F = head_parts(mouth=mouth, look=look, style=style)
    PAL = pal(style)
    Rw = np.asarray(Rw, float)
    tw = np.asarray(tw, float)

    ortho = np.allclose(Rw @ Rw.T, np.eye(3), atol=1e-6)
    Ai = np.linalg.inv(Rw)

    def w(s):
        if ortho:
            return s.transform(Rw).translate(*tw)
        # director round 2: a non-uniform head scale (the loading pose's taller head). SDF.transform assumes an
        # orthonormal matrix (it evaluates f(R^T p)); a scaled one needs f(A^-1 p), distances bounded by the smallest
        # singular value, and bounds from the forward map
        from sdf import SDF as _S, _corners
        f, A32, k = s.fn, Ai.T.astype(np.float32), np.float32(np.linalg.svd(Rw, compute_uv=False).min())
        c = _corners(s.lo, s.hi) @ Rw.T
        return _S(lambda p: f(p @ A32) * k, c.min(0), c.max(0)).translate(*tw)

    def wp(P):
        return np.asarray(P, float) @ Rw.T + tw

    def wn(N):
        if ortho:
            return np.asarray(N, float) @ Rw.T
        n = np.asarray(N, float) @ Ai
        return n / np.maximum(np.linalg.norm(n, axis=-1, keepdims=True), 1e-9)

    parts = [Part("skin", w(skin_h), K.skin("s_skin", PAL["skin"], None, vfn=None, rough=0.72, ior=1.2), voxel=0.008),
             Part("brows", w(F["brows"]), K.skin("s_browskin", PAL["browskin"], None, vfn=None, rough=0.7, ior=1.2), voxel=0.004),
             Part("eyes", w(F["eyes"]), gloss("s_eye", EYE_WHITE, rough=0.18, ior=1.45), voxel=0.003),
             Part("irises", w(F["irises"]), gloss("s_iris", IRIS, rough=0.2, ior=1.45), voxel=0.002),
             Part("pupils", w(F["pupils"]), gloss("s_pupil", PUPIL, rough=0.15, ior=1.5), voxel=0.002),
             Part("glints", w(F["glints"]), Material("s_glint", "#FFFFFF", roughness=0.3, emissive="#FFFFFF"), voxel=0.0018)]
    if "lipline" in F:
        parts.append(Part("lipline", w(F["lipline"]), satin("s_lip", LIP, rough=0.6), voxel=0.003))
    if "cavity" in F:
        # inside the mouth the key light cannot reach; the reference still reads a bright tooth band and a magenta
        # tongue (painted light), so they carry a little emission
        parts += [Part("mouth", w(F["inner"]), Material("s_mouth", MOUTH_IN, roughness=0.55, ior=1.22, emissive="#2A0616"),
                       voxel=0.004),
                  Part("teeth", w(F["teeth"]), Material("s_teeth", "#FBF8F4", roughness=0.25, ior=1.4, emissive="#8A8784"),
                       voxel=0.003),
                  Part("tongue", w(F["tongue"]), Material("s_tongue", PAL["tongue"], roughness=0.35, ior=1.3, emissive="#5A1030"),
                       voxel=0.004)]
    lid_sdf = None
    if eyes in ("half", "closed"):
        lid_sdf, crease = lids(F["skin0"], F, eyes)
        parts += [Part("lids", w(lid_sdf), K.skin("s_skin", PAL["skin"], None, vfn=None, rough=0.72, ior=1.2), voxel=0.003),
                  Part("lidcrease", w(crease), satin("s_crease", P_BROW2, rough=0.6), voxel=0.002)]
    fld = K.field_for(field_key or ("sci_head", mouth, tuple(np.round(tw, 3)), tuple(np.round(Rw.ravel(), 3))),
                      parts + list(extra_field))
    K.shade(parts, field=fld)
    view_h = K.unit(Ai @ np.asarray(view_w, float))

    def build(kind):
        def fn():
            rng = np.random.default_rng(seed + (0 if kind == "fur" else 1))
            v, f, n = FUR.surface(skin_h, 0.012, key=("sci_head_surf", mouth) + ((style,) if style != "home" else ()))
            dens = density(F)
            bm = brow_mask(F)
            if kind == "fur":
                P, N = FUR.sample(v, f, n, n_strands, rng, density=lambda p: dens(p) * (1 - bm(p)))
                comb, L, lift, W = groom(P, N, F, rng, style=style)
                V, Fc, NR, T, ri = FUR.strands(P, N, comb, L, lift, W, view_h, rng, segs=4, gravity=(0, -0.18, 0),
                                               clump=0.55, clump_size=0.03, per_clump=16, jitter=0.18, nbend=0.15)
                # the crown tuft (002): ~5 long spikes standing up from the top, leaning right -- strongly clumped
                Pc, Nc = FUR.sample(v, f, n, 420, rng, density=lambda p: np.exp(-((p[:, 0] - 0.03) ** 2 +
                                                                            (p[:, 2] + 0.02) ** 2) / 0.006) * (p[:, 1] > 1.0))
                Lc = 0.10 + 0.11 * rng.random(len(Pc))
                cdir = [-0.30, 1.0, 0.05] if style == "load" else [0.45, 1.0, 0.0]    # r3: store 8's crown tuft leans left
                Vc, Fcc, NRc, Tc, ric = FUR.strands(Pc, Nc, np.tile([cdir], (len(Pc), 1)), Lc, 0.9, 0.0075,
                                                    view_h, rng, segs=5, gravity=(0.05, -0.05, 0), clump=0.9,
                                                    clump_size=0.05, per_clump=80, jitter=0.12, nbend=0.15)
                Fc = np.vstack([Fc, Fcc + len(V)])
                V = np.vstack([V, Vc]); NR = np.vstack([NR, NRc]); T = np.r_[T, Tc]; ri = np.r_[ri, ric + len(P)]
                P = np.vstack([P, Pc]); N = np.vstack([N, Nc])
                tone0, gain, under = 0.40, 0.55, 0.30
            else:
                vb, fb, nb = FUR.surface(F["brows"], 0.005, key=("sci_brow_surf", mouth) + ((style,) if style != "home" else ()))
                P, N = FUR.sample(vb, fb, nb, n_strands // 6, rng, density=lambda p: np.ones(len(p)))
                keep = N[:, 2] > -0.1
                P, N = P[keep], N[keep]
                comb = np.zeros((len(P), 3))
                comb[:, 0] = np.sign(P[:, 0])                 # the brows comb outward along the arch
                comb[:, 1] = 0.35
                L = np.full(len(P), 0.036) * (0.8 + 0.4 * rng.random(len(P)))
                W = np.full(len(P), 0.0095)
                V, Fc, NR, T, ri = FUR.strands(P, N, comb, L, 0.35, W, view_h, rng, segs=3, clump=0.25,
                                               clump_size=0.03, per_clump=10, jitter=0.12, nbend=0.15)
                tone0, gain, under = 0.40, 0.45, 0.0
            jit = rng.normal(0, 0.06, len(P))
            uv = FUR.tone_uv(fld, None, T, ri, wp(P), jit, tone0=tone0, tone_gain=gain, N=wn(N), under=under)
            return wp(V), Fc, wn(NR), uv
        return fn
    if lid_sdf is not None:
        def lidfur():
            rng = np.random.default_rng(seed + 5)
            v, f, n = FUR.surface(lid_sdf, 0.004, key=("sci_lid_surf", eyes))
            P, N = FUR.sample(v, f, n, 2600, rng, density=lambda p: (np.asarray(p)[:, 2] > 0.2).astype(float) + 1e-6)
            comb = np.tile([[0.0, 1.0, 0.0]], (len(P), 1))
            V, Fc, NR, T, ri = FUR.strands(P, N, comb, 0.012, 0.25, 0.0055, view_h, rng, segs=2, clump=0.2,
                                           clump_size=0.02, per_clump=8, jitter=0.2, nbend=0.15)
            uv = FUR.tone_uv(fld, None, T, ri, wp(P), rng.normal(0, 0.05, len(P)), tone0=0.45, tone_gain=0.45, N=wn(N))
            return wp(V), Fc, wn(NR), uv
        parts.append(FUR.fur_part("lidfur", FUR.fur_material("s_fur", None, stops=PAL["fur"], rough=0.60), lidfur))
    parts.append(FUR.fur_part("fur", FUR.fur_material("s_fur", None, stops=PAL["fur"], rough=0.60), build("fur")))
    parts.append(FUR.fur_part("browfur", FUR.fur_material("s_browfur", None, stops=PAL["brow"], rough=0.6), build("brow")))
    return parts


def head_model(pose, roll=-10.0, **kw):
    """The head alone at HEAD_Y, rolled about the jowl bottom (the fur spike / the head read)."""
    Rr = K.rotate_matrix((0, 0, 1), roll)
    return head_parts_xf(Rr, (0, HEAD_Y, 0), _view_dir(pose), **kw), VOXEL


# ------------------------------------------------------------------ body (coat, shirt, lanyard + badge, pocket + pen)
# Measured on 002 (px -> world: x = (px - 620) / 200, y = HEAD_Y + (784 - py) / 200):
#   shoulders x 440 / 820 at y ~735 / 720; coat sides at the console line (y 880): x 405 / 855; console top y ~890
#   shirt (light blue) between the coat fronts x 505..640 (top) / 490..660 (y 880), crew neckband under the jowls
#   lanyard from (560, 770) / (650, 775) to the badge clip (590, 810); badge x 560..617 y 815..857, photo square at
#   its left; pocket x 680..760 y 840..885 with a purple pen x 694..706 y 812..848; pointed shirt-style coat collar
#   flaps: left tip (495, 760), right tip (705, 790). The torso is turned ~14 deg toward screen-left (the opening
#   and the badge sit left of the head's centre) and leans over the console.

COAT = [(0.0, "#FFFFFF"), (0.45, "#F2F1F6"), (0.7, "#DCDBE8"), (1.0, "#A9AACA")]
SHIRT = [(0.0, "#BCD0F4"), (0.5, "#A7BDEB"), (0.8, "#8EA5DA"), (1.0, "#6E86C4")]
SHIRT_WHITE = [(0.0, "#FBFBFE"), (0.45, "#EDEDF4"), (0.7, "#D6D6E4"), (1.0, "#A6A7C6")]   # the loading pose (V1 t=0)
NECKBAND = "#8599D2"
LANYARD = "#56618A"
BADGE, BADGE_PHOTO, BADGE_CLIP = "#4F86DE", "#9DBBF0", "#8FB0EA"
PEN, PEN_CAP = "#A45BE8", "#7437C2"      # the pen keeps the original's purple (an accessory)
PANTS = [(0.0, "#8FAAE8"), (0.45, "#6A86D2"), (0.75, "#4F68B4"), (1.0, "#34478A")]
BELT = [(0.0, "#B8704A"), (0.45, "#96502E"), (0.75, "#763A1E"), (1.0, "#4E240E")]

POSES = {
    # torso yaw (deg, + = front to screen right), lean (deg, + = top toward the camera), head roll/yaw/nod, arms
    # v6 (002 measured on the composed home): the coat was 24 % too wide and centred ~20 px left of theirs, the head
    # ~13 px left of the eyes -> narrower upper torso, body shifted right under the head, less torso yaw, head
    # rolled 8 (not 10) and turned 6 deg to screen left, arms tucked in (elbows / wrists x before body_dx)
    "home": dict(yaw=-8.0, lean=8.0, head=dict(roll=-8.0, yaw=-6.0, nod=0.0), arms="console", narrow=0.80, body_dx=0.07, body_dy=0.07,
                 elbow_x=(0.85, 0.84), wrist_x=(0.86, 0.96)),
    # loading (store 8): running to screen right, torso turned right, head toward the viewer, fist forward, arrows held
    # director round 2 (V1 t=0 next to ours at game size): the head was wide and flat -> scaled taller/narrower
    # (head_scale); rolled SHORT sleeves with bare fur forearms; a white shirt; the fist punched forward at chest
    # height (round 1 raised it beside the head); a big open smile (mouth "grin")
    "run": dict(yaw=26.0, lean=6.0, head=dict(roll=4.0, yaw=-8.0, nod=-2.0), lower=True, body_scale=0.84,
                head_scale=(0.93, 1.10, 0.95), short_sleeves=True, shirt="white",
                arrows=[("orange", (0.56, 1.24, 0.58), (-1.0, 0.45, 0.1), (0.1, 0.2, 1.0), dict(length=0.95, width=0.72, shaft=0.36, head_len=0.40, depth=0.16)),
                        ("red", (0.46, 0.98, 0.74), (-1.0, -0.15, 0.2), (0.0, 0.3, 1.0), dict(length=1.05, width=0.78, shaft=0.38, head_len=0.44, depth=0.17))]),
    # characters r3 -- the LOADING pose rebuilt on store 8 / V1 (measured about the eye line at 90 pt/u): a squat, WIDE
    # torso whose shoulders rise to the cheeks (the head sits down in the collar), centred ~0.34 u right of the face and
    # turned a little to screen left; the fist a clenched BALL beside the mouth (forearm rising from a rolled cuff); the
    # other forearm across the belly, its mitt gripping an orange (up-left) + red (left) arrow at the right side; the far
    # leg kicked back at the lower right; the head turned 16 deg to screen left, style "load" (taller dome, lifted fur
    # ladder, raised brows, crescent smile). Arm / arrow / leg points are WORLD (x right, y up; eye mid ~ (0, 2.09)).
    "load": dict(yaw=-14.0, lean=4.0, head=dict(roll=2.0, yaw=-16.0, nod=-2.0), lower=True, style="load",
                 body_scale=(1.05, 0.90, 1.0), body_dx=0.18, body_dy=0.20, head_scale=(1.0, 1.0, 0.97),
                 short_sleeves=True, shirt="white", plain_front=True,
                 arm_pts=dict(L=((-0.58, 1.13, 0.40), (-0.79, 1.48, 0.52), (-0.45, 0.85, 0.25), (-0.3, 0.3, 1.0), 0.21),
                              R=((1.10, 1.42, 0.20), (0.86, 1.02, 0.52), (-0.55, 0.75, 0.35), (-0.8, 0.0, -0.3), 0.19)),
                 arrows=[("orange", (0.52, 1.48, 0.62), (-0.55, 1.0, 0.15), (0.25, 0.1, 1.0),
                          dict(length=0.62, width=0.58, shaft=0.30, head_len=0.30, depth=0.18)),
                         ("red", (0.46, 1.03, 0.72), (-1.0, 0.12, 0.25), (0.05, 0.4, 1.0),
                          dict(length=0.80, width=0.66, shaft=0.34, head_len=0.36, depth=0.19))],
                 leg=((0.60, 0.67, -0.05), (1.00, 0.59, -0.25), (1.12, 0.31, -0.45))),
}
CONSOLE_Y = 0.78          # world y of the console top (002: y_px ~ 890)


def rot(axis, deg):
    return K.rotate_matrix(axis, deg)


def torso_space(narrow=1.0):
    """Coat, shirt, collar, lanyard, badge, pocket, pen in torso space (front +Z, before yaw/lean)."""
    # a bell: steep shoulders from the jowl sides down to a wide base (002 coat rows: half-width 0.61 at y 1.645,
    # 0.90 at 1.32, 1.10 at 0.97 incl. the sleeves)
    # (an ellipsoid stack, not a revolved spline: the spline polygon made every coat/collar evaluation ~5x slower)
    n_ = narrow
    torso = union(ellipsoid(0.99 * n_, 0.62, 0.64).translate(0, 0.72, -0.10),
                  ellipsoid(0.86 * n_, 0.42, 0.56).translate(0, 1.22, -0.10),
                  ellipsoid(0.56 * (0.5 + 0.5 * n_), 0.24, 0.40).translate(0, 1.56, -0.10), k=0.30)
    neck = capsule((0, 1.40, -0.08), (0, 1.62, -0.06), 0.34)
    # the coat: a shell over the torso with the front opening (the shirt shows between the fronts)
    op = polygon2([(-0.30, 1.80), (0.12, 1.80), (0.24, 1.30), (0.30, 0.30), (-0.52, 0.30), (-0.46, 1.30)])
    opening = extrude(op, 1.0).intersect(box(1.5, 1.2, 0.8).translate(0, 1.0, 0.8))
    coat = torso.offset(0.045).subtract(opening, k=0.03)
    # front edges: a slightly raised facing along both sides of the opening
    facing = torso.offset(0.058).intersect(extrude(op.offset(0.05), 1.0).intersect(box(1.5, 1.2, 0.8).translate(0, 1.0, 0.8)))
    facing = facing.subtract(opening, k=0.01)
    # shirt-style collar flaps: pointed, lying on the shoulders around the jowls
    flaps = []
    for sx in (-1, 1):
        poly = [(sx * 0.10, 1.78), (sx * 0.62 * n_, 1.62), (sx * 0.56 * n_, 1.50), (sx * 0.40 * n_, 1.30), (sx * 0.26, 1.50)]
        if sx < 0:
            poly = poly[::-1]
        prism = extrude(polygon2(poly), 1.0).intersect(box(1, 1, 0.9).translate(0, 1.4, 0.4))
        flaps.append(torso.offset(0.085).intersect(prism, k=0.01))
    collar = union(*flaps, k=0.02)
    band = torus(0.36, 0.035).transform(rot((1, 0, 0), 14)).translate(-0.06, 1.62, 0.02)
    # lanyard: a V of thin cord from the neckband to the badge clip; the badge hangs on the shirt
    bx, by = -0.13 + 0.08 * (1 - narrow) / 0.2, 1.22 - 0.045 * (1 - narrow) / 0.2   # v6 home (narrow 0.8): badge under the chin (002)
    bz = K.surface_z_of(torso, bx, by) + 0.02
    pa = []
    for sx in (-1, 1):
        a = np.array([sx * 0.30 - 0.05, 1.56, K.surface_z_of(torso, sx * 0.30 - 0.05, 1.56) + 0.02])
        m = np.array([sx * 0.15 - 0.08, 1.36, K.surface_z_of(torso, sx * 0.15 - 0.08, 1.36) + 0.018])
        b = np.array([bx, by + 0.14, bz + 0.012])
        pa.append(K.limb([a, m, b], [0.011, 0.011, 0.011], k=0.005))
    lanyard = union(*pa)
    n = K.unit([-0.12, 0.12, 1.0])
    Rb = K.frame_from([0, 1, 0], n)
    badge = box(0.170, 0.125, 0.018, round=0.026).transform(Rb).translate(*(np.array([bx, by, bz]) + n * 0.012))
    photo = box(0.058, 0.064, 0.004, round=0.013).transform(Rb).translate(*(np.array([bx - 0.062, by - 0.002, bz]) + n * 0.031))
    clip = box(0.036, 0.034, 0.012, round=0.009).transform(Rb).translate(*(np.array([bx, by + 0.135, bz + 0.01])))
    # the breast pocket on the coat's LEFT front (screen right) + the purple pen clipped in it
    px_, py_ = (0.50 + 0.21 * (1 - narrow) / 0.2) * n_, 1.02 + 0.10 * (1 - narrow) / 0.2   # v6 home: pocket + pen at 002's
    pocket = coat.offset(0.012).intersect(box(0.20, 0.13, 1.0, round=0.02).translate(px_, py_ - 0.03, 0.4), k=0.01)
    pz = K.surface_z_of(coat, px_ - 0.12, py_ + 0.12) + 0.01
    pen = capsule((px_ - 0.12, py_ + 0.02, pz), (px_ - 0.115, py_ + 0.20, pz + 0.005), 0.026)
    cap = capsule((px_ - 0.115, py_ + 0.13, pz + 0.004), (px_ - 0.115, py_ + 0.21, pz + 0.006), 0.029)
    penclip = box(0.008, 0.05, 0.006, round=0.004).translate(px_ - 0.115, py_ + 0.15, pz + 0.032)
    return dict(torso=torso, neck=neck, coat=coat, facing=facing, collar=collar, band=band, lanyard=lanyard,
                badge=badge, photo=photo, clip=clip, pocket=pocket, pen=pen, cap=cap, penclip=penclip)


def fist_ball(wrist, d, facing, r=0.21):
    """r3 (store 8's raised fist): a CLENCHED BALL -- a round palm core, four curled fingers as a row of knuckle rolls
    across its front-top (toward `facing`, the camera side), a thumb lying across under them. d = forearm direction."""
    R = K.frame_from(d, facing)                 # y = d (toward the knuckles), z = facing
    ex, ey, ez = R[:, 0], R[:, 1], R[:, 2]
    c = np.asarray(wrist, float) + ey * r * 0.95
    parts = [K.local_ellipsoid((r * 0.98, r * 0.95, r * 0.86), R, c)]
    for i, t in enumerate((-1.5, -0.5, 0.5, 1.5)):
        fc = c + ex * t * r * 0.40 + ey * r * 0.52 + ez * r * 0.42
        parts.append(K.local_ellipsoid((r * 0.24, r * 0.36, r * 0.34), R, fc))
    tb = c - ex * r * 0.55 + ez * r * 0.62 - ey * r * 0.10
    parts.append(capsule(tuple(tb), tuple(c + ex * r * 0.20 + ez * r * 0.70 + ey * r * 0.12), r * 0.22))
    return union(*parts, k=r * 0.22)


def arms_world(Rt, tt, side, variant="console", ks=1.0, narrow=1.0, elbow_x=(1.00, 1.10), wrist_x=(0.96, 1.16), dx=0.0,
               short=False, pts=None):
    """A coat sleeve from the shoulder down to the console, cuff, furry mitt resting palm-down on the console top.
    Rt, tt: torso space -> world. side -1 = screen left. variant "point": the store-7 gesture -- forearm up, a fist
    with the index finger pointing up."""
    neck_t = np.array([0.0, 1.62, -0.06])
    sh = ((np.array([side * 0.74 * narrow, 1.28, -0.14]) - neck_t) * np.asarray(ks, float) + neck_t) @ Rt.T + tt
    if pts is not None:
        # r3 loading: explicit WORLD elbow / wrist (store 8 measured about the eye line); a short rolled sleeve over
        # the upper arm, bare fur forearm into the hand (fist ball / an arrow-holding grip)
        el, wr = (np.asarray(v, float) for v in pts[:2])
        de = K.unit(wr - el)
        if variant == "fist":
            hand = fist_ball(wr, K.unit(pts[2]), K.unit(pts[3]), r=pts[4])
        else:
            hand = K.hand(wr + de * 0.03, K.unit(pts[2]), K.unit(pts[3]), r=pts[4], fingers=4, finger_len=0.95,
                          finger_r=0.42, spread=14, curl=95, thumb_side=-side, thumb_angle=45)
        send = el + de * 0.10
        sleeve = K.limb([sh, el, send], [0.27, 0.25, 0.24], k=0.10)
        cuff = round_cone(tuple(send - de * 0.11), tuple(send + de * 0.03), 0.265, 0.255)
        forearm = K.limb([el + de * 0.02, wr], [0.175, 0.160], k=0.05)
        return dict(sleeve=sleeve, cuff=cuff, hand=union(forearm, hand, k=0.05), shoulder=sh)
    if variant in ("fist", "hold") and short:
        # director round 2 (V1 t=0): a SHORT rolled coat sleeve over the upper arm, the forearm bare fur (it joins the
        # hand part, so it gets the skin + fur), a thick rolled cuff just below the elbow
        if variant == "fist":        # V1: the fist up at chin level beside the face, the forearm rising toward the camera
            el = sh + np.array([side * 0.34, -0.30, 0.22])
            wr = sh + np.array([side * 0.14, 0.18, 0.66])
            palm = K.unit([-side * 0.45, 0.0, 1.0])
            hand = K.hand(wr + K.unit(wr - el) * 0.03, K.unit(wr - el), palm, r=0.175, fingers=4, finger_len=0.60,
                          finger_r=0.46, spread=18, curl=160, thumb_side=-side, thumb_angle=80)
        else:                        # wrapping a bundle of arrows against the belly
            el = sh + np.array([side * 0.36, -0.46, 0.12])
            wr = sh + np.array([side * -0.10, -0.40, 0.72])
            hand = K.hand(wr + K.unit(wr - el) * 0.03, K.unit(wr - el), K.unit([0.0, 0.3, 1.0]), r=0.18, fingers=4,
                          finger_len=0.85, finger_r=0.42, spread=16, curl=80, thumb_side=-side, thumb_angle=50)
        de = K.unit(wr - el)
        send = el + de * 0.10
        sleeve = K.limb([sh, el, send], [0.24, 0.225, 0.22], k=0.10)
        cuff = round_cone(tuple(send - de * 0.10), tuple(send + de * 0.03), 0.245, 0.235)
        forearm = K.limb([el + de * 0.02, wr], [0.165, 0.150], k=0.05)
        return dict(sleeve=sleeve, cuff=cuff, hand=union(forearm, hand, k=0.05), shoulder=sh)
    if variant == "fist":
        # store 8: the fist punched forward-up beside the head, toward the camera
        el = sh + np.array([side * 0.42, -0.18, 0.35])
        wr = sh + np.array([side * 0.30, 0.30, 0.85])
        sleeve = K.limb([sh, el, wr], [0.24, 0.22, 0.195], k=0.10)
        d = K.unit(wr - el)
        cuff = round_cone(tuple(wr - d * 0.09), tuple(wr + d * 0.01), 0.20, 0.205)
        fist = K.hand(wr + d * 0.03, d, K.unit([-side * 0.3, 0.2, 1.0]), r=0.20, fingers=4, finger_len=0.62,
                      finger_r=0.46, spread=20, curl=150, thumb_side=-side, thumb_angle=80)
        return dict(sleeve=sleeve, cuff=cuff, hand=fist, shoulder=sh)
    if variant == "hold":
        # store 8: the other arm wraps a bundle of arrows against the belly
        el = sh + np.array([side * 0.36, -0.46, 0.12])
        wr = sh + np.array([side * -0.10, -0.40, 0.72])
        sleeve = K.limb([sh, el, wr], [0.24, 0.22, 0.195], k=0.10)
        d = K.unit(wr - el)
        cuff = round_cone(tuple(wr - d * 0.09), tuple(wr + d * 0.01), 0.20, 0.205)
        hand = K.hand(wr + d * 0.03, d, K.unit([0.0, 0.3, 1.0]), r=0.18, fingers=4, finger_len=0.85, finger_r=0.42,
                      spread=16, curl=80, thumb_side=-side, thumb_angle=50)
        return dict(sleeve=sleeve, cuff=cuff, hand=hand, shoulder=sh)
    if variant == "point":
        el = np.array([side * 1.10 * narrow + dx, 1.02, 0.10])
        wr = np.array([side * 1.16 * narrow + dx, 1.50, 0.26])
        sleeve = K.limb([sh, el, wr], [0.24, 0.22, 0.195], k=0.10)
        d = K.unit(wr - el)
        cuff = round_cone(tuple(wr - d * 0.09), tuple(wr + d * 0.01), 0.20, 0.205)
        fist = K.hand(wr + d * 0.03, d, K.unit([-side * 0.6, 0.0, 1.0]), r=0.165, fingers=3, finger_len=0.6,
                      finger_r=0.46, spread=22, curl=150, thumb_side=-side, thumb_angle=80)
        tipb = wr + d * 0.03 + d * 0.165 * 1.35 + np.array([-side * 0.06, 0, 0.07])
        index = K.limb([tipb, tipb + np.array([-side * 0.01, 0.15, 0.0]), tipb + np.array([-side * 0.025, 0.29, -0.02])],
                       [0.058, 0.054, 0.048], k=0.02)
        return dict(sleeve=sleeve, cuff=cuff, hand=union(fist, index, k=0.03), shoulder=sh)
    # console variant: elbow / wrist are WORLD points (x before the pose's body_dx, which `dx` adds; tt already has it)
    wr = np.array([side * wrist_x[0 if side < 0 else 1] + dx, CONSOLE_Y + 0.24, 0.50])
    el = np.array([side * elbow_x[0 if side < 0 else 1] + dx, 1.02, -0.06])
    sleeve = K.limb([sh, el, wr], [0.24, 0.22, 0.195], k=0.10)
    d = K.unit(wr - el)
    cuff = round_cone(tuple(wr - d * 0.09), tuple(wr + d * 0.01), 0.20, 0.205)
    hand = K.hand(wr + d * 0.03, K.unit([-side * 0.55, -0.30, 1.0]), [0, -1.0, 0.15], r=0.17, fingers=4,
                  finger_len=0.85, finger_r=0.42, spread=18, curl=34, thumb_side=-side, thumb_angle=58)
    return dict(sleeve=sleeve, cuff=cuff, hand=hand, shoulder=sh)


def hand_fur(name, hand_sdf, view_w, field, key, n=5000, seed=7, stops=None):
    def fn():
        rng = np.random.default_rng(seed)
        v, f, nn = FUR.surface(hand_sdf, 0.008, key=key)
        P, N = FUR.sample(v, f, nn, n, rng)
        comb = np.tile([[0.0, -0.2, 1.0]], (len(P), 1))
        L = 0.030 * (0.8 + 0.4 * rng.random(len(P)))
        V, Fc, NR, T, ri = FUR.strands(P, N, comb, L, 0.35, 0.0062, view_w, rng, segs=3, clump=0.45, clump_size=0.03,
                                       per_clump=14, jitter=0.2, nbend=0.15)
        uv = FUR.tone_uv(field, None, T, ri, P, rng.normal(0, 0.06, len(P)), tone0=0.40, tone_gain=0.55, N=N, under=0.25)
        return V, Fc, NR, uv
    return FUR.fur_part(name, FUR.fur_material("s_fur", None, stops=stops or FUR_STOPS, rough=0.60), fn)


ANCHORS = {}


def pose_anchors(pose):
    """World anchor points of a pose (computed without meshing)."""
    P = POSES[pose]
    Rt = rot((1, 0, 0), P["lean"]) @ rot((0, 1, 0), P["yaw"])
    pivot = np.array([0.0, 0.2, -0.1])
    tt = pivot - Rt @ pivot + np.array([0.0, -0.06, 0.0])
    H = P["head"]
    Rh = rot((0, 0, 1), H["roll"]) @ rot((0, 1, 0), H["yaw"]) @ rot((1, 0, 0), H["nod"])
    if P.get("head_scale"):
        Rh = Rh @ np.diag(P["head_scale"])
    th = np.array([0.0, HEAD_Y, 0.14]) + (Rt @ np.array([0, 1.55, 0]) + tt - np.array([0, 1.55, 0])) * np.array([1, 0, 1])
    tb, n_ = tt + np.array([P.get("body_dx", 0.0), P.get("body_dy", 0.0), 0.0]), P.get("narrow", 1.0)
    return dict(eyeMid=(Rh @ np.array([0.0, 0.79, 0.52]) + th).tolist(), neck=(Rh @ np.array([0.0, 0.25, 0.0]) + th).tolist(),
                shoulderL=(np.array([-0.74 * n_, 1.28, -0.14]) @ Rt.T + tb).tolist(),
                shoulderR=(np.array([0.74 * n_, 1.28, -0.14]) @ Rt.T + tb).tolist())


def scientist(pose="home", mouth="smile", n_strands=40000, only=None, eyes="open", armR="console", armL="console",
              view_pose=None, look=(0.14, -0.40)):
    """All parts in world space (before ui3d's view pose). only: a set of part names to build (layers)."""
    P = POSES[pose]
    vp = view_pose or HOME_POSE
    view_w = _view_dir(dict(yaw=vp["yaw"], pitch=vp["pitch"]))
    Rt = rot((1, 0, 0), P["lean"]) @ rot((0, 1, 0), P["yaw"])
    pivot = np.array([0.0, 0.2, -0.1])
    tt = pivot - Rt @ pivot + np.array([0.0, -0.06, 0.0])

    ks = P.get("body_scale", 1.0)
    neck_t = np.array([0.0, 1.62, -0.06])
    dx, n_ = P.get("body_dx", 0.0), P.get("narrow", 1.0)
    tb = tt + np.array([dx, P.get("body_dy", 0.0), 0.0])   # the body (torso + arms) under the head; the head keeps tt

    style = P.get("style", "home")
    PAL = pal(style)

    def tw(s):   # torso space -> world (optionally scaled about the neck: the running pose's torso is smaller)
        if isinstance(ks, (tuple, list)):          # r3: a squat, wide torso (x, y, z scales)
            s = s.translate(*(-neck_t)).scale_xyz(*ks).translate(*neck_t)
        elif ks != 1.0:
            s = s.translate(*(-neck_t)).scale(ks).translate(*neck_t)
        return s.transform(Rt).translate(*tb)
    T = torso_space(n_)
    coatm = K.skin("s_coat", COAT, None, vfn=None, rough=0.66, ior=1.22)
    shirtm = (K.skin("s_shirtW", SHIRT_WHITE, None, vfn=None, rough=0.7, ior=1.2) if P.get("shirt") == "white"
              else K.skin("s_shirt", SHIRT, None, vfn=None, rough=0.7, ior=1.2))
    body = [Part("coat", tw(T["coat"]), coatm, voxel=0.008), Part("facing", tw(T["facing"]), coatm, voxel=0.006),
            Part("collar", tw(T["collar"]), coatm, voxel=0.006),
            Part("shirt", tw(T["torso"]), shirtm, voxel=0.008),
            Part("band", tw(T["band"]), satin("s_band", NECKBAND, rough=0.7), voxel=0.005),
            Part("lanyard", tw(T["lanyard"]), satin("s_lanyard", LANYARD, rough=0.55), voxel=0.003),
            Part("badge", tw(T["badge"]), gloss("s_badge", BADGE, rough=0.3), voxel=0.003),
            Part("photo", tw(T["photo"]), gloss("s_photo", BADGE_PHOTO, rough=0.35), voxel=0.0025),
            Part("clip", tw(T["clip"]), gloss("s_clip", BADGE_CLIP, rough=0.3), voxel=0.003),
            Part("pocket", tw(T["pocket"]), coatm, voxel=0.005),
            Part("pen", tw(T["pen"]), gloss("s_pen", PEN, rough=0.3), voxel=0.003),
            Part("pencap", tw(T["cap"]), gloss("s_pencap", PEN_CAP, rough=0.3), voxel=0.003),
            Part("penclip", tw(T["penclip"]), metal("s_penclip", "#D8DCE8"), voxel=0.002)]
    if P.get("plain_front"):     # r3 (store 8): no lanyard / badge / pocket / pen on the running scientist's shirt
        body = [b_ for b_ in body if b_.name not in ("lanyard", "badge", "photo", "clip", "pocket", "pen", "pencap", "penclip")]
    arms = []
    for side, tag in ((-1, "L"), (1, "R")):
        A = arms_world(Rt, tb, side, variant=armR if tag == "R" else armL, ks=ks, narrow=n_, dx=dx,
                       elbow_x=P.get("elbow_x", (1.00, 1.10)), wrist_x=P.get("wrist_x", (0.96, 1.16)),
                       short=P.get("short_sleeves", False), pts=P.get("arm_pts", {}).get(tag))
        sl = A["sleeve"].subtract(tw(T["coat"]).offset(-0.02))
        arms += [Part(f"sleeve{tag}", sl, coatm, voxel=0.008), Part(f"cuff{tag}", A["cuff"], coatm, voxel=0.006),
                 Part(f"hand{tag}", A["hand"], K.skin("s_skin", PAL["skin"], None, vfn=None, rough=0.72, ior=1.2), voxel=0.005)]
    if P.get("leg"):
        # r3 (store 8): the far leg kicked back at the lower right -- a furry thigh + shin out of the trousers
        hip, knee, ank = (np.asarray(v, float) for v in P["leg"])
        legsdf = K.limb([hip, knee, ank], [0.24, 0.22, 0.20], k=0.06)
        arms.append(Part("handLeg", legsdf, K.skin("s_skin", PAL["skin"], None, vfn=None, rough=0.72, ior=1.2), voxel=0.006))
    H = P["head"]
    Rh = rot((0, 0, 1), H["roll"]) @ rot((0, 1, 0), H["yaw"]) @ rot((1, 0, 0), H["nod"])
    if P.get("head_scale"):
        Rh = Rh @ np.diag(P["head_scale"])
    # the head sits on the collar: jowl bottom at HEAD_Y, carried a little forward by the lean
    th = np.array([0.0, HEAD_Y, 0.14]) + (Rt @ np.array([0, 1.55, 0]) + tt - np.array([0, 1.55, 0])) * np.array([1, 0, 1])
    field_parts = body + arms
    if P.get("lower"):
        # store 8: brown belt with a grey buckle, blue trousers under the coat
        pants = union(ellipsoid(0.92, 0.42, 0.60).translate(0, 0.30, -0.10), k=0.1)
        belt = T["torso"].offset(0.06).intersect(box(1.6, 0.07, 1.6).translate(0, 0.46, 0), k=0.01)
        bz = K.surface_z_of(T["torso"], -0.05, 0.46) + 0.07
        buckle = box(0.12, 0.085, 0.02, round=0.02).subtract(box(0.07, 0.04, 0.1, round=0.01)).translate(-0.05, 0.46, bz)
        body += [Part("pants", tw(pants), K.skin("s_pants", PANTS, None, vfn=None, rough=0.66, ior=1.22), voxel=0.008),
                 Part("belt", tw(belt), K.skin("s_belt", BELT, None, vfn=None, rough=0.5, ior=1.25), voxel=0.005),
                 Part("buckle", tw(buckle), metal("s_buckle", "#9EA2B4", rough=0.3), voxel=0.003)]
    for i, (col, c, up, fc, shp) in enumerate(P.get("arrows", [])):
        import char_props as CP
        body.append(Part(f"arrow{i}", CP.place(CP.arrow_sdf(**shp), c, up, fc), CP.arrow_mat(col), voxel=0.006))
    head = head_parts_xf(Rh, th, view_w, mouth=mouth, n_strands=n_strands, extra_field=field_parts,
                         field_key=("sci", pose, mouth, armR, armL), eyes=eyes, look=look, style=style)
    ANCHORS[pose] = dict(eyeMid=(Rh @ np.array([0.0, 0.79, 0.52]) + th).tolist(),
                         neck=(Rh @ np.array([0.0, 0.25, 0.0]) + th).tolist(),
                         shoulderL=(np.array([-0.74 * n_, 1.28, -0.14]) @ Rt.T + tb).tolist(),
                         shoulderR=(np.array([0.74 * n_, 1.28, -0.14]) @ Rt.T + tb).tolist())
    fld = K.field_for(("sci", pose, mouth, armR, armL), [])
    K.shade(body + arms, field=fld)
    for side, tag in ((-1, "L"), (1, "R")) + (((0, "Leg"),) if P.get("leg") else ()):
        hp = [p for p in arms if p.name == f"hand{tag}"][0]
        arms.append(hand_fur(f"handfur{tag}", hp.sdf, view_w, fld, ("sci_hand", pose, tag, armR if tag == "R" else "",
                                                                     "short" if P.get("short_sleeves") else ""),
                             n=11000 if P.get("short_sleeves") else 5000, seed=7 + side,
                             stops=PAL["fur"] if style != "home" else None))
    parts = body + arms + head
    if only is not None:
        parts = [p for p in parts if p.name in only]
    return parts, VOXEL


# ------------------------------------------------------------------ home composition
# The visible scientist on 002 spans x 390..875 px, y 525..900 px (x 130..292 pt, y 175..300 pt; the console top
# hides everything below y ~297 pt). The frame keeps the torso down to y 330 pt so it continues behind the console.
HOME_POSE = dict(yaw=0, pitch=8, center=False)
HOME_FRAME = (190, 164)
HOME_VIEW = K.view_bounds(HOME_FRAME, scale_pt=SCALE_PT, center=(0.02, 1.32), zr=(-1.0, 1.2), margin=1.0)

# ------------------------------------------------------------------ spike cases (head only, home game size)

SPIKE_POSE = dict(yaw=0, pitch=6, center=False)
SPIKE_FRAME = (104, 92)
SPIKE_VIEW = K.view_bounds(SPIKE_FRAME, scale_pt=SCALE_PT, center=(0.0, HEAD_Y + 0.60), zr=(-0.8, 0.9), margin=1.0)

MODELS = {
    "sci_head_strands": lambda: head_model(SPIKE_POSE),
    "sci_home_full": lambda: scientist("home"),
    "sci_home_var": lambda: scientist("home", mouth="open", eyes="half", armR="point"),
}
_sp = dict(bounds=SPIKE_VIEW, frame=SPIKE_FRAME, fov=18, light=K.light(), no_fit=True)
ASSETS = {
    "char_sci_spikeB": dict(scene=[("sci_head_strands", SPIKE_POSE)], dest="route3d", **_sp),
    "char_sci_homeVar": dict(scene=[("sci_home_var", HOME_POSE)], dest="route3d", bounds=HOME_VIEW, frame=HOME_FRAME,
                             fov=18, light=K.light(), no_fit=True),
    "char_sci_homeDraft": dict(scene=[("sci_home_full", HOME_POSE)], dest="route3d", bounds=HOME_VIEW, frame=HOME_FRAME,
                               fov=18, light=K.light(), no_fit=True,
                               anchors={"eyeMid": [pose_anchors("home")["eyeMid"]], "consoleMid": [[0.0, CONSOLE_Y, 0.62]]}),
}


# ------------------------------------------------------------------ the home rig (cut-out puppet)
TORSO_PARTS = {"coat", "facing", "collar", "shirt", "band", "lanyard", "badge", "photo", "clip", "pocket", "pen", "pencap",
               "penclip"}
HEAD_PARTS = {"skin", "brows", "eyes", "irises", "pupils", "glints", "lipline", "mouth", "teeth", "tongue", "fur", "browfur"}
LID_PARTS = {"lids", "lidcrease", "lidfur"}
ARM_L = {"sleeveL", "cuffL", "handL", "handfurL"}
ARM_R = {"sleeveR", "cuffR", "handR", "handfurR"}
_A = pose_anchors("home")
# ref eye midpoint on 002: eyes (whites) L 571..608 x 600..646, R 624..665 x 607..656 -> (617, 627) px = (205.9, 209.2) pt.
# v6: the eyeMid anchor (a point 0.52 u in front of the head centre) projects ~10 px BELOW our visible eye whites'
# centre (measured on the v6 draft: whites L 569..604 x 592..636, R 627..664 x 599..639 with the anchor on 627), so
# the placement target carries that bias: our whites land on theirs (L 572..607 x 601..644, R 625..664 x 608..653).
EYE_BIAS_PX = 10.0
HOME_EYEMID_PT = (617 * 393 / 1178, (627 + EYE_BIAS_PX) * 393 / 1178)


def _factory(only=None, **kw):
    return scientist("home", only=only, **kw)


RIGS = {"sci_home": dict(K.explicit_rig(
    MODELS, ASSETS, "sci_home", _factory, HOME_FRAME, HOME_VIEW, HOME_POSE, K.light(),
    full_anchors={"eyeMid": _A["eyeMid"], "neck": _A["neck"]},
    layers=[
        dict(name="torso", parts=TORSO_PARTS, note="behind the console; the head and arms sit on it"),
        dict(name="armL", parts=ARM_L, holdout=TORSO_PARTS, pivots={"shoulder": _A["shoulderL"]},
             note="hand rests on the console top (in front of the console body, behind its joystick)"),
        dict(name="armR", parts=ARM_R, holdout=TORSO_PARTS, pivots={"shoulder": _A["shoulderR"]}, group="armR",
             default=True, note="hand rests on the console top (behind the purple lever)"),
        dict(name="armR_point", parts=ARM_R, kw=dict(armR="point"), holdout=TORSO_PARTS,
             pivots={"shoulder": _A["shoulderR"]}, group="armR", note="store-7 gesture: index finger up"),
        dict(name="headSmile", parts=HEAD_PARTS, holdout=TORSO_PARTS, pivots={"neck": _A["neck"]}, group="head",
             default=True, note="closed smile (002)"),
        dict(name="headOpen", parts=HEAD_PARTS, kw=dict(mouth="open"), holdout=TORSO_PARTS, pivots={"neck": _A["neck"]},
             group="head", note="open laugh (store 7)"),
        dict(name="lidsHalf", parts=LID_PARTS, kw=dict(eyes="half"), pivots={"neck": _A["neck"]}, overlay=True,
             parent="head", note="half-closed lids over the eyes (blink in-between)"),
        dict(name="lidsClosed", parts=LID_PARTS, kw=dict(eyes="closed"), pivots={"neck": _A["neck"]}, overlay=True,
             parent="head", note="closed happy eyes (blink / laugh)"),
    ]),
    place=dict(anchor="eyeMid", at=HOME_EYEMID_PT))}


# ------------------------------------------------------------------ comparison sheet (char_make.py sheet sci_home)

def console_mask_002(size):
    """The original's console on 002 (px): everything below its rim arc, plus the joystick, buttons and lever that
    stand on it -- used ONLY by the sheet to put the console back in front of our character (looked at only)."""
    from PIL import Image as _I, ImageDraw as _D
    m = _I.new("L", size, 0)
    d = _D.Draw(m)
    arc = [(x, 888 + 47 * ((x - 590) / 290.0) ** 2) for x in range(290, 892, 6)]
    d.polygon(arc + [(900, 1150), (280, 1150)], fill=255)
    for bx in ((318, 818, 390, 930), (430, 860, 485, 905), (535, 858, 595, 900), (640, 858, 695, 900), (785, 830, 872, 915)):
        d.rounded_rectangle(bx, 10, fill=255)
    return m


def _sheet_home():
    import os as _os
    from PIL import Image as _I
    rig_dir = _os.path.join(K.ART, "out", "char_sci_home_rig")
    box = (300, 470, 960, 1010)
    rows = []
    for shot_rel, names, label in (
            ("research/shots/002-home-L32.png", {"torso", "armL", "armR", "headSmile"}, "home 002 (default: smile, hands on the console)"),
            ("research/store/iphone-7.png", {"torso", "armL", "armR_point", "headOpen"}, "store 7 (open laugh + index up: headOpen + armR_point)")):
        base = K.shot(shot_rel)
        comp, rj = K.layer_composite(rig_dir, names)
        pl = rj["placement_pt"]
        flat = K.on_shot(K.flat_like(base, box), comp, pl["x"], pl["y"])
        ctx = K.on_shot(base, comp, pl["x"], pl["y"])
        ctx = _I.composite(base, ctx, console_mask_002(base.size))
        rows.append((label, [("reference (looked at only)", base.crop(box)), ("ours, same game size", flat.crop(box)),
                             ("ours in context (their console re-pasted in front)", ctx.crop(box))]))
    base = K.shot("research/shots/002-home-L32.png")
    tiles = []
    for names, cap in (({"headSmile"}, "eyes open"), ({"headSmile", "lidsHalf"}, "lidsHalf"),
                       ({"headSmile", "lidsClosed"}, "lidsClosed"), ({"headOpen", "lidsClosed"}, "laugh")):
        comp, rj = K.layer_composite(rig_dir, names)
        pl = rj["placement_pt"]
        t = K.on_shot(K.flat_like(base, box), comp, pl["x"], pl["y"]).crop((420, 480, 820, 800))
        tiles.append((cap, t))
    rows.append(("face swaps (head group + lid overlays)", tiles))
    return rows, "SCIENTIST (pink) vs the original at game size -- 1 phone px = 1 px; 1/3-size reads under each row"


SHEETS = {"sci_home": _sheet_home}
