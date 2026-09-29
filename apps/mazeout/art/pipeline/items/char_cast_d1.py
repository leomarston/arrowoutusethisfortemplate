"""R2 CAST (PLAN-P §4.2; art-direction.md §3.1): the D1 LOADING figures, EVENT figures and the 8 AVATARS, built on
char_boss.boss_v2 and char_crew_d1.digger. Every case renders to art/out/char_<id>@3x.png (+ a <id>.json anchor
sidecar), as the old characters did; nothing references them until A4 maps the ids (build/p/R2/handoff.json).

LOADING (art-direction §3.1 "Loading screen (D1)": the camera looks up a tunnel exit into daylight; the crew BURSTS out
of the ground; R4 LOADING owns the backdrop, the logo slot and the final layout -- `LOADING_LAYOUT` below is the draft):
  bossLoading   the boss behind a mossy rock, a glowing miner's lantern raised high, the other paw pointing the way out,
                laughing (fang), goggles on the brow                                                     (5 figures)
  digCart       a timber mine cart loaded with hand-painted ARROW BOARDS rolling at the camera; a Digger rides its front,
                one paw on the rim, the other flung up
  digFlyer      a Digger tossed up with a big arrow board held overhead, legs dangling, the hard hat flying off
  digPop1       a Digger bursting out of a dig hole (a crater mound), both paws up, laughing
  digPop2       a goggles-down Digger peeking out of a second hole, one paw on the rim, a trowel raised
EVENTS (R8 EVENT-ART composes these on its headers; our own event names, events.md §7.3):
  digClawPair   two Diggers cheering, close-up, cut at the bottom (the claw-machine header)
  digRacers     three Diggers riding mine carts down a rail, near -> far (the streak-race header)
  digBalloon    a Digger waving from a wicker basket, four rope stubs up to R8's balloon (the balloon event)
AVATARS (64 x 64 pt plated portraits; the SAME count and slot order as today's set, AvatarArt.arts; D1 plates):
  avatarMiner (slot of avatarWalkie) · avatarMapper (CapGlasses) · avatarSleuth (Detective) · avatarLunch (Burger) ·
  avatarBoss (Scientist) · avatarConfetti (Party) · avatarStrong (Notebook) · avatarSleepy (BoxHead)
"""
from __future__ import annotations

import math

import numpy as np

import char_boss as CB
import char_crew_d1 as C
import char_d1kit as D
import char_fur as FUR
import char_kit as K
import char_scientist as S
from mesher import Material
from uikit import (Part, box, capsule, capped_cone, cylinder, ellipsoid, extrude, gloss, glass, metal, polygon2,  # noqa: F401
                   round_cone, satin, sphere, torus, union)
from sdf import SDF as _SDF, fillet_points

VOXEL = 0.006
MODELS = {}
ASSETS = {}


def _P(parts):
    """[(name, sdf, mat, voxel)] -> [Part]"""
    return [Part(n, s_, m, voxel=v) for n, s_, m, v in parts]


# ================================================================== props

SANDSTONE = [(0.0, "#FFE8C2"), (0.28, "#F6CE98"), (0.50, "#E4AE72"), (0.72, "#C88A50"), (0.88, "#A0663A"), (1.0, "#6E4020")]
SANDSTONE1 = [(0.0, "#FBDDAE"), (0.28, "#EDBE84"), (0.50, "#D89C60"), (0.72, "#BA7C44"), (0.88, "#935A30"), (1.0, "#64381A")]


def rock(center=(0, 0, 0), scale=1.0, seed=3, moss=True, sand=False):
    """A hewn, mossy BOULDER (R2 v2; v1's smooth lumps + a full moss cap read as a green-topped cake): blended lumps,
    chiselled by 8 smooth planes into facets, a low-frequency value-noise displacement, two or three small moss
    patches on the upper facets. -> [(name, sdf, mat, voxel)]"""
    from sdf import value_noise3
    rng = np.random.default_rng(seed)
    c = np.asarray(center, float)
    R0 = np.array([0.95, 0.52, 0.62])
    lumps = [ellipsoid(*R0).translate(0, 0.40, 0)]
    for _ in range(4):
        p = rng.uniform([-0.55, 0.20, -0.30], [0.55, 0.50, 0.30])
        r = rng.uniform(0.26, 0.40)
        lumps.append(ellipsoid(r * 1.15, r * 0.85, r).translate(*p))
    body = union(*lumps, k=0.18)
    for _ in range(8):                  # chisel facets: planes cutting ~0.07 into the support along random directions
        n = K.unit(rng.normal(0, 1, 3) * np.array([1.0, 0.7, 0.8]) + np.array([0.0, 0.45, 0.25]))
        sup = float(np.sqrt(((R0 * n) ** 2).sum())) + 0.40 * n[1]
        d = sup - rng.uniform(0.05, 0.10)
        nn = n.astype(np.float32)
        plane = _SDF(lambda q, nn=nn, d=d: (q @ nn - np.float32(d)).astype(np.float32), [-3, -3, -3], [3, 3, 3])
        body = body.intersect(plane, k=0.020 if sand else 0.035)
    body = body.intersect(D.slab_y(0.0, 5.0), k=0.03)
    base = body

    def disp(q, f=base.fn):
        return (f(q) * np.float32(0.9) + np.float32(0.026 if sand else 0.018) * value_noise3(q, freq=5.0, seed=seed)).astype(np.float32)
    body = _SDF(disp, base.lo - 0.03, base.hi + 0.03)
    body = body.scale(scale).translate(*c)
    if sand:      # LOOK-L: a sunlit SANDSTONE boulder in the Loading's warm family (the teal-grey rock read as a grey blob)
        out = [("rock", body, K.skin(f"c_sand{seed}", SANDSTONE, SANDSTONE1, vfn=D.rock_vfn(6.0, seed), rough=0.70, ior=1.3), 0.006)]
    else:
        out = [("rock", body, K.skin(f"c_rock{seed}", D.ROCK, [(0.0, "#7C9A96"), (0.35, "#56777A"), (0.7, "#3A5A60"), (1.0, "#152A30")],
                                     vfn=D.rock_vfn(7.0, seed), rough=0.84, ior=1.3), 0.007)]
    if moss:
        blobs = []
        for _ in range(3):
            a = rng.uniform(-0.9, 0.9)
            p = np.array([0.55 * math.sin(a) * scale, 0.0, 0.25 * math.cos(a) * scale]) + c
            p[1] = c[1] + 0.85 * scale
            blobs.append(sphere(rng.uniform(0.16, 0.24) * scale).translate(*p))
        patch = body.offset(0.014 * scale).subtract(body.offset(-0.002)).intersect(union(*blobs), k=0.03)
        out.append(("moss", patch, K.skin(f"c_moss{seed}", [(0.0, "#8FB45A"), (0.4, "#5E8F36"), (0.8, "#3F6C24"), (1.0, "#244814")],
                                          [(0.0, "#A4C46A"), (0.4, "#709E42"), (0.8, "#4C7A2C"), (1.0, "#2C5218")],
                                          vfn=D.rock_vfn(22.0, seed + 5), rough=0.92, ior=1.2), 0.004))
    return out


def crater(center=(0, 0, 0), r_out=1.05, r_hole=0.62, h=0.36, seed=5, ground=1.55):
    """A dig hole in the GROUND (R2 v2; v1 was a mound ring floating round the belly with the legs showing below it):
    a flat earth patch with an irregular outline (the loading floor's earth; it hides the digger's lower body), a
    thrown-up rim mound round the hole, clods on it, and the hole's dark inner wall. Ground level = local y 0."""
    rng = np.random.default_rng(seed)
    c = np.asarray(center, float)
    ph = rng.uniform(0, 2 * math.pi, 3)
    g = np.float32(ground)

    def patch_fn(q, ph=ph):
        x, y, z = q[:, 0], q[:, 1], q[:, 2] * np.float32(1.12)
        th = np.arctan2(z, x)
        r = g * (1 + 0.07 * np.sin(5 * th + ph[0]) + 0.05 * np.sin(9 * th + ph[1]) + 0.03 * np.sin(13 * th + ph[2]))
        return (np.maximum((np.hypot(x, z) - r) * np.float32(0.8), np.abs(y + np.float32(0.02)) - np.float32(0.035))).astype(np.float32)
    patch = _SDF(patch_fn, [-ground * 1.2, -0.1, -ground * 1.1], [ground * 1.2, 0.1, ground * 1.1])
    mound = ellipsoid(r_out, h, r_out * 0.85).intersect(D.slab_y(0.0, 3.0), k=0.02)
    hole = cylinder(r_hole, 1.2).translate(0, 0.0, 0)
    ground_all = union(patch, mound, k=0.12).subtract(hole, k=0.08)
    floor = cylinder(r_hole + 0.02, 0.012).translate(0, -0.06, 0)       # the hole's dark depth, seen round the digger
    clods = []
    for i in range(10):
        a = rng.uniform(0, 2 * math.pi)
        rr = rng.uniform(r_hole + 0.08, r_out * 1.2)
        y = h * math.sqrt(max(0.0, 1 - (min(rr, r_out) / r_out) ** 2)) + 0.01
        s_ = rng.uniform(0.045, 0.085)
        clods.append(ellipsoid(s_, s_ * 0.8, s_ * 0.9).translate(math.cos(a) * rr, y, math.sin(a) * rr * 0.85))
    earth = K.skin(f"c_earth{seed}", D.EARTH, D.EARTH1, vfn=D.rock_vfn(9.0, seed), rough=0.9, ior=1.2)
    return [("ground", ground_all.translate(*c), earth, 0.007),
            ("clods", union(*clods).translate(*c), K.skin(f"c_clod{seed}", D.EARTH, None, vfn=None, rough=0.9, ior=1.2), 0.004),
            ("holeFloor", floor.translate(*c), K.skin(f"c_hole{seed}", [(0.0, "#3A2414"), (0.5, "#24160C"), (1.0, "#120A04")], None,
                                                     vfn=None, rough=0.95, ior=1.1), 0.006)]


GROUND_PARTS = {"ground", "clods", "holeFloor"}


def clip_below(parts, y0, keep=GROUND_PARTS):
    """Cut every part (but `keep`) below the ground plane y0: SDF parts are intersected with the half-space, premeshed
    fur drops every triangle with a vertex below it (the digger's lower body is IN the ground: nothing of it may show
    under the dirt patch -- R2 v2 showed the legs under a floating ring)."""
    out = []
    for p in parts:
        if p.name in keep:
            out.append(p)
            continue
        if p.sdf is not None and float(p.sdf.hi[1]) <= y0 + 0.01:
            continue                                  # wholly under the ground (belt, soles, toe claws)
        out.append(p)
        if p.sdf is not None:
            p.sdf = p.sdf.intersect(D.slab_y(y0, 8.0), k=0.004)
        pre = p.__dict__.get("premesh")
        if pre is not None:
            def fn(pre=pre):
                v, f, n, uv = pre()
                v = np.asarray(v)
                f = np.asarray(f)
                ok = (v[f][:, :, 1] > y0).all(1)
                if not ok.any():
                    ok[0] = True
                return v, f[ok], n, uv
            p.__dict__["premesh"] = fn
    return out


def mine_cart(center=(0, 0, 0), s=1.0, tag=""):
    """A timber mine cart (a tapered plank tub with iron corner bands + rivets) on four iron wheels.
    Origin: the cart's floor centre; front = +Z. -> [(name, sdf, mat, voxel)]"""
    c = np.asarray(center, float)
    top_w, top_d, bot_w, bot_d, hgt = 0.92, 0.58, 0.78, 0.48, 0.78

    lo_b = [-top_w - 0.15, -0.15, -top_d - 0.15]
    hi_b = [top_w + 0.15, hgt + 0.15, top_d + 0.15]

    def tub(off=0.0):
        # a tapered box: the intersection of 4 slanted half-spaces + top/bottom (Lipschitz ~1)
        kx = (top_w - bot_w) / hgt
        kz = (top_d - bot_d) / hgt

        def f(p):
            y = p[:, 1]
            wx = bot_w + kx * np.clip(y, 0, hgt) + off
            wz = bot_d + kz * np.clip(y, 0, hgt) + off
            dx = (np.abs(p[:, 0]) - wx) * 0.97
            dz = (np.abs(p[:, 2]) - wz) * 0.97
            dy = np.maximum(-y - off, y - hgt - off)
            q = np.stack([dx, dy, dz], 1)
            out = np.linalg.norm(np.maximum(q, 0), axis=1) + np.minimum(q.max(1), 0)
            return out.astype(np.float32)
        return _SDF(f, lo_b, hi_b)
    outer = tub(0.0)
    inner = tub(-0.07).translate(0, 0.10, 0)
    shell = outer.subtract(inner).offset(0.012)
    planks = []
    for yy in (0.20, 0.40, 0.60):        # plank seams: thin grooves round the tub
        planks.append(outer.offset(0.02).subtract(outer.offset(-0.02)).intersect(D.slab_y(yy - 0.008, yy + 0.008)))
    seams = union(*planks)
    shell = shell.subtract(seams, k=0.004)
    bands = []
    for sx in (-1, 1):
        for sz in (-1, 1):
            corner = capsule((sx * (bot_w + 0.01), 0.0, sz * (bot_d + 0.01)), (sx * (top_w + 0.01), hgt, sz * (top_d + 0.01)), 0.045)
            bands.append(corner)
    # the rim: a band round the tub's MOUTH only (R2 v1 kept the box's top face in the band = a closed dark lid)
    mouth = union(inner, inner.translate(0, 0.30, 0))
    rim = outer.offset(0.03).subtract(outer.offset(-0.03)).intersect(D.slab_y(hgt - 0.05, hgt + 0.03)).subtract(mouth)
    bands.append(rim)
    rivets = []
    for sx in (-1, 1):
        for yy in (0.15, 0.40, 0.65):
            wz = bot_d + (top_d - bot_d) * yy / hgt
            wx = bot_w + (top_w - bot_w) * yy / hgt
            rivets.append(sphere(0.022).translate(sx * (wx - 0.06), yy, wz + 0.05))
    wheels, axles = [], []
    for sx in (-1, 1):
        for sz in (-1, 1):
            wc = np.array([sx * (bot_w + 0.02), -0.06, sz * 0.36])
            Rw = K.frame_from([1, 0, 0], [0, 0, 1])
            wheels.append(union(cylinder(0.24, 0.045, round=0.02).transform(Rw).translate(*wc),
                                cylinder(0.27, 0.018, round=0.008).transform(Rw).translate(*(wc - np.array([sx * 0.05, 0, 0])))))
            axles.append(cylinder(0.06, 0.06, round=0.02).transform(Rw).translate(*(wc + np.array([sx * 0.05, 0, 0]))))
    xf = lambda q: q.scale(s).translate(*c) if s != 1.0 else q.translate(*c)   # noqa: E731
    wood = K.skin(f"c_cartwood{tag}", D.WOOD0, D.WOOD1, vfn=D.grain_vfn(20, 0, 7), rough=0.64, ior=1.25)
    iron = K.skin(f"c_iron{tag}", C.IRON_LUT, None, vfn=None, rough=0.40, ior=1.45)
    return [("cartTub", xf(shell), wood, 0.007 * max(s, 0.6)),
            ("cartBands", xf(union(*bands)), iron, 0.004 * max(s, 0.6)),
            ("cartRivets", xf(union(*rivets)), K.skin(f"c_crivet{tag}", D.BRASS_LUT, None, rough=0.3, ior=1.5), 0.003 * max(s, 0.6)),
            ("cartWheels", xf(union(*wheels, *axles)), iron, 0.004 * max(s, 0.6))]


def wicker_basket(center=(0, 0, 0), r=0.62, h=0.62):
    """A wicker balloon basket: a rounded box of woven rings (horizontal ribs) with a leather-bound rim and four rope
    stubs rising from the rim corners (R8 hangs the envelope on them)."""
    c = np.asarray(center, float)
    outer = box(r, h / 2, r * 0.9, round=0.10).translate(0, h / 2, 0)
    inner = box(r - 0.06, h / 2, r * 0.9 - 0.06, round=0.07).translate(0, h / 2 + 0.06, 0)
    shell = outer.subtract(inner)
    ribs = union(*[outer.offset(0.012).subtract(outer.offset(-0.02)).intersect(D.slab_y(yy - 0.012, yy + 0.012))
                   for yy in np.linspace(0.08, h - 0.08, 6)])
    rim = outer.offset(0.03).subtract(outer.offset(-0.03)).intersect(D.slab_y(h - 0.03, h + 0.035)).subtract(
        union(inner, inner.translate(0, 0.3, 0)))                      # a band round the mouth, not a lid
    ropes = union(*[capsule((sx * (r - 0.06), h + 0.02, sz * (r * 0.9 - 0.06)), (sx * (r - 0.02), h + 0.62, sz * (r * 0.9 - 0.02)), 0.018)
                    for sx in (-1, 1) for sz in (-1, 1)])
    weave = K.skin("c_wicker", [(0.0, "#F2CF8E"), (0.4, "#DDAE62"), (0.75, "#B98542"), (1.0, "#7A5424")],
                   [(0.0, "#E6BC76"), (0.4, "#C9964C"), (0.75, "#A07032"), (1.0, "#6A461C")], vfn=D.grain_vfn(90, 1, 11),
                   rough=0.78, ior=1.2)
    return [("basket", shell.translate(*c), weave, 0.006),
            ("basketRibs", ribs.translate(*c), weave, 0.004),
            ("basketRim", rim.translate(*c), K.skin("c_brim", D.LEATHER, None, rough=0.5, ior=1.25), 0.004),
            ("ropes", ropes.translate(*c), K.skin("c_rope", [(0.0, "#F4E4C0"), (0.5, "#D8C090"), (1.0, "#9E8456")], None,
                                                   vfn=None, rough=0.8, ior=1.2), 0.003)]


def boards(specs, tag=""):
    """Several arrow boards: specs = [(paint, center, up, face, length, width)], each with its own frame."""
    out = []
    for i, (paint, c, up, face, L, W) in enumerate(specs):
        R = K.frame_from(up, face)
        for n, s_, m, v in D.arrow_board(paint, length=L, width=W, shaft=W * 0.54, head_len=L * 0.42, depth=0.11,
                                         seed=i + 3 + (7 if tag else 0), R=R, t=np.asarray(c, float)):
            out.append((f"{n}{tag}{i}", s_, m, v))
    return out


def flying_hat(center, R, gloss_=False):
    """The hard hat (lamp + goggles) detached, flying: world frame R about center."""
    out = []
    for n, s_, m, v in C.hard_hat(center=(0, 0, 0), tilt=0.0, roll=0.0, lamp=True, goggles=True, gloss_=gloss_):
        out.append((n, s_.transform(np.asarray(R, float)).translate(*np.asarray(center, float)), m, v))
    return out


# ================================================================== the boss on the loading screen

CB.POSES["load_d1"] = dict(yaw=16.0, lean=4.0, head=dict(roll=5.0, yaw=12.0, nod=-4.0), narrow=0.92, body_dx=0.0, body_dy=0.0)
_BL_ARMS = dict(
    # the fist closes round the lantern's bail: fingers forward, palm down, so the lantern hangs straight below it
    R=dict(el=(1.42, 1.44, 0.04), wr=(1.20, 1.86, 0.26), d=(-0.20, 0.25, 1.0), palm=(0.0, -1.0, 0.20), r=0.175),
    L=dict(el=(-0.98, 1.04, 0.42), wr=(-0.56, 1.10, 0.86), d=(0.85, 0.05, 0.50), palm=(0.0, -1.0, 0.20), r=0.17),
)


def _boss_loading():
    wr = np.asarray(_BL_ARMS["R"]["wr"], float)
    pc = wr + K.unit(_BL_ARMS["R"]["d"]) * 0.175 * 0.95
    # the bail sits IN the fist: the lantern's origin (the bail's top) a little below the paw centre, hanging down
    lan = D.place_parts(D.lantern(1.45), t=pc + np.array([0.0, -0.06, 0.0]))
    rk = rock(center=(0.10, -0.05, 0.66), scale=0.95, seed=4, moss=False)    # the moss patch read as a flat decal
    ex = _P(lan + rk)
    return CB.boss_v2("load_d1", mouth="open", eyes="open", with_station=False, arms=_BL_ARMS, hands=dict(L="point", R="grip"),
                      extra=ex, look=(0.0, 0.10), view_pose=dict(yaw=0, pitch=4))


MODELS["boss_loading"] = _boss_loading
_BL_FRAME = (210, 250)
_BL_VIEW = K.view_bounds(_BL_FRAME, scale_pt=64.0, center=(0.08, 1.30), zr=(-1.0, 1.4), margin=1.0, fov=22.0)
ASSETS["char_bossLoading"] = dict(scene=[("boss_loading", dict(yaw=0, pitch=4, center=False))], bounds=_BL_VIEW,
                                  frame=_BL_FRAME, fov=22, light=D.LIGHT_D1, no_fit=True,
                                  anchors={"eyeMid": [[0.12, 2.12, 0.55]], "feet": [[0.05, -0.05, 0.62]]})


# ================================================================== Diggers on the loading screen

def _dig(spec, pose, key, n=110000, seed=31, extra=None):
    return C.digger(spec, view_pose=pose, n_strands=n, seed=seed, key=key, extra_parts=extra)


