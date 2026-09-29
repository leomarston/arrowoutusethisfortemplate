#!/usr/bin/env python3
"""SVG lane (route B2): the fixed flat-glossy icons, glyphs, unlock illustrations, badges, logo and small FX sprites.

    ~/.venvs/mf3d/bin/python art/ui/src/svg/gen_icons.py iconCoin glyphGear     # -> build/ui-art/svgsrc/<case>.svg
    # the manifest batch builds them for real (art/tools/art_batch.py, source "art/ui/src/svg/gen_icons.py:<case>")

Units inside every SVG: @3x px (1 unit = 1/3 pt), y down; the root carries the frame in pt (svg_doc). Every shape is a
primitive (circles, rounded rects, superellipses, stars, hexagons, arcs, our OFL font's glyphs) with parameters MEASURED
on the captures (sizes / positions / colour samples, see the comment above each case); nothing is traced, nothing is
sampled into an asset. Colours are STYLE.md §D tokens or profile samples written into the comments.

Translatable text is never baked. Numbers that change at runtime (counters, lives, ranks, prices) are live text drawn by
the app over the art (manifest `text_live`); the case comment names the point where the text goes.
"""
from __future__ import annotations

import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.dirname(HERE)
if SRC not in sys.path:
    sys.path.insert(0, SRC)
from shapes import fmt, heart2_path, poly_path, superellipse, svg_doc  # noqa: E402
from gen_board import _round_poly, hexagon, rrect  # noqa: E402  (read-only reuse of the pipeline's primitives)

F = fmt


# ====================================================================================== document helper
class Doc:
    """One SVG document: frame in pt, drawing in px (x3). Unique ids for defs; canvas-wide filter regions (a blur on a
    thin line must not be clipped by its bbox)."""

    def __init__(self, w_pt, h_pt):
        self.w, self.h = w_pt, h_pt
        self.W, self.H = w_pt * 3, h_pt * 3
        self.defs, self.body, self.n = [], [], 0

    def _id(self, p):
        self.n += 1
        return f"{p}{self.n}"

    @staticmethod
    def _stops(stops):
        out = []
        for st in stops:
            o, c = st[0], st[1]
            a = st[2] if len(st) > 2 else 1
            out.append(f'<stop offset="{F(o)}" stop-color="{c}"' + ("" if a == 1 else f' stop-opacity="{F(a)}"') + "/>")
        return "".join(out)

    def lin(self, stops, x1, y1, x2, y2):
        i = self._id("l")
        self.defs.append(f'<linearGradient id="{i}" gradientUnits="userSpaceOnUse" x1="{F(x1)}" y1="{F(y1)}" x2="{F(x2)}" '
                         f'y2="{F(y2)}">{self._stops(stops)}</linearGradient>')
        return f"url(#{i})"

    def rad(self, stops, cx, cy, r, fx=None, fy=None, sx=1.0, sy=1.0, rot=0.0):
        i = self._id("r")
        tr = ""
        if sx != 1 or sy != 1 or rot:
            tr = (f' gradientTransform="translate({F(cx)} {F(cy)}) rotate({F(rot)}) scale({F(sx)} {F(sy)}) '
                  f'translate({F(-cx)} {F(-cy)})"')
        f = f' fx="{F(fx)}" fy="{F(fy)}"' if fx is not None else ""
        self.defs.append(f'<radialGradient id="{i}" gradientUnits="userSpaceOnUse" cx="{F(cx)}" cy="{F(cy)}" r="{F(r)}"{f}{tr}>'
                         f'{self._stops(stops)}</radialGradient>')
        return f"url(#{i})"

    def blur(self, std):
        i = self._id("f")
        # region in the user space of the element using it, which may be a scaled group: make it generous
        self.defs.append(f'<filter id="{i}" filterUnits="userSpaceOnUse" x="{F(-3 * self.W)}" y="{F(-3 * self.H)}" width="{F(8 * self.W)}" '
                         f'height="{F(8 * self.H)}"><feGaussianBlur stdDeviation="{F(std)}"/></filter>')
        return f"url(#{i})"

    def clip(self, *ds, rule="nonzero"):
        i = self._id("c")
        self.defs.append(f'<clipPath id="{i}">' + "".join(f'<path d="{d}" clip-rule="{rule}"/>' for d in ds) + "</clipPath>")
        return f"url(#{i})"

    def mask(self, inner):
        i = self._id("m")
        self.defs.append(f'<mask id="{i}" maskUnits="userSpaceOnUse" x="{F(-3 * self.W)}" y="{F(-3 * self.H)}" width="{F(8 * self.W)}" '
                         f'height="{F(8 * self.H)}">{inner}</mask>')
        return f"url(#{i})"

    def add(self, *els):
        self.body.extend(els)

    def svg(self):
        return svg_doc(self.w, self.h, "\n".join(self.body), "".join(self.defs))


# ====================================================================================== shape helpers (px)
def circ(cx, cy, r):
    return f"M{F(cx - r)} {F(cy)}A{F(r)} {F(r)} 0 1 0 {F(cx + r)} {F(cy)}A{F(r)} {F(r)} 0 1 0 {F(cx - r)} {F(cy)}Z"


def ell(cx, cy, rx, ry, deg=0.0, N=72):
    t = math.radians(deg)
    c, s = math.cos(t), math.sin(t)
    pts = []
    for k in range(N):
        a = 2 * math.pi * k / N
        x, y = rx * math.cos(a), ry * math.sin(a)
        pts.append((cx + c * x - s * y, cy + s * x + c * y))
    return poly_path(pts)


def rr(x0, y0, x1, y1, r):
    return rrect(x0, y0, x1, y1, min(r, (x1 - x0) / 2, (y1 - y0) / 2))


def star_pts(cx, cy, R, r, n=5, rot=-90.0):
    pts = []
    for k in range(2 * n):
        a = math.radians(rot + 180.0 * k / n)
        rad = R if k % 2 == 0 else r
        pts.append((cx + rad * math.cos(a), cy + rad * math.sin(a)))
    return pts


def star(cx, cy, R, r, n=5, rot=-90.0, round_=0.0):
    pts = star_pts(cx, cy, R, r, n, rot)
    return poly_path(_round_poly(pts, round_, 6) if round_ else pts)


def arc_path(cx, cy, r, a0, a1):
    """Open arc from angle a0 to a1 (deg, screen: 0 = right, 90 = down), sweeping positive."""
    x0, y0 = cx + r * math.cos(math.radians(a0)), cy + r * math.sin(math.radians(a0))
    x1, y1 = cx + r * math.cos(math.radians(a1)), cy + r * math.sin(math.radians(a1))
    large = 1 if (a1 - a0) % 360 > 180 else 0
    return f"M{F(x0)} {F(y0)}A{F(r)} {F(r)} 0 {large} 1 {F(x1)} {F(y1)}"


def rounded(pts, r, n=6):
    return poly_path(_round_poly(pts, r, n))


def xf(pts, dx=0.0, dy=0.0, deg=0.0, sx=1.0, sy=1.0, ox=0.0, oy=0.0):
    t = math.radians(deg)
    c, s = math.cos(t), math.sin(t)
    out = []
    for x, y in pts:
        x, y = (x - ox) * sx, (y - oy) * sy
        out.append((ox + c * x - s * y + dx, oy + s * x + c * y + dy))
    return out


def rect_pts(x0, y0, x1, y1):
    return [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]


# ====================================================================================== the outlined "toon" glyph
def toon(parts, fill, outline, ow, drop=0.0, drop_col=None, rule="nonzero"):
    """A cartoon glyph = the UNION of parts with one outline around it and an optional solid drop (the outline shape
    moved straight down, the house style of every outlined label/glyph: fonts.md §6). parts: ("f", d) closed filled path,
    ("s", d, w) a stroked path of width w (round caps/joins). Returns the SVG layers, back to front."""
    def layer(col, grow, dy, extra=""):
        out = []
        for p in parts:
            if p[0] == "f":
                if grow > 0:
                    out.append(f'<path d="{p[1]}" fill="{col}" fill-rule="{rule}" stroke="{col}" stroke-width="{F(2 * grow)}" '
                               f'stroke-linejoin="round"/>')
                else:
                    out.append(f'<path d="{p[1]}" fill="{col}" fill-rule="{rule}"/>')
            else:
                out.append(f'<path d="{p[1]}" fill="none" stroke="{col}" stroke-width="{F(p[2] + 2 * grow)}" '
                           f'stroke-linecap="round" stroke-linejoin="round"/>')
        tr = f' transform="translate(0 {F(dy)})"' if dy else ""
        return f"<g{tr}{extra}>" + "".join(out) + "</g>"
    g = []
    if drop:
        g.append(layer(drop_col or outline, ow, drop))
    if ow:
        g.append(layer(outline, ow, 0))
    g.append(layer(fill, 0, 0))
    return g


def toon_fill_only(parts, fill, rule="nonzero"):
    return toon(parts, fill, None, 0, rule=rule)[-1]


def toon3d(parts, face, side, outline, ow, depth, rule="nonzero", steps=6):
    """An extruded toon glyph (the gear on the blue buttons): the face, its side wall swept `depth` px straight down in
    `side`, and ONE outline around the union of both."""
    def layer(col, grow, dy):
        out = []
        for p in parts:
            if p[0] == "f":
                st = f' stroke="{col}" stroke-width="{F(2 * grow)}" stroke-linejoin="round"' if grow > 0 else ""
                out.append(f'<path d="{p[1]}" fill="{col}" fill-rule="{rule}"{st}/>')
            else:
                out.append(f'<path d="{p[1]}" fill="none" stroke="{col}" stroke-width="{F(p[2] + 2 * grow)}" stroke-linecap="round" '
                           f'stroke-linejoin="round"/>')
        return f'<g transform="translate(0 {F(dy)})">' + "".join(out) + "</g>"
    g = [layer(outline, ow, depth * k / steps) for k in range(steps + 1)]
    g += [layer(side, 0, depth * k / steps) for k in range(steps, 0, -1)]
    g.append(layer(face, 0, 0))
    return g


def scaled(d, k, cx_from, cy_from, cx_to, cy_to):
    """Open a group that maps (cx_from, cy_from) to (cx_to, cy_to) with scale k (close it with d.add('</g>'))."""
    d.add(f'<g transform="translate({F(cx_to)} {F(cy_to)}) scale({F(k)}) translate({F(-cx_from)} {F(-cy_from)})">')


# ====================================================================================== HUD: coin
# Shot 003 hud.coinIcon (23.7 x 24.4 pt; home 026: 34 pt): a frontal gold coin with a little thickness showing below.
# Vertical profile through the centre: outline #98776A/#AB7C60 (soft, 1 px), rim top #FFF40F -> #FFE800, a dark orange
# GROOVE #D56C00 (the face is recessed), face #FEF100 (top) -> #FBDC00 -> #F8D100 (bottom), groove #D56200 -> #CD6A00,
# rim bottom #E18C00, a bright rim-bottom reflection #FCF591, the edge/thickness #F4C200 -> #CA6800. Star: rounded
# 5-point, face-coloured (#FBDD00), orange outline #D36400 (#EFA801 lit side). Rim band = outer 26 % of the radius.
def icon_coin(W=39, H=39, shadow=True):
    """Polish lane r3 (grader A: the outer rim read lighter and thinner than 003/026, and the 30 pt frame was drawn at
    1.28x on home). Re-measured on 002's clean home coin (34.0 x 34.3 pt of ink = 103 px; face radius R 48.5 px):
      vertical centre column  top edge light (#E6D25A, #FFFB9B) -> rim #FFF300 .. #FFE500 to 0.73 R, a #FFFB26 inner line,
                              the recess's top WALL in shadow 0.72..0.62 R (#D75E00 -> #B23C00), face #ECA700 / #F7C400
                              above the star; below it #B04400 (the star's extrusion) -> #E18C00; a 1 px groove #D45B05 at
                              0.69 R, a bright lip #FFF97A, rim #FBDE00 -> #F4C100, a reflection #FBEE3B at 0.97 R, then
                              the coin's THICKNESS 6 px (#E69014 -> #C15B00) and a dark outline #85430F
      horizontal centre row   outline #9A4410 / #BD6B09, rim 14 px (0.29 R; #F4C700 left, lit #FFFD00 at the right edge),
                              groove 3 px, face 0.67 R; star 50 x 45 px incl. its orange border + extrusion (chubby arms)
    Drawn so the INK is 34.4 pt in the 39 pt frame (home draws it at 38.5 pt = 0.99x; the HUD at 26.7 pt, downsampled)."""
    return _coin(W, H, shadow)


def _coin(W, H, shadow=True):
    d = Doc(W, H)
    s = W * 3 / 117.0
    R, t = 48.5 * s, 6.0 * s
    cx, cy = W * 1.5, H * 1.5 - t / 2 - 0.4 * s
    if shadow:
        d.add(f'<path d="{circ(cx, cy + t + 1.6 * s, R)}" fill="#132223" fill-opacity="0.34" filter="{d.blur(1.7 * s)}"/>')
    # thickness (the coin's edge below the face) + the dark outline under it
    d.add(f'<path d="{circ(cx, cy + t, R)}" fill="{d.lin([(0, "#E8961A"), (0.55, "#E08A04"), (0.8, "#D07300"), (1, "#BC5600")], 0, cy, 0, cy + R + t)}" '
          f'stroke="#804618" stroke-width="{F(1.5 * s)}"/>')
    # the face disc: outline light at the top, brown on the sides
    d.add(f'<path d="{circ(cx, cy, R)}" fill="none" stroke="{d.lin([(0, "#D9B83A"), (0.2, "#B06A12"), (0.5, "#8E400E"), (1, "#84400E")], 0, cy - R, 0, cy + R)}" '
          f'stroke-width="{F(1.9 * s)}"/>')
    d.add(f'<path d="{circ(cx, cy, R)}" fill="{d.lin([(0, "#FFF200"), (0.12, "#FFEF00"), (0.4, "#FDE400"), (0.62, "#FBDC00"), (0.82, "#F7CF00"), (1, "#F4C200")], 0, cy - R, 0, cy + R)}"/>')
    rimclip = d.clip(circ(cx, cy, R))
    # rim shading: the left side a touch deeper (#F4C700), the right edge lit (#FFFD00), a light top edge, the bottom
    # reflection near the edge
    d.add(f'<g clip-path="{rimclip}">'
          f'<path d="{circ(cx + 3.0 * s, cy, R)}" fill="none" stroke="#E9B000" stroke-opacity="0.55" stroke-width="{F(5 * s)}" filter="{d.blur(1.6 * s)}"/>'
          f'<path d="{arc_path(cx, cy, R - 1.3 * s, -38, 38)}" fill="none" stroke="#FFFD30" stroke-width="{F(2.0 * s)}" stroke-linecap="round" filter="{d.blur(0.35 * s)}"/>'
          f'<path d="{arc_path(cx, cy, R - 1.2 * s, 218, 322)}" fill="none" stroke="#FFFBA0" stroke-width="{F(2.0 * s)}" stroke-linecap="round" filter="{d.blur(0.4 * s)}"/>'
          f'<path d="{arc_path(cx, cy, R - 2.3 * s, 48, 132)}" fill="none" stroke="#FBEE3B" stroke-width="{F(2.0 * s)}" stroke-linecap="round" filter="{d.blur(0.45 * s)}"/>'
          f'</g>')
    # the recess: groove ring at 0.73 R, its top wall in shadow, a bright lower lip; the face circle sits LOWER in it
    rg = 0.73 * R
    rf, fdy = 0.655 * R, 0.035 * R
    d.add(f'<path d="{arc_path(cx, cy, rg + 0.7 * s, 200, 340)}" fill="none" stroke="#FFFB40" stroke-width="{F(1.3 * s)}" stroke-linecap="round"/>')
    d.add(f'<path d="{circ(cx, cy, rg)}" fill="{d.lin([(0, "#C85600"), (0.18, "#B23C00"), (0.55, "#CC6200"), (1, "#D45B05")], 0, cy - rg, 0, cy + rg)}"/>')
    d.add(f'<path d="{arc_path(cx, cy, rg + 1.0 * s, 38, 142)}" fill="none" stroke="#FFF97A" stroke-width="{F(1.9 * s)}" stroke-linecap="round"/>')
    fc = circ(cx, cy + fdy, rf)
    d.add(f'<path d="{fc}" fill="{d.lin([(0, "#D37200"), (0.1, "#EAA400"), (0.3, "#F2B400"), (0.62, "#ECA200"), (1, "#E28E00")], 0, cy + fdy - rf, 0, cy + fdy + rf)}"/>')
    d.add(f'<g clip-path="{d.clip(fc)}"><path d="{circ(cx, cy + fdy + 3.2 * s, rf + 2.6 * s)}" fill="none" stroke="#B84600" stroke-opacity="0.75" '
          f'stroke-width="{F(4.2 * s)}" filter="{d.blur(1.1 * s)}"/></g>')
    # the star: chubby (inner 0.6 of outer, big round tips), a little wider than tall, raised: an orange border and a
    # deep orange extrusion straight down (#DC6B00 -> #B04400), a light top edge
    scx, scy = cx, cy - 0.035 * R
    Ro, ri = 0.55 * R, 0.34 * R
    pts = [(x, scy + (y - scy) * 0.97) for x, y in star_pts(scx, scy, Ro, ri)]
    sp = poly_path(_round_poly(pts, 7.0 * s, 6))
    ext = 3.6 * s
    for k in range(6, 0, -1):
        d.add(f'<path d="{sp}" fill="#B04400" stroke="#B04400" stroke-width="{F(2.8 * s)}" stroke-linejoin="round" '
              f'transform="translate(0 {F(ext * k / 6)})"/>')
    d.add(f'<path d="{sp}" fill="#DC6E00" stroke="{d.lin([(0, "#EE9A10"), (0.5, "#DC6E00"), (1, "#D06000")], 0, scy - Ro, 0, scy + Ro)}" '
          f'stroke-width="{F(2.8 * s)}" stroke-linejoin="round"/>')
    d.add(f'<path d="{sp}" fill="{d.lin([(0, "#FFF45A"), (0.18, "#FFF000"), (0.55, "#FCDF00"), (1, "#F6CC00")], 0, scy - Ro, 0, scy + Ro)}"/>')
    d.add(f'<g clip-path="{d.clip(sp)}"><path d="{sp}" fill="none" stroke="#FFF8E8" stroke-opacity="0.9" stroke-width="{F(2.2 * s)}" '
          f'transform="translate({F(0.6 * s)} {F(1.6 * s)})" filter="{d.blur(0.5 * s)}"/>'
          f'<path d="{sp}" fill="none" stroke="#E9A400" stroke-opacity="0.55" stroke-width="{F(2.4 * s)}" '
          f'transform="translate(0 {F(-1.8 * s)})" filter="{d.blur(0.8 * s)}"/></g>')
    return d.svg()


def icon_coin_r2(W=30, H=30, shadow=True):
    """Round 2's coin (kept for comparison only; not in CASES)."""
    d = Doc(W, H)
    s = W * 3 / 90.0
    cx, cy, R, t = W * 1.5, H * 1.5 - 1.8 * s, 39.5 * s, 3.8 * s
    if shadow:
        d.add(f'<path d="{circ(cx, cy + t + 1.5 * s, R)}" fill="#5C3919" fill-opacity="0.3" filter="{d.blur(1.6 * s)}"/>')
    # thickness (the coin's edge seen below the face): #F4C200 -> #CA6800, soft brown outline
    d.add(f'<path d="{circ(cx, cy + t, R)}" fill="{d.lin([(0, "#F4C200"), (0.7, "#E49000"), (1, "#C46200")], 0, cy - R + t, 0, cy + R + t)}" '
          f'stroke="#945E0E" stroke-width="{F(1.4 * s)}"/>')
    # rim: bright yellow, a light reflection near its lower edge (#FFEB69 / #FCF591)
    d.add(f'<path d="{circ(cx, cy, R)}" fill="{d.lin([(0, "#FFF53A"), (0.2, "#FFEC00"), (0.6, "#F9D600"), (0.9, "#F4C400"), (1, "#F2BC00")], 0, cy - R, 0, cy + R)}" '
          f'stroke="#A8622A" stroke-width="{F(1.2 * s)}"/>')
    d.add(f'<path d="{arc_path(cx, cy, R - 2.6 * s, 40, 140)}" fill="none" stroke="#FFF08A" stroke-opacity="0.95" '
          f'stroke-width="{F(2.4 * s)}" stroke-linecap="round" filter="{d.blur(0.5 * s)}"/>')
    d.add(f'<path d="{arc_path(cx, cy, R - 3.0 * s, 198, 250)}" fill="none" stroke="#FFFBF2" stroke-opacity="0.95" '
          f'stroke-width="{F(2.4 * s)}" stroke-linecap="round" filter="{d.blur(0.5 * s)}"/>')
    # groove ring #D56C00 around the recessed ORANGE face (#EDA900 / #F19C00 top in shade, #E18C00 bottom), and the
    # groove's lit lower lip #FCF591
    rg = R * 0.70
    d.add(f'<path d="{arc_path(cx, cy, rg + 2.2 * s, 30, 150)}" fill="none" stroke="#FFF7A0" stroke-opacity="0.9" '
          f'stroke-width="{F(1.8 * s)}" stroke-linecap="round"/>')
    d.add(f'<path d="{circ(cx, cy, rg)}" fill="#D06200"/>')
    rf = rg - 2.2 * s
    d.add(f'<path d="{circ(cx, cy, rf)}" fill="{d.lin([(0, "#EA9C00"), (0.3, "#F0A800"), (0.7, "#EDA400"), (1, "#E28E00")], 0, cy - rf, 0, cy + rf)}"/>')
    d.add(f'<g clip-path="{d.clip(circ(cx, cy, rf))}"><path d="{circ(cx, cy + 2.6 * s, rf + 2.4 * s)}" fill="none" stroke="#C86A00" '
          f'stroke-opacity="0.6" stroke-width="{F(3.4 * s)}" filter="{d.blur(0.9 * s)}"/></g>')
    # star: 10 pt across on a 24 pt coin -> R 0.46 of the coin; yellow #FBD900 -> #F8D100, outline #D36400 (#D45F00 on
    # the shaded right), a slightly darker drop to the lower right
    sp = star(cx, cy + 0.9 * s, 18.5 * s, 9.6 * s, round_=4.2 * s)
    d.add(f'<path d="{sp}" fill="#C45400" stroke="#C45400" stroke-width="{F(3.2 * s)}" stroke-linejoin="round" '
          f'transform="translate({F(0.7 * s)} {F(1.5 * s)})"/>')
    d.add(f'<path d="{sp}" fill="none" stroke="#D66A00" stroke-width="{F(3.2 * s)}" stroke-linejoin="round"/>')
    d.add(f'<path d="{sp}" fill="{d.lin([(0, "#FFF45A"), (0.35, "#FEE600"), (1, "#F8D000")], 0, cy - 18 * s, 0, cy + 16 * s)}"/>')
    d.add(f'<g clip-path="{d.clip(sp)}"><path d="{sp}" fill="none" stroke="#FFFAEC" stroke-opacity="0.85" stroke-width="{F(2.0 * s)}" '
          f'transform="translate({F(1.0 * s)} {F(1.4 * s)})" filter="{d.blur(0.5 * s)}"/></g>')
    return d.svg()


