"""Fur for the characters lane: geometric STRAND CARDS grown on an SDF surface (not a recipe: no ASSETS).

Why strands (the fur spike, art/lanes/characters.md): the reference scientist is a groomed fur render -- a fuzzy,
tufted silhouette (crown tuft, cheek/jowl tufts) and a fine streaky interior. mfrender (RealityKit PBR from USDZ
UsdPreviewSurface) has no hair shader, no alpha-tested shells and no normal maps in our writer, but it renders a
million triangles in seconds. So the fur is real geometry: tens of thousands of thin tapered ribbons, each one
  - rooted on the body's SDF surface (area-weighted samples of its marching-cubes mesh, roots slightly buried),
  - grown along a groom field: lift off the surface + a comb direction in the tangent plane + gravity, in `segs`
    segments that bend from `lift` toward lying flat,
  - CLUMPED: strands pull toward the nearest guide strand toward their tips (tufts, not a velvet),
  - camera-facing (a billboarded ribbon: the camera is fixed per render), double-sided (both windings),
  - shaded with the SURFACE normal bent a little toward the strand (the soft form of the body reads through the fur),
  - coloured through a 2D LUT texture: u = the character's volumetric obscurance at the root (convex/thin -> light,
    crease -> deep saturated: the warm glow of the reference), v = root -> tip tone + a per-strand jitter.

Premeshed parts: a Part whose `premesh` attribute (a callable -> (v, f, n, uv)) replaces marching cubes; char_make.py
teaches ui3d.mesh_parts to use it (runtime patch; see art/lanes/requests.md).
"""
from __future__ import annotations

import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
PIPE = os.path.dirname(HERE)
if PIPE not in sys.path:
    sys.path.insert(0, PIPE)

from mesher import Material, Part, _normals, _project, mc_mesh  # noqa: E402

import char_kit as K  # noqa: E402


def unit(a):
    a = np.asarray(a, float)
    return a / np.maximum(np.linalg.norm(a, axis=-1, keepdims=True), 1e-9)


_SURF = {}


def surface(sdf, voxel, key=None):
    """(v, f, n) of the SDF's zero set (cached per key in this process)."""
    if key is not None and key in _SURF:
        return _SURF[key]
    v, f = mc_mesh(sdf, voxel)
    v = _project(sdf, v, eps=0.5 * voxel)
    n = _normals(sdf, v, eps=0.5 * voxel)
    out = (v, f, n)
    if key is not None:
        _SURF[key] = out
    return out


def sample(v, f, n, count, rng, density=None):
    """Area-weighted random points on the mesh; density(points) -> weight >= 0 (evaluated at triangle centroids)."""
    a, b, c = v[f[:, 0]], v[f[:, 1]], v[f[:, 2]]
    w = 0.5 * np.linalg.norm(np.cross(b - a, c - a), axis=1)
    if density is not None:
        w = w * np.clip(density((a + b + c) / 3), 0, None)
    idx = rng.choice(len(f), size=count, p=w / w.sum())
    r1 = np.sqrt(rng.random(count))
    r2 = rng.random(count)
    wa, wb, wc = 1 - r1, r1 * (1 - r2), r1 * r2
    P = a[idx] * wa[:, None] + b[idx] * wb[:, None] + c[idx] * wc[:, None]
    N = unit(n[f[idx, 0]] * wa[:, None] + n[f[idx, 1]] * wb[:, None] + n[f[idx, 2]] * wc[:, None])
    return P, N