# --- the cart rider: standing in the cart's front, one paw on the front rim, the other flung up; hat lamp on
_CART_Y = 0.55          # the cart floor (the rider's feet)
CART_RIDER = C.spec_with(C.BASE, head=dict(yaw=0.0, roll=-6.0, nod=-4.0), look=(0.0, 0.12), mouth="grin", brows="raised",
                         eyes="open", trowel=False, hat=dict(lamp=True, goggles=True, tilt=-6.0, roll=-8.0),
                         arms=dict(L=dict(el=(-0.70, 1.36, 0.18), wr=(-0.86, 1.72, 0.34), d=(-0.25, 1.0, 0.25),
                                          palm=(0.2, 0.0, 1.0), curl=14.0, spread=28.0),
                                   R=dict(el=(0.62, 0.92, 0.36), wr=(0.46, 0.76, 0.60), d=(0.05, -0.30, 1.0),
                                          palm=(0.0, -1.0, 0.25), curl=95.0, spread=14.0, claw_bend=60.0, claw_len=0.05)))
# the load: three boards standing in the tub behind the rider, heads UP and clear of him (R2 v1's sat low and read as
# wings); bottoms inside the tub, arrowheads above the shoulders / beside the hat
_CART_BOARDS = [("tangerine", (-0.70, 1.30, -0.27), (-0.30, 1.0, 0.0), (0.05, 0.0, 1.0), 1.55, 0.86),
                ("teal", (0.74, 1.28, -0.27), (0.34, 1.0, 0.0), (-0.08, 0.0, 1.0), 1.50, 0.84),
                ("sunflower", (0.02, 1.66, -0.45), (0.02, 1.0, -0.08), (0.0, 0.08, 1.0), 1.70, 0.90)]


def _cart_extra(ctx):
    cart = mine_cart(center=(0.0, 0.0, 0.0), s=1.0)
    # the whole cart sits under the rider: its floor at the rider's feet (y 0) -> translate down the cart height
    moved = [(n, s_.translate(0, -0.12, 0), m, v) for n, s_, m, v in cart]      # the rim at ~0.66: the vest + head show
    return moved + boards(_CART_BOARDS, tag="c")


def _dig_cart():
    parts, vx = _dig(CART_RIDER, dict(yaw=0, pitch=10), key="dig_cart", seed=41, extra=_cart_extra)
    return parts, vx


MODELS["dig_cart"] = _dig_cart
_CART_FRAME = (270, 280)
_CART_VIEW = K.view_bounds(_CART_FRAME, scale_pt=72.0, center=(0.0, 1.10), zr=(-1.2, 1.4), margin=1.0, fov=26.0)
ASSETS["char_digCart"] = dict(scene=[("dig_cart", dict(yaw=-6, pitch=10, center=False))], bounds=_CART_VIEW, frame=_CART_FRAME,
                              fov=26, light=D.LIGHT_D1, no_fit=True,
                              anchors={"eyeMid": [[0.0, 1.72, 0.50]], "feet": [[0.0, -0.30, 0.0]]})

# --- the flyer: tossed up, a big arrow board held overhead, legs dangling, hat flying off
FLYER = C.spec_with(C.BASE, head=dict(yaw=-4.0, roll=8.0, nod=-8.0), look=(0.20, 0.30), mouth="grin", brows="raised", eyes="open",
                    hat=False, trowel=True,
                    arms=dict(L=dict(el=(-0.62, 1.62, 0.25), wr=(-0.30, 1.96, 0.44), d=(0.10, 1.0, 0.05), palm=(0.0, 0.0, -1.0),
                                     curl=95.0, spread=14.0, claw_bend=60.0, claw_len=0.05),
                              R=dict(el=(0.62, 1.62, 0.25), wr=(0.26, 2.04, 0.44), d=(-0.10, 1.0, 0.05), palm=(0.0, 0.0, -1.0),
                                     curl=95.0, spread=14.0, claw_bend=60.0, claw_len=0.05)),
                    legs=dict(L=((-0.27, 0.36, 0.06), (-0.40, 0.06, 0.20), (-0.44, 0.00, 0.26), (-0.2, -0.6, 1.0)),
                              R=((0.27, 0.36, 0.06), (0.36, 0.14, -0.10), (0.40, 0.10, -0.14), (0.2, -0.3, -1.0))))


def _flyer_extra(ctx):
    # the board held overhead by its shaft (both paws on the front of the shaft), head up-right
    b = boards([("coral", (0.10, 2.42, 0.30), (0.30, 1.0, 0.0), (0.0, 0.0, 1.0), 1.30, 0.92)], tag="f")
    hat = flying_hat((-1.00, 2.55, -0.25), K.rotate_matrix((0, 0, 1), 32.0) @ K.rotate_matrix((1, 0, 0), 28.0))
    return b + hat


MODELS["dig_flyer"] = lambda: _dig(FLYER, dict(yaw=10, pitch=6), key="dig_flyer", seed=43, extra=_flyer_extra)
_FL_FRAME = (180, 220)
_FL_VIEW = K.view_bounds(_FL_FRAME, scale_pt=58.0, center=(-0.02, 1.52), zr=(-0.9, 1.1), margin=1.0)
ASSETS["char_digFlyer"] = dict(scene=[("dig_flyer", dict(yaw=10, pitch=6, roll=-14, center=False))], bounds=_FL_VIEW,
                               frame=_FL_FRAME, fov=18, light=D.LIGHT_D1, no_fit=True,
                               anchors={"eyeMid": [[0.0, 1.72, 0.50]]})

# --- the two diggers popping out of dig holes
POP1 = C.spec_with(C.BASE, head=dict(yaw=8.0, roll=-8.0, nod=-6.0), look=(0.10, 0.20), mouth="grin", brows="raised", eyes="open",
                   trowel=False, hat=dict(lamp=True, goggles=True, tilt=-12.0, roll=10.0),
                   arms=dict(L=dict(el=(-0.72, 1.40, 0.16), wr=(-0.70, 1.80, 0.30), d=(-0.05, 1.0, 0.2), palm=(0.2, 0.0, 1.0),
                                    curl=16.0, spread=26.0),
                             R=dict(el=(0.72, 1.40, 0.16), wr=(0.70, 1.80, 0.30), d=(0.05, 1.0, 0.2), palm=(-0.2, 0.0, 1.0),
                                    curl=16.0, spread=26.0)))
POP2 = C.spec_with(C.BASE, girth=0.96, head=dict(yaw=-12.0, roll=6.0, nod=4.0), look=(-0.25, 0.0), mouth="open", brows="raised",
                   eyes="open", trowel=False, fur="sage", goggles_down=True, hat=dict(lamp=False, goggles=False, tilt=-14.0, roll=-6.0),
                   arms=dict(L=dict(el=(-0.70, 1.12, 0.30), wr=(-0.60, 1.04, 0.66), d=(0.05, -0.5, 1.0), palm=(0.0, -1.0, 0.1),
                                    curl=60.0, spread=20.0, claw_bend=55.0, claw_len=0.06),
                             R=dict(el=(0.72, 1.40, 0.16), wr=(0.66, 1.76, 0.32), d=(0.0, 1.0, 0.25), palm=(-0.3, 0.0, 1.0),
                                    curl=95.0, spread=12.0, claw_bend=65.0, claw_len=0.05)))
_POP_Y = 0.78          # the crater rim sits at the belly: the digger's feet are this far below the ground


def _pop_extra(seed, trowel=False):
    def fn(ctx):
        # the ground is at y 0.80 (the digger's feet are down in the hole); the rim rises ~0.29 above it
        out = [(n, s_.translate(0, 0.80, 0), m, v) for n, s_, m, v in crater(center=(0, 0, 0), r_out=1.05, r_hole=0.64, seed=seed, ground=1.30)]
        if trowel:
            pc = ctx["paw"]["R"]
            leaf = polygon2(fillet_points([(0.0, 0.0), (0.09, -0.08), (0.06, -0.24), (0.0, -0.32), (-0.06, -0.24), (-0.09, -0.08)],
                                          [0.02, 0.03, 0.03, 0.02, 0.03, 0.03], n_arc=5))
            R = K.frame_from([0.1, -1.0, 0.1], [0.0, 0.0, 1.0])
            tip0 = pc + np.array([0.0, 0.26, 0.02])
            blade = extrude(leaf, 0.009, round=0.007).transform(R).translate(*tip0)      # the leaf rises from the handle top
            handle = capsule(tuple(pc + np.array([0.0, -0.08, 0.0])), tuple(tip0), 0.030)
            out += [("trowelB", blade, D.painted_metal("c_trowelb", C.STEEL_PAINT, C.STEEL_WORN, blade, rough=0.32, width=0.008), 0.0025),
                    ("trowelH", handle, K.skin("c_trowelh", D.WOOD0, D.WOOD1, vfn=D.grain_vfn(60, 1), rough=0.55, ior=1.25), 0.003)]
        return out
    return fn


def _popped(spec, pose, key, seed, extra):
    parts, vx = _dig(spec, pose, key=key, seed=seed, n=90000, extra=extra)
    return clip_below(parts, _POP_GROUND - 0.02), vx


_POP_GROUND = 0.80
MODELS["dig_pop1"] = lambda: _popped(POP1, dict(yaw=12, pitch=10), "dig_pop1", 47, _pop_extra(5))
MODELS["dig_pop2"] = lambda: _popped(POP2, dict(yaw=-14, pitch=10), "dig_pop2", 53, _pop_extra(8, trowel=True))
_POP_FRAME = (170, 160)
_POP_VIEW = K.view_bounds(_POP_FRAME, scale_pt=54.0, center=(0.0, 1.36), zr=(-1.0, 1.1), margin=1.0)
ASSETS["char_digPop1"] = dict(scene=[("dig_pop1", dict(yaw=12, pitch=10, center=False))], bounds=_POP_VIEW, frame=_POP_FRAME,
                              fov=18, light=D.LIGHT_D1, no_fit=True, anchors={"eyeMid": [[0.0, 1.72, 0.50]]})
ASSETS["char_digPop2"] = dict(scene=[("dig_pop2", dict(yaw=-14, pitch=10, center=False))], bounds=_POP_VIEW, frame=_POP_FRAME,
                              fov=18, light=D.LIGHT_D1, no_fit=True, anchors={"eyeMid": [[0.0, 1.72, 0.50]]})

# draft layout for R4 (frame top-left pt on the 393 x 852 screen, z back -> front); R4 LOADING owns the final one
LOADING_LAYOUT = {
    "char_digPop2": dict(x=228.0, y=430.0, z=-2),
    "char_bossLoading": dict(x=-14.0, y=238.0, z=-1),
    "char_digFlyer": dict(x=208.0, y=168.0, z=0),
    "char_digPop1": dict(x=-14.0, y=532.0, z=1),
    "char_digCart": dict(x=96.0, y=468.0, z=2),
}


# ================================================================== LOOK-L: the Loading figures, VINYL and IN MOTION
# OWNER 2026-09-28 13:56 ("the loading image is not as smooth and good as the original ... it is so obvious") -> the
# LOOK-L rebuild SUPERSEDES the R2 loading Diggers above (kept as data: r2_cast.py reads _CART_BOARDS): the same six
# ids, frames and anchors, re-cast as smooth glossy VINYL toys (char_crew_d1 finish "vinyl": a short wide muzzle with a
# big laugh, 1.45x glossy eyes with two glints, cream sleeves, leather wrist cuffs, laced work boots) under the
# high-key Loading rig (char_d1kit.LIGHT_D1_HK), and doing things with the original's ENERGY but our own actions:
#   char_digCart   a mine cart careening toward the camera, tilted on its wheels, the rider leaning out over the front rim
#                  flinging a paw up; arrow boards rattling in the tub behind him
#   char_digFlyer  a Digger SURFING a big flying arrow board up and out (crouched, arms out for balance), his hard hat
#                  blown off behind him
#   char_digPop2   (the front-right slot) a Digger RUNNING at the camera, an arrow board on his shoulder, the other paw
#                  pumping -- the id stays (A4 integrates by id); the dig hole is gone
#   char_digPop1   (the back-right slot) two Diggers running in, one cheering, one with a shovel on his shoulder
#   char_digDockPair  two tiny Diggers trotting along the dock (a PARTS render: scene_loading_d1.build_dock_pair
#                  hazes it into char_digDockL, so the Loading no longer borrows the furry home rigs)
# Arm points are in the UNLEANED body space (char_crew_d1.BodyXf); props that a paw holds are placed from ctx["paw"].

LOAD_LIGHT = D.LIGHT_D1_HK
VB = C.spec_with(C.BASE, finish="vinyl", snout="muzzle", eye_scale=1.45, eye_lift=0.035, hat_lift=0.05, lids_open=0.98,
                 girth=0.94, mouth="laugh", brows="none", trowel=False, eyes="happy")


def _vdig(spec, pose, key, seed=31, extra=None):
    return C.digger(spec, view_pose=pose, n_strands=0, seed=seed, key=key, extra_parts=extra)


def _world_arm(spec, el, wr, d, palm, **kw):
    """An arm authored in WORLD (after the torso lean: a paw that must land on a rim / a prop) -> the spec's body space."""
    bx = C.BodyXf(spec.get("lean", 0.0), spec.get("twist", 0.0), spec.get("body_roll", 0.0))
    return dict(el=tuple(np.round(bx.inv(el), 4)), wr=tuple(np.round(bx.inv(wr), 4)),
                d=tuple(np.round(np.asarray(d, float) @ bx.R, 4)), palm=tuple(np.round(np.asarray(palm, float) @ bx.R, 4)), **kw)


def _board_at(paint, c, up, face, L, W, tag):
    return [(f"{n}{tag}", s_, m, v) for n, s_, m, v in
            D.arrow_board(paint, length=L, width=W, shaft=W * 0.54, head_len=L * 0.42, depth=0.11, seed=len(tag) + 17,
                          R=K.frame_from(up, face), t=np.asarray(c, float))]


def _eye_anchor(spec):
    """The eye midpoint in model space (the head turns + the torso lean): the layout places a figure by it."""
    hx = C.BodyXf(spec.get("lean", 0.0), spec.get("twist", 0.0), spec.get("body_roll", 0.0)).head(
        C.HeadXf(lift=(spec["height"] - 1.0) * 1.25, **spec["head"]))
    ey = C.EYES[0][1] + spec.get("eye_lift", 0.0)
    return [round(float(v), 4) for v in hx.p(np.array([0.0, ey, 0.50]))]


def dust_post(puffs, lit="#FFF7EA", shade="#E9CFA6"):
    """post_fit: soft sunlit DUST puffs kicked up BEHIND the figure (drawn under it): puffs = [(x, y, r, alpha)] in
    frame pt; each puff is a small cluster of soft discs, lit from the top-left."""
    def fn(im):
        from PIL import Image as _I
        from scipy import ndimage
        W_, H_ = im.size
        yy, xx = np.mgrid[0:H_, 0:W_]
        X, Y = (xx + 0.5) / 3, (yy + 0.5) / 3
        cov = np.zeros((H_, W_))
        tone = np.zeros((H_, W_))
        rng = np.random.default_rng(7)
        for (x, y, r, al) in puffs:
            for _ in range(5):
                cx, cy = x + rng.uniform(-0.7, 0.7) * r, y + rng.uniform(-0.4, 0.3) * r
                rr = r * rng.uniform(0.45, 0.75)
                d = np.hypot(X - cx, Y - cy) / rr
                c = np.clip(1.2 - d, 0, 1) ** 0.8 * al
                cov = np.maximum(cov, c)
                tone = np.maximum(tone, np.clip(1 - np.hypot(X - cx + 0.35 * rr, Y - cy + 0.45 * rr) / rr, 0, 1) * (c > 0))
        cov = ndimage.gaussian_filter(cov, 2.0)
        tone = ndimage.gaussian_filter(tone, 3.0)
        l_, s_ = K.hexrgb(lit), K.hexrgb(shade)
        rgb_ = s_[None, None] + (l_ - s_)[None, None] * np.clip(tone * 1.4, 0, 1)[..., None]
        dust = np.concatenate([rgb_, cov[..., None]], -1)
        d_im = _I.fromarray((np.clip(dust, 0, 1) * 255).astype(np.uint8), "RGBA")
        return _I.alpha_composite(d_im, im.convert("RGBA"))
    return fn


FIST = dict(curl=95.0, spread=10.0, claw_bend=60.0, claw_len=0.05)
OPEN = dict(curl=16.0, spread=28.0)

def sand_boulder(center=(0, 0, 0), scale=1.0, seed=4):
    """LOOK-L: a stylised sunlit SANDSTONE boulder for the Loading boss -- a few big CRISP facets (a cartoon rock reads
    by its light / shadow planes; R2's value-noise lumps read as bread at 1:1), rounded edges, a deeper crease LUT and
    two crack grooves. Origin: the base centre; front = +Z. -> [(name, sdf, mat, voxel)]"""
    rng = np.random.default_rng(seed)
    c = np.asarray(center, float)
    R0 = np.array([0.98, 0.56, 0.64])
    body = union(ellipsoid(*R0).translate(0, 0.42, 0), ellipsoid(0.46, 0.38, 0.40).translate(-0.50, 0.32, 0.10),
                 ellipsoid(0.40, 0.34, 0.36).translate(0.56, 0.30, 0.06), k=0.20)
    for _ in range(11):
        n = K.unit(rng.normal(0, 1, 3) * np.array([1.0, 0.8, 0.9]) + np.array([0.0, 0.5, 0.35]))
        sup = float(np.sqrt(((R0 * n) ** 2).sum())) + 0.42 * n[1]
        d = sup - rng.uniform(0.06, 0.13)
        nn = n.astype(np.float32)
        plane = _SDF(lambda q, nn=nn, d=d: (q @ nn - np.float32(d)).astype(np.float32), [-3, -3, -3], [3, 3, 3])
        body = body.intersect(plane, k=0.010)
    body = body.intersect(D.slab_y(0.0, 5.0), k=0.02)
    cracks = []
    for pts in (((-0.30, 0.72), (-0.19, 0.55), (-0.25, 0.38), (-0.12, 0.22)), ((0.34, 0.66), (0.46, 0.48), (0.40, 0.30))):
        P = np.array([[x, y, K.surface_z_of(body, x, y) + 0.004] for x, y in pts])
        cracks.append(K.limb(P, np.linspace(0.016, 0.008, len(P)), k=0.01))
    body = body.subtract(union(*cracks), k=0.008)
    body = body.scale(scale).translate(*c)
    return [("rock", body, K.skin(f"c_sandb{seed}", SANDSTONE, SANDSTONE1, vfn=D.rock_vfn(2.2, seed), rough=0.62, ior=1.32), 0.006)]


def struck_pickaxe(stuck, hdir, tag=""):
    """A miner's pickaxe struck into the boulder: a curved iron head (one point buried at `stuck`, the other up), a
    honey wood handle along hdir with a brass ferrule. -> [(name, sdf, mat, voxel)]"""
    hd = K.unit(hdir)
    c = np.asarray(stuck, float) + hd * 0.10
    side = K.unit(np.cross(hd, [0.0, 0.0, 1.0]))
    if side[1] < 0:
        side = -side
    tip_up = c + side * 0.30 - hd * 0.06
    tip_in = c - side * 0.24 - hd * 0.10
    head = union(K.limb([tip_in, c, tip_up], [0.016, 0.060, 0.014], k=0.03),
                 round_cone(tuple(c - hd * 0.07), tuple(c + hd * 0.07), 0.066, 0.062), k=0.02)
    handle = capsule(tuple(c), tuple(c + hd * 0.92), 0.040)
    ferrule = round_cone(tuple(c + hd * 0.07), tuple(c + hd * 0.15), 0.050, 0.046)
    return [(f"pickHead{tag}", head, K.skin(f"c_pickiron{tag}", C.IRON_LUT, None, vfn=None, rough=0.34, ior=1.5), 0.0025),
            (f"pickHandle{tag}", handle, K.skin(f"c_pickwood{tag}", D.WOOD0, D.WOOD1, vfn=D.grain_vfn(60, 1), rough=0.5, ior=1.3), 0.003),
            (f"pickFerrule{tag}", ferrule, K.skin(f"c_pickbrass{tag}", D.BRASS_LUT, None, rough=0.26, ior=1.5), 0.0025)]


# --- the boss: the same lantern-raised, this-way pose on his boulder (now sunlit sandstone), with the Loading style
# (char_boss style "load": the lighter pink ladder, a calm velvet face, friendly raised brows) and a smaller open smile
def _boss_loading_hk():
    wr = np.asarray(_BL_ARMS["R"]["wr"], float)
    pc = wr + K.unit(_BL_ARMS["R"]["d"]) * 0.175 * 0.95
    lan = D.place_parts(D.lantern(1.45), t=pc + np.array([0.0, -0.06, 0.0]))
    rk = sand_boulder(center=(0.10, -0.05, 0.66), scale=0.95, seed=4)
    pk = struck_pickaxe((0.66, 0.56, 0.98), (0.78, 0.18, 0.60), tag="b")
    return CB.boss_v2("load_d1", mouth="grin", eyes="open", with_station=False, arms=_BL_ARMS, hands=dict(L="point", R="grip"),
                      extra=_P(lan + rk + pk), look=(0.0, 0.10), view_pose=dict(yaw=0, pitch=4), style="load")


MODELS["boss_loading"] = _boss_loading_hk
ASSETS["char_bossLoading"] = dict(ASSETS["char_bossLoading"], light=LOAD_LIGHT)

