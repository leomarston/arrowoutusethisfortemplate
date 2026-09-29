#!/usr/bin/env python3
"""Art lane "missing-svg" (route B2): the SVG icons SPEC-ui §4.2 listed as missing, plus the Settings OFF slash.

    ~/.venvs/mf3d/bin/python art/ui/src/svg/gen_missing.py heartBig iconCheck     # -> build/ui-art/svgsrc/<case>.svg
    # the batch builds them for real: art/tools/art_batch.py --manifest art/lanes/missing-svg.entries.json --svg

Same rules as gen_icons.py (whose helpers this module imports read-only; that file belongs to the svg lane): units
inside every SVG are @3x px (1 unit = 1/3 pt), y down; every shape is a primitive (circles, ellipses, rounded
polygons, strokes, the fitted two-ellipse heart of shapes.py) whose parameters were MEASURED on the captures (ink
extents, colour profiles, fitted shape parameters -- the numbers are in the comment above each case). Nothing is traced
and no capture pixel goes into an asset. Numbers and words stay live text (the case comment names where they go).

Placement: every case comment gives the frame's top-left in the reference shot (pt), so the shell can place the frame
exactly where the original draws the element; the lane file art/lanes/missing-svg.md repeats them.
"""
from __future__ import annotations

import math
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
import gen_icons as GI  # noqa: E402  (read-only: Doc, primitives, the stopwatch drawing)
from gen_icons import Doc, F, arc_path, circ, ell, embed, rounded, rr, toon, xf  # noqa: E402
from shapes import _contour, heart2_field, poly_path  # noqa: E402

try:
    from scipy import ndimage as _ndi
except Exception:  # pragma: no cover
    _ndi = None


# ====================================================================================== helpers
def heart_smooth(x, y, w, h, P, smooth=0.010, notch=None, low_smooth=0.0):
    """The fitted two-ellipse heart (shapes.heart2_field with parameters P) as a path, its field lightly smoothed so the
    tip wedge meets the lobes without a kink (visible at 185 pt, invisible at 30). smooth = sigma as a fraction of w.
    notch = (apex_y as a fraction of h, half-width growth per unit of height): a V wedge carved at the top centre where
    the capture's notch is deeper than the two ellipses make it."""
    f = heart2_field(w, h, P)
    step = max(w, h) / 420.0
    pad = 0.06 * max(w, h)
    xs = np.arange(-pad, w + pad, step)
    ys = np.arange(-pad, h + pad, step)
    X, Y = np.meshgrid(xs, ys)
    Fd = f(np.stack([X.ravel(), Y.ravel()], 1)).reshape(X.shape)
    if notch:
        ay, kk = notch[0] * h, notch[1]
        # distance-like field of the wedge |x - w/2| < (ay - y) * kk (open upward): positive outside
        nrm = math.hypot(1.0, kk)
        wedge = (np.abs(X - w / 2) - (ay - Y) * kk) / nrm
        Fd = np.maximum(Fd, -wedge)
    if smooth and _ndi is not None:
        Fs = _ndi.gaussian_filter(Fd, smooth * w / step)
        if low_smooth:   # a stronger smoothing on the lower half only (the tip wedge joins), the notch stays crisp
            Fl = _ndi.gaussian_filter(Fd, low_smooth * w / step)
            t = np.clip((Y / h - 0.45) / 0.2, 0, 1)
            Fs = Fs * (1 - t) + Fl * t
        Fd = Fs
    pts = _contour(Fd, -pad, -pad, step)
    return poly_path([(x + a, y + b) for a, b in pts])


def _paths(ds):
    return "".join(f'<path d="{p}"/>' for p in ds)


def stroke_poly(pts, w, cap="round"):
    return f'M{F(pts[0][0])} {F(pts[0][1])}' + "".join(f"L{F(px)} {F(py)}" for px, py in pts[1:])


def rot_pts(pts, deg, cx, cy):
    return xf(pts, deg=deg, ox=cx, oy=cy)


# ====================================================================================== 1. iced HUD stopwatch
# meta-065 (L62, freeze running) vs 003, profiles through the watch: the ring is iconStopwatch's (outer edges incl. the dark
# outline x 92.7-122.0 on both shots) but the whole watch sits ~1 pt HIGHER while iced (hand top 85.3 vs 86.0, lower
# tick bottom 105.4 vs 106.7): ring centre (107.35, 95.4). A puffy snow PILLOW hides the crown (grid-read at 12 px/pt:
# x 96.3-121.8, top y 76.8 flat over x 104-112, a lower edge bulging to y 86.8 at x 100 and 88 at x 119, ~84.8 between),
# white on top, blue-grey #C0D4E4 below with a darker line #7E9EB8 at its lower edge; a snow mass hugs the ring's bottom
# (top edge ~103.4, x 99-117.5) and drips two icicles (tips (104.3, 116.6) and (111.4, 120.2), widths 5.5 / 6.5).
# Face, ticks and the spade hand = iconStopwatch (its drawing is embedded).
# Frame 34 x 50 pt at shot (90.45, 72.4): ring centre at frame (16.9, 23.0) pt. hud.stopwatch (92.7, 77.7) -> the frozen
# frame origin = hud.stopwatch origin + (-2.25, -5.3).
FROZEN = dict(org=(90.45, 72.4), ring=(107.35, 95.4))


def blob_union(blobs, k, step=0.75):
    """ONE outline for a union of ellipses [(cx, cy, rx, ry, deg)] (px), blended with a polynomial smooth-min of radius k
    px (snow reads as one soft mass, not a cluster of bubbles)."""
    xs0 = min(cx - max(rx, ry) for cx, cy, rx, ry, _ in blobs) - 3 * k - 4
    xs1 = max(cx + max(rx, ry) for cx, cy, rx, ry, _ in blobs) + 3 * k + 4
    ys0 = min(cy - max(rx, ry) for cx, cy, rx, ry, _ in blobs) - 3 * k - 4
    ys1 = max(cy + max(rx, ry) for cx, cy, rx, ry, _ in blobs) + 3 * k + 4
    X, Y = np.meshgrid(np.arange(xs0, xs1, step), np.arange(ys0, ys1, step))
    D = None
    for cx, cy, rx, ry, deg in blobs:
        t = math.radians(deg)
        u = (X - cx) * math.cos(t) + (Y - cy) * math.sin(t)
        v = -(X - cx) * math.sin(t) + (Y - cy) * math.cos(t)
        di = (np.sqrt((u / rx) ** 2 + (v / ry) ** 2) - 1.0) * min(rx, ry)
        if D is None:
            D = di
        else:
            h = np.clip(0.5 + 0.5 * (di - D) / k, 0, 1)
            D = di * (1 - h) + D * h - k * h * (1 - h)
    pts = _contour(D, xs0, ys0, step)
    return poly_path(pts), (xs0, ys0, xs1, ys1)


def _snow(d, path, box, cast=(0.0, 3.6), soft=False):
    """Shade one snow mass: a soft blue shadow cast below, white body lit from the top, blue-grey underside band, a thin
    darker lower line, a light top rim. soft (to-A r4, meta-065 at 6x): the capture's snow has NO dark line along its lit
    top -- the outline only darkens the lower half (a vertical fade), and the cast shadow is a cooler, bluer blur."""
    x0, y0, x1, y1 = box
    y0 += 3 * 1.0; y1 -= 3 * 1.0
    d.add(f'<path d="{path}" fill="{"#3F79AE" if soft else "#3A6488"}" fill-opacity="0.42" transform="translate({F(cast[0])} {F(cast[1])})" filter="{d.blur(2.0)}"/>')
    # soft: the capture's shade is a saturated CYAN (#95CEE2 -> #67B8DB at the cap's underside, #A2DCF1 -> #5FB0D5 on the
    # shaded left drip), not grey-blue, and the light comes from the upper RIGHT (left ends / left drip in shade)
    stops = ([(0, "#FFFFFF"), (0.62, "#FDFEFE"), (0.82, "#E3F3F7"), (1, "#9CD3EA")] if soft else
             [(0, "#FFFFFF"), (0.42, "#FCFEFF"), (0.7, "#E4EFF6"), (1, "#C2D6E6")])
    d.add(f'<path d="{path}" fill="{d.lin(stops, 0, y0, 0, y1)}"/>')
    cp = d.clip(path)
    if soft:
        d.add(f'<path d="{path}" fill="{d.lin([(0, "#78C1E1", 0.38), (0.28, "#A6D8EC", 0.16), (0.5, "#FFFFFF", 0.0)], x0, 0, x1, 0)}"/>')
    d.add(f'<g clip-path="{cp}">'
          f'<path d="{path}" fill="none" stroke="{"#6CBADC" if soft else "#9AB5CE"}" stroke-opacity="{0.75 if soft else 0.95}" stroke-width="8" transform="translate(-1 -4.2)" filter="{d.blur(2.0)}"/>'
          f'<path d="{path}" fill="none" stroke="#FFFFFF" stroke-width="3.2" transform="translate(0.6 2.4)" filter="{d.blur(1.0)}"/>'
          f'</g>')
    if soft:
        d.add(f'<path d="{path}" fill="none" stroke="{d.lin([(0, "#4E86A8", 0.0), (0.45, "#4E86A8", 0.15), (1, "#467A99", 0.85)], 0, y0, 0, y1)}" stroke-width="1.0"/>')
    else:
        d.add(f'<path d="{path}" fill="none" stroke="#7E9EB8" stroke-opacity="0.55" stroke-width="1.0"/>')


