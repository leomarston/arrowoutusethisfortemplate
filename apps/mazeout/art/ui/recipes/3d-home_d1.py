"""R3 HOME (PLAN-P §4.2; owner items 8, 14, 15; SPEC ruling 46): the home's D1 event badges and bottom-nav icons.

Same composition and job as today's (3d-events_badges.py / 3d-hud_props.py): a badge = a back plate, the event's icon,
a pedestal carrying the live text (countdown / "Join"), a base; the nav = a shop, a home and a trophy icon at the same
frames. Restyled to D1 "Burrow Works" so nothing reads as the original's (gold hexagon + blue drum + gold ring,
chequered flags, red-nosed yellow rocket, pink pad on lilac clouds, orange basket, garage-house, cup with an up-arrow):

  badge base       a round brass-rimmed teal MEDALLION behind a TIMBER drum with a deep-teal text band, on a brass-banded
                   log-slice base
  Hot Streak       two crossed timber poles with PENNANTS (tangerine, coral) carrying a cream flame mark
  Rocket Rally     a teal riveted rocket, tangerine nose + fins, a brass porthole (the live rank is drawn on its glass)
  Cloud Hop        a bounce DRUM (tangerine hide top on brass tacks, teal shell, laced cord, brass tag for the live
                   count) on cream clouds
  navCart          a tangerine mine cart on iron wheels, heaped with star coins
  navLodge         a plank lodge under a steep teal shingle roof, a round tangerine door, a brass-capped chimney
  navCup           a gold cup with a teal star emblem on a timber plinth

The badges are exported AS LAYERS (owner item 8, motion-catalog §6.4 / §11.5): art/out/badge_<event>_rig/ with one
shared camera (explicit bounds, no_fit, center=False): body + the moving part (+ the painted smoke / flame layers added by
art/review/tools/r3_home.py badges). The full renders are also written as art/ui/out/badge<Event>@3x.png (80 x 84 pt,
the old eventBadge* frame) so a static fallback / preload exists. Live-text anchors kept from today's badges: pedestal
text centre x 40.6, baseline ~71; the rank on the rocket's porthole (baseline 39); the count on the drum's tag
(baseline 40.5): measured on the renders and written to the handoff.

    PY=~/.venvs/mf3d/bin/python
    $PY art/ui/tools/ui3d.py navCart navLodge navCup
    $PY art/ui/tools/rig.py badge_hotstreak badge_rocketrally badge_cloudhop       # layers + rig.json (+ the full PNGs)
Units: badges 1 u = 40 pt (P(pt)), ring bottom at y = 0, x centred; nav icons ~1 u across (like 3d-hud_props).
"""
from __future__ import annotations

import importlib.util
import math
import os

import numpy as np

from uikit import (F, SDF, SDF2, Part, box, capped_cone, capsule, circle2, cylinder, ellipsoid, extrude, gloss, glass,  # noqa: F401
                   path_tube, polygon2, rect2, revolve, round_cone, satin, sphere, spline_profile, star2, torus, union,
                   fillet_points)
from mesher import Material
from uikit import intersect2

_HERE = os.path.dirname(os.path.abspath(__file__))


def _mod(fname, alias):
    spec = importlib.util.spec_from_file_location(alias, os.path.join(_HERE, fname))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


HUD = _mod("3d-hud_props.py", "r3_hud_props")          # tpart / toon ramps / coins / Rx..Rz / the nav post-grade
tpart, coin_part, Rx, Ry, Rz, star_shape, xform = HUD.tpart, HUD.coin_part, HUD.Rx, HUD.Ry, HUD.Rz, HUD.star_shape, HUD.xform

VOXEL = 0.0055
PT = 1.0 / 40.0


def P(x):
    return x * PT


