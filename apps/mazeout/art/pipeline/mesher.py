"""SDF item -> per-part triangle meshes on a triangle budget.

Pipeline per item:
  1. every part: sparse grid evaluation (coarse blocks, fine only near the surface)
     -> marching cubes (skimage) -> closed, manifold mesh at `voxel` resolution
  2. hidden-surface estimate: triangles buried inside other (occluder) parts
  3. budget split: item budget shared by visible area x part.detail, with a floor
     per connected component (so 40 seeds keep a real shape each)
  4. quadric decimation (fast_simplification) of the closed mesh to that target,
     Newton-projection of vertices back onto the SDF, SDF-gradient normals
  5. buried triangles removed (open only where hidden inside another part)
  6. whole item: union SDF voxel -> volume, centre of mass, stable resting poses,
     convex hulls for physics; geometry re-centred so the COM is the origin and
     scaled so the longest side = item.length (1 unit = 1 board cell)
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Callable, Optional

import numpy as np
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components
from skimage.measure import marching_cubes
import fast_simplification

from sdf import SDF, F, gradient, union

# --------------------------------------------------------------------------- data model


@dataclass
class Material:
    name: str
    color: str  # sRGB hex, e.g. "#FFC400"
    roughness: float = 0.45
    metallic: float = 0.0
    clearcoat: float = 0.0
    clearcoat_roughness: float = 0.2
    emissive: Optional[str] = None
    specular: float = 0.5
    ior: float = 1.2  # low specular like the original (RealityKit maps ior->specular: 1.5->0.5, 1.25->0.15, 1.1->0.03); F0 = ((ior-1)/(ior+1))^2 ; 1.5 -> 0.04, 1.25 -> 0.012
    specular_color: Optional[str] = None  # set -> UsdPreviewSurface specular workflow with this F0 colour
    opacity: float = 1.0  # < 1 -> RealityKit blended transparency (glass/ice); keep >= 0.8 for pile items
    # optional procedural texture: fn(u, v) -> (H, W, 3) sRGB in [0,1]; u,v are (H,W) grids in [0,1)
    texture: Optional[Callable] = None
    texture_size: int = 256

    def color_srgb(self):
        return hex_to_rgb(self.color)


@dataclass
class Part:
    name: str
    sdf: SDF
    material: Material
    voxel: Optional[float] = None  # override item voxel (smaller for tiny details)
    detail: float = 1.0  # budget weight multiplier (curvy/small parts > 1)
    min_tris: int = 24  # floor per connected component
    occluder: bool = True  # hides other parts' buried triangles
    collide: bool = True  # contributes a convex hull to the physics compound
    cut: bool = False  # subtract occluding neighbours before meshing (opt-in: creates buried creases the decimator keeps)
    uv: Optional[tuple] = None  # ("cyl", origin, axis, v_scale) | ("planar", origin, u_axis, v_axis, scale) | ("sphere", origin)


@dataclass
class Item:
    name: str
    parts: list
    length: float = 1.0  # longest bbox side after scaling, in board cells
    budget: int = 3000  # total triangles
    voxel: float = 0.006  # authoring-space voxel
    display_name: str = ""
    notes: str = ""
    icon_view: tuple = (0.0, 0.0)  # (yaw, pitch) degrees for the goal-card icon, front = +Z
    # ---- tray / goal card (see PIPELINE.md "Tray and goal-card data")
    tray_view: Optional[tuple] = None  # (yaw, pitch, roll) deg standing the item upright facing +Z; None -> (icon yaw, 0, 0)
    tray_scale: Optional[float] = None  # override: on-screen size in the tray / size lying on the board (default: auto, <= 0.63)
    board_scale: float = 1.0  # hint for the engine: extra scale on the board (1 = modelled size)
    # ---- catalogue (None -> read from research/items.md by the item's slug)
    first_level: Optional[int] = None
    role: Optional[str] = None  # "goal" | "filler"
    slug: Optional[str] = None  # research name, e.g. "toy-hammer" (default: name with '_' -> '-')
    # ---- references for the contact sheet (paths relative to apps/matchfactory)
    ref_poses: list = field(default_factory=list)  # [(crop, ("up", item_axis[, roll]) | stable_pose_index, yaw_deg), ...]
    icon_ref: Optional[tuple] = None  # (goal-card image, (l, t, r, b) crop box) for the icon comparison
    tray_ref: Optional[str] = None  # crop of the item standing in the tray (default research/items/<slug>-upright-tray.png)
    # ---- outline shell for the engine's constant-width outline shader
    outline_tris: int = 600
    outline_voxel: Optional[float] = None  # authoring-space voxel for the shell (default: longest side / 56)
    variant_of: Optional[str] = None  # set by recolor(): id of the item whose geometry this one shares


def hex_to_rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) / 255.0 for i in (0, 2, 4))


def recolor(item: Item, name: str, materials: dict, display_name: str = "", **overrides) -> Item:
    """A colour variant of `item`: same SDFs (so build.py meshes the geometry ONCE), other materials.

    `materials` maps an old material name OR a part name -> new Material. Everything else
    (icon view, tray pose, budget ...) is inherited unless given in `overrides`, e.g. ref_poses=[...]."""
    from dataclasses import replace as _r
    parts = []
    for p in item.parts:
        m = materials.get(p.name) or materials.get(p.material.name) or p.material
        parts.append(_r(p, material=m))
    kw = dict(name=name, parts=parts, display_name=display_name or name.replace("_", " ").title(),
              variant_of=item.variant_of or item.name, first_level=None, role=None, slug=None,
              ref_poses=[], icon_ref=None, tray_ref=None)
    kw.update(overrides)
    return _r(item, **kw)


def load_items(recipe: str):
    """Import items/<recipe>.py and return its build() result as a list of Items (variants included)."""
    import importlib
    import os
    import sys
    here = os.path.dirname(os.path.abspath(__file__))
    if here not in sys.path:
        sys.path.insert(0, here)
    res = importlib.import_module(f"items.{recipe}").build()
    items = list(res) if isinstance(res, (list, tuple)) else [res]
    names = [it.name for it in items]
    assert len(set(names)) == len(names), f"{recipe}: duplicate item ids {names}"
    return items


def geometry_key(item: Item):
    """Items with the same key share every mesh (colour variants made with recolor())."""
    return tuple((id(p.sdf), p.voxel, p.detail, p.min_tris, p.occluder, p.cut, repr(p.uv)) for p in item.parts) + (
        item.length, item.budget, item.voxel, item.outline_tris, item.outline_voxel)


def srgb_to_linear(c):
    c = np.asarray(c, float)
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


# --------------------------------------------------------------------------- sparse grid evaluation

def eval_grid(sdf: SDF, lo, hi, voxel, block=8, chunk=1_500_000, lipschitz=1.5):
    """Evaluate `sdf` on a regular grid; only blocks near the surface are evaluated finely."""
    lo = np.asarray(lo, float)
    n = np.ceil((np.asarray(hi, float) - lo) / voxel).astype(int) + 1
    nb = np.ceil(n / block).astype(int)
    # coarse evaluation at block centres
    bi = np.stack(np.meshgrid(*[np.arange(k) for k in nb], indexing="ij"), -1).reshape(-1, 3)
    centers = lo + (bi * block + (block - 1) / 2.0) * voxel
    dc = _eval_chunks(sdf, centers.astype(F), chunk)
    half_diag = block * voxel * math.sqrt(3) / 2
    near = np.abs(dc) < lipschitz * half_diag + 2 * voxel
    vol = np.empty(tuple(nb * block), F)
    # far blocks: constant sign fill
    far_val = np.where(dc > 0, F(block * voxel), F(-block * voxel)).astype(F)
    vb = vol.reshape(nb[0], block, nb[1], block, nb[2], block)
    vb[...] = far_val.reshape(nb[0], 1, nb[1], 1, nb[2], 1)
    # near blocks: exact
    nbi = bi[near]
    if len(nbi):
        off = np.stack(np.meshgrid(np.arange(block), np.arange(block), np.arange(block), indexing="ij"), -1).reshape(-1, 3)
        # process in groups of blocks to bound memory
        per = max(1, chunk // len(off))
        for s in range(0, len(nbi), per):
            g = nbi[s:s + per]
            idx = (g[:, None, :] * block + off[None, :, :]).reshape(-1, 3)
            pts = (lo + idx * voxel).astype(F)
            d = sdf(pts)
            vol[idx[:, 0], idx[:, 1], idx[:, 2]] = d
    vol = vol[: n[0], : n[1], : n[2]]
    return vol, lo, near.mean()


def _eval_chunks(sdf, pts, chunk):
    out = np.empty(len(pts), F)
    for s in range(0, len(pts), chunk):
        out[s:s + chunk] = sdf(pts[s:s + chunk])
    return out


def mc_mesh(sdf: SDF, voxel: float, pad=None):
    pad = pad if pad is not None else 3 * voxel
    lo = sdf.lo - pad
    hi = sdf.hi + pad
    vol, lo, frac = eval_grid(sdf, lo, hi, voxel)
    if vol.min() >= 0 or vol.max() <= 0:
        raise ValueError("part has no surface inside its bounds")
    v, f, _, _ = marching_cubes(vol, level=0.0, spacing=(voxel,) * 3, allow_degenerate=False)
    v = v + lo
    v, f = _orient_outward(v, f)
    return v.astype(np.float64), f.astype(np.int64)


def _orient_outward(v, f):
    # signed volume > 0 for outward-facing CCW triangles
    a, b, c = v[f[:, 0]], v[f[:, 1]], v[f[:, 2]]
    vol = np.einsum("ij,ij->i", a, np.cross(b, c)).sum() / 6.0
    if vol < 0:
        f = f[:, ::-1].copy()
    return v, f


# --------------------------------------------------------------------------- mesh utilities

def tri_areas(v, f):
    return 0.5 * np.linalg.norm(np.cross(v[f[:, 1]] - v[f[:, 0]], v[f[:, 2]] - v[f[:, 0]]), axis=1)


def n_components(nv, f):
    if len(f) == 0:
        return 0
    rows = np.r_[f[:, 0], f[:, 1], f[:, 2]]
    cols = np.r_[f[:, 1], f[:, 2], f[:, 0]]
    g = coo_matrix((np.ones(len(rows)), (rows, cols)), shape=(nv, nv))
    k, lab = connected_components(g, directed=False)
    used = np.unique(f)
    return len(np.unique(lab[used]))


def drop_crumbs(v, f, min_frac=0.002):
    """Remove connected components whose area is below min_frac of the total (marching-cubes crumbs)."""
    if len(f) == 0:
        return f, 0
    nv = len(v)
    rows = np.r_[f[:, 0], f[:, 1], f[:, 2]]
    cols = np.r_[f[:, 1], f[:, 2], f[:, 0]]
    g = coo_matrix((np.ones(len(rows)), (rows, cols)), shape=(nv, nv))
    _, lab = connected_components(g, directed=False)
    fl = lab[f[:, 0]]
    a = tri_areas(v, f)
    tot = a.sum()
    area = np.bincount(fl, weights=a)
    small = np.nonzero(area < min_frac * tot)[0]
    if len(small) == 0:
        return f, 0
    keep = ~np.isin(fl, small)
    return f[keep], int(len(small))


def cap_holes(v, f):
    """Close every boundary loop with a centroid fan (orientation consistent with the mesh).
    Used after the deep pre-cull: a closed tube decimates without its buried rim shrinking."""
    e = np.r_[f[:, [0, 1]], f[:, [1, 2]], f[:, [2, 0]]]
    fwd = set(map(tuple, e))
    nxt = {}
    for a, b in e:
        if (b, a) not in fwd:
            if a in nxt:  # non-manifold boundary vertex: leave this loop alone
                nxt[a] = -1
            else:
                nxt[a] = b
    seen = set()
    newv, newf = [], []
    nv = len(v)
    for start in list(nxt.keys()):
        if start in seen or nxt[start] == -1:
            continue
        loop = [start]
        seen.add(start)
        cur = nxt[start]
        ok = True
        while cur != start:
            if cur in seen or cur not in nxt or nxt[cur] == -1 or len(loop) > 100000:
                ok = False
                break
            loop.append(cur); seen.add(cur)
            cur = nxt[cur]
        if not ok or len(loop) < 3:
            continue
        c = nv + len(newv)
        newv.append(v[loop].mean(0))
        for i in range(len(loop)):
            a, b = loop[i], loop[(i + 1) % len(loop)]
            newf.append((b, a, c))
    if not newv:
        return v, f, 0
    return np.vstack([v, np.array(newv)]), np.vstack([f, np.array(newf, np.int64)]), len(newv)


def compact(v, f, extra=None):
    used = np.unique(f)
    remap = -np.ones(len(v), np.int64)
    remap[used] = np.arange(len(used))
    out = [v[used], remap[f]]
    if extra is not None:
        out.append([e[used] for e in extra])
    return out


def edge_stats(f):
    """Counts of boundary and non-manifold edges."""
    e = np.sort(np.r_[f[:, [0, 1]], f[:, [1, 2]], f[:, [2, 0]]], axis=1)
    _, cnt = np.unique(e, axis=0, return_counts=True)
    return int((cnt == 1).sum()), int((cnt > 2).sum())


def buried_mask(v, f, other: Optional[SDF], margin):
    """Triangles whose vertices and centroid are all inside `other` by more than margin."""
    if other is None or len(f) == 0:
        return np.zeros(len(f), bool)
    dv = other(v.astype(F))
    cen = v[f].mean(1).astype(F)
    dc = other(cen)
    return (dv[f] < -margin).all(1) & (dc < -margin)


# --------------------------------------------------------------------------- UVs

def compute_uv(v, f, spec):
    """Returns (v, f, uv, remap) with seam-crossing triangles given duplicated vertices."""
    kind = spec[0]
    if kind == "fn":
        # ("fn", callable): callable(vertices (N, 3)) -> (N, 2) uv, e.g. per-vertex baked AO / thickness looked up in a
        # 2D LUT texture (characters lane request 3, art/lanes/requests.md). No seam handling: the callable owns it.
        uv = np.asarray(spec[1](v), float)
        assert uv.shape == (len(v), 2), f"uv fn returned {uv.shape}, expected ({len(v)}, 2)"
        return v, f, uv, np.arange(len(v))
    if kind == "planar":
        _, o, ua, va, sc = spec
        o = np.asarray(o, float)
        uv = np.stack([(v - o) @ np.asarray(ua, float), (v - o) @ np.asarray(va, float)], 1) * sc
        return v, f, uv, np.arange(len(v))
    if kind == "cyl":
        _, o, ax, vs = spec[:4]
        vo = spec[4] if len(spec) > 4 else 0.0
        o = np.asarray(o, float)
        ax = np.asarray(ax, float); ax /= np.linalg.norm(ax)
        ref = np.array([1.0, 0, 0]) if abs(ax[0]) < 0.9 else np.array([0, 1.0, 0])
        e1 = ref - ax * (ref @ ax); e1 /= np.linalg.norm(e1)
        e2 = np.cross(ax, e1)
        q = v - o
        u = (np.arctan2(q @ e2, q @ e1) / (2 * math.pi)) % 1.0
        vv = (q @ ax) * vs + vo
        uv = np.stack([u, vv], 1)
    elif kind == "sphere":
        _, o = spec
        q = v - np.asarray(o, float)
        q /= np.maximum(np.linalg.norm(q, axis=1, keepdims=True), 1e-9)
        u = (np.arctan2(q[:, 2], q[:, 0]) / (2 * math.pi)) % 1.0
        vv = np.arccos(np.clip(q[:, 1], -1, 1)) / math.pi
        uv = np.stack([u, vv], 1)
    else:
        raise ValueError(kind)
    # seam fix: triangles spanning u 0.9 -> 0.1 get duplicated vertices with u+1
    tu = uv[f, 0]
    span = tu.max(1) - tu.min(1)
    bad = np.nonzero(span > 0.5)[0]
    remap = np.arange(len(v))
    if len(bad):
        v = v.copy(); uv = uv.copy(); f = f.copy()
        extra_v, extra_uv, extra_src = [], [], []
        key = {}
        nv = len(v)
        for t in bad:
            for j in range(3):
                vi = f[t, j]
                if uv[vi, 0] < 0.5:
                    if vi not in key:
                        key[vi] = nv + len(extra_v)
                        extra_v.append(v[vi]); extra_uv.append([uv[vi, 0] + 1.0, uv[vi, 1]]); extra_src.append(vi)
                    f[t, j] = key[vi]
        v = np.vstack([v, np.array(extra_v)])
        uv = np.vstack([uv, np.array(extra_uv)])
        remap = np.r_[remap, np.array(extra_src, np.int64)]
    return v, f, uv, remap


def bake_texture(mat: Material):
    n = mat.texture_size
    w, h = (n, n) if np.isscalar(n) else n
    u, v = np.meshgrid((np.arange(w) + 0.5) / w, (np.arange(h) + 0.5) / h)
    img = np.clip(mat.texture(u, v), 0, 1)
    # image row 0 is v=1 (USD/GL convention: v up)
    return (img[::-1] * 255 + 0.5).astype(np.uint8)


# --------------------------------------------------------------------------- the build


@dataclass
class PartMesh:
    part: Part
    v: np.ndarray
    f: np.ndarray
    n: np.ndarray
    uv: Optional[np.ndarray] = None
    stats: dict = field(default_factory=dict)


def build_item(item: Item, log=print, cull_hidden=True, recipe=None, item_index=0):
    """Returns (part meshes, meta, (union_v, union_f) for stable poses, outline dict)."""
    parts = item.parts
    names = [p.name for p in parts]
    assert len(set(names)) == len(names), "part names must be unique"

    # 1. each part minus its (slightly shrunk) occluding neighbours -> closed meshes whose
    #    buried portion is only a thin cap, so decimation spends triangles where they show
    others, cut = [], []
    for i in range(len(parts)):
        o, c = part_cut(item, i)
        others.append(o); cut.append(c)
    raw = _parallel_mc(item, cut, [p.voxel or item.voxel for p in parts], recipe=recipe, item_index=item_index)

    # 2. cull buried triangles on the full-res mesh (1-voxel margin), drop crumbs
    vis = []
    for i, (v, f, vx) in enumerate(raw):
        closed_b, closed_nm = edge_stats(f)
        # only DEEPLY buried triangles go before decimation: open borders then sit >= 4 voxels inside
        # the occluder, so border collapse (chords) during decimation can never show
        hid = buried_mask(v, f, others[i], margin=4.0 * vx) if cull_hidden else np.zeros(len(f), bool)
        fv = f[~hid]
        fv, dropped = drop_crumbs(v, fv, min_frac=0.002)
        v1, f1 = compact(v, fv)
        v1, f1, _capped = cap_holes(v1, f1)
        vis.append((v1, f1, vx, dict(mc_tris=int(len(f)), mc_boundary_edges=closed_b, mc_nonmanifold_edges=closed_nm,
                                     buried_frac=round(float(hid.mean()), 3), crumbs_dropped=dropped)))

    # 3. budget split by visible area x detail, with a floor per connected component
    areas = np.array([tri_areas(v, f).sum() for v, f, _, _ in vis])
    comps = [n_components(len(v), f) for v, f, _, _ in vis]
    w = areas * np.array([p.detail for p in parts])
    floors = np.array([parts[i].min_tris * comps[i] for i in range(len(parts))], float)
    free = max(item.budget - floors.sum(), 0)
    share = floors + free * w / max(w.sum(), 1e-9)

    # 4-5. decimate the visible surface (open borders stay buried: border vertices only collapse
    #      along the border), project back onto the SDF, SDF-gradient normals, final cull
    out = []
    for i, p in enumerate(parts):
        v, f, vx, st0 = vis[i]
        target = int(max(share[i], 4 * comps[i]))
        goal = target
        for it in range(4):
            if goal < len(f):
                v2, f2 = fast_simplification.simplify(v, f.astype(np.int32), target_count=goal, agg=5)
            else:
                v2, f2 = v, f
            v2 = np.asarray(v2, np.float64)
            f2 = np.asarray(f2, np.int64)
            # project back onto the (cut) surface; normals from the uncut part so creases at
            # the buried cap never bend the shading of the visible side
            v2 = _project(cut[i], v2, eps=0.5 * vx)
            hid = buried_mask(v2, f2, others[i], margin=0.5 * vx) if cull_hidden else np.zeros(len(f2), bool)
            shipped = int((~hid).sum())
            if goal >= len(f) or abs(shipped - target) <= 0.12 * target:
                break
            goal = int(min(len(f), max(8, goal * target / max(shipped, 1))))
        nrm = _normals(p.sdf, v2, eps=0.5 * vx)
        fn_ = np.cross(v2[f2[:, 1]] - v2[f2[:, 0]], v2[f2[:, 2]] - v2[f2[:, 0]])
        agree = np.einsum("ij,ij->i", fn_, _normals(cut[i], v2, eps=0.5 * vx)[f2].mean(1)) > 0
        if agree.mean() < 0.5:
            f2 = f2[:, ::-1].copy()
            agree = ~agree
        flipped = int((~agree).sum())
        f3 = f2[~hid]
        v3, f3, (n3,) = compact(v2, f3, [nrm])
        uv = None
        if p.uv is not None:
            v3, f3, uv, remap = compute_uv(v3, f3, p.uv)
            n3 = n3[remap]
        b_open, nm_open = edge_stats(f3)
        st = dict(tris=int(len(f3)), verts=int(len(v3)), target=target, components=int(comps[i]),
                  boundary_edges=b_open, nonmanifold_edges=nm_open, flipped_tris=flipped, voxel=vx, **st0)
        out.append(PartMesh(p, v3, f3, n3, uv, st))
        log(f"  {p.name:14s} mc {st0['mc_tris']:7d} (open {st0['mc_boundary_edges']}, nm {st0['mc_nonmanifold_edges']}, "
            f"buried {st0['buried_frac']:.2f}, crumbs {st0['crumbs_dropped']}) -> {len(f3):5d} tris "
            f"(target {target}, {comps[i]} comp, nm {nm_open}, flipped {flipped})")

    # 6. mass properties from the union field
    U = union(*[p.sdf for p in parts])
    mvx = max(item.voxel * 1.5, 0.008)
    vol, lo, _ = eval_grid(U, U.lo - 2 * mvx, U.hi + 2 * mvx, mvx)
    inside = np.argwhere(vol < 0)
    pts_in = lo + inside * mvx
    com = pts_in.mean(0)
    volume = len(inside) * mvx ** 3
    # inertia tensor (unit density) about COM
    q = pts_in - com
    I = np.zeros((3, 3))
    I[0, 0] = np.sum(q[:, 1] ** 2 + q[:, 2] ** 2); I[1, 1] = np.sum(q[:, 0] ** 2 + q[:, 2] ** 2); I[2, 2] = np.sum(q[:, 0] ** 2 + q[:, 1] ** 2)
    I[0, 1] = I[1, 0] = -np.sum(q[:, 0] * q[:, 1]); I[0, 2] = I[2, 0] = -np.sum(q[:, 0] * q[:, 2]); I[1, 2] = I[2, 1] = -np.sum(q[:, 1] * q[:, 2])
    I *= mvx ** 3

    allv = np.vstack([pm.v for pm in out])
    bb_lo, bb_hi = allv.min(0), allv.max(0)
    scale = item.length / float(np.max(bb_hi - bb_lo))

    for pm in out:
        pm.v = (pm.v - com) * scale
    union_v, union_f = mc_mesh(U, mvx)
    union_v = (union_v - com) * scale
    union_v, union_f = fast_simplification.simplify(union_v, union_f.astype(np.int32), target_count=min(len(union_f), 3000), agg=5)
    outline = outline_mesh(item, U, com, scale, float(np.max(bb_hi - bb_lo)), log=log)

    meta = dict(
        name=item.name,
        display_name=item.display_name or item.name,
        units="1 unit = 1 board cell; metersPerUnit = 1",
        up="+Y", front="+Z",
        length=item.length,
        scale_from_authoring=scale,
        bbox_min=((bb_lo - com) * scale).round(4).tolist(),
        bbox_max=((bb_hi - com) * scale).round(4).tolist(),
        bbox_center=(((bb_lo + bb_hi) / 2 - com) * scale).round(4).tolist(),
        volume=round(volume * scale ** 3, 5),
        inertia_unit_density=(I * scale ** 5).round(6).tolist(),
        triangles=int(sum(len(pm.f) for pm in out)),
        vertices=int(sum(len(pm.v) for pm in out)),
        budget=item.budget,
        parts={pm.part.name: dict(material=pm.part.material.name, **pm.stats) for pm in out},
        icon_view=list(item.icon_view),
    )
    return out, meta, (np.asarray(union_v), np.asarray(union_f)), outline


# --------------------------------------------------------------------------- outline shell

def outline_mesh(item: Item, U: SDF, com, scale, longest, log=print):
    """Closed, manifold, low-poly shell of the union of all parts (iso-level 0) for the engine's
    constant-width outline shader: marching cubes at a coarse voxel -> keep the big components ->
    quadric decimation to item.outline_tris -> Newton projection onto the union -> smooth SDF normals.
    One vertex per position, so the shader's extrusion along the normal never cracks."""
    vx = item.outline_voxel or longest / 56.0
    target = int(item.outline_tris)
    best = None
    attempt_no = 0
    # Fallback (art-director fix 2026-09-24): thin gaps (fender/tyre, lugs, strings) can make every quadric
    # collapse of the exact union fold into non-manifold edges (monster_truck: 8 nm edges at any voxel/target).
    # If no attempt on the exact union passes, mesh the union grown by a fraction of the shell voxel: it closes
    # sub-voxel gaps, so the shell stays a single simple surface, <= 1.2 voxel (~0.5-1 pt) proud of the item.
    for off in (0.0, 0.5, 0.8, 1.2):
        Fld = U if off == 0.0 else U.offset(off * vx)
        v0, f0 = mc_mesh(Fld, vx)
        f0, _ = drop_crumbs(v0, f0, min_frac=0.01)
        v0, f0 = compact(v0, f0)
        if off:
            # grid-aligned flat MC faces stall the quadric decimator (6k tris for a 600 target): a tiny
            # deterministic jitter (2 % of a voxel) lets it collapse them; the projection below undoes it
            v0 = v0 + np.random.default_rng(7).normal(0.0, 0.02 * vx, v0.shape)
        for tgt, agg in [(target, 5), (int(target * 1.1), 5), (target, 3), (int(target * 1.25), 7), (int(target * 1.5), 3)]:
            attempt_no += 1
            if tgt < len(f0):
                v, f = fast_simplification.simplify(v0, f0.astype(np.int32), target_count=tgt, agg=agg)
            else:
                v, f = v0, f0
            v = np.asarray(v, np.float64); f = np.asarray(f, np.int64)
            # quadric collapses sometimes fold a sliver into two coincident triangles (a "fin" that makes
            # 2 non-manifold edges): drop every triangle whose vertex set occurs more than once
            key = np.sort(f, 1)
            _, inv, cnt = np.unique(key, axis=0, return_inverse=True, return_counts=True)
            f = f[cnt[inv.ravel()] == 1]
            v, f = compact(v, f)
            v = _project(Fld, v, eps=0.5 * vx, iters=4)
            v, f = _orient_outward(v, f)
            b, nm = edge_stats(f)
            if b or nm or _pinched_vertices(f):
                v, f = _repair_shell(v, f, Fld, vx)
                v, f = _orient_outward(v, f)
                b, nm = edge_stats(f)
            degen = int((tri_areas(v, f) < 1e-12).sum())
            dup = len(f) - len(np.unique(np.sort(f, 1), axis=0))
            de = np.r_[f[:, [0, 1]], f[:, [1, 2]], f[:, [2, 0]]]
            winding_ok = len(np.unique(de, axis=0)) == len(de)
            pinched = _pinched_vertices(f)
            ok = b == 0 and nm == 0 and degen == 0 and dup == 0 and winding_ok and pinched == 0
            if off and len(f) > 2 * target:  # a stalled fallback shell is too heavy for the outline pass
                ok = False
            nc = n_components(len(v), f) if ok else 99
            # rank: ok first, then fewest components (a repair may split a sub-voxel bridge), then the first found
            cand = (ok, v, f, b, nm, degen, dup, attempt_no - 1, winding_ok, pinched, off, Fld, len(f0), nc)
            if best is None or (ok and not best[0]) or (ok and nc < best[13]):
                best = cand
            if ok and nc == 1:
                break
        if best[0] and best[13] == 1:
            break
    ok, v, f, b, nm, degen, dup, attempt, winding_ok, pinched, off, Fld, n_mc, _nc = best
    f0 = np.zeros((n_mc, 3))  # for the log line
    n = _normals(Fld, v, eps=0.5 * vx)
    ncomp = n_components(len(v), f)
    cen = v[f].mean(1)
    dev = np.abs(U(cen.astype(F))).astype(float) * scale  # chord error at face centres, board units
    euler = len(v) - len(np.unique(np.sort(np.r_[f[:, [0, 1]], f[:, [1, 2]], f[:, [2, 0]]], 1), axis=0)) + len(f)
    stats = dict(tris=int(len(f)), verts=int(len(v)), target=target, voxel_authoring=round(vx, 5),
                 closed=bool(b == 0), manifold=bool(nm == 0), boundary_edges=b, nonmanifold_edges=nm,
                 degenerate_tris=degen, duplicate_tris=int(dup), winding_consistent=bool(winding_ok),
                 pinched_vertices=int(pinched), components=int(ncomp), euler_characteristic=int(euler),
                 chord_error_mean_pt=round(float(dev.mean()) * PT_PER_UNIT, 3),
                 chord_error_max_pt=round(float(dev.max()) * PT_PER_UNIT, 3), attempts=attempt + 1,
                 grown_authoring=round(off * vx, 5), grown_pt=round(off * vx * scale * PT_PER_UNIT, 3))
    log(f"  {'outline':14s} mc {len(f0):7d} -> {len(f):5d} tris (target {target}, closed {stats['closed']}, "
        f"manifold {stats['manifold']}, {ncomp} comp, chord err mean {stats['chord_error_mean_pt']} pt"
        + (f", grown {stats['grown_pt']} pt" if off else "") + ")")
    return dict(v=(v - com) * scale, f=f, n=n, stats=stats)