def icon_stopwatch_frozen(W=34, H=50):
    d = Doc(W, H)
    ox, oy = FROZEN["org"]
    P = lambda x, y: ((x - ox) * 3, (y - oy) * 3)          # shot pt -> frame px
    # the HUD watch: iconStopwatch's own drawing, its ring centre (49.5, 54.3) px placed on the measured ring centre
    cx, cy = P(*FROZEN["ring"])
    k = 1.02                                                 # iconStopwatch reads 1:1 on 003 at 1.02x (REVIEW)
    g, _, _ = embed(GI.icon_stopwatch(33, 33), cx - 49.5 * k, cy - 54.3 * k, "sw", k=k)
    d.add(g)
    # a cool frost tint on the ring's upper half (under the pillow) -- to-A r4: off (meta-065's ring stays saturated
    # orange right up to the snow; the tint read as a pale band once the cap stopped covering the ring top)
    d.add(f'<path d="{arc_path(cx, cy, 38.5, 205, 335)}" fill="none" stroke="#D6F2FF" stroke-opacity="0.0" stroke-width="5" '
          f'filter="{d.blur(1.4)}"/>')
    S3 = lambda v: v * 3
    # snow pillow over the crown (ellipses in shot pt)
    # to-A r4: re-measured on meta-065 at 6x with the frame registered on the ring (ring centre fit 107.10, 95.44 r 12.4):
    # the cap RESTS on the ring top -- left end a round lump at x 97.5 / y 78-83, underside ~84 across the middle (the
    # round-3 cap reached y 87 and covered the face top), top 76.4 with a lump over the crown, the right end drooping
    # onto the ring to y ~86.5 at x 118-120.
    cap = [(100.8, 81.9, 3.2, 2.7, -12), (105.8, 79.9, 5.3, 3.6, -6), (109.4, 78.3, 3.4, 1.9, 0),
           (112.6, 81.2, 4.8, 3.5, 14), (118.2, 84.4, 2.3, 2.5, 10)]
    cap = [(*P(x, y), S3(rx), S3(ry), dg) for x, y, rx, ry, dg in cap]
    path, box = blob_union(cap, S3(1.1))
    _snow(d, path, box, soft=True)
    # the snow mass under the ring + two icicles (the right one longer)
    # to-A r4 (meta-065, 6x): the collar hugs the ring bottom from x 100 (a lump at 7 o'clock) up to 117.5 (rising to
    # y ~103 at 4 o'clock); the clump hangs from x 103.5-116 and splits LOW (notch 108.8, 113.9): a short left drip
    # and a wider, longer right one; registered at 4x on the ring: left drip x 106-109.7 (tip ~117), right drip
    # x 110.1-115.5 (tip ~119.2).
    low = [(103.4, 107.4, 2.4, 2.3, 0), (110.0, 106.8, 7.4, 3.0, -9), (116.4, 105.4, 1.9, 2.3, 0),
           (115.0, 108.2, 2.2, 2.4, 0), (108.0, 112.4, 2.4, 4.6, -3), (113.0, 113.6, 2.9, 5.7, 3),
           (110.6, 110.4, 4.4, 2.8, 0)]
    low = [(*P(x, y), S3(rx), S3(ry), dg) for x, y, rx, ry, dg in low]
    path, box = blob_union(low, S3(1.4))
    _snow(d, path, box, cast=(1.0, 3.0), soft=True)
    return d.svg()


# ====================================================================================== 2. frost cracks (corner tile)
# meta-065 corners (4x crops): thin white ice cracks -- straight segments meeting at junction nodes, a few short branches,
# brighter where they cross, ~1 pt wide at alpha ~0.7 with a faint glow -- plus a few 6-arm snowflakes (7-10 pt, alpha
# ~0.45) and small bright dots, in a ~30 pt band along each screen edge (none over the HUD's middle); over the code gradient (fxFrostVignette: #6BD4F8 sides /
# #60EFFB top+bottom -> white). One TOP-LEFT corner tile, 120 x 120 pt; the shell mirrors it for the other corners
# (scaleX/scaleY -1). The crack web is OURS (authored node list below), not a trace.
CRACK_NODES = {  # pt in the tile, corner at (0, 0): the web hugs the two screen edges (top band ~30 pt, side band ~26 pt)
    "a": (0, 21), "b": (12, 11), "c": (29, 17), "d": (43, 6), "e": (50, 0), "f": (61, 15), "g": (79, 8), "h": (94, 0),
    "i": (103, 19), "j": (120, 13), "k": (9, 37), "l": (0, 50), "m": (17, 60), "n": (5, 79), "o": (19, 93), "p": (0, 106),
    "q": (11, 120), "r": (36, 27),
}
CRACK_EDGES = ["ab", "bc", "cd", "de", "cf", "fg", "gh", "gi", "ij", "bk", "kl", "km", "mn", "no", "op", "oq", "cr", "ak"]
FLAKES = [(22, 5, 3.4, 12), (70, 24, 3.0, 30), (6, 66, 2.8, 5), (108, 4, 2.6, 40)]
DOTS = [(40, 14, 1.2), (86, 20, 1.0), (14, 46, 1.1), (4, 98, 1.0), (58, 4, 0.9)]


def frost_cracks(W=120, H=120):
    d = Doc(W, H)
    N = {k: (x * 3, y * 3) for k, (x, y) in CRACK_NODES.items()}
    # visible in a band along the top and the left edge (the vignette: ~53 pt deep at the top, ~27 pt at the sides)
    band_t = d.lin([(0, "#FFFFFF", 1), (0.5, "#FFFFFF", 0.8), (1, "#FFFFFF", 0)], 0, 0, 0, 40 * 3)
    band_l = d.lin([(0, "#FFFFFF", 1), (0.55, "#FFFFFF", 0.8), (1, "#FFFFFF", 0)], 0, 0, 30 * 3, 0)
    m = d.mask(f'<rect x="0" y="0" width="{F(d.W)}" height="{F(d.H)}" fill="#000000"/>'
               f'<rect x="0" y="0" width="{F(d.W)}" height="{F(d.H)}" fill="{band_t}"/>'
               f'<rect x="0" y="0" width="{F(d.W)}" height="{F(d.H)}" fill="{band_l}"/>')
    lines = "".join(f'<path d="M{F(N[e[0]][0])} {F(N[e[0]][1])}L{F(N[e[1]][0])} {F(N[e[1]][1])}"/>' for e in CRACK_EDGES)
    g = [f'<g mask="{m}">',
         f'<g fill="none" stroke="#FFFFFF" stroke-opacity="0.25" stroke-width="4" stroke-linecap="round" filter="{d.blur(1.8)}">{lines}</g>',
         f'<g fill="none" stroke="#FFFFFF" stroke-opacity="0.6" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">{lines}</g>']
    for k in "bcfgkmo":
        x, y = N[k]
        g.append(f'<path d="{circ(x, y, 3.6)}" fill="#FFFFFF" fill-opacity="0.4" filter="{d.blur(1.8)}"/>')
    g.append("</g>")
    for x, y, r, rot in FLAKES:
        X, Y, R = x * 3, y * 3, r * 3
        arms = ""
        for a in range(6):
            t = math.radians(rot + 60 * a)
            ux, uy = math.cos(t), math.sin(t)
            arms += f'M{F(X)} {F(Y)}L{F(X + ux * R)} {F(Y + uy * R)}'
            for sg in (-1, 1):   # two short barbs per arm
                t2 = t + sg * math.radians(40)
                bx, by = X + ux * R * 0.58, Y + uy * R * 0.58
                arms += f'M{F(bx)} {F(by)}L{F(bx + math.cos(t2) * R * 0.34)} {F(by + math.sin(t2) * R * 0.34)}'
        g.append(f'<path d="{arms}" fill="none" stroke="#FFFFFF" stroke-opacity="0.42" stroke-width="1.5" stroke-linecap="round"/>')
    for x, y, r in DOTS:
        X, Y = x * 3, y * 3
        g.append(f'<path d="{circ(X, Y, r * 3 * 2.4)}" fill="#FFFFFF" fill-opacity="0.3" filter="{d.blur(r * 3)}"/>'
                 f'<path d="{circ(X, Y, r * 3 * 0.6)}" fill="#FFFFFF" fill-opacity="0.75"/>')
    d.add(*g)
    return d.svg()


# ====================================================================================== 3. big glossy hearts
# heartBig (meta-088, "Out of Lives!"): the heart's bright body is 184.8 x 155.1 pt at (104.0, 320.7) (red > 150), a dark
# rim #7E0102 -> #640E0B ~2.3 pt around it (ink 189.5 x 159.8 at (101.7, 318.3)). Silhouette = shapes.heart2 with the
# parameters FITTED on the red mask (IoU 0.982; holes filled): rx 0.455 w, ry 0.386 h, dx 0.102 w, cy 0.478 h, 45.5 deg,
# tip wedge from 0.936 h, half-width 0.152 w. Profiles (x = 150 / 240 vertical, y = 350 / 400 / 440 horizontal):
# top #FF2418..#FF3628, middle #E41008 (0.45 h), #BF1916 (0.7 h), #AC1612 (0.85 h); the right side ~15 % darker (#A5120E
# at 0.92 w); a thin bright rim light just inside the dark rim along the lower/side edges (#D82C1E, #DB2B1B, #D0231D); a big
# soft specular on the left lobe centred (0.243 w, 0.187 h) ~30 x 18 pt, peak #FFBEA9; a narrower diagonal highlight on
# the right lobe's inner shoulder (0.595 w, 0.19 h), peak #FEA289; a small bright spot on the right lobe's upper-right
# shoulder (0.885 w, 0.105 h) #FFAAA2; a darker crease under the notch (#E1140D). The red radial GLOW around it is the
# shell's code (SPEC-ui 2.6.2: #FF2F20 at the heart edge -> #480F0D at 100 pt -> black by 150 pt), not baked.
# Frame 194 x 164 pt at shot (99.5, 316.0): body box at frame (4.5, 5.0) 185 x 155 pt.
HEART_BIG = dict(rx=0.4547, ry=0.3901, dx=0.0994, cy=0.4749, deg=44.94, tip_y0=0.9311, tip_hw=0.1612)   # r2: joint fit with the notch, IoU 0.988


HEART_BIG_NOTCH = (0.150, 0.85)   # the capture's notch: gap 25 pt 9 pt below the top, bottom 19.5 pt below it (x 196.2)


