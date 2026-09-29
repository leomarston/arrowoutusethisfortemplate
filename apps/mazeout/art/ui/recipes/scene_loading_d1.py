"""R4 LOADING (PLAN-P §4.2, owner items 1 + 15; SPEC rulings 37b / 44 / 46): the D1 "Burrow Works" Loading backdrop,
restyled with the SAME composition and object types as today's Loading (scene_loading.py, which stays the geometry
source: every line / box / homography below is imported from it). Ruling 46: keep the composition, change materials,
colours and details just enough that the copy gate passes -- never a new theme or layout. Object by object:

    purple barrel vault + faint ribs        -> deep-teal boarded vault (painted planks) under honey timber arch beams
                                               with iron bolts (the beams are our own spacing)
    dark slanted tubes / vertical pipe     -> copper pipes with brass collars (light on the dark vault: the tone flips)
    backlit opening (pale lilac, crates)   -> the yard doorway: warm daylight, a timber gantry + stacked crates in the
                                               haze, a hanging lantern; a heavy timber lintel over it
    violet mid wall / pillar / lit jamb    -> teal-grey masonry / a timber post with iron straps / a honey timber jamb
    back room under the press              -> a burrow tunnel into the rock, timber props, a hanging lantern (the
                                               light shaft is gone)
    the press (blue housing, pale lip,     -> the sorting machine: teal painted iron housing with rivets, an aged bronze
     magenta panel, lilac girder, buttons)     band, a bright copper sheet panel, a teal iron beam with brass rivets, two
                                               brass-ringed push buttons (the band tones no longer follow the old order)
    stepped lilac conveyor + hazard side   -> a timber dock: plank deck, a studded timber side (no stripes), a round
                                               plank drum top
    blue U pipe / paper sheets             -> (dropped: hidden by the logo) / a rolled-out tunnel map on the floor
    cardboard stack                        -> timber crates (3-D)
    glossy tiled floor                     -> hewn sandstone flags in earth joints (irregular: our own pattern)
    floor cable + plug                     -> a hemp rope along the bottom with a brass ring, ending in a loose coil (3-D)
    glossy flying block arrows (red tail,  -> the same block arrows in D1 enamel: tangerine tail, teal, sunflower and
     purple, pale green + blue)                cream-mint (3-D)
    violet contact shadows + reflections   -> warm earth contact shadows (flags do not mirror)

LOOK-L fix round 2 (2026-09-29; the finish judge on v3: washed out, a blown cream doorway, flat pale floor, dull arrow
sides): ONE saturated azure family (CIELAB hue 262-276) at mid values; the doorway a view OUT with depth (a canopy with
rafters, a far ridge, sheds, a water tower, a lattice headframe, two light shafts) at L* ~74; a mid-azure polished
floor with a lit centre, a deeper edge falloff, stronger reflections and MINE RAILS with a turnout (the hemp rope --
the original's cable spot -- is gone); the flying arrows' sides in a darker step of their own colour (a neutral-warm
dome, a weak rim); the top-left flight sunflower, the top-right coral, the small one saturated teal.

The cast (R2's D1 loading figures + the two dock Diggers built here) is placed by LAYOUT below; r4_loading.py writes
art/out/char_loading_layout.json from it (LoadingScreen reads that file generically) and composes the proofs.

Build (one render job at a time on the Mac, >= 1 GB free swap):
    PY=~/.venvs/mf3d/bin/python
    $PY art/ui/recipes/scene_make.py build loadingBackdrop char_digDockL --draft     # 0.4x -> build/ui-art/scene/draft/
    $PY art/review/tools/r4_loading.py proof                                          # compose + copygate vs store 8
"""
from __future__ import annotations

import json
import math
import os
import sys

import numpy as np
from PIL import Image, ImageFilter

import scene_loading as SL
from scene_loading import (sd_poly, rounded, polyline, band_t, layer, blur_over, floor_uv, _curve_poly, _catmull, W,
                           T_TOP, R_TOP, P_TOP, B_TOP, B_MID, B_BOT, BUTTONS, OPEN_X0, OPEN_TOP, OPEN_R, FLOOR_TOP,
                           B_WORLD)
from scene_kit import (Canvas, Part, aa, blur, cylinder, extrude, gloss, rbox, rgb, rig, rot_x, rot_y, rot_z, satin,
                       smooth, stops_interp, noise2, grid_part, torus, metal, box, ellipsoid, union)
from scene_kit import OUT as K_OUT

_M = sys.modules[__name__]

# ====================================================================== palette
# LOOK-L FIX ROUND 1 (the judges on v2: "the whole page is one dusty warm peach family ... no darks, no bright light
# pool, reads sepia"; the original pops because WARM characters sit on a COOL ground): a COOL CERULEAN works -- a deep
# cerulean boarded vault that frames the logo, cool blue stone walls, pale cool flags with a soft sheen -- lit by ONE
# warm-white daylight pool behind the boss (the tunnel exit), falling off to the edges; warm only as accents (the flying
# arrows, the machine's tangerine panel, brass, pale timber ribs, the rope). Never lavender / violet (LAB hue 280-340:
# the original's); our ground sits at LAB hue ~240-250, 85 deg from the mint crew (165), opposite the orange kit.
#
# LOOK-L FIX ROUND 2 (the finish judge on v3: "the page is washed out ... pale blue-grey, low in colour" -- C* mean 26.7
# vs the original's 39.5, 20 % of pixels above L*85; the doorway a blown cream slab; the floor large, flat and pale):
# ONE SATURATED AZURE family (CIELAB hue 262-276, below the 280-340 violet band) at MID values -- the vault a deep
# cobalt at the crown that lifts to a clear azure toward the light, painted-timber ribs, posts and jamb in a lighter
# azure of the SAME family (no pale bleached timber: the upper ground's hue spread), mid-azure stone walls, a mid-blue
# polished floor with a lit centre that falls off to deeper blue at the edges; the doorway toned down to L* ~75-82 with
# depth (a warm-to-cool gradient, far rafters, soft light shafts). Warm only on the cast, the flying arrows and small
# accents (brass, the lantern, the tunnel lamp). Every hex below was picked in CIELAB (build/p/LOOK/F2/lch2hex.py).
VAULT = ("#1790EA", "#0080D7", "#006EB8", "#005D9A", "#004F80", "#00385B")   # L* 58 -> 22, C* 54 -> 26, h 266-273
RIB = ("#CBDFF2", "#AED0F0", "#8EC0F2", "#6BB0F3", "#4BA0F0")        # painted timber, a lighter azure (L* 88 -> 64)
WALLB = ("#7FBBF3", "#66A6E0", "#549BD8", "#3E8BCF", "#2F76B5")      # mid azure stone (L* 74 -> 48, C* 34-42)
STEEL = ("#DCEBF8", "#B7D6EE", "#9DC6E8", "#7EB1D8", "#5B96C4")      # light azure enamel (the machine housing)
TANG = ("#6BB0F3", "#4BA0F0", "#1790EA", "#0080D7")                  # the machine's azure enamel panel
BRASS = ("#FFEBB0", "#F2C872", "#DFAE55", "#B98A36")
COPPER = ("#FFD2A8", "#F4AE78", "#DE8E58", "#B8683A")
DOCKWOOD = ("#F6D9A8", "#E9C088", "#D2A066", "#A87A48", "#7E5630")   # the dock: the room's one warm timber (small, low)
PLASTER = VAULT
TIMBER = DOCKWOOD
STONE = WALLB
ENAMEL = STEEL
BEAM = ("#1790EA", "#006EB8", "#005D9A", "#004169")                  # the sorting machine's cobalt iron beam
IRON = "#3D6B9A"
LANTERN = "#FFE7A8"
WARM = "#FFF8EC"
POOL = "#F4EEE2"                                                     # the doorway light on the floor (L* ~94)
SAND = ("#7FBBF3", "#61ACED", "#4C9BE0", "#3E8BCF", "#2F76B5")       # the floor: mid azure polished stone (C* 34-42)
HAZE = "#B7D6EE"

# D1 enamel for the flying block arrows: (face, shade, rim, highlight) -- the 3d-home_d1 families
BLOCK_SHADES_D1 = {
    # fix round 2 (the finish judge: the arrows' side faces read "a dull grey-tan or mauve ... like another material"):
    # every shade / rim is a DARKER SATURATED step of its own face colour (a yellow face -> a #C77E00-class side), and
    # the sprites render under a neutral-warm dome (FLY_ENV) instead of the lab's lilac one
    "tangerine": ("#FF9A12", "#E07000", "#B45200", "#FFB23C"),
    "teal": ("#17B3A3", "#0C9888", "#066B62", "#3CCCBC"),
    "sunflower": ("#FFCB2F", "#E9A200", "#C77E00", "#FFDA50"),
    "mint": ("#9FE3C8", "#6CC7A6", "#3E9A7C", "#D2F5E6"),
    "coral": ("#FA5A40", "#E03A20", "#B02410", "#FF7A5E"),
}


