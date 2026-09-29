"""R2 CAST (PLAN-P §4.2; SPEC rulings 37b / 38; design/publish/art-direction.md §1.3, §3.1): the D1 crew species, the
velvet-furred "DIGGER", and its two HOME RIGS. Forked from R1's char_concepts_d1.digger (left as R1 wrote it).

A-bar (art-direction §1.3) in this recipe:
  R1 velvet strand fur on every body surface (short, dense, little clumping) + a lighter cream-mint BELLY / SNOUT patch
     grown in the same strand set and split into LUT bands (char_d1kit.banded_fur_parts: a soft gradient, no speckle);
  R2 every limb meets the body under fur; kit (vest, belt, hat, goggles, tools) meets the fur at constructed edges;
  R3 fur 0.62, fabric vest 0.78, leather 0.52, brass 0.26-0.30, painted steel 0.34, hat plastic 0.32, gloss eyes 0.18,
     nose 0.26 (+ a clearcoat on the NOSE only);
  R4 eyes IN sockets under fur-covered lid shells with a crease, brows of their own dark fur, 2 glints;
  R5 a big head with a snout cone + round peach nose + tiny ears, a hard hat, spade paws: reads at 1/3;
  R6 the CHAR_LIGHT family with the D1 room map, rim 1150 lx;
  R7 the vest is a shell with arm holes, a V opening, binding tape, a zip and a reflective stripe;
  R8 the rigs keep the workers' layer / group / pivot contract (below).
R1 -> R2 fixes (art/review/concepts/grades-r1.json "defects_for_R2" + the orchestrator's 04:32 note): a bigger head and
eyes with friendlier brows (appeal at 1/3), the patchy-at-1/3 fur calmed (less tone jitter, less clumping, denser), the
shovel / trowel as painted steel with worn bright edges + brass rivets (was plain grey), a real HEADLAMP (iron body,
brass bezel, a big glowing lens facing the camera; was a grey stub), claws that follow the finger curl on a gripping paw
(were poking out sideways), a lighter belly + snout.

Rigs (art/out/char_dig_home{L,R}_rig/), the SAME names as char_wk_home{L,R}_blue_rig so the ui.json puppet tracks and
PuppetStage apply unchanged:
  dig_homeL  body_smile (default) | body_open | eyes_open (default) | eyes_half | eyes_closed | eyes_wink | armL (default,
             the free paw at rest) | armL_wave | armR (the paw on a planted SHOVEL's handle)   pivots feet, neck,
             eyes, shoulder.   A lamp-hat Digger, goggles up on the brim, facing the centre (screen right).
  dig_homeR  body_smile (default) | body_open | eyes_open | eyes_half (default: reading) | eyes_closed | goggles (brass
             goggles DOWN over the eyes) | armL (holds the tunnel MAP) | armR (a carpenter's pencil marking it).
             A taller, slimmer Digger facing the centre (screen left).
Placement: the D1 home's feet spots (art-direction §3.1: L feet ~(70, 606), R front-right (318, 606)); data for R3.
"""
from __future__ import annotations

import math

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
DIG_FUR = [(0.0, [(0.0, "#2FA888"), (0.5, "#1C8068"), (1.0, "#115C4C")]),
           (0.35, [(0.0, "#7FE3C3"), (0.35, "#4CCBA5"), (0.6, "#2FA888"), (1.0, "#1C8068")]),
           (1.0, [(0.0, "#C6F9E8"), (0.35, "#9CEDD3"), (0.6, "#63D7B4"), (1.0, "#34AE8E")])]
DIG_FUR_SAGE = [(0.0, [(0.0, "#36A48E"), (0.5, "#227C6A"), (1.0, "#15584C")]),
                (0.35, [(0.0, "#8ADFC6"), (0.35, "#57C5A8"), (0.6, "#36A48E"), (1.0, "#227C6A")]),
                (1.0, [(0.0, "#CFF7EA"), (0.35, "#A6EAD5"), (0.6, "#6ED3B8"), (1.0, "#3DAA91")])]
DIG_BELLY = [(0.0, [(0.0, "#A8E3CF"), (0.5, "#86CDB6"), (1.0, "#5FAA92")]),
             (0.35, [(0.0, "#E6FCF3"), (0.35, "#D2F6E8"), (0.6, "#B6ECD8"), (1.0, "#90D9BF")]),
             (1.0, [(0.0, "#FAFFFC"), (0.35, "#EEFDF6"), (0.6, "#DCF8EC"), (1.0, "#B8EED9")])]
DIG_SKIN = [(0.0, "#63D7B4"), (0.5, "#3FB896"), (0.8, "#2A9478"), (1.0, "#176B57")]     # R2: lighter under the velvet
DIG_BROW = [(0.0, [(0.0, "#0C4238"), (1.0, "#072A24")]), (0.35, [(0.0, "#135646"), (1.0, "#0C4238")]),
            (1.0, [(0.0, "#1E7563"), (1.0, "#135646")])]
DIG_BROW_SKIN = [(0.0, "#135646"), (0.5, "#0C4238"), (1.0, "#072A24")]
NOSE = [(0.0, "#FFD6BF"), (0.45, "#FFB896"), (0.8, "#E8906E"), (1.0, "#B8604A")]
PAD = [(0.0, "#F6B8A2"), (0.5, "#E39A82"), (0.8, "#C27862"), (1.0, "#8E4E3E")]
INNER_EAR = [(0.0, "#F7B9A6"), (0.5, "#E49C88"), (1.0, "#A85E4E")]
CLAW = [(0.0, "#FFFBEE"), (0.45, "#FFF4DA"), (0.8, "#E8D7AF"), (1.0, "#BBA57A")]
IRIS_DIG = "#4A2E1C"
PUPIL = "#0D0806"
EYE_WHITE = "#F7F5F0"
MOUTH_IN = "#4A1A12"
TONGUE = "#E2566A"
STEEL_PAINT = [(0.0, "#8497A1"), (0.45, "#657883"), (0.8, "#4B5B64"), (1.0, "#2E3A41")]
STEEL_WORN = [(0.0, "#EEF3F6"), (0.45, "#CCD5DC"), (0.8, "#A6B1BA"), (1.0, "#737E87")]
IRON_LUT = [(0.0, "#6E747C"), (0.45, "#4B5057"), (0.8, "#34383E"), (1.0, "#1E2126")]
PENCIL = [(0.0, "#FFD27A"), (0.45, "#F7A734"), (0.8, "#D9801A"), (1.0, "#9E540A")]
TAG_RED = "#E4553A"

FUR_BANDS = 5

# ================================================================== LOOK-L: the smooth premium-VINYL finish (opt-in)
# OWNER 2026-09-28 13:56 ("the loading image is not as smooth and good as the original ... it is so obvious"): the
# velvet strand fur read as felt / sandpaper next to the category's smooth glossy vinyl-toy crews. spec["finish"] =
# "vinyl" drops every fur part and gives the body a glossy vinyl coat: a SATURATED mint ladder (u 0 thin / convex:
# lighter + a touch warmer = the fake subsurface glow; u 1 crease: deeper + MORE saturated, never grey), a soft
# clearcoat (crisp speculars from the high-key room), a small emissive in the skin's own hue (lifts the shadow side
# the way subsurface light does: the shadows stay mint, not grey), a cream-mint belly / snout patch in the same
# coat. Anti-DOUGH (the owner rejected smooth "dough" workers on 09-27; art-direction §1.3 R2 / R7): constructed
# material boundaries at every joint -- a cream canvas SLEEVE with a rolled hem over each upper arm, a leather WRIST
# CUFF, laced WORK BOOTS with a cream sole -- plus the spade paws' ivory claws, the vest, belt, hat and goggles.
# The default finish stays "fur" (home rigs, events, avatars are unchanged until the owner approves the look there).
VINYL_SKIN = [(0.0, "#8CF7D0"), (0.20, "#52EAB9"), (0.45, "#22D6A0"), (0.70, "#0EB488"), (0.88, "#068E6C"), (1.0, "#046A52")]
VINYL_BELLY = [(0.0, "#E2FCEF"), (0.20, "#CDF6E2"), (0.45, "#B2EAD2"), (0.70, "#86D8BA"), (0.88, "#56BC9C"), (1.0, "#36987C")]
VINYL_BROW = [(0.0, "#1F8A70"), (0.5, "#136650"), (1.0, "#0A4535")]
VINYL_GLOW = "#0E4A38"            # emissive: the fake subsurface lift, in the skin's own hue
VINYL_MAT = dict(rough=0.30, ior=1.42, clearcoat=0.50, cc_rough=0.14)   # r2: a softer coat (r1's 0.08 made tiny hot spots)
# LOOK-L fix round 1: the v2 coat's broad sheen veiled the colour (skin rendered C* ~40 from a C* ~60 ladder); a lower
# base reflectance + a thinner, tighter clearcoat keeps the colour and puts the gloss into crisp highlights
VINYL_MATS = {1: VINYL_MAT, 2: dict(rough=0.36, ior=1.33, clearcoat=0.30, cc_rough=0.06)}
SLEEVE = [(0.0, "#FBF1DC"), (0.30, "#F0DDB8"), (0.62, "#DEC293"), (0.85, "#BF9C68"), (1.0, "#86683E")]
SLEEVE1 = [(0.0, "#FFF8E8"), (0.30, "#F4E6C6"), (0.62, "#E0C592"), (0.85, "#BE9A62"), (1.0, "#846438")]
BOOT = [(0.0, "#B8743E"), (0.35, "#8A4F22"), (0.7, "#5E3212"), (1.0, "#361A06")]
BOOT_SOLE = [(0.0, "#FFF6E2"), (0.45, "#F0DDB6"), (0.8, "#CDB080"), (1.0, "#8C7248")]
LACE = "#F6E9CC"
BOOT_M = [(0.0, "#A8683A"), (0.35, "#7E4622"), (0.7, "#582E12"), (1.0, "#301606")]      # fix round 2: oiled matte leather
BOOT_SOLE_M = [(0.0, "#5A4A3E"), (0.45, "#3E3228"), (0.8, "#2A2019"), (1.0, "#16100C")]  # a dark rubber sole
EYE_WHITE_V = "#FBFAF6"
LASH = "#0A2E26"
# LOOK-L fix round 1 (the judges at 1:1: dingy cream eye whites, gummy paws, white claws sparkling into noise, one
# cloned face): a neutral cool-white sclera, satin paws with defined fingers, cream-tan claws, a second skin tint and a
# neckerchief so the crowd reads as a cast
EYE_WHITE_V2 = "#F7FAFD"
CLAW_V = [(0.0, "#F6E7C8"), (0.40, "#E6CD9C"), (0.75, "#C4A26E"), (1.0, "#846644")]
VINYL_SKIN_B = [(0.0, "#9CF2DA"), (0.20, "#5CE0C4"), (0.45, "#24C7AB"), (0.70, "#10A68E"), (0.88, "#077F6E"), (1.0, "#055E52")]
VINYL_BELLY_B = [(0.0, "#E4FBF4"), (0.20, "#CCF3E8"), (0.45, "#AEE6D8"), (0.70, "#80D2C0"), (0.88, "#52B4A0"), (1.0, "#349282")]
# LOOK-L fix round 1, r2/r3: the v3 cool room drew the v2 ladders ~10 C* greyer (the big convex head sits on the
# ladder's light end: r3 lifts its chroma, C* 40 -> 52) and ~8 deg bluer (measured on the hero:
# C* 44.5 -> 34.3, hue 163 -> 171): the "2" ladders sit ~5 deg yellower and ~10 C* richer, so the rendered skin lands
# back on a clean saturated mint
VINYL_SKIN2 = [(0.0, "#72F4BA"), (0.20, "#40EAA2"), (0.45, "#18D48E"), (0.70, "#06B474"), (0.88, "#038E58"), (1.0, "#026A42")]
VINYL_BELLY2 = [(0.0, "#E6FEF0"), (0.20, "#CDF8E0"), (0.45, "#AEEED0"), (0.70, "#80DCB4"), (0.88, "#4CC094"), (1.0, "#2C9A74")]
VINYL_SKIN_B2 = [(0.0, "#62F0CC"), (0.20, "#38E2B8"), (0.45, "#16CCA8"), (0.70, "#06AA8A"), (0.88, "#04866C"), (1.0, "#02604E")]
VINYL_BELLY_B2 = [(0.0, "#E6FCF6"), (0.20, "#CCF4EA"), (0.45, "#AAE8DA"), (0.70, "#7CD4C2"), (0.88, "#4AB8A2"), (1.0, "#2C9684")]
# LOOK-2 (the finish judge on v4, build/p/LOOK/round3.json finish_r3 #5-#7: "hard, tiny, near-white clearcoat
# hotspots over teal-grey shadows read wet gummy"; "below the vest the belly and legs are bare mint"; "long pale
# pointed claws on spread fingers read gremlin"): vmat 3 = a SATIN vinyl (no clearcoat spike: a broad, dimmer, soft
# highlight) with a warm yellow-green emissive lift (the fake subsurface glow keeps the shadow side warm and saturated);
# the "3" ladders run a touch yellower in the deep end (never toward teal-grey); work TROUSERS from under the vest to
# the boot tops; "mitt" paws (chunky, short fat fingers, short ROUNDED claws). All opt-in: the defaults are unchanged.
VINYL_MATS[3] = dict(rough=0.44, ior=1.40, clearcoat=0.10, cc_rough=0.40)
VINYL_GLOW3 = "#1E4E26"           # emissive: a warm yellow-green lift (was the teal #0E4A38)
# LOOK-2 fix round (the finish judge on the home crew, S5 MEASURED: "sheen area share 0 vs theirs 0.014 while small
# speculars sit at the top of the range: many pin highlights and no broad satin sheen on heads and bellies. FIX: a
# broader, dimmer sheen lobe (roughness about 0.4) without the old clearcoat pin hotspots"): vmat 4 = vmat 3 + a thin
# BROAD coat (cc_rough 0.30: a soft whitening lobe across the dome and belly, no pin)
VINYL_MATS[4] = dict(rough=0.40, ior=1.46, clearcoat=0.20, cc_rough=0.40)      # r2: cc_rough 0.30 -> 0.40 (the cheek streaks read wet)
VINYL_SKIN3 = [(0.0, "#8AF6D2"), (0.20, "#50EABA"), (0.45, "#20D6A2"), (0.70, "#0CB47E"), (0.88, "#068E58"), (1.0, "#04683C")]
VINYL_BELLY3 = [(0.0, "#EAFDF2"), (0.20, "#D2F8E4"), (0.45, "#B4EED2"), (0.70, "#86DCB4"), (0.88, "#52C08C"), (1.0, "#349862")]
VINYL_SKIN_B3 = [(0.0, "#80F2DE"), (0.20, "#46E4C6"), (0.45, "#1ACEB0"), (0.70, "#0AAE90"), (0.88, "#068A68"), (1.0, "#046448")]
VINYL_BELLY_B3 = [(0.0, "#EEFCF0"), (0.20, "#D2F6E2"), (0.45, "#B2ECD0"), (0.70, "#84D8B4"), (0.88, "#50BC92"), (1.0, "#32966E")]
TROUSERS = {"khaki": [(0.0, "#E2C48E"), (0.30, "#C9A56C"), (0.62, "#A7814C"), (0.85, "#7C5C32"), (1.0, "#4C361A")],
            "cocoa": [(0.0, "#B08466"), (0.30, "#8E6446"), (0.62, "#6E4A30"), (0.85, "#4E321E"), (1.0, "#2C1A0E")],
            "denim": [(0.0, "#7E9CC4"), (0.30, "#5A78A4"), (0.62, "#3E5A86"), (0.85, "#2A3E62"), (1.0, "#16223A")]}
TROUSERS1 = {"khaki": [(0.0, "#D8B882"), (0.30, "#BD9860"), (0.62, "#9C7644"), (0.85, "#72522C"), (1.0, "#443016")],
             "cocoa": [(0.0, "#A47A5C"), (0.30, "#845C40"), (0.62, "#66442C"), (0.85, "#482E1A"), (1.0, "#28180C")],
             "denim": [(0.0, "#7494BC"), (0.30, "#52709C"), (0.62, "#38527E"), (0.85, "#26385A"), (1.0, "#141E34")]}
CLAW_M = [(0.0, "#F4E2C0"), (0.40, "#E2C898"), (0.75, "#C09C6A"), (1.0, "#806040")]
SCARF = {"coral": [(0.0, "#FF9C86"), (0.35, "#F2553F"), (0.7, "#CF3A26"), (1.0, "#8A2414")],
         "sky": [(0.0, "#BDEBFF"), (0.35, "#5CC4F2"), (0.7, "#2392CC"), (1.0, "#0F5E8A")]}

# ================================================================== geometry constants (feet on y 0, facing +Z)
HEAD_C = np.array([0.0, 1.60, 0.06])
HEAD_R = (0.47, 0.42, 0.44)
NECK = np.array([0.0, 1.30, 0.0])
NOSE_C = np.array([0.0, 1.475, 0.745])
EYES = [(-0.200, 1.715), (0.200, 1.715)]
EYE_R = (0.104, 0.124, 0.074)
SHOULDERS = [np.array([-0.40, 1.20, 0.0]), np.array([0.40, 1.20, 0.0])]


def _rot(yaw=0.0, roll=0.0, nod=0.0):
    return S.rot((0, 0, 1), roll) @ S.rot((0, 1, 0), yaw) @ S.rot((1, 0, 0), nod)


class HeadXf:
    """Head space -> world: p' = R (p - NECK) + NECK (the head turns / tilts / nods about the neck)."""

    def __init__(self, yaw=0.0, roll=0.0, nod=0.0, lift=0.0):
        self.R = _rot(yaw, roll, nod)
        self.t = NECK - self.R @ NECK + np.array([0.0, lift, 0.0])      # lift: a taller body carries the head up

    def sdf(self, s):
        return s.transform(self.R).translate(*self.t)

    def p(self, P):
        return np.asarray(P, float) @ self.R.T + self.t

    def n(self, N):
        return np.asarray(N, float) @ self.R.T

    def inv(self, P):
        return (np.asarray(P, float) - self.t) @ self.R