# ====================================================================================== HUD: green plus badge
# Shot 013 / 026 (home.plusBadge circle 18.7 pt): a glossy green disc with a dark-green rim, a cream plus (#F9F1E7 /
# #FFFDEE) with a thin dark-green outline; bright top highlight. Frame 16 pt (the app scales it to the 18.7 pt slot).
def icon_plus_green(W=24, H=24):
    """Polish lane r3, re-measured on 002 (home coin pill; the shell draws this frame in a 23.5 pt rect, so the frame is
    24 pt now, not upscaled): a flat VIVID green disc 18.5 pt across (#00DB00 .. #00E400, #00D500 low), a dark-green edge
    ring ~3 px (#007402 .. #026E02; 6 px dark at the bottom, #00BC01 -> #006A01), a light-green inner ring right inside it
    (#72FD59 at the top, #3DDA30 on the sides); a SHORT CHUNKY cream plus: 0.545 of the disc across, arms 0.164 thick
    (#FFFEF9 top -> #FFF9D4 bottom), a 1.5 px dark-green outline #025225 and a 4 px solid drop of it straight down."""
    d = Doc(W, H)
    s = W * 3 / 72.0
    R = 28.3 * s
    cx, cy = W * 1.5, H * 1.5 - 0.2 * s
    d.add(f'<path d="{circ(cx, cy + 1.2 * s, R)}" fill="#202928" fill-opacity="0.35" filter="{d.blur(1.0 * s)}"/>')
    d.add(f'<path d="{circ(cx, cy, R)}" fill="{d.lin([(0, "#9D4D09"), (0.5, "#A4520A"), (1, "#924500")], 0, cy - R, 0, cy + R)}"/>')
    rb = R - 1.6 * s
    disc = circ(cx, cy, rb)
    d.add(f'<path d="{disc}" fill="{d.lin([(0, "#FFBA30"), (0.45, "#FFAE24"), (0.8, "#FDA313"), (1, "#E8860A")], 0, cy - rb, 0, cy + rb)}"/>')
    d.add(f'<g clip-path="{d.clip(disc)}">'
          f'<path d="{circ(cx, cy - 3.6 * s, rb + 2.6 * s)}" fill="none" stroke="#A4520A" stroke-width="{F(7.4 * s)}" filter="{d.blur(1.2 * s)}"/>'
          f'<path d="{arc_path(cx, cy, rb - 1.3 * s, 175, 365)}" fill="none" stroke="#FBD877" stroke-width="{F(2.6 * s)}" stroke-linecap="round" filter="{d.blur(0.6 * s)}"/>'
          f'<path d="{arc_path(cx, cy, rb - 1.2 * s, 205, 335)}" fill="none" stroke="#FFE29C" stroke-width="{F(2.2 * s)}" stroke-linecap="round" filter="{d.blur(0.4 * s)}"/>'
          f'</g>')
    L, T = 0.545 * R, 0.175 * R
    rr_ = 0.32 * T
    arms = [("f", rr(cx - L, cy - T, cx + L, cy + T, rr_)), ("f", rr(cx - T, cy - L, cx + T, cy + L, rr_))]
    d.add(*toon(arms, d.lin([(0, "#FFFEF9"), (0.5, "#FFFBF2"), (1, "#FFF5DD")], 0, cy - L, 0, cy + L), "#6F3800", 1.5 * s,
                drop=4.0 * s, drop_col="#6F3800"))
    return d.svg()


def icon_plus_green_r2(W=16, H=16):
    """Round 2's badge (comparison only; not in CASES)."""
    d = Doc(W, H)
    s = W * 3 / 48.0
    cx, cy, R = W * 1.5, H * 1.5 - 0.6 * s, 21.2 * s
    d.add(f'<path d="{circ(cx, cy + 1.2 * s, R)}" fill="#0A3A0A" fill-opacity="0.35" filter="{d.blur(0.8 * s)}"/>')
    d.add(f'<path d="{circ(cx, cy, R)}" fill="#0B6A12" />')
    rb = R - 1.8 * s
    d.add(f'<path d="{circ(cx, cy, rb)}" fill="{d.rad([(0, "#5EE25A"), (0.45, "#2EC22E"), (0.8, "#14A216"), (1, "#0C8A10")], cx - 3 * s, cy - 6 * s, rb * 1.25)}"/>')
    L, T = 12.2 * s, 3.9 * s
    plus = [("s", f"M{F(cx - L)} {F(cy)}L{F(cx + L)} {F(cy)}", 2 * T), ("s", f"M{F(cx)} {F(cy - L)}L{F(cx)} {F(cy + L)}", 2 * T)]
    d.add(*toon(plus, "#FBF3E6", "#0A5E10", 1.3 * s, drop=1.1 * s, drop_col="#0A5E10"))
    return d.svg()


# ====================================================================================== HUD: stopwatch
# Shot 003 hud.stopwatch (29 x 33 pt incl. the crown), profiles through its centre: crown #DC8301 outline -> #FECF0C ->
# #FCB90B -> #F09105; ring (outer diameter 29 pt, 3 pt thick) #FEF506 top -> #FFD80D -> #FECC06 sides -> #FDA806 ->
# #FFC309 bottom, dark-orange inner edge #E66000 / #EE8800 and outline #CE6C04 / #D06C00; face (diameter 23 pt) cream
# #F1E8D9 with #E6DED2 under the ring; four ticks + the hand in navy #404679 with a dark outline #1E244C / #292B54.
def icon_stopwatch(W=33, H=33, small=False, hand_deg=40.0):
    """small=True (iconStopwatchSmall, polish r3): re-measured on 204's Claw timer chip, the watch is 22.7 x 26 pt of ink
    (grader A's 18 pt box was too narrow), so the frame is 26 x 27 (was 18: the app drew it ~0.7x of the original); longer
    bolder tick pills that start at the face edge (0.29 R long), a thin white + salmon ring inside the face edge, and a FAT
    rounded wedge hand (204: ~40 deg; the original's hand turns, 026 shows it pointing down)."""
    d = Doc(W, H)
    s = W * 3 / 99.0
    cx, cy = W * 1.5, 54.3 * s
    Ro, Rf = 41.6 * s, 29.6 * s            # hud.stopwatch 29 x 33 pt: ring 29 pt across incl. outline            # ring outer 29 pt incl. outline, face 20 pt (+ its dark edge)
    ow = (2.2 if small else 1.8) * s
    OL = "#B85602"
    # crown: a wide gold cap on a short neck
    stem = rr(cx - 5.2 * s, 7.5 * s, cx + 5.2 * s, 16 * s, 1.5 * s)
    knob = rr(cx - 10.5 * s, 3.0 * s, cx + 10.5 * s, 10.8 * s, 3.4 * s)
    if small:   # 204: a rounder, taller dome cap sitting right on the ring (no neck showing)
        stem = rr(cx - 6.5 * s, 9.0 * s, cx + 6.5 * s, 16 * s, 1.5 * s)
        knob = rr(cx - 13.2 * s, 2.6 * s, cx + 13.2 * s, 14.5 * s, 6.0 * s)
    d.add(f'<path d="{circ(cx, cy + 2.8 * s, Ro)}" fill="#3D2816" fill-opacity="0.34" filter="{d.blur(1.5 * s)}"/>')
    for p in (stem, knob):
        d.add(f'<path d="{p}" fill="{OL}" stroke="{OL}" stroke-width="{F(2 * ow)}" stroke-linejoin="round"/>')
    d.add(f'<path d="{stem}" fill="{d.lin([(0, "#F09005"), (1, "#E07E03")], 0, 8 * s, 0, 19 * s)}"/>')
    ky0, ky1 = (2.6 * s, 14.5 * s) if small else (3.0 * s, 10.8 * s)
    d.add(f'<path d="{knob}" fill="{d.lin([(0, "#FFE340"), (0.4, "#FECF0C"), (0.75, "#FCB90B"), (1, "#F09105")], 0, ky0, 0, ky1)}"/>')
    d.add(f'<path d="M{F(cx - 6.5 * s)} {F(5.2 * s)}L{F(cx + 4.5 * s)} {F(5.2 * s)}" stroke="#FFF5DD" stroke-opacity="0.9" '
          f'stroke-width="{F(1.7 * s)}" stroke-linecap="round"/>')
    # ring: #FEF506 top -> #FFD80D -> #FECC06 -> #FDA806 lower -> #FFC309 at the very bottom (reflected light)
    d.add(f'<path d="{circ(cx, cy, Ro)}" fill="{OL}" stroke="{OL}" stroke-width="{F(2 * ow)}"/>')
    ring = ([(0, "#FFE81E"), (0.16, "#FFCA0A"), (0.45, "#FDB206"), (0.74, "#F89606"), (0.9, "#FAAC06"), (1, "#EE8A04")] if small else
            [(0, "#FFEC2A"), (0.16, "#FFD60C"), (0.48, "#FDBE07"), (0.78, "#FA9E04"), (0.93, "#FDB208"), (1, "#F79A05")])
    d.add(f'<path d="{circ(cx, cy, Ro)}" fill="{d.lin(ring, 0, cy - Ro, 0, cy + Ro)}"/>')
    d.add(f'<path d="{arc_path(cx, cy, Rf + 5.0 * s, 208, 332)}" fill="none" stroke="#FFF46A" stroke-opacity="0.95" '
          f'stroke-width="{F(3.2 * s)}" stroke-linecap="round" filter="{d.blur(0.6 * s)}"/>')
    d.add(f'<path d="{arc_path(cx, cy, Ro - 2.4 * s, 196, 250)}" fill="none" stroke="#FFFBF0" stroke-opacity="0.9" '
          f'stroke-width="{F(2.0 * s)}" stroke-linecap="round" filter="{d.blur(0.45 * s)}"/>')
    d.add(f'<path d="{arc_path(cx, cy, Ro - 3.0 * s, 40, 140)}" fill="none" stroke="#FFD24A" stroke-opacity="0.85" '
          f'stroke-width="{F(2.2 * s)}" stroke-linecap="round" filter="{d.blur(0.5 * s)}"/>')
    # inner dark-orange edge (#E66000 top / #EE8800 bottom) + cream face #F1E8D9 (shaded #E6DED2 under the ring)
    d.add(f'<path d="{circ(cx, cy, Rf + 2.6 * s)}" fill="{d.lin([(0, "#D25800"), (1, "#EA8200")], 0, cy - Rf, 0, cy + Rf)}"/>')
    d.add(f'<path d="{circ(cx, cy, Rf)}" fill="{d.lin([(0, "#E2D8C8"), (0.2, "#F0E7D8"), (1, "#F4ECDE")], 0, cy - Rf, 0, cy + Rf)}"/>')
    d.add(f'<g clip-path="{d.clip(circ(cx, cy, Rf))}"><path d="{circ(cx, cy + 3.4 * s, Rf + 2 * s)}" fill="none" stroke="#B9A386" '
          f'stroke-opacity="0.6" stroke-width="{F(3.6 * s)}" filter="{d.blur(1.1 * s)}"/></g>')
    if small:   # 204: a salmon band at the face edge and a thin white ring just inside it
        d.add(f'<path d="{circ(cx, cy, Rf - 0.9 * s)}" fill="none" stroke="#E0C3A2" stroke-width="{F(2.0 * s)}"/>'
              f'<path d="{circ(cx, cy, Rf - 2.9 * s)}" fill="none" stroke="#FFFFFF" stroke-opacity="0.85" stroke-width="{F(1.6 * s)}"/>')
    # ticks (12, 3, 6, 9) and a bold spade hand pointing up: navy #404679, outline #1E244C
    tl, tw = (12.8 * s, 6.6 * s) if small else (9.0 * s, 7.2 * s)
    navy, navy_o = "#374E4D", "#172A2C"
    tow = (1.4 if small else 1.1) * s
    ticks = []
    for ang in (0, 90, 180, 270):
        a = math.radians(ang - 90)
        if small:
            r1 = Rf + 0.6 * s - tw / 2
            r0 = r1 - tl + tw
        else:
            r0, r1 = Rf - 2.4 * s - tl + tw / 2, Rf - 2.4 * s - tw / 2 + 1.5 * s
        ux, uy = math.cos(a), math.sin(a)
        ticks.append(("s", f"M{F(cx + ux * r0)} {F(cy + uy * r0)}L{F(cx + ux * r1)} {F(cy + uy * r1)}", tw - 2 * tow))
    if small:
        # 204: a fat wedge from the centre (base ~0.26 R across, rounded) to a round tip at ~0.62 R
        hw0, hw1, L = 5.4 * s, 2.2 * s, 0.64 * Rf + 5.0 * s
        wedge = [(cx - hw0, cy + 1.0 * s), (cx - hw1, cy - L), (cx + hw1, cy - L), (cx + hw0, cy + 1.0 * s)]
        wedge = xf(wedge, deg=hand_deg, ox=cx, oy=cy)
        parts = ticks + [("f", rounded(wedge, 2.2 * s)), ("f", circ(cx, cy + 0.6 * s, 6.4 * s))]
        d.add(*toon(parts, navy, navy_o, tow))
        d.body = [f'<g transform="translate(0 {F(2.4 * s)})">'] + d.body + ['</g>']   # crown off the top edge
        return d.svg()
    hand = [(cx - 6.0 * s, cy + 1.5 * s), (cx - 2.4 * s, cy - 12 * s), (cx, cy - Rf + 6.0 * s), (cx + 2.4 * s, cy - 12 * s),
            (cx + 6.0 * s, cy + 1.5 * s), (cx, cy + 6.2 * s)]
    parts = ticks + [("f", rounded(hand, 2.0 * s))]
    d.add(*toon(parts, navy, navy_o, tow))
    d.add(f'<path d="M{F(cx - 1.4 * s)} {F(cy - Rf + 11 * s)}L{F(cx - 2.2 * s)} {F(cy - 1 * s)}" stroke="#488782" stroke-opacity="0.8" '
          f'stroke-width="{F(1.2 * s)}" stroke-linecap="round"/>')
    return d.svg()


# ====================================================================================== HUD hearts
# Lost heart (shot 110, L47 after a bump, the third heart): the same silhouette as heartHUD, FLAT #6C94DC (= the timer
# pill fill: an empty recessed slot), a darker edge band #638CD6 -> #5E8BD4 over ~1 pt inside the outline, a light rim
# #82A8EB just outside its top and #D1E4FC under its bottom (the panel's bevel catching light). No dark outline.
def heart_hud_lost(W=31, H=27):
    d = Doc(W, H)
    hx, hy, hw, hh = 2.5, 1.5, 88, 76
    p = heart2_path(hx, hy, hw, hh)
    d.add(f'<path d="{p}" fill="#D6EAE5" fill-opacity="0.9" transform="translate(0 2.4)" filter="{d.blur(0.9)}"/>')
    d.add(f'<path d="{p}" fill="#5BB0A9" fill-opacity="0.8" transform="translate(0 -1.6)" filter="{d.blur(0.8)}"/>')
    d.add(f'<path d="{p}" fill="#50A197"/>')
    d.add(f'<g clip-path="{d.clip(p)}"><path d="{p}" fill="none" stroke="#409087" stroke-width="5.2" filter="{d.blur(0.9)}"/>'
          f'<path d="{p}" fill="none" stroke="#37857D" stroke-opacity="0.55" stroke-width="5" transform="translate(0 2)" filter="{d.blur(1.4)}"/></g>')
    return d.svg()


# The HUD heart broken in two (FX: the heart-loss animation). Same body as heartHUD (gen_chrome.heart_hud recipe),
# split along a zig-zag crack down the middle; the halves are pulled 2 px apart and tilted 6 deg outward (the break's
# first frame). Left half = the connected component left of the crack (x < 46.5 px at the crack), right = the rest:
# the FX lane can mask either with the crack polyline CRACK (px, frame coordinates) or split by connected alpha.
CRACK = [(46.5, 6), (41, 20), (50, 33), (42, 47), (50, 60), (46.5, 80)]


def heart_hud_halves(W=31, H=27):
    d = Doc(W, H)
    hx, hy, hw, hh = 7.0, 3.5, 79, 69
    p = heart2_path(hx, hy, hw, hh)
    body_fill = d.rad([(0, "#FD6A48"), (0.25, "#FB3E2C"), (0.55, "#F02416"), (0.8, "#DC0C05"), (1, "#B80400")],
                      hx + 0.42 * hw, hy + 0.40 * hh, 0.62 * max(hw, hh), hx + 0.36 * hw, hy + 0.33 * hh)
    top = d.lin([(0, "#8A0006", 0.8), (0.14, "#A00003", 0), (0.78, "#A00003", 0), (1, "#8A0006", 0.45)], 0, hy, 0, hy + hh)
    spec = d.rad([(0, "#FFB189", 0.95), (0.45, "#FD9160", 0.55), (1, "#FC6A48", 0)], hx + 27, hy + 25, 10, sx=1, sy=0.7, rot=-38)
    left = CRACK + [(-10, 90), (-10, -10)]
    right = CRACK + [(110, 90), (110, -10)]
    ol, sh = d.blur(0.7), d.blur(1.6)
    for side, poly, dx, rot in (("L", left, -1.2, -3), ("R", right, 1.2, 3)):
        cp = d.clip(poly_path(poly))
        piv = (46.5, 80)
        tr = f'translate({F(dx)} 0) rotate({rot} {piv[0]} {piv[1]})'
        d.add(f'<g transform="{tr}"><g clip-path="{cp}">'
              f'<path d="{p}" fill="#1D3D40" fill-opacity="0.5" filter="{sh}" transform="translate(0 1)"/>'
              f'<path d="{p}" fill="{body_fill}"/><path d="{p}" fill="{top}"/>'
              + (f'<ellipse cx="{hx + 27}" cy="{hy + 25}" rx="10" ry="7" transform="rotate(-38 {hx + 27} {hy + 25})" fill="{spec}"/>' if side == "L" else
                 f'<path d="M{hx + 63} {hy + 8} Q{hx + 79} {hy + 9} {hx + 82} {hy + 26}" fill="none" stroke="#FF9A7C" stroke-opacity="0.7" stroke-width="2.4" stroke-linecap="round"/>')
              + f'<path d="{p}" fill="none" stroke="#7A0610" stroke-width="5" filter="{ol}" clip-path="{d.clip(p)}"/>'
              f'<path d="{p}" fill="none" stroke="#6E0E16" stroke-width="1.6"/>'
              f'<path d="{poly_path(CRACK, close=False)}" fill="none" stroke="#6E0E16" stroke-width="2.2" stroke-linejoin="round"/>'
              f'</g></g>')
    return d.svg()


# Home lives heart (shot 026 home.livesHeart 39 x 33 pt incl. halo; the count is LIVE text centred at (17, 15.5) pt of
# this frame): heartHUD's body scaled up, a heavier dark outline #6C1825 (top) / #79121B (bottom), face #E80301 ->
# #C80501 -> #A80300 lower, a white-pink specular on the upper-left lobe.
def heart_lives(W=42, H=40):
    """Polish lane r3 (grader A: slightly rounder and brighter than 026, less dark shading low). Re-measured on 002: the
    silhouette is HEART2's shape (IoU 0.976 fitted to its bbox) at 39.7 x 33.7 pt incl. the outline -- round 2's was
    ~6 % wider and 11 % TALLER once the shell scaled the 34 x 32 frame into its 42.3 x 39.8 pt rect. The frame is now
    42 x 40 (drawn 1:1 in that rect; the heart at x 1.5-41.2, y 1.8-35.4 pt of it). Colours (002): outline #741929 /
    #781724 ~0.7 pt, a dark inner band #AF0005 -> #C40101 -> #D90C05 at the top edge, face #E83525 / #F63728, low lobes
    #C50401 -> #B10301, a small soft peach specular #FE9A63 on the left lobe, a light streak #E24947 up the right lobe."""
    d = Doc(W, H)
    s_ = W / 42.0
    hx, hy, hw, hh = 6.7 * s_, 7.5 * s_, 113.7 * s_, 95.8 * s_
    p = heart2_path(hx, hy, hw, hh)
    d.add(f'<path d="{p}" fill="#1D3D40" fill-opacity="0.42" filter="{d.blur(1.6 * s_)}" transform="translate(0 {F(2.4 * s_)})"/>')
    d.add(f'<path d="{p}" fill="#7A0A14" stroke="#6C0A14" stroke-width="{F(4.0 * s_)}" stroke-linejoin="round"/>')
    d.add(f'<path d="{p}" fill="{d.rad([(0, "#F83C2A"), (0.28, "#F0301F"), (0.55, "#E2160C"), (0.8, "#CC0603"), (1, "#B00300")], hx + 0.60 * hw, hy + 0.46 * hh, 0.72 * hw, hx + 0.62 * hw, hy + 0.48 * hh)}"/>')
    d.add(f'<g clip-path="{d.clip(p)}"><path d="{p}" fill="none" stroke="#A00006" stroke-width="{F(7.5 * s_)}" filter="{d.blur(1.5 * s_)}"/>'
          f'<path d="{p}" fill="none" stroke="#C20000" stroke-opacity="0.8" stroke-width="{F(14 * s_)}" transform="translate(0 {F(-5.5 * s_)})" filter="{d.blur(2.6 * s_)}"/>'
          f'<ellipse cx="{F(hx + 29 * s_)}" cy="{F(hy + 30 * s_)}" rx="{F(11 * s_)}" ry="{F(7 * s_)}" transform="rotate(-38 {F(hx + 29 * s_)} {F(hy + 30 * s_)})" '
          f'fill="{d.rad([(0, "#FFB488", 1), (0.5, "#FC8A5C", 0.75), (1, "#F85A3C", 0)], hx + 29 * s_, hy + 30 * s_, 12 * s_)}" filter="{d.blur(1.0 * s_)}"/>'
          f'<path d="M{F(hx + 80 * s_)} {F(hy + 7 * s_)} Q{F(hx + 102 * s_)} {F(hy + 10 * s_)} {F(hx + 108 * s_)} {F(hy + 32 * s_)}" fill="none" stroke="#FF9A84" '
          f'stroke-opacity="0.8" stroke-width="{F(2.8 * s_)}" stroke-linecap="round" filter="{d.blur(0.7 * s_)}"/></g>')
    return d.svg()


# ====================================================================================== popup glyphs (Paused / Settings)
# Shot 007 (Paused panel, cream #F8E7D2 field): the Sound and Haptic glyphs are the house "toon" style = cream face
# (#FFFAF3 top -> #F7E4D8 -> #EBCFC3 at the bottom edges), a dark-brown outline #5A1C00 (the panel label colour family,
# "Sound" #632201) ~0.8 pt, and the same outline dropped ~1.2 pt (solid). Glyph boxes: speaker 30 x 30, haptic 33 x 32.
GLYPH_FILL = [(0, "#FFFCF6"), (0.55, "#FAEDE2"), (1, "#EED3C6")]
GLYPH_OL = "#522300"
# director round 2: the phone's Settings page (meta-029) puts the same glyphs WHITE on GREEN square buttons: a cream-white
# face (#FFFBF4 -> #F4EADF -> #E4D6CA at the bottom) with a thin dark-green outline + drop (#0A5A0B). Grader A: glyphMusic
# read muddy as a cream/brown glyph there. PAL picks the set; the Paused panel (007) keeps the cream/brown one.
GLYPH_PAL = {"cream": (GLYPH_FILL, GLYPH_OL, "#DBC5AE", "#FFF8EE", "#ECDECC"),
             "white": ([(0, "#FFFCF7"), (0.55, "#F4EEE5"), (1, "#E0D6C9")], "#7C3B00", "#D7CDC1", "#FFFFFF", "#E0D9D0")}


def _glyph_fill(d, y0, y1, pal="cream"):
    return d.lin(GLYPH_PAL[pal][0], 0, y0, 0, y1)


def glyph_sound(W=30, H=30, pal="cream", k=1.18):
    d = Doc(W, H)
    s = W * 3 / 90.0
    fillst, OL, joint = GLYPH_PAL[pal][0], GLYPH_PAL[pal][1], GLYPH_PAL[pal][2]
    ow, dr = 2.5 * s, 3.4 * s
    oy = -1.5 * s
    box = rounded([(9 * s, 31 * s + oy), (27 * s, 31 * s + oy), (27 * s, 57 * s + oy), (9 * s, 57 * s + oy)], 4 * s)
    cone = rounded([(22 * s, 31 * s + oy), (44 * s, 13 * s + oy), (47 * s, 16 * s + oy), (47 * s, 72 * s + oy), (44 * s, 75 * s + oy),
                    (22 * s, 57 * s + oy)], 3.6 * s)
    cx, cy = 45 * s, 44 * s + oy
    waves = [("s", arc_path(cx, cy, 15.5 * s, -48, 48), 6.4 * s), ("s", arc_path(cx, cy, 28 * s, -52, 52), 7.0 * s)]
    parts = [("f", box), ("f", cone)] + waves
    # measured ink (007, incl. outline + drop) 30.7 x 28.0 pt: the 30 pt frame holds it at 28.5 pt wide (x 1.18)
    scaled(d, k, 42.75 * s, 44.2 * s, W * 1.5, H * 1.5)
    d.add(*toon(parts, _glyph_fill(d, 13 * s, 76 * s, pal), OL, ow, drop=dr))
    # the cone's inner joint line (the speaker's front rim), as in the capture
    d.add(f'<path d="M{F(27 * s)} {F(33 * s + oy)}L{F(27 * s)} {F(55 * s + oy)}" stroke="{joint}" stroke-width="{F(1.6 * s)}" stroke-linecap="round"/>')
    d.add("</g>")
    return d.svg()


