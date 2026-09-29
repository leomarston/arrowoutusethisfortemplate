#!/usr/bin/env python3
"""SVG variants of the route-C candidates (art spike): the pink tape obstacle, the glossy arrow, the worker.
Writes art/ui/src/<case>.svg; `svg.py <case>` rasterises to art/ui/out/<case>@3x.png (copied to
build/ui-art/svgroute/ for the comparisons when the case lost to the 3D route).

    ~/.venvs/mf3d/bin/python art/ui/src/gen_props.py [case ...]

Units @3x px, y down. Colours measured on runner shot 003 (tape), the store icon and home shot 002 (arrow, worker);
see art/STYLE.md §C. Shapes are primitives, never traced.
"""
from __future__ import annotations

import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from gen_chrome import blur, lin, rad  # noqa: E402
from shapes import fmt, poly_path, svg_doc  # noqa: E402


def rrect_path(cx, cy, w, h, r, deg=0.0):
    """A rounded rectangle centred at (cx, cy), rotated by deg, as a path (arcs sampled)."""
    pts = []
    hw, hh = w / 2 - r, h / 2 - r
    for (sx, sy, a0) in ((1, 1, 0), (-1, 1, 90), (-1, -1, 180), (1, -1, 270)):
        for k in range(9):
            a = math.radians(a0 + k * 90 / 8)
            pts.append((sx * hw + r * math.cos(a), sy * hh + r * math.sin(a)))
    t = math.radians(deg)
    c, s = math.cos(t), math.sin(t)
    return poly_path([(cx + c * x - s * y, cy + s * x + c * y) for x, y in pts])


# ------------------------------------------------------------------ the pink tape (4 lanes, vertical)
# 003: body 53 x 186 px; base #D72169 (edges #BF1C5D), two straps corner to corner (#FF3B84), each strap bright
# near its top end (#FF93B4 at ~12 % of its length), a light streak along its upper-left edge (#FF7DA7), darker at the
# bottom end (#D42069) with a dark rim (#BC215B); strap-on-base shadow lines #B31E58; grey drop shadow below.

def tape(W=20, H=65, lanes=4, vertical=True):
    bw, bh = 53, 186
    ox, oy = (W * 3 - bw) / 2, 3
    cx, cy = ox + bw / 2, oy + bh / 2
    sw = 0.49 * bw
    ang = math.degrees(math.atan2(0.5 * bw, bh - sw))
    sl = (bh - sw) / math.cos(math.radians(ang)) + sw
    base = rrect_path(cx, cy, bw * 0.92, bh - 10, 6)
    straps = [rrect_path(cx, cy, sw, sl, 7, -ang), rrect_path(cx, cy, sw, sl, 7, ang)]
    defs = (lin("tb", [(0, "#BF1C5D"), (0.12, "#D72169"), (0.5, "#E12870"), (0.88, "#D72169"), (1, "#BF1C5D")], 0, 0, 1, 0) +
            lin("ts", [(0, "#C8215F"), (0.03, "#FF4A8C"), (0.12, "#FF93B4"), (0.2, "#FF6A9C"), (0.4, "#FF3B84"),
                       (0.75, "#FD3782"), (0.86, "#FF4187"), (0.93, "#F02A77"), (1, "#C81E62")]) +
            blur("sh", 2.2) + blur("s1", 0.8) +
            f'<clipPath id="tclip"><path d="{rrect_path(cx, cy, bw, bh, 8)}"/></clipPath>')
    g = [f'<g filter="url(#sh)" transform="translate(0 3)" fill="#28283A" fill-opacity="0.42"><path d="{base}"/>'
         f'<path d="{straps[0]}"/><path d="{straps[1]}"/></g>',
         f'<path d="{base}" fill="url(#tb)"/>', '<g clip-path="url(#tclip)">']
    for i, p in enumerate(straps):
        d = ang if i == 0 else -ang          # the strap running top-left -> bottom-right lies on top (003)
        # strap: its own lengthwise gradient (userSpace along the strap), dark rim, upper-left streak
        g.append(f'<g transform="rotate({fmt(d)} {fmt(cx)} {fmt(cy)})">'
                 f'<rect x="{fmt(cx - sw / 2 + 1)}" y="{fmt(cy - sl / 2 + 2)}" width="{fmt(sw - 2)}" height="{fmt(sl - 2)}" rx="7" '
                 f'fill="#8E1340" fill-opacity="0.55" filter="url(#s1)"/></g>')
        g.append(f'<g transform="rotate({fmt(d)} {fmt(cx)} {fmt(cy)})">'
                 f'<rect x="{fmt(cx - sw / 2)}" y="{fmt(cy - sl / 2)}" width="{fmt(sw)}" height="{fmt(sl)}" rx="7" fill="url(#ts)" '
                 f'stroke="#B81E5A" stroke-width="1.4"/>'
                 f'<rect x="{fmt(cx - sw / 2 + 4)}" y="{fmt(cy - sl / 2 + 8)}" width="3.2" height="{fmt(sl - 22)}" rx="1.6" '
                 f'fill="#FF8FB2" fill-opacity="0.8" filter="url(#s1)"/></g>')
    g.append('</g>')
    doc = "\n".join(g)
    if not vertical:
        doc = f'<g transform="rotate(-90 {fmt(W * 1.5)} {fmt(W * 1.5)}) translate(0 0)">{doc}</g>'
    return svg_doc(W, H, doc, defs)


