"""R3 HOME (PLAN-P §4.2; owner item 4: "the arrows under the pink monster are going in to each other ... make sth else
there, but still sth that will actually be looking good and our games style"; SPEC ruling 46: same place and role).

The SIGNPOST: the home cabinet's centrepiece, replacing the random arrow heap (scene_home.pile_layout placed 24 arrows
by jitter with no penetration test). A carved timber post stands on the cabinet floor; FIVE painted arrow boards (R2's
D1 arrow board, char_d1kit.arrow_board: the loading cart carries the same boards) are each bolted to the post by their
own iron bracket, alternating right / left at five heights, each with its own heading (yaw) and tilt (roll); a small
brass lantern hangs from an iron hook on the post top (where the heap's dispenser lamp hung). Every board has its own
mount, so no two arrows can meet: the pairwise overlap gate (art/review/tools/r3_home.py overlap) samples each board's
surface and evaluates every other board's (and the post's) SDF there.

Rig `home_signpost` (art/out/home_signpost_rig/, rig.py explicit mode, one shared view): layers back -> front
    base      the post, its foot block, the finial and the lantern hook (static)
    lantern   the lantern (pivot `hook`: a +-3 deg swing)
    board1..5 one arrow board + its bracket each (pivot `hinge` = the bracket's joint on the post face): the idle sway
              (+-2 deg, desynchronised) and the refill flip-in (scaleX 0 -> 1.06 -> 1 about the hinge, one after another)
Motion data (proposed ui.json blocks) + draw order: art/lanes/home.handoff.json. Frame 190 x 128 pt, placed so the
post's foot stands on the cabinet floor at (196.5, 505) pt.

Units: 1 u = 40 pt (SCALE_PT); x right, y up (the cabinet floor at y = 0), z toward the viewer; the post at x = z = 0.
"""
from __future__ import annotations

import math

import numpy as np

import char_d1kit as D
import char_kit as K
from uikit import Part, box, capsule, cylinder, sphere, torus, union  # noqa: F401
from sdf import path_tube

MODELS = {}
ASSETS = {}

SCALE_PT = 40.0
POST_HW = 0.12            # post half width (9.6 pt square)
POST_TOP = 2.18
HINGE_X = 0.15            # the hinge line, just off the post face
GAP = 0.05                # board tail -> post face clearance (2 pt)

# (paint, side, centre y, yaw deg (heading, + = tip toward the viewer), roll deg (+ = tip up))
BOARDS = [
    ("tangerine", +1, 1.93, 14.0, 7.0),
    ("teal", -1, 1.55, -12.0, 4.0),
    ("sunflower", +1, 1.17, -10.0, -4.0),
    ("coral", -1, 0.80, 15.0, -6.0),
    ("sky", +1, 0.43, 12.0, 3.0),
]
B_LEN, B_W = 1.42, 0.46
LANTERN_AT = (-0.37, 2.62, 0.06)     # the lantern's hanging point (the hook tip)


def _rot_y(deg):
    a = math.radians(deg)
    return np.array([[math.cos(a), 0, math.sin(a)], [0, 1, 0], [-math.sin(a), 0, math.cos(a)]])


def _rot_z(deg):
    a = math.radians(deg)
    return np.array([[math.cos(a), -math.sin(a), 0], [math.sin(a), math.cos(a), 0], [0, 0, 1]])


def board_frame(side, yc, yaw, roll):
    """World pose of board i: the arrow points along +x * side from its tail at the hinge line; R columns = (board x,
    board y = the arrow's direction, board z = the face normal) for char_d1kit.arrow_board; t = the board's centre."""
    hinge = np.array([HINGE_X * side, yc, 0.0])
    # heading: rotate about the hinge's vertical axis; tilt: about the viewer axis (sign mirrored on the left side)
    Rw = _rot_y(-yaw * side) @ _rot_z(roll * side)
    d = Rw @ np.array([side, 0.0, 0.0])
    n = Rw @ np.array([0.0, 0.0, 1.0])
    R = K.frame_from(d, n)
    centre = hinge + d * (GAP - (HINGE_X - POST_HW) + B_LEN / 2)
    return R, centre, hinge


def board_parts(i):
    paint, side, yc, yaw, roll = BOARDS[i]
    R, c, hinge = board_frame(side, yc, yaw, roll)
    parts = D.arrow_board(paint, length=B_LEN, width=B_W, shaft=B_W * 0.56, head_len=B_LEN * 0.36, depth=0.10, seed=20 + i,
                          R=R, t=c)
    out = [(f"{n}{i + 1}", s_, m, v) for n, s_, m, v in parts]
    # the bracket: an iron plate on the post face + an arm to the board's back, two bolt heads on the plate
    d = R[:, 1]
    tail = c - d * B_LEN / 2
    face_x = POST_HW * side
    plate = box(0.012, 0.11, 0.075, round=0.008).translate(face_x + 0.008 * side, yc, 0.0)
    arm_a = np.array([face_x + 0.01 * side, yc, -0.02])
    arm_b = tail + d * 0.22 - R[:, 2] * 0.075
    arm = capsule(tuple(arm_a), tuple(arm_b), 0.026)
    clip = box(0.05, 0.075, 0.012, round=0.006).transform(R).translate(*(tail + d * 0.16 - R[:, 2] * 0.062))
    bolts = union(*[sphere(0.018, center=(face_x + 0.024 * side, yc + dy, 0.045)) for dy in (-0.065, 0.065)],
                  *[sphere(0.016, center=tuple(tail + d * (0.16 + dx) - R[:, 2] * 0.047 + R[:, 0] * 0.0)) for dx in (-0.03, 0.03)])
    iron = D.painted_metal(f"sp_iron{i}", [(0.0, "#7B828C"), (0.5, "#4B4F55"), (1.0, "#2A2D31")],
                           [(0.0, "#C9CED6"), (1.0, "#8A9098")], union(plate, arm, clip), rough=0.42)
    boltm = K.skin(f"sp_bolt{i}", D.BRASS_LUT, None, rough=0.3, ior=1.5)
    out += [(f"bracket{i + 1}", union(plate, arm, clip, k=0.01), iron, 0.003),
            (f"bolts{i + 1}", bolts, boltm, 0.002)]
    return out, hinge


