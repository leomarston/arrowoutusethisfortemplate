"""Loading screen backdrop: loadingBackdrop. Rendered by scene_make.py.

Round 4 (loading-scene lane, 2026-09-25): rebuilt on the PHONE frame. The phone's loading art is store 8 scaled by
0.8925 and shifted (-6.5, -0.5) pt (NCC 0.993 on the parts the notification alert of research/kickoff/state.png does
not cover; `loading_scene_proofs.py` draws the registered copy), so every number below is phone pt, measured on that
registered frame and on state.png. The captures were LOOKED AT only (gridded crops, tone samples, seam maps); every
shape is written here from those numbers and every colour is a hex chosen here.

Layers, back to front (the characters, logoArrowOut and the live "Loading" label are composited over it in-app):
  room      purple vaulted ceiling (ribs, two dark tubes, a vertical pipe), the backlit opening at the right (rounded
            top-left corner, lintel lip, lit jamb, distant crates, the pale pole under the purple arrow), the violet mid
            wall, the back room under the press (light shaft, far floor) + the 3D cardboard stack -> defocused
  floor     big bevelled tiles on the floor plane FITTED to the capture's seams (homography, RMS 2.7 pt: the "+" joint
            at (272, 712), the long seam to the bottom edge at x ~200, the cross seams y ~590 / ~700), grooves with a
            lit far edge, cool blue-grey tone ladder, the opening's sheen, far tiles defocused
  conveyor  the stepped lilac platform at the left edge (the clipboard worker's deck, the round deck the two
            back-view workers stand on) with the yellow / plum hazard side and its floor shadow
  press     the long machine on the left wall receding to the right: navy-edged blue housing (slot marks), the pale
            rounded lip wrapping its end, the magenta -> pastel pink panel with a lit end face, the lilac girder (lit
            top bevel, a groove, a darker lower band, ridged underside) with two cream-pink push buttons in violet rings
  props     the blue U pipe at the top left, the paper sheets on the floor at the right edge
  3D        the flying block arrows (red tail block top left, purple top right, pale green + blue under the logo) and
            the floor cable with its plug (our SDF models, mfrender)
  cast      soft contact shadows + faint glossy-floor reflections under the grounded cast, baked from
            art/out/char_loading_layout.json and the characters' own renders (re-run this build when they move)
"""
from __future__ import annotations

import json
import math
import os
import sys

import numpy as np
from PIL import Image

from scene_kit import (Canvas, Part, aa, blur, cylinder, extrude, gloss, rbox, rgb, rig, rot_x, rot_y, rot_z, satin,
                       smooth, stops_interp, path_tube)

_M = sys.modules[__name__]


def W(sx, sy, z=0.0):
    return (sx / 10.0, -sy / 10.0, z)


# ====================================================================== 3D models
def boxes():
    """The cardboard stack behind the conveyor (store 8 / state: a wide box x 5..73, y 438..470 under a flatter one
    x 17..70, y 424..440; both turned a little so their right ends show)."""
    parts = []
    card = satin("ld_card", "#DDB38A", rough=0.55, ior=1.2)
    for (sx, sy, w, h, d, yaw) in ((38.0, 454.0, 6.2, 3.1, 4.2, -16), (43.0, 432.0, 5.0, 1.6, 3.6, -12)):
        parts.append(Part(f"box{int(sx)}{int(sy)}", rbox(w, h, d, 0.10).rotate_y(yaw).translate(*W(sx, sy, 0.0)), card,
                          voxel=0.03))
    return parts, 0.03


def _catmull(pts, n=10):
    """A smooth curve through control points (Catmull-Rom, n samples per span)."""
    P = np.asarray(pts, float)
    P = np.vstack([P[0] * 2 - P[1], P, P[-1] * 2 - P[-2]])
    out = []
    for i in range(1, len(P) - 2):
        p0, p1, p2, p3 = P[i - 1], P[i], P[i + 1], P[i + 2]
        for t in np.linspace(0, 1, n, endpoint=False):
            t2, t3 = t * t, t * t * t
            out.append(0.5 * (2 * p1 + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t2 + (-p0 + 3 * p1 - 3 * p2 + p3) * t3))
    out.append(P[-2])
    return [tuple(q) for q in out]


def _sweep(name, pts_pt, r, material, z=0.3, nv=28):
    """A premeshed tube swept along a planar screen-space curve (pt) -- a union of hundreds of round cones through
    marching cubes took ~155 s; the sweep takes well under a second and is exactly smooth."""
    from scene_kit import grid_part
    P = np.array([W(x, y, z) for x, y in pts_pt], float)
    L = np.concatenate([[0], np.cumsum(np.linalg.norm(np.diff(P, axis=0), axis=1))])
    L /= L[-1]
    T = np.gradient(P, axis=0)
    T /= np.maximum(np.linalg.norm(T, axis=1, keepdims=True), 1e-9)
    Z = np.array([0.0, 0.0, 1.0])
    N = np.cross(Z, T)
    N /= np.maximum(np.linalg.norm(N, axis=1, keepdims=True), 1e-9)

    def fn(u, v):
        idx = np.clip(np.searchsorted(L, u) - 1, 0, len(L) - 2)
        f = np.clip((u - L[idx]) / np.maximum(L[idx + 1] - L[idx], 1e-9), 0, 1)[..., None]
        c = P[idx] * (1 - f) + P[idx + 1] * f
        n = N[idx] * (1 - f) + N[idx + 1] * f
        a = (v * 2 * math.pi)[..., None]
        return c + r * (np.cos(a) * n + np.sin(a) * Z)
    part = grid_part(name, material, fn, len(P) * 2, nv, flip=True)
    return part


CABLE_PTS = [(-14, 697), (18, 699), (44, 707), (59, 724), (62, 746), (53, 768), (43, 789), (49, 806), (70, 814),
             (100, 815), (134, 812), (165, 812), (200, 815), (240, 827), (290, 846), (340, 870)]


def cable():
    """The floor cable (state.png / store 8: in from the left edge at y ~697, a loop down past x ~62 to y ~790, then
    right along y ~814 through the plug x 133..165 and off the bottom right), a smooth spline ~7 pt thick."""
    parts = [_sweep("cable", _catmull(CABLE_PTS, 12), 0.37, satin("ld_cable", "#8189CE", rough=0.30))]
    plug = cylinder(0.74, 1.55, round=0.22).rotate_z(90).translate(*W(149, 812, 0.3))
    parts.append(Part("plug", plug, satin("ld_plug", "#5A5F9F", rough=0.36), voxel=0.025))
    ring = cylinder(0.78, 0.2, round=0.08).rotate_z(90).translate(*W(160.5, 812, 0.3))
    parts.append(Part("plugRing", ring, satin("ld_plugring", "#8288CC", rough=0.3), voxel=0.02))
    return parts, 0.025