# the art-spike tape at the L32 fit pitch (20 x 65 pt); SUPERSEDED by gen_board.tape at the design pitch (the shipped
# tapeV4 is gen_board's). Renamed + compare-only so running this file can never overwrite art/ui/src/tapeV4.svg.
CASES = {"tapeV4Spike": tape}



# ------------------------------------------------------------------ the glossy arrow (icon / home pile), SVG variant
# Icon (1024 px): head height H 405, shaft 0.37 H, head length 0.79 H, rounding 0.085 H (tip, head corners),
# 0.035 H (junction). Face, bevel shade, dark rim and highlight colours per arrows3d.COLORS / STYLE.md §C.
ARROW_SVG = {"yellow": ("#FEBF0E", "#FB8A03", "#E46011", "#FED23B", "#FFF1B0"),
             "red": ("#FA3633", "#D4090B", "#A80508", "#FC635F", "#FFC2BE"),
             "blue": ("#0292FE", "#005FF1", "#0647CC", "#42B7FC", "#C8ECFF")}


def arrow_points(tip, cy, H, direction=1, shaft=1.2):
    """The arrow outline (fillets sampled) in px: tip x, centre y, head height H, direction +1 right / -1 left."""
    import numpy as np
    t, hl = 0.185, 0.79
    pts = [(0.0, 0.0), (-hl, 0.5), (-hl, t), (-hl - shaft, t), (-hl - shaft, -t), (-hl, -t), (-hl, -0.5)]
    radii = [0.085, 0.085, 0.035, 0.05, 0.05, 0.035, 0.085]
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(HERE)), "pipeline"))
    from sdf import fillet_points
    fp = np.asarray(fillet_points(pts, radii, n_arc=10))
    return [(tip + direction * x * H, cy - y * H) for x, y in fp]


def arrow_group(uid, tip, cy, H, color, direction=1, shaft=1.2):
    face, shade, rim, hi, spec = ARROW_SVG[color]
    p = poly_path(arrow_points(tip, cy, H, direction, shaft))
    s = H / 405
    defs = (f'<clipPath id="ac{uid}"><path d="{p}"/></clipPath>' + blur(f"ab{uid}", 9 * s) + blur(f"as{uid}", 3 * s) +
            blur(f"ah{uid}", 5 * s))
    g = (f'<path d="{p}" fill="#3A2A20" fill-opacity="0.16" filter="url(#ab{uid})" transform="translate(0 {12 * s:.1f})"/>'
         f'<path d="{p}" fill="{face}"/>'
         f'<g clip-path="url(#ac{uid})">'
         # lower/right bevel: the outline shifted up-left, stroked dark -> a shade band only on the lower/right edges
         f'<path d="{p}" fill="none" stroke="{shade}" stroke-width="{52 * s:.1f}" transform="translate({-9 * s:.1f} {-22 * s:.1f})" filter="url(#as{uid})"/>'
         # upper/left bevel light
         f'<path d="{p}" fill="none" stroke="{hi}" stroke-width="{26 * s:.1f}" transform="translate({5 * s:.1f} {9 * s:.1f})" filter="url(#ah{uid})"/>'
         f'<path d="{p}" fill="none" stroke="{spec}" stroke-opacity="0.75" stroke-width="{7 * s:.1f}" transform="translate({3 * s:.1f} {9 * s:.1f})" filter="url(#as{uid})"/>'
         f'</g><path d="{p}" fill="none" stroke="{rim}" stroke-opacity="0.8" stroke-width="{3 * s:.1f}"/>')
    return defs, g


