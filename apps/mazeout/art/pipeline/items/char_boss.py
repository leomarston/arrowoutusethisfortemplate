"""R2 CAST (PLAN-P §4.2; SPEC rulings 37b / 38; design/publish/art-direction.md §1.3, §3.0, §3.1): the pink BOSS v2 --
production recipe + home rig. Forked from R1's char_concepts_d1.boss_v2 (the draft file is left as R1 wrote it).

What changed vs today's scientist (ruling 38, the MINIMAL set) -- kept: the pink strand-fur head, its eye/brow language,
the smile, the fur ladder, his size and role:
  - two furry pink monster EARS (owner, SPEC ruling 44: "the horns of our new pink monster should not be horns but
    ears"; they replace R2's ivory horns and the old crown tuft): broad rounded leaves with a slightly pointed tip,
    set where the horns were (the top corners of the dome), angled out + up; the outside in the head's own pink strand
    fur combed toward the tip (a short tuft at each tip), a hollowed inner ear in the softer lighter blush with short
    velvet fur. They are part of the head's skin SDF and strand set (one material, R2), not a new rig layer;
  - a BLUSH MUZZLE: one strand set with one groom, split into LUT bands that step from the pink ladder to the blush
    (char_d1kit.banded_fur_parts) -- the orchestrator's 04:32 fix (R1's two dithered strand sets read speckled);
    BOSS-EARS pass: the blush keeps the body's saturation (the pale ladder read beige, a stain), 11 bands (finer
    dither steps), denser + barely shorter muzzle fur over a matching skin, calmer per-strand tone jitter;
  - AMBER irises; ONE snaggle FANG (upper left), 1.4x R1's and clean ivory so it reads at 1/3 size (04:32);
  - brass GOGGLES pushed up between the ears;
  - a teal canvas FOREMAN COAT (placket, brass buttons, rounded corduroy collar, breast pocket + blueprint roll; rolled
    sleeves, corduroy cuffs, fur forearms) instead of the lab coat / lanyard / badge / pen;
  - a timber SCAFFOLD RAIL + brass LEVER (station()) instead of the console: one paw grips the rail, one the lever.

Rig `boss_home` (art/out/char_boss_home_rig/): the SAME layer names, groups and pivots as char_sci_home_rig, so the
ui.json puppet tracks (torso breathe about (95.3, 164) = the frame's bottom centre, head nod/tilt about `neck`, arms
+-1.2 deg about `shoulder`, lids overlays) apply unchanged: torso | armL | armR (group armR, default) | armR_point |
headSmile (group head, default) | headOpen | lidsHalf, lidsClosed (overlays, parent head). Same frame (190 x 164 pt),
camera and scale (66.8 pt/u) as the scientist. The STATION is not a rig layer (the rest-pose test pins exactly
{torso, armL, armR, headSmile}); it is rendered from the same camera as `char_bossStation` (route3d, for R3 HOME, who
owns `homeScaffold`) and drawn between the torso/head stage and the arms stage, like homeConsole today.
Placement: TODAY's spot, centred behind the station (R3 HOME 09:19, ruling 46: the same composition); R3 owns it
(`place` below is data; `rig.py --skip-render` re-exports without rendering).
"""
from __future__ import annotations

import numpy as np

import char_d1kit as D
import char_fur as FUR
import char_kit as K
import char_scientist as S
from mesher import Material
from uikit import (Part, box, capsule, cylinder, ellipsoid, extrude, gloss, glass, metal, polygon2, round_cone,  # noqa: F401
                   satin, sphere, torus, union)
from sdf import fillet_points

VOXEL = 0.006

# ================================================================== palette
B_IRIS = "#D9951F"
# the blush ladder of the muzzle AND the inner ears, same rows as S.FUR_STOPS (0 deep root, 0.35 root, 1 tip): the pink
# body ladder ~1.5 steps LIGHTER at the same hue, keeping most of its chroma (CIELAB C* 25-52 vs the body's 36-66).
# R2 v1's #FFD6E4 -> #FFC1D6 ladder (C* 14-46) measured C* 32 vs the body's 46 in the render and read beige / a stain
# (build/p/BOSSEARS/muzzle-*.json); a smaller root -> tip step than the body's keeps overlapping strands from speckling
# (a touch cooler than the body -- LUT hue -10 vs -5 -- because the warm D1 key pushes a light pink toward peach)
MUZ_STOPS = [(0.0, [(0.0, "#FA9FCA"), (0.5, "#EF88B9"), (1.0, "#E071A6")]),
             (0.35, [(0.0, "#FFC4DE"), (0.35, "#FFB2D4"), (0.6, "#FE9FC9"), (1.0, "#F288BA")]),
             (1.0, [(0.0, "#FFCCE2"), (0.35, "#FFBCD9"), (0.6, "#FFA8CE"), (1.0, "#F592C0")])]
# the skin UNDER the blush (the gaps between strands show it): the blush ladder's root row, so no gap reads darker
MUZ_SKIN = [(0.0, "#FFBAD8"), (0.5, "#FDA2CB"), (0.8, "#F48CBE"), (1.0, "#E274AA")]
COAT_T = [(0.0, "#4FB3AF"), (0.40, "#2E8C8A"), (0.72, "#1F6B6B"), (1.0, "#144C4E")]
COAT_T2 = [(0.0, "#44A29E"), (0.40, "#277C7A"), (0.72, "#1A5E5E"), (1.0, "#114244")]
CORD = [(0.0, "#2F817E"), (0.45, "#1F6B6B"), (0.8, "#164F50"), (1.0, "#0D3436")]
# LOOK-L: the Loading's high-key coat (the same teal canvas, ~1.5 steps lighter: the centre boss must not be the
# darkest mass of the screen)
_COAT_T, _COAT_T2, _CORD = COAT_T, COAT_T2, CORD
COAT_T_LOAD = [(0.0, "#8FDCD2"), (0.40, "#5BBDB5"), (0.72, "#3F9C96"), (1.0, "#2A7672")]
COAT_T2_LOAD = [(0.0, "#84D0C6"), (0.40, "#52AFA8"), (0.72, "#398F89"), (1.0, "#256A66")]
CORD_LOAD = [(0.0, "#5DB8B1"), (0.45, "#3F9892"), (0.8, "#2E7A75"), (1.0, "#1E5552")]
# fix round 1: the home teal, half a step lighter (on the cool ground the boss stands in front of the warm daylight pool:
# a mid teal separates by value there; v2's pale teal washed out)
COAT_T_L2 = [(0.0, "#6AC9C2"), (0.40, "#3FA39F"), (0.72, "#2B807E"), (1.0, "#1A5A5B")]
COAT_T2_L2 = [(0.0, "#5FB8B2"), (0.40, "#37928E"), (0.72, "#247170"), (1.0, "#164F50")]
CORD_L2 = [(0.0, "#46A09B"), (0.45, "#2F807C"), (0.8, "#22625F"), (1.0, "#15403F")]
BLUEPRINT = [(0.0, "#A9D2F5"), (0.45, "#7FB6E8"), (0.8, "#5A94CF"), (1.0, "#3A6FA8")]
TOOTH = "#FFF8EA"
MUZ_C = np.array([0.015, 0.505])
FUR_BANDS = 11
# the EARS (head space; x per side): where the root enters the dome (the horns' spot), the base -> tip axis (out + up;
# ~42 deg from vertical, so with the home head roll the screen-left ear's fur tip stays >= 2.5 pt inside the 190 x 164
# frame, like the horn tip did), the direction the hollowed front faces (the camera, a little outward), the length
# (root -> tip, the root sunk EAR_SINK under the skin) and the leaf's half-width / flatness (thickness = 2 W T)
EAR_BASE = (0.270, 0.955)
EAR_AXIS = (0.90, 1.0, -0.08)
EAR_FACE = (0.30, 0.02, 1.0)
EAR_L, EAR_W, EAR_T, EAR_SINK = 0.28, 0.128, 0.40, 0.075

# ================================================================== LOOK-L fix round 1: the Loading boss, style "load2"
# The judges on v2 (style "load"): the face fur read FLOCKED / felt -- flat hot pink, no form shading, no groom; a bald
# pink upper-lip plate over the teeth ("a plastic duck bill"); two blurry magenta smudges for brows; the eyes could be
# ~15-20 % bigger; the copy judge: do NOT make the face lighter / more violet -- a WARMER pink (hue >= 5 deg LAB) widens
# the distance. "load2" = the home pink ladder turned ~9 deg warmer (toward watermelon) and lifted only a little (v2's
# lift 1.12 made it pale and flat), deep warm brow fur, the eyes x1.16, fur grown to the lip edge (short, combed away
# from the mouth), the face fur's form shading restored (only a little shorter than the body fur, not velvet).


def _warm(hexc, dh=9.0, v=1.05, s=1.06):
    import colorsys
    r, g, b = K.hexrgb(hexc)
    h, ss, vv = colorsys.rgb_to_hsv(r, g, b)
    h = (h + dh / 360.0) % 1.0
    r, g, b = colorsys.hsv_to_rgb(h, min(1.0, ss * s), min(1.0, vv * v))
    return "#%02X%02X%02X" % tuple(int(round(c * 255)) for c in (r, g, b))


def _warm_stops(stops, **kw):
    return [(v, [(u, _warm(c, **kw)) for u, c in row]) for v, row in stops]


FUR_STOPS_L2 = _warm_stops(S.FUR_STOPS)
SKIN_L2 = [(u, _warm(c)) for u, c in S.SKIN]
BROW_STOPS_L2 = [(0.0, [(0.0, "#7C1636"), (1.0, "#5A0E26")]), (0.35, [(0.0, "#9A2446"), (1.0, "#7C1636")]),
                 (1.0, [(0.0, "#B8405E"), (1.0, "#9A2446")])]
BROW_SKIN_L2 = [(0.0, "#9A2446"), (0.5, "#7C1636"), (1.0, "#5A0E26")]
# no pale blush patch on the load2 muzzle (it read as a separate plate): the body ladder, a touch lighter
MUZ_STOPS_L2 = _warm_stops(S.FUR_STOPS, dh=9.0, v=1.09, s=1.02)
MUZ_SKIN_L2 = [(u, _warm(c, dh=9.0, v=1.09, s=1.02)) for u, c in S.SKIN]
EYE_K2 = 1.16          # the "load2" eyes (x, y radii; z a little less so they stay in the face)

# ================================================================== LOOK-L fix round 2: style "load3" (the Loading boss)
# The finish judge on v3 (load2): the face fur and mittens read FLOCKED SANDPAPER (short uniform fuzz, pixel speckle,
# HF energy 1.4-1.8 vs the original's 1.0-1.3); the coat carries dark mottled blotches and no folds; the boots are shiny
# plasticine with cream disc soles; the face reads startled / shouting -- lidless eyes with a thin orange iris ring, a
# rectangular gape, maroon caterpillar brows, boar jowls, a wire of goggles. "load3" = load2's warm pink ladder with:
# LONGER groomed fur in clumped locks + a few flyaway strands on the outline (wider strands at a lower density so they
# resolve as strands at 3x, a calmer per-strand tone), upper LIDS over ~18 % of each eye, broad amber-brown irises with a
# dark limbal ring, a SMILE (corners up, one tooth row), brows in a deeper shade of the fur, shorter jowl fur, real
# brass goggles on a leather band; a clean canvas coat with sewn folds; matte leather boots on dark rubber soles.
EYE_K3 = 1.20
BROW_STOPS_L3 = [(0.0, [(0.0, "#96203F"), (1.0, "#761632")]), (0.35, [(0.0, "#AC2A4C"), (1.0, "#96203F")]),
                 (1.0, [(0.0, "#C23A5E"), (1.0, "#AC2A4C")])]
BROW_SKIN_L3 = [(0.0, "#AC2A4C"), (0.5, "#96203F"), (1.0, "#761632")]
B_IRIS3 = [(0.0, "#F2B04A"), (0.45, "#D98A22"), (0.8, "#B06414"), (1.0, "#7A400A")]
B_LIMBAL = "#4A2408"
GOGGLE_BRASS4 = [(0.0, "#F4C458"), (0.35, "#D29830"), (0.70, "#9C6414"), (1.0, "#5A3404")]     # LOOK-2: saturated brass rims
LID_CREASE3 = "#7A1838"

# ================================================================== LOOK-2 round 2: style "load5" (the Loading boss, v6)
# The finish judge on v5 (load4): "one flat hot-pink tone with speckly bright strand tips, reading as a pompom or terry
# towel rather than groomed plush (fur highlight headroom p95 - p50 L* 9.7 vs the original's 25.5) ... FIX: a deep
# crimson-root to light-pink-tip ramp, larger clumped locks with one flow direction, lower tip-brightness jitter, and a
# soft top key"; "every eye white clips to paper white"; the coat "an inflatable teal balloon ... no fabric cue". load5 =
# load4's head geometry with: this LONGER root -> tip ladder (the same rose hue family, LAB h ~7-12 deg: never violet),
# bigger calmer locks, an off-white sclera with a lid shadow; a canvas-weave coat with stitched seams, drag folds that
# converge on the belt, straight pocket flaps, a canvas keeper over the belt (no square buckle: the copy judge's echo)
# (r2 test render: the first ladder moved the fur's L* p50 only 61 -> 58 -- most strands sit at obscurance u > 0.5, so
# the crease half of every row is what shows: that half is now much deeper; the lit tips stay light)
# (r2 pass 4: the visible outer layer sits at strand tone v ~0.6-0.9 -- rendered fur L* p95 stayed ~70 with the light row
# at v 1.0 only; the light row now starts at v 0.84, the mid row at 0.58, so a lock's outer third catches the light)
FUR_STOPS_L5 = [(0.0, [(0.0, "#B82452"), (0.5, "#8A1440"), (1.0, "#5A0826")]),
                (0.32, [(0.0, "#E24474"), (0.35, "#C82C60"), (0.6, "#AA1E4E"), (1.0, "#7A1036")]),
                (0.58, [(0.0, "#FF7494"), (0.35, "#EE5480"), (0.6, "#D63C6C"), (1.0, "#AA2654")]),
                (0.84, [(0.0, "#FFC6D2"), (0.35, "#FFB2C4"), (0.6, "#FC9CB4"), (1.0, "#EA80A0")]),
                (1.0, [(0.0, "#FFD0DC"), (0.35, "#FFBECC"), (0.6, "#FFAABE"), (1.0, "#F08CA8")])]
SKIN_L5 = [(0.0, "#E84476"), (0.5, "#CC2E62"), (0.8, "#A81C4C"), (1.0, "#7C1036")]
MUZ_STOPS_L5 = _warm_stops(FUR_STOPS_L5, dh=0.0, v=1.06, s=0.97)
MUZ_SKIN_L5 = [(u, _warm(c, dh=0.0, v=1.06, s=0.97)) for u, c in SKIN_L5]
SCLERA_B5 = [(0.0, "#D4D8DE"), (0.45, "#C8CDD4"), (0.75, "#B6BCC4"), (1.0, "#99A0AA")]
SCLERA_B5_SH = [(0.0, "#BCC1C9"), (0.45, "#AEB4BD"), (0.75, "#9DA4AE"), (1.0, "#848B96")]
COAT_T5 = [(0.0, "#6ECBC3"), (0.35, "#5CBBB4"), (0.70, "#4AA8A2"), (1.0, "#378E89")]      # the canvas, lit threads
COAT_T5W = [(0.0, "#62BEB6"), (0.35, "#51AEA7"), (0.70, "#409A95"), (1.0, "#2F817C")]     # the weave's shaded threads
# home5: the home boss's eye whites under the home light (the load5 ladder read grey there): an off-white, still < paper
SCLERA_H5 = [(0.0, "#F6F4F0"), (0.45, "#EEECE8"), (0.75, "#E0DED9"), (1.0, "#C6C4BF")]
SCLERA_H5_SH = [(0.0, "#E2E0DC"), (0.45, "#D8D6D2"), (0.75, "#C8C6C1"), (1.0, "#AEACA7")]
THREAD5 = [(0.0, "#F0E8D2"), (0.45, "#DDD0B0"), (0.8, "#BAAA86"), (1.0, "#887858")]      # cream top-stitching


