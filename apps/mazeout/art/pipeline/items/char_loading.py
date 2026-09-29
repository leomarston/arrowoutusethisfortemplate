"""The LOADING SCREEN characters (store 8 = the loading art; kickoff/state.png = the same screen on the phone, partly
under the notification prompt): our blue workers + the pink scientist reproduced in the original's poses.

Placement is by each character's eye midpoint, measured on store 8 scaled to the phone (x 1178/1320; looked at only):
  carrier (front, box overhead)      eyes (242..303, 1671..1772) + (321..394, 1676..1769) -> mid (315, 1722) px
  flyer (holding the red arrow)      eyes (772..810, 629..670) + (815..860, 634..685)       -> mid (816, 655) px
  runner (glasses + notebook)        eyes (765..809, 1517..1591) + (850..903, 1500..1570)   -> mid (834, 1545) px
  scientist (running with arrows)    eyes (497..543, 962..1027) + (566..620, 952..1016)     -> mid (558, 989) px
Scales set so OUR visible eye whites match theirs (measured blobs, phone px): carrier 104 pt/u at fov 34 (eyes
~105 px tall vs 93-100), flyer 49 pt/u (eyes ~47 vs 41-51), runner 81 pt/u (eyes ~70 vs 70-74), scientist 75 pt/u.
"""
from __future__ import annotations

import numpy as np

import char_kit as K
import char_worker as W

PX2PT = 393 / 1178
COLOUR = "blue"


def eye_mid_pt(px):
    return (px[0] * PX2PT, px[1] * PX2PT)


