"""missing-3d lane: event art that SPEC-ui 4.2 lists as missing (3D route) -- built from the scene lane's models
(scene_events.py: the Rocket Race rock / gold chest / coin hoard / heart, the Sky Jump islands and pad), used READ-ONLY.

    rocketOfferScene     the Rocket Race offer popup's field (163, SPEC-ui 2.17.1): a starry sky with a banded planet,
                         a lilac moon, the gold-and-teal chest on its rock in a coin hoard with a red heart, coin stacks,
                         a pink cloud bank under it all (the stage strip, text and Start sit on the clouds)
    skyJumpIslandFar2    069's upper-right island (the purple-chest variant, further away and hazier than the left one)
    iconSkyDrum          the Sky Jump pad drum on its own (Profile "Sky Jump Wins", meta-002): pink cushion, cream rings,
                         gold belt with a blank pink plate, purple foot, a cyan glow under it
    planetStage1..3      the three stage planets on the Rocket Race offer's stage strip (163) and tutorial (166): a
                         lilac-striped planet, a pink-banded one, a blue one with a ring (not in SPEC-ui 4.2's list, but
                         2.17.1 / 2.17.2 draw them; ours, painted in code)

References (LOOKED AT only; measured in pt on gridded crops): research/shots/163-rocket-race-offer.png,
069-skyjump-screen.png, meta-002-avatar-tap.png, 166-rocket-race-tutorial.png. Live text (timer, prize bubble, stage
names) is never baked.
"""
from __future__ import annotations

import math
import sys

import numpy as np
from PIL import Image

import m3d_kit as MK
import scene_kit as K
import scene_events as SE
from scene_kit import Canvas, aa, d_ellipse, rgb, stops_interp, cloud_layer, fit_box, shadow_of

_M = sys.modules[__name__]


# ====================================================================== Rocket Race offer field (163)
# 163 (pt): the blue PanelFrame's field runs x 35-359, y ~196-689; OUR frame covers x 32-362, y 188-692 (the frame's
# rim hides the edges, so the art is full-bleed). In it: sky #1B1A5C (top) -> #4A35A0 (y 320) -> a lilac horizon glow
# at y ~345; the banded planet centre (308, 242) r 26; the lilac moon ground y 345-440 with craters; the hoard (rock +
# chest + coins + one heart at the left) x 86-255, y 287-450 (chest x 145-252, y 287-348); coin stacks at the left
# (48-70, 416-441), under the rock (157-227, 425-453) and right (236-291, 403-421); a white / pink cloud bank from y ~440
# (right side from ~470 behind the prize bubble) to the bottom.
RO_FRAME = (32, 188, 362, 692)


def ro_stacks():
    """Coin stacks round the rock's foot + the coin mound heaped against the chest (163: the hoard is a pyramid that
    buries the chest's lower half; scene_events' rr_hoard alone is a flat scatter). scene_events' coin (r 1)."""
    rng = np.random.default_rng(17)
    mats = []
    for (x, z, n) in [(-11.8, 4.2, 4), (-10.6, 5.2, 3), (-2.2, 5.6, 4), (0.2, 6.2, 3), (1.9, 5.4, 4), (9.8, 4.8, 3),
                      (11.6, 4.0, 2), (12.8, 5.0, 2)]:
        mats += SE.coin_stack_mats(rng, x, z, -2.4, n, 1.1)
    s = 1.1                      # coin radius in scene units; MK.heap_poses works in coin diameters (2 s)
    u = 2 * s
    for (cx, cz, rx, rz, h, y0, seed) in [(0.6, 2.2, 8.6, 2.8, 5.4, 1.0, 5), (-6.2, 1.8, 4.2, 2.2, 2.8, 0.6, 6),
                                          (7.2, 1.6, 4.0, 2.2, 2.6, 0.6, 7)]:
        for Rm, t in MK.heap_poses(cx / u, cz / u, rx / u, rz / u, h / u, y0=y0 / u, spacing=0.50, seed=seed, face=0.62,
                                   tilt=32, power=0.6, depth=0.2):
            mats.append(K.M4(Rm @ K.rot_x(0), tuple(np.asarray(t) * u), s))
    parts = [K.instanced_part("roStacks", SE.coin_mat(), SE.coin_sdf(), 0.03, mats)]
    for i, (cx, cz, rx, rz, h, y0) in enumerate([(0.6, 2.2, 8.6, 2.8, 5.4, 1.0), (-6.2, 1.8, 4.2, 2.2, 2.8, 0.6),
                                                 (7.2, 1.6, 4.0, 2.2, 2.6, 0.6)]):
        parts.append(MK.heap_core(f"roCore{i}", cx, cz, rx, rz, h, y0=y0, shrink=0.8, power=0.6, color="#E5920C"))
    return parts, 0.03


