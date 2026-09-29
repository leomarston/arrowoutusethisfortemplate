#!/usr/bin/env python3
"""Board obstacle sprites (STYLE.md route C3/B2, SVG): the pink TAPE (lanes x orientation), the locked DOOR (any w x h
cells), the purple HEX LOCK and the gold KEY on its ribbon. Writes art/ui/src/<case>.svg; art/ui/tools/svg.py (or the
manifest batch, art/tools/art_batch.py) rasterises them to art/ui/out/<case>@3x.png.

    ~/.venvs/mf3d/bin/python art/ui/src/gen_board.py                 # every case in CASES
    ~/.venvs/mf3d/bin/python art/ui/src/gen_board.py tapeV4 doorW4H8  # some

Every number is MEASURED on the untinted runner shots (art/tools/measure_obstacles.py -> STYLE.md §A "Board obstacles,
measured") and expressed in PITCH units, so one generator serves every level and zoom. Shapes are primitives
(rounded rects, chamfered rects, hexagons, ellipses); nothing is traced from a capture.

Design pitch (DECISION, see art/MANIFEST.json "board_design_pitch_pt"): board sprites are authored at P0 = 32 pt per
cell (96 px @3x), so they stay crisp up to 32 pt/cell on screen (fit pitch is 14-28 pt, zoom 0.75-3x); the engine
scales a sprite by (pitch_on_screen / 32). Each case's ANCHOR (the lattice point the sprite registers to) is in ANCHORS.

Units inside the SVG: @3x px (1 unit = 1/3 pt), y down. u = 3 * P0 = px per cell.
"""
from __future__ import annotations

import math
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from gen_chrome import blur  # noqa: E402
from shapes import fmt, poly_path, svg_doc  # noqa: E402
import d1_skin  # noqa: E402

P0 = 32.0          # design pitch, pt per cell
STROKE = 0.22      # arrow stroke / pitch (STYLE §A)

# PUBLISH R7 BOARD-UI (SPEC.md rulings 38 / 44 / 46): the shipped skin is D1 "Burrow Works". Every generator below keeps
# its measured geometry and shading structure; `skinned` recolours its output per material (d1_skin.py: teal webbing
# tape, teal-painted door frame + iron trim + honey plank shutter + iron bolts, brass lock in an iron socket, teal key
# ribbon, iron pipe collars + teal counter plate, slate-stone box + brass ring) and adds the D1 material details drawn in
# `_d1_details`. SKIN = "measured" reproduces the measured reference look (proofs / before-after sheets only).
SKIN = os.environ.get("BOARD_SKIN", "d1")


def skinned(kind):
    def wrap(fn):
        def inner(*a, **kw):
            res = fn(*a, **kw)
            if SKIN != "d1":
                return res
            svg, meta = res if isinstance(res, tuple) else (res, None)
            svg = d1_skin.recolour(svg, d1_skin.rules_for(kind))
            svg = re.sub(r"@d1:(\w+)", lambda m_: D1_DETAIL[m_.group(1)], svg)
            return (svg, meta) if meta is not None else svg
        inner.__name__ = fn.__name__
        inner.__doc__ = fn.__doc__
        inner.measured = fn
        return inner
    return wrap


def d1():
    return SKIN == "d1"


# D1 material details (drawn only in the d1 skin, AFTER the recolour: their colours are written as "@d1:<name>"
# placeholders so no material map touches them): wood grain + iron nails on the door's plank shutter, stitching on
# the tape's webbing straps. All inside the existing silhouettes (clip paths), so frames, anchors and alpha bboxes stay.
D1_DETAIL = dict(grain="#7E4E27", knot="#6A3E1C", nail="#3E4A4E", nailHi="#D5DEE0", stitch="#C2F7EE")


def _stops(stops):
    out = []
    for st in stops:
        o, c = st[0], st[1]
        a = st[2] if len(st) > 2 else 1
        out.append(f'<stop offset="{o}" stop-color="{c}"' + ("" if a == 1 else f' stop-opacity="{a}"') + '/>')
    return "".join(out)


def ulin(id_, stops, x1, y1, x2, y2):
    """A linear gradient in user space (px)."""
    return (f'<linearGradient id="{id_}" gradientUnits="userSpaceOnUse" x1="{fmt(x1)}" y1="{fmt(y1)}" x2="{fmt(x2)}" '
            f'y2="{fmt(y2)}">{_stops(stops)}</linearGradient>')


def urad(id_, stops, cx, cy, r, fx=None, fy=None):
    f = f' fx="{fmt(fx)}" fy="{fmt(fy)}"' if fx is not None else ""
    return (f'<radialGradient id="{id_}" gradientUnits="userSpaceOnUse" cx="{fmt(cx)}" cy="{fmt(cy)}" r="{fmt(r)}"{f}>'
            f'{_stops(stops)}</radialGradient>')


def rrect(x0, y0, x1, y1, rtl, rtr=None, rbr=None, rbl=None, n=8):
    """Rounded rectangle path with per-corner radii (arcs sampled)."""
    rtr = rtl if rtr is None else rtr
    rbr = rtl if rbr is None else rbr
    rbl = rtl if rbl is None else rbl
    pts = []

    def arc(cx, cy, r, a0):
        for k in range(n + 1):
            a = math.radians(a0 + 90 * k / n)
            pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    arc(x0 + rtl, y0 + rtl, rtl, 180)
    arc(x1 - rtr, y0 + rtr, rtr, 270)
    arc(x1 - rbr, y1 - rbr, rbr, 0)
    arc(x0 + rbl, y1 - rbl, rbl, 90)
    return poly_path(pts)


def rot_rrect(cx, cy, w, h, r, deg):
    """A w x h rounded rect centred at (cx, cy) rotated by deg (clockwise on screen)."""
    pts = []
    hw, hh = w / 2 - r, h / 2 - r
    for sx, sy, a0 in ((1, 1, 0), (-1, 1, 90), (-1, -1, 180), (1, -1, 270)):
        for k in range(9):
            a = math.radians(a0 + 90 * k / 8)
            pts.append((sx * hw + r * math.cos(a), sy * hh + r * math.sin(a)))
    t = math.radians(deg)
    c, s = math.cos(t), math.sin(t)
    return poly_path([(cx + c * x - s * y, cy + s * x + c * y) for x, y in pts])


def chamfer_top(x0, y0, x1, y1, c, r=0.0, rb=0.0):
    """A rectangle whose two TOP corners are cut at 45 deg by c (softened by r) and bottom corners rounded by rb."""
    pts = [(x0, y1 - rb), (x0, y0 + c), (x0 + c, y0), (x1 - c, y0), (x1, y0 + c), (x1, y1 - rb)]
    if rb:
        pts = [(x0 + rb, y1)] + pts + [(x1 - rb, y1)]
    else:
        pts = [(x0, y1)] + pts[1:] + [(x1, y1)]
    if r > 0:
        pts = _round_poly(pts, r)
    return poly_path(pts)


def _round_poly(pts, r, n=5):
    """Soften the corners of a closed polygon by r (quadratic-ish sampling between the two edge points)."""
    out = []
    N = len(pts)
    for i in range(N):
        p0, p1, p2 = pts[i - 1], pts[i], pts[(i + 1) % N]
        d1 = math.hypot(p0[0] - p1[0], p0[1] - p1[1]); d2 = math.hypot(p2[0] - p1[0], p2[1] - p1[1])
        rr = min(r, d1 / 2, d2 / 2)
        if rr < 0.2:
            out.append(p1); continue
        a = (p1[0] + (p0[0] - p1[0]) * rr / d1, p1[1] + (p0[1] - p1[1]) * rr / d1)
        b = (p1[0] + (p2[0] - p1[0]) * rr / d2, p1[1] + (p2[1] - p1[1]) * rr / d2)
        for k in range(n + 1):
            t = k / n
            out.append(((1 - t) ** 2 * a[0] + 2 * (1 - t) * t * p1[0] + t * t * b[0],
                        (1 - t) ** 2 * a[1] + 2 * (1 - t) * t * p1[1] + t * t * b[1]))
    return out


def hexagon(cx, cy, a, b, c=None, r=0.0):
    """Hexagon with vertices at left/right (+-a, 0) and a flat top/bottom of half-length c at +-b; corners softened."""
    c = a / 2 if c is None else c
    pts = [(cx - a, cy), (cx - c, cy - b), (cx + c, cy - b), (cx + a, cy), (cx + c, cy + b), (cx - c, cy + b)]
    return _round_poly(pts, r) if r else pts


def frame_pt(v_px):
    """Whole pt that hold v_px @3x."""
    return int(math.ceil(v_px / 3 - 1e-6))


# ====================================================================================== TAPE
# Measured (STYLE §A): band 0.99 pitch across x (lanes - 1 + 0.46) pitch along, centred on the bundle's cell block.
# The whole tape sits OVER the bound arrows: the shafts stop at the band's edges (sheet m_tapeV4 / m_tapeH4, round 2:
# round 1 cut lane gaps into the base and the sheet showed black stripes the capture does not have). Two straps corner to
# corner over the base, the one running top-left -> bottom-right on top (both orientations). Top light: each strap's up-facing long
# edge carries the light streak, the down-facing edge a dark rim + a shadow on what is below.
TAPE = dict(across=0.99, extra=0.46, strap=0.49, strap_r=0.13, base_r=0.10,
            base=[(0, "#C41C5F"), (0.08, "#D72169"), (0.3, "#DC236C"), (0.7, "#E0276F"), (0.92, "#DC236C"), (1, "#C8205F")],
            face="#FF3B84", lite="#FF93B4", streak="#FF7DA7", low="#E0246F", rim="#B81E5A", shade="#AE1C56")