# ------------------------------------------------------------------ the carrier (front, arms up, the box overhead)
# director round 2 (V1 t=0 next to ours at game size): the carrier read as a squat floating egg with dangling feet and
# a box whose two hand holes read as eyes. Now: a narrower, taller-reading bean (girth 0.86) at a larger scale so the
# body runs down to ~y 745 pt like V1's; running legs (the near foot lifted toward the camera, the far foot down behind);
# the box without holes, tipped so its underside shows; a wide laughing mouth with one tooth band.
CARRIER = dict(
    eyes="open", look=(0.10, 0.02), mouth="laugh", mouth_w=0.44, mouth_y=1.00, mouth_h=0.29, hat=None, glasses=False, no_brows=True,
    girth=0.86, tall=1.14, leg_r=0.165, foot_s=1.35,
    gloves=True, eye_c=(0.205, 1.46), eye_r=(0.195, 0.30, 0.14),
    arms=dict(L=((-0.60, 1.14, 0.00), (-0.80, 1.52, 0.12), (-0.46, 1.92, 0.26), (0.2, 1.0, 0.1), (0.3, 0.0, 1.0), "grip"),
              R=((0.60, 1.14, 0.00), (1.00, 1.46, 0.12), (0.98, 1.86, 0.30), (0.0, 1.0, 0.1), (-0.3, 0.0, 1.0), "grip")),
    feet=dict(L=((-0.20, 0.10, 0.02), (-0.30, -0.36, -0.30), (-0.1, 0.0, 1)),
              R=((0.20, 0.12, 0.10), (0.12, -0.24, 0.62), (0.0, -0.25, 1))),
    props=[("box", dict(center=(0.36, 2.20, 0.12), up=(0.14, 1.0, -0.30), facing=(-0.70, 0.0, 1.0),
                        shape=dict(w=1.55, h=0.60, d=0.95, holes=False))),
           ("arrow", dict(colour="purple", center=(-0.12, 2.86, -0.05), up=(-0.45, 1.0, 0.2), shape=dict(length=0.8, width=0.58))),
           ("arrow", dict(colour="orange", center=(0.26, 2.82, -0.15), up=(0.05, 1.0, -0.1), shape=dict(length=0.72, width=0.55))),
           ("arrow", dict(colour="red", center=(0.62, 2.84, 0.0), up=(0.55, 1.0, 0.15), shape=dict(length=0.9, width=0.62))),
           ("arrow", dict(colour="blue", center=(1.08, 2.42, 0.25), up=(1.0, 0.2, 0.3), shape=dict(length=0.62, width=0.5))),
           ("walkie", dict(center=(-0.62, 0.66, 0.20), up=(0.0, 1.0, 0.0), facing=(-0.8, 0.0, 0.6), s=0.95))],
    belt=dict(buckle=(-0.20, 0.64), pouch=(0.30, 0.62), wrench=(0.46, 0.80), wrench_scale=1.2),
    lean=(6.0, -4.0),
)
CARRIER_R2 = CARRIER      # round 2 (director B), kept for the before/after sheet
# characters r3 (store 8 / V1 next to ours at game size): their carrier is a FULL bean (tall 1.0, ~1.27 u wide at 92
# pt/u, girth ~0.97) turned to screen LEFT (the face sits on the left of the capsule, the pouch + wrench side shows),
# arms nearly vertical from the shoulders to the box's lower corners (gloves on its front edge), and SHORT CHUNKY legs
# (~0.35 u below the shorts) with big rounded shoe feet -- the near foot kicked toward the camera. Round 2's long tube
# legs + flared arms read as a different character.
CARRIER = dict(
    eyes="open", look=(0.05, 0.12), mouth="laugh", mouth_w=0.40, mouth_y=1.10, hat=None, glasses=False,
    face_kw=dict(mouth_h=0.47, teeth_w=0.32, mouth_z=0.06, eye_c=(0.172, 1.46), eye_r=(0.175, 0.235, 0.13), lid_w=0.6),
    no_brows=True, girth=0.97, tall=1.13, belt_y=0.48, gloves=True,
    arms=dict(L=((-0.62, 1.12, 0.00), (-0.60, 1.46, 0.24), (-0.40, 1.78, 0.46), (0.10, 1.0, 0.12), (0.0, 0.2, -1.0), "grip"),
              R=((0.62, 1.12, 0.00), (0.70, 1.46, 0.30), (0.50, 1.76, 0.62), (-0.10, 1.0, 0.12), (0.0, 0.2, -1.0), "grip")),
    # near leg (R) crosses under the belly toward the camera, its big round shoe-foot toe-on to the camera; the far leg
    # (L) kicks back-left (V1 / store 8: both feet on the screen-left half under a body turned left)
    legs=dict(R=((0.10, 0.14, 0.10), (0.04, 0.02, 0.28), (0.00, -0.06, 0.36), (-0.30, -0.35, 1.0), (0.0, -1.0, 0.25)),
              L=((-0.24, 0.10, -0.04), (-0.40, -0.04, -0.10), (-0.50, -0.12, -0.18), (-0.5, -0.4, -0.6), (0.0, -0.8, -0.6))),
    leg_r=0.21, shoe=(0.25, 0.30, 0.22),
    props=[("box", dict(center=(0.32, 2.26, 0.10), up=(0.05, 1.0, 0.08), facing=(-0.18, 0.0, 1.0),
                        shape=dict(w=1.42, h=0.70, d=0.92, holes=False))),
           ("arrow", dict(colour="purple", center=(-0.26, 2.98, -0.05), up=(-0.45, 1.0, 0.2), shape=dict(length=0.8, width=0.58))),
           ("arrow", dict(colour="orange", center=(0.10, 2.96, -0.15), up=(0.05, 1.0, -0.1), shape=dict(length=0.72, width=0.55))),
           ("arrow", dict(colour="red", center=(0.46, 2.98, 0.0), up=(0.55, 1.0, 0.15), shape=dict(length=0.9, width=0.62))),
           ("arrow", dict(colour="blue", center=(0.88, 2.56, 0.25), up=(1.0, 0.2, 0.3), shape=dict(length=0.62, width=0.5))),
           ("walkie", dict(center=(-0.68, 0.54, 0.14), up=(0.0, 1.0, 0.0), facing=(-0.8, 0.0, 0.6), s=0.95))],
    belt=dict(buckle=(-0.18, 0.50), pouch=(0.30, 0.48), wrench=(0.44, 0.70), wrench_scale=1.2),
    lean=(3.0, 0.0),
)
# the loading art is a wide-angle close-up (the near foot is big, the box is seen from below): fov 34
CARRIER_POSE = dict(yaw=-16, pitch=8, center=False)   # r3: turned to screen LEFT (r2: +10)
CARRIER_FRAME = (236, 400)
CARRIER_SCALE = 92.0      # r2: 84 -> 92 (V1's carrier body is ~10 % taller on screen); the eyes stay big (eye_r)
CARRIER_FOV = 34.0
CARRIER_VIEW = K.view_bounds(CARRIER_FRAME, scale_pt=CARRIER_SCALE, center=(0.10, 1.55), zr=(-1.0, 1.0), margin=1.0,
                             fov=CARRIER_FOV)