def heart_glossy(W, H, bx, by, bw, bh):
    """The Out-of-Lives heart at any size: body box (bx, by, bw, bh) in px. Shading = a puffy two-lobe gloss: a warm
    radial body, each lobe rounded by its own light, a soft valley under the notch, the big soft left specular, the
    diagonal right-lobe highlight, a small shoulder glint, a bright rim light low on the edge and a thin deep-red rim."""
    d = Doc(W, H)
    p = heart_smooth(bx, by, bw, bh, HEART_BIG, smooth=0.005, notch=HEART_BIG_NOTCH, low_smooth=0.022)
    u = lambda fx: bx + fx * bw
    v = lambda fy: by + fy * bh
    s = bw / 555.0                                 # 1.0 at the reference size (185 pt body)
    # dark rim (outside the body): deep red, soft outer edge (the glow behind is the shell's)
    d.add(f'<path d="{p}" fill="#5A0404" fill-opacity="0.55" stroke="#5A0404" stroke-opacity="0.55" stroke-width="{F(15 * s)}" '
          f'stroke-linejoin="round" filter="{d.blur(3.4 * s)}"/>')
    d.add(f'<path d="{p}" fill="#7A0203" stroke="#7A0203" stroke-width="{F(10.5 * s)}" stroke-linejoin="round" filter="{d.blur(1.0 * s)}"/>')
    # body: an elliptical ramp around the bright middle (profiles: peak #FF3F30 at (0.47 w, 0.33 h); #BB1611 at the left
    # edge and #A91510 at the right edge on y 0.51 h; #CF150F at 0.72 h and #B11914 at the bottom on the centre line)
    d.add(f'<path d="{p}" fill="{d.rad([(0, "#FF3A2C"), (0.26, "#FD2216"), (0.45, "#F0140A"), (0.62, "#D8130C"), (0.78, "#BE1611"), (0.92, "#AE1612"), (1, "#A81510")], u(0.47), v(0.34), 0.47 * bw, sx=1.0, sy=0.62 * bh / (0.47 * bw))}"/>')
    cp = d.clip(p)
    grp = [f'<g clip-path="{cp}">']
    # each lobe lit to its outer top (profiles y 0.19 h: #FE1509 at 0.08 w, #FF1B11 at 0.79 w)
    for lx in (0.25, 0.745):
        grp.append(f'<ellipse cx="{F(u(lx))}" cy="{F(v(0.22))}" rx="{F(0.26 * bw)}" ry="{F(0.22 * bh)}" '
                   f'fill="{d.rad([(0, "#FF3222", 1.0), (0.55, "#FF2616", 0.75), (1, "#FF2012", 0)], u(lx), v(0.2), 0.26 * bw, sx=1, sy=0.22 * bh / (0.26 * bw))}"/>')
    # a deeper red band just inside the UPPER edge (the lobes turn away from the light: #F7160B at the very top)
    top_m = d.mask(f'<rect x="{F(u(-0.1))}" y="{F(v(-0.1))}" width="{F(bw * 1.2)}" height="{F(bh * 1.2)}" '
                   f'fill="{d.lin([(0, "#FFFFFF"), (0.22, "#FFFFFF"), (0.4, "#000000")], 0, v(0), 0, v(1))}"/>')
    # director r3: 0.75 -> 0.35 (at 0.75 the band muddied the lobe tops; 088's top edge stays bright red to the outline)
    grp.append(f'<path d="{p}" fill="none" stroke="#D80C06" stroke-opacity="0.35" stroke-width="{F(16 * s)}" mask="{top_m}" filter="{d.blur(4 * s)}"/>')
    # the crevice under the notch: the cleft continues as a thin dark-red fold ~0.07 h below the carved apex, with a
    # darker lip on each lobe's inner flank (the capture's notch reads ~29 pt deep, the red mask closes at ~22)
    ay = HEART_BIG_NOTCH[0]
    cre = poly_path([(u(0.5) - 0.028 * bw, v(ay - 0.03)), (u(0.5) + 0.028 * bw, v(ay - 0.03)), (u(0.502) + 0.004 * bw, v(ay + 0.085)),
                     (u(0.498) - 0.004 * bw, v(ay + 0.085))])
    # director r3: the fold is kept faint and the two dark lip ellipses are gone -- at game size they read as a smudge
    # left of the notch and made the notch look ~10 pt deeper than 088's (whose inner flanks are lit, not shaded)
    grp.append(f'<path d="{cre}" fill="#B00A05" fill-opacity="0.22" filter="{d.blur(2.6 * s)}"/>')
    # rim light low on the edge (lower half + sides), then a thin deep line on the very edge
    rim_m = d.mask(f'<rect x="{F(u(-0.1))}" y="{F(v(-0.1))}" width="{F(bw * 1.2)}" height="{F(bh * 1.2)}" '
                   f'fill="{d.lin([(0, "#000000"), (0.28, "#000000"), (0.55, "#FFFFFF"), (1, "#FFFFFF")], 0, v(0), 0, v(1))}"/>')
    grp.append(f'<path d="{p}" fill="none" stroke="#E8341F" stroke-opacity="0.8" stroke-width="{F(28 * s)}" mask="{rim_m}" filter="{d.blur(4.5 * s)}"/>')
    grp.append(f'<path d="{p}" fill="none" stroke="#F24A30" stroke-opacity="0.8" stroke-width="{F(9 * s)}" mask="{rim_m}" filter="{d.blur(1.6 * s)}"/>')
    grp.append(f'<path d="{p}" fill="none" stroke="#800606" stroke-opacity="0.7" stroke-width="{F(2.6 * s)}" filter="{d.blur(0.6 * s)}"/>')
    # speculars: the big soft one on the left lobe (peak #FFBEA9 at (0.245 w, 0.19 h), a diagonal soft oval ~ -28 deg), a
    # long soft diagonal on the right lobe's inner slope (peak #FEA289), a glint arc on the right shoulder (#FFAAA2)
    def spec(fx, fy, rx, ry, rot, stops, blur):
        cx_, cy_ = u(fx), v(fy)
        return (f'<ellipse cx="{F(cx_)}" cy="{F(cy_)}" rx="{F(rx)}" ry="{F(ry)}" transform="rotate({F(rot)} {F(cx_)} {F(cy_)})" '
                f'fill="{d.rad(stops, cx_, cy_, rx, sx=1, sy=ry / rx)}"' + (f' filter="{d.blur(blur)}"' if blur else "") + "/>")
    # director r3: the gradient is no longer rotated a second time (the element transform already rotates the ellipse and
    # its user space, so rot on the gradient too turned it 2x: hard ellipse edges on the left lobe, a hard white
    # parallelogram on the right); the right-lobe streak is longer and softer and the shoulder glint is 088's soft crescent
    grp.append(spec(0.25, 0.2, 0.2 * bw, 0.13 * bh, -28,
                    [(0, "#FFC8B4", 1), (0.22, "#FFB6A0", 0.92), (0.48, "#FF8A72", 0.58), (0.75, "#FF5444", 0.24), (1, "#FF4A38", 0)], 2.5 * s))
    grp.append(spec(0.585, 0.225, 0.14 * bw, 0.052 * bh, -58,
                    [(0, "#FFB29C", 1.0), (0.45, "#FF927A", 0.62), (1, "#FF4A38", 0)], 3.6 * s))
    grp.append(spec(0.852, 0.118, 0.085 * bw, 0.03 * bh, 38, [(0, "#FFC4B8", 0.85), (0.55, "#FF9C8E", 0.45), (1, "#FF7060", 0)], 3.0 * s))
    grp.append("</g>")
    d.add(*grp)
    return d.svg()


def heart_big(W=194, H=164):
    return heart_glossy(W, H, 4.5 * 3, 5.0 * 3, 185 * 3, 155 * 3)


# heartLivesBig (meta-095 More Lives card; the count "3" and the white "+" are LIVE text, SPEC-ui 2.9). Silhouette fitted
# with position + size free (IoU 0.975; mask r > 120 & g < 90 & b < 90, text holes filled, the "+" masked): box incl. the
# outline (150.4, 254.3) 92.5 x 79.4 pt; rx 0.454 w, ry 0.377 h, dx 0.112 w, cy 0.474 h, 47.9 deg, tip from 0.877 h,
# half-width 0.224 w. Colour grid (fractions of the box): a bright band 0.29-0.45 h (#F33727..#F73727 on the right lobe,
# #E31A0F..#F73B2B left), a darker crimson top band (0.13 h: #D80904 / #E40605), falling to #D30501 (0.69 h), #CC0501 (0.85 h)
# and #B30400 (0.93 h); edges dark (#C0..#C7 at 0.05 w, #B7..#94 at 0.95 w); an ORANGE specular on the left lobe, peak
# #FDA266 at (0.28 w, 0.30 h), ~11 pt, stretched down-right; light glints just inside the left edge (#DA4038 at 0.45 h)
# and the right shoulder (#E15452 at (0.86 w, 0.1 h)); outline #950306 / #990203 ~1.3 pt.
# Frame 100 x 90 pt at shot (146.9, 250.5): the heart box at frame (3.5, 3.8).
# heartGlossySmall = the SAME heart style for the "+1 Live" ad button (meta-095: fitted box (141.9, 594.1) 42.6 x 35.9 pt,
# parameters ~ HEART2; the "+1" is LIVE text over its lower right). Frame 46 x 40 at shot (140.0, 592.0).
HEART_LIVES = dict(rx=0.4541, ry=0.3774, dx=0.1116, cy=0.4738, deg=47.92, tip_y0=0.8774, tip_hw=0.224)
HEART_AD = dict(rx=0.4601, ry=0.3860, dx=0.1057, cy=0.4850, deg=47.56, tip_y0=0.8984, tip_hw=0.2059)