@skinned("tape")
def tape(lanes=4, orient="V", P=P0):
    u = 3 * P
    T = TAPE
    Wb = T["across"] * u
    Lb = (lanes - 1 + T["extra"]) * u
    m = 0.10 * u
    if orient == "V":
        W, H = frame_pt(Wb + 2 * m), frame_pt(Lb + 2 * m)
    else:
        W, H = frame_pt(Lb + 2 * m), frame_pt(Wb + 2 * m)
    cx, cy = W * 1.5, H * 1.5
    # along / across unit vectors on screen
    al = (0.0, 1.0) if orient == "V" else (1.0, 0.0)
    ac = (1.0, 0.0) if orient == "V" else (0.0, 1.0)

    def P2(s, t):  # along s, across t (px from the centre)
        return (cx + al[0] * s + ac[0] * t, cy + al[1] * s + ac[1] * t)
    bw, bh = (Wb, Lb) if orient == "V" else (Lb, Wb)
    base = rrect(cx - bw / 2, cy - bh / 2, cx + bw / 2, cy + bh / 2, T["base_r"] * u)
    # base gradient runs ACROSS the band
    x1, y1 = P2(0, -Wb / 2); x2, y2 = P2(0, Wb / 2)
    defs = [ulin("tb", T["base"], x1, y1, x2, y2), blur("tsh", 0.035 * u), blur("ts1", 0.012 * u), blur("ts2", 0.02 * u)]
    # straps
    sw = T["strap"] * Wb
    ang = math.degrees(math.atan2(0.5 * Wb, Lb - sw))
    sl = (Lb - sw) / math.cos(math.radians(ang)) + sw
    # screen rotation of a strap whose long axis is 'along' tilted toward +across by ang (A) or -ang (B)
    base_deg = 90.0 if orient == "V" else 0.0          # rot_rrect's w axis = screen x; along V = screen y
    # strap A runs top-left -> bottom-right on screen, strap B top-right -> bottom-left
    degA = base_deg - ang if orient == "V" else ang
    degB = base_deg + ang if orient == "V" else -ang
    straps = []
    for name, deg in (("B", degB), ("A", degA)):
        path = rot_rrect(cx, cy, sl, sw, T["strap_r"] * u, deg)
        t = math.radians(deg)
        dx, dy = math.cos(t), math.sin(t)            # long axis
        nx, ny = -dy, dx                             # one normal
        if ny > 0:                                   # make n point UP (the lit edge)
            nx, ny = -nx, -ny
        straps.append((name, path, deg, (dx, dy), (nx, ny)))
    for name, path, deg, (dx, dy), (nx, ny) in straps:
        # vertical screen-space light across the strap's extent: brighter at the top, darker at the bottom
        ext = abs(dy) * sl / 2 + abs(dx) * sw / 2
        defs.append(ulin(f"tsg{name}", [(0, T["lite"]), (0.14, "#FF5F97"), (0.32, T["face"]), (0.8, T["face"]),
                                        (0.93, T["low"]), (1, "#C81E62")], cx, cy - ext, cx, cy + ext))
        defs.append(f'<clipPath id="tsc{name}"><path d="{path}"/></clipPath>')
    g = []
    # soft grey drop shadow of the whole tape (3 px down at 53.6 px pitch)
    g.append(f'<g filter="url(#tsh)" transform="translate(0 {fmt(0.05 * u)})" fill="#2A2A3A" fill-opacity="0.30">'
             f'<path d="{base}"/>' + "".join(f'<path d="{p}"/>' for _, p, _, _, _ in straps) + '</g>')
    g.append(f'<g><path d="{base}" fill="url(#tb)"/>'
             f'<path d="{base}" fill="none" stroke="#B81D59" stroke-opacity="0.55" stroke-width="{fmt(0.02 * u)}"/></g>')
    for name, path, deg, (dx, dy), (nx, ny) in straps:
        sh = 0.075 * u
        # the strap's shadow on the base / the other strap (down-facing side)
        g.append(f'<path d="{path}" fill="#8E1340" fill-opacity="0.55" filter="url(#ts1)" transform="translate({fmt(-nx * sh * 0.5)} {fmt(-ny * sh * 0.6)})"/>')
        g.append(f'<path d="{path}" fill="url(#tsg{name})" stroke="{T["rim"]}" stroke-width="{fmt(0.015 * u)}"/>')
        # the lit long edge: a light streak just inside it
        off = sw / 2 - 0.085 * u
        sx, sy = cx + nx * off, cy + ny * off
        ll = sl - 0.34 * u
        g.append(f'<g clip-path="url(#tsc{name})"><path d="M{fmt(sx - dx * ll / 2)} {fmt(sy - dy * ll / 2)} L{fmt(sx + dx * ll / 2)} {fmt(sy + dy * ll / 2)}" '
                 f'stroke="{T["streak"]}" stroke-opacity="0.9" stroke-width="{fmt(0.05 * u)}" stroke-linecap="round" filter="url(#ts1)"/>'
                 # the dark rim along the down-facing edge
                 f'<path d="M{fmt(cx - nx * sw / 2 - dx * sl / 2)} {fmt(cy - ny * sw / 2 - dy * sl / 2)} '
                 f'L{fmt(cx - nx * sw / 2 + dx * sl / 2)} {fmt(cy - ny * sw / 2 + dy * sl / 2)}" '
                 f'stroke="#C21F60" stroke-opacity="0.8" stroke-width="{fmt(0.06 * u)}" filter="url(#ts2)"/></g>')
        if d1():   # webbing: a running stitch along both long edges of the strap
            ls = sl - 0.30 * u
            for sgn in (1, -1):
                off = sgn * (sw / 2 - 0.085 * u)
                ax_, ay_ = cx + nx * off, cy + ny * off
                g.append(f'<g clip-path="url(#tsc{name})"><path d="M{fmt(ax_ - dx * ls / 2)} {fmt(ay_ - dy * ls / 2)} '
                         f'L{fmt(ax_ + dx * ls / 2)} {fmt(ay_ + dy * ls / 2)}" stroke="@d1:stitch" stroke-opacity="0.8" '
                         f'stroke-width="{fmt(0.022 * u)}" stroke-dasharray="{fmt(0.075 * u)} {fmt(0.055 * u)}" '
                         f'stroke-linecap="round"/></g>')
    return svg_doc(W, H, "\n".join(g), "".join(defs)), dict(anchor=(W / 2, H / 2), note="anchor = centre of the bundle's cell block")


# ====================================================================================== DOOR
# Measured on L33 (027) / L34 (036) / L37 (052), all in pitch units u (STYLE §A):
#   frame outer = the cell block (x exact), top 0.055 below the block top, bottom on the block's bottom edge;
#   top corners r 0.374, bottom r 0.05. Header 0.747 tall; posts 0.39 wide (outer dark band 0.11, orange face,
#   1 px light line, 2 px dark outline 0.037). Purple band: top 0.28, sides 0.24; outer boundary chamfered 0.32 at
#   the top corners; inner rim #69239B top 0.093 / sides 0.056 with a 1 px light line on its outside. Shutter from
#   0.635 in from each side, 1.027 below the frame top, down to 0.09 above the frame bottom; top corners chamfered
#   0.30. Slats: ONE PER CELL ROW, seam on every row boundary (+-0.5 px): seam 0.03 dark, highlight 0.04 below it,
#   face, a lower band from 0.72 to 0.94 of the row, 0.06 darkening into the next seam. Rivets: centre (0.458, 0.411)
#   from the frame's top corners, d 0.374. Drop shadow (0.02, 0.056), blur 0.035, black 0.5.
DOOR = dict(top=0.055, r_top=0.374, r_bot=0.05, header=0.747, post=0.39, band=0.11, outline=0.037,
            purple_top=0.28, purple_side=0.24, chamfer=0.32, chamfer_r=0.20, rim_top=0.093, rim_side=0.056, shutter_chamfer=0.30,
            shutter_bottom=0.09, rivet=(0.458, 0.411, 0.187),
            orange="#FFA40D", header_face="#FFAA10", header_low="#FFA20A", header_top="#FFB324", header_line="#FFC92D",
            band_l="#CD6D07", band_r="#CF7512", post_bottom="#B05A03", outline_col="#3A0E06",
            purple="#AE3DD3", purple_hi="#CE60F1", purple_line="#E08AF5", rim_col="#69239B",
            slat="#5FA6F2", slat_low="#579DEB", seam="#2B57A8", slat_hi="#A8E2FE", shutter_foot="#23519C")