# D1 toon schemes (face top/mid/bottom, edge top/bottom): art-direction §3.1 palette
D1 = {
    "teal": dict(top="#3FD0BF", mid="#17B3A3", bot="#0F9A8C", etop="#0B8A83", ebot="#075E5E"),
    "tealDeep": dict(top="#177A74", mid="#0E6560", bot="#0A5450", etop="#084844", ebot="#053634"),
    "timber": dict(top="#F2C586", mid="#E0A862", bot="#C98A4A", etop="#B97A3E", ebot="#7E4E27"),
    "timberDark": dict(top="#C98A4A", mid="#A86C34", bot="#8E5A2F", etop="#7E4E27", ebot="#5E3718"),
    "brass": dict(top="#FFE39A", mid="#E8B85A", bot="#D49A3A", etop="#C08A2E", ebot="#7E5510"),
    "gold": dict(top="#FFE66A", mid="#FFC82E", bot="#F5A816", etop="#E8980E", ebot="#B86A04"),
    "tangerine": dict(top="#FFC46A", mid="#FF9A12", bot="#F08A0A", etop="#E27608", ebot="#A84E00"),
    "coral": dict(top="#FF9C86", mid="#F2553F", bot="#E04430", etop="#D23A26", ebot="#9A2414"),
    "sunflower": dict(top="#FFE88A", mid="#FFCB2F", bot="#F5B81A", etop="#EDA80E", ebot="#B77C04"),
    "cream": dict(top="#FFFBEF", mid="#FFF3DF", bot="#F6E4C6", etop="#EAD2AE", ebot="#C9A878"),
    "cloud": dict(top="#FFFFFF", mid="#FDF4E4", bot="#F0DFC4", etop="#E8D2B2", ebot="#C8AC86"),
    "iron": dict(top="#8A919A", mid="#5A5F66", bot="#4B4F55", etop="#3E4247", ebot="#26292C"),
    "glass": dict(top="#2E7C78", mid="#145652", bot="#0E4744", etop="#0B3C39", ebot="#062624"),
}
HUD.SCHEMES.update({f"d1_{k}": v for k, v in D1.items()})


def T(name, sdf, scheme, y0, y1, view=(0, 0, 0), **kw):
    return tpart(name, sdf, f"d1_{scheme}", y0, y1, view, **kw)


BADGE_VIEW = (0, 8, 0)               # seen ~8 deg from above (the drum's text band faces the viewer)
BADGE_FRAME = (80, 84)
BADGE_LIGHT = dict(fill_color=(1.0, 0.88, 0.70), fill_lux=560.0, key_lux=3000.0, ibl_exp=-0.7)


def _bounds(frame, scale_pt, center, zr=(-1.0, 1.0), margin=1.0, fov=14.0):
    """char_kit.view_bounds (same maths): explicit bounds so the render maps scale_pt pt / u at the middle depth."""
    fw, fh = frame
    z0, z1 = zr
    zf = (z0 + z1) / 2
    t = math.tan(math.radians(fov) / 2)
    half_h = fh / (2 * scale_pt) - t * (z1 - zf)
    ext_y = 2 * (half_h - 0.02) / margin
    ext_x = ext_y * fw / fh
    cx, cy = center
    return ((cx - ext_x / 2, cy - ext_y / 2, z0), (cx + ext_x / 2, cy + ext_y / 2, z1))


# ------------------------------------------------------------------ the badge base (pt; ring bottom at y = 0)

MED_CY = 50.0          # medallion centre height
MED_R = 26.5           # medallion radius
MED_Z = -13.0


def _medallion_tex():
    """The medallion face: a teal sunburst (rays) with a darker rim ring, painted (planar uv over the disc)."""
    c0, c1, c2 = np.array([0x1E, 0xB9, 0xA8]) / 255, np.array([0x12, 0x96, 0x8A]) / 255, np.array([0x0A, 0x62, 0x5E]) / 255

    def fn(u, v):
        x, y = (u - 0.5) * 2, (v - 0.5) * 2
        r = np.sqrt(x * x + y * y)
        a = np.arctan2(y, x)
        ray = (0.5 + 0.5 * np.cos(a * 12)) ** 3
        col = c0[None, None] * (1 - ray[..., None] * 0.35) + c1[None, None] * ray[..., None] * 0.35
        col = col * (1 - np.clip((r - 0.55) / 0.45, 0, 1)[..., None] * 0.45) + c2[None, None] * np.clip((r - 0.55) / 0.45, 0, 1)[..., None] * 0.45
        return col
    return fn


