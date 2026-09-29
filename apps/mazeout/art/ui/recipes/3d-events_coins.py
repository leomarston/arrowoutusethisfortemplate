"""3d-events lane: the gold coin and everything built from it -- the prize bowl (coinBowl) and the six shop coin
packs (coinPackTiny .. coinPackGiant).

References (LOOKED AT only, never traced or sampled into an asset): the Claw ladder card on research/shots/023 (bowl,
"10000"), the Streak Race rows on meta-045 (bowl, "2000"), the shop coin grid on meta-011 (the six piles).
Measured there (pt, 393 pt screen):
  coin      diameter ~24-26 pt in the shop piles, ~24 pt in the bowl; thickness 0.23-0.25 of the diameter; a raised lip
            ring (~0.26 R wide), a shallow recessed field and a chunky rounded 5-point star; faces bright yellow, the
            rim/side a deeper orange (a hue shift, painted -- STYLE C.1 "painted bevel").
  bowl      a crimson band 68.5 pt wide x ~29 pt tall (023), a lighter top lip, dark inside, 3-5 coins heaped in it, one
            standing on edge at the left; the live amount sits on the band's front (never baked).
  piles     bottom-aligned stacks of 1-8 coins, tallest at the back, 1-3 coins standing on edge in front; seen ~22 deg
            from above (the coin tops read as 0.37 ellipses). bbox (pt): 1000 82x38, 5000 81x46, 10000 81x56,
            25000 98x56, 50000 95x58, 100000 96x62 -> one frame (102 x 66) and ONE world scale for all six, so the pile
            grows from pack to pack exactly like the reference.

Build: the coin is ONE SDF meshed once (cached in build/ui-art/events3d/), then instanced as a premeshed Part (a pile
of 150 coins would be far too slow as one SDF union). The coin's colour is painted through its uv: u = how much the
surface faces along the coin axis (side 0 -> face 1), v = radius / R.
"""
from __future__ import annotations

import functools
import hashlib
import math
import os

import numpy as np

from uikit import (APP, F, SDF, Part, cylinder, extrude, gloss, satin, star2, textured, torus, union, capped_cone,  # noqa: F401
                   rot_x, rot_y, rot_z)

VOXEL = 0.006
CACHE = os.path.join(APP, "build", "ui-art", "events3d")

# ------------------------------------------------------------------ the coin (axis +Y, lying flat, diameter 1)
R = 0.5            # radius
T = 0.165          # half thickness (thickness 0.33 of the diameter: the shop coins read 0.32-0.36, the bowl's 0.28)
EDGE = 0.085       # the rounded edge (the side reads as a band with one bright line, not a tyre)
LIP_IN = 0.34      # the recessed field's radius (the raised lip ring is R - LIP_IN wide)
REC = 0.04         # recess depth
STAR_R = 0.225     # star outer radius

# painted gold (sRGB): the reference's coins shift HUE into their shade (yellow face -> orange edge -> deep orange
# underside), which a PBR falloff on one yellow cannot do (it goes olive) -- STYLE C.1 "painted bevel"
GOLD_FACE = (1.000, 0.735, 0.000)   # #FFBB00 top face
GOLD_FIELD = (1.000, 0.735, 0.000)  # the recessed field (same paint; per-vertex uv on its big flat triangles streaked)
GOLD_SIDE = (1.000, 0.600, 0.000)   # #FF9900 the edge at its equator (the rig adds the bright bulge line)
GOLD_LOW = (0.950, 0.430, 0.000)    # #F26E00 the lower half of the edge
GOLD_DEEP = (0.860, 0.320, 0.000)   # #DB5200 the underside


def _mirror_y(s: SDF) -> SDF:
    f = s.fn
    lo, hi = s.lo.copy(), s.hi.copy()
    m = max(abs(lo[1]), abs(hi[1]))
    lo[1], hi[1] = -m, m

    def fn(p):
        q = p.copy()
        q[:, 1] = np.abs(q[:, 1])
        return f(q)
    return SDF(fn, lo, hi)


def coin_sdf() -> SDF:
    body = cylinder(R, T, round=EDGE)
    # the recessed field on the top face (mirrored to the bottom face below)
    field = cylinder(LIP_IN, 0.2).translate(0, T + 0.2 - REC, 0)
    top = body.subtract(field, k=0.022)
    star = star2(5, STAR_R, STAR_R * 0.56, round=0.07, round_valley=0.05)
    relief = extrude(star, 0.03, round=0.026).rotate_x(-90)      # extrusion axis Z -> Y
    relief = relief.translate(0, T - REC + 0.014, 0)
    shape = union(top, relief, k=0.012)
    return _mirror_y(shape)


