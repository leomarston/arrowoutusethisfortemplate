"""Scene lane kit: 3D sprites for the scene illustrations (home lab, loading, Claw, Sky Jump, Rocket Race, podium).

Not a recipe (no ASSETS table, so ui3d.py / art_batch.py never index it). The scene recipes (`scene_home.py`,
`scene_events.py`, ...) define MODELS (fn() -> (parts, voxel)) and a build function per manifest id; the driver
`scene_make.py` renders them.

Why a kit instead of ui3d.render_case: a scene is COMPOSED -- many 3D objects rendered with one light rig, fitted into
measured screen boxes (pt) over painted 2D structure (walls, floor, sky), with 2D contact shadows between them. ui3d's
per-case fit/crop and its per-recipe mesh cache (any edit re-meshes every model of the recipe) do not fit that loop, so
this kit caches meshes PER MODEL (hash of the model function + every module-level function / constant it references,
recursively) and renders batches of sprites in one mfrender job. It uses the pipeline read-only: ui3d.scene_job /
run_job (camera, rig, IBL, holdout mattes), mesher (marching cubes, UVs), usdwriter.

All captures are LOOKED AT only: shapes are written by hand from measured pt boxes, colours are chosen hex values.
"""
from __future__ import annotations

import hashlib
import inspect
import json
import math
import os
import sys
import time
import types

HERE = os.path.dirname(os.path.abspath(__file__))       # art/ui/recipes
UI = os.path.dirname(HERE)
ART = os.path.dirname(UI)
APP = os.path.dirname(ART)
TOOLS = os.path.join(UI, "tools")
PIPE = os.path.join(ART, "pipeline")
for _p in (TOOLS, PIPE, HERE):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import numpy as np  # noqa: E402
from PIL import Image  # noqa: E402

import uikit  # noqa: E402,F401
import ui3d  # noqa: E402
from uikit import (Material, Part, extrude, gloss, glass, mat, metal, rbox, rot_x, rot_y, rot_z, satin,  # noqa: E402,F401
                   arc2, intersect2, glyph2, heart2, poly_mask, raster_sdf2)
from sdf import (F, SDF, SDF2, box, capped_cone, capsule, capsule2, circle2, cylinder, ellipsoid, fillet_points,  # noqa: E402,F401
                 path_tube, polygon2, rect2, revolve, round_cone, rounded_polygon2, sphere, spline_profile, star2,
                 torus, union)
from mesher import PartMesh, _normals, _project, compute_uv, mc_mesh  # noqa: E402
from usdwriter import write_usdz  # noqa: E402
import fast_simplification  # noqa: E402

BUILD = os.path.join(APP, "build", "ui-art", "scene")
USDZ = os.path.join(BUILD, "usdz")
RAW = os.path.join(BUILD, "raw")
PARTS = os.path.join(BUILD, "parts")
OUT = os.path.join(ART, "out")
for _d in (USDZ, RAW, PARTS):
    os.makedirs(_d, exist_ok=True)

SW, SH = 393, 852          # the phone screen in pt
PX = 3                     # px per pt (@3x)


# ------------------------------------------------------------------ colour helpers

def rgb(h):
    h = h.lstrip("#")
    return np.array([int(h[i:i + 2], 16) for i in (0, 2, 4)], np.float64) / 255.0


def hexs(c):
    c = np.clip(np.asarray(c, float), 0, 1)
    return "#%02X%02X%02X" % tuple(int(round(v * 255)) for v in c[:3])


def mix(a, b, t):
    return hexs(rgb(a) * (1 - t) + rgb(b) * t)


# ------------------------------------------------------------------ per-model mesh cache