# --- the cart: careening at the camera, the rider leaning out over the front rim
LCART_RIDER = C.spec_with(VB, lean=24.0, head=dict(yaw=-4.0, roll=-8.0, nod=-12.0), look=(-0.05, 0.25),
                          hat=dict(lamp=True, goggles=True, tilt=-18.0, roll=-10.0),
                          arms=dict(L=dict(el=(-0.64, 1.42, 0.26), wr=(-0.78, 1.78, 0.46), d=(-0.30, 0.80, 0.45),
                                           palm=(0.25, -0.10, 1.0), **OPEN)))
LCART_RIDER = C.spec_with(LCART_RIDER, arms=dict(R=_world_arm(LCART_RIDER, el=(0.66, 1.02, 0.52), wr=(0.52, 0.78, 0.80),
                                                              d=(0.0, -0.45, 1.0), palm=(0.0, -1.0, 0.15), **FIST)))
_LCART_Z = 0.14
_LCART_BOARDS = [("tangerine", (-0.64, 1.28, _LCART_Z - 0.36), (-0.34, 1.0, -0.05), (0.08, 0.0, 1.0), 1.50, 0.86),
                 ("teal", (0.70, 1.24, _LCART_Z - 0.38), (0.40, 1.0, -0.05), (-0.10, 0.0, 1.0), 1.46, 0.84),
                 ("sunflower", (0.06, 1.62, _LCART_Z - 0.52), (0.10, 1.0, -0.12), (0.0, 0.10, 1.0), 1.66, 0.90)]


def _lcart_extra(ctx):
    cart = [(n, s_.translate(0, -0.12, _LCART_Z), m, v) for n, s_, m, v in mine_cart(center=(0.0, 0.0, 0.0), s=1.0, tag="l")]
    return cart + boards(_LCART_BOARDS, tag="lc")


MODELS["dig_cart"] = lambda: _vdig(LCART_RIDER, dict(yaw=-32, pitch=12), key="lk_cart", seed=41, extra=_lcart_extra)
_CART_POSE = dict(yaw=-32, pitch=12, roll=13, center=False)
_CART_VIEW = K.view_bounds(_CART_FRAME, scale_pt=72.0, center=(-0.16, 1.02), zr=(-1.2, 1.5), margin=1.0, fov=26.0)
ASSETS["char_digCart"] = dict(scene=[("dig_cart", _CART_POSE)], bounds=_CART_VIEW, frame=_CART_FRAME, fov=26, light=LOAD_LIGHT,
                              no_fit=True, anchors={"eyeMid": [_eye_anchor(LCART_RIDER)], "feet": [[0.0, -0.36, _LCART_Z]]},
                              post_fit=dust_post([(226, 246, 14, 0.70), (242, 236, 10, 0.50), (212, 258, 10, 0.55)]))

# --- the flyer: surfing a flying arrow board, crouched, arms out, hat blown off
LFLYER = C.spec_with(VB, lean=6.0, body_roll=-8.0, hat=False, brows="happy", head=dict(yaw=10.0, roll=0.0, nod=-6.0), look=(0.25, 0.05),
                     legs=dict(L=((-0.24, 0.34, 0.06), (-0.42, 0.22, 0.34), (-0.47, -0.05, 0.22), (-0.48, -0.10, 0.29), (-0.3, 0.0, 1.0)),
                               R=((0.24, 0.34, 0.06), (0.42, 0.22, 0.34), (0.47, -0.05, 0.22), (0.48, -0.10, 0.29), (0.3, 0.0, 1.0))),
                     arms=dict(L=dict(el=(-0.80, 1.26, 0.12), wr=(-1.10, 1.42, 0.24), d=(-0.90, 0.35, 0.25), palm=(0.0, -0.2, 1.0), **OPEN),
                               R=dict(el=(0.80, 1.06, 0.16), wr=(1.10, 0.98, 0.30), d=(0.95, -0.15, 0.25), palm=(0.0, -0.3, 1.0), **OPEN)))


def _lflyer_extra(ctx):
    b = _board_at("sunflower", (0.05, -0.30, 0.24), (1.0, 0.0, 0.15), (0.0, 1.0, 0.85), 2.30, 1.20, "fs")
    hat = flying_hat((-0.78, 2.12, 0.05), K.rotate_matrix((0, 0, 1), 34.0) @ K.rotate_matrix((1, 0, 0), 30.0))
    return b + hat


MODELS["dig_flyer"] = lambda: _vdig(LFLYER, dict(yaw=8, pitch=6), key="lk_flyer", seed=43, extra=_lflyer_extra)
_FL_VIEW = K.view_bounds(_FL_FRAME, scale_pt=50.0, center=(-0.24, 1.00), zr=(-1.2, 1.3), margin=1.0)
ASSETS["char_digFlyer"] = dict(scene=[("dig_flyer", dict(yaw=8, pitch=6, roll=24, center=False))], bounds=_FL_VIEW,
                               frame=_FL_FRAME, fov=18, light=LOAD_LIGHT, no_fit=True, anchors={"eyeMid": [_eye_anchor(LFLYER)]})

# --- the runner (front-right slot, id char_digPop2): running at the camera, a board on his shoulder
RUN_LEGS = dict(L=((-0.24, 0.34, 0.10), (-0.30, 0.22, 0.44), (-0.31, -0.10, 0.50), (-0.31, -0.15, 0.60), (0.0, -0.25, 1.0)),
                R=((0.24, 0.34, 0.0), (0.30, 0.04, -0.16), (0.32, 0.02, -0.46), (0.33, 0.07, -0.55), (0.0, 0.55, -1.0)))
RUN_LEGS_B = dict(L=((-0.24, 0.34, 0.0), (-0.30, 0.04, -0.16), (-0.32, 0.02, -0.46), (-0.33, 0.07, -0.55), (0.0, 0.55, -1.0)),
                  R=((0.24, 0.34, 0.10), (0.30, 0.22, 0.44), (0.31, -0.10, 0.50), (0.31, -0.15, 0.60), (0.0, -0.25, 1.0)))
LRUNNER = C.spec_with(VB, lean=14.0, twist=-6.0, head=dict(yaw=12.0, roll=4.0, nod=-6.0), look=(0.10, 0.08),
                      hat=dict(lamp=True, goggles=True, tilt=-14.0, roll=-6.0), legs=RUN_LEGS,
                      arms=dict(L=dict(el=(-0.60, 1.00, 0.36), wr=(-0.50, 1.22, 0.66), d=(0.10, 0.45, 1.0), palm=(0.8, 0.0, 0.2), **FIST),
                                R=dict(el=(0.78, 1.06, -0.04), wr=(0.86, 0.90, 0.28), d=(0.05, -0.15, 1.0), palm=(-1.0, 0.0, 0.1),
                                       curl=70.0, spread=12.0, claw_bend=55.0, claw_len=0.05)))


def _lrunner_extra(ctx):
    """the arrow board tucked under the near arm (pressed to his side by the paw), pointing forward-up"""
    pc = ctx["paw"]["R"]
    return _board_at("tangerine", pc + np.array([-0.10, 0.10, -0.02]), (0.12, 0.88, 0.45), (0.80, 0.0, 0.60), 1.24, 0.76, "rb")


MODELS["dig_pop2"] = lambda: _vdig(LRUNNER, dict(yaw=-32, pitch=8), key="lk_runner", seed=53, extra=_lrunner_extra)
_RUN_VIEW = K.view_bounds(_POP_FRAME, scale_pt=57.0, center=(-0.06, 0.95), zr=(-1.1, 1.4), margin=1.0)
ASSETS["char_digPop2"] = dict(scene=[("dig_pop2", dict(yaw=-32, pitch=8, center=False))], bounds=_RUN_VIEW, frame=_POP_FRAME,
                              fov=18, light=LOAD_LIGHT, no_fit=True, anchors={"eyeMid": [_eye_anchor(LRUNNER)]})

# --- the back-right pair (id char_digPop1): two Diggers running in, one cheering, one with a shovel on his shoulder
LPAIR_A = C.spec_with(VB, lean=12.0, eyes="joy", head=dict(yaw=-8.0, roll=-8.0, nod=-8.0), look=(-0.20, 0.25), legs=RUN_LEGS_B,
                      hat=dict(lamp=True, goggles=False, tilt=-14.0, roll=8.0),
                      arms=dict(L=dict(el=(-0.72, 1.40, 0.16), wr=(-0.78, 1.80, 0.30), d=(-0.10, 1.0, 0.2), palm=(0.2, 0.0, 1.0), **OPEN),
                                R=dict(el=(0.62, 0.98, 0.34), wr=(0.52, 1.18, 0.64), d=(-0.10, 0.45, 1.0), palm=(-0.8, 0.0, 0.2), **FIST)))
LPAIR_B = C.spec_with(VB, lean=10.0, girth=0.98, head=dict(yaw=-14.0, roll=6.0, nod=-6.0), look=(-0.30, 0.10), legs=RUN_LEGS,
                      mouth="laugh", hat=dict(lamp=False, goggles=True, tilt=-10.0, roll=-6.0),
                      arms=dict(L=dict(el=(-0.60, 1.00, 0.36), wr=(-0.50, 1.22, 0.66), d=(0.10, 0.45, 1.0), palm=(0.8, 0.0, 0.2), **FIST),
                                R=dict(el=(0.64, 1.34, 0.00), wr=(0.46, 1.58, 0.14), d=(-0.20, 0.30, 1.0), palm=(-0.6, 0.6, 0.2), **FIST)))


def _pair_b_extra(ctx):
    pc = ctx["paw"]["R"]
    h0 = pc + np.array([0.10, 0.02, -0.62])           # the shaft runs back over the shoulder, the blade behind him
    h1 = pc + np.array([-0.06, 0.02, 0.26])
    ax = K.unit(h1 - h0)
    return shovel(h0, h1, h0 - ax * 0.22, blade_up=ax, blade_face=K.unit([0.2, 1.0, 0.0]), tag="pb")


def shovel(*a, **kw):
    return C.shovel(*a, **kw)


MODELS["dig_pairA"] = lambda: _vdig(LPAIR_A, dict(yaw=-36, pitch=8), key="lk_pairA", seed=47)
MODELS["dig_pairB"] = lambda: _vdig(LPAIR_B, dict(yaw=-36, pitch=8), key="lk_pairB", seed=49, extra=_pair_b_extra)
_PAIR_VIEW = K.view_bounds(_POP_FRAME, scale_pt=40.0, center=(0.20, 1.20), zr=(-1.8, 1.4), margin=1.0)
ASSETS["char_digPop1"] = dict(scene=[("dig_pairA", dict(yaw=-36, pitch=8, pos=(-0.55, 0.0, 0.30), center=False)),
                                     ("dig_pairB", dict(yaw=-36, pitch=8, pos=(0.95, 0.16, -0.70), scale=0.88, center=False))],
                              bounds=_PAIR_VIEW, frame=_POP_FRAME, fov=18, light=LOAD_LIGHT, no_fit=True,
                              anchors={"eyeMid": [_eye_anchor(LPAIR_A)]})

# --- the dock pair (a PARTS render; scene_loading_d1.build_dock_pair hazes it into char_digDockL, 96 x 76 pt)
_DOCK_FRAME = (96, 76)
MODELS["dig_dockA"] = lambda: _vdig(C.spec_with(LPAIR_A, head=dict(yaw=10.0, roll=-6.0, nod=-4.0), look=(0.30, 0.1)),
                                    dict(yaw=40, pitch=8), key="lk_dockA", seed=57)
MODELS["dig_dockB"] = lambda: _vdig(C.spec_with(LRUNNER, head=dict(yaw=12.0, roll=6.0, nod=-4.0), look=(0.30, 0.1)),
                                    dict(yaw=40, pitch=8), key="lk_dockB", seed=59, extra=_lrunner_extra)
_DOCK_VIEW = K.view_bounds(_DOCK_FRAME, scale_pt=17.0, center=(0.10, 1.75), zr=(-1.8, 1.4), margin=1.0)
ASSETS["char_digDockPair"] = dict(scene=[("dig_dockB", dict(yaw=40, pitch=8, pos=(-0.95, 0.0, -0.60), center=False)),
                                         ("dig_dockA", dict(yaw=40, pitch=8, pos=(0.85, 0.0, 0.20), center=False))],
                                  bounds=_DOCK_VIEW, frame=_DOCK_FRAME, fov=18, light=LOAD_LIGHT, no_fit=True, dest="parts")


# ================================================================== LOOK-L FIX ROUND 1 (v3): the judges on v2
# (build/p/LOOK/judge: finish 5.5/10) -- the page was one washed warm family, the arrow boards read as iced gingerbread
# (dough), the four biggest figures were drawn 1.15-1.37x over their file resolution, the boss stood static behind a
# clay boulder, the Digger faces were cloned with dingy cream eyes and heavy lids, the hero did not dominate, the paws
# melted. v3 keeps every id, file size and sidecar key and re-casts them on the new COOL ground (scene_loading_d1):
#   char_digCart   THE HERO -- a big close cart rider bursting at the camera (face ~28 % of the screen width), cropped
#                  by the frame's bottom / left (he bleeds off the screen), drawn at its native 3x (layout scale 1.0)
#   char_digFlyer  the FRONT RUNNER (was the flyer's id): running at the camera with a glossy arrow on his shoulder, a
#                  coral neckerchief, the teal-mint skin -- in the 180 x 220 portrait frame he fits at native 3x
#   char_digPop2   the ARROW SURFER (was the runner's id): the 170 x 160 landscape frame fits the wide surf at native 3x
#   char_digPop1   the back pair, two DIFFERENT Diggers (a chubby goggles-down cheerer, a lamp-hat shoveller)
#   char_digDockPair  two small trotting Diggers, one bare-headed with a sky neckerchief
#   char_bossLoading  the boss STRIDING forward on his own legs + work boots, the lantern swung high, pointing the way
#                  out; style "load2" (a warmer pink, real brow tufts, bigger eyes, fur to the lip); no boulder
# Every arrow a figure holds is the game's GLOSSY enamel arrow (char_d1kit.glossy_arrow), not a painted board.
# The layout (scene_loading_d1.LAYOUT) places the ids; A4 integrates by id (the swap is data: file / frame / x / y).

LOAD_LIGHT3 = D.LIGHT_D1_HK2
# lids_open < 1: at 1.0 the lash crease's polyline collapses to one point -> a NaN SDF that poisons the whole obscurance
# field (every ramp-shaded material then rendered grey / olive: the first v3 renders)
VB3 = C.spec_with(VB, eyes="open", sclera="clean", eye_div=0.10, lash=0.70, low_lid=0.93, paws="defined", lids_open=0.965,
                  hat_gloss=True, skin_tint="a2", vmat=2, belly_face=0.0)


def _light3(rim_dx, **kw):
    """The v3 figure rig with the rim aimed from the daylight pool (screen offset of the pool from the figure)."""
    return dict(LOAD_LIGHT3, rim_dir=D.rim_from(rim_dx), **kw)


def garrow(paint, c, up, face, L, W, tag, depth=0.17, bevel=0.07):
    return D.glossy_arrow(paint, length=L, width=W, shaft=W * 0.54, head_len=L * 0.42, depth=depth, bevel=bevel, tag=tag,
                          R=K.frame_from(up, face), t=np.asarray(c, float))


def garrows(specs, tag=""):
    out = []
    for i, (paint, c, up, face, L, W) in enumerate(specs):
        out += garrow(paint, c, up, face, L, W, f"{tag}{i}")
    return out


# --- THE HERO: the cart rider, big and close, leaning out over the front rim at the camera
HERO = C.spec_with(VB3, lean=22.0, laugh=1.30, eye_scale=1.50, head=dict(yaw=-2.0, roll=-7.0, nod=-12.0), look=(0.02, 0.22),
                   eye_div=0.12, hat=dict(lamp=True, goggles=True, tilt=-16.0, roll=-9.0),
                   arms=dict(L=dict(el=(-0.66, 1.42, 0.30), wr=(-0.80, 1.80, 0.52), d=(-0.28, 0.85, 0.45),
                                    palm=(0.25, -0.10, 1.0), curl=18.0, spread=26.0)))
# both paws thrown up and out ("whee!") -- open spread paws read as paws at 1:1; a paw gripping the rim from above read
# as a gummy mitten (the judges' "formless blob")
HERO = C.spec_with(HERO, arms=dict(R=_world_arm(HERO, el=(0.70, 1.34, 0.40), wr=(0.90, 1.70, 0.58), d=(0.34, 0.85, 0.35),
                                                palm=(-0.25, -0.10, 1.0), curl=16.0, spread=28.0)))
_HERO_Z = 0.14
_HERO_ARROWS = [("coral", (-0.66, 1.26, _HERO_Z - 0.40), (-0.36, 1.0, -0.05), (0.08, 0.0, 1.0), 1.48, 0.86),
                ("sky", (0.72, 1.22, _HERO_Z - 0.42), (0.42, 1.0, -0.05), (-0.10, 0.0, 1.0), 1.42, 0.84),
                ("sunflower", (0.06, 1.62, _HERO_Z - 0.56), (0.10, 1.0, -0.12), (0.0, 0.10, 1.0), 1.66, 0.92)]


def _hero_extra(ctx):
    cart = [(n, s_.translate(0, -0.12, _HERO_Z), m, v) for n, s_, m, v in mine_cart(center=(0.0, 0.0, 0.0), s=1.0, tag="h")]
    return cart + garrows(_HERO_ARROWS, tag="h")


MODELS["dig_cart"] = lambda: _vdig(HERO, dict(yaw=-24, pitch=10), key="lk3_hero", seed=41, extra=_hero_extra)
_HERO_POSE = dict(yaw=-24, pitch=10, roll=10, center=False)
HERO_SCALE = 100.0
_HERO_VIEW = K.view_bounds(_CART_FRAME, scale_pt=HERO_SCALE, center=(-0.02, 1.02), zr=(-1.2, 1.5), margin=1.0, fov=26.0)
ASSETS["char_digCart"] = dict(scene=[("dig_cart", _HERO_POSE)], bounds=_HERO_VIEW, frame=_CART_FRAME, fov=26,
                              light=_light3(0.9), no_fit=True,
                              anchors={"eyeMid": [_eye_anchor(HERO)], "feet": [[0.0, -0.36, _HERO_Z]]})

# --- the FRONT RUNNER (id char_digFlyer, 180 x 220 pt): a glossy arrow on his shoulder, the other paw pumping
RUNNER = C.spec_with(VB3, skin_tint="b2", scarf="coral", lean=14.0, twist=-6.0, girth=0.96, laugh=1.15,
                     head=dict(yaw=10.0, roll=5.0, nod=-8.0), look=(0.12, 0.12),
                     hat=dict(lamp=False, goggles=True, tilt=-12.0, roll=-8.0), legs=RUN_LEGS,
                     arms=dict(L=dict(el=(-0.60, 1.00, 0.36), wr=(-0.46, 1.24, 0.66), d=(0.10, 0.45, 1.0), palm=(0.8, 0.0, 0.2), **FIST),
                               R=dict(el=(0.72, 1.12, 0.16), wr=(0.66, 1.46, 0.30), d=(-0.20, 0.55, 0.60), palm=(-0.8, -0.2, 0.2),
                                      curl=85.0, spread=12.0, claw_bend=55.0, claw_len=0.05)))


def _runner_extra(ctx):
    """the glossy arrow balanced on his right shoulder, the paw up at its shaft, pointing the way he runs"""
    # the shaft runs from the paw (in front of the shoulder) up and BACK past the head's right side: the arrowhead
    # rides high behind him, clear of the face
    pc = ctx["paw"]["R"]
    ax = K.unit([0.30, 0.80, -0.52])
    return garrow("tangerine", pc + ax * 0.52 + np.array([0.04, 0.0, 0.0]), ax, (0.35, 0.30, 1.0), 1.36, 0.80, "rn")


MODELS["dig_flyer"] = lambda: _vdig(RUNNER, dict(yaw=-30, pitch=8), key="lk3_runner", seed=53, extra=_runner_extra)
RUNNER_SCALE = 70.0
_RUNNER_VIEW = K.view_bounds(_FL_FRAME, scale_pt=RUNNER_SCALE, center=(0.02, 1.05), zr=(-1.2, 1.4), margin=1.0)   # feet inside
ASSETS["char_digFlyer"] = dict(scene=[("dig_flyer", dict(yaw=-30, pitch=8, center=False))], bounds=_RUNNER_VIEW,
                               frame=_FL_FRAME, fov=18, light=_light3(-0.8), no_fit=True, anchors={"eyeMid": [_eye_anchor(RUNNER)]})

# --- the ARROW SURFER (id char_digPop2, 170 x 160 pt): crouched on a big glossy arrow, arms out, hat blown off
SURFER = C.spec_with(VB3, lean=6.0, body_roll=-8.0, hat=False, brows="none", eyes="open", laugh=1.2,
                     head=dict(yaw=10.0, roll=0.0, nod=-6.0), look=(0.28, 0.10),
                     legs=dict(L=((-0.24, 0.34, 0.06), (-0.42, 0.22, 0.34), (-0.47, -0.05, 0.22), (-0.48, -0.10, 0.29), (-0.3, 0.0, 1.0)),
                               R=((0.24, 0.34, 0.06), (0.42, 0.22, 0.34), (0.47, -0.05, 0.22), (0.48, -0.10, 0.29), (0.3, 0.0, 1.0))),
                     arms=dict(L=dict(el=(-0.80, 1.26, 0.12), wr=(-1.10, 1.42, 0.24), d=(-0.90, 0.35, 0.25), palm=(0.0, -0.2, 1.0), **OPEN),
                               R=dict(el=(0.80, 1.06, 0.16), wr=(1.10, 0.98, 0.30), d=(0.95, -0.15, 0.25), palm=(0.0, -0.3, 1.0), **OPEN)))


