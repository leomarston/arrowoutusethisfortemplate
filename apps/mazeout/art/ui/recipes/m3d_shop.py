"""missing-3d lane: the shop's Special Offer and bundle art (SPEC-ui 2.12.2; the proposed ids of SPEC-ui 4.2).

    bundleSpecial   Special Offer (1 000 coins): the 1 000 coin-pack pile at the Special card's larger size + glints
    bundleBag       Mini Bundle: a crimson coin sack tied with a rope, on a lavender base, coin stacks either side
    bundleBarrel    Epic Bundle: a crimson stave barrel with a lavender hoop, broken open at the front, coins spilling
    bundleChest     Elite Bundle: an open crimson chest with lavender trim and a pink gem latch, full of coins
    bundleSafe      Mega Bundle: a lavender safe with its wheel door swung open, coins pouring out
    bundleCart      Legendary Bundle: a crimson cart with a lavender wheel under a huge coin heap

(SPEC-ui 4.2 proposed bundleBag / bundleChestRed / bundleChestPurple / bundleSafe / bundleCart for Mini .. Legendary;
the Epic art on the phone is a barrel and the Elite art a red chest, so the ids name what is drawn: bundleBarrel,
bundleChest. The lane log has the mapping.)

References (LOOKED AT only; measured in pt on gridded crops): research/shots/meta-012 + meta-007 (Special Offer, Mini),
meta-008 (Epic, Elite, Mega), meta-009 / meta-010 (Legendary). The coin is the shop's coin (3d-events_coins.py), so
bundle coins and coin-pack coins are the same object under the same light.

Frame: ONE frame for every bundle card, 176 x 102 pt, whose top-left sits at (16, cream top - 1) of the card = (16,
card top + 7.7) (SPEC-ui 2.12.2: the cream top starts 8.7 pt below the card top). Each art is fitted to its measured
bbox inside that frame, so the shell draws every bundle at the same offset. bundleSpecial: the same frame size at
(16, 200) on the Special Offer card (card top 190.2). Live text (the amounts "2 000" ...) is drawn by the shell over
the art, as on the phone; never baked.
"""
from __future__ import annotations

import math
import sys

import numpy as np

import m3d_kit as MK
import scene_kit as K
from scene_kit import (Canvas, Part, box, capsule, cylinder, ellipsoid, extrude, gloss, revolve, rounded_polygon2,
                       satin, sphere, spline_profile, torus, union, SDF, F, polygon2, circle2, rect2)

_M = sys.modules[__name__]
EC = MK.EC

FRAME = (176, 102)
VIEW = (0.0, 17.0)          # the shop art is seen ~17 deg from above (coin tops read as ~0.3 ellipses), like the packs

# the measured art bboxes inside FRAME (pt, frame origin = (16, cream top - 1)); from the gridded crops:
#   Mini   meta-012 cream top 481.4: art x 27-141, y 493-568
#   Epic   meta-008 cream top 151.8: art x 30-136, y 156-244
#   Elite  meta-008 cream top 355.6: art x 26-160, y 366-452
#   Mega   meta-008 cream top 559.1: art x 28-150, y 566-658
#   Legend meta-010 cream top 157.1: art x 27-188, y 160-256
#   Special meta-012 (frame at (16, 200)): pile x 58-158, y 236-282
BOX = {
    "bundleBag": (11.0, 12.6, 125.0, 87.6),
    "bundleBarrel": (14.0, 5.2, 120.0, 93.2),
    "bundleChest": (10.0, 11.4, 144.0, 97.4),
    "bundleSafe": (12.0, 7.9, 134.0, 99.9),
    "bundleCart": (11.0, 3.9, 172.0, 99.9),
    "bundleSpecial": (42.0, 36.0, 142.0, 82.0),
}


# ====================================================================== director r3: BIG heap coins
# At scale 1 a bundle heap packs ~60 coins across the card, each ~7 pt on screen, and their rims read as rings: next to
# meta-008 .. meta-010 the Elite / Mega / Legendary heaps looked like a tangle of noodles. The phone's heap coins are
# ~12-14 pt and face the viewer. big_heap / big_stack lay out the same mounds with the coin (and its spacing) scaled by s.
HEAP_S = 1.6


def big_heap(cx, cz, rx, rz, h, y0=0.0, spacing=0.5, seed=0, face=0.35, tilt=22.0, power=0.5, depth=0.0, s=HEAP_S):
    return MK.heap_poses(cx, cz, rx, rz, h, y0=y0, spacing=spacing * s, seed=seed, face=face, tilt=tilt, power=power,
                         depth=depth * s, lift=(s - 1) * MK.T * 0.5)


def big_stack(x, z, n, seed, s=HEAP_S):
    """MK.stack with every level's height scaled by s (the coins are drawn s x bigger)."""
    return [(Rm, (t[0], t[1] * s, t[2])) for Rm, t in MK.stack(x, z, n, seed)]


def big_upright(x, z, s=HEAP_S, **kw):
    Rm, t = EC.upright(x, z, **kw)
    return Rm, (t[0], t[1] * s, t[2])