def _grain(h, w, sx_px, sy_px, seed):
    """Wood grain: value noise stretched along one axis, in [-1, 1]."""
    rng = np.random.default_rng(seed)
    gh, gw = max(4, h // max(1, sy_px) + 3), max(4, w // max(1, sx_px) + 3)
    g = rng.standard_normal((gh, gw))
    im = Image.fromarray(((g - g.min()) / (np.ptp(g) + 1e-9) * 255).astype(np.uint8)).resize((gw * sx_px, gh * sy_px),
                                                                                              Image.BICUBIC)
    return np.asarray(im).astype(np.float64)[:h, :w] / 127.5 - 1


def _hash(a, b, k=12.9898):
    return (np.sin(a * k + b * 78.233) * 43758.5453) % 1.0


def ptube(cv, pts, width, dark, mid, light, hi=None, alpha=1.0, soft=0.5, light_side=1.0):
    """SL.tube on the canvas (a painted cylinder along a polyline)."""
    SL.tube(cv, pts, width, dark, mid, light, hi=hi, alpha=alpha, soft=soft, light_side=light_side)


def copper_pipe(cv, pts, width, collars=(), alpha=1.0):
    """A pale copper pipe (lit band up-left, a soft lower edge) with brass collars at the given arc fractions."""
    ptube(cv, pts, width, COPPER[3], COPPER[2], COPPER[0], hi="#FFF0DE", alpha=alpha)
    if not collars:
        return
    P = np.asarray(pts, float)
    seg = np.hypot(*np.diff(P, axis=0).T)
    cum = np.concatenate([[0], np.cumsum(seg)])
    for f in collars:
        s = f * cum[-1]
        i = int(np.clip(np.searchsorted(cum, s) - 1, 0, len(P) - 2))
        t = (s - cum[i]) / max(seg[i], 1e-6)
        c = P[i] + (P[i + 1] - P[i]) * t
        d = (P[i + 1] - P[i]) / max(seg[i], 1e-6)
        a = c - d * 2.6
        b = c + d * 2.6
        ptube(cv, [tuple(a), tuple(b)], width * 1.32, BRASS[3], BRASS[2], BRASS[0], hi="#FFF8E0", alpha=alpha)


def masonry(cv, mask, y0, course, seed, base, mortar="#CDB58C", lit="#FFF8EA", wmin=30, wmax=64, light=1.0,
            mortar_k=0.40):
    """Sandstone courses, calm: staggered blocks, a small per-block value drift, LIGHT mortar joints, a soft lit top
    edge (LOOK-L: R4's dark mortar was the busiest structure behind the boss)."""
    X, Y = cv.X, cv.Y
    h, w = cv.h, cv.w
    rng = np.random.default_rng(seed)
    row = np.floor((Y - y0) / course).astype(int)
    nrow = int(max(row.max(), 0)) + 2
    offs = rng.uniform(0, 70, nrow + 1)
    widths = rng.uniform(wmin, wmax, nrow + 1)
    rr = np.clip(row, 0, nrow)
    u = (X + offs[rr]) / widths[rr]
    blk = np.floor(u)
    lx = (u - blk) * widths[rr]
    ly = ((Y - y0) / course - row) * course
    key = (rr * 131 + blk.astype(int) * 17) % 97
    h1 = _hash(key, 0.0) - 0.5
    bw = widths[rr]
    r = 2.4
    qx = np.abs(lx - bw / 2) - (bw / 2 - 1.1 - r)
    qy = np.abs(ly - course / 2) - (course / 2 - 1.1 - r)
    dbox = np.sqrt(np.maximum(qx, 0) ** 2 + np.maximum(qy, 0) ** 2) + np.minimum(np.maximum(qx, qy), 0) - r
    col = base * (1 + 0.06 * h1[..., None])
    m = np.clip(mask, 0, 1)
    cv.a[..., :3] = cv.a[..., :3] * (1 - m[..., None]) + col * m[..., None]
    inside = aa(dbox, 0.9)
    cv.multiply((1 - inside) * m, mortar, mortar_k)
    edge = np.clip(1 + dbox / 2.6, 0, 1) * inside
    up = ly < course * 0.45
    cv.screen(edge * m * up, lit, 0.16 * light)


# ====================================================================== painted structure: the room
SPRING_Y = 188.0              # the vault's spring line (a pale timber wall plate runs along it)
POOL_C = (246.0, 392.0)       # the daylight pool's centre (pt): behind the boss's head / shoulders


def OPEN_TOP3(x):
    """LOOK-L fix round 1: the tunnel exit's top, LOWER than the old opening (the copy judge: the old bright opening
    filled the upper right like the original's pale hall) -- a heavy lintel at y ~262-284 under stone and the vault."""
    return 262.0 + 0.10 * (np.asarray(x, float) - OPEN_X0)


def paint_room(cv):
    """Vault, wall plate, stone walls, the lintel + the daylight exit, the back room -- ONE saturated azure family
    (fix round 2), one warm light (the doorway), real darks (the crown, the tunnel)."""
    X, Y = cv.X, cv.Y
    h, w = cv.h, cv.w
    # ---- the boarded vault: cobalt planks fanning from the upper right; deep at the crown and the upper-left corner
    # (a dark frame round the logo), lifting to a clear azure toward the daylight at the right
    base = stops_interp(Y, [(0, VAULT[4]), (70, VAULT[3]), (150, VAULT[2]), (SPRING_Y, VAULT[1])])
    cv.a[..., :3] = base
    cv.a[..., 3] = 1.0
    ang = np.arctan2(Y + 260.0, X - 520.0)
    k = ang * 180.0 / math.pi * 0.30
    pk = np.floor(k)
    fk = k - pk
    tone = (_hash(pk, 3.0) - 0.5) * 0.045
    gr = _grain(h, w, 3, 60, 7)
    cv.a[..., :3] = cv.a[..., :3] * (1 + tone[..., None] + 0.012 * gr[..., None])
    dseam = np.minimum(fk, 1 - fk)
    cv.multiply(aa((dseam - 0.03) * 24.0, 0.8), "#002844", 0.24)
    # the daylight washing up the RIGHT side of the vault (a clear azure, not white), the deep frame top-left
    cv.screen(np.exp(-(((X - 430) / 220.0) ** 2 + ((Y - 170) / 190.0) ** 2)), "#2A9AF0", 0.55)
    cv.screen(np.exp(-(((X - 300) / 170.0) ** 2 + ((Y - 235) / 90.0) ** 2)), "#6BB0F3", 0.28)
    # the upper-right vault lit too (a skylight's azure glow high on the right): the planks read there, the deep frame
    # stays top-left behind the logo (fix round 2: a dark flat crown matched the original's ceiling in the copy watch crop)
    cv.screen(np.exp(-(((X - 400) / 150.0) ** 2 + ((Y + 10) / 90.0) ** 2)), "#3A9CF0", 0.55)
    cv.multiply(aa((dseam - 0.03) * 24.0, 0.8) * smooth(X, 180, 330), "#002844", 0.20)
    cv.multiply(np.exp(-(((X + 40) / 200.0) ** 2 + ((Y + 30) / 180.0) ** 2)), "#001A30", 0.50)
    cv.multiply(np.clip(1 - Y / 80.0, 0, 1) ** 1.5 * (1 - smooth(X, 140, 330)), "#001828", 0.40)
    # ---- two painted-timber arch ribs across the vault (a lighter azure of the same family: soft lines, no cream)
    beams = ((-12, 58, 400, 4, 16, 10.0), (-12, 126, 400, 70, 14, 9.0))
    for (x0, y0, x1, y1, bow, bw) in beams:
        n = 32
        tt = np.linspace(0, 1, n)
        pts = [(x0 + (x1 - x0) * t, y0 + (y1 - y0) * t - bow * 4 * t * (1 - t)) for t in tt]
        d, s_, t = polyline(X, Y, pts)
        cov = aa(d - bw / 2, 0.7)
        q = np.clip(s_ / (bw / 2), -1, 1)
        col = stops_interp(q, [(-1.0, VAULT[2]), (-0.4, RIB[4]), (0.3, RIB[3]), (0.8, RIB[2]), (1.0, RIB[3])])
        col = col * (0.80 + 0.20 * smooth(X, 60, 330))[..., None]           # the ribs dim toward the dark crown
        cv.multiply(np.exp(-(np.maximum(d - bw / 2, 0) / 6.0) ** 2) * (s_ < 0) * (1 - cov), "#001E36", 0.40)
        src = np.zeros((h, w, 4))
        src[..., :3] = col
        src[..., 3] = cov
        cv.over(src)
        del src
    # ---- one brass miner's lantern hanging from the vault at the upper right (a warm spark)
    dc_, _, _ = polyline(X, Y, [(352, -4), (352, 104)])
    cv.fill(aa(dc_ - 0.9, 0.6), "#0B3A62", 0.9)
    cv.screen(np.exp(-(((X - 352) / 34.0) ** 2 + ((Y - 124) / 34.0) ** 2)), "#FFD98E", 0.50)
    cv.fill(aa(sd_poly(X, Y, [(344, 104), (360, 104), (357, 110), (347, 110)]), 0.6), BRASS[2])
    glass = sd_poly(X, Y, [(343, 110), (361, 110), (363, 134), (341, 134)])
    cv.fill(rounded(aa(glass, 0.6), 3.0), stops_interp(np.hypot(X - 350, Y - 118) / 14.0, [(0, "#FFFBE8"), (0.6, "#FFE7A8"), (1.2, "#F7C25E")]))
    for gx in (345.5, 352.0, 358.5):
        dg, _, _ = polyline(X, Y, [(gx, 110), (gx + (gx - 352) * 0.08, 134)])
        cv.fill(aa(dg - 0.6, 0.5) * aa(glass, 0.6), BRASS[3], 0.8)
    cv.fill(aa(sd_poly(X, Y, [(339, 133), (365, 133), (362, 140), (342, 140)]), 0.6), stops_interp(Y, [(133, BRASS[1]), (140, BRASS[3])]))
    # ---- the walls below the spring line: mid-azure stone masonry, calm joints, lit toward the doorway
    wall = aa(-(Y - SPRING_Y), 1.5) * aa(-(X - 100), 2.0) * (Y < 505)
    base_w = stops_interp(Y, [(SPRING_Y, WALLB[3]), (300, WALLB[2]), (420, WALLB[1]), (500, WALLB[1])])
    masonry(cv, wall, SPRING_Y, 24.0, 51, base_w, mortar="#2E5E8C", lit="#DCEEFF", mortar_k=0.22)
    # the wall plate: a painted beam along the spring line (the vault sits on it)
    wp = aa(np.abs(Y - (SPRING_Y + 3.0)) - 5.0, 0.7) * aa(-(X - 96), 1.0)
    cv.fill(wp, stops_interp(Y, [(SPRING_Y - 2, RIB[1]), (SPRING_Y + 4, RIB[3]), (SPRING_Y + 8, VAULT[2])]))
    cv.multiply(np.exp(-(np.maximum(Y - (SPRING_Y + 8), 0) / 5.0) ** 2) * (Y > SPRING_Y + 8) * aa(-(X - 96), 1.0), "#002844", 0.35)
    # ---- the painted timber post (was the pillar), one iron strap
    pil = sd_poly(X, Y, [(104, SPRING_Y - 6), (126, SPRING_Y - 10), (126, 330), (104, 330)])
    pc = aa(pil, 0.8)
    q = np.clip((X - 104) / 22.0, 0, 1)
    pcol = stops_interp(q, [(0, RIB[1]), (0.25, RIB[2]), (0.8, RIB[3]), (1.0, VAULT[1])])
    src = np.zeros((h, w, 4))
    src[..., :3] = pcol
    src[..., 3] = pc
    cv.over(src)
    st = aa(np.abs(Y - 250.0) - 3.0, 0.6) * pc
    cv.fill(st, stops_interp(Y, [(247, "#5B96C4"), (253, "#2E5E8C")]))
    # ---- the exit: a lower opening with a heavy cobalt-iron lintel, a painted jamb
    top = OPEN_TOP3(X)
    jamb = sd_poly(X, Y, [(148, OPEN_TOP3(148) - 34), (OPEN_X0, OPEN_TOP3(OPEN_X0) - 34), (OPEN_X0, 505), (148, 505)])
    q = np.clip((X - 148) / 20.0, 0, 1)
    jcol = stops_interp(q, [(0, VAULT[1]), (0.5, RIB[3]), (0.9, RIB[1]), (1.0, RIB[0])])
    src[..., :3] = jcol
    src[..., 3] = aa(jamb, 0.8)
    cv.over(src)
    lint = (Y > top - 34) & (Y < top + 1) & (X > OPEN_X0 - 24)
    tl = np.clip((Y - (top - 34)) / 35.0, 0, 1)
    lcol = stops_interp(tl, [(0, BEAM[1]), (0.10, BEAM[0]), (0.30, BEAM[1]), (0.80, BEAM[2]), (1.0, BEAM[3])])
    cv.a[..., :3] = np.where(lint[..., None], lcol, cv.a[..., :3])
    for bx in np.arange(OPEN_X0 - 12, 400, 34.0):         # a row of brass rivets on the lintel
        by = OPEN_TOP3(bx) - 26.0
        cv.fill(aa(np.hypot(X - bx, Y - by) - 1.7, 0.5), BRASS[1], 0.9)
    cv.multiply((1 - smooth(-(Y - (top - 34)), 0, 5)) * (Y < top - 34) * aa(-(X - (OPEN_X0 - 24)), 1.0), "#002844", 0.35)
    # the doorway (fix round 2: the judges' "flat cream slab ... the brightest values on the page"): a view OUT with
    # depth at L* ~74-86 -- a pale azure sky strip at the top, a warm sunlit haze band at the horizon behind the boss,
    # a far ridge + a row of sheds in soft hazy azure (no cross-shaped gantry), a pale sunlit ground; two soft light
    # shafts slanting in from the upper left (defocused hard later with the yard)
    qx = np.maximum(OPEN_X0 + OPEN_R - X, 0)
    qy = np.maximum(top + OPEN_R - Y, 0)
    corner = (X < OPEN_X0 + OPEN_R) & (Y < top + OPEN_R)
    d_open = np.where(corner, np.hypot(qx, qy) - OPEN_R, np.maximum(OPEN_X0 - X, top - Y))
    op = aa(d_open, 0.8) * (Y < 505)
    yard = Canvas(393, 852)
    YX, YY = yard.X, yard.Y
    # LOOK-2 round 2 (the finish judge on v5: "the new glow reads as a beige / tan haze, not light, and adds a second
    # hue family that muddies the azure room ... make the bloom core near-neutral to slightly cool white at L* 92-96
    # with a wide falloff, lift the doorway and the floor reflection under it, and keep the warmth only in the boss rim
    # and the lantern"): the yard's sky runs azure -> a cool WHITE daylight band at the horizon (no beige)
    sky = stops_interp(YY, [(262, "#5AA6E6"), (320, "#8EC8F4"), (372, "#D6E8F6"), (410, "#F2F7FB"), (452, "#E8F0F6"), (505, "#BCD6EA")])
    yard.a[..., :3] = sky
    yard.a[..., 3] = 1.0
    # the sun haze behind the boss's head: warm, soft, never above L* ~88
    yard.screen(np.exp(-(((YX - POOL_C[0] - 20) / 130.0) ** 2 + ((YY - 405) / 70.0) ** 2)), "#F6FAFE", 0.34)
    # a far ridge behind the sheds (softer, lighter: aerial perspective)
    ridge = 352.0 - 12.0 * np.sin((YX - 180) / 38.0) - 7.0 * np.sin((YX - 150) / 17.0)
    yard.fill(aa(ridge - YY, 2.0) * (YY < 404), "#8EBEEA", 0.55)
    # a far water tower on stilts (a tank + four legs), a hazy mid-azure silhouette
    yard.fill(aa(sd_poly(YX, YY, [(262, 318), (296, 318), (298, 342), (260, 342)]), 1.2), "#6A9ED2", 0.72)
    yard.fill(aa(sd_poly(YX, YY, [(258, 318), (279, 306), (300, 318)]), 1.0), "#6A9ED2", 0.72)
    for lx_ in (264, 274, 284, 294):
        yard.fill(aa(sd_poly(YX, YY, [(lx_, 342), (lx_ + 3, 342), (lx_ + 3 + (lx_ - 279) * 0.12, 396), (lx_ + (lx_ - 279) * 0.12, 396)]), 0.8),
                  "#6A9ED2", 0.62)
    # far sheds with pitched roofs, hazy azure silhouettes on the horizon; a big barn with a loft door at the right
    sheds = [((196, 404), (246, 404), (246, 382), (221, 366), (196, 382)),
             ((252, 408), (318, 408), (318, 392), (285, 372), (252, 392))]
    for poly in sheds:
        yard.fill(aa(sd_poly(YX, YY, list(poly)), 1.2), "#9CC4E8", 0.55)
    # a lattice HEADFRAME (the pit's hoist tower) on the right: two raked legs, cross beams, X braces, the sheave wheel
    hf = "#4A88C4"
    for (xb, xt) in ((324.0, 344.0), (392.0, 370.0)):
        dl, _, _ = polyline(YX, YY, [(xb, 410), (xt, 300)])
        yard.fill(aa(dl - 2.2, 0.9), hf, 0.85)
    for yb in np.arange(318.0, 408.0, 22.0):
        k_ = (410 - yb) / 110.0
        xl, xr = 324 + 20 * k_, 392 - 22 * k_
        dl, _, _ = polyline(YX, YY, [(xl, yb), (xr, yb)])
        yard.fill(aa(dl - 1.3, 0.8), hf, 0.80)
        k2 = (410 - yb - 22) / 110.0
        for (x0_, x1_) in ((xl, 392 - 22 * k2), (xr, 324 + 20 * k2)):
            dl, _, _ = polyline(YX, YY, [(x0_, yb), (x1_, yb - 22)])
            yard.fill(aa(dl - 0.8, 0.7), hf, 0.65)
    yard.fill(aa(np.abs(np.hypot(YX - 357, YY - 290) - 12.0) - 2.0, 0.9), hf, 0.85)
    for ang_ in np.linspace(0, math.pi, 4, endpoint=False):
        dl, _, _ = polyline(YX, YY, [(357 - 12 * math.cos(ang_), 290 - 12 * math.sin(ang_)), (357 + 12 * math.cos(ang_), 290 + 12 * math.sin(ang_))])
        yard.fill(aa(dl - 0.7, 0.6), hf, 0.75)
    # the yard's CANOPY just outside the doorway (fix round 2 -- a flat bright field there matched the original's pale
    # hall, copy watch crop 0.386): its dark underside across the top of the opening with rafter ends + two posts
    can = 292.0 + 0.04 * (YX - 200)
    yard.fill(aa(YY - can, 1.5), stops_interp(YY, [(262, "#1C5E98"), (300, "#2E78B8")]), 0.92)
    for rx_ in np.arange(186.0, 400.0, 26.0):
        yard.fill(aa(sd_poly(YX, YY, [(rx_, can_ := 292.0 + 0.04 * (rx_ - 200)), (rx_ + 9, can_), (rx_ + 9, can_ + 7), (rx_, can_ + 7)]), 1.0),
                  "#2466A4", 0.85)
    for (x0, x1) in ((244, 252), (318, 326)):
        yard.fill(aa(sd_poly(YX, YY, [(x0, 290), (x1, 290), (x1 + 2, 452), (x0 - 2, 452)]), 1.2), "#3A7EBE", 0.75)
    yard.fill(aa(-(YY - 452), 2.0), stops_interp(YY, [(452, "#E0EAF2"), (505, "#A8C8E2")]))
    # soft light shafts from the upper left into the yard's haze
    for (x0, wdt, al) in ((236, 22, 0.16), (290, 34, 0.12)):
        dsh = np.abs((YX - x0) - (YY - 262) * 0.42)
        yard.screen(np.exp(-(dsh / wdt) ** 2) * smooth(YY, 262, 300) * (1 - smooth(YY, 430, 500)), "#F8FBFF", al)
    yard.a[..., 3] = op
    cv.over(yard.a)
    del yard
    # ---- the back room under the machine: a deep cobalt tunnel with one warm lamp (the page's real darks)
    back = sd_poly(X, Y, [(-5, 350), (180, 350), (180, 530), (-5, 530)])
    bm = aa(back, 1.0) * aa(X - 150, 30)
    rock = stops_interp(Y, [(350, "#00243E"), (420, "#003458"), (520, "#004A78")])
    src = np.zeros((h, w, 4))
    src[..., :3] = rock
    src[..., 3] = bm
    cv.over(src)
    cv.screen(np.exp(-(((X - 66) / 46.0) ** 2 + ((Y - 420) / 38.0) ** 2)) * bm, "#FFA848", 0.50)
    for (x0, x1) in ((6, 14), (116, 124)):                     # the tunnel's timber props
        post = aa(sd_poly(X, Y, [(x0, 352), (x1, 352), (x1, 470), (x0, 470)]), 0.8) * bm
        cv.fill(post, stops_interp(X, [(x0, VAULT[2]), (x1, VAULT[4])]))
    cv.fill(aa(sd_poly(X, Y, [(0, 360), (132, 360), (132, 368), (0, 368)]), 0.8) * bm, VAULT[3])
    lamp = sd_poly(X, Y, [(60, 396), (72, 396), (74, 414), (58, 414)])
    cv.fill(aa(lamp, 0.6), "#FFF3CC")
    cv.fill(aa(sd_poly(X, Y, [(57, 392), (75, 392), (72, 397), (60, 397)]), 0.6), BRASS[2])
    d, _, _ = polyline(X, Y, [(66, 368), (66, 393)])
    cv.fill(aa(d - 0.6, 0.5), "#2E5E8C", 0.8)
    fl = stops_interp(Y, [(468, "#0A4A7C"), (530, "#2A6FA8")])
    src[..., :3] = fl
    src[..., 3] = aa(sd_poly(X, Y, [(-5, 468), (120, 468), (120, 530), (-5, 530)]), 2.0) * 0.9
    cv.over(src)
    del src
    # ---- the doorway light blooming a little over the jamb, the lintel's underside and the wall round it (warm, soft)
    cv.screen(np.exp(-(((X - POOL_C[0]) / 130.0) ** 2 + ((Y - POOL_C[1]) / 140.0) ** 2)) * (1 - op), "#EEF4FA", 0.24)


# ====================================================================== the floor: polished mid-azure flags + rails
FLAG_CELL = 0.78           # uv per flag (fix round 2: smaller stones, softer joints; v3's 0.95 read as big flat hexagons)
FLAG_ROT = 12.0            # the flag lattice is turned in the floor plane (our own pattern, not the old seams)
FLAG_VAR = 0.45            # per-stone value / hue drift (x R4's)
# fix round 2: a short run of MINE RAILS on the floor (the hero's cart line; replaces the hemp rope, which sat where the
# original's cable lies -- the copy judge's bottom strip): from under the cart at the bottom left, back across the
# floor's empty centre toward the doorway. Floor uv (scene_loading.floor_uv): u across, v receding (v 0.62 = the
# bottom edge, v -3.4 = the horizon).
RAIL_NEAR = (-0.30, 0.66)          # the track's centre line (u, v) at the bottom edge ...
RAIL_FAR = (-0.72, -3.05)          # ... and near the doorway
RAIL_GAUGE = 0.30                  # uv between the rails
RAIL_W = 0.030                     # uv width of one rail head
SLEEPER_STEP, SLEEPER_W, SLEEPER_L = 0.26, 0.060, 0.26


def _rail_u(v):
    t = (np.asarray(v, float) - RAIL_NEAR[1]) / (RAIL_FAR[1] - RAIL_NEAR[1])
    return RAIL_NEAR[0] + (RAIL_FAR[0] - RAIL_NEAR[0]) * t + 0.10 * np.sin(np.clip(t, 0, 1) * math.pi)   # a gentle bend


BRANCH_V0, BRANCH_DU = -1.10, 0.95     # a TURNOUT: a second track leaves the main one at v -1.1 and curves out to the
                                        # bottom right (the copy watch crops: the bottom-right floor was one flat field)


def _branch_u(v):
    t = np.clip((np.asarray(v, float) - BRANCH_V0) / (RAIL_NEAR[1] + 0.1 - BRANCH_V0), 0, 1)
    return _rail_u(v) + BRANCH_DU * t ** 1.8


def paint_floor(L):
    """The floor as a transparent LAYER (the caller defocuses it by depth)."""
    X, Y = L.X, L.Y
    u, v = floor_uv(X, Y)
    c, s_ = math.cos(math.radians(FLAG_ROT)), math.sin(math.radians(FLAG_ROT))
    U = (u * c - v * s_) / FLAG_CELL
    V = (u * s_ + v * c) / FLAG_CELL
    iu, iv = np.floor(U), np.floor(V)
    F1 = np.full(U.shape, 9.0)
    F2 = np.full(U.shape, 9.0)
    ID = np.zeros(U.shape)
    for du in (-2, -1, 0, 1, 2):          # 5 x 5 cells: the 3 x 3 search left notches in far joints (LOOK-L)
        for dv in (-2, -1, 0, 1, 2):
            cu, cvv = iu + du, iv + dv
            jx = 0.18 + 0.64 * _hash(cu, cvv)
            jy = 0.18 + 0.64 * _hash(cvv + 7.1, cu - 3.3, 39.3468)
            d = np.hypot(U - cu - jx, V - cvv - jy)
            closer = d < F1
            F2 = np.where(closer, F1, np.minimum(F2, d))
            ID = np.where(closer, cu * 131.0 + cvv * 17.0, ID)
            F1 = np.where(closer, d, F1)
    edge = (F2 - F1) * 0.5 * FLAG_CELL
    gu = np.hypot(*np.gradient(u)) * 3.0
    gv = np.hypot(*np.gradient(v)) * 3.0
    g = np.sqrt(gu * gv)
    e_pt = edge / np.maximum(g, 1e-6)
    tile_pt = 1.0 / np.maximum(gv, 1e-6)
    scale = np.clip(tile_pt / 120.0, 0.05, 1.6)
    far = np.clip((tile_pt - 14.0) / 22.0, 0, 1)
    # mid azure, a lit centre where the crew runs (the doorway's light reaching forward), deeper toward the edges
    base = stops_interp(Y, [(FLOOR_TOP, SAND[1]), (560, SAND[1]), (700, SAND[2]), (852, SAND[3])])
    h1 = _hash(ID, 5.0) - 0.5
    h2 = _hash(ID, 9.0, 51.17) - 0.5
    tint = np.stack([1 - 0.02 * h2, 1 + 0.004 * h2, 1 + 0.02 * h2], -1)
    near = np.clip((Y - 600) / 200.0, 0, 1)
    col = base * (1 + ((0.16 + 0.10 * near) * FLAG_VAR * h1)[..., None]) * tint
    nz = noise2(L.h, L.w, 30, seed=81) * 0.7 + noise2(L.h, L.w, 60, seed=82) * 0.3
    col = col * (1 + 0.035 * nz[..., None])
    # joints: a thin, soft, slightly deeper azure line; a faint lit bevel on the stone's far edge
    jw = 0.7 * np.clip(scale, 0.35, 1.3)
    ee = e_pt
    joint = (1 - smooth(ee, jw - 0.5, jw + 0.6)) * far
    jcol = stops_interp(Y, [(FLOOR_TOP, "#4C96D6"), (620, "#3A82C4"), (852, "#2F6EAA")])
    col = col * (1 - joint[..., None] * 0.45) + jcol * (joint * 0.45)[..., None]
    rim = np.exp(-((ee - jw - 1.4 * scale) / (2.0 * np.maximum(scale, 0.4))) ** 2) * far
    gy_, gx_ = np.gradient(F1)
    litw = np.clip(0.5 + 0.5 * gy_ / np.maximum(np.hypot(gx_, gy_), 1e-6), 0, 1)
    col = col + (rgb("#A8D2FA") - col) * (0.20 * rim * litw)[..., None]
    col = col * (1 - 0.05 * (rim * (1 - litw)))[..., None]
    # the value structure: a broad LIT CENTRE under the cast (x ~220, y ~640) and the doorway's spill, falling off to a
    # deeper cobalt at the bottom corners and the left edge (a vignette that frames the crew)
    lit = np.exp(-(((X - 225) / 175.0) ** 2 + ((Y - 625) / 135.0) ** 2))
    col = col + (rgb("#7FBBF3")[None, None] - col) * (0.50 * lit)[..., None]
    fall = (np.clip((Y - 660) / 192.0, 0, 1) ** 1.2 * (0.55 + 0.45 * np.abs(X - 200) / 200.0))[..., None]
    col = col + (rgb("#1F5E9E")[None, None] - col) * (0.55 * fall)
    edge_l = np.exp(-((X + 10) / 90.0) ** 2) * smooth(Y, 520, 620)
    col = col + (rgb("#265F96")[None, None] - col) * (0.40 * edge_l)[..., None]
    col = col * (1 - 0.30 * np.exp(-(((X + 20) / 110.0) ** 2 + ((Y - 530) / 60.0) ** 2)))[..., None]   # under the dock
    # the GLOSSY sheen: the doorway mirrored on the polished flags -- a soft warm-white streak under the exit, widest
    # near it, fading toward the camera
    sx = np.exp(-((X - (POOL_C[0] + 40) - (Y - 505) * 0.10) / (72.0 + (Y - 505) * 0.12)) ** 2)
    sy = np.clip(1 - (Y - 500) / 230.0, 0, 1) ** 1.5 * smooth(Y, 478, 500)
    col = col + (rgb("#E6F0FA")[None, None] - col) * (0.50 * sx * sy)[..., None]     # LOOK-2 r2: a cool-white sheen
    hz = np.clip(1 - (Y - FLOOR_TOP) / 60.0, 0, 1) ** 1.5
    col = col + (rgb("#91C6F7") - col) * (hz * 0.35)[..., None]
    col = paint_rails(col, X, Y, u, v, gu, gv)
    L.a[..., :3] = np.clip(col, 0, 1)
    L.a[..., 3] = aa(FLOOR_TOP - Y, 2.0)


def paint_rails(col, X, Y, u, v, gu, gv):
    """The main track and its turnout (two steel rails on timber sleepers each, laid on the floor plane)."""
    col = paint_track(col, X, Y, u, v, gu, gv, _rail_u(v), v_min=RAIL_FAR[1])
    return paint_track(col, X, Y, u, v, gu, gv, _branch_u(v), v_min=BRANCH_V0 + 0.15, sleepers_from=BRANCH_V0 + 0.45)


def paint_track(col, X, Y, u, v, gu, gv, uc, v_min, sleepers_from=None):
    """Two steel rails on timber sleepers, laid on the floor plane (painted in uv: the perspective is exact), with a
    crisp lit rail head, a dark web below it, a soft contact shadow and the sleepers' own shading."""
    inside = (v < RAIL_NEAR[1] + 0.2) & (v > v_min) & (Y > FLOOR_TOP + 4)
    fade = (1 - smooth(-v, -RAIL_FAR[1] - 0.6, -RAIL_FAR[1])) * inside     # the far end fades into the haze
    ppu = 1.0 / np.maximum(gu, 1e-6)                   # pt per u (across) here (gu, gv: per-pt derivatives)
    # sleepers first (under the rails)
    sv = (v - RAIL_NEAR[1]) / SLEEPER_STEP
    fv = (sv - np.floor(sv)) * SLEEPER_STEP                # 0 .. step in v
    ds = (np.abs(fv - SLEEPER_STEP / 2) - SLEEPER_W / 2) / np.maximum(gv, 1e-6)       # pt from the sleeper's edge (v)
    du_s = (np.abs(u - uc) - (RAIL_GAUGE / 2 + SLEEPER_L / 2 - 0.02)) * ppu
    slp = aa(np.maximum(ds, du_s), 0.5) * fade
    if sleepers_from is not None:                   # the turnout's own sleepers start where it clears the main track
        slp = slp * smooth(v, sleepers_from, sleepers_from + 0.2)
    sid = np.floor(sv)
    sc = stops_interp(Y, [(FLOOR_TOP, "#3E86C8"), (700, "#2F72B2"), (852, "#285F98")]) * (1 + 0.06 * (_hash(sid, 2.0) - 0.5))[..., None]
    col = col * (1 - 0.16 * aa(np.maximum(ds - 0.8, du_s - 0.8), 1.4) * fade)[..., None]     # its soft shadow
    col = col * (1 - slp[..., None]) + sc * slp[..., None]
    edge_lit = np.exp(-(ds + 0.35) ** 2 / 0.25) * slp
    col = col + (rgb("#7FBBF3") - col) * (0.30 * edge_lit)[..., None]
    # the rails
    for sgn in (-1, 1):
        dr = (np.abs(u - (uc + sgn * RAIL_GAUGE / 2)) - RAIL_W / 2) * ppu      # pt from the rail's edge
        sh = np.exp(-np.maximum(dr - 0.2, 0) ** 2 / (2.0 * np.maximum(ppu * 0.012, 0.3) ** 2)) * fade
        col = col * (1 - 0.22 * sh * (dr > 0))[..., None]
        cov = aa(dr, 0.35) * fade
        w_ = np.clip((u - (uc + sgn * RAIL_GAUGE / 2)) / (RAIL_W / 2), -1, 1)
        rc = stops_interp(w_, [(-1.0, "#1A4A7E"), (-0.2, "#4E80B4"), (0.35, "#D8ECFF"), (0.7, "#8CB8E4"), (1.0, "#245890")])
        col = col * (1 - cov[..., None]) + rc * cov[..., None]
    return col


# ====================================================================== the dock (was the stepped conveyor)
def paint_dock(L):
    """LOOK-2 round 2 (the finish judge on v5: "the beige dock platform's edge is a confusing wavy blue cut-out"; the copy
    judge: "small figures on a disc, echoing their figures on a disc"): a CLEAN timber dock -- a deck with one straight
    front edge (a lit nosing), a front face of vertical planks, a darker end face, a soft contact shadow on the floor
    under it; no turntable disc (the pair stands on the planks)."""
    X, Y = L.X, L.Y
    h, w = L.h, L.w
    src = np.zeros((h, w, 4))
    # the floor's contact shadow under the dock's front face
    d, s, t = polyline(X, Y, [(-10, 541), (88, 534)])
    L.fill(np.exp(-(np.maximum(d, 0) / 7.0) ** 2) * (Y > 530) * aa(96 - X, 6), "#1E4A7A", 0.40)
    # the front face: vertical planks, darker toward the floor
    face = sd_poly(X, Y, [(-8, 513), (86, 509), (86, 532), (-8, 538)])
    cov = rounded(aa(face, 0.6), 1.2)
    bx = (X + 2.0) / 9.0
    fb = bx - np.floor(bx)
    tone = (_hash(np.floor(bx), 2.0) - 0.5) * 0.06
    col = stops_interp(Y, [(510, TIMBER[2]), (538, TIMBER[3])]) * (1 + tone[..., None])
    src[..., :3] = col
    src[..., 3] = cov
    L.over(src)
    L.multiply(aa((np.minimum(fb, 1 - fb) * 9.0) - 0.45, 0.6) * cov, TIMBER[4], 0.40)
    # the end face (right), in shade
    endf = sd_poly(X, Y, [(86, 509), (91, 506), (91, 529), (86, 532)])
    L.fill(rounded(aa(endf, 0.6), 0.8), stops_interp(Y, [(506, TIMBER[3]), (532, TIMBER[4])]), 0.95)
    # the deck: boards running left -> right, a straight front edge
    deck = sd_poly(X, Y, [(-8, 468), (84, 465), (91, 506), (86, 509), (-8, 513)])
    dcol = stops_interp(Y, [(465, DOCKWOOD[2]), (490, DOCKWOOD[1]), (513, DOCKWOOD[2])])     # (r2: a mid-tone deck)
    py = (Y - 465) / 8.0
    fp = py - np.floor(py)
    dcol = dcol * (1 + (_hash(np.floor(py), 4.0) - 0.5)[..., None] * 0.05)
    src[..., :3] = dcol
    src[..., 3] = rounded(aa(deck, 0.6), 1.5)
    L.over(src)
    L.multiply(aa((np.minimum(fp, 1 - fp) * 8.0) - 0.45, 0.6) * src[..., 3], TIMBER[2], 0.28)
    # the lit nosing along the front edge (one crisp light line) + a thin dark joint under it
    dn, _, _ = polyline(X, Y, [(-8, 512.2), (86, 508.2)])
    L.fill(aa(dn - 0.9, 0.5), "#FFF1D8", 0.85)
    dj, _, _ = polyline(X, Y, [(-8, 514.4), (86, 510.4)])
    L.fill(aa(dj - 0.5, 0.5), TIMBER[4], 0.55)
    # (r2: a plain smooth deck + face read as one flat plane -- the copy watch crop "dock left" rose to 0.38-0.40; the
    # board structure below brings it to ~0.33-0.37, measured with build/p/LOOK2/r2/dockexp.py)
    # heavier board joints on the deck
    L.multiply(aa((np.minimum(fp, 1 - fp) * 8.0) - 0.6, 0.5) * aa(deck, 0.6), TIMBER[3], 0.45)
    # a vertical-plank rhythm on the front face: a dark joint every 9 pt and a lit left edge on each board
    fc = aa(face, 0.6)
    L.multiply(aa((np.minimum(fb, 1 - fb) * 9.0) - 0.7, 0.5) * fc, "#3A2410", 0.55)
    L.fill(aa(np.abs(fb - 0.12) * 9.0 - 0.5, 0.5) * fc, "#F2D2A0", 0.35)
    # two mooring posts with iron caps at the deck's front corners
    for x0 in (4.0, 70.0):
        post = sd_poly(X, Y, [(x0, 486), (x0 + 7, 486), (x0 + 7, 530), (x0, 531)])
        L.fill(aa(post, 0.6), stops_interp(X, [(x0, TIMBER[2]), (x0 + 7, TIMBER[4])]))
        L.fill(aa(sd_poly(X, Y, [(x0 - 0.5, 485), (x0 + 7.5, 485), (x0 + 7.5, 489), (x0 - 0.5, 489)]), 0.5), "#3E4650")
    del src


# ====================================================================== the sorting machine (was the press)
def paint_machine(L):
    X, Y = L.X, L.Y
    h, w = L.h, L.w
    src = np.zeros((h, w, 4))

    def put(cov, col):
        src[..., :3] = np.clip(col, 0, 1)
        src[..., 3] = np.clip(cov, 0, 1)
        L.over(src)
    fade = aa(X - 186.0, 0.8)          # LOOK-L fix round 1: a crisp cut end (v2 faded it out over the bright exit: a smear)
    # --- the beam's underside, then its face: a terracotta painted iron beam (warm: one colour family)
    under = sd_poly(X, Y, _curve_poly(B_MID, B_BOT, -8, 240))
    tu = band_t(X, Y, B_MID, B_BOT)
    uc = stops_interp(X, [(-8, "#001E36"), (120, "#002C4E"), (240, BEAM[3])])
    uc = uc + (rgb(BEAM[1]) - uc) * (0.40 * smooth(tu, 0.86, 1.0))[..., None]
    put(aa(under, 0.5) * fade, uc)
    face = sd_poly(X, Y, _curve_poly(B_TOP, B_MID, -8, 240))
    tb = band_t(X, Y, B_TOP, B_MID)
    fc = stops_interp(X, [(-8, BEAM[2]), (100, BEAM[1]), (240, BEAM[0])])
    low = smooth(tb, 0.70, 0.78)
    fc = fc * (1 - low[..., None]) + (fc * np.array([0.86, 0.84, 0.84])) * low[..., None]
    fc = fc + (rgb("#9CCBF6") - fc) * (0.45 * (1 - smooth(tb, 0.0, 0.10)))[..., None]
    put(aa(face, 0.5) * fade, fc)
    for bx in np.arange(10.0, 236.0, 28.0):                  # a sparse row of brass rivets
        by = B_TOP(bx) + (B_MID(bx) - B_TOP(bx)) * 0.2
        L.fill(aa(np.hypot(X - bx, Y - by) - 1.6, 0.5) * fade, BRASS[2], 0.8)
    # --- LOOK-L fix round 1 (the copy judge: the two round push buttons were the original's object in its place): a
    # brass PRESSURE GAUGE (cream dial, ticks, a coral needle) and a small glowing signal LAMP on the beam face
    (gx, gy, grx, gry), (lx, ly, lrx, lry) = BUTTONS
    dx, dy = X - gx, Y - gy
    L.multiply(np.exp(-(((dx + 2.4) / (grx * 1.1)) ** 2 + ((dy - 2.8) / (gry * 1.1)) ** 2) ** 2), "#002844", 0.40)
    ring = np.hypot(dx / grx, dy / gry) - 1
    rc = stops_interp(dy / gry - dx / grx * 0.4, [(-1.2, BRASS[0]), (-0.2, BRASS[1]), (1.2, BRASS[3])])
    put(aa(ring * min(grx, gry), 0.45), rc)
    fr = np.hypot(dx / (grx - 2.6), dy / (gry - 2.6)) - 1
    put(aa(fr * (grx - 2.6), 0.4), stops_interp(dy / gry, [(-1, "#FFFFFF"), (1, "#E8E2D2")]))
    ang = np.arctan2(dy, dx)
    rr = np.hypot(dx / (grx - 2.6), dy / (gry - 2.6))
    tick = (np.abs(((ang + math.pi) / (2 * math.pi) * 12) % 1.0 - 0.5) > 0.40) * (rr > 0.70) * (rr < 0.90) * (dy < gry * 0.45)
    L.fill(tick * aa(fr * (grx - 2.6), 0.4), "#3A4A56", 0.9)
    na = math.radians(-40.0)
    dn, _, _ = polyline(X, Y, [(gx, gy), (gx + math.cos(na) * (grx - 5.0), gy + math.sin(na) * (gry - 5.0))])
    L.fill(aa(dn - 0.9, 0.4), "#E4402A", 1.0)
    L.fill(aa(np.hypot(dx, dy) - 1.8, 0.4), BRASS[3], 1.0)
    L.fill(np.exp(-(((dx + 4.0) / 3.2) ** 2 + ((dy + 4.4) / 2.2) ** 2)), "#FFFFFF", 0.55)
    dx, dy = X - lx, Y - ly
    rs = 0.62
    ring = np.hypot(dx / (lrx * rs), dy / (lry * rs)) - 1
    put(aa(ring * lrx * rs, 0.45), stops_interp(dy / lry - dx / lrx * 0.4, [(-1.2, BRASS[0]), (1.2, BRASS[3])]))
    fr = np.hypot(dx / (lrx * rs - 1.8), dy / (lry * rs - 1.8)) - 1
    put(aa(fr * (lrx * rs - 1.8), 0.4), stops_interp(np.hypot(dx + 1.5, dy + 1.5) / (lrx * rs), [(0, "#FFF2C8"), (0.5, "#FFB43A"), (1.0, "#E0761A")]))
    L.screen(np.exp(-((np.hypot(dx, dy) / (lrx * 1.2)) ** 2)), "#FFD27A", 0.35)
    # --- the pale copper sheet panel (+ its lit end face)
    pk = sd_poly(X, Y, [(-8, P_TOP(-8)), (106, P_TOP(106)), (106, B_TOP(106)), (-8, B_TOP(-8))])
    tp = band_t(X, Y, P_TOP, B_TOP)
    pc = stops_interp(X, [(-8, TANG[3]), (30, TANG[2]), (80, TANG[1]), (106, TANG[0])])
    pc = pc + (rgb("#B7D6EE") - pc) * (0.35 * np.exp(-((tp - 0.08) / 0.05) ** 2))[..., None]
    put(aa(pk, 0.5), pc)
    end = sd_poly(X, Y, [(105, P_TOP(105)), (112, P_TOP(105) - 2.5), (112, B_TOP(112) + 5), (105, B_TOP(105))])
    put(rounded(aa(end, 0.5), 1.5), stops_interp(Y, [(285, "#AED0F0"), (325, "#0080D7")]))
    # --- the brass band along the housing's bottom (rounded end at x ~106)
    lp = sd_poly(X, Y, [(-8, R_TOP(-8)), (100, R_TOP(100)), (100, P_TOP(100)), (-8, P_TOP(-8))])
    tl = band_t(X, Y, R_TOP, P_TOP)
    lc = stops_interp(tl, [(0, BRASS[1]), (0.25, BRASS[2]), (0.75, "#CFA050"), (1.0, BRASS[3])])
    put(rounded(aa(lp, 0.5), 6.0), lc)
    # --- the cream enamel iron housing
    hs = sd_poly(X, Y, [(-8, T_TOP(-8)), (95, T_TOP(95)), (95, R_TOP(95)), (-8, R_TOP(-8))])
    th = band_t(X, Y, T_TOP, R_TOP)
    hc = stops_interp(X, [(-8, ENAMEL[3]), (40, ENAMEL[2]), (95, ENAMEL[1])])
    hc = hc + (rgb(ENAMEL[0]) - hc) * (0.45 * np.exp(-((th - 0.35) / 0.14) ** 2))[..., None]
    hc = hc * (1 - 0.08 * smooth(th, 0.80, 1.0))[..., None]
    put(rounded(aa(hs, 0.5), 7.0), hc)
    L.screen(np.exp(-(((X - 98) / 16.0) ** 2 + ((Y - 272) / 18.0) ** 2)) * aa(lp, 0.5), "#FFFFFF", 0.35)
    del src


def paint_props(L):
    """LOOK-L fix round 1: the rolled-out tunnel map is gone (the copy judge: the original's paper sheets sat in the same
    spot); the floor at the right edge stays clear."""
    return


# ====================================================================== 3-D: crates, rope, flying arrows
def crates():
    """LOOK-2 round 2 (the finish judge on v5: "the crates are still pale striped slabs that read as cardboard sandwiches
    ... FIX: warmer crates with a few lit edges, or a crate-and-barrel mix"; the copy judge: "different crate stacking,
    or a barrel ... instead of the two-tier stack"): ONE framed timber crate (a darker frame, slats, a diagonal brace,
    a bevel that catches the lamp) + a staved BARREL with two iron hoops, side by side at the back of the dock."""
    parts = []
    from dataclasses import replace
    # (r2: a crate and a barrel of one height read as one flat band over the deck -- the copy watch crop "dock left"
    # rose 0.30 -> 0.38; a LOW crate + a TALL barrel make a stepped skyline instead)
    sx, sy, w, h, d, yaw = 22.0, 454.0, 4.4, 3.0, 3.8, -14
    m = satin("ld_crate6", "#B07A48", rough=0.62, ior=1.22)
    m = replace(m, texture=_crate_tex6(), texture_size=256)
    c = W(sx, sy, 0.0)
    body = rbox(w, h, d, 0.22).rotate_y(yaw).translate(*c)
    uv = ("planar", (c[0] - w / 2, c[1] - h / 2, 0.0), (1, 0, 0), (0, 1, 0), 1.0 / w)
    parts.append(Part("crate6", body, m, voxel=0.03, uv=uv))
    bx_, by_ = W(60.0, 438.0, -0.6)[:2]
    barrel = ellipsoid(2.05, 4.3, 2.05).intersect(box(3.0, 3.20, 3.0)).translate(bx_, by_, -0.6)
    bm = satin("ld_barrel6", "#A86E40", rough=0.60, ior=1.22)
    bm = replace(bm, texture=_stave_tex6(), texture_size=256)
    parts.append(Part("barrel6", barrel, bm, voxel=0.03, uv=("cyl", (bx_, by_ - 3.2, -0.6), (0, 1, 0), 1.0 / 6.4)))
    hoops = union(*[torus(1.98, 0.10).translate(bx_, by_ + yy, -0.6) for yy in (-2.2, 0.0, 2.2)])
    parts.append(Part("barrelHoops6", hoops, metal("ld_hoop6", "#3E4650", rough=0.40), voxel=0.02))
    return parts, 0.03


def _crate_tex6():
    """the crate's front: a darker FRAME (edge boards), four slats with dark gaps, a diagonal brace, a fine grain."""
    def fn(u, v):
        base = np.stack([np.full(u.shape, 0.80), np.full(u.shape, 0.56), np.full(u.shape, 0.33)], -1)
        frame = np.stack([np.full(u.shape, 0.64), np.full(u.shape, 0.42), np.full(u.shape, 0.24)], -1)
        vv = v / 0.83
        edge = (u < 0.11) | (u > 0.89) | (vv < 0.12) | (vv > 0.88)
        brace = np.abs((u - 0.11) / 0.78 - (vv - 0.12) / 0.76) < 0.075
        f = ((vv - 0.12) / 0.76 * 4.0) % 1.0
        gap = (np.minimum(f, 1 - f) < 0.05) & ~edge
        grain = (np.sin(u * 70.0 + np.sin(v * 9.0) * 2.5) * 0.045)[..., None]
        col = np.where((edge | brace)[..., None], frame, base) * (1 + grain)
        return np.clip(np.where(gap[..., None], col * 0.55, col), 0, 1)
    return fn


def _stave_tex6():
    """the barrel: vertical staves (u = the angle) with dark joints, a warm oiled wood, a little per-stave tone."""
    def fn(u, v):
        n = 18.0
        k = np.floor(u * n)
        f = (u * n) % 1.0
        tone = 1 + (np.sin(k * 12.9898) * 43758.5453 % 1.0 - 0.5) * 0.10
        base = np.stack([0.76 * tone, 0.50 * tone, 0.29 * tone], -1)
        grain = (np.sin(v * 40.0 + k) * 0.035)[..., None]
        joint = (np.minimum(f, 1 - f) < 0.06)[..., None]
        return np.clip(np.where(joint, base * 0.55, base * (1 + grain)), 0, 1)
    return fn


def _rope_pts():
    """In from the left edge low down, along the bottom under the label, then a loose coil lying on the flags at the
    bottom right (an inward elliptical spiral in the floor's foreshortening, so the rope never crosses itself)."""
    cx, cy = 318.0, 816.0
    run = [(-14, 842), (30, 846), (80, 848), (130, 846), (180, 842), (232, 838), (276, 834.5)]
    coil = []
    n = 64
    for i in range(0, n + 1):
        t = i / n
        a = math.pi * (1.5 + 3.2 * t)                 # enters at the coil's front (bottom) point along +x: no kink
        rx = 46.0 - 24.0 * t
        ry = 18.0 - 9.0 * t
        coil.append((cx + rx * math.cos(a), cy - ry * math.sin(a)))
    return run + coil


ROPE_PTS = _rope_pts()


def rope():
    """A hemp rope along the floor (the old cable's run, eased) with a brass coupling ring; twisted by texture."""
    from dataclasses import replace
    m = satin("ld_rope", "#E2C28E", rough=0.75, ior=1.15)
    m = replace(m, texture=_twist_tex(), texture_size=256)
    parts = [SL._sweep("rope", _catmull(ROPE_PTS, 6), 0.46, m)]
    ring = torus(0.68, 0.21).rotate_z(96).translate(*W(84, 848, 0.3))
    parts.append(Part("ropeRing", ring, metal("ld_ropering", BRASS[1], rough=0.3), voxel=0.02))
    return parts, 0.025


def _twist_tex():
    def fn(u, v):
        s = ((u * 260.0 + v * 3.0) % 1.0)
        k = 0.78 + 0.22 * np.cos(s * 2 * math.pi)
        base = np.stack([np.full(u.shape, 0.90), np.full(u.shape, 0.76), np.full(u.shape, 0.54)], -1)
        return np.clip(base * k[..., None], 0, 1)
    return fn


def block_arrow_d1(color):
    """The loading screen's chunky flying arrow (scene_loading.block_arrow's shape) in D1 enamel."""
    import scene_home as H
    from dataclasses import replace
    from arrows3d import arrow2d
    s2 = arrow2d(shaft=0.70, t=0.275, hl=0.62)
    c = (s2.lo + s2.hi) / 2
    s2c = s2.translate(-c[0], -c[1])
    body = extrude(s2c, 0.30, round=0.12).scale(3.2)
    lo = (float(s2c.lo[0]) - 0.05, float(s2c.lo[1]) - 0.05)
    size = float(max(s2c.hi - s2c.lo)) + 0.1
    sh = BLOCK_SHADES_D1[color]
    m = gloss(f"ld2_{color}", sh[0], rough=0.34, ior=1.30)     # r2: less grazing mirror on the side walls
    m = replace(m, texture=H._pile_bevel(s2c, lo, size, color, band=0.13, shades=sh), texture_size=512)
    uv = ("planar", (lo[0] * 3.2, lo[1] * 3.2, 0.0), (1, 0, 0), (0, 1, 0), 1.0 / (size * 3.2))
    return [Part("arrow", body, m, uv=uv)], 0.02


MODELS = {"crates_d1": crates, "rope_d1": rope}
for _c in BLOCK_SHADES_D1:
    MODELS[f"block_d1_{_c}"] = (lambda c=_c: block_arrow_d1(c))

# (model, centre pt, R, scale, haze, blur pt) -- the same four flights as today (scene_loading.FLY), D1 colours
FLY = [
    # fix round 2 (the copy judge: the top-left arrow was red like theirs in the same corner; the small pale arrow under
    # the big one echoed their pale periwinkle one): the top-left flight is SUNFLOWER, the top-right one CORAL (theirs
    # is purple there), the small one under the logo a saturated TEAL (no pale haze)
    ("block_d1_sunflower", (58, 8, 6.0), (rot_z(-128) @ rot_x(-6) @ rot_y(6)).tolist(), 3.1, 0.0, 0.35),
    ("block_d1_coral", (262, 40, 4.0), (rot_z(52) @ rot_x(-18) @ rot_y(-10)).tolist(), 2.1, 0.0, 0.40),
    ("block_d1_tangerine", (160, 246, 2.0), (rot_z(62) @ rot_x(16) @ rot_y(-20)).tolist(), 2.2, 0.05, 0.70),
    ("block_d1_teal", (122, 284, 2.5), (rot_z(40) @ rot_x(15) @ rot_y(-22)).tolist(), 1.05, 0.04, 0.90),
]
# the flying arrows' dome (fix round 2): neutral-warm, so the side walls show a darker step of their OWN colour (the
# lab's lilac dome turned the yellow's sides mauve)
FLY_ENV = dict(name="ld2fly2", sky=(0.92, 0.90, 0.86), hor=(0.46, 0.43, 0.40), gnd=(0.30, 0.28, 0.26))   # r2: a dim horizon --
# the tail's end cap caught the bright horizon at a grazing angle and read as a pale pink plate


# ====================================================================== the cast layout (frame top-left pt, z back -> front)
# Same roles and spots as today's Loading (build/p/R4/prev/char_loading_layout.json): each D1 figure takes the slot of
# the figure it replaces, placed by its eye midpoint (the sidecar's eyeMid) near the old figure's eyes, scaled to fill
# the old figure's share of the frame. scale = frame / the render's native frame (<= 1.15: the renders are @3x).
LAYOUT = {
    # name: (eye x, eye y, scale, z, grounded, replaces) -- LOOK-L fix round 1: every figure at (or within 5 % of) its
    # native 3x (the judges: v2 drew the four biggest at 1.15-1.37x -> soft at 1:1); the HERO cart rider big and close,
    # bleeding off the bottom-left; the runner (id char_digFlyer, portrait frame) front-right, a step behind the hero;
    # the arrow surfer (id char_digPop2, landscape frame) top-right; the striding boss centre in front of the daylight
    "char_digDockL": (None, None, 1.0, -3, True, "char_workerCrowdLeft"),
    # LOOK-2 round 2 (the finish judge on v5: "the far-right Digger's head is cut by the right screen edge ... shift the
    # pair about 15-20 pt left"): eye x 324 -> 304
    "char_digPop1": (304.0, 458.0, 0.90, -2, True, "char_workerRunners"),
    # fix round 2 (the finish judge: "dead centre / floating boss"): the boss steps DOWN and forward ~56 pt so his
    # boots land at y ~575 in the crew band, the runner pulled in so the front figures overlap in a pyramid
    "char_bossLoading": (190.0, 402.0, 1.0, -1, True, "char_scientistLoading"),
    "char_digPop2": (290.0, 190.0, 1.0, 0, False, "char_workerFlyer"),
    "char_digFlyer": (268.0, 618.0, 1.0, 1, True, "char_workerFist"),
    # fix round 2: the hero leans OUT of a tipping cart (a new eye point in its frame); the frame keeps v3's spot, its
    # bottom / left edges off-screen (x -9.7, y 573.6)
    # LOOK-2 (the finish judge on v4: "his left eye touches the left screen edge ... FIX: the whole face at least 40 px
    # inside the frame"): the hero rides high in a smaller cart, his eyes at x 103 pt (the face ~50 pt / 150 px inside
    # the screen); the frame keeps its bottom-left bleed (x -9.9, y 573.9)
    "char_digCart": (103.0, 656.0, 1.0, 2, True, "char_workerCarrier"),
}
DOCK_FRAME = (-6.0, 434.0, 96.0, 76.0)    # char_digDockL: two small Diggers on the dock (frame top-left + size, pt)
DOCK_BLUR_PX = 2.4       # LOOK-2: the dock pair's defocus (@3x px; v4 0.8 -- sharper than the crates around them)
DOCK_HAZE = "#CFE2F4"    # LOOK-2: the room's azure distance haze (v4 a warm cream from the peach page of v2)
DOCK_HAZE_K = 0.16
DOCK_CONTRAST = 0.88


FIG_DIR = os.environ.get("LOADING_FIG_DIR", K_OUT)     # review previews read figures from elsewhere (default art/out)


def layout_frames():
    """{name: dict(file, x, y, w, h, z)} in pt, from LAYOUT + the renders' sidecars."""
    out = {}
    for name, (ex, ey, s, z, grounded, _) in LAYOUT.items():
        if name == "char_digDockL":
            x, y, w, h = DOCK_FRAME
            out[name] = dict(file=f"{name}@3x.png", x=x, y=y, w=w, h=h, z=z, grounded=grounded)
            continue
        j = json.load(open(os.path.join(FIG_DIR, f"{name}.json")))
        fw, fh = j["frame_pt"]
        mx, my = j["eyeMid"][0]
        out[name] = dict(file=f"{name}@3x.png", x=round(ex - mx * s, 2), y=round(ey - my * s, 2), w=round(fw * s, 2),
                         h=round(fh * s, 2), z=z, grounded=grounded)
    return out


DOCK_PARTS = os.environ.get("LOADING_DOCK_PARTS") or os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))),
    "build", "ui-art", "parts", "char_digDockPair.png")