def glyph_haptic(W=30, H=32, pal="cream"):
    d = Doc(W, H)
    s = min(W * 3 / 90.0, H * 3 / 96.0)
    _, OL, _, scr_face, scr_line = GLYPH_PAL[pal]
    GLYPH_OL = OL  # noqa: N806  (the phone's outline colour for this palette)
    ow, dr = 2.5 * s, 3.4 * s
    cx = W * 1.5
    y0 = H * 1.5 - 38 * s          # the ink (outline + drop) centred in the frame
    y1 = y0 + 72 * s
    phone = rr(cx - 19 * s, y0, cx + 19 * s, y1, 8 * s)         # 15 x 25 pt of the 32 pt ink (007)
    parts = [("f", phone)]
    for sgn in (-1, 1):
        xs = cx + sgn * 31.5 * s
        amp = 5.0 * s
        pts = []
        n = 4                                                   # three outward points per side
        for k in range(n + 1):
            y = y0 + 10 * s + (y1 - 12 * s - y0 - 10 * s) * k / n
            pts.append((xs + (amp if k % 2 == 0 else -amp) * sgn, y))
        parts.append(("s", poly_path(pts, close=False), 6.2 * s))
    # measured ink (007) 32.4 x 31.1 pt is wider than the 30 pt frame: drawn at 29 pt wide (x 1.0 base = 87 px)
    d.add(*toon(parts, _glyph_fill(d, y0, y1, pal), GLYPH_OL, ow, drop=dr))
    # the screen: a dark-outlined cream window whose top fifth is dark (the notch band)
    scr = rr(cx - 10.5 * s, y0 + 9 * s, cx + 10.5 * s, y1 - 10 * s, 2.4 * s)
    d.add(f'<path d="{scr}" fill="{scr_face}" stroke="{GLYPH_OL}" stroke-width="{F(2.6 * s)}"/>')
    d.add(f'<path d="{rr(cx - 10.5 * s, y0 + 9 * s, cx + 10.5 * s, y0 + 20 * s, 2.4 * s)}" fill="{GLYPH_OL}"/>')
    d.add(f'<path d="M{F(cx - 6.5 * s)} {F(y0 + 17.2 * s)}L{F(cx + 6.5 * s)} {F(y0 + 17.2 * s)}" stroke="{scr_line}" stroke-width="{F(2.2 * s)}" '
          f'stroke-linecap="round"/>')
    return d.svg()


# Music: not on the phone's Paused panel; seen in the owner's V2 Settings (t 48 s) as a beamed note pair. Drawn in the
# same toon style as the Sound/Haptic pair so the Settings rows match the Paused panel.
def glyph_music(W=30, H=30, pal="white"):
    d = Doc(W, H)
    s = min(W, H) * 3 / 90.0
    OL, joint = GLYPH_PAL[pal][1], GLYPH_PAL[pal][2]
    ow, dr = 2.5 * s, 3.4 * s
    # two stems + a slanted double beam + two tilted oval heads
    xl, xr = 34 * s, 70 * s
    yb_l, yb_r = 16 * s, 9 * s
    beam = rounded([(xl - 2.8 * s, yb_l + 2 * s), (xr + 2.8 * s, yb_r - 1 * s), (xr + 2.8 * s, yb_r + 14 * s), (xl - 2.8 * s, yb_l + 17 * s)], 3 * s)
    stems = [("s", f"M{F(xl)} {F(yb_l + 8 * s)}L{F(xl)} {F(64 * s)}", 6.2 * s), ("s", f"M{F(xr)} {F(yb_r + 8 * s)}L{F(xr)} {F(57 * s)}", 6.2 * s)]
    heads = [("f", ell(xl - 9 * s, 66 * s, 13 * s, 10 * s, -22)), ("f", ell(xr - 9 * s, 59 * s, 13 * s, 10 * s, -22))]
    parts = [("f", beam)] + stems + heads
    ox = W * 1.5 - 45 * s
    d.add(f'<g transform="translate({F(ox)} {F(H * 1.5 - 45 * s)})">')
    d.add(*toon(parts, _glyph_fill(d, 9 * s, 78 * s, pal), OL, ow, drop=dr))
    d.add(f'<path d="M{F(xl + 2 * s)} {F(yb_l + 10.5 * s)}L{F(xr - 2 * s)} {F(yb_r + 7.5 * s)}" stroke="{joint}" stroke-opacity="0.9" '
          f'stroke-width="{F(1.8 * s)}" stroke-linecap="round"/>')
    d.add("</g>")
    return d.svg()


# Gear on the blue square button (shot 026 home.gearButton, 40 pt button; the glyph ~23 pt): six rounded teeth, a round
# hole showing the button face; face #E9FFFD (= the HUD button glyph colour), lower shade #ACD7EA -> #7DB8DB, a navy
# outline #072884 ~1 pt (the pause glyph's outline family #0B2B86).
def glyph_gear(W=26, H=26):
    d = Doc(W, H)
    s = W * 3 / 78.0
    cx, cy = W * 1.5, H * 1.5 - 2.2 * s
    Rt, Rb, hole = 31.0 * s, 23.5 * s, 10.0 * s     # light face 20.7 pt across (026), centred on the button
    n, tw = 6, 0.40                     # teeth, tooth half-width at the root (rad)
    pts = []
    for k in range(n):
        a0 = 2 * math.pi * k / n - math.pi / 2
        for da, r in ((-math.pi / n, Rb), (-tw, Rb), (-tw * 0.74, Rt), (tw * 0.74, Rt), (tw, Rb)):
            a = a0 + da
            pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    body = poly_path(_round_poly(pts, 4.2 * s, 6))
    ring = body + " " + circ(cx, cy, hole)
    face = d.lin([(0, "#F6FFFE"), (0.7, "#F2FDF8"), (1, "#E3F0EB")], 0, cy - Rt, 0, cy + Rt)
    side = d.lin([(0, "#BBD7CD"), (0.5, "#83BBB1"), (1, "#679D91")], 0, cy - Rt, 0, cy + Rt + 4 * s)
    d.add(f'<path d="{circ(cx, cy + 4 * s, Rt)}" fill="#032A2D" fill-opacity="0.35" filter="{d.blur(1.2 * s)}"/>')
    d.add(*toon3d([("f", ring)], face, side, "#00393D", 2.6 * s, 4.2 * s, rule="evenodd"))
    return d.svg()


# Bell (director round 2, from the PHONE's Settings page meta-029, not V2): a white-to-ice-blue bell with a thin NAVY
# outline, a small knob on top, a flared lip band and a clapper ball under it; ~28 x 35 pt incl. the clapper next to the
# "Notifications" label (grader A: round 1 was a 17 pt cream bell without an outline, from the older V2 build).
def glyph_bell(W=30, H=36):
    d = Doc(W, H)
    s = min(W * 3 / 84.0, H * 3 / 112.0)
    cx = W * 1.5
    top = H * 1.5 - 40 * s
    lip = top + 66 * s
    OL = "#033E42"
    body = (f"M{F(cx)} {F(top)}C{F(cx + 17 * s)} {F(top)} {F(cx + 22 * s)} {F(top + 12 * s)} {F(cx + 22 * s)} {F(top + 28 * s)}"
            f"L{F(cx + 23 * s)} {F(lip - 12 * s)}C{F(cx + 23.5 * s)} {F(lip - 5 * s)} {F(cx + 31 * s)} {F(lip - 4 * s)} {F(cx + 31 * s)} {F(lip + 1 * s)}"
            f"C{F(cx + 31 * s)} {F(lip + 5 * s)} {F(cx + 27 * s)} {F(lip + 7 * s)} {F(cx + 22 * s)} {F(lip + 7 * s)}"
            f"L{F(cx - 22 * s)} {F(lip + 7 * s)}C{F(cx - 27 * s)} {F(lip + 7 * s)} {F(cx - 31 * s)} {F(lip + 5 * s)} {F(cx - 31 * s)} {F(lip + 1 * s)}"
            f"C{F(cx - 31 * s)} {F(lip - 4 * s)} {F(cx - 23.5 * s)} {F(lip - 5 * s)} {F(cx - 23 * s)} {F(lip - 12 * s)}"
            f"L{F(cx - 22 * s)} {F(top + 28 * s)}C{F(cx - 22 * s)} {F(top + 12 * s)} {F(cx - 17 * s)} {F(top)} {F(cx)} {F(top)}Z")
    knob = circ(cx, top - 1 * s, 6.2 * s)
    clap = circ(cx, lip + 11 * s, 8.5 * s)
    face = d.lin([(0, "#FFFFFF"), (0.55, "#EFF7F5"), (0.85, "#D1E5DF"), (1, "#A6D2CA")], 0, top, 0, lip + 7 * s)
    d.add(f'<g transform="translate(0 {F(2.6 * s)})">' + "".join(
        f'<path d="{p}" fill="{OL}" stroke="{OL}" stroke-width="{F(5.6 * s)}" stroke-linejoin="round"/>' for p in (clap, knob, body)) + "</g>")
    for p in (clap, knob, body):
        d.add(f'<path d="{p}" fill="{OL}" stroke="{OL}" stroke-width="{F(5.6 * s)}" stroke-linejoin="round"/>')
    d.add(f'<path d="{clap}" fill="{d.lin([(0, "#DFECE9"), (1, "#8FC9C3")], 0, lip + 3 * s, 0, lip + 20 * s)}"/>')
    d.add(f'<path d="{knob}" fill="#F4FAFF"/>')
    d.add(f'<path d="{body}" fill="{face}"/>')
    # the lip band: a slightly bluer rim with a light top line
    lipband = rr(cx - 30 * s, lip - 3 * s, cx + 30 * s, lip + 6.5 * s, 4.5 * s)
    d.add(f'<g clip-path="{d.clip(body)}"><path d="{lipband}" fill="#CDE2DC"/>'
          f'<path d="M{F(cx - 26 * s)} {F(lip - 2.5 * s)}L{F(cx + 26 * s)} {F(lip - 2.5 * s)}" stroke="#FFFFFF" stroke-width="{F(1.6 * s)}"/>'
          f'<path d="M{F(cx - 14 * s)} {F(top + 12 * s)}C{F(cx - 17 * s)} {F(top + 24 * s)} {F(cx - 17 * s)} {F(top + 38 * s)} {F(cx - 17.5 * s)} {F(lip - 10 * s)}" '
          f'fill="none" stroke="#FFFFFF" stroke-width="{F(4 * s)}" stroke-linecap="round" stroke-opacity="0.9" filter="{d.blur(1.0 * s)}"/></g>')
    return d.svg()


# ====================================================================================== embedding the board sprites
import re  # noqa: E402

import gen_board as GB  # noqa: E402  (the pipeline's board sprites, parametric in the pitch; imported, never edited)


def embed(res, x, y, prefix, rot=0.0, piv=None, k=1.0):
    """Place a generated SVG (svg text or (svg, meta)) with its viewBox origin at (x, y) px, ids prefixed so several
    sprites share one document; optional rotation (deg) about piv (px, in the sprite's own coordinates) and scale k.
    Returns (group, (w_px, h_px), meta)."""
    svg, meta = res if isinstance(res, tuple) else (res, {})
    m = re.search(r"<svg[^>]*>", svg)
    inner = svg[m.end(): svg.rindex("</svg>")]
    vb = [float(v) for v in re.search(r'viewBox="([^"]+)"', m.group(0)).group(1).split()]
    for i in sorted(set(re.findall(r'id="([^"]+)"', inner)), key=len, reverse=True):
        inner = re.sub(r'(id="|url\(#|href="#)' + re.escape(i) + r'(["\)])', r"\g<1>" + prefix + i + r"\g<2>", inner)
    tr = f"translate({F(x)} {F(y)})"
    if k != 1.0:
        tr += f" scale({F(k)})"
    if rot:
        px, py = piv if piv else (vb[2] / 2, vb[3] / 2)
        tr += f" rotate({F(rot)} {F(px)} {F(py)})"
    return f'<g transform="{tr}">{inner}</g>', (vb[2] * k, vb[3] * k), meta


# ====================================================================================== unlock illustrations
# All four are the BOARD sprites of the pipeline lane (gen_board: pipe mouth + counter, door + hex lock, curtain/box
# block, tape) drawn at a larger pitch, plus what the board draws in code (the pipe tube, the arrows). The popup's
# sparkles are NOT baked: they twinkle in a loop in the original (research/motion.md "Feature unlock"), so the FX lane
# places sparkleTwinkle sprites around the icon.

# Pipe (shot 040, "Pipe! Unlocked!"): a U pipe, 3 cells long, 2 cells tall, both mouths on the left, the counter on the
# top run 1.4 cells from its mouth. Measured at a pitch of 35.5 pt (tube 35.5 pt thick; collar 43.3 x 21.6 pt = 1.22 x 0.61
# pitch; counter 69.5 x 47.3 pt = 1.96 x 1.33 pitch): the board's own proportions (STYLE §A.2), so the board sprites are
# reused at P = 35.5. Tube shading (STYLE §A.2 + 040): darker rim, cyan face, a light band along the middle whose
# corners meet at 45 deg, brighter toward the upper right. The counter's number is LIVE text centred on the counter
# (frame point (74.6, 28.0) pt) -- text_live.
PIPE_ICON = dict(P=35.5, ox=21.8, oy=28.0, counter_x=1.40)


def unlock_pipe(W=156, H=124):
    d = Doc(W, H)
    K = PIPE_ICON
    P = K["P"]
    u = 3 * P
    ox, oy = K["ox"] * 3, K["oy"] * 3
    X = lambda c: ox + c * u
    Y = lambda r: oy + r * u
    x_end = X(-0.05)
    path = f"M{F(x_end)} {F(Y(0))}L{F(X(3))} {F(Y(0))}L{F(X(3))} {F(Y(2))}L{F(x_end)} {F(Y(2))}"
    # shadow, rim, face, light band, edge light
    d.add(f'<path d="{path}" fill="none" stroke="#000000" stroke-opacity="0.35" stroke-width="{F(u)}" stroke-linejoin="round" '
          f'transform="translate({F(-0.05 * u)} {F(0.10 * u)})" filter="{d.blur(0.05 * u)}"/>')
    d.add(f'<path d="{path}" fill="none" stroke="#2291D6" stroke-width="{F(u)}" stroke-linejoin="round"/>')
    face = d.lin([(0, "#2EA8E4"), (0.45, "#39BCEF"), (1, "#45CCF7")], X(0), Y(2.5), X(3.5), Y(-0.5))
    d.add(f'<path d="{path}" fill="none" stroke="{face}" stroke-width="{F(0.90 * u)}" stroke-linejoin="round"/>')
    d.add(f'<path d="{path}" fill="none" stroke="#6ED3F8" stroke-opacity="0.55" stroke-width="{F(0.46 * u)}" stroke-linejoin="miter" '
          f'filter="{d.blur(0.035 * u)}"/>')
    d.add(f'<path d="{path}" fill="none" stroke="#A6E4FA" stroke-opacity="0.95" stroke-width="{F(0.22 * u)}" stroke-linejoin="miter" '
          f'filter="{d.blur(0.012 * u)}"/>')
    # the upper-right edges catch the light: a thin bright line inside the top of each horizontal run / right of the vertical
    for x0, y0, x1, y1 in ((X(-0.05), Y(-0.44), X(3.0), Y(-0.44)), (X(3.44), Y(0.0), X(3.44), Y(2.0)), (X(-0.05), Y(1.56), X(2.6), Y(1.56))):
        d.add(f'<path d="M{F(x0)} {F(y0)}L{F(x1)} {F(y1)}" stroke="#5FE0FB" stroke-opacity="0.8" stroke-width="{F(0.05 * u)}" stroke-linecap="round"/>')
    # mouths: the board's mouth sprite (drawn opening DOWN, anchor = the end cell's centre) turned to open LEFT
    for r in (0, 2):
        g, (w, h), meta = embed(GB.pipe_mouth(P), 0, 0, f"m{r}")
        ax, ay = meta["anchor"][0] * 3, meta["anchor"][1] * 3
        d.add(f'<g transform="translate({F(X(0) - ax)} {F(Y(r) - ay)}) rotate(90 {F(ax)} {F(ay)})">{g}</g>')
    # counter: the board's counter sprite (horizontal run, anchor = its centre)
    g, (w, h), meta = embed(GB.pipe_counter(P), 0, 0, "pc")
    ax, ay = meta["anchor"][0] * 3, meta["anchor"][1] * 3
    d.add(f'<g transform="translate({F(X(K["counter_x"]) - ax)} {F(Y(0) - ay)})">{g}</g>')
    return d.svg()


# Linked arrows (owner V1 t 78 s, "Linked Arrows! Unlocked!"): two blue arrows pointing right, bound by the pink tape.
# Measured on the frame: arrow spacing 55 pt, shaft 14 pt thick, head 44 x 43 pt, tape 58 x 81 pt = the board tape at a
# 55 pt pitch (0.99 x 1.44 pitch, STYLE §A.2) -> gen_board.tape(2, "V") reused; the whole icon (143 x 100 pt) drawn at
# 0.8 of that size to sit in the 120 x 110 pt frame (pitch 44 pt).
def unlock_linked(W=150, H=106):
    """Polish lane r3 (grader A: flatter heads and thinner shafts than V1's card). Re-measured on V1 t 78 s at 1:1
    (the card art is 141.7 x 97 pt: round 2 was drawn at 0.8 and the shell's default 120 x 110 rect shrinks it further).
    This frame is placed 1:1 at (121.0, 360.7) on the card (its art spans x 125-266.7, y 364.7-461.7 there). Two glossy
    blue arrows 53.3 pt apart: shafts 15.4 pt thick (dark edge #1B61BF top / #10298F bottom, a light band #2CAAFD ~3 pt
    under the top, face #1278FE, shade #124AFA -> #0D37F3 low), round tail caps at x 125; heads 43.4 x 43.3 pt, corners
    r ~5, the same bands; the board tape (gen_board.tape 2 lanes) at P = 58 so the band is 60 x 83 pt, centred on the
    lanes 60.3 pt right of the tails."""
    d = Doc(W, H)
    ox, oy = 121.0, 360.7                                   # the card point of this frame's origin
    X = lambda x: (x - ox) * 3                              # noqa: E731  card pt -> frame px
    Y = lambda y: (y - oy) * 3                              # noqa: E731
    for yc in (386.4, 439.7):
        cy = Y(yc)
        tail, tip, base = X(125.0), X(268.5), X(221.5)
        sw, hh = 15.4 * 3, 45.5 * 3
        shaft = rr(tail, cy - sw / 2, base + 4 * 3, cy + sw / 2, sw / 2)
        head = rounded([(base, cy - hh / 2), (tip, cy), (base, cy + hh / 2)], 8.0 * 3)
        d.add(f'<g filter="{d.blur(1.6 * 3)}" transform="translate(0 {F(2.4 * 3)})" fill="#000000" fill-opacity="0.5">'
              f'<path d="{shaft}"/><path d="{head}"/></g>')
        for p_, top, bot in ((shaft, cy - sw / 2, cy + sw / 2), (head, cy - hh / 2, cy + hh / 2)):
            d.add(f'<path d="{p_}" fill="{d.lin([(0, "#1B61BF"), (1, "#10298F")], 0, top, 0, bot)}" stroke="{d.lin([(0, "#1B61BF"), (1, "#10298F")], 0, top, 0, bot)}" '
                  f'stroke-width="{F(0.7 * 3)}" stroke-linejoin="round"/>')
            ins = 0.8 * 3
            face = d.lin([(0, "#1468D8"), (0.1, "#1C96F3"), (0.2, "#30AEFF"), (0.3, "#1487F5"), (0.45, "#127AFE"), (0.72, "#1776FF"),
                          (0.84, "#1459FC"), (0.93, "#0D3DF5"), (1, "#122FC0")], 0, top, 0, bot)
            d.add(f'<g clip-path="{d.clip(p_)}"><path d="{p_}" fill="{face}" transform="translate(0 0)"/>'
                  f'<path d="{p_}" fill="none" stroke="#10298F" stroke-opacity="0.5" stroke-width="{F(2 * ins)}"/></g>')
    res = GB.tape(2, "V", 54.0)
    g, (w, h), meta = embed(res, 0, 0, "tp")
    d.add(f'<g transform="translate({F(X(185.3) - w / 2)} {F(Y(413.4) - h / 2)})">{g}</g>')
    return d.svg()


def unlock_linked_r2(W=120, H=110):
    """Round 2's card icon (comparison only; not in CASES)."""
    d = Doc(W, H)
    P = 44.0
    u = 3 * P
    cy0, cy1 = H * 1.5 - 0.5 * u, H * 1.5 + 0.5 * u
    xs, xt = 8.0 * 3, (W - 5.0) * 3                 # shaft start, head tip
    sw = 0.28 * u                                    # shaft thickness (14 / 55, a touch heavier at this size)
    hl, hh = 0.84 * u, 0.86 * u                      # head length / height (44 x 43 / 55)
    blue = d.lin([(0, "#5AA4FF"), (0.3, "#3285FF"), (0.7, "#1C6CFA"), (1, "#135DEB")], 0, -hh / 2, 0, hh / 2)
    for cy in (cy0, cy1):
        head = rounded([(xt - hl, cy - hh / 2), (xt, cy), (xt - hl, cy + hh / 2)], 0.13 * u)
        shaft = rr(xs, cy - sw / 2, xt - hl + 0.1 * u, cy + sw / 2, sw / 2)
        d.add(f'<g filter="{d.blur(0.035 * u)}" transform="translate(0 {F(0.05 * u)})" fill="#000000" fill-opacity="0.45">'
              f'<path d="{head}"/><path d="{shaft}"/></g>')
        d.add(f'<path d="{shaft}" fill="#0D4ED0" stroke="#0D4ED0" stroke-width="{F(0.025 * u)}"/>'
              f'<path d="{head}" fill="#0D4ED0" stroke="#0D4ED0" stroke-width="{F(0.025 * u)}" stroke-linejoin="round"/>')
        d.add(f'<g transform="translate(0 {F(cy)})"><path d="{shaft}" transform="translate(0 {F(-cy)})" fill="{blue}"/>'
              f'<path d="{head}" transform="translate(0 {F(-cy)})" fill="{blue}"/></g>')
        # glossy streak along the shaft top + the head's upper edge
        d.add(f'<path d="M{F(xs + 0.12 * u)} {F(cy - sw * 0.2)}L{F(xt - hl - 0.05 * u)} {F(cy - sw * 0.2)}" stroke="#8EC4FF" '
              f'stroke-opacity="0.85" stroke-width="{F(0.06 * u)}" stroke-linecap="round"/>')
        d.add(f'<path d="M{F(xt - hl + 0.1 * u)} {F(cy - hh / 2 + 0.14 * u)}L{F(xt - 0.18 * u)} {F(cy - 0.06 * u)}" stroke="#7FB8FF" '
              f'stroke-opacity="0.8" stroke-width="{F(0.05 * u)}" stroke-linecap="round"/>')
    res = GB.tape(2, "V", P)
    g, (w, h), meta = embed(res, 0, 0, "tp")
    tx = (xs + (xt - hl)) / 2 - w / 2 - 0.02 * u
    d.add(f'<g transform="translate({F(tx)} {F(H * 1.5 - h / 2)})">{g}</g>')
    return d.svg()


# Box (phone v552 shot 134, "Box! / Unlocked! / Clear required amount of arrows to break the BOX!"; SPEC §5.11: the
# counter obstacle ships as the phone's BOX and its card replaces the videos' "Curtain!" card): a purple rounded slab
# 120 x 119 pt, a silver sphere with four lugs on the diagonals, a purple ring around a navy well holding the counter.
# = the pipeline's curtain/box block (gen_board.curtain_crate, 3 x 3 cells) at P = 34 pt; the digit is LIVE text centred
# on the well (the frame centre). The slab sits at 0.92 of the capture's size (frame 110 pt tall).
def unlock_curtain_legacy(W=120, H=110):
    """Round 1's Box card icon from the V1 curtain crate (NOT SHIPPED since director round 2: unlockIconBox)."""
    d = Doc(W, H)
    keep = dict(GB.CURTAIN)
    GB.CURTAIN.update(sphere=1.19, lug_r0=0.90, lug_r1=1.45, lug_w=0.62, ring=0.66, well=0.52)
    try:
        res = GB.curtain_crate(34.0, 3, 3)
    finally:
        GB.CURTAIN.clear(); GB.CURTAIN.update(keep)
    g, (w, h), meta = embed(res, 0, 0, "bx")
    d.add(f'<g transform="translate({F(W * 1.5 - w / 2)} {F(H * 1.5 - h / 2)})">{g}</g>')
    return d.svg()