def arrow_icon_svg():
    """The icon composition (for the side-by-side only; OUR app icon will be designed separately)."""
    W = 1024 / 3
    parts = [arrow_group("y", 584, 262, 405, "yellow"), arrow_group("r", 510, 508.5, 408, "red", -1),
             arrow_group("b", 584, 755.5, 422, "blue")]
    defs = "".join(d for d, _ in parts)
    body = '<rect width="1024" height="1024" fill="#FEFEFE"/>' + "".join(g for _, g in parts)
    return svg_doc(W, W, body, defs)


CASES["arrowIcon"] = arrow_icon_svg


# ------------------------------------------------------------------ OUR worker, SVG variant (same design as recipes/worker.py)
def _gumdrop_outline(S, ox, oy):
    """The worker body silhouette = the 3D body's front projection: capsule (0,.72)-(0,1.36) r .5 smooth-unioned
    (k .22) with an ellipse .62 x .52 at y .62 (units -> px: x ox + x S, y oy - y S)."""
    import numpy as np
    from shapes import _contour
    step = 0.004
    xs = np.arange(-0.8, 0.8, step); ys = np.arange(0.0, 1.95, step)
    X, Y = np.meshgrid(xs, ys)
    yc = np.clip(Y, 0.72, 1.36)
    d1 = np.sqrt(X ** 2 + (Y - yc) ** 2) - 0.5
    k = np.sqrt((X / 0.62) ** 2 + ((Y - 0.62) / 0.52) ** 2)
    d2 = (k - 1) * 0.52
    kk = 0.22
    h = np.clip(0.5 + 0.5 * (d2 - d1) / kk, 0, 1)
    d = d2 * (1 - h) + d1 * h - kk * h * (1 - h)
    pts = _contour(d, 0, 0, 1.0)
    return [(ox + (-0.8 + c * step) * S, oy - (0.0 + r * step) * S) for c, r in pts]


