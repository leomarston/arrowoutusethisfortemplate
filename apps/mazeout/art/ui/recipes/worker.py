"""OUR factory worker (art spike, 3D route): a chunky golden capsule in the original's toy style, designed so it is
clearly not theirs.

Style family kept (looked at only: home shot 002, store shots 6/8): a bean-shaped yellow body that IS the head, big
glossy eyes, a wide open grin, stubby limbs with mitten hands, a tool belt over work shorts, soft warm lighting.
Body colours measured on 002/store 8 (k-means): highlight #FECB39, lit #FBB510 (55 %), shade #EE9B0D, deep #D07405.

What makes it OURS (silhouette + details all different from their workers):
  - a gumdrop body, wider at the base (theirs: a tall leaning bean)
  - eyes with free-floating rounded brows and no heavy black upper lids (theirs: thick black lid strokes)
  - one orange hair CURL on top (theirs: two black antenna sprouts / a baseball cap / big glasses)
  - TEAL work shorts + dark-teal boots (theirs: indigo shorts, yellow bare feet)
  - a ROUND brass buckle and a red-handled screwdriver in the belt (theirs: a square lilac buckle + a wrench)

Authoring: +Y up, +Z toward the viewer, ~2 units tall, feet at y 0.
"""
import math

import numpy as np

from uikit import (Part, capsule, ellipsoid, extrude, gloss, box, path_tube, satin, sphere, torus, union, metal,  # noqa: F401
                   cylinder, round_cone)

VOXEL = 0.006
BODY = "#FFB612"
TEAL = "#1F95A6"
BOOT = "#1B5F70"
BELT = "#8E4A1C"
BRASS = "#F4B63A"
RED = "#E8332A"


def _body():
    upper = capsule((0, 0.72, 0), (0, 1.36, 0), 0.50)
    base = ellipsoid(0.62, 0.52, 0.56).translate(0, 0.62, 0)       # the gumdrop: wider at the base
    return union(upper, base, k=0.22)


POSES = {
    # (shoulder -> elbow -> hand) per side, hand radius; feet spread
    "wave": dict(L=((-0.50, 0.92, 0.08), (-0.70, 0.70, 0.16), (-0.74, 0.50, 0.24)),
                 R=((0.50, 0.98, 0.05), (0.74, 1.14, 0.10), (0.78, 1.40, 0.14)), feet=0.26),
    "stand": dict(L=((-0.52, 0.95, 0.05), (-0.78, 0.72, 0.12), (-0.84, 0.46, 0.20)),
                  R=((0.52, 0.95, 0.05), (0.78, 0.72, 0.12), (0.84, 0.46, 0.20)), feet=0.26),
}


def _mitten(p_wrist, direction, r=0.12, thumb_side=1):
    d = np.asarray(direction, float); d /= np.linalg.norm(d)
    c = np.asarray(p_wrist) + d * r * 0.8
    side = np.cross(d, [0, 0, 1.0]); side = side / max(np.linalg.norm(side), 1e-6)
    palm = ellipsoid(r * 1.05, r * 1.15, r * 0.85).orient((0, 1, 0), tuple(d)).translate(*c)
    thumb = capsule(tuple(c - d * r * 0.2 + side * thumb_side * r * 0.75),
                    tuple(c + d * r * 0.25 + side * thumb_side * r * 1.1), r * 0.36)
    return union(palm, thumb, k=0.04)