# ====================================================================== Special Offer: the 1 000 pile
# meta-012 / meta-011 (the Special art = the 1 000 coin tile's pile, 1.23x): pt at the Special card, coin ~27 pt:
# a 5-coin centre stack (x 94-122), a coin on edge leaning on its left side turned to the right (x 70-100), a 2-stack
# behind left and 2 flat coins in front left (x 60-100), a 3-stack behind right (x 118-150), a big coin on edge in front
# right facing the viewer (x 116-150), a 2-stack far right (x 140-160).
def special_pile():
    P = []
    P += MK.stack(0.0, 0.0, 5, seed=31)
    P += MK.stack(-1.20, -0.40, 2, seed=32) + MK.stack(-1.05, 0.78, 2, seed=33)
    P += MK.stack(0.98, -0.50, 3, seed=34) + MK.stack(1.66, 0.10, 2, seed=35)
    # the two coins on edge are drawn bigger than the stacked coins (the phone art does the same: ~34 pt vs ~28 pt)
    U = [(EC.upright(-0.70, 0.36, lean=12, turn=-38, spin=10)), (EC.upright(0.80, 0.66, lean=8, turn=-14, spin=36))]
    U = [(Rm, (t[0], t[1] * 1.22, t[2])) for Rm, t in U]       # coins_part scales the mesh, not the offset
    return [MK.coins("coins", P), MK.coins("bigCoins", U, scale=1.22)], 0.02


# ====================================================================== Mini: the coin sack (coin = 20 pt)
SACK_VIEW = (0, 0, 0)
SACK_WIDE = 1.14        # meta-012: the sack is 72 pt across for 20 pt coins (3.6 coins), the base 57 pt


def _lobed_revolve(prof_pts, lobes=0, amp=0.0, y_from=-9.0, y_to=9.0, samples=64):
    """A solid of revolution from a (r, y) spline profile, its radius modulated by amp * cos(lobes * theta) between
    y_from and y_to (soft cloth folds). Lipschitz-safe for small amp."""
    base = revolve(spline_profile(prof_pts, samples=samples))
    if not lobes or not amp:
        return base
    f = base.fn

    def fn(p):
        q = p.copy()
        th = np.arctan2(q[:, 2], q[:, 0])
        w = np.clip((q[:, 1] - y_from) / max(1e-6, (y_to - y_from)), 0, 1)
        w = w * w * (3 - 2 * w)
        k = 1.0 - amp * w * np.cos(lobes * th)
        q[:, 0] *= k
        q[:, 2] *= k
        return (f(q) * 0.85).astype(F)
    lo, hi = base.lo.copy(), base.hi.copy()
    lo[[0, 2]] *= 1 + amp
    hi[[0, 2]] *= 1 + amp
    return SDF(fn, lo, hi)


def rope_ring(R, r, y, twist=11, amp=0.03):
    """A twisted rope ring (torus with a helical ridge)."""
    t = torus(R, r).translate(0, y, 0)
    f = t.fn

    def fn(p):
        q = p - np.array([0, y, 0], F)
        th = np.arctan2(q[:, 2], q[:, 0])
        rr = np.sqrt(q[:, 0] ** 2 + q[:, 2] ** 2) - R
        ph = np.arctan2(q[:, 1], rr)
        return ((f(p) - amp * np.cos(twist * th * 2 + 2 * ph)) * 0.9).astype(F)
    return SDF(fn, t.lo - 0.05, t.hi + 0.05)


def rope_seg(a, b, r, twist=9.0, amp=0.025):
    """A short twisted rope piece from a to b (a capsule with a helical ridge)."""
    c = capsule(a, b, r)
    f = c.fn
    a_, b_ = np.asarray(a, F), np.asarray(b, F)
    ax = (b_ - a_) / np.linalg.norm(b_ - a_)
    ref = np.array([1, 0, 0], F) if abs(ax[0]) < 0.9 else np.array([0, 0, 1], F)
    e1 = np.cross(ax, ref); e1 /= np.linalg.norm(e1)
    e2 = np.cross(ax, e1)

    def fn(p):
        q = p - a_
        t = q @ ax
        ph = np.arctan2(q @ e2, q @ e1)
        return ((f(p) - amp * np.cos(twist * t * 2 + 2 * ph)) * 0.9).astype(F)
    return SDF(fn, c.lo - 0.05, c.hi + 0.05)