def coin_texture():
    """uv: u = n . axis * 0.5 + 0.5 (underside 0, edge 0.5, top face 1), v = radius / R."""
    face, field, side, low, deep = (np.array(c) for c in (GOLD_FACE, GOLD_FIELD, GOLD_SIDE, GOLD_LOW, GOLD_DEEP))

    def ramp(u):
        stops = [(0.0, deep), (0.20, deep), (0.36, low), (0.50, side), (0.70, face), (1.0, face)]
        out = np.zeros(u.shape + (3,))
        for (u0, c0), (u1, c1) in zip(stops[:-1], stops[1:]):
            t = np.clip((u - u0) / max(u1 - u0, 1e-6), 0, 1)
            t = t * t * (3 - 2 * t)
            m = ((u >= u0) & (u <= u1))[..., None]
            out = np.where(m, c0 * (1 - t[..., None]) + c1 * t[..., None], out)
        return out

    def fn(u, v):
        return ramp(np.clip((u - 0.03) / 0.94, 0, 1))
    return fn


def coin_material():
    return textured(gloss("coin_gold", "#FFC400", rough=0.30, ior=1.36), coin_texture(), size=256)


def _src_key():
    import inspect
    src = inspect.getsource(coin_sdf) + repr((R, T, EDGE, LIP_IN, REC, STAR_R))
    return hashlib.sha1(src.encode()).hexdigest()[:10]


@functools.lru_cache(maxsize=4)
def coin_mesh(target=4200, voxel=0.0055):
    """(v, f, n) of one coin, cached on disk by the recipe's coin parameters."""
    os.makedirs(CACHE, exist_ok=True)
    path = os.path.join(CACHE, f"coin_{_src_key()}_{target}_{voxel}.npz")
    if os.path.exists(path):
        d = np.load(path)
        return d["v"], d["f"], d["n"]
    import fast_simplification
    from mesher import _normals, _project, mc_mesh
    s = coin_sdf()
    v, f = mc_mesh(s, voxel)
    if len(f) > target:
        v2, f2 = fast_simplification.simplify(v, f.astype(np.int32), target_count=target, agg=5)
        v, f = np.asarray(v2, np.float64), np.asarray(f2, np.int64)
    v = _project(s, v, eps=0.5 * voxel)
    n = _normals(s, v, eps=0.5 * voxel)
    tmp = path + f".tmp{os.getpid()}.npz"
    np.savez(tmp, v=v, f=f, n=n)
    os.replace(tmp, path)
    return v, f, n


def coins_part(name, poses, scale=1.0):
    """A premeshed Part: one coin mesh instanced at every pose (R 3x3, t 3) -> one mesh, one material."""
    v0, f0, n0 = coin_mesh()
    # keep the uv off the texture's border: the sampler wraps (repeat), so u = 1.0 on a flat face blended the top-face
    # paint with the underside paint at u = 0 -> streaks across every face (seen on the first full renders)
    u0 = 0.03 + 0.94 * (n0[:, 1] * 0.5 + 0.5)
    rad = np.sqrt(v0[:, 0] ** 2 + v0[:, 2] ** 2) / R
    uv0 = np.stack([u0, 0.03 + 0.94 * np.clip(rad, 0, 1)], 1)

    def premesh():
        V, Fc, N, UV = [], [], [], []
        off = 0
        for Rm, t in poses:
            Rm = np.asarray(Rm, float)
            V.append(v0 @ Rm.T * scale + np.asarray(t, float))
            N.append(n0 @ Rm.T)
            Fc.append(f0 + off)
            UV.append(uv0)
            off += len(v0)
        return np.vstack(V), np.vstack(Fc), np.vstack(N), np.vstack(UV)
    p = Part(name, None, coin_material())
    p.__dict__["premesh"] = premesh
    return p


# ------------------------------------------------------------------ poses

def flat(x, z, y=None, yaw=0.0, tilt=(0.0, 0.0), level=0):
    """A coin lying flat, its centre at (x, level * 2T + T, z) unless y is given."""
    Rm = rot_y(yaw)
    if tilt != (0.0, 0.0):
        Rm = rot_x(tilt[0]) @ rot_z(tilt[1]) @ Rm
    return Rm, (x, (level * 2 * T + T) if y is None else y, z)