def eyes_of(eye_scale=1.0, eye_lift=0.0):
    """The eye centres (head space) for an eye scale: bigger eyes sit a little wider apart and higher (LOOK-L)."""
    dx = 0.033 * (eye_scale - 1.0)
    return [(EYES[0][0] - dx, EYES[0][1] + eye_lift), (EYES[1][0] + dx, EYES[1][1] + eye_lift)]


class BodyXf:
    """LOOK-L: a torso LEAN (deg, + = toward the camera) and TWIST (deg about +Y) about the hips' pivot, applied to
    everything above the legs (torso, kit, arms, head); the legs stay in world space so the feet can plant.
    Identity (and never applied) when both are 0: the home rigs mesh exactly as before."""
    PIVOT = np.array([0.0, 0.50, 0.0])

    def __init__(self, lean=0.0, twist=0.0, roll=0.0):
        self.on = bool(lean or twist or roll)
        self.R = S.rot((0, 0, 1), roll) @ S.rot((0, 1, 0), twist) @ S.rot((1, 0, 0), lean)

    def sdf(self, s):
        if not self.on:
            return s
        return s.translate(*(-self.PIVOT)).transform(self.R).translate(*self.PIVOT)

    def p(self, P):
        P = np.asarray(P, float)
        return P if not self.on else (P - self.PIVOT) @ self.R.T + self.PIVOT

    def n(self, N):
        N = np.asarray(N, float)
        return N if not self.on else N @ self.R.T

    def inv(self, P):
        P = np.asarray(P, float)
        return P if not self.on else (P - self.PIVOT) @ self.R + self.PIVOT

    def head(self, hx):
        """Compose a HeadXf with the lean: p'' = Rb (R p + t - pivot) + pivot."""
        if not self.on:
            return hx
        out = HeadXf()
        out.R = self.R @ hx.R
        out.t = self.R @ (hx.t - self.PIVOT) + self.PIVOT
        return out


NOSE_MUZZLE = np.array([0.0, 1.535, 0.668])     # LOOK-L: the short-muzzle face's nose (on the muzzle's top front)


def head_skin_local(head_s=1.0, snout="long", snout_back=0.0):
    """snout "long" = R2's mole cone (the nose far out on its tip); "muzzle" (LOOK-L, the vinyl Loading crew) = a
    short wide rounded muzzle -- the nose on its top front and room for a big laughing mouth under it."""
    hr = np.array(HEAD_R) * head_s
    head = ellipsoid(*hr).translate(*HEAD_C)
    if snout == "muzzle":
        snout = union(ellipsoid(0.265, 0.185, 0.220).translate(0.0, 1.405, 0.470 - snout_back),
                      ellipsoid(0.150, 0.110, 0.150).translate(0.0, 1.520, 0.540 - snout_back), k=0.06)
    else:
        snout = round_cone((0, 1.52, 0.34), (0, 1.43, 0.64), 0.20, 0.140)
    ears = [ellipsoid(0.110, 0.118, 0.050).transform(K.frame_from([sx * 0.25, 1.0, 0.1], [sx * 0.62, 0.1, 0.78]))
            .translate(sx * 0.430 * head_s, 1.705, -0.03) for sx in (-1, 1)]
    s = union(head, snout, k=0.07)
    s = union(s, *ears, k=0.03)
    return dict(head=head, snout=snout, ears=ears, skin=s)


def body_space(girth=1.0, height=1.0):
    g, h = girth, height
    hips = ellipsoid(0.60 * g, 0.52 * h, 0.50 * g).translate(0, 0.66 * h, 0.0)
    chest = ellipsoid(0.46 * g, 0.42 * h, 0.42 * g).translate(0, 1.08 * h, 0.02)
    torso = union(hips, chest, k=0.25)
    return torso


def legs_sdf(legs=None, girth=1.0):
    """Per side: None (the rest stance) or (hip, ankle, foot_c[, foot_dir]) -- one cone -- or, LOOK-L, (hip, KNEE,
    ankle, foot_c, foot_dir) -- a bent leg through the knee (a run / a leap). feet_pts also carries the leg's
    joint chain for the vinyl finish's boots."""
    out, soles, feet_pts = [], [], []
    for i, sx in enumerate((-1, 1)):
        spec = (legs or {}).get("L" if sx < 0 else "R")
        knee = None
        if spec is None:
            hip = np.array([sx * 0.27 * girth, 0.36, 0.06])
            ank = np.array([sx * 0.31 * girth, 0.13, 0.12])
            foot_c = np.array([sx * 0.32 * girth, 0.10, 0.17])
            fdir = np.array([0.0, 0.0, 1.0])
        elif len(spec) == 5:
            hip, knee, ank, foot_c = (np.asarray(v, float) for v in spec[:4])
            fdir = K.unit(spec[4])
        else:
            hip, ank, foot_c = (np.asarray(v, float) for v in spec[:3])
            fdir = K.unit(spec[3]) if len(spec) > 3 else np.array([0.0, 0.0, 1.0])
        R = K.frame_from(fdir, [0, 1, 0.0])      # y = toe direction, z = up
        foot = K.local_ellipsoid((0.175, 0.235, 0.105), R, foot_c)
        if knee is None:
            leg = round_cone(tuple(hip), tuple(ank), 0.17, 0.15)
        else:
            leg = K.limb([hip, knee, ank], [0.17, 0.158, 0.15], k=0.05)
        out.append(union(leg, foot, k=0.06))
        sole = K.local_ellipsoid((0.165, 0.22, 0.06), R, foot_c - R[:, 2] * 0.065)
        soles.append(sole.intersect(K.local_ellipsoid((0.4, 0.4, 0.4), R, foot_c - R[:, 2] * 0.40).offset(0.0)))
        feet_pts.append((foot_c, R, hip, knee, ank))
    return out, soles, feet_pts


def work_boots(feet_pts, matte=False, tag="", lace=None):
    """LOOK-L vinyl finish: a laced leather work boot over each foot (the ankle shaft a third of the way up the lower
    leg, a rolled top, a cream crepe sole, a toe cap seam, three cream laces): the leg meets the boot at a material
    edge (anti-dough R2). matte (LOOK-L fix round 2, the boss: "shiny plasticine blobs ... cream disc soles look like
    display bases"): oiled MATTE leather, a dark rubber sole, bigger laces. -> [(name, sdf, mat, voxel)]"""
    uppers, soles, laces, rims = [], [], [], []
    for foot_c, R, hip, knee, ank in feet_pts:
        up = knee if knee is not None else hip
        top = ank + (up - ank) * 0.42
        ex, ey, ez = R[:, 0], R[:, 1], R[:, 2]           # across, toe, up (foot frame)
        foot = K.local_ellipsoid((0.190, 0.255, 0.118), R, foot_c + ey * 0.012 + ez * 0.008)
        shaft = round_cone(tuple(top), tuple(ank + ez * 0.02), 0.186, 0.180)
        upper = union(foot, shaft, k=0.07)
        sole_c = foot_c + ey * 0.012 - ez * 0.080
        sole = K.local_ellipsoid((0.205, 0.272, 0.052), R, sole_c).intersect(
            K.local_ellipsoid((0.5, 0.5, 0.5), R, sole_c - ez * 0.45), k=0.01)
        upper = upper.subtract(K.local_ellipsoid((0.25, 0.32, 0.5), R, sole_c - ez * 0.52), k=0.01)
        rim = torus(0.184, 0.020).transform(K.frame_from(K.unit(up - ank), [1.0, 0.0, 0.0])).translate(*top)
        for j in range(3):
            lp = foot_c + ey * (0.06 + 0.07 * j) + ez * (0.10 - 0.035 * j)
            lp = lp + ez * 0.0
            laces.append(capsule(tuple(lp - ex * 0.055 + ez * 0.028), tuple(lp + ex * 0.055 + ez * 0.028), 0.0115))
        uppers.append(upper)
        soles.append(sole)
        rims.append(rim)
    if matte:
        return [("boots", union(*uppers), K.skin(f"d_bootm{tag}", BOOT_M, None, rough=0.66, ior=1.3), 0.004),
                ("bootRims", union(*rims), K.skin(f"d_bootrimm{tag}", BOOT_M, None, rough=0.7, ior=1.25), 0.0025),
                ("bootSoles", union(*soles), K.skin(f"d_bootsolem{tag}", BOOT_SOLE_M, None, rough=0.8, ior=1.2), 0.003),
                ("bootLaces", union(*laces), satin(f"d_lacem{tag}{'d' if lace else ''}", lace or LACE, rough=0.7), 0.002)]
    return [("boots", union(*uppers), K.skin("d_boot", BOOT, None, rough=0.40, ior=1.38, clearcoat=0.40, cc_rough=0.16), 0.004),
            ("bootRims", union(*rims), K.skin("d_bootrim", BOOT, None, rough=0.45, ior=1.3), 0.0025),
            ("bootSoles", union(*soles), K.skin("d_bootsole", BOOT_SOLE, None, rough=0.55, ior=1.3), 0.003),
            ("bootLaces", union(*laces), satin("d_lace", LACE, rough=0.6), 0.002)]


def trousers_sdf(torso, legs, feet_pts, hgt=1.0, BX=None, boot_fit=False):
    """LOOK-2 (the finish judge: "below the vest the belly and legs are bare mint ... the 'dough' join the owner
    rejected"): canvas work trousers from under the vest's hem (tucked in: inside the vest's inner shell, under the belt)
    down each leg to just inside the boot's rolled top. A shell over the hips + the legs; the hem ends in each boot."""
    seat = torso.offset(0.024).intersect(D.slab_y(-1.0, 0.86 * hgt), k=0.02)
    if BX is not None and BX.on:
        seat = BX.sdf(seat)
    tubes = []
    for leg, (foot_c, R, hip, knee, ank) in zip(legs, feet_pts):
        up = knee if knee is not None else hip
        hem = ank + (up - ank) * 0.36                     # inside the boot (the shaft's rolled top is at 0.42)
        ax = K.unit(up - ank)
        keep = _halfspace(hem, ax)
        tube = leg.offset(0.030).intersect(keep, k=0.01)
        if boot_fit:
            # v6: below the boot's rolled top the trouser leg is held strictly INSIDE the boot shaft (the tube and the
            # shaft have nearly the same radius: a crouched leg z-fought into a jagged, torn-looking hem)
            ez_ = R[:, 2]
            btop = ank + (up - ank) * 0.42
            inside = round_cone(tuple(btop + ax * 0.02), tuple(ank + ez_ * 0.02), 0.186 - 0.016, 0.178 - 0.016)
            tube = tube.intersect(union(_halfspace(btop - ax * 0.004, ax), inside), k=0.004)
        tubes.append(tube)
    return union(seat, *tubes, k=0.05)


TROUSERS_EDGE = [(0.0, "#EAD0A0"), (0.30, "#D0AE76"), (0.62, "#AC8852"), (0.85, "#806036"), (1.0, "#503A1C")]
# (a touch cool: the warm key + honey bounce turn a neutral white cream -- r2 test render: C* 10-12)
# (r2 measured on the composite: at ~0.84 albedo the key-lit half still clipped -- hero sclera median 96, 39 % of it
# above L* 99 -- so ~0.76 in the lit half; the render lands it at L* ~90-93)
SCLERA6 = [(0.0, "#D4D8DE"), (0.45, "#C8CDD4"), (0.75, "#B6BCC4"), (1.0, "#99A0AA")]        # open: ~0.76 albedo
SCLERA6_SH = [(0.0, "#BCC1C9"), (0.45, "#AEB4BD"), (0.75, "#9DA4AE"), (1.0, "#848B96")]     # under the upper lid


def _sclera_vfn(hx, centres, rx, ry):
    """v6 sclera shading (head space): 1 in the upper lid's shadow band (the top ~40 % of the eyeball) + a falloff
    toward the rim / corners, 0 on the open lit white."""
    C_ = np.asarray(centres, float)

    def fn(v):
        q = hx.inv(np.asarray(v, float))
        dd = np.stack([np.hypot((q[:, 0] - c[0]) / rx, (q[:, 1] - c[1]) / ry) for c in C_], 0)
        i = np.argmin(dd, 0)
        ty = (q[:, 1] - C_[i, 1]) / ry
        rr = dd[i, np.arange(len(q))]
        top = np.clip((ty - 0.26) / 0.64, 0, 1) ** 1.4
        rim = np.clip((rr - 0.55) / 0.45, 0, 1) ** 2
        return np.clip(np.maximum(top, 0.45 * rim), 0, 1)
    return fn


def weave_vfn(period=0.020, amp=0.28):
    """v6: a clean fine canvas WEAVE for the v term (two crossed sine threads, low amplitude) instead of heathered
    value noise (the judge: "a faint noisy grain")."""
    f = 2 * math.pi / period

    def fn(v):
        p = np.asarray(v, np.float64)
        a = np.sin(f * (0.71 * p[:, 0] + 0.71 * p[:, 2]))
        b = np.sin(f * p[:, 1])
        return np.clip(0.5 + amp * a * b, 0, 1)
    return fn


def trousers_detail(torso, legs, feet_pts, hgt=1.0, BX=None):
    """v6 work trousers: trousers_sdf's shell + raised side SEAMS down the outer legs, soft knee CREASES (bent legs:
    two ridges on the knee front), the hems BLOUSED over the boot tops (a soft bulging ring above each boot's rim), a
    WAISTBAND ridge at the top edge. -> (sdf, [(name, sdf)]) -- the extras: a patch POCKET (+ flap) on each outer
    thigh, in the lighter edge ramp (their edges read sewn and thick)."""
    base = trousers_sdf(torso, legs, feet_pts, hgt, BX, boot_fit=True)
    ridges, pockets = [], []
    # the waistband's BELT LOOPS over the belt (the belt runs where the waistband is: a separate band read wrong)
    loops = []
    for lx in (-0.44, -0.20, 0.20, 0.44):
        loops.append(torso.offset(0.068).subtract(torso.offset(0.020)).intersect(
            box(0.017, 0.064, 1.0, round=0.008).translate(lx, 0.525 * hgt, 0.6), k=0.004))
    loops = union(*loops)
    if BX is not None and BX.on:
        loops = BX.sdf(loops)
    pockets.append(loops)
    for leg, (foot_c, R, hip, knee, ank) in zip(legs, feet_pts):
        sx = 1.0 if hip[0] >= 0 else -1.0
        up = knee if knee is not None else hip
        chain = [hip, knee, ank] if knee is not None else [hip, ank]
        rads = [0.17, 0.158, 0.15] if knee is not None else [0.17, 0.15]
        hem = ank + (up - ank) * 0.36
        # the side seam: along the chain's outer side, from the hip down to just above the boot's rim
        pts, rr = [], []
        for j in range(len(chain) - 1):
            a0, a1 = chain[j], chain[j + 1]
            ax = K.unit(a1 - a0)
            lat = np.array([sx, 0.0, 0.0]) - ax * sx * ax[0]
            lat = K.unit(lat + np.array([0.0, 0.0, -0.25]))
            for t in np.linspace(0.0, 1.0, 5)[(1 if j else 0):]:
                if j == len(chain) - 2 and t > 0.52:
                    continue
                r_ = rads[j] + (rads[j + 1] - rads[j]) * t + 0.030
                pts.append(a0 + (a1 - a0) * t + lat * (r_ + 0.002))
                rr.append(0.0085)
        if len(pts) >= 2:
            ridges.append(K.limb(np.array(pts), np.array(rr), k=0.006))
        # (r2: a blousing ring over the boot top read as a hoop round the leg -- dropped; the boot's rolled top is the hem)
        if knee is not None:           # two short soft creases on the FRONT of the bent knee (arcs, not rings)
            th, sh_ = K.unit(knee - hip), K.unit(ank - knee)
            kax = K.unit(th + sh_)
            front = K.unit(np.cross(np.cross(th, sh_), kax)) if np.linalg.norm(np.cross(th, sh_)) > 1e-3 else np.array([0, 0, 1.0])
            if np.dot(front, np.array([0, 0, 1.0])) < 0:
                front = -front
            for dz in (-0.050, 0.045):
                ring = torus(0.158 + 0.030 - 0.002, 0.0075).transform(K.frame_from(kax, front)).translate(*(knee + kax * dz))
                ridges.append(ring.intersect(_halfspace(knee + front * 0.13, front), k=0.015))
        # the patch pocket on the outer thigh (+ its flap), hugging the trouser surface
        seg_b = knee if knee is not None else ank
        pc = hip + (seg_b - hip) * 0.42
        axp = K.unit(seg_b - hip)
        latp = K.unit(np.array([sx, 0.0, 0.35]) - axp * np.dot(np.array([sx, 0.0, 0.35]), axp))
        Rp = K.frame_from(axp, latp)
        rloc = 0.17 + (0.158 - 0.17) * 0.42 + 0.030
        cpos = pc + latp * rloc
        box_p = box(0.070, 0.082, 0.10, round=0.018).transform(Rp).translate(*(cpos + axp * 0.01))
        box_f = box(0.076, 0.024, 0.10, round=0.010).transform(Rp).translate(*(cpos - axp * 0.070))
        pockets.append(base.offset(0.012).intersect(box_p, k=0.006))
        pockets.append(base.offset(0.019).intersect(box_f, k=0.004))
    return union(base, *ridges, k=0.008), [("trouserPockets", union(*pockets, k=0.003))]


def _halfspace(p0, n):
    """{x : (x - p0) . n >= 0} as an SDF (negative inside)."""
    from sdf import SDF as _S
    p0 = np.asarray(p0, np.float32)
    n = np.asarray(n, np.float32) / np.linalg.norm(n)
    return _S(lambda p: (-(np.asarray(p, np.float32) - p0) @ n).astype(np.float32), [-3, -3, -3], [3, 3, 3])


# ================================================================== paws

