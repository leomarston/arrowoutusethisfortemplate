"""Props held by the characters on the loading screen (not a recipe: no ASSETS): chunky glossy 3D arrows (the game's
arrow family: a thick extruded arrow with rounded edges) and the carrier's cardboard box.

Measured on store 8 / kickoff state.png (looked at only): the flyer's red arrow ~1.9 x 2.6 worker units (head up), the
small blue arrow ~0.5 x 0.7; the box ~1.9 u wide, 0.75 u tall, ~1.0 u deep, with two dark hand holes on its front and a
tape strip over the lid; arrows (purple, red, orange, blue) stick out of it.
"""
from __future__ import annotations

import numpy as np

import char_kit as K
from uikit import box, extrude, gloss, polygon2, satin, union  # noqa: F401

ARROW_COLOURS = {
    # face / shade / crease ramps (LUT over obscurance), the store icon's family (STYLE.md: yellow #FEBF0E/#FB8A03,
    # red #FA3633/#D4090B, blue #0292FE/#005FF1) extended to the loading pile's orange/purple
    "red": [(0.0, "#FF7A5E"), (0.35, "#F4492F"), (0.7, "#D62A1C"), (1.0, "#A3160F")],
    "orange": [(0.0, "#FFC46A"), (0.35, "#FA9A1C"), (0.7, "#E4700C"), (1.0, "#B24E06")],
    "blue": [(0.0, "#7FD0FF"), (0.35, "#2A9DF6"), (0.7, "#1071DF"), (1.0, "#0A4AB0")],
    "purple": [(0.0, "#D69CFF"), (0.35, "#AE63F0"), (0.7, "#8B40D6"), (1.0, "#6428A8")],
    "yellow": [(0.0, "#FFE27A"), (0.35, "#FEC21A"), (0.7, "#F39A08"), (1.0, "#C87404")],
    "green": [(0.0, "#B8F08A"), (0.35, "#7ACB43"), (0.7, "#4EA52C"), (1.0, "#33791C")],
}


def arrow_sdf(length=1.0, width=0.62, shaft=0.34, head_len=0.44, depth=0.13, round_=0.05):
    """A chunky arrow pointing +Y, centred on its bbox, in the XY plane (depth along Z)."""
    L, W, S, H = length, width, shaft, head_len
    y0, y1 = -L / 2, L / 2
    pts = [(-S / 2, y0), (S / 2, y0), (S / 2, y1 - H), (W / 2, y1 - H), (0.0, y1), (-W / 2, y1 - H), (-S / 2, y1 - H)]
    r = round_ * 0.9
    shape = polygon2(pts).offset(-r).offset(r)            # rounded corners (inset then grow)
    return extrude(shape, depth / 2, round=min(round_, depth / 2 * 0.95))


def arrow_mat(colour):
    return K.skin(f"arrow_{colour}", ARROW_COLOURS[colour], None, vfn=None, rough=0.26, ior=1.40, clearcoat=0.4,
                  cc_rough=0.15)


def place(sdf, center, up=(0, 1, 0), facing=(0, 0, 1)):
    R = K.frame_from(up, facing)
    return sdf.transform(R).translate(*np.asarray(center, float))


BOX = [(0.0, "#F4CB93"), (0.4, "#DDA66A"), (0.7, "#C28A4E"), (1.0, "#8E5E2E")]


def cardboard_box(w=1.9, h=0.72, d=1.0, wall=0.05, holes=True):
    """An open-top cardboard box (the lid flaps folded in), centred at the origin: (shell, holes, tape).
    holes=False (director round 2, the loading carrier): the two dark hand holes on the front read as a pair of EYES at
    game size; V1's box shows one small slot underneath -- dark is then None."""
    outer = box(w / 2, h / 2, d / 2, round=0.05)
    inner = box(w / 2 - wall, h / 2, d / 2 - wall, round=0.03).translate(0, wall * 1.5, 0)
    shell = outer.subtract(inner)
    tape = box(0.16, 0.012, d / 2 + 0.002, round=0.006).translate(0, h / 2 + 0.004, 0).intersect(
        box(0.2, 0.1, d / 2 + 0.01).translate(0, h / 2, 0))
    if not holes:
        return shell, None, tape
    holes = union(*[box(0.09, 0.055, 0.03, round=0.03).translate(sx * 0.42, h * 0.12, d / 2 + 0.005) for sx in (-1, 1)])
    shell = shell.subtract(holes.offset(0.004))
    tape = box(0.16, 0.012, d / 2 + 0.002, round=0.006).translate(0, h / 2 + 0.004, 0).intersect(
        box(0.2, 0.1, d / 2 + 0.01).translate(0, h / 2, 0))
    dark = union(*[box(0.085, 0.05, 0.02, round=0.028).translate(sx * 0.42, h * 0.12, d / 2 - 0.012) for sx in (-1, 1)])
    return shell, dark, tape