def build_dock_pair(ctx):
    """char_digDockL: two small Diggers trotting along the dock at the back left (today's left crowd). LOOK-L: from the
    vinyl Loading pair render (char_cast_d1 `char_digDockPair`, a PARTS render at exactly DOCK_FRAME x 3:
    `$PY art/pipeline/items/char_make.py render char_digDockPair` -> build/ui-art/parts/), a little of the room's haze
    and a touch soft for depth. Falls back to R4's composite of the home rigs if the parts render is missing."""
    x0, y0, fw, fh = DOCK_FRAME
    if os.path.exists(DOCK_PARTS):
        im = Image.open(DOCK_PARTS).convert("RGBA").resize((round(fw * 3), round(fh * 3)), Image.LANCZOS)
        a = np.asarray(im).astype(np.float64) / 255
        # LOOK-2 (the finish judge on v4: "the two small Diggers are crisp while the boxes around them are blurred ... edge
        # density 35 % vs 13.5 % on the original's far figures. FIX: blur the dock pair to match the boxes (sigma ~2-3 px
        # @3x) and lower their contrast slightly for distance haze"): the room's azure haze + a lower contrast, then the
        # mid-ground defocus (premultiplied, so the edge does not grow a dark fringe)
        lum = (a[..., :3] @ np.array([0.299, 0.587, 0.114]))[..., None]
        a[..., :3] = lum + (a[..., :3] - lum) * 0.92
        a[..., :3] = a[..., :3] + (rgb(DOCK_HAZE) - a[..., :3]) * DOCK_HAZE_K
        a[..., :3] = 0.5 + (a[..., :3] - 0.5) * DOCK_CONTRAST
        from scipy import ndimage
        pre = np.concatenate([a[..., :3] * a[..., 3:4], a[..., 3:4]], -1)
        pre = np.stack([ndimage.gaussian_filter(pre[..., ch], DOCK_BLUR_PX) for ch in range(4)], -1)
        out = np.zeros_like(pre)
        out[..., :3] = pre[..., :3] / np.maximum(pre[..., 3:4], 1e-6)
        out[..., 3] = pre[..., 3]
        return Image.fromarray(np.clip(out * 255, 0, 255).astype(np.uint8), "RGBA")
    cv = Image.new("RGBA", (round(fw * 3), round(fh * 3)), (0, 0, 0, 0))
    for (name, fx, feet_y, s) in (("char_dig_homeR", 34.0, 66.0, 0.40), ("char_dig_homeL", 70.0, 62.0, 0.36)):
        im = Image.open(os.path.join(K_OUT, f"{name}@3x.png")).convert("RGBA")
        j = json.load(open(os.path.join(FIG_DIR, f"{name}.json")))
        ftx, fty = j["feet"][0]
        im = im.resize((round(im.width * s), round(im.height * s)), Image.LANCZOS)
        a = np.asarray(im).astype(np.float64) / 255
        a[..., :3] = a[..., :3] + (rgb("#E9D9BC") - a[..., :3]) * 0.16          # a little of the room's haze
        im = Image.fromarray(np.clip(a * 255, 0, 255).astype(np.uint8), "RGBA").filter(ImageFilter.GaussianBlur(0.9))
        px = round((fx - ftx * s) * 3)
        py = round((feet_y - fty * s) * 3)
        lay = Image.new("RGBA", cv.size, (0, 0, 0, 0))
        lay.paste(im, (px, py))
        cv.alpha_composite(lay)
    return cv