def base_parts(view=BADGE_VIEW):
    from dataclasses import replace
    # the log-slice base with a brass hoop, the timber drum, the deep-teal text band, the medallion (brass rim + face)
    # the live text sits on the band: centre 16.5 pt up the drum -> ~66.5 pt from the frame top (baseline ~71)
    base = cylinder(P(28.5), P(2.3), round=P(2.0)).translate(0, P(2.3), 0)
    hoop = torus(P(28.6), P(1.2)).translate(0, P(2.4), 0)
    drum = cylinder(P(25.6), P(9.9), round=P(2.4)).translate(0, P(4.2 + 9.9), 0)
    band = cylinder(P(26.1), P(4.6), round=P(1.2)).translate(0, P(16.5), 0)
    rim = torus(P(MED_R - 2.2), P(3.0)).rotate_x(90).translate(0, P(MED_CY), P(MED_Z))
    face = cylinder(P(MED_R - 3.0), P(1.2), round=P(0.8)).rotate_x(90).translate(0, P(MED_CY), P(MED_Z - 0.6))
    rivets = union(*[sphere(P(1.25), center=(P((MED_R - 2.2) * math.cos(a)), P(MED_CY + (MED_R - 2.2) * math.sin(a)), P(MED_Z + 2.6)))
                     for a in np.linspace(0, 2 * math.pi, 13)[:-1] + 0.26])
    lo = P(MED_CY - MED_R); span = P(2 * MED_R)
    face_m = replace(gloss("med_face", "#17B3A3", rough=0.40, ior=1.28), texture=_medallion_tex(), texture_size=256)
    face_uv = ("planar", (P(-MED_R), lo, 0.0), (1.0 / span, 0, 0), (0, 1.0 / span, 0), 1.0)
    return [
        T("base", base, "timberDark", 0.0, P(4.6), view),
        T("hoop", hoop, "brass", 0.0, P(4.6), view, voxel=0.004),
        T("drum", drum, "timber", P(4.2), P(24.0), view),
        T("band", band, "tealDeep", P(11.9), P(21.1), view),
        T("medRim", rim, "brass", lo, lo + span, view, voxel=0.0045),
        Part("medFace", face, face_m, uv=face_uv),
        T("medRivets", rivets, "iron", lo, lo + span, view, voxel=0.0035),
    ]


BASE = {"base", "hoop", "drum", "band", "medRim", "medFace", "medRivets"}


# ------------------------------------------------------------------ Hot Streak: crossed poles + pennants

def _flame_tex(col_face, col_mark=(0xFF, 0xF6, 0xE4)):
    """A pennant face with a cream flame mark near the pole (u outward 0..1, v down the pole -1..0)."""
    cf = np.array(col_face) / 255
    cm = np.array(col_mark) / 255

    def fn(u, v):
        uu, vv = np.clip(u, 0, 1), np.clip(1.0 - v, 0, 1)      # the sampler wraps the cloth's v (-1..0) into 0..1
        # flame: a teardrop centred at (0.32, 0.5) pointing up (toward v 0)
        x, y = (uu - 0.30) / 0.16, (vv - 0.52) / 0.24
        d = np.sqrt(x * x + np.maximum(y, 0) ** 2 * 1.0) - (1 - np.clip(-y, 0, 1.2) * 0.75)
        m = np.clip(-d / 0.12, 0, 1)
        inner = np.clip(-(np.sqrt((x * 1.6) ** 2 + (np.maximum(y - 0.25, 0) * 1.6) ** 2) - (0.6 - np.clip(-(y - 0.25), 0, 1) * 0.5)) / 0.12, 0, 1)
        col = cf[None, None] * (1 - m[..., None]) + cm[None, None] * m[..., None]
        col = col * (1 - inner[..., None] * 0.6) + np.array([1.0, 0.78, 0.30])[None, None] * inner[..., None] * 0.6
        # a darker hem along the pennant's edges
        hem = np.clip(1 - np.minimum(uu, 1 - uu * 0.98) / 0.06, 0, 1) * 0.0
        return col * (1 - hem[..., None] * 0.25)
    return fn