@skinned("door")
def door(wc=4, hc=4, P=P0):
    u = 3 * P
    D = DOOR
    m = 9.0                                   # 3 pt margin (shadow); the cell block starts at (m, m)
    W, H = int(wc * P + 2 * m / 3), int(hc * P + 2 * m / 3)
    L, R = m, m + wc * u
    T, B = m + D["top"] * u, m + hc * u
    outer = rrect(L, T, R, B, D["r_top"] * u, D["r_top"] * u, D["r_bot"] * u, D["r_bot"] * u)
    ix0, ix1, iy0 = L + D["post"] * u, R - D["post"] * u, T + D["header"] * u
    inner_cut = chamfer_top(ix0, iy0, ix1, B - 0.035 * u, D["chamfer"] * u, r=D["chamfer_r"] * u)
    rx0, rx1, ry0 = ix0 + D["purple_side"] * u - D["rim_side"] * u, ix1 - D["purple_side"] * u + D["rim_side"] * u, \
        iy0 + D["purple_top"] * u - D["rim_top"] * u
    sx0, sx1, sy0 = ix0 + D["purple_side"] * u, ix1 - D["purple_side"] * u, iy0 + D["purple_top"] * u
    sy1 = B - D["shutter_bottom"] * u
    rim = chamfer_top(rx0, ry0, rx1, sy1, (D["shutter_chamfer"] + 0.02) * u, r=D["chamfer_r"] * 0.85 * u)
    shutter = chamfer_top(sx0, sy0, sx1, sy1, D["shutter_chamfer"] * u, r=D["chamfer_r"] * 0.8 * u)
    defs = [blur("dsh", 0.035 * u), blur("dsoft", 0.008 * u),
            f'<clipPath id="dco"><path d="{outer}"/></clipPath>',
            f'<clipPath id="dcs"><path d="{shutter}"/></clipPath>',
            f'<clipPath id="dci"><path d="{inner_cut}"/></clipPath>',
            ulin("dts", [(0, "#274161"), (0.35, "#3B6592", 0.9), (1, "#5FA6F2", 0)], 0, sy0, 0, sy0 + 0.16 * u),
            ulin("dsl", [(0, "#3F72A8"), (1, "#5FA6F2", 0)], sx0, 0, sx0 + 0.075 * u, 0),
            ulin("dsr", [(0, "#5FA6F2", 0), (1, "#4A7FB8")], sx1 - 0.075 * u, 0, sx1, 0),
            ulin("dbl", [(0, D["band_l"]), (0.78, D["band_l"]), (1, "#F39006", 0)], L, 0, L + 0.14 * u, 0),
            ulin("dbr", [(0, "#F39006", 0), (0.22, D["band_r"]), (1, D["band_r"])], R - 0.14 * u, 0, R, 0),
            urad("drv", [(0, "#FFFFF1"), (0.22, "#FFF48A"), (0.5, "#FFD23A"), (0.8, "#FFAE14"), (1, "#EF8E0B")],
                 0, 0, 1)]
    g = []
    # drop shadow: the frame + the shutter, offset down-right
    g.append(f'<g filter="url(#dsh)" transform="translate({fmt(0.02 * u)} {fmt(0.056 * u)})" fill="#141414" fill-opacity="0.5">'
             f'<path d="{outer}"/></g>')
    # ---- orange frame (as a solid slab; the purple + shutter cover its middle)
    g.append(f'<path d="{outer}" fill="{D["orange"]}"/>')
    g.append(f'<g clip-path="url(#dco)">'
             f'<rect x="{fmt(L)}" y="{fmt(T)}" width="{fmt(R - L)}" height="{fmt(D["header"] * u)}" fill="{D["header_face"]}"/>'
             f'<rect x="{fmt(L)}" y="{fmt(T + 0.575 * u)}" width="{fmt(R - L)}" height="{fmt(0.172 * u)}" fill="{D["header_low"]}"/>'
             f'<rect x="{fmt(L)}" y="{fmt(T)}" width="{fmt(R - L)}" height="{fmt(0.06 * u)}" fill="{D["header_top"]}"/>'
             f'<rect x="{fmt(L + 0.2 * u)}" y="{fmt(T + 0.075 * u)}" width="{fmt(R - L - 0.4 * u)}" height="{fmt(0.035 * u)}" '
             f'fill="{D["header_line"]}" filter="url(#dsoft)"/>'
             f'<rect x="{fmt(L)}" y="{fmt(T)}" width="{fmt(0.14 * u)}" height="{fmt(B - T)}" fill="url(#dbl)"/>'
             f'<rect x="{fmt(R - 0.14 * u)}" y="{fmt(T)}" width="{fmt(0.14 * u)}" height="{fmt(B - T)}" fill="url(#dbr)"/>'
             f'<rect x="{fmt(L)}" y="{fmt(B - 0.09 * u)}" width="{fmt(R - L)}" height="{fmt(0.09 * u)}" fill="{D["post_bottom"]}"/>'
             f'</g>')
    # 1 px light line on the orange side of the inner edge, then the dark outline
    # (clipped above the foot: the capture has no dark line along the door's bottom -- sheet m_doorW4H4 round 2)
    defs.append(f'<clipPath id="dnb"><rect x="0" y="0" width="{W * 3}" height="{fmt(B - 0.07 * u)}"/></clipPath>')
    g.append(f'<g clip-path="url(#dnb)">'
             f'<path d="{inner_cut}" fill="none" stroke="#FFD04A" stroke-width="{fmt(0.10 * u)}" stroke-opacity="0.8"/>'
             f'<path d="{inner_cut}" fill="none" stroke="{D["outline_col"]}" stroke-width="{fmt(2 * D["outline"] * u + 1)}"/></g>')
    # ---- purple inner frame
    g.append(f'<path d="{inner_cut}" fill="{D["purple"]}"/>')
    g.append(f'<g clip-path="url(#dci)"><rect x="{fmt(ix0)}" y="{fmt(iy0)}" width="{fmt(ix1 - ix0)}" height="{fmt(0.035 * u)}" '
             f'fill="{D["purple_hi"]}" filter="url(#dsoft)"/>'
             f'<path d="{inner_cut}" fill="none" stroke="#8A2BAE" stroke-width="{fmt(0.04 * u)}"/></g>')
    g.append(f'<path d="{rim}" fill="none" stroke="{D["purple_line"]}" stroke-width="{fmt(0.045 * u)}"/>')
    g.append(f'<path d="{rim}" fill="{D["rim_col"]}"/>')
    # ---- the shutter: flat face, then one slat per cell row
    g.append(f'<path d="{shutter}" fill="{D["slat"]}"/>')
    sl = []
    for k in range(hc):
        y0 = m + k * u
        y1 = y0 + u
        sl.append(f'<rect x="{fmt(sx0)}" y="{fmt(y0 + 0.72 * u)}" width="{fmt(sx1 - sx0)}" height="{fmt(0.22 * u)}" fill="{D["slat_low"]}"/>')
        defs.append(ulin(f"dsd{k}", [(0, D["slat_low"]), (0.45, "#4288DA"), (1, "#2C66B7")], 0, y1 - 0.06 * u, 0, y1))
        sl.append(f'<rect x="{fmt(sx0)}" y="{fmt(y1 - 0.06 * u)}" width="{fmt(sx1 - sx0)}" height="{fmt(0.06 * u)}" fill="url(#dsd{k})"/>')
        if k < hc - 1:
            sl.append(f'<rect x="{fmt(sx0)}" y="{fmt(y1 - 0.012 * u)}" width="{fmt(sx1 - sx0)}" height="{fmt(0.028 * u)}" fill="{D["seam"]}"/>'
                      f'<rect x="{fmt(sx0)}" y="{fmt(y1 + 0.016 * u)}" width="{fmt(sx1 - sx0)}" height="{fmt(0.036 * u)}" fill="{D["slat_hi"]}"/>')
    sl.append(f'<rect x="{fmt(sx0)}" y="{fmt(sy1 - 0.09 * u)}" width="{fmt(sx1 - sx0)}" height="{fmt(0.09 * u)}" fill="{D["shutter_foot"]}"/>')
    sl.append(f'<rect x="{fmt(sx0)}" y="{fmt(sy0)}" width="{fmt(sx1 - sx0)}" height="{fmt(0.16 * u)}" fill="url(#dts)"/>')
    sl.append(f'<rect x="{fmt(sx0)}" y="{fmt(sy0)}" width="{fmt(0.075 * u)}" height="{fmt(sy1 - sy0)}" fill="url(#dsl)"/>')
    sl.append(f'<rect x="{fmt(sx1 - 0.075 * u)}" y="{fmt(sy0)}" width="{fmt(0.075 * u)}" height="{fmt(sy1 - sy0)}" fill="url(#dsr)"/>')
    if d1():   # honey planks: grain lines along each plank + an iron nail at both ends (inside the fixed post zone of
        #          DoorLayer's 9-slice, so a stretched door never smears them)
        for k in range(hc):
            y0 = m + k * u
            for j, (fy, amp, ph) in enumerate(((0.26, 0.016, 0.0), (0.44, 0.012, 1.7), (0.60, 0.018, 3.1))):
                pts = [(sx0 + t / 24 * (sx1 - sx0),
                        y0 + fy * u + amp * u * math.sin(ph + k * 1.3 + 2 * math.pi * (t / 24) * (1.2 + 0.35 * j)))
                       for t in range(25)]
                sl.append(f'<path d="{poly_path(pts, close=False)}" fill="none" stroke="@d1:grain" stroke-opacity="0.30" '
                          f'stroke-width="{fmt(0.016 * u)}" stroke-linecap="round"/>')
            for nx_ in (sx0 + 0.05 * u, sx1 - 0.05 * u):
                ny_ = y0 + 0.44 * u
                sl.append(f'<circle cx="{fmt(nx_)}" cy="{fmt(ny_)}" r="{fmt(0.032 * u)}" fill="@d1:nail"/>'
                          f'<circle cx="{fmt(nx_ - 0.01 * u)}" cy="{fmt(ny_ - 0.011 * u)}" r="{fmt(0.012 * u)}" fill="@d1:nailHi" '
                          f'fill-opacity="0.9"/>')
    g.append(f'<g clip-path="url(#dcs)">{"".join(sl)}</g>')
    # ---- rivets
    rx, ry, rr = D["rivet"]
    for cxr in (L + rx * u, R - rx * u):
        cyr = T + ry * u
        r = rr * u
        g.append(f'<circle cx="{fmt(cxr)}" cy="{fmt(cyr)}" r="{fmt(r + 0.6)}" fill="#983A00"/>')
    return svg_doc(W, H, _rivet_faces("\n".join(g), D, L, R, T, u), "".join(defs)), \
        dict(anchor=(m / 3, m / 3), note="anchor = top-left corner of the door's cell block (cols x rows)")


def _rivet_faces(body, D, L, R, T, u):
    """The rivet domes: unit circles in a scaled group (keeps the unit-space radial gradient `drv`)."""
    rx, ry, rr = D["rivet"]
    out = body
    faces = []
    for cxr in (L + rx * u, R - rx * u):
        cyr = T + ry * u
        r = rr * u - 0.6
        faces.append(f'<g transform="translate({fmt(cxr)} {fmt(cyr)}) scale({fmt(r)})">'
                     f'<circle r="1" fill="url(#drv)"/></g>')
        # specular: upper-right of the dome (measured +0.25 r, -0.45 r)
        faces.append(f'<ellipse cx="{fmt(cxr + 0.25 * r)}" cy="{fmt(cyr - 0.45 * r)}" rx="{fmt(0.28 * r)}" ry="{fmt(0.2 * r)}" '
                     f'fill="#FFFFFF" fill-opacity="0.85"/>')
    return out + "\n" + "".join(faces)


# ====================================================================================== HEX LOCK
# Measured: purple hexagon (vertices left/right) 1.962 x 1.81 pitch, centred on the door (x) and 0.18 pitch below
# the frame bbox centre (y). A blue socket 0.093 around it (#3374BE, darker toward the hex). Bevel facets: top
# #DB61F9 (0.15), upper sides #C552EA, lower sides #9A37C2, bottom #8633AF (0.15); sides 0.093 at mid-height.
# Face #CC64E4 (top) -> #BB51DB -> #A444C9 (bottom) inside a 1 px light line. Keyhole: circle r 0.2 at y -0.19,
# tail to y +0.37 widening 0.22 -> 0.37; #7D35A2 with a dark top (#462166) and a light lower lip (#DB8EEB).
LOCK = dict(a=0.981, b=0.905, socket=0.093, bev_tb=0.15, bev_side=0.10, r=0.13,
            hole_cy=-0.20, hole_r=0.225, tail_y0=-0.08, tail_y1=0.42, tail_w0=0.24, tail_w1=0.40)