# ====================================================================== contact shadows under the grounded cast
def cast_shadows(cv, log=print):
    """Soft warm pools under each grounded figure (the flags do not mirror). LOOK-L: the footprint is the SOLID
    (alpha > 0.8: not the cart's dust puffs) lowest ~22 % of the figure, at least 0.45 of its solid width, so a
    runner mid-stride or a cart on its wheels gets a pool under its whole base (R4 sized it from the lowest 18 rows:
    a toe-sized dot)."""
    X, Y = cv.X, cv.Y
    for name, c in layout_frames().items():
        if not c["grounded"]:
            continue
        p = _figure_path(c)
        if p is None:
            log(f"  WARNING cast: {c['file']} missing (no shadow)")
            continue
        a = np.asarray(Image.open(p).convert("RGBA")).astype(np.float64)[..., 3] / 255
        solid = a > 0.8
        rows = np.where(solid.any(1))[0]
        if not len(rows):
            continue
        ytop, yb = rows[0], rows[-1]
        band = solid[max(ytop, yb - int(0.22 * (yb - ytop))):yb + 1]
        cols = np.where(band.any(0))[0]
        allc = np.where(solid.any(0))[0]
        sx = c["w"] / (a.shape[1] / 3.0)
        sy = c["h"] / (a.shape[0] / 3.0)
        x0 = c["x"] + cols[0] / 3.0 * sx
        x1 = c["x"] + cols[-1] / 3.0 * sx
        fy = c["y"] + yb / 3.0 * sy
        fx = (x0 + x1) / 2
        wdt = max(14.0, x1 - x0, 0.45 * (allc[-1] - allc[0]) / 3.0 * sx)
        g = np.exp(-(((X - fx) / (wdt * 0.58)) ** 2 + ((Y - fy + 1.5) / (wdt * 0.10 + 2.5)) ** 2) * 1.2)
        cv.multiply(np.clip(g, 0, 1), "#1E4A7A", 0.42)
        g2 = np.exp(-(((X - fx) / (wdt * 0.40)) ** 2 + ((Y - fy + 0.8) / (wdt * 0.030 + 1.6)) ** 2) * 1.5)
        cv.multiply(np.clip(g2, 0, 1), "#0A2A4C", 0.50)


