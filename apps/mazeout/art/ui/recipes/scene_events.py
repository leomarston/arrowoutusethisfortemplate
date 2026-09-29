"""Event scenes (scene lane): Sky Jump (skyJumpBackdrop, skyJumpPad, skyJumpIsland, skyJumpIslandFar,
skyJumpPopupScene), Claw Challenge header (clawHeaderArt), Weekly Contest podium (leaderboardPodium), Rocket Race
backdrop (rocketRaceBackdrop). Rendered by scene_make.py.

References (LOOKED AT only; measured in pt on gridded crops): research/shots/069-skyjump-screen.png (islands, pads,
sky), 065-join-event.png (popup art), 023-claw-challenge-c.png (claw header), meta-013-leaderboard-weekly.png (podium),
167-rocket-race-screen.png (rocket race; the phone has it, so the web frame in the manifest is superseded). Every
object is modelled here (SDF / analytic meshes, one light rig) and rendered by mfrender; skies and clouds are painted
in code. Live text (PRIZE amount, pad numbers, names, scores) is never baked: the plates are blank and their text
anchors are listed in art/lanes/scene.md.

Units: 1 world unit = 10 pt at the object's own scale; objects are fitted into measured screen boxes.
"""
from __future__ import annotations

import math
import sys

import numpy as np
from PIL import Image

from scene_kit import (Canvas, M4, Part, aa, box, capsule, capped_cone, cloud_layer, cylinder, extrude, fit_box, gloss, grade,
                       instanced_part, lathe_part, mat, noise2, polygon2, rbox, rect2, rgb, rig, rot_x, rot_y, rot_z,
                       rounded_polygon2, satin, shadow_of, smooth, sphere, stops_interp, torus, union, circle2,
                       fillet_points, SDF2, F, blur, d_ellipse, revolve, spline_profile)

_M = sys.modules[__name__]

GOLD = "#F9A20C"       # director r2: #FFAC1A read pale beige under the sky rig (grader B); 065/069's coins are orange-gold
GOLD_RIM = "#E88A08"


# ====================================================================== coins
def coin_sdf():
    """A chunky gold coin (r 1, 0.34 thick) with a raised rim and a five-lobed flower-star emboss (the reference coins
    carry a star/flower mark) on both faces. Axis = Y (lying flat)."""
    body = cylinder(1.0, 0.2, round=0.1)
    inner = cylinder(0.78, 0.3, center=(0, 0, 0))
    body = body.subtract(cylinder(0.8, 0.05, center=(0, 0.19, 0)), k=0.03).subtract(cylinder(0.8, 0.05, center=(0, -0.19, 0)), k=0.03)
    star = rounded_polygon2([(0.52 * math.cos(math.radians(90 + 72 * i + (36 if j else 0))) * (1 if not j else 0.52),
                              0.52 * math.sin(math.radians(90 + 72 * i + (36 if j else 0))) * (1 if not j else 0.52))
                             for i in range(5) for j in (0, 1)], 0.09, n_arc=4)
    em = extrude(star, 0.05, round=0.04).rotate_x(90)
    body = body.union(em.translate(0, 0.15, 0), em.translate(0, -0.15, 0))
    return body


def coin_mat():
    return gloss("coin_gold", GOLD, rough=0.26, ior=1.5)


def coin_stack_mats(rng, cx, cz, base_y, n, s=1.0, jitter=0.06):
    out = []
    for k in range(n):
        R = rot_y(rng.uniform(0, 360)) @ rot_x(rng.uniform(-3, 3))
        out.append(M4(R, (cx + rng.uniform(-jitter, jitter) * s, base_y + (0.17 + k * 0.33) * s, cz + rng.uniform(-jitter, jitter) * s), s))
    return out


def coin_scatter(seed, region, n_stacks, n_loose, base_y_fn, s=1.0, max_stack=5, tilt_loose=35):
    """Coin placement over region = (x0, x1, z0, z1): stacks of 1..max_stack and loose tilted coins."""
    rng = np.random.default_rng(seed)
    x0, x1, z0, z1 = region
    mats = []
    for _ in range(n_stacks):
        x, z = rng.uniform(x0, x1), rng.uniform(z0, z1)
        mats += coin_stack_mats(rng, x, z, base_y_fn(x, z), int(rng.integers(1, max_stack + 1)), s)
    for _ in range(n_loose):
        x, z = rng.uniform(x0, x1), rng.uniform(z0, z1)
        R = rot_y(rng.uniform(0, 360)) @ rot_x(rng.uniform(-tilt_loose, tilt_loose)) @ rot_z(rng.uniform(-tilt_loose, tilt_loose))
        mats.append(M4(R, (x, base_y_fn(x, z) + 0.25 * s + rng.uniform(0, 0.3) * s, z), s))
    return mats


# ====================================================================== the treasure chest (lavender frame, green quilt)
CHEST = dict(w=5.0, h=2.5, d=3.3, lid_r=1.75, open_deg=52)


def _quilt_tex(base="#1FA85E", dark="#10804A", light="#3CCB7C", n=7):
    def fn(u, v):
        a = (u * n * 1.6 + v * n * 0.9) % 1.0
        b = (u * n * 1.6 - v * n * 0.9) % 1.0
        d = np.minimum(np.minimum(a, 1 - a), np.minimum(b, 1 - b))      # distance to the diamond seams
        seam = np.clip(1 - d / 0.06, 0, 1)
        puff = np.clip(d / 0.25, 0, 1)
        col = rgb(dark)[None, None] * seam[..., None] + (rgb(base)[None, None] * (1 - puff[..., None] * 0.4)
                                                          + rgb(light)[None, None] * puff[..., None] * 0.4) * (1 - seam[..., None])
        return col
    return fn


