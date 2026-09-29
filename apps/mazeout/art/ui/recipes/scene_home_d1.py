"""R3 HOME (PLAN-P §4.2, owner item 4 + 15; SPEC rulings 37b / 38 / 46): the D1 "Burrow Works" home scene, restyled with
the SAME composition and object types as today's home (scene_home.py): wall, pipes, vents, valve, ledge, lower wall,
deck rim + railings, wainscot band, skirting band, floor + dais, the boss's station, the machine in the middle with the
live LEVEL plate in its housing. Ruling 46: keep the composition, change materials / colours / details just enough that
the copy gate passes -- never a new theme or layout. What changed, object by object:

    tank wall (smooth lilac metal)        -> deep-teal painted timber planks under a bolted header beam
    pipes (blue / lilac-striped)          -> copper risers with riveted brass collars up both side walls, our own runs
                                             (a gauge stub + a branch into a wall plate on the left; a red valve wheel on
                                             a brass valve body, a junction box and a riveted valve housing on the right)
    round grille vents / signal lamps     -> brass portholes with an iron grille (moved) / caged signal lamps (moved left)
    (new detail)                          -> two brass wall sconces flanking the boss (the warm pools on the planks)
    ledge lip (lilac)                     -> a honey timber beam, iron bolts
    lower wall (navy panels)              -> teal-grey stone masonry
    deck rim + tube railings (blue)       -> a timber deck beam; timber rail posts with a rope rail
    cream wainscot                        -> honey timber planks (horizontal boards, butt joints)
    blue skirting band                    -> a dark stone plinth with a timber cap strip
    lilac floor + glass dais              -> packed earth + a round plank work-pad with an iron rim (homeFloor)
    console (the station)                 -> R2's timber scaffold rail + brass lever (char_bossStation) -> homeScaffold
    capsule machine + arrow HEAP          -> a timber cabinet with a brass bezel (homeCabinet) and, inside, the SIGNPOST:
                                             a carved post with five painted arrow boards, each on its own iron bracket
                                             (home_signpost_rig: base + board1..5, pivots at the brackets). No arrow can
                                             touch another: every board has its own mount (item 4; overlap gate in
                                             art/review/tools/r3_home.py overlap).
    the dispenser ring (cyan glow)        -> a brass lantern hanging from the cabinet's ceiling (warm glow)

The UI rects never move (ui.json frames.home: LEVEL caption/plate, Play frame, pills, Claw bar, nav): the cabinet's
housing keeps the plate recess at (147.5, 536.8, 98.4 x 32.4); the dais keeps the Play frame's place.

Build (one render job at a time on the Mac, >= 1 GB free swap: art/review/tools/r3_home.py queue):
    PY=~/.venvs/mf3d/bin/python
    $PY art/ui/recipes/scene_make.py build homeWorkshop homeCabinet homeFloor homeScaffold homeSignpost
    $PY art/review/tools/r3_home.py signpost     # the centrepiece rig (layers + rig.json) from the same camera
Units: wall objects 1 u = 10 pt at the wall (W(sx, sy, z)), like scene_home.py.
"""
from __future__ import annotations

import json as _json
import math
import os as _os
import sys as _sys

import numpy as np

from scene_kit import (Part, box, capped_cone, capsule, circle2, cylinder, ellipsoid, extrude, gloss, glass, metal,  # noqa: F401
                       path_tube, polygon2, rect2, revolve, round_cone, satin, sphere, spline_profile, torus, union, rbox,
                       rot_x, rot_y, rot_z, SDF, F, rgb, mix)
from scene_kit import (Canvas, aa, blur, d_ellipse, d_rrect, noise2, smooth, stops_interp, grade, shadow_of, fit_box, rig,
                       alpha_bbox, save_png)
from scene_kit import BUILD as _BUILD, OUT as K_OUT, PX
from PIL import Image as _Image

_M = _sys.modules[__name__]

# ====================================================================== palette (D1, art-direction §3.1)
TEAL_PLANK = ("#2B6468", "#23565A", "#1B4448")     # wall planks: face, mid, shade
TIMBER = ("#E7B06A", "#C98A4A", "#9A6130", "#6A3E1C", "#3E2410")   # light .. outline
STONE = ("#56787A", "#466A6C", "#375A5D", "#24413F", "#162C2D")
BRASS = "#D9A441"
COPPER = "#C8743C"
IRON = "#4B4F55"
EARTH = ("#9A6A40", "#855733", "#6C4428")
LANTERN = "#FFCF6B"
WARM = "#FFF1CF"


def ledge_y(x):
    """The header ledge's top edge: 233 at the screen sides, bowing down ~15 pt at the centre (today's curve)."""
    return 233.0 + 15.0 * (1 - ((x - 196.5) / 196.5) ** 2)


def rim_y(x):
    """The deck beam's top edge: 350 at the sides, 362 at the centre (today's curve)."""
    return 350.0 + 12.0 * (1 - ((x - 196.5) / 196.5) ** 2)


WAINSCOT_BOTTOM = 478.0
FLOOR_Y = 575.0


# ====================================================================== the painted structure (homeWorkshop)