def profile_drum():
    """to-A r4: the Profile "Sky Jump Wins" drum (meta-002) is SQUATTER than the jump pad (069; scene_events.pad_drum,
    left as it is: skyJumpPad is A). Measured at 9 px/pt on meta-002 (column 1/4 in from the left): pink cushion, then
    ONE fat cream torus (4.4 pt above the belt, 3.3 below) with a thin gold belt (5.5 pt) round its lower middle, a
    short purple foot (5.5 pt visible, top r ~41 pt / 54 pt of the cream), and a BIG gold plate (18 x 19 pt) centred
    ~4.4 pt below the belt's centre, hanging over the foot. Round 3 (the pad model) stood 44 pt tall vs 38."""
    from scene_kit import lathe_part
    SEp = SE
    parts = []
    parts.append(lathe_part("pdBase", SEp.satin("pad_purple", "#5E34B8", rough=0.4),
                            [(0.0, -3.5), (3.25, -3.5), (3.8, -3.2), (4.15, -2.6), (4.35, -2.0), (0.0, -2.0)], n_seg=180, samples=90))
    parts.append(lathe_part("pdCream", SEp.gloss("pd_cream", "#F2E2D8", rough=0.32, ior=1.4),
                            [(0.0, -2.45), (4.9, -2.45), (5.35, -2.2), (5.54, -1.8), (5.5, -1.2), (5.5, -0.6), (5.55, 0.1), (5.45, 0.8), (5.05, 1.28), (0.0, 1.35)],
                            n_seg=180, samples=90))
    parts.append(lathe_part("pdGold", SEp.gloss("pad_gold", "#FFB21F", rough=0.26, ior=1.45),
                            [(0.0, -1.55), (5.35, -1.55), (5.6, -1.4), (5.72, -0.95), (5.6, -0.5), (5.35, -0.35), (0.0, -0.35)], n_seg=180, samples=90))
    parts.append(lathe_part("pdTop", SEp.gloss("pad_pink", "#EC3F7C", rough=0.28, ior=1.42),
                            [(0.0, 1.1), (4.6, 1.1), (4.72, 1.4), (4.25, 1.9), (2.6, 2.2), (0.0, 2.25)], n_seg=180, samples=90))
    # plate: centred 0.75 u below the torus middle, pushed forward so the belt (r 5.64) stays inside the frame
    parts.append(SEp.Part("pdPlateFrame", SEp.rbox(3.9, 4.3, 0.6, 0.7, center=(0, -0.95, 5.85)),
                          SEp.gloss("plate_gold", "#FFB61E", rough=0.26, ior=1.45), voxel=0.02))
    parts.append(SEp.Part("pdPlateFace", SEp.rbox(2.9, 3.3, 0.2, 0.48, center=(0, -0.95, 6.1)),
                          SEp.gloss("plate_pink", "#D9346F", rough=0.3, ior=1.4), voxel=0.02))
    return parts, 0.03


MODELS = {"roStacks": ro_stacks, "profileDrum": profile_drum}


def _stars(cv, n, y0, y1, seed, big=6, x0=0.0, x1=None):
    rng = np.random.default_rng(seed)
    X, Y = cv.X, cv.Y
    x1 = cv.w / 3 if x1 is None else x1
    for i in range(n):
        x, y = rng.uniform(x0, x1), rng.uniform(y0, y1)
        r = rng.uniform(0.45, 1.2)
        a = rng.uniform(0.35, 1.0)
        d = np.sqrt((X - x) ** 2 + (Y - y) ** 2)
        g = np.exp(-(d / r) ** 2) * a
        if i < big:   # a few sparkles with cross flares
            g = g + (np.exp(-((X - x) / 0.5) ** 2) * np.exp(-np.abs(Y - y) / 4.0) +
                     np.exp(-((Y - y) / 0.5) ** 2) * np.exp(-np.abs(X - x) / 4.0)) * 0.6
        cv.screen(np.clip(g, 0, 1), "#FFFFFF", 1.0)