def pennant_part(name, top, bottom, side, color, length=34.0, height=26.0, wave=4.0, slope=10.0):
    """A cloth pennant (a triangle tapering away from the pole) near `top` (pt), flying to `side`."""
    from dataclasses import replace
    top = np.array(top, float); bottom = np.array(bottom, float)
    up = top - bottom; up /= np.linalg.norm(up)
    out = np.array([up[1], -up[0], 0.0]) * side
    if out[0] * side < 0:
        out = -out
    rot = math.radians(slope * side)
    out = out * math.cos(rot) + up * math.sin(rot)
    out /= np.linalg.norm(out)
    t = 1.8
    L, Hh = length, height

    def local(p):
        q = p - top
        x = q @ out; y = q @ up; z = q[:, 2] - 1.5
        z = z - wave * np.sin(x / L * math.pi * 1.5) * np.clip(x / 6, 0, 1)
        # triangle: x in [0, L], |y + Hh/2| <= (Hh/2) * (1 - x / L) (a rounded tip)
        hw = (Hh / 2) * np.clip(1 - x / L, 0.05, 1)
        dy = np.abs(y + Hh / 2) - hw
        dx = np.maximum(-x, x - L)
        d2 = np.maximum(dx, dy * 0.92)
        return np.maximum(d2, np.abs(z) - t / 2) * 0.75
    lo = np.minimum(top, top + out * L - up * Hh) - 8
    hi = np.maximum(top, top + out * L - up * Hh) + 8
    lo = np.minimum(lo, top - up * Hh - 8); hi = np.maximum(hi, top + out * L + 8)

    def fn(p):
        q = p / PT
        return (local(q) * PT).astype(F)
    s = SDF(fn, np.r_[lo[:2], -8] * PT, np.r_[hi[:2], 8] * PT).offset(P(0.6))
    uv = ("planar", tuple((top * PT).tolist()), tuple((out / (L * PT)).tolist()), tuple((up / (Hh * PT)).tolist()), 1.0)
    return Part(name, s, replace(satin(f"pen_{name}", "#FF9A12", rough=0.45, ior=1.25), texture=_flame_tex(color), texture_size=256),
                uv=uv, voxel=0.0045)


STREAK_POLES = dict(L=((-12.0, 74.0, 1.0), (4.0, 28.0, 1.0)), R=((12.5, 74.0, -1.0), (-6.5, 28.0, -1.0)))


def streak_parts(view=BADGE_VIEW):
    (lt, lb), (rt, rb) = STREAK_POLES["L"], STREAK_POLES["R"]
    poles = union(capsule(tuple(P(v) for v in lt), tuple(P(v) for v in lb), P(3.1)),
                  capsule(tuple(P(v) for v in rt), tuple(P(v) for v in rb), P(3.1)))
    knobs = union(sphere(P(3.6), tuple(P(v) for v in lt)), sphere(P(3.6), tuple(P(v) for v in rt)))
    cross = (-1.0, 44.5, 0.2)
    wrap = cylinder(P(5.0), P(2.6), round=P(1.2)).rotate_z(8).translate(*[P(v) for v in cross])
    # tips stay inside the 80-pt frame (x +-40 at the badge camera's 38.8 pt / u): 27 pt pennants from x +-11.5
    pl = pennant_part("pennantL", (-11.2, 69.0, 3.4), lb, -1, (0xFF, 0x9A, 0x12), length=27.0, height=25.0, wave=3.6, slope=14.0)
    pr = pennant_part("pennantR", (11.8, 69.0, 1.4), rb, +1, (0xF2, 0x55, 0x3F), length=27.0, height=25.0, wave=3.6, slope=10.0)
    return [T("poles", poles, "timber", P(28), P(76), view, voxel=0.0045), T("knobs", knobs, "brass", P(70), P(78), view, voxel=0.004),
            T("wrap", wrap, "iron", P(40), P(49), view), pl, pr]


def badge_streak():
    return base_parts() + streak_parts(), VOXEL


# ------------------------------------------------------------------ Rocket Rally

ROCKET_BASE_Y = 24.0       # nozzle bottom (the drum top)
PORT_Y = 52.2              # porthole centre (pt above the base bottom): the live rank's place (baseline 39 in-frame)