BLOCK_SHADES = {"red": ("#F0373D", "#C21A2C", "#961222", "#FF6E6E"),
                "purple": ("#9B3BF0", "#7420D0", "#5714A8", "#C184FA"),
                "green": ("#A9D77F", "#7FB957", "#5E9A3E", "#D2F0B4"),
                "blue": ("#8EC0F6", "#5E97E4", "#3F77C8", "#C0DEFC")}


def block_arrow(color):
    """The loading screen's chunky flying arrow (store 8's purple: head 64 pt wide, head length ~0.62 of that, shaft
    0.55 wide and ~0.7 long), painted bevel like the pile arrows."""
    import scene_home as H
    from dataclasses import replace
    from arrows3d import arrow2d
    s2 = arrow2d(shaft=0.70, t=0.275, hl=0.62)
    c = (s2.lo + s2.hi) / 2
    s2c = s2.translate(-c[0], -c[1])
    body = extrude(s2c, 0.30, round=0.12).scale(3.2)
    lo = (float(s2c.lo[0]) - 0.05, float(s2c.lo[1]) - 0.05)
    size = float(max(s2c.hi - s2c.lo)) + 0.1
    sh = BLOCK_SHADES[color]
    m = gloss(f"lb_{color}", sh[0], rough=0.30, ior=1.42)
    m = replace(m, texture=H._pile_bevel(s2c, lo, size, color, band=0.13, shades=sh), texture_size=512)
    uv = ("planar", (lo[0] * 3.2, lo[1] * 3.2, 0.0), (1, 0, 0), (0, 1, 0), 1.0 / (size * 3.2))
    return [Part("arrow", body, m, uv=uv)], 0.02


MODELS = {"boxes": boxes, "cable": cable}
for _c in BLOCK_SHADES:
    MODELS[f"block_arrow_{_c}"] = (lambda c=_c: block_arrow(c))


# ====================================================================== 2D helpers (pt coordinates)
def sd_poly(X, Y, pts):
    """Exact signed distance (pt) to a polygon, < 0 inside."""
    P = np.asarray(pts, float)
    d = np.full(X.shape, np.inf)
    s = np.ones(X.shape)
    for i in range(len(P)):
        ax, ay = P[i]
        bx, by = P[(i + 1) % len(P)]
        ex, ey = bx - ax, by - ay
        wx, wy = X - ax, Y - ay
        t = np.clip((wx * ex + wy * ey) / (ex * ex + ey * ey), 0, 1)
        dx, dy = wx - ex * t, wy - ey * t
        d = np.minimum(d, dx * dx + dy * dy)
        c1 = Y >= ay
        c2 = Y < by
        c3 = ex * wy > ey * wx
        flip = (c1 & c2 & c3) | (~c1 & ~c2 & ~c3)
        s = np.where(flip, -s, s)
    return s * np.sqrt(d)


def rounded(cov, r_pt):
    """Round a coverage mask's convex corners (blur + re-threshold), r in pt."""
    if r_pt <= 0:
        return cov
    b = blur(cov, r_pt * 3 * 0.5)
    return smooth(b, 0.30, 0.70)


def polyline(X, Y, pts):
    """Distance (pt) to a polyline, the signed perpendicular offset (+ = left of the direction of travel in screen
    space, i.e. 'up' for a left-to-right line) and the arc-length parameter in [0, 1]."""
    P = np.asarray(pts, float)
    seg = np.hypot(*np.diff(P, axis=0).T)
    cum = np.concatenate([[0], np.cumsum(seg)])
    best = np.full(X.shape, np.inf)
    side = np.zeros(X.shape)
    par = np.zeros(X.shape)
    for i in range(len(P) - 1):
        ax, ay = P[i]
        bx, by = P[i + 1]
        ex, ey = bx - ax, by - ay
        L2 = ex * ex + ey * ey
        wx, wy = X - ax, Y - ay
        t = np.clip((wx * ex + wy * ey) / L2, 0, 1)
        dx, dy = wx - ex * t, wy - ey * t
        d = np.sqrt(dx * dx + dy * dy)
        m = d < best
        best = np.where(m, d, best)
        cr = (ex * wy - ey * wx) / math.sqrt(L2)      # > 0: right of travel in screen space (y down)
        side = np.where(m, -cr, side)
        par = np.where(m, (cum[i] + t * seg[i]) / cum[-1], par)
    return best, side, par


def tube(cv, pts, width, dark, mid, light, hi=None, alpha=1.0, soft=0.5, light_side=1.0):
    """A painted cylinder along a polyline: dark edges, a lit band offset toward `light_side` (+1 = the 'up' side),
    an optional thin specular line. width may be a number or (w0, w1) along the path."""
    d, s, t = polyline(cv.X, cv.Y, pts)
    w = width if np.isscalar(width) else width[0] + (width[1] - width[0]) * t
    cov = aa(d - w / 2, soft)
    q = np.clip(s / np.maximum(w / 2, 1e-3), -1, 1) * light_side          # -1 .. 1 across, +1 toward the light
    col = stops_interp(q, [(-1.0, dark), (-0.35, mid), (0.35, light), (1.0, mid)])
    if hi is not None:
        col = col + (rgb(hi) - col) * (np.exp(-((q - 0.45) / 0.14) ** 2) * 0.7)[..., None]
    src = np.zeros((cv.h, cv.w, 4))
    src[..., :3] = col
    src[..., 3] = cov * alpha
    cv.over(src)


def line(a, b):
    """y = a + b x."""
    return lambda x: a + b * x


def band_t(X, Y, top, bot):
    return (Y - top(X)) / np.maximum(bot(X) - top(X), 1e-3)


def layer(cv):
    """An empty transparent canvas the size of cv."""
    L = Canvas(cv.w / 3, cv.h / 3)
    return L


def blur_over(cv, L, sigma_pt, alpha=1.0):
    """Composite layer L onto cv after a Gaussian blur of sigma_pt (premultiplied, so edges do not darken)."""
    a = L.a
    if sigma_pt > 0:
        pre = a[..., :3] * a[..., 3:4]
        pre = blur(pre, sigma_pt * 3)
        al = blur(a[..., 3], sigma_pt * 3)
        out = np.zeros_like(a)
        out[..., :3] = pre / np.maximum(al[..., None], 1e-6)
        out[..., 3] = al
        a = out
    cv.over(a, alpha_mul=alpha)