def worker(pose="wave", split_arm=None):
    """split_arm "R"/"L": that arm + mitten become their own part "arm<side>" (a cut-out puppet layer)."""
    P = POSES[pose]
    body = _body()
    # ---- face (on the upper body, facing +Z)
    eyes, pupils, irises, glints, brows = [], [], [], [], []
    for sx in (-1, 1):
        c = np.array([sx * 0.19, 1.30, 0.40])
        eyes.append(ellipsoid(0.16, 0.19, 0.12).translate(*c))
        iris_c = c + np.array([-sx * 0.012, -0.02, 0.10])
        irises.append(ellipsoid(0.095, 0.11, 0.04).translate(*iris_c))
        pupils.append(ellipsoid(0.055, 0.064, 0.03).translate(*(iris_c + np.array([0, -0.005, 0.02]))))
        glints.append(sphere(0.026).translate(*(iris_c + np.array([0.03, 0.045, 0.035]))))
        glints.append(sphere(0.012).translate(*(iris_c + np.array([-0.035, -0.04, 0.035]))))
        brows.append(capsule(tuple(c + np.array([-0.08, 0.26 + (0.02 if sx < 0 else 0.03), 0.04])),
                             tuple(c + np.array([0.08, 0.26 + (0.045 if sx < 0 else 0.015), 0.04])), 0.034))
    # open grin: a real cavity (a flat-topped half ellipsoid cut into the front), a dark-red inside, a pink tongue on
    # its floor and two front teeth under the upper lip
    grin_zone = ellipsoid(0.27, 0.19, 0.30).translate(0, 1.03, 0.44).intersect(box(1, 0.3, 1).translate(0, 1.03 - 0.3, 0))
    body = body.subtract(grin_zone, k=0.03)
    mouth = ellipsoid(0.25, 0.17, 0.26).translate(0, 1.02, 0.36).intersect(box(1, 0.3, 1).translate(0, 1.04 - 0.3, 0))
    tongue = ellipsoid(0.15, 0.075, 0.16).translate(0.02, 0.89, 0.46)
    teeth = union(*[box(0.045, 0.035, 0.03, round=0.012).translate(sx * 0.052, 1.0, 0.56) for sx in (-1, 1)])
    # hair curl on top (ours): a tube spiralling once
    t = np.linspace(0, 1.6 * math.pi, 22)
    curl_pts = [(0.02 + 0.10 * math.sin(a) * (1 - 0.35 * a / 5), 1.83 + 0.10 * a / 5 + 0.10 * (1 - math.cos(a)) * 0.6, -0.02 + 0.05 * math.cos(a)) for a in t]
    curl = path_tube(curl_pts, [0.055 - 0.025 * i / (len(t) - 1) for i in range(len(t))])
    # ---- clothes: teal shorts, brown belt with a round brass buckle, a red neckerchief knot
    shorts = body.offset(0.03).intersect(box(1.2, 0.2, 1.2).translate(0, 0.30, 0), k=0.02)
    belt = body.offset(0.05).intersect(box(1.2, 0.058, 1.2).translate(0, 0.53, 0), k=0.01)
    buckle = torus(0.075, 0.024).rotate_x(90).translate(0, 0.53, 0.66)
    driver = union(capsule((0.40, 0.66, 0.40), (0.44, 0.52, 0.44), 0.05),
                   capsule((0.44, 0.52, 0.44), (0.47, 0.40, 0.46), 0.018))
    kerchief = body.offset(0.02).intersect(box(1.2, 0.05, 1.2).translate(0, 0.80, 0), k=0.01).intersect(
        box(1.2, 1, 0.9).translate(0, 0, 0.55))
    knot = ellipsoid(0.07, 0.06, 0.05).translate(0.0, 0.76, 0.62)
    # ---- limbs: stubby arms with mittens, short legs with dark-teal boots
    arms, hands, loose = [], [], []
    for side, (s, e, h) in ((-1, P["L"]), (1, P["R"])):
        arm = union(capsule(s, e, 0.115), capsule(e, h, 0.105), k=0.05)
        hand = _mitten(h, np.asarray(h) - np.asarray(e), r=0.15, thumb_side=-side)
        if split_arm == ("L" if side < 0 else "R"):
            loose.append(union(arm, hand, k=0.05))
            continue
        arms.append(arm)
        hands.append(hand)
    legs, boots = [], []
    for sx in (-1, 1):
        fx = sx * P["feet"]
        legs.append(capsule((sx * 0.20, 0.30, 0.0), (fx, 0.14, 0.04), 0.11))
        boots.append(union(ellipsoid(0.15, 0.10, 0.20).translate(fx, 0.08, 0.10),
                           cylinder(0.12, 0.05, round=0.03).translate(fx, 0.03, 0.08), k=0.05))
    parts = [
        Part("body", union(body, *arms, *hands, *legs, k=0.05), gloss("w_body", BODY, rough=0.40, ior=1.28), voxel=0.007),
        Part("mouth", mouth, satin("w_mouth", "#7E1A12", rough=0.5), voxel=0.004),
        Part("tongue", tongue, gloss("w_tongue", "#F0707A", rough=0.4), voxel=0.004),
        Part("teeth", teeth, gloss("w_teeth", "#FFFFFF", rough=0.35), voxel=0.003),
        Part("eyes", union(*eyes), gloss("w_eye", "#FFFFFF", rough=0.22, ior=1.45), voxel=0.004),
        Part("irises", union(*irises), gloss("w_iris", "#6A3A18", rough=0.2), voxel=0.003),
        Part("pupils", union(*pupils), gloss("w_pupil", "#1A0E08", rough=0.18), voxel=0.003),
        Part("glints", union(*glints), gloss("w_glint", "#FFFFFF", rough=0.2), voxel=0.0025),
        Part("brows", union(*brows), satin("w_brow", "#4A240E", rough=0.5), voxel=0.003),
        Part("curl", curl, gloss("w_curl", "#F08A0A", rough=0.4), voxel=0.004),
        Part("shorts", shorts, satin("w_shorts", TEAL, rough=0.62), voxel=0.006),
        Part("belt", belt, satin("w_belt", BELT, rough=0.55), voxel=0.004),
        Part("buckle", buckle, metal("w_buckle", BRASS), voxel=0.003),
        Part("driver_handle", driver, gloss("w_driver", RED, rough=0.3), voxel=0.003),
        Part("boots", union(*boots), satin("w_boot", BOOT, rough=0.5), voxel=0.005),
    ]
    if loose:
        parts.append(Part(f"arm{split_arm}", loose[0], gloss("w_body", BODY, rough=0.40, ior=1.28), voxel=0.007))
    return parts, VOXEL