def heart_lives_style(W, H, bx, by, bw, bh, P, ol_pt=1.3, notch=None):
    d = Doc(W, H)
    ol = ol_pt * 3
    s = bw / (92.5 * 3)
    p_out = heart_smooth(bx, by, bw, bh, P, smooth=0.006, notch=notch, low_smooth=0.03)
    ni = (notch[0] * bh / (bh - 2 * ol) - ol / (bh - 2 * ol), notch[1]) if notch else None   # the same apex, inset
    p = heart_smooth(bx + ol, by + ol, bw - 2 * ol, bh - 2 * ol, P, smooth=0.006, notch=ni, low_smooth=0.03)
    u = lambda fx: bx + fx * bw
    v = lambda fy: by + fy * bh
    d.add(f'<path d="{p_out}" fill="#5A1A10" fill-opacity="0.25" transform="translate(0 {F(3 * s + 1)})" filter="{d.blur(2.2 * s + 0.6)}"/>')
    # outline: the fitted box + a soft half-pixel ring outside it (the capture's outline edge is soft, maroon-purple)
    d.add(f'<path d="{p_out}" fill="#7C1424" stroke="#7C1424" stroke-opacity="0.85" stroke-width="{F(2.2 * s + 0.8)}" stroke-linejoin="round" filter="{d.blur(0.5 * s + 0.2)}"/>')
    d.add(f'<path d="{p_out}" fill="#8C0510"/>')
    d.add(f'<path d="{p}" fill="{d.rad([(0, "#F83A28"), (0.35, "#F43020"), (0.55, "#E81C10"), (0.72, "#D60A05"), (0.86, "#C40402"), (1, "#B00400")], u(0.5), v(0.36), 0.62 * bw, sx=1, sy=0.62 * bh / (0.62 * bw))}"/>')
    cp = d.clip(p)
    top = d.lin([(0, "#B00000", 0.7), (0.12, "#B00000", 0.45), (0.26, "#B00000", 0)], 0, v(0), 0, v(1))
    lm = d.mask(f'<rect x="{F(u(-0.1))}" y="{F(v(-0.1))}" width="{F(bw * 1.2)}" height="{F(bh * 1.2)}" '
                f'fill="{d.lin([(0, "#000000"), (0.3, "#000000"), (0.42, "#FFFFFF"), (0.56, "#FFFFFF"), (0.66, "#000000")], 0, v(0), 0, v(1))}"/>')
    rm = d.mask(f'<rect x="{F(u(0.62))}" y="{F(v(-0.1))}" width="{F(bw * 0.5)}" height="{F(bh * 0.5)}" '
                f'fill="{d.lin([(0, "#000000"), (0.35, "#000000"), (0.6, "#FFFFFF"), (1, "#FFFFFF")], u(0.62), 0, u(0.95), 0)}"/>')
    rm2 = d.mask(f'<g mask="{rm}"><rect x="{F(u(0.62))}" y="{F(v(-0.1))}" width="{F(bw * 0.5)}" height="{F(bh * 0.5)}" '
                 f'fill="{d.lin([(0, "#FFFFFF"), (0.5, "#FFFFFF"), (0.8, "#000000")], 0, v(-0.05), 0, v(0.38))}"/></g>')
    d.add(f'<g clip-path="{cp}">'
          f'<rect x="{F(u(0))}" y="{F(v(0))}" width="{F(bw)}" height="{F(bh)}" fill="{top}"/>'
          f'<path d="{p}" fill="none" stroke="#A00000" stroke-opacity="0.6" stroke-width="{F(16 * s)}" filter="{d.blur(4 * s)}"/>'
          # glints: inside the left edge around 0.45 h, inside the right shoulder
          f'<path d="{p}" fill="none" stroke="#EE6A60" stroke-opacity="0.9" stroke-width="{F(5 * s)}" mask="{lm}" '
          f'transform="translate({F(3.2 * s)} 0)" filter="{d.blur(0.9 * s)}"/>'
          f'<path d="{p}" fill="none" stroke="#EE7068" stroke-opacity="0.95" stroke-width="{F(5 * s)}" mask="{rm2}" '
          f'transform="translate({F(-2.6 * s)} {F(2.6 * s)})" filter="{d.blur(0.9 * s)}"/>'
          f'</g>')
    # the orange specular on the left lobe (peak #FDA266 at (0.28 w, 0.30 h), stretched down-right)
    cx_, cy_ = u(0.285), v(0.305)
    rx_, ry_ = 0.19 * bw, 0.13 * bw
    d.add(f'<g clip-path="{cp}"><ellipse cx="{F(cx_)}" cy="{F(cy_)}" rx="{F(rx_)}" ry="{F(ry_)}" transform="rotate(38 {F(cx_)} {F(cy_)})" '
          f'fill="{d.rad([(0, "#FEA868", 1), (0.2, "#FC9860", 0.9), (0.45, "#F87050", 0.55), (0.75, "#F44A34", 0.2), (1, "#F54030", 0)], cx_, cy_, rx_, sx=1, sy=ry_ / rx_, rot=38)}"/></g>')
    return d.svg()


def heart_lives_big(W=100, H=90):
    return heart_lives_style(W, H, 3.5 * 3, 3.8 * 3, 92.5 * 3, 79.4 * 3, HEART_LIVES, notch=(0.145, 0.8))   # notch 11.5 pt deep


def heart_glossy_small(W=46, H=40):
    return heart_lives_style(W, H, 1.9 * 3, 2.1 * 3, 42.6 * 3, 35.9 * 3, HEART_AD, ol_pt=0.8, notch=(0.153, 0.9))


# ====================================================================================== 4. video clapper (rewarded ad)
# meta-095 "+1 Live" button (the shell routes it through the offline AdSlot; SPEC.md 18): dark-green #025225 toon on the
# green face, cream #FFFDEE -> #FFF9D3 fill. Grid-read at 14 px/pt: body rounded rect x 99.5-134.5, y 604.3-628.8 (r 3.5,
# outline ~1.8 pt, 2.3 at the bottom); the clapper stick a rounded bar tilted -12.5 deg from (99.3, 598.5)..(134.5,
# 591.7) top to ~7 pt thick, cream inside with three dark rounded slots; a play triangle (dark outline, the button green
# showing through: a hole) (112.5, 610.5) (112.5, 620.5) (122, 615.5). Ink 35.7 x 37.0 at (99.0, 591.7).
# Frame 40 x 41 pt at shot (97.0, 589.7).
def icon_video_ad(W=40, H=41):
    d = Doc(W, H)
    ox, oy = 97.0, 589.7
    P = lambda x, y: ((x - ox) * 3, (y - oy) * 3)
    OL, FACE = "#025225", d.lin([(0, "#FFFDEF"), (1, "#FFF8D2")], 0, P(0, 592)[1], 0, P(0, 628)[1])
    # body
    x0, y0 = P(99.5, 604.3); x1, y1 = P(134.5, 628.8)
    body = rr(x0, y0, x1, y1, 3.6 * 3)
    face = rr(x0 + 5.6, y0 + 3.2, x1 - 5.6, y1 - 7.0, 2.0 * 3)
    # stick: a rounded bar hinged at the body's top-left corner, tilted -10.8 deg (ref edges (99, 598.5)->(134.5, 591.7) top,
    # (100.5, 605)->(134.6, 598.5) bottom): local frame u along, v up from the hinge; cream strip inside a 1.5 pt outline,
    # three dark slanted slots nearly filling the strip
    hx, hy = P(99.6, 606.6)
    ang = -10.8
    Q = lambda pts: rot_pts([(hx + uu * 3, hy - vv * 3) for uu, vv in pts], ang, hx, hy)
    stick = rounded(Q([(0, 0), (35.4, 0), (35.4, 8.8), (0, 8.8)]), 2.6 * 3)
    stick_in = rounded(Q([(1.8, 2.4), (33.6, 2.4), (33.6, 7.0), (1.8, 7.0)]), 1.2 * 3)
    slots = []
    for u0 in (3.4, 14.0, 24.6):
        slots.append(rounded(Q([(u0, 2.9), (u0 + 5.6, 2.9), (u0 + 7.0, 6.5), (u0 + 1.4, 6.5)]), 1.0 * 3))
    d.add(f'<path d="{stick}" fill="{OL}"/><path d="{body}" fill="{OL}"/>')
    d.add(f'<path d="{stick_in}" fill="{FACE}"/>')
    for sp in slots:
        d.add(f'<g clip-path="{d.clip(stick_in)}"><path d="{sp}" fill="{OL}"/></g>')
    d.add(f'<path d="{face}" fill="{FACE}"/>')
    # the play triangle: an outlined HOLE (evenodd: face minus the inner triangle shows the button through)
    t = [P(112.0, 609.7), P(123.2, 615.6), P(112.0, 621.5)]
    tin = [P(113.9, 613.0), P(119.6, 615.6), P(113.9, 618.2)]
    tri = rounded(t, 1.9 * 3)
    tri_in = rounded(tin, 0.7 * 3)
    d.add(f'<path d="{tri} {tri_in}" fill="{OL}" fill-rule="evenodd"/>')
    # the hole itself: cut the inner triangle out of everything (mask), so the button face shows through
    return _clapper_with_hole(d, tri_in)


def _clapper_with_hole(d, hole):
    """Wrap the whole drawing in a mask that punches the play triangle's hole (the button face shows through)."""
    m = d.mask(f'<rect x="0" y="0" width="{F(d.W)}" height="{F(d.H)}" fill="#FFFFFF"/><path d="{hole}" fill="#000000"/>')
    d.body = [f'<g mask="{m}">'] + d.body + ["</g>"]
    return d.svg()


# ====================================================================================== 5. check marks
# iconCheck (meta-039 Claw done card, 096 Sky Jump won stage at 0.75x): a thick glossy lime check, dark-green outline
# #0B3A08 ~1 pt, face #5DD62E -> #6FDD30 with a light bevel line #B6F28A along the upper edges, the extruded side
# #3A9A18 showing ~2.2 pt below-right, a soft dark drop shadow. Ink 55.7 x 47.4 pt at (214.0, 740.7) (claw). Centre line
# (pt), FITTED as a round-capped polyline stroke + its copy moved by the extrusion (IoU 0.977 on the dark-or-green mask;
# 096's check gives the same shape at 0.755): (223.1, 764.5) -> (235.0, 776.3) -> (259.8, 750.6), 19.1 pt across incl.
# the 1 pt outline, side offset (0.65, 2.31). Frame 60 x 54 pt at shot (211.8, 738.2).
CHECK = dict(org=(211.8, 738.2), pts=[(223.1, 764.5), (235.0, 776.3), (259.8, 750.6)], w=17.0, side=(0.65, 2.31))
# to-A r4: column profiles of meta-039 (3 px/pt) show a DEEP extruded side -- ~21-22 px (7 pt) of vertical side band
# under both arms (a dark crease #2B8404 at its top, lighter #3B9415 toward the outline), under a face only ~12 pt
# across; round 3's side was 5-9 px. Same silhouette, re-split: the extrusion grows by (-0.5, +4.84) pt (side
# (0.15, 7.15): arm bands 7.0 / 7.3 pt as measured) and the face loses 4.84 / sqrt2 of width with its centre line
# raised 2.42 pt, which keeps both the upper edge and the side's lower edge where they were on the 45-deg arms.
CHECK_R4 = dict(org=CHECK["org"], pts=[(x, y - 2.42) for x, y in CHECK["pts"]], w=17.0 - 4.84 / math.sqrt(2),
                side=(0.15, 7.5), shrink=0.036)   # shrink: the far (bottom) copy is 3.6 % smaller about the centre:
                                                  # 039's end walls converge (left wall +0.8 pt, right wall -0.8 pt)