# ====================================================================== measured geometry
# The press (left wall machine), lines y = a + b x fitted to the band edges sampled at x = 5, 30, 60, 90 pt:
T_TOP = line(157.0, 0.72)      # the blue housing's navy top edge
R_TOP = line(184.0, 0.85)      # housing -> pale lip
P_TOP = line(202.0, 0.81)      # lip -> pink panel (a dark crease)
B_TOP = line(254.0, 0.62)      # pink panel -> girder top
def B_MID(x):                  # girder face -> underside (bends: 329 / 341 / 355 / 358 at x 5 / 30 / 60 / 90)
    return 327.0 + 0.50 * x - 0.0018 * x * x


B_BOT = line(359.0, 0.30)      # underside -> the lit back room
BUTTONS = ((25.0, 297.0, 12.5, 13.0), (54.0, 312.5, 12.0, 12.5))

# The floor plane: homography (u, v, 1) -> (x, y, w) pt, fitted by least squares to the capture's seams (u = the
# seams receding to the upper right, v = the cross seams; u 0 / v 0 = the "+" joint at (272, 712)); RMS 2.7 pt.
FLOOR_H = np.array([[2.00101572e+02, -2.24275660e+02, 2.71544266e+02],
                    [-5.58312950e+01, -1.57190857e+02, 7.11796272e+02],
                    [-1.03401216e-01, -4.69933195e-01, 1.0]])

# The backlit opening at the right: left edge x ~168 (the first bright column above the scientist's head at y 260 /
# 300: x 167 / 172), top edge falling to the right, rounded top-left corner.
OPEN_X0 = 168.0
OPEN_TOP = line(280.0, -0.2)   # y at x: 240 at x 200, 201 at x 393
OPEN_R = 26.0


# ====================================================================== painted structure
def paint_room(cv):
    """Ceiling, lintel + opening, mid wall, back room (opaque, painted onto cv)."""
    X, Y = cv.X, cv.Y
    cv.a[..., :3] = stops_interp(Y, [(0, "#5640AC"), (60, "#5A44B0"), (120, "#5542AE"), (200, "#5140AA"),
                                     (300, "#6A55BC")])
    cv.a[..., 3] = 1.0
    # the vault is lighter toward the top right (x ~240-393, y 0-80), darker toward the lintel (y 120-200 at the right)
    cv.screen(np.exp(-(((X - 330) / 120.0) ** 2 + ((Y - 25) / 60.0) ** 2)), "#7560C8", 0.30)
    cv.multiply(np.exp(-(((X - 380) / 90.0) ** 2 + ((Y - 165) / 40.0) ** 2)), "#3A2A96", 0.30)
    cv.multiply(np.exp(-(((X - 0) / 60.0) ** 2 + ((Y - 0) / 50.0) ** 2)), "#3A2A90", 0.20)
    # vault ribs: faint lighter arcs (panel seams of the barrel ceiling)
    for (x0, y0, x1, y1, bow, w) in ((105, 44, 400, 16, 10, 2.2), (215, 110, 400, 86, 8, 2.0), (-10, 34, 36, -6, 3, 3.0),
                                     (120, 150, 230, 130, 6, 1.6)):
        n = 24
        tt = np.linspace(0, 1, n)
        pts = [(x0 + (x1 - x0) * t, y0 + (y1 - y0) * t - bow * 4 * t * (1 - t)) for t in tt]
        d, s, _ = polyline(X, Y, pts)
        cv.fill(aa(d - w / 2, 0.8), "#7461C9", 0.55)
        cv.multiply(aa(np.abs(d - w / 2 - 1.2) - 0.8, 0.8) * (s < 0), "#3A2A8C", 0.35)
    # dark tubes: slanted (190, -5) -> (258, 126), the vertical pipe at x ~270, a slanted one behind the red block
    tube(cv, [(190, -6), (224, 60), (258, 126)], 8.0, "#231A63", "#2F2474", "#44359A", hi="#5A4AB2")
    tube(cv, [(267, -6), (270, 60), (275, 124)], 6.5, "#221961", "#2B2170", "#3E3094", hi="#5243AA")
    cv.fill(aa((np.hypot((X - 275.5) / 5.5, (Y - 126) / 3.2) - 1) * 3.2, 0.5), "#2B2170")
    tube(cv, [(18, -6), (48, 44), (78, 96)], 6.0, "#261C68", "#302575", "#45369C")
    tube(cv, [(119, 26), (121, 72)], 4.5, "#211860", "#2B2170", "#3D3092")
    # the lintel over the opening: a darker band above it, a lit lip on the edge
    top = OPEN_TOP(X)
    lint = np.clip((Y - (top - 34)) / 34.0, 0, 1) * (X > OPEN_X0 - 20) * (Y < top + 2)
    cv.multiply(lint * aa(OPEN_X0 - 20 - X, 6), "#3B2A92", 0.35)
    # the mid wall between the press and the opening (x 108..148)
    wall = stops_interp(Y, [(190, "#5D48AF"), (300, "#8069C8"), (420, "#B39DE2"), (480, "#CDBDEE")])
    m = aa(-(Y - 188), 2.0) * aa(-(X - 100), 2.0)
    src = np.zeros((cv.h, cv.w, 4))
    src[..., :3] = wall
    src[..., 3] = m
    cv.over(src)
    # a pillar between the press and the opening (x ~104..126, y 185..320): a lighter violet column with a lit left edge
    pil = sd_poly(X, Y, [(104, 180), (126, 176), (126, 330), (104, 330)])
    cv.fill(rounded(aa(pil, 0.8), 3.0), stops_interp(Y, [(180, "#6F5ABF"), (320, "#9C88DA")]))
    cv.fill(aa(np.abs(X - 105.5) - 1.2, 0.6) * aa(pil, 0.8), "#B2A2E6", 0.7)
    cv.multiply(aa(np.abs(X - 124.5) - 1.5, 0.8) * aa(pil, 0.8), "#4A3A9E", 0.35)
    # the lit jamb (x 148..168): a lighter vertical face, brighter at its bottom
    jamb = sd_poly(X, Y, [(148, OPEN_TOP(148) + 6), (OPEN_X0, OPEN_TOP(OPEN_X0) + 2), (OPEN_X0, 500), (148, 500)])
    cv.fill(aa(jamb, 0.8), stops_interp(Y, [(230, "#8672D2"), (330, "#B6A2E6"), (470, "#E2D5F6")]))
    cv.fill(aa(np.abs(X - OPEN_X0 + 1.2) - 1.0, 0.6) * (Y > OPEN_TOP(OPEN_X0) + 20) * (Y < 500), "#F2EAFB", 0.8)
    # the opening: a rounded-corner hole full of light
    qx = np.maximum(OPEN_X0 + OPEN_R - X, 0)
    qy = np.maximum(top + OPEN_R - Y, 0)
    corner = (X < OPEN_X0 + OPEN_R) & (Y < top + OPEN_R)
    d_open = np.where(corner, np.hypot(qx, qy) - OPEN_R, np.maximum(OPEN_X0 - X, top - Y))
    op = aa(d_open, 0.8) * (Y < 505)
    glow = stops_interp(np.hypot((X - 330) / 120.0, (Y - 330) / 150.0), [(0, "#F8EEF8"), (0.7, "#F2E4F5"), (1.4, "#E9D7F1")])
    src[..., :3] = glow
    src[..., 3] = op
    cv.over(src)
    # distant pale crates in the opening
    for (x0, y0, x1, y1, c) in ((338, 352, 400, 383, "#E3D6F1"), (352, 383, 400, 420, "#E6DAF2"), (373, 286, 400, 342, "#EDE1F6")):
        cv.fill(aa(sd_poly(X, Y, [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]), 1.5) * op, c, 0.85)
    # the light spilling out over the jamb, the wall and the lintel
    cv.screen(np.exp(-(((X - 330) / 150.0) ** 2 + ((Y - 350) / 170.0) ** 2)) * (1 - op), "#F7E8FF", 0.55)
    # the rod under the purple arrow, down to the lintel (x ~352..366, y 80..142: dark against the vault)
    tube(cv, [(349, 78), (356, 110), (361, 142)], 7.0, "#241A66", "#2F2476", "#46379E", hi="#5D4DB6")
    # the back room under the press (x < 110, y 355..520): a lilac wall lit by the light shaft, a far floor strip
    back = sd_poly(X, Y, [(-5, 350), (180, 350), (180, 530), (-5, 530)])
    col = stops_interp(Y, [(350, "#8F78CE"), (400, "#B79ED8"), (455, "#C9B1DE"), (520, "#CDB8E4")])
    src[..., :3] = col
    src[..., 3] = aa(back, 1.0) * aa(X - 150, 30)
    cv.over(src)
    # the light shaft falling from under the girder (x ~0..65), warm
    shaft = sd_poly(X, Y, [(2, 356), (50, 362), (64, 440), (-8, 440)])
    k = aa(shaft, 3.5) * np.clip(1 - (Y - 360) / 95.0, 0, 1) ** 0.9
    cv.screen(k, "#FFEAE0", 0.92)
    cv.screen(np.exp(-(((X - 28) / 26.0) ** 2 + ((Y - 372) / 14.0) ** 2)), "#FFF3EC", 0.55)
    # the far floor of the back room, under the boxes
    cv.fill(aa(sd_poly(X, Y, [(-5, 468), (120, 468), (120, 530), (-5, 530)]), 2.0), stops_interp(Y, [(468, "#C3A9DB"), (530, "#B9A0D6")]), 0.9)
    del src


