"""Shared helpers for the UI-art 3D recipes (art/ui/recipes/*.py).

The recipes reuse the item pipeline's SDF toolbox, mesher and USD writer READ-ONLY (art/pipeline is shared with
the modelling lanes and is never edited from here). UI props are NOT game items: they live in art/ui/recipes/,
not art/pipeline/items/, so build.py --all never meshes them and art/out/catalog.json never lists them.

A recipe module defines
    MODELS = {"model_name": fn}        fn() -> list[Part]   (authoring units, +Y up, +Z toward the viewer)
    ASSETS = {"UIArtCase": spec}       spec: see ui3d.py (model or scene, view, frame in pt, padding, post)
"""
from __future__ import annotations

import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
UI = os.path.dirname(HERE)
ART = os.path.dirname(UI)
APP = os.path.dirname(ART)
PIPE = os.path.join(ART, "pipeline")
if PIPE not in sys.path:
    sys.path.insert(0, PIPE)

import numpy as np  # noqa: E402

from sdf import (F, SDF, box, capsule, capped_cone, chamfer_cylinder, circle2, cylinder, ellipsoid, extrude,  # noqa: E402,F401
                 fillet_points, path_tube, plane, polygon2, rect2, revolve, round_cone, rounded_polygon2, sphere,
                 spline_profile, star2, torus, union, SDF2, capsule2, round_cone2)
from mesher import Material, Part  # noqa: E402,F401
import palette as PAL  # noqa: E402,F401


# ------------------------------------------------------------------ materials (UI renders are glossier than pile items)

def mat(name, color, rough=0.38, ior=1.3, **kw):
    """Toy plastic with a visible broad highlight (the UI renders read glossier than the board items)."""
    return Material(name, color, roughness=rough, ior=ior, **kw)


def gloss(name, color, **kw):
    kw.setdefault("rough", 0.30)
    kw.setdefault("ior", 1.38)
    return mat(name, color, **kw)


def satin(name, color, **kw):
    kw.setdefault("rough", 0.48)
    kw.setdefault("ior", 1.22)
    return mat(name, color, **kw)


def metal(name, color, **kw):
    """Brushed toy metal: bright albedo, nearly dielectric (see STYLE.md: metallic > 0 renders olive under the IBL)."""
    kw.setdefault("rough", 0.34)
    kw.setdefault("ior", 1.45)
    return Material(name, color, roughness=kw.pop("rough"), ior=kw.pop("ior"), metallic=kw.pop("metallic", 0.05), **kw)


def glass(name, color="#CFEFFF", opacity=0.45, **kw):
    return Material(name, color, roughness=kw.pop("rough", 0.12), ior=kw.pop("ior", 1.45), opacity=opacity, **kw)


def textured(m: Material, fn, size=512):
    from dataclasses import replace
    return replace(m, texture=fn, texture_size=size)


# ------------------------------------------------------------------ 2D shapes

def heart2(w=1.0, h=0.9, round_=0.0):
    """Chubby cartoon heart centred on the origin, width w, height h (the lobes are round, the tip soft)."""
    r = 0.285 * w
    cx = 0.215 * w
    cy = 0.5 * h - r
    tip = (0.0, -0.5 * h)
    lob_l = circle2(r).translate(-cx, cy)
    lob_r = circle2(r).translate(cx, cy)

    def fn(p):
        # the lower V: a round cone from each lobe to the tip
        d1 = round_cone2((-cx, cy), tip, r, 0.06 * w)(p)
        d2 = round_cone2((cx, cy), tip, r, 0.06 * w)(p)
        return np.minimum(np.minimum(lob_l(p), lob_r(p)), np.minimum(d1, d2)) - round_

    return SDF2(fn, np.array([-0.5 * w - 0.05, -0.5 * h - 0.05]), np.array([0.5 * w + 0.05, 0.5 * h + 0.05]))


def pillow(s2: SDF2, R, H):
    """Inflate a 2D shape into a soft pillow: the rim rises as a quarter ellipse (R in plane, H in depth) and the
    middle is flat where the shape is wider than 2R. Symmetric about z = 0 (half-thickness H)."""
    return extrude(s2, R, round=R).scale_xyz(1, 1, H / R)


