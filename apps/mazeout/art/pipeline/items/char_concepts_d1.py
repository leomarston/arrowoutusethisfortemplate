"""R1 CONCEPTS (PLAN-P §4.2; SPEC ruling 38; design/publish/art-direction.md §1.3 / §3.0 / §3.1 / §5): DRAFT renders for
direction D1 "Burrow Works". Nothing here ships: every case writes to build/ui-art/route3d/ (dest="route3d"), and the
sheets in art/review/concepts/ are built from those by art/review/tools/r1_concepts.py.

  concept_bossV2_home   the pink boss with the MINIMAL change set (ruling 38): two ivory horns instead of the crown
                        tuft, a blush muzzle patch (its own fur + LUT), amber irises, one snaggle tooth, a teal canvas
                        foreman coat (placket, brass buttons, rounded corduroy collar, rolled sleeves, a blueprint roll
                        in the breast pocket) instead of the lab coat / lanyard / badge / pen, goggles pushed up between
                        the horns, and a timber scaffold rail with a brass lever instead of the console. SAME camera,
                        frame and pose table as char_sci_home (char_scientist.HOME_*), so old -> new is a 1:1 swap.
  concept_digger_hero   the D1 crew species ("Digger"): a velvet strand-fur critter (R1), pear body + separate head +
                        snout cone + peach nose + tiny ears, spade paws with ivory claws and bare palm pads, a sunflower
                        hard hat with a headlamp, brass goggles, a tangerine hi-vis vest (a shell with arm holes and a
                        V opening + a cream reflective stripe), a leather tool belt with a trowel, a shovel. Home scale
                        (57 pt/u, the workers' scale) so it sits next to today's workers on the calibration card.
  concept_iconIC1       icon draft IC-1 "Out the Door" at 512 px: a chunky tangerine arrow bursting out of a maze
                        block's doorway with a Digger clinging to its shaft, the hard hat flying off; the teal ground +
                        embossed maze is painted in post_fit.

The boss re-uses char_scientist's head/fur/groom/arm code (imported, never edited); R2 CAST forks this file into
char_boss.py / char_crew_d1.py. The A-bar rules R1-R8 (art-direction.md §1.3) are the design brief of every part below.
"""
from __future__ import annotations

import math
import os

import numpy as np

import char_fur as FUR
import char_kit as K
import char_scientist as S
from mesher import Material
from uikit import (Part, box, capsule, cylinder, ellipsoid, extrude, gloss, glass, metal, polygon2, round_cone,  # noqa: F401
                   satin, sphere, torus, union)
from sdf import SDF as _SDF, fillet_points

VOXEL = 0.006
HERE = os.path.dirname(os.path.abspath(__file__))


# ================================================================== D1 room + light (R6)

def env_d1(path=None):
    """Equirect room of the Burrow Works: warm timber props and lantern light on one side, cool teal rock on the other,
    a cream daylight shaft from above, packed-earth floor (art-direction.md §3.1 palette). Made once."""
    from PIL import Image
    path = path or os.path.join(K.APP, "build", "ui-art", "char_env_d1.png")
    if os.path.exists(path):
        return path
    os.makedirs(os.path.dirname(path), exist_ok=True)
    W, H = 512, 256
    u, v = np.meshgrid((np.arange(W) + 0.5) / W, (np.arange(H) + 0.5) / H)
    phi = (u - 0.5) * 2 * math.pi
    theta = v * math.pi
    d = np.stack([np.sin(theta) * np.sin(phi), np.cos(theta), -np.sin(theta) * np.cos(phi)], -1)
    t = d[..., 1]
    ceil = np.array([0.93, 0.85, 0.68])
    timber = np.array([0.70, 0.50, 0.29])
    rock = np.array([0.28, 0.46, 0.48])
    floor = np.array([0.50, 0.39, 0.28])
    wmix = np.clip(0.5 + 0.55 * (-d[..., 0]), 0, 1)[..., None]          # timber on the left, rock on the right
    wall = rock + (timber - rock) * wmix
    col = np.where(t[..., None] > 0, wall + (ceil - wall) * np.clip(t, 0, 1)[..., None] ** 0.8,
                   wall + (floor - wall) * np.clip(-t * 2.2, 0, 1)[..., None])
    for k, amp, width in (((-0.55, 0.62, 0.56), np.array([0.64, 0.52, 0.32]), 0.78),     # lantern (key reflection)
                          ((0.70, 0.55, -0.45), np.array([0.36, 0.44, 0.42]), 0.86)):    # daylight shaft
        kk = K.unit(k)
        col = col + np.clip((d @ kk - width) / (1 - width), 0, 1)[..., None] ** 1.3 * amp
    Image.fromarray((np.clip(col, 0, 1) * 255).astype(np.uint8)).save(path)
    return path


# R6: the CHAR_LIGHT family (key 1730 lx warm, fill warm = fake SSS); the rim is a cool teal-white at 1150 lx (<= 1400 lx,
# never the workers' 4200-lx hot orange rim); the D1 room as the ambient dome
LIGHT_D1 = dict(K.CHAR_LIGHT, env=env_d1(), rim_color=(0.80, 0.96, 0.92), rim_lux=1150.0,
                fill_color=(1.0, 0.80, 0.60), fill_lux=375.0)


def slab_y(y0, y1, big=3.0):
    return box(big, (y1 - y0) / 2, big).translate(0, (y0 + y1) / 2, 0)


def _sdf_fn(sdf):
    return lambda p: sdf(np.asarray(p, np.float32))


# ================================================================== the DIGGER (crew species)

MINT = ("#B6F5E2", "#7FE3C3", "#4CCBA5", "#2FA888", "#1C8068", "#115C4C")
DIG_FUR = [(0.0, [(0.0, "#2FA888"), (0.5, "#1C8068"), (1.0, "#115C4C")]),
           (0.35, [(0.0, "#7FE3C3"), (0.35, "#4CCBA5"), (0.6, "#2FA888"), (1.0, "#1C8068")]),
           (1.0, [(0.0, "#C6F9E8"), (0.35, "#9CEDD3"), (0.6, "#63D7B4"), (1.0, "#34AE8E")])]
DIG_SKIN = [(0.0, "#4CCBA5"), (0.5, "#2FA888"), (0.8, "#1C8068"), (1.0, "#115C4C")]
DIG_BROW = [(0.0, [(0.0, "#0C4238"), (1.0, "#072A24")]), (0.35, [(0.0, "#135646"), (1.0, "#0C4238")]),
            (1.0, [(0.0, "#1E7563"), (1.0, "#135646")])]
DIG_BROW_SKIN = [(0.0, "#135646"), (0.5, "#0C4238"), (1.0, "#072A24")]
NOSE = [(0.0, "#FFD6BF"), (0.45, "#FFB896"), (0.8, "#E8906E"), (1.0, "#B8604A")]
PAD = [(0.0, "#F6B8A2"), (0.5, "#E39A82"), (0.8, "#C27862"), (1.0, "#8E4E3E")]
INNER_EAR = [(0.0, "#F7B9A6"), (0.5, "#E49C88"), (1.0, "#A85E4E")]
CLAW = [(0.0, "#FFFBEE"), (0.45, "#FFF4DA"), (0.8, "#E8D7AF"), (1.0, "#BBA57A")]
HAT = [(0.0, "#FFE27A"), (0.4, "#FFCB2F"), (0.75, "#EDA80E"), (1.0, "#B77C04")]
VEST = [(0.0, "#FFB36A"), (0.45, "#FF8A2A"), (0.75, "#E26A12"), (1.0, "#A64806")]
STRIPE = [(0.0, "#FFFCF0"), (0.5, "#FFF4DA"), (1.0, "#D8C8A4")]
LEATHER = [(0.0, "#B8824F"), (0.45, "#8E5A2F"), (0.8, "#6A3F1E"), (1.0, "#43260F")]
WOOD0 = [(0.0, "#F2C586"), (0.45, "#E0A862"), (0.8, "#B97A3E"), (1.0, "#7E4E27")]
WOOD1 = [(0.0, "#D9A462"), (0.45, "#B97A3E"), (0.8, "#8E5A2F"), (1.0, "#5E3718")]
IRIS_DIG = "#3A2618"
PUPIL = "#0D0806"
EYE_WHITE = "#F7F5F0"
BRASS = "#E3B04B"
STEEL = "#BCC5CE"
MOUTH_IN = "#4A1A12"
TONGUE = "#E2566A"


def grain_vfn(freq=26.0, axis=0, seed=1):
    """Wood grain for the v term of a 2-ramp LUT: streaks running along `axis`, warped by value noise."""
    from sdf import value_noise3

    def fn(v):
        p = np.asarray(v, np.float32)
        other = [i for i in range(3) if i != axis]
        n = value_noise3(p * np.float32(1.0), freq=3.0, seed=seed)
        s = np.sin(freq * (p[:, other[0]] * 1.0 + p[:, other[1]] * 0.6) + 5.0 * n)
        return np.clip(0.5 + 0.5 * s, 0, 1) ** 2.2
    return fn