def sack_model():
    parts = []
    # meta-012 (pt, ground y 566, sack axis x 76, coin 20 pt): base x 50-107 (r 1.43), a band 15 pt tall; body widest
    # 72 pt at y 543; the rope ring x 47-111 at y 515-530; the rolled rim x 49-104 at y 505-522; coins to y 490
    base = cylinder(1.43 * SACK_WIDE, 0.30, round=0.15).translate(0, 0.30, 0)
    parts.append(MK.painted("sackBase", base, MK.SCHEMES["baseGrey"], -0.1, 0.62, SACK_VIEW, rough=0.40, ior=1.34))
    body = _lobed_revolve([(0.0, 0.46), (1.28, 0.50), (1.74, 0.84), (1.82, 1.16), (1.68, 1.56), (1.34, 1.90),
                           (1.02, 2.12), (0.0, 2.2)], lobes=9, amp=0.04, y_from=1.45, y_to=2.15)
    neck = revolve(spline_profile([(0.0, 1.9), (1.00, 1.92), (0.98, 2.3), (1.14, 2.62), (0.0, 2.7)], samples=48))
    rim = torus(1.08, 0.19).translate(0, 2.74, 0)
    rim = _lobed_like(rim, 8, 0.07)
    sack = union(body, neck, rim, k=0.10).subtract(cylinder(0.90, 0.6).translate(0, 3.12, 0), k=0.1)
    sack = sack.scale_xyz(SACK_WIDE, 1.0, SACK_WIDE)
    parts.append(MK.painted("sack", sack, MK.SCHEMES["crimson"], 0.5, 2.95, SACK_VIEW, rough=0.32, ior=1.40, e0=0.22))
    # the rope round the neck (a fat twisted ring), a knot in front and two hanging ends with knotted tips, lying on
    # the bulge of the sack
    W = SACK_WIDE
    rope = rope_ring(1.18 * W, 0.19, 2.18, twist=13, amp=0.035)
    knot = ellipsoid(0.27, 0.24, 0.22, center=(0.03, 2.06, 1.30 * W))
    end_l = union(capsule((-0.08, 1.98, 1.40 * W), (-0.24, 1.38, 1.80 * W), 0.115), ellipsoid(0.16, 0.19, 0.15, center=(-0.26, 1.26, 1.86 * W)), k=0.04)
    end_r = union(capsule((0.13, 1.98, 1.40 * W), (0.30, 1.44, 1.78 * W), 0.115), ellipsoid(0.16, 0.19, 0.15, center=(0.32, 1.32, 1.84 * W)), k=0.04)
    parts.append(MK.painted("rope", union(rope, knot, end_l, end_r, k=0.04), MK.SCHEMES["rope"], 1.1, 2.4, SACK_VIEW,
                            rough=0.45, ior=1.3))
    # a dark bed inside the opening (gaps between the coins read as depth, not as the sky)
    parts.append(Part("sackBed", cylinder(0.95, 0.12).translate(0, 2.66, 0), satin("sack_bed", "#8A0A26")))
    poses = MK.heap_poses(0.0, 0.0, 0.92, 0.82, 0.25, y0=2.72, spacing=0.56, seed=3, face=0.45, tilt=25)
    big = [MK.facing(-0.56, 3.05, 0.18, lean=40, turn=26, spin=8), MK.facing(0.05, 3.16, -0.12, lean=36, turn=-6, spin=40),
           MK.facing(0.62, 3.02, 0.16, lean=44, turn=-28, spin=20), MK.facing(-0.08, 2.92, 0.50, lean=58, turn=8, spin=60)]
    parts.append(MK.coins("sackTop", [(Rm, (t[0], t[1], t[2])) for Rm, t in big], scale=1.15))
    # stacks: left an upright coin, a 4-stack in front and a 2-stack behind; right a tall 5-stack behind, 4 + 3 in front
    poses += MK.stack(-1.70, 1.50, 4, seed=21) + MK.stack(-2.12, 0.62, 2, seed=22)
    poses += [EC.upright(-2.30, 1.72, lean=8, turn=40, spin=12)]
    poses += MK.stack(2.45, 0.10, 5, seed=23) + MK.stack(2.22, 1.28, 4, seed=24) + MK.stack(2.85, 1.05, 3, seed=25)
    parts.append(MK.coins("sackCoins", poses))
    return parts, 0.02


def _lobed_like(s, lobes, amp):
    f = s.fn

    def fn(p):
        q = p.copy()
        th = np.arctan2(q[:, 2], q[:, 0])
        k = 1.0 - amp * np.cos(lobes * th)
        q[:, 0] *= k
        q[:, 2] *= k
        return (f(q) * 0.85).astype(F)
    lo, hi = s.lo.copy(), s.hi.copy()
    lo[[0, 2]] *= 1 + amp
    hi[[0, 2]] *= 1 + amp
    return SDF(fn, lo, hi)


# ====================================================================== Epic: the broken barrel (coin = 14 pt)
# meta-008 (pt, ground y ~240, axis x 84.5): staves x 47-122 (r 2.68), rim top y 163 (h 5.4), a lavender hoop x 45-124
# at y 178-196 (h 3.1-4.4), coins heaped over the rim to y 156; a jagged hole low in the front (x 62-112, y 200-238)
# with coins pouring out into a heap in front; a broken stave on the ground at the left (x 50-62, y 222-240); coin
# stacks either side (x 30-46, x 117-137).
BAR_H, BAR_RB, BAR_RM, BAR_N = 4.70, 2.36, 2.60, 12