def unlock_box(W=132, H=134):
    """Polish lane r3: the Box CARD icon drawn as its own illustration (grader: the ring's lugs whiter, the well larger;
    at game size round 2's board-sprite version also read flatter and its sphere + lugs overfilled the slab). Measured on
    134 (card at 1:1; the shell fits the ink to (136.5, 351, 121.5, 127.5), so the ink here is that box at 1:1 in the
    132 x 134 frame): a PILLOW slab 121.5 x 127 (corner r ~18) -- top bevel highlight #F0BCF2, face #BF5DF7 / #B95AF5,
    rounded sides darkening to #503191 over ~8 pt, a 10 pt darker bottom face #8B45C2 -> #5A3195; the sphere sits in a
    dark crease (#7138A4 / #3C196D) -- sphere ⌀ ~89 pt, pale #DBE8FD / #FDFEFE, lower #7D90C2 -> #465890, edge #3B4990;
    FOUR SHORT STUBBY lugs on the diagonals (caps ~51 pt out above, ~45 pt below: seen a little from above); a thin
    TUBE-like purple ring (outer ⌀ 52: #884AED edge, #D1A5FC core, #833FC9 inner) around a navy well ⌀ 41 (#0D3363 ->
    #275B9D, outline #082650). The counter digit is LIVE text centred on the well = frame (65.55, 65.25) pt."""
    d = Doc(W, H)
    k = 3.0
    x0, x1, y0, y1 = 5.25 * k, 126.75 * k, 3.25 * k, 130.75 * k
    R = 21.0 * k
    cx, cy = 65.55 * k, 65.25 * k
    # the slab: bottom face (darker, 10 pt), then the top face with rounded sides and a bevel highlight
    d.add(f'<path d="{rr(x0 + 1.5 * k, y0 + 10 * k, x1 - 1.5 * k, y1 + 0.4 * k, R)}" fill="#0A0620" fill-opacity="0.45" filter="{d.blur(0.9 * k)}"/>')
    d.add(f'<path d="{rr(x0, y0 + 9 * k, x1, y1, R)}" fill="{d.lin([(0, "#9A50D2"), (0.6, "#7A3CB4"), (0.85, "#5E3399"), (1, "#4E2E87")], 0, y1 - 30 * k, 0, y1)}"/>')
    top = rr(x0, y0, x1, y1 - 9.5 * k, R)
    d.add(f'<path d="{top}" fill="{d.lin([(0, "#C26BF7"), (0.08, "#C263F7"), (0.5, "#BC5CF6"), (1, "#B356EE")], 0, y0, 0, y1 - 9.5 * k)}"/>')
    tc = d.clip(top)
    d.add(f'<g clip-path="{tc}">'
          f'<path d="{top}" fill="none" stroke="#5A3196" stroke-width="{F(12 * k)}" filter="{d.blur(4.0 * k)}"/>'
          f'<path d="{top}" fill="none" stroke="#6C38B4" stroke-opacity="0.8" stroke-width="{F(4 * k)}" filter="{d.blur(1.0 * k)}"/>'
          f'</g>')
    fade = d.lin([(0, "#FFFFFF"), (0.45, "#FFFFFF"), (1, "#000000")], 0, y0, 0, y0 + 16 * k)
    mk = d.mask(f'<rect x="0" y="0" width="{F(d.W)}" height="{F(d.H)}" fill="{fade}"/>')
    d.add(f'<g clip-path="{tc}"><g mask="{mk}"><path d="{top}" fill="none" stroke="#F2C4F4" stroke-width="{F(6 * k)}" '
          f'transform="translate(0 {F(3.6 * k)})" filter="{d.blur(1.1 * k)}"/></g></g>')
    # the crease the sphere sits in
    rs = 44.5 * k
    d.add(f'<path d="{circ(cx, cy + 1.2 * k, rs + 2.2 * k)}" fill="{d.lin([(0, "#7A3CB0"), (0.5, "#5A2A92"), (1, "#3C196D")], 0, cy - rs, 0, cy + rs)}" '
          f'filter="{d.blur(0.9 * k)}"/>')
    # the sphere
    sph = d.rad([(0, "#FBFDFF"), (0.35, "#DDE8FC"), (0.55, "#B9C8EE"), (0.75, "#7F90C6"), (1, "#44528E")], cx - 0.10 * rs, cy - 0.32 * rs, 1.3 * rs)
    d.add(f'<path d="{circ(cx, cy, rs)}" fill="{sph}" stroke="#3B4990" stroke-width="{F(0.7 * k)}"/>')
    d.add(f'<g clip-path="{d.clip(circ(cx, cy, rs))}">'
          f'<path d="{circ(cx, cy + 4 * k, rs + 3 * k)}" fill="none" stroke="#3E4C8C" stroke-opacity="0.55" stroke-width="{F(8 * k)}" filter="{d.blur(3 * k)}"/>'
          f'<path d="{arc_path(cx, cy, 29.5 * k, 20, 160)}" fill="none" stroke="#E4EEFD" stroke-width="{F(3.2 * k)}" stroke-linecap="round" filter="{d.blur(0.8 * k)}"/>'
          f'</g>')
    # lugs (IN FRONT of the sphere's rim, 134): stubby cylinders 25 pt wide; seen a little from above, so the upper pair points more UP
    # (-128 / -52 deg, caps ~54 pt out) and the lower pair more SIDEWAYS (145 / 35 deg, caps ~42 pt out)
    lw = 25.0 * k
    for ang, dist in ((-128, 51.0), (-52, 51.0), (136, 45.0), (44, 45.0)):
        t = math.radians(ang)
        ux, uy = math.cos(t), math.sin(t)
        ex, ey = cx + ux * dist * k, cy + uy * dist * k
        bx, by = cx + ux * (dist - 13) * k, cy + uy * (dist - 13) * k
        L = math.hypot(ex - bx, ey - by)
        body = rr(-lw / 2, -4 * k, lw / 2, L, 1.5 * k)
        rot = math.degrees(math.atan2(ey - by, ex - bx)) - 90
        g = d.lin([(0, "#F2F6FF"), (0.3, "#D2DDF6"), (0.7, "#9AA9DC"), (1, "#6573B0")], -lw / 2, 0, lw / 2, 0)
        d.add(f'<path d="{ell(ex + 1.5 * k, ey + 4 * k, lw * 0.55, 9 * k, math.degrees(t) + 90)}" fill="#2A1460" fill-opacity="0.35" filter="{d.blur(2 * k)}"/>')
        d.add(f'<g transform="translate({F(bx)} {F(by)}) rotate({F(rot)})"><path d="{body}" fill="{g}" stroke="#8C9ACF" stroke-opacity="0.7" stroke-width="{F(0.5 * k)}"/></g>')
        cap = ell(ex, ey, lw / 2, 7.0 * k, math.degrees(t) + 90)
        d.add(f'<path d="{cap}" fill="{d.lin([(0, "#F4F8FF"), (0.6, "#DCE5FA"), (1, "#BCC9EE")], 0, ey - 10 * k, 0, ey + 10 * k)}" stroke="#8F9CD2" stroke-width="{F(0.6 * k)}"/>')
        d.add(f'<path d="{ell(ex - 1.5 * k, ey - 1.5 * k, lw * 0.28, 3.0 * k, math.degrees(t) + 90)}" fill="#FFFFFF" fill-opacity="0.6" filter="{d.blur(0.7 * k)}"/>')
    # ring groove, the tube-like purple ring, the navy well
    d.add(f'<path d="{circ(cx, cy, 27.3 * k)}" fill="#455897"/>')
    d.add(f'<path d="{circ(cx, cy, 23.4 * k)}" fill="none" stroke="{d.lin([(0, "#9A5AF0"), (1, "#7A3CCB")], 0, cy - 26 * k, 0, cy + 26 * k)}" stroke-width="{F(6.4 * k)}"/>')
    d.add(f'<path d="{circ(cx, cy, 23.6 * k)}" fill="none" stroke="#D3A8FC" stroke-width="{F(3.0 * k)}" filter="{d.blur(0.6 * k)}"/>')
    well = circ(cx, cy, 20.5 * k)
    d.add(f'<path d="{well}" fill="{d.rad([(0, "#2A5FA2"), (0.55, "#245595"), (0.85, "#18427A"), (1, "#0D3363")], cx, cy + 2 * k, 21 * k)}" '
          f'stroke="#082650" stroke-width="{F(0.8 * k)}"/>')
    return d.svg()


def unlock_box_r2(W=132, H=134, P=40.0):
    """The Box card icon (134 "Box! Unlocked!"; director round 2: now the PHONE's Box skin -- gen_board.box_slab 3 x 3 +
    box_ring -- the same sprites the board draws, at P = 37 pt so the slab is 134's 111 pt). The counter is live text in
    the well at the frame centre."""
    d = Doc(W, H)
    # 134 at 3 px/pt: the slab is 120 pt wide with corners r ~0.62 pitch and no rivets; the sphere ~88 pt across
    g, (w, h), meta = embed(GB.box_slab(3, 3, P, rivets=False, r=0.62, top=0.10, lip=0.24), 0, 0, "bs")
    d.add(f'<g transform="translate({F(W * 1.5 - w / 2)} {F(H * 1.5 - h / 2 - 1.5)})">{g}</g>')
    ring = GB.box_ring(P)
    g2, (w2, h2), _ = embed(ring, 0, 0, "br", k=1.13)      # 134: the ring nearly fills the 3 x 3 slab (2.2 x 1.13 pitch)
    d.add(f'<g transform="translate({F(W * 1.5 - w2 / 2)} {F(H * 1.5 - h2 / 2 - 6)})">{g2}</g>')
    return d.svg()


# Door (owner V1 t 185 s: the unlock card's icon = the board's locked door, orange frame + rivets, purple inner frame,
# blue slatted shutter, purple hex lock): gen_board.door(4, 4) + gen_board.hex_lock at P = 25.5 pt (door 102 pt), the lock
# at 0.85 of the board ratio (the icon's lock is 0.42 of the door's width), centred 0.18 pitch below the frame centre.
def unlock_door(W=128, H=128, P=24.0):
    """Polish lane r3 (grader A: V1's card door is taller, ours read squat). Re-measured on V1 t 185 s: the card door is
    SQUARE, 5 x 5 cells (154 x 154 pt at P 30.8: 4 light slat seams + the header), and its hex lock is the board lock at
    the door's OWN pitch (~61 x 52 pt = 0.39 of the door's width; round 2 drew it at 0.85 P), centred 0.44 P below the
    door's centre. Drawn here at P = 24 (a 120 x 120 pt door in a 128 x 128 frame) = the phone cards' size class (Box
    121.5 x 127.5, Pipe 123.8 x 112); the shell's ink rect for it: (135.5, 351, 122, 122)."""
    d = Doc(W, H)
    u = 3 * P
    g, (w, h), meta = embed(GB.door(5, 5, P), 0, 0, "dr")
    dx, dy = W * 1.5 - w / 2, H * 1.5 - h / 2
    d.add(f'<g transform="translate({F(dx)} {F(dy)})">{g}</g>')
    lg, (lw, lh), _ = embed(GB.hex_lock(P), 0, 0, "lk")
    lcx, lcy = W * 1.5, H * 1.5 + 0.44 * u
    d.add(f'<g transform="translate({F(lcx - lw / 2)} {F(lcy - lh / 2)})">{lg}</g>')
    return d.svg()


# ====================================================================================== tutorial hand
# Owner V1 0.80-3.64 s ("Tap to move!", research/tutorials.md §3): a yellow-orange emoji-style hand, the index finger up
# (the whole hand turned ~16 deg counter-clockwise), the other fingers curled (two knuckle bumps at the upper right,
# the thumb bulging at the lower left), the wrist at the bottom right; yellow #FFD21E face, orange #F59A12 toward the
# edges, a warm highlight down the finger; a soft grey drop shadow. Measured size 70 x 99 pt incl. the shadow (the
# frame here is 60 x 70 pt: the app draws it at ~1.4x, anchored on the FINGERTIP = HAND_TIP_PT of this frame).
HAND = dict(rot=-16.0, k=3.15, dx=2.5)   # r2: k fixed so the opaque hand is ~72 x 99 pt (V1 t 1.2: 70 x 99)
SHADOW = (-3.0, 21.0)  # pt: V1 t 1.2 casts it straight down and a little left
HAND_TIP_PT = None     # filled by tutorial_hand() (fingertip in frame pt)


def tutorial_hand(W=60, H=70):
    """The hand fills the frame (fingertip at the top left); the measured on-screen size is 70 x 100 pt WITHOUT the
    shadow (V1 t 1.2 s, yellow bbox 191-261 x 424-523 pt), so at the manifest's 60 x 70 pt frame the app scales it ~1.5x;
    tutorial_hand(78, 110) renders it at 1:1 (the lane log asks for that frame)."""
    global HAND_TIP_PT
    d = Doc(W, H)
    rot = HAND["rot"]
    # upright hand in units (height 104): one silhouette = finger + wide palm + two knuckle bumps + thumb + wrist
    # director r2 (V1 t 1.2 at 4.5 px/pt): a slimmer, rounder palm (round 1 read boxy), smaller knuckle bumps
    finger = rr(15, 0, 37, 66, 11)
    palm = rr(15, 36, 72, 90, 23)
    kn1 = circ(46.5, 38.5, 11.5)
    kn2 = circ(62, 44.5, 10.5)
    thumb = ell(16, 67, 10, 15, 14)
    wrist = rr(36, 72, 71, 104, 12)
    shapes = [palm, wrist, thumb, kn2, kn1, finger]
    cx, cy = 46, 52
    t = math.radians(rot)
    pts = [(x, y) for (x, y) in ((4, 0), (37, -1), (79, 30), (79, 90), (73, 105), (35, 105), (4, 82))]
    rp = [(cx + math.cos(t) * (x - cx) - math.sin(t) * (y - cy), cy + math.sin(t) * (x - cx) + math.cos(t) * (y - cy)) for x, y in pts]
    bx0, by0 = min(p[0] for p in rp), min(p[1] for p in rp)
    bx1, by1 = max(p[0] for p in rp), max(p[1] for p in rp)
    # V1's hand casts a BIG soft grey shadow down-right (~ +10, +22 pt, blur ~5 pt); the hand is 70 x 100 pt: the frame
    # keeps the hand at the top-left and the shadow room at the bottom-right
    mx, my = SHADOW[0] * 3 + 18, SHADOW[1] * 3 + 18
    k = HAND.get("k") or min((W * 3 - mx - 3) / (bx1 - bx0), (H * 3 - my - 3) / (by1 - by0))
    tx = 3 - bx0 * k - HAND.get("dx", 0.0) * 3      # the bbox points overestimate the left side: dx pt to the left
    ty = 3 - by0 * k
    tr = f'translate({F(tx)} {F(ty)}) scale({F(k)}) rotate({F(rot)} {F(cx)} {F(cy)})'
    body = "".join(f'<path d="{p}"/>' for p in shapes)
    d.add(f'<g transform="translate({F(SHADOW[0] * 3)} {F(SHADOW[1] * 3)})" filter="{d.blur(4.5 * 3)}"><g transform="{tr}" fill="#6A7488" '
          f'fill-opacity="0.42">{body}</g></g>')
    base = d.rad([(0, "#FFE445"), (0.4, "#FFD222"), (0.75, "#FDBC18"), (1, "#F5A012")], 52, 46, 62, 46, 34)
    uni = d.clip(*shapes)
    inner_edge = d.mask(f'<rect x="-200" y="-200" width="600" height="600" fill="white"/><g fill="black">{body}</g>')
    g = [f'<g transform="{tr}">', f'<g fill="{base}">{body}</g>',
         # the silhouette's own inner edge: warm orange, soft (one edge for the union, no seams between the parts)
         f'<g clip-path="{uni}"><g filter="{d.blur(2.2)}"><rect x="-200" y="-200" width="600" height="600" fill="#EA8A0E" '
         f'mask="{inner_edge}"/></g></g>',
         # creases: finger over the knuckles / palm, knuckle tops, the thumb
         f'<g clip-path="{uni}" fill="none" stroke-linecap="round">'
         f'<path d="M37.5 30 C38.5 42 38 52 35 60" stroke="#E98A10" stroke-opacity="0.55" stroke-width="3" filter="{d.blur(1.4)}"/>'
         f'<path d="M57 32 C58.5 38 58.5 42 57.5 46" stroke="#EE9412" stroke-opacity="0.45" stroke-width="2.2" filter="{d.blur(1.2)}"/>'
         f'<path d="M20 50 C25 56 26 66 22 76" stroke="#E98A10" stroke-opacity="0.45" stroke-width="2.6" filter="{d.blur(1.4)}"/>'
         f'<path d="M40 84 C50 88 62 88 72 83" stroke="#EE9412" stroke-opacity="0.35" stroke-width="2.4" filter="{d.blur(1.6)}"/>'
         # highlights: down the finger, on the knuckles, across the palm
         f'<path d="M23 7 C22 20 22.5 36 24 52" stroke="#FFF29A" stroke-opacity="0.9" stroke-width="5.5" filter="{d.blur(2.2)}"/>'
         f'<path d="M44 27 C47 25.5 51 25.5 54 27.5" stroke="#FFF08A" stroke-opacity="0.7" stroke-width="3" filter="{d.blur(1.2)}"/>'
         f'<path d="M45 52 C52 50 62 51 68 56" stroke="#FFEB70" stroke-opacity="0.55" stroke-width="7" filter="{d.blur(3.0)}"/>'
         f'</g>', "</g>"]
    d.add(*g)
    x0, y0 = 25.5 - cx, 0.5 - cy
    xr, yr = cx + math.cos(t) * x0 - math.sin(t) * y0, cy + math.sin(t) * x0 + math.cos(t) * y0
    HAND_TIP_PT = (round((tx + xr * k) / 3, 1), round((ty + yr * k) / 3, 1))
    return d.svg(), {"anchor": HAND_TIP_PT}


# ====================================================================================== rank badges (hexagon + ring)
# Store shot 6 (Streak Race / leaderboard rows): a hexagon with points left/right and a flat top/bottom, 42 x 36 store pt;
# a rim darker than the row (gold: outline #883F00 / #AB4F00, rim #F28206 -> light top lip #FFF48E), the face in the row
# colour (gold #FFD302 top -> #FFBE02 bottom), a darker ring #F17E01 (2 pt) around a round window of the same face; the
# rank number is LIVE text (cream #FCE6D7, outline #76001B gold / navy #263A70 silver) centred on the window = the frame
# centre. Silver: face #C1CAF0, rim #7083D3 / outline #3E50A1, ring #697DD1. Bronze: face #FAA965, rim #CB5316 / outline
# #9C370D, ring #D46A2A. Plain (ranks 4+, not in the capture): the HUD blue family (#5AA6FF face, #1F6FE0 rim).
RANK = {
    "gold": dict(ol="#8E4000", rim=["#FFF28A", "#F6A410", "#E47A04", "#C45A00"], face=["#FFDE20", "#FFD000", "#FFBE02"],
                 ring="#EC7A02", ring_lo="#FFE070"),
    "silver": dict(ol="#34458F", rim=["#E4EAFF", "#9AA8E6", "#6F82D2", "#4E60B0"], face=["#D6DEFA", "#C4CDF2", "#B2BDEB"],
                   ring="#6A7ED0", ring_lo="#E0E7FF"),
    "bronze": dict(ol="#8A300A", rim=["#FFD2A8", "#F08A45", "#D8662A", "#B04A12"], face=["#FDBB80", "#FAAA66", "#F29A55"],
                   ring="#D5652A", ring_lo="#FFD0A8"),
    "plain": dict(ol="#0E3A96", rim=["#A8D8FF", "#3C8EF6", "#1F6FE0", "#1552C0"], face=["#8CC8FF", "#6AB0FF", "#4F98F4"],
                  ring="#2A74E0", ring_lo="#B8E0FF"),
}


RANK3 = {   # polish lane r3: profiles through 203 (silver row 2, bronze row 3) and store 6 (gold row 1)
    "gold": dict(ol="#7F3800", side="#BB4700", rim="#F17E01", top="#FFF389", face="#FFDB03", low="#FFB800",
                 line="#823400", band="#F27D00", lite="#FEE87A", win=("#FEE461", "#FFC21A")),
    "silver": dict(ol="#1C2E5E", side="#3F509D", rim="#6B7FD4", top="#D4DCF8", face="#C9D2F8", low="#8593D3",
                   line="#243B6C", band="#6E83D5", lite="#D4DCF9", win=("#C6D0F7", "#8E9DD9")),
    "bronze": dict(ol="#840010", side="#B03706", rim="#CC4C0C", top="#FFE8CD", face="#FAA865", low="#F69449",
                   line="#8D0711", band="#CC5011", lite="#FFE5CC", win=("#F9A867", "#F4934A")),
    "plain": dict(ol="#05494D", side="#08645E", rim="#009F92", top="#CFE7E0", face="#81D0C7", low="#2CA79B",
                  line="#05494D", band="#00857D", lite="#C3E1D8", win=("#81D0C7", "#2CA79B")),
}


def rank_badge(kind, W=40, H=40):
    """Polish lane r3 (grader A: bevel thinner, silver face lighter than 203). Re-measured on 203 at 1:1: the badge is
    37.3 x 36.3 pt (round 2's ink was 33 x 32 in its 36 pt frame -> frame 40 now); from outside in: a thin dark outline
    (silver #1C2E5E / bronze #840010 / gold #7F3800), a 1.7 pt 3D bottom side (#3F509D / #B03706 / #BB4700), a 1.2 pt rim
    band (#6B7FD4 / #CC4C0C / #F17E01), a light upper bevel face (#D4DCF8 / #FFE8CD / #FFF389) over the face, darker low
    (#8593D3 / #F69449 / #FFB800); the round window (ring ⌀ 24.2 = 0.65 of the width): a thin dark line, a 1 pt band, a light inner line,
    and a vertical face gradient. The rank number is LIVE text at the window centre = frame (20, 19.3) pt."""
    d = Doc(W, H)
    c = RANK3[kind]
    cx, cy = W * 1.5, H * 1.5 - 1.2
    a, b = 55.0, 49.0
    sd = 5.0                                               # the side's depth (1.7 pt)
    def hexp(dx=0.0, dy=0.0, da=0.0, db=0.0, r=7.0):
        return rounded(hexagon(cx + dx, cy + dy, a - da, b - db, (a - da) * 0.52), r)
    outer, side = hexp(), hexp(dy=sd)
    d.add(f'<path d="{side}" fill="#101840" fill-opacity="0.45" transform="translate(0 3)" filter="{d.blur(1.8)}"/>')
    for p_ in (side, outer):
        d.add(f'<path d="{p_}" fill="{c["ol"]}" stroke="{c["ol"]}" stroke-width="3.6" stroke-linejoin="round"/>')
    d.add(f'<path d="{side}" fill="{c["side"]}"/>')
    d.add(f'<path d="{outer}" fill="{c["rim"]}"/>')
    face = hexp(da=3.6, db=3.6, r=5.5)
    d.add(f'<path d="{face}" fill="{d.lin([(0, c["top"]), (0.22, c["face"]), (0.6, c["face"]), (1, c["low"])], 0, cy - b, 0, cy + b)}"/>')
    d.add(f'<g clip-path="{d.clip(face)}"><path d="{face}" fill="none" stroke="{c["top"]}" stroke-width="4" transform="translate(0 2)" '
          f'filter="{d.blur(0.8)}"/></g>')
    r = 34.7                                               # ring ⌀ 24.2 pt incl. its dark line (0.65 of the width)
    wy = cy - 0.8
    d.add(f'<path d="{circ(cx, wy, r + 1.6)}" fill="{c["line"]}"/>')
    d.add(f'<path d="{circ(cx, wy, r)}" fill="{c["band"]}"/>')
    d.add(f'<path d="{circ(cx, wy, r - 3.0)}" fill="{c["lite"]}"/>')
    d.add(f'<path d="{circ(cx, wy, r - 4.6)}" fill="{d.lin([(0, c["win"][0]), (1, c["win"][1])], 0, wy - r, 0, wy + r)}"/>')
    return d.svg()