def _walk(obj, h, seen, depth=0):
    """Hash a model function by its source and everything it references (functions, simple constants), recursively,
    so editing one model re-meshes only that model (plus the models sharing an edited helper)."""
    if depth > 40 or id(obj) in seen:
        return
    seen.add(id(obj))
    if isinstance(obj, types.FunctionType):
        try:
            h.update(inspect.getsource(obj).encode())
        except (OSError, TypeError):
            h.update(obj.__code__.co_code)
        for d in (obj.__defaults__ or ()):
            _walk(d, h, seen, depth + 1)
        for cell in (obj.__closure__ or ()):
            try:
                _walk(cell.cell_contents, h, seen, depth + 1)
            except ValueError:
                pass
        names = set()

        def co_names(co):
            names.update(co.co_names)
            for c in co.co_consts:
                if isinstance(c, types.CodeType):
                    co_names(c)
        co_names(obj.__code__)
        g = obj.__globals__
        for n in sorted(names):
            if n in g:
                _walk(g[n], h, seen, depth + 1)
    elif isinstance(obj, (int, float, str, bool, type(None))):
        h.update(repr(obj).encode())
    elif isinstance(obj, (tuple, list)):
        h.update(b"[")
        for v in obj:
            _walk(v, h, seen, depth + 1)
        h.update(b"]")
    elif isinstance(obj, dict):
        h.update(b"{")
        for k in sorted(obj, key=repr):
            h.update(repr(k).encode())
            _walk(obj[k], h, seen, depth + 1)
        h.update(b"}")
    # modules, classes, numpy arrays referenced by name: library code, not part of the model's identity


def model_hash(fn):
    h = hashlib.sha1()
    _walk(fn, h, set())
    return h.hexdigest()[:14]