def floor_uv(X, Y):
    Hi = np.linalg.inv(FLOOR_H)
    x = Hi[0, 0] * X + Hi[0, 1] * Y + Hi[0, 2]
    y = Hi[1, 0] * X + Hi[1, 1] * Y + Hi[1, 2]
    w = Hi[2, 0] * X + Hi[2, 1] * Y + Hi[2, 2]
    return x / w, y / w


FLOOR_TOP = 478.0


def paint_floor(cv):
    """The tiled floor (a transparent layer): tones by screen position, per-tile variation, bevelled grooves at the
    fitted seams, the opening's sheen; far tiles fade into the haze."""
    X, Y = cv.X, cv.Y
    L = layer(cv)
    u, v = floor_uv(X, Y)
    gu = np.hypot(*np.gradient(u)) * 3.0          # per pt
    gv = np.hypot(*np.gradient(v)) * 3.0
    base = stops_interp(Y, [(FLOOR_TOP, "#DDE0F6"), (540, "#CDD2EE"), (620, "#BFC5E6"), (720, "#AEB4DA"),
                            (800, "#A1A8D1"), (852, "#949BC9")])
    # cooler/darker toward the left edge and the bottom-left corner, lighter toward the opening (right)
    base = base * (1 - 0.07 * np.clip((90 - X) / 90.0, 0, 1))[..., None]
    base = base * (1 - 0.16 * np.exp(-(((X + 10) / 120.0) ** 2 + ((Y - 860) / 110.0) ** 2)))[..., None]
    tu, tv = np.floor(u), np.floor(v)
    jit = ((np.sin(tu * 12.9898 + tv * 78.233) * 43758.5453) % 1.0 - 0.5) * 0.05
    col = base * (1 + jit[..., None])
    # rounded tile edges: distance (pt) to the nearest seam with a corner fillet
    fu, fv = u - np.round(u), v - np.round(v)
    du, dv = np.abs(fu) / gu, np.abs(fv) / gv
    tile_pt = 1.0 / gv                              # the tile's depth on screen, pt (~120 at the joint)
    scale = np.clip(tile_pt / 120.0, 0.05, 1.6)
    r = 7.0 * scale
    both = (du < r) & (dv < r)
    d_edge = np.where(both, r - np.hypot(r - du, r - dv), np.minimum(du, dv))
    w = 3.4 * np.clip(scale, 0.35, 1.3)
    far = np.clip((tile_pt - 14.0) / 22.0, 0, 1)
    groove = (1 - smooth(d_edge, w * 0.5 - 0.5, w * 0.5 + 0.5)) * far
    core = (1 - smooth(d_edge, 0.0, w * 0.45)) * far
    on_v = dv <= du
    far_side = np.where(on_v, fv < 0, fu < 0)       # the far tile's front edge / the left tile's right edge is lit
    lip = np.exp(-((d_edge - (w * 0.5 + 0.9 * scale)) / (0.8 * np.maximum(scale, 0.4))) ** 2) * far
    col = col * (1 - 0.06 * (lip * ~far_side)[..., None])
    col = col + (rgb("#EEF0FD") - col) * (0.75 * lip * far_side)[..., None]
    gcol = stops_interp(Y, [(FLOOR_TOP, "#9097CF"), (650, "#6C72BA"), (852, "#5A61AC")])
    col = col * (1 - groove[..., None]) + gcol * groove[..., None]
    col = col * (1 - 0.25 * core[..., None])
    # gloss: the opening's light on the far-right floor, a broad soft streak down the middle
    col = 1 - (1 - col) * (1 - (0.35 * np.exp(-(((X - 345) / 120.0) ** 2 + ((Y - 540) / 90.0) ** 2)))[..., None])
    col = 1 - (1 - col) * (1 - (0.10 * np.exp(-(((X - 250) / 60.0) ** 2 + ((Y - 700) / 160.0) ** 2)))[..., None])
    col = 1 - (1 - col) * (1 - (0.30 * np.exp(-(((X - 372) / 60.0) ** 2 + ((Y - 665) / 75.0) ** 2)))[..., None])
    # a touch less blue (measured: our tiles sat ~3 b* bluer than the capture's on the uncovered floor)
    col = col * np.array([1.008, 1.0, 0.975])
    # haze toward the back
    hz = np.clip(1 - (Y - FLOOR_TOP) / 70.0, 0, 1) ** 1.6
    col = col + (rgb("#EDE6F8") - col) * (hz * 0.85)[..., None]
    L.a[..., :3] = col
    L.a[..., 3] = aa(FLOOR_TOP - Y, 2.0)
    # far tiles defocused, near tiles sharp (premultiplied blur: the transparent rows above do not darken the edge)
    a = L.a
    al = blur(a[..., 3], 5.0)
    soft = np.concatenate([blur(a[..., :3] * a[..., 3:4], 5.0) / np.maximum(al[..., None], 1e-6), al[..., None]], -1)
    k = np.clip((600 - Y) / 90.0, 0, 1)[..., None]
    cv.over(a * (1 - k) + soft * k)