def smooth_extrude(s2: SDF2, half_depth, round_):
    """Extrude with a rounded rim of radius round_ (<= half_depth); the outline stays s2."""
    return extrude(s2, half_depth, round=round_)


def rbox(w, h, d, r, center=(0, 0, 0)):
    """Rounded box with FULL sizes (w, h, d)."""
    return box(w / 2, h / 2, d / 2, round=r).translate(*center)


def hazard_stripes(yellow="#F4C21A", black="#2B2B2B", n=18, slant=0.9):
    return PAL.stripes([yellow, black], n=n, axis="u", slant=slant, soft=0.002)


def wood_grain(base, dark, light=None, n=28, strength=0.35, seed=0, axis="v"):
    return PAL.streaks(base, dark, light, n_lines=n, strength=strength, seed=seed, axis=axis)


def rot_y(deg):
    a = math.radians(deg)
    return np.array([[math.cos(a), 0, math.sin(a)], [0, 1, 0], [-math.sin(a), 0, math.cos(a)]])


def rot_x(deg):
    a = math.radians(deg)
    return np.array([[1, 0, 0], [0, math.cos(a), -math.sin(a)], [0, math.sin(a), math.cos(a)]])


def rot_z(deg):
    a = math.radians(deg)
    return np.array([[math.cos(a), -math.sin(a), 0], [math.sin(a), math.cos(a), 0], [0, 0, 1]])


# ------------------------------------------------------------------ glyphs and arcs as 2D SDFs

# OFL fonts picked by the fonts lane land in design/fonts/ under NEUTRAL names; until then glyph2() callers must pass
# `font=` explicitly (the macOS system font below is a placeholder for spike renders only, never shipped).
FONT_DISPLAY = os.path.join(APP, "design", "fonts", "Display-Regular.ttf")
FONT_ROUND = os.path.join(APP, "design", "fonts", "Rounded-ExtraBold.ttf")
FONT_PLACEHOLDER = "/System/Library/Fonts/Supplemental/Arial Rounded Bold.ttf"


def glyph2(text, height, font=FONT_DISPLAY, px=512, center=True):
    """Text rendered by an OFL font -> 2D SDF (exact-ish, from a distance transform of a 512 px raster).
    `height` = the ink height in world units; the ink box is centred on the origin."""
    from PIL import Image as _I, ImageDraw as _D, ImageFont as _F
    from scipy import ndimage
    f = _F.truetype(font, px)
    bb = f.getbbox(text)
    W, H = bb[2] - bb[0] + 64, bb[3] - bb[1] + 64
    im = _I.new("L", (W, H), 0)
    _D.Draw(im).text((32 - bb[0], 32 - bb[1]), text, font=f, fill=255)
    a = np.asarray(im) > 127
    ys, xs = np.nonzero(a)
    ink_h = ys.max() - ys.min() + 1
    s = height / ink_h  # world units per px
    cx, cy = (xs.min() + xs.max()) / 2, (ys.min() + ys.max()) / 2
    din = ndimage.distance_transform_edt(a)
    dout = ndimage.distance_transform_edt(~a)
    d = (dout - din).astype(np.float32) * s  # >0 outside
    from scipy.ndimage import map_coordinates

    def fn(p):
        x = p[:, 0] / s + cx
        y = -p[:, 1] / s + cy
        v = map_coordinates(d, [y, x], order=1, mode="nearest")
        # outside the raster: grow with the distance to it
        ox = np.maximum(np.maximum(-x, x - (W - 1)), 0) * s
        oy = np.maximum(np.maximum(-y, y - (H - 1)), 0) * s
        return (v + np.sqrt(ox * ox + oy * oy)).astype(F)
    lo = np.array([(xs.min() - cx) * s - 0.02, -(ys.max() - cy) * s - 0.02])
    hi = np.array([(xs.max() - cx) * s + 0.02, -(ys.min() - cy) * s + 0.02])
    return SDF2(fn, lo, hi)