def _banded_planet(cv, cx, cy, r, stops, light=(-0.45, -0.55), freq=7.0, wob=0.6, shade_col="#3E2E8A", seed=0,
                   rim="#FFFFFF", marble=0.0, atmo=None):
    """A banded gas giant (ours, painted): wavy latitude bands (warped by value noise when `marble` > 0 -- the stage
    planets' marbled look), a soft terminator toward the lower right, a bright rim on the lit side and an optional
    glassy atmosphere ring `atmo` (163's planets read as glossy balls)."""
    X, Y = cv.X, cv.Y
    d = d_ellipse(X, Y, cx, cy, r, r)
    u, v = (X - cx) / r, (Y - cy) / r
    warp = 0.0
    if marble:
        warp = marble * K.noise2(cv.h, cv.w, max(6, int(r * 3 * 0.35)), seed=int(seed * 10) + 3, octaves=3)
    # bands curve with the sphere (latitude lines seen slightly from above)
    lat = v + 0.12 * (u * u)
    band = 0.5 + 0.5 * np.sin(lat * freq + np.sin(u * 3.1 + seed) * wob + 0.5 * np.sin(lat * 17 + u * 2 + seed) + warp * 3.0)
    col = stops_interp(band, stops)
    lx, ly = light
    lit = np.clip(1 - np.sqrt((u - lx) ** 2 + (v - ly) ** 2) / 1.9, 0, 1)
    col = col * (0.42 + 0.68 * lit[..., None]) + rgb(shade_col) * (1 - lit[..., None]) * 0.34
    cv.fill(aa(d, 0.45), np.clip(col, 0, 1))
    rimc = np.clip(1 - np.abs(d) / 1.2, 0, 1) * np.clip(-(u * lx + v * ly) / 0.9, 0, 1)
    cv.screen(rimc * aa(d, 0.45), rim, 0.35)
    if atmo is not None:
        ring = np.exp(-((d + 1.6) / 1.4) ** 2) * aa(d, 0.45)
        cv.screen(ring, atmo, 0.28)


def _lat_planet(cv, cx, cy, r, lat_stops, light=(-0.45, -0.55), shade_col="#3E2E8A", seed=0, marble=0.35,
                streak=0.05, rim="#FFFFFF", atmo=None):
    """Director r3: a planet coloured by LATITUDE bands read off 163 (top -1 -> bottom +1), so the bands are as broad and
    as contrasted as the capture's (the sine bands of _banded_planet came out as thin light lines on one flat colour).
    The latitude is warped by value noise (marbling) and by fine streaks, then lit like _banded_planet."""
    X, Y = cv.X, cv.Y
    d = d_ellipse(X, Y, cx, cy, r, r)
    u, v = (X - cx) / r, (Y - cy) / r
    lat = v + 0.10 * (u * u)
    n1 = K.noise2(cv.h, cv.w, max(6, int(r * 3 * 0.30)), seed=int(seed * 10) + 3, octaves=3)
    n2 = K.noise2(cv.h, cv.w, max(3, int(r * 3 * 0.08)), seed=int(seed * 10) + 7, octaves=2)
    lat = lat + marble * 0.16 * n1 + streak * np.sin(u * 7.0 + lat * 23.0 + seed) + 0.03 * n2
    col = stops_interp(np.clip(lat, -1, 1), lat_stops)
    col = col * (1 + 0.10 * n2[..., None])                      # fine marbling in the value, as on 163
    lx, ly = light
    lit = np.clip(1 - np.sqrt((u - lx) ** 2 + (v - ly) ** 2) / 1.9, 0, 1)
    col = col * (0.40 + 0.70 * lit[..., None]) + rgb(shade_col) * (1 - lit[..., None]) * 0.30
    cv.fill(aa(d, 0.45), np.clip(col, 0, 1))
    rimc = np.clip(1 - np.abs(d) / 1.2, 0, 1) * np.clip(-(u * lx + v * ly) / 0.9, 0, 1)
    cv.screen(rimc * aa(d, 0.45), rim, 0.35)
    if atmo is not None:
        ring = np.exp(-((d + 1.6) / 1.4) ** 2) * aa(d, 0.45)
        cv.screen(ring, atmo, 0.16)


# 163 at 2x, top -> bottom (director r3): Stage 1 = lilac with MAGENTA streaks, a broad white -> mint middle band, purple
# and lilac bands below; Stage 2 = a cream / white planet with pink-red bands, darker at the bottom; Stage 3 = sky blue at
# the top, dark navy streaks through the middle, royal blue below.
LAT_STAGE1 = [(-1.0, "#B878E4"), (-0.82, "#D24CC4"), (-0.68, "#A070DE"), (-0.52, "#CC5ACC"), (-0.38, "#8E6ADA"),
              (-0.2, "#D6E2F2"), (-0.02, "#F2F6F6"), (0.12, "#92DCCE"), (0.24, "#B4E8E0"), (0.36, "#7C5ACC"),
              (0.5, "#B48AE8"), (0.64, "#6C4EC4"), (0.8, "#8A6AD2"), (1.0, "#5240AA")]