def paint_conveyor(L):
    """The stepped platform at the left edge (x < 72, y 488..570), placed under the characters lane's left crowd (the
    two back-view workers' feet at y ~499, the clipboard worker's at ~528): the round deck, the lower deck with a
    rounded front corner at x ~46, its lip, the hazard-striped side (stripes '/' ~33 pt apart) and its floor shadow."""
    X, Y = L.X, L.Y
    src = np.zeros((L.h, L.w, 4))
    # floor shadow along the base
    d, s, t = polyline(X, Y, [(-10, 571), (40, 560), (68, 552), (80, 546)])
    L.fill(np.exp(-(np.maximum(d, 0) / 5.5) ** 2) * (s < 0.5) * aa(X - 80, 6), "#5B4C98", 0.45)
    # hazard side
    side = sd_poly(X, Y, [(-8, 537), (62, 531), (71, 537), (68, 551), (-8, 570)])
    cov = rounded(aa(side, 0.6), 3.0)
    # stripes '/' ~33 pt apart along x, yellow ~45 % (measured on rows y 545 / 552: yellow x 0..8 + 29..45 / 23..39)
    ph = ((X + 0.9 * Y) / 33.0 + 0.235) % 1.0
    stripe = smooth(ph, 0.43, 0.47) * (1 - smooth(ph, 0.97, 1.0))
    yl = stops_interp(Y, [(531, "#F7D484"), (550, "#EDC066"), (570, "#D6A451")])
    pl = stops_interp(Y, [(531, "#86527A"), (550, "#6E3E66"), (570, "#573152")])
    col = yl * (1 - stripe[..., None]) + pl * stripe[..., None]
    src[..., :3] = col
    src[..., 3] = cov
    L.over(src)
    L.multiply(aa(np.abs(side + 1.3) - 1.3, 0.6) * (Y > 545), "#3C2450", 0.45)
    # the lower deck: lip, then the top (lit), rounded front corner; the platform reaches back to the wall (y ~466)
    lip = sd_poly(X, Y, [(-8, 530), (44, 527), (51, 531), (48, 538), (-8, 541)])
    L.fill(rounded(aa(lip, 0.6), 2.5), stops_interp(X, [(-8, "#9E70A8"), (50, "#8E64A2")]))
    deck = sd_poly(X, Y, [(-8, 466), (78, 464), (78, 500), (62, 514), (50, 527), (-8, 531)])
    L.fill(rounded(aa(deck, 0.6), 5.0), stops_interp(Y, [(464, "#D3BDE2"), (500, "#C8A8D6"), (531, "#C4A2D2")]))
    side = sd_poly(X, Y, [(72, 466), (78, 464), (78, 500), (62, 514), (56, 512), (72, 497)])
    L.fill(rounded(aa(side, 0.6), 2.0), stops_interp(Y, [(466, "#B597CC"), (512, "#9C78B4")]), 0.8)
    L.fill(aa(np.abs(deck + 1.0) - 0.9, 0.6) * (Y > 514) * (X > 20), "#EADAF2", 0.85)     # lit front edge
    # the round deck the two back-view workers stand on (x 8..88, top y ~490..503): pale top, dark rim, its shadow
    L.multiply(np.exp(-(((X - 48) / 44.0) ** 2 + ((Y - 509.5) / 3.5) ** 2)), "#5A3C88", 0.40)
    L.fill(aa((np.hypot((X - 48) / 40.0, (Y - 501.0) / 7.0) - 1) * 7.0, 0.5), stops_interp(X, [(8, "#9467AC"), (88, "#835AA0")]))
    top = (np.hypot((X - 48) / 40.0, (Y - 496.5) / 7.0) - 1) * 7.0
    L.fill(aa(top, 0.5), stops_interp(Y, [(489, "#E6D5EE"), (503, "#D6BCE0")]))
    L.fill(aa(np.abs(top + 0.7) - 0.5, 0.4) * (Y < 494), "#F6EFFA", 0.8)
    del src


def _curve_poly(top, bot, x0, x1, n=24):
    xs = np.linspace(x0, x1, n)
    return [(x, top(x)) for x in xs] + [(x, bot(x)) for x in xs[::-1]]


