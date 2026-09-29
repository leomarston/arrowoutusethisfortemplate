"""Signed-distance modelling for Match Factory items.

Every shape is an `SDF`: a vectorised function (N,3) float32 -> (N,) float32
(negative inside) plus a conservative axis-aligned bounding box. Operations
return new SDFs, so a recipe reads like a CSG tree:

    head = cylinder(0.19, 0.17, round=0.03).rotate_z(90)
    star = extrude(star2(5, 0.11, 0.05, round=0.01), 0.5).intersect(head.offset(0.006))
    body = ellipsoid(0.4, 0.3, 0.3).smooth_union(sphere(0.25).translate(0.3, 0.3, 0), k=0.08)

Conventions: Y is up, +Z is the item's front (the side the goal icon shows),
1 unit = 1 board cell. Angles are degrees.

Notes on exactness: primitives are exact or tight bounds; smooth blends and
non-rigid deforms (bend/twist/taper) make the field approximate, which is
fine for marching cubes but keep deformation amounts modest.
"""
from __future__ import annotations

import math
import numpy as np

F = np.float32
BIG = F(1e3)


def _v(*a):
    if len(a) == 1:
        a = a[0]
    return np.asarray(a, dtype=F).reshape(3)


def _len(a, axis=-1):
    return np.sqrt(np.sum(a * a, axis=axis))


def _rot(axis, deg):
    axis = np.asarray(axis, float)
    axis = axis / np.linalg.norm(axis)
    t = math.radians(deg)
    c, s = math.cos(t), math.sin(t)
    x, y, z = axis
    C = 1 - c
    return np.array([
        [c + x * x * C, x * y * C - z * s, x * z * C + y * s],
        [y * x * C + z * s, c + y * y * C, y * z * C - x * s],
        [z * x * C - y * s, z * y * C + x * s, c + z * z * C],
    ])


def _corners(lo, hi):
    return np.array([[x, y, z] for x in (lo[0], hi[0]) for y in (lo[1], hi[1]) for z in (lo[2], hi[2])], float)


def rot_align(a, b):
    """Rotation matrix taking unit vector a to unit vector b."""
    a = np.asarray(a, float); a = a / np.linalg.norm(a)
    b = np.asarray(b, float); b = b / np.linalg.norm(b)
    v = np.cross(a, b)
    c = float(np.dot(a, b))
    if np.linalg.norm(v) < 1e-9:
        if c > 0:
            return np.eye(3)
        # 180 degrees: any perpendicular axis
        p = np.array([1, 0, 0]) if abs(a[0]) < 0.9 else np.array([0, 1, 0])
        ax = np.cross(a, p); ax /= np.linalg.norm(ax)
        return _rot(ax, 180)
    vx = np.array([[0, -v[2], v[1]], [v[2], 0, -v[0]], [-v[1], v[0], 0]])
    return np.eye(3) + vx + vx @ vx * (1 / (1 + c))


# --------------------------------------------------------------------------- core