def rank_badge_r2(kind, W=36, H=36):
    """Round 2's badge (comparison only; not in CASES)."""
    d = Doc(W, H)
    c = RANK[kind]
    cx, cy = W * 1.5, H * 1.5 - 1.2
    a, b = 50.5, 46.5
    outer = rounded(hexagon(cx, cy, a, b, a * 0.52), 7.0)
    d.add(f'<path d="{outer}" fill="{c["ol"]}"/>')
    return d.svg()


# ====================================================================================== logo "ARROW OUT!"
# OUR logo in the original logo's STYLE (shot 049 L36 win splash; store 8): an arched blue plate with a thick white rim
# and a grey underside carrying a yellow bubble word, hung on two grey pegs over a purple ARROW plate (white rim, grey
# underside, tilted up to the right) carrying a white bubble word. The letters are OUR OFL font (PC Display = Nunito
# wght 1000, design/fonts) placed along the arch, inflated with a round stroke, extruded straight down, glossed; the
# owner's name (02:33) is "Arrow Out" -> "ARROW" on the blue plate, "OUT!" on the arrow. Brand art: not translated.
# Geometry measured on 049 in "design px" (6 px per pt; the 306 x 236 pt frame = the design scaled by 0.47):
# top plate 1830 x 705 (rim 45, corner r 150, ends 120 lower than the middle, underside 60), yellow word cap 420 over
# x 255-1790 (MAZE; ARROW has 5 letters: compressed to 0.84 wide); pegs at x 640-750 / 1225-1335; arrow plate body
# 345-1440 x 900-1440, head to x 1765, turned -3 deg; white word cap 330 over x 520-1480.
GLYPHS = None


def _glyphs():
    global GLYPHS
    if GLYPHS is None:
        GLYPHS = json.load(open(os.path.join(HERE, "pcdisplay_glyphs.json"), encoding="utf-8"))["black"]
    return GLYPHS


def rr_pts(x0, y0, x1, y1, r, n=10, step=20.0):
    """Rounded-rect outline as dense points (straight edges sampled every `step`, so a warp can bend them)."""
    pts = []
    corners = ((x0 + r, y0 + r, 180), (x1 - r, y0 + r, 270), (x1 - r, y1 - r, 0), (x0 + r, y1 - r, 90))
    for i, (cx_, cy_, a0) in enumerate(corners):
        for k in range(n + 1):
            a = math.radians(a0 + 90 * k / n)
            pts.append((cx_ + r * math.cos(a), cy_ + r * math.sin(a)))
        nx_, ny_, _ = corners[(i + 1) % 4]
        a1 = math.radians(a0 + 90)
        p0 = (cx_ + r * math.cos(a1), cy_ + r * math.sin(a1))
        a2 = math.radians(corners[(i + 1) % 4][2])
        p1 = (nx_ + r * math.cos(a2), ny_ + r * math.sin(a2))
        L = math.hypot(p1[0] - p0[0], p1[1] - p0[1])
        m = int(L // step)
        for j in range(1, m):
            pts.append((p0[0] + (p1[0] - p0[0]) * j / m, p0[1] + (p1[1] - p0[1]) * j / m))
    return pts


def _arch(pts, cx, half, bend):
    return [(x, y + bend * ((x - cx) / half) ** 2) for x, y in pts]


def _sweep(d, path, col, depth, steps=8, extra=""):
    return "".join(f'<path d="{path}" fill="{col}" transform="translate(0 {F(depth * k / steps)})"{extra}/>' for k in range(steps, 0, -1))


def _word(d, text, xs, x1, base_fn, cap, sx, face, extr, extr_depth, glint, rim_col, infl, tilt=()):
    """Bubble letters: each glyph scaled to `cap`, compressed by sx, laid out between xs and x1, its baseline centre on
    base_fn(x) -> (y, slope deg); inflated (round stroke `infl`), extruded `extr_depth` down, a glint on the upper-left."""
    G = _glyphs()
    gs = [G["glyphs"][c] for c in text]
    k = cap / 720.0
    sxs = list(sx) if isinstance(sx, (list, tuple)) else [sx] * len(gs)   # director r3: a compression per letter
    inks = [(g["bounds"][2] - g["bounds"][0]) * k * q for g, q in zip(gs, sxs)]
    gap = ((x1 - xs) - sum(inks)) / max(1, len(gs) - 1)
    out, x = [], xs
    for i, (g, w) in enumerate(zip(gs, inks)):
        xc = x + w / 2
        y, slope = base_fn(xc)
        rot = slope + (tilt[i] if i < len(tilt) else 0.0)
        bx0 = g["bounds"][0]
        gid = d._id("g")
        # glyph in place: font units -> px (y up -> y down), ink centred on xc, baseline on y
        tr = (f"translate({F(xc)} {F(y)}) rotate({F(rot)}) scale({F(k * sxs[i])} {F(-k)}) "
              f"translate({F(-(bx0 + (g['bounds'][2] - g['bounds'][0]) / 2))} 0)")
        d.defs.append(f'<path id="{gid}" d="{g["d"]}" transform="{tr}"/>')
        st = f'stroke-width="{F(infl / (k * 1.0))}" stroke-linejoin="round"'
        # the stroke width is in font units inside the transform: infl px / k (x compressed by sx too, close enough)
        out.append(("".join(f'<use href="#{gid}" fill="{extr}" stroke="{extr}" {st} transform="translate(0 {F(extr_depth * j / 22)})"/>'
                            for j in range(22, 0, -1)),
                    f'<use href="#{gid}" fill="{rim_col}" stroke="{rim_col}" stroke-width="{F((infl + 5) / k)}" stroke-linejoin="round" '
                    f'transform="translate(0 {F(extr_depth + 2)})" opacity="0.55"/>',
                    f'<use href="#{gid}" fill="{face}" stroke="{face}" {st}/>',
                    gid))
        x += w + gap
    return out


LOGO = dict(sx=0.80, infl=34, depth=58, infl_out=26)   # polish r3: fatter letters (was 0.78 / 22 / OUT! 16)
# director r3: at sx 0.80 the five inked letters were 63 design px WIDER than their span before the 34 px inflation, so
# neighbours overlapped by ~95 px (~15 pt @3x): ARROW read as one melted blob next to 049's separate MAZE blocks. A
# compression per letter (the wide W most), a wider span on the plate and a thinner inflation leave the letters just
# kissing, as MAZE's do.
# The baseline is 25 px higher and the extrusion shallower so the letters' undersides stay on the blue face, as MAZE's do.
LOGO.update(sx=(0.75, 0.77, 0.77, 0.73, 0.60), infl=32, x0=222, x1=1828, base=635, depth=50, cap_out=312)
# LOGOGREEN (2026-09-28, SPEC.md ruling 44: the owner keeps the logo's art and motion; ONLY the OUT! sign's background turns
# GREEN in the D1 family). The arrow plate's FACE paint only -- its face gradient (4 stops), inner shade, inner glint and face
# outline -- moved from purple to green; its white rim, grey underside sweep, outer outline and drop shadow, the geometry,
# the pegs, the blue sign and every letter are unchanged. Derivation (build/p/LOGOGREEN/tools/candidates.py, colour.py):
# each purple colour keeps its own CIELab L* STEP (the same shading ramp, lifted +18 L*) at hue h 155 -- inside D1's green
# family (moss #86C04E h 127 ... crew mint fur #2FA888 h 170), clear of D1's teal chrome #17B3A3 h 183 / page #155158
# h 211 -- with its chroma capped at 42 = the crew mint ladder's (41-45). Why this tone and not the purple's own L* / full
# chroma: the colour test (logo_parts look, ruling 36 (c)) measures OUT!'s layered-vs-one-sprite residual, which scales
# with the contrast between the cream / lilac glyphs and the sign under their edges; a saturated green (h 160, +10 L*,
# C 57) raised OUT!'s max 37.3 -> 43.7/255 (25 px > 41), this paint keeps it under round 4's 37.3 (build/p/LOGOGREEN/).
# Was: face #C050FF / #A92CF6 / #8E16E4 / #7A0ED0, shade #5A0AA8, glint #E4A0FF, line #6A0CBC.
LOGO_SIGN_GREEN = dict(face0="#70C895", face40="#5AB280", face85="#479F6E", face100="#389161",
                       shade="#1D7A4C", glint="#A6FFC9", line="#2B8657")


def _logo_layers(W=306, H=236):
    """The logo's drawing split into its ANIMATION PARTS, each a list of SVG elements in paint order (UI-ART, OWNER P0 19:40 (b):
    the win sequence animates the parts; the shell's runtime colour-key split of the one PNG, upscaled, drew the owner's
    "weird lines" on OUT!). -> (doc, open_tag, layers) with layers = {"signPurple": the arrow plate (LOGO-ART-2: without
    the pegs), "pegs": the two grey pegs, "signBlue": the arched top plate (its drop shadow falls on the arrow plate), "ARROW" / "OUT!": one (extrusion
    elements, face element, glyph id, stroke width) per letter}. logo_arrow_out paints them in the original order
    (arrow plate, pegs, top plate, every ARROW extrusion, every ARROW face, then the same for OUT!), byte-identical."""
    d = Doc(W, H)
    sc = 0.47
    ox, oy = W * 1.5 - 1025 * sc, H * 1.5 - 834 * sc
    g = [f'<g transform="translate({F(ox)} {F(oy)}) scale({F(sc)})">']
    # ---- top plate: rim (white), underside (grey), blue face
    cx, half, bend = 1025.0, 915.0, 120.0
    outer = poly_path(_arch(rr_pts(110, 95, 1940, 785, 170), cx, half, bend))
    face_p = poly_path(_arch(rr_pts(155, 140, 1895, 740, 130), cx, half, bend))
    shadow = d.blur(14)
    g.append(f'<path d="{outer}" fill="#000000" fill-opacity="0.45" transform="translate(6 78)" filter="{shadow}"/>')
    # pegs (behind the top plate's underside, in front of the arrow plate: drawn after the arrow plate below)
    g.append(_sweep(d, outer, d.lin([(0, "#C9CCDC"), (0.6, "#A9AEC6"), (1, "#8D93AE")], 0, 400, 0, 960), 56))
    g.append(f'<path d="{outer}" fill="{d.lin([(0, "#FFFFFF"), (0.5, "#F2F3F8"), (1, "#DCDFEA")], 0, 95, 0, 900)}"/>')
    g.append(f'<path d="{face_p}" fill="{d.lin([(0, "#3E95FF"), (0.35, "#2479F6"), (0.8, "#1462E6"), (1, "#0E54D2")], 0, 140, 0, 870)}"/>')
    g.append(f'<g clip-path="{d.clip(face_p)}"><path d="{face_p}" fill="none" stroke="#0A3FAE" stroke-opacity="0.7" stroke-width="26" '
             f'transform="translate(0 -10)" filter="{d.blur(9)}"/>'
             f'<path d="{face_p}" fill="none" stroke="#7CC0FF" stroke-opacity="0.9" stroke-width="10" transform="translate(0 7)" '
             f'filter="{d.blur(3)}"/></g>')
    g.append(f'<path d="{face_p}" fill="none" stroke="#0B47BA" stroke-width="5"/>')
    g.append(f'<path d="{outer}" fill="none" stroke="#9EA4BE" stroke-width="4"/>')
    top_group = g[1:]
    g = g[:1]
    # ---- arrow plate (tilted -3 deg about its centre), pegs, then the top plate over them
    ax0, ay0, ax1, ay1, hx, htip, hover = 345, 925, 1440, 1460, 1440, 1765, 70
    acx, acy = (ax0 + htip) / 2, (ay0 + ay1) / 2
    arrow_pts = [(ax0, ay0), (hx, ay0), (hx, ay0 - hover), (htip, acy), (hx, ay1 + hover), (hx, ay1), (ax0, ay1)]
    face_pts = [(ax0 + 34, ay0 + 34), (hx - 8, ay0 + 34), (hx - 8, ay0 - hover + 50), (htip - 48, acy), (hx - 8, ay1 + hover - 50),
                (hx - 8, ay1 - 34), (ax0 + 34, ay1 - 34)]
    rot = -3.0
    ar = poly_path(_round_poly(xf(arrow_pts, deg=rot, ox=acx, oy=acy), 60, 8))
    af = poly_path(_round_poly(xf(face_pts, deg=rot, ox=acx, oy=acy), 40, 8))
    g.append(f'<path d="{ar}" fill="#000000" fill-opacity="0.45" transform="translate(6 60)" filter="{shadow}"/>')
    g.append(_sweep(d, ar, d.lin([(0, "#C6C9DA"), (0.6, "#A4A9C2"), (1, "#8A90AC")], 0, 900, 0, 1560), 46))
    g.append(f'<path d="{ar}" fill="{d.lin([(0, "#FFFFFF"), (0.5, "#F2F3F8"), (1, "#DCDFEA")], 0, 820, 0, 1560)}"/>')
    sg = LOGO_SIGN_GREEN                                  # LOGOGREEN (ruling 44): the sign's face paint; rim / underside kept
    g.append(f'<path d="{af}" fill="{d.lin([(0, sg["face0"]), (0.4, sg["face40"]), (0.85, sg["face85"]), (1, sg["face100"])], 0, 880, 0, 1500)}"/>')
    g.append(f'<g clip-path="{d.clip(af)}"><path d="{af}" fill="none" stroke="{sg["shade"]}" stroke-opacity="0.65" stroke-width="24" '
             f'transform="translate(0 -9)" filter="{d.blur(8)}"/>'
             f'<path d="{af}" fill="none" stroke="{sg["glint"]}" stroke-opacity="0.9" stroke-width="9" transform="translate(0 6)" '
             f'filter="{d.blur(3)}"/></g>')
    g.append(f'<path d="{af}" fill="none" stroke="{sg["line"]}" stroke-width="5"/>')
    g.append(f'<path d="{ar}" fill="none" stroke="#9EA4BE" stroke-width="4"/>')
    # pegs: short grey cylinders joining the plates (painted after the arrow plate, before the top plate). LOGO-ART-2
    # (LOGO-SPEC §9.2): their own layer "pegs" (the part logoPegs, z between the two signs) -- the arrow plate's rim under
    # them is drawn whole (the pegs only ever covered it), so logoSignPurple without them has a continuous top rim.
    pegs = []
    for x0 in (640, 1225):
        pg = rr(x0, 800, x0 + 110, 935, 16)
        pegs.append(f'<path d="{pg}" fill="{d.lin([(0, "#8A90AA"), (0.3, "#E6E8F2"), (0.55, "#F6F7FB"), (1, "#8C92AC")], x0, 0, x0 + 110, 0)}" '
                    f'stroke="#7C829E" stroke-width="3"/>')
    head, purple = g[0], g[1:]
    layers = {"signPurple": purple, "pegs": pegs, "signBlue": top_group}
    # ---- words
    def arch_base(yb):
        return lambda x: (yb + bend * ((x - cx) / half) ** 2, math.degrees(math.atan(2 * bend * (x - cx) / half ** 2)))
    yel = d._id("yf")
    d.defs.append(f'<linearGradient id="{yel}" x1="0" y1="1" x2="0" y2="0"><stop offset="0" stop-color="#FFE62E"/>'
                  f'<stop offset="0.45" stop-color="#FFCF1C"/><stop offset="1" stop-color="#FFB414"/></linearGradient>')
    # (gradient in the glyph's own bbox: the glyph is y-flipped, so 1 -> 0 runs top -> bottom on screen)
    ext_y = d.lin([(0, "#F08A08"), (0.6, "#DC7004"), (1, "#C45A02")], 0, 250, 0, 780)
    # director r2 (grader A: ARROW read thinner and flatter than the original's puffy letters -- 0.70 compression, a
    # shallow extrusion): wider letters (0.84) that touch like bubble letters, a fatter inflation, a deeper extrusion
    word1 = _word(d, "ARROW", LOGO.get("x0", 250), LOGO.get("x1", 1800), arch_base(LOGO.get("base", 660)), 430, LOGO["sx"], f"url(#{yel})", ext_y, LOGO["depth"], "#FFF6C0",
                  "#D67A00", LOGO["infl"], tilt=(-6.0, 3.5, -2.5, 4.5, -4.0))
    wht = d._id("wf")
    d.defs.append(f'<linearGradient id="{wht}" x1="0" y1="1" x2="0" y2="0"><stop offset="0" stop-color="#FFFFFF"/>'
                  f'<stop offset="0.6" stop-color="#F8F5F4"/><stop offset="1" stop-color="#E9E3E6"/></linearGradient>')
    t = math.radians(rot)

    def plate_base(x):
        return (1355 + math.tan(t) * (x - acx), rot)
    ext_w = d.lin([(0, "#B9B2CC"), (1, "#8E86AA")], 0, 900, 0, 1400)
    # director r3: OUT! at cap 312 over x 500-1465 (was 335 over 470-1500): at 335 the white letters filled the arrow
    # plate edge to edge; 049's OUT! keeps a purple margin all round
    word2 = _word(d, "OUT!", 500, 1465, plate_base, LOGO.get("cap_out", 335), 1.0, f"url(#{wht})", ext_w, 70, "#FFFFFF", "#A9A0C0", 16,
                  tilt=(-4.0, 2.5, -2.0, 5.0))
    # polish lane r3 (grader A / director: MAZE's letters are fatter and puffier; ours read as flat faces over a shifted
    # dark copy = a double image): the extrusion is now a SOLID side (18 steps, orange #EE8A06 -> #B85200 down it, no
    # outlines), and every face is INFLATED inside its own mask -- a dark rim that is thick along the lower edges
    # (#E47400, blurred) and a light rim along the upper-left edges (#FFF8C0) -- so each letter reads as one puffy
    # rounded solid, like the original logo's letters. OUT! gets the same in cream / lilac-grey.
    def mix(a, b, t_):
        a_, b_ = [int(a[i:i + 2], 16) for i in (1, 3, 5)], [int(b[i:i + 2], 16) for i in (1, 3, 5)]
        return "#%02X%02X%02X" % tuple(round(a_[i] + (b_[i] - a_[i]) * t_) for i in range(3))
    for name, word, infl, depth, et, eb, dark, light, k_ in (
            ("ARROW", word1, LOGO["infl"], LOGO["depth"], "#EE8A06", "#B45000", "#E06C00", "#FFF8C0", 430 / 720.0),
            ("OUT!", word2, LOGO["infl_out"], 44, "#CBC4DC", "#877FA6", "#BDB5CF", "#FFFFFF", LOGO.get("cap_out", 335) / 720.0)):
        sw = infl / k_
        steps = 18
        exts = []
        for ex, rim, face, gid in word:          # every extrusion first, then every face (letters overlap a little)
            exts.append([])
            for j in range(steps, 0, -1):
                c_ = mix(et, eb, j / steps)
                exts[-1].append(f'<use href="#{gid}" fill="{c_}" stroke="{c_}" stroke-width="{F(sw)}" stroke-linejoin="round" '
                                f'transform="translate(0 {F(depth * j / steps)})"/>')
        # the inflation: one SVG filter per word colour (inner bevel from the letter's own alpha: a blurred copy shifted UP
        # leaves a soft dark rim along the lower edges, one shifted DOWN-RIGHT a light rim along the upper-left edges)
        fid = d._id("inf")
        d.defs.append(f'<filter id="{fid}" filterUnits="userSpaceOnUse" x="0" y="0" width="2200" height="1800">'
                      f'<feGaussianBlur in="SourceAlpha" stdDeviation="9" result="b"/>'
                      f'<feOffset in="b" dx="0" dy="-13" result="bo"/>'
                      f'<feComposite in="SourceAlpha" in2="bo" operator="out" result="be"/>'
                      f'<feFlood flood-color="{dark}" flood-opacity="0.95" result="dk"/>'
                      f'<feComposite in="dk" in2="be" operator="in" result="dke"/>'
                      f'<feGaussianBlur in="SourceAlpha" stdDeviation="5" result="b2"/>'
                      f'<feOffset in="b2" dx="5" dy="8" result="bo2"/>'
                      f'<feComposite in="SourceAlpha" in2="bo2" operator="out" result="te"/>'
                      f'<feFlood flood-color="{light}" flood-opacity="0.95" result="lt"/>'
                      f'<feComposite in="lt" in2="te" operator="in" result="lte"/>'
                      f'<feMerge><feMergeNode in="SourceGraphic"/><feMergeNode in="dke"/><feMergeNode in="lte"/></feMerge></filter>')
        layers[name] = []
        for (ex, rim, face, gid), e_ in zip(word, exts):
            fill = re.search(r'fill="([^"]+)"', face).group(1)
            layers[name].append((e_, f'<g filter="url(#{fid})"><use href="#{gid}" fill="{fill}" stroke="{fill}" stroke-width="{F(sw)}" '
                                     f'stroke-linejoin="round"/></g>', gid, sw))
    return d, head, layers


def logo_arrow_out(W=306, H=236):
    d, head, L = _logo_layers(W, H)
    g = [head] + L["signPurple"] + L["pegs"] + L["signBlue"]      # byte-identical to the one-piece before the peg split
    for name in ("ARROW", "OUT!"):
        for exts, face, gid, sw in L[name]:
            g += exts
        for exts, face, gid, sw in L[name]:
            g.append(face)
    g.append("</g>")
    d.add(*g)
    return d.svg()


# ---- the logo's animation parts (UI-ART, OWNER P0 19:40 (b); proofs: art/ui/tools/logo_parts.py -> build/logo/art/)
# The win sequence animates the logo in parts (blue sign, A R R O W popping one by one, the purple arrow sign, "OUT!"
# ballooning to ~2.6x). Each part is exported STRAIGHT FROM THE VECTOR DRAWING above (never cut from the PNG), rendered
# bigger than its largest on-screen size so the animation only ever scales DOWN, on a frame that is an integer rect of
# logoArrowOut's own @3x pixel grid (918 x 708 px), so the parts re-assemble onto logoArrowOut pixel for pixel.
#   LOGO_PART_FRAMES[id] = (layer, x, y, w, h, factor): the frame in logoArrowOut @3x px; the file is (w, h) x factor px.
#   factor: signs 1.5, letters 2.0, OUT! 3.0 (x logoArrowOut @3x; integer WebKit mappings, see logo_parts.py). On screen
#   (ui.json celebrate.logo + ArtInk box of logoArrowOut + WinLogoSequence win.settleScale 0.94) the settled logo is
#   0.94625 x logoArrowOut and the largest scales are 1.0066 (signs, flying in at group scale 1), 1.258 (a letter's 1.25
#   pop) and 2.617 (OUT! at outBig + 0.1 = 2.6) x logoArrowOut: each file is 1.49x / 1.59x / 1.15x its largest on-screen
#   size (still >= 1.07x if the settle is moved so the SETTLED logo fills celebrate.logo), OUT! = 3.17x its settled size.
# Paint order = z order: logoSignPurple, logoSignBlue, logoLetterA, R1, R2, O, W, logoOut. In the one-piece logo every
# ARROW extrusion is painted before every ARROW face, so where two letters touch, a letter's extrusion lies UNDER the face
# of the letter before it. As one layer per letter that is Porter-Duff ATOP: letter i (i > 0) = its face over (the faces of
# the letters before it ATOP its extrusion) -- the earlier faces are kept only where this extrusion is, so they travel with
# this letter during its own pop. A hole in the extrusion instead (the first export) conflates the hole's anti-aliased edge
# with the face's in the composite (a x (1 - a) of the wrong colour: split test max 79.5 at the A|R1, R1|R2, O|W joins).
# WebKit cannot draw that ATOP pixel-exactly in one SVG (a mask cut with the bare glyph misses the face's filtered edge;
# filtered content inside a mask buffer lands ~1 device px off the same content on the canvas), so these four parts are
# rendered as three plain PASSES (logo_part_svg pass_ "ext" / "before" / "face", same frame, same clamped regions) and
# composited in premultiplied float by art/ui/tools/logo_parts.compose (svg.py does it for any SVG whose root carries
# data-passes). The one-SVG version below (plus-lighter ATOP) stays the source record / browser preview.
# Measured 2026-09-26 by art/ui/tools/logo_parts.py measure: each part's alpha box on logoArrowOut's grid (2x WebKit render,
# area filter) + 3 px, sizes rounded so (w, h) x factor is whole px AND whole pt (check.py: px % 3 == 0).
LOGO_PART_FRAMES = {
    "logoSignPurple": ("signPurple", 120, 332, 698, 376, 1.5),   # ink x 123..814 y 337..707 (the canvas clips its shadow)
    "logoSignBlue": ("signBlue", 12, 2, 898, 424, 1.5),          # ink x 16..907 y 5..422 (incl. its drop shadow)
    "logoLetterA": ("ARROW", 68, 82, 174, 261, 2.0),             # ink x 71..239 y 85..339
    "logoLetterR1": ("ARROW", 225, 57, 156, 249, 2.0),           # ink x 228..378 y 60..303
    "logoLetterR2": ("ARROW", 354, 49, 159, 252, 2.0),           # ink x 357..510 y 53..297
    "logoLetterO": ("ARROW", 510, 52, 174, 252, 2.0),            # ink x 513..681 y 56..301
    "logoLetterW": ("ARROW", 668, 66, 195, 261, 2.0),            # ink x 671..860 y 70..324
    "logoOut": ("OUT!", 194, 436, 486, 206, 3.0),                # ink x 197..677 y 439..639
}
LOGO_LETTERS = ("logoLetterA", "logoLetterR1", "logoLetterR2", "logoLetterO", "logoLetterW")

# ---- LOGO-ART-2 (2026-09-27; build/logo/LOGO-SPEC.md §9.1-9.3, proofs: art/ui/tools/logo_parts.py *2 -> build/logo/art2/)
# P0: "OUT!" as FOUR layers (v552's glyphs spread apart and tilt on their own, LOGO-SPEC D6): logoOutO, logoOutU, logoOutT,
#   logoOutBang, split exactly like ARROW's letters -- paint order O < U < T < !; glyph i > 0 = its face OVER (the faces
#   of the glyphs before it ATOP its extrusion), rendered as the three passes ext / before / face; O is one pass (as A).
#   Factor 4.0 x logoArrowOut @3x (8 WebKit device px per logo px, an integer mapping): each file >= 3.97x its settled
#   size at the new rest (k 1.00665), >= 1.3x its largest on-screen size (the 3.01x OUT! peak; LOGO-SPEC table U).
#   logoOut (one layer) stays: Loading + the fallback.
# P1: the two grey pegs as their own layer logoPegs (factor 1.5, like the signs), logoSignPurple re-exported without them.
# P2: four bent variants of logoSignPurple (LOGO_BENDS): the rest drawing warped y' = y + k (x - x_a)^2 in the part's own
#   axes (its frame / the layer's axes, as sx / sy), k = |bend| rad / (2 L_body), x_a = the anchor's x (the purple face's
#   centroid): the ends move DOWN (a stronger arch). L_body (LOGO_BEND body) is set so that LOGO-SPEC's own bend metric
#   reads the nominal bend (see LOGO_BEND).
#   The warp runs on the premultiplied WebKit 2x render of the rest drawing (clipped at the canvas bottom exactly as the
#   rest file is), before the 2:1 area filter (svg.py data-warp / logo_parts.warp). Frame = logoSignPurple's frame padded
#   at the bottom (LOGO_BEND pad), same x, y, width, factor 1.5; the anchor point is a fixed point of the warp.
LOGO_GLYPHS = ("logoOutO", "logoOutU", "logoOutT", "logoOutBang")
LOGO_PART_FRAMES.update({                                         # measured 2026-09-27 (logo_parts.py measure)
    "logoPegs": ("pegs", 274, 334, 336, 72, 1.5),                # ink x 277..606 y 337..403 (on even logo px: the sign's grid)
    "logoOutO": ("OUT!", 193, 454, 171, 189, 4.0),               # ink x 197..360 y 457..639
    "logoOutU": ("OUT!", 348, 446, 153, 189, 4.0),               # ink x 352..497 y 450..631
    "logoOutT": ("OUT!", 467, 438, 156, 189, 4.0),               # ink x 471..619 y 442..624
    "logoOutBang": ("OUT!", 611, 436, 69, 186, 4.0),             # ink x 614..677 y 439..618
})
# x_a = the rest sign's purple-face centroid (LOGO-SPEC's anchor, frac 0.46619 of its frame); pad = 24 logo px = 8.05 pt at
# the bottom (LOGO-SPEC: >= 8 pt; the -10 deg warp moves the lowest ink to 720.8, 11 px above the padded frame's edge)
# body = L_body (logo px), set so that LOGO-SPEC's own bend measurement (build/logo/spec/tools/bend.py, the one that
# measured v552's -8...-11 deg, table K) reads each variant at its nominal bend: -2.53 / -4.96 / -7.55 / -10.11 deg
# (logo_parts.py bendcal -> build/logo/art2/bend_calibration.json). §2's literal 0.70 x the frame width (488.6, as
# spec/tools/render_ours.py warps) read only 83 % of the nominal bend (-8.34 for -10).
LOGO_BEND = dict(xa=445.402, body=398.4, clip=708, pad=24)
LOGO_BENDS = {"logoSignPurpleBend25": -2.5, "logoSignPurpleBend50": -5.0, "logoSignPurpleBend75": -7.5,
              "logoSignPurpleBend100": -10.0}
for _pid in LOGO_BENDS:
    _f = LOGO_PART_FRAMES["logoSignPurple"]
    LOGO_PART_FRAMES[_pid] = (_f[0], _f[1], _f[2], _f[3], _f[4] + LOGO_BEND["pad"], _f[5])
# LOGO-SPEC-FIX (2026-09-27, LOGO-SPEC M3): logoSignPurple itself ships on the bend variants' PADDED frame (same x, y,
# width, factor; + LOGO_BEND pad logo px at the bottom), so the arrow-sign layer's five contents (rest + 4 bends) share
# ONE frame and ONE anchor and a contents-only discrete swap is exact (before: rest 1047 x 564 px vs bends 1047 x 600 px --
# a contents-only swap squashed the sign and moved it ~7.9 pt). The drawing is still rendered on its OWN frame (y + h =
# the canvas bottom, which clips its shadow, exactly as before) and LOGO_PAD logo px of transparent rows are appended
# after the render (root data-pad: art/ui/tools/svg.py, logo_parts.render_part): its pixels are unchanged inside.
LOGO_PAD = {"logoSignPurple": LOGO_BEND["pad"]}
_f = LOGO_PART_FRAMES["logoSignPurple"]
LOGO_PART_FRAMES["logoSignPurple"] = (_f[0], _f[1], _f[2], _f[3], _f[4] + LOGO_PAD["logoSignPurple"], _f[5])

# ---- LOGO-ART-3 (2026-09-27; the owner: "the OUT! has weird lines when it grows on the screen"; proofs:
#   art/ui/tools/logo_parts.py proof3 / motion -> build/logo/art3/)
# Rounds 1-2 exported a letter / glyph i > 0 as ONE layer: its face OVER (the faces of the letters before it ATOP its
# extrusion). That re-assembles the one-piece at rest, but it BAKES pieces of the neighbour's face into the file (logoOutT
# carries 501 logo px^2 of U's cream face, logoOutU a strip of O's, R2 63 px^2 of R1's ...): when LOGO-SPEC's motion
# spreads the glyphs apart (U|T +4...+20 pt, O|U +4...+14 pt at W+1.30-1.60; ARROW's letters overshoot and tilt on their
# own at W+0.69-1.27) those pieces travel with the wrong glyph and show as a cream block + a light line.
# Round 3: every independently moving letter / glyph is a PAIR of layers, each a plain single pass of the SAME drawing:
#   <id>Ext  = the glyph's extrusion alone (the 18-step lilac / orange 3-D side, its stroke = its outline),
#   <id>Face = the glyph's face alone (the cream / yellow face through the word's inflation filter = its outline + bevel),
# on the SAME frame as the round-1/2 part (the same logo_rect, anchor and file size), with NO element of any other glyph.
# The two layers of a pair share ONE transform (same anchor, same animation values). Stacking order = the one-piece's
# paint order: every extrusion of a word under every face of that word (ARROW: 5 Ext then 5 Face inside the blue sign;
# OUT!: Ext z 7-10, Face z 11-14), so at rest the stack IS logo_arrow_out's order and re-assembles it exactly. A pair's
# root carries data-pass="ext" / "face": svg.py area-filters its premultiplied 2x render 2:1 in float (as the passes).
# The round-1/2 ids stay (logoOut = Loading / fallback; the composed letters / glyphs are no longer animated).
# The Ext layer is TRIMMED under its own face (data-trim, logo_parts.trim_ext): two separately filtered layers conflate
# where their edges coincide (the extrusion's sides run exactly under the face's sides: up to +0.24 alpha of the lilac /
# orange side on the side-edge pixels at the settled scale); so where its OWN face is opaque the extrusion is removed,
# except within LOGO_TRIM logo px of where it shows (outside that face). The removed part is always hidden by that face
# (same transform, opaque), so face OVER trimmed extrusion == face OVER extrusion at the render's resolution.
# LOGO-ART-4 (ruling 36 (c): "if the trim still causes lines anywhere, drop or change the trim"): 4 -> 1 logo px. The kept
# ring must cover the face's bottom-edge anti-aliasing (r 0: 40 387 device px > 16/255 over 12 opacity-1 frames, the
# bottom-edge seam opens; r 0.5: 23 196), but along the SIDE edges the ring makes the extrusion's edge coincide with the
# face's, and those coinciding runs (conflation columns) grow with r (r 1: 3 770 px > 16 / 78 > 41; r 1.5: 4 030 / 127;
# r 2: 4 222 / 168; r 4: 4 908 / 334; r 8: 6 119 / 652; untrimmed: 19 459 / 3 216) -- build/logo/art4/trim_experiment*.json.
LOGO_TRIM = 1                                                     # logo @3x px
LOGO_PAIRS = {}
for _base in LOGO_LETTERS + LOGO_GLYPHS:
    for _k, _suf in (("ext", "Ext"), ("face", "Face")):
        LOGO_PAIRS[_base + _suf] = (_base, _k)
        LOGO_PART_FRAMES[_base + _suf] = LOGO_PART_FRAMES[_base]

# ---- LOGO-ART-4 (2026-09-27, SPEC.md ruling 36 (b); proofs: art/ui/tools/logo_parts.py swap / look -> build/logo/art4/)
# While an ARROW letter FADES (its opacity < 1, W+0.69...0.81) a pair drawn with per-layer opacity lets the trimmed
# extrusion show through the translucent face as an orange outline (the second adversarial check: up to 5 219 device px
# > 16/255 per glyph). So each letter also ships ONE flattened sprite <id>Flat = its own face OVER its own UNTRIMMED
# extrusion, nothing of any neighbour: two plain passes (the Ext's and the Face's elements, the same frame and clamped
# regions) composed in premultiplied float at the raw render resolution, then the exact 2:1 area filter -- one layer,
# so it fades as one. Same frame / anchor / file size as the pair; shown while the letter's opacity < 1, the pair from the
# first frame at opacity 1. (OUT! needs no flat: its 8 layers fade inside one group-opacity container, LOGO-SPEC §2.)
LOGO_FLAT_PASSES = ("ext", "face")
LOGO_FLATS = {}
for _base in LOGO_LETTERS:
    LOGO_FLATS[_base + "Flat"] = _base
    LOGO_PART_FRAMES[_base + "Flat"] = LOGO_PART_FRAMES[_base]


def _word_part(pid):
    """(word layer, index) of a letter / glyph part (a flat sprite: its letter's)."""
    pid = LOGO_FLATS.get(pid, pid)
    if pid in LOGO_LETTERS:
        return "ARROW", LOGO_LETTERS.index(pid)
    return "OUT!", LOGO_GLYPHS.index(pid)


def _logo_part_elements(pid, d, L, mask_letters=True):
    """The SVG elements (inside the logo's design group) of one part."""
    if pid == "logoSignPurple" or pid in LOGO_BENDS:
        return list(L["signPurple"])
    if pid == "logoPegs":
        return list(L["pegs"])
    if pid == "logoSignBlue":
        return list(L["signBlue"])
    if pid == "logoOut":
        return [e for exts, face, gid, sw in L["OUT!"] for e in exts] + [face for exts, face, gid, sw in L["OUT!"]]
    if pid in LOGO_PAIRS:                                   # LOGO-ART-3: the glyph's own extrusion OR its own face, nothing else
        base, k = LOGO_PAIRS[pid]
        return _logo_pass_elements(base, L, k)
    if pid in LOGO_FLATS:                                   # LOGO-ART-4: its own extrusion (whole), then its own face; the
        exts, face, gid, sw = L[_word_part(pid)[0]][_word_part(pid)[1]]   # one-SVG record (svg.py renders the 2 passes)
        return list(exts) + [face]
    word, i = _word_part(pid)
    exts, face, gid, sw = L[word][i]
    if mask_letters and i > 0:
        # The earlier letters' faces cover this letter's extrusion: paint them ATOP it (Porter-Duff), E x (1 - a_faces) +
        # F x b_ext, the two terms SUMMED (plus-lighter in an isolated group). A plain luminance hole in the extrusion
        # (the first export) left an a x (1 - a) conflation seam along every earlier face's anti-aliased edge (split test
        # max 79.5 at the A|R1, R1|R2 and O|W junctions); ATOP re-assembles exactly. The faces carried here are the part
        # of the earlier letters that lies over this extrusion (they travel with this letter during its own pop).
        # The hole must be the faces' RENDERED alpha, not the bare glyph's: the inflation filter's feMerge lifts the alpha
        # of every anti-aliased edge pixel (up to +105/255 on A's face) and WebKit resamples the filter output, so a hole
        # cut with the plain glyph misses the face's edge (that WAS the first export's seam). The faces are drawn black
        # through a twin of their own filter (same region and primitives, floods black) over white: luminance = 1 - a_face.
        # (The same for OUT!'s glyphs U, T, ! with the word's own filter.)
        fid = re.search(r'filter="url\(#([^)]+)\)"', L[word][0][1]).group(1)
        src = next(x for x in d.defs if f'<filter id="{fid}"' in x)
        blk = d._id("infk")
        d.defs.append(re.sub(r'flood-color="#[0-9A-Fa-f]{6}"', 'flood-color="#000000"', src.replace(f'id="{fid}"', f'id="{blk}"')))
        holes = "".join(f'<g filter="url(#{blk})"><use href="#{g_}" fill="#000000" stroke="#000000" stroke-width="{F(w_)}" '
                        f'stroke-linejoin="round"/></g>' for _, _, g_, w_ in L[word][:i])
        m = d.mask(f'<rect x="-6000" y="-6000" width="14000" height="14000" fill="#FFFFFF"/>{holes}')
        within = d.mask("".join(re.sub(r'\b(fill|stroke)="#[0-9A-Fa-f]{6}"', r'\1="#FFFFFF"', e) for e in exts))
        before = "".join(f for _, f, _, _ in L[word][:i])
        return ['<g style="isolation:isolate">' + f'<g mask="{m}">' + "".join(exts) + "</g>"
                + f'<g mask="{within}" style="mix-blend-mode:plus-lighter">{before}</g></g>', face]
    return list(exts) + [face]


LOGO_PASSES = ("ext", "before", "face")


def logo_part_passes(pid):
    """The passes a part is rendered in: () for a one-pass part (the signs, the pegs, A, O of OUT!, OUT!, the pair layers),
    LOGO_PASSES for R1 R2 O W and OUT!'s U T ! (rounds 1-2), LOGO_FLAT_PASSES for the flat sprites (LOGO-ART-4)."""
    if pid in LOGO_FLATS:
        return LOGO_FLAT_PASSES
    return LOGO_PASSES if pid in LOGO_LETTERS[1:] or pid in LOGO_GLYPHS[1:] else ()


def _logo_pass_elements(pid, L, pass_):
    word, i = _word_part(pid)
    exts, face, gid, sw = L[word][i]
    if pid in LOGO_FLATS:                                   # a flat sprite: its OWN extrusion and face only (no "before")
        return {"ext": list(exts), "face": [face]}[pass_]
    return {"ext": list(exts), "before": [f for _, f, _, _ in L[word][:i]], "face": [face]}[pass_]


def logo_part_svg(pid, frame=None, factor=None, mask_letters=True, pass_=None):
    """One part as its own SVG: viewBox = the part's frame in logoArrowOut @3x px, root size = frame x factor / 3 (pt), so
    svg.py rasterises it at exactly frame x factor px. frame/factor default to LOGO_PART_FRAMES (the full canvas at 1x
    when a part has no frame yet: the measuring pass). pass_ ("ext" / "before" / "face", multi-pass parts only) = just
    that pass on the same frame and regions; without it a multi-pass part is the one-SVG ATOP record, its root marked
    data-passes so svg.py rasterises it from the passes. A bend variant's root carries data-warp="bend x_a L_body clip"
    (degrees; logo @3x px): svg.py / logo_parts warp its render before the area filter (the SVG itself draws the rest
    drawing, unwarped, on the padded frame). A LOGO_PAD part on its own (padded) frame is drawn on the UNPADDED frame and
    its root carries data-pad="<logo px>": svg.py / logo_parts.render_part append that many transparent rows after the
    render (LOGO-SPEC-FIX M3: logoSignPurple on the bend variants' frame, its pixels unchanged)."""
    if frame is None:
        f_ = LOGO_PART_FRAMES.get(pid)
        frame, fac = (f_[1:5], f_[5]) if f_ else ((0, 0, 918, 708), 1.0)
        factor = factor or fac
    factor = factor or 1.0
    pad = 0
    if pid in LOGO_PAD and tuple(frame) == tuple(LOGO_PART_FRAMES[pid][1:5]):
        pad = LOGO_PAD[pid]
        frame = (frame[0], frame[1], frame[2], frame[3] - pad)
    d, head, L = _logo_layers()
    passes = logo_part_passes(pid) if mask_letters else ()
    els = _logo_pass_elements(pid, L, pass_) if pass_ else _logo_part_elements(pid, d, L, mask_letters)
    body = "\n".join([head] + els + ["</g>"])
    mark = f' data-passes="{",".join(passes)}"' if passes and not pass_ else ""
    if pid in LOGO_PAIRS:
        mark += f' data-pass="{LOGO_PAIRS[pid][1]}"'         # svg.py: float premultiplied 2:1 area filter (as the passes)
        if LOGO_PAIRS[pid][1] == "ext":
            mark += f' data-trim="{LOGO_TRIM}"'               # svg.py: trimmed under its own face (logo_parts.trim_ext)
    if pid in LOGO_BENDS:
        mark += ' data-warp="' + " ".join(f"{v:g}" for v in (LOGO_BENDS[pid], LOGO_BEND["xa"], LOGO_BEND["body"],
                                                                  LOGO_BEND["clip"])) + '"'     # exact (round-trips)
    if pad:
        mark += f' data-pad="{pad}"'                          # svg.py: + pad logo px of transparent rows at the bottom
    x, y, w, h = frame
    # WebKit rasterises a filter / mask over its whole REGION: the logo's are canvas-wide (the blurs 8 x the canvas, the
    # letter bevel 2200 x 1800 design units), which at 2.5-6 device px per design unit passes WebKit's filter size limit
    # (OUT! at 3x lost its faces). In a part, every region is clamped to the part's own viewBox in design units + 150 (the
    # largest shadow offset 78 + 3 sigma of the widest blur 42): the pixels inside the viewBox are unchanged.
    tx, ty, sc = (float(v) for v in re.match(r'<g transform="translate\(([-\d.]+) ([-\d.]+)\) scale\(([\d.]+)\)">', head).groups())
    rx, ry, rw, rh = (x - tx) / sc - 150, (y - ty) / sc - 150, w / sc + 300, h / sc + 300
    defs = re.sub(r'((?:filterUnits|maskUnits)="userSpaceOnUse") x="[-\d.]+" y="[-\d.]+" width="[\d.]+" height="[\d.]+"',
                  lambda m_: f'{m_.group(1)} x="{F(rx)}" y="{F(ry)}" width="{F(rw)}" height="{F(rh)}"', "".join(d.defs))
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{F(w * factor / 3)}" height="{F(h * factor / 3)}" '
            f'viewBox="{F(x)} {F(y)} {F(w)} {F(h)}" data-resample="box"{mark}>\n<defs>{defs}</defs>\n{body}\n</svg>\n')


