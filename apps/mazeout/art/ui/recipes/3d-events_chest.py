"""3d-events lane: the Sky Jump stage chests (stageChestGreen / Blue / Pink).

Reference (LOOKED AT only): the three stage tiles of the Sky Jump popup, research/shots/065 (also 096). Measured there:
the chest is 52 x ~38 pt (the bottom few pt sit under the live "Stage N" label), seen a little from above and from the
left (its left end shows). A barrel lid over a box body; wide gold straps down both ends that frame an inset of the
chest colour, a gold band round the lid/body seam, a gold base trim, and a rounded gold DIAMOND lock plate with an
orange-brown keyhole on the seam. Colours: lid lighter than the body panels (green #2BD27A / #1E9E4A, blue #22C4FA /
#1589CC, pink #D653C8 / #9B3597); gold face #FFC21A, shade #F29A0C.
"""
from __future__ import annotations

from uikit import (SDF, Part, box, circle2, cylinder, extrude, gloss, rect2, union, capsule2)  # noqa: F401

VOXEL = 0.0055

W2 = 0.50      # half width (x)
D2 = 0.30      # half depth (z)
HB = 0.40      # body height (the seam)
LH = 0.32      # lid height above the seam (a barrel, a little taller than round)
STRAP = 0.18   # end strap width on the front (the reference's straps are chunky: ~0.2 of the width each)
GOLD = "#FFA90C"
KEY = "#B8500A"

COLOURS = {
    "green": ("#1DB862", "#1A9446"),
    "blue": ("#18B0EE", "#137FC2"),
    "pink": ("#C23FBA", "#933090"),
}


def core_parts():
    body = box(W2, HB / 2, D2, round=0.045).translate(0, HB / 2, 0)
    lid = cylinder(D2, W2, round=0.05).rotate_z(90).scale_xyz(1, LH / D2, 1)
    lid = lid.intersect(box(W2 + 0.1, 0.6, D2 + 0.1).translate(0, 0.6, 0)).translate(0, HB - 0.02, 0)
    return body, lid


def prism_x(sd):
    """The x = 0 cross-section of `sd`, extruded along x without end (for the end-face insets)."""
    f = sd.fn

    def fn(p):
        q = p.copy()
        q[:, 0] = 0
        return f(q)
    return SDF(fn, [-3, sd.lo[1], sd.lo[2]], [3, sd.hi[1], sd.hi[2]])


def chest(colour):
    lid_c, body_c = COLOURS[colour]
    body, lid = core_parts()
    core = union(body, lid, k=0.01)
    big = 2.0
    shell = core.offset(0.026)
    end_shell = core.offset(0.030)
    ends = union(box(STRAP / 2 + 0.05, big, big).translate(W2 - STRAP / 2 + 0.05, 0, 0),
                 box(STRAP / 2 + 0.05, big, big).translate(-(W2 - STRAP / 2 + 0.05), 0, 0))
    straps = end_shell.intersect(ends, k=0.01)
    # each strap frames an inset of the chest colour on the END face (the reference's left end shows a D-shaped lid
    # inset over a body inset, split by the seam band)
    tip = union(box(0.1, big, big).translate(W2 + 0.1, 0, 0), box(0.1, big, big).translate(-(W2 + 0.1), 0, 0))
    ins_lid = prism_x(lid.offset(-0.07)).intersect(box(big, big, big).translate(0, big + HB + 0.07, 0))
    ins_body = prism_x(body.offset(-0.07)).intersect(box(big, big, big).translate(0, HB - 0.07 - big, 0))
    straps = straps.subtract(union(ins_lid, ins_body).intersect(tip), k=0.008)
    seam = shell.intersect(box(big, 0.066, big).translate(0, HB - 0.01, 0))
    trim = shell.intersect(box(big, 0.048, big).translate(0, 0.044, 0))
    gold = union(straps, seam, trim, k=0.008)
    # the lock: a big rounded diamond plate (~0.42 of the width) with a raised inner diamond and a keyhole
    zf = D2 + 0.026
    yc = HB + 0.015
    d_out = rect2(0.172, 0.172, round=0.06).rotate(45)
    d_in = rect2(0.122, 0.122, round=0.04).rotate(45)
    plate = extrude(d_out, 0.034, round=0.026).translate(0, yc, zf + 0.006)
    inner = extrude(d_in, 0.028, round=0.02).translate(0, yc, zf + 0.026)
    hole2 = circle2(0.050).translate(0, yc + 0.022).union(capsule2((0, yc), (0, yc - 0.080), 0.030))
    hole = extrude(hole2, 0.02, round=0.008).translate(0, 0, zf + 0.044)
    lock = union(plate, inner, k=0.012).subtract(extrude(hole2.offset(0.005), 0.05).translate(0, 0, zf + 0.085), k=0.005)
    return [
        Part("lid", lid, gloss(f"lid_{colour}", lid_c, rough=0.30, ior=1.38)),
        Part("body", body, gloss(f"body_{colour}", body_c, rough=0.34, ior=1.36)),
        Part("gold", gold, gloss("chest_gold", GOLD, rough=0.26, ior=1.45), voxel=0.0045),
        Part("lock", lock, gloss("lock_gold", GOLD, rough=0.24, ior=1.45), voxel=0.0035),
        Part("keyhole", hole, gloss("keyhole", KEY, rough=0.5, ior=1.2), voxel=0.0035),
    ], VOXEL


MODELS = {f"chest_{c}": (lambda c=c: chest(c)) for c in COLOURS}

# the reference chest: 52 x 38 pt, frontal (its base edge is level), ~18 deg from above (the lid top shows)
CHEST_LIGHT = dict(fill_color=(1.0, 0.8, 0.5), fill_lux=520.0, key_lux=2900.0, ibl_exp=-0.75)
_view = dict(yaw=3, pitch=15, frame=(56, 42), fill=(52 / 56, 38.5 / 42), fov=11, light=CHEST_LIGHT)

ASSETS = {
    "stageChestGreen": dict(model="chest_green", **_view),
    "stageChestBlue": dict(model="chest_blue", **_view),
    "stageChestPink": dict(model="chest_pink", **_view),
}