def _figure_path(c):
    p = os.path.join(FIG_DIR, c["file"])
    if not os.path.exists(p):                       # a draft run: the dock pair built just before, into the draft dir
        from scene_kit import BUILD as _KB
        p = os.path.join(_KB, "draft", c["file"].replace("@3x", ""))
    return p if os.path.exists(p) else None


REFL_ALPHA = 0.30
REFL_FADE_PT = 46.0


def cast_reflections(cv, log=print):
    """LOOK-L fix round 1 (the judges: "the floor is flat, matte ... the original's floor has soft glossy falloff and
    reflections"): each grounded figure mirrored on the polished flags under its feet -- flipped about its lowest solid
    row, foreshortened (x0.55), blurred, faded over ~46 pt and tinted toward the floor, on floor pixels only."""
    X, Y = cv.X, cv.Y
    from scipy import ndimage
    acc = np.zeros((cv.h, cv.w, 4))
    for name, c in layout_frames().items():
        if not c["grounded"]:
            continue
        p = _figure_path(c)
        if p is None:
            log(f"  WARNING reflection: {c['file']} missing")
            continue
        im = Image.open(p).convert("RGBA").resize((max(1, round(c["w"] * 3)), max(1, round(c["h"] * 3))), Image.LANCZOS)
        a = np.asarray(im).astype(np.float64) / 255
        solid = a[..., 3] > 0.8
        rows = np.where(solid.any(1))[0]
        if not len(rows):
            continue
        yb = rows[-1]
        top = a[:yb + 1][::-1]                                   # flipped about the feet row
        hh = max(1, int(round(top.shape[0] * 0.55)))
        top = np.asarray(Image.fromarray((top * 255).astype(np.uint8), "RGBA").resize((top.shape[1], hh), Image.LANCZOS)).astype(np.float64) / 255
        fade = np.exp(-(np.arange(hh) / (REFL_FADE_PT * 3)) ** 1.5)[:, None]
        top[..., 3] *= fade * REFL_ALPHA
        x0 = int(round(c["x"] * 3))
        y0 = int(round(c["y"] * 3 + yb + 1))
        ya, yb2 = max(0, y0), min(cv.h, y0 + hh)
        xa, xb = max(0, x0), min(cv.w, x0 + top.shape[1])
        if ya >= yb2 or xa >= xb:
            continue
        seg = top[ya - y0:yb2 - y0, xa - x0:xb - x0]
        dst = acc[ya:yb2, xa:xb]
        al = seg[..., 3:4]
        dst[..., :3] = seg[..., :3] * al + dst[..., :3] * (1 - al)
        dst[..., 3:4] = al + dst[..., 3:4] * (1 - al)
    pre = acc[..., :3]
    al = acc[..., 3]
    sig = 2.2 * 3
    pre = np.stack([ndimage.gaussian_filter(pre[..., ch], sig) for ch in range(3)], -1)
    al = ndimage.gaussian_filter(al, sig)
    col = pre / np.maximum(al[..., None], 1e-6)
    col = col + (rgb("#629BCD") - col) * 0.22
    al = al * smooth(Y, FLOOR_TOP + 2, FLOOR_TOP + 12)
    src = np.concatenate([np.clip(col, 0, 1), np.clip(al, 0, 1)[..., None]], -1)
    cv.over(src)