def barrel_shell():
    H, Rb, Rm, n = BAR_H, BAR_RB, BAR_RM, BAR_N
    wall, groove_d, groove_w, cap = 0.26, 0.07, 0.07, 0.30

    def fn(p):
        x, y, z = p[:, 0], p[:, 1], p[:, 2]
        rad = np.sqrt(x * x + z * z)
        th = np.arctan2(z, x) + np.pi / n        # a stave centred on the front (theta = pi/2)
        t = np.clip(y / H, 0, 1)
        r0 = Rb + (Rm - Rb) * np.sin(np.pi * t)
        s = (th * n / (2 * np.pi)) % 1.0
        ds = np.minimum(s, 1 - s) * (2 * np.pi * r0 / n)
        r = r0 - groove_d * np.exp(-(ds / groove_w) ** 2) + 0.05 * np.sin(np.pi * s)
        outer = rad - r
        inner = (r0 - wall) - rad
        ytop = H + cap * np.sqrt(np.clip(np.sin(np.pi * s), 0, 1)) - cap * 0.3
        d = np.maximum(np.maximum(outer, inner), np.maximum(y - ytop, -y))
        return (d * 0.8).astype(F)
    return SDF(fn, np.array([-Rm - 0.2, -0.1, -Rm - 0.2]), np.array([Rm + 0.2, H + 0.5, Rm + 0.2]))


def barrel_hole():
    """The jagged break low in the front."""
    c = np.array([0.30, 1.36, BAR_RM], F)

    def fn(p):
        q = p - c
        ang = np.arctan2(q[:, 1], q[:, 0])
        jag = 0.22 * np.abs(np.sin(3.5 * ang + 0.6)) + 0.12 * np.abs(np.sin(8.0 * ang + 1.3))
        e = np.sqrt((q[:, 0] / 1.70) ** 2 + (q[:, 1] / 1.30) ** 2) - (1.0 - jag * 0.55)
        return (np.maximum(e * 1.2, np.abs(q[:, 2]) - 1.2) * 0.8).astype(F)
    return SDF(fn, c - np.array([2.2, 1.9, 1.3]), c + np.array([2.2, 1.9, 1.3]))


def barrel_model():
    parts = []
    shell = barrel_shell().subtract(barrel_hole(), k=0.04)
    parts.append(MK.painted("staves", shell, MK.SCHEMES["crimson"], 0.0, BAR_H, (0, 0, 0), rough=0.30, ior=1.42, e0=0.25,
                            voxel=0.03))
    hoop = revolve(rounded_polygon2([(BAR_RM - 0.12, 2.75), (BAR_RM + 0.18, 2.75), (BAR_RM + 0.18, 3.88),
                                     (BAR_RM - 0.12, 3.88)], 0.15, n_arc=5))
    parts.append(MK.painted("hoop", hoop, MK.SCHEMES["lavender"], 2.7, 3.9, (0, 0, 0), rough=0.26, ior=1.45, voxel=0.03))
    # a dark core inside (depth behind the coins in the hole), coins heaped over the rim and inside the hole
    parts.append(Part("core", cylinder(1.45, BAR_H / 2 - 0.1).translate(0, BAR_H / 2, -0.45),
                      satin("barrel_core", "#5A0A1E"), voxel=0.05))
    # director r3: bigger coins at 0.64 spacing (big_heap; meta-008's spill is fewer, BIGGER coins), top heap x1.2
    Ptop = big_heap(0.0, 0.0, 2.22, 2.08, 1.0, y0=BAR_H - 0.15, spacing=0.64, seed=41, face=0.55, tilt=26, power=0.6, s=1.2)
    # coins filling the hole (seen through it, most facing out) and pouring out of it
    Phole = MK.heap_poses(0.30, 1.50, 1.35, 0.65, 2.25, y0=0.12, spacing=0.50, seed=42, face=0.8, tilt=24, power=0.7)
    Psp = big_heap(0.35, 2.55, 1.55, 0.80, 1.05, y0=0.0, spacing=0.64, seed=43, face=0.7, tilt=30, power=0.6, s=1.4)
    parts.append(MK.heap_core("spillCore", 0.35, 2.55, 1.55, 0.80, 1.05, color="#F4A812"))
    parts.append(MK.heap_core("topCore", 0.0, 0.0, 2.22, 2.08, 1.0, y0=BAR_H - 0.15, color="#F4A812"))
    Psp += big_heap(0.10, 2.95, 2.75, 0.60, 0.22, y0=0.0, spacing=0.66, seed=39, face=0.3, tilt=20, s=1.4)
    parts += [MK.coins("barrelTop", Ptop, scale=1.2), MK.coins("barrelSpill", Psp, scale=1.4)]
    P = Phole        # the coins seen through the hole stay at scale 1 (bigger ones cut through the staves)
    # stacks: left two columns + a low one, right two tall columns, two coins on edge
    P += MK.stack(-3.25, 0.55, 5, seed=44) + MK.stack(-2.85, 1.45, 4, seed=45) + MK.stack(-3.65, 1.45, 2, seed=46)
    P += MK.stack(3.20, 0.25, 7, seed=47) + MK.stack(2.95, 1.35, 5, seed=48) + MK.stack(3.65, 1.15, 3, seed=49)
    P += [EC.upright(-2.35, 2.45, lean=12, turn=30, spin=5), EC.upright(2.45, 2.50, lean=10, turn=-28, spin=44)]
    parts.append(MK.coins("barrelCoins", P))
    # the broken stave on the ground at the left front
    plank = box(0.42, 0.95, 0.13, round=0.10).transform(K.rot_z(58) @ K.rot_y(-30)).translate(-2.0, 0.42, 2.55)
    parts.append(MK.painted("plank", plank, MK.SCHEMES["wood"], 0.0, 1.0, (0, 0, 0), rough=0.5, ior=1.3, voxel=0.02))
    return parts, 0.025