def sclera_vfn5(eyes, to_head):
    """load5 sclera: 1 in the upper lid's shadow band + a falloff toward the rim (head space; eyes = eyes_of(style))."""
    cs = np.array([E["c"] for E in eyes], float)
    rs = np.array([E["r"][:2] for E in eyes], float)

    def fn(v):
        q = to_head(np.asarray(v, float))
        dd = np.stack([np.hypot((q[:, 0] - c[0]) / r[0], (q[:, 1] - c[1]) / r[1]) for c, r in zip(cs, rs)], 0)
        i = np.argmin(dd, 0)
        ty = (q[:, 1] - cs[i, 1]) / rs[i, 1]
        rr = dd[i, np.arange(len(q))]
        top = np.clip((ty - 0.26) / 0.64, 0, 1) ** 1.4
        rim = np.clip((rr - 0.55) / 0.45, 0, 1) ** 2
        return np.clip(np.maximum(top, 0.45 * rim), 0, 1)
    return fn


def pal2(style):
    """The boss palettes per style (home / load = char_scientist.pal; load2 = the warm ladder above; load3 = load2 with
    brows in a deeper shade of the fur)."""
    if style == "load2":
        return dict(fur=FUR_STOPS_L2, skin=SKIN_L2, brow=BROW_STOPS_L2, browskin=BROW_SKIN_L2, tongue="#E0384E",
                    muz=MUZ_STOPS_L2, muzskin=MUZ_SKIN_L2)
    if style == "load5":
        return dict(fur=FUR_STOPS_L5, skin=SKIN_L5, brow=BROW_STOPS_L3, browskin=BROW_SKIN_L3, tongue="#E0384E",
                    muz=MUZ_STOPS_L5, muzskin=MUZ_SKIN_L5)
    if style in ("load3", "load4"):
        return dict(fur=FUR_STOPS_L2, skin=SKIN_L2, brow=BROW_STOPS_L3, browskin=BROW_SKIN_L3, tongue="#E0384E",
                    muz=MUZ_STOPS_L2, muzskin=MUZ_SKIN_L2)
    d = dict(S.pal("load" if style == "load" else "home"))
    d.update(muz=MUZ_STOPS, muzskin=MUZ_SKIN)
    if style == "home6":        # LOOK-2 fix round: brows in a deeper PINK of the fur (not the maroon blotches), softer
        d.update(brow=BROW_STOPS_H6, browskin=BROW_SKIN_H6, tongue="#E0406A")
    return d


def eyes_of(style):
    """char_scientist.EYES, scaled for "load2" / "load3"."""
    if style not in ("load2", "load3", "load4", "load5"):
        return S.EYES
    k = EYE_K3 if style in ("load3", "load4", "load5") else EYE_K2
    return [dict(c=E["c"], r=(E["r"][0] * k, E["r"][1] * k, E["r"][2] * (1 + 0.5 * (k - 1)))) for E in S.EYES]


def density2(F, eyes, lip=0.012):
    """char_scientist.density with this style's eyes; lip = the bare margin kept round the open mouth (load2: small,
    the fur reaches the lip edge)."""
    def fn(p):
        w = np.ones(len(p))
        for E in eyes:
            ex, ey = E["c"]
            rx, ry, _ = E["r"]
            d = np.hypot((p[:, 0] - ex) / (rx * 1.05), (p[:, 1] - ey) / (ry * 1.05))
            w *= np.where((d < 1.0) & (p[:, 2] > 0.1), 0.0, 1.0)
        if "cavity" in F:
            w *= (F["cavity"](np.asarray(p, np.float32)) > lip).astype(float)
        return w
    return fn


# ================================================================== head (head space of char_scientist)

def _fang(tx, ty, tz, down=(0.08, 1.0, 0.30), scale=1.4):
    """One snaggle fang: a rounded, slightly curved canine pointing down, root at (tx, ty, tz)."""
    s = scale
    poly = [(-0.024 * s, 0.010 * s), (0.024 * s, 0.010 * s), (0.008 * s, -0.050 * s), (-0.001 * s, -0.056 * s)]
    fang = polygon2(fillet_points(poly, [0.004 * s, 0.004 * s, 0.007 * s, 0.007 * s], n_arc=4))
    return extrude(fang, 0.011 * s, round=0.009 * s).transform(K.frame_from(list(down), [0.0, -0.25, 1.0])).translate(
        tx, ty, tz)


def _ear_local(o):
    """One ear in its own frame (y = root -> tip, z = the hollowed front, x across; o = +-1, the local x sign that points
    AWAY from the head's centre): a broad rounded leaf -- an ellipsoid body + a short round cone to a slightly pointed
    tip leaning outward -- flattened to a thick pillow, and the front cutter (a shallow bowl) that hollows the inner ear.
    The root (y < 0) is sunk into the dome and smooth-unioned in the skin, so the fur runs over the joint (R2)."""
    body = ellipsoid(EAR_W, 0.155, EAR_W).translate(0, 0.095, 0)
    tipc = round_cone((0.0, 0.10, 0.0), (o * 0.035, EAR_L, 0.0), 0.085, 0.016)
    solid = union(body, tipc, k=0.06).scale_xyz(1.0, 1.0, EAR_T)
    cup = ellipsoid(0.080, 0.112, 0.050).translate(o * 0.006, 0.140, EAR_W * EAR_T + 0.018)
    return solid, cup


def boss_ears(skin0):
    """The two ears in head space: dict(solid, cup (the inner-ear cutters), tips, axes, sx) -- solid already hollowed."""
    solids, cups, tips, axes = [], [], [], []
    for sx in (-1, 1):
        bx, by = sx * EAR_BASE[0], EAR_BASE[1]
        b0 = np.array([bx, by, K.surface_z_of(skin0, bx, by) - EAR_SINK])
        d = K.unit([sx * EAR_AXIS[0], EAR_AXIS[1], EAR_AXIS[2]])
        R = K.frame_from(d, K.unit([sx * EAR_FACE[0], EAR_FACE[1], EAR_FACE[2]]))
        o = 1.0 if float(R[:, 0] @ np.array([sx, 0.0, 0.0])) > 0 else -1.0
        s_, c_ = _ear_local(o)
        cups.append(c_.transform(R).translate(*b0))
        solids.append(s_.transform(R).translate(*b0).subtract(cups[-1], k=0.012))
        tips.append(b0 + R @ np.array([o * 0.035, EAR_L, 0.0]))
        axes.append(d)
    return dict(solid=union(*solids), cup=union(*cups), tips=np.array(tips), axes=np.array(axes))


def friendly_brows(skin, eyes=None, thick=0.65, lift=0.075, spread=0.0, slope=0.020):
    """LOOK-L (the Loading boss; owner 09-28: the boss read "a bit menacing" at size): a raised, thinner, happy arch
    ~0.03 clear of each eye with the INNER ends lifted (the home arch hugs the eye top with low inner ends: cross).
    Laid on this boss's own dome (char_scientist's 'load' brows miss the ear-widened head: bogus bounds)."""
    brows = []
    for i, E in enumerate(eyes or S.EYES):
        ex, ey = E["c"]
        rx, ry, _ = E["r"]
        sx = -1 if i == 0 else 1
        a = np.linspace(-1.0, 1.0, 9)
        xs = ex + sx * (0.018 + spread) + a * rx * 0.66
        ys = ey + ry * 1.00 + lift + 0.034 * (1 - a ** 2) - slope * (a * sx)
        zs = np.array([S.surface_z(skin, x, y) for x, y in zip(xs, ys)])
        for j in range(len(zs)):          # LOOK-2: a point past the dome's edge (a missed ray: z -99) steps down onto it
            while zs[j] < -0.5 and ys[j] > ey:
                ys[j] -= 0.005
                zs[j] = S.surface_z(skin, xs[j], ys[j])
        if (zs < -0.5).any():
            raise ValueError(f"friendly_brows: a brow point misses the head: {zs}")
        rr = (0.022 + 0.022 * (1 - a ** 2) ** 0.6) * thick
        brows.append(K.limb(np.stack([xs, ys, zs + 0.004], 1), rr, k=0.02))
    return union(*brows)


SM2_TOP, SM2_CURV = 0.535, 1.60      # the load3 smile: the upper lip's centre height and how fast the corners rise
R_IRIS3, R_PUPIL3 = 0.084, 0.040


R_PUPIL4 = 0.052          # LOOK-2: the pupil ~60 % of the iris (the judge: "35 % of a large amber iris reads as a stare")


def face3(skin, look, mouth, v4=False):
    """LOOK-L fix round 2 (style "load3"): the parts that replace / join S.face's for the Loading boss -- broad amber
    irises (~62 % of the eye's width) with a dark limbal ring, a small pupil, a bigger key glint; upper LIDS over ~18 %
    of each eye (a shell hugging the eyeball + a deep-pink lash crease: a relaxed, friendly eye, not a lidless stare);
    and for mouth "smile2" a SMILE -- the upper lip an arc whose corners rise into the cheeks, a round bottom, one
    tooth row under the lip, a tongue low in the opening (the corners stay clear of the lower lids)."""
    out = dict(irises=[], pupils=[], glints=[], limbal=[], lids=[], lidcrease=[])
    for i, E in enumerate(eyes_of("load3")):
        ex, ey = E["c"]
        sx = -1 if i == 0 else 1
        ez = S.surface_z(skin, ex, ey)
        rx, ry, rz = E["r"]
        c = np.array([ex, ey, ez - rz * 0.05])
        eye = ellipsoid(rx, ry, rz).translate(*c)
        lx, ly = look
        lxx = -sx * abs(lx) if lx >= 0 else sx * abs(lx)
        d = K.unit([lxx * rx, ly * ry, rz * 1.0])
        sp = c + d * np.array([rx, ry, rz])
        out["irises"].append(eye.offset(0.0016).intersect(sphere(R_IRIS3).translate(*sp)))
        out["limbal"].append(eye.offset(0.0010).intersect(sphere(R_IRIS3 + 0.011).translate(*sp)))
        out["pupils"].append(eye.offset(0.0030).intersect(sphere(R_PUPIL4 if v4 else R_PUPIL3).translate(*sp)))
        gp = c + K.unit(d + np.array([-0.30, 0.34, 0.0])) * np.array([rx, ry, rz])
        out["glints"].append(sphere(0.025 if v4 else 0.021).translate(*(gp + d * 0.006)))
        out["glints"].append(sphere(0.0075).translate(*(c + K.unit(d + np.array([0.30, -0.30, 0.0])) * np.array([rx, ry, rz]))))
        gap = 0.010
        shell = ellipsoid(rx + gap, ry + gap, rz + gap).translate(*c)
        cut = ey + ry * (0.90 if v4 else 0.72)         # the upper lid over the top ~14 % of the eye (v4: a thin rim only)
        out["lids"].append(shell.intersect(box(0.3, 0.3, 0.3).translate(ex, cut + 0.3, c[2]), k=0.008))
        # the smiling lower lid: the cheek pushes up under the eye, its edge an ARC rising to the middle (a happy squint)
        # (v4: subtle -- only the bottom ~8 % of the eye, so the smile does not squint the eye shut)
        out["lids"].append(shell.intersect(ellipsoid(rx * 1.30, ry * 1.0, 1.0).translate(ex, ey - ry * (1.86 if v4 else 1.52), c[2]),
                                           k=0.010))
        if v4:                         # LOOK-2: no crease line (and its ray would miss the thin rim lid: z -4e17)
            continue
        a = np.linspace(-0.93, 0.93, 13)
        xs = ex + a * (rx + 0.006) * np.sqrt(max(0.0, 1 - 0.72 ** 2))
        ys = np.full_like(xs, cut) - 0.002
        zs = np.array([S.surface_z(shell, x, y) for x, y in zip(xs, ys)])
        out["lidcrease"].append(K.limb(np.stack([xs, ys, zs - 0.003], 1), np.full(len(xs), 0.0085), k=0.004))
    out = {k: union(*v) for k, v in out.items() if v}
    if mouth == "smile2":
        zf = S.surface_z(skin, 0.0, 0.46)
        top, curv = SM2_TOP, SM2_CURV
        cav = ellipsoid(0.27, 0.155, 0.30).translate(0, top - 0.02, zf - 0.10).intersect(S.SDF_arc_top(top, curv), k=0.02)
        inner = ellipsoid(0.26, 0.15, 0.22).translate(0, top - 0.03, zf - 0.30).intersect(S.SDF_arc_top(top + 0.01, curv))
        band = ellipsoid(0.200, 0.20, 0.30).translate(0, top - 0.03, zf - 0.12)
        teeth = band.intersect(S.SDF_arc_top(top - 0.008, curv)).subtract(S.SDF_arc_top(top - 0.048, curv), k=0.008)
        tongue = ellipsoid(0.15, 0.062, 0.15).translate(0.012, top - 0.125, zf - 0.19)
        out.update(cavity=cav, inner=inner, teeth=teeth, tongue=tongue)
    return out


# ================================================================== LOOK-2 FIX ROUND: style "home6" (the home boss)
# The finish judge on the LOOK-2 home (build/p/LOOK2/judge: #2 eyes, #9 open mouth, #12 teal on teal, #13 lever mitt)
# and the copy judge (J-copy-home: "the same sideways-down glance with a closed smile and heavy dark brows as their
# monster ... a pen in the chest pocket ... an orange ball-knob lever at his right hand"):
#   eyes   a soft pink UPPER-LID shell over ~15 % of each eyeball (no crease), the irises lifted to the lower centre and
#          aimed at the VIEWER, pupils ~58 % of the iris, a dark limbal ring, two catchlights
#   brows  thinner, higher, in a deeper PINK of the fur (soft), never maroon
#   laugh  a lower, narrower open mouth: a muzzle band between it and the eyes, the fang seated beside the tooth band, a
#          shaded throat and a tongue with volume
#   coat   lifted to a mid teal-GREEN (not the wall's turquoise) with lighter collar / placket / pocket edges, a canvas
#          weave; the blueprint "pen" out of the pocket; a warm rim light (the rig's light)
#   lever  the station's lever ends in a wooden T-HANDLE (brass caps), no ball knob; the paw wraps the bar -- a thumb and
#          chunky finger lobes over it
BROW_STOPS_H6 = [(0.0, [(0.0, "#B03C70"), (1.0, "#962E5E")]), (0.35, [(0.0, "#C64E82"), (1.0, "#B03C70")]),
                 (1.0, [(0.0, "#DC6C9C"), (1.0, "#C64E82")])]
BROW_SKIN_H6 = [(0.0, "#C64E82"), (0.5, "#B03C70"), (1.0, "#962E5E")]
MOUTH6 = [(0.0, "#B8344E"), (0.35, "#8E1E3A"), (0.7, "#5E0E26"), (1.0, "#340616")]      # lit lip edge .. the throat
TONGUE6 = [(0.0, "#FF8AA4"), (0.35, "#F2587C"), (0.7, "#D23A5E"), (1.0, "#A02444")]
GRIN6 = (0.585, 1.05, 0.188)          # the laugh: upper-lip centre y, arc curvature, tooth band half-width
R_IRIS6, R_PUPIL6 = 0.071, 0.041
LOOK6 = (0.0, -0.18)                  # the gaze: straight at the viewer, the irises a little below centre