def mitt_paw(wrist, d, palm_n, r=0.155, curl=15.0, spread=24.0, claw_bend=30.0):
    """LOOK-2 (the finish judge: "long pale pointed claws on spread fingers read gremlin or lizard ... a chunkier
    mitt-like paw with short, rounded claws"): a chunky MITT -- a thick rounded palm, three short FAT fingers kept close
    together (spread x0.55), a fat thumb, and a short BLUNT claw capping each fingertip (a rounded nail, not a hook).
    -> dict(paw, claws, pads)."""
    R = K.frame_from(d, palm_n)
    ex, ey, ez = R[:, 0], R[:, 1], R[:, 2]
    wrist = np.asarray(wrist, float)
    c = wrist + ey * r * 0.92
    palm = K.local_ellipsoid((r * 1.10, r * 0.98, r * 0.66), R, c)
    fingers, claws = [palm], []
    # one soft palm pad (no fingertip beans: at size they read as spots)
    pads = [K.local_ellipsoid((r * 0.62, r * 0.50, r * 0.24), R, c + ez * r * 0.50 - ey * r * 0.08)]
    sp = spread * 0.55
    for i in (-1, 0, 1):
        fd = K.rotate_about(ey, ez, -i * sp)
        base = c + fd * r * 0.56 + ex * i * r * 0.10
        tipd = K.unit(K.rotate_about(fd, np.cross(fd, ez), curl))
        tip = base + tipd * r * (0.40 - 0.05 * abs(i))
        fingers.append(round_cone(tuple(base), tuple(tip), r * 0.40, r * 0.37))
        cd = K.unit(K.rotate_about(tipd, np.cross(tipd, ez), claw_bend))
        cb = tip + tipd * r * 0.24 - ez * r * 0.04
        # (v5 draft: a fat short cone read as a round BEAD at size -- a little longer and tapered, still blunt)
        claws.append(K.limb([cb - tipd * r * 0.06, cb + K.unit(tipd + cd) * r * 0.14, cb + cd * r * 0.28],
                            [r * 0.15, r * 0.12, r * 0.075], k=0.004))
    tb = c + ex * r * 0.92 - ey * r * 0.16
    fingers.append(round_cone(tuple(tb), tuple(tb + K.unit(ex * 0.70 + ey * 0.62 + ez * 0.25) * r * 0.40), r * 0.36, r * 0.32))
    return dict(paw=union(*fingers, k=r * 0.24), claws=union(*claws, k=0.004), pads=union(*pads, k=r * 0.06))


# LOOK-2 round 2 (v6): FINGERLESS WORK GLOVES (the finish judge on v5: "the biggest hand on the page is a smooth mint
# lump with three cream beads ... put the crew in work gloves in a contrasting material, which also gives rule R2's
# material boundary"): matte brown work leather with light thread stitching, the mint fingertips + short cream claws
# poking out of the cut finger ends (the mole stays a mole), a flared gauntlet cuff instead of the glossy leather cuff
# (r2 test render: the first leather #AE7040 read as the vest's orange family -- a deeper, less saturated umber)
GLOVE = [(0.0, "#B48462"), (0.30, "#906244"), (0.62, "#6C442A"), (0.86, "#4A2C16"), (1.0, "#2C180A")]
GLOVE_EDGE = [(0.0, "#C89C78"), (0.30, "#A67A58"), (0.62, "#805636"), (0.86, "#58381E"), (1.0, "#36200E")]
GLOVE_PATCH = [(0.0, "#9C6C4C"), (0.30, "#7C5236"), (0.62, "#5C3820"), (0.86, "#3E2410"), (1.0, "#241406")]
GLOVE_THREAD = [(0.0, "#E6D2AE"), (0.45, "#D2BA90"), (0.8, "#AE9468"), (1.0, "#7A6444")]


def glove_paw(wrist, d, palm_n, r=0.155, curl=15.0, spread=24.0, claw_bend=30.0, thumb=None, thumb_curl=None):
    """A FINGERLESS work glove on a Digger paw (frame: y = d toward the fingers, z = palm_n): a flattish glove palm with
    a knuckle row on its back, three SEPARATED two-segment fingers -- the leather ends at the middle joint in a rolled
    edge, the mint fingertip comes out of it and ends in a short tapered cream claw -- a two-segment thumb (medial:
    `thumb` = the unit direction across the palm it sits on), three raised thread seams down the back, a flared
    gauntlet cuff with a rolled rim over the wrist. curl bends every finger toward the palm (the tip segment 1.0x, the
    leather segment 0.45x): ~15 open, ~100 wrapped round a rim / an arrow's edge.
    -> dict(glove, cuff, seams, tips, claws)"""
    R = K.frame_from(d, palm_n)
    ex, ey, ez = R[:, 0], R[:, 1], R[:, 2]
    tdir = K.unit(ex if thumb is None else thumb)
    wrist = np.asarray(wrist, float)
    c = wrist + ey * r * 0.88
    rx, ry, rz = r * 0.98, r * 0.90, r * 0.52
    palm = K.local_ellipsoid((rx, ry, rz), R, c)
    glove, rims, tips, claws, seams = [palm], [], [], [], []
    sp = spread * 0.70 + 6.0
    tc = curl if thumb_curl is None else thumb_curl
    for i in (-1, 0, 1):
        fd = K.rotate_about(ey, ez, -i * sp)
        ax = K.unit(np.cross(fd, ez))
        base = c + fd * r * 0.58 + ex * i * r * 0.05
        d1 = K.unit(K.rotate_about(fd, ax, curl * 0.45))
        ln1 = r * (0.40 - 0.04 * abs(i))
        k1 = base + d1 * ln1                                   # the middle joint: the leather ends here
        d2 = K.unit(K.rotate_about(fd, ax, curl))
        tip = k1 + d2 * r * (0.34 - 0.03 * abs(i))
        rf = r * 0.285
        glove.append(round_cone(tuple(base - d1 * r * 0.10), tuple(k1), rf * 1.04, rf))
        glove.append(sphere(r * 0.25).translate(*(base - ez * r * 0.16)))        # the knuckle on the back
        rims.append(torus(rf * 0.92, r * 0.058).transform(K.frame_from(d1, ez)).translate(*(k1 - d1 * r * 0.02)))
        tips.append(round_cone(tuple(k1 - d1 * r * 0.12), tuple(tip), rf * 0.84, rf * 0.76))
        cd = K.unit(K.rotate_about(d2, ax, claw_bend))
        cb = tip + d2 * r * 0.10 - ez * r * 0.05
        claws.append(K.limb([cb - d2 * r * 0.06, cb + K.unit(d2 + cd) * r * 0.10, cb + cd * r * 0.20],
                            [r * 0.13, r * 0.10, r * 0.050], k=0.003))
        # a raised thread seam from the knuckle down the back toward the wrist (on the palm's back surface)
        pts = []
        for t in np.linspace(0.0, 1.0, 6):
            lx = (i * 0.36 * (1 - 0.35 * t)) * rx
            ly = (0.62 - 1.20 * t) * ry
            lz = -rz * math.sqrt(max(0.05, 1 - (lx / rx) ** 2 - (ly / ry) ** 2)) - r * 0.012
            pts.append(c + ex * lx + ey * ly + ez * lz)
        seams.append(K.limb(np.array(pts), np.full(len(pts), r * 0.030), k=0.004))
    # the thumb: out of the palm's medial edge, two segments, curling across the palm
    tb = c + tdir * r * 0.78 - ey * r * 0.20 + ez * r * 0.05
    t1d = K.unit(tdir * 0.62 + ey * 0.66 + ez * 0.30)
    t1 = tb + t1d * r * 0.36
    t2d = K.unit(K.rotate_about(t1d, K.unit(np.cross(t1d, ez)), tc * 0.55) + ez * 0.10)
    t2 = t1 + t2d * r * 0.28
    glove.append(round_cone(tuple(tb), tuple(t1), r * 0.30, r * 0.27))
    rims.append(torus(r * 0.25, r * 0.055).transform(K.frame_from(t1d, ez)).translate(*(t1 - t1d * r * 0.02)))
    tips.append(round_cone(tuple(t1 - t1d * r * 0.10), tuple(t2), r * 0.23, r * 0.20))
    cb = t2 + t2d * r * 0.08 - ez * r * 0.04
    claws.append(K.limb([cb - t2d * r * 0.05, cb + t2d * r * 0.09, cb + K.unit(t2d + ez * 0.6) * r * 0.17],
                        [r * 0.11, r * 0.085, r * 0.045], k=0.003))
    # the gauntlet: a snug short cuff, a little wider at its mouth (r2: the first, r * 0.98 x 0.92 r long, read as a
    # big tube bigger than the hand), a rolled rim at the mouth
    g0, g1 = wrist - ey * r * 0.40, wrist + ey * r * 0.26
    cuff = round_cone(tuple(g0), tuple(g1), r * 0.80, r * 0.70)
    cuff = union(cuff, torus(r * 0.79, r * 0.065).transform(K.frame_from(ey, ez)).translate(*(g0 + ey * r * 0.02)), k=r * 0.03)
    # a reinforcing leather PATCH on the palm (a work glove's palm; reads when the palm faces the camera)
    patch = K.local_ellipsoid((rx * 0.74, ry * 0.66, rz * 1.0), R, c + ez * r * 0.02 + ey * r * 0.04).offset(r * 0.03).intersect(
        _halfspace(c + ez * rz * 0.55, ez), k=r * 0.02)
    return dict(glove=union(*glove, k=r * 0.07), rims=union(*rims), cuff=cuff, seams=union(*seams, k=0.003),
                tips=union(*tips), claws=union(*claws, k=0.003), patch=patch)


def spade_paw(wrist, d, palm_n, r=0.155, curl=15.0, spread=24.0, claw_len=0.075, claw_bend=40.0, defined=False):
    """A digger's SPADE paw: a broad flat palm, three short fingers fanned at the tip edge, an ivory claw at each
    fingertip continuing the finger's curl (claw_bend deg further toward the palm), bare palm + finger pads.
    defined (LOOK-L fix round 1, the vinyl Loading crew; the judges: "a gummy drip thumb", "a formless mint blob"):
    two-segment fingers with a knuckle, a real two-segment thumb with a rounded tip, and a small blend radius so each
    finger keeps its own form. -> dict(paw, claws, pads)."""
    R = K.frame_from(d, palm_n)
    ex, ey, ez = R[:, 0], R[:, 1], R[:, 2]
    wrist = np.asarray(wrist, float)
    c = wrist + ey * r * 0.95
    if defined:
        palm = K.local_ellipsoid((r * 1.02, r * 0.92, r * 0.50), R, c)
        fingers, claws, pads = [palm], [], [K.local_ellipsoid((r * 0.70, r * 0.56, r * 0.24), R, c + ez * r * 0.34 - ey * r * 0.08)]
        for i in (-1, 0, 1):
            fd = K.rotate_about(ey, ez, -i * (spread + 4.0))
            base = c + fd * r * 0.62
            knd = K.unit(K.rotate_about(fd, np.cross(fd, ez), curl * 0.55))
            knuckle = base + knd * r * 0.40
            tipd = K.unit(K.rotate_about(fd, np.cross(fd, ez), curl))
            tip = knuckle + tipd * r * 0.36
            fingers.append(K.limb([base, knuckle, tip], [r * 0.30, r * 0.27, r * 0.235], k=r * 0.05))
            pads.append(sphere(r * 0.16).translate(*(tip + ez * r * 0.17 - tipd * r * 0.04)))
            cb = tip + tipd * r * 0.14
            cd = K.unit(K.rotate_about(tipd, np.cross(tipd, ez), claw_bend))
            cm = cb + K.unit(tipd + cd) * claw_len * 0.50
            claws.append(K.limb([cb, cm, cm + cd * claw_len * 0.45], [r * 0.15, r * 0.10, r * 0.035], k=0.006))
        tb = c + ex * r * 0.86 - ey * r * 0.18
        t1 = tb + K.unit(ex * 0.75 + ey * 0.55 + ez * 0.25) * r * 0.34
        t2 = t1 + K.unit(ex * 0.25 + ey * 0.85 + ez * 0.35) * r * 0.30
        fingers.append(K.limb([tb, t1, t2], [r * 0.28, r * 0.25, r * 0.22], k=r * 0.05))
        return dict(paw=union(*fingers, k=r * 0.11), claws=union(*claws), pads=union(*pads, k=r * 0.05))
    palm = K.local_ellipsoid((r * 1.12, r * 1.02, r * 0.56), R, c)
    fingers, claws, pads = [palm], [], [K.local_ellipsoid((r * 0.78, r * 0.62, r * 0.26), R, c + ez * r * 0.38 - ey * r * 0.08)]
    for i in (-1, 0, 1):
        fd = K.rotate_about(ey, ez, -i * spread)
        base = c + fd * r * 0.72
        tipd = K.unit(K.rotate_about(fd, np.cross(fd, ez), curl))
        tip = base + tipd * r * 0.50
        fingers.append(round_cone(tuple(base), tuple(tip), r * 0.36, r * 0.31))
        pads.append(sphere(r * 0.19).translate(*(tip + ez * r * 0.20 - tipd * r * 0.05)))
        cb = tip + tipd * r * 0.12
        cd = K.unit(K.rotate_about(tipd, np.cross(tipd, ez), claw_bend))
        cm = cb + K.unit(tipd + cd) * claw_len * 0.55
        claws.append(K.limb([cb, cm, cm + cd * claw_len * 0.55], [r * 0.19, r * 0.13, r * 0.05], k=0.01))
    tb = c + ex * r * 0.95 - ey * r * 0.25
    fingers.append(round_cone(tuple(tb), tuple(tb + K.unit(ex * 0.8 + ey * 0.5 + ez * 0.2) * r * 0.45), r * 0.30, r * 0.26))
    return dict(paw=union(*fingers, k=r * 0.30), claws=union(*claws), pads=union(*pads, k=r * 0.08))


def grip_arm(Q, s, palm_n, r=0.155, rs=0.034):
    """wrist / d / palm for a paw GRIPPING a cylinder of radius rs through Q along s (the palm faces the shaft from the
    palm_n side, the fingers wrap round it)."""
    s = K.unit(s)
    pn = np.asarray(palm_n, float)
    pn = K.unit(pn - s * np.dot(pn, s))
    d = K.unit(np.cross(pn, s))
    c = np.asarray(Q, float) - pn * (rs + r * 0.42)
    wr = c - d * r * 0.95
    return dict(wr=tuple(wr), d=tuple(d), palm=tuple(pn), curl=100.0, spread=10.0, claw_bend=75.0, claw_len=0.05)


# ================================================================== face (head space)

def _arc_bottom(y0, curv):
    """Half-space ABOVE the arc y = y0 + curv * x^2 (an SDF bound, Lipschitz-safe for |x| <= 0.25 at curv 4)."""
    from sdf import SDF as _S
    return _S(lambda p: ((y0 + curv * p[:, 0] ** 2 - p[:, 1]) * 0.45).astype(np.float32), [-2, -2, -2], [2, 2, 2])


def _on_dome_y(skin, x, y, z_min=0.25):
    """y lowered in 0.005 steps until the ray at (x, y) hits the head's front (z >= z_min)."""
    for _ in range(60):
        if K.surface_z_of(skin, x, y) >= z_min:
            return y
        y -= 0.005
    return y