def _surfer_extra(ctx):
    b = garrow("sunflower", (0.10, -0.32, 0.24), (1.0, 0.0, 0.15), (0.0, 1.0, 0.85), 2.05, 1.16, "sf", depth=0.20, bevel=0.08)
    hat = flying_hat((-0.66, 2.02, 0.05), K.rotate_matrix((0, 0, 1), 34.0) @ K.rotate_matrix((1, 0, 0), 30.0), gloss_=True)
    return b + hat


MODELS["dig_pop2"] = lambda: _vdig(SURFER, dict(yaw=8, pitch=6), key="lk3_surfer", seed=43, extra=_surfer_extra)
SURFER_SCALE = 48.0
_SURF_VIEW = K.view_bounds(_POP_FRAME, scale_pt=SURFER_SCALE, center=(-0.24, 0.76), zr=(-1.2, 1.3), margin=1.0)   # board + hat inside
ASSETS["char_digPop2"] = dict(scene=[("dig_pop2", dict(yaw=8, pitch=6, roll=22, center=False))], bounds=_SURF_VIEW,
                              frame=_POP_FRAME, fov=18, light=_light3(-0.2), no_fit=True, anchors={"eyeMid": [_eye_anchor(SURFER)]})

# --- the back pair (id char_digPop1): a chubby goggles-down cheerer + a lamp-hat Digger shouldering a shovel
PAIR_A = C.spec_with(VB3, girth=1.10, height=0.96, lean=12.0, eyes="open", laugh=1.25, hat=False, goggles_down=True,
                     head=dict(yaw=-8.0, roll=-8.0, nod=-8.0), look=(-0.20, 0.25), legs=RUN_LEGS_B,
                     arms=dict(L=dict(el=(-0.72, 1.40, 0.16), wr=(-0.78, 1.80, 0.30), d=(-0.10, 1.0, 0.2), palm=(0.2, 0.0, 1.0), **OPEN),
                               R=dict(el=(0.74, 1.38, 0.16), wr=(0.84, 1.76, 0.30), d=(0.15, 1.0, 0.2), palm=(-0.2, 0.0, 1.0), **OPEN)))
PAIR_B = C.spec_with(VB3, skin_tint="b2", lean=10.0, girth=0.94, height=1.04, head=dict(yaw=-14.0, roll=6.0, nod=-6.0),
                     look=(-0.30, 0.10), legs=RUN_LEGS, hat=dict(lamp=True, goggles=False, tilt=-10.0, roll=-6.0),
                     arms=dict(L=dict(el=(-0.60, 1.00, 0.36), wr=(-0.50, 1.22, 0.66), d=(0.10, 0.45, 1.0), palm=(0.8, 0.0, 0.2), **FIST),
                               R=dict(el=(0.64, 1.34, 0.00), wr=(0.46, 1.58, 0.14), d=(-0.20, 0.30, 1.0), palm=(-0.6, 0.6, 0.2), **FIST)))
MODELS["dig_pairA"] = lambda: _vdig(PAIR_A, dict(yaw=-36, pitch=8), key="lk3_pairA", seed=47)
MODELS["dig_pairB"] = lambda: _vdig(PAIR_B, dict(yaw=-36, pitch=8), key="lk3_pairB", seed=49, extra=_pair_b_extra)
ASSETS["char_digPop1"] = dict(ASSETS["char_digPop1"], light=_light3(-0.9), anchors={"eyeMid": [_eye_anchor(PAIR_A)]})

# --- the dock pair: one bare-headed with a sky neckerchief, one lamp-hat
MODELS["dig_dockA"] = lambda: _vdig(C.spec_with(PAIR_A, girth=1.0, height=1.0, goggles_down=False, scarf="sky",
                                                head=dict(yaw=10.0, roll=-6.0, nod=-4.0), look=(0.30, 0.1)),
                                    dict(yaw=40, pitch=8), key="lk3_dockA", seed=57)
MODELS["dig_dockB"] = lambda: _vdig(C.spec_with(RUNNER, skin_tint="a2", scarf=None, head=dict(yaw=12.0, roll=6.0, nod=-4.0),
                                                look=(0.30, 0.1), hat=dict(lamp=True, goggles=True, tilt=-12.0, roll=-6.0)),
                                    dict(yaw=40, pitch=8), key="lk3_dockB", seed=59, extra=_runner_extra)
ASSETS["char_digDockPair"] = dict(ASSETS["char_digDockPair"], light=_light3(0.9))


# --- THE BOSS: striding forward on his own legs, the lantern swung high, pointing the way out
CB.POSES["load_d1b"] = dict(yaw=12.0, lean=9.0, head=dict(roll=-6.0, yaw=-6.0, nod=-5.0), narrow=0.92, body_dx=0.0, body_dy=0.0)
_BOSS_ARMS3 = dict(
    # the lantern arm swung HIGH (screen right): the fist round the bail, fingers forward, the lantern hanging below it
    R=dict(el=(1.30, 1.86, 0.12), wr=(1.06, 2.42, 0.34), d=(-0.20, 0.25, 1.0), palm=(0.0, -1.0, 0.20), r=0.175),
    # the pointing arm (screen left): thrown out forward-left, index claw along it -- "this way!"
    L=dict(el=(-1.10, 1.24, 0.46), wr=(-1.16, 1.40, 0.98), d=(-0.45, 0.30, 1.0), palm=(0.0, -1.0, 0.25), r=0.17),
)
BOSS_TROUSER = [(0.0, "#D39A6A"), (0.40, "#A96B40"), (0.75, "#7E4828"), (1.0, "#4A2814")]
BOSS_LEG_S = 1.42
# the stride: the near foot forward and flat, the far foot behind with its heel lifted -- its toe still points FORWARD
# (a back foot turned toe-back showed its sole to the camera as a brown disc)
_BOSS_LEGS = dict(L=((-0.26, 0.36, 0.06), (-0.30, 0.20, 0.34), (-0.31, -0.02, 0.38), (-0.31, -0.07, 0.48), (0.0, -0.15, 1.0)),
                  R=((0.26, 0.36, -0.02), (0.30, 0.14, -0.16), (0.32, 0.12, -0.36), (0.33, 0.04, -0.28), (0.0, -0.45, 1.0)))


def _boss_torso_xf(pose):
    P = CB.POSES[pose]
    Rt = S.rot((1, 0, 0), P["lean"]) @ S.rot((0, 1, 0), P["yaw"])
    pivot = np.array([0.0, 0.2, -0.1])
    tt = pivot - Rt @ pivot + np.array([0.0, -0.06, 0.0])
    tb = tt + np.array([P.get("body_dx", 0.0), P.get("body_dy", 0.0), 0.0])
    return Rt, tb


def boss_legs(pose="load_d1b", s=BOSS_LEG_S):
    """Two short stout legs in rust canvas trousers + big laced work boots under the coat (the crew's leg + boot
    builders at s x the size): the stride's hips sit up inside the coat's bell, the feet on the floor. World space."""
    Rt, tb = _boss_torso_xf(pose)
    hip_c = Rt @ np.array([0.0, 0.30, -0.08]) + tb           # the hips' centre (torso space -> world)
    legs, _soles, feet = C.legs_sdf(_BOSS_LEGS, 1.0)
    off = np.array([hip_c[0], hip_c[1] - 0.36 * s, hip_c[2]])

    def xf(q):
        return q.scale(s).translate(*off)
    out = [("trousers", xf(union(*legs, k=0.02)), K.skin("bl_trouser", BOSS_TROUSER, None, vfn=D.canvas_vfn(30, 7), rough=0.78,
                                                         ior=1.2), 0.006)]
    for n, sdf_, m, vx in C.work_boots(feet):
        out.append((f"boss_{n}", xf(sdf_), m, vx * 1.3))
    return out, float(off[1] + s * (-0.12))


def boss_eye_anchor(pose="load_d1b", style="load2"):
    """eyeMid (world) of the boss in a CB pose: boss_v2's head transform applied to the eyes' head-space midpoint."""
    P = CB.POSES[pose]
    Rt, tb = _boss_torso_xf(pose)
    tt = tb - np.array([P.get("body_dx", 0.0), P.get("body_dy", 0.0), 0.0])
    H = P["head"]
    Rh = S.rot((0, 0, 1), H["roll"]) @ S.rot((0, 1, 0), H["yaw"]) @ S.rot((1, 0, 0), H["nod"])
    th = np.array([0.0, S.HEAD_Y, 0.14]) + (Rt @ np.array([0, 1.55, 0]) + tt - np.array([0, 1.55, 0])) * np.array([1, 0, 1])
    E = CB.eyes_of(style)
    ey = (E[0]["c"][1] + E[1]["c"][1]) / 2
    ez = S.surface_z(S.head_skin_raw("home"), 0.0, ey)
    return [round(float(v), 4) for v in (Rh @ np.array([0.0, ey, ez]) + th)]


def _boss3():
    wr = np.asarray(_BOSS_ARMS3["R"]["wr"], float)
    pc = wr + K.unit(_BOSS_ARMS3["R"]["d"]) * 0.175 * 0.95
    lan = D.place_parts(D.lantern(1.45), t=pc + np.array([0.0, -0.06, 0.0]))
    legs, _ = boss_legs()
    return CB.boss_v2("load_d1b", mouth="grin", eyes="open", with_station=False, arms=_BOSS_ARMS3,
                      hands=dict(L="point", R="grip"), extra=_P(lan + legs), look=(0.02, 0.06), view_pose=dict(yaw=0, pitch=4),
                      style="load2", n_strands=56000)


MODELS["boss_loading"] = _boss3
BOSS_SCALE = 63.0
_BOSS_FEET_Y = boss_legs()[1]
_BOSS_VIEW = K.view_bounds(_BL_FRAME, scale_pt=BOSS_SCALE, center=(0.02, 1.16), zr=(-1.2, 1.6), margin=1.0, fov=22.0)
ASSETS["char_bossLoading"] = dict(scene=[("boss_loading", dict(yaw=0, pitch=4, center=False))], bounds=_BOSS_VIEW,
                                  frame=_BL_FRAME, fov=22, light=_light3(0.15), no_fit=True,
                                  anchors={"eyeMid": [boss_eye_anchor()], "feet": [[0.0, _BOSS_FEET_Y, 0.30]]})


# ================================================================== LOOK-L FIX ROUND 2 (v4): the finish judge on v3
# (build/p/LOOK/judge/r3: FAIL 6/10) -- light flat and front-on (one flat tone per part); Digger faces wall-eyed with
# floating lid caps + lash lines and a long rodent snout / buck teeth; the hero the flagged static "arms up in a cart"
# with a cheap squiggle-grain cart; the boss's fur flocked sandpaper, a blotchy coat, plasticine boots on cream discs,
# a startled lidless stare and a shouting gape. v4 keeps every id, frame, file size and sidecar key:
#   every figure  the MODELLING rig (char_d1kit.LIGHT_D1_HK3: a warm key more from the side, ~2:1 over a cool coloured
#                 fill, a warm rim from the doorway, a darker directional dome) + the fixed face (VB4)
#   char_digCart  the hero LEANS OUT over the front rim of a cart that TIPS toward the camera onto its front wheels,
#                 one paw reaching at the camera, the other thrown back, arrows spilling from the tub, sparks at the
#                 wheels; a new cart (bevelled planks, deep gaps, warm varnished wood, a riveted iron frame)
#   char_bossLoading  style "load3" (char_boss): groomed locks + flyaways, lids, broad amber irises, a smile, clean folded
#                 canvas, matte boots on dark soles; supersampled 3x (no strand speckle)
VB4 = C.spec_with(VB3, eye_div=-0.05, lash=0.0, lid_gap=0.004, lids_open=0.84, snout_back=0.035, teeth_k=0.72, laugh=1.25)
LOAD_LIGHT4 = D.LIGHT_D1_HK3


def _light4(rim_dx, **kw):
    return dict(LOAD_LIGHT4, rim_dir=D.rim_from(rim_dx), **kw)


def _look_cam(view_yaw, head_yaw, es=1.45, up=0.06):
    """look x that turns the eyes back to the CAMERA for a figure whose view yaw + head yaw turn it away (the iris
    sits on the eye ellipsoid at direction (lx rx, ly ry, rz): lx = tan(-net) rz / rx)."""
    rx = C.EYE_R[0] * es
    rz = C.EYE_R[2] * (1.0 + 0.55 * (es - 1.0))
    return (round(float(math.tan(math.radians(-(view_yaw + head_yaw))) * rz / rx), 3), up)


# the spark streaks at the cart's front wheels (post_fit: crisp, bright, a few; never a smudge)
def sparks_post(sparks):
    """sparks = [(x, y, angle_deg, length, width)] in frame pt: a hot white core with an orange sheath, tapering."""
    def fn(im):
        from PIL import Image as _I
        W_, H_ = im.size
        yy, xx = np.mgrid[0:H_, 0:W_]
        X, Y = (xx + 0.5) / 3, (yy + 0.5) / 3
        cov = np.zeros((H_, W_))
        core = np.zeros((H_, W_))
        for (x, y, ang, ln, wd) in sparks:
            ca, sa = math.cos(math.radians(ang)), math.sin(math.radians(ang))
            t = (X - x) * ca + (Y - y) * sa
            n = -(X - x) * sa + (Y - y) * ca
            u = np.clip(t / ln, 0, 1)
            half = wd * (1 - u) ** 0.8 + 0.15
            inside = (t >= 0) & (t <= ln)
            c = np.clip(1 - np.abs(n) / half, 0, 1) * inside
            cov = np.maximum(cov, c ** 0.7)
            core = np.maximum(core, np.clip(1 - np.abs(n) / (half * 0.45), 0, 1) * inside * (1 - u) ** 0.5)
        hot = np.array([1.0, 0.98, 0.86])
        sheath = np.array([1.0, 0.62, 0.16])
        rgb_ = sheath[None, None] + (hot - sheath)[None, None] * core[..., None]
        glow = np.clip(cov, 0, 1)
        spark = np.concatenate([rgb_, glow[..., None]], -1)
        s_im = _I.fromarray((np.clip(spark, 0, 1) * 255).astype(np.uint8), "RGBA")
        return _I.alpha_composite(im.convert("RGBA"), s_im)
    return fn


CART_WOOD = [(0.0, "#FFC578"), (0.30, "#F2A04A"), (0.60, "#D97C2C"), (0.85, "#A85418"), (1.0, "#6A300A")]
CART_IRON = [(0.0, "#8FA8C4"), (0.35, "#5A7290"), (0.70, "#34465E"), (1.0, "#18222E")]


def mine_cart2(center=(0, 0, 0), s=1.0, tag=""):
    """LOOK-L fix round 2 (the finish judge: "flat orange planks with dark marker-squiggle grain, flat light, a uniform
    grey frame and no occlusion shading in the gaps"): a tapered tub of SEPARATE bevelled planks (deep V gaps the
    obscurance darkens), warm varnished wood with NO drawn grain (a clearcoat catches the bevels), a riveted iron frame --
    corner posts, a waist band and a thick rim -- in a blued steel with highlights, brass rivets along every band, four
    spoked iron wheels. Origin: the floor centre; front = +Z. -> [(name, sdf, mat, voxel)]"""
    c = np.asarray(center, float)
    top_w, top_d, bot_w, bot_d, hgt = 0.92, 0.58, 0.78, 0.48, 0.78
    lo_b = [-top_w - 0.15, -0.15, -top_d - 0.15]
    hi_b = [top_w + 0.15, hgt + 0.15, top_d + 0.15]

    def tub(off=0.0):
        kx = (top_w - bot_w) / hgt
        kz = (top_d - bot_d) / hgt

        def f(p):
            y = p[:, 1]
            wx = bot_w + kx * np.clip(y, 0, hgt) + off
            wz = bot_d + kz * np.clip(y, 0, hgt) + off
            dx = (np.abs(p[:, 0]) - wx) * 0.97
            dz = (np.abs(p[:, 2]) - wz) * 0.97
            dy = np.maximum(-y - off, y - hgt - off)
            q = np.stack([dx, dy, dz], 1)
            out = np.linalg.norm(np.maximum(q, 0), axis=1) + np.minimum(q.max(1), 0)
            return out.astype(np.float32)
        return _SDF(f, lo_b, hi_b)
    outer = tub(0.0)
    inner = tub(-0.075).translate(0, 0.10, 0)
    shell = outer.subtract(inner).offset(0.010)
    gaps = []
    for yy in (0.195, 0.39, 0.585):          # V gaps between four horizontal planks
        gaps.append(outer.offset(0.03).subtract(outer.offset(-0.035)).intersect(D.slab_y(yy - 0.014, yy + 0.014)))
    shell = shell.subtract(union(*gaps), k=0.018)
    iron = []
    for sx in (-1, 1):
        for sz in (-1, 1):
            iron.append(capsule((sx * (bot_w + 0.012), 0.0, sz * (bot_d + 0.012)), (sx * (top_w + 0.012), hgt, sz * (top_d + 0.012)), 0.055))
    iron.append(outer.offset(0.036).subtract(outer.offset(-0.02)).intersect(D.slab_y(0.44, 0.50)))           # the waist band
    mouth = union(inner, inner.translate(0, 0.30, 0))
    iron.append(outer.offset(0.045).subtract(outer.offset(-0.045)).intersect(D.slab_y(hgt - 0.06, hgt + 0.035)).subtract(mouth))
    rivets = []
    for sx in (-1, 1):                         # rivets along the waist band and the rim, front + sides
        for yy in (0.47, hgt - 0.012):
            wz = bot_d + (top_d - bot_d) * yy / hgt
            wx = bot_w + (top_w - bot_w) * yy / hgt
            for f_ in np.linspace(-0.75, 0.75, 5):
                rivets.append(sphere(0.026).translate(f_ * wx, yy, wz + 0.05))
                rivets.append(sphere(0.026).translate(sx * (wx + 0.05), yy, f_ * wz))
    wheels, axles = [], []
    for sx in (-1, 1):
        for sz in (-1, 1):
            wc = np.array([sx * (bot_w + 0.03), -0.06, sz * 0.36])
            Rw = K.frame_from([1, 0, 0], [0, 0, 1])
            tyre = cylinder(0.25, 0.050, round=0.022).transform(Rw).translate(*wc)
            flange = cylinder(0.285, 0.016, round=0.008).transform(Rw).translate(*(wc - np.array([sx * 0.055, 0, 0])))
            hub = cylinder(0.075, 0.075, round=0.025).transform(Rw).translate(*(wc + np.array([sx * 0.03, 0, 0])))
            dish = cylinder(0.19, 0.06, round=0.02).transform(Rw).translate(*(wc + np.array([sx * 0.035, 0, 0])))
            wheels.append(union(tyre.subtract(dish, k=0.01), flange, k=0.01))
            axles.append(hub)
    xf = lambda q: q.scale(s).translate(*c) if s != 1.0 else q.translate(*c)   # noqa: E731
    wood = K.skin(f"c_cartwood2{tag}", CART_WOOD, None, vfn=None, rough=0.46, ior=1.35, clearcoat=0.45, cc_rough=0.10)
    ironm = K.skin(f"c_iron2{tag}", CART_IRON, None, vfn=None, rough=0.30, ior=1.5, clearcoat=0.35, cc_rough=0.08)
    return [("cartTub", xf(shell), wood, 0.0055 * max(s, 0.6)),
            ("cartBands", xf(union(*iron)), ironm, 0.004 * max(s, 0.6)),
            ("cartRivets", xf(union(*rivets)), K.skin(f"c_crivet2{tag}", D.BRASS_LUT, None, rough=0.26, ior=1.5, clearcoat=0.4,
                                                      cc_rough=0.06), 0.003 * max(s, 0.6)),
            ("cartWheels", xf(union(*wheels, *axles)), ironm, 0.0035 * max(s, 0.6))]


# --- THE HERO v4: leaning OUT over the front rim of a cart tipping at the camera; a paw reaching at the viewer
HERO4 = C.spec_with(VB4, lean=30.0, twist=6.0, laugh=1.38, eye_scale=1.50, head=dict(yaw=8.0, roll=-8.0, nod=-14.0),
                    hat=dict(lamp=True, goggles=True, tilt=-18.0, roll=-10.0))
# the NEAR paw (+x: the view yaw turns it toward the camera) reaches OUT at the viewer over the cart's rim -- along the
# model-space direction that the view pose sends to the camera, (0.59, 0.28, 0.76) (world points: the torso leans 30
# deg); the far paw is flung out and back past the screen's left edge ("whee!" -- raised, it was cut by the frame top)
HERO4 = C.spec_with(HERO4, look=_look_cam(-38.0, 8.0, es=1.50, up=0.02),
                    arms=dict(R=_world_arm(HERO4, el=(0.70, 1.04, 0.70), wr=(0.94, 1.10, 1.10), d=(0.55, 0.12, 0.83),
                                           palm=(0.40, 0.35, 0.85), curl=6.0, spread=34.0),
                              L=_world_arm(HERO4, el=(-0.80, 1.38, -0.06), wr=(-1.14, 1.60, -0.14), d=(-0.85, 0.50, -0.10),
                                           palm=(0.10, -0.05, 1.0), curl=12.0, spread=32.0)))