LAT_STAGE2 = [(-1.0, "#EEBCBC"), (-0.8, "#DC8496"), (-0.64, "#F4DCD2"), (-0.5, "#C8606E"), (-0.36, "#F0CCC2"),
              (-0.16, "#FFF2EC"), (0.04, "#F8E0D8"), (0.18, "#C45866"), (0.3, "#E8AEA8"), (0.44, "#B04658"),
              (0.58, "#DC9496"), (0.74, "#9C3C54"), (1.0, "#7C3050")]
LAT_STAGE3 = [(-1.0, "#6CC6F8"), (-0.62, "#44A0EE"), (-0.36, "#2E78DE"), (-0.16, "#1C4AB2"), (-0.04, "#3A88E6"),
              (0.1, "#1A44A6"), (0.26, "#2E6ED6"), (0.5, "#1E54BC"), (0.75, "#2A64CC"), (1.0, "#1C4AAE")]


def build_rocket_offer(ctx):
    F = RO_FRAME
    W, H = F[2] - F[0], F[3] - F[1]
    cv = Canvas(W, H)
    X, Y = cv.X + F[0], cv.Y + F[1]        # screen pt
    sky = stops_interp(Y, [(188, "#17175A"), (240, "#221E6E"), (290, "#35288A"), (325, "#4F38A6"), (345, "#7C62CC"),
                           (360, "#7C62CC")])
    cv.a[..., :3] = sky
    cv.a[..., 3] = 1.0
    _stars(cv, 55, 0, 160, 5, big=5)
    _banded_planet(cv, 308 - F[0], 242 - F[1], 26.5,
                   [(0, "#B98AA6"), (0.35, "#E2A895"), (0.7, "#F2CDBE"), (1, "#C6939E")], seed=1.3)
    # the moon: horizon ~y 345 (a gentle curve), lilac ground darkening toward the viewer, craters
    hz = 343 + 5 * ((X - 200) / 170) ** 2
    ground = Y > hz
    gcol = stops_interp(Y, [(343, "#C8B4F2"), (365, "#A994E4"), (400, "#8E78D6"), (450, "#7A64C8"), (692, "#7A64C8")])
    cv.a[..., :3] = np.where(ground[..., None], gcol, cv.a[..., :3])
    cv.screen(np.exp(-((Y - hz) / 5.0) ** 2), "#E2D6FF", 0.55)
    rng = np.random.default_rng(12)
    for i in range(10):
        ccx, ccy = rng.uniform(40, 350), rng.uniform(350, 430)
        rx = rng.uniform(7, 20) * (0.6 + (ccy - 345) / 90)
        ry = rx * (0.22 + (ccy - 345) / 320)
        dd = d_ellipse(X, Y, ccx, ccy, rx, ry)
        cv.multiply(aa(dd, 0.8), "#735ABF", 0.40)
        cv.screen(aa(np.abs(d_ellipse(X, Y, ccx, ccy - ry * 0.25, rx * 1.05, ry * 1.1)) - 0.9, 0.8) * (Y > ccy), "#E0D2FF", 0.40)
    # the hoard (the backdrop's chest on its rock + our stacks), seen more frontally than on the race page (163)
    scene = [(SE, "rock", dict(center=False)),
             (SE, "chest_gold", dict(center=False, pos=(0.6, 3.3, -1.6), scale=2.25, R=K.rot_y(-12).tolist())),
             (SE, "rr_hoard", dict(center=False)),
             (_M, "roStacks", dict(center=False)),
             (SE, "heart", dict(center=False, pos=(-6.6, 5.4, 4.2), R=(K.rot_z(10) @ K.rot_y(18)).tolist(), scale=1.6))]
    ims = ctx.render({"roHoard": dict(scene=scene, view=(0, 15), fov=16, px=1800, light=K.rig(key_lux=2400.0))},
                     tag="roHoard")
    hoard = K.grade(ims["roHoard"], gain=(1.10, 1.06, 0.92), gamma=0.96, sat=1.18)
    spr, (x, y) = fit_box(hoard, (44 - F[0], 285 - F[1], 294 - F[0], 455 - F[1]), mode="contain", align=(0.52, 1.0))
    sh, (ox, oy) = shadow_of(spr, 3, 9, 9, 0.35, color="#1E1060")
    cv.over(sh, x=x + ox, y=y + oy)
    cv.over(spr, x=x, y=y)
    # the cloud bank under the hoard (white tops, pink-lilac undersides), then the pale pink field to the bottom
    field = stops_interp(Y, [(440, "#F3E4F2"), (560, "#F1E0EE"), (692, "#E9D2EC")])
    low = (Y > 470)
    cv.a[..., :3] = np.where(low[..., None], field, cv.a[..., :3])
    cv.a[..., 3] = np.where(low, 1.0, cv.a[..., 3])
    rngc = np.random.default_rng(23)
    puffs_back = [(4, 470, 30), (44, 462, 22), (292, 470, 30), (330, 452, 30), (368, 460, 28), (262, 482, 22),
                  (80, 478, 18)]
    puffs_front = []
    for x0 in np.arange(-20, 400, 34):
        r = rngc.uniform(22, 36)
        puffs_front.append((float(x0 + rngc.uniform(-8, 8)), float(500 + rngc.uniform(-10, 8) + r * 0.2), float(r)))
    cloud_layer(cv, [(px - F[0], py - F[1], pr) for px, py, pr in puffs_back], top="#FFFFFF", mid="#F6E4F0",
                bottom="#E3C8E6", soft=1.8)
    cloud_layer(cv, [(px - F[0], py - F[1], pr) for px, py, pr in puffs_front], top="#FFFFFF", mid="#F7E6F1",
                bottom="#E7CDE8", soft=2.2)
    # soft pink-lilac cloud masses lower down (behind the stage strip, text and Start: 163 shows them at the sides)
    low_puffs = [(-10, 600, 44), (30, 640, 36), (380, 600, 46), (350, 650, 36), (200, 700, 60), (100, 690, 40),
                 (300, 700, 44)]
    cloud_layer(cv, [(px - F[0], py - F[1], pr) for px, py, pr in low_puffs], top="#FCF3F9", mid="#F0DDEE",
                bottom="#DDC4E6", soft=3.5, alpha=0.85)
    return cv.image()