def mesh_parts(parts, voxel, log=print, tri_div=4, min_tris=2000):
    """ui3d.mesh_parts + PREMESHED parts (Part.__dict__['premesh'] -> (v, f, n, uv)) for analytic surfaces."""
    out = []
    for p in parts:
        t0 = time.time()
        pre = p.__dict__.get("premesh")
        if pre is not None:
            v, f, n, uv = pre()
            out.append(PartMesh(p, np.asarray(v, np.float64), np.asarray(f, np.int64), np.asarray(n, np.float64),
                                None if uv is None else np.asarray(uv, np.float64), dict(tris=int(len(f)))))
            log(f"    {p.name:18s} {len(f):7d} tris  premeshed ({time.time() - t0:.1f}s)")
            continue
        vx = p.voxel or voxel
        v, f = mc_mesh(p.sdf, vx)
        target = max(min(len(f), p.min_tris if p.min_tris > 200 else min_tris), len(f) // tri_div)
        if target < len(f):
            v2, f2 = fast_simplification.simplify(v, f.astype(np.int32), target_count=target, agg=5)
            v, f = np.asarray(v2, np.float64), np.asarray(f2, np.int64)
        v = _project(p.sdf, v, eps=0.5 * vx)
        n = _normals(p.sdf, v, eps=0.5 * vx)
        uv = None
        if p.uv is not None:
            v, f, uv, remap = compute_uv(v, f, p.uv)
            n = n[remap]
        out.append(PartMesh(p, v, f, n, uv, dict(tris=int(len(f)))))
        log(f"    {p.name:18s} {len(f):7d} tris  ({time.time() - t0:.1f}s)")
    return out


def model_usdz(mod, name, force=False, log=print):
    """build/ui-art/scene/usdz/<module>/<model>.usdz, re-meshed only when the model's own code changes."""
    fn = mod.MODELS[name]
    d = os.path.join(USDZ, mod.__name__.split(".")[-1])
    os.makedirs(d, exist_ok=True)
    path = os.path.join(d, f"{name}.usdz")
    stamp = path + ".hash"
    h = model_hash(fn)
    if not force and os.path.exists(path) and os.path.exists(stamp) and open(stamp).read() == h:
        return path, json.load(open(path + ".json"))
    log(f"  meshing {name}")
    res = fn()
    parts, voxel = res if isinstance(res, tuple) else (res, 0.01)
    meshes = mesh_parts(parts, voxel, log=log)
    allv = np.vstack([m.v for m in meshes])
    meta = dict(bbox_min=allv.min(0).tolist(), bbox_max=allv.max(0).tolist(), tris=int(sum(len(m.f) for m in meshes)))
    tmp = path + f".tmp{os.getpid()}.usdz"
    write_usdz(name, meshes, tmp, log=lambda *a: None)
    os.replace(tmp, path)
    json.dump(meta, open(path + ".json", "w"))
    open(stamp, "w").write(h)
    return path, meta


# ------------------------------------------------------------------ analytic (premeshed) surfaces

def grid_part(name, material, fn_uv, nu, nv, uv_scale=(1.0, 1.0), flip=False, uv_fn=None):
    """A Part whose mesh is the parametric surface fn_uv(u, v) -> (..., 3) over [0,1]^2 (nu x nv quads), vertex
    normals from the grid (cross of the partial derivatives), texture coordinates = (u, v) * uv_scale, or
    uv_fn(points (N, 3)) -> (N, 2) (e.g. a top-down planar map)."""
    def premesh():
        u, v = np.meshgrid(np.linspace(0, 1, nu + 1), np.linspace(0, 1, nv + 1))
        P = np.asarray(fn_uv(u, v), float)                  # (nv+1, nu+1, 3)
        du = np.gradient(P, axis=1)
        dv = np.gradient(P, axis=0)
        n = np.cross(du, dv)
        if flip:
            n = -n
        n /= np.maximum(np.linalg.norm(n, axis=-1, keepdims=True), 1e-12)
        idx = np.arange((nu + 1) * (nv + 1)).reshape(nv + 1, nu + 1)
        a, b, c, d = idx[:-1, :-1], idx[:-1, 1:], idx[1:, 1:], idx[1:, :-1]
        if flip:
            f = np.concatenate([np.stack([a, c, b], -1).reshape(-1, 3), np.stack([a, d, c], -1).reshape(-1, 3)])
        else:
            f = np.concatenate([np.stack([a, b, c], -1).reshape(-1, 3), np.stack([a, c, d], -1).reshape(-1, 3)])
        uv = np.stack([u.reshape(-1) * uv_scale[0], v.reshape(-1) * uv_scale[1]], 1)
        if uv_fn is not None:
            uv = np.asarray(uv_fn(P.reshape(-1, 3)), float)
        return P.reshape(-1, 3), f, n.reshape(-1, 3), uv
    p = Part(name, sphere(1.0), material)
    p.__dict__["premesh"] = premesh
    return p


def lathe_part(name, material, prof, n_seg=256, samples=160, squash=1.0, uv_fn=None, center=(0, 0, 0)):
    """A surface of revolution about +Y from a profile polyline [(r, y), ...] listed from the axis at the BOTTOM to
    the axis at the TOP (outward normals), resampled smoothly (Catmull-Rom); `squash` scales z (elliptical plan)."""
    P = np.asarray(prof, float)
    P2 = np.vstack([P[0], P, P[-1]])
    pts = []
    for i in range(1, len(P2) - 2):
        p0, p1, p2, p3 = P2[i - 1], P2[i], P2[i + 1], P2[i + 2]
        for t in np.linspace(0, 1, max(2, samples // (len(P) - 1)), endpoint=False):
            t2, t3 = t * t, t * t * t
            pts.append(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t2 + (-p0 + 3 * p1 - 3 * p2 + p3) * t3))
    pts.append(P[-1])
    pts = np.array(pts)
    pts[:, 0] = np.maximum(pts[:, 0], 0)
    L = np.concatenate([[0], np.cumsum(np.linalg.norm(np.diff(pts, axis=0), axis=1))])
    L /= L[-1]
    c = np.asarray(center, float)

    def fn(u, v):
        r = np.interp(v, L, pts[:, 0])
        y = np.interp(v, L, pts[:, 1])
        a = u * 2 * math.pi
        return np.stack([c[0] + r * np.cos(a), c[1] + y, c[2] - r * np.sin(a) * squash], -1)
    return grid_part(name, material, fn, n_seg, len(pts) * 2, uv_fn=uv_fn, flip=False)


def planar_uv(x0, z0, size):
    """Top-down planar texture map over the square [x0, x0+size] x [z0, z0+size] (u = x, v = z)."""
    def f(P):
        return np.stack([(P[:, 0] - x0) / size, (P[:, 2] - z0) / size], 1)
    return f


# ------------------------------------------------------------------ lighting

def scene_env(name="lab", sky=(0.86, 0.88, 1.0), hor=(0.62, 0.62, 0.86), gnd=(0.42, 0.40, 0.62),
              boxes=(((-0.35, 0.75, 0.55), (0.55, 0.55, 0.60), 0.75), ((0.75, 0.25, -0.60), (0.30, 0.34, 0.46), 0.85))):
    """A tinted studio dome (equirect PNG) for the IBL: the lab's reflections are lilac-blue, not neutral grey."""
    p = os.path.join(BUILD, f"env_{name}.png")
    key = repr((sky, hor, gnd, boxes))
    if os.path.exists(p) and os.path.exists(p + ".key") and open(p + ".key").read() == key:
        return p
    W, H = 512, 256
    u, v = np.meshgrid((np.arange(W) + 0.5) / W, (np.arange(H) + 0.5) / H)
    phi = (u - 0.5) * 2 * math.pi
    theta = v * math.pi
    d = np.stack([np.sin(theta) * np.sin(phi), np.cos(theta), -np.sin(theta) * np.cos(phi)], -1)
    t = np.clip(d[..., 1], -1, 1)
    sky, hor, gnd = (np.asarray(x, float) for x in (sky, hor, gnd))
    col = np.where(t[..., None] > 0, hor + (sky - hor) * np.sqrt(np.clip(t, 0, 1))[..., None],
                   hor + (gnd - hor) * np.clip(-t * 2.5, 0, 1)[..., None])
    for k, amp, width in boxes:
        kk = np.asarray(k, float); kk /= np.linalg.norm(kk)
        col = col + np.clip((d @ kk - width) / (1 - width), 0, 1)[..., None] ** 1.3 * np.asarray(amp, float)
    Image.fromarray((np.clip(col, 0, 1) * 255).astype(np.uint8)).save(p)
    open(p + ".key", "w").write(key)
    return p


# The scene rig: a soft key from the upper left front (the reference props are lit from the top-front, highlights
# upper left), a cool rim from the right back, a lilac bounce from below, a lilac-blue dome.
LAB = dict(key_dir=(0.45, -0.70, -0.55), key_lux=2300.0, key_color=(1.0, 0.98, 0.95),
           rim_dir=(-0.75, -0.2, 0.62), rim_lux=900.0, rim_color=(0.85, 0.9, 1.0),
           fill_dir=(0.1, 0.85, -0.5), fill_lux=700.0, fill_color=(0.86, 0.86, 1.0),
           ibl_exp=-0.8, shadow=True)


def rig(base=None, env=None, **kw):
    r = dict(base or LAB)
    r.update(kw)
    r["env"] = env or r.get("env") or scene_env()
    return r


# ------------------------------------------------------------------ sprite rendering

def _look(yaw, pitch, roll=0.0):
    return rot_z(roll) @ rot_x(pitch) @ rot_y(yaw)


def _pose_matrix(meta, pose):
    c = (np.array(meta["bbox_min"]) + np.array(meta["bbox_max"])) / 2
    R = _look(pose.get("yaw", 0), pose.get("pitch", 0), pose.get("roll", 0))
    if "R" in pose:
        R = np.asarray(pose["R"]) @ R
    s = pose.get("scale", 1.0)
    pos = np.asarray(pose.get("pos", (0, 0, 0)), float)
    t = pos - (R @ c) * s if pose.get("center", True) else pos
    return ui3d.mat4(R, t, s)


def sprite_job(spec, raw):
    """spec: dict(scene=[(mod, model, pose)], view=(yaw, pitch) scene orbit, fov, light, px (long side of the raw
    render), bounds (fixed world framing), margin, holdout=[(mod, model, pose)]). Returns (jobs, camera info)."""
    items, metas = [], []
    Rv = ui3d.mat4(_look(*spec.get("view", (0, 0))))
    for group, hold in ((spec["scene"], False), (spec.get("holdout", []), True)):
        for mod, model, pose in group:
            u, meta = model_usdz(mod, model)
            M = Rv @ _pose_matrix(meta, pose)
            items.append((u, M, hold))
            if not hold:
                metas.append((meta, M))
    lo, hi = ui3d.posed_bounds(metas)
    if spec.get("bounds") is not None:
        lo, hi = (np.asarray(b, float) for b in spec["bounds"])
    ext = hi - lo
    long_px = spec.get("px", 1600)
    asp = spec.get("aspect") or max(ext[0], 1e-3) / max(ext[1], 1e-3)
    W, H = (long_px, long_px / asp) if asp >= 1 else (long_px * asp, long_px)
    W, H = int(max(64, round(W))), int(max(64, round(H)))
    light = spec.get("light") or rig()
    vis = [(u, M) for u, M, h in items if not h]
    job = ui3d.scene_job(raw, W, H, vis, (lo, hi), fov=spec.get("fov", 18.0), light=light,
                         background=spec.get("background", (0, 0, 0, 0)), margin=spec.get("margin", 1.04))
    if spec.get("floor"):
        job["floor"] = spec["floor"]
    jobs = [job]
    if len(vis) < len(items):
        mj = ui3d.scene_job(raw[:-4] + "_matte.png", W, H, [(u, M) for u, M, _ in items], (lo, hi),
                            fov=spec.get("fov", 18.0), light=light, background=(0, 0, 0, 1), margin=spec.get("margin", 1.04))
        for d, it in zip(mj["items"], items):
            d["unlit"] = [0.0, 0.0, 0.0] if it[2] else [1.0, 1.0, 1.0]
        jobs.append(mj)
    return jobs, dict(camera=job["camera"], W=W, H=H, bounds=(lo.tolist(), hi.tolist()))


def scene_bounds(spec):
    """The posed world bounds a sprite spec frames (the same numbers sprite_job uses), without rendering."""
    Rv = ui3d.mat4(_look(*spec.get("view", (0, 0))))
    metas = []
    for mod, model, pose in spec["scene"]:
        u, meta = model_usdz(mod, model)
        metas.append((meta, Rv @ _pose_matrix(meta, pose)))
    lo, hi = ui3d.posed_bounds(metas)
    return lo.tolist(), hi.tolist()


def render_sprites(specs, tag="scene", log=print):
    """specs: {name: spec}. One mfrender job for all of them. Returns {name: RGBA PIL image (raw, uncropped)}."""
    alljobs, info = [], {}
    for name, spec in specs.items():
        raw = os.path.join(RAW, f"{name}.png")
        jobs, inf = sprite_job(spec, raw)
        info[name] = (raw, jobs, inf)
        alljobs += jobs
    t0 = time.time()
    ok = ui3d.run_job(alljobs, f"{tag}", timeout=230)
    if not ok:
        raise SystemExit("render failed")
    log(f"  rendered {len(specs)} sprite(s) in {time.time() - t0:.1f}s")
    out = {}
    for name, (raw, jobs, inf) in info.items():
        im = Image.open(raw).convert("RGBA")
        if len(jobs) > 1:
            mt = np.asarray(Image.open(jobs[1]["out"]).convert("L")).astype(np.float32) / 255
            a = np.asarray(im).copy()
            a[..., 3] = np.clip(a[..., 3].astype(np.float32) * mt, 0, 255).astype(np.uint8)
            im = Image.fromarray(a, "RGBA")
        im.info["cam"] = inf
        out[name] = im
    return out


def alpha_bbox(im, thr=3):
    a = np.asarray(im.getchannel("A"))
    ys, xs = np.nonzero(a > thr)
    if not len(xs):
        return (0, 0, im.width, im.height)
    return (int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1)


def fit_box(im, box_pt, mode="contain", align=(0.5, 0.5), crop=True):
    """Crop to the alpha bbox, scale into box_pt (x0, y0, x1, y1 in screen pt) and return (image, (x_px, y_px)) --
    the paste position in @3x px. mode: contain | width | height | stretch."""
    if crop:
        im = im.crop(alpha_bbox(im))
    x0, y0, x1, y1 = (v * PX for v in box_pt)
    bw, bh = x1 - x0, y1 - y0
    if mode == "stretch":
        nw, nh = bw, bh
    else:
        s = {"contain": min(bw / im.width, bh / im.height), "width": bw / im.width, "height": bh / im.height}[mode]
        nw, nh = im.width * s, im.height * s
    nw, nh = max(1, int(round(nw))), max(1, int(round(nh)))
    im = im.resize((nw, nh), Image.LANCZOS)
    x = x0 + (bw - nw) * align[0]
    y = y0 + (bh - nh) * align[1]
    return im, (int(round(x)), int(round(y)))


# ------------------------------------------------------------------ 2D canvas (float RGBA, premultiplied-free)

class Canvas:
    """A float RGBA canvas in @3x px of a pt frame: over() pastes sprites, paint helpers take pt coordinates."""

    def __init__(self, w_pt, h_pt, color=None):
        self.w, self.h = int(round(w_pt * PX)), int(round(h_pt * PX))
        self.a = np.zeros((self.h, self.w, 4), np.float64)
        if color is not None:
            self.a[..., :3] = rgb(color)
            self.a[..., 3] = 1.0
        yy, xx = np.mgrid[0:self.h, 0:self.w]
        self.X = (xx + 0.5) / PX       # pt
        self.Y = (yy + 0.5) / PX

    def over(self, src_rgba, alpha_mul=1.0, x=0, y=0):
        """Porter-Duff OVER of a float (h, w, 4) array or PIL image at px offset (x, y)."""
        if isinstance(src_rgba, Image.Image):
            src_rgba = np.asarray(src_rgba.convert("RGBA")).astype(np.float64) / 255
        s = src_rgba
        h, w = s.shape[:2]
        x0, y0 = max(0, x), max(0, y)
        x1, y1 = min(self.w, x + w), min(self.h, y + h)
        if x1 <= x0 or y1 <= y0:
            return
        ss = s[y0 - y:y1 - y, x0 - x:x1 - x]
        d = self.a[y0:y1, x0:x1]
        sa = ss[..., 3:4] * alpha_mul
        da = d[..., 3:4]
        oa = sa + da * (1 - sa)
        oc = (ss[..., :3] * sa + d[..., :3] * da * (1 - sa)) / np.maximum(oa, 1e-9)
        d[..., :3] = oc
        d[..., 3:4] = oa

    def fill(self, cov, color, alpha=1.0):
        """Paint `color` (hex or (h, w, 3) array) with coverage `cov` (h, w) in [0, 1]."""
        col = rgb(color) if isinstance(color, str) else np.asarray(color, float)
        src = np.zeros((self.h, self.w, 4))
        src[..., :3] = col
        src[..., 3] = np.clip(cov, 0, 1) * alpha
        self.over(src)

    def multiply(self, cov, color, strength=1.0):
        """Darken/tint the existing colour: c = c * lerp(1, color, cov*strength) (alpha unchanged)."""
        col = rgb(color) if isinstance(color, str) else np.asarray(color, float)
        k = (np.clip(cov, 0, 1) * strength)[..., None]
        self.a[..., :3] = self.a[..., :3] * (1 - k + k * col)

    def screen(self, cov, color, strength=1.0):
        col = rgb(color) if isinstance(color, str) else np.asarray(color, float)
        k = (np.clip(cov, 0, 1) * strength)[..., None]
        self.a[..., :3] = 1 - (1 - self.a[..., :3]) * (1 - k * col)

    def image(self):
        return Image.fromarray((np.clip(self.a, 0, 1) * 255 + 0.5).astype(np.uint8), "RGBA")

    def save(self, path):
        im = self.image()
        tmp = path + f".tmp{os.getpid()}.png"
        im.save(tmp, optimize=True)
        os.replace(tmp, path)
        return path


# coverage helpers (antialiased by ~1 px; all coordinates in pt)
def aa(d_pt, soft_pt=0.34):
    """Signed distance (pt, < 0 inside) -> coverage."""
    return np.clip(0.5 - d_pt / max(soft_pt, 1e-6), 0, 1)


def d_ellipse(X, Y, cx, cy, rx, ry):
    q = np.sqrt(((X - cx) / rx) ** 2 + ((Y - cy) / ry) ** 2)
    return (q - 1) * min(rx, ry)


def d_rrect(X, Y, x0, y0, x1, y1, r):
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    hx, hy = (x1 - x0) / 2 - r, (y1 - y0) / 2 - r
    qx, qy = np.abs(X - cx) - hx, np.abs(Y - cy) - hy
    return np.sqrt(np.maximum(qx, 0) ** 2 + np.maximum(qy, 0) ** 2) + np.minimum(np.maximum(qx, qy), 0) - r


def smooth(a, t0, t1):
    t = np.clip((a - t0) / (t1 - t0), 0, 1)
    return t * t * (3 - 2 * t)


def blur(arr, sigma_px):
    from scipy import ndimage
    if sigma_px <= 0:
        return arr
    if arr.ndim == 3:
        return np.stack([ndimage.gaussian_filter(arr[..., i], sigma_px) for i in range(arr.shape[2])], -1)
    return ndimage.gaussian_filter(arr, sigma_px)


def noise2(h, w, scale_px, seed=0, octaves=3):
    """Smooth value noise in [-1, 1] (for subtle surface mottling)."""
    rng = np.random.default_rng(seed)
    out = np.zeros((h, w))
    amp, tot = 1.0, 0.0
    for o in range(octaves):
        s = max(2, int(scale_px / (2 ** o)))
        g = rng.standard_normal((h // s + 3, w // s + 3))
        im = Image.fromarray(((g - g.min()) / (np.ptp(g) + 1e-9) * 255).astype(np.uint8)).resize(
            ((w // s + 3) * s, (h // s + 3) * s), Image.BICUBIC)
        a = np.asarray(im).astype(np.float64)[:h, :w] / 127.5 - 1
        out += a * amp
        tot += amp
        amp *= 0.5
    return out / tot


def sprite_array(im):
    return np.asarray(im.convert("RGBA")).astype(np.float64) / 255


def shadow_of(im, dx_px, dy_px, sigma_px, opacity, color="#1A1440", grow_px=0):
    """A soft cast/contact shadow (float RGBA) from a sprite's alpha, offset and blurred, same size as the sprite plus
    a margin; returns (array, (ox, oy)) to paste at sprite position + (ox, oy)."""
    a = sprite_array(im)[..., 3]
    m = int(abs(dx_px) + abs(dy_px) + 3 * sigma_px + grow_px + 4)
    H, W = a.shape
    big = np.zeros((H + 2 * m, W + 2 * m))
    big[m:m + H, m:m + W] = a
    if grow_px:
        from scipy import ndimage
        big = ndimage.maximum_filter(big, size=int(2 * grow_px + 1))
    big = np.roll(np.roll(big, int(round(dy_px)), 0), int(round(dx_px)), 1)
    big = blur(big, sigma_px)
    out = np.zeros(big.shape + (4,))
    out[..., :3] = rgb(color)
    out[..., 3] = np.clip(big * opacity, 0, 1)
    return out, (-m, -m)


def save_png(im, path):
    tmp = path + f".tmp{os.getpid()}.png"
    im.save(tmp, optimize=True)
    os.replace(tmp, path)
    return path


def memory_ok(min_free_mb=400, wait=True, log=print):
    """The machine rule: before a render batch, free swap >= 400 MB and memory pressure normal; wait in 2 min steps."""
    import re
    import subprocess
    while True:
        sw = subprocess.run(["sysctl", "vm.swapusage"], capture_output=True, text=True).stdout
        m = re.search(r"free = ([\d.]+)M", sw)
        free = float(m.group(1)) if m else 1e9
        mp = subprocess.run(["memory_pressure", "-Q"], capture_output=True, text=True).stdout
        m2 = re.search(r"free percentage: (\d+)%", mp)
        pct = int(m2.group(1)) if m2 else 100
        if free >= min_free_mb and pct >= 20:
            return True
        log(f"  memory: swap free {free:.0f} MB, free {pct}% -> waiting 2 min")
        if not wait:
            return False
        time.sleep(120)


# ------------------------------------------------------------------ gradients for painted structure

def stops_interp(t, stops):
    """stops: [(t, hex), ...] sorted by t -> colour array (..., 3) by linear interpolation of sRGB (smoothstep between
    stops, so the bands do not show as kinks)."""
    ts = np.array([s[0] for s in stops], float)
    cs = np.array([rgb(s[1]) for s in stops])
    t = np.asarray(t, float)
    i = np.clip(np.searchsorted(ts, t) - 1, 0, len(ts) - 2)
    t0, t1 = ts[i], ts[i + 1]
    f = np.clip((t - t0) / np.maximum(t1 - t0, 1e-9), 0, 1)
    f = f * f * (3 - 2 * f)
    return cs[i] * (1 - f[..., None]) + cs[i + 1] * f[..., None]


def grade(im, gain=(1, 1, 1), lift=(0, 0, 0), gamma=1.0, sat=1.0):
    """Colour-grade OUR render (per-channel gain / lift, gamma, saturation) toward measured target tones."""
    a = np.asarray(im.convert("RGBA")).astype(np.float64) / 255
    c = a[..., :3]
    c = np.clip(c * np.asarray(gain) + np.asarray(lift), 0, 1) ** gamma
    if sat != 1.0:
        l = c @ np.array([0.2126, 0.7152, 0.0722])
        c = np.clip(l[..., None] + (c - l[..., None]) * sat, 0, 1)
    a[..., :3] = c
    return Image.fromarray((a * 255 + 0.5).astype(np.uint8), "RGBA")


# ------------------------------------------------------------------ instancing (one mesh, many copies: coins, blocks)

def instanced_part(name, material, sdf, voxel, mats, tri_div=4, min_tris=600):
    """Mesh `sdf` ONCE and replicate it under the 4x4 matrices `mats` (rotation * uniform scale + translation) into a
    single premeshed Part -- hundreds of coins cost one marching-cubes run."""
    def premesh():
        v, f = mc_mesh(sdf, voxel)
        target = max(min(len(f), min_tris), len(f) // tri_div)
        if target < len(f):
            v2, f2 = fast_simplification.simplify(v, f.astype(np.int32), target_count=target, agg=5)
            v, f = np.asarray(v2, np.float64), np.asarray(f2, np.int64)
        v = _project(sdf, v, eps=0.5 * voxel)
        n = _normals(sdf, v, eps=0.5 * voxel)
        V, Fs, N = [], [], []
        for i, M in enumerate(mats):
            M = np.asarray(M, float)
            A = M[:3, :3]
            V.append(v @ A.T + M[:3, 3])
            nn = n @ np.linalg.inv(A)
            N.append(nn / np.maximum(np.linalg.norm(nn, axis=1, keepdims=True), 1e-12))
            Fs.append(f + i * len(v))
        return np.vstack(V), np.vstack(Fs), np.vstack(N), None
    p = Part(name, sphere(1.0), material)
    p.__dict__["premesh"] = premesh
    return p


def M4(R=None, t=(0, 0, 0), s=1.0):
    M = np.eye(4)
    M[:3, :3] = (np.eye(3) if R is None else np.asarray(R, float)) * s
    M[:3, 3] = t
    return M


# ------------------------------------------------------------------ painted clouds / sky

def cloud_layer(cv, puffs, top="#FFFFFF", mid="#F9D3E3", bottom="#D6B8EA", rim="#FFFFFF", soft=1.2, alpha=1.0,
                shade_depth=26.0, seed=0):
    """Paint a cumulus bank onto Canvas `cv`: `puffs` = [(cx, cy, r) pt]. Colour by the height inside the bank
    (top -> bottom), a bright rim where each puff's upper-left edge is, pink-lilac shade in the creases between puffs."""
    X, Y = cv.X, cv.Y
    cov = np.zeros_like(X)
    lit = np.zeros_like(X)
    ys = [p[1] - p[2] for p in puffs]
    ye = [p[1] + p[2] for p in puffs]
    y0, y1 = min(ys), max(ye)
    for cx, cy, r in puffs:
        d = np.sqrt((X - cx) ** 2 + (Y - cy) ** 2) - r
        c = aa(d, soft)
        # per-puff light: brighter toward the upper-left of each puff
        l = np.clip(1 - np.sqrt(((X - (cx - 0.35 * r)) / (1.2 * r)) ** 2 + ((Y - (cy - 0.45 * r)) / (1.2 * r)) ** 2), 0, 1)
        lit = np.maximum(lit, l * c)
        cov = np.maximum(cov, c)
    t = np.clip((Y - y0) / max(y1 - y0, 1), 0, 1)
    col = stops_interp(t, [(0, top), (0.45, mid), (1.0, bottom)])
    col = col * (1 - 0.55 * lit[..., None]) + rgb(rim) * 0.55 * lit[..., None]
    # creases: where coverage is full but no puff is lit, deepen toward the bottom colour
    crease = np.clip(cov - lit * 1.3, 0, 1) * 0.35
    col = col * (1 - crease[..., None]) + rgb(bottom) * crease[..., None]
    src = np.zeros((cv.h, cv.w, 4))
    src[..., :3] = col
    src[..., 3] = cov * alpha
    cv.over(src)