def strands(P, N, comb, length, lift, width, view, rng, segs=4, gravity=(0, 0, 0), clump=0.45, clump_size=0.05,
            per_clump=24, bend=0.65, jitter=0.25, nbend=0.35):
    """Grow strand cards. P, N: roots + surface normals (M, 3); comb: (M, 3) flow directions (any; projected to the
    tangent plane); length, lift, width: scalars or (M,) arrays; view: unit vector from the model toward the camera
    (model space). Returns (V, F, NRM, T, root_index) with T = the vertex's position along its strand (0 root, 1 tip).

    lift: 0 = lying on the surface, 1 = standing straight out; `bend` of the lift is lost toward the tip (the strand
    lays over); gravity: a world vector added along the strand (x t); clump: 0..1 pull toward the nearest guide's path
    (x t^1.5; guides = M / per_clump, reach 2.5 x clump_size); jitter: random direction noise; nbend: how far the shading normal leans toward the strand at the tip."""
    M = len(P)
    L = np.broadcast_to(np.asarray(length, float), (M,)).copy()
    lf = np.broadcast_to(np.asarray(lift, float), (M,)).copy()
    W = np.broadcast_to(np.asarray(width, float), (M,)).copy()
    g = np.asarray(gravity, float)
    T = np.asarray(comb, float)
    T = T - N * np.sum(T * N, 1, keepdims=True)
    T = unit(T + rng.normal(0, jitter, (M, 3)))
    T = unit(T - N * np.sum(T * N, 1, keepdims=True))
    ts = np.linspace(0, 1, segs + 1)
    pts = np.empty((M, segs + 1, 3))
    dirs = np.empty((M, segs + 1, 3))
    pts[:, 0] = P - N * (W[:, None] * 0.9)          # the root sits a little inside the skin
    for k in range(segs + 1):
        tm = (k + 0.5) / segs
        l_k = lf * (1 - bend * tm)
        d = unit(N * l_k[:, None] + T * (1 - l_k)[:, None] + g[None] * tm)
        dirs[:, k] = d
        if k < segs:
            pts[:, k + 1] = pts[:, k] + d * (L / segs)[:, None]
    # clumping: pull toward the path of the nearest guide strand (guides = a subset, nearest by root distance)
    ck = np.asarray(clump, float)              # LOOK-L: a scalar (as before) or a PER-STRAND clump (a calm velvet face)
    if np.any(ck > 0) and M > 8:
        from scipy.spatial import cKDTree
        ng = max(4, M // max(1, per_clump))
        gi = rng.choice(M, size=min(ng, M), replace=False)
        tree = cKDTree(P[gi])
        dist, j = tree.query(P, k=1)
        G = pts[gi[j]] - pts[gi[j], :1] + pts[:, :1]            # the guide's shape, re-rooted at this strand's root
        wgt = ck * np.clip(1 - dist / (clump_size * 2.5), 0, 1)
        pts = pts + (G - pts) * (wgt[:, None, None] * (ts[None, :, None] ** 1.5))
        # directions follow the clumped path
        dd = np.diff(pts, axis=1)
        dirs[:, :segs] = unit(dd)
        dirs[:, segs] = dirs[:, segs - 1]
    # ribbon cross-section: perpendicular to the strand and the view (billboard)
    vw = unit(np.asarray(view, float))
    side = np.cross(dirs, vw[None, None, :])
    sn = np.linalg.norm(side, axis=2, keepdims=True)
    alt = np.cross(dirs, np.array([0.0, 1.0, 0.0])[None, None, :])
    side = np.where(sn > 0.15, side / np.maximum(sn, 1e-9), unit(alt))
    taper = (1 - ts) ** 0.75
    half = (W[:, None] * taper[None, :] * 0.5)[..., None]
    left = pts[:, :segs] + side[:, :segs] * half[:, :segs]
    right = pts[:, :segs] - side[:, :segs] * half[:, :segs]
    tip = pts[:, segs]
    # vertices per strand: L0 R0 L1 R1 ... L(s-1) R(s-1) TIP
    nv = 2 * segs + 1
    V = np.empty((M, nv, 3))
    V[:, 0:2 * segs:2] = left
    V[:, 1:2 * segs:2] = right
    V[:, 2 * segs] = tip
    tv = np.empty(nv)
    tv[0:2 * segs:2] = ts[:segs]
    tv[1:2 * segs:2] = ts[:segs]
    tv[2 * segs] = 1.0
    # shading normals: the surface normal leaning toward the strand direction near the tip
    dv = np.empty((M, nv, 3))
    dv[:, 0:2 * segs:2] = dirs[:, :segs]
    dv[:, 1:2 * segs:2] = dirs[:, :segs]
    dv[:, 2 * segs] = dirs[:, segs]
    NR = unit(N[:, None, :] * (1 - nbend * tv[None, :, None]) + dv * (nbend * tv[None, :, None]))
    # faces
    fl = []
    for k in range(segs - 1):
        a, b, c, d = 2 * k, 2 * k + 1, 2 * k + 2, 2 * k + 3
        fl += [(a, b, d), (a, d, c)]
    fl.append((2 * segs - 2, 2 * segs - 1, 2 * segs))
    fl = np.array(fl, np.int64)
    base = (np.arange(M) * nv)[:, None, None]
    Fx = (fl[None] + base).reshape(-1, 3)
    Fx = np.vstack([Fx, Fx[:, ::-1]])            # double-sided
    root_idx = np.repeat(np.arange(M), nv)
    return V.reshape(-1, 3), Fx, NR.reshape(-1, 3), np.tile(tv, M), root_idx


def lut_v(stops):
    """2D LUT fn(u, v): stops = [(v, ramp over u), ...] ascending in v; linear blend between neighbouring ramps."""
    vs = np.array([s[0] for s in stops], float)

    def fn(u, v):
        cols = np.stack([K._ramp(r, u) for _, r in stops], 0)          # (S, H, W, 3)
        i = np.clip(np.searchsorted(vs, v, side="right") - 1, 0, len(vs) - 2)
        t = np.clip((v - vs[i]) / np.maximum(vs[i + 1] - vs[i], 1e-9), 0, 1)[..., None]
        a = np.take_along_axis(cols, i[None, ..., None].repeat(3, -1), 0)[0]
        b = np.take_along_axis(cols, (i + 1)[None, ..., None].repeat(3, -1), 0)[0]
        return a + (b - a) * t
    return fn


def fur_material(name, ramp_root, ramp_tip=None, rough=0.62, ior=1.22, size=(128, 64), stops=None):
    """LUT material: u = obscurance (0 convex/thin .. 0.5 flat .. 1 crease), v = tone (0 root .. 1 tip); or `stops`
    = [(v, ramp), ...] for more than two tone rows (e.g. an underside row below the roots)."""
    fn = lut_v(stops) if stops else K.lut(ramp_root, ramp_tip)
    base = (stops[len(stops) // 2][1] if stops else ramp_root)
    return Material(name, base[len(base) // 2][1], roughness=rough, ior=ior, texture=fn, texture_size=size)


def fur_part(name, material, build):
    """A premeshed Part: build() -> (v, f, n, uv); not an occluder, never marching-cubed."""
    p = Part(name, None, material, occluder=False, collide=False)
    p.__dict__["premesh"] = build
    return p


def tone_uv(field, V, T, root_idx, P, rng_tone, tone0=0.18, tone_gain=0.72, cav_gain=2.2, N=None, under=0.0,
            up=(0.0, 1.0, 0.0)):
    """uv for strand vertices: u = obscurance at the strand's ROOT (one value per strand: no speckle along it),
    v = tone0 + tone_gain * t + per-strand jitter - under * (how much the root faces DOWN): the reference darkens the
    underside of the jowls into a deeper saturated shade that a warm bounce light alone does not give."""
    u_root = K.cavity_u(field, P, gain=cav_gain)
    u = u_root[root_idx]
    dn = np.zeros(len(P)) if N is None else np.clip(-(np.asarray(N) @ np.asarray(up, float)), 0, 1)
    tg = np.asarray(tone_gain, float)                 # LOOK-L: a scalar (as before) or a per-strand gain
    tg = tg[root_idx] if tg.ndim else tg
    v = np.clip(tone0 + tg * T + rng_tone[root_idx] - under * dn[root_idx], 0.02, 0.98)
    return np.stack([u, v], 1)