# ====================================================================================== home / events / profile icons
def lemniscate(cx, cy, a, N=96):
    pts = []
    for k in range(N):
        t = 2 * math.pi * k / N
        den = 1 + math.sin(t) ** 2
        pts.append((cx + a * math.cos(t) / den, cy + a * math.sin(t) * math.cos(t) / den))
    return poly_path(pts)


# Small infinite-lives heart (shot 026 home Claw bar reward, 46 x 42 pt): heartLives' glossy red heart with a thick cream
# infinity sign (#FFF1E6, outline #7A0A12) in its upper half; the duration under it ("30m") is LIVE text centred at
# (23, 29) pt of this frame.
def heart_infinite_small(W=46, H=42):
    """Polish lane r3 (grader A: the infinity strokes fatter and the heart a bit rounder than 026's). Re-measured on
    026 / 133 / 168 (identical): with this frame at the reward slot's top-left (323.6, 108.4) the red heart spans
    x 325.7-366.3, y 112.3-~147 (HEART2's shape, 42 x 36.4 pt incl. the outline: round 2's was 45 x 39); the cream
    infinity sign is 24.4 x 13 pt centred at frame (22.6, 19.1): round loops (the lemniscate 1.25x taller), cream
    #F8E6DA -> #F0D6C8 with a THIN dark-red outline #A00A12 and only a hint of a drop; small red lens holes. Heart colours
    as heartLives. The duration ("1h", "30m") is LIVE text centred at frame (22.6, 32.9) pt, over the heart's tip."""
    d = Doc(W, H)
    hx, hy, hw, hh = 6.2, 11.6, 122.0, 105.2
    p = heart2_path(hx, hy, hw, hh)
    d.add(f'<path d="{p}" fill="#1D3D40" fill-opacity="0.42" filter="{d.blur(1.6)}" transform="translate(0 2.4)"/>')
    d.add(f'<path d="{p}" fill="#7A0A14" stroke="#6C0A14" stroke-width="4.0" stroke-linejoin="round"/>')
    d.add(f'<path d="{p}" fill="{d.rad([(0, "#F83C2A"), (0.28, "#F0301F"), (0.55, "#E2160C"), (0.8, "#CC0603"), (1, "#B00300")], hx + 0.60 * hw, hy + 0.46 * hh, 0.72 * hw, hx + 0.62 * hw, hy + 0.48 * hh)}"/>')
    d.add(f'<g clip-path="{d.clip(p)}"><path d="{p}" fill="none" stroke="#A00006" stroke-width="7.5" filter="{d.blur(1.5)}"/>'
          f'<path d="{p}" fill="none" stroke="#C20000" stroke-opacity="0.8" stroke-width="14" transform="translate(0 -5.5)" filter="{d.blur(2.6)}"/>'
          f'<ellipse cx="{F(hx + 30)}" cy="{F(hy + 31)}" rx="12" ry="7.5" transform="rotate(-38 {F(hx + 30)} {F(hy + 31)})" '
          f'fill="{d.rad([(0, "#FFB488", 1), (0.5, "#FC8A5C", 0.75), (1, "#F85A3C", 0)], hx + 30, hy + 31, 13)}" filter="{d.blur(1.0)}"/>'
          f'<path d="M{F(hx + 86)} {F(hy + 7)} Q{F(hx + 110)} {F(hy + 10)} {F(hx + 116)} {F(hy + 34)}" fill="none" stroke="#FF9A84" '
          f'stroke-opacity="0.8" stroke-width="2.8" stroke-linecap="round" filter="{d.blur(0.7)}"/></g>')
    # the infinity sign: a lemniscate 1.25x taller (round loops), stroke 12 px cream + a 1.8 px dark-red outline
    icx, icy, a = 22.6 * 3, 19.1 * 3, 29.6
    pts = []
    for k in range(120):
        t = 2 * math.pi * k / 120
        den = 1 + math.sin(t) ** 2
        pts.append((icx + a * math.cos(t) / den, icy + 1.25 * a * math.sin(t) * math.cos(t) / den))
    inf = poly_path(pts)
    d.add(*toon([("s", inf, 12.2)], d.lin([(0, "#FCEEE4"), (0.5, "#F7E3D6"), (1, "#EDD2C3")], 0, icy - 20, 0, icy + 20), "#A00A12", 1.8,
                drop=1.2, drop_col="#8A0610"))
    return d.svg()