def chest(panel="#1FA85E", quilt=("#1FA85E", "#10804A", "#3CCB7C"), frame="#C9C6F3", with_coins=True, seed=3, open_deg=None,
          straps=False, shield_on=True, shield_on_lid=None):
    from dataclasses import replace
    c = dict(CHEST)
    if open_deg is not None:
        c["open_deg"] = open_deg
    c["shield_on_lid"] = shield_on_lid
    w, h, d, r = c["w"], c["h"], c["d"], c["lid_r"]
    lav = gloss("chest_frame", frame, rough=0.24, ior=1.42)
    parts = []
    body = rbox(w, h, d, 0.32, center=(0, h / 2, 0))
    body = body.subtract(rbox(w - 0.7, h, d - 0.7, 0.15, center=(0, h / 2 + 0.45, 0)))           # open top
    for zf in (d / 2, -d / 2):
        body = body.subtract(rbox(w - 1.3, h - 1.0, 0.5, 0.18, center=(0, h / 2 - 0.05, zf)), k=0.06)
    for xf in (w / 2, -w / 2):
        body = body.subtract(rbox(0.5, h - 1.0, d - 1.3, 0.18, center=(xf, h / 2 - 0.05, 0)), k=0.06)
    parts.append(Part("chestBody", body, lav, voxel=0.03))
    pan = union(rbox(w - 1.25, h - 0.95, 0.12, 0.12, center=(0, h / 2 - 0.05, d / 2 - 0.16)),
                rbox(0.12, h - 0.95, d - 1.25, 0.12, center=(w / 2 - 0.16, h / 2 - 0.05, 0)),
                rbox(0.12, h - 0.95, d - 1.25, 0.12, center=(-w / 2 + 0.16, h / 2 - 0.05, 0)))
    parts.append(Part("chestPanels", pan, satin("chest_panel", panel, rough=0.4), voxel=0.03))
    # lid: a half cylinder along x, hinged at the back top edge, opened backward
    shell = cylinder(r, w / 2 - 0.05).rotate_z(90).intersect(box(w, r + 0.1, r + 0.1, center=(0, r / 2, 0)))
    shell = shell.subtract(cylinder(r - 0.28, w / 2 - 0.35).rotate_z(90))
    ends = union(*[cylinder(r + 0.08, 0.22, round=0.12).rotate_z(90).translate(sx, 0, 0) for sx in (w / 2 - 0.2, -w / 2 + 0.2)])
    ends = ends.intersect(box(w, r + 0.2, r + 0.2, center=(0, r / 2, 0)))
    band = box(w / 2 - 0.1, 0.18, 0.2, round=0.1, center=(0, 0.12, r - 0.1))
    # the lid's outer barrel is the green quilt between lavender end arches (065/069: opened ~50 deg, seen from the
    # front-top, the quilt faces the viewer and the shield latch hangs from the raised front edge)
    q_outer = cylinder(r + 0.03, w / 2 - 0.42).rotate_z(90).intersect(box(w, r + 0.1, r + 0.1, center=(0, r / 2, 0)))
    q_outer = q_outer.subtract(cylinder(r - 0.1, w / 2).rotate_z(90))
    lining = cylinder(r - 0.27, w / 2 - 0.36).rotate_z(90).intersect(box(w, r + 0.1, r + 0.1, center=(0, r / 2 - 0.05, 0)))
    lining = lining.subtract(cylinder(r - 0.36, w / 2).rotate_z(90))
    # shield on the lid's front edge
    sh2 = rounded_polygon2([(-0.75, 0.55), (0.75, 0.55), (0.72, -0.25), (0.0, -0.85), (-0.72, -0.25)], 0.14, n_arc=5)
    shield = extrude(sh2, 0.14, round=0.1)
    shield_in = extrude(sh2.offset(-0.2), 0.08, round=0.05).translate(0, 0, 0.1)
    hinge = (0, h, -d / 2 + 0.05)
    ang = c["open_deg"]

    def lid_xf(s):
        # lid built with its hinge line at (y 0, z -r): move the hinge to the origin, rotate, move to the chest hinge
        return s.translate(0, 0, r).rotate_x(-ang).translate(*hinge)
    parts.append(Part("lidFrame", lid_xf(shell.union(ends).union(band)), lav, voxel=0.03))
    m_q = replace(satin("chest_quilt", quilt[0], rough=0.45), texture=_quilt_tex(*quilt), texture_size=512)
    axis_o = (0.0, h + r * math.sin(math.radians(ang)), -d / 2 + 0.05 + r * math.cos(math.radians(ang)))
    parts.append(Part("lidQuilt", lid_xf(q_outer), m_q, uv=("cyl", axis_o, (1, 0, 0), 1.0 / w), voxel=0.03))
    parts.append(Part("lidLining", lid_xf(lining), satin("chest_panel", panel, rough=0.4), voxel=0.03))
    # the shield hangs from the lid's front edge (which now points up/back): place it on the band
    sh_pos = lid_xf(sphere(0.01, center=(0, 0.3, r + 0.05)))
    shc = (sh_pos.lo + sh_pos.hi) / 2
    # the latch shield hangs from the raised front edge, facing the viewer
    if shield_on and c.get("shield_on_lid"):
        # director r2 (069): the green shield sits ON the quilted barrel's front, facing the viewer; built in lid space
        # on the barrel surface at theta (from the front edge toward the top) and rotated with the lid
        th = math.radians(c["shield_on_lid"])
        ss = 0.95
        sh_l = shield.scale(ss).rotate_x(-math.degrees(th)).translate(0, (r + 0.08) * math.sin(th), (r + 0.08) * math.cos(th))
        si_l = shield_in.scale(ss).rotate_x(-math.degrees(th)).translate(0, (r + 0.08) * math.sin(th), (r + 0.08) * math.cos(th))
        parts.append(Part("shield", lid_xf(sh_l), lav, voxel=0.02))
        parts.append(Part("shieldIn", lid_xf(si_l), satin("chest_shield", quilt[0], rough=0.4), voxel=0.02))
    elif shield_on:
        parts.append(Part("shield", shield.rotate_x(-10).translate(*shc).translate(0, -0.55, 0.3), lav, voxel=0.02))
        parts.append(Part("shieldIn", shield_in.rotate_x(-10).translate(*shc).translate(0, -0.55, 0.3),
                      satin("chest_panel", panel, rough=0.4), voxel=0.02))
    if straps:
        # three gold straps over the barrel lid and down the front, a big diamond clasp (167)
        for sx in (-w / 2 + 0.55, 0.0, w / 2 - 0.55):
            st = torus(r + 0.02, 0.2).rotate_z(90).intersect(box(1, r + 0.4, r + 0.4, center=(0, r / 2, 0)))
            parts.append(Part(f"strap{sx:.1f}", lid_xf(st.translate(sx, 0, 0)), lav, voxel=0.025))
            parts.append(Part(f"strapF{sx:.1f}", box(0.2, h / 2 - 0.1, 0.12, round=0.08, center=(sx, h / 2, d / 2 + 0.05)), lav, voxel=0.025))
        dia = rounded_polygon2([(0, 0.95), (0.8, 0.0), (0, -0.95), (-0.8, 0.0)], 0.18, n_arc=4)
        parts.append(Part("clasp", extrude(dia, 0.22, round=0.16).rotate_z(12).translate(0, h + 0.1, d / 2 + 0.3), lav, voxel=0.02))
    if with_coins:
        rng = np.random.default_rng(seed)
        mats = []
        for _ in range(26):
            x = rng.uniform(-w / 2 + 0.9, w / 2 - 0.9)
            z = rng.uniform(-d / 2 + 0.9, d / 2 - 0.8)
            top = h + 0.25 + 0.55 * (1 - (x / (w / 2)) ** 2) * (1 - (z / (d / 2)) ** 2)
            R = rot_y(rng.uniform(0, 360)) @ rot_x(rng.uniform(-28, 28))
            mats.append(M4(R, (x, top + rng.uniform(-0.15, 0.15), z), 0.7))
        parts.append(instanced_part("chestCoins", coin_mat(), coin_sdf(), 0.03, mats))
    return parts, 0.03


# ====================================================================== the PRIZE sign (blank board: live text)
def sign_board():
    """Green arrow board in a gold frame on a green post (069/065); the words and the amount are live text."""
    pts = [(-3.6, 1.0), (1.0, 1.0), (1.0, 2.1), (3.6, 0.0), (1.0, -2.1), (1.0, -1.0), (-3.6, -1.0)]
    outline = polygon2(fillet_points(pts, [0.35, 0.18, 0.25, 0.35, 0.25, 0.18, 0.35], n_arc=6))
    frame = extrude(outline, 0.26, round=0.2)
    face = extrude(outline.offset(-0.32), 0.1, round=0.06).translate(0, 0, 0.2)
    coin = cylinder(0.62, 0.09, round=0.06).rotate_x(90).translate(-2.55, 0.0, 0.33)
    coin_in = cylinder(0.44, 0.05, round=0.03).rotate_x(90).translate(-2.55, 0.0, 0.42)
    parts = [Part("signFrame", frame, gloss("sign_gold", "#FDBC1E", rough=0.26, ior=1.45), voxel=0.025),
             Part("signFace", face, satin("sign_green", "#1E9A5E", rough=0.4), voxel=0.025),
             Part("signCoin", coin.union(coin_in), gloss("coin_gold", GOLD, rough=0.26, ior=1.5), voxel=0.015)]
    post = capsule((-1.4, -1.0, -0.35), (-0.2, -6.2, -0.35), 0.28)
    parts.append(Part("signPost", post, satin("sign_post", "#1C7A55", rough=0.4), voxel=0.025))
    return parts, 0.025


