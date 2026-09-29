#!/usr/bin/env python3
"""Render previews of built items with the game-like lighting rig and make contact sheets.

    PY=~/.venvs/mf3d/bin/python
    $PY art/pipeline/preview.py toy_hammer star_mallet --sheet   # item ids or recipe names, any subset
    $PY art/pipeline/preview.py --board                          # level-1 board mock vs the capture
    $PY art/pipeline/preview.py rubber_duck strawberry toy_hammer --icons   # goal-card comparison strip

Needs build/art/mfrender (art/pipeline/render/build.sh). Per item id it writes
    art/out/<id>_icon.png, art/out/<id>_icon_sticker.png       (goal-card icons, 512 px, transparent)
    art/previews/<id>_sheet.png   one row: reference crops | our board renders (both 200 px/unit),
                                  goal-card ref | our sticker icon | hint-outline check,
                                  tray ref | our tray-pose render (both 3 px/pt), shape turntable
and with --sheet the rows stacked into art/previews/contact_<name>.png (--name, default from the ids).
"""
from __future__ import annotations

import argparse
import json
import math
import os
import subprocess
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
ART = os.path.dirname(HERE)
APP = os.path.dirname(ART)
OUT = os.path.join(ART, "out")
PREV = os.path.join(ART, "previews")
RIG = os.path.join(ART, "rig")
RENDER = os.path.join(APP, "build", "art", "mfrender")
RESEARCH = os.path.join(APP, "research")

# On the reference capture (1178 px wide iPhone screen) one board unit is ~200 px.
PX_PER_UNIT = 200.0
SS = 2  # supersampling factor

# ------------------------------------------------------------------ the lighting rig (see STYLE.md)
RIG_CFG = dict(
    # key light travels mostly toward +Z (screen down) and a little +X (screen right): the capture's
    # drop shadows stick out ~16 px down and ~6 px right of 0.5-unit-tall items
    key_dir=(0.13, -1.0, 0.36),
    key_lux=2260.0,  # hot key: top-facing lit ~1.45x albedo (capture duck highlight (255,200,0) vs albedo (251,169,0))
    key_color=(1.0, 0.985, 0.96),
    fill_dir=(-0.5, -0.6, -0.4),
    fill_lux=0.0,
    fill_color=(0.80, 0.88, 1.0),
    ibl_exponent=-2.3,  # items: dim ambient (capture: item darks ~0.2 linear of lit)
    floor_ibl_exponent=1.01,  # floor: shadow/lit = 0.5 linear (capture 0.77 sRGB)
    floor_gain=0.74,  # floor albedo scale so the brighter-lit floor still lands on the capture colours
    floor_center=(0.43, 0.53, 0.66),  # sRGB, measured board centre (110,135,168)
    floor_edge=(0.235, 0.28, 0.345),  # measured board edge (65,77,93)
    tonemap=False,
)


def srgb(c):
    return [float(x) for x in c]


def _save_atomic(img, path):
    tmp = f"{path}.tmp{os.getpid()}.png"
    img.save(tmp)
    os.replace(tmp, path)


def make_rig_assets(force=False):
    """studio_env.png, floor.png, tray_tile.usdz in art/rig/ (written once; --rig forces a rewrite)."""
    os.makedirs(RIG, exist_ok=True)
    if not os.path.exists(os.path.join(RIG, "tray_tile.usdz")) or force:
        make_tray_tile()
    if not force and os.path.exists(os.path.join(RIG, "studio_env.png")) and os.path.exists(os.path.join(RIG, "floor.png")):
        return
    # equirect studio environment: warm-white sky dome, soft big key "softbox" top-left-front,
    # blue-grey horizon, dark slate below (the floor)
    W, H = 512, 256
    u, v = np.meshgrid((np.arange(W) + 0.5) / W, (np.arange(H) + 0.5) / H)
    phi = (u - 0.5) * 2 * math.pi
    theta = v * math.pi  # 0 = up
    d = np.stack([np.sin(theta) * np.sin(phi), np.cos(theta), -np.sin(theta) * np.cos(phi)], -1)
    up = d[..., 1]
    sky = np.array([0.90, 0.90, 0.90])
    hor = np.array([0.42, 0.43, 0.45])
    gnd = np.array([0.14, 0.15, 0.17])
    t = np.clip(up, -1, 1)
    col = np.where(t[..., None] > 0, hor + (sky - hor) * np.sqrt(np.clip(t, 0, 1))[..., None],
                   hor + (gnd - hor) * np.clip(-t * 3, 0, 1)[..., None])
    k = -np.asarray(RIG_CFG["key_dir"], float); k /= np.linalg.norm(k)
    sb = np.clip((d @ k - 0.86) / 0.14, 0, 1) ** 1.5
    col = col + sb[..., None] * np.array([0.35, 0.34, 0.32])
    img = (np.clip(col, 0, 1) ** (1 / 1.0) * 255).astype(np.uint8)
    _save_atomic(Image.fromarray(img), os.path.join(RIG, "studio_env.png"))
    # floor: radial vignette like the game board
    N = 1024
    yy, xx = np.meshgrid(np.linspace(-1, 1, N), np.linspace(-1, 1, N), indexing="ij")
    r = np.sqrt((xx / 0.75) ** 2 + (yy / 1.0) ** 2)
    w = np.clip(1 - r, 0, 1) ** 1.2
    c0 = np.array(RIG_CFG["floor_edge"]); c1 = np.array(RIG_CFG["floor_center"])
    fl = (c0 + (c1 - c0) * w[..., None]) * RIG_CFG["floor_gain"]
    _save_atomic(Image.fromarray((fl * 255).astype(np.uint8)), os.path.join(RIG, "floor.png"))