# Claw points icon (shot 026 home Claw bar, 48 x 44 pt): a pale-blue bevelled hexagon (points left/right, turned -8 deg)
# holding a purple hexagon and a chunky pale-blue up-arrow with a navy outline.
def icon_hex_arrow(W=40, H=40):
    """Polish lane r3 (grader A: ~1.15x too big at 1:1, the arrow whiter and the bevel thinner than 026's). Re-measured
    on 026 / 168 / 204 (identical, a static icon): silhouette 37.3 x 35 pt at x 30.3-67.7, y 110.7-145.7 incl. a thin 3D
    side at the lower left; the purple well 25.3 x 24.3 pt. Centre row (168): outer edge #5285B3 ~1 pt, a light line
    #EEF8FF, frame face #D0E9FF, the well's LEFT inner edge light #F4FBFF and its RIGHT inner edge dark #4758AC, flat
    purple #950CF7 / #920EF4; the arrow (19 pt tall, head 16 x 8.8 pt, shaft 8.9 pt) is light sky #C8E5FC (not white)
    edged in DARK PURPLE #360C82 / #440188 (not navy), no drop. Turned -3 deg. The frame is 40 x 40 (the side's shadow
    needs the bottom 2 pt): the shell draws it 1:1 in the rect (29.0, 109.2, 40, 40)."""
    d = Doc(W, H)
    s_ = W / 40.0
    cx, cy = W * 1.5 + 1.9 * s_, 57.0 * s_ - 2.2 * s_       # (the 3D side + its shadow need the 2 pt below)
    rot = -3.0
    a, b = 54.6 * s_, 49.0 * s_
    def hx(ax, bx, dx=0.0, dy=0.0, r=4.0 * s_):
        return poly_path(xf(_round_poly(hexagon(cx + dx, cy + dy, ax, bx, ax * 0.5), r, 6), deg=rot, ox=cx, oy=cy))
    outer = hx(a, b)
    side = hx(a, b, -4.6 * s_, 6.6 * s_)
    mid = hx(a, b, -2.3 * s_, 3.3 * s_)
    d.add(f'<path d="{side}" fill="#0A1E60" fill-opacity="0.45" transform="translate(0 {F(3.2 * s_)})" filter="{d.blur(2.0 * s_)}"/>')
    for p_ in (side, mid, outer):
        d.add(f'<path d="{p_}" fill="#4F7DB2" stroke="#4F7DB2" stroke-width="{F(3.0 * s_)}" stroke-linejoin="round"/>')
    for p_ in (side, mid):
        d.add(f'<path d="{p_}" fill="{d.lin([(0, "#C4D8F2"), (0.6, "#A9C0E6"), (1, "#93ACDA")], 0, cy - b, 0, cy + b + 6 * s_)}"/>')
    d.add(f'<path d="{outer}" fill="{d.lin([(0, "#E2F2FF"), (0.35, "#D2EAFF"), (0.75, "#CBE5FD"), (1, "#BCD8F6")], 0, cy - b, 0, cy + b)}"/>')
    # facet light: the upper-left rim a touch lighter, a thin light line just inside the outer edge
    d.add(f'<g clip-path="{d.clip(outer)}"><path d="{outer}" fill="none" stroke="#F2FAFF" stroke-width="{F(3.2 * s_)}" '
          f'transform="translate({F(1.2 * s_)} {F(1.4 * s_)})" filter="{d.blur(0.5 * s_)}"/></g>')
    ai, bi = 38.0 * s_, 36.4 * s_
    well = hx(ai, bi, -0.9 * s_, 0.9 * s_, r=3.2 * s_)
    rim_in = hx(ai + 2.6 * s_, bi + 2.6 * s_, -0.9 * s_, 0.9 * s_, r=3.6 * s_)
    d.add(f'<path d="{rim_in}" fill="{d.lin([(0, "#F6FCFF"), (0.45, "#DDEEFF"), (0.55, "#6A86C8"), (1, "#4758AC")], cx - ai, 0, cx + ai, 0)}"/>')
    d.add(f'<path d="{well}" fill="{d.lin([(0, "#8A14EE"), (0.25, "#970CF7"), (1, "#920EF4")], 0, cy - bi, 0, cy + bi)}"/>')
    d.add(f'<g clip-path="{d.clip(well)}"><path d="{well}" fill="none" stroke="#6A06C0" stroke-opacity="0.75" stroke-width="{F(4.0 * s_)}" '
          f'transform="translate({F(1.4 * s_)} {F(1.8 * s_)})" filter="{d.blur(1.0 * s_)}"/></g>')
    # the arrow: 57 px tall, head 48 x 26.4, shaft 26.7 wide; sky face, a dark-purple edge (a soft shadow ring)
    ax_, ay0 = cx + 0.9 * s_, cy - 30.2 * s_
    hl, hwid, sw, L = 26.4 * s_, 24.0 * s_, 13.35 * s_, 57.0 * s_
    arrow = [(ax_, ay0), (ax_ + hwid, ay0 + hl), (ax_ + sw, ay0 + hl), (ax_ + sw, ay0 + L), (ax_ - sw, ay0 + L), (ax_ - sw, ay0 + hl),
             (ax_ - hwid, ay0 + hl)]
    ap = poly_path(xf(_round_poly(arrow, 3.6 * s_, 5), deg=rot, ox=cx, oy=cy))
    d.add(f'<path d="{ap}" fill="#3A0888" stroke="#3A0888" stroke-opacity="0.7" stroke-width="{F(4.4 * s_)}" stroke-linejoin="round" '
          f'filter="{d.blur(1.0 * s_)}"/>')
    for k in (3, 2, 1):   # the arrow is a raised slab too: a light side toward the lower left
        d.add(f'<path d="{ap}" fill="#98B2E0" stroke="#5A3AA8" stroke-width="{F(1.2 * s_)}" stroke-linejoin="round" '
              f'transform="translate({F(-0.8 * k * s_)} {F(1.0 * k * s_)})"/>')
    d.add(f'<path d="{ap}" fill="{d.lin([(0, "#DDEFFF"), (0.4, "#CCE7FD"), (1, "#BCD9F7")], 0, ay0, 0, ay0 + L)}"/>')
    d.add(f'<g clip-path="{d.clip(ap)}"><path d="{ap}" fill="none" stroke="#F4FBFF" stroke-opacity="0.9" stroke-width="{F(2.4 * s_)}" '
          f'transform="translate({F(1.0 * s_)} {F(1.3 * s_)})" filter="{d.blur(0.5 * s_)}"/>'
          f'<path d="{ap}" fill="none" stroke="#9DB6E4" stroke-opacity="0.8" stroke-width="{F(2.6 * s_)}" '
          f'transform="translate({F(-0.8 * s_)} {F(-1.6 * s_)})" filter="{d.blur(0.7 * s_)}"/></g>')
    return d.svg()


# Checkered flag (shot 016 Streak Race strip, 30 x 32 pt): a navy pole with a round knob, a waving flag of 4 x 3 navy /
# white squares with a navy outline, leaning right.
def icon_checkered_flag(W=30, H=32):
    """Director round 2, redrawn from 016's Streak Race logo flags (grader A: round 1 was a different flag -- small navy /
    white 4 x 3 checks on a blue ball-topped pole): a short grey-lilac pole with a silver knob, leaning left; a thick
    waving cloth with BIG glossy checks, 3 across x 2 down, cream (#F5EEDD) and slate blue (#4A6696), each cell with a
    light top gloss; a dark navy outline (#10245E) around pole + cloth."""
    d = Doc(W, H)
    rot = -14.0
    piv = (W * 1.5, H * 1.5)
    px0 = 16
    pole = rr(px0, 16, px0 + 8, 92, 4)
    knob = circ(px0 + 4, 13, 6.5)
    fx0, fx1, fy0, fh = px0 + 7, 86, 16, 50
    wave = lambda x: 6.0 * math.sin((x - fx0) / (fx1 - fx0) * 1.6 * math.pi) + (x - fx0) * 0.06   # noqa: E731
    def P(u, v):
        x = fx0 + (fx1 - fx0) * u
        return (x, fy0 + wave(x) + fh * v)
    outline = [P(u / 24, 0) for u in range(25)] + [P(1 - u / 24, 1) for u in range(25)]
    fl = poly_path(outline)
    g = [f'<g transform="rotate({F(rot)} {F(piv[0])} {F(piv[1])}) translate({F(piv[0])} {F(piv[1])}) scale(0.9) '
         f'translate({F(-piv[0])} {F(-piv[1])})">']
    g.append(f'<g transform="translate(3 4)" filter="{d.blur(1.8)}" fill="#032A2D" fill-opacity="0.35">'
             f'<path d="{fl}"/><path d="{pole}"/></g>')
    for p_ in (fl, pole, knob):
        g.append(f'<path d="{p_}" fill="#0E2D2F" stroke="#0E2D2F" stroke-width="5" stroke-linejoin="round"/>')
    g.append(f'<path d="{pole}" fill="{d.lin([(0, "#DDE9E7"), (0.5, "#9FC7C6"), (1, "#6DA09B")], px0, 0, px0 + 8, 0)}"/>')
    g.append(f'<path d="{knob}" fill="{d.rad([(0, "#FFFFFF"), (0.5, "#D0E0DD"), (1, "#7CAEAB")], px0 + 2, 10, 8)}"/>')
    g.append(f'<path d="{fl}" fill="#F5EEDD"/>')
    cells = []
    for i in range(3):
        for j in range(2):
            q = [P(i / 3 + t / 8 / 3, j / 2) for t in range(9)] + [P((i + 1) / 3 - t / 8 / 3, (j + 1) / 2) for t in range(9)]
            cells.append((poly_path(q), (i + j) % 2 == 1, P((i + 0.5) / 3, j / 2 + 0.12)))
    for c, dark, _ in cells:
        if dark:
            g.append(f'<path d="{c}" fill="{d.lin([(0, "#528079"), (1, "#3F5A55")], 0, fy0, 0, fy0 + fh)}"/>')
        else:
            g.append(f'<path d="{c}" fill="{d.lin([(0, "#FFFBF0"), (1, "#E8DEC8")], 0, fy0, 0, fy0 + fh)}"/>')
    # gloss: a soft light band along the top of each row, a shade in the wave's troughs
    clipf = d.clip(fl)
    g.append(f'<g clip-path="{clipf}">'
             f'<path d="{poly_path([P(u / 24, 0.08) for u in range(25)], close=False)}" fill="none" stroke="#FFFFFF" stroke-opacity="0.55" '
             f'stroke-width="5" filter="{d.blur(1.2)}"/>'
             f'<path d="{poly_path([P(u / 24, 0.58) for u in range(25)], close=False)}" fill="none" stroke="#FFFFFF" stroke-opacity="0.35" '
             f'stroke-width="4" filter="{d.blur(1.2)}"/>'
             f'<path d="{poly_path([P(0.42, 0), P(0.42, 1)], close=False)}" fill="none" stroke="#183537" stroke-opacity="0.25" '
             f'stroke-width="9" filter="{d.blur(3)}"/></g>')
    g.append("</g>")
    d.add(*g)
    return d.svg()


# Streak Race score chip (store 6 rows, 64 x 36 pt): the green capsule (a glass cylinder between two gold caps, turned
# -35 deg) over the left end of a rounded plate that darkens the row colour (black 0.28 so one sprite serves the gold /
# silver / bronze rows); the score is LIVE text centred at (45, 18) pt.
def score_chip(W=40, H=44):
    """Director round 2 (grader A: capsule 0.75x, one brown plate for every row): the chip is now the CAPSULE ONLY at the
    size store 6 shows it (~36 x 40 phone pt incl. caps); the number plate behind it is a row-tinted SwiftUI shape (gold
    row dark orange, silver row dark blue, bronze row dark brown-red; the shell draws it). The same capsule is SPEC-ui's
    proposed iconFlagRoll (Streak score chip, Profile "Streak Race Wins")."""
    d = Doc(W, H)
    cx, cy, rot = W * 1.5, H * 1.5 + 1, -30
    k = 1.32
    g = [f'<g transform="rotate({rot} {F(cx)} {F(cy)}) translate({F(cx)} {F(cy)}) scale({F(k)}) translate({F(-cx)} {F(-cy)})">']
    g.append(f'<path d="{rr(cx - 27, cy - 34, cx + 27, cy + 36, 14)}" fill="#3D2816" fill-opacity="0.4" transform="translate(3 4)" filter="{d.blur(2)}"/>')
    glass = rr(cx - 23, cy - 20, cx + 23, cy + 22, 6)
    g.append(f'<path d="{glass}" fill="{d.lin([(0, "#9F5617"), (0.22, "#EC9732"), (0.42, "#F4DEA3"), (0.58, "#F3A83F"), (1, "#B1631A")], cx - 23, 0, cx + 23, 0)}" '
             f'stroke="#7B3C00" stroke-width="2"/>')
    for y0, y1 in ((cy - 33, cy - 17), (cy + 19, cy + 35)):
        cap = rr(cx - 27, y0, cx + 27, y1, 8)
        g.append(f'<path d="{cap}" fill="{d.lin([(0, "#C87404"), (0.25, "#F7B614"), (0.5, "#FFE680"), (0.7, "#FBC52A"), (1, "#D08006")], cx - 27, 0, cx + 27, 0)}" '
                 f'stroke="#985317" stroke-width="2.2"/>')
    g.append(f'<path d="{rr(cx - 11, cy - 41, cx + 11, cy - 32, 4)}" fill="{d.lin([(0, "#D08006"), (0.5, "#FFE680"), (1, "#D08006")], cx - 11, 0, cx + 11, 0)}" '
             f'stroke="#985317" stroke-width="2"/>')
    g.append("</g>")
    d.add(*g)
    return d.svg()


# Sunburst (shot 023 Claw reward card, 120 x 80 pt): 16 soft white rays from the centre, fading out radially, over the
# cream card (alpha only: the card colour shows through).
def sunburst_rays(W=190, H=86):
    """Polish lane r3 (grader A: ours faded out at ~0.65 of the frame; 023's rays run to the card's edges). Re-measured
    on 023: the rays fill the whole cream reward field (190 x 85 pt at x 147.5-337.5, y 455-540; corners r ~22) from a
    centre at (0.5 W, 0.34 H) (the prize): ~22 white wedges, strong near the prize and still ~0.35 at the field's edges, with a soft
    white glow at the centre. White alpha only (the cream shows through); clipped to the field's rounded rect, so the
    shell draws it 1:1 on the field (147.5, 455, 190, 85 in 023)."""
    d = Doc(W, H)
    cx, cy = W * 1.5, H * 0.34 * 3
    R = math.hypot(W * 1.5, H * 3) * 1.1
    n = 22
    wedges = []
    for k in range(n):
        a0 = 2 * math.pi * k / n
        a1 = a0 + 2 * math.pi / n * 0.5
        wedges.append(f"M{F(cx)} {F(cy)}L{F(cx + R * math.cos(a0))} {F(cy + R * math.sin(a0))}L{F(cx + R * math.cos(a1))} {F(cy + R * math.sin(a1))}Z")
    fill = d.rad([(0, "#FFFFFF", 0.95), (0.18, "#FFFFFF", 0.66), (0.45, "#FFFFFF", 0.42), (1, "#FFFFFF", 0.24)], cx, cy, R * 0.75)
    field = rr(1.5, 1.5, W * 3 - 1.5, H * 3 - 1.5, 22 * 3)
    d.add(f'<g clip-path="{d.clip(field)}"><g filter="{d.blur(2.2)}">' + "".join(f'<path d="{w}" fill="{fill}"/>' for w in wedges) + "</g>"
          f'<path d="{ell(cx, cy + 6 * 3, 44 * 3, 28 * 3)}" fill="#FFFFFF" fill-opacity="0.6" filter="{d.blur(16)}"/></g>')
    return d.svg()


# Sky Jump prize sign (shot 069, 92 x 64 pt): a green arrow board pointing right, turned -14 deg, a gold rim with a dark
# outline, a coin on its left part; the text ("PRIZE" + amount) is LIVE text centred at (54, 25) pt; a green post down to
# the lower left.
def prize_sign(W=92, H=64):
    d = Doc(W, H)
    rot = -17
    cx, cy = 132, 78
    post = rr(106, 96, 122, 188, 7)
    d.add(f'<path d="{post}" fill="{d.lin([(0, "#835023"), (0.4, "#BC8549"), (1, "#764006")], 106, 0, 122, 0)}" transform="rotate(12 114 140)" '
          f'stroke="#4C290A" stroke-width="2"/>')
    pts = [(14, 40), (182, 40), (182, 14), (262, 78), (182, 142), (182, 116), (14, 116)]
    board = poly_path(xf(_round_poly(pts, 12, 6), deg=rot, ox=cx, oy=cy))
    face = poly_path(xf(_round_poly([(24, 50), (190, 50), (190, 34), (246, 78), (190, 122), (190, 106), (24, 106)], 7, 6), deg=rot, ox=cx, oy=cy))
    d.add(f'<path d="{board}" fill="#000000" fill-opacity="0.35" transform="translate(2 5)" filter="{d.blur(2.5)}"/>')
    d.add(f'<path d="{board}" fill="#894A13" stroke="#894A13" stroke-width="5" stroke-linejoin="round"/>')
    d.add(f'<path d="{board}" fill="{d.lin([(0, "#FFE060"), (0.4, "#FFBE1A"), (1, "#F09A08")], 0, 10, 0, 150)}"/>')
    d.add(f'<path d="{face}" fill="{d.lin([(0, "#D09752"), (0.5, "#B98143"), (1, "#A46C35")], 0, 30, 0, 130)}"/>')
    d.add(f'<g clip-path="{d.clip(face)}"><path d="{face}" fill="none" stroke="#835023" stroke-opacity="0.8" stroke-width="7" '
          f'transform="translate(0 3)" filter="{d.blur(2)}"/></g>')
    g, (w, h), _ = embed(icon_coin_r2(30, 30, shadow=False), 0, 0, "cn")   # the round-2 coin (this sign is unchanged)
    k = 0.72
    ccx, ccy = xf([(58, 80)], deg=rot, ox=cx, oy=cy)[0]
    d.add(f'<g transform="translate({F(ccx - w * k / 2)} {F(ccy - h * k / 2)}) scale({k})">{g}</g>')
    return d.svg()


# Edit-profile pencil (owner V2 Profile t 70 s: the orange edit disc at the avatar's corner): an orange disc with a dark
# outline and a white pencil (tip down-left).
def refit(svg, w_pt, h_pt):
    """Show a drawing authored for one frame in another: the SVG keeps its viewBox (the drawing's own px) and gets a new
    width/height, so WebKit scales it uniformly and centres it (preserveAspectRatio xMidYMid meet)."""
    head = re.search(r"<svg[^>]*>", svg).group(0)
    new = re.sub(r'width="[^"]+"', f'width="{F(w_pt)}"', head, count=1)
    new = re.sub(r'height="[^"]+"', f'height="{F(h_pt)}"', new, count=1)
    return svg.replace(head, new, 1)


def icon_pencil(W=20, H=20):
    d = Doc(W, H)
    cx, cy, R = W * 1.5, H * 1.5 - 0.5, 26
    d.add(f'<path d="{circ(cx, cy + 1.5, R)}" fill="#000000" fill-opacity="0.35" filter="{d.blur(1.2)}"/>')
    d.add(f'<path d="{circ(cx, cy, R)}" fill="#834008"/>')
    d.add(f'<path d="{circ(cx, cy, R - 2.2)}" fill="{d.lin([(0, "#FFC04A"), (0.5, "#FF9A1A"), (1, "#EE7A00")], 0, cy - R, 0, cy + R)}"/>')
    body = [(cx - 12, cy + 12), (cx - 15, cy + 15), (cx - 13.5, cy + 6.5), (cx + 8, cy - 15), (cx + 15, cy - 8), (cx - 6.5, cy + 13.5)]
    d.add(*toon([("f", poly_path(_round_poly(body, 1.6, 4)))], "#FFFFFF", "#723605", 1.8, drop=1.6))
    d.add(f'<path d="M{F(cx + 4)} {F(cy - 11)}L{F(cx + 11)} {F(cy - 4)}" stroke="#723605" stroke-width="1.6"/>')
    return d.svg()


# Info-overlay pointer (shot 025 Claw info, 46 x 50 pt): a fat yellow arrow curving from the upper left down to the right,
# its big head pointing down-right; yellow #FFE11A -> #FFC400, orange outline #E8620A ~2 pt.
def pointer_arrow_yellow(W=46, H=50):
    d = Doc(W, H)
    shaft = "M24 30 C50 28 72 44 86 66"
    head = [(56, 84), (126, 140), (124, 48)]
    parts = [("s", shaft, 34), ("f", poly_path(_round_poly(head, 8, 6)))]
    fill = d.lin([(0, "#FFE84A"), (0.5, "#FFD21A"), (1, "#FFC000")], 20, 20, 120, 130)
    d.add('<g transform="translate(69 75) scale(0.9) translate(-69 -75)">')
    d.add(f'<g transform="translate(1 3)" filter="{d.blur(2)}" opacity="0.4">' + "".join(toon(parts, "#000000", "#000000", 5)) + "</g>")
    d.add(*toon(parts, fill, "#E0600A", 6.0))
    d.add(f'<path d="M26 22 C48 20 66 30 78 44" fill="none" stroke="#FFF7B0" stroke-opacity="0.9" stroke-width="5" stroke-linecap="round" '
          f'filter="{d.blur(1.2)}"/>')
    d.add("</g>")
    return d.svg()


# Info maze tile (shot 025 Claw info, 118 x 118 pt): a pale tile (#EEF5FF) in a glossy blue rim, holding four blue
# path-arrows in the board's own grammar (straight runs, right-angle turns, triangle heads). The layout is ours.
def info_path_icon(W=118, H=118):
    d = Doc(W, H)
    x0, y0, x1, y1 = 5, 4, W * 3 - 5, H * 3 - 10
    tile = rr(x0, y0, x1, y1, 40)
    face = rr(x0 + 11, y0 + 11, x1 - 11, y1 - 14, 28)
    d.add(f'<path d="{tile}" fill="#000000" fill-opacity="0.4" transform="translate(0 7)" filter="{d.blur(4)}"/>')
    d.add(f'<path d="{tile}" fill="{d.lin([(0, "#009F93"), (0.5, "#00847E"), (1, "#006762")], 0, y0, 0, y1)}" stroke="#174F4E" stroke-width="3"/>')
    d.add(f'<path d="{face}" fill="{d.lin([(0, "#FFFFFF"), (0.7, "#EEF6F4"), (1, "#D5E6E2")], 0, y0, 0, y1)}"/>')
    d.add(f'<g clip-path="{d.clip(face)}"><path d="{face}" fill="none" stroke="#759992" stroke-opacity="0.55" stroke-width="14" '
          f'transform="translate(0 -6)" filter="{d.blur(6)}"/></g>')
    U = lambda u: x0 + 11 + (x1 - x0 - 22) * u
    V = lambda v: y0 + 11 + (y1 - y0 - 25) * v
    sw = 0.095 * (x1 - x0)
    hl, hw = 0.18 * (x1 - x0), 0.2 * (x1 - x0)
    paths = [  # (points, head direction)
        ([(0.14, 0.46), (0.14, 0.12), (0.50, 0.12), (0.50, 0.46)], "d"),
        ([(0.14, 0.88), (0.14, 0.66), (0.32, 0.66), (0.32, 0.30)], "u"),
        ([(0.30, 0.86), (0.66, 0.86)], "r"),
        ([(0.82, 0.12), (0.82, 0.86)], "d"),
    ]
    blue = d.lin([(0, "#009D92"), (1, "#007B77")], 0, y0, 0, y1)
    for pts, hd in paths:
        P = [(U(u), V(v)) for u, v in pts]
        ex, ey = P[-1]
        dx, dy = {"d": (0, 1), "u": (0, -1), "r": (1, 0)}[hd]
        base = (ex - dx * hl * 0.55, ey - dy * hl * 0.55)
        tip = (base[0] + dx * hl, base[1] + dy * hl)
        l = (base[0] + dy * hw / 2, base[1] - dx * hw / 2)
        r_ = (base[0] - dy * hw / 2, base[1] + dx * hw / 2)
        shaft = poly_path(P[:-1] + [base], close=False)
        headp = poly_path(_round_poly([l, tip, r_], 6, 5))
        d.add(f'<g transform="translate(0 5)" opacity="0.25" filter="{d.blur(2)}"><path d="{shaft}" fill="none" stroke="#003F44" '
              f'stroke-width="{F(sw)}" stroke-linecap="round" stroke-linejoin="round"/><path d="{headp}" fill="#003F44"/></g>')
        d.add(f'<path d="{shaft}" fill="none" stroke="#006560" stroke-width="{F(sw + 4)}" stroke-linecap="round" stroke-linejoin="round"/>'
              f'<path d="{headp}" fill="#006560" stroke="#006560" stroke-width="4" stroke-linejoin="round"/>')
        d.add(f'<path d="{shaft}" fill="none" stroke="{blue}" stroke-width="{F(sw)}" stroke-linecap="round" stroke-linejoin="round"/>'
              f'<path d="{headp}" fill="{blue}"/>')
        d.add(f'<path d="{shaft}" fill="none" stroke="#69CCC7" stroke-opacity="0.7" stroke-width="{F(sw * 0.22)}" stroke-linecap="round" '
              f'stroke-linejoin="round" transform="translate(-3 -3)"/>')
    return d.svg()