def spade_paw(wrist, d, palm_n, r=0.15, curl=15.0, spread=24.0, claw_len=0.11):
    """A digger's SPADE paw: a broad flat palm, three short fingers fanned at the tip edge, an ivory claw hooking out of
    each fingertip, bare palm + finger pads on the palm side. -> dict(paw, claws, pads)."""
    R = K.frame_from(d, palm_n)
    ex, ey, ez = R[:, 0], R[:, 1], R[:, 2]
    wrist = np.asarray(wrist, float)
    c = wrist + ey * r * 0.95
    palm = K.local_ellipsoid((r * 1.12, r * 1.02, r * 0.56), R, c)
    fingers, claws, pads = [palm], [], [K.local_ellipsoid((r * 0.78, r * 0.62, r * 0.26), R, c + ez * r * 0.38 - ey * r * 0.08)]
    for i in (-1, 0, 1):
        fd = K.rotate_about(ey, ez, -i * spread)
        base = c + fd * r * 0.72
        tipd = K.unit(K.rotate_about(fd, np.cross(fd, ez), curl))
        tip = base + tipd * r * 0.50
        fingers.append(round_cone(tuple(base), tuple(tip), r * 0.36, r * 0.31))
        pads.append(sphere(r * 0.19).translate(*(tip + ez * r * 0.20 - tipd * r * 0.05)))
        cb = tip + tipd * r * 0.10
        cd = K.unit(K.rotate_about(tipd, np.cross(tipd, ez), 28))
        claws.append(round_cone(tuple(cb), tuple(cb + cd * claw_len), r * 0.17, r * 0.045))
    tb = c + ex * r * 0.95 - ey * r * 0.25
    fingers.append(round_cone(tuple(tb), tuple(tb + K.unit(ex * 0.8 + ey * 0.5 + ez * 0.2) * r * 0.45), r * 0.30, r * 0.26))
    return dict(paw=union(*fingers, k=r * 0.30), claws=union(*claws), pads=union(*pads, k=r * 0.08))


DIG_POSES = {
    # home hero: waving with the screen-LEFT paw (palm + claws toward the camera), the other paw grips a shovel whose
    # blade rests on the ground beside the right foot
    "hero": dict(
        arms=dict(L=dict(el=(-0.72, 1.30, 0.14), wr=(-0.80, 1.63, 0.26), d=(-0.12, 1.0, 0.10), palm=(0.18, 0.0, 1.0),
                         curl=14, spread=26),
                  R=dict(el=(0.66, 0.94, 0.16), wr=(0.66, 0.78, 0.38), d=(0.10, -0.15, 1.0), palm=(1.0, 0.0, -0.1),
                         curl=105, spread=12)),
        shovel=True, trowel=True, hat=True, mouth="smile", look=(0.10, 0.02), lids=0.74),
    # the icon: clinging to the arrow shaft that runs in front of the belly (up-right), grinning, hat gone
    "ride": dict(
        arms=dict(L=dict(el=(-0.64, 0.86, 0.40), wr=(-0.36, 0.58, 0.68), d=(0.55, -0.25, 0.80), palm=(0.3, -1.0, 0.1),
                         curl=100, spread=12),
                  R=dict(el=(0.64, 1.20, 0.36), wr=(0.36, 1.00, 0.70), d=(0.55, 0.30, 0.78), palm=(0.2, -1.0, 0.2),
                         curl=100, spread=12)),
        shovel=False, trowel=False, hat=False, vest=False, mouth="grin", look=(0.35, 0.30), lids=0.90),
}

D_HEAD_C = np.array([0.0, 1.58, 0.06])
D_HEAD_R = (0.42, 0.38, 0.40)
D_NOSE_C = np.array([0.0, 1.475, 0.715])
D_EYES = [(-0.172, 1.678), (0.172, 1.678)]
D_EYE_R = (0.080, 0.094, 0.062)


def digger_body():
    hips = ellipsoid(0.60, 0.52, 0.50).translate(0, 0.66, 0.0)
    chest = ellipsoid(0.46, 0.42, 0.42).translate(0, 1.08, 0.02)
    torso = union(hips, chest, k=0.25)
    head = ellipsoid(*D_HEAD_R).translate(*D_HEAD_C)
    snout = round_cone((0, 1.50, 0.30), (0, 1.40, 0.60), 0.19, 0.135)
    ears = [ellipsoid(0.10, 0.108, 0.046).transform(K.frame_from([sx * 0.25, 1.0, 0.1], [sx * 0.62, 0.1, 0.78]))
            .translate(sx * 0.385, 1.665, -0.03) for sx in (-1, 1)]
    legs = []
    for sx in (-1, 1):
        hip = np.array([sx * 0.27, 0.36, 0.06])
        ank = np.array([sx * 0.31, 0.13, 0.12])
        foot = ellipsoid(0.175, 0.105, 0.235).translate(sx * 0.32, 0.10, 0.17)
        legs.append(union(round_cone(tuple(hip), tuple(ank), 0.17, 0.15), foot, k=0.06))
    skin = union(torso, head, k=0.10)
    skin = union(skin, snout, k=0.07)
    skin = union(skin, *ears, k=0.03)
    skin = union(skin, *legs, k=0.06)
    return dict(torso=torso, head=head, snout=snout, ears=ears, legs=legs, skin=skin)


def digger_face(skin, mouth="smile", look=(0.1, 0.0), lids=0.52):
    out = dict(eyes=[], irises=[], pupils=[], glints=[], sockets=[], brows=[], lids=[], crease=[])
    for i, (ex, ey) in enumerate(D_EYES):
        sx = -1 if i == 0 else 1
        rx, ry, rz = D_EYE_R
        ez = K.surface_z_of(skin, ex, ey)
        c = np.array([ex, ey, ez - rz * 0.30])
        e = ellipsoid(rx, ry, rz).translate(*c)
        out["eyes"].append(e)
        out["sockets"].append(ellipsoid(rx * 1.16, ry * 1.12, rz * 1.3).translate(*c))
        lx, ly = look
        dd = K.unit([-sx * lx * rx, ly * ry, rz])
        sp = c + dd * np.array([rx, ry, rz])
        out["irises"].append(e.offset(0.0015).intersect(sphere(0.054).translate(*sp)))
        out["pupils"].append(e.offset(0.003).intersect(sphere(0.031).translate(*sp)))
        gp = c + K.unit(dd + np.array([-0.32, 0.36, 0.0])) * np.array([rx, ry, rz])
        out["glints"].append(sphere(0.0135).translate(*(gp + dd * 0.005)))
        out["glints"].append(sphere(0.0055).translate(*(c + K.unit(dd + np.array([0.30, -0.28, 0.0])) * np.array([rx, ry, rz]) + dd * 0.004)))
        # the upper lid: a fur-covered shell over the top of the eyeball (R4: the eye sits IN the face under a lid)
        shell = ellipsoid(rx + 0.013, ry + 0.013, rz + 0.013).translate(*c)
        cut = ey + lids * ry
        out["lids"].append(shell.intersect(box(0.3, 0.3, 0.3).translate(ex, cut + 0.3, c[2]), k=0.008))
        a = np.linspace(-0.95, 0.95, 11)
        xs = ex + a * (rx + 0.008) * math.sqrt(max(0.0, 1 - lids ** 2))
        ys = np.full_like(xs, cut) - 0.002
        zs = np.array([K.surface_z_of(shell, x, y) for x, y in zip(xs, ys)])
        out["crease"].append(K.limb(np.stack([xs, ys, zs - 0.004], 1), np.full(len(xs), 0.0075), k=0.004))
        # brow ridge (its own dark fur grows on it, R4: no floating brows)
        a = np.linspace(-1.0, 1.0, 9)
        bx = ex + sx * 0.012 + a * rx * 0.78
        by = ey + ry + 0.058 + 0.028 * (1 - a ** 2) + sx * 0.010 * a
        bz = np.array([K.surface_z_of(skin, x, y) for x, y in zip(bx, by)])
        out["brows"].append(K.limb(np.stack([bx, by, bz + 0.003], 1), 0.016 + 0.012 * (1 - a ** 2) ** 0.6, k=0.015))
    for k_ in list(out):
        out[k_] = union(*out[k_])
    zf = K.surface_z_of(skin, 0.0, 1.345)
    if mouth == "smile":
        xs = np.linspace(-0.115, 0.115, 15)
        tt = xs / 0.115
        ys = 1.335 + 0.040 * tt ** 2 + 0.012 * tt ** 6
        zs = np.array([K.surface_z_of(skin, x, y) for x, y in zip(xs, ys)])
        rr = 0.010 * np.clip(1 - tt ** 2, 0, 1) ** 0.5 + 0.006
        out["groove"] = K.limb(np.stack([xs, ys, zs + 0.004], 1), rr, k=0.008)
        out["lipline"] = K.limb(np.stack([xs, ys, zs - 0.004], 1), rr * 0.6, k=0.006)
        # a short philtrum from the nose down to the smile
        out["philtrum"] = K.limb([np.array([0.0, 1.395, K.surface_z_of(skin, 0.0, 1.395) - 0.002]),
                                  np.array([0.0, 1.345, zf - 0.002])], [0.005, 0.006], k=0.004)
        out["smile_pts"] = np.stack([xs, ys, zs], 1)
    else:     # "grin": an open smile under the nose with two front teeth (rodent-like, cute) and a pink tongue
        top = 1.37
        cav = ellipsoid(0.125, 0.085, 0.14).translate(0, top - 0.035, zf - 0.02).intersect(
            S.SDF_arc_top(top, 1.4), k=0.01)
        inner = ellipsoid(0.12, 0.08, 0.10).translate(0, top - 0.04, zf - 0.10)
        teeth = union(*[box(0.022, 0.024, 0.02, round=0.010).translate(sx * 0.024, top - 0.012, zf - 0.025) for sx in (-1, 1)])
        tongue = ellipsoid(0.075, 0.035, 0.07).translate(0.0, top - 0.090, zf - 0.07)
        out.update(cavity=cav, inner=inner, teeth=teeth, tongue=tongue)
    return out