class SDF:
    def __init__(self, fn, lo, hi):
        self.fn = fn
        self.lo = np.asarray(lo, float).reshape(3)
        self.hi = np.asarray(hi, float).reshape(3)

    def __call__(self, p):
        return self.fn(np.asarray(p, dtype=F)).astype(F, copy=False)

    # ---- bounds helpers
    @property
    def size(self):
        return self.hi - self.lo

    @property
    def center(self):
        return (self.lo + self.hi) / 2

    def _bounded(self, lo, hi):
        return SDF(self.fn, lo, hi)

    # ---- rigid transforms
    def translate(self, x, y=None, z=None):
        t = _v(x, y, z) if y is not None else _v(x)
        f = self.fn
        return SDF(lambda p: f(p - t), self.lo + t, self.hi + t)

    def rotate(self, axis, deg):
        return self.transform(_rot(axis, deg))

    def rotate_x(self, deg):
        return self.rotate((1, 0, 0), deg)

    def rotate_y(self, deg):
        return self.rotate((0, 1, 0), deg)

    def rotate_z(self, deg):
        return self.rotate((0, 0, 1), deg)

    def orient(self, frm, to):
        """Rotate so direction `frm` points along `to`."""
        return self.transform(rot_align(frm, to))

    def transform(self, R):
        R = np.asarray(R, float)
        Rf = R.astype(F)
        f = self.fn
        c = _corners(self.lo, self.hi) @ R.T
        # p_local = R^T p  ->  row form p @ R
        return SDF(lambda p: f(p @ Rf), c.min(0), c.max(0))

    def scale(self, s):
        s = float(s)
        f = self.fn
        return SDF(lambda p: f(p / F(s)) * F(s), self.lo * s, self.hi * s)

    def scale_xyz(self, sx, sy, sz):
        """Non-uniform scale. Field is only a bound; keep ratios moderate (<2:1)."""
        s = np.array([sx, sy, sz], dtype=F)
        m = F(min(sx, sy, sz))
        f = self.fn
        lo, hi = self.lo * s, self.hi * s
        return SDF(lambda p: f(p / s) * m, np.minimum(lo, hi), np.maximum(lo, hi))

    def mirror_x(self):
        """Union of the shape and its mirror across the YZ plane."""
        return self.union(self.transform(np.diag([-1.0, 1, 1])))

    # ---- offsets
    def offset(self, r):
        """Grow (r>0) or shrink (r<0) the surface."""
        f = self.fn
        r = F(r)
        return SDF(lambda p: f(p) - r, self.lo - max(r, 0), self.hi + max(r, 0))

    round = offset

    def shell(self, t):
        f = self.fn
        t = F(t)
        return SDF(lambda p: np.abs(f(p)) - t, self.lo - t, self.hi + t)

    # ---- booleans
    def union(self, *others, k=0.0):
        return union(self, *others, k=k)

    def smooth_union(self, *others, k=0.05):
        return union(self, *others, k=k)

    def subtract(self, other, k=0.0):
        a, b = self.fn, other.fn
        if k <= 0:
            return SDF(lambda p: np.maximum(a(p), -b(p)), self.lo, self.hi)
        kk = F(k)

        def fn(p):
            d1, d2 = a(p), b(p)
            h = np.clip(0.5 - 0.5 * (d1 + d2) / kk, 0, 1)
            return d1 * (1 - h) + (-d2) * h + kk * h * (1 - h)
        return SDF(fn, self.lo, self.hi)

    def intersect(self, other, k=0.0):
        a, b = self.fn, other.fn
        lo = np.maximum(self.lo, other.lo)
        hi = np.minimum(self.hi, other.hi)
        if k <= 0:
            return SDF(lambda p: np.maximum(a(p), b(p)), lo, hi)
        kk = F(k)

        def fn(p):
            d1, d2 = a(p), b(p)
            h = np.clip(0.5 - 0.5 * (d2 - d1) / kk, 0, 1)
            return d2 * (1 - h) + d1 * h + kk * h * (1 - h)
        return SDF(fn, lo, hi)

    def clip_plane(self, normal, d=0.0):
        """Keep the half-space where dot(p, n) <= d."""
        return self.intersect(plane(normal, d).bounded(self.lo - 0.01, self.hi + 0.01))

    def bounded(self, lo, hi):
        return SDF(self.fn, lo, hi)

    # ---- deformations (approximate fields)
    def bend(self, k, axis="x"):
        """Bend around Z: points along +X curve toward +Y with curvature k (1/radius)."""
        f = self.fn
        kf = F(k)
        pad = 0.25 * abs(k) * float(np.max(np.abs(np.r_[self.lo, self.hi]))) ** 2

        def fn(p):
            x, y, z = p[:, 0], p[:, 1], p[:, 2]
            if abs(k) < 1e-6:
                return f(p)
            r = 1.0 / kf
            # map from bent space back to straight
            ang = np.arctan2(x, r - y)
            rad = np.sqrt(x * x + (r - y) ** 2)
            q = np.stack([ang * r, r - rad, z], 1).astype(F)
            return f(q)
        return SDF(fn, self.lo - pad, self.hi + pad)

    def twist(self, deg_per_unit):
        f = self.fn
        k = F(math.radians(deg_per_unit))
        ext = float(np.max(np.abs(np.r_[self.lo[[0, 2]], self.hi[[0, 2]]])))

        def fn(p):
            a = p[:, 1] * k
            c, s = np.cos(a), np.sin(a)
            x = c * p[:, 0] + s * p[:, 2]
            z = -s * p[:, 0] + c * p[:, 2]
            return f(np.stack([x, p[:, 1], z], 1)) * F(0.8)
        lo = self.lo.copy(); hi = self.hi.copy()
        lo[[0, 2]] = -ext * 1.42; hi[[0, 2]] = ext * 1.42
        return SDF(fn, lo, hi)

    def taper(self, y0, y1, s0, s1):
        """Scale XZ linearly from s0 at y=y0 to s1 at y=y1 (clamped)."""
        f = self.fn
        smax = max(s0, s1)

        def fn(p):
            t = np.clip((p[:, 1] - y0) / (y1 - y0), 0, 1)
            s = (s0 + (s1 - s0) * t).astype(F)
            q = p.copy()
            q[:, 0] /= s
            q[:, 2] /= s
            return f(q) * np.minimum(s, 1).astype(F) * F(0.9)
        lo = self.lo.copy(); hi = self.hi.copy()
        lo[[0, 2]] *= smax; hi[[0, 2]] *= smax
        return SDF(fn, lo, hi)

    def displace(self, fn2, amp):
        """Add amp * fn2(p) (fn2 returns values in [-1, 1])."""
        f = self.fn
        a = F(amp)
        return SDF(lambda p: f(p) + a * fn2(p).astype(F), self.lo - abs(amp), self.hi + abs(amp))