# ====================================================================== build
def build_loading(ctx):
    """LOOK-L: the same layers and object types as R4 (ruling 46), high-key, calm, with a real DEPTH OF FIELD built
    per layer (the renderer has none): the far room defocused hard, the floor by its homography depth (sharp where the
    crew runs, soft toward the horizon and a little at the bottom edge), the mid props soft; contact shadows after the
    floor blur; the flying arrows on top with their own small blur; a warm light bloom instead of R4's dark vignette."""
    cv = Canvas(393, 852)
    c = dict(center=False)
    from scene_kit import scene_env
    fly_rig = rig(key_lux=2400.0, fill_lux=520.0, fill_color=(1.0, 0.95, 0.88), rim_color=(1.0, 0.97, 0.92), rim_lux=220.0,
                  env=scene_env(**FLY_ENV))
    arrows = {f"ld2_{m}": dict(scene=[(_M, m, dict(center=True, pos=W(*p), R=R, scale=s))], bounds=B_WORLD,
                               aspect=393 / 852, margin=1.0, fov=4.0, px=2400, light=fly_rig)
              for (m, p, R, s, hz, bl) in FLY}
    specs = {
        "ld1Crates": dict(scene=[(_M, "crates_d1", c)], bounds=B_WORLD, aspect=393 / 852, margin=1.0, fov=4.0, px=2400,
                          light=rig(key_lux=2400.0, fill_lux=520.0)),
    }
    specs.update(arrows)
    ims = {k: v.resize((cv.w, cv.h), Image.LANCZOS) for k, v in ctx.render(specs).items()}
    # 1. the room (far: strongly defocused) + the alcove's crates (lamp-lit, pale)
    paint_room(cv)
    ba = np.asarray(ims["ld1Crates"]).astype(np.float64) / 255
    # (LOOK-2 round 2: no pale lift -- v5's "+ 0.06" washed the crates to cardboard; a touch of the room's haze only)
    ba[..., :3] = ba[..., :3] + (rgb("#B7D6EE") - ba[..., :3]) * 0.08
    cv.over(np.clip(ba, 0, 1))
    cv.a = dof_stack(cv.a, room_coc(cv))
    # 2. the floor, defocused by depth
    Lf = layer(cv)
    paint_floor(Lf)
    Lf.a = floor_dof(Lf.a)
    cv.over(Lf.a)
    del Lf
    cast_reflections(cv)
    # 3. dock + machine + props (mid distance, soft)
    for fn, sig in ((paint_dock, MID_BLUR_PT), (paint_machine, MID_BLUR_PT * 1.2), (paint_props, 0.9)):
        L = layer(cv)
        fn(L)
        blur_over(cv, L, sig)
        del L
    # 4. the cast's contact shadows (under the rope and the arrows)
    cast_shadows(cv)
    # 5. (fix round 2: the rope is gone -- the rails are painted into the floor layer)
    # 6. the flying arrows (the pale pair under the logo defocused and hazed)
    for (m, p, R, s, hz, bl) in FLY:
        a = np.asarray(ims[f"ld2_{m}"]).astype(np.float64) / 255
        # LOOK-L fix round 1 (the judges: "make the backdrop's flying arrows saturated and crisper"): the sprite rig
        # renders the enamel a little dull (the sunflower read ochre) -> a saturation + value lift on the arrow only
        lum = (a[..., :3] @ np.array([0.299, 0.587, 0.114]))[..., None]
        a[..., :3] = np.clip((lum + (a[..., :3] - lum) * ARROW_SAT) * ARROW_VAL, 0, 1)
        if hz:
            a[..., :3] = a[..., :3] + (rgb("#B7D6EE") - a[..., :3]) * hz
        La = layer(cv)
        La.a = a
        blur_over(cv, La, bl)
        del La
    # 7. the daylight pool's bloom (one warm-white light behind the boss, falling off to the edges) + a cool frame:
    # the top corners and the bottom-left fall into a deeper cerulean (value structure; the logo sits in the dark)
    X, Y = cv.X, cv.Y
    cv.screen(np.exp(-(((X - POOL_C[0]) / 150.0) ** 2 + ((Y - POOL_C[1]) / 170.0) ** 2)), "#EEF4FA", 0.16)
    # LOOK-2 round 2: the DOORWAY's daylight -- a wide, near-neutral cool-white bloom over the exit (L* 92-96 at its
    # core), so the light reads as light and the page is as high-key as the original's
    cv.screen(np.exp(-(((X - DOOR_GLOW_C[0]) / DOOR_GLOW_R[0]) ** 2 + ((Y - DOOR_GLOW_C[1]) / (DOOR_GLOW_R[0] * 0.9)) ** 2)),
              BACKGLOW_COL, DOOR_GLOW_K[0])
    cv.screen(np.exp(-(((X - DOOR_GLOW_C[0]) / DOOR_GLOW_R[1]) ** 2 + ((Y - DOOR_GLOW_C[1]) / (DOOR_GLOW_R[1] * 0.8)) ** 2)),
              BACKGLOW_COL, DOOR_GLOW_K[1])
    # LOOK-2 (the finish judge on v4: "the doorway is a dull blue-beige haze. The original's luminous glow that pops
    # its boss is missing ... FIX: a soft warm-white bloom centred behind the boss's head and shoulders (core L* 88-95,
    # wide falloff)"): a warm-white BACK-GLOW behind the boss -- a tight core round his head / shoulders + a wide halo
    bx, by = BACKGLOW_C
    cv.screen(np.exp(-(((X - bx) / BACKGLOW_R[0]) ** 2 + ((Y - by) / (BACKGLOW_R[0] * 1.15)) ** 2)), BACKGLOW_COL, BACKGLOW_K[0])
    cv.screen(np.exp(-(((X - bx) / BACKGLOW_R[1]) ** 2 + ((Y - by) / (BACKGLOW_R[1] * 1.10)) ** 2)), BACKGLOW_COL, BACKGLOW_K[1])
    cv.multiply(np.exp(-(((X + 30) / 170.0) ** 2 + ((Y - 880) / 150.0) ** 2)), "#0A2A4C", 0.32)
    cv.multiply(np.exp(-(((X - 430) / 150.0) ** 2 + ((Y - 900) / 170.0) ** 2)), "#0A2A4C", 0.22)
    # 8. a fine luminance grain (sigma GRAIN / 255): dithers the soft gradients (no 8-bit banding on the phone) and
    # gives the defocused surfaces the micro-texture a painted / rendered plate has (measured: R4-v2's floor was 10x
    # smoother than the original's at the finest scale)
    rng = np.random.default_rng(97)
    n = rng.normal(0.0, GRAIN / 255.0, (cv.h, cv.w))
    cv.a[..., :3] = np.clip(cv.a[..., :3] + n[..., None], 0, 1)
    return cv.image()