def digger_face(skin, mouth="smile", look=(0.10, 0.0), eyes="open", brows="friendly", lids_open=0.93, eye_scale=1.0,
                eye_lift=0.0, muzzle=False, eye_div=0.0, lash=1.0, laugh=1.0, low_lid=0.93, lid_gap=0.013, teeth_k=1.0,
                snout_back=0.0, iris_k=1.0, half_lid=0.05):
    """eye_scale / eye_lift (LOOK-L): bigger glossy eyes (iris, pupil and both glints scale with the eyeball).
    LOOK-L fix round 1 (the vinyl crew; the defaults keep every older face exactly): eye_div turns each eye's gaze a
    little OUTWARD (on the round head two parallel gazes read cross-eyed), lash scales the dark upper-lid line (the
    judges: "heavy lids, sleepy"), laugh scales the muzzle's open laugh (the hero's big mouth), low_lid places the thin
    lower lid of an open eye."""
    es = eye_scale
    if muzzle and mouth == "open":       # LOOK-2: the talking "open" mouth on the muzzle = a small laugh (laugh < 1)
        mouth = "laugh"
    out = dict(eyes=[], irises=[], pupils=[], glints=[], sockets=[], brows=[], lids=[], crease=[])
    for i, (ex, ey) in enumerate(eyes_of(es, eye_lift)):
        sx = -1 if i == 0 else 1
        rx, ry, rz = np.array(EYE_R) * np.array([es, es, 1.0 + 0.55 * (es - 1.0)])
        ez = K.surface_z_of(skin, ex, ey)
        c = np.array([ex, ey, ez - rz * 0.30])
        e = ellipsoid(rx, ry, rz).translate(*c)
        out["eyes"].append(e)
        out["sockets"].append(ellipsoid(rx * 1.16, ry * 1.12, rz * 1.3).translate(*c))
        lx, ly = look
        dd = K.unit([lx * rx + sx * eye_div * rx, ly * ry, rz])     # look: x > 0 = toward screen right, y > 0 = up
        sp = c + dd * np.array([rx, ry, rz])
        # LOOK-2 fix round (iris_k): bigger, darker irises + pupils (the map reader's eyes read blank at phone size)
        out["irises"].append(e.offset(0.0015).intersect(sphere(0.072 * es * iris_k).translate(*sp)))
        out["pupils"].append(e.offset(0.003).intersect(sphere(0.042 * es * iris_k).translate(*sp)))
        gk = 1.0 if es == 1.0 else 1.25          # LOOK-L: a bigger key glint (the vinyl eye's softbox reflection)
        gp = c + K.unit(dd + np.array([-0.32, 0.36, 0.0])) * np.array([rx, ry, rz])
        out["glints"].append(sphere(0.0190 * es * gk).translate(*(gp + dd * 0.005)))
        out["glints"].append(sphere(0.0060 * es * gk * 1.3 if es != 1.0 else 0.0060).translate(
            *(c + K.unit(dd + np.array([0.30, -0.28, 0.0])) * np.array([rx, ry, rz]) + dd * 0.004)))
        # the lid: a fur-covered shell over the eyeball; open = the top slice, half = the top ~55 %, closed = all
        e_this = eyes if eyes in ("open", "half", "closed") else ("closed" if (eyes == "wink" and sx > 0) else "open")
        if eyes == "happy":
            e_this = "open"
        elif eyes == "joy":
            e_this = "closed"
        shell = ellipsoid(rx + lid_gap, ry + lid_gap, rz + lid_gap).translate(*c)
        if e_this == "closed":
            out["lids"].append(shell)
            a = np.linspace(-0.92, 0.92, 11)
            xs = ex + a * (rx + 0.006)
            ys = ey - 0.012 - 0.030 * (1 - a ** 2)
            if eyes == "joy":             # LOOK-L: laughing closed eyes -- the crease arches UP (^ ^)
                ys = ey - 0.040 + 0.060 * (1 - a ** 2) * es
            zs = np.array([K.surface_z_of(shell, x, y) for x, y in zip(xs, ys)])
            out["crease"].append(K.limb(np.stack([xs, ys, zs - 0.004], 1), np.full(len(xs), 0.0085), k=0.004))
        else:
            lid = lids_open if e_this == "open" else half_lid      # (half_lid: LOOK-2 fix round's half-lid SMIRK height)
            cut = ey + lid * ry
            out["lids"].append(shell.intersect(box(0.3, 0.3, 0.3).translate(ex, cut + 0.3, c[2]), k=0.008))
            if e_this == "open":
                # a thin lower-lid rim (the eye sits in fur, round and open -- a thicker cheek lid read as anxious)
                # LOOK-L eyes "happy": the cheeks push the lower lid up (the smiling eye)
                low = ey - (0.60 if eyes == "happy" else low_lid) * ry
                out["lids"].append(shell.intersect(box(0.3, 0.3, 0.3).translate(ex, low - 0.3, c[2]), k=0.010))
            a = np.linspace(-0.95, 0.95, 11)
            xs = ex + a * (rx + 0.008) * max(0.12, math.sqrt(max(0.0, 1 - lid ** 2))) if lid >= 0.99 else \
                ex + a * (rx + 0.008) * math.sqrt(max(0.0, 1 - lid ** 2))     # (a fully open lid: never a 0-length crease)
            ys = np.full_like(xs, cut) - 0.002
            zs = np.array([K.surface_z_of(shell, x, y) for x, y in zip(xs, ys)])
            # LOOK-L: on the bigger vinyl eye the crease is a crisp dark LASH line (scales with the eye); lash 0 = none
            if lash > 0:
                out["crease"].append(K.limb(np.stack([xs, ys, zs - 0.004], 1), np.full(len(xs), 0.0078 * (1 + 0.8 * (es - 1)) * lash), k=0.004))
        # brow ridge (its own dark fur grows on it; R4: no floating brows)
        a = np.linspace(-1.0, 1.0, 9)
        bx = ex + sx * 0.014 + a * rx * 0.80
        bo = -0.085 * (es - 1.0)          # LOOK-L: the bigger eye's brow sits closer (it must clear the hat brim)
        if brows == "determined":         # inner ends lower: focused, keen
            by = ey + ry + 0.050 + bo + 0.022 * (1 - a ** 2) + sx * 0.020 * a
        elif brows == "raised":           # surprised / delighted
            by = ey + ry + 0.085 + bo + 0.034 * (1 - a ** 2) - sx * 0.006 * a
        elif brows == "happy":            # LOOK-L: a clean round arch, no tilt (the bigger eyes' delighted look)
            by = ey + ry + 0.060 + bo + 0.040 * (1 - a ** 2)
        else:                             # friendly: a soft raised arch, well clear of the lid, outer ends lower
            by = ey + ry + 0.074 + bo + 0.030 * (1 - a ** 2) - sx * 0.014 * a
        if es != 1.0:
            # LOOK-L: the bigger eyes push the arch toward the crown's edge, where a ray can miss the dome (its z ran
            # off to -inf: a giant bogus limb) -- step each point down onto the dome instead
            by = np.array([_on_dome_y(skin, x, y) for x, y in zip(bx, by)])
        bz = np.array([K.surface_z_of(skin, x, y) for x, y in zip(bx, by)])
        out["brows"].append(K.limb(np.stack([bx, by, bz + 0.003], 1), 0.016 + 0.012 * (1 - a ** 2) ** 0.6, k=0.015))
    for k_ in list(out):
        out[k_] = union(*out[k_]) if out[k_] else None
    if mouth == "laugh":
        # LOOK-L: a big happy LAUGH -- a lower JAW fills the pocket under the snout (a muzzle), and a wide D opens in
        # its front under the nose: two buck teeth under the upper lip, a dark inside, a tongue on the floor
        if muzzle:     # the short wide muzzle: a big SMILE -- a flat-ish top under the nose, a bottom that rises
            # steeply toward the corners (a crescent lying on its back: the corners up at the cheeks), down onto a jaw
            lg = laugh
            jaw = ellipsoid(0.225 + 0.03 * (lg - 1), 0.125 + 0.10 * (lg - 1), 0.200 + 0.03 * (lg - 1)).translate(0.0, 1.225 - 0.10 * (lg - 1), 0.445 - snout_back)
            skin_j = union(skin, jaw, k=0.07)
            # a bigger laugh grows TALLER, not wider (the corners stay inside the muzzle: at 1.4 a flatter bottom cut
            # the cheeks open into a dark crescent): the bottom arc steepens so the corners meet at x0
            top, curv, bot = 1.428 + 0.02 * (lg - 1), 0.70, 1.235 - 0.20 * (lg - 1)
            x0 = 0.205 + 0.03 * (lg - 1)
            curv_b = (top - curv * x0 ** 2 - bot) / x0 ** 2
            zt = K.surface_z_of(skin_j, 0.0, top + 0.01)
            slab = box(0.40, 0.40 + 0.12 * (lg - 1), 0.36).translate(0.0, 1.33 - 0.06 * (lg - 1), 0.61 - snout_back)
            cav = S.SDF_arc_top(top, curv).intersect(_arc_bottom(bot, curv_b), k=0.012).intersect(slab, k=0.01)
            inner = S.SDF_arc_top(top + 0.01, curv).intersect(_arc_bottom(bot - 0.01, curv_b)).intersect(
                box(0.40, 0.40 + 0.12 * (lg - 1), 0.10).translate(0.0, 1.33 - 0.06 * (lg - 1), 0.34 - snout_back))
            tk = teeth_k
            teeth = union(*[box(0.036 * tk, 0.042 * tk, 0.024, round=0.013 * tk).translate(sx * 0.040 * (0.5 + 0.5 * tk), top - 0.034 * tk - 0.004 * (1 - tk), zt - 0.040)
                            for sx in (-1, 1)])
            tongue = ellipsoid(0.125 * (1 + 0.25 * (lg - 1)), 0.052 * lg, 0.12).translate(0.012, bot + 0.030 * lg, 0.480 - 0.03 * (lg - 1) - snout_back)
        else:          # the long snout: the D on the snout's lower front
            jaw = ellipsoid(0.180, 0.118, 0.190).translate(0.0, 1.252, 0.515)
            top, wid, hh, curv, zy = 1.384, 0.168, 0.135, 1.10, 1.30
            skin_j = union(skin, jaw, k=0.07)
            zj = K.surface_z_of(skin_j, 0.0, zy)
            cav = ellipsoid(wid, hh, 0.21).translate(0.0, top - 0.60 * hh, zj + 0.03).intersect(S.SDF_arc_top(top, curv), k=0.012)
            inner = ellipsoid(wid - 0.008, hh - 0.010, 0.10).translate(0.0, top - 0.64 * hh, zj - 0.17).intersect(
                S.SDF_arc_top(top + 0.01, curv))
            teeth = union(*[box(0.032, 0.038, 0.022, round=0.012).translate(sx * 0.036, top - 0.036, zj - 0.028)
                            for sx in (-1, 1)])
            tongue = ellipsoid(wid * 0.62, 0.055, 0.11).translate(0.012, top - 1.28 * hh, zj - 0.10)
        out.update(jaw=jaw, cavity=cav, inner=inner, teeth=teeth, tongue=tongue)
        return out
    # R2: the mouth sits ON the snout's front, under the nose (a bear-like anchor: philtrum + a U smile); on the chin
    # below the snout it was hidden by the snout from the home camera (slightly above) and read as no expression
    zf = K.surface_z_of(skin, 0.0, 1.312)
    if mouth == "smile" and muzzle:
        # LOOK-2 (the vinyl home crew): a closed SMILE on the short muzzle -- the lip line under the nose, its corners
        # rising into the cheeks, a short philtrum (R2's smile sat on the long snout's front at y 1.316: on the muzzle
        # head that height is the chin)
        xs = np.linspace(-0.150, 0.150, 15)
        tt = xs / 0.150
        ys = 1.392 + 0.060 * tt ** 2 + 0.010 * tt ** 6
        zs = np.array([K.surface_z_of(skin, x, y) for x, y in zip(xs, ys)])
        rr = 0.011 * np.clip(1 - tt ** 2, 0, 1) ** 0.5 + 0.0070
        out["groove"] = K.limb(np.stack([xs, ys, zs + 0.004], 1), rr, k=0.007)
        out["lipline"] = K.limb(np.stack([xs, ys, zs - 0.0035], 1), rr * 0.62, k=0.005)
        out["philtrum"] = K.limb([np.array([0.0, 1.452, K.surface_z_of(skin, 0.0, 1.452) - 0.002]),
                                  np.array([0.0, 1.398, K.surface_z_of(skin, 0.0, 1.398) - 0.002])], [0.0055, 0.0065], k=0.004)
        out["smile_pts"] = np.stack([xs, ys, zs], 1)
        return out
    if mouth == "smile":
        xs = np.linspace(-0.108, 0.108, 13)
        tt = xs / 0.108
        ys = 1.316 + 0.040 * tt ** 2 + 0.006 * tt ** 6
        zs = np.array([K.surface_z_of(skin, x, y) for x, y in zip(xs, ys)])
        rr = 0.010 * np.clip(1 - tt ** 2, 0, 1) ** 0.5 + 0.0065
        out["groove"] = K.limb(np.stack([xs, ys, zs + 0.004], 1), rr, k=0.007)
        out["lipline"] = K.limb(np.stack([xs, ys, zs - 0.0035], 1), rr * 0.62, k=0.005)
        out["philtrum"] = K.limb([np.array([0.0, 1.392, K.surface_z_of(skin, 0.0, 1.392) - 0.002]),
                                  np.array([0.0, 1.320, zf - 0.002])], [0.0055, 0.0065], k=0.004)
        out["smile_pts"] = np.stack([xs, ys, zs], 1)
    else:     # "open" / "grin": the snout's lower front opens in a D (two front teeth, a tongue)
        top = 1.338
        wid = 0.105 if mouth == "grin" else 0.088
        cav = ellipsoid(wid, 0.068, 0.12).translate(0, top - 0.040, zf - 0.03).intersect(S.SDF_arc_top(top, 1.6), k=0.008)
        inner = ellipsoid(wid - 0.006, 0.062, 0.08).translate(0, top - 0.045, zf - 0.11)
        teeth = union(*[box(0.020, 0.022, 0.018, round=0.008).translate(sx * 0.022, top - 0.013, zf - 0.016) for sx in (-1, 1)])
        tongue = ellipsoid(0.055, 0.026, 0.055).translate(0.0, top - 0.080, zf - 0.07)
        out.update(cavity=cav, inner=inner, teeth=teeth, tongue=tongue)
    return out


# ================================================================== kit

HAT_GLOSS = [(0.0, "#FFEE92"), (0.30, "#FFD530"), (0.62, "#F7B800"), (0.86, "#D99600"), (1.0, "#9C6800")]


def hard_hat(center=(0.0, 1.905, 0.03), tilt=-10.0, roll=4.0, lamp=True, goggles=True, s=1.06, gloss_=False):
    """Sunflower hard hat (dome + ridge + brim), a HEADLAMP (iron body, brass bezel, a big glowing lens toward the
    camera), brass goggles resting on the brim (optional), a leather strap. -> [(name, sdf, material, voxel)]"""
    c = np.asarray(center, float)
    Rh = K.rotate_matrix((0, 0, 1), roll) @ K.rotate_matrix((1, 0, 0), tilt)

    def place(q):
        return q.scale(s).transform(Rh).translate(*c) if s != 1.0 else q.transform(Rh).translate(*c)
    dome = ellipsoid(0.425, 0.335, 0.44).intersect(box(1, 0.5, 1).translate(0, 0.5 - 0.005, 0), k=0.02)
    # a low, rounded crown ridge (R1's thin fin read as a sharp crease / tent peak at 2x)
    ridge = ellipsoid(0.437, 0.347, 0.452).intersect(box(0.07, 0.5, 1, round=0.035).translate(0, 0.5, 0)).intersect(
        box(1, 0.5, 1).translate(0, 0.5 + 0.02, 0))
    brim = ellipsoid(0.505, 0.028, 0.56).translate(0, 0.006, 0.07)
    strap = ellipsoid(0.438, 0.345, 0.452).subtract(ellipsoid(0.42, 0.33, 0.435)).intersect(box(1, 0.022, 1).translate(0, 0.075, 0))
    if gloss_:     # LOOK-L fix round 1: a glossy sunflower enamel (the plain one went olive under the cool dome)
        hm = K.skin("d_hatg", HAT_GLOSS, None, rough=0.34, ior=1.34, clearcoat=0.35, cc_rough=0.05)
        bm_ = K.skin("d_brimg", HAT_GLOSS, None, rough=0.36, ior=1.34, clearcoat=0.30, cc_rough=0.06)
    else:
        hm = K.skin("d_hat", D.HAT, None, rough=0.32, ior=1.42)
        bm_ = K.skin("d_brim", D.HAT, None, rough=0.34, ior=1.42)
    out = [("hat", place(union(dome, ridge, k=0.03)), hm, 0.005),
           ("brim", place(brim), bm_, 0.004),
           ("hatStrap", place(strap), K.skin("d_strap", D.LEATHER, None, rough=0.5, ior=1.25), 0.003)]
    if lamp:
        a = math.radians(34)
        lp = np.array([0.0, 0.335 * math.sin(a), 0.44 * math.cos(a)])
        ln = K.unit([0.0, math.sin(a) * 0.35, math.cos(a)])
        Rl = K.frame_from(ln, [1, 0, 0])
        # a flat-fronted cylinder lamp (R1's round-cone cap swallowed the lens: it read as a grey stub)
        body = union(cylinder(0.082, 0.050, round=0.016).transform(Rl).translate(*(lp + ln * 0.030)),
                     box(0.05, 0.03, 0.04, round=0.012).transform(Rl).translate(*(lp - ln * 0.02)), k=0.01)
        bezel = torus(0.078, 0.015).transform(Rl).translate(*(lp + ln * 0.080))
        lens = cylinder(0.068, 0.006).transform(Rl).translate(*(lp + ln * 0.084))
        out += [("lampHousing", place(body), K.skin("d_lampbody", IRON_LUT, None, rough=0.34, ior=1.45), 0.0025),
                ("lampBezel", place(bezel), K.skin("d_lampbezel", D.BRASS_LUT, None, rough=0.26, ior=1.5), 0.002),
                ("lampLens", place(lens), Material("d_lens", "#FFF6D6", roughness=0.08, ior=1.5, emissive="#FFE6A0"), 0.0018)]
    if goggles:
        gz, lenses = [], []
        for sx in (-1, 1):
            gp = np.array([sx * 0.112, 0.11, 0.0])
            gp[2] = 0.44 * math.sqrt(max(0.0, 1 - (gp[0] / 0.425) ** 2 - (gp[1] / 0.335) ** 2)) + 0.030
            gn = K.unit([sx * 0.25, 0.55, 1.0])
            Rg = K.frame_from(gn, [1, 0, 0])
            gz.append(torus(0.064, 0.016).transform(Rg).translate(*gp))
            gz.append(round_cone(tuple(gp - gn * 0.03), tuple(gp + gn * 0.008), 0.076, 0.072).subtract(
                cylinder(0.058, 0.2).transform(Rg).translate(*gp)))
            lenses.append(cylinder(0.056, 0.006).transform(Rg).translate(*(gp + gn * 0.004)))
        bz = 0.44 * math.sqrt(max(0.0, 1 - (0.11 / 0.335) ** 2)) + 0.045
        bridge = capsule((-0.045, 0.11, bz), (0.045, 0.11, bz), 0.012)
        out += [("goggles", place(union(*gz, bridge)), K.skin("d_goggle", D.BRASS_LUT, None, rough=0.26, ior=1.5), 0.0025),
                ("goggleLenses", place(union(*lenses)), glass("d_glens", "#A9E9F2", opacity=0.55), 0.002)]
    return out


def goggles_down(hx, head_skin, gk=1.0, elift=0.0, eyes_xy=None, dz=0.035):
    """Brass goggles pulled DOWN over the eyes (the map reader): two rims round the eye sockets, glass lenses, a bridge
    over the snout's root, a leather strap round the head. Head space -> world via hx. -> (rims+lenses, strap).
    LOOK-2 (the vinyl home crew): gk scales the rims / lenses round the bigger eyes, elift / eyes_xy follow the lifted
    eye centres, dz the stand-off (the defaults make R2's goggles exactly)."""
    rims, lenses = [], []
    for i, (ex, ey) in enumerate(eyes_xy if eyes_xy is not None else EYES):
        sx = -1 if i == 0 else 1
        ez = K.surface_z_of(head_skin, ex, ey) + dz
        gp = np.array([ex, ey + 0.005, ez])
        gn = K.unit([sx * 0.18, 0.05, 1.0])
        Rg = K.frame_from(gn, [1, 0, 0])
        rims.append(torus(0.118 * gk, 0.022 * (1 + 0.4 * (gk - 1))).transform(Rg).translate(*gp))
        rims.append(round_cone(tuple(gp - gn * 0.05), tuple(gp + gn * 0.004), 0.132 * gk, 0.126 * gk).subtract(
            cylinder(0.106 * gk, 0.3).transform(Rg).translate(*gp)))
        lenses.append(cylinder(0.106 * gk, 0.006).transform(Rg).translate(*(gp + gn * 0.002)))
    by_ = 1.715 + elift
    zb = K.surface_z_of(head_skin, 0.0, by_) + 0.05 + (dz - 0.035)
    bridge = capsule((-0.075 * gk, by_, zb), (0.075 * gk, by_, zb), 0.018)
    band = ellipsoid(HEAD_R[0] + 0.022, 0.05, HEAD_R[2] + 0.022).translate(HEAD_C[0], 1.72, HEAD_C[2]).subtract(
        ellipsoid(HEAD_R[0] + 0.004, 0.2, HEAD_R[2] + 0.004).translate(HEAD_C[0], 1.72, HEAD_C[2])).intersect(
        box(1, 0.021, 1).translate(0, 1.72, 0)).intersect(box(1, 0.3, 0.5).translate(0, 1.72, HEAD_C[2] - 0.1))
    brass = K.skin("d_goggleD", D.BRASS_LUT, None, rough=0.26, ior=1.5)
    return ([("gogglesD", hx.sdf(union(*rims, bridge)), brass, 0.0025),
             ("goggleLensesD", hx.sdf(union(*lenses)), glass("d_glensD", "#B8EEF6", opacity=0.42), 0.002)],
            [("goggleStrapD", hx.sdf(band), K.skin("d_strapD", D.LEATHER, None, rough=0.5, ior=1.25), 0.003)])