def _pinched_list(f):
    """Ids of vertices whose incident triangles form more than one fan."""
    from collections import defaultdict
    inc = defaultdict(list)
    for a, b, c in f:
        inc[a].append((b, c)); inc[b].append((c, a)); inc[c].append((a, b))
    out = []
    for vtx, opp in inc.items():
        parent = {}

        def find(x):
            while parent.setdefault(x, x) != x:
                x = parent[x]
            return x
        for a, b in opp:
            parent[find(a)] = find(b)
        if len({find(a) for a, _ in opp}) > 1:
            out.append(vtx)
    return out


def _repair_shell(v, f, fld, vx, iters=6):
    """Local repair of a decimated outline shell (art-director fix 2026-09-24): quadric collapses on thin
    features leave a few non-manifold edges / pinched vertices (monster_truck, fragile harp/camera shells).
    Cut every triangle touching one out, then close each resulting hole with a fan around its centroid
    projected onto the field. Repeats until the shell is closed + manifold or `iters` runs out."""
    v = np.asarray(v, np.float64).copy(); f = np.asarray(f, np.int64).copy()
    for _ in range(iters):
        e = np.sort(np.r_[f[:, [0, 1]], f[:, [1, 2]], f[:, [2, 0]]], axis=1)
        ue, inv, cnt = np.unique(e, axis=0, return_inverse=True, return_counts=True)
        nm_face = (cnt[inv.ravel()] > 2).reshape(3, -1).T.any(1)
        pin = _pinched_list(f)
        bad = nm_face | np.isin(f, pin).any(1)
        # boundary vertices with more than one outgoing boundary edge make loops ambiguous: cut around them too
        d = np.r_[f[:, [0, 1]], f[:, [1, 2]], f[:, [2, 0]]]
        dset = set(map(tuple, d))
        bnd = [tuple(x) for x in d if (x[1], x[0]) not in dset]
        outdeg = {}
        for a, b in bnd:
            outdeg[a] = outdeg.get(a, 0) + 1
        multi = [a for a, k in outdeg.items() if k > 1]
        if multi:
            bad |= np.isin(f, multi).any(1)
        if not bad.any() and not bnd:
            break
        f = f[~bad]
        d = np.r_[f[:, [0, 1]], f[:, [1, 2]], f[:, [2, 0]]]
        dset = set(map(tuple, d))
        nxt = {}
        ambiguous = False
        for a, b in d:
            if (b, a) not in dset:
                if a in nxt:
                    ambiguous = True
                nxt[a] = b
        if ambiguous:
            continue  # the next round cuts around the ambiguous vertex
        seen = set()
        new_f = []
        for s in list(nxt):
            if s in seen:
                continue
            loop = [s]; seen.add(s); cur = nxt[s]
            while cur != s and cur in nxt and cur not in seen:
                loop.append(cur); seen.add(cur); cur = nxt[cur]
            if cur != s or len(loop) < 3:
                continue
            if len(loop) == 3:  # a triangular hole: one reversed triangle, no centroid (avoids a sliver fan)
                new_f.append((loop[2], loop[1], loop[0]))
                continue
            c = v[loop].mean(0)
            c = _project(fld, c[None], eps=0.5 * vx, iters=4)[0]
            ci = len(v); v = np.vstack([v, c[None]])
            for i, a in enumerate(loop):
                b = loop[(i + 1) % len(loop)]
                new_f.append((b, a, ci))
        if new_f:
            f = np.vstack([f, np.array(new_f, np.int64)])
        v, f = compact(v, f)
    return v, f