# ====================================================================== Elite: the open chest (coin = 14 pt)
# meta-008 (pt, ground y ~452, axis x 100): body x 52-148 (6.9 coins) front y 405-452, lavender rim / posts, crimson
# panels; the lid opened back ~70 deg (y 367-400), its crimson barrel between lavender end arches, a pink hexagonal gem
# latch at its (raised) front edge (x 92-110, y 370-396); coins heaped in the chest and over the front rim; stacks
# left (x 26-55) and right (x 145-160).
EL_S = 0.92          # scene_events.chest units -> coins (the chest is also stretched EL_XY: 96 x 45 pt body, 17 pt coin)
EL_XY = (1.42, 0.95)
EL_OPEN = 100


def _stretch(s):
    return s.scale_xyz(EL_XY[0], EL_XY[1], 1.0)


def elite_chest():
    import scene_events as SE
    red = "#D4143F"
    parts, vox = SE.chest(panel=red, quilt=(red, "#C8123B", "#DA2048"), frame="#C6B6F2", with_coins=False,
                          open_deg=EL_OPEN, shield_on=False)
    for p in parts:
        p.sdf = _stretch(p.sdf)
    c = SE.CHEST
    w, h, d, r = c["w"], c["h"], c["d"], c["lid_r"]
    hinge = (0, h, -d / 2 + 0.05)
    hexa = rounded_polygon2([(0.62 * math.cos(math.radians(30 + 60 * i)), 0.62 * math.sin(math.radians(30 + 60 * i)))
                             for i in range(6)], 0.10, n_arc=4)
    gem = union(extrude(hexa, 0.16, round=0.12), extrude(hexa.offset(-0.18), 0.28, round=0.14), k=0.05)
    gem = gem.scale_xyz(1.0, 1.25, 1.0)
    # the gem hangs on the lid's front edge band facing the viewer (with the lid thrown back, the edge is on top):
    # the edge's world position = the lid transform of the lid-space point (0, 0, r) (scene_events.chest lid_xf)
    a = math.radians(EL_OPEN)
    ey, ez = h + 2 * r * math.sin(a), (-d / 2 + 0.05) + 2 * r * math.cos(a)
    gem = gem.transform(K.rot_x(-14)).translate(0, ey + 0.10, ez + 0.62)
    parts.append(MK.painted("gem", _stretch(gem), MK.SCHEMES["gem"], ey - 1.0, ey + 0.4, (0, 0, 0), rough=0.18, ior=1.55,
                            voxel=0.015))
    return parts, vox


def elite_coins():
    P = []
    top = 2.5 * EL_XY[1] * EL_S
    # director r3: big coins at 0.64 spacing (see big_heap: the scale-1 heap read as noodles), stacks re-spaced
    s = 1.45
    P += big_heap(0.0, 0.05, 2.85, 1.25, 1.45, y0=top - 0.35, spacing=0.64, seed=51, face=0.72, tilt=28, power=0.5, s=s)
    big = [MK.facing(-1.15, top + 0.75, 0.85, lean=28, turn=18, spin=10), MK.facing(0.95, top + 0.8, 0.9, lean=30, turn=-16, spin=50),
           MK.facing(-0.05, top + 1.15, 0.45, lean=34, turn=4, spin=20), MK.facing(1.95, top + 0.35, 0.95, lean=35, turn=-30, spin=5)]
    # the spill over the front rim at the right and on the ground
    P += big_heap(1.25, 1.95, 1.30, 0.55, 0.55, y0=0.0, spacing=0.64, seed=52, face=0.55, tilt=30, s=s)
    P += big_stack(-4.1, 0.1, 6, seed=53, s=s) + big_stack(-3.4, 1.55, 4, seed=54, s=s) + big_stack(-4.95, 1.6, 2, seed=55, s=s)
    P += big_stack(3.8, 0.2, 5, seed=57, s=s) + big_stack(4.45, 1.6, 3, seed=58, s=s)
    P += [big_upright(-2.8, 2.2, s=s, lean=10, turn=24, spin=30)]
    core = MK.heap_core("eliteCore", 0.0, 0.05, 2.85, 1.25, 1.45, y0=top - 0.35, color="#F4A812")
    return [MK.coins("eliteCoins", P, scale=s), MK.coins("eliteBig", big, scale=1.5), core], 0.02