def post_parts():
    from sdf import value_noise3  # noqa: F401
    post = box(POST_HW, POST_TOP / 2, POST_HW, round=0.028).translate(0, POST_TOP / 2, 0)
    # carved rings near the top and a notch band (a carved post, not a plain stick)
    band = box(POST_HW + 0.018, 0.035, POST_HW + 0.018, round=0.014).translate(0, POST_TOP - 0.22, 0)
    finial = union(sphere(0.105, center=(0, POST_TOP + 0.09, 0)),
                   cylinder(0.085, 0.03, round=0.012).translate(0, POST_TOP + 0.005, 0), k=0.02)
    foot = box(0.17, 0.055, 0.17, round=0.02).translate(0, 0.055, 0)
    wood = K.skin("sp_post", D.WOOD0, D.WOOD1, vfn=D.grain_vfn(30, 1, 7), rough=0.62, ior=1.25)
    wood2 = K.skin("sp_foot", D.WOOD1, D.LEATHER, vfn=D.grain_vfn(24, 0, 8), rough=0.66, ior=1.25)
    brass = K.skin("sp_brass", D.BRASS_LUT, None, rough=0.28, ior=1.5)
    # the hook: an iron rod from the post's top face out to the left, curling down to the lantern's bail
    hx, hy, hz = LANTERN_AT
    pts = [(0.0, POST_TOP - 0.05, 0.02), (0.0, POST_TOP + 0.20, 0.03), (-0.10, POST_TOP + 0.34, 0.05),
           (hx + 0.02, hy + 0.10, hz), (hx, hy + 0.02, hz)]
    hook = path_tube(pts, [0.02] * len(pts))
    iron = D.painted_metal("sp_hook", [(0.0, "#7B828C"), (0.5, "#4B4F55"), (1.0, "#2A2D31")],
                           [(0.0, "#C9CED6"), (1.0, "#8A9098")], hook, rough=0.42)
    return [("post", post, wood, 0.004), ("postBand", band, brass, 0.003), ("finial", finial, brass, 0.003),
            ("foot", foot, wood2, 0.004), ("hook", hook, iron, 0.0025)]


def lantern_parts():
    return [(n, s_, m, v) for n, s_, m, v in D.place_parts(D.lantern(1.0), t=LANTERN_AT)]


def all_parts():
    out = post_parts() + lantern_parts()
    for i in range(len(BOARDS)):
        out += board_parts(i)[0]
    return out


BASE_PARTS = {"post", "postBand", "finial", "foot", "hook"}
LANTERN_PARTS = {"lanternBrass", "lanternGlass"}


def board_names(i):
    return {f"board{i + 1}", f"boardFace{i + 1}", f"bracket{i + 1}", f"bolts{i + 1}"}


def _factory(only=None):
    tuples = all_parts()
    parts = [Part(n, s_, m, voxel=v) for n, s_, m, v in tuples]
    K.shade(parts, field=K.field_for("home_signpost", parts))
    if only is not None:
        parts = [p for p in parts if p.name in only]
    return parts, 0.004


FRAME = (190, 128)
POSE = dict(yaw=0, pitch=10)
VIEW = K.view_bounds(FRAME, scale_pt=SCALE_PT, center=(0.0, 1.45), zr=(-1.0, 1.0), margin=1.0, fov=18.0)
LIGHT = dict(D.LIGHT_D1_SOFT, key_lux=1900.0)

_layers = [dict(name="base", parts=BASE_PARTS, pivots={"foot": [0.0, 0.0, 0.0]},
                note="the carved post, foot block, finial and the lantern hook (static)"),
           dict(name="lantern", parts=LANTERN_PARTS, pivots={"hook": list(LANTERN_AT)},
                note="the brass lantern on the post's hook: an idle swing about `hook`")]
for _i in range(len(BOARDS)):
    _hinge = board_frame(*BOARDS[_i][1:])[2]
    _layers.append(dict(name=f"board{_i + 1}", parts=board_names(_i), pivots={"hinge": _hinge.tolist()},
                        note=f"{BOARDS[_i][0]} arrow board + its bracket ({'right' if BOARDS[_i][1] > 0 else 'left'}); "
                             f"sway + the refill flip-in about `hinge`"))

RIGS = {"home_signpost": dict(K.explicit_rig(
    MODELS, ASSETS, "home_signpost", _factory, FRAME, VIEW, POSE, LIGHT, _layers, fov=18.0,
    full_anchors={"foot": (0.0, 0.0, 0.0)}, full_case="homeSignpost"),
    dir="home_signpost_rig", bake=True,
    place=dict(anchor="foot", at=(196.5, 505.0)))}
