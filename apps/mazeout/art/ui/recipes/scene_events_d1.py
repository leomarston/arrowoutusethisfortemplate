"""R8 EVENT-ART (PLAN-P §4.2; owner items 14 + 15; SPEC rulings 37b / 38 / 44 / 46): the event art in D1 "Burrow Works",
restyled with the SAME composition and object types as today's event art (scene_events.py, m3d_events.py,
3d-events_*.py) -- ruling 46: keep the composition, change materials / colours / details just enough that the copy gate
passes, never a new theme or layout. Up & Away (the v582 Balloon Rise rules, build/p/PH0/balloon.md) is new: its page keeps
v582's object types (a tower on the left third with ledges + chests, the balloon on the right, a town at its foot, a dome
with a telescope on top) in our materials.

What changed, object by object (every new id is a NEW file; the old id becomes NOT-SHIPPED at A4's step, see
art/lanes/events-d1.handoff.json):

    Treasure Climb header   claw machine (violet/magenta neon glass box, sky-blue claw, candy cubes)
      clawHeaderArt           -> treasureHeader: a timber-framed prize cabinet (teal felt back, brass corner posts, warm
                                 lantern strip), a brass claw, the prize heap in D1 colours (bulbs, hearts, hourglasses,
                                 blocks, arrow boards), the two cheering Diggers (R2 char_digClawPair)
    Hot Streak header       pink tube slide spiralling through a lab, crew on sleds
      workerRacers            -> streakHeader: a mine-rail track swooping out of a burrow portal down to the front, R2's
                                 three Diggers in mine carts (char_digRacers), timber trestles, lanterns, crystals
    Rocket Rally            indigo space, lilac moon, gold/teal chest on a purple rock
      rocketRaceBackdrop      -> rallyBackdrop: deep-teal night, a sand-amber moon, copper + mint planets, the hoard on a
                                 teal-grey rock with a timber/brass chest
      rocketOfferScene        -> rallyOfferScene (same restyle, cream/apricot cloud bank)
    Cloud Hop               blue sky, pink clouds, cream/gold/purple islands, pink pads
      skyJumpBackdrop         -> hopBackdrop: a dawn sky (deep teal -> mint -> apricot), cream/apricot clouds
      skyJumpIsland(+Far/Far2)-> hopIsland(+Far/Far2): floating earth islets (moss top, timber deck ring, copper band,
                                 teal-rock underside), timber/brass chests, a carved arrow sign
      skyJumpPad / iconSkyDrum-> hopPad / hopDrum: a brass-and-teal drum with a tangerine cushion
      skyJumpPopupScene       -> hopOfferScene
    Weekly Cup              lilac / gold / orange podium blocks
      leaderboardPodium       -> cupPodium: timber-bodied blocks with pewter-mint / brass / copper caps
    Up & Away (new)         balloonTowerTop / balloonTowerShaft / balloonTowerFoot / balloonLedge / balloonHero /
                            eventBadgeBalloon (+ art/out/badge_upaway_rig)
    bar token               iconHexArrow (purple hex, white arrow) -> treasureToken (brass hex nut, teal enamel,
                            tangerine arrow)

No text is baked anywhere (lettering, numbers, names, "Step N", PRIZE amounts are live text). Captures are LOOKED AT only.

Build (one render job at a time on the Mac, >= 1 GB free swap, no other mfrender: art/review/tools/r8_events.py build):
    PY=~/.venvs/mf3d/bin/python
    $PY art/review/tools/r8_events.py build balloonHero ...
"""
from __future__ import annotations

import json as _json
import math
import os as _os
import sys as _sys
from dataclasses import replace as _replace

import numpy as np
from PIL import Image as _Image

from scene_kit import (Part, box, capped_cone, capsule, circle2, cylinder, extrude, gloss, glass, metal, path_tube,  # noqa: F401
                       polygon2, rect2, revolve, rounded_polygon2, satin, sphere, torus, union, rbox, rot_x, rot_y, rot_z,
                       rgb, mix, lathe_part, instanced_part, M4, fillet_points)
from scene_kit import (Canvas, aa, blur, d_ellipse, d_rrect, noise2, smooth, stops_interp, grade, shadow_of, fit_box, rig,
                       alpha_bbox, cloud_layer)
from scene_kit import BUILD as _BUILD, OUT as K_OUT, PX
from scene_kit import intersect2 as _intersect2

_M = _sys.modules[__name__]
UIOUT = _os.path.join(_os.path.dirname(K_OUT), "ui", "out")

# ---------------------------------------------------------------- D1 palette (art-direction.md §3.1; R2/R3 values)
TEAL = ("#7FEADB", "#17B3A3", "#0B8A83", "#075E5E", "#053F43")        # chrome light .. outline
TANGERINE = ("#FFD08A", "#FF9A3A", "#FF8A2A", "#E26A12", "#A64806")
SUNFLOWER = ("#FFE27A", "#FFCB2F", "#EDA80E", "#B77C04")
CREAM = ("#FFFCF0", "#FFF4DA", "#F2E2BE", "#D8C8A4")
TIMBER = ("#F2C586", "#E0A862", "#B97A3E", "#7E4E27", "#4A2C14")
ROCK = ("#8FB7B8", "#6A979B", "#4E7F86", "#2E5961", "#1B3A40")
MOSS = ("#B5DE7A", "#86C04E", "#5E9A36", "#3E6E22")
BRASS = "#E3B04B"
COPPER = "#C8743C"
IRON = "#4B4F55"
MINT = ("#DFFBF1", "#B6F5E2", "#7FE3C3", "#4CCBA5", "#2FA888")
LANTERN = "#FFCF6B"


def d1_env():
    import scene_kit as SK
    return SK.scene_env("d1", sky=(1.0, 0.93, 0.80), hor=(0.52, 0.66, 0.66), gnd=(0.50, 0.36, 0.24),
                        boxes=(((-0.35, 0.75, 0.55), (0.62, 0.52, 0.36), 0.75), ((0.75, 0.25, -0.60), (0.30, 0.44, 0.44), 0.85)))


def d1_sky_env():
    """Outdoor D1 dome (Up & Away, Cloud Hop): an apricot horizon, a mint-teal zenith, warm ground bounce."""
    import scene_kit as SK
    return SK.scene_env("d1sky", sky=(0.70, 0.90, 0.86), hor=(1.0, 0.86, 0.70), gnd=(0.62, 0.50, 0.40),
                        boxes=(((-0.35, 0.75, 0.55), (0.60, 0.55, 0.42), 0.75), ((0.75, 0.25, -0.60), (0.30, 0.46, 0.44), 0.85)))


def d1_rig(**kw):
    base = dict(key_dir=(0.45, -0.70, -0.55), key_lux=2200.0, key_color=(1.0, 0.95, 0.86),
                rim_dir=(-0.75, -0.2, 0.62), rim_lux=900.0, rim_color=(0.80, 0.96, 0.92),
                fill_dir=(0.1, 0.85, -0.5), fill_lux=650.0, fill_color=(1.0, 0.86, 0.70), ibl_exp=-0.85, shadow=True)
    base.update(kw)
    env = base.pop("env", None) or d1_env()
    return rig(base, env=env)


def sky_rig(**kw):
    kw.setdefault("env", d1_sky_env())
    kw.setdefault("fill_color", (0.86, 0.96, 0.94))
    return d1_rig(**kw)


def _tex_noise(u, v, scale, seed):
    """Cheap value noise on the (u, v) grid (texture functions)."""
    rng = np.random.default_rng(seed)
    n = int(scale)
    g = rng.uniform(-1, 1, (n + 2, n + 2))
    x, y = u * n, v * n
    x0, y0 = np.floor(x).astype(int), np.floor(y).astype(int)
    fx, fy = x - x0, y - y0
    fx, fy = fx * fx * (3 - 2 * fx), fy * fy * (3 - 2 * fy)
    a, b = g[y0 % (n + 1), x0 % (n + 1)], g[y0 % (n + 1), (x0 + 1) % (n + 1)]
    c, d = g[(y0 + 1) % (n + 1), x0 % (n + 1)], g[(y0 + 1) % (n + 1), (x0 + 1) % (n + 1)]
    return (a * (1 - fx) + b * fx) * (1 - fy) + (c * (1 - fx) + d * fx) * fy


# ====================================================================== Up & Away: the balloon
# v582 (build/p/PH0 002/024, LOOKED AT): a round envelope ~130 pt wide x ~125 pt tall of purple/yellow vertical stripes, a
# purple basket ~48 pt wide under it, the worker's cap above the rim. Ours: a PATCHED CANVAS envelope -- tangerine and
# cream gores with stitched seams, a teal crown cap with a brass ring, a sunflower skirt band, two stitched teal patches
# (the hand-made burrow world), hemp ropes down to R2's wicker basket with the lamp-hat Digger (char_digBalloon).
BALLOON_PROFILE = [(0.0, -0.30), (1.25, -0.30), (1.45, 0.25), (2.35, 1.70), (4.10, 4.20), (5.55, 6.90), (6.00, 8.70),
                   (5.72, 10.45), (4.55, 11.95), (2.55, 12.90), (0.0, 13.15)]
GORES = 14


def _envelope_tex(u, v):
    """u around (0..1), v up the profile (0 = the skirt, 1 = the crown). The camera sees u ~ 0.93 face on (measured on the
    draft render)."""
    k = (u * GORES) % 1.0
    idx = np.floor(u * GORES).astype(int) % GORES
    tang = stops_interp(v, [(0.0, "#F07818"), (0.5, "#FF8A2A"), (1.0, "#FF9E48")])
    crm = stops_interp(v, [(0.0, "#F2DDB4"), (0.5, "#FFF1D2"), (1.0, "#FFF6E2")])
    sun = stops_interp(v, [(0.0, "#EDA80E"), (0.5, "#FFC52F"), (1.0, "#FFD457")])
    upper = np.where((idx % 2 == 0)[..., None], tang, crm)
    # below the teal belt the gores shift by one (tangerine over cream, sunflower over tangerine): the belt breaks the
    # stripes into two tiers (theirs: one uninterrupted two-colour stripe)
    lower = np.where((idx % 2 == 0)[..., None], sun, tang)
    tier = smooth(v, 0.495, 0.505)
    col = lower * (1 - tier[..., None]) + upper * tier[..., None]
    # the teal belt with brass running stitches at both edges
    belt = smooth(v, 0.495, 0.502) * (1 - smooth(v, 0.568, 0.575))
    col = col * (1 - belt[..., None]) + rgb(TEAL[1]) * belt[..., None]
    for ve in (0.507, 0.564):
        st = np.exp(-((v - ve) / 0.0032) ** 2) * (np.sin(u * GORES * 2 * math.pi * 5) > 0.2)
        col = col * (1 - 0.9 * st[..., None]) + rgb("#FFE08A") * 0.9 * st[..., None]
    # the teal crown cap + its brass ring; the sunflower skirt band
    crown = smooth(v, 0.905, 0.915)
    col = col * (1 - crown[..., None]) + rgb(TEAL[1]) * crown[..., None]
    ring = np.exp(-((v - 0.905) / 0.006) ** 2)
    col = col * (1 - ring[..., None]) + rgb(BRASS) * ring[..., None]
    skirt = 1 - smooth(v, 0.105, 0.115)
    col = col * (1 - skirt[..., None]) + rgb(TEAL[2]) * skirt[..., None]
    band = np.exp(-((v - 0.118) / 0.005) ** 2)
    col = col * (1 - 0.8 * band[..., None]) + rgb(BRASS) * 0.8 * band[..., None]
    # two stitched patches on the face-on side (the hand-made burrow world)
    for (pu, pv, hw, hh, pc) in ((0.885, 0.36, 0.017, 0.050, "#2BA89A"), (0.975, 0.72, 0.014, 0.040, "#FFCB2F")):
        du, dv = np.abs(((u - pu + 0.5) % 1.0) - 0.5) / hw, np.abs(v - pv) / hh
        d = np.maximum(du, dv)
        patch = 1 - smooth(d, 0.96, 1.0)
        col = col * (1 - patch[..., None]) + rgb(pc) * patch[..., None]
        edge = np.exp(-((d - 0.84) / 0.035) ** 2)
        dash = (np.sin(np.where(du > dv, v / hh, (u - pu) / hw) * 18.0) > 0).astype(float)
        sc = "#FFF4DA" if pc != "#FFCB2F" else "#C0661A"
        col = col * (1 - (edge * dash * 0.85)[..., None]) + rgb(sc) * (edge * dash * 0.85)[..., None]
    # gore seams: a darker load tape between gores (except inside the crown and the belt)
    seam = np.exp(-(np.minimum(k, 1 - k) / 0.022) ** 2) * (1 - crown) * (1 - skirt * 0.5) * (1 - belt)
    col = col * (1 - 0.5 * seam[..., None]) + rgb("#8E4A12") * 0.5 * seam[..., None]
    # canvas weave (fine noise), and a soft darkening toward the mouth
    n = _tex_noise(u * 3, v * 3, 90, 7) * 0.035
    col = col * (1 + n[..., None])
    col = col * (0.86 + 0.14 * smooth(v, 0.0, 0.35))[..., None]
    return np.clip(col, 0, 1)


def balloon_envelope():
    m = _replace(satin("bal_canvas", "#FF8A2A", rough=0.62, ior=1.18), texture=_envelope_tex, texture_size=1024)
    parts = [lathe_part("envelope", m, BALLOON_PROFILE, n_seg=GORES * 16, samples=180)]
    # the brass crown ring (a torus at the cap's edge) and the skirt's rope ring
    parts.append(Part("crownRing", torus(2.02, 0.10, center=(0, 12.62, 0)), gloss("bal_brass", BRASS, rough=0.3, ior=1.45), voxel=0.02))
    parts.append(Part("mouthRing", torus(1.36, 0.12, center=(0, -0.25, 0)), satin("bal_rope", "#B58A55", rough=0.7), voxel=0.02))
    return parts, 0.03


MODELS = {"balloon_envelope": balloon_envelope}

# the envelope's mouth in its own units (the ropes leave the mouth ring at these 4 points, front-left/right, back-left/right)
MOUTH_R = 1.36
MOUTH_Y = -0.25


def _balloon_render(ctx, px=1100, name="balEnv"):
    ims = ctx.render({name: dict(scene=[(_M, "balloon_envelope", dict(center=False))], view=(0, 6), fov=14, px=px,
                                 light=sky_rig(key_lux=2300.0, fill_lux=760.0))})
    return ims[name]


def _rider():
    im = _Image.open(_os.path.join(K_OUT, "char_digBalloon@3x.png")).convert("RGBA")
    meta = _json.load(open(_os.path.join(K_OUT, "char_digBalloon.json")))
    return im, meta


def _paint_rope(cv, p0, p1, w=1.1, col="#8A6236", light="#D8B27A", sag=1.2):
    """A hemp rope from p0 to p1 (pt), a slight sag, a lighter upper edge."""
    X, Y = cv.X, cv.Y
    n = 48
    ts = np.linspace(0, 1, n)
    xs = p0[0] + (p1[0] - p0[0]) * ts
    ys = p0[1] + (p1[1] - p0[1]) * ts + sag * np.sin(ts * math.pi)
    x0, x1 = min(xs) - 4, max(xs) + 4
    y0, y1 = min(ys) - 4, max(ys) + 4
    m = (X > x0) & (X < x1) & (Y > y0) & (Y < y1)
    d = np.full(X.shape, 99.0)
    for i in range(n - 1):
        ax, ay, bx, by = xs[i], ys[i], xs[i + 1], ys[i + 1]
        px_, py_ = X[m] - ax, Y[m] - ay
        dx, dy = bx - ax, by - ay
        t = np.clip((px_ * dx + py_ * dy) / max(dx * dx + dy * dy, 1e-9), 0, 1)
        dd = np.sqrt((px_ - t * dx) ** 2 + (py_ - t * dy) ** 2)
        d[m] = np.minimum(d[m], dd)
    cv.fill(aa(d - w / 2, 0.35), col)
    cv.fill(aa(d - w / 4, 0.3) * 0.6, light)


# the hero frame: 150 x 220 pt (B1's page draws 150 x 190 today -> A4: 150 x 220, bottom = the count's height, i.e.
# .frame(150, 220).position(x: 285, y: balloonY - 110)); v582's balloon is ~205 pt from crown to basket bottom
HERO_F = (150.0, 220.0)
HERO_RIDER_S = 0.50            # R2's rider (150 x 176 pt) -> the basket ~ 43 pt wide (v582's ~ 60, a solid tub)
HERO_ENV_BOX = (12.0, 1.0, 138.0, 135.0)   # the envelope (with its crown ring and mouth ring) inside the hero frame


def balloon_layers(ctx, env_px=1100):
    """The hero's three layers on its frame: envelope (+ burner glow), ropes, rider (basket + Digger)."""
    env = _balloon_render(ctx, px=env_px)
    cam = env.info.get("cam")
    W, H = HERO_F
    rider, meta = _rider()
    s = HERO_RIDER_S
    rw, rh = rider.width * s, rider.height * s
    rx0, ry0 = (W - rw / PX) / 2, H - rh / PX
    rider_s = rider.resize((int(round(rw)), int(round(rh))), _Image.LANCZOS)
    tips = {k: (rx0 + meta[k][0][0] * s, ry0 + meta[k][0][1] * s) for k in ("ropeTL", "ropeTR", "ropeFL", "ropeFR")}
    # envelope, fitted into its box, bottom-aligned
    spr, (ex, ey) = fit_box(env, HERO_ENV_BOX, mode="contain", align=(0.5, 1.0))
    L_env = Canvas(W, H)
    L_env.over(spr, x=ex, y=ey)
    # the mouth ring's screen span (the fitted sprite's bottom ~ the ring): rope anchors on it
    bb = alpha_bbox(spr)
    mouth_y = (ey + bb[3]) / PX - 2.2
    cx = (ex + (bb[0] + bb[2]) / 2) / PX
    half = (bb[2] - bb[0]) / PX / 2 * (MOUTH_R / 6.0) * 1.02
    anchors = {"ropeTL": (cx - half * 0.72, mouth_y - 1.2), "ropeTR": (cx + half * 0.72, mouth_y - 1.2),
               "ropeFL": (cx - half * 1.0, mouth_y + 0.6), "ropeFR": (cx + half * 1.0, mouth_y + 0.6)}
    L_rope = Canvas(W, H)
    for k in ("ropeTL", "ropeTR"):
        _paint_rope(L_rope, anchors[k], tips[k], w=0.9, col="#6E4A28", light="#B58C58", sag=0.6)
    # the burner: a small brass pot on the ropes' crossing, a warm glow into the mouth
    bx, by = cx, mouth_y + 6.0
    X, Y = L_rope.X, L_rope.Y
    glow = np.exp(-(((X - cx) / (half * 1.1)) ** 2 + ((Y - (mouth_y - 3)) / 5.5) ** 2))
    L_env.screen(glow * (L_env.a[..., 3] > 0.5), "#FFC45A", 0.55)
    for sx in (-1, 1):
        _paint_rope(L_rope, (cx + sx * half * 0.55, mouth_y - 0.5), (bx + sx * 3.4, by - 1.6), w=0.5, col="#4B4F55", light="#8A9098", sag=0.0)
    L_rope.fill(aa(d_rrect(X, Y, bx - 4.2, by - 2.4, bx + 4.2, by + 2.4, 1.6), 0.3), "#8E6A2A")
    L_rope.fill(aa(d_rrect(X, Y, bx - 3.6, by - 2.0, bx + 3.6, by + 0.4, 1.2), 0.3), BRASS)
    flame = np.exp(-(((X - bx) / 1.6) ** 2 + ((Y - (by - 4.2)) / 2.8) ** 2))
    L_rope.fill(np.clip(flame * 1.6, 0, 1), "#FFB33A", 0.9)
    L_rope.fill(np.clip(np.exp(-(((X - bx) / 0.8) ** 2 + ((Y - (by - 3.8)) / 1.5) ** 2)) * 1.6, 0, 1), "#FFF3C4", 0.95)
    for k in ("ropeFL", "ropeFR"):
        _paint_rope(L_rope, anchors[k], tips[k], w=1.05, col="#7E5630", light="#C9A06A", sag=0.6)
    L_rider = Canvas(W, H)
    L_rider.over(rider_s, x=int(round(rx0 * PX)), y=int(round(ry0 * PX)))
    return dict(envelope=L_env.image(), ropes=L_rope.image(), rider=L_rider.image(),
                geometry=dict(frame=list(HERO_F), rider_origin=[rx0, ry0], rider_scale=s, rope_tips=tips,
                              rope_anchors=anchors, mouth_y=mouth_y, envelope_cx=cx, env_cam=cam))


def build_hero(ctx):
    L = balloon_layers(ctx)
    cv = Canvas(*HERO_F)
    for k in ("envelope", "ropes", "rider"):
        cv.over(L[k])
    im = cv.image()
    _json.dump({k: v for k, v in L["geometry"].items() if k != "env_cam"},
               open(_os.path.join(_BUILD, f"balloonHero_geom{'_draft' if ctx.draft else ''}.json"), "w"), indent=1)
    return im


BUILDS = {"balloonHero": build_hero}
DEST = {"balloonHero": "art"}
PAINT_ONLY = set()          # 2D-only builds (no mfrender): the render gate does not apply, only memory pressure