def _grain(h, w, sx_px, sy_px, seed):
    """Wood grain: value noise stretched along one axis (sx_px across, sy_px along), in [-1, 1]."""
    rng = np.random.default_rng(seed)
    gh, gw = max(4, h // max(1, sy_px) + 3), max(4, w // max(1, sx_px) + 3)
    g = rng.standard_normal((gh, gw))
    im = _Image.fromarray(((g - g.min()) / (np.ptp(g) + 1e-9) * 255).astype(np.uint8)).resize((gw * sx_px, gh * sy_px),
                                                                                              _Image.BICUBIC)
    a = np.asarray(im).astype(np.float64)[:h, :w] / 127.5 - 1
    return a


def _planks_v(X, Y, x0, x1, seed=1, wmin=24.0, wmax=33.0):
    """Vertical plank edges between x0 and x1 (pt): returns (edges list, plank index map)."""
    rng = np.random.default_rng(seed)
    edges = [x0]
    while edges[-1] < x1:
        edges.append(edges[-1] + rng.uniform(wmin, wmax))
    edges = np.array(edges)
    idx = np.clip(np.searchsorted(edges, X) - 1, 0, len(edges) - 2)
    return edges, idx


def paint_workshop():
    cv = Canvas(393, 852, color=TEAL_PLANK[0])
    X, Y = cv.X, cv.Y
    h, w = cv.h, cv.w
    col = np.zeros((h, w, 3))
    ly = ledge_y(X)
    ry = rim_y(X)
    rb = ry + 11.0

    # ---------------- upper wall: deep-teal vertical planks (painted timber), grain, per-plank tone
    edges, pi = _planks_v(X, Y, -6, 400, seed=7)
    rng = np.random.default_rng(11)
    tone = rng.uniform(-0.06, 0.06, len(edges))[pi]
    base = stops_interp(Y, [(0, TEAL_PLANK[2]), (60, TEAL_PLANK[1]), (160, TEAL_PLANK[0]), (240, TEAL_PLANK[1])])
    gr = _grain(h, w, 4, 90, 3)
    wall = base * (1 + tone[..., None] + 0.05 * gr[..., None])
    col[:] = wall
    # ---------------- ledge band and below: masonry (teal-grey stone blocks)
    below = Y > ly + 10
    stone = stops_interp(X, [(0, STONE[2]), (120, STONE[1]), (200, STONE[1]), (280, STONE[1]), (393, STONE[2])])
    col[below] = stone[below]
    # ---------------- wainscot: honey planks (horizontal)
    wm = (Y > rb) & (Y <= WAINSCOT_BOTTOM)
    ph = 13.2
    WTOP = 361.0                                   # the planks run level; the bowed deck beam covers their top
    prow = np.floor((Y - WTOP) / ph)
    rng2 = np.random.default_rng(5)
    rowtone = rng2.uniform(-0.07, 0.07, 64)
    wtone = rowtone[np.clip(prow.astype(int), 0, 63)]
    wg = _grain(h, w, 70, 3, 9)
    wg2 = _grain(h, w, 180, 2, 19)
    honey = stops_interp(X, [(0, TIMBER[2]), (60, TIMBER[1]), (196, "#D49651"), (330, TIMBER[1]), (393, TIMBER[2])])
    streak = np.clip(wg2 - 0.35, 0, 1) * 0.16
    wain = honey * (1 + wtone[..., None] + 0.06 * wg[..., None] - streak[..., None])
    col[wm] = wain[wm]
    # ---------------- skirting: dark stone plinth
    sm = (Y > WAINSCOT_BOTTOM) & (Y <= FLOOR_Y)
    plinth = stops_interp(X, [(0, STONE[3]), (100, STONE[2]), (196, STONE[2]), (300, STONE[2]), (393, STONE[3])])
    col[sm] = plinth[sm]
    # ---------------- floor: packed earth, lighter where the room light pools in front
    fl = stops_interp(Y, [(575, "#5E3C22"), (600, EARTH[2]), (660, EARTH[1]), (760, EARTH[0]), (852, "#A77446")])
    side = (np.abs(X - 196.5) / 196.5) ** 2
    fl = fl * (1 - 0.18 * side[..., None])
    fm = Y > FLOOR_Y
    col[fm] = fl[fm]
    cv.a[..., :3] = col
    cv.a[..., 3] = 1.0

    # ---------------- details: the plank wall
    up = Y < ly
    for e in edges:
        d = np.abs(X - e)
        cv.multiply(aa(d - 0.8, 0.45) * up, "#0C2426", 0.75)                  # the gap
        cv.screen(aa(np.abs(X - e - 1.6) - 0.45, 0.45) * up, "#8FD2CF", 0.10)  # the next plank's lit edge
        cv.multiply(aa(np.abs(X - e + 1.8) - 0.9, 0.9) * up, "#0C2426", 0.18)  # this plank's shaded edge
    # nail pairs at the header beam and near the ledge
    for e0, e1 in zip(edges[:-1], edges[1:]):
        cx = (e0 + e1) / 2
        for ny in (52.0,):
            for dx in (-5.0, 5.0):
                r = np.sqrt((X - cx - dx) ** 2 + (Y - ny) ** 2)
                cv.multiply(aa(r - 1.5, 0.4), "#0E2224", 0.55)
                cv.screen(aa(np.sqrt((X - cx - dx + 0.4) ** 2 + (Y - ny + 0.4) ** 2) - 0.7, 0.35), "#9CC6C4", 0.35)
    # the header beam (a bolted timber beam across the top)
    hb0, hb1 = 26.0, 42.0
    hbm = (Y > hb0) & (Y <= hb1)
    tb = np.clip((Y - hb0) / (hb1 - hb0), 0, 1)
    beam = stops_interp(tb, [(0, TIMBER[0]), (0.18, TIMBER[1]), (0.75, TIMBER[2]), (1.0, TIMBER[3])])
    beam = beam * (1 + 0.07 * _grain(h, w, 60, 3, 21)[..., None])
    cv.a[..., :3] = np.where(hbm[..., None], beam, cv.a[..., :3])
    cv.multiply(aa(np.abs(Y - hb1) - 0.6, 0.5), TIMBER[4], 0.7)
    cv.multiply(smooth(-(Y - hb1), -10, 0) * (Y > hb1) * up, "#081A1C", 0.45)   # the beam's shadow on the planks
    cv.screen(aa(np.abs(Y - hb0 - 1.2) - 0.5, 0.5), WARM, 0.35)
    for bx in (18, 104, 196.5, 289, 375):
        for by in (31.0, 37.0):
            r = np.sqrt((X - bx) ** 2 + (Y - by) ** 2)
            cv.multiply(aa(np.sqrt((X - bx - 0.5) ** 2 + (Y - by - 0.6) ** 2) - 2.1, 0.5), TIMBER[4], 0.55)
            cv.fill(aa(r - 1.8, 0.4), IRON)
            cv.screen(aa(np.sqrt((X - bx + 0.5) ** 2 + (Y - by + 0.5) ** 2) - 0.8, 0.4), "#C9CED6", 0.45)
    # a mid batten across the planks (a nailed timber strip; the planks' second fixing line)
    mb0, mb1 = 128.0, 135.0
    mbm = (Y > mb0) & (Y <= mb1)
    tm = np.clip((Y - mb0) / (mb1 - mb0), 0, 1)
    bat = stops_interp(tm, [(0, TIMBER[1]), (0.3, TIMBER[2]), (1.0, TIMBER[3])]) * (1 + 0.06 * _grain(h, w, 60, 3, 23)[..., None])
    cv.a[..., :3] = np.where(mbm[..., None], bat, cv.a[..., :3])
    cv.multiply(aa(np.abs(Y - mb1) - 0.5, 0.5), TIMBER[4], 0.6)
    cv.multiply(smooth(-(Y - mb1), -7, 0) * (Y > mb1) * up, "#081A1C", 0.35)
    cv.screen(aa(np.abs(Y - mb0 - 0.9) - 0.4, 0.5), WARM, 0.25)
    for e0, e1 in zip(edges[:-1], edges[1:]):
        cx = (e0 + e1) / 2
        r = np.sqrt((X - cx) ** 2 + (Y - 131.5) ** 2)
        cv.fill(aa(r - 1.3, 0.4), IRON)
        cv.screen(aa(np.sqrt((X - cx + 0.4) ** 2 + (Y - 131.1) ** 2) - 0.5, 0.35), "#C9CED6", 0.4)
    # warm lantern light on the wall (two soft pools, upper left + upper right, where the wall lanterns hang)
    for lx, lyy, rx, ryy, a in ((140, 118, 70, 90, 0.26), (254, 118, 70, 90, 0.26), (196, 150, 190, 170, 0.08)):
        g = np.exp(-(((X - lx) / rx) ** 2 + ((Y - lyy) / ryy) ** 2))
        cv.screen(g * up, LANTERN, a)

    # ---------------- the ledge: a honey timber beam following the curve
    lip = (Y > ly) & (Y <= ly + 10)
    tl = np.clip((Y - ly) / 10.0, 0, 1)
    lipcol = stops_interp(tl, [(0, TIMBER[0]), (0.25, TIMBER[1]), (0.8, TIMBER[2]), (1.0, TIMBER[3])])
    lipcol = lipcol * (1 + 0.06 * _grain(h, w, 60, 3, 31)[..., None])
    cv.a[..., :3] = np.where(lip[..., None], lipcol, cv.a[..., :3])
    cv.multiply(smooth(Y, ly - 14, ly) * (Y <= ly), "#081A1C", 0.35)        # AO on the planks above
    cv.multiply(aa(np.abs(Y - ly) - 0.5, 0.5), TIMBER[4], 0.6)
    cv.screen(aa(np.abs(Y - ly - 1.6) - 0.6, 0.5), WARM, 0.35)
    cv.multiply(aa(np.abs(Y - ly - 10.2) - 0.6, 0.6), TIMBER[4], 0.6)
    for bx in (24, 92, 160, 233, 301, 369):
        by = ledge_y(bx) + 5.0
        r = np.sqrt((X - bx) ** 2 + (Y - by) ** 2)
        cv.fill(aa(r - 1.7, 0.4), IRON)
        cv.screen(aa(np.sqrt((X - bx + 0.5) ** 2 + (Y - by + 0.5) ** 2) - 0.7, 0.4), "#C9CED6", 0.4)

    # ---------------- the stone courses (between the ledge and the deck beam; and the plinth)
    def masonry(mask, y0, course, seed, mortar="#0C1918", lit="#8DB3B2"):
        """Rough-cut stone blocks: level courses, staggered blocks of random width, corners and edges broken by noise
        (chipped), per-block value AND hue drift, a recessed dark mortar, a soft lit top edge / shaded bottom edge,
        pits and speckle (reads as hewn stone, not glossy tiles)."""
        rng3 = np.random.default_rng(seed)
        row = np.floor((Y - y0) / course).astype(int)
        nrow = int(max(row.max(), 0)) + 2
        offs = rng3.uniform(0, 70, nrow + 1)
        widths = rng3.uniform(30, 66, nrow + 1)
        rr_ = np.clip(row, 0, nrow)
        u = (X + offs[rr_]) / widths[rr_]
        blk = np.floor(u)
        lx = (u - blk) * widths[rr_]
        lyy = ((Y - y0) / course - row) * course
        key = (rr_ * 131 + blk.astype(int) * 17) % 97
        h1 = (np.sin(key * 12.9898) * 43758.5453) % 1.0 - 0.5
        h2 = (np.sin(key * 78.233) * 12543.123) % 1.0 - 0.5
        bw = widths[rr_]
        r = 2.2
        nz_e = noise2(h, w, 7, seed=seed + 5)
        qx = np.abs(lx - bw / 2) - (bw / 2 - 1.1 - r)
        qy = np.abs(lyy - course / 2) - (course / 2 - 1.1 - r)
        dbox = np.sqrt(np.maximum(qx, 0) ** 2 + np.maximum(qy, 0) ** 2) + np.minimum(np.maximum(qx, qy), 0) - r
        dbox = dbox + 0.9 * nz_e                               # chipped, uneven edges
        tint = np.stack([1 + 0.10 * h2, 1 + 0.03 * h2, 1 - 0.06 * h2], -1)
        cv.a[..., :3] = np.where(mask[..., None], cv.a[..., :3] * (1 + 0.26 * h1[..., None]) * tint, cv.a[..., :3])
        inside = aa(dbox, 0.55)
        cv.multiply((1 - inside) * mask, mortar, 0.9)
        edge = np.clip(1 + dbox / 2.2, 0, 1) * inside
        up_ = (lyy < course * 0.45)
        cv.screen(edge * mask * up_, lit, 0.16)
        cv.multiply(edge * mask * (~up_), "#0B1A1A", 0.35)
        nz = noise2(h, w, 4, seed=seed) * 0.5 + noise2(h, w, 14, seed=seed + 1) * 0.5
        cv.a[..., :3] = np.where(mask[..., None], cv.a[..., :3] * (1 + 0.10 * nz[..., None]), cv.a[..., :3])
        pits = (noise2(h, w, 2, seed=seed + 9) > 0.62) & mask & (inside > 0.9)
        cv.multiply(pits.astype(float), "#16302F", 0.35)

    lower = (Y > ly + 10) & (Y < ry)
    masonry(lower, 0.0, 21.0, 41)
    cv.multiply(smooth(-(Y - ly - 10), -14, 0) * lower, "#081A1C", 0.45)       # AO under the ledge
    plinth_m = (Y > WAINSCOT_BOTTOM + 6) & (Y <= FLOOR_Y)
    masonry(plinth_m, WAINSCOT_BOTTOM + 6, 24.0, 43, mortar="#0C1C1E", lit="#6F9A9E")

    # ---------------- the deck beam (timber), with its shadow on the wainscot
    rimm = (Y > ry) & (Y <= rb)
    tr = np.clip((Y - ry) / 11.0, 0, 1)
    rimcol = stops_interp(tr, [(0, TIMBER[0]), (0.15, "#DDA15C"), (0.55, TIMBER[1]), (0.9, TIMBER[2]), (1.0, TIMBER[3])])
    rimcol = rimcol * (1 + 0.07 * _grain(h, w, 70, 3, 51)[..., None])
    cv.a[..., :3] = np.where(rimm[..., None], rimcol, cv.a[..., :3])
    cv.multiply(aa(np.abs(Y - ry) - 0.5, 0.5), TIMBER[4], 0.55)
    cv.multiply(aa(np.abs(Y - rb) - 0.6, 0.5), TIMBER[4], 0.7)
    for bx in (14, 70, 126, 267, 323, 379):
        by = rim_y(bx) + 5.5
        r = np.sqrt((X - bx) ** 2 + (Y - by) ** 2)
        cv.fill(aa(r - 1.8, 0.4), IRON)
        cv.screen(aa(np.sqrt((X - bx + 0.5) ** 2 + (Y - by + 0.5) ** 2) - 0.8, 0.4), "#C9CED6", 0.4)

    # ---------------- the wainscot planks: seams, butt joints, shadow under the beam
    fy = (Y - WTOP) / ph
    dseam = (fy - np.floor(fy)) * ph
    cv.multiply(aa(np.minimum(dseam, ph - dseam) - 0.55, 0.45) * wm, TIMBER[4], 0.7)
    cv.screen(aa(np.abs(dseam - 1.3) - 0.45, 0.45) * wm, WARM, 0.18)
    rng4 = np.random.default_rng(13)
    joff = rng4.uniform(0, 120, 64)
    jw = rng4.uniform(110, 170, 64)
    rr = np.clip(prow.astype(int), 0, 63)
    ju = (X + joff[rr]) / jw[rr]
    jd = np.minimum(ju - np.floor(ju), np.ceil(ju) - ju) * jw[rr]
    cv.multiply(aa(jd - 0.6, 0.45) * wm, TIMBER[4], 0.65)
    # nails at the butt joints
    cv.multiply(smooth(-(Y - rb), -12, 0) * wm, "#3A1E0C", 0.45)
    cv.multiply(smooth(Y, WAINSCOT_BOTTOM - 8, WAINSCOT_BOTTOM) * wm, "#3A1E0C", 0.25)

    # ---------------- the plinth's timber cap strip
    cap = (Y > WAINSCOT_BOTTOM) & (Y <= WAINSCOT_BOTTOM + 6)
    tc = np.clip((Y - WAINSCOT_BOTTOM) / 6.0, 0, 1)
    capcol = stops_interp(tc, [(0, TIMBER[0]), (0.4, TIMBER[1]), (1.0, TIMBER[3])])
    cv.a[..., :3] = np.where(cap[..., None], capcol, cv.a[..., :3])
    cv.multiply(aa(np.abs(Y - WAINSCOT_BOTTOM) - 0.5, 0.5), TIMBER[4], 0.7)
    cv.multiply(smooth(-(Y - WAINSCOT_BOTTOM - 6), -10, 0) * plinth_m, "#081416", 0.45)
    cv.multiply(smooth(Y, FLOOR_Y - 12, FLOOR_Y) * plinth_m, "#081416", 0.35)

    # ---------------- the floor: the wall's contact shadow, dig marks, pebbles, plank-pad shadow comes with homeFloor
    cv.multiply(aa(np.abs(Y - FLOOR_Y) - 0.8, 0.6), "#1E1008", 0.6)
    cv.multiply(smooth(-(Y - FLOOR_Y), -22, 0) * fm, "#2A160A", 0.45)
    nz = noise2(h, w, 40, seed=61)
    nz2 = noise2(h, w, 8, seed=62)
    cv.a[..., :3] = np.where(fm[..., None], cv.a[..., :3] * (1 + (0.06 * nz + 0.04 * nz2)[..., None]), cv.a[..., :3])
    rng5 = np.random.default_rng(71)
    for _ in range(46):
        px, py = rng5.uniform(4, 389), rng5.uniform(590, 848)
        rx_, ry_ = rng5.uniform(1.2, 3.2), 0
        ry_ = rx_ * rng5.uniform(0.45, 0.7)
        d = d_ellipse(X, Y, px, py, rx_, ry_)
        cv.multiply(aa(d_ellipse(X, Y, px + 0.6, py + 0.8, rx_, ry_), 0.5) * fm, "#2A160A", 0.35)
        cv.fill(aa(d, 0.4) * fm, rng5.choice(["#B08058", "#9C9A8E", "#8A7560", "#C09A70"]), 0.9)
        cv.screen(aa(d_ellipse(X, Y, px - rx_ * 0.3, py - ry_ * 0.35, rx_ * 0.45, ry_ * 0.4), 0.4) * fm, WARM, 0.35)
    # overall vignette (the room's corners fall off into deep teal-brown)
    vx = ((X - 196.5) / 196.5) ** 2
    vy = ((Y - 380) / 470) ** 2
    cv.multiply(np.clip(vx * 0.5 + vy * 0.25, 0, 1), "#0E2428", 0.22)
    return cv


# ====================================================================== wall objects (3D), restyled in copper / brass

def W(sx, sy, z=0.0):
    return (sx / 10.0, -sy / 10.0, z)


def _open_fillet(pts, r, n=10):
    P = [np.asarray(p, float) for p in pts]
    out = [P[0]]
    for i in range(1, len(P) - 1):
        a, b, c = P[i - 1], P[i], P[i + 1]
        u = (a - b) / np.linalg.norm(a - b)
        w_ = (c - b) / np.linalg.norm(c - b)
        ang = math.acos(float(np.clip(u @ w_, -1, 1)))
        if ang > math.pi - 1e-3:
            out.append(b)
            continue
        t = r / math.tan(ang / 2)
        t = min(t, 0.49 * np.linalg.norm(a - b), 0.49 * np.linalg.norm(c - b))
        p0, p1 = b + u * t, b + w_ * t
        for k in range(n + 1):
            s = k / n
            out.append((1 - s) ** 2 * p0 + 2 * (1 - s) * s * b + s * s * p1)
    out.append(P[-1])
    return out


def tube(pts, r, bend=None):
    pts = _open_fillet(pts, bend if bend is not None else r * 1.6)
    return path_tube(pts, [r] * len(pts))


def copper(name="copper"):
    return metal(name, "#C87842", rough=0.30)


def brass(name="brass"):
    return metal(name, "#D8A544", rough=0.28)


def iron(name="iron"):
    return metal(name, "#5A5F66", rough=0.42)


def collar(name, sx, sy, r_pt, h_pt, z, mat_, axis="y"):
    c = cylinder(r_pt / 10, h_pt / 20, round=min(0.12, h_pt / 50))
    if axis == "x":
        c = c.rotate_z(90)
    return Part(name, c.translate(sx / 10, -sy / 10, z), mat_, voxel=0.025)


def rivet_ring(name, sx, sy, r_pt, z, n=8, axis="y"):
    """Small iron rivets round a brass collar (reads as a riveted band, not a plastic ring)."""
    pts = []
    for k in range(n):
        a = 2 * math.pi * (k + 0.5) / n
        if axis == "y":
            p = (sx / 10 + r_pt / 10 * math.sin(a), -sy / 10, z + r_pt / 10 * math.cos(a))
        else:
            p = (sx / 10, -sy / 10 + r_pt / 10 * math.sin(a), z + r_pt / 10 * math.cos(a))
        if (p[2] - z) > -0.2:
            pts.append(sphere(0.11, center=p))
    return Part(name, union(*pts), iron(f"{name}_iron"), voxel=0.012)


def wallplate(name, sx, sy, r_pt):
    """A round iron wall plate with four bolts where a pipe enters the wall."""
    plate = cylinder(r_pt / 10, 0.12, round=0.1).rotate_x(90).translate(sx / 10, -sy / 10, 0.12)
    bolts = union(*[sphere(0.16, center=(sx / 10 + 0.72 * r_pt / 10 * math.cos(a), -sy / 10 + 0.72 * r_pt / 10 * math.sin(a), 0.25))
                    for a in (math.pi / 4, 3 * math.pi / 4, 5 * math.pi / 4, 7 * math.pi / 4)])
    return [Part(name, plate, iron(f"{name}_pl"), voxel=0.03), Part(name + "B", bolts, brass(f"{name}_b"), voxel=0.015)]


def gauge(name, sx, sy, r_pt, z):
    """A brass pressure gauge facing the viewer: a thick bezel, a cream dial with a red needle and tick ring (painted
    texture), a glass dome."""
    from dataclasses import replace
    r = r_pt / 10
    x, y = sx / 10, -sy / 10
    bezel = torus(r * 0.92, r * 0.16).rotate_x(90).translate(x, y, z + 0.18)
    back = cylinder(r * 0.95, 0.16, round=0.1).rotate_x(90).translate(x, y, z)

    def dial(u, v):
        uu, vv = (u - 0.5) * 2, (v - 0.5) * 2
        rr = np.sqrt(uu * uu + vv * vv)
        ang = np.arctan2(vv, uu)
        col = np.ones(u.shape + (3,)) * rgb("#FFF3DF")
        ticks = (np.abs(((ang + math.pi) / (2 * math.pi) * 12) % 1 - 0.5) > 0.44) & (rr > 0.66) & (rr < 0.82) & (vv > -0.35)
        col[ticks] = rgb("#3E2410")
        red = (rr > 0.62) & (rr < 0.82) & (ang > 0.1) & (ang < 0.75)
        col[red] = rgb("#E2452F")
        # the needle: from the centre toward ~45 deg up-right
        na = 0.65
        px, py = uu * math.cos(na) + vv * math.sin(na), -uu * math.sin(na) + vv * math.cos(na)
        needle = (px > -0.1) & (px < 0.62) & (np.abs(py) < 0.05 * (1 - px * 0.6))
        col[needle] = rgb("#C0281A")
        col[rr < 0.10] = rgb("#3E2410")
        return col
    face = cylinder(r * 0.80, 0.03).rotate_x(90).translate(x, y, z + 0.17)
    fm = replace(satin(f"{name}_dial", "#FFF3DF", rough=0.5), texture=dial, texture_size=256)
    uvp = ("planar", (x - r * 0.8, y - r * 0.8, 0.0), (1.0 / (1.6 * r), 0, 0), (0, 1.0 / (1.6 * r), 0), 1.0)
    return [Part(name + "Back", back, iron(f"{name}_ib"), voxel=0.02), Part(name + "Bezel", bezel, brass(f"{name}_bz"), voxel=0.015),
            Part(name + "Face", face, fm, uv=uvp, voxel=0.012),
            Part(name + "Glass", ellipsoid(r * 0.78, r * 0.78, 0.12).translate(x, y, z + 0.22),
                 glass(f"{name}_gl", "#EAF6F2", opacity=0.25), voxel=0.012)]


def pipes_left():
    """Left wall: a thick copper riser near the edge (brass collars) with a pressure gauge on a stub, and a branch that
    runs across under the badge column into a wall plate left of the station (today's two parallel pipes + flange
    re-routed: same object types, our own arrangement)."""
    parts = []
    z1 = 1.25
    p1 = tube([W(26, -8, z1), W(26, 226, z1), W(26, 236, -0.4)], 1.25, bend=1.3)
    parts.append(Part("p1", p1, copper("cu1"), voxel=0.03))
    for sy in (70, 186):
        parts.append(collar(f"p1col{sy}", 26, sy, 14.4, 8, z1, brass("br1")))
        parts.append(rivet_ring(f"p1riv{sy}", 26, sy, 14.5, z1))
    parts += wallplate("p1fl", 26, 238, 16)
    # the gauge stub (from the riser to the right) + the gauge
    stub = tube([W(26, 128, z1), W(46, 128, z1)], 0.55)
    parts.append(Part("stub", stub, copper("cu1b"), voxel=0.02))
    parts += gauge("gaugeL", 58, 128, 13.0, z1 - 0.1)
    # the branch: out of the riser at y 206, across to x 118, into a wall plate
    z2 = 1.45
    p2 = tube([W(26, 206, z1), W(40, 206, z2), W(112, 206, z2), W(120, 206, -0.3)], 0.85, bend=0.9)
    parts.append(Part("p2", p2, copper("cu2"), voxel=0.025))
    parts.append(collar("p2mid", 78, 206, 10.6, 7, z2, brass("br2"), axis="x"))
    parts.append(rivet_ring("p2midR", 78, 206, 10.7, z2, n=8, axis="x"))
    parts += wallplate("p2fl", 120, 206, 13)
    return parts, 0.03


def pipes_right():
    """Right wall: a copper riser near the edge carrying the brass valve wheel, a short branch up into a brass junction
    box, and a pipe from the right edge into a riveted valve housing at the station's right (today's U-bend + bell
    re-routed)."""
    parts = []
    z3 = 1.35
    p3 = tube([W(367, -8, z3), W(367, 226, z3), W(367, 236, -0.4)], 1.25, bend=1.3)
    parts.append(Part("p3", p3, copper("cu3"), voxel=0.03))
    for sy in (58, 128):
        parts.append(collar(f"p3col{sy}", 367, sy, 14.4, 8, z3, brass("br3")))
        parts.append(rivet_ring(f"p3riv{sy}", 367, sy, 14.5, z3))
    parts += wallplate("p3fl", 367, 238, 16)
    # the valve wheel on the riser (a stem out of a brass valve body), below the ladder bar's band (y 107..151)
    vx, vy, vz = 367, 184, 3.0
    body = cylinder(1.65, 1.1, round=0.35).translate(vx / 10, -vy / 10, z3)
    parts.append(Part("valveBody", body, brass("brvb"), voxel=0.025))
    wheel = torus(1.75, 0.30).rotate_x(90)
    for a in (90, 210, 330):
        ca, sa = math.cos(math.radians(a)), math.sin(math.radians(a))
        wheel = wheel.union(capsule((0, 0, 0), (1.75 * ca, 1.75 * sa, 0), 0.22))
    wheel = wheel.union(cylinder(0.5, 0.28, round=0.18).rotate_x(90))
    parts.append(Part("valve", wheel.translate(vx / 10, -vy / 10, vz), metal("valve_red", "#D8452E", rough=0.3), voxel=0.025))
    parts.append(Part("valveStem", cylinder(0.26, 0.8).rotate_x(90).translate(vx / 10, -vy / 10, vz - 0.8), iron("irv"), voxel=0.03))
    # from the right edge at y 302 into a riveted valve housing (today's bell + flange)
    z5 = 1.5
    p5 = tube([W(405, 302, z5), W(356, 302, z5)], 1.3)
    parts.append(Part("p5", p5, copper("cu5"), voxel=0.03))
    parts.append(collar("p5col", 380, 302, 15.4, 8, z5, brass("br5"), axis="x"))
    parts.append(rivet_ring("p5riv", 380, 302, 15.5, z5, axis="x"))
    hous = rbox(1.35, 1.55, 0.9, 0.35, center=W(343, 302, 1.2))
    parts.append(Part("p5box", hous, iron("ir5"), voxel=0.02))
    parts.append(Part("p5boxBolts", union(*[sphere(0.15, center=W(343 + dx, 302 + dy, 2.12)) for dx in (-9, 9) for dy in (-11, 11)]),
                      brass("br5b"), voxel=0.012))
    return parts, 0.03


def porthole():
    """A brass porthole vent (today's round grille): a thick brass ring with 6 bolts, an iron cross grille over a dark
    recess (r = 1.7 u = 17 pt)."""
    parts = []
    ring = torus(1.42, 0.34).rotate_x(90).translate(0, 0, 0.3)
    plate = cylinder(1.74, 0.12, round=0.1).rotate_x(90).translate(0, 0, 0.1)
    parts.append(Part("phRing", ring.union(plate), brass("ph_br"), voxel=0.02))
    bolts = union(*[sphere(0.13, center=(1.56 * math.cos(a), 1.56 * math.sin(a), 0.36)) for a in np.linspace(0, 2 * math.pi, 7)[:-1] + 0.3])
    parts.append(Part("phBolts", bolts, iron("ph_ir"), voxel=0.012))
    parts.append(Part("phHole", cylinder(1.25, 0.05).rotate_x(90).translate(0, 0, 0.22), satin("ph_hole", "#0E1E20", rough=0.6),
                      voxel=0.02))
    grille = union(capsule((-1.2, 0, 0.34), (1.2, 0, 0.34), 0.11), capsule((0, -1.2, 0.34), (0, 1.2, 0.34), 0.11),
                   torus(0.62, 0.09).rotate_x(90).translate(0, 0, 0.34))
    parts.append(Part("phGrille", grille, iron("ph_gr"), voxel=0.012))
    return parts, 0.02


LAMP_X = 364.0      # the two signal lamps: high on the right wainscot, above the porthole (today's pair: x 308, y 440-458)


def signal_lamps():
    """Two small signal lanterns (today's green / red indicator lamps): brass caps, amber and red glass."""
    from dataclasses import replace
    parts = []
    for name, sy, col_, em in (("lampA", 394, "#FFB22E", "#6A3A00"), ("lampR", 411, "#E8452F", "#5A120A")):
        base = cylinder(0.74, 0.1, round=0.08).rotate_x(90).translate(LAMP_X / 10, -sy / 10, 0.1)
        parts.append(Part(name + "Base", base, brass(f"{name}_b"), voxel=0.015))
        dome = sphere(0.60, center=(LAMP_X / 10, -sy / 10, 0.05))
        parts.append(Part(name, dome, replace(gloss(name, col_, rough=0.16, ior=1.48), emissive=em), voxel=0.012))
        cage = union(*[capsule((LAMP_X / 10 + 0.62 * math.cos(a), -sy / 10 + 0.62 * math.sin(a), 0.0),
                               (LAMP_X / 10 + 0.62 * math.cos(a), -sy / 10 + 0.62 * math.sin(a), 0.42), 0.05)
                       for a in np.linspace(0, 2 * math.pi, 5)[:-1] + 0.4])
        parts.append(Part(name + "Cage", cage, iron(f"{name}_c"), voxel=0.01))
    return parts, 0.015


def rails():
    """Today's tube railings on the deck rim, restyled: timber posts with iron caps and a thick rope rail."""
    parts = []
    wood = satin("rail_wood", "#B97A3E", rough=0.6, ior=1.25)
    rope = satin("rail_rope", "#D9B77E", rough=0.8, ior=1.2)
    z = 2.2
    for side in (-1, 1):
        def X(sx):
            return sx if side < 0 else 393 - sx
        for px in (35, 78):
            post = rbox(0.42, 0.95, 0.42, 0.12, center=W(X(px), 340.5 if px == 35 else 341.5, z))
            parts.append(Part(f"post{side}{px}", post, wood, voxel=0.018))
            parts.append(Part(f"cap{side}{px}", cylinder(0.5, 0.09, round=0.06, center=W(X(px), 331.2 if px == 35 else 332.2, z)),
                              iron(f"cap{side}"), voxel=0.012))
        # a sagging rope from the screen edge through the two posts
        pts = []
        for k in range(26):
            sx = -12 + (78 + 12) * k / 25
            sag = 3.2 * math.sin(math.pi * np.clip((sx - 35) / 43.0, 0, 1)) if sx > 35 else 2.4 * math.sin(math.pi * np.clip((sx + 12) / 47.0, 0, 1))
            pts.append(W(X(sx), 334.5 + sag, z + 0.25))
        parts.append(Part(f"rope{side}", path_tube(pts, [0.3] * len(pts)), rope, voxel=0.015))
    return parts, 0.02


def wall_lanterns():
    """Two small wall lanterns on brackets (upper left, right of the U-bend): the warm pools painted on the planks."""
    from dataclasses import replace
    parts = []
    for name, sx, sy in (("lanL", 140, 112), ("lanR", 254, 112)):
        x, y = sx / 10, -sy / 10
        bracket = tube([(x, y + 1.6, 0.1), (x, y + 1.6, 0.9), (x, y + 1.1, 1.1)], 0.09, bend=0.3)
        parts.append(Part(name + "Br", bracket, iron(f"{name}_br"), voxel=0.012))
        hood = round_cone(0.5, 0.25, 0.35).rotate_x(180).translate(x, y + 0.95, 1.1) if False else \
            capped_cone(0.18, 0.55, 0.3, round=0.06).translate(x, y + 0.85, 1.1)
        parts.append(Part(name + "Hood", hood, brass(f"{name}_h"), voxel=0.012))
        globe = ellipsoid(0.46, 0.58, 0.46).translate(x, y + 0.15, 1.1)
        parts.append(Part(name + "Glass", globe, replace(glass(f"{name}_g", "#FFE3A0", opacity=0.55), emissive="#FFB84A"),
                          voxel=0.012))
        parts.append(Part(name + "Base", cylinder(0.36, 0.08, round=0.05, center=(x, y - 0.46, 1.1)), brass(f"{name}_b"),
                          voxel=0.012))
    return parts, 0.015


MODELS = {"pipes_left_d1": pipes_left, "pipes_right_d1": pipes_right, "porthole_d1": porthole,
          "lamps_d1": signal_lamps, "rails_d1": rails, "lanterns_d1": wall_lanterns}


def _objects_spec(px):
    c = dict(center=False)
    return dict(scene=[(_M, "pipes_left_d1", c), (_M, "pipes_right_d1", c), (_M, "rails_d1", c), (_M, "lamps_d1", c),
                       (_M, "lanterns_d1", c),
                       (_M, "porthole_d1", dict(center=False, pos=W(290, 214, 0.0))),
                       (_M, "porthole_d1", dict(center=False, pos=W(336, 430, 0.0)))],
                bounds=((0.0, -85.2, -1.0), (39.3, 0.0, 3.6)), aspect=393 / 852, margin=1.0, fov=3.0, px=px,
                light=rig(key_lux=2000.0, fill_lux=650.0, key_color=(1.0, 0.95, 0.86), fill_color=(0.80, 0.95, 0.95)))


def build_workshop(ctx, objects=None):
    """homeWorkshop = the painted structure + the wall objects (one render, registered to the screen) + their soft
    shadows + the cabinet's shadow on the wainscot. `objects`: a pre-rendered objects image (proof harness)."""
    if objects is None:
        ims = ctx.render({"homeObjectsD1": _objects_spec(2556 * 1.3)})
        objects = ims["homeObjectsD1"].resize((1179, 2556), _Image.LANCZOS)
    cv = paint_workshop()
    mp = _os.path.join(K_OUT, "homeCabinet@3x.png")
    if _os.path.exists(mp):
        mim = _Image.open(mp).convert("RGBA")
        sh, (ox, oy) = shadow_of(mim, 6, 9, 14, 0.55, color="#1C0E06", grow_px=6)
        cv.over(sh, x=F_CABINET[0] * PX + ox, y=F_CABINET[1] * PX + oy)
    sh, (ox, oy) = shadow_of(objects, 7, 8, 7, 0.45, color="#061416")
    cv.over(sh, x=ox, y=oy)
    cv.over(objects)
    return cv.image()


F_CABINET = (95, 365, 301, 580)
F_BACKDROP = (0, 0, 393, 852)
BUILDS = {"homeWorkshop": build_workshop}


# ====================================================================== the cabinet (today's capsule machine, restyled)
# Same silhouette as scene_home.machine() (frame x 100..290, y 382..518; the housing with the LEVEL plate recess), so
# the same MACH_BOX mapping puts the recess exactly behind the UI plate rect. Materials: a honey timber frame with wood
# grain and brass corner plates, a brass bezel, dark timber inner walls, a deep-teal back wall with plank seams (the
# heap's bright cyan cavity -> a dark lantern-lit case), dark timber behind the plate. The signpost (home_signpost_rig)
# is drawn over it; its lantern replaces the dispenser ring.

import scene_home as _SH  # noqa: E402

MA_HX, MA_Y0, MA_Y1, MA_R = _SH.MA_HX, _SH.MA_Y0, _SH.MA_Y1, _SH.MA_R
OP_HX, OP_Y0, OP_Y1, OP_R = _SH.OP_HX, _SH.OP_Y0, _SH.OP_Y1, _SH.OP_R
IN_HX, IN_Y0, IN_Y1, IN_R = _SH.IN_HX, _SH.IN_Y0, _SH.IN_Y1, _SH.IN_R
CAV_Z, SLANT_IN = _SH.CAV_Z, _SH.SLANT_IN
_rr2 = _SH._rr2


def _wood_tex(base=("#F0C07A", "#E0A862", "#C98A4A", "#A86C34"), freq=38.0, seed=3, horizontal=True):
    """Planar wood-grain albedo: fine long streaks (along u when horizontal), warped by a few low sines, with a slow
    board-to-board tone drift and darker latewood lines (reads as sanded timber, not camouflage blotches)."""
    stops = [rgb(c) for c in base]
    rng = np.random.default_rng(seed)
    ph = rng.uniform(0, 6.28, 6)

    def fn(u, v):
        a, b = (u, v) if horizontal else (v, u)
        warp = 0.020 * np.sin(a * 9.0 + ph[0]) + 0.012 * np.sin(a * 23.0 + b * 3.0 + ph[1]) + 0.006 * np.sin(a * 61.0 + ph[2])
        x = (b + warp) * freq
        ring = x - np.floor(x)
        late = np.clip(1 - np.abs(ring - 0.82) / 0.10, 0, 1) ** 1.5           # thin dark latewood lines
        fine = 0.5 + 0.5 * np.sin(x * 2 * math.pi * 3.0 + np.sin(a * 40.0 + ph[3]))
        board = 0.5 + 0.5 * np.sin(b * 7.0 + ph[4])                              # slow tone drift
        c = stops[1] * (1 - board[..., None] * 0.35) + stops[0] * board[..., None] * 0.35
        c = c * (1 - 0.06 * fine[..., None]) * (1 - 0.18 * late[..., None]) + stops[3] * 0.18 * late[..., None]
        return c
    return fn


def _plank_tex(face="#1C3A3D", seam="#0B1A1C", n=7, grain_a=0.05):
    """The cabinet's back wall: deep-teal vertical planks with dark seams and a faint grain."""
    f, s = rgb(face), rgb(seam)

    def fn(u, v):
        x = u * n
        d = np.minimum(x - np.floor(x), np.ceil(x) - x)
        seam_m = np.clip(1 - d / 0.035, 0, 1)[..., None]
        k = np.floor(x)
        tone = (1 + 0.10 * np.sin(k * 12.9898 + 1.3))[..., None]
        grain = (1 + grain_a * np.sin(v * 60.0 + np.sin(u * 30.0) * 2.0))[..., None]
        return (f * tone * grain) * (1 - seam_m) + s * seam_m
    return fn


def cabinet(hk=False):
    """hk (LOOK-2 high-key home): a light sea-glass planked back wall, mid-honey cavity walls, a sand floor -- the same
    object, shapes and parts; the case is no longer a dark hole in a bright room."""
    from dataclasses import replace
    parts = []
    wood = replace(satin("cab_wood", "#D49A58", rough=0.55, ior=1.28), texture=_wood_tex(), texture_size=1024)
    frame2 = _rr2(MA_HX, MA_Y0, MA_Y1, MA_R)
    open2 = _rr2(OP_HX, OP_Y0, OP_Y1, OP_R)
    ring = extrude(frame2.subtract(open2), 0.6, round=0.45).translate(0, 0, 0.5)
    hous2 = _rr2(6.6, 0.0, 6.6, 1.7)
    hous = extrude(hous2, 0.85, round=0.45).translate(0, 0, 0.25)
    rec = extrude(_rr2(5.35, 0.42, 4.3, 1.55, cx=0.17), 0.5, round=0.3).translate(0, 0, 1.3)
    hous = hous.subtract(rec, k=0.12)
    body = ring.smooth_union(hous, k=1.1)
    uvp = ("planar", (-MA_HX, 0.0, 0.0), (1.0 / (2 * MA_HX), 0, 0), (0, 1.0 / (2 * MA_HX), 0), 1.0)
    parts.append(Part("frame", body, wood, uv=uvp, voxel=0.035))
    # the recess floor behind the LEVEL plate: dark timber
    parts.append(Part("recess", extrude(_rr2(5.25, 0.5, 4.22, 1.45, cx=0.17), 0.03).translate(0, 0, 0.83),
                      satin("cab_recess", "#4A2A14", rough=0.6), voxel=0.03))
    # brass bezel between the opening and the cavity, with iron rivets round it
    inner2 = _rr2(IN_HX, IN_Y0, IN_Y1, IN_R)
    bez = extrude(open2.offset(0.1).subtract(inner2), 0.3, round=0.24).translate(0, 0, 0.25)
    parts.append(Part("bezel", bez, metal("cab_brass", "#D9A441", rough=0.26), voxel=0.03))
    riv = []
    for k in range(18):
        t = k / 18
        # rivets along the bezel's centre line (a rounded rectangle: walk its perimeter)
        per = 2 * (2 * (OP_HX - 0.45)) + 2 * ((OP_Y1 - OP_Y0) - 0.9)
        s_ = t * per
        wx, hy = 2 * (OP_HX - 0.45), (OP_Y1 - OP_Y0) - 0.9
        x0, y0 = -(OP_HX - 0.45), OP_Y0 + 0.45
        if s_ < wx:
            p = (x0 + s_, y0)
        elif s_ < wx + hy:
            p = (x0 + wx, y0 + (s_ - wx))
        elif s_ < 2 * wx + hy:
            p = (x0 + wx - (s_ - wx - hy), y0 + hy)
        else:
            p = (x0, y0 + hy - (s_ - 2 * wx - hy))
        riv.append(sphere(0.13, center=(p[0], p[1], 0.52)))
    parts.append(Part("rivets", union(*riv), metal("cab_iron", "#5A5F66", rough=0.4), voxel=0.012))
    # brass corner rosettes on the frame (a domed disc + a bolt at each rounded corner, inside the silhouette)
    ros = []
    bolts = []
    for sx in (-1, 1):
        for top_ in (True, False):
            sy = 1 if top_ else -1
            co = np.array([sx * (MA_HX - MA_R), (MA_Y1 - MA_R) if top_ else (MA_Y0 + MA_R)])
            ci = np.array([sx * (OP_HX - OP_R), (OP_Y1 - OP_R) if top_ else (OP_Y0 + OP_R)])
            dg = np.array([sx, sy]) / math.sqrt(2)
            p_ = ((co + dg * MA_R) + (ci + dg * OP_R)) / 2          # the middle of the frame band on the diagonal
            ros.append(cylinder(0.30, 0.06, round=0.05).rotate_x(90).translate(p_[0], p_[1], 1.12))
            bolts.append(sphere(0.12, center=(p_[0], p_[1], 1.17)))
    parts.append(Part("rosettes", union(*ros), metal("cab_brass2", "#D2A046", rough=0.3), voxel=0.012))
    parts.append(Part("rosBolts", union(*bolts), metal("cab_iron2", "#5A5F66", rough=0.4), voxel=0.01))
    # cavity: a box shell open at the front; dark timber side walls, deep-teal planked back wall
    outer = extrude(_rr2(IN_HX + 0.6, IN_Y0 - 0.6, IN_Y1 + 0.6, IN_R + 0.5), (0.3 - CAV_Z) / 2 + 0.3).translate(
        0, 0, (0.3 + CAV_Z) / 2 - 0.3)
    cav = extrude(_rr2(IN_HX, IN_Y0, IN_Y1, IN_R), 3.0).translate(0, 0, CAV_Z + 3.0)
    shell = outer.subtract(cav)
    cut = CAV_Z + 0.12
    sides = shell.intersect(box(20, 20, 5, center=(0, 12, cut + 5)))
    back = shell.intersect(box(20, 20, 5, center=(0, 12, cut - 5)))
    dwood = replace(satin("cab_side", "#6E4424", rough=0.6, ior=1.25),
                    texture=_wood_tex(("#8A5A30", "#7A4C28", "#5E3A1E", "#48280F") if not hk else
                                      ("#D8A868", "#C8955A", "#B07E46", "#946636"), freq=22.0, seed=8), texture_size=512)
    parts.append(Part("cavitySides", sides, dwood, uv=("planar", (-IN_HX, 0.0, 0.0), (1.0 / (2 * IN_HX), 0, 0),
                                                          (0, 0, 1.0 / 5.0), 1.0), voxel=0.04))
    L = 0.2 - CAV_Z
    ang = math.degrees(math.atan2(SLANT_IN, L))
    ln = math.hypot(SLANT_IN, L) / 2
    hy = (IN_Y1 - IN_Y0) / 2
    zc = (0.2 + CAV_Z) / 2
    left = box(0.07, hy, ln, round=0.03).rotate_y(-ang).translate(-IN_HX + SLANT_IN / 2, (IN_Y0 + IN_Y1) / 2, zc)
    right = box(0.07, hy, ln, round=0.03).rotate_y(ang).translate(IN_HX - SLANT_IN / 2, (IN_Y0 + IN_Y1) / 2, zc)
    top = box(IN_HX, 0.07, ln, round=0.03).rotate_x(-ang).translate(0, IN_Y1 - SLANT_IN / 2, zc)
    parts.append(Part("slant", left.union(right).union(top), dwood,
                      uv=("planar", (-IN_HX, 0.0, 0.0), (1.0 / (2 * IN_HX), 0, 0), (0, 1.0 / (2 * hy), 0), 1.0), voxel=0.035))
    teal = replace(satin("cab_back", "#1C3A3D", rough=0.62, ior=1.22),
                   texture=_plank_tex() if not hk else _plank_tex(face="#5EA69D", seam="#3F8078", grain_a=0.012), texture_size=512)
    parts.append(Part("cavityBack", back, teal, uv=("planar", (-IN_HX, IN_Y0, 0.0), (1.0 / (2 * IN_HX), 0, 0),
                                                        (0, 1.0 / (IN_Y1 - IN_Y0), 0), 1.0), voxel=0.04))
    # the cavity floor: packed earth (the signpost's foot stands on it)
    floor = box(IN_HX - 0.05, 0.08, (0.2 - CAV_Z) / 2, center=(0, IN_Y0 + 0.02, (0.2 + CAV_Z) / 2))
    parts.append(Part("cavFloor", floor, satin("cab_earth", "#6C4428" if not hk else "#C9A57A", rough=0.8, ior=1.2), voxel=0.03))
    # a brass ceiling rail where the dispenser ring hung (the lantern hangs off the post now)
    parts.append(Part("ceilRail", box(IN_HX - 1.8, 0.12, 0.18, round=0.06, center=(0, IN_Y1 - 0.25, -1.6)),
                      metal("cab_brass3", "#C8943E", rough=0.3), voxel=0.02))
    return parts, 0.04


MODELS["cabinet"] = cabinet
MODELS["cabinet_hk"] = lambda: cabinet(hk=True)
MACH_VIEW = _SH.MACH_VIEW
MACH_BOX = _SH.MACH_BOX


def _cabinet_spec():
    return dict(scene=[(_M, "cabinet", dict(center=False))], view=MACH_VIEW, fov=12, px=1500,
                light=rig(key_lux=2000.0, fill_lux=700.0, shadow=False, key_color=(1.0, 0.94, 0.84),
                          fill_color=(0.85, 0.95, 0.95), env=d1_env()))


def d1_env():
    import scene_kit as SK
    return SK.scene_env("d1", sky=(1.0, 0.93, 0.80), hor=(0.52, 0.66, 0.66), gnd=(0.50, 0.36, 0.24),
                        boxes=(((-0.35, 0.75, 0.55), (0.62, 0.52, 0.36), 0.75), ((0.75, 0.25, -0.60), (0.30, 0.44, 0.44), 0.85)))


def build_cabinet(ctx):
    ims = ctx.render({"cabinetD1": _cabinet_spec()})
    im = ims["cabinetD1"]
    bb = alpha_bbox(im)
    _json.dump(dict(bb=bb, bounds=im.info["cam"]["bounds"], size=im.size),
               open(_os.path.join(_BUILD, f"cabinet_map{'_draft' if ctx.draft else ''}.json"), "w"))
    out = _SH._paste_mapped(im, bb, F_CABINET)
    cv = Canvas(F_CABINET[2] - F_CABINET[0], F_CABINET[3] - F_CABINET[1])
    cv.over(out)
    X, Y = cv.X + F_CABINET[0], cv.Y + F_CABINET[1]
    # the lantern's warm glow on the back wall + ceiling (the lantern hangs at ~(183, 410) pt), inside the window only
    win = aa(d_rrect(X, Y, 117, 395, 275, 509, 10), 1.0)
    g = np.exp(-(((X - 183) / 46.0) ** 2 + ((Y - 412) / 38.0) ** 2))
    cv.screen(g * win, "#FFC86A", 0.42)
    g2 = np.exp(-(((X - 196) / 70.0) ** 2 + ((Y - 470) / 50.0) ** 2))
    cv.screen(g2 * win, "#FFB85A", 0.10)
    # glass sheen: a soft highlight across the window's upper left (the case has a glass pane)
    for cx, cy, rx, ry, a in ((128, 404, 10, 6, 0.30), (262, 402, 6, 4, 0.20)):
        gg = np.exp(-(((X - cx) / rx) ** 2 + ((Y - cy) / ry) ** 2) * 1.6)
        cv.screen(gg, "#FFF6E0", a)
    return cv.image()


BUILDS["homeCabinet"] = build_cabinet


# ====================================================================== the floor + round plank work-pad (homeFloor)
# Today's glass dais (a wide shallow disc with a broad soft rim) -> a round work-pad of radial timber planks inside an
# iron hoop, on the packed-earth floor: same size and place (it carries the Play frame), the Diggers stand on it.

PAD_R = 20.0
PAD_IN = 18.3


def _pad_tex():
    """Top-down albedo: radial planks (18 wedges) with dark seams, grain along each plank, a darker iron hoop ring."""
    rng = np.random.default_rng(17)
    tones = rng.uniform(-0.08, 0.08, 64)
    c0, c1, c2 = rgb("#E3AA66"), rgb("#C98A4A"), rgb("#9A6130")

    def fn(u, v):
        x = (u - 0.5) * 2 * PAD_R
        z = (v - 0.5) * 2 * PAD_R
        r = np.sqrt(x * x + z * z)
        a = (np.arctan2(z, x) + math.pi) / (2 * math.pi)
        n = 20
        k = np.floor(a * n)
        fa = a * n - k
        seam = np.clip(1 - np.minimum(fa, 1 - fa) * (2 * math.pi * np.maximum(r, 0.3) / n) / 0.09, 0, 1)
        tone = tones[(k.astype(int)) % 64][..., None]
        g = 0.5 + 0.5 * np.sin(r * 5.1 + np.sin(a * 60.0) * 0.8 + k * 1.7)
        base = c0 * (1 - g[..., None]) + c1 * g[..., None]
        base = base * (1 + tone)
        # the centre boss: a round plank disc (concentric rings)
        hub = np.clip((3.2 - r) / 0.15, 0, 1)[..., None]
        base = base * (1 - hub) + (c1 * (0.92 + 0.08 * np.sin(r * 9.0))[..., None]) * hub
        seam = seam * (r > 3.3)
        base = base * (1 - 0.65 * seam[..., None]) + rgb("#4A2A12") * 0.65 * seam[..., None]
        # outer hoop (iron) and the inner ring (a darker plank border)
        hoop = np.clip((r - (PAD_IN + 0.1)) / 0.12, 0, 1)[..., None]
        base = base * (1 - hoop) + rgb("#4B4F55") * hoop
        ring = (np.clip((r - 16.9) / 0.1, 0, 1) * np.clip((17.35 - r) / 0.1, 0, 1))[..., None]
        base = base * (1 - ring) + c2 * ring
        return base
    return fn


def work_pad():
    from dataclasses import replace
    from scene_kit import lathe_part, planar_uv
    prof = [(0.0, -0.3), (PAD_R - 0.3, -0.3), (PAD_R, -0.1), (PAD_R - 0.05, 0.22), (PAD_R - 0.4, 0.40),
            (PAD_R - 1.0, 0.44), (PAD_IN + 0.3, 0.40), (PAD_IN - 0.3, 0.26), (PAD_IN - 1.2, 0.22), (6.0, 0.22), (0.0, 0.22)]
    m = replace(satin("pad", "#C98A4A", rough=0.58, ior=1.25), texture=_pad_tex(), texture_size=1024)
    return [lathe_part("pad", m, prof, n_seg=360, samples=220, uv_fn=planar_uv(-PAD_R, -PAD_R, 2 * PAD_R))], 0.05


MODELS["work_pad"] = work_pad
F_FLOOR = (0, 576, 393, 758)
DIGGER_FEET = ((70.0, 606.0), (318.0, 606.0))


def build_floor(ctx):
    ims = ctx.render({"workPadD1": dict(scene=[(_M, "work_pad", dict(pitch=21.5))], fov=10, px=1800,
                                        light=rig(key_lux=2000.0, fill_lux=650.0, key_color=(1.0, 0.95, 0.86),
                                                  fill_color=(0.85, 0.95, 0.95), env=d1_env()))})
    cv = Canvas(F_FLOOR[2] - F_FLOOR[0], F_FLOOR[3] - F_FLOOR[1])
    spr, (x, y) = fit_box(ims["workPadD1"], (-9 - F_FLOOR[0], 583.5 - F_FLOOR[1], 402 - F_FLOOR[0], 751 - F_FLOOR[1]),
                          mode="stretch")
    # the pad's own contact shadow on the earth (painted under it), then the pad
    X, Y = cv.X + F_FLOOR[0], cv.Y + F_FLOOR[1]
    g = aa(d_ellipse(X, Y, 196.5, 670, 208, 86), 6.0)
    cv.fill(g, "#2A160A", 0.35)
    cv.over(spr, x=x, y=y)
    # the Diggers' soft contact shadows (they stand still on the home screen; baked like today's platform)
    for fx, fy in DIGGER_FEET:
        g = np.exp(-(((X - fx) / 30.0) ** 2 + ((Y - fy - 1.5) / 7.0) ** 2) * 1.4)
        core = np.exp(-(((X - fx) / 18.0) ** 2 + ((Y - fy - 1.0) / 4.0) ** 2) * 1.6)
        cv.multiply(np.clip(g * 0.7 + core * 0.45, 0, 1), "#3A1E0C", 0.8)
    return cv.image()


BUILDS["homeFloor"] = build_floor


# ====================================================================== the station (homeScaffold, replaces homeConsole)
# R2's scaffold rail + brass lever (char_boss.station(), rendered from the boss rig's camera as char_bossStation, so
# the paws sit on the rail / knob exactly). That render is clipped by the rig's 190 x 164 frame: the rail ends are cut
# flat at the frame edges and the posts stop at the frame bottom (y 340 on screen), above the deck beam. homeScaffold =
# that render + (1) rounded, end-grain rail / brace ends, (2) the posts carried down onto the deck beam (their own
# timber repeated below the brace + an iron shoe), (3) soft contact shadows on the beam. No new render: registration
# with the boss's arm layers is exact by construction.
# Frame (109, 176, 191, 192) pt = the boss rig's frame (placed at (109, 176): the scientist's spot, whole pt) + 28 pt.

STATION_SRC = _os.path.join(_os.path.dirname(_BUILD), "route3d", "char_bossStation.png")
F_SCAFFOLD = (109, 176, 300, 368)
BOSS_PLACE = (109.0, 176.0)
RAIL_ROWS = (114.0, 125.67)          # frame pt (char_bossStation measured)
BRACE_ROWS = (152.33, 161.33)
POSTS = ((4.67, 17.33), (169.67, 182.33))


def build_scaffold(ctx):
    st = np.asarray(_Image.open(STATION_SRC).convert("RGBA")).astype(np.float64) / 255
    Hs, Ws = st.shape[:2]
    fw, fh = F_SCAFFOLD[2] - F_SCAFFOLD[0], F_SCAFFOLD[3] - F_SCAFFOLD[1]
    out = np.zeros((fh * PX, fw * PX, 4))
    ox, oy = round((BOSS_PLACE[0] - F_SCAFFOLD[0]) * PX), round((BOSS_PLACE[1] - F_SCAFFOLD[1]) * PX)
    out[oy:oy + Hs, ox:ox + Ws] = st
    yy, xx = np.mgrid[0:fh * PX, 0:fw * PX]
    X = (xx + 0.5) / PX - (BOSS_PLACE[0] - F_SCAFFOLD[0])       # frame-of-the-render pt
    Y = (yy + 0.5) / PX - (BOSS_PLACE[1] - F_SCAFFOLD[1])
    # (1) rounded rail / brace ends 2.5 pt past each post (end grain a shade darker)
    for (y0, y1) in (RAIL_ROWS, BRACE_ROWS):
        x0, x1 = POSTS[0][0] - 2.5, POSTS[1][1] + 2.5
        r = (y1 - y0) / 2
        d = d_rrect(X, Y, x0, y0 - 0.4, x1, y1 + 0.4, r)
        band = (Y >= y0 - 1.0) & (Y <= y1 + 1.0) & ((X < POSTS[0][0]) | (X > POSTS[1][1]))
        keep = aa(d, 0.5)
        out[..., 3] = np.where(band, out[..., 3] * keep, out[..., 3])
        endg = band & (np.abs(d) < 1.6) & (keep > 0.2)
        out[..., :3] = np.where(endg[..., None], out[..., :3] * 0.82, out[..., :3])
    # (2) the posts carried down: repeat the post's own rows between the rail and the brace (130..150) below the frame
    bottom_src = 163.0
    for (px0, px1) in POSTS:
        c0, c1 = int(round((px0 + BOSS_PLACE[0] - F_SCAFFOLD[0]) * PX)) - 2, int(round((px1 + BOSS_PLACE[0] - F_SCAFFOLD[0]) * PX)) + 2
        sx = (px0 + px1) / 2 + BOSS_PLACE[0]
        foot = rim_y(sx) + 2.0                                   # onto the deck beam's top face
        t0, t1 = int(round((130 + (BOSS_PLACE[1] - F_SCAFFOLD[1])) * PX)), int(round((150 + (BOSS_PLACE[1] - F_SCAFFOLD[1])) * PX))
        tile = out[t0:t1, c0:c1].copy()
        y = int(round((bottom_src + BOSS_PLACE[1] - F_SCAFFOLD[1]) * PX))
        yend = int(round((foot - F_SCAFFOLD[1]) * PX))
        k = 0
        while y < yend:
            n = min(t1 - t0, yend - y)
            seg = tile[k % 1 * 0: n]
            dst = out[y:y + n, c0:c1]
            a = seg[..., 3:4]
            dst[..., :3] = seg[..., :3] * a + dst[..., :3] * (1 - a)
            dst[..., 3:4] = np.maximum(dst[..., 3:4], a)
            y += n
            k += 1
        # a short blend over the seam (the render's last rows were anti-aliased by the frame cut)
        ys = int(round((bottom_src - 1.2 + BOSS_PLACE[1] - F_SCAFFOLD[1]) * PX))
        out[ys:ys + int(2.4 * PX), c0:c1, 3] = np.maximum(out[ys:ys + int(2.4 * PX), c0:c1, 3],
                                                           out[ys - 3:ys - 3 + int(2.4 * PX), c0:c1, 3])
        # an iron shoe at the foot + a darker grain band just above it
        shoe0 = int(round((foot - 4.5 - F_SCAFFOLD[1]) * PX))
        col = out[shoe0:yend, c0:c1]
        m = col[..., 3:4] > 0.5
        grad = np.linspace(0, 1, col.shape[0])[:, None, None]
        iron = np.array([0x5A, 0x5F, 0x66]) / 255 * (1.15 - 0.4 * grad)
        col[..., :3] = np.where(m, iron, col[..., :3])
        col[:2, :, :3] = np.where(m[:2], np.array([0xC9, 0xCE, 0xD6]) / 255 * 0.85, col[:2, :, :3])
    img = _Image.fromarray((np.clip(out, 0, 1) * 255 + 0.5).astype(np.uint8), "RGBA")
    # (3) contact shadows on the deck beam under each post (painted UNDER the posts)
    cv = Canvas(fw, fh)
    Xs, Ys = cv.X + F_SCAFFOLD[0], cv.Y + F_SCAFFOLD[1]
    for (px0, px1) in POSTS:
        sx = (px0 + px1) / 2 + BOSS_PLACE[0]
        g = np.exp(-(((Xs - sx - 2) / 11.0) ** 2 + ((Ys - rim_y(sx) - 3.5) / 3.2) ** 2))
        cv.fill(g, "#241206", 0.55)
    cv.over(img)
    return cv.image()


BUILDS["homeScaffold"] = build_scaffold


# ---------------------------------------------------------------------- homeFloor, painted (the pad is a flat disc seen at
# ~21 deg: painted in the disc's own coordinates, lit like the wall; no render job needed). Replaces the render build.
PAD_BOX = (-9.0, 583.5, 402.0, 751.0)        # today's dais box (pt): the pad keeps its size and place


def paint_floor():
    cv = Canvas(F_FLOOR[2] - F_FLOOR[0], F_FLOOR[3] - F_FLOOR[1])
    X, Y = cv.X + F_FLOOR[0], cv.Y + F_FLOOR[1]
    h, w = cv.h, cv.w
    x0, y0, x1, y1 = PAD_BOX
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2 - 3.0
    rx, ry = (x1 - x0) / 2, (y1 - y0) / 2 - 3.0
    thick = 7.0                                            # the pad's side band seen at the front
    u, v = (X - cx) / rx, (Y - cy) / ry
    r = np.sqrt(u * u + v * v)
    ang = np.arctan2(v, u)
    # side band (the pad's thickness): the ellipse shifted down by `thick`, outside the top face
    vs = (Y - cy - thick) / ry
    rs = np.sqrt(u * u + vs * vs)
    side = (rs <= 1.0) & (r > 1.0) & (Y > cy)
    # contact shadow on the earth
    g = aa(d_ellipse(X, Y, cx + 2, cy + thick + 3, rx + 4, ry + 3), 7.0)
    cv.fill(g, "#241206", 0.42)
    # top face: parallel planks (a round plank lid in an iron hoop), grain along the planks, staggered butt joints
    npl = 11
    pv = (v + 1) / 2 * npl
    k = np.floor(pv)
    fv = pv - k
    rng = np.random.default_rng(17)
    tones = rng.uniform(-0.08, 0.08, npl + 2)
    tone = tones[np.clip(k.astype(int), 0, npl + 1)]
    gr = _grain(h, w, 60, 2, 5)
    base = stops_interp(v, [(-1.0, "#8A5530"), (-0.2, "#A66C3A"), (0.5, "#B87C44"), (1.0, "#C68A4E")])   # oiled oak
    face = base * (1 + tone[..., None] + 0.06 * gr[..., None])
    top = r <= 1.0
    col = np.zeros((h, w, 3))
    col[top] = face[top]
    sidecol = stops_interp((Y - cy) / (ry + thick), [(0, "#8E5A2F"), (0.8, "#7A4C28"), (1.0, "#5E3718")])
    col[side] = sidecol[side]
    alpha = np.clip(aa((r - 1.0) * min(rx, ry), 0.6) + aa((rs - 1.0) * min(rx, ry), 0.6) * (Y > cy), 0, 1)
    src = np.zeros((h, w, 4))
    src[..., :3] = col
    src[..., 3] = alpha
    cv.over(src)
    seam_pt = np.minimum(fv, 1 - fv) * (2 * ry / npl)
    on = top & (r < 0.905)
    cv.multiply(aa(seam_pt - 0.5, 0.4) * on, "#4A2A12", 0.75)
    cv.screen(aa(np.abs(fv * (2 * ry / npl) - 1.1) - 0.3, 0.35) * on, WARM, 0.14)
    joff = rng.uniform(0, 1, npl + 2)
    jl = rng.uniform(0.55, 0.9, npl + 2)
    kk = np.clip(k.astype(int), 0, npl + 1)
    ju = (u + 1 + joff[kk]) / jl[kk]
    jd = np.minimum(ju - np.floor(ju), np.ceil(ju) - ju) * jl[kk] * rx
    cv.multiply(aa(jd - 0.5, 0.4) * on, "#4A2A12", 0.7)
    # nail pairs at the joints' ends and two batten lines of nails across the planks (the battens under the lid)
    for bu in (-0.45, 0.45):
        for kn in range(npl):
            vc = (kn + 0.5) / npl * 2 - 1
            px, py = cx + bu * rx, cy + vc * ry
            if (bu ** 2 + vc ** 2) > 0.8:
                continue
            d = d_ellipse(X, Y, px, py, 1.3, 0.8)
            cv.fill(aa(d, 0.35), "#3A2A1C")
            cv.screen(aa(d_ellipse(X, Y, px - 0.35, py - 0.25, 0.5, 0.3), 0.3), "#E8D8C0", 0.35)
    # the iron hoop round the rim (top face ring 0.915..1.0) with rivets, and its lit upper edge
    hoop = top & (r >= 0.915)
    hp = stops_interp(v, [(-1.0, "#3E4247"), (0.2, "#5A5F66"), (1.0, "#7A818A")])
    cv.a[..., :3] = np.where(hoop[..., None], hp, cv.a[..., :3])
    cv.multiply(aa(np.abs(r - 0.915) * min(rx, ry) - 0.5, 0.5) * top, "#1E1008", 0.6)
    cv.screen(aa(np.abs(r - 0.93) * min(rx, ry) - 0.3, 0.4) * top * (v < 0), "#C9CED6", 0.25)
    for a_ in np.linspace(-math.pi, math.pi, 29)[:-1]:
        px, py = cx + 0.957 * rx * math.cos(a_), cy + 0.957 * ry * math.sin(a_)
        d = d_ellipse(X, Y, px, py, 1.9, 1.2)
        cv.fill(aa(d, 0.4), "#2A2D31")
        cv.screen(aa(d_ellipse(X, Y, px - 0.5, py - 0.4, 0.8, 0.5), 0.35), "#D0D5DC", 0.5)
    # the side band: the hoop continues down the front (iron) over the timber edge
    sb = side & ((Y - cy - thick) / ry > -1.0)
    cv.multiply(sb * aa(np.abs((rs - 1.0) * min(rx, ry)) - 0.4, 0.5), "#1E1008", 0.5)
    hoop_side = side & (Y - (cy + ry * np.sqrt(np.clip(1 - u * u, 0, 1))) < thick * 0.55)
    cv.a[..., :3] = np.where(hoop_side[..., None], cv.a[..., :3] * 0.55 + np.array(rgb("#4B4F55")) * 0.45, cv.a[..., :3])
    # light: a warm pool on the front half, the back half falls off; worn centre where the crew walks
    cv.screen(np.exp(-(((X - cx) / (rx * 0.75)) ** 2 + ((Y - cy - ry * 0.25) / (ry * 0.8)) ** 2)) * top, LANTERN, 0.10)
    cv.multiply(np.clip(-v, 0, 1) ** 1.5 * top, "#3A1E0C", 0.25)
    # the Diggers' soft contact shadows (they stand still on the home screen; baked like today's platform)
    for fx, fy in DIGGER_FEET:
        g = np.exp(-(((X - fx) / 30.0) ** 2 + ((Y - fy - 1.5) / 7.0) ** 2) * 1.4)
        core = np.exp(-(((X - fx) / 18.0) ** 2 + ((Y - fy - 1.0) / 4.0) ** 2) * 1.6)
        cv.multiply(np.clip(g * 0.7 + core * 0.45, 0, 1), "#3A1E0C", 0.8)
    return cv.image()


def build_floor_painted(ctx):
    return paint_floor()


BUILDS["homeFloor"] = build_floor_painted


# ====================================================================== LOOK-2 HOME: the HIGH-KEY ground
# The owner (09-28): "the loading image is not as smooth and good as the original" -- the same diagnosis on the home
# (build/p/LOOK/round3.json home_findings, MEASURED by build/p/LOOK/measure.py): the D1 home's ground is too DARK (ground
# L* mean 42 vs the original's 59, near-white share 0.2 % vs 14 %, frame p95 68 vs 87) and its planks / brick / plank
# floor are 5-6x too EDGY (floor Laplacian 48x). LOOK-2 keeps the SAME composition, object types and UI rects (ruling 46:
# planks under a header beam, a mid batten, copper pipes, the curved ledge, stone courses, the deck beam + rope rails,
# the honey wainscot, the stone plinth, the earth floor + the round plank work-pad) and changes only VALUE and DETAIL
# FREQUENCY: a pale sea-glass plank wall lit by a warm-white glow behind the foreman, pale limestone courses, a light
# honey wainscot, a light sand floor; every joint wider + softer + lower in contrast (no pits, pebbles or nails that
# read as speckle); and a soft depth of field on the whole backdrop (the far layer), like the Loading's.
# The old painters above stay (paint_workshop / paint_floor) for rollback; BUILDS points at the _hk builds below.

HK_PLANK = ("#A6E8DC", "#64CDBE", "#35AFA2", "#1F8D84")      # glow-side face .. far corner
HK_TIMBER = ("#FBE2B4", "#EFC98E", "#DDAE6E", "#B98A4E", "#8A6232")    # light .. outline (a light honey, never dark brown)
HK_STONE = ("#72C4B9", "#52ADA2", "#3A948A", "#2C7E76", "#1F6A63")
HK_PLINTH = ("#3A9189", "#2A7770", "#1F625C", "#154A45")    # limestone: lit .. shade .. mortar
HK_EARTH = ("#B4A68E", "#C2B49C", "#CEC1AA", "#D6CAB4")
HK_GLOW = "#FFF7E8"
HK_COOLGLOW = "#F4FFFC"      # the light behind the foreman: a cool white in the wall's own hue (a warm white on teal
                             # made a green-yellow in-between band)
HK_JOINT = "#3F7C76"          # the plank gaps (a darker teal of the wall's own hue, not near-black)
HK_TJOINT = "#9A6E3C"         # timber seams (a darker honey)
HK_BLUR_PT = 0.55             # the backdrop's depth of field (gaussian sigma, pt): the far layer, behind every figure


def _masonry_hk(cv, X, Y, mask, y0, course, seed, base_c, mortar, amp=0.07):
    """Pale limestone courses: level courses, staggered blocks, per-block tone +-amp (was +-0.26), a WIDE soft mortar
    joint of a mid tone (was a crisp near-black line), a faint lit top edge; no chips, pits or speckle."""
    h, w = cv.h, cv.w
    rng3 = np.random.default_rng(seed)
    row = np.floor((Y - y0) / course).astype(int)
    nrow = int(max(row.max(), 0)) + 2
    offs = rng3.uniform(0, 70, nrow + 1)
    widths = rng3.uniform(36, 70, nrow + 1)
    rr_ = np.clip(row, 0, nrow)
    u = (X + offs[rr_]) / widths[rr_]
    blk = np.floor(u)
    lx = (u - blk) * widths[rr_]
    lyy = ((Y - y0) / course - row) * course
    key = (rr_ * 131 + blk.astype(int) * 17) % 97
    h1 = (np.sin(key * 12.9898) * 43758.5453) % 1.0 - 0.5
    bw = widths[rr_]
    r = 3.0
    qx = np.abs(lx - bw / 2) - (bw / 2 - 1.3 - r)
    qy = np.abs(lyy - course / 2) - (course / 2 - 1.3 - r)
    dbox = np.sqrt(np.maximum(qx, 0) ** 2 + np.maximum(qy, 0) ** 2) + np.minimum(np.maximum(qx, qy), 0) - r
    col = base_c * (1 + 2 * amp * h1[..., None])
    cv.a[..., :3] = np.where(mask[..., None], col, cv.a[..., :3])
    inside = aa(dbox, 1.1)
    cv.multiply((1 - inside) * mask, mortar, 0.42)
    up_ = (lyy < course * 0.45)
    edge = np.clip(1 + dbox / 3.0, 0, 1) * inside
    cv.screen(edge * mask * up_, HK_GLOW, 0.10)
    cv.multiply(edge * mask * (~up_), mortar, 0.10)
    nz = noise2(h, w, 30, seed=seed)
    cv.a[..., :3] = np.where(mask[..., None], cv.a[..., :3] * (1 + 0.025 * nz[..., None]), cv.a[..., :3])


def paint_workshop_hk():
    cv = Canvas(393, 852, color=HK_PLANK[1])
    X, Y = cv.X, cv.Y
    h, w = cv.h, cv.w
    col = np.zeros((h, w, 3))
    ly = ledge_y(X)
    ry = rim_y(X)
    rb = ry + 11.0
    # ---------------- upper wall: pale sea-glass planks; the value comes from the light (a warm-white glow behind the
    # foreman, falling off to the top corners), not from dark gaps
    edges, pi = _planks_v(X, Y, -6, 400, seed=7, wmin=30.0, wmax=40.0)
    rng = np.random.default_rng(11)
    tone = rng.uniform(-0.055, 0.055, len(edges))[pi]      # board-to-board tone (painted boards, not one sheet)
    gl = np.exp(-(((X - 196.5) / 175.0) ** 2 + ((Y - 175.0) / 150.0) ** 2))
    base = stops_interp(gl, [(0.0, HK_PLANK[3]), (0.30, HK_PLANK[2]), (0.62, HK_PLANK[1]), (1.0, HK_PLANK[0])])
    gr = _grain(h, w, 6, 140, 3)
    col[:] = base * (1 + tone[..., None] + 0.015 * gr[..., None])
    # ---------------- below the ledge: limestone courses (pale; the same glow falls on them)
    below = Y > ly + 10
    gl2 = np.exp(-(((X - 196.5) / 190.0) ** 2 + ((Y - 290.0) / 120.0) ** 2))
    stone = stops_interp(gl2, [(0.0, HK_STONE[3]), (0.45, HK_STONE[2]), (0.8, HK_STONE[1]), (1.0, HK_STONE[0])])
    col[below] = stone[below]
    # ---------------- wainscot: light honey planks
    wm = (Y > rb) & (Y <= WAINSCOT_BOTTOM)
    ph = 13.2
    WTOP = 361.0
    prow = np.floor((Y - WTOP) / ph)
    rng2 = np.random.default_rng(5)
    rowtone = rng2.uniform(-0.025, 0.025, 64)
    wtone = rowtone[np.clip(prow.astype(int), 0, 63)]
    wg = _grain(h, w, 110, 4, 9)
    honey = stops_interp(X, [(0, "#C8944F"), (70, "#DAAA66"), (196, "#E4BA7C"), (320, "#DAAA66"), (393, "#C8944F")])
    col[wm] = (honey * (1 + wtone[..., None] + 0.02 * wg[..., None]))[wm]
    # ---------------- plinth: limestone, a step darker (it is in the shade of the deck)
    sm = (Y > WAINSCOT_BOTTOM) & (Y <= FLOOR_Y)
    plinth = stops_interp(X, [(0, HK_PLINTH[2]), (110, HK_PLINTH[1]), (196, HK_PLINTH[0]), (290, HK_PLINTH[1]), (393, HK_PLINTH[2])])
    col[sm] = plinth[sm]
    # ---------------- floor: light sand, brighter toward the front (the room light pools on it)
    fl = stops_interp(Y, [(575, HK_EARTH[0]), (620, HK_EARTH[1]), (720, HK_EARTH[2]), (852, HK_EARTH[3])])
    side = (np.abs(X - 196.5) / 196.5) ** 2
    fl = fl * (1 - 0.10 * side[..., None])
    fm = Y > FLOOR_Y
    col[fm] = fl[fm]
    cv.a[..., :3] = col
    cv.a[..., 3] = 1.0

    up = Y < ly
    for e in edges:                       # soft, wide, low-contrast plank joints (a groove, not a black line)
        d = np.abs(X - e)
        cv.multiply(aa(d - 1.2, 1.2) * up, HK_JOINT, 0.58)
        cv.screen(aa(np.abs(X - e - 2.2) - 0.8, 1.2) * up, HK_GLOW, 0.07)
    # the header beam
    hb0, hb1 = 26.0, 42.0
    hbm = (Y > hb0) & (Y <= hb1)
    tb = np.clip((Y - hb0) / (hb1 - hb0), 0, 1)
    beam = stops_interp(tb, [(0, HK_TIMBER[0]), (0.25, HK_TIMBER[1]), (0.8, HK_TIMBER[2]), (1.0, HK_TIMBER[3])])
    beam = beam * (1 + 0.02 * _grain(h, w, 90, 4, 21)[..., None])
    cv.a[..., :3] = np.where(hbm[..., None], beam, cv.a[..., :3])
    cv.multiply(aa(np.abs(Y - hb1) - 0.6, 0.9), HK_TIMBER[4], 0.35)
    cv.multiply(smooth(-(Y - hb1), -12, 0) * (Y > hb1) * up, HK_JOINT, 0.18)
    for bx in (18, 104, 196.5, 289, 375):
        for by in (31.0, 37.0):
            r = np.sqrt((X - bx) ** 2 + (Y - by) ** 2)
            cv.fill(aa(r - 1.9, 0.8), "#8A8F96", 0.8)
    # the mid batten
    mb0, mb1 = 128.0, 135.0
    mbm = (Y > mb0) & (Y <= mb1)
    tm = np.clip((Y - mb0) / (mb1 - mb0), 0, 1)
    bat = stops_interp(tm, [(0, HK_TIMBER[1]), (0.35, HK_TIMBER[2]), (1.0, HK_TIMBER[3])])
    cv.a[..., :3] = np.where(mbm[..., None], bat, cv.a[..., :3])
    cv.multiply(aa(np.abs(Y - mb1) - 0.5, 0.9), HK_TIMBER[4], 0.30)
    cv.multiply(smooth(-(Y - mb1), -8, 0) * (Y > mb1) * up, HK_JOINT, 0.14)
    # the warm-white glow behind the foreman (screened over planks + batten), and the lantern pools
    # (r3: a DAYLIGHT SHAFT from the upper right -- art-direction D1's "daylight shaft from the top-right" -- falling
    # across the planks onto the foreman's shoulders, instead of a round pool centred behind him: the copy gate's SSIM
    # read the centred pool as the original's bright column)
    ax, ay = -0.52, 0.85
    t_ = (X - 330.0) * ax + (Y - 0.0) * ay                  # along the shaft (down-left)
    n_ = -(X - 330.0) * ay + (Y - 0.0) * ax                 # across it
    shaft = np.exp(-(n_ / (58.0 + 0.22 * np.clip(t_, 0, None))) ** 2) * smooth(t_, -20, 60) * (1 - smooth(t_, 230, 330))
    cv.screen(shaft * up, HK_COOLGLOW, 0.50)
    g = np.exp(-(((X - 205.0) / 95.0) ** 2 + ((Y - 200.0) / 70.0) ** 2))
    cv.screen(g * up, HK_COOLGLOW, 0.22)
    for lx, lyy in ((140, 118), (254, 118)):
        cv.screen(np.exp(-(((X - lx) / 40.0) ** 2 + ((Y - lyy) / 50.0) ** 2)) * up, LANTERN, 0.08)
    # ---------------- the ledge
    lip = (Y > ly) & (Y <= ly + 10)
    tl = np.clip((Y - ly) / 10.0, 0, 1)
    lipcol = stops_interp(tl, [(0, HK_TIMBER[0]), (0.3, HK_TIMBER[1]), (0.85, HK_TIMBER[2]), (1.0, HK_TIMBER[3])])
    cv.a[..., :3] = np.where(lip[..., None], lipcol, cv.a[..., :3])
    cv.multiply(smooth(Y, ly - 14, ly) * (Y <= ly), HK_JOINT, 0.16)
    cv.multiply(aa(np.abs(Y - ly) - 0.5, 0.8), HK_TIMBER[4], 0.30)
    cv.multiply(aa(np.abs(Y - ly - 10.2) - 0.6, 0.9), HK_TIMBER[4], 0.30)
    # ---------------- limestone courses + plinth
    lower = (Y > ly + 10) & (Y < ry)
    _masonry_hk(cv, X, Y, lower, 0.0, 24.0, 41, cv.a[..., :3].copy(), HK_STONE[4])
    cv.multiply(smooth(-(Y - ly - 10), -16, 0) * lower, HK_JOINT, 0.20)
    plinth_m = (Y > WAINSCOT_BOTTOM + 6) & (Y <= FLOOR_Y)
    _masonry_hk(cv, X, Y, plinth_m, WAINSCOT_BOTTOM + 6, 27.0, 43, cv.a[..., :3].copy(), HK_PLINTH[3])
    # ---------------- the deck beam
    rimm = (Y > ry) & (Y <= rb)
    tr = np.clip((Y - ry) / 11.0, 0, 1)
    rimcol = stops_interp(tr, [(0, HK_TIMBER[0]), (0.2, HK_TIMBER[1]), (0.7, HK_TIMBER[2]), (1.0, HK_TIMBER[3])])
    cv.a[..., :3] = np.where(rimm[..., None], rimcol, cv.a[..., :3])
    cv.multiply(aa(np.abs(Y - ry) - 0.5, 0.8), HK_TIMBER[4], 0.30)
    cv.multiply(aa(np.abs(Y - rb) - 0.6, 0.8), HK_TIMBER[4], 0.35)
    # ---------------- wainscot seams: soft
    fy = (Y - WTOP) / ph
    dseam = (fy - np.floor(fy)) * ph
    cv.multiply(aa(np.minimum(dseam, ph - dseam) - 0.8, 1.0) * wm, HK_TJOINT, 0.62)
    cv.screen(aa(np.abs(dseam - 1.6) - 0.5, 0.9) * wm, HK_GLOW, 0.10)
    rng4 = np.random.default_rng(13)
    joff = rng4.uniform(0, 120, 64)
    jw = rng4.uniform(130, 200, 64)
    rr = np.clip(prow.astype(int), 0, 63)
    ju = (X + joff[rr]) / jw[rr]
    jd = np.minimum(ju - np.floor(ju), np.ceil(ju) - ju) * jw[rr]
    cv.multiply(aa(jd - 0.6, 0.9) * wm, HK_TJOINT, 0.40)
    cv.multiply(smooth(-(Y - rb), -12, 0) * wm, HK_TJOINT, 0.22)
    cv.multiply(smooth(Y, WAINSCOT_BOTTOM - 8, WAINSCOT_BOTTOM) * wm, HK_TJOINT, 0.12)
    # ---------------- the plinth's cap strip
    cap = (Y > WAINSCOT_BOTTOM) & (Y <= WAINSCOT_BOTTOM + 6)
    tc = np.clip((Y - WAINSCOT_BOTTOM) / 6.0, 0, 1)
    capcol = stops_interp(tc, [(0, HK_TIMBER[0]), (0.45, HK_TIMBER[1]), (1.0, HK_TIMBER[3])])
    cv.a[..., :3] = np.where(cap[..., None], capcol, cv.a[..., :3])
    cv.multiply(smooth(-(Y - WAINSCOT_BOTTOM - 6), -10, 0) * plinth_m, HK_JOINT, 0.20)
    cv.multiply(smooth(Y, FLOOR_Y - 12, FLOOR_Y) * plinth_m, HK_JOINT, 0.16)
    # ---------------- the floor: a soft contact line at the wall, a gentle mottling (no pebbles)
    cv.multiply(aa(np.abs(Y - FLOOR_Y) - 0.8, 1.0), "#7A5A36", 0.30)
    cv.multiply(smooth(-(Y - FLOOR_Y), -26, 0) * fm, "#8A6844", 0.26)
    nz = noise2(h, w, 60, seed=61)
    cv.a[..., :3] = np.where(fm[..., None], cv.a[..., :3] * (1 + 0.025 * nz[..., None]), cv.a[..., :3])
    # a light vignette (the corners fall off a little, in the wall's own hue: the page stays high-key)
    vx = ((X - 196.5) / 196.5) ** 2
    vy = ((Y - 380) / 470) ** 2
    cv.multiply(np.clip(vx * 0.62 + vy * 0.36, 0, 1), "#15524C", 0.52)
    cv.multiply(smooth(-Y, -120, 0), "#15524C", 0.22)          # the top band falls off into the wall's deep teal
    return cv


def _objects_hk(objects):
    """The wall objects render in the high-key room: shadows lifted toward the room's light (the dark room made them
    heavy), a warm lift, then the same depth of field as the wall they hang on."""
    a = np.asarray(objects.convert("RGBA")).astype(np.float64) / 255
    c = a[..., :3]
    lum = c @ np.array([0.2126, 0.7152, 0.0722])
    lift = np.clip(0.55 - lum, 0, 1)[..., None] * 0.30
    c = c + (np.array(rgb(HK_GLOW)) - c) * lift
    c = np.clip(c * 1.06 + 0.02, 0, 1)
    a[..., :3] = c
    return _Image.fromarray((a * 255 + 0.5).astype(np.uint8), "RGBA")


def _dof(im, sigma_pt=HK_BLUR_PT):
    """Premultiplied gaussian blur of an RGBA image (sigma in pt at @3x)."""
    a = np.asarray(im.convert("RGBA")).astype(np.float64) / 255
    pm = np.concatenate([a[..., :3] * a[..., 3:], a[..., 3:]], -1)
    pm = blur(pm, sigma_pt * PX)
    al = pm[..., 3:]
    c = np.where(al > 1e-4, pm[..., :3] / np.maximum(al, 1e-4), 0)
    out = np.concatenate([np.clip(c, 0, 1), np.clip(al, 0, 1)], -1)
    return _Image.fromarray((out * 255 + 0.5).astype(np.uint8), "RGBA")


HK_OBJECTS_RAW = _os.path.join(_BUILD, "raw", "homeObjectsD1.png")     # R3's objects render (reused: no new render)


def build_workshop_hk(ctx, objects=None):
    """homeWorkshop (LOOK-2 high-key): the high-key painted structure + R3's wall-objects render (the same objects and
    places, regraded for the brighter room) + their soft shadows + the cabinet's shadow, then the backdrop's depth of
    field."""
    if objects is None:
        if _os.path.exists(HK_OBJECTS_RAW):
            objects = _Image.open(HK_OBJECTS_RAW).convert("RGBA").resize((1179, 2556), _Image.LANCZOS)
        else:
            ims = ctx.render({"homeObjectsD1": _objects_spec(2556 * 1.3)})
            objects = ims["homeObjectsD1"].resize((1179, 2556), _Image.LANCZOS)
    objects = _objects_hk(objects)
    cv = paint_workshop_hk()
    mp = _os.path.join(K_OUT, "homeCabinet@3x.png")
    if _os.path.exists(mp):
        mim = _Image.open(mp).convert("RGBA")
        sh, (ox, oy) = shadow_of(mim, 6, 10, 18, 0.30, color="#5A4026", grow_px=6)
        cv.over(sh, x=F_CABINET[0] * PX + ox, y=F_CABINET[1] * PX + oy)
    sh, (ox, oy) = shadow_of(objects, 7, 9, 10, 0.26, color="#2F6A64")
    cv.over(sh, x=ox, y=oy)
    cv.over(objects)
    return _dof(cv.image())


def paint_floor_hk():
    """homeFloor (LOOK-2 high-key): the same round plank work-pad in an iron hoop at the same place and size, as a
    light POLISHED oak lid -- wide soft seams, no nails, a soft broad sheen across the front (the pad reads as one
    calm lit surface, not a grid of hard lines), a pewter hoop with soft rivets; the Diggers' contact shadows."""
    cv = Canvas(F_FLOOR[2] - F_FLOOR[0], F_FLOOR[3] - F_FLOOR[1])
    X, Y = cv.X + F_FLOOR[0], cv.Y + F_FLOOR[1]
    h, w = cv.h, cv.w
    x0, y0, x1, y1 = PAD_BOX
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2 - 3.0
    rx, ry = (x1 - x0) / 2, (y1 - y0) / 2 - 3.0
    thick = 7.0
    u, v = (X - cx) / rx, (Y - cy) / ry
    r = np.sqrt(u * u + v * v)
    vs = (Y - cy - thick) / ry
    rs = np.sqrt(u * u + vs * vs)
    side = (rs <= 1.0) & (r > 1.0) & (Y > cy)
    g = aa(d_ellipse(X, Y, cx + 2, cy + thick + 3, rx + 5, ry + 4), 9.0)
    cv.fill(g, "#7A5A36", 0.26)
    npl = 11
    pv = (v + 1) / 2 * npl
    k = np.floor(pv)
    fv = pv - k
    rng = np.random.default_rng(17)
    tones = rng.uniform(-0.025, 0.025, npl + 2)
    tone = tones[np.clip(k.astype(int), 0, npl + 1)]
    gr = _grain(h, w, 70, 2, 5)
    base = stops_interp(v, [(-1.0, "#C99E68"), (-0.2, "#D8AE78"), (0.5, "#E2BC88"), (1.0, "#E8C592")])   # honey oak
    face = base * (1 + tone[..., None] + 0.030 * gr[..., None])
    top = r <= 1.0
    col = np.zeros((h, w, 3))
    col[top] = face[top]
    sidecol = stops_interp((Y - cy) / (ry + thick), [(0, "#BCB2A2"), (0.8, "#A69C8A"), (1.0, "#8C8270")])
    col[side] = sidecol[side]
    alpha = np.clip(aa((r - 1.0) * min(rx, ry), 0.8) + aa((rs - 1.0) * min(rx, ry), 0.8) * (Y > cy), 0, 1)
    src = np.zeros((h, w, 4))
    src[..., :3] = col
    src[..., 3] = alpha
    cv.over(src)
    seam_pt = np.minimum(fv, 1 - fv) * (2 * ry / npl)
    on = top & (r < 0.905)
    cv.multiply(aa(seam_pt - 0.6, 1.1) * on, HK_TJOINT, 0.30)
    joff = rng.uniform(0, 1, npl + 2)
    jl = rng.uniform(0.55, 0.9, npl + 2)
    kk = np.clip(k.astype(int), 0, npl + 1)
    ju = (u + 1 + joff[kk]) / jl[kk]
    jd = np.minimum(ju - np.floor(ju), np.ceil(ju) - ju) * jl[kk] * rx
    cv.multiply(aa(jd - 0.6, 1.1) * on, HK_TJOINT, 0.24)
    # the hoop: pewter, lit upper edge, soft rivets
    hoop = top & (r >= 0.915)
    hp = stops_interp(v, [(-1.0, "#9A9E9E"), (0.2, "#AEB2B0"), (1.0, "#C2C5C2")])
    cv.a[..., :3] = np.where(hoop[..., None], hp, cv.a[..., :3])
    cv.multiply(aa(np.abs(r - 0.915) * min(rx, ry) - 0.5, 1.0) * top, "#6A4A2A", 0.18)
    cv.screen(aa(np.abs(r - 0.93) * min(rx, ry) - 0.4, 0.7) * top * (v < 0), "#FFFFFF", 0.20)
    for a_ in np.linspace(-math.pi, math.pi, 15)[:-1]:
        px, py = cx + 0.957 * rx * math.cos(a_), cy + 0.957 * ry * math.sin(a_)
        d = d_ellipse(X, Y, px, py, 1.9, 1.2)
        cv.fill(aa(d, 1.1), "#7E848C", 0.32)
        cv.screen(aa(d_ellipse(X, Y, px - 0.5, py - 0.4, 0.8, 0.5), 0.7), "#FFFFFF", 0.18)
    hoop_side = side & (Y - (cy + ry * np.sqrt(np.clip(1 - u * u, 0, 1))) < thick * 0.55)
    cv.a[..., :3] = np.where(hoop_side[..., None], cv.a[..., :3] * 0.60 + np.array(rgb("#8A9098")) * 0.40, cv.a[..., :3])
    # light: a broad warm pool on the front half + a soft polished sheen band; the back falls off gently
    cv.screen(np.exp(-(((X - cx) / (rx * 0.80)) ** 2 + ((Y - cy - ry * 0.30) / (ry * 0.85)) ** 2)) * top, HK_GLOW, 0.34)
    sheen = np.exp(-(((X - cx + 30) / (rx * 0.55)) ** 2 + ((Y - cy + ry * 0.05) / (ry * 0.22)) ** 2))
    cv.screen(sheen * top, "#FFFFFF", 0.22)
    cv.multiply(np.clip(-v, 0, 1) ** 1.6 * top, "#8A6844", 0.16)
    for fx, fy in DIGGER_FEET:
        g = np.exp(-(((X - fx) / 30.0) ** 2 + ((Y - fy - 1.5) / 7.0) ** 2) * 1.4)
        core = np.exp(-(((X - fx) / 18.0) ** 2 + ((Y - fy - 1.0) / 4.0) ** 2) * 1.6)
        cv.multiply(np.clip(g * 0.7 + core * 0.45, 0, 1), "#6A4A2A", 0.62)
    return cv.image()


def build_floor_hk(ctx):
    return _dof(paint_floor_hk(), 0.60)


BUILDS["homeWorkshop"] = build_workshop_hk
BUILDS["homeFloor"] = build_floor_hk


def build_cabinet_hk(ctx):
    """homeCabinet (LOOK-2 high-key): the same cabinet from the same camera (cabinet_hk: a light interior), a brighter
    fill, the lantern's glow on the lighter back wall; mapped onto F_CABINET exactly like build_cabinet."""
    spec = _cabinet_spec()
    spec["scene"] = [(_M, "cabinet_hk", dict(center=False))]
    spec["light"] = rig(key_lux=2100.0, fill_lux=1100.0, shadow=False, key_color=(1.0, 0.95, 0.86),
                        fill_color=(0.95, 0.97, 0.94), env=d1_env())
    ims = ctx.render({"cabinetD1hk": spec})
    im = ims["cabinetD1hk"]
    bb = alpha_bbox(im)
    out = _SH._paste_mapped(im, bb, F_CABINET)
    cv = Canvas(F_CABINET[2] - F_CABINET[0], F_CABINET[3] - F_CABINET[1])
    cv.over(out)
    X, Y = cv.X + F_CABINET[0], cv.Y + F_CABINET[1]
    win = aa(d_rrect(X, Y, 117, 395, 275, 509, 10), 1.0)
    g = np.exp(-(((X - 183) / 50.0) ** 2 + ((Y - 412) / 42.0) ** 2))
    cv.screen(g * win, "#FFD98A", 0.40)
    g2 = np.exp(-(((X - 196) / 80.0) ** 2 + ((Y - 460) / 60.0) ** 2))
    cv.screen(g2 * win, HK_GLOW, 0.18)
    for cx, cy, rx, ry, a in ((128, 404, 12, 7, 0.34), (262, 402, 7, 5, 0.22)):
        gg = np.exp(-(((X - cx) / rx) ** 2 + ((Y - cy) / ry) ** 2) * 1.6)
        cv.screen(gg, "#FFFBF0", a)
    return cv.image()


BUILDS["homeCabinet"] = build_cabinet_hk


# ====================================================================== LOOK-2 FIX ROUND: a SATURATED high-key ground
# The two judges on the LOOK-2 home (build/p/LOOK2/judge + J-copy-home, 2026-09-29):
#   finish #1  the ground is "washed-out pastel sea-glass" (MEASURED C* 31 vs 45; wall 27 vs 42; background gamut_fill
#              0.445 < 0.487, L_std 14.2 < 15.2) -> keep it light, push CHROMA: a clear turquoise plank wall (C* ~40),
#              deeper plank joints, a darker lower stone band (value range), a saturated honey wainscot + floor
#   copy       "the high-key ground copies the original's LIGHT LAYOUT" (every home crop moved toward 002; art-only SSIM
#              0.3135 FAIL, crew band 0.337 FAIL): their bright wall behind the monster + their pale oval platform with a
#              light rim. -> the brightest light is a DAYLIGHT CORNER at the top right (a window light falling down the
#              right wall, fading before the foreman), the wall behind his head stays a MID saturated turquoise; the
#              floor pad is a mid-value honey oak with a DARK IRON rim (never a pale disc with a pale rim), in a warm
#              umber floor, with a warm pool of lamp light on its front (finish #10) and a satin sheen
#   finish #11 unlit ghost lanterns -> warm emissive glass with a small glow halo (2-D, over R3's objects render)
# Same composition, objects and UI rects as ever (ruling 46): only colour, value placement and surface detail change.
HK2_PLANK = [(0.00, "#066E76"), (0.22, "#058C8E"), (0.45, "#08AEAA"), (0.62, "#12C2BA"), (0.80, "#3CDACE"),
             (0.92, "#8CEADE"), (1.00, "#D6FAF0")]     # (r2: the mid stops ~5 C* richer at the same luma: wall C* -> ~40)
HK2_JOINT = "#0A4C52"          # a deep teal groove (deeper than LOOK-2's #3F7C76: the joints give the wall its value range)
HK2_STONE = [(0.0, "#065A62"), (0.35, "#0A747A"), (0.7, "#0E8E8E"), (1.0, "#18A8A2")]
HK2_MORTAR = "#073A40"
HK2_PLINTH = [(0.0, "#0B4E54"), (0.5, "#11666A"), (1.0, "#1A7C7C")]
HK2_HONEY = [(0.0, "#B7782E"), (0.35, "#D18E38"), (0.7, "#E4A548"), (1.0, "#F0BC66")]     # wainscot: saturated honey
HK2_TJOINT = "#7A4A1A"
HK2_EARTH = [(0.0, "#B07C4A"), (0.35, "#C48E58"), (0.7, "#D2A068"), (1.0, "#E0B07A")]    # floor apron: warm umber-honey
HK2_DAY = "#F2FFF8"            # the daylight (a cool white in the wall's own hue family)
HK2_LAMP = "#FFC45C"           # lantern glow
LANTERN_GLOBES = ((140.1, 110.8), (254.1, 110.8))
HK2_PLANK_SEED = 170           # the board joints: one at x ~150 and one at ~252, flanking the foreman's head (a joint
                               # behind a flat stretch of the original's wall breaks its match in the boss-head crop)     # R3's wall lanterns: the glass globe centres (pt, measured)


def _light_hk2(X, Y):
    """The wall's light field t in [0, 1] (0 = the far shade, 1 = the daylight corner): a mid base, the daylight
    falling from the TOP-RIGHT corner down the right wall (fades before the foreman's head), two small warm lamp pools,
    a fall-off toward the left and the ledge."""
    base = 0.42 + 0.05 * np.exp(-(((X - 196.5) / 150.0) ** 2))
    ax, ay = -0.36, 0.93                                  # the shaft: from the corner, steeply down the right wall
    ox, oy = 372.0, -10.0
    t_ = (X - ox) * ax + (Y - oy) * ay
    n_ = -(X - ox) * ay + (Y - oy) * ax
    shaft = np.exp(-(n_ / (46.0 + 0.22 * np.clip(t_, 0, None))) ** 2) * smooth(t_, -30, 30) * (1 - smooth(t_, 150, 270))
    corner = np.exp(-(((X - 400.0) / 170.0) ** 2 + ((Y + 20.0) / 210.0) ** 2))
    right = smooth(X, 235, 320) * (1 - smooth(Y, 160, 250))          # the whole right wall catches the window light
    lamps = sum(np.exp(-(((X - lx) / 26.0) ** 2 + ((Y - ly - 6.0) / 30.0) ** 2)) for lx, ly in LANTERN_GLOBES)
    fall = 0.16 * np.clip((196.5 - X) / 196.5, 0, 1) ** 1.5 + 0.10 * smooth(Y, 150, 245)
    return np.clip(base + 0.46 * shaft + 0.55 * corner + 0.30 * right + 0.08 * lamps - fall, 0, 1)


def paint_workshop_hk2():
    cv = Canvas(393, 852, color="#18AAA8")
    X, Y = cv.X, cv.Y
    h, w = cv.h, cv.w
    col = np.zeros((h, w, 3))
    ly = ledge_y(X)
    ry = rim_y(X)
    rb = ry + 11.0
    up = Y < ly
    # ---------------- upper wall: turquoise planks, the value from the corner daylight; strong board-to-board tone
    edges, pi = _planks_v(X, Y, -6, 400, seed=HK2_PLANK_SEED, wmin=30.0, wmax=40.0)
    rng = np.random.default_rng(11)
    tone = rng.uniform(-0.085, 0.085, len(edges))[pi]
    L = _light_hk2(X, Y)
    gr = _grain(h, w, 6, 140, 3)
    gr2 = _grain(h, w, 14, 90, 19)             # a soft painted-board streak (a few pt wide, along the board)
    col[:] = stops_interp(np.clip(L + tone * 0.9 + 0.012 * gr + 0.030 * gr2, 0, 1), HK2_PLANK)
    # ---------------- below the ledge: a darker turquoise stone band (value range under the bright upper wall)
    below = Y > ly + 10
    ls = np.clip(0.55 + 0.25 * np.exp(-(((X - 330.0) / 110.0) ** 2)) - 0.20 * np.clip((196.5 - X) / 196.5, 0, 1), 0, 1)
    col[below] = stops_interp(ls, HK2_STONE)[below]
    # ---------------- wainscot: saturated honey planks (lit from the right)
    wm = (Y > rb) & (Y <= WAINSCOT_BOTTOM)
    ph = 13.2
    WTOP = 361.0
    prow = np.floor((Y - WTOP) / ph)
    rng2 = np.random.default_rng(5)
    rowtone = rng2.uniform(-0.11, 0.11, 64)
    wtone = rowtone[np.clip(prow.astype(int), 0, 63)]
    wl = np.clip(0.60 + 0.40 * np.exp(-(((X - 340.0) / 120.0) ** 2)) - 0.25 * np.clip((196.5 - X) / 196.5, 0, 1) ** 1.3, 0, 1)
    col[wm] = stops_interp(np.clip(wl + wtone + 0.02 * _grain(h, w, 110, 4, 9), 0, 1), HK2_HONEY)[wm]
    # ---------------- plinth: dark teal limestone
    sm = (Y > WAINSCOT_BOTTOM) & (Y <= FLOOR_Y)
    pl_ = np.clip(0.45 + 0.35 * np.exp(-(((X - 300.0) / 140.0) ** 2)) - 0.25 * np.clip((196.5 - X) / 196.5, 0, 1), 0, 1)
    col[sm] = stops_interp(pl_, HK2_PLINTH)[sm]
    # ---------------- floor apron: warm umber-honey, brighter toward the front right
    fm = Y > FLOOR_Y
    fl = np.clip(0.35 + 0.45 * smooth(Y, 585, 800) + 0.15 * np.exp(-(((X - 300.0) / 160.0) ** 2)), 0, 1)
    col[fm] = stops_interp(fl, HK2_EARTH)[fm]
    cv.a[..., :3] = col
    cv.a[..., 3] = 1.0
    for e in edges:                       # deep, soft plank grooves + a lit lip on the right of each groove
        d = np.abs(X - e)
        cv.multiply(aa(d - 1.3, 1.1) * up, HK2_JOINT, 0.80)
        cv.screen(aa(np.abs(X - e - 2.4) - 0.8, 1.1) * up, HK2_DAY, 0.10 + 0.20 * L)
    # the header beam (honey)
    hb0, hb1 = 26.0, 42.0
    hbm = (Y > hb0) & (Y <= hb1)
    tb = np.clip((Y - hb0) / (hb1 - hb0), 0, 1)
    beam = stops_interp(np.clip(0.95 - 0.75 * tb + 0.02 * _grain(h, w, 90, 4, 21), 0, 1), HK2_HONEY)
    cv.a[..., :3] = np.where(hbm[..., None], beam, cv.a[..., :3])
    cv.multiply(aa(np.abs(Y - hb1) - 0.6, 0.9), HK2_TJOINT, 0.55)
    cv.multiply(smooth(-(Y - hb1), -14, 0) * (Y > hb1) * up, HK2_JOINT, 0.35)
    for bx in (18, 104, 196.5, 289, 375):
        for by in (31.0, 37.0):
            r = np.sqrt((X - bx) ** 2 + (Y - by) ** 2)
            cv.fill(aa(r - 1.9, 0.8), "#5E6268", 0.85)
    # the mid batten
    mb0, mb1 = 128.0, 135.0
    mbm = (Y > mb0) & (Y <= mb1)
    tm = np.clip((Y - mb0) / (mb1 - mb0), 0, 1)
    bat = stops_interp(np.clip(0.9 - 0.7 * tm, 0, 1), HK2_HONEY)
    cv.a[..., :3] = np.where(mbm[..., None], bat, cv.a[..., :3])
    cv.multiply(aa(np.abs(Y - mb1) - 0.5, 0.9), HK2_TJOINT, 0.50)
    cv.multiply(smooth(-(Y - mb1), -9, 0) * (Y > mb1) * up, HK2_JOINT, 0.30)
    # the lamp glow: warm pools round the two lanterns (over planks + batten)
    for lx, lyy in LANTERN_GLOBES:
        cv.screen(np.exp(-(((X - lx) / 22.0) ** 2 + ((Y - lyy - 4) / 26.0) ** 2)) * up, HK2_LAMP, 0.42)
    # ---------------- the ledge
    lip = (Y > ly) & (Y <= ly + 10)
    tl = np.clip((Y - ly) / 10.0, 0, 1)
    lipcol = stops_interp(np.clip(0.98 - 0.8 * tl, 0, 1), HK2_HONEY)
    cv.a[..., :3] = np.where(lip[..., None], lipcol, cv.a[..., :3])
    cv.multiply(smooth(Y, ly - 16, ly) * (Y <= ly), HK2_JOINT, 0.34)
    cv.multiply(aa(np.abs(Y - ly) - 0.5, 0.8), HK2_TJOINT, 0.50)
    cv.multiply(aa(np.abs(Y - ly - 10.2) - 0.6, 0.9), HK2_TJOINT, 0.55)
    # ---------------- stone courses + plinth
    lower = (Y > ly + 10) & (Y < ry)
    _masonry_hk(cv, X, Y, lower, 0.0, 24.0, 41, cv.a[..., :3].copy(), HK2_MORTAR, amp=0.16)
    cv.multiply(smooth(-(Y - ly - 10), -18, 0) * lower, HK2_MORTAR, 0.40)
    plinth_m = (Y > WAINSCOT_BOTTOM + 6) & (Y <= FLOOR_Y)
    _masonry_hk(cv, X, Y, plinth_m, WAINSCOT_BOTTOM + 6, 27.0, 43, cv.a[..., :3].copy(), HK2_MORTAR, amp=0.17)
    # ---------------- the deck beam
    rimm = (Y > ry) & (Y <= rb)
    tr = np.clip((Y - ry) / 11.0, 0, 1)
    rimcol = stops_interp(np.clip(0.98 - 0.8 * tr, 0, 1), HK2_HONEY)
    cv.a[..., :3] = np.where(rimm[..., None], rimcol, cv.a[..., :3])
    cv.multiply(aa(np.abs(Y - ry) - 0.5, 0.8), HK2_TJOINT, 0.5)
    cv.multiply(aa(np.abs(Y - rb) - 0.6, 0.8), HK2_TJOINT, 0.6)
    # ---------------- wainscot seams
    fy = (Y - WTOP) / ph
    dseam = (fy - np.floor(fy)) * ph
    cv.multiply(aa(np.minimum(dseam, ph - dseam) - 0.8, 1.0) * wm, HK2_TJOINT, 0.62)
    cv.screen(aa(np.abs(dseam - 1.6) - 0.5, 0.9) * wm, "#FFF1CF", 0.16)
    rng4 = np.random.default_rng(13)
    joff = rng4.uniform(0, 120, 64)
    jw = rng4.uniform(130, 200, 64)
    rr = np.clip(prow.astype(int), 0, 63)
    ju = (X + joff[rr]) / jw[rr]
    jd = np.minimum(ju - np.floor(ju), np.ceil(ju) - ju) * jw[rr]
    cv.multiply(aa(jd - 0.6, 0.9) * wm, HK2_TJOINT, 0.45)
    cv.multiply(smooth(-(Y - rb), -14, 0) * wm, HK2_TJOINT, 0.38)
    cv.multiply(smooth(Y, WAINSCOT_BOTTOM - 10, WAINSCOT_BOTTOM) * wm, HK2_TJOINT, 0.25)
    # ---------------- the plinth's cap strip
    cap = (Y > WAINSCOT_BOTTOM) & (Y <= WAINSCOT_BOTTOM + 6)
    tc = np.clip((Y - WAINSCOT_BOTTOM) / 6.0, 0, 1)
    capcol = stops_interp(np.clip(0.95 - 0.8 * tc, 0, 1), HK2_HONEY)
    cv.a[..., :3] = np.where(cap[..., None], capcol, cv.a[..., :3])
    cv.multiply(smooth(-(Y - WAINSCOT_BOTTOM - 6), -12, 0) * plinth_m, HK2_MORTAR, 0.35)
    cv.multiply(smooth(Y, FLOOR_Y - 14, FLOOR_Y) * plinth_m, HK2_MORTAR, 0.30)
    # ---------------- the floor: a contact line at the wall, broad packed-earth mottling (large, soft: no pebbles)
    cv.multiply(aa(np.abs(Y - FLOOR_Y) - 0.8, 1.0), "#4A2C12", 0.45)
    cv.multiply(smooth(-(Y - FLOOR_Y), -18, 0) * fm, "#5A3A1A", 0.30)
    nz = noise2(h, w, 70, seed=61)
    cv.a[..., :3] = np.where(fm[..., None], cv.a[..., :3] * (1 + 0.06 * nz[..., None]), cv.a[..., :3])
    # a light vignette in the wall's own deep teal (left + top corners), the right corner stays lit
    vx = np.clip((196.5 - X) / 196.5, 0, 1) ** 2
    vy = ((Y - 380) / 470) ** 2
    cv.multiply(np.clip(vx * 0.55 + vy * 0.30, 0, 1) * (Y < FLOOR_Y), "#0A4A4E", 0.45)
    cv.multiply(smooth(-Y, -110, 0) * np.clip(1.2 - X / 330.0, 0, 1), "#0A4A4E", 0.30)
    return cv


def _lanterns_lit(cv):
    """finish #11: the two wall lanterns lit -- a warm emissive globe (hot core, amber rim) over R3's pale glass, and a
    small halo on the planks round it (painted OVER the objects render, before the depth of field)."""
    X, Y = cv.X, cv.Y
    for gx, gy in LANTERN_GLOBES:
        d = d_ellipse(X, Y, gx, gy, 4.5, 5.2)
        core = np.exp(-(((X - gx) / 2.6) ** 2 + ((Y - gy + 0.4) / 3.2) ** 2))
        glass_ = stops_interp(np.clip(core, 0, 1), [(0.0, "#F29A2E"), (0.45, "#FFC658"), (0.8, "#FFE7A2"), (1.0, "#FFF8E4")])
        m = aa(d, 0.6)
        cv.a[..., :3] = cv.a[..., :3] * (1 - m[..., None]) + glass_ * m[..., None]
        cv.screen(np.exp(-(((X - gx) / 11.0) ** 2 + ((Y - gy) / 12.0) ** 2)) * (1 - m), HK2_LAMP, 0.55)
        cv.screen(np.exp(-(((X - gx) / 5.0) ** 2 + ((Y - gy) / 6.0) ** 2)), "#FFF3D0", 0.35)


def build_workshop_hk2(ctx, objects=None):
    """homeWorkshop (LOOK-2 fix round): the saturated high-key painted structure + R3's wall objects (regraded as in
    LOOK-2) + shadows, the lanterns lit, then the backdrop's depth of field."""
    if objects is None:
        objects = _Image.open(HK_OBJECTS_RAW).convert("RGBA").resize((1179, 2556), _Image.LANCZOS)
    objects = _objects_hk(objects)
    cv = paint_workshop_hk2()
    mp = _os.path.join(K_OUT, "homeCabinet@3x.png")
    if _os.path.exists(mp):
        mim = _Image.open(mp).convert("RGBA")
        sh, (ox, oy) = shadow_of(mim, 6, 10, 18, 0.40, color="#3A2210", grow_px=6)
        cv.over(sh, x=F_CABINET[0] * PX + ox, y=F_CABINET[1] * PX + oy)
    sh, (ox, oy) = shadow_of(objects, 7, 9, 10, 0.34, color="#063A3E")
    cv.over(sh, x=ox, y=oy)
    cv.over(objects)
    _lanterns_lit(cv)
    # the foreman's soft cast shadow on the planks behind him, down-left of him (the daylight comes from the top-right
    # corner): the wall right behind his head stays a mid / deep turquoise, never a bright halo
    bp = _os.path.join(K_OUT, "char_boss_home@3x.png")
    if _os.path.exists(bp):
        bim = _Image.open(bp).convert("RGBA")
        sh, (ox, oy) = shadow_of(bim, -36, 30, 16, 0.50, color="#06363A", grow_px=4)
        cv.over(sh, x=int(BOSS_PLACE[0] * PX) + ox, y=int(BOSS_PLACE[1] * PX) + oy)
    return _dof(cv.image())


def paint_floor_hk2():
    """homeFloor (LOOK-2 fix round): the same round plank work-pad in its hoop, same place and size -- a MID-value honey
    oak (planks with a visible tone step, soft seams, fine grain) inside a DARK IRON hoop with brass rivets, on the warm
    umber floor; a warm pool of lamp light on the pad's front half and a satin sheen band; the Diggers' contact
    shadows."""
    cv = Canvas(F_FLOOR[2] - F_FLOOR[0], F_FLOOR[3] - F_FLOOR[1])
    X, Y = cv.X + F_FLOOR[0], cv.Y + F_FLOOR[1]
    h, w = cv.h, cv.w
    x0, y0, x1, y1 = PAD_BOX
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2 - 3.0
    rx, ry = (x1 - x0) / 2, (y1 - y0) / 2 - 3.0
    thick = 7.0
    u, v = (X - cx) / rx, (Y - cy) / ry
    r = np.sqrt(u * u + v * v)
    vs = (Y - cy - thick) / ry
    rs = np.sqrt(u * u + vs * vs)
    side = (rs <= 1.0) & (r > 1.0) & (Y > cy)
    g = aa(d_ellipse(X, Y, cx + 2, cy + thick + 3, rx + 6, ry + 5), 10.0)
    cv.fill(g, "#3E2410", 0.40)
    cv.fill(aa(d_ellipse(X, Y, cx, cy, rx + 4, ry + 3), 4.0), "#4A2E16", 0.35)     # a soft dark bed round the hoop
    npl = 9
    pv = (v + 1) / 2 * npl
    k = np.floor(pv)
    fv = pv - k
    rng = np.random.default_rng(17)
    tones = rng.uniform(-0.07, 0.07, npl + 2)
    tones[::2] += 0.04                         # alternate boards a visible step apart (coarse structure, soft seams)
    tone = tones[np.clip(k.astype(int), 0, npl + 1)]
    gr = _grain(h, w, 70, 2, 5) + 0.6 * _grain(h, w, 24, 2, 8)      # + a finer grain (the floor's fine texture)
    lit = np.clip(0.49 + 0.34 * np.exp(-(((X - cx) / (rx * 0.75)) ** 2 + ((Y - cy - ry * 0.35) / (ry * 0.70)) ** 2))
                  + 0.08 * v, 0, 1)
    face = stops_interp(np.clip(lit + tone + 0.035 * gr, 0, 1),
                        [(0.0, "#94602E"), (0.35, "#B47C42"), (0.6, "#CE9658"), (0.85, "#E4B070"), (1.0, "#F2C688")])
    top = r <= 1.0
    col = np.zeros((h, w, 3))
    col[top] = face[top]
    sidecol = stops_interp((Y - cy) / (ry + thick), [(0, "#6A4424"), (0.8, "#553418"), (1.0, "#3E2410")])
    col[side] = sidecol[side]
    alpha = np.clip(aa((r - 1.0) * min(rx, ry), 1.6) + aa((rs - 1.0) * min(rx, ry), 1.6) * (Y > cy), 0, 1)
    src = np.zeros((h, w, 4))
    src[..., :3] = col
    src[..., 3] = alpha
    cv.over(src)
    seam_pt = np.minimum(fv, 1 - fv) * (2 * ry / npl)
    on = top & (r < 0.915)
    cv.multiply(aa(seam_pt - 1.0, 2.6) * on, "#6A4018", 0.22)
    joff = rng.uniform(0, 1, npl + 2)
    jl = rng.uniform(0.55, 0.9, npl + 2)
    kk = np.clip(k.astype(int), 0, npl + 1)
    ju = (u + 1 + joff[kk]) / jl[kk]
    jd = np.minimum(ju - np.floor(ju), np.ceil(ju) - ju) * jl[kk] * rx
    cv.multiply(aa(jd - 1.0, 2.4) * on, "#6A4018", 0.16)
    # the hoop: DARK iron, a lit upper lip, brass rivets
    # (soft-edged: a dark band read, not a hard black line -- the floor's fine edge energy is S4)
    hw = np.clip((r - 0.915) / 0.026, 0, 1) * top
    hp = stops_interp(v, [(-1.0, "#463C32"), (0.2, "#54483C"), (1.0, "#625444")])      # a dark bronze-iron hoop (a lighter
    # one cut the floor's edge energy but gave back the original's structure: the real-UI scene band 0.2707 > 0.27)
    cv.a[..., :3] = cv.a[..., :3] * (1 - hw[..., None]) + hp * hw[..., None]
    cv.screen(np.exp(-((r - 0.962) / 0.016) ** 2) * top * (v < 0.3), "#C8B090", 0.16)
    for a_ in np.linspace(-math.pi, math.pi, 13)[:-1]:
        px, py = cx + 0.962 * rx * math.cos(a_), cy + 0.962 * ry * math.sin(a_)
        d = d_ellipse(X, Y, px, py, 1.8, 1.2)
        cv.fill(aa(d, 1.4), "#A88040", 0.45)
    hoop_side = side & (Y - (cy + ry * np.sqrt(np.clip(1 - u * u, 0, 1))) < thick * 0.55)
    cv.a[..., :3] = np.where(hoop_side[..., None], cv.a[..., :3] * 0.8 + np.array(rgb("#4E453B")) * 0.2, cv.a[..., :3])
    # light: a warm lamp pool on the front half + a satin sheen band across the middle; the back edge in shade
    cv.screen(np.exp(-(((X - cx) / (rx * 0.82)) ** 2 + ((Y - cy - ry * 0.40) / (ry * 0.66)) ** 2)) * (r < 0.93), "#FFD890", 0.46)
    sheen = np.exp(-(((X - cx - 55) / (rx * 0.42)) ** 2 + ((Y - cy + ry * 0.02) / (ry * 0.16)) ** 2))
    cv.screen(sheen * (r < 0.9), "#FFF4DC", 0.26)
    cv.multiply(np.clip(-v, 0, 1) ** 1.4 * (r < 0.93), "#6A3E18", 0.26)
    for fx, fy in DIGGER_FEET:
        g = np.exp(-(((X - fx) / 32.0) ** 2 + ((Y - fy - 1.5) / 7.5) ** 2) * 1.4)
        core = np.exp(-(((X - fx) / 19.0) ** 2 + ((Y - fy - 1.0) / 4.2) ** 2) * 1.6)
        cv.multiply(np.clip(g * 0.7 + core * 0.45, 0, 1), "#3E2410", 0.70)
    return cv.image()


HK2_FLOOR_GRAIN = 0.0055        # a fine timber / earth grain laid on AFTER the depth of field (the finish judge #10:
                                # "over-smoothed ... fine grain"; MEASURED floor Laplacian 0.21 < 0.34)


def build_floor_hk2(ctx):
    im = _dof(paint_floor_hk2(), 0.80)
    a = np.asarray(im).astype(np.float64) / 255
    rng = np.random.default_rng(71)
    n = blur(rng.standard_normal(a.shape[:2]), 0.7)
    n = n / (n.std() + 1e-9)
    a[..., :3] = np.clip(a[..., :3] * (1 + HK2_FLOOR_GRAIN * n[..., None]), 0, 1)
    return _Image.fromarray((a * 255 + 0.5).astype(np.uint8), "RGBA")


BUILDS["homeWorkshop"] = build_workshop_hk2
BUILDS["homeFloor"] = build_floor_hk2


# ---------------------------------------------------------------------- homeScaffold (LOOK-2 fix round)
# finish #5 "the home boss floats": his round coat belly ended in mid-air below the lower rail, the wall showing between
# it and the ledge (no legs, no seat). -> a boarded plank APRON between the posts from the lower rail (the brace) down
# onto the deck beam, behind the brace and the posts (the lower body is behind it, the way a workbench hides it). The
# station itself is the home6 render (the lever's wooden T-handle, no ball knob), same camera, same registration.
STATION_SRC6 = _os.environ.get("MF_STATION6", _os.path.join(_os.path.dirname(_BUILD), "route3d", "char_bossStation6.png"))


def _apron(fw, fh):
    """The plank apron (frame F_SCAFFOLD, @3x RGBA float): vertical honey boards, soft seams, a grain, the brace's
    shadow along the top, darker toward the deck, an iron strap with rivets."""
    cv = Canvas(fw, fh)
    X, Y = cv.X + F_SCAFFOLD[0], cv.Y + F_SCAFFOLD[1]
    h, w = cv.h, cv.w
    x0, x1 = BOSS_PLACE[0] + POSTS[0][1] - 1.5, BOSS_PLACE[0] + POSTS[1][0] + 1.5
    y0 = BOSS_PLACE[1] + BRACE_ROWS[0] + 2.0
    y1 = rim_y(X) + 1.5
    m = (X >= x0) & (X <= x1) & (Y >= y0) & (Y <= y1)
    edges, pi = _planks_v(X, Y, x0, x1 + 30, seed=29, wmin=21.0, wmax=27.0)
    rng = np.random.default_rng(31)
    tone = rng.uniform(-0.07, 0.07, len(edges))[pi]
    gr = _grain(h, w, 5, 120, 33)
    t = np.clip(0.62 + tone + 0.035 * gr - 0.30 * smooth(Y, y0 + 4, y0 + 26) * 0.5, 0, 1)
    col = stops_interp(t, [(0.0, "#7A4A1E"), (0.35, "#A8703A"), (0.7, "#C99050"), (1.0, "#E2AE6C")])
    src = np.zeros((h, w, 4))
    src[..., :3] = col
    src[..., 3] = m.astype(float)
    cv.over(src)
    inside = m.astype(float)
    for e in edges:
        cv.multiply(aa(np.abs(X - e) - 0.7, 0.9) * inside, "#5A3414", 0.55)
    cv.multiply(smooth(-(Y - y0), -9, 0) * inside, "#3E2410", 0.55)        # under the brace
    cv.multiply(smooth(Y, y1 - 8, y1) * inside, "#4A2C12", 0.30)            # toward the deck
    sy = y0 + (y1.mean() if np.ndim(y1) else y1) * 0 + 12.0
    strap = (np.abs(Y - sy) < 1.6) & m
    cv.a[..., :3] = np.where(strap[..., None], np.array(rgb("#4E545C")) * (1.1 - 0.25 * ((Y - sy + 1.6) / 3.2))[..., None],
                             cv.a[..., :3])
    for rx_ in np.linspace(x0 + 8, x1 - 8, 6):
        cv.fill(aa(d_ellipse(X, Y, rx_, sy, 1.1, 1.1), 0.6), "#C99640", 0.9)
    return cv.a


def build_scaffold6(ctx):
    st = np.asarray(_Image.open(STATION_SRC6).convert("RGBA")).astype(np.float64) / 255
    fw, fh = F_SCAFFOLD[2] - F_SCAFFOLD[0], F_SCAFFOLD[3] - F_SCAFFOLD[1]
    global STATION_SRC
    keep = STATION_SRC
    tmp = _os.path.join(_os.path.dirname(STATION_SRC6), "_station6_tmp.png")
    _Image.fromarray((st * 255 + 0.5).astype(np.uint8), "RGBA").save(tmp)
    STATION_SRC = tmp
    try:
        scaf = build_scaffold(ctx)          # the rail / brace / posts / shoes / contact shadows as before, on the home6 render
    finally:
        STATION_SRC = keep
        _os.remove(tmp)
    ap = _apron(fw, fh)
    cv = Canvas(fw, fh)
    cv.over(ap)
    cv.over(scaf)
    return cv.image()


BUILDS["homeScaffold"] = build_scaffold6