# Profile stat icons (owner V2 Profile t 70 s "General Stats"): a red/white target seen from the front-left with a dart
# (purple fletching, gold shaft) in the bullseye; a gold medal on a red/white ribbon with an embossed "1" (our font).
def stat_first_try(W=34, H=34):
    d = Doc(W, H)
    cx, cy = 42, 60
    rx, ry = 36, 34.5
    d.add(f'<path d="{ell(cx + 1, cy + 6, rx, ry)}" fill="#57150C" fill-opacity="0.35" filter="{d.blur(2)}"/>')
    # director r2 (meta-002): a THICK glossy red side under the face (the target is a disc seen from the front-right)
    for k in range(6, 0, -1):
        d.add(f'<path d="{ell(cx + 0.9 * k, cy + 0.9 * k, rx, ry)}" fill="{"#85160D" if k > 3 else "#AA2316"}"/>')
    for i, (f, col) in enumerate(((1.0, "#D74030"), (0.72, "#FFFFFF"), (0.46, "#D74030"), (0.2, "#FFFFFF"))):
        d.add(f'<path d="{ell(cx, cy, rx * f, ry * f)}" fill="{col}"/>')
    d.add(f'<path d="{ell(cx, cy, 5, 5)}" fill="#D74030"/>')
    d.add(f'<path d="{ell(cx, cy, rx, ry)}" fill="none" stroke="#95190E" stroke-width="2"/>')
    d.add(f'<path d="{arc_path(cx, cy, rx - 4, 195, 265)}" fill="none" stroke="#F7BCB2" stroke-opacity="0.9" stroke-width="3.6" stroke-linecap="round"/>')
    d.add(f'<path d="{arc_path(cx, cy, rx * 0.46 - 3, 200, 250)}" fill="none" stroke="#F3A193" stroke-opacity="0.8" stroke-width="2.4" stroke-linecap="round"/>')
    # dart from the upper right into the centre
    d.add(f'<path d="M{F(cx + 2)} {F(cy - 2)}L{F(cx + 34)} {F(cy - 34)}" stroke="#7D4815" stroke-width="7" stroke-linecap="round"/>')
    d.add(f'<path d="M{F(cx + 2)} {F(cy - 2)}L{F(cx + 34)} {F(cy - 34)}" stroke="#F7B81A" stroke-width="4.4" stroke-linecap="round"/>')
    fl = [(cx + 30, cy - 30), (cx + 47, cy - 44), (cx + 53, cy - 28), (cx + 42, cy - 24)]
    fl2 = [(cx + 30, cy - 30), (cx + 45, cy - 51), (cx + 29, cy - 50), (cx + 26, cy - 38)]
    d.add(*toon([("f", poly_path(_round_poly(fl, 3, 4))), ("f", poly_path(_round_poly(fl2, 3, 4)))],
                d.lin([(0, "#EE5B98"), (1, "#AC1F6B")], 0, cy - 58, 0, cy - 26), "#6A173F", 1.6))
    return d.svg()


def stat_weekly_wins(W=36, H=38):
    d = Doc(W, H)
    cx = W * 1.5
    # ribbon: red/white/red stripes from the top bar down behind the medal
    # director r2 (meta-002): the ribbon is as wide as the medal, the gold bar wider still
    rib = poly_path([(cx - 26, 8), (cx + 26, 8), (cx + 22, 48), (cx - 22, 48)])
    d.add(f'<path d="{rib}" fill="#BC3021" stroke="#76150C" stroke-width="2" stroke-linejoin="round"/>')
    d.add(f'<path d="{poly_path([(cx - 8, 8), (cx + 8, 8), (cx + 7, 47), (cx - 7, 47)])}" fill="#FFFFFF"/>')
    bar = rr(cx - 30, 2, cx + 30, 14, 5)
    d.add(f'<path d="{bar}" fill="{d.lin([(0, "#FFE060"), (1, "#E8A00A")], 0, 4, 0, 15)}" stroke="#9A5202" stroke-width="2"/>')
    g, (w, h), _ = embed(icon_coin_r2(30, 30, shadow=True), 0, 0, "md")    # the round-2 coin (the medal is unchanged)
    k = 0.9
    d.add(f'<g transform="translate({F(cx - w * k / 2)} {F(31)}) scale({k})">{g}</g>')
    # hide the coin's star under a medal face disc carrying our font's "1" (embossed)
    ccx, ccy = cx, 31 + (45 - 1.8) * k
    d.add(f'<path d="{circ(ccx, ccy + 0.5, 21)}" fill="{d.lin([(0, "#F4B400"), (1, "#E89A00")], 0, ccy - 21, 0, ccy + 21)}"/>')
    G = _glyphs()["glyphs"].get("1") or _glyphs()["glyphs"]["A"]
    kk = 29 / 720.0
    bx0, bx1 = G["bounds"][0], G["bounds"][2]
    tr = f"translate({F(ccx)} {F(ccy + 14.5)}) scale({F(kk)} {F(-kk)}) translate({F(-(bx0 + bx1) / 2)} 0)"
    d.add(f'<path d="{G["d"]}" transform="{tr}" fill="#C46200" stroke="#C46200" stroke-width="40" stroke-linejoin="round"/>')
    d.add(f'<g transform="translate(-1 -1.4)"><path d="{G["d"]}" transform="{tr}" fill="#FFE34A" stroke="#FFE34A" stroke-width="16" '
          f'stroke-linejoin="round"/></g>')
    return d.svg()


# ====================================================================================== FX sprites
# Trail star (store 1 / 5 rainbow trails, 12 x 12 pt): a white rounded 5-point star (the engine tints it per particle).
def board_trail_star(W=12, H=12):
    d = Doc(W, H)
    c = W * 1.5
    d.add(f'<path d="{star(c, c + 1.2, 15.5, 7.6, round_=3.2)}" fill="#FFFFFF"/>')
    return d.svg()


# Twinkle (shot 020 win, unlock cards: 4-point white sparkles with a warm glow), 16 x 16 pt.
def sparkle_twinkle(W=16, H=16):
    d = Doc(W, H)
    c = W * 1.5
    pts = []
    for k in range(8):
        a = math.radians(-90 + 45 * k)
        r = 21 if k % 2 == 0 else 4.2
        pts.append((c + r * math.cos(a), c + r * math.sin(a)))
    sp = poly_path(_round_poly(pts, 1.6, 4))
    d.add(f'<path d="{circ(c, c, 12)}" fill="#FFF3B0" fill-opacity="0.55" filter="{d.blur(4)}"/>')
    d.add(f'<path d="{sp}" fill="#FFF6C8" filter="{d.blur(1.2)}"/>')
    d.add(f'<path d="{sp}" fill="#FFFFFF"/>')
    d.add(f'<path d="{circ(c, c, 3.4)}" fill="#FFFFFF"/>')
    return d.svg()


# Shatter fragments: 6 shards in a 3 x 2 grid of 16 pt cells (cell i = column i % 3, row i // 3), each centred in its
# cell so the FX lane can cut the sheet or emit it as one particle atlas.
def _shards(d, specs):
    for i, (pts, fill, edge, hi) in enumerate(specs):
        ox, oy = (i % 3) * 48 + 24, (i // 3) * 48 + 48      # cell centres (8 + 16 c, 16 + 16 r) pt
        P = poly_path(_round_poly([(ox + x, oy + y) for x, y in pts], 1.8, 3))
        d.add(f'<path d="{P}" fill="#000000" fill-opacity="0.3" transform="translate(1 2)" filter="{d.blur(1)}"/>')
        d.add(f'<path d="{P}" fill="{fill}" stroke="{edge}" stroke-width="1.8" stroke-linejoin="round"/>')
        if hi:
            d.add(f'<path d="M{F(ox + pts[0][0] * 0.7)} {F(oy + pts[0][1] * 0.7)}L{F(ox + pts[1][0] * 0.7)} {F(oy + pts[1][1] * 0.7)}" '
                  f'stroke="{hi}" stroke-opacity="0.9" stroke-width="2.4" stroke-linecap="round"/>')


def door_shards(W=48, H=48):
    """The door's colours (STYLE §A.2): orange frame #FFA40D / #CD6D07, blue slat #5FA6F2 / #2B57A8, purple #AE3DD3."""
    d = Doc(W, H)
    orange = d.lin([(0, "#FFC84A"), (0.5, "#FFA40D"), (1, "#E0880A")], 0, 0, 0, 48)
    blue = d.lin([(0, "#A8E2FE"), (0.2, "#5FA6F2"), (1, "#3F7EC8")], 0, 48, 0, 96)
    purple = d.lin([(0, "#CE60F1"), (1, "#8A2CB8")], 0, 0, 0, 96)
    _shards(d, [([(-14, -9), (12, -13), (15, 4), (-6, 12), (-15, 3)], orange, "#9A5006", "#FFE08A"),
                ([(-10, -14), (9, -10), (12, 11), (-12, 13)], blue, "#23519C", "#D0F0FF"),
                ([(-13, -6), (0, -14), (14, -4), (6, 12), (-10, 9)], purple, "#5A1A80", "#F0B0FF"),
                ([(-15, -4), (8, -12), (13, 8), (-9, 12)], blue, "#23519C", "#D0F0FF"),
                ([(-9, -13), (13, -9), (7, 13), (-13, 6)], orange, "#9A5006", "#FFE08A"),
                ([(-12, -11), (12, -7), (0, 14)], purple, "#5A1A80", "#F0B0FF")])
    return d.svg()


def pipe_shards(W=48, H=48):
    """Cyan glass (the tube's colours, STYLE §A.2 pipe): face #7DDAFA / #31B1E7, rim #2291D6, highlight #E6FBFF."""
    d = Doc(W, H)
    glass = d.lin([(0, "#BDEFFF"), (0.35, "#7DDAFA"), (1, "#31B1E7")], 0, 0, 96, 96)
    _shards(d, [([(-13, -12), (14, -6), (4, 13), (-12, 5)], glass, "#2291D6", "#FFFFFF"),
                ([(-6, -15), (10, -6), (8, 14), (-11, 6)], glass, "#2291D6", "#FFFFFF"),
                ([(-14, -3), (4, -13), (14, 6), (-5, 12)], glass, "#2291D6", "#FFFFFF"),
                ([(-12, -12), (13, -10), (-2, 14)], glass, "#2291D6", "#FFFFFF"),
                ([(-15, 2), (-2, -13), (14, -5), (6, 12)], glass, "#2291D6", "#FFFFFF"),
                ([(-9, -12), (12, -12), (9, 10), (-13, 10)], glass, "#2291D6", "#FFFFFF")])
    return d.svg()


# ====================================================================================== elevator (unconfirmed)
# NOT on the phone (v552): the owner's V2 video t 1182.5 s ("Elevator! / Unlocked! / Clear all arrows on the ELEVATOR to
# activate it!", L31). Two lavender sliding-door panels side by side (158 x 104 pt on the card), a thin dark seam between
# them, soft lighter diagonal stripes, each with a darker inset window carrying two small studs; rounded outer corners.
# Drawn at 0.73 of the card size to sit in the 120 x 110 pt frame (the app shows it ~1.37x).
def unlock_elevator(W=164, H=112):
    """Polish lane r3 (grader A: stripes a little strong; at game size the lavender tint and dark outline also read off).
    Re-measured on V2 t 1182.5 s at 1:1: the two sliding panels are ICY BLUE-GREY, 159.5 x 105 pt (x 117-276.5,
    y 363.5-468.5), corner r ~14; face #CBD9ED -> #C4D0E8, a light rim #DFE6F6 / #DBE0F4, a thin grey edge #636773;
    faint diagonal stripes (#C2CEE4 vs #CDDAED, period ~15 pt); a 1.5 pt seam #6E7A92 with light lines #ABB7CF beside it;
    each panel's window 37.5 x 62 pt (21 pt in from the outer edge / 21.5 from the top), flat #A1B1CB, a dark edge #8796AB
    inside a light bevel line #D3DFF7, two small studs. This frame (164 x 112) holds the art at 1:1; the shell's ink rect
    for it: (117, 363.5, 159.5, 105)."""
    d = Doc(W, H)
    k = 3.0
    x0, y0 = 2.25 * k, 2.0 * k
    x1, y1 = x0 + 159.5 * k, y0 + 105.0 * k
    r = 14.0 * k
    body = rr(x0, y0, x1, y1, r)
    d.add(f'<path d="{body}" fill="#000000" fill-opacity="0.45" transform="translate(0 {F(2.2 * k)})" filter="{d.blur(1.8 * k)}"/>')
    d.add(f'<path d="{body}" fill="#7A8398"/>')
    inner = rr(x0 + 0.7 * k, y0 + 0.7 * k, x1 - 0.7 * k, y1 - 0.7 * k, r - 0.7 * k)
    d.add(f'<path d="{inner}" fill="{d.lin([(0, "#D2DDF1"), (0.3, "#CBD9ED"), (1, "#C3CFE7")], 0, y0, 0, y1)}"/>')
    per = 20.0 * k
    blr = d.blur(0.8 * k)
    stripes = "".join(f'<path d="M{F(x0 - 110 * k + i * per)} {F(y0)}L{F(x0 + i * per)} {F(y1)}" stroke="#D8E3F4" stroke-opacity="0.95" '
                      f'stroke-width="{F(9.5 * k)}" filter="{blr}"/>' for i in range(0, 16))
    d.add(f'<g clip-path="{d.clip(inner)}">{stripes}'
          f'<path d="{inner}" fill="none" stroke="#E4EBF8" stroke-width="{F(2.2 * k)}"/></g>')
    mx = (x0 + x1) / 2
    d.add(f'<path d="M{F(mx)} {F(y0 + 1.2 * k)}L{F(mx)} {F(y1 - 1.2 * k)}" stroke="#ABB7CF" stroke-width="{F(3.6 * k)}"/>'
          f'<path d="M{F(mx)} {F(y0 + 1.0 * k)}L{F(mx)} {F(y1 - 1.0 * k)}" stroke="#6E7A92" stroke-width="{F(1.5 * k)}"/>')
    for wx in (x0 + 21.0 * k, x0 + 101.0 * k):
        wy = y0 + 21.5 * k
        ww, wh = 37.5 * k, 62.0 * k
        d.add(f'<path d="{rr(wx - 1.0 * k, wy - 1.0 * k, wx + ww + 1.0 * k, wy + wh + 1.0 * k, 5.0 * k)}" fill="#D6E2F6"/>')
        win = rr(wx, wy, wx + ww, wy + wh, 4.0 * k)
        d.add(f'<path d="{win}" fill="#8796AB"/>')
        d.add(f'<path d="{rr(wx + 1.0 * k, wy + 1.0 * k, wx + ww - 1.0 * k, wy + wh - 1.0 * k, 3.2 * k)}" '
              f'fill="{d.lin([(0, "#98A7C1"), (0.12, "#A1B1CB"), (1, "#A2B2CC")], 0, wy, 0, wy + wh)}"/>')
        for fy in (0.29, 0.71):
            cxx, cyy = wx + ww / 2, wy + wh * fy
            d.add(f'<path d="{circ(cxx, cyy, 2.3 * k)}" fill="#8E9BB3"/><path d="{circ(cxx, cyy, 1.7 * k)}" fill="#B6C2D8"/>'
                  f'<path d="{circ(cxx - 0.5 * k, cyy - 0.5 * k, 0.7 * k)}" fill="#E4EAF6"/>')
    return d.svg()


# ====================================================================================== cases
CASES = {
    "iconCoin": icon_coin,
    "iconPlusGreen": icon_plus_green,                         # polish r3: 24 pt frame (the shell's 23.5 pt rect), 002 plus
    "iconStopwatch": icon_stopwatch,
    "iconStopwatchSmall": lambda: icon_stopwatch(26, 28, small=True),   # polish r3: 204 chip watch is 22.7 x 26 pt of ink
    "heartHUDLost": heart_hud_lost,
    "heartHUDHalves": heart_hud_halves,
    "heartLives": heart_lives,
    "glyphSound": glyph_sound,
    "glyphHaptic": lambda: glyph_haptic(34, 33),             # r2: the measured ink is 32.4 x 31.1 pt (007)
    "glyphSoundWhite": lambda: glyph_sound(42, 38, "white"), # r2: Settings (meta-029) white-on-green set
    "glyphHapticWhite": lambda: glyph_haptic(42, 38, "white"),
    "glyphMusic": lambda: glyph_music(38, 36, "white"),      # r2: meta-029 white on green (only on Settings)
    "glyphGear": glyph_gear,
    "glyphBell": lambda: glyph_bell(30, 36),                 # r2: meta-029 white/ice bell, navy outline
    "unlockIconPipe": unlock_pipe,
    "unlockIconLinked": unlock_linked,
    "unlockIconBox": unlock_box,                             # r2: the phone Box card (134); unlockIconCurtain superseded
    "unlockIconCurtain": unlock_curtain_legacy,              # NOT SHIPPED (round 1's crate icon, kept for provenance)
    "rankBadgePlain": lambda: rank_badge("plain"),           # NOT SHIPPED (ranks 4+ are live digits)
    "unlockIconDoor": unlock_door,
    "unlockIconElevator": unlock_elevator,
    "tutorialHand": lambda: tutorial_hand(102, 136),         # r2: hand ~72 x 99 pt + V1's shadow room
    "rankBadgeGold": lambda: rank_badge("gold"),
    "rankBadgeSilver": lambda: rank_badge("silver"),
    "rankBadgeBronze": lambda: rank_badge("bronze"),
    "logoArrowOut": logo_arrow_out,
    "logoSignPurple": lambda i_="logoSignPurple": logo_part_svg(i_),   # the win logo's animation parts (logo_part_svg)
    "logoSignBlue": lambda i_="logoSignBlue": logo_part_svg(i_),
    "logoLetterA": lambda i_="logoLetterA": logo_part_svg(i_),
    "logoLetterR1": lambda i_="logoLetterR1": logo_part_svg(i_),
    "logoLetterR2": lambda i_="logoLetterR2": logo_part_svg(i_),
    "logoLetterO": lambda i_="logoLetterO": logo_part_svg(i_),
    "logoLetterW": lambda i_="logoLetterW": logo_part_svg(i_),
    "logoOut": lambda i_="logoOut": logo_part_svg(i_),
    "logoPegs": lambda i_="logoPegs": logo_part_svg(i_),             # LOGO-ART-2: pegs, OUT! glyphs, bend variants
    "logoOutO": lambda i_="logoOutO": logo_part_svg(i_),
    "logoOutU": lambda i_="logoOutU": logo_part_svg(i_),
    "logoOutT": lambda i_="logoOutT": logo_part_svg(i_),
    "logoOutBang": lambda i_="logoOutBang": logo_part_svg(i_),
    "logoSignPurpleBend25": lambda i_="logoSignPurpleBend25": logo_part_svg(i_),
    "logoSignPurpleBend50": lambda i_="logoSignPurpleBend50": logo_part_svg(i_),
    "logoSignPurpleBend75": lambda i_="logoSignPurpleBend75": logo_part_svg(i_),
    "logoSignPurpleBend100": lambda i_="logoSignPurpleBend100": logo_part_svg(i_),
    "logoLetterAExt": lambda i_="logoLetterAExt": logo_part_svg(i_),   # LOGO-ART-3: every letter / glyph as Ext + Face (a pair)
    "logoLetterAFace": lambda i_="logoLetterAFace": logo_part_svg(i_),
    "logoLetterR1Ext": lambda i_="logoLetterR1Ext": logo_part_svg(i_),
    "logoLetterR1Face": lambda i_="logoLetterR1Face": logo_part_svg(i_),
    "logoLetterR2Ext": lambda i_="logoLetterR2Ext": logo_part_svg(i_),
    "logoLetterR2Face": lambda i_="logoLetterR2Face": logo_part_svg(i_),
    "logoLetterOExt": lambda i_="logoLetterOExt": logo_part_svg(i_),
    "logoLetterOFace": lambda i_="logoLetterOFace": logo_part_svg(i_),
    "logoLetterWExt": lambda i_="logoLetterWExt": logo_part_svg(i_),
    "logoLetterWFace": lambda i_="logoLetterWFace": logo_part_svg(i_),
    "logoOutOExt": lambda i_="logoOutOExt": logo_part_svg(i_),
    "logoOutOFace": lambda i_="logoOutOFace": logo_part_svg(i_),
    "logoOutUExt": lambda i_="logoOutUExt": logo_part_svg(i_),
    "logoOutUFace": lambda i_="logoOutUFace": logo_part_svg(i_),
    "logoOutTExt": lambda i_="logoOutTExt": logo_part_svg(i_),
    "logoOutTFace": lambda i_="logoOutTFace": logo_part_svg(i_),
    "logoOutBangExt": lambda i_="logoOutBangExt": logo_part_svg(i_),
    "logoOutBangFace": lambda i_="logoOutBangFace": logo_part_svg(i_),
    "logoLetterAFlat": lambda i_="logoLetterAFlat": logo_part_svg(i_),   # LOGO-ART-4: a letter's flat sprite while it fades
    "logoLetterR1Flat": lambda i_="logoLetterR1Flat": logo_part_svg(i_),
    "logoLetterR2Flat": lambda i_="logoLetterR2Flat": logo_part_svg(i_),
    "logoLetterOFlat": lambda i_="logoLetterOFlat": logo_part_svg(i_),
    "logoLetterWFlat": lambda i_="logoLetterWFlat": logo_part_svg(i_),
    "heartInfiniteSmall": heart_infinite_small,
    "iconHexArrow": icon_hex_arrow,
    "iconCheckeredFlag": icon_checkered_flag,
    "scoreChip": score_chip,                                 # r2: capsule only, 40 x 44 (plate = SwiftUI)
    "sunburstRays": sunburst_rays,
    "prizeSign": prize_sign,
    "iconPencil": lambda: refit(icon_pencil(), 32, 32),      # r2: meta-002 disc ~32 pt (0.6x before)
    "pointerArrowYellow": pointer_arrow_yellow,
    "infoPathIcon": info_path_icon,
    "statFirstTryIcon": lambda: refit(stat_first_try(), 56, 54),     # r2: meta-002 target ~51 x 50 pt of ink
    "statWeeklyWinsIcon": lambda: refit(stat_weekly_wins(), 48, 51),  # r2: meta-002 medal ~38 x 51 pt, coin ~36 pt
    "boardTrailStar": board_trail_star,
    "sparkleTwinkle": sparkle_twinkle,
    "doorShards": door_shards,
    "pipeShards": pipe_shards,
}


if __name__ == "__main__":
    out = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(SRC))), "build", "ui-art", "svgsrc")
    os.makedirs(out, exist_ok=True)
    for n in sys.argv[1:] or list(CASES):
        r = CASES[n]()
        svg = r[0] if isinstance(r, tuple) else r
        open(os.path.join(out, f"{n}.svg"), "w", encoding="utf-8").write(svg)
        print("wrote", os.path.join(out, f"{n}.svg"))