# ====================================================================== Mega: the open safe (coin = 13 pt)
# meta-008 (pt, ground y ~652, safe x 55-148): a lavender safe body, rounded, its front open (maroon inside, the top of
# the inside shows at the upper left), coins pouring out of it to the right front; the door hinged on the front-left
# edge and swung ~120 deg (its inner face with two round bolts turned to the viewer, the wheel on its outer face seen
# edge-on at the far left, x 28-48); stacks to the right (x 128-150).
SF_W, SF_H, SF_D = 6.0, 6.2, 5.0
SF_OPEN = 94


def safe_model():
    parts = []
    W, H, D = SF_W, SF_H, SF_D
    body = box(W / 2, H / 2, D / 2, round=0.55, center=(0, H / 2, 0))
    mouth = box(W / 2 - 0.62, H / 2 - 0.62, D / 2, round=0.35, center=(0, H / 2, 0.55))
    shell = body.subtract(mouth, k=0.12)
    parts.append(MK.painted("safeBody", shell, MK.SCHEMES["lavender"], 0.0, H, (0, 0, 0), rough=0.26, ior=1.45, voxel=0.04))
    inside = box(W / 2 - 0.66, H / 2 - 0.66, 0.1, center=(0, H / 2, -D / 2 + 0.65))
    floor_ = box(W / 2 - 0.66, 0.1, D / 2 - 0.5, center=(0, 0.66, 0.2))
    parts.append(Part("safeInside", union(inside, floor_), satin("safe_in", "#6E0E25", rough=0.5), voxel=0.05))
    # the door: a thick slab in its own frame (hinge on its left edge at the origin, closed along +x), swung open
    t = 0.62
    dw, dh = W - 1.0, H - 0.9
    slab = box(dw / 2, dh / 2, t / 2, round=0.28, center=(dw / 2, 0, 0))
    inner_panel = box(dw / 2 - 0.55, dh / 2 - 0.55, 0.08, round=0.2, center=(dw / 2, 0, -t / 2 - 0.02))
    door = union(slab, inner_panel, k=0.06)
    # the two bolts stick out of the door's free edge (facing the viewer once the door stands open)
    bolts = union(*[cylinder(0.32, 0.18, round=0.10).transform(K.rot_z(90)).translate(dw + 0.10, yy, 0.0)
                    for yy in (0.85, -0.85)])
    ring = torus(1.35, 0.20).transform(K.rot_x(90)).translate(dw / 2, 0.1, t / 2 + 0.55)
    spokes = union(*[capsule((dw / 2, 0.1, t / 2 + 0.55), (dw / 2 + 1.3 * math.cos(a), 0.1 + 1.3 * math.sin(a), t / 2 + 0.55), 0.12)
                     for a in (0.4, 0.4 + math.pi / 2, 0.4 + math.pi, 0.4 + 1.5 * math.pi)])
    hub = union(cylinder(0.45, 0.30, round=0.18).transform(K.rot_x(90)).translate(dw / 2, 0.1, t / 2 + 0.35),
                cylinder(0.18, 0.40).transform(K.rot_x(90)).translate(dw / 2, 0.1, t / 2 + 0.2))
    wheel = union(ring, spokes, hub, k=0.06)
    hinge_pt = np.array([-W / 2 + 0.1, H / 2, D / 2 - 0.05])
    Rd = K.rot_y(-SF_OPEN)

    def place(s):
        return s.transform(Rd).translate(*hinge_pt)
    parts.append(MK.painted("door", place(door), MK.SCHEMES["lavender"], 0.0, H, (0, 0, 0), rough=0.26, ior=1.45, voxel=0.035))
    parts.append(MK.painted("bolts", place(bolts), MK.SCHEMES["lavender"], 1.5, 5.0, (0, 0, 0), rough=0.22, ior=1.5, voxel=0.02))
    parts.append(MK.painted("wheel", place(wheel), MK.SCHEMES["lavender"], 1.0, 5.2, (0, 0, 0), rough=0.24, ior=1.48, voxel=0.025))
    # coins: filling the safe's lower half and pouring out of the mouth down to the ground at the right front
    # director r3: big coins at 0.64 spacing (big_heap), brighter cores, stacks re-spaced for the bigger coins
    s = 1.45
    P = big_heap(0.3, 0.2, 2.35, 2.0, 2.1, y0=0.75, spacing=0.64, seed=61, face=0.5, tilt=26, power=0.55, s=s)
    P += big_heap(0.9, 3.0, 2.9, 1.4, 1.9, y0=0.0, spacing=0.64, seed=62, face=0.55, tilt=30, power=0.6, s=s)
    P += big_heap(2.9, 3.4, 1.4, 1.0, 0.7, y0=0.0, spacing=0.64, seed=63, face=0.5, tilt=30, s=s)
    parts.append(MK.heap_core("safeCore0", 0.3, 0.2, 2.35, 2.0, 2.1, y0=0.75, color="#F4A812"))
    parts.append(MK.heap_core("safeCore1", 0.9, 3.0, 2.9, 1.4, 1.9, color="#F4A812"))
    P += big_stack(4.10, 0.6, 7, seed=64, s=s) + big_stack(3.55, 2.05, 5, seed=65, s=s) + big_stack(5.05, 1.95, 4, seed=66, s=s)
    P += big_stack(-2.4, 3.65, 1, seed=68, s=s)
    parts.append(MK.coins("safeCoins", P, scale=s))
    return parts, 0.03


