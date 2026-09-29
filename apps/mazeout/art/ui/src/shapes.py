"""Parametric 2D shapes shared by the SVG generators (art/ui/src/gen_*.py).

Every outline here is built from primitives with MEASURED parameters (sizes, exponents, radii read off the
captures; see art/STYLE.md). Nothing is traced from a capture. Units: @3x px (1 unit = 1/3 pt), y down.
"""
from __future__ import annotations

import math

import numpy as np


def fmt(v):
    return f"{v:.2f}".rstrip("0").rstrip(".")


def poly_path(pts, close=True):
    s = "M" + " L".join(f"{fmt(x)} {fmt(y)}" for x, y in pts)
    return s + (" Z" if close else "")


def superellipse(cx, cy, a, b, n=4.0, N=240):
    """|x/a|^n + |y/b|^n = 1: the pillow squircle of the glossy buttons (n 3.5 pause, 4 wide buttons)."""
    t = np.linspace(0, 2 * math.pi, N, endpoint=False)
    c, s = np.cos(t), np.sin(t)
    x = cx + a * np.sign(c) * np.abs(c) ** (2 / n)
    y = cy + b * np.sign(s) * np.abs(s) ** (2 / n)
    return list(zip(x, y))


def superellipse_path(x, y, w, h, n=4.0, N=240):
    return poly_path(superellipse(x + w / 2, y + h / 2, w / 2, h / 2, n, N))


def _contour(field, x0, y0, step):
    from skimage import measure
    cs = measure.find_contours(field, 0.0)
    c = max(cs, key=len)
    return [(x0 + p[1] * step, y0 + p[0] * step) for p in c[::2]]


def heart_sdf(w, h, lobe_r=None, tip_r=None, notch=None, lobe_dx=None):
    """A puffy cartoon heart in a w x h box (origin top-left, y down): two lobe circles + a tip circle, joined by
    the tangent hull of each lobe with the tip (a 2D round cone). Parameters measured on shot 003's HUD heart
    (88 x 76 px incl. its outline; a 4-parameter grid fit, silhouette IoU 0.963): lobe r 0.31 w, lobe centres
    0.5 w +- 0.21 w at y 0.37 h, tip r 0.20 w, tip centre y h - tip_r."""
    lr = lobe_r or 0.31 * w
    tr = tip_r or 0.20 * w
    cx = w / 2
    dx = lobe_dx or 0.21 * w
    cy = 0.37 * h if notch is None else notch
    tip = (cx, h - tr)

    def round_cone(p, a, b, ra, rb):
        # Inigo Quilez's sdUnevenCapsule: circle ra at a, circle rb at b, joined by their tangent lines
        pa = p - np.array(a)
        ba = np.array(b) - np.array(a)
        L = np.linalg.norm(ba)
        u = ba / L
        v = np.array([-u[1], u[0]])
        y_ = pa @ u
        x_ = np.abs(pa @ v)
        bb = (ra - rb) / L
        aa = math.sqrt(max(1 - bb * bb, 1e-9))
        k = -bb * x_ + aa * y_
        d_a = np.sqrt(x_ ** 2 + y_ ** 2) - ra
        d_b = np.sqrt(x_ ** 2 + (y_ - L) ** 2) - rb
        d_side = aa * x_ + bb * y_ - ra
        return np.where(k < 0, d_a, np.where(k > aa * L, d_b, d_side))

    def f(p):
        l = round_cone(p, (cx - dx, cy), tip, lr, tr)
        r = round_cone(p, (cx + dx, cy), tip, lr, tr)
        return np.minimum(l, r)
    return f


def heart_outline(x, y, w, h, **kw):
    f = heart_sdf(w, h, **kw)
    step = 0.25
    xs = np.arange(-4, w + 4, step)
    ys = np.arange(-4, h + 4, step)
    X, Y = np.meshgrid(xs, ys)
    P = np.stack([X.ravel(), Y.ravel()], 1)
    F = f(P).reshape(X.shape)
    pts = _contour(F, -4, -4, step)
    return [(x + a, y + b) for a, b in pts]


def heart_path(x, y, w, h, **kw):
    return poly_path(heart_outline(x, y, w, h, **kw))


def svg_doc(w_pt, h_pt, body, defs=""):
    W, H = w_pt * 3, h_pt * 3
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{fmt(w_pt)}" height="{fmt(h_pt)}" viewBox="0 0 {fmt(W)} {fmt(H)}">\n'
            f'<defs>{defs}</defs>\n{body}\n</svg>\n')


# The heart used by the HUD (lives) and everywhere a glossy heart appears: the union of two ellipses leaning
# +-48 deg toward the tip. Fitted on shot 003's HUD heart (88 x 76 px incl. outline) by a 5-parameter grid search,
# silhouette IoU 0.981 (the round-cone model above reached 0.963 with a blunt tip, rejected on the sheet).
HEART2 = dict(rx=0.46, ry=0.38, dx=0.105, cy=0.485, deg=48.0,   # rx x w, ry x h, centres (0.5 +- dx) w, cy h
              tip_y0=0.89, tip_hw=0.21)                         # + a tip wedge: base at 0.89 h, half-width 0.21 w,
#                                                                 apex at h (the ellipses alone end 3 px short, blunt)


def heart2_ellipses(x, y, w, h, P=HEART2):
    """[(cx, cy, rx, ry, rotation_deg)] in px: left lobe leans +deg (its long axis runs down-right to the tip)."""
    return [(x + (0.5 - P["dx"]) * w, y + P["cy"] * h, P["rx"] * w, P["ry"] * h, P["deg"]),
            (x + (0.5 + P["dx"]) * w, y + P["cy"] * h, P["rx"] * w, P["ry"] * h, -P["deg"])]


def heart2_field(w, h, P=HEART2):
    es = heart2_ellipses(0, 0, w, h, P)

    tri = np.array([(0.5 * w - P["tip_hw"] * w, P["tip_y0"] * h), (0.5 * w + P["tip_hw"] * w, P["tip_y0"] * h), (0.5 * w, h)])

    def f(p):
        # the tip wedge (exact polygon SDF)
        dmin = None
        inside = np.ones(len(p), bool)
        for i in range(3):
            a_, b_ = tri[i], tri[(i + 1) % 3]
            e = b_ - a_
            q = p - a_
            t = np.clip((q @ e) / (e @ e), 0, 1)
            dd = np.sqrt(((q - np.outer(t, e)) ** 2).sum(1))
            dmin = dd if dmin is None else np.minimum(dmin, dd)
            inside &= (e[0] * q[:, 1] - e[1] * q[:, 0]) > 0
        d = np.where(inside, -dmin, dmin)
        for cx, cy, rx, ry, deg in es:
            t = math.radians(deg)
            X, Y = p[:, 0] - cx, p[:, 1] - cy
            xr = math.cos(t) * X + math.sin(t) * Y
            yr = -math.sin(t) * X + math.cos(t) * Y
            k = np.sqrt((xr / rx) ** 2 + (yr / ry) ** 2)
            di = (k - 1) * min(rx, ry)
            d = np.minimum(d, di)
        return d
    return f


def heart2_path(x, y, w, h, P=HEART2):
    f = heart2_field(w, h, P)
    step = 0.25
    xs = np.arange(-4, w + 4, step)
    ys = np.arange(-4, h + 4, step)
    X, Y = np.meshgrid(xs, ys)
    F = f(np.stack([X.ravel(), Y.ravel()], 1)).reshape(X.shape)
    pts = _contour(F, -4, -4, step)
    return poly_path([(x + a, y + b) for a, b in pts])