GRAIN = 0.9
BACKGLOW_C = (192.0, 418.0)       # pt: behind the boss's head / shoulders (his eye point is (190, 402))
BACKGLOW_R = (70.0, 165.0)        # pt: the core, the halo
BACKGLOW_K = (0.55, 0.24)         # screen strengths
BACKGLOW_COL = "#F3F8FD"          # LOOK-2 round 2: near-neutral, a touch cool (v5's #FFF2DA read as a beige haze)
DOOR_GLOW_C = (318.0, 402.0)      # pt: the doorway's daylight (behind the right pair)
DOOR_GLOW_R = (70.0, 190.0)
DOOR_GLOW_K = (0.34, 0.18)
ARROW_SAT = 1.15           # the flying arrows' grade (fix round 1)
ARROW_VAL = 1.04


ROOM_BLUR_PX = (2.2, 6.5)   # the room's defocus (@3x px): the vault / walls / machine side .. the far yard (R4: 2.2)
MID_BLUR_PT = 1.1          # the dock / machine (R4 0.45-0.55)
FLOOR_FAR_PX = 6.0         # the floor's defocus toward the horizon (@3x px) ...
FLOOR_NEAR_PX = 2.5        # ... and at the bottom edge; sharp where the crew runs (y ~600-720 pt)
FOCUS_Y = (600.0, 720.0)