def _pinched_vertices(f):
    """Vertices whose incident triangles form more than one fan (two sheets touching at a point)."""
    from collections import defaultdict
    inc = defaultdict(list)
    for t, (a, b, c) in enumerate(f):
        inc[a].append((b, c)); inc[b].append((c, a)); inc[c].append((a, b))
    bad = 0
    for vtx, opp in inc.items():
        # union-find over the ring edges: triangles sharing an opposite vertex are in one fan
        parent = {}

        def find(x):
            while parent.setdefault(x, x) != x:
                x = parent[x]
            return x
        for a, b in opp:
            parent[find(a)] = find(b)
        if len({find(a) for a, _ in opp}) > 1:
            bad += 1
    return bad


# --------------------------------------------------------------------------- tray / goal-card pose

PT_PER_UNIT = 200.0 / 3.0  # board: 1 unit = 200 px on the 3x capture = 66.7 pt
TRAY_NATURAL = 0.63  # tray size / board size (strawberry, research/motion.md 1.3)
TRAY_BOX_PT = (48.0, 58.0)  # big items are shrunk to fit this box (w, h) in the tray


def euler_matrix(yaw=0.0, pitch=0.0, roll=0.0):
    """R = Rz(roll) @ Rx(pitch) @ Ry(yaw) (column vectors): spin about the item's up axis first,
    then tip toward the viewer (+pitch shows the top), then roll in the picture plane."""
    a, b, c = (math.radians(x) for x in (yaw, pitch, roll))
    Ry = np.array([[math.cos(a), 0, math.sin(a)], [0, 1, 0], [-math.sin(a), 0, math.cos(a)]])
    Rx = np.array([[1, 0, 0], [0, math.cos(b), -math.sin(b)], [0, math.sin(b), math.cos(b)]])
    Rz = np.array([[math.cos(c), -math.sin(c), 0], [math.sin(c), math.cos(c), 0], [0, 0, 1]])
    return Rz @ Rx @ Ry