# ====================================================================== Legendary: the cart (coin = 14 pt)
# meta-010 (pt, ground y ~256): a crimson cart box with lavender corner posts / rims, its length running into the
# picture to the right (front-left corner x ~50, far corner post x 150-165), a big lavender spoked wheel on its near
# side at the front (x 38-75, y 195-255); a huge coin heap on it (top y 160) spilling over the right end to the ground
# (x 150-187) and to the front; stacks at the left front (x 27-60).
CT_L, CT_D, CT_H, CT_Y = 7.0, 3.4, 2.5, 0.95      # box length (x), depth (z), height, floor height (coin = 16 pt)
CT_YAW = 36                                        # the long side recedes to the right-back, its near end at the left


def cart_model():
    parts = []
    L, D, Hh, y0 = CT_L, CT_D, CT_H, CT_Y
    outer = box(L / 2, Hh / 2, D / 2, round=0.18, center=(0, y0 + Hh / 2, 0))
    inner = box(L / 2 - 0.28, Hh / 2, D / 2 - 0.28, round=0.10, center=(0, y0 + Hh / 2 + 0.3, 0))
    tub = outer.subtract(inner, k=0.05)
    tub_f = tub.fn

    def planks(p):
        # shallow horizontal plank grooves on the outside (meta-009: three planks per side)
        d = tub_f(p)
        ph = ((p[:, 1] - y0) / (Hh / 3.0)) % 1.0
        g = 0.045 * np.exp(-(np.minimum(ph, 1 - ph) / 0.05) ** 2)
        return (d + g).astype(F)
    parts.append(MK.painted("cartTub", SDF(planks, tub.lo, tub.hi), MK.SCHEMES["crimson"], y0, y0 + Hh, (0, 0, 0),
                            rough=0.32, ior=1.42, voxel=0.03))
    posts = union(*[box(0.28, Hh / 2 + 0.10, 0.28, round=0.12, center=(sx * (L / 2 - 0.05), y0 + Hh / 2 + 0.05, sz * (D / 2 - 0.05)))
                    for sx in (-1, 1) for sz in (-1, 1)])
    rims = union(box(L / 2 + 0.05, 0.20, 0.22, round=0.14, center=(0, y0 + Hh + 0.02, D / 2 - 0.05)),
                 box(L / 2 + 0.05, 0.20, 0.22, round=0.14, center=(0, y0 + Hh + 0.02, -D / 2 + 0.05)),
                 box(0.22, 0.20, D / 2 + 0.05, round=0.14, center=(L / 2 - 0.05, y0 + Hh + 0.02, 0)),
                 box(0.22, 0.20, D / 2 + 0.05, round=0.14, center=(-L / 2 + 0.05, y0 + Hh + 0.02, 0)))
    parts.append(MK.painted("cartFrame", union(posts, rims, k=0.04), MK.SCHEMES["lavender"], y0, y0 + Hh, (0, 0, 0),
                            rough=0.26, ior=1.45, voxel=0.03))

    def wheel(cx, cz, R=1.45):
        tyre = torus(R - 0.24, 0.28).transform(K.rot_x(90))
        hub = cylinder(0.42, 0.30, round=0.18).transform(K.rot_x(90))
        spokes = union(*[capsule((0, 0, 0), (R * 0.85 * math.cos(a), R * 0.85 * math.sin(a), 0), 0.16)
                         for a in np.linspace(0, 2 * math.pi, 4, endpoint=False) + 0.35])
        disc = cylinder(R - 0.4, 0.06).transform(K.rot_x(90))
        return union(tyre, hub, spokes, disc, k=0.05).translate(cx, R - 0.05, cz)
    wheels = union(wheel(-L / 2 + 1.15, D / 2 + 0.36, R=1.6), wheel(L / 2 - 1.35, D / 2 + 0.36))
    parts.append(MK.painted("wheels", wheels, MK.SCHEMES["lavender"], 0.0, 2.9, (0, 0, 0), rough=0.26, ior=1.45, voxel=0.03))
    return parts, 0.03


CART_HEAPS = [   # (cx, cz, rx, rz, h, y0, face, seed): the load, the spill down the far end, the spill along the side
    (1.0, 0.3, 4.3, 2.3, 3.6, CT_Y + CT_H - 0.3, 0.72, 71, 0.5),    # director r3: one tall load (meta-010's pyramid)
    (2.8, 1.7, 3.2, 2.2, 3.3, 0.0, 0.72, 72, 0.85),                # ... and the spill down its far end
    (0.2, 2.8, 2.6, 0.9, 1.1, 0.0, 0.72, 73, 0.7),
]