# tray tile (research/motion.md 2 + tray crops): 46.5 pt square slab, ~6 pt thick, blue-grey
PT_PX = 3.0  # capture px per pt
TILE_W = 46.5 * PT_PX / PX_PER_UNIT  # in board units (1 unit = 200 capture px)
TILE_T = 6.0 * PT_PX / PX_PER_UNIT
TILE_TILT = 25.0  # deg: the tile top face reads ~0.4 of its depth on the capture (55 px top, 15 px front)
ITEM_TILT = 12.0  # deg: tray items show "a little of the top"


def make_tray_tile():
    sys.path.insert(0, HERE)
    from mesher import Item, Material, Part, build_item
    from sdf import box
    from usdwriter import write_usdz
    mat = Material("tray_tile", "#56709A", roughness=0.7, ior=1.1)
    it = Item("tray_tile", [Part("tile", box(TILE_W / 2, TILE_T / 2, TILE_W / 2, round=0.03), mat, voxel=0.006)],
              length=TILE_W, budget=400, voxel=0.006)
    meshes, _, _, _ = build_item(it, log=lambda *a: None)
    tmp = os.path.join(RIG, f"tray_tile.tmp{os.getpid()}.usdz")
    write_usdz("tray_tile", meshes, tmp)
    os.replace(tmp, os.path.join(RIG, "tray_tile.usdz"))


def lights(shadow_half=None):
    c = RIG_CFG
    L = [dict(type="directional", direction=list(c["key_dir"]), intensity=c["key_lux"], color=list(c["key_color"]), shadow=True, shadowScale=24)]
    if shadow_half:
        L[0]["shadowFixed"] = float(shadow_half)
    if c["fill_lux"] > 0:
        L.append(dict(type="directional", direction=list(c["fill_dir"]), intensity=c["fill_lux"], color=list(c["fill_color"]), shadow=False))
    return L


def base_scene(out, w, h, cam, floor=True, background=None, floor_size=12.0, shadow_half=None):
    s = dict(out=out, width=w, height=h, toneMapping=RIG_CFG["tonemap"], msaa=True,
             background=background or [*RIG_CFG["floor_edge"], 1.0], camera=cam,
             ibl=dict(image=os.path.join(RIG, "studio_env.png"), exponent=RIG_CFG["ibl_exponent"]),
             lights=lights(shadow_half), items=[])
    if floor:
        s["floor"] = dict(y=0.0, size=floor_size, texture=os.path.join(RIG, "floor.png"), roughness=1.0, unlit=False,
                          iblExponent=RIG_CFG["floor_ibl_exponent"])
    return s


def top_camera(view_w_units, aspect, center=(0.0, 0.0), dist=14.0):
    """Straight-down, narrow-FOV perspective camera (screen up = -Z) framing view_w_units on the floor.
    (RealityKit's automatic directional shadows barely work with an orthographic camera.)"""
    h_units = view_w_units / aspect
    fov = 2 * math.degrees(math.atan(h_units / 2 / dist))
    return dict(type="persp", position=[center[0], dist, center[1] + 0.0001], target=[center[0], 0, center[1]],
                up=[0, 0, -1], fov=fov, near=1.0, far=dist + 10)