def paint_press(L):
    """The long machine on the left wall (x < 240, y 150..420), as measured (see the lines above)."""
    X, Y = L.X, L.Y
    src = np.zeros((L.h, L.w, 4))

    def put(cov, col):
        src[..., :3] = np.clip(col, 0, 1)
        src[..., 3] = np.clip(cov, 0, 1)
        L.over(src)
    fade = 1 - smooth(X, 175, 240)
    # --- girder underside (dark, ridged), then the face
    under = sd_poly(X, Y, _curve_poly(B_MID, B_BOT, -8, 240))
    tu = band_t(X, Y, B_MID, B_BOT)
    uc = stops_interp(X, [(-8, "#4038B2"), (40, "#4B41BC"), (80, "#5C52C4"), (120, "#7A70D2"), (240, "#A69CE4")])
    ridge = np.exp(-((((tu * 4.0) % 1.0) - 0.5) / 0.08) ** 2) * (tu > 0.12) * (tu < 0.9)
    uc = uc * (1 - 0.16 * ridge[..., None])
    uc = uc + (rgb("#8C84DA") - uc) * (0.45 * smooth(tu, 0.86, 1.0))[..., None]      # the lower lip catches light
    put(aa(under, 0.5) * fade, uc)
    face = sd_poly(X, Y, _curve_poly(B_TOP, B_MID, -8, 240))
    tb = band_t(X, Y, B_TOP, B_MID)
    fc = stops_interp(X, [(-8, "#6E6CD5"), (30, "#8F88DD"), (60, "#B2A6EA"), (95, "#CBBEF2"), (150, "#D9CEF6"),
                          (240, "#E2D8F8")])
    low = smooth(tb, 0.70, 0.78)                                                      # the darker lower band
    fc = fc * (1 - low[..., None]) + (fc * np.array([0.70, 0.72, 0.90])) * low[..., None]
    fc = fc * (1 - 0.16 * np.exp(-((tb - 0.42) / 0.03) ** 2))[..., None]              # a groove
    fc = fc + (rgb("#E3DCFA") - fc) * (0.30 * np.exp(-((tb - 0.47) / 0.025) ** 2))[..., None]
    fc = fc + (rgb("#C3BBF2") - fc) * (0.50 * (1 - smooth(tb, 0.0, 0.09)))[..., None]  # lit top bevel
    put(aa(face, 0.5) * fade, fc)
    # --- buttons in violet rings on the girder face
    for (bx, by, rx, ry) in BUTTONS:
        dx, dy = X - bx, Y - by
        L.multiply(np.exp(-(((dx + 2.4) / (rx * 1.08)) ** 2 + ((dy - 2.8) / (ry * 1.08)) ** 2) ** 2), "#3E2F9A", 0.50)
        ring = np.hypot(dx / rx, dy / ry) - 1
        rc = stops_interp(dy / ry - dx / rx * 0.4, [(-1.2, "#A07CE4"), (-0.2, "#8157D0"), (1.2, "#5A3AAE")])
        put(aa(ring * min(rx, ry), 0.45), rc)
        ri = 4.3
        fr = np.hypot((dx - 0.6) / (rx - ri), (dy - 0.4) / (ry - ri)) - 1
        g = (dx - 0.6) / (rx - ri) * 0.6 + (dy - 0.4) / (ry - ri)
        bc = stops_interp(g, [(-1.3, "#FCF2F2"), (-0.2, "#F5DADD"), (0.6, "#EFC4CA"), (1.4, "#DEA3B6")])
        put(aa(fr * (rx - ri), 0.4), bc)
        L.fill(np.exp(-(((dx + 2.6) / 2.8) ** 2 + ((dy + 3.0) / 2.0) ** 2)), "#FFFFFF", 0.70)
        L.multiply(aa(np.abs(fr * (rx - ri)) - 0.5, 0.45) * (g > 0.1), "#7A4C9C", 0.35)
    # --- pink panel (+ its lit end face at x 104..112)
    pk = sd_poly(X, Y, [(-8, P_TOP(-8)), (106, P_TOP(106)), (106, B_TOP(106)), (-8, B_TOP(-8))])
    tp = band_t(X, Y, P_TOP, B_TOP)
    pc = stops_interp(X, [(-8, "#C44BA1"), (5, "#C84FA4"), (30, "#D35CAD"), (60, "#E187BF"), (90, "#F0B1D6"),
                          (106, "#F4BCDC")])
    pc = pc * (1 + 0.06 * tp[..., None])
    pc = pc + (rgb("#EE9BD0") - pc) * (0.40 * np.exp(-((tp - 0.07) / 0.05) ** 2))[..., None]
    put(aa(pk, 0.5), pc)
    end = sd_poly(X, Y, [(105, P_TOP(105)), (112, P_TOP(105) - 2.5), (112, B_TOP(112) + 5), (105, B_TOP(105))])
    put(rounded(aa(end, 0.5), 1.5), stops_interp(Y, [(285, "#F9D2E6"), (325, "#F3BCD8")]))
    L.multiply(aa(np.abs(X - 105) - 0.5, 0.5) * aa(end - 1, 1), "#B0609A", 0.25)
    # the girder's crisp top edge under the panel
    d, s, t = polyline(X, Y, [(-8, B_TOP(-8)), (106, B_TOP(106))])
    L.fill(aa(d - 0.8, 0.5) * (s < 0), "#7E62C8", 0.55)
    # --- the pale lip along the housing's bottom: a flat band with a bright upper edge, a rounded end at x ~106
    lp = sd_poly(X, Y, [(-8, R_TOP(-8)), (100, R_TOP(100)), (100, P_TOP(100)), (-8, P_TOP(-8))])
    tl = band_t(X, Y, R_TOP, P_TOP)
    lc = stops_interp(X, [(-8, "#6E7CB7"), (30, "#7A86BA"), (60, "#9CA2CB"), (90, "#B9BEDF"), (106, "#C6CBE8")])
    lc = lc + (rgb("#D5D9F2") - lc) * (0.55 * np.exp(-((tl - 0.12) / 0.09) ** 2))[..., None]
    lc = lc * (1 - 0.12 * smooth(tl, 0.75, 1.0))[..., None]
    put(rounded(aa(lp, 0.5), 6.0), lc)
    d, s, t = polyline(X, Y, [(-8, P_TOP(-8)), (103, P_TOP(103))])
    L.fill(aa(d - 1.1, 0.5) * (X < 103), "#4E3A86", 0.85)                              # the crease above the panel
    # --- blue housing: navy top edge, blue face with a lighter inner panel, slot marks, rounded end
    hs = sd_poly(X, Y, [(-8, T_TOP(-8)), (95, T_TOP(95)), (95, R_TOP(95)), (-8, R_TOP(-8))])
    th = band_t(X, Y, T_TOP, R_TOP)
    hc = stops_interp(X, [(-8, "#4E8AD4"), (30, "#3E83D6"), (60, "#4C88D4"), (95, "#6390D2")])
    hc = hc + (rgb("#78AAE8") - hc) * (0.30 * np.exp(-((th - 0.35) / 0.12) ** 2))[..., None]
    hc = hc * (1 - 0.14 * smooth(th, 0.80, 1.0))[..., None]
    put(rounded(aa(hs, 0.5), 7.0), hc)
    d, s, t = polyline(X, Y, [(-8, T_TOP(-8) + 1.6), (88, T_TOP(88) + 1.6), (93, T_TOP(93) + 5)])
    L.fill(aa(d - 1.7, 0.5), "#18255F", 0.95)
    for (sx, sy) in ((12.0, 174.0), (80.0, 233.0)):
        for k in (0.0, 3.2):
            p = [(sx + k, sy - 3.4 + k * 0.85), (sx + k + 1.2, sy + 3.4 + k * 0.85)]
            d, _, _ = polyline(X, Y, p)
            L.fill(aa(d - 0.75, 0.4), "#1D3A86", 0.9)
    # the right end of the lip catches the opening's light
    L.screen(np.exp(-(((X - 98) / 16.0) ** 2 + ((Y - 272) / 18.0) ** 2)) * aa(lp, 0.5), "#E8E8FB", 0.35)
    del src