def face_h6(skin, look=None):
    """home6 eye parts on the HOME eyeballs (char_scientist.EYES): irises / limbal / pupils / glints + upperLids."""
    lx, ly = LOOK6 if look is None else look
    out = dict(irises=[], pupils=[], glints=[], limbal=[], upperLids=[])
    for i, E in enumerate(S.EYES):
        ex, ey = E["c"]
        sx = -1 if i == 0 else 1
        ez = S.surface_z(skin, ex, ey)
        rx, ry, rz = E["r"]
        c = np.array([ex, ey, ez - rz * 0.05])
        eye = ellipsoid(rx, ry, rz).translate(*c)
        d = K.unit([(lx - sx * 0.05) * rx, ly * ry, rz * 1.0])     # a touch convergent: a direct look, not wall-eyed
        sp = c + d * np.array([rx, ry, rz])
        out["irises"].append(eye.offset(0.0016).intersect(sphere(R_IRIS6).translate(*sp)))
        out["limbal"].append(eye.offset(0.0010).intersect(sphere(R_IRIS6 + 0.010).translate(*sp)))
        out["pupils"].append(eye.offset(0.0030).intersect(sphere(R_PUPIL6).translate(*sp)))
        gp = c + K.unit(d + np.array([-0.30, 0.34, 0.0])) * np.array([rx, ry, rz])
        out["glints"].append(sphere(0.020).translate(*(gp + d * 0.006)))
        out["glints"].append(sphere(0.0080).translate(*(c + K.unit(d + np.array([0.30, -0.30, 0.0])) * np.array([rx, ry, rz]))))
        shell = ellipsoid(rx + 0.010, ry + 0.010, rz + 0.010).translate(*c)
        cut = ey + ry * 0.70                                       # the top ~15 % of the eye's height
        out["upperLids"].append(shell.intersect(box(0.3, 0.3, 0.3).translate(ex, cut + 0.3, c[2]), k=0.010))
    return {k: union(*v) for k, v in out.items()}


def grin6(skin):
    """home6 open laugh: lower + narrower than char_scientist's "open" D (whose upper lip cut the eyeballs)."""
    top, curv, bw = GRIN6
    zf = S.surface_z(skin, 0.0, 0.50)
    cav = ellipsoid(0.305, 0.160, 0.30).translate(0, top - 0.03, zf - 0.10).intersect(S.SDF_arc_top(top, curv), k=0.02)
    inner = ellipsoid(0.295, 0.155, 0.22).translate(0, top - 0.04, zf - 0.30).intersect(S.SDF_arc_top(top + 0.01, curv))
    band = ellipsoid(bw, 0.20, 0.30).translate(0, top - 0.03, zf - 0.12)
    teeth = band.intersect(S.SDF_arc_top(top - 0.008, curv)).subtract(S.SDF_arc_top(top - 0.050, curv), k=0.008)
    groove = capsule((0.012, top - 0.090, zf - 0.08), (0.012, top - 0.175, zf - 0.10), 0.010)
    tongue = ellipsoid(0.165, 0.072, 0.15).translate(0.012, top - 0.128, zf - 0.17).subtract(groove, k=0.012)
    return dict(cavity=cav, inner=inner, teeth=teeth, tongue=tongue)


def boss_head_parts(mouth="smile", look=(0.14, -0.40), style="home"):
    """(skin, F) in head space: today's head profile + a muzzle fullness, the ears, goggles, straps and the fang.
    style "load" (LOOK-L): the friendly brows."""
    if style == "load5":          # LOOK-2 round 2: load4's head geometry exactly (the changes are fur / sclera / coat)
        return boss_head_parts(mouth=mouth, look=look, style="load4")
    skin0 = S.head_skin_raw("home")
    zf = K.surface_z_of(skin0, 0.0, 0.57)
    if style not in ("load2", "load3", "load4", "load5"):   # load2 (fix round 1): no muzzle bump -- cut by the open grin it left a smooth upper-lip SHELF
        skin0 = union(skin0, ellipsoid(0.29, 0.155, 0.11).translate(0.01, 0.57, zf - 0.07), k=0.08)     # the muzzle's fullness
    if style in ("load2", "load3", "load4", "load5"):          # S.face reads S.EYES: swap in the bigger eyes for this one call
        saved = S.EYES
        S.EYES = eyes_of(style)
        try:
            F = S.face(skin0, mouth=mouth, look=look, style="home")
        finally:
            S.EYES = saved
        if style == "load3":
            F["brows"] = friendly_brows(skin0, eyes=eyes_of("load3"), thick=0.82, lift=0.078)
            F.update(face3(skin0, look, mouth))
        elif style == "load4":     # LOOK-2: brows UP and APART, the inner ends lifted more (delighted, not cross)
            F["brows"] = friendly_brows(skin0, eyes=eyes_of("load4"), thick=0.86, lift=0.050, spread=0.032, slope=0.046)
            F.update(face3(skin0, look, mouth, v4=True))
        else:
            F["brows"] = friendly_brows(skin0, eyes=eyes_of("load2"), thick=0.95, lift=0.018)
    else:
        F = S.face(skin0, mouth=mouth, look=look, style="home")
    if style == "load":
        F["brows"] = friendly_brows(skin0)
    elif style == "home5":        # LOOK-2 HOME: the home face, a friendlier brow (raised a little, the inner ends lifted)
        F["brows"] = friendly_brows(skin0, thick=0.85, lift=0.048, slope=0.030)
    elif style == "home6":        # LOOK-2 fix round: lidded eyes looking at the viewer, lighter brows, a lower laugh
        F["brows"] = friendly_brows(skin0, thick=0.66, lift=0.056, slope=0.036)
        F.update(face_h6(skin0))
        if mouth == "open":
            F.update(grin6(skin0))
    # the ears join the skin (one material, one strand set); the face, lids, goggles and fang are placed on the dome
    # alone (skin0), exactly as before
    E = boss_ears(skin0)
    F["ears"] = E
    skin = union(skin0, E["solid"], k=0.045)
    if mouth == "smile":
        skin = skin.subtract(F["groove"], k=0.012)
    elif "cavity" in F:
        skin = skin.subtract(F["cavity"], k=0.03)
    skin = skin.subtract(F["sockets"].offset(-0.02), k=0.02)
    F["skin0"] = skin0
    # goggles pushed up between the ears (lenses looking up-forward) + a thin strap back over the crown on each side
    gl, rims, ginner, gglint = [], [], [], []
    gk = {"load3": 1.45, "load4": 1.25}.get(style, 1.0)      # load3: real brass goggles (v3's read as a wire at size)
    # LOOK-2 (load4): the goggles pushed further UP the crown and tilted back (the lenses face the sky, not the camera:
    # with the raised brows they no longer read as a second pair of eyes)
    gdy, gnz = (0.012, 0.80) if style == "load4" else (0.0, 0.95)   # (the dome ends at y ~1.10 at x 0.11: no higher)
    for sx in (-1, 1):
        gx, gy = sx * 0.078 * gk, 1.075 - 0.02 * (gk - 1) + gdy
        gzz = K.surface_z_of(skin0, gx, gy) + 0.030 * gk
        gp = np.array([gx, gy, gzz])
        gn = K.unit([sx * 0.2, 1.0, gnz])
        Rg = K.frame_from(gn, [1, 0, 0])
        rims.append(torus(0.058 * gk, 0.015 * gk * (1.15 if gk > 1 else 1.0)).transform(Rg).translate(*gp))
        rims.append(round_cone(tuple(gp - gn * 0.028 * gk), tuple(gp + gn * 0.006 * gk), 0.068 * gk, 0.064 * gk).subtract(
            cylinder(0.052 * gk, 0.2).transform(Rg).translate(*gp)))
        gl.append(cylinder(0.051 * gk, 0.005 * gk).transform(Rg).translate(*(gp + gn * 0.003 * gk)))
        if style == "load4":     # LOOK-2: a dark inner edge round each lens + ONE white glint on the tinted glass
            ginner.append(torus(0.050 * gk, 0.0055 * gk).transform(Rg).translate(*(gp + gn * 0.006 * gk)))
            gx_ = K.unit(np.cross(gn, [0.0, 0.0, 1.0]) if abs(gn[2]) < 0.99 else [1.0, 0.0, 0.0])
            gy_ = K.unit(np.cross(gx_, gn))
            gglint.append(ellipsoid(0.012 * gk, 0.007 * gk, 0.004 * gk).transform(K.frame_from(gx_, gn)).translate(
                *(gp + gn * 0.010 * gk - gx_ * 0.020 * gk * sx + gy_ * 0.018 * gk)))
    straps = []
    for sx in (-1, 1):
        pts = []
        for t_ in np.linspace(0.0, 1.0, 7):
            x_, y_ = sx * (0.132 * gk + 0.085 * t_ * (1.6 if gk > 1 else 1.0)), 1.072 - 0.02 * (gk - 1) - 0.035 * t_ * (2.0 if gk > 1 else 1.0) + gdy
            z_ = K.surface_z_of(skin0, x_, y_)
            while gk > 1 and not (z_ > -1.0) and abs(x_) > 0.05:   # load3: a ray past the dome's edge -> step inward
                x_ *= 0.94                                            # (a missed ray gave z -99: a 100-unit strap)
                z_ = K.surface_z_of(skin0, x_, y_)
            pts.append([x_, y_, z_ + 0.030 * gk - 0.045 * t_ * (1.3 if gk > 1 else 1.0)])
        straps.append(K.limb(np.array(pts), np.full(7, 0.012 * (1.9 if gk > 1 else 1.0)), k=0.01))
    zb = K.surface_z_of(skin0, 0, 1.085 - 0.02 * (gk - 1) + gdy) + 0.04 * gk
    F["goggles"] = union(*rims, capsule((-0.02 * gk, 1.085 - 0.02 * (gk - 1) + gdy, zb), (0.02 * gk, 1.085 - 0.02 * (gk - 1) + gdy, zb),
                                        0.011 * gk))
    F["goggleLenses"] = union(*gl)
    if ginner:
        F["goggleInner"] = union(*ginner)
        F["goggleGlints"] = union(*gglint)
    F["straps"] = union(*straps)
    # the snaggle fang, screen-left: on the closed smile it pokes down over the lower lip; on the open laugh it hangs
    # from the upper lip beside the tooth band
    if mouth == "smile":
        tx = -0.12
        tt = (tx - (S.SMILE_X[0] + S.SMILE_X[1]) / 2) / ((S.SMILE_X[1] - S.SMILE_X[0]) / 2)
        ty = 0.535 + 0.075 * tt ** 2 + 0.030 * tt ** 8 + S.SMILE_TILT * tx
        tz = K.surface_z_of(skin0, tx, ty)
        F["tooth"] = _fang(tx, ty + 0.006, tz + 0.004)
    elif mouth == "smile2":       # LOOK-L fix round 2: the fang hangs from the smile's upper lip, left of the tooth row
        tx = -0.150
        ty = SM2_TOP + SM2_CURV * tx ** 2 - 0.008
        tz = K.surface_z_of(F["inner"], tx, ty - 0.03) + 0.030
        F["tooth"] = _fang(tx, ty, tz, down=(0.05, 1.0, 0.18), scale=1.15)
    elif mouth == "grin":         # LOOK-L: the smaller open smile (S.face "grin": top 0.60, arc curvature 1.0)
        tx, ty = -0.185, 0.60 + 1.00 * 0.185 ** 2 - 0.010
        tz = K.surface_z_of(F["inner"], tx, ty - 0.03) + 0.030
        F["tooth"] = _fang(tx, ty, tz, down=(0.05, 1.0, 0.18), scale=1.30)
    elif style == "home6":        # LOOK-2 fix round: seated beside the tooth band (the judge: "the fang floats apart")
        tx = -GRIN6[2] - 0.022
        ty = GRIN6[0] + GRIN6[1] * tx ** 2 - 0.010
        tz = K.surface_z_of(F["inner"], tx, ty - 0.03) + 0.034
        F["tooth"] = _fang(tx, ty, tz, down=(0.06, 1.0, 0.20), scale=1.22)
    else:
        tx, ty = -0.205, 0.655 + 0.55 * 0.205 ** 2 - 0.012
        # just IN FRONT of the mouth's dark back wall (R2 v1 buried it inside that solid: invisible)
        tz = K.surface_z_of(F["inner"], tx, ty - 0.04) + 0.035
        F["tooth"] = _fang(tx, ty, tz, down=(0.05, 1.0, 0.18), scale=1.55)
    return skin, F


def muzzle_weight(P):
    """The blush patch: an oval over the mouth + lower cheeks with a wide smooth falloff (head space)."""
    p = np.asarray(P)
    d = np.hypot((p[:, 0] - MUZ_C[0]) / 0.35, (p[:, 1] - MUZ_C[1]) / 0.175)
    m = np.clip((1.10 - d) / 0.58, 0, 1)
    m = m * m * (3 - 2 * m)
    return m * np.clip((p[:, 2] - 0.10) / 0.12, 0, 1)


def ear_weights(F):
    """fn(P) -> (e, inner, tip, axis) per head-space point: e = how much the point is ON an ear (0 on the dome, 1 once
    the ear stands >= 0.035 off it: a smooth ramp over the fur-covered joint), inner = the hollowed inner ear (1 on the
    bowl, a ~0.02 soft rim), tip = closeness to the ear's tip, axis = that side's root -> tip direction."""
    E = F["ears"]
    dome, cup = D.sdf_fn(F["skin0"]), D.sdf_fn(E["cup"])

    def fn(P):
        P = np.asarray(P, float)
        P32 = P.astype(np.float32)
        e = np.clip(dome(P32) / 0.035, 0, 1)
        e = e * e * (3 - 2 * e)
        w = np.clip((0.022 - cup(P32)) / 0.020, 0, 1)            # 1 on the bowl (cup distance ~0), 0 by 0.022 out
        inner = w * w * (3 - 2 * w) * e
        side = (P[:, 0] > 0).astype(int)
        tip = np.exp(-np.sum((P - E["tips"][side]) ** 2, 1) / 0.055 ** 2)
        return e, inner, tip, E["axes"][side]
    return fn


def patch_weight(F):
    """The blush weight: the muzzle patch or the inner ear, whichever is stronger (head space)."""
    ew = ear_weights(F)

    def fn(P):
        return np.maximum(muzzle_weight(P), ew(P)[1])
    return fn


FACE_C = np.array([0.0, 0.62, 0.40])
FACE_R = np.array([0.58, 0.48, 0.66])


def face_weight(P):
    """LOOK-L: 0..1 in head space -- the FRONT of the face (eyes, cheeks, muzzle, brows); the crown, jowl tufts and
    (by the caller) the ears stay 0. The Loading boss's velvet face lives here."""
    P = np.asarray(P, float)
    d = np.linalg.norm((P - FACE_C) / FACE_R, axis=1)
    w = np.clip((1.15 - d) / 0.35, 0, 1) * np.clip((P[:, 2] - 0.10) / 0.20, 0, 1)
    return w * w * (3 - 2 * w)


HEAD_PARTS = ({"skin", "brows", "eyes", "irises", "pupils", "glints", "lipline", "mouth", "teeth", "tongue",
               "tooth", "goggles", "goggleLenses", "goggleStraps", "browfur"} | D.band_names("fur", FUR_BANDS))
LID_PARTS = {"lids", "lidcrease", "lidfur"}