# ====================================================================== Sky Jump: the upper-right island (069)
# 069 (pt): the purple-chest island sits at x ~229-340 (cream top), chest top y ~227, the pale gold band ~y 290-306,
# the purple base fading into the clouds by y ~335. It is further away than the left island: paler, lower contrast
# (aerial haze toward the sky's #CFDDF6). Frame 144 x 132 at (213, 214).
ISL_FRAME = (213, 214, 357, 346)
ISL_BODY = (228, 224, 341, 342)


def build_island_far2(ctx):
    """scene_events._island_build("farR") with our framing: 069's far-right chest is smaller and further back than
    the scene lane's island_scene("farR") puts it, and the island is seen from higher (pitch 34)."""
    from PIL import Image
    F, B = ISL_FRAME, ISL_BODY
    scene = [(SE, "island_farR", dict(center=False)), (SE, "chest_purple", SE._chest_pose((0.6, 0.05, -3.2), s=1.22))]
    ims = ctx.render({"isl_farR2": dict(scene=scene, view=(0, 34), fov=16, px=1500, light=SE._sky_rig())}, tag="isl_farR2")
    im = ims["isl_farR2"]
    bb = K.alpha_bbox(im)
    im = SE._fade_base(im.crop(bb), (bb[3] - bb[1]) * 0.80, (bb[3] - bb[1]) * 1.0)
    cv = Canvas(F[2] - F[0], F[3] - F[1])
    X, Y = cv.X + F[0], cv.Y + F[1]
    fw, fh = F[2] - F[0], F[3] - F[1]
    cxh, cyh = (B[0] + B[2]) / 2, B[3] - (B[3] - B[1]) * 0.12
    g = np.exp(-(((X - cxh) / ((B[2] - B[0]) * 0.42)) ** 2 + ((Y - cyh) / ((B[3] - B[1]) * 0.22)) ** 2) * 1.5)
    ex = np.clip(np.minimum(cv.X, fw - cv.X) / (0.14 * fw), 0, 1)
    ey = np.clip(np.minimum(cv.Y, fh - cv.Y) / (0.14 * fh), 0, 1)
    cv.fill(np.clip(g, 0, 1) * ex * ey, "#B48BEA", 0.5)
    spr, (x, y) = fit_box(im, (B[0] - F[0], B[1] - F[1], B[2] - F[0], B[3] - F[1]), mode="width", align=(0.5, 1.0), crop=False)
    cv.over(spr, x=x, y=y)
    MK.edge_fade(cv, 2.0)
    a = cv.a.copy()
    haze = rgb("#D2D8F6")
    a[..., :3] = a[..., :3] * 0.66 + haze * 0.34        # aerial haze: 069's far-right island is the palest object
    return Image.fromarray((np.clip(a, 0, 1) * 255 + 0.5).astype(np.uint8), "RGBA")