def union(*shapes, k=0.0, pad=0.06):
    """Union with bounding-box culling: each child is only evaluated near its box.

    Outside every (padded) child box the field is clamped to `pad`, which keeps
    marching cubes exact near the surface and makes unions of many small parts
    (seeds, dots) cheap.
    """
    shapes = [s for s in shapes if s is not None]
    if len(shapes) == 1:
        return shapes[0]
    lo = np.min([s.lo for s in shapes], 0)
    hi = np.max([s.hi for s in shapes], 0)
    kk = F(k)
    pad = max(pad, 2 * k + 0.02)
    padf = F(pad)
    boxes = [(s.lo - pad, s.hi + pad, s.fn) for s in shapes]

    def fn(p):
        d = np.full(len(p), padf, dtype=F)
        for blo, bhi, f in boxes:
            m = np.all((p >= blo.astype(F)) & (p <= bhi.astype(F)), axis=1)
            if not m.any():
                continue
            idx = np.nonzero(m)[0]
            di = f(p[idx]).astype(F)
            if kk > 0:
                a = d[idx]
                h = np.clip(0.5 + 0.5 * (di - a) / kk, 0, 1)
                d[idx] = di * (1 - h) + a * h - kk * h * (1 - h)
            else:
                d[idx] = np.minimum(d[idx], di)
        return d
    return SDF(fn, lo - k, hi + k)


# --------------------------------------------------------------------------- primitives

def sphere(r, center=(0, 0, 0)):
    c = _v(center)
    r = F(r)
    return SDF(lambda p: _len(p - c) - r, c - r, c + r)


def ellipsoid(rx, ry, rz, center=(0, 0, 0)):
    """iq's ellipsoid bound: exact on the surface, good near it."""
    r = _v(rx, ry, rz)
    c = _v(center)

    def fn(p):
        q = p - c
        k0 = _len(q / r)
        k1 = _len(q / (r * r))
        return k0 * (k0 - 1) / np.maximum(k1, F(1e-6))
    return SDF(fn, c - r, c + r)


def box(sx, sy, sz, round=0.0, center=(0, 0, 0)):
    """Box with half-extents (sx, sy, sz), edges rounded by `round`."""
    b = _v(sx, sy, sz)
    c = _v(center)
    rr = F(round)

    def fn(p):
        q = np.abs(p - c) - b + rr
        return _len(np.maximum(q, 0)) + np.minimum(np.max(q, 1), 0) - rr
    return SDF(fn, c - b, c + b)