_HERO4_Z = 0.10
_CART_TIP = 13.0         # deg: the cart pitched forward about its front axle (the rear wheels lifted)
_HERO4_ARROWS = [("tangerine", (-0.58, 1.24, _HERO4_Z - 0.42), (-0.40, 1.0, -0.10), (0.10, 0.0, 1.0), 1.46, 0.86),
                 ("teal", (0.62, 1.30, _HERO4_Z - 0.44), (0.55, 1.0, -0.12), (-0.12, 0.0, 1.0), 1.36, 0.82),
                 # (a sunflower arrow behind the hat was cut by the frame's top edge -- mid-screen -- and repeated the
                 # hat's yellow: dropped)
                 ]


def _tip(sdf_, deg=_CART_TIP, pivot=(0.0, -0.31, 0.36)):
    pv = np.asarray(pivot, float)
    return sdf_.translate(*(-pv)).transform(K.rotate_matrix((1, 0, 0), deg)).translate(*pv)


def _hero4_extra(ctx):
    cart = [(n, _tip(s_.translate(0, -0.12, _HERO4_Z)), m, v) for n, s_, m, v in mine_cart2(center=(0.0, 0.0, 0.0), s=1.0, tag="h4")]
    arrows = garrows(_HERO4_ARROWS, tag="h4")
    # one small coral arrow tumbling OUT over the rear corner of the tub (spilling)
    arrows += garrow("coral", (0.98, 1.02, _HERO4_Z - 0.30), (0.85, 0.45, 0.10), (0.10, -0.15, 1.0), 0.80, 0.52, "h4s")
    return cart + [(n, _tip(s_), m, v) for n, s_, m, v in arrows]


MODELS["dig_cart"] = lambda: _vdig(HERO4, dict(yaw=-38, pitch=16), key="lk4_hero", seed=41, extra=_hero4_extra)
_HERO4_POSE = dict(yaw=-38, pitch=16, roll=12, center=False)
HERO4_SCALE = 100.0
_HERO4_VIEW = K.view_bounds(_CART_FRAME, scale_pt=HERO4_SCALE, center=(0.10, 0.77), zr=(-1.3, 1.6), margin=1.0, fov=26.0)
# shadow off: the key's shadow map striped the cart's front planks with diagonal bands (build/p/LOOK/F2/review/p_hero_ns.png)
ASSETS["char_digCart"] = dict(scene=[("dig_cart", _HERO4_POSE)], bounds=_HERO4_VIEW, frame=_CART_FRAME, fov=26,
                              light=_light4(0.9, shadow=False), no_fit=True,
                              anchors={"eyeMid": [_eye_anchor(HERO4)], "feet": [[0.0, -0.36, _HERO4_Z]]})

# --- the FRONT RUNNER v4 (id char_digFlyer): the v3 pose, the fixed face, eyes on the camera, the modelling light
RUNNER4 = C.spec_with(RUNNER, **{k: VB4[k] for k in ("eye_div", "lash", "lid_gap", "lids_open", "snout_back", "teeth_k")},
                      laugh=1.22, look=_look_cam(-30.0, 10.0))
MODELS["dig_flyer"] = lambda: _vdig(RUNNER4, dict(yaw=-30, pitch=8), key="lk4_runner", seed=53, extra=_runner_extra)
ASSETS["char_digFlyer"] = dict(ASSETS["char_digFlyer"], light=_light4(-0.8), anchors={"eyeMid": [_eye_anchor(RUNNER4)]})

# --- the ARROW SURFER v4 (id char_digPop2)
SURFER4 = C.spec_with(SURFER, **{k: VB4[k] for k in ("eye_div", "lash", "lid_gap", "lids_open", "snout_back", "teeth_k")},
                      laugh=1.25, look=_look_cam(8.0, 10.0, up=0.0))
MODELS["dig_pop2"] = lambda: _vdig(SURFER4, dict(yaw=8, pitch=6), key="lk4_surfer", seed=43, extra=_surfer_extra)
ASSETS["char_digPop2"] = dict(ASSETS["char_digPop2"], light=_light4(-0.2), anchors={"eyeMid": [_eye_anchor(SURFER4)]})

# --- the back pair v4 (id char_digPop1): both look at the boss / the way out (up-left), converging
_FACE4 = {k: VB4[k] for k in ("eye_div", "lash", "lid_gap", "lids_open", "snout_back", "teeth_k")}
PAIR_A4 = C.spec_with(PAIR_A, **_FACE4, look=(-0.20, 0.22))
PAIR_B4 = C.spec_with(PAIR_B, **_FACE4, look=(-0.26, 0.10))
MODELS["dig_pairA"] = lambda: _vdig(PAIR_A4, dict(yaw=-36, pitch=8), key="lk4_pairA", seed=47)
MODELS["dig_pairB"] = lambda: _vdig(PAIR_B4, dict(yaw=-36, pitch=8), key="lk4_pairB", seed=49, extra=_pair_b_extra)
ASSETS["char_digPop1"] = dict(ASSETS["char_digPop1"], light=_light4(-0.9), anchors={"eyeMid": [_eye_anchor(PAIR_A4)]})

# --- the dock pair v4
MODELS["dig_dockA"] = lambda: _vdig(C.spec_with(PAIR_A4, girth=1.0, height=1.0, goggles_down=False, scarf="sky",
                                                head=dict(yaw=10.0, roll=-6.0, nod=-4.0), look=(0.30, 0.1)),
                                    dict(yaw=40, pitch=8), key="lk4_dockA", seed=57)
MODELS["dig_dockB"] = lambda: _vdig(C.spec_with(RUNNER4, skin_tint="a2", scarf=None, head=dict(yaw=12.0, roll=6.0, nod=-4.0),
                                                look=(0.30, 0.1), hat=dict(lamp=True, goggles=True, tilt=-12.0, roll=-6.0)),
                                    dict(yaw=40, pitch=8), key="lk4_dockB", seed=59, extra=_runner_extra)
ASSETS["char_digDockPair"] = dict(ASSETS["char_digDockPair"], light=_light4(0.9))


# --- THE BOSS v4: style "load3", the same stride / lantern / pointing pose
def boss_legs4(pose="load_d1b", s=BOSS_LEG_S):
    """boss_legs with MATTE leather boots on dark rubber soles (the finish judge: "shiny plasticine blobs ... cream disc
    soles look like display bases") and matte canvas trousers."""
    Rt, tb = _boss_torso_xf(pose)
    hip_c = Rt @ np.array([0.0, 0.30, -0.08]) + tb
    legs, _soles, feet = C.legs_sdf(_BOSS_LEGS, 1.0)
    off = np.array([hip_c[0], hip_c[1] - 0.36 * s, hip_c[2]])

    def xf(q):
        return q.scale(s).translate(*off)
    out = [("trousers", xf(union(*legs, k=0.02)), K.skin("bl_trouser4", BOSS_TROUSER, None, vfn=None, rough=0.84, ior=1.18), 0.006)]
    for n, sdf_, m, vx in C.work_boots(feet, matte=True, tag="b4"):
        out.append((f"boss_{n}", xf(sdf_), m, vx * 1.3))
    return out, float(off[1] + s * (-0.12))


def _boss4():
    wr = np.asarray(_BOSS_ARMS3["R"]["wr"], float)
    pc = wr + K.unit(_BOSS_ARMS3["R"]["d"]) * 0.175 * 0.95
    lan = D.place_parts(D.lantern(1.45), t=pc + np.array([0.0, -0.06, 0.0]))
    legs, _ = boss_legs4()
    return CB.boss_v2("load_d1b", mouth="smile2", eyes="open", with_station=False, arms=_BOSS_ARMS3,
                      hands=dict(L="point", R="grip"), extra=_P(lan + legs), look=(0.05, -0.05), view_pose=dict(yaw=0, pitch=4),
                      style="load3", n_strands=36000)


MODELS["boss_loading"] = _boss4
# shadow off: the key's shadow map laid long dark diagonal bands across the coat (build/p/LOOK/F2/review/p_boss_ns.png);
# the baked obscurance field keeps the contact darks (under the collar, the arms, the head)
ASSETS["char_bossLoading"] = dict(ASSETS["char_bossLoading"], light=_light4(0.15, shadow=False), ss=3,
                                  anchors={"eyeMid": [boss_eye_anchor(style="load3")], "feet": [[0.0, _BOSS_FEET_Y, 0.30]]})


# ================================================================== LOOK-2 (v5): the finish judge on v4
# (build/p/LOOK/round3.json finish_r3: FAIL 6/10) -- the boss glares (lids on the irises, brows down, small pupils) and
# his goggles read as a second pair of eyes; the hero is clipped by the screen edge, looks away and hides in a cart of
# orange plastic with sprinkle rivets; the crew skin is wet gummy (tiny clearcoat hotspots, teal-grey shadows), bare
# mint legs under the vest, gremlin claws; the boss coat is a smudged balloon; no back-light, an unlit lantern. v5 keeps
# every id, frame, file size and sidecar key:
#   every Digger  vmat 3 = SATIN vinyl (a broad soft highlight, warm yellow-green shadow lift), khaki canvas work
#                 TROUSERS + matte boots, chunky MITT paws with short rounded claws, lids without spec, the warm-fill
#                 rig (char_d1kit.LIGHT_D1_HK4: a big soft key window, a honey / peach bounce instead of the azure room)
#   char_digCart  the hero rides HIGH in a smaller (x0.8) cart of worn stained TIMBER with dark iron bands, turned more
#                 to the camera, eyes on the viewer, the near paw reaching at the camera (a 1.5x mitt), the far paw
#                 waving above his shoulder; the face well inside the screen
#   char_bossLoading  style "load4" (char_boss): delighted face (lids off the irises, brows up and apart, big pupils),
#                 dark tinted goggle glass with a sky reflection + one glint, a belted coat with fold ridges and thick
#                 trims, a LIT lantern (a flame in amber glass, a warm point light on his face) and a warm rim
V5 = dict(vmat=3, paws="mitt", trousers="khaki", boots_matte=True)
LOAD_LIGHT5 = D.LIGHT_D1_HK4


def _light5(rim_dx, **kw):
    return dict(LOAD_LIGHT5, rim_dir=D.rim_from(rim_dx), **kw)


CART_WOOD5 = [(0.0, "#BC9272"), (0.30, "#9A7456"), (0.60, "#7C5A40"), (0.85, "#5A3E2A"), (1.0, "#362416")]    # stained timber
CART_WORN5 = [(0.0, "#EAD8BA"), (0.30, "#D8C09C"), (0.60, "#BCA27C"), (0.85, "#947852"), (1.0, "#604A2E")]    # worn raw edges
CART_IRON5 = [(0.0, "#56687E"), (0.35, "#3A4A5E"), (0.70, "#263242"), (1.0, "#121A24")]                       # dark blued iron
CART_IRONW5 = [(0.0, "#C8D6E4"), (0.35, "#A2B2C4"), (0.70, "#7A8A9C"), (1.0, "#4A5664")]                      # worn steel edges


def _wood_vfn(sdf_, seed=7):
    """v for the timber LUT: the WORN convex edges (lighter raw wood) + a faint grain along the planks (x)."""
    wear = D.wear_vfn(sdf_, width=0.014, seed=seed, gain=1.0)
    grain = D.grain_vfn(freq=40.0, axis=0, seed=seed)

    def fn(v):
        return np.clip(0.80 * wear(v) + 0.12 * grain(v), 0, 1)
    return fn


def mine_cart3(center=(0, 0, 0), s=1.0, tag="", post=None):
    """LOOK-2 (the finish judge on v4: "orange-and-grey plastic with sprinkle-like rivets ... no grain, edge wear or
    metal specular. FIX: warm-brown timber (lower chroma) with lighter worn edges and a subtle grain, roughness ~0.6;
    dark blued metallic iron with crisp edge highlights, roughness ~0.35; smaller, darker rivets each with one
    highlight"): mine_cart2's geometry (separate bevelled planks, iron posts / waist band / rim, spoked wheels) with a
    stained TIMBER (no clearcoat, worn light edges + grain in the LUT's v), DARK blued iron with bright worn edges, and
    three small dark rivets per band face. post(sdf) -> the placed sdf (the worn-edge maps are measured on it)."""
    parts = mine_cart2(center, s, tag)
    post = post or (lambda q: q)
    out = []
    for n, sdf_, m, vx in parts:
        q = post(sdf_)
        if n == "cartTub":
            m = K.skin(f"c_wood5{tag}", CART_WOOD5, CART_WORN5, vfn=_wood_vfn(q, 7), rough=0.62, ior=1.30)
        elif n in ("cartBands", "cartWheels"):
            # (v5 draft: gain 1.4 at width 0.010 made the whole thin band read "worn" -> silver aluminium)
            m = K.skin(f"c_iron5{n}{tag}", CART_IRON5, CART_IRONW5, vfn=D.wear_vfn(q, width=0.005, seed=11, gain=0.40),
                       rough=0.36, ior=1.55, clearcoat=0.08, cc_rough=0.20)
        elif n == "cartRivets":
            continue
        out.append((n, q, m, vx))
    # fewer, smaller, darker rivets: three per band face (front + sides), on the waist band and the rim
    c = np.asarray(center, float)
    top_w, top_d, bot_w, bot_d, hgt = 0.92, 0.58, 0.78, 0.48, 0.78
    rv = []
    for yy in (0.47, hgt - 0.012):
        wz = bot_d + (top_d - bot_d) * yy / hgt
        wx = bot_w + (top_w - bot_w) * yy / hgt
        for f_ in (-0.62, 0.0, 0.62):
            rv.append(sphere(0.019).translate(f_ * wx, yy, wz + 0.046))
            for sx in (-1, 1):
                rv.append(sphere(0.019).translate(sx * (wx + 0.046), yy, f_ * wz))
    rq = union(*rv)
    rq = rq.scale(s).translate(*c) if s != 1.0 else rq.translate(*c)
    out.append(("cartRivets", post(rq), K.skin(f"c_rivet5{tag}", [(0.0, "#8494A8"), (0.4, "#4A586A"), (1.0, "#1A222C")], None,
                                                rough=0.22, ior=1.5, clearcoat=0.5, cc_rough=0.06), 0.0028 * max(s, 0.6)))
    return out


# --- THE HERO v5: high in a smaller cart, turned to the camera, reaching at the viewer
_V5_VIEW_POSE = dict(yaw=-24, pitch=12)
HERO5 = C.spec_with(VB4, **V5, lean=16.0, twist=0.0, laugh=1.36, eye_scale=1.50, lids_open=0.93,
                    head=dict(yaw=4.0, roll=-5.0, nod=-8.0), hat=dict(lamp=True, goggles=True, tilt=-16.0, roll=-8.0))
HERO5 = C.spec_with(HERO5, look=_look_cam(-24.0, 4.0, es=1.50, up=0.04),
                    arms=dict(R=_world_arm(HERO5, el=(0.62, 1.08, 0.54), wr=(0.72, 1.16, 0.96), d=(0.30, 0.88, 0.36),
                                           palm=(0.40, 0.21, 0.89), curl=12.0, spread=22.0, paw_s=1.4),
                              L=_world_arm(HERO5, el=(-0.74, 1.42, 0.24), wr=(-0.86, 1.80, 0.34), d=(-0.20, 1.0, 0.15),
                                           palm=(0.40, 0.20, 0.90), curl=12.0, spread=22.0)))
_HERO5_Z = 0.10
_CART5_S = 0.80
_CART5_Y = -0.34
_CART5_TIP = 8.0
_CART5_PIVOT = (0.0, -0.06 * _CART5_S + _CART5_Y, 0.36 * _CART5_S + _HERO5_Z)
_HERO5_ARROWS = [("tangerine", (-0.50, 0.98, _HERO5_Z - 0.34), (-0.42, 1.0, -0.10), (0.10, 0.0, 1.0), 1.24, 0.76),
                 ("teal", (0.50, 1.04, _HERO5_Z - 0.36), (0.50, 1.0, -0.12), (-0.12, 0.0, 1.0), 1.16, 0.72)]


def _tip5(q):
    return _tip(q, deg=_CART5_TIP, pivot=_CART5_PIVOT)


def _hero5_extra(ctx):
    cart = mine_cart3(center=(0.0, _CART5_Y, _HERO5_Z), s=_CART5_S, tag="h5", post=_tip5)
    arrows = garrows(_HERO5_ARROWS, tag="h5")
    arrows += garrow("coral", (0.80, 0.62, _HERO5_Z - 0.24), (0.85, 0.45, 0.10), (0.10, -0.15, 1.0), 0.70, 0.46, "h5s")
    return cart + [(n, _tip5(s_), m, v) for n, s_, m, v in arrows]


MODELS["dig_cart"] = lambda: _vdig(HERO5, _V5_VIEW_POSE, key="lk5_hero", seed=41, extra=_hero5_extra)
_HERO5_POSE = dict(yaw=-24, pitch=12, roll=6, center=False)
HERO5_SCALE = 100.0
HERO5_CENTER = (-0.20, 0.90)
_HERO5_VIEW = K.view_bounds(_CART_FRAME, scale_pt=HERO5_SCALE, center=HERO5_CENTER, zr=(-1.3, 1.6), margin=1.0, fov=26.0)
ASSETS["char_digCart"] = dict(scene=[("dig_cart", _HERO5_POSE)], bounds=_HERO5_VIEW, frame=_CART_FRAME, fov=26,
                              light=_light5(0.9, shadow=False), no_fit=True,
                              anchors={"eyeMid": [_eye_anchor(HERO5)], "feet": [[0.0, _CART5_Y - 0.25 * _CART5_S, _HERO5_Z]]})

# --- the FRONT RUNNER v5 (id char_digFlyer), the ARROW SURFER v5 (id char_digPop2), the back pair v5 (id char_digPop1)
RUNNER5 = C.spec_with(RUNNER4, **V5, lids_open=0.92)
MODELS["dig_flyer"] = lambda: _vdig(RUNNER5, dict(yaw=-30, pitch=8), key="lk5_runner", seed=53, extra=_runner_extra)
ASSETS["char_digFlyer"] = dict(ASSETS["char_digFlyer"], light=_light5(-0.8), anchors={"eyeMid": [_eye_anchor(RUNNER5)]})
SURFER5 = C.spec_with(SURFER4, **V5, lids_open=0.92)
MODELS["dig_pop2"] = lambda: _vdig(SURFER5, dict(yaw=8, pitch=6), key="lk5_surfer", seed=43, extra=_surfer_extra)
ASSETS["char_digPop2"] = dict(ASSETS["char_digPop2"], light=_light5(-0.2), anchors={"eyeMid": [_eye_anchor(SURFER5)]})
PAIR_A5 = C.spec_with(PAIR_A4, **V5, lids_open=0.92)
PAIR_B5 = C.spec_with(PAIR_B4, **V5, lids_open=0.92)
MODELS["dig_pairA"] = lambda: _vdig(PAIR_A5, dict(yaw=-36, pitch=8), key="lk5_pairA", seed=47)
MODELS["dig_pairB"] = lambda: _vdig(PAIR_B5, dict(yaw=-36, pitch=8), key="lk5_pairB", seed=49, extra=_pair_b_extra)
ASSETS["char_digPop1"] = dict(ASSETS["char_digPop1"], light=_light5(-0.9), anchors={"eyeMid": [_eye_anchor(PAIR_A5)]})
MODELS["dig_dockA"] = lambda: _vdig(C.spec_with(PAIR_A5, girth=1.0, height=1.0, goggles_down=False, scarf="sky",
                                                head=dict(yaw=10.0, roll=-6.0, nod=-4.0), look=(0.30, 0.1)),
                                    dict(yaw=40, pitch=8), key="lk5_dockA", seed=57)
MODELS["dig_dockB"] = lambda: _vdig(C.spec_with(RUNNER5, skin_tint="a2", scarf=None, head=dict(yaw=12.0, roll=6.0, nod=-4.0),
                                                look=(0.30, 0.1), hat=dict(lamp=True, goggles=True, tilt=-12.0, roll=-6.0)),
                                    dict(yaw=40, pitch=8), key="lk5_dockB", seed=59, extra=_runner_extra)
ASSETS["char_digDockPair"] = dict(ASSETS["char_digDockPair"], light=_light5(0.9))


# --- THE BOSS v5: style "load4", a lit lantern, the same stride / lantern / pointing pose
def boss_lantern_pos():
    wr = np.asarray(_BOSS_ARMS3["R"]["wr"], float)
    pc = wr + K.unit(_BOSS_ARMS3["R"]["d"]) * 0.175 * 0.95
    return pc + np.array([0.0, -0.06, 0.0])


def _boss5():
    lan = D.place_parts(D.lantern_lit(1.45), t=boss_lantern_pos())
    legs, _ = boss_legs4()
    return CB.boss_v2("load_d1b", mouth="smile2", eyes="open", with_station=False, arms=_BOSS_ARMS3,
                      hands=dict(L="point", R="grip"), extra=_P(lan + legs), look=(0.04, 0.02), view_pose=dict(yaw=0, pitch=4),
                      style="load4", n_strands=36000)


MODELS["boss_loading"] = _boss5


def _boss_lights5():
    """the lantern's warm point light (the flame, in the render's world: the scene pose is yaw 0 / pitch 4 about the
    origin) + the warm back-light rim to match the backdrop's glow behind his head"""
    import uikit
    p = boss_lantern_pos() + np.array([0.0, -0.42, 0.10])
    q = uikit.rot_x(4.0) @ p            # ui3d._look(yaw 0, pitch 4): the pose the boss renders in
    return [dict(type="point", position=[float(v) for v in q], intensity=5200.0, color=[1.0, 0.72, 0.36], attenuation=2.6)]