EYE_MID = [0.0, 1.535, 0.62]     # r3: + 0.075 u = the visible whites' centre (measured 7 pt above the eye_c point)      # r3: the eyes' real centre (face_kw eye_c; r2's eye_c was never applied)

LIGHT = W.WORKER_LIGHT_BLUE

MODELS = {"ld_carrier": lambda: W.worker(CARRIER, COLOUR)}
ASSETS = {"char_workerCarrier": dict(scene=[("ld_carrier", CARRIER_POSE)], bounds=CARRIER_VIEW, frame=CARRIER_FRAME, fov=CARRIER_FOV,
                                  light=LIGHT, no_fit=True, anchors={"eyeMid": [W.leaned(CARRIER, EYE_MID)]})}


# ------------------------------------------------------------------ the flyer (top right: the big red arrow held overhead)
FLYER = dict(
    eyes="open", look=(-0.45, -0.45), mouth="smile", mouth_w=0.30, hat=None, glasses=False, no_brows=True, gloves=True,
    eye_r=(0.19, 0.235, 0.13), eye_c=(0.19, 1.44),
    arms=dict(L=((-0.58, 1.12, 0.0), (-0.70, 1.55, 0.18), (-0.40, 1.95, 0.30), (0.4, 1.0, 0.0), (0.0, -0.2, 1.0), "grip"),
              R=((0.58, 1.10, 0.0), (0.92, 0.92, 0.20), (0.98, 1.20, 0.40), (0.1, 1.0, 0.2), (-1.0, 0.0, 0.3), "grip")),
    feet=dict(L=((-0.22, 0.32, 0.05), (-0.55, 0.12, 0.45), (-0.6, 0.2, 1)), R=((0.22, 0.30, 0.05), (-0.05, 0.02, 0.62), (-0.3, 0.2, 1))),
    props=[("arrow", dict(colour="red", name="bigArrow", center=(-0.02, 3.15, -0.05), up=(-0.30, 1.0, 0.0), facing=(0.25, 0.0, 1.0),
                          shape=dict(length=2.75, width=2.15, shaft=1.15, head_len=1.20, depth=0.40, round_=0.16))),
           ("arrow", dict(colour="blue", name="smallArrow", center=(1.00, 1.50, 0.45), up=(-0.25, 1.0, 0.1), facing=(0.3, 0.0, 1.0),
                          shape=dict(length=0.85, width=0.62, shaft=0.30, head_len=0.36, depth=0.14)))],
    belt=dict(buckle=(0.02, 0.64), pouch=None, wrench=None),
    lean=(-22.0, 0.0),
)
FLYER_POSE = dict(yaw=-8, pitch=-6, center=False)
FLYER_FRAME = (170, 220)          # v2: 150 x 204 clipped the feet + the small arrow (frame grown right / down)
FLYER_SCALE = 49.0
FLYER_VIEW = K.view_bounds(FLYER_FRAME, scale_pt=FLYER_SCALE, center=(0.504, 1.987), zr=(-1.0, 1.0), margin=1.0)