def capsule(a, b, r):
    a = _v(a); b = _v(b)
    r = F(r)
    ba = b - a
    bb = F(np.dot(ba, ba))

    def fn(p):
        pa = p - a
        h = np.clip(pa @ ba / bb, 0, 1)
        return _len(pa - h[:, None] * ba) - r
    return SDF(fn, np.minimum(a, b) - r, np.maximum(a, b) + r)


def round_cone(a, b, ra, rb):
    """Capsule whose radius goes from ra at a to rb at b (iq sdRoundCone, arbitrary endpoints)."""
    a = _v(a); b = _v(b)
    ra = F(ra); rb = F(rb)
    ba = b - a
    l2 = F(np.dot(ba, ba))
    rr = ra - rb
    a2 = l2 - rr * rr
    il2 = F(1.0 / l2)

    def fn(p):
        pa = p - a
        y = pa @ ba
        z = y - l2
        xv = pa * l2 - y[:, None] * ba
        x2 = np.sum(xv * xv, 1)
        y2 = y * y * l2
        z2 = z * z * l2
        k = np.sign(rr) * rr * rr * x2
        out = np.empty(len(p), F)
        c1 = np.sign(z) * a2 * z2 > k
        c2 = np.sign(y) * a2 * y2 < k
        c3 = ~(c1 | c2)
        out[c1] = np.sqrt(x2[c1] + z2[c1]) * il2 - rb
        out[c2] = np.sqrt(x2[c2] + y2[c2]) * il2 - ra
        out[c3] = (np.sqrt(x2[c3] * a2 * il2) + y[c3] * rr) * il2 - ra
        return out
    m = max(float(ra), float(rb))
    return SDF(fn, np.minimum(a, b) - m, np.maximum(a, b) + m)


def cylinder(r, h, round=0.0, center=(0, 0, 0)):
    """Y-axis cylinder, radius r, half-height h, edges rounded by `round`."""
    c = _v(center)
    r = F(r); h = F(h); rr = F(round)

    def fn(p):
        q = p - c
        dx = _len(q[:, [0, 2]]) - r + rr
        dy = np.abs(q[:, 1]) - h + rr
        d = np.stack([dx, dy], 1)
        return np.minimum(np.maximum(dx, dy), 0) + _len(np.maximum(d, 0)) - rr
    return SDF(fn, c - _v(r, h, r), c + _v(r, h, r))


def chamfer_cylinder(r, h, ch, center=(0, 0, 0)):
    """Y-axis cylinder with 45-degree chamfered rims (the toy-hammer cap look)."""
    c = _v(center)
    r = F(r); h = F(h); ch = F(ch)

    def fn(p):
        q = p - c
        rad = _len(q[:, [0, 2]])
        y = np.abs(q[:, 1])
        d1 = rad - r
        d2 = y - h
        d3 = (rad + y - (r + h - ch)) * F(0.70710678)
        return np.maximum(np.maximum(d1, d2), d3)
    return SDF(fn, c - _v(r, h, r), c + _v(r, h, r))


def capped_cone(h, r_bottom, r_top, round=0.0, center=(0, 0, 0)):
    """Y-axis truncated cone from y=-h (r_bottom) to y=+h (r_top), optionally rounded."""
    c = _v(center)
    rr = F(round)
    h0 = F(h) - rr
    r1 = F(r_bottom) - rr
    r2 = F(r_top) - rr
    k1 = np.array([r2, h0], F)
    k2 = np.array([r2 - r1, 2 * h0], F)
    k2d = F(np.dot(k2, k2))

    def fn(p):
        qp = p - c
        q = np.stack([_len(qp[:, [0, 2]]), qp[:, 1]], 1)
        ca = np.stack([q[:, 0] - np.minimum(q[:, 0], np.where(q[:, 1] < 0, r1, r2)), np.abs(q[:, 1]) - h0], 1)
        t = np.clip(((k1 - q) @ k2) / k2d, 0, 1)
        cb = q - k1 + t[:, None] * k2
        s = np.where((cb[:, 0] < 0) & (ca[:, 1] < 0), F(-1), F(1))
        return s * np.sqrt(np.minimum(np.sum(ca * ca, 1), np.sum(cb * cb, 1))) - rr
    m = float(max(r_bottom, r_top))
    return SDF(fn, c - _v(m, h, m), c + _v(m, h, m))