def shovel(h0, h1, blade_c, blade_up, blade_face, size=1.0, tag=""):
    """A shovel: a wood-grain handle h0 (socket end) -> h1 (grip end) + a D-grip, an iron socket (ferrule) with brass
    rivets, a slightly dished PAINTED STEEL blade with bright worn edges. -> [(name, sdf, material, voxel)]"""
    h0, h1 = np.asarray(h0, float), np.asarray(h1, float)
    ax = K.unit(h1 - h0)
    handle = capsule(tuple(h0), tuple(h1), 0.034 * size)
    gcen = h1 + ax * 0.06 * size
    side = K.unit(np.cross(ax, blade_face))
    grip = union(capsule(tuple(gcen - side * 0.075 * size), tuple(gcen + side * 0.075 * size), 0.028 * size),
                 capsule(tuple(h1 - side * 0.045 * size), tuple(gcen - side * 0.07 * size), 0.020 * size),
                 capsule(tuple(h1 + side * 0.045 * size), tuple(gcen + side * 0.07 * size), 0.020 * size), k=0.01)
    ferrule = round_cone(tuple(h0 - ax * 0.07 * size), tuple(h0 + ax * 0.07 * size), 0.052 * size, 0.040 * size)
    rivets = union(*[sphere(0.012 * size).translate(*(h0 + ax * dz * size + np.asarray(blade_face) * 0.046 * size))
                     for dz in (-0.03, 0.03)])
    spade2 = polygon2(fillet_points([(-0.15, 0.20), (0.15, 0.20), (0.16, -0.02), (0.0, -0.21), (-0.16, -0.02)],
                                    [0.03, 0.03, 0.08, 0.05, 0.08], n_arc=6))
    blade = extrude(spade2, 0.012, round=0.010)
    blade = blade.subtract(ellipsoid(0.5, 0.5, 0.5).translate(0, 0, 0.505), k=0.004)   # a shallow dish on the front
    Rb = K.frame_from(blade_up, blade_face)
    blade = blade.scale(size).transform(Rb).translate(*np.asarray(blade_c, float))
    return [(f"shovelHandle{tag}", union(handle, grip, k=0.01), K.skin(f"d_wood_s{tag}", D.WOOD0, D.WOOD1,
                                                                    vfn=D.grain_vfn(70, 1), rough=0.55, ior=1.25), 0.004),
            (f"shovelBlade{tag}", blade, D.painted_metal(f"d_blade{tag}", STEEL_PAINT, STEEL_WORN, blade, rough=0.34, width=0.012), 0.003),
            (f"shovelIron{tag}", ferrule, K.skin(f"d_ferrule{tag}", IRON_LUT, None, rough=0.36, ior=1.45), 0.003),
            (f"shovelRivets{tag}", rivets, K.skin(f"d_rivet{tag}", D.BRASS_LUT, None, rough=0.28, ior=1.5), 0.002)]


BLUEPRINT_PAPER = [(0.0, "#7CC0F0"), (0.45, "#4A93D8"), (0.8, "#3070B4"), (1.0, "#1E4C84")]
BLUEPRINT_PAPER1 = [(0.0, "#88C8F2"), (0.45, "#5A9EDC"), (0.8, "#3A78B8"), (1.0, "#245088")]


def tunnel_map(center, up, face, w=0.62, h=0.46, tag="", style="parchment"):
    """A tunnel MAP: a slightly curved parchment sheet between two wooden rollers, inked with a web of tunnels, an
    arrow out and a red X. up = the rollers' perpendicular (sheet up), face = the inked side."""
    c = np.asarray(center, float)
    R = K.frame_from(up, face)
    sheet = box(w / 2, h / 2, 0.006, round=0.004)
    # a gentle curl (the sheet bows away from the viewer)
    rollers = union(*[capsule((-w / 2 - 0.035, yy, 0.0), (w / 2 + 0.035, yy, 0.0), 0.028) for yy in (h / 2 + 0.01, -h / 2 - 0.01)])
    knobs = union(*[sphere(0.034).translate(sx * (w / 2 + 0.05), yy, 0.0) for sx in (-1, 1) for yy in (h / 2 + 0.01, -h / 2 - 0.01)])
    ink = []
    segs = [((-0.24, 0.16), (0.10, 0.16)), ((0.10, 0.16), (0.10, 0.02)), ((-0.24, 0.16), (-0.24, -0.16)),
            ((-0.24, -0.16), (-0.02, -0.16)), ((-0.12, 0.04), (-0.12, -0.06)), ((-0.12, 0.04), (0.0, 0.04)),
            ((0.10, 0.02), (0.22, 0.02)), ((0.22, 0.02), (0.22, -0.12))]
    for (x0, y0), (x1, y1) in segs:
        ink.append(capsule((x0, y0, 0.007), (x1, y1, 0.007), 0.012))
    arrow = extrude(D.arrow2d(0.12, 0.10, 0.045, 0.06), 0.003, round=0.002).transform(K.rotate_matrix((0, 0, 1), -90)).translate(0.27, -0.12, 0.009)
    xmark = union(capsule((-0.035, -0.035, 0.008), (0.035, 0.035, 0.008), 0.011),
                  capsule((-0.035, 0.035, 0.008), (0.035, -0.035, 0.008), 0.011)).translate(-0.12, -0.02, 0.0)

    def pl(q):
        return q.transform(R).translate(*c)
    if style == "blueprint":
        # LOOK-2 fix round (the copy judge: "notepad and pencil" = their right worker's prop idea): the same held sheet
        # as a mine BLUEPRINT -- blue paper, white tunnel lines, a tangerine exit arrow (no red X)
        return [(f"map{tag}", pl(sheet), K.skin(f"d_bprint{tag}", BLUEPRINT_PAPER, BLUEPRINT_PAPER1, vfn=D.canvas_vfn(24, 4),
                                                rough=0.74, ior=1.2), 0.003),
                (f"mapRollers{tag}", pl(union(rollers, knobs, k=0.01)), K.skin(f"d_roll{tag}", D.WOOD0, D.WOOD1,
                                                                               vfn=D.grain_vfn(60, 0), rough=0.5, ior=1.25), 0.003),
                (f"mapInk{tag}", pl(union(*ink)), Material(f"d_bink{tag}", "#F4FAFF", roughness=0.6, ior=1.3,
                                                          emissive="#3A4A5A"), 0.0018),
                (f"mapMark{tag}", pl(arrow), satin(f"d_bmark{tag}", "#FF8F1F", rough=0.5), 0.0018)]
    return [(f"map{tag}", pl(sheet), K.skin(f"d_parch{tag}", D.PARCHMENT, D.PARCHMENT1, vfn=D.canvas_vfn(24, 4), rough=0.78, ior=1.2), 0.003),
            (f"mapRollers{tag}", pl(union(rollers, knobs, k=0.01)), K.skin(f"d_roll{tag}", D.WOOD0, D.WOOD1, vfn=D.grain_vfn(60, 0), rough=0.5, ior=1.25), 0.003),
            (f"mapInk{tag}", pl(union(*ink)), satin(f"d_ink{tag}", D.INK, rough=0.7), 0.0018),
            (f"mapMark{tag}", pl(union(arrow, xmark)), satin(f"d_mark{tag}", TAG_RED, rough=0.6), 0.0018)]


def pencil(tip, direction, length=0.34, tag=""):
    """A flat carpenter's pencil (octagonal, tangerine paint), a sharpened wood cone + graphite tip at `tip`."""
    tip = np.asarray(tip, float)
    d = K.unit(direction)                      # from the tip toward the back end
    back = tip + d * length
    cone0 = tip + d * 0.07
    body = capsule(tuple(cone0), tuple(back), 0.024).intersect(
        box(0.024, 1.0, 0.017, round=0.006).transform(K.frame_from(d, [0.0, 0.0, 1.0])).translate(*((cone0 + back) / 2)))
    wood = round_cone(tuple(tip + d * 0.012), tuple(cone0), 0.008, 0.022)
    lead = round_cone(tuple(tip), tuple(tip + d * 0.02), 0.005, 0.009)
    return [(f"pencil{tag}", body, K.skin(f"d_pencil{tag}", PENCIL, None, rough=0.4, ior=1.35), 0.002),
            (f"pencilWood{tag}", wood, K.skin(f"d_pencilwood{tag}", D.WOOD0, None, rough=0.6, ior=1.25), 0.0018),
            (f"pencilLead{tag}", lead, satin(f"d_lead{tag}", "#2A2A2E", rough=0.35), 0.0015)]


# ================================================================== the Digger

BASE = dict(girth=1.0, height=1.0, head_s=1.0, head=dict(yaw=0.0, roll=0.0, nod=0.0), mouth="smile", eyes="open",
            look=(0.10, 0.0), brows="friendly", lids_open=0.93, hat=dict(lamp=True, goggles=True, tilt=-10.0, roll=4.0),
            goggles_down=False, vest=True, belt=True, trowel=True, fur="mint", legs=None,
            arms=dict(L=dict(el=(-0.60, 0.92, 0.10), wr=(-0.66, 0.70, 0.22), d=(-0.10, -1.0, 0.25), palm=(0.9, 0.0, 0.3),
                             curl=22.0, spread=22.0),
                      R=dict(el=(0.60, 0.92, 0.10), wr=(0.66, 0.70, 0.22), d=(0.10, -1.0, 0.25), palm=(-0.9, 0.0, 0.3),
                             curl=22.0, spread=22.0)),
            props=())


def spec_with(base, **kw):
    s = dict(base)
    for k, v in kw.items():
        if k == "arms" and v is not None:
            s["arms"] = dict(s["arms"], **v)
        elif v is not None:
            s[k] = v
    return s


BODY_KIT = {"vest", "piping", "zipper", "stripe", "belt", "buckle", "trowel", "trowelHandle", "hat", "brim", "hatStrap", "scarf",
            "lampHousing", "lampBezel", "lampLens", "goggles", "goggleLenses", "goggleStrapD"}
BODY_PARTS = ({"skin", "browridge", "browfur", "nose", "innerEars", "soles", "toeClaws", "lipline", "philtrum", "mouth",
               "teeth", "tongue", "boots", "bootRims", "bootSoles", "bootLaces", "trousers", "trouserPockets"} | BODY_KIT
              | D.band_names("fur", FUR_BANDS))
EYE_PARTS = {"eyes", "irises", "pupils", "glints", "lids", "crease", "lidfur"}
GOGGLE_PARTS = {"gogglesD", "goggleLensesD"}
ARM_L = {"armL", "furArmL", "clawsL", "padsL", "sleeveL", "cuffL", "pawL", "gloveRimsL", "gloveSeamsL", "tipsL", "glovePatchL"}
ARM_R = {"armR", "furArmR", "clawsR", "padsR", "sleeveR", "cuffR", "pawR", "gloveRimsR", "gloveSeamsR", "tipsR", "glovePatchR"}


def _akey(A):
    return tuple(sorted((k, tuple(np.round(np.asarray(v, float).ravel(), 4)) if not isinstance(v, str) else v)
                        for k, v in A.items()))