def floor_dof(a):
    """A thin-lens-like blur of the floor layer by its homography depth (1 / pt-per-uv ~ distance, normalised to 1 in
    the crew band): CoC far = FLOOR_FAR_PX (1 - 1/d)/0.75, near = FLOOR_NEAR_PX (1/d - 1)/0.6, interpolated over a
    premultiplied blur stack."""
    from scipy import ndimage
    h, w = a.shape[:2]
    yy, xx = np.mgrid[0:h, 0:w]
    X, Y = (xx + 0.5) / 3, (yy + 0.5) / 3
    u, v = floor_uv(X, Y)
    gv = np.hypot(*np.gradient(v)) * 3.0
    band = (Y > FOCUS_Y[0]) & (Y < FOCUS_Y[1])
    dist = gv / np.median(gv[band])
    dist = np.where(Y < FLOOR_TOP - 2, 4.0, np.clip(dist, 0.3, 4.0))
    dist = ndimage.gaussian_filter(dist, 10)
    coc = np.where(dist >= 1.0, FLOOR_FAR_PX * np.clip((1 - 1 / dist) / 0.75, 0, 1),
                   FLOOR_NEAR_PX * np.clip((1 / dist - 1) / 0.6, 0, 1))
    return dof_stack(a, coc)


def room_coc(cv):
    """The room's defocus map (@3x px): the vault, walls and machine side ROOM_BLUR_PX[0]; the yard seen through the
    doorway (the farthest thing) ROOM_BLUR_PX[1], feathered."""
    X, Y = cv.X, cv.Y
    top = OPEN_TOP(X)
    yard = smooth(X, OPEN_X0 - 6, OPEN_X0 + 14) * smooth(Y, top - 4, top + 16) * (1 - smooth(Y, 490, 510))
    return ROOM_BLUR_PX[0] + (ROOM_BLUR_PX[1] - ROOM_BLUR_PX[0]) * yard


def dof_stack(a, coc):
    """Per-pixel Gaussian defocus (sigma = coc, @3x px) of a float RGBA array: a premultiplied blur stack with hat
    weights between neighbouring levels."""
    from scipy import ndimage
    pre = np.concatenate([a[..., :3] * a[..., 3:4], a[..., 3:4]], -1).astype(np.float32)
    sig = [0.0, 1.5, 3.0, 5.0, 8.0, 12.0, 18.0]
    idx = np.interp(coc, sig, np.arange(len(sig))).astype(np.float32)
    out = np.zeros_like(pre)
    for i, s in enumerate(sig):
        wgt = np.clip(1 - np.abs(idx - i), 0, 1)[..., None]
        if not wgt.any():
            continue
        lvl = pre if s == 0 else np.stack([ndimage.gaussian_filter(pre[..., ch], s) for ch in range(4)], -1)
        out += lvl * wgt
        del lvl
    res = np.zeros(a.shape)
    res[..., :3] = out[..., :3] / np.maximum(out[..., 3:4], 1e-6)
    res[..., 3] = out[..., 3]
    return np.clip(res, 0, 1)


def build_dock(ctx):
    return build_dock_pair(ctx)


BUILDS = {"loadingBackdrop": build_loading, "char_digDockL": build_dock}