# ====================================================================== Up & Away: the page (tower, ledges, foot, top)
# The page is TALL (BalloonTrackGeometry: sky 330 + ground gap 94 + 340 per platform + street 250 = 3 734 pt for 10
# platforms). One 1179 x 11 202 px backdrop would cost ~ 50 MB decoded and a first-open decode stall, so the tower ships as
# PIECES that A4 stacks (art/lanes/events-d1.handoff.json "upaway"): balloonTowerTop at the page top, balloonTowerShaft
# repeated every 340 pt below it, balloonTowerFoot at the page bottom, balloonLedge per platform, balloonCloudA/B scattered,
# the sky stays a code gradient (D1 stops in the handoff). Every piece is painted from ONE periodic function of the page y,
# so the pieces meet without seams wherever they are stacked (ledges sit at y = 330 + 340 k from the top).
UA_SKY, UA_GAP, UA_PITCH, UA_STREET = 330.0, 94.0, 340.0, 250.0
UA_N = 10
UA_H = UA_SKY + UA_GAP + UA_PITCH * (UA_N - 1) + UA_STREET          # 3 734
UA_GROUND = UA_H - UA_STREET                                        # 3 484
UA_TOP_H = 470.0            # balloonTowerTop: page y 0 .. 470
UA_SHAFT_Y0 = 470.0         # the first shaft tile; then every 340 pt
UA_FOOT_H = 700.0           # balloonTowerFoot: page y H - 700 .. H
UA_TRACK_TOP = UA_SKY - 40.0    # B1's track starts 40 pt above the last ledge
TW_CX, TW_R = 12.0, 86.0        # the tower: a masonry cylinder, centre off-screen left, right silhouette at x 98
TW_EDGE = TW_CX + TW_R
TW_TOP = 252.0                  # the gallery floor: the tower's masonry stops here (the dome sits on it)
SHAFT_W = 112.0                 # the shaft tile's width (tower + pipe + rim glow)
CH = UA_PITCH / 16.0            # stone course height (16 courses per ledge pitch -> the pattern tiles)
BL = 34.0                       # stone block length along the curve


def ua_ledge_y(i, n=UA_N):
    """Platform i's ledge line (page pt), i = 0 .. n-1 from the bottom (B1: y(platform:))."""
    h = UA_SKY + UA_GAP + UA_PITCH * (n - 1) + UA_STREET
    return h - UA_STREET - UA_GAP - UA_PITCH * i


def _phase(Y):
    return np.mod(Y - UA_SKY, UA_PITCH)


def _hash_tab(seed, n, m):
    return np.random.default_rng(seed).uniform(0, 1, (n, m))


def paint_tower(cv, y_off, y_from=-1e9, y_to=1e9, groove_from=UA_TRACK_TOP, groove_to=None):
    """The masonry tower over page rows [y_from, y_to) of a canvas whose top is page y = y_off."""
    X, Y = cv.X, cv.Y + y_off
    rows = (Y >= y_from) & (Y < y_to)
    nx = np.clip((X - TW_CX) / TW_R, -1, 1)
    body = aa(X - TW_EDGE, 0.5) * rows
    if not body.any():
        return
    s = TW_R * np.arcsin(nx)
    ph = _phase(Y)
    row = np.floor(ph / CH).astype(int) % 16
    stag = np.where(row % 2 == 0, 0.0, BL / 2) + _hash_tab(3, 16, 1)[row, 0] * 9.0
    cidx = np.floor((s + stag + 400.0) / BL).astype(int)
    tint = _hash_tab(5, 16, 64)[row, cidx % 64]
    warm = _hash_tab(6, 16, 64)[row, cidx % 64]
    stones = ["#5E8C90", "#6A979B", "#739FA0", "#5A8589", "#7AA3A2", "#648F93"]
    pal = np.array([rgb(c) for c in stones])
    base = pal[np.clip((tint * len(stones)).astype(int), 0, len(stones) - 1)]
    base = np.where((warm > 0.9)[..., None], base * 0.7 + rgb("#A89C80") * 0.3, base)
    gn = noise2(cv.h, cv.w, 18, seed=11 + int(y_off) % 97, octaves=3)
    base = base * (1 + 0.06 * gn[..., None])
    # cylinder light: key from the upper left front, a cool sky rim on the right silhouette
    nz = np.sqrt(np.clip(1 - nx ** 2, 0, 1))
    L = np.array([-0.45, 0.35, 0.82]); L = L / np.linalg.norm(L)
    dif = np.clip(nx * L[0] + nz * L[2], 0, 1)
    shade = 0.58 + 0.52 * dif
    col = base * shade[..., None]
    # mortar joints + block bevels
    fr = ph - np.floor(ph / CH) * CH
    dj = np.minimum(fr, CH - fr)
    ds = np.abs(((s + stag + 400.0) % BL) - BL / 2)
    dsx = (BL / 2 - ds) * nz            # screen distance to the vertical joint
    mortar = np.maximum(aa(dj - 0.9, 0.45), aa(dsx - 0.8, 0.45))
    col = col * (1 - 0.72 * mortar[..., None]) + rgb("#1B3A40") * 0.72 * mortar[..., None]
    top_edge = np.clip(1 - np.abs(fr - 2.0) / 1.2, 0, 1) * (1 - mortar)
    col = col + (rgb("#D8F4EE") - col) * (0.20 * top_edge)[..., None]
    bot_edge = np.clip(1 - np.abs((CH - fr) - 2.2) / 1.6, 0, 1) * (1 - mortar)
    col = col * (1 - 0.16 * bot_edge[..., None])
    rim = np.clip((X - (TW_EDGE - 9)) / 9, 0, 1) ** 2
    col = col + (rgb("#A8F0E0") - col) * (0.30 * rim)[..., None]
    src = np.zeros((cv.h, cv.w, 4))
    src[..., :3] = np.clip(col, 0, 1)
    src[..., 3] = body
    cv.over(src)
    # the timber ring at every ledge line (the ledge's deck beam is anchored into it)
    band = aa(np.abs(ph - 6.0 - np.where(ph > 300, 340.0, 0.0)) - 8.5, 0.5) * body
    bcol = stops_interp(Y - np.floor((Y - 330) / 340) * 340, [(0, TIMBER[1]), (400, TIMBER[1])])
    wood = rgb(TIMBER[1]) * (0.62 + 0.52 * dif)[..., None]
    wg = noise2(cv.h, cv.w, 3, seed=21, octaves=2)
    wood = wood * (1 + 0.07 * wg[..., None])
    bsrc = np.zeros((cv.h, cv.w, 4)); bsrc[..., :3] = np.clip(wood, 0, 1); bsrc[..., 3] = band
    cv.over(bsrc)
    phb = np.where(ph > 300, ph - 340.0, ph)
    cv.multiply(aa(np.abs(phb + 2.2) - 0.8, 0.4) * body, "#3E2410", 0.7)
    cv.multiply(aa(np.abs(phb - 14.3) - 0.8, 0.4) * body, "#3E2410", 0.7)
    cv.screen(aa(np.abs(phb - 0.2) - 0.6, 0.4) * body, "#FFE7B8", 0.35)
    for k in range(-2, 4):
        rx_s = k * 26.0 + 6.0
        rxx = TW_CX + TW_R * math.sin(max(-1.5, min(1.5, rx_s / TW_R)))
        for ry in (1.5, 10.5):
            d = np.sqrt((X - rxx) ** 2 + (phb - ry) ** 2)
            cv.fill(aa(d - 1.3, 0.35) * body, IRON)
            cv.fill(aa(np.sqrt((X - rxx + 0.4) ** 2 + (phb - ry + 0.4) ** 2) - 0.5, 0.3) * body, "#9AA0A8", 0.8)
    # a lit window slit between the ledges (phase ~ 170), on the lit face
    wx0, wx1 = 58.0, 71.0
    wy0, wy1 = 152.0, 184.0
    arch = np.where(ph < wy0 + 6.5, np.sqrt(((X - (wx0 + wx1) / 2) / ((wx1 - wx0) / 2)) ** 2 + ((ph - (wy0 + 6.5)) / 6.5) ** 2) - 1,
                    np.maximum(np.abs(X - (wx0 + wx1) / 2) - (wx1 - wx0) / 2, np.abs(ph - (wy0 + wy1) / 2) - (wy1 - wy0) / 2) / 3.0)
    win = aa(arch * 4.0, 0.4) * body
    frame_ = aa(arch * 4.0 - 2.4, 0.4) * body
    cv.fill(frame_, TIMBER[3])
    glow = stops_interp(ph, [(wy0, "#FFE6A0"), (wy1, "#F2A94A")])
    cv.fill(win, glow)
    cv.multiply(aa(np.abs(X - (wx0 + wx1) / 2) - 0.6, 0.3) * win, "#6A3E1C", 0.8)
    cv.multiply(aa(np.abs(ph - (wy0 + 16)) - 0.6, 0.3) * win, "#6A3E1C", 0.8)
    cv.fill(aa(np.maximum(np.abs(X - (wx0 + wx1) / 2) - 9.0, np.abs(ph - (wy1 + 1.8)) - 1.8), 0.4) * body, TIMBER[2])
    halo = np.exp(-(((X - (wx0 + wx1) / 2) / 14.0) ** 2 + ((ph - (wy0 + wy1) / 2) / 22.0) ** 2)) * body
    cv.screen(halo, "#FFC46A", 0.18)
    # the copper downpipe on the right side, brass collars
    px0, px1 = 84.5, 91.0
    pc = aa(np.maximum(X - px1, px0 - X), 0.4) * rows
    u = np.clip((X - px0) / (px1 - px0), 0, 1)
    pcol = stops_interp(u, [(0, "#E7A16A"), (0.3, "#F2C08C"), (0.6, COPPER), (1.0, "#7A3E1A")])
    cv.fill(pc, pcol)
    for cy in (58.0, 228.0):
        cm = aa(np.maximum(np.maximum(X - (px1 + 1.4), (px0 - 1.4) - X), np.abs(ph - cy) - 2.6), 0.35) * rows
        cv.fill(cm, stops_interp(u, [(0, "#FFE39A"), (0.4, "#E8B85A"), (1.0, "#7E5510")]))
        cv.fill(aa(np.sqrt((X - (px0 + px1) / 2) ** 2 + (ph - cy) ** 2) - 0.9, 0.3) * rows, "#7E5510")
    # the track groove (B1 draws the dark rail + green fill at x 34 +- 11 over it)
    g_to = groove_to if groove_to is not None else UA_GROUND
    gm = rows & (Y >= groove_from) & (Y <= g_to)
    gv = aa(np.abs(X - 34.0) - 15.0, 0.4) * gm
    cv.multiply(gv, "#12292D", 0.62)
    cv.multiply(np.clip(1 - (X - 19.0) / 5.0, 0, 1) * gv, "#0A1A1C", 0.5)
    for ex in (19.0, 49.0):
        cv.fill(aa(np.abs(X - ex) - 0.9, 0.35) * gm, stops_interp(Y * 0 + (0.2 if ex < 30 else 0.7), [(0, "#FFE39A"), (1, "#B98A2E")]))


def paint_stars(cv, y_off, y0, y1, n=70, seed=4):
    X, Y = cv.X, cv.Y + y_off
    rng = np.random.default_rng(seed)
    for i in range(n):
        x, y = rng.uniform(4, 389), rng.uniform(y0, y1)
        r = rng.uniform(0.6, 1.5)
        a = rng.uniform(0.55, 1.0) * np.clip(1 - (y - y0) / (y1 - y0) * 0.5, 0.4, 1)
        m = (np.abs(X - x) < 10) & (np.abs(Y - y) < 10)
        if not m.any():
            continue
        d = np.sqrt((X - x) ** 2 + (Y - y) ** 2)
        g = np.exp(-(d / r) ** 2) * a
        if i < 7:
            g = g + (np.exp(-((X - x) / 0.45) ** 2) * np.exp(-np.abs(Y - y) / 4.0) +
                     np.exp(-((Y - y) / 0.45) ** 2) * np.exp(-np.abs(X - x) / 4.0)) * 0.6 * a
        cv.screen(np.clip(g, 0, 1), "#FFF6DC", 1.0)


def build_tower_shaft(ctx):
    cv = Canvas(SHAFT_W, UA_PITCH)
    paint_tower(cv, UA_SHAFT_Y0)
    return cv.image()


BUILDS["balloonTowerShaft"] = build_tower_shaft
DEST["balloonTowerShaft"] = "ui"
PAINT_ONLY.add("balloonTowerShaft")


# ---------------------------------------------------------------------- the ledge (one per platform)
# Frame 240 x 150 pt, top-left = page (60, ledge_y - 94) = B1's BalloonLedge frame origin (its code-drawn purple bar, sign and
# chest box keep their places): the deck top at local y 91 (B1: ledge_y - 3), the chest stands at local (146..224, 22..92),
# the blank sign board hangs at local (34..118, 112..140) on two chains (B1's "Step N" live text, baseline local 131), the
# round burrow door stands against the tower at local x 14..56. v582 (LOOKED AT): a purple slab ledge, a pink arched door,
# a blue sign on an arm, a pipe bracket below. Ours: a plank balcony on iron knee braces, a teal plank door in a stone
# arch with a brass porthole, a hanging timber board, a lantern post at the outer end.
LEDGE_F = (240.0, 150.0)