# ====================================================================== islands and pads
def clover2(R=10.0, lobe=5.0, dist=5.2, core=7.4):
    """Top outline of an island: a rounded 4-lobed (clover) shape."""
    s = circle2(core)
    for a in (0, 90, 180, 270):
        s = s.union(circle2(lobe).translate(dist * math.cos(math.radians(a)), dist * math.sin(math.radians(a))))
    return s


def _slab(s2, y0, y1, round_):
    """A horizontal slab from y0 to y1 with the 2D outline s2 in the XZ plane (s2 x -> x, s2 y -> -z)."""
    return extrude(s2, (y1 - y0) / 2, round=round_).rotate_x(-90).translate(0, (y0 + y1) / 2, 0)


def island(felt="#1E9E5A", felt_light="#2CB86C", chest_colors=None, scale=1.0, coins=60, seed=5, pad=True,
           chest_pos=(0.6, -2.4), gold="#FFB224", dense=False):
    from dataclasses import replace
    parts = []
    top2 = clover2(lobe=5.4, dist=4.9, core=8.2)      # r2: 069's outline is a rounder square with softer lobes
    cream = gloss("isl_cream", "#FBEFEA", rough=0.3, ior=1.38)
    # r2: 069's cream band and gold band are thick (a tall layered body): -2.6 / -4.9 (round 1: -1.7 / -3.5)
    parts.append(Part("islTop", _slab(top2, -2.6, 0.0, 0.8), cream, voxel=0.05))
    parts.append(Part("islGold", _slab(top2.offset(-0.05), -4.9, -2.4, 0.7), gloss("isl_gold", gold, rough=0.28, ior=1.42), voxel=0.05))
    base2 = top2.offset(-0.5)
    parts.append(Part("islBase", _slab(base2, -8.0, -4.7, 1.0), satin("isl_purple", "#9A6BE0", rough=0.45), voxel=0.06))
    # felt inset (back/centre), recessed slightly
    felt2 = clover2(core=5.8, lobe=3.9, dist=4.6).translate(0, 1.4)
    m_f = satin("isl_felt", felt, rough=0.6, ior=1.2)
    parts.append(Part("islFelt", _slab(felt2, -0.3, 0.06, 0.12), m_f, voxel=0.04))
    if pad:
        cushion = revolve(rounded_polygon2([(0.0, -0.1), (3.3, -0.1), (3.35, 0.25), (2.9, 0.62), (0.0, 0.75)], 0.12, n_arc=6))
        parts.append(Part("islPad", cushion.translate(0, 0.0, 5.6), gloss("pad_pink", "#EC3F7C", rough=0.3, ior=1.4), voxel=0.03))
        ring = revolve(rounded_polygon2([(3.2, -0.2), (3.7, -0.2), (3.7, 0.3), (3.2, 0.3)], 0.2, n_arc=5))
        parts.append(Part("islPadRing", ring.translate(0, 0.0, 5.6), satin("isl_ring", "#F3DDE3", rough=0.35), voxel=0.03))
    if coins:
        if dense:
            # r2 (069): TALL coin stacks (3-6) crowd the felt in front of and beside the chest, a few loose coins
            mats = coin_scatter(seed, (-5.8, 6.4, -3.8, 2.0), coins // 5, coins // 6, lambda x, z: 0.06, s=1.05, max_stack=6)
        else:
            mats = coin_scatter(seed, (-5.5, 6.0, -4.5, 1.5), coins // 4, coins - coins // 4 * 3,
                                lambda x, z: 0.06, s=0.9, max_stack=4)
        parts.append(instanced_part("islCoins", coin_mat(), coin_sdf(), 0.03, mats))
    return parts, 0.05


def pad_drum():
    """Sky Jump jump pad (069): pink domed cushion, thick cream ring, gold belt, thin cream ring, tapered purple base,
    a blank pink number plate in a gold frame on the belt (the digit is live text)."""
    from scene_kit import lathe_part
    parts = []
    parts.append(lathe_part("padBase", satin("pad_purple", "#5E34B8", rough=0.4),
                            [(0.0, -4.7), (3.5, -4.7), (4.15, -4.35), (4.55, -3.4), (4.7, -2.2), (0.0, -2.2)], n_seg=180, samples=90))
    parts.append(lathe_part("padCreamLo", gloss("pad_cream", "#F6E6E2", rough=0.3, ior=1.4),
                            [(0.0, -2.3), (4.7, -2.3), (5.05, -2.0), (5.12, -1.4), (0.0, -1.4)], n_seg=180, samples=90))
    parts.append(lathe_part("padGold", gloss("pad_gold", "#FFB21F", rough=0.26, ior=1.45),
                            [(0.0, -1.45), (5.1, -1.45), (5.25, -1.2), (5.27, -0.35), (5.15, -0.1), (0.0, -0.1)], n_seg=180, samples=90))
    parts.append(lathe_part("padCream", gloss("pad_cream", "#F6E6E2", rough=0.3, ior=1.4),
                            [(0.0, -0.15), (5.1, -0.15), (5.45, 0.3), (5.55, 0.85), (5.3, 1.4), (4.7, 1.65), (0.0, 1.65)],
                            n_seg=180, samples=90))
    parts.append(lathe_part("padTop", gloss("pad_pink", "#EC3F7C", rough=0.28, ior=1.42),
                            [(0.0, 1.5), (4.6, 1.5), (4.72, 1.8), (4.25, 2.3), (2.6, 2.6), (0.0, 2.65)], n_seg=180, samples=90))
    plate = rbox(3.5, 3.5, 0.6, 0.62, center=(0, -0.8, 5.35))
    parts.append(Part("plateFrame", plate, gloss("plate_gold", "#FFB61E", rough=0.26, ior=1.45), voxel=0.02))
    parts.append(Part("plateFace", rbox(2.7, 2.7, 0.2, 0.42, center=(0, -0.8, 5.58)),
                      gloss("plate_pink", "#D9346F", rough=0.3, ior=1.4), voxel=0.02))
    return parts, 0.03


MODELS = {"chest_green": lambda: chest(panel="#9C88EA", frame="#BCAFF5", open_deg=36, shield_on_lid=12),
          "sign": sign_board, "island_main": lambda: island(coins=150, seed=5, dense=True),
          "pad": pad_drum}


# ====================================================================== Sky Jump builds
SKY_LIGHT = dict(key_dir=(0.35, -0.75, -0.55), key_lux=2400.0, fill_lux=800.0, fill_color=(1.0, 0.9, 0.95),
                 rim_lux=900.0, rim_color=(1.0, 0.92, 0.98), ibl_exp=-0.75)


def _sky_rig(**kw):
    from scene_kit import scene_env
    env = scene_env("sky", sky=(0.80, 0.90, 1.0), hor=(0.98, 0.84, 0.92), gnd=(0.95, 0.80, 0.90))
    return rig(env=env, **dict(SKY_LIGHT, **kw))


def build_pad(ctx):
    F = (51, 503, 163, 607)
    ims = ctx.render({"pad": dict(scene=[(_M, "pad", dict(pitch=22))], fov=14, px=1200, light=_sky_rig())})
    cv = Canvas(F[2] - F[0], F[3] - F[1])
    # cyan hover glow under the drum
    X, Y = cv.X + F[0], cv.Y + F[1]
    g = np.exp(-(((X - 107.5) / 30) ** 2 + ((Y - 592) / 6.0) ** 2) * 1.3)
    cv.fill(np.clip(g, 0, 1), "#7FF0FF", 0.9)
    spr, (x, y) = fit_box(ims["pad"], (58 - F[0], 506 - F[1], 157 - F[0], 591 - F[1]), mode="contain", align=(0.5, 1.0))
    cv.over(spr, x=x, y=y)
    return cv.image()


BUILDS = {"skyJumpPad": build_pad}


# ---------------------------------------------------------------------- islands (main + far), composed as one render
def _sign_pose(base, s=1.15, roll=14):
    """Place the sign so its post foot lands on `base` (island local)."""
    R = rot_z(roll)
    foot = np.array([-0.2, -6.2, -0.35]) * s
    return dict(center=False, R=R.tolist(), scale=s, pos=tuple(np.asarray(base) - R @ foot))


def _chest_pose(pos, s=1.66, yaw=-24):
    return dict(center=False, R=rot_y(yaw).tolist(), scale=s, pos=pos)


def island_scene(kind):
    if kind == "main":
        return [(_M, "island_main", dict(center=False)),
                (_M, "chest_green", _chest_pose((1.6, 0.05, -2.9))),
                (_M, "sign", _sign_pose((-3.6, 0.05, -2.8), s=1.3, roll=15))]
    if kind == "farL":
        return [(_M, "island_farL", dict(center=False)), (_M, "chest_blue", _chest_pose((0.4, 0.05, -2.6), s=1.5))]
    return [(_M, "island_farR", dict(center=False)), (_M, "chest_purple", _chest_pose((0.4, 0.05, -2.6), s=1.5))]


MODELS.update({
    "island_farL": lambda: island(felt="#4A63DA", coins=150, seed=8, dense=True),
    "island_farR": lambda: island(felt="#8C63DC", coins=150, seed=9, gold="#F7D46A", dense=True),
    "chest_blue": lambda: chest(panel="#9C88EA", quilt=("#4A6CE0", "#2D48B8", "#7D9BF2"), frame="#BCAFF5", seed=4,
                                open_deg=36, shield_on_lid=12),
    "chest_purple": lambda: chest(panel="#8B5FDA", quilt=("#9A6DE6", "#6E44C0", "#C4A3F6"), frame="#D4CEF6", seed=6,
                                  open_deg=36, shield_on_lid=12),
})


def _fade_base(im, y_from, y_to):
    """Fade the island's purple base into the clouds (alpha ramps to 0 between the two image rows)."""
    a = np.asarray(im.convert("RGBA")).astype(np.float64)
    h = a.shape[0]
    t = np.clip((np.arange(h) - y_from) / max(1, y_to - y_from), 0, 1)
    a[..., 3] *= (1 - t * t * (3 - 2 * t))[:, None]
    return Image.fromarray(a.clip(0, 255).astype(np.uint8), "RGBA")


def _island_build(kind, frame, body_box, pitch=24):
    def fn(ctx):
        ims = ctx.render({f"isl_{kind}": dict(scene=island_scene(kind), view=(0, pitch), fov=16, px=1700,
                                               light=_sky_rig())})
        im = ims[f"isl_{kind}"]
        from scene_kit import alpha_bbox
        bb = alpha_bbox(im)
        im = _fade_base(im.crop(bb), (bb[3] - bb[1]) * 0.80, (bb[3] - bb[1]) * 1.0)
        cv = Canvas(frame[2] - frame[0], frame[3] - frame[1])
        X, Y = cv.X + frame[0], cv.Y + frame[1]
        # a soft violet haze under the island (it hangs over the cloud sea)
        bx0, by0, bx1, by1 = body_box
        cxh, cyh = (bx0 + bx1) / 2, by1 - (by1 - by0) * 0.12
        g = np.exp(-(((X - cxh) / ((bx1 - bx0) * 0.42)) ** 2 + ((Y - cyh) / ((by1 - by0) * 0.22)) ** 2) * 1.5)
        # director r2 (grader B): the haze reached the frame edge (alpha up to 83/255 on 39 % of the border), which drew a
        # visible rectangle on the backdrop -- fade it to 0 over the outer 14 % of the frame
        fw, fh = frame[2] - frame[0], frame[3] - frame[1]
        ex = np.clip(np.minimum(cv.X, fw - cv.X) / (0.14 * fw), 0, 1)
        ey = np.clip(np.minimum(cv.Y, fh - cv.Y) / (0.14 * fh), 0, 1)
        cv.fill(np.clip(g, 0, 1) * ex * ey, "#B48BEA", 0.55)
        # r2: fitted by the island's WIDTH (069: the main island spans ~220 pt, round 1 ~172 as the sign + chest made a
        # height-limited "contain" fit); bottom-aligned
        spr, (x, y) = fit_box(im, (bx0 - frame[0], by0 - frame[1], bx1 - frame[0], by1 - frame[1]), mode="width",
                              align=(0.5, 1.0), crop=False)
        cv.over(spr, x=x, y=y)
        edge = np.clip(np.minimum(np.minimum(cv.X - 0.5, fw - 0.5 - cv.X), np.minimum(cv.Y - 0.5, fh - 0.5 - cv.Y)) / 2.0, 0, 1)
        cv.a[..., 3] *= edge
        return cv.image()
    return fn


# r2 frames grown for the bigger islands (069: main x ~89..309, far-left x ~20..157 pt)
BUILDS["skyJumpIsland"] = _island_build("main", (66, 306, 326, 562), (88, 312, 310, 556), pitch=13)
BUILDS["skyJumpIslandFar"] = _island_build("farL", (6, 222, 172, 380), (19, 226, 158, 376), pitch=15)


# ---------------------------------------------------------------------- popup scene: coin hill, overflowing chest, sign
def coin_hill():
    """065: a green felt hill heaped with hundreds of coins (stacks + loose), wider than the popup."""
    parts = []
    hill = sphere(1.0).scale_xyz(19.0, 2.4, 8.0).translate(0, -1.2, 0)
    hill = hill.intersect(box(20, 5, 10, center=(0, 3.6, 0)))
    parts.append(Part("hill", hill, satin("hill_felt", "#1E9A5A", rough=0.6, ior=1.2), voxel=0.08))

    def top(x, z):
        v = 1 - (x / 19.0) ** 2 - (z / 8.0) ** 2
        return -1.2 + 2.4 * math.sqrt(max(v, 0.0))
    mats = coin_scatter(21, (-17.5, 17.5, -6.5, 6.5), 170, 230, top, s=0.95, max_stack=6, tilt_loose=40)
    # a denser heap in front of the chest
    mats += coin_scatter(22, (-4.0, 8.0, -1.5, 5.0), 60, 50, lambda x, z: top(x, z) + 0.4, s=0.95, max_stack=7)
    parts.append(instanced_part("hillCoins", coin_mat(), coin_sdf(), 0.03, mats))
    return parts, 0.06


MODELS.update({"coin_hill": coin_hill,
               "chest_green_full": lambda: chest(seed=12, panel="#9C88EA", frame="#BCAFF5", open_deg=36, shield_on_lid=12)})


def build_popup(ctx):
    F = (30, 270, 360, 460)
    scene = [(_M, "coin_hill", dict(center=False)),
             (_M, "chest_green_full", _chest_pose((3.4, 1.0, -1.8), s=2.3, yaw=-20)),
             (_M, "sign", _sign_pose((-6.6, 0.9, -1.2), s=1.75, roll=14))]
    ims = ctx.render({"sjPopup": dict(scene=scene, view=(0, 22), fov=16, px=1800, light=_sky_rig())})
    im = ims["sjPopup"]
    cv = Canvas(F[2] - F[0], F[3] - F[1])
    # soft pink cloud banks behind the hill at both sides (065)
    cloud_layer(cv, [(8, 95, 26), (30, 104, 22), (-2, 118, 24)], top="#FFFFFF", mid="#FBE3EE", bottom="#E9C7E4", soft=2.0)
    cloud_layer(cv, [(322, 92, 24), (300, 104, 20), (334, 116, 24)], top="#FFFFFF", mid="#FBE3EE", bottom="#E9C7E4", soft=2.0)
    # r2 (065): a warm golden glow behind the heap
    Xg, Yg = cv.X, cv.Y
    glow = np.exp(-(((Xg - 175) / 150.0) ** 2 + ((Yg - 150) / 60.0) ** 2) * 1.2)
    cv.fill(np.clip(glow, 0, 1), "#FFD66A", 0.45)
    spr, (x, y) = fit_box(im, (-80, 5, 410, 196), mode="height", align=(0.5, 1.0))
    # the hill is wider than the popup (like the reference); the panel clips it -- fade the last 5 pt so no pixel
    # touches the frame edge
    cv.over(spr, x=x, y=y)
    edge = np.clip(np.minimum(cv.X - 0.5, (F[2] - F[0]) - 0.5 - cv.X) / 5.0, 0, 1)
    edge = np.minimum(edge, np.clip(((F[3] - F[1]) - 0.5 - cv.Y) / 3.0, 0, 1))
    cv.a[..., 3] *= edge
    return cv.image()


BUILDS["skyJumpPopupScene"] = build_popup


# ---------------------------------------------------------------------- the sky backdrop (full screen, painted)
def build_sky(ctx):
    cv = Canvas(393, 852)
    X, Y = cv.X, cv.Y
    sky = stops_interp(Y, [(0, "#2F86F0"), (140, "#4B9DF4"), (300, "#83C1F8"), (420, "#B9D9F6"), (560, "#F4D8E8"),
                           (852, "#F7D6E6")])
    cv.a[..., :3] = sky
    cv.a[..., 3] = 1.0
    rng = np.random.default_rng(5)
    # far bank (bluish-lilac, behind the islands), then pink-white banks rolling toward the viewer
    banks = [
        (250, 330, 16, 24, 40, ("#F4F2FF", "#DCD6F6", "#B9B2E8")),
        (320, 420, 12, 30, 52, ("#FFFFFF", "#F6DDEB", "#D9BEE6")),
        (420, 560, 10, 36, 64, ("#FFFFFF", "#F9D5E5", "#E2B9DE")),
        (540, 700, 8, 44, 78, ("#FFFFFF", "#FAD3E3", "#E8B8DA")),
        (680, 900, 7, 52, 90, ("#FFFFFF", "#FBD8E6", "#EDBFDD")),
    ]
    for y0, y1, n, rmin, rmax, (top, mid, bot) in banks:
        puffs = []
        xs = np.linspace(-40, 433, n) + rng.uniform(-15, 15, n)
        for x in xs:
            r = rng.uniform(rmin, rmax)
            cy = rng.uniform(y0, y1 - r * 0.3)
            puffs.append((float(x), float(cy), float(r)))
            puffs.append((float(x + r * 0.6), float(cy + r * 0.35), float(r * 0.8)))
        cloud_layer(cv, puffs, top=top, mid=mid, bottom=bot, soft=2.5)
    # the thin haze that softens the far banks (aerial perspective)
    haze = np.exp(-((Y - 330) / 90.0) ** 2)
    cv.screen(haze, "#EAF3FF", 0.25)
    return cv.image()


BUILDS["skyJumpBackdrop"] = build_sky


# ====================================================================== Claw Challenge header (023)
# 023 (pt): light bar across the top (x 60..330, y 0..15), the claw hanging from the top centre (hub y 20..60, three
# prongs spanning x 135..250 down to y ~110), glass box edges (thin cyan lines), purple / magenta neon on the back
# walls; a heap of prizes from y ~130 to the bottom: glass bulbs (97, 165) and (300, 160) r ~20, a red heart (153,
# 165) r ~22, an hourglass (233, 160) ~50 tall, rounded cubes (green / yellow / orange / purple / blue, 25-35 pt) and
# chunky arrows. The two workers (characters lane, workerClawPair) stand between the back wall and the prizes.
def rcube(s=1.0, r=0.22):
    return box(s / 2, s / 2, s / 2, round=r * s)


BLOCK_COLORS = {"green": "#39C43A", "yellow": "#FFC21A", "orange": "#FF8A1C", "purple": "#A96BEA", "blue": "#2FA8F4",
                "red": "#F0364A"}


def claw_model():
    metal_ = gloss("claw_metal", "#8FC3F2", rough=0.22, ior=1.45)
    parts = []
    parts.append(Part("clawRod", cylinder(0.32, 2.2, center=(0, 3.4, 0)), metal_, voxel=0.02))
    parts.append(Part("clawCap", cylinder(0.9, 0.25, round=0.15, center=(0, 5.3, 0)), metal_, voxel=0.02))
    hub = cylinder(1.25, 0.7, round=0.3, center=(0, 0.9, 0)).union(cylinder(0.8, 0.5, round=0.2, center=(0, 1.8, 0)))
    parts.append(Part("clawHub", hub, gloss("claw_hub", "#6FAEEA", rough=0.22, ior=1.45), voxel=0.02))
    prongs = []
    for a in (90, 210, 330):
        ca, sa = math.cos(math.radians(a)), math.sin(math.radians(a))
        pts = []
        for t in np.linspace(0, 1, 14):
            r = 1.0 + 2.3 * math.sin(t * math.pi * 0.7)
            y = 0.6 - 3.4 * t
            k = max(0.0, (t - 0.65) / 0.35)
            r -= 1.9 * k * k
            pts.append((r * ca, y, r * sa))
        from scene_kit import path_tube
        prongs.append(path_tube(pts, [0.62 - 0.34 * (i / 13) ** 1.5 for i in range(14)]))
    parts.append(Part("clawProngs", union(*prongs), metal_, voxel=0.02))
    return parts, 0.02


def bulb_model():
    from dataclasses import replace
    parts = []
    parts.append(Part("bulbGlass", sphere(1.55, center=(0, 1.3, 0)).union(capped_cone(0.6, 0.72, 1.1, center=(0, 0.1, 0)), k=0.3),
                      replace(gloss("bulb_glass", "#CBEBFF", rough=0.08, ior=1.5), opacity=0.72), voxel=0.025))
    fil = []
    for i in range(5):
        x = -0.6 + 0.3 * i
        fil.append(capsule((x, 1.1, 0.3), (x * 0.6, 0.3, 0.2), 0.07))
        fil.append(capsule((x, 1.1, 0.3), (x + 0.15, 1.5, 0.3), 0.07))
    parts.append(Part("bulbFil", union(*fil), satin("bulb_fil", "#FFFFFF", rough=0.3), voxel=0.012))
    parts.append(Part("bulbCollar", cylinder(0.8, 0.22, round=0.12, center=(0, -0.55, 0)), gloss("bulb_col", "#FFC21A", rough=0.25), voxel=0.015))
    base = union(*[torus(0.62, 0.16, center=(0, -0.95 - 0.3 * i, 0)) for i in range(4)]).union(cylinder(0.6, 0.6, center=(0, -1.4, 0)))
    parts.append(Part("bulbBase", base, gloss("bulb_base", "#2F7FEA", rough=0.25), voxel=0.015))
    parts.append(Part("bulbTip", sphere(0.3, center=(0, -2.1, 0)), gloss("bulb_tip", "#2F7FEA", rough=0.25), voxel=0.012))
    return parts, 0.02


def hourglass_model():
    from dataclasses import replace
    parts = []
    cap = gloss("hg_cap", "#2F7FEA", rough=0.24)
    parts.append(Part("hgTop", cylinder(1.35, 0.3, round=0.2, center=(0, 2.1, 0)), cap, voxel=0.02))
    parts.append(Part("hgBot", cylinder(1.35, 0.3, round=0.2, center=(0, -2.1, 0)), cap, voxel=0.02))
    glass_ = capped_cone(0.9, 0.2, 0.95, center=(0, 0.9, 0)).union(capped_cone(0.9, 0.95, 0.2, center=(0, -0.9, 0)), k=0.25)
    parts.append(Part("hgGlass", glass_, replace(gloss("hg_glass", "#DDF4FF", rough=0.08, ior=1.5), opacity=0.5), voxel=0.02))
    sand = capped_cone(0.45, 0.8, 0.12, center=(0, -1.3, 0)).union(capsule((0, -0.2, 0), (0, 0.5, 0), 0.08))
    parts.append(Part("hgSand", sand, satin("hg_sand", "#46C6F7", rough=0.4), voxel=0.015))
    return parts, 0.02


def heart_model():
    from uikit import heart2
    s2 = heart2(2.6, 2.4)
    body = extrude(s2, 0.55, round=0.5)
    return [Part("heart", body, gloss("heart_red", "#EE2536", rough=0.2, ior=1.45), voxel=0.02)], 0.02


def block_model(color):
    return [Part("block", rcube(2.2, 0.2), gloss(f"blk_{color}", BLOCK_COLORS[color], rough=0.26, ior=1.42), voxel=0.025)], 0.025


MODELS.update({"claw": claw_model, "bulb": bulb_model, "hourglass": hourglass_model, "heart": heart_model})
for _c in BLOCK_COLORS:
    MODELS[f"block_{_c}"] = (lambda c=_c: block_model(c))


def _prize_heap(seed=31):
    """The prize heap in screen-registered world coords (x = sx/10, y = -sy/10), a few rows in depth."""
    import scene_home as H
    rng = np.random.default_rng(seed)
    items = []
    # hero prizes at measured spots (z forward so they sit in front of the blocks behind them)
    items.append((_M, "bulb", dict(center=False, pos=(9.6, -16.8, 2.6), R=(rot_z(-10)).tolist(), scale=1.5)))
    items.append((_M, "bulb", dict(center=False, pos=(30.2, -16.2, 1.8), R=(rot_z(12)).tolist(), scale=1.5)))
    items.append((_M, "heart", dict(center=False, pos=(15.6, -16.4, 1.6), R=(rot_z(-10) @ rot_y(-15)).tolist(), scale=1.75)))
    items.append((_M, "hourglass", dict(center=False, pos=(23.4, -16.2, 1.2), R=(rot_z(-6) @ rot_x(-10)).tolist(), scale=1.45)))
    items.append((_M, "bulb", dict(center=False, pos=(4.2, -22.2, 4.4), R=(rot_z(58) @ rot_x(20)).tolist(), scale=1.35)))
    items.append((_M, "heart", dict(center=False, pos=(38.0, -21.0, 3.6), R=(rot_z(14)).tolist(), scale=1.3)))
    items.append((_M, "heart", dict(center=False, pos=(26.8, -21.6, 4.6), R=(rot_z(-20) @ rot_x(-30)).tolist(), scale=1.2)))
    cols = list(BLOCK_COLORS)
    # blocks + arrows in three depth rows, the heap rising toward the middle
    for z, y_top, n in ((-0.8, -14.6, 10), (1.2, -17.6, 10), (3.4, -20.8, 9)):
        for i in range(n):
            x = -1.5 + 42.0 * (i + rng.uniform(0.1, 0.9)) / n
            y = y_top - rng.uniform(0, 2.6) - 1.8 * (abs(x - 19.6) / 19.6) ** 2
            R = rot_y(rng.uniform(-35, 35)) @ rot_x(rng.uniform(-30, 30)) @ rot_z(rng.uniform(-30, 30))
            if rng.uniform() < 0.28:
                c = ["orange", "yellow", "sky", "lilac", "green"][int(rng.integers(0, 5))]
                items.append((H, f"pile_arrow_{c}", dict(center=True, pos=(x, y, z), R=(R @ rot_z(rng.uniform(0, 360))).tolist(), scale=1.15)))
            else:
                c = cols[int(rng.integers(0, len(cols)))]
                items.append((_M, f"block_{c}", dict(center=False, pos=(x, y, z), R=R.tolist(), scale=rng.uniform(1.6, 2.0))))
    return items


def _claw_back(cv):
    """Back walls: deep violet with magenta / blue neon washes, the lit ceiling bar, the glass box edges."""
    X, Y = cv.X, cv.Y
    base = stops_interp(X, [(0, "#5B1E8E"), (40, "#7A2AA8"), (80, "#3B2D9E"), (196, "#2A2F9A"), (300, "#3A2AA0"),
                            (350, "#7E27A6"), (393, "#4B1D86")])
    cv.a[..., :3] = base
    cv.a[..., 3] = 1.0
    # neon washes (soft magenta at both sides, cyan-blue glow in the upper middle)
    for cx, cy, rx, ry, col, a in ((20, 120, 50, 110, "#E23BC8", 0.55), (375, 110, 45, 100, "#D536C4", 0.5),
                                   (196, 60, 150, 70, "#3F6BE8", 0.45), (110, 150, 50, 60, "#3B4FD6", 0.35)):
        g = np.exp(-(((X - cx) / rx) ** 2 + ((Y - cy) / ry) ** 2))
        cv.screen(g, col, a)
    # ceiling: a dark frame with a bright strip light
    top = (Y < 20)
    cv.multiply(top.astype(float), "#1C2A7A", 0.6)
    strip = aa(np.abs(Y - 9) - 5.5, 0.8) * aa(np.abs(X - 196) - 125, 2.0)
    cv.fill(strip, "#E9F6FF", 1.0)
    glow = np.exp(-((Y - 8) / 12.0) ** 2) * aa(np.abs(X - 196) - 140, 25.0)
    cv.screen(glow, "#7FD8FF", 0.6)
    # glass box: back vertical edges and the perspective edges to the front corners (thin cyan lines)
    for (x0, y0, x1, y1) in ((64, 40, 64, 150), (329, 40, 329, 150), (64, 40, 0, 12), (329, 40, 393, 12), (64, 40, 329, 40)):
        n = max(1, int(max(abs(x1 - x0), abs(y1 - y0))))
        # distance to a segment
        px, py = X - x0, Y - y0
        dx, dy = x1 - x0, y1 - y0
        L2 = dx * dx + dy * dy
        t = np.clip((px * dx + py * dy) / max(L2, 1e-9), 0, 1)
        d = np.sqrt((px - t * dx) ** 2 + (py - t * dy) ** 2)
        cv.screen(aa(d - 0.6, 0.6), "#8FE6FF", 0.55)
        cv.screen(np.exp(-(d / 3.0) ** 2), "#58B8FF", 0.25)


def build_claw(ctx):
    import os
    import scene_kit as K
    F = (0, 0, 393, 240)
    cv = Canvas(393, 240)
    _claw_back(cv)
    # the workers (characters lane) between the back wall and the prizes, if their render exists
    pair = os.path.join(K.OUT, "char_workerClawPair@3x.png")
    have_pair = os.path.exists(pair)
    if have_pair:
        im = Image.open(pair).convert("RGBA")
        w, h = im.size
        cv.over(im, x=int(200 * 3 - w / 2), y=int(115 * 3 - h / 2))
    specs = {
        "clawPrizes": dict(scene=_prize_heap(), bounds=((0.0, -24.0, -3.0), (39.3, 0.0, 6.0)), aspect=393 / 240,
                           margin=1.0, fov=6.0, px=2000, light=rig(key_lux=2600.0)),
        "clawClaw": dict(scene=[(_M, "claw", dict(center=False, pos=(19.6, -5.8, 0.5), R=rot_y(18).tolist(), scale=1.75))],
                         bounds=((0.0, -24.0, -3.0), (39.3, 0.0, 6.0)), aspect=393 / 240, margin=1.0, fov=6.0, px=2000,
                         light=rig(key_lux=2400.0)),
    }
    ims = ctx.render(specs)
    for k in ("clawClaw", "clawPrizes"):
        im = ims[k].resize((cv.w, cv.h), Image.LANCZOS)
        sh, (ox, oy) = shadow_of(im, 0, 6, 8, 0.35, color="#1A0C4A")
        cv.over(sh, x=ox, y=oy)
        cv.over(im)
    out = cv.image()
    out.info["note"] = "workers composited" if have_pair else "workers missing (char_workerClawPair not rendered yet)"
    return out


BUILDS["clawHeaderArt"] = build_claw


# ====================================================================== Weekly Contest podium (meta-013)
# meta-013 (pt): three blocks standing on the list's top edge (~y 500): 2nd lilac-silver x 5..128 (cap top y 330), 1st
# gold x 125..265 (cap top 300), 3rd orange x 262..390 (cap top 342); each a thick cap slab over a body with a grooved
# front panel and two rivets; a blank hexagon rank badge at the cap / body seam (the digit is live text), avatars
# (UI) sit on the caps, names / coin stacks / score chips (live / other lanes) on the front panels.
PODIUM = {"silver": dict(x=(5, 128), top=330, body="#949CF0", cap="#AEB5F8", groove="#6F76D2", hexc="#B4BCF6",
                         hexrim="#7B83DA"),
          "gold": dict(x=(125, 265), top=300, body="#FFBA22", cap="#FFD045", groove="#E28D0A", hexc="#FFC93E",
                       hexrim="#E88A0C"),
          "bronze": dict(x=(262, 390), top=342, body="#FF801F", cap="#FF9A3E", groove="#D85C0C", hexc="#FF9A45",
                         hexrim="#D9601A")}
PODIUM_BOTTOM = 500.0


def podium_block(kind):
    c = PODIUM[kind]
    x0, x1 = c["x"]
    w = (x1 - x0) / 10.0
    cx = (x0 + x1) / 20.0
    top = -c["top"] / 10.0
    bot = -PODIUM_BOTTOM / 10.0
    d = 6.0
    cap_h = 1.8
    parts = []
    cap = rbox(w, cap_h, d + 0.4, 0.45, center=(cx, top - cap_h / 2, 0))
    parts.append(Part(f"cap_{kind}", cap, gloss(f"pod_cap_{kind}", c["cap"], rough=0.28, ior=1.4), voxel=0.03))
    bw = w - 0.3
    body = rbox(bw, top - cap_h - bot + 0.4, d, 0.35, center=(cx, (top - cap_h + bot) / 2 - 0.2, 0))
    # grooved front panel
    gx0, gx1 = cx - bw / 2 + 0.75, cx + bw / 2 - 0.75
    gy1, gy0 = top - cap_h - 1.2, bot + 0.2
    outer = rbox(gx1 - gx0, gy1 - gy0, 0.6, 0.5, center=((gx0 + gx1) / 2, (gy0 + gy1) / 2, d / 2))
    inner = rbox(gx1 - gx0 - 0.36, gy1 - gy0 - 0.36, 1.0, 0.4, center=((gx0 + gx1) / 2, (gy0 + gy1) / 2, d / 2))
    groove = outer.subtract(inner)
    body = body.subtract(groove, k=0.05)
    parts.append(Part(f"body_{kind}", body, gloss(f"pod_body_{kind}", c["body"], rough=0.3, ior=1.4), voxel=0.03))
    ring2 = rect2((gx1 - gx0) / 2, (gy1 - gy0) / 2, round=0.5).subtract(rect2((gx1 - gx0) / 2 - 0.18, (gy1 - gy0) / 2 - 0.18, round=0.4))
    parts.append(Part(f"groove_{kind}", extrude(ring2, 0.06).translate((gx0 + gx1) / 2, (gy0 + gy1) / 2, d / 2 - 0.22),
                      satin(f"pod_groove_{kind}", c["groove"], rough=0.4), voxel=0.02))
    for rx in (gx0 + 0.75, gx1 - 0.75):
        parts.append(Part(f"rivet_{kind}{int(rx)}", sphere(0.36, center=(rx, gy1 - 0.75, d / 2 - 0.05)),
                          gloss(f"pod_rivet_{kind}", c["groove"], rough=0.25, ior=1.45), voxel=0.012))
    # blank hexagon badge on the seam
    hx = rounded_polygon2([(2.05 * math.cos(math.radians(a)), 1.85 * math.sin(math.radians(a))) for a in range(0, 360, 60)], 0.25, n_arc=4)
    hy = top - cap_h - 0.1
    parts.append(Part(f"hexRim_{kind}", extrude(hx, 0.35, round=0.25).translate(cx, hy, d / 2 + 0.35),
                      gloss(f"pod_hexrim_{kind}", c["hexrim"], rough=0.26, ior=1.42), voxel=0.02))
    parts.append(Part(f"hexFace_{kind}", extrude(hx.offset(-0.3), 0.2, round=0.15).translate(cx, hy, d / 2 + 0.55),
                      gloss(f"pod_hex_{kind}", c["hexc"], rough=0.26, ior=1.42), voxel=0.02))
    return parts, 0.03


for _k in PODIUM:
    MODELS[f"podium_{_k}"] = (lambda k=_k: podium_block(k))


def build_podium(ctx):
    F = (2, 294, 391, 500)
    scene = [(_M, f"podium_{k}", dict(center=False, pos=(0, 0, 0.35 if k == "gold" else 0.0))) for k in ("silver", "gold", "bronze")]
    ims = ctx.render({"podium": dict(scene=scene, view=(0, 7), fov=8, px=1800,
                                     light=rig(key_lux=1750.0, key_dir=(0.3, -0.5, -0.8), fill_lux=700.0))})
    cv = Canvas(F[2] - F[0], F[3] - F[1])
    spr, (x, y) = fit_box(grade(ims["podium"], sat=1.2), (5 - F[0], 298 - F[1], 390 - F[0], 500 - F[1]), mode="width", align=(0.5, 0.0))
    cv.over(spr, x=x, y=y)
    # the blocks stand behind the list: fade the last 4 pt so nothing touches the frame's bottom edge
    cv.a[..., 3] *= np.clip(((F[3] - F[1]) - 0.5 - cv.Y) / 3.5, 0, 1)
    return cv.image()


BUILDS["leaderboardPodium"] = build_podium


# ====================================================================== Rocket Race backdrop (167, on the phone v552)
# 167 (pt): indigo space with sparkling stars, a small ringed planet (210, 18), a big banded planet (295, 50) r ~30,
# a lilac cratered moon surface from the horizon at y ~120 down to ~230, a two-tier purple rock under a closed gold /
# teal treasure chest (x ~135..250, y 62..140) heaped with coins and two red hearts; below the header strip (UI, y
# ~230..330) the race lanes' dark violet gradient with faint stars (lane dividers and rockets are UI).
def rock():
    parts = []
    s1 = rounded_polygon2([(-13.5, -3.2), (12.5, -3.8), (14.2, 1.0), (9.0, 3.6), (-9.5, 3.8), (-14.0, 0.8)], 1.2, n_arc=6)
    s2 = rounded_polygon2([(-9.0, -2.6), (9.5, -2.8), (10.5, 1.0), (6.0, 2.8), (-6.5, 3.0), (-10.0, 0.6)], 1.0, n_arc=6)
    from scene_kit import noise2 as _n
    t1 = extrude(s1, 1.2, round=0.8).rotate_x(-90).translate(0, -1.2, 0)
    t2 = extrude(s2, 1.0, round=0.7).rotate_x(-90).translate(0.6, 1.0, -0.8)
    parts.append(Part("rock", t1.smooth_union(t2, k=0.3), satin("rock", "#5E54B8", rough=0.55, ior=1.25), voxel=0.06))
    return parts, 0.06


def rr_hoard():
    """Coins heaped around the chest on the rock's two tiers."""
    parts = []

    def base(x, z):
        tier = 2.1 if (abs(x - 0.6) < 9.5 and -3.5 < z < 2.2) else 0.1
        mound = 2.2 * max(0.0, 1 - (x / 9.0) ** 2 - ((z - 0.5) / 3.5) ** 2)
        return tier + mound
    mats = coin_scatter(41, (-12.5, 12.5, -2.5, 3.5), 80, 90, base, s=1.1, max_stack=6, tilt_loose=40)
    mats += coin_scatter(42, (-7.0, 8.0, -1.0, 3.0), 30, 40, base, s=1.2, max_stack=4, tilt_loose=35)
    parts.append(instanced_part("rrCoins", coin_mat(), coin_sdf(), 0.03, mats))
    return parts, 0.03


MODELS.update({"rock": rock, "rr_hoard": rr_hoard,
               "chest_gold": lambda: chest(panel="#2AA2C6", quilt=("#2AA7C9", "#2AA7C9", "#34B0D0"), frame="#FFC22A",
                                           with_coins=False, open_deg=0, straps=True, shield_on=False)})


def _stars(cv, n, y0, y1, seed, big=6):
    rng = np.random.default_rng(seed)
    X, Y = cv.X, cv.Y
    for i in range(n):
        x, y = rng.uniform(0, 393), rng.uniform(y0, y1)
        r = rng.uniform(0.5, 1.3)
        a = rng.uniform(0.4, 1.0)
        m = (np.abs(X - x) < 12) & (np.abs(Y - y) < 12)
        if not m.any():
            continue
        d = np.sqrt((X - x) ** 2 + (Y - y) ** 2)
        g = np.exp(-(d / r) ** 2) * a
        if i < big:   # a few sparkles with cross flares
            g = g + (np.exp(-((X - x) / 0.5) ** 2) * np.exp(-np.abs(Y - y) / 5.0) +
                     np.exp(-((Y - y) / 0.5) ** 2) * np.exp(-np.abs(X - x) / 5.0)) * 0.7
        cv.screen(np.clip(g, 0, 1), "#FFFFFF", 1.0)


def build_rocket(ctx):
    cv = Canvas(393, 852)
    X, Y = cv.X, cv.Y
    sky = stops_interp(Y, [(0, "#241B6E"), (60, "#2F2285"), (115, "#5B3BB7"), (130, "#7A56D2"), (330, "#3A1E9C"),
                           (500, "#2A1680"), (852, "#431FB0")])
    cv.a[..., :3] = sky
    cv.a[..., 3] = 1.0
    _stars(cv, 70, 0, 120, 3, big=6)
    # small ringed planet
    d = d_ellipse(X, Y, 210, 18, 11, 11)
    cv.fill(aa(d, 0.5), stops_interp(Y, [(7, "#9DD3F6"), (29, "#3F7BD6")]))
    ring = np.abs(np.sqrt(((X - 210) / 24.0) ** 2 + ((Y - 20) / 5.5) ** 2) - 1) * 5
    cv.fill(aa(ring - 0.9, 0.5) * ((Y > 19) | (np.abs(X - 210) > 11)), "#4C8CE8", 0.95)
    # the banded planet
    d = d_ellipse(X, Y, 296, 50, 30, 30)
    band = 0.5 + 0.5 * np.sin((Y - 50) / 30 * 7.5 + np.sin((X - 296) / 9) * 0.6)
    pc = stops_interp(band, [(0, "#B88196"), (0.5, "#D9927E"), (1, "#E7B7B0")])
    shade = np.clip(((X - 280) ** 2 + (Y - 35) ** 2) ** 0.5 / 42, 0, 1)
    pc = pc * (1 - 0.45 * shade[..., None]) + rgb("#5A4AA8") * 0.45 * shade[..., None]
    cv.fill(aa(d, 0.5), pc)
    # the moon surface: horizon ~y 120 (slightly curved), lilac ground with craters, darker toward the viewer
    hz = 118 + 6 * ((X - 196) / 196) ** 2
    # director r2 (grader B): the moon ground ran down the whole screen, so the race lanes sat on flat lavender #6A48BA;
    # on 167 the ground ends under the header (the banner covers y ~235-370) and the lane area is DEEP INDIGO
    # (#16105C at the top of the lanes -> #420FAC at the bottom) with faint stars
    ground = (Y > hz) & (Y < 300)
    gcol = stops_interp(Y, [(118, "#C6AEF0"), (140, "#A28AE0"), (200, "#8466CE"), (260, "#6A48BA"), (300, "#4A30A0")])
    cv.a[..., :3] = np.where(ground[..., None], gcol, cv.a[..., :3])
    lanes = stops_interp(Y, [(300, "#1C1464"), (370, "#16105C"), (520, "#24128A"), (700, "#3410A0"), (852, "#420FAC")])
    cv.a[..., :3] = np.where((Y >= 300)[..., None], lanes, cv.a[..., :3])
    # a soft violet glow band down the middle of the lane area (167: the lanes are lighter in their middle third)
    cv.screen(np.exp(-(((Y - 560) / 170.0) ** 2)) * (Y > 300), "#5A2FD0", 0.35)
    cv.screen(np.exp(-((Y - hz) / 4.0) ** 2), "#D8C8FF", 0.6)
    rng = np.random.default_rng(9)
    for i in range(14):
        cx, cy = rng.uniform(0, 393), rng.uniform(125, 225)
        rx = rng.uniform(8, 26) * (0.6 + (cy - 120) / 140)
        ry = rx * (0.22 + (cy - 120) / 400)
        dd = d_ellipse(X, Y, cx, cy, rx, ry)
        cv.multiply(aa(dd, 0.8), "#6F52C0", 0.45)
        cv.screen(aa(np.abs(d_ellipse(X, Y, cx, cy - ry * 0.25, rx * 1.05, ry * 1.1)) - 0.9, 0.8) * (Y > cy), "#D6C4FF", 0.45)
    # lanes area: faint stars
    _stars(cv, 90, 330, 852, 5, big=4)
    # the hoard: rock, chest, coins, hearts (one render, fitted to its measured box)
    scene = [(_M, "rock", dict(center=False)),
             (_M, "chest_gold", dict(center=False, pos=(0.4, 3.3, -1.6), scale=2.15, R=rot_y(-18).tolist())),
             (_M, "rr_hoard", dict(center=False)),
             (_M, "heart", dict(center=False, pos=(-8.0, 5.0, 2.4), R=(rot_z(12) @ rot_y(20)).tolist(), scale=1.6)),
             (_M, "heart", dict(center=False, pos=(7.6, 7.4, 0.8), R=(rot_z(-10) @ rot_y(-20)).tolist(), scale=1.55))]
    # r2: seen from higher (167 shows the chest's lid top and the hoard as a pyramid from a 3/4 top view)
    ims = ctx.render({"rrHoard": dict(scene=scene, view=(0, 40), fov=16, px=1800, light=rig(key_lux=2400.0))})
    spr, (x, y) = fit_box(ims["rrHoard"], (48, 55, 345, 232), mode="contain", align=(0.5, 1.0))
    sh, (ox, oy) = shadow_of(spr, 3, 10, 10, 0.4, color="#1E1060")
    cv.over(sh, x=x + ox, y=y + oy)
    cv.over(spr, x=x, y=y)
    return cv.image()


BUILDS["rocketRaceBackdrop"] = build_rocket