# ====================================================================== Profile: the Sky Jump drum (meta-002)
# meta-002 (pt): the drum x 30-83, y 540-585, top ellipse ~0.3 (seen ~18 deg from above), a cyan glow under the foot
# to y ~590. Frame 57 x 52 (SPEC-ui 4.2): drum 53 x 45 at the top, the glow in the bottom margin.
def build_sky_drum(ctx):
    # to-A r4: the squat Profile drum model (profile_drum), camera a little higher (pitch 22: 002 shows more of the
    # cushion), fitted to 002's ink box (frame x 1.3-55.8, top 2.4; the foot ends ~41.3) and a brighter, wider cyan
    # glow right under the foot (002: x ~32 pt wide, strong, fading by ~44).
    ims = ctx.render({"skyDrum": dict(scene=[(_M, "profileDrum", dict(pitch=22))], fov=14, px=700, light=SE._sky_rig())},
                     tag="skyDrumR4")
    cv = Canvas(57, 52)
    spr, (x, y) = fit_box(ims["skyDrum"], (1.3, 2.4, 55.8, 46.0), mode="contain", align=(0.5, 0.0))
    bot = (y + spr.height) / 3
    g = np.exp(-(((cv.X - 28.5) / 16.5) ** 2 + ((cv.Y - (bot - 0.6)) / 3.0) ** 2) * 1.3)
    cv.fill(np.clip(g * 1.25, 0, 1), "#7FF0FF", 0.95)
    core = np.exp(-(((cv.X - 28.5) / 12.0) ** 2 + ((cv.Y - (bot - 1.2)) / 1.6) ** 2))
    cv.fill(np.clip(core, 0, 1), "#D8FCFF", 0.8)
    cv.over(spr, x=x, y=y)
    MK.edge_fade(cv, 1.2)
    return cv.image()


# ====================================================================== stage planets (163 / 166)
# 163 (pt): three planets ~52 pt across standing on the stage tiles: Stage 1 a lilac / teal-striped planet (129, 451),
# Stage 2 a pink-red banded one (210, 453), Stage 3 a blue one with a tilted ring (315, 447, ring 90 x 30).
PLANET_FRAMES = {1: (60, 60), 2: (60, 60), 3: (104, 60)}     # 163: planets ~55 pt across, Stage 3's ring ~96 pt


def _planet_frame(kind):
    w, h = PLANET_FRAMES[kind]
    cv = Canvas(w, h)
    cx, cy, r = w / 2, h / 2, 27.0
    if kind == 1:
        _lat_planet(cv, cx, cy, r, LAT_STAGE1, seed=0.4, shade_col="#3A2A80", marble=0.45, atmo="#E8DDFF")
    elif kind == 2:
        _lat_planet(cv, cx, cy, r, LAT_STAGE2, seed=2.2, shade_col="#4A2060", marble=0.45, atmo="#FFE2EC")
    else:
        X, Y = cv.X, cv.Y
        ang = math.radians(-24)
        u = (X - cx) * math.cos(ang) - (Y - cy) * math.sin(ang)
        v = (X - cx) * math.sin(ang) + (Y - cy) * math.cos(ang)
        ringd = np.abs(np.sqrt((u / 46.0) ** 2 + (v / 13.0) ** 2) - 0.76) * 14.0 - 3.6   # director r3: 163's ring is fatter
        back = (v < 0)
        cv.fill(aa(ringd, 0.5) * back, stops_interp(u, [(-48, "#26A4EA"), (0, "#56D6FA"), (48, "#26A4EA")]), 0.9)
        _lat_planet(cv, cx, cy, 25.0, LAT_STAGE3, seed=1.0, shade_col="#10307A", marble=0.35, atmo="#CFF0FF")
        front = (v >= 0)
        cv.fill(aa(ringd, 0.5) * front, stops_interp(u, [(-48, "#2EB2F0"), (-10, "#86EEFF"), (20, "#5CDAF8"), (48, "#24A0E4")]),
                0.95)
        r = 25.0
    # a soft glass-like highlight + a small hot specular (163: the planets read as glossy balls)
    X, Y = cv.X, cv.Y
    inside = aa(d_ellipse(X, Y, cx, cy, r, r), 0.4)
    hl = np.exp(-(((X - (cx - 0.38 * r)) / (0.38 * r)) ** 2 + ((Y - (cy - 0.44 * r)) / (0.24 * r)) ** 2))
    cv.screen(hl * inside, "#FFFFFF", 0.16)     # director r3: 0.30 washed the stage planets pastel next to 163
    sp = np.exp(-(((X - (cx - 0.46 * r)) / (0.07 * r)) ** 2 + ((Y - (cy - 0.50 * r)) / (0.05 * r)) ** 2))
    cv.screen(sp * inside, "#FFFFFF", 0.8)
    MK.edge_fade(cv, 1.0)
    return cv.image()


