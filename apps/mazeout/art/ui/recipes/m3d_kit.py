"""missing-3d lane kit: shared helpers for the lane's recipes (m3d_shop.py, m3d_events.py, m3d_fx.py).

Not a recipe (no ASSETS / BUILDS table). The lane's recipes are BUILD modules in the scene lane's format
({manifest id: fn(ctx) -> PIL RGBA at exactly frame x 3}) rendered through scene_kit (per-model mesh cache, one
mfrender job per batch); the driver is m3d_make.py.

What is shared (read-only reuse, never edited from here):
  * the shop's gold coin (art/ui/recipes/3d-events_coins.py: one SDF coin meshed once, painted gold through its uv)
    so every coin in the shop -- the coin packs and the bundles -- is the same coin;
  * the painted toy materials of the 3d-hud lane (art/ui/recipes/3d-hud_props.py: `tpart` + SCHEMES) and its heart
    body (heartBig is the same heart family as heartInfinite / heartBroken).

Every capture (research/shots, the owner's videos) is LOOKED AT only: shapes and colours here are hand-written numbers
measured in pt on gridded crops; nothing is traced, sampled into an asset or reused.
"""
from __future__ import annotations

import importlib.util
import math
import os
import sys

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import scene_kit as K  # noqa: E402
import ui3d  # noqa: E402  (scene_kit puts art/ui/tools on the path)
from sdf import F, rot_align  # noqa: E402

APP = K.APP
UI_OUT = os.path.join(K.UI, "out")      # UI props (B3): art/ui/out/<id>@3x.png
ART_OUT = K.OUT                          # scenes (C1): art/out/<id>@3x.png


def _load(fname, modname):
    if modname in sys.modules:
        return sys.modules[modname]
    spec = importlib.util.spec_from_file_location(modname, os.path.join(HERE, fname))
    m = importlib.util.module_from_spec(spec)
    sys.modules[modname] = m
    spec.loader.exec_module(m)
    return m


EC = _load("3d-events_coins.py", "m3d_evcoins")     # the shop coin (coins_part, flat, upright, stack, PILES ...)
HP = _load("3d-hud_props.py", "m3d_hudprops")       # tpart, SCHEMES, heart_body

T = EC.T            # coin half thickness (coin diameter = 1 world unit)
R = EC.R


# ------------------------------------------------------------------ coin placement (coin diameter = 1)

def orient(n, spin=0.0):
    """Rotation taking the coin axis (+Y) to the unit vector n, spun by `spin` deg about n."""
    n = np.asarray(n, float)
    n = n / np.linalg.norm(n)
    return rot_align((0, 1, 0), n) @ K.rot_y(spin)


