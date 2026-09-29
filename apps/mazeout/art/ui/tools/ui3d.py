#!/usr/bin/env python3
"""Mesh + render the 3D UI art (SPEC-ui §7 method "3D") to art/ui/out/<UIArt case>@3x.png.

    PY=~/.venvs/mf3d/bin/python
    $PY art/ui/tools/ui3d.py boosterVacuum coin          # UIArt cases (or recipe names = all their cases)
    $PY art/ui/tools/ui3d.py --list
    $PY art/ui/tools/ui3d.py boosterVacuum --draft       # quick low-res render to build/ui-art/draft/ (no out/ write)
    $PY art/ui/tools/ui3d.py --recipes art/pipeline/items --out art/out char_doc_home   # recipes elsewhere
    $PY art/ui/tools/ui3d.py --recipes art/pipeline/items --rig doc                     # cut-out puppet (rig.py)

Recipes live in art/ui/recipes/<name>.py (see uikit.py). They reuse art/pipeline's SDF toolbox, mesher and USD
writer read-only; USDZs and job files go to build/ui-art/ (gitignored), never to art/out/.

An ASSETS spec:
    model        name in MODELS (or `scene`: [(model, matrix-kwargs), ...] for several models / art/out items)
    yaw, pitch   deg: the model spins by yaw about +Y, then the camera looks down by pitch
    roll         deg about the view axis (applied to the model after yaw/pitch)
    frame        (w, h) in pt: the PNG is exactly w*3 x h*3 px and the art is fitted inside it
    fill         fraction of the frame the art's bbox fills (default 0.96), `align` (ax, ay) in [0,1] (default centre)
    fov          camera vertical FOV (default 18: a gentle toy perspective)
    light        rig overrides (key_dir camera space, key_lux, ibl_exp, rim_lux ...)
    post         optional fn(PIL.Image RGBA) -> Image (e.g. desaturate, glow) applied before fitting

Parts are SDF parts (marching cubes -> decimate -> reproject) or PREMESHED parts: a Part with sdf=None and a `premesh`
instance attribute, a callable -> (v, f, n, uv) taken as-is (the characters lane's fur strand cards, char_fur.fur_part;
self-test art/pipeline/examples/premesh_example.py).
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import uikit  # noqa: E402  (sets up the pipeline path)
from uikit import APP, ART, UI  # noqa: E402

import numpy as np  # noqa: E402
from PIL import Image  # noqa: E402

import fast_simplification  # noqa: E402
from mesher import PartMesh, _normals, _project, compute_uv, mc_mesh  # noqa: E402
from usdwriter import write_usdz  # noqa: E402

RECIPES = os.path.join(UI, "recipes")
if RECIPES not in sys.path:
    sys.path.insert(0, RECIPES)  # recipes may import each other's helpers (e.g. props uses boosters.hourglass_parts)
OUT = os.path.join(UI, "out")
BUILD = os.path.join(APP, "build", "ui-art")
USDZ = os.path.join(BUILD, "usdz")
RENDER = os.path.join(APP, "build", "art", "mfrender")
ITEMS = os.path.join(ART, "out")  # the game item models (read-only), for scene renders
SS = 2  # supersampling

# ------------------------------------------------------------------ the UI lighting rig
# The UI renders (booster icons, coin, crate ...) are lit brighter and glossier than the board: a warm key from the
# upper left in front, a soft ambient dome and a cool-white rim from the right-back (the right edges of the
# reference icons are light, e.g. the vacuum's right side and the crate's right planks).
RIG = dict(
    key_dir=(0.55, -0.62, -0.56),   # camera space: travels right, down and into the screen
    key_lux=3000.0,
    key_color=(1.0, 0.975, 0.94),
    rim_dir=(-0.75, -0.25, 0.60),   # from the right-back, toward the viewer's left
    rim_lux=1000.0,
    rim_color=(0.92, 0.96, 1.0),
    fill_dir=(0.2, 0.9, -0.4),      # a weak bounce from below-front, keeps undersides from going black
    fill_lux=260.0,
    fill_color=(1.0, 0.93, 0.85),
    ibl_exp=-0.95,
    shadow=True,
)


def ui_env():
    """A brighter, warmer studio dome than the board rig (build/ui-art/ui_env.png, made once)."""
    p = os.path.join(BUILD, "ui_env.png")
    if os.path.exists(p):
        return p
    os.makedirs(BUILD, exist_ok=True)
    W, H = 512, 256
    u, v = np.meshgrid((np.arange(W) + 0.5) / W, (np.arange(H) + 0.5) / H)
    phi = (u - 0.5) * 2 * math.pi
    theta = v * math.pi
    d = np.stack([np.sin(theta) * np.sin(phi), np.cos(theta), -np.sin(theta) * np.cos(phi)], -1)
    up = d[..., 1]
    sky = np.array([0.98, 0.97, 0.95]); hor = np.array([0.60, 0.62, 0.66]); gnd = np.array([0.30, 0.28, 0.27])
    t = np.clip(up, -1, 1)
    col = np.where(t[..., None] > 0, hor + (sky - hor) * np.sqrt(np.clip(t, 0, 1))[..., None],
                   hor + (gnd - hor) * np.clip(-t * 2.5, 0, 1)[..., None])
    # two soft boxes: a big warm one upper-left-front, a cool strip right-back
    for k, amp, width in (((-0.55, 0.62, 0.56), np.array([0.55, 0.52, 0.46]), 0.80),
                          ((0.75, 0.25, -0.60), np.array([0.30, 0.34, 0.40]), 0.90)):
        kk = np.asarray(k, float); kk /= np.linalg.norm(kk)
        col = col + np.clip((d @ kk - width) / (1 - width), 0, 1)[..., None] ** 1.3 * amp
    Image.fromarray((np.clip(col, 0, 1) * 255).astype(np.uint8)).save(p)
    return p


# ------------------------------------------------------------------ recipes

def _load(name):
    path = os.path.join(RECIPES, name + ".py")
    spec = importlib.util.spec_from_file_location(f"uirecipe_{name}", path)
    m = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = m
    spec.loader.exec_module(m)
    return m


def set_recipes(d):
    """Point the tool at another recipe directory (e.g. art/pipeline/items for the characters lane's char_*.py)."""
    global RECIPES
    RECIPES = os.path.abspath(d)
    if RECIPES not in sys.path:
        sys.path.insert(0, RECIPES)


def _is_recipe(path):
    """A recipe = a non-underscore module with a top-level ASSETS table (helpers such as char_kit.py / char_make.py and
    board-item recipes with build() are not UI recipes)."""
    import re
    with open(path, encoding="utf-8") as fh:
        return re.search(r"^ASSETS\b", fh.read(), re.M) is not None


def recipe_names():
    return sorted(f[:-3] for f in os.listdir(RECIPES)
                  if f.endswith(".py") and not f.startswith("_") and _is_recipe(os.path.join(RECIPES, f)))


def index():
    idx = {}
    for r in recipe_names():
        m = _load(r)
        for case in getattr(m, "ASSETS", {}):
            idx[case] = r
    return idx


def _local_deps(recipe, seen=None):
    """The recipe's own module + every module it imports (recursively) that lives in the recipe directory
    (e.g. char_doc.py -> char_kit.py), so an edit to a shared helper re-meshes its users."""
    import re
    seen = seen if seen is not None else set()
    if recipe in seen:
        return seen
    path = os.path.join(RECIPES, recipe + ".py")
    if not os.path.exists(path):
        return seen
    seen.add(recipe)
    src = open(path, encoding="utf-8").read()
    for m in re.finditer(r"^\s*(?:from\s+([A-Za-z_][\w]*)\s+import|import\s+([A-Za-z_][\w, ]*))", src, re.M):
        names = [m.group(1)] if m.group(1) else [n.strip().split(" ")[0] for n in m.group(2).split(",")]
        for n in names:
            if n and os.path.exists(os.path.join(RECIPES, n + ".py")):
                _local_deps(n, seen)
    return seen


def _src_hash(recipe):
    h = hashlib.sha1()
    for dep in sorted(_local_deps(recipe)):
        h.update(open(os.path.join(RECIPES, dep + ".py"), "rb").read())
    h.update(open(os.path.join(HERE, "uikit.py"), "rb").read())
    for extra in sorted(os.listdir(RECIPES)):
        if extra.startswith("_") and extra.endswith(".py"):
            h.update(open(os.path.join(RECIPES, extra), "rb").read())
    return h.hexdigest()[:12]


# ------------------------------------------------------------------ meshing

def premeshed(p):
    """The part's `premesh` callable, or None. A PREMESHED part (e.g. the characters lane's fur strand cards,
    char_fur.fur_part) carries `premesh() -> (v, f, n, uv)` (uv may be None) instead of an SDF; set it as an instance
    attribute (`p.__dict__["premesh"] = fn`) -- mesher.Part is a verbatim Match Factory dataclass without the field."""
    fn = getattr(p, "premesh", None)
    return fn if callable(fn) else None


def mesh_parts(parts, voxel, log=print, tri_div=5, min_tris=1500):
    """Parts -> PartMesh list, in the parts' order. SDF parts: marching cubes -> decimate to max(min_tris, tris/tri_div)
    -> project onto the surface -> SDF normals -> uv (p.uv). Premeshed parts (`premeshed(p)`) are taken as-is: no
    marching cubes, no decimation, no reprojection; their uv comes from premesh() (p.uv is ignored)."""
    out = []
    for p in parts:
        vx = p.voxel or voxel
        t0 = time.time()
        pre = premeshed(p)
        if pre is not None:
            v, f, n, uv = pre()
            f = np.asarray(f, np.int64)
            out.append(PartMesh(p, np.asarray(v, np.float64), f, np.asarray(n, np.float64),
                                None if uv is None else np.asarray(uv, np.float64), dict(tris=int(len(f)))))
            log(f"    {p.name:16s} {len(f):7d} tris  premeshed ({time.time() - t0:.1f}s)")
            continue
        if p.sdf is None:
            raise ValueError(f"part {p.name}: no SDF and no premesh callable")
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
        log(f"    {p.name:16s} {len(f):6d} tris  ({time.time() - t0:.1f}s)")
    return out


def model_usdz(recipe, mod, model, force=False, log=print):
    """build/ui-art/usdz/<recipe>/<model>.usdz, rebuilt when the recipe source changes."""
    d = os.path.join(USDZ, recipe)
    os.makedirs(d, exist_ok=True)
    path = os.path.join(d, f"{model}.usdz")
    stamp = path + ".hash"
    h = _src_hash(recipe)
    if not force and os.path.exists(path) and os.path.exists(stamp) and open(stamp).read() == h:
        return path, json.load(open(path + ".json"))
    log(f"  meshing {recipe}/{model}")
    fn = mod.MODELS[model]
    res = fn()
    parts, voxel = (res if isinstance(res, tuple) else (res, getattr(mod, "VOXEL", 0.006)))
    meshes = mesh_parts(parts, voxel, log=log)
    allv = np.vstack([m.v for m in meshes])
    meta = dict(bbox_min=allv.min(0).tolist(), bbox_max=allv.max(0).tolist(), tris=int(sum(len(m.f) for m in meshes)))
    tmp = path + f".tmp{os.getpid()}.usdz"
    write_usdz(model, meshes, tmp, log=lambda *a: None)
    os.replace(tmp, path)
    json.dump(meta, open(path + ".json", "w"))
    open(stamp, "w").write(h)
    return path, meta


# ------------------------------------------------------------------ rendering

def _look(yaw, pitch, roll=0.0):
    """Rotation applied to the model: yaw about +Y, then pitch toward the camera (tilts the top into view), roll."""
    R = uikit.rot_z(roll) @ uikit.rot_x(pitch) @ uikit.rot_y(yaw)
    return R


def mat4(R=np.eye(3), t=(0, 0, 0), s=1.0):
    M = np.eye(4)
    M[:3, :3] = np.asarray(R) * s
    M[:3, 3] = t
    return M


def scene_job(out, W, H, items, bounds, fov=18.0, light=None, background=(0, 0, 0, 0), ortho=False, margin=1.06):
    """items: [(usdz, 4x4)], bounds: (lo, hi) of the posed scene (world). Camera on +Z looking at -Z."""
    rig = dict(RIG, **(light or {}))
    lo, hi = np.asarray(bounds[0], float), np.asarray(bounds[1], float)
    c = (lo + hi) / 2
    ext = hi - lo
    aspect = W / H
    dist = 30.0
    # fit the XY extent (plus the depth's perspective growth) into the view
    half_h = max(ext[1] / 2, ext[0] / 2 / aspect) * margin + (0.02 if margin > 1 else 0.0)
    near_z = hi[2]
    fovr = 2 * math.degrees(math.atan(half_h / (dist - (near_z - c[2]))))
    if fov:  # a fixed FOV: move the camera to fit
        dist = half_h / math.tan(math.radians(fov) / 2) + (near_z - c[2])
        fovr = fov
    cam = dict(type="persp", position=[float(c[0]), float(c[1]), float(c[2] + dist)], target=[float(c[0]), float(c[1]), float(c[2])],
               up=[0, 1, 0], fov=float(fovr), near=0.1, far=dist + 60)
    lights = [dict(type="directional", direction=list(rig["key_dir"]), intensity=rig["key_lux"], color=list(rig["key_color"]),
                   shadow=bool(rig["shadow"]), shadowFixed=float(max(ext) * 0.75 + 0.2), shadowBias=0.6)]
    if rig.get("rim_lux", 0) > 0:
        lights.append(dict(type="directional", direction=list(rig["rim_dir"]), intensity=rig["rim_lux"], color=list(rig["rim_color"]), shadow=False))
    if rig.get("fill_lux", 0) > 0:
        lights.append(dict(type="directional", direction=list(rig["fill_dir"]), intensity=rig["fill_lux"], color=list(rig["fill_color"]), shadow=False))
    for extra in rig.get("extra", []):
        lights.append(extra)
    return dict(out=out, width=int(W), height=int(H), toneMapping=False, msaa=True, background=list(background), camera=cam,
                ibl=dict(image=rig.get("env") or ui_env(), exponent=rig["ibl_exp"]), lights=lights,
                items=[_item(it) for it in items])


def _item(it):
    """(usdz, 4x4) or (usdz, 4x4, holdout): a holdout item occludes but renders transparent (mfrender OcclusionMaterial)."""
    d = dict(usdz=it[0], matrix=np.asarray(it[1]).reshape(-1).tolist())
    if len(it) > 2 and it[2]:
        d["holdout"] = True
    return d


def run_job(renders, tag, attempts=3, timeout=220):
    os.makedirs(os.path.join(BUILD, "jobs"), exist_ok=True)
    for s in renders:
        if os.path.exists(s["out"]):
            os.remove(s["out"])
    todo = renders
    for _ in range(attempts):
        job = os.path.join(BUILD, "jobs", f"job_{tag}_{os.getpid()}.json")
        json.dump(dict(renders=todo), open(job, "w"))
        p = subprocess.Popen([RENDER, job], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        try:
            _, err = p.communicate(timeout=timeout)
            if "fail" in err.lower():
                print(err.strip()[-2000:])
        except subprocess.TimeoutExpired:
            p.kill(); p.communicate()
        os.remove(job)
        todo = [s for s in todo if not os.path.exists(s["out"])]
        if not todo:
            return True
    print("WARNING: missing renders:", [s["out"] for s in todo])
    return False


def posed_bounds(meta_list):
    """meta_list: [(meta with bbox_min/max, 4x4)] -> world bounds of the transformed boxes."""
    pts = []
    for meta, M in meta_list:
        lo, hi = np.array(meta["bbox_min"]), np.array(meta["bbox_max"])
        corners = np.array([[x, y, z] for x in (lo[0], hi[0]) for y in (lo[1], hi[1]) for z in (lo[2], hi[2])])
        pts.append(corners @ np.asarray(M)[:3, :3].T + np.asarray(M)[:3, 3])
    pts = np.vstack(pts)
    return pts.min(0), pts.max(0)


def fit_to_frame(im, frame_px, fill=0.96, align=(0.5, 0.5), anchor=None, xform=None):
    """Crop to the alpha bbox, scale to fit fill*frame (keeping aspect), paste into the exact frame.
    `xform` (a dict) receives the crop origin, scale and paste offset, so 3D anchors can follow the image."""
    a = np.asarray(im.getchannel("A"))
    ys, xs = np.nonzero(a > 3)
    if not len(xs):
        return Image.new("RGBA", frame_px, (0, 0, 0, 0))
    im = im.crop((xs.min(), ys.min(), xs.max() + 1, ys.max() + 1))
    W, H = frame_px
    fx, fy = (fill, fill) if np.isscalar(fill) else fill
    s = min(W * fx / im.width, H * fy / im.height)
    nw, nh = max(1, round(im.width * s)), max(1, round(im.height * s))
    im = im.resize((nw, nh), Image.LANCZOS)
    canvas = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    x = round((W - nw) * align[0]); y = round((H - nh) * align[1])
    canvas.alpha_composite(im, (x, y))
    if xform is not None:
        xform.update(crop=(int(xs.min()), int(ys.min())), scale=nw / (xs.max() + 1 - xs.min()), offset=(x, y))
    return canvas


def project(cam, W, H, pts):
    """World points -> raw render pixels for a scene_job camera."""
    C = np.array(cam["position"], float); T = np.array(cam["target"], float); up = np.array(cam["up"], float)
    f = T - C; f /= np.linalg.norm(f)
    r = np.cross(f, up); r /= np.linalg.norm(r)
    u = np.cross(r, f)
    v = np.asarray(pts, float) - C
    xc, yc, zc = v @ r, v @ u, v @ f
    t = math.tan(math.radians(cam["fov"]) / 2)
    x = xc / (zc * t * (W / H)); y = yc / (zc * t)
    return np.stack([(x + 1) / 2 * W, (1 - y) / 2 * H], 1)


def sticker_outline(im, color, width_px):
    """A soft constant-width outline around the alpha (the sticker rim some UI icons have, e.g. the key)."""
    from scipy import ndimage
    a = np.asarray(im.getchannel("A")).astype(np.float32) / 255
    r = int(math.ceil(width_px)) + 1
    yy, xx = np.mgrid[-r:r + 1, -r:r + 1]
    k = (xx * xx + yy * yy) <= width_px * width_px
    grown = ndimage.maximum_filter(a, footprint=k)
    grown = ndimage.gaussian_filter(grown, 0.6)
    col = np.array(Image.new("RGB", (1, 1), color).getpixel((0, 0)), np.float32)
    base = np.zeros(a.shape + (4,), np.float32)
    base[..., :3] = col
    base[..., 3] = grown * 255
    under = Image.fromarray(np.clip(base, 0, 255).astype(np.uint8), "RGBA")
    under.alpha_composite(im)
    return under


def item_usdz(item_id):
    """A built game item (art/out/<id>.usdz) + its bbox, for scene renders (splash, pages)."""
    meta = json.load(open(os.path.join(ITEMS, f"{item_id}.json")))
    return os.path.join(ITEMS, f"{item_id}.usdz"), dict(bbox_min=meta["bbox_min"], bbox_max=meta["bbox_max"])


def render_case(case, recipe, draft=False, force=False, log=print, mod=None):
    """mod: an already-loaded recipe module (rig.py injects generated models/cases into it)."""
    mod = mod or _load(recipe)
    spec = mod.ASSETS[case]
    frame = spec["frame"]
    fw, fh = int(round(frame[0] * 3)), int(round(frame[1] * 3))
    q = 0.35 if draft else 1.0
    # scene: a list of (model or "item:<id>", dict(yaw, pitch, roll, pos, scale, center, holdout))
    entries = spec.get("scene") or [(spec["model"], dict(yaw=spec.get("yaw", 0), pitch=spec.get("pitch", 0), roll=spec.get("roll", 0)))]
    items, metas = [], []
    for model, pose in entries:
        if model.startswith("item:"):
            u, meta = item_usdz(model[5:])
        else:
            u, meta = model_usdz(recipe, mod, model, force=force, log=log)
        c = (np.array(meta["bbox_min"]) + np.array(meta["bbox_max"])) / 2
        R = _look(pose.get("yaw", 0), pose.get("pitch", 0), pose.get("roll", 0))
        if "R" in pose:
            R = np.asarray(pose["R"]) @ R
        s = pose.get("scale", 1.0)
        t = np.asarray(pose.get("pos", (0, 0, 0)), float) - (R @ c) * s if pose.get("center", True) else np.asarray(pose.get("pos", (0, 0, 0)), float)
        M = mat4(R, t, s)
        if "view" in spec:  # a scene-level camera orbit: (yaw, pitch) applied to every entry, positions included
            Rv = uikit.rot_x(spec["view"][1]) @ uikit.rot_y(spec["view"][0])
            M = mat4(Rv) @ M
        items.append((u, M, bool(pose.get("holdout")))); metas.append((meta, M))
    lo, hi = posed_bounds(metas)
    if "bounds" in spec:
        lo, hi = np.asarray(spec["bounds"][0], float), np.asarray(spec["bounds"][1], float)
    ext = hi - lo
    # render size: the frame at SS x, shaped like the posed bounds so little is wasted
    long_px = max(fw, fh) * spec.get("ss", SS) * q * spec.get("oversample", 1.15)
    asp = max(ext[0], 1e-3) / max(ext[1], 1e-3)
    if spec.get("render_aspect"):
        asp = spec["render_aspect"]
    W, H = (long_px, long_px / asp) if asp >= 1 else (long_px * asp, long_px)
    W, H = int(max(64, W)), int(max(64, H))
    tag = f"{case}{'_draft' if draft else ''}"
    raw = os.path.join(BUILD, "raw", f"{tag}.png")
    os.makedirs(os.path.dirname(raw), exist_ok=True)
    vis = [it for it in items if not it[2]]
    job = scene_job(raw, W, H, vis, (lo, hi), fov=spec.get("fov", 18.0), light=spec.get("light"),
                    background=spec.get("background", (0, 0, 0, 0)), margin=spec.get("margin", 1.06))
    jobs = [job]
    if len(vis) < len(items):
        # holdout entries: a MATTE render with the same camera -- visible parts unlit white, holdout parts unlit black
        # on black -- multiplied into the alpha, so the case keeps only what the holdout parts do not hide
        mj = scene_job(raw[:-4] + "_matte.png", W, H, [(u, M) for u, M, _ in items], (lo, hi), fov=spec.get("fov", 18.0),
                       light=spec.get("light"), background=(0, 0, 0, 1), margin=spec.get("margin", 1.06))
        for d, it in zip(mj["items"], items):
            d["unlit"] = [0.0, 0.0, 0.0] if it[2] else [1.0, 1.0, 1.0]
        jobs.append(mj)
    ok = run_job(jobs, tag)
    if not ok:
        raise SystemExit(f"{case}: render failed")
    im = Image.open(raw).convert("RGBA")
    if len(jobs) > 1:
        mt = np.asarray(Image.open(jobs[1]["out"]).convert("L")).astype(np.float32) / 255
        arr = np.asarray(im).copy()
        arr[..., 3] = np.clip(arr[..., 3].astype(np.float32) * mt, 0, 255).astype(np.uint8)
        im = Image.fromarray(arr, "RGBA")
    if spec.get("post"):
        im = spec["post"](im)
    xf = {}
    if spec.get("no_fit"):
        out_im = im.resize((fw, fh), Image.LANCZOS)
        xf = dict(crop=(0, 0), scale=fw / im.width, offset=(0, 0))
    else:
        out_im = fit_to_frame(im, (fw, fh), fill=spec.get("fill", 0.96), align=spec.get("align", (0.5, 0.5)), xform=xf)
    if spec.get("anchors") and not draft:
        M0 = items[0][1]
        side = dict(case=case, frame_pt=[fw / 3, fh / 3], note="points in pt within the image (origin top-left)")
        for name, pts in spec["anchors"].items():
            P = np.asarray(pts, float) @ M0[:3, :3].T + M0[:3, 3]
            px = project(job["camera"], W, H, P)
            q = (px - np.array(xf["crop"])) * xf["scale"] + np.array(xf["offset"])
            side[name] = [[round(float(a) / 3, 2), round(float(b) / 3, 2)] for a, b in q]
        side_dir = os.path.join(BUILD, "route3d") if spec.get("dest") == "route3d" else OUT
        os.makedirs(side_dir, exist_ok=True)
        json.dump(side, open(os.path.join(side_dir, spec.get("sidecar", case) + ".json"), "w"), indent=1)
        if spec.get("dest") == "parts":  # rig layers: keep the pivots next to the part PNG too (art/ui/tools/rig.py)
            os.makedirs(os.path.join(BUILD, "parts"), exist_ok=True)
            json.dump(side, open(os.path.join(BUILD, "parts", case + ".json"), "w"), indent=1)
    if spec.get("outline"):
        out_im = sticker_outline(out_im, *spec["outline"])
    if spec.get("post_fit"):
        out_im = spec["post_fit"](out_im)
    dst = os.path.join(BUILD, "draft", f"{case}.png") if draft else os.path.join(OUT, f"{case}@3x.png")
    if spec.get("dest") == "parts" and not draft:  # intermediate layers for composites (never shipped as-is)
        dst = os.path.join(BUILD, "parts", f"{case}.png")
    if spec.get("dest") == "route3d" and not draft:  # art-spike candidates (compare_swap.py route "3d"), not shipped
        nm = case[:-3] if case.endswith("_3d") else case
        dst = os.path.join(BUILD, "route3d", f"{nm}.png")
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    tmp = dst + f".tmp{os.getpid()}.png"
    out_im.save(tmp, optimize=True)
    os.replace(tmp, dst)
    log(f"  {case}: {fw}x{fh} px -> {os.path.relpath(dst, APP)}")
    return dst


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("names", nargs="*")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--draft", action="store_true")
    ap.add_argument("--force", action="store_true", help="re-mesh even if the recipe is unchanged")
    ap.add_argument("--recipes", help="recipe directory (default art/ui/recipes; e.g. art/pipeline/items for char_*.py)")
    ap.add_argument("--out", help="output directory for non-dest cases (default art/ui/out; 3D characters/scenes: art/out)")
    ap.add_argument("--rig", action="store_true", help="names are RIGS entries: export cut-out puppet layers (rig.py)")
    a = ap.parse_args()
    global OUT
    if a.recipes:
        set_recipes(a.recipes)
    if a.out:
        OUT = os.path.abspath(a.out)
    if a.rig:
        import rig as _rig
        for n in a.names:
            _rig.export(n, draft=a.draft, force=a.force)
        return
    idx = index()
    if a.list:
        by = {}
        for c, r in idx.items():
            by.setdefault(r, []).append(c)
        for r, cs in sorted(by.items()):
            print(f"{r}: {', '.join(cs)}")
        return
    cases = []
    for n in a.names:
        if n in idx:
            cases.append((n, idx[n]))
        elif n in recipe_names():
            cases += [(c, n) for c, r in idx.items() if r == n]
        else:
            raise SystemExit(f"unknown case or recipe {n}")
    for c, r in cases:
        t0 = time.time()
        render_case(c, r, draft=a.draft, force=a.force)
        print(f"  ({time.time() - t0:.1f}s)")


if __name__ == "__main__":
    main()