def worker_svg(W=110, H=120):
    S, ox, oy = 150.0, 168.0, 350.0
    X = lambda x: ox + x * S
    Y = lambda y: oy - y * S
    body = poly_path(_gumdrop_outline(S, ox, oy))
    defs = (rad("wb", [(0, "#FFD95A"), (0.35, "#FDBD18"), (0.7, "#F29C0C"), (1, "#D87606")], cx=0.38, cy=0.3, r=0.78) +
            rad("warm", [(0, "#FDBD18"), (0.6, "#F4A012"), (1, "#D87606")], cx=0.35, cy=0.3, r=0.8) +
            lin("sh", [(0, "#26A9B8"), (1, "#15707E")]) + lin("bt", [(0, "#A5582A"), (0.45, "#8E4A1C"), (1, "#6A3310")]) +
            rad("iris", [(0, "#8A5028"), (0.7, "#6A3A18"), (1, "#4A2410")]) +
            rad("eye", [(0, "#FFFFFF"), (0.75, "#F4F2F0"), (1, "#C9C3C0")], cx=0.45, cy=0.35, r=0.7) +
            blur("wbl", 3) + blur("wsm", 1.2) + blur("wsh", 6) +
            f'<clipPath id="wc"><path d="{body}"/></clipPath>')
    g = []
    g.append(f'<ellipse cx="{X(0)}" cy="{Y(0.0)}" rx="{0.62 * S}" ry="{0.09 * S}" fill="#1A2350" fill-opacity="0.35" filter="url(#wsh)"/>')
    for sx in (-1, 1):   # boots
        g.append(f'<ellipse cx="{X(sx * 0.26)}" cy="{Y(0.07)}" rx="{0.16 * S}" ry="{0.10 * S}" fill="#1B5F70"/>'
                 f'<ellipse cx="{X(sx * 0.26 - 0.03)}" cy="{Y(0.11)}" rx="{0.08 * S}" ry="{0.035 * S}" fill="#3F8FA0" fill-opacity="0.8" filter="url(#wsm)"/>')

    def limb(pts, r):
        d = "M" + " L".join(f"{X(a):.1f} {Y(b):.1f}" for a, b in pts)
        return (f'<path d="{d}" fill="none" stroke="#D98008" stroke-width="{2 * r * S + 4:.1f}" stroke-linecap="round" stroke-linejoin="round"/>'
                f'<path d="{d}" fill="none" stroke="url(#warm)" stroke-width="{2 * r * S:.1f}" stroke-linecap="round" stroke-linejoin="round"/>'
                f'<path d="{d}" fill="none" stroke="#FFE08A" stroke-opacity="0.55" stroke-width="{0.5 * r * S:.1f}" stroke-linecap="round" '
                f'transform="translate({-0.25 * r * S:.1f} {-0.35 * r * S:.1f})" filter="url(#wsm)"/>')
    g.append(limb([(-0.50, 0.92), (-0.70, 0.70), (-0.74, 0.50)], 0.11))
    g.append(f'<circle cx="{X(-0.76)}" cy="{Y(0.42)}" r="{0.15 * S}" fill="url(#warm)" stroke="#D98008" stroke-width="2"/>')
    g.append(f'<path d="{body}" fill="url(#wb)"/>')
    # rim light (cool, right edge) and a soft specular on the upper left
    g.append(f'<g clip-path="url(#wc)"><path d="{body}" fill="none" stroke="#FFF4D0" stroke-opacity="0.7" stroke-width="10" '
             f'transform="translate(-6 2)" filter="url(#wbl)"/>'
             f'<ellipse cx="{X(-0.22)}" cy="{Y(1.62)}" rx="{0.16 * S}" ry="{0.10 * S}" fill="#FFFFFF" fill-opacity="0.45" filter="url(#wbl)"/>'
             # shorts + belt clipped to the body
             f'<rect x="0" y="{Y(0.47)}" width="400" height="200" fill="url(#sh)"/>'
             f'<rect x="0" y="{Y(0.60)}" width="400" height="{0.13 * S}" fill="url(#bt)"/>'
             f'<rect x="0" y="{Y(0.60)}" width="400" height="3" fill="#C27A48" fill-opacity="0.8"/></g>')
    g.append(f'<circle cx="{X(0)}" cy="{Y(0.535)}" r="{0.075 * S}" fill="none" stroke="#F4B63A" stroke-width="{0.045 * S:.1f}"/>'
             f'<circle cx="{X(0) - 2}" cy="{Y(0.535) - 2}" r="{0.075 * S}" fill="none" stroke="#FFE08A" stroke-width="2" stroke-opacity="0.8"/>')
    g.append(f'<rect x="{X(0.42)}" y="{Y(0.70)}" width="{0.09 * S}" height="{0.20 * S}" rx="6" fill="#E8332A" transform="rotate(10 {X(0.46)} {Y(0.6)})"/>')
    # face
    for sx in (-1, 1):
        cx, cy = X(sx * 0.19), Y(1.30)
        g.append(f'<ellipse cx="{cx}" cy="{cy}" rx="{0.16 * S}" ry="{0.19 * S}" fill="url(#eye)" stroke="#C07010" stroke-opacity="0.35" stroke-width="2"/>')
        ix, iy = cx - sx * 2 + 2, cy + 4
        g.append(f'<ellipse cx="{ix}" cy="{iy}" rx="{0.095 * S}" ry="{0.11 * S}" fill="url(#iris)"/>'
                 f'<ellipse cx="{ix}" cy="{iy + 1}" rx="{0.055 * S}" ry="{0.064 * S}" fill="#1A0E08"/>'
                 f'<circle cx="{ix + 5}" cy="{iy - 7}" r="{0.026 * S}" fill="#FFFFFF"/><circle cx="{ix - 5}" cy="{iy + 6}" r="{0.012 * S}" fill="#FFFFFF"/>')
        g.append(f'<path d="M{cx - 0.08 * S:.1f} {Y(1.56 + (0.02 if sx < 0 else 0.03)):.1f} L{cx + 0.08 * S:.1f} {Y(1.56 + (0.045 if sx < 0 else 0.015)):.1f}" '
                 f'stroke="#4A240E" stroke-width="{0.068 * S:.1f}" stroke-linecap="round"/>')
    mx, my = X(0), Y(1.03)
    g.append(f'<clipPath id="mc"><path d="M{mx - 0.27 * S:.1f} {my:.1f} A{0.27 * S:.1f} {0.19 * S:.1f} 0 0 0 {mx + 0.27 * S:.1f} {my:.1f} Z"/></clipPath>'
             f'<path d="M{mx - 0.27 * S:.1f} {my:.1f} A{0.27 * S:.1f} {0.19 * S:.1f} 0 0 0 {mx + 0.27 * S:.1f} {my:.1f} Z" fill="#7E1A12"/>'
             f'<g clip-path="url(#mc)"><ellipse cx="{mx + 3}" cy="{Y(0.89)}" rx="{0.15 * S}" ry="{0.075 * S}" fill="#F0707A"/>'
             f'<rect x="{mx - 14}" y="{my}" width="12" height="9" rx="3" fill="#FFFFFF"/><rect x="{mx + 2}" y="{my}" width="12" height="9" rx="3" fill="#FFFFFF"/></g>'
             f'<path d="M{mx - 0.29 * S:.1f} {my - 1:.1f} Q{mx:.1f} {my + 4:.1f} {mx + 0.29 * S:.1f} {my - 1:.1f}" fill="none" stroke="#C86A08" stroke-width="3" stroke-linecap="round"/>')
    # curl
    import math as _m
    pts = [(0.02 + 0.10 * _m.sin(a) * (1 - 0.35 * a / 5), 1.83 + 0.10 * a / 5 + 0.10 * (1 - _m.cos(a)) * 0.6) for a in [i * 1.6 * _m.pi / 21 for i in range(22)]]
    d = "M" + " L".join(f"{X(a):.1f} {Y(b):.1f}" for a, b in pts)
    g.append(f'<path d="{d}" fill="none" stroke="#C86A04" stroke-width="{0.11 * S + 3:.1f}" stroke-linecap="round"/>'
             f'<path d="{d}" fill="none" stroke="#F08A0A" stroke-width="{0.11 * S:.1f}" stroke-linecap="round"/>')
    # raised arm (in front)
    g.append(limb([(0.50, 0.98), (0.74, 1.14), (0.78, 1.40)], 0.105))
    g.append(f'<circle cx="{X(0.80)}" cy="{Y(1.50)}" r="{0.15 * S}" fill="url(#warm)" stroke="#D98008" stroke-width="2"/>'
             f'<ellipse cx="{X(0.93)}" cy="{Y(1.46)}" rx="{0.06 * S}" ry="{0.08 * S}" fill="url(#warm)" stroke="#D98008" stroke-width="2"/>')
    return svg_doc(W, H, "\n".join(g), defs)


CASES["workerHome"] = worker_svg


# comparison-only compositions (they re-create a reference layout to judge a route) never live in the repo tree
COMPARE_ONLY = {"arrowIcon", "tapeV4Spike", "workerHome"}   # spike candidates: never shipped from art/ui/src
SVGSRC_BUILD = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(HERE))), "build", "ui-art", "svgsrc")

if __name__ == "__main__":
    names = sys.argv[1:] or list(CASES)
    for n in names:
        d = SVGSRC_BUILD if n in COMPARE_ONLY else HERE
        os.makedirs(d, exist_ok=True)
        open(os.path.join(d, f"{n}.svg"), "w", encoding="utf-8").write(CASES[n]())
        print("wrote", os.path.join(d, f"{n}.svg"))