def icon_check(W=60, H=54):
    d = Doc(W, H)
    C = CHECK_R4
    ox, oy = C["org"]
    pts = [((x - ox) * 3, (y - oy) * 3) for x, y in C["pts"]]
    cl = stroke_poly(pts, 0)
    w = C["w"] * 3
    sx, sy = C["side"][0] * 3, C["side"][1] * 3
    ow = 1.0 * 3
    st = 'fill="none" stroke-linecap="round" stroke-linejoin="round"'
    n = 16
    d.add(f'<path d="{cl}" {st} stroke="#462000" stroke-opacity="0.55" stroke-width="{F(w + 2 * ow + 5)}" transform="translate({F(sx + 1)} {F(sy + 1)})" filter="{d.blur(4.0)}"/>')
    # outline around face + side (swept), then the side (dark crease under the face -> lighter toward the outline), then the face
    ccx, ccy = W * 3 / 2, H * 3 / 2

    def tr(t):
        f = 1 - C["shrink"] * t
        return f'translate({F(sx * t + ccx)} {F(sy * t + ccy)}) scale({f:.4f}) translate({F(-ccx)} {F(-ccy)})'
    for k in range(0, n + 1):
        t = k / n
        d.add(f'<path d="{cl}" {st} stroke="#532400" stroke-width="{F(w + 2 * ow)}" transform="{tr(t)}"/>')

    def mix(c0, c1, t):
        a = [int(c0[i:i + 2], 16) for i in (1, 3, 5)]
        b = [int(c1[i:i + 2], 16) for i in (1, 3, 5)]
        return "#" + "".join(f"{round(x + (y - x) * t):02X}" for x, y in zip(a, b))
    for k in range(n, 0, -1):
        t = k / n
        col = mix("#A65717", "#C36E23", min(1.0, t * 1.25))
        d.add(f'<path d="{cl}" {st} stroke="{col}" stroke-width="{F(w)}" transform="{tr(t)}"/>')
    # (no separate crease stroke: any stroke moved down shows as a dark crescent on the round ends' walls; the darkest
    # copies right under the face read as 039's crease)
    face = d.lin([(0, "#F1CD77"), (0.35, "#FBB045"), (1, "#F8A339")], 0, pts[2][1] - w / 2, 0, pts[1][1] + w / 2)
    d.add(f'<path d="{cl}" {st} stroke="{face}" stroke-width="{F(w)}"/>')
    # bevel light along the upper edges: the centre line moved up-left, clipped to the face's stroke outline
    fclip = d.clip(_stroke_outline(pts, w))
    d.add(f'<g clip-path="{fclip}"><path d="{cl}" {st} stroke="#FFE7B8" stroke-opacity="1" stroke-width="{F(w * 0.8)}" '
          f'transform="translate({F(-0.9)} {F(-w * 0.36)})" filter="{d.blur(0.9)}"/>'
          f'<path d="{cl}" {st} stroke="#FBB045" stroke-width="{F(w * 0.70)}" transform="translate({F(0.3)} {F(-w * 0.20)})" filter="{d.blur(1.1)}"/>'
          f'<path d="{cl}" {st} stroke="#ED912F" stroke-opacity="0.45" stroke-width="{F(w * 0.6)}" transform="translate({F(0.6)} {F(w * 0.34)})" filter="{d.blur(1.6)}"/>'
          f'</g>')
    return d.svg()


def _stroke_outline(pts, w, n=24):
    """The outline of a polyline stroked w wide with round caps/joins, as a union of capsules (one clip path)."""
    ds = []
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        a = math.atan2(y1 - y0, x1 - x0)
        r = w / 2
        q = []
        for k in range(n + 1):
            t = a + math.pi / 2 + math.pi * k / n
            q.append((x0 + r * math.cos(t), y0 + r * math.sin(t)))
        for k in range(n + 1):
            t = a - math.pi / 2 + math.pi * k / n
            q.append((x1 + r * math.cos(t), y1 + r * math.sin(t)))
        ds.append(poly_path(q))
    return " ".join(ds)


# iconCheckBadge (meta-003 Edit Profile, the selected avatar tile's badge at its lower right): a FLATTER check than the
# Claw one -- a thick dark-green outline #0A4A0A (~1.7 pt) + a darker green band #0E8A10, a face #5AD824 (top) ->
# #1FA012 (bottom) and a thin light contour line #A0F070 inset ~1.6 pt all round; no extrusion. Grid-read (10 px/pt):
# ink x 117-153, y 395-424; centre line (123.8, 404.2) -> (132.4, 413.6) -> (147.6, 400.4), 11.4 pt thick outline
# included. Frame 40 x 34 pt at shot (115.0, 392.6) (SPEC-ui: 113.4 . 390.3 . 40 . 33.4).
BADGE = dict(org=(115.0, 392.6), pts=[(124.0, 407.0), (132.9, 417.1), (148.0, 402.6)], w=12.6)
# to-A r4, re-read on meta-003 at 18 px/pt: the FACE centre line is (124.6, 406.7) -> (131.9, 414.2) -> (146.2, 401.4)
# (round 3's vertex sat 2.9 pt low), the face 7.1 pt across with its light contour ON its edge (#9EF05A, ~0.45 pt);
# around it a wide mid-green band (#009E08 on the top side -> #007A07 below) and only a THIN dark outline (#0B560B,
# ~0.7 pt; round 3 drew a 1.5 pt outline and a thin band): outer silhouette = the face dilated ~3.5 pt, ~0.4 pt more below
# (the badge's side). Face #56E204 top -> #2EBE02 bottom (round 3's #44C81E read dull).
BADGE_R4 = dict(face=[(124.6, 406.7), (131.9, 414.2), (146.2, 401.4)], wf=7.1, band=3.5, drop=0.4, ol=0.7)


def icon_check_badge(W=40, H=34):
    d = Doc(W, H)
    ox, oy = BADGE["org"]
    B = BADGE_R4
    pts = [((x - ox) * 3, (y - oy) * 3) for x, y in B["face"]]
    cl = stroke_poly(pts, 0)
    low = stroke_poly([(x, y + B["drop"] * 3) for x, y in pts], 0)
    wf = B["wf"] * 3
    wo = (B["wf"] + 2 * B["band"]) * 3
    st = 'fill="none" stroke-linecap="round" stroke-linejoin="round"'
    y0, y1 = min(p[1] for p in pts) - wo / 2, max(p[1] for p in pts) + wo / 2
    d.add(f'<path d="{low}" {st} stroke="#3B1C00" stroke-opacity="0.35" stroke-width="{F(wo + 1)}" transform="translate(0.5 1.8)" filter="{d.blur(1.6)}"/>')
    for path in (cl, low):   # the outline + band swept from the face's line to the dropped line (the side)
        d.add(f'<path d="{path}" {st} stroke="#773800" stroke-width="{F(wo)}"/>')
    band = d.lin([(0, "#D2750D"), (0.5, "#BA630C"), (1, "#9F4F0B")], 0, y0, 0, y1)
    for path in (low, cl):
        d.add(f'<path d="{path}" {st} stroke="{band}" stroke-width="{F(wo - 2 * B["ol"] * 3)}"/>')
    d.add(f'<path d="{cl}" {st} stroke="#FAD685" stroke-width="{F(wf)}"/>')
    face = d.lin([(0, "#FEBC41"), (0.5, "#FCA125"), (1, "#ED8B17")], 0, pts[2][1] - wf / 2, 0, pts[1][1] + wf / 2)
    d.add(f'<path d="{cl}" {st} stroke="{face}" stroke-width="{F(wf - 2 * 0.5 * 3)}"/>')
    return d.svg()


# ====================================================================================== 6. skulls (win-panel tag ribbon)
# 037 (Hard, "Hard Level" red tag): a cream skull in the house toon style = face #FFF8EC -> #F6E2CC, outline = the tag
# label's outline #69000C (~1.2 pt) + the same outline dropped ~1.3 pt; eye sockets = dark ovals with a tan rim
# #EFC6A4; an inverted rounded-triangle nose; the jaw narrower than the cranium with a tan band at the bottom (teeth
# line). Tilted ~-5 deg (the right eye higher). Cream core 23.7 x 23.7 pt at (104.3, 120.3); ink incl. outline + drop
# 26.7 x 29.0 at (102.7, 119.0). Frame 30 x 32 at shot (101.0, 117.5); one skull each side of the label (mirror the
# right one? The capture's two skulls are the same drawing, not mirrored).
# 063 (Super Hard, purple tag, outline #3A007C): a smaller skull (cream core 18 x 19 at (107.0, 122.3)) over crossbones
# whose four knobbed ends show at the corners (ends ~(103.5, 122) (126.5, 120.5) (104.5, 145) (126.5, 141.5)); ink
# ~34 x 34 at (98, 116). Frame 38 x 38 at shot (95.5, 114.0).
def _skull_parts(cx, cy, s, tilt, eye_k=1.0):
    """Skull silhouette + features at scale s (px per unit; the Hard skull = 3.0), centred (cx, cy), tilted (deg).
    Measured on 037 (units = pt of the Hard skull): a boxy head -- a cranium 23.8 wide with round top corners (r 10) and
    straight sides, a jaw a little narrower (x -9.0..10.6) to y 12, a small cheek step at the lower left; eye sockets are
    wide ovals (left (-5.4, 2.1) 3.8 x 2.8, right (5.0, 2.1) 3.6 x 3.0) that are HOLES (the ribbon shows through, 037
    red / 063 purple) inside a dark ring and a tan rim; a dark rounded nose pointing up."""
    def T(pts):
        return rot_pts([(cx + x * s, cy + y * s) for x, y in pts], tilt, cx, cy)
    from gen_board import rrect as _rr
    def rr_pts(x0, y0, x1, y1, rtl, rtr, rbr, rbl):
        import re as _re
        d_ = _rr(x0, y0, x1, y1, rtl, rtr, rbr, rbl)
        v_ = [float(q) for q in _re.findall(r"-?[\d.]+", d_)]
        return list(zip(v_[0::2], v_[1::2]))
    # director r3: the cranium is a DOME (an ellipse 23.8 x 21.4 whose sides bulge), not a rounded box: next to 037 / 063
    # at 6x the box read square; the jaw below is unchanged
    head = poly_path(T([(0.1 + 11.9 * math.cos(a), -1.2 + 10.7 * math.sin(a)) for a in np.linspace(0, 2 * math.pi, 96, endpoint=False)]))
    jaw = poly_path(T(rr_pts(-9.0, 2.0, 10.6, 12.0, 2.0, 2.0, 2.4, 2.2)))
    E = lambda ex, ey, rx, ry: T([(ex + rx * math.cos(a), ey + ry * math.sin(a)) for a in np.linspace(0, 2 * math.pi, 48, endpoint=False)])
    eyes = [E(-5.3, 2.2, 3.5 * eye_k, 2.6 * eye_k), E(5.0, 2.2, 3.4 * eye_k, 2.7 * eye_k)]
    holes = [E(-5.1, 2.2 + 0.55 * eye_k, 2.15 * eye_k, 1.25 * eye_k), E(4.9, 2.2 + 0.6 * eye_k, 2.05 * eye_k, 1.35 * eye_k)]
    nose = rounded(T([(0.2, 5.0), (2.2, 9.0), (-1.8, 9.0)]), 0.9 * s)
    return head, jaw, eyes, nose, holes