def rocket_parts(view=BADGE_VIEW):
    y0 = ROCKET_BASE_Y + 3.0
    prof = spline_profile([(0, y0), (9.8, y0), (12.4, y0 + 5.0), (13.4, y0 + 13.0), (13.0, y0 + 22.0), (11.2, y0 + 30.0),
                           (8.0, y0 + 37.0), (4.2, y0 + 42.0), (1.2, y0 + 45.5), (0.0, y0 + 46.3)], samples=120)
    body = revolve(prof).scale(PT).translate(0, 0, P(-2.0))
    big = P(200)
    nose = body.offset(P(0.4)).intersect(box(big, big, big).translate(0, P(y0 + 33.0) + big, 0), k=P(0.5))
    bandc = body.offset(P(0.45)).intersect(box(big, P(2.2), big).translate(0, P(y0 + 9.0), 0), k=P(0.4))
    fin2 = polygon2([(P(10.5), P(y0 + 17.0)), (P(15.5), P(y0 + 13.0)), (P(20.5), P(y0 + 5.0)), (P(21.5), P(y0 - 2.5)),
                     (P(17.0), P(y0 - 1.5)), (P(11.0), P(y0 + 2.5))]).offset(P(1.1))
    fin = extrude(fin2, P(2.0), round=P(1.7)).translate(0, 0, P(-2.0))
    fins = union(fin, fin.transform(np.diag([-1.0, 1.0, 1.0])))
    ffin = box(P(1.6), P(8.0), P(5.0), round=P(1.4)).translate(0, P(y0 + 2.5), P(-2.0 + 13.0))
    nozzle = capped_cone(P(3.6), P(8.6), P(9.4), round=P(1.2)).translate(0, P(y0 - 1.6), P(-2.0))
    zf = P(-2.0 + 12.9)
    ring = torus(P(7.2), P(2.3)).rotate_x(90).scale_xyz(1, 1, 0.8).translate(0, P(PORT_Y), zf + P(0.6))
    glass_ = ellipsoid(P(5.8), P(5.8), P(2.4)).translate(0, P(PORT_Y), zf + P(0.4))
    rivets = union(*[sphere(P(0.9), center=(P(12.6 * math.sin(a)), P(y0 + 9.0 + 2.6), P(-2.0) + P(12.6 * math.cos(a))))
                     for a in np.linspace(-1.2, 1.2, 7)])
    return [
        T("rkBody", body, "teal", P(y0), P(y0 + 46), view),
        T("rkNose", nose, "tangerine", P(y0 + 33), P(y0 + 47), view),
        T("rkBand", bandc, "brass", P(y0 + 7), P(y0 + 11), view, voxel=0.004),
        T("rkRivets", rivets, "iron", P(y0 + 7), P(y0 + 14), view, voxel=0.0035),
        T("rkFins", union(fins, ffin), "tangerine", P(y0 - 3), P(y0 + 18), view),
        T("rkNozzle", nozzle, "iron", P(y0 - 6), P(y0 + 2), view),
        T("rkRing", ring, "brass", P(PORT_Y - 9), P(PORT_Y + 9), view, voxel=0.004),
        T("rkGlass", glass_, "glass", P(PORT_Y - 6), P(PORT_Y + 6), view, voxel=0.004),
    ]


ROCKET = {"rkBody", "rkNose", "rkBand", "rkRivets", "rkFins", "rkNozzle", "rkRing", "rkGlass"}


def badge_rocket():
    return base_parts() + rocket_parts(), VOXEL


# ------------------------------------------------------------------ Cloud Hop: the bounce drum on clouds

SKY_CY = 51.6              # the drum's centre height (the live count's tag, baseline ~40.5 in-frame)


def _lace_tex():
    """The bounce drum's teal shell with a cream zig-zag cord (u = around, v = up)."""
    teal, dark, cord = np.array([0x17, 0xB3, 0xA3]) / 255, np.array([0x0B, 0x8A, 0x83]) / 255, np.array([0xFF, 0xF3, 0xDF]) / 255

    def fn(u, v):
        col = teal[None, None] * (1 - v[..., None] * 0.0) * (0.85 + 0.15 * v[..., None]) + dark[None, None] * 0.0
        zz = np.abs(((u * 14) % 1.0) - 0.5) * 2          # 0..1 triangle
        line = np.clip(1 - np.abs(v - (0.15 + 0.7 * zz)) / 0.06, 0, 1)
        return col * (1 - line[..., None]) + cord[None, None] * line[..., None]
    return fn