def tray_info(item: Item, verts):
    """Tray + goal-card data: the pose that stands the item upright facing the camera (+Z) with its
    bottom-centre at the origin, and the per-item tray scale (natural 0.63x of the board size, capped
    to the 48 x 58 pt tray box)."""
    from scipy.spatial.transform import Rotation
    yaw, pitch, roll = item.tray_view if item.tray_view is not None else (item.icon_view[0], 0.0, 0.0)
    R = euler_matrix(yaw, pitch, roll)
    q = np.asarray(verts) @ R.T
    lo, hi = q.min(0), q.max(0)
    w, h, d = (hi - lo).tolist()
    fit_w = TRAY_BOX_PT[0] / (w * PT_PER_UNIT)
    fit_h = TRAY_BOX_PT[1] / (h * PT_PER_UNIT)
    if item.tray_scale is not None:
        s, why = float(item.tray_scale), "override"
    else:
        s = min(TRAY_NATURAL, fit_w, fit_h)
        why = "natural" if s == TRAY_NATURAL else ("width" if fit_w <= fit_h else "height")
    t = -np.array([(lo[0] + hi[0]) / 2, lo[1], (lo[2] + hi[2]) / 2])
    M = np.eye(4); M[:3, :3] = R; M[:3, 3] = t
    quat = Rotation.from_matrix(R).as_quat()  # x, y, z, w
    ppu = s * PT_PER_UNIT
    return dict(
        tray_pose=dict(view_deg=[float(yaw), float(pitch), float(roll)], quat_xyzw=np.round(quat, 6).tolist(),
                       matrix=M.round(5).tolist(), rotation=R.round(6).tolist(),
                       note="model -> tray frame (+Y up, +Z toward the camera), bottom-centre at the origin, model units; "
                            "the engine adds the shelf tilt and the scale"),
        tray_scale=round(s, 4),
        tray_fit=dict(pt_per_unit=round(ppu, 3), size_pt=[round(w * ppu, 1), round(h * ppu, 1)], box_pt=list(TRAY_BOX_PT),
                      natural=TRAY_NATURAL, limited_by=why, extent_units=[round(w, 4), round(h, 4), round(d, 4)]),
        board_scale=float(item.board_scale),
    )