def digger(pose="hero", only=None, view_pose=None, n_strands=120000, seed=11):
    """All parts of a Digger in its own frame (feet on y 0, facing +Z). only: a set of part names (layers)."""
    P = DIG_POSES[pose]
    vp = view_pose or DIG_VIEW_POSE
    view = S._view_dir(dict(yaw=vp.get("yaw", 0), pitch=vp.get("pitch", 0)))
    B = digger_body()
    skin0 = B["skin"]
    F = digger_face(skin0, mouth=P["mouth"], look=P["look"], lids=P["lids"])
    skin = skin0.subtract(F["sockets"].offset(-0.012), k=0.014)
    if "groove" in F:
        skin = skin.subtract(F["groove"], k=0.008)
    if "cavity" in F:
        skin = skin.subtract(F["cavity"], k=0.015)
    torso = B["torso"]
    # ---- kit: vest (a shell with arm holes, a V opening and a bottom edge), stripe, belt, buckle, trowel
    shoulders = [np.array([-0.40, 1.20, 0.0]), np.array([0.40, 1.20, 0.0])]
    # vest: a thin fabric shell from the chest to above the belly (the fur belly shows between hem and belt), arm holes,
    # a V neck, binding tape along every cut edge, a zip down the front, one reflective stripe
    VB, VT = 0.80, 1.43
    vest_outer = torso.offset(0.060)
    vest = vest_outer.subtract(torso.offset(0.034)).intersect(slab_y(VB, VT), k=0.008)
    for sh in shoulders:
        vest = vest.subtract(sphere(0.215).translate(*sh), k=0.02)
    vee = extrude(polygon2([(-0.19, 1.50), (0.19, 1.50), (0.0, 1.03)]), 0.6).translate(0, 0, 0.85)
    vest = vest.subtract(vee, k=0.02).subtract(B["head"].offset(0.03), k=0.02)
    band = union(slab_y(VB - 0.004, VB + 0.022), vee.offset(0.024).subtract(vee),
                 *[sphere(0.240).translate(*sh).subtract(sphere(0.214).translate(*sh)) for sh in shoulders])
    piping = torso.offset(0.068).subtract(torso.offset(0.030)).intersect(slab_y(VB - 0.004, VT)).intersect(band).subtract(
        vee.offset(0.002)).subtract(union(*[sphere(0.213).translate(*sh) for sh in shoulders]))
    zipper = torso.offset(0.066).subtract(torso.offset(0.040)).intersect(box(0.010, (1.04 - VB) / 2, 1.0).translate(0, (1.04 + VB) / 2, 0.8))
    zz = K.surface_z_of(torso.offset(0.066), 0.0, 1.00)
    pull = box(0.018, 0.034, 0.008, round=0.006).translate(0.0, 0.985, zz + 0.006)
    stripe = torso.offset(0.068).subtract(torso.offset(0.045)).intersect(slab_y(0.90, 0.97))
    belt = torso.offset(0.058).subtract(torso.offset(0.030)).intersect(slab_y(0.47, 0.58), k=0.006)
    bz = K.surface_z_of(torso.offset(0.058), 0.0, 0.525)
    buckle = box(0.072, 0.058, 0.016, round=0.012).subtract(box(0.040, 0.030, 0.05, round=0.008)).translate(0.0, 0.525, bz + 0.006)
    no_vest = P.get("vest", True) is False
    kit = [("vest", vest, K.skin("d_vest", VEST, None, rough=0.78, ior=1.18), 0.005),
           ("piping", piping, K.skin("d_piping", [(0.0, "#D9681A"), (0.5, "#B84E0A"), (1.0, "#7A3004")], None, rough=0.6, ior=1.2), 0.003),
           ("zipper", union(zipper, pull), metal("d_zip", "#C9CED4", rough=0.3), 0.002),
           ("stripe", stripe, Material("d_stripe", "#FFF4DA", roughness=0.30, ior=1.35, emissive="#2C2A22",
                                       texture=K.lut(STRIPE), texture_size=64), 0.004),
           ("belt", belt, K.skin("d_leather", LEATHER, None, rough=0.52, ior=1.25), 0.004),
           ("buckle", buckle, metal("d_buckle", BRASS, rough=0.28), 0.003)]
    kit[3][2].__dict__["_vfn"] = None
    if no_vest:
        kit = [k_ for k_ in kit if k_[0] not in ("vest", "piping", "zipper", "stripe")]
    if P.get("trowel"):
        tx, ty = 0.47, 0.42
        tz = K.surface_z_of(torso.offset(0.07), tx, ty + 0.10) + 0.03
        leaf = polygon2(fillet_points([(0.0, 0.0), (0.075, -0.07), (0.05, -0.20), (0.0, -0.27), (-0.05, -0.20), (-0.075, -0.07)],
                                      [0.02, 0.03, 0.03, 0.02, 0.03, 0.03], n_arc=5))
        Rt = K.frame_from([0.30, 1.0, 0.12], [0.35, 0.0, 1.0])
        blade = extrude(leaf, 0.008, round=0.006).transform(Rt).translate(tx + 0.02, ty, tz)
        handle = capsule((tx + 0.02, ty + 0.01, tz), (tx - 0.02, ty + 0.16, tz - 0.01), 0.026)
        kit += [("trowel", blade, metal("d_steel", STEEL, rough=0.30), 0.0025),
                ("trowelHandle", handle, K.skin("d_wood_t", WOOD0, WOOD1, vfn=grain_vfn(60, 1), rough=0.55, ior=1.25), 0.003)]
    # ---- hard hat (+ headlamp, + goggles resting on the brim), R3/R7
    hat_parts = []
    if P.get("hat", True):
        hat_parts = hard_hat()
    # ---- nose, inner ears, soles, claws
    nose = ellipsoid(0.098, 0.080, 0.080).translate(*D_NOSE_C)
    inner_ears = union(*[ellipsoid(0.062, 0.070, 0.03).transform(K.frame_from([sx * 0.25, 1.0, 0.1], [sx * 0.62, 0.1, 0.78]))
                         .translate(sx * 0.385 + sx * 0.014, 1.665, -0.03 + 0.020) for sx in (-1, 1)])
    skin = skin.subtract(inner_ears.offset(-0.004), k=0.01)
    soles = union(*[ellipsoid(0.165, 0.06, 0.22).translate(sx * 0.32, 0.035, 0.17) for sx in (-1, 1)]).intersect(slab_y(-0.1, 0.028))
    toe_claws = []
    for sx in (-1, 1):
        for j in (-1, 0, 1):
            b0 = np.array([sx * 0.32 + j * 0.075, 0.075, 0.37 - abs(j) * 0.02])
            toe_claws.append(round_cone(tuple(b0), tuple(b0 + np.array([j * 0.01, -0.035, 0.055])), 0.024, 0.009))
    # ---- arms + spade paws
    arms, claws, pads = {}, [toe_claws[0]], []
    for tag, sh in (("L", shoulders[0]), ("R", shoulders[1])):
        A = P["arms"][tag]
        el, wr = np.asarray(A["el"], float), np.asarray(A["wr"], float)
        pw = spade_paw(wr, K.unit(A["d"]), K.unit(A["palm"]), r=0.155, curl=A["curl"], spread=A["spread"])
        arms[tag] = union(K.limb([sh, el, wr], [0.14, 0.13, 0.12], k=0.06), pw["paw"], k=0.05)
        claws.append(pw["claws"])
        pads.append(pw["pads"])
    claws = union(*claws, *toe_claws[1:])
    pads = union(*pads)
    # ---- the shovel (hero)
    tools = []
    if P.get("shovel"):
        h0, h1 = np.array([0.80, 0.34, 0.40]), np.array([0.70, 1.42, 0.36])
        handle = capsule(tuple(h0), tuple(h1), 0.034)
        grip = capsule(tuple(h1 + np.array([-0.08, 0.03, 0.0])), tuple(h1 + np.array([0.08, 0.03, 0.0])), 0.030)
        ferrule = round_cone(tuple(h0 + np.array([0.004, -0.06, 0.0])), tuple(h0 + np.array([0.0, 0.06, 0.0])), 0.052, 0.040)
        spade2 = polygon2(fillet_points([(-0.15, 0.20), (0.15, 0.20), (0.16, -0.02), (0.0, -0.20), (-0.16, -0.02)],
                                        [0.03, 0.03, 0.08, 0.05, 0.08], n_arc=6))
        blade = extrude(spade2, 0.012, round=0.010)
        blade = blade.transform(K.frame_from([0.06, 1.0, 0.0], [0.1, 0.0, 1.0])).translate(0.815, 0.12, 0.42)
        tools = [("shovelHandle", union(handle, grip), K.skin("d_wood_s", WOOD0, WOOD1, vfn=grain_vfn(70, 1), rough=0.55, ior=1.25), 0.004),
                 ("shovelBlade", union(blade, ferrule, k=0.02), metal("d_steel2", STEEL, rough=0.32), 0.003)]
    # ---- assemble the solid parts
    skin_m = K.skin("d_skin", DIG_SKIN, None, rough=0.74, ior=1.2)
    parts = [Part("skin", skin, skin_m, voxel=0.007),
             Part("armL", arms["L"], K.skin("d_skinL", DIG_SKIN, None, rough=0.74, ior=1.2), voxel=0.005),
             Part("armR", arms["R"], K.skin("d_skinR", DIG_SKIN, None, rough=0.74, ior=1.2), voxel=0.005),
             Part("browridge", F["brows"], K.skin("d_browskin", DIG_BROW_SKIN, None, rough=0.7, ior=1.2), voxel=0.003),
             Part("lids", F["lids"], K.skin("d_lidskin", DIG_SKIN, None, rough=0.74, ior=1.2), voxel=0.003),
             Part("crease", F["crease"], satin("d_crease", "#0B3A31", rough=0.6), voxel=0.002),
             Part("eyes", F["eyes"], gloss("d_eye", EYE_WHITE, rough=0.18, ior=1.45), voxel=0.003),
             Part("irises", F["irises"], gloss("d_iris", IRIS_DIG, rough=0.2, ior=1.45), voxel=0.002),
             Part("pupils", F["pupils"], gloss("d_pupil", PUPIL, rough=0.15, ior=1.5), voxel=0.002),
             Part("glints", F["glints"], Material("d_glint", "#FFFFFF", roughness=0.3, emissive="#FFFFFF"), voxel=0.0016),
             Part("nose", nose, K.skin("d_nose", NOSE, None, rough=0.26, ior=1.35, clearcoat=0.35, cc_rough=0.2), voxel=0.003),
             Part("innerEars", inner_ears, K.skin("d_innerear", INNER_EAR, None, rough=0.6, ior=1.2), voxel=0.003),
             Part("soles", soles, K.skin("d_soles", PAD, None, rough=0.62, ior=1.2), voxel=0.004),
             Part("pads", pads, K.skin("d_pads", PAD, None, rough=0.55, ior=1.25), voxel=0.003),
             Part("claws", claws, K.skin("d_claws", CLAW, None, rough=0.34, ior=1.4), voxel=0.0025)]
    if "lipline" in F:
        parts += [Part("lipline", F["lipline"], satin("d_lip", "#0E3F35", rough=0.6), voxel=0.002),
                  Part("philtrum", F["philtrum"], satin("d_phil", "#0E3F35", rough=0.6), voxel=0.002)]
    if "cavity" in F:
        parts += [Part("mouth", F["inner"], Material("d_mouth", MOUTH_IN, roughness=0.55, ior=1.22, emissive="#1A0604"), voxel=0.003),
                  Part("teeth", F["teeth"], Material("d_teeth", "#FFFDF6", roughness=0.25, ior=1.4, emissive="#7A7870"), voxel=0.002),
                  Part("tongue", F["tongue"], Material("d_tongue", TONGUE, roughness=0.35, ior=1.3, emissive="#4A1018"), voxel=0.003)]
    for name, sdf, m, vx in kit + tools + hat_parts:
        parts.append(Part(name, sdf, m, voxel=vx))
    fld = K.field_for(("digger", pose), parts)
    K.shade(parts, field=fld)
    # ---- fur (R1): velvet -- short, dense, little clumping; not under the kit, not in the sockets / nose / pads / ears
    covers = ([] if no_vest else [vest.offset(0.012), piping.offset(0.008)]) + [belt.offset(0.012), nose.offset(0.004), F["eyes"].offset(0.012), inner_ears.offset(0.006),
              soles.offset(0.004), pads.offset(0.006), F["brows"].offset(0.004)]
    if hat_parts:
        covers.append(union(*[s for n_, s, _, _ in hat_parts if n_ in ("hat", "brim")]).offset(0.01))
    if "cavity" in F:
        covers.append(F["cavity"].offset(0.01))
    cover = union(*covers)
    fur_m = FUR.fur_material("d_fur", None, stops=DIG_FUR, rough=0.62)
    furs = [FUR.fur_part("fur", fur_m, _digger_fur(skin, cover, F, view, fld, n_strands, seed, key=("dig_body", pose))),
            FUR.fur_part("furArmL", fur_m, _digger_fur(arms["L"], union(cover, claws.offset(0.006), torso.offset(-0.01)), F, view, fld,
                                                      n_strands // 7, seed + 1, key=("dig_armL", pose), limb=True)),
            FUR.fur_part("furArmR", fur_m, _digger_fur(arms["R"], union(cover, claws.offset(0.006), torso.offset(-0.01)), F, view, fld,
                                                      n_strands // 7, seed + 2, key=("dig_armR", pose), limb=True)),
            FUR.fur_part("browfur", FUR.fur_material("d_browfur", None, stops=DIG_BROW, rough=0.6),
                         _brow_fur(F["brows"], view, fld, seed + 3, key=("dig_brow", pose))),
            FUR.fur_part("lidfur", fur_m, _lid_fur(F["lids"], view, fld, seed + 4, key=("dig_lid", pose)))]
    parts += furs
    if only is not None:
        parts = [p for p in parts if p.name in only]
    return parts, VOXEL


def _digger_fur(sdf, cover, F, view, fld, n, seed, key, limb=False):
    cov = _sdf_fn(cover)

    def fn():
        rng = np.random.default_rng(seed)
        v, f, nn = FUR.surface(sdf, 0.009 if not limb else 0.006, key=key)
        vw = K.unit(view)

        def dens(p):
            p = np.asarray(p)
            w = (cov(p) > 0.0).astype(float)
            nrm = FUR.unit(np.asarray(__import__("sdf").gradient(sdf, p.astype(np.float32), 0.004), float))
            w *= np.clip((nrm @ vw + 0.40) / 0.25, 0, 1)            # the camera side + the silhouette only
            return w
        P, N = FUR.sample(v, f, nn, n, rng, density=dens)
        x, y = P[:, 0], P[:, 1]
        away_nose = FUR.unit(P - D_NOSE_C[None])
        down = np.tile([[0.0, -1.0, -0.35]], (len(P), 1))
        hb = np.clip((y - 1.22) / 0.20, 0, 1)[:, None]
        comb = away_nose * hb + down * (1 - hb) + np.array([0, 0.25, 0])[None] * hb
        L = np.full(len(P), 0.022)
        L += 0.006 * np.clip((y - 1.55) / 0.3, 0, 1)                       # a little longer on the crown / cheeks
        snout = np.clip(1 - np.linalg.norm((P - np.array([0, 1.44, 0.58])) / np.array([0.22, 0.20, 0.20]), axis=1), 0, 1)
        L *= 1 - 0.50 * snout
        for ex, ey in D_EYES:
            dd = np.hypot((x - ex) / 0.10, (y - ey) / 0.115)
            L *= 1 - 0.55 * np.clip(1.6 - dd, 0, 1)
        if "smile_pts" in F:
            from scipy.spatial import cKDTree
            dd, _ = cKDTree(F["smile_pts"]).query(P)
            L *= 1 - 0.6 * np.clip(1 - dd / 0.03, 0, 1)
        if limb:
            L = np.full(len(P), 0.018)
            comb = np.tile([[0.0, -0.4, 1.0]], (len(P), 1))
        L *= 0.85 + 0.30 * rng.random(len(P))
        W = np.full(len(P), 0.0052) * (0.85 + 0.3 * rng.random(len(P)))
        V, Fc, NR, T, ri = FUR.strands(P, N, comb, L, 0.42, W, view, rng, segs=3, gravity=(0, -0.04, 0), clump=0.18,
                                       clump_size=0.018, per_clump=8, jitter=0.22, nbend=0.20)
        uv = FUR.tone_uv(fld, None, T, ri, P, rng.normal(0, 0.05, len(P)), tone0=0.42, tone_gain=0.52, N=N, under=0.28)
        return V, Fc, NR, uv
    return fn


def _brow_fur(brows, view, fld, seed, key):
    def fn():
        rng = np.random.default_rng(seed)
        vb, fb, nb = FUR.surface(brows, 0.004, key=key)
        P, N = FUR.sample(vb, fb, nb, 5000, rng, density=lambda p: (np.asarray(p)[:, 2] > 0.1).astype(float) + 1e-6)
        comb = np.zeros((len(P), 3))
        comb[:, 0] = np.sign(P[:, 0])
        comb[:, 1] = 0.3
        L = np.full(len(P), 0.026) * (0.8 + 0.4 * rng.random(len(P)))
        V, Fc, NR, T, ri = FUR.strands(P, N, comb, L, 0.35, 0.0075, view, rng, segs=3, clump=0.3, clump_size=0.02,
                                       per_clump=10, jitter=0.15, nbend=0.15)
        uv = FUR.tone_uv(fld, None, T, ri, P, rng.normal(0, 0.05, len(P)), tone0=0.40, tone_gain=0.45)
        return V, Fc, NR, uv
    return fn


def _lid_fur(lids, view, fld, seed, key):
    def fn():
        rng = np.random.default_rng(seed)
        v, f, n = FUR.surface(lids, 0.004, key=key)
        P, N = FUR.sample(v, f, n, 2400, rng, density=lambda p: (np.asarray(p)[:, 2] > 0.3).astype(float) + 1e-6)
        comb = np.tile([[0.0, 1.0, 0.0]], (len(P), 1))
        V, Fc, NR, T, ri = FUR.strands(P, N, comb, 0.010, 0.25, 0.0048, view, rng, segs=2, clump=0.2, clump_size=0.02,
                                       per_clump=8, jitter=0.2, nbend=0.15)
        uv = FUR.tone_uv(fld, None, T, ri, P, rng.normal(0, 0.05, len(P)), tone0=0.45, tone_gain=0.45, N=N)
        return V, Fc, NR, uv
    return fn


def hard_hat(center=(0.0, 1.885, 0.03), tilt=-10.0, roll=4.0):
    """Sunflower hard hat (dome + ridge + brim), a headlamp with an emissive lens, brass goggles resting on the brim
    with a leather strap round the dome. -> [(name, sdf, material, voxel)]"""
    c = np.asarray(center, float)
    Rh = K.rotate_matrix((0, 0, 1), roll) @ K.rotate_matrix((1, 0, 0), tilt)

    def place(s):
        return s.transform(Rh).translate(*c)

    def pt(p):
        return Rh @ np.asarray(p, float) + c
    dome = ellipsoid(0.425, 0.335, 0.44).intersect(box(1, 0.5, 1).translate(0, 0.5 - 0.005, 0), k=0.02)
    ridge = ellipsoid(0.445, 0.355, 0.46).intersect(box(0.045, 0.5, 1, round=0.02).translate(0, 0.5, 0)).intersect(
        box(1, 0.5, 1).translate(0, 0.5 + 0.02, 0))
    brim = ellipsoid(0.505, 0.028, 0.56).translate(0, 0.006, 0.07)
    strap = ellipsoid(0.438, 0.345, 0.452).subtract(ellipsoid(0.42, 0.33, 0.435)).intersect(box(1, 0.022, 1).translate(0, 0.075, 0))
    # headlamp on the dome's front, above the goggles
    a = math.radians(42)
    lp = np.array([0.0, 0.335 * math.sin(a), 0.44 * math.cos(a)])
    ln = K.unit([0.0, math.sin(a) * 0.55, math.cos(a)])
    housing = round_cone(tuple(lp - ln * 0.02), tuple(lp + ln * 0.055), 0.070, 0.066)
    lens = cylinder(0.052, 0.006).transform(K.frame_from(ln, [1, 0, 0])).translate(*(lp + ln * 0.118))
    rim_ring = torus(0.058, 0.011).transform(K.frame_from(ln, [1, 0, 0])).translate(*(lp + ln * 0.114))
    # goggles on the strap at the front (lenses looking forward-up)
    gz = []
    lenses = []
    for sx in (-1, 1):
        gp = np.array([sx * 0.098, 0.10, 0.0])
        gp[2] = 0.44 * math.sqrt(max(0.0, 1 - (gp[0] / 0.425) ** 2 - (gp[1] / 0.335) ** 2)) + 0.035
        gn = K.unit([sx * 0.25, 0.30, 1.0])
        Rg = K.frame_from(gn, [1, 0, 0])
        gz.append(torus(0.066, 0.017).transform(Rg).translate(*gp))
        gz.append(round_cone(tuple(gp - gn * 0.03), tuple(gp + gn * 0.008), 0.078, 0.074).subtract(
            cylinder(0.060, 0.2).transform(Rg).translate(*gp)))
        lenses.append(cylinder(0.058, 0.006).transform(Rg).translate(*(gp + gn * 0.004)))
    bridge = capsule((-0.035, 0.10, 0.455), (0.035, 0.10, 0.455), 0.012)
    hat_m = K.skin("d_hat", HAT, None, rough=0.32, ior=1.42)
    return [("hat", place(union(dome, ridge, k=0.01)), hat_m, 0.005),
            ("brim", place(brim), K.skin("d_brim", HAT, None, rough=0.34, ior=1.42), 0.004),
            ("hatStrap", place(strap), K.skin("d_strap", LEATHER, None, rough=0.5, ior=1.25), 0.003),
            ("lampHousing", place(union(housing, rim_ring)), metal("d_lamp", "#8C939C", rough=0.3), 0.003),
            ("lampLens", place(lens), Material("d_lens", "#FFF6D8", roughness=0.1, ior=1.5, emissive="#FFE9A8"), 0.002),
            ("goggles", place(union(*gz, bridge)), metal("d_goggle", BRASS, rough=0.26), 0.0025),
            ("goggleLenses", place(union(*lenses)), glass("d_glens", "#A9E9F2", opacity=0.55), 0.002)]


# ================================================================== BOSS v2 (ruling 38 minimal change set)

B_IRIS = "#D9951F"
B_IRIS_RING = "#8A5510"
HORN = [(0.0, "#FFF6E6"), (0.40, "#F6E6C8"), (0.75, "#E3CFA8"), (1.0, "#C9AE82")]
MUZ_STOPS = [(0.0, [(0.0, "#F28CB4"), (0.5, "#E6749F"), (1.0, "#CC5886")]),
             (0.35, [(0.0, "#FFB8D0"), (0.35, "#FFA9C7"), (0.6, "#FA96B9"), (1.0, "#EA7AA6")]),
             (1.0, [(0.0, "#FFD3E2"), (0.35, "#FFC4D8"), (0.6, "#FFB2CB"), (1.0, "#F79CBC")])]
COAT_T = [(0.0, "#4FB3AF"), (0.40, "#2E8C8A"), (0.72, "#1F6B6B"), (1.0, "#144C4E")]
CORD = [(0.0, "#2F817E"), (0.45, "#1F6B6B"), (0.8, "#164F50"), (1.0, "#0D3436")]
BLUEPRINT = [(0.0, "#A9D2F5"), (0.45, "#7FB6E8"), (0.8, "#5A94CF"), (1.0, "#3A6FA8")]
MUZ_C = np.array([0.015, 0.515])


COAT_T2 = [(0.0, "#44A29E"), (0.40, "#277C7A"), (0.72, "#1A5E5E"), (1.0, "#114244")]


def canvas_vfn(freq=34.0, seed=9):
    from sdf import value_noise3

    def fn(v):
        p = np.asarray(v, np.float32)
        n = 0.65 * value_noise3(p, freq=freq, seed=seed) + 0.35 * value_noise3(p, freq=freq * 2.7, seed=seed + 1)
        return np.clip(0.5 + 0.9 * n, 0, 1)
    return fn


def boss_head_parts(mouth="smile", look=(0.14, -0.40)):
    skin0 = S.head_skin_raw("home")
    zf = K.surface_z_of(skin0, 0.0, 0.57)
    skin0 = union(skin0, ellipsoid(0.30, 0.165, 0.12).translate(0.01, 0.575, zf - 0.075), k=0.07)     # the muzzle's fullness
    F = S.face(skin0, mouth=mouth, look=look, style="home")
    skin = skin0
    if mouth == "smile":
        skin = skin.subtract(F["groove"], k=0.012)
    elif "cavity" in F:
        skin = skin.subtract(F["cavity"], k=0.03)
    skin = skin.subtract(F["sockets"].offset(-0.02), k=0.02)
    F["skin0"] = skin0
    # horns: two short rounded ivory horns replacing the crown tuft, curving out, 3 soft growth rings (grooves)
    horns, rings = [], []
    for sx in (-1, 1):
        bx, by = sx * 0.232, 1.000
        bz = K.surface_z_of(skin0, bx, by) - 0.050
        b0 = np.array([bx, by, bz])
        d0 = K.unit([sx * 0.30, 1.0, 0.12])
        b1 = b0 + d0 * 0.105
        b2 = b1 + K.unit([sx * 0.80, 0.80, 0.10]) * 0.075
        b3 = b2 + K.unit([sx * 1.0, 0.25, 0.05]) * 0.055
        horns.append(K.limb([b0, b1, b2, b3], [0.074, 0.058, 0.040, 0.016], k=0.025))
        for q, rr in ((b0 + (b1 - b0) * 0.55, 0.066), (b1 + (b2 - b1) * 0.15, 0.057)):
            rings.append(torus(rr, 0.0045).transform(K.frame_from(d0, [1, 0, 0])).translate(*q))
    horn = union(*horns).subtract(union(*rings), k=0.003)
    F["horn"] = horn
    # goggles pushed up between the horns (lenses looking up-forward), two thin straps back over the crown
    gl, rims = [], []
    for sx in (-1, 1):
        gx, gy = sx * 0.078, 1.075
        gzz = K.surface_z_of(skin0, gx, gy) + 0.030
        gp = np.array([gx, gy, gzz])
        gn = K.unit([sx * 0.2, 1.0, 0.95])
        Rg = K.frame_from(gn, [1, 0, 0])
        rims.append(torus(0.058, 0.015).transform(Rg).translate(*gp))
        rims.append(round_cone(tuple(gp - gn * 0.028), tuple(gp + gn * 0.006), 0.068, 0.064).subtract(
            cylinder(0.052, 0.2).transform(Rg).translate(*gp)))
        gl.append(cylinder(0.051, 0.005).transform(Rg).translate(*(gp + gn * 0.003)))
    straps = []
    for sx in (-1, 1):
        pts = []
        for t_ in np.linspace(0.0, 1.0, 7):
            x_, y_ = sx * (0.132 + 0.085 * t_), 1.072 - 0.035 * t_
            pts.append([x_, y_, K.surface_z_of(skin0, x_, y_) + 0.030 - 0.045 * t_])
        straps.append(K.limb(np.array(pts), np.full(7, 0.012), k=0.01))
    F["goggles"] = union(*rims, capsule((-0.02, 1.085, K.surface_z_of(skin0, 0, 1.085) + 0.04),
                                        (0.02, 1.085, K.surface_z_of(skin0, 0, 1.085) + 0.04), 0.011))
    F["goggleLenses"] = union(*gl)
    F["straps"] = union(*straps)
    # one snaggle tooth on the screen-left of the closed smile, poking down over the lower lip
    tx = -0.12
    tt = (tx - (S.SMILE_X[0] + S.SMILE_X[1]) / 2) / ((S.SMILE_X[1] - S.SMILE_X[0]) / 2)
    ty = 0.535 + 0.075 * tt ** 2 + 0.030 * tt ** 8 + S.SMILE_TILT * tx
    tz = K.surface_z_of(skin0, tx, ty)
    fang = polygon2(fillet_points([(-0.024, 0.010), (0.024, 0.010), (0.006, -0.050), (-0.002, -0.052)], [0.004, 0.004, 0.006, 0.006], n_arc=4))
    F["tooth"] = extrude(fang, 0.010, round=0.008).transform(K.frame_from([0.08, 1.0, 0.30], [0.0, -0.25, 1.0])).translate(tx, ty + 0.004, tz + 0.004)
    return skin, F


def muzzle_mask(p):
    p = np.asarray(p)
    d = np.hypot((p[:, 0] - MUZ_C[0]) / 0.36, (p[:, 1] - MUZ_C[1]) / 0.175)
    m = np.clip((1.0 - d) / 0.40, 0, 1)
    m = m * m * (3 - 2 * m)
    return m * (p[:, 2] > 0.18)


def boss_head_parts_xf(Rw, tw, view_w, mouth="smile", look=(0.14, -0.40), n_strands=40000, seed=3, extra_field=(),
                       field_key=None):
    """char_scientist.head_parts_xf with the ruling-38 changes (horns, muzzle fur, amber eyes, tooth, goggles; no
    crown tuft). Same head space and placement, so the swap is 1:1."""
    skin_h, F = boss_head_parts(mouth=mouth, look=look)
    PAL = S.pal("home")
    Rw = np.asarray(Rw, float)
    tw = np.asarray(tw, float)
    Ai = np.linalg.inv(Rw)

    def w(s):
        return s.transform(Rw).translate(*tw)

    def wp(P):
        return np.asarray(P, float) @ Rw.T + tw

    def wn(N):
        return np.asarray(N, float) @ Rw.T
    parts = [Part("skin", w(skin_h), K.skin("b_skin", PAL["skin"], None, vfn=None, rough=0.72, ior=1.2), voxel=0.008),
             Part("brows", w(F["brows"]), K.skin("b_browskin", PAL["browskin"], None, vfn=None, rough=0.7, ior=1.2), voxel=0.004),
             Part("eyes", w(F["eyes"]), gloss("b_eye", S.EYE_WHITE, rough=0.18, ior=1.45), voxel=0.003),
             Part("irises", w(F["irises"]), gloss("b_iris", B_IRIS, rough=0.2, ior=1.45), voxel=0.002),
             Part("pupils", w(F["pupils"]), gloss("b_pupil", S.PUPIL, rough=0.15, ior=1.5), voxel=0.002),
             Part("glints", w(F["glints"]), Material("b_glint", "#FFFFFF", roughness=0.3, emissive="#FFFFFF"), voxel=0.0018),
             Part("lipline", w(F["lipline"]), satin("b_lip", S.LIP, rough=0.6), voxel=0.003),
             Part("horns", w(F["horn"]), K.skin("b_horn", HORN, None, vfn=None, rough=0.42, ior=1.35), voxel=0.003),
             Part("tooth", w(F["tooth"]), Material("b_tooth", "#FFFDF8", roughness=0.25, ior=1.4, emissive="#77746E"), voxel=0.002),
             Part("goggles", w(F["goggles"]), metal("b_goggle", BRASS, rough=0.26), voxel=0.0025),
             Part("goggleLenses", w(F["goggleLenses"]), glass("b_glens", "#A9E9F2", opacity=0.55), voxel=0.002),
             Part("goggleStraps", w(F["straps"]), K.skin("b_strap", LEATHER, None, vfn=None, rough=0.5, ior=1.25), voxel=0.003)]
    fld = K.field_for(field_key or ("boss_head", mouth), parts + list(extra_field))
    K.shade(parts, field=fld)
    view_h = K.unit(Ai @ np.asarray(view_w, float))
    horn_f = _sdf_fn(F["horn"])
    gog_f = _sdf_fn(union(F["goggles"], F["goggleLenses"], F["straps"]))
    tooth_f = _sdf_fn(F["tooth"])

    def base_density(p):
        d = S.density(F)(p)
        d *= (horn_f(p) > 0.004).astype(float)
        d *= (gog_f(p) > 0.010).astype(float)
        d *= (tooth_f(p) > 0.02).astype(float)
        return d

    def build(kind):
        def fn():
            rng = np.random.default_rng(seed + {"fur": 0, "brow": 1, "muzzle": 2}[kind])
            v, f, n = FUR.surface(skin_h, 0.012, key=("boss_head_surf", mouth))
            bm = S.brow_mask(F)
            if kind == "fur":
                P, N = FUR.sample(v, f, n, n_strands, rng,
                                  density=lambda p: base_density(p) * (1 - bm(p)) * (1 - muzzle_mask(p)))
                comb, L, lift, W = S.groom(P, N, F, rng, style="home")
                # a short fur collar round each horn base
                hd = horn_f(P)
                ring = np.exp(-(np.clip(hd, 0, None) / 0.05) ** 2)
                L = L * (1 + 0.55 * ring)
                away = FUR.unit(np.asarray(__import__("sdf").gradient(F["horn"], np.asarray(P, np.float32), 0.004), float))
                comb = comb * (1 - ring[:, None]) + away * ring[:, None]
                V, Fc, NR, T, ri = FUR.strands(P, N, comb, L, lift, W, view_h, rng, segs=4, gravity=(0, -0.18, 0),
                                               clump=0.55, clump_size=0.03, per_clump=16, jitter=0.18, nbend=0.15)
                tone0, gain, under = 0.40, 0.55, 0.30
            elif kind == "muzzle":
                P, N = FUR.sample(v, f, n, n_strands // 4, rng, density=lambda p: base_density(p) * muzzle_mask(p))
                cm = np.array([MUZ_C[0], MUZ_C[1] - 0.02, 0.0])
                comb = FUR.unit((P - cm) * np.array([1.0, 1.0, 0.2])) + np.array([0, -0.35, 0])[None]
                L = np.full(len(P), 0.030) * (0.8 + 0.4 * rng.random(len(P)))
                from scipy.spatial import cKDTree
                dd, _ = cKDTree(F["smile"]).query(P)
                L *= 1 - 0.6 * np.clip(1 - dd / 0.05, 0, 1)
                W = np.full(len(P), 0.0062) * (0.8 + 0.4 * rng.random(len(P)))
                V, Fc, NR, T, ri = FUR.strands(P, N, comb, L, 0.38, W, view_h, rng, segs=3, gravity=(0, -0.12, 0),
                                               clump=0.45, clump_size=0.025, per_clump=12, jitter=0.18, nbend=0.15)
                tone0, gain, under = 0.40, 0.55, 0.20
            else:
                vb, fb, nb = FUR.surface(F["brows"], 0.005, key=("boss_brow_surf", mouth))
                P, N = FUR.sample(vb, fb, nb, n_strands // 6, rng, density=lambda p: np.ones(len(p)))
                keep = N[:, 2] > -0.1
                P, N = P[keep], N[keep]
                comb = np.zeros((len(P), 3))
                comb[:, 0] = np.sign(P[:, 0])
                comb[:, 1] = 0.35
                L = np.full(len(P), 0.036) * (0.8 + 0.4 * rng.random(len(P)))
                W = np.full(len(P), 0.0095)
                V, Fc, NR, T, ri = FUR.strands(P, N, comb, L, 0.35, W, view_h, rng, segs=3, clump=0.25,
                                               clump_size=0.03, per_clump=10, jitter=0.12, nbend=0.15)
                tone0, gain, under = 0.40, 0.45, 0.0
            jit = rng.normal(0, 0.06, len(P))
            uv = FUR.tone_uv(fld, None, T, ri, wp(P), jit, tone0=tone0, tone_gain=gain, N=wn(N), under=under)
            return wp(V), Fc, wn(NR), uv
        return fn
    parts.append(FUR.fur_part("fur", FUR.fur_material("b_fur", None, stops=PAL["fur"], rough=0.60), build("fur")))
    parts.append(FUR.fur_part("muzzlefur", FUR.fur_material("b_muzzle", None, stops=MUZ_STOPS, rough=0.62), build("muzzle")))
    parts.append(FUR.fur_part("browfur", FUR.fur_material("b_browfur", None, stops=PAL["brow"], rough=0.6), build("brow")))
    return parts


RAIL_Y, RAIL_Z = 0.86, 0.60
LEVER = dict(hub=(1.02, RAIL_Y + 0.085, RAIL_Z - 0.02), top=(1.04, 1.50, RAIL_Z - 0.10))


def station():
    """The foreman's scaffold (replaces the console): a timber rail on two posts, a lower brace, iron bolts, a brass
    lever with a turned wooden knob on the rail."""
    rail = box(1.62, 0.072, 0.095, round=0.024).translate(0, RAIL_Y, RAIL_Z)
    brace = box(1.62, 0.055, 0.075, round=0.02).translate(0, 0.30, RAIL_Z - 0.02)
    posts = union(*[box(0.085, 0.60, 0.085, round=0.02).translate(sx * 1.22, 0.40, RAIL_Z - 0.03) for sx in (-1, 1)])
    bolts = union(*[cylinder(0.024, 0.012, round=0.006).transform(K.frame_from([0, 0, 1], [1, 0, 0]))
                    .translate(sx * 1.22 + dx, RAIL_Y, RAIL_Z + 0.098) for sx in (-1, 1) for dx in (-0.035, 0.035)])
    hub0 = np.asarray(LEVER["hub"], float)
    top = np.asarray(LEVER["top"], float)
    hub = cylinder(0.075, 0.045, round=0.012).transform(K.frame_from([1, 0, 0], [0, 0, 1])).translate(*hub0)
    arm = capsule(tuple(hub0), tuple(top), 0.030)
    base = box(0.11, 0.022, 0.08, round=0.012).translate(hub0[0], RAIL_Y + 0.08, hub0[2])
    knob = ellipsoid(0.074, 0.080, 0.074).translate(*(top + np.array([0.004, 0.050, 0.004])))
    wood = K.skin("b_wood", WOOD0, WOOD1, vfn=grain_vfn(22, 0), rough=0.62, ior=1.25)
    return [Part("rail", rail, wood, voxel=0.007),
            Part("brace", brace, K.skin("b_wood2", WOOD0, WOOD1, vfn=grain_vfn(22, 0, 3), rough=0.62, ior=1.25), voxel=0.007),
            Part("posts", posts, K.skin("b_wood3", WOOD0, WOOD1, vfn=grain_vfn(30, 1, 5), rough=0.62, ior=1.25), voxel=0.007),
            Part("bolts", bolts, metal("b_iron", "#5A5F66", rough=0.4), voxel=0.003),
            Part("lever", union(hub, arm, base, k=0.01), metal("b_brass", BRASS, rough=0.26), voxel=0.003),
            Part("knob", knob, K.skin("b_knob", [(0.0, "#FFB86A"), (0.45, "#FF8A2A"), (0.8, "#D8620E"), (1.0, "#9A3F04")], None,
                                      rough=0.28, ior=1.4), voxel=0.003)]


def foreman_coat(T, n_):
    """Teal canvas foreman coat (closed; placket + 3 brass buttons; a rounded corduroy collar; a breast pocket with a
    rolled blueprint) in torso space. R7: shells with edges, not body offsets painted on."""
    torso = T["torso"]
    coat = torso.offset(0.045)
    plx = -0.07
    plk = coat.offset(0.014).intersect(box(0.058, 0.8, 1.0, round=0.01).translate(plx, 0.95, 0.8), k=0.006)
    plk = plk.intersect(box(1, 1, 1).translate(0, 0, 1.0 - 0.0))
    buttons = []
    for by in (1.42, 1.18, 0.95):
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
        flaps.append(torso.offset(0.088).intersect(prism, k=0.012))
    collar = union(*flaps, k=0.02)
    px_, py_ = (0.50 + 0.21 * (1 - n_) / 0.2) * n_, 1.02 + 0.10 * (1 - n_) / 0.2
    pocket = coat.offset(0.013).intersect(box(0.19, 0.14, 1.0, round=0.03).translate(px_, py_ - 0.03, 0.4), k=0.01)
    flap = coat.offset(0.020).intersect(box(0.20, 0.035, 1.0, round=0.02).translate(px_, py_ + 0.10, 0.4), k=0.006)
    pz = K.surface_z_of(coat, px_ - 0.02, py_ + 0.10) + 0.02
    r0 = np.array([px_ + 0.03, py_ - 0.02, pz - 0.01])
    r1 = np.array([px_ - 0.10, py_ + 0.30, pz + 0.035])
    roll = capsule(tuple(r0), tuple(r1), 0.046)
    ax = K.unit(r1 - r0)
    band = torus(0.049, 0.008).transform(K.frame_from(ax, [1, 0, 0])).translate(*(r0 + (r1 - r0) * 0.62))
    end = cylinder(0.040, 0.006).transform(K.frame_from(ax, [1, 0, 0])).translate(*(r1 + ax * 0.043))
    return dict(coat=coat, placket=plk, buttons=union(*buttons), collar=collar, pocket=union(pocket, flap, k=0.004),
                roll=roll, rollband=band, rollend=end)


BOSS_ARMS = dict(
    # screen-left paw grips the rail's front edge (fingers curled over it); screen-right paw rests on the lever knob
    L=dict(el=(-1.02, 1.00, 0.10), wr=(-0.88, 1.11, 0.45), d=(0.15, -0.45, 1.0), palm=(0.0, -1.0, 0.15), r=0.17),
    R=dict(el=(1.22, 0.95, 0.02), wr=(1.13, 1.14, 0.37), d=(0.0, 0.05, 1.0), palm=(-1.0, 0.0, 0.0), r=0.17),
)


def boss_v2(pose="home", mouth="smile", n_strands=40000, only=None, view_pose=None, look=(0.14, -0.40)):
    P = S.POSES[pose]
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
    C = foreman_coat(T, n_)
    coatm = K.skin("b_coat", COAT_T, COAT_T2, vfn=canvas_vfn(), rough=0.82, ior=1.2)
    cordm = K.skin("b_cord", CORD, None, vfn=None, rough=0.86, ior=1.18)
    body = [Part("coat", tw(C["coat"]), coatm, voxel=0.008),
            Part("placket", tw(C["placket"]), K.skin("b_coat2", COAT_T, None, vfn=None, rough=0.80, ior=1.2), voxel=0.005),
            Part("buttons", tw(C["buttons"]), metal("b_buttons", BRASS, rough=0.26), voxel=0.0025),
            Part("collar", tw(C["collar"]), cordm, voxel=0.006),
            Part("pocket", tw(C["pocket"]), K.skin("b_coat3", COAT_T, None, vfn=None, rough=0.80, ior=1.2), voxel=0.004),
            Part("blueprint", tw(C["roll"]), K.skin("b_blue", BLUEPRINT, None, vfn=None, rough=0.82, ior=1.2), voxel=0.003),
            Part("blueprintBand", tw(C["rollband"]), satin("b_band", "#E4553A", rough=0.5), voxel=0.002),
            Part("blueprintEnd", tw(C["rollend"]), satin("b_paper", "#F4F7FA", rough=0.7), voxel=0.002)]
    arms = []
    for side, tag in ((-1, "L"), (1, "R")):
        A = BOSS_ARMS[tag]
        W = S.arms_world(Rt, tb, side, variant="hold", narrow=n_, dx=dx, short=True,
                         pts=(A["el"], A["wr"], A["d"], A["palm"], A["r"]))
        sl = W["sleeve"].subtract(tw(C["coat"]).offset(-0.02))
        arms += [Part(f"sleeve{tag}", sl, K.skin(f"b_sleeve{tag}", COAT_T, COAT_T2, vfn=canvas_vfn(seed=11 + side), rough=0.82, ior=1.2), voxel=0.008),
                 Part(f"cuff{tag}", W["cuff"], K.skin(f"b_cuff{tag}", CORD, None, vfn=None, rough=0.86, ior=1.18), voxel=0.006),
                 Part(f"hand{tag}", W["hand"], K.skin("b_handskin", S.pal("home")["skin"], None, vfn=None, rough=0.72, ior=1.2), voxel=0.005)]
    st = station()
    H = P["head"]
    Rh = S.rot((0, 0, 1), H["roll"]) @ S.rot((0, 1, 0), H["yaw"]) @ S.rot((1, 0, 0), H["nod"])
    th = np.array([0.0, S.HEAD_Y, 0.14]) + (Rt @ np.array([0, 1.55, 0]) + tt - np.array([0, 1.55, 0])) * np.array([1, 0, 1])
    head = boss_head_parts_xf(Rh, th, view_w, mouth=mouth, n_strands=n_strands, extra_field=body + arms,
                              field_key=("boss", pose, mouth), look=look)
    fld = K.field_for(("boss_body", pose, mouth), body + arms + st)
    K.shade(body + arms + st, field=fld)
    for side, tag in ((-1, "L"), (1, "R")):
        hp = [p for p in arms if p.name == f"hand{tag}"][0]
        arms.append(S.hand_fur(f"handfur{tag}", hp.sdf, view_w, fld, ("boss_hand", pose, tag), n=11000, seed=7 + side))
    parts = st + body + arms + head
    if only is not None:
        parts = [p for p in parts if p.name in only]
    return parts, VOXEL


# ================================================================== IC-1 "Out the Door" (icon draft)

TANGERINE = ("#FF9A12", "#D06A06", "#9E4A00", "#FFC45A")
BLOCK = [(0.0, "#FFF1D2"), (0.40, "#F3DDB0"), (0.75, "#D9B983"), (1.0, "#9E7A48")]
BLOCK_DARK = [(0.0, "#6A4A2A"), (0.5, "#3E2A16"), (1.0, "#1E140A")]
S_ICON = 2.5
ARROW_ROLL = 38.0


def icon_block():
    """A chunky rounded maze block (lower left): maze channels carved in its top, an arched doorway in its front face
    (dark inside) the arrow bursts out of."""
    blk = box(0.52, 0.40, 0.52, round=0.09)
    walls = []
    # maze channels on the top face (a small hand-drawn maze, 5x5 cells of 0.18)
    segs = [((-0.36, 0.36), (0.18, 0.36)), ((0.36, 0.36), (0.36, -0.18)), ((-0.36, 0.36), (-0.36, -0.36)),
            ((-0.18, 0.18), (0.18, 0.18)), ((0.18, 0.18), (0.18, -0.18)), ((-0.18, 0.18), (-0.18, -0.18)),
            ((-0.36, -0.36), (0.36, -0.36)), ((0.0, -0.18), (0.18, -0.18)), ((0.0, 0.0), (0.0, -0.18))]
    cuts = []
    for (x0, z0), (x1, z1) in segs:
        cuts.append(capsule((x0, 0.40, z0), (x1, 0.40, z1), 0.050))
    blk = blk.subtract(union(*cuts), k=0.012)
    door = union(box(0.23, 0.20, 0.36).translate(0.06, -0.20, 0.52), cylinder(0.23, 0.36).transform(
        K.frame_from([0, 0, 1], [1, 0, 0])).translate(0.06, 0.0, 0.52))
    blk = blk.subtract(door, k=0.02)
    inside = box(0.24, 0.40, 0.08).translate(0.06, -0.05, 0.20)
    wood = K.skin("i_block", BLOCK, None, vfn=None, rough=0.55, ior=1.3)
    return [Part("block", blk, wood, voxel=0.006),
            Part("doorDark", inside, K.skin("i_dark", BLOCK_DARK, None, vfn=None, rough=0.8, ior=1.1), voxel=0.008)], VOXEL


def icon_arrow():
    import arrows3d as A3
    from dataclasses import replace
    A3.SHADES["tangerine"] = TANGERINE
    s2 = A3.arrow2d(shaft=1.55, t=0.165)
    body = extrude(s2, 0.15, round=0.10)
    lo = (-0.79 - 1.55 - 0.05, -0.55)
    size = 0.79 + 1.55 + 0.1
    m = gloss("i_arrow", TANGERINE[0], rough=0.28, ior=1.40)
    m = replace(m, texture=A3.bevel_texture(s2, lo, size, "tangerine", band=0.13), texture_size=1024)
    uv = ("planar", (lo[0], lo[1], 0.0), (1, 0, 0), (0, 1, 0), 1.0 / size)
    return [Part("arrow", body, m, uv=uv)], 0.005


def icon_digger():
    return digger("ride", view_pose=dict(yaw=-16, pitch=8), n_strands=150000)


def icon_hat():
    parts = [Part(n, s, m, voxel=v) for n, s, m, v in hard_hat(center=(0, 0, 0), tilt=0.0, roll=0.0)]
    K.shade(parts, field=K.Field(parts))
    return parts, VOXEL


def _icon_ground(im):
    """Teal radial ground (#1C8C86 -> #0C4A4C) with a faint embossed maze pattern; the render composited on top."""
    from PIL import Image, ImageFilter
    W, H = im.size
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    r = np.hypot((xx - W * 0.46) / W, (yy - H * 0.42) / H)
    t = np.clip(r / 0.75, 0, 1)[..., None]
    c0, c1 = np.array([0x2A, 0xA3, 0x9C], np.float32), np.array([0x0C, 0x4A, 0x4C], np.float32)
    g = c0 * (1 - t) + c1 * t
    # embossed maze: a coarse lattice of wall segments, drawn once, blurred, as a light/dark offset pair
    from PIL import ImageDraw
    rng = np.random.default_rng(7)
    m = Image.new("L", (W, H), 0)
    d = ImageDraw.Draw(m)
    n = 9
    cs = W / n
    for i in range(n + 1):
        for j in range(n + 1):
            if rng.random() < 0.55 and i < n:
                d.line([(i * cs, j * cs), ((i + 1) * cs, j * cs)], fill=255, width=max(2, int(cs * 0.16)))
            if rng.random() < 0.45 and j < n:
                d.line([(i * cs, j * cs), (i * cs, (j + 1) * cs)], fill=255, width=max(2, int(cs * 0.16)))
    m = m.filter(ImageFilter.GaussianBlur(cs * 0.05))
    a = np.asarray(m, np.float32) / 255.0
    lit = np.roll(np.roll(a, -2, 0), -2, 1)
    sh = np.roll(np.roll(a, 2, 0), 2, 1)
    g = g + (lit - sh)[..., None] * 10.0 + a[..., None] * 6.0
    base = Image.fromarray(np.clip(g, 0, 255).astype(np.uint8), "RGB").convert("RGBA")
    base.alpha_composite(im)
    return base.convert("RGB")


def _icon_pos(xn, yn, z=0.0):
    return np.array([(xn - 0.5) * S_ICON, (0.5 - yn) * S_ICON, z])


def _look(yaw, pitch, roll=0.0):
    import uikit
    return uikit.rot_z(roll) @ uikit.rot_x(pitch) @ uikit.rot_y(yaw)


def _icon_layout(tip_n=(0.83, 0.16), block_n=(0.24, 0.77), t_grip=0.34, s_dig=0.58):
    """IC-1 composition (art-direction.md §5): the block in the lower-left third, the arrow's tail in its doorway and
    its head in the top-right third, the Digger gripping the shaft near the optical centre, the hat flying off."""
    blk_pos, blk_s, blk_R = _icon_pos(*block_n, -0.25), 0.82, _look(-14, 12)
    door = blk_pos + blk_s * blk_R @ np.array([0.06, -0.12, 0.50])
    tip = _icon_pos(*tip_n, 0.0)
    tail = np.array([door[0], door[1], 0.0])
    v = tip[:2] - tail[:2]
    roll = math.degrees(math.atan2(v[1], v[0]))
    sa = float(np.linalg.norm(v)) / (2.34 * math.cos(math.radians(14)))
    # the tail sits ~0.15 inside the doorway's recess: the -14 deg yaw sends it 2.34 * sa * sin 14 deeper than the tip
    za = float(door[2]) - 0.15 + 2.34 * sa * math.sin(math.radians(14))
    Ra = K.rotate_matrix((0, 0, 1), roll)
    # the Digger: its paws' midpoint (local) lands on the shaft at t_grip, the local shaft line (37 deg) along the arrow
    g_local = np.array([0.09, 0.66, 0.80])
    Rd_roll = K.rotate_matrix((0, 0, 1), roll - 37.0)
    Rd = Rd_roll @ _look(-16, 8)
    shaft_pt = np.array([tail[0] + (tip[0] - tail[0]) * t_grip, tail[1] + (tip[1] - tail[1]) * t_grip, za])
    pos_d = shaft_pt - s_dig * Rd @ g_local
    head = pos_d + s_dig * Rd @ np.array([0.0, 1.78, 0.1])
    hat_pos = head + np.array([-0.30, 0.26, 0.10])
    return [
        ("icon_block", dict(pos=tuple(blk_pos), yaw=-14, pitch=12, center=False, scale=blk_s)),
        ("icon_arrow", dict(pos=(tip[0], tip[1], za), R=Ra, yaw=-14, pitch=0, center=False, scale=sa)),
        ("icon_digger", dict(pos=tuple(pos_d), R=Rd_roll, yaw=-16, pitch=8, center=False, scale=s_dig)),
        ("icon_hat", dict(pos=tuple(hat_pos), R=K.rotate_matrix((0, 0, 1), 30.0) @ K.rotate_matrix((1, 0, 0), 25.0),
                          yaw=12, pitch=10, center=False, scale=s_dig)),
    ]


ICON_SCENE = _icon_layout()
ICON_LIGHT = dict(LIGHT_D1, key_lux=2000.0, fill_lux=650.0, fill_color=(1.0, 0.90, 0.80), ibl_exp=-0.85)


# ================================================================== cases (route3d: never shipped)

HOME = dict(bounds=S.HOME_VIEW, frame=S.HOME_FRAME, fov=18, no_fit=True)
DIG_SCALE = 57.0
DIG_FRAME = (150, 140)
DIG_VIEW = K.view_bounds(DIG_FRAME, scale_pt=DIG_SCALE, center=(0.04, 1.08), zr=(-0.8, 1.0), margin=1.0)
DIG_VIEW_POSE = dict(yaw=-14, pitch=6, center=False)

MODELS = {
    "boss_v2_home": lambda: boss_v2("home"),
    "digger_hero": lambda: digger("hero"),
    "icon_block": icon_block,
    "icon_arrow": icon_arrow,
    "icon_digger": icon_digger,
    "icon_hat": icon_hat,
}
ASSETS = {
    "concept_bossV2_home": dict(scene=[("boss_v2_home", S.HOME_POSE)], dest="route3d", light=LIGHT_D1, **HOME),
    "concept_bossV2_homeLab": dict(scene=[("boss_v2_home", S.HOME_POSE)], dest="route3d", light=K.light(), **HOME),
    "concept_digger_hero": dict(scene=[("digger_hero", DIG_VIEW_POSE)], dest="route3d", bounds=DIG_VIEW, frame=DIG_FRAME,
                                fov=18, light=LIGHT_D1, no_fit=True),
    "concept_iconIC1": dict(scene=ICON_SCENE, view=(0, 0), frame=(512 / 3, 512 / 3), fov=12, light=ICON_LIGHT,
                            bounds=((-S_ICON / 2, -S_ICON / 2, -0.8), (S_ICON / 2, S_ICON / 2, 0.8)), no_fit=True, margin=1.0,
                            post_fit=_icon_ground, dest="route3d"),
}