BUILDS = {
    "rocketOfferScene": build_rocket_offer,
    "skyJumpIslandFar2": build_island_far2,
    "iconSkyDrum": build_sky_drum,
    "planetStage1": lambda ctx: _planet_frame(1),
    "planetStage2": lambda ctx: _planet_frame(2),
    "planetStage3": lambda ctx: _planet_frame(3),
}
DEST = {"rocketOfferScene": "art", "skyJumpIslandFar2": "art", "iconSkyDrum": "ui",
        "planetStage1": "ui", "planetStage2": "ui", "planetStage3": "ui"}


# ====================================================================== Weekly Contest lettering (meta-013)
# meta-013 (pt): the lettering on the Weekly page's blue rail, frame 60.1 x 193.5, 276.9 x 50 (SPEC-ui 2.15.3). Letters
# x 64-333, cap height 28 pt (W 201-229), the 'y' descender to 237; upright chunky rounded display letters (the game's
# OFL font, PC Display Black); "Weekly" yellow (face #FFED40 -> #FAB910, an orange lower bevel #FC8E04 -> #BB5500, a
# thin #631F00 line), "Contest" white (face #FFFFFF -> #E6EEFA, a blue-grey lower bevel); a ~5 pt blue outer outline
# (#1E86F2 top -> #0A55D0 bottom) with a light cyan rim #14C4F9 along its upper edge, and a ~3 pt darker blue
# extrusion (#0442B4) under it. The words are drawn from the font here -- one raster per language (EN + TR).
import os as _os
FONT_LOGO = _os.path.join(K.APP, "design", "fonts", "PCDisplay-Black.ttf")
WLOGO_FRAME = (277, 54)     # SPEC-ui says 277 x 50; the 'y' descender + outline + extrusion reach y 245 -> 54 tall
WLOGO_WORDS = {"en": ("Weekly", "Contest"), "tr": ("Haftalık", "Yarışma")}


def _dilate(m, r_px):
    from scipy import ndimage
    r = int(math.ceil(r_px))
    yy, xx = np.mgrid[-r:r + 1, -r:r + 1]
    k = (xx * xx + yy * yy) <= r_px * r_px
    return ndimage.maximum_filter(m, footprint=k)


def _shift(m, dx, dy):
    out = np.zeros_like(m)
    H, W = m.shape
    ys, yd = (slice(0, H - dy), slice(dy, H)) if dy >= 0 else (slice(-dy, H), slice(0, H + dy))
    xs, xd = (slice(0, W - dx), slice(dx, W)) if dx >= 0 else (slice(-dx, W), slice(0, W + dx))
    out[yd, xd] = m[ys, xs]
    return out