def _frame_pt(case, P):
    """a model point -> frame pt of a case (ui3d's exact camera for the case's bounds / pose; no render)."""
    import ui3d
    spec = ASSETS[case]
    pose = spec["scene"][0][1]
    R = ui3d._look(pose.get("yaw", 0), pose.get("pitch", 0), pose.get("roll", 0))
    fw, fh = spec["frame"]
    lo, hi = np.asarray(spec["bounds"][0], float), np.asarray(spec["bounds"][1], float)
    W, H = int(fw * 9), int(fh * 9)
    job = ui3d.scene_job("/dev/null", W, H, [], (lo, hi), fov=spec.get("fov", 18.0), margin=spec.get("margin", 1.06))
    px = ui3d.project(job["camera"], W, H, (np.asarray([P], float) @ R.T))[0]
    return float(px[0]) / 9, float(px[1]) / 9


def lantern_halo(im):
    """LOOK-2 post_fit: the lit lantern's warm GLOW HALO (additive light in premultiplied space: over the fur it warms
    and brightens, over the transparent frame it becomes a soft semi-transparent glow the app composites on the page)."""
    fx, fy = _frame_pt("char_bossLoading", boss_lantern_pos() + np.array([0.0, -0.42, 0.0]))
    a = np.asarray(im.convert("RGBA")).astype(np.float64) / 255
    h, w = a.shape[:2]
    yy, xx = np.mgrid[0:h, 0:w]
    d2 = ((xx + 0.5) / 3 - fx) ** 2 + ((yy + 0.5) / 3 - fy) ** 2
    g = 0.55 * np.exp(-d2 / (2 * 7.0 ** 2)) + 0.26 * np.exp(-d2 / (2 * 20.0 ** 2))
    warm = np.array([1.0, 0.80, 0.46])
    al = a[..., 3:4]
    pre = a[..., :3] * al + warm * g[..., None]
    na = 1 - (1 - al) * (1 - g[..., None])
    rgb_ = np.clip(pre / np.maximum(na, 1e-6), 0, 1)
    out = np.concatenate([rgb_, np.clip(na, 0, 1)], -1)
    from PIL import Image as _I
    return _I.fromarray((out * 255 + 0.5).astype(np.uint8), "RGBA")


ASSETS["char_bossLoading"] = dict(ASSETS["char_bossLoading"], light=_light5(0.15, shadow=False, rim_lux=1900.0,
                                                                            rim_color=(1.0, 0.90, 0.72), extra=_boss_lights5()),
                                  ss=3, post_fit=lantern_halo,
                                  anchors={"eyeMid": [boss_eye_anchor(style="load4")], "feet": [[0.0, _BOSS_FEET_Y, 0.30]]})


# ================================================================== LOOK-2 round 2 (v6): the finish judge on v5
# (build/p/LOOK2/judge: FAIL -- finish 7, light 7, appeal 7, depth 7.5, overall 7): every hand a smooth mint lump with
# bead claws (the hero's reach merging with a mint arrow, the runner's "drumstick" grip); "Loading.." lands on the
# hero's belt; clay trousers; paper-white eye whites; a stray sliver in the hero's mouth; a copper-streak cart with
# plastic-grey iron; the boss an inflatable coat on clay boots with eye-dot laces, a flat pink pompom fur, a plastic
# lantern. v6 keeps every id, frame, file size and sidecar key:
#   every Digger  FINGERLESS WORK GLOVES (char_crew_d1.glove_paw), detailed work trousers (side seams, knee creases,
#                 patch pockets, bloused hems, belt loops, a clean weave), an off-white sclera with a lid shadow, the
#                 open mouth cut clean of the vest
#   char_digCart  the cart RAISED so its front planks sit under the app's "Loading.." label (ui.json frames.loading
#                 .label, y 765.6-805.6 pt); the near glove grips the front rim (the back of the hand, three fingers over
#                 the edge), the far glove waves; the tub's arrows tangerine + sunflower (no mint / teal beside the skin);
#                 an umber timber tub (grain, knots, worn chipped edges), near-black blued iron (bright worn edges, rust
#                 in the crevices)
#   char_digFlyer the runner's glove GRIPS the arrow's shaft edge (three fingers over its front face)
#   char_digPop1  the cheerer: laughing ^ ^ eyes and his goggles on a hat (no glasses on a face)
#   char_bossLoading  style "load5" (char_boss); boots with a heel, a toe-spring, an instep strap and ankle creases; an
#                 aged-brass lantern with amber glass and an orange flame, a stronger warm spill; a soft top light
# (lace_color: the cream laces read as two white dots -- "eyes" -- on a boot at size; dark waxed laces instead)
V6 = dict(vmat=3, paws="glove", trousers="khaki", trousers_detail=True, boots_matte=True, sclera="soft", mouth_clean=True,
          lace_color="#6A3E20")          # (r2: #3A2414 read as two dark dashes -- "closed eyes"; now a low-contrast brown)

CART_WOOD6 = [(0.0, [(0.0, "#5E442E"), (0.5, "#3E2C1C"), (1.0, "#22160C")]),     # knots
              (0.40, [(0.0, "#8C6E54"), (0.5, "#6A503A"), (1.0, "#3C2A1A")]),    # the grain's darker streaks
              (0.55, [(0.0, "#A48468"), (0.5, "#80624A"), (1.0, "#4A3422")]),    # stained umber timber
              (1.0, [(0.0, "#DCC8A8"), (0.5, "#B89C7C"), (1.0, "#7C664A")])]     # worn / chipped raw edges
# (r2 test: the first iron ladder + wear gain 0.55 still read mid-grey on the thin bands and the wheel discs)
CART_IRON6 = [(0.0, "#444E5A"), (0.30, "#2A313A"), (0.55, "#1A1F26"), (0.78, "#2A211A"), (1.0, "#4E2C16")]   # rust in the crevices
CART_IRONW6 = [(0.0, "#A6B0BC"), (0.30, "#848E9A"), (0.55, "#626A76"), (0.78, "#52463C"), (1.0, "#5E3822")]


def _wood6_vfn(sdf_, seed=7):
    """v for CART_WOOD6: umber timber (0.55) with darker grain streaks along the planks, a few dark KNOTS (sparse
    low-frequency noise blobs stretched along the grain), and lighter WORN edges broken up into chips."""
    from sdf import value_noise3
    wear = D.wear_vfn(sdf_, width=0.012, seed=seed, gain=1.0)
    grain = D.grain_vfn(freq=46.0, axis=0, seed=seed)

    def fn(v):
        p = np.asarray(v, np.float32)
        g = grain(v)
        kn = np.clip((value_noise3(p * np.array([0.30, 1.0, 1.0], np.float32), freq=5.5, seed=seed + 3) - 0.60) / 0.10, 0, 1)
        chip = np.clip((value_noise3(p, freq=22.0, seed=seed + 5) + 0.10) / 0.40, 0, 1)
        w = np.clip(wear(v) * (0.55 + 0.75 * chip), 0, 1)
        vv = 0.55 - 0.13 * g
        vv = vv * (1 - kn) + 0.03 * kn
        return np.clip(vv + (0.97 - vv) * w, 0, 1)
    return fn


def mine_cart4(center=(0, 0, 0), s=1.0, tag="", post=None):
    """v6 (the finish judge on v5: "the planks read as streaky brushed copper ... the iron as uniform mid-grey plastic
    tube. FIX: darker, less saturated umber timber with grain and a few knots, end grain, rounded or chipped edges;
    near-black blued iron with edge-wear highlights and a little rust staining at the rivets"): mine_cart3's geometry
    and rivets with a matte umber timber (grain + knots + chipped worn edges, rough 0.72) and near-black blued iron
    (bright worn edges; rust where the obscurance is deep -- round the rivet heads, under the rim)."""
    out = []
    for n, q, m, vx in mine_cart3(center, s, tag, post):
        if n == "cartTub":
            m = Material(f"c_wood6{tag}", "#80624A", roughness=0.72, ior=1.26, texture=FUR.lut_v(CART_WOOD6), texture_size=(128, 64))
            m.__dict__["_vfn"] = _wood6_vfn(q, 7)
        elif n in ("cartBands", "cartWheels"):
            m = K.skin(f"c_iron6{n}{tag}", CART_IRON6, CART_IRONW6, vfn=D.wear_vfn(q, width=0.006, seed=11, gain=0.30),
                       rough=0.42, ior=1.45, clearcoat=0.08, cc_rough=0.24)
        elif n == "cartRivets":
            m = K.skin(f"c_rivet6{tag}", [(0.0, "#8A949E"), (0.35, "#4A5058"), (0.7, "#2A2420"), (1.0, "#4A2A16")], None,
                       rough=0.30, ior=1.5, clearcoat=0.30, cc_rough=0.10)
        out.append((n, q, m, vx))
    return out


def _tip_p(P, deg, pivot):
    """the point form of _tip (a model point on the tipped cart)."""
    pv = np.asarray(pivot, float)
    R = K.rotate_matrix((1, 0, 0), deg)
    return (np.asarray(P, float) - pv) @ R.T + pv


# --- THE HERO v6: the cart raised under the label, the near glove on the front rim, the far glove waving
_HERO6_Z = 0.10
_CART6_S = 0.80
_CART6_Y = 0.12              # (-0.02 put the rim top at 764 pt: the near glove's fingers hung into the label)
_CART6_TIP = 8.0
_CART6_PIVOT = (0.0, -0.06 * _CART6_S + _CART6_Y, 0.36 * _CART6_S + _HERO6_Z)


def _cart6_w(P):
    """cart-local point (mine_cart2's frame: floor centre origin, front +Z) -> the hero model's world (placed + tipped)."""
    return _tip_p(np.asarray(P, float) * _CART6_S + np.array([0.0, _CART6_Y, _HERO6_Z]), _CART6_TIP, _CART6_PIVOT)


def _tip6(q):
    return _tip(q, deg=_CART6_TIP, pivot=_CART6_PIVOT)


_R_TIP6 = K.rotate_matrix((1, 0, 0), _CART6_TIP)
_FWD6 = _R_TIP6 @ np.array([0.0, 0.0, 1.0])          # the cart's front, tipped
_UP6 = _R_TIP6 @ np.array([0.0, 1.0, 0.0])
_GRIP_R6 = 0.155 * 1.35                               # the near glove (paw_s 1.35)
_RIM_GRIP = _cart6_w((0.50, 0.815, 0.545))            # on the rim's top, just behind its front edge (local z 0.625)
_GRIP_C = _RIM_GRIP + _UP6 * (_GRIP_R6 * 0.52 + 0.014)
_GRIP_D = K.unit(_FWD6 - _UP6 * 0.12)
_GRIP_WR = _GRIP_C - _GRIP_D * _GRIP_R6 * 0.88
# (the raised cart's floor is above his rest-pose soles: the legs fold up short inside the tub, nothing pokes out below)
HERO6 = C.spec_with(VB4, **V6, lean=16.0, twist=0.0, laugh=1.36, eye_scale=1.50, lids_open=0.93,
                    head=dict(yaw=4.0, roll=-5.0, nod=-8.0), hat=dict(lamp=True, goggles=True, tilt=-16.0, roll=-8.0),
                    legs=dict(L=((-0.27, 0.36, 0.06), (-0.31, 0.33, 0.14), (-0.32, 0.31, 0.20)),
                              R=((0.27, 0.36, 0.06), (0.31, 0.33, 0.14), (0.32, 0.31, 0.20))))
HERO6 = C.spec_with(HERO6, look=_look_cam(-24.0, 4.0, es=1.50, up=0.04),
                    arms=dict(R=_world_arm(HERO6, el=(0.70, 0.99, 0.30), wr=tuple(_GRIP_WR), d=tuple(_GRIP_D), palm=tuple(-_UP6),
                                           curl=104.0, spread=16.0, paw_s=1.35, thumb_curl=40.0),
                              L=_world_arm(HERO6, el=(-0.74, 1.42, 0.24), wr=(-0.86, 1.80, 0.34), d=(-0.20, 1.0, 0.15),
                                           palm=(0.40, 0.20, 0.90), curl=16.0, spread=30.0, paw_s=1.1)))
_HERO6_ARROWS = [("tangerine", (-0.50, 0.98, _HERO6_Z - 0.34), (-0.42, 1.0, -0.10), (0.10, 0.0, 1.0), 1.24, 0.76),
                 ("sunflower", (0.52, 1.02, _HERO6_Z - 0.38), (0.50, 1.0, -0.12), (-0.12, 0.0, 1.0), 1.16, 0.72)]


def _hero6_extra(ctx):
    cart = mine_cart4(center=(0.0, _CART6_Y, _HERO6_Z), s=_CART6_S, tag="h6", post=_tip6)
    arrows = garrows(_HERO6_ARROWS, tag="h6")
    arrows += garrow("coral", (0.84, 0.96, _HERO6_Z - 0.26), (0.85, 0.45, 0.10), (0.10, -0.15, 1.0), 0.70, 0.46, "h6s")
    return cart + [(n, _tip6(s_), m, v) for n, s_, m, v in arrows]


MODELS["dig_cart"] = lambda: _vdig(HERO6, _V5_VIEW_POSE, key="lk6_hero", seed=41, extra=_hero6_extra)
ASSETS["char_digCart"] = dict(ASSETS["char_digCart"], light=_light5(0.9, shadow=False),
                              anchors={"eyeMid": [_eye_anchor(HERO6)], "feet": [[0.0, _CART6_Y - 0.25 * _CART6_S, _HERO6_Z]]})


# --- the FRONT RUNNER v6: the same arrow on his shoulder, his glove GRIPPING its shaft's edge
def _runner_arrow6():
    """the v5 runner's arrow (placed from the v5 paw): (centre, frame R with columns x (across the shaft), y (the
    point), z (the face)) -- v6 keeps the arrow exactly where it was and moves the paw onto it."""
    bx = C.BodyXf(RUNNER5.get("lean", 0.0), RUNNER5.get("twist", 0.0), RUNNER5.get("body_roll", 0.0))
    A = RUNNER5["arms"]["R"]
    pc = bx.p(A["wr"]) + bx.n(K.unit(A["d"])) * 0.155 * 0.95
    ax = K.unit([0.30, 0.80, -0.52])
    return pc + ax * 0.52 + np.array([0.04, 0.0, 0.0]), K.frame_from(ax, (0.35, 0.30, 1.0))


_RA_C, _RA_R = _runner_arrow6()
_RA_S = 0.80 * 0.54 / 2                                # the shaft's half-width (garrow: shaft = W * 0.54)
_RA_T = 0.17 / 2                                       # its half-depth
_RG_R = 0.155
# grip the shaft 0.40 below the arrow's centre at the edge nearer the runner's right elbow; the palm on that edge,
# the fingers wrapping over the FRONT face (toward the camera), the thumb on the back
_ex, _ey, _ez = _RA_R[:, 0], _RA_R[:, 1], _RA_R[:, 2]
_el5 = C.BodyXf(RUNNER5.get("lean", 0.0), RUNNER5.get("twist", 0.0)).p(RUNNER5["arms"]["R"]["el"])
_side = min((-1.0, 1.0), key=lambda sgn: np.linalg.norm(_RA_C - _ey * 0.40 + _ex * sgn * _RA_S - _el5))
_EDGE = _RA_C - _ey * 0.40 + _ex * _side * _RA_S
_RG_PN = -_ex * _side                                  # the palm faces into the edge
_RG_D = _ez                                            # the fingers reach toward the front face, then curl over it
_RG_C = _EDGE + _ex * _side * (_RG_R * 0.52 + 0.010) - _ez * 0.020
_RG_WR = _RG_C - _RG_D * _RG_R * 0.88
RUNNER6 = C.spec_with(RUNNER5, **V6, lids_open=0.92)
RUNNER6 = C.spec_with(RUNNER6, arms=dict(R=_world_arm(RUNNER6, el=tuple(_el5), wr=tuple(_RG_WR), d=tuple(_RG_D), palm=tuple(_RG_PN),
                                                      curl=100.0, spread=12.0, claw_bend=30.0, thumb_curl=30.0),
                                         L=RUNNER5["arms"]["L"]))


def _runner6_extra(ctx):
    return garrow("tangerine", _RA_C, _RA_R[:, 1], (0.35, 0.30, 1.0), 1.36, 0.80, "rn")


MODELS["dig_flyer"] = lambda: _vdig(RUNNER6, dict(yaw=-30, pitch=8), key="lk6_runner", seed=53, extra=_runner6_extra)
ASSETS["char_digFlyer"] = dict(ASSETS["char_digFlyer"], anchors={"eyeMid": [_eye_anchor(RUNNER6)]})

# --- the ARROW SURFER v6, the back pair v6 (the cheerer: ^ ^ eyes, goggles on a hat), the dock pair v6
SURFER6 = C.spec_with(SURFER5, **V6, lids_open=0.92)
MODELS["dig_pop2"] = lambda: _vdig(SURFER6, dict(yaw=8, pitch=6), key="lk6_surfer", seed=43, extra=_surfer_extra)
ASSETS["char_digPop2"] = dict(ASSETS["char_digPop2"], anchors={"eyeMid": [_eye_anchor(SURFER6)]})
PAIR_A6 = C.spec_with(PAIR_A5, **V6, lids_open=0.92, eyes="joy", goggles_down=False,
                      hat=dict(lamp=False, goggles=True, tilt=-12.0, roll=-8.0))
PAIR_B6 = C.spec_with(PAIR_B5, **V6, lids_open=0.92)
MODELS["dig_pairA"] = lambda: _vdig(PAIR_A6, dict(yaw=-36, pitch=8), key="lk6_pairA", seed=47)
MODELS["dig_pairB"] = lambda: _vdig(PAIR_B6, dict(yaw=-36, pitch=8), key="lk6_pairB", seed=49, extra=_pair_b_extra)
ASSETS["char_digPop1"] = dict(ASSETS["char_digPop1"], anchors={"eyeMid": [_eye_anchor(PAIR_A6)]})
MODELS["dig_dockA"] = lambda: _vdig(C.spec_with(PAIR_A6, girth=1.0, height=1.0, scarf="sky", hat=False, eyes="open",
                                                head=dict(yaw=10.0, roll=-6.0, nod=-4.0), look=(0.30, 0.1)),
                                    dict(yaw=40, pitch=8), key="lk6_dockA", seed=57)
MODELS["dig_dockB"] = lambda: _vdig(C.spec_with(RUNNER6, skin_tint="a2", scarf=None, head=dict(yaw=12.0, roll=6.0, nod=-4.0),
                                                look=(0.30, 0.1), hat=dict(lamp=True, goggles=True, tilt=-12.0, roll=-6.0)),
                                    dict(yaw=40, pitch=8), key="lk6_dockB", seed=59, extra=_runner6_extra)


# --- THE BOSS v6: style "load5", real work boots, the aged-brass lantern, a top light for the fur's crown sheen
BOOT6 = [(0.0, "#A87248"), (0.35, "#7E4E2E"), (0.70, "#553018"), (1.0, "#2E1606")]
BOOT6_STRAP = [(0.0, "#8A5A34"), (0.40, "#633C1E"), (0.80, "#42240E"), (1.0, "#261204")]


def _sole6_sdf(R, c, hw=0.205, hl=0.280, t=0.032, spring=0.060):
    """an outsole slab under a boot (foot frame R: x across, y toe, z up; centre c): an elliptic footprint, `t` half
    thick, its front third curving UP (the toe-spring)."""
    Rm = np.asarray(R, np.float32)
    c32 = np.asarray(c, np.float32)

    def f(p):
        q = (np.asarray(p, np.float32) - c32) @ Rm
        x, y, z = q[:, 0], q[:, 1], q[:, 2]
        yy = np.clip((y - 0.05) / (hl - 0.05), 0, 1)
        zc = z - spring * yy ** 2
        d2 = (np.sqrt((x / hw) ** 2 + (y / hl) ** 2) - 1.0) * min(hw, hl)
        dz = np.abs(zc) - t
        o = np.stack([np.maximum(d2, 0), np.maximum(dz, 0)], 1)
        return ((np.minimum(np.maximum(d2, dz), 0) + np.linalg.norm(o, axis=1)) * 0.85).astype(np.float32)
    return _SDF(f, np.asarray(c, float) - 0.40, np.asarray(c, float) + 0.40)