def torus(R, r, center=(0, 0, 0)):
    """Torus in the XZ plane."""
    c = _v(center)
    R = F(R); r = F(r)

    def fn(p):
        q = p - c
        x = _len(q[:, [0, 2]]) - R
        return np.sqrt(x * x + q[:, 1] * q[:, 1]) - r
    return SDF(fn, c - _v(R + r, r, R + r), c + _v(R + r, r, R + r))


def plane(normal, d=0.0):
    n = np.asarray(normal, float)
    n = (n / np.linalg.norm(n)).astype(F)
    d = F(d)
    return SDF(lambda p: p @ n - d, [-BIG] * 3, [BIG] * 3)


# --------------------------------------------------------------------------- 2D shapes + extrusion / revolution

class SDF2:
    """2D signed distance (N,2)->(N,) with bounds (lo2, hi2)."""

    def __init__(self, fn, lo, hi):
        self.fn = fn
        self.lo = np.asarray(lo, float)
        self.hi = np.asarray(hi, float)

    def __call__(self, p):
        return self.fn(p)

    def offset(self, r):
        f = self.fn
        return SDF2(lambda p: f(p) - F(r), self.lo - max(r, 0), self.hi + max(r, 0))

    round = offset

    def translate(self, x, y):
        t = np.array([x, y], F)
        f = self.fn
        return SDF2(lambda p: f(p - t), self.lo + t, self.hi + t)

    def rotate(self, deg):
        a = math.radians(deg)
        R = np.array([[math.cos(a), -math.sin(a)], [math.sin(a), math.cos(a)]])
        Rf = R.astype(F)
        f = self.fn
        c = np.array([[self.lo[0], self.lo[1]], [self.lo[0], self.hi[1]], [self.hi[0], self.lo[1]], [self.hi[0], self.hi[1]]]) @ R.T
        return SDF2(lambda p: f(p @ Rf), c.min(0), c.max(0))

    def union(self, other):
        a, b = self.fn, other.fn
        return SDF2(lambda p: np.minimum(a(p), b(p)), np.minimum(self.lo, other.lo), np.maximum(self.hi, other.hi))

    def subtract(self, other):
        a, b = self.fn, other.fn
        return SDF2(lambda p: np.maximum(a(p), -b(p)), self.lo, self.hi)


def circle2(r):
    return SDF2(lambda p: _len(p) - F(r), [-r, -r], [r, r])


def rect2(hx, hy, round=0.0):
    b = np.array([hx, hy], F)
    rr = F(round)

    def fn(p):
        q = np.abs(p) - b + rr
        return _len(np.maximum(q, 0)) + np.minimum(np.max(q, 1), 0) - rr
    return SDF2(fn, -b, b)


def polygon2(pts):
    """Exact SDF of a simple polygon given as (M,2) points (any winding)."""
    v = np.asarray(pts, F)
    M = len(v)
    e = np.roll(v, -1, 0) - v
    ee = np.sum(e * e, 1)

    def fn(p):
        d = np.full(len(p), BIG, F)
        s = np.ones(len(p), F)
        for i in range(M):
            w = p - v[i]
            b = w - e[i] * np.clip((w @ e[i]) / ee[i], 0, 1)[:, None]
            d = np.minimum(d, np.sum(b * b, 1))
            vi, vj = v[i], v[(i + 1) % M]
            c1 = p[:, 1] >= vi[1]
            c2 = p[:, 1] < vj[1]
            c3 = e[i][0] * w[:, 1] > e[i][1] * w[:, 0]
            flip = (c1 & c2 & c3) | (~c1 & ~c2 & ~c3)
            s[flip] *= -1
        return s * np.sqrt(d)
    return SDF2(fn, v.min(0), v.max(0))