def arc2(R, t, a0, a1, center=(0.0, 0.0)):
    """A stroke of width t along a circle of radius R from angle a0 to a1 (deg, CCW), round caps."""
    c = np.array(center, float)
    A0, A1 = math.radians(a0), math.radians(a1)
    mid, half = (A0 + A1) / 2, (A1 - A0) / 2
    e0 = c + R * np.array([math.cos(A0), math.sin(A0)])
    e1 = c + R * np.array([math.cos(A1), math.sin(A1)])

    def fn(p):
        q = p - c.astype(F)
        ang = np.arctan2(q[:, 1], q[:, 0])
        rel = (ang - mid + math.pi) % (2 * math.pi) - math.pi
        inside = np.abs(rel) <= half
        d_ring = np.abs(np.sqrt((q * q).sum(1)) - R) - t / 2
        d0 = np.sqrt(((p - e0.astype(F)) ** 2).sum(1)) - t / 2
        d1 = np.sqrt(((p - e1.astype(F)) ** 2).sum(1)) - t / 2
        return np.where(inside, d_ring, np.minimum(d0, d1)).astype(F)
    return SDF2(fn, c - R - t, c + R + t)


def intersect2(a: SDF2, b: SDF2):
    fa, fb = a.fn, b.fn
    return SDF2(lambda p: np.maximum(fa(p), fb(p)), np.maximum(a.lo, b.lo), np.minimum(a.hi, b.hi))


def emboss(s2: SDF2, z0, height, round_=None):
    """A raised 2D mark standing on the plane z = z0 (toward +Z), height `height`, soft rounded top."""
    r = height * 0.45 if round_ is None else round_
    return extrude(s2, height, round=r).translate(0, 0, z0)


def raster_sdf2(mask, extent, blur_px=0.0):
    """A 2D SDF from a boolean raster `mask` (rows = +Y down) covering `extent` = (xmin, ymin, xmax, ymax).
    `blur_px` smooths the INSIDE of the distance field so an inflated pillow has no crease along the medial axis."""
    from scipy import ndimage
    from scipy.ndimage import map_coordinates
    m = np.asarray(mask, bool)
    H, W = m.shape
    xmin, ymin, xmax, ymax = extent
    s = (xmax - xmin) / W
    din = ndimage.distance_transform_edt(m)
    dout = ndimage.distance_transform_edt(~m)
    d = (dout - din).astype(np.float32)
    if blur_px > 0:
        inner = np.minimum(d, 0)
        bl = ndimage.gaussian_filter(inner, blur_px)
        # keep the zero crossing: blend in the blur only away from the edge
        w = np.clip(-d / (2 * blur_px), 0, 1)
        d = np.where(d < 0, inner * (1 - w) + np.minimum(bl, -0.01) * w, d)
    d *= s

    def fn(p):
        x = (p[:, 0] - xmin) / s - 0.5
        y = (ymax - p[:, 1]) / s - 0.5
        v = map_coordinates(d, [y, x], order=1, mode="nearest")
        ox = np.maximum(np.maximum(-x, x - (W - 1)), 0) * s
        oy = np.maximum(np.maximum(-y, y - (H - 1)), 0) * s
        return (v + np.sqrt(ox * ox + oy * oy)).astype(F)
    return SDF2(fn, np.array([xmin, ymin]), np.array([xmax, ymax]))


def poly_mask(pts, extent, px=768, soften_px=0.0):
    """Rasterise a polygon (world coords) into a mask over `extent`; `soften_px` rounds sharp corners."""
    from PIL import Image as _I, ImageDraw as _D, ImageFilter as _Fl
    xmin, ymin, xmax, ymax = extent
    W = px
    H = int(round(px * (ymax - ymin) / (xmax - xmin)))
    im = _I.new("L", (W, H), 0)
    q = [((x - xmin) / (xmax - xmin) * W, (ymax - y) / (ymax - ymin) * H) for x, y in pts]
    _D.Draw(im).polygon(q, fill=255)
    if soften_px > 0:
        im = im.filter(_Fl.GaussianBlur(soften_px))
    return np.asarray(im) > 127


def heart_curve(n=400, w=1.0):
    """The classic parametric heart outline, scaled to width w and centred."""
    t = np.linspace(0, 2 * math.pi, n, endpoint=False)
    x = 16 * np.sin(t) ** 3
    y = 13 * np.cos(t) - 5 * np.cos(2 * t) - 2 * np.cos(3 * t) - np.cos(4 * t)
    x = x / 32 * w
    y = (y - (y.max() + y.min()) / 2) / 32 * w
    return np.stack([x, y], 1)