def part_cut(item, i):
    """(union of the other occluding parts, part i minus those occluders shrunk by 2.5 voxels)."""
    parts = item.parts
    p = parts[i]
    vx = p.voxel or item.voxel
    occ = [q.sdf for j, q in enumerate(parts) if j != i and q.occluder]
    o = union(*occ) if occ else None
    c = p.sdf.subtract(o.offset(-2.5 * vx)) if (o is not None and p.cut) else p.sdf
    return o, c


def _mc_worker(args):
    """Spawned worker: rebuild the recipe by name (SDF closures cannot be pickled) and mesh one part."""
    recipe, k, i = args
    item = load_items(recipe)[k]
    _, c = part_cut(item, i)
    p = item.parts[i]
    vx = p.voxel or item.voxel
    v, f = mc_mesh(c, vx)
    return v, f, vx


def _parallel_mc(item, cuts, voxels, recipe=None, item_index=0, workers=None):
    """Marching cubes for every part. With a recipe name, parts run in spawned worker processes
    (MF_WORKERS, default 2; MF_SERIAL=1 or MF_WORKERS=1 for serial)."""
    import multiprocessing as mp
    import os
    if workers is None:
        workers = int(os.environ.get("MF_WORKERS", "2") or 2)
    n = min(workers, len(cuts), os.cpu_count() or 1)
    if recipe is None or n <= 1 or os.environ.get("MF_SERIAL"):
        return [(*mc_mesh(c, vx), vx) for c, vx in zip(cuts, voxels)]
    with mp.get_context("spawn").Pool(n) as pool:
        return pool.map(_mc_worker, [(recipe, item_index, i) for i in range(len(cuts))], chunksize=1)