# ------------------------------------------------------------------ the runner (glasses + green cap + notebook, fist up)
RUNNER_R2 = dict(
    eyes="open", look=(0.05, 0.05), mouth="laugh", mouth_w=0.36, mouth_h=0.16, mouth_y=1.02, hat="green",
    hat_tilt=(-10, 0, 18), brim_yaw=-20, hat_size=0.95, glasses=True, brows=(0.20, 0.0), eye_c=(0.25, 1.44),
    eye_r=(0.19, 0.235, 0.13),
    tall=1.08, leg_r=0.155, foot_s=1.3,
    arms=dict(L=((-0.60, 1.02, 0.02), (-1.00, 1.06, 0.14), (-0.95, 1.48, 0.30), (0.1, 1.0, 0.2), (0.2, 0.0, 1.0), "fist"),
              R=((0.60, 1.00, 0.02), (0.78, 0.70, 0.30), (0.52, 0.86, 0.58), (-0.4, 1.0, 0.2), (-0.8, 0.0, 0.6), "grip")),
    feet=dict(L=((-0.22, 0.20, 0.0), (-0.30, -0.16, 0.18), (-0.2, 0, 1)), R=((0.22, 0.24, 0.0), (0.36, 0.04, -0.34), (0.2, 0.3, 1))),
    props=[("clipboard", dict(center=(0.66, 1.00, 0.56), up=(-0.25, 1.0, 0.2), facing=(-0.55, 0.0, 1.0), s=1.15))],
    belt=dict(buckle=(-0.10, 0.64), pouch=(0.42, 0.60), wrench=None),
    lean=(-4.0, 0.0),
)
# characters r3 (store 8 / V1 at game size): their runner is ~20 % bigger than r2's, flexes a BIG fist beside the glasses
# (thick arm, bicep out), grips a spiral NOTEBOOK (brown cover, cream pages, rings on top) against his right side, grins
# wide with a closed-corner open smile (no teeth, tongue low), and runs on SHORT CHUNKY legs with big shoe feet (the near
# foot forward at screen left) -- r2's thin tube legs and small red clipboard read as a different worker
RUNNER = dict(
    eyes="open", look=(0.10, 0.10), mouth="laugh", mouth_w=0.38, mouth_y=1.04, hat="green",
    face_kw=dict(mouth_h=0.13, teeth_w=0.0, mouth_z=0.04, eye_c=(0.200, 1.46), eye_r=(0.18, 0.225, 0.13)),
    hat_tilt=(-10, 0, 14), brim_yaw=-20, hat_size=1.02, glasses=True, eye_c=(0.215, 1.46),
    girth=1.14, tall=1.10, belt_y=0.52, arm_r=(0.16, 0.15, 0.14), no_brows=True, hand_r=dict(L=0.18),   # brows sit under the cap (and missed the dome: a -321 z bound)
    glasses_kw=dict(size=(0.28, 0.255), thick=0.074),
    arms=dict(L=((-0.60, 1.04, 0.02), (-0.94, 0.80, 0.30), (-0.64, 1.02, 0.58), (0.10, 1.0, 0.20), (0.3, 0.0, 1.0), "fist"),
              R=((0.60, 1.00, 0.02), (0.80, 0.72, 0.30), (0.52, 0.92, 0.62), (-0.4, 1.0, 0.2), (-0.8, 0.0, 0.6), "grip")),
    legs=dict(L=((-0.12, 0.16, 0.08), (-0.14, 0.04, 0.34), (-0.16, -0.08, 0.44), (-0.35, -0.30, 1.0), (0.0, -1.0, 0.2)),
              R=((0.22, 0.16, -0.04), (0.36, 0.04, -0.16), (0.44, -0.02, -0.34), (0.3, -0.5, -0.8), (0.0, -0.8, -0.6))),
    leg_r=0.19, shoe=(0.22, 0.28, 0.20),
    props=[("notebook", dict(center=(0.64, 1.10, 0.64), up=(-0.15, 1.0, 0.15), facing=(-0.45, 0.0, 1.0), s=1.30))],
    belt=dict(buckle=(-0.10, 0.54), pouch=(0.42, 0.50), wrench=None),
    lean=(-4.0, 0.0),
)
RUNNER_POSE = dict(yaw=-14, pitch=4, center=False)
RUNNER_FRAME = (236, 236)        # r3: 208 x 212 -> 236 x 236 (the runner is 20 % bigger)
RUNNER_SCALE = 79.0      # r3: 66 -> 79 (store 8's runner is ~20 % bigger: 100 pt bean, cap -> sole 166 pt)
RUNNER_VIEW = K.view_bounds(RUNNER_FRAME, scale_pt=RUNNER_SCALE, center=(-0.04, 1.08), zr=(-0.9, 1.0), margin=1.0)

MODELS["ld_flyer"] = lambda: W.worker(FLYER, COLOUR)
MODELS["ld_runner"] = lambda: W.worker(RUNNER, COLOUR)
ASSETS["char_workerFlyer"] = dict(scene=[("ld_flyer", FLYER_POSE)], bounds=FLYER_VIEW, frame=FLYER_FRAME, fov=18, light=LIGHT,
                               no_fit=True, anchors={"eyeMid": [W.leaned(FLYER, [0.0, 1.44, 0.62])]})