def pose_matrix(meta, pose_index=0, yaw=0.0, pos=(0.0, 0.0)):
    poses = meta.get("stable_poses") or []
    M = np.array(poses[pose_index]["matrix"]) if poses else np.eye(4)
    c, s = math.cos(math.radians(yaw)), math.sin(math.radians(yaw))
    Ry = np.array([[c, 0, s, 0], [0, 1, 0, 0], [-s, 0, c, 0], [0, 0, 0, 1]])
    M = Ry @ M
    # recentre the rested item on (pos) in XZ
    T = np.eye(4); T[0, 3] = pos[0] - M[0, 3]; T[2, 3] = pos[1] - M[2, 3]
    M2 = M.copy(); M2[0, 3] += T[0, 3]; M2[2, 3] += T[2, 3]
    return M2.reshape(-1).tolist()


def pose_up(meta, up_axis, yaw=0.0, pos=(0.0, 0.0), roll=0.0):
    """Lay the item so its local `up_axis` points to world +Y, spin by `yaw` about +Y, rest it on the floor."""
    import sys as _s
    _s.path.insert(0, HERE)
    from sdf import rot_align
    R = rot_align(up_axis, (0, 1, 0))
    if roll:
        a = math.radians(roll); ax = np.asarray(up_axis, float) / np.linalg.norm(up_axis)
        from sdf import _rot
        R = R @ _rot(ax, roll)
    c, s_ = math.cos(math.radians(yaw)), math.sin(math.radians(yaw))
    Ry = np.array([[c, 0, s_], [0, 1, 0], [-s_, 0, c]])
    R = Ry @ R
    pts = np.vstack([np.array(h["points"]) for h in meta["collision_hulls"]])
    q = pts @ R.T
    M = np.eye(4); M[:3, :3] = R
    M[0, 3] = pos[0] - (q[:, 0].min() + q[:, 0].max()) / 2
    M[2, 3] = pos[1] - (q[:, 2].min() + q[:, 2].max()) / 2
    M[1, 3] = -q[:, 1].min()
    return M.reshape(-1).tolist()


def upright_matrix(yaw=0.0, pitch=0.0, pos=(0.0, 0.0, 0.0)):
    a, b = math.radians(yaw), math.radians(pitch)
    Ry = np.array([[math.cos(a), 0, math.sin(a)], [0, 1, 0], [-math.sin(a), 0, math.cos(a)]])
    Rx = np.array([[1, 0, 0], [0, math.cos(b), -math.sin(b)], [0, math.sin(b), math.cos(b)]])
    R = Rx @ Ry
    M = np.eye(4); M[:3, :3] = R; M[:3, 3] = pos
    return M.reshape(-1).tolist()