def sky_parts(view=BADGE_VIEW):
    from dataclasses import replace
    clouds = []
    for (x, y, z, r) in [(-26, 27, 5, 7.0), (-17, 28, 11, 8.2), (-6, 27, 14, 8.6), (7, 27, 14, 8.6), (18, 28, 11, 8.2),
                         (27, 27, 5, 7.0), (-21, 32, -4, 7.5), (0, 31, 3, 9.2), (21, 32, -4, 7.5), (-11, 32, 6, 7.2),
                         (11, 32, 6, 7.2)]:
        clouds.append(sphere(P(r), (P(x), P(y + 5.5), P(z))))
    cloud = union(*clouds, k=P(2.8))
    cy = SKY_CY
    shell = cylinder(P(21.5), P(7.0), round=P(2.2)).translate(0, P(cy - 0.5), 0)
    top = cylinder(P(22.6), P(2.0), round=P(1.8)).translate(0, P(cy + 7.2), 0)
    rimb = torus(P(22.0), P(1.6)).translate(0, P(cy + 6.2), 0)
    rimt = torus(P(21.8), P(1.5)).translate(0, P(cy - 7.2), 0)
    tacks = union(*[sphere(P(1.1), center=(P(22.6 * math.sin(a)), P(cy + 6.0), P(22.6 * math.cos(a)))) for a in np.linspace(-1.5, 1.5, 9)])
    zf = P(22.5)
    tag_rim = extrude(rect2(P(8.8), P(9.6), round=P(3.6)), P(1.6), round=P(1.2)).translate(0, P(cy - 0.5), zf + P(0.2))
    tag = extrude(rect2(P(6.6), P(7.4), round=P(2.6)), P(1.0), round=P(0.8)).translate(0, P(cy - 0.5), zf + P(1.6))
    shell_m = replace(satin("drum_shell", "#17B3A3", rough=0.42, ior=1.3), texture=_lace_tex(), texture_size=256)
    return [
        T("clouds", cloud, "cloud", P(24), P(46), view, rough=0.5),
        Part("dShell", shell, shell_m, uv=("cyl", (0.0, P(cy - 7.5), 0.0), (0, 1, 0), 1.0 / P(15.0))),
        T("dTop", top, "tangerine", P(cy + 5), P(cy + 9.5), view),
        T("dRims", union(rimb, rimt), "brass", P(cy - 9), P(cy + 8), view, voxel=0.004),
        T("dTacks", tacks, "iron", P(cy + 5), P(cy + 7.5), view, voxel=0.0035),
        T("dTagRim", tag_rim, "brass", P(cy - 10), P(cy + 9), view, voxel=0.004),
        T("dTag", tag, "coral", P(cy - 8), P(cy + 7), view, voxel=0.004),
    ]


DRUM = {"dShell", "dTop", "dRims", "dTacks", "dTagRim", "dTag"}


def badge_sky():
    return base_parts() + sky_parts(), VOXEL


# ------------------------------------------------------------------ nav icons (same frames as today's)

def mine_cart():
    """Tangerine mine cart (tapered tub, iron top band + corner straps), two iron wheels, a heap of star coins."""
    tub = box(0.44, 0.22, 0.26, round=0.08).taper(-0.22, 0.22, 0.78, 1.0).translate(0, -0.06, 0)
    band = box(0.49, 0.06, 0.30, round=0.05, center=(0, 0.16, 0))
    straps = union(*[box(0.035, 0.20, 0.28, round=0.02, center=(sx * 0.30, -0.07, 0.0)) for sx in (-1, 1)])
    wheels = union(*[cylinder(0.12, 0.05, round=0.03).transform(Rx(90)).translate(sx * 0.27, -0.30, 0.27) for sx in (-1, 1)])
    hubs = union(*[sphere(0.045, center=(sx * 0.27, -0.30, 0.33)) for sx in (-1, 1)])
    c1 = coin_part("coinA", R=0.25, T=0.07, Rw=Rx(-8) @ Rz(8), t=(-0.08, 0.34, -0.04), back=False)
    c2 = coin_part("coinB", R=0.22, T=0.065, Rw=Rx(-14) @ Rz(-12), t=(0.20, 0.28, -0.08), back=False)
    view = (0, 10, 0)
    return [T("cart", tub, "tangerine", -0.30, 0.24, view), T("cartBand", union(band, straps, k=0.01), "iron", -0.30, 0.24, view),
            T("wheels", wheels, "iron", -0.44, -0.16, view), T("hubs", hubs, "brass", -0.36, -0.24, view, voxel=0.003), c1, c2], 0.004