def _project(sdf, v, eps, iters=3):
    p = v.astype(F).copy()
    for _ in range(iters):
        d = sdf(p)
        g = gradient(sdf, p, eps)
        gn = np.sum(g * g, 1)
        step = (d / np.maximum(gn, F(1e-8)))[:, None] * g
        # never move more than 2 voxels (protects thin features)
        m = np.linalg.norm(step, axis=1, keepdims=True)
        step *= np.minimum(1, (4 * eps) / np.maximum(m, 1e-9))
        p -= step
    return p.astype(np.float64)


def _normals(sdf, v, eps):
    g = gradient(sdf, v.astype(F), eps).astype(np.float64)
    n = np.linalg.norm(g, axis=1, keepdims=True)
    return g / np.maximum(n, 1e-9)


# --------------------------------------------------------------------------- physics helpers

def _symmetry_axis(m, tol=0.03, gap=0.05):
    """Unit axis of (near) rotational symmetry of the convex hull, or None: two principal moments equal within `tol`
    of the largest, the third at least `gap` apart (cans, drums, cups, bats, cues, balloons). Isotropic shapes (balls,
    cubes) return None, so a cube keeps its distinct faces."""
    h = m.convex_hull
    c = np.asarray(h.principal_inertia_components, float)
    V = np.asarray(h.principal_inertia_vectors, float)
    o = np.argsort(c)
    c, V = c[o], V[o]
    top = max(c[2], 1e-12)
    if (c[1] - c[0]) / top < tol and (c[2] - c[1]) / top > gap:
        a = V[2]
    elif (c[2] - c[1]) / top < tol and (c[1] - c[0]) / top > gap:
        a = V[0]
    else:
        return None
    a = a / np.linalg.norm(a)
    # equal moments are not enough (the duck has two by chance, a square prism always): the hull must also be ROUND
    # about the axis through the COM (support width within 6 % in every direction across it)
    e1 = np.cross(a, [1.0, 0, 0] if abs(a[0]) < 0.9 else [0, 1.0, 0]); e1 /= np.linalg.norm(e1)
    e2 = np.cross(a, e1)
    th = np.linspace(0, 2 * np.pi, 48, endpoint=False)
    d = np.outer(np.cos(th), e1) + np.outer(np.sin(th), e2)
    r = (np.asarray(h.vertices) @ d.T).max(0)
    if (r.max() - r.min()) / max(r.max(), 1e-9) > 0.06:
        return None
    return a