def run_job(renders, name, attempts=4):
    """Render a batch; the renderer's watchdog exits on a RealityKit stall, so retry what is missing.
    Safe for parallel lanes: private job file, and a timeout kills only this job's renderer."""
    os.makedirs(PREV, exist_ok=True)
    for o in (s["out"] for s in renders):
        if os.path.exists(o):
            os.remove(o)
    todo = renders
    for attempt in range(attempts):
        job = os.path.join(PREV, f".job_{name}_{os.getpid()}.json")
        with open(job, "w") as fh:
            json.dump(dict(renders=todo), fh)
        p = subprocess.Popen([RENDER, job], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        try:
            _, err = p.communicate(timeout=200)
            if "failed" in err:
                print(err.strip())
        except subprocess.TimeoutExpired:
            p.kill(); p.communicate()
        os.remove(job)
        todo = [s for s in todo if not os.path.exists(s["out"])]
        if not todo:
            return
    print(f"WARNING: {len(todo)} renders missing after {attempts} attempts:", [s["out"] for s in todo])


def downsample(path, factor=SS):
    im = Image.open(path)
    im = im.resize((im.width // factor, im.height // factor), Image.LANCZOS)
    im.save(path)
    return im


# ------------------------------------------------------------------ per-item previews

# Legacy fallback only: reference crops + poses now live in the recipes (Item.ref_poses) and are
# copied into <id>.json by build.py, so modelling lanes never edit this file.
REF_POSES = {}


def load_meta(name):
    return json.load(open(os.path.join(OUT, f"{name}.json")))


def resolve_ids(names):
    """Item ids or recipe names -> built item ids (a recipe name expands to every id it emits)."""
    built = {}
    for fn in os.listdir(OUT):
        if fn.endswith(".json") and fn != "catalog.json" and ".tmp" not in fn:
            try:
                built[fn[:-5]] = json.load(open(os.path.join(OUT, fn))).get("recipe")
            except Exception:
                pass
    ids = []
    for n in names:
        hits = ([n] if n in built else []) + sorted(i for i, r in built.items() if r == n and i != n)
        if not hits:
            raise SystemExit(f"{n}: not built (run build.py {n} first)")
        ids += [h for h in hits if h not in ids]
    return ids


def _font(size=16):
    from PIL import ImageFont
    try:
        return ImageFont.load_default(size=size)
    except Exception:
        return ImageFont.load_default()


def item_refs(name, meta):
    """[(crop path relative to APP or None, pose, yaw)]: the recipe's ref_poses, else research/items/<slug>[-x].png
    with the most probable resting poses."""
    refs = [tuple(r) for r in (meta.get("ref_poses") or REF_POSES.get(name, []))]
    if refs:
        return refs
    import glob
    slug = meta.get("slug") or name.replace("_", "-")
    crops = sorted(glob.glob(os.path.join(RESEARCH, "items", f"{slug}.png")) +
                   glob.glob(os.path.join(RESEARCH, "items", f"{slug}-[a-z].png")))
    n = max(1, len(meta.get("stable_poses") or []))
    if crops:
        return [(os.path.relpath(c, APP), i % n, 0.0) for i, c in enumerate(crops[:3])]
    return [(None, i, 0.0) for i in range(min(3, n))]


def _pose_M(meta, pose, yaw, pos=(0.0, 0.0)):
    if isinstance(pose, (tuple, list)) and pose and pose[0] == "up":
        return pose_up(meta, pose[1], yaw, pos, roll=pose[2] if len(pose) > 2 else 0.0)
    n = max(1, len(meta.get("stable_poses") or []))
    return pose_matrix(meta, min(int(pose), n - 1), yaw, pos)


def icon_camera(meta, px=768):
    rad = 0.5 * float(np.linalg.norm(np.subtract(meta["bbox_max"], meta["bbox_min"])))
    fov = 2 * math.degrees(math.atan(rad * 1.04 / 8.0))
    px_per_unit = px / (2 * 8.0 * math.tan(math.radians(fov) / 2))
    return dict(type="persp", position=[0, 0, 8.0], target=[0, 0, 0], up=[0, 1, 0], fov=fov, near=0.1, far=20), px_per_unit


def icon_rig(s):
    """Goal-card / tray rig: frontal key from the upper left, brighter ambient."""
    s["lights"][0]["direction"] = [0.35, -0.5, -0.8]
    s["lights"][0]["intensity"] = RIG_CFG["key_lux"] * 1.1
    s["ibl"]["exponent"] = RIG_CFG["ibl_exponent"] + 1.6
    return s


def tray_scene(meta, usdz, out, w_pt=70, h_pt=82):
    """The item standing on a tray tile in its tray pose and tray scale, at capture scale (3 px/pt)."""
    W, H = int(w_pt * PT_PX) * SS, int(h_pt * PT_PX) * SS
    view_h = h_pt * PT_PX / PX_PER_UNIT
    dist = 14.0
    fov = 2 * math.degrees(math.atan(view_h / 2 / dist))
    cam = dict(type="persp", position=[0, 0, dist], target=[0, 0, 0], up=[0, 1, 0], fov=fov, near=1, far=30)
    s = icon_rig(base_scene(out, W, H, cam, floor=False, background=[60 / 255, 71 / 255, 85 / 255, 1]))
    s["lights"][0]["shadow"] = False
    ay = -view_h / 2 + 0.24 * view_h  # anchor: the middle of the tile's top face
    t = math.radians(TILE_TILT)
    Rt = np.array([[1, 0, 0], [0, math.cos(t), -math.sin(t)], [0, math.sin(t), math.cos(t)]])
    Mt = np.eye(4); Mt[:3, :3] = Rt; Mt[:3, 3] = np.array([0, ay, 0]) - Rt @ np.array([0, TILE_T / 2, 0])
    a = math.radians(ITEM_TILT)
    Ri = np.eye(4); Ri[:3, :3] = [[1, 0, 0], [0, math.cos(a), -math.sin(a)], [0, math.sin(a), math.cos(a)]]
    S = np.diag([meta["tray_scale"]] * 3 + [1.0])
    T = np.eye(4); T[1, 3] = ay + 3.0 * PT_PX / PX_PER_UNIT; T[2, 3] = 0.05
    Mi = T @ S @ Ri @ np.array(meta["tray_pose"]["matrix"])
    s["items"] = [dict(usdz=os.path.join(RIG, "tray_tile.usdz"), matrix=Mt.reshape(-1).tolist()),
                  dict(usdz=usdz, matrix=Mi.reshape(-1).tolist())]
    return s


def item_previews(name, turntable=True):
    meta = load_meta(name)
    usdz = os.path.join(OUT, f"{name}.usdz")
    ousdz = os.path.join(OUT, meta.get("outline", {}).get("file", f"{name}.outline.usdz"))
    tile_units = 1.6
    tile = int(tile_units * PX_PER_UNIT) * SS
    renders = []
    refs = item_refs(name, meta)
    for i, (_, pose, yaw) in enumerate(refs):
        s = base_scene(os.path.join(PREV, f"{name}_board{i}.png"), tile, tile, top_camera(tile_units, 1.0),
                       shadow_half=tile_units / 2 + 0.3)
        s["items"] = [dict(usdz=usdz, matrix=_pose_M(meta, pose, yaw))]
        renders.append(s)
    # upright icon (goal card): front view, slight top-down, transparent; + the outline shell, same camera
    yaw, pitch = meta.get("icon_view", [0, 8])
    cam, ppu = icon_camera(meta)
    c = np.array(meta["bbox_center"])
    for tag, f in (("icon", usdz), ("outlinecheck", ousdz)):
        s = icon_rig(base_scene(os.path.join(PREV, f"{name}_{tag}_raw.png"), 768, 768, cam, floor=False, background=[0, 0, 0, 0]))
        s["items"] = [dict(usdz=f, matrix=upright_matrix(yaw, pitch, tuple(-c)))]
        renders.append(s)
    renders.append(tray_scene(meta, usdz, os.path.join(PREV, f"{name}_tray.png")))
    if turntable:
        for k in range(4):
            cam3 = dict(type="persp", position=[0, 3.2, 3.2], target=[0, 0.25, 0], up=[0, 1, 0], fov=24, near=0.1, far=20)
            s = base_scene(os.path.join(PREV, f"{name}_turn{k}.png"), 300, 300, cam3)
            s["items"] = [dict(usdz=usdz, matrix=upright_matrix(90 * k + 30, 0, (0, -meta["bbox_min"][1], 0)))]
            renders.append(s)
    run_job(renders, name)
    for i in range(len(refs)):
        p = os.path.join(PREV, f"{name}_board{i}.png")
        if os.path.exists(p):
            downsample(p)
    if os.path.exists(os.path.join(PREV, f"{name}_tray.png")):
        downsample(os.path.join(PREV, f"{name}_tray.png"))
    check = finish_icon(name, meta, ppu)
    make_row(name, meta, refs, check, turntable)
    return check


def finish_icon(name, meta, ppu):
    """Crop the icon to out/<id>_icon.png (512 px) + sticker; compare the outline shell's silhouette with
    the item's (IoU) and draw the hint look (constant-width lime rim around the shell) to <id>_hint.png."""
    from scipy import ndimage
    raw = os.path.join(PREV, f"{name}_icon_raw.png")
    oraw = os.path.join(PREV, f"{name}_outlinecheck_raw.png")
    res = {}
    if not os.path.exists(raw):
        return res
    im = Image.open(raw).convert("RGBA")
    ia = np.asarray(im)[..., 3] > 8
    if os.path.exists(oraw):
        oa = np.asarray(Image.open(oraw).convert("RGBA"))[..., 3] > 8
        res["outline_iou"] = round(float((ia & oa).sum() / max((ia | oa).sum(), 1)), 4)
        res["outline_outside_px"] = int((oa & ~ia).sum())
        res["item_outside_px"] = int((ia & ~oa).sum())
        w = max(2, int(round(3.5 / (200 / 3) * ppu)))  # the engine's 3.5 pt rim at board scale
        yy, xx = np.mgrid[-w:w + 1, -w:w + 1]
        ring = ndimage.binary_dilation(oa, structure=xx * xx + yy * yy <= w * w) & ~ia
        hint = np.zeros(ia.shape + (4,), np.uint8)
        hint[ring] = (224, 248, 0, 255)
        h = Image.fromarray(hint, "RGBA"); h.alpha_composite(im)
        bb = Image.fromarray((ring | ia).astype(np.uint8) * 255).getbbox()
        if bb:
            h = h.crop(bb)
        bg = Image.new("RGBA", h.size, (40, 47, 57, 255)); bg.alpha_composite(h)
        bg.convert("RGB").save(os.path.join(PREV, f"{name}_hint.png"))
        os.remove(oraw)
    bb = im.getchannel("A").point(lambda a: 255 if a > 8 else 0).getbbox()
    if bb:
        im = im.crop(bb)
        side = int(max(im.size) * 1.08)
        sq = Image.new("RGBA", (side, side), (0, 0, 0, 0))
        sq.paste(im, ((side - im.width) // 2, (side - im.height) // 2))
        icon = sq.resize((512, 512), Image.LANCZOS)
        icon.save(os.path.join(OUT, f"{name}_icon.png"))
        sticker(icon).save(os.path.join(OUT, f"{name}_icon_sticker.png"))
    os.remove(raw)
    return res


def fit(im, h):
    return im.resize((max(1, int(im.width * h / im.height)), h), Image.LANCZOS)


CARD = (47, 66, 97)


def make_row(name, meta, refs, check, turntable=True):
    """One contact-sheet row: refs | ours (200 px/unit) | goal card ref | ours icon | hint | tray ref | ours tray | turntable."""
    blocks = []

    def add(caption, im, group):
        blocks.append((caption, im.convert("RGB"), group))

    for i, (r, _, _) in enumerate(refs):
        if r and os.path.exists(os.path.join(APP, r)):
            add(os.path.basename(r)[:-4][:22], Image.open(os.path.join(APP, r)), 0)
    for i in range(len(refs)):
        p = os.path.join(PREV, f"{name}_board{i}.png")
        if os.path.exists(p):
            add(f"ours {i}", Image.open(p), 1)
    ir = meta.get("icon_ref")
    if ir and os.path.exists(os.path.join(APP, ir[0])):
        add("goal card (ref)", fit(Image.open(os.path.join(APP, ir[0])).crop(tuple(ir[1])), 200), 2)
    sp = os.path.join(OUT, f"{name}_icon_sticker.png")
    if os.path.exists(sp):
        card = Image.new("RGBA", (512, 512), CARD + (255,)); card.alpha_composite(Image.open(sp).convert("RGBA"))
        add("ours icon", fit(card, 200), 2)
    hp = os.path.join(PREV, f"{name}_hint.png")
    if os.path.exists(hp):
        add(f"hint rim, IoU {check.get('outline_iou', 0):.3f}", fit(Image.open(hp), 200), 2)
    tr = meta.get("tray_ref") or f"research/items/{meta.get('slug') or name.replace('_', '-')}-upright-tray.png"
    if os.path.exists(os.path.join(APP, tr)):
        add("tray (ref)", Image.open(os.path.join(APP, tr)), 3)
    tp = os.path.join(PREV, f"{name}_tray.png")
    if os.path.exists(tp):
        add(f"ours tray x{meta['tray_scale']}", Image.open(tp), 3)
    if turntable:
        for k in range(4):
            p = os.path.join(PREV, f"{name}_turn{k}.png")
            if os.path.exists(p):
                add("turntable" if k == 0 else "", fit(Image.open(p), 150), 4)
    pad, cap, head = 8, 20, 30
    H = max([b[1].height for b in blocks] + [120])
    width = pad + sum(b[1].width + pad for b in blocks) + 16 * 4
    row = Image.new("RGB", (max(width, 900), head + cap + H + pad), (24, 26, 30))
    dr = ImageDraw.Draw(row)
    o = meta.get("outline", {})
    tf = meta.get("tray_fit", {})
    title = (f"{name}  ({meta.get('display_name', '')})   L{meta.get('first_level')} {meta.get('role')}"
             + (f"   variant of {meta['variant_of']}" if meta.get("variant_of") else "")
             + f"   {meta['triangles']} tris   outline {o.get('tris')} tris "
             + ("closed+manifold" if o.get("closed") and o.get("manifold") else "NOT CLOSED/MANIFOLD")
             + f"   tray x{meta.get('tray_scale')} = {tf.get('size_pt')} pt ({tf.get('limited_by')})")
    dr.text((pad, 6), title, fill=(235, 235, 235), font=_font(17))
    x, last = pad, None
    for caption, im, g in blocks:
        if last is not None and g != last:
            dr.line([(x + 4, head), (x + 4, head + cap + H)], fill=(70, 74, 82), width=2)
            x += 16
        dr.text((x, head + 2), caption, fill=(170, 176, 186), font=_font(13))
        row.paste(im, (x, head + cap + (H - im.height)))  # bottom-aligned
        x += im.width + pad
        last = g
    row = row.crop((0, 0, max(x, 900), row.height))
    p = os.path.join(PREV, f"{name}_sheet.png")
    row.save(p)
    print("sheet:", p, row.size, f"({meta['triangles']} tris, outline IoU {check.get('outline_iou')})")
    return p


def contact_sheet(ids, name=None):
    rows = [Image.open(os.path.join(PREV, f"{i}_sheet.png")).convert("RGB") for i in ids
            if os.path.exists(os.path.join(PREV, f"{i}_sheet.png"))]
    if not rows:
        return None
    W = max(r.width for r in rows)
    sh = Image.new("RGB", (W, sum(r.height + 6 for r in rows)), (12, 13, 15))
    y = 0
    for r in rows:
        sh.paste(r, (0, y)); y += r.height + 6
    nm = name or ("_".join(ids) if len("_".join(ids)) <= 60 else f"{ids[0]}_and_{len(ids) - 1}_more")
    p = os.path.join(PREV, f"contact_{nm}.png")
    sh.save(p)
    print("contact sheet:", p, sh.size)
    return p


# ------------------------------------------------------------------ level 1 board mock

def board_mock():
    """The level-1 board after the tutorial (capture 007) with our items, same framing."""
    ref = os.path.join(RESEARCH, "shots", "007-L01-after-continue.png")
    W_px, H_px = 1178, 660  # crop (0,1100)-(1178,1760) of the capture
    units_w = W_px / PX_PER_UNIT
    # (item, index into the item's ref_poses, centre x, centre y in crop px) -- matches capture 007
    layout = [
        ("strawberry", 0, 250, 195), ("strawberry", 1, 580, 122), ("strawberry", 2, 928, 152),
        ("rubber_duck", 0, 135, 420), ("rubber_duck", 1, 605, 462), ("rubber_duck", 2, 890, 520),
    ]
    items = []
    for name, ri, x, y in layout:
        mp = os.path.join(OUT, f"{name}.json")
        if not os.path.exists(mp):
            continue
        meta = json.load(open(mp))
        _, pose, yaw = item_refs(name, meta)[ri]
        ux = (x - W_px / 2) / PX_PER_UNIT
        uz = (y - H_px / 2) / PX_PER_UNIT
        items.append(dict(usdz=os.path.join(OUT, f"{name}.usdz"), matrix=_pose_M(meta, pose, yaw, (ux, uz))))
    o = os.path.join(PREV, "board_level1.png")
    s = base_scene(o, W_px * SS, H_px * SS, top_camera(units_w, W_px / H_px), shadow_half=units_w / 2 + 0.3)
    s["items"] = items
    run_job([s], "board")
    ours = downsample(o).convert("RGB")
    sheet = Image.new("RGB", (W_px, H_px * 2 + 8), (0, 0, 0))
    if os.path.exists(ref):
        sheet.paste(Image.open(ref).convert("RGB").crop((0, 1100, 1178, 1760)), (0, 0))
    sheet.paste(ours, (0, H_px + 8))
    sheet.save(os.path.join(PREV, "board_level1_vs_ref.png"))
    print("board:", os.path.join(PREV, "board_level1_vs_ref.png"))


# ------------------------------------------------------------------ goal-card icons (sticker style)

def sticker(icon_rgba, outline_px=14, color=(255, 255, 255)):
    """White sticker outline around the icon alpha, like the game's goal cards."""
    from scipy import ndimage
    a = np.asarray(icon_rgba)[..., 3] > 16
    yy, xx = np.mgrid[-outline_px:outline_px + 1, -outline_px:outline_px + 1]
    disk = xx * xx + yy * yy <= outline_px * outline_px
    grown = ndimage.binary_dilation(a, structure=disk)
    soft = ndimage.gaussian_filter(grown.astype(float), 1.0)
    base = np.zeros(a.shape + (4,), np.uint8)
    base[..., :3] = color
    base[..., 3] = (np.clip(soft, 0, 1) * 255).astype(np.uint8)
    out = Image.fromarray(base, "RGBA")
    out.alpha_composite(icon_rgba)
    return out


def icon_sheet(names):
    """Goal-card reference | our sticker icon on the card colour, for every id with an icon_ref."""
    tiles = []
    for n in names:
        sp = os.path.join(OUT, f"{n}_icon_sticker.png")
        if not os.path.exists(sp):
            continue
        our = Image.new("RGBA", (512, 512), CARD + (255,)); our.alpha_composite(Image.open(sp).convert("RGBA"))
        our = our.convert("RGB").resize((260, 260), Image.LANCZOS)
        ir = load_meta(n).get("icon_ref")
        if ir and os.path.exists(os.path.join(APP, ir[0])):
            ref = Image.open(os.path.join(APP, ir[0])).convert("RGB").crop(tuple(ir[1]))
            ref = ref.resize((260, int(260 * ref.height / ref.width)), Image.LANCZOS)
        else:
            ref = Image.new("RGB", (260, 260), (0, 0, 0))
        tiles.append((ref, our))
    if not tiles:
        return
    sh = Image.new("RGB", (8 + len(tiles) * (260 * 2 + 24), 8 + 300), (24, 26, 30))
    x = 8
    for ref, our in tiles:
        sh.paste(ref, (x, 8)); sh.paste(our, (x + 268, 8)); x += 260 * 2 + 24
    p = os.path.join(PREV, "icons_vs_goalcards.png")
    sh.save(p)
    print("icons:", p)


def material_swatches():
    """Render items/_materials.py (one sphere per palette family) with the board rig, labelled, next to
    capture crops of the hard families (gold, silver, ice, glossy ball) -> previews/material_presets.png."""
    sys.path.insert(0, HERE)
    import importlib
    mod = importlib.import_module("items._materials")
    usdz = os.path.join(OUT, "_materials.usdz")
    if not os.path.exists(usdz):
        raise SystemExit("run build.py _materials first")
    W_u, H_u = mod.COLS * mod.STEP + 0.4, 3 * mod.STEP + 0.4
    o = os.path.join(PREV, "_materials_board.png")
    s = base_scene(o, int(W_u * PX_PER_UNIT) * SS, int(H_u * PX_PER_UNIT) * SS, top_camera(W_u, W_u / H_u), shadow_half=W_u / 2 + 0.3)
    s["items"] = [dict(usdz=usdz, matrix=np.eye(4).reshape(-1).tolist())]
    # the JSON re-centres on the centre of mass; the grid is symmetric so the origin stays put
    run_job([s], "materials")
    im = downsample(o).convert("RGB")
    dr = ImageDraw.Draw(im)
    for i, (label, m) in enumerate(mod.SWATCHES):
        x = (i % mod.COLS - (mod.COLS - 1) / 2) * mod.STEP
        z = (i // mod.COLS - 1) * mod.STEP
        px = im.width / 2 + x * PX_PER_UNIT; py = im.height / 2 + z * PX_PER_UNIT
        dr.text((px - 60, py + mod.R * PX_PER_UNIT + 2), label, fill=(240, 240, 240), font=_font(15))
    refs = [os.path.join(RESEARCH, "items", f) for f in ("gold-bell-a.png", "gold-trumpet-a.png", "disco-ball-a.png",
                                                        "microphone-a.png", "ice-cube-a.png", "bowling-ball-blue.png")]
    ref_ims = [fit(Image.open(r).convert("RGB"), 200) for r in refs if os.path.exists(r)]
    W = max(im.width, sum(r.width + 6 for r in ref_ims))
    sheet = Image.new("RGB", (W, im.height + 236), (24, 26, 30))
    sheet.paste(im, (0, 0))
    ImageDraw.Draw(sheet).text((6, im.height + 6), "capture crops (gold, silver, ice, glossy ball) at 200 px/unit:", fill=(200, 200, 200), font=_font(14))
    x = 0
    for r in ref_ims:
        sheet.paste(r, (x, im.height + 30)); x += r.width + 6
    p = os.path.join(PREV, "material_presets.png")
    sheet.save(p)
    os.remove(o)
    print("materials:", p)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("items", nargs="*", help="item ids or recipe names (a recipe expands to all its variants)")
    ap.add_argument("--sheet", action="store_true", help="stack the per-item rows into previews/contact_<name>.png")
    ap.add_argument("--name", default=None, help="contact sheet name")
    ap.add_argument("--board", action="store_true")
    ap.add_argument("--icons", action="store_true")
    ap.add_argument("--no-turntable", action="store_true")
    ap.add_argument("--rig", action="store_true", help="rewrite the rig assets (env, floor, tray tile)")
    ap.add_argument("--materials", action="store_true", help="material-family swatches (build.py _materials first)")
    a = ap.parse_args()
    make_rig_assets(force=a.rig)
    ids = resolve_ids(a.items)
    for n in ids:
        item_previews(n, turntable=not a.no_turntable)
    if a.sheet:
        contact_sheet(ids, a.name)
    if a.materials:
        material_swatches()
    if a.board:
        board_mock()
    if a.icons:
        icon_sheet(ids or ["rubber_duck", "strawberry", "toy_hammer"])
    if ids:
        from build import write_catalog
        write_catalog(OUT)


if __name__ == "__main__":
    main()