def digger(spec, only=None, view_pose=None, n_strands=140000, seed=11, key="dig", extra_parts=None):
    """All parts of one Digger (feet on y 0, facing +Z, before ui3d's view pose). spec: BASE + overrides.
    props: [(name, sdf, material, voxel), ...] already in world space (held props join their arm's layer via the rig's
    part sets). extra_parts(ctx) -> more such tuples, computed from the pose (ctx: paw centres, head xf).
    LOOK-L keys (optional; the defaults mesh exactly the fur Digger of R2): finish "vinyl" (no fur: the glossy vinyl
    coat + sleeves, wrist cuffs, work boots), eye_scale / eye_lift (bigger glossy eyes), hat_lift, mouth "laugh",
    lean / twist / body_roll (BodyXf: everything above the legs turns about the hips; arm points are authored in the
    UNLEANED body space), legs with knees (legs_sdf)."""
    P = spec
    vinyl = P.get("finish", "fur") == "vinyl"
    es, elift = P.get("eye_scale", 1.0), P.get("eye_lift", 0.0)
    vp = view_pose or dict(yaw=0, pitch=6)
    view = S._view_dir(dict(yaw=vp.get("yaw", 0), pitch=vp.get("pitch", 0)))
    g, hgt, hs = P["girth"], P["height"], P["head_s"]
    BX = BodyXf(P.get("lean", 0.0), P.get("twist", 0.0), P.get("body_roll", 0.0))
    hx0 = HeadXf(lift=(hgt - 1.0) * 1.25, **P["head"])        # body space (the kit's neck cut-outs)
    hx = BX.head(hx0)                                          # world
    muzzle = P.get("snout", "long") == "muzzle"
    sb = P.get("snout_back", 0.0) if muzzle else 0.0
    nose_c = (NOSE_MUZZLE - np.array([0.0, 0.0, sb])) if muzzle else NOSE_C
    hl = head_skin_local(hs, snout="muzzle" if muzzle else "long", **({"snout_back": sb} if sb else {}))
    fkw = {} if (es == 1.0 and elift == 0.0) else dict(eye_scale=es, eye_lift=elift)
    if muzzle:
        fkw["muzzle"] = True
    for k_ in ("eye_div", "lash", "laugh", "low_lid", "lid_gap", "teeth_k", "snout_back", "iris_k", "half_lid"):   # LOOK-L face keys (absent = the old face)
        if k_ in P:
            fkw[k_] = P[k_]
    F = digger_face(hl["skin"], mouth=P["mouth"], look=P["look"], eyes=P["eyes"], brows=P["brows"],
                    lids_open=P["lids_open"], **fkw)
    head_skin0 = hl["skin"] if "jaw" not in F else union(hl["skin"], F["jaw"], k=0.07)
    head_local = head_skin0.subtract(F["sockets"].offset(-0.012), k=0.014)
    if "groove" in F:
        head_local = head_local.subtract(F["groove"], k=0.008)
    if "cavity" in F:
        head_local = head_local.subtract(F["cavity"], k=0.015)
    inner_ears_l = union(*[ellipsoid(0.066, 0.075, 0.03).transform(K.frame_from([sx * 0.25, 1.0, 0.1], [sx * 0.62, 0.1, 0.78]))
                           .translate(sx * 0.430 * hs + sx * 0.014, 1.705, -0.03 + 0.021) for sx in (-1, 1)])
    head_local = head_local.subtract(inner_ears_l.offset(-0.004), k=0.01)
    torso = body_space(g, hgt)
    legs, soles_l, feet = legs_sdf(P.get("legs"), g)
    skin = union(BX.sdf(torso), hx.sdf(head_local), k=0.10)
    skin = union(skin, *legs, k=0.06)
    # ---- kit: vest (shell with arm holes + V neck + binding + zip + stripe), belt, buckle, trowel (body space)
    shoulders = [np.array([sx * 0.40 * g, 1.20 * hgt, 0.0]) for sx in (-1, 1)]
    VB, VT = 0.80 * hgt, 1.43 * hgt
    kit = []
    vest = piping = None
    if P.get("vest", True):
        vest = torso.offset(0.060).subtract(torso.offset(0.034)).intersect(D.slab_y(VB, VT), k=0.008)
        for sh in shoulders:
            vest = vest.subtract(sphere(0.215).translate(*sh), k=0.02)
        vee = extrude(polygon2([(-0.19, 1.50 * hgt), (0.19, 1.50 * hgt), (0.0, 1.03 * hgt)]), 0.6).translate(0, 0, 0.85)
        vest = vest.subtract(vee, k=0.02).subtract(hx0.sdf(ellipsoid(*(np.array(HEAD_R) * hs)).translate(*HEAD_C)).offset(0.03), k=0.02)
        band = union(D.slab_y(VB - 0.004, VB + 0.022), vee.offset(0.024).subtract(vee),
                     *[sphere(0.240).translate(*sh).subtract(sphere(0.214).translate(*sh)) for sh in shoulders])
        piping = torso.offset(0.068).subtract(torso.offset(0.030)).intersect(D.slab_y(VB - 0.004, VT)).intersect(band).subtract(
            vee.offset(0.002)).subtract(union(*[sphere(0.213).translate(*sh) for sh in shoulders]))
        zipper = torso.offset(0.066).subtract(torso.offset(0.040)).intersect(box(0.010, (1.04 * hgt - VB) / 2, 1.0).translate(0, (1.04 * hgt + VB) / 2, 0.8))
        zz = K.surface_z_of(torso.offset(0.066), 0.0, 1.00 * hgt)
        pull = box(0.018, 0.034, 0.008, round=0.006).translate(0.0, 0.985 * hgt, zz + 0.006)
        stripe = torso.offset(0.068).subtract(torso.offset(0.045)).intersect(D.slab_y(0.90 * hgt, 0.97 * hgt))
        stm = Material("d_stripe", "#FFF4DA", roughness=0.30, ior=1.35, emissive="#2C2A22", texture=K.lut(D.STRIPE), texture_size=64)
        stm.__dict__["_vfn"] = None
        kit += [("vest", vest, K.skin("d_vest", D.VEST, None, rough=0.78, ior=1.18), 0.005),
                ("piping", piping, K.skin("d_piping", [(0.0, "#D9681A"), (0.5, "#B84E0A"), (1.0, "#7A3004")], None, rough=0.6, ior=1.2), 0.003),
                ("zipper", union(zipper, pull), metal("d_zip", "#C9CED4", rough=0.3), 0.002),
                ("stripe", stripe, stm, 0.004)]
    if P.get("scarf"):       # LOOK-L fix round 1: a knotted neckerchief in the V of the vest (a cast variant)
        sc = SCARF[P["scarf"]]
        nk = torso.offset(0.075).subtract(torso.offset(0.028)).intersect(D.slab_y(1.34 * hgt, 1.46 * hgt), k=0.01)
        nk = nk.subtract(hx0.sdf(ellipsoid(*(np.array(HEAD_R) * hs)).translate(*HEAD_C)).offset(0.012), k=0.01)
        zk = K.surface_z_of(torso.offset(0.075), 0.0, 1.30 * hgt)
        knot = ellipsoid(0.070, 0.058, 0.050).translate(0.0, 1.30 * hgt, zk + 0.02)
        tails = union(round_cone((-0.02, 1.27 * hgt, zk + 0.02), (-0.075, 1.12 * hgt, zk + 0.035), 0.045, 0.030),
                      round_cone((0.02, 1.27 * hgt, zk + 0.02), (0.060, 1.13 * hgt, zk + 0.040), 0.042, 0.028), k=0.02)
        kit += [("scarf", union(nk, knot, tails, k=0.02), K.skin(f"d_scarf{P['scarf']}", sc, None, vfn=D.canvas_vfn(40, 5),
                                                                  rough=0.72, ior=1.2), 0.004)]
    belt = None
    if P.get("belt", True):
        belt = torso.offset(0.058).subtract(torso.offset(0.030)).intersect(D.slab_y(0.47 * hgt, 0.58 * hgt), k=0.006)
        bz = K.surface_z_of(torso.offset(0.058), 0.0, 0.525 * hgt)
        buckle = box(0.072, 0.058, 0.016, round=0.012).subtract(box(0.040, 0.030, 0.05, round=0.008)).translate(0.0, 0.525 * hgt, bz + 0.006)
        kit += [("belt", belt, K.skin("d_leather", D.LEATHER, None, rough=0.52, ior=1.25), 0.004),
                ("buckle", buckle, K.skin("d_buckle", D.BRASS_LUT, None, rough=0.28, ior=1.5), 0.003)]
        if P.get("trowel"):
            tx, ty = -0.47 * g, 0.42 * hgt
            tz = K.surface_z_of(torso.offset(0.07), tx, ty + 0.10) + 0.03
            leaf = polygon2(fillet_points([(0.0, 0.0), (0.075, -0.07), (0.05, -0.20), (0.0, -0.27), (-0.05, -0.20), (-0.075, -0.07)],
                                          [0.02, 0.03, 0.03, 0.02, 0.03, 0.03], n_arc=5))
            Rt_ = K.frame_from([-0.30, 1.0, 0.12], [-0.35, 0.0, 1.0])
            blade = extrude(leaf, 0.008, round=0.006).transform(Rt_).translate(tx - 0.02, ty, tz)
            handle = capsule((tx - 0.02, ty + 0.01, tz), (tx + 0.02, ty + 0.16, tz - 0.01), 0.026)
            kit += [("trowel", blade, D.painted_metal("d_trowel", STEEL_PAINT, STEEL_WORN, blade, rough=0.32, width=0.008), 0.0025),
                    ("trowelHandle", handle, K.skin("d_wood_t", D.WOOD0, D.WOOD1, vfn=D.grain_vfn(60, 1), rough=0.55, ior=1.25), 0.003)]
    if BX.on:                                                  # the kit follows the torso's lean
        kit = [(n_, BX.sdf(s_), m_, v_) for n_, s_, m_, v_ in kit]
        vest = BX.sdf(vest) if vest is not None else None
        piping = BX.sdf(piping) if piping is not None else None
        belt = BX.sdf(belt) if belt is not None else None
    if P.get("mouth_clean") and "cavity" in F:
        # LOOK-2 round 2 (v6; the finish judge on v5: "two orange-brown slivers show inside the mouth at its right corner;
        # the vest collar or zipper pokes through the open mouth cavity"): the V-neck's top edges reach into the laughing
        # jaw's corners -- cut the open mouth (+ a margin) out of every garment part, so nothing but the mouth's own
        # dark inside, teeth and tongue can show through it
        mcut = hx.sdf(F["cavity"]).offset(0.035)
        kit = [(n_, s_.subtract(mcut, k=0.01) if n_ in ("vest", "piping", "zipper", "stripe", "scarf") else s_, m_, v_)
               for n_, s_, m_, v_ in kit]
    # ---- hat (head space -> world) / goggles down
    hat_parts = []
    if P.get("hat"):
        H = P["hat"]
        for n_, s_, m_, v_ in hard_hat(center=(0.0, 1.905 + (hs - 1) * 0.42 + P.get("hat_lift", 0.0), 0.03), tilt=H.get("tilt", -10.0),
                                       roll=H.get("roll", 4.0), lamp=H.get("lamp", True), goggles=H.get("goggles", True),
                                       **({"gloss_": True} if P.get("hat_gloss") else {})):
            hat_parts.append((n_, hx.sdf(s_), m_, v_))
        if P.get("brim_goggles_layer"):
            # LOOK-2 fix round (the copy judge: the map reader's goggles-down read as big round spectacles = their right
            # worker's glasses): the goggles sit UP on the hard hat, and they are the rig's "goggles" layer (same name)
            hat_parts = [({"goggles": "gogglesD", "goggleLenses": "goggleLensesD"}.get(n_, n_), s_, m_, v_)
                         for n_, s_, m_, v_ in hat_parts]
    gog_parts, gog_strap = [], []
    if P.get("goggles_down"):
        if P.get("goggles_fit"):       # LOOK-2 (the vinyl home map reader): the goggles sized to the bigger eyes
            gf = P["goggles_fit"]
            gog_parts, gog_strap = goggles_down(hx, hl["skin"], gk=gf.get("gk", 1.0), elift=elift, eyes_xy=eyes_of(es, elift),
                                                dz=gf.get("dz", 0.035))
        else:
            gog_parts, gog_strap = goggles_down(hx, hl["skin"])
    # ---- nose, inner ears, soles, toe claws (world)
    nose = hx.sdf(ellipsoid(0.112, 0.090, 0.090).translate(*nose_c))
    inner_ears = hx.sdf(inner_ears_l)
    soles = union(*soles_l)
    toe_claws = []
    for foot_c, Rf, _h, _k, _a in feet:
        for j in (-1, 0, 1):
            b0 = foot_c + Rf[:, 1] * (0.20 - abs(j) * 0.02) + Rf[:, 0] * j * 0.075 - Rf[:, 2] * 0.03
            toe_claws.append(round_cone(tuple(b0), tuple(b0 + Rf[:, 1] * 0.055 - Rf[:, 2] * 0.035 + Rf[:, 0] * j * 0.01), 0.024, 0.009))
    toe_claws = union(*toe_claws)
    # ---- arms + spade paws (arm points in body space -> the lean)
    arms, claws, pads, paw_c, sleeves, cuffs, paws = {}, {}, {}, {}, {}, {}, {}
    gloves = {}
    for tag, sh in (("L", shoulders[0]), ("R", shoulders[1])):
        A = P["arms"][tag]
        el, wr = BX.p(A["el"]), BX.p(A["wr"])
        dd, pn = BX.n(K.unit(A["d"])), BX.n(K.unit(A["palm"]))
        shw = BX.p(sh)
        defined = bool(P.get("paws") in ("defined", "mitt", "glove"))
        if P.get("paws") == "glove":      # LOOK-2 round 2 (v6): the fingerless work glove (thumb on the medial side)
            ex_ = K.frame_from(dd, pn)[:, 0]
            med = BX.n(np.array([1.0 if tag == "L" else -1.0, 0.0, 0.0]))
            th = A.get("thumb") or (ex_ if float(np.dot(ex_, med)) >= 0 else -ex_)
            gw = glove_paw(wr, dd, pn, r=0.155 * A.get("paw_s", 1.0), curl=A.get("curl", 15.0), spread=A.get("spread", 24.0),
                           claw_bend=min(A.get("claw_bend", 30.0), 35.0), thumb=th, thumb_curl=A.get("thumb_curl"))
            gloves[tag] = gw
            pw = dict(paw=gw["glove"], claws=gw["claws"], pads=None)
        elif P.get("paws") == "mitt":       # LOOK-2: the chunky mitt (A["paw_s"] scales one paw, e.g. the hero's reach)
            pw = mitt_paw(wr, dd, pn, r=0.155 * A.get("paw_s", 1.0), curl=A.get("curl", 15.0), spread=A.get("spread", 24.0),
                          claw_bend=min(A.get("claw_bend", 30.0), 35.0))
        else:
            pw = spade_paw(wr, dd, pn, r=0.155, curl=A.get("curl", 15.0), spread=A.get("spread", 24.0),
                           claw_len=A.get("claw_len", 0.075), claw_bend=A.get("claw_bend", 40.0), **({"defined": True} if defined else {}))
        if defined:     # LOOK-L fix round 1: the paw is its own satin part (less wet than the vinyl arm), met at the cuff
            arms[tag] = K.limb([shw, el, wr + dd * 0.02], [0.14, 0.13, 0.12], k=0.06)
            paws[tag] = pw["paw"]
        else:
            arms[tag] = union(K.limb([shw, el, wr], [0.14, 0.13, 0.12], k=0.06), pw["paw"], k=0.05)
        claws[tag], pads[tag] = pw["claws"], pw["pads"]
        paw_c[tag] = wr + dd * 0.155 * 0.95
        if vinyl:
            ax_u = K.unit(el - shw)
            mid = shw + (el - shw) * 0.64
            sleeves[tag] = union(sphere(0.192).translate(*shw), round_cone(tuple(shw), tuple(mid), 0.184, 0.170), k=0.03)
            hem = torus(0.170, 0.026).transform(K.frame_from(ax_u, [1.0, 0.0, 0.0])).translate(*mid)
            sleeves[tag] = union(sleeves[tag], hem, k=0.012)
            ck = 1.0 if P.get("paws") != "mitt" else max(1.0, 0.5 + 0.5 * A.get("paw_s", 1.0))   # LOOK-2: a bigger mitt, a wider cuff
            cuffs[tag] = union(round_cone(tuple(wr - dd * 0.075), tuple(wr + dd * 0.012), 0.146 * ck, 0.143 * ck),
                               torus(0.142 * ck, 0.014).transform(K.frame_from(dd, [1.0, 0.0, 0.0])).translate(*(wr - dd * 0.032)), k=0.006)
            if tag in gloves:          # v6: the glove's own flared gauntlet is the cuff
                cuffs[tag] = gloves[tag]["cuff"]
    # ---- props (world) + pose-dependent extras
    props = list(P.get("props", ()))
    if extra_parts is not None:
        props += list(extra_parts(dict(paw=paw_c, hx=hx, spec=P, bx=BX)))
    # ---- assemble the solid parts
    if vinyl:
        def belly(v):
            return _belly_weight(np.asarray(v, float), hx, g, hgt, BX, **({} if "belly_face" not in P else {"face": P["belly_face"]}))
        tint = P.get("skin_tint", "a")
        vm3 = P.get("vmat", 1) in (3, 4)          # (vmat 4 = vmat 3's ladders + glow with the broader sheen coat)
        if vm3 and tint in ("a", "a2"):      # LOOK-2: the warmer "3" ladders with the satin coat
            tint = "a3"
        elif vm3 and tint in ("b", "b2"):
            tint = "b3"
        vsk, vbl = {"a": (VINYL_SKIN, VINYL_BELLY), "b": (VINYL_SKIN_B, VINYL_BELLY_B), "a2": (VINYL_SKIN2, VINYL_BELLY2),
                    "b2": (VINYL_SKIN_B2, VINYL_BELLY_B2), "a3": (VINYL_SKIN3, VINYL_BELLY3),
                    "b3": (VINYL_SKIN_B3, VINYL_BELLY_B3)}[tint]
        tg = "" if tint == "a" else tint
        VM = VINYL_MATS[P.get("vmat", 1)]
        tg += "" if P.get("vmat", 1) == 1 else f"m{P['vmat']}"
        glow = VINYL_GLOW3 if vm3 else VINYL_GLOW
        skin_m = K.skin(f"d_vskin{tg}", vsk, vbl, vfn=belly, emissive=glow, **VM)
        arm_ms = {t: K.skin(f"d_vskin{tg}{t}", vsk, None, emissive=glow, **VM) for t in ("L", "R")}
        browskin = K.skin("d_vbrow", VINYL_BROW, None, rough=0.36, ior=1.40, clearcoat=0.40, cc_rough=0.12)
        lid_m = K.skin(f"d_vlid{tg}", vsk, None, emissive=glow, **VM)
        if vm3:          # LOOK-2: no specular on the lid caps (the judge: "the mint lid caps carry their own hot spec")
            lid_m = K.skin(f"d_vlid{tg}", vsk, None, emissive=glow, rough=0.70, ior=1.22)
        crease_m = satin("d_lash", LASH, rough=0.5)
        if P.get("sclera") == "soft":
            # LOOK-2 round 2 (v6; the finish judge on v5: "every eye white clips to paper white (median L* 99-100 vs the
            # original's 90-93) ... FIX: sclera albedo ~0.82-0.85 with a soft upper-lid shadow and an occlusion falloff
            # toward the corners, so only the glints reach 100"): an off-white LUT (no emissive lift), the v term =
            # the upper lid's shadow band + the rim falloff (head space, per eye)
            rx_, ry_ = EYE_R[0] * es, EYE_R[1] * es
            rz_ = EYE_R[2] * (1.0 + 0.55 * (es - 1.0))
            ecs = [(x_, y_, K.surface_z_of(hl["skin"], x_, y_) - rz_ * 0.30) for x_, y_ in eyes_of(es, elift)]
            eye_m = K.skin(f"d_veye6{tg}", SCLERA6, SCLERA6_SH, vfn=_sclera_vfn(hx, ecs, rx_, ry_), rough=0.16, ior=1.40,
                           clearcoat=0.30, cc_rough=0.07)
        elif P.get("sclera") == "clean":     # LOOK-L fix round 1: a neutral cool white (the warm key made the old one cream)
            eye_m = Material("d_veye2", EYE_WHITE_V2, roughness=0.10, ior=1.45, clearcoat=0.6, clearcoat_roughness=0.04,
                             emissive="#5C6064")
        else:
            eye_m = Material("d_veye", EYE_WHITE_V, roughness=0.10, ior=1.45, clearcoat=0.6, clearcoat_roughness=0.04,
                             emissive="#43423E")
        nose_m = K.skin("d_vnose", NOSE, None, rough=0.24, ior=1.40, clearcoat=0.65, cc_rough=0.08)
        ear_m = K.skin("d_vinnerear", INNER_EAR, None, rough=0.36, ior=1.35, clearcoat=0.3, cc_rough=0.14)
    else:
        skin_m = K.skin("d_skin", DIG_SKIN, None, rough=0.74, ior=1.2)
        arm_ms = {t: K.skin(f"d_skin{t}", DIG_SKIN, None, rough=0.74, ior=1.2) for t in ("L", "R")}
        browskin = K.skin("d_browskin", DIG_BROW_SKIN, None, rough=0.7, ior=1.2)
        lid_m = K.skin("d_lidskin", DIG_SKIN, None, rough=0.74, ior=1.2)
        crease_m = satin("d_crease", "#0B3A31", rough=0.6)
        eye_m = gloss("d_eye", EYE_WHITE, rough=0.18, ior=1.45)
        nose_m = K.skin("d_nose", NOSE, None, rough=0.26, ior=1.35, clearcoat=0.35, cc_rough=0.2)
        ear_m = K.skin("d_innerear", INNER_EAR, None, rough=0.6, ior=1.2)
    parts = [Part("skin", skin, skin_m, voxel=0.007 if not vinyl else 0.0055),
             Part("armL", arms["L"], arm_ms["L"], voxel=0.005 if not vinyl else 0.0042),
             Part("armR", arms["R"], arm_ms["R"], voxel=0.005 if not vinyl else 0.0042),
             Part("browridge", hx.sdf(F["brows"]), browskin, voxel=0.003),
             Part("lids", hx.sdf(F["lids"]), lid_m, voxel=0.003),
             *([Part("crease", hx.sdf(F["crease"]), crease_m, voxel=0.002)] if F.get("crease") is not None else []),
             Part("eyes", hx.sdf(F["eyes"]), eye_m, voxel=0.003),
             Part("irises", hx.sdf(F["irises"]), gloss("d_iris", IRIS_DIG, rough=0.2, ior=1.45), voxel=0.002),
             Part("pupils", hx.sdf(F["pupils"]), gloss("d_pupil", PUPIL, rough=0.15, ior=1.5), voxel=0.002),
             Part("glints", hx.sdf(F["glints"]), Material("d_glint", "#FFFFFF", roughness=0.3, emissive="#FFFFFF"), voxel=0.0016),
             Part("nose", nose, nose_m, voxel=0.003),
             Part("innerEars", inner_ears, ear_m, voxel=0.003),
             Part("padsL", pads["L"], K.skin("d_padsL", PAD, None, rough=0.55, ior=1.25), voxel=0.003),
             Part("padsR", pads["R"], K.skin("d_padsR", PAD, None, rough=0.55, ior=1.25), voxel=0.003),
             Part("clawsL", claws["L"], K.skin("d_clawsL", CLAW, None, rough=0.34, ior=1.4), voxel=0.0022),
             Part("clawsR", claws["R"], K.skin("d_clawsR", CLAW, None, rough=0.34, ior=1.4), voxel=0.0022)]
    parts = [p_ for p_ in parts if p_.sdf is not None]      # (v6 gloves: no bare pads)
    if gloves and vinyl:     # LOOK-2 round 2 (v6): the fingerless work gloves -- matte leather, rolled finger ends, thread seams
        for t in ("L", "R"):
            gw = gloves[t]
            parts += [Part(f"paw{t}", gw["glove"], K.skin(f"d_glove{t}", GLOVE, None, rough=0.62, ior=1.30), voxel=0.0032),
                      Part(f"gloveRims{t}", gw["rims"], K.skin(f"d_glrim{t}", GLOVE_EDGE, None, rough=0.58, ior=1.30), voxel=0.0020),
                      Part(f"gloveSeams{t}", gw["seams"], K.skin(f"d_glseam{t}", GLOVE_THREAD, None, rough=0.70, ior=1.25),
                           voxel=0.0016),
                      Part(f"tips{t}", gw["tips"], K.skin(f"d_vtip{tg}{t}", vsk, None, emissive=glow, rough=0.50, ior=1.38),
                           voxel=0.0026),
                      Part(f"glovePatch{t}", gw["patch"], K.skin(f"d_glpatch{t}", GLOVE_PATCH, None, rough=0.66, ior=1.28),
                           voxel=0.0024)]
        parts = [p_ if not p_.name.startswith("claws") else
                 Part(p_.name, p_.sdf, K.skin(f"d_vclaws{p_.name[-1]}", CLAW_M, None, rough=0.55, ior=1.3), voxel=0.0018)
                 for p_ in parts]
    elif paws and vinyl:     # LOOK-L fix round 1: satin paws (a soft sheen, not the arm's wet clearcoat), cream-tan matte claws
        mitt = P.get("paws") == "mitt"
        for t in ("L", "R"):
            parts.append(Part(f"paw{t}", paws[t], K.skin(f"d_vpaw{tg}{t}", vsk, None, emissive=glow, rough=0.50 if mitt else 0.42,
                                                         ior=1.38, clearcoat=0.0 if mitt else 0.22, cc_rough=0.22),
                              voxel=0.0036 if mitt else 0.0032))
        parts = [p_ if not p_.name.startswith("claws") else
                 Part(p_.name, p_.sdf, K.skin(f"d_vclaws{p_.name[-1]}", CLAW_M if mitt else CLAW_V, None, rough=0.55, ior=1.3),
                      voxel=0.0024 if mitt else 0.0020)
                 for p_ in parts]
    if vinyl:
        shirt = {t: K.skin(f"d_sleeve{t}", SLEEVE, SLEEVE1, vfn=D.canvas_vfn(18, 3 + (t == "R")), rough=0.66, ior=1.22)
                 for t in ("L", "R")}
        for t in ("L", "R"):
            cuff_m = K.skin(f"d_cuff{t}", D.LEATHER, None, rough=0.42, ior=1.3, clearcoat=0.3, cc_rough=0.18)
            if t in gloves:        # v6: the gauntlet in the glove's matte leather (the judge: "acorn cups or chocolate")
                cuff_m = K.skin(f"d_gcuff{t}", GLOVE, None, rough=0.62, ior=1.30)
            parts += [Part(f"sleeve{t}", sleeves[t], shirt[t], voxel=0.004),
                      Part(f"cuff{t}", cuffs[t], cuff_m, voxel=0.003)]
        for name, sdf_, m, vx in work_boots(feet, matte=bool(P.get("boots_matte")), lace=P.get("lace_color")):
            parts.append(Part(name, sdf_, m, voxel=vx))
        if P.get("trousers") and P.get("trousers_detail"):
            # LOOK-2 round 2 (v6; the finish judge on v5: "smooth seamless bloomers with sausage legs: no waistband, side
            # seam, fly, pocket, hem or knee crease, and a faint noisy grain"): a waistband, raised side seams, knee
            # creases, a patch pocket on each outer thigh, the hems bloused over the boot tops, a clean fine weave
            tr, extras = trousers_detail(torso, legs, feet, hgt, BX)
            parts.append(Part("trousers", tr, K.skin(f"d_trousers6_{P['trousers']}", TROUSERS[P["trousers"]],
                                                     TROUSERS1[P["trousers"]], vfn=weave_vfn(), rough=0.74, ior=1.2),
                              voxel=0.0040))
            for n_, s_ in extras:          # (r2: the lighter edge ramp made the loops read as cream staples)
                parts.append(Part(n_, s_, K.skin(f"d_{n_}6b_{P['trousers']}", TROUSERS[P["trousers"]], None, rough=0.72, ior=1.2),
                                  voxel=0.0026))
        elif P.get("trousers"):
            parts.append(Part("trousers", trousers_sdf(torso, legs, feet, hgt, BX), K.skin(
                f"d_trousers_{P['trousers']}", TROUSERS[P["trousers"]], TROUSERS1[P["trousers"]], vfn=D.canvas_vfn(30, 13),
                rough=0.80, ior=1.2), voxel=0.0045))
    else:
        parts[12:12] = [Part("soles", soles, K.skin("d_soles", PAD, None, rough=0.62, ior=1.2), voxel=0.004),
                        Part("toeClaws", toe_claws, K.skin("d_toeclaws", CLAW, None, rough=0.34, ior=1.4), voxel=0.0025)]
    if P["brows"] == "none":          # LOOK-L: no brow ridge (the hard hat's brim is the brow line)
        parts = [p_ for p_ in parts if p_.name != "browridge"]
    if "lipline" in F:
        parts += [Part("lipline", hx.sdf(F["lipline"]), satin("d_lip", "#0E3F35", rough=0.6), voxel=0.002),
                  Part("philtrum", hx.sdf(F["philtrum"]), satin("d_phil", "#0E3F35", rough=0.6), voxel=0.002)]
    if "cavity" in F:
        parts += [Part("mouth", hx.sdf(F["inner"]), Material("d_mouth", MOUTH_IN, roughness=0.55, ior=1.22, emissive="#1A0604"), voxel=0.003),
                  Part("teeth", hx.sdf(F["teeth"]), Material("d_teeth", "#FFFDF6", roughness=0.25, ior=1.4, emissive="#7A7870"), voxel=0.002),
                  Part("tongue", hx.sdf(F["tongue"]), Material("d_tongue", TONGUE, roughness=0.35, ior=1.3, emissive="#4A1018"), voxel=0.003)]
    for name, sdf_, m, vx in kit + hat_parts + gog_parts + gog_strap + props:
        parts.append(Part(name, sdf_, m, voxel=vx))
    skip = set(P.get("occl_skip") or ())
    if skip:
        # LOOK-2 fix round (the finish judge: "when the paw swings out, a dark-brown speckled felt rectangle shows on the
        # trousers where the resting arm was"): a layer that the animation UNCOVERS (the body under the free arm) is
        # shaded by a field WITHOUT that arm -- the resting arm's occlusion was baked into the hip + trouser pocket
        for p_ in parts:
            if p_.name in skip:
                p_.occluder = False
        fld = K.field_for((key, "field", tuple(sorted(skip))), parts)
        for p_ in parts:
            if p_.name in skip:
                p_.occluder = True
    else:
        fld = K.field_for((key, "field"), parts)      # one field per character: every layer shades alike
    K.shade(parts, field=fld)
    if vinyl:                                         # LOOK-L: no strand fur at all (the smooth vinyl coat)
        if only is not None:
            parts = [p for p in parts if p.name in only]
        return parts, VOXEL
    # ---- fur (R1): velvet -- short, dense, little clumping; not under the kit, the sockets, nose, pads, ears
    covers = [nose.offset(0.004), hx.sdf(F["eyes"]).offset(0.012), inner_ears.offset(0.006), soles.offset(0.004),
              hx.sdf(F["brows"]).offset(0.004)]
    if vest is not None:
        covers += [vest.offset(0.012), piping.offset(0.008)]
    if belt is not None:
        covers.append(belt.offset(0.012))
    if hat_parts:
        covers.append(union(*[s_ for n_, s_, _, _ in hat_parts if n_ in ("hat", "brim")]).offset(0.01))
    if gog_strap:
        covers.append(union(*[s_ for _, s_, _, _ in gog_parts + gog_strap]).offset(0.006))
    if "cavity" in F:
        covers.append(hx.sdf(F["cavity"]).offset(0.01))
    cover = union(*covers)
    fstops = DIG_FUR_SAGE if P.get("fur") == "sage" else DIG_FUR
    fur_m = FUR.fur_material(f"d_fur_{P.get('fur', 'mint')}", None, stops=fstops, rough=0.62)
    mk = P["mouth"]
    body_key = (key, "bodyfur", mk, n_strands, seed)

    def build_body():
        return _body_strands(skin, cover, F, hx, view, fld, n_strands, seed, key=(key, "surf", mk), girth=g, hgt=hgt)
    parts += D.banded_fur_parts("fur", body_key, build_body, fstops, DIG_BELLY, bands=FUR_BANDS, rough=0.62,
                                mat_prefix=f"d_fur_{P.get('fur', 'mint')}")
    arm_cover = union(cover, claws["L"].offset(0.006), claws["R"].offset(0.006), torso.offset(-0.01))
    parts += [FUR.fur_part("furArmL", fur_m, _limb_fur(arms["L"], union(arm_cover, pads["L"].offset(0.006)), view, fld,
                                                       n_strands // 7, seed + 1, key=(key, "armL", _akey(P["arms"]["L"])))),
              FUR.fur_part("furArmR", fur_m, _limb_fur(arms["R"], union(arm_cover, pads["R"].offset(0.006)), view, fld,
                                                       n_strands // 7, seed + 2, key=(key, "armR", _akey(P["arms"]["R"])))),
              FUR.fur_part("browfur", FUR.fur_material("d_browfur", None, stops=DIG_BROW, rough=0.6),
                           _brow_fur(hx.sdf(F["brows"]), view, fld, seed + 3, key=(key, "brow", P["brows"]))),
              FUR.fur_part("lidfur", fur_m, _lid_fur(hx.sdf(F["lids"]), hx, view, fld, seed + 4, key=(key, "lid", P["eyes"])))]
    if only is not None:
        parts = [p for p in parts if p.name in only]
    return parts, VOXEL


def _belly_weight(P, hx, girth=1.0, hgt=1.0, bx=None, face=1.0):
    """The cream-mint patch: the tummy (body space) + the snout / chin (head space). face scales the snout / chin part
    (LOOK-L fix round 1: 0.35 on the Loading crew -- the full patch washed the whole face out to a pale mint)."""
    p = np.asarray(P, float)
    pb = bx.inv(p) if bx is not None else p
    d = np.hypot(pb[:, 0] / (0.40 * girth), (pb[:, 1] - 0.66 * hgt) / (0.42 * hgt))
    wb = np.clip((1.15 - d) / 0.50, 0, 1) * np.clip((pb[:, 2] - 0.14) / 0.14, 0, 1)
    q = hx.inv(p)
    ds = np.linalg.norm((q - np.array([0.0, 1.38, 0.52])) / np.array([0.27, 0.22, 0.34]), axis=1)
    ws = np.clip((1.15 - ds) / 0.50, 0, 1) * np.clip((q[:, 2] - 0.24) / 0.12, 0, 1) * face
    w = np.maximum(wb, ws)
    return w * w * (3 - 2 * w)


def _body_strands(skin, cover, F, hx, view, fld, n, seed, key, girth=1.0, hgt=1.0):
    cov = D.sdf_fn(cover)
    rng = np.random.default_rng(seed)
    v, f, nn = FUR.surface(skin, 0.009, key=key)
    vw = K.unit(view)
    from sdf import gradient

    def dens(p):
        p = np.asarray(p)
        w = (cov(p) > 0.0).astype(float)
        nrm = FUR.unit(np.asarray(gradient(skin, p.astype(np.float32), 0.004), float))
        w *= np.clip((nrm @ vw + 0.45) / 0.30, 0, 1)            # the camera side + the silhouette only
        return w
    P, N = FUR.sample(v, f, nn, n, rng, density=dens)
    x, y = P[:, 0], P[:, 1]
    nose_w = hx.p(NOSE_C[None])[0]
    away_nose = FUR.unit(P - nose_w[None])
    down = np.tile([[0.0, -1.0, -0.35]], (len(P), 1))
    q = hx.inv(P)
    hb = np.clip((q[:, 1] - 1.24) / 0.20, 0, 1)[:, None]
    comb = away_nose * hb + down * (1 - hb) + np.array([0, 0.25, 0])[None] * hb
    L = np.full(len(P), 0.021)
    L += 0.006 * np.clip((q[:, 1] - 1.60) / 0.3, 0, 1)              # a little longer on the crown / cheeks
    snout = np.clip(1 - np.linalg.norm((q - np.array([0, 1.44, 0.58])) / np.array([0.22, 0.20, 0.20]), axis=1), 0, 1)
    L *= 1 - 0.50 * snout
    for ex, ey in EYES:
        dd = np.hypot((q[:, 0] - ex) / 0.11, (q[:, 1] - ey) / 0.125)
        L *= 1 - 0.55 * np.clip(1.6 - dd, 0, 1)
    if "smile_pts" in F:
        from scipy.spatial import cKDTree
        dd, _ = cKDTree(F["smile_pts"]).query(q)
        L *= 1 - 0.6 * np.clip(1 - dd / 0.03, 0, 1)
    L *= 0.88 + 0.24 * rng.random(len(P))
    W = np.full(len(P), 0.0068) * (0.88 + 0.24 * rng.random(len(P)))
    V, Fc, NR, T, ri = FUR.strands(P, N, comb, L, 0.42, W, view, rng, segs=3, gravity=(0, -0.04, 0), clump=0.12,
                                   clump_size=0.016, per_clump=8, jitter=0.20, nbend=0.22)
    # R2: a plush velvet -- a low root->tip contrast (the light tips on dark gaps read as a frosted speckle at 2x)
    uv = FUR.tone_uv(fld, None, T, ri, P, rng.normal(0, 0.020, len(P)), tone0=0.55, tone_gain=0.28, N=N, under=0.22)
    w = _belly_weight(P, hx, girth, hgt)
    return dict(V=V, F=Fc, NR=NR, uv=uv, nv=2 * 3 + 1, band=D.band_of(w, FUR_BANDS, rng))


def _limb_fur(sdf, cover, view, fld, n, seed, key):
    cov = D.sdf_fn(cover)

    def fn():
        rng = np.random.default_rng(seed)
        v, f, nn = FUR.surface(sdf, 0.006, key=key)
        vw = K.unit(view)
        from sdf import gradient

        def dens(p):
            p = np.asarray(p)
            w = (cov(p) > 0.0).astype(float)
            nrm = FUR.unit(np.asarray(gradient(sdf, p.astype(np.float32), 0.004), float))
            w *= np.clip((nrm @ vw + 0.45) / 0.30, 0, 1)
            return w
        P, N = FUR.sample(v, f, nn, n, rng, density=dens)
        comb = np.tile([[0.0, -0.4, 1.0]], (len(P), 1))
        L = np.full(len(P), 0.018) * (0.88 + 0.24 * rng.random(len(P)))
        W = np.full(len(P), 0.0064) * (0.88 + 0.24 * rng.random(len(P)))
        V, Fc, NR, T, ri = FUR.strands(P, N, comb, L, 0.42, W, view, rng, segs=3, gravity=(0, -0.03, 0), clump=0.12,
                                       clump_size=0.016, per_clump=8, jitter=0.20, nbend=0.22)
        uv = FUR.tone_uv(fld, None, T, ri, P, rng.normal(0, 0.020, len(P)), tone0=0.55, tone_gain=0.28, N=N, under=0.18)
        return V, Fc, NR, uv
    return fn


def _brow_fur(brows, view, fld, seed, key):
    def fn():
        rng = np.random.default_rng(seed)
        vb, fb, nb = FUR.surface(brows, 0.004, key=key)
        P, N = FUR.sample(vb, fb, nb, 5200, rng, density=lambda p: (np.asarray(p)[:, 2] > 0.1).astype(float) + 1e-6)
        comb = np.zeros((len(P), 3))
        comb[:, 0] = np.sign(P[:, 0])
        comb[:, 1] = 0.3
        L = np.full(len(P), 0.026) * (0.8 + 0.4 * rng.random(len(P)))
        V, Fc, NR, T, ri = FUR.strands(P, N, comb, L, 0.35, 0.0075, view, rng, segs=3, clump=0.3, clump_size=0.02,
                                       per_clump=10, jitter=0.15, nbend=0.15)
        uv = FUR.tone_uv(fld, None, T, ri, P, rng.normal(0, 0.05, len(P)), tone0=0.40, tone_gain=0.45)
        return V, Fc, NR, uv
    return fn


def _lid_fur(lids, hx, view, fld, seed, key):
    def fn():
        rng = np.random.default_rng(seed)
        v, f, n = FUR.surface(lids, 0.004, key=key)
        front = lambda p: (hx.inv(np.asarray(p))[:, 2] > 0.3).astype(float) + 1e-6   # noqa: E731
        P, N = FUR.sample(v, f, n, 2600, rng, density=front)
        comb = np.tile([hx.n([0.0, 1.0, 0.0])], (len(P), 1))
        V, Fc, NR, T, ri = FUR.strands(P, N, comb, 0.010, 0.25, 0.0048, view, rng, segs=2, clump=0.2, clump_size=0.02,
                                       per_clump=8, jitter=0.2, nbend=0.15)
        uv = FUR.tone_uv(fld, None, T, ri, P, rng.normal(0, 0.04, len(P)), tone0=0.46, tone_gain=0.45, N=N)
        return V, Fc, NR, uv
    return fn


# ================================================================== the two HOME poses

SCALE_PT = 57.0            # the old workers' home scale: the crew stand as tall as before (~128 pt to the hat top)

# L: a lamp-hat Digger, facing the centre (screen right), a planted SHOVEL gripped at chest height by the right paw
# (armR); the free paw at rest (armL) / waving (armL_wave)
# R2 tried the shovel OVER the shoulder twice (the shaft projected vertical / like a raised torch from the home camera);
# the planted shovel of R1's concept reads best at 1/3: the blade on the ground by the right foot, the paw on the handle
_SHOVEL_B = np.array([0.80, 0.34, 0.40])      # the socket just above the blade (near the ground)
_SHOVEL_G = np.array([0.70, 1.42, 0.36])      # the D-grip end, above the paw
_SAX = K.unit(_SHOVEL_G - _SHOVEL_B)           # socket -> grip (up)
_Q = _SHOVEL_B + (_SHOVEL_G - _SHOVEL_B) * 0.565
_GRIP_R = grip_arm(_Q, _SAX, palm_n=(0.50, 0.0, -1.0))
ARM_L_REST = dict(el=(-0.68, 0.94, 0.06), wr=(-0.62, 0.72, 0.28), d=(0.20, -0.85, 0.45), palm=(0.55, 0.05, -0.85),
                  curl=26.0, spread=20.0)          # the paw resting on the upper hip, palm on the fur
ARM_L_WAVE = dict(el=(-0.74, 1.30, 0.16), wr=(-0.82, 1.64, 0.28), d=(-0.12, 1.0, 0.10), palm=(0.18, 0.0, 1.0),
                  curl=12.0, spread=26.0)
ARM_R_SHOVEL = dict(el=(0.72, 0.98, 0.08), **_GRIP_R)


def _shovel_L(ctx):
    # the blade continues BEYOND the socket (away from the grip); its local +y (the shoulders of the spade) points
    # back along the handle
    return shovel(_SHOVEL_B, _SHOVEL_G, _SHOVEL_B - _SAX * 0.22, blade_up=_SAX, blade_face=K.unit([0.10, 0.0, 1.0]))


HOME_L = spec_with(BASE, girth=1.06, head=dict(yaw=6.0, roll=-3.0, nod=-4.0), look=(0.15, 0.10), brows="friendly",
                   mouth="smile", eyes="open", trowel=False,
                   hat=dict(lamp=True, goggles=True, tilt=-10.0, roll=6.0),
                   arms=dict(L=ARM_L_REST, R=ARM_R_SHOVEL))
SHOVEL_PARTS = {"shovelHandle", "shovelBlade", "shovelIron", "shovelRivets"}

# R: taller, slimmer, sage-mint; goggles DOWN over the eyes, reading the tunnel MAP (armL) and marking it with a pencil
# (armR); facing the centre (screen left); eyes half (reading) by default
_MAP_C = np.array([-0.10, 0.98, 0.78])
_MAP_UP = K.unit([0.10, 0.62, -0.78])        # the sheet tilted up toward the face (and the camera sees the ink)
_MAP_FACE = K.unit([0.05, 0.78, 0.62])
ARM_L_MAP = dict(el=(-0.62, 0.94, 0.30), wr=(-0.44, 0.92, 0.66), d=(0.55, 0.10, 0.60), palm=(0.05, 1.0, 0.05),
                 curl=70.0, spread=14.0, claw_bend=60.0, claw_len=0.06)
_PENCIL_TIP = _MAP_C + _MAP_FACE * 0.012 + np.array([0.10, -0.02, 0.0])
ARM_R_PENCIL = dict(el=(0.62, 0.90, 0.26), wr=(0.30, 1.00, 0.78), d=(-0.55, -0.10, 0.45), palm=(-0.2, -0.9, 0.3),
                    curl=95.0, spread=10.0, claw_bend=70.0, claw_len=0.05)


def _map_R(ctx):
    return tunnel_map(_MAP_C, _MAP_UP, _MAP_FACE)


def _pencil_R(ctx):
    return pencil(_PENCIL_TIP, K.unit([0.45, 0.55, 0.25]), length=0.30)


HOME_R = spec_with(BASE, girth=0.96, height=1.05, head=dict(yaw=-6.0, roll=4.0, nod=8.0), look=(-0.10, -0.55),
                   brows="friendly", mouth="smile", eyes="half", fur="sage", trowel=True,
                   hat=dict(lamp=False, goggles=False, tilt=-16.0, roll=-5.0), goggles_down=True,
                   arms=dict(L=ARM_L_MAP, R=ARM_R_PENCIL))
MAP_PARTS = {"map", "mapRollers", "mapInk", "mapMark"}
PENCIL_PARTS = {"pencil", "pencilWood", "pencilLead"}

POSE_L = dict(yaw=18, pitch=6, center=False)       # turned toward the screen centre (right)
POSE_R = dict(yaw=-20, pitch=6, center=False)      # turned toward the screen centre (left)
FRAME_L = (156, 152)
FRAME_R = (144, 150)
VIEW_L = K.view_bounds(FRAME_L, scale_pt=SCALE_PT, center=(0.04, 1.20), zr=(-0.9, 1.1), margin=1.0)
VIEW_R = K.view_bounds(FRAME_R, scale_pt=SCALE_PT, center=(-0.04, 1.20), zr=(-0.9, 1.1), margin=1.0)
FEET_L_PT = (70.0, 606.0)
FEET_R_PT = (318.0, 606.0)

MODELS = {}
ASSETS = {}


def _rig(name, base, pose, view, frame, feet_pt, arm_l_props=(), arm_r_props=(), extra=None, mouths=("smile", "open"),
         eye_members=("open", "half", "closed"), eyes_default="open", goggles=False, arm_l_alts=None, seed=11, light=None):
    def factory(only=None, eyes=None, mouth=None, armL=None):
        sp = spec_with(base, eyes=eyes, mouth=mouth, arms=(dict(L=armL) if armL is not None else None))
        return digger(sp, only=only, view_pose=pose, seed=seed, key=name, extra_parts=extra)
    feet = [0.0, 0.0, 0.12]
    hx0 = HeadXf(lift=(base["height"] - 1.0) * 1.25, **base["head"])
    neck = list(hx0.p(NECK[None])[0])
    eyes_p = list(hx0.p(np.array([[0.0, 1.705, 0.50]]))[0])
    lo = [dict(name=f"body_{m}", parts=BODY_PARTS, kw=dict(mouth=m), group="body", default=(m == base["mouth"]),
               pivots={"feet": feet, "neck": neck}, note=f"the Digger + vest, belt, hat; mouth {m}") for m in mouths]
    lo += [dict(name=f"eyes_{e}", parts=EYE_PARTS, kw=dict(eyes=e), holdout=BODY_PARTS, group="eyes",
                default=(e == eyes_default), parent="body", pivots={"eyes": eyes_p},
                note=f"eyes {e} (swap group: blink = open -> half -> closed -> open)") for e in eye_members]
    if goggles:
        lo.append(dict(name="goggles", parts=GOGGLE_PARTS, holdout=BODY_PARTS, parent="body", pivots={"eyes": eyes_p},
                       note="brass goggles pulled down over the eyes (glass lenses: the eyes read through)"))
    sh_l, sh_r = list(SHOULDERS[0] * [base["girth"], base["height"], 1]), list(SHOULDERS[1] * [base["girth"], base["height"], 1])
    lo.append(dict(name="armL", parts=ARM_L | set(arm_l_props), holdout=BODY_PARTS, pivots={"shoulder": sh_l}, parent="body",
                   **(dict(group="armL", default=True) if arm_l_alts else {})))
    for m, arm_ in (arm_l_alts or {}).items():
        lo.append(dict(name=m, parts=ARM_L, kw=dict(armL=arm_), holdout=BODY_PARTS, pivots={"shoulder": sh_l}, parent="body",
                       group="armL", note="idle-loop wave: the free paw raised, palm + claws to the camera"))
    lo.append(dict(name="armR", parts=ARM_R | set(arm_r_props), holdout=BODY_PARTS, pivots={"shoulder": sh_r}, parent="body"))
    spec = K.explicit_rig(MODELS, ASSETS, name, factory, frame, view, pose, light or D.LIGHT_D1, lo, full_kw={},
                          full_anchors={"feet": feet})
    spec["place"] = dict(anchor="feet", at=feet_pt)
    return spec


RIGS = {
    "dig_homeL": _rig("dig_homeL", HOME_L, POSE_L, VIEW_L, FRAME_L, FEET_L_PT, arm_r_props=SHOVEL_PARTS, extra=_shovel_L,
                      eye_members=("open", "half", "closed", "wink"), arm_l_alts={"armL_wave": ARM_L_WAVE}, seed=11),
    "dig_homeR": _rig("dig_homeR", HOME_R, POSE_R, VIEW_R, FRAME_R, FEET_R_PT, arm_l_props=MAP_PARTS, arm_r_props=PENCIL_PARTS,
                      extra=lambda ctx: _map_R(ctx) + _pencil_R(ctx), eyes_default="half", goggles=True, seed=23),
}


# ================================================================== LOOK-2 HOME: the home Diggers in the Loading's VINYL finish
# The owner (09-28 13:56: "not as smooth and good as the original") -> the Loading crew became smooth satin VINYL toys
# (LOOK-L / LOOK-2 v6); the measured home gap is the same (build/p/LOOK/round3.json home_findings: crew skin Laplacian
# 34x the original's = felt). The two home rigs take the Loading crew's finish exactly (char_cast_d1.VB4 face + V6:
# the short muzzle, 1.4x glossy eyes with an off-white sclera, satin vinyl (vmat 3, no clearcoat spike, warm shadows),
# fingerless leather work gloves, detailed khaki work trousers, matte laced boots, a glossy hard hat) with the SAME
# rig contract: names, frames, views, poses, the feet placement, the layer / group / pivot names and pivot points, the
# same props (L: the planted shovel + the waving paw; R: goggles DOWN over the eyes, the tunnel map + pencil, eyes half).
# The fur HOME_L / HOME_R specs above stay (event / avatar figures still use the fur finish unless they pass "vinyl").
HOME_VINYL = dict(finish="vinyl", snout="muzzle", eye_scale=1.40, eye_lift=0.035, hat_lift=0.05, brows="none",
                  sclera="soft", eye_div=-0.05, lash=0.0, lid_gap=0.004, lids_open=0.92, low_lid=0.93, snout_back=0.035,
                  teeth_k=0.72, laugh=0.72, hat_gloss=True, vmat=3, belly_face=0.0, paws="glove", trousers="khaki",
                  trousers_detail=True, boots_matte=True, mouth_clean=True, lace_color="#6A3E20")
HOME_L_V = spec_with(HOME_L, skin_tint="a2", **HOME_VINYL)
HOME_R_V = spec_with(HOME_R, skin_tint="b2", goggles_fit=dict(gk=1.30, dz=0.040), **HOME_VINYL)
LIGHT_HOME_V = {"L": dict(D.LIGHT_D1_HK4, rim_dir=D.rim_from(0.7)), "R": dict(D.LIGHT_D1_HK4, rim_dir=D.rim_from(-0.7))}

RIGS["dig_homeL"] = _rig("dig_homeL", HOME_L_V, POSE_L, VIEW_L, FRAME_L, FEET_L_PT, arm_r_props=SHOVEL_PARTS, extra=_shovel_L,
                         eye_members=("open", "half", "closed", "wink"), arm_l_alts={"armL_wave": ARM_L_WAVE}, seed=11,
                         light=LIGHT_HOME_V["L"])
RIGS["dig_homeR"] = _rig("dig_homeR", HOME_R_V, POSE_R, VIEW_R, FRAME_R, FEET_R_PT, arm_l_props=MAP_PARTS,
                         arm_r_props=PENCIL_PARTS, extra=lambda ctx: _map_R(ctx) + _pencil_R(ctx), eyes_default="half",
                         goggles=True, seed=23, light=LIGHT_HOME_V["R"])


# ================================================================== LOOK-2 FIX ROUND: the home Diggers (judged 2026-09-29)
# The finish judge on the LOOK-2 home (build/p/LOOK2/judge; defects 3, 7, 8, 14) and the copy judge (J-copy-home: "the
# right crew's goggles-down read as big round spectacles plus notepad and pencil = their right worker's idea"):
#   3  the hip under the free arm: a dark speckled "felt" rectangle when the arm swings out (the resting arm's occlusion
#      baked into the trouser pocket) -> the body layers are shaded by a field WITHOUT the free arm (occl_skip)
#   7  small + static -> the same frame / placement, the figure 60/57 bigger (the view centre re-solved so the feet land
#      on the SAME frame point: build/p/LOOK2/home2/tools/viewsolve.py), L: elbow out (a hand-on-hip swagger), a jaunty
#      head tilt, the upper body twisted a little toward the viewer; R: glancing UP from the plan toward his mate
#   8  R's eyes lost behind goggle glare -> goggles UP on the hard hat (still the rig's "goggles" layer), bigger darker
#      irises, a half-lid smirk
#   14 no broad satin sheen -> vmat 4 (a thin broad coat, cc_rough 0.30)
#   copy: R reads a mine BLUEPRINT (blue sheet, white lines) instead of a cream note sheet; no glasses on the face
SCALE_PT2 = 60.0
VIEW_L2 = K.view_bounds(FRAME_L, scale_pt=SCALE_PT2, center=(0.03988, 1.13784), zr=(-0.9, 1.1), margin=1.0)
VIEW_R2 = K.view_bounds(FRAME_R, scale_pt=SCALE_PT2, center=(-0.03999, 1.13978), zr=(-0.9, 1.1), margin=1.0)
ARM_L_AKIMBO = dict(el=(-0.86, 0.97, -0.02), wr=(-0.62, 0.72, 0.24), d=(0.30, -0.80, 0.50), palm=(0.60, 0.05, -0.80),
                    curl=30.0, spread=18.0)


def _shovel_L2(ctx):
    # the planted shovel follows the upper body's twist (a twist turns about +Y: the blade slides on the floor plane)
    bx = ctx["bx"]
    return [(n_, bx.sdf(s_), m_, v_) for n_, s_, m_, v_ in _shovel_L(ctx)]


def _map_R2(ctx):
    return tunnel_map(_MAP_C, _MAP_UP, _MAP_FACE, style="blueprint")


HOME_L_V2 = spec_with(HOME_L_V, vmat=4, twist=-7.0, head=dict(yaw=4.0, roll=-8.0, nod=-3.0), arms=dict(L=ARM_L_AKIMBO))
HOME_R_V2 = spec_with(HOME_R_V, vmat=4, goggles_down=False, brim_goggles_layer=True,
                      hat=dict(lamp=False, goggles=True, tilt=-14.0, roll=-4.0),
                      head=dict(yaw=-10.0, roll=8.0, nod=-1.0), look=(-0.36, 0.02), iris_k=1.22, half_lid=0.40)


def _rig2(name, base, pose, view, frame, feet_pt, arm_l_props=(), arm_r_props=(), extra=None, mouths=("smile", "open"),
          eye_members=("open", "half", "closed"), eyes_default="open", goggles=False, arm_l_alts=None, seed=11, light=None,
          body_occl_skip=None):
    """_rig + (1) the pivots follow the body's lean / twist (BodyXf), (2) body_occl_skip: the body layers' obscurance
    field leaves those parts out (an arm the animation swings away)."""
    def factory(only=None, eyes=None, mouth=None, armL=None, occl=None):
        sp = spec_with(base, eyes=eyes, mouth=mouth, arms=(dict(L=armL) if armL is not None else None))
        if occl:
            sp["occl_skip"] = set(occl)
        return digger(sp, only=only, view_pose=pose, seed=seed, key=name, extra_parts=extra)
    feet = [0.0, 0.0, 0.12]
    BX = BodyXf(base.get("lean", 0.0), base.get("twist", 0.0), base.get("body_roll", 0.0))
    hx0 = HeadXf(lift=(base["height"] - 1.0) * 1.25, **base["head"])
    neck = list(BX.p(hx0.p(NECK[None]))[0])
    eyes_p = list(BX.p(hx0.p(np.array([[0.0, 1.705 + base.get("eye_lift", 0.0), 0.50]])))[0])
    okw = dict(occl=tuple(sorted(body_occl_skip))) if body_occl_skip else {}
    lo = [dict(name=f"body_{m}", parts=BODY_PARTS, kw=dict(mouth=m, **okw), group="body", default=(m == base["mouth"]),
               pivots={"feet": feet, "neck": neck}, note=f"the Digger + vest, belt, hat; mouth {m}") for m in mouths]
    lo += [dict(name=f"eyes_{e}", parts=EYE_PARTS, kw=dict(eyes=e), holdout=BODY_PARTS, group="eyes",
                default=(e == eyes_default), parent="body", pivots={"eyes": eyes_p},
                note=f"eyes {e} (swap group: blink = open -> half -> closed -> open)") for e in eye_members]
    if goggles:
        lo.append(dict(name="goggles", parts=GOGGLE_PARTS, holdout=BODY_PARTS, parent="body", pivots={"eyes": eyes_p},
                       note="brass goggles pushed UP on the hard hat (the rig's goggles layer)"))
    sh_l = list(BX.p(SHOULDERS[0] * [base["girth"], base["height"], 1]))
    sh_r = list(BX.p(SHOULDERS[1] * [base["girth"], base["height"], 1]))
    lo.append(dict(name="armL", parts=ARM_L | set(arm_l_props), holdout=BODY_PARTS, pivots={"shoulder": sh_l}, parent="body",
                   **(dict(group="armL", default=True) if arm_l_alts else {})))
    for m, arm_ in (arm_l_alts or {}).items():
        lo.append(dict(name=m, parts=ARM_L, kw=dict(armL=arm_), holdout=BODY_PARTS, pivots={"shoulder": sh_l}, parent="body",
                       group="armL", note="idle-loop wave: the free paw raised, palm + claws to the camera"))
    lo.append(dict(name="armR", parts=ARM_R | set(arm_r_props), holdout=BODY_PARTS, pivots={"shoulder": sh_r}, parent="body"))
    spec = K.explicit_rig(MODELS, ASSETS, name, factory, frame, view, pose, light or D.LIGHT_D1, lo, full_kw={},
                          full_anchors={"feet": feet})
    spec["place"] = dict(anchor="feet", at=feet_pt)
    return spec


RIGS["dig_homeL"] = _rig2("dig_homeL", HOME_L_V2, POSE_L, VIEW_L2, FRAME_L, FEET_L_PT, arm_r_props=SHOVEL_PARTS,
                          extra=_shovel_L2, eye_members=("open", "half", "closed", "wink"), arm_l_alts={"armL_wave": ARM_L_WAVE},
                          seed=11, light=LIGHT_HOME_V["L"], body_occl_skip=ARM_L)
RIGS["dig_homeR"] = _rig2("dig_homeR", HOME_R_V2, POSE_R, VIEW_R2, FRAME_R, FEET_R_PT, arm_l_props=MAP_PARTS,
                          arm_r_props=PENCIL_PARTS, extra=lambda ctx: _map_R2(ctx) + _pencil_R(ctx), eyes_default="half",
                          goggles=True, seed=23, light=LIGHT_HOME_V["R"])