def _select_poses(m, T, prob, n=4, max_out=8, per_cluster=4):
    """[(pose index, probability)] to ship.

    Art-director round 2: the engine draws a start pose by probability from the shipped list (Spawner.drawPose), and the
    list used to be the 4 most probable hull facets. A can or drum lying on its side rests on ~60-110 thin facets of
    ~0.01-0.03 each (together 0.5-0.75), so the top 4 were the two END faces (0.12-0.24 each) plus two side facets and
    ~80 % of the cans/drums spawned standing, where the captures show most lying (L13 drums, L14 cans, L16 stacking rings).
    For a hull with a symmetry axis the facets are grouped by (COM height, up . axis): every roll of a lying can is one
    group. A group's probability is its sum; an end group ships one pose (yaw is random anyway), a lying/tilted group
    ships up to `per_cluster` poses spread round the axis (labels and prints show different sides) sharing the sum.
    Items without a symmetry axis keep the plain top-n facets (unchanged)."""
    order = [int(i) for i in np.argsort(-prob)]
    a = _symmetry_axis(m)
    if a is None:
        return [(i, float(prob[i])) for i in order[:n]]
    L = float(np.max(m.extents)) or 1.0
    z = np.array([0.0, 0.0, 1.0])
    ups = [T[i][:3, :3].T @ z for i in range(len(prob))]      # item-frame direction that points up in pose i
    groups = {}
    for i in order:
        key = (int(round(T[i][2, 3] / L * 40)), int(round(float(ups[i] @ a) * 8)))
        groups.setdefault(key, []).append(i)
    ranked = sorted(groups.values(), key=lambda g: -sum(prob[j] for j in g))
    e1 = np.cross(a, [1.0, 0, 0] if abs(a[0]) < 0.9 else [0, 1.0, 0]); e1 /= np.linalg.norm(e1)
    e2 = np.cross(a, e1)
    out = []
    for g in ranked[:n]:
        tot = float(sum(prob[j] for j in g))
        if tot < 0.01:
            break
        if abs(float(ups[g[0]] @ a)) > 0.95 or len(g) == 1:
            out.append((g[0], tot))
            continue
        k = min(per_cluster if not out else 2, len(g))
        phi = {j: math.atan2(float(ups[j] @ e2), float(ups[j] @ e1)) for j in g}
        chosen = []
        for t in range(k):
            target = phi[g[0]] + 2 * math.pi * t / k
            cand = [j for j in g if j not in chosen]
            chosen.append(min(cand, key=lambda j: abs(math.remainder(phi[j] - target, 2 * math.pi))))
        out += [(j, tot / k) for j in chosen]
    out.sort(key=lambda x: -x[1])
    return out[:max_out]