def upright(x, z, lean=18.0, turn=0.0, spin=0.0, y=None, on=0):
    """A coin standing on its edge facing the viewer (+Z), its top leaning back by `lean` deg, turned by `turn` about
    +Y, the star spun by `spin` about the coin axis. The lowest point of the rim rests on y = 0 unless y is given."""
    Rm = rot_y(turn) @ rot_x(90 - lean) @ rot_y(spin)       # axis +Y -> tilted toward +Z
    # the lowest point: the rim point furthest down along -Y
    a = Rm @ np.array([0, 1.0, 0])
    low = abs(R * math.sqrt(max(0.0, 1 - a[1] ** 2))) + abs(T * a[1])
    return Rm, (x, (low + on * 2 * T) if y is None else y, z)


def stack(x, z, n, seed, jit=0.035, level0=0, tilt=1.8):
    rng = np.random.default_rng(seed)
    out = []
    for i in range(n):
        out.append(flat(x + rng.uniform(-jit, jit), z + rng.uniform(-jit, jit), yaw=rng.uniform(0, 72),
                        tilt=(rng.uniform(-tilt, tilt), rng.uniform(-tilt, tilt)), level=level0 + i))
    return out


# ------------------------------------------------------------------ the shop piles
# Each pile = stacks (x, z, n) on the ground (y = 0), + coins standing on edge in front. Units: coin diameters.
# Our own arrangements in the reference's composition (a mound of stacks, tallest behind, 1-3 coins on edge in front).

PILES = {
    # (x, z, n) stacks + (x, z, lean, turn, spin) coins on edge, in coin diameters; `ref` = the pile's bbox on meta-011
    # in pt (w, h): each pack is fitted to it (the reference draws the bigger heaps with smaller coins: ~25 pt in
    # 1000, ~20 pt in 100000), bottom-aligned in one 102 x 66 frame.
    # 1000: a 4-coin stack in the middle, a 3-stack behind right, a 2-stack + one flat coin left, one coin on edge
    # leaning left of centre, one big coin on edge front right
    "tiny": dict(stacks=[(0.14, 0.10, 4), (-0.88, -0.25, 2), (-0.95, 0.50, 1), (1.12, -0.35, 3), (1.50, 0.35, 2)],
                 up=[(-0.52, 0.42, 16, 36, 10), (1.00, 0.85, 8, -22, 40)], seed=11, ref=(82, 38)),
    # 5000: a 6-stack in the middle, 4 and 5 either side, a low stack at the far left, one coin on edge front left
    "small": dict(stacks=[(0.05, -0.10, 5), (-0.85, 0.05, 4), (0.90, -0.05, 4), (1.30, 0.55, 2), (-1.35, 0.50, 2),
                          (0.25, 0.75, 2)],
                  up=[(-0.70, 0.85, 14, 24, 30)], seed=12, ref=(81, 46)),
    # 10000: a mound -- 8 behind, 6-7 either side, 4-5 in the middle row, a coin on edge at the left
    "medium": dict(stacks=[(0.05, -0.45, 6), (-0.85, -0.30, 5), (0.90, -0.35, 5), (-1.30, 0.35, 3), (-0.40, 0.30, 4),
                           (0.50, 0.35, 4), (1.30, 0.45, 3), (-0.10, 1.00, 1), (0.85, 1.00, 2)],
                   up=[(-0.90, 0.95, 12, 22, 50)], seed=13, ref=(81, 56)),
    # 25000: a wider mound, one coin on edge at the left
    "big": dict(stacks=[(-0.43, -0.60, 6), (0.48, -0.55, 6), (-1.28, -0.20, 4), (1.33, -0.20, 5), (-1.76, 0.50, 2),
                        (-0.86, 0.30, 4), (0.05, 0.25, 5), (0.95, 0.30, 4), (1.76, 0.55, 2), (-1.28, 1.00, 1),
                        (-0.38, 1.05, 2), (0.52, 1.05, 2), (1.38, 1.00, 1)],
                up=[(-1.05, 1.25, 14, 22, 20)], seed=14, ref=(98, 56)),
    # 50000: taller, two coins on edge in front
    "super": dict(stacks=[(-0.43, -0.65, 6), (0.48, -0.60, 6), (-1.28, -0.25, 5), (1.33, -0.25, 6), (-1.76, 0.45, 3),
                          (-0.86, 0.25, 5), (0.05, 0.20, 6), (0.95, 0.25, 5), (1.76, 0.50, 3), (-1.28, 0.95, 2),
                          (-0.38, 1.00, 3), (0.52, 1.00, 2), (1.38, 0.95, 2)],
                  up=[(-0.30, 1.25, 16, 14, 0), (0.85, 1.30, 12, -18, 36), (-0.95, 0.55, 18, 20, 20, 4)], seed=15,
                  ref=(95, 58)),
    # 100000: the biggest heap -- 9-coin columns behind, three coins on edge
    "giant": dict(stacks=[(-0.45, -0.75, 7), (0.50, -0.70, 7), (-1.35, -0.35, 6), (1.40, -0.35, 6), (-1.90, 0.30, 4),
                          (-0.90, -0.05, 7), (0.05, -0.10, 7), (1.00, -0.05, 6), (1.90, 0.35, 4), (-1.40, 0.60, 4),
                          (-0.45, 0.55, 5), (0.50, 0.60, 5), (1.45, 0.65, 4), (-1.90, 1.10, 1), (-0.95, 1.15, 2),
                          (0.00, 1.20, 3), (0.95, 1.15, 2), (1.90, 1.10, 1)],
                  up=[(-1.20, 1.35, 14, 20, 12), (1.30, 1.40, 10, -18, 50), (0.95, 0.30, 20, -14, 30, 5)], seed=16,
                  ref=(96, 62)),
}