@skinned("lock")
def hex_lock(P=P0):
    u = 3 * P
    K = LOCK
    a, b = K["a"] * u, K["b"] * u
    m = K["socket"] * u + 0.06 * u
    W, H = frame_pt(2 * (a + m)), frame_pt(2 * (b + m))
    cx, cy = W * 1.5, H * 1.5
    s = K["socket"] * u
    sock = poly_path(hexagon(cx, cy, a + s, b + s * 0.9, (a + s) / 2, K["r"] * u * 1.6))
    outer_pts = hexagon(cx, cy, a, b, a / 2)
    ia, ib = a - K["bev_side"] * u * 1.15, b - K["bev_tb"] * u
    inner_pts = hexagon(cx, cy, ia, ib, a / 2 - 0.05 * u)
    outer = poly_path(_round_poly(outer_pts, K["r"] * u))
    inner = poly_path(_round_poly(inner_pts, K["r"] * u * 0.75))
    facet_col = ["#CB58EF", "#E36CFB", "#CB58EF", "#9331BC", "#7A2BA3", "#9331BC"]   # edges 0-1 (upper-left) ... 5-0
    defs = [blur("lsh", 0.03 * u), blur("lso", 0.012 * u),
            ulin("lface", [(0, "#CE67E6"), (0.45, "#BB51DB"), (1, "#A242C8")], 0, cy - ib, 0, cy + ib),
            ulin("lline", [(0, "#F7B0FC"), (0.5, "#DD82EF"), (1, "#B84FDB")], 0, cy - ib, 0, cy + ib),
            ulin("lsock", [(0, "#3A7BC6"), (0.55, "#3272BC"), (1, "#1F52A0")], 0, cy - b - s, 0, cy + b + s),
            ulin("lhole", [(0, "#44205F"), (0.3, "#62297F"), (0.45, "#7B34A0"), (1, "#7F36A3")],
                 0, cy + K["hole_cy"] * u - K["hole_r"] * u, 0, cy + K["tail_y1"] * u),
            f'<clipPath id="lco"><path d="{outer}"/></clipPath>']
    g = [f'<path d="{sock}" fill="url(#lsock)"/>',
         f'<path d="{poly_path(_round_poly(hexagon(cx, cy, a + 0.03 * u, b + 0.03 * u, (a + 0.03 * u) / 2), K["r"] * u))}" fill="#2C65B1"/>',
         f'<path d="{outer}" fill="#A032CD"/>']
    facets = []
    for i in range(6):
        p0, p1 = outer_pts[i], outer_pts[(i + 1) % 6]
        q0, q1 = inner_pts[i], inner_pts[(i + 1) % 6]
        facets.append(f'<path d="{poly_path([p0, p1, q1, q0])}" fill="{facet_col[i]}"/>')
    g.append(f'<g clip-path="url(#lco)">{"".join(facets)}</g>')
    g.append(f'<path d="{outer}" fill="none" stroke="#6A2090" stroke-opacity="0.8" stroke-width="{fmt(0.022 * u)}"/>')
    g.append(f'<path d="{inner}" fill="url(#lface)" stroke="url(#lline)" stroke-width="{fmt(0.03 * u)}"/>')
    # keyhole
    hr = K["hole_r"] * u
    hcy = cy + K["hole_cy"] * u
    t0, t1 = cy + K["tail_y0"] * u, cy + K["tail_y1"] * u
    w0, w1 = K["tail_w0"] * u / 2, K["tail_w1"] * u / 2
    rt = 0.04 * u
    tail = poly_path(_round_poly([(cx - w0, t0), (cx + w0, t0), (cx + w1, t1), (cx - w1, t1)], rt))
    hole = f'<circle cx="{fmt(cx)}" cy="{fmt(hcy)}" r="{fmt(hr)}"/><path d="{tail}"/>'
    g.append(f'<g fill="#DB8EEB" transform="translate(0 {fmt(0.03 * u)})">{hole}</g>')     # light lower lip
    g.append(f'<g fill="url(#lhole)">{hole}</g>')
    return svg_doc(W, H, "\n".join(g), "".join(defs)), dict(anchor=(W / 2, H / 2), note="anchor = lock centre = door frame "
                                                           "bbox centre + (0, 0.18 pitch)")


# ====================================================================================== KEY (on a key arrow)
# Measured on L33 (027, 53.5 px pitch; down key at cells (0,1)-(0,2), up key 180 deg, L34/L37 horizontal keys):
# bbox 1.03 x 2.20 pitch. Origin = the arrow's line (x) and the FIRST key cell's centre (y), pointing DOWN (toward the
# head). Ribbon loop x +-0.37, y -0.76..+0.16 (#C020FF..#D948FF); knot band x -0.13..+0.09, y -0.05..+0.17; ring
# centre (-0.03, 0.29), outer 0.93 x 0.78, hole 0.37 x 0.34; shaft x -0.25..+0.17, y 0.60..1.45; bit x 0.08..0.57,
# y 0.91..1.40. One sprite serves every direction (the capture's lighting rotates with it): down = as drawn, up = rotate
# 180, right = transpose (x <-> y: ribbon left, bit hanging below), left = INFERRED (right rotated 180).
KEY = dict(ring=(-0.03, 0.29, 0.465, 0.39, 0.185, 0.17), shaft=(-0.25, 0.17, 0.60, 1.45, 0.12),
           bit=(0.08, 0.57, 0.91, 1.40, 0.085), knot=(-0.14, 0.10, -0.07, 0.19),
           ribbon=dict(top=-0.76, bottom=0.10, half=0.37, width=0.155))


@skinned("key")
def key(P=P0):
    u = 3 * P
    Kk = KEY
    mx0, mx1, my0, my1 = -0.62, 0.72, -0.86, 1.56          # frame extents (pitch) incl. the shadow
    W, H = frame_pt((mx1 - mx0) * u), frame_pt((my1 - my0) * u)
    ox, oy = -mx0 * u, -my0 * u                            # anchor in px
    X = lambda v: ox + v * u
    Y = lambda v: oy + v * u
    rcx, rcy, rrx, rry, hrx, hry = Kk["ring"]
    sx0, sx1, sy0, sy1, sr = Kk["shaft"]
    bx0, bx1, by0, by1, br = Kk["bit"]
    kx0, kx1, ky0, ky1 = Kk["knot"]
    rb = Kk["ribbon"]
    # ribbon: a teardrop loop from the knot up around the arrow line and back (a thick stroke, hole = transparent)
    top, bot, half, wid = rb["top"] * u, rb["bottom"] * u, rb["half"] * u, rb["width"] * u
    cyl = (top + bot) / 2
    hw = half / u - wid / u / 2                           # centre-line half width
    ty = (top + wid / 2) / u                              # centre-line top
    loop = (f'M{fmt(X(-0.02))} {fmt(Y(0.10))} C{fmt(X(-hw * 1.38))} {fmt(Y(-0.10))} {fmt(X(-hw * 1.24))} {fmt(Y(ty))} {fmt(X(0))} {fmt(Y(ty))} '
            f'C{fmt(X(hw * 1.24))} {fmt(Y(ty))} {fmt(X(hw * 1.38))} {fmt(Y(-0.10))} {fmt(X(0.02))} {fmt(Y(0.10))}')
    ring_o = f'<ellipse cx="{fmt(X(rcx))}" cy="{fmt(Y(rcy))}" rx="{fmt(rrx * u)}" ry="{fmt(rry * u)}"/>'
    ring_path = (f'M{fmt(X(rcx - rrx))} {fmt(Y(rcy))} a{fmt(rrx * u)} {fmt(rry * u)} 0 1 0 {fmt(2 * rrx * u)} 0 '
                 f'a{fmt(rrx * u)} {fmt(rry * u)} 0 1 0 {fmt(-2 * rrx * u)} 0 Z '
                 f'M{fmt(X(rcx - hrx))} {fmt(Y(rcy))} a{fmt(hrx * u)} {fmt(hry * u)} 0 1 1 {fmt(2 * hrx * u)} 0 '
                 f'a{fmt(hrx * u)} {fmt(hry * u)} 0 1 1 {fmt(-2 * hrx * u)} 0 Z')
    shaft = rrect(X(sx0), Y(sy0), X(sx1), Y(sy1), 0.02 * u, 0.02 * u, sr * u, sr * u)
    bit = rrect(X(bx0), Y(by0), X(bx1), Y(by1), br * u)
    knot = rrect(X(kx0), Y(ky0), X(kx1), Y(ky1), 0.05 * u)
    defs = [blur("ksh", 0.035 * u), blur("ks1", 0.012 * u), blur("ks2", 0.025 * u),
            # torus: dark at the hole and the outer edge, light on the tube's crown; lit from the upper left
            urad("kring", [(0, "#B35A00"), (hrx / rrx * 0.98, "#C86A04"), (hrx / rrx + 0.08, "#F5B21E"),
                           (0.66, "#FFC93A"), (0.82, "#F7AE17"), (1, "#D27A06")], X(rcx), Y(rcy), rrx * u),
            ulin("kshaft", [(0, "#E59612"), (0.14, "#FFE9A0"), (0.3, "#F9C63C"), (0.62, "#F4B11C"), (0.86, "#E08A0A"),
                            (1, "#C96A04")], X(sx0), 0, X(sx1), 0),
            ulin("kbit", [(0, "#FFD458"), (0.35, "#F7BD2A"), (1, "#E08A0A")], X(bx0), Y(by0), X(bx1), Y(by1)),
            ulin("krib", [(0, "#C52BFF"), (0.5, "#D94BFF"), (1, "#B61CF3")], X(-half / u), 0, X(half / u), 0),
            ulin("kknot", [(0, "#B51BF2"), (0.4, "#D64AFF"), (1, "#A416DE")], X(kx0), 0, X(kx1), 0),
            f'<clipPath id="kcr"><path d="{ring_path}" clip-rule="evenodd"/></clipPath>']
    g = []
    # soft drop shadow of the whole key (down-right)
    g.append(f'<g filter="url(#ksh)" transform="translate({fmt(0.03 * u)} {fmt(0.05 * u)})" fill="#3A2A20" fill-opacity="0.28">'
             f'<path d="{loop}" fill="none" stroke="#3A2A20" stroke-width="{fmt(wid)}"/>'
             f'<path d="{ring_path}" fill-rule="evenodd"/><path d="{shaft}"/><path d="{bit}"/></g>')
    # ribbon loop (behind the ring), with a darker inner edge and a light outer sheen
    g.append(f'<path d="{loop}" fill="none" stroke="#9A10D0" stroke-width="{fmt(wid + 0.03 * u)}" stroke-linecap="round"/>'
             f'<path d="{loop}" fill="none" stroke="url(#krib)" stroke-width="{fmt(wid)}" stroke-linecap="round"/>'
             f'<path d="{loop}" fill="none" stroke="#EE9BFF" stroke-opacity="0.55" stroke-width="{fmt(0.035 * u)}" '
             f'transform="translate({fmt(-0.02 * u)} {fmt(-0.02 * u)})" filter="url(#ks1)"/>')
    # bit, then shaft (the shaft sits in front of the bit's left edge)
    g.append(f'<path d="{bit}" fill="url(#kbit)" stroke="#C86A08" stroke-width="{fmt(0.015 * u)}"/>'
             f'<path d="{rrect(X(bx0) + 0.05 * u, Y(by0) + 0.04 * u, X(bx1) - 0.08 * u, Y(by0) + 0.09 * u, 0.02 * u)}" fill="#FFE48A" fill-opacity="0.7" filter="url(#ks1)"/>')
    g.append(f'<path d="{shaft}" fill="url(#kshaft)" stroke="#C86A08" stroke-width="{fmt(0.012 * u)}"/>')
    # ring (torus)
    g.append(f'<path d="{ring_path}" fill="url(#kring)" fill-rule="evenodd"/>')
    g.append(f'<g clip-path="url(#kcr)"><ellipse cx="{fmt(X(rcx - 0.12))}" cy="{fmt(Y(rcy - 0.2))}" rx="{fmt(0.2 * u)}" ry="{fmt(0.07 * u)}" '
             f'transform="rotate(-28 {fmt(X(rcx - 0.12))} {fmt(Y(rcy - 0.2))})" fill="#FFF6C8" fill-opacity="0.85" filter="url(#ks2)"/></g>')
    g.append(f'<path d="{ring_path}" fill="none" fill-rule="evenodd" stroke="#C06204" stroke-opacity="0.6" stroke-width="{fmt(0.012 * u)}"/>')
    # knot band over the ring top
    g.append(f'<path d="{knot}" fill="url(#kknot)" stroke="#8E0FC4" stroke-width="{fmt(0.012 * u)}"/>'
             f'<rect x="{fmt(X(kx0 + 0.04))}" y="{fmt(Y(ky0 + 0.03))}" width="{fmt(0.04 * u)}" height="{fmt((ky1 - ky0 - 0.06) * u)}" '
             f'rx="{fmt(0.02 * u)}" fill="#F0A8FF" fill-opacity="0.7" filter="url(#ks1)"/>')
    return svg_doc(W, H, "\n".join(g), "".join(defs)), dict(anchor=(ox / 3, oy / 3), note="anchor = arrow line (x) and the "
                                                            "centre of the key's first cell on the tail side (y); sprite points DOWN")