def boss_head_parts_xf(Rw, tw, view_w, mouth="smile", look=(0.14, -0.40), n_strands=48000, seed=3, extra_field=(),
                       field_key=None, eyes="open", style_fur=None, style="home"):
    """The boss head in the world (p' = Rw p + tw), char_scientist.head_parts_xf's contract + the ruling-38 changes.
    style "load" (LOOK-L, the Loading boss): the lighter 'load' pink ladder, the friendly brows and a smooth VELVET
    FACE -- on the face front the strands get shorter, flatter, finer, barely clumped and calmer in tone (the ears,
    crown and jowl tufts keep the home fur)."""
    skin_h, F = boss_head_parts(mouth=mouth, look=look, style=style)
    PAL = pal2(style)
    fur_stops = style_fur or PAL["fur"]
    l2 = style in ("load2", "load3", "load4", "load5")
    l3 = style in ("load3", "load4", "load5")
    l4 = style in ("load4", "load5")
    l5 = style == "load5"
    # LOOK-2 HOME (style "home5"): the HOME boss's head, design, groom and palette, with the Loading boss's SMOOTHER fur
    # TONE (the measured gap: face-fur Laplacian 7.6x the original's = per-strand speckle): a calm root -> tip ramp, a
    # low per-strand jitter + a small lock-level tone, a little more clumping and slightly wider strands; a friendlier
    # brow (raised, inner ends lifted); the clear-coated amber iris, an off-white eye; saturated brass + dark tinted
    # goggle glass (the lenses no longer read as a second pair of eyes). The load3+ face geometry stays load-only.
    h5 = style in ("home5", "home6")
    h6 = style == "home6"
    f2, f3, f5 = l2, l3, l5       # (r2: home5 keeps the HOME groom -- the load3/5 locks + short jowls read as bald
    #                              rubber on the home boss's face; home5 only calms the strand-level tone, below)
    Rw = np.asarray(Rw, float)
    tw = np.asarray(tw, float)
    Ai = np.linalg.inv(Rw)

    def w(s):
        return s.transform(Rw).translate(*tw)

    def wp(P):
        return np.asarray(P, float) @ Rw.T + tw

    def wn(N):
        return np.asarray(N, float) @ Rw.T
    pw = patch_weight(F)

    def muz_vfn(v):
        return pw((np.asarray(v, float) - tw) @ Ai.T)
    parts = [Part("skin", w(skin_h), K.skin("b_skin2" if l2 else "b_skin", PAL["skin"], PAL["muzskin"], vfn=muz_vfn, rough=0.72, ior=1.2),
                  voxel=0.008),
             Part("brows", w(F["brows"]), K.skin("b_browskin3" if l3 else ("b_browskin2" if l2 else "b_browskin"), PAL["browskin"], None,
                                                 vfn=None, rough=0.7, ior=1.2), voxel=0.004),
             Part("eyes", w(F["eyes"]), K.skin("b_eye5", SCLERA_B5, SCLERA_B5_SH, vfn=sclera_vfn5(eyes_of("load4"),
                                                                                                   lambda v: (v - tw) @ Rw),
                                              rough=0.16, ior=1.40, clearcoat=0.30, cc_rough=0.07)
                  if l5 else gloss("b_eyeh5", "#F2EFEB", rough=0.16, ior=1.45) if h5 else gloss("b_eye", S.EYE_WHITE, rough=0.18, ior=1.45), voxel=0.003),
             Part("irises", w(F["irises"]), K.skin("b_iris3", B_IRIS3, None, vfn=None, rough=0.18, ior=1.45, clearcoat=0.6, cc_rough=0.05)
                  if (l3 or h5) else gloss("b_iris", B_IRIS, rough=0.2, ior=1.45), voxel=0.002),
             Part("pupils", w(F["pupils"]), gloss("b_pupil", S.PUPIL, rough=0.15, ior=1.5), voxel=0.002),
             Part("glints", w(F["glints"]), Material("b_glint", "#FFFFFF", roughness=0.3, emissive="#FFFFFF"), voxel=0.0018),
             Part("tooth", w(F["tooth"]), Material("b_tooth", TOOTH, roughness=0.28, ior=1.4, emissive="#8C877C"),
                  voxel=0.0018),
             Part("goggles", w(F["goggles"]), K.skin("b_goggle4" if (l4 or h5) else "b_goggle", GOGGLE_BRASS4 if (l4 or h5) else D.BRASS_LUT, None,
                                                     vfn=None, rough=0.24 if (l4 or h5) else 0.26, ior=1.5,
                                                     **({"clearcoat": 0.35, "cc_rough": 0.08} if (l4 or h5) else {})),
                  voxel=0.0025),
             # LOOK-2 (the finish judge: "the lenses reflect pink/red fur and the rims are pale cream, so at normal size they
             # read as a second pair of small eyes with red pupils"): OPAQUE dark tinted glass -- a deep smoky teal-blue
             # under a mirror clearcoat, so the lens shows the sky (the rig's cool top) and one white glint
             Part("goggleLenses", w(F["goggleLenses"]), Material("b_glens4", "#20384A", roughness=0.05, ior=1.52, clearcoat=1.0,
                                                               clearcoat_roughness=0.02, emissive="#0C2A3C") if (l4 or h5) else
                  glass("b_glens", "#A9E9F2", opacity=0.55), voxel=0.002),
             Part("goggleStraps", w(F["straps"]), K.skin("b_strap", D.LEATHER, None, vfn=None, rough=0.5, ior=1.25), voxel=0.003)]
    if l4 and "goggleInner" in F:
        parts += [Part("goggleInner", w(F["goggleInner"]), K.skin("b_goginner4", [(0.0, "#6A4A14"), (1.0, "#2A1A04")], None, vfn=None,
                                                                 rough=0.4, ior=1.4), voxel=0.0016),
                  Part("goggleGlints", w(F["goggleGlints"]), Material("b_gglint4", "#FFFFFF", roughness=0.3, emissive="#FFFFFF"),
                       voxel=0.0012)]
    if "lipline" in F:
        parts.append(Part("lipline", w(F["lipline"]), satin("b_lip", S.LIP, rough=0.6), voxel=0.003))
    if "cavity" in F and h6:
        # LOOK-2 fix round (the judge: "the cavity is flat maroon, and the tongue is a flat lozenge"): the mouth's inside
        # and the tongue take LUT skins, so the obscurance field shades them (a dark throat, a lit tongue tip + groove)
        parts += [Part("mouth", w(F["inner"]), K.skin("b_mouth6", MOUTH6, None, vfn=None, rough=0.55, ior=1.22), voxel=0.004),
                  Part("teeth", w(F["teeth"]), Material("b_teeth", "#FBF8F4", roughness=0.25, ior=1.4, emissive="#8A8784"),
                       voxel=0.003),
                  Part("tongue", w(F["tongue"]), K.skin("b_tongue6", TONGUE6, None, vfn=None, rough=0.38, ior=1.32,
                                                        clearcoat=0.25, cc_rough=0.20), voxel=0.003)]
    elif "cavity" in F:
        parts += [Part("mouth", w(F["inner"]), Material("b_mouth", S.MOUTH_IN, roughness=0.55, ior=1.22, emissive="#2A0616"),
                       voxel=0.004),
                  Part("teeth", w(F["teeth"]), Material("b_teeth", "#FBF8F4", roughness=0.25, ior=1.4, emissive="#8A8784"),
                       voxel=0.003),
                  Part("tongue", w(F["tongue"]), Material("b_tongue", PAL["tongue"], roughness=0.35, ior=1.3, emissive="#5A1030"),
                       voxel=0.004)]
    if l3:        # fix round 2: the limbal ring round each iris + the upper lids (pink skin, a deep-pink lash crease)
        parts += [Part("limbal", w(F["limbal"]), gloss("b_limbal", B_LIMBAL, rough=0.25, ior=1.45), voxel=0.002),
                  Part("lids", w(F["lids"]), K.skin("b_lidskin3", PAL["skin"], None, vfn=None, rough=0.70, ior=1.2), voxel=0.003)]
        if not l4:         # LOOK-2: no crease line (the judge: "drop the crease line")
            parts.append(Part("lidcrease", w(F["lidcrease"]), satin("b_crease3", LID_CREASE3, rough=0.55), voxel=0.002))
    if h6:        # LOOK-2 fix round: the limbal ring + the permanent UPPER LIDS (pink skin, no crease) of the home face
        parts += [Part("limbal", w(F["limbal"]), gloss("b_limbal", B_LIMBAL, rough=0.25, ior=1.45), voxel=0.002),
                  Part("upperLids", w(F["upperLids"]), K.skin("b_uplid6", PAL["skin"], None, vfn=None, rough=0.70, ior=1.2),
                       voxel=0.003)]
    lid_sdf = None
    if eyes in ("half", "closed"):
        lid_sdf, crease = S.lids(F["skin0"], F, eyes)
        parts += [Part("lids", w(lid_sdf), K.skin("b_lidskin", PAL["skin"], None, vfn=None, rough=0.72, ior=1.2), voxel=0.003),
                  Part("lidcrease", w(crease), satin("b_crease", S.P_BROW2, rough=0.6), voxel=0.002)]
    fld = K.field_for(field_key or ("boss_head", mouth), parts + list(extra_field))
    K.shade(parts, field=fld)
    view_h = K.unit(Ai @ np.asarray(view_w, float))
    gog_f = D.sdf_fn(union(F["goggles"], F["goggleLenses"], F["straps"]))
    tooth_f = D.sdf_fn(F["tooth"])
    ew = ear_weights(F)

    dens0 = density2(F, eyes_of(style), lip=0.004) if f2 else S.density(F)

    def base_density(p):
        d = dens0(p)
        d *= (gog_f(p) > 0.010).astype(float)
        d *= (tooth_f(p) > 0.02).astype(float)
        return d

    def build_head():
        rng = np.random.default_rng(seed)
        v, f, n = FUR.surface(skin_h, 0.012, key=("boss2_head_surf", mouth))
        bm = S.brow_mask(F)
        # denser on the muzzle (short fur must still cover its skin) and on the ears (a thin shape: its rim must read
        # furry at 1/3 size)
        P, N = FUR.sample(v, f, n, n_strands, rng,
                          density=lambda p: base_density(p) * (1 - bm(p)) * (1.0 + 0.8 * muzzle_weight(p) + 0.9 * ew(p)[0] + 0.6 * ew(p)[1]))
        comb, L, lift, W = S.groom(P, N, F, rng, style="home")
        mz = muzzle_weight(P)
        e, inner, tip, axis = ew(P)
        fw = face_weight(P) * (1 - e) if style == "load" else np.zeros(len(P))
        mw = np.maximum(mz, inner)
        # ONE groom: on the patch the comb turns radial from the muzzle centre (down + out), the fur gets a little
        # shorter and flatter -- continuously, so the blush edge has no direction break
        cm = np.array([MUZ_C[0], MUZ_C[1] - 0.02, 0.0])
        radial = FUR.unit((P - cm) * np.array([1.0, 1.0, 0.2])) + np.array([0, -0.35, 0])[None]
        comb = FUR.unit(comb) * (1 - 0.5 * mz[:, None]) + FUR.unit(radial) * (0.5 * mz[:, None])
        L = L * (1 - 0.12 * mz)
        lift = lift * (1 - 0.12 * mz)
        # the EARS: the fur lies along the ear toward its tip (so the leaf keeps its shape), a short tuft at the tip;
        # the inner ear is short velvet in the blush (its band below), a little more upright
        Le = (0.026 + 0.040 * tip) * (1 - 0.30 * inner) * (0.8 + 0.4 * rng.random(len(P)))
        comb = FUR.unit(comb) * (1 - e[:, None]) + axis * e[:, None]
        L = L * (1 - e) + Le * e
        lift = lift * (1 - e) + (0.22 + 0.20 * inner + 0.25 * tip) * e
        if style == "load":       # the velvet face (LOOK-L T5b): shorter, flatter, finer, barely clumped
            L, lift, W = L * (1 - 0.40 * fw), lift * (1 - 0.35 * fw), W * (1 - 0.20 * fw) * 0.85
        lipw = np.zeros(len(P))
        if f2:
            # fix round 1: the face keeps a real groom + form (only a little shorter / finer than the crown), and the
            # fur round the open mouth is short and combed AWAY from it (no bald lip plate, no hairs in the mouth)
            fw = face_weight(P) * (1 - e)
            if "cavity" in F:
                # S.groom (style home) cut the lip fur to 15 % (L *= 1 - 0.85 near, near = 1 - dc / 0.09) -> the bald
                # "duck bill" rim: grow it back to ~60 %, still combed away from the opening
                dc = np.asarray(F["cavity"](np.asarray(P, np.float32)), float)
                lipw = np.clip(1 - dc / 0.09, 0, 1)
                L = L * (1 - 0.40 * lipw) / np.maximum(1 - 0.85 * lipw, 0.05)
            # S.groom also cut the fur round the (home-size) eyes to 45 % (L *= 1 - 0.55 near, near = 1.6 - d): with the
            # lip cut it left the band between the eyes and the mouth nearly bald (the plate). Undo it; re-apply a
            # milder cut round the load2 eyes (the sockets themselves grow no fur: density2)
            ek = 1.0 if h5 else (EYE_K3 if l3 else EYE_K2)
            for Eh, E2 in zip(S.EYES, eyes_of(style)):
                exh, eyh = Eh["c"]
                dh = np.hypot((P[:, 0] - exh) / 0.13, (P[:, 1] - eyh) / 0.155)
                L = L / np.maximum(1 - 0.55 * np.clip(1.6 - dh, 0, 1), 0.05)
                d2 = np.hypot((P[:, 0] - exh) / (0.13 * ek), (P[:, 1] - eyh) / (0.155 * ek))
                L = L * (1 - 0.30 * np.clip(1.4 - d2, 0, 1))
            L = L * (1 - 0.18 * fw)
            lift = lift * (1 - 0.10 * fw) * (1 - 0.25 * lipw)
            W = W * (1 - 0.08 * fw) * 0.92
        clump_v = 0.55 * (1 - 0.75 * fw) if style == "load" else (0.55 * (1 - 0.30 * fw) if f2 else 0.55)
        csize, pclump, jitd, jamp = 0.03, 16, 0.18, 0.05
        if f3:
            # fix round 2 (the finish judge: "flocked sandpaper ... pixel speckle, not strands"): LONGER groomed fur in
            # clumped LOCKS, WIDER strands at a lower density (they resolve as strands at 3x), a calmer per-strand tone,
            # shorter jowl / cheek-tuft fur (the "boar" jowls), and a few FLYAWAY strands on the outline (crown, ears,
            # the silhouette) that break the even halo
            xx_, yy_ = P[:, 0], P[:, 1]
            side_ = np.abs(xx_) / 0.6
            tuft_ = np.exp(-((yy_ - np.where(xx_ < 0, 0.60, 0.64)) / 0.11) ** 2) * np.clip((side_ - 0.66) / 0.2, 0, 1)
            jowl_ = np.clip((0.70 - yy_) / 0.4, 0, 1)
            if not h5:           # (home5 keeps the home boss's full cheeks / jowls: short jowls read as a bald muzzle)
                L = L * (1 - 0.60 * tuft_) * (1 - 0.35 * jowl_)
            near_feat = np.clip(lipw, 0, 1)
            L = L * (1.0 + 0.30 * (1 - 0.6 * fw) * (1 - near_feat))
            W = W * 1.55
            sil = 1 - np.abs(N @ view_h)
            fly = (rng.random(len(P)) < (0.004 + 0.030 * np.clip((sil - 0.60) / 0.3, 0, 1) + 0.030 * e + 0.020 * np.clip((yy_ - 0.95) / 0.1, 0, 1))
                   * (0.05 if h5 else (0.12 if l5 else (0.30 if l4 else 1.0))))     # LOOK-2: ~70 % fewer flyaways (the judge: "a fuzzy pompom, not groomed plush")
            lift = lift * 0.85                                   # groomed: the locks lie a little flatter
            fly &= near_feat < 0.2
            L = np.where(fly, L * (1.7 + 0.5 * rng.random(len(P))), L)
            lift = np.where(fly, np.minimum(lift * 1.35 + 0.08, 0.95), lift)
            comb = np.where(fly[:, None], FUR.unit(comb + rng.normal(0, 0.35, (len(P), 3))), comb)
            clump_v = np.where(fly, 0.15, 0.72 * (1 - 0.30 * fw))
            csize, pclump, jitd, jamp = 0.048, 24, 0.12, 0.020
            if f5:
                # LOOK-2 round 2: bigger LOCKS (more strands per clump, tighter to their clump centre), one calm flow
                # (the groom blended toward a down-and-out comb off the crown), a calmer per-strand tone
                flow = FUR.unit(np.stack([np.sign(xx_) * 0.42, -np.ones_like(xx_), 0.30 * np.ones_like(xx_)], 1))
                keep_ = np.maximum(e, np.clip(lipw * 1.5, 0, 1))[:, None]
                comb = np.where(fly[:, None], comb, FUR.unit(FUR.unit(comb) * (0.62 + 0.38 * keep_) + flow * 0.38 * (1 - keep_)))
                clump_v = np.where(fly, 0.15, 0.90 * (1 - 0.18 * fw))
                csize, pclump, jitd, jamp = 0.080, 56, 0.06, 0.008
                W = W * 1.42          # (pass 6: fewer, wider strands -- the caller's n_strands 26000 -- less pixel speckle)
        if h5:        # LOOK-2 HOME: coherent tufts (not a per-strand scatter), a touch wider strands
            csize, pclump, jitd, jamp = 0.036, 20, 0.14, 0.018
            clump_v = 0.64
            W = W * 1.18
        V, Fc, NR, T, ri = FUR.strands(P, N, comb, L, lift, W, view_h, rng, segs=5 if f3 else 4, gravity=(0, -0.18, 0),
                                       clump=clump_v, clump_size=csize,
                                       per_clump=pclump, jitter=jitd, nbend=0.15)
        jit = rng.normal(0, jamp, len(P)) * (1 - 0.5 * mw) * ((1 - 0.7 * fw) if style == "load" else (1 - 0.3 * fw) if f2 else 1.0)
        if h5:        # LOOK-2 HOME: a small tuft-level tone (tufts, not per-strand speckle)
            cell = np.floor(np.asarray(P, float) / 0.05).astype(np.int64)
            hsh = ((cell[:, 0] * 73856093) ^ (cell[:, 1] * 19349663) ^ (cell[:, 2] * 83492791)) & 1023
            jit = jit + np.random.default_rng(seed + 9).uniform(-1, 1, 1024)[hsh] * 0.035 * (1 - 0.6 * mw)
        if f5:        # LOOK-2 round 2: a LOCK-level tone (one offset per ~0.07 cell of roots): tufts, not per-strand speckle
            cell = np.floor(np.asarray(P, float) / 0.07).astype(np.int64)
            hsh = ((cell[:, 0] * 73856093) ^ (cell[:, 1] * 19349663) ^ (cell[:, 2] * 83492791)) & 1023
            jit = jit + (np.random.default_rng(seed + 9).uniform(-1, 1, 1024)[hsh] * 0.075) * (1 - 0.6 * mw) * (1 - 0.5 * fw)
        tg = 0.55 * (1 - 0.40 * fw) if style == "load" else (0.62 * (1 + 0.10 * fw) if f2 else 0.55)
        t0 = 0.40
        if l3:        # a calmer root -> tip tone: the resolved strands kept v4-draft's micro-contrast (judge's HF metric)
            tg = 0.44 * (1 + 0.10 * fw)
        if l5:        # LOOK-2 round 2: the strands span the whole crimson-root -> light-pink-tip ladder
            t0, tg = 0.20, 0.74 * (1 - 0.30 * fw)       # (pass 6: calmer tips on the face front -- the HF metric)
        if h5:        # LOOK-2 HOME: the home ladder (3 rows) spanned calmly: a lower root -> tip contrast
            t0, tg = 0.44, 0.44
        uv = FUR.tone_uv(fld, None, T, ri, wp(P), jit, tone0=t0, tone_gain=tg,
                         N=wn(N), under=(0.36 if f2 else 0.30) * (1 - 0.6 * mw[ri]))
        return dict(V=wp(V), F=Fc, NR=wn(NR), uv=uv, nv=2 * (5 if f3 else 4) + 1, band=D.band_of(mw, FUR_BANDS, rng))

    def build_brow():
        rng = np.random.default_rng(seed + 1)
        vb, fb, nb = FUR.surface(F["brows"], 0.005, key=("boss2_brow_surf", mouth))
        P, N = FUR.sample(vb, fb, nb, n_strands // 6, rng, density=lambda p: np.ones(len(p)))
        keep = N[:, 2] > -0.1
        P, N = P[keep], N[keep]
        comb = np.zeros((len(P), 3))
        comb[:, 0] = np.sign(P[:, 0])
        comb[:, 1] = 0.35
        L = np.full(len(P), 0.046 if f3 else (0.052 if l2 else 0.036)) * (0.8 + 0.4 * rng.random(len(P)))
        V, Fc, NR, T, ri = FUR.strands(P, N, comb, L, 0.42 if f2 else 0.35, 0.0125 if f3 else (0.0100 if l2 else 0.0095), view_h, rng, segs=3,
                                       clump=0.50 if f2 else 0.25, clump_size=0.03, per_clump=10, jitter=0.12, nbend=0.15)
        uv = FUR.tone_uv(fld, None, T, ri, wp(P), rng.normal(0, 0.03 if h6 else 0.06, len(P)), tone0=0.40,
                         tone_gain=0.30 if h6 else 0.45, N=wn(N), under=0.0)
        return wp(V), Fc, wn(NR), uv
    key = ("boss2_head", field_key, mouth, n_strands, seed) + ((style,) if (f2 or h6) else ())
    parts += D.banded_fur_parts("fur", key, build_head, fur_stops, PAL["muz"], bands=FUR_BANDS, mat_prefix="b_fur2" if l2 else "b_fur",
                                **({"rough": 0.46} if l5 else {}))       # load5: a broader soft sheen on the locks
    parts.append(FUR.fur_part("browfur", FUR.fur_material("b_browfur3" if l3 else ("b_browfur2" if l2 else "b_browfur"), None,
                                                          stops=PAL["brow"], rough=0.6), build_brow))
    if l3:        # a short velvet on the upper lids (a bald smooth lid read as a plastic cap on the furry face)
        def lidfur3():
            rng = np.random.default_rng(seed + 6)
            v, f, n = FUR.surface(F["lids"], 0.004, key=("boss3_lid_surf", mouth))
            P, N = FUR.sample(v, f, n, 3000, rng, density=lambda p: (np.asarray(p)[:, 2] > 0.2).astype(float) + 1e-6)
            comb = np.tile([[0.0, 1.0, 0.25]], (len(P), 1))
            V, Fc, NR, T, ri = FUR.strands(P, N, comb, 0.014, 0.30, 0.0080, view_h, rng, segs=2, clump=0.3,
                                           clump_size=0.02, per_clump=8, jitter=0.15, nbend=0.15)
            uv = FUR.tone_uv(fld, None, T, ri, wp(P), rng.normal(0, 0.03, len(P)), tone0=0.45, tone_gain=0.45, N=wn(N))
            return wp(V), Fc, wn(NR), uv
        parts.append(FUR.fur_part("lidfur3", FUR.fur_material("b_lidfur3", None, stops=fur_stops, rough=0.60), lidfur3))
    if h6:        # a short velvet on the upper lids (a bald lid reads as a plastic cap on the furry face)
        def uplidfur():
            rng = np.random.default_rng(seed + 7)
            v, f, n = FUR.surface(F["upperLids"], 0.004, key=("boss6_uplid_surf", mouth))
            P, N = FUR.sample(v, f, n, 2600, rng, density=lambda p: (np.asarray(p)[:, 2] > 0.2).astype(float) + 1e-6)
            comb = np.tile([[0.0, 1.0, 0.25]], (len(P), 1))
            V, Fc, NR, T, ri = FUR.strands(P, N, comb, 0.013, 0.30, 0.0075, view_h, rng, segs=2, clump=0.3,
                                           clump_size=0.02, per_clump=8, jitter=0.15, nbend=0.15)
            uv = FUR.tone_uv(fld, None, T, ri, wp(P), rng.normal(0, 0.03, len(P)), tone0=0.45, tone_gain=0.45, N=wn(N))
            return wp(V), Fc, wn(NR), uv
        parts.append(FUR.fur_part("upperLidFur", FUR.fur_material("b_uplidfur6", None, stops=fur_stops, rough=0.60), uplidfur))
    if lid_sdf is not None:
        def lidfur():
            rng = np.random.default_rng(seed + 5)
            v, f, n = FUR.surface(lid_sdf, 0.004, key=("boss2_lid_surf", eyes))
            P, N = FUR.sample(v, f, n, 2600, rng, density=lambda p: (np.asarray(p)[:, 2] > 0.2).astype(float) + 1e-6)
            comb = np.tile([[0.0, 1.0, 0.0]], (len(P), 1))
            V, Fc, NR, T, ri = FUR.strands(P, N, comb, 0.012, 0.25, 0.0055, view_h, rng, segs=2, clump=0.2,
                                           clump_size=0.02, per_clump=8, jitter=0.2, nbend=0.15)
            uv = FUR.tone_uv(fld, None, T, ri, wp(P), rng.normal(0, 0.05, len(P)), tone0=0.45, tone_gain=0.45, N=wn(N))
            return wp(V), Fc, wn(NR), uv
        parts.append(FUR.fur_part("lidfur", FUR.fur_material("b_lidfur", None, stops=fur_stops, rough=0.60), lidfur))
    return parts


# ================================================================== station (the scaffold rail + lever)

RAIL_Y, RAIL_Z = 0.86, 0.60
LEVER = dict(hub=(1.02, RAIL_Y + 0.085, RAIL_Z - 0.02), top=(1.04, 1.50, RAIL_Z - 0.10))


def station(style="home"):
    """The foreman's scaffold (replaces the console): a timber rail on two posts, a lower brace, iron bolts, a brass
    lever with a turned knob on the rail. Parts carry the D1 wood (grain LUT) + brass + iron.
    style "home6" (LOOK-2 fix round; the copy judge: "an orange ball-knob lever at his right hand where their console
    lever sits"): the lever ends in a wooden T-HANDLE with brass end caps (a hoist brake), no ball knob."""
    rail = box(1.62, 0.072, 0.095, round=0.024).translate(0, RAIL_Y, RAIL_Z)
    brace = box(1.62, 0.055, 0.075, round=0.02).translate(0, 0.30, RAIL_Z - 0.02)
    posts = union(*[box(0.085, 0.60, 0.085, round=0.02).translate(sx * 1.22, 0.40, RAIL_Z - 0.03) for sx in (-1, 1)])
    bolts = union(*[cylinder(0.024, 0.012, round=0.006).transform(K.frame_from([0, 0, 1], [1, 0, 0]))
                    .translate(sx * 1.22 + dx, yy, RAIL_Z + 0.098 - (0.02 if yy < 0.5 else 0.0))
                    for sx in (-1, 1) for dx in (-0.035, 0.035) for yy in (RAIL_Y, 0.30)])
    hub0 = np.asarray(LEVER["hub"], float)
    top = np.asarray(LEVER["top"], float)
    hub = cylinder(0.075, 0.045, round=0.012).transform(K.frame_from([1, 0, 0], [0, 0, 1])).translate(*hub0)
    arm = capsule(tuple(hub0), tuple(top), 0.030)
    base = box(0.11, 0.022, 0.08, round=0.012).translate(hub0[0], RAIL_Y + 0.08, hub0[2])
    knob = ellipsoid(0.074, 0.080, 0.074).translate(*(top + np.array([0.004, 0.050, 0.004])))
    wood = K.skin("b_wood", D.WOOD0, D.WOOD1, vfn=D.grain_vfn(22, 0), rough=0.62, ior=1.25)
    if style == "home6":
        tj = np.asarray(T6["joint"], float)
        arm = capsule(tuple(hub0), tuple(tj), 0.030)
        a0, a1 = np.asarray(T6["bar"][0], float), np.asarray(T6["bar"][1], float)
        collar = cylinder(0.042, 0.030, round=0.010).transform(K.frame_from([0, 1, 0], [0, 0, 1])).translate(*(tj - np.array([0, 0.012, 0])))
        caps = union(*[round_cone(tuple(e - K.unit(a1 - a0) * s_ * 0.02), tuple(e + K.unit(a1 - a0) * s_ * 0.030), 0.050, 0.046)
                       for e, s_ in ((a0, -1), (a1, 1))])
        grip = capsule(tuple(a0), tuple(a1), 0.046)
        return [Part("rail", rail, wood, voxel=0.007),
                Part("brace", brace, K.skin("b_wood2", D.WOOD0, D.WOOD1, vfn=D.grain_vfn(22, 0, 3), rough=0.62, ior=1.25), voxel=0.007),
                Part("posts", posts, K.skin("b_wood3", D.WOOD0, D.WOOD1, vfn=D.grain_vfn(30, 1, 5), rough=0.62, ior=1.25), voxel=0.007),
                Part("bolts", bolts, metal("b_iron", "#5A5F66", rough=0.4), voxel=0.003),
                Part("lever", union(hub, arm, base, collar, caps, k=0.008), K.skin("b_brass", D.BRASS_LUT, None, rough=0.26, ior=1.5),
                     voxel=0.003),
                Part("knob", grip, K.skin("b_tgrip6", D.WOOD0, D.WOOD1, vfn=D.grain_vfn(40, 0, 7), rough=0.50, ior=1.3), voxel=0.003)]
    return [Part("rail", rail, wood, voxel=0.007),
            Part("brace", brace, K.skin("b_wood2", D.WOOD0, D.WOOD1, vfn=D.grain_vfn(22, 0, 3), rough=0.62, ior=1.25), voxel=0.007),
            Part("posts", posts, K.skin("b_wood3", D.WOOD0, D.WOOD1, vfn=D.grain_vfn(30, 1, 5), rough=0.62, ior=1.25), voxel=0.007),
            Part("bolts", bolts, metal("b_iron", "#5A5F66", rough=0.4), voxel=0.003),
            Part("lever", union(hub, arm, base, k=0.01), K.skin("b_brass", D.BRASS_LUT, None, rough=0.26, ior=1.5), voxel=0.003),
            Part("knob", knob, K.skin("b_knob", [(0.0, "#FFB86A"), (0.45, "#FF8A2A"), (0.8, "#D8620E"), (1.0, "#9A3F04")], None,
                                      rough=0.28, ior=1.4), voxel=0.003)]


STATION_PARTS = {"rail", "brace", "posts", "bolts", "lever", "knob"}
# home6: the T-handle (world, the boss's frame): the stick from the hub up to the joint, the grip bar across it
T6 = dict(joint=(1.03, 1.27, RAIL_Z - 0.06), bar=((0.66, 1.300, RAIL_Z - 0.07), (1.42, 1.300, RAIL_Z - 0.07)))
# (r2: the bar is LONG -- the paw layer is drawn over the scaffold, so a short bar hid under the paw and the paw read as
# floating; the bar's capped ends now show on both sides of the paw)
# the paw wrapped over the bar: the wrist above-behind it, the fingers forward then curled DOWN over its front
ARM_R6 = dict(el=(1.22, 0.98, 0.04), wr=(1.05, 1.40, RAIL_Z - 0.20), d=(0.0, -0.30, 1.0), palm=(0.0, -1.0, -0.10), r=0.17)


# ================================================================== the foreman coat (torso space of char_scientist)

def _stitch_dashes(path, surf, lift=0.0030, dash=0.020, gap=0.013, r=0.0052, zmin=0.05, step=0.010):
    """LOOK-2 round 2: a line of top-stitching -- short raised thread DASHES laid on the FRONT surface of `surf` along
    the (x, y) polyline `path` (the surface z by a sphere trace, sampled every `step`, interpolated between). Points
    where the ray misses / lands behind z < zmin are dropped. -> an SDF (union of capsules) or None."""
    P = np.asarray(path, float)
    seg = np.linalg.norm(np.diff(P, axis=0), axis=1)
    s_ = np.r_[0.0, np.cumsum(seg)]
    L = s_[-1]
    ss = np.linspace(0.0, L, max(2, int(L / step) + 1))
    xs, ys = np.interp(ss, s_, P[:, 0]), np.interp(ss, s_, P[:, 1])
    zs = np.array([K.surface_z_of(surf, x, y) for x, y in zip(xs, ys)])
    caps = []
    t = gap * 0.5
    while t + dash <= L:
        a, b = t, t + dash
        za, zb = np.interp(a, ss, zs), np.interp(b, ss, zs)
        if min(za, zb) > zmin:
            pa = np.array([np.interp(a, ss, xs), np.interp(a, ss, ys), za + lift])
            pb = np.array([np.interp(b, ss, xs), np.interp(b, ss, ys), zb + lift])
            caps.append(capsule(tuple(pa), tuple(pb), r))
        t += dash + gap
    return union(*caps) if caps else None


def _stitch_ring(c, axis, rad, lift=0.0030, dash=0.020, gap=0.013, r=0.0052):
    """a ring of thread dashes round `axis` at centre c, radius rad (+ lift): the edge of a cuff."""
    ax = K.unit(axis)
    u = K.unit(np.cross(ax, [0.0, 0.0, 1.0]) if abs(ax[2]) < 0.95 else np.cross(ax, [1.0, 0.0, 0.0]))
    v = np.cross(ax, u)
    R_ = rad + lift
    n = int(2 * np.pi * R_ / (dash + gap))
    caps = []
    for i in range(n):
        a0 = 2 * np.pi * i / n
        a1 = a0 + dash / R_
        p0 = np.asarray(c) + R_ * (np.cos(a0) * u + np.sin(a0) * v)
        p1 = np.asarray(c) + R_ * (np.cos(a1) * u + np.sin(a1) * v)
        caps.append(capsule(tuple(p0), tuple(p1), r))
    return union(*caps)


def _inset(poly, d):
    """a closed polygon's vertices moved d toward its centroid (a cheap inset for a stitch path)."""
    P = np.asarray(poly, float)
    c = P.mean(0)
    return [tuple(p + K.unit(c - p) * d) for p in P]


def coat_ridges5(coat, n_):
    """load5 (the finish judge on v5: "two 'fold ridges' above the belt look like sausages lying across the belly ...
    FIX: replace the belly ridges with 2-3 tapered drag folds converging on the buckle"): TAPERED drag folds -- fat at
    the flank, thinning to nothing at the belt's centre -- two per side above the belt converging on the keeper, and
    one short pair below the belt near the placket (clear of the hip pockets). -> an SDF to union (smoothly)."""
    ridges = []
    for (x0, y0, x1, y1, r) in ((-0.60, 1.00, -0.16, 0.815, 0.024), (-0.56, 0.90, -0.17, 0.805, 0.018),
                                (0.46, 1.02, 0.03, 0.815, 0.024), (0.50, 0.92, 0.04, 0.805, 0.018),
                                (-0.17, 0.675, -0.30, 0.44, 0.016), (0.04, 0.675, 0.16, 0.44, 0.016)):
        t = np.linspace(0.0, 1.0, 9)
        xs = (x0 + (x1 - x0) * t) * n_
        ys = y0 + (y1 - y0) * t + 0.018 * np.sin(np.pi * t)
        zs = np.array([K.surface_z_of(coat, x, y) for x, y in zip(xs, ys)])
        ok = zs > -1.0
        if ok.sum() < 3:
            continue
        taper = (1.0 - t) ** 0.8 if y0 > 0.7 else np.sin(np.linspace(0.15, np.pi - 0.3, len(t)))
        rr = r * (0.18 + 0.82 * taper)[ok]
        pts = np.stack([xs[ok], ys[ok], zs[ok] - rr * 0.50], 1)
        ridges.append(K.limb(pts, rr, k=0.03))
    return union(*ridges, k=0.02)


def foreman_coat(T, n_, v4=False, v5=False):
    """Teal canvas foreman coat (closed; placket + 3 brass buttons; a rounded corduroy collar; a breast pocket with a
    rolled blueprint). R7: shells with edges, not body offsets painted on.
    v4 (LOOK-2, the finish judge on v4: "an inflated teal balloon ... the pocket recesses are flat dark rectangles, and
    the collar and facings have no thickness. FIX: constructed edges ... 2-3 soft fabric folds at the waist ... a belt
    to break up the mass"): soft fabric FOLD ridges bunched above and below a leather BELT at the waist, a THICKER
    collar, pockets and flaps that stand proud of the coat (real thickness, their edges catch the light)."""
    torso = T["torso"]
    coat = torso.offset(0.045)
    coat0 = coat
    if v5:
        coat = union(coat, coat_ridges5(coat0, n_), k=0.035)
    elif v4:
        coat = union(coat, coat_ridges(coat, n_), k=0.035)
    plx = -0.07
    plk = coat.offset(0.014).intersect(box(0.058, 0.8, 1.0, round=0.01).translate(plx, 0.95, 0.8), k=0.006)
    plk = plk.intersect(box(1, 3, 1).translate(0, 0, 1.0))      # the front half only (R1 cut it at y 1.0 by mistake)
    buttons = []
    for by in ((1.42, 1.18, 0.95) if v4 else (1.42, 1.18, 0.95, 0.72)):
        bz = K.surface_z_of(coat.offset(0.014), plx, by)
        buttons.append(ellipsoid(0.036, 0.036, 0.016).translate(plx, by, bz + 0.004))
        buttons.append(torus(0.028, 0.006).transform(K.frame_from([0, 0, 1], [1, 0, 0])).translate(plx, by, bz + 0.014))
    flaps = []
    for sx in (-1, 1):
        poly = [(sx * 0.07, 1.80), (sx * 0.66 * n_, 1.66), (sx * 0.62 * n_, 1.44), (sx * 0.40 * n_, 1.30), (sx * 0.20, 1.50)]
        if sx < 0:
            poly = poly[::-1]
        pp = polygon2(fillet_points(poly, [0.02, 0.10, 0.12, 0.10, 0.04], n_arc=6))
        prism = extrude(pp, 1.0).intersect(box(1, 1, 0.9).translate(0, 1.4, 0.4))
        flaps.append(torso.offset(0.108 if v4 else 0.088).intersect(prism, k=0.012))
    collar = union(*flaps, k=0.02)
    px_, py_ = (0.50 + 0.21 * (1 - n_) / 0.2) * n_, 1.02 + 0.10 * (1 - n_) / 0.2
    pk, fk = (0.024, 0.040) if v4 else (0.013, 0.020)
    pc_ = coat0 if v5 else coat          # load5: the pockets hug the plain canvas (the folds crumpled their edges)
    rk, kk = (0.016, 0.003) if v5 else (0.03, 0.01)
    pocket = pc_.offset(pk).intersect(box(0.19, 0.14, 1.0, round=rk).translate(px_, py_ - 0.03, 0.4), k=kk)
    flap = pc_.offset(fk).intersect(box(0.20, 0.035 if not v4 else 0.042, 1.0, round=0.012 if v5 else 0.02).translate(px_, py_ + 0.10, 0.4),
                                    k=0.002 if v5 else 0.006)
    pz = K.surface_z_of(coat, px_ - 0.02, py_ + 0.10) + 0.02
    r0 = np.array([px_ + 0.03, py_ - 0.02, pz - 0.01])
    r1 = np.array([px_ - 0.10, py_ + 0.30, pz + 0.035])
    roll = capsule(tuple(r0), tuple(r1), 0.046)
    ax = K.unit(r1 - r0)
    band = torus(0.049, 0.008).transform(K.frame_from(ax, [1, 0, 0])).translate(*(r0 + (r1 - r0) * 0.62))
    end = cylinder(0.040, 0.006).transform(K.frame_from(ax, [1, 0, 0])).translate(*(r1 + ax * 0.043))
    # a stitched welt seam round the waist (a sewn garment, R7)
    seam = coat.offset(0.006).subtract(coat.offset(-0.004)).intersect(D.slab_y(0.735, 0.748), k=0.004)
    # two hip pockets with flaps (R1 defect: the coat below the rail read as a plain bell between rail and brace)
    hips = []
    for sx in (-1, 1):
        hx_, hy_ = sx * 0.50 * (0.5 + 0.5 * n_) - 0.03, 0.52
        hips.append(pc_.offset(pk if v4 else 0.012).intersect(box(0.17, 0.12, 1.0, round=rk).translate(hx_, hy_ - (0.03 if v4 else 0.0), 0.4),
                                                              k=kk))
        hips.append(pc_.offset(fk).intersect(box(0.18, 0.032 if not v4 else 0.040, 1.0, round=0.012 if v5 else 0.02).translate(
            hx_, hy_ + (0.10 if v4 else 0.13), 0.4), k=0.002 if v5 else 0.006))
    out = dict(coat=coat, placket=plk, buttons=union(*buttons), collar=collar,
               pocket=union(pocket, flap, *hips, k=0.004),
               roll=roll, rollband=band, rollend=end, seam=seam)
    if v4:           # the leather belt round the waist (over the welt seam) + a brass buckle on the placket
        belt = coat.offset(0.030).subtract(coat.offset(-0.03)).intersect(D.slab_y(0.690, 0.795), k=0.008)
        bz = K.surface_z_of(coat.offset(0.030), plx, 0.742)
        buckle = box(0.088, 0.066, 0.018, round=0.014).subtract(box(0.052, 0.034, 0.05, round=0.010)).translate(plx, 0.742, bz + 0.008)
        out.update(belt=belt, buckle=buckle)
    if v5:
        # no square buckle (the copy judge: theirs wears a brown belt with a buckle): the coat's canvas KEEPER tab laps
        # over the belt at the placket (the belt runs under it), top-stitched round its edge
        keeper = coat0.offset(0.046).intersect(box(0.066, 0.074, 1.0, round=0.014).translate(plx, 0.742, 0.4), k=0.004)
        out.pop("buckle", None)
        out["keeper"] = keeper
        # the TOP-STITCHING (cream thread dashes): the placket's two edges (broken at the belt), the pocket U's and the
        # flap edges, the collar's outer edges, the belt's two edges, round the keeper
        st = {}
        pl_s = coat.offset(0.014)
        pl_lines = []
        for dx in (-0.043, 0.043):
            pl_lines += [_stitch_dashes([(plx + dx, 1.62), (plx + dx, 0.815)], pl_s),
                         _stitch_dashes([(plx + dx, 0.672), (plx + dx, 0.30)], pl_s)]
        st["stitchPlacket"] = union(*[q for q in pl_lines if q is not None])
        ps = coat0.offset(pk)
        fs = coat0.offset(fk)
        pk_lines = [_stitch_dashes([(px_ - 0.166, py_ + 0.055), (px_ - 0.166, py_ - 0.150), (px_ + 0.166, py_ - 0.150),
                                    (px_ + 0.166, py_ + 0.055)], ps),
                    _stitch_dashes([(px_ - 0.178, py_ + 0.074), (px_ + 0.178, py_ + 0.074)], fs)]
        for sx in (-1, 1):
            hx_ = sx * 0.50 * (0.5 + 0.5 * n_) - 0.03
            pk_lines += [_stitch_dashes([(hx_ - 0.148, 0.570), (hx_ - 0.148, 0.392), (hx_ + 0.148, 0.392), (hx_ + 0.148, 0.570)], ps),
                         _stitch_dashes([(hx_ - 0.158, 0.596), (hx_ + 0.158, 0.596)], fs)]
        st["stitchPockets"] = union(*[q for q in pk_lines if q is not None])
        col_s = torso.offset(0.108 if v4 else 0.088)
        col_lines = []
        for sx in (-1, 1):
            poly = [(sx * 0.07, 1.80), (sx * 0.66 * n_, 1.66), (sx * 0.62 * n_, 1.44), (sx * 0.40 * n_, 1.30), (sx * 0.20, 1.50)]
            q = _inset(poly, 0.030)
            col_lines.append(_stitch_dashes([q[4], q[3], q[2], q[1]], col_s, zmin=0.10))
        st["stitchCollar"] = union(*[q for q in col_lines if q is not None])
        bs = coat.offset(0.030)
        be = []                   # (two runs per edge, left and right of the keeper)
        for yy in (0.779, 0.706):
            be.append(_stitch_dashes([(x, yy) for x in np.linspace(-0.95, plx - 0.080, 20)], bs, zmin=0.25))
            be.append(_stitch_dashes([(x, yy) for x in np.linspace(plx + 0.080, 0.95, 20)], bs, zmin=0.25))
        kp = [(plx - 0.052, 0.800), (plx + 0.052, 0.800), (plx + 0.052, 0.684), (plx - 0.052, 0.684), (plx - 0.052, 0.800)]
        be.append(_stitch_dashes(kp, coat0.offset(0.046), dash=0.016, gap=0.011))
        st["stitchBelt"] = union(*[q for q in be if q is not None])
        out["stitches"] = st
    return out


def coat_ridges(coat, n_):
    """v4: soft fabric FOLDS as low RIDGES (a ridge catches the key on its top and turns away below: it reads as cloth,
    where v4-draft's grooves read as stains under the baked obscurance) -- the canvas bunched just above the belt on
    both sides of the placket, and two drag folds on the skirt below it. -> an SDF to union (smoothly) into the coat."""
    ridges = []
    # (v5 draft: a second pair of belly ridges made the chest read as stacked rolls with a dark groove between them)
    for (x0, x1, y0, y1, bow, r) in ((-0.62, -0.18, 0.905, 0.850, 0.030, 0.036), (0.08, 0.58, 0.850, 0.905, 0.030, 0.036),
                                     (-0.46, -0.52, 0.64, 0.40, 0.0, 0.026), (0.40, 0.48, 0.64, 0.40, 0.0, 0.026)):
        t = np.linspace(0.0, 1.0, 9)
        xs = (x0 + (x1 - x0) * t) * n_
        ys = y0 + (y1 - y0) * t - bow * (1 - (2 * t - 1) ** 2)
        zs = np.array([K.surface_z_of(coat, x, y) for x, y in zip(xs, ys)])
        ok = zs > -1.0
        if ok.sum() < 3:
            continue
        rr = r * (0.35 + 0.65 * np.sin(np.linspace(0.12, np.pi - 0.12, len(xs))))[ok]
        pts = np.stack([xs[ok], ys[ok], zs[ok] - rr * 0.45], 1)
        ridges.append(K.limb(pts, rr, k=0.03))
    return union(*ridges, k=0.02)


TORSO_PARTS = {"coat", "placket", "buttons", "collar", "pocket", "blueprint", "blueprintBand", "blueprintEnd", "seam"}


# ================================================================== arms: rolled sleeve, cuff, fur forearm, paw

def boss_arm(Rt, tb, side, n_, A, hand="grip"):
    """A short rolled canvas sleeve over the upper arm, a corduroy cuff below the elbow, a bare fur forearm into the
    paw. A = dict(el, wr, d, palm, r) in WORLD; hand "grip" (fingers curled round a rail / knob) or "point" (a fist
    with the index finger up)."""
    neck_t = np.array([0.0, 1.62, -0.06])
    sh = (np.array([side * 0.74 * n_, 1.28, -0.14]) - neck_t + neck_t) @ Rt.T + tb
    el, wr = np.asarray(A["el"], float), np.asarray(A["wr"], float)
    de = K.unit(wr - el)
    if hand == "point":
        fist = S.fist_ball(wr + de * 0.02, K.unit(A["d"]), K.unit(A["palm"]), r=A["r"] * 1.02)
        R = K.frame_from(A["d"], A["palm"])
        ex, ey, ez = R[:, 0], R[:, 1], R[:, 2]
        c = wr + de * 0.02 + ey * A["r"] * 0.95
        tipb = c + ey * A["r"] * 0.55 + ez * A["r"] * 0.25 - ex * side * A["r"] * 0.25
        up = K.unit(ey * 1.0 + ez * 0.25)
        index = K.limb([tipb, tipb + up * 0.14, tipb + K.unit(up + ez * 0.25) * 0.26], [0.060, 0.056, 0.050], k=0.02)
        paw = union(fist, index, k=0.03)
    elif hand == "tgrip":         # home6: chunky finger lobes curled over the T-handle's bar + a thumb (reads under fur)
        paw = K.hand(wr + de * 0.03, K.unit(A["d"]), K.unit(A["palm"]), r=A["r"], fingers=3, finger_len=1.05,
                     finger_r=0.50, spread=26, curl=105, thumb=1.1, thumb_side=-side, thumb_angle=35, k=0.22)
    else:
        paw = K.hand(wr + de * 0.03, K.unit(A["d"]), K.unit(A["palm"]), r=A["r"], fingers=4, finger_len=0.95,
                     finger_r=0.42, spread=14, curl=95, thumb_side=-side, thumb_angle=45)
    send = el + de * 0.10
    sleeve = K.limb([sh, el, send], [0.27, 0.25, 0.24], k=0.10)
    cuff = round_cone(tuple(send - de * 0.11), tuple(send + de * 0.03), 0.265, 0.255)
    forearm = K.limb([el + de * 0.02, wr], [0.175, 0.160], k=0.05)
    return dict(sleeve=sleeve, cuff=cuff, hand=union(forearm, paw, k=0.05), shoulder=sh)


BOSS_ARMS = dict(
    # screen-left paw grips the rail's front edge (fingers curled over it); screen-right paw rests on the lever knob
    L=dict(el=(-1.02, 1.00, 0.10), wr=(-0.88, 1.11, 0.45), d=(0.15, -0.45, 1.0), palm=(0.0, -1.0, 0.15), r=0.17),
    R=dict(el=(1.22, 0.95, 0.02), wr=(1.13, 1.14, 0.37), d=(0.0, 0.05, 1.0), palm=(-1.0, 0.0, 0.0), r=0.17),
    # armR_point: the forearm up beside the shoulder, a fist with the index claw raised ("this way!")
    R_point=dict(el=(1.24, 1.02, 0.08), wr=(1.20, 1.46, 0.30), d=(-0.05, 1.0, 0.25), palm=(-0.55, 0.0, 1.0), r=0.165),
)
ARM_L = {"sleeveL", "cuffL", "handL", "handfurL"}
ARM_R = {"sleeveR", "cuffR", "handR", "handfurR"}


def boss_v2(pose="home", mouth="smile", eyes="open", armR="grip", n_strands=48000, only=None, view_pose=None,
            look=(0.14, -0.40), arms=None, with_station=True, extra=None, hands=None, style="home"):
    """hands: {"L"/"R": "grip" | "point"} overrides (loading / avatar poses); arms: {"L"/"R": dict(el, wr, d, palm, r)}.
    extra: more Parts (props, a rock) -- in the parts and in the obscurance field."""
    """All parts of the boss in world space (before ui3d's view pose). only: a set of part names (layers)."""
    P = S.POSES[pose] if pose in S.POSES else POSES[pose]
    vp = view_pose or S.HOME_POSE
    view_w = S._view_dir(dict(yaw=vp["yaw"], pitch=vp["pitch"]))
    Rt = S.rot((1, 0, 0), P["lean"]) @ S.rot((0, 1, 0), P["yaw"])
    pivot = np.array([0.0, 0.2, -0.1])
    tt = pivot - Rt @ pivot + np.array([0.0, -0.06, 0.0])
    dx, n_ = P.get("body_dx", 0.0), P.get("narrow", 1.0)
    tb = tt + np.array([dx, P.get("body_dy", 0.0), 0.0])

    def tw(s):
        return s.transform(Rt).translate(*tb)
    T = S.torso_space(n_)
    l3 = style in ("load3", "load4", "load5")
    l4 = style in ("load4", "load5")
    l5 = style == "load5"
    h6 = style == "home6"
    C = foreman_coat(T, n_, v4=l4, v5=l5)
    COAT_T, COAT_T2, CORD = (COAT_T_LOAD, COAT_T2_LOAD, CORD_LOAD) if style == "load" else (
        (COAT_T_L2, COAT_T2_L2, CORD_L2) if style in ("load2", "load3", "load4", "load5") else (_COAT_T, _COAT_T2, _CORD))
    coatm = K.skin("b_coat", COAT_T, COAT_T2, vfn=D.canvas_vfn(), rough=0.82, ior=1.2)
    if l3:
        # fix round 2 (the finish judge: "dark mottled blotches cover the coat's belly and sleeves ... no real fabric
        # folds"): ONE clean canvas ramp (the heathered two-ramp noise was the blotches) + sewn FOLDS -- two soft drag
        # folds across the belly and two tension folds from the armpits, grooved into the coat shell
        coatm = K.skin("b_coat_l3", COAT_T3, None, vfn=None, rough=0.80, ior=1.2)
        # (the coat's own folds were dropped: under the coarse baked field any dip on the belly read as a stain; the
        # sewn folds live on the sleeves, round the elbows, below)
    cordm = K.skin("b_cord", CORD, None, vfn=None, rough=0.86, ior=1.18)
    if l4:    # LOOK-2: the collar, placket and pocket flaps in the coat's own canvas with LIT convex edges (not dark slabs)
        cordm = K.skin("b_cord4", CORD4, None, vfn=None, rough=0.84, ior=1.18)
        COAT_T = COAT_T4E
    body = [Part("coat", tw(C["coat"]), coatm, voxel=0.008 if not l4 else 0.007),
            Part("placket", tw(C["placket"]), K.skin("b_coat2", COAT_T, None, vfn=None, rough=0.80, ior=1.2), voxel=0.005),
            Part("buttons", tw(C["buttons"]), K.skin("b_buttons", D.BRASS_LUT, None, vfn=None, rough=0.26, ior=1.5), voxel=0.0025),
            Part("collar", tw(C["collar"]), cordm, voxel=0.006),
            Part("pocket", tw(C["pocket"]), K.skin("b_coat3", COAT_T, None, vfn=None, rough=0.80, ior=1.2), voxel=0.004),
            Part("seam", tw(C["seam"]), K.skin("b_seam", COAT_T2, None, vfn=None, rough=0.85, ior=1.2), voxel=0.003),
            Part("blueprint", tw(C["roll"]), K.skin("b_blue", BLUEPRINT, None, vfn=None, rough=0.82, ior=1.2), voxel=0.003),
            Part("blueprintBand", tw(C["rollband"]), satin("b_band", "#E4553A", rough=0.5), voxel=0.002),
            Part("blueprintEnd", tw(C["rollend"]), satin("b_paper", "#F4F7FA", rough=0.7), voxel=0.002)]
    if h6:
        # LOOK-2 fix round: the coat lifted to a mid teal-GREEN canvas with a weave; the collar, placket and pocket in the
        # canvas with LIGHTER convex edges; no blueprint "pen" in the pocket
        import char_crew_d1 as _CREW
        body = [Part("coat", tw(C["coat"]), K.skin("b_coat6", COAT_H6, COAT_H6W, vfn=_CREW.weave_vfn(period=0.030, amp=0.30),
                                                   rough=0.74, ior=1.2), voxel=0.0060),
                Part("placket", tw(C["placket"]), K.skin("b_placket6", COAT_H6E, None, vfn=None, rough=0.76, ior=1.2), voxel=0.005),
                Part("buttons", tw(C["buttons"]), K.skin("b_buttons", D.BRASS_LUT, None, vfn=None, rough=0.26, ior=1.5), voxel=0.0025),
                Part("collar", tw(C["collar"]), K.skin("b_collar6", CORD_H6, None, vfn=None, rough=0.82, ior=1.18), voxel=0.006),
                Part("pocket", tw(C["pocket"]), K.skin("b_pocket6", COAT_H6E, None, vfn=None, rough=0.76, ior=1.2), voxel=0.004),
                Part("seam", tw(C["seam"]), K.skin("b_seam6", COAT_H6W, None, vfn=None, rough=0.80, ior=1.2), voxel=0.003)]
    if l5:
        # LOOK-2 round 2: a CANVAS WEAVE in the albedo (two crossed thread sines, low amplitude, rough 0.72) on the coat
        # and sleeves; the cream top-stitching; the keeper over the belt (no buckle)
        import char_crew_d1 as _CREW
        coatm = K.skin("b_coat5", COAT_T5, COAT_T5W, vfn=_CREW.weave_vfn(period=0.030, amp=0.34), rough=0.72, ior=1.2)
        body[0] = Part("coat", tw(C["coat"]), coatm, voxel=0.0055)
        body += [Part("coatBelt", tw(C["belt"]), K.skin("b_belt5", D.LEATHER, None, vfn=None, rough=0.55, ior=1.3), voxel=0.004),
                 Part("coatKeeper", tw(C["keeper"]), K.skin("b_keeper5", COAT_T4E, None, vfn=None, rough=0.74, ior=1.2), voxel=0.0030)]
        for nm, sd in C["stitches"].items():
            body.append(Part(nm, tw(sd), K.skin(f"b_{nm}5", THREAD5, None, vfn=None, rough=0.70, ior=1.25), voxel=0.0020))
    elif l4:
        body += [Part("coatBelt", tw(C["belt"]), K.skin("b_belt4", D.LEATHER, None, vfn=None, rough=0.55, ior=1.3), voxel=0.004),
                 Part("coatBuckle", tw(C["buckle"]), K.skin("b_buckle4", D.BRASS4_LUT, None, vfn=None, rough=0.26, ior=1.5,
                                                             clearcoat=0.3, cc_rough=0.08), voxel=0.0025)]
    arm_pts = dict(BOSS_ARMS, **(arms or {}))
    if h6 and not (arms and "R" in arms):
        arm_pts["R"] = ARM_R6
    armp = []
    for side, tag in ((-1, "L"), (1, "R")):
        hand = (hands or {}).get(tag, armR if tag == "R" else "grip")
        if h6 and tag == "R" and hand == "grip" and not (arms and "R" in arms):
            hand = "tgrip"
        A = arm_pts["R_point"] if (tag == "R" and armR == "point" and not (arms and "R" in arms)) else arm_pts[tag]
        W = boss_arm(Rt, tb, side, n_, A, hand=hand)
        sl = W["sleeve"].subtract(tw(C["coat"]).offset(-0.02))
        if l3:           # two soft folds round the sleeve just above the elbow (a bent canvas sleeve)
            el_, sh_ = np.asarray(A["el"], float), W["shoulder"]
            ax_ = K.unit(el_ - sh_)
            folds = union(*[torus(0.262, 0.020).transform(K.frame_from(ax_, [1.0, 0.0, 0.0])).translate(*(el_ - ax_ * dd))
                            for dd in (0.05, 0.16)])
            sl = sl.subtract(folds, k=0.03)
        armp += [Part(f"sleeve{tag}", sl, K.skin(f"b_sleeve{tag}", COAT_T, COAT_T2, vfn=D.canvas_vfn(seed=11 + side), rough=0.82,
                                                  ior=1.2) if not l3 else K.skin(f"b_sleeve3{tag}", COAT_T3, None, vfn=None, rough=0.80,
                                                                                 ior=1.2), voxel=0.008),
                 Part(f"cuff{tag}", W["cuff"], K.skin(f"b_cuff{tag}", CORD, None, vfn=None, rough=0.86, ior=1.18), voxel=0.006)]
        if h6:
            import char_crew_d1 as _CREW
            armp[-2] = Part(f"sleeve{tag}", sl, K.skin(f"b_sleeve6{tag}", COAT_H6, COAT_H6W,
                                                        vfn=_CREW.weave_vfn(period=0.030, amp=0.30), rough=0.74, ior=1.2), voxel=0.0060)
            armp[-1] = Part(f"cuff{tag}", W["cuff"], K.skin(f"b_cuff6{tag}", CORD_H6, None, vfn=None, rough=0.84, ior=1.18), voxel=0.006)
        if l5:          # LOOK-2 round 2: the woven sleeve + a stitched ring at both edges of the cuff
            import char_crew_d1 as _CREW
            armp[-2] = Part(f"sleeve{tag}", sl, K.skin(f"b_sleeve5{tag}", COAT_T5, COAT_T5W,
                                                        vfn=_CREW.weave_vfn(period=0.030, amp=0.34), rough=0.72, ior=1.2), voxel=0.0060)
            el_, wr_ = np.asarray(A["el"], float), np.asarray(A["wr"], float)
            de_ = K.unit(wr_ - el_)
            send_ = el_ + de_ * 0.10
            armp.append(Part(f"stitchCuff{tag}", union(*[_stitch_ring(send_ + de_ * off, de_, rad)
                                                         for off, rad in ((-0.092, 0.2665), (0.014, 0.2575))]),
                             K.skin(f"b_stitchcuff5{tag}", THREAD5, None, vfn=None, rough=0.70, ior=1.25), voxel=0.0020))
        armp += [Part(f"hand{tag}", W["hand"], K.skin("b_handskin2" if style in ("load2", "load3") else "b_handskin", pal2(style)["skin"], None,
                                                       vfn=None, rough=0.72, ior=1.2), voxel=0.005)]
    st = station(style)     # always in the obscurance field (the rail shades the coat); in the parts only if asked
    ex = list(extra or [])
    H = P["head"]
    Rh = S.rot((0, 0, 1), H["roll"]) @ S.rot((0, 1, 0), H["yaw"]) @ S.rot((1, 0, 0), H["nod"])
    th = np.array([0.0, S.HEAD_Y, 0.14]) + (Rt @ np.array([0, 1.55, 0]) + tt - np.array([0, 1.55, 0])) * np.array([1, 0, 1])
    fkey = ("boss2", pose, mouth)
    head = boss_head_parts_xf(Rh, th, view_w, mouth=mouth, n_strands=n_strands, extra_field=body + armp + ex,
                              field_key=fkey, look=look, eyes=eyes, **({} if style == "home" else dict(style=style)))
    fld = K.field_for(("boss2_body", pose, mouth), body + armp + st + ex)
    if l4 or h6:
        # LOOK-2 (the finish judge: "dark occlusion smudges on the chest left of the placket and on the right belly"):
        # the coat's garment parts are shaded by a field WITHOUT the arms (the arm hovering in front of the chest baked a
        # blotch into the canvas); the arms, legs and props keep the full field
        fld_c = K.field_for(("boss4_coat", pose, mouth), body + st + ex)
        K.shade(body, field=fld_c, gain=1.3)          # a gentler contact shading on the canvas (no dark grooves / smudges)
        K.shade(armp + st + ex, field=fld)
    else:
        K.shade(body + armp + st + ex, field=fld)
    for side, tag in ((-1, "L"), (1, "R")):
        hp = [p for p in armp if p.name == f"hand{tag}"][0]
        if h6:        # home6: the home hand fur, SHORTER on the gripping paw so its finger lobes + thumb read
            armp.append(hand_fur3(f"handfur{tag}", hp.sdf, view_w, fld, ("boss6_hand", pose, tag, armR if tag == "R" else ""),
                                  seed=7 + side, stops=pal2(style)["fur"], tone=(0.40, 0.40, 0.012), locks=(0.55, 0.035, 14),
                                  length=0.62 if (tag == "R" and armR != "point") else 0.85))
            continue
        if l3:
            armp.append(hand_fur3(f"handfur{tag}", hp.sdf, view_w, fld, ("boss3_hand", pose, tag) + (("l5",) if l5 else ()),
                                  seed=7 + side, stops=pal2(style)["fur"],
                                  **(dict(tone=(0.32, 0.58, 0.010), locks=(0.80, 0.055, 30)) if l5 else {})))
            continue
        armp.append(S.hand_fur(f"handfur{tag}", hp.sdf, view_w, fld, ("boss2_hand", pose, tag, armR if tag == "R" else ""),
                               n=11000, seed=7 + side, **({} if style == "home" else dict(stops=pal2(style)["fur"]))))
    parts = (st if with_station else []) + body + armp + ex + head
    if only is not None:
        parts = [p for p in parts if p.name in only]
    return parts, VOXEL


# load3: a clean mid teal canvas with a GENTLE obscurance ramp (the baked field is coarse, 0.013 u: a steep ramp turned
# the arm's occlusion on the belly into dark smudges) -- the lights, not the ramp, shape the coat
COAT_T3 = [(0.0, "#66C6BE"), (0.35, "#58B8B1"), (0.70, "#4AA8A2"), (1.0, "#3A928C")]
# LOOK-2: the garment trims (placket, pockets + flaps) in the coat's canvas with a LIGHTER convex end (their edges read
# lit and thick), the collar in a lighter corduroy (v4's CORD_L2 read as a dark flat shape)
COAT_T4E = [(0.0, "#8CDAD2"), (0.22, "#6CC8C0"), (0.55, "#56B6AF"), (1.0, "#3C948E")]
# home6: a mid teal-GREEN canvas (hue ~160, clear of the turquoise wall's ~190) + its shaded weave threads, the trims
# with lighter convex edges, a lighter corduroy collar
COAT_H6 = [(0.0, "#66CCA6"), (0.35, "#4BB692"), (0.70, "#379C7C"), (1.0, "#257C62")]
COAT_H6W = [(0.0, "#5ABE9A"), (0.35, "#42A686"), (0.70, "#308C70"), (1.0, "#206E56")]
COAT_H6E = [(0.0, "#96E4C6"), (0.22, "#72D0AE"), (0.55, "#54B894"), (1.0, "#389878")]
CORD_H6 = [(0.0, "#8ADCBE"), (0.35, "#62C09E"), (0.75, "#46A282"), (1.0, "#308266")]
CORD4 = [(0.0, "#80D2CA"), (0.35, "#56B0AA"), (0.75, "#3E918C"), (1.0, "#2C726E")]


def coat_folds(coat, n_):
    """load3: soft fabric folds on the coat front (torso space) -- two shallow drag folds across the belly under the
    placket, two tension folds running from each armpit toward the belly. -> an SDF to subtract (smoothly)."""
    grooves = []
    # WIDE, SHALLOW dips (a fold is a broad soft valley, not a crease: v4-draft's narrow grooves read as smudges) --
    # a fat capsule whose axis rides ~0.05 above the surface, so only ~0.012 of it cuts in, blended wide
    for (y0, y1, x0, x1, r) in ():                   # (the belly drag folds read as stains under the baked obscurance)
        xs = np.linspace(x0, x1, 9)
        ys = y0 + (y1 - y0) * (xs - x0) / (x1 - x0) - 0.035 * (1 - ((xs - (x0 + x1) / 2) / ((x1 - x0) / 2)) ** 2)
        zs = np.array([K.surface_z_of(coat, x, y) for x, y in zip(xs, ys)])
        rr = r * (0.55 + 0.45 * np.sin(np.linspace(0.15, np.pi - 0.15, len(xs))))
        grooves.append(K.limb(np.stack([xs, ys, zs + rr - 0.012], 1), rr, k=0.04))
    for sx in (-1, 1):
        xs = np.linspace(sx * 0.56 * n_, sx * 0.26, 7)
        ys = np.linspace(1.24, 0.99, 7)
        zs = np.array([K.surface_z_of(coat, x, y) for x, y in zip(xs, ys)])
        rr = 0.050 * (0.55 + 0.45 * np.sin(np.linspace(0.2, np.pi - 0.2, 7)))
        grooves.append(K.limb(np.stack([xs, ys, zs + rr - 0.007], 1), rr, k=0.04))
    return union(*grooves)


def hand_fur3(name, hand_sdf, view_w, field, key, seed=7, stops=None, tone=(0.42, 0.36, 0.018), locks=(0.62, 0.04, 20),
              length=1.0):
    """load3 mitten fur (the finish judge: "the mittens show pixel speckle, not strands"): fewer, LONGER, WIDER strands
    in clumped locks combed down the back of the paw toward the knuckles, a calm tone, a few flyaways on the back."""
    def fn():
        rng = np.random.default_rng(seed)
        v, f, nn = FUR.surface(hand_sdf, 0.008, key=key)
        P, N = FUR.sample(v, f, nn, 6200, rng)
        comb = np.tile([[0.0, -0.3, 1.0]], (len(P), 1))
        L = 0.044 * length * (0.8 + 0.4 * rng.random(len(P)))
        sil = 1 - np.abs(N @ K.unit(view_w))
        fly = rng.random(len(P)) < 0.02 + 0.08 * np.clip((sil - 0.6) / 0.3, 0, 1)
        L = np.where(fly, L * 1.8, L)
        comb = np.where(fly[:, None], FUR.unit(comb + rng.normal(0, 0.4, (len(P), 3))), comb)
        V, Fc, NR, T, ri = FUR.strands(P, N, comb, L, 0.36, 0.0102, view_w, rng, segs=4, clump=np.where(fly, 0.1, locks[0]),
                                       clump_size=locks[1], per_clump=locks[2], jitter=0.12, nbend=0.15)
        uv = FUR.tone_uv(field, None, T, ri, P, rng.normal(0, tone[2], len(P)), tone0=tone[0], tone_gain=tone[1], N=N, under=0.18)
        return V, Fc, NR, uv
    return FUR.fur_part(name, FUR.fur_material("s_fur3", None, stops=stops, rough=0.60), fn)


def boss_anchors(pose="home"):
    """eyeMid / neck / shoulders (world) of a pose, as char_scientist.pose_anchors (same head + torso space)."""
    return S.pose_anchors(pose) if pose in S.POSES else None


POSES = {}

# ================================================================== the home rig + cases

HOME_POSE = S.HOME_POSE
HOME_FRAME = S.HOME_FRAME
HOME_VIEW = S.HOME_VIEW
_A = S.pose_anchors("home")
# R3 HOME (build/blocked.md 09:19, ruling 46 = the SAME composition): the boss back at TODAY's spot, centred behind the
# station: rig frame top-left (109.0, 176.0) = eyeMid (205.61, 211.99) (the scientist's frame was (109.23, 176.52); whole
# pt so homeScaffold registers to the pixel). R2's D1 draft had him right of centre at (299.6, 216.0). R3 owns the spot.
HOME_EYEMID_PT = (205.61, 211.99)
MODELS = {"boss_stage": lambda: boss_v2("home"),
          "boss_station": lambda: boss_v2("home", only=STATION_PARTS)}
ASSETS = {
    # proofs + R3's registered station (never shipped: route3d)
    "char_bossStage": dict(scene=[("boss_stage", HOME_POSE)], dest="route3d", bounds=HOME_VIEW, frame=HOME_FRAME, fov=18,
                           light=D.LIGHT_D1, no_fit=True),
    "char_bossStation": dict(scene=[("boss_station", HOME_POSE)], dest="route3d", bounds=HOME_VIEW, frame=HOME_FRAME, fov=18,
                             light=D.LIGHT_D1, no_fit=True),
}


def _factory(only=None, **kw):
    # the rig's full render and layers exclude the station (it is homeScaffold's), its shading stays in the field
    # LOOK-2 HOME: style "home5" (the home design + a smoother fur tone / friendlier face); 44k slightly wider strands
    return boss_v2("home", only=only, with_station=False, style="home5", n_strands=44000, **kw)


RIGS = {"boss_home": dict(K.explicit_rig(
    MODELS, ASSETS, "boss_home", _factory, HOME_FRAME, HOME_VIEW, HOME_POSE, D.LIGHT_D1,
    full_kw={}, full_anchors={"eyeMid": _A["eyeMid"], "neck": _A["neck"]},
    layers=[
        dict(name="torso", parts=TORSO_PARTS, note="foreman coat; behind the scaffold (homeScaffold / char_bossStation); "
                                                   "the head and arms sit on it"),
        dict(name="armL", parts=ARM_L, holdout=TORSO_PARTS, pivots={"shoulder": _A["shoulderL"]},
             note="paw grips the scaffold rail's front edge (drawn in front of the scaffold)"),
        dict(name="armR", parts=ARM_R, holdout=TORSO_PARTS, pivots={"shoulder": _A["shoulderR"]}, group="armR",
             default=True, note="paw on the brass lever's knob (drawn in front of the scaffold)"),
        dict(name="armR_point", parts=ARM_R, kw=dict(armR="point"), holdout=TORSO_PARTS,
             pivots={"shoulder": _A["shoulderR"]}, group="armR", note="gesture: forearm up, index claw raised"),
        dict(name="headSmile", parts=HEAD_PARTS, holdout=TORSO_PARTS, pivots={"neck": _A["neck"]}, group="head",
             default=True, note="closed smile + snaggle fang, furry ears, goggles"),
        dict(name="headOpen", parts=HEAD_PARTS, kw=dict(mouth="open"), holdout=TORSO_PARTS, pivots={"neck": _A["neck"]},
             group="head", note="open laugh (fang beside the tooth band)"),
        dict(name="lidsHalf", parts=LID_PARTS, kw=dict(eyes="half"), pivots={"neck": _A["neck"]}, overlay=True,
             parent="head", note="half-closed lids over the eyes (blink in-between)"),
        dict(name="lidsClosed", parts=LID_PARTS, kw=dict(eyes="closed"), pivots={"neck": _A["neck"]}, overlay=True,
             parent="head", note="closed happy eyes (blink / laugh)"),
    ]),
    place=dict(anchor="eyeMid", at=HOME_EYEMID_PT))}

# LOOK-2 HOME: every boss_home case (the full render + each layer) at 3x supersampling (the Loading boss's ss=3): the
# strands average into a soft plush at 1:1 instead of aliasing into speckle (the measured face-fur Laplacian gap)
for _c in [RIGS["boss_home"]["full"]] + [c for _, c in RIGS["boss_home"]["layers"]]:
    ASSETS[_c]["ss"] = 3


def plush_pass(im, sigma=0.9, k=0.80):
    """LOOK-2 HOME post_fit (the measured gap: the home boss's face-fur Laplacian 7.6x the original's): a PLUSH pass on
    the pink fur only -- a premultiplied gaussian (sigma px @3x) blended in at k inside the fur mask (pink hue, saturated,
    opaque, eroded 1 px so the silhouette's strands keep their edge); eyes, goggles, tooth, mouth and the coat are
    untouched. The strands then read as a soft plush at 1:1 instead of pixel speckle (the render's own 3x supersampling
    does not change it: the speckle is real strand-scale shading, not aliasing)."""
    import numpy as _np
    from PIL import Image as _I
    from scipy import ndimage as _ndi
    from skimage.color import rgb2hsv as _hsv
    a = _np.asarray(im.convert("RGBA")).astype(_np.float64) / 255
    rgb, al = a[..., :3], a[..., 3]
    hs = _hsv(rgb)
    h = hs[..., 0] * 360
    fur = ((h > 318) | (h < 12)) & (hs[..., 1] > 0.30) & (al > 0.99)
    fur = _ndi.binary_erosion(fur, iterations=1).astype(_np.float64)
    w = _ndi.gaussian_filter(fur, 1.0)[..., None] * k
    pm = rgb * al[..., None]
    b = _np.stack([_ndi.gaussian_filter(pm[..., c], sigma) for c in range(3)], -1)
    ab = _ndi.gaussian_filter(al, sigma)[..., None]
    b = b / _np.maximum(ab, 1e-4)
    out = rgb * (1 - w) + _np.clip(b, 0, 1) * w
    o = _np.concatenate([_np.clip(out, 0, 1), al[..., None]], -1)
    return _I.fromarray((o * 255 + 0.5).astype(_np.uint8), "RGBA")


for _c in [RIGS["boss_home"]["full"]] + [c for _, c in RIGS["boss_home"]["layers"]]:
    ASSETS[_c]["post_fit"] = plush_pass


# ================================================================== LOOK-2 FIX ROUND: the home rig in style "home6"
# Same rig contract as the LOOK-2 rig above (names, frame, view, pose, placement, layer / group / pivot names); the head
# layers carry the new permanent upper lids (+ their velvet) and the limbal rings; a WARM rim light from the daylit
# upper right (the finish judge #12: "a warm rim light on the coat and fur edges"; the room's daylight corner is there).
HEAD_PARTS6 = HEAD_PARTS | {"limbal", "upperLids", "upperLidFur"}
LIGHT_BOSS6 = dict(D.LIGHT_D1, rim_color=(1.0, 0.86, 0.64), rim_lux=1550.0, rim_dir=D.rim_from(0.8, -0.25))


def _factory6(only=None, **kw):
    return boss_v2("home", only=only, with_station=False, style="home6", n_strands=44000, **kw)


MODELS["boss_station6"] = lambda: boss_v2("home", only=STATION_PARTS, style="home6")
ASSETS["char_bossStation6"] = dict(scene=[("boss_station6", HOME_POSE)], dest="route3d", bounds=HOME_VIEW, frame=HOME_FRAME,
                                   fov=18, light=LIGHT_BOSS6, no_fit=True)
RIGS["boss_home"] = dict(K.explicit_rig(
    MODELS, ASSETS, "boss_home", _factory6, HOME_FRAME, HOME_VIEW, HOME_POSE, LIGHT_BOSS6,
    full_kw={}, full_anchors={"eyeMid": _A["eyeMid"], "neck": _A["neck"]},
    layers=[
        dict(name="torso", parts=TORSO_PARTS, note="foreman coat; behind the scaffold (homeScaffold / char_bossStation); "
                                                   "the head and arms sit on it"),
        dict(name="armL", parts=ARM_L, holdout=TORSO_PARTS, pivots={"shoulder": _A["shoulderL"]},
             note="paw grips the scaffold rail's front edge (drawn in front of the scaffold)"),
        dict(name="armR", parts=ARM_R, holdout=TORSO_PARTS, pivots={"shoulder": _A["shoulderR"]}, group="armR",
             default=True, note="paw wrapped over the lever's T-handle (drawn in front of the scaffold)"),
        dict(name="armR_point", parts=ARM_R, kw=dict(armR="point"), holdout=TORSO_PARTS,
             pivots={"shoulder": _A["shoulderR"]}, group="armR", note="gesture: forearm up, index claw raised"),
        dict(name="headSmile", parts=HEAD_PARTS6, holdout=TORSO_PARTS, pivots={"neck": _A["neck"]}, group="head",
             default=True, note="closed smile + snaggle fang, lidded eyes on the viewer, furry ears, goggles"),
        dict(name="headOpen", parts=HEAD_PARTS6, kw=dict(mouth="open"), holdout=TORSO_PARTS, pivots={"neck": _A["neck"]},
             group="head", note="open laugh (fang beside the tooth band)"),
        dict(name="lidsHalf", parts=LID_PARTS, kw=dict(eyes="half"), pivots={"neck": _A["neck"]}, overlay=True,
             parent="head", note="half-closed lids over the eyes (blink in-between)"),
        dict(name="lidsClosed", parts=LID_PARTS, kw=dict(eyes="closed"), pivots={"neck": _A["neck"]}, overlay=True,
             parent="head", note="closed happy eyes (blink / laugh)"),
    ]),
    place=dict(anchor="eyeMid", at=HOME_EYEMID_PT))
for _c in [RIGS["boss_home"]["full"]] + [c for _, c in RIGS["boss_home"]["layers"]]:
    ASSETS[_c]["ss"] = 3
    ASSETS[_c]["post_fit"] = plush_pass

# ================================================================== F3-art (2026-09-29): the station occludes the right arm
# LOOK-2 carry-over (the finish judge: "the lever's stick is hidden by the forearm"): HomeView draws torso + head, THEN
# homeScaffold (this station, rendered alone as char_bossStation6), THEN the arms -- so the whole right arm covered the
# station. In the model the forearm is BEHIND the station (elbow z 0.04 -> wrist z 0.40; the stick z ~0.54-0.58, the T-bar
# z 0.53, the rail z 0.55-0.65); only the paw's fingers curl in FRONT of the T-bar. The shipped armR / armR_point layers
# therefore carry the station's occlusion: each was re-rendered with the station parts (STATION_PARTS, all six) added to
# its holdout matte (torso as before), and the pixels that matte removes are cut from the SHIPPED layer (baked colours
# kept) only where homeScaffold actually draws the station (its 2-D edits trim the rail's ends past the posts); the rig's
# full render (char_boss_home@3x.png) takes the new rest composite in those pixels, so the rest layers still recompose it
# (ShellTests, mean <= 1/255). Names, frame, placement, pivots, rig.json and file sizes are unchanged.
# A RE-EXPORT of RIGS["boss_home"] (rig.py / char_make.rig) regenerates the UN-occluded arms and full render: re-apply
# with build/p/F3art/lever_render.py <armR|armR_point> stk, then lever_apply.py and full_patch.py (build/p/F3art/REDONE).
# Nothing is registered here (no extra MODELS / ASSETS cases): the driver injects its cases at run time.