def fillet_points(pts, radii, n_arc=6):
    """Replace every corner of a closed polyline by a circular arc of the given radius."""
    P = np.asarray(pts, float)
    M = len(P)
    radii = np.broadcast_to(np.asarray(radii, float), (M,))
    out = []
    for i in range(M):
        p, a, b = P[i], P[i - 1], P[(i + 1) % M]
        r = radii[i]
        u = a - p; lu = np.linalg.norm(u); u /= lu
        w = b - p; lw = np.linalg.norm(w); w /= lw
        th = math.acos(np.clip(u @ w, -1, 1))
        if r <= 0 or th < 1e-3 or th > math.pi - 1e-3:
            out.append(p); continue
        t = min(r / math.tan(th / 2), 0.49 * lu, 0.49 * lw)
        rr = t * math.tan(th / 2)
        bis = (u + w) / np.linalg.norm(u + w)
        c = p + bis * rr / math.sin(th / 2)
        t1, t2 = p + u * t, p + w * t
        a1 = math.atan2(*(t1 - c)[::-1]); a2 = math.atan2(*(t2 - c)[::-1])
        da = (a2 - a1 + math.pi) % (2 * math.pi) - math.pi
        for k in range(n_arc + 1):
            ang = a1 + da * k / n_arc
            out.append(c + rr * np.array([math.cos(ang), math.sin(ang)]))
    return np.array(out)


def star2(n, r_outer, r_inner, rotation=90.0, round=0.0, round_valley=None, n_arc=6):
    """n-pointed star with filleted tips (`round`) and valleys (`round_valley`, default round/2)."""
    pts = []
    for i in range(2 * n):
        r = r_outer if i % 2 == 0 else r_inner
        a = math.radians(rotation + 180.0 * i / n)
        pts.append((r * math.cos(a), r * math.sin(a)))
    if round > 0:
        rv = round * 0.5 if round_valley is None else round_valley
        pts = fillet_points(pts, [round if i % 2 == 0 else rv for i in range(2 * n)], n_arc)
    return polygon2(pts)


def rounded_polygon2(pts, r, n_arc=6):
    return polygon2(fillet_points(pts, r, n_arc))


def extrude(s2, h, round=0.0):
    """Extrude a 2D shape (in XY) along Z to half-depth h."""
    f = s2.fn
    hh = F(h)
    rr = F(round)

    def fn(p):
        d = f(p[:, :2]) + rr
        w = np.stack([d, np.abs(p[:, 2]) - hh + rr], 1)
        return np.minimum(np.max(w, 1), 0) + _len(np.maximum(w, 0)) - rr
    return SDF(fn, [s2.lo[0], s2.lo[1], -h], [s2.hi[0], s2.hi[1], h])


def revolve(s2, offset=0.0):
    """Revolve a 2D profile given in (r, y) around the Y axis."""
    f = s2.fn
    o = F(offset)

    def fn(p):
        q = np.stack([_len(p[:, [0, 2]]) - o, p[:, 1]], 1)
        return f(q)
    R = max(abs(s2.lo[0]), abs(s2.hi[0])) + offset
    return SDF(fn, [-R, s2.lo[1], -R], [R, s2.hi[1], R])


def spline_profile(points, samples=48):
    """Catmull-Rom through (r, y) points from the bottom axis point to the top axis point.
    Returns a closed polygon (mirrored across r=0) suitable for revolve()."""
    P = np.asarray(points, float)
    P2 = np.vstack([P[0], P, P[-1]])
    out = []
    for i in range(1, len(P2) - 2):
        p0, p1, p2, p3 = P2[i - 1], P2[i], P2[i + 1], P2[i + 2]
        for t in np.linspace(0, 1, samples // (len(P) - 1), endpoint=False):
            t2, t3 = t * t, t * t * t
            out.append(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t2 + (-p0 + 3 * p1 - 3 * p2 + p3) * t3))
    out.append(P[-1])
    out = np.array(out)
    out[:, 0] = np.maximum(out[:, 0], 0)
    mirror = out[::-1].copy()
    mirror[:, 0] *= -1
    poly = np.vstack([out, mirror[1:-1]])
    return polygon2(poly)