# ====================================================================================== PIPE mouth + counter
# Measured on L35 (042, pitch 84.2 px; STYLE §A.2): the tube itself is CODE (CAShapeLayer); these are the two sprites.
# Mouth, drawn for a pipe end that opens DOWN (rotate for the other three): a gold collar 1.22 across x 0.61 along, centred
# 0.10 outward from the end cell's centre (along -0.20 .. +0.40); the opening on the outward face = an ellipse whose
# visible interior spans along +0.15 .. +0.35 (#722F00 far side -> #E97F01), the near lip +0.34 .. +0.40; the collar face
# above it #FEF3A6 -> #FAAF05 (a rim line at +0.12 .. +0.14); grey drop shadow below. Origin (anchor) = the end cell centre.
PIPE_MOUTH = dict(half=0.61, y0=-0.20, y1=0.40, open_y0=0.15, open_y1=0.35, lip=0.05)   # round 2: rounded ring


@skinned("pipeMouth")
def pipe_mouth(P=P0):
    u = 3 * P
    K = PIPE_MOUTH
    mx0, mx1, my0, my1 = -0.72, 0.72, -0.30, 0.62
    W, H = frame_pt((mx1 - mx0) * u), frame_pt((my1 - my0) * u)
    ox, oy = -mx0 * u, -my0 * u
    X = lambda v: ox + v * u
    Y = lambda v: oy + v * u
    hw = K["half"] * u
    r_end = 0.10 * u
    collar = rrect(X(-K["half"]), Y(K["y0"]), X(K["half"]), Y(K["y1"]), 0.14 * u, 0.14 * u, 0.26 * u, 0.26 * u)
    ocy = Y((K["open_y0"] + K["open_y1"]) / 2 + 0.02)
    orx, ory = hw - 0.10 * u, ((K["open_y1"] - K["open_y0"]) / 2 + 0.01) * u
    defs = [blur("pmsh", 0.04 * u), blur("pms1", 0.01 * u),
            # cylinder shading across the collar (lit from the upper right: bright band right of centre)
            ulin("pmface", [(0, "#D9860A"), (0.12, "#F2A20C"), (0.35, "#FCC83A"), (0.62, "#FEF0A0"), (0.74, "#FFF7CF"),
                            (0.86, "#FCD04A"), (1, "#E0900A")], X(-K["half"]), 0, X(K["half"]), 0),
            ulin("pmopen", [(0, "#6E2D01"), (0.45, "#A94E01"), (1, "#E98001")], 0, ocy - ory, 0, ocy + ory),
            f'<clipPath id="pmc"><path d="{collar}"/></clipPath>']
    g = [f'<g filter="url(#pmsh)" transform="translate({fmt(-0.02 * u)} {fmt(0.10 * u)})" fill="#2A2A2A" fill-opacity="0.32">'
         f'<path d="{collar}"/></g>',
         f'<path d="{collar}" fill="url(#pmface)" stroke="#C06A06" stroke-width="{fmt(0.012 * u)}"/>',
         f'<g clip-path="url(#pmc)">'
         # rim line above the opening + a warm band along the far edge
         f'<rect x="{fmt(X(-K["half"]))}" y="{fmt(Y(0.115))}" width="{fmt(2 * hw)}" height="{fmt(0.03 * u)}" fill="#E8900A" fill-opacity="0.8"/>'
         f'<rect x="{fmt(X(-K["half"]))}" y="{fmt(Y(K["y0"]))}" width="{fmt(2 * hw)}" height="{fmt(0.035 * u)}" fill="#FFF6C8" '
         f'fill-opacity="0.7" filter="url(#pms1)"/></g>',
         # the opening: dark interior ellipse, then the near lip covering its lower edge
         f'<ellipse cx="{fmt(X(0))}" cy="{fmt(ocy)}" rx="{fmt(orx)}" ry="{fmt(ory)}" fill="url(#pmopen)"/>',
         f'<path d="M{fmt(X(0) - orx)} {fmt(ocy)} A{fmt(orx)} {fmt(ory)} 0 0 0 {fmt(X(0) + orx)} {fmt(ocy)} '
         f'L{fmt(X(K["half"]) - 0.02 * u)} {fmt(Y(K["y1"]) - 0.02 * u)} L{fmt(X(-K["half"]) + 0.02 * u)} {fmt(Y(K["y1"]) - 0.02 * u)} Z" '
         f'fill="none"/>',
         f'<path d="M{fmt(X(0) - orx)} {fmt(ocy + 0.01 * u)} A{fmt(orx)} {fmt(ory)} 0 0 0 {fmt(X(0) + orx)} {fmt(ocy + 0.01 * u)}" '
         f'fill="none" stroke="#FCD65C" stroke-width="{fmt(0.045 * u)}" stroke-linecap="round"/>']
    return svg_doc(W, H, "\n".join(g), "".join(defs)), dict(anchor=(ox / 3, oy / 3), note="anchor = the end cell's centre; "
                                                            "drawn for a mouth opening DOWN (rotate 90/180/270 for left/up/right)")


# Counter, drawn for a HORIZONTAL run (sheet m_pipeCounter round 2 layout): a narrow gold collar 0.25 wide x 1.05 tall
# at each end, between them a gold FRAME 1.40 x 1.33 (r 0.16) holding the orange face 1.04 x 1.12 (#CD4D00: top band
# #BC3200 with a #A92403 edge, mid #E66B00, a lighter inset bevel); total 1.90 x 1.33 centred on the tube line. The number
# is LIVE text (white, #822521 outline), never baked. Anchor = the box centre; a vertical run uses it rotated 90.
PIPE_COUNTER = dict(total_w=1.90, total_h=1.33, frame_w=1.40, face_w=1.04, face_h=1.12, collar_w=0.25, collar_h=1.05)