def boss_boots6(feet_pts):
    """v6 (the finish judge on v5: "the boots are smooth clay cylinders on flat puck-disc soles, and their two white
    dots read as a pair of eyes. FIX: a real sole with heel and toe-spring, a strap or laces instead of the two dots,
    ankle creases, leather roughness about 0.55"): a leather upper (a toe box + the shaft, two creases across the
    ankle's front, a rolled top), a dark rubber outsole with a toe-spring and a raised HEEL block, an instep STRAP with
    a small aged-brass buckle on the outer side. -> [(name, sdf, mat, voxel)] in the leg space (the caller scales)."""
    from char_crew_d1 import _halfspace
    uppers, soles, straps, buckles, rims = [], [], [], [], []
    for foot_c, R, hip, knee, ank in feet_pts:
        ex, ey, ez = R[:, 0], R[:, 1], R[:, 2]
        up = knee if knee is not None else hip
        top = ank + (up - ank) * 0.42
        foot = K.local_ellipsoid((0.186, 0.250, 0.112), R, foot_c + ey * 0.015 + ez * 0.014)
        toe = K.local_ellipsoid((0.170, 0.125, 0.090), R, foot_c + ey * 0.150 + ez * 0.004)
        shaft = round_cone(tuple(top), tuple(ank + ez * 0.02), 0.186, 0.178)
        upper = union(foot, toe, shaft, k=0.07)
        ax = K.unit(up - ank)
        for dz in (0.045, 0.095):
            cr = torus(0.184, 0.0085).transform(K.frame_from(ax, ey)).translate(*(ank + ax * dz))
            upper = upper.subtract(cr.intersect(_halfspace(ank + ey * 0.06, ey), k=0.01), k=0.006)
        sole_c = foot_c + ey * 0.020 - ez * 0.086
        upper = upper.subtract(K.local_ellipsoid((0.30, 0.36, 0.30), R, sole_c - ez * 0.29), k=0.012)
        sole = _sole6_sdf(R, sole_c)
        heel = box(0.160, 0.080, 0.034, round=0.016).transform(R).translate(*(sole_c - ey * 0.180 - ez * 0.050))
        soles.append(union(sole, heel, k=0.018))
        uppers.append(upper)
        band = foot.offset(0.016).subtract(foot.offset(-0.03)).intersect(
            box(0.40, 0.034, 0.40, round=0.012).transform(R).translate(*(foot_c + ey * 0.075)), k=0.006)
        straps.append(band.intersect(_halfspace(foot_c + ez * 0.0, ez), k=0.02))
        sx = 1.0 if foot_c[0] >= 0 else -1.0
        bp = foot_c + ey * 0.075 + ex * sx * 0.190 + ez * 0.045
        bn = K.unit(ex * sx + ez * 0.35)
        buckles.append(box(0.030, 0.026, 0.008, round=0.006).subtract(box(0.016, 0.013, 0.05, round=0.004))
                       .transform(K.frame_from(ey, bn)).translate(*bp))
        rims.append(torus(0.184, 0.020).transform(K.frame_from(ax, [1.0, 0.0, 0.0])).translate(*top))
    return [("boots", union(*uppers), K.skin("bb6_upper", BOOT6, None, rough=0.55, ior=1.32), 0.004),
            ("bootRims", union(*rims), K.skin("bb6_rim", BOOT6, None, rough=0.58, ior=1.30), 0.0025),
            ("bootSoles", union(*soles), K.skin("bb6_sole", C.BOOT_SOLE_M, None, rough=0.85, ior=1.2), 0.003),
            ("bootStraps", union(*straps), K.skin("bb6_strap", BOOT6_STRAP, None, rough=0.50, ior=1.30), 0.0025),
            ("bootBuckles", union(*buckles), K.skin("bb6_buckle", D.BRASS5_LUT, None, rough=0.36, ior=1.5), 0.0015)]


def boss_legs6(pose="load_d1b", s=BOSS_LEG_S):
    Rt, tb = _boss_torso_xf(pose)
    hip_c = Rt @ np.array([0.0, 0.30, -0.08]) + tb
    legs, _soles, feet = C.legs_sdf(_BOSS_LEGS, 1.0)
    off = np.array([hip_c[0], hip_c[1] - 0.36 * s, hip_c[2]])

    def xf(q):
        return q.scale(s).translate(*off)
    out = [("trousers", xf(union(*legs, k=0.02)), K.skin("bl_trouser4", BOSS_TROUSER, None, vfn=None, rough=0.84, ior=1.18), 0.006)]
    for n, sdf_, m, vx in boss_boots6(feet):
        out.append((f"boss_{n}", xf(sdf_), m, vx * 1.3))
    return out, float(off[1] + s * (-0.12))


def _boss6():
    lan = D.place_parts(D.lantern_lit5(1.45), t=boss_lantern_pos())
    legs, _ = boss_legs6()
    return CB.boss_v2("load_d1b", mouth="smile2", eyes="open", with_station=False, arms=_BOSS_ARMS3,
                      hands=dict(L="point", R="grip"), extra=_P(lan + legs), look=(0.04, 0.02), view_pose=dict(yaw=0, pitch=4),
                      style="load5", n_strands=26000)


MODELS["boss_loading"] = _boss6


def _boss_lights6():
    """the lantern's warm point light (stronger, a little oranger) + a soft TOP light (the fur's crown / cheek-top sheen)."""
    import uikit
    # (r2: the light 0.12 in FRONT of the globe blew the frame's front faces out to a pale lemon -- now at the flame,
    # inside the glass: the cage is lit from within, its outer faces keep the tarnished brass)
    p = boss_lantern_pos() + np.array([0.0, -0.45, 0.0])
    q = uikit.rot_x(4.0) @ p
    return [dict(type="point", position=[float(v) for v in q], intensity=7000.0, color=[1.0, 0.64, 0.28], attenuation=2.0),
            dict(type="directional", direction=[0.12, -1.0, -0.22], intensity=1600.0, color=[1.0, 0.97, 0.94], shadow=False)]


def lantern_halo6(im):
    """v6 post_fit: lantern_halo with a warmer, WIDER spill (the judge: "the glow on the mitten and face is weak ...
    a larger soft warm spill on the fur mitten and the right side of his face")."""
    fx, fy = _frame_pt("char_bossLoading", boss_lantern_pos() + np.array([0.0, -0.44, 0.0]))
    a = np.asarray(im.convert("RGBA")).astype(np.float64) / 255
    h, w = a.shape[:2]
    yy, xx = np.mgrid[0:h, 0:w]
    d2 = ((xx + 0.5) / 3 - fx) ** 2 + ((yy + 0.5) / 3 - fy) ** 2
    g = 0.16 * np.exp(-d2 / (2 * 6.0 ** 2)) + 0.16 * np.exp(-d2 / (2 * 18.0 ** 2))     # (r2: 0.46 core washed the lantern pale)
    al = a[..., 3:4]
    spill = 0.22 * np.exp(-d2 / (2 * 38.0 ** 2))[..., None] * al        # the warm spill: on the figure only
    warm = np.array([1.0, 0.72, 0.36])
    pre = a[..., :3] * al + warm * g[..., None] + warm * spill * (1 - a[..., :3]) * 0.9
    na = 1 - (1 - al) * (1 - g[..., None])
    rgb_ = np.clip(pre / np.maximum(na, 1e-6), 0, 1)
    out = np.concatenate([rgb_, np.clip(na, 0, 1)], -1)
    from PIL import Image as _I
    return _I.fromarray((out * 255 + 0.5).astype(np.uint8), "RGBA")


# (key up, fill down: the fur's value range was compressed -- L* p50 56 / p95 68 vs the original's 50 / 75)
ASSETS["char_bossLoading"] = dict(ASSETS["char_bossLoading"], light=_light5(0.15, shadow=False, rim_lux=1900.0,
                                                                            rim_color=(1.0, 0.92, 0.80), extra=_boss_lights6(),
                                                                            key_lux=3400.0, fill_lux=520.0),
                                  ss=3, post_fit=lantern_halo6,
                                  anchors={"eyeMid": [boss_eye_anchor(style="load4")], "feet": [[0.0, _BOSS_FEET_Y, 0.30]]})


# ================================================================== event figures

CLAW_L = C.spec_with(C.BASE, head=dict(yaw=10.0, roll=-10.0, nod=-6.0), look=(0.20, 0.30), mouth="grin", brows="raised",
                     trowel=False, hat=dict(lamp=True, goggles=True, tilt=-8.0, roll=8.0),
                     arms=dict(L=dict(el=(-0.74, 1.42, 0.14), wr=(-0.76, 1.84, 0.28), d=(-0.1, 1.0, 0.2), palm=(0.2, 0.0, 1.0),
                                      curl=14.0, spread=28.0),
                               R=dict(el=(0.74, 1.42, 0.14), wr=(0.70, 1.86, 0.30), d=(0.1, 1.0, 0.2), palm=(-0.2, 0.0, 1.0),
                                      curl=100.0, spread=12.0, claw_bend=60.0, claw_len=0.05)))
CLAW_R = C.spec_with(C.BASE, girth=0.96, head=dict(yaw=-12.0, roll=8.0, nod=-2.0), look=(-0.20, 0.10), mouth="open", brows="raised",
                     eyes="open", fur="sage", goggles_down=True, trowel=False, hat=dict(lamp=False, goggles=False, tilt=-14.0, roll=-8.0),
                     arms=dict(L=dict(el=(-0.62, 0.98, 0.34), wr=(-0.30, 1.28, 0.60), d=(0.5, 0.6, 0.5), palm=(0.3, -0.2, -1.0),
                                      curl=100.0, spread=12.0, claw_bend=60.0, claw_len=0.05),
                               R=dict(el=(0.62, 0.98, 0.34), wr=(0.30, 1.30, 0.62), d=(-0.5, 0.6, 0.5), palm=(-0.3, -0.2, -1.0),
                                      curl=100.0, spread=12.0, claw_bend=60.0, claw_len=0.05)))
MODELS["dig_clawL"] = lambda: _dig(CLAW_L, dict(yaw=14, pitch=6), key="dig_clawL", seed=61, n=120000)
MODELS["dig_clawR"] = lambda: _dig(CLAW_R, dict(yaw=-16, pitch=6), key="dig_clawR", seed=67, n=120000)
_CLAW_FRAME = (360, 170)
_CLAW_VIEW = K.view_bounds(_CLAW_FRAME, scale_pt=84.0, center=(0.0, 1.62), zr=(-1.0, 1.2), margin=1.0)
ASSETS["char_digClawPair"] = dict(scene=[("dig_clawL", dict(yaw=14, pitch=6, pos=(-0.92, 0.0, 0.0), center=False)),
                                         ("dig_clawR", dict(yaw=-16, pitch=6, pos=(0.95, 0.06, -0.10), center=False))],
                                  bounds=_CLAW_VIEW, frame=_CLAW_FRAME, fov=18, light=D.LIGHT_D1, no_fit=True, full_bleed=True)

RACER = C.spec_with(C.BASE, head=dict(yaw=-10.0, roll=-6.0, nod=-4.0), look=(-0.10, 0.10), mouth="grin", brows="determined",
                    trowel=False, hat=dict(lamp=True, goggles=True, tilt=-4.0, roll=-6.0),
                    arms=dict(L=dict(el=(-0.66, 0.98, 0.38), wr=(-0.56, 0.90, 0.78), d=(0.05, -0.55, 1.0), palm=(0.0, -1.0, 0.2),
                                     curl=90.0, spread=14.0, claw_bend=60.0, claw_len=0.05),
                              R=dict(el=(0.72, 1.40, 0.16), wr=(0.74, 1.80, 0.30), d=(0.05, 1.0, 0.2), palm=(-0.2, 0.0, 1.0),
                                     curl=18.0, spread=26.0)))


def _racer_extra(ctx):
    cart = [(n, s_.translate(0, -0.10, 0), m, v) for n, s_, m, v in mine_cart(center=(0.0, 0.0, 0.0), s=1.0, tag="r")]
    # a short stretch of track under the cart (two iron rails under the wheels, timber sleepers), along its travel (+Z)
    rails = union(*[capsule((sx * 0.80, -0.42, -1.1), (sx * 0.80, -0.42, 1.1), 0.035) for sx in (-1, 1)])
    sleepers = union(*[box(1.0, 0.03, 0.07, round=0.015).translate(0, -0.47, zz) for zz in np.linspace(-0.95, 0.95, 6)])
    return cart + [("rails", rails, K.skin("c_rail", C.IRON_LUT, None, rough=0.35, ior=1.45), 0.004),
                   ("sleepers", sleepers, K.skin("c_sleeper", D.WOOD0, D.WOOD1, vfn=D.grain_vfn(30, 0, 9), rough=0.7, ior=1.25), 0.006)]


MODELS["dig_racer"] = lambda: _dig(RACER, dict(yaw=44, pitch=14), key="dig_racer", seed=71, n=100000, extra=_racer_extra)


_RACE_FRAME = (393, 210)
_RACE_VIEW = K.view_bounds(_RACE_FRAME, scale_pt=50.0, center=(0.0, 0.62), zr=(-3.2, 2.0), margin=1.0, fov=24.0)
ASSETS["char_digRacers"] = dict(scene=[("dig_racer", dict(yaw=50, pitch=14, pos=(-2.30, 0.30, -2.25), scale=0.66, center=False)),
                                       ("dig_racer", dict(yaw=46, pitch=14, pos=(-0.70, 0.12, -0.80), scale=0.82, center=False)),
                                       ("dig_racer", dict(yaw=42, pitch=14, pos=(1.20, -0.10, 0.80), scale=1.0, center=False))],
                                bounds=_RACE_VIEW, frame=_RACE_FRAME, fov=24, light=D.LIGHT_D1, no_fit=True, full_bleed=True)

BALLOONIST = C.spec_with(C.BASE, head=dict(yaw=6.0, roll=-6.0, nod=-10.0), look=(0.10, 0.40), mouth="grin", brows="raised",
                         trowel=False, hat=dict(lamp=True, goggles=True, tilt=-12.0, roll=6.0),
                         arms=dict(L=dict(el=(-0.72, 1.40, 0.16), wr=(-0.78, 1.80, 0.30), d=(-0.12, 1.0, 0.2), palm=(0.2, 0.0, 1.0),
                                          curl=14.0, spread=28.0),
                                   R=dict(el=(0.64, 0.96, 0.40), wr=(0.56, 0.96, 0.74), d=(0.05, -0.6, 1.0), palm=(0.0, -1.0, 0.1),
                                          curl=80.0, spread=18.0, claw_bend=55.0, claw_len=0.06)))


def _balloon_extra(ctx):
    # the floor under the feet (R2 v1's basket floated above them), the rim at the belt
    return wicker_basket(center=(0.0, -0.05, 0.06), r=0.70, h=0.86)


MODELS["dig_balloon"] = lambda: _dig(BALLOONIST, dict(yaw=10, pitch=8), key="dig_balloon", seed=73, n=100000, extra=_balloon_extra)
_BAL_FRAME = (150, 176)
_BAL_VIEW = K.view_bounds(_BAL_FRAME, scale_pt=56.0, center=(0.0, 1.30), zr=(-1.0, 1.1), margin=1.0)
ASSETS["char_digBalloon"] = dict(scene=[("dig_balloon", dict(yaw=10, pitch=8, center=False))], bounds=_BAL_VIEW, frame=_BAL_FRAME,
                                 fov=18, light=D.LIGHT_D1, no_fit=True,
                                 anchors={"ropeTL": [[-0.68, 1.43, -0.55]], "ropeTR": [[0.68, 1.43, -0.55]],
                                          "ropeFL": [[-0.68, 1.43, 0.67]], "ropeFR": [[0.68, 1.43, 0.67]]})


# ================================================================== avatars (64 x 64 pt portraits on D1 plates)

AV_FRAME = (64, 64)
AV_SCALE = 36.0
PLATES = {   # (centre, edge) of a soft radial gradient (D1 palette; none of the original's pink / purple / green set)
    "honey": ("#FFE39A", "#F0A23A"), "teal": ("#7FEADB", "#138E86"), "sky": ("#C8F4FF", "#3FA8D8"),
    "moss": ("#D6F08A", "#6FA83A"), "amber": ("#FFD27A", "#D9731E"), "coral": ("#FFB39C", "#E0503A"),
    "crystal": ("#D8FAFF", "#5FC6E0"), "dusk": ("#8FA8C8", "#2E4A6E"),
}


def _plate(colours):
    c0, c1 = (K.hexrgb(h) for h in colours)

    def post(im):
        from PIL import Image as _I
        W_, H_ = im.size
        yy, xx = np.mgrid[0:H_, 0:W_]
        r = np.clip(np.hypot((xx - W_ * 0.45) / W_, (yy - H_ * 0.38) / H_) / 0.75, 0, 1)[..., None]
        col = c0 * (1 - r) + c1 * r
        bg = _I.fromarray((col * 255).astype(np.uint8)).convert("RGBA")
        bg.alpha_composite(im)
        return bg
    return post


def party_hat(top, tilt=18.0):
    cone = capped_cone(0.40, 0.23, 0.02, round=0.02).translate(0, top + 0.16, 0.0)
    dots = []
    rng = np.random.default_rng(4)
    for i in range(14):
        t = 0.1 + 0.8 * rng.random()
        a = rng.random() * 2 * math.pi
        r = 0.23 * (1 - t) + 0.02 * t + 0.008
        dots.append(sphere(0.026).translate(r * math.cos(a), top - 0.04 + t * 0.40, r * math.sin(a)))
    pom = sphere(0.07).translate(0, top + 0.38, 0)
    R = K.rotate_matrix((0, 0, 1), -tilt)
    piv = np.array([0, top - 0.1, 0])

    def xf(s):
        return s.translate(*(-piv)).transform(R).translate(*piv).translate(0.10, 0, -0.04)
    return [("partyHat", xf(cone), K.skin("c_party", [(0.0, "#8CF0E0"), (0.5, "#17B3A3"), (1.0, "#075E5E")], None, rough=0.45, ior=1.3), 0.003),
            ("partyDots", xf(union(*dots)), K.skin("c_pdots", [(0.0, "#FFE88A"), (0.5, "#FFCB2F"), (1.0, "#B77C04")], None, rough=0.4, ior=1.3), 0.002),
            ("partyPom", xf(pom), K.skin("c_ppom", [(0.0, "#FFC46A"), (0.5, "#FF9A12"), (1.0, "#A84E00")], None, rough=0.7, ior=1.2), 0.003)]


def nightcap(hx):
    """A striped knitted nightcap flopping to one side, a pom-pom at its tip (head space via hx)."""
    pts = [np.array([0.0, 1.88, 0.02]), np.array([0.10, 2.12, 0.0]), np.array([0.32, 2.20, -0.02]), np.array([0.52, 2.02, 0.02])]
    cone = K.limb(pts, [0.40, 0.26, 0.14, 0.07], k=0.06).intersect(D.slab_y(1.80, 3.0), k=0.02)
    brim = torus(0.40, 0.06).translate(0, 1.86, 0.03)
    pom = sphere(0.10).translate(*(pts[-1] + np.array([0.04, -0.08, 0.0])))
    knit = K.skin("c_knit", [(0.0, "#9FD8FF"), (0.5, "#4F8FD0"), (1.0, "#22457A")], [(0.0, "#FFF4DA"), (0.5, "#E8D7AF"), (1.0, "#A89060")],
                  vfn=lambda v: (np.sin(np.asarray(v)[:, 1] * 55.0) > 0).astype(float), rough=0.85, ior=1.2)
    return [("nightcap", hx.sdf(cone), knit, 0.004), ("capBrim", hx.sdf(brim), K.skin("c_capbrim", [(0.0, "#FFFCF0"), (1.0, "#D8C8A4")], None, rough=0.9, ior=1.2), 0.004),
            ("capPom", hx.sdf(pom), K.skin("c_cappom", [(0.0, "#FFFCF0"), (1.0, "#D8C8A4")], None, rough=0.9, ior=1.2), 0.004)]


def magnifier(center, handle_dir, lens_n):
    c = np.asarray(center, float)
    R = K.frame_from(lens_n, [0, 1, 0])
    ring = torus(0.13, 0.022).transform(K.frame_from(lens_n, [1, 0, 0])).translate(*c)
    lens = cylinder(0.12, 0.008).transform(K.frame_from(lens_n, [1, 0, 0])).translate(*c)
    h0 = c + K.unit(handle_dir) * 0.15
    handle = capsule(tuple(h0), tuple(h0 + K.unit(handle_dir) * 0.26), 0.030)
    del R
    return [("magRing", ring, K.skin("c_magring", D.BRASS_LUT, None, rough=0.26, ior=1.5), 0.002),
            ("magLens", lens, glass("c_maglens", "#DFF7FF", opacity=0.30), 0.002),
            ("magHandle", handle, K.skin("c_maghandle", D.WOOD0, D.WOOD1, vfn=D.grain_vfn(60, 1), rough=0.5, ior=1.25), 0.003)]


def lunch_pail(center, s=1.0):
    c = np.asarray(center, float)
    tin = box(0.20 * s, 0.13 * s, 0.13 * s, round=0.04 * s).translate(*c)
    lid = ellipsoid(0.21 * s, 0.08 * s, 0.135 * s).intersect(D.slab_y(0, 1)).translate(*(c + np.array([0, 0.12 * s, 0])))
    handle = torus(0.11 * s, 0.014 * s).transform(K.rotate_matrix((1, 0, 0), 90)).intersect(D.slab_y(0.0, 1.0)).translate(
        *(c + np.array([0, 0.20 * s, 0])))
    return [("pail", union(tin, lid, k=0.01), D.painted_metal("c_pail", [(0.0, "#FF9C86"), (0.45, "#F2553F"), (0.8, "#C23A26"), (1.0, "#8A2414")],
                                                              C.STEEL_WORN, union(tin, lid), rough=0.36, width=0.006), 0.003),
            ("pailHandle", handle, metal("c_pailh", "#C9CED4", rough=0.3), 0.002)]