def paint_props(L):
    """The blue pipe at the top left (a thick tube in from the left edge, bending down behind the logo) and the paper
    sheets lying on the floor at the right edge."""
    X, Y = L.X, L.Y
    tube(L, [(-14, 88), (12, 88), (24, 94), (31, 106), (33, 124)], 20.0, "#1D4CA6", "#2F73D0", "#5A9AE8", hi="#98C8F6")
    # paper sheets lying on the floor at the right edge (x 356..393, y 641..698)
    s1 = sd_poly(X, Y, [(359, 660), (397, 655), (397, 694), (356, 698)])
    L.fill(np.exp(-(np.maximum(s1, 0) / 3.0) ** 2) * (Y > 670), "#8D8FC6", 0.35)
    L.fill(aa(s1, 0.5), stops_interp(Y, [(655, "#E9E1EA"), (698, "#DCD3E4")]))
    L.fill(aa(np.abs(s1 + 0.6) - 0.6, 0.5) * (Y > 690), "#A79BB8", 0.6)
    s2 = sd_poly(X, Y, [(378, 648), (397, 641), (397, 675), (376, 678)])
    L.fill(aa(s2, 0.5), stops_interp(X, [(376, "#EFE8EE"), (397, "#E2D9E6")]))


# ====================================================================== the cast: contact shadows + reflections
# Feet per grounded character, in pt RELATIVE to its frame origin in art/out/char_loading_layout.json (so a moved
# character takes its shadow along): (x0, x1, sole y, strength, planted?). Read off the renders' lowest opaque pixels
# (round 3 renders); the build checks each against the render's alpha and warns when a pose change left one stale.
# A lifted foot (planted False) gets a fainter, wider pool on the floor below it. The flyer hangs in the air and the
# scientist's feet are hidden, so neither has one.
FEET = {
    "char_workerCarrier": [(65.9, 113.9, 384.5, 1.0, True), (42.0, 67.0, 384.5, 0.35, False)],
    "char_workerFist": [(73.9, 113.9, 229.6, 1.0, True), (123.9, 179.9, 233.0, 0.35, False)],
    "char_workerRunners": [(53.0, 66.0, 142.0, 0.60, True), (74.0, 95.0, 188.0, 0.75, True),
                           (96.0, 122.0, 176.0, 0.60, True), (124.0, 140.0, 141.0, 0.55, True)],
    "char_workerCrowdLeft": [(22.0, 49.0, 92.0, 0.60, True), (54.0, 88.0, 63.5, 0.50, True),
                             (92.0, 112.0, 62.5, 0.50, True)],
}
REFLECT = ("char_workerCarrier", "char_workerFist", "char_workerRunners")   # on the glossy floor (not the decks)


def cast_on_floor(cv, log=print):
    """Soft violet contact pools under the grounded cast + a faint mirrored reflection on the glossy floor."""
    from scene_kit import OUT as _OUT
    lay = json.load(open(os.path.join(_OUT, "char_loading_layout.json")))["characters"]
    X, Y = cv.X, cv.Y
    refl = np.zeros((cv.h, cv.w, 4))
    for name, feet in FEET.items():
        c = lay.get(name)
        if not c:
            log(f"  WARNING cast: {name} is not in char_loading_layout.json (no shadow)")
            continue
        arr = np.asarray(Image.open(os.path.join(_OUT, c["file"])).convert("RGBA")).astype(np.float64) / 255
        op = arr[..., 3] > 0.25
        for (x0, x1, yb, k, planted) in feet:
            r = op[max(0, int((yb - 4) * 3)):int((yb + 1.5) * 3), max(0, int((x0 - 2) * 3)):int((x1 + 2) * 3)]
            if planted and not r.any():
                log(f"  WARNING cast: {name} foot ({x0}..{x1}, {yb}) has no opaque pixels at its sole -- re-measure FEET")
            fx = c["x"] + (x0 + x1) / 2
            fy = c["y"] + yb
            w = max(9.0, x1 - x0)
            if planted:
                g = np.exp(-(((X - fx) / (w * 0.85)) ** 2 + ((Y - fy - 2.0) / (w * 0.22)) ** 2) * 1.2)
                g2 = np.exp(-(((X - fx) / (w * 0.50)) ** 2 + ((Y - fy - 0.6) / (w * 0.10)) ** 2) * 1.5)
                cv.multiply(np.clip(g, 0, 1), "#4F43A0", 0.42 * k)
                cv.multiply(np.clip(g2, 0, 1), "#352A80", 0.45 * k)
            else:
                g = np.exp(-(((X - fx) / (w * 0.9)) ** 2 + ((Y - fy - 3.0) / (w * 0.26)) ** 2) * 1.2)
                cv.multiply(np.clip(g, 0, 1), "#4F43A0", 0.42 * k)
        if name not in REFLECT:
            continue
        # the render mirrored about its planted soles, strongly blurred, fading with the distance below them
        yb = max(f[2] for f in feet if f[4]) * 3
        fl = arr[::-1]
        ox = round(c["x"] * 3)
        oy = round(c["y"] * 3 + 2 * yb - (arr.shape[0] - 1))
        h, w_ = fl.shape[:2]
        y0, x0 = max(0, oy), max(0, ox)
        y1, x1 = min(cv.h, oy + h), min(cv.w, ox + w_)
        if y1 <= y0 or x1 <= x0:
            continue
        piece = fl[y0 - oy:y1 - oy, x0 - ox:x1 - ox].copy()
        dist = (np.arange(y0, y1)[:, None] - (c["y"] * 3 + yb)) / 3.0
        piece[..., 3] *= np.clip(1 - dist / 80.0, 0, 1) ** 1.6 * 0.22
        sub = refl[y0:y1, x0:x1]
        sa = piece[..., 3:4]
        sub[..., :3] = piece[..., :3] * sa + sub[..., :3] * (1 - sa)
        sub[..., 3:4] = sa + sub[..., 3:4] * (1 - sa)
    if refl[..., 3].max() > 0:
        pre = blur(refl[..., :3] * refl[..., 3:4], 12.0)
        al = blur(refl[..., 3], 12.0)
        out = np.zeros_like(refl)
        out[..., :3] = pre / np.maximum(al[..., None], 1e-6)
        out[..., 3] = al * aa(FLOOR_TOP + 40 - Y, 10.0)
        cv.over(out)