@skinned("pipeCounter")
def pipe_counter(P=P0):
    u = 3 * P
    K = PIPE_COUNTER
    W, H = frame_pt((K["total_w"] + 0.2) * u), frame_pt((K["total_h"] + 0.3) * u)
    cx, cy = W * 1.5, H * 1.5 - 0.05 * u
    th, fw, fh = K["total_h"] * u, K["face_w"] * u, K["face_h"] * u
    frw, cw, ch = K["frame_w"] * u, K["collar_w"] * u, K["collar_h"] * u
    defs = [blur("pcsh", 0.04 * u), blur("pcs1", 0.012 * u),
            ulin("pcface", [(0, "#A92403"), (0.04, "#BC3200"), (0.3, "#C83D00"), (0.55, "#E26500"), (0.7, "#E66B00"),
                            (0.92, "#C63C00"), (1, "#AB2503")], 0, cy - fh / 2, 0, cy + fh / 2),
            ulin("pcfr", [(0, "#E08A06"), (0.08, "#FAD151"), (0.2, "#F6B81F"), (0.5, "#F0A606"), (0.85, "#EF9A06"),
                          (0.93, "#FCD454"), (1, "#D07A05")], 0, cy - th / 2, 0, cy + th / 2),
            ulin("pccol", [(0, "#DC8404"), (0.12, "#F6B81F"), (0.35, "#FDF2AB"), (0.6, "#FEED82"), (0.85, "#F0A606"),
                           (1, "#D87E04")], 0, cy - ch / 2, 0, cy + ch / 2)]
    frame = rrect(cx - frw / 2, cy - th / 2, cx + frw / 2, cy + th / 2, 0.16 * u)
    face = rrect(cx - fw / 2, cy - fh / 2, cx + fw / 2, cy + fh / 2, 0.07 * u)
    cols = [rrect(x0, cy - ch / 2, x0 + cw, cy + ch / 2, 0.06 * u) for x0 in (cx - K["total_w"] * u / 2, cx + K["total_w"] * u / 2 - cw)]
    g = [f'<g filter="url(#pcsh)" transform="translate({fmt(-0.02 * u)} {fmt(0.10 * u)})" fill="#2A2A2A" fill-opacity="0.32">'
         f'<path d="{frame}"/>' + "".join(f'<path d="{c}"/>' for c in cols) + '</g>']
    for c in cols:
        g.append(f'<path d="{c}" fill="url(#pccol)" stroke="#C06A06" stroke-width="{fmt(0.012 * u)}"/>')
    for x0 in (cx - K["total_w"] * u / 2, cx + K["total_w"] * u / 2 - cw):   # a vertical glint on each collar
        g.append(f'<rect x="{fmt(x0 + 0.08 * u)}" y="{fmt(cy - ch / 2 + 0.1 * u)}" width="{fmt(0.05 * u)}" height="{fmt(ch - 0.2 * u)}" '
                 f'rx="{fmt(0.025 * u)}" fill="#FFFBE6" fill-opacity="0.7" filter="url(#pcs1)"/>')
    g += [f'<path d="{frame}" fill="url(#pcfr)" stroke="#C06A06" stroke-width="{fmt(0.014 * u)}"/>',
          f'<path d="{face}" fill="url(#pcface)" stroke="#8E2A06" stroke-width="{fmt(0.02 * u)}"/>',
          f'<path d="{rrect(cx - fw / 2 + 0.06 * u, cy - fh / 2 + 0.06 * u, cx + fw / 2 - 0.06 * u, cy + fh / 2 - 0.06 * u, 0.05 * u)}" '
          f'fill="none" stroke="#F07A12" stroke-opacity="0.5" stroke-width="{fmt(0.022 * u)}"/>']
    return svg_doc(W, H, "\n".join(g), "".join(defs)), dict(anchor=(cx / 3, cy / 3), note="anchor = the counter's centre; the "
                                                             "number is live text")


# ====================================================================================== CURTAIN counter block (V1 skin)
# Measured on the owner's video V1 (Aug build, L11, t 186 s; 592 px frame, pitch 42.5 px; looked at only): a 3 x 3-cell
# block (2.94 pitch, centred on the block), purple rounded square r ~0.45 (top edge #FDDFFF -> #E899F4, face #B453EE ..
# #C36AF8, lower band #592F95 -> #3E2C68 at the bottom), holding a SILVER sphere r 1.08 (lit top-left #E5F2FB, edge
# #7C86C4 -> #48498C lower right, a reflected-light crescent #CFE1FF along the bottom) with FOUR cylindrical lugs on the
# diagonals out to r 1.38, and a round window: purple ring r 0.70 (#5D46AE -> #C698FF at the top) around a navy well r 0.53
# (#142C6A .. #1F3C80). The counter is LIVE text in the well (white, dark outline). Anchor = top-left of the 3 x 3 cells.
CURTAIN = dict(half=1.47, r=0.45, sphere=1.07, lug_r0=0.80, lug_r1=1.36, lug_w=0.58, ring=0.68, well=0.53)   # round 3


@skinned("crate")
def curtain_crate(P=P0, wc=3, hc=3):
    """wc x hc cells (L11: 3 x 3; the videos also show ~2 x 2 and tall 1 x 3 variants): the block fills the cells less a
    0.03-pitch gap per side; the sphere, lugs and window scale with min(wc, hc) / 3 and sit at the block centre."""
    u = 3 * P
    K = CURTAIN
    m = 4 * 3.0                                   # 4 pt margin (shadow)
    W, H = int(round(wc * P + 2 * m / 3)), int(round(hc * P + 2 * m / 3))
    cx, cy = m + wc / 2 * u, m + hc / 2 * u
    sc = min(wc, hc) / 3.0
    hx, hy = (wc / 2 - 0.03) * u, (hc / 2 - 0.03) * u
    h = min(hx, hy)
    blk = rrect(cx - hx, cy - hy, cx + hx, cy + hy, K["r"] * u * max(sc, 0.6))
    u_s = u * sc                                  # scale of the sphere assembly
    rs, rr, rw = K["sphere"] * u_s, K["ring"] * u_s, K["well"] * u_s
    defs = [blur("csh", 0.05 * u), blur("cs1", 0.015 * u), blur("cs2", 0.04 * u),
            ulin("cblk", [(0, "#F2B8FF"), (0.03, "#DD84FA"), (0.1, "#C168F8"), (0.55, "#AF55EC"), (0.84, "#8846C2"),
                          (0.93, "#592F95"), (1, "#3E2C68")], 0, cy - hy, 0, cy + hy),
            ulin("cside", [(0, "#6431B2", 0.9), (0.12, "#9044E5", 0), (0.88, "#C36AF8", 0), (1, "#653DBA", 0.9)], cx - hx, 0, cx + hx, 0),
            urad("csph", [(0, "#F4F8FF"), (0.35, "#D2DCF6"), (0.7, "#9FA9DC"), (0.9, "#6F78B8"), (1, "#4E4F92")],
                 cx - 0.35 * rs, cy - 0.4 * rs, 1.25 * rs),
            ulin("clug", [(0, "#F6F9FF"), (0.45, "#C9D3F2"), (1, "#7E88C2")], 0, 0, 0, 1),
            ulin("cring", [(0, "#C698FF"), (0.35, "#A270E8"), (0.7, "#6A52BC"), (1, "#4C3AA0")], 0, cy - rr, 0, cy + rr),
            urad("cwell", [(0, "#24468A"), (0.6, "#1A3372"), (1, "#101F52")], cx, cy + 0.15 * rw, rw),
            f'<clipPath id="cclip"><path d="{blk}"/></clipPath>',
            f'<clipPath id="csphc"><circle cx="{fmt(cx)}" cy="{fmt(cy)}" r="{fmt(rs)}"/></clipPath>']
    g = [f'<g filter="url(#csh)" transform="translate(0 {fmt(0.07 * u)})"><path d="{blk}" fill="#2A1A48" fill-opacity="0.45"/></g>',
         f'<path d="{blk}" fill="url(#cblk)"/>',
         f'<path d="{blk}" fill="url(#cside)"/>',
         f'<g clip-path="url(#cclip)"><path d="{rrect(cx - hx + 0.08 * u, cy - hy + 0.05 * u, cx + hx - 0.08 * u, cy - hy + 0.13 * u, 0.04 * u)}" '
         f'fill="#FFE6FF" fill-opacity="0.75" filter="url(#cs1)"/></g>',
         f'<path d="{blk}" fill="none" stroke="#3A2466" stroke-opacity="0.55" stroke-width="{fmt(0.02 * u)}"/>']
    # lugs: short CYLINDERS on the diagonals (round 2: m_curtainCrate round 1 hid them behind the sphere); body shaded
    # across (light on the upper-left side), a lighter elliptical end cap; drawn under the sphere (they grow out of it)
    lw, l0, l1 = K["lug_w"] * u_s, K["lug_r0"] * u_s, K["lug_r1"] * u_s
    defs.append(ulin("clugb", [(0, "#EEF3FF"), (0.35, "#C6D0F0"), (0.75, "#8C96CC"), (1, "#5E659F")], -lw / 2, 0, lw / 2, 0))
    for ang in (45, 135, 225, 315):
        body = f'M{fmt(-lw / 2)} {fmt(l0)} L{fmt(lw / 2)} {fmt(l0)} L{fmt(lw / 2)} {fmt(l1)} L{fmt(-lw / 2)} {fmt(l1)} Z'
        flip = ' scale(-1 1)' if ang in (45, 315) else ''       # keep the lit side facing up-left on every lug
        g.append(f'<g transform="translate({fmt(cx)} {fmt(cy)}) rotate({ang - 90}){flip}">'
                 f'<path d="{body}" fill="#2E2A66" fill-opacity="0.45" filter="url(#cs1)" transform="translate(0 {fmt(0.04 * u)})"/>'
                 f'<path d="{body}" fill="url(#clugb)" stroke="#565C9A" stroke-width="{fmt(0.016 * u)}"/>'
                 f'<ellipse cx="0" cy="{fmt(l1)}" rx="{fmt(lw / 2)}" ry="{fmt(0.13 * u)}" fill="#DCE4FA" stroke="#6F77B2" '
                 f'stroke-width="{fmt(0.016 * u)}"/>'
                 f'<ellipse cx="{fmt(-0.06 * u)}" cy="{fmt(l1 - 0.02 * u)}" rx="{fmt(lw * 0.3)}" ry="{fmt(0.06 * u)}" fill="#FFFFFF" '
                 f'fill-opacity="0.7" filter="url(#cs1)"/></g>')
    # sphere
    g.append(f'<circle cx="{fmt(cx)}" cy="{fmt(cy + 0.05 * u)}" r="{fmt(rs)}" fill="#2E2466" fill-opacity="0.5" filter="url(#cs2)"/>')
    g.append(f'<circle cx="{fmt(cx)}" cy="{fmt(cy)}" r="{fmt(rs)}" fill="url(#csph)" stroke="#50509A" stroke-width="{fmt(0.02 * u)}"/>')
    g.append(f'<g clip-path="url(#csphc)"><path d="M{fmt(cx - 0.8 * rs)} {fmt(cy + 0.62 * rs)} A{fmt(rs)} {fmt(rs)} 0 0 0 {fmt(cx + 0.8 * rs)} '
             f'{fmt(cy + 0.62 * rs)}" fill="none" stroke="#D6E6FF" stroke-opacity="0.85" stroke-width="{fmt(0.07 * u)}" filter="url(#cs1)"/></g>')
    # window: ring + navy well
    g.append(f'<circle cx="{fmt(cx)}" cy="{fmt(cy)}" r="{fmt(rr)}" fill="url(#cring)" stroke="#433595" stroke-width="{fmt(0.02 * u)}"/>')
    g.append(f'<circle cx="{fmt(cx)}" cy="{fmt(cy)}" r="{fmt(rw)}" fill="url(#cwell)" stroke="#0E1946" stroke-width="{fmt(0.02 * u)}"/>')
    g.append(f'<path d="M{fmt(cx - 0.75 * rw)} {fmt(cy - 0.35 * rw)} A{fmt(rw * 0.85)} {fmt(rw * 0.85)} 0 0 1 {fmt(cx + 0.6 * rw)} '
             f'{fmt(cy - 0.62 * rw)}" fill="none" stroke="#6C86D6" stroke-opacity="0.45" stroke-width="{fmt(0.04 * u)}" '
             f'stroke-linecap="round" filter="url(#cs1)"/>')
    return svg_doc(W, H, "\n".join(g), "".join(defs)), dict(anchor=(m / 3, m / 3), note="anchor = top-left of the 3 x 3 cells; "
                                                             "the counter is live text centred on the block")