def cart_coins():
    # director r3: big coins (HEAP_S), facing the viewer more (face 0.72 -> 0.8) and a taller load (meta-010's pyramid);
    # the stacks re-spaced so the bigger coins do not interpenetrate
    P, cores = [], []
    for i, (cx, cz, rx, rz, h, y0, face, seed, pw) in enumerate(CART_HEAPS):
        hh = h
        # spacing 0.47 -> 0.64 of the coin diameter: at 0.47 every coin hid half of its neighbours and showed only a
        # crescent (the "noodles"); meta-010's heap coins overlap by about a third, so whole star faces read
        P += big_heap(cx, cz, rx, rz, hh, y0=y0, spacing=0.64, seed=seed, face=min(0.85, face + 0.08), tilt=30, power=pw,
                      depth=0.25)
        cores.append(MK.heap_core(f"cartCore{i}", cx, cz, rx, rz, hh, y0=y0, power=pw, shrink=0.45, color="#F4A812"))
    P += big_stack(-3.0, 3.2, 4, seed=74) + big_stack(-4.7, 2.5, 5, seed=75) + big_stack(-4.3, 4.2, 2, seed=76)
    P += big_stack(5.6, 2.6, 5, seed=77) + big_stack(6.3, 0.9, 4, seed=78) + big_stack(5.2, 4.3, 2, seed=80)
    P += [big_upright(-2.2, 2.6, lean=16, turn=10, spin=15)]
    return [MK.coins("cartCoins", P, scale=HEAP_S)] + cores, 0.02


# ====================================================================== models + builds

MODELS = {"special": special_pile, "sack": sack_model, "barrel": barrel_model, "elite": elite_chest,
          "eliteCoins": elite_coins, "safe": safe_model, "cart": cart_model, "cartCoins": cart_coins}


def _art(ctx, name, scene, box, view=VIEW, fov=16, px=1500, shadow=True, glints=(), fit="contain", light=None,
         align=(0.5, 1.0), gamma=1.08, sat=1.12):
    ims = ctx.render({name: dict(scene=scene, view=view, fov=fov, px=px, light=light or MK.shop_rig())}, tag=name)
    cv = Canvas(*FRAME)
    im = ims[name]
    if shadow:
        # the warm contact pool under the art (the reference art sits on a soft brown shadow on the cream)
        sh = Canvas(*FRAME)
        MK.contact_shadow(sh, (box[0] + 4, box[1], box[2] - 4, box[3]), color="#7A3A10", alpha=0.30, blur_pt=2.0)
        cv.over(sh.a)
    im = K.grade(im, gamma=gamma, sat=sat)
    MK.fit_into(cv, im, box, mode=fit, align=align)
    MK.edge_fade(cv)
    out = cv.image()
    if glints:
        out = MK.twinkles(out, glints)
    return out


def build_special(ctx):
    scene = [(_M, "special", dict(center=False))]
    return _art(ctx, "bundleSpecial", scene, BOX["bundleSpecial"], view=EC.PACK_VIEW, fov=16, fit="width",
                glints=[(68.0, 34.0, 13.0), (88.0, 33.0, 10.0), (122.5, 37.5, 15.0), (43.0, 63.0, 8.0)])


def build_bag(ctx):
    return _art(ctx, "bundleBag", [(_M, "sack", dict(center=False))], BOX["bundleBag"],
                glints=[(80.0, 24.0, 8.0), (133.0, 37.0, 16.0)])


def build_barrel(ctx):
    return _art(ctx, "bundleBarrel", [(_M, "barrel", dict(center=False))], BOX["bundleBarrel"],
                glints=[(66.0, 38.0, 9.0), (103.0, 27.0, 12.0), (70.0, 58.0, 8.0), (128.0, 32.0, 10.0)])


def build_chest(ctx):
    scene = [(_M, "elite", dict(center=False, scale=EL_S, yaw=16)), (_M, "eliteCoins", dict(center=False, yaw=16))]
    return _art(ctx, "bundleChest", scene, BOX["bundleChest"], view=(0.0, 20.0), glints=[(79.0, 23.0, 10.0), (57.0, 51.0, 9.0), (99.0, 50.0, 8.0)])


def build_safe(ctx):
    # director r3: no cast shadows -- the safe's wall threw a hard diagonal shadow across the coins in its mouth (a dark
    # wedge next to the lit spill); meta-008's coins are lit all the way into the safe
    return _art(ctx, "bundleSafe", [(_M, "safe", dict(center=False, yaw=18))], BOX["bundleSafe"], gamma=1.12, sat=1.15,
                light=MK.shop_rig(shadow=False),
                glints=[(88.0, 25.0, 14.0), (71.0, 36.0, 9.0), (58.0, 53.0, 9.0)])


def build_cart(ctx):
    scene = [(_M, "cart", dict(center=False, yaw=CT_YAW)), (_M, "cartCoins", dict(center=False, yaw=CT_YAW))]
    return _art(ctx, "bundleCart", scene, BOX["bundleCart"], gamma=1.16, sat=1.2, glints=[(125.0, 25.0, 11.0), (72.0, 58.0, 9.0)])


BUILDS = {"bundleSpecial": build_special, "bundleBag": build_bag, "bundleBarrel": build_barrel,
          "bundleChest": build_chest, "bundleSafe": build_safe, "bundleCart": build_cart}
DEST = {k: "ui" for k in BUILDS}