# --------------------------------------------------------------------------- utilities

def gradient(sdf, p, eps=1e-3):
    """Central-difference gradient (unnormalised) at points p (N,3)."""
    p = np.asarray(p, F)
    e = F(eps)
    g = np.empty_like(p)
    for i in range(3):
        d = np.zeros(3, F); d[i] = e
        g[:, i] = sdf(p + d) - sdf(p - d)
    return g / (2 * e)


def normals(sdf, p, eps=1e-3):
    g = gradient(sdf, p, eps)
    n = np.linalg.norm(g, axis=1, keepdims=True)
    return g / np.maximum(n, 1e-8)


def value_noise3(p, freq=4.0, seed=0):
    """Cheap smooth 3D value noise in [-1, 1] for surface displacement."""
    rng = np.random.default_rng(seed)
    table = rng.uniform(-1, 1, 4096).astype(F)
    q = p * F(freq)
    i = np.floor(q).astype(np.int64)
    f = q - i
    u = f * f * (3 - 2 * f)

    def h(ix, iy, iz):
        return table[(ix * 73856093 ^ iy * 19349663 ^ iz * 83492791) & 4095]
    x, y, z = i[:, 0], i[:, 1], i[:, 2]
    ux, uy, uz = u[:, 0], u[:, 1], u[:, 2]
    c000 = h(x, y, z); c100 = h(x + 1, y, z); c010 = h(x, y + 1, z); c110 = h(x + 1, y + 1, z)
    c001 = h(x, y, z + 1); c101 = h(x + 1, y, z + 1); c011 = h(x, y + 1, z + 1); c111 = h(x + 1, y + 1, z + 1)
    x00 = c000 + (c100 - c000) * ux; x10 = c010 + (c110 - c010) * ux
    x01 = c001 + (c101 - c001) * ux; x11 = c011 + (c111 - c011) * ux
    y0 = x00 + (x10 - x00) * uy; y1 = x01 + (x11 - x01) * uy
    return y0 + (y1 - y0) * uz


def fibonacci_sphere(n, seed=0, jitter=0.0):
    """n well-spread unit vectors."""
    rng = np.random.default_rng(seed)
    i = np.arange(n) + 0.5
    phi = np.arccos(1 - 2 * i / n)
    theta = math.pi * (1 + 5 ** 0.5) * i
    v = np.stack([np.cos(theta) * np.sin(phi), np.cos(phi), np.sin(theta) * np.sin(phi)], 1)
    if jitter:
        v += rng.normal(0, jitter, v.shape)
        v /= np.linalg.norm(v, axis=1, keepdims=True)
    return v


def project_to_surface(sdf, p, iters=4, eps=1e-3):
    """Newton-project points onto the zero set."""
    p = np.asarray(p, F).copy()
    for _ in range(iters):
        d = sdf(p)
        g = gradient(sdf, p, eps)
        gn = np.sum(g * g, 1)
        p -= (d / np.maximum(gn, F(1e-8)))[:, None] * g
    return p


def round_cone2(a, b, ra, rb):
    """2D tapered capsule (convex hull of two circles) in XY."""
    rc = round_cone((a[0], a[1], 0.0), (b[0], b[1], 0.0), ra, rb)
    f = rc.fn

    def fn(p):
        q = np.concatenate([p, np.zeros((len(p), 1), F)], 1)
        return f(q)
    m = max(ra, rb)
    return SDF2(fn, np.minimum(a, b) - m, np.maximum(a, b) + m)


def capsule2(a, b, r):
    return round_cone2(a, b, r, r)


def path_tube(points, radii):
    """Tube through a polyline of 3D points with per-point radii (union of round cones)."""
    segs = [round_cone(points[i], points[i + 1], radii[i], radii[i + 1]) for i in range(len(points) - 1)]
    return union(*segs)