# ====================================================================================== the phone BOX (v552; director round 2)
# SPEC.md 5.11: every counter level uses the PHONE's Box skin (135 L50 at pitch 28.07, meta-062; looked at only). Grader A
# graded round 1's curtain crate C: no corner studs, a dark shaded body, and a sphere that GREW with the block (a 10 x 9 box
# got a huge sphere). The phone draws a flat violet slab that covers its cell block exactly + a counter ring of a FIXED
# size at the block centre. So the skin is two sprites (SPEC-ui 4.3): boxSlab (any W x H: authored at 3 x 3 cells and
# 9-sliced by the engine with cap insets 0.5 pitch + the 4 pt shadow margin, or rendered at a size with box_slab(w, h))
# and boxRing (one sprite, 2.2 pitch across its sphere; the counter is live text in the well).
# Measured on 135 (3 px/pt, pitch 84.2 px): slab corner r 0.40 pitch; face #BC5BF6 flat; a light top line (#E9A6F6)
# 0.04 pitch; the side edges darken over 0.26 pitch (#5935A2 at the edge); bottom lip 0.28 pitch #AB50EB -> #582D96 ->
# #4F2F83; a soft grey shadow 0.1 pitch below; four rivet domes d 0.31 pitch centred 0.50 pitch in from both edges (lighter
# lilac top #E7B3FA, darker lower rim #7D35B8). Ring: silver sphere r 0.98 pitch (lit top-left #EEF4FF, #9DA7D8 mid, #545A9C
# lower right), four stubby lugs on the diagonals from r 0.62 to 1.40 (w 0.52, domed light end caps), a purple ring r 0.70
# (#C698FF top -> #5D46AE), a navy-teal well r 0.50 (#1F4C7C .. #142C6A).
BOXS = dict(r=0.40, top=0.07, side=0.26, lip=0.28, rivet_d=0.31, rivet_in=0.50, shadow=0.10)
BOXR = dict(sphere=0.98, lug_r0=0.62, lug_r1=1.37, lug_w=0.62, ring=0.72, well=0.50)
# to-A r4, radial profiles on 135 (pitch 28.07) through the well's centre (195.65, 649.4): silver sphere r 28.9 pt =
# 1.03 pitch (horizontal extents 166.8-224.5), purple ring outer 18.5 = 0.66, well 14.2 = 0.51; along the diagonals
# the lug ends at 36.6 pt = 1.30 (round 3: 1.40); the lugs point out AND toward the viewer, so their light end discs
# (~15 x 10 pt) sit IN FRONT of the sphere's edge; lug 17.5 pt = 0.62 wide at r 33, body blue-grey (#B7C7E8); the
# sphere reads whiter than round 3's. The frame stays 76 pt (reach 1.37).
BOXR_R4 = dict(sphere=1.03, ring=0.66, well=0.51, lug_r1=1.275, cap_ry=0.31, frame_reach=1.37, sphere_light=True,
               caps_front=True, cap_k=1.15)


@skinned("boxSlab")
def box_slab(wc=3, hc=3, P=P0, rivets=True, **over):
    """over: BOXS overrides (the unlock card's bigger icon: rounder corners, a stronger top bevel, no rivets on 134)."""
    u = 3 * P
    K = dict(BOXS, **over)
    m = 4 * 3.0                                   # 4 pt margin for the shadow
    W, H = int(round(wc * P + 2 * m / 3)), int(round(hc * P + 2 * m / 3))
    x0, y0, x1, y1 = m, m, m + wc * u, m + hc * u
    r = K["r"] * u
    blk = rrect(x0, y0, x1, y1, r)
    lip = K["lip"] * u
    defs = [blur("bsh", 0.05 * u), blur("bs1", 0.012 * u),
            ulin("bface", [(0, "#ECB2F3"), (min(0.99, K["top"] * u / (y1 - y0)), "#E89FF4"),
                           (min(0.99, 2.2 * K["top"] * u / (y1 - y0)), "#BC5BF6"), (1, "#BC5BF6")], 0, y0, 0, y1),
            ulin("blip", [(0, "#AB50EB"), (0.55, "#6E36B2"), (1, "#4F2F83")], 0, y1 - lip, 0, y1),
            ulin("bside", [(0, "#5935A2", 0.95), (K["side"] * u / (x1 - x0), "#BC5BF6", 0),
                           (1 - K["side"] * u / (x1 - x0), "#BC5BF6", 0), (1, "#5935A2", 0.95)], x0, 0, x1, 0),
            f'<clipPath id="bclip"><path d="{blk}"/></clipPath>']
    g = [f'<g filter="url(#bsh)" transform="translate(0 {fmt(K["shadow"] * u)})"><path d="{blk}" fill="#3A3450" fill-opacity="0.38"/></g>',
         f'<path d="{blk}" fill="url(#bface)"/>',
         f'<g clip-path="url(#bclip)"><rect x="{fmt(x0)}" y="{fmt(y1 - lip)}" width="{fmt(x1 - x0)}" height="{fmt(lip)}" '
         f'fill="url(#blip)"/>'
         f'<rect x="{fmt(x0)}" y="{fmt(y0)}" width="{fmt(x1 - x0)}" height="{fmt(y1 - y0)}" fill="url(#bside)"/>'
         f'<path d="M{fmt(x0 + r * 0.6)} {fmt(y1 - lip)} L{fmt(x1 - r * 0.6)} {fmt(y1 - lip)}" stroke="#D07DF8" '
         f'stroke-opacity="0.55" stroke-width="{fmt(0.02 * u)}" filter="url(#bs1)"/></g>',
         f'<path d="{blk}" fill="none" stroke="#4B2A86" stroke-opacity="0.55" stroke-width="{fmt(0.018 * u)}"/>']
    rd, ri = K["rivet_d"] * u, K["rivet_in"] * u
    defs.append(urad("briv", [(0, "#F6DDFF"), (0.35, "#E0A6F8"), (0.75, "#B25AE8"), (1, "#7D35B8")], 0, 0, rd * 0.62,
                     fx=-rd * 0.18, fy=-rd * 0.2))
    for cx, cy in ((x0 + ri, y0 + ri), (x1 - ri, y0 + ri), (x0 + ri, y1 - ri - 0.04 * u), (x1 - ri, y1 - ri - 0.04 * u))[:4 if rivets else 0]:
        g.append(f'<g transform="translate({fmt(cx)} {fmt(cy)})">'
                 f'<circle cx="0" cy="{fmt(0.03 * u)}" r="{fmt(rd / 2)}" fill="#4B2280" fill-opacity="0.45" filter="url(#bs1)"/>'
                 f'<circle cx="0" cy="0" r="{fmt(rd / 2)}" fill="url(#briv)" stroke="#6A2BA6" stroke-width="{fmt(0.012 * u)}"/></g>')
    return svg_doc(W, H, "\n".join(g), "".join(defs)), dict(
        anchor=(m / 3, m / 3), note=f"anchor = top-left of the {wc} x {hc} cells; 9-slice cap insets 0.5 pitch + 4 pt margin")