def pile_poses(name):
    P = PILES[name]
    poses = []
    for i, (x, z, n) in enumerate(P["stacks"]):
        poses += stack(x, z, n, seed=P["seed"] * 100 + i)
    for u in P["up"]:
        x, z, lean, turn, spin = u[:5]
        on = u[5] if len(u) > 5 else 0
        if not on:   # slide a standing coin forward until it clears every stack (no coin cut by another)
            for _ in range(40):
                if not _hits(upright(x, z, lean=lean, turn=turn, spin=spin), P["stacks"]):
                    break
                z += 0.05
        poses.append(upright(x, z, lean=lean, turn=turn, spin=spin, on=on))
    return poses


def _disc_points(pose, n=24):
    Rm, t = pose
    th = np.linspace(0, 2 * math.pi, n, endpoint=False)
    pts = []
    for rr in (R, R * 0.6):
        for yy in (-T, T):
            pts.append(np.stack([rr * np.cos(th), np.full(n, yy), rr * np.sin(th)], 1))
    return np.vstack(pts) @ np.asarray(Rm).T + np.asarray(t)


def _hits(pose, stacks, pad=0.02):
    p = _disc_points(pose)
    for (sx, sz, n) in stacks:
        d = np.hypot(p[:, 0] - sx, p[:, 2] - sz)
        if np.any((d < R + pad) & (p[:, 1] < n * 2 * T + pad)):
            return True
    return False


def pile_model(name):
    def model():
        return [coins_part("coins", pile_poses(name))], VOXEL
    return model


# ------------------------------------------------------------------ the prize bowl (coinBowl)
BOWL_R = 1.42          # outer radius of the band (coin diameters): 68.5 pt wide for a ~24 pt coin (023)
BOWL_H = 0.80          # band height: the band's front is about 0.9 of a coin diameter tall
BOWL_T = 0.14          # wall thickness
FILL_Y = 0.80          # the heap's hidden bed inside the band
BOWL_RED = "#D6124F"   # crimson band face (023: #D0104A..#E0255E lit, #A00A3A below)
BOWL_LIP = "#FF6A96"   # the lighter top lip
BOWL_IN = "#A0082F"    # inside of the wall


def bowl_parts():
    outer = cylinder(BOWL_R, BOWL_H / 2, round=0.12)
    inner = cylinder(BOWL_R - BOWL_T, BOWL_H, round=0.0)
    band = outer.subtract(inner, k=0.06).translate(0, BOWL_H / 2, 0)
    lip = torus(BOWL_R - BOWL_T / 2, BOWL_T / 2 + 0.014).translate(0, BOWL_H - 0.045, 0)
    bed = cylinder(BOWL_R - BOWL_T - 0.005, 0.05).translate(0, FILL_Y - 0.10, 0)
    return [Part("band", band, gloss("bowl_red", BOWL_RED, rough=0.34, ior=1.40)),
            Part("lip", lip, gloss("bowl_lip", BOWL_LIP, rough=0.30, ior=1.40), voxel=0.006),
            Part("bed", bed, satin("bowl_bed", "#C76400"))]