ASSETS["char_workerFist"] = dict(scene=[("ld_runner", RUNNER_POSE)], bounds=RUNNER_VIEW, frame=RUNNER_FRAME, fov=18,
                                light=LIGHT, no_fit=True, anchors={"eyeMid": [W.leaned(RUNNER, [0.0, 1.46, 0.62])]})

# ------------------------------------------------------------------ the scientist (running with arrows, fist forward)
import char_scientist as SC  # noqa: E402

SCI_POSE = dict(yaw=0, pitch=5, center=False)       # r3: -4 -> +5 (store 8 is seen from a little above: the belt smiles, no mouth roof shows)
SCI_FRAME = (318, 306)
SCI_SCALE = 90.0      # the head bbox (tuft top -> jowl bottom) is 354 phone px on store 8 = ~1.3 u; eyes match within 10 %
SCI_VIEW = K.view_bounds(SCI_FRAME, scale_pt=SCI_SCALE, center=(0.10, 1.55), zr=(-1.0, 1.2), margin=1.0)
# r2 (kept): SC.scientist("run", mouth="grin", armL="fist", armR="hold", view_pose=SCI_POSE, look=(0.05, 0.0))
# r3: the "load" pose + style (store 8 measured about the eye line; see char_scientist.POSES["load"])
MODELS["ld_sci"] = lambda: SC.scientist("load", mouth="crescent", armL="fist", armR="hold", view_pose=SCI_POSE, look=(0.25, 0.15))
ASSETS["char_scientistLoading"] = dict(scene=[("ld_sci", SCI_POSE)], bounds=SCI_VIEW, frame=SCI_FRAME, fov=18, light=K.light(),
                             no_fit=True, anchors={"eyeMid": [SC.pose_anchors("load")["eyeMid"]]})


# ------------------------------------------------------------------ the background crowd (workerRunners, P1)
# V1 t=0 (the phone recording; looked at only): three small workers running in behind the scientist at the right, soft
# (depth of field) and hazed toward the lavender room: a top-hat worker waving both arms (head ~ (980, 1180) px), a
# waver (~ (1090, 1230) px), the burger eater in front (~ (1040, 1380) px); beans ~100 px wide (25 pt/u).
import char_avatars as AV  # noqa: E402

# characters r3 (store 8 / V1 at game size): round 2's crowd read as pale blue ghosts, ~30 % too small. Theirs is only
# lightly softened, saturated, and BIG in front: the top-hat worker (eyes ~ (333, 388) pt, bean ~33 pt), the waver
# ((366, 406), ~31 pt) and the burger eater in front ((357, 438), ~60 pt wide, the burger at his open mouth), all on
# short chunky running legs.
RUNNERS_FRAME = (156, 200)        # r3: 112 x 164 -> 156 x 200 (the bigger crowd; the waver's arm reaches past x 402)
RUNNERS_AT = (262.0, 335.0)                  # frame top-left on the 393 x 852 pt screen
RUNNERS_SCALE = 38.0     # r3: 28 -> 38
_RC = (RUNNERS_AT[0] + RUNNERS_FRAME[0] / 2, RUNNERS_AT[1] + RUNNERS_FRAME[1] / 2)
_RUNFEET = dict(L=((-0.22, 0.30, 0.0), (-0.28, 0.08, 0.30), (-0.2, 0.1, 1)), R=((0.22, 0.32, 0.0), (0.28, 0.16, -0.26), (0.2, 0.3, 1)))
_RUNLEGS = dict(L=((-0.18, 0.20, 0.06), (-0.22, 0.04, 0.30), (-0.24, -0.04, 0.40), (-0.2, -0.4, 1.0), (0.0, -1.0, 0.3)),
                R=((0.22, 0.20, -0.04), (0.34, 0.08, -0.16), (0.40, 0.04, -0.34), (0.3, -0.5, -0.8), (0.0, -0.8, -0.6)))