def _skull(d, cx, cy, s, tilt, OL, ow, drop, extra_parts=(), holes=True, eye_k=1.0, face_stops=None, span=12.0):
    """Draw the toon skull (+ extra parts sharing its outline); returns the eye-hole paths (the caller masks them out)."""
    head, jaw, eyes, nose, holes = _skull_parts(cx, cy, s, tilt, eye_k)
    parts = list(extra_parts) + [("f", head), ("f", jaw)]
    face = d.lin(face_stops or [(0, "#FFFCF3"), (0.6, "#FAF2E4"), (1, "#ECDABF")], 0, cy - span * s, 0, cy + span * s)
    d.add(*toon(parts, face, OL, ow, drop=drop))
    cl = d.clip(head, jaw)
    d.add(f'<g clip-path="{cl}"><path d="{jaw}" fill="none" stroke="#E6CAA2" stroke-opacity="0.9" stroke-width="{F(2.4 * s)}" '
          f'transform="translate(0 {F(-1.2 * s)})" filter="{d.blur(0.6 * s)}"/>'
          f'<path d="{head}" fill="none" stroke="#E5CBA6" stroke-opacity="0.7" stroke-width="{F(2.0 * s)}" transform="translate(0 {F(1.4 * s)})" '
          f'filter="{d.blur(0.7 * s)}"/></g>')
    eps = [poly_path(e) for e in eyes]
    for ep in eps:
        d.add(f'<path d="{ep}" fill="none" stroke="#E7C9A1" stroke-width="{F(2.4 * s)}" stroke-linejoin="round"/>')
        d.add(f'<path d="{ep}" fill="{OL}"/>')
    d.add(f'<path d="{nose}" fill="{OL}"/>')
    return [poly_path(h) for h in holes]


def _punch(d, holes):
    """Everything drawn so far, with the given closed paths cut out (transparent)."""
    m = d.mask(f'<rect x="0" y="0" width="{F(d.W)}" height="{F(d.H)}" fill="#FFFFFF"/>' + "".join(f'<path d="{h}" fill="#000000"/>' for h in holes))
    d.body = [f'<g mask="{m}">'] + d.body + ["</g>"]


def icon_skull(W=30, H=32):
    d = Doc(W, H)
    ox, oy = 101.0, 117.5
    cx, cy = (116.15 - ox) * 3, (132.2 - oy) * 3
    eyes = _skull(d, cx, cy, 3.0, -4.8, "#650D05", 1.25 * 3, 1.6 * 3)
    _punch(d, eyes)
    return d.svg()


def icon_skull_bones(W=38, H=38):
    d = Doc(W, H)
    ox, oy = 95.5, 114.0
    OL = "#56092E"
    s = 3.0 * 0.78
    cx, cy = (116.0 - ox) * 3, (131.9 - oy) * 3
    # crossbone ends at the four corners (knob = two lobes across the bone's diagonal) + a short neck under the skull
    ends = [(103.8, 123.0), (126.8, 121.0), (104.3, 143.8), (127.7, 141.2)]
    parts = []
    for x, y in ends:
        X, Y = (x - ox) * 3, (y - oy) * 3
        ang = math.atan2(cy - Y, cx - X)
        nx, ny = -math.sin(ang), math.cos(ang)
        # director r3: fatter bones (shaft 3.2 -> 4.0 pt, knobs 2.55 -> 2.85 pt): 063's crossbones are short and chunky
        parts.append(("s", f"M{F(X)} {F(Y)}L{F(X + math.cos(ang) * 4.5 * 3)} {F(Y + math.sin(ang) * 4.5 * 3)}", 4.0 * 3))
        for sgn in (-1, 1):
            parts.append(("f", circ(X + sgn * nx * 2.1 * 3 - math.cos(ang) * 0.3 * 3, Y + sgn * ny * 2.1 * 3 - math.sin(ang) * 0.3 * 3, 2.85 * 3)))
    eyes = _skull(d, cx, cy, s, -3.5, OL, 1.2 * 3, 1.5 * 3, extra_parts=parts, eye_k=1.15,
                 face_stops=[(0, "#FFFEF8"), (0.4, "#FEF6EA"), (0.62, "#F7ECDC"), (0.75, "#FBF4E7"), (1, "#F8EFDF")], span=16.0)
    # a tan shade on each knob's lower side (drawn over the cream, under the skull's own features is fine: they do not touch)
    _punch(d, eyes)
    return d.svg()


# ====================================================================================== 7. winged rank badge "1"
# 167 (Rocket Race page, lane 1 leader) / 171 (win-panel race bar, the leader's tile): a gold badge = a rounded DIAMOND
# (vertices N/E/S/W; gold core 31.7 x 31.7 pt at (24.0, 341.3) on 167) with a bright rim (#FFF050 top -> #FFD020 ->
# #F59A10 bottom, soft dark-orange edge #C05800), an inset orange ring #E07808, an inner orange face #FFA82A -> #F08A10;
# gold wings behind it on both sides reaching x 15 / 64 (ribbon ends: top edge sloping down toward the badge, a notched
# outer end, gold #FFC21A with a light top edge #FFE36A and an orange lower band #E08A10). The digit "1" is LIVE text
# (white, outline #800100, SPEC-ui 2.7.4) centred on the badge (frame (26.3, 18.7) pt). Ink ~49 x 34.
# Frame 52 x 38 pt at shot (13.5, 338.5) on 167 (on 171 the tile's badge: frame at (308.3, 713.8)).
def _diamond(cx, cy, R, r):
    pts = [(cx, cy - R), (cx + R, cy), (cx, cy + R), (cx - R, cy)]
    return rounded(pts, r, 10)


def _octagon(cx, cy, apothem, r):
    Rv = apothem / math.cos(math.pi / 8)
    pts = [(cx + Rv * math.cos(math.pi / 8 + k * math.pi / 4), cy + Rv * math.sin(math.pi / 8 + k * math.pi / 4)) for k in range(8)]
    return rounded(pts, r, 8)