@skinned("boxRing")
def box_ring(P=P0):
    """The counter ring (fixed size; the engine centres it on the block and puts the live counter in the well)."""
    u = 3 * P
    K = dict(BOXR, **BOXR_R4)
    half = K.get("frame_reach", K["lug_r1"]) * 0.72 + 0.1   # the lugs' diagonal reach, per axis, + the caps (frame kept)
    m = 3 * 3.0
    W = H = int(math.ceil(2 * (half * P) + 2 * m / 3))
    cx = cy = W * 1.5
    rs, rr, rw = K["sphere"] * u, K["ring"] * u, K["well"] * u
    defs = [blur("rs1", 0.015 * u), blur("rs2", 0.045 * u),
            urad("rsph", [(0, "#F8FBFF"), (0.32, "#E6ECFA"), (0.66, "#B3BEE6"), (0.88, "#8590C8"), (1, "#5E66A8")] if K.get("sphere_light") else
                 [(0, "#F6FAFF"), (0.32, "#DCE4F8"), (0.66, "#A3ADDC"), (0.88, "#737BBA"), (1, "#545A9C")],
                 cx - 0.35 * rs, cy - 0.42 * rs, 1.3 * rs),
            ulin("rring", [(0, "#C698FF"), (0.35, "#A270E8"), (0.7, "#6A52BC"), (1, "#4C3AA0")], 0, cy - rr, 0, cy + rr),
            urad("rwell", [(0, "#24528A"), (0.6, "#1B3F76"), (1, "#122A62")], cx, cy + 0.15 * rw, rw),
            f'<clipPath id="rsphc"><circle cx="{fmt(cx)}" cy="{fmt(cy)}" r="{fmt(rs)}"/></clipPath>']
    lw, l0, l1 = K["lug_w"] * u, K["lug_r0"] * u, K["lug_r1"] * u
    defs.append(ulin("rlugb", [(0, "#E6EDFB"), (0.35, "#C2CFEE"), (0.75, "#8E9ACC"), (1, "#646AA6")], -lw / 2, 0, lw / 2, 0))
    ck0, cry0 = K.get("cap_k", 1.0), K.get("cap_k", 1.0) * lw * K.get("cap_ry", 0.30)
    defs.append(ulin("rcapf", [(0, "#A4B2DE"), (0.45, "#CBD6F2"), (1, "#EEF3FD")], 0, K["lug_r1"] * u - lw * 0.25 - cry0, 0,
                     K["lug_r1"] * u - lw * 0.25 + cry0))
    g = [f'<circle cx="{fmt(cx)}" cy="{fmt(cy + 0.08 * u)}" r="{fmt(rs * 1.02)}" fill="#2E2466" fill-opacity="0.45" filter="url(#rs2)"/>']
    caps = []
    for ang in (45, 135, 225, 315):
        body = f'M{fmt(-lw / 2)} {fmt(l0)} L{fmt(lw / 2)} {fmt(l0)} L{fmt(lw / 2)} {fmt(l1 - lw * 0.25)} L{fmt(-lw / 2)} {fmt(l1 - lw * 0.25)} Z'
        flip = ' scale(-1 1)' if ang in (45, 315) else ''
        ck = K.get("cap_k", 1.0)          # to-A r4: 135's end discs read ~15 % wider than the lug body (the fillet)
        cap = (f'<ellipse cx="0" cy="{fmt(l1 - lw * 0.25)}" rx="{fmt(ck * lw / 2)}" ry="{fmt(ck * lw * K.get("cap_ry", 0.30))}" fill="#E4EAFC" stroke="#6F77B2" '
               f'stroke-width="{fmt(0.016 * u)}"/>'
               f'<ellipse cx="{fmt(-0.05 * u)}" cy="{fmt(l1 - lw * 0.3)}" rx="{fmt(lw * 0.28)}" ry="{fmt(lw * 0.13)}" fill="#FFFFFF" '
               f'fill-opacity="0.75" filter="url(#rs1)"/>')
        tr = f'translate({fmt(cx)} {fmt(cy)}) rotate({ang - 90}){flip}'
        if K.get("caps_front"):   # to-A r4: the end discs sit in front of the sphere's edge (135)
            g.append(f'<g transform="{tr}"><path d="{body}" fill="url(#rlugb)" stroke="#5A609E" stroke-width="{fmt(0.016 * u)}"/></g>')
            # a stubby cylinder seen from outside-and-above: its side shows on the sphere's side of the end disc (135),
            # blue-grey, then the disc itself shaded light at the outer rim -> blue-grey toward the sphere
            ccy, crx, cry, dep = l1 - lw * 0.25, ck * lw / 2, ck * lw * K.get("cap_ry", 0.30), 0.13 * u
            side = (f'M{fmt(-crx)} {fmt(ccy)} L{fmt(-crx)} {fmt(ccy - dep)} A{fmt(crx)} {fmt(cry)} 0 0 1 {fmt(crx)} {fmt(ccy - dep)} '
                    f'L{fmt(crx)} {fmt(ccy)} A{fmt(crx)} {fmt(cry)} 0 0 0 {fmt(-crx)} {fmt(ccy)} Z')
            side = (f'<ellipse cx="0" cy="{fmt(ccy - dep)}" rx="{fmt(crx)}" ry="{fmt(cry)}" fill="url(#rlugb)" stroke="#5A609E" '
                    f'stroke-width="{fmt(0.016 * u)}"/><path d="{side}" fill="url(#rlugb)" stroke="none"/>'
                    f'<path d="M{fmt(-crx)} {fmt(ccy)} L{fmt(-crx)} {fmt(ccy - dep)} M{fmt(crx)} {fmt(ccy - dep)} L{fmt(crx)} {fmt(ccy)}" '
                    f'stroke="#5A609E" stroke-width="{fmt(0.016 * u)}"/>')
            face = (f'<ellipse cx="0" cy="{fmt(ccy)}" rx="{fmt(crx)}" ry="{fmt(cry)}" fill="url(#rcapf)" stroke="#6F77B2" '
                    f'stroke-width="{fmt(0.016 * u)}"/>'
                    f'<ellipse cx="{fmt(-0.05 * u)}" cy="{fmt(ccy + 0.25 * cry)}" rx="{fmt(crx * 0.5)}" ry="{fmt(cry * 0.35)}" fill="#FFFFFF" '
                    f'fill-opacity="0.6" filter="url(#rs1)"/>')
            caps.append(f'<g transform="{tr}"><ellipse cx="0" cy="{fmt(ccy - dep - 0.03 * u)}" rx="{fmt(crx)}" '
                        f'ry="{fmt(cry)}" fill="#2E2466" fill-opacity="0.35" filter="url(#rs1)"/>{side}{face}</g>')
        else:
            g.append(f'<g transform="{tr}"><path d="{body}" fill="url(#rlugb)" stroke="#5A609E" stroke-width="{fmt(0.016 * u)}"/>{cap}</g>')
    g.append(f'<circle cx="{fmt(cx)}" cy="{fmt(cy)}" r="{fmt(rs)}" fill="url(#rsph)" stroke="#50569A" stroke-width="{fmt(0.02 * u)}"/>')
    g.append(f'<g clip-path="url(#rsphc)"><path d="M{fmt(cx - 0.8 * rs)} {fmt(cy + 0.62 * rs)} A{fmt(rs)} {fmt(rs)} 0 0 0 '
             f'{fmt(cx + 0.8 * rs)} {fmt(cy + 0.62 * rs)}" fill="none" stroke="#D6E6FF" stroke-opacity="0.85" '
             f'stroke-width="{fmt(0.07 * u)}" filter="url(#rs1)"/>'
             f'<ellipse cx="{fmt(cx - 0.42 * rs)}" cy="{fmt(cy - 0.5 * rs)}" rx="{fmt(0.32 * rs)}" ry="{fmt(0.18 * rs)}" '
             f'transform="rotate(-35 {fmt(cx - 0.42 * rs)} {fmt(cy - 0.5 * rs)})" fill="#FFFFFF" fill-opacity="0.7" filter="url(#rs1)"/></g>')
    g += caps
    g.append(f'<circle cx="{fmt(cx)}" cy="{fmt(cy)}" r="{fmt(rr)}" fill="url(#rring)" stroke="#433595" stroke-width="{fmt(0.02 * u)}"/>')
    g.append(f'<circle cx="{fmt(cx)}" cy="{fmt(cy)}" r="{fmt(rw)}" fill="url(#rwell)" stroke="#0E1946" stroke-width="{fmt(0.02 * u)}"/>')
    g.append(f'<path d="M{fmt(cx - 0.75 * rw)} {fmt(cy - 0.35 * rw)} A{fmt(rw * 0.85)} {fmt(rw * 0.85)} 0 0 1 {fmt(cx + 0.6 * rw)} '
             f'{fmt(cy - 0.62 * rw)}" fill="none" stroke="#6C9AD6" stroke-opacity="0.45" stroke-width="{fmt(0.04 * u)}" '
             f'stroke-linecap="round" filter="url(#rs1)"/>')
    return svg_doc(W, H, "\n".join(g), "".join(defs)), dict(anchor=(W / 2, H / 2), note="anchor = the ring centre = the "
                                                             "block centre; the counter is live text in the well")


def box_case(wc, hc):
    """Register a slab size on demand (boxW10H3 ...), for proofs; the engine 9-slices boxSlab."""
    CASES[f"boxW{wc}H{hc}"] = (lambda: box_slab(wc, hc))
    return f"boxW{wc}H{hc}"


# ====================================================================================== cases
CASES = {}
ANCHORS = {}
for n in (2, 3, 4):
    CASES[f"tapeV{n}"] = (lambda n=n: tape(n, "V"))
    CASES[f"tapeH{n}"] = (lambda n=n: tape(n, "H"))
for h in (4, 8, 12, 16, 20):
    CASES[f"doorW4H{h}"] = (lambda h=h: door(4, h))
CASES["lockHex"] = hex_lock
CASES["keyOnArrow"] = key
CASES["pipeMouth"] = pipe_mouth
CASES["pipeCounter"] = pipe_counter
CASES["curtainCrate"] = curtain_crate
CASES["boxSlab"] = box_slab
CASES["boxRing"] = box_ring


def curtain_case(wc, hc):
    """Register a curtain block size on demand (curtainW2H2, curtainW1H3 ...)."""
    CASES[f"curtainW{wc}H{hc}"] = (lambda: curtain_crate(P0, wc, hc))
    return f"curtainW{wc}H{hc}"


def build(names=None):
    for n in names or list(CASES):
        svg, meta = CASES[n]()
        open(os.path.join(HERE, f"{n}.svg"), "w", encoding="utf-8").write(svg)
        ANCHORS[n] = meta
        print("wrote", os.path.join(HERE, f"{n}.svg"), "anchor pt", tuple(round(v, 2) for v in meta["anchor"]))


def door_case(wc, hc):
    """Register a door size on demand (the manifest lists more sizes than CASES' L33 set)."""
    CASES[f"doorW{wc}H{hc}"] = (lambda: door(wc, hc))
    return f"doorW{wc}H{hc}"


if __name__ == "__main__":
    args = sys.argv[1:]
    for a in args:  # doorW13H4 etc. on demand
        if a.startswith("doorW") and a not in CASES:
            w, h = a[5:].split("H")
            door_case(int(w), int(h))
        if a.startswith("boxW") and a not in CASES:
            w, h = a[4:].split("H")
            box_case(int(w), int(h))
    build(args or None)