_CHUNKY = dict(legs=_RUNLEGS, leg_r=0.18, shoe=(0.20, 0.26, 0.18))
_UP_L = ((-0.56, 1.02, 0.02), (-0.92, 1.30, 0.10), (-0.86, 1.72, 0.20), (0.0, 1.0, 0.0), (0.2, 0.0, 1.0), "wave")
_UP_R = ((0.56, 1.02, 0.02), (0.92, 1.30, 0.10), (0.86, 1.72, 0.20), (0.0, 1.0, 0.0), (-0.2, 0.0, 1.0), "wave")
_DN_L = ((-0.56, 1.02, 0.02), (-0.76, 0.76, 0.14), (-0.70, 0.52, 0.30), (0.0, -1.0, 0.3), (0.3, 0.0, 1.0), "open")
_FIST_OUT_L = ((-0.56, 1.02, 0.02), (-0.92, 0.96, 0.14), (-1.02, 1.20, 0.30), (-0.3, 1.0, 0.2), (0.3, 0.0, 1.0), "fist")
RUNNERS = [  # (spec, eye target pt on the screen, scale, yaw, z)
    (dict(eyes="open", look=(0.1, 0.1), mouth="open", mouth_w=0.32, hat=None, tophat=True, no_brows=True,
          arms=dict(L=_FIST_OUT_L, R=_UP_R), lean=(4.0, 0.0), **_CHUNKY), (333, 388), 0.80, 10, -0.6),
    (dict(eyes="open", look=(-0.2, 0.1), mouth="open", mouth_w=0.30, hat=None, no_brows=True,
          arms=dict(L=_UP_L, R=_UP_R), lean=(-8.0, 0.0), **_CHUNKY), (369, 401), 0.74, -12, 0.6),
    # the burger eater: no floating brows (theirs has none), the burger lower at a bigger open mouth (teeth above it)
    (dict(AV.AVATARS["char_avatarBurger"][0], lean=(0.0, 0.0), no_brows=True, burger=(0.02, 0.92, 0.74),
          face_kw=dict(mouth_h=0.34), **_CHUNKY), (357, 438), 1.25, 4, 0.4),
]
MODELS["ld_runner0"] = lambda: AV.avatar_worker(RUNNERS[0][0])
MODELS["ld_runner1"] = lambda: AV.avatar_worker(RUNNERS[1][0])
MODELS["ld_runner2"] = lambda: AV.avatar_worker(RUNNERS[2][0])
RUNNERS_VIEW = K.view_bounds(RUNNERS_FRAME, scale_pt=RUNNERS_SCALE, center=(0.0, 0.0), zr=(-1.5, 1.5), margin=1.0)


def _haze(im):
    """V1's crowd sits in the room's haze + depth of field: soften and lift toward the lavender room (#E4DCF4)."""
    from PIL import Image as _I, ImageFilter as _F
    a = im.split()[-1]
    # director r2: round 1 (blur 1.1 px, 22 % haze) still read as crisp saturated stickers at game size; V1's crowd is
    # clearly defocused and lifted toward the room
    # characters r3 (store 8 / V1 side by side): r2's 2.2 px + 36 % made pale ghosts -- theirs is only lightly softened
    # and keeps its saturation (the depth reads from size + position): 1.1 px + 12 %
    rgb = im.convert("RGB").filter(_F.GaussianBlur(1.1))
    rgb = _I.blend(rgb, _I.new("RGB", im.size, (226, 218, 244)), 0.12)
    out = rgb.convert("RGBA")
    out.putalpha(a.filter(_F.GaussianBlur(1.0)))
    return out


_rscene = []
for _i, (_sp, (_ex, _ey), _s, _yaw, _z) in enumerate(RUNNERS):
    _pos = ((_ex - _RC[0]) / RUNNERS_SCALE, -(_ey - _RC[1]) / RUNNERS_SCALE - 1.44 * _s, _z)
    _rscene.append((f"ld_runner{_i}", dict(yaw=_yaw, pitch=4, center=False, pos=_pos, scale=_s)))
ASSETS["char_workerRunners"] = dict(scene=_rscene, bounds=RUNNERS_VIEW, frame=RUNNERS_FRAME, fov=18, light=LIGHT, no_fit=True,
                                    post_fit=_haze)