# ====================================================================== build
FLY = [   # (model, centre pt, R, scale, haze, blur pt), placed on the registered store 8 / state.png:
    # red: only the TAIL of a big arrow flying up-left out of the frame (a ~76 pt wide block, x 37..154, y 0..53)
    ("block_arrow_red", (70, -50, 6.0), (rot_z(115) @ rot_x(-4) @ rot_y(4)).tolist(), 4.6, 0.0, 0.5),
    # purple: pointing up, head x 308..372 at y 0..40, shaft x 325..360 down to y ~84
    ("block_arrow_purple", (338, 42, 4.0), (rot_z(90) @ rot_x(-24) @ rot_y(-8)).tolist(), 2.1, 0.0, 0.6),
    # green / blue: pale and defocused under the logo, pointing up-left
    ("block_arrow_green", (147, 243, 2.0), (rot_z(102) @ rot_x(16) @ rot_y(22)).tolist(), 2.2, 0.18, 1.0),
    ("block_arrow_blue", (143, 277, 2.5), (rot_z(126) @ rot_x(15) @ rot_y(24)).tolist(), 1.05, 0.36, 1.2),
]
B_WORLD = ((0.0, -85.2, -8.0), (39.3, 0.0, 8.0))


def build_loading(ctx):
    cv = Canvas(393, 852)
    c = dict(center=False)
    arrows = {f"ld_{m}": dict(scene=[(_M, m, dict(center=True, pos=W(*p), R=R, scale=s))], bounds=B_WORLD,
                              aspect=393 / 852, margin=1.0, fov=4.0, px=2400, light=rig(key_lux=2300.0))
              for (m, p, R, s, hz, bl) in FLY}
    specs = {
        "ldBoxes": dict(scene=[(_M, "boxes", c)], bounds=B_WORLD, aspect=393 / 852, margin=1.0, fov=4.0, px=2400,
                        light=rig(key_lux=2200.0)),
        "ldCable": dict(scene=[(_M, "cable", c)], bounds=B_WORLD, aspect=393 / 852, margin=1.0, fov=4.0, px=2400,
                        light=rig(key_lux=2200.0, key_dir=(0.3, -0.8, -0.5))),
    }
    specs.update(arrows)
    ims = {k: v.resize((cv.w, cv.h), Image.LANCZOS) for k, v in ctx.render(specs).items()}
    # 1. the room (defocused, far)
    paint_room(cv)
    bx = ims["ldBoxes"]
    ba = np.asarray(bx).astype(np.float64) / 255
    ba[..., :3] = ba[..., :3] + (rgb("#D0B3CC") - ba[..., :3]) * 0.34          # lilac room haze on the cardboard
    ba[..., :3] = ba[..., :3] * (1 + 0.10 * np.exp(-(((cv.X - 30) / 30.0) ** 2 + ((cv.Y - 430) / 20.0) ** 2)))[..., None]
    cv.over(np.clip(ba, 0, 1))
    # the light shaft goes on down over the cardboard stack (a lighter wedge on its left half)
    shaft = sd_poly(cv.X, cv.Y, [(2, 420), (58, 424), (66, 482), (-8, 482)])
    cv.screen(aa(shaft, 5.0) * np.clip(1 - (cv.Y - 420) / 70.0, 0, 1), "#FFEDE6", 0.35)
    img = Image.fromarray(np.clip(cv.a * 255, 0, 255).astype(np.uint8), "RGBA")
    from PIL import ImageFilter
    cv.a = np.asarray(img.filter(ImageFilter.GaussianBlur(2.5))).astype(np.float64) / 255
    # 2. the floor
    paint_floor(cv)
    # 3. conveyor + press (mid distance, a little soft)
    L = layer(cv)
    paint_conveyor(L)
    blur_over(cv, L, 0.55)
    del L
    L = layer(cv)
    paint_press(L)
    blur_over(cv, L, 0.45)
    del L
    L = layer(cv)
    paint_props(L)
    blur_over(cv, L, 0.7)
    del L
    # 4. the cast's contact shadows + reflections (under the cable and the arrows)
    cast_on_floor(cv)
    # 5. the cable (near, sharp) and its shadow
    from scene_kit import shadow_of
    im = ims["ldCable"]
    sh, (ox, oy) = shadow_of(im, 3, 7, 6, 0.30, color="#3F3690")
    cv.over(sh, x=ox, y=oy)
    cv.over(im)
    # 6. the flying arrows (the pale green / blue ones are defocused and hazed)
    for (m, p, R, s, hz, bl) in FLY:
        im = ims[f"ld_{m}"]
        a = np.asarray(im).astype(np.float64) / 255
        if hz:
            a[..., :3] = a[..., :3] + (rgb("#E9E4F6") - a[..., :3]) * hz
        if m == "block_arrow_red":
            a[..., :3] = a[..., :3] * np.array([0.93, 0.84, 0.94])
        La = layer(cv)
        La.a = a
        blur_over(cv, La, bl)
        del La
    # vignette (the reference's corners are a touch darker)
    cv.multiply(np.clip(((cv.X - 196.5) / 196.5) ** 2 * 0.35 + ((cv.Y - 426) / 426) ** 2 * 0.25, 0, 1), "#3F3486", 0.22)
    return cv.image()


BUILDS = {"loadingBackdrop": build_loading}