def stable_poses(union_v, union_f, n=4):
    """Resting poses the engine draws from (4x4 world transforms, item COM at origin before transform), with their
    probabilities: the n most probable hull facets, or for symmetric items the n most probable facet GROUPS
    (see _select_poses)."""
    import trimesh
    m = trimesh.Trimesh(union_v, union_f, process=True)
    try:
        T, prob = trimesh.poses.compute_stable_poses(m, center_mass=np.zeros(3), sigma=0.0, n_samples=1, threshold=0.0)
    except Exception:
        return []
    try:
        sel = _select_poses(m, T, prob, n)
    except Exception:
        sel = [(int(i), float(prob[i])) for i in np.argsort(-prob)[:n]]
    res = []
    for i, p in sel:
        # trimesh gives transforms that put the mesh on the XY plane with +Z up; convert to Y-up
        Zup_to_Yup = np.array([[1, 0, 0, 0], [0, 0, 1, 0], [0, -1, 0, 0], [0, 0, 0, 1]], float)
        M = Zup_to_Yup @ T[i]
        res.append(dict(probability=round(float(p), 3), matrix=M.round(5).tolist()))
    return res


def convex_hulls(meshes, max_points=48):
    from scipy.spatial import ConvexHull
    hulls = []
    for pm in meshes:
        if not pm.part.collide or len(pm.v) < 4:
            continue
        try:
            h = ConvexHull(pm.v)
            pts = pm.v[h.vertices]
        except Exception:
            continue
        if len(pts) > max_points:
            # farthest point sampling keeps the silhouette
            sel = [int(np.argmax(np.linalg.norm(pts - pts.mean(0), axis=1)))]
            d = np.linalg.norm(pts - pts[sel[0]], axis=1)
            while len(sel) < max_points:
                k = int(np.argmax(d)); sel.append(k)
                d = np.minimum(d, np.linalg.norm(pts - pts[k], axis=1))
            pts = pts[sel]
        hulls.append(dict(part=pm.part.name, points=pts.round(4).tolist()))
    return hulls