def lodge():
    """A plank lodge: steep teal shingle roof with deep eaves, honey plank walls, a round tangerine door with a brass
    knob, a small lantern, a stone chimney with a brass cap."""
    view = (0, 4, 0)
    walls = box(0.40, 0.30, 0.20, round=0.05, center=(0, -0.28, 0))
    roof2 = polygon2(fillet_points([(-0.62, -0.02), (0.0, 0.52), (0.62, -0.02), (0.50, -0.10), (0.0, 0.34), (-0.50, -0.10)],
                                   [0.06, 0.10, 0.06, 0.03, 0.05, 0.03], n_arc=6))
    roof = extrude(roof2, 0.27, round=0.07)
    gable2 = polygon2(fillet_points([(-0.44, -0.04), (0.0, 0.33), (0.44, -0.04)], [0.03, 0.06, 0.03], n_arc=5))
    gable = extrude(gable2, 0.17, round=0.04)
    chim = box(0.075, 0.13, 0.075, round=0.025, center=(0.28, 0.36, -0.05))
    cap = box(0.10, 0.03, 0.10, round=0.02, center=(0.28, 0.50, -0.05))
    door2 = intersect2(circle2(0.17).translate(0, -0.33), rect2(0.2, 0.3).translate(0, -0.28))
    door_fr = extrude(intersect2(circle2(0.205).translate(0, -0.33).subtract(circle2(0.16).translate(0, -0.33)), rect2(0.3, 0.3).translate(0, -0.30)),
                      0.04, round=0.02).translate(0, 0, 0.21)
    door = extrude(door2, 0.03, round=0.015).translate(0, 0, 0.20)
    knob = sphere(0.03, center=(0.08, -0.35, 0.24))
    lamp = union(sphere(0.05, center=(-0.28, -0.12, 0.23)), box(0.05, 0.012, 0.03, center=(-0.28, -0.065, 0.22)))
    step = box(0.26, 0.04, 0.08, round=0.02, center=(0, -0.60, 0.20))
    return [T("walls", union(walls, gable, k=0.02), "timber", -0.60, 0.33, view),
            T("roof", roof, "teal", -0.10, 0.52, view),
            T("chim", chim, "iron", 0.23, 0.50, view), T("chimCap", cap, "brass", 0.47, 0.53, view, voxel=0.003),
            T("doorFrame", door_fr, "timberDark", -0.58, -0.12, view), T("door", door, "tangerine", -0.58, -0.16, view),
            T("knob", knob, "brass", -0.39, -0.31, view, voxel=0.003),
            Part("lamp", lamp, Material("lodge_lamp", "#FFE08A", roughness=0.2, ior=1.45, emissive="#FFB84A")),
            T("step", step, "timberDark", -0.64, -0.56, view)], 0.004


def cup():
    """Gold cup with round handles on a short stem, a teal star emblem, on a timber plinth."""
    view = (0, -4, 0)
    prof = spline_profile([(0.0, -0.06), (0.16, -0.05), (0.28, 0.02), (0.34, 0.14), (0.36, 0.26), (0.37, 0.36), (0.0, 0.36)], samples=60)
    bowl = revolve(prof)
    rim = cylinder(0.40, 0.06, round=0.05, center=(0, 0.40, 0))
    stem = cylinder(0.075, 0.09, center=(0, -0.14, 0))
    knot = sphere(0.11, center=(0, -0.18, 0))
    hs = []
    for sx in (-1, 1):
        th = np.linspace(math.radians(100), math.radians(-95), 14)
        pts = [(sx * (0.38 + 0.13 * math.cos(a)), 0.20 + 0.13 * math.sin(a), 0.0) for a in th]
        pts[0] = (sx * 0.34, 0.33, 0.0); pts[-1] = (sx * 0.31, 0.06, 0.0)
        hs.append(path_tube(pts, [0.055] * len(pts)))
    goldcup = union(bowl, rim, stem, knot, *hs, k=0.03)
    plinth = box(0.30, 0.09, 0.18, round=0.04, center=(0, -0.33, 0))
    plinth2 = box(0.24, 0.05, 0.15, round=0.03, center=(0, -0.21, 0))
    st2 = star_shape(0.15).translate(0, 0.18)
    mark = goldcup.offset(0.024).intersect(extrude(st2, 0.6).translate(0, 0, 0.6), k=0.01)
    return [T("cup", goldcup, "gold", -0.26, 0.46, view), T("cupStar", mark, "teal", 0.03, 0.34, view, voxel=0.003),
            T("plinth", union(plinth, plinth2, k=0.01), "timberDark", -0.42, -0.16, view)], 0.004


MODELS = dict(badge_streak=badge_streak, badge_rocket=badge_rocket, badge_sky=badge_sky, mine_cart=mine_cart, lodge=lodge,
              cup=cup)


def _sel(model_fn, keep):
    def fn():
        parts, v = model_fn()
        return [p for p in parts if p.name in keep], v
    return fn


# badge layers: the same model, subsets of its parts
for _k, _fn, _groups in (("streak", badge_streak, {"body": BASE | {"poles", "knobs", "wrap"}, "pennantL": {"pennantL"},
                                                   "pennantR": {"pennantR"}}),
                         ("rocket", badge_rocket, {"body": BASE, "rocket": ROCKET}),
                         ("sky", badge_sky, {"body": BASE, "clouds": {"clouds"}, "drum": DRUM})):
    for _L, _keep in _groups.items():
        MODELS[f"badge_{_k}_{_L}"] = _sel(_fn, _keep)

BADGE_BOUNDS = _bounds(BADGE_FRAME, 36.0, center=(0.0, 0.929), zr=(-1.2, 1.0), margin=1.0, fov=14.0)