# Measured on 167 at 12 px/pt (grid): the badge is a rounded DIAMOND with big corners (r ~7; gold 31.7 x 31.7 pt, centre
# (40.0, 357.2)); inside it a darker orange ring and an orange rounded DIAMOND face (vertices ~12 pt from the centre);
# the wings sit behind it: top edge (31, 347) -> (17.4, 342.8), a squared outer end at x 15.6 (y 344.6..354.6), bottom
# edge (17, 356.6) -> (30.4, 361.8) -- the ribbon tilts up ~17 deg; gold upper half, a fold at mid-height, a
# darker orange lower half; soft orange-brown outline #C06A08.
def rank_wings1(W=52, H=38):
    d = Doc(W, H)
    cx, cy = (40.0 - 13.5) * 3, (357.2 - 338.5) * 3
    # to-A r4 (167 at 18 px/pt, pt relative to the badge centre): each wing is TWO tiers, not one flat ribbon -- an
    # upper tier (top edge (-11.3, -10.9) -> (-24.4, -13.4), a rolled light lip ~2.5 pt along the top, a darker curled
    # outer end, down to y +4.1) over a darker orange LOWER STRIP whose outer end is inset ~1.5 pt ((-23.3, 4.4) ->
    # (-22.7, 7.5)) -- the notch -- and whose bottom edge runs to (-13.6, 9.7) under the diamond.
    P3 = lambda sgn, q: [(cx + sgn * x * 3, cy + y * 3) for x, y in q]
    upper = [(-10.5, -11.0), (-23.4, -13.6), (-24.9, -12.3), (-24.9, 3.0), (-23.8, 4.2), (-11.5, 5.6)]
    lower = [(-11.0, 1.6), (-23.3, 3.4), (-23.0, 6.3), (-21.9, 7.0), (-12.4, 9.6)]
    for sgn in (-1, 1):
        lp = rounded(P3(sgn, lower), 1.2 * 3)
        d.add(f'<path d="{lp}" fill="#2A1400" fill-opacity="0.35" transform="translate(0 3)" filter="{d.blur(2)}"/>')
        d.add(f'<path d="{lp}" fill="#B85F06" stroke="#B85F06" stroke-width="3.0" stroke-linejoin="round"/>')
        d.add(f'<path d="{lp}" fill="{d.lin([(0, "#F2A41C"), (0.5, "#EA9314"), (1, "#DA7C0C")], 0, cy + 2 * 3, 0, cy + 10 * 3)}"/>')
        d.add(f'<g clip-path="{d.clip(lp)}"><path d="{lp}" fill="none" stroke="#FFD25A" stroke-opacity="0.55" stroke-width="2.4" '
              f'transform="translate(0 1.6)" filter="{d.blur(0.7)}"/></g>')
        q = P3(sgn, upper)
        wp = rounded(q, 1.5 * 3)
        d.add(f'<path d="{wp}" fill="#2A1400" fill-opacity="0.30" transform="translate(0 2.4)" filter="{d.blur(1.6)}"/>')
        d.add(f'<path d="{wp}" fill="#C06A08" stroke="#C06A08" stroke-width="3.0" stroke-linejoin="round"/>')
        d.add(f'<path d="{wp}" fill="{d.lin([(0, "#FFE04E"), (0.14, "#FFD232"), (0.22, "#FDBE1E"), (0.55, "#F9AC1A"), (1, "#EC9214")], 0, cy - 13.6 * 3, 0, cy + 5.6 * 3)}"/>')
        cp = d.clip(wp)
        # the rolled top lip: a light band that follows the top edge, a darker crease under it; the curled outer end
        lip = P3(sgn, [(-9.0, -11.6), (-26.0, -14.8), (-26.0, -10.6), (-9.0, -8.2)])
        crease = P3(sgn, [(-9.0, -8.6), (-26.0, -11.1), (-26.0, -10.3), (-9.0, -7.8)])
        curl = P3(sgn, [(-26.0, -15.0), (-21.4, -15.0), (-21.4, 6.0), (-26.0, 6.0)])
        d.add(f'<g clip-path="{cp}">'
              f'<path d="{poly_path(lip)}" fill="#FFEA70" fill-opacity="0.85" filter="{d.blur(0.9)}"/>'
              f'<path d="{poly_path(crease)}" fill="#E08A10" fill-opacity="0.55" filter="{d.blur(0.8)}"/>'
              f'<path d="{poly_path(curl)}" fill="{d.lin([(0, "#E08A10", 0.85), (1, "#F6AE1E", 0.0)], cx + sgn * -25 * 3, 0, cx + sgn * -21.4 * 3, 0)}" filter="{d.blur(0.8)}"/>'
              f'<path d="{wp}" fill="none" stroke="#FFF4B0" stroke-opacity="0.6" stroke-width="2.4" transform="translate(0 1.8)" filter="{d.blur(0.7)}"/></g>')
    ap = 15.85 * 3
    # to-A r4: 167's corners are much rounder (a broad arc at each vertex; same 15.9 pt extent: R 20.8, r 12) and the
    # face sits ~1 pt HIGH in the rim (the rim reads thicker at the bottom: the badge's side); ring extent 11.9, face 10.7
    outer = _diamond(cx, cy, 20.8 * 3, 12.0 * 3)         # rounded vertex extent 20.8 - 12 (sqrt2 - 1) = 15.83 pt
    ring = _diamond(cx, cy - 0.5 * 3, 15.2 * 3, 8.0 * 3)
    inner = _diamond(cx, cy - 0.4 * 3, 13.6 * 3, 7.0 * 3)
    d.add(f'<path d="{outer}" fill="#2A1400" fill-opacity="0.4" transform="translate(0 3.5)" filter="{d.blur(2.2)}"/>')
    d.add(f'<path d="{outer}" fill="#C06A08" stroke="#C06A08" stroke-width="3" stroke-linejoin="round"/>')
    d.add(f'<path d="{outer}" fill="{d.lin([(0, "#FFF36E"), (0.18, "#FFE23A"), (0.5, "#FFCC20"), (0.8, "#F9AE14"), (1, "#F0920E")], 0, cy - ap, 0, cy + ap)}"/>')
    d.add(f'<g clip-path="{d.clip(outer)}"><path d="{outer}" fill="none" stroke="#FFFBD0" stroke-opacity="0.8" stroke-width="3.2" '
          f'transform="translate(0 2.6)" filter="{d.blur(0.9)}"/>'
          f'<path d="{outer}" fill="none" stroke="#D07A0A" stroke-opacity="0.5" stroke-width="4" transform="translate(0 -2.4)" filter="{d.blur(1.4)}"/></g>')
    d.add(f'<path d="{ring}" fill="{d.lin([(0, "#D8700A"), (1, "#E88C14")], 0, cy - ap, 0, cy + ap)}"/>')
    d.add(f'<path d="{inner}" fill="{d.lin([(0, "#FFB038"), (0.45, "#FFA024"), (1, "#F48C12")], 0, cy - ap, 0, cy + ap)}"/>')
    d.add(f'<g clip-path="{d.clip(inner)}"><path d="{inner}" fill="none" stroke="#C86004" stroke-opacity="0.5" stroke-width="4" '
          f'transform="translate(0 2.4)" filter="{d.blur(1.2)}"/></g>')
    return d.svg()


# ====================================================================================== 8. shop discount seal
# meta-012 Special Offer card: a red scalloped seal with 8 lobes (radius profile of the red body: harmonic 8 dominant,
# valleys 23.4 pt / peaks 26.9 pt, peaks at 35 + 45 k deg), centre (34.4, 216.3); a gold rim ~3.2 pt outside the red
# (#FFE070 top-left -> #FFC830 -> #F09010 bottom, a dark-orange outer edge #B85A00), a dark-red line #7A0010 between rim
# and body, the body #F4101A top -> #E0000F -> #C8000C bottom with a light inner line #FF5A5A along the upper-left. The
# "90%" / "OFF" (TR "%90" / "İNDİRİM") are LIVE text (SPEC-ui 2.12.2), tilted -12 deg in the capture.
# Frame 66 x 66 pt at shot (1.4, 183.3): the seal centre at the frame centre.
SEAL = dict(n=8, phase=35.0, R0=22.0, rb=10.25, Rc=16.65, rim=3.4)   # peaks 26.9, valleys (circle crossings) 23.4 pt


def _scallop(cx, cy, n, phase, R0, rb, Rc, grow=0.0, step=0.75):
    """ONE outline: the union of a disk R0 and n circles rb on a ring Rc (px), grown by `grow` (exact union field)."""
    Rmax = Rc + rb + grow + 4
    X, Y = np.meshgrid(np.arange(cx - Rmax, cx + Rmax, step), np.arange(cy - Rmax, cy + Rmax, step))
    D = np.hypot(X - cx, Y - cy) - (R0 + grow)
    for i in range(n):
        a = math.radians(phase + 360.0 * i / n)
        D = np.minimum(D, np.hypot(X - cx - Rc * math.cos(a), Y - cy - Rc * math.sin(a)) - (rb + grow))
    return [poly_path(_contour(D, cx - Rmax, cy - Rmax, step))]


def shop_seal(W=66, H=66):
    d = Doc(W, H)
    K = SEAL
    cx, cy = W * 1.5, H * 1.5
    s = 3.0
    rim = _scallop(cx, cy, K["n"], K["phase"], K["R0"] * s, K["rb"] * s, K["Rc"] * s, grow=K["rim"] * s)
    body = _scallop(cx, cy, K["n"], K["phase"], K["R0"] * s, K["rb"] * s, K["Rc"] * s)
    R = (K["Rc"] + K["rb"] + K["rim"]) * s
    g = lambda ds, extra: "".join(f'<path d="{p}" {extra}/>' for p in ds)
    d.add(f'<g fill="#1F0A0D" fill-opacity="0.45" transform="translate(0 3.5)" filter="{d.blur(2.4)}">{g(rim, "")}</g>')
    d.add(f'<g fill="#A84E00" stroke="#A84E00" stroke-width="3" stroke-linejoin="round">{g(rim, "")}</g>')
    d.add(f'<g fill="{d.lin([(0, "#FFE474"), (0.3, "#FFCC34"), (0.7, "#F9A818"), (1, "#EE8C0C")], cx - R * 0.5, cy - R, cx + R * 0.3, cy + R)}">{g(rim, "")}</g>')
    rc = d.clip(*rim)
    d.add(f'<g clip-path="{rc}"><g fill="none" stroke="#FFF4D7" stroke-opacity="0.85" stroke-width="3.2" transform="translate(1 2.6)" '
          f'filter="{d.blur(1.0)}">{g(rim, "")}</g>'
          f'<g fill="none" stroke="#C86A04" stroke-opacity="0.6" stroke-width="3.6" transform="translate(-1 -2.6)" filter="{d.blur(1.2)}">{g(rim, "")}</g></g>')
    d.add(f'<g fill="#751009" stroke="#751009" stroke-width="{F(1.9 * s)}" stroke-linejoin="round">{g(body, "")}</g>')
    d.add(f'<g fill="{d.lin([(0, "#EE4934"), (0.3, "#E23A28"), (0.7, "#D03020"), (1, "#BC2416")], 0, cy - R, 0, cy + R)}">{g(body, "")}</g>')
    bc = d.clip(*body)
    d.add(f'<g clip-path="{bc}"><g fill="none" stroke="#EF7763" stroke-opacity="0.9" stroke-width="{F(0.8 * s)}" transform="translate(1.5 2.6)">{g(body, "")}</g>'
          f'<g fill="none" stroke="#95150C" stroke-opacity="0.5" stroke-width="{F(1.4 * s)}" transform="translate(-1 -3)" filter="{d.blur(1.2)}">{g(body, "")}</g></g>')
    return d.svg()


# ====================================================================================== 9. page ground pattern (tile)
# meta-029 (Settings; SPEC-ui 1.6.9: also Leaderboard / Claw / Shop-bundles): the navy page ground carries faint chunky
# ARROWS, lighter than the ground by (0, +4, +3.5) RGB (contrast-stretched crops): two per repeat, one pointing up and
# tilted ~+25 deg (r2, from a stretched side-by-side: ~31 x 40 pt overall -> head 36.6 across, 30.5 long; shaft 20.7 x
# 13.4), centred (177.5, 670) and every (145, 79.3) pt; one pointing DOWN tilted ~+29 deg toward the left, centred
# (+72.5, -30) pt from the first. Tile 145 x 79 pt, transparent, the arrows #0B4A97 at alpha 0.10 (over the navy ground
# #0B2176..#0A1F72 that is (0, +4.2, +3.5): the measured lift); they wrap across the tile edges. PHASE (screen pt): tile
# origins at x = 145 i, y = -7 + 79 j (the capture's tile at (145, 625) puts the first arrow on (177.5, 670)).
PATTERN = dict(W=145, H=79, a=(32.5, 45.0, 25.0), b=(105.0, 15.0, 209.0), fill="#0B4A97", alpha=0.10)


def _block_arrow(cx, cy, deg, head_w=36.6, head_l=30.5, shaft_w=20.7, shaft_l=13.4, r=4.0):
    """A chunky arrow pointing UP (before rotation), centred on its bbox; pt -> px."""
    Lt = head_l + shaft_l
    top = -Lt / 2
    pts = [(0, top), (head_w / 2, top + head_l), (shaft_w / 2, top + head_l), (shaft_w / 2, Lt / 2), (-shaft_w / 2, Lt / 2),
           (-shaft_w / 2, top + head_l), (-head_w / 2, top + head_l)]
    P = [(cx * 3 + x * 3, cy * 3 + y * 3) for x, y in pts]
    return rounded(rot_pts(P, deg, cx * 3, cy * 3), r * 3, 6)