def _only(names, keep):
    def fn():
        parts, vx = worker("wave", split_arm="R")
        return [p for p in parts if (p.name in names) == keep], vx
    return fn


MODELS = {"worker_wave": lambda: worker("wave"), "worker_stand": lambda: worker("stand"),
          # cut-out puppet proof: the raised right arm as its own layer, everything else as the torso layer
          "worker_puppet_torso": _only({"armR"}, keep=False), "worker_puppet_armR": _only({"armR"}, keep=True)}

# home-screen size: the reference workers stand ~110 pt tall on 002
WORKER_LIGHT = dict(key_lux=2600.0, fill_lux=700.0, fill_color=(1.0, 0.78, 0.5), rim_lux=1400.0, ibl_exp=-0.7)
# Puppet layers share ONE camera: center=False keeps the model origin (no per-part recentring), explicit `bounds`
# fix the framing, `no_fit` keeps registration (the PNG is the raw render resized to the frame; frame aspect = bounds
# aspect 2.1 : 2.25). `anchors` project 3D pivots into the PNG (pt) -> build/ui-art/.../<case>.json sidecar.
PUPPET_VIEW = dict(fov=18, light=WORKER_LIGHT, bounds=((-1.05, -0.12, -1.0), (1.05, 2.13, 1.0)), no_fit=True,
                   frame=(112, 120), dest="route3d")
ASSETS = {
    "workerPuppetTorso_3d": dict(scene=[("worker_puppet_torso", dict(yaw=-16, pitch=6, center=False))], **PUPPET_VIEW),
    "workerPuppetArmR_3d": dict(scene=[("worker_puppet_armR", dict(yaw=-16, pitch=6, center=False))],
                                anchors={"shoulderR": [[0.50, 0.98, 0.05]]}, sidecar="workerPuppetArmR", **PUPPET_VIEW),
    "workerPuppetFull_3d": dict(scene=[("worker_wave", dict(yaw=-16, pitch=6, center=False))], **PUPPET_VIEW),
    "workerHome_3d": dict(model="worker_wave", yaw=-16, pitch=6, frame=(110, 120), fill=0.97, align=(0.5, 1.0), fov=18,
                          light=WORKER_LIGHT, margin=1.15, dest="route3d"),
}