def bowl_coin_poses():
    """The heap (our arrangement in the reference's composition, 023/meta-045): a bed of flat coins at the rim, a short
    stack at the right, a coin standing on edge at the upper left, one tilted toward the viewer behind it to the right,
    one tilted forward in the front middle (half under the band's lip)."""
    P = []
    y0 = FILL_Y - 0.05 + T
    for (x, z, yaw, tl) in [(-0.75, -0.55, 10, (4, -3)), (0.20, -0.75, 40, (-5, 3)), (0.95, -0.40, 5, (3, 6)),
                            (-0.95, 0.30, 60, (-6, 2)), (-0.10, 0.10, 25, (5, -4)), (0.80, 0.45, 70, (-3, -5)),
                            (-0.35, 0.75, 15, (8, 3))]:
        P.append(flat(x, z, y=y0, yaw=yaw, tilt=tl))
    for i, (yaw, tl) in enumerate([(17, (6, 5))]):
        P.append(flat(0.95, 0.00, y=y0 + 2 * T * (i + 1), yaw=yaw, tilt=tl))                        # the right stack
    P.append(flat(-0.15, -0.35, y=y0 + 2 * T + 0.05, yaw=5, tilt=(10, 4)))
    P.append(flat(0.45, -0.35, y=1.48, yaw=41, tilt=(62, -22)))                  # back right, tilted to the viewer
    P.append(upright(-0.45, 0.10, lean=12, turn=26, spin=10, y=1.50))            # standing on edge, upper left
    P.append(flat(0.05, 0.62, y=0.86, yaw=12, tilt=(48, -6)))                    # front middle, tilted forward
    return P


def bowl_model():
    return bowl_parts() + [coins_part("coins", bowl_coin_poses())], VOXEL


def single_coin_model():
    return [coins_part("coin", [flat(0, 0)])], VOXEL


MODELS = {
    "coin": single_coin_model,
    "bowl": bowl_model,
    **{f"pile_{k}": pile_model(k) for k in PILES},
}

# a warmer fill than the default UI rig: the gold's shade stays orange instead of going olive
COIN_LIGHT = dict(fill_color=(1.0, 0.78, 0.45), fill_lux=700.0, key_lux=3400.0, ibl_exp=-0.45)

def base_shadow(im, color=(122, 44, 0), alpha=0.30, h_frac=0.16, blur_frac=0.05):
    """A soft elliptical contact shadow under the pile's base (the reference piles sit on a faint warm shadow)."""
    from PIL import Image as _I, ImageDraw as _D, ImageFilter as _F
    a = np.asarray(im.getchannel("A"))
    ys, xs = np.nonzero(a > 40)
    if not len(xs):
        return im
    x0, x1, y1 = int(xs.min()), int(xs.max()), int(ys.max())
    w = x1 - x0; h = max(4, int((y1 - int(ys.min())) * h_frac))
    sh = _I.new("L", im.size, 0)
    _D.Draw(sh).ellipse([x0 + 0.02 * w, y1 - h * 0.75, x1 - 0.02 * w, y1 + h * 0.25], fill=int(255 * alpha))
    sh = sh.filter(_F.GaussianBlur(max(1.0, blur_frac * w)))
    # director r2 (grader B): the blurred pool ran past the frame's bottom edge (bottom-row alpha up to ~75/255), which
    # draws a faint hard line on the shop card -- fade it to 0 over the last 2 pt of the frame
    ramp = np.clip((im.size[1] - 1 - np.arange(im.size[1])) / 6.0, 0, 1)[:, None]
    sh = _I.fromarray((np.asarray(sh).astype(np.float32) * ramp).astype(np.uint8), "L")
    base = _I.new("RGBA", im.size, color + (0,))
    base.putalpha(sh)
    base.alpha_composite(im)
    return base


# one frame for all six packs; each pile is fitted to its measured bbox (PILES[..]["ref"]) and stands on one baseline
PACK_VIEW = (0.0, 17.0)   # the coin tops read as 0.28-0.30 ellipses
PACK_FRAME = (102, 66)
PACK_BASE = 2.0   # pt between the pile's lowest point and the frame bottom


def _pack(name):
    w, h = PILES[name]["ref"]
    W, H = PACK_FRAME
    nh = h
    ay = (H - PACK_BASE - nh) / max(1e-6, H - nh)
    return dict(scene=[(f"pile_{name}", dict(center=False))], view=PACK_VIEW, frame=PACK_FRAME, fov=16,
                fill=(w / W, h / H), align=(0.5, ay), light=COIN_LIGHT, post_fit=base_shadow)


ASSETS = {
    # 023: the bowl + heap measure 69 x 56 pt; frame 74 x 62, fitted to that bbox and centred
    "coinBowl": dict(scene=[("bowl", dict(center=False))], view=(0.0, 12.0), frame=(74, 62), fill=(69 / 74, 56 / 62),
                     fov=16, align=(0.5, 0.5), light=COIN_LIGHT),
    "coinPackTiny": _pack("tiny"),
    "coinPackSmall": _pack("small"),
    "coinPackMedium": _pack("medium"),
    "coinPackBig": _pack("big"),
    "coinPackSuper": _pack("super"),
    "coinPackGiant": _pack("giant"),
}
