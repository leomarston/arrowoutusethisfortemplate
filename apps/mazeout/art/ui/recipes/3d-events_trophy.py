"""3d-events lane: the gold trophy cup (trophyCup) -- Weekly Contest info ("Compete against your friends!").

Reference (LOOKED AT only): research/shots/meta-017 (and meta-016, 130/131; the same cup is the home nav trophy on
026). Measured on meta-017 (pt, y up from the foot's bottom): 57 wide over the handles x 53 tall; rim band r 20.6,
y 43.6..52.8 (flat, seen almost level); bowl r 18.4 at the top, a U curving in to r ~7.5 at y 17; knob collar r 8.3,
y 10..17; neck r 6; flared foot r 15.5, y 0..8; loop handles out to 28.5, y 24..42, tube ~2.8, a small hole; an
orange rounded up-arrow emblem on the bowl front (17 wide, y 22..41: head 12.5 tall, shaft 10 wide). Gold #FFC00C
(highlights #FFE05A, shade #F2A200); arrow #FF6410 (edge #E04E0A). Units: 1 world unit = 40 pt.
"""
from __future__ import annotations

import math

from uikit import (Part, cylinder, extrude, gloss, polygon2, revolve, rounded_polygon2, spline_profile, torus, union,  # noqa: F401
                   capped_cone)

VOXEL = 0.006
PT = 1.0 / 40.0


def P(x):
    return x * PT


GOLD = "#FFC00C"
ARROW = "#FF5E0E"


def cup_parts():
    # the stand: a wide slab with straight sides, its top sloping in to the neck (a trapezoid seen level)
    slab = cylinder(P(15.6), P(2.5), round=P(1.4)).translate(0, P(2.5), 0)
    slope = capped_cone(P(2.4), P(15.0), P(6.8), round=P(0.9)).translate(0, P(7.2), 0)
    foot = union(slab, slope, k=P(1.0))
    neck = cylinder(P(6.4), P(1.4)).translate(0, P(10.4), 0)
    knob = cylinder(P(8.4), P(3.1), round=P(2.5)).translate(0, P(14.2), 0)
    bowl = revolve(spline_profile([(0, P(16.4)), (P(8.4), P(17.0)), (P(13.4), P(20.6)), (P(16.8), P(26.0)),
                                   (P(18.2), P(32.0)), (P(18.5), P(38.0)), (P(18.4), P(44.0)), (0, P(44.0))], samples=96))
    rim = cylinder(P(20.6), P(4.6), round=P(2.2)).translate(0, P(48.2), 0)
    # ear handles: an oval loop each side, thick on the outside (6.6 pt), thin top and bottom (3-4 pt), a narrow tall
    # hole (3.5 x 11 pt) against the bowl; its inner part is buried in the bowl
    def ellipse(cx, cy, ax, ay, n=72):
        return polygon2([(P(cx + ax * math.cos(t)), P(cy + ay * math.sin(t)))
                         for t in [2 * math.pi * k / n for k in range(n)]])
    ear2 = ellipse(21.2, 33.2, 7.3, 9.0).subtract(ellipse(20.3, 33.0, 2.1, 5.6))
    ear = extrude(ear2, P(2.9), round=P(2.6))
    handles = union(ear, ear.transform([[-1, 0, 0], [0, 1, 0], [0, 0, 1]]))
    body = union(foot, neck, knob, bowl, k=P(1.2))
    # the emblem: a rounded up-arrow raised off the bowl front, following its curvature
    arrow2 = rounded_polygon2([(P(0), P(41.2)), (P(8.8), P(28.2)), (P(5.0), P(28.2)), (P(5.0), P(22.2)), (P(-5.0), P(22.2)),
                               (P(-5.0), P(28.2)), (P(-8.8), P(28.2))],
                              [P(2.6), P(1.6), P(0.9), P(1.4), P(1.4), P(0.9), P(1.6)], n_arc=8)
    front = extrude(arrow2, P(20)).translate(0, 0, P(20))
    mark = bowl.offset(P(1.5)).intersect(front, k=P(1.1))
    gold = gloss("trophy_gold", GOLD, rough=0.26, ior=1.45)
    return [
        Part("body", body, gold),
        Part("rim", rim, gold),
        Part("handles", handles, gold, voxel=0.005),
        Part("arrow", mark, gloss("trophy_arrow", ARROW, rough=0.28, ior=1.40), voxel=0.0045),
    ], VOXEL


MODELS = {"trophy": cup_parts}

# no cast shadows: the reference cup has none (the bowl's shadow drew a hard diagonal band across the knob)
TROPHY_LIGHT = dict(fill_color=(1.0, 0.82, 0.55), fill_lux=620.0, key_lux=3100.0, ibl_exp=-0.6, shadow=False)

ASSETS = {
    # 57 x 53 pt as measured, in a 62 x 58 frame (the same render scales up for bigger uses)
    "trophyCup": dict(model="trophy", yaw=0, pitch=0, frame=(62, 58), fill=(57 / 62, 53 / 58), fov=14,
                      light=TROPHY_LIGHT),
}