def heap_poses(cx, cz, rx, rz, h, y0=0.0, spacing=0.56, seed=0, face=0.35, tilt=22.0, view=(0.0, 0.42, 1.0),
               clip=None, lift=0.0, power=0.5, depth=0.0):
    """Coins lying on a dome (centre (cx, y0, cz), radii rx / rz, height h): a jittered hex grid over the ellipse, each
    coin's axis = the dome normal, blended toward the viewer by `face` (the reference heaps show many star faces) and
    tilted at random by up to `tilt` deg. `clip(x, z) -> bool` drops points (e.g. behind a wall). `power` < 0.5 makes a
    flatter-topped mound (a pile of coins, not a hemisphere)."""
    rng = np.random.default_rng(seed)
    v = np.asarray(view, float)
    v /= np.linalg.norm(v)
    out = []
    dz = spacing * math.sqrt(3) / 2
    nz = int(2 * rz / dz) + 2
    nx = int(2 * rx / spacing) + 2
    for j in range(-nz // 2 - 1, nz // 2 + 2):
        for i in range(-nx // 2 - 1, nx // 2 + 2):
            x = cx + (i + 0.5 * (j % 2)) * spacing + rng.uniform(-0.12, 0.12) * spacing
            z = cz + j * dz + rng.uniform(-0.12, 0.12) * spacing
            u, w = (x - cx) / rx, (z - cz) / rz
            r2 = u * u + w * w
            if r2 > 0.97:
                continue
            if clip is not None and clip(x, z):
                continue
            s = max(1e-3, 1 - r2)
            y = y0 + h * s ** power
            dydr = h * power * s ** (power - 1)
            gx, gz = -dydr * 2 * u / rx, -dydr * 2 * w / rz
            n = np.array([-gx, 1.0, -gz])
            n /= np.linalg.norm(n)
            f = np.clip(face + rng.uniform(-0.2, 0.25), 0, 0.9)
            n = n * (1 - f) + v * f
            n /= np.linalg.norm(n)
            a = math.radians(rng.uniform(-tilt, tilt))
            b = math.radians(rng.uniform(0, 360))
            k = np.array([math.cos(b), 0, math.sin(b)])
            n = n * math.cos(a) + np.cross(k, n) * math.sin(a)
            n /= np.linalg.norm(n)
            Rm = orient(n, rng.uniform(0, 72))
            p = np.array([x, y + lift, z]) + n * T * 0.5 - n * rng.uniform(0, depth)
            out.append((Rm, tuple(p)))
    return out


def heap_core(name, cx, cz, rx, rz, h, y0=0.0, color="#E08E08", shrink=0.30, power=0.5):
    """A solid mound under a heap_poses() coin layer (same dome profile y0 + h (1 - r^2)^power, shrunk by `shrink`),
    so the gaps between the coins read as more gold, not as the card behind (the heaps are one coin layer deep)."""
    from scene_kit import Part, satin
    rx2, rz2, h2 = max(0.2, rx - shrink), max(0.2, rz - shrink), max(0.2, h - shrink)

    def fn(p):
        u = (p[:, 0] - cx) / rx2
        w = (p[:, 2] - cz) / rz2
        r2 = u * u + w * w
        ys = y0 + h2 * np.clip(1 - r2, 0, 1) ** power
        d_top = (p[:, 1] - ys) * 0.45
        d_side = (np.sqrt(r2) - 1) * min(rx2, rz2) * 0.9
        return np.maximum(np.maximum(d_top, d_side), y0 - p[:, 1]).astype(F)
    from sdf import SDF as _SDF
    sd = _SDF(fn, np.array([cx - rx2 - 0.1, y0 - 0.1, cz - rz2 - 0.1]), np.array([cx + rx2 + 0.1, y0 + h2 + 0.1, cz + rz2 + 0.1]))
    return Part(name, sd, satin(name + "_gold", color, rough=0.45), voxel=0.05)


def stack(x, z, n, seed, y0=0.0, jit=0.035, tilt=1.8):
    """A stack of n flat coins standing on y0."""
    rng = np.random.default_rng(seed)
    out = []
    for i in range(n):
        Rm, t = EC.flat(x + rng.uniform(-jit, jit), z + rng.uniform(-jit, jit), yaw=rng.uniform(0, 72),
                        tilt=(rng.uniform(-tilt, tilt), rng.uniform(-tilt, tilt)), level=i)
        out.append((Rm, (t[0], t[1] + y0, t[2])))
    return out


def facing(x, y, z, lean=14.0, turn=0.0, spin=0.0):
    """A coin standing up and facing the viewer (+Z), centre at (x, y, z), its top leaning back by `lean` deg."""
    Rm = K.rot_y(turn) @ K.rot_x(90 - lean) @ K.rot_y(spin)
    return Rm, (x, y, z)


def coins(name, poses, scale=1.0):
    return EC.coins_part(name, poses, scale=scale)


# ------------------------------------------------------------------ materials

def painted(name, sdf, scheme, y0, y1, view=(0, 0, 0), rough=0.28, ior=1.42, voxel=None, e0=0.30, e1=0.95,
            opacity=1.0):
    """The 3d-hud lane's painted toy material (3d-hud_props.tpart: colour by height in VIEW space + a hue-shifted edge
    band), with one fix: the uv stays inside 0.02..0.98. The texture sampler WRAPS, so tpart's u = 1 - n.z = 0 on a
    surface facing the camera sampled the far edge colour -> a dark spot at the apex of a dome (heartBig round 3)."""
    from dataclasses import replace
    from sdf import normals as _normals
    from mesher import Material
    R = HP._view(*view)
    sc = SCHEMES[scheme] if isinstance(scheme, str) else scheme

    def uvf(v):
        n = _normals(sdf, v.astype(F), eps=0.003)
        nv = n @ R.T
        yv = (v @ R.T)[:, 1]
        u = np.clip(1 - nv[:, 2], 0, 1)
        vv = np.clip((yv - y0) / (y1 - y0), 0, 1)
        return np.stack([0.02 + 0.96 * u, 0.02 + 0.96 * vv], 1)
    tex = HP.toon_texture(sc, e0, e1)

    def fn(u, v):     # undo the 0.02..0.98 squeeze so the scheme's stops land where tpart puts them
        return tex(np.clip((u - 0.02) / 0.96, 0, 1), np.clip((v - 0.02) / 0.96, 0, 1))
    m = Material(name, sc["mid"], roughness=rough, ior=ior, opacity=opacity)
    m = replace(m, texture=fn, texture_size=128)
    from scene_kit import Part
    return Part(name, sdf, m, uv=("fn", uvf), voxel=voxel)


SCHEMES = dict(HP.SCHEMES)
SCHEMES.update({
    # shop bundle lavender metal (meta-008..010): lit #D9CCF8, face #B9A5EC, shade #8C78D0, edge #7560BE
    "lavender": dict(top="#E2D7FB", mid="#C3B2F1", bot="#A895E2", etop="#9C88DA", ebot="#6F5AB8"),
    # crimson (the sack, barrel, chest, safe interior and cart): lit #F0345E, face #D8123F, shade #A00A2E
    "crimson": dict(top="#F23A5F", mid="#DC1843", bot="#C20F38", etop="#B00C33", ebot="#7E0622"),
    "rope": dict(top="#F9B458", mid="#EE9236", bot="#DE7C26", etop="#C9681C", ebot="#9C4A10"),
    "baseGrey": dict(top="#E7E4F6", mid="#D2CDEB", bot="#BDB6DF", etop="#ABA3D3", ebot="#8B82BE"),
    "gem": dict(top="#FF9AE4", mid="#F25CCB", bot="#D83CB4", etop="#C2309F", ebot="#8E1E78"),
    "wood": dict(top="#C77A4A", mid="#A85C34", bot="#8E4827", etop="#7E3E20", ebot="#5A2A14"),
    "maroon": dict(top="#8A1631", mid="#6E0E25", bot="#5A0A1E", etop="#4E0819", ebot="#360512"),
})


# ------------------------------------------------------------------ light

# the shop renders: the coin packs' warm rig (3d-events COIN_LIGHT on ui3d's warm studio dome), so the bundle coins
# match the coin tiles below them
SHOP_LIGHT = dict(ui3d.RIG, **EC.COIN_LIGHT)


def shop_rig(**kw):
    return K.rig(base=SHOP_LIGHT, env=ui3d.ui_env(), **kw)


# ------------------------------------------------------------------ 2D post (ours)

def twinkles(im, spots, color=(255, 251, 232)):
    """4-point glints (ours, drawn here) at [(x_pt, y_pt, size_pt)] in the frame -- the white star glints the shop
    art carries (meta-007/008/012: 2-4 per piece, static in both captures): two thin rays (size = tip to tip), a hot
    core and a soft halo."""
    W, H = im.size
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    acc = np.zeros((H, W), np.float32)
    for (x, y, s) in spots:
        cx, cy, ss = x * 3, y * 3, s * 3 / 2
        dx, dy = np.abs(xx - cx) / ss, np.abs(yy - cy) / ss
        rh = np.clip(1 - dx, 0, 1) ** 1.6 * np.exp(-(dy / (0.075 * (1.2 - dx.clip(0, 1)))) ** 2)
        rv = np.clip(1 - dy, 0, 1) ** 1.6 * np.exp(-(dx / (0.075 * (1.2 - dy.clip(0, 1)))) ** 2)
        core = np.exp(-(dx * dx + dy * dy) / 0.012)
        halo = np.exp(-(dx * dx + dy * dy) / 0.07) * 0.45
        acc = np.maximum(acc, np.clip(np.maximum(np.maximum(rh, rv), core) + halo, 0, 1))
    ov = np.zeros((H, W, 4), np.float32)
    ov[..., :3] = color
    ov[..., 3] = np.clip(acc, 0, 1) * 255
    out = im.copy()
    out.alpha_composite(Image.fromarray(ov.astype(np.uint8), "RGBA"))
    return out


def contact_shadow(cv, box_pt, color="#7A2C00", alpha=0.28, blur_pt=2.2, squash=0.18):
    """A soft warm elliptical pool under an object whose alpha bbox is box_pt (x0, y0, x1, y1) on Canvas cv."""
    x0, y0, x1, y1 = box_pt
    cx, cy = (x0 + x1) / 2, y1 - 0.5
    rx, ry = (x1 - x0) * 0.50, max(2.0, (y1 - y0) * squash)
    d = K.d_ellipse(cv.X, cv.Y, cx, cy, rx, ry)
    cov = np.clip(0.5 - d / max(blur_pt, 0.5), 0, 1)
    cov = K.blur(cov, blur_pt * 3)
    cv.fill(cov, color, alpha)


def edge_fade(cv, pt=1.5):
    """Nothing may touch the frame edge (checker rule): fade alpha over the outer `pt`."""
    fw, fh = cv.w / 3, cv.h / 3
    e = np.minimum(np.minimum(cv.X, fw - cv.X), np.minimum(cv.Y, fh - cv.Y))
    cv.a[..., 3] *= np.clip((e - 0.3) / pt, 0, 1)


def fit_into(cv, im, box_pt, mode="contain", align=(0.5, 1.0), crop=True):
    """Paste a raw render into box_pt (frame pt) of Canvas cv; returns the pasted alpha bbox in pt."""
    spr, (x, y) = K.fit_box(im, box_pt, mode=mode, align=align, crop=crop)
    cv.over(spr, x=x, y=y)
    return (x / 3, y / 3, (x + spr.width) / 3, (y + spr.height) / 3)