# ------------------------------------------------------------------ the LEFT crowd (workerCrowdLeft, P1, NEW id r3)
# store 8 / V1 (looked at only): at the left edge, behind the carrier, a worker in a navy cap holding a clipboard out
# toward the room (eyes ~ (12, 478) pt, bean ~45 pt, cut by the screen edge, feet ~530) and two small workers seen from
# BEHIND on the conveyor (~25 pt beans at x 38..68 and 68..90, feet ~495), the first pointing up-left; all soft (depth
# of field). The conveyor itself is the scene lane's (loadingBackdrop).
CROWDL_FRAME = (124, 106)
CROWDL_AT = (-30.0, 436.0)
CROWDL_SCALE = 34.0
_LC = (CROWDL_AT[0] + CROWDL_FRAME[0] / 2, CROWDL_AT[1] + CROWDL_FRAME[1] / 2)
_STAND = dict(L=((-0.22, 0.30, 0.0), (-0.25, 0.0, 0.08), (-0.2, 0, 1)), R=((0.22, 0.30, 0.0), (0.26, 0.0, 0.08), (0.2, 0, 1)))
_POINT_L = ((-0.56, 1.02, 0.02), (-0.90, 1.24, 0.10), (-1.10, 1.56, 0.16), (-0.5, 1.0, 0.0), (0.0, 0.0, 1.0), "open")
CROWDL = [  # (spec, eye target pt, scale, yaw, z)
    (dict(eyes="open", look=(0.45, 0.05), mouth="open", mouth_w=0.20, hat="navy", hat_tilt=(0, 0, 10), brim_yaw=-20,
          hat_size=0.9, no_brows=True, feet=_STAND,
          arms=dict(L=((-0.56, 1.02, 0.02), (-0.40, 0.78, 0.42), (0.20, 0.92, 0.64), (1.0, 0.3, 0.0), (0.0, 0.0, 1.0), "grip"),
                    R=((0.56, 1.02, 0.02), (0.80, 0.88, 0.30), (0.74, 1.08, 0.52), (0.0, 1.0, 0.2), (-1.0, 0.0, 0.2), "grip")),
          props=[("clipboard", dict(center=(0.82, 1.14, 0.56), up=(0.05, 1.0, 0.1), facing=(-0.45, 0.0, 1.0), s=1.25))],
          belt=dict(buckle=(-0.10, 0.64), pouch=None, wrench=None)), (4, 479), 0.90, 35, 0.6),
    (dict(eyes="open", mouth="smile", hat="navy", hat_size=0.95, no_brows=True, feet=_STAND,
          arms=dict(L=_POINT_L, R=((0.56, 1.02, 0.02), (0.76, 0.76, 0.14), (0.70, 0.52, 0.30), (0.0, -1.0, 0.3), (-0.3, 0.0, 1.0),
                                   "open")),
          belt=dict(buckle=(-0.10, 0.64), pouch=None, wrench=None)), (53, 473), 0.56, 150, -1.0),
    (dict(eyes="open", mouth="smile", hat="navy", hat_size=0.95, no_brows=True, feet=_STAND,
          arms=dict(L=_DN_L, R=((0.56, 1.02, 0.02), (0.76, 0.76, 0.14), (0.70, 0.52, 0.30), (0.0, -1.0, 0.3), (-0.3, 0.0, 1.0), "open")),
          belt=dict(buckle=(-0.10, 0.64), pouch=None, wrench=None)), (78, 471), 0.56, 205, -1.2),
]
for _i, (_sp, *_r) in enumerate(CROWDL):
    MODELS[f"ld_crowdL{_i}"] = (lambda sp=_sp: W.worker(sp, COLOUR))
CROWDL_VIEW = K.view_bounds(CROWDL_FRAME, scale_pt=CROWDL_SCALE, center=(0.0, 0.0), zr=(-1.5, 1.5), margin=1.0)


def _haze_far(im):
    """V1's left crowd is further back and clearly defocused (the conveyor's depth of field)."""
    from PIL import Image as _I, ImageFilter as _F
    a = im.split()[-1]
    rgb = im.convert("RGB").filter(_F.GaussianBlur(1.8))
    rgb = _I.blend(rgb, _I.new("RGB", im.size, (226, 218, 244)), 0.16)
    out = rgb.convert("RGBA")
    out.putalpha(a.filter(_F.GaussianBlur(1.6)))
    return out