def pickaxe(center, shaft_dir, head_dir):
    c = np.asarray(center, float)
    sd, hd = K.unit(shaft_dir), K.unit(head_dir)
    shaft = capsule(tuple(c - sd * 0.55), tuple(c + sd * 0.45), 0.035)
    top = c + sd * 0.45
    pick = K.limb([top - hd * 0.42 - sd * 0.05, top, top + hd * 0.42 - sd * 0.05], [0.02, 0.055, 0.02], k=0.02)
    return [("pickShaft", shaft, K.skin("c_pickwood", D.WOOD0, D.WOOD1, vfn=D.grain_vfn(70, 1), rough=0.55, ior=1.25), 0.003),
            ("pickHead", pick, D.painted_metal("c_pickhead", C.STEEL_PAINT, C.STEEL_WORN, pick, rough=0.32, width=0.01), 0.0025)]


# the 8 portraits: id -> (spec, view pose, plate, extra-parts fn)
_AV_ARM_DOWN = dict(L=dict(el=(-0.62, 0.92, 0.12), wr=(-0.60, 0.72, 0.30), d=(0.2, -0.85, 0.45), palm=(0.55, 0.05, -0.85), curl=26.0, spread=20.0),
                    R=dict(el=(0.62, 0.92, 0.12), wr=(0.60, 0.72, 0.30), d=(-0.2, -0.85, 0.45), palm=(-0.55, 0.05, -0.85), curl=26.0, spread=20.0))
_WAVE_R = dict(el=(0.66, 1.30, 0.20), wr=(0.70, 1.60, 0.34), d=(0.10, 1.0, 0.12), palm=(-0.18, 0.0, 1.0), curl=12.0, spread=26.0)


def _av(spec, **kw):
    return C.spec_with(C.BASE, **dict(dict(trowel=False, arms=_AV_ARM_DOWN), **kw)) if spec is None else spec


AVATARS = {
    "avatarMiner": (_av(None, head=dict(yaw=8.0, roll=-6.0, nod=0.0), look=(0.0, 0.05), mouth="grin", brows="raised",
                        hat=dict(lamp=True, goggles=True, tilt=-8.0, roll=6.0), arms=dict(_AV_ARM_DOWN, R=_WAVE_R)),
                    dict(yaw=-10, pitch=4), "honey", None),
    "avatarMapper": (_av(None, head=dict(yaw=-8.0, roll=5.0, nod=4.0), look=(0.10, -0.05), mouth="smile", brows="determined",
                         fur="sage", goggles_down=True, hat=dict(lamp=False, goggles=False, tilt=-14.0, roll=-5.0),
                         arms=dict(L=C.ARM_L_MAP, R=_AV_ARM_DOWN["R"])),
                     dict(yaw=10, pitch=4), "teal", lambda ctx: C.tunnel_map(C._MAP_C + np.array([0.0, 0.1, 0.0]), C._MAP_UP, C._MAP_FACE)),
    "avatarSleuth": (_av(None, head=dict(yaw=10.0, roll=-4.0, nod=0.0), look=(0.0, 0.0), mouth="smile", brows="determined",
                         hat=dict(lamp=True, goggles=False, tilt=-10.0, roll=4.0),
                         arms=dict(_AV_ARM_DOWN, R=dict(el=(0.64, 1.02, 0.30), wr=(0.40, 1.36, 0.62), d=(-0.3, 0.8, 0.4),
                                                        palm=(-0.8, 0.0, 0.4), curl=95.0, spread=12.0, claw_bend=60.0, claw_len=0.05))),
                     dict(yaw=-8, pitch=4), "sky",
                     lambda ctx: magnifier(C.HeadXf(yaw=10.0, roll=-4.0).p(np.array([[0.19, 1.70, 0.74]]))[0], (0.35, -1.0, 0.2), (0.1, 0.05, 1.0))),
    "avatarLunch": (_av(None, head=dict(yaw=-6.0, roll=4.0, nod=2.0), look=(0.0, 0.0), mouth="grin", brows="friendly",
                        hat=dict(lamp=True, goggles=True, tilt=-10.0, roll=-4.0),
                        arms=dict(L=dict(el=(-0.62, 0.90, 0.34), wr=(-0.36, 0.86, 0.66), d=(0.6, 0.15, 0.6), palm=(0.3, 1.0, 0.1),
                                         curl=70.0, spread=14.0, claw_bend=55.0, claw_len=0.05),
                                  R=_AV_ARM_DOWN["R"])),
                    dict(yaw=8, pitch=6), "moss", lambda ctx: lunch_pail(np.array([-0.12, 1.00, 0.80]), s=1.05)),
    "avatarConfetti": (_av(None, head=dict(yaw=6.0, roll=-10.0, nod=0.0), look=(0.0, 0.05), mouth="grin", brows="raised", hat=False,
                        arms=dict(_AV_ARM_DOWN, R=_WAVE_R)),
                    dict(yaw=-8, pitch=4), "coral", lambda ctx: [(n, ctx["hx"].sdf(s_), m, v) for n, s_, m, v in party_hat(2.00)]),
    "avatarStrong": (_av(None, head=dict(yaw=-6.0, roll=6.0, nod=0.0), look=(0.0, 0.0), mouth="grin", brows="determined",
                         hat=dict(lamp=True, goggles=True, tilt=-12.0, roll=-6.0),
                         arms=dict(L=dict(el=(-0.80, 1.24, 0.10), wr=(-0.66, 1.60, 0.26), d=(0.30, 0.90, 0.20), palm=(0.7, -0.3, 0.6),
                                          curl=110.0, spread=12.0, claw_bend=60.0, claw_len=0.05),
                                   R=dict(el=(0.80, 1.24, 0.10), wr=(0.66, 1.60, 0.26), d=(-0.30, 0.90, 0.20), palm=(-0.7, -0.3, 0.6),
                                          curl=110.0, spread=12.0, claw_bend=60.0, claw_len=0.05))),
                     dict(yaw=8, pitch=4), "crystal", None),
    "avatarSleepy": (_av(None, head=dict(yaw=4.0, roll=-12.0, nod=6.0), look=(0.0, 0.0), mouth="smile", eyes="closed",
                         brows="friendly", hat=False, vest=False),
                     dict(yaw=-6, pitch=4), "dusk", lambda ctx: nightcap(ctx["hx"])),
}
_AV_VIEW = K.view_bounds(AV_FRAME, scale_pt=AV_SCALE, center=(0.02, 1.62), zr=(-0.8, 1.1), margin=1.0)
for _id, (_spec, _pose, _plate_name, _extra) in AVATARS.items():
    MODELS[f"av_{_id}"] = (lambda s=_spec, p=_pose, e=_extra, i=_id: _dig(s, p, key=f"av_{i}", n=70000, seed=91, extra=e))
    ASSETS[f"char_{_id}"] = dict(scene=[(f"av_{_id}", dict(_pose, center=False))], bounds=_AV_VIEW, frame=AV_FRAME, fov=18,
                                 light=D.LIGHT_D1_SOFT, no_fit=True, post_fit=_plate(PLATES[_plate_name]), full_bleed=True)

# the case ids, spelled out (manifest_check looks each source case up by name)
AVATAR_CASES = ("char_avatarMiner", "char_avatarMapper", "char_avatarSleuth", "char_avatarLunch", "char_avatarConfetti",
                "char_avatarStrong", "char_avatarSleepy")
assert all(c in ASSETS for c in AVATAR_CASES)

# the boss portrait (slot of avatarScientist): head + collar, open laugh with the fang, looking at the viewer
CB.POSES["portrait_d1"] = dict(yaw=-8.0, lean=0.0, head=dict(roll=-5.0, yaw=6.0, nod=4.0), narrow=0.9)
_BP_ARMS = dict(L=dict(el=(-1.02, 0.80, 0.0), wr=(-0.92, 0.46, 0.22), d=(0.0, -1.0, 0.2), palm=(1.0, 0.0, 0.0), r=0.17),
                R=dict(el=(1.02, 0.80, 0.0), wr=(0.92, 0.46, 0.22), d=(0.0, -1.0, 0.2), palm=(-1.0, 0.0, 0.0), r=0.17))
MODELS["av_avatarBoss"] = lambda: CB.boss_v2("portrait_d1", mouth="open", with_station=False, n_strands=36000, arms=_BP_ARMS,
                                             view_pose=dict(yaw=0, pitch=2), look=(0.05, -0.05))
_BVIEW = K.view_bounds(AV_FRAME, scale_pt=34.0, center=(-0.04, 1.98), zr=(-1.0, 1.2), margin=1.0)
ASSETS["char_avatarBoss"] = dict(scene=[("av_avatarBoss", dict(yaw=0, pitch=2, center=False))], bounds=_BVIEW, frame=AV_FRAME,
                                 fov=18, light=D.LIGHT_D1_SOFT, no_fit=True, post_fit=_plate(PLATES["amber"]), full_bleed=True)

# the Edit Profile order: the SAME slots as today's AvatarArt.arts (avatarDefault stays the SVG silhouette)
PROFILE_ORDER = ["avatarDefault", "avatarMiner", "avatarMapper", "avatarSleuth", "avatarLunch", "avatarBoss", "avatarConfetti",
                 "avatarStrong", "avatarSleepy"]
REPLACES = {"avatarWalkie": "avatarMiner", "avatarCapGlasses": "avatarMapper", "avatarDetective": "avatarSleuth",
            "avatarBurger": "avatarLunch", "avatarScientist": "avatarBoss", "avatarParty": "avatarConfetti",
            "avatarNotebook": "avatarStrong", "avatarBoxHead": "avatarSleepy"}


# ================================================================== LOOK-2 HOME + EVENTS: the event / avatar Diggers in VINYL
# The owner (09-28 13:56: "not as smooth and good as the original") -> the Loading crew became satin VINYL toys (LOOK-L,
# LOOK-2 v6); the home rigs now wear the same finish (char_crew_d1.HOME_VINYL). The event figures and the avatars take
# it too, so the crew is ONE look on every screen: same ids, frames, cameras (bounds / poses / fov), anchors, poses and
# props as R2's fur figures above -- only the finish (and "grin" -> the muzzle's laugh, "smile" -> the muzzle's smile).
# The fur specs above stay as data (identity checks / rollback).
EV_VINYL = C.HOME_VINYL
_GOG_FIT = dict(gk=1.30, dz=0.040)
LIGHT_EV = dict(D.LIGHT_D1_HK4, rim_dir=D.rim_from(0.0))
LIGHT_AV = dict(D.LIGHT_D1_HK4, rim_dir=D.rim_from(0.3), fill_lux=1450.0, ibl_exp=-0.80)   # portraits: a little more fill


def _ev(spec, **kw):
    """spec -> the vinyl finish (+ overrides); the fur "grin" / "open" become the muzzle's laugh."""
    m = kw.pop("mouth", spec.get("mouth"))
    lg = kw.pop("laugh", 1.05)
    if m in ("grin", "open"):
        m, kw["laugh"] = "laugh", lg
    kw.setdefault("skin_tint", "b2" if spec.get("fur") == "sage" else "a2")
    if spec.get("goggles_down"):
        kw.setdefault("goggles_fit", _GOG_FIT)
    d = dict(EV_VINYL)
    d.update(kw)
    d["mouth"] = m
    return C.spec_with(spec, **d)


CLAW_L_V = _ev(CLAW_L, laugh=1.12)
CLAW_R_V = _ev(CLAW_R, laugh=0.92)
MODELS["dig_clawL"] = lambda: _vdig(CLAW_L_V, dict(yaw=14, pitch=6), key="lk2e_clawL", seed=61)
MODELS["dig_clawR"] = lambda: _vdig(CLAW_R_V, dict(yaw=-16, pitch=6), key="lk2e_clawR", seed=67)
ASSETS["char_digClawPair"] = dict(ASSETS["char_digClawPair"], light=LIGHT_EV)

RACER_V = _ev(RACER, laugh=1.05)
MODELS["dig_racer"] = lambda: _vdig(RACER_V, dict(yaw=44, pitch=14), key="lk2e_racer", seed=71, extra=_racer_extra)
ASSETS["char_digRacers"] = dict(ASSETS["char_digRacers"], light=LIGHT_EV)

BALLOONIST_V = _ev(BALLOONIST, laugh=1.10)
MODELS["dig_balloon"] = lambda: _vdig(BALLOONIST_V, dict(yaw=10, pitch=8), key="lk2e_balloon", seed=73, extra=_balloon_extra)
ASSETS["char_digBalloon"] = dict(ASSETS["char_digBalloon"], light=LIGHT_EV)

AVATARS_V = {}
for _id, (_spec, _pose, _plate_name, _extra) in AVATARS.items():
    AVATARS_V[_id] = _ev(_spec, laugh=1.0)
    MODELS[f"av_{_id}"] = (lambda s=AVATARS_V[_id], p=_pose, e=_extra, i=_id: _vdig(s, p, key=f"lk2e_av_{i}", seed=91, extra=e))
    ASSETS[f"char_{_id}"] = dict(ASSETS[f"char_{_id}"], light=LIGHT_AV)

# the boss portrait: the home boss's LOOK-2 treatment (char_boss style "home5": finer, smoother locks, the soft sclera)
MODELS["av_avatarBoss"] = lambda: CB.boss_v2("portrait_d1", mouth="open", with_station=False, n_strands=24000, arms=_BP_ARMS,
                                             view_pose=dict(yaw=0, pitch=2), look=(0.05, -0.05), style="home5")
ASSETS["char_avatarBoss"] = dict(ASSETS["char_avatarBoss"], post_fit=lambda im: _plate(PLATES["amber"])(CB.plush_pass(im)))


# ================================================================== LOOK-2 FIX ROUND: events + avatars (judged 2026-09-29)
# finish #4  Treasure Climb: the claw's prong tip covered the left Digger's second eye -> the left Digger moved left + down
#            in the pair (the header's claw is where it was)
# copy       "their pair: an excited open-mouthed worker on the left and a glasses worker on the right": the right mole's
#            goggles go UP on his hard hat (no glasses on a face), a calmer closed smile with smiling eyes
# finish #6  Hot Streak: "three identical clones ... the same waving arm, the same laughing face, the same glove on the
#            rim; R2's orange timber carts with a printed grain and grey tubes" -> three different riders (front: looking
#            BACK laughing, eyes shut; middle: cheering with both arms up; back: leaning forward, both paws on the rim)
#            in the Loading's cart finish (umber worn timber, near-black blued iron: mine_cart4's materials)
# copy       avatars: the map reader's goggles-down read as glasses -> goggles up on the hat, a blueprint; the boss
#            portrait takes the home6 face (lidded eyes on the viewer, the lower laugh)
CLAW_R_V2 = _ev(CLAW_R, mouth="smile", eyes="happy", goggles_down=False, brim_goggles_layer=False,
                hat=dict(lamp=False, goggles=True, tilt=-14.0, roll=-8.0))
MODELS["dig_clawR"] = lambda: _vdig(CLAW_R_V2, dict(yaw=-16, pitch=6), key="lk2f_clawR", seed=67)
ASSETS["char_digClawPair"] = dict(ASSETS["char_digClawPair"],
                                  scene=[("dig_clawL", dict(yaw=14, pitch=6, pos=(-1.22, -0.12, 0.0), center=False)),
                                         ("dig_clawR", dict(yaw=-16, pitch=6, pos=(0.95, 0.06, -0.10), center=False))])


def mine_cart_v6(center=(0, 0, 0), s=1.0, tag=""):
    """R2's racer cart geometry (so the riders' paws still land on its rim) in the v6 Loading cart's materials."""
    out = []
    for n, q, m, vx in mine_cart(center, s, tag):
        if n == "cartTub":
            m = Material(f"c_wood6{tag}", "#80624A", roughness=0.72, ior=1.26, texture=FUR.lut_v(CART_WOOD6), texture_size=(128, 64))
            m.__dict__["_vfn"] = _wood6_vfn(q, 7)
        elif n in ("cartBands", "cartWheels"):
            m = K.skin(f"c_iron6{n}{tag}", CART_IRON6, CART_IRONW6, vfn=D.wear_vfn(q, width=0.006, seed=11, gain=0.30),
                       rough=0.42, ior=1.45, clearcoat=0.08, cc_rough=0.24)
        elif n == "cartRivets":
            m = K.skin(f"c_rivet6{tag}", [(0.0, "#8A949E"), (0.35, "#4A5058"), (0.7, "#2A2420"), (1.0, "#4A2A16")], None,
                       rough=0.30, ior=1.5, clearcoat=0.30, cc_rough=0.10)
        out.append((n, q, m, vx))
    return out


def _racer_extra6(ctx):
    cart = [(n, s_.translate(0, -0.10, 0), m, v) for n, s_, m, v in mine_cart_v6(center=(0.0, 0.0, 0.0), s=1.0, tag="r6")]
    rails = union(*[capsule((sx * 0.80, -0.42, -1.1), (sx * 0.80, -0.42, 1.1), 0.035) for sx in (-1, 1)])
    sleepers = union(*[box(1.0, 0.03, 0.07, round=0.015).translate(0, -0.47, zz) for zz in np.linspace(-0.95, 0.95, 6)])
    return cart + [("rails", rails, K.skin("c_rail6", CART_IRON6, None, rough=0.40, ior=1.45), 0.004),
                   ("sleepers", sleepers, K.skin("c_sleeper6", CART_WOOD6[1][1], None, rough=0.72, ior=1.25), 0.006)]


_RIM_L = dict(el=(-0.66, 0.98, 0.38), wr=(-0.56, 0.90, 0.78), d=(0.05, -0.55, 1.0), palm=(0.0, -1.0, 0.2), curl=90.0, spread=14.0,
              claw_bend=60.0, claw_len=0.05)
_UP_L = dict(el=(-0.74, 1.42, 0.14), wr=(-0.80, 1.86, 0.26), d=(-0.12, 1.0, 0.2), palm=(0.2, 0.0, 1.0), curl=14.0, spread=28.0)
_UP_R = dict(el=(0.74, 1.42, 0.14), wr=(0.80, 1.86, 0.26), d=(0.12, 1.0, 0.2), palm=(-0.2, 0.0, 1.0), curl=14.0, spread=28.0)
# front: looking BACK at the others, laughing with his eyes shut, one paw on the rim, the other thrown up behind him
RACER_A = _ev(C.spec_with(RACER, head=dict(yaw=-42.0, roll=8.0, nod=-2.0), look=(0.0, 0.0), eyes="joy",
                          arms=dict(L=_RIM_L, R=dict(el=(0.70, 1.40, -0.02), wr=(0.66, 1.80, -0.20), d=(0.0, 1.0, -0.35),
                                                     palm=(-0.3, 0.0, 1.0), curl=18.0, spread=26.0))), laugh=1.18)
# middle: cheering, both arms up
RACER_B = _ev(C.spec_with(RACER, head=dict(yaw=-6.0, roll=-9.0, nod=-8.0), look=(0.0, 0.30), eyes="happy",
                          arms=dict(L=_UP_L, R=_UP_R)), laugh=1.22)
# back: leaning forward over the front rim, both paws gripping it, a keen grin
_RB = dict(RACER, lean=12.0)
RACER_C = _ev(C.spec_with(RACER, lean=12.0, head=dict(yaw=-4.0, roll=-3.0, nod=6.0), look=(0.25, 0.05),
                          arms=dict(L=_world_arm(_RB, (-0.64, 0.99, 0.46), (-0.48, 0.84, 0.76), (0.05, -0.55, 1.0), (0.0, -1.0, 0.2),
                                                 curl=90.0, spread=14.0, claw_bend=60.0, claw_len=0.05),
                                    R=_world_arm(_RB, (0.64, 0.99, 0.46), (0.48, 0.84, 0.76), (-0.05, -0.55, 1.0), (0.0, -1.0, 0.2),
                                                 curl=90.0, spread=14.0, claw_bend=60.0, claw_len=0.05))), laugh=0.90)
MODELS["dig_racerA"] = lambda: _vdig(RACER_A, dict(yaw=44, pitch=14), key="lk2f_racerA", seed=71, extra=_racer_extra6)
MODELS["dig_racerB"] = lambda: _vdig(RACER_B, dict(yaw=44, pitch=14), key="lk2f_racerB", seed=72, extra=_racer_extra6)
MODELS["dig_racerC"] = lambda: _vdig(RACER_C, dict(yaw=44, pitch=14), key="lk2f_racerC", seed=73, extra=_racer_extra6)
ASSETS["char_digRacers"] = dict(ASSETS["char_digRacers"],
                                scene=[("dig_racerC", dict(yaw=50, pitch=14, pos=(-2.30, 0.30, -2.25), scale=0.66, center=False)),
                                       ("dig_racerB", dict(yaw=46, pitch=14, pos=(-0.70, 0.12, -0.80), scale=0.82, center=False)),
                                       ("dig_racerA", dict(yaw=42, pitch=14, pos=(1.20, -0.10, 0.80), scale=1.0, center=False))])

AVATARS_V["avatarMapper"] = C.spec_with(AVATARS_V["avatarMapper"], goggles_down=False,
                                        hat=dict(lamp=False, goggles=True, tilt=-14.0, roll=-5.0), iris_k=1.15)
MODELS["av_avatarMapper"] = lambda: _vdig(AVATARS_V["avatarMapper"], AVATARS["avatarMapper"][1], key="lk2f_av_mapper", seed=91,
                                          extra=lambda ctx: C.tunnel_map(C._MAP_C + np.array([0.0, 0.1, 0.0]), C._MAP_UP, C._MAP_FACE,
                                                                         style="blueprint"))
MODELS["av_avatarBoss"] = lambda: CB.boss_v2("portrait_d1", mouth="open", with_station=False, n_strands=24000, arms=_BP_ARMS,
                                             view_pose=dict(yaw=0, pitch=2), look=(0.05, -0.05), style="home6")