def build_weekly_logo(lang="en"):
    from PIL import ImageDraw, ImageFont
    Wf, Hf = WLOGO_FRAME
    SS = 2                                         # supersample
    W, H = Wf * 3 * SS, Hf * 3 * SS
    w1, w2 = WLOGO_WORDS[lang]
    cap_pt = 29.5
    track = -0.9 * 3 * SS                          # 013's letters sit tighter than the font's own spacing
    f = ImageFont.truetype(FONT_LOGO, 200)
    capb = f.getbbox("W")
    size = int(round(200 * cap_pt * 3 * SS / (capb[3] - capb[1])))

    def word_mask(word, fnt):
        """The word drawn char by char with tracking; returns (mask, width) on a scratch canvas."""
        adv = [fnt.getlength(ch) + track for ch in word]
        width = int(sum(adv) - track + 40)
        im = Image.new("L", (width + 80, H), 0)
        dr = ImageDraw.Draw(im)
        x = 20.0
        cb = fnt.getbbox("W")
        for ch, a in zip(word, adv):
            dr.text((x, base_top - cb[1]), ch, font=fnt, fill=255)
            x += a
        arr = np.asarray(im).astype(np.float64) / 255
        xs = np.nonzero(arr.max(0) > 0.05)[0]
        return arr[:, xs.min():xs.max() + 1]
    base_top = int((200.5 - 193.5) * 3 * SS)
    gap = int(1.8 * 3 * SS)
    room = W - 2 * int(3.5 * 3 * SS)
    for _ in range(2):
        f = ImageFont.truetype(FONT_LOGO, size)
        a1, a2 = word_mask(w1, f), word_mask(w2, f)
        tw = a1.shape[1] + gap + a2.shape[1]
        if tw <= room:
            break
        size = int(size * max(0.7, room / tw))     # TR is longer: shrink to fit (SPEC-ui 14: auto-shrink, min 0.7)
    x0 = (W - tw) // 2
    masks = []
    for arr, xo in ((a1, x0), (a2, x0 + a1.shape[1] + gap)):
        mm = np.zeros((H, W))
        w_ = min(arr.shape[1], W - xo)
        mm[:, xo:xo + w_] = arr[:, :w_]
        masks.append(np.clip(K.blur(_dilate(mm > 0.5, 0.45 * 3 * SS).astype(np.float64), 0.5), 0, 1))
    capb = f.getbbox("W")
    m1, m2 = masks
    m = np.maximum(m1, m2)
    px = 3 * SS
    yy = np.arange(H)[:, None] * np.ones((1, W))
    top_px, bot_px = base_top, base_top + (capb[3] - capb[1])
    tv = np.clip((yy - top_px) / (bot_px - top_px), 0, 1)
    cv = np.zeros((H, W, 4))

    def over(color, a):
        c = np.asarray(color, float)
        a = np.clip(a, 0, 1)[..., None]
        cv[..., :3] = c * a + cv[..., :3] * cv[..., 3:4] * (1 - a)
        cv[..., 3:4] = a + cv[..., 3:4] * (1 - a)
        cv[..., :3] = np.where(cv[..., 3:4] > 1e-6, cv[..., :3] / np.maximum(cv[..., 3:4], 1e-6), 0)

    # blue plate: outline 5 pt round the letters (holes filled at that size), extrusion 3 pt below
    outline = _dilate(m, 5.2 * px)
    outline = K.blur(outline, 0.6 * px).clip(0, 1)
    ext = _shift(outline, 0, int(3.0 * px))
    over(rgb("#0341B2"), ext)
    blue = stops_interp(tv, [(-0.2, "#2A93F6"), (0.4, "#1670E6"), (1.2, "#0A55D0")])
    over(blue, outline)
    rim = np.clip(outline - _shift(outline, 0, int(1.4 * px)), 0, 1)
    rim = rim * np.clip(1.2 - tv * 1.6, 0, 1)
    over(rgb("#14C4F9"), rim * 0.9)
    # the letters: a thin dark line, a lower bevel (the letter shifted down), the face, a light upper edge
    for mk, face, bevel, line, hi in ((m1, [(0, "#FFF26A"), (0.45, "#FFE13A"), (1, "#FAB60E")],
                                       [(0, "#FC8E04"), (1, "#BB5500")], "#631F00", "#FFFBD0"),
                                      (m2, [(0, "#FFFFFF"), (0.6, "#F4F7FE"), (1, "#DDE6F8")],
                                       [(0, "#AEBFE6"), (1, "#6F83BE")], "#27407E", "#FFFFFF")):
        dark = K.blur(_dilate(mk, 0.9 * px), 0.3 * px)
        over(rgb(line), dark * 0.85)
        low = _shift(mk, 0, int(1.6 * px))
        over(stops_interp(tv, bevel), np.maximum(low, mk))
        facem = mk * (1 - np.clip(_shift(1 - mk, 0, -int(1.6 * px)), 0, 1))     # the face = letter minus its lower bevel
        over(stops_interp(tv, face), facem)
        hl = np.clip(mk - _shift(mk, 0, int(1.0 * px)), 0, 1) * np.clip(1 - tv * 1.4, 0, 1)
        over(rgb(hi), hl * 0.7)
    out = Image.fromarray((np.clip(cv, 0, 1) * 255 + 0.5).astype(np.uint8), "RGBA")
    out = out.resize((Wf * 3, Hf * 3), Image.LANCZOS)
    c2 = Canvas(Wf, Hf)
    c2.a = np.asarray(out).astype(np.float64) / 255
    MK.edge_fade(c2, 0.8)
    return c2.image()


BUILDS["weeklyContestLogo"] = lambda ctx: build_weekly_logo("en")
BUILDS["weeklyContestLogoTR"] = lambda ctx: build_weekly_logo("tr")
# director r3 ruling: the lettering ships as SwiftUI EventLogo with LIVE text (SPEC-ui 2.15.3 route B1, PIPELINE "never
# bake translatable text", like the other four event logos); these renders are its look target (EN + TR), never shipped
DEST["weeklyContestLogo"] = "target"
DEST["weeklyContestLogoTR"] = "target"