def _tb(name, x0, x1, y0, y1, z0, z1, col, r=0.06, rough=0.55, voxel=0.02):
    """A box from local-pt style extents given in world units (x right, y up, z toward the camera)."""
    return Part(name, rbox(x1 - x0, y1 - y0, z1 - z0, r, center=((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2)),
                satin(name, col, rough=rough), voxel=voxel)


def ledge_model():
    rng = np.random.default_rng(12)
    parts = []
    # deck: 5 boards along the ledge (seen from above), a front beam, bolts
    zs = np.linspace(-2.2, 2.0, 6)
    for k in range(5):
        hexc = mix(TIMBER[1], TIMBER[0], rng.uniform(0, 0.5)) if k % 2 == 0 else mix(TIMBER[1], TIMBER[2], rng.uniform(0.1, 0.45))
        parts.append(_tb(f"plank{k}", 0.0, 23.7 - rng.uniform(0, 0.25), -9.55, -9.1, zs[k] + 0.04, zs[k + 1] - 0.04, hexc, r=0.05))
    parts.append(_tb("beam", -0.2, 23.9, -10.4, -9.5, 1.55, 2.35, TIMBER[2], r=0.12))
    parts.append(_tb("beamEnd", 23.2, 23.95, -10.4, -9.1, -2.2, 2.35, TIMBER[2], r=0.1))
    bolts = union(*[sphere(0.16, center=(x, -9.95, 2.38)) for x in (1.2, 6.2, 11.2, 16.2, 21.2)])
    parts.append(Part("bolts", bolts, gloss("iron_bolt", IRON, rough=0.35, ior=1.5), voxel=0.012))
    # iron knee braces from the tower wall to the beam's underside
    braces = []
    for bx in (2.4, 15.6):
        pts = [(bx - 2.0, -14.0, 0.2), (bx - 1.2, -12.1, 0.6), (bx + 0.4, -10.9, 1.0), (bx + 2.4, -10.45, 1.3)]
        braces.append(path_tube(pts, [0.2, 0.19, 0.18, 0.17]))
        braces.append(capsule((bx - 2.3, -14.3, 0.2), (bx - 2.3, -10.5, 0.2), 0.16))
    parts.append(Part("braces", union(*braces), gloss("iron", IRON, rough=0.42, ior=1.45), voxel=0.015))
    # the door: a stone arch round a teal plank door, iron straps, brass knob + porthole
    arch2 = rounded_polygon2([(-2.3, 0.0), (2.3, 0.0), (2.3, 4.6), (1.6, 6.3), (0.0, 7.0), (-1.6, 6.3), (-2.3, 4.6)], 0.4, n_arc=6)
    door2 = rounded_polygon2([(-1.7, 0.0), (1.7, 0.0), (1.7, 4.4), (1.15, 5.7), (0.0, 6.25), (-1.15, 5.7), (-1.7, 4.4)], 0.35, n_arc=6)
    dx, dy = 3.5, -9.1
    stone = extrude(arch2, 0.45, round=0.25).subtract(extrude(door2, 1.0))
    parts.append(Part("arch", stone.translate(dx, dy, -1.8), satin("arch_stone", ROCK[1], rough=0.7), voxel=0.02))
    boards = []
    for k in range(4):
        bx0 = -1.7 + k * 0.85
        b2 = _intersect2(door2, rect2(0.40, 4.0).translate(bx0 + 0.425, 3.1))
        boards.append(extrude(b2, 0.12, round=0.05))
    parts.append(Part("door", union(*boards).translate(dx, dy, -1.62), satin("door_teal", "#1F8C80", rough=0.5), voxel=0.012))
    straps = union(*[extrude(rect2(1.72, 0.14).translate(0, yy), 0.05, round=0.03) for yy in (1.2, 3.9)])
    parts.append(Part("straps", straps.translate(dx, dy, -1.47), gloss("iron", IRON, rough=0.42, ior=1.45), voxel=0.01))
    parts.append(Part("knob", sphere(0.2, center=(dx + 1.1, dy + 2.6, -1.4)), gloss("brass", BRASS, rough=0.25, ior=1.5), voxel=0.01))
    parts.append(Part("porthole", torus(0.62, 0.14, center=(0, 0, 0)).rotate_x(90).translate(dx, dy + 4.8, -1.42),
                      gloss("brass", BRASS, rough=0.25, ior=1.5), voxel=0.01))
    parts.append(Part("portGlass", cylinder(0.56, 0.04).rotate_x(90).translate(dx, dy + 4.8, -1.47),
                      _replace(gloss("port_glass", "#FFD27A", rough=0.15, ior=1.4), emissive="#E8A23A"), voxel=0.01))
    # the lantern post at the outer end
    parts.append(_tb("post", 22.55, 23.05, -9.2, -5.4, 1.55, 2.05, TIMBER[2], r=0.1))
    parts.append(_tb("arm", 21.6, 23.05, -5.75, -5.4, 1.62, 1.98, TIMBER[2], r=0.08))
    lant = union(rbox(0.62, 0.8, 0.62, 0.1, center=(21.85, -6.55, 1.8)), cylinder(0.22, 0.12, center=(21.85, -6.05, 1.8)))
    parts.append(Part("lanternCage", lant.subtract(rbox(0.46, 0.62, 1.0, 0.05, center=(21.85, -6.58, 1.8))).subtract(
        rbox(1.0, 0.62, 0.46, 0.05, center=(21.85, -6.58, 1.8))), gloss("brass", BRASS, rough=0.3, ior=1.5), voxel=0.01))
    parts.append(Part("lanternGlow", rbox(0.48, 0.6, 0.48, 0.08, center=(21.85, -6.58, 1.8)),
                      _replace(satin("lamp_glow", "#FFE3A0", rough=0.3), emissive="#FFC04A"), voxel=0.01))
    # the blank sign board on two chains under the beam (B1's live "Step N" goes on it)
    parts.append(_tb("signBoard", 3.4, 11.8, -14.0, -11.2, 1.3, 1.62, TIMBER[1], r=0.18))
    parts.append(_tb("signFace", 3.75, 11.45, -13.7, -11.5, 1.55, 1.72, "#1F8C80", r=0.12))
    links = []
    for cx_ in (4.6, 10.6):
        for k in range(3):
            yy = -10.55 - k * 0.28
            links.append(torus(0.1, 0.035, center=(0, 0, 0)).rotate_y(90 if k % 2 else 0).rotate_x(90).translate(cx_, yy, 1.46))
    parts.append(Part("chains", union(*links), gloss("iron", IRON, rough=0.4, ior=1.45), voxel=0.008))
    return parts, 0.02


MODELS["ledge"] = ledge_model
LEDGE_TILT = 16.0          # the ledge is seen from slightly above (v582: its top face shows)


def _pivot_pose(R, pivot):
    R = np.asarray(R, float)
    p = np.asarray(pivot, float)
    return dict(center=False, R=R.tolist(), pos=tuple(p - R @ p))


def build_ledge(ctx):
    W, H = LEDGE_F
    spec = dict(scene=[(_M, "ledge", _pivot_pose(rot_x(LEDGE_TILT), (0.0, -9.1, 2.0)))],
                bounds=((0.0, -H / 10, -3.0), (W / 10, 0.0, 3.0)), aspect=W / H, margin=1.0, fov=6.0, px=1500,
                light=sky_rig(key_lux=2300.0, fill_lux=700.0))
    ims = ctx.render({"uaLedge": spec})
    im = ims["uaLedge"].resize((int(W * PX), int(H * PX)), _Image.LANCZOS)
    cv = Canvas(W, H)
    sh, (ox, oy) = shadow_of(im, 0, 5, 6, 0.30, color="#123036")
    cv.over(sh, x=ox, y=oy)
    cv.over(im)
    # the lantern's warm pool on the deck + door
    X, Y = cv.X, cv.Y
    g = np.exp(-(((X - 218) / 20.0) ** 2 + ((Y - 70) / 16.0) ** 2))
    cv.screen(g * (cv.a[..., 3] > 0.5), "#FFC46A", 0.25)
    edge = np.clip(np.minimum(np.minimum(X - 0.3, W - 0.3 - X), np.minimum(Y - 0.3, H - 0.3 - Y)) / 1.0, 0, 1)
    cv.a[..., 3] *= edge
    return cv.image()


BUILDS["balloonLedge"] = build_ledge
DEST["balloonLedge"] = "ui"


# ---------------------------------------------------------------------- 2D helpers (polygons, houses, bushes)
def poly_cov(cv, pts_pt, y_off=0.0, ss=2):
    """Anti-aliased coverage of a polygon given in page pt (y_off = the canvas top's page y); drawn in its bbox only."""
    from PIL import ImageDraw
    xs = [x * PX for x, y in pts_pt]
    ys = [(y - y_off) * PX for x, y in pts_pt]
    x0, x1 = max(0, int(math.floor(min(xs))) - 2), min(cv.w, int(math.ceil(max(xs))) + 2)
    y0, y1 = max(0, int(math.floor(min(ys))) - 2), min(cv.h, int(math.ceil(max(ys))) + 2)
    out = np.zeros((cv.h, cv.w))
    if x1 <= x0 or y1 <= y0:
        return out
    im = _Image.new("L", ((x1 - x0) * ss, (y1 - y0) * ss), 0)
    ImageDraw.Draw(im).polygon([((x - x0) * ss, (y - y0) * ss) for x, y in zip(xs, ys)], fill=255)
    im = im.resize((x1 - x0, y1 - y0), _Image.BOX)
    out[y0:y1, x0:x1] = np.asarray(im).astype(np.float64) / 255
    return out


def haze(col, k, to="#F6C9A0"):
    """col (hex or rgb array) pushed toward the aerial-perspective colour by k -> rgb array."""
    c = rgb(col) if isinstance(col, str) else np.asarray(col, float)
    return c * (1 - k) + rgb(to) * k


def _hx(c):
    c = np.clip(np.asarray(c, float), 0, 1)
    return "#%02X%02X%02X" % tuple(int(round(v * 255)) for v in c)


def paint_house(cv, y_off, x, ground, w, h, roof_h, side_w, k_haze=0.0, wall=TIMBER[1], roof="#2E6E6C", seed=0,
                chimney=True, door=True, windows=2, round_door=False):
    """A timber cottage in 3/4 view: front gable (w x h + roof), a shaded side face (side_w), teal-slate roof, lit windows."""
    X, Y = cv.X, cv.Y + y_off
    rng = np.random.default_rng(seed)
    hz = lambda c: _hx(haze(c, k_haze))
    top = ground - h
    # side face (to the right, receding up-right)
    side = [(x + w, ground), (x + w + side_w, ground - side_w * 0.35), (x + w + side_w, top - side_w * 0.35), (x + w, top)]
    cv.fill(poly_cov(cv, side, y_off), hz(mix(wall, "#5A3418", 0.45)))
    # front face
    front = [(x, ground), (x + w, ground), (x + w, top), (x, top)]
    fcov = poly_cov(cv, front, y_off)
    cv.fill(fcov, hz(wall))
    # planks on the front (vertical seams)
    for sx in np.arange(x + 4.5, x + w - 1, 4.5):
        cv.multiply(aa(np.abs(X - sx) - 0.35, 0.3) * fcov, hz("#6A3E1C"), 0.35)
    # roof: the gable triangle on the front + the slope over the side
    apex = (x + w / 2, top - roof_h)
    gable = [(x - 2.5, top + 1), (x + w + 2.5, top + 1), apex]
    slope = [(apex[0], apex[1]), (x + w + 2.5, top + 1), (x + w + side_w + 2.5, top + 1 - side_w * 0.35),
             (apex[0] + side_w, apex[1] - side_w * 0.35)]
    cv.fill(poly_cov(cv, slope, y_off), hz(roof))
    # slate rows on the slope
    scov = poly_cov(cv, slope, y_off)
    for r in range(1, 6):
        t = r / 6
        yy = apex[1] + (top + 1 - apex[1]) * t
        cv.multiply(aa(np.abs(Y + (X - apex[0]) * 0.35 - yy) - 0.3, 0.3) * scov, hz("#163C3C"), 0.3)
    gcov = poly_cov(cv, gable, y_off)
    cv.fill(gcov, hz(mix(roof, "#0E2E2E", 0.35)))
    inner = [(x + 1.8, top + 0.4), (x + w - 1.8, top + 0.4), (apex[0], apex[1] + 3.2)]
    cv.fill(poly_cov(cv, inner, y_off), hz(mix(wall, "#FFE6B8", 0.18)))
    # chimney with a smoke curl
    if chimney:
        cx0 = apex[0] + side_w * 0.55
        cy0 = apex[1] - side_w * 0.35 * 0.55 + roof_h * 0.35
        ch = [(cx0 - 2.2, cy0 + 2), (cx0 + 2.2, cy0 + 2), (cx0 + 2.2, cy0 - 9), (cx0 - 2.2, cy0 - 9)]
        cv.fill(poly_cov(cv, ch, y_off), hz(ROCK[3]))
        cv.fill(poly_cov(cv, [(cx0 - 2.8, cy0 - 9), (cx0 + 2.8, cy0 - 9), (cx0 + 2.8, cy0 - 10.6), (cx0 - 2.8, cy0 - 10.6)], y_off), hz(ROCK[2]))
        for j in range(4):
            px_, py_ = cx0 + 2.0 * j + math.sin(j * 1.3) * 1.2, cy0 - 14 - 6.0 * j
            d = np.sqrt((X - px_) ** 2 + (Y - py_) ** 2) - (2.2 + 1.0 * j)
            cv.fill(aa(d, 1.4) * (0.55 - 0.1 * j), hz("#F7EBDD"))
    # windows (warm light) + door
    ww = min(6.0, w / (windows * 2 + 1) * 1.1)
    for i in range(windows):
        wx = x + w * (i + 1) / (windows + 1) - ww / 2
        wy = top + h * 0.22
        wr = [(wx, wy), (wx + ww, wy), (wx + ww, wy + ww * 1.1), (wx, wy + ww * 1.1)]
        cv.fill(poly_cov(cv, wr, y_off), hz("#FFD27A"))
        cv.multiply(aa(np.abs(X - (wx + ww / 2)) - 0.3, 0.25) * poly_cov(cv, wr, y_off), "#8A5020", 0.7)
        cv.fill(poly_cov(cv, [(wx - 0.8, wy + ww * 1.1), (wx + ww + 0.8, wy + ww * 1.1), (wx + ww + 0.8, wy + ww * 1.1 + 1.2),
                              (wx - 0.8, wy + ww * 1.1 + 1.2)], y_off), hz(TIMBER[3]))
    if door:
        dw = min(7.0, w * 0.28)
        dx = x + w * 0.5 - dw / 2 if windows != 2 else x + w * 0.5 - dw / 2
        if round_door:
            d = np.sqrt((X - (dx + dw / 2)) ** 2 + (Y - ground) ** 2) - dw * 0.62
            cv.fill(aa(d, 0.4) * (Y < ground), hz("#1F8C80"))
            cv.fill(aa(np.sqrt((X - (dx + dw * 0.8)) ** 2 + (Y - (ground - dw * 0.3)) ** 2) - 0.6, 0.3), hz(BRASS))
        else:
            dr = [(dx, ground), (dx + dw, ground), (dx + dw, ground - dw * 1.5), (dx, ground - dw * 1.5)]
            cv.fill(poly_cov(cv, dr, y_off), hz("#1F8C80"))
    # contact shadow
    d = np.sqrt(((X - (x + w / 2 + side_w / 2)) / (w * 0.7 + side_w)) ** 2 + ((Y - ground) / 2.5) ** 2)
    cv.multiply(np.clip(1 - d, 0, 1) * (Y > ground - 1), "#2E3A20", 0.35 * (1 - k_haze))


def paint_bushes(cv, y_off, puffs, dark=MOSS[3], mid=MOSS[1], light=MOSS[0], k_haze=0.0, seed=0):
    """Round moss-green canopies (a bush / tree crown bank) from puffs [(cx, cy, r) page pt]."""
    pz = [(cx, cy - y_off, r) for cx, cy, r in puffs]
    cloud_layer(cv, pz, top=_hx(haze(light, k_haze)), mid=_hx(haze(mid, k_haze)), bottom=_hx(haze(dark, k_haze)),
                rim=_hx(haze("#E4F7B0", k_haze)), soft=0.7, seed=seed)
    # leaf speckle
    X, Y = cv.X, cv.Y + y_off
    rng = np.random.default_rng(seed + 3)
    for cx, cy, r in puffs:
        for _ in range(int(r * 0.9)):
            a = rng.uniform(0, 2 * math.pi)
            rr = r * math.sqrt(rng.uniform(0, 0.8))
            px_, py_ = cx + rr * math.cos(a), cy + rr * math.sin(a) * 0.9
            d = np.sqrt((X - px_) ** 2 + (Y - py_) ** 2) - rng.uniform(0.8, 1.6)
            m = (np.abs(X - px_) < 3) & (np.abs(Y - py_) < 3)
            if m.any():
                cv.fill(aa(d, 0.4) * m, _hx(haze(dark if py_ > cy else light, k_haze)), 0.35)


def paint_hills(cv, y_off, base_y, amp, col, k_haze, seed, freq=0.018):
    X, Y = cv.X, cv.Y + y_off
    rng = np.random.default_rng(seed)
    ph1, ph2 = rng.uniform(0, 6.3, 2)
    top = base_y - amp * (0.55 + 0.45 * np.sin(X * freq + ph1)) - amp * 0.3 * np.sin(X * freq * 2.7 + ph2)
    cov = aa(top - Y, 0.6)
    shade = np.clip((Y - top) / 40.0, 0, 1)
    c = rgb(_hx(haze(col, k_haze)))
    n1 = noise2(cv.h, cv.w, 26, seed=seed + 40, octaves=3)
    n2 = noise2(cv.h, cv.w, 5, seed=seed + 41, octaves=2)
    tex = (0.10 * n1 + 0.05 * n2) * (1 - k_haze)
    cc = c[None, None] * (1 - 0.18 * shade[..., None] + tex[..., None]) + rgb("#FFE6C0")[None, None] * 0.12 * np.clip(1 - (Y - top) / 3.0, 0, 1)[..., None]
    src = np.zeros((cv.h, cv.w, 4)); src[..., :3] = np.clip(cc, 0, 1); src[..., 3] = cov
    cv.over(src)
    return top


# ---------------------------------------------------------------------- the tower top: gallery, observatory dome, telescope
# v582 (LOOKED AT, PH0 016): the tower ends in a railed balcony under a purple observatory dome with a telescope pointing
# up-right, star-lit navy sky. Ours: a timber gallery with posts and a rope rail, a teal plank drum under a riveted
# COPPER dome with brass ribs, a brass telescope with teal bands through the dome's slit, a tangerine pennant on top.
# World units: 1 u = 10 pt, page-registered (x_u = x / 10, y_u = -y / 10); the tower's front surface is at z ~ 0.
TW_Z = -TW_R / 10.0                   # the tower axis (z)


def _gallery_front(theta_deg, r_u, y_u):
    t = math.radians(theta_deg)
    return (TW_CX / 10 + r_u * math.sin(t), y_u, TW_Z + r_u * math.cos(t))


def ua_top_model():
    parts = []
    deck_y = -TW_TOP / 10
    ring = cylinder(TW_R / 10 + 0.5, 0.45, round=0.12, center=(TW_CX / 10, deck_y + 0.25, TW_Z))
    parts.append(Part("galleryDeck", ring, satin("gal_deck", TIMBER[1], rough=0.6), voxel=0.05))
    parts.append(Part("galleryBeam", cylinder(TW_R / 10 + 0.3, 0.35, round=0.1, center=(TW_CX / 10, deck_y - 0.45, TW_Z)),
                      satin("gal_beam", TIMBER[2], rough=0.6), voxel=0.05))
    posts, rails = [], []
    for th in range(-30, 91, 12):
        p0 = _gallery_front(th, TW_R / 10 + 0.25, deck_y + 0.5)
        p1 = (p0[0], p0[1] + 2.1, p0[2])
        posts.append(capsule(p0, p1, 0.16))
    rail_pts = [_gallery_front(th, TW_R / 10 + 0.25, deck_y + 2.45) for th in range(-34, 95, 4)]
    rails.append(path_tube(rail_pts, [0.13] * len(rail_pts)))
    rope_pts = [_gallery_front(th, TW_R / 10 + 0.28, deck_y + 1.3 - 0.25 * abs(math.sin(math.radians((th + 30) * 15)))) for th in range(-34, 95, 3)]
    parts.append(Part("galleryPosts", union(*posts), satin("gal_post", TIMBER[2], rough=0.6), voxel=0.02))
    parts.append(Part("galleryRail", union(*rails), satin("gal_rail", TIMBER[1], rough=0.55), voxel=0.02))
    parts.append(Part("galleryRope", path_tube(rope_pts, [0.07] * len(rope_pts)), satin("gal_rope", "#B58A55", rough=0.75), voxel=0.012))
    # the observatory: drum + dome, centred at x 42 pt, set back on the gallery
    dcx, dcz = 4.6, TW_Z + 4.8
    drum_top = deck_y + 5.0
    drum = cylinder(5.1, (drum_top - deck_y) / 2, center=(dcx, (drum_top + deck_y) / 2 + 0.25, dcz))
    parts.append(Part("drum", drum, satin("drum_teal", "#1F8C80", rough=0.55), voxel=0.03))
    bands = union(*[torus(5.14, 0.11, center=(dcx, yy, dcz)) for yy in (deck_y + 0.9, drum_top - 0.2)])
    parts.append(Part("drumBands", bands, gloss("brass", BRASS, rough=0.3, ior=1.5), voxel=0.015))
    dome = sphere(5.3, center=(dcx, drum_top, dcz)).intersect(box(6, 6, 6, center=(dcx, drum_top + 6, dcz)))
    slit_dir = np.array([math.sin(math.radians(35)), 0, math.cos(math.radians(35))])
    slit = box(0.85, 6.4, 3.4, center=(0, 0, 0)).rotate_y(35).translate(dcx + slit_dir[0] * 3.8, drum_top + 2.6, dcz + slit_dir[2] * 3.8)
    dome_cut = dome.subtract(slit, k=0.1)
    parts.append(Part("dome", dome_cut, gloss("dome_copper", "#D07A40", rough=0.34, ior=1.45), voxel=0.03))
    ribs = []
    for a in (-60, -20, 60, 100, 140):
        pts = []
        for e in np.linspace(0, 88, 12):
            ra, re_ = math.radians(a), math.radians(e)
            pts.append((dcx + 5.36 * math.cos(re_) * math.sin(ra), drum_top + 5.36 * math.sin(re_), dcz + 5.36 * math.cos(re_) * math.cos(ra)))
        ribs.append(path_tube(pts, [0.1] * len(pts)))
    parts.append(Part("domeRibs", union(*ribs), gloss("brass", BRASS, rough=0.3, ior=1.5), voxel=0.015))
    parts.append(Part("slitDark", box(0.72, 2.9, 1.7, center=(0, 0, 0)).rotate_y(35).translate(dcx + slit_dir[0] * 2.9, drum_top + 2.4, dcz + slit_dir[2] * 2.9),
                      satin("slit_dark", "#12292D", rough=0.9), voxel=0.02))
    # the telescope out of the slit, pointing up-right (straight tubes via path_tube: no orientation maths)
    a0 = np.array([dcx + 1.2, drum_top + 1.8, dcz + 1.9])
    a1 = np.array([dcx + 8.4, drum_top + 6.1, dcz + 3.9])

    def seg(f0, f1, r0, r1, n=6):
        pts = [tuple(a0 + (a1 - a0) * f) for f in np.linspace(f0, f1, n)]
        return path_tube(pts, list(np.linspace(r0, r1, n)))
    parts.append(Part("scope", seg(0.0, 1.0, 0.55, 0.78), gloss("scope_brass", "#E8B85A", rough=0.28, ior=1.5), voxel=0.02))
    parts.append(Part("scopeBands", union(seg(0.30, 0.36, 0.68, 0.70, 3), seg(0.66, 0.72, 0.76, 0.78, 3), seg(0.95, 1.0, 0.86, 0.86, 3)),
                      satin("scope_teal", TEAL[2], rough=0.45), voxel=0.015))
    parts.append(Part("lens", seg(1.0, 1.012, 0.7, 0.7, 2), _replace(gloss("lens", "#BFF3EA", rough=0.1, ior=1.5), emissive="#3E8C84"), voxel=0.01))
    # pennant pole + a tangerine pennant
    top_y = drum_top + 5.3
    parts.append(Part("pole", capsule((dcx, top_y - 0.2, dcz), (dcx, top_y + 3.6, dcz), 0.1), gloss("brass", BRASS, rough=0.3, ior=1.5), voxel=0.012))
    parts.append(Part("poleKnob", sphere(0.22, center=(dcx, top_y + 3.7, dcz)), gloss("brass", BRASS, rough=0.3, ior=1.5), voxel=0.01))
    pen = polygon2([(0.0, 0.55), (2.9, 0.05), (0.0, -0.55)])
    parts.append(Part("pennant", extrude(pen, 0.04, round=0.03).translate(dcx + 0.12, top_y + 3.05, dcz),
                      satin("pennant", TANGERINE[2], rough=0.6), voxel=0.012))
    return parts, 0.03


MODELS["ua_top"] = ua_top_model


def build_tower_top(ctx):
    W, H = 393.0, UA_TOP_H
    cv = Canvas(W, H)
    paint_stars(cv, 0.0, 6.0, 330.0, n=110, seed=4)
    paint_tower(cv, 0.0, y_from=TW_TOP - 2.0)
    spec = dict(scene=[(_M, "ua_top", dict(center=False))], bounds=((0.0, -H / 10, -3.0), (W / 10, 0.0, 3.0)), aspect=W / H,
                margin=1.0, fov=6.0, px=1900, light=sky_rig(key_lux=2200.0, fill_lux=650.0, key_dir=(0.5, -0.55, -0.65)))
    ims = ctx.render({"uaTop": spec})
    im = ims["uaTop"].resize((cv.w, cv.h), _Image.LANCZOS)
    sh, (ox, oy) = shadow_of(im, 0, 4, 5, 0.28, color="#0E2A2E")
    cv.over(sh, x=ox, y=oy)
    cv.over(im)
    # the dome's warm slit glow + the lens glint
    X, Y = cv.X, cv.Y
    cv.screen(np.exp(-(((X - 62) / 10.0) ** 2 + ((Y - 186) / 14.0) ** 2)) * (cv.a[..., 3] > 0.5), "#FFC46A", 0.25)
    return cv.image()


BUILDS["balloonTowerTop"] = build_tower_top
DEST["balloonTowerTop"] = "art"


# ---------------------------------------------------------------------- the tower foot: plinth, door, walkway, pad, the town
# v582 (LOOKED AT, PH0 002/024): the tower's foot with pipes and a machine, a blue landing pad on a pole under the balloon, a
# hazy city skyline of tall towers behind, trees and pastel low-rise buildings in front. Ours: the tower's stone plinth with
# a round burrow door, a plank walkway out to a round timber launch pad (iron hoop) on a braced post, and a hillside TOWN of
# timber cottages with teal-slate roofs, chimney smoke and lit windows, moss-green tree crowns; aerial haze to apricot.
FOOT_Y0 = UA_H - UA_FOOT_H            # 3 034 (page y of the foot's top edge)
PAD_X = 285.0                         # under the balloon (B1: the balloon's x = 285)
PAD_R_PT = 66.0


def _fy(page_y):
    """page y -> foot-local world y (1 u = 10 pt)."""
    return -(page_y - FOOT_Y0) / 10.0


def _pad_tex(u, v):
    """The launch pad (lathe: u round, v up the profile): radial planks on the top, an iron hoop band at the rim."""
    k = (u * 22) % 1.0
    idx = np.floor(u * 22).astype(int)
    tone = np.random.default_rng(3).uniform(-0.07, 0.07, 23)[idx]
    wood = stops_interp(v, [(0.0, TIMBER[2]), (0.5, TIMBER[1]), (1.0, TIMBER[0])]) * (1 + tone[..., None])
    seam = np.exp(-(np.minimum(k, 1 - k) / 0.03) ** 2) * smooth(v, 0.55, 0.62)
    wood = wood * (1 - 0.45 * seam[..., None]) + rgb("#5E3718") * 0.45 * seam[..., None]
    hoop = (1 - smooth(v, 0.44, 0.47)) * smooth(v, 0.12, 0.15)
    wood = wood * (1 - hoop[..., None]) + rgb("#51565E") * hoop[..., None]
    ring = np.exp(-((v - 0.80) / 0.012) ** 2)
    wood = wood * (1 - 0.35 * ring[..., None]) + rgb("#5E3718") * 0.35 * ring[..., None]
    return np.clip(wood, 0, 1)


def ua_foot_model():
    parts = []
    G = _fy(UA_GROUND)                  # -45
    cx = PAD_X / 10
    r = PAD_R_PT / 10
    pad = lathe_part("pad", _replace(satin("pad_wood", TIMBER[1], rough=0.6), texture=_pad_tex, texture_size=512),
                     [(0.0, -0.95), (r - 0.2, -0.95), (r, -0.75), (r + 0.05, -0.2), (r - 0.1, 0.0), (0.0, 0.0)], n_seg=176, samples=90,
                     center=(0, 0, 0))
    tilt = rot_x(24)
    parts.append(("pad", pad))
    post = cylinder(0.78, 12.5, center=(0, -13.4, -0.3))
    parts.append(("post", Part("post", post, satin("post_wood", TIMBER[2], rough=0.6), voxel=0.04)))
    bands = union(*[cylinder(0.84, 0.14, round=0.05, center=(0, yy, -0.3)) for yy in (-3.2, -7.8, -14.0)])
    parts.append(("postBands", Part("postBands", bands, gloss("iron", IRON, rough=0.42, ior=1.45), voxel=0.02)))
    braces = union(*[capsule((sx * 0.5, -4.6, -0.3), (sx * 4.3, -1.05, -0.3), 0.26) for sx in (-1, 1)])
    parts.append(("padBraces", Part("padBraces", braces, satin("brace_wood", TIMBER[2], rough=0.6), voxel=0.025)))
    placed = []
    for name, p in parts:
        placed.append((name, p))
    # everything above is built round the pad's top centre (0, 0, 0): tilt the disc toward the camera, move to (cx, G)
    out = []
    for name, p in placed:
        if name == "pad":
            p.__dict__["premesh_xf"] = (tilt, (cx, G, 0.0))
        out.append(p)
    # walkway from the tower door to the pad: planks across, a front rope rail on stubby posts
    x0, x1 = 9.6, cx - r + 0.4
    planks = []
    n = int((x1 - x0) / 0.62)
    rng = np.random.default_rng(8)
    for i in range(n):
        px_ = x0 + (i + 0.5) * (x1 - x0) / n
        planks.append(rbox(0.52, 0.28, 2.6, 0.06, center=(px_, G - 0.14 - rng.uniform(0, 0.05), -0.6)))
    out.append(Part("walkPlanks", union(*planks), satin("walk_wood", TIMBER[1], rough=0.6), voxel=0.02))
    out.append(Part("walkBeams", union(rbox(x1 - x0, 0.36, 0.3, 0.06, center=((x0 + x1) / 2, G - 0.45, 0.62)),
                                       rbox(x1 - x0, 0.36, 0.3, 0.06, center=((x0 + x1) / 2, G - 0.45, -1.8))),
                    satin("walk_beam", TIMBER[2], rough=0.6), voxel=0.02))
    wposts = [capsule((xx, G - 6.0, 0.62), (xx, G + 1.5, 0.62), 0.2) for xx in np.linspace(x0 + 0.6, x1 - 0.6, 4)]
    out.append(Part("walkPosts", union(*wposts), satin("walk_post", TIMBER[2], rough=0.6), voxel=0.02))
    rope = []
    xs = np.linspace(x0 + 0.6, x1 - 0.6, 4)
    for a, b in zip(xs[:-1], xs[1:]):
        pts = [(a + (b - a) * t, G + 1.2 - 0.45 * math.sin(math.pi * t), 0.62) for t in np.linspace(0, 1, 9)]
        rope.append(path_tube(pts, [0.07] * 9))
    out.append(Part("walkRope", union(*rope), satin("walk_rope", "#B58A55", rough=0.75), voxel=0.012))
    # the burrow door at the tower's foot (the ledge door's shapes, bigger)
    arch2 = rounded_polygon2([(-2.9, 0.0), (2.9, 0.0), (2.9, 5.2), (2.0, 7.4), (0.0, 8.3), (-2.0, 7.4), (-2.9, 5.2)], 0.5, n_arc=6)
    door2 = rounded_polygon2([(-2.2, 0.0), (2.2, 0.0), (2.2, 5.0), (1.5, 6.7), (0.0, 7.4), (-1.5, 6.7), (-2.2, 5.0)], 0.45, n_arc=6)
    dx, dy = 7.0, G
    out.append(Part("footArch", extrude(arch2, 0.5, round=0.3).subtract(extrude(door2, 1.2)).translate(dx, dy, -0.2),
                    satin("arch_stone", ROCK[1], rough=0.7), voxel=0.025))
    boards = []
    for k in range(5):
        bx0 = -2.2 + k * 0.88
        boards.append(extrude(_intersect2(door2, rect2(0.41, 5.0).translate(bx0 + 0.44, 3.7)), 0.14, round=0.05))
    out.append(Part("footDoor", union(*boards).translate(dx, dy, 0.0), satin("door_teal", "#1F8C80", rough=0.5), voxel=0.015))
    out.append(Part("footStraps", union(*[extrude(rect2(2.2, 0.16).translate(0, yy), 0.06, round=0.03) for yy in (1.4, 4.6)]).translate(dx, dy, 0.17),
                    gloss("iron", IRON, rough=0.42, ior=1.45), voxel=0.012))
    out.append(Part("footKnob", sphere(0.26, center=(dx + 1.4, dy + 3.1, 0.3)), gloss("brass", BRASS, rough=0.25, ior=1.5), voxel=0.01))
    out.append(Part("footPort", torus(0.78, 0.17).rotate_x(90).translate(dx, dy + 5.6, 0.25), gloss("brass", BRASS, rough=0.25, ior=1.5), voxel=0.012))
    out.append(Part("footPortGlass", cylinder(0.7, 0.05).rotate_x(90).translate(dx, dy + 5.6, 0.2),
                    _replace(gloss("port_glass", "#FFD27A", rough=0.15, ior=1.4), emissive="#E8A23A"), voxel=0.012))
    # a hanging lantern on an iron hook beside the door
    out.append(Part("footHook", union(capsule((dx + 3.4, dy + 6.4, 0.2), (dx + 4.6, dy + 6.4, 0.2), 0.08),
                                      capsule((dx + 4.6, dy + 6.4, 0.2), (dx + 4.6, dy + 5.9, 0.2), 0.06)),
                    gloss("iron", IRON, rough=0.42, ior=1.45), voxel=0.01))
    lant = rbox(0.62, 0.82, 0.62, 0.1, center=(dx + 4.6, dy + 5.3, 0.2))
    out.append(Part("footLantern", lant.subtract(rbox(0.46, 0.64, 1.0, 0.05, center=(dx + 4.6, dy + 5.3, 0.2))),
                    gloss("brass", BRASS, rough=0.3, ior=1.5), voxel=0.01))
    out.append(Part("footLanternGlow", rbox(0.48, 0.62, 0.48, 0.08, center=(dx + 4.6, dy + 5.3, 0.2)),
                    _replace(satin("lamp_glow", "#FFE3A0", rough=0.3), emissive="#FFC04A"), voxel=0.01))
    return out, 0.03


def _apply_premesh_xf(parts):
    """Parts with __dict__['premesh_xf'] = (R, t): wrap their premesh so the (analytic) mesh is rotated + moved."""
    for p in parts:
        xf = p.__dict__.get("premesh_xf")
        pre = p.__dict__.get("premesh")
        if xf is None or pre is None:
            continue
        R, t = np.asarray(xf[0], float), np.asarray(xf[1], float)

        def wrapped(pre=pre, R=R, t=t):
            v, f, n, uv = pre()
            return np.asarray(v) @ R.T + t, f, np.asarray(n) @ R.T, uv
        p.__dict__["premesh"] = wrapped
    return parts


def ua_foot_model_placed():
    parts, vox = ua_foot_model()
    # the post / braces / bands are built round the pad's top centre too: move them with the pad (no tilt)
    cx, G = PAD_X / 10, _fy(UA_GROUND)
    out = []
    for p in parts:
        if p.name in ("post", "postBands", "padBraces"):
            out.append(Part(p.name, p.sdf.translate(cx, G, 0.0), p.material, voxel=p.voxel))
        else:
            out.append(p)
    return _apply_premesh_xf(out), vox


MODELS["ua_foot"] = ua_foot_model_placed


def paint_plinth(cv, y_off, top_y, bot_y, x1=112.0):
    """The tower's wider stone plinth (big blocks, darker), from page y top_y to bot_y, flush with the masonry's centre."""
    X, Y = cv.X, cv.Y + y_off
    R = TW_R + 8.0
    edge = TW_CX + R
    rows = (Y >= top_y) & (Y < bot_y)
    body = aa(X - edge, 0.5) * rows
    nx = np.clip((X - TW_CX) / R, -1, 1)
    nz = np.sqrt(np.clip(1 - nx ** 2, 0, 1))
    s = R * np.arcsin(nx)
    ch = 26.0
    row = np.floor((Y - top_y) / ch).astype(int)
    stag = np.where(row % 2 == 0, 0.0, 26.0)
    cidx = np.floor((s + stag + 400) / 52.0).astype(int)
    tint = np.random.default_rng(31).uniform(0, 1, (40, 64))[np.clip(row, 0, 39), cidx % 64]
    pal = np.array([rgb(c) for c in ("#4E7F86", "#57878C", "#467378", "#5E8C90")])
    base = pal[np.clip((tint * 4).astype(int), 0, 3)]
    gn = noise2(cv.h, cv.w, 22, seed=17, octaves=3)
    base = base * (1 + 0.07 * gn[..., None])
    L = np.array([-0.45, 0.35, 0.82]); L = L / np.linalg.norm(L)
    dif = np.clip(nx * L[0] + nz * L[2], 0, 1)
    col = base * (0.55 + 0.5 * dif)[..., None]
    fr = (Y - top_y) - row * ch
    dj = np.minimum(fr, ch - fr)
    ds = np.abs(((s + stag + 400) % 52.0) - 26.0)
    mortar = np.maximum(aa(dj - 1.1, 0.5), aa((26.0 - ds) * nz - 1.0, 0.5))
    col = col * (1 - 0.7 * mortar[..., None]) + rgb("#16323A") * 0.7 * mortar[..., None]
    col = col + (rgb("#CDEDE7") - col) * (0.18 * np.clip(1 - np.abs(fr - 2.4) / 1.4, 0, 1) * (1 - mortar))[..., None]
    rim = np.clip((X - (edge - 9)) / 9, 0, 1) ** 2
    col = col + (rgb("#A8F0E0") - col) * (0.25 * rim)[..., None]
    src = np.zeros((cv.h, cv.w, 4)); src[..., :3] = np.clip(col, 0, 1); src[..., 3] = body
    cv.over(src)
    # the plinth's cap: a timber beam with a lit top edge
    cap = aa(np.abs(Y - top_y) - 3.2, 0.4) * aa(X - (edge + 2), 0.5)
    cv.fill(cap, stops_interp(X, [(0, TIMBER[2]), (60, TIMBER[1]), (edge, TIMBER[3])]))
    cv.screen(aa(np.abs(Y - (top_y - 2.4)) - 0.6, 0.4) * aa(X - (edge + 2), 0.5), "#FFE7B8", 0.4)


UA_TOWN_MID = [("cottage1", 128, 16, 1.10, -28), ("cottage3", 238, 10, 1.00, -22), ("cottage0", 338, 20, 1.25, -30),
               ("cottage2", 186, 28, 0.95, -25), ("tree0", 104, 30, 0.95, 0), ("tree2", 212, 36, 1.0, 0), ("tree1", 298, 40, 1.05, 0),
               ("tree0", 380, 36, 1.15, 0)]
UA_TOWN_NEAR = [("tree1", 128, 84, 1.25, 0), ("tree0", 258, 92, 1.35, 0), ("tree2", 344, 86, 1.2, 0), ("tree1", 394, 96, 1.3, 0),
                ("cottage2", 152, 164, 1.55, -25), ("cottage0", 318, 188, 1.7, -30), ("cottage3", 214, 228, 1.5, -20),
                ("tree1", 116, 252, 1.6, 0), ("tree0", 266, 262, 1.7, 0), ("tree2", 382, 254, 1.6, 0)]


def _town(items, z0, dz):
    out = []
    for k, (m, x, g, sc, yaw) in enumerate(items):
        out.append((_M, m, dict(center=False, pos=(x / 10, _fy(UA_GROUND + g), z0 + dz * k), R=(rot_x(16) @ rot_y(yaw)).tolist(),
                                scale=sc)))
    return out


def build_tower_foot(ctx):
    W, H = 393.0, UA_FOOT_H
    y0 = FOOT_Y0
    G = UA_GROUND
    cv = Canvas(W, H)
    X, Y = cv.X, cv.Y + y0
    bounds = ((0.0, -H / 10, -14.0), (W / 10, 0.0, 8.0))
    light = sky_rig(key_lux=2300.0, fill_lux=720.0, key_dir=(0.5, -0.55, -0.65))
    specs = {"uaTownMid": dict(scene=_town(UA_TOWN_MID, -10.0, 0.05), bounds=bounds, aspect=W / H, margin=1.0, fov=6.0, px=2200,
                               light=light),
             "uaFoot": dict(scene=[(_M, "ua_foot", dict(center=False))] + _town(UA_TOWN_NEAR, 1.0, 0.35), bounds=bounds,
                            aspect=W / H, margin=1.0, fov=6.0, px=2200, light=light)}
    ims = ctx.render(specs)
    # far hills + a far town (painted silhouettes), hazed into the apricot horizon
    paint_hills(cv, y0, G - 6, 70, "#5E9A7A", 0.62, seed=3, freq=0.021)
    for i, (hx, hg, hw, hh) in enumerate([(128, G - 48, 12, 10), (146, G - 58, 14, 12), (214, G - 64, 13, 11), (246, G - 60, 16, 13),
                                           (318, G - 52, 12, 10), (352, G - 40, 15, 12), (172, G - 44, 10, 8)]):
        paint_house(cv, y0, hx, hg, hw, hh, hh * 0.8, hw * 0.35, k_haze=0.58, seed=i, windows=1, door=False, chimney=(i % 2 == 0))
    paint_hills(cv, y0, G + 30, 44, MOSS[2], 0.30, seed=7, freq=0.017)
    # the mid town (rendered), a light haze
    mid = np.asarray(ims["uaTownMid"].resize((cv.w, cv.h), _Image.LANCZOS)).astype(np.float64) / 255
    mid[..., :3] = mid[..., :3] * 0.78 + rgb("#F6C9A0") * 0.22
    cv.over(mid)
    # the tower + its plinth, the track groove down to the ground
    paint_tower(cv, y0, y_to=G - 60.0, groove_to=G)
    paint_plinth(cv, y0, G - 60.0, UA_H)
    gm = (Y >= G - 60.0) & (Y <= G)
    cv.multiply(aa(np.abs(X - 34.0) - 15.0, 0.4) * gm, "#12292D", 0.62)
    # a cobbled lane winding down between the cottages, contact shadows where the near town stands
    path = [(150, G + 40), (190, G + 90), (170, G + 150), (225, G + 210), (205, G + 260)]
    for (xa, ya), (xb, yb) in zip(path[:-1], path[1:]):
        for t in np.linspace(0, 1, 16):
            px_, py_ = xa + (xb - xa) * t, ya + (yb - ya) * t
            w_ = 7 + (py_ - G) * 0.05
            cv.fill(aa(np.sqrt(((X - px_) / w_) ** 2 + ((Y - py_) / (w_ * 0.5)) ** 2) - 1, 0.08), "#C9A57A", 0.9)
    cn = noise2(cv.h, cv.w, 2, seed=77, octaves=1)
    for (m, x, g, sc, yaw) in UA_TOWN_NEAR:
        rx = (2.2 if m.startswith("cottage") else 1.2) * sc * 10
        d = np.sqrt(((X - x) / rx) ** 2 + ((Y - (G + g + 1)) / (rx * 0.28)) ** 2)
        cv.multiply(np.clip(1 - d, 0, 1) ** 1.5, "#2E3A20", 0.55)
    del cn
    # the near scene: door + lantern, walkway, launch pad + post, the near town and its trees
    im = ims["uaFoot"].resize((cv.w, cv.h), _Image.LANCZOS)
    sh, (ox, oy) = shadow_of(im, 0, 5, 7, 0.28, color="#1E2E22")
    cv.over(sh, x=ox, y=oy)
    cv.over(im)
    cv.screen(np.exp(-(((X - 116) / 22.0) ** 2 + ((Y - (G - 52)) / 18.0) ** 2)) * (cv.a[..., 3] > 0.5), "#FFC46A", 0.22)
    # chimney smoke over the near cottages
    for (m, x, g, sc, yaw) in UA_TOWN_NEAR + UA_TOWN_MID:
        if not m.startswith("cottage"):
            continue
        k = 1.0 if (m, x, g) in [(a[0], a[1], a[2]) for a in UA_TOWN_NEAR] else 0.6
        cx0 = x + 3.2 * sc * 2
        cy0 = G + g - (2.6 + 1.9 * 0.55 + 1.3) * sc * 10
        for j in range(4):
            px_, py_ = cx0 + 2.4 * j * sc + math.sin(j * 1.3) * 1.5, cy0 - (6 + 7.0 * j) * sc
            d = np.sqrt((X - px_) ** 2 + (Y - py_) ** 2) - (2.0 + 1.1 * j) * sc
            cv.fill(aa(d, 1.6) * (0.5 - 0.1 * j) * k, "#F7EBDD")
    return cv.image()


BUILDS["balloonTowerFoot"] = build_tower_foot
DEST["balloonTowerFoot"] = "art"


# ---------------------------------------------------------------------- the town in 3-D: half-timbered cottages + moss trees
def _lut_mat(name, stops, rough=0.6, vert=True):
    """A material whose texture is a 1-D colour ramp along v (u ignored): parts give per-vertex (u, v) through a 'fn' uv."""
    def tex(u, v):
        return np.clip(stops_interp(v, stops), 0, 1)
    return _replace(satin(name, stops[len(stops) // 2][1], rough=rough), texture=tex, texture_size=256)


def cottage_model(w=3.2, h=2.6, d=2.8, roof_h=1.9, seed=0, chimney=True, round_door=False):
    """A half-timbered cottage, its front facing +z: cream plaster walls, dark timber frame, a teal slate roof with an
    overhang + a ridge beam, a stone chimney, warm-lit windows (emissive), a teal door. Base at y = 0, centred on x/z."""
    rng = np.random.default_rng(seed)
    parts = []
    plaster = satin(f"plaster{seed % 3}", ["#F2E2BE", "#EFD9AE", "#F6E8C8"][seed % 3], rough=0.7)
    beam = satin("tbeam", TIMBER[3], rough=0.6)
    parts.append(Part("walls", rbox(w, h, d, 0.05, center=(0, h / 2, 0)), plaster, voxel=0.02))
    fr = []
    for sx in (-w / 2, w / 2):
        for sz in (-d / 2, d / 2):
            fr.append(rbox(0.22, h, 0.22, 0.04, center=(sx, h / 2, sz)))
    for yy in (0.1, h * 0.52, h - 0.08):
        fr.append(rbox(w + 0.1, 0.18, 0.12, 0.03, center=(0, yy, d / 2 + 0.03)))
        fr.append(rbox(0.12, 0.18, d + 0.1, 0.03, center=(w / 2 + 0.03, yy, 0)))
    fr.append(rbox(0.16, h * 0.5, 0.1, 0.03, center=(-w * 0.22, h * 0.76, d / 2 + 0.04)))
    fr.append(rbox(0.1, h * 0.5, 0.16, 0.03, center=(w / 2 + 0.04, h * 0.76, d * 0.1)))
    parts.append(Part("frame", union(*fr), beam, voxel=0.015))
    # roof: a gable prism along z (the gable faces the camera), overhangs, a ridge beam
    tri = polygon2([(-w / 2 - 0.35, 0.0), (w / 2 + 0.35, 0.0), (0.0, roof_h)])
    roof = extrude(tri, d / 2 + 0.3, round=0.06).translate(0, h, 0)
    inner = extrude(polygon2([(-w / 2 + 0.05, -0.2), (w / 2 - 0.05, -0.2), (0.0, roof_h - 0.45)]), d / 2 + 0.6).translate(0, h, 0)
    shell = roof.subtract(inner)
    parts.append(Part("roof", shell, satin("slate", "#2E6E6C", rough=0.55), voxel=0.02))
    gable = extrude(polygon2([(-w / 2 + 0.02, 0.0), (w / 2 - 0.02, 0.0), (0.0, roof_h - 0.4)]), 0.06).translate(0, h, d / 2 - 0.02)
    parts.append(Part("gable", gable, plaster, voxel=0.015))
    parts.append(Part("ridge", rbox(0.22, 0.2, d + 0.7, 0.05, center=(0, h + roof_h - 0.02, 0)), beam, voxel=0.015))
    if chimney:
        cx = w * 0.22
        ch = rbox(0.55, 1.5, 0.55, 0.05, center=(cx, h + roof_h * 0.55 + 0.4, -d * 0.18))
        parts.append(Part("chimney", ch, satin("chim_stone", ROCK[2], rough=0.75), voxel=0.015))
        parts.append(Part("chimCap", rbox(0.7, 0.14, 0.7, 0.04, center=(cx, h + roof_h * 0.55 + 1.18, -d * 0.18)), satin("chim_cap", ROCK[3], rough=0.7), voxel=0.012))
    glow = _replace(satin("win_glow", "#FFD27A", rough=0.35), emissive="#E8A23A")
    wins = []
    for wx in (-w * 0.28, w * 0.28):
        wins.append(rbox(0.5, 0.58, 0.06, 0.04, center=(wx, h * 0.72, d / 2 + 0.03)))
    wins.append(rbox(0.06, 0.58, 0.5, 0.04, center=(w / 2 + 0.03, h * 0.30, -d * 0.2)))
    wins.append(rbox(0.46, 0.46, 0.06, 0.2, center=(0, h + roof_h * 0.35, d / 2 + 0.04)))
    parts.append(Part("windows", union(*wins), glow, voxel=0.012))
    sills = [rbox(0.62, 0.08, 0.14, 0.02, center=(wx, h * 0.72 - 0.34, d / 2 + 0.07)) for wx in (-w * 0.28, w * 0.28)]
    parts.append(Part("sills", union(*sills), beam, voxel=0.012))
    if round_door:
        dr = extrude(circle2(0.5), 0.05).translate(0.0, 0.5, d / 2 + 0.03)
    else:
        dr = union(rbox(0.72, 0.95, 0.06, 0.03, center=(0, 0.47, d / 2 + 0.03)), extrude(circle2(0.36), 0.03).translate(0, 0.94, d / 2 + 0.03))
    parts.append(Part("door", dr, satin("door_teal", "#1F8C80", rough=0.5), voxel=0.012))
    return parts, 0.02


def tree_model(r=1.3, seed=0, trunk=1.0):
    """A moss-green tree: a lumpy crown of leaf clumps (spheres on a core), a short timber trunk; per-vertex shade through a
    'fn' uv ramp (clump height + a hashed tint)."""
    rng = np.random.default_rng(seed)
    clumps = [sphere(r * 0.72, center=(0, trunk + r * 0.9, 0))]
    for k in range(22):
        th, ph = rng.uniform(0, 2 * math.pi), math.acos(rng.uniform(-0.55, 1.0))
        rr = r * rng.uniform(0.34, 0.46)
        cc = (r * 0.62 * math.sin(ph) * math.cos(th), trunk + r * 0.9 + r * 0.58 * math.cos(ph), r * 0.62 * math.sin(ph) * math.sin(th))
        clumps.append(sphere(rr, center=cc))
    crown = clumps[0]
    for c in clumps[1:]:
        crown = crown.smooth_union(c, k=0.08 * r) if hasattr(crown, "smooth_union") else crown.union(c)
    y0, y1 = trunk + r * 0.1, trunk + r * 1.9

    def uvfn(v):
        t = np.clip((v[:, 1] - y0) / (y1 - y0), 0, 1)
        return np.stack([np.zeros(len(v)), t], 1)
    leaf = _lut_mat("leaf", [(0.0, MOSS[3]), (0.35, MOSS[2]), (0.75, MOSS[1]), (1.0, MOSS[0])], rough=0.72)
    parts = [Part("crown", crown, leaf, voxel=0.03 * r, uv=("fn", uvfn))]
    parts.append(Part("trunk", capsule((0, 0, 0), (0, trunk + r * 0.5, 0), 0.16 * r), satin("trunk", TIMBER[3], rough=0.7), voxel=0.02))
    return parts, 0.03


for _i, (_w, _h, _d, _rh, _rd) in enumerate([(3.2, 2.6, 2.8, 1.9, False), (2.6, 2.3, 2.4, 1.6, True), (3.6, 2.9, 3.0, 2.1, False),
                                              (2.8, 2.4, 2.6, 1.7, True)]):
    MODELS[f"cottage{_i}"] = (lambda w=_w, h=_h, d=_d, rh=_rh, rd=_rd, s=_i: cottage_model(w, h, d, rh, seed=s, round_door=rd))
for _i, _r in enumerate([1.3, 1.6, 1.1]):
    MODELS[f"tree{_i}"] = (lambda r=_r, s=_i: tree_model(r, seed=s + 3))


# ---------------------------------------------------------------------- clouds for the Up & Away sky (A4 scatters them)
def _cloud_build(puffs, frame, seed):
    def fn(ctx):
        cv = Canvas(*frame)
        cloud_layer(cv, puffs, top="#FFF6E6", mid="#FBDCC0", bottom="#9CC7C0", rim="#FFFFFF", soft=1.6, seed=seed)
        return cv.image()
    return fn


BUILDS["balloonCloudA"] = _cloud_build([(34, 40, 20), (62, 30, 26), (96, 38, 22), (124, 46, 16), (80, 50, 18), (48, 52, 14)], (150, 70), 1)
BUILDS["balloonCloudB"] = _cloud_build([(26, 34, 16), (50, 26, 20), (76, 32, 15), (60, 40, 12), (36, 42, 11)], (100, 56), 2)
DEST.update({"balloonCloudA": "ui", "balloonCloudB": "ui"})
PAINT_ONLY.update({"balloonCloudA", "balloonCloudB"})


# ====================================================================== the bar tokens: Treasure Climb (hex + arrow), Up & Away
# iconHexArrow (theirs-derived: a purple hexagon, white rim, white up-arrow) -> treasureToken: a BRASS hex nut with rivets, a
# teal enamel face, a tangerine board-arrow (our exit colour) pointing up. eventBadgeBalloon: the same brass/teal plate with
# our patched balloon floating in it (v582: a striped balloon on a gold hexagon); rig = body + balloon (bob +-1 pt / 4.0 s).
def _hex2(r, flat=True, round_=0.18):
    pts = [(r * math.cos(math.radians(a + (0 if flat else 30))), r * math.sin(math.radians(a + (0 if flat else 30)))) for a in range(0, 360, 60)]
    return rounded_polygon2(pts, round_, n_arc=5)


def hex_plate(cx, cy, r=1.9):
    parts = []
    rim = extrude(_hex2(r, round_=0.3), 0.42, round=0.26).subtract(extrude(_hex2(r - 0.46, round_=0.2), 0.6).translate(0, 0, 0.36))
    parts.append(Part("hexRim", rim.translate(cx, cy, 0), gloss("tok_brass", BRASS, rough=0.26, ior=1.5), voxel=0.012))
    parts.append(Part("hexFace", extrude(_hex2(r - 0.44, round_=0.2), 0.16, round=0.1).translate(cx, cy, 0.14),
                      _replace(gloss("tok_enamel", TEAL[1], rough=0.2, ior=1.5), clearcoat=0.6), voxel=0.01))
    riv = [sphere(0.13, center=(cx + (r - 0.22) * math.cos(math.radians(a)), cy + (r - 0.22) * math.sin(math.radians(a)), 0.38))
           for a in range(0, 360, 60)]
    parts.append(Part("hexRivets", union(*riv), gloss("tok_rivet", "#F2D08A", rough=0.25, ior=1.5), voxel=0.008))
    return parts


def arrow2(len_=2.1, w=1.5, shaft=0.62, head=0.95):
    pts = [(-shaft / 2, -len_ / 2), (shaft / 2, -len_ / 2), (shaft / 2, len_ / 2 - head), (w / 2, len_ / 2 - head),
           (0.0, len_ / 2), (-w / 2, len_ / 2 - head), (-shaft / 2, len_ / 2 - head)]
    return rounded_polygon2(pts, 0.14, n_arc=5)


def token_model():
    parts = hex_plate(2.0, -2.0, 1.85)
    parts.append(Part("tokArrow", extrude(arrow2(2.25, 1.62, 0.7, 1.0), 0.22, round=0.15).translate(2.0, -1.98, 0.4),
                      gloss("tok_arrow", TANGERINE[2], rough=0.24, ior=1.45), voxel=0.01))
    return parts, 0.012


def badge_body_model():
    return hex_plate(2.3, -2.45, 2.05), 0.012


def badge_balloon_model():
    env_parts, _ = balloon_envelope6b()      # F3-art (2026-09-29): the hero's patchwork at badge scale (was R8's balloon_envelope)
    s = 0.17
    ey = -2.79
    parts = []
    for p in env_parts:
        if p.__dict__.get("premesh") is not None:
            p.__dict__["premesh_xf"] = (np.eye(3) * s, (2.3, ey, 0.9))
            parts.append(p)
        else:
            parts.append(Part(p.name, p.sdf.scale(s).translate(2.3, ey, 0.9), p.material, voxel=0.006))
    parts = _apply_premesh_xf(parts)
    basket = rbox(0.6, 0.42, 0.46, 0.08, center=(2.3, -3.58, 0.9))
    parts.append(Part("miniBasket", basket, satin("wicker", "#C9A06A", rough=0.75), voxel=0.008))
    parts.append(Part("miniRim", rbox(0.66, 0.1, 0.52, 0.04, center=(2.3, -3.38, 0.9)), satin("wicker_rim", "#8A6236", rough=0.7), voxel=0.006))
    ropes = union(*[capsule((2.3 + sx * 0.27, -3.35, 0.9 + sz * 0.19), (2.3 + sx * 0.17, -2.86, 0.9 + sz * 0.12), 0.025)
                    for sx in (-1, 1) for sz in (-1, 1)])
    parts.append(Part("miniRopes", ropes, satin("rope", "#7E5630", rough=0.7), voxel=0.005))
    return parts, 0.01


MODELS.update({"token": token_model, "badge_body": badge_body_model, "badge_balloon": badge_balloon_model})


def build_token(ctx):
    spec = dict(scene=[(_M, "token", dict(center=False))], bounds=((0.0, -4.0, -1.0), (4.0, 0.0, 1.2)), aspect=1.0, margin=1.0,
                fov=8.0, px=900, light=d1_rig(key_lux=2300.0, fill_lux=760.0))
    im = ctx.render({"treasureToken": spec})["treasureToken"].resize((120, 120), _Image.LANCZOS)
    cv = Canvas(40, 40)
    sh, (ox, oy) = shadow_of(im, 0, 3, 3, 0.35, color="#0A2A2C")
    cv.over(sh, x=ox, y=oy)
    cv.over(im)
    return cv.image()


BADGE_F = (46.0, 46.0)


def badge_layers(ctx):
    b = ((0.0, -4.6, -1.0), (4.6, 0.0, 2.2))
    common = dict(bounds=b, aspect=1.0, margin=1.0, fov=8.0, px=1000, light=d1_rig(key_lux=2300.0, fill_lux=760.0))
    ims = ctx.render({"uaBadgeBody": dict(scene=[(_M, "badge_body", dict(center=False))], **common),
                      "uaBadgeBalloon": dict(scene=[(_M, "badge_balloon", dict(center=False))], **common)})
    W, H = BADGE_F
    out = {}
    for k, name in (("uaBadgeBody", "body"), ("uaBadgeBalloon", "balloon")):
        im = ims[k].resize((int(W * PX), int(H * PX)), _Image.LANCZOS)
        cv = Canvas(W, H)
        if name == "body":
            sh, (ox, oy) = shadow_of(im, 0, 3, 3, 0.35, color="#0A2A2C")
            cv.over(sh, x=ox, y=oy)
        cv.over(im)
        out[name] = cv.image()
    return out


def build_badge(ctx):
    L = badge_layers(ctx)
    cv = Canvas(*BADGE_F)
    cv.over(L["body"])
    cv.over(L["balloon"])
    return cv.image()


BUILDS.update({"treasureToken": build_token, "eventBadgeBalloon": build_badge})
DEST.update({"treasureToken": "ui", "eventBadgeBalloon": "art"})


# ====================================================================== Treasure Climb header (today: clawHeaderArt, 393 x 240)
# Today's composition (scene_events.build_claw, from 023): the claw hanging from the top centre, a heap of prizes across the
# bottom (glass bulbs, hearts, an hourglass, rounded blocks, chunky arrows), the two crew cheering between the back wall and
# the heap, a lit strip + glass-box edges framing it. Ruling 46: the same objects in D1 materials -- a timber-framed prize
# cabinet (brass-capped corner posts instead of cyan glass edges, a timber lintel with a warm lantern strip instead of the white
# light bar), deep-teal felt back wall with amber lantern washes (instead of violet walls with magenta neon), a BRASS claw on a
# copper rod, the prizes in D1 colours (teal-based bulbs, teal/brass hourglass, tangerine / sunflower / teal / mint / cream
# blocks, painted arrow boards), R2's two Diggers (char_digClawPair).
TR_BLOCKS = {"tangerine": TANGERINE[2], "sunflower": SUNFLOWER[1], "teal": TEAL[1], "mint": MINT[3], "cream": "#FFF1D2",
             "red": "#E8483A"}


def claw_d1():
    brass_ = gloss("claw_brass", "#E3B04B", rough=0.24, ior=1.5)
    parts = [Part("clawRod", cylinder(0.32, 2.2, center=(0, 3.4, 0)), gloss("claw_copper", COPPER, rough=0.3, ior=1.45), voxel=0.02),
             Part("clawCap", cylinder(0.9, 0.25, round=0.15, center=(0, 5.3, 0)), brass_, voxel=0.02)]
    hub = cylinder(1.25, 0.7, round=0.3, center=(0, 0.9, 0)).union(cylinder(0.8, 0.5, round=0.2, center=(0, 1.8, 0)))
    parts.append(Part("clawHub", hub, gloss("claw_hub", "#C98E3E", rough=0.26, ior=1.5), voxel=0.02))
    rivs = union(*[sphere(0.14, center=(1.22 * math.cos(math.radians(a)), 0.9, 1.22 * math.sin(math.radians(a)))) for a in range(0, 360, 45)])
    parts.append(Part("clawRivets", rivs, gloss("claw_rivet", "#F2D08A", rough=0.25, ior=1.5), voxel=0.01))
    from scene_kit import path_tube as _pt
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
        prongs.append(_pt(pts, [0.62 - 0.34 * (i / 13) ** 1.5 for i in range(14)]))
    parts.append(Part("clawProngs", union(*prongs), brass_, voxel=0.02))
    return parts, 0.02


def bulb_d1():
    parts = []
    parts.append(Part("bulbGlass", sphere(1.55, center=(0, 1.3, 0)).union(capped_cone(0.6, 0.72, 1.1, center=(0, 0.1, 0)), k=0.3),
                      _replace(gloss("bulb_glass", "#E6FFF6", rough=0.08, ior=1.5), opacity=0.72), voxel=0.025))
    fil = []
    for i in range(5):
        x = -0.6 + 0.3 * i
        fil.append(capsule((x, 1.1, 0.3), (x * 0.6, 0.3, 0.2), 0.07))
        fil.append(capsule((x, 1.1, 0.3), (x + 0.15, 1.5, 0.3), 0.07))
    parts.append(Part("bulbFil", union(*fil), _replace(satin("bulb_fil", "#FFE9A8", rough=0.3), emissive="#C98A2A"), voxel=0.012))
    parts.append(Part("bulbCollar", cylinder(0.8, 0.22, round=0.12, center=(0, -0.55, 0)), gloss("bulb_col", BRASS, rough=0.25), voxel=0.015))
    base = union(*[torus(0.62, 0.16, center=(0, -0.95 - 0.3 * i, 0)) for i in range(4)]).union(cylinder(0.6, 0.6, center=(0, -1.4, 0)))
    parts.append(Part("bulbBase", base, gloss("bulb_base", TEAL[2], rough=0.25), voxel=0.015))
    parts.append(Part("bulbTip", sphere(0.3, center=(0, -2.1, 0)), gloss("bulb_tip", TEAL[2], rough=0.25), voxel=0.012))
    return parts, 0.02


def hourglass_d1():
    parts = []
    cap = gloss("hg_cap", TIMBER[2], rough=0.35)
    parts.append(Part("hgTop", cylinder(1.35, 0.3, round=0.2, center=(0, 2.1, 0)), cap, voxel=0.02))
    parts.append(Part("hgBot", cylinder(1.35, 0.3, round=0.2, center=(0, -2.1, 0)), cap, voxel=0.02))
    posts = union(*[capsule((1.05 * math.cos(math.radians(a)), -1.9, 1.05 * math.sin(math.radians(a))),
                            (1.05 * math.cos(math.radians(a)), 1.9, 1.05 * math.sin(math.radians(a))), 0.12) for a in (30, 150, 270)])
    parts.append(Part("hgPosts", posts, gloss("hg_post", BRASS, rough=0.28, ior=1.5), voxel=0.012))
    glass_ = capped_cone(0.9, 0.2, 0.95, center=(0, 0.9, 0)).union(capped_cone(0.9, 0.95, 0.2, center=(0, -0.9, 0)), k=0.25)
    parts.append(Part("hgGlass", glass_, _replace(gloss("hg_glass", "#E6FFF6", rough=0.08, ior=1.5), opacity=0.5), voxel=0.02))
    sand = capped_cone(0.45, 0.8, 0.12, center=(0, -1.3, 0)).union(capsule((0, -0.2, 0), (0, 0.5, 0), 0.08))
    parts.append(Part("hgSand", sand, satin("hg_sand", MINT[3], rough=0.4), voxel=0.015))
    return parts, 0.02


def heart_d1():
    from uikit import heart2
    body = extrude(heart2(2.6, 2.4), 0.55, round=0.5)
    return [Part("heart", body, gloss("heart_red", "#EE2536", rough=0.2, ior=1.45), voxel=0.02)], 0.02


def block_d1(color):
    return [Part("block", box(1.1, 1.1, 1.1, round=0.44), gloss(f"blk_{color}", TR_BLOCKS[color], rough=0.3, ior=1.42), voxel=0.025)], 0.025


def arrow_block_d1(color):
    s2 = arrow2(3.0, 2.0, 0.9, 1.25)
    body = extrude(s2, 0.36, round=0.26)
    return [Part("arrowBlock", body, gloss(f"arw_{color}", TR_BLOCKS[color], rough=0.28, ior=1.42), voxel=0.02)], 0.02


MODELS.update({"claw_d1": claw_d1, "bulb_d1": bulb_d1, "hourglass_d1": hourglass_d1, "heart_d1": heart_d1})
for _c in TR_BLOCKS:
    MODELS[f"block_d1_{_c}"] = (lambda c=_c: block_d1(c))
    MODELS[f"arrow_d1_{_c}"] = (lambda c=_c: arrow_block_d1(c))


def _prize_heap_d1(seed=31):
    """Today's heap layout (scene_events._prize_heap: the hero prizes at the same spots, blocks + arrows in three depth rows),
    with the D1 models."""
    rng = np.random.default_rng(seed)
    items = []
    items.append((_M, "bulb_d1", dict(center=False, pos=(9.6, -16.8, 2.6), R=(rot_z(-10)).tolist(), scale=1.5)))
    items.append((_M, "bulb_d1", dict(center=False, pos=(30.2, -16.2, 1.8), R=(rot_z(12)).tolist(), scale=1.5)))
    items.append((_M, "heart_d1", dict(center=False, pos=(15.6, -16.4, 1.6), R=(rot_z(-10) @ rot_y(-15)).tolist(), scale=1.75)))
    items.append((_M, "hourglass_d1", dict(center=False, pos=(23.4, -16.2, 1.2), R=(rot_z(-6) @ rot_x(-10)).tolist(), scale=1.45)))
    items.append((_M, "bulb_d1", dict(center=False, pos=(4.2, -22.2, 4.4), R=(rot_z(58) @ rot_x(20)).tolist(), scale=1.35)))
    items.append((_M, "heart_d1", dict(center=False, pos=(38.0, -21.0, 3.6), R=(rot_z(14)).tolist(), scale=1.3)))
    items.append((_M, "heart_d1", dict(center=False, pos=(26.8, -21.6, 4.6), R=(rot_z(-20) @ rot_x(-30)).tolist(), scale=1.2)))
    cols = ["tangerine", "sunflower", "teal", "mint", "cream", "tangerine", "teal", "red"]
    for z, y_top, n in ((-0.8, -14.6, 10), (1.2, -17.6, 10), (3.4, -20.8, 9)):
        for i in range(n):
            x = -1.5 + 42.0 * (i + rng.uniform(0.1, 0.9)) / n
            y = y_top - rng.uniform(0, 2.6) - 1.8 * (abs(x - 19.6) / 19.6) ** 2
            R = rot_y(rng.uniform(-35, 35)) @ rot_x(rng.uniform(-30, 30)) @ rot_z(rng.uniform(-30, 30))
            c = cols[int(rng.integers(0, len(cols)))]
            if rng.uniform() < 0.28:
                items.append((_M, f"arrow_d1_{c}", dict(center=False, pos=(x, y, z), R=(R @ rot_z(rng.uniform(0, 360))).tolist(), scale=0.95)))
            else:
                items.append((_M, f"block_d1_{c}", dict(center=False, pos=(x, y, z), R=R.tolist(), scale=rng.uniform(1.6, 2.0))))
    return items


def _treasure_back(cv):
    X, Y = cv.X, cv.Y
    base = stops_interp(X, [(0, "#0F3438"), (40, "#15474B"), (110, "#1B5559"), (196, "#1E5E62"), (290, "#1B5559"), (350, "#15474B"), (393, "#0F3438")])
    base = base * (1 - 0.25 * np.clip((Y - 60) / 180, 0, 1))[..., None]
    cv.a[..., :3] = base
    cv.a[..., 3] = 1.0
    # felt texture (fine noise) + soft vertical quilting seams on the back wall
    n = noise2(cv.h, cv.w, 4, seed=5, octaves=2)
    cv.a[..., :3] *= (1 + 0.035 * n)[..., None]
    for sx in np.arange(20, 393, 38):
        cv.multiply(aa(np.abs(X - sx) - 0.5, 0.6) * (Y > 22), "#0A2226", 0.35)
    # lantern washes: amber at both sides, a mint crystal glow in the upper middle
    for cx, cy, rx, ry, col, a in ((22, 120, 55, 110, "#FFB24A", 0.42), (372, 110, 50, 100, "#FFB24A", 0.40),
                                   (196, 62, 150, 70, "#6FE0CC", 0.30), (110, 150, 50, 60, "#FFCF6B", 0.16)):
        g = np.exp(-(((X - cx) / rx) ** 2 + ((Y - cy) / ry) ** 2))
        cv.screen(g, col, a)
    # the timber lintel with its warm lantern strip
    lint = aa(Y - 21.0, 0.5)
    cv.fill(lint, stops_interp(Y, [(0, TIMBER[3]), (12, TIMBER[2]), (21, TIMBER[3])]))
    cv.multiply(aa(np.abs(Y - 20.5) - 0.8, 0.5), "#2A170A", 0.7)
    strip = aa(np.abs(Y - 9.5) - 4.5, 0.8) * aa(np.abs(X - 196) - 122, 2.0)
    cv.fill(strip, "#FFF1CF", 1.0)
    glow = np.exp(-((Y - 12) / 14.0) ** 2) * aa(np.abs(X - 196) - 140, 25.0)
    cv.screen(glow, "#FFC46A", 0.55)
    for bx in np.arange(84, 320, 26.0):
        cv.fill(aa(np.sqrt((X - bx) ** 2 + (Y - 9.5) ** 2) - 1.1, 0.35), "#E3B04B")
    # the cabinet's timber corner posts (where today's glass-box edges are) + perspective beams to the front corners
    for (x0, y0, x1, y1, w) in ((64, 22, 64, 150, 5.0), (329, 22, 329, 150, 5.0), (64, 22, 0, 4, 4.0), (329, 22, 393, 4, 4.0)):
        px_, py_ = X - x0, Y - y0
        dx, dy = x1 - x0, y1 - y0
        L2 = dx * dx + dy * dy
        t = np.clip((px_ * dx + py_ * dy) / max(L2, 1e-9), 0, 1)
        d = np.sqrt((px_ - t * dx) ** 2 + (py_ - t * dy) ** 2)
        cv.fill(aa(d - w / 2, 0.5), TIMBER[2])
        cv.screen(aa(d - w / 5, 0.5) * aa(-(X - x0) * (1 if x0 < 200 else -1) + 0.2, 0.5), "#FFE3B0", 0.35)
        cv.multiply(aa(np.abs(d - w / 2) - 0.4, 0.4), "#2A170A", 0.5)
    for bx in (64, 329):
        cv.fill(aa(np.maximum(np.abs(X - bx) - 4.2, np.abs(Y - 26) - 3.2), 0.4), BRASS)


def build_treasure(ctx):
    import os
    cv = Canvas(393, 240)
    _treasure_back(cv)
    pair = os.path.join(K_OUT, "char_digClawPair@3x.png")
    im = _Image.open(pair).convert("RGBA")
    w, h = im.size
    cv.over(im, x=int(200 * 3 - w / 2), y=int(115 * 3 - h / 2))
    bounds = ((0.0, -24.0, -3.0), (39.3, 0.0, 6.0))
    specs = {"trPrizes": dict(scene=_prize_heap_d1(), bounds=bounds, aspect=393 / 240, margin=1.0, fov=6.0, px=2000,
                              light=d1_rig(key_lux=2500.0)),
             "trClaw": dict(scene=[(_M, "claw_d1", dict(center=False, pos=(19.6, -5.8, 0.5), R=rot_y(18).tolist(), scale=1.75))],
                            bounds=bounds, aspect=393 / 240, margin=1.0, fov=6.0, px=2000, light=d1_rig(key_lux=2300.0))}
    ims = ctx.render(specs)
    for k in ("trClaw", "trPrizes"):
        spr = ims[k].resize((cv.w, cv.h), _Image.LANCZOS)
        sh, (ox, oy) = shadow_of(spr, 0, 6, 8, 0.35, color="#06201F")
        cv.over(sh, x=ox, y=oy)
        cv.over(spr)
    return cv.image()


BUILDS["treasureHeader"] = build_treasure
DEST["treasureHeader"] = "art"


# ====================================================================== Hot Streak header (today: workerRacers, 393 x 290)
# Today (char_workerRacers, from meta-045 / 203): a pink tube slide spiralling through a lab, the crew on sleds at three
# depths. Ours (ruling 46: the same "a ride track sweeping from the back to the front, riders at three depths"): R2's three
# Diggers in mine carts (char_digRacers, registered as rendered) on three timber trestle tracks that run back from their carts
# up into a burrow TUNNEL PORTAL in the cavern wall; teal rock strata, pit-prop timbers, hanging lanterns, cyan crystals.
# The lanes are rendered with R2's own camera (char_cast_d1: frame 393 x 210, 50 pt/u, centre (0, 0.62), fov 24, margin
# 1.06) extended 80 pt upward, and posed exactly like the three racers, so each lane continues its cart's rail stub.
ST_F = (393.0, 290.0)
ST_RACERS_Y = 80.0                  # the racers' 393 x 210 frame sits at the header's bottom
ST_POSES = [dict(yaw=50, pitch=14, pos=(-2.30, 0.30, -2.25), scale=0.66), dict(yaw=46, pitch=14, pos=(-0.70, 0.12, -0.80), scale=0.82),
            dict(yaw=42, pitch=14, pos=(1.20, -0.10, 0.80), scale=1.0)]


def _st_view():
    """R2's racer camera (char_cast_d1: frame 393 x 210, view_bounds(scale 50, centre (0, 0.62), zr (-3.2, 2.0), margin 1.0,
    fov 24) rendered by ui3d.render_case with margin 1.06), with the frame grown SYMMETRICALLY to 393 x 370 (+80 pt up and
    down) at the SAME camera position: the same frustum centre, fov widened so that tan(fov/2) grows by 370/210. Rendering
    at this frame and dropping the bottom 80 pt registers every lane with its cart's rail stub. Returns (bounds, fov)."""
    # (the numbers of char_kit.view_bounds + ui3d.scene_job for R2's case, inlined: no char pipeline import needed)
    t = math.tan(math.radians(12.0))
    half_r = (210.0 / 100.0 - t * 2.6 - 0.02) * 1.06 + 0.02          # the racers' scene_job half-height at the near plane
    k = 370.0 / 210.0
    fov = 2 * math.degrees(math.atan(t * k))
    half = half_r * k
    ey = (half - 0.02) / 1.06
    ex = ey * 393.0 / 370.0
    return ((-ex, 0.62 - ey, -3.2), (ex, 0.62 + ey, 2.0)), fov


def lane_model(z0=-9.5, z1=3.2):
    """One track in the racer's local frame (travel along +z): two iron rails on timber sleepers on a plank bed, the bed on
    trestle bents every 2.4 u (legs splayed down into the cavern)."""
    parts = []
    rails = union(*[capsule((sx * 0.80, -0.42, z0), (sx * 0.80, -0.42, z1), 0.04) for sx in (-1, 1)])
    parts.append(Part("rails", rails, gloss("rail_iron", "#5A5F66", rough=0.35, ior=1.45), voxel=0.012))
    zs = np.arange(z1 - 0.15, z0, -0.38)
    sl = [M4(None, (0.0, -0.47, float(z)), 1.0) for z in zs]
    parts.append(instanced_part("sleepers", satin("sleeper", TIMBER[1], rough=0.65), box(0.5, 0.03, 0.06, round=0.015), 0.01, sl))
    bed = rbox(2.3, 0.14, z1 - z0, 0.04, center=(0.0, -0.57, (z0 + z1) / 2))
    parts.append(Part("bed", bed, satin("bed_wood", TIMBER[2], rough=0.65), voxel=0.03))
    parts.append(Part("bedEdge", union(rbox(0.12, 0.22, z1 - z0, 0.03, center=(-1.12, -0.52, (z0 + z1) / 2)),
                                       rbox(0.12, 0.22, z1 - z0, 0.03, center=(1.12, -0.52, (z0 + z1) / 2))),
                      satin("bed_edge", TIMBER[3], rough=0.6), voxel=0.02))
    legs = []
    for z in np.arange(z1 - 1.2, z0 + 1.0, -3.2):
        for sx in (-1, 1):
            legs.append(capsule((sx * 1.0, -0.62, z), (sx * 1.5, -5.5, z), 0.09))
        legs.append(capsule((-1.05, -1.4, z), (1.05, -1.4, z), 0.06))
        legs.append(capsule((-1.2, -2.6, z), (1.2, -1.45, z), 0.05))
    parts.append(Part("trestle", union(*legs), satin("trestle_wood", TIMBER[3], rough=0.7), voxel=0.03))
    return parts, 0.02


MODELS["lane"] = lane_model


def paint_cavern(cv, portal=(78.0, 64.0, 58.0, 50.0)):
    """The cavern behind the tracks: rock strata (teal-grey), warm lantern pools, pit-prop timbers, crystal clusters, the
    tunnel portal (timber frame, a warm glow deep inside) where the tracks come from. portal = (cx, cy, rx, ry) pt."""
    X, Y = cv.X, cv.Y
    base = stops_interp(Y, [(0, "#123A40"), (90, "#1C4E55"), (180, "#24585E"), (290, "#1A454B")])
    cv.a[..., :3] = base
    cv.a[..., 3] = 1.0
    # rock strata: wavy bands, lighter edges, noise
    n = noise2(cv.h, cv.w, 30, seed=8, octaves=4)
    band = np.sin((Y + 9 * np.sin(X / 37.0) + 6 * n) / 11.0)
    cv.a[..., :3] *= (1 + 0.07 * band + 0.06 * n)[..., None]
    cv.screen(np.clip(band - 0.85, 0, 1) * 4 * (0.5 + 0.5 * n), "#8FC5C0", 0.12)
    # warm lantern pools + the daylight-cool rim on the right
    for cx, cy, rx, ry, col, a in ((250, 70, 90, 70, "#FFB24A", 0.30), (360, 150, 60, 80, "#FFC46A", 0.18), (40, 200, 60, 70, "#FFB24A", 0.18)):
        cv.screen(np.exp(-(((X - cx) / rx) ** 2 + ((Y - cy) / ry) ** 2)), col, a)
    # pit-prop timbers: two posts + a cap beam on the right, one post on the far left
    for (x0, x1, y0, y1) in ((300, 311, 0, 290), (372, 384, 0, 290), (292, 393, 34, 46)):
        m = aa(np.maximum(np.maximum(X - x1, x0 - X), np.maximum(Y - y1, y0 - Y)), 0.5)
        horiz = (x1 - x0) > (y1 - y0)
        u = np.clip((Y - y0) / (y1 - y0), 0, 1) if horiz else np.clip((X - x0) / (x1 - x0), 0, 1)
        cv.fill(m, stops_interp(u, [(0, TIMBER[1]), (0.35, TIMBER[2]), (1, TIMBER[3])]))
        g = noise2(cv.h, cv.w, 3, seed=int(x0), octaves=2)
        cv.multiply(m * np.clip(g, 0, 1), "#5E3718", 0.18)
    for bx in (305.5, 378):
        for by in (40.0,):
            cv.fill(aa(np.sqrt((X - bx) ** 2 + (Y - by) ** 2) - 1.4, 0.35), IRON)
    # hanging lanterns (painted glow + a small brass cage)
    for lx, ly in ((250, 58), (345, 80)):
        cv.fill(aa(np.abs(X - lx) - 0.4, 0.3) * (Y < ly - 5), "#2A2A2A", 0.8)
        cv.fill(aa(np.maximum(np.abs(X - lx) - 3.6, np.abs(Y - ly) - 4.8), 0.4), BRASS)
        cv.fill(aa(np.maximum(np.abs(X - lx) - 2.6, np.abs(Y - ly) - 3.6), 0.4), "#FFE9A8")
        cv.screen(np.exp(-(((X - lx) / 22.0) ** 2 + ((Y - ly) / 20.0) ** 2)), "#FFC46A", 0.45)
    # a string of warm bulbs sagging across the cavern roof (the festive "streak" night-ride)
    for (xa, ya, xb, yb, sag, seed_) in ((-10, 26, 403, 14, 22, 1), (150, 70, 403, 52, 14, 2)):
        ts = np.linspace(0, 1, 90)
        xs_ = xa + (xb - xa) * ts
        ys_ = ya + (yb - ya) * ts + sag * np.sin(ts * math.pi)
        for i in range(len(ts) - 1):
            m = (np.abs(X - xs_[i]) < 6) & (np.abs(Y - ys_[i]) < 6)
            if m.any():
                ax, ay, bx, by = xs_[i], ys_[i], xs_[i + 1], ys_[i + 1]
                dx, dy = bx - ax, by - ay
                t = np.clip(((X - ax) * dx + (Y - ay) * dy) / max(dx * dx + dy * dy, 1e-9), 0, 1)
                d = np.sqrt((X - ax - t * dx) ** 2 + (Y - ay - t * dy) ** 2)
                cv.fill(aa(d - 0.45, 0.3) * m, "#1A1410", 0.85)
        for k, t in enumerate(np.arange(0.04, 1.0, 0.055)):
            bx_, by_ = xa + (xb - xa) * t, ya + (yb - ya) * t + sag * math.sin(t * math.pi) + 3.2
            col = ("#FFD27A", "#FFB24A", "#FFF1CF", "#7FF0E0")[(k + seed_) % 4]
            cv.fill(aa(np.sqrt((X - bx_) ** 2 + ((Y - by_) / 1.25) ** 2) - 2.0, 0.35), col)
            cv.screen(np.exp(-(((X - bx_) / 7.0) ** 2 + ((Y - by_) / 7.0) ** 2)), col, 0.45)
    # crystal clusters (cyan) in the rock
    rng = np.random.default_rng(4)
    for (ccx, ccy, s) in ((24, 120, 1.0), (352, 206, 0.8), (210, 22, 0.7), (150, 150, 0.6)):
        for k in range(5):
            ang = math.radians(rng.uniform(-50, 50))
            L = rng.uniform(8, 16) * s
            w = rng.uniform(2.2, 3.4) * s
            bx, by = ccx + rng.uniform(-5, 5) * s, ccy
            tx, ty = bx + L * math.sin(ang), by - L * math.cos(ang)
            pts = [(bx - w, by), (bx + w, by), (tx + w * 0.3, ty + w * 0.6), (tx, ty), (tx - w * 0.3, ty + w * 0.6)]
            cov = poly_cov(cv, pts)
            cv.fill(cov, "#58D8E0")
            cv.screen(cov * np.clip(1 - np.abs(X - (bx + tx) / 2) / (w * 0.8), 0, 1), "#E6FFFF", 0.5)
        cv.screen(np.exp(-(((X - ccx) / (20 * s)) ** 2 + ((Y - ccy + 8) / (16 * s)) ** 2)), "#7FF0F0", 0.30)
    # the tunnel portal: a dark round mouth with a warm glow deep inside, a heavy timber frame (posts + lintel)
    px_, py_, rx, ry = portal
    d = np.sqrt(((X - px_) / rx) ** 2 + ((Y - py_) / ry) ** 2)
    cut = aa((py_ + ry * 0.45) - Y, 1.5)          # an arch: the mouth + ring stop at the tracks' level (rock below)
    mouth = aa((d - 1.0) * min(rx, ry), 0.6) * cut
    cv.fill(mouth, stops_interp(d, [(0, "#FFC46A"), (0.35, "#A2582A"), (0.7, "#2A1A12"), (1.0, "#0E1A1C")]))
    ring = aa(np.abs(d - 1.06) * min(rx, ry) - 5.0, 0.6) * cut
    cv.fill(ring, stops_interp(np.arctan2(Y - py_, X - px_), [(-3.2, TIMBER[2]), (-1.6, TIMBER[1]), (0, TIMBER[2]), (3.2, TIMBER[3])]))
    for a in np.linspace(-math.pi, 0, 7):
        sx_, sy_ = px_ + rx * 1.06 * math.cos(a), py_ + ry * 1.06 * math.sin(a)
        cv.multiply(aa(np.abs((X - sx_) * math.sin(a) - (Y - sy_) * math.cos(a)) - 0.5, 0.4) * ring, "#3E2410", 0.6)
    cv.screen(np.exp(-(((X - px_) / (rx * 1.4)) ** 2 + ((Y - py_) / (ry * 1.4)) ** 2)) * cut, "#FFB24A", 0.18)


def build_streak(ctx):
    W, H = ST_F
    cv = Canvas(W, H)
    bounds, fov = _st_view()
    specs = {"stLanes": dict(scene=[(_M, "lane", dict(center=False, **p)) for p in ST_POSES], bounds=bounds, aspect=393.0 / 370.0,
                             margin=1.06, fov=fov, px=2400, light=d1_rig(key_lux=2300.0, fill_lux=700.0))}
    ims = ctx.render(specs)
    full = ims["stLanes"].resize((int(393 * PX), int(370 * PX)), _Image.LANCZOS)
    lanes = full.crop((0, 0, cv.w, cv.h))
    # where do the lanes vanish? (their topmost pixels) -> the portal goes there
    a = np.asarray(lanes)[..., 3]
    ys, xs = np.nonzero(a > 30)
    top = ys.min() if len(ys) else 150
    sel = ys < top + 30 * PX
    if sel.any():
        vx, vy = float(xs[sel].mean()) / PX, float(ys[sel].mean()) / PX
        rx = max(46.0, (xs[sel].max() - xs[sel].min()) / PX / 2 + 16.0)
    else:
        vx, vy, rx = 80.0, 60.0, 60.0
    paint_cavern(cv, portal=(vx, vy - 2.0, rx, rx * 0.8))
    sh, (ox, oy) = shadow_of(lanes, 0, 12, 12, 0.35, color="#081E22")
    cv.over(sh, x=ox, y=oy)
    cv.over(lanes)
    rac = _Image.open(_os.path.join(K_OUT, "char_digRacers@3x.png")).convert("RGBA")
    cv.over(rac, x=0, y=int(ST_RACERS_Y * PX))
    im = cv.image()
    im.info["portal"] = (vx, vy)
    return im


BUILDS["streakHeader"] = build_streak
DEST["streakHeader"] = "art"


# ====================================================================== Rocket Rally (today: rocketRaceBackdrop, rocketOfferScene)
# Today (167 / 163): indigo space with sparkles, a small ringed planet and a banded planet, a LILAC cratered moon, a purple
# two-tier rock under a gold / teal-quilted chest heaped with coins + two red hearts; the lanes' deep indigo below. Ruling 46:
# the same objects -- a deep-TEAL night, a copper-banded planet + a mint planet with a tangerine ring, a SANDSTONE moon with
# craters, a teal-grey rock under a TIMBER chest with brass straps (the coins and hearts stay: genre props), the lanes' deep
# teal. The offer popup's field (163) gets the same world + a cream / apricot cloud bank.
import scene_events as SE        # noqa: E402  (read-only: coins, hoard, heart, the chest builder)
import m3d_events as ME          # noqa: E402  (read-only: coin stacks, painted planets)


def rock_d1():
    s1 = rounded_polygon2([(-13.5, -3.2), (12.5, -3.8), (14.2, 1.0), (9.0, 3.6), (-9.5, 3.8), (-14.0, 0.8)], 1.2, n_arc=6)
    s2 = rounded_polygon2([(-9.0, -2.6), (9.5, -2.8), (10.5, 1.0), (6.0, 2.8), (-6.5, 3.0), (-10.0, 0.6)], 1.0, n_arc=6)
    t1 = extrude(s1, 1.2, round=0.8).rotate_x(-90).translate(0, -1.2, 0)
    t2 = extrude(s2, 1.0, round=0.7).rotate_x(-90).translate(0.6, 1.0, -0.8)
    return [Part("rock", t1.smooth_union(t2, k=0.3), satin("rock_d1", "#4E7F86", rough=0.6, ior=1.25), voxel=0.06)], 0.06


def chest_d1_closed():
    return SE.chest(panel="#1F8C80", quilt=(TIMBER[1], TIMBER[1], TIMBER[0]), frame=COPPER, with_coins=False, open_deg=0,
                    straps=True, shield_on=False)


MODELS.update({"rock_d1": rock_d1, "chest_d1_closed": chest_d1_closed})

RALLY_SKY = [(0, "#08262B"), (60, "#0B3036"), (115, "#155158"), (130, "#2A6E70"), (330, "#0E3A40"), (500, "#0A2F35"), (852, "#0D3D44")]
LAT_COPPER = [(-1.0, "#F2B27A"), (-0.7, "#D9824A"), (-0.45, "#F6CFA4"), (-0.2, "#C8743C"), (0.05, "#EFB787"), (0.3, "#A95A2A"),
              (0.55, "#E09B62"), (0.8, "#8E4A22"), (1.0, "#B9683A")]
LAT_MINT = [(-1.0, "#DFFBF1"), (-0.6, "#B6F5E2"), (-0.3, "#7FE3C3"), (0.0, "#A9EFDA"), (0.3, "#4CCBA5"), (0.6, "#7FE3C3"),
            (1.0, "#2FA888")]


def _rally_hoard(ctx, name, view=(0, 40), stacks=False):
    scene = [(_M, "rock_d1", dict(center=False)),
             (_M, "chest_d1_closed", dict(center=False, pos=(0.4, 3.3, -1.6), scale=2.15, R=rot_y(-18).tolist())),
             (SE, "rr_hoard", dict(center=False)),
             (SE, "heart", dict(center=False, pos=(-8.0, 5.0, 2.4), R=(rot_z(12) @ rot_y(20)).tolist(), scale=1.6)),
             (SE, "heart", dict(center=False, pos=(7.6, 7.4, 0.8), R=(rot_z(-10) @ rot_y(-20)).tolist(), scale=1.55))]
    if stacks:
        scene = [s for s in scene if not (s[1] == "heart" and s[2]["pos"][0] > 0)] + [(ME, "roStacks", dict(center=False))]
    return ctx.render({name: dict(scene=scene, view=view, fov=16, px=1800, light=d1_rig(key_lux=2400.0))})[name]


def _moon(cv, X, Y, hz, y_end, crater_seed, n=14, y0=125, y1=225):
    gcol = stops_interp(Y, [(hz.min(), "#F2DDB4"), (hz.min() + 22, "#E0C08E"), (hz.min() + 80, "#C99C66"),
                            (hz.min() + 140, "#A77A4E"), (y_end, "#7E5634")])
    ground = (Y > hz) & (Y < y_end)
    cv.a[..., :3] = np.where(ground[..., None], gcol, cv.a[..., :3])
    cv.screen(np.exp(-((Y - hz) / 4.0) ** 2), "#FFE9C4", 0.6)
    rng = np.random.default_rng(crater_seed)
    for i in range(n):
        cx, cy = rng.uniform(0, 393), rng.uniform(y0, y1)
        rx = rng.uniform(8, 26) * (0.6 + (cy - y0) / 140)
        ry = rx * (0.22 + (cy - y0) / 400)
        dd = d_ellipse(X, Y, cx, cy, rx, ry)
        cv.multiply(aa(dd, 0.8) * ground, "#8E6A40", 0.45)
        cv.screen(aa(np.abs(d_ellipse(X, Y, cx, cy - ry * 0.25, rx * 1.05, ry * 1.1)) - 0.9, 0.8) * (Y > cy) * ground, "#FFE6C0", 0.45)


def _ringed_planet(cv, X, Y, cx, cy, r):
    ME._lat_planet(cv, cx, cy, r, LAT_MINT, shade_col="#0E3A40", seed=2, marble=0.3)
    ring = np.abs(np.sqrt(((X - cx) / (r * 2.2)) ** 2 + ((Y - cy - 2) / (r * 0.5)) ** 2) - 1) * r * 0.45
    cv.fill(aa(ring - 0.9, 0.5) * ((Y > cy + 1) | (np.abs(X - cx) > r)), TANGERINE[2], 0.95)


def build_rally(ctx):
    cv = Canvas(393, 852)
    X, Y = cv.X, cv.Y
    cv.a[..., :3] = stops_interp(Y, RALLY_SKY)
    cv.a[..., 3] = 1.0
    ME._stars(cv, 70, 0, 120, 3, big=6, x1=393)
    _ringed_planet(cv, X, Y, 210, 18, 11)
    ME._lat_planet(cv, 296, 50, 30, LAT_COPPER, shade_col="#0E3A40", seed=1.3, marble=0.35)
    hz = 118 + 6 * ((X - 196) / 196) ** 2
    _moon(cv, X, Y, hz, 300, 9)
    lanes = stops_interp(Y, [(300, "#0A2A30"), (370, "#0A262B"), (520, "#0C3339"), (700, "#0F3D44"), (852, "#124A52")])
    cv.a[..., :3] = np.where((Y >= 300)[..., None], lanes, cv.a[..., :3])
    cv.screen(np.exp(-(((Y - 560) / 170.0) ** 2)) * (Y > 300), "#1F6E6A", 0.35)
    ME._stars(cv, 90, 330, 852, 5, big=4, x1=393)
    spr, (x, y) = fit_box(_rally_hoard(ctx, "rallyHoard"), (48, 55, 345, 232), mode="contain", align=(0.5, 1.0))
    sh, (ox, oy) = shadow_of(spr, 3, 10, 10, 0.4, color="#06201F")
    cv.over(sh, x=x + ox, y=y + oy)
    cv.over(spr, x=x, y=y)
    return cv.image()


RO_F = ME.RO_FRAME


def build_rally_offer(ctx):
    F = RO_F
    W, H = F[2] - F[0], F[3] - F[1]
    cv = Canvas(W, H)
    X, Y = cv.X + F[0], cv.Y + F[1]
    cv.a[..., :3] = stops_interp(Y, [(188, "#08262B"), (240, "#0B3036"), (290, "#11464D"), (325, "#1B5C62"), (345, "#3A8A86"), (360, "#3A8A86")])
    cv.a[..., 3] = 1.0
    ME._stars(cv, 55, 0, 160, 5, big=5, x1=W)
    # (planet painted in frame coordinates)
    Xl, Yl = cv.X, cv.Y
    ME._lat_planet(cv, 308 - F[0], 242 - F[1], 26.5, LAT_COPPER, shade_col="#0E3A40", seed=1.3, marble=0.35)
    hz = 343 + 5 * ((X - 200) / 170) ** 2
    _moon(cv, X, Y, hz, 700, 12, n=10, y0=345, y1=430)
    hoard = grade(_rally_hoard(ctx, "rallyOfferHoard", view=(0, 15), stacks=True), gain=(1.06, 1.04, 0.96), sat=1.1)
    spr, (x, y) = fit_box(hoard, (44 - F[0], 285 - F[1], 294 - F[0], 455 - F[1]), mode="contain", align=(0.52, 1.0))
    sh, (ox, oy) = shadow_of(spr, 3, 9, 9, 0.35, color="#06201F")
    cv.over(sh, x=x + ox, y=y + oy)
    cv.over(spr, x=x, y=y)
    field = stops_interp(Y, [(440, "#FBEBD6"), (560, "#F7E2C8"), (692, "#EFD6BC")])
    low = (Y > 470)
    cv.a[..., :3] = np.where(low[..., None], field, cv.a[..., :3])
    cv.a[..., 3] = np.where(low, 1.0, cv.a[..., 3])
    rngc = np.random.default_rng(23)
    back = [(4, 470, 30), (44, 462, 22), (292, 470, 30), (330, 452, 30), (368, 460, 28), (262, 482, 22), (80, 478, 18)]
    front = []
    for x0 in np.arange(-20, 400, 34):
        r = rngc.uniform(22, 36)
        front.append((float(x0 + rngc.uniform(-8, 8)), float(500 + rngc.uniform(-10, 8) + r * 0.2), float(r)))
    cloud_layer(cv, [(px - F[0], py - F[1], pr) for px, py, pr in back], top="#FFFBF2", mid="#FBE6CC", bottom="#9CC7C0", soft=1.8)
    cloud_layer(cv, [(px - F[0], py - F[1], pr) for px, py, pr in front], top="#FFFBF2", mid="#FCE8D0", bottom="#A8CFC6", soft=2.2)
    low_puffs = [(-10, 600, 44), (30, 640, 36), (380, 600, 46), (350, 650, 36), (200, 700, 60), (100, 690, 40), (300, 700, 44)]
    cloud_layer(cv, [(px - F[0], py - F[1], pr) for px, py, pr in low_puffs], top="#FFF6EA", mid="#F6E0C8", bottom="#B8D6CE",
                soft=3.5, alpha=0.85)
    return cv.image()


BUILDS.update({"rallyBackdrop": build_rally, "rallyOfferScene": build_rally_offer})
DEST.update({"rallyBackdrop": "art", "rallyOfferScene": "art"})


# ====================================================================== Cloud Hop (today: skyJumpBackdrop / Island / IslandFar / IslandFar2 /
#                                                                       Pad / PopupScene, iconSkyDrum)
# Today (069 / 080 / 065 / meta-002): a blue sky over PINK-white cloud banks, clover-shaped islands (cream slab, thick gold
# band, purple base, green felt, a pink pad), lavender chests quilted green / blue / purple heaped with coins, a green PRIZE
# arrow on a green post; pink-cushioned drums (cream rings, gold belt, purple foot). Ruling 46: the same objects in D1 --
# a dawn sky (deep teal -> mint -> apricot) over CREAM / APRICOT cloud banks with cool mint shadows; the islands keep their
# clover plan and layered body but become floating earth: a moss top, a timber-plank rim, a COPPER band, a teal-rock underside
# fading into the clouds; timber chests with brass frames quilted teal / tangerine / sunflower; a carved timber arrow sign with
# a teal painted face; drums with a TANGERINE cushion, cream rings, a brass belt, a teal foot and a teal plate.
HOP_SKY = [(0, "#1E6E78"), (140, "#3C8E92"), (300, "#7DBFB4"), (420, "#BFDFCC"), (560, "#F6D8BC"), (852, "#F8D2B2")]
HOP_CLOUD = ("#FFFBF2", "#FBE3CA", "#B9D8CC")


def island_d1(felt=MOSS[1], band=COPPER, coins=150, seed=5, dense=True):
    parts = []
    top2 = SE.clover2(lobe=5.4, dist=4.9, core=8.2)
    parts.append(Part("islTop", SE._slab(top2, -2.6, 0.0, 0.8), satin("isl_rim", TIMBER[1], rough=0.6), voxel=0.05))
    parts.append(Part("islBand", SE._slab(top2.offset(-0.05), -4.9, -2.4, 0.7), gloss("isl_band", band, rough=0.32, ior=1.42), voxel=0.05))
    parts.append(Part("islBase", SE._slab(top2.offset(-0.5), -8.0, -4.7, 1.0), satin("isl_rock", ROCK[2], rough=0.6), voxel=0.06))
    felt2 = SE.clover2(core=5.8, lobe=3.9, dist=4.6).translate(0, 1.4)
    parts.append(Part("islFelt", SE._slab(felt2, -0.3, 0.06, 0.12), satin("isl_moss", felt, rough=0.75, ior=1.2), voxel=0.04))
    cushion = revolve(rounded_polygon2([(0.0, -0.1), (3.3, -0.1), (3.35, 0.25), (2.9, 0.62), (0.0, 0.75)], 0.12, n_arc=6))
    parts.append(Part("islPad", cushion.translate(0, 0.0, 5.6), gloss("pad_tang", TANGERINE[2], rough=0.3, ior=1.4), voxel=0.03))
    ring = revolve(rounded_polygon2([(3.2, -0.2), (3.7, -0.2), (3.7, 0.3), (3.2, 0.3)], 0.2, n_arc=5))
    parts.append(Part("islPadRing", ring.translate(0, 0.0, 5.6), gloss("isl_brass", BRASS, rough=0.3, ior=1.45), voxel=0.03))
    if coins:
        mats = SE.coin_scatter(seed, (-5.8, 6.4, -3.8, 2.0), coins // 5, coins // 6, lambda x, z: 0.06, s=1.05, max_stack=6)
        parts.append(instanced_part("islCoins", SE.coin_mat(), SE.coin_sdf(), 0.03, mats))
    return parts, 0.05


def sign_d1():
    pts = [(-3.6, 1.0), (1.0, 1.0), (1.0, 2.1), (3.6, 0.0), (1.0, -2.1), (1.0, -1.0), (-3.6, -1.0)]
    outline = polygon2(fillet_points(pts, [0.35, 0.18, 0.25, 0.35, 0.25, 0.18, 0.35], n_arc=6))
    parts = [Part("signFrame", extrude(outline, 0.26, round=0.2), satin("sign_timber", TIMBER[1], rough=0.55), voxel=0.025),
             Part("signFace", extrude(outline.offset(-0.32), 0.1, round=0.06).translate(0, 0, 0.2), satin("sign_teal", "#1F8C80", rough=0.45), voxel=0.025),
             Part("signCoin", cylinder(0.62, 0.09, round=0.06).rotate_x(90).translate(-2.55, 0.0, 0.33).union(
                 cylinder(0.44, 0.05, round=0.03).rotate_x(90).translate(-2.55, 0.0, 0.42)), SE.coin_mat(), voxel=0.015)]
    nails = union(*[sphere(0.12, center=(x, y, 0.3)) for x, y in ((-3.1, 0.6), (-3.1, -0.6), (0.6, 0.6), (0.6, -0.6))])
    parts.append(Part("signNails", nails, gloss("iron", IRON, rough=0.4, ior=1.45), voxel=0.01))
    parts.append(Part("signPost", capsule((-1.4, -1.0, -0.35), (-0.2, -6.2, -0.35), 0.3), satin("sign_post", TIMBER[2], rough=0.6), voxel=0.025))
    return parts, 0.025


def chest_hop(quilt):
    return SE.chest(panel=TIMBER[1], quilt=quilt, frame=BRASS, open_deg=36, shield_on_lid=12)


MODELS.update({
    "island_d1_main": lambda: island_d1(coins=150, seed=5),
    "island_d1_farL": lambda: island_d1(felt=MOSS[2], coins=150, seed=8),
    "island_d1_farR": lambda: island_d1(felt=MOSS[0], band="#D9A441", coins=150, seed=9),
    "chest_hop_teal": lambda: chest_hop((TEAL[1], TEAL[2], TEAL[0])),
    "chest_hop_tang": lambda: chest_hop((TANGERINE[2], TANGERINE[3], TANGERINE[1])),
    "chest_hop_sun": lambda: chest_hop((SUNFLOWER[1], SUNFLOWER[2], SUNFLOWER[0])),
    "sign_d1": sign_d1,
})


def _hop_rig():
    return sky_rig(key_dir=(0.35, -0.75, -0.55), key_lux=2400.0, fill_lux=800.0, rim_lux=900.0)


def _hop_island_scene(kind):
    if kind == "main":
        return [(_M, "island_d1_main", dict(center=False)), (_M, "chest_hop_teal", SE._chest_pose((1.6, 0.05, -2.9))),
                (_M, "sign_d1", SE._sign_pose((-3.6, 0.05, -2.8), s=1.3, roll=15))]
    if kind == "farL":
        return [(_M, "island_d1_farL", dict(center=False)), (_M, "chest_hop_tang", SE._chest_pose((0.4, 0.05, -2.6), s=1.5))]
    return [(_M, "island_d1_farR", dict(center=False)), (_M, "chest_hop_sun", SE._chest_pose((0.6, 0.05, -3.2), s=1.22))]


def _hop_island_build(kind, frame, body_box, pitch=24, haze_k=0.0):
    def fn(ctx):
        ims = ctx.render({f"hop_{kind}": dict(scene=_hop_island_scene(kind), view=(0, pitch), fov=16, px=1700, light=_hop_rig())})
        im = ims[f"hop_{kind}"]
        bb = alpha_bbox(im)
        im = SE._fade_base(im.crop(bb), (bb[3] - bb[1]) * 0.80, (bb[3] - bb[1]) * 1.0)
        cv = Canvas(frame[2] - frame[0], frame[3] - frame[1])
        X, Y = cv.X + frame[0], cv.Y + frame[1]
        bx0, by0, bx1, by1 = body_box
        cxh, cyh = (bx0 + bx1) / 2, by1 - (by1 - by0) * 0.12
        g = np.exp(-(((X - cxh) / ((bx1 - bx0) * 0.42)) ** 2 + ((Y - cyh) / ((by1 - by0) * 0.22)) ** 2) * 1.5)
        fw, fh = frame[2] - frame[0], frame[3] - frame[1]
        ex = np.clip(np.minimum(cv.X, fw - cv.X) / (0.14 * fw), 0, 1)
        ey = np.clip(np.minimum(cv.Y, fh - cv.Y) / (0.14 * fh), 0, 1)
        cv.fill(np.clip(g, 0, 1) * ex * ey, "#8FC7BC", 0.5)
        spr, (x, y) = fit_box(im, (bx0 - frame[0], by0 - frame[1], bx1 - frame[0], by1 - frame[1]), mode="width",
                              align=(0.5, 1.0), crop=False)
        cv.over(spr, x=x, y=y)
        edge = np.clip(np.minimum(np.minimum(cv.X - 0.5, fw - 0.5 - cv.X), np.minimum(cv.Y - 0.5, fh - 0.5 - cv.Y)) / 2.0, 0, 1)
        cv.a[..., 3] *= edge
        if haze_k:
            cv.a[..., :3] = cv.a[..., :3] * (1 - haze_k) + rgb("#D6EAE0") * haze_k
        return cv.image()
    return fn


BUILDS["hopIsland"] = _hop_island_build("main", (66, 306, 326, 562), (88, 312, 310, 556), pitch=13)
BUILDS["hopIslandFar"] = _hop_island_build("farL", (6, 222, 172, 380), (19, 226, 158, 376), pitch=15)
BUILDS["hopIslandFar2"] = _hop_island_build("farR", ME.ISL_FRAME, ME.ISL_BODY, pitch=34, haze_k=0.30)


def hop_drum():
    parts = []
    parts.append(lathe_part("padBase", satin("drum_teal", TEAL[2], rough=0.4),
                            [(0.0, -4.7), (3.5, -4.7), (4.15, -4.35), (4.55, -3.4), (4.7, -2.2), (0.0, -2.2)], n_seg=180, samples=90))
    parts.append(lathe_part("padCreamLo", gloss("drum_cream", "#FFF1D6", rough=0.3, ior=1.4),
                            [(0.0, -2.3), (4.7, -2.3), (5.05, -2.0), (5.12, -1.4), (0.0, -1.4)], n_seg=180, samples=90))
    parts.append(lathe_part("padBrass", gloss("drum_brass", BRASS, rough=0.26, ior=1.5),
                            [(0.0, -1.45), (5.1, -1.45), (5.25, -1.2), (5.27, -0.35), (5.15, -0.1), (0.0, -0.1)], n_seg=180, samples=90))
    parts.append(lathe_part("padCream", gloss("drum_cream", "#FFF1D6", rough=0.3, ior=1.4),
                            [(0.0, -0.15), (5.1, -0.15), (5.45, 0.3), (5.55, 0.85), (5.3, 1.4), (4.7, 1.65), (0.0, 1.65)], n_seg=180, samples=90))
    parts.append(lathe_part("padTop", gloss("drum_tang", TANGERINE[2], rough=0.28, ior=1.42),
                            [(0.0, 1.5), (4.6, 1.5), (4.72, 1.8), (4.25, 2.3), (2.6, 2.6), (0.0, 2.65)], n_seg=180, samples=90))
    rivets = union(*[sphere(0.16, center=(5.28 * math.sin(math.radians(a)), -0.78, 5.28 * math.cos(math.radians(a)))) for a in range(-60, 61, 20)])
    parts.append(Part("belRivets", rivets, gloss("drum_rivet", "#F2D08A", rough=0.25, ior=1.5), voxel=0.012))
    parts.append(Part("plateFrame", rbox(3.5, 3.5, 0.6, 0.62, center=(0, -0.8, 5.35)), gloss("plate_brass", BRASS, rough=0.26, ior=1.5), voxel=0.02))
    parts.append(Part("plateFace", rbox(2.7, 2.7, 0.2, 0.42, center=(0, -0.8, 5.58)), gloss("plate_teal", TEAL[2], rough=0.3, ior=1.4), voxel=0.02))
    return parts, 0.03


MODELS["hop_drum"] = hop_drum


def build_hop_pad(ctx):
    F = (51, 503, 163, 607)
    ims = ctx.render({"hopPad": dict(scene=[(_M, "hop_drum", dict(pitch=22))], fov=14, px=1200, light=_hop_rig())})
    cv = Canvas(F[2] - F[0], F[3] - F[1])
    X, Y = cv.X + F[0], cv.Y + F[1]
    g = np.exp(-(((X - 107.5) / 30) ** 2 + ((Y - 592) / 6.0) ** 2) * 1.3)
    cv.fill(np.clip(g, 0, 1), "#FFE0A0", 0.85)
    spr, (x, y) = fit_box(ims["hopPad"], (58 - F[0], 506 - F[1], 157 - F[0], 591 - F[1]), mode="contain", align=(0.5, 1.0))
    cv.over(spr, x=x, y=y)
    return cv.image()


def build_hop_drum_icon(ctx):
    ims = ctx.render({"hopDrumIcon": dict(scene=[(_M, "hop_drum", dict(pitch=22))], fov=14, px=700, light=_hop_rig())})
    cv = Canvas(57, 52)
    spr, (x, y) = fit_box(ims["hopDrumIcon"], (1.3, 2.4, 55.8, 46.0), mode="contain", align=(0.5, 0.0))
    bot = (y + spr.height) / 3
    g = np.exp(-(((cv.X - 28.5) / 16.5) ** 2 + ((cv.Y - (bot - 0.6)) / 3.0) ** 2) * 1.3)
    cv.fill(np.clip(g * 1.25, 0, 1), "#FFE0A0", 0.9)
    cv.over(spr, x=x, y=y)
    edge = np.clip(np.minimum(np.minimum(cv.X - 0.3, 57 - 0.3 - cv.X), np.minimum(cv.Y - 0.3, 52 - 0.3 - cv.Y)) / 1.2, 0, 1)
    cv.a[..., 3] *= edge
    return cv.image()


def build_hop_sky(ctx):
    cv = Canvas(393, 852)
    X, Y = cv.X, cv.Y
    cv.a[..., :3] = stops_interp(Y, HOP_SKY)
    cv.a[..., 3] = 1.0
    rng = np.random.default_rng(5)
    banks = [(250, 330, 16, 24, 40, ("#F4FBF4", "#D8EDE2", "#A9D2C6")),
             (320, 420, 12, 30, 52, ("#FFFBF2", "#FBE6CF", "#B7D6CA")),
             (420, 560, 10, 36, 64, ("#FFFBF2", "#FADFC4", "#C2D8C8")),
             (540, 700, 8, 44, 78, ("#FFFBF2", "#FBDDC0", "#CFD6C2")),
             (680, 900, 7, 52, 90, ("#FFFBF2", "#FCE0C4", "#D8D2BC"))]
    for y0, y1, n, rmin, rmax, (top, mid, bot) in banks:
        puffs = []
        xs = np.linspace(-40, 433, n) + rng.uniform(-15, 15, n)
        for x in xs:
            r = rng.uniform(rmin, rmax)
            cy = rng.uniform(y0, y1 - r * 0.3)
            puffs.append((float(x), float(cy), float(r)))
            puffs.append((float(x + r * 0.6), float(cy + r * 0.35), float(r * 0.8)))
        cloud_layer(cv, puffs, top=top, mid=mid, bottom=bot, soft=2.5)
    cv.screen(np.exp(-((Y - 330) / 90.0) ** 2), "#EAFBF4", 0.22)
    # a low sun glow behind the far banks (dawn)
    cv.screen(np.exp(-(((X - 290) / 160.0) ** 2 + ((Y - 400) / 110.0) ** 2)), "#FFD9A0", 0.35)
    return cv.image()


def build_hop_offer(ctx):
    F = (30, 270, 360, 460)
    scene = [(SE, "coin_hill_d1", dict(center=False)),
             (_M, "chest_hop_teal_full", SE._chest_pose((3.4, 1.0, -1.8), s=2.3, yaw=-20)),
             (_M, "sign_d1", SE._sign_pose((-6.6, 0.9, -1.2), s=1.75, roll=14))]
    ims = ctx.render({"hopOffer": dict(scene=scene, view=(0, 22), fov=16, px=1800, light=_hop_rig())})
    im = ims["hopOffer"]
    cv = Canvas(F[2] - F[0], F[3] - F[1])
    cloud_layer(cv, [(8, 95, 26), (30, 104, 22), (-2, 118, 24)], top=HOP_CLOUD[0], mid=HOP_CLOUD[1], bottom=HOP_CLOUD[2], soft=2.0)
    cloud_layer(cv, [(322, 92, 24), (300, 104, 20), (334, 116, 24)], top=HOP_CLOUD[0], mid=HOP_CLOUD[1], bottom=HOP_CLOUD[2], soft=2.0)
    glow = np.exp(-(((cv.X - 175) / 150.0) ** 2 + ((cv.Y - 150) / 60.0) ** 2) * 1.2)
    cv.fill(np.clip(glow, 0, 1), "#FFD66A", 0.45)
    spr, (x, y) = fit_box(im, (-80, 5, 410, 196), mode="height", align=(0.5, 1.0))
    cv.over(spr, x=x, y=y)
    edge = np.clip(np.minimum(cv.X - 0.5, (F[2] - F[0]) - 0.5 - cv.X) / 5.0, 0, 1)
    edge = np.minimum(edge, np.clip(((F[3] - F[1]) - 0.5 - cv.Y) / 3.0, 0, 1))
    cv.a[..., 3] *= edge
    return cv.image()


def coin_hill_d1():
    parts = []
    hill = sphere(1.0).scale_xyz(19.0, 2.4, 8.0).translate(0, -1.2, 0)
    hill = hill.intersect(box(20, 5, 10, center=(0, 3.6, 0)))
    parts.append(Part("hill", hill, satin("hill_moss", MOSS[2], rough=0.7, ior=1.2), voxel=0.08))

    def top(x, z):
        v = 1 - (x / 19.0) ** 2 - (z / 8.0) ** 2
        return -1.2 + 2.4 * math.sqrt(max(v, 0.0))
    mats = SE.coin_scatter(21, (-17.5, 17.5, -6.5, 6.5), 170, 230, top, s=0.95, max_stack=6, tilt_loose=40)
    mats += SE.coin_scatter(22, (-4.0, 8.0, -1.5, 5.0), 60, 50, lambda x, z: top(x, z) + 0.4, s=0.95, max_stack=7)
    parts.append(instanced_part("hillCoins", SE.coin_mat(), SE.coin_sdf(), 0.03, mats))
    return parts, 0.06


SE.MODELS["coin_hill_d1"] = coin_hill_d1       # registered on SE so its mesh cache sits beside the original's (read-only use)
MODELS["chest_hop_teal_full"] = lambda: SE.chest(seed=12, panel=TIMBER[1], quilt=(TEAL[1], TEAL[2], TEAL[0]), frame=BRASS, open_deg=36,
                                                 shield_on_lid=12)
BUILDS.update({"hopPad": build_hop_pad, "hopDrum": build_hop_drum_icon, "hopBackdrop": build_hop_sky, "hopOfferScene": build_hop_offer})
DEST.update({"hopIsland": "art", "hopIslandFar": "art", "hopIslandFar2": "art", "hopPad": "art", "hopDrum": "ui",
             "hopBackdrop": "art", "hopOfferScene": "art"})
PAINT_ONLY.add("hopBackdrop")


# ====================================================================== Weekly Cup podium (today: leaderboardPodium, 389 x 206)
# Today (meta-013): three solid glossy blocks, 2nd LILAC-silver / 1st GOLD / 3rd ORANGE, each a thick cap slab over a body with
# a grooved front panel, two rivets and a blank hexagon rank badge on the seam. Ruling 46: the same blocks, places, sizes and
# badge -- in D1 materials: TIMBER-PLANK bodies (horizontal boards, a darker frame round the front panel, iron rivets) under
# rank-METAL caps and hex badges: pewter-mint (2nd), brass (1st), copper (3rd).
PODIUM_D1 = {"silver": dict(cap="#C9DDD8", capd="#8FB0A9", hexc="#DCEEEA", hexrim="#7E9C96", body=TIMBER[2]),
             "gold": dict(cap="#F6C24A", capd="#C98A1E", hexc="#FFD76A", hexrim="#B8801A", body=TIMBER[1]),
             "bronze": dict(cap="#D9824A", capd="#9E5426", hexc="#EFA06A", hexrim="#8E4A22", body=TIMBER[2])}


def _plank_tex(base, dark="#5E3718", n_boards=9, seed=1):
    rng = np.random.default_rng(seed)
    tones = rng.uniform(-0.07, 0.07, n_boards + 1)

    def tex(u, v):
        b = np.clip((v * n_boards).astype(int), 0, n_boards)
        f = (v * n_boards) % 1.0
        col = rgb(base)[None, None] * (1 + tones[b])[..., None]
        grain = 0.025 * np.sin(u * 38 + np.sin(v * 24 + b) * 1.6) + 0.012 * np.sin(u * 97 + b * 3)
        col = col * (1 + grain[..., None])
        seam = np.exp(-(np.minimum(f, 1 - f) / 0.045) ** 2)
        col = col * (1 - 0.5 * seam[..., None]) + rgb(dark) * 0.5 * seam[..., None]
        return np.clip(col, 0, 1)
    return tex


def podium_block_d1(kind):
    c0 = SE.PODIUM[kind]
    c = PODIUM_D1[kind]
    x0, x1 = c0["x"]
    w = (x1 - x0) / 10.0
    cx = (x0 + x1) / 20.0
    top = -c0["top"] / 10.0
    bot = -SE.PODIUM_BOTTOM / 10.0
    d = 6.0
    cap_h = 1.8
    parts = []
    cap = rbox(w, cap_h, d + 0.4, 0.45, center=(cx, top - cap_h / 2, 0))
    parts.append(Part(f"cap_{kind}", cap, gloss(f"pod_cap_{kind}", c["cap"], rough=0.3, ior=1.5), voxel=0.03))
    bw = w - 0.3
    by0, by1 = bot, top - cap_h + 0.2
    body = rbox(bw, by1 - by0, d, 0.25, center=(cx, (by0 + by1) / 2, 0))
    m_body = _replace(satin(f"pod_body_{kind}", c["body"], rough=0.6), texture=_plank_tex(c["body"], seed=len(kind)), texture_size=512)
    uv = ("planar", (cx - bw / 2, by0, 0.0), (1.0 / bw, 0, 0), (0, 1.0 / (by1 - by0), 0), 1.0)
    parts.append(Part(f"body_{kind}", body, m_body, uv=uv, voxel=0.03))
    gx0, gx1 = cx - bw / 2 + 0.75, cx + bw / 2 - 0.75
    gy1, gy0 = top - cap_h - 1.2, bot + 0.2
    ring2 = rect2((gx1 - gx0) / 2, (gy1 - gy0) / 2, round=0.35).subtract(rect2((gx1 - gx0) / 2 - 0.34, (gy1 - gy0) / 2 - 0.34, round=0.25))
    parts.append(Part(f"frame_{kind}", extrude(ring2, 0.14, round=0.06).translate((gx0 + gx1) / 2, (gy0 + gy1) / 2, d / 2 + 0.05),
                      satin(f"pod_frame_{kind}", TIMBER[3], rough=0.6), voxel=0.02))
    for rx in (gx0 + 0.75, gx1 - 0.75):
        parts.append(Part(f"rivet_{kind}{int(rx)}", sphere(0.34, center=(rx, gy1 - 0.75, d / 2 + 0.12)),
                          gloss(f"pod_rivet", IRON, rough=0.35, ior=1.45), voxel=0.012))
    hx = rounded_polygon2([(2.05 * math.cos(math.radians(a)), 1.85 * math.sin(math.radians(a))) for a in range(0, 360, 60)], 0.25, n_arc=4)
    hy = top - cap_h - 0.1
    parts.append(Part(f"hexRim_{kind}", extrude(hx, 0.35, round=0.25).translate(cx, hy, d / 2 + 0.35),
                      gloss(f"pod_hexrim_{kind}", c["hexrim"], rough=0.28, ior=1.5), voxel=0.02))
    parts.append(Part(f"hexFace_{kind}", extrude(hx.offset(-0.3), 0.2, round=0.15).translate(cx, hy, d / 2 + 0.55),
                      gloss(f"pod_hex_{kind}", c["hexc"], rough=0.28, ior=1.5), voxel=0.02))
    # the cap's metal band: a darker lip under the cap (the metal is a sheet over the timber)
    parts.append(Part(f"capLip_{kind}", rbox(w - 0.1, 0.22, d + 0.3, 0.08, center=(cx, top - cap_h + 0.06, 0)),
                      gloss(f"pod_lip_{kind}", c["capd"], rough=0.32, ior=1.5), voxel=0.02))
    return parts, 0.03


for _k in PODIUM_D1:
    MODELS[f"podium_d1_{_k}"] = (lambda k=_k: podium_block_d1(k))


def build_cup_podium(ctx):
    F = (2, 294, 391, 500)
    scene = [(_M, f"podium_d1_{k}", dict(center=False, pos=(0, 0, 0.35 if k == "gold" else 0.0))) for k in ("silver", "gold", "bronze")]
    ims = ctx.render({"cupPodium": dict(scene=scene, view=(0, 7), fov=8, px=1800,
                                        light=d1_rig(key_lux=1900.0, key_dir=(0.3, -0.5, -0.8), fill_lux=700.0))})
    cv = Canvas(F[2] - F[0], F[3] - F[1])
    spr, (x, y) = fit_box(ims["cupPodium"], (5 - F[0], 298 - F[1], 390 - F[0], 500 - F[1]), mode="width", align=(0.5, 0.0))
    cv.over(spr, x=x, y=y)
    cv.a[..., 3] *= np.clip(((F[3] - F[1]) - 0.5 - cv.Y) / 3.5, 0, 1)
    return cv.image()


BUILDS["cupPodium"] = build_cup_podium
DEST["cupPodium"] = "art"


# ====================================================================== Rocket Rally race rockets (today: rocketMine / rocketOther)
# Today (178): the player's rocket is YELLOW with red nose / fins / band and a blue porthole, the others WHITE-BLUE with blue
# trim (the original's own scheme). Ours: the same rocket shape (3d-events_badges.rocket_parts, read-only) in D1 schemes --
# the player's TANGERINE with teal trim and a brass porthole, the others CREAM with teal trim; the same painted exhaust.
import importlib as _il
_RB = _il.import_module("3d-events_badges")
_RB.ROCKET_SCHEMES.setdefault("d1mine", dict(body="#FF8A2A", red="#0B8A83", nozzle="#4B4F55", ring="#E3B04B", glass="#9FF0E0"))
_RB.ROCKET_SCHEMES.setdefault("d1other", dict(body="#F2E6CF", red="#17B3A3", nozzle="#4B4F55", ring="#E3B04B", glass="#9FF0E0"))
MODELS["rally_rocket_mine"] = lambda: (_RB.rocket_parts("d1mine"), _RB.VOXEL)
MODELS["rally_rocket_other"] = lambda: (_RB.rocket_parts("d1other"), _RB.VOXEL)


def _rally_rocket(model):
    def fn(ctx):
        light = d1_rig(key_lux=2600.0, fill_lux=620.0, fill_color=(1.0, 0.85, 0.6), shadow=False)
        im = ctx.render({model: dict(scene=[(_M, model, dict(pitch=4))], fov=14, px=900, light=light)})[model]
        cv = Canvas(68, 98)
        spr, (x, y) = fit_box(im, (2, 2, 66, 76), mode="contain", align=(0.5, 0.0))
        layer = _Image.new("RGBA", (cv.w, cv.h), (0, 0, 0, 0))
        layer.paste(spr, (x, y))
        cv.over(_RB.flame(layer))
        return cv.image()
    return fn


BUILDS.update({"rallyRocketMine": _rally_rocket("rally_rocket_mine"), "rallyRocketOther": _rally_rocket("rally_rocket_other")})
DEST.update({"rallyRocketMine": "ui", "rallyRocketOther": "ui"})


# ====================================================================== LOOK-2 FIX ROUND: the Up & Away hero's envelope
# The copy judge (build/p/LOOK2/J-copy-home, MEASURED): the whole-hero art crop scores SSIM 0.313 >= 0.30 against v582's
# balloon -- R8's two-colour VERTICAL gores echo their purple / yellow vertical stripes ("change the envelope pattern:
# horizontal bands, patchwork or diamond panels"). -> a PATCHWORK of HORIZONTAL bands (the gores stay as thin stitched
# seams, so it still reads as a sewn balloon): a tangerine / cream / sunflower ring pattern with a harlequin DIAMOND band
# round the equator, the teal crown cap + skirt + brass rings as before. Only the hero's envelope (balloonHero) changes;
# the bar badge (eventBadgeBalloon) keeps R8's render. (F3-art, 2026-09-29: the badge now follows -- balloon_envelope6b
# at the end of this file.)
def _envelope_tex6(u, v):
    tang = stops_interp(v, [(0.0, "#E86E14"), (0.5, "#FF8A2A"), (1.0, "#FF9E48")])
    crm = stops_interp(v, [(0.0, "#EAD3AA"), (0.5, "#FFF1D2"), (1.0, "#FFF6E2")])
    sun = stops_interp(v, [(0.0, "#E8A20C"), (0.5, "#FFC52F"), (1.0, "#FFD457")])
    teal = np.array(rgb(TEAL[1]))
    bands = [(0.11, tang), (0.21, crm), (0.33, tang), (0.43, sun), (0.60, None), (0.66, sun), (0.71, crm), (0.76, tang), (0.81, crm),
             (0.86, sun), (0.905, tang)]        # (r2: narrower bands toward the crown: more rings where the page is sky)
    col = np.zeros(np.shape(u) + (3,))
    lo = 0.0
    for hi, c in bands:
        m = ((v >= lo) & (v < hi))[..., None]
        if c is None:          # the harlequin diamond band round the equator: cream / teal diamonds on tangerine
            t = (v - lo) / (hi - lo)
            k = (u * GORES * 1.0) % 1.0
            dd = np.abs(k - 0.5) * 2 + np.abs(t - 0.5) * 2
            dia = dd < 0.92
            alt = (np.floor(u * GORES).astype(int) % 2 == 0)[..., None]
            dc = np.where(alt, crm, teal * np.ones_like(crm))
            c = np.where(dia[..., None], dc, tang)
        col = np.where(m, c, col)
        lo = hi
    # stitched seams between the bands (a darker tape + cream running stitches)
    for vb, _ in bands[:-1]:
        tape = np.exp(-((v - vb) / 0.004) ** 2)
        col = col * (1 - 0.45 * tape[..., None]) + rgb("#8E4A12") * 0.45 * tape[..., None]
        st = np.exp(-((v - vb - 0.007) / 0.0025) ** 2) * (np.sin(u * GORES * 2 * math.pi * 6) > 0.3)
        col = col * (1 - 0.7 * st[..., None]) + rgb("#FFF4DA") * 0.7 * st[..., None]
    # the gore seams: thin, low contrast (the sewn panels, not stripes)
    k = (u * GORES) % 1.0
    seam = np.exp(-(np.minimum(k, 1 - k) / 0.012) ** 2) * (v > 0.11) * (v < 0.905)
    col = col * (1 - 0.22 * seam[..., None]) + rgb("#8E4A12") * 0.22 * seam[..., None]
    crown = smooth(v, 0.905, 0.915)
    col = col * (1 - crown[..., None]) + rgb(TEAL[1]) * crown[..., None]
    ring = np.exp(-((v - 0.905) / 0.006) ** 2)
    col = col * (1 - ring[..., None]) + rgb(BRASS) * ring[..., None]
    skirt = 1 - smooth(v, 0.105, 0.115)
    col = col * (1 - skirt[..., None]) + rgb(TEAL[2]) * skirt[..., None]
    band = np.exp(-((v - 0.118) / 0.005) ** 2)
    col = col * (1 - 0.8 * band[..., None]) + rgb(BRASS) * 0.8 * band[..., None]
    n = _tex_noise(u * 3, v * 3, 90, 7) * 0.035
    col = col * (1 + n[..., None])
    col = col * (0.86 + 0.14 * smooth(v, 0.0, 0.35))[..., None]
    return np.clip(col, 0, 1)


def balloon_envelope6():
    m = _replace(satin("bal_canvas6", "#FF8A2A", rough=0.62, ior=1.18), texture=_envelope_tex6, texture_size=1024)
    parts = [lathe_part("envelope", m, BALLOON_PROFILE, n_seg=GORES * 16, samples=180)]
    parts.append(Part("crownRing", torus(2.02, 0.10, center=(0, 12.62, 0)), gloss("bal_brass", BRASS, rough=0.3, ior=1.45), voxel=0.02))
    parts.append(Part("mouthRing", torus(1.36, 0.12, center=(0, -0.25, 0)), satin("bal_rope", "#B58A55", rough=0.7), voxel=0.02))
    return parts, 0.03


MODELS["balloon_envelope6"] = balloon_envelope6


def _balloon_render(ctx, px=1100, name="balEnv6"):
    ims = ctx.render({name: dict(scene=[(_M, "balloon_envelope6", dict(center=False))], view=(0, 6), fov=14, px=px,
                                 light=sky_rig(key_lux=2300.0, fill_lux=760.0))})
    return ims[name]


# ====================================================================== F3-art (2026-09-29): the Up & Away bar token's envelope
# LOOK-2 carry-over: the bar token (eventBadgeBalloon + art/out/badge_upaway_rig) still wore R8's VERTICAL-stripe envelope
# while balloonHero is the horizontal patchwork. The token now wears the hero's patchwork at badge scale: the same palette,
# the same band order (cream / tangerine / sunflower under the harlequin diamond belt, sunflower / cream / tangerine over
# it), the same diamond belt, teal crown cap + skirt + brass rings; at 46 pt the crown's five 0.05 rings merge into three
# (they read as speckle at 1:1) and the running stitches are dropped (sub-pixel), the band tapes stay. Same camera, frame,
# scale and layers as R8's token (badge_layers), so the rig contract (frame, layer names, rect_pt, the basket pivot, the bob)
# is unchanged. Build: build/p/F3art/badge_build.py (stage) -> land.
def _envelope_tex6b(u, v):
    tang = stops_interp(v, [(0.0, "#E86E14"), (0.5, "#FF8A2A"), (1.0, "#FF9E48")])
    crm = stops_interp(v, [(0.0, "#EAD3AA"), (0.5, "#FFF1D2"), (1.0, "#FFF6E2")])
    sun = stops_interp(v, [(0.0, "#E8A20C"), (0.5, "#FFC52F"), (1.0, "#FFD457")])
    teal = np.array(rgb(TEAL[1]))
    bands = [(0.11, tang), (0.21, crm), (0.33, tang), (0.43, sun), (0.60, None), (0.68, sun), (0.76, crm), (0.84, tang),
             (0.905, crm)]
    col = np.zeros(np.shape(u) + (3,))
    lo = 0.0
    for hi, c in bands:
        m = ((v >= lo) & (v < hi))[..., None]
        if c is None:          # the hero's harlequin belt: cream / teal diamonds on tangerine
            t = (v - lo) / (hi - lo)
            k = (u * GORES) % 1.0
            dd = np.abs(k - 0.5) * 2 + np.abs(t - 0.5) * 2
            dia = dd < 0.92
            alt = (np.floor(u * GORES).astype(int) % 2 == 0)[..., None]
            dc = np.where(alt, crm, teal * np.ones_like(crm))
            c = np.where(dia[..., None], dc, tang)
        col = np.where(m, c, col)
        lo = hi
    for vb, _ in bands[:-1]:   # the band tapes (no running stitches at badge scale)
        tape = np.exp(-((v - vb) / 0.005) ** 2)
        col = col * (1 - 0.40 * tape[..., None]) + rgb("#8E4A12") * 0.40 * tape[..., None]
    crown = smooth(v, 0.905, 0.915)
    col = col * (1 - crown[..., None]) + rgb(TEAL[1]) * crown[..., None]
    ring = np.exp(-((v - 0.905) / 0.006) ** 2)
    col = col * (1 - ring[..., None]) + rgb(BRASS) * ring[..., None]
    skirt = 1 - smooth(v, 0.105, 0.115)
    col = col * (1 - skirt[..., None]) + rgb(TEAL[2]) * skirt[..., None]
    band = np.exp(-((v - 0.118) / 0.005) ** 2)
    col = col * (1 - 0.8 * band[..., None]) + rgb(BRASS) * 0.8 * band[..., None]
    n = _tex_noise(u * 3, v * 3, 90, 7) * 0.035
    col = col * (1 + n[..., None])
    col = col * (0.86 + 0.14 * smooth(v, 0.0, 0.35))[..., None]
    return np.clip(col, 0, 1)


def balloon_envelope6b():
    m = _replace(satin("bal_canvas6b", "#FF8A2A", rough=0.62, ior=1.18), texture=_envelope_tex6b, texture_size=1024)
    parts = [lathe_part("envelope", m, BALLOON_PROFILE, n_seg=GORES * 16, samples=180)]
    parts.append(Part("crownRing", torus(2.02, 0.10, center=(0, 12.62, 0)), gloss("bal_brass", BRASS, rough=0.3, ior=1.45), voxel=0.02))
    parts.append(Part("mouthRing", torus(1.36, 0.12, center=(0, -0.25, 0)), satin("bal_rope", "#B58A55", rough=0.7), voxel=0.02))
    return parts, 0.03


MODELS["balloon_envelope6b"] = balloon_envelope6b