def page_bg_pattern(W=None, H=None):
    K = PATTERN
    W, H = W or K["W"], H or K["H"]
    d = Doc(W, H)
    shapes = []
    for (x, y, deg) in (K["a"], K["b"]):
        for dx in (-W, 0, W):
            for dy in (-H, 0, H):
                shapes.append(_block_arrow(x + dx, y + dy, deg))
    d.add(f'<g fill="{K["fill"]}" fill-opacity="{F(K["alpha"])}">' + "".join(f'<path d="{p}"/>' for p in shapes) + "</g>")
    return d.svg()


# ====================================================================================== 10. the Weekly tutorial pointer
# 130 (L50 Weekly Contest tutorial, pointing at the Leaderboard tab): a STRAIGHT down block arrow (not the curved Claw
# info pointer). Row extents: shaft x 307.2-340.7 (33.5 wide, centre 324.0) from y 638.7; head from y ~686, 72 across
# (288.0-360.1) at y 697 with rounded wing tips; tip (324.2, 736.0). Profiles: orange rim #F28A15 / #F89116 ~2.2 pt
# (#DB6D11 on the right), a light line #FDCB46..#FFE966 ~1 pt inside it, the face #FFAE09 (shaft top) -> #FFB70C ->
# #FFCE12 (head) -> yellower at the tip; corners r ~4.5 pt. Frame 78 x 104 pt at shot (285.0, 635.2).
def round_poly_var(pts, rs, n=8):
    """gen_board._round_poly with a radius per vertex (distance along each edge, clamped to half the edge)."""
    out = []
    N = len(pts)
    for i in range(N):
        p0, p1, p2 = pts[i - 1], pts[i], pts[(i + 1) % N]
        d1 = math.hypot(p0[0] - p1[0], p0[1] - p1[1]); d2 = math.hypot(p2[0] - p1[0], p2[1] - p1[1])
        r_ = min(rs[i], d1 / 2, d2 / 2)
        if r_ < 0.2:
            out.append(p1); continue
        a_ = (p1[0] + (p0[0] - p1[0]) * r_ / d1, p1[1] + (p0[1] - p1[1]) * r_ / d1)
        b_ = (p1[0] + (p2[0] - p1[0]) * r_ / d2, p1[1] + (p2[1] - p1[1]) * r_ / d2)
        for k in range(n + 1):
            t = k / n
            out.append(((1 - t) ** 2 * a_[0] + 2 * (1 - t) * t * p1[0] + t * t * b_[0],
                        (1 - t) ** 2 * a_[1] + 2 * (1 - t) * t * p1[1] + t * t * b_[1]))
    return poly_path(out)


# Head geometry from the row extents: the diagonal edges pass x 301.7 at y 715 and 310.4 at 725 (slope 0.87) down to the
# tip vertex (c, 740.6) (rounded: visible tip 736); the wings end in a short rounded outer side at c -+ 36 from y 686 to
# 700 (widest 72 pt at y 697, as measured).
def pointer_arrow_down(W=78, H=104):
    d = Doc(W, H)
    ox, oy = 285.0, 635.2
    P = lambda x, y: ((x - ox) * 3, (y - oy) * 3)
    c = 324.0
    pts = [P(c - 16.75, 638.9), P(c + 16.75, 638.9), P(c + 16.75, 686.0), P(c + 36.0, 686.0), P(c + 36.0, 700.0), P(c, 740.6),
           P(c - 36.0, 700.0), P(c - 36.0, 686.0), P(c - 16.75, 686.0)]
    R = [4.6, 4.6, 1.2, 6.5, 7.0, 11.0, 7.0, 6.5, 1.2]
    outer = round_poly_var(pts, [r * 3 for r in R])
    d.add(f'<path d="{outer}" fill="#000000" fill-opacity="0.35" transform="translate(0 4)" filter="{d.blur(3)}"/>')
    d.add(f'<path d="{outer}" fill="{d.lin([(0, "#F28A15"), (0.6, "#F7931A"), (1, "#F59A1C")], 0, pts[0][1], 0, pts[4][1])}"/>')
    d.add(f'<g clip-path="{d.clip(outer)}"><rect x="{F(P(c + 14, 0)[0])}" y="0" width="{F(40 * 3)}" height="{F(d.H)}" fill="#DB6D11" '
          f'fill-opacity="0.45" filter="{d.blur(3)}"/></g>')
    # inset face: the polygon pulled in by 2.3 / 3.3 pt (per-edge offset), rounded a little less
    light = round_poly_var(_inset(pts, 2.3 * 3), [max(0.6, r - 2.0) * 3 for r in R])
    face = round_poly_var(_inset(pts, 3.3 * 3), [max(0.4, r - 3.0) * 3 for r in R])
    d.add(f'<path d="{light}" fill="{d.lin([(0, "#FDCB46"), (0.5, "#FFD650"), (1, "#FFE966")], 0, pts[0][1], 0, pts[4][1])}"/>')
    d.add(f'<path d="{face}" fill="{d.lin([(0, "#FFAC08"), (0.28, "#FFB70C"), (0.55, "#FFC410"), (0.82, "#FFCE12"), (1, "#FFD41C")], 0, pts[0][1], 0, pts[4][1])}"/>')
    return d.svg()


def _inset(pts, dist):
    """Offset a convex-ish CLOCKWISE polygon (screen coords) inward by dist: each edge moved along its inner normal,
    consecutive edges intersected."""
    n = len(pts)
    lines = []
    for i in range(n):
        (x0, y0), (x1, y1) = pts[i], pts[(i + 1) % n]
        dx, dy = x1 - x0, y1 - y0
        L = math.hypot(dx, dy)
        nx, ny = -dy / L, dx / L          # inner normal for a clockwise polygon on screen (y down)
        lines.append(((x0 + nx * dist, y0 + ny * dist), (dx, dy)))
    out = []
    for i in range(n):
        (p, r), (q, s) = lines[i - 1], lines[i]
        den = r[0] * s[1] - r[1] * s[0]
        if abs(den) < 1e-9:
            out.append(q); continue
        t = ((q[0] - p[0]) * s[1] - (q[1] - p[1]) * s[0]) / den
        out.append((p[0] + r[0] * t, p[1] + r[1] * t))
    return out


# ====================================================================================== 11. Settings OFF slash
# meta-029 (Music OFF) / meta-030 (Sound tapped OFF): a glossy red rod across the SquareToggle's glyph, top-right ->
# bottom-left, identical on every button: red ink 49.0 x 44.0 pt, centred 2.5 pt ABOVE the button face centre (music:
# (195.2, 342.7) vs face centre (195.15, 345.15)); rod ~6.6 pt thick with round caps, axis from (-24.2, +16.8) to
# (+21.0, -23.6) pt of the face centre; a white-pink highlight along its upper edge (#FF9A9A -> white), core #FF2626,
# lower edge #CD0000 -> #9A0000, a soft dark shadow under it. SPEC-ui 1.6.14 draws it in SwiftUI; this sprite is the
# same thing as art, optional for the shell. Frame 56 x 52 pt, anchor = the button face centre at frame (28.6, 28.4) pt.
SLASH = dict(a=(-21.4, 17.4), b=(21.05, -20.95), w=7.6, anchor=(28.6, 28.4))   # cap centres from the red extents


def glyph_off_slash(W=56, H=52):
    d = Doc(W, H)
    ax, ay = SLASH["anchor"]
    (x0, y0), (x1, y1) = SLASH["a"], SLASH["b"]
    A = ((ax + x0) * 3, (ay + y0) * 3)
    B = ((ax + x1) * 3, (ay + y1) * 3)
    w = SLASH["w"] * 3
    ln = f"M{F(A[0])} {F(A[1])}L{F(B[0])} {F(B[1])}"
    ang = math.degrees(math.atan2(B[1] - A[1], B[0] - A[0]))
    st = 'fill="none" stroke-linecap="round"'
    d.add(f'<path d="{ln}" {st} stroke="#572300" stroke-opacity="0.45" stroke-width="{F(w + 3)}" transform="translate(1.5 4.5)" filter="{d.blur(2.4)}"/>')
    d.add(f'<path d="{ln}" {st} stroke="#8E0000" stroke-width="{F(w + 1.5)}"/>')
    # the rod's cross-section shading: a gradient perpendicular to the axis (upper edge light, lower edge dark)
    mx, my = (A[0] + B[0]) / 2, (A[1] + B[1]) / 2
    t = math.radians(ang - 90)
    ux, uy = math.cos(t) * w / 2, math.sin(t) * w / 2        # toward the upper-left side of the rod
    grad = d.lin([(0, "#A41206"), (0.3, "#D0311F"), (0.55, "#EE4630"), (0.78, "#EE6F5C"), (0.9, "#F6B4A7"), (1, "#F18471")],
                 mx - ux, my - uy, mx + ux, my + uy)
    d.add(f'<path d="{ln}" {st} stroke="{grad}" stroke-width="{F(w)}"/>')
    d.add(f'<path d="{ln}" {st} stroke="#FFFFFF" stroke-opacity="0.75" stroke-width="{F(w * 0.16)}" '
          f'transform="translate({F(ux * 0.55)} {F(uy * 0.55)})" filter="{d.blur(0.5)}"/>')
    return d.svg()


# ====================================================================================== cases
CASES = {
    "iconStopwatchFrozen": icon_stopwatch_frozen,
    "frostCracks": frost_cracks,
    "heartBig": heart_big,            # SVG route (SPEC-ui said B3; the missing-3d lane keeps its 3D heart as a route candidate)
    "heartGlossySmall": heart_glossy_small,
    "heartLivesBig": heart_lives_big,
    "iconVideoAd": icon_video_ad,
    "iconCheck": icon_check,
    "iconCheckBadge": icon_check_badge,
    "iconSkull": icon_skull,
    "iconSkullBones": icon_skull_bones,
    "rankWings1": rank_wings1,
    "shopSeal": shop_seal,
    "pageBgPattern": page_bg_pattern,
    "pointerArrowDown": pointer_arrow_down,
    "glyphOffSlash": glyph_off_slash,
}


if __name__ == "__main__":
    out = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(HERE)))), "build", "ui-art", "svgsrc")
    os.makedirs(out, exist_ok=True)
    for n in sys.argv[1:] or list(CASES):
        r = CASES[n]()
        svg = r[0] if isinstance(r, tuple) else r
        open(os.path.join(out, f"{n}.svg"), "w", encoding="utf-8").write(svg)
        print("wrote", os.path.join(out, f"{n}.svg"))