_lscene = []
for _i, (_sp, (_ex, _ey), _s, _yaw, _z) in enumerate(CROWDL):
    _pos = ((_ex - _LC[0]) / CROWDL_SCALE, -(_ey - _LC[1]) / CROWDL_SCALE - 1.44 * _s, _z)
    _lscene.append((f"ld_crowdL{_i}", dict(yaw=_yaw, pitch=4, center=False, pos=_pos, scale=_s)))
ASSETS["char_workerCrowdLeft"] = dict(scene=_lscene, bounds=CROWDL_VIEW, frame=CROWDL_FRAME, fov=18, light=LIGHT, no_fit=True,
                                      post_fit=_haze_far)


# ------------------------------------------------------------------ loading composition sheet + layout
# v2 (2026-09-25): cases renamed to the manifest ids (char_<id>): scientistLoading, workerCarrier, + proposed ids
# workerFlyer (the red-arrow flyer) and workerFist (fist up + notebook); the background crowd is workerRunners.
LAYOUT = [  # (case, their eye midpoint in phone px on store 8 at phone scale), back -> front
    # r3: the scientist's eye whites measured 3.5 pt right / 3 pt high of store 8's with the eyeMid anchor -> target biased
    ("char_scientistLoading", (558 - 10.5, 989 + 9)), ("char_workerFlyer", (816, 655)), ("char_workerFist", (834, 1545)),
    ("char_workerCarrier", (315, 1722))]


def layout():
    """Frame top-left of every loading character on the 393 x 852 pt screen (placed by the eye midpoint)."""
    import json as _json
    import os as _os
    out = {"char_workerRunners": dict(file="char_workerRunners@3x.png", frame_pt=list(RUNNERS_FRAME), x=RUNNERS_AT[0],
                                      y=RUNNERS_AT[1], z=-1)}
    if _os.path.exists(_os.path.join(K.ART, "out", "char_workerCrowdLeft@3x.png")):     # r3 (P1)
        out["char_workerCrowdLeft"] = dict(file="char_workerCrowdLeft@3x.png", frame_pt=list(CROWDL_FRAME), x=CROWDL_AT[0],
                                           y=CROWDL_AT[1], z=-2)
    for zi, (case, (ex, ey)) in enumerate(LAYOUT):
        anc = _json.load(open(_os.path.join(K.ART, "out", f"{case}.json")))["eyeMid"][0]   # the render's anchor sidecar
        fw, fh = ASSETS[case]["frame"]
        out[case] = dict(file=f"{case}@3x.png", frame_pt=[fw, fh], x=round(ex * PX2PT - anc[0], 2),
                         y=round(ey * PX2PT - anc[1], 2), z=zi)
    return out


def _sheet_loading():
    import json as _json
    import os as _os
    from PIL import Image as _I
    L = layout()
    _json.dump(dict(note="loading screen (store 8 / kickoff state.png): frame top-left x/y in pt on the 393 x 852 "
                         "screen, z back -> front; placed so each character's eye midpoint sits on the original's",
                    characters=L), open(_os.path.join(K.ART, "out", "char_loading_layout.json"), "w"), indent=1)
    base = K.shot("research/store/iphone-8.png")
    flat = K.flat_like(base, (0, 0, 10, 10), (206, 198, 236))
    ctx, solo = base.copy(), flat.copy()
    for case, spec in sorted(L.items(), key=lambda kv: kv[1]["z"]):
        im = _I.open(_os.path.join(K.ART, "out", spec["file"])).convert("RGBA")
        ctx = K.on_shot(ctx, im, spec["x"], spec["y"])
        solo = K.on_shot(solo, im, spec["x"], spec["y"])
    box = (0, 150, 1178, 2400)
    rows = [("loading screen at game size (ours pasted over theirs by the eye midpoints; background characters and "
             "logo are theirs / other lanes)", [("reference store 8 at phone scale (looked at only)", base.crop(box)),
                                                ("ours, flat backdrop", solo.crop(box)),
                                                ("ours over the reference", ctx.crop(box))])]
    return rows, "LOADING SCREEN characters (blue workers, pink scientist) vs the original at game size"


SHEETS = {"loading": _sheet_loading}