def _bcase(model, **extra):
    return dict(scene=[(model, dict(yaw=BADGE_VIEW[0], pitch=BADGE_VIEW[1], center=False))], bounds=BADGE_BOUNDS,
                frame=BADGE_FRAME, fov=14, light=BADGE_LIGHT, no_fit=True, **extra)


def _nav(model, view, **kw):
    kw.setdefault("light", HUD.PROP_LIGHT)
    return dict(model=model, yaw=view[0], pitch=view[1], roll=view[2], **kw)


ASSETS = {
    "badgeHotStreak": _bcase("badge_streak", anchors={"ringBottom": [[0.0, 0.0, 0.0]], "textBand": [[0.0, P(16.5), P(26.1)]]}),
    "badgeRocketRally": _bcase("badge_rocket", anchors={"ringBottom": [[0.0, 0.0, 0.0]], "textBand": [[0.0, P(16.5), P(26.1)]],
                                                       "porthole": [[0.0, P(PORT_Y), P(-2.0 + 12.9 + 2.8)]]}),
    "badgeCloudHop": _bcase("badge_sky", anchors={"ringBottom": [[0.0, 0.0, 0.0]], "textBand": [[0.0, P(16.5), P(26.1)]],
                                                 "tag": [[0.0, P(SKY_CY - 0.5), P(22.5 + 2.8)]]}),
    "navCart": _nav("mine_cart", (0, 10, 0), frame=(62, 62), fill=(0.90, 0.88), post_fit=HUD._satgrade()),
    "navLodge": _nav("lodge", (0, 4, 0), frame=(80, 86), fill=(0.92, 0.95), post_fit=HUD._satgrade()),
    "navCup": _nav("cup", (0, -4, 0), frame=(68, 62), fill=(0.84, 0.92), align=(0.5, 0.52), fov=10, post_fit=HUD._satgrade()),
}
# the layer cases (dest parts; pivots projected by ui3d)
LAYER_PIVOTS = {
    "streak": {"pennantL": {"pole": [P(-11.2), P(69.0), P(3.4)]}, "pennantR": {"pole": [P(11.8), P(69.0), P(1.4)]},
               "body": {"ringBottom": [0.0, 0.0, 0.0]}},
    "rocket": {"rocket": {"nozzle": [0.0, P(ROCKET_BASE_Y + 1.4), P(-2.0)]}, "body": {"ringBottom": [0.0, 0.0, 0.0]}},
    "sky": {"drum": {"tag": [0.0, P(SKY_CY - 0.5), P(22.5 + 2.8)]}, "clouds": {"centre": [0.0, P(34.0), P(6.0)]},
            "body": {"ringBottom": [0.0, 0.0, 0.0]}},
}
LAYER_ORDER = {"streak": ["body", "pennantL", "pennantR"], "rocket": ["body", "rocket"], "sky": ["body", "drum", "clouds"]}
for _k, _order in LAYER_ORDER.items():
    for _L in _order:
        ASSETS[f"badge_{_k}_L_{_L}"] = _bcase(f"badge_{_k}_{_L}", dest="parts",
                                              anchors={n: [v] for n, v in LAYER_PIVOTS[_k].get(_L, {}).items()})

_NOTES = {
    "streak": {"body": dict(note="medallion, pedestal (live countdown), poles"),
               "pennantL": dict(note="the left pennant: flutter about `pole` (motion-catalog §6.4 flags)"),
               "pennantR": dict(note="the right pennant: flutter about `pole`")},
    "rocket": {"body": dict(note="medallion + pedestal (live countdown / Join)"),
               "rocket": dict(note="the rocket: the lift-off (translateY -8 pt) + the live rank on its porthole")},
    "sky": {"body": dict(note="medallion + pedestal (live countdown / Join)"),
            "drum": dict(note="the bounce drum: the hop (translateY -5 pt) + the live count on its tag"),
            "clouds": dict(note="the clouds in front of the drum's foot: a small drift")},
}
RIGS = {f"badge_{_n}": dict(full=_case, layers=[(L, f"badge_{_k}_L_{L}") for L in LAYER_ORDER[_k]], layer_notes=_NOTES[_k],
                            dir=f"badge_{_n}_rig", bake=True)
        for _k, _n, _case in (("streak", "hotstreak", "badgeHotStreak"), ("rocket", "rocketrally", "badgeRocketRally"),
                              ("sky", "cloudhop", "badgeCloudHop"))}
